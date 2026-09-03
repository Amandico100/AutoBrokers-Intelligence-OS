Você é o novo líder técnico do AutoBrokers Intelligence OS. O líder anterior
passou dias sem resolver um problema que trava uma pessoa real, e o Founder
está justificadamente sem paciência. Esta é a passagem de bastão.

Trabalhe em português. O Founder não é engenheiro: explique em linguagem
simples, sem enrolação, e nunca afirme que algo funciona sem ter medido.


═══════════════════════════════════════════════════════════════════════
1. O QUE É O PRODUTO, em cinco linhas
═══════════════════════════════════════════════════════════════════════

AutoBrokers.ai é um SaaS multi-tenant para corretoras de seguros brasileiras.
Cada corretora conecta o WhatsApp que já usa para atender. A partir daí o
sistema observa as conversas, aprende, e (quando ligado) responde os segurados
e aciona as seguradoras sozinho.

Conectar o WhatsApp = "parear", por QR code. **É o primeiro passo de todo
cliente novo.** Se o pareamento não funciona, não existe produto.

Repositório: c:\Users\amand\Projetos\AUTOBROKERS RESULTA\AutoBrokers-Opus-Exec
Leia `CLAUDE.md` inteiro antes de qualquer coisa — ele é a regra da casa.
Depois `docs/canon/FOUNDER-DECISIONS.md`, em especial **D-Canal-01**.


═══════════════════════════════════════════════════════════════════════
2. O PROBLEMA, exatamente como o Founder o vê
═══════════════════════════════════════════════════════════════════════

Uma atendente (Saionara, corretora **Resulta**) tenta parear o WhatsApp e o QR
code NUNCA aparece. A tela mostra, alternadamente:

    "O serviço de conexão está indisponível no momento."   (provider_unavailable)
    "A configuração do canal precisa de ajuste pelo suporte." (configuration_error)

...com um código tipo `WA-9ADD5458D6` que muda a cada tentativa. **Não há
suporte a chamar: o suporte é o próprio sistema.**

Enquanto isso, outra atendente (Regina, corretora **AutoFleet**) está pareada e
funcionando. ⚠️ **NADA do que você fizer pode derrubá-la.** Ela é a única
captura de conversas viva do produto.

Isso dura DIAS. Já houve três diagnósticos, dois consertos aplicados em
produção, e o QR continua não aparecendo.


═══════════════════════════════════════════════════════════════════════
3. A ARQUITETURA, o mínimo para você se orientar
═══════════════════════════════════════════════════════════════════════

    navegador  →  Next.js (smith-web)  →  FastAPI (smith-api)  →  Evolution Go
                  app/api/dashboard/       backend/app/services/    fork nosso
                  whatsapp-channel/        whatsapp/                de whatsmeow
                  route.ts                 pairing_orchestrator.py

**Evolution Go** é um FORK NOSSO, com patches em
`infra/evolution-go-autobrokers/patches/` (0001 a 0006). Rodando no EasyPanel em
`https://autobrokers-intelligence-os-evolution-go-teste.golhpm.easypanel.host`
— **é público e alcançável**, você pode medir contra ele.

Cada corretora tem uma "instância" no Evolution Go, identificada por uma
`apikey` própria. **A apikey É a identidade da instância** — não existe forma de
alcançar a instância de um tenant sem a chave dele. É a base do isolamento.

O estado do pareamento vive no **Redis** com TTL, e a integração (nome da
instância + token cifrado) vive no Supabase, tabela `integrations`.

**D-Canal-01 (decisão do Founder, 03/08/2026):** um pareamento serve DUAS
funções — observar (mudo, sempre ligado) e atender (fala, nasce desligado). Por
isso o frontend manda `purpose='observer'` em tudo, inclusive na tela que se
chama "Atendimento & Acionamentos". **Isso está CERTO. Não "conserte" isso** —
o líder anterior quase o fez e teria derrubado a Regina.


═══════════════════════════════════════════════════════════════════════
4. O QUE JÁ FOI MEDIDO — use, mas CONFIRA
═══════════════════════════════════════════════════════════════════════

📊 = medido, com a fonte. 💭 = inferência, não citável como fato.

📊 O provedor está de pé: `GET /server/ok` → HTTP 200 em 40 ms.

📊 As variáveis existem em produção: `EVOLUTION_GO_BASE_URL`,
   `EVOLUTION_GO_GLOBAL_KEY`, `PUBLIC_BACKEND_URL`
   (= https://autobrokers-intelligence-os-autobrokers-smith-api.golhpm.easypanel.host)

📊 A criptografia dos tokens FUNCIONA. Prova: o heartbeat
   (`channel_state.py`) só grava `last_seen_at` quando o provedor responde
   < 400 com o token DECIFRADO. Observado avançando de 5 em 5 minutos, em
   quatro linhas ativas de três tenants:
       12:45:07 → 12:55 → 13:00 → 13:05 → 13:10

📊 O estado das instâncias no provedor, hoje:
       ab-obs-6c9c55e22f-1  observer   AutoFleet  connected     ← a Regina
       ab-obs-04b5cdbc04-1  observer   Resulta    disconnected  ← a que trava
       ab-04b5cdbc04cd      attendance Resulta    connecting

📊 **A MEDIÇÃO MAIS RECENTE E MAIS IMPORTANTE.** Com a instância da Resulta no
   estado LIMPO (`Connected: False, LoggedIn: False`), o `start()` do
   orquestrador rodou e devolveu:

       estado    : configuration_error
       erro      : provider_http_400
       qr_base64 : 0 chars
       qr_text   : 0 chars

   **É 400, não 401.** Não é autenticação — é requisição recusada.

   No `_prepare_and_connect` a sequência é:
       GET  /instance/status   → 200 (confirmado)
       POST /instance/connect  → { webhookUrl, subscribe:[...], immediate:true }
       GET  /instance/qr       → via `_refresh`

   💭 Por eliminação, o 400 vem do `POST /instance/connect`. **CONFIRME isso
   antes de agir** — é a primeira coisa a medir, e ninguém mediu ainda.

📊 Um `DELETE /instance/logout` funcionou (`Connected` foi de True para False).
   Não resolveu: o erro apenas mudou de 401 para 400.


═══════════════════════════════════════════════════════════════════════
5. O QUE JÁ FOI DESCARTADO — não repita
═══════════════════════════════════════════════════════════════════════

❌ **"O evolution-go caiu"** — está de pé, 200 em 40 ms.

❌ **"Limite de tentativas (429)"** — foram ~5 tentativas em 15 horas.

❌ **"O ENCRYPTION_KEY está errado"** — o heartbeat prova o contrário (§4).
   ⚠️ E aqui está o ERRO DE MÉTODO que custou meio dia, para você não repetir:
   testaram os tokens **como estão no banco** (cifrados) contra o provedor e os
   cinco deram 401. Concluíram "chave errada". Mas um ciphertext usado como
   apikey dá 401 SEMPRE, com qualquer chave. **Cinco resultados iguais
   produzidos pelo mesmo defeito não são cinco evidências.** Faltou a linha de
   controle: medir com o token DECIFRADO. CLAUDE.md §9.2 existe para isso.

❌ **"É cifra dupla"** — morta por aritmética: `encrypt` de 32 bytes dá 188
   chars; de 188 bytes daria 444. O banco tem 188.

❌ **"O `purpose='observer'` chumbado no frontend está errado"** — está certo,
   é a D-Canal-01.


═══════════════════════════════════════════════════════════════════════
6. O QUE JÁ FOI CONSERTADO (e não bastou)
═══════════════════════════════════════════════════════════════════════

Commit `76c39a0` — `_integration()` filtrava `is_active=True`, então uma
corretora que desconectou perdia o NOME e o TOKEN da instância, e o código
inventava um token novo para um nome determinístico que já existia no provedor.
Consertado com `_instancia_lembrada` + `identidade_da_instancia`.
📊 Funcionou nessa camada, mas o erro só mudou de forma.

Commit `ead311a` — `decrypt_integration_secret` era fail-OPEN: não conseguia
decifrar e devolvia o próprio ciphertext "tratando como plaintext legado".
Agora distingue legado de quebrado e GRITA no segundo caso.
📊 Não era a causa, mas era o que a escondia.

**Os dois estão certos e devem ficar. Nenhum resolveu o QR.**


═══════════════════════════════════════════════════════════════════════
7. A PISTA MAIS FORTE, e nunca foi investigada a fundo
═══════════════════════════════════════════════════════════════════════

`infra/evolution-go-autobrokers/patches/0002-qrtimeout-terminal.patch` — o
`GetQr` do nosso fork trata dois casos:

    if client == nil                    → inicia instância e emite QR
    if client != nil && IsLoggedIn()    → "connected"

💭 **Não há ramo para `client != nil && !IsLoggedIn()`** — socket de pé, sessão
não logada. A instância da Resulta esteve exatamente nesse estado.

E do nosso lado (`pairing_orchestrator.py`, `_refresh`), qualquer 4xx do
`/instance/qr` é TERMINAL com `next_action=contact_support`. Já
`admin_atlas.py:455` trata o MESMO 4xx como "ainda não tem QR", sem erro.
**Três consumidores de `/instance/qr`, três semânticas diferentes.**


═══════════════════════════════════════════════════════════════════════
8. O QUE O FOUNDER PEDE DE VOCÊ
═══════════════════════════════════════════════════════════════════════

**PRIMEIRO: audite e descubra. NÃO conserte antes de entender.**

Ele foi explícito: *"pra ele analisar tudo, não fazer nada, só descobrir por que
não funciona e resolver isso"*. Ele está cansado de consertos parciais que
mudam o sintoma.

1. **O inventário do Evolution Go.** Quais rotas existem no fork, o que cada uma
   aceita e devolve, e o que os 6 patches mudaram. Leia o código Go, não só os
   patches. Se o binário estiver rodando, `GET /server/ok` e as rotas de
   listagem ajudam.

2. **A causa do HTTP 400, provada.** Meça: qual chamada, qual corpo, qual
   resposta. Não conclua por eliminação — mostre a requisição e a resposta.

3. **O caminho para a Saionara parear**, com os comandos exatos para o console
   do contêiner (`/app`), dizendo o que cada um destrói.

   ⚠️ **NÃO APAGUE a instância `ab-obs-04b5cdbc04-1`.** Ela responde OK no
   heartbeat, tem telefone pareado, e o `observer_number` dela é metade da chave
   de deduplicação de 69.150 transcrições já capturadas. Apagar regravaria o
   acervo inteiro. Logout (encerrar sessão) é diferente de delete — e é seguro.

4. **A pergunta de arquitetura, que é a que mais importa para ele:**

   > "Como deve ser um tenant bem estruturado? A Saionara precisa parear, a
   > Regina precisa continuar pareada, qualquer outra corretora que entrar
   > precisa parear normalmente sem que outra instância caia, sem interferência
   > de um tenant pro outro. É possível deixar observador e evolution ligados
   > juntos? Provavelmente a arquitetura está errada."

   Responda com ESTE código na mão — arquivo e linha — não com teoria genérica.

**Fragilidades já mapeadas, para você confirmar ou derrubar:**
  · três lugares criam instância com nomes INCOMPATÍVEIS entre si:
    `pairing_orchestrator.py:517`, `whatsapp_channel.py:116`, `admin_atlas.py:394`
    (violação da CLAUDE.md §5 — proibido motor paralelo)
  · `admin_atlas.py:419-433` grava token em TEXTO PURO, e `:445-448` lê sem
    decifrar e sem filtrar por `company_id`
  · `deve_reconectar` (`channel_state.py:325-341`) só religa quem estava
    `connected`/`connecting` — uma vez gravado `disconnected`, o reconector
    automático NUNCA mais tenta
  · `/health` devolve `git_commit: "nao-injetado"` — não dá para saber qual
    código está no ar durante um incidente


═══════════════════════════════════════════════════════════════════════
9. COMO TRABALHAR AQUI — as regras que não são negociáveis
═══════════════════════════════════════════════════════════════════════

**§9.2 — toda medição precisa de linha de CONTROLE.** Varie um fator por vez e
inclua a rodada que repete a anterior. Foi a ausência disso que produziu o
diagnóstico errado do ENCRYPTION_KEY.

**§9.3 — um guarda que não tem como falhar não guarda nada.** Prove por mutação:
quebre o próprio conserto e mostre que o teste reprova.

**§12.1 — 📊 medido (com a query/comando) · 💭 ilustrativo.** Número sem marca é
defeito de revisão.

**§5 — proibido criar motor paralelo.** Consolide antes de duplicar.

**§13.3 — nunca exiba segredo.** Presença, tamanho e forma; nunca o valor.

**Teste:** Python solto em `backend/tests/`, docstring narrativa contando a
história do defeito, helper `checar()`, `main()` → 0/1, **sem pytest**.
Rodar tudo: `for t in backend/tests/test_*.py; do PYTHONIOENCODING=utf-8 python "$t" < /dev/null > /dev/null 2>&1 || echo "VERMELHO: $t"; done`
📊 Hoje são **180 verdes**. Não entregue menos.

⛔ **Nunca use `git checkout` para desfazer experimento.** Em 05/08 isso apagou
201 linhas de trabalho não commitado neste repositório. Backup por cópia.

⛔ **O deploy sai da `main`.** Commit em branch não chega em produção.

**O acesso do Founder:** ele roda comandos no console do EasyPanel (contêiner
`smith-api`, diretório `/app`). Cada comando que você pedir custa tempo e
paciência dele — mande poucos, completos, e explique como ler a saída.


═══════════════════════════════════════════════════════════════════════
10. O QUE ESTÁ FUNCIONANDO — não mexa
═══════════════════════════════════════════════════════════════════════

📊 O RAG foi terminado hoje: 12.071 cartas publicadas e indexadas, 5 categorias
de assunto, rótulo de seguradora honesto, corpus normativo com 9 documentos
novos. A captura da AutoFleet está viva. 180 testes verdes.

O único bloqueio é o pareamento. **É só nele que você deve mexer.**
