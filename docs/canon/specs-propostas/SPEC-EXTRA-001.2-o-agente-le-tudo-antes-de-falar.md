# SPEC-EXTRA-001.2 — O AGENTE LÊ TUDO ANTES DE FALAR
## Uma rajada, uma resposta · sem pergunta repetida · sem cumprimento no meio · com o nome certo

**Produto:** AutoBrokers Intelligence OS.
**Status:** **PROPOSTA PARA CONVERSÃO, AQUECIMENTO E EXECUÇÃO** — não é SPEC canônica aprovada nem implementação realizada.
**Versão:** 1.0 · **Data:** 13/09/2026.
**Origem:** `docs/canon/DIAGNOSTICO-PILOTOS-E-PLANO-EXTRA-2026-09-12.md` §1.4 (os defeitos com causa), §3 bloco 001.2, **§7.4** (o nome do agente) e §12.1 (a ordem). Decisões **D-PILOTO-08, 12, 14, 20**.
**Baseline medida:** `a0bb5fef440eba394a9275671b1143f5025807ef` — `git rev-list --count HEAD..origin/main` = **0**, `origin/main..HEAD` = **0**, medido em 13/09/2026. O BLOCO 0 remede a revisão do dia da execução.
**Branch sugerida:** `feat/spec-extra-001-2-le-tudo-antes-de-falar`.
**Destino desta proposta:** `docs/canon/specs-propostas/SPEC-EXTRA-001.2-o-agente-le-tudo-antes-de-falar.md`.
**SPEC definitiva a criar pelo executor:** `docs/canon/specs/SPEC-EXTRA-001.2-o-agente-le-tudo-antes-de-falar.md`.
**Research Pack:** `SPEC-EXTRA-001.2-o-agente-le-tudo-antes-de-falar-RESEARCH-PACK.md` (mesma pasta).
**Relatório a criar durante a execução:** `docs/canon/reports/SPEC-EXTRA-001.2-EXECUTION-REPORT.md`.
**Protocolo:** AAA v11.2 + OPÇÃO B. **Marcha fixada pelo diagnóstico §8: CRÍTICO, 3 juízes.** 💭 6–9 h de relógio.
**Dependências:** nenhuma SPEC precede esta. Ela **entrega** à EXTRA-001.3 a peça "uma conversa por contraparte" (diagnóstico §12.1, linha 5).

---

## 0. Resultado e motivo

> O segurado manda cinco mensagens e uma foto em doze segundos. O agente lê **tudo**, e responde **uma vez** — no máximo duas, e a segunda é continuação, não repetição. Não pergunta o que já foi respondido. Não cumprimenta no meio da conversa. Não chama o segurado pelo nome de outra pessoa. E o nome que a corretora escolheu para o agente nunca se confunde com o nome de quem trabalha lá.

**Por que isto é a segunda SPEC da família, e não a décima.** 📊 No piloto de 09–11/09 o agente falou com **5 segurados reais**. Em **4 de 4** rajadas de duas ou mais mensagens em ≤ 30 s, ele **fragmentou** — duas respostas para uma pergunta. Fez **10 perguntas para 8 slots**; perguntou `agua_escorrendo` **três vezes** depois de o segurado dizer que já tinha fechado o registro; perguntou "vocês estão bem?" **duas** vezes; escreveu *"boa notícia começar o dia com você"* na **30ª** mensagem de um sinistro **com vítima**; e abriu um caso chamando o cliente pelo nome de outra pessoa de 22 dias atrás (diagnóstico §1.4).

**E a rajada não é um caso de borda: é o caso comum.** 📊 Medido em 13/09/2026 sobre `attendance_transcripts` (166.365 linhas, 84.818 mensagens de entrada de cliente, 1.874 contrapartes, 17/09/2024 → 12/09/2026; as consultas estão no RESEARCH-PACK §3):

```
20.727 rajadas de ≥2 mensagens em ≤30 s
72.610 mensagens dentro delas  =  85,6% de TODO o inbound de cliente
 5.608 delas têm MÍDIA          =  27,06%   ← e a mídia pula o buffer hoje
 8.574 silêncios no MEIO da conversa (26,0% dos turnos) · 6 motivos escritos no banco inteiro
   175 conversas-fantasma (LID), 100% abertas — eram 174 em 09/09
```

Nada disso é opinião sobre o tom do agente. **Cada um destes é um byte que chegou errado ao segurado** — o teste do produto do protocolo §2 dá SIM para todos. E a causa de cada um está localizada, medida e cabe em código pequeno-a-médio.

**O que esta SPEC NÃO promete.** Não promete que o modelo sempre escreverá bem. Promete que **o modelo recebe o conjunto inteiro antes de escrever**, que **o que já foi respondido está escrito no prompt**, que **a decisão de se apresentar deixa de ser do modelo**, e que **duas gerações não disputam a mesma conversa**. O que o modelo faz com isso é medido, não prometido.

### 0.1 Decisões do Founder já incorporadas — são lei, não se reabrem

| ID | Decisão, e o que ela obriga aqui |
|---|---|
| **D-PILOTO-12** (12/09) | **Nome do agente é escolha livre da corretora**, trocável a qualquer hora ("Amanda" na Resulta é escolha da Saionara e **fica**). Esta SPEC **não escolhe nome**: garante que o nome escolhido nunca confunde — apresentação usa o nome; "especialista" nomeia a **atendente real**; trocar o nome não muda conversa em andamento; **nome de agente ≠ nome de membro da equipe (o card recusa)**; nos dossiês o agente assina **🤖**. → §10 |
| **D-PILOTO-14** (12/09) | Alta qualidade sem ser exorbitante: AAA opção B, marcha fixada, **≤ 12 guardas novos por SPEC**, bateria sobre **motor e acervo real**. → §12 tem exatamente **12** |
| **D-PILOTO-08** (12/09) | Numeração `EXTRA-001.1…001.9` mantida; nada renumera. Esta é a **001.2** |
| **D-PILOTO-20** (13/09) | Proposta escrita no chat de planejamento; **execução em chat novo, sob AAA opção B** |
| **D-PILOTO-07** (08/09) | Meta: ≥ 4 atendimentos simultâneos por corretora e **nenhuma corretora interferindo em outra**. 🔴 Obriga a trava a ser **por conversa**, nunca por corretora (§5) |
| **D-PILOTO-02** (08/09) | Não encerrar em lote as 467 conversas abertas da AutoFleet; a Regina responder pelo celular **pausa o robô naquela conversa, e isso é o desejado**. → a §9 não pode enfraquecer a pausa |
| **D-E001-02** | Atendimento permanece **Evolution Go**; não migrar provedor. → a presença "digitando…" sai pelo provider que já existe (§6.4) |
| **D-E001-07** | Testes vivos **somente** pelos números do Founder (§1). Números operacionais Resulta/AutoFleet **proibidos** |

### 0.2 EXECUTION CARD — proposto, a confirmar no BLOCO 0

```text
OUTCOME .............. rajada de 5 mensagens + foto → UMA resposta (no máximo duas), sem pergunta
                       repetida, sem cumprimento no meio, com a identidade certa e o nome que a
                       corretora escolheu
RISCO ................ 8  =  ALCANCE 3 (o SEGURADO) + REVERSIBILIDADE 3 (a mensagem SAI DO PRÉDIO;
                       e há migration que altera ESTRUTURA e TRAVA) + FREQUÊNCIA 2 (TODO atendimento)
SUPERFÍCIE ........... 3  — e o motivo está medido: o diagnóstico apontou UM ponto onde a mídia pula
                       o buffer; a remedição de hoje achou TRÊS (webhook.py:1449, :1634, :2226).
                       "não consigo apontar TODOS os lugares" → 3 (AAA §3)
PISO APLICADO ........ AAA §3.2, três vezes: (a) qualquer coisa que ENVIE mensagem — inclusive a
                       presença "digitando…", que chega ao aparelho do segurado; (b) migration que
                       altera ESTRUTURA e TRAVA (índice único + CHECK); (c) o filtro company_id
                       entra na chave de uma trava nova
NÍVEL ................ CRÍTICO — opção B. A soma já dava CRÍTICO sem o piso (AAA §3.1: "se o rótulo
                       e a soma discordarem, a soma vence")
UNIDADES ............. 6:  A trava de turno · B janela que escuta o conteúdo (+mídia +re-planejamento
                       +presença) · C a ficha sabe o que já foi respondido · D apresentação, tamanho
                       e identidade da thread · E uma conversa, uma linha, um silêncio com motivo
                       (+migrations) · F o nome do agente
COESÃO ............... A e B são UMA unidade de escrita (mesmos dois arquivos: message_buffer_service
                       e buffer_processor) — separadas só para o gate. D e F tocam o mesmo hub
                       (prompts.py + o_fim_do_atendimento.py): serial, um dono por vez.
                       ARQUIVOS-HUB com dono único: app/api/webhook.py · app/agents/graph.py ·
                       app/services/o_fim_do_atendimento.py · app/tasks/buffer_processor.py
PARALELISMO REAL ..... nenhum na escrita dos hubs. Paralelo possível: C (nodes.py + attendance_ficha)
                       ∥ E-migrations (SQL) ∥ F-frontend (card Agente/Equipe). Integração SERIAL
TIME ................. investigador+pesquisador (um agente, AAA §10) · desenhista da prova ANTES do
                       código · builders por unidade (um escritor por arquivo) · verificador mecânico ·
                       painel de 3 lentes (verdade+regressão · produto+DADO · red team) · juiz fresco
                       que confirma o conserto E audita o dado (§6.1)
REFERÊNCIA ........... INTERNA: backend/tests/test_a_maquina_de_lavar_vai_ate_o_fim.py (atendimento
                       ponta a ponta) · backend/tests/test_a_ultima_palavra_humana_manda.py (573
                       linhas, motor real — é o guarda do reencontro) · backend/tests/
                       test_midia_e_concorrencia_do_webhook.py (608 linhas, motor real por AST — é a
                       LINHA DE CONTROLE da trava) · docs/canon/MIGRATIONS-AUTHORITY.md
                       EXTERNA: as 7 de §20 (Redis SET/locks · Meta typing indicators · Evolution
                       sendPresence · Meta webhooks · Evolution webhook retry · Stripe · e a
                       declaração de que janela adaptativa NÃO tem fonte primária)
GATES ................ G0 (zero vermelho: G6 e G7 já falham hoje) + G1–G12 da §12 + os canônicos
O ELO ................ "a resposta fragmenta PORQUE o debounce é por ociosidade" — A medido (4 de 4
                       fragmentaram) · B medido (message_buffer_service.py:158) · 🔴 B CHEGA em A:
                       medido em §0.3. E o segundo elo, o da pergunta repetida, está medido no
                       ESCRITOR da ficha (§7.1) — e é diferente do que o diagnóstico supôs
FAIXA DE RELÓGIO ..... 💭 6–9 h. Faixa, nunca promessa (AAA §9.2). Estourou → resposta escrita de
                       POR QUE CONTINUAR, não parada
ORÇAMENTO ............ alvo canônico CRÍTICO ≤ 2,5 M tokens de subagentes (AAA §10). Estourou →
                       menos LENTES, nunca menos MUTAÇÃO
```

> 🔴 O card definitivo abre o relatório (AAA §0.1 item 2: *"Relatório sem card = SPEC aberta"*), e o guarda `backend/tests/test_o_protocolo_tem_policia.py` confere por máquina.

### 0.3 🔴 O ELO, medido — porque duas medições certas não fazem uma causa certa

**Afirmação-título:** *a resposta ao segurado se parte em duas PORQUE o debounce é por ociosidade.*

| passo | o que se mede | resultado |
|---|---|---|
| **medi A?** | rajadas de ≥ 2 mensagens do segurado em ≤ 30 s que receberam mais de uma resposta | 📊 **4 de 4 fragmentaram** (diagnóstico §1.4, sobre o acervo de 09–11/09). Os intervalos internos medidos: **10, 12 e 22 s** |
| **medi B?** | a regra que decide fechar a rajada | 📊 `message_buffer_service.py:158` — `if seconds_since_last >= max(settings.BUFFER_DEBOUNCE_SECONDS, 8): return True`. É **ociosidade**, e o `max(…, 8)` é **piso**: não há configuração que desça de 8 s |
| **🔴 B CHEGA em A?** | o caminho de B até a segunda resposta, lido da linha 1 da função até o efeito | 📊 **sim, e por dois caminhos independentes** — ver abaixo |

**Caminho 1 — a rajada de texto.** Pausa de 10 s ⇒ `should_process` devolve `True` ⇒ `buffer_processor._uma` faz `get_and_clear_buffer` (`buffer_processor.py:83`) ⇒ chama `process_whatsapp_message_background`. As mensagens 3, 4 e 5 chegam durante a geração, criam **chave nova** no Redis, e a varredura de **1 s** (`buffer_processor.py:154-160`, `max_instances=10`) abre o **segundo turno**. 🔴 O comentário do próprio arquivo (`buffer_processor.py:47-51`) declara que a proteção é o `get_and_clear` atômico — e essa proteção cobre **duas tarefas na mesma chave**, não a **chave nova**. **O elo está medido, e a proteção declarada não cobre o caso real.**

**Caminho 2 — a foto.** `webhook.py:2226-2229` desvia imagem e áudio para `background_tasks` e devolve `{"status":"received","type":"media"}` **sem passar pelo buffer**. A foto gera turno imediato **em paralelo** ao texto que ainda está no buffer. 🔴 E são **três** pontos com esse desvio, não um (`:1449`, `:1634`, `:2226`) — foi o que a remedição de hoje corrigiu no diagnóstico, e é o que sustenta a SUPERFÍCIE 3. 📊 E o caminho 2 vale para **27,06%** das rajadas do acervo, não para um punhado.

🔴 **Um terceiro elo — o do relógio — foi medido hoje e ninguém o tinha visto.** A primeira tentativa de medir rajadas usou `messages.created_at` e devolveu 2.510. Esse número **está errado**: `created_at` é `DEFAULT now()`, o instante em que **o espelho gravou**, não em que o segurado mandou — e o próprio produto documenta a diferença (`espelho_chat.py:771-777`, `:921`). 📊 **32.231 das 33.565** linhas de `messages` vieram do espelho, e os dias de backfill aparecem como picos (14/08: 5.365 · 15/08: 5.090 · 10/09: 4.928): um HISTORY_SYNC grava **meses** de conversa em segundos, e tudo vira "rajada". Linha de controle, mesmas linhas, dois relógios, mesma regra de 30 s: **9.927** intervalos pelo `created_at` × **7.249** pelo `wa_timestamp` — **+39,2% de falsos positivos**. ⚠️ **Toda régua desta SPEC lê `attendance_transcripts.wa_timestamp`.** Uma janela calibrada em `created_at` é uma janela sobre o relógio do espelho — o defeito do CLAUDE.md §9.4 na versão relógio.

**Segundo elo, o da pergunta repetida — e aqui o diagnóstico estava errado.** Ele afirmou que *"a ficha guarda `apolice_confirmada: bool`, não os slots já respondidos"*. 📊 A ficha **tem** `confirmados: {}` (`attendance_ficha.py:136`) e **tem** o bloco *"JÁ CONFIRMADO com o cliente — **não pergunte de novo**"* (`attendance_ficha.py:274`), injetado no prompt em `graph.py:1459-1471`. O elo partido está **um passo antes**, no escritor:

```bash
cd backend && PYTHONIOENCODING=utf-8 python -c "
import re
rot=set(re.findall(r'\"([a-z0-9_]+)\":', re.search(r'ROTULOS = \{(.*?)\n\}', open('app/services/attendance_ficha.py',encoding='utf-8').read(), re.S).group(1)))
fic=set(re.findall(r'\"([a-z0-9_]+)\"', re.search(r'_SLOTS_DA_FICHA = \((.*?)\n\)', open('app/agents/nodes.py',encoding='utf-8').read(), re.S).group(1)))
print(len(rot), len(fic), len(rot-fic))"
# 📊 13/09/2026 → 35 15 20
```

📊 O vocabulário (`ROTULOS`) tem **35** slots; o escritor (`_SLOTS_DA_FICHA`, `nodes.py:836-847`) grava **15**. **20 nunca chegam à ficha** — entre eles `ponto_referencia`, que foi exatamente o slot que travou a sessão da Vivian em 10/09. E `agua_escorrendo`, o do "3 vezes", **não está em nenhum dos dois**: é slot do corredor (`corridor_playbooks.py:1302`, `:3826`, `:9712`) e da tool (`insurer_dispatch_tool.py:320`), e o vocabulário do atendimento não o conhece. **O bloco existe, é injetado, e está vazio para esses slots. B não chega em A porque B nunca é escrito.**

---

## 1. AUTORIZAÇÃO DE TESTES — a fronteira de todo pacote desta SPEC

### 1.1 Allowlist explícita e privada

| Alias | Número | Forma normalizada |
|---|---|---|
| **TESTE-A** | `[TESTE-A · allowlist privada]` | `+55TESTE-A` |
| **TESTE-B** | `[TESTE-B · allowlist privada]` | `+55TESTE-B` |

Os valores reais vivem **só** na configuração privada (o mesmo mecanismo já usado por `JANELA_SILENCIO_EXCECOES` e `ATTENDANT_INBOUND_ALLOWLIST`) e no prompt privado do chat executor. ⛔ **Não commitar, não publicar no dossiê, não escrever em log, fixture, screenshot ou relatório.** No canon, sempre os aliases.

### 1.2 O que está autorizado

- Implementar esta SPEC e executar o processo AAA com as permissões vigentes do projeto.
- **Canário vivo entre TESTE-A e TESTE-B**, em conexão cuja identidade efetiva foi conferida **hoje** (nome de corretora, rótulo de instância ou propósito **não** provam identidade).
- 🔴 **Novo nesta SPEC:** a **presença "digitando…"** é efeito externo — ela chega ao aparelho do segurado. No canário só pode ser enviada para TESTE-A/TESTE-B, e a mesma verificação da §1.4 vale para ela.
- Consultas **read-only** ao banco de produção para o BLOCO 0 e para gerar o corpus de rajadas (§13): **só contagens, intervalos e traços derivados**. ⛔ Nunca conteúdo de mensagem, CPF, telefone, nome, placa ou e-mail em saída, arquivo ou relatório.
- Rodar `backend/scripts/migrar_conversas_fantasma_lid.py` **em dry-run** quantas vezes quiser. O `--vivo` só depois da migration M1 aplicada e verificada (§11).

### 1.3 O que permanece proibido

1. Usar número operacional Resulta ou AutoFleet como remetente — **inclusive** para enviar ao Founder, **inclusive** presença.
2. Enviar a segurados, seguradoras, atendentes, grupos ou qualquer contato fora da allowlist — por texto, mídia, presença, alerta, fila, retry ou resposta automática.
3. Ligar o agente de atendimento globalmente numa corretora operacional para fazer o canário funcionar. Se a limitação seletiva não existir, **implementá-la antes**.
4. Acionar assistência real, abrir sinistro/chamado ou tocar portal.
5. Rodar `--vivo` do script das fantasmas sem a migration, sem VERIFY e sem backup conferido.
6. Alterar `JANELA_SILENCIO_EXCECOES` para "facilitar" um teste. A lista é de produção e o que ela faz muda nesta SPEC (§9.3).
7. Tratar restrição de canário como permissão para retirar controle de produção.

### 1.4 Verificação imediatamente antes de cada efeito

O guardião do canário confere, **na ordem**: ambiente · tenant · conversa/run de teste · conexão fixada · **identidade real do remetente** · destino normalizado · janela vigente · autorização do ator · orçamento de teste · **tipo de operação** (texto · mídia · **presença**). **Remetente e destinatário ambos na allowlist, e distintos.**

Se a identidade não puder ser confirmada, ou a sessão tiver sido trocada: **não enviar.** Não escolher outra conexão automaticamente. Não aceitar autorização deduzida pelo modelo. A normalização usa a autoridade de telefone brasileiro que já existe — ⛔ nunca comparação por últimos dígitos.

### 1.5 Falta de canal ou ação física do Founder

Continuar código, testes, gates, migrations em branch e preparação do rollout. Deixar para o Founder **apenas** a ação física indispensável (parear um número, clicar Implantar). **Ausência de canário não vira aprovação de produção** — vira gate não comprovado, escrito com esse nome.

---

## 2. Escopo completo e exclusões deliberadas

### Obrigatório nesta SPEC

1. **Trava de turno por conversa**, com token de dono, renovação com teto e reconferência de posse antes de enviar (§5).
2. **Janela adaptativa por conteúdo** (3 · 8 · 18 s), teto 25 s, **e a morte do piso rígido de 8 s** (§6.1).
3. **Mídia dentro do buffer**, nos **três** pontos, com legenda e arquivo no mesmo turno (§6.2).
4. **Re-planejamento**: reler o buffer e mesclar imediatamente antes de gerar (§6.3).
5. **Presença "digitando…"** pela Evolution, pelo provider que já existe, **só quando o agente vai mesmo falar** (§6.4).
6. **A ficha passa a guardar todo slot que o corredor exige**, derivado e não escrito à mão (§7).
7. **Guarda de pergunta repetida** sobre o motor e o acervo (§7.3).
8. **Apresentação condicional ao reencontro** — a decisão sai do modelo (§8.1); **hierarquia de tamanho medida** (§8.2); **identidade da thread fixada por assunto** (§8.3).
9. **Dedupe do espelho por `wa_message_id` no pipeline do agente** (§9.1).
10. **Uma conversa por contraparte** (LID × telefone) + as **175** fantasmas + a trava que impede a **176ª** (§9.2, §11).
11. **Ordem correta do silêncio** e **P-PILOTO-15**; **todo silêncio no feed com motivo** (§9.3, §9.4).
12. **Nome do agente** (D-PILOTO-12), inteiro: campo, apresentação, "especialista", troca, recusa de colisão, assinatura 🤖 (§10).

### Fora desta SPEC, sem empobrecer o outcome — a tabela completa com gatilho de retorno está em §21

Isolamento por corretora (fila/worker por tenant) → **EXTRA-001.8** · lista de números da casa e o que o grupo recebe → **EXTRA-001.3** · corredor que não trava e humano na URA → **EXTRA-001.4** · apólice certa e a porta `PolicyDataProvider` → **EXTRA-001.1** · teto no bloco de RAG e o "não recebi sua pergunta" → **EXTRA-001.1** · resumo das 19h e eficiência → **EXTRA-001.3** · troca de provedor de WhatsApp · Meta Cloud API · multicanal.

⚠️ **Um item de fronteira, declarado:** 📊 `graph.py:1394-1405` injeta `rag_prefetch_content` **sem teto**, e foi isso que sepultou a pergunta em dois turnos de 135k e 163k tokens (diagnóstico §1.2). **Isso é da 001.1**, e esta SPEC **não** mexe lá — mas o re-planejamento da §6.3 acrescenta texto ao mesmo prompt, então o BLOCO 0 **mede** o tamanho do prompt antes e depois, e se o acréscimo piorar o caso medido, a SPEC **para de acrescentar** e registra em `CHANGE-ADDENDA.md`.

---

## 3. Autoridades preservadas e arquitetura — o que já existe e por que não se cria nada ao lado

**CLAUDE.md §5 é a regra:** nunca criar em paralelo runtime, scheduler, executor, publisher. Esta SPEC **não cria nenhuma peça nova de infraestrutura.** Cada contrato abaixo diz onde mora e qual peça existente ele estende.

| o que a SPEC precisa | o que JÁ EXISTE, por caminho | por que serve |
|---|---|---|
| trava com lease | `app/api/webhook.py:1425-1427` e `:1496-1503` já usam `redis.set(..., nx=True, ex=...)` para dedupe de mensagem; `app/services/atlas/route_sentinel.py:103-107` já faz claim **com token de dono** e release comparando o valor; `backend/portal_worker/leases.py` tem o motor completo com Lua CAS (`:145-151`, `:154+`) | 🔴 a trava de turno é **o mesmo comando**, com outra chave e um token. Mora no módulo que já é dono das chaves Redis do buffer (`message_buffer_service.py`). **Zero motor novo** |
| isolamento multi-tenant da chave | `message_buffer_service.py:56-57` — `whatsapp_buffer:{escopo}:{phone}`, com `escopo` = id da integração, e a docstring `:36-55` explica o vazamento entre corretoras que isso corrigiu (SPEC-063 Bloco H) | a trava **herda a mesma chave**. Escopo novo seria escopo não provado |
| janela / debounce | `message_buffer_service.should_process` (`:133`) | a janela adaptativa **substitui a comparação**, não o mecanismo |
| paralelismo entre conversas | `app/tasks/buffer_processor.py:63-110`, com as peças recebidas por parâmetro *"porque é assim que o teste exercita ESTE motor com dublês"* (docstring `:69-71`) | ponto de enxerto **já testável pelo motor** (CLAUDE.md §9.4) |
| ficha de slots | `app/services/attendance_ficha.py` inteiro; coluna JSON `conversations.ficha_atendimento`; renderizador `bloco_para_o_prompt` (`:253-290`); injeção `graph.py:1459-1471` | **a ficha existe.** A SPEC fecha o buraco do escritor. **Nenhuma tabela nova** |
| vocabulário de slot | `attendance_ficha.ROTULOS` (`:75-113`), importado por `insurer_dispatch_service._rotulo` (`:1362`) — a docstring `:70-74` declara que é *"o ÚNICO vocabulário de rótulo do atendimento"* | acrescentar slot **ali** conserta os dois lados de uma vez |
| reencontro / religamento | `o_fim_do_atendimento.py:1460-1466` (`_ASSUNTO_NOVO`), `:1468-1474` (`_RELIGAMENTO`), `contexto_do_reencontro` **puro** (`:1490-1526`), `bloco_do_reencontro` (`:1529-1562`), montagem em `graph.py:1501-1512` | **o motor do reencontro existe e tem guarda** (`tests/test_a_ultima_palavra_humana_manda.py`, 573 linhas, motor real). A SPEC resolve o **conflito** dele com `prompts.py:359`, não o refaz |
| dedupe durável de mensagem | `backend/supabase/migrations/20260806_02_espelho_sem_duplicata.sql:41-43` — índice único parcial `(conversation_id, payload->>'wa_message_id')` | 🔴 **o índice existe.** A SPEC dá a **chave** às linhas do pipeline (`webhook.py:952-963`, `:1294-1300`), que hoje nascem sem `payload` e por isso ficam fora do índice |
| normalização LID × telefone | `app/services/whatsapp/identidade_do_evento.py:100-115`, módulo puro sem imports do produto (`:23-26`) | a normalização **existe e é boa**. O defeito é haver **duas** resoluções de conversa (`espelho_chat.py:502-505` × `webhook.py:936-945`) |
| migração das fantasmas | `backend/scripts/migrar_conversas_fantasma_lid.py` — dry-run por padrão (`:346-351`), pareamento só sem ambiguidade (`:113-137`), ordem obrigatória copiar-antes-de-fechar (`:35-38`), escritas com `.eq("company_id", …)` (`:308-315`, `:323-329`) | **reaproveitar.** Falta só o valor no CHECK |
| portão do silêncio | `o_fim_do_atendimento.a_ia_deve_calar` (`:1325`), `pausar_ia` (`:344`), `silenciar_por_palavra_humana` (`:1194`, pura), `anotar_silencio_no_feed` (`:1411`) | a SPEC **corrige a ordem** e **alarga o feed**. Nenhuma função nova de decisão |
| presença no WhatsApp | `app/services/whatsapp/providers/base.py` — `ProviderCapabilities` é *"the EXHAUSTIVE closed set … adding a new capability MUST start by adding a flag here, then having the fachada branch on it"*; `EvolutionProvider._post` (`evolution.py:286`) é o **único** ponto de saída HTTP | 🔴 o ponto de extensão **é declarado no próprio código**. Presença = uma flag + um método + um branch da fachada. **Nenhum cliente HTTP novo** |
| nome do agente | `agents.name` + `agents.context_package[…].variables.attendant_name` → `graph.py:1256-1261` → `prompts.py:350`; tela `app/dashboard/personalizacao/agentes/AgentConfigClient.tsx`; card Equipe em `company_members` + `users_v2` (`lib/admin/tenant-overview-store.ts:18-44`) | 🔴 **`conversations.agent_name` NÃO é esse campo** — é rótulo de origem com três hard-codes (`espelho_chat.py:535`, `dispatch_mirror.py:147`, `webhook.py:219`). A SPEC mexe no campo certo |

**Contrato lógico mínimo, sem obrigar tabela nova:**

```text
evento do WhatsApp (texto · imagem · áudio · documento)
→ identidade normalizada da contraparte (LID resolvido)      identidade_do_evento
→ buffer por (integração, contraparte), itens tipados         message_buffer_service
→ janela por CONTEÚDO, teto 25 s                              message_buffer_service (puro)
→ TRAVA DE TURNO por (integração, contraparte), com token     message_buffer_service (Redis)
→ portão do silêncio, com motivo                              o_fim_do_atendimento
→ presença "digitando…" (só se vai falar)                     provider Evolution
→ RE-LEITURA do buffer e mescla                               message_buffer_service
→ prompt com: ficha (slots já respondidos) + decisão de
  apresentação (calculada, não pedida ao modelo) + nome        attendance_ficha · o_fim_do_atendimento · prompts
→ geração
→ RECONFERÊNCIA de posse do turno + do silêncio
→ envio                                                        whatsapp_service
→ gravação com wa_message_id (entra no índice único)           webhook · espelho_chat
→ liberação da trava (comparando o token)
```

⚠️ **Arquivos-hub, com dono único por vez (AAA §3.4):** `app/api/webhook.py` (2.472 linhas) · `app/agents/graph.py` (2.290) · `app/services/o_fim_do_atendimento.py` (1.562) · `app/tasks/buffer_processor.py` (594 — registra **24** jobs do scheduler, não só o buffer) · `app/core/prompts.py` (660).

---

## 4. BLOCO 0 — converter medindo, antes de qualquer código de produto

> AAA §5 ①: *"o executor REMEDE o que a SPEC afirma. **O número dele vence**."* Este documento envelhece; o BLOCO 0 é quem o corrige.

0. 🔴 **ANTES DE TUDO — o candidato a P0 cross-tenant.** 📊 **104 de 134** `wa_message_id` repetidos aparecem sob **dois `company_id`** (RESEARCH-PACK §3.6), com texto idêntico, 6 contrapartes, nenhum `observer_number` compartilhado. Determinar a causa: ingestão cruzada? o mesmo segurado nas duas corretoras com id reaproveitado? **Confirmado como cross-tenant → PARE, registre em `FOUNDER-DECISIONS.md` e trate como P0 próprio** (CLAUDE.md §10 item 4 e §7). ⛔ **Nenhuma migration antes deste veredito** — M2 cria índice sobre `(company_id, contraparte)` e um dado cruzado faria a migration falhar ou, pior, passar.

1. **Preflight na ordem do CLAUDE.md §2**: `git fetch`, `HEAD..origin/main` (tem de ser **0** — diferente disso, **pare e pergunte**), `origin/main..HEAD`, branch, `git rev-parse HEAD` (vai no relatório), `git status --short`.
2. **Reabrir cada `arquivo:linha` desta SPEC e do RESEARCH-PACK.** Divergência → corrigir na SPEC definitiva **e anotar** (o RP §1 traz cinco correções já feitas ao diagnóstico; espere mais).
3. 🔴 **Recontar os desvios de mídia:** `grep -n 'type": "media"' backend/app/api/webhook.py` **tem de voltar 3**. Voltou 2 ou 4 → o mapa mudou e a unidade B muda com ele.
4. 🔴 **Remedir o buraco da ficha** com o comando de §0.3. Se `len(ROTULOS)-len(_SLOTS_DA_FICHA)` mudou, a lista derivada da §7.1 muda.
5. **Medir a duração real de um turno** (`get_and_clear_buffer` → envio), p50/p90/máx, sobre o acervo ou por instrumentação temporária. 🔴 **O TTL da trava sai deste número.** Os 💭 90 s da §5.2 são ponto de partida, não valor final.
6. **Medir os traços das mensagens reais** com a **função do motor** (`tracos_da_mensagem`), imprimindo só contagens: quantas terminam em pontuação final · quantas são dado curto · quantas terminam em conectivo. 🔴 CLAUDE.md §9.4: *medir com a ferramenta que vai usar*. Um número medido em SQL e aplicado em Python é um número sobre outra coisa.
7. **Gerar o corpus das 20 rajadas** (§13) e conferir que ele tem variedade de tamanho (2, 3, 4, 5+), de intervalo (faixas 0–3, 3–8, 8–18, 18–25, > 25 s), **mídia em pelo menos 3**, e **as duas corretoras**.
8. **Ler `MIGRATIONS-AUTHORITY.md` inteiro** antes de qualquer SQL. Medir o schema vivo de `conversations` e `messages` (colunas, constraints, índices, RLS, triggers) por `information_schema`/catálogo — **nunca por suposição**; e **quem é o escritor de cada coluna tocada** (a ficha tem **três**: `nodes.py:849+`, `human_handoff.py:1078-1084`, `atendimento/acompanhamento.py:419-441`).
9. **Recontar as fantasmas.** 📊 13/09: 860 conversas, **175 fantasmas** (106 AutoFleet, **69** Resulta), **100% abertas**, **10** com pausa presa, **9** com par real, **166 sem par** (RESEARCH-PACK §3.5). ⚠️ Eram **174** em 09/09: **nasce cerca de uma por dia**, e é isso que a trava da M2 para. ⚠️ Divergência a resolver: o script diz **7** com pausa (`migrar_conversas_fantasma_lid.py:24-31`, medição de 09/09), o banco diz **10** hoje — **o dry-run do BLOCO 0 decide**, e o número dele vence.
10. **Confirmar se o fork Evolution Go implantado tem `POST /chat/sendPresence/{instance}`** (`rotas_de_envio_medidas()`, `evolution_go.py:577`). 🔴 **Não tem → a presença fica desligada, com pendência nomeada. Não se simula "digitando…".**
11. **Rodar os guardas que não podem quebrar** e anotar o verde de partida: `tests/test_midia_e_concorrencia_do_webhook.py`, `tests/test_a_ultima_palavra_humana_manda.py`, `tests/test_a_janela_esta_ligada_nos_portoes.py`, `tests/test_quem_fala_primeiro_cala_o_outro.py`, `tests/test_o_atendimento_tem_memoria.py`, os três do espelho.
12. **Reencontrar por número** P-PILOTO-13, 15, 16, 17, 18 e dar `FECHADA` / `CONTINUA` / `MORREU` (AAA §2). ⚠️ P-PILOTO-15 **não é** o que o plano de execução supôs — o texto real fala de `resolvido_em`, não da ordem das checagens. **As duas coisas entram** (§9.3).

**GATE B0.** Matriz `premissa → observação nova → comando/consulta → decisão`, mapa de efeitos externos (texto · mídia · **presença**) e autorização do canário. Nenhum achado não reproduzido é vendido como incidente confirmado. Achado já fechado → testar, reaproveitar e **dizer que fechou**.

**MUTAÇÃO B0.** O desenhista entrega ao aquecimento premissas deliberadamente falsas, assinadas (§6 do prompt de abertura). O executor as refuta **com comando**. Permissões reais não se alteram no exercício.

---

## 5. BLOCO A — a trava de turno por conversa

### 5.1 O contrato

Tudo em `backend/app/services/message_buffer_service.py` (o módulo que já é dono das chaves Redis do buffer) e `backend/app/tasks/buffer_processor.py`.

```python
# --- message_buffer_service.py -------------------------------------------
TURNO_PREFIXO = "whatsapp_turno"          # irmão de "whatsapp_buffer"
TURNO_TTL_SEGUNDOS: int                   # do settings; 💭 90 de partida, MEDIDO no BLOCO 0
TURNO_RENOVACOES_MAX = 3                  # teto — E01 exige teto na renovação

@staticmethod
def chave_do_turno(escopo: str, phone: str) -> str
    """`whatsapp_turno:{escopo}:{phone}` — MESMO escopo do buffer (SPEC-063 Bloco H)."""

async def abrir_turno(self, escopo: str, phone: str, *, ttl_s: int = 0) -> Optional[str]
    """`SET chave token NX EX ttl`. Devolve o TOKEN se ganhou; `None` se outro está no turno.
    O token é `uuid4().hex` — E01: "set a non-guessable large random string"."""

async def renovar_turno(self, escopo, phone, token: str, *, ttl_s: int = 0) -> bool
    """EVAL: renova SÓ se o valor ainda for o token. No máximo TURNO_RENOVACOES_MAX vezes."""

async def ainda_sou_o_dono(self, escopo, phone, token: str) -> bool
    """A reconferência antes de enviar. E01: 'don't assume that a lock is retained
    as long as the process that had acquired it is alive'."""

async def fechar_turno(self, escopo, phone, token: str) -> bool
    """EVAL com o script oficial da doc do Redis (§20 E01). ⛔ NUNCA `DEL` cego."""
```

O script de liberação é o **literal da documentação** (§20 E01), e o VERIFY do juiz é abrir a página e comparar:

```lua
if redis.call("get",KEYS[1]) == ARGV[1] then return redis.call("del",KEYS[1]) else return 0 end
```

### 5.2 Onde a trava entra, e por que **antes** do `get_and_clear`

`buffer_processor._uma(chave)` passa a ser:

```python
async def _uma(chave: str) -> bool:
    async with semaforo:
        escopo, phone = partes_da_chave(chave)          # "whatsapp_buffer:{esc}:{phone}"
        if not await buffer_service.should_process(chave):
            return False
        token = await buffer_service.abrir_turno(escopo, phone)
        if token is None:
            return False        # 🔴 o buffer FICA. A varredura de 1 s tenta de novo
        try:
            buffer = await buffer_service.get_and_clear_buffer(chave)
            if not buffer:
                return False
            await processar(payload_dict=buffer["payload"],
                            combined_message=buffer_service.get_combined_message(buffer),
                            buffered_messages=...,
                            turno=Turno(escopo, phone, token))   # parâmetro NOVO, opcional
            return True
        finally:
            await buffer_service.fechar_turno(escopo, phone, token)
```

🔴 **A ordem é a regra inteira.** Se a trava viesse depois do `get_and_clear`, perder a trava custaria o buffer — as cinco mensagens do segurado sumiriam. Perder a trava **antes** custa 1 segundo.

**"Mensagem que chega com a trava tomada volta ao buffer"** — e volta pelo caminho mais simples que existe: ela **nunca sai**. O webhook sempre escreve no buffer (`_buffer_or_dispatch_text`, `webhook.py:1593-1604`), e a varredura só a retira quando ninguém está no turno.

### 5.3 Por que a chave é `(escopo, telefone)` e não `(company_id, conversation_id)`

O pedido original diz `company_id + conversation_id`. **Em substância é o mesmo**, e a forma escolhida é melhor por três razões medidas:

1. 📊 `escopo` **é** o id da integração, e uma integração pertence a **uma** corretora — a chave do buffer já carrega o tenant desde a SPEC-063 Bloco H, e a docstring `message_buffer_service.py:36-55` registra o vazamento entre corretoras que essa decisão corrigiu. Herdar essa chave é herdar isolamento **provado**. 🔴 O BLOCO 0 confirma com um `SELECT` que nenhuma integração serve duas corretoras.
2. 📊 `company_id` **não está disponível** no caminho: `webhook.py:1593-1604` grava o buffer com `company_id="pending"` literal. Resolver o tenant antes da trava custaria uma consulta ao banco no caminho mais quente do produto.
3. `conversation_id` exigiria leitura no banco. 🔴 E **depois do BLOCO E** a contraparte normalizada é 1:1 com a conversa — que é exatamente o que o G11 prova. **A trava fica correta porque o BLOCO E existe**; sem ele, a mesma pessoa teria duas chaves. Esta dependência é interna à SPEC e está no plano de integração (§18.1).

O `company_id` continua obrigatório **onde importa**: no feed, no log e em toda leitura/escrita do banco (CLAUDE.md §7).

### 5.4 A trava é por CONVERSA — e a prova disso é um teste que já existe

⛔ **Trava por corretora é o defeito da EXTRA-001.8, não o conserto desta SPEC.** `tests/test_midia_e_concorrencia_do_webhook.py:519` (`teste_o_buffer_processa_em_paralelo`) afirma hoje que conversas diferentes rodam em paralelo, e carrega o motor real por AST (`:61-89`). 🔴 **Esse teste é a LINHA DE CONTROLE (CLAUDE.md §9.2): ele tem de continuar verde depois da trava.** A mutação "chave da trava sem o telefone" (global por corretora) o deixa **vermelho** — e é assim que se prova que a trava não virou gargalo.

### 5.5 Fencing possível: reconferir a posse antes de enviar

E01 é explícita: *"don't assume that a lock is retained as long as the process that had acquired it is alive"* e *"Redis is not using monotonic clock for TTL expiration mechanism"*. Não temos token monotônico. O que temos é o ponto de efeito, e ele é um só: `webhook.py:1330-1345`.

**Contrato:** imediatamente antes de `whatsapp_service.send_message`, no mesmo bloco onde hoje se reconfere o silêncio (`webhook.py:1240-1290`), o turno chama `ainda_sou_o_dono(...)`. **Falso → não envia**, registra `turno_perdido` no feed com motivo legível 💭 *"a resposta demorou mais que o turno; outra rodada já respondeu"*, e a resposta pronta é **descartada** — exatamente como já se faz quando a atendente assume no meio (`webhook.py:1266-1290`). ⛔ Nunca enviar "por via das dúvidas": duas respostas para uma pergunta é o defeito que esta SPEC existe para matar.

**GATE A.** 20 rajadas do corpus pelo motor `processar_buffers_prontos` → **1 turno cada**; conversas diferentes continuam paralelas (o teste existente verde); duas tarefas concorrentes na mesma conversa → uma ganha, a outra devolve `False` **sem tocar o buffer**; turno que estoura o TTL não envia.
**MUTAÇÃO A.** (a) `abrir_turno` devolve sempre um token → as rajadas fragmentam → **vermelho**; (b) chave da trava sem o telefone → o teste de paralelismo → **vermelho**; (c) `fechar_turno` com `DEL` cego → o teste de posse → **vermelho**.

---

## 6. BLOCO B — a janela que escuta o conteúdo, a mídia que entra, e o "digitando…"

### 6.1 A janela adaptativa — e a morte do piso de 8 s

**Hoje:** `message_buffer_service.py:158` fecha a rajada com `max(settings.BUFFER_DEBOUNCE_SECONDS, 8)` e `:166` com `max(settings.BUFFER_MAX_WAIT_SECONDS, 25)`. 🔴 **O `max(…, 8)` torna a janela de 3 s impossível**, por construção e por qualquer configuração.

**Contrato — duas funções PURAS, e é de propósito que sejam duas:**

```python
@dataclass(frozen=True)
class Tracos:
    n_chars: int
    termina_em_pontuacao_final: bool     # . ! ? … e o emoji final conta como fim
    termina_em_conectivo: bool           # lista fechada em português: "e", "mas", "porque", "que",
                                         # "de", "para", "com", "aí", "então", "só que", …
    dado_curto: bool                     # ≤ N chars E (só dígitos/pontuação OU palavra de confirmação)
    tipo: str                            # "text" | "image" | "audio" | "document"

def tracos_da_mensagem(texto: str, *, tipo: str = "text") -> Tracos:
    """Roda sobre o TEXTO REAL. É esta função que o script de medição aplica ao acervo."""

def janela_de_espera(t: Tracos) -> int:
    """Segundos de ociosidade que fecham a rajada. PURA, sem I/O, sem settings."""
    #  3 s  dado curto        — CPF, placa, CEP, "sim", "não", "ok", um número
    # 18 s  frase inacabada   — sem pontuação final, ou terminando em conectivo
    #  8 s  frase completa    — o comportamento de hoje, preservado

TETO_DA_RAJADA_SEGUNDOS = 25   # 🔴 é o número da Meta (§20 E02), não um palpite nosso
```

`should_process` passa a ler o **último item** do buffer e a usar `janela_de_espera(tracos_da_mensagem(...))` no lugar do `max(...)`. O teto continua desde `first_at`, agora pela constante.

🔴 **A regra do comando (AAA §0.4) se aplica ao valor que morre:** depois da mudança, `grep -rn "max(settings.BUFFER" backend/` tem de voltar **vazio**. *"Sobrevivente = defeito."*

**Por que 3 · 8 · 18 — e agora com a distribuição real ao lado.** 📊 Medido em 13/09/2026 sobre **51.883** intervalos dentro de rajada, pelo relógio certo (`wa_timestamp`; consulta no RESEARCH-PACK §3.1):

| | min | p25 | mediana | p75 | p90 | máx |
|---|---|---|---|---|---|---|
| intervalo dentro da rajada | 0 s | 0 s | **1 s** | 8 s | 17 s | 30 s |

| faixa | intervalos | % | acumulado |
|---|---|---|---|
| **0–3 s** | 29.065 | **56,0%** | 56,0% |
| 3–8 s | 8.579 | 16,5% | **72,5%** |
| **8–18 s** | 9.253 | 17,8% | **90,3%** |
| 18–25 s | 3.508 | 6,8% | 97,1% |
| > 25 s | 1.478 | 2,8% | 100% |

🔴 **É esta tabela que justifica a janela por conteúdo, e não um número só.** Uma janela fixa de 8 s agrega **72,5%** dos intervalos e deixa 27,5% fragmentando. Uma janela fixa de 18 s agrega **90,3%** — e cobra **18 segundos de espera de toda resposta**, inclusive daquela em que o segurado só disse "sim". 📊 Como **56,0%** dos intervalos são ≤ 3 s, a maioria das rajadas fecha rápido **se a janela souber que a mensagem acabou**; e os 17,8% da faixa 8–18 s são exatamente os que uma frase inacabada explica. As três rajadas do piloto tinham **10, 12 e 22 s** — os 8 s de hoje perdem as três; 18 s pega duas; o teto de 25 s pega a terceira.

⚠️ **O que ainda falta para fechar a calibragem, e é do BLOCO 0:** a distribuição acima é **por intervalo**, não **por classe de traço**. Quantos dos intervalos ≤ 3 s vêm depois de um dado curto? Quantos dos de 8–18 s vêm depois de frase inacabada? 🔴 Isso exige aplicar `tracos_da_mensagem` ao **texto real**, e esta proposta não leu texto. É o item 6 do BLOCO 0, e é o que pode mover 3 · 8 · 18 para outros números — **o número do executor vence** (AAA §5 ①).
⚠️ `wa_timestamp` tem granularidade de **segundo inteiro** (o `messageTimestamp` do WhatsApp é em segundos): o p25 = 0 s é real, e ⛔ **não há como validar a classe "dado curto" contra intervalos sub-segundo neste acervo**.
⚠️ **E não há de onde copiar os números:** a pesquisa não achou **nenhuma** plataforma que documente janela de agregação com segundos recomendados, e **nenhum** projeto aberto com janela adaptativa por conteúdo (§20 E07). **A invenção é nossa, e é declarada como tal.**

### 6.2 A mídia entra no buffer — nos três pontos

**Hoje:** três lugares desviam imagem e áudio para geração imediata — `webhook.py:1449-1452` (rota legada), `:1634-1637` (z-api com token), **`:2226-2229`** (`_handle_evolution_like_inbound`, o caminho quente de `/evolution/{token}` e `/evolution-go/{token}`). ⚠️ E `documento_payload` (`:2206`) **já** cai no buffer — a assimetria é acidental.

📊 **O tamanho do buraco, medido em 13/09:** **5.608 de 20.727 rajadas têm mídia — 27,06%.** Entrada de cliente por tipo: text 68.943 · **áudio 7.302** · **imagem 4.652** · **documento 2.744** · sticker 381 · buttons 361 · vídeo 310 · list 97. 🔴 E há rajadas **100% mídia** no acervo (6 de 6, 5 de 5, 4 de 4 entre as candidatas do corpus) — nessas, **o buffer hoje não vê nada**.

**Contrato — a forma do buffer muda, com compatibilidade in-flight:**

```json
{ "v": 2,
  "itens": [
    {"tipo":"text",  "texto":"...",                   "wa_message_id":"...", "em":"..."},
    {"tipo":"image", "legenda":"...", "midia":{...},  "wa_message_id":"...", "em":"..."}
  ],
  "first_at":"...", "last_at":"...", "payload":{...}, "integration":{...} }
```

- `get_combined_message` lê `itens` quando `v == 2` e `messages` quando não — 🔴 **a migração é in-flight e dura ≤ 60 s**, porque `BUFFER_TTL_SECONDS` é 60 (`config.py:75`) e o TTL é reescrito a cada mensagem (`:127`). O executor **não** precisa drenar Redis à mão; precisa **não quebrar** o formato velho por um minuto.
- A legenda e o arquivo entram como **um item**, e o turno recebe os dois juntos.
- A regra de `interactive` que já existe (`message_buffer_service.py:109-113`: *"interativa nova vence a antiga; ausência não vence presença"*) **é o precedente** e continua valendo.
- ⚠️ `.env.example:40-42` ainda ensina `BUFFER_TTL_SECONDS=300`. Corrigir junto, senão um ambiente novo nasce com 5 min de buffer órfão.

### 6.3 Re-planejamento: reler o buffer imediatamente antes de gerar

```python
async def mesclar_o_que_chegou(self, chave: str) -> list[dict]:
    """Pipeline get+delete atômico (o mesmo de `get_and_clear_buffer`). Devolve os
    itens que chegaram DEPOIS do início do turno, ou lista vazia."""
REPLANEJAMENTOS_MAX = 2
```

Chamado em `process_whatsapp_message_background`, **imediatamente antes** da chamada ao modelo. Itens novos → acrescentados ao texto combinado, e o turno recomeça a montagem do prompt (não a geração já feita). Teto de 2, para não virar laço: depois disso, o que chegar fica no buffer e vira **a segunda resposta** — que é a razão de o outcome dizer *"uma resposta, no máximo duas"*.

🔴 **O que isto mata:** a mensagem que chega no segundo 9 de uma janela de 18 s hoje espera o turno inteiro e vira resposta separada. Com a releitura, ela entra na mesma.
⚠️ **O que isto NÃO mata:** a mensagem que chega **durante** a geração do modelo. Essa fica no buffer e a trava impede que vire turno paralelo — ela é respondida no turno seguinte, **inteira**, e o prompt já sabe o que foi dito antes.

### 6.4 A presença "digitando…" — e a regra que impede a promessa vazia

📊 **13/09/2026: não existe nenhuma chamada de presença no produto.** `grep -rn "sendPresence|setPresence|composing|presenceSubscribe" backend/app/` volta só comentários de eventos de **entrada ignorados** (`providers/evolution.py:89,157`) e o gate que os **rejeita** (`providers/uazapi.py:127,140`). O único reconhecimento do problema é um comentário: `buffer_processor.py:39` — *"é o segurado nº 4 olhando para o 'digitando…' que não vem"*.

**Contrato, pelo ponto de extensão que o próprio código declara** (`providers/base.py`: *"adding a new capability MUST start by adding a flag here, then having the fachada branch on it"*):

```python
# providers/base.py
class ProviderCapabilities:
    presence: bool = False          # flag NOVA no conjunto fechado

class WhatsAppProvider(Protocol):
    async def send_presence(self, to: str, presence: str, delay_ms: int) -> SendResult: ...

# providers/evolution.py — pelo _post que já existe (:286)
#   POST {base}/chat/sendPresence/{instance}   body: {"number", "presence", "delay"}
#   presence ∈ {unavailable, available, composing, recording, paused}   (§20 E03: os três são
#   obrigatórios no schema do projeto)
```

**As cinco regras de produto, cada uma com a razão:**

1. 🔴 **Só depois do portão de silêncio.** `a_ia_deve_calar` roda **antes** (`webhook.py:766-769`). Vai calar → **nenhuma presença**. E02, literal: *"only display a typing indicator if you are going to respond."* Mostrar "digitando…" e não responder é pior que silêncio.
2. **Renovar a cada ≤ 20 s** enquanto o turno gera — é a fatia que a própria Evolution usa (`whatsapp.baileys.service.ts`, laço de 20 000 ms, §20 E03).
3. **Teto de 25 s**, a mesma constante do teto da rajada — porque é o tempo em que a Meta apaga o indicador sozinha (E02, literal: *"dismissed … after 25 seconds"*).
4. **`paused` ao terminar**, sempre, inclusive quando o turno é descartado por perda de posse ou por takeover.
5. **Quando a resposta já está pronta**, usar `delay` no próprio `sendText` em vez de uma segunda chamada — 📊 o código da Evolution mostra que `delay` **é** `composing` por N ms antes de enviar.

⚠️ **Degradação honesta:** se o fork Go implantado não expuser a rota (BLOCO 0 item 10), a flag `presence` fica `False`, a fachada não chama, **e o relatório diz isso com todas as letras**. ⛔ Não se inventa "digitando…" com uma mensagem de texto.

**GATE B.** As 20 rajadas do corpus → 1 turno cada, pelo motor; rajada com foto → **um** turno contendo legenda **e** arquivo; mensagem que chega no meio da janela entra na mesma resposta; `grep "max(settings.BUFFER"` volta vazio; presença só sai depois do portão.
**MUTAÇÃO B.** (a) `janela_de_espera` fixa em 8 s → N rajadas do corpus fragmentam → **vermelho**; (b) religar o desvio de `webhook.py:2226` → a rajada com foto vira 2 turnos → **vermelho**; (c) `mesclar_o_que_chegou` devolve `[]` → a mensagem do meio se perde → **vermelho**; (d) presença antes do portão → o guarda que conta "digitando…" sem resposta → **vermelho**.

---

## 7. BLOCO C — a ficha sabe o que já foi respondido

### 7.1 O conserto é no ESCRITOR, e ele deixa de ser lista escrita à mão

📊 `_SLOTS_DA_FICHA` (`nodes.py:836-847`) é uma **tupla literal de 15 nomes**. `ROTULOS` (`attendance_ficha.py:75-113`) tem **35**. Os corredores exigem slots que **não estão em nenhum dos dois** (`agua_escorrendo`, `vazamento_local`, `risco_confirmado_registro_fechado`, `caixas_dagua_quantidade_opcao`, …). Duas listas escritas à mão divergem no dia em que alguém acrescenta um slot num lado só — **e já divergiram.**

**Contrato:**

```python
# attendance_ficha.py
def slots_do_atendimento() -> frozenset[str]:
    """Todo slot que o produto pode coletar do segurado. DERIVADO, nunca escrito à mão:
       ROTULOS  ∪  todos os `required_slots` declarados em corridor_playbooks
       menos     CAMPOS_DE_CONTROLE (lista fechada e justificada, ex.: `dados_confirmados`)
    """
ROTULOS: dict[str, str]   # ganha rótulo em português para CADA slot novo — o rótulo é o que
                          # o modelo lê, e chave técnica não ajuda o modelo a conversar
```

`nodes._gravar_ficha_do_turno` passa a usar `slots_do_atendimento()` no lugar da tupla. ⛔ **A tupla literal morre** — `grep -n "_SLOTS_DA_FICHA = (" backend/app/agents/nodes.py` tem de voltar vazio (AAA §0.4).

🔴 **O guarda que fecha a porta é vermelho HOJE** (gate zero, AAA §8): *"todo `required_slots` de todo corredor está em `ROTULOS` e é gravado na ficha"* falha agora, em `agua_escorrendo`, e essa é a prova de que ele consegue ficar vermelho (CLAUDE.md §9.3).

⚠️ **Não mexer no que já está certo:** `_tem_valor` (`attendance_ficha.py:119`) recusa `"não informado"` como confirmação — é o que impede a ficha de declarar completo um atendimento que não está. `fundir` (`:174`) é aditivo: valor novo só sobrescreve se não for vazio. Os **três** escritores da coluna (`nodes.py`, `human_handoff.py:1078-1084`, `acompanhamento.py:419-441`) continuam sendo três; o BLOCO 0 confirma que cada um é dono de chaves diferentes.

### 7.2 O bloco no prompt já existe — e o que muda nele

`bloco_para_o_prompt` (`attendance_ficha.py:253-290`) já lista o confirmado (`:273-277`) e o que falta (`:278`), com a frase *"JÁ CONFIRMADO com o cliente — **não pergunte de novo**"* (`:274`). Injeção em `graph.py:1459-1471`, dentro do gate de papel de `graph.py:1453`.

**Muda uma coisa só:** o bloco passa a nomear **a origem** de cada confirmação — *"o cliente disse"* × *"veio do sistema de gestão"*. 💭 Porque um dado que veio do cadastro pode precisar de confirmação, e um dado que o segurado disse **não pode ser perguntado de novo, nunca**. Sem isso o modelo trata os dois igual, e foi assim que ele pediu confirmação de placa que a InfoCap já tinha resolvido.

⚠️ **Guarda frágil a promover:** `tests/test_o_atendimento_tem_memoria.py:204` protege este caminho afirmando que a **string** do `import` existe em `graph.py`. 🔴 Isso é exatamente o que CLAUDE.md §9.4 proíbe: prova que o import está escrito, não que a ficha chega ao prompt. O guarda G7 substitui a afirmação por uma chamada ao motor.

### 7.3 O guarda de pergunta repetida — sobre o motor, e sobre o acervo

```python
def slots_reperguntados(resposta: str, ficha: dict, *, corredor: str) -> list[str]:
    """Quais slots JÁ CONFIRMADOS a resposta volta a perguntar. PURA."""
```

A detecção usa **âncoras por slot**, e as âncoras vêm do acervo, nunca da imaginação (CLAUDE.md §9.4: *"o passo `numero_residencia` exigiu por semanas uma frase com ZERO ocorrências em 28.096 eventos"*). O BLOCO 0 extrai, para cada slot do corredor ativo, as formas reais com que o agente já perguntou aquilo, e **declara no relatório os slots que ficaram sem âncora**. ⛔ Slot sem âncora **não** é silenciosamente aprovado: aparece na lista "sem âncora" e o guarda diz quantos são.

**Em produção:** a resposta gerada passa por `slots_reperguntados`. Não vazia → **uma** regeneração com a lista explícita no prompt; persistiu → **envia assim mesmo** e registra `pergunta_repetida` no feed com os slots. 🔴 Travar a resposta do segurado para proteger uma regra de estilo seria trocar um defeito silencioso por um barulhento (CLAUDE.md §9.5).

**GATE C.** (1) todo `required_slots` de corredor existe em `ROTULOS` e é gravado — **vermelho hoje**; (2) replay estrutural da conversa do encanador de 10/09: com `agua_escorrendo` confirmado na ficha, a pergunta **não** volta; (3) `slots_reperguntados` roda sobre o texto real das respostas do acervo e o relatório traz a contagem.
**MUTAÇÃO C.** (a) esvaziar `ficha["confirmados"]` antes da montagem → o guarda (2) → **vermelho**; (b) devolver `slots_do_atendimento()` = a tupla velha de 15 → o guarda (1) → **vermelho**.

---

## 8. BLOCO D — a apresentação, o tamanho e a identidade da thread

### 8.1 A apresentação deixa de ser decisão do modelo

**O conflito, medido.** `prompts.py:359` (bloco **estático e cacheado**) diz `- SEMPRE se apresente com nome E corretora na primeira mensagem`. `o_fim_do_atendimento.py:1472` (bloco **dinâmico**) diz `Continue de onde parou, sem se reapresentar`. 🔴 **Duas instruções, dois blocos, e a estática vem primeiro no prompt.** O modelo lê "primeira mensagem" como "primeira **minha**", e cumprimenta no meio de um sinistro com vítima.

**Contrato — a decisão vira código, e o prompt recebe só o resultado:**

```python
# o_fim_do_atendimento.py — onde o reencontro já mora, ao lado de contexto_do_reencontro (:1490)
def deve_se_apresentar(*, assunto_novo: bool, apresentado_neste_assunto: bool,
                       nome_atual: str, nome_da_apresentacao: str) -> tuple[bool, str]:
    """(apresenta?, modo) — PURA. modo ∈ {"", "primeira", "mudou_de_nome"}"""
```

`prompts.py:355-361` perde a palavra `SEMPRE` e a frase condicional some do bloco estático. O bloco **dinâmico** passa a receber **uma** das três linhas:

| modo | o que entra no prompt |
|---|---|
| `primeira` | `APRESENTE-SE agora, uma vez, assim: …` |
| `""` | `NÃO se apresente: você já está nesta conversa. Continue de onde parou.` |
| `mudou_de_nome` | `Você mudou de nome desde a última vez. Diga isso UMA vez, assim: …` |

💭 **Copy proposta** (ilustrativa; o tom final vem do Jeito de atender da corretora):
- primeira · *"Oi! Aqui é a {agent_name}, assistente virtual da {corretora}. Como posso ajudar?"*
- mudou de nome · *"Oi! Aqui é a {agent_name}, da {corretora} — antes eu me apresentava como {nome_anterior}."*

⚠️ **O guarda do reencontro já existe e é bom:** `tests/test_a_ultima_palavra_humana_manda.py` (573 linhas, motor real, com linha de controle em `:490`) exercita `contexto_do_reencontro` e `bloco_do_reencontro`. A SPEC **acrescenta** casos a ele em vez de criar arquivo novo. E `o_fim_do_atendimento.py:1513` (`_TURNO_SEGUNDOS` de folga, para a mensagem recém-chegada não ser lida como "a última") **não muda**.

### 8.2 Hierarquia de tamanho — a regra já está escrita; falta o número

📊 As regras **existem** em `prompts.py`: `:87` *"Frases CURTAS (1 a 3 por mensagem). Nada de textão"* · `:95-100` bloco de perguntas com **máximo 4 itens** · `:102-108` **exceção documental** (lista inteira numa mensagem só, mesmo com 20 itens). E ainda assim o piloto mediu mensagens de até **760 caracteres**.

🔴 **Trocar o texto do prompt não é conserto** (AAA §3: *"NÃO SEI SE O MODELO OBEDECE → é PROVA: mostre o modelo fazendo. Mais gente não ajuda"*).

**Contrato:**

```python
def classe_do_tamanho(resposta: str, *, contexto: str) -> tuple[str, int, int]:
    """(classe, n_frases, n_chars) — PURA. classe ∈ {"conversa", "lista_documental",
    "bloco_de_ate_4", "avisar"}"""
TETO_POR_CLASSE = {"conversa": 3, "bloco_de_ate_4": 4, "lista_documental": 0, "avisar": 1}
#                                                        0 = sem teto, é a exceção declarada
```

Fora da classe → **uma** regeneração; persistiu → envia e registra. 📊 O relatório traz a distribuição de tamanho **antes e depois**, sobre o acervo, com a query.

⚠️ **Régua correta:** `whatsapp/balloons.py:17-20` já quebra a resposta em até **4 balões** (`TARGET_LEN=300`, `HARD_LEN=500`, `MAX_BALLOONS=4`). 🔴 **"Uma resposta por rajada" é UM TURNO, nunca um balão.** Medir balões mediria a humanização, não a fragmentação.

### 8.3 A identidade da thread, fixada a cada assunto novo

**O defeito, medido:** o agente abriu um caso chamando o cliente pelo nome de **outra pessoa de 22 dias atrás** — a thread por telefone nunca reinicia (diagnóstico §1.4). E 📊 `graph.py:1517` monta o estado com **exatamente duas** mensagens (`[SystemMessage, HumanMessage]`); os 60 turnos de histórico vivem noutra camada (`langchain_service.py:417-428`, `CHAT_HISTORY_WINDOW=60`) e a continuidade real vem do checkpointer do LangGraph, com `thread_id = f"{company_id}:{session_id}"` (`graph.py:1545`).

**Contrato — sem coluna nova, sem tabela nova.** A identidade mora dentro da ficha, que já é uma coluna JSON:

```python
ficha["identidade"] = {
  "assunto_id":        "...",   # muda quando o assunto novo começa (o motor do reencontro já sabe)
  "titular_nome":      "...",   # o nome com que o agente trata o segurado NESTE assunto
  "apresentado_em":    "...",
  "nome_da_apresentacao": "..." # o nome com que o AGENTE se apresentou (§10.3)
}
```

Assunto novo ⇒ `identidade` é **reescrita**, nunca herdada. 🔴 E o nome do segurado entra no prompt **só** de `identidade.titular_nome` — ⛔ nunca de memória, nunca de bloco de RAG, nunca do histórico. É o que impede o nome de 22 dias atrás de reaparecer.

**GATE D.** Replay estrutural da conversa do encanador de 10/09 pelo motor → **0 cumprimentos fora da abertura**; troca de `agent_name` no meio → nenhuma reapresentação naquele assunto, e **uma** no assunto seguinte; distribuição de tamanho medida antes/depois; assunto novo → `identidade` reescrita.
**MUTAÇÃO D.** (a) devolver `SEMPRE se apresente` ao bloco estático → **vermelho**; (b) `deve_se_apresentar` sempre `True` → **vermelho**; (c) herdar `identidade` no assunto novo → o nome antigo volta → **vermelho**.

---

## 9. BLOCO E — uma conversa, uma linha, e todo silêncio com motivo

### 9.1 Dedupe do espelho — e o achado que muda o desenho

📊 **O índice único existe desde 06/08/2026** — `20260806_02_espelho_sem_duplicata.sql:41-43`, parcial sobre `(conversation_id, payload->>'wa_message_id')` onde o campo não é nulo. O espelho grava com a chave (`espelho_chat.py:588-614`) e trata o 23505 (`:571-579`). 📊 E a chave está preenchida em **96,03%** das 33.565 linhas de `messages`.

🔴 **O pipeline do agente grava sem `payload`** — `webhook.py:952-963` (mensagem do segurado) e `:1294-1300` (resposta da IA). Linhas sem `wa_message_id` ficam **fora** do índice parcial.

🔴🔴 **E aqui a medição de 13/09 desmente a suposição do diagnóstico.** Contando os ids repetidos:

| | |
|---|---|
| `wa_message_id` repetidos | **134** · 273 linhas · **139 excedentes** |
| **na mesma conversa** | **0** |
| **em conversas DIFERENTES** | **134 — 100%** |
| **atravessando CORRETORAS** | 🔴 **104** |

**O índice funciona exatamente como escrito — e é por isso que ele não pega nada disto: ele é único POR CONVERSA.** Duplicata dentro da conversa é impossível; entre conversas é livre. **Dar a chave ao pipeline conserta um caso que 📊 é 0 de 134.** O que realmente produz a leitura em dobro é a mesma mensagem sob **duas conversas** — e é o BLOCO E2 (uma conversa por contraparte) que ataca isso.

Cruzando com as fantasmas: **35 dos 134** são par fantasma × real — o LID responde por ~26%. 🔴 **Os outros 99 se repetem entre duas conversas REAIS**, e a migração das fantasmas não os toca.

🔴 **Os 104 que atravessam corretoras são candidato a P0 cross-tenant.** O medidor investigou antes de reportar: os grupos repetidos têm **texto idêntico** (0 com texto diferente → **não é colisão de id**), tocam 6 contrapartes, **nenhuma é seguradora**, e **nenhum dos 5 `observer_number` aparece em mais de uma empresa**. **INFERÊNCIA, não fato:** a mesma mensagem está gravada sob dois `company_id`. ⛔ **Isto é investigado no BLOCO 0, antes de qualquer migration** (§4 item 0). Confirmado como cross-tenant, é uma das oito condições de parada do CLAUDE.md §10 (item 4): **pare, registre em `FOUNDER-DECISIONS.md`, e o conserto vira P0 próprio** — não se empilha dentro desta SPEC.

**Contrato (vale de qualquer forma, e é barato):**
- Os dois inserts passam a gravar `payload = {"wa_message_id": ..., "origem": "agente", "direcao": ...}` e a tratar 23505 como **sucesso silencioso**, exatamente como o espelho já faz.
- Para a **resposta da IA** o id só existe depois do envio. Ordem: gravar a linha (para não perder a resposta se o envio falhar) → enviar → **completar** o `wa_message_id` com o que o provider devolveu. Provider que não devolve id → a linha fica sem chave e a rede de segurança continua sendo `e_a_nossa_propria_voz` (`webhook.py:1951-1953`) e `_eco_do_dashboard` (`espelho_chat.py:433-459`). 🔴 **Isso é declarado, não escondido** — e o relatório diz a porcentagem de linhas que ficaram com chave.
- ⚠️ `observer_intake.py:711-738` (*"quando a atendente está ligada, o espelho não grava o que entra"*) **não sai**: dedupe e divisão de responsabilidade resolvem coisas diferentes, e o comentário do próprio arquivo carrega a medição de 17/08 que justifica o `return`.

### 9.2 Uma conversa por contraparte

📊 **Duas resoluções de conversa convivem:** o espelho usa `(company_id, user_id, channel='whatsapp', agent_id IS NULL)` (`espelho_chat.py:502-505`); o pipeline usa `get_or_create_conversation(..., session_id, agent_id)` (`webhook.py:936-945`). A normalização de LID **existe e é boa** (`identidade_do_evento.py:100-115`, puro) — o que falta é uma **chave só**.

🔴 **E não existe nada no schema que impeça a próxima.** Constraints reais de `conversations`, lidas do catálogo em 13/09:

```sql
conversations_pkey             PRIMARY KEY (id)
conversations_session_id_key   UNIQUE (session_id)      ← o @lid gera session_id diferente: a fantasma nasce LEGALMENTE
uq_conversations_id_company    UNIQUE (id, company_id)  ← é só o par de FK composta
ck_conversations_resolucao_coerente / ck_conversations_resolucao_motivo
```
📊 `idx_conversations_company_user_channel (company_id, user_id, channel)` **NÃO é UNIQUE**; `user_phone` **não tem índice nem constraint**.

**Contrato:**
1. Coluna `conversations.contraparte` (text), escrita pelos **dois** resolvedores, com o valor de `telefone_do_evento` já normalizado. Expand-first: a coluna nasce, os escritores passam a preenchê-la, o backfill aplica a função ao `user_phone` existente.
2. **Índice único parcial** sobre `(company_id, contraparte)` restrito a conversas de WhatsApp **abertas** e sem agente — é o que impede a fantasma **nº 176** sem tocar no histórico. 📊 Pode ser criado sem `CONCURRENTLY`: a tabela tem **860** linhas (13/09); o BLOCO 0 reconta antes de aplicar.
3. As **175 fantasmas** de hoje são fechadas pelo script que já existe, com a migration M1 destravando o CHECK (§11).

📊 **O tamanho real do problema, medido em 13/09** (era 174 em 09/09 — **nasceu mais uma enquanto esta SPEC era escrita**):

| | |
|---|---|
| fantasmas | **175** · **100% abertas** (`open` 170 · `HUMAN_REQUESTED` 5) |
| AutoFleet · Resulta · AMANDUS | **106** · **69** · 0 |
| **com pausa humana presa** | **10** |
| **com par real inequívoco** | **9** |
| **sem par encontrável** | **166 (94,9%)** |
| mensagens presas do lado fantasma | **1.884**, todas com `wa_message_id` |

⚠️ **Honestidade sobre o alcance:** para **166** delas não há o que mesclar — só fechar com motivo. 🔴 **O produto ganha na 176ª, não nas 166.** O que se recupera de verdade são as **10** com pausa de atendente presa, que hoje ninguém abre. ⚠️ E o script diz **7** com pausa (`migrar_conversas_fantasma_lid.py:24-31`, medição de 09/09) contra **10** hoje: **10 é o número da execução**, e o dry-run do BLOCO 0 reconta.

### 9.3 A ordem do silêncio — e as **duas** coisas que P-PILOTO-15 significa

⚠️ **Divergência registrada.** O plano de execução pede *"ordem `pausar_ia` antes da lista de exceções — P-PILOTO-15"*. 📊 O texto real de P-PILOTO-15 (`PENDENCIAS.md:10538-10539`) é outro: *"`pausar_ia` devolve False quando `resolvido_em` está preenchido e a pausa não limpa o campo; conversa encerrada e reaberta pelo segurado com intervenção humana não fica protegida"*. **As duas entram, e são defeitos diferentes.**

**Defeito 1 — a ordem (medido hoje, não estava em nenhuma pendência).** `a_ia_deve_calar` (`o_fim_do_atendimento.py:1325-1377`) checa, nesta ordem: `company_id` vazio (`:1341`) → **`telefone_e_excecao_da_janela`** (`:1343-1345`) → `pausar_ia` (`:1348`) → janela de N dias. 🔴 A exceção de teste está **antes** do takeover, logo **um telefone na lista neutraliza `claimed_by` e `HUMAN_REQUESTED`** — o robô fala por cima da atendente. O comentário do env admite isso (`:1288-1292`); o **docstring da função descreve dois passos e omite a exceção** (`:1329-1332`).

**Contrato:** ordem nova — `company_id` → **`pausar_ia`** → exceção de teste → janela de N dias. A exceção passa a valer **só para a janela de N dias**, nunca para o takeover. Docstring reescrito com os **três** passos.

**Defeito 2 — P-PILOTO-15 como está escrita.** `pausar_ia` (`:344-395`) devolve `False` quando `resolvido_em` está preenchido (`:390-392`): conversa encerrada e reaberta pelo segurado, com a atendente dentro, **não** fica protegida. **Contrato:** a intervenção humana passa a valer sobre conversa reaberta — a pausa limpa `resolvido_em` (ou a checagem passa a olhar a pausa mesmo com o campo preenchido). O executor escolhe **medindo** qual das duas quebra menos leitor, e registra a escolha com nota (AAA §9).

📊 **E há um buraco de guarda:** `grep -rn "JANELA_SILENCIO_EXCECOES"` no repo inteiro devolve **2 linhas, ambas dentro do próprio motor** (`:1288` comentário, `:1293` a constante). **A lista de exceções não tem nenhum teste.** G12 passa a ser o primeiro.

### 9.4 Todo silêncio no feed, com motivo

📊 `anotar_silencio_no_feed` (`:1411`) começa com `if not foi_a_janela(motivo): return False` (`:1419-1420`). **Não viram linha no feed:** o silêncio por `claimed_by`/`HUMAN_REQUESTED` · por `sem corretora` · pelas duas falhas fail-closed (*"não consegui ler o histórico"*, *"não consegui saber se alguém assumiu"*) · e a **não-calada** por exceção de telefone (`:1344` só faz `logger.info`).

📊 **O tamanho do buraco, medido em 13/09:**

| janela | turnos de cliente | **silêncios no MEIO da conversa** | % |
|---|---|---|---|
| acervo inteiro | 32.935 | **8.574** | **26,0%** |
| desde 01/08/2026 | 6.416 | 1.777 | 27,7% |
| desde 01/09/2026 | 2.127 | **589** | **27,7%** |

*(«no meio» exclui o último turno da conversa, que naturalmente não tem resposta — é o número honesto.)*

🔴 **8.574 silêncios no meio da conversa, e 6 motivos escritos no banco inteiro.** A única coluna de motivo é `conversations.human_handoff_reason`, preenchida em **6 de 860** conversas — e **129 das 131** em `HUMAN_REQUESTED` não dizem por quê. Pior: 📊 `conversation_logs` tem **566 linhas, todas `status='success'`, zero com `error_message`** — **ele só grava o que deu certo. Uma resposta que nunca saiu não deixa linha nenhuma.** `work_events` (45.459 linhas) só tem ciclo de vida de run/step. **Não existe, hoje, onde escrever "o agente não respondeu porque X".**

⚠️ **E um achado de PII que apareceu no caminho:** `conversations.human_handoff_reason` guarda **narrativa livre em texto claro** sobre o sinistro do segurado — detalhe de acidente, terceiros, orientação jurídica. Descoberto ao listar os 6 valores distintos; ⛔ o conteúdo **não** foi reproduzido. É campo sem redação que o produto trata como "motivo". **Vira pendência nomeada** (CLAUDE.md §7: nenhum segredo nem dado pessoal em log, blueprint, artifact ou RAG) — e 🔴 **a frase de motivo que esta SPEC escreve no feed nunca carrega narrativa do segurado**, só a razão do silêncio.

**Contrato:** o filtro sai. Toda decisão de `a_ia_deve_calar` que resulte em silêncio vira **uma linha por conversa, por motivo, por dia** — a memória de processo (`_SILENCIO_JA_ANOTADO`, `:1396`, teto `:1397`) ganha o motivo na chave. E a **não-calada por exceção** também vira linha: 💭 *"número de teste: o agente respondeu mesmo com a conversa pausada"* — porque sem ela a Regina vê o robô falando numa conversa dela e não tem como saber por quê.

💭 As frases continuam sendo **frases**, não códigos — `silenciar_por_palavra_humana` já documenta por quê (`:1197-1200`): *"um código de motivo obrigaria a tela a traduzir, e a tradução é onde o texto envelhece longe do código que o produz"*.

⚠️ **Sem tabela nova** (CLAUDE.md §5): o escritor continua sendo o `log_activity` que já alimenta a página Atividades (`:1434-1438`).

**GATE E.** Mesma entrega duas vezes → **1** linha em `messages` e **1** turno; LID e telefone da mesma contraparte → **1** conversa, e a segunda é recusada pelo índice; as **175** fantasmas fechadas com VERIFY em zero (e as **10** com pausa presa com a pausa copiada **antes** do fechamento); telefone na lista de exceções **não** fura o takeover; cada um dos 5 motivos de silêncio produz linha no feed.
**MUTAÇÃO E.** (a) tirar o `wa_message_id` do insert do pipeline → o guarda de dedupe → **vermelho**; (b) desligar a normalização de LID → duas conversas → **vermelho**; (c) reverter a ordem de `a_ia_deve_calar` → o guarda do takeover → **vermelho**.

---

## 10. BLOCO F — o nome do agente (D-PILOTO-12), inteiro

### 10.1 Primeiro, o campo certo

🔴 **O diagnóstico §7.4 aponta o campo errado — e o campo que ele nomeia nem existe onde ele pensa.**

```sql
select column_name from information_schema.columns
 where table_name='companies' and column_name='agent_name';   -- 📊 13/09: 0 linhas
```

📊 **`companies.agent_name` NÃO EXISTE.** `conversations.agent_name` existe, mas é **rótulo de quem atendeu**, com **três** escritores constantes — `"Espelho"` (`espelho_chat.py:535`), `"Motor de Acionamento"` (`dispatch_mirror.py:147`), `"AutoBrokers"` (`webhook.py:219`) — e default de coluna `'Smith Agent'` (`schema_completo.sql:675`). 📊 O que ele realmente contém hoje:

| valor | conversas | ⚠️ |
|---|---|---|
| **Espelho** | **782** | nome de mecanismo interno no campo que o corretor lê |
| **Smith Agent** | **73** | 🔴 "Smith" é runtime técnico invisível, **nunca marca** (GLOSSARIO) |
| AutoBrokers | **4** | o nome certo, em 4 de 860 |
| Motor de Acionamento | 1 | |

**O nome configurável** vive em `agents.name` + `agents.context_package[TENANT_AGENT_CONFIG_NS].variables.attendant_name`, escrito por `lib/admin/agent-blueprints-canonical.ts:439,460-466`, com o blueprint `even-attendance-v1` usando `display_name = '{{attendant_name}}'` (`:99`) e a variável rotulada *"Nome do atendente"*, máx. 60 (`:116`). Lido em `graph.py:1256-1261` → `prompts.py:350`.

🔴🔴 **E o que está gravado lá contradiz a D-PILOTO-12.** 📊 `agents.name` em 13/09 — 8 agentes, 3 ativos:

| corretora | nome | ativo |
|---|---|---|
| **Resulta** | **AutoBrokers** | ✅ |
| Resulta | **Amanda** | ❌ **desativado** |
| **AutoFleet** | **AutoBrokers** | ✅ |
| AutoFleet | Maria Regina | ❌ |
| AMANDUS | AutoBrokers Sandbox | ✅ |
| AMANDUS · Blueprint Studio | JOANA · AutoBrokers · **Even** | ❌ |

A decisão diz *"'Amanda' na Resulta é escolha da Saionara e **fica**"*. **A linha `Amanda` está desativada; o agente ativo da Resulta se chama `AutoBrokers`.** 🔴 **Isto é caixa do Founder, não decisão do executor** — a SPEC entrega o mecanismo e pergunta qual nome vale. ⚠️ E `Even` continua no banco, desativado: nomenclatura da SPEC-013, **memória superada** (CLAUDE.md §4).

📊 **Contexto que enquadra tudo:** `companies.agent_enabled = false` nas **5** empresas. O agente está desligado agora — o que torna o canário desta SPEC o primeiro exercício real do nome.

**Contrato:** esta SPEC mexe **só** em `agents.name`/`attendant_name`. ⛔ `conversations.agent_name` não muda de significado — mudaria a tela de conversas e o marcador `'espelho'` (`ConversasClient.tsx:39,112,115`). Que o nome dele minta é **pendência de renomeação registrada, não executada aqui** (CLAUDE.md §12.1: *"o nome errado é a causa"* — mas trocá-lo agora custaria a tela inteira).

### 10.2 A apresentação usa o nome escolhido

`prompts.py:352-361` já compõe com `display_name` e o nome da corretora. O que muda é o `SEMPRE` (§8.1) e **o que acontece quando o nome está vazio**: hoje o bloco inteiro some (`:352-354`), e o agente fica sem identidade. **Contrato:** nome vazio → o card mostra o valor efetivo (nunca campo em branco silencioso) e o agente se apresenta 💭 *"Aqui é a assistente virtual da {corretora}"*. ⛔ Nunca "da sua corretora" — a regra já está em `prompts.py:360`.

### 10.3 "Especialista" nomeia a atendente real, nunca o agente

📊 Hoje não existe nenhuma instrução mandando o agente se dizer "especialista"; a palavra só aparece como **subagente** (`prompts.py:35,604,614-626`). Mas o piloto mostrou o agente prometendo "vou passar para a especialista" sem dizer quem.

**Contrato:**

```python
def atendente_de_plantao(company_id: str) -> Optional[str]:
    """O nome da pessoa a quem o agente vai passar o caso. `None` quando não dá para saber."""
```

Regra determinística, **declarada e nesta ordem**: (1) membro ativo de `company_members` com papel `attendant` e plantão marcado, se o plantão existir; (2) **exatamente um** membro ativo com papel `attendant` → é ela; (3) qualquer outro caso → `None`.

🔴 **`None` não vira nome inventado.** Copy 💭: com nome — *"Vou passar seu caso para a {atendente}, da nossa equipe. Ela te responde por aqui."*; sem nome — *"Vou passar seu caso para a nossa equipe. Uma pessoa te responde por aqui."* ⛔ **Nunca o próprio nome do agente.**

⚠️ **Fronteira com a 001.3:** o conceito de **plantão** (quem está de turno, com horário) é do card Equipe e pertence à EXTRA-001.3 (D-PILOTO-09). Esta SPEC entrega o **contrato** e a regra (2)/(3); a 001.3 liga a regra (1). Está em §21 com o gatilho.

### 10.4 Trocar o nome não muda conversa em andamento

A thread guarda `identidade.nome_da_apresentacao` (§8.3). `agent_name` mudou **e** já houve apresentação neste assunto → **nada acontece agora**; no **próximo assunto**, `deve_se_apresentar` devolve `mudou_de_nome` e o agente diz uma vez (copy em §8.1). 🔴 Trocar o nome no meio de um acionamento e o agente virar outra pessoa na mensagem seguinte é pior que manter o nome antigo até o assunto fechar.

### 10.5 O card recusa nome de agente igual a nome de membro da equipe

**Contrato:** a validação roda **no servidor** (a rota que grava `agents.name`/`attendant_name`) e a tela mostra a frase — ⛔ validação só no cliente não é validação. Comparação **normalizada**: sem acento, sem caixa, sem espaço duplo, sobre `company_members` ativos da **mesma** corretora (CLAUDE.md §7). 💭 Frase de recusa: *"Esse nome já é de alguém da sua equipe ({nome}). Escolha outro para a assistente — senão, no grupo e nos dossiês, ninguém vai saber quem falou."*

⚠️ **Legado:** o BLOCO 0 mede se **hoje** existe colisão. Existe → a validação recusa **mudanças novas** e o card mostra um aviso sobre a colisão existente, **sem** bloquear a corretora de salvar outras coisas. ⛔ Quebrar o salvamento de quem já está em produção não é conserto.

### 10.6 Nos dossiês o agente assina 🤖

Nos textos que vão ao grupo de suporte e ao dossiê, **o agente assina `🤖 {agent_name}`** e a atendente aparece **pelo nome, sem emoji**. ⛔ Nunca o contrário. ⚠️ Os **modelos** de dossiê (🆘 PRECISO DE AJUDA, 🚨 NOVO SINISTRO, ✅ ATENDIMENTO CONCLUÍDO, 📊 ATENDIMENTOS REALIZADOS) são da **EXTRA-001.3**; esta SPEC entrega **a assinatura** e o guarda de que ela não se inverte.

**GATE F.** Apresentação usa o `agent_name` da corretora (duas corretoras, dois nomes, no mesmo teste); "especialista" nomeia a atendente ou não nomeia ninguém — **nunca** o agente; trocar o nome no meio → nada muda no assunto atual e **uma** reapresentação no seguinte; o card recusa nome colidente **pelo servidor**; dossiê com 🤖 no agente e nome puro na atendente.
**MUTAÇÃO F.** (a) aceitar nome de agente igual ao de um membro → **vermelho**; (b) `atendente_de_plantao` devolver o nome do agente quando não sabe → **vermelho**; (c) inverter a assinatura do dossiê → **vermelho**.

---

## 11. Migrations — APPLY · VERIFY · ROLLBACK escritos ANTES

> 🔴 **Ler `docs/canon/MIGRATIONS-AUTHORITY.md` inteiro antes de qualquer SQL.** Diretório canônico: `backend/supabase/migrations/`. Nome: `YYYYMMDD_NN_spec_extra001_2_<slug>.sql`. Formato obrigatório: §7 de lá. VERIFY é **SQL executável**, não prosa. ROLLBACK escrito **antes** de aplicar. ⛔ Proibido: `schema_completo.sql`, `upgrade_v6.2.sql`, `storage_buckets.sql`, reaplicar `APLICADA`/`ISOLADA`, aplicar qualquer `NÃO RASTREADA`, DDL fora de migration versionada. Forma a copiar: `20260907_02_spec_extra001_reclamar_so_do_que_pode.sql`. Atualizar `backend/supabase/migrations/MANIFEST.md`.

### M1 — o CHECK aceita `fantasma_lid` (destrava P-PILOTO-13)

- **APPLY:** substituir `ck_conversations_resolucao_motivo` por versão que inclui `'fantasma_lid'`. Expand-first: **sim** (a lista só cresce). Destrutiva: **não**. O valor tem de estar também na lista fechada do produto (`o_fim_do_atendimento.MOTIVOS`) — 🔴 senão `marcar_fim` levanta `ValueError` de chamador errado (`:230-249`) e o conserto fica pela metade.
- **VERIFY:** (V1) `pg_get_constraintdef` do CHECK contém `fantasma_lid`; (V2) `INSERT`/`UPDATE` adversarial com um motivo **fora** da lista → **recusado**; (V3) `UPDATE` com `fantasma_lid` numa conversa de canário → aceito, e revertido por id + `company_id`.
- **ROLLBACK:** recriar o CHECK sem o valor. ⚠️ **Só é seguro se nenhuma linha já usar `fantasma_lid`** — o ROLLBACK confere isso primeiro e, havendo linhas, **não** reverte: registra. (Reverter apagaria a razão pela qual 174 conversas foram fechadas.)
- **Depois:** rodar `migrar_conversas_fantasma_lid.py --vivo`, com o dry-run colado antes e o VERIFY do próprio script depois (ele já imprime o esperado, `:276-281`).

### M2 — `conversations.contraparte` e a trava da fantasma nº 176

- **APPLY:** (a) `ALTER TABLE ... ADD COLUMN IF NOT EXISTS contraparte text`; (b) backfill aplicando a normalização às linhas existentes; (c) **índice único parcial** sobre `(company_id, contraparte)` restrito a `channel='whatsapp' AND agent_id IS NULL AND status <> 'closed'`, com `IF NOT EXISTS`. Expand-first: **sim** (nada some; os escritores passam a preencher antes de o índice existir). Destrutiva: **não**.
- 🔴 **Ordem obrigatória:** escritores preenchendo → backfill → **contar duplicatas** → resolver as duplicatas → **só então** criar o índice. Criar o índice com duplicata viva falha a migration inteira. O BLOCO 0 conta antes.
- 📊 Sem `CONCURRENTLY` porque a tabela é pequena (**774** linhas em 09/09; o BLOCO 0 reconta — passou de ~50 mil, usar `CONCURRENTLY` fora de transação).
- **VERIFY:** (V1) a coluna existe e o índice existe, com a cláusula `WHERE` do contrato; (V2) `SELECT company_id, contraparte, count(*) … HAVING count(*) > 1` sobre conversas abertas → **0 linhas**; (V3) `INSERT` adversarial de uma segunda conversa aberta para a mesma contraparte → **recusado pelo banco**; (V4) uma conversa de **outra** corretora com a **mesma** contraparte → **aceita** (o isolamento não virou bloqueio).
- **ROLLBACK:** `DROP INDEX IF EXISTS`; a coluna **fica** (expand-first: coluna órfã não quebra leitor).

### O que NÃO é migration

⛔ **Não criar** o índice único do espelho: ele existe (`20260806_02_espelho_sem_duplicata.sql:41-43`). ⛔ **Não criar** tabela de ficha, de identidade ou de silêncio: `conversations.ficha_atendimento` e `log_activity` já são os escritores.

---

## 12. Guardas e mutações — exatamente **12** novos (D-PILOTO-14)

> 🔴 Todos sobre o **MOTOR** e o **ACERVO** (CLAUDE.md §9.3–9.5). ⛔ Proibido teste que reimplementa a regra. Cada guarda vem com a mutação que o deixa **vermelho** — e um guarda que não consegue ficar vermelho é carimbo, não guarda.

| # | o guarda afirma | como (motor + acervo) | MUTAÇÃO que o deixa vermelho |
|---|---|---|---|
| **G1** | a trava serializa a **mesma** conversa e **não** serializa conversas diferentes | `processar_buffers_prontos` real (carregado por AST, como `test_midia_e_concorrencia_do_webhook.py:61-89` já faz) com Redis dublê; **linha de controle:** o `teste_o_buffer_processa_em_paralelo` existente continua verde | (a) `abrir_turno` sempre devolve token → dois turnos; (b) chave sem o telefone → o paralelismo morre |
| **G2** | a janela adaptativa coalesce as **20 rajadas** do corpus em 1 turno cada | `janela_de_espera(tracos_da_mensagem(...))` sobre o corpus de §13 | `janela_de_espera` fixa em 8 s → N rajadas fragmentam |
| **G3** | mídia entra no buffer nos **três** pontos; legenda e arquivo no mesmo turno | conta os `"type": "media"` de `webhook.py` (tem de ser 0 desvios) + rajada com foto pelo motor | religar o desvio de `webhook.py:2226` |
| **G4** | mensagem que chega durante a janela entra **na mesma** resposta e nunca se perde | `mesclar_o_que_chegou` real, com Redis dublê | devolver `[]` → a mensagem some |
| **G5** | quem perdeu a posse do turno **não envia** | `ainda_sou_o_dono` no caminho real de envio | sempre `True` → duas respostas |
| **G6** | todo `required_slots` de todo corredor está em `ROTULOS` **e** é gravado na ficha | `slots_do_atendimento()` × `corridor_playbooks` reais | 🔴 **vermelho HOJE** (`agua_escorrendo`) = gate zero. Mutação: devolver a tupla velha de 15 |
| **G7** | slot já confirmado **não** é perguntado de novo | replay estrutural do encanador 10/09 pelo motor (`bloco_para_o_prompt` + `slots_reperguntados`) | esvaziar `ficha["confirmados"]` |
| **G8** | 0 cumprimentos fora da abertura; e a resposta respeita a classe de tamanho | `deve_se_apresentar` + `classe_do_tamanho` reais sobre o replay 10/09 | devolver `SEMPRE se apresente` ao bloco estático |
| **G9** | a mesma entrega duas vezes → **1** linha e **1** turno; **e o mesmo `wa_message_id` nunca aparece sob dois `company_id`** | payload real reenviado pela rota real + a consulta de §3.6 do RP sobre o acervo | tirar o `wa_message_id` do insert do pipeline. 🔴 A segunda asserção é **vermelha HOJE** (104 de 134): ela fica verde pelo veredito do BLOCO 0 item 0, não por edição do teste |
| **G10** | LID e telefone da mesma contraparte → **1** conversa; a segunda é recusada pelo banco | `telefone_do_evento` real + VERIFY V3 da M2 | desligar a normalização de `@lid` |
| **G11** | silêncio: exceção **não** fura o takeover, e **todo** motivo vira linha no feed | `a_ia_deve_calar` + `anotar_silencio_no_feed` reais, os 5 motivos | reverter a ordem das checagens |
| **G12** | o nome: apresentação usa o `agent_name`; "especialista" nunca é o agente; o **servidor** recusa nome colidente | duas corretoras com nomes diferentes + a rota real de gravação | aceitar nome de agente igual ao de um membro |

**Regras da bateria (AAA §10):** mutação roda em **worktree próprio** ou com lock exclusivo, restaura por **cópia** (nunca `git checkout`), e o orquestrador **não** roda a suíte inteira enquanto um juiz muta. A suíte inteira roda no gate de cada bloco e no fim — 2 a 4 vezes na SPEC, **nunca a cada commit**; o relatório traz a contagem.

**Guardas frágeis a promover (não contam no teto, porque substituem afirmação por chamada):** `test_higiene_de_plataforma.py:71-105` e `test_o_flow_token_atravessa.py:61` afirmam **strings** do fonte do buffer; `test_o_atendimento_tem_memoria.py:204` protege a ficha afirmando que o `import` está escrito em `graph.py`. 🔴 São exatamente o defeito do CLAUDE.md §9.4. G6 e G7 os substituem onde tocam esta SPEC; o resto vira pendência nomeada.

---

## 13. O corpus das 20 rajadas — estrutura, nunca texto

📊 Hoje `backend/tests/corpus/` tem **só** `retornos_de_cobranca.json` (frases 100% sintéticas, declaradas no próprio `_doc`) e `telas_reais/` (17 `.jsonl` de **URA**, não de atendimento). **Não existe corpus de conversa de atendimento.** Este é artefato novo, e a forma a copiar é `tests/corpus/telas_reais/INDICE.md` (índice + **CONTROLE de máscara** + linhas recusadas).

**Como ele resolve a tensão entre "medir no acervo" e "não carregar texto".** A janela precisa de conteúdo para classificar; o corpus não pode ter conteúdo. A saída é separar a função que **lê texto** da que **decide**:

```
tracos_da_mensagem(texto) ──► Tracos  ──► janela_de_espera(Tracos) ──► segundos
      ↑ roda no acervo, por script                ↑ roda no CI, sobre o corpus
      ↑ imprime só CONTAGENS                      ↑ o corpus guarda só os Tracos
```

**O arquivo** — `backend/tests/corpus/rajadas_reais.jsonl`, uma rajada por linha:

```json
{"id":"r01","company":"A","itens":[
   {"tipo":"text","n_chars":42,"pont_final":false,"conectivo":true,"dado_curto":false,"intervalo_ms":0},
   {"tipo":"text","n_chars":11,"pont_final":false,"conectivo":false,"dado_curto":true,"intervalo_ms":2400},
   {"tipo":"image","n_chars":0,"pont_final":false,"conectivo":false,"dado_curto":false,"intervalo_ms":9100}],
 "turnos_hoje":2,"turnos_esperados":1}
```

⛔ **Nenhum campo de texto. Nenhum telefone. Nenhuma data absoluta.** `company` é `"A"`/`"B"`, não o UUID.

**O gerador** — `backend/scripts/gerar_corpus_de_rajadas.py`, read-only, que (a) acha rajadas de ≥ 2 mensagens de entrada em ≤ 30 s 🔴 **lendo `attendance_transcripts.wa_timestamp`, nunca `messages.created_at`** (§0.3: o segundo é o relógio do espelho e infla as rajadas em **+39,2%**), com o filtro `insurer_key is null` conferido contra o motor `canais_observados.natureza_da_contraparte` (📊 divergência de 0,006%), (b) aplica **`tracos_da_mensagem` do motor** a cada texto, (c) grava só os traços, (d) imprime as contagens 📊 do relatório, (e) traz **duas linhas de CONTROLE** (CLAUDE.md §9.2): se `n_chars` somado for 0 em tudo, a extração não rodou; **e a mesma consulta pelos dois relógios tem de devolver números diferentes** — iguais significa que o `wa_timestamp` não foi usado.

📊 **A matéria-prima existe de sobra:** 20.727 rajadas, 5.608 com mídia, nas três corretoras (Resulta 14.509 · AutoFleet 6.202 · AMANDUS 16). O RESEARCH-PACK §3.4 já traz **28 candidatas estratificadas** por tamanho × ritmo × corretora, com UUID, para o executor não recomeçar a busca.

**Critérios de aceite do corpus:** 20 rajadas · tamanhos 2, 3, 4 e 5+ representados · intervalos nas faixas 0–3, 3–8, 8–18, 18–25 e **> 25 s** · **≥ 3 com mídia** · **as duas corretoras** · e **pelo menos as 4 rajadas que fragmentaram no piloto** (elas são a régua: `turnos_hoje` = 2, `turnos_esperados` = 1).

⚠️ **Se o acervo não tiver 20 rajadas que satisfaçam os critérios**, o corpus tem o que houver, o número real vai no relatório, e ⛔ **não se completa com rajada inventada** — inventar removeria justamente o que faz o guarda valer.

---

## 14. Multi-tenant — como o `company_id` chega, e como o isolamento se prova

**CLAUDE.md §7:** RLS + filtro obrigatório no código + constraints + **teste automático de isolamento com dois tenants reais**. O backend usa service role: RLS sem policy não protege contra erro de filtro.

| contrato novo | como o tenant chega | como se prova |
|---|---|---|
| trava de turno | pela chave, que herda o `escopo` = id da integração (§5.3) | duas corretoras, mesma contraparte → **duas** travas independentes; e o BLOCO 0 prova por `SELECT` que nenhuma integração serve duas corretoras |
| buffer com itens | mesma chave de hoje | o isolamento já existe e tem docstring (`message_buffer_service.py:36-55`) |
| ficha e slots | `conversations.ficha_atendimento`, sempre lida por `company_id` + `session_id` (`attendance_ficha.py:310-315`) | leitura cruzada entre corretoras → vazia |
| `conversations.contraparte` + índice | `company_id` é a **primeira** coluna do índice | VERIFY V4 da M2: mesma contraparte em outra corretora → **aceita** |
| silêncio no feed | `log_activity(company_id, …)` | linha da corretora A não aparece no feed de B |
| nome do agente / atendente | `company_members` filtrado por `company_id` | nome de membro da corretora B **não** bloqueia nome de agente da A |
| corpus e script de medição | `company` vira `"A"`/`"B"` | ⛔ nenhum UUID de corretora no arquivo versionado |

🔴 **O teste de isolamento é com dois tenants reais, no filtro do código, não na RLS** (AAA §7.1).

---

## 15. Matriz de aceite — gates e contraexemplos

| Gate | precisa comprovar | contraexemplo / mutação que **tem** de reprovar |
|---|---|---|
| **G0** | gate zero **vermelho** antes de implementar | G6 e G7 verdes hoje = prova que a régua não mede |
| **B0** | base, schema, escritores e desvios remedidos | proposta tratada como produção comprovada |
| **A1** | 20 rajadas → 1 turno cada | duas gerações para a mesma rajada |
| **A2** | conversas diferentes continuam paralelas | trava global por corretora |
| **A3** | perder a trava não custa o buffer | buffer limpo e turno não iniciado |
| **A4** | quem perdeu a posse não envia | resposta velha enviada "por via das dúvidas" |
| **B1** | janela por conteúdo; teto 25 s; piso de 8 s morto | `grep "max(settings.BUFFER"` ainda encontra |
| **B2** | mídia no buffer nos **3** pontos | foto gerando turno paralelo |
| **B3** | re-leitura mescla e nada se perde | mensagem do meio vira segunda resposta |
| **B4** | presença só quando vai falar | "digitando…" seguido de silêncio |
| **C1** | todo slot de corredor está no vocabulário e na ficha | slot coletado que não volta no turno seguinte |
| **C2** | slot confirmado não é reperguntado | o "água escorrendo?" pela terceira vez |
| **D1** | 0 cumprimentos fora da abertura | saudação na 30ª mensagem |
| **D2** | tamanho dentro da classe, com as exceções declaradas | 760 caracteres de conversa comum |
| **D3** | identidade reescrita a cada assunto | nome de 22 dias atrás |
| **E1** | 1 entrega = 1 linha = 1 turno | a mesma pergunta relida como nova |
| **E2** | 1 conversa por contraparte; a 175ª fantasma não nasce | LID e telefone com duas linhas |
| **E3** | exceção de teste não fura takeover | robô falando por cima da atendente |
| **E4** | todo silêncio tem motivo no feed | conversa calada sem explicação |
| **F1** | o nome escolhido aparece e não confunde | "Amanda, a assistente" × "Amanda, a atendente" |
| **F2** | "especialista" = a atendente, ou ninguém | o agente prometendo passar para si mesmo |
| **M1/M2** | VERIFY executável, verde, e ROLLBACK escrito antes | migration aplicada com VERIFY em prosa |
| **T1** | dois tenants isolados no dado e no efeito | trava, índice ou feed cruzando corretora |
| **R1** | os guardas existentes continuam verdes | paralelismo do buffer quebrado pela trava |
| **P1** | push com saída colada e head remoto conferido | commit local tratado como entrega |

---

## 16. Canário controlado em produção

### Antes

Identificar TESTE-A/TESTE-B na configuração privada e conferir a **identidade real** da conexão hoje. Fixar tenant, conversa, run e orçamento. **Provar os bloqueios com saídas simuladas antes de liberar qualquer envio vivo** — inclusive o bloqueio da **presença**. Se o produto não permitir habilitar só o canário, **implementar essa limitação antes**. ⛔ Nunca ligar tenant operacional inteiro.

### Os casos mínimos

1. 🔴 **O caso-título:** TESTE-A manda **5 mensagens + 1 foto em 12 s**. Esperado: **1 turno**, 1 resposta (até 4 balões pela humanização, que é outra coisa), com a foto reconhecida, sem pergunta repetida e sem cumprimento no meio. **Evidência:** contagem de turnos, não de balões.
2. **Dado curto:** TESTE-A manda um CPF de teste sozinho → resposta em ~3 s, não em 8.
3. **Frase inacabada:** TESTE-A manda *"o carro parou na"* e completa 15 s depois → **um** turno.
4. **Durante o turno:** TESTE-A manda mais uma mensagem enquanto o agente responde → ela entra na mesma resposta ou na seguinte, **nunca se perde e nunca vira resposta duplicada**.
5. **Presença:** o "digitando…" aparece enquanto o agente pensa e **some** ao responder. Conversa que o agente vai calar → **nenhum** "digitando…".
6. **Reencontro:** encerrar o assunto, TESTE-A volta dentro da janela → **sem** reapresentação. Assunto novo → **uma** apresentação, com o nome da corretora.
7. **Nome:** trocar o `agent_name` no card no meio da conversa → nada muda naquele assunto; no seguinte, uma linha dizendo que mudou. Tentar salvar nome igual ao de um membro → **recusa com a frase**.
8. **Espelho:** TESTE-B (representando a atendente) responde pelo celular → a pausa vale, o silêncio aparece **no feed com motivo**, e a mensagem dela não é gravada em dobro.

### Depois

Desligar **só** a habilitação temporária do canário. Cancelar intenções pendentes do canário. Restaurar configurações de teste alteradas. Conferir que não ficou agente amplamente habilitado nem trava órfã no Redis. Preservar auditoria **sem PII**. Entregar evidências **com aliases**.

---

## 17. Validação com Saionara e Regina

O executor **prepara** roteiro e telas; **o Founder conduz**, pelos números de teste. ⛔ O executor não as contata e não usa os números operacionais delas.

O que se valida com elas: a resposta chega **inteira** quando o segurado escreve em pedaços? O agente repete pergunta? Ele cumprimenta na hora certa? O "digitando…" ajuda ou incomoda? O nome escolhido está certo, e a frase de "vou passar para a especialista" nomeia a pessoa certa? O feed explica os silêncios?

O roteiro distingue três estados, e o relatório também: **não testado** · **aprovado no canário técnico** · **validado pela atendente**. ⛔ Não bloquear trabalho técnico esperando a agenda delas; ⛔ não declarar o aceite delas antecipadamente.

---

## 18. Entrega, implantação e rollback

### 18.1 Ordem de integração (serial, porque os hubs são compartilhados)

```
BLOCO 0 (mede)
→ E-migrations M1+M2 e a normalização  (a trava de A depende de E para a chave ser 1:1)
→ A trava + B janela/mídia/re-leitura   (mesmos dois arquivos: uma unidade de escrita)
→ B4 presença                            (só se o BLOCO 0 confirmar a rota)
→ C ficha                                (nodes.py + attendance_ficha.py — disjunto dos acima)
→ D apresentação/tamanho/identidade      (hub: prompts.py + o_fim_do_atendimento.py + graph.py)
→ F nome                                 (mesmo hub de D + frontend) — serial depois de D
→ suíte inteira → painel de 3 lentes → conserto → juiz fresco
```

### 18.2 Entrega

Preflight e regressão pela autoridade vigente. ⛔ Nunca `git add -A`, force push, exclusão de trabalho ou alteração de guarda para obter verde. Commit **arquivo por arquivo**, cada conserto salvo completo antes do seguinte.

🔴 **Entregar não é commitar. É empurrar** (CLAUDE.md §2):

```bash
git rev-list --count origin/main..HEAD    # 0 = o trabalho está no ar
git merge-base --is-ancestor origin/main HEAD && git push origin HEAD:main
```

**A saída real do push, colada no relatório, com o SHA remoto conferido.**

### 18.3 Implantação

Serviços a implantar no EasyPanel: o **backend** (é onde vivem webhook, buffer, scheduler, prompts e providers) e, se o card Agente/Equipe mudar, o **web**. 🔴 A ordem sai do contrato medido desta SPEC, ⛔ não se copia de SPEC anterior. Se a autoridade exigir o clique do Founder, entregar tudo pronto e **o passo exato** — ⛔ não contornar por API.

⚠️ **CLAUDE.md §9.1 se aplica:** mexeu em `app/`, `middleware.ts`, `next.config.js` ou variável de ambiente → `npm run test:rotas-montam` + `next start` + **uma requisição real a `/api/…`**. Build verde não prova que a aplicação sobe.

**Variáveis de ambiente novas — nome, sem valor:**

| variável | o que faz | ausente → |
|---|---|---|
| `TURNO_TTL_SEGUNDOS` | vida da trava de turno | usa o padrão medido no BLOCO 0 |
| `TURNO_RENOVACOES_MAX` | teto de renovações (E01) | 3 |
| `JANELA_DADO_CURTO_SEGUNDOS` · `JANELA_FRASE_COMPLETA_SEGUNDOS` · `JANELA_FRASE_INACABADA_SEGUNDOS` | a janela adaptativa | os valores calibrados no BLOCO 0 |
| `PRESENCA_DIGITANDO_LIGADA` | liga/desliga o "digitando…" | **desligada** (falha para o lado de não prometer) |
| `REPLANEJAMENTOS_MAX` | teto da re-leitura | 2 |

⚠️ E corrigir `backend/.env.example:40-42`, que ainda ensina `BUFFER_DEBOUNCE_SECONDS=3` / `MAX_WAIT=30` / `TTL=300`.

### 18.4 Rollback

Reverter código e flags de forma compatível (`PRESENCA_DIGITANDO_LIGADA=false` desliga a presença sem deploy). `DROP INDEX` da M2 (a coluna fica — expand-first). 🔴 **A M1 só é revertida se nenhuma linha usar `fantasma_lid`** — havendo linhas, não se reverte: registra-se. ⛔ Nunca apagar linha de `messages`, de conversa ou de feed para "limpar". ⛔ Reverter código não desfaz mensagem enviada: o rollback **impede repetição**, não desfaz efeito.

**O relatório separa os marcos, e nenhum deles substitui o outro:** implementado e gateado · na main (SHA remoto + saída do push) · implantado (imagem/SHA + health + uma rota que executa código) · validado no canário (casos, aliases, resultados) · validado pelas pilotos · ativado em linha operacional (**fora** da autorização atual).

---

## 19. Documentação e acompanhamento obrigatórios

Durante a execução, **um escritor por arquivo**:

1. SPEC definitiva em `docs/canon/specs/` e relatório pelo `SPEC-EXECUTION-REPORT-TEMPLATE.md`, **abrindo com o EXECUTION CARD** e com a telemetria de cinco linhas (AAA §11).
2. `docs/canon/ESTADO-DAS-SPECS.md` — a família EXTRA já tem seção própria; acrescentar a 001.2 com estado, **sem renumerar nada** (D-PILOTO-08).
3. `docs/canon/PENDENCIAS.md` — P-PILOTO-13 e 15 com veredito (`FECHADA` com a prova · `CONTINUA` com o que destrava · `MORREU`); e o que esta SPEC deixar de fora entra como pendência nova, com **o que destrava**, **de quem é** (🧑/🤖) e **o que custa esquecer** (CLAUDE.md §11.1).
4. `docs/canon/FOUNDER-DECISIONS.md` — só se surgir decisão nova. D-PILOTO-12 já está registrada; ⛔ não reabrir.
5. `docs/canon/CHANGE-ADDENDA.md` — toda mudança além do texto desta SPEC, classificada **BLOCKER · ESSENCIAL · VALIOSA · FUTURA**, com problema, evidência, consequência e autorização. ⛔ Escopo não se reduz sem decisão do Founder (D5).
6. `backend/supabase/migrations/MANIFEST.md` — as duas migrations.
7. **Dossiê:** `docs/canon/reports/dossies/dossies-autobrokers.html`, com página/aba da EXTRA-001.2, progresso por bloco, gates, provas, falhas materiais e caixa do Founder. 🔴 **Ler o HTML publicado inteiro antes de republicar com `url`**, preservar o que existe, e conferir no link. Sem ferramenta/acesso → atualizar a fonte e dizer **"publicação do dossiê pendente"** com o passo exato. ⛔ Nunca alegar que atualizou. ⛔ Nunca publicar número de teste ou dado de cliente.
8. **GLOSSARIO** — ⚠️ ele **não** define "buffer", "rajada", "turno", "janela de silêncio", "reencontro", "ficha" nem "slot". Se algum desses virar termo canônico, a emenda passa pela regra do bootstrap: **nada entra sem que outro saia ou encolha** (AAA §1).

---

## 20. O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS

> AAA §7.3: 3 a 7 referências, cada uma com **URL · o que faz · o que MODELAMOS · o que REJEITAMOS**, mais **como o juiz inspeciona**. 🔴 SPEC ≥ 088 sem 3 URLs **não fecha**. Todas reabertas em **13/09/2026**; o pesquisador do executor **reabre de novo** e escreve a data nova.

| # | referência | o que faz | o que MODELAMOS | o que REJEITAMOS | como o juiz inspeciona |
|---|---|---|---|---|---|
| **E01** | **Redis — `SET` e Distributed Locks**<br>https://redis.io/docs/latest/commands/set/<br>https://redis.io/docs/latest/develop/clients/patterns/distributed-locks/ | documenta `SET key value NX PX`, o **token aleatório**, a liberação por **script que compara o valor**, a renovação com teto, e avisa que *"don't assume that a lock is retained as long as the process that had acquired it is alive"* | `abrir/renovar/fechar_turno` com token `uuid4`, release pelo **script Lua literal da doc**, renovação com `TURNO_RENOVACOES_MAX`, e a reconferência de posse antes de enviar (§5.5) | **Redlock multi-instância** (temos um Redis; complexidade sem o problema) e **`DEL` cego**, que apagaria a trava de outro turno | abre a página do `SET`, compara o script de liberação com o do código, e roda a mutação "liberar com `DEL`" exigindo vermelho |
| **E02** | **Meta — WhatsApp Cloud API · typing indicators**<br>https://developers.facebook.com/docs/whatsapp/cloud-api/typing-indicators/ | *"The typing indicator will be dismissed once you respond, or **after 25 seconds**, whichever comes first."* · *"only display a typing indicator if you are going to respond."* | 🔴 o **teto da rajada e a vida do indicador viram a mesma constante, 25 s** — que já é o `BUFFER_MAX_WAIT_SECONDS`; e a regra de produto "presença só depois do portão de silêncio" | **a chamada da Meta**: nosso canal é Evolution (D-E001-02). Modela-se o **limite e a regra**, não o endpoint | abre a página, confere o 25 no texto, e confere no código que teto e renovação saem da **mesma** constante |
| **E03** | **Evolution API — `sendPresence` (código-fonte)**<br>`src/api/routes/chat.router.ts` · `src/validate/chat.schema.ts` · `src/api/integrations/channel/whatsapp/whatsapp.baileys.service.ts` em https://github.com/EvolutionAPI/evolution-api | `POST /chat/sendPresence/{instance}` com `{number, presence, delay}` **os três obrigatórios**; enum `unavailable/available/composing/recording/paused`; e `delay` no `sendText` **já é** `composing` por N ms, refeito a cada 20 000 ms | presença pelo `EvolutionProvider._post` que já existe, `composing` renovado a cada ≤ 20 s, `paused` ao fim; e `delay` no `sendText` quando a resposta já está pronta | um cliente HTTP novo; e tratar 20 s como número **nosso** — é constante **deles**. ⚠️ `doc.evolution-api.com/.../send-presence` devolveu **404**; a autoridade é o repositório | abre os dois arquivos, confere enum e obrigatoriedade, e confere que o `delay` sai em **milissegundos** |
| **E04** | **Meta — webhooks**<br>https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/overview<br>https://developers.facebook.com/docs/graph-api/webhooks/getting-started/ | *"These retries can result in duplicate webhook notifications."* · *"Your server should handle deduplication in these cases."* | a dedupe durável é **nossa**, por `wa_message_id`, no índice único **que já existe** | herdar garantia de unicidade de quem não a escreve — ⚠️ **a Meta não documenta unicidade do `wamid` em texto**, só nos exemplos. E TTL de Redis não é histórico | reenvia o mesmo payload duas vezes pela rota real e conta **1** linha e **1** resposta |
| **E05** | **Evolution API — retry do webhook (código-fonte)**<br>`src/api/integrations/event/webhook/webhook.controller.ts` · `prisma/postgresql-schema.prisma` | **até 10 tentativas** com backoff exponencial + jitter (inicial 5 s, teto 300 s); não retenta 400/401/403/404/422. E `model Message { key Json }` **sem `@unique`** — reentrega grava linha nova lá dentro | responder **200 rápido** e deixar o trabalho no buffer/turno; a trava como segunda rede contra a reentrega que chega durante a geração | supor `key.id` estável por contrato (não há fonte); e devolver erro em caminho lento, que é o gatilho das 10 retentativas | injeta a mesma entrega duas vezes com 5 s de intervalo e conta **turnos** |
| **E06** | **Stripe — webhooks**<br>https://docs.stripe.com/webhooks | *"registre os IDs de evento que você processou e não processe eventos já registrados"* · *"A Stripe não garante a entrega dos eventos na ordem em que foram gerados"* | id processado não se reprocessa; e **ordem de chegada não é ordem de acontecimento** — a rajada se ordena pelo relógio da mensagem, não pela entrega | copiar headers, assinatura ou formato da Stripe. O provedor é outro | reordena duas entregas da mesma rajada e confere a ordem do texto combinado |
| **E07** | 🔴 **A janela adaptativa não tem fonte primária — e isso é a referência**<br>https://github.com/devmoreir4/whatsapp-ai-chatbot (verificado arquivo a arquivo) | procurado em `rasa.com/docs`, `botpress.com/docs`, `twilio.com/docs`, `learn.microsoft.com` e `developers.facebook.com`: **nenhum** documenta agregação de mensagens do usuário com segundos recomendados. O único projeto verificado usa **janela fixa**: *"Debounce window: 10 seconds"*, `DEBOUNCE_SECONDS = 10` | a **forma** (buffer em Redis + janela + varredor) — que já é a nossa | 🔴 **copiar o número.** Os 10 s dele não são referência. Todo segundo desta SPEC sai do acervo ou é 💭 calibrado no BLOCO 0 | procura no diff qualquer constante de janela **sem 📊 ao lado**. Uma constante sem medição é achado |

⚠️ **Pistas não verificadas, registradas como pistas:** `openclaw/openclaw` (`debounceMs`), `NousResearch/hermes-agent` (`_text_batch_delay_seconds`), `Anmoldureha/whatsapp-bot` (5 s). ⛔ **Não citar como fonte** — os arquivos não foram abertos.

---

## 21. O QUE SAIU, E QUANDO VOLTA

| frente | por que não entra aqui | gatilho de retorno |
|---|---|---|
| Isolamento por corretora (fila/worker por tenant, backpressure) | é motor de infraestrutura; esta SPEC só garante que a trava é **por conversa** | **EXTRA-001.8** (P-PILOTO-01, D-PILOTO-07) |
| Lista de números da casa · o que o grupo recebe · resumo das 19h | é o card Equipe e os quatro modelos de dossiê | **EXTRA-001.3** (D-PILOTO-09, 13). 🔴 Esta SPEC **entrega** a ela "uma conversa por contraparte" |
| **Plantão** (quem está de turno, com horário) | o campo e a tela são do card Equipe | **EXTRA-001.3**. Esta SPEC entrega o contrato `atendente_de_plantao` e as regras (2)/(3); a 001.3 liga a (1) |
| Teto no bloco de RAG e o "ainda não recebi uma pergunta sua" | é a montagem do prompt de apólice | **EXTRA-001.1**. ⚠️ Esta SPEC **mede** o efeito do re-planejamento sobre o tamanho do prompt e para de acrescentar se piorar (§2) |
| Corredor que não trava · humano na URA (60 s) | é o motor de acionamento | **EXTRA-001.4** (D-PILOTO-10) |
| Renomear `conversations.agent_name` (o rótulo que mente) | trocar hoje quebra a tela de conversas e o marcador `'espelho'` | pendência nomeada; volta com a SPEC de painel ou com a 001.9 |
| Corpus de conversa de atendimento **com texto** mascarado | esta SPEC não precisa de texto versionado; traços bastam (§13) | quando um guarda precisar do texto, com a forma de `telas_reais/INDICE.md` (índice + CONTROLE de máscara) |
| Trocar provedor de WhatsApp · Meta Cloud API · multicanal | D-E001-02 e a fila de canais | **099**, depois dos pilotos |

⛔ Nenhum item obrigatório da §2 sai em silêncio. Conflito material na conversão → **proposta registrada em `CHANGE-ADDENDA.md`**, nunca recorte unilateral chamado de "otimização AAA".

---

## 22. A fila depois desta entrega — contexto, não autorização

Ordem canônica do diagnóstico §12.1: **001.0** retroativa · **001.6-P0** · **001.1** apólice certa + `PolicyDataProvider` · **001.2 (esta)** · **001.3** grupo só o que importa *(depende desta)* · **001.4** corredor + humano na URA · **001.6** cobrança completa · **001.7** piloto medido · **001.10** portal de vidros · **001.5** base de produtos · **001.8** isolamento · **001.9** rotas do painel.

⛔ Esta sessão não cria nem executa as próximas. O handoff de encerramento diz qual é a próxima e **não a começa**.

---

## 23. Definição final de conclusão — lista fechada e verificável

Esta SPEC está concluída quando **todas** as linhas abaixo tiverem evidência escrita no relatório:

1. **G0 vermelho registrado** antes do código (G6 e G7 falhando hoje), e **verde depois** — pelo comportamento, não pela edição do teste.
2. **G1–G12 verdes**, cada um com a **saída real** colada, e **cada mutação demonstrada vermelha** por falha nomeada em subprocesso, restaurada por cópia.
3. Os guardas existentes **continuam verdes**, com destaque para `tests/test_midia_e_concorrencia_do_webhook.py` (a linha de controle da trava) e `tests/test_a_ultima_palavra_humana_manda.py`.
4. **Corpus de 20 rajadas** versionado, sem uma linha de texto, com a linha de CONTROLE, e o script gerador no repositório.
5. **M1 e M2** aplicadas, com **VERIFY executável verde colado** e ROLLBACK escrito **antes**; `MANIFEST.md` atualizado; `--vivo` das fantasmas rodado com o VERIFY em **zero**.
6. **Canário vivo:** o caso-título (5 mensagens + 1 foto em 12 s → **1 turno**) executado com TESTE-A/TESTE-B, com contagem de **turnos** e nenhum efeito fora da allowlist. Presença conferida — **ou declarada desligada** por ausência da rota no fork implantado.
7. **Suíte inteira verde**, com a contagem de rodadas no relatório (2 a 4, nunca a cada commit).
8. **Painel de 3 lentes + red team** rodado sobre o diff, o teste rodando e o banco; achados fundidos com o **teste do produto** aplicado a cada um; conserto conjunto; **juiz fresco** confirmando o conserto **e** auditando o dado sobre o acervo real.
9. **Push na main** com a saída colada e o head remoto conferido; implantação executada ou entregue como **um único clique** com os passos exatos.
10. **Relatório** com card, telemetria de 5 linhas, FATO/INFERÊNCIA/RECOMENDAÇÃO separados, todo número com 📊 ou 💭, o que ficou fora e por quê, canário Amandus → Resulta → AutoFleet, riscos remanescentes, **e a declaração explícita de que nenhum motor paralelo foi criado** (CLAUDE.md §5).
11. **P-PILOTO-13 e 15** com veredito e prova; pendências novas registradas com destrava, dono e custo de esquecer.
12. **Dossiê atualizado e publicado** — ou "publicação pendente" dita com todas as letras, com o arquivo e o passo exato.

### O resumo ao Founder, em linguagem simples, responde a sete perguntas

o que mudou para o segurado · o que mudou para a Regina e a Saionara · o que foi **realmente** testado (e com quem) · o que ficou desligado por autorização ou por falta de rota · que falhas ainda impedem uso · onde acompanhar · **qual é a única próxima ação necessária**.

⛔ **"100% testado em produção" não se atribui a uma suíte nem a uma leitura de código.**

---

### 📋 Caixa do Founder — o que só ele faz (nada disto bloqueia o resto)

| item | o que é | o que custa esquecer | bloqueia? |
|---|---|---|---|
| 🔴 **Qual é o nome do agente da Resulta** | 📊 a D-PILOTO-12 diz *"Amanda fica"*, mas em 13/09 a linha `Amanda` está **desativada** e o agente **ativo** se chama **`AutoBrokers`** (o mesmo da AutoFleet). Uma frase sua resolve: `Amanda` volta, ou `AutoBrokers` fica | o agente se apresenta com um nome que a Saionara não reconhece — e a decisão registrada e o banco continuam discordando | não — a SPEC usa o que estiver ativo e **escreve qual foi** |
| **Colisão de nome agente × equipe** | 📊 hoje são **zero** (9 nomes de agente × 10 membros, nem nome completo nem primeiro nome) | nenhum custo hoje; a trava existe para o dia em que alguém digitar o nome da atendente no card Agente | não |
| **Presença "digitando…"** | decidir se fica **ligada** nos pilotos | 💭 pode parecer artificial para alguns segurados; começar desligada é o padrão seguro | não — `PRESENCA_DIGITANDO_LIGADA` nasce desligada |
| **Janela de 18 s para frase inacabada** | confirmar que esperar até 18 s por uma frase incompleta é aceitável | segurado ansioso pode achar lento; o teto de 25 s limita o pior caso | não — os números saem medidos e são configuráveis |
| **Implantar** | o clique no EasyPanel, se a autoridade assim exigir | o trabalho fica na main e **não** no ar (CLAUDE.md §2) | 🔴 sim, para o canário |
| **Fechar as 175 fantasmas** | 📊 **166 das 175 não têm par real** e serão **fechadas**, não mescladas; as **10** com pausa de atendente presa têm a pausa copiada antes | as conversas somem do "aberto" (o histórico **fica**); e a **176ª** nasce amanhã se a trava não entrar | não — mas é decisão de dado, e vai escrita |
| 🔴 **`wa_message_id` repetido entre corretoras** | 📊 **104 de 134** ids repetidos aparecem sob **dois `company_id`**, com texto idêntico, sem observador compartilhado. **INFERÊNCIA**, não fato | se for cross-tenant de verdade, é P0 e **para a SPEC** (CLAUDE.md §10 item 4) | 🔴 **pode** — o BLOCO 0 investiga **antes** de qualquer migration e registra o veredito |
