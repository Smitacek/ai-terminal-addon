#!/usr/bin/env python3
"""
Home Assistant Interface pro AI Terminal.
Komunikace s HA pres Supervisor API a REST API.
"""

import os
import sys
import json
import click
from typing import Any, Dict, List, Optional
import httpx
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


class HAInterface:
    """Interface pro komunikaci s Home Assistant."""

    def __init__(self):
        self.supervisor_token = os.environ.get("SUPERVISOR_TOKEN", "")
        self.supervisor_url = "http://supervisor"
        self.ha_url = "http://supervisor/core"

        self.headers = {
            "Authorization": f"Bearer {self.supervisor_token}",
            "Content-Type": "application/json",
        }

    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        base_url: Optional[str] = None,
    ) -> Dict:
        """Zakladni HTTP request."""
        url = f"{base_url or self.supervisor_url}{endpoint}"

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    json=data,
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            console.print(f"[red]HTTP chyba: {e}[/red]")
            raise

    # =========================================================================
    # Supervisor API
    # =========================================================================

    def get_supervisor_info(self) -> Dict:
        """Informace o Supervisoru."""
        return self._request("GET", "/supervisor/info")

    def get_host_info(self) -> Dict:
        """Informace o hostu."""
        return self._request("GET", "/host/info")

    def get_core_info(self) -> Dict:
        """Informace o HA Core."""
        return self._request("GET", "/core/info")

    def get_addons(self) -> List[Dict]:
        """Seznam add-onu."""
        result = self._request("GET", "/addons")
        return result.get("data", {}).get("addons", [])

    # =========================================================================
    # Home Assistant Core API
    # =========================================================================

    def get_entities(self) -> List[Dict]:
        """Seznam vsech entit."""
        result = self._request("GET", "/api/states", base_url=self.ha_url)
        return result if isinstance(result, list) else []

    def get_entity_state(self, entity_id: str) -> Dict:
        """Stav konkretni entity."""
        return self._request("GET", f"/api/states/{entity_id}", base_url=self.ha_url)

    def call_service(self, domain: str, service: str, data: Optional[Dict] = None) -> Dict:
        """Volani HA service."""
        return self._request(
            "POST",
            f"/api/services/{domain}/{service}",
            data=data or {},
            base_url=self.ha_url,
        )

    def check_config(self) -> bool:
        """Kontrola konfigurace."""
        try:
            result = self._request("POST", "/api/config/core/check_config", base_url=self.ha_url)
            return result.get("result") == "valid"
        except Exception:
            # Fallback na Supervisor API
            try:
                result = self._request("POST", "/core/check")
                return result.get("result") == "ok"
            except Exception:
                return False

    def reload_core(self) -> bool:
        """Reload HA core."""
        try:
            self._request("POST", "/api/services/homeassistant/reload_all", base_url=self.ha_url)
            return True
        except Exception as e:
            console.print(f"[red]Reload selhal: {e}[/red]")
            return False

    def restart_core(self) -> bool:
        """Restart HA core."""
        try:
            self._request("POST", "/core/restart")
            return True
        except Exception as e:
            console.print(f"[red]Restart selhal: {e}[/red]")
            return False

    def get_logs(self, lines: int = 100) -> str:
        """Ziskani HA logu."""
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(
                    f"{self.ha_url}/api/error_log",
                    headers=self.headers,
                )
                return response.text[-lines * 200:]  # Priblizne poslednich N radku
        except Exception as e:
            return f"Chyba pri ziskavani logu: {e}"

    def get_entity_registry(self) -> List[Dict]:
        """Entity registry."""
        try:
            # Websocket API pres REST wrapper
            result = self._request(
                "GET",
                "/api/config/entity_registry",
                base_url=self.ha_url,
            )
            return result if isinstance(result, list) else []
        except Exception:
            # Fallback - pouzij states
            return self.get_entities()

    def get_device_registry(self) -> List[Dict]:
        """Device registry."""
        try:
            result = self._request(
                "GET",
                "/api/config/device_registry",
                base_url=self.ha_url,
            )
            return result if isinstance(result, list) else []
        except Exception:
            return []


# =============================================================================
# CLI Interface
# =============================================================================

@click.group()
def cli():
    """Home Assistant CLI pro AI Terminal."""
    pass


@cli.command()
def info():
    """Zobraz informace o systemu."""
    ha = HAInterface()

    try:
        core = ha.get_core_info()
        host = ha.get_host_info()

        info_text = f"""
[bold]Home Assistant Core[/bold]
  Version:    {core.get('data', {}).get('version', 'N/A')}
  State:      {core.get('data', {}).get('state', 'N/A')}

[bold]Host[/bold]
  OS:         {host.get('data', {}).get('operating_system', 'N/A')}
  Hostname:   {host.get('data', {}).get('hostname', 'N/A')}
  Arch:       {host.get('data', {}).get('chassis', 'N/A')}
"""
        console.print(Panel(info_text, title="System Info", border_style="blue"))
    except Exception as e:
        console.print(f"[red]Chyba: {e}[/red]")


@cli.command()
@click.option("--domain", "-d", help="Filtruj podle domeny (light, switch, ...)")
def entities(domain: Optional[str]):
    """Seznam entit."""
    ha = HAInterface()

    try:
        all_entities = ha.get_entities()

        if domain:
            all_entities = [e for e in all_entities if e.get("entity_id", "").startswith(f"{domain}.")]

        table = Table(title=f"Entity ({len(all_entities)})")
        table.add_column("Entity ID", style="cyan")
        table.add_column("State", style="green")
        table.add_column("Name", style="dim")

        for entity in all_entities[:50]:  # Limit 50
            table.add_row(
                entity.get("entity_id", ""),
                str(entity.get("state", "")),
                entity.get("attributes", {}).get("friendly_name", ""),
            )

        console.print(table)

        if len(all_entities) > 50:
            console.print(f"[dim]... a dalsich {len(all_entities) - 50} entit[/dim]")

    except Exception as e:
        console.print(f"[red]Chyba: {e}[/red]")


@cli.command()
def check():
    """Kontrola konfigurace."""
    ha = HAInterface()
    console.print("[dim]Kontroluji konfiguraci...[/dim]")

    if ha.check_config():
        console.print("[green]Konfigurace je validni![/green]")
    else:
        console.print("[red]Konfigurace obsahuje chyby![/red]")


@cli.command()
def reload():
    """Reload HA konfigurace."""
    ha = HAInterface()
    console.print("[dim]Reloaduji...[/dim]")

    if ha.reload_core():
        console.print("[green]Reload uspesny![/green]")
    else:
        console.print("[red]Reload selhal![/red]")


@cli.command()
@click.option("--lines", "-n", default=50, help="Pocet radku")
def logs(lines: int):
    """Zobraz HA logy."""
    ha = HAInterface()
    log_content = ha.get_logs(lines)
    console.print(log_content)


@cli.command()
@click.argument("domain")
@click.argument("service")
@click.option("--entity", "-e", help="Entity ID")
@click.option("--data", "-d", help="JSON data")
def call(domain: str, service: str, entity: Optional[str], data: Optional[str]):
    """Volani HA service."""
    ha = HAInterface()

    service_data = {}
    if entity:
        service_data["entity_id"] = entity
    if data:
        service_data.update(json.loads(data))

    console.print(f"[dim]Volam {domain}.{service}...[/dim]")
    result = ha.call_service(domain, service, service_data)
    console.print("[green]OK[/green]")


if __name__ == "__main__":
    cli()
