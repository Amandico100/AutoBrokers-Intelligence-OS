# SPEC-015A - Canonical InfoCap Policy Read Adapter

> Status: **RASCUNHO CANONICO PARA REVISAO DO CEO**
> Data: 2026-06-24
> Escopo: Fase R1, apos aprovacao documental do R0.
> Regra maior: **nao criar runtime, conector, RAG, Vault, parser, storage ou sistema de agentes paralelo**.

## 1. Problema comprovado

A Auditoria Forense V2 comprovou que o Chat Principal encontra clientes/apolices, mas pode responder com CPF inconsistente, cobertura ausente, cobertura igual a codigo curto como `P` e texto final aparentemente conclusivo sobre uma base tecnica incompleta.

As causas comprovadas no codigo atual sao:

- busca por nome em `backend/app/api/infocap_connector.py` chama `/lista_clientes`, mas nao confirma o cliente canonico em `/cliente?codigo` antes de usar CPF e apolices;
- `_DOC_KEYS` aceita candidatos genericos como `cpf`, `cnpj`, `documento`, `doc`, `cpfcnpj`, `cgccpf` e `ni`, em vez de exigir `cpf_cnpj` do detalhe canonico do cliente;
- `policy_ref` pode ser derivado de `nosnum`, `codigo` ou `codcli`, misturando identificador de apolice com identificador de cliente;
- `numapo` e `nosnum` nao sao tratados com semantica separada em todos os fluxos;
- o retorno de `/documento` e reduzido cedo demais para `docs[0]`, podendo descartar listas irmas do envelope, como `itens`, `coberturas`, `parcelas`, `historico` e `acompanhamento`;
- `_coverage_sections` pode transformar valores curtos de campos como `item` ou `tipo` em nome de cobertura;
- o LLM recebe o resumo da tool e nao ha validador deterministico pos-resposta que impeça inferencia sobre evidencia incompleta.

O ResultVision antigo, usado apenas como referencia historica, seguia uma sequencia mais contratual: nome/CPF -> cliente -> `/cliente?codigo` -> `cpf_cnpj` canonico -> `/cliente_ligacoes` -> `nosnum` -> `/documento`. Ele separava `nosnum` como identificador de detalhe e `numapo` como numero exibivel/buscavel.

## 2. Decisoes canonicas preservadas

1. O Smith/LangGraph e o runtime principal do Chat Principal.
2. `tenant_connections` + Vault sao a unica fonte de conexoes e segredos.
3. Capability Registry sera a unica autoridade de disponibilidade/autorizacao de ferramentas.
4. `tools_config` pode existir somente como configuracao de comportamento visual/local, nunca como autorizacao concorrente.
5. Core interno autorizado pode ler dados completos da propria corretora.
6. Even externa nunca confirma cobertura; recebe apenas evidencia minima vinculada a caso, identidade e apolice.
7. Auxiliares so recebem dados e tools declarados na capability do proprio auxiliar.
8. Nao criar InfoCap paralela, RAG paralelo, parser paralelo, storage paralelo, Vault paralelo ou runtime paralelo.
9. MCP nao e mecanismo de login; OAuth/Vault e o mecanismo de conexao.
10. HTTP Tools nao devem ser usadas como conector paralelo da InfoCap.
11. O Core pode interpretar os dados retornados, mas nao pode inventar cobertura, premio, franquia, clausula, LMI ou assistencia.
12. RAG explica e recupera documentos; nao confirma cobertura sozinho.
13. PDF/documento so e consultado quando a InfoCap nao trouxer detalhe suficiente ou quando houver documento oficial vinculado.
14. Nao baixar ou processar PDF em toda consulta de apolice. InfoCap deve ser consultada como leitura estruturada sob demanda.
15. `/api/n8n` e `lib/n8nClient` sao transport legacy/de compatibilidade, nao runtime principal, nao fonte de verdade e nao caminho da leitura de apolices.

## 3. Principios

- **Contrato antes de heuristica:** campos canonicos da InfoCap devem ter significado fixo.
- **Identidade antes de documento:** nome ou CPF resolvem cliente; cliente resolve `codigo`; `codigo` resolve catalogo; catalogo resolve `nosnum`.
- **Envelope antes de resumo:** o adapter nao pode descartar o envelope de `/documento` antes de extrair e registrar shape, contagens e proveniencia.
- **Evidencia antes de linguagem:** o LLM so interpreta um evidence pack validado.
- **Exposicao por papel:** Core, Even e Auxiliares consomem o mesmo dado canonico, mas recebem DTOs diferentes por RBAC/capability.
- **Rollback sem paralelo:** feature flag temporaria pode controlar o novo adapter, mas nao pode criar segundo conector ou segundo runtime.

## 4. Estruturas existentes que devem ser reutilizadas

- `tenant_connections`
- `connector_templates`
- Vault e `encrypted_secret_ref`
- Capability Registry e `operational.infocap.policy_lookup.read`
- `AgentService`, `LangChainService` e `backend/app/agents/graph.py`
- `backend/app/agents/tools/infocap_tool.py`
- `DocumentService`
- `IngestionService`
- MinIO
- Qdrant
- `SearchService`
- `KnowledgeBaseTool`
- policy evidence/readiness do Atendimento

## 5. Estruturas proibidas

- conector InfoCap paralelo;
- HTTP Tool para InfoCap operacional;
- MCP para login ou consulta InfoCap;
- Vault paralelo;
- storage paralelo de payload;
- RAG paralelo para apolice;
- parser PDF paralelo;
- runtime novo de agente;
- prompt que tente compensar parser ruim.

## 6. Contrato de entrada

O adapter canonico deve aceitar uma requisicao normalizada:

```text
company_id
agent_role: core | attendance | auxiliary | subagent
actor_id
query_type: customer_name | cpf_cnpj | policy_number | policy_ref
customer_name?
cpf_cnpj?
policy_number?
policy_ref?
case_id?
tenant_connection_id?
prefer_insurer?
prefer_product?
trace_context?
```

Regras:

- `company_id` e obrigatorio.
- a conexao real deve ser resolvida por `tenant_connections` + Vault;
- `tenant_connection_id` pode restringir a conexao, mas nao pode trazer segredo;
- uma requisicao deve declarar explicitamente se esta buscando cliente, CPF, numero de apolice ou detalhe por `policy_ref`;
- busca por `policy_number` deve resolver para `nosnum` antes de chamar detalhe;
- Even deve sempre incluir contexto de caso quando receber evidencia de apolice.

## 7. Semantica obrigatoria dos campos InfoCap

| Campo | Semantica canonica | Regra |
| --- | --- | --- |
| `codigo` | codigo canonico do cliente na InfoCap | Pode identificar cliente. Nunca pode virar `policy_ref`. |
| `codfil` | filial/contexto da API | Deve acompanhar chamadas de cliente e documento quando exigido pelo provider. |
| `cpf_cnpj` | documento canonico do cliente | Deve vir do detalhe canonico do cliente, preferencialmente `/cliente?codigo`. |
| `nosnum` | identificador de detalhe/documento da apolice | E a base de `policy_ref`. |
| `numapo` | numero exibivel/buscavel da apolice | Pode buscar ou mostrar, mas deve resolver para `nosnum` antes do detalhe. |
| `policy_ref` | referencia interna da apolice | Deve ser derivada exclusivamente de `nosnum`, com `codfil` como contexto quando necessario. |

Proibido:

- `policy_ref = codigo`;
- `policy_ref = codcli`;
- CPF canonico derivado de campo generico quando o detalhe do cliente esta disponivel;
- tratar `numapo` como se fosse sempre o identificador de detalhe.

## 8. Fluxo canonico obrigatorio

### 8.1 Busca por nome

```text
customer_name
-> /lista_clientes?texto=<nome>
-> resolver ambiguidade
-> obter codigo
-> /cliente?codfil=<codfil>&codigo=<codigo>
-> extrair cpf_cnpj canonico
-> /cliente_ligacoes?codigo=<codigo>
-> obter nosnum/numapo
-> /documento?codfil=<codfil>&nosnum=<nosnum>
-> evidence pack
```

### 8.2 Busca por CPF/CNPJ

```text
cpf_cnpj
-> /cliente_cpf?codfil=<codfil>&cpf_cnpj=<digits>
-> obter/confirmar codigo e cpf_cnpj
-> se necessario, /cliente?codigo para detalhe canonico
-> /cliente_ligacoes?codigo=<codigo>
-> /documento por nosnum
-> evidence pack
```

### 8.3 Busca por numero de apolice

```text
policy_number/numapo
-> /documentos?codfil=<codfil>&texto=<policy_number>
-> match exato por numapo/nosnum normalizados
-> resolver nosnum
-> /documento?codfil=<codfil>&nosnum=<nosnum>
-> evidence pack
```

### 8.4 Detalhe por policy_ref

```text
policy_ref
-> validar que policy_ref deriva de nosnum retornado anteriormente ou de lookup canonico
-> /documento?codfil=<codfil>&nosnum=<policy_ref>
-> preservar envelope restrito
-> evidence pack
```

## 9. Preservacao restrita do envelope

O adapter deve preservar internamente um envelope restrito, nunca em logs:

```text
provider: infocap
logical_endpoint
request_id
company_id_hash
codfil
customer_code
nosnum
policy_ref
endpoint_path
retrieved_at
adapter_version
shape_keys
array_keys_detected
document_count
coverage_item_count
installment_count
history_count
payload_hash
raw_envelope_ref?
parse_status
```

Regras:

- nao logar payload bruto;
- nao logar CPF, nome, token, senha ou segredo;
- se schema for necessario para armazenar envelope restrito, a mudanca deve ser minima e aprovada antes da R1;
- payload bruto, quando indispensavel, deve ter retencao curta, acesso restrito e referencia opaca.

## 10. DTO interno e DTOs externos

### 10.1 DTO interno do adapter

```text
PolicyReadResult
  status
  ambiguity
  customer
    codigo
    codfil
    name
    cpf_cnpj
    source_endpoint
  policy_catalog[]
    policy_ref
    nosnum
    numapo
    insurer
    product
    status
    valid_from
    valid_to
    active_now
    cancelled
  selected_policy?
    policy_ref
    nosnum
    numapo
    detail_source
    coverage_sections[]
    deductibles[]
    premiums[]
    installments[]
    clauses[]
    assistances[]
    limitations[]
  evidence_envelope
  parse_status
  safe_trace
```

### 10.2 DTO para Core

Core autorizado pode receber dados completos da propria corretora, incluindo CPF/CNPJ, nome, numero de apolice, vigencias, premio, franquia, LMI, clausulas e assistencias, desde que venham de fonte rastreada.

O Core nao recebe token, segredo, senha, payload bruto irrestrito nem dados de outro tenant.

### 10.3 DTO para Even

Even recebe somente:

- `case_id`;
- policy evidence minima;
- status de verificacao;
- validade/seguradora/produto quando necessario ao caso;
- cobertura apenas como evidencia, nunca como promessa;
- campos mascarados quando nao forem estritamente necessarios.

### 10.4 DTO para Auxiliares

Auxiliares recebem apenas o subconjunto declarado pela capability do auxiliar. Um auxiliar sem `operational.infocap.policy_lookup.read` nao consulta InfoCap.

## 11. Regras de cobertura

- Cobertura operacional vem de InfoCap estruturada, policy snapshot, documento oficial da apolice, evidencia vinculada, `policy_ref` e validacao humana quando necessaria.
- RAG pode explicar termos e recuperar documento, mas nao confirma cobertura sozinho.
- A ausencia de `itens`, `coberturas`, clausulas, franquias ou premio deve ser retornada como ausencia honesta.
- O texto final deve dizer: "a fonte registra X", nao "o sinistro esta coberto", salvo decisao humana/corredor que autorize o estado operacional.

## 12. Codigos curtos como cobertura

Campos com valores como `P`, `A`, `C`, `S`, `N`, numeros isolados ou abreviacoes sem dicionario comprovado:

- nao podem virar nome de cobertura;
- devem ser preservados em `raw_code`, `type_code` ou campo equivalente;
- so podem ganhar label humano se houver dicionario documentado por provider;
- devem reduzir confianca do parser quando forem o unico sinal de cobertura.

## 13. Ambiguidade

O adapter deve exigir selecao quando:

- busca por nome retornar mais de um cliente plausivel;
- CPF retornar mais de um registro;
- numero de apolice bater em mais de um `nosnum`;
- houver mais de uma apolice ativa sem criterio explicito;
- `policy_ref` nao estiver na lista retornada para o cliente/caso.

Nao selecionar automaticamente por aproximacao fraca.

## 14. Prompt e LLM

A R1 nao altera prompts como solucao principal. O prompt pode continuar instruindo o Core a nao inventar, mas a garantia deve vir do adapter:

- tool retorna evidence pack validado;
- tool informa lacunas;
- tool nao transforma codigo em cobertura;
- tool nao entrega `policy_ref` errado;
- resposta final deve poder ser auditada contra o evidence pack.

## 15. Trace seguro

Campos permitidos:

```text
request_id
company_id_hash
agent_role
logical_endpoint
query_type
codfil
customer_code
nosnum
policy_ref
provider_shape_keys
array_key_selected
document_count
coverage_item_count
coverage_section_count
parse_status
ambiguity_status
selected_by
adapter_version
```

Campos proibidos em log:

```text
CPF/CNPJ
nome do segurado
payload bruto
token
senha
segredo
conteudo integral de apolice
PII real em fixture
```

## 16. Feature flag e rollback

Permitido:

- uma feature flag temporaria para alternar o adapter canonico durante rollout;
- rollback para o caminho antigo congelado se Golden tests ou monitoramento falharem.

Proibido:

- segundo conector InfoCap;
- segundo runtime;
- HTTP Tool/MCP para substituir o adapter;
- schema grande ou armazenamento novo antes de prova de necessidade.

## 17. Golden tests obrigatorios

A matriz completa esta em `GOLDEN-TEST-MATRIX-INFOCAP.md`. A R1 nao passa sem:

- fixtures sinteticas;
- fixtures reais anonimizadas quando disponiveis;
- formato do JSON preservado;
- nenhuma PII real;
- cobertura de nome, CPF, homonimo, `numapo`, `nosnum`, envelope `/documento`, item `P`, ausencia de cobertura, Core/Even/Auxiliar e logs sem PII.

## 18. Criterios de aceite da R1

- Busca por nome sempre confirma cliente canonico via `/cliente?codigo` antes de usar CPF.
- CPF canonico vem de `cpf_cnpj` do detalhe do cliente.
- `policy_ref` deriva exclusivamente de `nosnum`.
- `numapo` e apenas exibivel/buscavel.
- Envelope de `/documento` nao e descartado antes da extracao de `itens`, `coberturas`, `parcelas`, `historico` e `acompanhamento`.
- Codigo curto como `P` nao vira cobertura.
- Ausencia de cobertura e declarada como ausencia.
- Core e Even recebem DTOs diferentes.
- Trace nao contem PII, token, senha ou payload bruto.
- Nenhum endpoint paralelo, runtime paralelo, RAG paralelo ou Vault paralelo foi criado.

## 19. APPLY -> VERIFY -> ROLLBACK

### APPLY

- Implementar adapter canonico dentro da estrutura existente.
- Manter tool Smith existente como entrada operacional.
- Usar feature flag temporaria apenas para rollout/rollback.
- Criar ou ajustar somente testes Golden aprovados.

### VERIFY

- Rodar matriz Golden completa.
- Verificar logs sem PII.
- Verificar que `/api/n8n` nao entrou no caminho de leitura de apolice.
- Verificar que Capability Registry continua sendo autoridade.
- Verificar que Core, Even e Auxiliares recebem exposicoes diferentes.

### ROLLBACK

- Desativar feature flag do adapter canonico.
- Manter rota antiga congelada.
- Nao criar fallback externo.
- Registrar falha por fixture/trace seguro.
- Corrigir e repetir Golden tests antes de novo rollout.

## 20. Fora de escopo da SPEC-015A

- Prompt Efetivo no Portal Admin.
- Migracao completa de `tools_config`.
- Document Evidence por `policy_ref`.
- Ingestao automatica Docling -> Qdrant.
- Drive/Notion produtivos no Core.
- WhatsApp real.
- novos Auxiliares.
- Portal Browser operacional.
