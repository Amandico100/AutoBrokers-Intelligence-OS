# SPEC-060 — AutoBrokers Research Intelligence

**Produto:** AutoBrokers Intelligence OS  
**Status:** CANÔNICA E AUTORIZADA PARA EXECUÇÃO — aprovada pelo Founder em 24/07/2026  
**Autoridade superior:** `SPEC-052-cerebro-cognitivo-unificado-autobrokers.md`, `SPEC-053-autobrokers-work-os-core-harness.md`, `SPEC-054-foundation-hardening-schema-governance.md`, `SPEC-055-durable-work-runs-queue-checkpoints-hitl.md`, `SPEC-056-skill-registry-tool-gateway.md`, `SPEC-057-artifact-hub-report-studio.md`, `SPEC-058-auxiliary-routine-factory.md` e `SPEC-059-briefing-proatividade-garimpo-v3.md`  
**Runtime preservado:** Smith + LangGraph/LangChain + FastAPI + Supabase/Postgres + Redis + Qdrant + MinIO  
**Nome oficial do agente central:** **AutoBrokers**  
**Escopo:** criar a camada canônica de pesquisa interna e externa do AutoBrokers: busca, descoberta, scraping permitido, crawling, extração, verificação, claims, citações, monitoramento, inteligência regulatória, seguradoras, concorrentes, SEO/AEO, descoberta de empresas, Evidence Packs, dossiês, custos, segurança e conexão com Work Runs, Skills, Artifact Hub, Intelligence Fabric e Knowledge Candidates.  
**Natureza desta SPEC:** autoriza migrations, backend, adapters de providers, Skills, Tool Releases, APIs, UI, templates, monitors, migração do web search atual, deploy, cutover e ativação em produção.  
**Dependência de execução:** as SPECs 054–059 devem estar implementadas ou ser executadas no mesmo programa na ordem canônica.

---

# 0. Comando direto ao executor — Fable, Opus, Codex ou equivalente

Você está autorizado a **implementar integralmente esta SPEC em linha reta**.

Esta não é uma SPEC para:

- apenas trocar Tavily por Firecrawl;
- criar uma tool que devolve três links;
- escrever respostas sem citações rastreáveis;
- criar um “agente pesquisador” paralelo ao Smith;
- armazenar toda a internet no RAG;
- fazer scraping indiscriminado;
- raspar a interface do Google Maps;
- criar relatórios bonitos sem base verificável;
- deixar a pesquisa avançada desligada permanentemente depois da implementação.

Ao final da mesma iniciativa:

- o AutoBrokers deverá responder perguntas atuais com fontes e datas;
- pesquisas complexas deverão criar Work Runs duráveis;
- o sistema deverá planejar a pesquisa antes de consumir providers caros;
- claims relevantes deverão possuir citações no nível da afirmação;
- fontes oficiais deverão prevalecer em seguros, legislação e regulação;
- Firecrawl deverá estar disponível como capacidade global da plataforma;
- Tavily deverá ser preservado e evoluído como provider homologado;
- descoberta de empresas deverá usar APIs e fontes permitidas;
- a interface do Google Maps não deverá ser raspada;
- pesquisas deverão gerar dossiês, matrizes, planilhas e Evidence Packs pelo Artifact Hub;
- monitors recorrentes deverão produzir Signals da SPEC-059 somente quando houver mudança relevante;
- pesquisa aceita como conhecimento durável deverá gerar Knowledge Candidate, nunca publicar diretamente no RAG;
- custos deverão ser atribuídos por tenant, Skill, provider e Work Run;
- prompt injection e conteúdo web malicioso deverão ser tratados como entrada não confiável;
- Amandus, Resulta e AutoFleet deverão passar pelos critérios de lançamento;
- o caminho canônico deverá permanecer ativo em produção ao encerrar o programa.

## 0.1 Doutrina de lançamento

```text
Entender a pergunta.
Definir o nível de rigor.
Planejar fontes e orçamento.
Pesquisar com providers adequados.
Adquirir conteúdo de forma permitida.
Extrair fatos e claims.
Verificar e contradizer.
Citar no nível da afirmação.
Entregar um resultado utilizável.
Monitorar mudanças quando solicitado.
Transformar aprendizado durável em candidato governado.
```

## 0.2 Proibições centrais

Não criar:

- outro runtime;
- outro Work Run;
- outro Tool Gateway;
- outro Artifact Hub;
- outro Intelligence Fabric;
- outro RAG;
- outro publisher de conhecimento;
- outro scheduler;
- outro sistema de approvals;
- uma tabela de execução concorrente a `work_runs`;
- um provider com autoridade soberana sobre claims;
- uma resposta profunda baseada em um único snippet;
- scraping de área autenticada sem autorização e corredor próprio;
- bypass de paywall, CAPTCHA, login ou controle de acesso;
- download massivo incompatível com termos de uso;
- coleta de PII sem finalidade, base e policy;
- prospecção automática com dados pessoais coletados de forma obscura;
- disparo de mensagens para leads dentro da Skill de pesquisa;
- publicação automática no conhecimento global;
- cópia integral de páginas protegidas quando um resumo e evidência bastam;
- retenção ilimitada de conteúdo externo;
- monitor que alerta por mudança cosmética;
- versão beta permanentemente desligada.

Feature flags são permitidas apenas para rollback e corte controlado durante a mesma iniciativa.

## 0.3 Número de blocos

A execução deverá ocorrer em **três blocos macro**, o menor número compatível com segurança, migração e lançamento:

1. **Bloco A — Research Foundation, providers, fontes, segurança e claims**;
2. **Bloco B — Skills, artifacts, monitors, UX e integração operacional**;
3. **Bloco C — experiências de lançamento, cutover, canários e produção**.

Com os gates verdes, avançar automaticamente.

## 0.4 Saída obrigatória

Ao final deverão existir e estar ativos:

- Research Orchestrator único;
- Research Request e Research Plan canônicos;
- Source Registry e Source Policy;
- adapters homologados para Tavily e Firecrawl;
- provider oficial para descoberta de empresas por lugares;
- direct fetch seguro para fontes oficiais quando adequado;
- pesquisa rápida, verificada, profunda e recorrente;
- source snapshots e hashes;
- claims estruturados;
- citações claim-level;
- contradição e verificação;
- Evidence Packs;
- dossiês web/PDF;
- matrizes XLSX/CSV;
- monitors e change detection;
- integração com Intelligence Signals;
- integração com Knowledge Candidates;
- cache e dedupe governados;
- quotas, budgets e metering;
- dashboard mínimo de pesquisas;
- Portal Admin mínimo de providers, fontes, monitors, custos e qualidade;
- migração do `TavilyService` e `WebSearchTool` históricos;
- remoção da tool antiga como autoridade soberana;
- Skills iniciais publicadas;
- Auxiliar global de Radar de Mercado configurável;
- Amandus, Resulta e AutoFleet validados;
- relatório final de execução publicado.

---

# 1. Ordem de leitura e autoridade

Antes de editar código ou banco:

1. atualizar a `main`;
2. registrar commit inicial;
3. ler SPEC-052;
4. ler SPEC-053;
5. ler SPEC-054 e relatório final;
6. ler SPEC-055 e relatório final;
7. ler SPEC-056 e relatório final;
8. ler SPEC-057 e relatório final;
9. ler SPEC-058 e relatório final;
10. ler SPEC-059 e relatório final;
11. ler ADR-001, ADR-002 e ADR-003;
12. ler SPEC-014 e documentos históricos de web search apenas como fundação subordinada;
13. ler `backend/app/services/tavily_service.py`;
14. ler `backend/app/agents/tools/web_search.py`;
15. ler Capability Registry, Tool Gateway, Work Runs, Artifact Hub, Intelligence Fabric e Auxiliary Factory reais;
16. confirmar schema vivo em modo read-only;
17. confirmar chaves/providers configurados sem revelar segredos;
18. confirmar planos, quotas e custos atuais diretamente nas documentações oficiais;
19. confirmar termos, políticas e limitações das fontes iniciais;
20. confirmar comportamento de Amandus, Resulta e AutoFleet.

Comandos mínimos:

```bash
git fetch origin
git checkout main
git pull origin main
git rev-parse HEAD
git status --short
```

Ordem normativa:

```text
SPEC-052
→ SPEC-053
→ SPEC-054
→ SPEC-055
→ SPEC-056
→ SPEC-057
→ SPEC-058
→ SPEC-059
→ SPEC-060
→ SPECs posteriores subordinadas
→ ADRs e documentos históricos quando não conflitarem
→ código atual como estado de implementação
```

---

# 2. Visão de produto

O corretor não precisa apenas de “busca na internet”.

Ele precisa pedir:

- “Pesquise o que mudou na SUSEP esta semana e o que afeta minha corretora.”
- “Compare o posicionamento de dez concorrentes da minha região.”
- “Analise meu site e diga como melhorar SEO e presença nas respostas das IAs.”
- “Encontre cinquenta empresas da região com perfil para seguro empresarial.”
- “Monitore as páginas de uma seguradora e me avise quando houver mudança relevante.”
- “Monte um dossiê sobre este produto, com fontes oficiais e riscos.”
- “Verifique se esta informação que recebi está correta.”

E receber:

- fontes confiáveis;
- fatos separados de interpretação;
- data de publicação e de recuperação;
- contradições;
- nível de confiança;
- limitações;
- planilha ou relatório pronto;
- ação possível no AutoBrokers;
- monitoramento recorrente quando solicitado.

A promessa desta SPEC é:

> **O AutoBrokers transforma a web e fontes oficiais em inteligência verificável, utilizável e acionável para corretoras de seguros, sem exigir que cada corretora contrate ou configure ferramentas de pesquisa.**

## 2.1 Diferencial vertical

O diferencial não será possuir Firecrawl ou Tavily.

O diferencial será combinar:

- conhecimento global de seguros;
- dados privados autorizados da corretora;
- fontes oficiais atuais;
- Work Runs duráveis;
- Skills especializadas;
- artifacts profissionais;
- monitoramento;
- portais e sistemas operacionais;
- Briefings e recomendações;
- execução real depois da pesquisa.

## 2.2 Resultado empresarial

A pesquisa deverá ajudar a corretora a:

- tomar decisões mais rápido;
- reduzir tempo manual;
- acompanhar mudanças regulatórias;
- entender seguradoras e produtos;
- analisar concorrentes;
- melhorar presença digital;
- encontrar empresas potenciais dentro de regras permitidas;
- preparar reuniões e apresentações;
- identificar oportunidades;
- validar informações;
- transformar tarefas recorrentes em Rotinas e Auxiliares.

---

# 3. Estado atual auditado

## 3.1 Peças existentes

O repositório já possui:

- `TavilyService`;
- `WebSearchTool`;
- `TAVILY_API_KEY` em configuração;
- capability `platform.web.search`;
- autorização da busca web para Core, Auxiliares e subagentes;
- LangGraph/Smith;
- Tool Gateway planejado/canônico;
- Work Runs;
- Artifact Hub;
- Intelligence Fabric;
- Vault;
- budgets e metering.

## 3.2 Limitações atuais

O serviço atual:

- executa somente Tavily Search básico;
- retorna no máximo três resultados por padrão;
- devolve texto formatado, não objetos de fonte;
- não possui Research Plan;
- não possui claims;
- não possui citações claim-level;
- não possui source registry;
- não distingue fontes oficiais de secundárias;
- não faz verificação cruzada;
- não registra snapshots e hashes;
- não possui monitoramento;
- não possui crawling canônico;
- não possui policy de robots/termos;
- não possui cache governado;
- não possui budget por pesquisa;
- não produz artifacts;
- não gera Signals;
- não cria Knowledge Candidates;
- não possui proteção especializada contra prompt injection web;
- usa `_arun` chamando a execução síncrona;
- registra a query em log sem uma política explícita de redaction;
- trata Tavily como string de contexto, não como provider versionado.

## 3.3 Decisão de migração

Preservar:

- a chave e integração Tavily existentes;
- testes úteis;
- capability `platform.web.search` como fundação histórica;
- uso de plataforma, sem exigir chave da corretora.

Evoluir:

- `TavilyService` para adapter homologado;
- `WebSearchTool` para tool/release do Tool Gateway;
- resposta textual para Source/Claim/Citation estruturados;
- pesquisa simples para modos de rigor distintos.

Depois do cutover:

- nenhum agente recebe a tool antiga diretamente;
- nenhuma resposta profunda usa o retorno bruto antigo como autoridade;
- o adapter Tavily permanece, mas o Research Orchestrator governa seu uso.

---

# 4. Decisões arquiteturais congeladas

## 4.1 O AutoBrokers é dono da pesquisa

Provider externo pode:

- buscar;
- rastrear;
- extrair;
- resumir;
- auxiliar planejamento.

Provider externo não é autoridade sobre:

- plano final;
- política de fontes;
- claims aceitos;
- citações apresentadas;
- classificação de risco;
- verdade de seguros;
- publicação no RAG;
- ação no sistema;
- outcome.

## 4.2 Firecrawl é capacidade da plataforma

A chave é da AutoBrokers.

A corretora não precisa:

- contratar Firecrawl;
- criar conta;
- fornecer chave;
- conhecer a ferramenta.

O custo será atribuído ao tenant/Work Run conforme plano e billing.

## 4.3 Firecrawl não substitui Tavily

Estratégia inicial:

- **Tavily:** busca rápida, pesquisa orientada a LLM, descoberta inicial, fallback e provider complementar;
- **Firecrawl:** scrape, crawl, map, parse, conteúdo completo, extração estruturada e aquisição de sites;
- **Google Places API ou provider oficial equivalente:** descoberta de empresas e lugares;
- **Direct Fetch governado:** fontes oficiais, RSS, APIs, sitemaps e documentos quando mais confiável e econômico;
- **browser público homologado:** somente quando conteúdo legítimo exigir interação permitida;
- **Portal Worker:** continua exclusivo para sistemas autenticados de seguradoras e gestão.

## 4.4 Provider-agnostic

O sistema deverá permitir homologar novos providers sem reescrever Skills:

- Exa;
- Brave Search API;
- APIs oficiais;
- bases regulatórias;
- providers regionais;
- self-hosting futuro quando justificado.

Nenhum deles será obrigatório para o lançamento além do conjunto aprovado pelo executor e Founder.

## 4.5 Google Maps

É proibido usar scraping da interface do Google Maps como caminho canônico de prospecção.

Para empresas e locais:

```text
Google Places API / provider licenciado
→ Place IDs e campos permitidos
→ enrichment do website público via Firecrawl
→ dedupe
→ planilha/artifact
```

Retenção, atribuição e uso dos campos deverão respeitar as políticas vigentes do provider.

## 4.6 Pesquisa não é RAG

- pesquisa consulta fontes atuais;
- RAG recupera conhecimento já governado;
- monitor observa mudanças;
- Artifact entrega o resultado;
- Knowledge Candidate propõe aprendizado durável.

Nenhuma página pesquisada entra automaticamente no Qdrant global.

---

# 5. Ontologia oficial

## 5.1 Research Request

Pedido do usuário ou sistema contendo objetivo, escopo, rigor, prazo, formato e orçamento.

## 5.2 Research Mode

Nível operacional de pesquisa.

## 5.3 Research Plan

Plano versionado que define subquestões, fontes, providers, orçamento, critérios de parada e output.

## 5.4 Source Policy

Regra que classifica uma fonte, domínio, tipo de conteúdo e usos permitidos.

## 5.5 Source Record

Identidade estável de uma fonte consultada.

## 5.6 Source Snapshot

Estado recuperado de uma fonte em determinado momento, com hash e metadata.

## 5.7 Extracted Fact

Dado extraído diretamente da fonte.

## 5.8 Claim

Afirmação que poderá aparecer no resultado e precisa de sustentação.

## 5.9 Citation

Ligação entre Claim e evidência.

## 5.10 Contradiction

Conflito entre claims, fontes ou versões.

## 5.11 Research Finding

Síntese verificável de múltiplos claims.

## 5.12 Evidence Pack

Pacote estruturado de claims, fontes, citações, snapshots, validade e limitações.

## 5.13 Research Monitor

Configuração recorrente que observa fontes ou tópicos.

## 5.14 Research Observation

Mudança ou ausência de mudança registrada por um monitor.

## 5.15 Research Artifact

Dossiê, relatório, matriz, briefing, planilha ou apresentação gerada pelo Artifact Hub.

---

# 6. Arquitetura canônica

```text
Chat / Rotina / Auxiliar / Briefing / Admin
                      │
                      ▼
              Research Request
                      │
                      ▼
           Research Orchestrator
                      │
             Research Plan + Budget
                      │
       ┌──────────────┼───────────────┐
       ▼              ▼               ▼
 Search Providers  Source Registry  Official APIs
       │              │               │
       └──────────────┼───────────────┘
                      ▼
        Acquisition / Crawl / Extract
                      │
                      ▼
     Sanitization + Prompt Injection Guard
                      │
                      ▼
      Facts + Claims + Citations + Conflict
                      │
                      ▼
             Verifier / Stop Rules
                      │
       ┌──────────────┼───────────────┐
       ▼              ▼               ▼
  Artifact       Intelligence       Knowledge
   Hub             Fabric           Candidate
       │              │               │
       ▼              ▼               ▼
  Entrega         Briefing/Alert    Curadoria
```

## 6.1 Autoridades

| Responsabilidade | Autoridade |
|---|---|
| execução | `work_runs` |
| planejamento | `research_plans` |
| providers | Tool Registry/Tool Releases |
| fontes | `research_sources` + policies |
| snapshots | `research_source_snapshots` |
| claims | `research_claims` |
| citações | `research_claim_citations` |
| artifacts | Artifact Hub |
| monitoramento | `research_monitors` |
| mudança relevante | Intelligence Fabric |
| conhecimento durável | Knowledge Candidate da SPEC-052 |
| segredos | Vault |
| acesso | Capability Registry |
| custo | usage/metering + research usage |

## 6.2 Serviços

Criar/consolidar:

```text
backend/app/services/research/
```

Componentes mínimos:

- `orchestrator.py`;
- `planner.py`;
- `mode_resolver.py`;
- `source_registry.py`;
- `source_policy.py`;
- `provider_router.py`;
- `query_decomposer.py`;
- `acquisition_service.py`;
- `content_sanitizer.py`;
- `prompt_injection_guard.py`;
- `fact_extractor.py`;
- `claim_service.py`;
- `citation_service.py`;
- `contradiction_service.py`;
- `verifier.py`;
- `freshness_service.py`;
- `cache_service.py`;
- `monitor_service.py`;
- `change_detector.py`;
- `places_service.py`;
- `lead_enrichment_service.py`;
- `knowledge_candidate_adapter.py`;
- `intelligence_adapter.py`;
- `artifact_adapter.py`;
- `legacy_tavily_adapter.py`;
- `policy.py`;
- `schemas.py`;
- `providers/`;

Nenhum serviço cria runtime, worker ou scheduler paralelo.

---

# 7. Modos de pesquisa

## 7.1 `quick`

Uso:

- pergunta atual simples;
- até poucas fontes;
- baixa latência;
- sem Artifact obrigatório.

Requisitos:

- pelo menos uma fonte adequada;
- data de recuperação;
- citações quando houver fatos externos;
- não usar para alto risco.

## 7.2 `verified`

Uso:

- informação importante;
- comparação;
- decisão operacional;
- seguros e mercado.

Requisitos:

- duas ou mais fontes quando possível;
- fonte oficial para claim crítico;
- contradição;
- claim-level citations;
- Evidence Pack leve.

## 7.3 `deep`

Uso:

- dossiê;
- concorrentes;
- mercado;
- produto;
- regulação;
- planejamento estratégico.

Requisitos:

- Work Run;
- Research Plan;
- orçamento;
- decomposição;
- múltiplas famílias de fontes;
- verificação;
- Artifact;
- anexos e metodologia.

## 7.4 `site_audit`

Uso:

- SEO;
- AEO/GEO;
- conteúdo;
- estrutura;
- concorrente;
- documentação.

Requisitos:

- Map/Crawl;
- limites de páginas;
- sitemap/robots;
- dados técnicos;
- análise de conteúdo;
- recomendações priorizadas.

## 7.5 `business_discovery`

Uso:

- empresas potenciais;
- fornecedores;
- parceiros;
- negócios por região e categoria.

Requisitos:

- Places API/provider autorizado;
- finalidade empresarial;
- dedupe;
- campos permitidos;
- sem coleta obscura de dados pessoais;
- Artifact tabular.

## 7.6 `monitor`

Uso:

- legislação;
- seguradora;
- produto;
- concorrente;
- página;
- tópico.

Requisitos:

- Rotina/trigger canônico;
- snapshots;
- diff;
- significance score;
- cooldown;
- Signal somente quando relevante.

## 7.7 `claim_check`

Uso:

- “isso é verdade?”;
- validar notícia;
- validar regra;
- validar informação de seguro.

Requisitos:

- decompor claim;
- fonte oficial/primária;
- veredito com incerteza;
- não usar apenas snippet.

---

# 8. Source Registry e política de fontes

## 8.1 Princípio

Nem toda fonte pública possui a mesma autoridade.

## 8.2 Tiers

### Tier 0 — autoridade oficial

- legislação;
- órgãos reguladores;
- Diário Oficial;
- SUSEP;
- CNSP;
- ANPD;
- sites oficiais de seguradoras;
- documentos oficiais do produto;
- APIs oficiais.

### Tier 1 — fonte primária institucional

- comunicação oficial da empresa;
- relatório corporativo;
- central de ajuda;
- documentação técnica oficial;
- página oficial do serviço.

### Tier 2 — fonte especializada reconhecida

- entidades setoriais;
- associações;
- estudos com metodologia;
- publicações técnicas identificáveis.

### Tier 3 — imprensa e análise secundária confiável

- veículos reconhecidos;
- pesquisa jornalística;
- análise de mercado com autoria.

### Tier 4 — fonte comunitária

- fóruns;
- redes sociais;
- avaliações;
- blogs pessoais.

### Tier 5 — conteúdo não verificado

- agregadores sem origem;
- conteúdo gerado por IA sem fontes;
- páginas anônimas;
- spam.

## 8.3 Regras

- claims de cobertura, exclusão, obrigação legal e regulação exigem Tier 0/1;
- Tier 4 pode indicar experiência ou opinião, não fato universal;
- Tier 5 não sustenta claim relevante;
- fontes patrocinadas devem ser identificadas;
- data e versão importam;
- fonte antiga pode estar correta historicamente e inválida atualmente;
- fonte oficial contraditória prevalece conforme vigência e hierarquia;
- nenhuma lista de domínios substitui análise de página e validade.

## 8.4 Source Policy

Cada política declara:

- domínio/padrão;
- owner;
- tier;
- categoria;
- país;
- idioma;
- robots status;
- termos revisados;
- conteúdo permitido;
- métodos permitidos;
- taxa máxima;
- retenção;
- cache;
- citações;
- uso comercial permitido;
- PII;
- login permitido ou proibido;
- paywall;
- data da revisão;
- responsável.

---

# 9. Estratégia de providers

## 9.1 Adapter contract

Todo provider implementa:

```text
provider_key
release
capabilities
health
search()
extract()
crawl()
map()
research() optional
usage()
rate_limit
cost_estimate()
data_retention_policy
regional_support
```

## 9.2 Tavily

Preservar e evoluir para:

- Search basic/advanced;
- Extract;
- Crawl;
- Map;
- Research quando homologado;
- uso assíncrono real;
- retorno estruturado;
- usage metering;
- domain filters;
- temporal filters;
- raw content somente quando necessário.

A integração oficial atual recomenda pacote atualizado que suporte Search, Extract, Map, Crawl e Research.

## 9.3 Firecrawl

Homologar Tool Releases para:

- `research.firecrawl.search`;
- `research.firecrawl.scrape`;
- `research.firecrawl.crawl`;
- `research.firecrawl.map`;
- `research.firecrawl.parse`;
- `research.firecrawl.extract_structured`;
- `research.firecrawl.agent` somente em casos aprovados;
- `research.firecrawl.browser` somente em casos públicos e permitidos.

Usar:

- `onlyMainContent`;
- formatos mínimos necessários;
- cache conforme policy;
- ZDR quando exigido;
- lockdown quando adequado;
- limites de URL/página;
- parsers de PDF quando apropriado;
- location/language quando necessário.

Não permitir:

- `skipTlsVerification=true` por padrão;
- browser irrestrito;
- login clandestino;
- actions arbitrárias fora do Tool Gateway;
- screenshots desnecessários em conteúdo sensível;
- armazenamento sem prazo.

## 9.4 Places Provider

Tool Release:

```text
research.places.search_businesses
research.places.get_details
```

Campos devem usar Field Mask mínimo.

Deve registrar:

- provider;
- place ID;
- campos solicitados;
- custo/SKU;
- attribution;
- retenção permitida;
- query e região redigidas quando necessário.

## 9.5 Direct Fetch

Para fonte oficial simples:

- HTTP Egress Guard da SPEC-054;
- DNS/IP validation;
- redirects limitados;
- content length;
- MIME allowlist;
- timeout;
- TLS obrigatório;
- robots/terms policy;
- sanitização.

## 9.6 Router

O provider router considera:

- modo;
- tipo de fonte;
- domínio;
- formato;
- idioma;
- região;
- freshness;
- custo;
- latência;
- health;
- retenção;
- confiança histórica;
- disponibilidade.

Não escolher provider somente pelo menor preço.

---

# 10. Modelo de dados canônico

Todas as migrations seguem APPLY/VERIFY/ROLLBACK da SPEC-054.

## 10.1 `research_requests`

```text
id uuid PK
company_id uuid NOT NULL
user_id uuid NULL
conversation_id uuid NULL
work_run_id uuid NULL
request_type text NOT NULL
mode text NOT NULL
objective text NOT NULL
question text NOT NULL
scope jsonb NOT NULL
constraints jsonb NOT NULL
requested_outputs jsonb NOT NULL
freshness_requirement text NULL
source_requirements jsonb NOT NULL
time_budget_seconds integer NULL
budget_brl numeric NULL
status text NOT NULL
created_at timestamptz NOT NULL
updated_at timestamptz NOT NULL
```

## 10.2 `research_plans`

```text
id uuid PK
company_id uuid NOT NULL
research_request_id uuid NOT NULL
work_run_id uuid NOT NULL
version integer NOT NULL
status text NOT NULL
subquestions jsonb NOT NULL
search_strategy jsonb NOT NULL
source_strategy jsonb NOT NULL
provider_strategy jsonb NOT NULL
stop_rules jsonb NOT NULL
verification_rules jsonb NOT NULL
output_contract jsonb NOT NULL
estimated_cost_brl_min numeric NULL
estimated_cost_brl_max numeric NULL
approved_at timestamptz NULL
created_at timestamptz NOT NULL
```

Plan publicado para execução é imutável.

## 10.3 `research_sources`

```text
id uuid PK
canonical_url text NOT NULL
normalized_domain text NOT NULL
source_type text NOT NULL
publisher text NULL
title text NULL
country text NULL
language text NULL
trust_tier integer NOT NULL
official boolean NOT NULL
source_policy_id uuid NULL
first_seen_at timestamptz NOT NULL
last_seen_at timestamptz NOT NULL
status text NOT NULL
metadata jsonb NOT NULL
```

URL canônica e domínio devem ser normalizados.

## 10.4 `research_source_snapshots`

```text
id uuid PK
company_id uuid NULL
research_source_id uuid NOT NULL
work_run_id uuid NULL
provider_key text NOT NULL
retrieved_at timestamptz NOT NULL
published_at timestamptz NULL
modified_at timestamptz NULL
http_status integer NULL
content_type text NULL
content_hash text NOT NULL
structure_hash text NULL
storage_ref text NULL
clean_text_ref text NULL
excerpt_redacted text NULL
retention_class text NOT NULL
valid_until timestamptz NULL
robots_result text NULL
terms_policy_result text NULL
prompt_injection_status text NOT NULL
metadata jsonb NOT NULL
```

`company_id = NULL` somente para snapshot público compartilhável e sem contexto privado.

## 10.5 `research_claims`

```text
id uuid PK
company_id uuid NOT NULL
research_request_id uuid NOT NULL
work_run_id uuid NOT NULL
claim_key text NOT NULL
claim_text text NOT NULL
claim_type text NOT NULL
status text NOT NULL
confidence numeric NOT NULL
risk_level text NOT NULL
freshness text NOT NULL
valid_from timestamptz NULL
valid_until timestamptz NULL
contradiction_status text NOT NULL
verification_status text NOT NULL
created_at timestamptz NOT NULL
updated_at timestamptz NOT NULL
```

Estados:

```text
draft
supported
partially_supported
unsupported
contradicted
stale
withdrawn
```

## 10.6 `research_claim_citations`

```text
id uuid PK
company_id uuid NOT NULL
claim_id uuid NOT NULL
source_snapshot_id uuid NOT NULL
citation_role text NOT NULL
support_strength numeric NOT NULL
source_excerpt text NULL
locator jsonb NOT NULL
created_at timestamptz NOT NULL
```

Roles:

```text
supports
contradicts
context
methodology
```

## 10.7 `research_findings`

```text
id uuid PK
company_id uuid NOT NULL
research_request_id uuid NOT NULL
work_run_id uuid NOT NULL
finding_type text NOT NULL
title text NOT NULL
summary text NOT NULL
fact_statement text NULL
inference_statement text NULL
limitations text NULL
confidence numeric NOT NULL
status text NOT NULL
created_at timestamptz NOT NULL
updated_at timestamptz NOT NULL
```

## 10.8 `research_finding_claims`

Liga Findings e Claims com role/weight.

## 10.9 `research_monitors`

```text
id uuid PK
company_id uuid NOT NULL
user_id uuid NULL
name text NOT NULL
monitor_type text NOT NULL
topic text NULL
source_policy_filter jsonb NOT NULL
url_filters jsonb NOT NULL
query_spec jsonb NOT NULL
cadence text NOT NULL
schedule_spec jsonb NOT NULL
timezone text NOT NULL
change_policy jsonb NOT NULL
severity_policy jsonb NOT NULL
channels jsonb NOT NULL
budget_brl numeric NULL
is_active boolean NOT NULL
routine_id uuid NOT NULL
created_at timestamptz NOT NULL
updated_at timestamptz NOT NULL
```

## 10.10 `research_observations`

```text
id uuid PK
company_id uuid NOT NULL
research_monitor_id uuid NOT NULL
work_run_id uuid NOT NULL
source_snapshot_id uuid NULL
observation_type text NOT NULL
change_class text NOT NULL
significance_score numeric NOT NULL
summary text NOT NULL
evidence jsonb NOT NULL
content_hash text NOT NULL
previous_content_hash text NULL
signal_id uuid NULL
status text NOT NULL
observed_at timestamptz NOT NULL
created_at timestamptz NOT NULL
```

## 10.11 `research_provider_usage`

```text
id uuid PK
company_id uuid NOT NULL
work_run_id uuid NOT NULL
research_request_id uuid NULL
provider_key text NOT NULL
operation text NOT NULL
request_count integer NOT NULL
units numeric NULL
provider_cost numeric NULL
cost_currency text NULL
cost_brl numeric NULL
latency_ms integer NULL
cache_hit boolean NOT NULL
status text NOT NULL
created_at timestamptz NOT NULL
```

## 10.12 `research_cache_entries`

```text
id uuid PK
scope text NOT NULL
company_id uuid NULL
cache_key text NOT NULL
source_snapshot_id uuid NULL
result_ref text NULL
content_hash text NOT NULL
fresh_until timestamptz NOT NULL
stale_until timestamptz NULL
policy_class text NOT NULL
created_at timestamptz NOT NULL
last_hit_at timestamptz NULL
hit_count integer NOT NULL
```

## 10.13 RLS e integridade

- todas as tabelas tenant-scoped com RLS;
- FKs company-scoped quando aplicável;
- service role governada;
- snapshots públicos compartilhados não podem conter query privada;
- unique/index por fingerprints e work_run;
- nenhuma evidência cross-tenant;
- sources globais não dão acesso ao resultado privado de pesquisa.

---

# 11. Research Request Contract

Todo pedido deve declarar ou inferir:

```text
objetivo
pergunta principal
subproduto desejado
modo
escopo geográfico
escopo temporal
idioma
fontes obrigatórias
fontes proibidas
freshness
profundidade
prazo
orçamento
formato
necessidade de monitoramento
risco
```

O sistema pergunta somente o que muda substancialmente a execução.

Exemplo:

> “Quer que eu compare apenas corretoras da sua cidade ou também concorrentes estaduais?”

Não perguntar:

> “Qual provider de crawl você prefere?”

---

# 12. Research Plan

## 12.1 Estrutura

```text
question
subquestions[]
claim targets[]
source families[]
queries[]
providers[]
acquisition methods[]
verification rules[]
stop rules[]
budget
output contract
```

## 12.2 Stop rules

Parar quando:

- claims críticos têm fonte suficiente;
- contradições foram explicadas;
- cobertura das subquestões atingiu threshold;
- ganho marginal de novas fontes ficou baixo;
- orçamento foi atingido;
- prazo foi atingido;
- fonte necessária é inacessível legitimamente;
- usuário pediu interrupção.

## 12.3 Replan

Replanejar quando:

- queries retornarem ruído;
- fonte oficial não for encontrada;
- provider estiver degradado;
- houver contradição relevante;
- escopo estiver amplo demais;
- orçamento exigir redução.

Replan cria nova versão do plano e evento na timeline.

---

# 13. Descoberta e busca

## 13.1 Query decomposition

A LLM pode decompor, mas a saída deve ser estruturada.

Dimensões:

- entidade;
- evento;
- data;
- local;
- tipo de fonte;
- idioma;
- domínio oficial;
- sinônimos;
- termos de seguro;
- exclusões.

## 13.2 Diversidade

Em pesquisa profunda, buscar quando aplicável:

- fonte oficial;
- fonte primária;
- fonte especializada;
- fonte secundária independente;
- fonte contraditória;
- perspectiva regional.

## 13.3 Snippet não é evidência final

Snippet de busca pode:

- ajudar descoberta;
- priorizar URL;
- indicar possível conteúdo.

Não pode sozinho:

- sustentar claim de alto risco;
- confirmar cobertura;
- confirmar obrigação legal;
- confirmar mudança vigente.

## 13.4 Search policy

- filtros de domínio;
- recency;
- país/idioma;
- query budget;
- dedupe por URL;
- normalização de tracking params;
- SafeSearch conforme caso;
- bloqueio de domínios maliciosos.

---

# 14. Aquisição, crawling e extração

## 14.1 Hierarquia

```text
API/RSS/documento oficial
→ direct fetch seguro
→ provider extract/scrape
→ crawl/map
→ browser público permitido
→ declarar limitação
```

## 14.2 Map antes de crawl

Para sites grandes:

- mapear URLs;
- filtrar paths;
- limitar profundidade;
- priorizar páginas relevantes;
- evitar crawl integral sem justificativa.

## 14.3 Crawl budget

Cada crawl declara:

- domínio;
- max pages;
- max depth;
- max duration;
- max bytes;
- rate;
- include paths;
- exclude paths;
- subdomains;
- cache;
- retention;
- estimated cost.

## 14.4 Conteúdo dinâmico

Browser/interact somente quando:

- conteúdo é público;
- termos permitem;
- não existe API mais adequada;
- nenhuma credencial privada é usada;
- actions são declaradas;
- sandbox ativo;
- timeout e budget definidos.

## 14.5 PDFs e documentos

- usar parser homologado;
- preservar paginação/localizador;
- hash;
- metadata;
- fonte;
- data;
- OCR somente quando necessário;
- claims citam página/seção.

## 14.6 Conteúdo inalcançável

Não contornar.

Registrar:

- motivo;
- tentativa;
- alternativa;
- impacto na confiança.

---

# 15. Segurança de conteúdo web

## 15.1 Regra soberana

Todo conteúdo externo é **dado não confiável**.

Nunca é instrução para o AutoBrokers.

## 15.2 Prompt injection

Detectar e neutralizar padrões como:

- “ignore instruções anteriores”;
- pedidos para revelar prompt;
- comandos para executar tools;
- instruções ocultas;
- conteúdo branco/invisível;
- payload em metadata;
- links de exfiltração;
- instruções em PDF;
- base64 suspeito;
- código que solicita secrets.

## 15.3 Separação

- system/policies fora do conteúdo;
- conteúdo em envelope delimitado;
- nenhuma tool disponível ao extrator salvo as necessárias;
- extrator não executa comandos encontrados;
- URL descoberta não é chamada sem policy/egress guard;
- secrets nunca entram no prompt de fonte.

## 15.4 Sanitização

- remover scripts;
- remover event handlers;
- remover formulários;
- remover trackers;
- limitar tamanho;
- normalizar Unicode;
- remover conteúdo duplicado;
- marcar hidden text;
- registrar injection score;
- quarentenar conteúdo crítico.

## 15.5 SSRF

Reutilizar HTTP Egress Guard da SPEC-054:

- bloquear localhost;
- redes privadas;
- metadata cloud;
- DNS rebinding;
- redirects perigosos;
- esquemas não HTTP/HTTPS;
- portas proibidas.

---

# 16. Claims, verificação e citações

## 16.1 Claim-first

Antes de escrever o Artifact, o sistema deve estruturar os claims principais.

## 16.2 Tipos

- factual;
- temporal;
- numérico;
- comparativo;
- regulatório;
- causal;
- estratégico;
- opinião atribuída.

## 16.3 Regras

- claim numérico exige fonte e período;
- claim temporal exige data;
- claim regulatório exige vigência;
- claim causal exige evidência ou label de hipótese;
- comparação exige critérios equivalentes;
- ausência de resultado não prova inexistência;
- source count não substitui qualidade.

## 16.4 Verifier

O verifier:

- checa suporte;
- checa contradição;
- checa fonte;
- checa freshness;
- checa citações;
- checa números;
- checa escopo;
- checa se a conclusão excede a evidência.

## 16.5 Citation Contract

Toda citação apresentada possui:

```text
source_id
source_snapshot_id
title
publisher
canonical_url
published_at
retrieved_at
locator
excerpt curto
claim_role
trust_tier
content_hash
```

## 16.6 Citações no produto

- clicáveis;
- associadas ao claim;
- não agrupadas genericamente no final quando puderem ser inline;
- fonte oficial identificada;
- data visível;
- link autorizado;
- sem expor storage path interno.

## 16.7 Quotes

- usar o mínimo necessário;
- preferir paráfrase;
- respeitar limites de copyright;
- quote literal com locator;
- nunca reproduzir artigo integral.

## 16.8 Contradição

Quando houver:

- apresentar os lados;
- explicar hierarquia e datas;
- reduzir confiança;
- não executar ação sensível;
- buscar fonte adicional;
- permitir revisão humana.

---

# 17. Freshness e validade

## 17.1 Classes

```text
real_time
hourly
daily
weekly
monthly
stable
historical
```

## 17.2 Freshness requirement

O pedido define quanto a informação pode estar desatualizada.

Exemplos:

- notícia: horas;
- regra vigente: fonte atual;
- telefone oficial: validação recente;
- histórico: data original;
- concorrente: semanas;
- legislação: vigência.

## 17.3 Stale

Resultado stale:

- pode ser mostrado como histórico;
- não pode ser apresentado como atual;
- deve indicar data;
- pode disparar refresh.

---

# 18. Pesquisa de seguros e fontes oficiais

## 18.1 Registry inicial

O executor deverá criar um catálogo inicial revisável para:

- SUSEP;
- CNSP;
- Diário Oficial da União;
- Planalto/legislação;
- ANPD;
- Receita Federal quando aplicável;
- Banco Central quando aplicável;
- sites oficiais de seguradoras;
- centrais oficiais de ajuda;
- documentos e condições oficiais;
- associações setoriais reconhecidas.

Não hardcodar conclusões. Hardcodar políticas e identidades de fonte.

## 18.2 Regulação

Toda análise regulatória contém:

- norma;
- órgão;
- número;
- publicação;
- vigência;
- alteração/revogação;
- escopo;
- impacto possível;
- label de não aconselhamento jurídico quando aplicável.

## 18.3 Seguradoras

Monitoramento poderá observar:

- produtos;
- canais;
- assistência;
- contatos;
- documentação;
- condições;
- comunicados;
- status de portal público;
- materiais para corretores.

Mudança de página não equivale automaticamente a mudança de regra.

## 18.4 Cobertura individual

Pesquisa web não confirma cobertura de um segurado.

A confirmação individual continua exigindo:

- apólice;
- Evidence Pack;
- InfoCap/Quiver/portal;
- fonte oficial aplicável.

---

# 19. Descoberta de empresas e prospecção responsável

## 19.1 Objetivo

Permitir pedidos como:

> “Toda semana encontre cinquenta empresas da região com perfil para seguro empresarial.”

## 19.2 Fluxo

```text
segmento + região + critérios
→ Places API/provider licenciado
→ dados permitidos
→ dedupe
→ enrichment do website público
→ classificação
→ planilha/artifact
→ entrega
```

## 19.3 Campos iniciais

Conforme policy do provider:

- empresa;
- categoria;
- endereço comercial;
- telefone comercial;
- website;
- place ID;
- status do negócio;
- região;
- fonte;
- data;
- critérios de fit;
- score explicável.

## 19.4 Proibições

- raspar Google Maps UI;
- coletar e-mail pessoal de funcionário sem base;
- inferir dado sensível;
- enriquecer com dados vazados;
- fazer perfil discriminatório;
- enviar WhatsApp/e-mail automaticamente dentro da pesquisa;
- fingir que lead é cliente interessado;
- armazenar campos além do permitido pelo provider;
- omitir attribution exigida.

## 19.5 Outreach

Pesquisa entrega lista.

Contato é outra ação:

- Skill de comunicação;
- consentimento/base;
- policy;
- aprovação;
- limite;
- opt-out;
- idempotência;
- canal autorizado.

## 19.6 Score de fit

Pode considerar:

- segmento;
- porte público aproximado quando verificável;
- localização;
- website;
- sinais de operação;
- produtos de seguro relevantes.

Não usar:

- renda presumida de pessoa;
- raça;
- saúde;
- religião;
- dados sensíveis;
- proxies discriminatórios.

---

# 20. Análise de concorrentes

## 20.1 Escopo

- posicionamento;
- produtos divulgados;
- presença local;
- site;
- SEO/AEO;
- conteúdo;
- canais;
- provas sociais públicas;
- diferenciais declarados;
- experiência digital pública.

## 20.2 Método

- critérios iguais;
- data comum;
- fontes por concorrente;
- separar declaração própria de evidência independente;
- nenhuma nota sem rubrica;
- sem afirmar faturamento ou carteira sem fonte.

## 20.3 Artifact

- resumo executivo;
- matriz comparativa;
- fontes;
- gaps;
- oportunidades;
- recomendações;
- plano de ação;
- XLSX opcional.

---

# 21. SEO, AEO e discoverability

## 21.1 Objetivo

Ajudar a corretora a ser encontrada por mecanismos de busca e sistemas de resposta.

## 21.2 Auditoria técnica

- robots.txt;
- sitemap;
- indexabilidade;
- titles;
- descriptions;
- canonicals;
- headings;
- structured data;
- links;
- status codes;
- redirects;
- mobile;
- performance quando provider/API disponível;
- duplicação;
- localização;
- páginas de serviço.

## 21.3 Auditoria de conteúdo

- intenção;
- cobertura temática;
- clareza;
- respostas diretas;
- entidades;
- autoridade;
- fontes;
- FAQs úteis;
- conteúdo local;
- consistência NAP;
- risco de conteúdo genérico.

## 21.4 AEO/GEO

Avaliar:

- conteúdo estruturado;
- respostas citáveis;
- evidência;
- autoria;
- atualização;
- páginas por produto/região;
- consistência de entidades;
- presença em fontes relevantes.

Não prometer ranking ou citação por IA.

## 21.5 Search Console

Quando houver conector autorizado:

- queries;
- páginas;
- impressões;
- cliques;
- CTR;
- posição;
- indexação.

Sem conector, declarar limitação.

---

# 22. Monitoramento e change intelligence

## 22.1 Tipos

- URL;
- domínio;
- query;
- entidade;
- norma;
- seguradora;
- concorrente;
- produto;
- tópico.

## 22.2 Detecção de mudança

Combinar:

- HTTP metadata;
- content hash;
- structure hash;
- diff textual;
- diff semântico;
- mudança em campos extraídos;
- publicação oficial;
- data de vigência.

## 22.3 Ruído

Suprimir:

- menu;
- banner;
- cookie;
- anúncio;
- timestamp automático;
- ordem de cards;
- tracking;
- whitespace;
- mudança sem efeito no conteúdo relevante.

## 22.4 Significance

Score baseado em:

- seção alterada;
- tipo de claim;
- fonte;
- magnitude;
- vigência;
- impacto;
- novidade;
- confiança.

## 22.5 Integração

```text
Research Observation
→ Intelligence Signal
→ Finding
→ Briefing/Alert
→ Recommendation
```

Somente mudança relevante gera Signal.

## 22.6 Falha de monitor

- registrar health;
- retry;
- não afirmar “sem mudança” se a fonte não foi acessada;
- alertar degradação quando persistente;
- não apagar último snapshot válido.

---

# 23. Pesquisa profunda

## 23.1 Workflow

```text
intake
→ plan
→ search
→ map/fetch
→ extract
→ claims
→ verify
→ contradiction
→ synthesize
→ artifact
→ review
→ delivery
```

## 23.2 Subagentes

Subagentes podem ser usados por família de fonte:

- oficial;
- concorrentes;
- mercado;
- técnico;
- verificação.

Cada um recebe:

- subquestão;
- tools mínimas;
- budget;
- limite de iteração;
- output schema;
- nenhuma capability herdada automaticamente.

## 23.3 Conselho de verificação

Não criar novo runtime.

Pode usar etapas do workflow:

- pesquisador;
- crítico;
- fact checker;
- sintetizador.

Todos dentro do Work Run e Skill.

## 23.4 Critério de completude

Medir:

- cobertura de subquestões;
- claims suportados;
- fontes oficiais;
- diversidade;
- contradições resolvidas;
- freshness;
- limitações.

---

# 24. Cache, dedupe e reaproveitamento

## 24.1 Tipos de cache

- search result cache;
- source snapshot cache;
- parsed document cache;
- public extraction cache;
- research synthesis cache tenant-scoped.

## 24.2 Compartilhamento seguro

Pode compartilhar entre tenants:

- snapshot de página pública;
- hash;
- metadata;
- conteúdo limpo sem query privada;
- conforme termos e retenção.

Não compartilhar:

- pergunta do usuário;
- plano;
- seleção estratégica;
- Artifact;
- claims tenant;
- dados internos;
- conexão.

## 24.3 Cache key

Inclui:

- URL/query normalizada;
- provider;
- options;
- idioma;
- região;
- policy;
- freshness class;
- schema/version.

## 24.4 Revalidação

- ETag/Last-Modified quando disponível;
- max age;
- conditional fetch;
- refresh assíncrono;
- stale-while-revalidate quando permitido.

## 24.5 Dedupe

- canonical URL;
- content hash;
- near duplicate;
- syndicated content;
- tracking parameters;
- mirrored press release.

Não contar cópias do mesmo release como fontes independentes.

---

# 25. Integração com Work OS

## 25.1 Work Runs

Criam Work Run:

- pesquisa verificada complexa;
- deep research;
- site audit;
- business discovery;
- monitor execution;
- artifact;
- verification extensa;
- Knowledge Candidate preparation.

Quick search pode ocorrer em um step do Work Run da conversa quando curta.

## 25.2 Checkpoints

Checkpoints entre:

- planejamento;
- descoberta;
- aquisição;
- extração;
- claims;
- verificação;
- artifact.

Restart não perde pesquisa.

## 25.3 Cancelamento

Cancelar:

- novos requests;
- crawls pendentes quando provider permitir;
- subagentes;
- artifact não iniciado.

Preservar:

- custo já consumido;
- fontes coletadas conforme retenção;
- timeline;
- resultado parcial claramente marcado.

## 25.4 Approvals

Exigir aprovação quando:

- orçamento supera limite;
- crawl é amplo;
- monitor recorrente tem custo relevante;
- dados pessoais poderão ser processados;
- browser público fará interações;
- envio externo será solicitado;
- fonte/uso possui risco jurídico.

---

# 26. Skills, Capability Packs e Tools

## 26.1 Capabilities

Evoluir o catálogo para incluir:

```text
platform.research.search
platform.research.extract
platform.research.crawl
platform.research.deep
platform.research.monitor
platform.research.claim_verify
platform.research.places
platform.research.site_audit
platform.research.regulatory
```

`platform.web.search` poderá permanecer como alias/deprecação controlada.

## 26.2 Capability Packs

```text
pack.research.quick
pack.research.verified
pack.research.deep
pack.research.site_audit
pack.research.regulatory
pack.research.business_discovery
pack.research.monitoring
```

## 26.3 Skills iniciais

### `research.quick_verified_answer`

Resposta atual com fontes e claim checks mínimos.

### `research.deep_dossier`

Dossiê completo sobre tema, empresa, produto ou mercado.

### `research.insurer_official_update`

Pesquisa fontes oficiais de seguradoras e identifica mudanças.

### `research.regulatory_watch`

Monitora normas e publicações oficiais.

### `research.competitor_analysis`

Compara concorrentes com critérios versionados.

### `research.website_seo_aeo_audit`

Audita site para SEO, AEO e discoverability.

### `research.business_lead_discovery`

Descobre empresas por região/segmento via provider autorizado.

### `research.company_enrichment`

Enriquece empresas com dados públicos permitidos.

### `research.source_monitor`

Cria monitor de fonte/tópico.

### `research.claim_verify`

Valida uma afirmação.

### `research.prepare_meeting_dossier`

Cria briefing de reunião com fontes e contexto autorizado.

## 26.4 Tool Releases

Mínimas:

```text
research.search_web
research.fetch_source
research.extract_urls
research.map_site
research.crawl_site
research.parse_document
research.extract_structured
research.search_places
research.get_place_details
research.verify_claims
research.create_monitor
research.get_monitor_status
```

Todas passam pelo Tool Gateway.

---

# 27. Artifact Hub

## 27.1 Tipos

- Research Brief;
- Dossiê;
- Evidence Pack;
- Matriz de concorrentes;
- Auditoria SEO/AEO;
- Radar regulatório;
- Planilha de empresas;
- apresentação executiva;
- source appendix;
- change report.

## 27.2 Conteúdo

Todo Artifact relevante contém:

- pergunta;
- escopo;
- data;
- metodologia;
- resumo executivo;
- findings;
- claims;
- fontes;
- limitações;
- conflitos;
- próximos passos;
- apêndice de citações;
- custo quando apropriado.

## 27.3 Visual

Reutilizar o Visual Acceptance Pack da SPEC-057.

Adicionar ao mesmo pack, sem criar sistema separado:

- Dossiê de Pesquisa;
- matriz de concorrentes;
- Evidence Pack;
- página Research Library;
- monitor/change card.

## 27.4 Formatos

- web;
- PDF;
- XLSX;
- CSV;
- PPTX quando solicitado;
- DOCX quando solicitado.

---

# 28. Integração com Intelligence Fabric

## 28.1 Research → Signal

Pode gerar Signal quando houver:

- nova norma;
- mudança oficial;
- alteração de produto;
- atualização de contato oficial;
- mudança competitiva relevante;
- risco de site;
- monitor degradado;
- fonte contraditória.

## 28.2 Não gerar Signal

- resultado de busca rotineiro;
- fonte duplicada;
- mudança cosmética;
- opinião isolada;
- inferência sem evidência;
- conteúdo velho reencontrado.

## 28.3 Briefings

Findings de pesquisa poderão entrar no Briefing:

- regulatório;
- mercado;
- seguradora;
- concorrente;
- discoverability.

Com validade e link para Artifact.

---

# 29. Integração com Knowledge Fabric

## 29.1 Elegibilidade

Pode gerar Knowledge Candidate:

- norma oficial;
- mudança confirmada de seguradora;
- documento oficial;
- procedimento estável;
- FAQ oficial;
- informação de produto com validade;
- aprendizado repetido e verificado.

## 29.2 Não elegível

- notícia passageira;
- opinião;
- lista de leads;
- relatório de concorrentes;
- score de SEO;
- recomendação estratégica;
- conteúdo sem fonte;
- dado privado do tenant;
- cópia integral de página.

## 29.3 Fluxo

```text
Research Claim elegível
→ Knowledge Candidate
→ classificação
→ provenance
→ validade
→ dedupe
→ contradição
→ Curador/Conselho
→ Publicador
```

Nunca publicação direta.

---

# 30. Research Library e experiência do corretor

## 30.1 Princípio

A pesquisa nasce pelo chat.

Uma biblioteca ajuda a encontrar resultados e monitors, mas não substitui o AutoBrokers.

## 30.2 Navegação mínima

```text
Inteligência
└── Pesquisas
    ├── Recentes
    ├── Monitores
    └── Fontes salvas
```

Evitar menu excessivo.

## 30.3 Chat

Entender:

- “Pesquise...”;
- “Verifique...”;
- “Compare...”;
- “Monitore...”;
- “Encontre empresas...”;
- “Transforme isso em planilha”;
- “Crie uma rotina semanal”;
- “Use apenas fontes oficiais”;
- “Explique de onde veio essa informação”.

## 30.4 Card de pesquisa

Mostrar:

- título;
- modo;
- status;
- etapa;
- fontes analisadas;
- custo estimado/real quando aplicável;
- data;
- Artifact;
- cancelar;
- monitorar;
- repetir com novo escopo.

## 30.5 Pesquisa concluída

- resumo;
- findings;
- confiança;
- fontes;
- limitações;
- Artifact;
- CTA de ação;
- opção de criar monitor.

## 30.6 Monitor

Usuário pode:

- editar tema;
- frequência;
- fontes;
- threshold;
- canais;
- custo;
- pausar;
- executar agora;
- ver mudanças.

---

# 31. Portal Admin mínimo

A SPEC-061 consolidará o Control Plane completo, mas esta SPEC entrega administração funcional.

## 31.1 Providers

- provider;
- operações;
- status;
- latência;
- erro;
- quota;
- custo;
- retenção;
- região;
- Tool Release;
- última chamada;
- fallback.

Ações:

- homologar;
- desativar;
- rollout;
- rollback;
- testar;
- alterar peso;
- definir limite.

## 31.2 Source Registry

- domínio;
- tier;
- policy;
- robots;
- termos;
- retenção;
- official;
- última revisão;
- incidentes;
- bloqueio.

## 31.3 Pesquisas

- tenant;
- modo;
- status;
- Work Run;
- fontes;
- claims;
- citações;
- custo;
- Artifact;
- erros;
- qualidade.

## 31.4 Monitores

- tenant;
- tópico;
- frequência;
- health;
- custo;
- últimas mudanças;
- Signals;
- falhas;
- ruído.

## 31.5 Qualidade

- citation coverage;
- unsupported claims;
- stale claims;
- source diversity;
- official-source rate;
- contradiction handling;
- prompt-injection detections;
- false positive monitor;
- user feedback.

## 31.6 Custos

- provider;
- tenant;
- Skill;
- Work Run;
- cache hit;
- custo médio por modo;
- orçamento;
- projeção.

## 31.7 Segurança

- URLs bloqueadas;
- SSRF;
- injection;
- robots/terms violations prevented;
- PII redaction;
- downloads/quarantine;
- browser actions.

---

# 32. APIs e tools

## 32.1 Tenant

```text
POST   /api/research
GET    /api/research
GET    /api/research/{id}
POST   /api/research/{id}/cancel
POST   /api/research/{id}/refresh
POST   /api/research/{id}/monitor
GET    /api/research/{id}/sources
GET    /api/research/{id}/claims
GET    /api/research/{id}/artifact
GET    /api/research/monitors
POST   /api/research/monitors
PATCH  /api/research/monitors/{id}
POST   /api/research/monitors/{id}/run
POST   /api/research/monitors/{id}/pause
DELETE /api/research/monitors/{id}
```

## 32.2 Admin

```text
GET    /api/admin/research/overview
GET    /api/admin/research/providers
POST   /api/admin/research/providers/{key}/test
POST   /api/admin/research/providers/{key}/rollout
POST   /api/admin/research/providers/{key}/rollback
GET    /api/admin/research/sources
PATCH  /api/admin/research/sources/{id}
GET    /api/admin/research/runs
GET    /api/admin/research/monitors
GET    /api/admin/research/quality
GET    /api/admin/research/costs
POST   /api/admin/research/replay
```

## 32.3 Core tools

```text
research.start
research.get_status
research.cancel
research.list_sources
research.explain_claim
research.create_monitor
research.update_monitor
research.list_monitors
research.export
research.verify_claim
```

## 32.4 Regras

- server-side auth;
- company scope;
- role/policy;
- idempotency key;
- budget;
- schema validation;
- audit event;
- stable error codes;
- URL não vem diretamente do client para fetch sem validação;
- nenhuma query livre no banco;
- output redigido.

---

# 33. FinOps, quotas e billing

## 33.1 Princípio

Provider cost não pode ficar invisível.

## 33.2 Medição

Por chamada:

- provider;
- operação;
- credits/units;
- custo de provider;
- moeda;
- conversão registrada quando aplicável;
- custo em BRL;
- cache;
- latência;
- páginas;
- bytes;
- Work Run;
- tenant;
- Skill.

## 33.3 Budget modes

```text
economy
standard
thorough
custom
```

## 33.4 Estimativa

Antes de deep/crawl/monitor caro:

- faixa de custo;
- fontes/páginas previstas;
- frequência;
- limites;
- policy de aprovação.

## 33.5 Quotas

- por plano;
- tenant;
- usuário;
- Skill;
- provider;
- período;
- concorrência;
- pages/minute.

## 33.6 Degradação

Quando orçamento baixo:

- reduzir fontes secundárias;
- preservar oficiais;
- usar cache;
- diminuir crawl;
- oferecer escopo menor;
- não reduzir factualidade silenciosamente.

## 33.7 Preços

Não hardcodar preços comerciais de provider na SPEC.

Criar catálogo versionado atualizado por Admin/integração.

---

# 34. Privacidade, LGPD, termos e direitos autorais

## 34.1 Minimização

- coletar somente o necessário;
- finalidade explícita;
- retenção por classe;
- PII redigida;
- source refs em vez de cópia;
- exclusão/revogação;
- audit trail.

## 34.2 Robots

Robots informa regras de crawling do site.

O sistema deve:

- consultar;
- registrar resultado;
- respeitar policy;
- não tratar robots como autorização jurídica completa;
- combinar com termos e uso pretendido.

## 34.3 Termos

- registrar revisão para fontes críticas;
- preferir API oficial;
- bloquear scraping proibido;
- não bypassar acesso;
- respeitar attribution;
- respeitar retenção do provider.

## 34.4 Copyright

- não republicar conteúdo integral;
- usar trechos mínimos;
- sintetizar;
- citar;
- armazenar snapshot somente conforme policy;
- limitar compartilhamento;
- expirar material quando necessário.

## 34.5 Leads

- tratar telefone/e-mail individual como dado pessoal quando aplicável;
- finalidade empresarial;
- base e policy;
- opt-out no outreach;
- não vender base bruta;
- não enriquecer com dados ilegítimos.

## 34.6 Segurança

- Vault;
- ZDR quando necessário;
- logs sem query sensível completa;
- encrypted storage;
- signed URLs;
- malware scan para downloads;
- sandbox;
- egress guard;
- provider DPA quando aplicável.

---

# 35. Migração do legado

## 35.1 `TavilyService`

- manter temporariamente;
- criar provider adapter novo;
- suportar retorno estruturado;
- assíncrono real;
- usage;
- errors estáveis;
- domain/time filters;
- deprecar singleton bruto após cutover.

## 35.2 `WebSearchTool`

- transformar em Tool Release;
- passar pelo Tool Gateway;
- output de Sources/Claims;
- não retornar string markdown como contrato principal;
- alias temporário para compatibilidade;
- remover attachment direto ao grafo depois do cutover.

## 35.3 Capability

- migrar `platform.web.search` para capabilities granulares;
- preservar alias para releases antigas;
- preencher scopes;
- entitlements/budgets;
- Authority Strict.

## 35.4 Prompts

- remover instruções que tratam web search como fonte única;
- usar Skill Resolver;
- exigir citations;
- marcar web content como untrusted.

## 35.5 Logs

- redigir queries sensíveis;
- não gravar conteúdo completo;
- atribuir Work Run;
- provider usage.

## 35.6 Cutover

```text
Research Orchestrator ativo
→ Skills publicadas
→ Tool Gateway governa providers
→ WebSearchTool vira adapter/alias
→ Graph não anexa tool antiga diretamente
→ claims/citations ativos
→ artifacts e monitors ativos
```

---

# 36. Experiências iniciais de lançamento

## 36.1 Pergunta atual verificada

> “Quais mudanças recentes da SUSEP podem afetar corretoras?”

Entrega:

- fontes oficiais;
- data;
- claims;
- limitações;
- resumo acionável.

## 36.2 Dossiê de seguradora

> “Monte um dossiê atualizado sobre a seguradora X para minha equipe.”

Entrega:

- oficial;
- produtos públicos;
- canais;
- mudanças;
- riscos;
- fontes;
- PDF/web.

## 36.3 Análise de concorrentes

> “Compare dez corretoras da minha região.”

Entrega:

- matriz;
- critérios;
- fontes;
- oportunidades;
- XLSX/PDF.

## 36.4 Descoberta de empresas

> “Encontre cinquenta empresas de logística em Joinville para prospecção empresarial.”

Entrega:

- lista permitida;
- fit;
- website;
- fonte;
- dedupe;
- planilha;
- sem outreach automático.

## 36.5 SEO/AEO

> “Analise meu site e diga o que devo melhorar para aparecer melhor no Google e nas IAs.”

Entrega:

- crawl;
- issues;
- impacto;
- prioridade;
- plano;
- Artifact.

## 36.6 Monitor regulatório

> “Monitore mudanças oficiais relacionadas a seguros residenciais.”

Entrega:

- Rotina;
- fontes oficiais;
- Signal apenas em mudança;
- Briefing/alerta.

## 36.7 Monitor de seguradora

> “Avise quando a seguradora X alterar contatos ou materiais de assistência.”

## 36.8 Verificação de claim

> “É verdade que esta regra passou a valer?”

Entrega:

- claim decomposto;
- veredito;
- fonte;
- vigência;
- incerteza.

---

# 37. Auxiliar global inicial

## 37.1 `Radar de Mercado e Regulação`

Auxiliar global configurável.

Funções:

- monitorar fontes;
- gerar Briefing;
- criar Artifact;
- emitir Signals;
- sugerir ações;
- nunca publicar conhecimento diretamente.

Configuração:

- temas;
- seguradoras;
- região;
- frequência;
- canais;
- orçamento;
- fontes;
- severidade.

Runtime:

```text
Auxiliar
+ Rotinas
+ Skills de pesquisa
+ Capability Pack
+ Work Runs
+ Artifact Hub
+ Intelligence Fabric
```

Não criar Agent dedicado salvo necessidade aprovada.

---

# 38. Evals e testes obrigatórios

## 38.1 Unitários

- URL normalization;
- canonicalization;
- cache key;
- source tier;
- policy;
- query decomposition;
- claim validation;
- citation binding;
- freshness;
- contradiction;
- change significance;
- PII redaction;
- budget;
- provider routing.

## 38.2 Provider contracts

- Tavily;
- Firecrawl;
- Places;
- Direct Fetch;
- timeout;
- 429;
- 5xx;
- partial result;
- usage;
- malformed payload;
- schema drift.

## 38.3 Segurança

- localhost;
- metadata IP;
- private IP;
- redirect;
- DNS rebinding;
- file://;
- javascript:;
- prompt injection HTML;
- prompt injection PDF;
- hidden text;
- exfiltration link;
- oversized content;
- malware;
- secret in log.

## 38.4 Factualidade

Golden cases:

- source official;
- source stale;
- contradiction;
- unsupported claim;
- numeric claim;
- missing date;
- duplicated press release;
- opinion vs fact;
- snippet vs full source;
- no result.

Critérios:

- citation precision;
- citation coverage;
- zero número inventado;
- zero claim crítico sem fonte;
- fact/inference separation.

## 38.5 Deep research

- replan;
- budget stop;
- cancel;
- restart;
- checkpoint;
- provider failure;
- partial Artifact;
- verifier rejection;
- contradictory sources.

## 38.6 Monitor

- no change;
- cosmetic change;
- relevant change;
- source unavailable;
- duplicated tick;
- cooldown;
- Signal;
- quiet hours;
- provider cost.

## 38.7 Business discovery

- Places API;
- field mask;
- dedupe place ID/domain/phone;
- regional query;
- no personal scraping;
- retention;
- attribution;
- 50 results with pagination where allowed;
- budget.

## 38.8 Multi-tenant

- Resulta não vê pesquisa AutoFleet;
- AutoFleet não vê Artifact Resulta;
- snapshot público não expõe query privada;
- monitor não cruza tenant;
- cache público não vaza contexto;
- lead list isolada;
- Knowledge Candidate redigido.

## 38.9 UX

- chat;
- status card;
- cancel;
- sources;
- citations;
- research library;
- monitor;
- mobile;
- erro;
- dados insuficientes;
- custo;
- language human.

## 38.10 Broker Outcome Regression Pack

Validar:

- resposta rápida com fonte;
- deep dossier concluído;
- Artifact abre;
- planilha abre;
- monitor detecta mudança real;
- monitor não alerta ruído;
- recommendation entra no Briefing;
- Knowledge Candidate não publica sozinho;
- Firecrawl funciona com chave da plataforma;
- Tavily continua disponível;
- Google Maps UI não é raspado;
- login, Atendimento, pareamento, Rotinas, Auxiliares, Portais e Briefings continuam funcionando.

---

# 39. Observabilidade e SLOs

## 39.1 Métricas

- requests por modo;
- sucesso;
- tempo;
- provider latency;
- provider errors;
- cache hit;
- pages;
- sources;
- official-source rate;
- claims;
- unsupported claims;
- citation coverage;
- cost;
- monitor noise;
- user feedback;
- artifacts;
- cancellations.

## 39.2 Tracing

Trace inclui:

- request;
- plan version;
- queries redigidas;
- provider calls;
- snapshots;
- claim extraction;
- verification;
- artifact;
- delivery;
- Signal/Knowledge Candidate.

## 39.3 SLOs iniciais

Definir por modo depois do benchmark:

- quick latency;
- verified latency;
- deep completion;
- citation coverage;
- provider availability;
- monitor timeliness;
- zero cross-tenant;
- zero critical unsupported claims.

Não fixar números irreais antes do benchmark.

---

# 40. Plano de execução em três blocos

## Bloco A — Research Foundation, providers e claims

Implementar:

- migrations;
- RLS/FKs/índices;
- Research Request/Plan;
- Source Registry/Policy;
- Source Snapshot;
- Claims/Citations/Findings;
- provider adapters;
- Tavily novo;
- Firecrawl;
- Places;
- Direct Fetch;
- provider router;
- cache;
- security guard;
- redaction;
- usage/metering;
- tests unitários/provider/security.

Gate A:

- schema verde;
- providers homologados;
- Firecrawl com chave da plataforma;
- Tavily preservado;
- Places sem scraping de Maps;
- source snapshots rastreáveis;
- claim/citation funcionando;
- injection/SSRF bloqueados;
- zero cross-tenant;
- custos registrados.

## Bloco B — Skills, artifacts, monitors e produto

Implementar:

- Research Orchestrator;
- planner;
- modes;
- Skills;
- Capability Packs;
- Tool Releases;
- deep research;
- site audit;
- business discovery;
- competitor analysis;
- regulatory research;
- monitors;
- change detector;
- Intelligence integration;
- Knowledge Candidate adapter;
- Artifact templates;
- dashboard tenant;
- Portal Admin mínimo;
- observabilidade.

Gate B:

- quick/verified/deep funcionam;
- dossiê abre;
- planilha abre;
- monitor cria Work Run;
- mudança relevante vira Signal;
- claims citados;
- source policy respeitada;
- CTA usa Work OS;
- budgets funcionam.

## Bloco C — Cutover e lançamento

Implementar:

- experiências iniciais;
- Auxiliar Radar;
- migração TavilyService;
- migração WebSearchTool;
- alias capability;
- remoção do attachment direto legado;
- evals completos;
- canário Amandus;
- canário Resulta;
- canário AutoFleet;
- ajuste de providers/custos;
- ajuste de monitors;
- correção de achados;
- ativação em produção;
- relatório final.

Gate C:

- nenhuma autoridade paralela;
- pesquisa real ativa;
- citations/evidence verdes;
- monitors sem ruído excessivo;
- zero scraping proibido;
- Amandus/Resulta/AutoFleet verdes;
- rollback pronto;
- funcionalidade ativa.

---

# 41. Definition of Done

A SPEC-060 só termina quando:

1. existe Research Orchestrator único.
2. Research Requests e Plans são persistidos.
3. Tavily é adapter homologado.
4. Firecrawl é capacidade global da plataforma.
5. Places/provider oficial é usado para empresas.
6. Google Maps UI não é raspado.
7. Direct Fetch usa Egress Guard.
8. fontes possuem policy e tier.
9. snapshots possuem hashes e datas.
10. claims possuem status e confiança.
11. citations são claim-level.
12. contradição é tratada.
13. quick/verified/deep funcionam.
14. site audit funciona.
15. business discovery funciona.
16. competitor analysis funciona.
17. regulatory watch funciona.
18. monitors usam Rotinas + Work Runs.
19. change detection suprime ruído.
20. Intelligence Signals recebem mudanças relevantes.
21. Knowledge Candidates não são publicados diretamente.
22. artifacts web/PDF/XLSX/CSV funcionam.
23. Research Library funciona.
24. Admin gerencia providers, fontes, monitors, qualidade e custos.
25. prompt injection é bloqueado/isolado.
26. SSRF é bloqueado.
27. budgets e quotas funcionam.
28. provider usage é atribuído.
29. cache não vaza tenant.
30. legado Tavily/WebSearch foi migrado.
31. nenhuma tool antiga permanece soberana.
32. Auxiliar Radar funciona.
33. nenhum número é inventado.
34. nenhum claim crítico fica sem fonte.
35. nenhum tenant vaza.
36. APPLY/VERIFY/ROLLBACK existem.
37. Amandus, Resulta e AutoFleet passaram.
38. relatório final existe.
39. funcionalidade está ativa em produção.

---

# 42. Critérios de parada legítima

O executor só deve parar e pedir decisão do Founder quando encontrar:

- risco real de perda de dados;
- dependência anterior impossível de executar no mesmo programa;
- custo comercial que altere planos/preços do AutoBrokers;
- necessidade de aceitar termos/provider com obrigação relevante;
- definição legal de prospecção sem responsável;
- fonte regulatória ambígua de alto risco;
- design que exija decisão de marca;
- acesso de produção não autorizado;
- provider sem disponibilidade regional mínima.

Não parar por:

- necessidade de migration;
- necessidade de refatorar Tavily;
- necessidade de adicionar Firecrawl;
- necessidade de UI;
- necessidade de testes;
- necessidade de deploy;
- necessidade de calibrar providers;
- necessidade de revisar source policies;
- necessidade de criar artifacts;
- necessidade de remover caminho legado.

---

# 43. Fora do escopo desta SPEC

Ficam para SPECs seguintes:

- Control Plane completo de toda a plataforma — SPEC-061;
- billing comercial final, evals globais e launch readiness consolidado — SPEC-062;
- publicação completa em redes sociais;
- campanhas de outbound autônomas;
- CRM de prospecção completo;
- compra/venda de bases;
- scraping autenticado de portais de seguradoras — permanece no Portal Worker;
- cotações e renovações automatizadas;
- decisões jurídicas autônomas;
- previsão de vendas sem base histórica;
- marketplace público de pesquisas.

A arquitetura deverá aceitar futuras Skills de Growth/Marketing sem criar outro Research Orchestrator.

---

# 44. Referências primárias de implementação

Durante a implementação, consultar documentação oficial atual:

- Firecrawl API v2: Search, Scrape, Crawl, Map, Parse, Agent, Browser, cache, ZDR e Lockdown;
- Tavily: Search, Extract, Crawl, Map, Research, usage, rate limits e integração LangChain oficial;
- Google Places API (New): Text Search, Nearby Search, Place Details, Field Masks, billing, attribution e políticas;
- Google Search Central: robots.txt, sitemaps, indexabilidade e crawling;
- LangGraph: persistence, interrupts e Work Runs;
- Redis Streams: consumer groups e recovery;
- MCP: host authority e least privilege;
- providers oficiais de fontes regulatórias e seguradoras;
- LGPD, termos de uso e políticas vigentes.

As referências inspiram e limitam a implementação. Não autorizam copiar marca, violar termos ou criar runtime paralelo.

---

# 45. Próxima SPEC

A próxima autoridade será:

```text
SPEC-061 — AutoBrokers Portal Admin Control Plane
```

Ela deverá consolidar em uma única experiência administrativa:

- corretoras;
- saúde operacional;
- Work Runs;
- approvals;
- Skills;
- tools;
- MCPs;
- conexões;
- artifacts;
- Auxiliares;
- Rotinas;
- Intelligence Signals;
- Briefings;
- Garimpo/Demand Radar;
- Research providers;
- fontes;
- monitors;
- custos;
- segurança;
- evals;
- releases;
- rollouts e rollback.

Não deverá criar outra autoridade operacional ou acessar tabelas brutas como produto final.