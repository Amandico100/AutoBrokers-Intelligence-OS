# SPEC-093-B · O SINISTRO DEIXA RASTRO — o trabalho humano de hoje vira dataset, sem tocar no segurado

> **O que ela entrega:** todo atendimento que fala de sinistro passa a existir como um **Work Run
> de sombra** no Work OS, com um log de eventos por ator (robô · atendente · segurado · seguradora)
> e esperas medidas — sem um byte de texto livre, sem uma mensagem a mais para o segurado, sem
> decidir nada. Um digest diário agrupa os rastros em **variantes de processo** e escreve sinais
> no trilho de inteligência que já existe. A Central mostra o trabalhador novo sozinha.
>
> **v1 · 03/09/2026 · protocolo v11** · commit base `b70225f` · repo `AutoBrokers-FIX`
> Proposta: `specs-propostas/7 - SPEC-093-claims-learning-shadow.md` (3.075 linhas)
> Research-pack: `specs-propostas/7 - SPEC-093-claims-learning-shadow-RESEARCH-PACK.md` · reaberto em 03/09/2026
> Número: **093-B** — 093 já foi executada (INDICE-DE-SPECS, decisão do Founder de 30/08).

---

## 0. O TESTE DO PRODUTO

> **Na quarta-feira do piloto, um segurado da Resulta escreve "bati o carro, e agora?". O robô
> faz o que já faz (coleta e entrega ao humano). A Regina assume, pede o boletim de ocorrência,
> anota `#nota seguradora pediu fotos dos dois lados`, espera três dias pela seguradora e encerra.
> Na sexta, o Founder abre a Central e vê o trabalhador "Sombra de sinistros": 1 caso, 6 eventos,
> 3 dias em espera da seguradora. Em 30 dias, com 40 casos, o digest diz: "auto × Porto: 23 casos
> seguiram a mesma sequência de 5 passos". Nenhum segurado recebeu uma palavra a mais.**

⛔ Qualquer bloco que não sirva a esse parágrafo sai desta SPEC.
⛔ **Esta SPEC é C0 — OBSERVA.** Não recomenda, não inicia, não fala com seguradora, não muda a
conduta do atendente nem do robô. A referência ④ (ARISE) começa em L1; nós criamos o degrau abaixo.

---

## 1. 📊 O QUE A MEDIÇÃO DE HOJE ACHOU — 03/09/2026, produção `dcajcvlzcjbmyapmklil`

### 1.1 · Não existe objeto "caso", e o número 093 está ocupado
📊 `SELECT relname FROM pg_class WHERE relname ~ 'case|claim|sinistro'` → só `research_claims` (0 linhas, outro domínio).
📊 175 tabelas em `public`; nenhuma com `tipo_sinistro`, `documentos` ou `data_ocorrencia`. A tela
"casos" (`app/dashboard/atendimentos/casos/`) é uma **view derivada** de `conversations` +
`attendance_sessions` (`app/api/dashboard/atendimentos/route.ts:217-219`), não uma tabela.

### 1.2 · A classificação de sinistro é recalculada a cada turno e descartada
📊 `backend/app/services/atlas/templater.py:1670 infer_ramo_servico` é o único classificador; não há
enum de intenção. Linha 1725: `servico = servico or "sinistro"` — **sinistro só ganha se nenhuma
palavra de assistência apareceu antes** ("bati o carro, preciso de guincho" sai `auto/guincho`).
O prompt corrige em prosa (`prompts.py:131`). Chamadores `graph.py:792` e `weaver.py:855` **não
persistem** o resultado: 📊 `attendance_sessions.servico` NULL em **12.616 de 12.616**;
`observed_sessions.servico` NULL em **580 de 580**. A ficha (`conversations.ficha_atendimento`) tem
conteúdo em **1 de 679** conversas.

### 1.3 · O handoff existe inteiro e nunca disparou
📊 `conversations.status='HUMAN_REQUESTED'` → **0** · `human_handoff_reason IS NOT NULL` → **4**
(nenhum com "sinistro") · `claimed_by IS NOT NULL` → **1** · `resolvido_em` → **0** · `work_waits` →
**0 linhas** · `work_runs.unblock_state='assumido_por_humano'` → **0** · `work_events` com ator
humano → **0 em 35.705**. Caminho: `human_handoff.py:611` → `dispatch_router.py:1138` →
`o_fim_do_atendimento.py:251 abrir_espera(ESPERANDO_HUMANO)` → `handoff_watchdog.py:471`.
📊 `human_handoff.py:19-20`: a tool só é anexada com `tools_config.human_handoff.enabled`. **Medido em
03/09: `enabled=false` em 1 dos 8 agentes e AUSENTE nos outros 7.** A tool nunca esteve ligada em
lugar nenhum — os zeros do handoff são "nunca esteve ligada", não "nunca precisou". 🔴 O sinal
humano REAL hoje é o botão **Assumir** do painel (`ConversasClient.tsx:432` → `claimed_by`), não o
handoff do robô. O BLOCO B trata `claims.handoff_pedido` como evento OPCIONAL e `claims.humano_assumiu`
como o gesto principal. F-093B-05.

### 1.4 · A anotação da atendente tem porta e zero uso
📊 `notas_da_atendente` → **0 linhas** (escritor único `a_nota_da_atendente.py:207`, gatilho
`webhook.py:1550`, prefixo `^#nota`). `messages WHERE payload ? 'nota_interna'` → **0**. 📊 `grep -rn
"notas_da_atendente" app components` → **0**: nenhuma tela lê a nota depois de gravada.

### 1.5 · O volume existe, e é o limite superior
📊 regex `sinistro|colis[ãa]o|batida|roubo|furto|acidente|terceiro` em `attendance_transcripts.text`
→ **4.827 linhas · 2.187 sessões · 2 corretoras**, de 156.917. Só a palavra exata `sinistro`
(`\msinistro\M`): **222 sessões em 08/2026**, 195 em 07, 161 em 05 — entre 94 e 222 sessões/mês nos
últimos 12 meses. Distribuição mensal estável em **~130–270 sessões/mês** (07/2025→08/2026). ⚠️ `terceiro` e
`acidente` casam fora de contexto: é teto, não contagem. 📊 `work_runs` de sinistro: **0**.

### 1.6 · O trilho de aprendizagem existe e está quase vazio
📊 `intelligence_signals` 91 (`source_type` ∈ {detector, garimpo}; `domain` ∈ 5 valores, nenhum é
sinistro) · `knowledge_candidates` **0** (o adapter `knowledge_candidate_adapter.py:137` nunca
escreveu em produção) · `intelligence_findings` 14 · `conduct_playbooks` 18 (4 com `servico='sinistro'`).
`intelligence_signals` já tem `conversation_id`, `work_run_id`, `summary_redacted`, `trust_tier`,
`dedupe_key`, `subject_type/subject_id`.

### 1.7 · Documentos chegam e são arquivados, sem ligação a caso
📊 `attendance_transcripts` com `msg_type<>'text'` → **26.943**; com `media_meta` → **24.386** (o maior
acervo pronto). `documents` (11 linhas, RAG) **não tem** `conversation_id`. `_detect_document_type`
existe em `backend/app/api/attendance_media.py:242`.

### 1.8 · O redator não cobre saúde, e 12 tabelas de aprendizagem têm RLS sem policy
📊 `redaction_service.py` (290 linhas): CPF · CNPJ · apólice · sinistro nº · placa · e-mail · telefone ·
cartão · CEP · documento. `grep -Ei "cid|laudo|m[eé]dic|sa[uú]de|prontu"` → **0**. 📊 `pg_policies`
para `intelligence_signals`, `knowledge_candidates`, `notas_da_atendente`, `work_waits`,
`attendance_transcripts`, `observed_*`, … → **0 policies** (RLS ligado nega tudo a `authenticated`; o
backend usa service role). `work_runs` e `work_events` **têm** policies (2 cada).

### 1.9 · O Work OS já é um log de eventos por objeto
📊 `work_runs` (53 colunas): `company_id, conversation_id, workflow_key, outcome_type, status,
risk_level, result_payload jsonb, unblock_state, requested_at/started_at/finished_at`. `work_events`
(12 colunas): `company_id, work_run_id, event_type, actor_type CHECK (system|worker|user|agent|admin|
provider), severity, message_human, payload_redacted, created_at`. `work_waits`: `kind ∈ esperando_
cliente|esperando_seguradora|esperando_humano`, `vence_em`, `satisfeito_em`. 📊 Índices em
`work_runs(company_id, created_at)`, `work_runs(conversation_id)`, `approval_requests/artifacts/
usage_events(work_run_id)`. **É o esquema da referência ① (evento × objetos qualificados) já
construído — falta só o `workflow_key` e o vocabulário de eventos.**

---

## 2. ⛔ AS TRAVAS

```
⛔ NENHUMA mensagem sai para segurado ou seguradora. NENHUM agente é ligado. NENHUM portal.
⛔ A CONDUTA do atendimento não muda: nem prompt, nem playbook, nem classificador em graph.py.
   A sombra OBSERVA o que já acontece; não desvia um turno.
⛔ ZERO texto livre na sombra: work_events.message_human só por TEMPLATE; payload_redacted só com
   enums, contagens, tipos de documento e timestamps. Nada do que o segurado escreveu entra.
⛔ NUNCA imprimir CPF, telefone, apólice, placa, nome de pessoa, CID, laudo, senha ou token.
⛔ ZERO migration (§7). Banco: SELECT livre; escrita só pelo código do Work OS que já escreve.
⛔ Multi-tenant: todo INSERT e todo SELECT com company_id; teste com DOIS tenants reais.
⛔ NUNCA `git add -A`. NÃO tocar em variável de ambiente.
```

## 2.1 O EXECUTION CARD da conversão — o executor confere e discorda com número

```
OUTCOME ..............  cada sinistro atendido deixa um rastro estruturado no Work OS; um digest diário agrupa
                        variantes e escreve sinais; a Central mostra o trabalhador; nada chega ao segurado
RISCO ................  6   ALCANCE 2 (a corretora vê na Central e no resumo admin; o segurado nunca)
                            REVERSIBILIDADE 2 (linhas em work_runs/work_events/intelligence_signals sobram ao desfazer)
                            FREQUÊNCIA 2 (todo atendimento é avaliado; todo sinistro grava)
SUPERFÍCIE ...........  2   dois escritores (Python e Next) sobre o mesmo vocabulário; uma peça nova (o digest);
                            lugares mapeados em §1 e §4 com file:line
PISO APLICADO ........  nenhum por efeito (não envia · sem migration · não toca auth nem company_id de escrita).
                            ⚠️ MAS grava dado derivado de conversa de sinistro — dado sensível por natureza (ref. ⑦)
NÍVEL ................  CRÍTICO   (RISCO 6+): desenhista da prova ANTES do código · painel de 4 lentes · red team ·
                            auditoria externa · integrador
UNIDADES .............  6   BLOCO 0 · A (detector + abertura da sombra, Python) · B (o ledger: eventos humanos, Python +
                            Next) · C (digest de variantes + prazos + AGENT_TASKS) · D (resumo admin, read-only) · E (guarda)
COESÃO ...............  A+B(Python) juntas (mesmo módulo, mesmo vocabulário) · B(Next) separada, contra o VOCABULÁRIO
                            congelado em §5 · C separada (só lê o que A/B escrevem; fixture) · D separada · E junto
PARALELISMO REAL .....  3 escritores: {A+B py} ‖ {B next} ‖ {C}. D depois de C. E nasce junto. Integração serial
TIME .................  investigador ✅ · pesquisador ✅ · aquecimento (antes do código) · desenhista · 3 builders ·
                            verificador · painel de 4 lentes · red team · juiz de confirmação · auditoria externa
REFERÊNCIA ...........  interna: backend/tests/test_a_central_diz_a_verdade.py (forma do guarda, 12 blocos com controle) ·
                            backend/app/services/o_fim_do_atendimento.py (como se abre espera no Work OS) ·
                            backend/app/services/intelligence/signal_service.py (como se escreve sinal com dedupe)
                            externa (§3): OCEL 2.0 · Celonis variantes · agentevals · ARISE · Sprout.ai · SUSEP 496/2026 · GDPR Art. 89
GATES ................  por bloco (§4). Todos com mutação. Dois tenants em A, B, C, D
O ELO ................  a afirmação-título é "o trabalho humano vira dataset". O elo é: (i) o sinistro É detectado (A abre
                            a sombra) → (ii) o humano AGE e o gesto vira evento (B) → (iii) os eventos VIRAM variante (C).
                            Cada seta tem gate próprio com fixture de ponta a ponta (E gate ⑧)
FAIXA DE RELÓGIO .....  🔴 6–10h
```

---

## 3. 🌐 O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS — §7.3, reaberto em 03/09/2026

O research-pack tinha referências de mercado (Guidewire, Shift, Sprout, Snapsheet) e regulatórias.
📊 Reabertas: **todas vivas**; Snapsheet AI diz *"Available 2026"* (é lançamento, não base
instalada); Shift Claims é de 16/09/2025; **LGPD no planalto.gov.br não abriu (ECONNRESET 2×)** e a
ANPD **não tem guia final** de anonimização (só estudos de 2023 e consulta encerrada em 02/2024). As
quatro primeiras abaixo não estavam no pack e respondem ao que ele não respondia: **como se registra
e como se agrupa** trabalho humano.

### ① OCEL 2.0 — o registro é evento × objetos qualificados, não uma lista com case_id
```
URL ................. https://www.ocel-standard.org/  (03/09/2026)
o que ela faz ....... um evento liga-se a VÁRIOS objetos com relação qualificada (papel do objeto no evento);
                      objeto tem atributos que mudam no tempo. Evita o achatamento num só case_id, que
                      replica evento entre casos (convergência) ou desordena instâncias (divergência)
MODELAMOS ........... BLOCO B: cada work_event da sombra carrega em payload_redacted os objetos {ator: papel,
                      documento: tipo, seguradora: slug, espera: kind} — o evento aparece UMA vez, com
                      qualificadores. É o que permite "quais tipos de documento atravessaram quais sinistros"
REJEITAMOS .......... formato OCEL e biblioteca de process mining como runtime (CLAUDE.md §5). O Work OS É o log;
                      copiamos a forma. E o objeto humano é PAPEL (atendente), nunca identidade
COMO O JUIZ INSPECIONA abre a seção de relacionamentos qualificados · pega um evento real da sombra com 2+ objetos e
                      confere que existe UMA linha, com qualificadores no payload, não uma por objeto
```
### ② Celonis — variante é a sequência ordenada de atividades; frequência é prioridade, nunca autoridade
```
URL ................. https://www.celonis.com/blog/how-process-mining-modernizes-process-discovery  (03/09/2026)
o que ela faz ....... deriva o processo real do log (case, activity, timestamp) e chama VARIANTE cada sequência
                      distinta, ordenada por frequência; "if you ask three people how a process works, you'll
                      get five different answers"
MODELAMOS ........... BLOCO C: assinatura da variante = sequência ORDENADA de event_type da sombra; o sinal nasce de
                      (ramo × seguradora × variante) com N ≥ limiar declarado. A frequência ordena a fila de
                      curadoria; a curadoria (SPEC-052/053) decide
REJEITAMOS .......... "happy path = processo aprovado"; conformance checking (é a 091, adiada)
COMO O JUIZ INSPECIONA confere que a assinatura é ordenada e o timestamp vem do EVENTO · roda o controle: duas trajetórias
                      com as mesmas atividades em ordens diferentes caem em variantes DIFERENTES (CLAUDE.md §9.3)
```
### ③ LangChain agentevals — a trajetória humana tem a forma de uma tool call, para ser comparável depois
```
URL ................. https://github.com/langchain-ai/agentevals  (03/09/2026)
o que ela faz ....... avalia TRAJETÓRIAS (passos, não só saída) em quatro modos: strict (mesma ordem), unordered,
                      subset/superset, llm-as-judge; entrada = lista de passos com tool_calls
MODELAMOS ........... BLOCO B: cada gesto humano é {evento, argumentos-enum, resultado} — a forma de uma tool call —
                      para que a trajetória humana e uma futura trajetória de agente sejam comparáveis pela mesma
                      régua. Os quatro modos viram as quatro perguntas do gold corpus (P-093B-CORPUS)
REJEITAMOS .......... instalar agentevals/LangSmith; llm-as-judge como gate (C0 não julga)
COMO O JUIZ INSPECIONA confere que o evento tem campo de argumentos (sem ele "pediu documento" e "pediu BO" colidem) ·
                      aplica strict e unordered a duas trajetórias de fixture: se derem o mesmo, não há ordem no corpus
```
### ④ Shift Technology ARISE — cinco níveis, e o nosso degrau zero
```
URL ................. https://www.shift-technology.com/en-gb/resources/reports-and-insights/arise-a-standard-framework-for-ai-agent-autonomy-in-insurance  (03/09/2026 · publicada 10/06/2026)
o que ela faz ....... L1 Answers · L2 Recommends · L3 Initiates · L4 Solves (99%+) · L5 Exceeds; a fronteira é "grau de
                      envolvimento humano e complexidade do julgamento"
MODELAMOS ........... esta SPEC é C0 OBSERVE, abaixo de L1: zero decisão, zero efeito. Autonomy readiness (proposta §32)
                      NÃO entra: sem corpus não há o que medir, e score sem denominador vira autorização disfarçada
REJEITAMOS .......... generalizar L4 de vidros na Europa para sinistro aqui; readiness como autorização; qualquer
                      automação de cobertura, dano corporal, culpa, fraude, valor ou pagamento
COMO O JUIZ INSPECIONA procura na SPEC e no código qualquer caminho em que a sombra escreva em conversations, messages
                      ou envie algo → tem de dar zero
```
### ⑤ Sprout.ai — por que capturar o tácito ANTES é a SPEC inteira
```
URL ................. https://sprout.ai/resource/why-claims-ai-pilots-stall-before-production-and-how-to-escape-the-pilot-trap/  (03/09/2026 · 13/07/2026)
o que ela faz ....... pilotos de claims AI travam por dado fragmentado, integração, compliance, adoção — e por "decision
                      logic that lives in experienced adjusters' heads rather than documented workflows"
MODELAMOS ........... os cinco motivos viram cinco CONTADORES do digest (BLOCO C), cada um com denominador: sinistros com
                      documento faltante · com espera de seguradora > prazo · com nota da atendente · com retomada do
                      humano · encerrados sem desfecho conhecido
REJEITAMOS .......... inferir decisão sobre o sinistro; "sempre pedimos isso" como regra (vira evidência de variante)
COMO O JUIZ INSPECIONA roda a query dos cinco contadores: número sem denominador não é citável
```
### ⑥ SUSEP / CNSP 496/2026 — prazo sem vigência é bug futuro
```
URL ................. https://www.gov.br/susep/pt-br/central-de-conteudos/noticias/2026/agosto/nova-norma-do-cnsp-estabelece-regras-gerais-para-contratos-de-seguros-de-danos  (03/09/2026)
o que ela faz ....... 📊 30 dias para regular o sinistro com documentos essenciais (120 no Capítulo III); 30 para liquidar
                      após cobertura reconhecida; obrigatória em contratos formados ou renovados a partir de 05/01/2027;
                      planos anteriores adaptados até 04/01/2027
MODELAMOS ........... BLOCO C: módulo puro `prazos_regulatorios.py` com {valor, unidade, ramo, fonte, vigencia_de, vigencia_ate};
                      a espera "vencida" resolve o prazo pela DATA DO CONTRATO quando conhecida, e diz "regime não
                      determinado" quando não — nunca um `30` solto
REJEITAMOS .......... hardcode de 30; alerta ao segurado; interpretar aplicabilidade (fica com o humano)
COMO O JUIZ INSPECIONA confere os quatro números contra a notícia · `grep -n "\b30\b" prazos_regulatorios.py` sem vigência ao
                      lado reprova · controle: contrato 2026 e contrato 2027 resolvem prazos por caminhos diferentes
```
### ⑦ GDPR Art. 89(1) — uso secundário exige minimização e pseudonimização, com a chave separada
```
URL ................. https://eur-lex.europa.eu/eli/reg/2016/679/oj/eng  (03/09/2026)
o que ela faz ....... Art. 4(5) pseudonimização com informação adicional mantida SEPARADA; Art. 5(1)(c) minimização; Art. 9
                      categorias especiais (saúde); Art. 89(1) fins estatísticos exigem salvaguardas
MODELAMOS ........... a sombra NÃO guarda texto: só enums, contagens, tipos e timestamps (minimização por construção). A
                      chave de reidentificação é `conversation_id`, que vive em `conversations` com as próprias 4
                      policies — "mantida separadamente" é literal. O corpus continua dado pessoal: RLS + company_id +
                      filtro + dois tenants
REJEITAMOS .......... citar GDPR como base legal brasileira (a LGPD não abriu hoje — P-093B-LGPD); pseudonimização como
                      se fosse anonimização
COMO O JUIZ INSPECIONA pega uma linha real de work_events da sombra e procura os sete campos proibidos e qualquer texto do
                      segurado → qualquer um presente reprova · confere o teste de dois tenants sobre work_events
```

**O que o estado da arte faz que nós não fazemos** (💭 nota do pesquisador): task mining fora do
nosso canal (portal, e-mail, telefone) **85** · outcome oficial da seguradora **75** (InfoCap
`/sinistro` deu 403 em 14/07, por medir) · conformance checking **70** · etiquetagem de documento **55**
· replay com juiz **45** · severidade/fraude **35** · straight-through **25** · fraude entre
seguradoras **10** (hard blocker permanente).

---

# BLOCO 0 · REMEDIR, antes da primeira linha

```sql
-- ① o handoff está LIGADO? (a tool só existe com tools_config.human_handoff.enabled)
SELECT slug, agent_role, is_active, tools_config->'human_handoff' FROM agents ORDER BY 1;   -- ⛔ não imprima nomes de pessoa; slug é ok
-- ② os zeros de hoje
SELECT count(*) FILTER (WHERE status='HUMAN_REQUESTED') hr, count(*) FILTER (WHERE human_handoff_reason IS NOT NULL) hhr,
       count(*) FILTER (WHERE claimed_by IS NOT NULL) claimed, count(*) FILTER (WHERE resolvido_em IS NOT NULL) resolvidos FROM conversations;
SELECT count(*) FROM work_waits; SELECT count(*) FROM notas_da_atendente;
SELECT actor_type, count(*) FROM work_events GROUP BY 1;
-- ③ o volume (teto) e a palavra exata
SELECT date_trunc('month', coalesce(wa_timestamp, created_at)) m, count(*) linhas, count(DISTINCT session_id) sessoes
  FROM attendance_transcripts WHERE text ~* '\msinistro\M' GROUP BY 1 ORDER BY 1 DESC LIMIT 6;
-- ④ o trilho
SELECT source_type, domain, count(*) FROM intelligence_signals GROUP BY 1,2;  SELECT count(*) FROM knowledge_candidates;
-- ⑤ o vocabulário de actor_type (CHECK) e as policies de work_runs/work_events
SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid='work_events'::regclass AND contype='c';
SELECT tablename, policyname, cmd FROM pg_policies WHERE tablename IN ('work_runs','work_events','work_waits');
```
```bash
grep -n "servico = servico or" backend/app/services/atlas/templater.py       # espere :1725
grep -rn "notas_da_atendente" app components | wc -l                          # espere 0
grep -n "def registrar_ato_do_agente\|agente=\"" backend/app/services/dispatch_router.py | head   # como se escreve work_event hoje
```
**Gate do BLOCO 0:** ① escrito no relatório com o valor de `human_handoff.enabled` por corretora (se
desligado em todas, a sombra ainda captura pelo detector do BLOCO A — mas o rastro humano do BLOCO B
depende de alguém assumir; escreva isso) · ② os zeros continuam zeros · ③ o volume mensal · ⑤ o CHECK de
`actor_type` contém `user` (é o ator da atendente) — se não, PARE e registre: a sombra não pode inventar
ator.

---

# BLOCO A · O sinistro é detectado e a sombra abre — sem desviar um turno

## O conserto
Um módulo novo `backend/app/services/claims_shadow.py` (💭 nome) com uma função pura
`detectar_sinistro(texto_normalizado, ficha) -> (bool, confianca, motivo_enum)` e uma função de I/O
`abrir_sombra(company_id, conversation_id, ...) -> work_run_id`:

```
detecção      (a) infer_ramo_servico(...) devolve servico == 'sinistro'                → confianca ALTA
              (b) regex estrito \m(sinistro|colis[ãa]o|batida|roub(o|aram)|furt(o|aram)|acidente)\M
                  no texto do SEGURADO (nunca da URA)                                  → confianca MEDIA
              ⛔ 'terceiro' sozinho NÃO abre (§1.5: casa fora de contexto)
abertura      WorkRunService.criar(workflow_key='claims.shadow', outcome_type='claims.shadow',
              source_type='chat', source_id=conversation_id, conversation_id=…,
              📊 o CHECK de work_runs.source_type é {chat, routine, auxiliary, portal, api, admin, system,
              retry, child_run} — 'conversation' NÃO existe; 'chat' é o canal do segurado. thread_id é
              CHECK derivado ('work:'+company_id+':'+id): o RPC o gera, não se passa
              idempotency_key=f'claims.shadow:{conversation_id}', risk_level='low',
              input_payload={'confianca':…, 'motivo':…, 'ramo':…, 'seguradora_slug':…})
              — UMA sombra por conversa (idempotente); reabrir não duplica
gancho        no ponto do webhook onde a mensagem do segurado já está normalizada e a ficha existe
              (o executor localiza: perto de onde infer_ramo_servico é chamado ou onde a ficha grava,
              attendance_ficha.py:328). 🔴 Em try/except que ENGOLE erro e loga: a sombra NUNCA
              derruba o atendimento
```
⛔ **`infer_ramo_servico` não muda.** O defeito da §1.2 ("guincho vence sinistro") é conduta do
atendimento e muda o que o segurado recebe — está em F-093B-01 para o Founder, não aqui.
🔴 **Zero texto:** `input_payload` só tem enums e slugs. O `motivo_enum` é qual regra casou, não a frase.

## O gate
```
① fixture "bati o carro e preciso de guincho" → abre sombra (regex, MEDIA) sem tocar em ramo/servico do atendimento
② fixture "quero falar com o terceiro andar" → NÃO abre
③ duas mensagens da mesma conversa → UMA sombra (idempotency_key)
④ 🔴 DOIS TENANTS: a sombra da corretora A não aparece no SELECT filtrado da B
⑤ 🔴 LINHA DE CONTROLE: exceção forçada dentro de abrir_sombra → o webhook segue e loga; nenhuma exceção sobe
⑥ input_payload não contém nenhum campo de texto do segurado (o guarda lista as chaves)
```
**Mutação:** troque o regex para casar `terceiro` → ② vermelho. Remova o try/except → ⑤ vermelho.

---

# BLOCO B · O ledger: cada gesto vira evento, no vocabulário único

## O vocabulário — congelado em §5, lido por Python e por Next do MESMO arquivo
`backend/app/services/claims_shadow_vocab.json` (💭 caminho; o Next o importa por caminho relativo ou
uma cópia gerada com teste de igualdade — o executor escolhe e o guarda ⑤ prova que os dois lados
leem o mesmo conteúdo).

## Os escritores (todos com `actor_type` do CHECK existente; `payload_redacted` só enums)
| gesto | onde já acontece | evento | ator |
|---|---|---|---|
| robô entrega ao humano | `human_handoff.py:611` | `claims.handoff_pedido` {motivo_enum} | `agent` |
| atendente assume / devolve / encerra | `app/api/dashboard/conversas/[id]/route.ts` (claimed_by, status) | `claims.humano_assumiu` · `claims.humano_devolveu` · `claims.encerrado` {desfecho_enum: desconhecido por padrão} | `user` |
| atendente envia mensagem ao segurado | `webhook.py:1386` (sinal humano) e a rota do painel | `claims.humano_respondeu` {canal} — **sem o texto** | `user` |
| atendente anota `#nota` | `a_nota_da_atendente.py:207` e `route.ts:295` | `claims.nota_registrada` {tem_numero: bool} — **sem o texto** | `user` |
| segurado manda documento/foto | `webhook.py:222` (mídia) · `attendance_media.py:242 _detect_document_type` | `claims.documento_recebido` {tipo_documento_enum} | `provider` |
| espera aberta/satisfeita | `o_fim_do_atendimento.py:251` e watchdog | `claims.espera_aberta`/`_satisfeita` {kind} — e a `work_waits` ganha o `work_run_id` da sombra | `system` |
| mensagem da seguradora (URA) chega ao caso | `attendance_capture`/`dispatch_router` quando há sombra | `claims.seguradora_respondeu` {canal} | `provider` |
🔴 Todo escritor: `SELECT id FROM work_runs WHERE conversation_id=? AND workflow_key='claims.shadow' AND company_id=?`
(índice existe) → se não há sombra, **não escreve** (nada de sombra retroativa nesta SPEC).
🔴 `work_events.message_human` vem de template por evento; `payload_redacted` passa por `contem_pii()`
do `redaction_service` antes do INSERT — se acusar, o evento grava com `payload_redacted={}` e um
`severity='warning'` (a sombra prefere perder detalhe a vazar).

## O gate
```
① cada linha da tabela acima tem um teste de fixture que produz o evento com o event_type do vocabulário
② 🔴 payload_redacted de cada evento: só chaves do vocabulário; nenhum valor com mais de 64 chars; contem_pii() falso
③ conversa SEM sombra → o gesto NÃO escreve evento (controle)
④ 🔴 DOIS TENANTS em work_events: evento da A não aparece filtrado pela B
⑤ 🔴 Python e Next leem o MESMO vocabulário (hash igual dos dois lados; teste em ambos os stacks)
⑥ o evento aparece UMA vez com seus qualificadores (referência ①): dois objetos no mesmo gesto = uma linha
```
**Mutação:** faça um escritor gravar `texto` no payload → ② vermelho. Altere um event_type só no Next → ⑤ vermelho.

---

# BLOCO C · O digest: variantes, contadores, prazos — e o trabalhador aparece na Central

## O conserto
Workflow `intelligence.claims_shadow_digest` (registrado com `@registrar_workflow` em
`backend/app/services/intelligence/workflows.py`, agendado 1×/dia no `tick.py` como os outros):
1. por `company_id`, lê sombras e eventos dos últimos 90 dias;
2. **variante** = sequência ordenada de `event_type` (referência ②); agrupa por `(ramo, seguradora_slug, variante)`;
3. escreve `intelligence_signals` via `signal_service` com `source_type='claims_shadow'`, `domain='sinistro'`,
   `signal_type='process_variant'`, `dedupe_key=(company, ramo, seguradora, hash(variante))`, `summary_redacted`
   por template ("23 sinistros auto × porto seguiram 5 passos: …event_types…"), `trust_tier` baixo,
   `subject_type='claims_shadow'`; N ≥ **3** para escrever (💭 limiar inicial; sobe com corpus);
4. os **cinco contadores** da referência ⑤ como um sinal `signal_type='claims_shadow_resumo'` por corretora,
   cada um com denominador;
5. `prazos_regulatorios.py` (puro): tabela de prazos com vigência (referência ⑥); `espera_vencida(kind, aberta_em,
   data_contrato|None)` → `True|False|'regime_nao_determinado'`. Usado no contador "espera de seguradora > prazo".
6. `AGENT_TASKS` (heartbeat.py, SPEC-088) ganha o trabalhador `sombra_sinistros`: grupo `aprende_avisa`, eixo
   `work_runs` com `workflow_keys=['intelligence.claims_shadow_digest']`, `fonte_de_producao` =
   `intelligence_signals.created_at WHERE source_type='claims_shadow'`, cadência 86400. **A Central o mostra sem uma
   linha de frontend.** ⚠️ Sem sinistro no corpus ele sairá 🟡 PULSA SEM PRODUZIR — e é a verdade.
⛔ **Não escreve `knowledge_candidates`** nesta SPEC (📊 o adapter nunca escreveu em produção; ligar a
sombra a um caminho nunca exercido é dois desconhecidos de uma vez — P-093B-CANDIDATO).

## O gate
```
① fixture com 5 sombras: 3 com a sequência X e 2 com Y → 1 sinal process_variant (N=3), Y não escreve
② 🔴 CONTROLE (referência ②): X e a permutação de X caem em variantes DIFERENTES
③ dedupe: rodar o digest duas vezes não duplica sinal (dedupe_key)
④ os 5 contadores têm denominador no summary_redacted
⑤ prazos: `grep -n "\b30\b\|\b120\b" prazos_regulatorios.py` só em linhas com vigencia_de; contrato 2026 vs 2027 → caminhos diferentes;
   sem data de contrato → 'regime_nao_determinado'
⑥ 🔴 DOIS TENANTS: sinais da A não misturam sombras da B (agrupamento por company_id)
⑦ AGENT_TASKS tem `sombra_sinistros` com fonte e cadência; o guarda da SPEC-088 (test_a_central_diz_a_verdade.py) continua verde
   (a cobertura do BLOCO A ② dela exige que o workflow_key novo tenha card — este é o card)
```
**Mutação:** limiar N=3 → 1 → ① escreve Y também (vermelho). Ordenação removida da assinatura → ② vermelho.

---

# BLOCO D · O resumo admin — read-only, sem PII, para o Founder ver funcionando

`GET /api/admin/spec034/claims-shadow` (mesmo router, `require_master_admin`, cache 60s): por corretora
(contagem, não id exposto além do agregado que a Central já faz): sombras abertas/encerradas (30d),
eventos por tipo, esperas por kind com média de dias, top variantes com N, os cinco contadores.
Nenhuma chave fora do contrato; nenhum texto.
**Gate:** ① contrato fechado (lista de chaves) ② `require_master_admin` na assinatura (bloco [9] do
guarda da 088 cobre o padrão) ③ com banco vazio devolve zeros SEM erro ④ nenhum campo textual.
💭 Frontend: **nenhum** nesta SPEC. A Central mostra o trabalhador; o resumo é JSON para o admin.
F-093B-02: se o Founder quiser a tela, é a próxima peça.

---

# BLOCO E · O guarda — `backend/tests/test_o_sinistro_deixa_rastro.py`

No formato de `test_a_central_diz_a_verdade.py`: blocos numerados, `certo()`, linha de controle em cada.
Cobre A①–⑥, B①–⑥, C①–⑦, D①–④ e o **gate do ELO ⑧**: uma fixture de ponta a ponta — mensagem
de sinistro → sombra aberta → handoff → humano assume → documento → nota → espera → encerra → digest
→ 1 sinal com a variante de 7 passos e os contadores com denominador 1. **Sem esse teste a SPEC prova
as pontas e não o elo (§0.3).**
**Mutações obrigatórias (3):** payload com texto → vermelho · permutação da variante igual → vermelho ·
sombra da A visível pela B → vermelho.

---

## 4. Os arquivos, por caminho (o mapa da SUPERFÍCIE 2)

```
NOVOS     backend/app/services/claims_shadow.py · backend/app/services/claims_shadow_vocab.json ·
          backend/app/services/prazos_regulatorios.py · backend/tests/test_o_sinistro_deixa_rastro.py
TOCADOS   backend/app/api/webhook.py (gancho da detecção + evento de documento + evento humano_respondeu)
          backend/app/agents/tools/human_handoff.py (:611 evento handoff_pedido)
          backend/app/services/a_nota_da_atendente.py (:207 evento nota_registrada)
          backend/app/services/o_fim_do_atendimento.py (espera ganha work_run_id da sombra; eventos de espera)
          backend/app/services/intelligence/workflows.py (+1 workflow) · backend/app/services/intelligence/tick.py (+1 agendamento)
          backend/app/core/heartbeat.py (+1 trabalhador) · backend/app/api/admin_spec034.py (+1 rota)
          app/api/dashboard/conversas/[id]/route.ts (eventos humano_assumiu/devolveu/encerrado/nota/respondeu)
```

## 5. O VOCABULÁRIO — congelado para os builders trabalharem em paralelo
```json
{ "versao": 1,
  "eventos": {
    "claims.sombra_aberta":        {"ator": "system",   "payload": ["confianca", "motivo", "ramo", "seguradora_slug"]},
    "claims.handoff_pedido":       {"ator": "agent",    "payload": ["motivo_enum"]},
    "claims.humano_assumiu":       {"ator": "user",     "payload": ["origem"]},
    "claims.humano_devolveu":      {"ator": "user",     "payload": ["origem"]},
    "claims.humano_respondeu":     {"ator": "user",     "payload": ["canal"]},
    "claims.nota_registrada":      {"ator": "user",     "payload": ["origem", "tem_numero"]},
    "claims.documento_recebido":   {"ator": "provider", "payload": ["tipo_documento"]},
    "claims.seguradora_respondeu": {"ator": "provider", "payload": ["canal"]},
    "claims.espera_aberta":        {"ator": "system",   "payload": ["kind"]},
    "claims.espera_satisfeita":    {"ator": "system",   "payload": ["kind", "dias"]},
    "claims.encerrado":            {"ator": "user",     "payload": ["desfecho"]}
  },
  "enums": {
    "confianca": ["alta", "media"], "motivo": ["servico_sinistro", "regex_segurado"],
    "origem": ["dashboard", "whatsapp"], "canal": ["whatsapp", "dashboard", "ura"],
    "tipo_documento": ["boletim_ocorrencia", "cnh", "crlv", "foto_dano", "orcamento", "laudo", "outro", "desconhecido"],
    "kind": ["esperando_cliente", "esperando_seguradora", "esperando_humano"],
    "desfecho": ["desconhecido", "aberto_na_seguradora", "negado", "pago", "desistencia", "handoff_externo"]
  } }
```
Nenhuma chave de payload fora destas listas. `dias` é inteiro. Nada de texto.

---

## 6. 🔴 O QUE SAIU DA PROPOSTA — e o gatilho de cada peça

📊 3.075 linhas · 6 referências no pack. Saiu quase tudo que é C1+, porque C0 é o que dá para provar hoje.

| peça da proposta | 📊 medido em 03/09 | volta quando |
|---|---|---|
| Claim Shadow Profile como tabela própria (§4) | não existe objeto caso; o Work OS já é log de eventos (§1.9) | ⛔ nunca como tabela nova: o Work Run É o perfil |
| FNOL/intake estruturado, safety first (§8) | muda a conduta do robô | o Founder liberar C1 depois do piloto |
| Dossiê de handoff enriquecido (§9), C1 output (§30) | `human_handoff.py:288` já monta dossiê; 0 handoffs | 30 sombras com eventos humanos (para saber o que falta no dossiê) |
| Document intelligence (§12) | `_detect_document_type` existe; 24.386 mídias sem caso | a sombra ter 100 documentos etiquetados |
| Policy context / InfoCap sinistro (§13) | InfoCap `/sinistro` 403 em 14/07 | 🧑 acesso liberado pela InfoCap |
| Autonomy Readiness Score (§32) | sem corpus, score é autorização disfarçada (ref. ④) | 100 sombras encerradas com desfecho conhecido |
| Global claims learning, cross-tenant (§23–24) | 2 corretoras; dado pessoal pseudonimizado | ⛔ nunca sem decisão do Founder e base legal escrita (P-093B-LGPD) |
| Human Action Ledger fora do nosso canal (portal, e-mail) | task mining é o maior buraco (ref. lista, 85) | conector de portal com evento (SPEC-101) |
| Dreams (§0.6) | congelado para a 106 pela própria proposta | 106 |

Nada foi julgado ruim. Foi julgado C1+, e a 093-B é C0.

## 7. ⛔ POR QUE ZERO MIGRATION
A sombra é um `workflow_key` em `work_runs`; o ledger é `work_events` (CHECK de `actor_type` já tem
`user`, `agent`, `provider`, `system`); as esperas são `work_waits`; os sinais são `intelligence_signals`.
As quatro tabelas existem, têm `company_id` e índices. **Criar tabela seria motor paralelo** (CLAUDE.md §5).
⚠️ REVERSIBILIDADE 2 mesmo assim: desfazer o código deixa as linhas — o ROLLBACK escrito é
`DELETE FROM work_events WHERE work_run_id IN (SELECT id FROM work_runs WHERE workflow_key='claims.shadow')`,
depois `DELETE FROM work_runs WHERE workflow_key='claims.shadow'`, depois os sinais `source_type='claims_shadow'` —
só por decisão do Founder, nunca automático.

## 8. O que fica pendente
```
P-093B-LGPD      🔴 a base legal brasileira não foi lida hoje (planalto.gov.br ECONNRESET; ANPD sem guia final). A SPEC cita a
                 FORMA (GDPR Art. 89) e minimiza por construção. 🧑 Antes de qualquer uso cross-tenant ou global, a leitura
                 da LGPD art. 5º, 7º, 11 e 12 com jurista.
P-093B-CLASSIF   📊 templater.py:1725 `servico or "sinistro"`: assistência vence sinistro. Muda conduta → F-093B-01.
P-093B-CANDIDATO knowledge_candidates = 0 em produção; o adapter nunca escreveu. A sombra escreve só sinais até o adapter ser exercido.
P-093B-SAUDE     redaction_service sem padrão de saúde (CID, laudo). A sombra não guarda texto, então não vaza; o serviço
                 canônico continua incompleto para quem guarda. ~30 min.
P-093B-RLS       12 tabelas de aprendizagem com RLS ligado e 0 policies (herda P-090-01). A sombra usa work_runs/work_events,
                 que TÊM policies. intelligence_signals não tem.
P-093B-CORPUS    o gold corpus (4 perguntas da ref. ③) só existe com 20+ trajetórias humanas reais. Medir em 14 dias de piloto.
P-093B-TERCEIRO  2.187 sessões históricas com palavras de sinistro NÃO viram sombra (sem retroativo nesta SPEC). Decidir se
                 vale um backfill C0 sobre attendance_transcripts com o mesmo detector — 🧑 é dado antigo de segurado.
P-093B-TELA      a Regina/Saionara não veem a sombra; a nota `#nota` continua sem tela que a exiba (0 leitores).
```

## 9. 🧑 A CAIXA DO FOUNDER
```
F-093B-01  "bati o carro, preciso de guincho" é classificado como GUINCHO, não sinistro (templater.py:1725). Consertar muda a
           conduta do robô ANTES do piloto. Recomendo consertar DEPOIS da primeira semana, com os casos reais na mão.
F-093B-02  Sem tela nesta SPEC: a Central mostra o trabalhador e o admin tem o JSON. Se quiser ver os casos da sombra numa
           tela de corretora, é a próxima peça (~2h).
F-093B-03  Nível CRÍTICO por RISCO 6 (dado de sinistro, todo atendimento, linhas que sobram). Red team e auditoria externa
           entram. Custo 💭 +1,5h. Se preferir PADRÃO, diga — mas é aqui que eu não rebaixaria.
F-093B-04  Backfill das 2.187 sessões históricas: dado antigo de segurado virando corpus. Não faço sem sua palavra.
F-093B-05  📊 `tools_config.human_handoff.enabled` está false ou ausente nos 8 agentes: o robô NUNCA pede handoff. No piloto,
           quem "entrega ao humano" é a atendente clicando Assumir. Ligar a tool muda a conduta do robô — decisão sua, para
           depois da primeira semana.
```

## 10. A ordem de execução
```
BLOCO 0 → desenhista escreve E (fixtures e gates) → {A+B py} ‖ {B next} ‖ {C} → integração → D → E fecha → verificador →
painel de 4 lentes (verdade · adversarial/PII/tenant · regressão do atendimento · produto+guarda) → red team → conserto →
juiz de confirmação → auditoria externa
```
🔴 A regressão do atendimento é a lente que mais importa: **a sombra não pode mudar um turno.** A lente roda
`test_a_maquina_de_lavar_vai_ate_o_fim.py` e `test_golden_do_eletricista.py` (referências internas §7.1) antes e depois.

💭 **6–10h.**
