#!/usr/bin/env python3
"""
MCP Server pro Home Assistant
Model Context Protocol server poskytující nástroje pro Claude CLI
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Any, Optional

import httpx
import yaml

# MCP SDK
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    CallToolResult,
)


# =============================================================================
# Konfigurace
# =============================================================================

# Načíst proměnné z env souboru pokud existuje
ENV_FILE = "/etc/ai-terminal.env"
if os.path.exists(ENV_FILE):
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                # Odstranit 'export ' prefix
                if line.startswith('export '):
                    line = line[7:]
                key, _, value = line.partition('=')
                # Odstranit uvozovky
                value = value.strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value

HA_URL = "http://supervisor/core/api"
HA_TOKEN = os.environ.get("SUPERVISOR_TOKEN", "")
MQTT_BROKER = os.environ.get("MQTT_BROKER", "")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 1883))
MQTT_USER = os.environ.get("MQTT_USER", "")
MQTT_PASSWORD = os.environ.get("MQTT_PASSWORD", "")
AI_MODE = os.environ.get("AI_MODE", "dry_run")
CONFIG_PATH = "/config"
BACKUP_DIR = "/config/.ai_backups"
ALLOWED_FILES = os.environ.get("ALLOWED_FILES", "automations.yaml,scripts.yaml,scenes.yaml,configuration.yaml").split(",")


# =============================================================================
# Home Assistant API Client
# =============================================================================

class HAClient:
    """Klient pro Home Assistant REST API"""

    def __init__(self):
        self.base_url = HA_URL
        self.headers = {
            "Authorization": f"Bearer {HA_TOKEN}",
            "Content-Type": "application/json"
        }

    async def get(self, endpoint: str) -> dict:
        """GET request na HA API"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}{endpoint}",
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()

    async def post(self, endpoint: str, data: dict = None) -> dict:
        """POST request na HA API"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}{endpoint}",
                headers=self.headers,
                json=data or {},
                timeout=30.0
            )
            response.raise_for_status()
            return response.json() if response.text else {}

    async def get_states(self) -> list:
        """Získá všechny stavy entit"""
        return await self.get("/states")

    async def get_state(self, entity_id: str) -> dict:
        """Získá stav konkrétní entity"""
        return await self.get(f"/states/{entity_id}")

    async def call_service(self, domain: str, service: str, data: dict = None) -> list:
        """Zavolá HA službu"""
        return await self.post(f"/services/{domain}/{service}", data)

    async def get_config(self) -> dict:
        """Získá konfiguraci HA"""
        return await self.get("/config")

    async def get_services(self) -> list:
        """Získá seznam služeb"""
        return await self.get("/services")


ha_client = HAClient()


# =============================================================================
# YAML Tools
# =============================================================================

def backup_file(filepath: str) -> str:
    """Vytvoří zálohu souboru"""
    if not os.path.exists(filepath):
        return None

    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.basename(filepath)
    backup_path = f"{BACKUP_DIR}/{filename}.{timestamp}.bak"

    with open(filepath, 'r') as src:
        with open(backup_path, 'w') as dst:
            dst.write(src.read())

    return backup_path


def read_yaml_file(filename: str) -> tuple[Any, str]:
    """Přečte YAML soubor"""
    if filename not in ALLOWED_FILES:
        return None, f"Soubor '{filename}' není v seznamu povolených souborů"

    filepath = f"{CONFIG_PATH}/{filename}"
    if not os.path.exists(filepath):
        return None, f"Soubor '{filepath}' neexistuje"

    with open(filepath, 'r', encoding='utf-8') as f:
        content = yaml.safe_load(f)

    return content, None


def write_yaml_file(filename: str, content: Any) -> tuple[bool, str]:
    """Zapíše YAML soubor"""
    if filename not in ALLOWED_FILES:
        return False, f"Soubor '{filename}' není v seznamu povolených souborů"

    filepath = f"{CONFIG_PATH}/{filename}"

    # Záloha
    backup_path = backup_file(filepath)

    # Zápis
    with open(filepath, 'w', encoding='utf-8') as f:
        yaml.dump(content, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    return True, f"Soubor uložen (záloha: {backup_path})"


# =============================================================================
# MCP Server
# =============================================================================

server = Server("ha-mcp-server")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """Seznam dostupných nástrojů"""
    return [
        # Entity tools
        Tool(
            name="ha_get_states",
            description="Získá seznam všech entit a jejich stavů v Home Assistant. Vrací entity_id, state, attributes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "Filtrovat podle domény (light, switch, sensor, climate, cover, binary_sensor, automation, script, scene, input_boolean, input_number, input_select, person, zone, sun, weather)"
                    },
                    "search": {
                        "type": "string",
                        "description": "Hledat v entity_id nebo friendly_name"
                    }
                }
            }
        ),
        Tool(
            name="ha_get_state",
            description="Získá detailní stav konkrétní entity včetně všech atributů",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": "ID entity (např. light.living_room, sensor.temperature)"
                    }
                },
                "required": ["entity_id"]
            }
        ),
        Tool(
            name="ha_call_service",
            description="Zavolá službu Home Assistant (zapnout/vypnout světlo, nastavit teplotu, atd.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "Doména služby (light, switch, climate, cover, media_player, notify, automation, script, scene, input_boolean, input_number, input_select)"
                    },
                    "service": {
                        "type": "string",
                        "description": "Název služby (turn_on, turn_off, toggle, set_temperature, set_hvac_mode, open_cover, close_cover, set_cover_position, volume_set, play_media, set_value, select_option, trigger)"
                    },
                    "entity_id": {
                        "type": "string",
                        "description": "ID cílové entity"
                    },
                    "data": {
                        "type": "object",
                        "description": "Dodatečná data služby (brightness, temperature, position, volume_level, ...)"
                    }
                },
                "required": ["domain", "service"]
            }
        ),
        Tool(
            name="ha_get_services",
            description="Získá seznam všech dostupných služeb v Home Assistant",
            inputSchema={
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "Filtrovat podle domény"
                    }
                }
            }
        ),
        Tool(
            name="ha_get_history",
            description="Získá historii stavů entity",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": "ID entity"
                    },
                    "hours": {
                        "type": "integer",
                        "description": "Počet hodin historie (výchozí 24)",
                        "default": 24
                    }
                },
                "required": ["entity_id"]
            }
        ),

        # Config tools
        Tool(
            name="config_read",
            description="Přečte konfigurační YAML soubor Home Assistant",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": f"Název souboru: {', '.join(ALLOWED_FILES)}"
                    }
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="config_write",
            description=f"Zapíše konfigurační YAML soubor (mód: {AI_MODE}). Automaticky vytvoří zálohu.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": f"Název souboru: {', '.join(ALLOWED_FILES)}"
                    },
                    "content": {
                        "type": "object",
                        "description": "Obsah souboru jako YAML/JSON objekt"
                    }
                },
                "required": ["filename", "content"]
            }
        ),
        Tool(
            name="config_add_automation",
            description="Přidá novou automatizaci do automations.yaml",
            inputSchema={
                "type": "object",
                "properties": {
                    "automation": {
                        "type": "object",
                        "description": "Automatizace jako objekt s alias, description, trigger, condition, action",
                        "properties": {
                            "alias": {"type": "string", "description": "Název automatizace"},
                            "description": {"type": "string", "description": "Popis"},
                            "trigger": {"type": "array", "description": "Seznam triggerů"},
                            "condition": {"type": "array", "description": "Seznam podmínek (volitelné)"},
                            "action": {"type": "array", "description": "Seznam akcí"}
                        },
                        "required": ["alias", "trigger", "action"]
                    }
                },
                "required": ["automation"]
            }
        ),
        Tool(
            name="config_add_script",
            description="Přidá nový skript do scripts.yaml",
            inputSchema={
                "type": "object",
                "properties": {
                    "script_id": {
                        "type": "string",
                        "description": "ID skriptu (bez 'script.' prefixu)"
                    },
                    "script": {
                        "type": "object",
                        "description": "Skript s alias, description, sequence, mode",
                        "properties": {
                            "alias": {"type": "string"},
                            "description": {"type": "string"},
                            "sequence": {"type": "array", "description": "Seznam akcí"},
                            "mode": {"type": "string", "enum": ["single", "restart", "queued", "parallel"]}
                        },
                        "required": ["alias", "sequence"]
                    }
                },
                "required": ["script_id", "script"]
            }
        ),
        Tool(
            name="config_add_scene",
            description="Přidá novou scénu do scenes.yaml",
            inputSchema={
                "type": "object",
                "properties": {
                    "scene": {
                        "type": "object",
                        "description": "Scéna s name a entities",
                        "properties": {
                            "name": {"type": "string"},
                            "entities": {"type": "object", "description": "Slovník entity_id: state/attributes"}
                        },
                        "required": ["name", "entities"]
                    }
                },
                "required": ["scene"]
            }
        ),

        # Template tools
        Tool(
            name="ha_render_template",
            description="Vyhodnotí Jinja2 šablonu v kontextu Home Assistant",
            inputSchema={
                "type": "object",
                "properties": {
                    "template": {
                        "type": "string",
                        "description": "Jinja2 šablona (např. '{{ states(\"sensor.temperature\") }}')"
                    }
                },
                "required": ["template"]
            }
        ),

        # MQTT tools
        Tool(
            name="mqtt_publish",
            description="Publikuje zprávu na MQTT topic",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "MQTT topic"
                    },
                    "payload": {
                        "type": "string",
                        "description": "Zpráva k odeslání"
                    },
                    "retain": {
                        "type": "boolean",
                        "description": "Retain flag",
                        "default": False
                    }
                },
                "required": ["topic", "payload"]
            }
        ),

        # System tools
        Tool(
            name="ha_reload",
            description="Znovu načte konfiguraci Home Assistant",
            inputSchema={
                "type": "object",
                "properties": {
                    "component": {
                        "type": "string",
                        "description": "Co znovu načíst: automation, script, scene, group, core, all",
                        "enum": ["automation", "script", "scene", "group", "core", "all"]
                    }
                },
                "required": ["component"]
            }
        ),
        Tool(
            name="ha_get_config",
            description="Získá informace o konfiguraci Home Assistant (verze, lokace, jednotky, ...)",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="ha_check_config",
            description="Zkontroluje validitu konfigurace Home Assistant",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> CallToolResult:
    """Zpracuje volání nástroje"""
    try:
        result = await _execute_tool(name, arguments)
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]
        )
    except Exception as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Chyba: {str(e)}")],
            isError=True
        )


async def _execute_tool(name: str, args: dict) -> Any:
    """Vykoná nástroj a vrátí výsledek"""

    # =========================================================================
    # Entity tools
    # =========================================================================

    if name == "ha_get_states":
        states = await ha_client.get_states()

        # Filtrování podle domény
        if domain := args.get("domain"):
            states = [s for s in states if s["entity_id"].startswith(f"{domain}.")]

        # Hledání
        if search := args.get("search"):
            search = search.lower()
            states = [s for s in states if
                search in s["entity_id"].lower() or
                search in s.get("attributes", {}).get("friendly_name", "").lower()
            ]

        # Zjednodušený výstup
        return [
            {
                "entity_id": s["entity_id"],
                "state": s["state"],
                "friendly_name": s.get("attributes", {}).get("friendly_name"),
                "last_changed": s.get("last_changed")
            }
            for s in states[:100]  # Limit 100 entit
        ]

    elif name == "ha_get_state":
        entity_id = args["entity_id"]
        state = await ha_client.get_state(entity_id)
        return state

    elif name == "ha_call_service":
        if AI_MODE == "read_only":
            return {"error": "Režim read_only - služby nelze volat", "mode": AI_MODE}

        domain = args["domain"]
        service = args["service"]
        data = args.get("data", {})

        if entity_id := args.get("entity_id"):
            data["entity_id"] = entity_id

        if AI_MODE == "dry_run":
            return {
                "dry_run": True,
                "would_call": f"{domain}.{service}",
                "with_data": data,
                "message": "Režim dry_run - služba nebyla skutečně zavolána"
            }

        result = await ha_client.call_service(domain, service, data)
        return {"success": True, "result": result}

    elif name == "ha_get_services":
        services = await ha_client.get_services()

        if domain := args.get("domain"):
            services = [s for s in services if s["domain"] == domain]

        return services

    elif name == "ha_get_history":
        entity_id = args["entity_id"]
        hours = args.get("hours", 24)

        from datetime import timedelta
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{HA_URL}/history/period/{start_time.isoformat()}",
                headers=ha_client.headers,
                params={"filter_entity_id": entity_id, "end_time": end_time.isoformat()},
                timeout=30.0
            )
            response.raise_for_status()
            history = response.json()

        if history and len(history) > 0:
            return history[0][:50]  # Max 50 záznamů
        return []

    # =========================================================================
    # Config tools
    # =========================================================================

    elif name == "config_read":
        content, error = read_yaml_file(args["filename"])
        if error:
            return {"error": error}
        return {"filename": args["filename"], "content": content}

    elif name == "config_write":
        if AI_MODE == "read_only":
            return {"error": "Režim read_only - zápis není povolen", "mode": AI_MODE}

        if AI_MODE == "dry_run":
            return {
                "dry_run": True,
                "would_write": args["filename"],
                "content_preview": str(args["content"])[:500],
                "message": "Režim dry_run - soubor nebyl skutečně zapsán"
            }

        success, message = write_yaml_file(args["filename"], args["content"])
        return {"success": success, "message": message}

    elif name == "config_add_automation":
        if AI_MODE == "read_only":
            return {"error": "Režim read_only - zápis není povolen", "mode": AI_MODE}

        automation = args["automation"]

        # Načíst existující automatizace
        content, error = read_yaml_file("automations.yaml")
        if error:
            content = []
        if content is None:
            content = []

        # Přidat novou
        content.append(automation)

        if AI_MODE == "dry_run":
            return {
                "dry_run": True,
                "would_add": automation,
                "to_file": "automations.yaml",
                "message": "Režim dry_run - automatizace nebyla skutečně přidána"
            }

        success, message = write_yaml_file("automations.yaml", content)
        return {"success": success, "message": message, "automation": automation}

    elif name == "config_add_script":
        if AI_MODE == "read_only":
            return {"error": "Režim read_only - zápis není povolen", "mode": AI_MODE}

        script_id = args["script_id"]
        script = args["script"]

        content, error = read_yaml_file("scripts.yaml")
        if error:
            content = {}
        if content is None:
            content = {}

        content[script_id] = script

        if AI_MODE == "dry_run":
            return {
                "dry_run": True,
                "would_add": {script_id: script},
                "to_file": "scripts.yaml",
                "message": "Režim dry_run - skript nebyl skutečně přidán"
            }

        success, message = write_yaml_file("scripts.yaml", content)
        return {"success": success, "message": message, "script_id": script_id}

    elif name == "config_add_scene":
        if AI_MODE == "read_only":
            return {"error": "Režim read_only - zápis není povolen", "mode": AI_MODE}

        scene = args["scene"]

        content, error = read_yaml_file("scenes.yaml")
        if error:
            content = []
        if content is None:
            content = []

        content.append(scene)

        if AI_MODE == "dry_run":
            return {
                "dry_run": True,
                "would_add": scene,
                "to_file": "scenes.yaml",
                "message": "Režim dry_run - scéna nebyla skutečně přidána"
            }

        success, message = write_yaml_file("scenes.yaml", content)
        return {"success": success, "message": message, "scene": scene}

    # =========================================================================
    # Template tools
    # =========================================================================

    elif name == "ha_render_template":
        template = args["template"]
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{HA_URL}/template",
                headers=ha_client.headers,
                json={"template": template},
                timeout=30.0
            )
            response.raise_for_status()
            return {"template": template, "result": response.text}

    # =========================================================================
    # MQTT tools
    # =========================================================================

    elif name == "mqtt_publish":
        if AI_MODE == "read_only":
            return {"error": "Režim read_only - MQTT publish není povolen", "mode": AI_MODE}

        topic = args["topic"]
        payload = args["payload"]
        retain = args.get("retain", False)

        if AI_MODE == "dry_run":
            return {
                "dry_run": True,
                "would_publish": {"topic": topic, "payload": payload, "retain": retain},
                "message": "Režim dry_run - zpráva nebyla skutečně odeslána"
            }

        # Použijeme HA MQTT službu
        result = await ha_client.call_service("mqtt", "publish", {
            "topic": topic,
            "payload": payload,
            "retain": retain
        })
        return {"success": True, "topic": topic}

    # =========================================================================
    # System tools
    # =========================================================================

    elif name == "ha_reload":
        if AI_MODE == "read_only":
            return {"error": "Režim read_only - reload není povolen", "mode": AI_MODE}

        component = args["component"]

        if AI_MODE == "dry_run":
            return {
                "dry_run": True,
                "would_reload": component,
                "message": "Režim dry_run - reload nebyl proveden"
            }

        if component == "all":
            await ha_client.call_service("homeassistant", "reload_all")
        elif component == "core":
            await ha_client.call_service("homeassistant", "reload_core_config")
        else:
            await ha_client.call_service(component, "reload")

        return {"success": True, "reloaded": component}

    elif name == "ha_get_config":
        return await ha_client.get_config()

    elif name == "ha_check_config":
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{HA_URL}/config/core/check_config",
                headers=ha_client.headers,
                timeout=60.0
            )
            response.raise_for_status()
            return response.json()

    else:
        return {"error": f"Neznámý nástroj: {name}"}


# =============================================================================
# Main
# =============================================================================

async def main():
    """Spustí MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
