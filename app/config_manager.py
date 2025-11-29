#!/usr/bin/env python3
"""
Config Manager pro AI Terminal.
Sprava konfiguracnich souboru, zaloh a sandboxu.
"""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from rich.console import Console

console = Console()


class ConfigManager:
    """Spravce konfiguracnich souboru Home Assistanta."""

    def __init__(
        self,
        config_dir: str = "/config",
        backup_dir: str = "/config/.ai_backups",
        sandbox_dir: str = "/config/ai_sandbox",
        allowed_files: Optional[List[str]] = None,
    ):
        self.config_dir = Path(config_dir)
        self.backup_dir = Path(backup_dir)
        self.sandbox_dir = Path(sandbox_dir)
        self.allowed_files = allowed_files or []

        # Vytvoreni adresaru pokud neexistuji
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)

    def is_file_allowed(self, filename: str) -> bool:
        """Kontrola zda je soubor v whitelistu."""
        return filename in self.allowed_files

    def get_file_path(self, filename: str) -> Path:
        """Ziskani cesty k souboru."""
        if not self.is_file_allowed(filename):
            raise PermissionError(f"Soubor '{filename}' neni v whitelistu.")
        return self.config_dir / filename

    def read_file(self, filename: str) -> str:
        """Precteni obsahu souboru."""
        filepath = self.get_file_path(filename)
        if not filepath.exists():
            return ""
        return filepath.read_text(encoding="utf-8")

    def write_file(self, filename: str, content: str, create_backup: bool = True) -> Path:
        """
        Zapis obsahu do souboru.

        Args:
            filename: Nazev souboru
            content: Obsah k zapisu
            create_backup: Zda vytvorit zalohu

        Returns:
            Cesta k zapsanemu souboru
        """
        filepath = self.get_file_path(filename)

        # Backup existujiciho souboru
        if create_backup and filepath.exists():
            self.create_backup(filename)

        # Zapis
        filepath.write_text(content, encoding="utf-8")
        console.print(f"[green]Zapsano: {filepath}[/green]")

        return filepath

    def write_to_sandbox(self, filename: str, content: str) -> Path:
        """Zapis do sandbox adresare (pro dry-run mod)."""
        sandbox_path = self.sandbox_dir / filename
        sandbox_path.write_text(content, encoding="utf-8")
        console.print(f"[cyan]Sandbox: {sandbox_path}[/cyan]")
        return sandbox_path

    def create_backup(self, filename: str) -> Optional[Path]:
        """Vytvoreni zalohy souboru."""
        filepath = self.config_dir / filename
        if not filepath.exists():
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{filename}.{timestamp}.bak"
        backup_path = self.backup_dir / backup_name

        shutil.copy2(filepath, backup_path)
        console.print(f"[dim]Backup: {backup_path}[/dim]")

        return backup_path

    def list_backups(self, filename: Optional[str] = None) -> List[Path]:
        """Seznam zaloh."""
        pattern = f"{filename}.*.bak" if filename else "*.bak"
        return sorted(self.backup_dir.glob(pattern), reverse=True)

    def restore_backup(self, backup_path: Path) -> Path:
        """Obnoveni ze zalohy."""
        # Extrakce puvodniho nazvu
        backup_name = backup_path.name
        # Odstraneni timestamp a .bak
        original_name = ".".join(backup_name.split(".")[:-2])

        if not self.is_file_allowed(original_name):
            raise PermissionError(f"Soubor '{original_name}' neni v whitelistu.")

        target_path = self.config_dir / original_name

        # Backup aktualniho stavu pred obnovenim
        if target_path.exists():
            self.create_backup(original_name)

        shutil.copy2(backup_path, target_path)
        console.print(f"[green]Obnoveno: {target_path}[/green]")

        return target_path

    def clean_old_backups(self, days: int = 7) -> int:
        """Smazani starych zaloh."""
        import time

        cutoff = time.time() - (days * 86400)
        count = 0

        for backup in self.backup_dir.glob("*.bak"):
            if backup.stat().st_mtime < cutoff:
                backup.unlink()
                count += 1

        console.print(f"[dim]Smazano {count} starych zaloh[/dim]")
        return count

    def get_config_files(self) -> dict:
        """Nacteni vsech povolenych konfiguracnich souboru."""
        files = {}
        for filename in self.allowed_files:
            filepath = self.config_dir / filename
            if filepath.exists():
                files[filename] = filepath.read_text(encoding="utf-8")
            else:
                files[filename] = ""
        return files

    def validate_yaml(self, content: str) -> bool:
        """Zakladni validace YAML syntaxe."""
        import yaml

        try:
            yaml.safe_load(content)
            return True
        except yaml.YAMLError as e:
            console.print(f"[red]YAML chyba: {e}[/red]")
            return False
