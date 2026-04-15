FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV ARDUINO_DATA_DIR=/usr/local/share/arduino

# Instala dependências de sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    python3-serial \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Instala o Arduino CLI
RUN curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh

# Cria o diretório de dados e instala os cores (Uno/Mega e ESP8266)
RUN mkdir -p $ARDUINO_DATA_DIR && \
    arduino-cli config init && \
    arduino-cli config add board_manager.additional_urls https://arduino.esp8266.com/stable/package_esp8266com_index.json && \
    arduino-cli core update-index && \
    arduino-cli core install arduino:avr && \
    arduino-cli core install esp8266:esp8266

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
