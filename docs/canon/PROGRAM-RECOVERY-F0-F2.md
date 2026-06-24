# PROGRAM-RECOVERY-F0-F2 - Recuperacao Arquitetural AutoBrokers Intelligence OS

> Status: **R0 DOCUMENTAL**
> Data: 2026-06-24
> Objetivo: formalizar a recuperacao segura sem iniciar implementacao.
> Regra: **nao criar sistemas paralelos**.

## 1. Contexto

O AutoBrokers Intelligence OS deve operar como um SaaS multi-tenant para corretoras de seguros sobre o Smith/LangGraph, reutilizando a infraestrutura existente de agentes, tools, Vault, conectores, memoria, RAG, documentos, MinIO, Qdrant, Docling e Capability Registry.

A Auditoria Forense V2 encerrou a investigacao ampla. A causa principal da leitura ruim de apolices esta no adapter atual de InfoCap, nao na capacidade geral do modelo:

- cliente por nome nao e confirmado por `/cliente?codigo`;
- CPF e extraido por candidatos genericos;
- `codigo`, `codcli`, `nosnum` e `numapo` sao misturados;
- o envelope de `/documento` e reduzido cedo demais;
- codigo curto como `P` pode virar cobertura;
- o LLM recebe evidencia incompleta.

## 2. Decisoes canonicas obrigatorias

1. O Smith/LangGraph e o runtime principal do Chat Principal.
2. `tenant_connections` + Vault sao a unica fonte de conexoes e segredos.
3. Capability Registry sera a unica autoridade de disponibilidade/autorizacao de ferramentas.
4. `tools_config` podera existir somente como configuracao de comportamento visual/local, nunca como autorizacao concorrente.
5. Core interno autorizado pode ler dados completos da propria corretora somente apos sessao autenticada, usuario vinculado a empresa, papel permitido, `company_id` resolvido server-side, capability ativa e conexao InfoCap saudavel da propria empresa.
6. Even externa nunca confirma cobertura; recebe apenas evidencia minima vinculada a caso, identidade e apolice.
7. Auxiliares so recebem dados e tools declarados na capability do proprio auxiliar.
8. Nao criar InfoCap paralela, RAG paralelo, parser paralelo, storage paralelo, Vault paralelo ou runtime paralelo.
9. MCP nao e mecanismo de login; OAuth/Vault e o mecanismo de conexao.
10. HTTP Tools nao devem ser usadas como conector paralelo da InfoCap.
11. O Core pode interpretar os dados retornados, mas nao pode inventar cobertura, premio, franquia, clausula, LMI ou assistencia.
12. RAG explica e recupera documentos; nao confirma cobertura sozinho.
13. PDF/documento so e consultado quando a InfoCap nao trouxer detalhe suficiente ou quando houver documento oficial vinculado.
14. Nao baixar ou processar PDF em toda consulta de apolice.
15. `/api/n8n` e `lib/n8nClient` sao transport legacy/de compatibilidade: congelados para novas funcionalidades, nao removidos nesta fase.

## 3. Mapa alvo

```text
tenant_connections + Vault
        |
        v
Canonical InfoCap Policy Read Adapter
        |
        v
Customer Resolution
nome/CPF -> codigo -> /cliente
        |
        v
Policy Catalog
/cliente_ligacoes -> nosnum / numapo
        |
        v
Policy Detail
/documento -> DTO explicito + Evidence Envelope
        |
        +--> AutoBrokers Core
        +--> Even
        +--> Auxiliares
```

Documentos:

```text
DocumentService + MinIO
        |
        v
Docling/OCR/extracao
        |
        v
IngestionService
        |
        v
Qdrant + SearchService
        |
        v
KnowledgeBaseTool
```

## 4. R0 - Formalizacao documental

### Escopo

- Criar a SPEC-015A.
- Criar este programa F0-F2.
- Criar matriz Golden de InfoCap.
- Criar mapa de autoridade de tools do Smith.
- Criar relatorio forense V2.

### Proibido

- codigo operacional;
- schema/migration;
- provider externo;
- alteracao de credencial;
- alteracao de prompt;
- ativacao de tools;
- alteracao em Docling, Qdrant, MinIO, Vault ou InfoCap.

### Criterio de aceite

- Somente Markdown canonico criado.
- Nenhum runtime alterado.
- Nenhum schema alterado.
- Nenhum provider chamado.
- Um commit documental unico autorizado.

## 5. R0.5 - Contract Capture Gate

### Escopo

- Estender o probe existente da InfoCap com o modo `policy_chain_contract`.
- Reutilizar `tenant_connections`, Vault, conexao InfoCap existente e o endpoint `POST /attendance/connectors/infocap/probe`.
- Executar somente diagnostico seguro de shape da cadeia:
  - `/cliente_cpf` ou `/lista_clientes`;
  - `/cliente`;
  - `/cliente_ligacoes`;
  - `/documento`.
- Retornar somente chaves, tipos, listas, contagens, `shape_hash`, status e campos canonicos detectados.
- Preparar harness de Golden tests com fixtures sinteticas.

### Proibido

- mudar comportamento produtivo do Chat Principal;
- alterar `graph.py`;
- alterar prompts;
- alterar Capability Registry;
- chamar provider real durante desenvolvimento local;
- criar migration;
- criar endpoint paralelo;
- criar servico ou pagina nova;
- retornar/logar CPF, nome, apolice, `nosnum`, `codigo`, `codfil`, token, senha, valor de premio/cobertura ou payload bruto.

### Dependencias

- R0 documental.
- Master admin autenticado para executar o diagnostico no Portal Admin.
- Conexao InfoCap existente da corretora.

### Criterio de aceite

- R1B continua bloqueada ate captura real de shape.
- O Founder recebe somente resultado estrutural.
- Nenhum dado operacional muda.
- Nenhuma estrutura paralela e criada.

## 6. Fase 0 / R1 - Canonical InfoCap Policy Read Adapter

### Escopo

- Corrigir o adapter canonico de leitura InfoCap.
- Garantir fluxo nome/CPF -> cliente -> `/cliente?codigo` -> CPF canonico.
- Separar `codigo`, `codfil`, `cpf_cnpj`, `nosnum`, `numapo`, `policy_ref` e `PolicyLocator`.
- Usar `PolicyLocator(provider=infocap, codfil, nosnum)` em toda leitura de detalhe.
- Preservar envelope restrito, hash, shape, proveniencia e contagens.
- Construir DTO interno para Core, DTO minimo para Even e DTO limitado para Auxiliares.
- Implementar trace seguro.
- Rodar Golden tests.
- Usar feature flag temporaria somente para rollback.

### Proibido

- mudar UI;
- criar endpoints paralelos;
- criar conector paralelo;
- criar HTTP Tool/MCP para InfoCap;
- mexer em RAG;
- mexer em Drive/Notion;
- mexer em Even alem de consumir o contrato quando autorizado;
- alterar prompts para mascarar problema de parser.

### Dependencias

- SPEC-015A aprovada pelo CEO.
- R0.5 executado em apolice de teste e resultado estrutural revisado.
- Matriz Golden aprovada.
- Fixtures sinteticas e, quando disponiveis, reais anonimizadas.
- Acesso apenas a estruturas existentes de Vault/tenant connection.

### Criterios de aceite

- Todos os Golden tests de InfoCap passam.
- Logs sem PII.
- `policy_ref` nunca deriva de `codigo`/`codcli`.
- detalhe sempre usa `codfil + nosnum`.
- `P` nao vira cobertura.
- Ausencia de cobertura e reportada honestamente.
- Core/Even/Auxiliar recebem exposicoes diferentes.

### Golden necessario

Ver `GOLDEN-TEST-MATRIX-INFOCAP.md`.

### Risco de duplicacao a evitar

Criar "InfoCap v2" como outro servico. O correto e corrigir o adapter dentro do caminho existente.

## 7. Fase 1 / R2 - Smith Runtime and Admin Unification

### Escopo

- Unificar autoridade de tools no Capability Registry.
- Transformar `tools_config` em configuracao visual/comportamental, nao autorizacao.
- Mapear HTTP Tools e MCP como execucao governada por capability.
- Documentar e exibir Prompt Efetivo no Portal Admin.
- Exibir diagnostico de capabilities, tools vinculadas, RAG/memoria e contexto.
- Congelar `/api/n8n` como transport legacy.

### Proibido

- criar runtime novo;
- transformar politica imutavel em campo editavel de tenant;
- liberar tool por URL/token colado no editor;
- usar MCP como login;
- usar HTTP Tool como conector InfoCap;
- remover `/api/n8n` sem auditoria dedicada.

### Dependencias

- R1 estabilizada.
- Mapa de autoridade aprovado.
- Decisao de UX do Portal Admin para Prompt Efetivo.
- Capability Registry considerado autoridade unica.

### Criterios de aceite

- Portal Admin mostra politica da plataforma, blueprint global, personalizacao local e Prompt Efetivo.
- Prompt Efetivo e somente leitura e redigido.
- Toda tool produtiva tem capability correspondente ou status explicito de legado/congelado.
- Dashboard nao promete ferramenta ligada se runtime nao le.

### Golden necessario

- Core com web ligada/desligada por capability.
- InfoCap ligada/desligada por capability e conexao.
- HTTP Tool sem capability nao entra como autoridade.
- MCP sem capability nao vira login.
- Prompt Efetivo mostra tools realmente vinculadas.

### Risco de duplicacao a evitar

Criar "admin novo" ou "editor novo" para contornar o Smith. O correto e diagnosticar e governar o Smith existente.

## 8. Fase 2 / R3 - Document Evidence and Knowledge Intake

### Escopo

- Ligar apolice/documento oficial a `policy_ref`.
- Usar DocumentService, MinIO, Docling/OCR quando necessario, IngestionService, Qdrant e SearchService existentes.
- Permitir que Core e Even consultem evidencia documental sem criar novo RAG.
- Automatizar caminho Docling -> ingestao quando confianca e tipo permitirem.
- Exigir revisao humana para baixa confianca, conflito InfoCap x documento ou uso sensivel.

### Proibido

- RAG paralelo da Even;
- storage paralelo de apolice;
- parser PDF paralelo;
- baixar/processar PDF em toda consulta;
- confirmar cobertura apenas por RAG;
- usar Drive/Notion como fonte produtiva sem capability/evidence contract.

### Dependencias

- R1 canonico de InfoCap.
- R2 autoridade de tools e Prompt Efetivo.
- Politica de retencao documental aprovada.
- Metadados de `policy_ref` no payload documental, se schema permitir ou for aprovado.

### Criterios de aceite

- Documento oficial pode ser vinculado a `policy_ref`.
- SearchService recupera evidencia filtravel por tenant/agente/caso/policy_ref quando aplicavel.
- Even recebe apenas minimo necessario.
- Core pode citar fonte/documento/pagina quando houver.
- Conflito InfoCap x documento exige validacao humana.

### Golden necessario

- Apolice com documento oficial indexado.
- Apolice sem cobertura estruturada na InfoCap, mas com documento vinculado.
- Conflito entre InfoCap e documento.
- Documento com baixa confianca OCR.
- Isolamento entre tenants.

### Risco de duplicacao a evitar

Criar "Policy RAG" separado. O correto e completar o pipeline documental existente.

## 9. Congelamentos imediatos

Enquanto R1 nao for aprovado:

- nao ligar manualmente Visao Computacional no Portal Admin para tentar resolver apolice;
- nao criar HTTP Tools para InfoCap;
- nao criar MCP para InfoCap;
- nao criar agente novo para ler apolice;
- nao alterar system prompt para forcar adivinhacao;
- nao abrir RAG curado;
- nao criar Auxiliares novos;
- nao adicionar Gmail, Outlook, Meta, Instagram ou novos conectores;
- nao alterar Docling, Qdrant, MinIO, Drive/Notion ou EasyPanel.

## 10. N8N legacy

Classificacao canonica:

```text
/api/n8n + lib/n8nClient
= transport legacy / compatibilidade
!= runtime principal do Smith
!= caminho do Chat textual atual
!= fonte de verdade
!= caminho da leitura de apolices
```

Regras:

- nenhuma funcionalidade nova deve passar por `/api/n8n`;
- nao remover agora;
- auditar chamadas antes de migracao/remocao;
- voz pode permanecer dependente ate frente propria.

## 11. Ordem de execucao aprovada

```text
R0 - documentacao canonica
R0.5 - Contract Capture Gate seguro da InfoCap
R1 - Canonical InfoCap Policy Read Adapter + Golden tests
R2 - Prompt Efetivo + Capability Registry unico + diagnostico Portal Admin
R3 - Document Evidence por policy_ref usando pipeline existente
Depois - Knowledge OS curado, Auxiliares, WhatsApp, Portais e conectores
```
