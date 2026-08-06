FROM python:3.11-slim

WORKDIR /app

# Instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    python -m spacy download en_core_web_lg

# Copiar código
COPY . .

# Qual commit está nesta imagem. Aditivo de propósito: sem `--build-arg
# GIT_COMMIT=...` o valor fica vazio e o /health cai no "nao-injetado" de sempre
# — exatamente o comportamento de hoje. Nenhum build pode quebrar por isto.
#
# Não é a fonte principal: o /health prova o que está no ar pelos SINAIS de
# capacidade, que não dependem de o builder lembrar de passar variável. Este
# campo é a confirmação barata quando alguém lembra.
ARG GIT_COMMIT=""
ENV GIT_COMMIT=${GIT_COMMIT}

# Porta
EXPOSE 8000

# Comando
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
