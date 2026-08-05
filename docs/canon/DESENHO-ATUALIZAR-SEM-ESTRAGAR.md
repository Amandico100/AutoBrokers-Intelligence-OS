# Atualizar sem estragar — o desenho, para ser criticado antes de executar

> **Status:** PROPOSTA. Nada aqui foi executado. 05/08/2026.
> **Origem:** o Founder pediu que o sistema se atualize sozinho — e disse, com
> todas as letras, qual é o medo: *"não podemos atualizar e estragar durante a
> atualização o que tínhamos bem feito."*

---

## 1. O medo, traduzido em quatro modos de falha

Não é um receio vago. São quatro maneiras concretas de piorar o sistema, e cada
uma precisa de uma trava própria.

### F1 · A atualização apaga a verdade que ainda vale

A Porto muda a regra de vidros em 03/2026. Um segurado com apólice de 02/2024
pergunta. **A regra dele é a antiga** — Circular SUSEP 667/2022, art. 2º §3º: a
alteração só vale para contratações a partir do registro.

Se a carta nova substitui a velha, o agente responde a regra de 2026 para o
contrato de 2024, com toda a confiança do mundo. E a resposta certa foi
destruída.

📊 Isto **já está no código**: `insurance_corpus.py:232` apaga o documento antes
de reingerir. O comentário lá escolheu conscientemente o lado errado do dilema.

### F2 · O agente estreito

Um agente instruído a *"atualizar a regra de vidros da Porto"* reescreve a carta
de vidros e não percebe que existem outras 14 cartas mencionando a regra antiga
— destiladas de atendimento real. O cérebro fica **internamente contraditório**,
e a contradição é invisível porque cada carta, isolada, parece certa.

### F3 · A promoção que degrada

📊 Achado de 05/08/2026, e ele derruba a minha própria recomendação anterior:

```
render_map_for_llm(map_obj, max_nodes=30)   →  list(nodes.items())[:30]

allianz    1.323 nós  →  o modelo vê 30  (2,3%), por ordem de inserção
porto        840 nós  →  3,6%
tokio         60 nós  →  50%
```

E o prompt rotula isso como **"MAPA COMPLETO DA URA DESTA SEGURADORA"**.

Hoje `get_active_map` devolve `None` para todas, então nada disso acontece.
**Promover os 10 mapas injetaria uma fatia arbitrária de 2% no prompt do
acionamento ao vivo, anunciada como completa.** Pior que não ter mapa: o modelo
confia no que o prompt afirma.

### F4 · A regressão silenciosa

Mexemos na busca, no filtro, na precedência — e as respostas pioram sem que
ninguém meça. É o modo de falha que não tem sintoma até um segurado reclamar.

---

## 2. O princípio que resolve os quatro

> ### Nada é substituído. Tudo é datado e superposto.
> ### A pergunta nunca é "qual é a regra?" — é **"qual regra valia no dia D?"**

Isto não é preferência de engenharia. É a forma como o seguro funciona por lei,
e adotar qualquer outra é construir um sistema que discorda do contrato.

Três consequências diretas:

1. **Append-only.** Uma versão nova nunca apaga a anterior. Ela **fecha** a
   janela da anterior (`vigencia_ate = véspera`) e abre a sua.
2. **Toda resposta sobre regra carrega a data da versão citada.** Sem data, a
   resposta é uma afirmação sem contrato — e o agente tem de dizer isso.
3. **Quem não sabe a data não afirma.** Existe uma resposta legítima entre "é
   coberto" e "não é coberto": *"a versão que tenho é de tal data; se a apólice
   é anterior, a regra pode ser outra — me confirma a emissão?"*

---

## 3. As travas, uma por modo de falha

### T1 · Contra o apagamento (F1)

```
proibido    DELETE / UPDATE destrutivo em carta, condição geral ou mapa
obrigatório  a versão nova FECHA a janela da anterior e abre a sua
             toda peça de conhecimento tem `vigencia_de` e `vigencia_ate`
             `vigencia_ate` NULL = corrente
consulta    "o que valia em D" é `vigencia_de <= D <= coalesce(vigencia_ate, ∞)`
```

**A trava que não depende de ninguém lembrar:** uma restrição de exclusão no
banco (`EXCLUDE USING gist`) impede que duas versões do mesmo assunto valham no
mesmo dia. Se o código tentar, o banco recusa.

### T2 · Contra o agente estreito (F2)

A unidade de atualização **não é o documento. É o assunto.**

```
errado   "atualize a carta X"
certo    "a regra de vidros da Porto mudou em D.
          ache TUDO que fala disso — cartas, condição geral, playbook —
          e date cada peça. O que era verdade continua verdade ATÉ D."
```

**A trava:** o agente que atualiza é obrigado a devolver a **lista completa do
que tocou** e a **lista do que achou e decidiu não tocar, com o motivo**. Uma
atualização que devolve lista vazia de "não toquei" é rejeitada — porque em
10.818 cartas é impossível que nada mais fale do assunto.

### T3 · Contra a promoção que degrada (F3)

**Não promover nada sem portão medido.** Para o Atlas, o portão tem três provas:

```
1. o mapa novo cobre pelo menos tanto quanto o anterior     (coverage não cai)
2. as rotas que o acionamento REALMENTE usou continuam lá   (regressão de rota)
3. o que entra no prompt é RELEVANTE, não os 30 primeiros   ← conserto obrigatório
```

**A prova 3 vem antes de qualquer promoção.** Enquanto `render_map_for_llm`
cortar por ordem de inserção, promover é injetar ruído rotulado como verdade.

E a promoção é **uma seguradora por vez**, começando pela de maior cobertura,
com medição entre uma e outra. Dez de uma vez é dez riscos simultâneos e
nenhuma forma de saber qual deu errado.

### T4 · Contra a regressão silenciosa (F4)

**Medida "antes" obrigatória, e linha de controle obrigatória.**

```
antes     roda o conjunto de perguntas com o sistema como está → nota base
depois    roda o mesmo conjunto → nota tem de ser >= base
controle  roda com a mudança DESLIGADA por flag, no mesmo commit
          tem de reproduzir a base. Se não reproduzir, a comparação não vale.
```

CLAUDE.md §9.2: **é a linha de controle que dá direito à conclusão.**

---

## 4. Quem atualiza o quê — a Central, separada dos Auxiliares

O Founder foi explícito: **Auxiliar não é o assunto agora.** Auxiliar é trabalho
que a corretora contrata (o "Primeira Mão" avisa o corretor sobre mudanças).
O que está em questão é a **manutenção do cérebro da plataforma**.

| Agente da Central | O que mantém | Gatilho | Estado |
|---|---|---|---|
| **Observador** | o que a URA falou | webhook | 🟢 vivo |
| **Tecelão** | o mapa da URA | 15 min, se chegou conversa | 🟢 vivo |
| **Sentinela de Rotas** | detecta que a URA mudou | 15 min | 🔴 cego: 0 mapas `active` |
| **Espelho** | conversas da equipe | contínuo | 🟢 vivo |
| **Destilador** | conversa → carta | diário | 🟡 teto 0 (por decisão) |
| **Curador** | junta quase-cópia, publica | junto ao Destilador | 🟢 vivo |
| **Corpus normativo** | condição geral e circular | 45 dias | 🔴 23 presos em `fetching` |
| **Vigia da Atualidade** | *avisa que algo envelheceu* | horário | ⚫ **não existe** |

**A orquestração que falta** é justamente a última linha: ninguém vigia os
vigias. Cada peça sabe fazer a sua parte e nenhuma sabe dizer *"faz oito dias
que eu não produzo nada."*

---

## 5. O que executar, na ordem, com o que cada passo NÃO faz

```
A. varrer órfão preso em `fetching`            🟢 risco zero — só reencontra trabalho
   NÃO muda resposta nenhuma. Destrava 23 documentos invisíveis.

B. o Vigia da Atualidade                        🟢 risco zero — só observa
   8 consultas, custo zero de LLM.

   ⚠️ CORREÇÃO de mim mesmo, 05/08: o desenho dizia "escreve em
   `intelligence_signals`". 📊 Medido: essa tabela é LIDA por `rule_engine.py`,
   `demand_cluster_service.py` e `garimpo_v3.py` — escrever lá aciona coisa a
   jusante, e ela é inteligência DA CORRETORA, não da plataforma.

   Os vigias irmãos (`vigia_do_portal`, `regression_sentinel`) não escrevem
   lá: usam `logger` + `heartbeat.beat()` + alerta ao suporte. O Vigia da
   Atualidade segue o mesmo padrão. É vigilância de plataforma, e plataforma
   não fala pela tabela da corretora.

C. marca d'água não avança em rodada degradada  🟢 risco baixo
   Efeito: retece de novo na próxima passada. Custo: uma tecelagem a mais.

D. resumo × texto inteiro no monitor            🟢 risco baixo, e é pré-requisito
   Sem isto o Radar acusa "mudou tudo" em toda verificação.

E. render_map_for_llm por RELEVÂNCIA            🟠 muda o prompt — mede antes
   Pré-requisito de F. Sem ele, promover é injetar ruído.

F. promover mapa para `active`                  🔴 UMA POR VEZ, com portão
   Só depois de E, e só com a medida antes/depois.

G. vigência nas cartas e condições gerais       🔴 o desenho grande
   É o que resolve F1 de verdade. Precisa de migration e de teste de regressão.
```

**A → D podem ser feitos hoje, com segurança.**
**E → G exigem medida "antes" e vão em passos separados.**

---

## 6. O que eu quero que o crítico derrube

1. O princípio da §2 está certo, ou existe caso em que substituir é melhor que
   datar?
2. A T2 (lista do que não foi tocado) é executável, ou é burocracia que o agente
   vai preencher com ruído?
3. A ordem da §5 está certa? Algum item "risco zero" tem risco escondido?
4. O portão da T3 basta para promover um mapa, ou falta prova?
5. O que eu não vi?
