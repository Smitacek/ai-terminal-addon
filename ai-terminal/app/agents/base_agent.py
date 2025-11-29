#!/usr/bin/env python3
"""
Base Agent - základ pro všechny HA agenty.
"""

import os
import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional
from rich.console import Console
from rich.panel import Panel

console = Console()


class BaseAgent(ABC):
    """Základní třída pro všechny AI agenty."""

    # Přepsat v podtřídách
    AGENT_NAME = "base"
    AGENT_DESCRIPTION = "Základní agent"
    SYSTEM_PROMPT = ""

    def __init__(self, ha_interface=None, claude_client=None):
        """
        Inicializace agenta.

        Args:
            ha_interface: Instance HAInterface pro komunikaci s HA
            claude_client: Instance ClaudeClient pro AI
        """
        self.ha = ha_interface
        self.claude = claude_client
        self.config_dir = Path("/config")
        self.mode = os.environ.get("AI_MODE", "dry_run")
        self.allowed_files = self._get_allowed_files()

    def _get_allowed_files(self) -> List[str]:
        """Získání seznamu povolených souborů."""
        files_str = os.environ.get("ALLOWED_FILES", "")
        if not files_str:
            return [
                "automations.yaml",
                "scripts.yaml",
                "scenes.yaml",
                "sensors.yaml",
                "binary_sensors.yaml",
                "switches.yaml",
                "groups.yaml",
                "input_booleans.yaml",
                "input_numbers.yaml",
                "input_selects.yaml",
                "input_texts.yaml",
                "input_datetimes.yaml",
            ]
        return [f.strip() for f in files_str.split(",") if f.strip()]

    def read_yaml_file(self, filename: str) -> str:
        """Přečtení YAML souboru."""
        filepath = self.config_dir / filename
        if filepath.exists():
            return filepath.read_text(encoding="utf-8")
        return ""

    def get_entities(self, domain: Optional[str] = None) -> List[Dict]:
        """Získání entit z HA."""
        if not self.ha:
            return []
        try:
            entities = self.ha.get_entities()
            if domain:
                entities = [e for e in entities if e.get("entity_id", "").startswith(f"{domain}.")]
            return entities
        except Exception:
            return []

    def format_entities_for_context(self, entities: List[Dict], limit: int = 50) -> str:
        """Formátování entit pro kontext AI."""
        if not entities:
            return "Žádné entity nenalezeny."

        lines = []
        for entity in entities[:limit]:
            entity_id = entity.get("entity_id", "")
            state = entity.get("state", "")
            name = entity.get("attributes", {}).get("friendly_name", "")
            lines.append(f"- {entity_id}: {state} ({name})")

        if len(entities) > limit:
            lines.append(f"... a dalších {len(entities) - limit} entit")

        return "\n".join(lines)

    def build_context(self) -> str:
        """Sestavení kontextu pro AI. Přepsat v podtřídách."""
        return ""

    def get_full_prompt(self, user_request: str) -> tuple:
        """Sestavení kompletního promptu."""
        context = self.build_context()
        system_prompt = self.SYSTEM_PROMPT

        if context:
            system_prompt += f"\n\n--- KONTEXT ---\n{context}"

        return system_prompt, user_request

    @abstractmethod
    def process(self, user_request: str) -> Dict[str, Any]:
        """
        Zpracování požadavku. Implementovat v podtřídách.

        Args:
            user_request: Požadavek od uživatele

        Returns:
            Dict s výsledkem (success, response, files, ...)
        """
        pass

    def call_ai(self, user_request: str) -> str:
        """Volání AI s kontextem."""
        if not self.claude:
            raise RuntimeError("Claude client není dostupný.")

        system_prompt, user_msg = self.get_full_prompt(user_request)

        return self.claude.chat(
            system_prompt=system_prompt,
            user_message=user_msg,
        )

    def show_result(self, result: Dict[str, Any]):
        """Zobrazení výsledku."""
        if result.get("success"):
            if result.get("yaml"):
                from rich.syntax import Syntax
                syntax = Syntax(result["yaml"], "yaml", theme="monokai", line_numbers=True)
                console.print(Panel(syntax, title="Vygenerovaný YAML", border_style="green"))

            if result.get("response"):
                console.print(Panel(result["response"], title=self.AGENT_NAME, border_style="cyan"))

            if result.get("files"):
                console.print(f"\n[green]Soubory: {', '.join(result['files'])}[/green]")
        else:
            console.print(f"[red]Chyba: {result.get('error', 'Neznámá chyba')}[/red]")

    def extract_yaml_from_response(self, response: str) -> Dict[str, str]:
        """Extrakce YAML bloků z odpovědi AI."""
        files = {}
        current_file = None
        current_content = []
        in_yaml = False

        for line in response.split("\n"):
            # Detekce FILE: komentáře
            if line.strip().startswith("# FILE:"):
                if current_file and current_content:
                    files[current_file] = "\n".join(current_content)
                current_file = line.replace("# FILE:", "").strip().split()[0]
                current_content = []
                in_yaml = True
            # Detekce yaml code blocku
            elif line.strip().startswith("```yaml"):
                in_yaml = True
            elif line.strip() == "```" and in_yaml:
                if current_file and current_content:
                    files[current_file] = "\n".join(current_content)
                current_file = None
                current_content = []
                in_yaml = False
            elif in_yaml:
                current_content.append(line)

        # Poslední soubor
        if current_file and current_content:
            files[current_file] = "\n".join(current_content)

        return files
