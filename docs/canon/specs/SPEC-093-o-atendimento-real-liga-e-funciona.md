# SPEC-093 · O ATENDIMENTO REAL LIGA E FUNCIONA

> **O que ela entrega:** a Regina e a Saionara ligam o agente de manhã, assistem
> pelo WhatsApp delas, e **quando ele trava, um clique o faz seguir — e o produto
> registra que travou ali**. O cliente real deixa de ser descartado. E quem
> escreveu de madrugada recebe **bom dia** em vez de silêncio.
>
> **v2** · 25/08/2026 · commit base `b8ef4e5` · repo `AutoBrokers-FIX`

## ⚠️ Isto NÃO é uma versão reduzida

**É a lista do que está quebrado entre "a corretora aperta LIGAR" e "o cliente
é atendido de ponta a ponta."** Nada aqui é adiado para depois; nada aqui é
ensaio. Cada bloco existe porque 📊 foi medido quebrado hoje.

⛔ **A SPEC-086 não é "a versão completa disto".** Ela é outra coisa — uma
arquitetura de posse (quem "assume" a conversa), que o Founder decidiu **não
usar**: *"não é para ela assumir. É para ele apenas destravar e monitorar."*

---

## 🔴 A razão desta SPEC existir, em cinco linhas medidas

Três lentes independentes revisaram a proposta de SPEC-086 (52 KB) contra o
código e o banco. **Nenhuma sabia da outra.** As três disseram a mesma coisa:

> **A arquitetura de posse dela é boa — e nada nela destrava o piloto.**

📊 Notas: **62/100** (canon + execução) · **68/100** (medida + escopo).

O que o piloto precisa **não estava lá**, e cabe em cinco consertos. Quatro são
de poucas linhas. **Esta SPEC é esses cinco.**

⚠️ **A SPEC-086 não morre** — ela vem depois, calibrada pelo que o piloto
mostrar. `CLAUDE.md` §11: isto é **proposta de ordem**, não corte de escopo.

---

## 0. O TESTE DO PRODUTO — a régua desta SPEC inteira

> **Segunda-feira, 8h. A Regina abre o dashboard, aperta LIGAR, e o telefone
> dela começa a mostrar o robô atendendo cliente de verdade. Quando o robô
> trava numa tela que não sabe responder, ela dá UM clique e ele segue —
> e o produto REGISTRA que travou ali. Quando ela sai, aperta DESLIGAR.
> Quando volta, aperta LIGAR e quem escreveu no intervalo recebe um bom-dia.
> **E ao ligar, os 73 corredores ligam junto — ela não clica 73 vezes.**

## 🔴 E o que ela NÃO faz — decisão do Founder, 25/08

> *"Não é para ela assumir o atendimento. É para ele apenas destravar e
> monitorar."*

⛔ **Não existe trava de posse nesta SPEC.** Nada de `claimed_by`, nada de
epoch, nada de fencing. **Elas estão olhando.** Se as duas e o robô falarem
juntos, isso é assunto do piloto — não de arquitetura escrita antes dele.

> **O clique dela não é intervenção: é uma muleta.** E toda vez que a muleta é
> usada, **o produto tem de saber** — porque é exatamente ali que falta corredor.

⛔ **Qualquer bloco que não sirva a esse parágrafo sai desta SPEC.**

---

## 1. O ESTADO DE HOJE — 📊 tudo medido em 25/08/2026

### Os cinco impedimentos, e por que cada um mata o primeiro dia

```
1  🧑 o finalize         o cliente ouve "estou acionando" e ninguém vem
2  o papel               `member` → 403. Elas NÃO conseguem apertar o botão
3  a allowlist           cliente real é descartado ANTES de existir
4  🔴 o travamento       o corredor para, alguém clica, e NADA fica registrado
5  a saudação            quem escreveu de madrugada espera para sempre
```

### 1.1 · 🔴 O "meio aberto" — e a frase é do próprio código

📊 [insurer_dispatch_service.py:358-362](../../backend/app/services/insurer_dispatch_service.py#L358-L362):

> *"Com o envio liberado e a finalização em `test`, mensagens REAIS chegam à URA
> da seguradora, o fluxo anda até o fim e é CANCELADO — **o segurado ouviu
> 'estou acionando', ninguém vem**, e a seguradora registrou uma conversa que não
> virou serviço. Ou o corredor trabalha, ou ele não fala; **não existe um meio
> termo honesto.**"*

📊 Lido no `/health` da `smith-api` em 25/08 20:32:

```
acionamento_env_aberta        false      ← hoje fechado
freio_de_emergencia_armado    true       ← e é SÓ o freio que fecha
finalize_modo                 "test"
finalize_abre_de_verdade      []         ← nenhum corredor abre chamado
```

🔴 **A cadeia, medida em [insurer_dispatch_service.py:343-376](../../backend/app/services/insurer_dispatch_service.py#L343-L376):**

```python
def dispatch_live_enabled():
    if freio_de_emergencia_armado(): return False
    # 🔴 04/08 (P-90): AUSENTE passou a significar ABERTO
    return os.getenv("INSURER_DISPATCH_LIVE","") in ("1","true",...)

def finalize_live_for(ref):
    if freio_de_emergencia_armado(): return False
    mode = os.getenv("DISPATCH_FINALIZE_MODE","live")   # padrão LIVE
```

⚠️ **A armadilha:** o piloto começa **desarmando o freio**. No instante em que
ele sai, `INSURER_DISPATCH_LIVE` volta ao que o ambiente disser — e 📊 a
**P-168** (aberta 15/08, dona 🧑 Founder) registra `INSURER_DISPATCH_LIVE=true`
lido no EasyPanel de `autobrokers-smith-api` e `smith-worker`.

📊 E `finalize_modo` lê `"test"` **contra um padrão `live`** — logo
`DISPATCH_FINALIZE_MODE=test` **está escrito no ambiente**. Os dois juntos, com o
freio desarmado, são exatamente o meio aberto.

### 1.2 · O papel — 📊 com o número

```
company_members ativos:   8 admin_company  +  2 member
o botão exige:            owner|admin|admin_company|master_admin
                          admin-auth-policy.ts:5 · TENANT_WRITE_ROLES
member ∉ lista            →  403 admin_required
```

⚠️ **E dar `admin_company` às duas resolve o botão e abre a configuração
inteira** — prompt do agente, integrações, tudo. **Não é o conserto certo.**

### 1.3 · A allowlist — o cliente que nunca existiu

📊 [webhook.py:519-525](../../backend/app/api/webhook.py#L519-L525): `attendant_inbound_allowed()`
descarta **antes** de `get_or_create_user`. 📊 `PENDENCIAS.md:1449`: em produção
ela tem **um** número.

> ⛔ **Nem o Espelho aprende.** O cliente escreve, e para o produto ele **nunca
> escreveu.**

### 1.4 · 🔴 O travamento — e o clique dela é creditado ao robô

📊 **O caminho, quando o corredor recebe uma tela que não sabe responder**
([insurer_dispatch_service.py:2471](../../backend/app/services/insurer_dispatch_service.py#L2471)):

```
match_ura_step → None
  → formulário nativo, 2ª tentativa                              :2701
  → detect_handoff_trigger → needs_human                         :2706
  → responder_da_ficha (banco determinístico)                    :2723
  → state = "human_phase"  ← aqui o Cérebro é convocado          :2740
  → fail-safe: empilha em `pending_insurer_messages`,
    e NÃO responde às cegas                                      :2766
```

✅ **Isso é bom para o piloto:** corredor incompleto degrada para **silêncio e
pausa**, nunca para chute.

## 🔴 Mas o clique da Regina some — e o robô leva o crédito

📊 O clique dela entra por [webhook.py:1250](../../backend/app/api/webhook.py#L1250)
(`from_me`) → `note_manual_outbound`
([dispatch_router.py:1656](../../backend/app/services/dispatch_router.py#L1656)).
**O que ele faz, inteiro:**

```python
session.setdefault("transcript", []).append(
    {"direction": "out", "text": str(text)[:2000], "manual": True})
await save_active_dispatch(company_id, insurer_phone, session)
```

🔴 **Redis. Só Redis.** Não toca `unblock_state`, não grava `work_events`, não
chama `registrar_checkpoint`.

**E aí a mentira se monta sozinha, em quatro passos medidos:**

```
1  Regina clica          `manual:True` no Redis · unblock_state segue 'travado'
2  a URA responde        checkpoint fase='ura', fase_anterior='needs_human'
3  decidir_travamento     :533  → devolve "retomado_pelo_robo"
4  _marcar_travamento     :564  aplica — porque NADA marcou o humano
```

> ⛔ **O piloto, como está, produziria um relatório que diz que o robô se
> destravou sozinho — nas exatas vezes em que uma pessoa o destravou.**

⚠️ **E a guarda existe — só não cobre esta porta.** O único escritor correto de
`assumido_por_humano` é
[acionamentos-travados/route.ts:162](../../app/api/dashboard/acionamentos-travados/route.ts#L162),
o botão ASSUMIR do dashboard. 📊 `grep -rn "acionamentos-travados" --include=*.tsx`
→ **0 resultados.** *A única rota que credita o humano certo não tem tela.*

📊 E o docstring de `_marcar_travamento:548` diz, com todas as letras, que
creditar o robô *"é a mesma classe de mentira do `dossier_sent = True`"*. **A
guarda foi construída para o clique do dashboard; o do WhatsApp passa por baixo.**

### Os três que deveriam destravar — 📊 medidos

| | **Vigia** | **Sentinela** | **Cérebro** |
|---|---|---|---|
| onde | `dispatch_watchdog.py:510` | `dispatch_watchdog.py:322` | `dispatch_watchdog.py:464` |
| dispara | cron **20s** | inline, só em `stall_unanswered` | no turno |
| destrava | 📊 quase nada — alerta, e um cutucão | 📊 **responde a seguradora**, teto 2 | 📊 **redige o texto** |
| deixa rastro | indireto | ✅ `unblock_state='retomado_pelo_robo'` | 🔴 **nenhum em Postgres** |
| 📊 já agiu | — | **0 vezes** | **indeterminável** |

🔴 **O Cérebro não deixa rastro nenhum** — `beat("cerebro")` é só Redis
([heartbeat.py:73](../../backend/app/core/heartbeat.py#L73)). *"O Cérebro
destravou quantos?"* é hoje uma pergunta sem resposta possível.

### E contar travamentos não dá por `unblock_state`

📊 `_marcar_travamento:562` filtra `.is_("unblock_state","null")` — **um run que
trava duas vezes conta uma.** É *estado*, não *contador*.

```sql
-- 📊 o contador de verdade é `work_steps`:
select s.output_summary->>'reason', count(*)
  from work_steps s join work_runs r on r.id = s.work_run_id
 where r.runtime_kind='acionamento' and s.step_key='needs_human'
 group by 1;
-- 25/08: missing_slots:problema_eletrico_opcao=1 · sentinela_stall=1
```

### 1.5 · A saudação — o cliente da madrugada

📊 Medido: com o agente desligado a mensagem **é gravada** ([webhook.py:697-712](../../backend/app/api/webhook.py#L697-L712))
e o pipeline **para** ([:753-786](../../backend/app/api/webhook.py#L753-L786)).
Ao religar, 📊 **não existe replay** — [tenant-agent-store.ts:85-97](../../lib/admin/tenant-agent-store.ts#L85-L97)
escreve `is_active` e nada mais.

🔴 **E o agente acorda cego:** o histórico vive no checkpointer do LangGraph por
`thread_id` ([graph.py:1418](../../backend/app/agents/graph.py#L1418)), e as mensagens da
noite nunca entraram nele. Se o cliente escrever *"e aí?"* às 9h, **o agente
responde sem saber que o carro quebrou.**

📊 **O tamanho do problema, hoje** — conversas terminando em mensagem do cliente
sem resposta:

```
< 4h ......  12        24-72h ....   5
4-12h .....   7        3-7 dias ..  25
12-24h ....   4        > 7 dias .. 181
                       ─────────────────
                       234 no total
com corte de 24h  →     23
```

> **234 é um incidente. 23 é uma manhã.** O corte de 24h é a SPEC inteira.

---

## 2. ⛔ AS TRAVAS — valem em todos os blocos

```
⛔ NENHUMA mensagem sai para segurado durante a execução desta SPEC.
⛔ NENHUM agente de atendimento é ligado pela execução. Quem liga é a corretora,
   pelo botão. Os quatro estão `is_active=false` e continuam.
⛔ NENHUMA entrada em portal de seguradora.
⛔ Banco: SELECT livre; escrita só pelas migrations desta SPEC.
⛔ NUNCA imprimir CPF, telefone, apólice, placa ou nome de pessoa.
⛔ NÃO mexer em variável de ambiente de produção. O BLOCO E é REGISTRO, não ação.
```

### 🔴 E um furo no freio que o executor precisa saber

📊 [dispatch_watchdog.py:379](../../backend/app/tasks/dispatch_watchdog.py#L379) — o
Sentinela chama `wa.send_message` **direto**, e 📊 `dispatch_live_enabled` tem
**zero ocorrências no arquivo**.

> ⚠️ **Um dos três freios não se aplica ao caminho do Sentinela.** Ele é quem
> responde à seguradora quando o corredor emperra — exatamente o caminho que o
> piloto vai exercitar.

**Registrar como pendência e medir no piloto.** ⛔ Não consertar nesta SPEC: mexer
em freio às vésperas de ligar é a troca errada. Mas **ninguém pode descobrir isso
depois.**

---

# BLOCO A · A atendente aperta o botão — e só o botão

## O problema

📊 `member` recebe 403. `admin_company` abre a configuração inteira.

## O conserto

Um papel novo **`attendant`**, com uma permissão só: **alternar `is_active` do
agente de atendimento.** Nada de prompt, nada de integração, nada de billing.

```
lib/admin/admin-auth-policy.ts
  + ATTENDANCE_TOGGLE_ROLES = TENANT_WRITE_ROLES ∪ {'attendant'}
  + canToggleAttendanceAgent(ctx)     ← NOVA, separada de canWriteTenantConfig

app/api/dashboard/agents/[agentKey]/route.ts:20-35
  🔴 usa canToggleAttendanceAgent QUANDO o corpo só muda `is_active`.
     Qualquer outro campo continua exigindo canWriteTenantConfig.
```

⚠️ **A separação é o ponto.** Se o mesmo `PATCH` aceitar `is_active` **e**
prompt, dar `attendant` a alguém dá o prompt junto. **O portão é por CAMPO.**

## O gate

```
① `attendant` alterna `is_active`                           → 200
② 🔴 `attendant` tenta mudar QUALQUER outro campo           → 403
③ 🔴 `attendant` de OUTRA corretora tenta alternar          → 403
④ `member` continua 403 no toggle                            (linha de controle)
⑤ `admin_company` continua podendo tudo                      (linha de controle)
```

🔴 **As duas linhas de controle são obrigatórias.** Sem ④ e ⑤, um bug que
libere geral passa como sucesso — `CLAUDE.md` §9.3.

---

# BLOCO B · O cliente real deixa de ser descartado

## O problema

📊 `ATTENDANT_INBOUND_ALLOWLIST` com um número: todo o resto some antes da
captura.

## O conserto

⚠️ **Não é apagar a variável.** Apagar é irreversível de cabeça — quem vier
depois não sabe o que havia. O conserto é **torná-la por corretora e
observável**:

```
1. o valor vazio passa a significar "todos", e isso vira COMENTÁRIO no código
2. 🔴 o `/health` passa a expor `allowlist_ativa: true|false` e o TAMANHO
   ⛔ nunca os números. `CLAUDE.md` §13.3 — presença, não conteúdo.
3. quando ela descarta, o produto REGISTRA (contador, sem o telefone)
```

📊 **Por que o contador:** hoje o descarte é `return` mudo. Se a allowlist ficar
mal configurada no dia do piloto, **o sintoma é "ninguém escreveu"** — e é
indistinguível de um dia fraco.

## 🔴 E esvaziá-la QUEBRA outra coisa — os dois blocos colidem

📊 [route_sentinel.py:363](../../backend/app/services/atlas/route_sentinel.py#L363)
monta **o destino do alerta de deriva** assim:

```python
os.getenv("ATTENDANT_INBOUND_ALLOWLIST", "").split(",")[0]
```

⚠️ **Env vazia ⇒ telefone vazio ⇒ o alerta não chega a ninguém.**

📊 E não é hipótese: **14 linhas de `route_drift` de hoje, 25/08**, todas
`structural`/`escalated` com `needs_founder=true`. 💭 Podem não ter chegado a
pessoa nenhuma.

> 🔴 **O BLOCO B, como escrito, apagaria em silêncio o alarme que avisa quando um
> corredor sai do lugar — no exato dia em que corredores começam a atender
> cliente real.**

**O conserto é uma linha:** o destino do alerta ganha variável própria
(`ATLAS_ALERTA_DESTINO`), e a allowlist volta a ser só allowlist. ⛔ **Duas
responsabilidades numa variável é o defeito; usá-la para as duas é o sintoma.**

## O gate

```
🔴 ⓪ allowlist vazia → o alerta do Sentinela AINDA chega ao destino
① allowlist vazia → mensagem de telefone qualquer é capturada
② allowlist com 1 número → o resto é descartado E CONTADO
③ 🔴 o contador sobe sem que telefone nenhum apareça em log     (§13.3)
④ o `/health` diz `allowlist_ativa` sem revelar um dígito
```

---

# BLOCO C · O travamento vira evidência — e o clique tem dono

> 🔴 **É o bloco mais valioso da SPEC**, porque é o que transforma o piloto em
> aprendizado. Sem ele, duas semanas de atendimento real produzem **zero linhas**
> sobre onde o produto falha.

## C.1 · O clique da Regina para de ser creditado ao robô

`note_manual_outbound` ([dispatch_router.py:1656](../../backend/app/services/dispatch_router.py#L1656))
passa a marcar a sessão de forma **durável**, não só no Redis:

```
work_runs.unblock_state = 'destravado_por_humano'
work_events              tipo próprio, com o canal ('whatsapp' | 'dashboard')
```

⚠️ **Sem tela e sem fluxo novo.** Ela continua clicando no WhatsApp dela. **O
que muda é só que o produto passa a saber.**

🔴 **E `decidir_travamento:533` passa a olhar essa marca antes de concluir
`retomado_pelo_robo`.** É a correção da mentira, e é uma condição a mais num
`if` que já existe.

## C.2 · Contar travamento, por `work_steps`

Um evento por travamento — **não um estado por run.**

```
quantas vezes travou hoje       ✅ conta
em que rota e em que tela       ✅ já está em `output_summary`
quem destravou                  ✅ Vigia | Sentinela | Cérebro | HUMANO
quanto tempo ficou travado      ✅ do `needs_human` até a fase seguinte
```

## C.3 · 🔴 O Cérebro passa a deixar rastro

📊 Hoje só existe `beat("cerebro")` no Redis. **Quando o Cérebro redige a
resposta que destrava, isso vira uma linha em `work_events`.**

⚠️ **Sem isso o piloto não responde a pergunta do Founder** — *"quero ver o
desempenho do Vigia, Sentinela e do Cérebro"*. Dois dos três são
inauditáveis hoje.

## O gate do BLOCO C

```
① corredor trava → 1 evento contável, com rota e tela
② o Sentinela destrava → o evento diz `sentinela`
③ 🔴 um humano clica no WhatsApp → o evento diz `humano`, NÃO `robo`
④ o Cérebro redige → o evento diz `cerebro`
⑤ 🔴 trava DUAS vezes no mesmo run → DOIS eventos   (é o furo do `unblock_state`)
⑥ ninguém destrava → o run continua `travado`, e aparece na fila
⑦ dois tenants: o travamento de um não conta para o outro
```

🔴 **A mutação obrigatória do bloco:** desligue a marca do humano e **o teste ③
tem de ficar vermelho.** Se ele continuar verde, o bloco não está guardando nada.

---

# BLOCO D · A saudação do religamento

> 🔴 **Decisão do Founder, 25/08:** ao religar, o agente **saúda e pergunta**.
> Não retoma, não age, não presume. *"Bom dia…"*

## D.1 · Desde quando estávamos fora

📊 `agents` tem `is_active` e `updated_at` — **e `updated_at` é sobrescrito por
qualquer save de configuração** ([tenant-agent-store.ts:68](../../lib/admin/tenant-agent-store.ts#L68),
[:114](../../lib/admin/tenant-agent-store.ts#L114)). *"Desde quando"* **não é
recuperável hoje.**

```sql
alter table public.agents
  add column if not exists desligado_em timestamptz;
```

⚠️ Escrita **só** na transição `true → false`. Ligar **limpa**.

## D.2 · Quem recebe

```
mensagem do cliente, sem resposta depois dela, e:
   idade ≤ 12h      → saúda e pergunta se ainda precisa
   12h < idade ≤ 24h → saúda NOMEANDO a demora
   idade > 24h       → 🔴 NÃO ENVIA. vai para a fila humana.
```

📊 **Por que 24h:** acima disso a janela da Meta já exige template — a regra de
produto e a regra do canal dão a mesma resposta. E 📊 **181 dos 234 têm mais de
7 dias**: ali a saudação é exumação, não recuperação.

⛔ **Nunca envia se:** `claimed_by`/`claimed_by_name` preenchido · status
`HUMAN_REQUESTED` · já existe mensagem `assistant` posterior à do cliente.

📊 **O terceiro item funciona a favor sozinho:** as linhas do Espelho chegam como
`role='assistant'` — **resposta humana pelo celular já conta como respondida.**

## D.3 · 🔴 O limitador já existe. Não construa outro.

📊 [platform_outbound.py:125-145](../../backend/app/services/platform_outbound.py#L125-L145):

```
_TETO_HORA = 12          _TETO_DIA_NOVO = 20
espaçamento sorteado 241–479 s
janela 08:00–20:00       domingo bloqueado inteiro
parada de emergência por corretora (_STOP_KEY)
```

🔴 **E o caminho de resposta pula tudo isso de propósito** —
[webhook.py:883](../../backend/app/api/webhook.py#L883) chama `send_message` direto,
com `temperatura=QUENTE`.

> **A saudação sai por `send_to_client_guarded` com `temperatura=FRIA`.**
> Aí 23 conversas drenam em ~2h a 12/h, e 234 esbarram no teto de 20/dia
> **sozinhas**. O problema das "cinquenta às 8h" **se resolve por roteamento,
> não por código novo.** — `CLAUDE.md` §5.

## D.4 · Não mandar duas vezes

📊 Não existe chave de idempotência em nenhum ponto de saída, e `messages` não
tem campo de "respondida" — 📊 as colunas são
`id, conversation_id, role, content, created_at, type, audio_url, image_url,
sender_user_id, payload` e nada mais.

```
chave:  saudacao:{conversation_id}:{id_da_ultima_mensagem_inbound}
```

🔴 **A chave é a mensagem, não o clique.** Desligar e ligar duas vezes gera a
**mesma** chave → a segunda é no-op. Chavear no evento de toggle mandaria duas.

⚠️ **Onde persistir.** 📊 `work_effects` existe, **não tem DDL no repositório**
(0 ocorrências em 68 migrations — foi aplicada direto no Supabase) e **tem 0
linhas e nenhum chamador de produção**. 🔴 **Usá-la aqui é escolher uma tabela
sem escritor para a primeira coisa que não pode falhar.**

> **Decisão: tabela própria, mínima, `saudacoes_enviadas(company_id, conversation_id,
> inbound_message_id, enviada_em)` com UNIQUE nas três primeiras.** Registrar em
> `PENDENCIAS.md` que `work_effects` continua sem escritor.

## D.5 · 🔴 A prévia, no primeiro religar

📊 O robô teve **4 conversas de WhatsApp em toda a história do produto** (21.901
de 23.028 mensagens são Espelho de conversa **humana**).

> **A primeira vez que o replay rodar será a maior coisa que este produto já
> mandou sozinho.**

```
primeiro religar de cada corretora:
   mostra a CONTAGEM e a lista → espera confirmação explícita → só então envia
```

⚠️ Uma tela é o guarda mais barato que existe.

## O gate do BLOCO D

```
① 3 mensagens de 2h → 3 saudações, pelo caminho FRIO
② mensagem de 30h → NÃO envia, vai para a fila
③ 🔴 desligar/ligar duas vezes → 1 saudação      (a chave é a mensagem)
④ conversa com `claimed_by` → NÃO envia
⑤ conversa com `assistant` posterior → NÃO envia
⑥ 🔴 agente ligado o tempo todo → ZERO saudações  (linha de controle)
⑦ 40 conversas elegíveis → o governador segura em 12/h, não dispara 40
⑧ dois tenants: a saudação de um não vaza para o outro
```

🔴 **O ⑥ é a linha de controle e é obrigatório.** Sem ele, um bug que saúde
sempre passa como sucesso.

---

# BLOCO E · 🧑 A DECISÃO DO FINALIZE — registro, não código

⛔ **Nada é executado neste bloco.** Ele existe para que a decisão seja
**escrita** antes do piloto, e não descoberta depois.

```
A)  DISPATCH_FINALIZE_MODE=live
    + DISPATCH_FINALIZE_LIVE_PLAYBOOKS=<só os corredores completos>
    ⚠️ guincho de verdade, custo de verdade. Só onde há confiança.

B)  manter `test`
    ⛔ então NÃO se faz piloto com cliente real — serve para
       acionamento fictício e mais nada.
```

## 🔴 E o Founder já indicou a direção, em 25/08

> *"Nós vamos deixar o atendimento ser pedido e, se for fictício, elas vão
> cancelar depois de feito."*

📊 **Isso é a opção (A)** — `finalize` aberto, com o cancelamento feito **por
pessoa, depois do fato**. É coerente com o resto do desenho: as duas estão
olhando, e cancelar é o mesmo gesto de destravar.

⚠️ **Mas o executor não pode inferir daí a configuração.** Faltam duas coisas
que só o Founder decide, e as duas custam dinheiro se erradas:

```
1  abre em TODOS os corredores, ou só nos completos?
   (`DISPATCH_FINALIZE_LIVE_PLAYBOOKS` gradua corredor a corredor)
2  quanto tempo elas têm para cancelar antes de virar serviço de verdade?
   🔴 não medido: ninguém sabe quanto a seguradora demora entre aceitar
      e despachar. Pode ser minutos.
```

🔴 **A nº 2 é a que preocupa.** *"Cancelar depois"* só funciona se existir um
"depois". **Se a seguradora despacha o guincho em dois minutos, não existe.**

> **O executor MEDE isso no acervo antes de escrever o gate** — e, se não houver
> dado, isso vira a primeira pergunta do piloto, não uma suposição.

**O executor:** registra a decisão do Founder em `FOUNDER-DECISIONS.md`, atualiza
a **P-168**, e **não toca em variável nenhuma**.

🔴 **Se a decisão não estiver registrada, o BLOCO F reprova.**

---

# BLOCO G · Todos os corredores ligados — e a tela que aguenta 73

> 🔴 **Decisão do Founder, 25/08:** *"na hora que a corretora ligar o atendimento,
> tudo pode estar ligado automaticamente. Ela pode desligar no dashboard."*

## G.1 · O estado de hoje

📊 O mecanismo **existe**: `tenant_corridors` guarda o que cada corretora ativou,
e `setTenantCorridorStatus` ([tenant-corridor-store.ts](../../lib/admin/tenant-corridor-store.ts))
liga e pausa, um a um, pela tela
[personalizacao/corredores](../../app/dashboard/personalizacao/corredores/CorridorGalleryClient.tsx).

⚠️ **O que falta são duas coisas:**

```
1  ligar TODOS de uma vez — hoje é um clique por corredor
2  a tela lista os 73 numa coluna só, sem agrupamento e sem filtro
```

## G.2 · Ligar tudo junto

Quando a corretora ativa o agente de atendimento, **todos os corredores
disponíveis passam a `ativo`** — numa única transação.

```
⛔ NÃO é um laço de N chamadas: 73 escritas soltas deixam metade ligada
   se a rede cair no meio, e "metade ligada" é o pior estado possível.
🔴 É um upsert em lote, e ele é IDEMPOTENTE: ligar duas vezes não muda nada.
⚠️ E RESPEITA quem já foi desligado à mão: um corredor que a corretora
   pausou de propósito NÃO volta sozinho.
```

📊 Esse último ponto é o que separa *"começa com tudo ligado"* de *"o dashboard
desfaz a escolha da corretora toda manhã"*.

## G.3 · Corredor desligado vira handoff

Um corredor pausado **não some** — ele passa para a pessoa.

⚠️ **E isso já quase funciona:** 📊 o corredor que não sabe responder já degrada
para `needs_human` e para `human_phase` sem chutar
([insurer_dispatch_service.py:2740](../../backend/app/services/insurer_dispatch_service.py#L2740)).
O bloco só precisa que **corredor pausado entre no mesmo caminho**, em vez de
falhar de outro jeito.

## G.4 · A tela organizada — 🔴 e o Founder deixou a decisão comigo

> *"Talvez seja ideal ter uma lista de corredores por seguradoras e aí as
> seguradoras têm os ramos e serviços. Não sei, você deve verificar."*

📊 São **73 rotas** em ~14 seguradoras. Uma coluna de 73 cartões é o que a tela
faz hoje — e ela já está longa demais na captura que o Founder mandou.

**A decisão, e o motivo de cada parte:**

```
AGRUPAR por SEGURADORA        14 blocos em vez de 73 cartões
  └ dentro, por RAMO          Auto · Residencial
     └ os SERVIÇOS ficam como estão (a linha de chips já funciona)

FECHADO por padrão, com o resumo na dobra:
  "Porto Seguro · 2 ramos · 11 serviços · 2 de 2 ativos"

UM FILTRO SÓ, e é o que a operação pergunta:
  ( ) todos   ( ) ativos   ( ) desligados
```

⛔ **O que NÃO entra agora**, e por quê:

| | |
|---|---|
| busca por texto | 14 blocos fechados cabem numa tela. Busca resolve problema que o agrupamento já resolveu |
| filtro por serviço | 💭 ninguém pediu; e serviço é atributo de rota, não de escolha |
| ordenar | a ordem alfabética é previsível, e previsível vale mais que configurável |

> 🔴 **O critério: a corretora tem de conseguir responder "o que está ligado?"
> sem rolar a página.** Hoje ela não consegue. Com 14 blocos fechados, consegue.

⚠️ **E o rodapé da tela continua dizendo a verdade que já diz:** ativar é
registro de configuração — *não liga canal, não abre portal, não envia nada.*
Quem liga o atendimento é o botão do agente.

## O gate

```
① a corretora liga o agente → todos os corredores disponíveis ficam ativos
② 🔴 um corredor pausado À MÃO antes disso CONTINUA pausado    (a escolha dela vence)
③ ligar duas vezes → nada muda                                  (idempotente)
④ 🔴 a escrita é uma só: derrube a rede no meio e não sobra metade ligada
⑤ corredor pausado recebe atendimento → vai para handoff, não falha
⑥ a tela mostra 14 blocos fechados, e o resumo bate com o banco
⑦ o filtro "desligados" mostra exatamente os que estão pausados
⑧ dois tenants: ligar tudo em A não liga nada em B
```

🔴 **A mutação obrigatória:** desligue a checagem do ② e o teste tem de ficar
vermelho. Se continuar verde, o bloco está desfazendo a escolha da corretora
sem ninguém perceber.

---

# BLOCO F · A prova — e ela roda com o agente DESLIGADO

```
① os gates de A, B, C, D, G passam
② 🔴 os quatro agentes `attendance` continuam `is_active=false`
③ 🔴 zero mensagens enviadas durante toda a execução
④ a decisão do BLOCO E está escrita
⑤ a bateria inteira verde, com o número de rodadas do diário
⑥ dois tenants: A não vê nada de B em nenhum dos quatro blocos
```

## 🔴 A mutação obrigatória

```
desligue o corte de 24h    → o teste de idade tem de REPROVAR
desligue a chave           → o teste de duplicata tem de REPROVAR
desligue o filtro tenant   → o teste de dois tenants tem de REPROVAR
```

⚠️ **Restaurar por CÓPIA, nunca por `git checkout`** — `git diff --quiet` diz
"idêntico" sobre arquivo que ele nem rastreia. É a P-231.

---

## 3. O QUE NÃO ESTÁ AQUI, e por quê

| | por quê |
|---|---|
| a arquitetura de posse (epoch/fencing) | é a 086. **Vem depois**, calibrada pelo piloto |
| o motor de follow-up | 💭 depende de tempos que ninguém mediu ainda |
| a Insurer Human Bridge | 📊 4 acionamentos na história. O piloto dirá se é 1× ou 40× |
| a tela de acompanhamento | 🔴 **elas monitoram pelo WhatsApp.** Decisão do Founder |
| consertar `apply_auto_overlays` | 📊 0 overlays, namespace quebrado. **Não bloqueia** |

---

## 4. 🔴 O que fica pendente — vai para `PENDENCIAS.md`

```
P-093-01  `work_effects` sem DDL no repositório e sem escritor de produção
P-093-02  os 4 serviços: só 2 têm digital de deploy (Worker e Web não têm)
P-093-03  `INSURER_DISPATCH_LIVE=true` no EasyPanel — P-168, e agora com dono
P-093-04  a corrida do epoch: o eco `fromMe` chega DEPOIS do envio dela
P-093-05  `whatsapp/service.py:129-176` — `send_message` paralelo, zero
          importadores. Motor paralelo morto (`CLAUDE.md` §5)
P-093-06  `conversations.resolvido_em` e `resolucao_motivo`: 0 linhas
P-093-07  🔴 `dispatch_watchdog.py:379` envia sem consultar `dispatch_live_enabled`
P-093-08  🔴 `acionamentos-travados` é a única rota que credita o humano — e
          📊 não tem NENHUM consumidor de UI (0 matches em *.tsx)
P-093-09  o Cérebro só bate em Redis (`heartbeat.py:73`): desempenho dele é
          inauditável
P-093-10  `route_sentinel.py:363` usa a allowlist como destino de alerta
```

---

## 5. A ordem de execução

```
E  (registro, 10 min)  →  A  →  B  →  C  →  D  →  G  →  F
```

🔴 **E vem primeiro** porque se a decisão for **(B) manter test**, os blocos A–D
continuam certos mas **o piloto não é com cliente real** — e o executor precisa
saber disso antes de escrever o gate.
