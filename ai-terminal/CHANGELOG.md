# Changelog

## [0.5.0] - 2025-11-29

### Pridano
- **OpenAI Codex CLI** (@openai/codex) s MCP podporou
- `openai_api_key` v konfiguraci
- Codex CLI automaticky nakonfigurovan s MCP serverem
- **ha-tool** - univerzalni nastroj pro Gemini a dalsi AI bez MCP:
  - `ha-tool states [domain]` - seznam entit
  - `ha-tool state <entity>` - stav entity
  - `ha-tool on/off/toggle <entity>` - ovladani entit
  - `ha-tool call <domain> <service>` - volani sluzeb
  - `ha-tool template '<jinja>'` - vyhodnoceni sablony
  - `ha-tool reload <component>` - reload konfigurace

### Zmeneno
- Tri AI asistenti: Claude, Codex (s MCP), Gemini (bez MCP)
- Aktualizovany welcome screen

## [0.4.0] - 2025-11-29

### Pridano
- **MCP Server pro Claude CLI a Codex CLI** - Claude ma nyni pristup k HA nastrujum:
  - `ha_get_states` - seznam vsech entit
  - `ha_get_state` - detailni stav entity
  - `ha_call_service` - volani HA sluzeb
  - `ha_get_services` - seznam sluzeb
  - `ha_get_history` - historie entity
  - `config_read` - cteni YAML konfigurace
  - `config_write` - zapis YAML konfigurace
  - `config_add_automation` - pridani automatizace
  - `config_add_script` - pridani skriptu
  - `config_add_scene` - pridani sceny
  - `ha_render_template` - vyhodnoceni Jinja2 sablony
  - `mqtt_publish` - publikovani MQTT zpravy
  - `ha_reload` - reload konfigurace
  - `ha_get_config` - informace o HA
  - `ha_check_config` - kontrola konfigurace

### Zmeneno
- Claude CLI automaticky nakonfigurovan s MCP serverem
- Aktualizovany welcome screen

## [0.3.0] - 2024-11-29

### Pridano
- **7 specializovanych AI agentu:**
  - `ai-auto` - Automation Agent pro automatizace
  - `ai-entity` - Entity Agent pro spravu entit a sluzeb
  - `ai-sensor` - Sensor Agent pro template/MQTT senzory
  - `ai-script` - Script Agent pro skripty a sceny
  - `ai-energy` - Energy Agent pro FVE, baterie, spotrebu
  - `ai-debug` - Debug Agent pro diagnostiku
  - `ai-helper` - Helper Agent pro input helpers, groups
- Interaktivni napoveda `ai-help`
- Detailni system prompty pro kazdeho agenta
- CLI rozhrani pro vsechny agenty

### Zmeneno
- Prepracovany welcome screen s prehledem prikazu
- Verze 0.3.0

## [0.2.0] - 2024-11-29

### Pridano
- Gemini CLI (@google/gemini-cli) od Google
- gemini_api_key v konfiguraci
- Aktualizovana dokumentace pro oba AI asistenty

### Zmeneno
- ai-update nyni aktualizuje i Gemini CLI

## [0.1.0] - 2024-11-29

### Pridano
- Webovy terminal (ttyd + xterm.js)
- Claude CLI integrace (@anthropic-ai/claude-code)
- AI Config Agent pro upravu YAML konfigurace
- MQTT Inspector pro analyzu topicu
- HA CLI pro interakci s Home Assistantem
- Bezpecnostni mody (read_only, dry_run, apply)
- Automaticke zalohy konfigurace
- Sandbox rezim pro testovani
