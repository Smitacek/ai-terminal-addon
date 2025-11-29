#!/usr/bin/env python3
"""
AI Agent pro Home Assistant
Hlavni modul pro AI-asistovanou konfiguraci Home Assistanta.
"""

import os
import sys
import json
import click
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.prompt import Confirm

from config_manager import ConfigManager
from yaml_tools import YAMLHandler
from ha_interface import HAInterface
from claude_client import ClaudeClient

console = Console()


class AIAgent:
    """Hlavni AI agent pro konfiguraci Home Assistanta."""

    def __init__(self):
        self.mode = os.environ.get("AI_MODE", "dry_run")
        self.backup_enabled = os.environ.get("BACKUP_ENABLED", "true").lower() == "true"
        self.sandbox_enabled = os.environ.get("SANDBOX_ENABLED", "true").lower() == "true"
        self.sandbox_dir = os.environ.get("SANDBOX_DIR", "/config/ai_sandbox")
        self.allowed_files = self._parse_allowed_files()
        self.backup_dir = os.environ.get("BACKUP_DIR", "/config/.ai_backups")

        self.config_manager = ConfigManager(
            config_dir="/config",
            backup_dir=self.backup_dir,
            sandbox_dir=self.sandbox_dir,
            allowed_files=self.allowed_files,
        )
        self.yaml_handler = YAMLHandler()
        self.ha_interface = HAInterface()
        self.claude_client = ClaudeClient()

    def _parse_allowed_files(self) -> list:
        """Parsovani allowed_files z env promenne."""
        files_str = os.environ.get("ALLOWED_FILES", "")
        if not files_str:
            return ["automations.yaml", "scripts.yaml", "scenes.yaml"]
        return [f.strip() for f in files_str.split(",") if f.strip()]

    def show_status(self):
        """Zobrazeni aktualniho stavu agenta."""
        status_info = f"""
[bold]AI Terminal Agent Status[/bold]

Mode:           [cyan]{self.mode}[/cyan]
Backup:         [{'green' if self.backup_enabled else 'red'}]{self.backup_enabled}[/]
Sandbox:        [{'green' if self.sandbox_enabled else 'red'}]{self.sandbox_enabled}[/]
Sandbox Dir:    [dim]{self.sandbox_dir}[/dim]
Backup Dir:     [dim]{self.backup_dir}[/dim]

Allowed Files:
"""
        for f in self.allowed_files:
            status_info += f"  - {f}\n"

        console.print(Panel(status_info, title="AI Agent", border_style="blue"))

    def gather_context(self) -> dict:
        """Sebrani kontextu pro AI - konfigurace, entity, MQTT."""
        context = {
            "mode": self.mode,
            "allowed_files": self.allowed_files,
            "config_files": {},
            "entities": [],
            "mqtt_topics": [],
        }

        # Nacteni povolenych konfiguracnich souboru
        for filename in self.allowed_files:
            filepath = Path("/config") / filename
            if filepath.exists():
                try:
                    content = self.yaml_handler.read_file(str(filepath))
                    context["config_files"][filename] = content
                except Exception as e:
                    console.print(f"[yellow]Varovani: Nelze nacist {filename}: {e}[/yellow]")

        # Nacteni entit z HA (pokud je k dispozici token)
        try:
            entities = self.ha_interface.get_entities()
            context["entities"] = entities[:100]  # Limit pro kontext
        except Exception as e:
            console.print(f"[dim]HA entity registry nedostupny: {e}[/dim]")

        # Nacteni MQTT topicu (pokud existuje cache)
        mqtt_cache = Path("/config/ai_mqtt_topics.json")
        if mqtt_cache.exists():
            try:
                with open(mqtt_cache) as f:
                    context["mqtt_topics"] = json.load(f)
            except Exception:
                pass

        return context

    def build_system_prompt(self, context: dict) -> str:
        """Vytvoreni systemoveho promptu pro Claude."""
        return f"""Jsi AI asistent pro konfiguraci Home Assistanta. Tvym ukolem je pomoci uzivateli s upravou YAML konfigurace.

PRAVIDLA:
1. VZDY vracis kompletni, validni YAML kod
2. Zachovej existujici strukturu a komentare kde je to mozne
3. Pouzivej entity_id ktere existuji v systemu
4. Dodrzuj HA best practices
5. Kazdy soubor oznac komentarem # FILE: nazev.yaml

AKTUALNI MOD: {context['mode']}
- read_only: Pouze zobraz navrhy, nic nezapisuj
- dry_run: Uloz do *.ai.yaml pro kontrolu
- apply: Zapis primo do konfigurace (s backupem)

POVOLENE SOUBORY PRO UPRAVU:
{', '.join(context['allowed_files'])}

DOSTUPNE ENTITY (ukazka):
{json.dumps(context.get('entities', [])[:20], indent=2)}

AKTUALNI KONFIGURACE:
"""

    def process_request(self, user_request: str) -> dict:
        """Zpracovani uzivatelskeho pozadavku."""
        console.print(f"\n[bold blue]Zpracovavam pozadavek...[/bold blue]")
        console.print(f"[dim]Mod: {self.mode}[/dim]\n")

        # 1. Sebrani kontextu
        context = self.gather_context()

        # 2. Pridani obsahu souboru do promptu
        system_prompt = self.build_system_prompt(context)
        for filename, content in context["config_files"].items():
            system_prompt += f"\n# FILE: {filename}\n{content}\n"

        # 3. Volani Claude API
        console.print("[dim]Volam Claude API...[/dim]")
        try:
            response = self.claude_client.chat(
                system_prompt=system_prompt,
                user_message=user_request,
            )
        except Exception as e:
            console.print(f"[red]Chyba pri volani Claude API: {e}[/red]")
            return {"success": False, "error": str(e)}

        # 4. Parsovani odpovedi - extrakce YAML bloku
        files_to_update = self._parse_response(response)

        if not files_to_update:
            # Zadne soubory k uprave - jen zobrazit odpoved
            console.print(Panel(response, title="Claude", border_style="green"))
            return {"success": True, "response": response, "files": []}

        # 5. Zobrazeni navrzenych zmen
        console.print("\n[bold]Navrzene zmeny:[/bold]\n")
        for filename, content in files_to_update.items():
            syntax = Syntax(content, "yaml", theme="monokai", line_numbers=True)
            console.print(Panel(syntax, title=f"FILE: {filename}", border_style="cyan"))

        # 6. Aplikace zmen podle modu
        result = self._apply_changes(files_to_update)

        return result

    def _parse_response(self, response: str) -> dict:
        """Parsovani odpovedi Claude - extrakce YAML souboru."""
        files = {}
        current_file = None
        current_content = []

        lines = response.split("\n")
        in_yaml_block = False

        for line in lines:
            # Detekce zacatku souboru
            if line.strip().startswith("# FILE:"):
                if current_file and current_content:
                    files[current_file] = "\n".join(current_content)
                current_file = line.replace("# FILE:", "").strip()
                current_content = []
                in_yaml_block = True
            elif line.strip().startswith("```yaml"):
                in_yaml_block = True
            elif line.strip() == "```" and in_yaml_block:
                if current_file and current_content:
                    files[current_file] = "\n".join(current_content)
                    current_file = None
                    current_content = []
                in_yaml_block = False
            elif in_yaml_block and current_file:
                current_content.append(line)

        # Posledni soubor
        if current_file and current_content:
            files[current_file] = "\n".join(current_content)

        # Filtrovani pouze povolenych souboru
        allowed = {k: v for k, v in files.items() if k in self.allowed_files}
        return allowed

    def _apply_changes(self, files: dict) -> dict:
        """Aplikace zmen podle aktualniho modu."""
        results = {"success": True, "files": [], "mode": self.mode}

        for filename, content in files.items():
            filepath = Path("/config") / filename

            if self.mode == "read_only":
                # Jen zobrazit, nic neukladat
                console.print(f"[yellow]READ_ONLY: {filename} - neukladam[/yellow]")
                results["files"].append({"file": filename, "action": "displayed"})

            elif self.mode == "dry_run":
                # Ulozit do *.ai.yaml
                ai_filepath = filepath.with_suffix(".ai.yaml")
                if self.sandbox_enabled:
                    ai_filepath = Path(self.sandbox_dir) / f"{filename}.ai.yaml"
                    Path(self.sandbox_dir).mkdir(parents=True, exist_ok=True)

                self.yaml_handler.write_file(str(ai_filepath), content)
                console.print(f"[green]DRY_RUN: Ulozeno do {ai_filepath}[/green]")
                results["files"].append({"file": filename, "action": "dry_run", "path": str(ai_filepath)})

            elif self.mode == "apply":
                # Potvrzeni od uzivatele
                if not Confirm.ask(f"Opravdu prepsat {filename}?"):
                    console.print(f"[yellow]Preskakuji {filename}[/yellow]")
                    continue

                # Backup
                if self.backup_enabled and filepath.exists():
                    backup_name = f"{filename}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
                    backup_path = Path(self.backup_dir) / backup_name
                    Path(self.backup_dir).mkdir(parents=True, exist_ok=True)

                    import shutil
                    shutil.copy(filepath, backup_path)
                    console.print(f"[dim]Backup: {backup_path}[/dim]")

                # Zapis
                self.yaml_handler.write_file(str(filepath), content)
                console.print(f"[green]APPLY: {filename} upraven[/green]")
                results["files"].append({"file": filename, "action": "applied"})

                # Validace
                self._validate_config()

        return results

    def _validate_config(self):
        """Validace konfigurace pres HA API."""
        console.print("\n[dim]Validuji konfiguraci...[/dim]")
        try:
            valid = self.ha_interface.check_config()
            if valid:
                console.print("[green]Konfigurace je validni![/green]")
            else:
                console.print("[red]Konfigurace obsahuje chyby![/red]")
        except Exception as e:
            console.print(f"[yellow]Nelze validovat: {e}[/yellow]")


@click.command()
@click.argument("request", required=False)
@click.option("--status", is_flag=True, help="Zobraz status agenta")
@click.option("--mode", type=click.Choice(["read_only", "dry_run", "apply"]), help="Prepis mod")
def main(request: str, status: bool, mode: str):
    """AI Config Agent pro Home Assistant.

    Pouziti:
        ai-config "pridej automatizaci pro svetla"
        ai-config --status
    """
    # Prepis modu pokud je zadan
    if mode:
        os.environ["AI_MODE"] = mode

    agent = AIAgent()

    if status:
        agent.show_status()
        return

    if not request:
        console.print("[yellow]Pouziti: ai-config \"popis zmeny\"[/yellow]")
        console.print("[dim]Nebo: ai-config --status[/dim]")
        return

    result = agent.process_request(request)

    if result.get("success"):
        console.print("\n[bold green]Hotovo![/bold green]")
    else:
        console.print(f"\n[bold red]Chyba: {result.get('error')}[/bold red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
