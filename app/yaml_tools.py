#!/usr/bin/env python3
"""
YAML Tools pro AI Terminal.
Nastroje pro praci s YAML soubory - cteni, zapis, merge, diff.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Union
from ruamel.yaml import YAML
from deepdiff import DeepDiff
from rich.console import Console

console = Console()


class YAMLHandler:
    """Handler pro praci s YAML soubory s zachovanim formatu a komentaru."""

    def __init__(self):
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.yaml.default_flow_style = False
        self.yaml.indent(mapping=2, sequence=4, offset=2)

    def read_file(self, filepath: str) -> str:
        """Precteni YAML souboru jako text."""
        path = Path(filepath)
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def read_yaml(self, filepath: str) -> Any:
        """Precteni a parsovani YAML souboru."""
        path = Path(filepath)
        if not path.exists():
            return None

        with open(path, "r", encoding="utf-8") as f:
            return self.yaml.load(f)

    def write_file(self, filepath: str, content: str) -> None:
        """Zapis textu do souboru."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def write_yaml(self, filepath: str, data: Any) -> None:
        """Zapis YAML dat do souboru."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            self.yaml.dump(data, f)

    def parse_string(self, content: str) -> Any:
        """Parsovani YAML z retezce."""
        from io import StringIO
        return self.yaml.load(StringIO(content))

    def dump_string(self, data: Any) -> str:
        """Dump YAML dat do retezce."""
        from io import StringIO
        stream = StringIO()
        self.yaml.dump(data, stream)
        return stream.getvalue()

    def validate(self, content: str) -> tuple[bool, Optional[str]]:
        """
        Validace YAML syntaxe.

        Returns:
            Tuple (is_valid, error_message)
        """
        try:
            self.parse_string(content)
            return True, None
        except Exception as e:
            return False, str(e)

    def merge(self, base: Dict, update: Dict) -> Dict:
        """
        Rekurzivni merge dvou YAML struktur.

        Args:
            base: Zakladni struktura
            update: Aktualizace k aplikovani

        Returns:
            Zmergovana struktura
        """
        result = base.copy()

        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self.merge(result[key], value)
            else:
                result[key] = value

        return result

    def diff(self, old_content: str, new_content: str) -> Dict:
        """
        Porovnani dvou YAML obsahu.

        Returns:
            DeepDiff objekt s rozdily
        """
        old_data = self.parse_string(old_content) if old_content else {}
        new_data = self.parse_string(new_content) if new_content else {}

        return DeepDiff(old_data, new_data, ignore_order=True)

    def show_diff(self, old_content: str, new_content: str) -> None:
        """Zobrazeni rozlilu mezi dvema YAML obsahy."""
        diff = self.diff(old_content, new_content)

        if not diff:
            console.print("[green]Zadne zmeny[/green]")
            return

        console.print("\n[bold]Zmeny:[/bold]")

        if "values_changed" in diff:
            console.print("\n[yellow]Zmeneno:[/yellow]")
            for path, change in diff["values_changed"].items():
                console.print(f"  {path}:")
                console.print(f"    [red]- {change['old_value']}[/red]")
                console.print(f"    [green]+ {change['new_value']}[/green]")

        if "dictionary_item_added" in diff:
            console.print("\n[green]Pridano:[/green]")
            for item in diff["dictionary_item_added"]:
                console.print(f"  [green]+ {item}[/green]")

        if "dictionary_item_removed" in diff:
            console.print("\n[red]Odebrano:[/red]")
            for item in diff["dictionary_item_removed"]:
                console.print(f"  [red]- {item}[/red]")


class HomeAssistantYAML:
    """Specialni handler pro Home Assistant YAML struktury."""

    def __init__(self):
        self.handler = YAMLHandler()

    def add_automation(self, content: str, automation: Dict) -> str:
        """Pridani nove automatizace do automations.yaml."""
        data = self.handler.parse_string(content) or []

        if not isinstance(data, list):
            data = [data]

        # Kontrola duplicity (podle id nebo alias)
        auto_id = automation.get("id") or automation.get("alias")
        for existing in data:
            if existing.get("id") == auto_id or existing.get("alias") == auto_id:
                console.print(f"[yellow]Automatizace '{auto_id}' jiz existuje - aktualizuji[/yellow]")
                data.remove(existing)
                break

        data.append(automation)
        return self.handler.dump_string(data)

    def add_script(self, content: str, script_name: str, script: Dict) -> str:
        """Pridani noveho scriptu do scripts.yaml."""
        data = self.handler.parse_string(content) or {}

        if script_name in data:
            console.print(f"[yellow]Script '{script_name}' jiz existuje - aktualizuji[/yellow]")

        data[script_name] = script
        return self.handler.dump_string(data)

    def add_sensor(self, content: str, sensor: Dict) -> str:
        """Pridani noveho senzoru."""
        data = self.handler.parse_string(content) or []

        if not isinstance(data, list):
            data = [data]

        data.append(sensor)
        return self.handler.dump_string(data)

    def validate_automation(self, automation: Dict) -> tuple[bool, list]:
        """Validace struktury automatizace."""
        errors = []

        if "trigger" not in automation and "triggers" not in automation:
            errors.append("Chybi 'trigger' nebo 'triggers'")

        if "action" not in automation and "actions" not in automation:
            errors.append("Chybi 'action' nebo 'actions'")

        return len(errors) == 0, errors
