# SPEC-086 · O ATENDIMENTO TERMINA — E O PRODUTO SABE

> **O que ela entrega:** o produto passa a saber a diferença entre *"terminou"*,
> *"está esperando"* e *"foi abandonado"*. E quando a espera vence, **alguém é
> avisado** em vez de a conversa apodrecer.
>
> **v1** · 26/08/2026 · commit base `6831879` · repo `AutoBrokers-FIX`

---

## ⚠️ Sobre o número 086

📊 O rótulo *"SPEC-086"* já era usado no código para outra coisa — o conserto do
handoff humano (`SPEC-085:390-392`, e há teste vivo em
`test_o_humano_e_chamado_de_verdade.py:228`).

**Esta SPEC assume o número**, porque é o número pelo qual o Founder conhece a
proposta, e renumerar agora custaria mais confusão do que resolve. 🔴 **O uso
antigo passa a ser citado como "o conserto do handoff (085)"**, e o teste que o
guarda ganha o texto novo no BLOCO F.

---

## 🔴 A razão desta SPEC existir — 📊 quatro números, medidos em 26/08

```
conversas com `resolvido_em` preenchido .....    0   de 671
conversas com `resolucao_motivo` ............    0
work_runs presos em `queued` ................    5   o mais velho há 28 DIAS
tabela `work_waits` .........................  NÃO EXISTE
```

> **O produto nunca marcou uma conversa como resolvida. Nem uma, em 671.**

As colunas existem. **Ninguém escreve nelas.** O resultado é que *"o atendimento
acabou bem"* e *"o cliente desistiu e foi embora"* são, para o banco, **o mesmo
estado**.

⚠️ **E na semana que vem isso vira o problema imediato:** a corretora liga o
atendimento para clientes reais, e **ninguém vai conseguir responder "quantos
atendimentos terminaram?"** — que é a primeira pergunta que qualquer pessoa faz.

## O que esta SPEC NÃO é

⛔ **Não é a trava de posse.** A proposta original (2.707 linhas) era, em mais de
metade, um *hard possession lock* — epoch, fencing, review × takeover, Resume
Pack. 🔴 **O Founder decidiu que ninguém assume:**

> *"Não é para ela assumir o atendimento. É para ele apenas destravar e
> monitorar."*

📊 E a medida concorda: o robô teve **4 acionamentos** e **61 conversas** com
mensagem própria na história do produto. **Escrever arbitragem de posse antes de
existir concorrência real é escrever contra hipótese.**

⚠️ `CLAUDE.md` §11: isto é **proposta de recorte registrada**, não corte
silencioso. O que saiu está listado na §6, com o gatilho que faz cada peça
voltar.

---

## 0. O TESTE DO PRODUTO — a régua desta SPEC inteira

> **Sexta-feira. A Regina abre a tela e pergunta: "dos atendimentos desta
> semana, quantos terminaram, quantos ainda esperam alguém, e quantos morreram
> esperando?" — e a tela responde, com número.**

⛔ **Qualquer bloco que não sirva a esse parágrafo sai desta SPEC.**

---

## 1. O ESTADO DE HOJE — 📊 medido em 26/08/2026

### 1.1 · Nada é marcado como terminado

📊 `conversations` tem `resolvido_em` e `resolucao_motivo`. **Zero linhas
preenchidas, em 671 conversas.**

⚠️ **E o `status` não substitui:** 📊 os valores em uso são `open` (614) e
`active` (57) — e nenhum deles quer dizer *"acabou"*.

### 1.2 · A espera não é um objeto

📊 `work_waits` **não existe**. Hoje "esperar" é:

```
um status ....................... que não distingue esperar de estar parado
um `retry_scheduled` ............ que é reexecução, não espera
o `handoff_watchdog` ............ que só olha `HUMAN_REQUESTED`
nada ............................ para "esperando o cliente responder"
```

🔴 **E o custo disso está documentado no próprio produto:**
[handoff_watchdog.py:3-4](../../backend/app/tasks/handoff_watchdog.py#L3-L4) registra uma
conversa **presa por ~730 horas — trinta dias** — porque *nenhum job lia
`conversations.status`*.

### 1.3 · E há coisa presa AGORA

```
📊 work_runs em `queued` .....  5
📊 o mais velho ..............  28 dias
```

⚠️ **Isto não é hipótese: são cinco trabalhos enfileirados que nunca rodaram**, e
ninguém foi avisado. `CLAUDE.md` §9.2 — medir vence deduzir, e a medida diz que
o buraco está aberto hoje.

### 1.4 · O que JÁ existe e não deve ser duplicado

⛔ `CLAUDE.md` §5 proíbe criar em paralelo. 📊 O que existe e serve:

| | onde | serve para |
|---|---|---|
| `work_runs` · `work_steps` · `work_events` | Supabase | o ciclo de vida durável **já existe** |
| o scheduler | `buffer_processor.py:88-95` | `AsyncIOScheduler` de 1s, no processo do webhook |
| `handoff_watchdog` | `app/tasks/` | já varre e já alerta — **estende-se, não se recria** |
| `dispatch_watchdog` | `app/tasks/` | o Vigia, cron de 20s |
| o governador de saída | `platform_outbound.py:125-145` | 12/h · 20 novos/dia · janela · domingo bloqueado |

🔴 **Nenhum motor novo. Nenhum scheduler novo. Nenhuma fila nova.**

---

## 2. ⛔ AS TRAVAS — valem em todos os blocos

```
⛔ NENHUMA mensagem sai para segurado durante a execução desta SPEC.
⛔ NENHUM agente de atendimento é ligado. Os quatro estão `is_active=false`.
⛔ NENHUMA entrada em portal de seguradora.
⛔ Banco: SELECT livre; escrita só pelas migrations desta SPEC.
⛔ NUNCA imprimir CPF, telefone, apólice, placa ou nome de pessoa.
⛔ NÃO mexer em variável de ambiente de produção.
⛔ NUNCA `git add -A` — 📊 em 25/08 isso levou uma mutação para dentro de um
   commit, pela segunda vez (P-247). Arquivo por arquivo.
```

---

# BLOCO A · A conversa passa a ter FIM

## O problema

📊 `resolvido_em` e `resolucao_motivo` existem e têm **0 linhas**. O produto não
sabe dizer que um atendimento acabou.

## O conserto

**Quem escreve, e quando:**

```
o robô conclui o acionamento          → resolvido_em, motivo='acionamento_aberto'
o segurado diz que resolveu           → motivo='resolvido_pelo_segurado'
a atendente fecha na tela             → motivo='fechado_por_humano'
🔴 a conversa vence sem resposta       → motivo='expirou'    ← o BLOCO C escreve
```

⚠️ **E `resolucao_motivo` é uma lista fechada, com CHECK.** 📊 A SPEC-093 aprendeu
isso da pior forma: ela pediu `destravado_por_humano`, o banco recusou porque não
estava no CHECK de `unblock_state`, e o executor teve de escolher outro valor no
meio da execução.

> ⛔ **Toda migration desta SPEC lista os valores do CHECK no APPLY, e o teste
> tenta gravar um valor inválido e exige que o banco RECUSE.**

## O gate

```
① robô conclui acionamento → `resolvido_em` preenchido, motivo certo
② segurado diz que resolveu → motivo diferente do ①
③ 🔴 valor fora do CHECK → o banco RECUSA          (e o teste prova a recusa)
④ conversa já resolvida não é resolvida de novo    (idempotente)
⑤ dois tenants: resolver em A não toca B
```

---

# BLOCO B · A espera vira objeto

> 🔴 **É o coração da SPEC**, e é o que a proposta original acertou.

## O problema

📊 Não existe `work_waits`. "Esperando o cliente" e "parado porque quebrou" são o
mesmo estado — e por isso ninguém consegue varrer as esperas vencidas.

## O conserto

Uma tabela **subordinada**, mínima:

```
work_waits
  id · company_id · conversation_id · work_run_id (NULO permitido)
  kind          esperando_cliente | esperando_seguradora | esperando_humano
  scope         para "um wait ativo por escopo"
  status        ativo | satisfeito | vencido | cancelado
  vence_em      timestamptz
  satisfeito_por · satisfeito_em
```

## 🔴 `work_run_id` PRECISA aceitar NULO — e a proposta errava aqui

📊 A proposta original declarava `work_waits.work_run_id NOT NULL`. **Mas conversa
de WhatsApp não cria Work Run**: 📊 existem **4** `work_runs` de acionamento na
história inteira, contra **671** conversas.

> ⛔ **Com `NOT NULL`, o bloco não executa: não há onde pendurar a espera da
> conversa comum, que é justamente o caso do piloto.**

⚠️ **A âncora é a CONVERSA.** O `work_run_id` entra quando existir.

## Multi-tenant

```
company_id NOT NULL · RLS com policy · 🔴 E FILTRO NO CÓDIGO
```

⚠️ 📊 `CLAUDE.md` §7: o backend usa **service role**. RLS sem filtro no
repositório **não protege nada**. E há precedente: `work_effects` tem RLS ligada
e **0 policies**. **O teste de dois tenants é obrigatório.**

## O gate

```
① criar wait de conversa SEM work_run → funciona
② dois waits ativos no mesmo escopo → o banco RECUSA        (UNIQUE parcial)
③ satisfazer um wait → status muda, `satisfeito_por` preenchido
④ 🔴 tenant A não enxerga wait de B — pelo REPOSITÓRIO, não só pela RLS
⑤ mutação: desligue o filtro de `company_id` e ④ TEM de ficar vermelho
```

---

# BLOCO C · A espera vencida acorda alguém

## O problema

📊 Cinco `work_runs` presos em `queued`, o mais velho há **28 dias**. E uma
conversa documentada presa por **730 horas**.

## O conserto

O `handoff_watchdog` — **que já existe e já varre** — passa a varrer `work_waits`
também.

```
wait vencido →  registra `work_events`  (tipo próprio, contável)
             →  alerta o canal que a corretora configurou
             →  🔴 e a conversa vira `resolucao_motivo='expirou'`
                 se ninguém agir depois de N varreduras
```

## ⛔ O que ele NÃO faz

```
⛔ NÃO manda mensagem para o segurado. Nenhuma. Nunca.
```

🔴 **Um watchdog que fala com o cliente é um robô que acorda às 3h da manhã.**
📊 O caminho de acordar o segurado já existe e já tem governador
(`platform_outbound.py`) — e **é o BLOCO D da SPEC-093, com corte de 24h e
prévia.** Este bloco **avisa a corretora**, e para aí.

## O gate

```
① wait vence → 1 `work_events` contável, com o tipo certo
② 🔴 ZERO mensagens para segurado          (linha de controle: conte `platform_sends`)
③ wait satisfeito antes de vencer → nada acontece
④ vencido e ignorado N vezes → conversa marcada `expirou`
⑤ dois tenants: o alerta de A não vai para B
```

🔴 **A mutação obrigatória:** desligue o `⛔ não manda para segurado` e o teste ②
tem de ficar **vermelho**. Se continuar verde, o guarda não guarda nada.

---

# BLOCO C.1 · 🔴 O conserto de agosto FUNCIONOU? Ninguém mediu.

## Por que este bloco existe

📊 O `RASCUNHO-SPECS-FUTURAS.md:183-187` do canon registra que **metade da 086 já
foi feita**:

> *"O grupo recebia alerta de conversa que ninguém esperava. Conserto aplicado
> (marcador compartilhado no Redis, teto de lembretes, 'só avisa quem espera') —
> **falta medir se funcionou e fechar as bordas.**"*

⚠️ **Um conserto sem medição é uma hipótese com data de aplicação.** E este é o
alarme que a corretora vai receber na semana que vem: se ele avisar demais, ela
desliga; se avisar de menos, ninguém vai.

## O que medir — e são três perguntas com resposta numérica

```
📊 quantos alertas saíram desde o conserto? por corretora?
📊 quantos eram de conversa que REALMENTE esperava alguém?
🔴 o teto de lembretes já foi atingido alguma vez?
   (se nunca, ou ele é frouxo demais, ou não há volume — e as duas
    conclusões são diferentes)
```

⚠️ **Se o dado não existir, esta é a resposta**: o conserto não é observável, e
tornar observável é o trabalho do bloco. ⛔ **Não invente que funcionou.**

## O gate

```
① as três perguntas têm resposta numérica, ou está escrito por que não têm
② 🔴 se o alerta for medido como ruidoso, o bloco AJUSTA o teto — com o número
③ o marcador de Redis sobrevive a reinício, ou está escrito que não sobrevive
```

---

# BLOCO D · A pergunta da sexta-feira tem resposta

## O problema

Mesmo com A, B e C prontos, **alguém precisa conseguir perguntar.**

## O conserto

Uma consulta, e a tela que já existe passa a mostrá-la.

```
dos atendimentos do período:
   terminaram ...........  resolvido_em preenchido, por motivo
   ainda esperam ........  work_waits ativos, por kind
   morreram esperando ...  motivo='expirou'
```

⚠️ **Sem tela nova.** 📊 `app/dashboard/atendimentos/fila` já existe e já lê
`unblock_state`. **Ganha três contadores no topo.**

## O gate

```
① a consulta responde com número, e o número bate com o banco
② período vazio → zeros, não erro
③ dois tenants: o número de A não inclui B
```

---

# BLOCO E · A prova

```
① os gates de A, B, C, D passam
② 🔴 os quatro agentes `attendance` continuam `is_active=false`
③ 🔴 ZERO mensagens enviadas durante toda a execução
④ a bateria inteira, com o número de rodadas do diário
⑤ dois tenants em todos os blocos
⑥ 🔴 o teste do handoff (085) continua verde — o número 086 mudou de dono,
   o conserto dele não
```

## 🔴 As mutações obrigatórias

```
desligue o filtro de company_id       → o teste de dois tenants REPROVA
desligue o ⛔ não-fala-com-segurado    → o teste do BLOCO C REPROVA
grave valor fora do CHECK             → o banco RECUSA
```

⚠️ **Restaurar por CÓPIA, nunca por `git checkout`** — `git diff --quiet` diz
"idêntico" sobre arquivo que ele nem rastreia (P-231).

---

## 6. 🔴 O QUE SAIU DA PROPOSTA — e o gatilho de cada peça

| peça | por que saiu | **volta quando** |
|---|---|---|
| hard possession lock (epoch/fencing) | 🧑 o Founder decidiu que ninguém assume | duas pessoas falarem por cima do robô no piloto |
| review × takeover | mesma razão | idem |
| Resume Pack (§9, §10) | existe para **entregar** o caso a quem assume | quando alguém assumir de verdade |
| Insurer Human Bridge (§11) | 📊 **4 acionamentos** na história | o piloto mostrar o especialista aparecendo |
| perfis de follow-up (§18) | 💭 depende de tempos que ninguém mediu | o piloto medir os tempos |
| `execution_control_epoch` no run | 📊 0 `owner_user_id` em 2.738 runs | quando "assumir" existir |

> ⚠️ **Nada aqui foi julgado ruim.** Foi julgado **cedo** — e a diferença é que
> cada linha acima tem um gatilho medível, não uma promessa vaga.

---

## 7. O que fica pendente

```
P-086-01  `work_effects` continua sem DDL no repositório e sem escritor
P-086-02  os 5 `work_runs` presos em `queued` há 28 dias: esta SPEC os torna
          VISÍVEIS, não os desatola. Desatolar é decisão de operação.
P-086-03  `conversations.status` tem só `open`/`active` — nenhum diz "acabou".
          Esta SPEC usa `resolvido_em`; unificar os dois é dívida.
```

---

## 8. A ordem de execução

```
A  →  B  →  C  →  D  →  E
```

💭 **~3h.** O BLOCO B domina (tabela nova, RLS, filtro, dois tenants).

🔴 **A não pode vir depois de C**, porque C escreve `resolucao_motivo='expirou'` —
e escrever num campo cujo CHECK ainda não existe é o erro que custou uma
correção no meio da SPEC-093.
