#!/usr/bin/env python3
"""
Energy Agent - FVE, baterie, spotřeba energie.
"""

import click
from typing import Any, Dict, List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .base_agent import BaseAgent

console = Console()


class EnergyAgent(BaseAgent):
    """Agent pro energetický management - FVE, baterie, spotřeba."""

    AGENT_NAME = "energy-agent"
    AGENT_DESCRIPTION = "FVE, baterie, spotřeba energie"

    SYSTEM_PROMPT = """Jsi expert na energetický management v Home Assistant. Pomáháš s:
- Konfigurací Energy Dashboardu
- FVE (fotovoltaické elektrárny) monitoring
- Správou baterií
- Automatizacemi pro optimalizaci spotřeby
- Utility metery pro statistiky

ENERGY DASHBOARD KONFIGURACE:
Energy Dashboard se konfiguruje v UI, ale potřebuje správné senzory.

Požadované senzory pro Energy Dashboard:
- Grid consumption (import ze sítě): device_class: energy, state_class: total_increasing
- Grid production (export do sítě): device_class: energy, state_class: total_increasing
- Solar production: device_class: energy, state_class: total_increasing
- Battery charge/discharge: device_class: energy, state_class: total_increasing

```yaml
# FILE: configuration.yaml
template:
  - sensor:
      # Výroba FVE - power (W)
      - name: "FVE Výkon"
        unique_id: pv_power
        unit_of_measurement: "W"
        device_class: power
        state_class: measurement
        state: "{{ states('sensor.inverter_power') | float(0) }}"

      # Výroba FVE - energie (kWh) pro Energy Dashboard
      - name: "FVE Energie Celkem"
        unique_id: pv_energy_total
        unit_of_measurement: "kWh"
        device_class: energy
        state_class: total_increasing
        state: "{{ states('sensor.inverter_energy_total') | float(0) }}"

      # Baterie SOC
      - name: "Baterie SOC"
        unique_id: battery_soc
        unit_of_measurement: "%"
        device_class: battery
        state_class: measurement
        state: "{{ states('sensor.battery_state_of_charge') | float(0) }}"

      # Baterie nabíjení
      - name: "Baterie Nabíjení"
        unique_id: battery_charging
        unit_of_measurement: "kWh"
        device_class: energy
        state_class: total_increasing
        state: "{{ states('sensor.battery_charge_total') | float(0) }}"

      # Baterie vybíjení
      - name: "Baterie Vybíjení"
        unique_id: battery_discharging
        unit_of_measurement: "kWh"
        device_class: energy
        state_class: total_increasing
        state: "{{ states('sensor.battery_discharge_total') | float(0) }}"

      # Spotřeba domu
      - name: "Spotřeba Domu"
        unique_id: house_consumption
        unit_of_measurement: "W"
        device_class: power
        state_class: measurement
        state: >
          {{ (states('sensor.grid_import_power') | float(0)
              + states('sensor.pv_power') | float(0)
              + states('sensor.battery_power') | float(0)
              - states('sensor.grid_export_power') | float(0)) | round(0) }}
```

UTILITY METER PRO STATISTIKY:
```yaml
# FILE: configuration.yaml
utility_meter:
  # Denní statistiky
  pv_energy_daily:
    source: sensor.pv_energy_total
    name: "FVE Denní výroba"
    cycle: daily

  grid_import_daily:
    source: sensor.grid_import_total
    name: "Denní odběr ze sítě"
    cycle: daily

  grid_export_daily:
    source: sensor.grid_export_total
    name: "Denní dodávka do sítě"
    cycle: daily

  # Měsíční statistiky
  pv_energy_monthly:
    source: sensor.pv_energy_total
    name: "FVE Měsíční výroba"
    cycle: monthly

  # Roční s tarify
  grid_import_yearly:
    source: sensor.grid_import_total
    name: "Roční odběr"
    cycle: yearly
    tariffs:
      - peak      # VT
      - offpeak   # NT
```

AUTOMATIZACE PRO ENERGII:

1. Přebytek FVE → zapni bojler:
```yaml
# FILE: automations.yaml
- id: solar_surplus_boiler
  alias: "Přebytek FVE - zapni bojler"
  description: "Když FVE vyrábí víc než spotřeba, zapni bojler"
  triggers:
    - trigger: numeric_state
      entity_id: sensor.grid_export_power
      above: 1000
      for:
        minutes: 5
  conditions:
    - condition: state
      entity_id: switch.boiler
      state: "off"
    - condition: numeric_state
      entity_id: sensor.boiler_temperature
      below: 55
  actions:
    - action: switch.turn_on
      target:
        entity_id: switch.boiler
```

2. Baterie > 90% → zapni spotřebiče:
```yaml
- id: battery_high_soc
  alias: "Vysoký SOC baterie - zapni spotřebiče"
  triggers:
    - trigger: numeric_state
      entity_id: sensor.battery_soc
      above: 90
  conditions:
    - condition: sun
      after: sunrise
      before: sunset
  actions:
    - action: switch.turn_on
      target:
        entity_id:
          - switch.pool_pump
          - switch.ev_charger
```

3. Nízký SOC baterie → vypni neesenciální:
```yaml
- id: battery_low_soc
  alias: "Nízký SOC baterie - úsporný režim"
  triggers:
    - trigger: numeric_state
      entity_id: sensor.battery_soc
      below: 20
  actions:
    - action: switch.turn_off
      target:
        entity_id:
          - switch.pool_pump
          - switch.ev_charger
    - action: climate.set_temperature
      target:
        entity_id: climate.thermostat
      data:
        temperature: 19
    - action: notify.mobile_app
      data:
        title: "Nízká baterie"
        message: "SOC baterie: {{ states('sensor.battery_soc') }}%"
```

4. Noční tarif - nabíjení baterie:
```yaml
- id: night_tariff_charge
  alias: "Noční tarif - nabíjení baterie"
  triggers:
    - trigger: time
      at: "22:00:00"
  conditions:
    - condition: numeric_state
      entity_id: sensor.battery_soc
      below: 50
  actions:
    - action: number.set_value
      target:
        entity_id: number.battery_charge_limit
      data:
        value: 80
```

INTEGRACE S BĚŽNÝMI STŘÍDAČI:

Fronius:
```yaml
sensor:
  - platform: fronius
    host: 192.168.1.100
    monitored_conditions:
      - power_ac
      - energy_total
```

SolarEdge:
```yaml
solaredge:
  api_key: YOUR_API_KEY
  site_id: YOUR_SITE_ID
```

Huawei/FusionSolar:
Použij HACS integraci fusion_solar

GoodWe:
Použij HACS integraci goodwe

DOPORUČENÍ:
1. Vždy používej state_class: total_increasing pro energie
2. Pro power používej state_class: measurement
3. Přidávej device_class pro správné zobrazení v UI
4. Používej Riemann sum pro převod power → energy pokud chybí
5. Nastavuj availability pro robustnost
"""

    def build_context(self) -> str:
        """Sestavení kontextu s energetickými senzory."""
        context_parts = []

        # Hledej energetické senzory
        sensors = self.get_entities("sensor")

        energy_keywords = ["energy", "power", "solar", "pv", "battery", "soc",
                          "grid", "consumption", "production", "inverter",
                          "kwh", "watt", "voltage", "current"]

        energy_sensors = [
            s for s in sensors
            if any(kw in s.get("entity_id", "").lower() for kw in energy_keywords)
            or s.get("attributes", {}).get("device_class") in ["energy", "power", "battery"]
        ]

        context_parts.append(f"ENERGETICKÉ SENZORY ({len(energy_sensors)}):")
        for sensor in energy_sensors[:40]:
            entity_id = sensor.get("entity_id", "")
            state = sensor.get("state", "")
            unit = sensor.get("attributes", {}).get("unit_of_measurement", "")
            device_class = sensor.get("attributes", {}).get("device_class", "")
            context_parts.append(f"  - {entity_id}: {state} {unit} (class: {device_class})")

        # Utility metery
        utility_meters = [s for s in sensors if "utility" in s.get("entity_id", "").lower()]
        if utility_meters:
            context_parts.append(f"\nUTILITY METERY ({len(utility_meters)}):")
            context_parts.append(self.format_entities_for_context(utility_meters, limit=10))

        # Přepínače pro spotřebiče
        switches = self.get_entities("switch")
        context_parts.append(f"\nPŘEPÍNAČE ({len(switches)}):")
        context_parts.append(self.format_entities_for_context(switches, limit=20))

        return "\n".join(context_parts)

    def process(self, user_request: str) -> Dict[str, Any]:
        """Zpracování požadavku na energii."""
        console.print(f"[bold blue]Generuji energetickou konfiguraci...[/bold blue]")
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
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    def get_energy_stats(self) -> Dict[str, Any]:
        """Získání aktuálních energetických statistik."""
        stats = {}

        sensors = self.get_entities("sensor")

        # Hledej známé senzory
        for sensor in sensors:
            entity_id = sensor.get("entity_id", "")
            state = sensor.get("state", "")
            unit = sensor.get("attributes", {}).get("unit_of_measurement", "")

            if "pv" in entity_id.lower() or "solar" in entity_id.lower():
                if "power" in entity_id.lower():
                    stats["pv_power"] = f"{state} {unit}"
                elif "energy" in entity_id.lower() and "daily" in entity_id.lower():
                    stats["pv_energy_daily"] = f"{state} {unit}"

            if "battery" in entity_id.lower() and "soc" in entity_id.lower():
                stats["battery_soc"] = f"{state} {unit}"

            if "grid" in entity_id.lower():
                if "import" in entity_id.lower() and "power" in entity_id.lower():
                    stats["grid_import"] = f"{state} {unit}"
                if "export" in entity_id.lower() and "power" in entity_id.lower():
                    stats["grid_export"] = f"{state} {unit}"

        return stats


# CLI Interface
@click.group()
def cli():
    """Energy Agent - energetický management."""
    pass


@cli.command()
@click.argument("request")
@click.option("--mode", type=click.Choice(["read_only", "dry_run", "apply"]), help="Mód")
def create(request: str, mode: Optional[str]):
    """Vytvoření energetické konfigurace."""
    import os
    import sys
    sys.path.insert(0, "/app")

    if mode:
        os.environ["AI_MODE"] = mode

    from ha_interface import HAInterface
    from claude_client import ClaudeClient

    agent = EnergyAgent(
        ha_interface=HAInterface(),
        claude_client=ClaudeClient(),
    )

    result = agent.process(request)
    agent.show_result(result)


@cli.command()
def status():
    """Aktuální energetické statistiky."""
    import sys
    sys.path.insert(0, "/app")

    from ha_interface import HAInterface

    agent = EnergyAgent(ha_interface=HAInterface())
    stats = agent.get_energy_stats()

    if not stats:
        console.print("[yellow]Žádné energetické senzory nenalezeny[/yellow]")
        return

    panel_content = ""
    for key, value in stats.items():
        panel_content += f"[bold]{key}:[/bold] {value}\n"

    console.print(Panel(panel_content, title="Energetické statistiky", border_style="green"))


@cli.command()
def sensors():
    """Seznam energetických senzorů."""
    import sys
    sys.path.insert(0, "/app")

    from ha_interface import HAInterface

    agent = EnergyAgent(ha_interface=HAInterface())
    all_sensors = agent.get_entities("sensor")

    energy_keywords = ["energy", "power", "solar", "pv", "battery", "soc",
                      "grid", "consumption", "production", "inverter"]

    energy_sensors = [
        s for s in all_sensors
        if any(kw in s.get("entity_id", "").lower() for kw in energy_keywords)
        or s.get("attributes", {}).get("device_class") in ["energy", "power", "battery"]
    ]

    table = Table(title=f"Energetické senzory ({len(energy_sensors)})")
    table.add_column("Entity ID", style="cyan")
    table.add_column("Stav", style="green")
    table.add_column("Jednotka", style="yellow")
    table.add_column("Device Class", style="magenta")

    for sensor in energy_sensors:
        table.add_row(
            sensor.get("entity_id", ""),
            str(sensor.get("state", "")),
            sensor.get("attributes", {}).get("unit_of_measurement", ""),
            sensor.get("attributes", {}).get("device_class", ""),
        )

    console.print(table)


@cli.command()
def setup():
    """Interaktivní průvodce nastavením Energy Dashboardu."""
    import sys
    sys.path.insert(0, "/app")

    from ha_interface import HAInterface
    from claude_client import ClaudeClient

    agent = EnergyAgent(
        ha_interface=HAInterface(),
        claude_client=ClaudeClient(),
    )

    request = """Analyzuj dostupné energetické senzory a navrhni:
1. Které senzory použít pro Energy Dashboard
2. Jaké template senzory případně vytvořit
3. Jaké utility metery přidat pro denní/měsíční statistiky
4. Základní automatizace pro optimalizaci spotřeby"""

    result = agent.process(request)
    agent.show_result(result)


if __name__ == "__main__":
    cli()
