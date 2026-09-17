# FICHA — SPEC-EXTRA-001.5 · O agente sabe o que cada plano cobre

> Lida **no lugar da proposta inteira** (v12.1 §1 · D-PROTO-08). A proposta
> (`specs-propostas/SPEC-EXTRA-001.5-o-agente-sabe-o-que-cada-plano-cobre.md`) abre-se **por unidade**, no §N
> de cada bloco; o RESEARCH-PACK só quando citado (§2 consultas · §4 greps do BLOCO 0). ⚠️ os caminhos e
> linhas dela estão vencidos — valem os desta ficha. 17/09/2026, `origin/main` = `ff2518a`.

## Outcome, em 3 linhas

O corretor pergunta *"ele tem carro reserva? cobre granizo? qual o limite do guincho?"* e recebe **sim · não ·
condicionado · não contratado · não sabemos ainda**, com **documento e página ao lado** e o **nível do plano**
contratado. *"Não sabemos ainda"* é acerto; *"a fonte não retornou"* é falha, e tem outro nome.

## EXECUTION CARD — recalcular no BLOCO 0, não copiar

```text
OUTCOME ....... pergunta de cobertura -> um dos cinco estados, com documento e página, dizendo o NÍVEL
                do plano, para qualquer seguradora que a corretora usa
RISCO ......... 7 = ALCANCE 3 (o SEGURADO lê "você tem carro reserva") + REVERSIBILIDADE 2 (tabela nova
                + CHECK de tabela viva) + FREQUÊNCIA 2 (toda pergunta de cobertura)
SUPERFÍCIE .... 2; vira 3 se aparecer leitor do corpus fora da lista da §3.1
PISO .......... §3.2, num ponto só: a migration que ALARGA o CHECK de `doc_kind` em tabela VIVA e de DDL
                NÃO RASTREADA (§11.2). As tabelas novas são aditivas
NÍVEL ......... PADRÃO — diagnóstico §13.4 ("1 lente + juiz + canário") e D-PROTO-02 (experimento C). A soma
                dá CRÍTICO: a divergência fica ESCRITA e o piso vale em 2 pontos (§11.2 e o texto ao
                segurado, §6.2). Opus 5 `high` · juiz Opus 5 · lente do dado SIM (§8)
UNIDADES ...... 5 · A chave+tabelas · B a Skill · C as três ondas · D a tela · E a medição
                FATIAS: 1 = A (hub, sozinha) · 2 = B+E (o turno da resposta) · 3 = C+D (a curadoria)
COESÃO ........ A é hub (chave + migrations), primeiro e sozinho; B e E tocam o MESMO turno; C e D, a
                MESMA fila de curadoria
PARALELISMO ... nenhum. A escrita é de um só (§4); da fatia 2 em diante, UM builder fresco (§5.2)
TIME .......... executor · juiz fresco · lente do dado (§8) · builder das fatias 2 e 3 (xhigh, em série)
REFERÊNCIA .... INTERNA `backend/tests/test_a_cobertura_tem_lastro_no_acervo.py` (📊 254 linhas): exige
                acervo por trás de afirmação de cobertura — mesmo formato, na LINHA da tabela. EXTERNA as
                3 da §14 (PROV-O · Citations da API Anthropic · ALCE 2023)
GATES ......... GA GB GC GD GE G-MIG G-CANÁRIO + canônicos (compile · suíte por diff · rotas montam)
O ELO ......... "responde genérico PORQUE não há plano estruturado": medir A, medir B (📊 0 linhas de
                plano) e medir que B CHEGA em A — o caminho ATUAL sobre 10 perguntas de carro reserva
FAIXA ......... 💭 fatia ≤ 75 min · juiz+lente+conserto+entrega ≤ 45 min (o 💭 "10–14 h" da §0.4 é do laço
                antigo e não vale). TETOS por fatia: 160 turnos · 250 k
```

## BLOCO 0 — as premissas cuja falsidade **muda o desenho** (§4 · comandos no RP §4)

1. **Fonte arquivada existe** para os 📊 56 documentos dos ramos dos pilotos? `select count(*) filter (where
   storage_ref is not null), count(*) from normative_document_versions` — 📊 `insurance_corpus.py:1612` registra
   **0 de 29**: baixo, o Bloco A **re-arquiva antes** de extrair, e o CHECK `pagina NOT NULL` depende dele.
2. **O elo SUSEP no caminho REAL:** `extrair_susep(build_document_plain_text(pages))` num PDF do acervo. Veio o
   processo → `_BOILERPLATE_RE` **não** era o bloqueio, **não se toca no filtro**, e a linha de controle do M-C2 é
   outra. Não veio → medir com e sem `susep` no filtro.
3. **O caminho vivo da assistência é único?** `rg -n "apply_residential_assistance_policy|InfocapPolicyLookupTool"
   backend/app` — segundo respondente muda a forma do B · 4. **casamento de chave** (M2/M3 do RP §2).
5. **O CHECK real de `doc_kind` vem do catálogo** (`pg_get_constraintdef` + `select doc_kind, count(*) group by 1`):
   📊 classe **SEM_ARQUIVO**, e o manifesto de §11.2 nasce desta saída.
6. **`tool_invocations` guarda argumento cru?** `select tool_args … limit 5` (sem colar PII) + `gateway.py:294`:
   CPF ali é **P1**, e a drenagem vem antes · 7. **`SkillRegistry` em runtime?** (`rg -n "SkillRegistry" backend/app`)
   decide tool × skill release · 8. **o ELO** (10 perguntas reais pelo caminho atual) · 9. **linha de base da suíte**
   (`cd backend && python -m pytest tests -q`), falhas nomeadas uma a uma.

**Já resolvidas:** a 001.1 fechou (`app/providers/policy_data_provider.py`) e **P-PILOTO-20 está FECHADA**.
**GATE B0:** matriz `premissa → observação → comando → decisão`, com as divergências listadas. **MUTAÇÃO B0:**
duas afirmações falsas, refutadas **com comando**, não por leitura.

## A · chave e tabelas — **fatia 1, sozinha** — §5, §11

A base global de planos e serviços nasce com fonte obrigatória **pelo BANCO**, e a chave **pendura na função que
já existe** (CLAUDE.md §5).
- `backend/app/services/corridor_playbooks.py` — `normalize_insurer_key(insurer, para=…)` **:8236**,
  `_INSURER_ALIASES` **:8166**, `_OPERADO_POR` **:8225**. ⚠️ **`para="conhecimento"` é obrigatório**: `"corredor"`
  aplica `_OPERADO_POR` (`{"itau":"porto"}`) e a carta do Itaú sumiria sob Porto.
- `docs/canon/providers/susep/seguradora-coenti.json` · `ramo-cogrupo.json` — as conciliações que faltarem, uma a
  uma, com o critério ao lado (`susep_ses_provider.py:167`); o que não casa sai `UNKNOWN` **listado**.
- `backend/supabase/migrations/` — as duas de §11 (data do arquivo = data da execução). ⚠️ `insurer_catalog.py`
  **só como CONSOLIDAÇÃO declarada** (migrar os 📊 14 chamadores com o `para=` preservado, com guarda); senão é o
  terceiro normalizador. A decisão vai escrita, com nota.

**GATE A:** ① `INSERT` sem `documento_id`, sem `pagina`, com `pagina=0` e `publicado` sem revisor são **recusados
pelo banco**, erro colado; ② `"tokio"` e `"tokio_marine"` dão a mesma chave, e a desconhecida sai `UNKNOWN`
listado; ③ zero coluna `company_id`/`user_id`, PII = 0; ④ duas corretoras → **a mesma** resposta.
**MUTAÇÃO A (5 vermelhas):** (a) remover o CHECK `servico_tem_fonte` — ⚠️ *nullable* **não serve**: o CHECK recusa
e o guarda ficaria verde; (b) `pagina=0`; (c) `publicado` sem revisor; (d) `ADD COLUMN company_id`; (e)
`limite_valor` sem `limite_unidade`.

## B · Skill `cobertura_e_assistencia` — **fatia 2** — §6

Um caminho **único** responde cobertura pela base, nos **cinco estados**, com origem escrita;
`assistance_policy.py` vira **fallback marcado**; a procedência volta do Qdrant **como campo**.
- `app/services/assistance_policy.py` — 📊 141 linhas; `STANDARD_SERVICES` **:28**, gatilho `"resid"` **:54**,
  `locator_hash = None` **:124** · `app/services/policy_answer_composer.py` importa **:24** e chama
  `apply_residential_assistance_policy` **:410** — é **aí** que a base entra (forma nota 90 da §6): um caminho, um
  registro · `graph.py:449-450` (⛔ nada novo ao lado) · `infocap_tool.py` (`:394`, `:461`, `:710`, `:747`).
- `app/agents/nodes.py:348-350` — o guarda dos 3 serviços. **Muda de regra, não morre:** com `assistencia_da_base`
  a resposta não pode OMITIR serviço da base; com o fallback, a regra dos 3 continua.
- `qdrant_service.py` — `_INDICES_DE_PAYLOAD` **:88**, `_filtro_de_seguradora` **:434**, `search_similar` **:639**
  (aditivo: a procedência já está no payload); **o índice de `doc_kind` nasce ANTES de qualquer ingestão nova** ·
  `knowledge_scope.py:342` (busca global, sem `company_id`).

**GATE B:** ① **30 perguntas reais do acervo** (PII removida), **pelo motor**: cada uma devolve um dos cinco
estados, e todo estado ≠ `nao_sabemos_ainda` traz documento e página; ② **controle**: pergunta fora de assistência
não consulta a base; ③ **par de controle**: a mesma pergunta em dois níveis → vereditos opostos, gancho só na
inferior; ④ `doc_kind` filtra mesmo.
**MUTAÇÃO B (5 vermelhas):** (a) `nao_sabemos_ainda` colapsando em `nao_coberto`; (b) origem removida do
contrato; (c) plano inferido só pela seguradora; (d) gancho sem plano superior; (e) guarda de `nodes.py` apagado.

## C · as três ondas — **fatia 3** — §7

As linhas nascem da **fonte arquivada** (o chunk não tem página); o **verificador só reprova**, a **pessoa publica**;
o elo SUSEP roda sobre o texto integral; `content_hash` alterado derruba as linhas para `proposto` sem apagá-las.
`app/services/knowledge/insurance_corpus.py` (`extrair_susep` **:65**, `_guardar_a_fonte` **:1608**, hash igual não
reingere **:1434**) · `knowledge/acervo_arquivo.py` (bytes no MinIO) · `policy_document_evidence_service.py`
(`build_document_plain_text` **:188**, `_BOILERPLATE_RE` **:229**, `is_boilerplate_fragment` **:408**,
`document_text` **:1134**) · `app/api/corpus.py` (a fila do DOCUMENTO existe e **não se toca**).

**GATE C:** ① onda 1 num documento de auto e num de residencial: a página **existe**, o `trecho_hash` **bate**,
nada em `publicado` sem revisor; ② onda 2 numa apólice real: o processo é extraído, **casa**, e a condição é a
**vigente na emissão**; ③ **controle** no caminho usado de verdade (BLOCO 0 passo 2); ④ `manual_de_assistencia`
aceito **depois** da migration e **recusado antes**; ⑤ `content_hash` novo derruba as linhas para `proposto`.
**MUTAÇÃO C (4 vermelhas):** (a) verificador promovendo a `publicado`; (b) página inexistente aceita;
(c) busca pela condição **atual**; (d) `content_hash` novo mantendo as linhas publicadas.

## D · tela mínima (Conhecimento) — **fatia 3** — §8

Cobertura por **seguradora × ramo** (nunca por contagem de linhas) e a **fila de curadoria** com o trecho e a
página ao lado. `app/dashboard/personalizacao/conhecimento/page.tsx` e `KnowledgeClient.tsx` — a tela existe e esta
SPEC **acrescenta**; ⚠️ **não move rotas** (é a 001.9); nada de tabela, coluna ou SQL na tela. Mexeu em `app/`:
`test:rotas-montam` **e** `next start` + 1 requisição (CLAUDE.md §9.1).
**GATE D:** abre com a base vazia (estado vazio honesto), com uma seguradora publicada e com um item na fila;
publicar grava `revisado_por`/`revisado_em`; trocar de corretora **não muda nada**, e a tela diz isso.
**MUTAÇÃO D:** a régua contando **linhas** — o defeito de `tests/test_cobertura_nao_mente_para_cima.py`
(📊 Allianz: painel 63 %, real 37 %).

## E · medição e `origem` no turno — **fatia 2** — §9

Três contagens separadas: **CG na base** ≠ **plano publicado** ≠ seguradora que a corretora **usa**. A origem
grava-se **no registro que já existe** — `app/services/skills/gateway.py:294` e `:323`, via
`app/api/chat.py:1265`. **Nenhum segundo registro** e **nenhum argumento cru**: `{"documento": "presente"}`.
**GATE E:** a consulta devolve os três números separados; um turno do canário aparece em `tool_invocations` com
estado, seguradora, documento e página, e o varredor de PII não acha nada.
**MUTAÇÃO E:** `tool_args` cru → o varredor fica vermelho.
📊 Hoje (13/09, §9): **8 de 61** com CG indexada (**6** com a chave casando) · **0 de 61** com plano estruturado ·
💭 meta da onda 1: 6 de 61, nos 3 ramos dos pilotos.

## Migrations — APPLY/VERIFY/ROLLBACK **antes** (SQL em §11)

**Ler `MIGRATIONS-AUTHORITY.md` inteiro antes do primeiro SQL.** Canônico `backend/supabase/migrations/`.
**São duas, de naturezas diferentes; elas não se juntam.**

**① aditiva.** APPLY as duas tabelas com `IF NOT EXISTS` (CHECKs `servico_tem_fonte`,
`servico_publicado_foi_revisado`, `limite_tem_unidade`) + três índices. VERIFY os CHECKs por
`pg_get_constraintdef`, e `company_id|user_id|owner_user_id` → **0**. ROLLBACK `DROP TABLE` filha primeiro — ⚠️
**apaga linhas curadas**.
**② altera uma TRAVA de tabela viva — é onde o piso CRÍTICO dispara.** Alarga o CHECK de `doc_kind` para
`manual_de_assistencia` numa tabela de 📊 **194 linhas**, DDL não rastreado. **MANIFESTO antes de rodar** (CHECK
atual colado, valores em uso, nenhuma linha perde validade) · **TRANSAÇÃO ÚNICA** (entre DROP e ADD a tabela fica
sem trava, com escritor ativo) · ROLLBACK só com zero linha no valor novo.
**GATE G-MIG:** ① os três escritos antes de rodar; ② APPLY 2× com o mesmo resultado; ③ ROLLBACK exercitado, com a
guarda de contagem; ④ as três inserções adversariais falharam, mensagem colada; ⑤ `MANIFEST.md` com
`normative_documents` **NÃO RASTREADA**; ⑥ **nenhuma outra migration nesta SPEC**.

## Canário (§12) — 8 casos; 5, 7 e 8 dão a conclusão

**Antes:** o **SHA implantado** de cada serviço (não o `/health`) · janela só com TESTE-A/B · **≥ 1** seguradora
publicada e revisada (com a base vazia prova-se só a metade fácil).
🧑 **Founder, chat `core`:** ① carro reserva com plano publicado → estado certo, com documento e página · ② a mesma
pergunta sem plano na base → `nao_sabemos_ainda` · ③ limite do guincho **com unidade** e fonte · ④ nível 1 com nível
2 acima → gancho, nomeando a atendente, **sem preço** · ⑤ nível máximo → **sem** gancho · ⑦ pergunta fora de
assistência → a base **não** é consultada. 🧑 **TESTE-A:** ⑥ "cobre granizo?". 🤖 **Executor:** ⑧ busca derrubada →
`fonte_indisponivel`, texto **diferente** do 2.

## Decisões do Founder — não se reabrem

**D-PILOTO-01** conhecimento é **GLOBAL** (nenhuma tabela com `company_id`) · **D-PILOTO-11** o **PDF** vence em
cobertura/franquia/**plano**, e seguradoras e ramos são **catálogo nosso** (chave SUSEP) · **D-PILOTO-12** o gancho
passa o caso à **atendente do card Equipe** · **D-PILOTO-14** **≤ 12 guardas novos**, pelo motor · **D-PROTO-01/02**
AAA FAST, 001.5 = **experimento C** · **D-PROTO-08 (v12.1)** UMA sessão, builder fresco da fatia 2 em diante.

## 📋 Caixa do Founder

① **revisar e publicar as primeiras linhas da fila de curadoria**, ou indicar quem revisa — **única dependência
humana, e bloqueia o canário completo** (💭 uma seguradora, um ramo, ~10 linhas bastam) · ② os casos 1–5 e 7 no
chat da Resulta · ③ o caso 6 pelo TESTE-A · ④ o **Implantar** · ⑤ a validação com as atendentes. **Nenhum bloqueia
a entrega na `main`.**

## O que ficou fora (§2)

Cotação/renovação do plano superior (**quem orça é gente**) · a porta `PolicyDataProvider` e o modelo de apólice
(é a 001.1 — a 001.5 **consome, não edita**) · a apólice certa e coberturas patrimoniais · adaptadores
Quiver/Agger/Segfy · chunker com página · `insurer_key` nas 14 tabelas · `ficha.faltando`, `_TITULOS`, dossiê de
sinistro. Cada um vira entrada em `PENDENCIAS.md` (**o que destrava · de quem é · o que custa esquecer**), e
**P-PILOTO-04** fica **PARCIAL**. Escopo não se reduz sem o Founder (D5).

**⚠️ Vencido:** 🔴 "`origem` via `nodes.py:784,1057`" é **falso** (grava `skills/gateway.py:294,323`) ·
`infocap_tool.py:319` não confere · §4 passos 2 e 10 já resolvidos.
