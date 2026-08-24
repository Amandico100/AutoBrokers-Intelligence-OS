---
> **Status:** relatório final de execução — pré-condição do gate
> **Criado em:** 23/08/2026
---

# Relatório de execução — SPEC-084.2: O CONTRATO

**Produto:** AutoBrokers Intelligence OS
**Branch:** `feat/spec084-a-fabrica-de-rotas` · **Worktree:** `AutoBrokers-FIX`
**Executor:** Claude Opus 5 (1M), com 5 subagentes de investigação e 5 juízes
**Início e conclusão:** 23/08/2026
**Commit inicial:** `0d98b19` · **Commit final:** ver §12
**Estado final:** CONCLUÍDA COM RESSALVAS — *a liberação é do juiz*

> **O achado, na frase que o define:**
> *As 19 rotas AAA respondiam 100% das telas da URA, com 100% de determinismo.
> E nenhuma acionava.*

---

## 0. Declaração de integridade

- [x] Nenhum motor paralelo foi criado. O corredor continua **um só**, a régua
      **uma só**, o motor **um só**. O `friendly` da ferramenta — que era uma
      segunda fonte de verdade — foi **removido**, não substituído.
- [x] Nenhuma migration foi criada, movida ou aplicada. **Esta SPEC não tocou
      em SQL.**
- [x] Nenhum segredo exposto. Auditoria de PII rodada; ver §7.
- [x] Nenhum escopo reduzido. Os seis consertos foram executados.
- [x] As seis proibições cumpridas: ✗ não ligou agente · ✗ não enviou mensagem
      · ✗ só `SELECT` · ✗ não acessou portal · ✗ não imprimiu segredo · ✗ não
      fez merge na `main`.

---

## 1. O achado, e o controle que o define

📊 Rodado no motor real, pelo caminho que o LLM percorre — só os campos que
`InsurerDispatchInput` **declara** podem chegar a `build_dry_run_plan`:

```
com TUDO que a ferramenta consegue carregar   →  missing_data     0 de 19
com os slots que ela NÃO carrega, em memória  →  ready_to_send   19 de 19
```

🔴 **O corredor estava certo. O bloqueio estava ANTES dele** — no contrato, que
é onde a régua da SPEC-084.1 não olha. E a causa foi a própria SPEC-084.1: ela
acrescentou slots a `required_slots` e não estendeu o schema.

⚠️ A prova de que a pergunta era legítima já estava escrita: 📊 **19 dos 22
slots já tinham redação em `_COMO_PERGUNTAR`.** O produto sabia perguntar e não
sabia guardar.

---

## 2. Os seis consertos

### C1 · O contrato não tinha campo para o que o portão exige

**Decisão, por nota:** (a) acrescentar campos **72** · (b) portão consultar o
padrão do motor e o galho condicional **58** · **(c) as duas, cada uma no seu
caso — 94** ✅

📊 Medi a origem dos 16 slots órfãos. **Nenhum tem constante no subserviço** —
nenhum é "o motor preenche". Mas se dividem em duas causas **opostas**:

| | quantos | por quê |
|---|---|---|
| **pergunta de verdade** → (a) | 14 | `local_seguro` sozinho bloqueia 13 rotas, e o corredor diz por que não tem default: *"responder 'sim' no escuro **rebaixa a prioridade** de quem está parado num lugar perigoso"*. `idade_aparelho_opcao` decide COBERTURA |
| **filho de galho não tomado** → (b) | 2 | `transporte_destino` e `taxi_passageiros` pendem de `meio_de_transporte`, cujo default é `"Não"` — o produto exigia saber *"para quantos passageiros no táxi?"* de quem pediu guincho |

🔴 Um remédio só erra numa das duas, e o erro de (b) aplicado aos 14 é o pior
possível: **um portão que libera acionamento sem saber se a pessoa está segura.**

O mecanismo de (b) não é exceção nova: o portão já pula `fallback_adaptive` e
`noop`. **`sem_chute` é o terceiro membro da família** — o passo que declara
*"não tenho default honesto e escalo quando a tela aparecer"*. E não afrouxa:
📊 `taxi_passageiros` continua cobrado em `porto/auto/taxi`, a rota que É sobre
táxi.

🔴 **O guarda que o próprio C1 prometia e eu não tinha escrito** —
`test_o_contrato_alcanca_o_portao` — foi apontado por um subagente. Ele acusou
na estreia o que esta mesma edição deixara passar: **16 slots órfãos em rotas
fora das 19**. Fechar só o que o gate mede é comprar o gate.

✅ **E a P-084-61 fechou**, porque a razão de estar travada deixou de existir:
`zurich/auto/guincho` exigia `local_seguro` **e** `local_seguro_opcao` — o mesmo
fato com dois nomes, duas perguntas ao segurado.

### C2 · O formulário nativo travava na PENÚLTIMA tela

```
montar_resposta_de_flow(flow, caso COMPLETO)  →  ok=False
   missing = rb_EmGaragemOuEstacionamento, rb_NivelDaRua, rb_InformacoesLocal
CONTROLE, mesma sessão + os três slots       →  ok=True
CONTROLE NEGATIVO, tirando UM por vez        →  cada slot derruba UM campo
```

🔴 O desfecho era o pior possível: a sessão nascia `ready_to_send` — o produto
**prometia** acionar —, falava ~25 telas com a URA e morria na penúltima, com o
segurado esperando na rua.

⚠️ E o C2 causou uma perda que eu não tinha visto: com os três em
`required_slots`, a lista de coleta passou a montá-los pela origem `subservico`
e eles **perderam a pergunta e as opções exatas da seguradora**. `_somar` agora
ENRIQUECE em vez de ignorar.

### C3 · A ferramenta dizia "a hdi não atende socorro mecânico" — sobre uma rota AAA

**Decisão, por nota:** (A) manter a lista à mão, completando-a **12** ·
**(B) DERIVAR dos playbooks — 94** ✅

📊 A lista literal de cinco nomes não conhecia os quatro subserviços de auto que
nasceram depois dela, conhecia `pane_seca` (que é apelido, não rota), e comparava
a string **crua**.

🔴 A prova que decidiu: **derivada dos 14 playbooks, a tabela aponta UM ÚNICO
subserviço ambíguo — `chaveiro` — que é exatamente a exceção que a lista à mão
precisava declarar num SEGUNDO lugar.** Uma derivação que descobre sozinha a
única exceção que a lista tinha de escrever prova que a lista era um resumo mal
copiado da tabela.

```
rotas com corredor errado    5 → 0
rotas em handoff (chaveiro) 14 → 14      ← o guarda NÃO afrouxou
apelidos de auto que erram  25 → 0
```

⚠️ E `chave`, apelido de `chaveiro`, **contornava o guarda do chaveiro**: o ramo
do handoff também comparava a string crua. O incidente que o comentário dizia
impedir acontecia por baixo dele.

### C4 · A yelum tem QUATRO formulários; o produto conhecia UM

📊 Varredura própria dos 28.096 eventos:

```
857030507196739   (veículo, local e ocupantes) V2   hdi   18/07   ✅ registrado
2887131368288279  (local e ocupantes)               yelum 07/08 e 17/08
3206000179602236  (veículo, local e ocupantes) V2   yelum 19/08
1579547063352571  Informar endereço V2              yelum 03/08   ⏸️ P-084-68
```

**Decisão:** (A) reusar o V2 inteiro **12** · **(B) registro próprio reusando as
TELAS por referência — 94** ✅. (A) foi medida e reprovada: reusar o V2 exigiria
dois campos que este formulário **não mostra** — `formulario_incompleto` em 100%
dos casos, para sempre.

🔴 **E o registro revelou três rotas que ninguém via:** `hdi/auto/chaveiro`,
`yelum/auto/pneu` e `yelum/auto/socorro_mecanico` — esta última uma rota 88/88 —
batiam no formulário e não o respondiam. **É a medição que muda o escopo, não a
preferência.**

### C5 · Três textos chegavam errados ao cliente — e o defeito era de classe

| defeito | o que o cliente lia |
|---|---|
| marcador interno | *"📊 A senha da visita técnica…"* — 📊 significa "número medido" |
| instrução de outro serviço | socorro mecânico: *"alguém para acompanhar o **guincho**"* |
| identificador cru | dossiê ao humano: *"Motivo: sem_chute:transporte_destino"* |

📊 **A classe varrida:** 9 pares herdavam o texto do guincho sendo outra coisa.
Os que têm texto medido ganharam o próprio; os que não têm tela de orientação
ganharam **silêncio** — e para o silêncio existir, `[]` precisou vencer o `or`.

🔴 **Duas afirmações caíram por não estarem no corpus:** *"sem a senha o
prestador não executa o serviço"* e *"a mão de obra é que está coberta"* —
verdade no encanador, **falsa** no eletrodoméstico, onde a mesma URA diz
*"coberto a mão de obra E PEÇAS"*. Regra de CORREDOR não decide cobertura de
ROTA.

⚠️ **Dois defeitos latentes que o texto novo expôs:** o limiar do deduplicador
era proporcional ao texto NOVO (quanto mais rica a redação, mais impossível
colapsar), e **a pontuação entrava na assinatura** — `local` e `local.` eram
palavras diferentes, e a interseção encolhia a cada ponto final.

### C6 · A régua PREMIANDO o buraco

**Decisão, por nota:** (a) sempre RESPONDIDA quando monta **35** · (b) sempre
ORFA_FUNCIONAL **55** · (c) classe nova **25** · **(d) as duas conforme o
produto consiga montar — 92** ✅

📊 `replay.py` nunca chamava `detect_native_flow`; `regua_motor` nem a
reexportava. A tela que TRAVA o acionamento saía do denominador como
`ORFA_INOCUA`, e *"zero órfãs funcionais"* dava 20/20 a duas rotas.

🔴 **Este furo não é o do C8.** O C8 era a régua punindo o comportamento certo.
Este é o inverso, e o mais perigoso: **a régua premiando o buraco.**

⚠️ E o formulário é consultado **ANTES** do passo — única divergência declarada
em relação ao motor. Sem isso, três linhas de âncora de texto comprariam os 20
pontos de volta. 📊 Custo da inversão hoje: **zero**.

---

## 3. O par C6 → C2 → C4, e por que ele é a prova

| momento | hdi/guincho | yelum/guincho | AAA | média |
|---|---|---|---|---|
| antes da 084.2 | 102/106 | 102/106 | 19 | 88,4% |
| **depois do C6** | **82/106** | **86/106** | **17** | **87,6%** |
| depois do C2 | 102/106 | 102/106 | 19 | 88,4% |
| **depois do C4** (só o registro) | 102 | 102 | **17** | **87,5%** |
| **final** | 102/106 | 102/106 | **19** | **88,4%** |

🔴 **A volta é a prova.** O mesmo número, antes pago por uma tela escondida,
agora é ganho por uma tela respondida. As cinco rotas com formulário têm hoje
`of=0` e **todas as telas RESPONDIDA**.

---

## 4. Migrations

**N/A — justificado.** Nenhuma migration criada, alterada ou aplicada. A
proibição nº 3 do Founder (*"PROIBIDO ESCREVER NO BANCO"*) tornaria qualquer
migration uma violação; as leituras foram exclusivamente `SELECT`.

---

## 5. Testes — com saída real

```
$ python scripts/verificar_mutacoes.py
  -> 12 de 12 mutacoes EXECUTADAS e vermelhas

$ python scripts/acionamento_pelo_contrato.py
  ACIONAM: 19 de 19                                    (era 0 de 19)
  CONTROLE 2: 19 de 19 continuam bloqueadas sem o CPF
  CONTROLE 3: cada campo novo derruba as rotas que o exigem
```

**Guardas novos desta SPEC:**

```
test_o_contrato_alcanca_o_portao.py            6 asserções
test_a_linha_do_servico_vem_do_corredor.py    21 asserções
test_o_formulario_nao_e_inocuo.py             27 asserções
test_o_cliente_nao_le_marcador_interno.py     16 asserções
```

**Guardas existentes atualizados (§9.3 — a lição migra, não morre):** cinco.
Cada um afirmava o defeito como invariante e passou a afirmar o conserto, com o
motivo e a data em que a condição mudou.

---

## 6. O que continua vermelho, e a prova de que é anterior

`test_golden_do_eletricista`, `test_handoff_chega_em_alguem`,
`test_corredor_residencial_yelum`, `test_o_acionamento_nao_pede_o_impossivel`,
`test_spec017_dispatch` e outros — **provados vermelhos no commit anterior**,
num `git worktree` em `HEAD`, **com linha de controle**: um teste sabidamente
verde rodou verde lá.

⚠️ Sem esse controle a medição mente: 📊 na primeira tentativa o worktree nem
chegou a ser criado (`Filename too long`), e **todas** as linhas saíram *"já
estava vermelho"* — porque o `cd` falhava e o `||` disparava.

---

## 7. Segurança e PII

- 📊 `scripts/auditar_pii_no_codigo.py` rodado no escopo desta SPEC.
- ⚠️ **O repositório era público e o Founder o tornou privado durante a
  execução.** A limpeza dos ~89 identificadores restantes segue em
  `CHANGE-ADDENDA` como ESSENCIAL, aguardando autorização (P-084-66).
- Nenhum dado de pessoa foi introduzido por esta SPEC.

---

## 8. Riscos remanescentes

| # | risco | gravidade | onde está |
|---|---|---|---|
| 1 | 🔴 **o `flow_id` nunca chega** — sem isso, C2 e C4 entregam dossiê, não acionamento automático | alta | P-084-67 |
| 2 | a mutação foi commitada **pela segunda vez**; o guarda só acusa depois | alta | P-084-74 |
| 3 | o 4º formulário da yelum não foi transcrito, e um passo responde texto a ele | média | P-084-68 |
| 4 | qual `flow_id` ecoar à yelum não é decidível offline | média | P-084-69 |
| 5 | a regra dos "18 anos" é afirmada em 6 corredores onde o acervo não a mostra | média | P-084-70 |
| 6 | `confirm_first` roda antes da validação de subserviço | média | P-084-77 |

---

## 9. Canário Amandus → Resulta → AutoFleet

⚠️ **NÃO EXECUTADO — é proibição do Founder, não omissão.** O canário exige
ligar agente e enviar mensagem, as duas primeiras proibições.

| | prova | não prova |
|---|---|---|
| o gate do contrato | que o dado TEM COMO chegar ao portão | que a URA aceita a resposta hoje |
| replay contra 43 corpora | que o corredor responde a tela real | que a mensagem SAI pelo canal |
| 12 mutações | que os guardas veem o que dizem ver | que o `flow_token` chega (P-084-67) |

---

## 10. Declaração final

**FATO.** Seis consertos executados, medidos e commitados sozinhos. **19 de 19
rotas AAA acionam pelo caminho real da ferramenta** — eram 0. O portão continua
cobrando o que é legítimo (controle 2 e 3). 12 de 12 mutações vermelhas. A régua
passou a enxergar o formulário nativo, e a nota caiu e voltou, agora ganha.
Nenhum motor paralelo foi criado.

**INFERÊNCIA.** As 19 rotas *devem* levar um acionamento do começo ao fim — mas
isso é inferido de replay contra corpus gravado e de simulação do portão, **não
de um acionamento real**. E há um limite medido: enquanto o `flow_token` não
chegar (P-084-67), as rotas com formulário pausam com a resposta pronta em vez
de enviá-la.

**RECOMENDAÇÃO.** Ligar a leitura de `galaxy_message` (P-084-67) é o próximo
bloco, e é o que separa "dossiê pronto" de "acionamento automático". Depois,
o canário na Amandus.

> 🔴 **A LIBERAÇÃO É DO JUIZ.** Este relatório é a pré-condição do gate, não o
> gate. Nenhum merge na `main` foi feito.
