#!/usr/bin/env python3
"""
Automation Agent - vytváření a správa HA automatizací.
"""

import click
from typing import Any, Dict, List, Optional
from pathlib import Path
from rich.console import Console
from rich.table import Table

from .base_agent import BaseAgent

console = Console()


class AutomationAgent(BaseAgent):
    """Agent pro vytváření Home Assistant automatizací."""

    AGENT_NAME = "automation-agent"
    AGENT_DESCRIPTION = "Vytváření a správa automatizací"

    SYSTEM_PROMPT = """Jsi expert na Home Assistant automatizace. Tvým úkolem je vytvářet YAML konfigurace pro automatizace.

PRAVIDLA:
1. VŽDY generuj validní YAML pro automations.yaml
2. Používej POUZE entity_id které existují v systému (viz kontext)
3. Každá automatizace MUSÍ mít unikátní id, alias a description
4. Preferuj novou syntaxi (triggers/conditions/actions místo trigger/condition/action)
5. Přidávej smysluplné komentáře

DOSTUPNÉ TRIGGERY:
- state: Změna stavu entity (from, to, for)
- numeric_state: Číselná hodnota (above, below)
- time: Konkrétní čas (at: "07:00:00")
- time_pattern: Vzor (hours, minutes, seconds - /5 = každých 5)
- sun: Východ/západ (event: sunrise/sunset, offset)
- zone: Vstup/výstup ze zóny (entity_id, zone, event: enter/leave)
- device: Událost zařízení (device_id, type, subtype)
- mqtt: MQTT zpráva (topic, payload)
- webhook: HTTP webhook (webhook_id)
- event: HA událost (event_type, event_data)
- template: Šablona je true (value_template)
- calendar: Kalendářní událost (entity_id, event: start/end)
- tag: NFC tag (tag_id)

DOSTUPNÉ CONDITIONS:
- state: entity_id, state
- numeric_state: entity_id, above, below
- time: after, before, weekday
- sun: after/before sunrise/sunset
- zone: entity_id, zone
- template: value_template
- and/or/not: conditions (seznam)

DOSTUPNÉ ACTIONS:
- action: domain.service (data, target)
- delay: hours, minutes, seconds
- wait_template: value_template, timeout
- wait_for_trigger: triggers
- choose: conditions + sequence
- repeat: count/while/until + sequence
- if/then/else: podmíněné akce
- variables: nastavení proměnných
- stop: zastavení
- parallel: paralelní akce
- event: vyvolání události

FORMÁT VÝSTUPU:
```yaml
# FILE: automations.yaml
- id: 'unique_automation_id'
  alias: "Popisný název automatizace"
  description: "Detailní popis co automatizace dělá"
  mode: single  # single, restart, queued, parallel
  triggers:
    - trigger: state
      entity_id: sensor.example
      to: "on"
  conditions:
    - condition: time
      after: "06:00:00"
      before: "22:00:00"
  actions:
    - action: light.turn_on
      target:
        entity_id: light.example
      data:
        brightness_pct: 100
```

PŘÍKLADY BĚŽNÝCH AUTOMATIZACÍ:

1. Světla při západu slunce:
```yaml
- id: 'lights_at_sunset'
  alias: "Rozsvícení světel při západu slunce"
  triggers:
    - trigger: sun
      event: sunset
      offset: "-00:30:00"
  conditions:
    - condition: state
      entity_id: binary_sensor.someone_home
      state: "on"
  actions:
    - action: light.turn_on
      target:
        entity_id: light.living_room
```

2. Termostat podle přítomnosti:
```yaml
- id: 'thermostat_presence'
  alias: "Topení podle přítomnosti"
  triggers:
    - trigger: state
      entity_id: binary_sensor.someone_home
  actions:
    - choose:
        - conditions:
            - condition: state
              entity_id: binary_sensor.someone_home
              state: "on"
          sequence:
            - action: climate.set_temperature
              target:
                entity_id: climate.thermostat
              data:
                temperature: 22
        - conditions:
            - condition: state
              entity_id: binary_sensor.someone_home
              state: "off"
          sequence:
            - action: climate.set_temperature
              target:
                entity_id: climate.thermostat
              data:
                temperature: 18
```

3. Notifikace při nízké baterii:
```yaml
- id: 'low_battery_notification'
  alias: "Upozornění na nízkou baterii"
  triggers:
    - trigger: numeric_state
      entity_id: sensor.phone_battery
      below: 20
  conditions:
    - condition: state
      entity_id: device_tracker.phone
      state: "home"
  actions:
    - action: notify.mobile_app
      data:
        title: "Nízká baterie"
        message: "Baterie telefonu je na {{ states('sensor.phone_battery') }}%"
```
"""

    def build_context(self) -> str:
        """Sestavení kontextu s entitami a existujícími automatizacemi."""
        context_parts = []

        # Aktuální mód
        context_parts.append(f"AKTUÁLNÍ MÓD: {self.mode}")

        # Entity podle domén
        domains = ["light", "switch", "sensor", "binary_sensor", "climate",
                   "cover", "fan", "lock", "media_player", "person", "zone",
                   "input_boolean", "input_number", "input_select", "automation"]

        context_parts.append("\nDOSTUPNÉ ENTITY:")
        for domain in domains:
            entities = self.get_entities(domain)
            if entities:
                context_parts.append(f"\n{domain.upper()}:")
                context_parts.append(self.format_entities_for_context(entities, limit=20))

        # Existující automatizace
        automations_yaml = self.read_yaml_file("automations.yaml")
        if automations_yaml:
            # Jen prvních 2000 znaků pro kontext
            context_parts.append(f"\nEXISTUJÍCÍ AUTOMATIZACE (ukázka):\n{automations_yaml[:2000]}")

        return "\n".join(context_parts)

    def process(self, user_request: str) -> Dict[str, Any]:
        """Zpracování požadavku na automatizaci."""
        console.print(f"[bold blue]Generuji automatizaci...[/bold blue]")
        console.print(f"[dim]Mód: {self.mode}[/dim]\n")

        try:
            response = self.call_ai(user_request)
            files = self.extract_yaml_from_response(response)

            if not files:
                # Žádné YAML - jen textová odpověď
                return {
                    "success": True,
                    "response": response,
                    "yaml": None,
                    "files": [],
                }

            # Máme YAML
            yaml_content = files.get("automations.yaml", list(files.values())[0] if files else "")

            return {
                "success": True,
                "response": response,
                "yaml": yaml_content,
                "files": list(files.keys()),
                "target_file": "automations.yaml",
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    def list_automations(self) -> List[Dict]:
        """Seznam existujících automatizací."""
        if not self.ha:
            return []

        try:
            entities = self.get_entities("automation")
            return [
                {
                    "entity_id": e.get("entity_id"),
                    "state": e.get("state"),
                    "friendly_name": e.get("attributes", {}).get("friendly_name"),
                    "last_triggered": e.get("attributes", {}).get("last_triggered"),
                }
                for e in entities
            ]
        except Exception:
            return []

    def toggle_automation(self, entity_id: str, enable: bool) -> bool:
        """Zapnutí/vypnutí automatizace."""
        if not self.ha:
            return False

        try:
            service = "turn_on" if enable else "turn_off"
            self.ha.call_service("automation", service, {"entity_id": entity_id})
            return True
        except Exception:
            return False

    def trigger_automation(self, entity_id: str) -> bool:
        """Ruční spuštění automatizace."""
        if not self.ha:
            return False

        try:
            self.ha.call_service("automation", "trigger", {"entity_id": entity_id})
            return True
        except Exception:
            return False


# CLI Interface
@click.group()
def cli():
    """Automation Agent - správa HA automatizací."""
    pass


@cli.command()
@click.argument("request")
@click.option("--mode", type=click.Choice(["read_only", "dry_run", "apply"]), help="Mód")
def create(request: str, mode: Optional[str]):
    """Vytvoření nové automatizace."""
    import os
    import sys
    sys.path.insert(0, "/app")

    if mode:
        os.environ["AI_MODE"] = mode

    from ha_interface import HAInterface
    from claude_client import ClaudeClient

    agent = AutomationAgent(
        ha_interface=HAInterface(),
        claude_client=ClaudeClient(),
    )

    result = agent.process(request)
    agent.show_result(result)


@cli.command("list")
def list_cmd():
    """Seznam automatizací."""
    import sys
    sys.path.insert(0, "/app")

    from ha_interface import HAInterface

    agent = AutomationAgent(ha_interface=HAInterface())
    automations = agent.list_automations()

    table = Table(title="Automatizace")
    table.add_column("Entity ID", style="cyan")
    table.add_column("Název", style="white")
    table.add_column("Stav", style="green")
    table.add_column("Poslední spuštění", style="dim")

    for auto in automations:
        table.add_row(
            auto["entity_id"],
            auto.get("friendly_name", ""),
            auto["state"],
            auto.get("last_triggered", "")[:19] if auto.get("last_triggered") else "",
        )

    console.print(table)


@cli.command()
@click.argument("entity_id")
def enable(entity_id: str):
    """Zapnutí automatizace."""
    import sys
    sys.path.insert(0, "/app")

    from ha_interface import HAInterface

    agent = AutomationAgent(ha_interface=HAInterface())
    if agent.toggle_automation(entity_id, True):
        console.print(f"[green]Automatizace {entity_id} zapnuta[/green]")
    else:
        console.print(f"[red]Chyba při zapínání {entity_id}[/red]")


@cli.command()
@click.argument("entity_id")
def disable(entity_id: str):
    """Vypnutí automatizace."""
    import sys
    sys.path.insert(0, "/app")

    from ha_interface import HAInterface

    agent = AutomationAgent(ha_interface=HAInterface())
    if agent.toggle_automation(entity_id, False):
        console.print(f"[yellow]Automatizace {entity_id} vypnuta[/yellow]")
    else:
        console.print(f"[red]Chyba při vypínání {entity_id}[/red]")


@cli.command()
@click.argument("entity_id")
def trigger(entity_id: str):
    """Ruční spuštění automatizace."""
    import sys
    sys.path.insert(0, "/app")

    from ha_interface import HAInterface

    agent = AutomationAgent(ha_interface=HAInterface())
    if agent.trigger_automation(entity_id):
        console.print(f"[green]Automatizace {entity_id} spuštěna[/green]")
    else:
        console.print(f"[red]Chyba při spouštění {entity_id}[/red]")


if __name__ == "__main__":
    cli()
