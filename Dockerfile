FROM python:3.10-slim

# Instala curl e Arduino CLI
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh && \
    apt-get clean

# Prepara os cores do Arduino Uno
RUN arduino-cli core update-index && \
    arduino-cli core install arduino:avr

WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
