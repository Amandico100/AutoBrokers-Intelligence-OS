# PROMPT DE EXECUÇÃO — SPEC-085

> **Cole isto inteiro num chat novo.** Ele é o briefing de quem vai executar.
> 24/08/2026 · commit base `401ab33` · repo `AutoBrokers-FIX`

---

Você vai executar a **SPEC-085 · O destravamento não trava em silêncio** do AutoBrokers.ai.

## ⛔ AS TRAVAS. Leia antes de tudo, e elas não são negociáveis.

```
⛔ É PROIBIDO LIGAR AGENTE DE ATENDIMENTO.
   📊 Os quatro agentes `attendance` estão `is_active = false` no banco, e
   CONTINUAM. A única forma de ligar é a corretora clicando no botão.

⛔ NENHUMA MENSAGEM SAI PARA SEGURADO REAL.
   `INSURER_DISPATCH_LIVE` fica FECHADO. O ensaio roda em DRY-RUN.

⛔ SÓ AMANDUS SEGUROS nos ensaios. Ela é uma corretora FICTÍCIA e existe para
   isso. 🔴 A única corretora pareada de verdade é a AUTOFLEET — não a toque.

⛔ NO BANCO DE PRODUÇÃO: somente SELECT, fora das migrations desta SPEC.

⛔ NUNCA imprima CPF, telefone, apólice, placa ou nome de pessoa. Mascare ou
   agregue. Se um número identifica alguém, ele não entra em resposta nenhuma.

⛔ AVISE O FOUNDER ANTES de qualquer coisa que envie, ligue ou publique.
```

## 🔴 O CONTEXTO QUE MUDA COMO VOCÊ LÊ O BANCO

**Tudo até hoje foi TESTE.** Isso muda a interpretação de quase todo dado:

- 📊 Das **648** conversas, **588 são do ESPELHO** — conversas **humanas** da corretora no WhatsApp, espelhadas para o painel. `espelho_chat.py:592` grava `role='assistant'` para **a pessoa que atendeu**, não para o robô.
- 🔴 **O robô falou com segurado no WhatsApp TRÊS vezes na história do produto**: `04/07` (379 msgs) · `06/07` (2) · **`18/08` (165) — a máquina de lavar.**
- ✅ **A máquina de lavar é o ÚNICO teste ponta a ponta com cliente real e sem travas. NÃO SE REGRIDE DELA. É a referência viva.**
- ⚠️ **Muita coisa parece "pela metade" porque o teste foi até o fim e CLICOU EM SAIR** por causa da trava de finalização. **Meio-caminho no dado NÃO é prova de defeito** — confira o motivo antes de consertar.

> 🔴 **Corolário duro:** se você achar um número que parece um problema grande, **pergunte primeiro de onde vieram aquelas linhas.** Foi assim que a v1 desta SPEC afirmou *"33,2% dos atendimentos travam"* medindo, na verdade, **o time humano da corretora não respondendo**.

---

## 1. LEITURA OBRIGATÓRIA, nesta ordem

```
1. CLAUDE.md                                    as regras invioláveis
2. docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md      🔴 §1, §2, §4, §5, §6 e §7
3. docs/canon/specs/SPEC-085-...-silencio.md    o trabalho
4. docs/canon/reports/SPEC-084.2-EXECUTION-REPORT.md
5. docs/canon/MIGRATIONS-AUTHORITY.md           antes de QUALQUER SQL
6. docs/canon/PENDENCIAS.md                     P-180, P-181, P-182, P-183, P-93
```

## 2. PREFLIGHT

```bash
git rev-list --count HEAD..origin/main    # 🔴 TEM DE SER 0
git checkout -b feat/spec085-o-destravamento-nao-trava-em-silencio
git rev-parse HEAD                        # registre no relatório
git status --short                        # limpo
export PYTHONIOENCODING=utf-8             # 🔴 senão UnicodeEncodeError no Windows
```

⚠️ **A árvore de trabalho é a que está em dia com a `origin/main`, e o preflight MEDE isso.** 📊 Em 24/08 a `AutoBrokers-Opus-Exec` estava 169 commits atrás — se a contagem não der 0, **pare e pergunte qual árvore usar**.

## 3. 🔴 COMO SE TRABALHA — o protocolo, e ele não é sugestão

### As duas contas já estão feitas (§0 da SPEC)

**RISCO 8 · SUPERFÍCIE 3** → equipe completa + red team + juiz final fresco. E a **§5 da SPEC** traz o time de **cada unidade**, escrito por extenso.

### O PAINEL PARALELO — §6.0.0 do protocolo

⛔ **Não rode um juiz genérico três vezes. Rode as lentes de uma vez.**

```
① o builder entrega
② o VERIFICADOR MECÂNICO roda   🔴 é PASSO, não papel. Roda sempre que houve edição
③ 🔴 AS QUATRO LENTES DA §7 DA SPEC, EM PARALELO, CEGAS ENTRE SI:
      · O CÉTICO DA MEDIDA       "este número mede o que a frase diz?"
      · O CÉTICO DO SEGURADO     "promete o que não se cumpre?"
      · O CÉTICO DA VIZINHA      "o que a 086 construiu continua de pé?"
      · O CÉTICO DO ISOLAMENTO   "algo novo atravessa corretora?"
④ VOCÊ funde os achados e aplica o TESTE DO PRODUTO a CADA um:
      muda um byte que chega ao segurado, à corretora, ao banco ou à segurança?
      NÃO → PENDENCIAS.md, e SEGUE
⑤ conserta TUDO de uma vez
⑥ UM JUIZ NOVO confirma — 🔴 ele existe porque CONSERTO CRIA DEFEITO:
   na escrita desta SPEC, dois criaram.

🔴 TETO: 3 rodadas de painel. Bateu sem liberar → CLASSIFIQUE (§6):
   é uma das oito condições do CLAUDE.md §10? Não → entregue o que passou,
   registre o resto, e AVANCE.
```

### O verificador mecânico — e a lista longa

```
build · testes · lint · tipos · migrations · regressão
🔴 E MAIS, se tocou `app/`, `middleware.ts`, `next.config.js` ou env:
   npm run test:rotas-montam  +  next start  +  UMA requisição a /api/…
   ⚠️ Arquivo estático responde 200 com o roteador morto. Já custou 1h40.
🔴 E `python -m pytest tests/test_todos_os_guardas_script_rodam.py -q`
   (📊 138 passed, 14 xfailed — se mudar, você mexeu em guarda)
```

### Toda subagente reporta o que vir FORA do próprio escopo

📊 Na escrita desta SPEC, essa frase rendeu **quatro pendências e um achado grande**. Custa uma linha no prompt.

## 4. A ORDEM DO TRABALHO

```
FASE 0    o travamento vira linha de banco       ← 🔴 ANTES DE TUDO
FASE 1    a segurança (o mascarador)             ← antes de tocar as tabelas
BLOCO A   o estado diz a verdade
BLOCO B   o humano é chamado de verdade (3 cadeias)
BLOCO C   o segurado ouve a verdade
BLOCO D   a retomada cobre as 16 famílias
BLOCO E   a tela que destrava
BLOCO F   os dois vigias se encontram
BLOCO G   a prova
```

⚠️ **Um worktree por builder** quando dois tocarem `dispatch_router.py` — 📊 os blocos **A, B, C, D e F** tocam. **A integração é SERIAL, e a regressão roda depois de CADA merge.**

## 5. 🔴 AS TRÊS ARMADILHAS QUE JÁ DERRUBARAM ESTA SPEC NA ESCRITA

Elas estão no documento, mas repito porque custaram três rodadas de juiz:

1. **`FASES_ENCERRADAS`** — ⛔ **NÃO tire `needs_human` da tupla.** Ela tem três consumidores e um deles (`dispatch_router.py:528`) **já está certo**. O defeito é o `:757`.
2. **`output_summary`** — ⛔ **é o PAYLOAD DE RESTAURAÇÃO.** Mascarar ali faz um acionamento restaurado responder `###.###.###-##` à seguradora.
3. **`_support_alert`** — ⛔ mexa na chamada **`:311`**, nunca na definição `:189`. Ela tem **cinco** chamadores, e quatro não são handoff.

## 6. O RELATÓRIO

`docs/canon/reports/SPEC-EXECUTION-REPORT-TEMPLATE.md`, **completo**.

🔴 **A §0.1 é preenchida ANTES de montar time**, não no fim: as duas contas com os quatro números · a referência por dimensão com o estado · as voltas do painel · e os blockers que você rebaixou a pendência, com o texto do juiz ao lado.

⚠️ **Todo número sai com a consulta que o produziu.** 📊 medido · 💭 ilustrativo. Número sem marca, em documento novo, é defeito de revisão (`CLAUDE.md` §12.1).

🔴 **E a regra de drenagem:** as pendências que esta SPEC tocar saem com **FECHADA / CONTINUA / MORREU**. As que ela toca: **P-180, P-181, P-182, P-93** — e a **P-183**, que já está parcialmente fechada e cujos **14 guardas em quarentena** incluem o guarda central desta SPEC.

## 7. QUANDO PARAR E PERGUNTAR

Só por estas oito (`CLAUDE.md` §10): risco de perda de dados · decisão comercial · conflito canônico · P0/P1 de segurança ou cross-tenant · ação física do Founder · mudança material de escopo · custo extraordinário · falta de acesso.

**Fora disso: complete o bloco, execute o VERIFY, e avance.** ⛔ Não peça aprovação entre blocos.

---

## ⚠️ E a coisa mais importante deste prompt

> **Esta SPEC foi escrita sob o protocolo e reprovada três vezes.** Na volta 3, um juiz que nunca tinha visto o documento achou **quatro instruções que quebrariam produção** — em texto que dois juízes anteriores tinham lido e aprovado.
>
> 🔴 **Isso não é sinal de que a SPEC é ruim. É sinal de quanto o painel pega.**
>
> **Se você achar que uma instrução da SPEC está errada, você provavelmente tem razão.** Meça, mostre o número, e devolva. A §4 do protocolo diz, literal: *"o executor REPRODUZ antes de aplicar — e devolve com o número se não bater."*
