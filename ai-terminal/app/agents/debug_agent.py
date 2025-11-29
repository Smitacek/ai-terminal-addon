#!/usr/bin/env python3
"""
Debug Agent - diagnostika a řešení problémů.
"""

import click
import re
from typing import Any, Dict, List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax

from .base_agent import BaseAgent

console = Console()


class DebugAgent(BaseAgent):
    """Agent pro diagnostiku a řešení problémů v HA."""

    AGENT_NAME = "debug-agent"
    AGENT_DESCRIPTION = "Diagnostika a řešení problémů"

    SYSTEM_PROMPT = """Jsi expert na diagnostiku Home Assistant. Pomáháš s:
- Analýzou chybových hlášení
- Hledáním problémů v konfiguraci
- Vysvětlováním unavailable/unknown stavů
- Debugováním automatizací

BĚŽNÉ PROBLÉMY A ŘEŠENÍ:

1. Entity unavailable:
- Zkontroluj fyzické připojení zařízení
- Zkontroluj síťové připojení
- Restartuj integraci
- Zkontroluj logy pro konkrétní chybu

2. Automatizace se nespouští:
- Zkontroluj že je automatizace zapnutá (state: on)
- Ověř triggery - jsou podmínky splněny?
- Zkontroluj conditions - neblokují spuštění?
- Podívej se na trace v UI

3. Template nefunguje:
- Otestuj šablonu v Developer Tools → Template
- Zkontroluj syntaxi Jinja2
- Ověř že entity existují
- Ošetři unknown/unavailable stavy

4. YAML chyby:
- Zkontroluj odsazení (spaces, ne tabs)
- Ověř správné uvozovky
- Zkontroluj speciální znaky
- Validuj pomocí ha core check

5. Integrace nefunguje:
- Zkontroluj logy integrace
- Ověř credentials/API klíče
- Zkontroluj síťové připojení
- Zkus smazat a znovu přidat

DIAGNOSTICKÉ PŘÍKAZY:

Validace konfigurace:
```bash
ha core check
```

Logy:
```bash
ha core logs
ha core logs --filter <integration>
```

Restart služeb:
```bash
ha core restart
ha supervisor reload
```

ANALÝZA LOGŮ:
Při analýze logů hledej:
- ERROR a WARNING zprávy
- Stack traces
- Časové korelace s problémy
- Opakující se vzory

TRACE AUTOMATIZACE:
1. Jdi do Settings → Automations
2. Klikni na automatizaci
3. Klikni na "Traces"
4. Analyzuj jednotlivé kroky

TEMPLATE DEBUGGING:
```yaml
# Testovací template sensor pro debug
template:
  - sensor:
      - name: "Debug Test"
        state: >
          {% set value = states('sensor.test') %}
          {% if value in ['unknown', 'unavailable'] %}
            error
          {% else %}
            {{ value | float(0) }}
          {% endif %}
```

BĚŽNÉ CHYBY V YAML:

1. Špatné odsazení:
```yaml
# ŠPATNĚ
automation:
- alias: Test
  trigger:
  - platform: state

# SPRÁVNĚ
automation:
  - alias: Test
    trigger:
      - platform: state
```

2. Chybějící uvozovky:
```yaml
# ŠPATNĚ (speciální znaky)
alias: Test: automatizace

# SPRÁVNĚ
alias: "Test: automatizace"
```

3. Špatný formát času:
```yaml
# ŠPATNĚ
at: 7:00

# SPRÁVNĚ
at: "07:00:00"
```

Při odpovědi:
1. Identifikuj konkrétní problém
2. Vysvětli příčinu
3. Navrhni řešení krok za krokem
4. Uveď jak ověřit opravu
"""

    def build_context(self) -> str:
        """Sestavení kontextu pro debug."""
        context_parts = []

        # Problémové entity (unavailable, unknown)
        all_entities = self.get_entities()
        problem_entities = [
            e for e in all_entities
            if e.get("state") in ["unavailable", "unknown"]
        ]

        if problem_entities:
            context_parts.append(f"PROBLÉMOVÉ ENTITY ({len(problem_entities)}):")
            for entity in problem_entities[:30]:
                context_parts.append(f"  - {entity.get('entity_id')}: {entity.get('state')}")

        # Automatizace
        automations = self.get_entities("automation")
        disabled_automations = [a for a in automations if a.get("state") == "off"]

        if disabled_automations:
            context_parts.append(f"\nVYPNUTÉ AUTOMATIZACE ({len(disabled_automations)}):")
            for auto in disabled_automations:
                context_parts.append(f"  - {auto.get('entity_id')}")

        # Logy (pokud dostupné)
        if self.ha:
            try:
                logs = self.ha.get_logs(lines=50)
                # Filtruj ERROR a WARNING
                error_lines = [l for l in logs.split("\n") if "ERROR" in l or "WARNING" in l]
                if error_lines:
                    context_parts.append(f"\nPOSLEDNÍ CHYBY Z LOGŮ:")
                    context_parts.append("\n".join(error_lines[-20:]))
            except Exception:
                pass

        return "\n".join(context_parts)

    def process(self, user_request: str) -> Dict[str, Any]:
        """Zpracování diagnostického požadavku."""
        console.print(f"[bold blue]Analyzuji problém...[/bold blue]\n")

        try:
            response = self.call_ai(user_request)

            return {
                "success": True,
                "response": response,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    def check_config(self) -> Dict[str, Any]:
        """Kontrola konfigurace."""
        if not self.ha:
            return {"valid": False, "error": "HA interface není dostupný"}

        try:
            valid = self.ha.check_config()
            return {"valid": valid}
        except Exception as e:
            return {"valid": False, "error": str(e)}

    def get_problem_entities(self) -> List[Dict]:
        """Seznam problémových entit."""
        all_entities = self.get_entities()
        return [
            {
                "entity_id": e.get("entity_id"),
                "state": e.get("state"),
                "friendly_name": e.get("attributes", {}).get("friendly_name"),
                "last_changed": e.get("last_changed"),
            }
            for e in all_entities
            if e.get("state") in ["unavailable", "unknown"]
        ]

    def get_logs(self, lines: int = 100, filter_str: Optional[str] = None) -> str:
        """Získání logů."""
        if not self.ha:
            return "HA interface není dostupný"

        try:
            logs = self.ha.get_logs(lines=lines)
            if filter_str:
                logs = "\n".join(l for l in logs.split("\n") if filter_str.lower() in l.lower())
            return logs
        except Exception as e:
            return f"Chyba: {e}"

    def analyze_automation(self, entity_id: str) -> Dict[str, Any]:
        """Analýza automatizace."""
        entity = None
        for e in self.get_entities("automation"):
            if e.get("entity_id") == entity_id:
                entity = e
                break

        if not entity:
            return {"error": f"Automatizace {entity_id} nenalezena"}

        return {
            "entity_id": entity_id,
            "state": entity.get("state"),
            "friendly_name": entity.get("attributes", {}).get("friendly_name"),
            "last_triggered": entity.get("attributes", {}).get("last_triggered"),
            "mode": entity.get("attributes", {}).get("mode"),
            "current": entity.get("attributes", {}).get("current", 0),
        }


# CLI Interface
@click.group()
def cli():
    """Debug Agent - diagnostika HA."""
    pass


@cli.command()
@click.argument("request")
def analyze(request: str):
    """Analýza problému pomocí AI."""
    import sys
    sys.path.insert(0, "/app")

    from ha_interface import HAInterface
    from claude_client import ClaudeClient

    agent = DebugAgent(
        ha_interface=HAInterface(),
        claude_client=ClaudeClient(),
    )

    result = agent.process(request)
    agent.show_result(result)


@cli.command()
def config():
    """Kontrola konfigurace."""
    import sys
    sys.path.insert(0, "/app")

    from ha_interface import HAInterface

    agent = DebugAgent(ha_interface=HAInterface())
    result = agent.check_config()

    if result.get("valid"):
        console.print("[green]✓ Konfigurace je validní[/green]")
    else:
        console.print(f"[red]✗ Konfigurace obsahuje chyby[/red]")
        if result.get("error"):
            console.print(f"[red]{result['error']}[/red]")


@cli.command()
def problems():
    """Seznam problémových entit."""
    import sys
    sys.path.insert(0, "/app")

    from ha_interface import HAInterface

    agent = DebugAgent(ha_interface=HAInterface())
    entities = agent.get_problem_entities()

    if not entities:
        console.print("[green]Žádné problémové entity[/green]")
        return

    table = Table(title=f"Problémové entity ({len(entities)})")
    table.add_column("Entity ID", style="cyan")
    table.add_column("Stav", style="red")
    table.add_column("Název", style="white")
    table.add_column("Poslední změna", style="dim")

    for entity in entities:
        table.add_row(
            entity["entity_id"],
            entity["state"],
            entity.get("friendly_name", ""),
            entity.get("last_changed", "")[:19] if entity.get("last_changed") else "",
        )

    console.print(table)


@cli.command()
@click.option("--lines", "-n", default=50, help="Počet řádků")
@click.option("--filter", "-f", "filter_str", help="Filtr")
@click.option("--errors", "-e", is_flag=True, help="Pouze chyby")
def logs(lines: int, filter_str: Optional[str], errors: bool):
    """Zobrazení logů."""
    import sys
    sys.path.insert(0, "/app")

    from ha_interface import HAInterface

    agent = DebugAgent(ha_interface=HAInterface())
    log_content = agent.get_logs(lines=lines, filter_str=filter_str)

    if errors:
        log_content = "\n".join(
            l for l in log_content.split("\n")
            if "ERROR" in l or "WARNING" in l
        )

    console.print(log_content)


@cli.command()
@click.argument("entity_id")
def automation(entity_id: str):
    """Analýza automatizace."""
    import sys
    sys.path.insert(0, "/app")

    from ha_interface import HAInterface

    agent = DebugAgent(ha_interface=HAInterface())
    info = agent.analyze_automation(entity_id)

    if info.get("error"):
        console.print(f"[red]{info['error']}[/red]")
        return

    console.print(Panel(
        f"[bold]Entity ID:[/bold] {info['entity_id']}\n"
        f"[bold]Stav:[/bold] {info['state']}\n"
        f"[bold]Název:[/bold] {info.get('friendly_name', 'N/A')}\n"
        f"[bold]Poslední spuštění:[/bold] {info.get('last_triggered', 'Nikdy')}\n"
        f"[bold]Mode:[/bold] {info.get('mode', 'single')}\n"
        f"[bold]Aktivní běhy:[/bold] {info.get('current', 0)}",
        title="Analýza automatizace",
        border_style="cyan"
    ))


@cli.command()
@click.argument("entity_id")
def entity(entity_id: str):
    """Diagnostika entity."""
    import sys
    import json
    sys.path.insert(0, "/app")

    from ha_interface import HAInterface
    from claude_client import ClaudeClient

    ha = HAInterface()
    agent = DebugAgent(ha_interface=ha, claude_client=ClaudeClient())

    # Získej stav entity
    try:
        state = ha.get_entity_state(entity_id)
    except Exception:
        state = None

    if not state:
        console.print(f"[red]Entita {entity_id} nenalezena[/red]")
        return

    # Zobraz info
    console.print(Panel(
        f"[bold]Entity ID:[/bold] {state.get('entity_id')}\n"
        f"[bold]Stav:[/bold] {state.get('state')}\n"
        f"[bold]Poslední změna:[/bold] {state.get('last_changed', '')[:19]}\n"
        f"[bold]Atributy:[/bold]\n{json.dumps(state.get('attributes', {}), indent=2, ensure_ascii=False)}",
        title="Entity Info",
        border_style="cyan"
    ))

    # Pokud je problém, analyzuj
    if state.get("state") in ["unavailable", "unknown"]:
        console.print("\n[yellow]Entita má problém - analyzuji...[/yellow]\n")
        result = agent.process(f"Entita {entity_id} je {state.get('state')}. Proč a jak to opravit?")
        agent.show_result(result)


if __name__ == "__main__":
    cli()
