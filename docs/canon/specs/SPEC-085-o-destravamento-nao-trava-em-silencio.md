# SPEC-085 · O DESTRAVAMENTO NÃO TRAVA EM SILÊNCIO

> **Quando o robô não consegue, alguém tem de saber — e alguém tem de poder continuar.**
>
> Hoje ele não consegue, ninguém sabe, e ninguém pode. As três coisas são
> defeitos separados, com consertos separados, e esta SPEC trata as três.
>
> v2 · 24/08/2026 · escrita sob o `PROTOCOLO-AUTOBROKERS-AAA.md` v5
> Depende de: SPEC-084 ✅ · SPEC-084.1 ✅ · SPEC-084.2 ✅
> Branch: `feat/spec085-o-destravamento-nao-trava-em-silencio`

---

## 0. AS DUAS CONTAS — `PROTOCOLO-AUTOBROKERS-AAA.md` §2

**Do trabalho que esta SPEC manda fazer, não do ato de escrevê-la (§7 MODO SPEC).**

| | ALC | REV | FREQ | **RISCO** | **SUP** | piso? |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| a SPEC inteira, como lote | 3 | 3 | 2 | **8** | **3** | sim (§2.4: envia mensagem) |

**ALCANCE 3** — o segurado é quem fica sem atendimento. **REVERSIBILIDADE 3** — sai do
prédio: mensagem ao cliente, dossiê ao suporte, chamado na seguradora.
**FREQUÊNCIA 2** — roda em todo atendimento que não fecha sozinho, 📊 **33,2% deles**.
**SUPERFÍCIE 3** — território que ninguém mapeou: 📊 **quatro vigias** que não se
conhecem, **TRÊS cadeias de handoff** que passam umas pelas outras, **18 lugares** que
escrevem `needs_human` em 3 arquivos, e o estado do travamento morando em Redis com TTL
de 6h. ⚠️ **A v1 desta SPEC contava duas cadeias e três escritores. Era 3 e 18.**

> 🔴 **Time: equipe completa + red team + juiz final com contexto fresco.**

### 0.1 E o lote paga UMA passada de enquadramento (§2.2 do protocolo)

**Esta SPEC É essa passada.** O entregável dela é a **lista das unidades, cada uma já
pontuada** — §5. A SUPERFÍCIE 3 do lote **não se herda**: cada bloco monta o time dele.

### 0.2 As referências, por dimensão (§5 do protocolo)

| dimensão | referência inspecionável | 🧑 |
|---|---|:---:|
| **honestidade com o segurado** | `app/agents/honestidade_do_handoff.py` — o fiscal que reescreve resposta mentirosa, com os três estados `HANDOFF_OK` / `FALHA_DO_HANDOFF` / `SUCESSO_DO_HANDOFF`. **É o caminho A já consertado; o caminho B tem de chegar nele.** | proposta |
| **estado durável** | `work_runs` + `work_steps` como já usados por `intelligence.*` — 📊 **2.619** runs escritos, contra **4** de acionamento | proposta |
| **retomada** | `dispatch_router.py:1574-1596`, a retomada de `insurer_closed`: teto de tentativas, guarda de idempotência, e a condição de "não repetir se já capturou protocolo" | proposta |
| **aviso a quem espera** | `handoff_watchdog.py:135-192` + o marcador Redis de `human_handoff.py:69-152` — ⚠️ **o CÓDIGO existe e não pode ser desfeito; o documento `SPEC-086` NÃO EXISTE** (§3.2) | proposta |
| **tela de destravamento** | `app/dashboard/personalizacao/conectores/portais/` + `POST /api/dashboard/portal-jobs` `retry\|archive`, com a regra espelhada em `lib/portal/hitl.ts` × `backend/portal_worker/guardrails.py:269` | proposta |
| **segurança / PII** | o mascarador que **já roda** no `transcript` (`R. #####ES JÚN###`) e **não** no objeto `slots` | proposta |

⚠️ **Nenhuma confirmada pelo Founder ainda.** Pelo §5 do protocolo, isso **não trava**: o
juiz julga contra elas como propostas, e se o Founder discordar, o alvo muda e a rodada se
repete contra o alvo novo.

---

## 1. O RESULTADO — em uma frase, e ela é do segurado

```
Nenhum atendimento morre calado.

Se o robô não consegue, ou ele TENTA DE NOVO,
                       ou um HUMANO É CHAMADO e consegue continuar,
                       e o SEGURADO ouve a verdade sobre qual dos dois.
```

**O que NÃO é o resultado:** que o robô nunca trave. Travar é legítimo — a URA muda, a
credencial vence, o dado não existe. **O defeito é travar em silêncio.**

---

## 2. O QUE ESTÁ QUEBRADO — medido, com arquivo e linha

### 2.1 🔴 O achado que reordena a SPEC inteira: **não há onde medir**

📊 O estado do acionamento — onde `needs_human` vive — **não é persistido em Postgres**.
Ele mora no Redis com TTL (`dispatch_router.py:254-267`, `_gravar_no_redis`, `ex=ttl`).
O único espelho durável é `work_runs`, e ele tem:

```sql
SELECT workflow_key, status::text, count(*) FROM work_runs GROUP BY 1,2 ORDER BY 3 DESC;
--  intelligence.*            2.619      (os robôs internos)
--  bridge.routine / system / test  9
--  acionamento.seguradora  completed 3
--  acionamento.seguradora  cancelled 1
```

> 🔴 **Quatro acionamentos com rastro durável, na história inteira do produto.**

**LINHA DE CONTROLE:** a mesma tabela tem 2.632 linhas — ela funciona. São os acionamentos
que são quatro. **O rascunho dizia *"nunca foi medido em produção"*; a causa não é falta de
análise, é que não existe onde medir.**

⚠️ **Consequência direta no desenho desta SPEC:** qualquer bloco de conserto que viesse
antes de tornar o travamento visível seria um conserto **sem antes e sem depois**. Por isso
a **FASE 0** existe, e por isso ela vem antes de tudo.

### 2.2 📊 O tamanho do problema, pela única medida possível hoje

Como não há campo de desfecho, a medida é indireta: **a última mensagem é do cliente, e
nada veio depois em mais de 24h.**

| corretora | conversas | terminam no cliente | **paradas >24h** | % |
|---|---:|---:|---:|---:|
| AutoFleet | 379 | 121 | 108 | 28,5% |
| Resulta Seguros | 260 | 104 | 104 | 40,0% |
| **subtotal (sem AMANDUS)** | **639** | **225** | **212** | **33,2%** |
| AMANDUS (teste) | 9 | 7 | 7 | 77,8% |

**LINHA DE CONTROLE:** 📊 416 de 648 (64,2%) terminam **com o bot falando**. Se o motor
estivesse morto, esse número seria ~0. **Ele responde na maioria, e para em um terço.**

**REFINO que separa o defeito do ruído:** 📊 das 224 paradas nos últimos 30 dias,
**177 tiveram o bot falando antes e depois pararam** — esse é o perfil do defeito. As
outras **47 nunca ouviram o bot**: é outro problema (nunca engatou), e **fica fora desta
SPEC** (§9).

⚠️ **Ressalva honesta, e ela é obrigatória:** *"o cliente falou por último"* inclui quem
disse "obrigado". **O 33,2% é um TETO, não uma medida limpa.** É exatamente por isso que a
FASE 0 existe: depois dela, o número passa a ser contado, não estimado.

📊 **E não está piorando.** Por semana, sem AMANDUS: 36,2% · 37,5% · 41,4% · 33,3%.
⚠️ O corte "30 dias × 30 anteriores" daria **37,6% contra 4,5%** e seria **erro de
denominador** — 596 conversas contra 22, porque a produção real começou em 03/08.
**A taxa é estável em ~37%. Ninguém deve escrever "piorou 8×".**

### 2.3 As TRÊS travas que tornam `needs_human` terminal

O estado nasce em `insurer_dispatch_service.py`, em três saídas:

```python
2251  if step.get("sem_chute"):                    # 18 passos
2253      session["state"] = "needs_human"
2254      session["reason"] = f"sem_chute:{...}"
2289  if step.get("fallback_adaptive") or not decisao:   # o cérebro assume
2308  else:                                         # tela IRREVERSÍVEL
2310      session["state"] = "needs_human"
2311      session["reason"] = f"missing_slots:{...}"
```

E aí três coisas independentes o prendem:

```
TRAVA 1 · O VIGIA VÊ E VAI EMBORA
   dispatch_watchdog.py:73-74     if state in _TERMINAL_STATES: return None
   _TERMINAL_STATES (:49) contém `needs_human`.
   🔴 O único laço que varre sessões vivas a 20s desiste dela de propósito.

TRAVA 2 · O ESPELHO DURÁVEL FECHA COMO SUCESSO
   dispatch_router.py:757         UPDATE work_runs SET status='completed'
   porque FASES_ENCERRADAS (insurer_dispatch_service.py:138) contém `needs_human`.
   ⚠️  E a varredura de órfãos TAMBÉM não a vê — mas por OUTRO motivo: ela
      filtra `_STATUS_EM_VOO_WORK_RUN`, que 📊 é uma tupla literal INDEPENDENTE
      (`dispatch_router.py:360-362`), NÃO derivada de FASES_ENCERRADAS.
      🔴 A v1 desta SPEC ligava as duas e mandava auditar a relação errada.

TRAVA 3 · A SESSÃO EVAPORA
   dispatch_router.py:263         TTL de 6h para tudo que não é `monitoring`.
   🔴 Passadas 6h não sobra NADA. Nem no Redis, nem no Postgres.
```

⚠️ **E há uma nuance que muda o conserto:** `try_route_insurer_inbound` tem early-return
para `test_aborted` (`:1278`) e `monitoring` (`:1285`), **mas não para `needs_human`**. Se
a seguradora mandar outra mensagem, o caso **pode** escapar via `_emit(next_state="ura")`.
🔴 **O travamento não é um cadeado no estado — é que ninguém INICIA.** A URA encerra por
inatividade, e o silêncio vira definitivo.

### 2.4 A retomada existe, e cobre **8 de 38**

```python
dispatch_router.py:1574-1596
if (reason == "insurer_closed"
        and int(session.get("retry_count") or 0) == 0
        and not (session.get("captured") or {}).get("protocol")):
```

📊 O relatório da SPEC-084.2 §10 mede o universo: **das 72 sessões, **38 não chegam a
protocolo** — 17 por `handoff_trigger`, **8 por `insurer_closed`**, 5 sem `flow_token`,
e ⚠️ **8 com gravação interrompida** (`SPEC-084.2-EXECUTION-REPORT.md:506-509`), que são
artefato de medição e não travamento. **17+8+5 = 30; o 38 só fecha com a quarta classe.**

> 🔴 **Só as 8 têm retomada.** `missing_slots:`, `sem_chute:`, `handoff_trigger:`,
> `loop_guard`, `conferencia_divergente:`, `subservico_invalido` e `playbook_not_found`
> caem direto em avisar cliente → dossiê → gravar. **Ninguém tenta de novo.**

### 2.5 🔴 São **TRÊS** cadeias de handoff, e só uma foi consertada

> ⚠️ **A v1 desta SPEC contava DUAS.** 🔴 A terceira é a única com prova em produção — e
> era a única que nenhum bloco alcançava.

| | **A** · a ferramenta da atendente | **B** · o corredor de URA | 🔴 **C** · o vigia |
|---|---|---|---|
| onde | `agents/tools/human_handoff.py` | `services/dispatch_router.py:1572-1637` | **`tasks/dispatch_watchdog.py:221-323`** |
| escreve `HUMAN_REQUESTED` | ✅ `:608` | 🔴 **NUNCA** | 🔴 **NUNCA** |
| avisa o cliente | depois, e só se o dossiê saiu | 🔴 **antes, e independentemente** (`:1610-1618`) | ⛔ **NÃO FALA COM ELE. NUNCA.** |
| se não há destino | `FALHA_DO_HANDOFF` (`:642`, `:684`) | 🔴 só um `warning` (`:1620-1629`) | 🔴 `_support_alert` próprio (`:189`) |
| fiscal de honestidade | ✅ `honestidade_do_handoff.py:192` | 🔴 nenhum | 🔴 nenhum |
| radar do `handoff_watchdog` | ✅ (lê `HUMAN_REQUESTED`, `:123`) | 🔴 não entra | 🔴 não entra |
| marcador e teto da SPEC-086 | ✅ é dono deles | 🔴 não usa | 🔴 não usa |

📊 **Medido no caminho C** — `dispatch_watchdog.py`, contagem de ocorrências:

```bash
client_phone 0 · send_to_client 0 · HUMAN_REQUESTED 0
reivindicar_o_aviso 0 · contar_lembrete 0
# e `:299-300`  session["state"] = "needs_human" ; reason = "sentinela_stall"
```

🔴 **E ELE É O QUE DISPAROU DE VERDADE.** 📊 Dos **dois** únicos `needs_human` duráveis da
história do produto, um tem `error_code = 'needs_human:sentinela_stall'` — **este caminho.**
O segurado cujo acionamento morre pela sentinela **não ouve nem a mentira do `:1614`.**
Ouve nada.

🔴 **E no ramo `insurer_closed` é pior:** `clear_active_dispatch` (`:1632` → `:310`)
**apaga a sessão do Redis**. O caso some de `/api/dispatch/active` (a fonte da Fila) **e**
nunca entrou em `HUMAN_REQUESTED` (a fonte do Vigia). **O cliente foi avisado de que um
colega vai assumir, e nenhum sistema guarda que alguém precisa assumir.**

### 2.6 📊 Três de cinco corretoras não têm para quem avisar

```sql
corretoras ....................................................... 5
  com destino em `human_support_destinations` .................... 2
  com `companies.acionamento_profile.suporte_humano_whatsapp` .... 0
  com `integrations.alert_target` com dígito ..................... 0
conversas em HUMAN_REQUESTED agora ............................... 0
```

> 🔴 **Para 3 das 5, todo handoff termina em uma linha de log.**

### 2.7 A mensagem ao segurado promete o que ninguém garante

`dispatch_router.py:1614`, literal:

> *"Estou finalizando um detalhe do seu atendimento com a seguradora e um colega da equipe
> vai assumir daqui a pouquinho, tá bom? Já já te retorno 🙂"*

🔴 Ela sai **antes** de qualquer tentativa de avisar alguém, e para 3 das 5 corretoras não
há ninguém a avisar. **É o mesmo defeito do SMS que cinco corredores nunca mandam.**

⚠️ **E o dossiê mente para o humano também:** `insurer_dispatch_service.py:2853` grava,
incondicionalmente, *"Cliente no WhatsApp: … — ele **JÁ foi avisado** que a equipe vai
assumir"* — **mesmo quando o envio ao cliente estourou exceção** (`:1617-1618`).

### 2.8 🔴 `HUMAN_REQUESTED` significa duas coisas opostas

```
"a IA pediu um humano"        human_handoff.py:608
"um humano JÁ assumiu"        api/dashboard/conversas/[id]/route.ts:85 e :139
                              espelho_chat.py:674  (grava junto `claimed_by_name`)
```

🔴 **E o Vigia não lê `claimed_by`** — o `select` de `handoff_watchdog.py:121-122` nem pede
a coluna. **INFERÊNCIA de alta confiança:** conversa já assumida por uma pessoa continua
gerando *"ATENDIMENTO PRECISA DE VOCÊ"* a cada 6h sempre que o cliente escrever por último.
O filtro de 21/08 (SPEC-086) trata o **sintoma**; a sobrecarga do estado é a **causa**.

### 2.9 Nenhuma tela destrava um acionamento

📊 `backend/app/api/dispatch_monitor.py` tem **52 linhas e só GET** (`:25`, `:35`).
`app/admin/acionamentos/page.tsx` é leitura pura. `admin_spec034.py` não tem POST de sessão.

> **O único destravamento humano do produto é o do PORTAL**
> (`POST /api/dashboard/portal-jobs` `retry|archive`). **O acionamento não tem.**

### 2.10 E ninguém nunca destravou nada, na história inteira

```sql
work_events com run.resumed / run.paused / approval.* / step.retried ....... 0
work_runs.paused_at IS NOT NULL ............................................ 0
human_review_tasks (schema completo: motivo, veredito, revisado_por) ....... 0 linhas
conversations.resolvido_em ................................................. 0
conversations.claimed_by ................................................... 1
```

**LINHA DE CONTROLE:** 📊 **26.803 eventos gravados**, e nenhum deles é de retomada.
**Não é que a retomada falhou — ela não tem como ser registrada.**

📊 **O caso concreto:** a conversa do `needs_human` segue `open`, não reivindicada, não
resolvida, **zero mensagens humanas**, seis dias depois.

### 2.11 A telemetria que existe não tem leitor

`dispatch_router.py:1052` `_log_deflection` grava em `deflection:{company_id}` no Redis,
cap 200. 📊 `grep -rn "deflection:"` → **uma ocorrência: a própria escrita.**
🔴 A *"meta dos 3%"* citada em `:1054` **não tem como ser calculada.**

---

## 3. O QUE JÁ ESTÁ RESOLVIDO — 🔴 e esta SPEC NÃO PODE REFAZER

> **Esta seção existe porque o rascunho avisava:** *"espera a 084 fechar — os 8 passos que
> respondiam errado e o `subservice_supported` mudaram o terreno desta SPEC."* Mudaram
> mesmo. Segue o que está fechado, com a evidência.

### 3.1 A SPEC-084 reduziu QUEM ENTRA em `needs_human`

- **Tela reversível deixou de ser handoff** — `insurer_dispatch_service.py:2304-2306`:
  *"REVERSÍVEL, o cérebro assume (antes isto era needs_human terminal)"*. Só tela
  **irreversível** ainda para.
- **`sem_chute` nasceu** como terceira família de passo (`corridor_playbooks.py:9121`), fora
  da cobrança do portão. 18 passos.
- **Escada de correção antes do handoff** (`:1905-1930`): divergência de conferência tenta
  corrigir até um teto por campo antes de desistir.
- **O formulário nativo é tentado ANTES do gatilho de handoff** (`:2325-2332`).
- **O contrato da ferramenta ganhou campos para os slots do portão** — 📊 **10** `Field(...)`
  em `insurer_dispatch_tool.py:437-535` (a v1 dizia "7").
- 📊 **Os 8 passos que respondiam errado estão fechados** — `python backend/scripts/conferir_respostas.py --todas` → `OK nenhum passo responde sem confirmacao`, exit 0.
- 📊 **`fallback_adaptive` foi de 29 para 228 passos** (14 corredores, 805 passos, 28,3%).

> 🔴 **O que a 084 NÃO tocou: o que acontece DEPOIS de entrar.** As três travas da §2.3 e a
> retomada estreita da §2.4 são exatamente o mesmo código de antes dela. **É esta SPEC.**

### 3.2 O freio de excesso já está construído — 🔴 não desfazer

> ⚠️ 📊 **E há uma armadilha de nome:** **não existe arquivo `SPEC-086*` em
> `docs/canon/specs/`.** O conserto vive no **código**, com os guardas abaixo, e o
> documento nunca foi escrito. **Não procure a SPEC-086 — leia o código.**

| peça | onde | quem usa |
|---|---|---|
| marcador compartilhado no Redis | `human_handoff.py:69-152` (`_CHAVE_DO_MARCADOR`, `reivindicar_o_aviso`, SET nx atômico) | `handoff_watchdog.py:64-91` importa **as mesmas funções** |
| teto de lembretes | `MAX_LEMBRETES_POR_CONVERSA = 4` | idem |
| *"só avisa quem espera"* | `handoff_watchdog.py:135-192` (última mensagem `role == 'user'`) | — |
| guardas | `test_o_grupo_so_e_chamado_quando_alguem_espera.py`, `test_o_grupo_nao_recebe_o_mesmo_aviso_duas_vezes.py`, `test_handoff_chega_em_alguem.py`, `test_o_segurado_nao_fica_no_escuro.py` | — |

🔴 **Os arquivos que as duas SPECs disputam** — a 085 não consegue evitá-los:

```
backend/app/agents/tools/human_handoff.py         marcador, teto, _avisar_suporte, _arun
backend/app/tasks/handoff_watchdog.py             filtro de espera, teto, telemetria
backend/app/services/dispatch_router.py           needs_human + resolver_destino_de_suporte
backend/app/agents/honestidade_do_handoff.py      os três estados HANDOFF_*
backend/app/services/insurer_dispatch_service.py  build_handoff_dossier
```

> ⛔ **REGRA DURA DESTA SPEC:** **o marcador e o teto são REUSADOS, nunca reescritos.**
> Quem tocar `human_handoff.py:69-152` sem uma linha do relatório explicando por quê,
> reprova no gate. **A 086 cobriu o EXCESSO de aviso; a 085 cobre o SILÊNCIO.**

### 3.3 E o que também já está fechado, para ninguém "consertar" de novo

- **`SUBSERVICO_INVALIDO` já não vira `missing_data`** — `insurer_dispatch_tool.py:801`
  devolve `sem_corredor` ou, para a família de vidros, **`use_portal`** com ordem explícita
  de **não** chamar `request_human_agent` (`:822-831`). O laço de "perguntar ao cliente o
  campo `subservico_invalido`" está morto.
- **O caminho A do handoff não mente mais** — os três estados de
  `honestidade_do_handoff.py` e o `RuntimeError` no caminho síncrono (`:686-702`).

---

## 4. A ORDEM, E POR QUE ELA É ESSA

```
FASE 0    O TRAVAMENTO VIRA LINHA DE BANCO         ← antes de tudo, sem exceção
FASE 1    A SEGURANÇA                              ← antes de tocar as tabelas
──────────────────────────────────────────────────────────────────────────────
BLOCO A   o estado diz a verdade
BLOCO B   o humano é chamado DE VERDADE            ← 3 de 5 não têm destino
BLOCO C   o segurado ouve a verdade
BLOCO D   a retomada deixa de cobrir 8 de 38
BLOCO E   a tela que destrava
BLOCO F   os dois vigias se encontram
──────────────────────────────────────────────────────────────────────────────
BLOCO G   A PROVA
```

🔴 **A FASE 0 vem primeiro porque sem ela nenhum bloco tem antes e depois.** §2.1: existem
quatro acionamentos com rastro durável na história inteira. **Consertar antes de medir é
consertar no escuro, e a SPEC-084 já provou o custo disso.**

🔴 **A FASE 1 vem antes dos blocos porque eles ESCREVEM nas tabelas que hoje guardam
CPF em claro** (P-180). Ampliar a escrita antes de mascarar multiplica o problema.

⚠️ **B vem antes de C de propósito.** Parar de mentir ao segurado (C) sem ter para quem
avisar (B) transforma "um colega vai assumir" em "ninguém vai te atender" — **verdade
pior que a mentira.** A ordem é: **primeiro exista o colega, depois se promete o colega.**

---

## 5. AS UNIDADES DE TRABALHO — cada uma pontuada (§2.2 do protocolo)

> **Unidade = a menor coisa que dá para ENTREGAR e PROVAR sozinha.**

| # | unidade | ALC/REV/FREQ | **RISCO** | **SUP** | time |
|---|---|:---:|:---:|:---:|---|
| **F0** | o travamento vira linha de banco | 0/2/2 | **4** | 2 | builder + juiz + verificador |
| **F1** | mascarar `slots` antes de gravar + backfill das 12 | 3/2/2 | **7**·piso | 0 | builder + juiz da superfície |
| **A** | `needs_human` deixa de ser `completed` | 2/2/2 | **6** | 1 | + verificador + desenhista |
| **B** | o handoff do corredor chega em alguém | 3/3/2 | **8**·piso | 2 | + investigador + desenhista |
| **C** | a mensagem ao segurado deixa de prometer | 3/3/2 | **8**·piso | 0 | builder + juiz da superfície |
| **D** | a retomada cobre mais que `insurer_closed` | 3/3/2 | **8**·piso | 2 | + verificador + desenhista |
| **E** | a tela que destrava um acionamento | 2/3/1 | **6**·piso | 2 | + verificador + desenhista |
| **F** | `HUMAN_REQUESTED` deixa de ter dois sentidos | 2/2/2 | **6** | 2 | + verificador + desenhista |
| **G** | a prova ponta a ponta | 3/0/2 | **5** | 3 | + investigador + desenhista |

🔴 **INTEGRADOR entra** — §3 do protocolo: 3 ou mais unidades no mesmo lote.
🔴 **RED TEAM entra** nos blocos **B**, **C** e **D** — RISCO 8 com superfície ≥1.
🔴 **Um worktree por builder** quando dois tocarem `dispatch_router.py` (§7 MODO EXECUÇÃO):
📊 os blocos **A, B, C, D e F** tocam esse arquivo — ⚠️ **o A também**, em `:528`,
`:553-562` e `:757`. **A integração é SERIAL.**

---

## FASE 0 · O TRAVAMENTO VIRA LINHA DE BANCO

> **Nada nesta SPEC pode ser medido antes disto. É a primeira entrega e o primeiro gate.**

### F0.1 O que se grava

Quando uma sessão de acionamento entra em `needs_human` — nas três saídas da §2.3 — grava
uma linha **durável**, com:

```
company_id            🔴 obrigatório, e é o filtro do repository (CLAUDE.md §7)
conversation_id       para casar com a conversa
session_key           a chave Redis, para reconciliar enquanto ela vive
playbook_ref          qual corredor
subservico            qual serviço
reason                🔴 o motivo COMPLETO: `missing_slots:local_seguro,cpf`
                         nunca só `missing_slots`
slots_que_faltaram    a lista, 🔴 MASCARADA (FASE 1)
tela_da_ura           o texto que o corredor não soube responder, MASCARADO
estado_do_destravamento   `travado` | `retomado_pelo_robo` | `assumido_por_humano`
                          | `resolvido` | `abandonado`
quem_destravou        null, ou o usuário
travado_em / destravado_em
```

⚠️ **Onde isto mora é decisão do investigador do bloco**, e ele tem **duas candidatas
reais**: estender `work_runs`/`work_steps` (que já é o espelho durável e já tem
`error_code`), ou dar escritor à **`human_review_tasks`**, que 📊 tem schema completo
(`motivo`, `veredito`, `revisado_por`) e **zero linhas desde sempre** (P-182).

> 🔴 **CLAUDE.md §5 — consolidar antes de duplicar.** Criar uma terceira tabela para o
> mesmo assunto **reprova no gate**. Se nenhuma das duas servir, a justificativa vai
> escrita no relatório, com o que falta em cada uma.

### F0.2 A migration — 🔴 e ela leva POLICY, não só coluna

📊 **Medido em 24/08/2026, e muda o desenho:**

```sql
SELECT relname, relrowsecurity, (SELECT count(*) FROM pg_policies p
        WHERE p.tablename = c.relname) FROM pg_class c ...

  human_review_tasks   RLS ligado   policies 0     ← candidata da F0.1
  work_runs            RLS ligado   policies 0     ← candidata da F0.1
  work_steps           RLS ligado   policies 0
  work_events          RLS ligado   policies 0
  conversations        RLS ligado   policies 4
  human_support_destinations        policies 4
```

🔴 **As duas candidatas da FASE 0 são exatamente as tabelas sem policy.** O `CLAUDE.md`
§7 é literal: *"O backend usa service role: **RLS sem policy não protege nada** contra
erro de filtro no código."*

**Logo a migration da FASE 0 leva as duas coisas:** a estrutura **e** a policy por
`company_id`. Ela é **expand-first**, **idempotente**, e sai com **APPLY / VERIFY /
ROLLBACK escritos antes de rodar** (`CLAUDE.md` §8).

⚠️ 🔴 **E o piso da §2.4 do protocolo dispara aqui duas vezes:** *"migration que altera
dado, estrutura, trava ou **quem pode ler**"*. Policy é quem pode ler. **RISCO 6, sem
discussão.**
🔴 **Leia `MIGRATIONS-AUTHORITY.md` antes** — 📊 e saiba que o ledger mente: 3 das 9
migrations da SPEC-084 estão aplicadas de fato e ausentes de `schema_migrations`.
**VERIFY confere o OBJETO, nunca o ledger.**

### F0.3 O gate da FASE 0 — e ele é o mais duro da SPEC

```
1. um acionamento de teste entra em needs_human  →  a linha existe no banco
2. 🔴 A LINHA DE CONTROLE: um acionamento que TERMINA BEM  →  NENHUMA linha
      (senão o que se está gravando não é travamento, é qualquer coisa)
3. o `reason` gravado é o COMPLETO, com os slots
4. 🔴 dois tenants — **e o teste tem de FICAR VERMELHO quando o filtro sai**
      ⛔ "a corretora A não vê a linha da B" **passa sempre** com service role e
         zero policies, porque a consulta nunca roda sem o filtro.
      🔴 O guarda de verdade tem DUAS metades:
         (a) o teste chama o repository com A e não vê a linha de B;
         (b) 🔴 A MUTAÇÃO: apaga o `.eq("company_id", ...)` e o teste
             FICA VERMELHO. Se não ficar, ele não guarda nada.
      ⚠️ O relatório traz as duas saídas: com filtro e sem.
5. a linha sobrevive ao TTL de 6h da sessão Redis
      🔴 prova: apaga a chave do Redis à mão, e a linha continua lá
```

⚠️ **Sem o item 2, a FASE 0 não fecha.** Um gravador que grava sempre não mede nada.

---

## FASE 1 · A SEGURANÇA — antes de escrever mais

**P-180.** 📊 12 linhas de `work_steps.output_summary` guardam `titular_cpf`,
`telefone_contato` e `client_phone` **sem máscara**, de 18 a 19/08/2026.

🔴 **E o que torna isto defeito de construção, não esquecimento:** no **mesmo registro**, o
`transcript` **está mascarado** — `R. #####ES JÚN###`. **A máscara existe, roda, e não foi
aplicada ao objeto `slots`. Não falta a função: falta uma chamada.**

```
F1.1   aplicar o mascarador ao `slots` antes de gravar `output_summary`
F1.2   backfill das 12 linhas existentes
F1.3   🔴 O GUARDA TEM DE FALHAR HOJE:
       grava um passo com CPF, e prova que o que foi ao banco NÃO o contém.
       ⚠️ Rode-o ANTES do conserto e mostre-o VERMELHO no relatório.
       Um guarda que nasce verde não provou nada.
```

⚠️ **Escala:** as 12 linhas vêm de **4 acionamentos** — os únicos com rastro durável. Com
73 rotas ligadas e a FASE 0 gravando mais, isto vira o padrão.

---

## BLOCO A · O ESTADO DIZ A VERDADE

**P-181.** 📊 Os dois únicos `needs_human` duráveis estão em `work_runs` com
**`status = 'completed'`**. E um deles tem **três campos com três verdades**:

```
error_code          needs_human:missing_slots:problema_eletrico_opcao
current_step_key    test_aborted
result_summary      "Simulação completa"
```

### ⛔ A CAUSA É UMA LINHA, NÃO A LISTA — e a v1 mandava mexer na lista

📊 **`STATUS_WORK_RUN_POR_FASE` (`insurer_dispatch_service.py:146`) JÁ mapeia
`needs_human` → `waiting_input`**, e o comentário de `:143-145` diz por quê:
*"o trabalho existe, não terminou, e depende de algo de fora"*.
**A distinção já existe no vocabulário. O defeito é `dispatch_router.py:757`
atropelá-la.**

```
A.1   ⛔ NÃO TIRE `needs_human` de FASES_ENCERRADAS.
      📊 A lista tem TRÊS consumidores, e um deles está CERTO hoje:
        dispatch_router.py:528   "succeeded" if fase not in FASES_ENCERRADAS
                                 else "waiting_input"   ← JÁ ACERTA
        dispatch_router.py:757   UPDATE work_runs = 'completed'  ← O DEFEITO
        ura_simulator.py:65      `and estado_atual != "needs_human"`
      🔴 Tirar da tupla faria o `:528` gravar `succeeded` no lugar de
         `waiting_input` — **piorando o único lugar que hoje está certo.**

A.2   🔴 O CONSERTO É O `:757`: a reconciliação passa a usar
      STATUS_WORK_RUN_POR_FASE em vez de `completed` fixo.

A.3   os três campos passam a concordar. 📊 O sítio que os desalinha é
      `dispatch_router.py:553-562`: o `result_summary` é escrito quando
      `status == "completed"`, o `error_code` quando `fase == "needs_human"`,
      e **nenhum dos dois é limpo depois**.
```

⚠️ 📊 **E a v1 desta SPEC errava o aviso:** dizia que `FASES_ENCERRADAS` alimenta
`_STATUS_EM_VOO_WORK_RUN`. **Não alimenta** — `dispatch_router.py:360-362` é uma tupla
literal independente. O aviso mandava o executor auditar a relação errada.

**Gate A:** um `needs_human` gravado é distinguível de um sucesso **por consulta SQL**, e
📊 **a consulta é escrita no relatório**. ⚠️ **Controle:** um acionamento que deu certo
continua saindo como `completed`.

---

## BLOCO B · O HUMANO É CHAMADO DE VERDADE

> 🔴 **É o bloco mais importante da SPEC.** Nada adianta se não há para quem avisar.

```
B.0   ⛔ O CAMINHO C ENTRA AQUI, E É O PRIMEIRO.
      `dispatch_watchdog.py:299-323`, o `_sentinela_recover`:
        🔴 ele passa a AVISAR O SEGURADO — hoje não avisa nada
        🔴 escreve o estado durável, como B e A
        🔴 REUSA o marcador e o teto (`human_handoff.py:69-152`),
           em vez do `_support_alert` próprio de `:189`
      ⚠️ 📊 É a única cadeia com `needs_human` durável em produção
         (`sentinela_stall`). Consertar B e C sem ela é consertar o que
         nunca disparou e deixar de fora o que disparou.

B.1   o caminho B ganha o que o caminho A já tem:
        · escreve `conversations.status = 'HUMAN_REQUESTED'`  (ou o que o BLOCO F decidir)
        · o resultado do envio decide o desfecho — FALHA_DO_HANDOFF quando não saiu
        · 🔴 REUSA o marcador e o teto de human_handoff.py:69-152. NÃO REESCREVE.

B.2   🔴 quando NÃO há destino, isso deixa de ser um `warning`:
        · vira estado durável `sem_destino_de_suporte`
        · e aparece na tela da corretora — ela precisa saber que está surda

B.3   📊 3 das 5 corretoras não têm destino. O relatório diz, nominalmente,
      quais são, e o que cada uma precisa configurar.
      🧑 Configurar é do Founder/corretora — 🤖 detectar e avisar é nosso.

B.4   o dossiê para de mentir: insurer_dispatch_service.py:2853 só escreve
      "ele JÁ foi avisado" se o envio ao cliente REALMENTE saiu.
```

⚠️ 🔴 **E há um defeito latente que este bloco precisa fechar antes de mexer no
resolvedor:** `_normalizar_destino` (`dispatch_router.py:931`) recebe `alert_target`, que é
um **objeto JSON**, faz `str(raw)` e extrai os dígitos. 📊 Hoje devolve `""` porque os
valores não têm dígito. **No dia em que alguém preencher `internal_numbers` com telefones,
o terceiro fallback produz um destino colado de vários números — e manda um dossiê com CPF
para um número que não existe.** Guarda obrigatório.

**Gate B:** um handoff do corredor, numa corretora **com** destino, chega ao destino e
grava o estado. ⚠️ **CONTROLE:** numa corretora **sem** destino, ele grava
`sem_destino_de_suporte` e **não** declara sucesso. **Os dois casos no relatório.**

---

## BLOCO C · O SEGURADO OUVE A VERDADE

```
C.1   a mensagem de dispatch_router.py:1614 deixa de sair ANTES do dossiê

C.2   o que o segurado ouve passa a depender do que aconteceu:
        dossiê saiu           →  "um colega vai assumir"
        dossiê NÃO saiu       →  🔴 a verdade, no tom do produto —
                                 nunca "vai assumir", nunca silêncio
        (o modelo é RESPOSTA_HONESTA, honestidade_do_handoff.py:164:
         "Registrei seu pedido… ainda não consegui confirmar com a equipe…")

C.3   🔴 o fiscal do caminho A passa a valer no caminho B:
      guardar_a_verdade_do_handoff (honestidade_do_handoff.py:192)
```

⚠️ **Este bloco é RISCO 8 com SUPERFÍCIE 0** — poucas linhas, e cada palavra chega a um
segurado. **Pelo §2.2 do protocolo, texto que instrui modelo sai com obrigação de MOSTRAR
O MODELO FAZENDO:** se a redação passar por LLM, o relatório traz a **saída**, não o
prompt.

**Gate C:** as duas mensagens, verbatim, no relatório, com o caso que produz cada uma.
🔴 **E a busca que prova que a promessa não sobrou em lugar nenhum:**
`grep -rn "vai assumir" backend/app/` — toda ocorrência com o caso que a autoriza.

---

## BLOCO D · A RETOMADA COBRE MAIS QUE 8 DE 38

```
D.1   o investigador classifica os 7 motivos que hoje não retomam:
        insurer_closed          ✅ já retoma
        missing_slots:*         retomável? só se o dado puder chegar depois
        sem_chute:*             🔴 NUNCA retoma sozinho — é o dado que não existe
        handoff_trigger:*       🔴 a URA MANDOU falar com humano. Não insistir.
        loop_guard              retomar repetiria o laço
        conferencia_divergente  já tem escada própria (:1905-1930)
        subservico_invalido     já resolvido (§3.3)
        playbook_not_found      não é travamento: é rota inexistente

D.2   🔴 A REGRA QUE O BLOCO TEM DE ESCREVER, e ela é de negócio:
      "retomar" só vale quando A CAUSA PODE TER MUDADO.
      Retomar `sem_chute` é inventar dado. Retomar `handoff_trigger` é
      desobedecer a seguradora. 🔴 Nem tudo que trava deve ser retomado —
      e o que não deve, vai para o humano MAIS RÁPIDO, não mais devagar.

D.3   o que retomar herda de dispatch_router.py:1574-1596:
        teto de tentativas · guarda de idempotência ·
        não repetir se já capturou protocolo
```

⚠️ **Sobre a P-93, e a v1 desta SPEC errou o alcance dela.** 📊 A P-93 aparece **duas
vezes** em `PENDENCIAS.md`; a que interessa (`:1651`) é do **portal de vidros**
(`idx_portal_jobs_pedido_vivo`), e a frase *"já existe atendimento aberto"* mora em
`agents/tools/portal_params.py:501` — **portal, não URA**. 📊 A própria pendência mede:
*"Alcance hoje: **zero**. Os 91 jobs históricos têm `idempotency_key IS NULL`."*

🔴 **Logo ela NÃO é pré-requisito do BLOCO D.** Vale só para a sub-rota de vidros que cai
no portal via `use_portal` (§3.3). Os `idempotency_key` do caminho de URA
(`dispatch_router.py:422, :458, :531`) são dedup de `work_runs`/`work_steps` e **não
bloqueiam retomada nenhuma**. ⚠️ O executor NÃO abre `portal_jobs` antes de tocar a
retomada de URA.

**Gate D:** para cada um dos 8 motivos, o relatório diz **retoma / não retoma / vai direto
ao humano**, com o porquê. ⚠️ **CONTROLE:** um `sem_chute` **não** retoma, e a prova é o
teste que falha se alguém o fizer retomar.

---

## BLOCO E · A TELA QUE DESTRAVA

📊 Hoje: `dispatch_monitor.py` tem 52 linhas e só GET. **Não existe.**

```
E.1   a Fila (app/dashboard/atendimentos/fila) passa a mostrar acionamento travado
      🔴 e a fonte é a linha durável da FASE 0, nunca o Redis

E.2   dois botões, e não mais que dois:
        ASSUMIR    →  vira `assumido_por_humano`, com quem
        ARQUIVAR   →  vira `abandonado`, com o motivo escrito

E.3   🔴 a referência é o portal, que já fez isto:
      POST /api/dashboard/portal-jobs `retry|archive`, e a regra espelhada em
      lib/portal/hitl.ts × backend/portal_worker/guardrails.py:269
      ⚠️ o portal é a MEDIANA do que já passou no gate — §5 regra 3 do protocolo

E.4   🔴 e o `release` deixa de apagar o caso: hoje
      conversas/[id]/route.ts:105-112 devolve para `open`, e a conversa
      SOME do filtro `precisa_de_voce` E do select do Vigia.
```

⚠️ 🔴 **Este bloco toca `app/` — `CLAUDE.md` §9.1 vale integralmente:**
`npm run test:rotas-montam` **+** `next start` **+ uma requisição a rota que executa
código.** 📊 Uma pasta `[slug]` ao lado de uma `[templateId]` na mesma posição já derrubou
o produto inteiro por 1h40 com todos os gates verdes.

**Gate E:** um acionamento travado aparece na Fila, é assumido, e o estado muda no banco.
⚠️ **CONTROLE:** um acionamento **não** travado **não** aparece.

---

## BLOCO F · OS DOIS VIGIAS SE ENCONTRAM

```
F.1   `HUMAN_REQUESTED` deixa de significar duas coisas opostas.
      Duas saídas possíveis, e a escolha vai justificada no relatório:
        (a) dois estados: `AGUARDANDO_HUMANO` e `ASSUMIDA_POR_HUMANO`
        (b) um estado + `claimed_by` lido por quem hoje o ignora

F.2   🔴 o handoff_watchdog passa a LER `claimed_by`
      (hoje o select de :121-122 nem pede a coluna)

F.3   o teto de 4 lembretes deixa de ser um `continue` mudo (:239-241):
      quando estoura, o caso continua VISÍVEL em algum lugar —
      e a mensagem do 4º lembrete já promete isso: "ela continua na Fila
      do painel — de lá ninguém a tira sozinho". 🔴 Hoje a promessa é falsa,
      porque o `release` a tira.
```

⚠️ **Se (a) for escolhido, é migration** — e o piso da §2.4 do protocolo dispara: **altera
dado ou estrutura**. Expand-first, com backfill, sem quebrar o `select` de ninguém.

**Gate F:** uma conversa **já assumida** por uma pessoa **para** de gerar *"ATENDIMENTO
PRECISA DE VOCÊ"*. ⚠️ **CONTROLE:** uma conversa **não** assumida **continua** gerando —
até o teto.

---

## BLOCO G · A PROVA

> **Este bloco não conserta nada. Ele prova que os outros consertaram.**

```
G.1   O ENSAIO SECO, ponta a ponta, com a AMANDUS SEGUROS e SÓ com ela:
        1. um acionamento entra em `missing_slots`
        2. a linha durável nasce                          (FASE 0)
        3. o CPF nela está mascarado                      (FASE 1)
        4. o work_run NÃO diz `completed`                 (A)
        5. o suporte é avisado, ou o estado diz que não há destino  (B)
        6. o segurado ouve a mensagem certa PARA O CASO   (C)
        7. o motivo é classificado retomável ou não       (D)
        8. aparece na Fila e é assumido                   (E)
        9. e para de gerar lembrete                       (F)

G.2   🔴 A LINHA DE CONTROLE DO ENSAIO: o mesmo roteiro com um acionamento
      que TERMINA BEM. Nenhuma linha durável, nenhum aviso, nenhuma Fila.
      ⚠️ Sem esta segunda passada, o ensaio prova só que o sistema faz
      barulho — não que ele distingue.

G.3   a medição da §2.2 rodada DE NOVO, com a mesma query, e as duas lado a lado.
      ⚠️ 📊 Espere pouco movimento: a FASE 0 muda o que se CONTA, não o que
      ACONTECE. O número honesto é "quantos travamentos agora têm linha",
      não "a taxa caiu".

G.4   os guardas dos 14 vermelhos que esta SPEC toca (P-183):
      test_handoff_chega_em_alguem.py sai do vermelho, e o relatório diz
      se foi defeito de produto ou asserção vencida.
```

### 🔴 As travas do ensaio, e nenhuma é negociável

```
⛔ É PROIBIDO LIGAR AGENTE DE ATENDIMENTO. 📊 Os quatro attendance estão
   is_active=false, e continuam.
⛔ INSURER_DISPATCH_LIVE fica FECHADO. O ensaio roda em DRY-RUN.
⛔ NENHUMA mensagem sai para segurado real. Só AMANDUS SEGUROS.
⛔ O Founder é AVISADO ANTES de qualquer coisa que envie.
⛔ Somente SELECT no banco de produção, fora das migrations desta SPEC.
```

---

## 7. OS JUÍZES — quatro lentes, e cada uma tem uma pergunta só

> §4 do protocolo: **um juiz por SUPERFÍCIE DE FALHA, nunca quatro genéricos.**
> Cada um recebe o **artefato real** — o diff, o teste rodando, a consulta ao banco.
> **Nenhum recebe a narrativa do builder.**

### JUIZ 1 · O CÉTICO DA MEDIDA
> **"O que você gravou é travamento, ou é qualquer coisa?"**

Roda o controle da F0.3 item 2. Confere que o `reason` é o completo. Refaz a query da §2.2
e compara denominadores. 🔴 **Reprova qualquer número sem a consulta ao lado.**

### JUIZ 2 · O CÉTICO DO SEGURADO
> **"Alguma coisa que sai daqui promete o que não se cumpre?"**

Lê **toda** mensagem nova ou alterada. Para cada uma: **qual caso a produz, e o que
garante a promessa.** 🔴 Se a mensagem sai de LLM, exige a **saída**, não o prompt.
📊 A referência do dano: a promessa de SMS que foi de zero para dez rotas com
`azul 0/321 · porto 0/521 · yelum 0/607` de lastro.

### JUIZ 3 · O CÉTICO DA VIZINHA
> **"O que a SPEC-086 construiu continua de pé?"**

Roda os quatro guardas da 086. Confere que `human_handoff.py:69-152` não foi reescrito.
🔴 **Se o marcador ou o teto mudaram, exige a linha do relatório que justifica** — e se não
houver, é blocker. **É o juiz que existe porque as duas SPECs disputam cinco arquivos.**

### JUIZ 4 · O CÉTICO DO ISOLAMENTO
> **"Alguma coisa nova atravessa corretora?"**

Toda escrita nova passa por `company_id`? O teste de dois tenants existe e **falha** se o
filtro sair? 🔴 A tela da FASE 0 filtra por corretora? **E o `_normalizar_destino` continua
incapaz de colar números de corretoras diferentes?**

### 🔴 E o RED TEAM, nos blocos B, C e D
> **Missão: fazer o produto mentir ou calar.**
> Sem destino · destino inválido · Redis fora do ar · LLM sem chave · a URA mandando
> outra mensagem depois do handoff · duas retomadas simultâneas.

### O laço — §6 do protocolo, sem exceção

```
① builder entrega   ② verificador mecânico   ③ juiz da lente, com a medição
④ TESTE DO PRODUTO em cada achado: muda um byte que chega ao segurado,
   à corretora, ao banco ou à segurança?  NÃO → PENDENCIAS.md, e SEGUE
⑤ volta 2 = o MESMO juiz · volta 3 = um juiz NOVO que não vê as anteriores
🔴 TODA VOLTA CONTA.  Teto 3.  Bateu sem liberar → CLASSIFICA (§6):
   é uma das oito condições do CLAUDE.md §10? Não → entrega o que passou e AVANÇA.
```

---

## 8. O GATE DA SPEC

```
✅  FASE 0 fechada, COM a linha de controle (acionamento bom não grava)
✅  FASE 1 fechada, e o guarda foi mostrado VERMELHO antes do conserto
✅  os seis blocos com o gate próprio verde, cada um com o CONTROLE
✅  as quatro lentes liberaram, ou o que sobrou está em PENDENCIAS.md
✅  o ensaio G1 e o CONTROLE G2, os dois no relatório
✅  🔴 dois tenants reais, teste automático de isolamento
✅  🔴 npm run test:rotas-montam + next start + UMA requisição a /api/…
✅  🔴 nenhum motor paralelo: nem tabela nova para assunto que já tem tabela,
       nem segundo marcador de aviso, nem terceiro vigia
✅  relatório completo, com a §0.1 preenchida ANTES de o time ser montado
✅  as pendências que esta SPEC TOCOU: FECHADA / CONTINUA / MORREU (§1 do protocolo)
```

🔴 **E o gate NÃO é a nota.** É: **as fases cumpridas** e **o que ficou de fora nomeado,
com o que destrava**.

---

## 9. O QUE FICA DE FORA — e por quê

| fica de fora | por quê |
|---|---|
| 📊 as **47 conversas que nunca ouviram o bot** | é outro defeito: nunca engatou. Vira pendência com a medição |
| **P-084-67** — o `galaxy_message` / `flow_id` | 5 rotas param por falta de canal, não por travamento. **É SPEC própria** |
| a **causa** de cada travamento (URA mudou, credencial venceu) | é a **SPEC-087**, a auto-atualização. Esta SPEC trata o **sintoma**, e isso é deliberado |
| **P-183** — os 151 guardas invisíveis ao `pytest` | 🔴 grande demais para caber aqui, e **afeta toda SPEC futura**. Esta SPEC só conserta o guarda que ela toca |
| reescrever o marcador de aviso | ⛔ **é da SPEC-086, e está pronto** |
| ligar qualquer agente | ⛔ **decisão do Founder, e não é desta SPEC** |

⚠️ **Toda linha desta tabela vai para `PENDENCIAS.md` com o que destrava e de quem é
(`CLAUDE.md` §11.1).** Deixar pronto e desligado é aceitável; **deixar pronto e não anotado,
não.**

---

## 10. O RELATÓRIO

`docs/canon/reports/SPEC-EXECUTION-REPORT-TEMPLATE.md`, **completo**, e com atenção a:

- **§0.1 preenchida ANTES de montar time** — as duas contas por unidade, as referências
  com o estado (proposta / confirmada / não avaliada), as voltas com a porta de saída, e o
  que o juiz novo da volta 3 fez
- 🔴 **as queries**, não os números soltos — 📊 sem consulta, o número não entra
  (`CLAUDE.md` §12.1: 📊 medido · 💭 ilustrativo, e número sem marca é defeito de revisão)
- **o antes e o depois da §2.2**, com a mesma query e o mesmo denominador
- **as mensagens ao segurado, verbatim**, com o caso que produz cada uma
- **o que a SPEC-086 tinha e continua tendo**
- **os blockers que o orquestrador rebaixou a pendência**, com o texto do juiz e o motivo
- **canário Amandus → Resulta → AutoFleet**
- **a declaração de que nenhum motor paralelo foi criado**

---

## 11. PREFLIGHT — antes da primeira linha de código

```bash
git rev-list --count HEAD..origin/main    # 🔴 TEM DE SER 0
git branch --show-current                 # feat/spec085-...
git rev-parse HEAD                        # registrar no relatório
git status --short                        # limpo
export PYTHONIOENCODING=utf-8             # 🔴 senão UnicodeEncodeError no Windows
```

**Leitura obrigatória, nesta ordem** (`CLAUDE.md` §2): `EXECUTION-MASTER-PLAN` ·
`FOUNDER-DECISIONS` · `GLOSSARIO` · **`PROTOCOLO-AUTOBROKERS-AAA`** · `PENDENCIAS` ·
`README` · SPEC-052 · SPEC-053 · **`MIGRATIONS-AUTHORITY` antes de qualquer SQL**.

⚠️ **E leia a SPEC-084.2-EXECUTION-REPORT.md inteiro.** 📊 Ele tem a medição das 72 sessões
que esta SPEC usa como denominador, e traz os dois defeitos que quase foram a produção —
**uma mutação de teste commitada dentro da régua, e uma medição que escrevia no corredor.**
