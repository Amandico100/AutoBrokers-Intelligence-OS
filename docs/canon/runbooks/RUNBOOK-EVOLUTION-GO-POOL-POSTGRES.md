# Runbook — pool Postgres do Evolution Go

## Topologia canônica

O Evolution Go usa dois bancos separados:

- `evogo_auth`: instâncias, autenticação e configuração;
- `evogo_users`: sessões e dados do cliente WhatsApp.

Ambos pertencem ao papel dedicado `evolution_go`, sem superusuário, sem
`CREATEDB` e sem `CREATEROLE`. O papel possui limite de conexões e timeouts de
sessão/statement/lock. O serviço não usa o papel administrativo do Supabase.

## Linha de base

Com uma réplica ociosa e sem pareamento ativo, a linha de base observada é:

| Banco | Papel | Conexões esperadas |
| --- | --- | ---: |
| `evogo_auth` | `evolution_go` | 1 |
| `evogo_users` | `evolution_go` | 2 |
| **Total** |  | **3** |

Picos curtos durante QR, HistorySync e mídia são aceitáveis; crescimento
contínuo ou `too many clients already` não é.

## Configuração do serviço

- uma réplica;
- conexões separadas em `POSTGRES_AUTH_DB` e `POSTGRES_USERS_DB`;
- limites de pool explícitos para auth/users;
- `CONNECT_ON_STARTUP=false`;
- `QRCODE_MAX_COUNT=5`;
- limites de CPU e memória definidos;
- diretório `/app/logs` pertencente ao usuário não-root `evolution`.

## Diagnóstico

1. Consulte a versão e saúde em `/server/ok`.
2. Conte sessões por banco, usuário e estado em `pg_stat_activity`.
3. Confirme que não existem conexões do provider usando `postgres` ou outro
   papel administrativo.
4. Confira reinícios da tarefa, uso de memória, erros de ownership e mensagens
   `too many clients already`.
5. Compare o total ocioso com a linha de base acima após 60 segundos.

Não copie connection strings, senhas ou chaves para tickets e relatórios.

## Recuperação segura

1. Não gere novos QRs durante o diagnóstico.
2. Corrija primeiro ownership de schema, tabelas e sequências nos dois bancos;
   apenas trocar o dono do banco não é suficiente para o GORM.
3. Confirme que os ambientes salvos e os ambientes da tarefa em execução são
   iguais em nomes, sem revelar valores.
4. Reinicie uma única vez o serviço para aplicar ambiente salvo.
5. Aguarde saúde estável e retorne à linha de base.
6. Só então faça uma tentativa técnica de QR e deixe-a expirar.

Se o QR expirado disparar nova conexão, pare o teste: a cerimônia deve terminar
em `qr_expired` e exigir ação explícita para tentar novamente.
