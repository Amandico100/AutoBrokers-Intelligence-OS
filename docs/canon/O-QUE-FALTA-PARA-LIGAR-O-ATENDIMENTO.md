# O QUE FALTA PARA LIGAR O ATENDIMENTO

> **Uma folha só.** O que você faz com as mãos, o que o executor faz em código,
> e o que dá para começar sem.
>
> 26/08/2026 · commit base `5b14e57` · 📊 tudo medido hoje

---

# 🧑 PARTE 1 — O QUE SÓ VOCÊ PODE FAZER

⚠️ **Nenhum item aqui é código.** São seis, e o executor **não pode** fazer
nenhum: são variável de produção, papel de pessoa e botão de deploy.

### 1 · Empurrar a SPEC-093 para a `main`

> ## ✅ MINHA RECOMENDAÇÃO: EMPURRE.
>
> Uma auditoria independente disse **NÃO** por três motivos. 📊 **O mais forte
> deles eu consertei; os outros dois não seguram:**
>
> | o motivo | hoje |
> |---|---|
> | 🔴 a regressão da Fila | ✅ **consertada**, com guarda provado nos dois sentidos |
> | o `G.3` não veio | ⚠️ verdade — mas 📊 só **2 de 14** corredores estão ativados. Ninguém usa pausar ainda. **P-260** |
> | a bateria não fecha verde | 📊 remedi com **árvore exclusiva**: `2 failed · 672 passed`. **Os dois são a P-246**, e a árvore termina limpa |
>
> 🔴 **E a contaminação era minha:** o auditor viu 3 vermelhos porque eu
> commitava SPECs enquanto ele media. Com a árvore só dele, são 2 — e o
> terceiro (a política de autorização) **passa**.
>
> ⚠️ **O risco de empurrar é baixo:** nada da 093 consegue mandar mensagem —
> os agentes estão desligados, e há quatro freios em série. **E o risco de NÃO
> empurrar é real:** o schema já está à frente do código.



```bash
cd "c:/Users/amand/Projetos/AUTOBROKERS RESULTA/AutoBrokers-FIX"
git push origin feat/spec093-o-atendimento-real-liga-e-funciona:main
```

📊 São **11 commits**, 4.984 linhas (2.868 delas de teste). ⚠️ O EasyPanel
constrói a `main` — **este comando é o deploy.**

⚠️ **E a migration dela JÁ está no banco** (`20260825233516`, aplicada ontem).
Hoje o schema está à frente do código: existe uma tabela `saudacoes_enviadas`
que nenhum código usa. **Isso é a ordem certa** (`expand-first`), mas quer dizer
que *"não foi deployado"* é meia verdade.

### 2 · Dar o papel `attendant` à Regina e à Saionara

```
📊 pessoas com papel `attendant` hoje ....  0
```

A SPEC-093 **criou o papel**; ninguém o tem. ⚠️ Sem isso elas recebem **403** ao
apertar o botão de ligar o agente.

### 3 · Esvaziar a `ATTENDANT_INBOUND_ALLOWLIST` no EasyPanel

📊 Hoje ela tem **um número**, e todo telefone fora dela é **descartado antes de
existir** para o produto. ✅ Vazio já significa "todos" — não precisa de código.

⛔ **Mas veja o item 6 antes de esvaziar.**

### 4 · Decidir o `DISPATCH_FINALIZE_MODE`

```
live   →  o corredor ABRE o chamado. O guincho vem.
test   →  percorre tudo e CANCELA no fim. O guincho NÃO vem.
```

📊 Hoje está em `test`. Você disse que elas **cancelam depois** — isso é `live`.

⚠️ **E dá para graduar:** `DISPATCH_FINALIZE_LIVE_PLAYBOOKS=ref1,ref2` abre só
nos corredores que você confia, mantendo o resto em ensaio.

### 5 · Desarmar o `ACIONAMENTO_FREIO_DE_EMERGENCIA`

📊 Ele está **armado**, e hoje é **a única coisa** que impede o corredor de falar
com a seguradora. ⚠️ Ao desarmá-lo, `INSURER_DISPATCH_LIVE` volta a valer — e
📊 a **P-168** registra `true` no ambiente desde 15/08.

> 🔴 **Faça 4 e 5 juntos, e nessa ordem.** Desarmar o freio com o `finalize` em
> `test` é o "meio aberto": mensagem real chega à seguradora, o fluxo anda até o
> fim e é cancelado. **O segurado ouve "estou acionando" e ninguém vem.**

### 6 · 🔴 O item que quase passou despercebido

📊 [route_sentinel.py:363](../../backend/app/services/atlas/route_sentinel.py#L363) usa a
**allowlist como destino do alerta de deriva de rota**:

```python
os.getenv("ATTENDANT_INBOUND_ALLOWLIST", "").split(",")[0]
```

⚠️ **Esvaziá-la (item 3) apaga em silêncio o alarme** que avisa quando um
corredor sai do lugar. 📊 Há **14 alertas de deriva registrados**, e eles podem
já não estar chegando a ninguém.

**O conserto é uma variável nova** (`ATLAS_ALERTA_DESTINO`) — está no BLOCO B da
SPEC-093, **já executado**. ✅ **Confirme que ele está lá depois do deploy.**

---

# ✅ PARTE 2 — O QUE JÁ ESTÁ PRONTO

```
📊 integrações pareadas ..................  3      o pareamento FUNCIONA
📊 corretoras com agente attendance ......  4
📊 agentes attendance ligados ............  0      ⛔ e continuam, até você ligar
📊 a saudação de religamento .............  pronta (SPEC-093 BLOCO D)
📊 o travamento vira evidência ...........  pronto (SPEC-093 BLOCO C)
📊 o papel `attendant` ...................  existe (SPEC-093 BLOCO A)
📊 um clique liga os corredores ..........  pronto (SPEC-093 BLOCO G)
```

⚠️ **Tudo isso está numa branch não empurrada.** O item 1 é o que os liga.

---

# 🔴 PARTE 3 — O QUE FALTA EM CÓDIGO, e o que cada coisa custa

| SPEC | o que resolve | 💭 | **precisa antes de ligar?** |
|---|---|:---:|---|
| **087** | 📊 **35,6% das telas que a seguradora manda, o corredor não conhece** | ~5h | ⚠️ **o BLOCO A sim** — sem ele o piloto não ensina nada |
| **090** | a anotação da Regina e da Saionara entra no produto | ~4h | ⚠️ **o BLOCO C sim** — senão as notas se perdem |
| **086** | o produto sabe quando um atendimento terminou | ~3h | ❌ não bloqueia |
| **089** | a régua que decide quais rotas estão prontas | — | ❌ não bloqueia |

## 🔴 A conta que importa

> **Dois blocos — 087 A e 090 C — decidem se duas semanas de atendimento real
> viram conserto ou viram nada.**
>
> Sem eles: o robô atende, trava, alguém clica, e **na sexta-feira ninguém sabe
> onde ele travou nem o que a Regina viu.**

💭 **Os dois juntos: ~4 horas.**

---

# ⚠️ PARTE 4 — O QUE VAI DOER, e é melhor saber antes

```
📊 tokio ......... 13 de 13 telas cegas. CEM POR CENTO.
                   e com deriva de URA registrada em 25/08
📊 corredores ativados hoje ....  2 de 14
📊 o robô conversou com segurado  61 vezes na história do produto
📊 acionamentos completos ......   3
```

🔴 **O piloto não é "ver se funciona". É a primeira vez que este produto atende
de verdade em volume.** Espere que quebre — e é exatamente por isso que os dois
blocos da Parte 3 valem mais que tudo o resto.

---

# 📋 A ORDEM QUE EU RECOMENDO

```
HOJE      1. push da 093          🧑 você, um comando
          2. papel attendant      🧑 você, no dashboard
          3. confirmar o alerta   🧑 você, depois do deploy

DEPOIS    4. o executor faz 087 BLOCO A + 090 BLOCO C     💭 ~4h

🚦 AÍ     5. as variáveis (3, 4, 5 juntas)   🧑 você
          6. ligar o agente e começar

DURANTE   7. o executor faz o resto da 087, a 090, a 086, a 089
             — com o piloto rodando e produzindo dado de verdade
```

⚠️ **O 4 antes do 6 é a única ordem que eu defendo.** As variáveis podem esperar
quatro horas; **a evidência do primeiro dia não volta.**
