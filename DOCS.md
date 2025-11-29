# AI Terminal pro Home Assistant

Plnohodnotny webovy terminal s integrovanym Claude CLI a AI agentem pro konfiguraci Home Assistanta.

## Funkce

### Webovy Terminal
- Pristup pres Home Assistant ingress (bez nutnosti SSH)
- Plnohodnotny Bash shell s xterm.js
- Tmave tema optimalizovane pro praci

### Claude CLI
- Oficialni Claude CLI od Anthropic
- Interaktivni chat: `claude chat`
- Jednorazove dotazy: `claude "tvuj dotaz"`

### AI Config Agent
- Generovani YAML konfigurace pro HA
- Uprava automatizaci, scriptu, scen
- Automaticke zalohy pred kazdou zmenou
- Validace konfigurace

### MQTT Inspector
- Skenovani MQTT topicu
- Navrhy senzoru pro HA
- Generovani YAML konfigurace

### HA CLI
- Informace o systemu
- Seznam entit
- Volani sluzeb
- Kontrola a reload konfigurace

## Instalace

1. Pridejte repository do Home Assistant
2. Nainstalujte add-on "AI Terminal"
3. Nastavte `claude_api_key` v konfiguraci
4. Spustte add-on
5. Otevrete webovy terminal pres bocni panel

## Konfigurace

### Zakladni nastaveni

```yaml
mode: dry_run           # read_only | dry_run | apply
claude_api_key: "sk-..." # Vas Anthropic API klic
backup_enabled: true     # Automaticke zalohy
sandbox_enabled: true    # Sandbox pro dry-run
```

### Povolene soubory

```yaml
allowed_files:
  - automations.yaml
  - scripts.yaml
  - scenes.yaml
  - configuration.yaml
```

### MQTT (volitelne)

```yaml
mqtt_broker: "core-mosquitto"  # nebo IP adresa
mqtt_port: 1883
mqtt_user: ""
mqtt_password: ""
```

## Pouziti

### Claude CLI

```bash
# Interaktivni chat
claude chat

# Jednorazovy dotaz
claude "jak vytvorit automatizaci pro svetla?"
```

### AI Config Agent

```bash
# Generovani automatizace
ai-config "pridej automatizaci ktera zapne svetla pri zapadku slunce"

# Zobrazeni stavu
ai-config --status

# Zmena modu
ai-config --mode apply "uprav script pro FVE"
```

### MQTT Inspector

```bash
# Skenovani topicu (30 sekund)
mqtt-inspect scan

# Delsi skenovani
mqtt-inspect scan -d 120

# Zobrazeni cache
mqtt-inspect show

# Navrhy senzoru
mqtt-inspect suggest
```

### HA CLI

```bash
# Informace o systemu
ha-cli info

# Seznam entit
ha-cli entities

# Entity podle domeny
ha-cli entities -d light

# Kontrola konfigurace
ha-cli check

# Reload konfigurace
ha-cli reload

# Volani sluzby
ha-cli call light turn_on -e light.obyvak
```

### Sprava zaloh

```bash
# Seznam zaloh
ai-backup list

# Obnoveni zalohy
ai-backup restore automations.yaml.20240115_120000.bak

# Cisteni starych zaloh
ai-backup clean 7
```

### Aktualizace

```bash
# Aktualizace Claude CLI a Python zavislosti
ai-update
```

## Bezpecnostni mody

### read_only
- AI generuje navrhy ale nic nezapisuje
- Bezpecny pro experimentovani

### dry_run (doporuceno)
- Navrhy se ukladaji do `*.ai.yaml` souboru
- Moznost kontroly pred aplikaci

### apply
- Primo zapisuje do konfigurace
- Vzdycky vytvori zalohu
- Vyzaduje potvrzeni

## Struktura adresaru

```
/config/
├── automations.yaml      # Hlavni soubory
├── scripts.yaml
├── scenes.yaml
├── ai_config.yaml        # Volitelny AI config
├── ai_mqtt_topics.json   # MQTT cache
├── ai_sandbox/           # Sandbox pro dry-run
│   ├── automations.ai.yaml
│   └── scripts.ai.yaml
└── .ai_backups/          # Automaticke zalohy
    ├── automations.yaml.20240115_120000.bak
    └── scripts.yaml.20240115_120001.bak
```

## Reseni problemu

### Claude CLI nefunguje
- Zkontrolujte `claude_api_key` v konfiguraci
- Overite platnost API klice na console.anthropic.com

### MQTT Inspector nevidí topicy
- Zkontrolujte `mqtt_broker` nastaveni
- Overite pripojeni: `mosquitto_sub -h broker -t '#' -C 1`

### Konfigurace se neuklada
- Zkontrolujte `mode` nastaveni (ne `read_only`)
- Overite ze soubor je v `allowed_files`

### Chyby pri reloadu
- Spustte `ha-cli check` pro validaci
- Zkontrolujte logy: `ha-cli logs`

## Podpora

- GitHub Issues: https://github.com/your-repo/ai-terminal-addon/issues
- Home Assistant Community: https://community.home-assistant.io
