#!/usr/bin/env python3
"""
Script Agent - vytváření skriptů a scén.
"""

import click
from typing import Any, Dict, List, Optional
from rich.console import Console
from rich.table import Table

from .base_agent import BaseAgent

console = Console()


class ScriptAgent(BaseAgent):
    """Agent pro vytváření skriptů a scén."""

    AGENT_NAME = "script-agent"
    AGENT_DESCRIPTION = "Vytváření skriptů a scén"

    SYSTEM_PROMPT = """Jsi expert na Home Assistant skripty a scény. Tvým úkolem je vytvářet YAML konfigurace.

SKRIPTY (scripts.yaml):
Skripty jsou sekvence akcí které lze spustit ručně nebo z automatizací.

```yaml
# FILE: scripts.yaml
morning_routine:
  alias: "Ranní rutina"
  description: "Spustí ranní rutinu - rolety, světla, kávovar"
  icon: mdi:weather-sunny
  mode: single  # single, restart, queued, parallel
  fields:
    brightness:
      description: "Jas světel v %"
      default: 80
      selector:
        number:
          min: 0
          max: 100
  sequence:
    - action: cover.open_cover
      target:
        entity_id: cover.bedroom_blinds
    - delay:
        seconds: 5
    - action: light.turn_on
      target:
        entity_id: light.bedroom
      data:
        brightness_pct: "{{ brightness }}"
    - action: switch.turn_on
      target:
        entity_id: switch.coffee_maker
    - action: notify.mobile_app
      data:
        title: "Dobré ráno!"
        message: "Ranní rutina dokončena"

irrigation_zone:
  alias: "Zavlažování zóny"
  description: "Zavlažuje jednu zónu po zadanou dobu"
  fields:
    zone:
      description: "Entita zóny"
      required: true
      selector:
        entity:
          domain: switch
    duration:
      description: "Doba v minutách"
      default: 10
      selector:
        number:
          min: 1
          max: 60
  sequence:
    - action: switch.turn_on
      target:
        entity_id: "{{ zone }}"
    - delay:
        minutes: "{{ duration }}"
    - action: switch.turn_off
      target:
        entity_id: "{{ zone }}"
```

SCÉNY (scenes.yaml):
Scény ukládají stavy více entit pro rychlou aktivaci.

```yaml
# FILE: scenes.yaml
- id: movie_time
  name: "Film"
  icon: mdi:movie
  entities:
    light.living_room:
      state: on
      brightness: 50
      color_temp: 400
    light.tv_backlight:
      state: on
      brightness: 30
      rgb_color: [0, 0, 255]
    media_player.tv:
      state: on
    cover.living_room_blinds:
      state: closed

- id: good_night
  name: "Dobrou noc"
  icon: mdi:bed
  entities:
    light.all_lights:
      state: off
    cover.all_blinds:
      state: closed
    climate.thermostat:
      state: heat
      temperature: 19
    lock.front_door:
      state: locked
```

POKROČILÉ AKCE VE SKRIPTECH:

choose (if/else):
```yaml
sequence:
  - choose:
      - conditions:
          - condition: state
            entity_id: sun.sun
            state: below_horizon
        sequence:
          - action: light.turn_on
            target:
              entity_id: light.outdoor
    default:
      - action: light.turn_off
        target:
          entity_id: light.outdoor
```

repeat (smyčka):
```yaml
sequence:
  # Opakuj N-krát
  - repeat:
      count: 3
      sequence:
        - action: light.toggle
          target:
            entity_id: light.notification
        - delay:
            milliseconds: 500

  # Opakuj dokud není splněno
  - repeat:
      until:
        - condition: state
          entity_id: sensor.temperature
          state: "25"
      sequence:
        - action: climate.set_temperature
          data:
            temperature: 25
        - delay:
            minutes: 5
```

parallel (paralelní akce):
```yaml
sequence:
  - parallel:
      - action: light.turn_on
        target:
          entity_id: light.living_room
      - action: cover.open_cover
        target:
          entity_id: cover.blinds
      - action: media_player.turn_on
        target:
          entity_id: media_player.tv
```

wait_template:
```yaml
sequence:
  - action: climate.set_temperature
    data:
      temperature: 22
  - wait_template: "{{ states('sensor.temperature') | float >= 22 }}"
    timeout:
      minutes: 30
    continue_on_timeout: true
  - action: notify.mobile_app
    data:
      message: "Teplota dosažena!"
```

variables:
```yaml
sequence:
  - variables:
      target_temp: "{{ states('input_number.target_temp') | int }}"
      current_temp: "{{ states('sensor.temperature') | float }}"
  - action: notify.mobile_app
    data:
      message: "Cílová: {{ target_temp }}°C, Aktuální: {{ current_temp }}°C"
```

PRAVIDLA:
1. Každý skript musí mít alias a description
2. Používej fields pro parametrizované skripty
3. Přidej vhodnou icon (mdi:*)
4. Nastav správný mode podle použití
5. Pro scény ukládej jen změněné entity
"""

    def build_context(self) -> str:
        """Sestavení kontextu se skripty a scénami."""
        context_parts = []

        # Existující skripty
        scripts = self.get_entities("script")
        scenes = self.get_entities("scene")

        context_parts.append(f"EXISTUJÍCÍ SKRIPTY ({len(scripts)}):")
        context_parts.append(self.format_entities_for_context(scripts, limit=20))

        context_parts.append(f"\nEXISTUJÍCÍ SCÉNY ({len(scenes)}):")
        context_parts.append(self.format_entities_for_context(scenes, limit=20))

        # Entity pro použití ve skriptech
        for domain in ["light", "switch", "cover", "climate", "media_player", "lock", "fan"]:
            entities = self.get_entities(domain)
            if entities:
                context_parts.append(f"\n{domain.upper()} ({len(entities)}):")
                context_parts.append(self.format_entities_for_context(entities, limit=15))

        return "\n".join(context_parts)

    def process(self, user_request: str) -> Dict[str, Any]:
        """Zpracování požadavku na skript/scénu."""
        console.print(f"[bold blue]Generuji skript/scénu...[/bold blue]")
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
            target = "scripts.yaml" if "script" in list(files.keys())[0].lower() else "scenes.yaml"

            return {
                "success": True,
                "response": response,
                "yaml": yaml_content,
                "files": list(files.keys()),
                "target_file": target,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    def list_scripts(self) -> List[Dict]:
        """Seznam skriptů."""
        return self.get_entities("script")

    def list_scenes(self) -> List[Dict]:
        """Seznam scén."""
        return self.get_entities("scene")

    def run_script(self, entity_id: str, variables: Optional[Dict] = None) -> bool:
        """Spuštění skriptu."""
        if not self.ha:
            return False

        try:
            data = {"entity_id": entity_id}
            if variables:
                data["variables"] = variables
            self.ha.call_service("script", "turn_on", data)
            return True
        except Exception:
            return False

    def activate_scene(self, entity_id: str) -> bool:
        """Aktivace scény."""
        if not self.ha:
            return False

        try:
            self.ha.call_service("scene", "turn_on", {"entity_id": entity_id})
            return True
        except Exception:
            return False


# CLI Interface
@click.group()
def cli():
    """Script Agent - správa skriptů a scén."""
    pass


@cli.command()
@click.argument("request")
@click.option("--mode", type=click.Choice(["read_only", "dry_run", "apply"]), help="Mód")
def create(request: str, mode: Optional[str]):
    """Vytvoření nového skriptu nebo scény."""
    import os
    import sys
    sys.path.insert(0, "/app")

    if mode:
        os.environ["AI_MODE"] = mode

    from ha_interface import HAInterface
    from claude_client import ClaudeClient

    agent = ScriptAgent(
        ha_interface=HAInterface(),
        claude_client=ClaudeClient(),
    )

    result = agent.process(request)
    agent.show_result(result)


@cli.command("list")
@click.option("--type", "-t", "item_type", type=click.Choice(["scripts", "scenes", "all"]), default="all")
def list_cmd(item_type: str):
    """Seznam skriptů a scén."""
    import sys
    sys.path.insert(0, "/app")

    from ha_interface import HAInterface

    agent = ScriptAgent(ha_interface=HAInterface())

    if item_type in ["scripts", "all"]:
        scripts = agent.list_scripts()
        table = Table(title=f"Skripty ({len(scripts)})")
        table.add_column("Entity ID", style="cyan")
        table.add_column("Stav", style="green")
        table.add_column("Název", style="white")

        for script in scripts:
            table.add_row(
                script.get("entity_id", ""),
                script.get("state", ""),
                script.get("attributes", {}).get("friendly_name", ""),
            )
        console.print(table)

    if item_type in ["scenes", "all"]:
        scenes = agent.list_scenes()
        table = Table(title=f"Scény ({len(scenes)})")
        table.add_column("Entity ID", style="cyan")
        table.add_column("Název", style="white")

        for scene in scenes:
            table.add_row(
                scene.get("entity_id", ""),
                scene.get("attributes", {}).get("friendly_name", ""),
            )
        console.print(table)


@cli.command()
@click.argument("entity_id")
@click.option("--var", "-v", multiple=True, help="Proměnná ve formátu key=value")
def run(entity_id: str, var: tuple):
    """Spuštění skriptu."""
    import sys
    sys.path.insert(0, "/app")

    from ha_interface import HAInterface

    agent = ScriptAgent(ha_interface=HAInterface())

    variables = {}
    for v in var:
        if "=" in v:
            key, value = v.split("=", 1)
            variables[key] = value

    if agent.run_script(entity_id, variables if variables else None):
        console.print(f"[green]Skript {entity_id} spuštěn[/green]")
    else:
        console.print(f"[red]Chyba při spouštění {entity_id}[/red]")


@cli.command()
@click.argument("entity_id")
def activate(entity_id: str):
    """Aktivace scény."""
    import sys
    sys.path.insert(0, "/app")

    from ha_interface import HAInterface

    agent = ScriptAgent(ha_interface=HAInterface())

    if agent.activate_scene(entity_id):
        console.print(f"[green]Scéna {entity_id} aktivována[/green]")
    else:
        console.print(f"[red]Chyba při aktivaci {entity_id}[/red]")


if __name__ == "__main__":
    cli()
