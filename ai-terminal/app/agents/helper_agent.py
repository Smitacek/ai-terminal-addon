#!/usr/bin/env python3
"""
Helper Agent - input helpers, groups, timers.
"""

import click
from typing import Any, Dict, List, Optional
from rich.console import Console
from rich.table import Table

from .base_agent import BaseAgent

console = Console()


class HelperAgent(BaseAgent):
    """Agent pro vytváření pomocných entit - input helpers, groups, timers."""

    AGENT_NAME = "helper-agent"
    AGENT_DESCRIPTION = "Input helpers, groups, timers, counters"

    SYSTEM_PROMPT = """Jsi expert na Home Assistant pomocné entity. Tvým úkolem je vytvářet:
- Input helpers (boolean, number, select, text, datetime, button)
- Groups
- Timers
- Counters
- Schedules

INPUT_BOOLEAN (přepínač):
```yaml
# FILE: configuration.yaml
input_boolean:
  vacation_mode:
    name: "Režim dovolené"
    icon: mdi:airplane

  guest_mode:
    name: "Režim hostů"
    icon: mdi:account-multiple

  alarm_enabled:
    name: "Alarm zapnut"
    icon: mdi:shield-home
```

INPUT_NUMBER (číselná hodnota):
```yaml
# FILE: configuration.yaml
input_number:
  target_temperature:
    name: "Cílová teplota"
    min: 15
    max: 30
    step: 0.5
    unit_of_measurement: "°C"
    icon: mdi:thermometer
    mode: slider  # slider nebo box

  alarm_delay:
    name: "Zpoždění alarmu"
    min: 0
    max: 300
    step: 10
    unit_of_measurement: "s"
    icon: mdi:timer
```

INPUT_SELECT (výběr z možností):
```yaml
# FILE: configuration.yaml
input_select:
  house_mode:
    name: "Režim domu"
    options:
      - Doma
      - Pryč
      - Spánek
      - Dovolená
    icon: mdi:home

  hvac_mode:
    name: "Režim topení"
    options:
      - Auto
      - Manuální
      - Úsporný
      - Vypnuto
    icon: mdi:thermostat
```

INPUT_TEXT (textová hodnota):
```yaml
# FILE: configuration.yaml
input_text:
  notification_message:
    name: "Vlastní zpráva"
    min: 0
    max: 255
    pattern: "[a-zA-Z0-9 ]*"
    mode: text  # text nebo password

  guest_name:
    name: "Jméno hosta"
    min: 0
    max: 50
    icon: mdi:account
```

INPUT_DATETIME (datum a čas):
```yaml
# FILE: configuration.yaml
input_datetime:
  alarm_time:
    name: "Čas budíku"
    has_date: false
    has_time: true
    icon: mdi:alarm

  vacation_start:
    name: "Začátek dovolené"
    has_date: true
    has_time: false
    icon: mdi:calendar

  next_event:
    name: "Další událost"
    has_date: true
    has_time: true
    icon: mdi:calendar-clock
```

INPUT_BUTTON (tlačítko):
```yaml
# FILE: configuration.yaml
input_button:
  reset_counter:
    name: "Reset počítadla"
    icon: mdi:restart

  trigger_scene:
    name: "Spustit scénu"
    icon: mdi:play
```

TIMER:
```yaml
# FILE: configuration.yaml
timer:
  irrigation:
    name: "Zavlažování"
    duration: "00:30:00"
    icon: mdi:sprinkler
    restore: true

  laundry:
    name: "Pračka"
    duration: "01:30:00"
    icon: mdi:washing-machine
```

COUNTER:
```yaml
# FILE: configuration.yaml
counter:
  coffee_count:
    name: "Počet káv"
    initial: 0
    step: 1
    minimum: 0
    maximum: 100
    icon: mdi:coffee

  door_opens:
    name: "Otevření dveří"
    initial: 0
    step: 1
    icon: mdi:door
    restore: true
```

GROUP (skupina entit):
```yaml
# FILE: configuration.yaml
# Light group
light:
  - platform: group
    name: "Všechna světla obývák"
    unique_id: living_room_lights
    entities:
      - light.ceiling
      - light.lamp
      - light.tv_backlight

# Cover group
cover:
  - platform: group
    name: "Všechny rolety"
    unique_id: all_covers
    entities:
      - cover.living_room
      - cover.bedroom
      - cover.kitchen

# Generic group pro binary sensor
group:
  all_motion:
    name: "Všechny pohybové senzory"
    entities:
      - binary_sensor.motion_living_room
      - binary_sensor.motion_hallway
      - binary_sensor.motion_kitchen

  family:
    name: "Rodina"
    entities:
      - person.jan
      - person.petra
      - person.kids
```

SCHEDULE:
```yaml
# FILE: configuration.yaml
schedule:
  thermostat_schedule:
    name: "Rozvrh termostatu"
    monday:
      - from: "06:00:00"
        to: "08:00:00"
      - from: "17:00:00"
        to: "22:00:00"
    tuesday:
      - from: "06:00:00"
        to: "08:00:00"
      - from: "17:00:00"
        to: "22:00:00"
    # ... další dny
```

POUŽITÍ V AUTOMATIZACÍCH:

```yaml
# Trigger na input_boolean
triggers:
  - trigger: state
    entity_id: input_boolean.vacation_mode
    to: "on"

# Podmínka s input_select
conditions:
  - condition: state
    entity_id: input_select.house_mode
    state: "Doma"

# Akce s input_number
actions:
  - action: climate.set_temperature
    target:
      entity_id: climate.thermostat
    data:
      temperature: "{{ states('input_number.target_temperature') | float }}"

# Timer akce
actions:
  - action: timer.start
    target:
      entity_id: timer.irrigation
    data:
      duration: "00:15:00"
```

PRAVIDLA:
1. Vždy přidej name a icon
2. Pro input_number nastav smysluplné min/max/step
3. Pro input_select definuj všechny relevantní možnosti
4. Používej restore: true pro perzistenci po restartu
5. Skupiny pojmenuj logicky podle umístění/funkce
"""

    def build_context(self) -> str:
        """Sestavení kontextu s existujícími helpery."""
        context_parts = []

        helper_domains = [
            "input_boolean", "input_number", "input_select",
            "input_text", "input_datetime", "input_button",
            "timer", "counter", "group", "schedule"
        ]

        for domain in helper_domains:
            entities = self.get_entities(domain)
            if entities:
                context_parts.append(f"\n{domain.upper()} ({len(entities)}):")
                context_parts.append(self.format_entities_for_context(entities, limit=10))

        # Světla a další entity pro skupiny
        for domain in ["light", "switch", "cover", "binary_sensor", "person"]:
            entities = self.get_entities(domain)
            if entities:
                context_parts.append(f"\n{domain.upper()} (pro skupiny) ({len(entities)}):")
                context_parts.append(self.format_entities_for_context(entities, limit=15))

        return "\n".join(context_parts)

    def process(self, user_request: str) -> Dict[str, Any]:
        """Zpracování požadavku na helper."""
        console.print(f"[bold blue]Generuji helper...[/bold blue]")
        console.print(f"[dim]Mód: {self.mode}[/dim]\n")

        try:
            response = self.call_ai(user_request)
            files = self.extract_yaml_from_response(response)

            if not files:
                return {
                    "success": True,
                    "response": response,
                    "yaml": None,
                    "files": [],
                }

            yaml_content = list(files.values())[0] if files else ""

            return {
                "success": True,
                "response": response,
                "yaml": yaml_content,
                "files": list(files.keys()),
                "target_file": "configuration.yaml",
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    def list_helpers(self, helper_type: Optional[str] = None) -> Dict[str, List[Dict]]:
        """Seznam všech helper entit."""
        helper_domains = [
            "input_boolean", "input_number", "input_select",
            "input_text", "input_datetime", "input_button",
            "timer", "counter"
        ]

        if helper_type:
            helper_domains = [d for d in helper_domains if helper_type in d]

        result = {}
        for domain in helper_domains:
            entities = self.get_entities(domain)
            if entities:
                result[domain] = entities

        return result


# CLI Interface
@click.group()
def cli():
    """Helper Agent - input helpers a skupiny."""
    pass


@cli.command()
@click.argument("request")
@click.option("--mode", type=click.Choice(["read_only", "dry_run", "apply"]), help="Mód")
def create(request: str, mode: Optional[str]):
    """Vytvoření nového helperu."""
    import os
    import sys
    sys.path.insert(0, "/app")

    if mode:
        os.environ["AI_MODE"] = mode

    from ha_interface import HAInterface
    from claude_client import ClaudeClient

    agent = HelperAgent(
        ha_interface=HAInterface(),
        claude_client=ClaudeClient(),
    )

    result = agent.process(request)
    agent.show_result(result)


@cli.command("list")
@click.option("--type", "-t", "helper_type", help="Typ helperu (boolean, number, select...)")
def list_cmd(helper_type: Optional[str]):
    """Seznam helper entit."""
    import sys
    sys.path.insert(0, "/app")

    from ha_interface import HAInterface

    agent = HelperAgent(ha_interface=HAInterface())
    helpers = agent.list_helpers(helper_type)

    if not helpers:
        console.print("[yellow]Žádné helper entity nenalezeny[/yellow]")
        return

    for domain, entities in helpers.items():
        table = Table(title=f"{domain} ({len(entities)})")
        table.add_column("Entity ID", style="cyan")
        table.add_column("Stav", style="green")
        table.add_column("Název", style="white")

        for entity in entities:
            table.add_row(
                entity.get("entity_id", ""),
                str(entity.get("state", "")),
                entity.get("attributes", {}).get("friendly_name", ""),
            )

        console.print(table)
        console.print()


@cli.command()
@click.argument("name")
@click.option("--icon", "-i", default="mdi:toggle-switch", help="Ikona")
def boolean(name: str, icon: str):
    """Rychlé vytvoření input_boolean."""
    import sys
    sys.path.insert(0, "/app")

    from ha_interface import HAInterface
    from claude_client import ClaudeClient

    agent = HelperAgent(
        ha_interface=HAInterface(),
        claude_client=ClaudeClient(),
    )

    result = agent.process(f"Vytvoř input_boolean s názvem '{name}' a ikonou {icon}")
    agent.show_result(result)


@cli.command()
@click.argument("name")
@click.option("--min", "min_val", type=float, default=0, help="Minimum")
@click.option("--max", "max_val", type=float, default=100, help="Maximum")
@click.option("--step", type=float, default=1, help="Krok")
@click.option("--unit", "-u", default="", help="Jednotka")
def number(name: str, min_val: float, max_val: float, step: float, unit: str):
    """Rychlé vytvoření input_number."""
    import sys
    sys.path.insert(0, "/app")

    from ha_interface import HAInterface
    from claude_client import ClaudeClient

    agent = HelperAgent(
        ha_interface=HAInterface(),
        claude_client=ClaudeClient(),
    )

    request = f"Vytvoř input_number s názvem '{name}', rozsah {min_val}-{max_val}, krok {step}"
    if unit:
        request += f", jednotka {unit}"

    result = agent.process(request)
    agent.show_result(result)


@cli.command()
@click.argument("name")
@click.argument("options", nargs=-1)
def select(name: str, options: tuple):
    """Rychlé vytvoření input_select."""
    import sys
    sys.path.insert(0, "/app")

    from ha_interface import HAInterface
    from claude_client import ClaudeClient

    agent = HelperAgent(
        ha_interface=HAInterface(),
        claude_client=ClaudeClient(),
    )

    options_str = ", ".join(options)
    result = agent.process(f"Vytvoř input_select s názvem '{name}' a možnostmi: {options_str}")
    agent.show_result(result)


@cli.command()
@click.argument("name")
@click.argument("entities", nargs=-1)
def group(name: str, entities: tuple):
    """Rychlé vytvoření skupiny."""
    import sys
    sys.path.insert(0, "/app")

    from ha_interface import HAInterface
    from claude_client import ClaudeClient

    agent = HelperAgent(
        ha_interface=HAInterface(),
        claude_client=ClaudeClient(),
    )

    entities_str = ", ".join(entities)
    result = agent.process(f"Vytvoř skupinu s názvem '{name}' obsahující entity: {entities_str}")
    agent.show_result(result)


@cli.command()
@click.argument("name")
@click.option("--duration", "-d", default="00:30:00", help="Výchozí doba")
def timer(name: str, duration: str):
    """Rychlé vytvoření timeru."""
    import sys
    sys.path.insert(0, "/app")

    from ha_interface import HAInterface
    from claude_client import ClaudeClient

    agent = HelperAgent(
        ha_interface=HAInterface(),
        claude_client=ClaudeClient(),
    )

    result = agent.process(f"Vytvoř timer s názvem '{name}' a výchozí dobou {duration}")
    agent.show_result(result)


if __name__ == "__main__":
    cli()
