FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Instala dependências essenciais
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    python3-serial \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Instala Arduino CLI
RUN curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh

# Configura as URLs ANTES de baixar os cores
RUN arduino-cli config init && \
    arduino-cli config add board_manager.additional_urls https://arduino.esp8266.com/stable/package_esp8266com_index.json && \
    arduino-cli config add board_manager.additional_urls https://github.com/stm32duino/Board_ManagerData/raw/main/package_st_index.json

# Atualiza o índice (Passo isolado para evitar erro)
RUN arduino-cli core update-index

# Instala os cores um por um (Isso evita timeout no Easypanel)
RUN arduino-cli core install arduino:avr
RUN arduino-cli core install esp8266:esp8266
RUN arduino-cli core install stm32:stm32

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
