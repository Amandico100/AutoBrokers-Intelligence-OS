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
