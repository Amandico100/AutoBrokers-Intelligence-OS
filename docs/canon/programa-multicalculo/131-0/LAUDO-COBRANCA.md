# LAUDO — Auxiliar de Cobrança (`cobranca-feita`): por que "dá muito erro" e o desenho estável

> 📋 **Cópia para o canon (11/10/2026, agente de síntese):** revisada por `grep` de CPF/CNPJ, telefone, e-mail, nº de apólice e nomes próprios de pessoa → **0 ocorrências a redigir**. Nenhuma credencial: do `/incorp_url_post` só a FORMA da resposta, nunca os valores. Os caminhos `scratchpad/…` citados são do rascunho da sessão e não estão no repositório. O resumo para o Founder está em [`MAPA-DE-POSSIBILIDADES-INFOCAP-AGGER-SEGURADORAS.md`](MAPA-DE-POSSIBILIDADES-INFOCAP-AGGER-SEGURADORAS.md).

> Modo INVESTIGAÇÃO (protocolo AAA v13.2 §3.3) · read-only · 11/10/2026 · investigador Opus 5.5
> Banco: só pelo MCP do Supabase (`execute_sql`, SELECT), projeto `dcajcvlzcjbmyapmklil`.
> Nenhum dado pessoal neste laudo. Corretoras pelo prefixo do `company_id`: **A = `04b5cdbc`** (a que tem a rotina) · **B = `6c9c55e2`**.

```
EXECUTION CARD (investigação)
OUTCOME ........ o Founder sabe POR QUE cada seguradora falha e o que capturar para estabilizar
RISCO/SUPERF. .. n/a (§3.3: varredura read-only) · nada alterado no repositório nem no banco
O FIO .......... rotina → routine_engine → billing_collection → portal_jobs → portal_worker (Playwright)
                 → journey da seguradora → evidence → fila/entrega WhatsApp → peça (Artifact)
O ELO .......... "falha PORQUE X" só onde a tela/evidência do próprio job diz X (§0.3)
```

---

## 0. AS TRÊS FRASES QUE MUDAM O DIAGNÓSTICO

1. **📊 Quando entra no portal, o robô acerta 100%.** Nas 13 varreduras `done` da rotina desde 17/08, o número de boletos baixados é IGUAL ao de inadimplentes em 13 de 13. Toda falha medida está na **porta de entrada** (senha recusada) ou na **resposta vazia da Zurich** — nenhuma está na leitura da lista nem no download do boleto (exceto um caso de navegação Allianz em 18/08).
2. **📊 O portal-worker não roda nada há 30 dias.** Último job de toda a tabela `portal_jobs`: **11/09/2026 14:01**; jobs desde 12/09: **0**. Todo o endurecimento feito depois (canário de login, reclassificação "Acesso negado", disjuntor de saúde — SPEC-EXTRA-001.6, 13–14/09) **nunca rodou em produção**: 📊 `login_check` enfileirados na história = **0**.
3. **📊 Nas duas últimas execuções com as 6 seguradoras (10 e 11/09) deram certo 3 de 6, as mesmas 3 nas duas:** HDI, Tokio, Yelum ✅ · Allianz, Mapfre ❌ por **senha recusada pelo portal** · Zurich ❌ por **lista vazia não confirmada**.

---

## 1. O MAPA DE PONTA A PONTA (FATO, por leitura de código com a linha)

| elo | arquivo:linha | o que faz |
|---|---|---|
| quem dispara | `routines` (1 linha, corretora A, `config.kind='billing_collection'`, agenda diária 11:01 seg–sex) → `backend/app/services/routine_engine.py:304-319` | chama `execute_billing_collection_routine` com teto `min(max(ROUTINE_EXEC_TIMEOUT, BILLING_COLLECTION_TIMEOUT_SECONDS=900), 1800)` |
| ponte de Work Run | `work_runs.workflow_key='bridge.routine.execute'` | a mesma execução vira Work Run (📊 9 `completed`, 17/08–11/09) |
| orquestrador | `backend/app/services/billing_collection.py:3481` | canário de login (`:3361`) → um `cobranca_sweep` por portal (`:1074 _enqueue_job`, fila `portal_jobs`) → espera (`_poll_job`, 360 s cada, sequencial) → fila de cobrança (48 h de carência) → envio (modo `test`: só para o número de teste) → avisos ao grupo → peça no Artifact Hub |
| registro de capacidades | `backend/portal_worker/journeys/__init__.py:230-236` | 6 portais com `login_check` + `cobranca_sweep`: allianz, hdi, tokiomarine, yelum, mapfre, zurich |
| executor | `backend/portal_worker/worker.py` | **Playwright/Chromium** (`:1337`), `--headless=new` (`:335`), sessão salva cifrada em `portal_sessions`, serial (`leases.py:293` — `PORTAL_WORKER_CONCURRENCY` padrão 1) |
| o que baixa | evidence `inadimplentes[]` + `boletos[]` (PDF no bucket) | 2ª via de boleto da parcela vencida; débito automático/cartão vira TAREFA para a equipe (robô não fala) |
| para onde manda | WhatsApp da corretora (Evolution), `billing_sent_log` (dedup só nos modos reais), grupo de suporte, peça | 📊 `billing_sent_log` = **0 linhas** (nunca saiu cobrança real; só modo teste) |

### Como cada journey fala com o portal — TODAS são HÍBRIDAS
Navegador só para **entrar**; a leitura e o boleto são **chamadas HTTP de dentro da página** (fetch in-page / função do próprio portal), desenhadas a partir de captura do Founder.

| seguradora | login | lista de parcelas | boleto | captura de referência | 📊 `.click(` no arquivo |
|---|---|---|---|---|---|
| **Allianz** | formulário Angular + reuso de sessão (`allianz_corretor.py:830`) | ⚠️ **navegação por CLIQUE** até "Parcelas inadimplentes" (`_ensure_inadimplentes_page :2647`) + escuta da API | BFF in-page (`getListIni`/`getDetail` "Carta Inadimplência", `:3309`) | "headers capturados 11/07" + PDF de prints; **HAR NÃO localizado** | **20** |
| **HDI** | navegador (Akamai exige `headless=new`) | POST legado HTML, 4 passos (`hdi_corretor.py:18`) | `dsp_boleto` → `boletoPDF.jsp` | "capturas 10/08"; **HAR NÃO localizado** | 1 |
| **Tokio** | navegador | GraphQL + relatório XML com **testemunha** (totais) | prorrogação → `cUrlCSF` | ✅ 2 HAR (12/08) | 3 |
| **Yelum** | navegador Auth0; token ESCUTADO na rede | REST JSON + testemunha `overdue?filter=count` | GET que já é PDF | ✅ HAR 24,5 MB (12/08) | 1 |
| **Mapfre** | navegador Ionic (tecla a tecla, modal de privacidade, 3 tokens) | REST `/receipts` | `BO_{receiptId}` base64 | ✅ HAR 29 MB (12/08) + CSV/HTML | 7 |
| **Zurich** | navegador; sessão em cookie | GET `ListarParcelaVencida` in-page, com pausa de 2,5 s (portal recusa rajada com 404) | função da página `GerarBoleto2` (a URL reconstruída dá 404) | ✅ 2 HAR (13/08, "PARTE 2 COM ERRO") | 6 |

📊 cliques: `for f in allianz hdi mapfre tokio yelum zurich; do grep -c "\.click(" backend/portal_worker/journeys/${f}_corretor.py; done` → 20 · 1 · 7 · 3 · 1 · 6.
📊 HARs: `find …/AutoBrokers-Opus-Exec/docs/intake/MATERIAIS -iname "*.har"` → MAPFRE 1, TOKIO 2, YELUM 1, ZURICH 2 (+ vidros). ⚠️ Estão **só na árvore vencida `AutoBrokers-Opus-Exec`** (fora do git: `.gitignore:113 docs/intake/`), **não** na `AutoBrokers-FIX`. Allianz/HDI: buscado em FIX/docs/intake, 15 árvores irmãs, Downloads/Desktop/Documents (profundidade 7) → nenhum `.har`; só `AutoBrokers-Fable-Exec-SPEC016/docs/intake/PRINTS PORTAL ALLIANZ PARA COBRANÇA.pdf`.

---

## 2. AS EXECUÇÕES REAIS, MEDIDAS

### 2.1 A rotina e o auxiliar
```sql
select r.is_active, r.config->'portal_keys', r.config->>'send_mode', r.schedule, r.last_run_at, ta.slug, ta.status
from routines r left join tenant_auxiliaries ta on ta.id=r.tenant_auxiliary_id
where r.config->>'kind'='billing_collection';
```
📊 1 rotina (corretora A): `is_active=false`, 6 portais, `send_mode=test`, última execução **11/09 14:01**; auxiliar `cobranca-feita` **paused** desde 12/09 18:56. Corretora B: auxiliar instalado, `paused` desde 17/08, **nunca rodou** (`last_run_at` NULL) e sem rotina.

### 2.2 Execuções da rotina (`routine_runs`, 15/07 → 11/09)
```sql
select started_at::date, status, round(extract(epoch from finished_at-started_at)) seg, left(error,120)
from routine_runs where routine_id='cc69c3b9-9671-411a-87a6-cf99f609d57b' order by started_at;
```
📊 **18 linhas: 11 `ok`, 7 `error`.** Os 7 erros, agrupados:
| motivo | n | datas |
|---|---|---|
| órfã — worker reiniciou no meio (deploy) | 4 | 17/08 |
| envio WhatsApp falhou (`HTTP 401` evolution-go ×2, "Failed to send" ×1) | 3 | 17/08 |
| falha de portal | **0** — a execução fica `ok` mesmo com 3 de 6 portais caídos | — |

⚠️ Cada execução gera **duas** linhas (`"entregue ao motor de trabalhos e concluído"` + o relatório) — a tela de Entregas mostra o mesmo dia em dobro.
⚠️ 📊 Duração das execuções com 6 portais: **886 s, 893 s (10/09), 831 s, 837 s (11/09)** — contra um teto de **900 s** (`routine_engine.py:309`, `BILLING_COLLECTION_TIMEOUT_SECONDS` padrão 900).

### 2.3 Varreduras por seguradora (`portal_jobs`, `journey='cobranca_sweep'`)
```sql
select portal_key, count(*) total, count(*) filter (where status='done') ok, count(*) filter (where status<>'done') falha
from portal_jobs where journey='cobranca_sweep' and params->>'source'='routine_engine' and created_at>='2026-08-17'
group by rollup(portal_key);
```
| seguradora | rotina desde 17/08 (ok/total) | história inteira, todas as origens (done/total) | últimas 2 (10–11/09) |
|---|---|---|---|
| Allianz | 5/8 | 28/65 (+34 needs_human, 3 archived) | ❌❌ |
| HDI | **4/4** | 7/9 (2 `failed` Akamai em diagnóstico de 12/08, já resolvido) | ✅✅ |
| Mapfre | **0/2** | **0/2** — nunca entrou, em nenhuma corretora | ❌❌ |
| Tokio | **2/2** | 5/5 | ✅✅ |
| Yelum | **2/2** | 6/6 | ✅✅ |
| Zurich | **0/2** | 1/3 (o único `done` é da corretora B, 14/08) | ❌❌ |
| **total** | **13/20 = 65 %** | | **6/12 = 50 %** |

📊 Completude quando dá certo (`jsonb_array_length(evidence->'inadimplentes')` vs `…->'boletos'`, mesmos filtros): **13 de 13 `done` com inad = boletos** (3/3, 2/2, 1/1, 5/5…).
📊 Tempo na fila do 6º portal: **376–379 s** (worker serial; `started_at - created_at`).

### 2.4 Os motivos, agrupados (todas as origens)
```sql
select portal_key, status, left(coalesce(evidence->>'message', error),140), coalesce(evidence->>'stage', evidence->'captured'->>'stage'), count(*), min(created_at)::date, max(created_at)::date
from portal_jobs where journey='cobranca_sweep' group by 1,2,3,4;
```
| seguradora | motivo gravado | n | período | classe |
|---|---|---|---|---|
| Allianz | "download de boletos precisa de revisão humana (busca de clientes devolveu vazio)" | 28 | 10–11/07 | navegação/UI (versão antiga por busca visual — superada pela cadeia BFF) |
| Allianz | "não consegui localizar a área de parcelas inadimplentes" | 6 | 08/07–18/08 | **navegação por clique** |
| Allianz | "tela de inadimplentes encontrada, mas não consegui extrair linhas" | 1 | 08/07 | UI |
| Allianz | "tela pós-login Allianz não reconhecida" | 2 | 10–11/09 | **senha recusada** (ver §3) |
| HDI | Akamai "Access Denied" | 2 | 12/08 | anti-robô — resolvido com `headless=new` |
| Mapfre | "a MAPFRE recusou a credencial (autenticação inválida)" | 2 | 10–11/09 | **senha recusada** |
| Zurich | "http 200 com ZERO parcelas, duas vezes seguidas" | 2 | 10–11/09 | **resposta vazia do portal** |

⚠️ 📊 Job Allianz de 18/08 ficou "rodando" **1.885.967 s (≈22 dias)** até ser arquivado; dois de 11/07 ≈ 60 dias. Trava sem vigia na época.

### 2.5 Saúde das contas
```sql
select portal_key, health, updated_at::date from portal_accounts; select portal_key, health, verified_at::date from portal_sessions;
```
📊 `portal_accounts.health` = **`unknown` em 20 de 20 linhas** — o escritor (`worker.veredito_de_saude`, `worker.py:152`) nasceu em 13–14/09 e nenhum job rodou depois. 📊 Sessão salva da Allianz (A): verificada pela última vez **17/08**; Mapfre (A) e Zurich (A): **nenhuma sessão salva**, nunca.

---

## 3. A CAUSA DOMINANTE, POR SEGURADORA (com a evidência)

| seguradora | causa | classe | evidência | confiança |
|---|---|---|---|---|
| **Allianz** | o portal **recusa a senha**: a tela diz *"Acesso negado — Por favor, valide os dados introduzidos."* O robô preencheu usuário e senha (📊 `login_fields_found = {username:true, password:true}`), clicou, e voltou ao formulário. O código antigo classificava isso como "tela não reconhecida". | **login (senha)** | `backend/tests/corpus/telas_reais_de_portal/allianz_corretor-needs_human-20260911.txt` (transcrição do print do job); `allianz_corretor.py:659-676` (`_FAIL` ganhou "acesso negado" em 13/09) e `:703-731` | FATO (a tela) · INFERÊNCIA: senha trocada/expirada entre 18/08 e 10/09 (a conta não foi atualizada desde 08/07) |
| **Allianz (2ª)** | navegação por clique até a lista de inadimplentes quebra quando a tela muda | **mudança de tela** | 6 jobs `inadimplentes_nao_localizado` (08/07–18/08); 20 `.click(` no arquivo | FATO |
| **Mapfre** | o portal **recusa a credencial**: *"Autenticação inválida!"*. O botão Entrar foi achado e estava habilitado (📊 `mapfre_botao_entrar = {achou:true, desabilitado:false}`, modal de privacidade fechado `true`), então não é o bug do Ionic. Usuário no formato certo (📊 11 dígitos, `username ~ '^\d{11}$'` = true). **Nunca houve um `done` da Mapfre em produção.** | **login (senha)** | `mapfre_corretor-failed-20260911.txt`; `mapfre_corretor.py:520-522` | FATO (a tela) · INFERÊNCIA: senha errada/bloqueada na conta cadastrada |
| **Zurich** | entra (dashboard da corretora na tela, `logged_in=true`), chama a lista de 90 dias e recebe **HTTP 200 com 46 bytes: `{"corretor":[],…}`** — duas vezes. A regra da journey é: zero parcelas nunca é "carteira em dia" → `needs_human`. | **resposta vazia do portal** (recusa silenciosa OU carteira sem Zurich) | evidence `zurich_lista.bytes=46`, `zurich_segunda_leitura.lidas=0`; `zurich_corretor.py:1193-1222`; o próprio código registra (13/08) "a mesma janela devolveu 43 linhas e, três minutos depois, 200 com 46 bytes" | FATO (a resposta) · **NÃO DECIDIDO**: só um HAR logado como corretora A diz se a tela também mostra zero |
| **HDI** | estável (4/4) | — | Akamai resolvido com `headless=new` (`worker.py:335`) | FATO |
| **Tokio** | estável (2/2; 5/5 na história) | — | XML com testemunha de totais | FATO |
| **Yelum** | estável (2/2; 6/6) | — | testemunha `overdue?filter=count` | FATO |

**Nenhuma** falha medida é captcha, 2FA ou timeout de portal. Captcha só na Porto (fora, decisão do Founder).

### O que mais aparece como "erro" para o Founder, e NÃO é portal
- 📊 3 execuções de 17/08 morreram no **envio do WhatsApp** (401 do evolution-go) e 4 por **deploy no meio**.
- 📊 Work Run `completed` nas 9 execuções, inclusive nas duas em que 3 de 6 portais caíram: o status não diz "parcial".

---

## 4. RISCO NOVO, ANTES DE RELIGAR (INFERÊNCIA forte, a medir)

**A primeira execução com o código endurecido tende a estourar o teto de 900 s.**
- A (medido): execução com 6 portais = **831–893 s** (📊 §2.2), 93–99 % do teto.
- B (lido): teto = 900 s (`routine_engine.py:309`); worker serial (`leases.py`, padrão 1); `POLL_SECONDS=30` (`worker.py:21`).
- O ELO: o canário (`billing_collection.py:3361`) enfileira **6 `login_check` a mais na MESMA fila serial**, antes das 6 varreduras. Cada um é um login inteiro (≈15–100 s) + até 30 s de latência de pegada. ⚠️ Não medido (0 `login_check` na história) — **é a primeira coisa que a execução de teste mede.** Se estourar, `asyncio.wait_for` cancela e o relatório do dia se perde.
- Remédio barato (para a SPEC, não feito aqui): `BILLING_COLLECTION_TIMEOUT_SECONDS=1800` no smith-api, ou `PORTAL_WORKER_CONCURRENCY=2`.

Achado lateral (comentário, não produto): `allianz_corretor.py:673` e `:3787-3791` afirmam "34 tentativas entre 18/08 e 11/09"; 📊 medido **3** (`select status,count(*) from portal_jobs where portal_key='allianz_corretor' and journey='cobranca_sweep' and created_at>='2026-08-18' and created_at<'2026-09-12' group by 1` → archived 1, needs_human 2). Os 34 são o total histórico de `needs_human` desde julho.

---

## 5. RECOMENDAÇÃO — o desenho estável

### 5.1 O que o dado diz sobre "estável"
O desenho atual — **navegador só para entrar, HTTP para ler e baixar** — já é o estável: onde ele é usado de ponta a ponta (HDI, Tokio, Yelum), 📊 **8/8** varreduras da rotina desde 17/08 (HDI 4 + Tokio 2 + Yelum 2) e **18/20** na história inteira (as 2 falhas são o diagnóstico Akamai da HDI de 12/08, já resolvido). O que falha é (a) **senha** e (b) os dois lugares onde o desenho ainda não é API-primeiro: a **lista da Allianz** (clique) e a **lista da Zurich** (resposta vazia sem testemunha).

### 5.2 As opções, com nota

| opção | o que é | nota |
|---|---|---|
| **A. Higiene de credencial + religar com o canário em teste** | Founder entra à mão na Allianz e na Mapfre, troca/confirma a senha, salva em Personalização › Conectores › Portais (isso põe `health='unknown'`, e o robô tenta uma vez). Religa em `send_mode=test` por 3 dias úteis com o teto subido para 1800 s. | **93** — destrava 2 de 3 seguradoras caídas sem uma linha de código; prova pela 1ª vez o canário e o disjuntor |
| **B. Allianz API-primeiro na LISTA** | trocar a navegação por clique até "Parcelas inadimplentes" pela chamada BFF que a tela faz (o boleto já é BFF). Exige HAR. | **86** — a Allianz é a única com 20 cliques e a maior história de falha de tela (35 jobs de UI) |
| **C. Zurich: decidir o vazio com HAR da corretora A** | HAR logado como a corretora A: Consulta › Parcelas vencidas, 90 dias. Se a tela também mostra zero → a carteira não tem Zurich e a regra precisa de testemunha (ex.: contagem do dashboard); se a tela mostra linhas → a chamada in-page perde um estado (sucursal/filtro) que o HAR revela. | **82** |
| **D. HDI: HAR de referência** | já é HTTP e está 4/4; o HAR serve de régua de regressão (as capturas de 10/08 não estão no disco) | **60** |
| **E. Login 100 % HTTP, sem navegador** | reproduzir login por requisição | **35** — Akamai (HDI), Auth0 com token em memória (Yelum), Ionic com 3 tokens (Mapfre); a porta é exatamente onde mora a detecção de robô, e o navegador NÃO é a causa de nenhuma falha medida |
| **F. Agente de navegador com visão (LLM clicando)** | | **20** — troca o determinístico que acerta 100 % por um probabilístico mais caro, na parte que já funciona |
| **G. Só religar como está** | | **45** — 📊 3 de 6 cairiam no 1º dia (2 por senha que ninguém trocou) e o teto de 900 s está a 7 s |

### 5.3 A ordem
1. **Founder — senhas (hoje, 15 min).** Entrar à mão em `allianznet.com.br` e `negocios.mapfre.com.br` com a conta cadastrada da corretora A. Se a senha antiga não entra: redefinir, e salvar a nova no conector. Conferir que **não** aparece captcha/2FA na entrada (se aparecer, avisar — muda o desenho).
2. **Execução — teto e religar em teste** (`BILLING_COLLECTION_TIMEOUT_SECONDS=1800`; rotina ativa, `send_mode=test`; 3 dias úteis). Medir: `login_check` por portal, duração total, `portal_accounts.health` escrito.
3. **Founder — HAR da Allianz** (o mais valioso).
4. **Founder — HAR da Zurich** como corretora A.
5. **Execução — copiar os HARs existentes** (Mapfre, Tokio, Yelum, Zurich) de `AutoBrokers-Opus-Exec/docs/intake/MATERIAIS/` para `AutoBrokers-FIX/docs/intake/` (copiar, nunca link — memória "nunca junction em worktree").
6. **Founder — HAR da HDI** (referência, sem pressa).

### 5.4 Como capturar o HAR (o que o Founder faz)
Chrome → F12 → aba **Network** → marcar **Preserve log** e **Disable cache** → apagar a lista → só então abrir a página de login. Fazer o caminho inteiro, devagar (o portal da Zurich recusa rajada). Ao fim: ícone de download → **"Export HAR (with sensitive data)"** — sem isso o Chrome tira o `Authorization` e os cookies (foi o que escondeu o token da Yelum). Salvar em `docs/intake/MATERIAIS/<SEGURADORA>/`.

| portal | as telas, nesta ordem | por quê |
|---|---|---|
| **Allianz** | login → home → **Parcelas inadimplentes** (o card/menu) → a lista aparecer → abrir 1 parcela → baixar a **2ª via / Carta de inadimplência** | revela a chamada BFF da LISTA, para matar os 20 cliques |
| **Zurich** (corretora A) | login → Consulta › **Parcelas vencidas** → período 90 dias → **Buscar** → (se houver linha) **Gerar 2ª via** · + um print da tela de resultado | decide se o vazio é real ou recusa |
| **HDI** | login → **Parcela** → filtro de vencimento → lista → **2ª via** de 1 boleto | régua de regressão (captura de 10/08 perdida) |
| Mapfre | só se, depois da senha nova, a varredura falhar além do login — o HAR de 12/08 existe | — |

---

## 6. O QUE FICOU FORA / LIMITES DESTE LAUDO
- Não abri os HARs existentes (são de 12–13/08; a causa das falhas de setembro está antes deles: senha e resposta vazia).
- Não li o `.env` de produção: a afirmação do teto de 900 s vale **se** `BILLING_COLLECTION_TIMEOUT_SECONDS` não estiver definida lá (INFERÊNCIA a favor: as durações de 831–893 s ficaram sempre abaixo de 900, compatível com o padrão; a confirmação é `printenv BILLING_COLLECTION_TIMEOUT_SECONDS` no contêiner do smith-api).
- `git log` nos arquivos de cobrança estourou o relógio (repo grande); as datas do endurecimento (13–14/09) vêm dos comentários do código e da memória da SPEC-EXTRA-001.6.
- Porto: fora (captcha, decisão do Founder). Bradesco tem conta cadastrada nas duas corretoras mas não tem journey de cobrança.
