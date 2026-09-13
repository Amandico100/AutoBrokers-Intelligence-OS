# SPEC-EXTRA-001.5 — O AGENTE SABE O QUE CADA PLANO COBRE
## Três níveis de assistência por seguradora, numa base com fonte e página por linha

**Status:** PROPOSTA PARA CONVERSÃO, AQUECIMENTO E EXECUÇÃO — não é SPEC aprovada nem implementação realizada.
**Versão:** 1.0 · 13/09/2026. **Baseline:** `a0bb5fe` (📊 `git rev-parse HEAD` hoje; 0 atrás e 0 à frente de `origin/main`).
**Branch sugerida:** `feat/spec-extra-001-5-planos-de-assistencia`.
**SPEC definitiva a criar:** `docs/canon/specs/SPEC-EXTRA-001.5-o-agente-sabe-o-que-cada-plano-cobre.md`.
**Research Pack:** `SPEC-EXTRA-001.5-…-RESEARCH-PACK.md` — **as evidências `arquivo:linha` (C01–C57) e as consultas
📊 (M1–M7) vivem lá; esta proposta as cita por ID e não as repete.**
**Prompt:** `PROMPT-DE-ABERTURA-EXTRA-001.5.md`. **Relatório:** `docs/canon/reports/SPEC-EXTRA-001.5-EXECUTION-REPORT.md`.
**Origem:** `DIAGNOSTICO-PILOTOS-E-PLANO-EXTRA-2026-09-12.md` §1.3, §3 (bloco 001.5), **§7.3**, **§7.6**, §12.1.
**Protocolo:** AAA v11.2 + OPÇÃO B. Marcha **PADRÃO** · **1 lente + 1 juiz fresco + canário vivo** · 💭 10–14 h ·
**trilho paralelo**, abre quando o BLOCO A da EXTRA-001.1 fechar. **Absorve** P-PILOTO-04 (só a parte de conhecimento).

---

## 0. Resultado e motivo

> O corretor pergunta *"o segurado X tem carro reserva?"*, *"cobre granizo?"*, *"qual o limite do guincho?"* — e
> recebe **sim · não · não contratado · não sabemos ainda**, com a **origem escrita ao lado** (documento e página),
> para **qualquer** seguradora que a corretora usa. A resposta diz o **nível** do plano: *"o seu é o Essencial da
> HDI: guincho até 200 km, sem carro reserva."* Quando existe plano acima **na tabela**, e só então, aparece o
> gancho comercial. **"Não sabemos ainda" é resposta honesta e conta como acerto. "A fonte não retornou" é falha, e
> tem outro nome na tela.**

### 0.1 Os números, remedidos hoje (consultas em RP §2)

| 📊 medido em 13/09/2026, banco de produção, só SELECT | resultado |
|---|---|
| documentos em `normative_documents` · **indexados** (`ingested` + `chunk_count>0`) | **194** · **97** |
| **seguradoras reais** com condição geral indexada | **8** (allianz azul bradesco hdi mapfre porto tokio yelum) + `susep`, o regulador |
| siglas da **carteira viva** da piloto · com chave canônica · cobertura de prêmio | **61** · 14 · **83,86%** |
| das 14 canônicas, quantas têm CG **sob a mesma chave** | **6** — `tokio` não casa com `tokio_marine` (§0.3 ③) |
| **planos/níveis de assistência estruturados** em qualquer tabela | **0** — nenhuma tabela, nenhuma coluna |
| corpus por ramo | auto **24** · resi **24** · condomínio **8** · **vida 101** (a maior fatia **não** é a carteira dos pilotos) |
| cartas publicadas · de assistência · **sem** seguradora nomeada | **17.995** · **1.535** · **784** |
| perguntas reais no acervo (`messages`, papel humano) | guincho **121** · vidro **93** · carro reserva **81** · eletricista **36** · granizo **26** · chaveiro **24** |

⚠️ **Três números do diagnóstico não bateram; o de hoje vence** (protocolo §5 ①; RP §3): *"10 de 61 seguradoras"* →
**8**, e **6** exigindo que a chave case · *"`knowledge_cards` 857/39/4"* → **17.995/1.535/20** · *"a ligação apólice
→ CG por SUSEP **já casa hoje**"* → 🔴 **não existe, e está bloqueada** (§0.3 ②).

E o motivo: o agente **misturou Allianz auto com residencial** e admitiu *"não recuperei o detalhe fino do plano
VIP"*. 📊 O que ele tem hoje é `assistance_policy.py` — **142 linhas, três serviços residenciais fixos** (`:28`),
**sem seguradora, sem produto, sem nível; "carro reserva" não aparece no arquivo**.

### 0.2 Decisões do Founder já incorporadas — são lei

| ID | Decisão | Onde |
|---|---|---|
| **D-PILOTO-01** | Conhecimento de atendimento é **GLOBAL**: toda corretora usa o mesmo | `FOUNDER-DECISIONS.md:1745` |
| **D-PILOTO-08** | Numeração **EXTRA-001.5**; nada renumera | `:1752` |
| **D-PILOTO-11** | **PDF** vence em cobertura/franquia/**plano**; sistema de gestão em parcela/status. Não nasce presa à InfoCap. **Seguradoras e ramos são catálogo nosso (chave SUSEP)** | `:1755` |
| **D-PILOTO-14** | **≤ 12 guardas novos**, bateria sobre o **motor** e o **acervo real** | `:1758` |
| **D-PILOTO-16** | SPEC-101 vira a porta; EXTRA-002/008/009 viram adaptadores | `:1760` |
| **D-PILOTO-20** | Execução em **chat novo**, sob AAA opção B | `:1763` |

🔴 **D-PILOTO-01 decide a forma da tabela:** ela é **global, sem `company_id`**. O que a HDI cobre no Essencial é o
mesmo para a Resulta, a AutoFleet e quem entrar amanhã. §3.3 prova que isso não é furo: **não há dado de corretora
aqui.**

### 0.3 🔴 As quatro correções que mudam esta SPEC — todas medidas hoje

**① O corpus não mora em `documents`. Mora em `normative_documents` — e o pipeline inteiro já existe.** 📊 `doc_kind`
**não existe** em `documents` (RP M7). `insurance_corpus.py` (2.020 linhas) já faz descobrir · classificar ·
**aprovar/rejeitar/candidatos** · baixar · extrair · limpar · partir · etiquetar · indexar no global · versionar ·
reconferir. 🔴 **A fila de curadoria que a proposta pediu (`curation_status`) JÁ EXISTE**: `status` +
`approved_at`/`approved_by`, com `vencidos()` exigindo `approved_at is not null` (RP C29). Criar outra seria motor
paralelo (CLAUDE.md §5). Esta SPEC pendura na que existe e acrescenta a curadoria da **linha extraída**, que é outro
julgamento (§5.4).

**② O elo apólice → condições gerais não existe. E está ativamente bloqueado.** 📊 O extrator existe
(`insurance_corpus.py:65`) e o lado do corpus está pronto (`susep_process` em **190 de 194**). Mas
`grep -rn 'eq("susep_process"' backend/` → **vazio**, e a única ocorrência de `susep` na camada de apólice é o
contrário do que se precisa: `policy_document_evidence_service.py:204-209` tem **`susep` dentro de
`_BOILERPLATE_RE`** — **toda linha do PDF da apólice que menciona SUSEP é descartada como entulho**, inclusive a que
carrega o número do processo. A ponte não está faltando: está **demolida**, por um filtro escrito para outro fim.
§7.2 a reabre, e **M-C2 exige ZERO casamentos com o filtro de volta** — é assim que se prova que era o filtro
(CLAUDE.md §9.4).

**③ Não existe chave canônica de seguradora. Existem quatro, e duas já discordam.** 📊 14 tabelas têm `insurer_key`;
**zero constraints** a mencionam. `portals`→`tokio_marine` · `normative_documents`→`tokio` ·
`knowledge_cards`→`tokio` (mais 5 chaves que `portals` não tem) · `seguradora-coenti.json`→`tokio_marine`.
**Consequência:** a Tokio tem **25 documentos** e, num casamento por chave canônica, **cairia para zero, em
silêncio**. A HDI tem **10** e **não está entre as 61 siglas** — é a seguradora da apólice de referência da Saionara.
🔴 **Base pendurada em chave que ninguém governa emudece por digitação.** §5.1 resolve antes do primeiro dado.

**④ A procedência é gravada e morre na volta — e o corpus não tem página.** 📊 `insurance_corpus.py:1125-1171` grava
na raiz do payload `insurer_key`, `doc_kind`, `susep_process`, `effective_from`, `vigente`, `unit_id`, `faceta`;
📊 `qdrant_service.py:891-909` monta o resultado com **oito chaves, e nenhuma é essas** — a procedência entra
estruturada e volta **como texto** (a etiqueta colada dentro do pedaço). 📊 **`doc_kind` nunca filtra**: não está no
índice de payload (`:88-99`) nem na assinatura de `search_similar` (`:639-668`). E 🔴 **o corpus normativo não tem
página** — o corte é por **seção** (`:696`); do outro lado, o caminho da apólice **tem** página
(`policy_document_evidence_service.py:387-407`) e `nodes.py:297-303` **já rejeita página inventada**, mas o fallback
docling devolve **uma única página, `page_number: 1`** (`:539-549`). **Citar a partir do chunk é impossível; citar a
partir do docling é mentir.** §7.1 extrai da **fonte arquivada**.

### 0.4 EXECUTION CARD proposto — a medir no BLOCO 0, não a copiar

```text
OUTCOME .............. "tem carro reserva? cobre granizo? qual o limite do guincho?" → sim · não ·
                       não contratado · NÃO SABEMOS AINDA, com documento e página ao lado, dizendo
                       o NÍVEL do plano contratado, para toda seguradora que a corretora usa
RISCO ................ 7 = ALCANCE 3 (o SEGURADO lê "você tem carro reserva")
                          + REVERSIBILIDADE 2 (dado e estrutura: tabela nova, CHECK de tabela viva)
                          + FREQUÊNCIA 2 (toda pergunta de cobertura, no chat e no atendimento)
                       ⚠️ VER §0.5: a soma dá CRÍTICO e a marcha fixada é PADRÃO. Registrada, não silenciada
SUPERFÍCIE ........... 2 (peça nova — tabela e Skill — mais comportamentos que eu consigo listar)
                       ⚠️ vira 3 se o BLOCO 0 achar leitor do corpus fora da lista de §3.1
PISO APLICADO ........ §3.2 dispara em UM ponto e só nele: a migration que ALARGA O CHECK de `doc_kind`
                       numa tabela VIVA e de DDL não rastreada (§11.2). A tabela nova é aditiva
NÍVEL ................ PADRÃO — opção B, com o reforço de §0.5
UNIDADES ............. 5 · A tabela+chave · B a Skill · C as três ondas · D a tela · E a medição
COESÃO ............... A é arquivo-hub (chave + migrations): UM dono, primeiro, sozinho. B e C consomem
                       o contrato de A → integração SERIAL. D e E são disjuntas
PARALELISMO REAL ..... (D ∥ E) ∥ (A → B → C). Nenhum outro
TIME ................. investigador+pesquisador (um agente, §10) · desenhista da prova ANTES do código ·
                       builder por unidade · verificador mecânico · UMA lente (produto + DADO, porque o
                       outcome É um dataset — §5 ④) · UM JUIZ FRESCO que confirma o conserto e audita o dado
REFERÊNCIA ........... INTERNA: backend/tests/test_a_cobertura_tem_lastro_no_acervo.py (254 linhas) — o
                       guarda que já exige que toda afirmação de COBERTURA aponte uma tela do acervo. É o
                       mesmo formato aplicado à linha da tabela. O juiz abre e compara
                       EXTERNA: as 3 de §15, reabertas em 13/09/2026
GATES ................ GA, GB, GC, GD, GE, G-MIG, G-CANÁRIO + os canônicos
O ELO ................ "o agente responde genérico PORQUE não há plano estruturado": medir A (respostas
                       genéricas do acervo), medir B (0 linhas de plano) e 🔴 medir que B CHEGA em A —
                       rodar a Skill ATUAL sobre perguntas reais de carro reserva e mostrar
                       assistance_policy.py:28 devolvendo os mesmos 3 serviços residenciais
FAIXA DE RELÓGIO ..... 💭 10–14 h · faixa, nunca promessa (§9.2)
ORÇAMENTO ............ 💭 0,9–1,5 M tokens no chat executor. Medir, não prometer
```

### 0.5 🔴 A divergência de marcha, escrita em vez de escondida

A conta dá **RISCO 7 → CRÍTICO** (§3.1); a marcha fixada pelo Founder é **PADRÃO** (diagnóstico §8/§12.1,
D-PILOTO-14), ajustada nesta redação para **1 lente + juiz fresco + canário**. §3.1 diz *"se o rótulo e a soma
discordarem, a soma vence"*; §3.2 diz que a exceção do Founder **só sobe**. **Não é condição de parada** (nenhuma
das oito do CLAUDE.md §10): é divergência a resolver com nota (§9).

- **PADRÃO com o piso aplicado nos dois pontos onde ele dispara — 86.** A lente única é "produto + DADO", a que §5 ④
  **exige** quando o outcome é dataset; o juiz fresco audita o dado; o canário prova a resposta; e §11.2 recebe
  tratamento CRÍTICO com manifesto completo.
- **Subir tudo para 3 lentes — 62.** Duas lentes a mais lendo o mesmo diff; o defeito aqui é **dado errado com cara
  de certo**, e isso uma lente de DADO pega melhor que três de código.
- **Baixar e seguir sem registrar — 15.** Rebaixamento silencioso de um RISCO 7 que chega ao segurado.

🔴 **O executor recalcula no BLOCO 0.** Soma 6+? escreve a divergência no card, mantém a marcha e **aplica o piso
nos dois pontos**: (a) a migration de §11.2, (b) todo texto que chega ao segurado (§6.2). Soma 5 ou menos? escreve
por quê.

---

## 1. AUTORIZAÇÃO DE TESTES — a fronteira, antes de qualquer efeito

| Alias | Uso nesta SPEC |
|---|---|
| **TESTE-A** | único número de WhatsApp autorizado no canário de atendimento |
| **TESTE-B** | segundo número, só se o caso exigir dois interlocutores |

Os valores reais ficam na configuração privada existente (`ATTENDANT_INBOUND_ALLOWLIST` /
`JANELA_SILENCIO_EXCECOES`, commit `05f46a9`). **Nunca commitar, publicar em dossiê, print, log, fixture ou
relatório.** No canon só existem os aliases.

**Autorizado:** ler o banco de produção **em SELECT e contagem**; ler o corpus normativo e as fontes arquivadas no
MinIO (documentos **públicos** de seguradora); **baixar condições gerais e manuais de assistência de sites públicos
e do registro público da SUSEP (REP2)** pelo caminho existente (`insurance_corpus._buscar`); chat `core` do painel
da Resulta pela conta do Founder; **uma** conversa com TESTE-A, com o agente habilitado **apenas** para esse número;
rodar a suíte, mutações em cópia, e as duas migrations de §11 **depois** do gate.

**Proibido:** ① qualquer mensagem a segurado real, seguradora, atendente, grupo de suporte ou número fora da
allowlist — inclusive por fallback, alerta, fila, retry ou job de fundo; ② ligar o agente globalmente numa corretora
operacional; ③ **entrar em portal com login, acionar assistência, abrir chamado, alterar apólice** — nada desta SPEC
precisa; ④ gravar em arquivo, log, teste, fixture, dossiê, commit ou relatório CPF, CNPJ, telefone, nome de
segurado, placa, chassi, e-mail, endereço, número completo de apólice ou credencial; ⑤ copiar dado de uma corretora
para outra; ⑥ 🔴 **publicar linha da base sem revisão humana** — extração assistida por modelo **propõe**, gente
publica; ⑦ rodar migration antes do gate, ou aplicar `schema_completo.sql` / `upgrade_v6.2.sql` / `storage_buckets.sql`.

🔴 **A verificação específica desta SPEC:** antes de gravar qualquer linha ou fixture, o texto citado passa pelo
redator de PII existente e é **conferido por consulta**, não por leitura. Condição geral é documento público — mas o
**exemplo** que o extrator copiar pode ter vindo de uma apólice. **Valor em R$, km e dias é permitido; identificador
de pessoa, nunca.** E o trecho entra **como referência** (documento + página + `trecho_hash`), não como cópia.

---

## 2. Escopo completo e exclusões deliberadas

**Obrigatório:** ① a **chave canônica** governada, com guarda, antes do primeiro dado (§5.1); ②
`insurer_assistance_plans` (com **`nivel`**) e `insurer_assistance_services` (com **documento-fonte e página
obrigatórios por CHECK**), migrations expand-first com APPLY/VERIFY/ROLLBACK (§11); ③ a Skill única
`cobertura_e_assistencia` com os **cinco estados** e origem escrita (§6); ④ `assistance_policy.py` **vira fallback
com marca** (§6.4); ⑤ as **três ondas** com revisão humana antes de publicar (§7); ⑥ `doc_kind` passa a **filtrar** e
a **procedência volta como campo** (§6.5); ⑦ a **tela mínima** (§8); ⑧ a **medição declarada** com `origem` no turno
(§9); ⑨ **P-PILOTO-04**, só a parte de conhecimento.

| Fora desta SPEC | Por que não entra | Volta em |
|---|---|---|
| **cotação e renovação** do plano superior | 🔴 outra SPEC. Esta **diz** que o plano superior existe e o que cobre; **quem orça é gente** | EXTRA-003 · 004 |
| a porta `PolicyDataProvider` e o modelo canônico de apólice | é a **001.1**; 📊 a porta existe (`policy_data_provider.py:41`). A 001.5 **consome, não edita** — dois escritores no mesmo arquivo é o que §3.4 proíbe | EXTRA-001.1 |
| ler a apólice certa em uma rodada (vigência, ramo, briefing) | é a 001.1; a 001.5 recebe a apólice escolhida | EXTRA-001.1 |
| coberturas patrimoniais (LMI, franquia, cláusula) | a 001.1 as entrega pela reconciliação CORP × PDF | já na 001.1 |
| adaptadores Quiver / Agger / Segfy | sem credencial; a base pendura na **chave nossa** e já serve qualquer um | EXTRA-002/008/009 |
| reescrever o chunker para carregar **página** | tocaria 42.091 pedaços por algo que §7.1 resolve pela fonte arquivada | pendência com número |
| normalizar `insurer_key` nas 14 tabelas | migração não medida; o módulo resolve no ponto de uso (nota 82 × 40) | pendência com número |
| `ficha.faltando`, `_TITULOS`, dossiê de sinistro (resto de P-PILOTO-04) | é a 001.3 | EXTRA-001.3 |
| rajadas, debounce, dossiê ao grupo | 001.2 e 001.3; mesmo arquivo, dois escritores | EXTRA-001.2/001.3 |

🔴 **Nada do obrigatório sai em silêncio.** Conflito material vai para `CHANGE-ADDENDA.md` classificado
(BLOCKER · ESSENCIAL · VALIOSA · FUTURA), com problema, evidência, consequência e autorização (CLAUDE.md §11).
**Escopo não se reduz sem decisão explícita do Founder (D5).**

---

## 3. Autoridades preservadas e arquitetura

### 3.1 O que se reaproveita (evidência `arquivo:linha` em RP §1)

| peça | já existe em | o que a 001.5 faz |
|---|---|---|
| corpus, curadoria, versão, manutenção | `insurance_corpus.py` · `normative_documents` · `normative_document_versions` | **reusa inteiro**; nenhum segundo pipeline |
| extrator e normalizador de processo SUSEP | `insurance_corpus.py:49,65` · `susep_rep2.py:214` | reusa; falta **chamá-lo do lado da apólice** (§7.2) |
| fila de curadoria do documento | `insurance_corpus.py:1887,1900,1908,1921` · `api/corpus.py:90` | **pendura**; a curadoria da **linha** é irmã (§5.4) |
| manutenção por `content_hash` | `insurance_corpus.py:58-62,1433-1438`; 📊 `next_check_at` 194/194 | reusa; §7.4 estende à linha |
| arquivo da fonte (bytes, MinIO) | `insurance_corpus.py:1608` → `acervo_arquivo.py` | 🔴 **é daqui que a extração lê a página** (§7.1) |
| coleção global e escopo | `knowledge_scope.py:37,383-389` | reusa; **nenhuma coleção nova** |
| busca híbrida com filtros | `search_service.py:466-579` · `qdrant_service.py:434,835` | **estende** com `doc_kind`; nenhum buscador novo |
| catálogo de seguradoras e ramos | `docs/canon/providers/susep/*.json` · `susep_ses_provider.py:129-212` | **pendura**; §5.1 acrescenta o que falta |
| a porta da apólice | `policy_data_provider.py:41,55,137,144` | **consome o que a 001.1 entregar**; não edita |
| plano vindo do documento | `policy_document_evidence_service.py:230-318` | 🔴 **já extrai o bloco de assistência do PDF.** Reusa |
| regra de assistência residencial | `assistance_policy.py` (142 linhas) | **vira fallback com marca** (§6.4) |
| guarda de afirmação com lastro · de página citada | `tests/test_a_cobertura_tem_lastro_no_acervo.py` · `nodes.py:297-303` | referência do juiz; **reusa o padrão** |
| registro de ferramenta do turno | `tool_invocations` · `gateway.py:294` · `nodes.py:784,1057` | grava `origem` pelo que existe; **nenhum segundo registro** |

### 3.2 🔴 A fronteira, escrita como regra verificável

```
A BASE É GLOBAL: nenhuma tabela desta SPEC tem company_id, e nenhuma linha dela carrega nome,
        documento, telefone, apólice ou qualquer dado de cliente.
NINGUÉM cria segunda coleção de Qdrant, segundo pipeline de ingestão, segunda fila de curadoria,
        segundo catálogo de seguradoras ou segundo caminho de leitura documental.
NENHUM texto ao corretor ou ao segurado nomeia o sistema de gestão — diz "as condições gerais da
        <seguradora>" e "o documento oficial da apólice".
NENHUMA linha entra sem documento-fonte e página. O BANCO recusa, não o código.
```

### 3.3 Multi-tenant — e por que aqui a prova é ao contrário (CLAUDE.md §7)

CLAUDE.md §7 exige *"teste de isolamento com dois tenants reais"*. **Esta base não tem tenant.** A prova é **"não
existe dado de corretora aqui"**, em três partes (guarda **M-A4**): ① **estrutural** — nenhuma tabela tem
`company_id`, `user_id` ou FK para `companies`; um `ALTER TABLE` que acrescente `company_id` deixa o guarda
vermelho, porque conhecimento global com coluna de dono é o começo de "a base da Resulta"; ② **de conteúdo** — o
varredor de PII existente roda sobre as colunas de texto e acha **zero**; ③ **de efeito** — a leitura usa
`build_global_search_kwargs()` (`knowledge_scope.py:384`), que **não passa `company_id` algum**, e o teste de duas
corretoras prova que **as duas recebem a mesma resposta** para a mesma apólice da mesma seguradora.

⚠️ **O que continua tenant-scoped:** a **apólice**, que chega pela porta da 001.1 com `company_id` explícito. A base
diz *"o Essencial da HDI tem guincho até 200 km"*; **quem tem esse plano** nunca entra aqui.

---

## 4. BLOCO 0 — converter medindo, antes de qualquer código

> Conferido em 13/09/2026 sobre `a0bb5fe`. **O número do executor vence.**

1. **Preflight**, com a saída colada: `git fetch origin` · `git rev-list --count HEAD..origin/main` (🔴 tem de ser 0)
   · `git rev-list --count origin/main..HEAD` · `git branch --show-current` · `git rev-parse HEAD` · `git status --short`.
2. **Confirmar que a 001.1 fechou o BLOCO A.** Se não, medir o que existe e escrever o contrato mínimo — **sem
   editar a porta**.
3. **Reabrir cada `arquivo:linha` do RP §1** e **rerodar as 7 medições do RP §2**. Divergiu? corrigir **e anotar**.
4. **Medir o casamento de chave** (RP M2/M3), que decide o tamanho do Bloco A. **Contar os órfãos dos dois lados.**
5. 🔴 **Provar a armadilha do `susep` com comando:** rodar o extrator documental sobre um PDF de apólice do acervo
   **com** e **sem** `susep` em `_BOILERPLATE_RE` e contar os processos recuperados. 📊 Esperado: **0 com, ≥1 sem**.
6. **Medir o ELO com a ferramenta que vai usar** (CLAUDE.md §9.4): rodar a Skill **atual** sobre 10 perguntas reais
   de "carro reserva" e mostrar `assistance_policy.py:28` devolvendo os mesmos três serviços residenciais.
7. **Ler `MIGRATIONS-AUTHORITY.md` inteiro** antes de qualquer SQL. 🔴 Ler o DDL **real** de `normative_documents` no
   catálogo do Postgres: 📊 a tabela é **classe SEM_ARQUIVO** (RP C55).
8. **Linha de base da suíte** (falhas preexistentes nomeadas, uma a uma). 🔴 Conferir se **P-PILOTO-20** já foi
   fechada pela 001.1 — com aqueles 4 guardas mudos, esta SPEC não fecha.
9. **Recontar RISCO e SUPERFÍCIE** e escrever o card definitivo, com §0.5 resolvida por escrito.

**GATE B0:** matriz `premissa → observação nova → comando → decisão`, com **as divergências listadas**. Nenhum achado
não reproduzido entra como incidente confirmado.
**MUTAÇÃO B0:** o aquecimento carrega **duas afirmações deliberadamente falsas, assinadas** (prompt §6). O executor
refuta **com comando**, não com leitura.

---

## 5. BLOCO A — A CHAVE E A TABELA

> Arquivo-hub. **UM dono. Primeiro, sozinho.** Arquivos: `backend/app/providers/insurer_catalog.py` (novo, pequeno)
> · `docs/canon/providers/susep/seguradora-coenti.json` (linhas novas, revisadas) · as duas migrations de §11.

### 5.1 A chave canônica — governada, antes do primeiro dado

📊 O catálogo já tem a governança certa escrita (`susep_ses_provider.py:165-167`): *"Uma sigla só entra por
igualdade de nome COMPLETO com o Noenti do SES ou por DECISÃO EXPLÍCITA de gente. Nunca por derivação de string em
runtime."* **O que a 001.5 acrescenta:**

1. **Um módulo de leitura único** — `insurer_catalog.py` — com `chave_canonica(valor)`, que resolve uma chave vinda
   de qualquer tabela por **mapa explícito** e devolve a sentinela `UNKNOWN` (**a string, nunca `None`** — o motivo
   está em `susep_ses_provider.py:92-95`) quando não casa.
2. **As linhas de conciliação que faltam:** `tokio` → `tokio_marine`, e as chaves de `knowledge_cards` ausentes de
   `portals` (`axa`, `chubb`, `essor`, `itau`, `unimed`, `youse`), **listadas, com o critério ao lado**. 🔴 Uma por
   uma, revisada por gente.
3. **`hdi` entra nas siglas** ou fica registrado por que não entra — 📊 tem 10 documentos e é a seguradora da
   apólice de referência.
4. **A tabela nova referencia a chave canônica**; **M-A1** fica vermelho com chave que o catálogo não conhece.

⚠️ **O que a 001.5 NÃO faz:** normalizar `insurer_key` nas 14 tabelas existentes (§2, pendência com número).

### 5.2 As duas tabelas — e por que são duas

O pedido junta duas coisas: o **plano** (nível, vigência) e a **linha de serviço** (limite, carência, **fonte**).
Duas tabelas: **88**. Tabela única: **60** — repete o plano em cada serviço, o *"existe plano acima?"* vira
`DISTINCT` sobre dado repetido, e o CHECK de fonte obrigatória, que pertence à **linha**, sobra no plano. **O nome
que o Founder fixou fica no pai.**

```sql
insurer_assistance_plans                     -- O PLANO: o que a seguradora vende, e em que nível
  id uuid pk
  insurer_key   text not null                -- chave CANÔNICA (§5.1)
  ramo          text not null                -- chave nossa (ramo-cogrupo.json)
  produto       text not null                -- "Auto Perfil"; 'GERAL' quando a CG não separa
  plano         text not null                -- "Essencial", "Completo", "VIP"
  nivel         int  not null                -- 1..N DENTRO do produto. 1 = o mais básico
  vigencia_inicio date not null              -- a condição que vale na EMISSÃO da apólice (§7.2)
  vigencia_fim    date null                  -- null = vigente
  susep_process text null                    -- o elo com a condição geral
  documento_id  uuid not null                -- FK -> normative_documents
  pagina        int  not null                -- a página onde o plano é nomeado
  confianca     text not null                -- alta | media | baixa
  curadoria     text not null                -- rascunho | proposto | publicado | rejeitado
  revisado_por  uuid null · revisado_em timestamptz null
  content_hash  text not null                -- do documento de origem, para a manutenção (§7.4)
  unique (insurer_key, ramo, produto, plano, vigencia_inicio)
  unique (insurer_key, ramo, produto, nivel, vigencia_inicio)   -- 🔴 dois planos no mesmo nível é erro

insurer_assistance_services                  -- A LINHA: o que o plano faz, com fonte obrigatória
  id uuid pk
  plano_id      uuid not null                -- FK -> insurer_assistance_plans, on delete cascade
  servico       text not null                -- chave nossa: guincho | carro_reserva | chaveiro |
                                             -- vidros | eletricista | encanador | hospedagem | ...
  coberto       text not null                -- sim | nao | condicionado
  limite_valor  numeric null · limite_unidade text null   -- km | dias | acionamentos_ano | reais
  limite_texto  text null                    -- a prosa, quando o limite não é número
  carencia_dias int null · condicao text null             -- "só em caso de sinistro coberto"
  documento_id  uuid not null                -- 🔴 NOT NULL
  pagina        int  not null                -- 🔴 NOT NULL, >= 1
  trecho_hash   text not null                -- sha256 do trecho; o trecho CRU não é copiado
  confianca     text not null · curadoria text not null
  revisado_por  uuid null · revisado_em timestamptz null
  unique (plano_id, servico)

-- 🔴 Os três CHECKs de insurer_assistance_services:
constraint servico_tem_fonte check (
    documento_id is not null and pagina is not null and pagina >= 1
    and trecho_hash is not null and length(trecho_hash) = 64),
constraint servico_publicado_foi_revisado check (
    curadoria <> 'publicado' or (revisado_por is not null and revisado_em is not null)),
constraint limite_tem_unidade check (limite_valor is null or limite_unidade is not null)
```

🔴 **`servico` é chave nossa, não texto livre.** Uma tabela em que "carro reserva", "veículo reserva" e "carro extra"
são três serviços diferentes não responde a pergunta. O vocabulário nasce **das perguntas reais do acervo** (📊 §0.1)
e mora num arquivo versionado ao lado do catálogo, com sinônimos declarados — **nunca num regex escondido**.

O segundo CHECK impede o pior desfecho desta SPEC: **uma extração assistida por modelo publicando sozinha**. O
terceiro é pequeno e caro: 💭 `limite_valor=200` sem unidade vira "200 dias de carro reserva" na cabeça de quem lê.
**Número sem unidade é número errado.**

### 5.3 A curadoria da linha é irmã da curadoria do documento

O **documento** já é curado (`normative_documents.status` + `approved_at`/`approved_by`, com
`aprovar()`/`rejeitar()`/`candidatos()`) — a 001.5 não acrescenta nada ali. A **linha extraída** não é curada por
ninguém hoje, e ganha `curadoria` + `revisado_por`/`revisado_em` nas duas tabelas, com a fila na tela (§8).
**São dois julgamentos:** aprovar o PDF da HDI não é aprovar *"guincho até 200 km"*. Um campo só publicaria 40 linhas
que ninguém leu.

**GATE A:** ① as tabelas existem com os CHECKs, e `INSERT` sem `documento_id`, sem `pagina`, com `pagina=0` e
`curadoria='publicado'` sem revisor são **recusados pelo banco**, com o erro colado; ② `chave_canonica("tokio")` e
`chave_canonica("tokio_marine")` devolvem **a mesma**; `chave_canonica("xpto")` devolve `UNKNOWN` **com o nome
listado**; ③ nenhuma coluna `company_id`, varredor de PII = **0**; ④ duas corretoras, a mesma apólice → **a mesma**
resposta.
**MUTAÇÃO A:** (a) `documento_id`/`pagina` nullable; (b) `pagina=0`; (c) `publicado` com `revisado_por IS NULL`;
(d) `ADD COLUMN company_id`; (e) `limite_valor` sem `limite_unidade`. **As cinco vermelhas.**

---

## 6. BLOCO B — A SKILL `cobertura_e_assistencia`

> Arquivos: `backend/app/agents/tools/cobertura_e_assistencia.py` (novo) · `assistance_policy.py` (vira fallback) ·
> `search_service.py` / `qdrant_service.py` · `nodes.py:307-317` (o guarda que muda de regra).

**Skill ou tool?** 📊 O GLOSSARIO define Skill como procedimento versionado (`skills`/`skill_releases`, 21 releases)
e Tool como implementação (`tool_definitions`). 📊 O caminho de apólice de hoje é **tool** (`graph.py:447-449`); o
`SkillRegistry` só é tocado por `gateway_cutover.py:153` e `auxiliaries/factory.py:333`. **Tool sob capability
própria: 88** — é o caminho que o chat e o atendimento percorrem, e ganha o registro em `tool_invocations` de graça;
o nome "Skill" do diagnóstico é o **conceito**. **Skill release: 45** — segundo caminho de resolução ao lado do que a
tool usa. ⚠️ **O BLOCO 0 confere** se algum agente resolve skill em runtime; se resolver, reescreve com o número.

### 6.1 A cadeia, do pedido à resposta

```
pergunta ("ele tem carro reserva?")
 ①  apólice VIGENTE do ramo deduzido    ← pela PORTA (001.1). A 001.5 não escolhe apólice
 ②  documento oficial da apólice         ← já no caminho feliz da 001.1
 ③  produto + plano contratado
       a) linha "Assistência"/bloco 24h do PDF  (policy_document_evidence_service.py:230-318)
       b) `tabela_itens` do sistema de gestão   (o nome do plano; hoje só vira sinal, :4015)
       c) processo SUSEP do PDF                 (§7.2 — amarra na condição geral CERTA)
 ④  chave canônica: seguradora + ramo + produto + plano → insurer_assistance_plans
 ⑤  a linha do serviço perguntado                      → insurer_assistance_services
 ⑥  a prosa, quando a pergunta pede "por quê" → RAG global, FILTRADO por insurer_key +
                                                doc_kind + vigência na data da apólice
 ⑦  existe plano de nível > o contratado, mesmo produto e vigência? → o gancho (§6.3)
```

🔴 **③ é onde a resposta pode mentir com mais confiança.** Plano não identificado → **`nao_sabemos_ainda`**, nunca
"o plano padrão da seguradora". Guarda **M-B4**.

### 6.2 Os cinco estados — e a distinção que o Founder pediu

| estado | quando | 💭 como sai na conversa |
|---|---|---|
| `coberto` | linha publicada diz `sim` | *"Tem sim: carro reserva por 7 dias. (Condições gerais da HDI, p. 23.)"* |
| `nao_coberto` | linha publicada diz `nao` | *"No plano dele, não. O Essencial da HDI não tem carro reserva. (p. 23.)"* |
| `condicionado` | `condicionado` + `condicao` | *"Tem, mas só em caso de sinistro coberto — não em pane. (p. 24.)"* |
| `nao_contratado` | o serviço existe no produto e o **nível contratado** não o inclui | *"O plano dele é o Essencial, que não inclui. O Completo inclui 7 dias."* |
| 🔴 `nao_sabemos_ainda` | não há linha publicada para essa seguradora/ramo/produto/plano, **ou o plano não foi identificado** | *"Ainda não tenho as condições da <seguradora> para esse produto na base. Posso confirmar com a seguradora — quer que eu abra?"* |

**Os cinco contam como acerto na medição de §9.** 🔴 **E o sexto, que não é estado da base:** `fonte_indisponivel` —
a apólice não carregou, o documento não abriu, a busca falhou. 💭 *"Não consegui abrir a apólice dele agora."*
**Isto é falha**, tem outro texto, e outra coluna na tela. **Confundir os dois é o defeito que esta SPEC existe para
matar:** *"não sabemos ainda"* é honestidade sobre a base; *"a fonte não retornou"* é um incidente.

⚠️ **Regra de texto (e o piso de §0.5 se aplica aqui):** toda frase que diz **"não"** carrega documento e página.
Uma frase que diz "não cobre" **sem lastro** é proibida — custa um acionamento a que o segurado tinha direito.

### 6.3 O gancho comercial — e a trava

```
gancho aparece ⇔ existe linha em insurer_assistance_plans com mesmo insurer_key + ramo + produto,
                 nivel > nivel_contratado, curadoria='publicado', vigente na data da apólice
                 E a linha do serviço perguntado nesse plano superior diz coberto='sim'
```

💭 *"O plano acima (Completo) teria carro reserva por 7 dias — a Regina pode orçar a troca na renovação."*

🔴 **Três coisas que o gancho NÃO faz:** não diz preço, não diz o custo da troca, não promete que a seguradora
aceita. **Cotação é outra SPEC.** Ele **passa o caso para a atendente**, nomeando-a pelo card Equipe — nunca pelo
nome do agente (D-PILOTO-12; a 001.2 garante). Guarda **M-B3**.

### 6.4 O que acontece com `assistance_policy.py`

📊 Hoje: 142 linhas, três serviços (`:28`), gatilho por substring `"resid"` (`:54`), um único importador
(`policy_answer_composer.py:24`). O próprio arquivo declara a intenção em `:4-6`: *"migração para tabela
`platform_policies` com overrides por seguradora/produto/plano/corretora está prevista para quando o primeiro
override existir"*. **O primeiro override é esta SPEC.**

**Vira fallback, com marca, e não é apagado:** ① a Skill consulta a base **primeiro**; ② não achou e a apólice é
residencial com assistência confirmada → a regra antiga responde **marcada** (`origem='regra_generica'`,
`confianca='baixa'`), dizendo que é padrão de mercado, não o contrato dele; ③ 🔴 `policy_rule_facts` **perde o
vínculo com a apólice hoje** (`:123` fixa `locator_hash = None`) — conserta-se junto, porque fato sem apólice não se
audita depois.

⚠️ **E o guarda de saída muda de regra, não morre.** 📊 `nodes.py:307-317` hoje anula qualquer resposta final que
não contenha "eletricista" **e** "chaveiro" **e** ("hidraulica"|"hidráulica"|"encanador"). **Com a base no ar isso
passa a ser errado**: a resposta certa para uma apólice de auto não tem encanador.

```
contrato traz `assistencia_da_base` com N serviços?    → a resposta não pode OMITIR nenhum deles
contrato traz `assistance_policy_applied` (fallback)?  → a regra dos 3 serviços continua valendo
```

🔴 **Quem apagar o guarda "porque a base substituiu a regra" reabre o defeito que ele fechou.** Guarda **M-B5**.

### 6.5 A procedência que volta — o conserto de §0.3 ④

① `qdrant_service.py:891-909` passa a copiar para o item devolvido os campos que **já estão no payload**
(`insurer_key`, `doc_kind`, `susep_process`, `effective_from`, `vigente`, `unit_id`, `parent_id`, `faceta`) —
⚠️ **aditivo**, nenhum leitor perde chave. ② `doc_kind` entra em `_INDICES_DE_PAYLOAD` (`:88-99`) e vira parâmetro
de filtro de `search_similar`, no molde de `_filtro_de_seguradora:434` (o braço "desta OU sem" — documento sem
`doc_kind` não some). 🔴 **O índice é criado ANTES de qualquer ingestão nova**, porque a documentação primária é
explícita: *"For best results, create payload indexes before ingesting data"*.

**GATE B:** ① **30 perguntas reais do acervo**, por categoria (carro reserva, granizo, chaveiro, vidros, guincho,
residência) — 🔴 **só as perguntas, PII removida** — rodadas **pelo motor**: cada uma devolve um dos cinco estados, e
todo estado ≠ `nao_sabemos_ainda` traz **documento e página**; ② **linha de controle** (CLAUDE.md §9.2): pergunta que
**não** é de assistência (💭 "quantas parcelas faltam?") **não** consulta a base; ③ **par de controle:** a mesma
pergunta em duas apólices de níveis diferentes do mesmo produto → vereditos opostos, gancho só na inferior;
④ `doc_kind='condicoes_gerais'` filtra: com e sem o filtro os conjuntos diferem, e **zero** `manual_do_segurado` com
o filtro ligado.
**MUTAÇÃO B:** (a) `nao_sabemos_ainda` colapsando em `nao_coberto`; (b) origem removida; (c) plano inferido pela
seguradora; (d) gancho sem plano superior; (e) guarda de `nodes.py` apagado. **As cinco vermelhas.**

---

## 7. BLOCO C — AS TRÊS ONDAS DE COLETA

### 7.1 Onda 1 — extrair das 97 já indexadas, com revisão humana antes de publicar

📊 **auto 24 · residencial 24 · condomínio 8** são os ramos dos pilotos; **vida 101** é a maior fatia do corpus e
**não é a carteira que os pilotos vendem**. 🔴 **A onda 1 começa pelos 56, não pelos 97.** O resto fica declarado.

🔴 **A extração lê a FONTE ARQUIVADA, não o pedaço indexado** — porque o chunk não tem página (§0.3 ④). A fonte está
no MinIO (`insurance_corpus.py:1608` → `acervo_arquivo.py`) e o extrator por página existe (`:177`, PyMuPDF —
escolhido porque 📊 devolvia 11.064 linhas onde o PyPDF2 devolvia 519).

```
1. o extrator (modelo)      lê a fonte arquivada, página a página, e PROPÕE linhas
                            → curadoria='proposto', confianca, trecho_hash, pagina
2. o verificador (máquina)  a página existe? o trecho_hash bate com ela? o serviço está no
                            vocabulário? limite tem unidade? o nível é único no produto?
                            falhou → volta para 'rascunho' com o motivo, nunca para 'proposto'
3. a pessoa                 abre a fila (§8), vê o trecho ao lado da linha, publica ou rejeita
                            → 'publicado' + revisado_por + revisado_em  (o CHECK exige)
```

⚠️ **O verificador não é o revisor: ele só reprova, nunca aprova.** Um verificador que promove a `publicado` seria a
curadoria automática que o CHECK de §5.2 existe para impedir. 💭 **Meta da onda 1:** as **6 seguradoras** cuja chave
já casa, nos 3 ramos dos pilotos. O número real sai da onda, não desta proposta.

### 7.2 Onda 2 — o elo apólice → condição geral pelo processo SUSEP

① `susep` **sai** de `_BOILERPLATE_RE` (`policy_document_evidence_service.py:208`) — ⚠️ ele está lá por um motivo
real (rodapé institucional), então a substituição é cirúrgica: continua descartando `ouvidoria|sac 24`, e passa a
**capturar** a linha que casa `_RE_SUSEP`. **M-C2 exige ZERO com o filtro de volta.** ② `extrair_susep` roda sobre o
texto do PDF da apólice, e o processo entra no modelo canônico da 001.1 com origem `documento_oficial`.
③ `normative_documents` é consultado por `susep_process` — 📊 **190 de 194 têm o campo**. Casou → a condição geral
**daquele contrato** é a fonte, não "a condição geral atual da seguradora".

🔴 **E a armadilha que o próprio código já avisa** (docstring de abertura de `insurance_corpus.py`):

> *"Uma apólice emitida em 2023 é regida pela condição vigente **na emissão**, não pela de hoje. Um cache que guarda
> 'a condição atual' e responde sobre uma apólice antiga pode estar confiantemente errado sobre cobertura — e o
> corretor repete isso para o cliente."*

Por isso o plano tem `vigencia_inicio`/`vigencia_fim`, e a Skill busca **pela data de emissão da apólice**, não por
`now()`. 📊 A base sustenta: `normative_document_versions` tem **206 linhas para 194 documentos**, com
`effective_from`/`effective_until` e `superseded_at`. Guarda **M-C3**.

### 7.3 Onda 3 — as seguradoras ausentes, pela carteira

**O critério de ordem é a carteira, medida, não o alfabeto.** 📊 O `placar_das_siglas` foi construído sobre **a
carteira viva de 2025 da corretora piloto, 3.861 linhas, soma de `pretot` por sigla**, e cobre **83,86%** do prêmio.
A fila são as **12 siglas da carteira sem `coenti`** (`MAP, AXA, MAG, JUNT, AIG, ESSO, ITAU, BERK, CHUB, FATO, JNS,
MITS`) mais as canônicas sem CG (`alfa, seguros_unimed, sompo, suhai, sulamerica, sura, zurich`). ⚠️ **O BLOCO 0
remede a carteira pela porta** (D-PILOTO-11: o catálogo é nosso, o **peso** é da corretora). Das nove seguradoras que
o diagnóstico nomeia, **8 já estão presentes** — 📊 só a Zurich falta.

**`doc_kind='manual_de_assistencia'` é valor novo** e 📊 **não está entre os 9 do CHECK** → §11.2. ⚠️ Dívida herdada
a registrar, não a consertar: 📊 **3 dos 9 valores não têm escritor** (`condicoes_particulares`, `glossario`,
`regulamento`); o classificador produz apenas 6 (`insurance_corpus.py:976-983`).

### 7.4 Manutenção — já existe, e só precisa alcançar a linha

📊 `content_hash` com espaço normalizado (`:58-62`) impede que PDF re-renderizado pareça alteração; `:1433-1438` não
reingere com hash igual; `next_check_at` está em **194 de 194**. **O que a 001.5 acrescenta:** quando o
`content_hash` **muda**, as linhas daquele documento caem de `publicado` para **`proposto`**, com o motivo, e voltam
para a fila. 🔴 **Não são apagadas e não continuam publicadas em silêncio** — a resposta de ontem pode ter sido certa
e a de hoje já não ser.

**GATE C:** ① onda 1 sobre um documento de auto e um de residencial: página que **existe**, `trecho_hash` que
**bate**, e **nenhuma** linha em `publicado` sem revisor; ② onda 2 sobre uma apólice real: o processo é extraído,
**casa**, e a condição é a **vigente na emissão**; ③ **linha de controle:** com `susep` de volta no boilerplate o
casamento cai para **ZERO**; ④ `manual_de_assistencia` aceito depois da migration e **recusado antes**; ⑤ mudar o
`content_hash` derruba as linhas para `proposto` — e **não** as apaga.
**MUTAÇÃO C:** (a) verificador promovendo a `publicado`; (b) página inexistente aceita; (c) busca pela condição
**atual**; (d) `content_hash` novo mantendo as linhas publicadas. **As quatro vermelhas.**

---

## 8. BLOCO D — A TELA MÍNIMA (Conhecimento)

> Disjunta. ⚠️ A SPEC **não move** rotas (`agentes/even → corretora/…` é a 001.9).

**① Cobertura da base** — seguradoras × ramos × planos × fonte:

```
seguradora   ramo         produto      planos     serviços  fonte                       atualizado
HDI          residencial  Residencial  2 níveis     14      Condições gerais · p.23-26   há 3 dias
Allianz      auto         —              —           —      🔴 nenhuma linha publicada    —
Zurich       —            —              —           —      ⚪ sem condições gerais        —
```

🔴 **A régua conta seguradora × ramo com plano publicado — não conta linhas.** É o erro que
`tests/test_cobertura_nao_mente_para_cima.py` documenta (📊 Allianz: painel 63%, real 37%): uma seguradora com 40
linhas de um ramo só não é "a base está boa". Guarda **M-D1**.

**② A fila de curadoria** — cada item mostra seguradora · ramo · produto · plano/nível · serviço · o que o extrator
propôs · **o trecho e a página ao lado**, para a pessoa não precisar abrir o PDF. Publicar exige a leitura; rejeitar
exige motivo. ⚠️ **Não exibir nome de tabela, coluna, SQL ou `insurer_key`** — a tela fala "seguradora", "condições
gerais", "página".

**GATE D:** a tela abre com a base vazia (estado vazio honesto: *"nenhum plano publicado ainda"*), com uma
seguradora publicada, e com um item na fila; publicar grava `revisado_por`/`revisado_em`; trocar de corretora **não
muda nada** (é base global) e a tela diz isso em uma linha.

---

## 9. BLOCO E — A MEDIÇÃO

```
denominador   as 61 siglas da carteira viva (seguradora-coenti.json) — remedido no BLOCO 0 pela porta

HOJE (📊 13/09/2026)
  seguradoras com condição geral indexada .....  8 de 61   (6 quando a chave tem de casar)
  seguradoras com PLANO estruturado ...........  0 de 61
  serviços com limite, carência e fonte .......  0

💭 META POR ONDA — faixa, nunca promessa
  onda 1 (as 56 CGs de auto/resi/condomínio) ..  6 de 61, nos 3 ramos dos pilotos
  onda 2 (o elo SUSEP) ........................  a condição CERTA da apólice, não a atual
  onda 3 (as ausentes de maior carteira) ......  a fila sai da carteira remedida
```

🔴 **O relatório separa três contagens que é tentador juntar:** seguradoras com **CG na base** ≠ seguradoras com
**plano publicado** ≠ seguradoras que a corretora **usa**.

**`origem` no turno:** toda resposta da Skill grava, no registro que **já existe** (`tool_invocations`, via
`nodes.py:784,1057` → `gateway.py:294,323`): o **estado** (§6.2), a `insurer_key` canônica, o `plano_id`, o
`documento_id` e a `pagina`. 🔴 **Nenhum segundo registro** (CLAUDE.md §5) e 🔴 **nenhum argumento cru** — um
`tool_args` desse caminho carrega CPF; grava-se `{"documento": "presente"}`. ⚠️ Se o BLOCO 0 achar que
`tool_invocations` já guarda argumento cru hoje, é **P1 de segurança** e a drenagem vem antes da funcionalidade.

**GATE E:** a consulta de cobertura devolve os três números separados; um turno real do canário aparece em
`tool_invocations` com estado, seguradora, documento e página; o varredor de PII não acha nada nele.

---

## 10. Os guardas novos — **12, o teto de D-PILOTO-14** (+ 1 canônico)

🔴 Todos sobre o **MOTOR** e o **ACERVO real** (CLAUDE.md §9.4/§9.5). **Proibido teste que reimplementa a regra:** o
teste chama a tool e o banco, nunca um regex sobre a mesma tabela que o código lê.

| # | guarda | o que afirma | mutação que o deixa VERMELHO |
|---|---|---|---|
| **M-A1** | `test_a_seguradora_tem_uma_chave_so` | `chave_canonica("tokio")==chave_canonica("tokio_marine")`; desconhecida → `UNKNOWN` **listado**; nenhuma linha com chave fora do catálogo | chave nova aceita sem decisão |
| **M-A2** | `test_a_linha_sem_fonte_nao_entra` | o **banco** recusa `documento_id` nulo, `pagina` nula, `pagina=0`, `trecho_hash` de tamanho errado | CHECK `servico_tem_fonte` removido |
| **M-A3** | `test_a_pagina_existe_e_o_trecho_bate` | a `pagina` existe no documento e o `trecho_hash` bate com o texto **daquela** página; `nivel` único no produto; `limite_valor` sem unidade recusado | página inexistente aceita |
| **M-A4** ⚖️ | `test_a_base_de_planos_nao_tem_dono` — **canônico, não conta no teto** (CLAUDE.md §7) | nenhum `company_id`; varredor de PII = **0**; duas corretoras → mesma resposta | `ALTER TABLE … ADD COLUMN company_id` |
| **M-B1** | `test_nao_sabemos_ainda_nao_vira_nao` | sem linha publicada → `nao_sabemos_ainda` com frase própria; **par:** com linha → `nao_coberto` **com fonte** | estado desconhecido colapsando em "não cobre" |
| **M-B2** | `test_a_resposta_traz_documento_e_pagina` | sobre as **30 perguntas reais do acervo** (sem PII), pelo motor: todo estado ≠ `nao_sabemos_ainda` cita documento e página | origem removida do contrato de resposta |
| **M-B3** | `test_o_gancho_so_aparece_com_plano_superior` | **par de controle:** nível 1 com nível 2 na tabela → gancho; nível máximo → **sem** gancho | gancho com `nivel` máximo |
| **M-B4** | `test_o_plano_vem_da_apolice_nao_do_chute` | PDF sem nome de plano → `nao_sabemos_ainda`, nunca "o padrão da seguradora" | plano inferido só pela seguradora |
| **M-B5** | `test_o_guarda_dos_servicos_mudou_de_regra_nao_morreu` | com `assistencia_da_base` a resposta não pode omitir serviço da base; com o fallback, a regra dos 3 continua | guarda de `nodes.py:307` apagado |
| **M-C1** | `test_extracao_nao_publica_sem_gente` | o verificador só reprova; nada chega a `publicado` sem `revisado_por`+`revisado_em` | verificador promovendo a `publicado` |
| **M-C2** | `test_o_susep_da_apolice_encontra_a_condicao` | sobre um PDF real do acervo: o processo é extraído e casa. 🔴 **Controle:** com `susep` de volta no boilerplate → **ZERO** | `susep` de volta em `_BOILERPLATE_RE` |
| **M-C3** | `test_a_condicao_e_a_da_emissao_nao_a_de_hoje` | apólice antiga → a versão **vigente na emissão**; par de controle com duas versões do mesmo processo | busca por `now()` |
| **M-D1** | `test_a_cobertura_da_base_nao_mente_para_cima` | a régua conta seguradora × ramo com plano publicado; 40 linhas de um ramo só **não** inflam | contagem por linhas |

⚠️ **Não contam no teto** (e não servem para ampliá-lo): o VERIFY das migrations e o varredor de PII — são **gates de
bloco**. **Se o executor discordar, corta um da lista e escreve qual.**
🔴 **CLAUDE.md §9.3:** cada mutação roda em **cópia**, em subprocesso, produz **falha nova nomeada**, e a árvore é
restaurada por cópia. **Um guarda que não conseguiu ficar vermelho não é guarda.**

---

## 11. Migrations — APPLY / VERIFY / ROLLBACK escritos ANTES

🔴 **Ler `MIGRATIONS-AUTHORITY.md` inteiro antes da primeira linha de SQL.** 📊 9 versões aplicadas sem arquivo, 16
arquivos sem versão. Diretório canônico: `backend/supabase/migrations/`. Proibido sempre: `schema_completo.sql`,
`upgrade_v6.2.sql`, `storage_buckets.sql`. **São duas migrations, de naturezas diferentes. Elas não se juntam.**

### 11.1 `20260913_01_extra0015_assistance_plans.sql` — ADITIVA

```sql
-- APPLY (expand-first · idempotente) — não toca objeto existente
CREATE TABLE IF NOT EXISTS insurer_assistance_plans ( … );      -- §5.2
CREATE TABLE IF NOT EXISTS insurer_assistance_services ( … );   -- §5.2, com os 3 CHECKs
CREATE INDEX IF NOT EXISTS ix_iap_chave ON insurer_assistance_plans (insurer_key, ramo, produto, nivel);
CREATE INDEX IF NOT EXISTS ix_ias_servico ON insurer_assistance_services (plano_id, servico);
CREATE INDEX IF NOT EXISTS ix_ias_curadoria ON insurer_assistance_services (curadoria)
    WHERE curadoria <> 'publicado';

-- VERIFY (a saída vai COLADA no relatório)
SELECT table_name, count(*) FROM information_schema.columns WHERE table_schema='public'
   AND table_name IN ('insurer_assistance_plans','insurer_assistance_services') GROUP BY 1;
SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint
 WHERE conrelid='insurer_assistance_services'::regclass AND contype='c';
 -- esperado: servico_tem_fonte · servico_publicado_foi_revisado · limite_tem_unidade
SELECT count(*) FROM information_schema.columns WHERE table_schema='public'
   AND table_name IN ('insurer_assistance_plans','insurer_assistance_services')
   AND column_name IN ('company_id','user_id','owner_user_id');
 -- 🔴 esperado: 0. Maior que 0 reprova o gate (D-PILOTO-01, §3.3)
-- e as TRÊS inserções adversariais TÊM de falhar, com a mensagem colada:
--   documento_id NULL · pagina=0 · curadoria='publicado' com revisado_por NULL

-- ROLLBACK
DROP TABLE IF EXISTS insurer_assistance_services;   -- filha primeiro
DROP TABLE IF EXISTS insurer_assistance_plans;
-- ⚠️ o rollback APAGA as linhas curadas. Em ambiente com curadoria feita, exportar as duas tabelas
--    para o acervo antes. Trabalho humano perdido não volta com `git revert`.
```

### 11.2 🔴 `20260913_02_extra0015_doc_kind_manual.sql` — ALTERA UMA TRAVA DE TABELA VIVA

**É aqui que o piso CRÍTICO do §3.2 dispara**, por dois motivos somados: ela **altera um CHECK** de uma tabela com
**194 linhas em produção**, e 📊 `normative_documents` é **classe SEM_ARQUIVO** — o DDL só existe em
`docs/canon/sql/reconstruidas/20260725215808_spec057_h1_normative_corpus.sql`, marcado **PROIBIDO APLICAR**. **O
CHECK real tem de ser lido do catálogo do Postgres.**

**MANIFESTO obrigatório (MIGRATIONS-AUTHORITY §5), antes de rodar:** o `pg_get_constraintdef` atual colado, a lista
de valores em uso, e a declaração de que nenhuma linha existente perde validade.

```sql
-- APPLY (expand-first: o CHECK novo é SUPERCONJUNTO do antigo)
ALTER TABLE normative_documents DROP CONSTRAINT IF EXISTS normative_documents_doc_kind_check;
ALTER TABLE normative_documents ADD  CONSTRAINT normative_documents_doc_kind_check
  CHECK (doc_kind = ANY (ARRAY[
    'condicoes_gerais','condicoes_especiais','condicoes_particulares','manual_do_segurado',
    'nota_tecnica','circular_susep','tabela_coberturas','glossario','regulamento',
    'manual_de_assistencia']));          -- <- o único valor novo

-- VERIFY
SELECT pg_get_constraintdef(oid) FROM pg_constraint
 WHERE conname='normative_documents_doc_kind_check';     -- tem de conter manual_de_assistencia
SELECT doc_kind, count(*) FROM normative_documents GROUP BY 1 ORDER BY 2 DESC;
 -- 📊 esperado em 13/09: condicoes_gerais 184 · circular_susep 5 · manual_do_segurado 5
 -- ⚠️ não bateu? PARE: alguém mexeu, e o manifesto está desatualizado

-- ROLLBACK (só é seguro se NENHUMA linha usar o valor novo)
SELECT count(*) FROM normative_documents WHERE doc_kind='manual_de_assistencia';
 -- 🔴 > 0 → NÃO rodar: deixaria a tabela violando o próprio CHECK. Reclassificar antes
ALTER TABLE normative_documents DROP CONSTRAINT IF EXISTS normative_documents_doc_kind_check;
ALTER TABLE normative_documents ADD  CONSTRAINT normative_documents_doc_kind_check
  CHECK (doc_kind = ANY (ARRAY[ … os 9 valores lidos do catálogo no manifesto … ]));
```

**GATE G-MIG:** ① APPLY/VERIFY/ROLLBACK escritos **antes** de rodar qualquer um; ② APPLY rodado **duas vezes** →
mesmo resultado; ③ ROLLBACK exercitado em teste, **incluindo** a guarda de contagem; ④ as **três inserções
adversariais** falharam, com a mensagem colada; ⑤ `MANIFEST.md` atualizado e `normative_documents` registrada como
**NÃO RASTREADA** com o DDL real; ⑥ **nenhuma outra migration nesta SPEC** — se aparecer, **pare e registre**.

---

## 12. Canário controlado em produção, e a validação com as pilotos

**Antes:** confirmar o SHA implantado de cada serviço (não o `/health` — CLAUDE.md §9.1); confirmar que as exceções
de janela (`05f46a9`) contêm **só** TESTE-A/TESTE-B; confirmar que há **pelo menos uma** seguradora com plano
publicado e revisado — **canário com base vazia prova só o `nao_sabemos_ainda`**, a metade fácil.

| # | caso | onde | o que prova |
|---|---|---|---|
| 1 | "ele tem carro reserva?" numa apólice **com** plano publicado | chat `core` da Resulta, conta do Founder | estado certo **com documento e página** |
| 2 | a mesma pergunta numa seguradora **sem** plano na base | idem | `nao_sabemos_ainda` — e **não** "não cobre" |
| 3 | "qual o limite do guincho dele?" | idem | limite **com unidade** e fonte |
| 4 | apólice de nível 1 num produto que tem nível 2 | idem | o **gancho**, nomeando a atendente, **sem preço** |
| 5 | apólice no nível máximo | idem | o gancho **não** aparece (par de controle do 4) |
| 6 | "cobre granizo?" | WhatsApp, **TESTE-A** | linguagem de conversa, mesma verdade, origem em português |
| 7 | pergunta que **não** é de assistência | chat `core` | **linha de controle**: a base não é consultada |
| 8 | busca derrubada de propósito, em ambiente controlado | — | `fonte_indisponivel`, texto **diferente** do caso 2 |

🔴 **Os casos 5, 7 e 8 são os que dão direito à conclusão** (CLAUDE.md §9.2). Sem eles, "funcionou" pode ser um
`return "nao_sabemos_ainda"` no topo da função.

**Depois:** desligar apenas a habilitação temporária; conferir que não ficou agente amplamente ligado; preservar logs
**sem PII**; entregar evidências **por alias**.

**📋 O que só o Founder faz:** ① colar as perguntas dos casos 1–5 e 7 no chat da Resulta (ou autorizar a conta);
② mandar a mensagem do caso 6 do aparelho TESTE-A; ③ 🔴 **revisar e publicar as primeiras linhas da fila de
curadoria**, ou indicar quem revisa — **é a única dependência humana, e ela bloqueia o canário completo**; 💭 uma
seguradora, um ramo, ~10 linhas já destravam os casos 1, 3, 4 e 5; ④ o clique do EasyPanel, se houver.

**Validação com Saionara e Regina:** o executor prepara roteiro e telas, o Founder conduz, o executor **não as
contata**. Valida-se, em linguagem delas: a resposta diz de onde veio de um jeito que dá para conferir? *"ainda não
sabemos"* soa honesto ou soa falha? o gancho soa útil ou soa empurrão de venda? a fila é revisável por quem não é
técnico, olhando o trecho, sem abrir o PDF? 📊 A Saionara é a dona do caso de referência (a HDI cujo cadastro
escondia **R$ 125,94 de Assistências Essenciais, 41% do prêmio**) — pedir a ela **as perguntas, nunca os dados**.
Registrar: **"não testado" × "aprovado no canário técnico" × "validado pela atendente"**.

---

## 13. Entrega, implantação e rollback

```bash
# 🔴 ENTREGAR NÃO É COMMITAR. É EMPURRAR. (CLAUDE.md §2)
git rev-list --count origin/main..HEAD          # 0 = o trabalho está no ar
git merge-base --is-ancestor origin/main HEAD && git push origin HEAD:main
```

A saída real do `push` e o SHA remoto vão **colados** no relatório. Nunca `git add -A`, nunca force push, nunca
apagar `index.lock` por timeout. **Serviços:** `smith-api` e **`smith-web`** (a tela de §8 muda o front).
**Variáveis novas:** 💭 nenhuma prevista — se houver, entra com **nome e sem valor** no relatório e na caixa do
Founder. ⚠️ Mexeu em `app/`: `npm run test:rotas-montam` **e** `next start` + uma requisição real a `/api/…`.

| marco | evidência exigida |
|---|---|
| Implementado e gateado | commit, gates, mutações vermelhas, parecer da lente e do juiz fresco |
| Entregue na main | SHA remoto + saída do `push` |
| Implantado | serviço/imagem/SHA + `/health` + **uma requisição que executa código** |
| Validado no canário | os 8 casos, por alias, sem efeito fora do escopo |
| Validado pelas pilotos | feedback real, registrado pelo Founder |

**Rollback:** o código é reversível (a Skill é aditiva; `assistance_policy.py` continua inteiro e volta a ser o
caminho único). As migrations têm ROLLBACK próprio, com as duas ressalvas de §11.

---

## 14. Documentação e acompanhamento — um escritor por arquivo

1. `docs/canon/reports/SPEC-EXTRA-001.5-EXECUTION-REPORT.md` pelo template canônico, **abrindo com o EXECUTION
   CARD** (protocolo §0.1: relatório sem card = SPEC aberta), com a telemetria de 5 linhas.
2. `PENDENCIAS.md`, **por número, com veredito e prova**: **P-PILOTO-04** → 🔴 **PARCIAL** (a parte de conhecimento
   fecha; `ficha.faltando`, `_TITULOS` e o dossiê de sinistro ficam na 001.3 — fechar inteira seria fechar o que não
   se fez); **P-PILOTO-20** → CONTINUA ou FECHADA pela 001.1, conforme o BLOCO 0. **Entradas novas obrigatórias**,
   cada uma com **o que destrava · de quem é · o que custa esquecer**: (a) o corpus normativo **não carrega página**
   no pedaço indexado; (b) `insurer_key` inconsistente em 14 tabelas, sem constraint; (c) 3 valores de `doc_kind`
   sem escritor; (d) `documents` do repo diverge do banco vivo; (e) `normative_documents` e
   `normative_document_versions` são **classe SEM_ARQUIVO**.
3. `FOUNDER-DECISIONS.md`: registrar, datadas — a divergência de marcha de §0.5; "duas tabelas, não uma" (§5.2);
   "tool, não skill release" (§6).
4. `CHANGE-ADDENDA.md`: tudo além do texto desta SPEC, classificado.
5. `ESTADO-DAS-SPECS.md` e `INDICE-DE-SPECS.md`: a família EXTRA-001.x na fila; **não renumerar**.
6. Dossiê: fonte versionada `docs/canon/reports/dossies/dossies-autobrokers.html`, página **`p-extra0015`** na
   convenção existente, com item de navegação e linha na home. 🔴 **Ler o HTML publicado inteiro antes de republicar
   com `url`** (https://claude.ai/code/artifact/afe1510d-f31c-4d13-9441-aa920ad2b868). Sem ferramenta ou acesso:
   manter a fonte atualizada e declarar **"publicação pendente"** com o passo exato. **Nunca fingir.**

---

## 15. O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS

> Três referências, todas **fontes primárias**, reabertas em **13/09/2026** pelo redator. O pesquisador do executor
> reabre cada uma e **registra a data dele** (protocolo §7.3).

**① PROV-O: The PROV Ontology — W3C Recommendation, 30/04/2013** · https://www.w3.org/TR/prov-o/
**Faz:** proveniência com **Entity**, **Activity**, **Agent** e as relações `wasDerivedFrom`, `wasAttributedTo`
(*"the ascribing of an entity to an agent"*) e `wasQuotedFrom`.
**MODELAMOS (um ponto):** **`wasQuotedFrom` + `wasAttributedTo` na mesma linha** — de **onde** foi citada
(`documento_id` + `pagina` + `trecho_hash`) **e por quem** foi afirmada (`revisado_por` + `revisado_em`). 🔴 As duas
juntas distinguem *"a base diz"* de *"alguém revisou e publicou"*, e é por isso que o CHECK
`servico_publicado_foi_revisado` existe.
**REJEITAMOS:** RDF, OWL, a ontologia inteira, um grafo de proveniência — modela-se **a ideia**, em quatro colunas
relacionais. E rejeitamos guardar proveniência em **log**: proveniência é **do dado**.
**O juiz inspeciona:** pega 3 linhas ao acaso da base publicada e pergunta, para cada uma: de que documento e página
veio, quem publicou, em que data. Uma sem resposta reprova a amostra (protocolo §0.4).

**② Citations — documentação oficial da API da Anthropic** ·
https://platform.claude.com/docs/en/docs/build-with-claude/citations (301 de `docs.anthropic.com`; **registrar o
redirect**, não trocar a URL em silêncio).
**Faz:** *"Citations return the exact passages that support each claim."* Três formatos de localização:
**`page_location`** com `start_page_number` (*"1-indexed"*) para PDF, **`char_location`** para texto e
**`content_block_location`** para conteúdo customizado; cada bloco traz `cited_text`.
**MODELAMOS (um ponto):** a frase que vira teste — *"citations are guaranteed to contain valid pointers to the
provided documents"*. **Um ponteiro válido, não uma citação plausível.** É o guarda **M-A3**: a `pagina` tem de
**existir** e o `trecho_hash` tem de **bater** com o texto daquela página. E `page_location`/`start_page_number` é o
que nos convence a guardar **página**, não offset de caractere — página é o que a pessoa que revisa consegue conferir.
**REJEITAMOS:** trocar o extrator por uma chamada com `citations: true` e publicar o que voltar. 🔴 A garantia é de
**ponteiro válido**, não de **afirmação correta**: a página existe, o trecho é literal, e a leitura de que aquilo
significa "carro reserva por 7 dias no Completo" continua sendo julgamento. Por isso §7.1 tem três papéis e a pessoa
é o terceiro.
**O juiz inspeciona:** abre a seção de formatos, confere `start_page_number` e `cited_text`, e roda **M-A3** pedindo
uma linha cuja página **não** exista no documento.

**③ Enabling Large Language Models to Generate Text with Citations — Gao, Yen, Yu, Chen · EMNLP 2023** ·
https://arxiv.org/abs/2305.14627
**Faz:** propõe o ALCE, com *"automatic metrics along three dimensions — fluency, correctness, and citation
quality"*. 📊 *"on the ELI5 dataset, even the best models lack complete citation support 50% of the time"*.
**MODELAMOS (um ponto):** **qualidade de citação é dimensão separada de correção, e se mede em separado.** Uma
resposta pode estar certa e mal citada, ou bem citada e errada. §9 mede as duas como **contagens diferentes**, e
**M-B2** exige as duas nas 30 perguntas reais.
**REJEITAMOS:** deixar o modelo citar sozinho a partir do contexto recuperado — o cenário em que o paper mede metade
de falha. 🔴 Aqui **a citação não é gerada: é lida da tabela**, posta por um extrator, conferida por máquina e
publicada por gente. O modelo redige a frase; **a fonte não passa pela redação dele.** E rejeitamos usar as métricas
do ALCE como gate: o gate é o acervo real.
**O juiz inspeciona:** abre o abstract, confere as três dimensões e o número do ELI5, e pergunta qual das duas
contagens de §9 corresponde a cada dimensão.

⛔ **Referência externa nunca vira autoridade** (protocolo §7.3): Smith, Work OS, Tool Gateway, Skill Registry e
Artifact Hub continuam únicos. Modela-se o **padrão**.

---

## 16. A fila depois desta entrega — contexto, não autorização

```
001.0 → 001.6-P0 → 001.1 → 001.2 → 001.3 ∥ 001.4 → 001.6 → 001.7 → 001.10 ∥ ★ 001.5 (esta) → 001.8 → 001.9
```

**O que a 001.5 deixa pronto:** para a **001.3**, o dossiê ao grupo passa a dizer *o que o plano dele cobre*, com
fonte; para a **001.4**, o corredor sabe antes de discar se o serviço está no plano, e para de acionar o que não é
coberto; para a **EXTRA-003/004**, o catálogo por nível é metade de uma cotação de renovação; para a **SPEC-101**, a
base pendura na chave nossa e vale para qualquer adaptador.

---

## 17. Definição final de conclusão — lista fechada, verificável

1. A **chave canônica** existe num módulo único, `tokio` e `tokio_marine` resolvem para a mesma, e o que não casa sai
   **`UNKNOWN` listado**.
2. As duas tabelas existem, com os **três CHECKs**, e as **três inserções adversariais** falharam com a mensagem
   colada. 📊 **Zero** colunas `company_id`/`user_id`; varredor de PII = **0**; duas corretoras, mesma resposta.
3. A Skill responde nos **cinco estados**, **`nao_sabemos_ainda` nunca vira "não cobre"**, e `fonte_indisponivel` tem
   texto próprio e outra coluna na tela.
4. **30 perguntas reais do acervo** (sem PII) rodadas **pelo motor** → todo estado ≠ `nao_sabemos_ainda` cita
   **documento e página**.
5. As **linhas de controle** funcionam: pergunta não-assistência não consulta a base; nível máximo não mostra gancho;
   `susep` de volta no boilerplate → **ZERO** casamentos.
6. `assistance_policy.py` continua existindo **como fallback marcado**, e o guarda de `nodes.py:307` **mudou de regra
   sem morrer**.
7. Onda 1 produziu linhas publicadas para ≥ 1 seguradora em ≥ 1 ramo dos pilotos, **todas revisadas por gente**;
   onda 2 casou o processo SUSEP com a condição **vigente na emissão**; onda 3 teve `manual_de_assistencia` aceito
   depois da migration e **recusado antes**.
8. `doc_kind` **filtra**, com índice criado **antes** da ingestão nova; a procedência **volta como campo**.
9. A tela mostra cobertura por **seguradora × ramo** (não por linhas) e a fila com trecho e página.
10. As **duas migrations** aplicadas, VERIFY colado, ROLLBACK exercitado, **manifesto** de §11.2 escrito, e
    `MANIFEST.md` atualizado com `normative_documents` como **NÃO RASTREADA**.
11. Os **12 guardas** existem e cada um ficou **vermelho** na sua mutação, em cópia, em subprocesso, com falha nova
    nomeada; o canônico **M-A4** também.
12. Canário: os **8 casos** rodados, só com TESTE-A/TESTE-B e a conta do Founder, evidências por alias.
13. `git push` feito, saída colada, SHA remoto conferido, serviços implantados e **uma requisição que executa
    código** respondida.
14. Relatório com **EXECUTION CARD**, a **divergência de marcha de §0.5 resolvida por escrito**,
    FATO/INFERÊNCIA/RECOMENDAÇÃO separados, 📊/💭 em todo número, pendências drenadas **por número**, dossiê
    publicado ou **publicação pendente** declarada com o passo exato.
15. **Declaração explícita de que nenhum motor paralelo foi criado** — nominalmente: nenhum segundo pipeline de
    ingestão, nenhuma segunda coleção de Qdrant, nenhuma segunda fila de curadoria, nenhum segundo catálogo de
    seguradoras, nenhum segundo registro de chamada de ferramenta, nenhuma segunda porta de apólice.

🔴 **E a pergunta que o resumo ao Founder responde em linguagem simples:** *quando eu perguntar se o meu cliente tem
carro reserva, eu recebo sim ou não — e consigo ver em que página de qual documento isso está escrito?*
