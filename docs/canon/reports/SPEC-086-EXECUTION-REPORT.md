# Relatório de execução — SPEC-086: o atendimento termina, e o produto sabe

**Produto:** AutoBrokers Intelligence OS
**SPEC:** `docs/canon/specs/SPEC-086-o-atendimento-termina-e-o-produto-sabe.md` (v1)
**Branch:** `feat/spec086-o-atendimento-termina-e-o-produto-sabe`
**Executor:** Opus 5 (1M) · 26/08/2026
**Commit inicial:** `871298e` · **Commit final:** `fbbfb7a` + este relatório
**Estado final:** CONCLUÍDA COM RESSALVAS

---

## 🧑 PARA O FOUNDER — uma página

### O que muda

Sexta-feira você abre a tela e ela responde, **com número**: quantos
atendimentos terminaram, quantos ainda esperam alguém, e quantos **morreram
esperando**.

### 🔴 Quatro coisas que você precisa saber

**1. A SPEC acertou os quatro números. Todos.**

| a SPEC dizia | 📊 eu medi |
|---|---|
| `conversations` 671 | **671** ✅ exato |
| `resolvido_em` preenchido: 0 | **0** ✅ |
| `resolucao_motivo`: 0 | **0** ✅ |
| status `open`=614, `active`=57 | **614 e 57** ✅ exato |
| `work_waits` não existe | **não existia** ✅ |
| 5 runs presos em `queued` | **5** ✅ (o mais velho há **29** dias) |

> **O produto nunca marcou uma conversa como resolvida. Nem uma, em 671.**

**2. 🔴 E a tubulação já estava inteira — faltava quem DECIDISSE.**

📊 `attendance_ficha.gravar()` **já escrevia** as duas colunas
(`attendance_ficha.py:342-344`), e a fase `resolvido` já existia em
`derivar_fase`. ⛔ `grep '"resolvido_em"'` fora daquele arquivo devolve **zero**:
nenhum chamador jamais preencheu o campo. **Esta SPEC ligou o que existe.**

**3. ⚠️ Um dos quatro motivos da SPEC mentia sobre o que guarda.**

A SPEC pede `acionamento_aberto` quando *"o robô conclui o acionamento"*. 📊 Mas
*"aberto"* é o **meio**: `derivar_fase` chama o estado com protocolo de
`acompanhando` — *"há protocolo; espera-se o prestador"*. **Marcar ali contaria
como "terminou" um guincho que nunca chegou.**

📊 E o produto já sabe o que é terminar, e são **dois** desfechos de sucesso:

```
FASES_ENCERRADAS = ("needs_human", "test_aborted", "encaminhado", "resolvido")

`resolvido`     o serviço foi prestado e o ciclo fechou
`encaminhado`   o formulário/orientação já está em mãos (P-46)
```

🔴 `CLAUDE.md` §12.1 — *"se o nome de um campo mente sobre o que ele guarda,
conserte o campo"*. Virou **`acionamento_concluido`**, e `encaminhado` entrou ao
lado.

**4. ⚠️ Os cinco runs presos não são atendimento.**

📊 São **todos** `intelligence.detect_signals` — jobs de background. Não os torna
menos reais (ninguém foi avisado em 29 dias), mas **a prova de que o atendimento
apodrece é a conversa de 730 horas, não eles**. Esta SPEC os torna visíveis; **não
os desatola** — isso é decisão sua (P-086-D).

---

## 0. Declaração de integridade

- [x] Nenhum motor paralelo. 🔴 O vigia foi **estendido**, não recriado; o
      alerta usa o **mesmo** `_avisar_suporte`; o contador da sexta-feira entrou
      na tela que já existe.
- [x] Duas migrations novas, aditivas, idempotentes, expand-first, não destrutivas.
- [x] ⛔ **Nenhuma mensagem saiu** · 📊 `platform_sends` 24h: **0**.
- [x] ⛔ **Nenhum agente ligado** · 📊 `attendance` com `is_active`: **0 de 4**.
- [x] ⛔ Nenhum portal, nenhuma variável de produção, nenhum dado pessoal impresso.
- [x] ⛔ `git add -A` **não foi usado** (P-247).
- [x] ⛔ Restauração de mutação **por cópia**, sha256 conferido — e o esquema de
      backup foi consertado no meio (ver §4).

---

## 1. O que cada bloco entregou

### BLOCO A — a conversa passa a ter FIM · `990d6e6`

CHECK de lista fechada + CHECK de coerência (`resolvido_em` e `resolucao_motivo`
andam juntos, senão a conversa *"acabou por um motivo, em momento nenhum"* e
some de toda consulta por período).

**Quatro dos cinco motivos têm escritor:**

```
acionamento_concluido    ✅ o dispatch, ao chegar em `resolvido`
encaminhado              ✅ o dispatch, ao chegar em `encaminhado`
fechado_por_humano       ✅ o botão de encerrar do painel
expirou                  ✅ o vigia, depois de 3 avisos ignorados
resolvido_pelo_segurado  🔴 ninguém — P-086-A, e foi decisão
```

⛔ `needs_human` e `test_aborted` **não** terminam nada: no primeiro tem gente
esperando, o segundo é simulação.

### BLOCO B — a espera vira objeto · `990d6e6` + `fbbfb7a`

🔴 **`work_run_id` aceita NULO, e é isso que faz o bloco existir.** 📊 A proposta
pedia `NOT NULL`; são **4** `work_runs` de acionamento contra **671** conversas.
Com `NOT NULL` não haveria onde pendurar a espera da conversa comum — o caso do
piloto. **A âncora é a CONVERSA.**

⚠️ **E eu quase entreguei o bloco de enfeite.** Escrevi a pendência P-086-B
dizendo *"`abrir_espera` existe e ninguém chama"* — e reler isso mostrou que era
pendência demais: com `work_waits` vazia, o vigia varre nada e a sexta-feira
responde `ainda_esperam: 0` para sempre. 📊 O sinal medido existia: `needs_human`.

```
needs_human      → abre `esperando_humano`, escopo `acionamento`
qualquer outra   → SATISFAZ (o acionamento voltou a andar)
```

⚠️ Sem a segunda metade, o vigia cobraria uma conversa que voltou a andar
sozinha — **e alarme falso é como se ensina uma equipe a ignorar alarme**.

### BLOCO C — a espera vencida acorda alguém · `990d6e6`

O vigia que já existe ganhou `varrer_esperas_vencidas`: **mesmo módulo, mesmo
agendador, mesmo `_avisar_suporte`**. ⛔ **Zero caminho para o segurado** — um
watchdog que fala com o cliente é um robô que acorda às 3h da manhã.

⚠️ E o teto da passada (50) é **declarado**: se encher, sai uma linha de aviso.
A lição da P-090-03, migrada.

### BLOCO C.1 — 🔴 o conserto de agosto NÃO era observável

📊 **As três perguntas da SPEC não tinham resposta, e a causa está medida:**

```
quantos alertas saíram desde o conserto? ..... NÃO DÁ PARA SABER
quantos eram de quem realmente esperava? ..... NÃO DÁ PARA SABER
o teto de lembretes já foi atingido? ......... NÃO DÁ PARA SABER
```

📊 `_avisar_suporte` **não gravava em lugar nenhum contável**. `platform_sends`
tem **5 linhas na base inteira**, todas de outra coisa (`billing`,
`acionamento_protocolo`), a mais recente de **19/08** — **dois dias antes do
conserto**. E 📊 hoje há **0** conversas em `HUMAN_REQUESTED`.

⛔ **Não inventei que funcionou.** A SPEC prevê exatamente isso: *"se o dado não
existir, esta é a resposta; tornar observável é o trabalho do bloco"*. Agora
`handoff.realertado` e `handoff.teto_de_lembretes` são eventos contáveis em
`work_events`.

⚠️ **Gate ② (ajustar o teto se for ruidoso) não foi executado, e é honesto:**
📊 zero alertas desde o conserto e zero `HUMAN_REQUESTED` hoje. **Não há como
medir ruído sem volume**, e mexer no teto sem número seria adivinhar.

⚠️ **Gate ③ (o marcador sobrevive a reinício?):** 🔴 **não sobrevive** — vive no
Redis com TTL. Está escrito, e agora é detectável. P-086-C.

### BLOCO D — a pergunta da sexta-feira · `990d6e6`

Três contadores na rota `app/api/dashboard/atendimentos`, **sem tela nova**.

🔴 `morreram_esperando` sai de **fora** de `terminaram`: contá-los juntos faria a
sexta-feira dizer *"12 terminaram"* num dia em que sete morreram esperando — e é
justamente essa diferença que a SPEC inteira existe para criar.

---

## 2. Migrations — aplicadas e verificadas

```
20260826_04 · a conversa tem fim
  🔴 OS VALORES DO CHECK, no APPLY:
     acionamento_concluido · encaminhado · resolvido_pelo_segurado
     fechado_por_humano · expirou
  V2 CONTROLE (transação desfeita por `raise`):
     motivo INVÁLIDO recusado?  t     ← o testado foi `acionamento_aberto`,
     motivo SEM data recusado?  t        o nome que a PRÓPRIA SPEC pedia
     data SEM motivo recusada?  t
     motivo VÁLIDO aceito?      t     ← a linha que dá direito à conclusão
     outros erros: []

20260826_05 · work_waits
  🔴 OS VALORES DOS CHECKS: kind(3) · status(4) · avisos>=0 · satisfação coerente
  V3 CONTROLE, SETE linhas:
     kind inválido?        t   status inválido?      t
     avisos<0?             t   satisfação pela metade? t
     cross-tenant?         t   DOIS ativos no escopo?  t
     🔴 VÁLIDO SEM work_run aceito?  t
     outros erros: []
```

---

## 3. Testes — saída real

```
test_o_atendimento_termina_e_o_produto_sabe.py    52 passed
test_o_humano_e_chamado_de_verdade.py (gate ⑥)    22 passed
tsc --noEmit                                       exit 0
```

### As mutações — 41, todas vermelhas

```
CONTROLE (sem mutação) ......  52 passed
41 mutações ................. 41 VERMELHAS · 0 verdes · 0 puladas
VERDE DE NOVO ...............  52 passed
restauração ................. sha256 idêntico nos 8 arquivos
```

🔴 **As três obrigatórias da SPEC, vermelhas:**

```
desligar o filtro de company_id     →  o teste de dois tenants REPROVA
desligar o "não-fala-com-segurado"  →  o teste do BLOCO C REPROVA
gravar valor fora do CHECK          →  recusado antes de chegar ao banco
```

---

## 4. 🔴 Os defeitos — e um deles corrompeu um arquivo

### 🔴 A PRÓPRIA BATERIA corrompeu um `route.ts`

```python
backups = {a: SP / (a.name + ".p086b") for a in ARQUIVOS}
```

📊 **Dois arquivos do conjunto se chamam `route.ts`** —
`conversas/[id]/route.ts` e `atendimentos/route.ts`. Os dois apontavam para o
**mesmo backup**, o segundo sobrescreveu o do primeiro, e a restauração escreveu
o conteúdo de um **dentro** do outro: 📊 **307 inserções, 255 remoções** no
arquivo errado.

⚠️ **O sintoma foi indireto:** duas mutações viraram *"âncora 0x — PULADA"* e o
`VERDE DE NOVO` saiu **vermelho**.

> 🔴 **Sem a linha final de verificação, a corrupção teria ido para o commit** —
> e ela é literalmente a linha que o protocolo exige.

O backup passou a ser por **caminho** (sha do path + nome), não por nome.
⚠️ E a restauração foi por `git checkout` **desta vez com razão**: o conteúdo
correto estava commitado, e o da árvore era corrupção pura — não trabalho não
salvo (a distinção que a P-231 faz).

### 🔴 E oito guardas meus não guardavam — sete pela MESMA doença

📊 A bateria pegou **8 verdes** ao longo desta SPEC:

| # | o guarda | por que passava |
|---|---|---|
| 1 | UNIQUE parcial | `[:220]` alcançava o **índice seguinte**, que também tem `WHERE status='ativo'` |
| 2 | `satisfazer_espera` dois tenants | **não existia guarda nenhum** |
| 3 | rastro contável | contar `_anotar_no_diario(` não vê um `if False:` — **ocorrência ≠ alcance** |
| 4 | payload sem telefone | olhava **um** dos dois escritores |
| 5 | o painel apaga o desfecho | 🔴 **6ª vez**: o comentário cita `.is('resolvido_em', null)` |
| 6 | `satisfazer_espera` alcançável | a mutação punha um `return` antes — **alcance de novo** |
| 7 | o prazo é o do vigia | 🔴 **7ª vez**: `HANDOFF_ALERTA_MINUTOS` está no comentário |
| 8 | uma âncora com indentação errada | virou **PULADA silenciosa** |

> ⚠️ **Sete das oito eram a mesma doença desta execução inteira: a asserção
> lendo a explicação de por que o código deveria existir, e concluindo que ele
> existia.** Cada arquivo de teste desta sequência ganhou um cortador de prosa
> — SQL, Python e TypeScript — **cada um com um controle que prova que corta**.

---

## 5. 📊 A BATERIA

| | |
|---|---|
| rodadas nesta SPEC | 📊 **210** |
| das quais **bateria inteira** | 📊 **4** |
| relógio total esperando a suíte | 📊 **74.7 min** |

```
09:07:29 UTC   871.6 s   937 coletados   3 falhas
09:50:01 UTC   1151.8 s   942 coletados   2 falhas
09:50:03 UTC   1153.9 s   942 coletados   1 falhas
10:05:56 UTC   898.0 s   942 coletados   2 falhas
```

⚠️ 🔴 **E DUAS DELAS RODARAM EM PARALELO, POR ENGANO MEU.** Um `&` no comando do
commit deixou uma bateria solta enquanto a rastreada rodava. 📊 As duas
aparecem no diário no MESMO segundo (09:50:01 e 09:50:03), com **2 falhas** e
**1 falha** — números diferentes para a mesma árvore, no mesmo instante.

> ⛔ **É exatamente a lição de que duas suítes na mesma árvore mentem.** Nenhum
> dos dois números vale; a rodada de 14m57 é a que vale, e ela rodou sozinha.

⚠️ **As falhas não são desta SPEC:**

```
test_a_arvore_ficou_limpa_no_fim   o vazamento de mutação da P-246
test_a_politica_de_autorizacao     🔴 NÃO é teste reprovando: é o node CRASHANDO
```

📊 **E agora há evidência do que eu vinha chamando de "instabilidade":**

```
exit 3221226505  (0xC0000409 — STATUS_STACK_BUFFER_OVERRUN)
Assertion failed: !(handle->flags & UV_HANDLE_CLOSING), file src\winsync.c:76
```

🔴 **É o libuv do Node abortando sob carga**, não uma asserção do produto. O
mesmo arquivo dá **6/6 em três rodadas seguidas** quando roda sozinho.

---

## 6. Pendências abertas

`P-086-A` `resolvido_pelo_segurado` no CHECK e **sem escritor** — e foi decisão ·
`P-086-C` o contador de lembretes vive só no Redis (gate ③, respondido) ·
`P-086-D` 🧑 os 5 runs presos há 29 dias: **visíveis, não desatolados** ·
`P-086-E` `work_effects` sem DDL e sem escritor (herdada da P-086-01).

⚠️ **P-086-B foi FECHADA durante a execução** — ela dizia *"`abrir_espera` existe
e ninguém chama"*, e escrever isso mostrou que era pendência demais.

---

## 7. Separando FATO de INFERÊNCIA

**📊 FATO:** os seis números da §1; a tubulação existente sem chamador; os dois
desfechos de sucesso em `FASES_ENCERRADAS`; `platform_sends` = 5 linhas, a mais
recente de 19/08; 0 `HUMAN_REQUESTED` hoje; 41/41 mutações vermelhas.

**💭 INFERÊNCIA:**

- 💭 Que **3 avisos** (~18 h) é o número certo antes de marcar `expirou`. Sai de
  ~6 h entre lembretes × 3, contra as 730 horas documentadas. **Ninguém mediu
  quanto tempo a Regina realmente leva.**
- 💭 Que 30 minutos é o prazo certo da espera de `needs_human`. É o padrão do
  vigia de handoff, escolhido para ser **o mesmo número** — não porque foi
  medido.

**🔴 RECOMENDAÇÃO:**

1. Na segunda, com o piloto rodando, medir **quanto tempo passa entre o
   travamento e o destrave**. Esse número substitui os dois 💭 acima.
2. 🧑 Decidir sobre os 5 runs presos (P-086-D).
3. Se o grupo reclamar de ruído, o número agora existe: `handoff.realertado` em
   `work_events`, por corretora, por dia.
