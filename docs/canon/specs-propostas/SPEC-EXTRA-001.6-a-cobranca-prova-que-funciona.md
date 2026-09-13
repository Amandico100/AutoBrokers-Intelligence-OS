# SPEC-EXTRA-001.6 — A COBRANÇA PROVA QUE FUNCIONA
## Uma mensagem inteira por segurado, nenhuma parcela duas vezes, e cada portal dizendo em português por que não entrou

**Produto:** AutoBrokers Intelligence OS.
**Status:** PROPOSTA PARA CONVERSÃO, AQUECIMENTO E EXECUÇÃO — não é SPEC canônica aprovada nem implementação realizada.
**Versão:** 1.0 · **Data:** 13/09/2026.
**Baseline medido nesta redação:** worktree `AutoBrokers-FIX`, branch `docs/diagnostico-pilotos-0912`, `HEAD = origin/main = a0bb5fef440eba394a9275671b1143f5025807ef` (📊 `git rev-parse HEAD`, 0 atrás, 0 à frente, 13/09/2026). **Todo `arquivo:linha` deste documento foi reaberto e conferido nesta revisão.**
**Origem:** `docs/canon/DIAGNOSTICO-PILOTOS-E-PLANO-EXTRA-2026-09-12.md` §1.7 (primeira leitura) e **§9 inteiro** (laudo I6, 13/09 — que substitui a §1.7).
**Antecessora:** `SPEC-EXTRA-001 · Operação dos pilotos` (proposta em `docs/canon/specs-propostas/SPEC-EXTRA-001-operacao-dos-pilotos.md`; relatório em `docs/canon/reports/SPEC-EXTRA-001-EXECUTION-REPORT.md`; `main` em `ba7ba75`).
**Branch sugerida:** `feat/spec-extra-0016-a-cobranca-prova-que-funciona`.
**Destino desta proposta:** `docs/canon/specs-propostas/SPEC-EXTRA-001.6-a-cobranca-prova-que-funciona.md`.
**SPEC definitiva a criar pelo executor:** `docs/canon/specs/SPEC-EXTRA-001.6-a-cobranca-prova-que-funciona.md`.
**Research Pack:** `SPEC-EXTRA-001.6-a-cobranca-prova-que-funciona-RESEARCH-PACK.md`.
**Relatório a criar durante a execução:** `docs/canon/reports/SPEC-EXTRA-001.6-EXECUTION-REPORT.md`.
**Protocolo:** `PROTOCOLO-AUTOBROKERS-AAA.md` v11.2 + OPÇÃO B.

---

## 0. RESULTADO E MOTIVO

> A rotina de cobrança roda em modo **`equipe`**. A atendente da Resulta recebe **uma mensagem inteira por segurado**, com os N boletos dele anexados — nunca o mesmo boleto duas vezes, nunca o mesmo segurado mais de uma vez a cada 7 dias. Cada portal que não entrou diz **em português** por que não entrou. Credencial recusada é uma classe própria: chega ao dono no mesmo dia, e o robô para de bater na porta trancada.

### 0.1 O motivo, em três medições

📊 **A máquina da EXTRA-001 nunca foi ligada.** `select count(*) from billing_sent_log` = **0** (13/09/2026, projeto `dcajcvlzcjbmyapmklil`). O ledger com reserva atômica, os estados por componente e a retenção honesta que a EXTRA-001 construiu existem, estão na `main` desde `ba7ba75`, estão implantados — e **nunca escreveram uma linha**, porque as duas execuções de 10 e 11/09 rodaram em `send_mode='test'`, e em teste o ledger é desligado por desenho.

📊 **O que saiu do canal não é o que o sistema acha que saiu.** Em 10 e 11/09 a rotina tratou 7 parcelas por dia e gravou **7 linhas por dia** em `platform_sends` (`select date_trunc('day',created_at), count(*) from platform_sends where kind='billing'` → 10/09: 7 · 11/09: 7). Medido com o motor real (`build_customer_message` + `_format_test_message` + `split_whatsapp_balloons`, 13/09), a mensagem de teste tem **517 caracteres e vira 3 balões**; com o PDF, **4 mensagens por parcela**. O canal recebeu **≈28 mensagens por dia** e o governador de vazão contou **7**. Subestimou **4×**.

📊 **Metade dos portais não entrou, e nenhum disse por quê de um jeito acionável.** Dos 6 portais, `select portal_key,status,count(*) ... from portal_jobs` (13/09) mostra Allianz com **34 `needs_human`** e último `done` em **17/08**, Mapfre com **2 `failed`** (nunca teve um `done`), Zurich com 2 `needs_human` — e **`error IS NULL` em 100% dos jobs da história**, porque o worker limpa esse campo ao finalizar (`portal_worker/worker.py:944`). O relatório da cobrança lê exatamente `error` na linha que trata `failed` (`billing_collection.py:2331`) e lê `evidence.message` na linha vizinha, que trata `needs_human` (`:2329`). **A Mapfre já escreveu o motivo certo** — `evidence.message` = *"a MAPFRE recusou a credencial (autenticacao invalida)"* — e ninguém o lê.

### 0.2 O que esta SPEC conserta, dito como o corretor entende

| hoje | depois |
|---|---|
| a atendente recebe 5 mensagens picotadas por segurado | 1 mensagem inteira + os boletos |
| 4 boletos do mesmo CNPJ = 4 abordagens | 1 mensagem com 4 PDFs |
| o mesmo segurado cobrado dois dias seguidos | 1 cobrança a cada 7 dias, por segurado |
| "Aqui é a **nossa equipe**, da Resulta" | o nome da atendente de verdade — ou a rotina não sai |
| "portal mapfre_corretor: failed" | "a MAPFRE recusou a credencial (autenticação inválida)" |
| Allianz há 25 dias devolvendo "tela não reconhecida" | "a senha da Allianz foi recusada — renove em Conectores > Portais" |
| a sessão morta de 17/08 marcada `health='ok'` | a sessão vence, o `health` muda, e a tela mostra |
| 7 mensagens contadas, 28 enviadas | o governador conta o que o canal recebeu |
| CPF e telefone em claro no relatório da execução | mascarados no relatório; inteiros só na nota à atendente |

### 0.3 As decisões do Founder já incorporadas — são LEI nesta SPEC

| ID | decisão (13/09/2026) | como entra no produto |
|---|---|---|
| **D-PILOTO-18** | **O modo da rotina é `equipe`**, não `cliente` (nota 92 × 48). A atendente recebe o pacote e repassa. | `send_mode='equipe'`; `cliente` continua existindo e não é usado no piloto |
| **D-PILOTO-18** | **N = 7 dias** por segurado (nota 85 × 3 dias 60 × 14 dias 70) | `dias_entre_cobrancas_do_mesmo_segurado` = 7, na tela, clamp 1–30 |
| **D-PILOTO-18** | **`attendant_name` = a atendente humana da Resulta.** O executor **confirma o nome com o Founder** e nunca o inventa. | blocker quando vazio (§5, P0.4); o nome vai na **caixa do Founder**, não num palpite |
| **D-PILOTO-18** | **`team_number` = TESTE-B durante o canário**; trocar pelo número real da atendente é ato **só do Founder**, depois. | §1.1 e §10.2 |
| **D-PILOTO-18** | **A rotina só é reativada depois que o bloco implantável estiver no ar.** Reativar antes = avalanche picotada na atendente (nota 25). | §5 (a equivalência de nomes) e §15.1 |
| **D-PILOTO-19** | **As senhas novas da Allianz e da Mapfre chegam na segunda-feira (15/09), e isso NÃO trava nada.** O canário roda com Tokio, HDI, Yelum e Zurich; os dois portais entram quando a senha chegar. | §8.1, §10.2 e `P-E0016-SENHAS-ALLIANZ-MAPFRE` |
| **D-PILOTO-08** | numeração EXTRA-001.1…001.10 mantida | esta é a 001.6 |
| **D-PILOTO-14** | execuções de alta qualidade sem serem exorbitantemente longas | teto de **12 guardas novos**; painel de 3 lentes, uma rodada |
| **D-E001-03** | cobrança e atendimento usam o MESMO número pareado da corretora | nenhuma conexão é criada, renomeada ou desativada |
| **D-E001-04/05** | `equipe` = nota interna separada + texto final limpo + PDF | preservado byte a byte; o que muda é **quantos balões** |
| **D-E001-07** | testes vivos **só** entre TESTE-A e TESTE-B | §1 |

> 📊 **D-PILOTO-01…20 já estão gravadas** em `docs/canon/FOUNDER-DECISIONS.md` (commit `c0aaf65`; a 18 em `:1762`, a 19 em `:1763`). O entregável desta SPEC **não é registrar** — é **conferir, no BLOCO 0, se o texto gravado bate com o que esta SPEC executa**, e emendar o que divergir, com a diferença escrita (§10.3).

### 0.4 EXECUTION CARD proposto — a medir e reafirmar no BLOCO 0

```text
OUTCOME .............. a rotina roda em `equipe`: 1 mensagem inteira por segurado com N boletos, nunca a mesma
                       parcela duas vezes, nunca o mesmo segurado 2× em 7 dias; cada portal diz em português por
                       que não entrou; credencial recusada é classe própria e chega ao dono no mesmo dia
RISCO ................ 6 = ALCANCE 2 (a corretora: em `equipe` quem recebe é a atendente, não o segurado)
                         + REVERSIBILIDADE 3 (mensagem sai do prédio) + FREQUÊNCIA 1 (toda semana)
SUPERFÍCIE ........... 2 — vários comportamentos, todos em lugares que EU LISTO: billing_collection ·
                       platform_outbound · whatsapp_service · portal_worker/worker · allianz_corretor ·
                       app/api/portal · 2 telas Next. Nenhum território não mapeado
PISO APLICADO ........ §3.2 "qualquer coisa que ENVIE" + migration que ALTERA ESTRUTURA (coluna + índice +
                       função) → CRÍTICO. 🔴 O piso é absoluto; a soma (6) já chegaria a CRÍTICO sozinha
NÍVEL ................ CRÍTICO · opção B. 🔴 Não é escolha: o piso §3.2 é absoluto (§12.4)
UNIDADES ............. B0 medir · P0 a mensagem chega inteira · B1 ninguém é cobrado duas vezes ·
                       B2 a sessão morre e alguém sabe · B3 o portal é vigiado antes da rotina ·
                       B4 a prova tem leitor · B5 canário vivo e documentação
COESÃO ............... P0+B1 = billing_collection (arquivo-hub, UM dono por vez) · B2+B3 = portal_worker +
                       app/api/portal · B4 = billing_collection + worker (integração SERIAL depois de B1)
PARALELISMO REAL ..... B2/B3 (portal_worker) ∥ P0/B1 (backend/app/services) — conjuntos de arquivos disjuntos.
                       B4 depois de B1. As telas Next (B3.4) em paralelo com tudo
TIME ................. investigador+pesquisador (um agente) · aquecimento Opus · desenhista Opus ·
                       builders Opus (2) · verificador Sonnet · **INTEGRADOR** (§3.1 exige com 3+ unidades;
                       aqui são 6, em DOIS hubs: billing_collection e portal_worker/worker) ·
                       painel de 3 lentes CEGAS (verdade+regressão · produto+DADO · **red team, que é
                       uma das três — papel próprio com missão de quebrar, não uma 4ª lente**) ·
                       juiz fresco (§6.1). 📊 É a composição que a EXTRA-001 rodou
REFERÊNCIA ........... interna: CLAUDE.md §7 · `backend/tests/test_a_cobranca_esta_como_estava.py` (o CONTROLE) ·
                       `test_a_cobranca_chega_a_quem_deve.py` (162 asserções da EXTRA-001) ·
                       `backend/supabase/migrations/20260907_01_*.sql` (o formato de migration desta família)
                       externa: §13 — Playwright auth/locators · Microsoft Circuit Breaker · AWS jitter ·
                       PostgreSQL partial indexes
GATES ................ G1–G12 (§11), cada um com a mutação M1–M12 que o deixa vermelho · canário Q1–Q6
                       herdado + Q7–Q10 novos · suíte inteira ×2 · `git push` com a saída colada
O ELO ................ "a atendente recebe 5 mensagens PORQUE o envio não pede bloco único" —
                       A medido (📊 nota 322 ch → 2 balões · texto 331 ch → 2 balões · PDF 1 = 5) ·
                       B medido (`billing_collection.py:1153` e `platform_outbound.py:1478` chamam
                       `send_message` sem `bloco_unico`) · B chega em A ✅ (com `bloco_unico=True` os mesmos
                       dois textos viram 1 balão cada — medido na mesma execução)
FAIXA DE RELÓGIO ..... 💭 6–9 h (mantida do diagnóstico §9.4) + 💭 0,5 h da 3ª lente. Faixa, nunca promessa
ORÇAMENTO ............ ≤ 2,5 M de tokens de subagentes (CRÍTICO). 💭 alvo 1,4–1,8 M, pela superfície 2
BLOCKER (o que é) .... muda um byte do que a ATENDENTE lê, do que o SEGURADO recebe, do que fica no BANCO ou
                       de quem pode LER. Tudo o mais é pendência (protocolo §2)
```

### 0.5 O que esta SPEC **não** refaz — e por quê

O motor difícil está bom. 📊 O laudo I6 deu **36/100** ao auxiliar nos dois dias e a frase que resume o diagnóstico é: *"o que falha é tudo entre o motor e o humano"*. Ficam intactos, e a SPEC prova que ficaram:

- a **reserva atômica antes do efeito** (`billing_reservar_obrigacao`, migration `20260907_01`) — a identidade da obrigação continua `(company_id, portal_key, recibo)`;
- a **retenção honesta** — a Zurich recusando afirmar "está em dia" com HTTP 200 vazio é comportamento CERTO e não se toca (📊 a frase real está em `evidence.message` dos dois jobs de 11/09);
- os **estados verdadeiros** — `incerto` nunca é reclamado, `parcial` só reenvia o documento, `colisao_recibo` retém com incidente;
- a **porta única** `send_to_client_guarded` e o **governador de vazão**;
- o **modo teste de 17/08** como controle — o que muda nele está escrito, assertiva por assertiva, na §12.3.

---

## 1. AUTORIZAÇÃO DE TESTES — a fronteira que vale em todo pacote

### 1.1 Allowlist

| alias | onde mora o valor |
|---|---|
| **TESTE-A** | allowlist privada do executor · env `BILLING_CANARIO_ALLOWLIST` do smith-api |
| **TESTE-B** | allowlist privada do executor · env `CANARIO_TESTE_B` do smith-api |

📊 08/09: as duas variáveis **já estão no smith-api** (`P-PILOTO-11`). 📊 07/09: a conexão ativa da Resulta é **TESTE-A**; o destino do canário é **TESTE-B**.

⛔ **Nunca commitar, publicar em dossiê, colar em log, fixture permanente, screenshot ou relatório.** Só aliases.

### 1.2 O que está autorizado

- Implementar, converter, aquecer, provar e entregar esta SPEC.
- Mensagens vivas **exclusivamente entre TESTE-A (remetente) e TESTE-B (destino)**, com os dois na allowlist e no tenant/run do canário.
- Rodar a rotina de cobrança da Resulta em `test` e em `equipe` **com `team_number` = TESTE-B**.
- Consultas read-only ao banco de produção e leitura dos objetos já gravados no bucket privado `portal-evidence`.
- `login_check` nos portais **onde a credencial já está cadastrada e válida** (Tokio, HDI, Yelum, Zurich).

### 1.3 O que permanece proibido

1. Enviar para segurado, atendente real, grupo de suporte, seguradora ou qualquer número fora da allowlist — inclusive por fallback, alerta, fila, retry, replay e incidente.
2. Usar número operacional da Resulta ou da AutoFleet como remetente, mesmo para enviar ao Founder.
3. Trocar, apagar, renomear ou reparear conexão de WhatsApp; mexer em QR.
4. **Tentar entrar na Allianz ou na Mapfre com a senha atual.** 📊 As duas estão recusadas (Allianz desde 18/08, Mapfre sempre). Insistir é o caminho para o portal **bloquear a conta da corretora** — e é exatamente o que o breaker do B3 existe para impedir. Novas tentativas só depois da senha nova (🧑 segunda-feira).
5. Alterar valor, vencimento ou beneficiário de boleto real; publicar PDF de cliente.
6. Aplicar migration sem APPLY/VERIFY/ROLLBACK escritos antes e sem ler `MIGRATIONS-AUTHORITY.md`.
7. Relaxar qualquer controle de produção para "fazer o teste passar".

### 1.4 Verificação imediatamente antes de cada efeito

Ambiente · tenant · run de canário · conexão fixada por id · identidade real do remetente · destino normalizado por `telefone_br` · allowlist **dos dois lados** · janela · autorização do ator · orçamento do governador · tipo de operação. **Identidade não confirmada → não envia.** Não escolher outra conexão automaticamente. A verificação cobre texto, documento, nota interna, incidente, aviso e replay — não só o botão.

---

## 2. ESCOPO — o que entra, o que sai, e quando o que saiu volta

### 2.1 Obrigatório nesta SPEC

1. `bloco_unico` nos três textos da cobrança (nota interna, texto ao cliente, mensagem de teste) e nas duas portas.
2. O motivo do portal legível no relatório e no aviso — inclusive quando o job é `failed`.
3. Allianz: as frases reais da tela de credencial recusada, medidas no acervo, na lista `_FAIL`; e o diagnóstico de sessão morta alcançável.
4. Blocker quando `attendant_name` está vazio.
5. Governador contando mensagens reais.
6. Dedup por parcela **sempre**, inclusive em teste, com a flag invertida.
7. Agrupamento por segurado: 1 mensagem + N PDFs.
8. "Não cobrar o mesmo segurado mais de 1× por N dias" (N=7), com `segurado_chave` no ledger (migration expand-first).
9. Sessão que expira: TTL, `health` que muda, `session_reused` que diz a verdade.
10. Canário diário de `login_check` nos 6 portais antes da rotina; `available_at` + backoff com jitter; circuit breaker por portal; `health` escrito e **mostrado**.
11. Fila de telas desconhecidas de portal **entregue junto com o leitor**.
12. Print de desfecho redigido antes de subir; PII fora de `routine_runs.output_full`.
13. Canário Q1–Q6 herdado da EXTRA-001 + Q7–Q10 novos; roteiro das atendentes.

### 2.2 Fora desta SPEC, com o gatilho que a faz voltar

| frente | por que não entra | gatilho de retorno |
|---|---|---|
| Modo `cliente` (envio direto ao segurado) | D-PILOTO-18 escolheu `equipe`; o motor já existe e fica desligado | decisão do Founder depois do piloto medido (001.7) |
| Reescrever a Allianz com `getByRole` (📊 38 seletores por atributo × 5 por texto) | é refatoração de navegação, não é o que impediu a cobrança — **a senha foi recusada** | depois da senha nova, se o `login_check` diário mostrar quebra de seletor |
| API-first na Allianz e na Tokio (📊 0 pontos de API nas duas) | mesma razão; e exige captura de HAR que ninguém tem | SPEC própria de portais, ou 001.10 quando o motor de vidros provar o padrão |
| Régua de lembretes recorrentes | a EXTRA-001 recusou inaugurá-la e nada mudou | decisão comercial do Founder |
| `avisar_suporte_humano` deixar de falar com o grupo e passar a falar com o dono | é o coração da **001.3** (o grupo só recebe o que importa) | 001.3 — esta SPEC só acrescenta a frase do estágio novo |
| Dedup por conteúdo/`message_id` do provedor | `P-E001-RETORNO-IDEMPOTENTE-POR-CONTEUDO`; sem efeito hoje | 099 |
| Tabela nova para telas desconhecidas de portal | P-264 ensina: fila sem leitor não é fila. Aqui a fila é uma CONSULTA com leitor no dia 1 | 🔴 **o medidor é a própria consulta do B4.2**: quando ela devolver mais de 💭 50 telas distintas por mês, ou quando o `jsonb` de `portal_jobs` começar a pesar na leitura da lista, a consulta vira tabela — e o leitor já existe, que é a condição que P-264 pede |

⛔ Nada da §2.1 sai em silêncio. Corte material vira proposta registrada em `CHANGE-ADDENDA.md` com classe e evidência (CLAUDE.md §11, D5).

---

## 3. AUTORIDADES PRESERVADAS E ARQUITETURA — nenhum motor paralelo

🔴 **Nada aqui cria runtime, fila, scheduler, sender, ledger, publisher ou inbox.** Cada peça tem dono, e o dono é o que já existe:

| o que a SPEC precisa | quem já é o dono | caminho |
|---|---|---|
| ledger da cobrança | `billing_sent_log` + `billing_reservar_obrigacao` | `backend/supabase/migrations/20260907_01_*.sql` |
| porta de saída | `send_to_client_guarded` → `_entregar_agora` | `backend/app/services/platform_outbound.py:1070`, `:1439` |
| fatiar / não fatiar mensagem | `WhatsappService.send_message(..., bloco_unico=)` | `backend/app/services/whatsapp_service.py:131-160` |
| contador de vazão | `record_platform_send` → `platform_sends` | `platform_outbound.py:301-330` |
| fila de trabalho de portal | `portal_jobs` + `_candidatos_da_fila` + `_tentar_claim` | `backend/portal_worker/worker.py:982-1019` |
| sessão de portal | `portal_sessions` + `_load_session_bundle`/`_save_session_state` | `worker.py:240-304` |
| credencial e saúde da conta | `portal_accounts` + `POST /portal/credentials` | `backend/app/api/portal.py:146-183` |
| prova do desfecho | `_prova_do_desfecho` → `_materializar_provas` → bucket `portal-evidence` | `worker.py:411`, `:428`, `:884` |
| classificação de login | `interpret_login` de cada journey | `allianz_corretor.py:693`, e as 5 irmãs |
| incidente para a corretora | `_incidente` → `agent_activities` | `billing_collection.py:1333` |
| agendamento | a própria rotina diária | `routine_engine.py` |

### 3.1 O contrato lógico, sem obrigar tabela nova

```text
rotina (equipe) em company X
  → canário de login dos 6 portais            [B3] portal_jobs.journey='login_check'
  → portais com health OK entram              [B3] portal_accounts.health
  → cobranca_sweep por portal                 (como hoje)
  → itens + boletos                           (como hoje)
  → fila_de_cobranca (retém com motivo)       (como hoje)
  → AGRUPAR POR SEGURADO  (segurado_chave|portal) [B1] NOVO — 1 grupo = 1 mensagem
  → ordenar_para_entrega (grupo pelo mais velho)
  → por GRUPO: regra de N dias por segurado   [B1] NOVO
  →   por PARCELA: reserva atômica            (como hoje — a reserva NÃO agrupa)
  → 1 nota interna + 1 texto + N PDFs         [P0] bloco_unico
  → governador conta MENSAGENS, não parcelas  [P0]
  → estado por componente no ledger           (como hoje)
  → relatório: motivo de cada portal, PII mascarada   [P0][B4]
```

🔴 **A reserva continua por parcela.** Agrupar é decisão de ENTREGA; reservar é decisão de OBRIGAÇÃO. Uma reserva por grupo apagaria a identidade `(company_id, portal_key, recibo)` que a EXTRA-001 construiu e reabriria "cobrar de novo trocando o agrupamento".

### 3.2 Multi-tenant (CLAUDE.md §7)

Todo contrato novo carrega `company_id` explícito:
- `agrupar_por_segurado` é função pura sobre itens de **uma** execução, e a execução já é de uma rotina de uma corretora — o guarda mistura itens de dois `company_id` na entrada e exige que a função **nunca** produza um grupo com dois tenants (G7).
- A consulta dos N dias filtra `company_id` **no código e no índice** (`WHERE send_mode='real'`, prefixo `company_id`).
- `portal_accounts.health` e `portal_sessions.health` já são tenant-scoped por chave composta; a leitura da tela passa `company_id` do servidor, nunca do cliente.
- A consulta das telas desconhecidas (B4) filtra `company_id` e nunca agrega entre corretoras.

---

## 4. BLOCO 0 — CONVERTER MEDINDO (antes de qualquer código)

> Este documento envelhece. Os números abaixo foram medidos em **13/09/2026** na revisão `a0bb5fe`. O executor **remede**, e **o número dele vence** (protocolo §5 ①).

### 4.1 Preflight, na ordem

```bash
git fetch origin
git rev-list --count HEAD..origin/main      # 🔴 tem de ser 0
git rev-list --count origin/main..HEAD      # ⚠️ o que ainda não subiu
git branch --show-current
git rev-parse HEAD                          # registrar no relatório
git status --short
```

### 4.2 As 15 premissas a remedir — cada uma com o comando

| # | premissa desta SPEC | comando / consulta | 📊 valor em 13/09 |
|---|---|---|---|
| 1 | o ledger nunca escreveu | `select count(*) from billing_sent_log` | **0** |
| 2 | a rotina está desligada e sem destino | `select is_active,next_run_at,config->>'send_mode', length(config->>'team_number'), length(config->>'attendant_name') from routines where config->>'kind'='billing_collection'` | `false` · `2026-09-14` · `test` · **0** · **0** |
| 3 | o governador contou 7 e o canal recebeu 28 | `select date_trunc('day',created_at)::date,count(*) from platform_sends where kind='billing' and created_at>='2026-09-09' group by 1` | 10/09 **7** · 11/09 **7** |
| 4 | o texto real vira mais de um balão | rodar `split_whatsapp_balloons` sobre `build_customer_message` (o motor, §12.2) | texto **331 ch → 2** · nota **322 ch → 2** · teste **517 ch → 3** · com `bloco_unico` → **1** |
| 5 | `error` é sempre nulo nos jobs | `select count(*) filter (where error is null), count(*) from portal_jobs` | **100%** nulo |
| 6 | o motivo existe em `evidence.message` | `select distinct portal_key,status,evidence->>'message' from portal_jobs where status in ('failed','needs_human') and finished_at>='2026-09-10'` | Mapfre: *"a MAPFRE recusou a credencial (autenticacao invalida)"* · Allianz: *"tela pos-login Allianz nao reconhecida"* |
| 7 | a sessão nunca vence | `select portal_key,health,verified_at from portal_sessions order by verified_at` | 8 linhas, **8 `ok`**; Allianz **17/08**, Zurich **14/08** |
| 8 | `portal_accounts.health` não tem escritor | `select distinct health,count(*) from portal_accounts group by 1` | **16 de 16 = `unknown`** |
| 9 | `available_at` é lido e nunca escrito | `select count(*) from portal_jobs where available_at is not null` | **0** |
| 10 | `attempts` é incrementado e nunca lido | `select max(attempts) from portal_jobs` + ler `worker.py:1017` e `:1001` | **1** |
| 11 | a PII está no relatório da execução | `select count(*) from routine_runs r join routines t on t.id=r.routine_id where t.config->>'kind'='billing_collection' and r.output_full like '%CPF/CNPJ%'` | **7** de 49 |
| 12 | os prints do desfecho existem e são a ÚNICA fonte do texto da tela | `select split_part(name,'/',2),count(*) from storage.objects where bucket_id='portal-evidence' and name like '%desfecho%' group by 1` **e** `select length(evidence->>'body_text'), length(evidence->>'debug_dom') from portal_jobs where status in ('failed','needs_human') and finished_at>='2026-09-10'` | 6 `done` · 4 `needs-human` · 2 `failed`; **`body_text` e `debug_dom` = 0 em todos** |
| 13 | ninguém enfileira `login_check` | `grep -n '"journey"' backend/app/services/billing_collection.py` | só `"cobranca_sweep"` (`:680`) |
| 14 | `tela_cega` tem escritor e não tem leitor | `select count(*) from tela_cega` + `grep -rn "tela_cega" backend --include=*.py` | **2 linhas**; zero leitores fora do escritor e dos testes (P-264) |
| **15** | 🔴 **quantos itens reais trazem `cpf_cnpj` preenchido** — é a chave do agrupamento E da janela de 7 dias | ler `routine_runs.output_full` das execuções de 10–11/09 (a seção "Clientes encontrados" imprime `CPF/CNPJ` por item) e contar preenchidos × `?`; e `grep -rn "cpf_cnpj" backend/portal_worker/journeys/*.py` para ver **quais das 6 journeys** o extraem | **NÃO MEDIDO na redação.** 📊 Só se confirmou que a Allianz preenche (`allianz_corretor.py:170, :1578`). Se o preenchimento for baixo, a regra da §B1.3 muda de tamanho — e é por isso que ela **não** depende do documento (ver B1.2) |

### 4.3 🔴 O achado do BLOCO 0 que muda o desenho do guarda da Allianz

📊 **O texto real das telas de portal não está no banco.** Nos 6 jobs `failed`/`needs_human` de 10–11/09, `evidence.body_text` e `evidence.debug_dom` têm **comprimento 0**. A única coisa que carrega a frase *"Acesso negado — Por favor, valide os dados introduzidos"* é a **imagem** em `portal-evidence/{job}/00-desfecho-needs-human.jpg`.

Consequências que a SPEC assume:

1. O corpus de telas reais de portal **nasce da leitura dos 12 prints** (`Read` da imagem pelo executor), transcrito para `backend/tests/corpus/telas_reais_de_portal/<portal>-<desfecho>-<aaaammdd>.txt`, no mesmo espírito de `backend/tests/corpus/telas_reais/` (protocolo §7.1: *"o texto vem do acervo, não da imaginação"*).
2. **O B4 passa a ter um pré-requisito:** o job precisa guardar o TEXTO da tela, redigido, e não só a foto — senão a próxima mudança de tela exige de novo que alguém abra uma imagem (o investigador do laudo I6 foi o primeiro a abrir, **2 dias depois**).
3. O guarda G3 roda `interpret_login` sobre esse texto — **com o motor, nunca com regex sobre a constante** (CLAUDE.md §9.4).

### 4.4 O dialeto do motor — a armadilha que o BLOCO 0 tem de refutar

`allianz_corretor._norm` (`:24-26`) faz `NFKD → ascii → lower → colapsa espaços`. Logo:

```
✅  "acesso negado"          casa
✅  "valide os dados"        casa
❌  "Acesso negado"          NÃO casa (maiúscula)
❌  "validação"              NÃO casa (o acento some antes)
```

🔴 **Escrever a frase com acento ou com maiúscula na `_FAIL` produz um padrão que nunca casa e um guarda que fica verde porque o teste normaliza do mesmo jeito errado.** É a lição da SPEC-083 (CLAUDE.md §9.4): *"um padrão medido com um motor e aplicado com outro é um padrão sobre outra coisa"*. O guarda G3 exige **ZERO** classificação "não reconhecida" para o texto real do print **e** um controle que prove que a tela de dashboard continua `done`.

### 4.5 GATE B0

Matriz **premissa → observação nova → comando → decisão**, o mapa de efeitos, a autorização do canário e a lista das linhas do diagnóstico que mudaram de número (§12.1). Nenhum achado não reproduzido é vendido como incidente confirmado. **MUTAÇÃO B0:** o aquecimento recebe duas afirmações deliberadamente falsas, assinadas (§6 do prompt de abertura), e precisa refutá-las com comando.

---

## 5. BLOCO P0 — A MENSAGEM CHEGA INTEIRA E A FALHA FALA PORTUGUÊS
### Implantável no 1º dia · não depende das senhas novas

> 🔴 **Este bloco é a condição de reativar a rotina** (D-PILOTO-18: reativar antes = avalanche picotada na atendente, nota 25).
>
> ⚠️ **A equivalência de nomes, para ninguém se perder:** a decisão D-PILOTO-18 chama de **"BLOCO 0"** o bloco implantável no primeiro dia. Nesta SPEC, **BLOCO 0 é a medição** (§4, sem código) e o implantável é o **BLOCO P0** (§5). **"BLOCO 0 da D-PILOTO-18" = "BLOCO P0 desta SPEC".** A condição de reativar a rotina é **este** bloco estar no ar.

### P0.1 · `bloco_unico=True` nos três textos

**Contrato.** A decisão "isto é documento, não é conversa" mora em **um lugar só**, e o lugar é o `kind`:

```python
# backend/app/services/platform_outbound.py (perto de _entregar_agora)
#: Mensagens que são DOCUMENTO e não fala. Documento vai inteiro.
#: 🔴 Por que `kind` e não um parâmetro novo: a entrada da fila Redis carrega
#: `kind` e NÃO carregaria uma flag nova (P-E001-FILA-SEM-AUTORIZACAO-DE-AUXILIAR
#: mede exatamente isso). Um parâmetro se perderia no replay e a mensagem
#: voltaria a sair picotada — sem ninguém ver.
MENSAGENS_QUE_SAO_DOCUMENTO = frozenset({
    "billing_equipe",        # o texto final que a atendente repassa
    "billing_equipe_nota",   # a nota interna
    "billing_cliente",       # o texto ao segurado, quando o modo cliente for ligado
})

def e_documento(kind: str) -> bool:
    return str(kind or "") in MENSAGENS_QUE_SAO_DOCUMENTO
```

- `platform_outbound.py:1478-1479` passa `bloco_unico=e_documento(kind)` ao `send_message`.
- `billing_collection.py:1153` (modo teste, que não passa pela porta) passa `bloco_unico=True` direto.
- ⛔ **Não** ligar `bloco_unico` para todo mundo: `saudacao_do_religamento.py:541` e `dispatch_followup.py:282` chamam a mesma porta e falam com o SEGURADO como gente. Balão curto existe por um motivo bom, e ele continua valendo para conversa (`whatsapp_service.py:139-152`).

📊 **O efeito, medido com o motor em 13/09:** nota 322 ch → 2 balões → **1**; texto 331 ch → 2 balões → **1**; teste 517 ch → 3 balões → **1**. Em `equipe`, o segurado deixa de gerar **5** mensagens e passa a gerar **3** (nota + texto + PDF).

### P0.2 · O motivo do portal aparece

**Contrato.** `billing_collection.py:2330-2331` passa a ler o mesmo lugar que a linha vizinha:

```python
if status in {"failed", "timeout"}:
    motivo = (job.get("evidence") or {}).get("message") or job.get("error") or "sem motivo registrado"
    blockers.append(f"portal {job.get('portal_key')}: {status} — {motivo}")
```

🔴 A ordem importa: `evidence.message` **primeiro**, porque 📊 `error` é NULL em 100% dos jobs da história (`worker.py:944` o limpa) e `evidence.message` está preenchido em 100% deles. Manter `error` como segunda opção preserva o caso do requeue.

**O que a atendente passa a ler, hoje, sem nenhuma senha nova:**
`portal mapfre_corretor: failed — a MAPFRE recusou a credencial (autenticacao invalida)`

### P0.3 · A Allianz para de mentir

**Contrato.** `allianz_corretor.py:659-667`, `_FAIL` ganha as frases reais, **no dialeto do `_norm`** (§4.4):

```python
_FAIL = (
    "senha invalida", "usuario invalido", "usuario ou senha invalida",
    "credenciais invalidas", "login invalido", "dados incorretos", "nao autorizado",
    # 📊 13/09/2026 — lidas no print real do job de 11/09
    # (portal-evidence/{job}/00-desfecho-needs-human.jpg). A frase da tela é
    # "Acesso negado — Por favor, valide os dados introduzidos."; `_norm` tira
    # acento e maiúscula ANTES da comparação, então é assim que ela se escreve aqui.
    "acesso negado",
    "valide os dados",
)
```

E o teste `backend/tests/test_spec023_allianz_login.py:113-114` para de exercitar a frase inventada `"Usuario ou senha invalida"` como se fosse o acervo: passa a exercitar **o texto transcrito do print**, com a frase inventada mantida **como controle de compatibilidade** (ela continua tendo de dar `failed`).

⚠️ **A varredura das 6 journeys** (§9.4 do diagnóstico): o executor roda `interpret_login` de **cada uma das 6** contra **cada um dos 12 prints transcritos** e registra a matriz no relatório. O que se procura é o inverso do óbvio: uma journey que classifique `done` uma tela de login (falso positivo) é pior que uma que diga "não reconheço".

### P0.4 · Sem o nome da atendente, a rotina não sai

**Contrato.** `normalize_billing_config` (`billing_collection.py:449-508`):

```python
elif send_mode in MODOS_REAIS and not str(raw.get("attendant_name") or raw.get("nome_atendente") or "").strip():
    send_mode = MODO_RETIDO
    retido_motivo = ("sem o nome de quem assina a mensagem: preencha 'Quem assina' "
                     "na tela do Auxiliar — o segurado não pode receber "
                     "'Aqui é a nossa equipe'")
```

🔴 **Reter, não default.** O default `"nossa equipe"` de `:500` continua existindo para os modos `test`/`none` (onde o destino é a própria corretora e nada vaza), e deixa de valer para `equipe`/`cliente`. 📊 A frase que o Founder leu em 10/09 — *"Aqui é a nossa equipe, da Resulta"* — foi reproduzida literalmente pelo motor em 13/09 com `attendant_name=''`.

O campo ganha rótulo humano na tela (`components/auxiliares/PainelDeRotinas.tsx`): **"Quem assina a mensagem"**, com ajuda *"o nome que o segurado vai ler; use o nome de quem atende"*.

### P0.5 · O governador conta o que o canal recebeu

🔴 **A decisão, tomada aqui e não deixada em aberto: UMA LINHA POR COMPONENTE, com `kind` próprio. Nem por balão, nem por coluna nova.**

`platform_sends` **não é só do governador**: 📊 13/09 ela tem **4 escritores** (`billing_collection.py:1261`, `dispatch_router.py:244`, `platform_outbound.py:1494`, `dispatch_followup.py:320`) e **leitores humanos**:

| leitor | o que faz | o que 1 linha por BALÃO quebraria |
|---|---|---|
| `platform_outbound.py:1659-1682` `context_note_for` | pega os 30 últimos envios, filtra pelo telefone e monta o bloco `[CONTEXTO DA PLATAFORMA]` com **os 3 primeiros** (`hits[:3]`, por `summary`/`kind`) | 🔴 a **mesma** cobrança ocuparia os 3 lugares, e o agente perderia o contexto real do cliente |
| `app/core/heartbeat.py:311-320` (Central de Agentes) | conta produção por `kind` com filtro `in` — 📊 o comentário de 03/09 registra `billing 4` | um card contando balões diria que a cobrança produziu 4× mais |

E `record_platform_send(..., unidades=N)` exigiria **coluna nova** → migration → e o P0 **deixaria de ser implantável sem migration**, que é a razão de ele existir.

**Contrato.** Uma linha por componente que o canal recebeu, com `kind` que diz qual é:

| componente | `kind` | quem grava |
|---|---|---|
| o texto que a pessoa lê (a cobrança) | `billing` *(inalterado)* | `_entregar_agora`, como hoje |
| a nota interna à atendente | `billing_nota` | `_entregar_agora` |
| **cada boleto anexado** | `billing_doc` | `_entregar_agora`, **depois** do `send_document` aceito — hoje o PDF **não é contado em lugar nenhum** |

E os dois leitores são ajustados **junto**, no mesmo bloco:
- `context_note_for` ignora os `kind` de componente (`billing_nota`, `billing_doc`) ao montar as 3 linhas — a atendente e o cliente veem "a cobrança", não as peças dela;
- os cards de `heartbeat.py` continuam filtrando `kind='billing'`, então continuam contando **cobranças**, e passam a contar 1 por segurado em vez de 1 por parcela (efeito do agrupamento do B1). Isso vai escrito no gate.

⚠️ **E o balão?** Depois de P0.1 o texto é **1 balão por construção** (📊 medido: 331 ch → 1). Se `_fatiar_documento` algum dia devolver mais de um pedaço — texto acima de 3.500 caracteres —, isso é **sinal de defeito**, não de contabilidade: vira linha de log e blocker no relatório, nunca linhas a mais na tabela.

📊 Depois, para 7 parcelas de 5 segurados em `equipe`: **5** linhas `billing` + 5 `billing_nota` + **7** `billing_doc` = 17 linhas, contra 7 hoje — e o PDF deixa de ser invisível.

### 🎯 GATE P0

```
① teste que afirma 1 BALÃO para o template REAL, pelos dois caminhos, e que CONSEGUE falhar
   (mutação M1: tirar `billing_cliente` da tabela de kinds → vermelho)
② um job `failed` com `error IS NULL` e `evidence.message` preenchido → o motivo aparece no relatório
   (o corpus é a linha real da Mapfre de 11/09)
③ `interpret_login` das 6 journeys sobre os 12 prints transcritos → ZERO "tela não reconhecida"
   para tela de credencial recusada; CONTROLE: o dashboard real continua `done`
④ `attendant_name` vazio em `equipe` → rotina RETIDA, zero mensagens, motivo em português
⑤ rotina da Resulta em `test` (destino = a própria corretora) → 1 balão por texto e
   `platform_sends` com uma linha por COMPONENTE (`billing` · `billing_nota` · `billing_doc`)
⑥ 🔴 OS LEITORES, no mesmo gate: `context_note_for` sobre um cliente com 1 cobrança + 3 boletos
   devolve UMA linha de cobrança (não três); os cards de `heartbeat.py` que filtram `kind='billing'`
   continuam contando cobranças e nada mais entrou na conta deles
```

**Implantação 1 (smith-api):** este bloco sozinho. Só depois disto o Founder reativa a rotina (§9.1).

---

## 6. BLOCO 1 — NINGUÉM É COBRADO DUAS VEZES

### B1.1 · A dedup vale sempre; a flag passa a DESLIGAR

**Contrato.** `billing_collection.py:1059-1065`:

```python
#: 🔴 INVERTIDA em 13/09/2026 (diagnóstico §9.4; CLAUDE.md §9.3). A de 17/08 — "em teste não
#: deduplica, porque em teste o destino é a própria corretora e o que se quer é
#: REPETIR" — produziu, em 10 e 11/09, os MESMOS 7 boletos nos dois dias, e a
#: tela de Pendências vazia e correta ao mesmo tempo. Um controle que não pode
#: falhar não é controle (CLAUDE.md §9.3). O padrão passa a ser DEDUPLICAR;
#: quem quer repetir num dia de demonstração liga a flag.
FLAG_DEDUP_TESTE_DESLIGADA = "BILLING_DEDUP_TEST_DISABLED"

def dedup_de_envio_ativa(send_mode: Any, env: Optional[Dict[str, str]] = None) -> bool:
    modo = str(send_mode or "").strip().lower()
    if modo != "test":
        return True                                  # ⛔ a flag NUNCA toca modo real
    return not _truthy((env if env is not None else os.environ).get(FLAG_DEDUP_TESTE_DESLIGADA))
```

⚠️ **A regra do comando (protocolo §0.4):** `grep -rn "BILLING_DEDUP_TEST_ENABLED"` na árvore INTEIRA (código, testes, docs, `.env.example`, PENDENCIAS). Sobrevivente = defeito.

### B1.2 · `agrupar_por_segurado` — 1 mensagem, N boletos

**Contrato.** Função pura, nova, em `billing_collection.py`, entre `fila_de_cobranca` (termina em **`:424`**) e `ordenar_para_entrega` (**`:334`**):

🔴 **Duas chaves, e elas são diferentes de propósito** — a confusão entre as duas é o que produz "o segurado sem CPF nunca é limitado":

```python
def segurado_chave(item: Dict[str, Any]) -> str:
    """QUEM é o segurado — independente de seguradora. É o que vai para o ledger.

    🔴 O nome da coluna é `segurado_chave`, e NÃO `cpf_cnpj`, porque o valor nem
    sempre É um documento (CLAUDE.md §12.1: campo cujo nome mente reinfecta todo
    leitor seguinte). O prefixo diz de onde a identidade veio, e é isso que a
    mensagem de retenção mostra para a pessoa poder discordar.

    ⚠️ Sem documento, a identidade é o NOME normalizado. Isso pode unir dois
    homônimos reais e segurar uma cobrança legítima por N dias — e é o erro que
    se escolhe: não cobrar alguém por uma semana é recuperável; cobrar duas
    vezes o mesmo segurado é o defeito que esta SPEC existe para fechar.
    A retenção diz `por nome` e a pessoa libera pela tela se discordar.
    """
    doc = so_digitos(item.get("cpf_cnpj"))
    if doc:
        return f"doc:{doc}"
    nome = _norm_txt(item.get("cliente_nome") or item.get("nome_segurado"))
    return f"nome:{nome}" if nome else f"recibo:{str(item.get('recibo') or '').strip()}"


def chave_do_grupo(item: Dict[str, Any]) -> str:
    """QUEM + ONDE — é o que decide o que cabe numa MESMA mensagem.

    🔴 Inclui o portal, porque o texto nomeia a seguradora ("A Seguradora {x}
    informou") e um grupo com duas seguradoras exigiria uma mensagem que ninguém
    escreveu e o Founder não aprovou (B1.5).
    ⚠️ E o mesmo segurado em DUAS seguradoras não recebe duas mensagens: quem
    impede é a janela de N dias (B1.3), que usa `segurado_chave` — SEM o portal.
    Uma regra por pergunta.
    """
    return f"{segurado_chave(item)}|{str(item.get('portal') or '').strip().lower()}"


def agrupar_por_segurado(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Devolve GRUPOS, na ordem da dívida mais velha do grupo.

    Cada grupo: {"chave_do_grupo", "segurado_chave", "cliente_nome", "portal",
                 "parcelas": [item, ...]}
    A ordem entre grupos é a de `ordenar_para_entrega` aplicada à parcela mais
    VELHA de cada grupo — a fila continua significando o que significava.
    """
```

**Onde entra, nos dois caminhos:**
- real: `_entregar_cobranca_real`, hoje `for indice, item in enumerate(ordenar_para_entrega(fila))` (**`:1544`**) → passa a iterar grupos;
- teste: `_send_test_messages`, hoje `a_enviar = ordenar_para_entrega(items)` (**`:1119`**) → idem.

🔴 **Os dois, de propósito.** Se o modo teste não agrupar, o Founder ensaia uma coisa e a atendente recebe outra — que foi exatamente o defeito de 10/09.

**O que muda na entrega de um grupo:**
- **1** nota interna (que passa a listar as N parcelas);
- **1** texto final (plural quando N > 1 — §6.3);
- **N** documentos, um por parcela, cada um com `boleto_document_name(item)`;
- **N** reservas, uma por parcela, **antes** do primeiro efeito do grupo. Perdeu a reserva de uma parcela → **essa parcela sai do grupo** e o grupo segue com as outras; perdeu todas → o grupo inteiro não sai;
- **1** passagem pelo governador por grupo (hoje é uma por parcela) — é menos espera e é mais honesto: o espaçamento existe para proteger o *interlocutor*, e o interlocutor é um só.

📊 O caso medido: 4 parcelas do mesmo CNPJ → **1 mensagem + 4 PDFs**, no lugar de 4 abordagens.

### B1.3 · Uma cobrança por segurado a cada N dias

**Contrato.**

```python
#: D-PILOTO-18 (13/09): N = 7 (nota 85 × 3 dias 60 × 14 dias 70). Na tela, ajustável por corretora.
DIAS_ENTRE_COBRANCAS_PADRAO = 7

def _segurados_cobrados_recentemente(client, company_id: str, dias: int) -> Dict[str, str]:
    """`{segurado_chave: data_iso}` dos segurados já cobrados na janela.

    🔴 A leitura é por `segurado_chave` — SEM o portal. É isso que faz a janela
    valer ENTRE seguradoras, que é a pergunta que ela responde.
    🔴 Falha de leitura LEVANTA — nunca devolve vazio. Vazio significaria
    "não cobrei ninguém", e a resposta a isso seria cobrar todo mundo de novo
    (R04 da EXTRA-001; é a mesma disciplina de `_obrigacoes_reais`).
    ⚠️ Estados que CONTAM como cobrado: aceito_pelo_canal · entregue_equipe ·
    parcial · incerto. `falhou`, `adiado`, `suprimido` e `reservado` NÃO contam
    — ninguém recebeu nada.
    """
```

- O grupo cuja `segurado_chave` está na janela é **retido**, com motivo legível, a data e **de onde veio a identidade**: *"este segurado já foi cobrado em 11/09 (regra de 1 cobrança a cada 7 dias, identificado por CPF/CNPJ) — volta em 18/09"* · *"…(identificado por NOME, porque a seguradora não devolveu o documento) — se não for a mesma pessoa, libere pela tela"*. **Nada some** (CLAUDE.md §11.1).
- 🔴 **A regra cobre TODO segurado, com ou sem documento.** Sem documento, a identidade é o nome normalizado (B1.2). Um item sem documento **e** sem nome cai no recibo — que nunca repete —, e aí sim a janela não o limita; isso vai escrito no relatório, contado.
- 📊 **Quanto disso é real ainda não se sabe:** a premissa 15 do BLOCO 0 mede o preenchimento de `cpf_cnpj` no acervo. Se for alto, a janela é quase toda por documento; se for baixo, o fallback por nome passa a ser a regra — e a frase da retenção é o que deixa a pessoa discordar.
- ⚠️ Não é uma reserva: a janela é de 7 dias e uma corrida de milissegundos é imaterial. Quem protege a parcela continua sendo a reserva atômica.

### B1.4 · A migration

Arquivo: `backend/supabase/migrations/20260914_01_spec_extra0016_cobranca_por_segurado.sql`.
**Antes de escrevê-la, ler `docs/canon/MIGRATIONS-AUTHORITY.md` inteiro** (CLAUDE.md §8).

```sql
-- =============================================================================
-- MIGRATION: spec_extra0016_cobranca_por_segurado
-- SPEC:      SPEC-EXTRA-001.6 — B1 "ninguém é cobrado duas vezes"
-- AUTOR:     <executor>                           DATA: 2026-09-14
-- OBJETIVO:  o ledger passa a saber DE QUEM é a parcela, para a regra de N dias
--
-- EXPAND-FIRST: sim   ·   DESTRUTIVA: não   ·   IDEMPOTENTE: sim
--
-- 📊 MEDIDO EM 13/09/2026, antes de uma linha de SQL:
--      select count(*) from public.billing_sent_log;                    -> 0
--      select count(*) from public.billing_sent_log where send_mode='real'; -> 0
--    A tabela está VAZIA: não há backfill, e a coluna nova nasce nula sem mentir
--    sobre nenhuma cobrança passada.
--
-- 🔴 POR QUE A FUNÇÃO GANHA UMA VERSÃO DE 13 ARGUMENTOS EM VEZ DE UM DEFAULT:
--    `CREATE OR REPLACE` com um parâmetro a mais NÃO substitui a função — cria
--    uma SOBRECARGA. Se o novo parâmetro tivesse DEFAULT, uma chamada com 12
--    argumentos passaria a casar com as DUAS e o Postgres devolveria 42725
--    (ambiguous function call) — em produção, na hora de reservar, com o boleto
--    na mão. Sem default, a chamada de 12 resolve só na antiga e a de 13 só na
--    nova: expand-first de verdade. A antiga é derrubada por uma migration
--    POSTERIOR, depois que o código novo estiver no ar (P-E0016-RESERVA-12-ARGS).
-- =============================================================================

-- ----------------------------------------------------------------- APPLY -----
ALTER TABLE public.billing_sent_log
  ADD COLUMN IF NOT EXISTS segurado_chave text;

COMMENT ON COLUMN public.billing_sent_log.segurado_chave IS
  'QUEM é o segurado, para a regra "1 cobrança por segurado a cada N dias" (D-PILOTO-18). Formato: "doc:<digitos>" quando a seguradora devolveu CPF/CNPJ, "nome:<normalizado>" quando não devolveu, "recibo:<n>" quando não há nem nome. 🔴 NÃO se chama cpf_cnpj porque nem sempre É um documento — nome que mente reinfecta todo leitor seguinte (CLAUDE.md §12.1). ⛔ Dado da PRÓPRIA CORRETORA: NUNCA vai para log, relatório de execução, artifact, prompt ou RAG (CLAUDE.md §7).';

-- A janela por segurado. 🔴 SEM o portal na chave: a pergunta é "já falei com
-- esta pessoa esta semana?", e ela vale ENTRE seguradoras. Com o company_id na
-- frente, nenhuma leitura atravessa tenant (CLAUDE.md §7).
CREATE INDEX IF NOT EXISTS billing_sent_log_segurado_idx
    ON public.billing_sent_log (company_id, segurado_chave, sent_at DESC)
 WHERE send_mode = 'real';

-- 🔴 O CORPO DA FUNÇÃO NÃO SE COPIA À MÃO. Gere-o do objeto que está no banco e
--    acrescente só o parâmetro e o campo do INSERT:
--        select pg_get_functiondef(p.oid) from pg_proc p
--          join pg_namespace n on n.oid = p.pronamespace
--         where n.nspname='public' and p.proname='billing_reservar_obrigacao';
--    Copiar 60 linhas de plpgsql à mão é como o `EXCEPTION WHEN unique_violation`
--    da 20260907_01 desaparece sem ninguém ver — e com ele a retenção de
--    `colisao_recibo`, que é produto.
CREATE OR REPLACE FUNCTION public.billing_reservar_obrigacao(
    p_company_id uuid, p_portal_key text, p_recibo text, p_modalidade text,
    p_to_phone text, p_to_last4 text, p_cliente_nome text, p_apolice_susep text,
    p_routine_id uuid, p_work_run_id uuid, p_integration_id uuid, p_canario boolean,
    p_segurado_chave text                -- 🔴 13º: sem DEFAULT, de propósito
) RETURNS TABLE(id uuid, ganhou boolean, status text)
LANGUAGE plpgsql SET search_path = public, pg_temp
AS $function$
-- corpo GERADO de pg_get_functiondef, com `segurado_chave` no INSERT.
-- ⚠️ Conferir que o `EXCEPTION WHEN unique_violation` e o ramo `colisao_recibo`
--    vieram junto — um diff contra o texto gerado prova isso.
$function$;

-- ---------------------------------------------------------------- VERIFY -----
-- V0) 🔴 o corpo novo é o antigo + o campo — e nada a menos
--   select pg_get_functiondef(p.oid) ... ; diff contra o corpo da 20260907_01
--   esperado: as únicas diferenças são o parâmetro e a coluna do INSERT;
--             `EXCEPTION WHEN unique_violation` e `colisao_recibo` presentes
-- V1) a coluna existe e é nula
--   select column_name, is_nullable from information_schema.columns
--    where table_schema='public' and table_name='billing_sent_log' and column_name='segurado_chave';
--   esperado: 1 linha, is_nullable='YES'
-- V2) o índice existe com o predicado certo
--   select indexdef from pg_indexes where indexname='billing_sent_log_segurado_idx';
--   esperado: contém "WHERE (send_mode = 'real'::text)"
-- V3) as DUAS assinaturas convivem, sem ambiguidade
--   select pg_get_function_identity_arguments(p.oid) from pg_proc p join pg_namespace n
--     on n.oid=p.pronamespace where n.nspname='public' and p.proname='billing_reservar_obrigacao';
--   esperado: 2 linhas — uma com 12 tipos, outra com 13
-- V4) 🔴 a reserva continua reservando, e agora grava o segurado
--   begin;
--     select * from public.billing_reservar_obrigacao(
--       (select id from public.companies order by created_at limit 1),
--       'verify_portal','VERIFY-0016','equipe',null,null,'VERIFY',null,null,null,null,true,'doc:00000000000');
--       -- esperado: ganhou=true, status='reservado'
--     select segurado_chave from public.billing_sent_log where recibo='VERIFY-0016';
--       -- esperado: 'doc:00000000000'
--     select * from public.billing_reservar_obrigacao(
--       (select id from public.companies order by created_at limit 1),
--       'verify_portal','VERIFY-0016','cliente',null,null,'VERIFY',null,null,null,null,true,'doc:00000000000');
--       -- esperado: ganhou=FALSE, mesmo id
--   rollback;   -- 🔴 o VERIFY não deixa lixo
-- V5) CONTROLE — a chamada de 12 argumentos ainda resolve, sem 42725
--   begin;
--     select * from public.billing_reservar_obrigacao(
--       (select id from public.companies order by created_at limit 1),
--       'verify_portal','VERIFY-0016-B','equipe',null,null,'VERIFY',null,null,null,null,true);
--       -- esperado: executa (não levanta ambiguous function call)
--   rollback;
-- V6) CONTROLE — nada do modo test mudou
--   select count(*) from public.billing_sent_log where send_mode='test';  -- esperado: 0
--
-- -------------------------------------------------------------- ROLLBACK -----
-- ⚠️ Só é seguro enquanto não houver linha `send_mode='real'` (📊 0 em 13/09).
--    Havendo, apagar a coluna apaga de quem era a cobrança já enviada — e as
--    mensagens não se desfazem. Nesse caso o rollback correto é pôr a rotina em
--    'none' na tela e deixar a coluna onde está.
-- drop function if exists public.billing_reservar_obrigacao(uuid,text,text,text,text,text,text,text,uuid,uuid,uuid,boolean,text);
-- drop index if exists public.billing_sent_log_segurado_idx;
-- alter table public.billing_sent_log drop column if exists segurado_chave;
-- =============================================================================
```

⛔ **Não aplicar antes do VERIFY escrito.** ⛔ Não tocar em `schema_completo.sql`, `upgrade_v6.2.sql`, `storage_buckets.sql`, nem em migration já aplicada. ✅ Atualizar `backend/supabase/migrations/MANIFEST.md`.

### B1.5 · 💭 A copy do plural — proposta, e o que o Founder decide

A mensagem padrão é **travada** (definida pelo Founder em 11/07, `billing_collection.py:81-92`). O agrupamento exige uma variante para N > 1. 💭 Proposta (ilustrativa; **não citável como fato**):

```
Olá {primeiro_nome},

Aqui é a {nome_atendente}, da {nome_corretora}, tudo bem?

A Seguradora {nome_seguradora} informou que as parcelas {lista_de_parcelas} do
seguro do {item_segurado} ainda estão pendentes.

Desta forma, a seguradora gerou novos boletos para pagamento pra você não ficar
sem cobertura, ok!?

Qualquer dúvida estou à disposição.

Seguem os boletos abaixo.
Apólice: {numero_apolice}
```

- `{lista_de_parcelas}` = `"2/6, 3/6 e 4/6"` (vírgula e "e" antes da última).
- N = 1 continua usando **exatamente** o template de hoje, byte a byte. O guarda prova isso.
- Apólices diferentes do mesmo segurado na mesma seguradora: a linha `Apólice:` vira `Apólices: A, B` e o `{item_segurado}` vira `"seus seguros"`. 💭
- **Caixa do Founder:** confirmar a redação. Sem resposta, vale a acima — não trava a execução.

### 🎯 GATE B1

```
① dedup ligada por padrão em `test`; `BILLING_DEDUP_TEST_DISABLED=1` desliga; a flag NÃO toca modo real
② `agrupar_por_segurado` sobre o ACERVO de 10–11/09 (corpus anonimizado): 4 parcelas do mesmo CNPJ = 1 grupo;
   dois segurados distintos nunca se fundem; sem documento o fallback por nome agrupa, e NÃO junta portais diferentes
   na mesma mensagem;
   dois `company_id` na entrada nunca produzem um grupo misto
③ N dias por `segurado_chave` (SEM o portal): mesmo segurado cobrado há 3 dias → retido com motivo, DATA e a
   ORIGEM da identidade (documento × nome); há 8 dias → cobrado. CONTROLE: um segurado SEM documento também é retido
④ a reserva continua POR PARCELA: 4 parcelas do grupo = 4 linhas no ledger, 1 mensagem
⑤ migration aplicada com VERIFY V1–V6 rodado no Postgres real, saída colada no relatório
⑥ rotina da Resulta em `test`, DUAS execuções seguidas → a segunda envia ZERO
```

---

## 7. BLOCO 2 — A SESSÃO MORRE E ALGUÉM FICA SABENDO

### B2.1 · TTL sobre `verified_at`

📊 A sessão da Allianz tem `verified_at = 17/08` e `health='ok'` — **27 dias** — porque `_save_session_state` (`worker.py:271-304`) só escreve **no sucesso**, e ninguém compara com o relógio.

**Contrato.** `_load_session_bundle` (`worker.py:240`) passa a devolver `None` quando `verified_at` é mais velho que `PORTAL_SESSION_TTL_HORAS` (💭 default **12**, configurável, clamp 1–72), registrando `evidence["sessao_vencida"] = {"verified_at": ..., "idade_h": ...}`. Sem storage injetado, a journey faz login limpo — que é o comportamento certo e o que teria descoberto a senha recusada **no dia 18/08**.

### B2.2 · `health` passa a ter escritor

**Contrato.** Depois do resultado da journey, para `login_check` e `cobranca_sweep`, o worker escreve o veredito nos dois lugares (`portal_sessions.health` e `portal_accounts.health`), com o mesmo vocabulário:

| valor | quando | quem lê |
|---|---|---|
| `ok` | login confirmado | tela, canário, rotina |
| `expirada` | a sessão foi injetada e o portal devolveu a tela de login | canário (tenta login limpo) |
| `credencial_recusada` | a journey classificou `failed` por credencial | 🔴 **breaker abre** (B3.3) · incidente · relatório |
| `pede_humano` | CAPTCHA / 2FA / tela desconhecida | canário · fila de telas (B4) |
| `fora_do_ar` | N falhas seguidas não-credenciais | breaker temporário |
| `unknown` | credencial recém-salva | 🔴 **é o meio-aberto** (B3.3) |

⚠️ `POST /portal/credentials` já grava `health='unknown'` a cada salvamento (`app/api/portal.py:165`). **Isso está certo e fica**: senha nova merece veredito novo. É o que fecha o ciclo do breaker sem inventar botão.

### B2.3 · `session_reused` diz a verdade

📊 `worker.py:812` grava `evidence["session_reused"] = True` no instante em que **injeta** o storage — antes de saber se ele vale. O job da Allianz de 11/09 carrega `session_reused` **e** terminou `needs_human`.

**Contrato** (CLAUDE.md §12.1 — *conserte o campo, não só o texto*):
- `evidence["session_injetada"] = True` no ponto atual (é o que de fato acontece ali);
- `evidence["session_reused"] = True` **só** depois de a journey confirmar login sem relogin;
- os dois convivem uma versão, e o `resumo_do_desfecho` usa o segundo.

### B2.4 · Allianz: o diagnóstico de sessão morta fica alcançável

📊 `cobranca_sweep` (`allianz_corretor.py:3755`) começa com `login = await login_check(...)` e, em `:3758-3759`, `if login.status != "done": return login`. O diagnóstico de sessão morta + relogin fresco vive em **`:3786`** — **depois do `return`**, e por isso nunca rodou nas 34 tentativas.

**Contrato.** Antes do `return`:

```python
login = await login_check(page, params, evidence)
if login.status != "done":
    # 🔴 UMA retentativa, nunca laço: entrada repetida é o que faz o portal
    #    bloquear a corretora. E credencial RECUSADA não é sessão morta —
    #    relogar com a mesma senha errada é bater na porta trancada.
    if login.status != "failed" and (await _diagnosticar_sessao_na_pagina(page, evidence)).get("morta"):
        if await _relogin_fresh(page, params, evidence, motivo="sessao morta no servidor"):
            login = await login_check(page, params, evidence)
    if login.status != "done":
        return login
```

### 🎯 GATE B2

```
① `verified_at` mais velho que o TTL → storage NÃO injetado e `sessao_vencida` na evidência
   (mutação M9: TTL ignorado → vermelho)
② `health` muda de `ok` para `credencial_recusada` no primeiro `failed` de credencial, nas DUAS tabelas
③ `session_reused` só é verdadeiro quando a sessão valeu — CONTROLE: o job real de 11/09, replayado,
   produz `session_injetada=True` e `session_reused` ausente
④ replay do `cobranca_sweep` com login `needs_human` → o diagnóstico de sessão morta É chamado;
   com login `failed` (credencial) → NÃO é chamado e não há relogin
```

---

## 8. BLOCO 3 — O PORTAL É VIGIADO ANTES DA ROTINA

### B3.1 · O canário de login, sem scheduler novo

📊 `login_check` existe nas 6 journeys (`journeys/__init__.py:205-226`) e **ninguém o enfileira**: `_enqueue_job` (`billing_collection.py:676-734`) escreve `"journey": "cobranca_sweep"` fixo.

**Contrato.** A própria rotina, no começo da execução, enfileira os `login_check` dos portais selecionados e espera por eles **antes** de abrir qualquer `cobranca_sweep`:

```text
execute_billing_collection_routine
  → enfileirar_canario_de_login(portais)        6 jobs, journey='login_check', priority alta
  → esperar (teto 💭 120 s por portal, em paralelo)
  → portais com veredito `ok`        → cobranca_sweep, como hoje
  → portais com outro veredito       → NÃO abre job; entra no relatório com a frase do estágio
```

Notas, com a conta escrita:
- **nota 88** — a rotina é diária, então "canário diário" e "prólogo da rotina" são o mesmo relógio; zero motor novo; e o veredito é de minutos antes, não de ontem;
- nota 65 — pendurar no `vigia_do_portal` (`backend/app/tasks/vigia_do_portal.py:306`): ele é watchdog de **vidros** (`.eq("portal_key","vidros_lanternas")`) e virar produtor muda o papel dele;
- nota 10 — scheduler próprio: proibido (CLAUDE.md §5).

💭 Custo: 6 jobs de navegador a mais por dia, ≈100 s cada.

### B3.2 · `available_at` + backoff com jitter

📊 `available_at` é lido em `worker.py:1001` e **nunca escrito** (0 linhas). `attempts` é incrementado em `:1017` e nunca lido para decidir nada (máx. 1 em toda a base).

**Contrato.**

```python
#: AWS, "Exponential Backoff and Jitter" (§13 E4): full jitter — sleep = random(0, base*2^n).
#: Teto BAIXO de propósito: tentativa repetida de login bloqueia a conta da corretora.
BACKOFF_BASE_S = 60
BACKOFF_TETO_S = 900          # 15 min
MAX_TENTATIVAS_DE_PORTAL = 3

def proximo_available_at(attempts: int) -> str: ...
```

- Falha **transitória** (timeout, rede, 5xx, tela que não carregou) → `status='queued'` + `available_at` futuro + `attempts+1`, até 3.
- ⛔ `credencial_recusada` **nunca** entra no backoff: não é transitória. É a *"accelerated circuit breaking"* do padrão (§13 E3) — a resposta de falha carrega informação suficiente para abrir o circuito imediatamente.
- `attempts >= MAX` → estado terminal com motivo, e o breaker do B3.3 decide.

### B3.3 · Circuit breaker por portal — com os três estados

Modelado no padrão da Microsoft (§13 E3), implementado **inteiro dentro de `portal_accounts.health`**:

| estado do padrão | aqui | efeito |
|---|---|---|
| **Closed** | `health='ok'` | a rotina abre `cobranca_sweep` normalmente |
| **Open** | `health='credencial_recusada'` ou `'fora_do_ar'` | 🔴 a rotina **não enfileira** aquele portal; escreve no relatório o que fazer; `opened_at` no `portal_sessions` |
| **Half-Open** | `health='unknown'` | uma tentativa (o `login_check` do canário). Passou → `ok`; falhou → volta a `Open` |

- `credencial_recusada` **só fecha por gesto humano**: salvar a senha nova põe `health='unknown'` (`app/api/portal.py:165`, que já faz isso hoje) e a próxima execução testa uma vez. É o meio-aberto sem um botão novo.
- `fora_do_ar` reabre sozinho depois de 💭 6 h (timer do padrão).
- 📊 O que isso teria evitado: a Allianz gastou ≈100 s/dia por 25 dias para produzir a mesma linha.

### B3.4 · O `health` aparece — nas duas telas

1. **Personalização > Conectores > Portais** (`app/dashboard/personalizacao/conectores/portais/page.tsx`): 📊 a rota já devolve `health` (`app/api/portal.py:141`) e o tipo da página já o declara (`:18`) — e **nada o renderiza**. Passa a mostrar, com palavra de gente e a ação ao lado:
   *"⛔ senha recusada pelo portal — atualize a senha aqui"* · *"⏳ não verificado ainda"* · *"✅ entrou hoje às 06:12"* · *"⚠️ fora do ar desde 11/09 08:30"*.
2. **Central de Agentes** (`app/admin/central-agentes/page.tsx`, alimentada por `backend/app/api/admin_spec034.py:56 /agents-status`): um grupo **"Portais das seguradoras"**, um card por portal, com **última verificação · taxa de sucesso em 7 dias · motivo da última falha**. Mesma palavra, mesma fonte — o guarda exige que as duas telas leiam o mesmo campo.

### 🎯 GATE B3

```
① a rotina enfileira 6 `login_check` ANTES de qualquer `cobranca_sweep`, e um portal reprovado
   não gera job de varredura (mutação M10: breaker ignorado → vermelho)
② salvar credencial põe `health='unknown'` e a execução seguinte testa UMA vez (meio-aberto)
③ `available_at` escrito com jitter (duas chamadas com o mesmo `attempts` dão valores diferentes),
   teto 3 tentativas, e ZERO backoff para credencial recusada (mutação M11)
④ as duas telas mostram a MESMA palavra vinda do MESMO campo
```

---

## 9. BLOCO 4 — A PROVA TEM LEITOR

### B4.1 · O texto da tela passa a existir

📊 A causa raiz de "ninguém vê a prova" não é falta de tela: é que **o texto da tela não é gravado** (`body_text` e `debug_dom` = 0 em todos os 6 jobs). A foto existe; a palavra, não.

**Contrato.** Em todo desfecho não-`done` de portal, junto com a foto:

```python
evidence["tela"] = {
    "texto": redigir_texto_de_tela(await _body_text(page))[:2000],
    "hash": sha256(_norm(texto))[:16],     # a mesma normalização do motor da journey
    "url": url_sem_query,
    "prova": "portal-evidence/{job}/00-desfecho-*.jpg",
}
```

`redigir_texto_de_tela` reaproveita `portal_worker/redaction.py` (que hoje cobre o envelope JSON) e mascara CPF/CNPJ, e-mail e telefone **antes** de o texto entrar na evidência.

### B4.2 · A fila de telas desconhecidas — e o leitor, no mesmo dia

🔴 **Nenhuma tabela nova.** P-264 é a prova de que uma fila sem leitor não é fila: 📊 `tela_cega` tem **2 linhas** e **zero leitores** fora do escritor e dos testes, desde 26/08.

A fila é uma **consulta** sobre `portal_jobs`, agrupada por `evidence.tela.hash`, e o leitor nasce com ela:

```sql
-- "telas que eu não reconheço", por corretora e portal
select portal_key, evidence->'tela'->>'hash' as tela, count(*) as vezes,
       max(finished_at) as ultima, min(evidence->'tela'->>'texto') as amostra
  from public.portal_jobs
 where company_id = :company_id and status in ('needs_human','failed')
   and evidence->'tela'->>'hash' is not null
 group by 1,2 order by vezes desc;
```

Os leitores, os dois no dia 1:
1. **o card da Central de Agentes** do B3.4 ganha a linha *"3 telas que eu não reconheço — a mais frequente vista 12×"*, com o link do print;
2. **o relatório da rotina** ganha uma linha por tela nova do dia.

Nota: consulta com leitor **90** × tabela nova com leitor 70 × tabela nova sem leitor **0** (proibido por P-264).

### B4.3 · O print sai redigido

📊 O print da Mapfre grava o **CPF do corretor em claro**; `redaction.py` cobre o JSON, não a imagem.

**Contrato.** A máscara é aplicada **no DOM, antes da foto** — não na imagem depois:

```python
# antes de `page.screenshot`, quando o motivo é login/credencial
await page.evaluate("""() => {
  document.querySelectorAll('input').forEach(i => {
    const t = (i.type||'').toLowerCase();
    if (t === 'password' || t === 'text' || t === 'email' || t === 'tel') i.value = '••••••••';
  });
}""")
```

Nota: mascarar no DOM antes da foto **92** × borrar a imagem depois 40 (custo e dependência nova) × não guardar a foto 20 (perde a única prova que existe).
E: a URL assinada da evidência ganha TTL curto (💭 15 min) e **nunca** é anexada a mensagem.

### B4.4 · PII fora de `routine_runs.output_full`

📊 7 de 49 execuções têm `CPF/CNPJ` em claro em `output_full`, escrito por `_format_report` (`billing_collection.py:1885-1891`, seção "Clientes encontrados") e gravado em `routine_engine.py:362-367`.

**Contrato.** No relatório da execução, `cpf_cnpj` e `whatsapp` saem **mascarados** (`_mascarar_documento`, que já existe em `:1931`, e os 4 últimos dígitos do telefone). O que **não** muda:
- a **nota interna** à atendente continua com o WhatsApp legível (`_whatsapp_legivel`, `:1350`) — ela precisa discar;
- o **ledger** continua guardando `to_phone` e agora `segurado_chave`, com o comentário que diz que eles não saem dali.

Três níveis de exposição, de propósito: ledger (tenant, comentado) → nota à atendente (o número dela) → relatório e artifact (mascarados).

🔴 **E o que já está gravado?** 📊 **7 de 49** execuções têm CPF/CNPJ em claro em `routine_runs.output_full` (escritas por `:1891`). Mascarar daqui para a frente não apaga o que já está lá. Duas saídas, e a SPEC escolhe a primeira:

- **`20260914_03_spec_extra0016_redigir_output_full.sql`** — um `UPDATE` de redação sobre as 7 linhas, com **APPLY / VERIFY / ROLLBACK escritos antes**:
  - APPLY: `update routine_runs set output_full = regexp_replace(output_full, '(CPF/CNPJ )[0-9./-]{11,18}', '\1•••', 'g') where id in (...)` — 🔴 **a lista de ids é fixada por um SELECT rodado antes**, nunca um `where like` aberto, para o UPDATE não crescer sozinho;
  - VERIFY: `select count(*) ... where output_full like '%CPF/CNPJ%' and output_full ~ 'CPF/CNPJ [0-9]'` → esperado **0**; e a contagem de linhas afetadas = 7;
  - ROLLBACK: 🔴 **não existe** — a redação é irreversível por construção. Por isso o APPLY grava antes um `select id, md5(output_full) from routine_runs where id in (...)` no relatório, e a decisão é registrada: **o dado apagado é PII de segurado que nunca deveria ter sido escrita ali**, e a mesma informação continua no ledger e na InfoCap. Irreversível **e** correto.
- Se o Founder preferir não tocar no histórico: `P-E0016-PII-LEGADA-NO-OUTPUT-FULL`, com o custo de esquecer escrito — *"7 relatórios de execução com CPF/CNPJ de segurado em claro, legíveis por qualquer sessão autenticada da corretora; e o número cresce toda vez que a rotina roda antes do conserto"*.

### 🎯 GATE B4

```
① todo desfecho não-`done` de portal grava `evidence.tela.texto` redigido + hash (mutação: redação
   desligada → o guarda acha um CPF de teste no texto → vermelho)
② a consulta da fila devolve as telas agrupadas e a Central de Agentes as MOSTRA
③ o print de tela de login sai com os campos mascarados — prova sobre uma página real de teste
④ `_format_report` não contém CPF/CNPJ inteiro nem telefone inteiro; CONTROLE: a nota interna CONTÉM
   o telefone (prova que o guarda consegue ver a diferença — CLAUDE.md §9.3)
```

---

## 10. BLOCO 5 — O CANÁRIO VIVO, O ROTEIRO E A DOCUMENTAÇÃO

### 10.1 Canário Q1–Q6 herdado — a dívida da EXTRA-001

📊 `P-E001-CANARIO-VIVO-NO-IMPLANTADO` e `P-PILOTO-11`: `BILLING_CANARIO_ALLOWLIST` e `CANARIO_TESTE_B` **já estão no smith-api desde 08/09**. Falta chamar `POST /api/admin/canario/extra001` (chave interna) e colar o resultado. **Esta SPEC fecha essa dívida** antes de acrescentar a sua.

| Q | o que prova | herdado de |
|---|---|---|
| Q1 | `equipe`: pacote chega a TESTE-B; ledger `entregue_equipe`, `canario=true` | EXTRA-001 |
| Q2a/Q2b | `cliente`: 0 envios até liberar; depois texto + PDF | EXTRA-001 |
| Q3 | reexecução: 0 envios | EXTRA-001 |
| Q4 | retorno "já paguei" → `contestado` + atividade | EXTRA-001 |
| Q5 | destino fora da allowlist → `fora_da_allowlist`, 0 envios | EXTRA-001 |
| Q6 | limpeza por id: ledger 0 · platform_sends 0 · atividades 0 · PDF removido | EXTRA-001 |

### 10.2 Q7–Q10 — o que esta SPEC acrescenta

| Q | o que prova | como |
|---|---|---|
| **Q7** | **1 mensagem inteira por segurado, com N boletos** | 2 itens sintéticos com o mesmo documento, mesmo portal → TESTE-B recebe **3** mensagens (nota, texto, 2 PDFs = 4 objetos, 1 balão cada) e **nenhuma** picotada |
| **Q8** | segunda execução no mesmo dia = **0** envios | repetir o job |
| **Q9** | a regra de 7 dias bloqueia o mesmo segurado na **outra** seguradora | 3º item sintético, mesmo documento, portal diferente → retido com motivo e data |
| **Q10** | o canário de login roda antes e o motivo aparece em português | executar com **Tokio, HDI, Yelum, Zurich**; Allianz e Mapfre só quando a senha chegar |

⛔ Só TESTE-A → TESTE-B. Documentos sintéticos, sem linha digitável acionável. Limpeza por `id + company_id + canario`.

### 10.3 Documentação e acompanhamento — obrigatórios, com um escritor por arquivo

1. `docs/canon/specs/SPEC-EXTRA-001.6-…md` (a definitiva) e `docs/canon/reports/SPEC-EXTRA-001.6-EXECUTION-REPORT.md` pelo template, **abrindo com o EXECUTION CARD** e com a telemetria de 5 linhas.
2. `FOUNDER-DECISIONS.md`: 📊 D-PILOTO-01…20 **já gravadas** em `c0aaf65`. O trabalho é **conferir** que o texto da 18 (`:1762`) e da 19 (`:1763`) descreve o que esta SPEC executa — e emendar a linha, com a diferença escrita, se divergir. ⛔ Não reescrever decisão do Founder por conta própria: divergência material vira pergunta na caixa.
3. `PENDENCIAS.md`: fechar `P-E001-CANARIO-VIVO-NO-IMPLANTADO`, `P-E001-Q4-VIVO-DEPENDE-DE-DEPLOY` e `P-PILOTO-11` com prova; abrir as desta SPEC (§14).
4. `CHANGE-ADDENDA.md`: tudo além do texto desta SPEC, classificado.
5. `ESTADO-DAS-SPECS.md`, `INDICE-DE-SPECS.md`, `EXECUTION-MASTER-PLAN.md`: a 001.6 e a fila de §15.
6. `backend/supabase/migrations/MANIFEST.md`.
7. **Dossiê:** https://claude.ai/code/artifact/afe1510d-f31c-4d13-9441-aa920ad2b868 — ler o HTML publicado **inteiro** antes de republicar com `url`; página da 001.6 na aba **Pilotos**; sem números de teste em claro. Sem ferramenta: atualizar `docs/canon/reports/dossies/dossies-autobrokers.html` e dizer **"publicação pendente"** com o passo exato. ⛔ Nunca alegar que o link foi atualizado.

---

## 11. OS GUARDAS — 12, cada um com a mutação que o deixa vermelho

> 🔴 **Teto de 12 guardas novos** (D-PILOTO-14). Todos sobre o **MOTOR** e sobre o **ACERVO real**. ⛔ Proibido teste que reimplementa a regra: quem afirma é a função do produto, não um helper do teste (CLAUDE.md §9.4). Todo guarda precisa **poder ficar vermelho** (§9.3).

| # | o guarda afirma | sobre o quê | **MUTAÇÃO que o deixa vermelho** |
|---|---|---|---|
| **G1** | o texto real da cobrança vira **1 balão** pelos dois caminhos | `send_message` + `build_customer_message` + `_nota_interna_para_a_equipe` reais | **M1** tirar `billing_cliente` de `MENSAGENS_QUE_SAO_DOCUMENTO` |
| **G2** | `failed` com `error IS NULL` e `evidence.message` cheio → o motivo aparece | a linha REAL da Mapfre de 11/09, em corpus | **M2** voltar `:2331` a ler só `error` |
| **G3** | `interpret_login` das 6 journeys sobre os 12 prints transcritos → ZERO "não reconhecida" para credencial recusada | corpus `telas_reais_de_portal/` | **M3** remover `"acesso negado"` do `_FAIL` |
| **G4** | `attendant_name` vazio em modo real → rotina RETIDA, zero envios | `normalize_billing_config` | **M4** devolver o default `"nossa equipe"` |
| **G5** | uma linha por componente (`billing` · `billing_nota` · `billing_doc`), o PDF contado, e `context_note_for` devolvendo **uma** linha de cobrança | `record_platform_send` + `context_note_for` + os cards de `heartbeat` | **M5** gravar o `billing_doc` com `kind='billing'` → o contexto do cliente volta a ser ocupado 3× |
| **G6** | dedup ON por padrão em `test`; a flag só desliga `test` | `dedup_de_envio_ativa` | **M6** inverter de volta o default |
| **G7** | agrupamento correto sobre o acervo; nunca funde tenants nem portais numa mensagem; `segurado_chave` **não** leva portal e `chave_do_grupo` leva | `agrupar_por_segurado` · `segurado_chave` · `chave_do_grupo` | **M7** pôr o portal em `segurado_chave` → a janela deixa de valer entre seguradoras |
| **G8** | a janela de N dias retém com motivo, data e **origem da identidade**; fora da janela, cobra; **um segurado sem documento também é retido** | o leitor do ledger | **M8** ignorar a janela |
| **G9** | sessão vencida não é injetada; `session_reused` só quando valeu | `_load_session_bundle` + worker | **M9** ignorar o TTL |
| **G10** | portal com breaker aberto não gera `cobranca_sweep`; senha nova reabre | prólogo da rotina + `/portal/credentials` | **M10** enfileirar assim mesmo |
| **G11** | backoff com jitter, teto 3, **ZERO** para credencial recusada | `proximo_available_at` | **M11** aplicar backoff à credencial recusada |
| **G12** | `_format_report` sem CPF/telefone inteiros; a nota interna **com** o telefone | `_format_report` + `_nota_interna_para_a_equipe` | **M12** desligar a máscara |

**Onde moram:** G1–G8 em `backend/tests/test_a_cobranca_prova_que_funciona.py` (novo, script no padrão dos irmãos); G9–G11 em `backend/tests/test_o_portal_diz_por_que_nao_entrou.py` (novo); G12 junto de G1–G8.
**Como rodam as mutações:** worktree próprio ou lock exclusivo, restauração **por cópia** (⚠️ a suíte restaura arquivos por cópia — lição registrada no relatório da EXTRA-001), falha nova nomeada em subprocesso. ⛔ Nunca `git checkout` para restaurar. ⛔ Nunca `xfail`.

---

## 12. O QUE ESTA SPEC MUDA EM VERDADES JÁ ESCRITAS

### 12.1 Linhas do diagnóstico que mudaram de número (medido em `a0bb5fe`, 13/09)

| o diagnóstico §9.2 diz | a linha de hoje | o que está lá de verdade |
|---|---|---|
| `billing_collection.py:1191` (envio do modo teste) | **`:1153`** | `:1191` é o `if dedup:` |
| `platform_outbound.py:1477` | **`:1478-1479`** | a chamada a `send_message` |
| `fila_de_cobranca:362-441` | def **`:362`**, return **`:424`** | |
| `ordenar_para_entrega:334-348` | def **`:334`**, return **`:345-350`** | |
| `normalize_billing_config:502` (`attendant_name`) | **`:500`** | |
| laço `:1542` | **`:1544`** | |
| reserva `:1583` | **`:1589-1590`** | |
| `:2329` / `:2331` | **exatas** ✅ | |
| `worker.py:812, 884, 944, 1001, 1017` | **exatas** ✅ | |
| `allianz_corretor.py:659-667, :704, :3757-3759` | **exatas** ✅ (o diagnóstico de sessão morta é `:3786`) | |
| `app/api/portal.py:165` · `vigia_do_portal.py:306` | **exatas** ✅ (a segunda mora em `backend/app/tasks/`) | |

### 12.2 Como os números de balões foram medidos (o comando, §0.4 do protocolo)

```bash
cd backend && PYTHONIOENCODING=utf-8 python -c "
import sys; sys.path.insert(0,'.')
from app.services.billing_collection import build_customer_message, _format_test_message, normalize_billing_config, _nota_interna_para_a_equipe
from app.services.whatsapp.balloons import split_whatsapp_balloons
from app.services.whatsapp_service import _fatiar_documento
# item e cfg ilustrativos (💭), attendant_name VAZIO de propósito
..."
# 📊 13/09/2026:
#   texto ao cliente  331 ch -> 2 balões  · com bloco_unico -> 1
#   nota interna      322 ch -> 2 balões  · com bloco_unico -> 1
#   mensagem de teste 517 ch -> 3 balões
#   attendant_name vazio renderiza "Aqui é a nossa equipe, da Resulta, tudo bem?"
```

### 12.3 🔴 O guarda de controle guarda uma verdade vencida — e por que ele está ERRADO hoje

`backend/tests/test_a_cobranca_esta_como_estava.py` é **o CONTROLE** desta família (34/34 na EXTRA-001). Duas assertivas dele mudam, e **uma delas já está errada antes de esta SPEC tocar em nada**:

| linha | afirma | o que acontece |
|---|---|---|
| `:152` | "a mensagem da Cobranca vira os MESMOS baloes de antes" | **migra**: passa a afirmar 1 balão pelo caminho de documento |
| `:158` | "o inadimplente recebe UMA mensagem, como sempre recebeu" | 🔴 **é falsa hoje.** Ela mede uma constante `MSG_DA_COBRANCA` **reconstruída à mão** (292 ch) que o produto **não envia**. 📊 O texto que o produto realmente monta tem 331 ch e vira **2** balões. O guarda está verde e o produto está picotado — exatamente CLAUDE.md §9.4: *"o texto vem do acervo, não da imaginação"* |
| `:212` | "a dedup continua DESLIGADA por padrão no modo teste" | **migra** e inverte, com três controles: `test` sem flag → `True`; `test` com `BILLING_DEDUP_TEST_DISABLED=1` → `False`; `equipe` com a flag ligada → `True` (prova que a flag só toca `test`) |

🔴 **Duas migrações obrigatórias, e a segunda é a que o §9.4 exige:**

1. `:158` passa a medir o texto que o produto **monta**, chamando `build_customer_message` — não uma constante escrita dentro do teste.
2. 🔴 **O helper `caminho_de_hoje` (`:146-149`) sai.** Ele **reimplementa** a decisão do produto (`_fatiar(texto) if bloco_unico else split_whatsapp_balloons(...)`) — e hoje ele até acerta, porque a decisão é um `if` de uma linha em `send_message`. Com o P0.1 a decisão passa a ser **`e_documento(kind)`, em `platform_outbound`**, e um helper que continue perguntando "e se `bloco_unico` fosse True?" provaria que o fatiador funciona e **não** provaria que alguém o usa — que é literalmente o defeito da SPEC-083 (CLAUDE.md §9.4: *"o que se afirma é o comportamento do MOTOR sobre o texto REAL"*). O guarda migrado pergunta ao produto: `e_documento("billing_equipe")` e `send_message` com um dublê de provider que **conta os balões que chegaram ao canal**.

As duas linhas de CONTROLE de `:171-176` (texto longo faz os dois caminhos divergirem) **ficam** — são elas que dão direito à conclusão.

### 12.4 A marcha é CRÍTICO, e isso não é uma escolha

A tabela de §8 do diagnóstico trazia "PADRÃO, 2 juízes" no **título** da 001.6 — e o próprio diagnóstico, em §13.4, já a lista como **CRÍTICO**. O título é que estava errado, e está corrigido.

🔴 **O piso do protocolo §3.2 não admite escolha:** *"CRÍTICO no mínimo, independente da conta — qualquer coisa que ENVIE"* e *"migration que ALTERA DADO, ESTRUTURA, TRAVA ou QUEM PODE LER · ⚠️ só o COMMENT é isento; índice e GRANT disparam"*. Esta SPEC faz as duas coisas: envia mensagem e cria coluna, índice e função. E a soma do RISCO (6) chegaria a CRÍTICO sozinha. **Não há nota a dar nem decisão a tomar no card** — rebaixar aqui seria afrouxar a régua (§5 do protocolo).

---

## 13. O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS

> Cinco fontes primárias, **reabertas em 13/09/2026**. O pesquisador do executor reabre cada uma na conversão e registra a data (protocolo §7.3).

### E1 — Playwright · Authentication (`storageState` e o "setup project")
**URL:** https://playwright.dev/docs/auth · reaberta 13/09/2026
**O que faz:** persiste cookies, localStorage, IndexedDB e WebAuthn num arquivo e os reinjeta para começar autenticado. O padrão recomendado é autenticar **uma vez** num *setup project* que roda como dependência dos demais.
**O que MODELAMOS:** o `login_check` das 6 journeys vira o nosso *setup project* — ele roda **antes** do trabalho, e o trabalho só começa nos portais que ele aprovou (B3.1). E a frase que a doc diz com todas as letras — *"you need to delete the stored state when it expires"* — vira o TTL sobre `verified_at` (B2.1): 📊 a nossa sessão da Allianz tinha 27 dias e era reinjetada todo dia.
**O que REJEITAMOS:** o `outputDir` limpo a cada rodada. A sessão do portal é cara (login real na seguradora) e reusá-la é o que evita bater na porta; o que faltava não era apagar sempre, era **saber quando ela venceu**.
**Como o juiz inspeciona:** abre a doc, confere que o TTL do B2.1 existe e que um `verified_at` velho realmente impede a injeção (G9).

### E2 — Playwright · Locators (`getByRole` × CSS/XPath)
**URL:** https://playwright.dev/docs/locators · reaberta 13/09/2026
**O que faz:** recomenda localizadores voltados ao usuário — *"XPath and CSS selectors can be tied to the DOM structure or implementation. These selectors can break when the DOM structure changes."*
**O que MODELAMOS:** nada nesta SPEC — e a razão é o achado. 📊 A Allianz é a journey mais frágil (38 seletores por atributo × 5 por papel/texto, 0 pontos de API) e **não foi a fragilidade que a derrubou**: foi a senha recusada. Modelar aqui seria consertar o que não quebrou.
**O que REJEITAMOS:** reescrever a Allianz nesta SPEC. Fica registrado em §2.2 com gatilho: **depois** da senha nova, se o `login_check` diário mostrar quebra de seletor. É o oposto de deduzir — é medir primeiro.
**Como o juiz inspeciona:** confere que §2.2 tem o gatilho e que nenhum seletor da Allianz foi tocado no diff.

### E3 — Microsoft · Circuit Breaker pattern
**URL:** https://learn.microsoft.com/en-us/azure/architecture/patterns/circuit-breaker · reaberta 13/09/2026
**O que faz:** define os três estados (Closed / Open / Half-Open), o contador de falhas por janela de tempo, o timer do Open e o meio-aberto que deixa passar poucas tentativas. E diz que *"the retry logic should be sensitive to any exceptions that the circuit breaker returns and stop retry attempts if the circuit breaker indicates that a fault isn't transient"*.
**O que MODELAMOS:** dois pontos. (1) Os três estados dentro de `portal_accounts.health`, sem tabela nova (B3.3) — com o detalhe de que o **Half-Open é o gesto humano**: salvar a senha nova já grava `health='unknown'` hoje. (2) *"Accelerated circuit breaking: sometimes a failure response can contain enough information for the circuit breaker to trip immediately"* — é exatamente a credencial recusada: abre na primeira, e **não** volta por timer.
**O que REJEITAMOS:** os limiares adaptativos por ML e o *failed request replay* — sem volume que os justifique, e replay de login é o que bloqueia conta.
**Como o juiz inspeciona:** abre a doc nos três estados e roda G10 (portal aberto não gera job; senha nova reabre para UMA tentativa).

### E4 — AWS · Exponential Backoff and Jitter
**URL:** https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/ · reaberta 13/09/2026
**O que faz:** compara, por simulação, backoff sem jitter, *full jitter*, *equal jitter* e *decorrelated jitter*. Sem jitter, as tentativas se agrupam em ondas sincronizadas; *full jitter* reduziu o trabalho do cliente em mais de 50% com 100 clientes concorrentes.
**O que MODELAMOS:** `available_at = agora + random(0, base·2^n)` — **full jitter**, base 60 s, teto 15 min, **máximo 3 tentativas** (B3.2).
**O que REJEITAMOS:** o teto alto e o número alto de tentativas que a fonte tolera. O nosso limite não é carga do servidor: é **bloqueio da conta da corretora** no portal da seguradora. Um efeito que a fonte não modela pede um teto mais baixo que o dela.
**Como o juiz inspeciona:** chama `proximo_available_at(2)` duas vezes e exige valores diferentes; e confirma que credencial recusada não passa por ali (G11).

### E5 — PostgreSQL · Partial Indexes
**URL:** https://www.postgresql.org/docs/current/indexes-partial.html · reaberta 13/09/2026
**O que faz:** índice sobre um subconjunto definido por um predicado; e um UNIQUE parcial *"enforces uniqueness among the rows that satisfy the index predicate, without constraining those that do not"*.
**O que MODELAMOS:** o índice da janela por segurado nasce parcial (`WHERE send_mode='real'`), como os dois da `20260907_01` — o modo `test` não é tocado, e a leitura da janela nunca atravessa tenant porque `company_id` é a primeira coluna.
**O que REJEITAMOS:** transformar a regra de N dias num UNIQUE. Ela é uma **janela de tempo**, não uma identidade: um UNIQUE por `(company_id, segurado_chave)` impediria para sempre a segunda cobrança do mesmo segurado.
**Como o juiz inspeciona:** roda o VERIFY V2 e confere o predicado no `pg_indexes`.

---

## 14. AS PENDÊNCIAS — as que fecham e as que nascem

**Fecham com prova:** `P-E001-CANARIO-VIVO-NO-IMPLANTADO` · `P-E001-Q4-VIVO-DEPENDE-DE-DEPLOY` · `P-PILOTO-11`.
**São tocadas e re-justificadas:** `P-264` (a fila de portal nasce com leitor; a `tela_cega` da URA continua sem — CONTINUA, com o que destrava escrito) · `P-E001-LEDGER-SEM-VENCIMENTO-E-VALOR` (a migration do B1 é a oportunidade natural: decidir e registrar) · `P-E001-INCERTO-ESCRITA-DUPLA`.

**Nascem (nome, o que destrava, dono, o que custa esquecer):**

| pendência | o que destrava | dono |
|---|---|---|
| `P-E0016-SENHAS-ALLIANZ-MAPFRE` | as senhas novas (🧑 segunda-feira) → rodar `login_check` nos dois e colar o veredito | 🧑 → 🤖 |
| `P-E0016-RESERVA-12-ARGS` | 🔴 **com prazo:** a migration `20260914_02` que derruba a sobrecarga de 12 argumentos entra **no mesmo lote da implantação 2**, depois de o código novo estar no ar e o VERIFY V5 provar que ninguém mais a chama (`select count(*) ... from pg_stat_user_functions` + `grep` no repo). Sobrecarga órfã é armadilha: um `git revert` do código voltaria a chamar a de 12 e gravaria linhas sem `segurado_chave` | 🤖 |
| `P-E0016-NOME-DA-ATENDENTE` | o Founder diz o nome; o executor **nunca** o inventa | 🧑 |
| `P-E0016-ALLIANZ-POR-PAPEL` | depois da senha nova, medir se os 38 seletores por atributo quebram; só então reescrever | 🤖 |
| `P-E0016-TELA-CEGA-DA-URA-SEM-LEITOR` | o leitor de portal do B4.2 é o modelo; a URA ganha o mesmo (P-264) | 🤖 (001.4) |
| `P-E0016-GRUPO-COM-DUAS-SEGURADORAS` | se o Founder quiser 1 mensagem para N seguradoras, a copy precisa ser escrita e aprovada | 🧑 |

---

## 15. ENTREGA, IMPLANTAÇÃO E ROLLBACK

### 15.1 Duas implantações, nesta ordem

| # | o que vai | serviços | pré-requisito |
|---|---|---|---|
| **1** | **BLOCO P0 sozinho** | `smith-api` (backend) · `smith-web` se o rótulo "Quem assina" entrar junto | nenhum. **Não depende das senhas novas** |
| **2** | B1 + B2 + B3 + B4 | `smith-api` **primeiro**, `smith-web` depois (mesma razão medida na EXTRA-001 §6.2: a web nova gravando um `send_mode` que a API antiga normaliza para `test` faria a tela mentir) · `portal-worker` junto do smith-api (B2/B3 moram nele) | as migrations **aplicadas e verificadas** antes: `20260914_01` (coluna+índice+função de 13 args) e `20260914_03` (redação do legado); a `20260914_02` (derruba a sobrecarga de 12 args) vai **no mesmo lote, depois** de o código estar no ar |

🔴 **Entre a implantação 1 e a reativação da rotina, nada mais.** D-PILOTO-18: reativar antes do bloco implantável = avalanche picotada na atendente (📊 hoje, 5 mensagens por segurado).

### 15.2 Variáveis de ambiente novas (nome, sem valor)

| variável | serviço | para quê |
|---|---|---|
| `BILLING_DEDUP_TEST_DISABLED` | smith-api | desligar a dedup num dia de demonstração (⛔ **não** definir na operação normal) |
| `PORTAL_SESSION_TTL_HORAS` | portal-worker | TTL da sessão (💭 12) |
| `PORTAL_BACKOFF_BASE_S` · `PORTAL_BACKOFF_TETO_S` · `PORTAL_MAX_TENTATIVAS` | portal-worker | backoff com jitter |
| `PORTAL_BREAKER_HORAS` | portal-worker | quanto tempo o `fora_do_ar` fica aberto (💭 6) |

📊 Já existentes e necessárias, confirmadas em 08/09: `BILLING_CANARIO_ALLOWLIST`, `CANARIO_TESTE_B`.
⛔ Nenhuma variável nova é obrigatória para a operação normal: todas têm default no código.

### 15.3 A entrega é o `git push`

```bash
git rev-list --count HEAD..origin/main                 # 0
git rev-list --count origin/main..HEAD                 # o que vai
git merge-base --is-ancestor origin/main HEAD && git push origin HEAD:main
git fetch origin && git rev-parse --short origin/main  # confere
```

🔴 **A saída real vai colada no relatório.** Commit local não é entrega (CLAUDE.md §2). Depois o Founder clica **Implantar** — e o pedido entrega **o comando**, nunca a tarefa.

### 15.4 Rollback

```text
1. aplicação: reverter os commits da branch em ordem inversa. ⚠️ ANTES de reverter, pôr a rotina em 'none' —
   o código antigo normaliza 'equipe' para 'test' e passaria a mandar para o test_number.
2. flags: nenhuma de produto. Retirar as 5 variáveis do §15.2 (todas têm default).
3. banco: ROLLBACK da 20260914_01 (drop function 13 args · drop index · drop column `segurado_chave`) — só seguro
   sem linhas `send_mode='real'`. 📊 0 em 13/09; se houver, o rollback correto é deixar a coluna e desligar a rotina.
   🔴 A 20260914_03 (redação da PII legada) **não tem rollback** e não deve ter: ver B4.4.
   ⚠️ Se a 20260914_02 já tiver derrubado a sobrecarga de 12 argumentos, reverter o código sem reverter o banco
   quebra a reserva — reverter as duas juntas, nesta ordem: código, depois banco.
4. efeitos já executados: mensagens enviadas não se desfazem. O ledger fica — é a prova de que saíram.
5. irreversível: as mensagens do canário (TESTE-A → TESTE-B) e as linhas de `agent_activities` do período.
```

---

## 16. VALIDAÇÃO COM SAIONARA E REGINA

O executor **prepara**; o Founder **conduz**. ⛔ Não contatar nenhuma das duas, nem usar os números operacionais delas.

Roteiro (`docs/canon/ROTEIRO-VALIDACAO-EXTRA-001.6-ATENDENTES.md`), com as perguntas que só elas respondem:

1. A mensagem chegou **inteira**? Dá para encaminhar sem editar?
2. A nota interna diz de quem é a cobrança sem você precisar abrir o painel?
3. Quando o mesmo cliente tem 3 boletos, **uma** mensagem com 3 PDFs é melhor que 3 mensagens? (💭 a resposta esperada é sim — se não for, a B1.5 muda)
4. O nome que assina a mensagem é o certo?
5. Quando um portal não entra, o que você lê basta para saber o que fazer?
6. Você prefere ver o CPF inteiro ou os 4 últimos dígitos no relatório? (decide a §9.4)

⛔ Não declarar aceite antes de recebê-lo. O relatório distingue **não testado** · **aprovado no canário técnico** · **validado pela atendente**.

---

## 17. A FILA DEPOIS DESTA ENTREGA

Ordem canônica (diagnóstico §12.1), com o que esta SPEC deixa pronto para cada uma:

```
001.0 retroativa → 001.6-P0 (dentro desta) → 001.1 apólice certa → 001.2 lê tudo antes de falar
→ 001.3 o grupo só recebe o que importa → 001.4 o corredor não trava → [ESTA: 001.6 completa]
→ 001.7 piloto medido → 001.10 vidros → 001.5 base de produtos → 001.8 isolamento → 001.9 rotas
```

| para quem | o que esta SPEC deixa |
|---|---|
| **001.3** | o vocabulário de `health` e a frase por estágio; o aviso de credencial recusada já existe e ela só o **redireciona** ao dono |
| **001.4** | o leitor da fila de telas desconhecidas, que a `tela_cega` da URA copia (P-264) |
| **001.7** | a observabilidade por portal (última verificação · sucesso em 7 d · motivo) — a régua do piloto medido |
| **001.8** | o breaker e o backoff por portal, que são a metade "portal" do isolamento |

---

## 18. DEFINIÇÃO FINAL DE CONCLUSÃO — lista fechada e verificável

Esta SPEC está concluída quando **todas** as linhas abaixo tiverem evidência colada no relatório:

```
[ ]  1. EXECUTION CARD no topo do relatório, dentro do limite do guarda
[ ]  2. BLOCO 0: as 15 premissas remedidas, com comando e valor de hoje
[ ]  3. G1–G12 verdes, e M1–M12 VERMELHAS, cada uma com o nome da falha nova em subprocesso
[ ]  4. o guarda de controle migrado (§12.3) com as três linhas de controle intactas
[ ]  5. migrations aplicadas com VERIFY rodado no Postgres real e saída colada (01: V0–V6 · 03: a contagem antes e
        depois · 02 no lote 2 com a prova de que ninguém chama a de 12 args); MANIFEST atualizado
[ ]  6. suíte inteira ×2, com triagem nominal de toda falha contra a base
[ ]  7. `next start` + uma requisição real, se as telas do B3.4 entraram
[ ]  8. painel de 3 lentes + juiz fresco (§6.1), achados fundidos e consertados juntos
[ ]  9. Q1–Q6 herdados, RODADOS no implantado, com resultado colado (fecha 3 pendências)
[ ] 10. Q7–Q10 rodados com TESTE-A → TESTE-B, e a limpeza conferida
[ ] 11. implantação 1 (P0) no ar, e a rotina reativada DEPOIS dela — nunca antes
[ ] 12. `git push origin HEAD:main` com a saída colada e o head remoto conferido
[ ] 13. D-PILOTO-18 e 19 CONFERIDAS contra o que foi executado (já gravadas em `c0aaf65`), com a divergência escrita se houver
[ ] 14. PENDENCIAS atualizado: 3 fechadas, 6 abertas, P-264 re-justificada
[ ] 15. dossiê republicado — ou "publicação pendente" com o arquivo e o passo exato
[ ] 16. caixa do Founder com as ações concretas mínimas (senhas, nome da atendente, team_number, copy do plural)
```

E o resumo ao Founder responde, em linguagem simples: **o que eu consigo usar agora · o que foi realmente testado · o que ficou desligado e por quê · qual é a única próxima ação necessária.**

⛔ "Pronto" não substitui evidência. Gate material faltando → status **PARCIAL** ou **BLOQUEADO**, com o nome do gate.
