#!/usr/bin/env python3
"""
Entity Agent - správa entit a volání služeb.
"""

import click
import json
from typing import Any, Dict, List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .base_agent import BaseAgent

console = Console()


class EntityAgent(BaseAgent):
    """Agent pro práci s Home Assistant entitami."""

    AGENT_NAME = "entity-agent"
    AGENT_DESCRIPTION = "Správa entit, stavů a služeb"

    SYSTEM_PROMPT = """Jsi expert na Home Assistant entity a služby. Pomáháš uživatelům s:
- Vyhledáváním a filtrováním entit
- Čtením stavů a atributů
- Voláním služeb
- Vysvětlováním stavů a chyb

HLAVNÍ DOMÉNY A JEJICH SLUŽBY:

light:
  - turn_on (brightness_pct, color_temp, rgb_color, transition)
  - turn_off (transition)
  - toggle

switch:
  - turn_on
  - turn_off
  - toggle

climate:
  - set_temperature (temperature, target_temp_high, target_temp_low)
  - set_hvac_mode (hvac_mode: heat, cool, auto, off)
  - set_fan_mode (fan_mode)
  - set_preset_mode (preset_mode: home, away, eco)

cover:
  - open_cover
  - close_cover
  - stop_cover
  - set_cover_position (position: 0-100)
  - set_cover_tilt_position (tilt_position)

fan:
  - turn_on (speed, percentage)
  - turn_off
  - set_percentage (percentage)
  - set_preset_mode (preset_mode)

lock:
  - lock
  - unlock

media_player:
  - turn_on
  - turn_off
  - play_media (media_content_id, media_content_type)
  - media_play
  - media_pause
  - media_stop
  - volume_set (volume_level: 0-1)
  - volume_up
  - volume_down

vacuum:
  - start
  - stop
  - return_to_base
  - locate
  - clean_spot

notify:
  - notify (message, title, data)

automation:
  - turn_on
  - turn_off
  - trigger
  - reload

script:
  - turn_on (volání skriptu)
  - turn_off
  - reload

scene:
  - turn_on (aktivace scény)

homeassistant:
  - turn_on (univerzální)
  - turn_off
  - toggle
  - update_entity
  - reload_core_config

input_boolean:
  - turn_on
  - turn_off
  - toggle

input_number:
  - set_value (value)
  - increment
  - decrement

input_select:
  - select_option (option)
  - select_first
  - select_last
  - select_next
  - select_previous

input_text:
  - set_value (value)

input_datetime:
  - set_datetime (date, time, datetime)

FORMÁT PRO VOLÁNÍ SLUŽBY:
```json
{
  "domain": "light",
  "service": "turn_on",
  "data": {
    "entity_id": "light.living_room",
    "brightness_pct": 80
  }
}
```

Když uživatel požaduje akci, vygeneruj JSON s voláním služby.
Když uživatel požaduje informace, poskytni je ve srozumitelné formě.
"""

    def build_context(self) -> str:
        """Sestavení kontextu s entitami."""
        context_parts = []

        # Všechny entity podle domén
        all_entities = self.get_entities()

        # Seskupení podle domén
        domains = {}
        for entity in all_entities:
            entity_id = entity.get("entity_id", "")
            domain = entity_id.split(".")[0] if "." in entity_id else "unknown"
            if domain not in domains:
                domains[domain] = []
            domains[domain].append(entity)

        context_parts.append(f"CELKEM ENTIT: {len(all_entities)}")
        context_parts.append("\nENTITY PODLE DOMÉN:")

        for domain, entities in sorted(domains.items()):
            context_parts.append(f"\n{domain.upper()} ({len(entities)}):")
            for e in entities[:15]:  # Max 15 na doménu
                entity_id = e.get("entity_id", "")
                state = e.get("state", "")
                name = e.get("attributes", {}).get("friendly_name", "")
                context_parts.append(f"  - {entity_id}: {state} ({name})")
            if len(entities) > 15:
                context_parts.append(f"  ... a dalších {len(entities) - 15}")

        return "\n".join(context_parts)

    def process(self, user_request: str) -> Dict[str, Any]:
        """Zpracování požadavku na entity."""
        console.print(f"[bold blue]Zpracovávám požadavek...[/bold blue]\n")

        try:
            response = self.call_ai(user_request)

            # Zkus extrahovat JSON pro volání služby
            service_call = self._extract_service_call(response)

            if service_call:
                return {
                    "success": True,
                    "response": response,
                    "service_call": service_call,
                    "action": "call_service",
                }

            return {
                "success": True,
                "response": response,
                "action": "info",
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    def _extract_service_call(self, response: str) -> Optional[Dict]:
        """Extrakce volání služby z odpovědi."""
        import re

        # Hledej JSON blok
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Hledej inline JSON
        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except json.JSONDecodeError:
            pass

        return None

    def list_entities(self, domain: Optional[str] = None, filter_str: Optional[str] = None) -> List[Dict]:
        """Seznam entit s volitelným filtrem."""
        entities = self.get_entities(domain)

        if filter_str:
            filter_lower = filter_str.lower()
            entities = [
                e for e in entities
                if filter_lower in e.get("entity_id", "").lower()
                or filter_lower in e.get("attributes", {}).get("friendly_name", "").lower()
            ]

        return entities

    def get_entity_state(self, entity_id: str) -> Optional[Dict]:
        """Získání stavu konkrétní entity."""
        if not self.ha:
            return None

        try:
            return self.ha.get_entity_state(entity_id)
        except Exception:
            return None

    def call_service(self, domain: str, service: str, data: Optional[Dict] = None) -> bool:
        """Volání HA služby."""
        if not self.ha:
            return False

        try:
            self.ha.call_service(domain, service, data or {})
            return True
        except Exception as e:
            console.print(f"[red]Chyba: {e}[/red]")
            return False


# CLI Interface
@click.group()
def cli():
    """Entity Agent - správa HA entit."""
    pass


@cli.command("list")
@click.argument("domain", required=False)
@click.option("--filter", "-f", "filter_str", help="Filtr podle názvu")
@click.option("--limit", "-l", default=50, help="Maximální počet")
def list_cmd(domain: Optional[str], filter_str: Optional[str], limit: int):
    """Seznam entit."""
    import sys
    sys.path.insert(0, "/app")

    from ha_interface import HAInterface

    agent = EntityAgent(ha_interface=HAInterface())
    entities = agent.list_entities(domain, filter_str)

    table = Table(title=f"Entity ({len(entities)})")
    table.add_column("Entity ID", style="cyan")
    table.add_column("Stav", style="green")
    table.add_column("Název", style="white")

    for entity in entities[:limit]:
        table.add_row(
            entity.get("entity_id", ""),
            str(entity.get("state", "")),
            entity.get("attributes", {}).get("friendly_name", ""),
        )

    console.print(table)

    if len(entities) > limit:
        console.print(f"[dim]... a dalších {len(entities) - limit} entit[/dim]")


@cli.command()
@click.argument("entity_id")
def state(entity_id: str):
    """Zobrazení stavu entity."""
    import sys
    sys.path.insert(0, "/app")

    from ha_interface import HAInterface

    agent = EntityAgent(ha_interface=HAInterface())
    entity = agent.get_entity_state(entity_id)

    if not entity:
        console.print(f"[red]Entita {entity_id} nenalezena[/red]")
        return

    console.print(Panel(
        f"[bold]Entity ID:[/bold] {entity.get('entity_id')}\n"
        f"[bold]Stav:[/bold] {entity.get('state')}\n"
        f"[bold]Poslední změna:[/bold] {entity.get('last_changed', '')[:19]}\n"
        f"[bold]Atributy:[/bold]\n{json.dumps(entity.get('attributes', {}), indent=2, ensure_ascii=False)}",
        title=entity.get("attributes", {}).get("friendly_name", entity_id),
        border_style="cyan"
    ))


@cli.command()
@click.argument("domain")
@click.argument("service")
@click.option("--entity", "-e", "entity_id", help="Entity ID")
@click.option("--data", "-d", "data_json", help="JSON data")
def call(domain: str, service: str, entity_id: Optional[str], data_json: Optional[str]):
    """Volání služby."""
    import sys
    sys.path.insert(0, "/app")

    from ha_interface import HAInterface

    agent = EntityAgent(ha_interface=HAInterface())

    data = {}
    if entity_id:
        data["entity_id"] = entity_id
    if data_json:
        data.update(json.loads(data_json))

    console.print(f"[dim]Volám {domain}.{service}...[/dim]")

    if agent.call_service(domain, service, data):
        console.print(f"[green]OK[/green]")
    else:
        console.print(f"[red]Chyba[/red]")


@cli.command()
@click.argument("entity_id")
def on(entity_id: str):
    """Zapnutí entity."""
    import sys
    sys.path.insert(0, "/app")

    from ha_interface import HAInterface

    agent = EntityAgent(ha_interface=HAInterface())
    domain = entity_id.split(".")[0]

    if agent.call_service(domain, "turn_on", {"entity_id": entity_id}):
        console.print(f"[green]{entity_id} zapnuto[/green]")


@cli.command()
@click.argument("entity_id")
def off(entity_id: str):
    """Vypnutí entity."""
    import sys
    sys.path.insert(0, "/app")

    from ha_interface import HAInterface

    agent = EntityAgent(ha_interface=HAInterface())
    domain = entity_id.split(".")[0]

    if agent.call_service(domain, "turn_off", {"entity_id": entity_id}):
        console.print(f"[yellow]{entity_id} vypnuto[/yellow]")


@cli.command()
@click.argument("entity_id")
def toggle(entity_id: str):
    """Přepnutí entity."""
    import sys
    sys.path.insert(0, "/app")

    from ha_interface import HAInterface

    agent = EntityAgent(ha_interface=HAInterface())
    domain = entity_id.split(".")[0]

    if agent.call_service(domain, "toggle", {"entity_id": entity_id}):
        console.print(f"[cyan]{entity_id} přepnuto[/cyan]")


@cli.command()
@click.argument("request")
def ask(request: str):
    """Dotaz na AI ohledně entit."""
    import sys
    sys.path.insert(0, "/app")

    from ha_interface import HAInterface
    from claude_client import ClaudeClient

    agent = EntityAgent(
        ha_interface=HAInterface(),
        claude_client=ClaudeClient(),
    )

    result = agent.process(request)
    agent.show_result(result)

    # Pokud je návrh na volání služby
    if result.get("service_call"):
        sc = result["service_call"]
        console.print(f"\n[yellow]Návrh volání služby:[/yellow]")
        console.print(f"  {sc.get('domain')}.{sc.get('service')}")
        console.print(f"  Data: {json.dumps(sc.get('data', {}), ensure_ascii=False)}")


if __name__ == "__main__":
    cli()
