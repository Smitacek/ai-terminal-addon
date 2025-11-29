#!/usr/bin/env python3
"""
Claude API Client pro AI Terminal.
Wrapper pro Anthropic Claude API.
"""

import os
from typing import Optional
import anthropic
from rich.console import Console

console = Console()


class ClaudeClient:
    """Klient pro komunikaci s Claude API."""

    def __init__(self):
        self.api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        self.model = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-20250514")
        self.max_tokens = int(os.environ.get("CLAUDE_MAX_TOKENS", "4096"))

        if not self.api_key:
            console.print("[yellow]VAROVANI: ANTHROPIC_API_KEY neni nastaven![/yellow]")

        self.client = anthropic.Anthropic(api_key=self.api_key) if self.api_key else None

    def chat(
        self,
        user_message: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
    ) -> str:
        """
        Poslani zpravy do Claude a ziskani odpovedi.

        Args:
            user_message: Uzivatelska zprava
            system_prompt: Systemovy prompt (volitelny)
            temperature: Teplota pro generovani (0.0-1.0)

        Returns:
            Textova odpoved od Claude
        """
        if not self.client:
            raise RuntimeError(
                "Claude API klient neni inicializovan. "
                "Nastavte ANTHROPIC_API_KEY v konfiguraci add-onu."
            )

        messages = [{"role": "user", "content": user_message}]

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system_prompt or "",
                messages=messages,
                temperature=temperature,
            )

            # Extrakce textove odpovedi
            if response.content:
                return response.content[0].text
            return ""

        except anthropic.APIError as e:
            console.print(f"[red]Claude API chyba: {e}[/red]")
            raise
        except Exception as e:
            console.print(f"[red]Neocekavana chyba: {e}[/red]")
            raise

    def chat_stream(
        self,
        user_message: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
    ):
        """
        Streaming verze chatu pro realtime vystup.

        Yields:
            Fragmenty textu jak prichazeji
        """
        if not self.client:
            raise RuntimeError("Claude API klient neni inicializovan.")

        messages = [{"role": "user", "content": user_message}]

        try:
            with self.client.messages.stream(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system_prompt or "",
                messages=messages,
                temperature=temperature,
            ) as stream:
                for text in stream.text_stream:
                    yield text

        except Exception as e:
            console.print(f"[red]Streaming chyba: {e}[/red]")
            raise

    def is_available(self) -> bool:
        """Kontrola dostupnosti API."""
        return bool(self.api_key and self.client)
