# SPEC-088 · A CENTRAL DE AGENTES PARA DE MENTIR DE VERDE

> **O que ela entrega:** a Central deixa de responder *"o laço rodou?"* e passa a
> responder *"o trabalho aconteceu?"* — agrupada por propósito, com uma cor por
> agente que **consegue ficar amarela e vermelha**, e com "desligado de propósito"
> e "quebrado em silêncio" em cores **diferentes**.
>
> **v1** · 02/09/2026 · commit base `862dd1c` · repo `AutoBrokers-FIX`
> Proposta de origem: `specs-propostas/4 - SPEC-088-central-de-agentes-organizacao-operacional.md`

---

## 🔴 A razão desta SPEC existir — e ela não é a da proposta

O Founder escreveu uma linha, em `RASCUNHO-SPECS-FUTURAS.md:195`:

> *"**A CENTRAL DE AGENTES EM GRUPOS.** 'Está muito confuso para mim.' Agrupar
> por propósito, cada grupo com sua página, fluxo e explicação."*

A proposta respondeu com **3.718 linhas** de organização operacional: grupos,
papéis, contratos de delegação, admission gate, especialistas, juízes e execução
governada. 📊 **Zero marcas 📊/💭 em todas elas** (`CLAUDE.md` §12.1).

⚠️ **A queixa é de NAVEGAÇÃO. A proposta responde com ONTOLOGIA.** E enquanto
media-se a navegação, apareceu um defeito maior, que ninguém tinha visto — e que
é a razão real desta SPEC existir.

---

## 1. 📊 O QUE A MEDIÇÃO DE HOJE ACHOU

### 1.1 · 🔴 A Central dá VERDE quando o laço roda, não quando o trabalho acontece

📊 **Medido em 02/09/2026, produção `dcajcvlzcjbmyapmklil`, duas consultas:**

```sql
-- o laço do Garimpo, nos últimos 3 dias
SELECT workflow_key, status, count(*), max(created_at)
  FROM work_runs WHERE created_at > now() - interval '3 days'
   AND workflow_key = 'intelligence.garimpo' GROUP BY 1,2;
-- → intelligence.garimpo | completed | 9 | 2026-09-02 00:00:12

-- o que o Garimpo produziu
SELECT count(*), max(created_at) FROM broker_insights;
-- → 270 | 2026-08-26 00:05:34
```

> 🔴 **9 execuções `completed` em 3 dias. Zero linhas produzidas em 7 dias.**

**E o que o card mostra nesse tempo — 📊 lido nos dois arquivos, não suposto:**

```
backend/app/tasks/buffer_processor.py:148   scheduler: seconds=3600 → PULSA DE HORA EM HORA
                                            ⚠️ o comentário ao lado diz "1x/dia":
                                               é a MINERAÇÃO que é diária, travada
                                               por marcador no Redis. O pulso, não.
app/admin/central-agentes/page.tsx health()  < 900s 🟢 SAUDÁVEL · < 7200s 🟡 ATENÇÃO
```

> 🔴 **Com pulso de hora em hora: 🟢 SAUDÁVEL nos primeiros 15 minutos de CADA
> HORA, 🟡 ATENÇÃO nos outros 45. E nenhuma das duas cores tem relação com o fato
> de ele não produzir uma linha há 7 dias.**
>
> ⚠️ **O verde é falso porque não produziu. O amarelo é falso porque nada está
> errado com o laço.** As duas cores estão erradas, por motivos opostos — e é isso
> que um instrumento que mede o gesto errado faz.

🔴 **A frase que resume o defeito inteiro:** o `beat()` mede o **tique do
agendador**, e o card é lido como se medisse **o trabalho**.

### 1.2 · As quatro causas, cada uma com arquivo e linha

| # | onde | o que faz | por que é grave |
|---|---|---|---|
| **D1** | `backend/app/services/broker_insights.py:307-311` `if cutover_ligado(): return 0` — **antes** do `finally:` da `:337` | 🔴 o `beat("garimpo")` da `:343` é **inalcançável em produção** | 📊 `INTELLIGENCE_CUTOVER` tem padrão `"1"` (`legacy_adapter.py:36`) e 📊 `grep beat( services/intelligence/` → **zero**. O motor canônico não pulsa nada |
| **D1-b** | o mesmo `finally:` da `:337`, quando o cutover está DESLIGADO | o pulso sai com `mined = 0` no caminho de exceção | 🔴 quebrou → pulsou. ⚠️ **É o defeito do rollback, não o de hoje** — e os dois têm de cair juntos |
| **D2** | `backend/app/services/conversation_auditor.py:181` `await beat("alfaiate")` | o **Auditor** dá o pulso do **Alfaiate**, sem contagem | o card de um agente fica verde pelo trabalho de outro |
| **D3** | `backend/app/services/atlas/attendance_capture.py:378` `await _beat(0)  # pulso sem acao: mostra o agente vivo na Central` | pulso com zero ações, **de propósito** | está escrito no código que o verde é decorativo |
| **D4** | `backend/app/core/heartbeat.py:18` `_TTL = 7 * 86400` + `app/admin/central-agentes/page.tsx` `health()` | morto há **2h** → `PARADO` 🔴 · morto há **8 dias** → a chave expira, `last_run: null` → `AGUARDANDO` ⚪ | 🔴 **o estado MELHORA conforme a morte envelhece.** É a SPEC-089 outra vez: a régua sobe quando deixa de medir |

### 1.3 · 📊 E a prova de que isso já custou — está escrita no repositório

`SPEC-090`, pendência **P-090-02**:

> *"`knowledge_cards` parado desde 16/08 (10 dias). 18.715 linhas e nenhuma nova.
> **Ninguém percebeu.**"*

📊 Reconferido hoje, 02/09: `max(created_at)` de `knowledge_cards` = **16/08/2026
16:46**. São **17 dias**.

> 🔴 **A Central existe exatamente para alguém perceber. Ela não percebeu, e o
> instrumento continuou verde.** Isso não é cosmético: é um instrumento que mente.

### 1.4 · 📊 O silêncio de 7 dias, tabela por tabela

**Consulta:** `SELECT count(*), max(created_at) FROM <tabela>;` · 02/09/2026

```
🟢 VIVO HOJE          work_runs ............. 3.463 · 02/09 18:04
                      work_events .......... 35.293 · 02/09 18:04

🔴 MUDO HÁ 7 DIAS     attendance_transcripts  156.913 · 26/08 16:40
                      conversations ............. 677 · 26/08 16:27
                      observed_events ......... 28.220 · 26/08 13:52
                      observed_sessions .......... 580 · 26/08 13:52
                      ura_maps ................... 324 · 26/08 14:07
                      route_drift ................. 17 · 26/08 14:07
                      broker_insights ............ 270 · 26/08 00:05
                      conversation_scorecards .... 686 · 26/08 00:19

🔴 MUDO HÁ 17 DIAS    knowledge_cards ......... 18.715 · 16/08 16:46
🔴 MUDO HÁ 14 DIAS    platform_sends ................ 5 · 19/08 19:41
⛔ NUNCA ESCREVEU     playbook_overlays ............. 0 · —
```

⚠️ **E aqui está a honestidade que muda o desenho:** 📊 os 4 agentes de
atendimento estão `is_active = false` (`SELECT name, is_active FROM agents WHERE
agent_role='attendance'` → 4 de 4 `false`). **Boa parte deste silêncio é
DELIBERADA** — o piloto não começou.

> 🔴 **E é exatamente esse o defeito.** A Central **não consegue distinguir
> "desligado de propósito" de "quebrado em silêncio"**. Os dois aparecem iguais.
> Quando o piloto ligar, o Founder vai olhar 14 cards e não vai saber qual dos
> dois está vendo.

### 1.5 · 📊 O menor dos defeitos, e o que ele PROVA

```python
# app/admin/central-agentes/page.tsx  ·  const COLORS = {...}   →  9 chaves
# backend/app/core/heartbeat.py       ·  AGENT_TASKS            → 14 agentes
# SEM COR: conselho · espelho_atendimento · observador · sentinela_rotas · tecelao
```

📊 **5 dos 14 caem na cor padrão.** ⚠️ Sozinho é cosmético. 🔴 **O que ele prova
não é:** uma segunda lista de agentes, no frontend, **envelheceu em silêncio**
enquanto a primeira crescia. Qualquer coisa nova que esta SPEC criar — grupo,
cor, fonte de produção — **repete esse defeito se morar numa segunda lista.**

### 1.6 · 📊 O console do Garimpo mostra vazio, e há 270 linhas

```python
backend/app/api/admin_spec034.py:90
    garimpo = [r for r in rows.data or [] if r.get("source") == "garimpo"]
backend/app/api/admin_spec034.py:99
    for r in (rows.data or []) if r.get("source") == "sugestoes_ia"
```

📊 `SELECT source, count(*) FROM broker_insights GROUP BY 1;` → **`garimpo_v3` ·
270**, e mais nada.

> 🔴 **`"garimpo"` casa com 0 de 270. `"sugestoes_ia"` casa com 0 de 270.** A tela
> `/admin/insights` mostra ranking vazio, e o operador conclui *"não há nada"*.

⚠️ É o mesmo defeito da §1.1 com outra roupa: **a tela responde com confiança
sobre um filtro que não casa.** É um `grep` de conserto, e entra nesta SPEC porque
é o mesmo console e a mesma classe.

---

## 0. O TESTE DO PRODUTO

> **A Sentinela — que destrava o segurado parado na URA — morre numa
> quinta-feira. Na sexta o Founder abre a Central e o card dela está
> AMARELO com "pulsa há 6h, não destrava nada há 2 dias", e não cinza
> "AGUARDANDO".**

⛔ **Qualquer bloco que não sirva a esse parágrafo sai desta SPEC.**

⚠️ **E a cadeia até o segurado tem dois passos — está declarado, não escondido.**
A Central é `require_master_admin`: o segurado nunca a vê. O que ela vigia são os
agentes que **falam com ele** — `followup`, `vigia_sentinela`, `cerebro`. 🔴 **Um
instrumento cego sobre a cadeia de atendimento é o motivo de ninguém ter percebido
17 dias de `knowledge_cards` parado.**

---

## 2. ⛔ AS TRAVAS

```
⛔ NENHUMA mensagem sai para segurado. NENHUM agente é ligado.
⛔ NENHUM `is_active` muda. Os 4 de atendimento continuam `false`.
⛔ NENHUMA entrada em portal de seguradora.
⛔ Banco: SELECT livre. 🔴 ZERO migration nesta SPEC — ver §5.
⛔ A Central continua `require_master_admin`. NADA daqui aparece para corretora.
⛔ NUNCA imprimir CPF, telefone, apólice, placa ou nome de pessoa.
⛔ NÃO mexer em variável de ambiente.
⛔ NUNCA `git add -A` (P-247).
```

---

## 2.1 🔴 A CONTA DO §3 — a conversão fez, e o executor CONFERE

⚠️ **Isto não substitui o EXECUTION CARD do executor** (protocolo §0.2). É a conta
da conversão, escrita para ele **discordar com número** se medir diferente.

```
ALCANCE ........... 2   a Central é `require_master_admin`: o segurado NUNCA a vê.
                        🔴 Mas o que ela vigia alcança o segurado, e a cadeia
                        tem DOIS passos — por isso 2, e não 3. Ver §0.
REVERSIBILIDADE ... 0   🔴 e é DESENHO, não sorte: zero migration (§5).
                        Revert + as chaves do Redis expiram = não sobra nada.
FREQUÊNCIA ........ 2   `beat()` é chamado em TODO atendimento
                   ──
RISCO ............. 4
SUPERFÍCIE ........ 3   🔴 subiu de 2 para 3 na revisão de 02/09, e a razão é
                        medida: eu listáva as 📊 27 chamadas a `beat()` e
                        conclí que sabia apontar tudo. ⚠️ **Não sabia.**
                        📊 `work_runs` · 7 dias: **SEIS `workflow_key`,
                        640 execuções**, e 🔴 **CINCO** não têm card nem
                        `beat()`. ⚠️ O `garimpo` tem os dois
                        (`heartbeat.py:44` e `broker_insights.py:343`)
                        — e por isso ele é o D1, não um dos invisíveis:
                          detect_signals 504 (hoje 21:03) · outcomes 84
                          garimpo 21 · daily_briefing 21 · cluster 7 · weekly 3
                        🔴 O §3 é explícito: *"consigo apontar TODOS os
                        lugares? Não → SUPERFÍCIE 3."* Eu não conseguia.
                        ⚠️ RISCO 4 × SUP 3 acrescenta **investigador** e
                        **desenhista da prova** ao time (§3.1)
PISO .............. nenhum, por EFEITO (§3.2), e cada linha conferida:
                        não envia · sem migration · não toca auth nem
                        `company_id` · não escreve noutra corretora
TIME .............. builder · juiz · verificador · 🔴 **investigador** ·
                    🔴 **desenhista da prova**   (§3.1, RISCO 4 × SUP 3)
                    ⚠️ os dois últimos entraram com a SUPERFÍCIE 3
PARALELISMO REAL .. nenhum. A e B tocam `heartbeat.py` e os mesmos call sites
FAIXA DE RELÓGIO .. 🔴 **4–7h**   faixa, nunca promessa (§9.2)
                    ⚠️ subiu de 3–5h com a SUPERFÍCIE e os dois papéis novos
```

🔴 **A auditoria externa (§6.1) NÃO é obrigatória aqui** — RISCO 4, e nada sai do
prédio. ⚠️ **Recomendada mesmo assim**, por um motivo medido: os arquivos editados
(`dispatch_router`, `dispatch_followup`, `dispatch_watchdog`) são a cadeia do
atendimento, e o §6.1 mede que quem olha de fora pega **o que o próprio conserto
criou**.

---

# BLOCO 0 · 🔴 REMEDIR, antes de escrever a primeira linha

⚠️ **Os números desta SPEC são de 02/09/2026. Eles vão ter dias quando você
executar.** O `INDICE-DE-SPECS.md` registra por que isto é regra: 📊 a proposta da
087 afirmava `structural escalated = 4`; no dia da conversão o medido era **14 + 2**.

**Rode e cole a saída no relatório:**

```sql
-- ① o laço roda e a saída não cresce?  (o defeito da §1.1)
SELECT workflow_key, status, count(*), max(created_at)
  FROM work_runs WHERE created_at > now() - interval '3 days' GROUP BY 1,2;
SELECT 'broker_insights' t, count(*), max(created_at) FROM broker_insights
UNION ALL SELECT 'conversation_scorecards', count(*), max(created_at) FROM conversation_scorecards
UNION ALL SELECT 'observed_events', count(*), max(created_at) FROM observed_events
UNION ALL SELECT 'ura_maps', count(*), max(created_at) FROM ura_maps
UNION ALL SELECT 'route_drift', count(*), max(created_at) FROM route_drift
UNION ALL SELECT 'attendance_transcripts', count(*), max(created_at) FROM attendance_transcripts
UNION ALL SELECT 'playbook_overlays', count(*), max(created_at) FROM playbook_overlays
UNION ALL SELECT 'platform_sends', count(*), max(created_at) FROM platform_sends
UNION ALL SELECT 'knowledge_cards', count(*), max(created_at) FROM knowledge_cards;

-- ② o silêncio é deliberado?
SELECT name, agent_role, is_active FROM agents ORDER BY agent_role;

-- ③ o filtro do console casa?   🔴 espere `garimpo_v3`, não `garimpo`
SELECT source, count(*) FROM broker_insights GROUP BY 1;
```

```bash
# ④ a lista dupla ainda diverge?
python - <<'PY'
import re
c=open('app/admin/central-agentes/page.tsx',encoding='utf-8').read()
cor=set(re.findall(r'(\w+):',re.search(r'const COLORS[^{]*\{(.*?)\};',c,re.S).group(1)))
t=re.findall(r'\("([a-z_]+)", "',open('backend/app/core/heartbeat.py',encoding='utf-8').read())
print(len(cor),'cores ·',len(t),'agentes · sem cor:',sorted(set(t)-cor))
PY
```

## O gate do BLOCO 0

```
① as 4 causas D1–D4 continuam no código, com o arquivo:linha desta SPEC
   🔴 se alguma já foi consertada, o bloco correspondente SAI — e o relatório diz
② ao menos UM agente com laço `completed` recente e saída parada — o caso da §1.1
   ⚠️ se não houver nenhum hoje, a SPEC continua: o defeito é estrutural,
   não depende de estar acontecendo no minuto da execução
③ 🔴 `AGENT_TASKS` tem 14 entradas. Se tiver outro número, a tabela do BLOCO A
   é REFEITA por medição, não copiada daqui
```

---

# BLOCO A · 🔴 Cada agente declara o que PRODUZ — e num lugar só

## O problema

📊 O pulso mede o **laço**. Nada no produto mede a **saída**. E `beat()` aceita
`actions: int = 0` (`heartbeat.py:54`), então o valor honesto e o valor decorativo
são indistinguíveis no destino.

## O conserto

🔴 **`AGENT_TASKS` passa a ser a ÚNICA lista.** Cada entrada ganha três campos:

```
grupo               a que propósito ele serve      (BLOCO C)
cor                 🔴 sai do frontend e vem para cá   (mata a §1.5)
fonte_de_producao   a consulta que responde "ele produziu?" — ou None
cadencia_esperada   de quanto em quanto tempo ele DEVIA produzir
```

📊 **As fontes que a conversão já mediu — confira, não copie:**

| agente | fonte de produção | 📊 último em 02/09 |
|---|---|---|
| `observador` | `observed_events` | 26/08 13:52 |
| `tecelao` | `ura_maps` | 26/08 14:07 |
| `sentinela_rotas` | `route_drift` | 26/08 14:07 |
| `espelho_atendimento` | `attendance_transcripts` | 26/08 16:40 |
| `followup` | `platform_sends` | 19/08 19:41 |
| `garimpo` | 🔴 **as DUAS, com `greatest()`** — `intelligence_signals`·`source_type='garimpo'` **e** `broker_insights`·`source IN ('garimpo_v3','garimpo','garimpo_llm')` | 26/08 00:04 e 00:05 |
| `detector` | 🔴 `intelligence_signals` · `source_type='detector'` — **não existe card para ele** | ⚠️ **02/09 04:04 — VIVO HOJE** |

🔴 **Por que o `garimpo` usa `greatest()` das duas, e não uma:** 📊 o fluxo
canônico escreve **as duas com a mesma caneta** — `workflows.py:291` chama
`GarimpoV3`, que grava `intelligence_signals` na `:106` e **projeta** em
`broker_insights` na `:174` pela `_projetar_legado` (`:164`), **incondicional**
(📊 `grep -c cutover garimpo_v3.py` → **0**). Os dois últimos registros
distam 📊 **69 segundos**. ⚠️ E o caminho de rollback grava OUTRO rótulo —
`source='garimpo'`/`'garimpo_llm'` (`broker_insights.py:98,:232`), 📊 com
**zero linhas em toda a história da tabela**.

> 🔴 **Uma fonte só cega o card no dia em que a flag virar.** Com o cutover
> desligado, o legado escreve `broker_insights` e **para** de escrever
> `intelligence_signals`. O `greatest()` sobrevive nas duas direções.

⚠️ **Esta linha já esteve errada duas vezes, e as duas por não abrir a
`_projetar_legado`:** a conversão cravou `source='garimpo_v3'` — uma versão atrás
do escritor — e o primeiro conserto inverteu para `intelligence_signals` citando
a `garimpo_v3.py:216`, que é um `.select()` de painel dentro da
`voz_do_periodo()`. **Uma LEITURA apresentada como escritor.**
| `auditor` | `conversation_scorecards` | 26/08 00:19 |
| `alfaiate` | `playbook_overlays` | ⛔ **0 linhas, nunca** |
| `cartografo` | `ura_maps` | 26/08 14:07 |
| `sugestoes` | `broker_insights` · `source='sugestoes_ia'` | ⛔ **0 de 270** |
| `espelho` · `vigia_sentinela` · `cerebro` | 🔎 **o executor mede e declara** | — |
| `conselho` | ⛔ **sem saída durável conhecida** | — |

🔴 **A regra que fecha a porta, e é a §7 do protocolo aplicada à própria Central:**

> **Agente sem `fonte_de_producao` declarada mostra `NÃO MEDIDO`. NUNCA
> `SAUDÁVEL`.** *"Sem referência inspecionável, a dimensão vira 'não avaliada',
> nunca 'aprovada'."*

⚠️ **Custo:** a leitura roda no backend com cache de 60s em Redis. ⛔ **Não é uma
consulta por card a cada 20s** — a tela recarrega a cada 20s hoje, e 14 consultas
× 3/min contra produção é um autogol.

⛔ **E não é uma tabela nova.** `max(created_at)` da tabela que o agente já
escreve **é** o histórico. Uma tabela de "saúde de agente" seria um segundo lugar
para a verdade — que é o defeito da §1.5 sendo reconstruído.

## O gate

```
① os 14 agentes têm grupo, cor e fonte (ou `None` explícito) — 🔴 nenhum implícito
② `/api/admin/spec034/agents-status` devolve, por agente:
   pulso · última produção · cadência esperada
③ 🔴 o frontend NÃO tem lista de agente nenhuma — nem cor, nem nome, nem grupo
④ a leitura inteira responde em UMA chamada, com cache de 60s
⑤ dois tenants: um SELECT sem filtro de empresa não vaza para a resposta
   ⚠️ a Central é de plataforma e agrega tudo — o gate é que o número
   agregado NUNCA é servido por rota de corretora (ver ⑥ do BLOCO D)
```

🔴 **A mutação:** apague `fonte_de_producao` de um agente. O gate ① tem de ficar
**vermelho**, e o card dele tem de virar `NÃO MEDIDO` — nunca verde.

---

# BLOCO B · 🔴 Cinco estados, e o verde é o mais difícil de conseguir

## O problema

📊 `health()` em `app/admin/central-agentes/page.tsx` tem 3 estados e todos
derivam de **um** número: `last_run`. `< 900s` → SAUDÁVEL · `< 7200s` → ATENÇÃO ·
resto → PARADO · `null` → AGUARDANDO.

⚠️ **E o limiar é o mesmo para os 14, o que produz duas mentiras de uma vez:**

```
📊 Garimpo   pulsa 1×/hora (`buffer_processor.py:148`, seconds=3600)
             → 🟢 15 min de cada hora · 🟡 os outros 45
             ⛔ e mineração ZERO há 7 dias nas duas cores
📊 Conselho  roda raramente, por env    →  🔴 PARADO quase sempre, por DESENHO
```

> 🔴 **Um limiar único condena o agente lento a viver vermelho e promove o
> agente frequente a verde.** Quando o vermelho é normal, ninguém olha para ele —
> e é assim que um instrumento morre sem que ninguém desligue.

## O conserto

```
🟢 SAUDÁVEL          pulsou  E  produziu dentro da cadência DELE
🟡 PULSA SEM PRODUZIR  o laço roda e a saída não cresce      ← o Garimpo, hoje
⚪ DESLIGADO          declarado, e diz DESDE QUANDO          ← o atendimento, hoje
🔴 PARADO            devia pulsar na cadência dele, e não pulsa
⚫ NÃO MEDIDO        sem fonte declarada (BLOCO A)           ← o Conselho, hoje
```

🔴 **`DESLIGADO` sai de um fato do banco, não de um palpite:** os agentes ligados
à cadeia de atendimento leem `agents.is_active` da tabela. ⛔ **Se o motivo do
silêncio não for verificável, o estado é `PARADO`** — e não `DESLIGADO`. A dúvida
paga do lado de quem alerta.

## E as duas travas que fazem o pulso valer alguma coisa

```
D1  `broker_insights.py:337`   o pulso SAI do `finally`
    🔴 caminho de exceção não pinta card. Falhou → o card conta a falha
    ⚠️ **E isto sozinho não muda NADA em produção**, porque o `return 0` da
    `:311` já torna a linha inalcançável. 🔴 **O pulso do Garimpo tem de
    nascer no fluxo canônico** (`garimpo_v3.py` / `workflows.py:291`), senão
    o gate fica verde com o card mentindo igual (§0.3 do protocolo)
D2  🔴 **AS OITO chamadas cruzadas do gate ⑥, não só a `:181`:**
    `agent_memory:212` · `history_ingest:204` · `history_ingest:212`
    `route_sentinel:444` · `attendance_distiller:1344` · `auditor:181`
    `prompt_optimizer:199` · `regression_sentinel:160`
    🔴 cada agente dá o próprio pulso, ou não dá nenhum
    ⚠️ **Consertar só a `:181` REPROVA no gate ⑥** — e era esse o erro que
    o gate existe para impedir. 🔴 As três do `alfaiate` vão para
    `playbook_tailor.py`, que é a casa dele
```

⚠️ **D3 (`attendance_capture.py:378`, `_beat(0)`) NÃO é removido.** Com a regra
nova ele passa a ser **honesto**: pulsou, não produziu → 🟡. Era só o destino que
estava errado.

## O gate

```
① o Garimpo de hoje (laço `completed`, saída de 7 dias atrás) → 🟡, NUNCA 🟢
   🔴 e o teste roda com `last_run` de 1 MINUTO ATRÁS — a janela exata em que
   o código de hoje pinta 🟢. ⛔ Testar com pulso velho não prova nada:
   ali o código antigo já daria 🟡 sozinho, pelo motivo errado
② agente `is_active=false` → ⚪ DESLIGADO. 🔴 **E a data é opcional por
   medição, não por preguica:** 📊 `SELECT count(desligado_em) FROM agents` →
   **0 de 8**. A coluna existe e está inteiramente NULL, e esta SPEC proíbe
   migration e backfill. **Sem data → o card escreve `sem registro`**, nunca
   uma data inferida do último transcript
②-b 🔴 **E `is_active` é POR CORRETORA:** 📊 a `core` tem 3 `true` e 1 `false`.
   O card da Central é UM, de plataforma. **A regra é `all()`: DESLIGADO só
   quando TODAS as corretoras desligaram** — uma ligada já espera trabalho.
   ⚠️ E não existe chave ligando os 8 `agents.slug` aos 14 de `AGENT_TASKS`:
   **agente sem correspondência mostra `NÃO MEDIDO`, nunca `DESLIGADO`**
③ agente sem fonte → ⚫ NÃO MEDIDO
④ 🔴 agente morto há 30 dias → 🔴 PARADO.  ⛔ o `_TTL` de 7 dias NÃO pode
   transformar morte antiga em ⚪ — é a §1.2 D4, e é o coração desta SPEC
⑤ 🔴 LINHA DE CONTROLE: um agente que pulsou E produziu na cadência dele → 🟢
   ⚠️ sem esta linha, um guarda que pinta tudo de amarelo passaria em ①–④
```

🔴 **A mutação obrigatória, e são duas:**

```
1. force `last_run = agora` e a produção parada  →  ① tem de ficar 🟡
   ⛔ se ficar 🟢, o guarda não guarda: é o defeito original, intacto
2. force a chave de heartbeat a EXPIRAR (morte de 30 dias)  →  ④ tem de dar 🔴
   ⛔ se der ⚪ AGUARDANDO, o D4 continua vivo com teste verde em cima
```

---

# BLOCO C · Os quatro grupos — a queixa do Founder, respondida

## O conserto

📊 Os 14 agentes respondem a **quatro** perguntas, e a descrição de cada um em
`heartbeat.py` já diz qual:

```
👁️  OBSERVA E REGISTRA      o que aconteceu ficou gravado
    observador · tecelao · espelho · espelho_atendimento

🚑 ATENDE AGORA            alguém está esperando neste minuto
    vigia_sentinela · cerebro · followup
    🔴 é o único grupo que ALCANÇA O SEGURADO

🧭 MANTÉM A ROTA CERTA     a seguradora mudou e nós acompanhamos
    sentinela_rotas · alfaiate · cartografo

🎓 APRENDE E AVISA         ontem virou conserto e recomendação
    garimpo · auditor · sugestoes · conselho
```

**Cada grupo abre com UMA linha de resumo, e ela é a única coisa que o Founder
precisa ler:** `3 de 3 saudáveis` · `1 pulsa sem produzir` · `4 desligados desde
26/08`.

## ⚠️ O que eu NÃO fiz, e por quê — está aqui para o Founder derrubar se quiser

O pedido diz *"cada grupo com sua página"*. 📊 **Não fiz, e a razão é medida:**

```
lib/navigation.ts:MENU_NAO_CRESCE = 5, guardado por backend/tests/test_menu_nao_cresce.py
lib/navigation.ts, histórico: 8 telas já MUDARAM DE CASA por excesso de navegação
                              Briefing e Pesquisas entraram como pilar e saíram
```

> ⚠️ **Quatro páginas novas para 14 cards adiciona navegação para consertar
> navegação.** Um grupo com 3 cards não sustenta uma página.

✅ **O que entrega o mesmo:** os quatro grupos **numa tela só**, cada um com
título, a frase do propósito e a linha de resumo. 📊 **É o que a SPEC-093 fez com
os corredores**, e funcionou.

🧑 **CAIXA DO FOUNDER · F-088-01** — se depois de ver agrupado ainda parecer
confuso, a próxima peça é **uma página por grupo, e aí o menu muda por escrito**.
⛔ **Não bloqueia.**

## O gate

```
① os 14 aparecem, em 4 grupos, e o grupo sai de `AGENT_TASKS` (BLOCO A)
② 🔴 nenhum agente fica fora de grupo — inclusive um agente NOVO
   ⚠️ é a §1.5: a lista que não sabe do agente novo é a que mente
③ cada grupo tem a linha de resumo, e o número dela bate com os cards
④ os 5 sem cor ganham cor — 🔴 vinda de `AGENT_TASKS`, não de mapa no frontend
⑤ `test_menu_nao_cresce.py` continua verde: nenhum pilar novo
```

🔴 **A mutação:** acrescente um 15º agente a `AGENT_TASKS` **sem grupo**. O gate ②
tem de ficar **vermelho**. ⛔ Se ficar verde, a SPEC reconstruiu a §1.5.

---

# BLOCO D · O console para de mostrar vazio, e o guarda que segura tudo

## O conserto — a parte de um `grep`

📊 `admin_spec034.py:90` e `:99` filtram `"garimpo"` e `"sugestoes_ia"`; o banco
só tem `garimpo_v3`.

⛔ **Não é trocar a string.** 🔴 **O filtro sai do código e vira a mesma
`fonte_de_producao` do BLOCO A** — senão a próxima versão (`garimpo_v4`) repete
o defeito em silêncio, e é exatamente o que aconteceu de `garimpo` para `garimpo_v3`.

## O guarda

**Um arquivo, no formato do `backend/tests/test_o_protocolo_tem_policia.py`.**

## O gate

```
① 🔴 o ranking de `/admin/insights` devolve > 0 com 270 linhas no banco
   ⚠️ e o teste conta LINHAS DO BANCO, não confia em leitura de código
② 🔴 LINHA DE CONTROLE: banco realmente vazio → devolve 0 **sem erro**
   ⚠️ sem ela, "devolve linhas" passaria com um filtro que aceita tudo
③ toda `fonte_de_producao` de `AGENT_TASKS` aponta para tabela/coluna que EXISTE
   🔴 um `source` inventado tem de reprovar o teste
④ os 14 têm grupo e cor; o frontend não tem lista de agente
⑤ 🔴 NENHUM `beat(` mora dentro de um `finally:` — em NENHUM dos 18 arquivos
   ⚠️ é uma regra sobre as 📊 27 chamadas, não sobre a do Garimpo:
   consertar só o caso conhecido deixa os outros 26 livres para repetir
⑥ 🔴 nenhum agente dá o pulso de outro — o `beat("x")` está no laço do `x`
   📊 **NÃO é uma violação. São OITO**, medidas em 02/09:
     `agent_memory:212`→espelho · `history_ingest:204`→espelho_atendimento
     `history_ingest:212`→observador · `route_sentinel:444`→alfaiate
     `attendance_distiller:1344`→espelho_atendimento · `auditor:181`→alfaiate
     `prompt_optimizer:199`→alfaiate · `regression_sentinel:160`→auditor
   🔴 **O `alfaiate` recebe de TRÊS módulos e não pulsa da casa dele.**
   ⚠️ 📊 `backend/app/services/playbook_tailor.py` linha 1 diz `ALFAIATE v1
   (SPEC-034 Onda 4)` — existe desde 26/08, e 📊 `grep -c 'beat('` dá **0**.
   **A casa existe e não pulsa.** O conserto é mover o pulso para lá, não
   escolher qual dos três invasores fica
   ⚠️ Consertar só o `:181` deixa as outras sete de pé — e era exatamente
   esse o erro que este gate existia para impedir
⑥-b 🔴 **TODO `workflow_key` visto em `work_runs` nos últimos 7 dias tem
   agente correspondente em `AGENT_TASKS`** — ou está numa lista de
   `SEM CARD, POR DECISÃO` escrita nesta SPEC.
   📊 Hoje **CINCO reprovam** (o `garimpo` passa), inclusive o
   `detect_signals` (504 execuções,
   59 sinais, o único que produziu alguma coisa hoje).
   ⚠️ **Este é o único gate que teria pegado o motor invisível** — e é a
   §1.5 desta SPEC aplicada à lista que sobrou
⑦ 🔴 DOIS TENANTS: nenhuma rota de corretora serve `agents-status` nem o número
   agregado. `require_master_admin` provado, não presumido
⑧ `next start` + 1 requisição a `/api/admin/spec034/agents-status`
   (`CLAUDE.md` §9.1 — mexeu em `app/`)
```

🔴 **A mutação do guarda:** troque uma `fonte_de_producao` por
`tabela_que_nao_existe`. O gate ③ tem de ficar **vermelho**. ⛔ Restaurar **por
cópia**, nunca `git checkout` (protocolo §10 · P-231).

---

## 3. 🔴 O QUE SAIU DA PROPOSTA — e o gatilho de cada peça

📊 A proposta tem **3.718 linhas**. Saiu quase tudo, e a razão é uma só:
**ela dimensiona uma organização de agentes que este projeto não tem.**

📊 **A conta de hoje, 02/09:** `agents` = **8 linhas — 2 por corretora × 4
corretoras.** ⚠️ **Uma corretora vê DOIS agentes.** `agent_delegations` = **0**.
`routines` = **1**. `tenant_auxiliaries` = **9**.

| peça da proposta | 📊 medido hoje | **volta quando** |
|---|---|---|
| contratos de delegação entre agentes | `agent_delegations` = **0 linhas** | existir a primeira delegação real |
| Admission Gate ("precisa de mais de um agente?") | 1 corretora = 2 agentes | houver caso com 3+ agentes disputando o mesmo pedido |
| grupos paralelos de 2–5 workers · Lead/Orchestrator | nenhum grupo existe | 🔴 depois do Admission Gate, nunca antes |
| papéis, especialistas e juízes dentro do produto | o painel de juízes é do **protocolo**, não do produto | ⛔ **e o protocolo v10 §5.1 proíbe:** juiz julga código, não documento |
| Quality Gate por resultado de agente | `conversation_scorecards` já dá nota | consolidar isto seria peça nova com nome de consolidação |
| ontologia "Auxiliar não é subagente" | ✅ **já é canon** — `ONTOLOGIA-DO-TRABALHO.md` | ⛔ nunca: reescrever canon que já existe é motor paralelo (`CLAUDE.md` §5) |

> ⚠️ **Nada foi julgado ruim. Foi julgado cedo.** O gatilho da auditoria de 26/08
> era *"quando agentes ou auxiliares passarem de ~20"*. 📊 **Hoje: 8 agentes e 9
> auxiliares instalados. O gatilho NÃO disparou.**

🔴 **E é por isso que a SPEC mudou de assunto:** medindo a navegação, o defeito
que apareceu foi o instrumento mentindo — que **muda o produto** e custa 🔴 **4–7h**,
contra uma organização operacional que **não muda nada hoje** e custa semanas.

---

## 4. A REFERÊNCIA — §7.1, por caminho, e o juiz ABRE

| dimensão | referência | como comparar |
|---|---|---|
| **um guarda serve?** | `backend/tests/test_o_protocolo_tem_policia.py` | 📊 **205 linhas** · 17 asserções · **e a mutação escrita no commit `9dddb7f`**. O guarda do BLOCO D chega perto? |
| **a tela não mente** | `backend/tests/test_a_casa_diz_a_verdade.py` | 📊 236 linhas — o precedente deste projeto de guardar contra documentação e menu que contradizem o código |
| **UI / design** | `docs/canon/DS-001-design-brief.md` **§5** | o agrupamento do BLOCO C |
| **o número é medido?** | `CLAUDE.md` §12.1 | 📊 tem consulta e data · 💭 nunca é citável |

⚠️ **`CLAUDE.md` §9.3 vale aqui ao pé da letra:** os gates desta SPEC comparam o
comportamento do **motor** (a rota, o `health()` real) sobre dado **real do
banco** — nunca um regex sobre a declaração.

---

## 5. ⛔ POR QUE ZERO MIGRATION — e é decisão, não esquecimento

```
a produção sai de `max(created_at)` da tabela que o agente JÁ escreve
o estado é CALCULADO na leitura, com cache de 60s em Redis
```

🔴 **Consequência da conta do §3:** REVERSIBILIDADE = **0**. Desfeito o commit,
as chaves do Redis expiram e **não sobra estrutura nem dado**. ⛔ Uma tabela
`agent_health` teria posto a SPEC no piso de RISCO 6 (§3.2) e criado um segundo
lugar para a verdade.

---

## 6. O que fica pendente

```
P-088-01  🔴 `knowledge_cards` parado desde 16/08 — 📊 17 dias, 18.715 linhas,
          zero novas. Herdada da P-090-02 e RECONFERIDA hoje. Esta SPEC faz o
          silêncio APARECER; ⛔ não religa o destilador.
P-088-02  📊 `playbook_overlays` = 0 linhas desde sempre. O Alfaiate nunca
          escreveu nada. Depois desta SPEC o card dele fica 🟡 o tempo todo —
          🔴 e isso é a informação certa, não um defeito da Central.
P-088-03  📊 `platform_sends` = 5 linhas, última em 19/08. Se é a fonte do
          Follow-up, ele está mudo há 14 dias. 🔎 confirmar a fonte (BLOCO A).
P-088-04  🔴 P-70 continua aberta: o Follow-up PERGUNTA ao segurado e ninguém lê
          a resposta (`heartbeat.py`, comentário de 03/08). O card fica 🟡
          honesto; ⛔ o ciclo continua sem fechar.
P-088-05  ⚠️ O 6º pilar `Memórias` é EXCEÇÃO TEMPORÁRIA de 18/08 com "quando
          tirar" escrito em `lib/navigation.ts` — 📊 **15 dias sem a decisão**.
          🧑 é do Founder: vira pilar por escrito, ou volta para dentro de um.
P-088-06  📊 10 de 17 tabelas com RLS ligada e ZERO policies (P-090-01). Não é
          desta SPEC; ela não cria tabela.
```

---

## 7. A ordem de execução

```
0  →  A  →  B  →  C  →  D
```

🔴 **A ordem não é negociável:** B classifica o que A declara, C mostra o que B
classificou, D guarda os três. ⛔ **Começar por C** (o agrupamento, que é o pedido
literal) entrega uma tela mais bonita mentindo o mesmo verde.

⚠️ **A escrita é de UM SÓ** (protocolo §8): A e B tocam `heartbeat.py` e os call
sites; **paralelizar aqui é o caso medido da SPEC-085.**

💭 **~4–7h** (subiu de 3–5h com a SUPERFÍCIE 3 e os dois papéis novos). O BLOCO A domina — declarar e conferir 14 fontes de produção, três
delas por medição do executor.
