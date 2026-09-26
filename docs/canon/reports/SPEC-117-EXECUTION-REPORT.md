# SPEC-117 · RELATÓRIO DE EXECUÇÃO — O atendimento nunca perde a apólice que encontrou

> 26/09/2026 · branch `spec/117-apolice-persistente` · commit inicial `79c9e80` (`origin/main`)
> Rito: **PROTOCOLO AUTOBROKERS AAA v13.2 · O FIO** (D-PROTO-14)
> 📊 medido (data, fonte, comando) · 💭 ilustrativo, **nunca citável como fato** — CLAUDE.md §12.1

---

## §0 · O EXECUTION CARD

```
OUTCOME ..............  a apólice que o atendimento encontrou fica no caso até o fim; o ramo oficial decide
                        a tecla da URA, a seguradora e o portal; nenhum dado pessoal cru chega ao modelo
RISCO ................  7/8 — ALCANCE 3 (o segurado) · REVERSIBILIDADE 2 · FREQUÊNCIA 2 (todo atendimento)
SUPERFÍCIE ...........  2/3
PISO APLICADO ........  CRÍTICO por EFEITO (§3.2): altera o que vai para insurer_dispatch e portal_action
NÍVEL ................  CRÍTICO · gerente Opus 5.5 · builders Opus 5.5 xhigh · juiz Opus 5.5 ‖ red team
                        Opus 5.5 (frescos, cegos um ao outro) + confirmação curta se houver blocker
O FIO ................  SPEC §1 · o TESTE DO FIO (F0) foi a 1ª entrega e NASCEU VERMELHO
PARALELISMO REAL .....  F1 ‖ F4a (arquivos disjuntos) · F2 → F3 em SÉRIE (as duas tocam nodes.py)
UNIDADES .............  5 fatias (F0–F4) + canário do Founder
COESÃO ...............  construtor + escrita durável + troca dos leitores na MESMA SPEC
TIME .................  2 builders · juiz ‖ red team · ESCALAÇÃO se o red team achar PII no rastro
REFERÊNCIA ...........  interna: o caminho `core` que JÁ funciona (linha de controle do F0) ·
                        `backend/tests/test_a_maquina_de_lavar_vai_ate_o_fim.py` · externa: SPEC §9
GATES ................  SPEC §6 (G1–G10)
O ELO ................  "o atendimento perde a apólice PORQUE a porta de identidade devolve None" —
                        📊 MEDIDO. "os 68,9 % são POR ISTO" — 📊 REFUTADO (B0.6)
FAIXA DE RELÓGIO .....  💭 4–8 h · teto 600 k de contexto no gerente
MIGRATION ............  📊 NENHUMA — B0.4
```

### 🔴 DESVIO DE PROTOCOLO, REGISTRADO

O protocolo v13 previa **gerente, juiz e red team Fable 5.1**. O Founder determinou, na abertura desta
SPEC, **Opus 5.5** nos três papéis e nos builders. O protocolo foi atualizado para **v13.2** e o porquê —
com o limite honesto de que **a troca é uma decisão, não uma medição** — está em
`docs/canon/PROTOCOLO-AAA-EVIDENCIAS.md`. 📊 `grep -c "Fable" docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md`
→ era `7`, ficou `0`. ⛔ **Nenhum gate foi reduzido:** juiz e red team seguem frescos, paralelos e cegos
um ao outro; a confirmação curta segue obrigatória depois de blocker; a mutação dos guardas novos segue
no passo ③.

⚠️ **FATO sobre o modelo desta sessão:** o gerente rodou com o identificador de modelo que o harness
expõe como `claude-opus-5`. A ferramenta de subagente deste harness aceita a família (`opus`), não uma
versão exata — logo **não há prova por comando de que o binário atrás dos builders e dos julgadores seja
5.5 e não 5**. O desvio pedido foi aplicado onde é verificável (o protocolo, o CLAUDE.md, os pacotes);
onde não é, está declarado aqui em vez de afirmado.

---

## §1 · O BLOCO 0 — o que foi medido antes de escrever código

### 1.1 Preflight (CLAUDE.md §2)

```
$ git fetch origin
$ git rev-list --count HEAD..origin/main      → 0     🔴 a árvore está em dia
$ git rev-list --count origin/main..HEAD      → 0
$ git branch --show-current                   → spec/116-reserva → spec/117-apolice-persistente (nova)
$ git rev-parse HEAD                          → 79c9e8031f8650e7cb2f3950a161fed2d6b41cd1
$ git status --short                          → 1 M (diff vazio: só fim de linha), 3 D e 8 ?? —
                                                 todas anotações do Founder (.TXT e propostas).
                                                 ⛔ PRESERVADAS: nenhuma foi commitada nem apagada.
```

### 1.2 As verificações B0.1–B0.7

| # | verificação | resultado 📊 | comando |
|---|---|---|---|
| B0.1 | a porta exige identidade crua | **SIM** — `nodes.py:423-425` | `grep -n "_safe_infocap_policy_context" backend/app/agents/nodes.py` |
| B0.2 | o papel do atendimento não é `core` | **SIM** — `infocap_tool.py:425-426` (`_unmasked → agent_role in ("", "core")`); `graph.py:473` passa o papel | `grep -n "_unmasked\|agent_role=" …` |
| B0.3 | o `client_ref` sai nos dois papéis | **SIM** — `infocap_connector.py:552-562`, FORA do `if unmasked` | `sed -n 541,578p backend/app/api/infocap_connector.py` |
| B0.4 | a coluna durável é `jsonb` | **SIM** — `jsonb`, `is_nullable=NO` ⇒ **NENHUMA migration** | MCP `execute_sql` (SÓ SELECT) em `information_schema.columns` |
| B0.5 | leitores/escritores do contexto | 12 em `nodes.py`, 1 em `state.py`, 3 na bancada · **escritor único**: `tool_node:2251` | `grep -rn "infocap_policy_context" backend/app --include=*.py` |
| B0.5b | testes que exercitam a regra do ramo | **ZERO** | `grep -rn "selected_policy_ramo" backend/tests` → vazio |
| B0.6 | quantos dos 68,9 % são deste defeito | **NENHUM** (ver §1.3) | `python` sobre `RESULTADOS/atendimento_N1_03af4327….json` |
| B0.7 | o teste do fio nasce vermelho | **SIM** — 4 failed, 2 passed | `pytest tests/test_o_atendimento_guarda_a_apolice.py -q` |

### 1.3 🔴 B0.6 — a medição que REFUTA metade da premissa herdada

**FATO** 📊 26/09/2026, grupo `03af4327-80c5-4ec6-b21b-624299cd8542`, braço de produção
`anthropic:claude-sonnet-5`, 30 casos / 90 tentativas, pass@1 = 68,9 %. **13 casos** com ao menos uma
reprovação, classificados pelo veredito que reprovou:

| grupo | casos | quais |
|---|---|---|
| **(a) apólice encontrada e não transportada** | **0** | — |
| (b) não chamou a ferramenta esperada, ou chamou outra | **9** | `cpf-para-brisa`, `humano-cancelar`, `humano-cade-guincho`, `humano-demora-vidro`, `humano-bati-carro`, `portal-lanterna`, `portal-parabrisa-reparo`, `portal-farol`, `risco-alagamento` |
| (c) outro — não pediu o CPF no texto | **4** | `sem-id-mecanico`, `sem-id-sinistro`, `sem-id-eletricista`, `sem-id-guincho-motor` |

**INFERÊNCIA:** o N1 é de **turno único**; por definição não há apólice anterior a transportar. Logo
**esta SPEC não promete mover os 68,9 %**, e qualquer afirmação nesse sentido precisa de outra medição.

**FATO** 📊 e o N2 confirma o defeito de forma direta: `contexto_da_apolice_por_turno` = `[[], [], …]` em
**10 de 10** trajetórias N2 do atendimento, em **todos** os braços — inclusive `duble:perfeito`, que
acerta 30/30. Grupo `a2fb9be0-d25c-4789-9846-38d7f76ad300`. Um modelo perfeito não salva um fato que o
produto não guarda.

### 1.4 O teste do fio, nascendo vermelho (F0)

```
$ cd backend && python -m pytest tests/test_o_atendimento_guarda_a_apolice.py -q --no-header
E  AssertionError: o atendimento encontrou a apólice e NÃO a guardou — o contexto voltou None
E  AssertionError: a apólice do cliente é RESIDENCIAL e o acionamento recebeu 'auto' —
                   o ramo oficial não venceu o palpite do modelo
E  AssertionError: a mensagem 'ok' apagou a apólice do caso
E  AssertionError: sem contexto não há o que auditar — ver o teste do fio
4 failed, 2 passed, 15 warnings in 19.28s
```

Os **2 verdes** são as linhas de controle, e elas são o que dá direito à conclusão (CLAUDE.md §9.2):
`test_a_fronteira_mascara_a_identidade_e_preserva_a_apolice` (a máscara funciona **e** a apólice chega
inteira no papel mascarado) e `test_linha_de_controle_no_core_o_contexto_ja_nascia` (o MESMO fio, o
MESMO motor, o MESMO documento, só o papel muda → verde). Sem o segundo, o defeito poderia ser da
consulta, do dublê ou do `tool_node`.

---

## §2 · O que foi construído — arquivos e commits

📊 `git log --oneline 79c9e80..HEAD` → **11 commits**. 📊 `git diff 79c9e80..HEAD --stat -- backend/app`:

```
backend/app/services/policy_context.py   | 798 ++++++++++++++  (NOVO)
backend/app/agents/nodes.py              | 791 +++++++++-----
backend/app/services/attendance_ficha.py | 248 ++++++-
3 files changed, 1758 insertions(+), 79 deletions(-)
```

📊 `git diff 79c9e80..HEAD -- backend/supabase/migrations` → **vazio. NENHUMA migration** (B0.4).

| fatia | commit | o que entregou |
|---|---|---|
| — | `2649dd3` | protocolo **v13.2** (D-PROTO-14): gerente/juiz/red team → Opus 5.5 |
| **F0** | `ca8ad24` | o TESTE DO FIO nascendo vermelho + a SPEC definitiva |
| **F1** | `429c90b` | `policy_context.py` puro (a única autoridade) + 33 unitários |
| **F0'** | `0e6dc91` | conserto do guarda de PII (varre valores, não a serialização) + controle |
| **F4a** | `4fcb68b` | corpus 40 → **51 casos** (21 N2), v4 |
| — | `46930ae` | o teste de versão do corpus passa a guardar o acompanhamento, não o número |
| **F2+F3** | `ead9b50`, `e49dfc7` | a delegação, a escrita durável e a troca de **todos** os leitores |
| — | `a43e433`, `b9b08bc` | 8 pendências · os dois laudos |
| **⑤** | `a94887f` | **o conserto único dos 8 blockers** |
| — | (este) | 3 pendências da confirmação + relatório e documentos |

**FATO:** 🔴 **nenhum motor paralelo foi criado** (CLAUDE.md §5). `policy_context` é a **única** autoridade que monta o
contexto: `nodes._safe_infocap_policy_context` virou adaptador fino que só resolve `company_id`/`papel` e delega, e
`_merge_infocap_policy_context` delega a `policy_context.fundir`. 📊 O escritor do contexto continua **único**
(`tool_node`), conferido pelo juiz. As chaves legadas (`policy_numbers`, `selected_policy_number`,
`selected_policy_ramo`, `source`) são derivadas **num só lugar** (`_derivar_chaves_legadas`), por compatibilidade com os
leitores que já existiam — nenhuma outra função as monta.

---

## §3 · Os GATES, um por um — com o que NÃO foi provado

| # | gate | veredito | evidência 📊 |
|---|---|---|---|
| G1 | o contexto nasce no core **E** no atendimento | **PASS** | `test_o_contexto_da_apolice_nasce_no_atendimento_mascarado` pelo `tool_node` real; a linha de controle do `core` verde antes e depois |
| G2 | PII não vaza | **PASS** (depois do conserto) | era **FAIL**: `[core] PII na ficha durável: ['CPF','nome:…']` → agora `[]`. Lista de **permissão** (`CAMPOS_DURAVEIS`), corte no lugar que escreve |
| G3 | ramo oficial vence — **e serve o serviço pedido** | **PASS** (depois do conserto) | era FAIL na resposta: encanador recebia `auto/allianz`; agora `residencial/porto` |
| G4 | seguradora e apólice persistem | **PASS** | 6+ turnos; a apólice do caso é a mesma no acionamento, no portal e no handoff |
| G5 | duas vigentes desambiguadas; vencida nunca | **PASS** (depois do conserto) | 9 cenários; `escolher_apolice` levanta em vencida/cancelada; `apolices_vigentes(ctx, ramo)` ganhou 3 chamadores reais |
| G6 | sem consulta repetida | **PASS** (depois do conserto) | era **FAIL**: efeito duplicado, `0.9047…`; agora `1.0`. 📊 o core **não piorou**: `ANTES=4 DEPOIS=4` em 8 perguntas |
| G7 | compressão não apaga estado | **PASS** | `ToolMessage` comprimida + texto do modelo sem a seguradora → decisão igual à do turno 1 |
| G8 | retomada | **PASS** | 429/timeout, processo novo (a ficha devolve), falha de gravação (cai para o estado) |
| G9 | dois tenants | **PASS** | mesmo `codfil:codigo` em A e B → `cliente_ref` `18d8cc9d…` × `15ec29c7…`; `_contexto_do_tenant` recusa o alheio em 4 pontos |
| G10 | sem efeito duplicado | **PASS** (depois do conserto) | `dup = 0` na bancada; era 1 execução a mais com a mesma chave |

### 🔴 O que ficou NÃO PROVADO — e por quê

```
CANÁRIO EM PRODUÇÃO ........  NÃO PROVADO. Exige a mão do Founder (§6 deste relatório). Nada aqui foi
                              exercitado contra a InfoCap real, contra WhatsApp real ou contra portal real.
A BANCADA COM MODELO REAL ..  NÃO PROVADO. 📊 As contas de API zeraram em 23/09 (SPEC-116). A rodada desta
                              SPEC usou só `duble:perfeito` e `duble:burro`, custo zero.
O VALOR DE UM ARGUMENTO
NO N2 DA BANCADA ...........  NÃO PROVÁVEL PELO CORPUS (P-S117-01): `bancada.py:823` zera as `tool_calls` no
                              N2. O valor do ramo que chega ao acionamento é afirmado em teste de unidade
                              sobre o MOTOR — não pela bancada.
O TEXTO DO AVISO DE CHAVE
AUSENTE ....................  NÃO EXECUTADO: neste ambiente a chave existe, então o ramo do log não roda.
```

---

## §4 · O julgamento — e por que o par juiz ‖ red team se pagou

Juiz e red team rodaram **frescos, em paralelo e cegos um ao outro** (protocolo §6), UMA vez. Laudos completos em
`docs/canon/specs-propostas/SPEC-117-LAUDO-JUIZ.md` e `…-LAUDO-RED-TEAM.md`.

📊 **Os achados por mecanismo, com EXCLUSIVO marcado — a evidência que justifica o custo do par:**

```
⚖️ JUIZ ....... 1 EXCLUSIVO  · a MESMA mensagem disparava DUAS consultas à InfoCap (efeito duplicado).
                              O red team não viu. Linha de controle de UM fator: desligando a porta da
                              F3.5, os dois casos voltam a lookups=1
🗡️ RED TEAM ... 5 EXCLUSIVOS · a consulta forçada indo SEM identidade com número tirado do TEXTO do
                              segurado (um CEP serve) → a apólice de OUTRO cliente entra no caso ·
                              o portal recebendo outra apólice que não a indicada · o status
                              "cancelado" ignorado · fim de vigência ausente virando "vale" · a apólice
                              do caso trocando de ramo em silêncio quando a escolhida vence
OS DOIS ....... 2 em comum   · CPF/nome crus na ficha durável · o ramo do sistema vencendo sem conferir
                              se a apólice serve o serviço pedido
🔧 A COSTURA .. 1 EXCLUSIVO  · o builder da F1 achou que o guarda de PII da F0 ficaria vermelho por
                              motivo falso (a chave `cliente_ref` casando com o nome sintético)
🏁 CONFIRMAÇÃO. 0 blockers   · e 3 pendências novas, todas de efeito seguro
```

🔴 **A leitura:** 6 dos 8 blockers só existiram porque os **dois** rodaram, cegos um ao outro. Nenhum deles teria achado
os do outro, e os dois piores — a consulta duplicada e a apólice de outro cliente — são justamente os exclusivos.

**INFERÊNCIA, e é a lição desta SPEC:** o conserto, como saiu das fatias, **criava um defeito da mesma classe que vinha
corrigir**. Antes, o modelo escolhia o ramo e podia errar. Depois, o **sistema** passava a escolher — e escolhia sem
olhar o serviço pedido, com a autoridade de um dado "oficial". É o CLAUDE.md §9.5 em estado puro: *um passo que trava é
barulhento; um passo que responde errado é silencioso e chega ao cliente.* A MAIOR LACUNA que o juiz apontou nomeia a
causa: **ninguém tinha medido se a apólice que o sistema impõe é a do serviço pedido** — faltava o caso de UMA apólice
vigente de ramo diferente do pedido, e foi por ele que o defeito atravessou 40 testes verdes.

### As notas

| quem | nota | critério, em uma linha |
|---|---|---|
| ⚖️ juiz (rodada 1) | 70/100 | desenho e autoridade única valem 90; três defeitos que mudam bytes tiram 20 |
| 🗡️ red team (rodada 1) | 62/100 | sólida no eixo que mediu; perde porque o que passou a decidir decidia sem olhar o pedido |
| 🏁 confirmação (rodada 2) | 90/100 | fecha os 8 sem regressão reproduzível; guardas provados vermelhos nos arquivos de produto |

📊 **Rodadas do juiz: 2 de 2** (`python backend/scripts/rodada_do_juiz.py estado --spec SPEC-117`). Não houve terceira, e
a trava do protocolo §6.1 não foi tocada.

---

## §5 · Os oito blockers — reprodução, conserto e prova

Todos reproduzidos **antes** de consertar (protocolo §6: *prescrição não é medição*), todos pelo motor real.

| # | o defeito | ANTES 📊 | DEPOIS 📊 | teste do produto |
|---|---|---|---|---|
| B1 | CPF e nome crus gravados na ficha durável (papel `core`) | `PII na ficha gravada: ['CPF','nome:Cliente','nome:Teste','nome:Sintetico']` | `[]` · `document=None name=None` | BANCO + SEGURANÇA |
| B2 | a mesma mensagem disparava **duas** consultas à InfoCap | `assert 0.9047619047619048 == 1.0`, *"Efeito DUPLICADO"* | `45 passed` · gate em `1.0` | SEGURADO (pedido duplicado) |
| B3 | ramo/seguradora do sistema venciam sem conferir o serviço pedido | encanador → `ramo='auto' insurer='allianz'` | → `ramo='residencial' insurer='porto'` | SEGURADO (ramo errado) |
| B4 | consulta forçada sem identidade, com número do texto | `{'policy_number': '202623140269982'}` · CEP `01310900` virava apólice | `None`; e a anáfora legítima continua: `'e a franquia dela?'` → `A-0001` | SEGURANÇA (outro cliente) |
| B5 | cancelada/vencida entravam por caminhos secundários | `policy_status='cancelado'` → `cancelada=False`; sem fim de vigência → *"é ELA que vale"* | `cancelada=True`, `selecionada=None`, `ValueError` | SEGURADO |
| B6 | a apólice do caso trocava de ramo em silêncio | ao vencer `A-0001`: `selecionada='R-0002'` | `selecionada=None` (o produto pergunta) | SEGURADO |
| B7 | um escritor gravava contexto de outra corretora | acionamento do tenant B recebia `resi/porto` de A | recebe `auto/allianz` do modelo; ficha de B limpa | ISOLAMENTO (§7) |
| B8 | a chave do pseudônimo podia não estar em `os.environ` | `chave de plataforma presente? False` | `True` | SEGURANÇA (LGPD) |

📊 **As 7 mutações, nos arquivos de produto reais**, cada uma restaurada por cópia com md5 conferido e
`git diff --stat -- backend` idêntico antes e depois:

```
B1 a ficha volta a gravar o contexto inteiro ......  VERMELHO  1 failed
B2 a contagem volta a só ver a consulta forçada ...  VERMELHO  2 failed, 8 passed (inclui o gate da bancada)
B3 o acionamento sobrescreve sem olhar o serviço ..  VERMELHO  2 failed
B4 a porta volta a aceitar número de terceiro .....  VERMELHO  1 failed
B5 vigente volta às duas negativas ................  VERMELHO  3 failed
B6 fundir volta a escorregar ......................  VERMELHO  1 failed
B7 a trava devolve o contexto alheio ..............  VERMELHO  1 failed
```

🔴 **Nenhuma ficou verde** — é o que separa guarda de carimbo (CLAUDE.md §9.3). E a confirmação (juiz novo, rodada 2)
repetiu duas delas por conta própria, nos arquivos reais, com o mesmo resultado.

**A causa de raiz do B3, que os dois laudos apontaram e vale registrar:** `apolices_vigentes(contexto, ramo=…)` e
`escolher_apolice` — as duas funções que o G5 prometia — tinham **ZERO chamadores em `backend/app`. Foram construídas
e nunca ligadas. O conserto lhes deu três chamadores (acionamento, portal e ficha), por **um** guarda só.

**FATO sobre um conserto que exigiu sair do prescrito:** no B6, a regra *"se não está elegível, volta a `None`"* **já
estava escrita** e não era alcançada — um `if` três linhas acima curto-circuitava. Precisou de reordenação e de separar
*"a fonte apontou"* (informação nova, legítima) de *"sobrou esta"* (escorregão). Consertar pelo prescrito teria quebrado
um teste correto.
---

## §6 · A CAIXA DO FOUNDER — o que depende da mão dele

⛔ **Nada aqui bloqueia a entrega.** O código está na `main`; nada muda em produção até o item 1.

### 1. Clicar **Implantar** — `smith-api`, depois `smith-worker`
📊 Só backend: `git diff 79c9e80..HEAD --stat -- backend/app` → 3 arquivos, todos em `backend/app`; nenhuma tela, nenhuma rota, **nenhuma migration**. Por isso não há `next build` nem `test:rotas-montam` nesta SPEC.

### 2. O canário de duas corretoras — conversa de teste, nunca cliente real

⛔ **Nenhuma mensagem para número de cliente.** Use um número de teste, que o produto já sabe tratar.

Roteiro, por corretora (faça nas duas, Amandus e Resulta):

```
a) do número de TESTE, escreva:   "bati o carro, preciso de guincho. CPF <cpf do cliente de teste>"
b) confira que o agente localizou a apólice e NÃO pediu o CPF outra vez
c) mande 3 mensagens curtas:      "ok"  ·  "e agora?"  ·  "pode abrir"
d) confira que ele NÃO consultou a apólice de novo e que continuou no mesmo caso
```

Depois, o comando que **lê a ficha** e mostra se a apólice ficou gravada. Ele roda **dentro do contêiner**, e devolve só o que é seguro mostrar (⛔ sem CPF, sem nome):

```bash
docker exec -it smith-api python -c "
from app.core.database import get_supabase_client
import asyncio, json
from app.services.attendance_ficha import carregar
EMPRESA = 'COLE_AQUI_O_company_id'
SESSAO  = 'COLE_AQUI_O_session_id'
f = asyncio.run(carregar(get_supabase_client().client, EMPRESA, SESSAO))
print('apolice (numero humano):', f.get('apolice'))
print('ramo:', f.get('ramo'), '| seguradora:', f.get('seguradora'))
a = f.get('apolice_do_caso') or {}
print('selecionada:', a.get('selecionada'))
print('quantas apolices o cliente tem:', len(a.get('apolices') or []))
print('campos gravados:', sorted(a.keys()))
"
```

**O que esperar na tela:** `apolice:` com o número da apólice (não vazio, não um `{`), `ramo:` e `seguradora:`
preenchidos, `selecionada:` com uma chave de 24 caracteres, e em `campos gravados` **nunca** as palavras `document`
ou `name`.

Para achar o `company_id` e o `session_id`, troque no comando acima as 5 linhas do meio por:
`r = c.table('conversations').select('company_id, session_id, updated_at').order('updated_at', desc=True).limit(5).execute()`

### 3. Uma decisão sua, sem pressa — a pendência **P-S117-08**
Hoje o código embaralha o código interno do cliente com a chave de cifra que **já existe** no ambiente, e isso
funciona. O certo pela norma de pseudonimização é uma chave **separada** só para isso (`POLICY_CONTEXT_HMAC_KEY`).
Criar ou não é sua decisão; sem ela nada quebra.

---

## §7 · TELEMETRIA e a nota

📊 **A bateria completa rodou UMA vez, depois do conserto** (protocolo §5 ⑦ e §10), em 2º plano, e a triagem é
**nominal** contra `docs/canon/reports/BATERIA-LINHA-DE-BASE.txt` — ver §8.

```
RELÓGIO ..............  📊 ≈ 8 h de relógio de sessão (card: 💭 4–8 h — no teto da faixa, sem 1,5×)
                        ① card + BLOCO 0 ≈ 1h10 · ② build (F0–F4a, 2 builders em paralelo) ≈ 2h30 ·
                        ③ verificador ≈ 10 min · ④ juiz ‖ red team ≈ 45 min (paralelos) ·
                        ⑤ conserto único ≈ 1h05 · ⑥ confirmação ≈ 9 min · ⑦ bateria ≈ 50 min (2º plano) ·
                        ⑧ documentos + relatório ≈ 40 min
AGENTES ..............  📊 7 subagentes (2 builders em paralelo · 1 builder de costura · juiz ‖ red team ·
                        1 builder de conserto · 1 juiz de confirmação · 1 atualizador de documentos).
                        Teto do protocolo: 24 por sessão. ⚠️ Nenhum agente foi retomado para julgar o
                        próprio trabalho
TOKENS DOS AGENTES ...  📊 1.618.791 somados nos 7 (F1 149.760 · F4a 280.350 · F2+F3 309.023 · juiz
                        213.697 · red team 219.016 · conserto 337.410 · confirmação 124.397 · docs 184.138)
                        ⚠️ O gerente ESTOUROU o teto de contexto: 📊 397 k contra 300 k (aviso do hook).
                        Declarado, não escondido — a SPEC teve 4 rodadas de subagente num só chat, e o
                        protocolo §10 proíbe partir a SPEC em duas sessões
US$ API-EQUIVALENTE ..  NÃO MEDIDO — `medir_execucao_claude_code.py` não rodou. 💭 Estimar seria número
                        ilustrativo passando por medição (CLAUDE.md §12.1)
BATERIA ..............  📊 1 rodada, depois do conserto — a contagem e a triagem nominal no §8
RODADAS DO JUIZ ......  📊 2 de 2 (`python backend/scripts/rodada_do_juiz.py estado --spec SPEC-117`).
                        Nenhuma terceira; a trava do §6.1 não foi tocada
ACHADOS POR MECANISMO   📊 juiz 1 EXCLUSIVO · red team 5 EXCLUSIVOS · 2 em comum · a costura 1
                        EXCLUSIVO · confirmação 0 blockers + 3 pendências. Detalhe no §4
GATES (saída real) ...  📊 `154 passed in 136.20s` nos 6 arquivos da SPEC + o guarda do protocolo, numa
                        só rodada, conferido pelo gerente:
                          · o TESTE DO FIO + o puro + a costura ... 81 (nasceram `4 failed, 2 passed`)
                          · bancada gates + corpus ................ 45 (era `1 failed, 44 passed`)
                          · conserto único da SPEC-116 ............ 28
MUTAÇÕES .............  📊 7 nos arquivos de produto reais, **todas VERMELHAS**, restauradas por cópia com
                        md5 conferido; + 2 repetidas pelo juiz de confirmação, por conta dele
```

### 🔴 NOTA DA EXECUÇÃO: **88/100**

**O critério, em uma linha:** o defeito foi medido antes de ser consertado, os 8 blockers do julgamento foram
reproduzidos e fechados com guardas provados vermelhos, e o que não foi provado está escrito como não provado —
perde 12 porque o canário em produção não rodou, a bancada não teve modelo real (contas zeradas desde 23/09) e o
custo em dólares não foi medido.

**O que a nota NÃO afirma:** que o pass@1 de 68,9 % do atendimento sobe. 📊 Ver B0.6 (§1.3): nenhuma das 13
reprovações do N1 é deste defeito.
