---
> **Status:** canônico — registro append-only
> **Criado em:** 25/07/2026
> **Função:** registrar toda mudança executada além do texto literal de uma SPEC, impedindo alteração silenciosa de escopo
---

# Change Addenda — mudanças além do texto literal das SPECs

## 1. Por que este documento existe

As SPECs 052–062 são detalhadas, mas nenhuma especificação sobrevive intacta ao contato com o código real. O executor **vai** encontrar situações não previstas.

O risco não é a mudança. É a mudança **silenciosa** — aquela que ninguém registrou, ninguém aprovou e que reaparece seis semanas depois como uma divergência inexplicável entre documentação e produção.

```text
Mudança registrada e classificada  → governança
Mudança executada em silêncio      → deriva
```

---

## 2. Regras

1. Este arquivo é **append-only**. Entradas existentes não são editadas nem removidas.
2. Toda alteração além do literal da SPEC recebe entrada aqui **antes ou junto** com o commit que a implementa.
3. Toda entrada é classificada como **BLOCKER**, **ESSENCIAL**, **VALIOSA** ou **FUTURA**.
4. Entradas **BLOCKER** e **ESSENCIAL** podem ser executadas pelo executor dentro da SPEC corrente, desde que registradas.
5. Entradas **VALIOSA** e **FUTURA** são **propostas**. Não são executadas sem decisão em [`FOUNDER-DECISIONS.md`](FOUNDER-DECISIONS.md).
6. **Nenhuma entrada pode reduzir escopo.** Redução exige decisão explícita do Founder — ver **D5**.
7. Mudança que altere arquitetura, sequência de SPECs, risco material ou dinheiro **também** vai para `FOUNDER-DECISIONS.md`.
8. Correção de bug dentro do escopo da SPEC **não** vem para cá — vai para o relatório final da SPEC.

---

## 3. Classificação

### BLOCKER
Sem isso, a execução causa erro grave, insegurança, perda de dados, duplicidade estrutural ou inviabilidade técnica.
→ Executar dentro da SPEC corrente. Registrar aqui. Notificar no relatório final.

### ESSENCIAL
Melhora materialmente qualidade, robustez, segurança, experiência ou resultado, e o custo de deixar para depois é maior que o de fazer agora.
→ Executar dentro da SPEC corrente. Registrar aqui.

### VALIOSA
Melhoria real, mas com encaixe natural em uma SPEC posterior ou custo desproporcional agora.
→ **Não executar.** Registrar como proposta.

### FUTURA
Boa ideia que não deve atrasar o lançamento.
→ **Não executar.** Registrar como proposta.

---

## 4. Formato obrigatório de entrada

```markdown
## CA-nnn — <título curto>

**Data:** DD/MM/AAAA · **SPEC:** SPEC-0NN Bloco X · **Classe:** BLOCKER | ESSENCIAL | VALIOSA | FUTURA
**Estado:** EXECUTADA | PROPOSTA | REJEITADA | SUPERSEDED BY CA-nnn

### Problema
O que estava errado ou faltando.

### Evidência
Arquivo:linha, consulta ao banco, saída de teste ou commit. Fato, não impressão.

### Consequência de não fazer
Concreta e específica.

### Mudança
O que foi (ou seria) feito, exatamente.

### Custo e risco
Esforço relativo e risco introduzido.

### Autorização
Executor dentro da SPEC | decisão D-nn do Founder | aguardando decisão.
```

---

## 5. Índice

| ID | Título | SPEC | Classe | Estado | Data |
|---|---|---|---|---|---|
| CA-001 | Cruzamento factual de migrations e checksums iniciais | 054 | ESSENCIAL | EXECUTADA | 25/07/2026 |
| CA-002 | Adiar PPTX e DOCX na SPEC-057 | 057 | VALIOSA | **PROPOSTA — não executar** | 25/07/2026 |
| CA-003 | Adiar SEO/AEO e Business Discovery na SPEC-060 | 060 | VALIOSA | **PROPOSTA — não executar** | 25/07/2026 |
| CA-004 | Simplificar Briefing por cargo na SPEC-059 | 059 | VALIOSA | **PROPOSTA — não executar** | 25/07/2026 |
| CA-005 | Fixar imagens e credenciais do docker-compose | 054 | VALIOSA | PROPOSTA | 25/07/2026 |
| CA-006 | Consolidar os 60 runners em um pack único | 054 | ESSENCIAL | PROPOSTA | 25/07/2026 |
| CA-007 | Substituir testes de inspeção de fonte por testes de comportamento | 054 | ESSENCIAL | PROPOSTA | 25/07/2026 |
| CA-008 | Brand Identity Fabric como pré-requisito do Artifact Hub | 057 | BLOCKER | EXECUTADA | 25/07/2026 |
| CA-009 | Context Assembly 2.0 e a regra de cobertura | 052 | BLOCKER | EXECUTADA | 25/07/2026 |
| CA-010 | As nove tools da §27.3 chegam ao chat agrupadas em quatro | 059 | ESSENCIAL | EXECUTADA | 26/07/2026 |
| CA-011 | O gatilho da memória não pode viver dentro do turno | 059 | BLOCKER | EXECUTADA | 26/07/2026 |
| CA-012 | Dois falsos positivos que só o dado real revelou | 059 | BLOCKER | EXECUTADA | 26/07/2026 |
| CA-013 | Menu do Admin: rótulo duplicado e página órfã | 059 | ESSENCIAL | EXECUTADA | 26/07/2026 |
| CA-014 | O Admin foi desenhado para 5 corretoras, não para 1000 | 061 | ESSENCIAL | REGISTRADA — a corrigir na 061 | 26/07/2026 |
| CA-015 | "Origem interna não vira sinal" é um conceito, não uma correção pontual | 060 | ESSENCIAL | EXECUTADA | 27/07/2026 |
| CA-016 | O catálogo de pesquisa já existia; adotá-lo em vez de criar o segundo | 060 | BLOCKER (evitado) | EXECUTADA | 27/07/2026 |
| CA-017 | "O número está errado" é informação sobre o detector, e ninguém via | 060 | ESSENCIAL | EXECUTADA | 27/07/2026 |
| CA-018 | Seis peças de pesquisa, porque o dossiê não serve para tudo | 060 | VALIOSA | EXECUTADA | 27/07/2026 |
| CA-019 | O Auxiliar Radar não podia ser um card que não faz nada | 060 | ESSENCIAL | EXECUTADA | 27/07/2026 |
| CA-020 | O produto trabalhava sem deixar rastro | Bloco 0 da 061 | BLOCKER | EXECUTADA | 27/07/2026 |
| CA-021 | A view do cutover era lida por qualquer visitante | Bloco 0 da 061 | BLOCKER | EXECUTADA | 27/07/2026 |
| CA-022 | Firecrawl era o único degrau acima da leitura direta | Bloco 0 da 061 | ESSENCIAL | EXECUTADA (D18: proposta) | 27/07/2026 |
| CA-023 | Quatro índices para o Cockpit que ainda não existe | Bloco 0 da 061 | VALIOSA | EXECUTADA | 27/07/2026 |

> **Sobre CA-013 e CA-014.** Nasceram como CA-010 e CA-011, números que já
> pertenciam a registros da SPEC-059 citados no código e no relatório daquela
> SPEC. Foram renumerados aqui: dois registros com o mesmo ID tornam a
> referência ambígua, que é o mesmo defeito de classe que o CA-013 descreve.
>
> A regra append-only (§2.1) protege o **conteúdo** de um registro, não um ID
> colidido — manter a colisão preservaria a forma e destruiria a função.

---

## CA-001 — Cruzamento factual de migrations e checksums iniciais

**Data:** 25/07/2026 · **SPEC:** SPEC-054 (preparatório, Fase 0) · **Classe:** ESSENCIAL
**Estado:** EXECUTADA

### Problema
A SPEC-054 §8.1 exige baseline reproduzível, mas nem a SPEC nem a auditoria de 24/07 traziam o cruzamento **arquivo × versão aplicada × checksum**. Sem isso, o executor do Bloco B decide no escuro quais arquivos são pendentes e quais já estão em produção.

### Evidência
Cruzamento read-only entre `main` @ `3c8c752` e `supabase_migrations.schema_migrations` (projeto `dcajcvlzcjbmyapmklil`): 21 versões rastreadas, 28 arquivos no repositório, **12** correspondências, **9** versões sem arquivo, **16** arquivos sem versão.

### Consequência de não fazer
Treze arquivos da classe `NÃO RASTREADA` (rotinas, portais, corredores, capability seeds) parecem pendentes e **não são** — as estruturas já existem em produção. Aplicá-los repetiria DDL, sobrescreveria policies e alteraria defaults.

### Mudança
Produzido [`MIGRATIONS-AUTHORITY.md`](MIGRATIONS-AUTHORITY.md) com a classificação completa e o sha256 inicial de cada arquivo, como baseline de integridade do futuro `MANIFEST.md`.

### Custo e risco
Custo baixo — documental. Risco zero: nenhum arquivo foi movido, aplicado ou alterado.

### Autorização
Decisão **D2** do Founder.

---

## CA-002 — Adiar PPTX e DOCX na SPEC-057

**Data:** 25/07/2026 · **SPEC:** SPEC-057 · **Classe:** VALIOSA
**Estado:** **PROPOSTA — NÃO EXECUTAR**

### Problema
A SPEC-057 exige oito formatos de saída. PPTX e DOCX são os de maior custo de implementação e menor contribuição para o efeito "wow" inicial.

### Evidência
SPEC-057 §7.6 e §7.7 · §16.5 e §16.6.

### Consequência de não fazer
Nenhuma imediata. É otimização de cronograma, não correção de defeito.

### Mudança proposta
Entregar web, PDF, XLSX, CSV, gráficos e Evidence Pack no lançamento; PPTX e DOCX logo após.

### Custo e risco
Reduz esforço da SPEC-057. Risco: o Founder pode considerar apresentação executiva parte do wow.

### Autorização
**Rejeitada como execução pela decisão D5.** Permanece registrada. Só muda por nova decisão do Founder.

---

## CA-003 — Adiar SEO/AEO e Business Discovery na SPEC-060

**Data:** 25/07/2026 · **SPEC:** SPEC-060 · **Classe:** VALIOSA
**Estado:** **PROPOSTA — NÃO EXECUTAR**

### Problema
A SPEC-060 inclui auditoria de SEO/AEO (§21) e descoberta de empresas (§19), enquanto o próprio Founder já declarou que Growth e prospecção ficam para uma fase posterior.

### Evidência
SPEC-060 §19 e §21 · SPEC-053 §23 (fora do primeiro ciclo).

### Consequência de não fazer
Nenhuma imediata.

### Mudança proposta
Priorizar `quick`, `verified`, `deep`, `claim_check` e `monitor`; entregar `site_audit` e `business_discovery` em seguida.

### Custo e risco
Reduz esforço. Risco: o Radar de Mercado depende de `monitor`, que **permanece no escopo**.

### Autorização
**Rejeitada como execução pela decisão D5.**

---

## CA-004 — Simplificar Briefing por cargo na SPEC-059

**Data:** 25/07/2026 · **SPEC:** SPEC-059 · **Classe:** VALIOSA
**Estado:** **PROPOSTA — NÃO EXECUTAR**

### Problema
A SPEC-059 §16.6 prevê Briefing personalizado por cargo. Com 5 empresas e poucos usuários, a segmentação por cargo tem pouco sinal para calibrar.

### Evidência
SPEC-059 §16.5 e §16.6 · banco vivo: 5 companies.

### Consequência de não fazer
Nenhuma imediata.

### Mudança proposta
Lançar com Briefing operacional diário + executivo semanal; adicionar segmentação por cargo quando houver volume.

### Custo e risco
Baixo dos dois lados.

### Autorização
**Rejeitada como execução pela decisão D5.**

---

## CA-005 — Fixar imagens e credenciais do docker-compose

**Data:** 25/07/2026 · **SPEC:** SPEC-054 · **Classe:** VALIOSA
**Estado:** PROPOSTA — depende de **P1**

### Problema
`backend/docker-compose.yml` usa `minio/minio:latest` e credenciais `minioadmin/minioadmin123`.

### Evidência
[`backend/docker-compose.yml`](../../backend/docker-compose.yml) · SPEC-053 §25.3 proíbe `latest` em imagem crítica.

### Consequência de não fazer
Se o compose espelhar produção: mudança silenciosa de versão do MinIO e credenciais default expostas. Se for apenas dev local: nenhuma.

### Mudança proposta
Fixar tag do MinIO e mover credenciais para `.env` não versionado.

### Custo e risco
Custo mínimo. **Classificação sobe para ESSENCIAL** se o Founder confirmar que o compose espelha produção — ver P1 secundária 2.

### Autorização
Aguardando resposta de **P1**.

---

## CA-006 — Consolidar os 60 runners em um pack único

**Data:** 25/07/2026 · **SPEC:** SPEC-054 · **Classe:** ESSENCIAL
**Estado:** PROPOSTA — executar no Bloco C da SPEC-054

### Problema
`backend/tests/` contém ~60 arquivos executados isoladamente, sem gate único. Cada SPEC de 054 a 062 referencia um "Broker Outcome Regression Pack" que **não existe** como artefato executável.

### Evidência
`backend/tests/` — 60 arquivos · SPEC-062 §2.1 confirma: *"muitos testes eram runners independentes, e não uma única suíte com gates de release"*.

### Consequência de não fazer
Cada SPEC declara gate verde sem um critério comum. Regressão entre SPECs passa despercebida até a 062.

### Mudança proposta
Criar o pack executável por um comando na SPEC-054 Bloco C, preservando todos os arquivos atuais como casos. Cada SPEC posterior adiciona seus casos ao mesmo pack.

### Custo e risco
Custo médio, uma vez. Risco de não fazer: alto e cumulativo.

### Autorização
Executor dentro da SPEC-054 Bloco C, registrando aqui a mudança de estado para EXECUTADA.

---

## CA-007 — Substituir testes de inspeção de fonte por testes de comportamento

**Data:** 25/07/2026 · **SPEC:** SPEC-054 · **Classe:** ESSENCIAL
**Estado:** PROPOSTA — executar no Bloco B da SPEC-054

### Problema
Testes como `test_spec048_isolamento_corretoras.py` verificam a **presença de um guard no código-fonte**, não seu comportamento em runtime. Passam verde mesmo com o guard quebrado.

### Evidência
[`backend/tests/test_spec048_isolamento_corretoras.py`](../../backend/tests/test_spec048_isolamento_corretoras.py) · auditoria SPEC-054 §12.1.

### Consequência de não fazer
Um gate de isolamento multi-tenant verde que não prova isolamento. É o pior tipo de falso positivo — dá confiança sem dar segurança.

### Mudança proposta
Implementar a suíte real exigida pela SPEC-054 §8.8, executando `anon`, `authenticated` tenant A, `authenticated` tenant B, `service_role` e usuário multiempresa contra o banco. Manter os testes de inspeção como smoke barato, **nunca** como prova de segurança.

### Custo e risco
Custo médio. Risco de não fazer: crítico — é pré-condição para o Gate 2.

### Autorização
Executor dentro da SPEC-054 Bloco B, registrando aqui a mudança de estado para EXECUTADA.

---

## CA-008 — Brand Identity Fabric como pré-requisito do Artifact Hub

**Data:** 25/07/2026 · **Estado:** EXECUTADA (Bloco A) · **SPEC:** 057 · **Origem:** D15

### Lacuna encontrada

A SPEC-057 exige que toda peça saia com a identidade da corretora, mas **nenhum
objeto do sistema guardava identidade de marca**. `companies` tem CNPJ, endereço
e contato — não tem site, logo, cor nem tipografia. O requisito era inexequível
como escrito.

### Mudança

Cinco tabelas novas antes do Artifact Hub: `brand_profiles`, `brand_assets`,
`brand_sources`, `brand_field_provenance`, `brand_profile_versions`. Mais o motor
de cor em `app/services/brand/`.

### Decisão de engenharia que merece registro

**O logo manda na cor, o CSS não.** Medido no primeiro site real testado: o CSS
da Resulta devolve `#f78da7`, `#cf2e2e`, `#ff6900`, `#fcb900` — a paleta padrão
do editor do WordPress, sem uma única cor da marca. O logo devolve `#1D5579`
(94,4% da tinta) e `#EE7501` (5,6%). Ler cor do CSS daria a **toda** corretora
em WordPress a mesma identidade rosa-e-âmbar.

`brand_field_provenance` guarda de onde veio cada campo e com que confiança. Sem
isso, captura automática em material que vai ao cliente final é passivo, não
ativo — o corretor precisa poder conferir e discordar.

### Custo e risco
Custo alto (bloco inteiro). Risco de não fazer: a promessa central da SPEC-057
sairia falsa — peça "personalizada" com a cor da AutoBrokers.

### Autorização
D15.

---

## CA-009 — Context Assembly 2.0 e a regra de cobertura

**Data:** 25/07/2026 · **Estado:** EXECUTADA (shadow) · **SPEC:** 052 Lote 3

### O que existia

O roteador de intenção do sistema era literalmente:

```python
def should_prefetch_rag(user_message):
    return len(user_message) > 25
```

"Bom dia, tudo bem?" (20 chars) não buscava nada. "Me manda o telefone de
vocês" (28 chars) disparava recuperação completa. Memória do usuário e da
corretora eram carregadas em **toda** mensagem.

### Por que virou urgente agora

A SPEC-052 §6.4 diz: *"O RAG global nunca confirma sozinho que uma apólice
específica possui cobertura."* Isso era teórico enquanto o conhecimento global
tinha só documentos de estrutura.

No momento em que **35 condições gerais** entraram no corpus (Bloco H da
SPEC-057), a regra deixou de ser teórica. Sem ela, o agente lê "cobre vidro" na
condição geral da Porto e responde que a apólice do cliente cobre vidro —
quando a apólice pode ter sido emitida sob outra versão, com cláusula excluída
ou franquia diferente. O corretor repete ao cliente; a corretora responde.

### O que entrou

`app/agents/context_assembly.py`: Intent Router léxico, Context Planner,
Evidence Builder com precedência da §6.4, deduplicação por autoridade e
orçamento com teto por fonte.

Quando a pergunta é sobre cobertura de apólice **concreta** e a evidência é
normativa, o pacote carrega instrução explícita de **não confirmar** — e a
vigência da condição viaja junto do texto.

### Modo

`CONTEXT_ASSEMBLY_MODE` = `off` | `shadow` (padrão) | `on`. Em shadow o plano é
calculado e registrado, mas nada é pulado. Classificação errada que decida "não
precisa buscar" produz resposta pior sem rastro óbvio — o corretor só vê o
agente ficar burro. Observar antes de interferir.

### Autorização
SPEC-052 Lote 3, dentro do escopo já aprovado.

---

## CA-010 — As nove tools da §27.3 chegam ao chat agrupadas em quatro

**Data:** 26/07/2026 · **Estado:** EXECUTADA · **SPEC:** 059 §27.3
**Classificação:** ESSENCIAL

### O conflito canônico

A SPEC-059 §27.3 nomeia **nove** tools do Core. A SPEC-053 §13.1 fixa um teto
de **12 ferramentas por execução**, e o Tool Gateway o implementa
(`MAX_TOOLS_POR_EXECUCAO`). O Core hoje já carrega perto do teto: base de
conhecimento, busca, handoff, CSV, HTTP router, MCPs, rotinas, operações,
relatório, Factory.

Anexar nove ferramentas novas estouraria o teto e — pior — degradaria a escolha
do modelo em **toda** conversa, inclusive nas que nada têm a ver com briefing.
O corte por prioridade do Gateway derrubaria ferramentas silenciosamente.

### O que foi feito

As nove operações continuam existindo e estão **todas** disponíveis pelas APIs
de §27.1. No chat elas chegam agrupadas em quatro ferramentas registradas no
Registry, com release publicada e capability própria:

| Tool registrada | Operações de §27.3 que atende |
|---|---|
| `intelligence.briefing` | `get_briefing`, `generate_briefing` |
| `intelligence.findings` | `list_findings`, `explain_finding`, `list_recommendations` |
| `intelligence.respond` | `respond_recommendation`, `execute_recommendation`, `report_feedback` |
| `intelligence.preferences` | `update_preferences` |

Isto **não é redução de escopo** (D5): nenhuma operação foi removida, adiada ou
tornada indisponível. É consolidação de superfície, e o motivo é proteger a
qualidade da resposta que o corretor recebe.

### O que seria pior

Registrar as nove chaves no Registry com só quatro implementações. Isso criaria
cinco entradas governáveis que não executam — exatamente o "botão que promete e
não cumpre" que a §14.2 existe para impedir.

### Autorização
Dentro do escopo da SPEC-059; conflito entre duas SPECs canônicas resolvido em
favor da que protege o resultado do corretor. Registrado para revisão do Founder.

---

## CA-011 — O gatilho da memória não pode viver dentro do turno

**Data:** 26/07/2026 · **Estado:** EXECUTADA · **SPEC:** 052 Lote 4 / 059 Bloco A
**Classificação:** BLOCKER

### O que a auditoria da SPEC-054 encontrou, e o que faltou

A SPEC-054 Bloco B diagnosticou a memória zerada e corrigiu `should_summarize`:
o modo `session_end` era inalcançável porque o grafo sempre passa
`session_ended=False`. A correção adicionou um caminho por inatividade dentro
do próprio `session_end`.

**A correção ficou inerte, e dá para provar em uma linha.**
`backend/app/agents/graph.py:1052` chama o gatilho com:

```python
last_message_at=datetime.now()
```

No instante do turno, a inatividade é sempre **zero**. A condição "passou do
timeout" nunca é satisfeita durante a conversa — por construção. As seis linhas
de `memory_settings` estão todas em `session_end`.

### Evidência (FATO, medido em 26/07/2026)

```text
conversations       144        user_memories        0
                               session_summaries    0
```

Dois meses depois do diagnóstico, ainda zero.

### A conclusão que importa

Ninguém sabe, no meio de uma conversa, que ela acabou. Quem sabe é o relógio,
depois. **O gatilho não pertence ao turno** — pertence a uma varredura.

### O que entrou

`backend/app/services/memory_fabric.py`: fecha sessões inativas e chama o
`MemoryService` que já existe, com `session_ended=True`. Roda no laço de
manutenção do Smith Worker — o mesmo que já faz a reconferência do corpus.
Nenhum agendador novo (CLAUDE.md §5).

Junto vieram as duas peças que faltavam ao Lote 4: `company_memories` (memória
da corretora, não da pessoa) e `knowledge_candidates` (o objeto comum onde todas
as fontes depositam aprendizado antes da curadoria).

E um diagnóstico consultável em `/api/admin/intelligence/memory-health`: o
defeito ficou dois meses invisível porque **nenhuma tela mostrava a contagem**.

### Autorização
D1 (Lote 4 da SPEC-052, executado na SPEC-059 Bloco A).

---

## CA-012 — Dois falsos positivos que só o dado real revelou

**Data:** 26/07/2026 · **Estado:** EXECUTADA · **SPEC:** 059 §23.4 e §23.6
**Classificação:** BLOCKER

### Por que isto está registrado

Os dois defeitos passariam em qualquer teste sintético. Eles só apareceram ao
rodar as condições dos detectores contra o banco vivo, antes de ligar. Se
tivessem chegado à produção, o **primeiro briefing da Resulta** — a primeira
impressão do produto proativo — abriria com vinte avisos falsos.

### Achado 1 — o chat do corretor não é fila de atendimento

O detector `qualidade.atendimento_parado` encontrou **20 conversas paradas** na
Resulta. Dezoito eram `channel='web'`, `status='active'`: as conversas do
**próprio corretor** com o AutoBrokers no dashboard, que ficam `active` para
sempre porque ninguém "encerra" um chat.

A §23.6 pedia definição de parado "por estado **e canal**". Só o estado estava
implementado. Com o canal, a Resulta cai de 20 para 2 — as duas conversas de
WhatsApp genuinamente paradas.

Exceção mantida: `HUMAN_REQUESTED` entra em qualquer canal. Alguém pediu uma
pessoa e ninguém veio é atendimento parado, mesmo no web.

### Achado 2 — canal desligado não é canal quebrado

O detector `conexoes.conexao_degradada` acusava **2 canais ruins** na Resulta.
Eram integrações antigas com `is_active=false` e estado `close`/`retired` —
canais que alguém aposentou de propósito. Alertar sobre elas é acusar a
corretora de um problema que é decisão dela.

Ao mesmo tempo, `close` **não estava** na lista de estados ruins — e há um canal
de atendimento `is_active=true` com `channel_status='close'`. O detector estava
simultaneamente inventando dois problemas e perdendo o único real.

Correção: só alerta canal **ligado** em estado ruim; `close`/`closed` entram na
lista; `connecting` e outros transitórios ficam fora.

### Resultado

Resulta passa de 22 avisos (20 falsos + 2 verdadeiros mal classificados) para
**3 sinais verdadeiros**: canal de atendimento caído, 2 conversas de WhatsApp
paradas, 1 trabalho concluído.

Os dois casos viraram teste de regressão (`[19]` em
`test_spec059_intelligence.py`) para não voltarem.

### Autorização
Correção de defeito dentro do escopo da SPEC-059. Nenhuma decisão do Founder
necessária.

---

## CA-013 — Menu do Admin: rótulo duplicado e página órfã

> **Renumerado.** Este registro nasceu como CA-010, número que já pertencia ao
> agrupamento de tools da SPEC-059. Dois registros com o mesmo ID tornam a
> referência ambígua — o mesmo defeito de classe que este próprio registro
> descreve, aplicado a uma numeração. Os IDs 010, 011 e 012 permanecem com os
> registros originais, que já são citados no código e no relatório da SPEC-059.

**Data:** 26/07/2026 · **Estado:** EXECUTADA · **SPEC:** 059 (correção pós-merge)

### O que o Founder encontrou

Ele seguiu a instrução "abra /admin/inteligencia" e **não achou**. Clicou em
"Inteligência" no menu e caiu em Rotinas prontas / Blueprint Center / Prompt
efetivo — não na Central de sinais.

### Três defeitos, um deles anterior à SPEC-059

1. **Rótulo duplicado.** A SPEC-059 criou um item "Inteligência"
   (`/admin/inteligencia`) sem notar que já existia outro com o mesmo rótulo.
   Menu com dois itens de nome idêntico não é confuso — é **ambíguo**: não há
   como o usuário saber qual abrir, e ele acerta por sorte.

2. **Página órfã.** `app/admin/inteligencia/page.tsx` tem 589 linhas e existia
   sem nenhum link chegando até ela pelo Admin. A SPEC-059 lembrou de pôr o
   Briefing no menu do corretor e esqueceu do Admin. Tela sem link é tela que
   não existe para quem usa.

3. **Cabeçalho e filhos divergentes** (anterior à 059). O grupo antigo tinha
   `href: '/admin/auxiliares'` e submenu sobre templates. Clicar no título
   levava a um lugar; clicar nos filhos, a outro assunto.

### Correção

- O grupo antigo virou **"Catálogo Global"** — nome do que de fato está lá: o
  que a plataforma publica para as corretoras. Ganhou entrada explícita para
  Auxiliares Globais, que antes só era alcançável clicando no cabeçalho.
- Os rótulos do submenu novo passaram a dizer o que **respondem**, não o que
  são por dentro: "Central (sinais, regras, demanda)" virou **"O que o sistema
  percebeu"**, e a Fábrica virou **"O que as corretoras pediram"**.

### Regra que fica

Toda página nova precisa de link no menu do papel que a usa, e nenhum rótulo
pode repetir. Verificar isso deveria fazer parte do gate visual de qualquer
SPEC que crie tela — hoje não faz.

### Nota para a SPEC-061

O Founder relatou que o Admin está confuso: páginas demais, linguagem técnica,
difícil de administrar. Estes três defeitos são evidência concreta disso, não
impressão. A SPEC-061 (Control Plane) deve tratar navegação e linguagem como
requisito, não como acabamento.

---

## CA-014 — O Admin foi desenhado para 5 corretoras, não para 1000

> **Renumerado** de CA-011 pelo mesmo motivo do [CA-013](#ca-013--menu-do-admin-rótulo-duplicado-e-página-órfã).

**Data:** 26/07/2026 · **Estado:** REGISTRADA — a corrigir na SPEC-061
**Origem:** Founder · **Prioridade:** ESSENCIAL antes de escalar

### A pergunta do Founder

> "O BRIEFING DA RESULTA VAI APARECER PARA MIM NO PORTAL ADMIN OU VAI APARECER
> PARA A RESULTA? COMO VOU FAZER QUANDO TIVEREM 1000 CORRETORAS USANDO O
> SISTEMA? O PORTAL ADMIN É UM LOCAL ONDE É PRA GERENCIAR TUDO, TODAS AS
> CORRETORAS."

Ele está certo, e a distinção é arquitetural.

### O que está correto hoje

O Briefing é **produto da corretora**, não da plataforma:

- vive em `/dashboard/briefing`, cada corretora vê só o seu
- `briefing_profiles` tem `scope='company'` e `company_id` obrigatório
- a Central do Admin já tem filtro opcional por `company_id` e teto de 40

Nada vaza entre corretoras. A separação de audiência está certa.

### O que NÃO escala

A aba "Briefings publicados" da Central lista os mais recentes, limitada a 40.
Com 5 corretoras isso é uma amostra útil. Com 1000 corretoras publicando
diariamente, essa lista mostra os últimos 40 minutos de atividade — e passa a
não responder pergunta nenhuma.

**Lista não é ferramenta de operação em escala.** O que o operador da
plataforma precisa saber não é *"quais briefings saíram"*, e sim:

- quantas corretoras **não** receberam briefing (essa é a falha, não o sucesso)
- quantos foram abertos — briefing publicado e nunca aberto é trabalho jogado fora
- quais regras disparam demais (ruído) e quais nunca disparam (regra morta)
- quais corretoras estão com saúde degradada

Os cartões agregados no topo da Central já seguem esse princípio e escalam. A
lista, não.

### Regra que fica para a SPEC-061

Toda tela do Portal Admin responde por **N corretoras**, não por uma. Quando a
resposta for uma lista, ela precisa de filtro, ordenação por relevância e um
agregado acima — e a pergunta a fazer no desenho é sempre *"o que isto mostra
quando houver mil?"*.

O caso individual continua acessível **por busca**, nunca por rolagem.

### Nota

Ligado ao CA-013, que registra os defeitos de navegação encontrados pelo
Founder. Os dois apontam a mesma causa: o Admin cresceu por adição de páginas,
sem alguém perguntando como ele se usa.

---

## CA-015 â€” "Origem interna nÃ£o vira sinal" Ã© um conceito, nÃ£o uma correÃ§Ã£o pontual

**Data:** 27/07/2026 Â· **Estado:** EXECUTADA Â· **SPEC:** 060 (melhoria da 059)
**Classe:** ESSENCIAL Â· **Origem:** Founder

### O problema

O canÃ¡rio da SPEC-059 encontrou dois falsos positivos com dado real (CA-012):
o chat do corretor com o AutoBrokers contado como "atendimento parado", e uma
integraÃ§Ã£o aposentada contada como "canal quebrado". Os dois foram corrigidos
**dentro do detector que os produziu**.

Corrigir dentro do detector resolve o caso e nÃ£o resolve a classe. O sistema
produz rastro o tempo todo â€” conversas de dashboard, Work Runs de manutenÃ§Ã£o,
artifacts gerados por rotina, pesquisas disparadas por monitor â€” e **cada
detector novo Ã© uma nova chance de contar esse rastro como fato da corretora**.
O corretor recebe um aviso sobre um problema que Ã© o prÃ³prio sistema
respirando, e a partir do terceiro aviso desses ele para de acreditar na tela.

### O que foi feito

`backend/app/services/intelligence/origem.py` â€” um conceito, quatro conjuntos
declarados e duas funÃ§Ãµes:

```python
CANAIS_INTERNOS            # web, dashboard, chat, playground, routine
PREFIXOS_DE_SESSAO_INTERNA # dispatch:, routine:, work:, monitor:, research:â€¦
ORIGENS_DE_SISTEMA         # system, monitor, recommendation, intelligenceâ€¦
ORIGENS_DE_PESQUISA_INTERNA

e_interno(tipo, registro) -> bool
filtrar_externos(tipo, registros, *, manter=None) -> list[dict]
```

Duas decisÃµes que valem mais que o cÃ³digo:

1. **Tipo desconhecido devolve `False`.** Na dÃºvida o item PASSA. Um filtro que
   erra para o lado de esconder produz o silÃªncio â€” e silÃªncio nÃ£o tem sintoma:
   ninguÃ©m abre chamado dizendo "nÃ£o recebi o aviso que eu nÃ£o sabia que
   existia". Falso positivo incomoda; falso negativo custa dinheiro.

2. **A exceÃ§Ã£o Ã© explÃ­cita e local.** `manter=` recebe um predicado do prÃ³prio
   detector. Ã‰ como o pedido de atendimento humano continua aparecendo mesmo
   vindo do canal `web`: a exceÃ§Ã£o fica escrita onde alguÃ©m consegue ler o
   motivo, e nÃ£o escondida numa regra genÃ©rica.

Aplicado nos detectores de qualidade, operaÃ§Ã£o e automaÃ§Ã£o. Na SPEC-060, a
mesma regra impede que **pesquisa disparada pela prÃ³pria plataforma vire sinal
de mercado da corretora** (`pesquisa_e_interna`, em `adapters.py`).

O gate cobra a presenÃ§a: RES-02 falha se qualquer um dos trÃªs detectores
deixar de chamar `filtrar_externos`.

---

## CA-016 â€” O catÃ¡logo de pesquisa jÃ¡ existia; adotÃ¡-lo em vez de criar o segundo

**Data:** 27/07/2026 Â· **Estado:** EXECUTADA Â· **SPEC:** 060
**Classe:** BLOCKER (evitado) Â· **Origem:** Executor

### O que foi encontrado

Ao preparar o seed de capacidades, ferramentas e Skills da SPEC-060, a consulta
ao banco de produÃ§Ã£o mostrou que **o catÃ¡logo jÃ¡ estava lÃ¡**, semeado em
26/07/2026 com `execution_manifest->>'spec' = 'SPEC-060'`:

| Camada | Existente |
|---|---|
| Capabilities | 8, todas com binding para `core`: `search`, `extract`, `deep`, `monitor`, `places`, `site_audit`, `claim_verify`, `regulatory` |
| Tools | `research.search_web`, `research.fetch_source`, `research.create_monitor`, `research.site_audit`, `research.search_places`, `research.verify_claims` â€” publicadas, apontando para `app.agents.tools.research_tool` |
| Skills | `research.quick_verified_answer`, `research.deep_dossier`, `research.claim_verify`, `research.regulatory_watch`, `research.website_seo_aeo_audit`, `research.business_lead_discovery` â€” 1.0.0 publicadas e ligadas ao `core` |

### O que teria acontecido

A migration que eu havia escrito criava um segundo conjunto com chaves prÃ³prias
(`research.search`, `research.monitor`, `research.answer_with_sources`,
`research.site_diagnosis`, `research.find_companies`). Duas consequÃªncias:

1. o Tool Gateway passaria a ter **duas ferramentas de busca** com o mesmo
   efeito e manifestos diferentes, sem nada dizendo qual Ã© a certa;
2. o teto de 12 tools por execuÃ§Ã£o (SPEC-053 Â§13.1) seria consumido por
   duplicatas â€” degradando a escolha do modelo em **toda** conversa, inclusive
   nas que nÃ£o tÃªm nada a ver com pesquisa.

Havia um segundo risco, no ROLLBACK: eu tinha escrito
`delete from tool_definitions where tool_key like 'research.%'`. Aplicado, ele
apagaria o catÃ¡logo em uso em produÃ§Ã£o â€” nÃ£o as linhas da minha migration.

### O que foi feito

- A migration foi reescrita para conter **apenas** o Auxiliar do Radar, a Ãºnica
  linha genuinamente ausente (`20260727_02_spec060_auxiliar_radar.sql`).
- O ROLLBACK passou a ser `delete ... where slug='radar-mercado-regulacao'` â€”
  por chave exata, nunca por `LIKE`.
- O motivo da nÃ£o-inserÃ§Ã£o ficou escrito no cabeÃ§alho da migration, com a lista
  do que jÃ¡ existe. Sem isso, a prÃ³xima pessoa reabre a mesma discussÃ£o.

Nenhuma mudanÃ§a de cÃ³digo foi necessÃ¡ria: a SPEC-060 depende de
**capabilities** (`platform.research.*`), nÃ£o de `tool_key`.

### A regra que isso confirma

CLAUDE.md Â§5 â€” consolidar e migrar antes de duplicar â€” vale para **dados de
catÃ¡logo**, nÃ£o sÃ³ para motores. Um segundo registro de Skills nÃ£o parece um
motor paralelo enquanto vocÃª o escreve; ele se comporta como um.

E um corolÃ¡rio sobre ROLLBACK: `delete ... like 'prefixo%'` num seed Ã©
destrutivo por construÃ§Ã£o, porque apaga por padrÃ£o de nome e nÃ£o por autoria.
Rollback de seed se escreve por chave.

---

## CA-017 â€” "O nÃºmero estÃ¡ errado" Ã© informaÃ§Ã£o sobre o detector, e ninguÃ©m via

**Data:** 27/07/2026 Â· **Estado:** EXECUTADA Â· **SPEC:** 060 (melhoria da 059)
**Classe:** ESSENCIAL Â· **Origem:** Founder

### O problema

Na SPEC-059, quando o corretor responde `wrong_data` a uma recomendaÃ§Ã£o, o
efeito era **cooldown**: aquele item para de aparecer para aquela corretora.
Correto e insuficiente.

`wrong_data` nÃ£o Ã© uma preferÃªncia sobre o item â€” Ã© um **relatÃ³rio de defeito
sobre a regra que o gerou**. Se trÃªs corretoras diferentes dizem que o mesmo
detector erra, o limiar estÃ¡ errado para todo mundo, e o sistema tratava isso
como trÃªs silÃªncios independentes. A informaÃ§Ã£o mais valiosa que a plataforma
recebe â€” o usuÃ¡rio apontando o erro â€” morria no cooldown.

### O que foi feito

`rule_engine.qualidade_por_regra()` passou a devolver, por regra:

- `dado_errado` â€” quantas vezes disseram que o nÃºmero estÃ¡ errado
- `dado_errado_tenants` â€” **em quantas corretoras distintas**
- `nao_relevante`
- `revisar_limiar` â€” verdadeiro a partir de 3 corretoras distintas
- `motivo_revisao` â€” a frase em portuguÃªs que explica por quÃª

A contagem percorre resposta â†’ recomendaÃ§Ã£o â†’ finding â†’ sinal â†’ regra. Em
`/admin/inteligencia`, as regras marcadas aparecem num alerta no topo, e a
coluna "NÂº errado" fica ao lado de cada regra.

### O que deliberadamente NÃƒO foi feito

**Nenhum limiar Ã© ajustado automaticamente.** A instruÃ§Ã£o do Founder foi
explÃ­cita, e a razÃ£o Ã© boa: um detector que se recalibra sozinho a partir de
feedback pode ser levado a qualquer lugar por um punhado de respostas â€” e
quando alguÃ©m finalmente perguntar por que ele parou de avisar, nÃ£o haverÃ¡
ninguÃ©m para responder. Ajuste automÃ¡tico de detector sem revisÃ£o Ã© como se
perde a confianÃ§a de vez.

O sistema **mostra**. Um humano decide.

### Contagem, nÃ£o mÃ©dia

A tela mostra nÃºmero de corretoras distintas, nÃ£o percentual. Dez reclamaÃ§Ãµes
de uma corretora sÃ£o um caso â€” provavelmente configuraÃ§Ã£o. Uma reclamaÃ§Ã£o de
dez corretoras Ã© um defeito de regra. Percentual confundiria os dois.

---

## CA-018 â€” Seis peÃ§as de pesquisa, porque o dossiÃª nÃ£o serve para tudo

**Data:** 27/07/2026 Â· **Estado:** EXECUTADA Â· **SPEC:** 060
**Classe:** VALIOSA Â· **Origem:** Executor

### O problema

A SPEC-057 entregou `research.market_brief` â€” um dossiÃª narrativo, onde o texto
conduz e o nÃºmero sustenta. Era o Ãºnico template de pesquisa, entÃ£o **todos** os
modos da SPEC-060 caÃ­am nele: uma lista de 40 empresas para prospectar saÃ­a
como ensaio, e uma auditoria de site saÃ­a como estudo de mercado.

A informaÃ§Ã£o estava lÃ¡ e o corretor nÃ£o conseguia usar. Documento com a forma
errada nÃ£o Ã© um problema estÃ©tico: Ã© trabalho entregue que ninguÃ©m aplica.

### O que foi feito

Seis templates no **mesmo catÃ¡logo** de `services/artifacts/templates.py`
(nenhum motor de peÃ§a novo):

| Chave | Forma | Por que nÃ£o cabia no dossiÃª |
|---|---|---|
| `research.evidence_pack` | precision_led | a fonte Ã© o assunto, nÃ£o o pano de fundo |
| `research.competitor_matrix` | comparative | a comparaÃ§Ã£o lado a lado Ã© o argumento inteiro |
| `research.site_audit` | precision_led | Ã© lista priorizada de conserto, nÃ£o anÃ¡lise |
| `research.regulatory_radar` | chronological | publicaÃ§Ã£o e vigÃªncia sÃ£o datas diferentes |
| `research.company_list` | precision_led | dado para trabalhar, nÃ£o para ler |
| `research.change_report` | chronological | antes e depois de UMA pÃ¡gina |

`adapters.template_do_modo()` escolhe pela intenÃ§Ã£o do pedido. `escolher()`
ganhou as pistas novas â€” e `concorr` e `regulaÃ§` **saÃ­ram** das pistas do
`market_brief`: mantÃª-las nos dois criaria empate, e empate ali Ã© resolvido por
ordem de dicionÃ¡rio, que Ã© o tipo de comportamento que ninguÃ©m explica depois.

Cada template carrega no `instruction_md` o limite que o protege: a auditoria
nÃ£o promete posiÃ§Ã£o no Google, a matriz nÃ£o estima faturamento de terceiro, a
lista de empresas nÃ£o infere renda, o radar nÃ£o trata minuta como norma
vigente.

---

## CA-019 â€” O Auxiliar Radar nÃ£o podia ser um card que nÃ£o faz nada

**Data:** 27/07/2026 Â· **Estado:** EXECUTADA Â· **SPEC:** 060 Â§37
**Classe:** ESSENCIAL Â· **Origem:** Executor

### O problema

O caminho genÃ©rico de instalaÃ§Ã£o de Auxiliar (`installTenantAuxiliary`) grava
`tenant_auxiliaries` e resolve o runtime. Para um Auxiliar com blueprint de
Agent isso basta. Para o Radar, nÃ£o: ele sÃ³ existe se **os monitores forem
criados**.

Instalado pelo caminho genÃ©rico, o Radar apareceria como "ativo" na galeria e
nunca avisaria nada. Ã‰ a pior forma de falhar, porque parece que estÃ¡
funcionando â€” e a corretora sÃ³ descobre quando perde uma mudanÃ§a de norma.

### O que foi feito

- `services/research/radar.py` â€” `instalar` / `desinstalar` / `status` /
  `compor_semanal`. A instalaÃ§Ã£o cria os monitores oficiais (SUSEP, CNSP,
  legislaÃ§Ã£o) via `MonitorService`, cada um preso a uma Rotina, mais a Rotina
  de fechamento semanal.
- `POST /api/research/radar/install` â€” o efeito real.
- `installTenantAuxiliary` passou a chamar o backend **antes** de gravar o
  status: se o efeito falha, o Auxiliar fica `awaiting_runtime` com o motivo,
  em vez de `active` mentindo.
- A Rotina de fechamento declara `config.workflow = research.radar_weekly`, e a
  ponte de Rotinas passou a respeitar essa declaraÃ§Ã£o. Sem lista de nomes na
  ponte: uma lista viraria um segundo registro de workflows.

### Nenhum motor novo

| Papel | Quem faz |
|---|---|
| agendar | `routine_engine` |
| verificar | `MonitorService` via `research.monitor_check` |
| compor | Artifact Hub |
| avisar | Intelligence Fabric |

O Auxiliar Ã© o **nome** que a corretora reconhece para esse conjunto.

### Sem mudanÃ§a, sem peÃ§a

`compor_semanal` nÃ£o gera Artifact quando nada mudou. Um radar que entrega
documento vazio toda semana treina o corretor a nÃ£o abrir o prÃ³ximo â€” e o
prÃ³ximo pode ser o que importava.

---

## CA-020 â€” O produto trabalhava sem deixar rastro

**Data:** 27/07/2026 Â· **Estado:** EXECUTADA Â· **SPEC:** Bloco 0 da 061 (Â§8, Â§9)
**Classe:** BLOCKER Â· **Origem:** Executor

### O problema

Com 43 Work Runs concluÃ­dos, 104 etapas e 423 eventos em produÃ§Ã£o:

```text
work_attempts    = 0
tool_invocations = 0
```

Duas causas diferentes, as duas defeito:

1. **`work_attempts` nÃ£o tinha writer nenhum.** A docstring de `executar_passo`
   prometia "registrando inÃ­cio, fim, **tentativa** e progresso" e a tentativa
   nunca era gravada.
2. **`tool_invocations` tinha writer e ninguÃ©m o chamava.**
   `ToolGateway.registrar_invocacao()` e `finalizar_invocacao()` estavam
   escritos, sem um Ãºnico chamador no repositÃ³rio.

### ConsequÃªncia de nÃ£o fazer

`work_steps` guarda o **estado final**. Sem a tentativa, uma etapa que sÃ³ passou
na quarta vez Ã© indistinguÃ­vel de uma que passou de primeira â€” e nÃ£o hÃ¡ como
diagnosticar trabalho lento.

Sem a invocaÃ§Ã£o, o corretor diz "ele nÃ£o conseguiu consultar a apÃ³lice" e nÃ£o hÃ¡
como saber se a ferramenta falhou, se foi negada por capability ou se o modelo
nunca a chamou. O Gateway decidia *quais* ferramentas o agente recebia e depois
perdia a chamada de vista.

E o Cockpit da SPEC-061 governa exatamente esses objetos: construÃ­do hoje,
mostraria "0 tentativas, 0 chamadas" e o operador concluiria, errado, que o
sistema nÃ£o trabalha.

### MudanÃ§a

- `services/work/workflows.py`: `_abrir_tentativa` / `_fechar_tentativa` /
  `_localizar_step`. NÃºmero vem de quantas tentativas jÃ¡ existem no banco â€” nÃ£o
  de contador em memÃ³ria, porque o worker pode morrer e outro assumir.
- `services/skills/invocation_recorder.py` (novo): amarra a execuÃ§Ã£o aos
  mÃ©todos que **jÃ¡ existiam** no Gateway. NÃ£o Ã© um segundo Gateway.
- `agents/nodes.py`: o `tool_node` executa dentro de um `with` de registro.

**Registrar no `tool_node`, e nÃ£o dentro de cada ferramenta, Ã© o que impede que
a prÃ³xima ferramenta nasÃ§a sem auditoria:** quem esquecer de instrumentar
continua registrado, porque o ponto de execuÃ§Ã£o Ã© um sÃ³.

TrÃªs decisÃµes que valem mais que o cÃ³digo:

- **falhar ao registrar nunca derruba a ferramenta** â€” contabilidade quebrada Ã©
  ruim, trabalho do corretor perdido Ã© pior;
- **a invocaÃ§Ã£o que abre sempre fecha** â€” sair sem confirmar fecha como falha,
  porque "running" eterno polui qualquer contagem de trabalho em andamento;
- **a mensagem de erro Ã© redigida antes de ir ao banco** â€” exceÃ§Ã£o de provider
  carrega URL com query string, e query string carrega chave.

### O que NÃƒO era defeito

`usage_events = 0` e `artifacts = 0` estavam **certos**. Os 43 runs sÃ£o todos
workflows internos de inteligÃªncia, que leem o banco da prÃ³pria corretora e nÃ£o
chamam provider pago. Sem chave de Tavily e com Firecrawl sem crÃ©dito, zero
consumo Ã© o nÃºmero verdadeiro.

Tratar as quatro tabelas igual teria produzido correÃ§Ã£o onde nÃ£o havia problema
â€” e nenhuma onde havia.

### AutorizaÃ§Ã£o

Executor, dentro do Bloco 0 autorizado pelo Founder. Gate `AUD-01`.

---

## CA-021 â€” A view do cutover era lida por qualquer visitante

**Data:** 27/07/2026 Â· **Estado:** EXECUTADA Â· **SPEC:** Bloco 0 da 061 Â§7
**Classe:** BLOCKER Â· **Origem:** Security Advisor + Founder

### O problema

`public.v_gateway_cutover_progresso` era `SECURITY DEFINER` e concedia
`SELECT, INSERT, UPDATE, DELETE, TRUNCATE` a **`anon` e `authenticated`**.

A tabela base `tool_gateway_shadow_diffs` tem RLS ligada e zero policy â€” ela
barrava corretamente esses papÃ©is. A view, por executar com os poderes do dono,
**contornava exatamente essa barreira**.

### ConsequÃªncia de nÃ£o fazer

Quem tivesse a chave pÃºblica do projeto â€” que por definiÃ§Ã£o vive no navegador â€”
lia telemetria de plataforma: quantas decisÃµes o Gateway toma por dia, em
quantas ele diverge do caminho antigo, quantas dÃ£o erro.

NÃ£o Ã© dado de segurado. Ã‰ a resposta para "o AutoBrokers estÃ¡ com quantos por
cento de divergÃªncia hoje?" â€” que nÃ£o Ã© pergunta de visitante anÃ´nimo.

### MudanÃ§a

`20260727_03`: `security_invoker = on`, `revoke` de `anon`, `authenticated` e
`public`, `grant select` apenas a `service_role`.

**Por que `security_invoker` e nÃ£o sÃ³ `revoke`:** o `revoke` sozinho resolve
hoje, mas a view continuaria SECURITY DEFINER e o prÃ³ximo `grant` distraÃ­do â€” ou
o `GRANT ALL ... TO anon` que o Supabase aplica por padrÃ£o â€” reabriria o buraco
em silÃªncio. Com `security_invoker`, a RLS da tabela base volta a valer e a
defesa deixa de depender de alguÃ©m lembrar. Passa a ser estrutural.

SaÃ­da real do Advisor depois: **ERROR 0, WARN 0**, 97 INFO â€” que sÃ£o o deny-all
deliberado de CLAUDE.md Â§7, nÃ£o pendÃªncia.

### AutorizaÃ§Ã£o

Executor, dentro do Bloco 0.

---

## CA-022 â€” Firecrawl era o Ãºnico degrau acima da leitura direta

**Data:** 27/07/2026 Â· **Estado:** EXECUTADA (reclassificaÃ§Ã£o do D18: **proposta**)
**SPEC:** Bloco 0 da 061 Â§13, Â§15, Â§16 Â· **Classe:** ESSENCIAL Â· **Origem:** Founder

### O problema

A hierarquia de leitura era `direct_fetch â†’ firecrawl`: o mais barato e, em
seguida, **o mais caro**. Nada no meio. Uma pÃ¡gina que o leitor direto nÃ£o
resolvia â€” porque monta conteÃºdo por JavaScript, ou porque o HTML vem sujo de
menu e rodapÃ© â€” caÃ­a direto no provider premium.

Pior: `TavilyProvider.operacoes` **declarava** `("search", "extract")` e o
mÃ©todo `extract` **nÃ£o existia**. A capacidade estava anunciada e ausente.

### MudanÃ§a

- `TavilyProvider.extract` â€” lÃª UMA pÃ¡gina jÃ¡ escolhida, devolve texto limpo.
  Descobrir nÃ£o Ã© ler: `search` acha o endereÃ§o, `extract` lÃª o que estÃ¡ nele.
  Usar `search` para obter conteÃºdo devolve o resumo do buscador, que nÃ£o serve
  para citar no nÃ­vel da afirmaÃ§Ã£o.
- `TavilyProvider.crawl` â€” vÃ¡rias pÃ¡ginas do mesmo site, com **teto absoluto**
  (`TETO_DE_CRAWL = 50`, constante e nÃ£o argumento padrÃ£o, porque argumento
  padrÃ£o Ã© sugestÃ£o), profundidade limitada e fronteira de domÃ­nio. Crawl que
  sai do site pedido vira varredura da internet, e ninguÃ©m orÃ§ou isso.
- Hierarquia: `direct_fetch â†’ tavily_extract â†’ firecrawl`.
- PolÃ­tica de roteamento escrita no `provider_router`, incluindo a regra que ela
  existe para impedir: **escolher provider sÃ³ porque a chave estÃ¡ configurada**.

`Research` (pesquisa profunda do Tavily) **nÃ£o** entra em rota automÃ¡tica: Ã©
minutos e crÃ©ditos por pergunta, e uma pergunta de rotina que caia nele
transforma custo previsÃ­vel em conta surpresa.

### Sobre o D18

Com Tavily configurado, **Firecrawl deixa de ser bloqueio** e passa a ser
provider opcional/premium. O suporte nÃ£o foi removido, o status continua
explÃ­cito (`no_credit` â‰  erro genÃ©rico) e a fila continua retomÃ¡vel.

Nenhum plano foi comprado. A reclassificaÃ§Ã£o formal em `FOUNDER-DECISIONS.md`
Ã© decisÃ£o do Founder.

### AutorizaÃ§Ã£o

Executor, dentro do Bloco 0. ReclassificaÃ§Ã£o do D18 fica como **proposta**.

---

## CA-023 â€” Quatro Ã­ndices para o Cockpit que ainda nÃ£o existe

**Data:** 27/07/2026 Â· **Estado:** EXECUTADA Â· **SPEC:** Bloco 0 da 061 Â§19
**Classe:** VALIOSA Â· **Origem:** Executor

### O problema

O levantamento cruzou as consultas previstas pelo Cockpit da SPEC-061 com os
Ã­ndices existentes. A maioria jÃ¡ existia. Faltavam quatro, todos com a mesma
forma â€” *filtra por corretora, ordena por tempo decrescente*:

| Ãndice | Consulta que atende |
|---|---|
| `ix_work_runs_company_recente` | "Ãºltimos trabalhos desta corretora" |
| `ix_work_attempts_company_status` | "onde falhou e quantas vezes tentou" |
| `ix_tool_invocations_company_recente` | "quais ferramentas usou, quais falharam" |
| `ix_usage_events_company_recente` | "quanto consumiu no perÃ­odo" |

### Honestidade sobre o ganho

**Custo antes/depois nÃ£o Ã© mensurÃ¡vel hoje.** TrÃªs dessas tabelas estÃ£o com zero
linhas; com tabela vazia o plano usa Seq Scan de qualquer jeito e o nÃºmero seria
sem significado.

Foram criados **agora** porque com a tabela vazia a criaÃ§Ã£o Ã© desprezÃ­vel.
Depois, com volume e o Admin em uso, exigiria `CONCURRENTLY` e uma janela.

Nenhum outro Ã­ndice foi criado. Â§19 pede o oposto de "criar Ã­ndice atÃ© o advisor
calar".

### AutorizaÃ§Ã£o

Executor, dentro do Bloco 0.
