# Usa uma imagem Python leve como base
FROM python:3.10-slim

# Evita que o Python gere arquivos .pyc e permite logs em tempo real
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Instala dependências do sistema necessárias para o arduino-cli e compilação
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Instala o Arduino CLI na pasta /usr/local/bin
RUN curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh

# Configura o Arduino CLI: atualiza o índice e instala o core AVR (Uno, Mega, Nano)
RUN arduino-cli core update-index && \
    arduino-cli core install arduino:avr

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Copia o requirements.txt primeiro (para aproveitar o cache do Docker)
COPY requirements.txt .

# Instala as dependências do Python (FastAPI, Uvicorn, etc)
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante dos arquivos do projeto (incluindo o main.py)
COPY . .

# Expõe a porta que o FastAPI vai rodar
EXPOSE 8000

# Comando para iniciar a API usando Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
