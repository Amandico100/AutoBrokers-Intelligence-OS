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
| CA-024 | A proteção do Admin acontecia no navegador | 061 A | BLOCKER | EXECUTADA | 27/07/2026 |
| CA-025 | Minha baseline de páginas órfãs estava errada | 061 C | ESSENCIAL | EXECUTADA | 27/07/2026 |
| CA-026 | A Inbox precisa mostrar a causa, não o sintoma | 061 B | ESSENCIAL | EXECUTADA | 27/07/2026 |
| CA-027 | Eu tranquei o dono para fora do próprio Admin | 061 A | BLOCKER | EXECUTADA | 27/07/2026 |
| CA-028 | Leitor tolerante engolia coluna inexistente | 061 B | BLOCKER | EXECUTADA | 27/07/2026 |

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

---

## CA-024 â€” A proteÃ§Ã£o do Admin acontecia no navegador

**Data:** 27/07/2026 Â· **Estado:** EXECUTADA Â· **SPEC:** 061 Bloco A (Â§7.2, Â§8.4)
**Classe:** BLOCKER Â· **Origem:** Executor

### O problema

`app/admin/layout.tsx` lia a sessÃ£o administrativa de `localStorage` e comparava
a rota atual com uma lista de `masterOnlyRoutes`. A decisÃ£o de acesso era do
navegador.

`localStorage` Ã© editÃ¡vel por quem estÃ¡ na frente da tela, e a lista de rotas
protegidas vivia lÃ¡. Mas o defeito mais grave Ã© outro: **esconder a tela nÃ£o
protege a API**. Quem quisesse pular a interface chamava a rota direto â€” e ela
respondia.

Â§8.4 jÃ¡ dizia: *"esconder botÃ£o Ã© conveniÃªncia, nÃ£o seguranÃ§a"*.

### ConsequÃªncia de nÃ£o fazer

Um `company_admin` que soubesse o endereÃ§o de uma rota `master` a acionaria. Com
118 rotas de API no Admin, a superfÃ­cie nÃ£o Ã© pequena.

### MudanÃ§a

- `lib/admin/control-plane/authority.ts` â€” resolve sessÃ£o â†’ papÃ©is â†’ permissions
  no servidor, com `exigirPermissao()` como portÃ£o das rotas.
- `app/api/admin/control-plane/me` â€” o menu passa a ser **derivado** das
  permissions. Mostrar item que devolve 403 ensina o operador a duvidar da tela
  inteira, e tela em que nÃ£o se confia deixa de ser usada.
- `localStorage` volta ao que o Â§7.2 permite: preferÃªncia de barra, tema,
  densidade.

**A matriz nÃ£o foi duplicada.** O BFF pergunta ao backend. Duas cÃ³pias
divergiriam na primeira permission nova: alguÃ©m acrescenta a tela, o backend
passa a cobrar `releases.rollout`, o front nÃ£o conhece a chave, e o operador vÃª
um botÃ£o que devolve 403 â€” ou o inverso, que Ã© pior.

Cache de 30s por processo, e falha de rede **nÃ£o** entra em cache: backend fora
do ar nÃ£o pode conceder acesso.

### AutorizaÃ§Ã£o

Executor, dentro da SPEC-061 Bloco A. Gate `RBA-01`.

---

## CA-025 â€” Minha baseline de pÃ¡ginas Ã³rfÃ£s estava errada

**Data:** 27/07/2026 Â· **Estado:** EXECUTADA Â· **SPEC:** 061 Bloco C
**Classe:** ESSENCIAL Â· **Origem:** Executor (correÃ§Ã£o de si mesmo)

### O problema

O Bloco 0 declarou **9 pÃ¡ginas Ã³rfÃ£s** no Admin. O nÃºmero estava errado, por dois
defeitos no teste `test_navegacao_sem_pagina_orfa.py` â€” escrito por mim na
SPEC-060:

1. **Lia apenas `masterMenuItems`.** O Admin serve dois papÃ©is com menus
   diferentes (`role === 'master' ? masterMenuItems : companyAdminMenuItems`).
   Cinco das nove sÃ£o alcanÃ§adas normalmente pelo administrador da corretora:
   `/admin/team`, `/admin/conversations`, `/admin/agent`, `/admin/documents` e
   `/admin/billing`.
2. **Contava link comentado como link.** O regex casava
   `// { href: '/admin/integrations', â€¦ } // HIDDEN` â€” cÃ³digo desligado.

### ConsequÃªncia de nÃ£o fazer

Um teste que **superestima** a dÃ­vida Ã© tÃ£o ruim quanto um que a esconde: no
primeiro caso alguÃ©m "conserta" o que nÃ£o estava quebrado â€” no caso, criando
links de menu para telas que jÃ¡ eram alcanÃ§Ã¡veis, e poluindo o menu que a
SPEC-061 existe para simplificar.

E o segundo defeito escondia o caso real: uma pÃ¡gina cujo item de menu foi
comentado Ã© exatamente o que o teste deveria pegar, e ele a declarava
alcanÃ§Ã¡vel.

### MudanÃ§a

- o teste lÃª os **dois** menus;
- comentÃ¡rios sÃ£o removidos antes do parsing;
- rÃ³tulo duplicado passou a ser comparado **por menu**, nÃ£o somado â€” "Conversas"
  existir nos dois nÃ£o Ã© ambiguidade, porque ninguÃ©m vÃª os dois.

A dÃ­vida real era de **quatro** pÃ¡ginas. TrÃªs ganharam link no submenu a que jÃ¡
pertenciam; `/admin/integrations` Ã© um redirecionamento e ficou como exceÃ§Ã£o
nomeada. `ORFAS_ANTERIORES_A_SPEC059` Ã© hoje um conjunto **vazio**.

### AutorizaÃ§Ã£o

Executor. CorreÃ§Ã£o de mediÃ§Ã£o prÃ³pria, registrada porque a baseline errada jÃ¡
tinha ido para o relatÃ³rio do Bloco 0 e para o Master Plan.

---

## CA-026 â€” A Inbox precisa mostrar a causa, nÃ£o o sintoma

**Data:** 27/07/2026 Â· **Estado:** EXECUTADA Â· **SPEC:** 061 Â§13
**Classe:** ESSENCIAL Â· **Origem:** Executor

### O problema

As SPECs 054â€“060 produzem trabalho o tempo todo, cada um na sua tabela com a sua
tela. Sem uma caixa Ãºnica, o operador da plataforma abre nove telas de manhÃ£ â€” ou
nÃ£o abre nenhuma.

E uma caixa mal feita Ã© pior que nenhuma: oito rotinas quebradas pelo mesmo
provider fora do ar viram oito cartÃµes, o operador trata sintoma, e o provider
continua fora do ar.

### MudanÃ§a

`services/control_plane/inbox.py` â€” projeÃ§Ã£o de sete fontes, com dedupe por
causa e prioridade explicÃ¡vel.

A causa Ã© `(fonte, tÃ­tulo, motivo)` e deliberadamente **nÃ£o** inclui a
corretora: Ã© juntando corretoras diferentes que o cartÃ£o revela que o problema
Ã© de plataforma. O texto resultante Ã© o do Â§13.4: *"afeta 3 corretoras e 8
itens"*.

TrÃªs decisÃµes:

- **fonte que a pessoa nÃ£o pode ler nÃ£o Ã© consultada** â€” ler para depois esconder
  Ã© como dado vaza por um log ou por uma contagem que sobrou na tela;
- **fonte fora do ar nÃ£o zera a caixa** â€” se aprovaÃ§Ãµes cair, o operador ainda
  precisa ver os incidentes. Caixa vazia por erro parcial Ã© a pior resposta
  possÃ­vel para "o que precisa de mim?";
- **caixa vazia diz que estÃ¡ vazia** â€” sem a frase, ninguÃ©m sabe se estÃ¡ limpa ou
  quebrada.

Â§13.3: dispensar tira o item da caixa **daquela pessoa** e nÃ£o altera o objeto de
origem. A aprovaÃ§Ã£o continua pendente; outra pessoa continua vendo.

### AutorizaÃ§Ã£o

Executor, dentro da SPEC-061 Bloco B. Gate `INB-01`.

---

## CA-027 — Eu tranquei o dono para fora do próprio Admin

**Data:** 27/07/2026 · **Estado:** EXECUTADA · **SPEC:** 061 Bloco A
**Classe:** BLOCKER · **Origem:** Founder (primeiro deploy real)

### O problema

O Founder implantou API, web e worker, abriu `/admin/inbox` e
`/admin/governanca` e leu **"Seu papel não inclui ver esta caixa"** — sendo ele
o único administrador da plataforma.

Dois defeitos meus, independentes, com o mesmo sintoma:

1. **Nome de papel que eu supus.** `PAPEL_LEGADO` nasceu com a chave
   `"master"`. Esse nome não existe em lugar nenhum do código: o valor gravado
   na sessão é `master_admin` (`lib/iron-session.ts`).
2. **Eu fiz o Admin depender do backend estar no ar.** Até esta SPEC o master
   via tudo com zero chamadas a outro serviço. Depois dela, uma variável de
   ambiente faltando no serviço web trancava o dono para fora.

### O que o teste não pegava

`test_spec061_rbac.py` conferia que o mapeamento **aponta** para um papel
existente. Não conferia que a **chave** bate com o que a sessão grava — a
diferença entre "o destino existe" e "a porta abre".

### Mudança

- `PAPEL_LEGADO` passou a conhecer `master_admin`, e o teste agora **lê
  `lib/iron-session.ts`** e cobra que todo papel de plataforma esteja no mapa —
  e que `company_admin` **não** esteja, porque §8.2 proíbe convertê-lo.
- Rede de segurança no BFF: sem resposta do backend, se `isPlatformMaster` (que
  lê o cookie iron-session assinado no servidor, já autoridade em
  `requireMasterAdmin`) o acesso é mantido, com `podeTudo`.

**Não é afrouxar autorização.** É recusar que a permanência de um acesso
**existente** dependa de um segundo serviço responder. Para os outros papéis
segue fail-closed.

A tela **avisa** quando está nesse modo — e é isso que distingue as duas causas:
aviso âmbar significa backend inacessível; sem aviso, era o nome do papel.

### Bootstrap

`amandico10@hotmail.com` recebeu `platform_owner` sem prazo.
`/admin/governanca` ganhou conceder, retirar e motivo obrigatório — sem isso a
tela mostrava a governança e não deixava governar.

### Autorização

Executor, correção de defeito próprio dentro da SPEC-061.

---

## CA-028 — Um leitor tolerante engolia coluna que não existe

**Data:** 27/07/2026 · **Estado:** EXECUTADA · **SPEC:** 061 Bloco B
**Classe:** BLOCKER · **Origem:** Executor

### O problema

A Inbox lia `approval_requests.action_key`. A coluna real é `action_type` — eu
escrevi de memória. O Cockpit lia `company_integrations`, tabela que **não
existe** (é `integrations`, com `channel_status`).

O leitor tolerante (`_ler`, que devolve `[]` quando a consulta falha) engolia os
dois. **Aprovação nunca apareceria na caixa**, sem nada na tela indicando por
quê — e a caixa continuaria dizendo "Nada precisa de você agora", que nesse
caso é mentira.

### A lição

A tolerância está certa: uma fonte fora do ar não pode zerar a caixa inteira.
Mas um leitor que não derruba a tela **também não avisa**. Ela precisa de um
teste do lado de fora, senão vira silêncio.

E o canário anterior não pegou: ele rodou `count(*)`, que não toca as colunas
do `select`.

### Mudança

`test_spec061_colunas_reais.py` (caso `COL-01`) extrai do código os pares
`(tabela, colunas)` de cada `.table().select()` **e** de cada
`_ler("tabela","colunas")` — que é onde o defeito estava — e compara com o
schema real copiado do banco.

Tabela cujo schema não foi copiado precisa estar declarada em
`NAO_VERIFICADAS` **com o motivo**. Esquecer não é opção; declarar é.

A cópia do schema vem datada e com a consulta que a regera — um teste que
compara com uma cópia velha é pior que nenhum, porque dá confiança falsa.

### Autorização

Executor, correção de defeito próprio dentro da SPEC-061.

---

## CA-020 — `middleware.ts` libera todo `/api/` sem olhar sessão

**ESSENCIAL** · registrado em 27/07/2026 · autorizado pelo Founder para a SPEC-063

### Problema

```ts
const isApiRoute = apiRoutes.includes(pathname) || pathname.startsWith('/api/');
if (isPublicRoute || isPublicPrefix || isApiRoute) return response;
```

Todo endereço sob `/api/` passa pelo middleware **sem nenhuma checagem de
sessão**. As rotas conferem por conta própria — e é aí que mora o risco: a
proteção depende de cada autor lembrar.

### Evidência

Medido em produção em 27/07/2026, sem cookie nenhum:

```
GET /dashboard                                 → 307 para /login
GET /admin/companies                           → 307 para /admin/login
GET /api/admin/proxy/agents/company/<id>/…     → 200 com o prompt da corretora
```

O `lib/admin-proxy.ts` era uma das rotas que não conferiam: carimbava
`X-Admin-API-Key` (a chave de plataforma) em requisição de qualquer pessoa da
internet e entregava ao backend, que obedecia — GET, PUT e DELETE em agente de
qualquer corretora. Origem: primeiro commit do repositório (`6274293`,
04/06/2026), do código original do Smith.

### Consequência

O buraco conhecido foi fechado em `6cc4bf1` e `0eb903b` (só sessão de
plataforma passa). **A causa de raiz continua.** Não há outro buraco conhecido
hoje — mas o padrão é o oposto do que deveria ser: **uma rota nova mal escrita
nasce pública**, e o autor não recebe nenhum sinal disso.

### Correção proposta (SPEC-063)

Inverter o padrão: o middleware exige sessão em `/api/**` por omissão, e as
rotas genuinamente públicas entram numa lista curta e explícita
(`/api/auth/login`, `/api/admin/login`, webhooks com token próprio, `/embed/`).

Uma rota nova passa a nascer **fechada**. Esquecer de listá-la produz um 401 em
desenvolvimento — visível — em vez de uma exposição silenciosa em produção.

### Autorização

> Founder, 27/07/2026: "SOBRE ESSA QUESTÃO ABAIXO EU CONCORDO. PODE DEIXAR
> ANOTADO."

---

## CA-029 — Um `hash()` aleatório dobrou o material e torceu as rotas

**Classificação: BLOCKER (corrigido) + ESSENCIAL (limpeza pendente)**
**Data:** 28/07/2026 · commits `a2bde81`, `b0e1778`, `73a8b1f`

### Problema

A ingestão de histórico montava o id da mensagem assim:

```python
mid = f"hist-{counterparty}-{ts}-{abs(hash(str(text)[:60])) % 10**7}"
```

`hash()` de string em Python é **aleatorizado a cada processo**. O
`on_conflict="observer_number,message_id"` — que existe exatamente para impedir
duplicação — nunca disparava, porque o id mudava a cada reimportação.

### Evidência

| Tabela | Linhas | Mensagens reais | Fator |
|---|---:|---:|---:|
| `observed_events` (Allianz) | 14.203 | 5.330 | 2,66x |
| `observed_events` (Zurich) | 273 | 94 | 2,90x |
| `attendance_transcripts` | 116.877 | 58.786 | 1,99x |

Três `history_sync` num só dia (14:01, 15:02, 15:43), cada um gravando tudo
de novo. No `live`, o fator é 1,00x — o id vem do WhatsApp e é estável.

### Consequência

**Não era custo, era rota.** O Tecelão casa cada tela com a resposta que vem
logo depois. Com as cópias intercaladas a sequência vira tela-tela-tela-
resposta, e como o destino da aresta sequencial é eleito por maioria, o voto
da tela em si mesma chegava a **vencer o destino real**:

| Mapa | Arestas | Apontando para a própria tela |
|---|---:|---:|
| Allianz | 1.899 | 840 (44%) |
| Porto | 576 | 284 (49%) |
| Yelum | 280 | 152 (54%) |
| Tokio | 58 | 40 (69%) |

No Espelho, o transcript é cortado em 7.000 caracteres: **56 sessões
estouravam o teto e só 9 estourariam sem as cópias.** As 47 do meio perdiam o
fim — onde o atendimento se resolve.

E o id só olhava os 60 primeiros caracteres: duas mensagens longas de começo
igual colidiam, e a segunda era **descartada em silêncio**. Isso perdia
mensagem, contra a regra do Founder.

### Corrigido

`_history_message_id()` com sha1 de (direção, tipo, texto inteiro), provado
estável em processos separados com `PYTHONHASHSEED=random`. As cópias já
gravadas são ignoradas na **leitura**, pelo mesmo filtro no Tecelão e no
Espelho. Tela apontando para si mesma sem escolha capturada deixa de virar
aresta — com escolha capturada continua, porque "digitou 9 e voltou pro menu"
é rota de verdade.

### Pendente de decisão do Founder

**15.176 linhas em `observed_events` e ~58.091 em `attendance_transcripts`
continuam no banco**, ignoradas na leitura. Apagá-las é §10.1 — decisão do
Founder, com tabela de backup antes.

**47 sessões do Espelho foram destiladas com o texto cortado.** Redestilar só
essas é barato e recupera perda real.

---

## CA-030 — Nenhum áudio, foto ou documento do Espelho foi lido

**Classificação: ESSENCIAL — não corrigido, depende de decisão**
**Data:** 28/07/2026

### Problema

9.588 mensagens de mídia no Espelho. Nenhuma com transcrição, nenhuma com OCR:

```
document 3.900   image 2.950   audio 2.631   video 130
```

O que chega à LLM é `[audio]`. Em seguro, o áudio é justamente onde o cliente
explica o sinistro, e o documento é a apólice.

### Evidência

- **9.565** vieram do `history_sync` e **nunca entraram na fila** de
  enriquecimento — só o caminho `live` enfileira.
- **23** do `live` tentaram e **falharam todas**, gravadas como
  `HTTPStatusError`.

Sondagem do servidor sem token, em 28/07/2026:

```
POST /message/downloadmedia              → HTTP 401   (rota existe)
POST /chat/getBase64FromMediaMessage     → HTTP 404
POST /message/download                   → HTTP 404
POST /media/download                     → HTTP 404
```

**A rota está certa.** O problema é autenticação ou corpo — e o registro não
distinguia 401 (token) de 404 (mídia expirada) de 5xx (servidor fora), que
pedem três consertos diferentes.

### Feito agora

`_motivo_da_falha()` grava `HTTP 401 /message/downloadmedia`: status e rota,
nunca o corpo (pode trazer dado de cliente) e nunca o token. A próxima mídia
ao vivo diz exatamente o que houve.

### Decisão pendente

Enriquecer as 9.565 mídias do histórico tem custo de transcrição e as mídias
antigas podem já ter expirado no WhatsApp. **Recomendação: testar numa amostra
de 20 antes de decidir o lote.**

---

## CA-031 — A mídia do segurado, o que ela custa e por que o plano Max não serve

**Classificação: ESSENCIAL (ao vivo, corrigido) + decisão de custo (histórico)**
**Data:** 28/07/2026 · commit `682dd91`

### O que estava desligado

`_download_evolution_media`, para `evolution-go`:

```python
# GO usa /message/downloadmedia com o message bruto (shape a confirmar
# no primeiro teste ao vivo). Sem inventar wire: mídia entra depois.
return None
```

A prudência estava certa na época. Mas com o **agente de atendimento ligado**,
isso significa que toda foto de dano, todo áudio explicando o sinistro e todo
PDF de apólice que o segurado mandasse seria invisível para o agente.

O fork publica o próprio Swagger em `/swagger/doc.json`:

```
POST /message/downloadmedia   body = { message: waE2E.Message }
POST /chat/getBase64FromMediaMessage   → 404 (é o wire do Baileys)
```

Ou seja: o corpo que o Observador já enviava estava certo. Corrigido; o
caminho reusa `observer_media._download_media` — um motor só.

### Por que não existe "reprocessar as 9.002"

O download exige o `waE2E.Message` inteiro — `mediaKey`, `directPath`,
`fileEncSha256`. **Nada disso fica no banco.** `media_meta` guarda tipo, nome
e legenda. Depois que a ingestão retorna, aquela foto é inalcançável.

As 23 falhas ao vivo também não dão para repetir: o payload do Redis expirou.

A única via é enfileirar **durante** um novo HistorySync — que é como o
orçamento foi construído.

### O custo real (preços da nossa `llm_pricing`, 28/07/2026)

| Item | Quantidade | Custo |
|---|---:|---:|
| Áudio (Whisper, 45s médios) | 2.631 | US$ 11,84 |
| Imagem (gpt-4o-mini) | 2.685 | US$ 0,77 |
| Imagem (gemini-2.5-flash-lite) | 2.685 | US$ 0,26 |
| Documento (docling local + resumo flash-lite) | 3.572 | US$ 0,57 |
| Vídeo | 114 | desprezível |
| **Tudo, cenário baixo** | **9.002** | **US$ 8,72** |
| **Tudo, cenário pessimista (áudios de 2 min)** | **9.002** | **US$ 32,91** |
| **As 20 do teste** | 20 | **US$ 0,03** |

O receio de que fosse caro não se confirma: **ler tudo custa menos que um
almoço.** O item que domina é o áudio, e não há alternativa barata — é
Whisper a US$ 0,006/minuto.

### Por que o plano Max não resolve isto

O Founder propôs enriquecer pelo Claude Code com o plano Max, talvez com
Sonnet num agente paralelo. Três impedimentos, em ordem de peso:

1. **Claude não recebe áudio.** O áudio é 90% do custo. O plano Max não toca
   no item que pesa.
2. **As mídias não são arquivos que eu possa abrir.** Elas só existem dentro
   do WhatsApp durante o sync, e baixá-las exige o token da instância, que
   vive no backend.
3. **Para imagem o ganho seria de US$ 0,77** — e mesmo assim o backend teria
   de baixar e guardar tudo antes.

Usar Opus para isso custaria **US$ 27,52 só nas imagens** e não melhoraria
nada: descrever foto de para-choque amassado não é trabalho de modelo de
raciocínio.

### O orçamento

> Founder, 28/07/2026: "NÃO FAÇA A ANÁLISE DAS 9565 MÍDIAS VIA API NUNCA.
>  APENAS AS 20 QUE VC FALOU."

`POST /admin/atlas/observer/media-budget {"quantas": 20}` abre o crédito;
`POST /admin/atlas/observer/history-sync` gasta. O contador é um `DECR` no
Redis: sem crédito aberto devolve -1 e a mídia é ignorada. Teto de 500 por
pedido, validade de 2 horas, zero fecha.

### Recomendação

1. Rodar as 20 (US$ 0,03) e confirmar que o download funciona.
2. Se funcionar, ler as mídias dos **últimos 90 dias** em vez de tudo — a
   regra do próprio Founder é que conversa mais nova vale mais.
3. Gravar `seconds` e `fileLength` no `media_meta` para a próxima estimativa
   ser medida, não estimada. **Ainda não feito.**

---

## CA-021 · Mensagem encaminhada troca quem falou — VALIOSA

**Achado por** um subagente destilando o lote 007 em 29/07/2026, com dado real.

### O problema

Na sessão `35a2f0a9-…` falas claramente do segurado ("Mas para adiantar ela
está enchendo e não para transborda", "Vou testar fim-de-semana") aparecem
como **ATENDENTE**.

A causa é estrutural, não é bug de código: `direction` vem de `from_me`. Quando
alguém da equipe **encaminha** a mensagem do segurado para dentro do grupo de
observação, a mensagem sai do número da corretora — `from_me` é verdadeiro, e o
transcript rotula ATENDENTE um texto que o segurado escreveu.

### Por que importa mais do que parece

`fatos_reutilizaveis` sobrevive: um fato de processo continua verdadeiro
independentemente de quem o disse.

`resumo_conduta` e `perguntas_na_ordem`, não. Eles ensinam **como a melhor
atendente conduz**, e alimentam os playbooks. Aprender conduta de uma fala do
cliente atribuída à atendente ensina o agente a fazer a pergunta errada, do
lado errado da conversa.

### O que impede de consertar hoje

`attendance_transcripts` não guarda a marca de encaminhamento. As colunas são
`direction, msg_type, text, interactive, media_meta, message_id, wa_timestamp,
source` — o `contextInfo.isForwarded` do WhatsApp não é persistido. Sem esse
dado, nenhuma regra determinística distingue "a atendente escreveu" de "a
atendente encaminhou".

### Encaminhamento

**Agora:** o briefing do subagente manda devolver `fatos_reutilizaveis` só
quando o fato independe de quem falou, e **zerar a conduta** quando a
atribuição parecer trocada, com a razão em `flags`. Foi o que o subagente do
lote 007 fez por conta própria, e está certo.

**Depois:** persistir `isForwarded` na captura e reprocessar. É mudança na
ingestão, e o histórico já capturado não recupera a marca — só o que entrar
daqui para frente. Não bloqueia a campanha.

**Não fazer:** inferir encaminhamento por heurística de texto. Errar para o
lado de "isto é do cliente" apaga conduta legítima da atendente; errar para o
outro lado é o defeito que já temos. Sem o dado, o silêncio é mais honesto.

---

## CA-032 · `Palhoça/SC` deixava a UF vazia — ESSENCIAL

**Encontrado em** 05/08/2026, durante a SPEC-063, escrevendo o guarda da
confirmação (item 4). **Não estava no texto da SPEC.**

### O problema

`parse_address_br` não quebrava na **barra**. A grafia mais comum do Brasil —
`Palhoça/SC`, `São José/SC`, `Florianópolis/SC` — produzia:

```
cidade = "Palhoça/SC"      uf = ""        ← a UF simplesmente sumia
```

### A evidência, e por que ela é maior que o guarda

O guarda da confirmação encontrou o defeito porque **compara endereços**: com a
cidade grudada na UF, ele reprovava uma confirmação legítima. Mas o estrago não
começa nele — ele só foi o primeiro a olhar.

📊 Os passos do corredor que mandam `{local_cidade}` e `{destino_uf}` para a URA
liam o mesmo campo torto. Onde a URA pedia a UF, o corredor entregava vazio — e
a pergunta caía no caminho adaptativo, que custa uma chamada de modelo e uma
chance do contador de falhas. Em silêncio, e no formato de endereço mais comum
que existe.

### O que foi feito

Consertado **o campo**, não o texto — CLAUDE.md §12.1: *"se o nome de um campo
mente sobre o que ele guarda, conserte o campo"*. Aqui o campo não mentia no
nome; mentia no conteúdo, que é a mesma doença.

### Consequência declarada

A UF passa a ser preenchida onde antes caía no adaptativo. Isso muda o
comportamento do corredor em telas que já funcionavam **por acidente** — elas
funcionavam porque o cérebro cobria o buraco. Agora respondem pelo passo
determinístico, que é mais rápido e não gasta chance.

**Autorização:** Founder autorizou a execução dos itens 3 e 4 da rodada de
05/08/2026 com "PODE FAZER... FAZER TUDO MUITO BEM FEITO". O conserto é
pré-requisito do item 4 aprovado — sem ele o guarda reprova endereço correto.
Registrado aqui por ser mudança de comportamento **fora** do texto da SPEC.

---

## CA-033 · O acervo tinha dois rótulos, e nenhum dizia o que o nome prometia — ESSENCIAL

**Data:** 05/08/2026 · **Branch:** `feat/spec063-atendimento-canais`

### O problema

📊 Medido no banco `dcajcvlzcjbmyapmklil`, 05/08/2026:

```
11.640 cartas em knowledge_cards
  category    = 'processo' em 100% delas — sem CHECK, texto livre, coluna morta
  insurer_key preenchida em 3.760, e só 1.083 (32,3%) das published etiquetadas
              citavam a própria seguradora no texto
```

`attendance_distiller._store_card_sync` gravava `meta.get("category") or
"processo"` — e ninguém nunca passou `category`. E carimbava a seguradora da
**sessão** nos até oito fatos que ela produzia, inclusive nos genéricos. O campo
guardava *"este fato apareceu numa conversa sobre a Allianz"* com o nome de
*"este fato é regra da Allianz"*.

### O que foi feito

1. **Parar de piorar.** A decisão "de quem é esta regra" virou uma função só —
   `curadoria_cartas.seguradora_do_fato` — e as **quatro** portas de escrita
   passam por ela: o destilador em runtime, `aplicar.py`, `aplicar_sql.py` e
   `atribuir_seguradora.py`. O atalho `_chave_da_seguradora` foi removido.
2. **Honestidade no que já existe.** 2.582 rótulos rebaixados para NULL, 20
   prestadoras movidas para `pii_check.prestadora`, e as 52 chaves distintas
   viraram 20 — todas seguradoras de verdade.
3. **O eixo do assunto.** `category` passou a valer cinco momentos do trabalho
   (`sinistro`, `cobranca`, `assistencia`, `apolice`, `atendimento`), calculados
   pela `assunto_da_carta` que já existia e agora é **persistida**.

### Por que é ESSENCIAL e não VALIOSA

O rebaixamento é seguro por construção — `build_global_search_kwargs` aceita
`carrier_slug` e o **descarta**, então não existe filtro por seguradora e uma
carta sem rótulo se comporta exatamente como antes. O que não pode esperar é o
contrário: **ligar o filtro sobre o acervo velho** faria dois terços das cartas
responderem sob a bandeira errada, e o dia de ligar o filtro é o dia em que
ninguém vai lembrar de conferir o acervo.

### Mudanças fora do texto que precisam de registro

- **`_INSURER_ALIASES` ganhou dez companhias** (`essor`, `ezze`, `chubb`,
  `generali`, `darwin`, `berkley`, `pottencial`, `sulamerica`, `unimed`) porque
  a tabela virou a **lista de quem é seguradora** — é ela que autoriza um valor
  em `insurer_key`. Efeito colateral desejado: `Sul America` deixou de virar a
  chave `sul` pelo fallback `raw.split()[0]`.
- **Prestadora não ganhou coluna.** Autoglass, Mondial, Crawford, Hantei e Ativa
  atendem várias seguradoras; em `insurer_key` fariam o filtro devolver a
  errada. Foram para `pii_check.prestadora` — a caixa de marcação que
  `corrigir.py` já usa e que `reconciliar_indice_sync` já lê em produção. Uma
  coluna nova que ninguém lê é a mesma doença que `category` tinha. A dívida
  está em **P-102** com o gatilho escrito: no dia em que alguém filtrar por
  prestadora, ela ganha coluna.
- **`curar_sync` paginava por `created_at`.** 📊 A destilação grava as até oito
  cartas de uma sessão no mesmo instante; paginar por chave que empata devolveu
  11.640 linhas com 11.628 hashes distintos. Trocado por `.order("id")`. Não
  estava no pedido — foi achado medindo, e uma curadoria que não vê a carta
  deixa a quase-cópia no RAG para sempre.

### Consequência declarada

O índice do Qdrant **não** foi refeito: o prefixo `(allianz / auto / cobranca)`
continua escrito dentro do chunk publicado, e o BM25 casa por termo exato. O
banco ficou honesto antes da busca. Registrado em **P-101** com o motivo de não
ter sido feito agora (outro agente está em `search_service`/`qdrant_service`) e
o custo de esquecer.

**Autorização:** Founder autorizou a execução do UPDATE em massa, em duas
etapas (previsão com amostra, depois gravação), na rodada de 05/08/2026.

---

## SPEC-070 LOTE 1 — o maestro do acervo (08/08/2026)

`backend/scripts/acervo/coletar_seguradora.py` executa a §9 do começo ao fim
para uma seguradora inteira. As três peças do LOTE 0 existiam e não estavam
ligadas. Quatro mudanças saíram do texto da SPEC:

### 1. ESSENCIAL — `knowledge_extras` por pedaço (`qdrant_service.py`)

A §5.3 pede `unit_id` e `faceta` **na raiz** do payload, e os dois mudam de
pedaço para pedaço. `insert_embeddings` só aceitava um dicionário igual para
todos os chunks; `metadata` já aceitava lista. Passou a aceitar as duas formas,
com a mesma simetria.

**Sem isso** `unit_id` só caberia em `metadata`, que o filtro não lê — e o
`unit_id` é o caminho de volta da carta destilada para o trecho de origem
(migration 03). Uma procedência que não se resolve é procedência falsa.

### 2. ESSENCIAL — a URL do registro oficial é um arquivo (`insurance_corpus.py`)

`_buscar` decidia baixar direto por `".pdf" in url`. A URL do REP2 é
`…/DownloadConsultaPublica/508497`, **sem extensão** — a fonte que a §3 declara
oficial caía no crawler, que renderiza HTML, gasta crédito do Firecrawl e não
devolve o PDF. O guarda estava recusando justamente a fonte que a SPEC manda
usar. 📊 Com a correção, o CG144 baixa em 1.223 ms, 1.601.187 bytes.

### 3. VALIOSA — o `egress_guard` carregável fora do contêiner (`susep_rep2.py`)

`app/core/__init__.py` importa `settings` na primeira linha, então
`import app.core.egress_guard` exigia `MINIO_ROOT_USER` e o resto do ambiente.
O `egress_guard.py` em si só usa a stdlib. Efeito: o levantamento **somente
leitura** da §9 (catálogo + REP2, nada escrito) não rodava fora de produção — e
a conferência da §3.2.1, que decide se um documento entra, só podia ser feita
no lugar onde ela já não impede nada. **Um controle que só roda em produção é
um controle que ninguém roda antes.**

Nada foi afrouxado: mesmo arquivo, mesma `EgressPolicy`, mesma lista de hosts;
só o caminho de importação muda, e se nem por ele carregar, a exceção sobe.

### 4. Dois testes atualizados (CLAUDE.md §9.3)

- `test_a_vigencia_mora_na_versao.py` procurava as migrations por
  `spec067_*`; elas foram renumeradas para `spec070_*` e o teste ficou
  vermelho na bateria — 📊 era o único vermelho de 208 antes deste trabalho.
- `test_o_contrato_da_allianz_nao_responde_pela_porto.py` lia os campos de raiz
  **dentro** dos parênteses de `insert_embeddings(...)`. Eles passaram a ser
  montados antes da chamada (mudança 1). A afirmação guardada não mudou —
  a etiqueta na raiz e o regulador sem etiqueta —, só o lugar. A fatia lida foi
  movida para *antes* da chamada de propósito: olhar a fatia inteira faria
  `metadata={..., "insurer_key": ...}`, que é justamente o que **não** sobe,
  satisfazer o teste com o defeito de volta.

### Consequência declarada

Nada foi indexado nem gravado. O que rodou de verdade foi o levantamento
read-only da Porto: 📊 31.871 produtos no catálogo, 71 de varejo, **68 com
versão vigente confirmada e 3 recusados** por formato de processo anterior a
2004 (P-140). O `--aplicar` continua exigindo `QDRANT_HOST` e
`OPENAI_API_KEY`, e recusa fora do contêiner.

**Autorização:** execução do LOTE 1 da SPEC-070, sessão de 08/08/2026.

---

## SPEC-070 · LOTE 1 (destilação) — 08/08/2026

Os três primeiros itens são do **mascarador de dado pessoal**, não do acervo.
Apareceram porque as 783 cartas destiladas das Condições Gerais da Porto foram
submetidas à mesma verificação que protege as cartas de atendimento — e a
verificação estava errada nas três frentes. Nenhum deles foi procurado: os dois
últimos vieram de **linha de controle** (CLAUDE.md §9.2).

### 1. BLOCKER — o valor do contrato era tratado como dado de uma pessoa

📊 36 das 783 cartas (5,0%) foram recusadas, todas por trazerem valor em reais:
*"Pequenos Reparos (10A/10B): o limite é de R$ 2.500,00 por vigência"*.

A regra que as barrava está certa **para conversa** — "sua franquia é de
R$ 2.480,00" é o caso de um segurado, e foi medida nos lotes 007/008. Numa
condição geral o mesmo número é o produto: está no contrato registrado na
SUSEP, vale para toda apólice que contratou a cláusula, é público, e **é a
pergunta que o corretor faz**. As barradas eram justamente as de `limite`.

Sem a ressalva só havia dois caminhos, e os dois perdem: recusar a carta, ou
publicar *"o limite é de {VALOR_RS}"* — pior, porque parece resposta e não é.

`templatize(valor_e_conhecimento=True)` reusa `_reservar`, o mecanismo que já
existia para "isto é conhecimento e não pode ser mascarado". **Quem liga é o
chamador, nunca o texto**: nenhuma heurística lê a frase e adivinha de quem é o
R$, e errar para o lado permissivo publica dado de cliente. O padrão é
desligado; só `publicar_cartas.py` — que sabe estar lendo um PDF da SUSEP — o
liga, e `publish_card_sync` o deriva de `source_unit_id`, ou seja, da
procedência.

### 2. BLOCKER — `Bom dia, <nome>` não era mascarado

A lista de gatilhos de saudação tinha `olá`, `oi`, `bem-vindo` e `prezado`, e
**não tinha a saudação mais comum do português brasileiro**:

    templatize("Olá, Maria Aparecida da Silva!")     → "Olá, {NOME} da Silva!"
    templatize("Bom dia, Maria Aparecida da Silva!") → passa inteiro

📊 Alcance: ZERO das 12.063 cartas publicadas contêm "bom dia" — a carta é um
fato destilado, não transcrição. Mas `templatize` também limpa o **mapa de URA**
(`ura_map_service.py:295`) e a **transcrição que vai para o prompt do
destilador** (`attendance_distiller.py:353`), e ali "Bom dia, Fulano" é o
primeiro turno de quase toda conversa.

**Como apareceu:** testando se a ressalva do item 1 tinha aberto buraco, o caso
do nome passou. A linha de controle — o mesmo texto com a ressalva DESLIGADA —
mostrou que ele já passava antes, e que era a cifra que vinha salvando aquele
caso **por acidente**. Sem o controle, eu teria creditado o furo à mudança do
dia e consertado o lugar errado.

### 3. BLOCKER — três nomes de ramo eram lidos como nome de rua

O miolo do padrão de logradouro aceitava `[^\n,;]{2,45}` — qualquer coisa entre
o tipo e um número. E **três dos tipos da lista são ramos do nosso produto**:
`residencial`, `condomínio`, `edifício`.

    "desistir do residencial da Porto em até 7 dias" → "desistir do {ENDERECO} dias"
    "a garantia … da Porto é de 90 dias"            → "a garantia {ENDERECO}"

📊 3 das 783 cartas destruídas assim, e a frase que sobra continua parecendo uma
carta — o formato pior, porque ninguém percebe que a resposta foi comida.

O conserto não encurta a regra: descreve melhor o que é nome de rua. Nome de
logradouro é feito de palavras capitalizadas ligadas por conectivo
(`Marechal Deodoro da Fonseca`), e **nunca termina em conectivo**. Uma frase tem
verbo e preposição em minúscula, e é isso que o miolo passa a recusar.

📊 CONTROLE: 17 endereços reais dos 27 lotes medidos continuam 100% mascarados.

### 4. ESSENCIAL — a carta do acervo leva procedência e faceta ao índice

`publish_card_sync` mandava ao Qdrant `insurer_key`, `ramo` e `card_category`.
A carta de conversa não tem origem única e por isso nasce sem `unit_id`; a carta
de condição geral tem origem exata. Sem `unit_id` no payload, o agente fica com
a afirmação e perde o lastro — e o lastro é o produto: é o que separa *"acho que
a Porto não cobre"* de *"a cláusula 4.4.2.d das Condições Gerais vigentes desde
01/07/2026 diz que não cobre"*. `faceta` entra junto, e já tinha índice.

### 5. ESSENCIAL — o título do documento carregava a versão, e mentia

📊 Dois dos seis documentos da Porto: o título dizia `(CG140)` e o arquivo era o
**CG144**; outro dizia `(abr/2025)` e a vigência era **31/07/2026**. O título é
congelado no cadastro e não muda quando a versão troca — então carregar versão
nele é garantir que ele envelheça errado (CLAUDE.md §12.1: conserte o campo, não
o texto). Os três títulos afetados foram limpos; a versão vive em
`version_label` e a vigência em `effective_from`.

**Achado por um subagente destilador**, que reparou na divergência entre o
briefing e o cabeçalho injetado nos 484 pedaços.

### Prova de mutação (CLAUDE.md §9.3)

`test_o_valor_da_condicao_geral_nao_e_de_ninguem.py`, 5 mutações, 5 pegas:

| mutação | o teste |
|---|---|
| desliga a ressalva do valor | reprovou (3) |
| tira `bom dia` da lista de saudações | reprovou (4) |
| miolo do logradouro volta a aceitar minúscula | reprovou (5) |
| miolo do logradouro volta a poder terminar em conectivo | reprovou (3) |
| liga a ressalva FIXA no publicador | reprovou (2) |

A quarta mutação **passou na primeira tentativa** e revelou lacuna do próprio
teste: as frases usavam "é de" com acento, e sem acento ("e de") são dois
conectivos seguidos de número — o casamento que comia a carta. Transcrição de
URA chega sem acento o tempo todo; os casos foram acrescentados.

📊 Bateria completa depois de tudo: **210 verdes, 0 vermelhos.**

**Autorização:** execução do LOTE 1 da SPEC-070, sessão de 08/08/2026.

---

## CA-034 · O recovery do Espelho virou um leitor permanente do proprio historico — **BLOCKER**

**Data:** 13/08/2026 · **SPEC:** 063 · **Branch:** `fix/p0-espelho-egress`
**Commits:** `51b5c0f` (Alavanca A) · `d9d17bb` (Alavanca B)

### Problema

📊 A organizacao Supabase foi restringida por Fair Use no ciclo 05/08 → 05/09:
cota Free de 5 GB, **6,98 GB consumidos**, overage de 1,98 GB. Producao passou a
responder **HTTP 402** em PostgREST, Storage e Auth. O portal-worker parou de
enxergar `portal_jobs` e a conclusao da MAPFRE ficou bloqueada.

### Evidencia

Medido em 13/08/2026 pela Management API do Supabase (que continua respondendo
apesar do 402 em PostgREST):

| Consulta (PostgREST) | calls | linhas/call | bytes/linha | atribuido |
|---|---:|---:|---:|---:|
| `messages(id, content, created_at, payload) LIMIT 40` | **771.313** | 33 | 290 | **~7.040 MB** |
| `users_v2(id, first_name, last_name)` | 776.542 | 1 | ~95 | ~70 MB |
| `conversations(id, status)` | 776.338 | 1 | ~60 | ~44 MB |
| `work_queue_outbox(*)` — resposta vazia | 712.971 | 0 | ~40 | ~27 MB |

As tres primeiras sao **exatamente** as tres consultas de `espelhar_no_chat`, em
contagens quase identicas: assinatura 1:1:1. A coluna `payload` **so existe
desde 06/08** (migration `20260806_01`), logo os 771.313 calls sao todos
posteriores ao Espelho. Primeira mensagem espelhada: **06/08 23:25 UTC**; o
salto do grafico de Egress e **07/08**. Nenhuma outra consulta do repositorio
usa aquele conjunto de colunas.

**O numero que resume:** 771.313 leituras de `messages` produziram **5.681**
mensagens espelhadas — **136 leituras por escrita**. 99,3% do trabalho foi
descobrir que a mensagem ja estava la.

Hipoteses **refutadas por medicao**: Realtime (zero tabelas publicadas em
`supabase_realtime`) · Storage/midia (94 objetos, 11 MB) · banco cheio (241 MB)
· RAG/Qdrant (servico separado, nao gera Egress Supabase).

Achado que muda a correcao obvia: 776.542 calls ÷ 6,77 dias ÷ 4.008 linhas por
ciclo = **~28,6 ciclos/dia**, ou um ciclo a cada ~50 min — nao a cada 10. Com
`max_instances=1` o agendador ja descartava 4 de cada 5 disparos. **Aumentar o
intervalo nao reduziria o Egress em nada**: o laco ja estava saturado.

### Consequencia se nao corrigido

O custo e `(linhas na janela) × (mensagens por conversa)`. As duas crescem com o
trafego: e quadratico. Fazer o Upgrade para Pro sem corrigir apenas moveria o
teto — e no primeiro boot pos-desbloqueio dezenas de componentes em 402 voltam
ao mesmo tempo, com o sync retomando saturado.

### Mudanca executada

**Alavanca A** — a leitura de 40 mensagens servia duas perguntas e pagava o
preco da mais cara para responder a mais barata. Dedup passa a ser
`INSERT` + indice unico (que ja era a garantia definitiva; o Python era atalho
declarado). Eco so e consultado quando `direcao=="out"`, com texto, e a mensagem
tem menos de 300s — filtro por `created_at`, sem filtro JSON.

**Alavanca B** — marca d'agua duravel por corretora no relogio de **ingestao**
(`created_at, id`), com atraso de seguranca de 5 min, cursor que nao avanca
sobre erro, e partida a frio em `now()` (nunca varredura). Kill switch
`ESPELHO_SYNC_ENABLED`, que **nasce desligado**.

**Migration `20260813_01`** — expand-only: tabela `espelho_sync_cursor` +
indice `(company_id, created_at, id)` + seed em `now()`.

### Fora de escopo, registrado aqui

| Achado | Classificacao | Onde |
|---|---|---|
| `.select("*")` em `integrations` traz `token` pela rede a cada webhook (94.833 calls) | **ESSENCIAL** — bloco proprio, com inventario de consumidores e teste | CA-035 |
| Polling do outbox a cada 2s com `pending=0` (712.971 calls, ~27 MB) | **VALIOSA** — backoff adaptativo com jitter | CA-036 |
| `ix_attendance_transcripts_lookup` nao atende ao access pattern incremental | resolvido pelo indice novo; o antigo **permanece** (serve outro consumidor) | — |
| Guarda SEC-05 aponta para tela que mudou de casa | pre-existente, sem exposicao real | P-124 |

### Autorizacao

Founder, 13/08/2026, apos duas rodadas de revisao independente:
*"PODE EXECUTAR O PLANO com os guardrails acima."*

Duas correcoes vieram da revisao e evitaram regressao real: o cursor por
`wa_timestamp` (perderia 99,89% das linhas `history_sync`) e a proibicao de
rodar codigo antigo em producao como linha de controle.

---

## CA-035 · `.select("*")` em `integrations` carrega segredo pela rede — **ESSENCIAL**

**Data:** 13/08/2026 · **Estado:** REGISTRADA, nao executada

📊 `get_integration_by_webhook_token` e mais 4 caminhos usam `.select("*")`.
O contador registra **94.833** chamadas de `integrations(instance_id, token)` e
**21.079** de `integrations(*)`. Cada webhook traz `token` e credenciais pela
rede sem precisar delas.

**Nao e problema de Egress** (poucos bytes) — e superficie de **seguranca**.

Nao executado neste P0 por decisao do Founder: reduzir `.select("*")` parece
trivial e pode quebrar chamadores que dependem implicitamente de um campo.
Exige bloco proprio, com inventario de consumidores e teste.

---

## CA-036 · Outbox consulta o banco a cada 2s para achar zero — **VALIOSA**

**Data:** 13/08/2026 · **Estado:** REGISTRADA, nao executada

📊 712.971 chamadas de `work_queue_outbox(*) WHERE status='pending'`, com
`pending_all = 0` medido no banco. ~27 MB — **0,4% do Egress do ciclo**.

**Nao e a causa do P0.** E desperdicio real de requests, nao de bytes.

Proposta (nao executada): backoff adaptativo quando vazio, com reset imediato ao
surgir trabalho e jitter, preservando SLA e durabilidade. **Nao criar segunda
fila. Nao tornar Redis fonte de verdade.**

---

## CA-039 · Republicar uma carta apagava o lastro dela — **BLOCKER**

**Data:** 15/08/2026 · **SPEC:** SPEC-072 Bloco 0 · **Estado:** EXECUTADA
**Autorizacao:** decisao do Founder, item 1 da ordem de execucao da SPEC-072
(*"20 MINUTOS, ANTES DE TUDO"*), apos auditoria + juiz critico independente.

⚠️ **CA-037 e CA-038 estao reservados** pelas decisoes 3 e 4 do Founder (excecao
documental no prompt · regra de uso de carta no `ATTENDANCE_BASE_PROMPT`), ambas
do Bloco 4. Este registro toma o numero seguinte para nao ocupar os dois.

### Problema

`insert_embeddings` faz `client.upsert` de **ponto inteiro**
(`backend/app/services/qdrant_service.py:355`), nao `set_payload`. Republicar uma
carta com menos payload nao acrescenta: **substitui**. Logo o `select` de quem
republica e a lista do que sobrevive — e duas colunas nao estavam nela.

Tres caminhos chamam `publish_card_sync`, e dois liam a carta incompleta:

```
reindexar_acervo.py:157    id, card_text, insurer_key, ramo, category
curadoria_cartas.py:1066   id, card_text, insurer_key, ramo      ← roda SOZINHO
admin_atlas.py:724         select("*")                           ← completo
```

E a `faceta` se perdia nos **tres**, inclusive no que usa `select("*")`:
`knowledge_cards` nao tem coluna `faceta`, entao `publicar_cartas.py:332` a grava
dentro do jsonb `pii_check` — e `publish_card_sync:659` lia `card["faceta"]`, uma
chave de topo que so existe na primeira publicacao.

### Evidencia

📊 Medido em 15/08/2026 sobre as 5.394 cartas de acervo `published`, rodando a
rede de PII real (`curadoria_cartas.veredito_de_pii`), nao uma reimplementacao:

```
RECUSADAS com documento_publico=False (o que rodava)   57
RECUSADAS com documento_publico=True  (o correto)       0
                                                       --
regressao silenciosa                                    57 cartas
```

As 57 sao **todas da HDI** e **todas por `{CNPJ}`** — e o `{CNPJ}` e o numero de
**processo SUSEP** (`15414.900228/2017-63`), que so parece CNPJ para quem nao sabe
que o documento e publico. `publish_card_sync:571` decide isso com
`documento_publico=bool(card.get("source_unit_id"))`, e a coluna nao vinha no
select.

E as outras **5.337** voltariam ao indice sem `unit_id` e sem `faceta`. Alvo de
um `--aplicar`: **100% das 5.394**.

### Consequencia de nao fazer

O Bloco 2 da SPEC-072 produz cartas de documento com lastro. A rodada seguinte
do reindexador as desmontaria — e `publicar_lote_sync`, que roda sozinho a cada
rodada do Destilador, faria o mesmo sem ninguem pedir. O indice de payload
`faceta` (`qdrant_service.py:96`) ficaria apontando para nada.

O modo de falha e o pior: o script conta as 57 como `falhou` e segue. O nome no
relatorio seria `rejected_pii` — que **mente**: nao vazou dado de ninguem.

### Mudanca

1. `attendance_distiller.publish_card_sync` resolve a faceta de `card["faceta"]`
   **ou** de `card["pii_check"]["faceta"]`. Um lugar conserta os tres chamadores
   em vez de repetir a linha em cada um (CLAUDE.md §5 — consolidar, nao duplicar).
2. `reindexar_acervo._ler_publicadas` e `curadoria_cartas.publicar_lote_sync`
   passam a pedir `source_unit_id, pii_check` (e o segundo recupera `category`,
   que tambem faltava).
3. `backend/tests/test_a_republicacao_nao_apaga_o_lastro.py` — comportamental,
   com linha de controle em cada caso (§9.2) e prova de mutacao (§9.3).
4. `test_o_valor_da_condicao_geral_nao_e_de_ninguem.py:411` estava **vermelho
   desde `0a8282a`**: afirmava `"MAX_CARACTERES = 1800" in publicador`, e a regua
   mudou de dono para `curadoria_cartas`. A licao migrou e ficou mais forte —
   agora guarda que **existe um dono e ninguem mais escreve o numero**.

### Custo e risco

Nenhuma migration, nenhum dado tocado, nenhum motor novo. Risco de egresso: o
`select` passa a trazer `pii_check` por carta — jsonb pequeno, e o reindexador
roda sob demanda, nao em laco.

**VERIFY (saida real):**

```
suite baseline (worktree isolado no HEAD)   197 verdes · 21 vermelhos
suite depois                                201 verdes · 18 vermelhos
vermelhos NOVOS                             NENHUM
vermelho herdado consertado                 test_o_valor_da_condicao_geral_*

mutacao (source_unit_id fora do select)     EXIT=1   ← o guarda falha
restaurado da copia                         EXIT=0
```

**ROLLBACK:** `git revert` dos quatro arquivos. Nada de banco foi alterado, e o
valor da faceta continua gravado em `pii_check` como sempre esteve.

### 📊 Addendo do juiz critico — o que ele derrubou, e o que sobrou

O conserto acima passou por juiz adversarial (instruido a REFUTAR, nao a
aprovar). Ele confirmou o defeito e a correcao, e **derrubou o conserto do teste
herdado**. Registrado porque o erro e instrutivo:

**REFUTADO — a licao tinha migrado para o arquivo errado.** A guarda nova varria
`publicar_cartas.py` atras do literal escrito a mao. Mas 📊
`test_a_regua_da_carta_e_uma_so.py:8-11` diz textualmente que as quatro copias
viviam em `attendance_distiller`, `aplicar.py`, `aplicar_sql.py` e
`atribuir_seguradora.py` — e que **`publicar_cartas.py` usava 40–1800, ou seja,
era o que estava CERTO**. A guarda nao tinha como pegar o defeito que dizia estar
pegando. Agora varre os **cinco** pontos de ingestao, com regex que tambem pega
`MAX_CARACTERES=400` sem espaco e `MAX_CARACTERES: int = 400`.

**REFUTADO — substring nao e valor.** `"MAX_CARACTERES = 1800" in fonte` e
satisfeito por um **comentario**, e o arquivo tem centenas de linhas que citam a
regua. Agora o teste carrega o modulo e afirma `C.MAX_CARACTERES == 1800`.

**REFUTADO — o conserto nao era observavel.** `test_o_valor_da_condicao_geral_*`
nao tinha `sys.stdout.reconfigure`, que os dois irmaos do diretorio tem. Em
console cp1252 ele morre de `UnicodeEncodeError: '\u2192'` no bloco **[3]**,
antes de chegar ao **[6]**, que e o bloco editado. Verde so com
`PYTHONIOENCODING=utf-8` na mao. **Um conserto que nao pode ser observado nao
foi observado.** A linha entrou.

**Prova de mutacao dos guardas novos** (com copia de arquivo, nunca
`git checkout`):

```
teto 1800 -> 1500 em curadoria_cartas.py         EXIT=1  <- o guarda falha
MAX_CARACTERES=400 (sem espaco) em aplicar.py    EXIT=1  <- o guarda falha
restaurado                                        EXIT=0
```

**REFUTADO — os 📊 nao eram reproduziveis.** Os cinco numeros sairam de um script
que morava so no `%TEMP%` da sessao. Mesma critica que esta SPEC fez aos numeros
antigos dela. Corrigido: **`backend/scripts/destilacao_max/medir_o_lastro.py`**,
versionado, somente leitura, reproduz os cinco a partir do repositorio.

**Dois reparos no teste novo:** (1) `"faceta" not in (c or {})` era satisfeito
quando a carta era RECUSADA — agora `c is not None` vem primeiro; (2) a ancora do
select de `reindexar_acervo` pegava o primeiro `.select(` do arquivo e acertava
por acidente (ha quatro; o de `_diagnostico` so escapava por ter `count=`
quebrando o regex) — agora ancora na funcao, como a outra.

**Limite declarado, nao escondido:** o teste afere os **kwargs** entregues a
`insert_embeddings`, nao o payload final montado em `qdrant_service.py:306-330`.
A regra de promocao de `:329` fica inexercitada. Um guarda dela pertence a um
teste de `qdrant_service`.

### ⚠️ A ressalva desta entrega

**"Republicar nao apaga mais o lastro" vale para os cinco chamadores de
`publish_card_sync`. NAO vale para o Postgres.**

`scripts/destilacao_max/corrigir.py:85` tem o mesmo defeito uma camada abaixo, e
la a autoridade e **duravel**: o `select` sem `pii_check` faz o `update` de
`:118-120` substituir a coluna inteira. E a carta **substituta** (`:124-132`)
nasce sem `source_unit_id`. **Nao consertado nesta entrega, por decisao de
escopo do Founder** — registrado em **P-176**, com as duas metades separadas por
gravidade.

E **P-177**: `temas` nao chega ao indice em caminho nenhum, o que torna
inexecutavel a promessa da §4 da SPEC ("achavel por faceta + insurer_key +
temas"). Pertence ao Bloco 1 (o leitor), e esta escrito la.

### ✅ 15/08/2026 — a ressalva CAIU: P-176 consertada por decisao do Founder

> *"1 linha, mesma familia, e sem ela o titulo do seu commit e falso: 'republicar
> nao apaga o lastro' valeria para o indice e nao para o Postgres, que e o
> duravel."* — decisao do Founder, 15/08/2026.

⚠️ Este arquivo e **append-only** (§2.1): a ressalva acima nao foi editada nem
removida. Ela fica como registro do que era verdade quando foi escrita, e esta
nota diz o que mudou — que e a mesma disciplina do CLAUDE.md §9.3 aplicada a
documento em vez de a teste.

**O conserto**, em `backend/scripts/destilacao_max/corrigir.py`:

- o `select` de `:85` passa a pedir `pii_check, source_unit_id,
  source_document_id, source_version_id`
- a carta **substituta** herda as tres colunas de procedencia e a `faceta`

⚠️ **Sao TRES colunas, nao uma** — e isso nao estava na P-176. `20260808_03_
spec070_a_carta_sabe_de_que_contrato_saiu.sql:154-159` criou a FK composta
`knowledge_cards_procedencia_coerente_fk (source_version_id,
source_document_id)`. Propagar so o `unit_id`, como a pendencia sugeria, daria
uma carta com **endereco e sem documento** — coerente na aparencia, incoerente no
schema.

`origem` fica de fora de proposito: ela descreve de que RODADA a carta veio, e a
substituta veio desta correcao, nao daquela.

**Teste:** `backend/tests/test_corrigir_nao_perde_a_procedencia.py` — dubla o
Supabase e afere o que o script GRAVA, com linha de controle (a mesma carta sem
procedencia: a nova nao inventa nenhuma) e mutacao (a linha que o `select` de
ontem devolvia faz os guardas reprovarem).

**Com isto, "republicar nao apaga o lastro" vale para os cinco chamadores de
`publish_card_sync` E para o Postgres.**

---

## CA-040 · Dois rotulos com escritor e sem leitor ganham filtro — **ESSENCIAL**

**Data:** 15/08/2026 · **SPEC:** SPEC-072 Bloco 1 · **Estado:** EXECUTADA
**Autorizacao:** decisao do Founder — *"P-177 SOBE PARA DENTRO DO BLOCO 1. Nao
abra bloco novo. O Bloco 1 ja constroi o filtro; ele passa a cobrir DOIS campos."*

⚠️ **CA-037 e CA-038 seguem reservados** para a excecao documental no prompt e
para a regra de uso de carta no `ATTENDANCE_BASE_PROMPT` (Bloco 4).

### Problema

`faceta` e `temas` eram **write-only**, e por motivos diferentes:

```
faceta   escritor desde 08/08 (insurance_corpus:1169, attendance_distiller:686)
         indice de payload KEYWORD ja existia
         LEITOR: nenhum. Sem _filtro_de_faceta, sem param em search_similar,
         sem kwarg em build_global_search_kwargs.                      (P-142)

temas    14.264 cartas rotuladas em 15/08, coluna text[] + indice GIN criados
         na mesma noite
         ESCRITOR de payload: nenhum. INDICE no Qdrant: nenhum. LEITOR: nenhum.
         `grep temas search_service.py qdrant_service.py` -> ZERO       (P-177)
```

O `temas` era o mais grave dos dois: a `faceta` ao menos **chegava** ao indice.

### Evidencia

📊 `backend/tests/test_o_filtro_de_faceta_tem_dois_bracos.py`, saida real:

```
so o filtro de FACETA salva  12.534 cartas + 1.139 trechos de contrato
so o filtro de TEMA   salva   4.083 cartas + 6.797 trechos de contrato
CONTROLE: sem pedido          nenhum ponto some (24.725 de 24.725)

MUTACAO — tirar o braco "OU ausente":
    dois bracos  11.252 pontos
    um braco so   1.798 pontos
    APAGADOS      9.454
```

### Mudanca

1. `_filtro_de_faceta` e `_filtro_de_temas` em `qdrant_service.py`, **espelhados
   literalmente** nos dois irmaos. ⚠️ Nao generalizados num helper de proposito:
   tres testes afirmam substrings sobre o corpo de `_filtro_de_seguradora` e
   `_filtro_de_namespace` (`"should=["`, `"IsEmptyCondition"`, `"if not slug:"`,
   `count("return None") >= 2`), e um refactor generico os derrubaria. Repetir e
   o certo aqui: o guarda mora na forma.
2. Params `faceta`/`temas` em `search_similar`, aplicados em `must_conditions`.
3. `("temas", PayloadSchemaType.KEYWORD)` em `_INDICES_DE_PAYLOAD` — filtro sem
   indice nao e filtro, e varredura.
4. **Escritor** de `temas` em `publish_card_sync`, e `temas` nos selects dos dois
   republicadores.
5. `faceta_da_pergunta()` e `temas_da_pergunta()` em `knowledge_scope.py`.
6. `build_global_search_kwargs` monta as duas chaves, e os **DOIS** caminhos
   globais passam a chamar (`search_service.py` e `langchain_service.py`).

⚠️ Os itens 2 e 5 tinham de entrar no MESMO commit: o retorno de
`build_global_search_kwargs` e splatado com `**`, e um kwarg sem parametro vira
`TypeError` — que os dois services ENGOLEM num `except Exception`, matando
**todos** os resultados globais em silencio.

### A decisao de projeto, e ela e a parte que merece revisao

📊 `faceta_da_pergunta` reconhece **1 das 8 facetas**; `temas_da_pergunta`, **1
dos 24 temas**. Nao e provisorio por preguica:

**`escopo` e `exclusao` sao um PAR.** O proprio payload documenta a intencao —
*"e por ela que a busca EQUILIBRA a resposta, para a cobertura nao voltar sem a
exclusao que a anula"*. Filtrar *"a apolice cobre vidro?"* por `faceta='escopo'`
esconderia a clausula que a anula: seria usar o rotulo para ESTREITAR quando ele
existe para EQUILIBRAR, e o defeito seria invisivel — a busca devolve resultado,
so que meio.

`documento` entra porque e a unica pergunta fechada: nao existe clausula que
anule uma lista de documentos.

As outras sete "provavelmente" servem, e "provavelmente" e o que a **P-145**
proibe: la um sinal por faceta foi implementado, MEDIDO contra 19 erros
confirmados e recusado (3 acertos, 19 falsos alarmes). *"Um sinal que grita mais
do que acerta ensina o proximo a ignorar sinal."* Sem dados novos, `None` — que
e o comportamento de hoje e nao esconde nada.

**O que destrava as outras sete:** medir, por faceta, quantas respostas melhoram
e quantas pioram, com linha de controle.

### Custo e risco

Nenhuma migration. Nenhum dado tocado. Nenhum motor novo — o filtro entra no
`search_similar` que ja existia, ao lado dos dois irmaos.

**VERIFY:** suite **203 verdes / 18 vermelhos**, contra 202/18 antes (o +1 e o
teste novo). Vermelhos NOVOS: **nenhum**. Os tres testes que afirmam substrings
sobre os filtros irmaos seguem verdes.

**ROLLBACK:** `git revert`. Os filtros sao aditivos e so entram quando a pergunta
pede; `faceta=None`/`temas=None` devolve exatamente o comportamento anterior — e
ha teste de controle provando isso.

### 🔴 15/08/2026 — O JUIZ DERRUBOU A FIACAO. O `must` CONFLITA COM O CANON.

O CA-040 acima foi submetido a juiz adversarial e **a parte que ligava o filtro
na busca global nao sobreviveu**. A entrega foi revertida na mesma sessao, antes
de qualquer deploy. Registrado aqui porque o erro e de PROJETO, nao de codigo, e
o proximo a ler precisa do motivo.

**O conflito, literal.** SPEC-070 §5.1:304-305:

    "Nao casou nenhuma -> `faceta = null`. E `null` passa em todo filtro, NUNCA
     ELIMINA. Rotulo da COTA E PRIORIDADE; so fato verificavel (seguradora,
     vigencia, documento) elimina candidato."

Um `must` faz o rotulo **eliminar**. Eu li o aviso de P-142 sobre os dois bracos,
implementei os dois bracos, e conclui que estava protegido. Estava protegido
contra o caso ERRADO.

**📊 O que a medicao mostrou, e ela e devastadora para o desenho:**

```
faceta AUSENTE nas 5.396 cartas do acervo ........ 0   (ZERO)
```

O braco `IsEmptyCondition` protege quem **nao tem** rotulo. No acervo — que e a
populacao inteira desta SPEC — **todo mundo tem**. La o filtro vira um
`faceta == 'documento'` duro que esconde as outras 5.016 cartas.

O caso concreto que fecha o argumento, medido em `porto/auto_CARTAS.jsonl`,
`faceta='exclusao'`:

    "nao ha cobertura se quem dirigia estava sem habilitacao legal, ou com a
     CNH suspensa, cassada, vencida"

E exatamente o que o segurado precisa ouvir ao perguntar sobre documentos. Um
filtro `faceta='documento'` a esconde.

**E o segundo defeito, que e meu e da SPEC ao mesmo tempo:** os dois rotulos
entravam no MESMO `must`, virando um AND. 📊 `faceta` e `temas` discordam em
**47%** — so 201 das 380 cartas com `faceta='documento'` tem o tema
`documentacao`. A propria SPEC-072 §7 lista isso como risco aberto e o §Bloco 6
manda "reconciliar ANTES do backfill". **Eu liguei o AND antes da reconciliacao
que a minha propria SPEC exige.**

⚠️ E o teste nao pegava, porque a FIXTURE correlacionava os dois rotulos em
100%. Corrigida para discordar, ela agora mede o estrago e o teste o afirma.

### O que ficou, e o que saiu

```
FICA   _filtro_de_faceta / _filtro_de_temas    corretos, dois bracos, testados
FICA   params em search_similar                aditivos, so agem se pedidos
FICA   ("temas", KEYWORD) no indice
FICA   ESCRITOR de temas                       + o 4o escritor, publicar_cartas.py
FICA   faceta_da_pergunta / temas_da_pergunta
SAI    a fiacao em search_service e langchain_service
```

A infraestrutura fica **pronta e inerte**. Ninguem perde carta, e nada precisa
ser reescrito quando a forma certa for decidida.

### A FORMA CERTA — proposta, nao executada (🧑 decisao do Founder)

O canon ja descreve o mecanismo: **cota e prioridade**. E a arquitetura ja tem
onde — `ORCAMENTO_GLOBAL` roda uma busca por faixa com orcamento proprio.

    ORCAMENTO_GLOBAL = (
        ("normativo", ["normative"], 12),
        ("cartas",    ["cards", "canon"], 12),
        ("documento", ["normative", "cards"], 6),   <- NOVA, so quando a
    )                                                  pergunta pede faceta

Uma terceira linha, com `faceta=<pedida>` e cota propria, **ACRESCENTA** cartas
de documento sem **REMOVER** nenhuma. O `merge_rag_results` dedupe, e
`selecionar_com_cota` ja sabe dividir vagas por balde.

⚠️ Custa um `search_similar` a mais por pergunta documental (mesmo embedding),
e exige um balde novo em `COTA_FINAL`. Nao executei: e mudanca de arquitetura de
busca, e a CLAUDE.md §10.3 manda parar e registrar em conflito canonico.

### O resto do veredito do juiz, aceito e corrigido

- **`publicar_cartas.py:381`** era um QUARTO escritor, esquecido por nao ter
  select: monta o dict a mao e nao passava `temas`. E republica toda carta em
  toda rodada. Corrigido — e o valor vem de `res.data[0]` (a linha que o
  PostgREST devolve), nao de `linha`, que e o dict de ESCRITA e nunca teve
  `temas`. Ler de `linha` daria `None` sempre e o conserto seria so aparencia.
- **Comentario falso** em `_filtro_de_temas`: eu afirmei que `IsEmptyCondition`
  nao alcanca `[]`. Alcanca — a doc do Qdrant diz "does not exist, or has `null`
  or `[]` value". O proprio teste ja contradizia. Corrigido, com o motivo real.
- **Duas guardas mortas** em `knowledge_scope`: o ramo `len(apelido) < 6` nunca
  executa (o menor apelido tem 9 chars) e `len(achadas) == 1` nunca desempata
  (todos os valores mapeiam para um so). Ficam — a segunda faceta as acorda —
  mas a docstring passou a dizer que estao INERTES, em vez de vende-las como
  garantia.
- **Uma tautologia no teste** (`len(juntos) <= min(...)`, impossivel de falhar
  com `must` = `all()`) trocada pela medicao do AND.
- **Nomes que mentiam:** `apagados_faceta`/`apagados_tema` contavam
  SOBREVIVENTES, e o print afirmava o oposto. Renomeados para `salvos_*`.
- **`_casa()` ignorava `must_not`**, ficando mais permissivo que o Qdrant.
  Corrigido.

**VERIFY apos as correcoes:** 203 verdes / 18 vermelhos, lista identica.

---

## CA-037 · A excecao documental no prompt de atendimento — **ESSENCIAL**

**Data:** 16/08/2026 · **SPEC:** SPEC-072 Bloco 4 · **Estado:** EXECUTADA
**Autorizacao:** decisao do Founder, 15/08/2026 — *"AUTORIZADO registrar e
executar dentro da SPEC. E atualize o teste do 'Maximo 4', que afirma o
literal."*

### Problema

`prompts.py:95-100` manda *"peca num bloco de ate 4 itens, numerados… Maximo 4
itens… pergunta DELICADA (…, documento pessoal) NUNCA entra em bloco"*.

📊 A medicao diz o contrario para o caso documental: o pedido padrao da atendente
tem **5 itens** e o segurado responde; a **CNH entra em bloco em 100%** dos casos
observados; e **numerar e o que as humanas NAO fazem** (0,2%).

A regra e defensavel para PERGUNTA e errada para LISTA DE DOCUMENTOS. Uma lista
partida em blocos de 4 e meia lista, e 📊 o proprio acervo registra o custo: *"sem
isso o segurado vai ao orgao, volta sem o papel certo e o processo perde dias a
cada ida."*

### Mudanca

Excecao NOMEADA, nao revogacao. `### 📄 A EXCECAO DOCUMENTAL` entra logo abaixo
da regra geral e diz cinco coisas: a lista vai INTEIRA numa mensagem; documento
pessoal ENTRA nela; os dificeis vem com ONDE PEGAR; fecha com O QUE TRAVA; e ao
receber, o agente ECOA o que chegou e o que falta. E `documento pessoal` saiu da
lista de perguntas delicadas do bloco geral — manter nos dois lugares deixaria o
modelo escolher qual obedecer.

⚠️ **O teste tinha de mudar junto com o fato.** Ele passava IGUAL antes e depois
da excecao existir, porque afirmava so a palavra `DELICADA`. Um guarda que nao
distingue os dois estados do produto nao e guarda (CLAUDE.md §9.3). Agora afirma
as cinco clausulas, e a mutacao (tirar "CNH ENTRA na lista") o derruba.

---

## CA-038 · O atendimento nao sabia o que e uma carta de conhecimento — **ESSENCIAL**

**Data:** 16/08/2026 · **SPEC:** SPEC-072 Bloco 4 · **Estado:** EXECUTADA
**Autorizacao:** decisao do Founder — *"AUTORIZADO, e sobe para dentro do BLOCO
4. Voce tem razao: e maior que os Blocos 3 e 4 somados."*

### Problema

📊 `ATTENDANCE_BASE_PROMPT` (prompts.py:83-208) RECEBE as cartas do RAG global
(`graph.py:1220-1231`, sob `=== 📚 CONTEXTO RECUPERADO ===`) e **nao tinha
nenhuma instrucao sobre elas**. A regra *"nunca copie o texto da carta; carta e o
que costuma acontecer, nao garantia contratual"* existia so no
`CORE_BASE_PROMPT:30-31` — o do CORRETOR.

O unico papel que fala com o SEGURADO era o unico sem a regra. Entregar a lista
perfeita a um prompt que nao sabe disso e otimizar o abastecimento de um cano
solto.

### Mudanca

Uma linha SOMADA ao bloco `🛡️ LIMITES INEGOCIAVEIS`, ao lado da regra que ja
proibia confirmar cobertura sem evidencia — **nao um bloco novo**. A ressalva do
juiz era essa: `:201` ja existia, e duplicar teria criado duas regras vizinhas
sobre o mesmo assunto.

Diz quatro coisas: a carta NAO e a apolice dele; serve para ORIENTAR e nunca para
AFIRMAR cobertura/valor/franquia; nao se copia o texto; e **discordando, a
APOLICE vence**.

### Custo e risco

Texto de prompt, revertivel por `git revert`. **VERIFY:** 204 verdes / 18
vermelhos, lista identica. Mutacao: EXIT=1 mutado, EXIT=0 restaurado.

---

## CA-041 · Os seis P1 de segurança do Portal Worker — **ESSENCIAL**

**SPEC-073 · autorizado pelo Founder em 16/08/2026 (resposta Q2)**

### Problema

A auditoria de readiness da SPEC-073 mediu seis defeitos de segurança
operacional que **não estavam no texto da SPEC**. Todos com a mesma assinatura:
uma proteção que existe em um lugar e falta no lugar irmão.

| # | Achado | Evidência |
|---|---|---|
| 1 | Yelum busca com `{"brokerlist": []}` e descarta o `BrokerName` de cada linha | `yelum_corretor.py:542`, `:227`; zero `account_label` no arquivo |
| 2 | Tokio captura `nomeParceiroNegocioPrimario` e nunca compara | `tokio_corretor.py:501-509` |
| 3 | Zurich pula a revalidação quando o rótulo é `principal` — o default do dashboard | `zurich_corretor.py:705` × `portal-credentials/route.ts:67` |
| 4 | `account_id` buscado só por `id`; o `company_id` vinha no SELECT e nunca era comparado | `worker.py:424-430` |
| 5 | `stale_running_patch` e o botão de retry do dashboard reexecutam job pós-efeito | `worker.py:83-101`, `hitl.ts:58` |
| 6 | `GLOBAL_KILL_SWITCH` lido só pelo Next.js | `grep -rn GLOBAL_KILL_SWITCH backend/` → vazio |

### Autorização

O Founder aprovou incluí-los na SPEC-073, com a regra: *"corrigir agora tudo que
possa gerar cross-tenant, duplicidade, side effect incorreto ou incapacidade de
parar a execução"* — e **não** transformar a SPEC numa limpeza geral de
segurança.

### O que ficou de FORA, deliberadamente

Rotação de `PORTAL_VAULT_KEY` (chave única global, sem key-id) · retenção LGPD
de `portal_jobs.evidence` · remoção da pilha TypeScript morta · rate-limit e
tenant-binding do endpoint interno. Registrados em PENDENCIAS P-182 a P-185.

### Custo e risco

MAPFRE **não** foi tocada: é o único guarda cross-tenant provado, tem teste com
duas carteiras disjuntas, e reescrevê-la para "unificar" trocaria certeza por
elegância. A generalização foi extraída para `identidade.py` e aplicada às três
que não tinham nada.

**VERIFY:** 211 verdes / 17 vermelhos no backend inteiro; os mesmos 17 medidos
como já-vermelhos na baseline `5cac02f`, um a um. Mutação: 6 guardas quebrados
de propósito, 5 detectados de imediato, o 6º expôs uma lacuna do próprio teste,
corrigida.

---

## CA-042 · A tela escondia quatro seguradoras prontas — **ESSENCIAL**

**SPEC-073 · autorizado pelo Founder em 16/08/2026 (resposta Q3)**

### Problema

📊 `app/dashboard/auxiliares/rotinas/page.tsx:62` mantinha
`PORTAIS_COM_COBRANCA = ['allianz_corretor', 'hdi_corretor']` enquanto
`portais_com_cobranca()` já derivava SEIS do registry. Tokio, Yelum, MAPFRE e
Zurich tinham journey completa, testada e **invisível** para a corretora.

O comentário no código admitia a duplicação como deliberada. A intenção era boa;
o resultado não: duas listas que precisam concordar sempre acabam discordando.

### Decisão

Não acrescentar quatro nomes ao array — **apagar o array**.

A disponibilidade passa a vir de `/api/portal/cobranca-capabilities`, que
devolve a **interseção** entre o que o registry sabe fazer (`registry`) e o que
a imagem no ar realmente carrega (`deployed`, lido do `/health` do
portal-worker).

### Por que a interseção, e não só o registry

📊 A P-149 registra a journey da MAPFRE existindo no repositório e **não** na
imagem implantada — um job dela termina em *"journey desconhecida"* com todos os
testes verdes. Marcar a MAPFRE como pronta por causa do registry seria repetir a
mentira em outro lugar. Ela só aparece quando a P-149 for implantada.

### Fail-closed

Sem conseguir falar com o portal-worker: `degraded=true`, nenhum portal
operacional, e a tela **diz por quê**. Dizer "não consegui confirmar" custa uma
tentativa; dizer "está pronto" sem estar custa um job que morre em produção.

### Custo e risco

Rotina já existente mantém exatamente os portais que a corretora escolheu — uma
seguradora nova entrando no registry não liga a cobrança de ninguém sozinha.
`tsc --noEmit` limpo.

---

## CA-043 · O roteador de canal de vidros saiu de quatro lugares para um — **ESSENCIAL**

**SPEC-074** · 16/08/2026 · autorizado pela SPEC-074 §9 (fluxo ponta a ponta)

### Problema

A decisão *"isto vai para o portal de vidros ou é sinistro?"* estava escrita em
quatro lugares independentes: o prompt de atendimento, o `insurer_dispatch_tool`,
o `portal_tool` e o playbook. Quatro autores, quatro critérios, nenhum
verificável.

📊 O caso que expõe: *"quebrei o vidro na colisão"* contém as duas palavras.
Quem inclui antes de excluir manda ao portal de vidros um caso que precisa de
regulação de sinistro.

### Decisão

`services/vidros_flow.resolver_canal()` passa a ser a regra única, e a **exclusão
vem antes da inclusão**. A SPEC-074 pedia o fluxo ponta a ponta; consolidar a
decisão em vez de escrever a quinta cópia é o que a CLAUDE.md §5 exige.

### Custo e risco

Não remove os textos dos quatro lugares — remove a **decisão** deles. Os
chamadores passam a perguntar à função. Provado pela mutação M4: mandar tudo ao
portal acende 2 vermelhas, e o controle prova que os dois vereditos diferem.

---

## CA-044 · Um pedido por lateralidade: `separar_itens` é conservador de propósito — **ESSENCIAL**

**SPEC-074** · 16/08/2026

### Problema

O portal diz, em texto presente em todas as telas, que permite *"apenas a SELEÇÃO
DE 1 (UM) ITEM POR ATENDIMENTO"*, e no passo 1 que *"se o item possuir
lateralidade será necessário abrir uma nova solicitação"*. Quem quebrou os dois
vidros precisa de **dois** pedidos.

### Decisão

`separar_itens()` separa quando a lateralidade é **explícita** ("motorista e
carona") e **não separa** em plural vago ("quebraram os vidros"), devolvendo um
item e deixando a pergunta para o atendente.

### Por que conservador, e não esperto

Cada atendimento é cobrado. Errar para mais abre um pedido que o segurado não
pediu, no nome dele, com custo. Errar para menos gera uma pergunta. As duas
pontas estão testadas, inclusive o controle do plural vago.

### Custo e risco

Uma conversa a mais em casos ambíguos. É o lado barato de errar.

---

## CA-045 · A frase de resultado passa a ler estado de negócio, não status técnico — **BLOCKER**

**SPEC-074** · 16/08/2026

### Problema

`format_result` decidia o que dizer olhando o status técnico do job. Com o
caminho API-first, o número do pedido chega em `evidence.vidros_estado`, não no
texto raspado da tela. Sem a ponte, um job que **criou o pedido** e caiu depois
diria *"não consegui abrir"* — a pior frase possível para alguém cujo pedido
existe, porque convida a pedir de novo, e o portal cobra por atendimento.

### Decisão

`format_result` lê `evidence["vidros_estado"]` **antes** do switch de status
técnico, e o Vigia ganhou três ramos de estado de negócio antes dos ramos
`done`/`failed`.

Quando o pedido existe mas o número não foi lido, a frase diz a verdade
incômoda: *"FOI aberto, mas não consegui ler o número. NÃO reexecute."* Não
inventa número — o teste prova que não há dígito algum na saída.

### Fail-closed, e o controle

Job sem `vidros_estado` cai no ramo antigo, idêntico. Protocolo lido do texto
continua tendo prioridade. Sem pedido nenhum, a frase honesta de falha
permanece. Os três controles estão na matriz (V06, V07).

### Custo e risco

Classificado BLOCKER porque a alternativa não é uma frase feia: é o segurado
abrindo o segundo pedido pago.

---

## CA-046 · O caminho API-first entra desligado — **VALIOSA**

**SPEC-074** · 16/08/2026 · previsto na SPEC-074 §27

### Problema

📊 A mineração de 58 MB de HAR mostrou que o portal é API-first nativo: 34
endpoints REST sob o AngularJS. A API devolve estruturado o que a tela obriga a
adivinhar — catálogo de peças, causas por peça, próxima pergunta, franquia e,
principalmente, a **ausência de cobertura num 400, antes de qualquer escrita**.

### Decisão

O caminho existe, atrás de `PORTAL_VIDROS_API_FIRST`, **desligada por padrão**.
Devolver `None` é resposta legítima: o que a API não resolver com certeza cai
para o navegador, que continua sendo a autoridade de último recurso. Um `except`
largo garante que erro no caminho novo nunca custe o acionamento de alguém com o
carro parado.

### Por que não ligar agora

Não existe canário read-only de fronteira material neste portal — exercitar de
verdade significa abrir um pedido pago no nome de um segurado. Ligar sem isso
seria afirmar em produção o que só foi provado em replay. Ver P-190 e P-191.

### Custo e risco

258 linhas inertes. Não quebram nada paradas; só não entregam o ganho. A mutação
M6 (flag nascendo ligada) acende vermelha, então "nasce desligada" é propriedade
testada, não convenção.

---

## CA-047 · `failed` deixa de liberar um pedido que existe — **BLOCKER**

**SPEC-074** · 16/08/2026 · achado por juiz crítico adversarial, verificado no código

### Problema

`portal_tool._buscar_pedido_vivo` excluía jobs `failed` do dedup, e o
`worker.py` gravava `failed` no handler de exceção **mesmo sabendo** que houve
efeito material — o bloco imediatamente acima já rebaixava a fase para `unknown`
justamente porque sabia.

Um job que criou o atendimento e caiu depois virava `failed`, sumia do dedup, e o
próximo `portal_action` com a mesma chave abria o **segundo atendimento, pago, no
nome do mesmo segurado**.

Nenhuma entrada maliciosa é necessária: basta um timeout do Supabase ao gravar o
checkpoint, ou um crash do Playwright no `browser.close()` depois de a journey já
ter retornado `done`.

### Decisão

Defesa em três camadas, porque nenhuma delas sozinha fecha:

1. `worker.py` grava `needs_human` — não `failed` — quando há prova de efeito;
2. `portal_tool` trata `failed` **com prova de efeito** como pedido vivo, para
   jobs gravados por versões anteriores e qualquer outro caminho;
3. `vidros_apifirst` grava `evidence["protocolo"]` já na **fronteira A**.

O terceiro é o que fecha de verdade. `tem_prova_de_efeito` procura
`evidence["protocolo"]`, e o caminho API só escrevia essa chave depois da
fronteira B — havia uma janela em que o pedido já existia na seguradora e a
evidência dizia que não havia prova de nada.

### Por que isso é BLOCKER e não ESSENCIAL

A alternativa não é um relatório ruim: é o segurado com dois atendimentos pagos
abertos no nome dele, e a corretora descobrindo pela fatura.

### Custo e risco

`needs_human` mantém o pedido vivo para o dedup e é o único status que o botão de
retry do dashboard aceita — onde `pode_retentar_pelo_dashboard` já confere efeito
antes de deixar repetir. O caminho de retry legítimo continua existindo, agora
com conferência.

---

## CA-048 · O fallback API→DOM passa a ser um portão, não um corredor — **BLOCKER**

**SPEC-074** · 16/08/2026

### Problema

Eu escrevi, no bloco da flag em `vidros_lanternas`:

```
# Um erro no caminho novo NUNCA pode custar o acionamento
```

Está certo **antes** da fronteira A e é um desastre **depois** dela. `POST
/atendimentos` devolve ok, a gravação seguinte falha, a exceção sobe, e o
`except` cai para o DOM com `confirm=True` — `run_adaptive` preenche o formulário
de novo e submete.

### Decisão

Só cai para o DOM quem consegue **provar** que nada material aconteceu
(`pode_repetir_com_seguranca`). Com prova de efeito, devolve `needs_human` com a
frase que o segurado precisa ouvir: *"o pedido FOI aberto, não peça para eu abrir
de novo"*.

### Custo e risco

Um acionamento a menos completado automaticamente, em troca de zero pedidos
duplicados. Ausência de informação não é prova de ausência de efeito.

---

## CA-049 · Teste de inspeção de fonte deixa de valer como prova de comportamento — **ESSENCIAL**

**SPEC-074** · 16/08/2026 · regra de método

### Problema

📊 Medido: a matriz de 62 asserções ficava **62/0 verde** com o caminho API-first
completamente inerte — bastava trocar `return _r` por `pass`. E o caminho já
estava inerte de outro jeito, por exigir dois campos que ninguém escrevia.

Os blocos V12 e V13 provavam a orquestração por `inspect.getsource()`: *"a
palavra `guard.before` aparece antes da palavra `criar_atendimento`"*. Isso prova
que um texto existe num arquivo.

### Decisão

Onde houver **fronteira material**, tem de haver ao menos um teste que EXECUTA e
**conta quantas vezes o POST saiu**. A checagem de texto pode ficar, como
documentação — nunca como prova única.

`test_spec074_a_fronteira_material_executada.py`: 29 asserções, sessão falsa que
conta chamadas, seis mutações detectadas.

### Custo e risco

Mais trabalho para escrever o teste. O primeiro deles achou dois defeitos na
estreia — o caminho morto e a janela sem prova de protocolo.

---

## CA-050 · O registro enriquece sem duplicar: a definição finge ser tupla — **ESSENCIAL**

**SPEC-075** · 16/08/2026 · previsto pela SPEC-075 §9.1

### Problema

`JOURNEYS` mapeava `chave → (módulo, função)`. A SPEC-075 precisa que o registro
diga a operação de negócio e a classe de efeito — e proíbe, no mesmo parágrafo,
criar um `journey_registry_v2`.

Enriquecer o valor quebraria todo código que faz `modulo, funcao = JOURNEYS[k]`.
Criar um mapa paralelo seria o segundo registry proibido.

### Decisão

`JourneyDefinition` implementa `__iter__`, `__getitem__` e `__len__`. O
desempacotamento antigo funciona byte por byte; o acesso novo (`d.effect_class`)
existe ao lado.

### Custo e risco

Um dataclass que se comporta como tupla é incomum, e por isso está documentado no
próprio arquivo. 📊 A prova de que a compatibilidade é real: as 11 suítes que leem
o registry passaram sem uma linha alterada.

---

## CA-051 · Três tools estreitas em vez de uma `portal.execute` — **ESSENCIAL**

**SPEC-075** · 16/08/2026

### Problema

⚠️ **CORRIGIDO em 17/08/2026.** O texto original dizia que não havia linha em
`tool_definitions`. 📊 O banco vivo mostrou que `portal.execute`,
`portal.billing_read` e `portal.policy_read` **já existiam** — com
`input_schema = {}` e provider antigo. Eu havia inferido o estado de produção a
partir do `grep` no repositório, que a `MIGRATIONS-AUTHORITY` §4 avisa não ser a
fonte completa.

O problema real, então, não era ausência de tool: era **tool sem schema**. Uma
tool com `input_schema = {}` não valida nada — o modelo pode mandar qualquer
coisa, inclusive os campos que a §10.4 proíbe.

Uma tool única "executa portal" obriga o modelo a dizer **qual journey** rodar —
proibido pela §10.4 — e carrega um `side_effect_class` só, então autorizar
leitura de cobrança passaria a autorizar abertura de atendimento pago.

### Decisão

`portal.billing_read` (read), `portal.policy_read` (read),
`portal.assistance_request` (write_external, `requires_approval`, risco alto).

🔴 Nenhum dos três `input_schema` menciona `journey`, `module`, `function`,
`portal_key`, `account_id`, `cookie`, `token` ou `password`. O `VERIFY` da
migration inclui uma consulta que devolve **zero linhas** se algum mencionar.

### O que NÃO se fez

Tool por seguradora. `billing.overdue.list` vale para as seis — e uma seguradora
nova entra no registry do portal-worker e passa a ser atendida pela mesma tool,
sem migration, sem release nova, sem Auxiliar novo.

---

## CA-052 · `failed` do worker deixa de ser status neutro — **BLOCKER**

**SPEC-075** · 16/08/2026 · continuação do CA-047 da SPEC-074

### Problema

Ver CA-047. A SPEC-075 acrescenta a peça que faltava do outro lado: o
`billing_collection` e o `portal_tool` agora gravam `operation_key`, e o insert
podia **derrubar a operação inteira** se a coluna ainda não existisse no banco.

### Decisão

Tenta com a coluna; se o banco recusar, repete sem. É o que "expand-first"
significa do lado do **código** — o `smith-api` sobe com a imagem nova antes de
a migration rodar, e entre os dois instantes o código tem de funcionar dos dois
jeitos.

### Custo e risco

Um `except` a mais em dois lugares. A alternativa era a varredura de cobrança
inteira parar por causa de uma coluna que nem é usada ainda.

---

## CA-053 · Concorrência por CONTA, e o lease mudou de contêiner — **ESSENCIAL**

**SPEC-075** · 16/08/2026

### Problema

📊 O worker é globalmente serial: um job por vez, `ORDER BY created_at`. Uma
varredura de 200 apólices enfileirada às 3h fica na frente do acionamento de um
segurado com o carro parado às 9h.

### Decisão

`run_lote` roda até N jobs, **um por conta**. Contas diferentes em paralelo; a
mesma conta nunca — cada conta tem sessão de navegador persistida, e duas em
paralelo se sobrescrevem e derrubam a corretora do portal.

`run_once` ficou **idêntica** ao baseline: é o caminho de `concurrency=1`, e o
Gate D exige que ele não mude.

### O erro que quase passou

🔴 O lease nasceu em `app/services/portals/leases.py`. O `Dockerfile` do
portal-worker copia **só** `backend/portal_worker`. Um lease que importa
`app.core.redis` não existe no processo que precisa dele — teria falhado em
produção com todos os testes verdes. Movido, com cliente próprio.

### Custo e risco

`redis>=5.0` entrou no `requirements` do worker; enquanto não houver deploy, a
biblioteca não está na imagem e a concorrência efetiva fica em 1 — que `/health`
informa explicitamente.

---

## CA-054 · Score de prontidão ANULA em vez de subtrair — **VALIOSA**

**SPEC-075** · 16/08/2026 · §21.3

### Decisão

Hard blocker não tira pontos: zera. A medição fica em `score_bruto`; o campo que
telas e ordenações leem é `score`.

### Por que subtrair seria errado

Três razões, e a terceira é a que fecha: subtrair implica que evidência boa
**compra** ausência de isolamento de tenant; põe "proibido" e "inacabado" na
mesma régua, de modo que ordenar por score recomendaria subir a mais perigosa;
e é negociável — no dia em que faltarem 3 pontos, alguém mexe no peso. Zero não
tem peso para mexer.

---

## CA-055 · A SPEC-077 executada é metade do que ela pedia — **ESSENCIAL**

**SPEC-077** · 17/08/2026 · autorizado pela própria SPEC §4.3 (melhoria técnica)

### Problema

A SPEC-077 foi escrita antes de a SPEC-075 ser executada e contra um upstream
que a auditoria mostrou ser diferente do imaginado. Executá-la como escrita
duplicaria sete capacidades e traria uma dependência inauditável.

### Decisão

Escopo reordenado por valor e risco. Entrou: `HarImporter`, `browser-to-api`,
ciclo de vida do endpoint, drift, injeção de erro, DeepTrace com CDP nativo,
comandos `lab`. Saiu: `browse` CLI, AutoBrowse, Browserbase Remote,
`webmcp-gen`, Functions.

📊 O corte não é conservadorismo: das oito skills, **três não têm uma linha de
código** (são prompts) e **cinco dependem de um binário com fonte 404**.

### Custo e risco

A SPEC não é entregue "inteira" segundo a letra. É entregue inteira segundo o
objetivo declarado no §51 dela: *"quanto menos trabalho humano é necessário para
descobrir uma nova capacidade de portal"*. 📊 218 endpoints descobertos em 5
seguradoras, incluindo 4 que estavam declarados desconhecidos.

---

## CA-056 · Redação na COLETA, não na emissão — **BLOCKER**

**SPEC-077** · 17/08/2026

### Problema

📊 O inferidor guardava valor cru em `Forma.exemplos` e o emitia como
`examples`. O artefato gerado saiu com **410 achados de PII** — 340 chassis, 16
placas, 4 CPFs — e o destino dele é `docs/generated/`, **versionado**.

### Decisão

Valor passa pelo detector **antes** de entrar na estrutura. O que nunca entrou
não vaza por `print` de depuração, por traceback nem por `json.dumps` de
diagnóstico.

E o detector usado é o **mais estrito disponível**: o `varredura_de_pii` da 075
(que conhece chassi) além do `redigir_texto` da 073 (que não conhece). Os dois
guardas nasceram para contextos diferentes; aqui vale a soma.

### Custo e risco

Classificado BLOCKER porque a alternativa é PII de segurado em commit — que é
permanente e público no repositório.

---

## CA-057 · O caminho da URL também é PII — **BLOCKER**

**SPEC-077** · 17/08/2026

### Problema

A API da MAPFRE tem `/api/1.0.0/client/12097137725_1/interactions`. O
`normalizar_path` da SPEC-073 preserva número colado em palavra — a regra
**certa** (distingue `passo5` de `passo6`) aplicada a um caso que ela não previu.

### Decisão

Segunda passada, **só no Lab**: segmento que contém CPF/CNPJ vira `{id}`. A
regra da 073 continua intacta para o que ela protege.

### O erro dentro do conserto

A primeira versão exigia **exatamente** 11 ou 14 dígitos. O segmento real limpo
dá **12** — CPF mais o sufixo `_1`. A pergunta certa não é *"este segmento É um
CPF?"*, é *"este segmento CONTÉM um?"*.

---

## CA-058 · `routine_runs` ganha `company_id` denormalizado — **ESSENCIAL**

**SPEC-078 F.3** · 17/08/2026 · autonomia da §14 (nota 0–100)

### Problema

📊 `routine_runs` tinha 32 linhas e **nenhuma coluna de corretora**. A rota de
Entregas filtra toda fonte por `.eq('company_id', empresa)` — o backend usa
service role e é o filtro no código, não a policy, que protege (CLAUDE.md §7).
Sem a coluna, a sexta fonte não tinha como existir.

### As opções, com nota

| Opção | Nota | Por quê |
|---|---|---|
| **Coluna `company_id` denormalizada + backfill + trigger** | **92** | a leitura fica idêntica às outras cinco fontes; a regra continua verificável por leitura; o índice `(company_id, started_at desc)` serve à consulta real |
| Duas consultas: ids das rotinas da empresa, depois `in('routine_id', …)` | 60 | sem migration, mas o escopo vira indireto — o próximo a copiar o padrão perde o filtro sem perceber, e a lista de ids cresce |
| Join embutido `routines!inner` com `.eq('routines.company_id')` | 70 | uma consulta só, mas a segurança passa a depender de o `!inner` estar lá; alguém tirando o `!inner` transforma filtro em vazamento silencioso |

### A trigger, e por que ela existe

📊 `routine_runs` tem **dois** escritores (`routine_engine.py:255` e `:553`), e
esta rodada só autorizava tocar num deles. `NOT NULL` quebraria o outro na hora.
Expand-first: coluna nullable + `trg_routine_runs_herda_empresa`, que copia o
dono da rotina quando o escritor esquece. O `NOT NULL` fica para uma migration
de endurecimento, depois de o banco provar que não há nulos.

---

## CA-059 · O relatório completo mora em coluna, não em artifact — **ESSENCIAL**

**SPEC-078 F.4** · 17/08/2026

### Problema

📊 Das 32 execuções gravadas, **29 tinham `output_preview` com exatamente 500
caracteres** — o teto de `output[:500]`. 91% truncadas, e o corte cai justamente
antes de "PRECISA DE VOCÊ" e "Clientes encontrados".

### Onde guardar o texto inteiro — as opções, com nota

| Opção | Nota | Por quê |
|---|---|---|
| **Coluna nova `routine_runs.output_full`** | **88** | mesma linha, mesma retenção (a purga de 90 dias leva o texto junto), mesmo escopo de tenant; a página lê com um `.eq('company_id')` |
| Artifact | 75 | o artifact é o entregável **compartilhável** — e é por isso que ele **não pode** carregar o CPF. São perguntas diferentes: o artifact é o que se manda; `output_full` é o que aconteceu |
| Objeto no Storage | 45 | acrescenta rede no caminho de leitura e uma segunda política de retenção para 4 KB de texto |

### `output_preview` fica, e ganha papel declarado

Nota 85 contra 60 de derivá-lo na leitura: derivar obrigaria a lista de Entregas
a trazer 4 KB por linha, 120 por fonte, para cortar 500 na memória. Os dois saem
da **mesma string, no mesmo `update`** — não têm como divergir.

### Sem backfill, de propósito

Copiar os 500 caracteres truncados para `output_full` apresentaria o corte como
se fosse o relatório. A página diz, para as 32 antigas, que são anteriores ao
registro completo. Mentir por conveniência de schema é pior que a lacuna.

---

## CA-060 · A peça da Cobrança sai SEM CPF, e o texto integral fica atrás da sessão — **BLOCKER**

**SPEC-078 F.5** · 17/08/2026

### Problema

Um artifact pode virar `artifact_shares`: link público com validade de 30 dias,
autenticado só pelo token da URL. O relatório da cobrança carrega **CPF/CNPJ e
telefone de segurado em texto claro** (`billing_collection.py:1069-1140`).

### Decisão

Dois níveis de exposição, deliberadamente diferentes:

```text
routine_runs.output_full   texto integral, com CPF   sessão + .eq('company_id')
artifact                   contagens, nomes, ...9901  pode virar link público
```

`_mascarar_documento` reduz o documento aos quatro últimos dígitos — o bastante
para distinguir dois "João Silva" na mesma lista, insuficiente para usar.

📊 Render real conferido: 8 blocos, `{'desconhecidos': [], 'falhas': []}`,
23.714 bytes de HTML, com `Precisa de você`, `Inadimplentes encontrados` e o
portal que falhou presentes — e zero ocorrências do CPF inteiro ou do telefone.

### Nenhum motor paralelo

O caminho é o do Checklist das 6h, lido em `intelligence/workflows.py:131-157`:
`ArtifactService.criar → renderizar → publicar`. `criar` aceita
`work_run_id=None`, então F.5 **não** exigiu criar Work Run — que seria o
segundo motor que a SPEC-078 e o CLAUDE.md §5 proíbem. O guarda do teste recusa
escrita direta em `artifacts`, `artifact_versions` ou `artifact_renders`.

---

## CA-061 · O GLOSSÁRIO não define `rota` — e a SPEC-083 manda conferir contra ele — **ESSENCIAL**

> Registrado em 21/08/2026, durante a execução da SPEC-083, Bloco A.
> Autorização: o Founder, ao liberar a execução — *"registre em CHANGE-ADDENDA.md,
> não invente definição, e siga. Não pare por isso."*

### Problema

A SPEC-083 §0 obriga, antes da primeira linha de código:

> *"`docs/canon/GLOSSARIO.md` — conferir **termo a termo**: `corredor`,
> `subcorredor`, `rota`, `playbook`, `âncora`, `passo`, `subserviço`. Se esta SPEC
> divergir, **o glossário vence** e a SPEC é corrigida antes de executar."*

📊 Conferência feita em 21/08/2026 contra `docs/canon/GLOSSARIO.md`
(`grep -ci "<termo>" docs/canon/GLOSSARIO.md`):

| termo | ocorrências | está definido? |
|---|---:|---|
| `corredor` | 5 | ✅ sim — linha 58: *"o roteiro para acionar assistência \| a **URA** da seguradora \| `corridor_playbooks.py`"* |
| `playbook` | 1 | ⚠️ citado, não definido |
| `passo` | 1 | ⚠️ citado, não definido |
| **`rota`** | **0** | 🔴 **AUSENTE** |
| `subcorredor` | 0 | 🔴 AUSENTE |
| `âncora` / `ancora` | 0 | 🔴 AUSENTE |
| `subserviço` / `subservico` | 0 | 🔴 AUSENTE |

🔴 **`rota` é a unidade de trabalho da SPEC-084 inteira** — *"levar as 62 rotas ao
nível da máquina de lavar"* — e é o sujeito de cada linha da rubrica da SPEC-083.
O CLAUDE.md §2 diz *"um termo, uma definição. Se dois documentos discordarem,
este vence"*. Não há o que vencer: o termo não existe lá.

### Decisão

🔴 **Não inventar definição.** Um glossário é autoridade justamente porque não é
escrito de passagem por quem precisa do termo — é o mesmo defeito que produziu o
`numero_residencia` (âncora escrita de cabeça, ZERO ocorrências em 28.096
eventos), um nível acima.

**O que fica registrado, e é o que a SPEC-083 usa operacionalmente** (§1.4, §2.1):

```text
rota  =  seguradora × ramo × serviço
         a unidade que recebe nota na rubrica
         📊 62 delas, medidas como a soma dos `subservices` dos 14 playbooks
```

**A execução segue** com essa leitura. A escrita canônica no GLOSSARIO fica como
pendência com dono 🧑 Founder — ver `PENDENCIAS.md`, entrada do Bloco E.

### Nenhum motor paralelo

Nenhuma definição nova foi criada em documento nenhum. Esta entrada **registra a
ausência**; não a preenche.

---

## CA-062 · `templatize` MATA a captura de senha — a exceção da SPEC-083 §6.4 não está implementada — **BLOCKER**

> Registrado em 21/08/2026, SPEC-083 Bloco A, antes de gerar uma linha de corpus.

### Problema

A SPEC-083 §6.4 é literal ao definir a higiene do corpus:

> *"telefone → `+55 (##) #####-####`
> **EXCEÇÃO: preservar os 4 últimos se eles reaparecerem como senha**
> (📊 tela #27 de `7ac3c101`) — **senão a âncora de senha perde o alvo**."*

E a SPEC-084 §2.5.1.3 afirma, sobre o mesmo caso, que só o VALOR se perde e que a
âncora sobrevive:

> *"✅ a ÂNCORA sobrevive — o passo casa por PROSA, e a prosa está intacta
> (conferido: a regex do passo ainda casa)"*

📊 **Medido em 21/08/2026, com o CONTROLE VERDE**
(`marcas_de_corretora(recarregar=True)` → **8 marcas**, banco ligado):

```
tela #27 CRU
  "Sua senha sera os 4 ultimos digitos desse telefone *4743*"
  extract_capture_anchors(PB, tela)  ->  {'password': '4743'}   OK

tela #27 DEPOIS de templatize()
  "Sua senha sera os 4 ultimos digitos desse telefone *{SEGREDO}*"
  extract_capture_anchors(PB, tela)  ->  {}                     A CAPTURA MORRE
```

🔴 **A afirmação da SPEC-084 mede a coisa errada.** `match_ura_step` devolve
`None` para a tela #27 **nos dois casos** — ela não é um passo, é uma tela de
captura. O que importa ali é `capture_anchors["password"]`, e ele **para de
capturar**. Um teste que verifique *"o corredor capturou a senha"* passaria a
não ter como verificar nada — e a perda apareceria só como um número menor.

📊 **E as outras duas telas de telefone SOBREVIVEM** — o dano é cirúrgico, não geral:

```
"Registramos o telefone *{TELEFONE}*. Deseja adicionar outro numero?"
   -> match_ura_step = confirmar_telefone           OK
"Obrigada! Anotei seu numero *{TELEFONE}*. Esta correto?"
   -> match_ura_step = confirmar_telefone_anotado   OK
```

### Decisão

A exceção da §6.4 é **implementada no gerador de corpus**, não no `templatize`:

1. antes de mascarar, roda `extract_capture_anchors(pb, texto_cru)`
2. se veio `password`, guarda o valor
3. mascara com `templatize(...)`
4. **reinjeta** o valor da senha no lugar do marcador
5. 🔴 **CONTROLE nos dois sentidos, obrigatório no teste:**
   · a tela #27 do corpus **capturada** devolve a senha → senão o corpus perdeu um passo
   · uma tela com telefone **que não é senha** continua mascarada → senão a exceção
     virou um buraco de PII

🔴 **Não se toca em `templatize`.** Ele tem 📊 8 consumidores de produção — o
Tecelão entre eles, que escreve `ura_maps`, e o Atlas é UM SÓ e é de todas as
corretoras. Mudá-lo para atender ao corpus mudaria o que o Tecelão grava
(CLAUDE.md §5, e `O-ATLAS-E-UM-SO-E-E-DE-TODAS.md`).

### Nenhum motor paralelo

O mascarador continua sendo **um só**: `templatize`. O gerador de corpus o
**chama** e aplica uma exceção declarada pela SPEC-083 §6.4 sobre a saída dele.
Nenhum segundo mascarador foi escrito.

---

## CA-063 · O "buraco real" do mascarador não reproduz — está mascarado — **ESSENCIAL**

> Registrado em 21/08/2026, SPEC-083 Bloco A. Entrada de MEDIÇÃO: ela não muda
> comportamento, corrige um fato que a SPEC-084 vai herdar.

### Problema

A SPEC-084 §2.5.1.3 registra, depois de refazer a medição com o banco ligado:

```
templatize("Saionara - Resulta")  ->  Saionara - Resulta     BURACO REAL
```

e conclui: *"a marca gravada é `Resulta Seguros`; a yelum escreve só `Resulta`.
Essa é uma das 66 telas do §2.5.1.3, e entraria no corpus com nome de atendente e
razão social em claro."*

📊 **Medido em 21/08/2026, com o CONTROLE VERDE**
(`marcas_de_corretora(recarregar=True)` → **8 marcas**):

```
'Christian - AutoFleet'          ->  '{NOME} - {CORRETORA}'          OK
'Saionara - Resulta Seguros'     ->  '{NOME} - {CORRETORA}'          OK
'Saionara - Resulta'             ->  '{NOME} - {CORRETORA}'          NAO REPRODUZ
'SGA Corretora de Seguros Ltda'  ->  'SGA Corretora de Seguros Ltda' reproduz
```

**A causa está no próprio código, comentada** (`templater.py:1337`):

> *"'Resulta Seguros' também gera 'Resulta': é assim que o caso sem sufixo — o que
> nenhuma regex cobre — passa a ser coberto."*

📊 `marcas_de_corretora()` deriva **duas** marcas por linha de `companies` (a razão
social inteira e a primeira palavra), e ordena por comprimento decrescente para
que `Resulta Seguros` seja trocado antes de `Resulta`. Com 5 linhas em
`companies`, isso produz as **8 marcas** medidas — e `Resulta` é uma delas.

### Decisão

**O buraco ① da SPEC-084 §2.5.1.3 é dado como NÃO REPRODUZIDO** e não gera
trabalho. A SPEC-084 herda esta entrada e corrige o texto quando chegar ao seu
BLOCO 0.

⚠️ **O que CONTINUA de pé, e é outra classe:** `SGA Corretora de Seguros Ltda`
segue inalterada — a SGA não é corretora cliente e não está em `companies`. Ela é
coberta pela regra **genérica de razão social** da SPEC-083 §6.4, e o gate de PII
do Bloco A a persegue. 📊 4 eventos na porto, numa tela que traz também telefone e
e-mail de terceiro.

### O que esta entrada ensina, e por que ela está aqui

A medição que produziu o "buraco real" foi feita **com o banco ligado** e mesmo
assim envelheceu: entre ela e hoje, a lista de marcas mudou. 🔴 **Medição sobre
estado vivo carrega data ou não carrega nada** — é a §12.1 do CLAUDE.md aplicada
ao próprio instrumento de medida.

---

## CA-064 · O nome no vocativo vaza — e a trava é ESTRUTURAL, não lexical — **BLOCKER**

> Registrado em 21/08/2026, SPEC-083 Bloco A.

### Problema

📊 A SPEC-083 §6.4 manda mascarar `nome → {NOME}`, e §8 (VERIFY) é literal:
*"Um primeiro nome no início da tela passaria a auditoria inteira — e é exatamente
o vazamento que `O-ATLAS-E-UM-SO-E-E-DE-TODAS.md` nomeia como o real."*

Medido, com o CONTROLE verde (`marcas_de_corretora()` = 8):

```
templatize("Rafael, escolha a opcao desejada: Cartao de Credito")
  -> "Rafael, escolha a opcao desejada: Cartao de Credito"     INALTERADO
```

📊 A escala: **425 eventos em 154 sessões, 9 seguradoras**, com a forma
`<Palavra>, <resto>` no início de tela `direction='in'`.

### A regra que NÃO se pode escrever

`templatize` **já tem** `NOME_NO_VOCATIVO`, e ela exige — de propósito — que a URA
tenha se apresentado **na linha anterior**. O próprio arquivo registra por quê:

> *"Sem ela, este mascarador come português. Um teste que já existia reprovou o
> conserto e mostrou três frases reais que eu estava destruindo:
> `"Roubo, furto e incêndio têm franquia própria"`, `"Agora, me informe o CEP do
> local"`, `"Elogios, reclamações e informações de como…"`. Nenhuma lista de
> palavras cobre o português inteiro."*

🔴 **A ideia óbvia — um `^Palavra,` genérico — já foi tentada e derrubada por
medição.** Repeti-la seria escrever de cabeça o que o acervo já refutou.

### Decisão — o discriminador estrutural

> ## Um NOME varia sobre o mesmo esqueleto. Um abridor de frase é sempre a MESMA palavra.

📊 Medido sobre os 16.242 eventos `direction='in'`, agrupando pelo texto que vem
DEPOIS do vocativo (60 chars, dígitos neutralizados):

```
esqueletos com 1 cabeça só ....... 352   (2.090 eventos)   LINGUA — não se toca
esqueletos com >=3 cabeças .......   7   (  137 eventos)   DADO  — mascara
                                                           102 sessões, 5 seguradoras
```

🔴 **CONTROLE, nos dois sentidos:**

```
as 7 famílias marcadas como DADO — todas vocativo real:
  "X, é você que está no local para acompanhar o serviço?"   15 cabeças / 19 ses
  "X, agora preciso saber se o veículo está em uma rodovia"   7 cabeças / 34 ses
  "X, escolha a opção desejada: seguro auto…"                11 cabeças / 15 ses
  "X, qual a placa do veículo?…"                              4 cabeças / 17 ses
  "X, escolha a opção desejada: cartão de crédito…"           5 cabeças /  9 ses
  "X, além do guincho, você precisa também solicitar táxi"    4 cabeças /  5 ses
  "X, localizei o seu *seguro auto*…"                         3 cabeças /  3 ses

as palavras de LÍNGUA, que EXISTEM em massa e NÃO são marcadas:
  "certo"   565 ocorrências ·  66 esqueletos · max_cabeças = 1
  "agora"   341 ocorrências ·  24 esqueletos · max_cabeças = 1
  "pronto"   68 ocorrências ·   9 esqueletos · max_cabeças = 1
```

**974 ocorrências de abridores de frase: o discriminador os VÊ e não os marca.**

⚠️ A faixa de **exatamente 2 cabeças** (8 esqueletos, 37 eventos) **não** é
mascarada automaticamente — vai para `INDICE.md` como `NOME_DUVIDOSO`, com a
contagem, para leitura humana. 🔴 Truncar calado lê-se como "cobrimos tudo".

### Nenhum motor paralelo

`templatize` continua sendo **o** mascarador, com as 38 regras de PII. O corpus
aplica, sobre a saída dele, uma regra derivada do próprio acervo — do mesmo jeito
que a exceção da senha (CA-062). **`templater.py` não foi tocado**, e os seus 8
consumidores de produção — o Tecelão entre eles — não mudaram.

---

## CA-065 · Os padrões foram medidos em SQL e aplicados em Python — e `.` não casa `\n` — **BLOCKER**

> Registrado em 21/08/2026, SPEC-083 Bloco A, quando o CONTROLE obrigatório da
> sessão `7ac3c101` falhou.

### Problema

A SPEC-083 §8 exige, como controle do passo 0:

> *"`7ac3c101` classifica como residencial PELO NÍVEL 2 — e a saída DIZ qual nível
> decidiu."*

📊 Primeira execução do classificador: **`indefinido`**. A régua não classificava a
própria sessão que a validou — o cenário que a SPEC nomeia como *"a SPEC falharia
no Bloco A, medindo a si mesma"*.

**A causa, isolada:** a tela 3 daquela sessão é

```
qual seguro deseja utilizar?
<linha em branco>
1 - residencial: para sua casa ou apartamento individual
```

e o padrão é `qual seguro deseja utilizar\?.{0,40}resid[ea]ncial`.

```
Python  re.search(p, tela)                -> False     ← `.` NÃO casa \n
Python  re.search(p, tela, re.DOTALL)     -> True
Postgres  text ~ p                        -> true      ← `.` casa \n por padrão
```

> ## As tabelas foram MEDIDAS em SQL e APLICADAS em Python. Todo padrão multilinha perdia tudo, em silêncio.

📊 O estrago, medido alternativa a alternativa:

```
alternativa                                                sem DOTALL   com DOTALL
qual seguro deseja utilizar ... residencial     (allianz)       0           37
escolha a opcao desejada ... servico para resid (porto)         0           26
qual o servico que voce precisa ... encanador   (hdi)           0            4
idem                                            (yelum)         0            3
```

### Decisão

1. `padroes_de_ramo._compilar()` passa a usar `re.DOTALL`.
2. A dependência vai para o **docstring**, com a medição.
3. 🔴 Nasce `test_a_tabela_de_ramo_exige_dotall`, e ele é o guarda que importa:
   **o motor do produto (`corridor_playbooks`) compila as âncoras dele SEM
   `DOTALL`.** Quem copiar uma destas quatro para um `ura_step` ganha o
   `numero_residencia` de volta — âncora que não casa nada, e ninguém vê.

📊 Efeito medido: `7ac3c101` passa a classificar `residencial / nivel-2-texto`; as
colisões `ambos` da porto caem de 20 para 2; o nível 1 da porto sobe de 7 para 29.

### A lição, que é maior que o conserto

**Motor de regex tem dialeto.** Um número medido com um motor e aplicado com outro
é um número sobre outra coisa. Vale para `.`/`\n`, para `\b` em Unicode, para
classes POSIX. 📊 E a SPEC-083 já tinha o irmão disto registrado — `unaccent` não
existe no banco, então `_norm` não pode ser reescrito em SQL.

---

## CA-066 · O corpus da SPEC-083 é `zona='URA'`, não `direction='in'` — **ESSENCIAL**

> Registrado em 21/08/2026, SPEC-083 Bloco A. **Ampliação de escopo, nunca redução**
> (CLAUDE.md §11, D5).

### Problema

A SPEC-083 §6.3 exige apenas *"só `direction='in'`"*. A separação URA/HUMANO é
§2.5 da SPEC-084. Mas o corpus da 083 alimenta o replay (eixo B, 35 pontos) e a
pergunta do JUIZ 1 — *"alguma tela do corpus não casa passo nenhum e pede algo?"*.

📊 Medido na Allianz: telas distintas que PEDEM algo — **zona humana 472 · zona
URA 126 (3,7×)**. Com a zona humana dentro, **472 reprovações automáticas,
permanentes e insanáveis**: nenhuma rota da Allianz seria liberada.

### Decisão, com as notas do método (§4 do handoff do Founder)

| opção | objetivo | medida | guarda fica vermelho | motor paralelo | nota |
|---|---|---|---|---|---|
| A · só `direction='in'` (literal da 083) | ✗ 472 órfãs insanáveis | ✓ | ✗ passa 100% num corpus 29% humano | ✓ | **35** |
| **B · zona URA** | ✓✓ | ✓ medida nas 10 | ✓ semeia-se linha humana | ✓ um módulo só | **92** |
| C · gerar os dois corpora | ~ dois divergem | ✓ | ~ | ✗ | **40** |

**Escolhida a B.** O módulo `zonas_do_acervo.py` serve às duas SPECs; a 084 o
herda em vez de criar.

📊 Zonas medidas: **10.498 URA · 5.250 HUMANO (32,3%) · 493 ORFAO**.

---

## CA-067 · `ANCORA_SUSPEITA` revisado — e o bradesco é um estado NOVO — **ESSENCIAL**

> Registrado em 21/08/2026. **Esta entrada corrige um achado do próprio executor.**

### Problema

A SPEC-083 §3.2 classifica 13 rotas como `ANCORA_SUSPEITA` apoiada em:

> *"📊 Zurich e Bradesco nunca escrevem 'protocolo' — escrevem **'ordem de serviço'**
> (zurich 25 ocorrências, bradesco 10)."*

📊 **A segunda metade não existe:** `ordem de servi` = **0** em zurich e bradesco.
No acervo INTEIRO são **7 telas** — tokio 3, hdi 2, porto 2. O par "25/10" não
corresponde a nenhuma seguradora.

🔴 **E a primeira conclusão do executor sobre isso também estava errada.** Ele
mediu `(sucesso|solicitad|abert|registrad) [^0-9]{0,40}[0-9]{5,}` → 0 de 14 na
zurich, e propôs `SEM_DESFECHO_NO_ACERVO` para as 9 rotas. **A query tinha um
espaço literal depois do grupo.** Sem ele: **3 de 14**. Um minerador derrubou o
achado, e a derrubada foi reproduzida antes de aceita.

### Decisão — três estados, não um

| seguradora | rotas | estado | evidência medida |
|---|---:|---|---|
| **zurich** | 5 | 🟠 `ANCORA_SUSPEITA` | o desfecho EXISTE: `*Número da solicitação:* *NNNNNNNN*` e `*Número do processo:* 31.26.NNNNNN.01`. Âncora a ampliar: `n[uú]mero d[ao] (solicita[çc][ãa]o\|processo)` → **4 de 14** |
| **bradesco** | 4 | 🔵 **`DESFECHO_SEM_NUMERO`** — estado novo | 📊 a URA **não emite número nenhum** neste canal: fecha com URL — *"o agendamento tá confirmado! para acompanhar… é só entrar no link"* → 3 de 22. **Não é âncora incompleta: é uma URA que não dá protocolo.** |
| **mapfre** | 4 | ⚫ `SEM_DESFECHO_NO_ACERVO` | 📊 **0 de 13 sessões abriram assistência.** Ninguém escolheu "Assistência 24H". Não é âncora faltando — é acionamento que nunca aconteceu |

🔴 **E o `DESFECHO_SEM_NUMERO` é achado de PRODUTO, não de classificação:** hoje a
atendente promete ao segurado um número que a seguradora **não dá**. A
`expectativa_do_desfecho` do bradesco tem de dizer que o acompanhamento é pelo
link. Entrega da SPEC-084.

---

## CA-068 · A demanda contava o CARDÁPIO, não a ESCOLHA — e o ranking inverte — **BLOCKER**

> Registrado em 21/08/2026. 🔴 **Esta entrada muda a ORDEM DE EXECUÇÃO da SPEC-084.**

### Problema

A coluna DEMANDA ordena a SPEC-084 inteira. Ela vinha contando as sessões em que a
palavra do serviço aparece em **qualquer** evento `direction='in'` — o que inclui a
tela que **LISTA** os serviços.

📊 Medido em 21/08/2026, com a cascata de dois níveis aplicada ao serviço:

```
serviço                ESCOLHIDO   (cardápio)   💭 a SPEC-083 §10.2 dizia
guincho / reboque          72         197            ~205
bateria                    16         106            ~113
encanador                  14         132            ~152
eletricista                12         109            ~176
troca de pneu              10         101            ~105
eletrodoméstico             9         102            ~105
socorro mecânico            7          70             ~91
chaveiro                    5         210            ~213
vidro / para-brisa          1          77             ~79
telhado                     0          51              —
carro reserva               0          75              —
martelinho de ouro          0          57              —
```

> ## `chaveiro` cai de 1º (210) para 8º (5). `guincho` vira líder isolado, 4,5× o segundo.

🔴 **`carro reserva` e `martelinho` aparecem em 75 e 57 sessões de cardápio e em
ZERO escolhas no acervo inteiro.**

**Ordenar a SPEC-084 pela coluna do cardápio mandaria construir chaveiro e vidro
primeiro — 5 e 1 pedidos reais em 573 sessões.**

### Por que aconteceu — quatro causas medidas

1. **Uma tela lista tudo.** 📊 azul: guincho = chaveiro = vidro = martelinho =
   carro reserva = **16 sessões, e nas 3 numeradas os quatro estão no MESMO
   EVENTO**. zurich: cinco serviços com 9 cada. alfa: quatro com 5 cada.
2. **A corretora responde com NÚMERO.** 📊 allianz: `chaveiro`, `eletrodoméstico`,
   `telhado`, `reboque` e `vidro` têm **0 ocorrências** em `direction='out'`.
3. **O caminho dominante da allianz é FUGA, não escolha.** 📊 `3` (outros) → `7`
   (outros) → transferência para humano em **39 de 39 sessões** (27% do acervo).
   É a explicação medida do colapso 210 → 5.
4. **937 respostas de botão têm texto VAZIO e são irrecuperáveis** — ver CA-069.

### Decisão

A mesma cascata de dois níveis que a §8 já usa para o RAMO, estendida ao SERVIÇO:

```
NÍVEL 1a · PADRÃO-OURO   a seguradora nomeia o serviço na tela de RESUMO
                         📊 existe em 6 das 10 (allianz 37 · yelum 26 · porto 20
                         · hdi 15 · azul 11 · alfa 3)
NÍVEL 1b · A RESPOSTA    a tecla/rótulo, decodificado CONTRA AQUELA TELA
NÍVEL 2  · O TEXTO       `direction='out'` obrigatório, como reserva
```

⚠️ 🔴 **E a regex do padrão-ouro que a SPEC-083 §10 publica NÃO REPRODUZ:**
`\nservi[çc]o:` devolve **1 sessão**, não 37. O separador não é quebra de linha —
é o **asterisco de negrito**: o texto real é `*Serviço:* *encanador*;`. A regex que
reproduz os 37 e os 19 rótulos é `\*servi[çc]o\*?:\*?[ ]*\*?([^*;\n]{1,55})`.

🔴 **A REGRA DO EMPATE, que pega o que o teste dos 80% deixa passar:** dois
serviços com **exatamente a mesma contagem** de sessões na mesma seguradora são
**uma tela**, não dois sinais. 📊 O teste dos 80% só reprova a azul (88,9%); o do
empate pega azul, zurich, alfa e tokio.

---

## CA-069 · 937 respostas de botão estão vazias e são irrecuperáveis — **ESSENCIAL**

> Registrado em 21/08/2026. Achado pelo JUIZ 2 e reproduzido pelo executor.

### Problema

📊 Medido em `observed_events`:

```
seguradora   button_reply   com `text` VAZIO   recuperável por interactive->>'title'
yelum             887             370                        0
hdi               540             263                        0
porto             361             167                        0
bradesco          129              62                        0
azul              110              54                        0
mapfre · zurich · tokio            21                        0
                                 ────
                                  937                        0
```

`interactive` guardou apenas as **chaves** (`selectedButtonID` entre elas) — sem os
valores. **A escolha do segurado não está no banco.**

### Consequência, e ela é grande

É a maior causa isolada de perda do **nível 1** das duas cascatas (ramo e serviço).
📊 A yelum tem 13 sessões longas indefinidas hoje; 370 dos seus botões estão em
branco. O corpus e a régua medem uma URA cujas respostas foram apagadas na
ingestão.

### Decisão

- **Não se conserta a ingestão nesta SPEC** — é fora do escopo da 083.
- `regua_motor.eventos_observados()` passa a selecionar `msg_type` e `interactive`,
  para que um consumidor possa ao menos **ver** que a resposta existiu.
- Vai para `PENDENCIAS.md` com dono 🤖 e o que destrava: gravar `selectedButtonID`
  no ingestor. 🔴 **E com o controle que prova o conserto:** as 13 sessões longas
  indefinidas da yelum têm de cair depois dele.
