# AI Terminal Add-ons pro Home Assistant

[![Open your Home Assistant instance and show the add add-on repository dialog with a specific repository URL pre-filled.](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FSmitacek%2Fai-terminal-addon)

## Add-ony

### AI Terminal

Plnohodnotny webovy terminal s integrovanym Claude CLI a AI agentem pro konfiguraci Home Assistanta.

**Funkce:**
- Webovy terminal (ttyd + xterm.js) primo v HA
- Claude CLI (`@anthropic-ai/claude-code`)
- AI Config Agent pro upravu YAML konfigurace
- MQTT Inspector pro analyzu topicu
- HA CLI pro interakci s Home Assistantem
- Bezpecnostni mody (read_only, dry_run, apply)
- Automaticke zalohy konfigurace

## Instalace

1. Klikni na tlacitko vyse nebo pridej repository rucne:
   - Prejdi do **Settings** > **Add-ons** > **Add-on Store**
   - Klikni na **...** (menu) > **Repositories**
   - Pridej URL: `https://github.com/Smitacek/ai-terminal-addon`
2. Najdi "AI Terminal" a nainstaluj
3. Nastav `claude_api_key` v konfiguraci
4. Spust add-on

## Dokumentace

Viz [ai-terminal/DOCS.md](ai-terminal/DOCS.md)

## Licence

MIT
