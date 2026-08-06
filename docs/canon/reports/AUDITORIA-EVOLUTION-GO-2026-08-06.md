# Auditoria do pareamento e da arquitetura de canais — Evolution Go

**Data:** 06/08/2026 · **Commit base:** `64c3629` · **Branch:** `feat/spec063-atendimento-canais`
**Escopo:** por que o QR da Saionara (Resulta) nunca aparece; se a arquitetura de canais escala.
**Natureza:** auditoria (Parte I) + execução autorizada (Parte II).
A Parte I foi escrita **antes** de qualquer alteração, e nenhuma conclusão dela
depende de código escrito depois. O que foi mudado está declarado na Parte II §10.

Marcação obrigatória (CLAUDE.md §12.1): 📊 medido · 💭 inferência.

---

## 0. Resumo em cinco linhas

A Saionara **já está pareada** — o telefone dela está gravado nos dois lados. O sistema
insiste em pedir um QR code para uma linha que já tem sessão, o provedor responde
corretamente "não tenho QR para dar", e o nosso código traduz essa resposta como
"chame o suporte". Enquanto isso, o reconector automático **apaga o endereço de webhook**
de toda instância que religa — e é por isso que a captura das duas corretoras está morta
há dias com o painel dizendo "Conectado".

---

## 1. Método

Toda conclusão abaixo tem requisição e resposta. As medições foram feitas contra o
provedor público `autobrokers-intelligence-os-evolution-go-teste.golhpm.easypanel.host`,
usando uma **instância de laboratório própria** (`ab-lab-diag-1/3`), criada e apagada
dentro da sessão, mais leitura read-only das instâncias reais.

Toda bateria tem **linha de controle** (CLAUDE.md §9.2). A instância da Regina
(`ab-obs-6c9c55e22f-1`) foi medida no começo e no fim de cada bateria como controle vivo:
📊 permaneceu `Connected: true, LoggedIn: true, Name: "Maria Regina - Autofleet Seguros"`
do início ao fim da auditoria.

O código Go foi lido na fonte: upstream `9337afc4` baixado e os **6 patches do fork
aplicados** (`git apply --check` limpo nos 6), de modo que o que foi lido é exatamente
o que roda em produção.

---

## 2. Inventário do Evolution Go

### 2.1 Rotas (`pkg/routes/routes.go:80-109`)

Dois grupos, com **autenticação diferente**:

| Grupo | Auth | Rotas |
|---|---|---|
| admin (`AuthAdmin`) | chave **global** | `POST /instance/create` · `GET /instance/all` · `GET /instance/info/:id` · `DELETE /instance/delete/:id` · `POST /instance/proxy/:id` · `DELETE /instance/proxy/:id` · `POST /instance/forcereconnect/:id` · `GET /instance/logs/:id` |
| instância (`Auth`) | **apikey da instância** | `POST /instance/connect` · `GET /instance/status` · `GET /instance/qr` · `POST /instance/pair` · `POST /instance/disconnect` · `POST /instance/reconnect` · `DELETE /instance/logout` · `GET/PUT /instance/:id/advanced-settings` |

`GET /server/ok` é aberto. `/send/*` usa a **mesma** `Auth` de instância — ponto central
da §5.

📊 `pkg/middleware/auth_middleware.go`: `Auth` resolve a instância por
`GetInstanceByToken(apikey)`. Token desconhecido → **401**, sempre. É por isso que
**qualquer** ciphertext usado como apikey dá 401 com qualquer chave de criptografia —
a origem do diagnóstico errado que custou meio dia.

### 2.2 Mapa real de códigos HTTP (📊 medido, não inferido)

| Chamada | Situação | Resposta medida |
|---|---|---|
| `POST /instance/create` | nome novo + token novo | **200** |
| `POST /instance/create` | **nome já existe** | **500** `{"error":"instance already exists"}` |
| `POST /instance/create` | **token já existe** | **500** `duplicate key ... uni_instances_token` |
| `POST /instance/connect` | corpo do orquestrador, instância limpa | **200** |
| `POST /instance/connect` | mesmo corpo, `Connected:true LoggedIn:false` | **200** |
| `GET /instance/qr` | instância **sem** `jid` | **200** + PNG base64 |
| `GET /instance/qr` | instância **com** `jid` | **400** `{"error":"no QR code available. Please wait a moment and try again"}` |
| `POST /instance/forcereconnect/:id` | sem corpo | **400** `EOF` (exige `{"number": ...}`) |

**O 409/422 que o nosso código espera no `create` não existe.** O provedor devolve **500**.

### 2.3 O que os 6 patches mudaram

| Patch | Efeito |
|---|---|
| 0001 | ciclo de vida do sqlstore |
| **0002** | `GetQr` ganha `State`/`ErrorCode`; `Connect` **zera `DisconnectReason`**; remove o auto-restart do cliente ("waiting for an explicit connect request"); `teardownQR` grava `qr_expired`; `LoggedOut` grava `re_pair_required`; `Disconnected` só religa se houver sessão persistida |
| 0003 / 0004 | eventos e invalidação de socket do passkey |
| 0005 / 0006 | envio de resposta interativa (formulário nativo) |

O 0002 é o que mais importa aqui, e **a §7 do briefing estava certa**: não há ramo para
`client != nil && !IsLoggedIn()`. Ver §3.3.

---

## 3. A causa do erro, provada

### 3.1 A hipótese herdada está DERRUBADA

💭 Herdado: *"por eliminação, o 400 vem do `POST /instance/connect`"*.

📊 Medido: `POST /instance/connect` com o corpo **exato** de
[pairing_orchestrator.py:944-952](backend/app/services/whatsapp/pairing_orchestrator.py#L944-L952)
devolve **HTTP 200**, tanto em instância limpa quanto em `Connected:true LoggedIn:false`.

O 400 vem do **`GET /instance/qr`**.

### 3.2 Onde o 400 nasce, linha a linha

`pkg/instance/handler/instance_handler.go:283-287` — **qualquer** erro do `GetQr` vira 400:

```go
qrcode, err := i.instanceService.GetQr(instance)
if err != nil {
    ctx.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})   // ← 400 para tudo
    return
}
```

E o `GetQr` (`pkg/instance/service/instance_service.go`, com o patch 0002) só tem um erro
provável em produção:

```go
code = instance.Qrcode
if code == "" {
    if state := normalizedPairingTerminalState(instance.DisconnectReason); state != "" {
        return &QrcodeStruct{State: state, ErrorCode: state}, nil        // 200, estado terminal
    }
    return nil, fmt.Errorf("no QR code available. Please wait a moment and try again")  // → 400
}
```

E do nosso lado,
[pairing_orchestrator.py:1008-1009](backend/app/services/whatsapp/pairing_orchestrator.py#L1008-L1009):

```python
if qr_response.status_code >= 400:
    raise RuntimeError(f"provider_http_{qr_response.status_code}")
```

→ `_error_state` ([:1048](backend/app/services/whatsapp/pairing_orchestrator.py#L1048))
→ `configuration_error` → **"A configuração do canal precisa de ajuste pelo suporte."**

> **O provedor diz literalmente "espere um momento e tente de novo".
> Nós traduzimos isso como "chame o suporte" — e não existe suporte.**

### 3.3 Por que o QR fica vazio para a Saionara — bateria com controle

`pkg/whatsmeow/service/whatsmeow.go:325-335` decide o destino da instância **pelo `jid`**:

```go
if cd.Instance.Jid != "" {
    deviceStore, err = container.GetDevice(ctx, jid)   // sessão salva
} else {
    deviceStore = container.NewDevice()                // device novo
}
```

e `:488` decide se emite QR **pelo device**:

```go
if client.Store.ID != nil {
    // "Already logged in with JID" → Connect() para RECONECTAR. Nunca emite QR.
} else {
    // New-device pairing → Connect() e emite *events.QR
}
```

📊 **Bateria de controle (06/08/2026 ~14:54Z).** Mesmo corpo, mesma sequência
(`POST /instance/connect` → `GET /instance/qr`). **Único fator variado: existência do `jid`.**

| Rodada | Instância | `jid` | connect | qr |
|---|---|---|---|---|
| **A — controle** | `ab-lab-diag-3` (laboratório) | ausente | 200 | **200 + QR** |
| **B — teste** | `ab-obs-04b5cdbc04-1` (Saionara) | presente | 200 | **400** `no QR code available` |

Um fator variado, um resultado invertido. **Conclusão travada:**

> **Enquanto `instances.jid` estiver preenchido no banco do Evolution Go, aquela instância
> NUNCA vai gerar QR. Ela sempre tenta ressuscitar a sessão antiga.**

### 3.4 A prova na fonte: o log da própria instância

📊 `GET /instance/logs/3be363b1-...` (06/08/2026, 12:32:23Z) — lido, não deduzido:

```
12:32:23.784  Processing subscribe events: [MESSAGE CONNECTION HISTORY_SYNC QRCODE]
12:32:23.785  Starting new client instance
12:32:23.786  Jid found. Getting device store for jid: 554788087463:26@s.whatsapp.net   ← ☠️
12:32:23.979  No client found, starting new instance for QR code
12:32:23.980  Waiting for QR code generation...
12:32:23.980  Jid found. Getting device store for jid: 554788087463:26@s.whatsapp.net   ← ☠️ (2ª vez)
12:32:26.982  No QR code available yet, waiting a bit more...
12:32:27.860  ===== MESSAGE RECEIVED ===== From: status@broadcast, Type: media
12:32:28.022  ===== DISPATCHING WEBHOOK ===== Event: GroupInfo
12:32:39.011  ===== DISPATCHING WEBHOOK ===== Event: Picture
```

Duas leituras dessa página:

1. **`Jid found`** é a linha 326 do whatsmeow. Confirma §3.3 na instância real.
2. **A instância CONECTOU e recebeu mensagens reais do WhatsApp.** `MESSAGE RECEIVED`,
   `GroupInfo`, `PushName`, `Picture` só acontecem com sessão **válida e autenticada**.

> **A tentativa de pareamento da Saionara é justamente o que religa a captura dela.
> Falha na tela e funciona no provedor.**

Note também **duas** chamadas a `StartInstance` no mesmo segundo (`.786` e `.980`): o
`connect` com `immediate:true` sobe um cliente e o `GetQr` sobe outro. Corrida conhecida,
registrada em §6.

### 3.5 O outro erro alternado — `provider_unavailable`

Quando o orquestrador não encontra integração ativa, ele chama `_provider_create`
([:809-863](backend/app/services/whatsapp/pairing_orchestrator.py#L809-L863)), que trata
**409/422**. 📊 O provedor devolve **500** para nome repetido. Logo:

`provider_http_500` → `_error_state` → `provider_unavailable`
→ **"O serviço de conexão está indisponível no momento."**

**Os dois erros alternados que a Saionara vê estão explicados, e são defeitos distintos.**

### 3.6 Por que "dura dias" — a instância zumbi

📊 Medido: às 14:54Z fiz `connect` + `qr` na instância da Saionara. **Nenhuma linha de log
nova foi escrita** — nem `No client found`, nem `Client exists but not connected`.

Isso só é possível num caminho: `client != nil && !client.IsLoggedIn()`. Releia o `GetQr`:

```go
if client == nil { ...estado terminal... }          // não entra
if client != nil && client.IsLoggedIn() { ... }     // não entra
if client == nil { ...StartInstance... }            // não entra  ← nada é feito
```

**É exatamente o buraco previsto na §7 do briefing, agora medido.** O cliente morto de
12:32 ficou no mapa. A partir daí, toda tentativa devolve 400 em milissegundos sem sequer
tentar. A instância fica presa **até o contêiner reiniciar** — ou até um `logout`, que é
o único caminho que faz `delete(clientPointer)`.

Isso explica por que o erro "mudou de 401 para 400 e travou": o logout destravou o zumbi
uma vez, e o zumbi voltou.

### 3.7 Dois mapas, duas verdades

📊 `Status` (`instance_service.go:391-400`) lê `clientPointer` — **memória do processo**,
não o banco:

```go
client := i.clientPointer[instance.Id]
if client == nil {
    return &StatusStruct{Connected: false, LoggedIn: false}, nil   // ← mente sobre a sessão
}
```

E `Connect` (`:251`, `:255-262`) decide se precisa subir cliente por **`myClientPointer`**,
via `UpdateInstanceSettings`. 📊 `instance_service.go:366, 381, 647, 796` deletam
`clientPointer` **sem** deletar `myClientPointer`.

Consequência: depois de um `logout`,

- `GET /instance/status` → "LoggedIn: false" (embora pareada)
- `POST /instance/connect` → "Instance already running" → **não sobe cliente nenhum**

📊 Confirmado no comportamento: `CONNECT_ON_STARTUP=false` (credencial do serviço), então
após todo restart do provedor nenhuma instância religa sozinha, e `/instance/status`
passa a dizer `LoggedIn:false` para **todas** — inclusive as perfeitamente pareadas.

**É essa mentira que faz o orquestrador concluir "não está logada, vamos parear".**

---

## 4. O achado mais grave — e não é o QR

📊 `GET /instance/all` (06/08/2026, 14:56Z):

| instância | corretora | `events` | `webhook` |
|---|---|---|---|
| `ab-obs-6c9c55e22f-1` | **AutoFleet (Regina)** | `MESSAGE` | **`''`** |
| `ab-04b5cdbc04cd` | Resulta | `MESSAGE` | **`''`** |
| `ab-obs-3aa75902a3-1` | Amandus | `MESSAGE` | **`''`** |
| `ab-obs-04b5cdbc04-1` | Resulta (Saionara) | `MESSAGE,CONNECTION,HISTORY_SYNC,QRCODE` | preenchido¹ |

¹ preenchido pela minha medição de §3.3 — ver §8.

**A instância da Regina está conectada e logada no WhatsApp, e não tem endereço para
entregar mensagem nenhuma.**

📊 O preço, medido no Supabase:

| corretora | `observed_events` | último evento | `attendance_transcripts` | última captura |
|---|---|---|---|---|
| AutoFleet | 12.219 | 04/08 20:34Z (**42 h**) | 41.966 | 05/08 13:59Z (**25 h**) |
| Resulta | 8.041 | 03/08 20:19Z (**67 h**) | 59.168 | 29/07 18:27Z (**188 h**) |

### Quem apaga o webhook

[channel_state.py:366-368](backend/app/services/whatsapp/channel_state.py#L366-L368):

```python
resposta = await cliente.post(f"{base}/instance/connect",
                              headers={"apikey": token},
                              json={"immediate": True})       # ← sem webhookUrl, sem subscribe
```

E o `Connect` do Go (`instance_service.go:236-247`) **grava incondicionalmente**:

```go
if len(data.Subscribe) == 0 {
    subscribedEvents = append(subscribedEvents, event_types.MESSAGE)   // ← reduz a MESSAGE
}
instance.Events  = eventString
instance.Webhook = data.WebhookUrl                                     // ← "" apaga a URL
i.instanceRepository.Update(instance)
```

> **O reconector religa o canal MUDO E SURDO.** O socket sobe, o painel diz "Conectado",
> e o Evolution Go não sabe mais para onde mandar as mensagens.

Os dados assinam: `events='MESSAGE'` em exatamente as três instâncias que o reconector
tocou, e os quatro eventos na única que recebeu um `connect` completo.

Esta é a pior falha do conjunto porque é **silenciosa**: o `last_seen_at` avança de 5 em 5
minutos, o heartbeat fica verde, e o acervo não cresce.

---

## 5. A pergunta de arquitetura

> *"Como deve ser um tenant bem estruturado? É possível deixar observador e evolution
> ligados juntos?"*

### 5.1 A resposta curta: sim, e com UMA instância — não duas

📊 Prova no código, não em teoria. `pkg/routes/routes.go:95-120`: `/instance/*` e
`/send/*` usam **o mesmo** `authMiddleware.Auth`, isto é, **a mesma apikey de instância**:

```go
routes = eng.Group("/instance") { routes.Use(r.authMiddleware.Auth) { ... } }
routes = eng.Group("/send")     { routes.Use(r.authMiddleware.Auth) {
    routes.POST("/text", ...)   // ← a MESMA apikey que observa, envia
}}
```

Um dispositivo vinculado do WhatsApp **recebe tudo e envia** — é uma só sessão. A
`ab-obs-6c9c55e22f-1` que observa a Regina hoje já poderia responder por ela agora, sem
nenhum pareamento adicional.

**Observar e atender não são dois canais. São duas políticas sobre o mesmo canal.**
E isso é precisamente o que a **D-Canal-01** decidiu — o frontend está certo em mandar
`purpose='observer'` sempre. É o **backend** que não implementou a decisão: ele traduz
`purpose` em **instâncias separadas**.

### 5.2 O custo real do modelo de hoje

📊 A Resulta tem duas instâncias no provedor (`ab-obs-04b5cdbc04-1` e `ab-04b5cdbc04cd`)
para o mesmo WhatsApp. A de atendimento tem `jid=''` e `disconnect_reason='qr_expired'`:
**nunca foi pareada.** A AutoFleet não tem instância de atendimento nenhuma.

> **Nenhuma corretora tem canal de atendimento pareado. O agente de atendimento não tem,
> hoje, por onde falar** — e a arquitetura atual exige que cada atendente escaneie um
> **segundo** QR para isso, gastando um segundo slot dos ~4 dispositivos vinculados que o
> WhatsApp permite por número.

### 5.3 Motores paralelos — CLAUDE.md §5 violada, com prova viva

Três funções geram nome de instância, e **discordam**:

| Arquivo | Função | Regra | `observer` | `attendance` |
|---|---|---|---|---|
| [pairing_orchestrator.py:516-522](backend/app/services/whatsapp/pairing_orchestrator.py#L516-L522) | `_instance_name` | base **10** chars | `ab-obs-{b10}-1` | `ab-{b10}-attendance` |
| [whatsapp_channel.py:116-122](backend/app/api/whatsapp_channel.py#L116-L122) | `_go_instance_name` | base **12** chars | `ab-{b12}-observer` | `ab-{b12}` |
| [admin_atlas.py:394-395](backend/app/api/admin_atlas.py#L394-L395) | `_obs_instance_name` | base + `seq` | `ab-obs-{b}-{seq}` | — |

📊 **A prova está viva no provedor:** `ab-obs-04b5cdbc04-1` (base de 10) **e**
`ab-04b5cdbc04cd` (base de 12) coexistem para a mesma corretora. Dois caminhos de código
criaram duas identidades para o mesmo WhatsApp. **Nome de instância é identidade de
acervo** — e ela está bifurcada.

### 5.4 As demais fragilidades — confirmadas

| Fragilidade | Veredito |
|---|---|
| `admin_atlas.py:426` grava token em **texto puro** | 📊 **CONFIRMADO.** `inst_token = secrets.token_hex(16)`, gravado sem cifrar. O orquestrador cifra (188 chars). Duas escritas, dois formatos, na mesma coluna. |
| `admin_atlas.py:445-448` lê sem decifrar e **sem `company_id`** | 📊 **CONFIRMADO.** Filtra só por `instance_id` + `purpose`. Manda o valor cru como apikey — **se o token estiver cifrado, dá 401 sempre**. É esta rota que produziu os 401 que geraram o diagnóstico errado do `ENCRYPTION_KEY`. Filtro por tenant ausente viola CLAUDE.md §7. |
| `deve_reconectar` só religa quem estava `connected`/`connecting` | 📊 **CONFIRMADO** ([channel_state.py:337-341](backend/app/services/whatsapp/channel_state.py#L337-L341)). As três linhas em `disconnected` hoje **nunca** serão religadas automaticamente. |
| `/health` → `git_commit: "nao-injetado"` | 📊 **CONFIRMADO** ([main.py:486](backend/app/main.py#L486)). Durante incidente não se sabe qual código está no ar. |
| Três semânticas para o mesmo 4xx de `/instance/qr` | 📊 **CONFIRMADO.** `pairing_orchestrator:1008` = terminal `contact_support`; `admin_atlas:455` = "ainda não tem QR", sem erro; `whatsapp_channel:760` = terceiro tratamento. |

### 5.5 Escala

- **Isolamento entre tenants no provedor: correto.** Uma apikey por instância, resolvida
  por `GetInstanceByToken`. Não há caminho para alcançar a instância de outro tenant sem
  a chave dele. 📊 A Regina permaneceu intocada durante toda a auditoria.
- **Isolamento no nosso lado: furado em um ponto** — `admin_atlas.py:445-448` (§5.4).
- 💭 **Teto de escala a medir:** `POSTGRES_MAX_OPEN_CONNS=20` num `authContainer`
  compartilhado por todas as instâncias. `db_pool_exhausted` já é estado terminal previsto
  no patch 0002, o que sugere que alguém já bateu nesse teto. Precisa de medição com carga
  antes de qualquer promessa de N corretoras.

---

## 6. Ordem dos defeitos, por dano

| # | Defeito | Efeito | Onde |
|---|---|---|---|
| **1** | Reconector zera `webhook` e `events` | **captura morta em silêncio nas duas corretoras** | `channel_state.py:366-368` |
| **2** | Pede QR para linha que já tem `jid` | QR nunca aparece → `configuration_error` | `pairing_orchestrator.py:890-1009` |
| **3** | `create` devolve 500 e nós esperamos 409/422 | `provider_unavailable` | `pairing_orchestrator.py:825` |
| **4** | Zumbi `client != nil && !IsLoggedIn()` | trava a instância por dias | patch 0002 / `GetQr` |
| **5** | `Status` mente após restart (memória ≠ banco) | orquestrador decide parear quem já está pareado | `instance_service.go:391` |
| **6** | Três geradores de nome divergentes | identidade de acervo bifurcada | §5.3 |
| **7** | Token em texto puro + leitura sem `company_id` | risco cross-tenant + 401 enganosos | `admin_atlas.py:426,445` |
| **8** | `deve_reconectar` ignora `disconnected` | canal caído nunca volta sozinho | `channel_state.py:337` |
| **9** | Corrida de duplo `StartInstance` | dois clientes para uma instância | §3.4 |
| **10** | `/health` sem commit | incidente às cegas | `main.py:486` |

---

## 7. O que ficou fora desta auditoria

- **Nenhum conserto foi aplicado.** O Founder pediu diagnóstico antes de ação.
- 💭 Carga/pool (§5.5) não foi medido — exige ambiente de teste com N instâncias.
- Não foi investigado por que o socket da Saionara caiu depois de 12:32:39.
- `GET /instance/logs/:id` parou de registrar linhas novas após 12:32:39 apesar de novas
  requisições. 💭 Buffer por instância preso ao ciclo de vida do cliente. Não investigado
  — mas é observabilidade cega durante incidente.

## 8. Mutações que EU causei nesta sessão (declaração honesta)

1. Criei `ab-lab-diag-1` e `ab-lab-diag-3` — 📊 **apagadas** ao fim (`delete → http=200`).
   `ab-lab-diag-2` nunca chegou a existir (o create falhou por token duplicado).
2. `POST /instance/connect` na instância da Saionara (`ab-obs-04b5cdbc04-1`) com
   `webhookUrl` de sonda terminando em `/probe`. **Antes dessa chamada o campo estava
   vazio** (como as outras três) — ou seja, não entregava nada e continua não entregando,
   com um token de webhook que não autentica. Não houve piora, mas **precisa ser regravado
   com o token real no conserto do defeito #1**.
3. Nada foi apagado. `ab-obs-04b5cdbc04-1` está intacta, com `jid` e `paired_phone_e164`
   preservados. 📊 Controle Regina verde do início ao fim.

---

# PARTE II — Execução do bloco de emergência (06/08/2026)

Autorizada pelo Founder após a Parte I. Commits `f81e24e` (consertos) e `c6b7988`
(pendências). **Ainda na branch** — o deploy sai da `main`.

## 9. O número pareado, verificado a pedido do Founder

📊 `select paired_phone_e164 from integrations where provider='evolution-go'`:

| corretora | número | DDD | quem é |
|---|---|---|---|
| AutoFleet | `+554891759360` | 48 | Regina |
| **Resulta** | `+554788087463` | **47** | **o telefone do Founder** |

A atendente (DDD 48) pedia QR para uma linha cujo dono era outro número. Com
`jid` preenchido o whatsmeow **reconecta** em vez de emitir QR (§3.3) — o QR não
podia vir, em nenhuma tentativa.

📊 E o acervo da Resulta **já foi destilado**: 137 das 179 sessões. As 12.933
cartas do acervo estão todas em categoria de seguro (sinistro, cobrança, apólice,
assistência, atendimento; ramos auto/residencial/vida). Conversa sem assunto de
seguro não vira carta. O valor foi extraído; desconectar não apaga transcrição
nenhuma, só encerra a captura dali em diante.

⚠️ Correção de método: a primeira tentativa de separar "conversa de corretora" de
"conversa pessoal" usou `insurer_key`. 📊 A linha de controle derrubou a
conclusão — a AutoFleet também tem 0%, o campo não é preenchido para ninguém. A
comparação não distinguia nada e foi descartada antes de virar afirmação.

## 10. O que foi feito em produção

| # | Ação | Alvo | Resultado medido |
|---|---|---|---|
| 1 | rotação da credencial de webhook | AutoFleet | hash gravado, prefixo `2FoWlLjm` |
| 2 | `POST /instance/connect` completo | AutoFleet | 200 · webhook e 4 eventos gravados |
| 3 | `POST /instance/reconnect` | AutoFleet | 200 · `LoggedIn:true` antes e depois |
| 4 | `DELETE /instance/delete` + `create` mesmo nome/token | Resulta | 200 · `jid` agora vazio |
| 5 | rotação da credencial + limpeza do telefone | Resulta | prefixo `s7PuR57x` · `paired_phone_e164` nulo |
| 6 | `POST /instance/connect` completo | Resulta | 200 |
| 7 | **`GET /instance/qr`** | **Resulta** | **200 · `state: qr_ready` · 1830 chars** |

📊 Estado final do `/instance/all`:

```
ab-obs-6c9c55e22f-1   conn=True   jid=SIM   MESSAGE,CONNECTION,HISTORY_SYNC,QRCODE   webhook=SIM
ab-obs-04b5cdbc04-1   conn=False  jid=---   MESSAGE,CONNECTION,HISTORY_SYNC,QRCODE   webhook=SIM
```

📊 Autenticação do webhook, com linha de controle:

| requisição | resposta |
|---|---|
| token novo da AutoFleet | **200** |
| token novo da Resulta | **200** |
| token inventado | **401** |
| token do AutoFleet com 1 caractere trocado | **401** |

Os dois controles são o que dá mérito ao 200: o endpoint recusa o que deve
recusar. A corrente do nosso lado está fechada.

## 11. Correção a uma conclusão intermediária

Durante a execução afirmei que a instância da Regina "não gerava log há 16 horas,
logo o socket estaria morto-vivo". 📊 Errado: depois do `reconnect` — que
certamente escreve `Starting fresh instance` — o log **continuou parado em
05/08 23:23:55Z**. O congelado é o `GET /instance/logs/:id`, não o socket.

Fica como achado de observabilidade, e é grave do seu jeito: **durante um
incidente, o log por instância mente por omissão.** A fonte confiável de "está
capturando" é `observed_events` no Supabase, nunca o log do provedor.

## 12. O que ainda NÃO está provado

- 💭 **Que a captura voltou a gravar.** No fechamento desta sessão
  `observed_events` ainda não tinha linha nova. Isso é esperado — depende de
  chegar mensagem real — mas **não é prova**, e não deve ser tratado como tal.
  A verificação é a query do P-110, e ela precisa rodar de novo mais tarde.
- 💭 Que a sessão da Regina sobreviverá ao próximo restart do provedor:
  `CONNECT_ON_STARTUP=false` continua, e o reconector consertado só age sobre
  quem a sonda vê caído.
- O QR da Resulta gerado às 15:47Z **expira** (`QRCODE_MAX_COUNT=5`). A atendente
  deve gerar um novo pela tela no momento em que for escanear — e agora ele vem,
  porque o `jid` está vazio.
