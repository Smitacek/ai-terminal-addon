# AI Agenti pro Home Assistant - Analýza a Plán

## 1. CO VŠECHNO LZE V HA DĚLAT

### 1.1 YAML Konfigurace (soubory v /config)

| Soubor | Účel | Příklady použití |
|--------|------|------------------|
| `configuration.yaml` | Hlavní konfigurace | Integrace, základní nastavení |
| `automations.yaml` | Automatizace | Pravidla trigger → action |
| `scripts.yaml` | Skripty | Sekvence akcí |
| `scenes.yaml` | Scény | Přednastavené stavy entit |
| `sensors.yaml` | Template senzory | Vlastní senzory z šablon |
| `binary_sensors.yaml` | Binární senzory | On/off stavy |
| `switches.yaml` | Přepínače | Template switches |
| `input_*.yaml` | Pomocné entity | input_boolean, input_number, input_select |
| `groups.yaml` | Skupiny | Seskupení entit |
| `customize.yaml` | Úpravy entit | Ikony, friendly names |
| `packages/*.yaml` | Balíčky | Modulární konfigurace |

### 1.2 Entity Domény (typy zařízení)

| Doména | Popis | Služby |
|--------|-------|--------|
| `light` | Světla | turn_on, turn_off, toggle, brightness |
| `switch` | Přepínače | turn_on, turn_off, toggle |
| `sensor` | Senzory | - (pouze čtení) |
| `binary_sensor` | Binární senzory | - (pouze čtení) |
| `climate` | Klimatizace/topení | set_temperature, set_hvac_mode |
| `cover` | Rolety/garážová vrata | open, close, set_position |
| `fan` | Ventilátory | turn_on, turn_off, set_speed |
| `lock` | Zámky | lock, unlock |
| `media_player` | Média | play, pause, volume |
| `vacuum` | Vysavače | start, stop, return_to_base |
| `camera` | Kamery | snapshot, record |
| `alarm_control_panel` | Alarmy | arm, disarm |
| `water_heater` | Bojlery | set_temperature |
| `humidifier` | Zvlhčovače | set_humidity |
| `input_boolean` | Pomocné bool | turn_on, turn_off |
| `input_number` | Pomocná čísla | set_value |
| `input_select` | Pomocný výběr | select_option |
| `input_text` | Pomocný text | set_value |
| `input_datetime` | Pomocné datum/čas | set_datetime |
| `automation` | Automatizace | trigger, turn_on, turn_off |
| `script` | Skripty | turn_on (spustit) |
| `scene` | Scény | turn_on (aktivovat) |
| `person` | Osoby | - (tracking) |
| `zone` | Zóny | - (geolokace) |
| `device_tracker` | Sledování zařízení | - (přítomnost) |
| `notify` | Notifikace | send_message |
| `tts` | Text-to-speech | speak |
| `button` | Tlačítka | press |
| `number` | Číselné hodnoty | set_value |
| `select` | Výběr | select_option |
| `update` | Aktualizace | install |

### 1.3 Automatizace - Triggery

| Trigger | Popis | Příklad |
|---------|-------|---------|
| `state` | Změna stavu entity | Světlo se zapne |
| `numeric_state` | Číselná hodnota překročí práh | Teplota > 25°C |
| `time` | Konkrétní čas | V 7:00 |
| `time_pattern` | Časový vzor | Každých 5 minut |
| `sun` | Východ/západ slunce | Při západu |
| `zone` | Vstup/výstup ze zóny | Příchod domů |
| `device` | Událost zařízení | Stisk tlačítka |
| `mqtt` | MQTT zpráva | Topic update |
| `webhook` | HTTP webhook | Externí volání |
| `event` | HA událost | call_service |
| `template` | Šablona je true | Vlastní podmínka |
| `calendar` | Kalendářní událost | Začátek schůzky |
| `tag` | NFC/RFID tag | Přiložení tagu |
| `persistent_notification` | Notifikace | Nová notifikace |
| `sentence` | Hlasový příkaz | "Zapni světla" |

### 1.4 Automatizace - Podmínky (Conditions)

| Condition | Popis |
|-----------|-------|
| `state` | Entita má konkrétní stav |
| `numeric_state` | Číselná hodnota v rozsahu |
| `time` | Čas v rozsahu |
| `sun` | Před/po východu/západu |
| `zone` | Entita je v zóně |
| `template` | Vlastní šablona |
| `and` / `or` / `not` | Logické operátory |
| `device` | Stav zařízení |

### 1.5 Automatizace - Akce (Actions)

| Action | Popis |
|--------|-------|
| `service` | Volání služby |
| `delay` | Pauza |
| `wait_template` | Čekání na podmínku |
| `wait_for_trigger` | Čekání na trigger |
| `repeat` | Opakování |
| `choose` | If/else větve |
| `condition` | Podmínka uprostřed |
| `event` | Vyvolání události |
| `variables` | Nastavení proměnných |
| `stop` | Zastavení |
| `parallel` | Paralelní akce |
| `sequence` | Sekvence akcí |

### 1.6 REST API Endpointy

| Endpoint | Metoda | Popis |
|----------|--------|-------|
| `/api/` | GET | API status |
| `/api/config` | GET | Konfigurace |
| `/api/states` | GET | Všechny stavy |
| `/api/states/<entity_id>` | GET/POST | Stav entity |
| `/api/services` | GET | Seznam služeb |
| `/api/services/<domain>/<service>` | POST | Volání služby |
| `/api/history/period` | GET | Historie |
| `/api/logbook` | GET | Logbook |
| `/api/error_log` | GET | Error log |
| `/api/config/core/check_config` | POST | Validace konfigurace |
| `/api/template` | POST | Render šablony |

---

## 2. NÁVRH AI AGENTŮ

### Agent 1: `automation-agent` - Automatizace
**Účel:** Vytváření a úprava automatizací

**Schopnosti:**
- Generování YAML pro automations.yaml
- Všechny typy triggerů (state, time, sun, zone, device...)
- Podmínky (conditions)
- Akce (actions) včetně choose, repeat, parallel
- Šablony (templates) v triggerech a akcích

**Příklady promptů:**
```
"Vytvoř automatizaci která zapne světla v obýváku při západu slunce"
"Když přijdu domů, zapni topení na 22°C"
"Každý den v 7:00 otevři rolety, ale jen ve všední dny"
"Když SOC baterie > 90%, zapni bojler"
```

---

### Agent 2: `entity-agent` - Správa entit
**Účel:** Práce s entitami a jejich stavy

**Schopnosti:**
- Vyhledávání entit podle domény/názvu
- Čtení stavů a atributů
- Volání služeb (turn_on, turn_off, set_*)
- Skupiny entit
- History a statistiky

**Příklady promptů:**
```
"Jaká světla jsou zapnutá?"
"Vypni všechny přepínače v garáži"
"Jaká je aktuální teplota venku?"
"Zobraz historii spotřeby za poslední týden"
```

---

### Agent 3: `sensor-agent` - Template senzory
**Účel:** Vytváření vlastních senzorů

**Schopnosti:**
- Template sensors
- Template binary_sensors
- MQTT senzory
- Statistické senzory
- Utility meter

**Příklady promptů:**
```
"Vytvoř senzor který počítá průměrnou teplotu z 3 teploměrů"
"Senzor pro celkovou spotřebu FVE za měsíc"
"Binární senzor: někdo je doma"
"MQTT senzor pro Shelly zařízení"
```

---

### Agent 4: `script-agent` - Skripty a scény
**Účel:** Komplexní sekvence akcí

**Schopnosti:**
- Scripts s proměnnými
- Scenes
- Sekvence s delay, wait, repeat
- Volání jiných skriptů
- Notifikace

**Příklady promptů:**
```
"Skript pro ranní rutinu: rolety, kávovar, světla"
"Scéna 'Film' - ztlumit světla, zapnout TV"
"Skript pro zavlažování s čekáním mezi zónami"
```

---

### Agent 5: `mqtt-agent` - MQTT integrace
**Účel:** MQTT discovery a konfigurace

**Schopnosti:**
- Skenování MQTT topiců
- MQTT discovery konfigurace
- Manual MQTT sensors/switches
- Debug MQTT zpráv

**Příklady promptů:**
```
"Najdi všechny MQTT zařízení"
"Vytvoř MQTT senzor pro topic shellies/temp"
"Nastav MQTT discovery pro Tasmota zařízení"
```

---

### Agent 6: `energy-agent` - Energetický management
**Účel:** FVE, baterie, spotřeba

**Schopnosti:**
- Energy dashboard konfigurace
- Utility meters
- Automatizace pro FVE
- Statistiky spotřeby/výroby

**Příklady promptů:**
```
"Nastav energy dashboard pro FVE systém"
"Automatizace: při přebytku FVE zapni bojler"
"Vytvoř denní/měsíční statistiky spotřeby"
```

---

### Agent 7: `debug-agent` - Diagnostika
**Účel:** Hledání a oprava chyb

**Schopnosti:**
- Analýza error logů
- Validace konfigurace
- Kontrola automatizací
- Trace automatizací

**Příklady promptů:**
```
"Proč nefunguje automatizace pro světla?"
"Zkontroluj chyby v konfiguraci"
"Proč se entita hlásí jako unavailable?"
```

---

### Agent 8: `helper-agent` - Pomocné entity
**Účel:** Input helpers a groups

**Schopnosti:**
- input_boolean, input_number, input_select, input_text, input_datetime
- Groups
- Timers
- Counters

**Příklady promptů:**
```
"Vytvoř input_boolean pro režim dovolené"
"Input_number pro cílovou teplotu 15-30°C"
"Skupina všech světel v obýváku"
```

---

## 3. STRUKTURA NÁPOVĚDY

### 3.1 Interaktivní nápověda v terminálu

```bash
# Hlavní nápověda
ai-help

# Nápověda pro konkrétní oblast
ai-help automations
ai-help entities
ai-help mqtt
ai-help energy

# Příklady
ai-help examples automations
ai-help examples sensors
```

### 3.2 Kontextová nápověda pro Claude/Gemini

Soubor `/app/prompts/ha_context.md` obsahující:
- Seznam všech domén a služeb
- Příklady YAML pro každý typ
- Best practices
- Časté chyby a řešení

### 3.3 Quick reference karty

```
/config/ai_docs/
├── triggers.md      # Všechny triggery s příklady
├── conditions.md    # Všechny podmínky
├── actions.md       # Všechny akce
├── services.md      # Služby podle domény
├── templates.md     # Jinja2 šablony
└── examples/
    ├── lighting.yaml
    ├── climate.yaml
    ├── security.yaml
    └── energy.yaml
```

---

## 4. IMPLEMENTAČNÍ PLÁN

### Fáze 1: Základní agenti (v0.3.0)
- [ ] `automation-agent` - nejčastější use case
- [ ] `entity-agent` - práce se stavy
- [ ] Rozšíření `ai-config` o kontextovou nápovědu

### Fáze 2: Specializovaní agenti (v0.4.0)
- [ ] `sensor-agent`
- [ ] `script-agent`
- [ ] `mqtt-agent`

### Fáze 3: Pokročilí agenti (v0.5.0)
- [ ] `energy-agent`
- [ ] `debug-agent`
- [ ] `helper-agent`

### Fáze 4: Dokumentace a nápověda (průběžně)
- [ ] Interaktivní `ai-help` příkaz
- [ ] Kontextové prompty pro AI
- [ ] Příklady pro každou oblast

---

## 5. PŘÍKLAD IMPLEMENTACE AGENTA

```python
# /app/agents/automation_agent.py

class AutomationAgent:
    """Agent pro vytváření HA automatizací."""

    SYSTEM_PROMPT = """
    Jsi expert na Home Assistant automatizace.

    PRAVIDLA:
    1. Vždy generuj validní YAML
    2. Používej entity_id které existují
    3. Přidej smysluplné alias a description
    4. Použij vhodné triggery pro daný use case

    TRIGGERY: state, numeric_state, time, sun, zone, device, mqtt...
    CONDITIONS: state, numeric_state, time, sun, zone, template...
    ACTIONS: service, delay, wait, choose, repeat, condition...

    FORMÁT ODPOVĚDI:
    ```yaml
    # FILE: automations.yaml (append)
    - id: unique_id_here
      alias: "Popisný název"
      description: "Co automatizace dělá"
      triggers:
        - ...
      conditions:
        - ...
      actions:
        - ...
    ```
    """

    def __init__(self, ha_interface, claude_client):
        self.ha = ha_interface
        self.claude = claude_client

    def generate(self, user_request: str) -> str:
        # Získání kontextu
        entities = self.ha.get_entities()
        current_automations = self.read_automations()

        # Sestavení promptu
        context = f"""
        DOSTUPNÉ ENTITY:
        {self.format_entities(entities)}

        EXISTUJÍCÍ AUTOMATIZACE:
        {self.format_automations(current_automations)}
        """

        # Volání Claude
        response = self.claude.chat(
            system_prompt=self.SYSTEM_PROMPT + context,
            user_message=user_request
        )

        return response
```

---

## 6. CLI PŘÍKAZY PRO AGENTY

```bash
# Automatizace
ai-auto "zapni světla při západu slunce"
ai-auto --list                    # seznam automatizací
ai-auto --enable <id>
ai-auto --disable <id>
ai-auto --trace <id>              # debug

# Entity
ai-entity list light              # seznam světel
ai-entity state sensor.temp       # stav entity
ai-entity call light.turn_on light.obyvak --brightness 50

# Senzory
ai-sensor create "průměrná teplota"
ai-sensor mqtt "shelly/temp"

# Skripty
ai-script "ranní rutina"
ai-scene create "Film"

# MQTT
ai-mqtt scan
ai-mqtt subscribe "shellies/#"
ai-mqtt discover

# Energie
ai-energy setup
ai-energy stats today

# Debug
ai-debug config
ai-debug automation <id>
ai-debug entity <entity_id>

# Nápověda
ai-help
ai-help automations
ai-help triggers
ai-help --examples
```

---

## 7. ZDROJE

- [Automation YAML](https://www.home-assistant.io/docs/automation/yaml/)
- [Configuration](https://www.home-assistant.io/docs/configuration/)
- [Triggers](https://www.home-assistant.io/docs/automation/trigger)
- [Conditions](https://www.home-assistant.io/docs/automation/condition/)
- [Actions](https://www.home-assistant.io/docs/automation/action/)
- [REST API](https://developers.home-assistant.io/docs/api/rest/)
- [Entity Domains](https://www.home-assistant.io/docs/configuration/entities_domains/)
- [Scripts](https://www.home-assistant.io/integrations/script/)
- [Template](https://www.home-assistant.io/integrations/template/)
