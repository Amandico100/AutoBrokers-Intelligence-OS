# PROMPT — EXTRA-001.5.1 · para o FABLE 5.1 · REVISAR, VALIDAR e então EXECUTAR

> Cole este texto inteiro num chat **NOVO** do Claude Code, modelo **Fable 5.1**, aberto na árvore
> `AutoBrokers-FIX`. Escrito em 18/09/2026 pelo gerente Opus 5 que fechou a EXTRA-001.5 e depois investigou
> por que ela não funciona em produção. **Nada aqui é para executar antes da revisão.**

---

## 1. O que você vai fazer, nesta ordem

```
PASSO 1 · REVISAR a proposta. Você é o revisor, não o executor ainda. Mede, discorda, emenda.
PASSO 2 · APRESENTAR ao Founder o que mudou na proposta e a sua nota 0–100 a ela.
PASSO 3 · EXECUTAR, sob o PROTOCOLO AAA v12.2, modo GERENTE, só depois do "vai" dele.
```

🔴 **Não pule o passo 1.** A SPEC anterior (EXTRA-001.5) passou por juiz Fable, lente do dado e confirmação, com
nota 86, e entregou um produto que **está desligado em produção**. A revisão existe para achar o que essa
sequência inteira não achou.

---

## 2. A leitura mínima — isto, e nada mais

```
1. CLAUDE.md                                                    inteiro (é curto)
2. docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md                      inteiro, UMA vez: é o rito
3. docs/canon/specs-propostas/SPEC-EXTRA-001.5.1-a-base-de-planos-chega-ao-cliente.md   A PROPOSTA a revisar
4. docs/canon/reports/SPEC-EXTRA-001.5-EXECUTION-REPORT.md       §0.0 (card), §4 (juiz), §5 (conserto) — o que
                                                                 já foi julgado, para não rejulgar
5. docs/canon/reports/SPEC-EXTRA-001.5-INVENTARIO-DA-FILA.md     as 81 linhas, para saber o tamanho do dado
6. docs/canon/PROTOCOLO-DE-DESTILACAO-DAS-SEGURADORAS.md         o que é trabalho do Founder, e NÃO seu
7. docs/canon/FOUNDER-DECISIONS.md                               só as linhas D-PILOTO-* e D-PROTO-* e D-E0015-*
```

⛔ Não leia a proposta da 001.5 inteira (70 KB). O que dela importa está no relatório e nesta proposta.

---

## 3. PASSO 1 — a revisão, e o que ela tem de conferir

A proposta afirma doze defeitos com medição. **Reproduza pelo menos estes cinco**, porque são os que decidem o
desenho. Se o seu número for diferente, o seu vence e a proposta muda.

1. 🔴 **A cegueira.** Copie SÓ `backend/` para uma pasta temporária (sem `docs/`) e chame
   `assistance_plans_base.servico_canonico("tem carro reserva?")`. Ela levanta `VocabularioNaoEncontrado`?
   E o `backend/Dockerfile` copia mesmo só `backend/`?
2. **Produção.** Com a chave interna que o Founder tem (`ADMIN_API_KEY`, cabeçalho `X-Internal-Key`), chame
   `GET /api/assistance-plans/cobertura` e `GET /api/assistance-plans/fila?limite=3` na API implantada.
   📊 Em 18/09 deram 200 e **500**. Continua assim?
3. **O silêncio do composer.** Leia `policy_answer_composer.py:572-578`. O `except Exception` captura a falta do
   vocabulário e segue o caminho antigo? Então a Skill está desligada e ninguém vê. Confirme ou refute.
4. **O front.** `app/api/dashboard/knowledge/planos/route.ts:42` não testa `r.ok`? `KnowledgeClient.tsx:108`
   não testa `fila.ok`? `FilaDeCuradoria.tsx:88` escreve "Nada esperando revisão" para lista vazia?
5. **O dado.** `select curadoria, count(*)` nas duas tabelas da base. 📊 Em 18/09: 33 planos e 73 serviços
   `proposto`, 5 e 8 `rascunho`, **zero** publicado. E `TETO_DA_FILA = 60` contra 81 linhas.

**Depois, julgue a proposta como proposta.** Procure:
- unidade que não dá para provar com um comando;
- gate que não fica vermelho com uma mutação;
- ordem errada de fatia (a fatia A tem de vir primeiro: sem ela nada mais existe);
- coisa que a proposta manda fazer e que **já existe** no código (motor paralelo, `CLAUDE.md` §5);
- coisa que a proposta deixou de fora e que o Founder pediu nesta conversa;
- escopo que inchou: se couber menos e entregar o mesmo, corte e escreva por quê.

🔴 **Duas coisas que o Founder pediu explicitamente e que você deve conferir se a proposta cobre bem:**
- o conhecimento **da corretora** nunca vaza para outra, e o **global** chega a todas sem trabalho nenhum delas;
- o que o agente não souber vira **tarefa no portal admin**, para virar conhecimento depois.

---

## 4. PASSO 2 — o que apresentar ao Founder

Máximo 25 linhas, em português de gente:

```
O QUE REPRODUZI ......... os 5 números, com o comando e o resultado
O QUE MUDEI NA PROPOSTA . cada emenda em uma linha, com o porquê medido
O QUE TIREI ............. e por quê
O QUE FALTAVA ........... o que ninguém tinha visto
NOTA DA PROPOSTA ........ 0–100, com o critério em uma linha
A MARCHA ................ confirma CRÍTICO/3 fatias, ou propõe outra, com nota
```

Então **pare e espere o "vai" dele**. Não comece a construir.

---

## 5. PASSO 3 — a execução, sob AAA FAST modo GERENTE

Você é o **GERENTE**: não escreve código de produto. Monta o pacote, delega cada fatia a **um builder subagente
Opus 5 xhigh fresco**, roda as provas, chama **um juiz Fable fresco**, manda o conserto ao mesmo builder e
empurra. Tudo num chat só, do card ao push.

```
① CARD + BLOCO 0     ≤ 15 min. Relatório pelo template FAST. As premissas que mudariam o desenho.
② BUILD por fatia    fatia 1 = A (a cegueira) · fatia 2 = B (fila e lote) · fatia 3 = C + D + E
③ PROVA MECÂNICA     compile · guardas · mutação dos novos · rotas-montam + next start (a fatia 3 toca app/)
④ JUIZ FRESCO        Fable, read-only, com a lista de ataques do §6 do protocolo
⑤ CONSERTO ÚNICO     ao mesmo builder, contexto quente
⑥ ENTREGA            suíte uma vez, relatório ≤ 15 KB, push com a saída colada, telemetria
```

### 🔴 A regra nova, que esta SPEC existe para instituir

> **Todo gate que prove comportamento de produção roda numa árvore que reproduz o contêiner.**

Copie só `backend/` para uma pasta temporária e rode ali. Foi a ausência disso que deixou a 001.5 passar por
juiz, lente e confirmação com o produto desligado. **Ponha isso no pacote do juiz**, com estas palavras:
*"prove na cópia sem `docs/`, não na árvore"*.

### As travas de sempre

```
⛔ Nada envia. Nenhum agente é ligado. Nenhum portal. Banco: SELECT livre; escrita só por escritor existente
   ou migration com APPLY/VERIFY/ROLLBACK escritos antes.
⛔ NUNCA `git add -A`. Commit arquivo por arquivo. NUNCA imprimir PII nem valor de variável de ambiente.
⛔ Motor paralelo proibido (CLAUDE.md §5): a porta do grupo, o registro de invocação, o publicador global e a
   tabela `capability_gaps` JÁ EXISTEM. Pendure neles.
⛔ 🔴 NENHUMA linha da base vai a `publicado` em produção sem o Founder mandar. O script de lote nasce em
   `--dry-run`; quem aperta o gatilho é ele.
```

### O que o Founder já decidiu, e não se reabre

- A resposta ao segurado **não leva citação de documento nem página**; a do corretor leva.
- Quando a base diz que não cobre, a resposta ao segurado **oferece o caminho da equipe na mesma mensagem**.
- O conhecimento de planos é **global**; o da corretora é **dela**; a tela de curadoria é de administrador.
- A destilação das seguradoras que faltam é trabalho **dele**, não seu.

---

## 6. Onde está tudo

```
a proposta        docs/canon/specs-propostas/SPEC-EXTRA-001.5.1-a-base-de-planos-chega-ao-cliente.md
o relatório 001.5 docs/canon/reports/SPEC-EXTRA-001.5-EXECUTION-REPORT.md
o inventário      docs/canon/reports/SPEC-EXTRA-001.5-INVENTARIO-DA-FILA.md
a destilação      docs/canon/PROTOCOLO-DE-DESTILACAO-DAS-SEGURADORAS.md
o canário 001.5   docs/canon/reports/SPEC-EXTRA-001.5-CANARIO-PASSO-A-PASSO.md
o protocolo       docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md
o template        docs/canon/reports/SPEC-EXECUTION-REPORT-TEMPLATE-FAST.md
```

**Preflight, sempre:** `git fetch origin` · `git rev-list --count HEAD..origin/main` tem de ser 0 ·
`git status --short` limpo · registre o HEAD. Branch: `feat/extra-001-5-1-a-base-chega-ao-cliente`.
