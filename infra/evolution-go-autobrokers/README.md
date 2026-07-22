# Evolution Go AutoBrokers

Imagem derivada e reproduzível do Evolution Go usada no pareamento WhatsApp do AutoBrokers.

## Origem pinada

- upstream: `evolution-foundation/evolution-go`
- commit: ver `UPSTREAM_COMMIT`
- versão derivada: ver `VERSION`

O build busca exatamente o commit pinado, verifica o SHA antes de alterar o código e aplica, em ordem, os quatro patches auditáveis de `patches/`.

## Garantias dos patches

1. Um único `sqlstore.Container` compartilha o pool de autenticação durante todo o processo; tentativas de QR não criam novos pools.
2. `QRTimeout` e `LoggedOut` são terminais. Nova tentativa exige uma chamada explícita de conexão.
3. Eventos passkey entram no bucket `QRCODE`, o polling expõe TTL/erro e o endpoint público aceita CORS apenas de `https://web.whatsapp.com`.
4. Troca ou queda do socket invalida o challenge anterior com `passkey_socket_restarted`.

## Build

Use `infra/evolution-go-autobrokers` como contexto e caminho do Dockerfile no EasyPanel:

```bash
docker build \
  --build-arg UPSTREAM_COMMIT="$(cat UPSTREAM_COMMIT)" \
  --build-arg VERSION="$(cat VERSION)" \
  -t evolution-go:0.7.2-autobrokers.1 .
```

O próprio build executa os testes Go dos pacotes alterados antes de produzir o binário Linux com CGo.

## Testes de contrato

Os testes em `tests/` recebem como argumento a raiz de um checkout do upstream já com os patches aplicados:

```bash
tests/test_qr_timeout_no_restart.sh /src/evolution-go
tests/test_logged_out_terminal.sh /src/evolution-go
python tests/test_db_pool_stability.py /src/evolution-go
python tests/test_passkey_contract.py /src/evolution-go
```

## Variáveis operacionais

```text
CONNECT_ON_STARTUP=false
QRCODE_MAX_COUNT=5
PASSKEY_PUBLIC_URL=https://<host-publico-evolution-go>
WEBHOOK_FILES=true
GIN_MODE=release
POSTGRES_MAX_OPEN_CONNS=20
POSTGRES_MAX_IDLE_CONNS=5
POSTGRES_CONN_MAX_LIFETIME_MINUTES=30
POSTGRES_CONN_MAX_IDLE_TIME_MINUTES=5
```

`GET /server/ok` retorna o estado e a versão derivada sem expor segredos.
