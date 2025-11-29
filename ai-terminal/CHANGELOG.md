# Changelog

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
