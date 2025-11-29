#!/usr/bin/env python3
"""
MQTT Inspector pro AI Terminal.
Nastroj pro analyzu MQTT topicu a navrhovani HA integrace.
"""

import os
import sys
import json
import time
import click
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
import paho.mqtt.client as mqtt
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live

console = Console()


@dataclass
class MQTTMessage:
    """Reprezentace MQTT zpravy."""
    topic: str
    payload: str
    timestamp: float
    qos: int = 0
    retain: bool = False


@dataclass
class TopicInfo:
    """Informace o MQTT topicu."""
    topic: str
    messages: List[MQTTMessage] = field(default_factory=list)
    first_seen: float = 0
    last_seen: float = 0
    message_count: int = 0

    def add_message(self, msg: MQTTMessage):
        self.messages.append(msg)
        self.message_count += 1
        self.last_seen = msg.timestamp
        if not self.first_seen:
            self.first_seen = msg.timestamp

    @property
    def last_payload(self) -> str:
        return self.messages[-1].payload if self.messages else ""


class MQTTInspector:
    """MQTT Inspector pro analyzu a navrhovani HA konfigurace."""

    def __init__(self):
        self.broker = os.environ.get("MQTT_BROKER", "")
        self.port = int(os.environ.get("MQTT_PORT", "1883"))
        self.username = os.environ.get("MQTT_USER", "")
        self.password = os.environ.get("MQTT_PASSWORD", "")

        self.topics: Dict[str, TopicInfo] = {}
        self.running = False
        self.client: Optional[mqtt.Client] = None

        self.cache_file = Path("/config/ai_mqtt_topics.json")

    def connect(self) -> bool:
        """Pripojeni k MQTT brokeru."""
        if not self.broker:
            console.print("[red]MQTT broker neni nakonfigurovan![/red]")
            console.print("[dim]Nastavte mqtt_broker v konfiguraci add-onu.[/dim]")
            return False

        try:
            self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

            if self.username:
                self.client.username_pw_set(self.username, self.password)

            self.client.on_connect = self._on_connect
            self.client.on_message = self._on_message
            self.client.on_disconnect = self._on_disconnect

            console.print(f"[dim]Pripojuji k {self.broker}:{self.port}...[/dim]")
            self.client.connect(self.broker, self.port, 60)

            return True

        except Exception as e:
            console.print(f"[red]Pripojeni selhalo: {e}[/red]")
            return False

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        """Callback pri pripojeni."""
        if reason_code == 0:
            console.print("[green]Pripojeno k MQTT brokeru[/green]")
            client.subscribe("#")  # Vsechny topicy
        else:
            console.print(f"[red]Pripojeni selhalo: {reason_code}[/red]")

    def _on_message(self, client, userdata, msg):
        """Callback pri prijmu zpravy."""
        topic = msg.topic
        try:
            payload = msg.payload.decode("utf-8")
        except Exception:
            payload = str(msg.payload)

        message = MQTTMessage(
            topic=topic,
            payload=payload,
            timestamp=time.time(),
            qos=msg.qos,
            retain=msg.retain,
        )

        if topic not in self.topics:
            self.topics[topic] = TopicInfo(topic=topic)

        self.topics[topic].add_message(message)

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        """Callback pri odpojeni."""
        console.print("[yellow]Odpojeno od MQTT brokeru[/yellow]")

    def scan(self, duration: int = 30) -> Dict[str, TopicInfo]:
        """
        Sken MQTT topicu po zadanou dobu.

        Args:
            duration: Doba skenovani v sekundach

        Returns:
            Slovnik nalezenych topicu
        """
        if not self.connect():
            return {}

        self.running = True
        self.topics.clear()

        console.print(f"\n[bold]Skenuji MQTT topicy ({duration}s)...[/bold]")
        console.print("[dim]Stiskni Ctrl+C pro preruseni[/dim]\n")

        self.client.loop_start()

        try:
            with Live(self._generate_table(), refresh_per_second=2) as live:
                start = time.time()
                while time.time() - start < duration and self.running:
                    time.sleep(0.5)
                    live.update(self._generate_table())

        except KeyboardInterrupt:
            console.print("\n[yellow]Preruseno[/yellow]")

        self.client.loop_stop()
        self.client.disconnect()

        # Ulozeni do cache
        self._save_cache()

        return self.topics

    def _generate_table(self) -> Table:
        """Generovani tabulky pro live zobrazeni."""
        table = Table(title=f"MQTT Topicy ({len(self.topics)})")
        table.add_column("Topic", style="cyan", max_width=50)
        table.add_column("Msgs", style="green", justify="right")
        table.add_column("Last Payload", style="dim", max_width=40)

        for topic_info in sorted(self.topics.values(), key=lambda x: x.message_count, reverse=True)[:20]:
            payload = topic_info.last_payload
            if len(payload) > 40:
                payload = payload[:37] + "..."

            table.add_row(
                topic_info.topic,
                str(topic_info.message_count),
                payload,
            )

        return table

    def _save_cache(self):
        """Ulozeni nalezenych topicu do cache."""
        cache_data = {
            "timestamp": datetime.now().isoformat(),
            "broker": self.broker,
            "topics": {},
        }

        for topic, info in self.topics.items():
            cache_data["topics"][topic] = {
                "message_count": info.message_count,
                "last_payload": info.last_payload,
                "first_seen": info.first_seen,
                "last_seen": info.last_seen,
            }

        self.cache_file.write_text(json.dumps(cache_data, indent=2))
        console.print(f"\n[dim]Cache ulozena: {self.cache_file}[/dim]")

    def load_cache(self) -> Optional[Dict]:
        """Nacteni cache."""
        if not self.cache_file.exists():
            return None
        return json.loads(self.cache_file.read_text())

    def suggest_sensors(self) -> List[Dict]:
        """Navrh MQTT senzoru pro HA."""
        suggestions = []

        for topic, info in self.topics.items():
            payload = info.last_payload

            # Pokus o JSON parsing
            try:
                data = json.loads(payload)
                if isinstance(data, dict):
                    # Kazdy klic = potencialni senzor
                    for key, value in data.items():
                        if isinstance(value, (int, float, str)):
                            suggestions.append({
                                "type": "sensor",
                                "name": f"{topic.replace('/', '_')}_{key}",
                                "state_topic": topic,
                                "value_template": f"{{{{ value_json.{key} }}}}",
                                "sample_value": value,
                            })
            except json.JSONDecodeError:
                # Jednoduchy payload
                if payload.replace(".", "").replace("-", "").isdigit():
                    suggestions.append({
                        "type": "sensor",
                        "name": topic.replace("/", "_"),
                        "state_topic": topic,
                        "value_template": "{{ value }}",
                        "sample_value": payload,
                    })
                elif payload.lower() in ("on", "off", "true", "false", "1", "0"):
                    suggestions.append({
                        "type": "binary_sensor",
                        "name": topic.replace("/", "_"),
                        "state_topic": topic,
                        "payload_on": "on" if "on" in payload.lower() else payload,
                        "payload_off": "off" if "off" in payload.lower() else "",
                    })

        return suggestions

    def generate_yaml(self, suggestions: List[Dict]) -> str:
        """Generovani YAML konfigurace pro navrhy."""
        sensors = []
        binary_sensors = []

        for s in suggestions:
            if s["type"] == "sensor":
                sensors.append({
                    "name": s["name"],
                    "state_topic": s["state_topic"],
                    "value_template": s["value_template"],
                })
            elif s["type"] == "binary_sensor":
                binary_sensors.append({
                    "name": s["name"],
                    "state_topic": s["state_topic"],
                    "payload_on": s.get("payload_on", "ON"),
                    "payload_off": s.get("payload_off", "OFF"),
                })

        import yaml

        result = "# MQTT Sensors - vygenerovano AI Terminal\n\n"

        if sensors:
            result += "mqtt:\n  sensor:\n"
            result += yaml.dump(sensors, default_flow_style=False, allow_unicode=True, indent=4)

        if binary_sensors:
            result += "\n  binary_sensor:\n"
            result += yaml.dump(binary_sensors, default_flow_style=False, allow_unicode=True, indent=4)

        return result


# =============================================================================
# CLI
# =============================================================================

@click.group()
def cli():
    """MQTT Inspector pro AI Terminal."""
    pass


@cli.command()
@click.option("--duration", "-d", default=30, help="Doba skenovani v sekundach")
def scan(duration: int):
    """Skenuj MQTT topicy."""
    inspector = MQTTInspector()
    topics = inspector.scan(duration)

    console.print(f"\n[bold green]Nalezeno {len(topics)} topicu[/bold green]")


@cli.command()
def show():
    """Zobraz ulozene topicy z cache."""
    inspector = MQTTInspector()
    cache = inspector.load_cache()

    if not cache:
        console.print("[yellow]Cache neexistuje. Spust 'mqtt-inspect scan' prvni.[/yellow]")
        return

    console.print(f"[dim]Cache z: {cache.get('timestamp')}[/dim]\n")

    table = Table(title=f"MQTT Topicy ({len(cache.get('topics', {}))})")
    table.add_column("Topic", style="cyan")
    table.add_column("Msgs", justify="right")
    table.add_column("Last Payload", style="dim", max_width=50)

    for topic, info in cache.get("topics", {}).items():
        table.add_row(topic, str(info.get("message_count", 0)), info.get("last_payload", "")[:50])

    console.print(table)


@cli.command()
def suggest():
    """Navrhni MQTT senzory pro HA."""
    inspector = MQTTInspector()
    cache = inspector.load_cache()

    if not cache:
        console.print("[yellow]Cache neexistuje. Spust 'mqtt-inspect scan' prvni.[/yellow]")
        return

    # Rekonstrukce TopicInfo z cache
    for topic, info in cache.get("topics", {}).items():
        ti = TopicInfo(topic=topic)
        ti.message_count = info.get("message_count", 0)
        ti.messages = [MQTTMessage(topic=topic, payload=info.get("last_payload", ""), timestamp=0)]
        inspector.topics[topic] = ti

    suggestions = inspector.suggest_sensors()

    if not suggestions:
        console.print("[yellow]Zadne navrhy[/yellow]")
        return

    console.print(f"\n[bold]Navrhy ({len(suggestions)}):[/bold]\n")

    for s in suggestions[:20]:
        console.print(f"  [cyan]{s['type']}[/cyan]: {s['name']}")
        console.print(f"    [dim]Topic: {s['state_topic']}[/dim]")

    # Generovani YAML
    yaml_config = inspector.generate_yaml(suggestions)
    console.print("\n[bold]YAML konfigurace:[/bold]")
    console.print(Panel(yaml_config, border_style="green"))


if __name__ == "__main__":
    cli()
