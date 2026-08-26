# PROMPT DE EXECUÇÃO — 087 → 090 → 086

> **Cole no MESMO chat que executou a 085, a 092 e a 093.** Ele não precisa de
> aquecimento novo: conhece o produto e acabou de trabalhar nele.
> 26/08/2026 · commit base `bcb6ad0`

---

Você acabou de executar a SPEC-093. **Agora são três, em sequência**, e a ordem
não é preferência: ela vem de medição.

## ⛔ AS TRAVAS — as mesmas, e continuam valendo em toda a sequência

```
⛔ NENHUMA MENSAGEM SAI. Para segurado OU seguradora, por nenhum canal.
⛔ NENHUMA ENTRADA EM PORTAL DE SEGURADORA.
⛔ É PROIBIDO LIGAR AGENTE DE ATENDIMENTO. Os quatro estão `is_active=false`.
⛔ NÃO tocar em variável de ambiente de produção.
⛔ NUNCA imprimir CPF, telefone, apólice, placa ou nome de pessoa.
⛔ NUNCA `git add -A` — arquivo por arquivo (P-247).
⛔ Banco: SELECT livre; escrita só pelas migrations de cada SPEC.
```

## 🔴 PREFLIGHT

```bash
git rev-parse --show-toplevel            # AutoBrokers-FIX
git rev-list --count HEAD..origin/main   # 🔴 TEM DE SER 0
git status --short                       # limpo
```

⚠️ **A branch da 093 pode ainda não estar na `main`.** Se `HEAD..origin/main` for
0 mas a 093 não estiver mesclada, **pare e pergunte** — a 087 lê código que a
093 escreveu.

---

# A SEQUÊNCIA, e por que esta ordem

```
1º  SPEC-087  ~5h   a tela que o corredor não conhece
2º  SPEC-090  ~4h   o atendimento de ontem vira conserto de hoje
3º  SPEC-086  ~3h   o atendimento termina e o produto sabe
4º  SPEC-089  ~6h   a régua não sobe quando deixa de medir
```

🔴 **A 087 vem primeiro porque 📊 35,6% das telas que a seguradora manda hoje o
corredor não conhece** — e o piloto começa em dias. Sem o BLOCO A dela, duas
semanas de atendimento real não deixam registro de onde quebrou.

🔴 **A 090 vem em segundo por causa do BLOCO C:** é a única porta para a
anotação da Regina e da Saionara entrar no produto. **Sem ela, o que as duas
observarem no primeiro dia se perde.**

⚠️ **A 086 melhora muito e não bloqueia nada.** Se o Founder mandar ligar o
atendimento antes dela, ligue — e execute a 086 com o piloto rodando.

🔴 **A 089 vem por último, e por um motivo:** ela mede rotas, e o BLOCO C dela
lê o travamento que o piloto vai produzir. **Rodá-la antes é calibrar uma régua
sobre um banco vazio** — 📊 hoje há 2 `needs_human` no banco inteiro.

⛔ **E ela EXIGE árvore exclusiva:** a régua muta `corridor_playbooks.py` para
medir. É a P-261, e ela foi violada ontem por quem escreveu isto.
⚠️ No Windows, `PYTHONIOENCODING=utf-8` ou a CLI quebra (`medir_rota.py:488`).
📊 E medir UMA rota custa 4m14 — as 73 não cabem num laço ingênuo.

---

# 🔴 A LICENÇA DE AUTONOMIA

**Não pare para perguntar.** Se algo travar mais de **30 minutos**, ou se você
achar contradição na SPEC:

```
1. escolha o caminho MAIS CONSERVADOR
2. anote numa CAIXA DO FOUNDER no fim do relatório
3. e SIGA
```

O Founder lê tudo no fim. ⛔ **Parar no meio custa mais que escolher errado e
registrar.**

## As únicas coisas que param você de verdade

```
🔴 risco de perda de dado
🔴 qualquer coisa que possa mandar mensagem para segurado ou seguradora
🔴 P0 de segurança ou vazamento entre corretoras
🧑 ação física do Founder (variável de produção, deploy, papel de pessoa)
```

---

# O QUE CADA SPEC EXIGE DE VOCÊ

## Em todas as três

```
🔴 cada BLOCO 0 REFAZ as medições da SPEC antes de escrever código.
   Os números dela são de 26/08. Se o seu medir diferente, o SEU vence —
   meça, mostre, e devolva. Você já derrubou cinco afirmações minhas na 093.

🔴 toda migration lista os valores do CHECK no APPLY, e o teste TENTA gravar
   um valor inválido exigindo que o banco RECUSE.
   ⚠️ Na 093 a SPEC pediu `destravado_por_humano`, o CHECK não tinha, e você
   descobriu no meio da execução. Não repita.

🔴 toda tabela nova: `company_id` + RLS + FILTRO NO CÓDIGO + teste com DOIS
   tenants. O backend usa service role — RLS sozinha não protege nada.

🔴 as mutações obrigatórias de cada bloco. Restaure por CÓPIA, nunca por
   `git checkout` (P-231).

🔴 o relatório final traz QUANTAS VEZES a bateria rodou.
   📊 Na 093 foram 9 inteiras e 106 parciais, somando 2h — 50% do relógio.
   A query está no template.
```

## 🔴 E uma coisa específica da 087, que é a mais perigosa

O **BLOCO B** conserta a chave que hoje mata o Alfaiate. 📊 Com ela consertada,
`apply_auto_overlays` **volta a poder escrever no corredor** — e o piloto começa
na semana que vem.

```
⛔ O auto-apply NASCE DESLIGADO, por variável, padrão DESLIGADO.
🔴 E o gate ④ exige a LINHA DE CONTROLE: ligue a variável num teste e prove
   que o overlay É escrito. Sem ela, "0 overlays" passa por vacuidade e
   ninguém sabe se o caminho funciona.
```

---

# COMO REPORTAR

Um relatório por SPEC, em `docs/canon/reports/`, com o template do canon. E no
fim de cada um:

```
🧑 CAIXA DO FOUNDER    o que você decidiu sozinho e ele precisa saber
📊 A BATERIA           quantas rodadas, quanto tempo, que fração do relógio
🔴 O QUE FICOU ABERTO  com o que destrava cada coisa
```

⚠️ **E separe FATO de INFERÊNCIA.** 📊 medido · 💭 inferido. **Sem marca não
conta** — nem vindo de mim.

---

# 🔴 O que eu mais quero que você leve

> **Nas três últimas SPECs, quem tem o contexto inteiro deste projeto escreveu
> afirmações erradas — e você achou cinco delas só na 093.**
>
> **Quando a SPEC disser algo que você mediu diferente, a SPEC está errada até
> prova em contrário.**

E o corolário, que custou um dia: **conserto cria defeito.** Na 093, o painel
achou 22 defeitos e **todos os seis blockers foram criados pelos seus próprios
consertos**. Depois de consertar, olhe de novo — com olhos frescos, não com os
olhos de quem consertou.

---

## Comece pela 087

```
docs/canon/specs/SPEC-087-a-tela-que-o-corredor-nao-conhece.md
ordem:  C → A → B → D
```

🔴 **C vem primeiro e não é preferência:** o BLOCO A escreve texto de tela numa
tabela nova. Escrever primeiro e mascarar depois é criar o vazamento e tapá-lo.
