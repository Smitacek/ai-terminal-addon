# AI Terminal Add-on pro Home Assistant
# Plnohodnotny webovy terminal s Claude CLI a AI agentem

ARG BUILD_FROM
FROM ${BUILD_FROM}

# Nastaveni prostredi
ENV LANG=C.UTF-8
ENV TERM=xterm-256color

# Instalace systemovych zavislosti
RUN apk add --no-cache \
    bash \
    bash-completion \
    curl \
    wget \
    jq \
    git \
    openssh-client \
    vim \
    nano \
    ttyd \
    nodejs \
    npm \
    python3 \
    py3-pip \
    py3-yaml \
    py3-requests \
    mosquitto-clients \
    ca-certificates \
    && rm -rf /var/cache/apk/*

# Build zavislosti pro nativni moduly (potrebuje Gemini CLI)
RUN apk add --no-cache --virtual .build-deps \
    build-base \
    python3-dev \
    && npm install -g @anthropic-ai/claude-code @google/gemini-cli \
    && npm cache clean --force \
    && apk del .build-deps

# Vytvoreni virtualniho prostredi pro Python zavislosti
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Instalace Python zavislosti
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

# Kopirovani aplikacnich souboru
COPY rootfs /
COPY app /app

# Nastaveni prav pro spustitelne soubory
RUN chmod +x /usr/local/bin/* \
    && chmod +x /run.sh \
    && chmod +x /etc/services.d/ttyd/run

# Pracovni adresar
WORKDIR /config

# Exposed port pro ttyd
EXPOSE 7681

# Spusteni
CMD ["/run.sh"]
