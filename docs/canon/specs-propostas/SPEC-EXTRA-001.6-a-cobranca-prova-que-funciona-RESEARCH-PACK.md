# SPEC-EXTRA-001.6 — RESEARCH PACK
## A cobrança prova que funciona · evidência para a conversão

**Versão:** 1.0 · **Data:** 13/09/2026. **Natureza:** evidência para conversão. **Não é relatório de execução.**
**Revisão medida:** `a0bb5fef440eba394a9275671b1143f5025807ef` (worktree `AutoBrokers-FIX`, 0 atrás / 0 à frente de `origin/main`).
**Banco consultado (read-only, só contagens e strings de sistema):** projeto `dcajcvlzcjbmyapmklil`.
**Método:** todo `arquivo:linha` foi **reaberto nesta revisão**; as divergências com o diagnóstico estão na §2.1. Nenhuma mensagem foi enviada, nenhum portal foi acessado, nenhuma migration foi aplicada, nenhum código de produto foi alterado. Dois scripts locais de medição foram rodados (§3), ambos read-only.

⛔ **Nenhum CPF, CNPJ, telefone, nome de segurado, placa, e-mail ou credencial aparece neste documento.** Os dois números do Founder aparecem só como `TESTE-A` e `TESTE-B`.

---

## 0. Legenda e precedência

- **📊 MEDIDO** — tem comando/consulta e data. Citável como fato.
- **💭 ILUSTRATIVO** — exemplo, hipótese ou estimativa. **Nunca citável como fato.**
- **OBSERVADO NO CÓDIGO** — existe na revisão lida; ainda não é prova de comportamento em execução.
- **DESCONHECIDO** — §5.

Ordem de autoridade: `CLAUDE.md` → `PROTOCOLO-AUTOBROKERS-AAA.md` → decisões do Founder (D-PILOTO-*, D-E001-*) → o diagnóstico de 12–13/09 → este pacote. **Onde este pacote diverge do diagnóstico, ele traz o comando; o comando vence.**

---

## 1. A cadeia de evidência, do ledger vazio à mensagem picotada

### 1.1 A máquina da EXTRA-001 nunca foi ligada

```sql
-- 📊 13/09/2026
select count(*) from public.billing_sent_log;                     --> 0
select count(*) from public.billing_sent_log where send_mode='real'; --> 0
select count(*) from public.routines where (config->>'kind')='billing_collection'; --> 1
```

E a rotina, hoje:

```sql
select is_active, next_run_at::date, config->>'send_mode',
       length(trim(config->>'team_number'))   as team_len,
       length(trim(config->>'attendant_name')) as nome_len,
       config->>'confirmacao_cliente'
  from public.routines where (config->>'kind')='billing_collection';
-- 📊 false | 2026-09-14 | test | 0 | 0 | false   (6 portais em portal_keys)
```

**Consequência para a SPEC:** o ledger, a reserva atômica e os estados por componente da EXTRA-001 estão **implantados e não exercitados**. Não há backfill a fazer na migration do B1, e o `test` continua sendo o CONTROLE — o que muda nele está escrito assertiva por assertiva.

### 1.2 O governador contou 7; o canal recebeu 28

```sql
select date_trunc('day',created_at)::date as dia, kind, count(*)
  from public.platform_sends where created_at >= '2026-09-09' group by 1,2;
-- 📊 2026-09-10 | billing | 7        2026-09-11 | billing | 7
```

E o motor, rodado localmente sobre as funções de produto (§3.1):

```
📊 13/09 · texto ao cliente      331 ch → 2 balões  ·  com bloco_unico → 1
📊 13/09 · nota interna          322 ch → 2 balões  ·  com bloco_unico → 1
📊 13/09 · mensagem de teste     517 ch → 3 balões
```

**A conta que fecha:** 7 parcelas × (3 balões + 1 PDF) = **28 mensagens/dia**, contra **7** linhas em `platform_sends`. Em `equipe` seriam 7 × (2 da nota + 2 do texto + 1 PDF) = **35**; com `bloco_unico`, **21**.

**O ELO (protocolo §0.3):** A medido · B medido (`billing_collection.py:1153` e `platform_outbound.py:1478-1479` chamam `send_message` sem `bloco_unico`) · **B chega em A** — na mesma execução, os dois textos com `bloco_unico=True` deram 1 balão cada.

### 1.3 O motivo do portal existe, e ninguém o lê

```sql
select portal_key, status, count(*) as n, max(finished_at)::date as ultimo,
       count(*) filter (where error is null)                  as sem_error,
       count(*) filter (where (evidence->>'message') is not null) as com_msg
  from public.portal_jobs where journey in ('cobranca_sweep','login_check') group by 1,2;
```

📊 13/09 — **`sem_error = n` em TODAS as linhas** (100% com `error IS NULL`) e **`com_msg = n` em todas**:

| portal | done | needs_human | failed | último |
|---|---:|---:|---:|---|
| allianz_corretor | 28 | **34** | — | done em **17/08** · needs_human em 11/09 (+3 `archived`) |
| hdi_corretor | 7 | — | 2 | 11/09 |
| mapfre_corretor | — | — | **2** | 11/09 (**nunca teve um `done`**) |
| tokiomarine_corretor | 5 | — | — | 11/09 |
| yelum_corretor | 6 | — | — | 11/09 |
| zurich_corretor | 1 | 2 | — | 11/09 |

As mensagens reais (strings de sistema, sem PII), 10–11/09:

| portal | `evidence.message` |
|---|---|
| mapfre_corretor (`failed`) | **"a MAPFRE recusou a credencial (autenticacao invalida)"** |
| allianz_corretor (`needs_human`) | **"tela pos-login Allianz nao reconhecida"** (38 caracteres — é o *fallback* de `allianz_corretor.py:704`, palavra por palavra) |
| zurich_corretor (`needs_human`) | "a Zurich devolveu http 200 com ZERO parcelas em 45/90 dias, duas vezes seguidas — o portal ja devolveu 200 vazio estando com inadimplente na carteira, entao NAO afirmo que ela esta em dia" |

🔴 **O achado que muda o tamanho do conserto da Mapfre:** a journey **já classifica certo**. O defeito é de UMA linha de relatório (`billing_collection.py:2331` lê `error`; `:2329`, a vizinha, lê `evidence.message`). A Zurich é o CONTROLE do produto: ela retém e diz por quê, e a mensagem dela chega porque passa pela linha `:2329`.

### 1.4 A sessão nunca vence e a saúde nunca muda

```sql
select portal_key, health, verified_at::date, (now()-verified_at) > interval '7 days'
  from public.portal_sessions order by verified_at desc;
-- 📊 8 linhas, TODAS health='ok':
--    yelum 11/09 · tokio 11/09 · hdi 11/09 · allianz 17/08(!) · zurich 14/08 · tokio 12/08 · hdi 12/08 · allianz 12/08

select distinct health, count(*) from public.portal_accounts group by 1;
-- 📊 unknown | 16     (uma única string distinta em 16 contas)

select count(*) from public.portal_jobs where available_at is not null;  --> 📊 0
select max(attempts) from public.portal_jobs;                            --> 📊 1
```

Os escritores, lidos hoje:
- `portal_worker/worker.py:271-304` — `_save_session_state` grava `verified_at` e `health='ok'` **só no sucesso**;
- `portal_worker/worker.py:240-263` — `_load_session_bundle` lê `storage_state_encrypted, health` e **nunca compara `verified_at` com o relógio**;
- `backend/app/api/portal.py:165` — `save_credential` grava `health='unknown'` a cada salvamento (o único outro escritor);
- `portal_worker/worker.py:1001` lê `available_at`; **nenhuma linha o escreve**;
- `portal_worker/worker.py:1017` incrementa `attempts` em `_tentar_claim`; nenhuma linha o **lê** para decidir.

### 1.5 A prova existe como imagem — e só como imagem

```sql
select split_part(name,'/',2), count(*) from storage.objects
 where bucket_id='portal-evidence' and name like '%desfecho%' group by 1;
-- 📊 00-desfecho-done.jpg 6 · 00-desfecho-needs-human.jpg 4 · 00-desfecho-failed.jpg 2   (12 prints)

select length(coalesce(evidence->>'body_text','')), length(coalesce(evidence->>'debug_dom',''))
  from public.portal_jobs
 where journey='cobranca_sweep' and status in ('failed','needs_human') and finished_at >= '2026-09-10';
-- 📊 0 e 0 nas SEIS linhas
```

🔴 **Este é o achado mais importante do pacote, e o diagnóstico não o tem.** O texto real das telas de portal **não está no banco**. A frase *"Acesso negado — Por favor, valide os dados introduzidos"* existe **só dentro de um JPG**. Duas consequências diretas:

1. o guarda G3 não pode ler o texto do banco: o corpus nasce da **leitura dos 12 prints** pelo executor, transcritos para `backend/tests/corpus/telas_reais_de_portal/`;
2. o BLOCO 4 ganha um pré-requisito que a SPEC da manhã não tinha: **gravar o TEXTO da tela**, redigido, e não só a foto. Sem isso, a próxima mudança de tela exige de novo que alguém abra uma imagem — e o investigador do laudo I6 foi o primeiro a abrir, **dois dias depois**.

Caminho dos prints: `_prova_do_desfecho` (`worker.py:411`) → `_materializar_provas` (`worker.py:428-461`) → `portal-evidence/{job_id}/{NN}-{motivo}.jpg`, com `motivo = f"desfecho-{result.status}"` (`worker.py:884`). `_redigir` (`worker.py:44-56`, via `portal_worker/redaction.py`) cobre **o envelope JSON**, nunca a imagem.

### 1.6 A PII está no relatório da execução

```sql
select count(*) from public.routine_runs r join public.routines t on t.id=r.routine_id
 where (t.config->>'kind')='billing_collection';                         -- 📊 49
select count(*) ... and r.output_full like '%CPF/CNPJ%';                 -- 📊 7
```

Escritor: `_format_report` (`billing_collection.py:1810-1894`), seção "Clientes encontrados" (`:1885-1891`) imprime `cpf_cnpj` e `whatsapp` **inteiros**; `routine_engine.py:362-367` grava a string em `routine_runs.output_full`, com um comentário que já reconhece o fato. O artifact, por contraste, é mascarado de propósito (`billing_collection.py:1918-1931`). 🔴 A SPEC alinha os dois **para baixo**, e mantém o número legível só na nota que vai à atendente (`_whatsapp_legivel`, `:1350`).

---

## 2. Os `arquivo:linha`, reabertos hoje

### 2.1 Divergências com o diagnóstico (corrigidas na proposta §12.1)

| diagnóstico §9.2 | hoje em `a0bb5fe` | o que está na linha citada |
|---|---|---|
| `billing_collection.py:1191` (o envio do modo teste) | **`:1153`** | `:1191` é `if dedup:` |
| `platform_outbound.py:1477` | **`:1478-1479`** | a chamada a `send_message` |
| `fila_de_cobranca:362-441` | def `:362`, **return `:424`** | |
| `ordenar_para_entrega:334-348` | def `:334`, return `:345-350` | |
| `normalize_billing_config:502` | **`:500`** | `attendant_name` com default `"nossa equipe"` |
| laço `:1542` | **`:1544`** | `for indice, item in enumerate(ordenar_para_entrega(fila))` |
| reserva `:1583` | **`:1589-1590`** | `_reservar_obrigacao` |
| `allianz_corretor.py:3782-3796` | **`:3786`** | `_diagnosticar_sessao_na_pagina` |

### 2.2 Conferidos e **exatos**

| coordenada | o que está lá |
|---|---|
| `billing_collection.py:2329` | `needs_human` lê `(job.get("evidence") or {}).get("message")` |
| `billing_collection.py:2331` | `failed`/`timeout` lê `job.get('error')` — 📊 nulo em 100% dos jobs |
| `billing_collection.py:1059-1065` | `dedup_de_envio_ativa`: `test` só deduplica com `BILLING_DEDUP_TEST_ENABLED` |
| `billing_collection.py:471-476` | retenção quando `equipe` sem `team_number` |
| `billing_collection.py:1253-1262` | `_registrar_no_governador` — **1 linha por parcela** |
| `billing_collection.py:676-734` | `_enqueue_job` — `"journey": "cobranca_sweep"` fixo (`:680`) |
| `allianz_corretor.py:659-667` | `_FAIL`, 7 frases; **nenhuma** é "acesso negado" ou "valide os dados" |
| `allianz_corretor.py:693-705` | `interpret_login`; `:704` é o fallback "tela pos-login Allianz nao reconhecida" |
| `allianz_corretor.py:3755-3759` | `cobranca_sweep` → `login_check` → `return login` |
| `allianz_corretor.py:24-26` | `_norm`: NFKD → ascii → lower → colapsa espaços |
| `worker.py:812` | `evidence["session_reused"] = True` **no instante da injeção** |
| `worker.py:884` | `_prova_do_desfecho(page, evidence, f"desfecho-{result.status}")` |
| `worker.py:944` | `"error": None,  # limpa nota de requeue de tentativa anterior` |
| `worker.py:1001` / `:1017` | `available_at` lido / `attempts` incrementado |
| `app/api/portal.py:141` | `GET /portal/credentials` **já devolve `health`** |
| `app/api/portal.py:165` | `save_credential` grava `health='unknown'` |
| `app/tasks/vigia_do_portal.py:306` | `.eq("portal_key","vidros_lanternas")` — o vigia só olha vidros |
| `whatsapp_service.py:131-160` | `send_message(..., bloco_unico=False)`; `bloco_unico` → `_fatiar_documento` |
| `whatsapp/balloons.py:17-19` | `TARGET_LEN=300 · HARD_LEN=500 · MAX_BALLOONS=4` |
| `journeys/__init__.py:205-226` | `_cobranca()` registra `login_check` **e** `cobranca_sweep` nos 6 portais |
| `app/dashboard/personalizacao/conectores/portais/page.tsx:18` | o tipo declara `health` — e **nada o renderiza** |
| `app/admin/central-agentes/page.tsx:640` | a página lê `/api/admin/spec034/agents-status` (servida por `backend/app/api/admin_spec034.py:56`) |

### 2.3 Quem chama a porta — a razão de `bloco_unico` ser decidido por `kind`

```bash
grep -rn "send_to_client_guarded(" backend/app --include=*.py | grep -v "def "
# 📊 13/09:
#   billing_collection.py:1669   (nota interna)
#   billing_collection.py:1683   (texto + documento)
#   intelligence/delivery_executor.py:283
#   platform_outbound.py:1635    (o REPLAY da fila)
#   saudacao_do_religamento.py:541   ← fala com o SEGURADO, humanizada
#   tasks/dispatch_followup.py:282   ← fala com o SEGURADO, humanizada
```

🔴 Ligar `bloco_unico` incondicionalmente em `_entregar_agora` transformaria a saudação de religamento e o follow-up em blocos únicos — o oposto do que `whatsapp_service.py:139-152` documenta ("os balões existem por um motivo bom"). E um **parâmetro novo** não sobrevive ao replay: `P-E001-FILA-SEM-AUTORIZACAO-DE-AUXILIAR` registra que a entrada da fila carrega `integration_id`, `documento`, `ledger_ref` e `canario` — e nada mais. O `kind` **já viaja**. Por isso a decisão é uma tabela de `kind`.

---

## 3. Os dois scripts de medição rodados hoje (read-only)

### 3.1 Os balões, com o motor do produto

```bash
cd backend && PYTHONIOENCODING=utf-8 python -c "
import sys; sys.path.insert(0,'.')
from app.services.billing_collection import (build_customer_message, _format_test_message,
        normalize_billing_config, _nota_interna_para_a_equipe)
from app.services.whatsapp.balloons import split_whatsapp_balloons
from app.services.whatsapp_service import _fatiar_documento
item = {...}   # 💭 valores ilustrativos, sem PII
cfg  = normalize_billing_config({'kind':'billing_collection','send_mode':'equipe',
                                 'attendant_name':'', 'brokerage_name':'Resulta',
                                 'team_number':'<TESTE-B>'})
txt  = build_customer_message(item, cfg['message_template'], cfg)
print(len(txt), len(split_whatsapp_balloons(txt)), len(_fatiar_documento(txt)))
..."
```

📊 Saída, 13/09: `331 2 1` (texto) · `322 2 1` (nota) · `517 3` (teste) · e o texto renderizado contém literalmente **"Aqui é a nossa equipe, da Resulta, tudo bem?"** com `attendant_name` vazio.

⚠️ **Armadilha do ambiente:** `from app.services.whatsapp.balloons import ...` puxa o `__init__` do pacote e leva **mais de 100 s** para carregar (langchain). Para medir só o divisor, carregar o módulo por caminho:
`importlib.util.spec_from_file_location('balloons','app/services/whatsapp/balloons.py')` — 📊 <2 s.

### 3.2 As consultas do banco

Todas as da §1, executadas por MCP Supabase `execute_sql` no projeto `dcajcvlzcjbmyapmklil`, **só contagens, datas e strings de sistema**. Nenhum conteúdo de mensagem, nenhum documento de segurado.

---

## 4. Roteiro de remedição do executor (BLOCO 0)

```bash
git fetch origin && git rev-list --count HEAD..origin/main && git rev-list --count origin/main..HEAD
git rev-parse HEAD && git status --short

rg -n "bloco_unico" backend/app backend/tests
rg -n "BILLING_DEDUP_TEST_ENABLED" .                      # 🔴 o valor ANTIGO; sobrevivente = defeito
rg -n "send_to_client_guarded\(" backend/app --glob '!*test*'
rg -n "evidence.*message|job.get\('error'\)" backend/app/services/billing_collection.py
rg -n "_FAIL|interpret_login|def _norm" backend/portal_worker/journeys/
rg -n "verified_at|available_at|attempts|session_reused|health" backend/portal_worker/worker.py
rg -n "health" app/dashboard/personalizacao/conectores/portais/page.tsx backend/app/api/portal.py
rg -n "P-264|P-PILOTO-11|P-E001-CANARIO-VIVO-NO-IMPLANTADO" docs/canon/PENDENCIAS.md

# antes de QUALQUER SQL:
cat docs/canon/MIGRATIONS-AUTHORITY.md
```

Depois, as 14 premissas da proposta §4.2, uma a uma, com a saída colada. **O número do executor vence o deste pacote.**

---

## 5. O que continua DESCONHECIDO

1. **O texto exato das telas dos 12 prints.** Estão no bucket; ninguém os transcreveu. É a primeira tarefa do BLOCO 0, e dela depende o corpus do G3.
2. **Se as senhas novas resolvem.** 📊 A Allianz responde a mesma tela desde 18/08 e a Mapfre nunca teve um `done` — mas nunca foi testada uma senha diferente. 💭 A hipótese "senha expirada" explica os dois; não está provada.
3. **Quantas parcelas por segurado existem na carteira real.** 📊 7 parcelas/dia nos dois dias, e o diagnóstico registra 4 do mesmo CNPJ — mas a distribuição por segurado em 30 dias não foi medida (o ledger está vazio e os itens não são persistidos fora de `routine_runs.output_full`).
4. **Se `cpf_cnpj` chega preenchido em todas as 6 journeys.** Confirmado em `allianz_corretor.py:170, :1578`. As outras cinco não foram lidas linha a linha. 🔴 **O BLOCO 0 tem de medir isso** — é a chave do agrupamento e da regra de N dias.
5. **O custo real do prólogo de `login_check`** (💭 6 jobs × ≈100 s). Nunca foi executado.
6. **Se a Central de Agentes (`/agents-status`) aceita um grupo novo sem mudar o contrato do front.** `admin_spec034.py:56` não foi lido em profundidade.
7. **Quanto do `evidence.body_text` cabe redigido** sem estourar o `jsonb` do job.

---

## 6. Armadilhas que o aquecimento deve refutar

1. *"É só pôr `bloco_unico=True` em `_entregar_agora` e acabou."* — **Não.** Quebraria a saudação de religamento e o follow-up, que falam com o segurado (§2.3).
2. *"Passar um parâmetro novo pela porta resolve."* — **Não.** A entrada da fila não o carregaria, e o replay voltaria a picotar (§2.3).
3. *"A Mapfre falhou sem motivo."* — **Não.** 📊 O motivo está escrito em `evidence.message`; quem não lê é a linha do relatório.
4. *"A Allianz caiu por fragilidade de navegação (38 seletores)."* — **Não.** A tela real diz "Acesso negado / valide os dados". Fragilidade é hipótese para depois da senha nova.
5. *"Basta acrescentar 'Acesso negado' à lista `_FAIL`."* — **Cuidado.** `_norm` tira acento e maiúscula ANTES de comparar: escrever com maiúscula produz um padrão que nunca casa e um teste que fica verde porque normaliza igual (CLAUDE.md §9.4).
6. *"Agrupar por `cpf_cnpj` basta."* — **Não.** Sem o portal na chave, dois homônimos de seguradoras diferentes viram um segurado; e a mensagem nomeia uma seguradora só.
7. *"A regra de N dias substitui a dedup por parcela."* — **Não.** São perguntas diferentes: a dedup protege a PARCELA (identidade), a janela protege o SEGURADO (frequência). Uma não implica a outra.
8. *"A reserva pode ser por grupo."* — **Não.** Apagaria a identidade `(company_id, portal_key, recibo)` e reabriria "cobrar de novo trocando o agrupamento".
9. *"`CREATE OR REPLACE` com um parâmetro a mais substitui a função."* — **Não.** Cria uma sobrecarga; com DEFAULT, a chamada de 12 argumentos passa a ser **ambígua** (42725) — em produção, na hora de reservar.
10. *"`health='unknown'` é um defeito e deve sumir."* — **Não.** É o **meio-aberto** do circuit breaker: senha nova merece veredito novo, e é o único gesto humano que reabre o circuito sem inventar botão.
11. *"O teste `test_a_cobranca_esta_como_estava` prova que a mensagem sai inteira."* — **Não.** 📊 Ele mede uma constante de 292 caracteres **escrita dentro do teste**, que o produto não envia; o texto real tem 331 e vira 2 balões. Guarda verde, produto picotado.
12. *"O canário Q1–Q6 já foi rodado."* — **Não.** Ele está escrito desde 07/09 e **nunca rodou ao vivo**; as variáveis estão no smith-api desde 08/09 (`P-PILOTO-11`).
13. *"Criar uma tabela de telas desconhecidas é o caminho."* — **Cuidado.** P-264: 📊 `tela_cega` tem 2 linhas e zero leitores desde 26/08. Fila sem leitor não é fila.
14. *"Retry resolve credencial recusada."* — **Não.** Não é falha transitória; repetir entrada bloqueia a conta da corretora no portal.

---

## 7. Pesquisa externa — fontes primárias, reabertas em 13/09/2026

| # | fonte | o que entrou na SPEC | o que foi rejeitado |
|---|---|---|---|
| **E1** | https://playwright.dev/docs/auth | o *setup project* vira o prólogo de `login_check`; *"you need to delete the stored state when it expires"* vira o TTL sobre `verified_at` | o `outputDir` limpo a cada rodada — login real em seguradora é caro |
| **E2** | https://playwright.dev/docs/locators | nada, **de propósito**: a Allianz é a mais frágil e **não foi a fragilidade que a derrubou** | reescrever a Allianz por papel nesta SPEC; fica com gatilho medido |
| **E3** | https://learn.microsoft.com/en-us/azure/architecture/patterns/circuit-breaker | os três estados dentro de `portal_accounts.health`; *accelerated circuit breaking* para credencial recusada; *"stop retry attempts if the fault isn't transient"* | limiares adaptativos por ML; *failed request replay* (replay de login bloqueia conta) |
| **E4** | https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/ | **full jitter** (`random(0, base·2^n)`), base 60 s | o teto alto e o número alto de tentativas: o nosso limite não é carga, é bloqueio de conta |
| **E5** | https://www.postgresql.org/docs/current/indexes-partial.html | índice parcial `WHERE send_mode='real'`, com `company_id` na frente | transformar a regra de N dias num UNIQUE — ela é janela de tempo, não identidade |

> ⚠️ A URL canônica da AWS Builders' Library de *"Timeouts, retries and backoff with jitter"* redireciona hoje (301) para `builder.aws.com` e o conteúdo não abriu. O blog de arquitetura (E4), do mesmo autor e com as simulações, abriu e é o que está citado. O pesquisador do executor deve tentar a Builders' Library de novo e registrar o resultado.

---

## 8. Pendências, por número

**Fecham nesta SPEC (com prova):** `P-E001-CANARIO-VIVO-NO-IMPLANTADO` · `P-E001-Q4-VIVO-DEPENDE-DE-DEPLOY` · `P-PILOTO-11`.
**Tocadas, com estado a declarar:** `P-264` (a fila de portal nasce com leitor; a da URA continua sem) · `P-E001-LEDGER-SEM-VENCIMENTO-E-VALOR` (a migration do B1 é a oportunidade) · `P-E001-INCERTO-ESCRITA-DUPLA` · `P-E001-FILA-SEM-AUTORIZACAO-DE-AUXILIAR` (é a evidência que justifica decidir por `kind`).
**Fora do escopo, citadas só como contexto:** `P-PILOTO-17` (`llm_max_tokens`), `P-PILOTO-18` (tool calls do chat), `P-PILOTO-19` (403 do financeiro InfoCap), `P-PILOTO-20` (guardas de policy no harness).

⛔ Não ler `PENDENCIAS.md` inteiro (📊 562 KB). Só por número.

---

## 9. Regra de integridade deste pacote

Todo número deste documento tem o comando ao lado. Quem reproduzir e achar diferente **tem razão**: registra a diferença, corrige e segue (protocolo §0.4). O que **não** é permitido é transportar qualquer linha daqui para a SPEC definitiva sem reabrir o arquivo — as coordenadas mudam a cada commit, e a §2.1 é a prova de que já mudaram oito vezes entre 12 e 13/09.
