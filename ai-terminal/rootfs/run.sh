#!/usr/bin/with-contenv bash
# =============================================================================
# AI Terminal Add-on - Hlavni spousteci skript
# =============================================================================

set -e

CONFIG_PATH="/data/options.json"

# -----------------------------------------------------------------------------
# Nacteni konfigurace z Home Assistant options
# -----------------------------------------------------------------------------
echo "[INFO] Nacitam konfiguraci add-onu..."

# Nacteni options z JSON
AI_MODE=$(jq -r '.mode // "dry_run"' "$CONFIG_PATH")
BACKUP_ENABLED=$(jq -r '.backup_enabled // true' "$CONFIG_PATH")
SANDBOX_ENABLED=$(jq -r '.sandbox_enabled // true' "$CONFIG_PATH")
SANDBOX_DIR=$(jq -r '.sandbox_dir // "/config/ai_sandbox"' "$CONFIG_PATH")
LOG_LEVEL=$(jq -r '.log_level // "info"' "$CONFIG_PATH")
CLAUDE_API_KEY=$(jq -r '.claude_api_key // ""' "$CONFIG_PATH")
OPENAI_API_KEY=$(jq -r '.openai_api_key // ""' "$CONFIG_PATH")
GEMINI_API_KEY=$(jq -r '.gemini_api_key // ""' "$CONFIG_PATH")
MQTT_BROKER=$(jq -r '.mqtt_broker // ""' "$CONFIG_PATH")
MQTT_PORT=$(jq -r '.mqtt_port // 1883' "$CONFIG_PATH")
MQTT_USER=$(jq -r '.mqtt_user // ""' "$CONFIG_PATH")
MQTT_PASSWORD=$(jq -r '.mqtt_password // ""' "$CONFIG_PATH")

# Allowed files jako pole
ALLOWED_FILES=$(jq -r '.allowed_files | join(",")' "$CONFIG_PATH")

# Export promennych pro podprocesy
export AI_MODE
export BACKUP_ENABLED
export SANDBOX_ENABLED
export SANDBOX_DIR
export LOG_LEVEL
export ALLOWED_FILES
export ANTHROPIC_API_KEY="$CLAUDE_API_KEY"
export OPENAI_API_KEY="$OPENAI_API_KEY"
export GEMINI_API_KEY="$GEMINI_API_KEY"
export MQTT_BROKER
export MQTT_PORT
export MQTT_USER
export MQTT_PASSWORD

# HA Supervisor token (automaticky dostupny)
export SUPERVISOR_TOKEN="${SUPERVISOR_TOKEN:-}"
export HA_TOKEN="${SUPERVISOR_TOKEN}"

echo "[INFO] Konfigurace nactena:"
echo "  - AI Mode: $AI_MODE"
echo "  - Backup: $BACKUP_ENABLED"
echo "  - Sandbox: $SANDBOX_ENABLED"
echo "  - Log Level: $LOG_LEVEL"
echo "  - Allowed Files: $ALLOWED_FILES"

# -----------------------------------------------------------------------------
# Kontrola API klice
# -----------------------------------------------------------------------------
if [ -z "$CLAUDE_API_KEY" ]; then
    echo "[WARN] Claude API klic neni nastaven!"
    echo "[WARN] Claude CLI nebude funkcni. Nastavte 'claude_api_key' v konfiguraci."
fi

if [ -z "$OPENAI_API_KEY" ]; then
    echo "[WARN] OpenAI API klic neni nastaven!"
    echo "[WARN] Codex CLI nebude funkcni. Nastavte 'openai_api_key' v konfiguraci."
fi

if [ -z "$GEMINI_API_KEY" ]; then
    echo "[WARN] Gemini API klic neni nastaven!"
    echo "[WARN] Gemini CLI nebude funkcni. Nastavte 'gemini_api_key' v konfiguraci."
fi

# -----------------------------------------------------------------------------
# Vytvoreni sandbox adresare pokud je povolen
# -----------------------------------------------------------------------------
if [ "$SANDBOX_ENABLED" = "true" ]; then
    echo "[INFO] Vytvarim sandbox adresar: $SANDBOX_DIR"
    mkdir -p "$SANDBOX_DIR"
fi

# -----------------------------------------------------------------------------
# Vytvoreni zalozniho adresare
# -----------------------------------------------------------------------------
BACKUP_DIR="/config/.ai_backups"
mkdir -p "$BACKUP_DIR"
export BACKUP_DIR
echo "[INFO] Zalozni adresar: $BACKUP_DIR"

# -----------------------------------------------------------------------------
# Konfigurace Claude CLI MCP serveru
# -----------------------------------------------------------------------------
echo "[INFO] Konfiguruji Claude CLI s MCP serverem..."

CLAUDE_CONFIG_DIR="/root/.claude"
mkdir -p "$CLAUDE_CONFIG_DIR"

cat > "$CLAUDE_CONFIG_DIR/settings.json" << EOF
{
  "mcpServers": {
    "home-assistant": {
      "command": "/usr/local/bin/ha-mcp-server",
      "env": {
        "SUPERVISOR_TOKEN": "$SUPERVISOR_TOKEN",
        "AI_MODE": "$AI_MODE",
        "ALLOWED_FILES": "$ALLOWED_FILES",
        "MQTT_BROKER": "$MQTT_BROKER",
        "MQTT_PORT": "$MQTT_PORT",
        "MQTT_USER": "$MQTT_USER",
        "MQTT_PASSWORD": "$MQTT_PASSWORD"
      }
    }
  },
  "permissions": {
    "allow": [
      "mcp__home-assistant__*"
    ]
  }
}
EOF

echo "[INFO] Claude CLI MCP konfigurace vytvorena"

# -----------------------------------------------------------------------------
# Konfigurace Codex CLI MCP serveru
# -----------------------------------------------------------------------------
echo "[INFO] Konfiguruji Codex CLI s MCP serverem..."

CODEX_CONFIG_DIR="/root/.codex"
mkdir -p "$CODEX_CONFIG_DIR"

cat > "$CODEX_CONFIG_DIR/config.toml" << EOF
# Codex CLI konfigurace pro AI Terminal

[mcp_servers.home-assistant]
command = "/usr/local/bin/ha-mcp-server"

[mcp_servers.home-assistant.env]
SUPERVISOR_TOKEN = "$SUPERVISOR_TOKEN"
AI_MODE = "$AI_MODE"
ALLOWED_FILES = "$ALLOWED_FILES"
MQTT_BROKER = "$MQTT_BROKER"
MQTT_PORT = "$MQTT_PORT"
MQTT_USER = "$MQTT_USER"
MQTT_PASSWORD = "$MQTT_PASSWORD"
EOF

echo "[INFO] Codex CLI MCP konfigurace vytvorena"

# -----------------------------------------------------------------------------
# Inicializace MQTT pokud je nakonfigurovano
# -----------------------------------------------------------------------------
if [ -n "$MQTT_BROKER" ]; then
    echo "[INFO] MQTT broker: $MQTT_BROKER:$MQTT_PORT"
    # Test pripojeni
    if mosquitto_sub -h "$MQTT_BROKER" -p "$MQTT_PORT" \
        ${MQTT_USER:+-u "$MQTT_USER"} \
        ${MQTT_PASSWORD:+-P "$MQTT_PASSWORD"} \
        -t '#' -C 1 -W 3 2>/dev/null; then
        echo "[INFO] MQTT pripojeni OK"
    else
        echo "[WARN] MQTT pripojeni selhalo - mqtt-inspect nebude funkcni"
    fi
fi

# -----------------------------------------------------------------------------
# Nastaveni bash prostredi
# -----------------------------------------------------------------------------

# Nejdřív uložit proměnné do souboru (pro subshelly)
cat > /etc/ai-terminal.env << ENVFILE
export SUPERVISOR_TOKEN="$SUPERVISOR_TOKEN"
export HA_TOKEN="$SUPERVISOR_TOKEN"
export AI_MODE="$AI_MODE"
export ALLOWED_FILES="$ALLOWED_FILES"
export BACKUP_DIR="$BACKUP_DIR"
export MQTT_BROKER="$MQTT_BROKER"
export MQTT_PORT="$MQTT_PORT"
export MQTT_USER="$MQTT_USER"
export MQTT_PASSWORD="$MQTT_PASSWORD"
export ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY"
export OPENAI_API_KEY="$OPENAI_API_KEY"
export GEMINI_API_KEY="$GEMINI_API_KEY"
ENVFILE

cat > /etc/profile.d/ai-terminal.sh << 'PROFILE'
# AI Terminal environment - načíst proměnné
if [ -f /etc/ai-terminal.env ]; then
    source /etc/ai-terminal.env
fi

export PS1='\[\033[1;32m\]ai-terminal\[\033[0m\]:\[\033[1;34m\]\w\[\033[0m\]\$ '

# Aliasy pro pohodli
alias ll='ls -la'
alias la='ls -A'
alias l='ls -CF'
alias cls='clear'
alias ha='ha-cli'

# Welcome message
echo ""
echo "==========================================="
echo "  AI TERMINAL PRO HOME ASSISTANT v0.5.8"
echo "==========================================="
echo ""
echo "AI Asistenti s MCP Home Assistant tools:"
echo "  claude    - Anthropic Claude CLI"
echo "  codex     - OpenAI Codex CLI"
echo "  gemini    - Google Gemini CLI (bez MCP)"
echo ""
echo "MCP nastroje (claude/codex):"
echo "  ha_get_states, ha_call_service, config_add_automation..."
echo ""
echo "Nastroje:"
echo "  ha-cli       - Home Assistant CLI"
echo "  mqtt-inspect - MQTT inspector"
echo "  ai-help      - Napoveda"
echo ""
echo "Mod: $AI_MODE | Napoveda: ai-help"
echo ""
PROFILE

# -----------------------------------------------------------------------------
# Spusteni ttyd (webovy terminal)
# -----------------------------------------------------------------------------
echo "[INFO] Spoustim webovy terminal na portu 7681..."

# ttyd parametry:
#   -p 7681      - port
#   -W           - zapisovatelny terminal
#   -t fontSize=14
#   -t theme={"background":"#1e1e1e"}

# Spustit ttyd s explicitnim predanim promennych
exec env \
    SUPERVISOR_TOKEN="$SUPERVISOR_TOKEN" \
    HA_TOKEN="$SUPERVISOR_TOKEN" \
    AI_MODE="$AI_MODE" \
    ALLOWED_FILES="$ALLOWED_FILES" \
    BACKUP_DIR="$BACKUP_DIR" \
    MQTT_BROKER="$MQTT_BROKER" \
    MQTT_PORT="$MQTT_PORT" \
    MQTT_USER="$MQTT_USER" \
    MQTT_PASSWORD="$MQTT_PASSWORD" \
    ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
    OPENAI_API_KEY="$OPENAI_API_KEY" \
    GEMINI_API_KEY="$GEMINI_API_KEY" \
    ttyd \
    -p 7681 \
    -W \
    -t 'fontSize=14' \
    -t 'fontFamily=monospace' \
    -t 'theme={"background":"#1a1a2e","foreground":"#eaeaea","cursor":"#00ff00"}' \
    bash --login
