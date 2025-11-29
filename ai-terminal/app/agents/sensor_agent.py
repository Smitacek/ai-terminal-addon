#!/usr/bin/env python3
"""
Sensor Agent - vytváření template senzorů.
"""

import click
from typing import Any, Dict, List, Optional
from rich.console import Console
from rich.panel import Panel

from .base_agent import BaseAgent

console = Console()


class SensorAgent(BaseAgent):
    """Agent pro vytváření template a MQTT senzorů."""

    AGENT_NAME = "sensor-agent"
    AGENT_DESCRIPTION = "Vytváření template a MQTT senzorů"

    SYSTEM_PROMPT = """Jsi expert na Home Assistant senzory. Tvým úkolem je vytvářet YAML konfigurace pro:
- Template senzory
- Template binary senzory
- MQTT senzory
- Statistické senzory
- Utility metery

TEMPLATE SENSOR (nová syntaxe):
```yaml
# FILE: configuration.yaml
template:
  - sensor:
      - name: "Průměrná teplota"
        unique_id: avg_temperature
        unit_of_measurement: "°C"
        device_class: temperature
        state_class: measurement
        state: >
          {% set temps = [
            states('sensor.temp_living_room') | float(0),
            states('sensor.temp_bedroom') | float(0),
            states('sensor.temp_kitchen') | float(0)
          ] %}
          {{ (temps | sum / temps | count) | round(1) }}
        availability: >
          {{ states('sensor.temp_living_room') not in ['unknown', 'unavailable'] }}

  - binary_sensor:
      - name: "Někdo je doma"
        unique_id: someone_home
        device_class: presence
        state: >
          {{ is_state('person.jan', 'home') or is_state('person.petra', 'home') }}
```

MQTT SENSOR:
```yaml
# FILE: configuration.yaml
mqtt:
  sensor:
    - name: "Teplota Shelly"
      unique_id: shelly_temp
      state_topic: "shellies/shelly1/sensor/temperature"
      unit_of_measurement: "°C"
      device_class: temperature
      value_template: "{{ value_json.temperature }}"

  binary_sensor:
    - name: "Shelly tlačítko"
      unique_id: shelly_button
      state_topic: "shellies/shelly1/input/0"
      payload_on: "1"
      payload_off: "0"
      device_class: power
```

STATISTICS SENSOR:
```yaml
# FILE: configuration.yaml
sensor:
  - platform: statistics
    name: "Průměrná teplota 24h"
    unique_id: avg_temp_24h
    entity_id: sensor.temperature
    state_characteristic: mean
    max_age:
      hours: 24

  - platform: min_max
    name: "Min/Max teplota"
    unique_id: minmax_temp
    type: mean
    entity_ids:
      - sensor.temp_living_room
      - sensor.temp_bedroom
```

UTILITY METER:
```yaml
# FILE: configuration.yaml
utility_meter:
  daily_energy:
    source: sensor.energy_total
    name: "Denní spotřeba"
    cycle: daily

  monthly_energy:
    source: sensor.energy_total
    name: "Měsíční spotřeba"
    cycle: monthly

  yearly_energy:
    source: sensor.energy_total
    name: "Roční spotřeba"
    cycle: yearly
    tariffs:
      - peak
      - offpeak
```

HISTORY STATS:
```yaml
# FILE: configuration.yaml
sensor:
  - platform: history_stats
    name: "TV zapnutá dnes"
    unique_id: tv_on_today
    entity_id: media_player.tv
    state: "on"
    type: time
    start: "{{ today_at('00:00') }}"
    end: "{{ now() }}"
```

DEVICE CLASSES PRO SENSORY:
- temperature, humidity, pressure, illuminance
- power, energy, voltage, current
- battery, signal_strength
- co2, pm25, pm10, volatile_organic_compounds
- monetary, data_size, data_rate

DEVICE CLASSES PRO BINARY SENSORY:
- motion, occupancy, presence, door, window
- garage_door, lock, plug, power, light
- smoke, gas, moisture, problem, safety
- battery, connectivity, running, update

STATE CLASSES:
- measurement: průběžná hodnota (teplota)
- total: kumulativní hodnota která může klesnout (baterie)
- total_increasing: kumulativní hodnota která jen roste (energie)

JINJA2 ŠABLONY - UŽITEČNÉ FUNKCE:
- states('entity_id') - stav entity
- state_attr('entity_id', 'attribute') - atribut
- is_state('entity_id', 'state') - porovnání
- float(default), int(default) - konverze
- round(precision) - zaokrouhlení
- now(), today_at(), utcnow() - čas
- as_timestamp(), as_datetime() - konverze času
- relative_time(datetime) - relativní čas
- expand(group) - rozbalení skupiny
- area_entities('area'), device_entities('device') - entity podle oblasti/zařízení

PRAVIDLA:
1. Vždy přidej unique_id
2. Nastav správný device_class a state_class
3. Přidej unit_of_measurement kde je to relevantní
4. Používej availability template pro robustnost
5. Ošetři unknown/unavailable stavy v šablonách
"""

    def build_context(self) -> str:
        """Sestavení kontextu s existujícími senzory."""
        context_parts = []

        # Existující senzory
        sensors = self.get_entities("sensor")
        binary_sensors = self.get_entities("binary_sensor")

        context_parts.append(f"EXISTUJÍCÍ SENSORY ({len(sensors)}):")
        context_parts.append(self.format_entities_for_context(sensors, limit=30))

        context_parts.append(f"\nEXISTUJÍCÍ BINARY SENSORY ({len(binary_sensors)}):")
        context_parts.append(self.format_entities_for_context(binary_sensors, limit=20))

        # Další užitečné entity pro šablony
        for domain in ["person", "device_tracker", "climate", "weather"]:
            entities = self.get_entities(domain)
            if entities:
                context_parts.append(f"\n{domain.upper()} ({len(entities)}):")
                context_parts.append(self.format_entities_for_context(entities, limit=10))

        return "\n".join(context_parts)

    def process(self, user_request: str) -> Dict[str, Any]:
        """Zpracování požadavku na senzor."""
        console.print(f"[bold blue]Generuji senzor...[/bold blue]")
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


# CLI Interface
@click.group()
def cli():
    """Sensor Agent - vytváření senzorů."""
    pass


@cli.command()
@click.argument("request")
@click.option("--mode", type=click.Choice(["read_only", "dry_run", "apply"]), help="Mód")
def create(request: str, mode: Optional[str]):
    """Vytvoření nového senzoru."""
    import os
    import sys
    sys.path.insert(0, "/app")

    if mode:
        os.environ["AI_MODE"] = mode

    from ha_interface import HAInterface
    from claude_client import ClaudeClient

    agent = SensorAgent(
        ha_interface=HAInterface(),
        claude_client=ClaudeClient(),
    )

    result = agent.process(request)
    agent.show_result(result)


@cli.command("list")
@click.option("--domain", "-d", type=click.Choice(["sensor", "binary_sensor"]), default="sensor")
@click.option("--filter", "-f", "filter_str", help="Filtr")
def list_cmd(domain: str, filter_str: Optional[str]):
    """Seznam senzorů."""
    import sys
    sys.path.insert(0, "/app")

    from ha_interface import HAInterface
    from rich.table import Table

    agent = SensorAgent(ha_interface=HAInterface())
    entities = agent.get_entities(domain)

    if filter_str:
        filter_lower = filter_str.lower()
        entities = [e for e in entities if filter_lower in e.get("entity_id", "").lower()]

    table = Table(title=f"{domain} ({len(entities)})")
    table.add_column("Entity ID", style="cyan")
    table.add_column("Stav", style="green")
    table.add_column("Jednotka", style="yellow")
    table.add_column("Název", style="white")

    for entity in entities[:50]:
        table.add_row(
            entity.get("entity_id", ""),
            str(entity.get("state", "")),
            entity.get("attributes", {}).get("unit_of_measurement", ""),
            entity.get("attributes", {}).get("friendly_name", ""),
        )

    console.print(table)


@cli.command()
@click.argument("topic")
@click.option("--name", "-n", help="Název senzoru")
def mqtt(topic: str, name: Optional[str]):
    """Vytvoření MQTT senzoru z topicu."""
    import sys
    sys.path.insert(0, "/app")

    from ha_interface import HAInterface
    from claude_client import ClaudeClient

    request = f"Vytvoř MQTT senzor pro topic '{topic}'"
    if name:
        request += f" s názvem '{name}'"

    agent = SensorAgent(
        ha_interface=HAInterface(),
        claude_client=ClaudeClient(),
    )

    result = agent.process(request)
    agent.show_result(result)


@cli.command()
@click.argument("entities", nargs=-1)
@click.option("--operation", "-o", type=click.Choice(["avg", "sum", "min", "max"]), default="avg")
@click.option("--name", "-n", help="Název senzoru")
def combine(entities: tuple, operation: str, name: Optional[str]):
    """Vytvoření kombinovaného senzoru z více entit."""
    import sys
    sys.path.insert(0, "/app")

    from ha_interface import HAInterface
    from claude_client import ClaudeClient

    ops = {"avg": "průměr", "sum": "součet", "min": "minimum", "max": "maximum"}
    request = f"Vytvoř template senzor který počítá {ops[operation]} z entit: {', '.join(entities)}"
    if name:
        request += f" s názvem '{name}'"

    agent = SensorAgent(
        ha_interface=HAInterface(),
        claude_client=ClaudeClient(),
    )

    result = agent.process(request)
    agent.show_result(result)


if __name__ == "__main__":
    cli()
