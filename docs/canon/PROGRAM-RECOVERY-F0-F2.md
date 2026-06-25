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

## 6. R1A.1 - Connection Resolution Gate

### Escopo

- Corrigir somente a selecao de `tenant_connections` usada pelo Contract Capture Gate.
- Tratar a Resulta Seguros apenas como tenant piloto de validacao real, sem hard-code de empresa, CPF, apolice, `codfil`, seguradora, produto ou fluxo.
- Selecionar conexao InfoCap globalmente por criterio seguro e reutilizavel para qualquer corretora:
  - pertence a empresa consultada;
  - usa template InfoCap;
  - nao esta arquivada/inativa;
  - possui `encrypted_secret_ref` presente;
  - possui base URL efetiva por `connection_config.base_url` ou configuracao global do provider;
  - possui status compativel com uso operacional/teste seguro.
- Expor somente resumo seguro de resolucao: contagens, status de selecao e necessidade de reconexao/limpeza.

### Proibido

- iniciar R1B;
- alterar parser de CPF/apolice;
- alterar `_DOC_KEYS`, `_sanitize_policy`, `_coverage_sections`;
- alterar Chat Principal, `graph.py`, prompts, Capability Registry, Even, WhatsApp, Docling, Qdrant, MinIO, Drive, Notion ou Portal Browser;
- criar endpoint, pagina, tabela, migration, conector, Vault, RAG ou parser paralelo;
- retornar/logar ID da conexao, `encrypted_secret_ref`, base URL, credencial, token, CPF, nome, apolice, `nosnum`, `codigo`, `codfil` ou payload bruto.

### Criterio de aceite

- Zero conexoes elegiveis retorna `blocked_missing_credentials` com `selection_status = reconnect_required`.
- Uma conexao elegivel e usada internamente para o probe, sem expor ID.
- Mais de uma conexao elegivel retorna `ambiguous_connection` com `selection_status = manual_connection_cleanup_required` e nao chama provider.
- O Founder visualiza somente contagens e status de selecao.
- R1B permanece bloqueada ate captura estrutural real bem-sucedida.

## 7. Fase 0 / R1 - Canonical InfoCap Policy Read Adapter

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

## 7.1 R1B - Canonical InfoCap Policy Read Adapter

### Escopo aplicado

- Corrigir o caminho produtivo existente de `infocap_lookup` e `infocap_policy_detail`.
- Manter o Chat Principal no Smith/LangGraph e na tool `InfocapPolicyLookupTool`.
- Confirmar cliente canonico via `/cliente?codfil&codigo` em buscas por CPF e nome.
- Usar `cpf_cnpj` do detalhe canonico do cliente.
- Resolver apolice por `PolicyLocator(provider=infocap, codfil, nosnum)`.
- Tratar `numapo` como numero exibivel/buscavel que resolve para `nosnum`.
- Retornar `ambiguous_policy` quando houver multiplas apolices sem referencia explicita.
- Preservar envelope estrutural de `/documento` sem payload bruto.
- Normalizar parcelas e campos financeiros com `provider_field`.
- Declarar ausencia honesta de cobertura quando a InfoCap nao retorna listas estruturadas.
- Marcar fonte oficial de documento apenas como flag segura.

### Proibido preservado

- Nenhum runtime, conector, endpoint, HTTP Tool, MCP, RAG, parser, storage, tabela ou migration paralelo.
- Nenhuma alteracao de `graph.py`, prompts, Capability Registry, Docling, Qdrant, MinIO, Drive, Notion, WhatsApp, Portal Browser ou Auxiliares.
- Nenhuma chamada a provider real durante desenvolvimento.

### Feature flag

`INFOCAP_CANONICAL_POLICY_READ` controla rollout/rollback temporario dentro do adapter existente. A flag nao cria segundo conector, segunda rota ou segunda tool.

### Criterio de aceite

- Golden tests R1A/R1B passam.
- `py_compile` passa para conector e tool.
- `policy_ref` nao deriva de `codigo/codcli`.
- `P` nao vira cobertura.
- `official_document_source_available` nao expoe URL.
- Chat Principal passa a receber o DTO canonico pela tool existente.

## 7.2 R1B.1 - Canonical Runtime Hardening and Evidence Safety

### Escopo aplicado

- Consolidar duplicacoes internas do adapter/tool antes do aceite produtivo.
- Centralizar a resolucao de conexao InfoCap no backend Python existente.
- Fazer Chat Principal, detail e Contract Probe consumirem a mesma regra de `tenant_connections` + Vault.
- Remover a logica concorrente TypeScript de selecao de conexao do probe.
- Exigir `policy_locator_ref` preferencial no formato `infocap:<codfil>:<nosnum>` para detalhe.
- Impedir que `ramo`, `produto`, `ramo_abrev`, descricao geral ou tipo de documento gerem cobertura/assistencia.
- Retornar opcoes deterministicas em `ambiguous_policy`, sem o LLM escolher sozinho.

### Proibido preservado

- R1C nao foi iniciada.
- Nenhum documento oficial foi baixado, validado, acessado ou processado.
- Nenhum runtime, conector, endpoint, RAG, parser, storage, Vault, tabela, migration, agente ou ferramenta paralela foi criado.
- A Resulta continua sendo apenas tenant piloto, nunca excecao de codigo.

### Criterio de aceite

- R1B so sera aceita apos teste real no Chat Principal.
- `infocap_lookup`, `infocap_policy_detail`, `infocap_probe` e `InfocapPolicyLookupTool` usam a mesma resolucao canonica de conexao.
- Zero conexoes elegiveis retorna reconexao necessaria; mais de uma retorna limpeza manual necessaria.
- `codigo`, `codcli` e `numapo` nao sao usados diretamente como detalhe de apolice.
- Sinais de classificacao nao sao evidencia de cobertura.
- `coverage_sections` e `assistance_signals` so podem ser positivos com item/cobertura/clausula/assistencia estruturada comprovada.
- R1C permanece bloqueada ate aceite do R1B.1 no Chat Principal.

## 7.3 R1B.2 - Policy Query Contract and Smith Output Guard

### Escopo aplicado

- Permitir consulta pelo numero humano da apolice em `InfocapPolicyLookupTool`.
- Resolver `policy_number` por `/documentos?codfil&texto=<numero>` antes de chamar `/documento`.
- Fazer match exato normalizado por `numapo` ou `nosnum`.
- Detalhar somente apos montar `PolicyLocator(provider=infocap, codfil, nosnum)`.
- Impedir exibicao de numero `0`, vazio, nulo ou placeholder como numero de apolice.
- Manter `policy_locator_ref` como referencia interna/debug, nao requisito operacional do corretor.
- Adicionar Policy Response Contract e output guard dentro do Smith/LangGraph existente.
- Finalizar respostas operacionais de InfoCap com compositor deterministico quando houver contrato de apolice.

### Proibido preservado

- R1C nao foi iniciada.
- Nenhum PDF/documento oficial foi baixado, validado, acessado ou processado.
- Nenhum runtime, endpoint, conector, RAG, parser, storage, tabela, migration, agente ou ferramenta paralela foi criado.
- Nenhuma alteracao em Docling, MinIO, Qdrant, SearchService, KnowledgeBaseTool, Drive, Notion, WhatsApp, Portal Browser, Capability Registry ou Prompt Efetivo.

### Criterio de aceite

- O corretor pode pedir "detalhe a apolice <numero humano>" sem conhecer `codfil`, `nosnum` ou locator tecnico.
- Ambiguidade de apolice retorna ate 10 opcoes com seguradora, produto/ramo, vigencia, status e numero humano quando valido.
- A LLM nao pode apagar opcoes obrigatorias nem converter ausencia estruturada em "erro tecnico".
- Cobertura ausente deve ser explicada como ausencia de itens estruturados da InfoCap, sem inventar cobertura.
- R1C permanece bloqueada ate teste real do R1B.2 no Chat Principal.

## 7.4 R1C.0 - Official Policy Document Source Audit

### Escopo aplicado

- Estender somente o endpoint existente `POST /attendance/connectors/infocap/probe`.
- Adicionar modo master-only `official_document_source_audit`.
- Resolver conexao InfoCap por `tenant_connections + Vault`.
- Resolver apolice pela cadeia canonica ate `/documento`.
- Localizar internamente campos documentais comprovados, priorizando `acompanhamento.emissao.url_apolice`.
- Tentar recuperacao read-only do documento oficial usando a mesma sessao InfoCap.
- Retornar apenas metadados seguros: tipo de conteudo, magic file, bucket de tamanho, redirecionamentos, modo de autenticacao requerido, paginas PDF, camada de texto e ancoras documentais.

### Proibido

- Baixar/processar documento no fluxo normal do Chat Principal.
- Persistir PDF, texto extraido, URL, token, cookie, payload bruto ou PII.
- Enviar documento para Docling, MinIO, Qdrant, Supabase, DocumentService ou servico externo.
- Criar conector, runtime, endpoint, RAG, parser, storage, migration ou ferramenta paralela.
- Expor URL oficial, `codfil`, `nosnum`, numero de apolice, CPF, nome ou conteudo do PDF no output.

### Criterio de aceite

- O Founder consegue rodar o diagnostico no Portal Admin para uma apolice real.
- O retorno informa se a fonte oficial e PDF, HTML/login, erro, redirecionamento, bloqueio, arquivo grande, criptografado ou sem texto.
- O retorno indica `recommended_r1c_transport` sem expor segredo ou URL.
- R1C produtivo permanece bloqueado ate um JSON estrutural seguro real ser revisado.

## 7.4.1 R1C.0.1 - Security Hardening and Admin UX

### Escopo aplicado

- O modo `official_document_source_audit` continua no endpoint existente, sem rota paralela.
- O backend exige marcador master-only para modos globais de diagnostico antes de resolver conexao ou chamar provider.
- A rota Next valida same-origin e `requireMasterAdmin` antes de encaminhar o marcador master ao backend.
- O card existente "Diagnosticar contrato InfoCap" ganhou seletor de modo, sem pagina nova e sem pedir `company_id` manual.
- O fetch da fonte oficial bloqueia SSRF: HTTP, credenciais embutidas, localhost, loopback, redes privadas, link-local, endpoints de metadata e DNS que resolva para IP interno.
- Redirecionamentos sao manuais, limitados a 3 e nunca seguem HTTP.
- Authorization/cookies nao sao encaminhados para origin externo; redirect externo HTTPS e tentado sem credenciais.
- O fetch usa Range e limite de streaming/memoria.

### Proibido

- Iniciar leitura produtiva de documentos no Chat Principal.
- Chamar Docling, MinIO, Qdrant, Supabase, DocumentService ou qualquer servico externo com o conteudo.
- Persistir PDF, texto extraido, URL, token, cookie, header ou payload bruto.
- Criar parser, storage, cache, migration, endpoint, conector, runtime, tool ou agente paralelo.

### Criterio de aceite

- O Founder executa a auditoria pelo Portal Admin sem DevTools/Console.
- O JSON retornado contem somente `source_audit` e metadados seguros.
- Nenhum campo sensivel aparece no output.
- R1C produtivo permanece bloqueado ate a captura real ser revisada.

## 7.5 R1C - Official Policy Document Source and Cached Evidence

### Escopo futuro

- Validar acesso a fonte oficial da apolice quando `official_document_source_available=true`.
- Fazer fetch somente quando a InfoCap estruturada nao trouxer cobertura suficiente ou quando a apolice oficial for explicitamente necessaria.
- Cachear por `company_id + PolicyLocator + hash/ETag/versionamento`.
- Usar `DocumentService` e MinIO existentes antes de qualquer processamento.
- Usar Docling/OCR apenas quando o documento exigir.
- Gerar evidencia por pagina/trecho, sem RAG paralelo.
- Reutilizar evidencia em consultas futuras sem baixar/processar repetidamente o mesmo documento.

### Proibido futuro

- Baixar PDF em toda consulta de apolice.
- Criar parser PDF paralelo.
- Criar storage paralelo.
- Criar RAG paralelo.
- Pedir upload manual quando a fonte oficial da propria apolice estiver disponivel e acessivel.

## 8. Fase 1 / R2 - Smith Runtime and Admin Unification

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

## 9. Fase 2 / R3 - Document Evidence and Knowledge Intake

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

## 10. Congelamentos imediatos

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

## 11. N8N legacy

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

## 12. Ordem de execucao aprovada

```text
R0 - documentacao canonica
R0.5 - Contract Capture Gate seguro da InfoCap
R1 - Canonical InfoCap Policy Read Adapter + Golden tests
R2 - Prompt Efetivo + Capability Registry unico + diagnostico Portal Admin
R3 - Document Evidence por policy_ref usando pipeline existente
Depois - Knowledge OS curado, Auxiliares, WhatsApp, Portais e conectores
```
