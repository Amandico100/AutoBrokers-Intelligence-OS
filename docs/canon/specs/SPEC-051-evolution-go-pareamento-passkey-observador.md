# SPEC-051 — Evolution Go estável, pareamento QR/passkey e ativação segura do Observador

**Status:** pronta para execução pelo Codex, após leitura integral
**Prioridade:** P0
**Escopo:** Evolution Go + pareamento WhatsApp + modo Observador + validação da Central de Agentes
**Repositório oficial:** `Amandico100/AutoBrokers-Intelligence-OS`
**Branch de execução:** `feat/spec-051-evolution-go-pairing`
**Base obrigatória:** `origin/main` no commit mais recente
**Objetivo de negócio:** parear primeiro o WhatsApp Business técnico do founder, depois Resulta e Autofleet, sem respostas automáticas, para capturar as conversas de trabalho, construir rotas e alimentar a inteligência do AutoBrokers.

---

## 1. Resultado final obrigatório

Ao concluir esta SPEC:

1. O modal nunca ficará preso indefinidamente em `Preparando...`.
2. O Evolution Go não poderá reiniciar clientes de QR em loop nem vazar pools PostgreSQL.
3. O QR deverá aparecer de forma estável ou a tela deverá mostrar um erro terminal claro.
4. Se a conta exigir passkey, o AutoBrokers deverá detectar e abrir um fluxo guiado de chave de acesso.
5. Resulta e Autofleet terão instâncias separadas e isolamento por `company_id + purpose`.
6. As integrações piloto usarão `purpose=observer`, sem caminho de envio.
7. O Observador capturará mensagens de seguradoras e clientes conforme o escopo autorizado.
8. O Tecelão, a Sentinela de Rotas, o Espelho de Atendimento, o Destilador e as memórias dos agentes continuarão funcionando de forma orquestrada.
9. O sistema não enviará respostas automáticas durante a fase de observação.
10. A implantação será validada primeiro com o WhatsApp Business técnico do founder, depois Resulta, depois Autofleet.
11. Toda alteração será testada, commitada, enviada à `main` e implantada em Web, API e Evolution Go.
12. A entrega final terá evidências de código, testes, deploy e funcionamento real.

---

## 2. Contexto comprovado

### 2.1 Incidente atual

A Evolution Go 0.7.2 gerou cinco QRs, atingiu `QRTimeout`, executou `LoggedOut`, reiniciou o cliente e voltou a gerar QRs. Esse ciclo se repetiu até o PostgreSQL começar a responder `too many clients already`.

A causa é compatível com os issues upstream:

- Evolution Go #106;
- Evolution Go #109;
- Evolution Go #112;
- Evolution Go #118.

A imagem atual do EasyPanel usa:

`evoapicloud/evolution-go:latest`

Os logs confirmam que a imagem executada é a versão 0.7.2.

O serviço usa:

- um PostgreSQL dedicado;
- uma réplica;
- nenhum volume local;
- `CONNECT_ON_STARTUP=true`;
- `WEBHOOKFILES=true`, nome incorreto;
- ausência de `PASSKEY_PUBLIC_URL`;
- imagem não pinada;
- recursos sem limite explícito.

A ausência de volume local não é um bloqueador porque sessão/licença vivem no PostgreSQL. Não criar volume apenas para “resolver” o incidente.

### 2.2 Estado do AutoBrokers

Web e API implantam a branch `main`.

O código atual:

- já usa Evolution Go como provider principal;
- já possui integração multiempresa;
- já cria integrações por corretora;
- já possui Observador, Espelho de Atendimento, Tecelão, Sentinela de Rotas, Destilador e memória por agente;
- já agenda os trabalhos de fundo;
- já possui modo de observação com agente de atendimento desligado;
- ainda descarta os campos de passkey;
- ainda aceita falso sucesso do `/instance/connect`;
- ainda silencia erros de QR no frontend;
- ainda não possui timeout e máquina de estados completa;
- ainda não processa mídia do GO de forma completa.

---

## 3. Decisões arquiteturais obrigatórias

### D1 — Evolution Go continua como provider principal

Não retornar para Evolution API clássica.

Não migrar para Meta Cloud API nesta SPEC.

Manter a abstração de provider preparada para uma alternativa oficial futura.

### D2 — Build próprio pinado

Parar de usar `latest`.

Criar um build AutoBrokers baseado exatamente no upstream Evolution Go 0.7.2, commit:

`9337afc47e10b86cc896a6f432240e40fee95dd1`

Versão final:

`0.7.2-autobrokers.1`

O build deve aplicar patches mínimos, auditáveis e cobertos por testes.

### D3 — QR expirado é terminal

Depois que o limite de QR for atingido:

- encerrar o cliente;
- fechar recursos;
- emitir `QRTimeout`;
- não reiniciar automaticamente;
- não abrir outro pool;
- aguardar ação explícita do usuário.

### D4 — LoggedOut é terminal

`LoggedOut` não pode provocar loop de reconexão.

Deve virar:

`re_pair_required`

### D5 — Estado transitório no Redis

Não criar uma grande arquitetura nova de tabelas nesta etapa.

Usar Redis para tentativa transitória de pareamento:

`whatsapp:pairing:{company_id}:{purpose}`

Com:

- `attempt_id`;
- estado;
- timestamps;
- TTL;
- erro normalizado;
- correlation ID;
- campos de QR/passkey;
- lock distribuído.

Persistir no Supabase apenas a integração e o estado operacional final.

### D6 — Observador é mudo

Para Resulta e Autofleet:

- `purpose=observer`;
- nenhum cliente de envio importado pelo Observador;
- agente de atendimento desligado durante a fase piloto;
- nenhuma resposta automática;
- nenhuma marcação de leitura;
- nenhum online artificial;
- nenhuma rejeição de chamada.

### D7 — Aprendizado em lote, não mutação por mensagem

Cada mensagem deve ser capturada imediatamente.

O sistema não deve reescrever playbooks oficiais a cada mensagem.

Fluxo correto:

`mensagem → captura → sessão → mapa observado → evidência → draft/alteração → gate → publicação segura`

Mudanças cosméticas podem ser aplicadas apenas após Simulador.

Mudanças estruturais exigem revisão.

Knowledge cards permanecem `pending_review` até aprovação.

### D8 — Passkey sem promessa falsa

Implementar o melhor fluxo suportado pela Evolution Go:

- detectar;
- preservar campos;
- abrir cerimônia;
- orientar;
- acompanhar estados;
- mostrar código;
- confirmar manualmente;
- tratar expiração;
- tratar erro.

Não afirmar no produto que todo passkey será concluído automaticamente.

O upstream possui issue aberto de contas WhatsApp Business presas em `awaiting_confirmation`.

O produto deve detectar esse estado e parar com instrução clara, sem loop.

---

# BLOCO 1 — EVOLUTION GO CORRIGIDO E INFRAESTRUTURA ESTÁVEL

## 4. Criar o build pinado

Criar:

```text
infra/evolution-go-autobrokers/
├── Dockerfile
├── README.md
├── UPSTREAM_COMMIT
├── VERSION
├── patches/
│   ├── 0001-sqlstore-lifecycle.patch
│   ├── 0002-qrtimeout-terminal.patch
│   ├── 0003-passkey-webhook-events.patch
│   └── 0004-passkey-socket-invalidation.patch
└── tests/
    ├── test_qr_timeout_no_restart.sh
    ├── test_logged_out_terminal.sh
    ├── test_db_pool_stability.py
    └── test_passkey_contract.py
```

O Dockerfile deve:

1. usar build multi-stage;
2. clonar o upstream;
3. verificar o commit exato;
4. aplicar `git apply --check`;
5. aplicar os patches;
6. compilar o binário;
7. preservar manager/assets/licença;
8. expor porta 8080;
9. responder `/server/ok`;
10. incluir label com versão e commit upstream.

## 5. Patch de lifecycle PostgreSQL

Modificar o lifecycle para que:

- o `sqlstore.Container` seja retido por instância ou compartilhado de forma controlada;
- o container anterior seja fechado antes de substituição;
- delete/logout/shutdown fechem o container;
- erro ao iniciar cliente feche o container criado;
- reconnect não crie pools abandonados;
- QR timeout não crie um novo pool;
- `LoggedOut` não crie um novo pool.

Adicionar configuração de pool:

```text
POSTGRES_MAX_OPEN_CONNS
POSTGRES_MAX_IDLE_CONNS
POSTGRES_CONN_MAX_LIFETIME_MINUTES
POSTGRES_CONN_MAX_IDLE_TIME_MINUTES
```

Defaults conservadores para o piloto:

```text
MAX_OPEN=20
MAX_IDLE=5
MAX_LIFETIME=30
MAX_IDLE_TIME=5
```

## 6. Patch de QR timeout

Quando chegar ao limite:

```text
qr_ready
→ qr_expired
→ cliente encerrado
→ recursos fechados
→ aguardando ação explícita
```

Remover o comportamento:

```text
QRTimeout
→ kill
→ Restarting client
→ novo QR
→ loop
```

O endpoint de QR deve devolver estado terminal e código normalizado.

## 7. Patch de passkey

### 7.1 Eventos

Adicionar `PasskeyRequest`, `PasskeyConfirmation` e `PasskeyError` ao filtro de webhook, associados ao bucket `QRCODE` ou `CONNECTION`.

Mesmo com o patch, o AutoBrokers continuará usando polling de `/instance/qr` como fonte principal da cerimônia.

### 7.2 Reinício do socket

Se o socket reiniciar durante uma cerimônia:

- invalidar a cerimônia anterior;
- devolver `passkey_expired` ou `passkey_socket_restarted`;
- nunca manter challenge antigo em socket novo.

### 7.3 Diagnóstico

Expor sem segredo:

- versão;
- estágio;
- TTL;
- código de erro;
- `re_pair_required`;
- `provider_unavailable`;
- `db_pool_exhausted`.

Nunca logar token da cerimônia completo.

## 8. EasyPanel do Evolution Go

Alterar o serviço `evolution-go-teste`:

### Fonte

Trocar de `Imagem Docker` para build Git do repositório AutoBrokers:

- repositório oficial;
- branch `main`;
- caminho de build `infra/evolution-go-autobrokers`;
- Dockerfile do diretório.

Não usar `latest`.

### Ambiente

Manter as variáveis existentes e ajustar apenas nomes/estados:

```text
CONNECT_ON_STARTUP=false
QRCODE_MAX_COUNT=5
PASSKEY_PUBLIC_URL=<URL pública atual do Evolution Go>
WEBHOOK_FILES=true
GIN_MODE=release
POSTGRES_MAX_OPEN_CONNS=20
POSTGRES_MAX_IDLE_CONNS=5
POSTGRES_CONN_MAX_LIFETIME_MINUTES=30
POSTGRES_CONN_MAX_IDLE_TIME_MINUTES=5
```

Remover o nome incorreto:

```text
WEBHOOKFILES
```

Não reproduzir segredos em logs, relatório ou commit.

### Healthcheck

Configurar:

```text
GET /server/ok
intervalo: 30s
timeout: 5s
falhas: 3
```

### Recursos

Manter uma réplica.

Definir limites suficientes, sem exagero:

```text
reserva memória: 128 MB
limite memória: 512 MB
reserva CPU: 0.10
limite CPU: 1.00
```

### PostgreSQL

Criar role dedicada para Evolution Go, sem superuser, com limite de conexão.

A role deve ter acesso apenas aos bancos `evogo_auth` e `evogo_users`.

Aplicar um limite coerente com o pool configurado.

Configurar proteção adicional:

```text
idle_session_timeout
statement_timeout
lock_timeout
```

Não alterar ou apagar dados de sessão/licença existentes.

## 9. Recuperação controlada

Depois do novo build pronto:

1. registrar contagem de conexões atual;
2. implantar o Evolution Go corrigido;
3. verificar se conexões antigas caíram;
4. reiniciar o PostgreSQL somente se ainda estiver saturado;
5. validar `/server/ok`;
6. validar licença;
7. validar `/instance/all`;
8. validar que nenhuma instância não pareada inicia sozinha;
9. abrir uma tentativa de QR;
10. deixar expirar uma vez;
11. confirmar:
   - nenhum `Restarting client`;
   - nenhuma segunda cerimônia automática;
   - conexões retornam ao baseline.

---

# BLOCO 2 — PAREAMENTO, MODAL E PASSKEY

## 10. Orquestrador de pareamento

Criar serviço:

```text
backend/app/services/whatsapp/pairing_orchestrator.py
```

Responsabilidades:

- lock por `company_id + purpose`;
- criar `attempt_id`;
- criar/reusar instância corretamente;
- configurar webhook;
- iniciar connect;
- consultar QR/passkey/status;
- normalizar resposta do provider;
- gravar estado transitório em Redis;
- encerrar tentativa;
- cancelar;
- retry explícito;
- reconciliar integração final.

Não criar polling concorrente.

## 11. Máquina de estados

Estados obrigatórios:

```text
idle
preparing_instance
requesting_qr
qr_ready
qr_scanned
authenticating
passkey_required
passkey_challenge
passkey_awaiting_confirmation
passkey_code_available
connecting
connected
already_connected
qr_expired
passkey_expired
passkey_failed
passkey_socket_restarted
re_pair_required
provider_unavailable
db_pool_exhausted
configuration_error
timed_out
recoverable_error
technical_error
cancelled
```

Todo estado deve ter:

- `state`;
- `next_action`;
- `expires_at`;
- `poll_after_ms`;
- `support_ref`;
- erro normalizado, quando aplicável.

## 12. Contrato de API

Implementar ou adaptar:

```text
POST /api/whatsapp-channel/pairing
GET  /api/whatsapp-channel/pairing/{attempt_id}
POST /api/whatsapp-channel/pairing/{attempt_id}/retry
POST /api/whatsapp-channel/pairing/{attempt_id}/cancel
GET  /api/whatsapp-channel/status
GET  /api/admin/whatsapp-channel/diagnostics
```

O backend deve preservar:

```text
QRCode
qrcode
qr
base64
qr_base64
passkeyStage
passkeyOpenUrl
passkeyCode
passkeyError
expiresAt
providerVersion
```

Nunca devolver:

- token de instância;
- global key;
- token completo de cerimônia;
- credencial de webhook;
- string de conexão PostgreSQL.

## 13. Timeouts e polling

### Backend

- timeout de rede por chamada ao GO: 10s;
- deadline total de setup: 30s;
- uma tentativa de connect por attempt;
- backoff apenas para erros realmente transitórios;
- `LoggedOut`, QR expirado e passkey expirada são terminais.

### Next.js

- timeout AbortController: 20s;
- preservar status HTTP e JSON;
- correlation ID;
- não converter todo erro em 500 genérico.

### Frontend

- polling serial;
- nunca `setInterval` com chamadas sobrepostas;
- próxima chamada só depois da anterior concluir;
- encerrar polling em estado terminal;
- TTL total da tentativa: 10 minutos;
- QR expira conforme provider;
- retry somente por botão.

## 14. Modal final

Manter o visual atual, sem redesign completo.

### Estado inicial

Título:

`Conectar WhatsApp da corretora`

Texto:

`Use o número de trabalho que a equipe já utiliza. O celular continuará funcionando normalmente.`

Botão:

`Gerar QR code`

### QR disponível

- QR grande;
- contador;
- instruções de três passos;
- botão `Gerar novo QR` somente após expirar;
- texto informando que o celular continua normal;
- nenhum jargão técnico.

### Passkey detectada

Título:

`O WhatsApp pediu uma confirmação de segurança`

Texto:

`Essa conta exige uma chave de acesso para vincular um novo dispositivo. A confirmação é feita pela própria atendente, com biometria ou bloqueio do celular.`

Ações:

1. `Abrir WhatsApp Web`;
2. `Instalar assistente de pareamento`;
3. `Já instalei — continuar`;
4. exibir estágio;
5. exibir código se existir;
6. exibir contador;
7. botão `Cancelar tentativa`.

Não pedir:

- senha;
- PIN;
- passkey;
- código privado;
- compartilhamento de tela obrigatório.

### Falha passkey

Se ficar em `awaiting_confirmation` por mais de 90 segundos:

- encerrar tentativa;
- invalidar cerimônia;
- não repetir automaticamente;
- mostrar:

`A conta não confirmou a chave de acesso. Não houve alteração no WhatsApp. Use o código de suporte abaixo para continuar com acompanhamento.`

### Erros

Exemplos:

- banco indisponível;
- provider indisponível;
- sessão precisa ser refeita;
- QR expirou;
- configuração incompleta.

Nunca mostrar stack trace.

Nunca mostrar loading infinito.

## 15. Assistente de passkey

Auditar e empacotar o `passkey-helper` da mesma versão/commit upstream.

Criar artefato versionado:

```text
public/tools/passkey-helper-autobrokers-0.7.2-ab1.zip
```

Criar checksum e documentação:

```text
docs/canon/runbooks/RUNBOOK-PASSKEY-WHATSAPP.md
```

A interface deve explicar como instalar no Chrome/Edge em modo assistido.

Adicionar allowlist de origem e CORS estrito para:

```text
https://web.whatsapp.com
```

Não permitir origem genérica.

Não criar bypass de WebAuthn.

## 16. Pairing code

Adicionar opção secundária:

`Conectar usando número`

Somente para:

- câmera com problema;
- acessibilidade;
- QR ilegível.

Deixar explícito:

`Esse método não evita a confirmação por chave de acesso quando o WhatsApp a exige.`

---

# BLOCO 3 — OBSERVADOR, CENTRAL DE AGENTES, TESTES E IMPLANTAÇÃO

## 17. Configuração do piloto

Para o WhatsApp Business técnico, Resulta e Autofleet:

```text
purpose=observer
observer_scope=insurers_and_clients
agent_id=null
```

O agente de atendimento da corretora deve permanecer:

```text
is_active=false
```

O número deve continuar utilizável no celular e no WhatsApp Web existente.

## 18. Garantia de silêncio

Criar teste arquitetural que falha se o módulo Observador importar:

- provider de envio;
- `send_message`;
- `send_text`;
- dispatch;
- ferramentas de escrita do WhatsApp.

Confirmar no E2E:

- nenhuma resposta;
- nenhuma marcação de leitura;
- nenhum `alwaysOnline`;
- nenhuma rejeição de chamada;
- nenhum delete/edit/archive/label.

## 19. Captura de conversas

### Seguradoras

Manter filtro por registry + variáveis `INSURER_CONTACT_*`.

Capturar:

- mensagens recebidas;
- mensagens enviadas pela atendente;
- botões;
- listas;
- formulários;
- `fromMe`;
- `HISTORY_SYNC`;
- estado de conexão.

### Clientes

Quando `observer_scope=insurers_and_clients`:

- capturar chats diretos;
- excluir grupos, status, newsletters e chamadas;
- excluir o próprio número;
- excluir números internos da equipe;
- permitir exclusões por tenant;
- armazenar PII somente nas tabelas de transcript;
- nunca enviar PII ao RAG.

Criar configuração simples de exclusão por tenant, sem bloquear o lançamento.

## 20. Mídia

Nesta SPEC, implementar o mínimo útil sem bloquear pareamento:

### Obrigatório

- registrar tipo;
- mimetype;
- filename;
- caption;
- message ID;
- timestamp;
- remetente;
- tenant;
- status de enriquecimento.

### Áudio

Criar job assíncrono:

- baixar por `/message/downloadmedia`;
- limitar tamanho;
- transcrever com provider já configurado;
- gravar texto derivado;
- apagar temporário;
- falhar sem derrubar webhook.

### Imagem/documento

- download assíncrono;
- storage privado;
- extração via pipeline documental existente;
- derived text associado ao evento;
- sem exposição pública.

A falha de mídia não pode impedir texto e eventos de serem capturados.

## 21. Orquestração dos agentes

Não reescrever a arquitetura existente.

Validar:

### Observador

Captura cada evento imediatamente.

### Tecelão

Converte sessões em mapa observado, preservando:

- ordem;
- escolhas;
- variantes;
- cobertura;
- gaps;
- confiança;
- proveniência.

### Sentinela de Rotas

- cosmético: aplicar somente após Simulador;
- estrutural: alertar e não aplicar;
- nenhuma mudança estrutural automática.

### Espelho de Atendimento

Captura equipe ↔ segurado com PII isolada.

### Destilador

- processa sessões encerradas;
- mascara PII antes da LLM;
- gera playbooks `draft`;
- gera knowledge cards `pending_review`;
- não publica automaticamente.

### Memória por agente

Reconstrução periódica com dados agregados.

### Central de Agentes

Validar:

- heartbeat;
- última execução;
- ações do dia;
- memória;
- status real;
- erro visível quando uma task não executa.

## 22. Frequência de evolução

Captura: imediata.

Durante o piloto:

```text
ATLAS_INCREMENTAL_INTERVAL_MINUTES=15
AGENT_MEMORY_INTERVAL_HOURS=6
```

O incremental deve processar somente sessões novas/alteradas.

Destilador pode manter janela em lote, mas deve possuir botão admin:

`Processar aprendizado agora`

Esse botão:

- processa somente dados novos;
- respeita limites;
- não publica conhecimento;
- retorna relatório.

## 23. Testes obrigatórios

### Provider

1. QR nasce.
2. QR expira.
3. nenhum restart automático.
4. conexões DB voltam ao baseline.
5. dois ciclos manuais não aumentam conexões.
6. `LoggedOut` vira terminal.
7. serviço reinicia sem conectar instância não pareada.
8. serviço reconecta sessão válida de forma controlada.

### Modal

1. timeout;
2. provider 400;
3. backend 502;
4. QR;
5. QR expirado;
6. retry;
7. passkey;
8. passkey expirado;
9. awaiting confirmation;
10. erro técnico;
11. refresh;
12. clique duplo.

### Multi-tenant

1. Resulta não acessa Autofleet.
2. Autofleet não acessa Resulta.
3. QR de uma nunca aparece para outra.
4. webhook resolve tenant correto.
5. eventos e sessões ficam no tenant correto.
6. nenhuma credencial chega ao browser.

### Observador

1. mensagem de seguradora recebida;
2. mensagem da atendente enviada pelo celular;
3. botão/lista;
4. cliente direto;
5. grupo descartado;
6. status descartado;
7. áudio;
8. imagem;
9. documento;
10. HistorySync;
11. nenhuma resposta do sistema.

### Agentes

1. heartbeat Observador;
2. heartbeat Espelho;
3. Tecelão cria mapa observado;
4. Sentinela classifica drift;
5. mudança estrutural não é publicada;
6. Destilador gera draft;
7. card fica pending review;
8. memória dos agentes é atualizada.

## 24. Teste com o WhatsApp Business técnico

Depois do deploy, o Codex deve parar e pedir apenas:

`Founder, abra o modal e escaneie este QR com seu WhatsApp Business técnico.`

Uma tentativa por vez.

Não gerar tentativas automáticas sucessivas.

Se aparecer aviso de segurança do WhatsApp, a tela deve explicar que a vinculação está sendo feita pelo próprio AutoBrokers e mostrar o domínio/origem esperada.

Se aparecer passkey:

1. seguir fluxo guiado;
2. registrar cada estágio;
3. não repetir em loop;
4. se travar, gerar relatório de diagnóstico;
5. preservar a conta e encerrar tentativa.

Critérios:

- conectado;
- celular continua normal;
- nenhuma resposta automática;
- mensagem de teste capturada;
- banco e heartbeats confirmados.

## 25. Resulta

Somente depois do teste técnico verde:

1. gerar QR;
2. atendente escaneia;
3. validar conexão;
4. validar mensagem inbound;
5. validar mensagem `fromMe`;
6. validar Observador;
7. validar Espelho;
8. validar isolamento;
9. observar estabilidade por 30 minutos;
10. verificar conexões DB.

## 26. Autofleet

Somente após Resulta estável:

1. repetir o fluxo;
2. não interromper Resulta;
3. validar isolamento cruzado;
4. validar dois números simultâneos;
5. verificar conexões DB;
6. confirmar Central de Agentes.

---

## 27. Arquivos AutoBrokers que provavelmente serão alterados

```text
components/vault/WhatsAppChannelCard.tsx
components/vault/WhatsAppPairingFlow.tsx
components/vault/PairingStateView.tsx
app/api/dashboard/whatsapp-channel/route.ts
backend/app/api/whatsapp_channel.py
backend/app/api/webhook.py
backend/app/services/whatsapp/pairing_orchestrator.py
backend/app/services/whatsapp/providers/evolution_go.py
backend/app/services/whatsapp/integration_secrets.py
backend/app/services/atlas/observer_intake.py
backend/app/services/atlas/attendance_capture.py
backend/app/services/atlas/history_ingest.py
backend/app/tasks/buffer_processor.py
backend/app/core/heartbeat.py
```

Adicionar testes sem apagar os existentes.

## 28. Documentação obrigatória

Criar:

```text
docs/canon/specs/SPEC-051-evolution-go-pareamento-passkey-observador.md
docs/canon/runbooks/RUNBOOK-PAREAMENTO-WHATSAPP-CORRETORA.md
docs/canon/runbooks/RUNBOOK-PASSKEY-WHATSAPP.md
docs/canon/runbooks/RUNBOOK-EVOLUTION-GO-POOL-POSTGRES.md
docs/canon/reports/SPEC-051-IMPLEMENTATION-REPORT.md
```

Atualizar o índice canônico.

Corrigir a contradição documental que afirma que WhatsApp Business nunca pareia.

A regra correta:

`WhatsApp Business pode parear normalmente por QR. Algumas contas podem exigir passkey por decisão server-side.`

---

## 29. Critérios de aceite

A SPEC só termina quando:

- [ ] imagem não usa `latest`;
- [ ] versão mostra `0.7.2-autobrokers.1`;
- [ ] QR aparece;
- [ ] QR expirado não reinicia;
- [ ] pool fica estável;
- [ ] `too many clients already` não reaparece;
- [ ] modal nunca fica infinito;
- [ ] erro aparece de forma humana;
- [ ] passkey é detectado;
- [ ] helper está disponível;
- [ ] TTL é respeitado;
- [ ] Resulta e Autofleet estão isoladas;
- [ ] Observador é mudo;
- [ ] mensagens de seguradora e cliente são capturadas;
- [ ] mídias geram evento e enriquecimento assíncrono;
- [ ] Tecelão produz mapa;
- [ ] Sentinela não auto-aplica estrutural;
- [ ] Destilador produz draft;
- [ ] cards não publicam sem aprovação;
- [ ] Central mostra heartbeat e memória;
- [ ] seu WhatsApp Business técnico foi testado;
- [ ] Resulta foi pareada;
- [ ] Autofleet foi pareada ou está liberada para pareamento sem bloqueador técnico;
- [ ] relatório final contém evidências.

---

## 30. Forma de execução pelo Codex

O Codex deve executar em três blocos contínuos:

### Bloco A — Provider e infraestrutura

- implementar build;
- aplicar patches;
- testar;
- implantar Evolution Go;
- recuperar pool;
- comprovar estabilidade.

### Bloco B — Produto e passkey

- backend;
- proxy;
- modal;
- estados;
- helper;
- testes;
- deploy Web/API.

### Bloco C — Observador e validação

- validar/ajustar captura;
- validar agentes;
- executar E2E técnico;
- Resulta;
- Autofleet;
- relatório.

Não criar dezenas de ondas intermediárias.

Não parar para pedir ao founder comandos de terminal.

Só parar quando houver uma ação física inevitável:

- escanear QR;
- autenticar passkey;
- confirmar pareamento.

---

## 31. Prompt de início para o Codex

Você está autorizado a executar integralmente a SPEC-051.

Antes de alterar:

1. leia a SPEC inteira;
2. confirme repositório, branch, commit e worktree;
3. preserve qualquer trabalho existente;
4. crie a branch `feat/spec-051-evolution-go-pairing`;
5. implemente os três blocos sem expandir o escopo.

Você pode:

- editar código;
- criar testes;
- executar testes;
- criar build do Evolution Go;
- usar o acesso já disponível ao EasyPanel;
- alterar variáveis necessárias sem imprimir seus valores;
- executar SQL técnico no PostgreSQL dedicado;
- implantar Evolution Go, API e Web;
- criar commits;
- fazer push;
- integrar em `main` depois dos testes;
- validar endpoints reais.

Você não pode:

- enviar mensagens reais automaticamente;
- ativar agente de atendimento;
- apagar dados;
- misturar Resulta e Autofleet;
- executar loops de pareamento;
- expor credenciais;
- declarar passkey resolvido sem teste real;
- converter WhatsApp Business para Messenger;
- migrar para Meta Cloud API nesta SPEC.

Entregue ao final:

1. causa resolvida;
2. diff por arquivo;
3. testes;
4. versão do provider;
5. contagem de conexões antes/depois;
6. estados do modal;
7. resultado do passkey;
8. prova de Observador mudo;
9. prova dos agentes;
10. deploys;
11. pendências reais, sem exagero.

Comece agora pelo Bloco A.
