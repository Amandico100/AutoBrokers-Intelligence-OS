# SPEC-015A - Canonical InfoCap Policy Read Adapter

> Status: **CANONICO EM RECUPERACAO - R1C.1**
> Data: 2026-06-25
> Escopo: Fase R1 ate pipeline documental oficial cacheado.
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
5. Core interno autorizado pode ler dados completos da propria corretora somente apos validar sessao autenticada, vinculo do usuario a empresa, papel permitido, `company_id` resolvido server-side, capability ativa e conexao InfoCap saudavel da propria empresa.
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

## 6. R0.5 - Contract Capture Gate

Antes da R1B, e obrigatorio executar a captura contratual segura da InfoCap. Essa etapa descobre o shape real dos endpoints sem alterar o comportamento produtivo do Chat Principal:

```text
/cliente_cpf ou /lista_clientes
-> /cliente
-> /cliente_ligacoes
-> /documento
```

O gate deve retornar somente metadados estruturais: endpoint logico, HTTP status, tipo bruto, chaves, caminhos de chaves ate profundidade segura, tipos, listas, contagens, `shape_hash`, `parse_status` e campos canonicos detectaveis. Ele nao pode retornar CPF/CNPJ, nome, email, telefone, endereco, numero de apolice, `nosnum`, `codigo`, `codfil`, valores de premio/cobertura, token, senha, payload bruto ou preview de payload.

R1B permanece bloqueada ate o Founder rodar o diagnostico seguro em uma apolice de teste e trazer de volta somente chaves, tipos, hashes e contagens.

### 6.1 R1A.1 - Connection Resolution Gate

Antes de chamar a cadeia contratual, o diagnostico deve resolver a conexao InfoCap correta por `tenant_connections` + Vault, de forma global para qualquer corretora. A Resulta Seguros e apenas tenant piloto de validacao real; nao pode haver hard-code de empresa, CPF, apolice, `codfil`, seguradora, produto ou fluxo.

Uma conexao e elegivel para o Contract Capture Gate somente quando:

- pertence a empresa consultada;
- usa o template InfoCap;
- nao esta arquivada/inativa;
- possui `encrypted_secret_ref` presente;
- possui base URL efetiva por `connection_config.base_url` ou configuracao global do provider;
- possui status compativel com uso operacional/teste seguro.

Resultados de selecao:

```text
0 conexoes elegiveis -> blocked_missing_credentials + selection_status=reconnect_required
1 conexao elegivel   -> usar internamente no probe, sem expor ID
2+ elegiveis         -> ambiguous_connection + selection_status=manual_connection_cleanup_required
```

O diagnostico pode exibir somente contagens agregadas: total de conexoes InfoCap, inativas/arquivadas, status operacional, Vault presente, base URL configurada, elegiveis e estrategia de selecao. E proibido retornar ID da conexao, `encrypted_secret_ref`, base URL, credenciais, token, CPF, nome, numero de apolice, `nosnum`, `codigo`, `codfil` ou payload bruto.

### 6.2 R1B.1 - endurecimento canonico antes do aceite

O R1B nao pode ser aceito como producao final enquanto houver duplicacao de implementacao, resolucao concorrente de conexao ou sinal falso de cobertura.

Regras obrigatorias:

- deve existir uma unica definicao canonica de `_build_evidence_pack`, `_coverage_sections`, `_summarize` e `_summarize_detail`;
- a resolucao de conexao InfoCap deve morar no backend Python existente e ser reutilizada por `infocap_lookup`, `infocap_policy_detail`, `infocap_probe` e `InfocapPolicyLookupTool`;
- a rota Next do diagnostico pode autenticar e encaminhar a requisicao, mas nao pode manter algoritmo proprio de selecao de `tenant_connections`;
- `tenant_connection_id` pode restringir a escolha, mas a conexao continua precisando passar por empresa, template InfoCap, status operacional, nao arquivada/inativa, Vault presente, base URL efetiva e saude operacional;
- zero conexoes elegiveis retorna `blocked_missing_credentials`; mais de uma retorna `ambiguous_connection`;
- detalhe de apolice deve usar preferencialmente `policy_locator_ref = infocap:<codfil>:<nosnum>`;
- `nosnum` ou `numapo` simples nunca autorizam chamada direta a `/documento` com `codfil` padrao; precisam ter sido resolvidos no catalogo ou vir em um locator completo;
- `ramo`, `produto`, `ramo_abrev`, descricao geral e tipo de documento sao classificacao da apolice, nao evidencia de cobertura;
- `assistance_signals` so podem ser positivos quando vierem de item, cobertura, clausula ou assistencia estruturada com label humano comprovado;
- `tabela_itens` permanece desconhecido/classificavel ate existir contrato semantico validado;
- `ambiguous_policy` deve devolver opcoes deterministicas para o Core pedir escolha, sem selecao silenciosa pelo LLM.

### 6.3 R1B.2 - contrato de consulta e output guard do Smith

O corretor nao deve precisar conhecer `policy_locator_ref`, `nosnum` ou `codfil` para usar o Chat Principal. A tool deve aceitar numero humano da apolice e resolver o locator internamente.

Regras obrigatorias:

- `InfocapPolicyLookupTool` aceita `document`, `name`, `policy_number` e `policy_ref`;
- `policy_number` executa `/documentos?codfil&texto=<numero>` e filtra match exato normalizado por `numapo` ou `nosnum`;
- zero matches retorna `not_found`;
- multiplos matches retornam `ambiguous_policy` com opcoes deterministicas;
- um match monta `PolicyLocator(provider=infocap, codfil, nosnum)` e so entao chama `/documento`;
- numero humano nunca pode ser enviado diretamente como `nosnum` para `/documento`;
- numero `0`, vazio, nulo ou placeholder deve ser exibido como "numero nao retornado pela InfoCap";
- `policy_locator_ref` pode existir no DTO interno/debug, mas a resposta operacional deve orientar escolha pelo numero humano, seguradora, ramo e vigencia;
- resultados InfoCap devem produzir um Policy Response Contract dentro do Smith/LangGraph existente;
- o output guard deve impedir que a LLM apague opcoes, transforme `source_limited` em erro tecnico ou invente cobertura;
- se `structured_coverage_absent=true`, a resposta deve declarar ausencia estruturada da InfoCap;
- se `document_evidence_required=true`, a resposta pode mencionar a futura fonte documental oficial, mas nao pode afirmar que PDF foi lido.

### 6.4 R1C.0 - auditoria viva da fonte oficial da apolice

Quando `/documento` nao trouxer `itens`, `coberturas`, `franquias`, `clausulas` ou `assistencias`, mas trouxer `acompanhamento.emissao.url_apolice`, o sistema deve tratar a URL como ponte para evidencia documental futura, nao como cobertura confirmada.

O modo `official_document_source_audit` do endpoint existente `POST /attendance/connectors/infocap/probe` deve:

- ser master-only;
- reutilizar `tenant_connections + Vault`, login InfoCap e resolucao canonica de apolice;
- chamar `/documento` apenas por `PolicyLocator(provider=infocap, codfil, nosnum)`;
- localizar internamente `acompanhamento.emissao.url_apolice` e `acompanhamento.proposta.url_proposta`, sem heuristica generica de URL;
- priorizar `url_apolice`;
- tentar recuperacao read-only com Authorization, cookies de sessao e redirecionamentos HTTPS limitados;
- retornar somente metadados seguros de recuperacao e classificacao documental;
- nunca persistir PDF, texto, URL, payload bruto, token, cookie ou PII.

O retorno seguro deve conter, no maximo, campos como `retrieval_status`, `auth_mode_required`, `final_origin_class`, `content_type`, `content_length_bucket`, `file_magic`, `pdf_encrypted`, `pdf_page_count`, `text_layer_status`, `document_anchor_detection`, `source_fetch_safe_for_r1c`, `source_fetch_blocker` e `recommended_r1c_transport`.

### 6.5 R1C.0.1 - hardening de seguranca e UX do diagnostico

Antes de qualquer deploy do R1C.0, o modo `official_document_source_audit` deve cumprir:

- autorizacao master-only tambem no backend Python, antes de resolver `tenant_connections` ou chamar provider;
- rota Next com `assertSameOrigin` e `requireMasterAdmin`;
- UI no card existente "Diagnosticar contrato InfoCap", sem pagina nova e sem input manual de `company_id`;
- aceite somente de URL HTTPS sem usuario/senha embutidos;
- bloqueio de localhost, loopback, `0.0.0.0`, `::1`, redes privadas, link-local, endpoints de metadata e DNS que resolva para IP interno;
- redirecionamento manual, maximo 3, nunca para HTTP;
- Authorization e cookies somente para o origin original validado;
- redirect externo HTTPS sem Authorization/cookie;
- Range request e limite de tamanho por header e streaming;
- arquivo temporario apagado em `finally`, quando usado;
- proibicao de enviar conteudo para Docling, MinIO, Supabase, Qdrant ou DocumentService nesta etapa.

R1C.0.1 foi validado em producao controlada: duas apolices retornaram PDF oficial recuperavel por `signed_url_fetch`, com camada de texto presente, e uma apolice nao retornou fonte documental automatica. R1C.1 fica autorizado para leitura documental cacheada.

### 6.6 R1C.1 - pipeline de evidencia documental oficial

Quando a InfoCap estruturada nao trouxer cobertura/franquia/assistencia/clausula/LMI e houver fonte oficial disponivel, o adapter canonico pode acionar o pipeline documental oficial sob demanda.

Regras obrigatorias:

- fetch apenas quando a pergunta exigir evidencia documental sensivel ou quando `document_evidence_requested=true`;
- nunca baixar todas as apolices de um segurado;
- nunca baixar PDF em toda consulta;
- `signed_url_fetch` sem credenciais deve ser tentado antes de modos autenticados;
- Authorization/cookie so podem ir ao origin InfoCap validado; redirect/cross-origin deve remover credenciais;
- a signed URL nunca e persistida, logada ou enviada ao LLM/frontend;
- o PDF oficial e armazenado de forma privada pelo `DocumentService`/MinIO existentes;
- a extracao direta por pagina vem antes do Docling;
- Docling/OCR e fallback da mesma pipeline, nunca parser paralelo;
- a ingestao usa `IngestionService`, Qdrant e `SearchService` existentes;
- documentos `official_policy_document` nao entram em busca ampla de conhecimento sem filtro por apolice;
- evidencia enviada ao Core deve ser curta, por pagina/trecho, com `document_id`, `policy_locator_hash`, `content_hash`, `evidence_type`, `confidence` e `source_document=official_policy_document`;
- `codfil`, `nosnum`, URL, token, cookie, Authorization, payload bruto e texto integral do PDF nao podem aparecer em logs, chat ou resposta.

Estados documentais:

```text
source_available
fetching
fetched
direct_extracting
docling_pending
parsed
evidence_ready
source_unavailable
source_fetch_failed
document_not_policy_evidence
low_confidence
conflict_requires_human
```

Cache canonico:

```text
company_id + provider=infocap + policy_locator_hash + content_hash
```

Se o cache estiver valido, a mesma apolice nao deve ser baixada novamente. Se a fonte nao existir, a resposta deve dizer que a InfoCap confirmou a apolice, mas nao disponibilizou fonte documental oficial automatica.

## 7. Contrato de entrada

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

## 8. Semantica obrigatoria dos campos InfoCap

| Campo | Semantica canonica | Regra |
| --- | --- | --- |
| `codigo` | codigo canonico do cliente na InfoCap | Pode identificar cliente. Nunca pode virar `policy_ref`. |
| `codfil` | filial/contexto da API | Deve acompanhar chamadas de cliente e documento quando exigido pelo provider. |
| `cpf_cnpj` | documento canonico do cliente | Deve vir do detalhe canonico do cliente via `/cliente?codigo`, salvo prova contratual documentada e Golden especifico de equivalencia. |
| `nosnum` | identificador de detalhe/documento da apolice | E parte obrigatoria do `PolicyLocator`. |
| `numapo` | numero exibivel/buscavel da apolice | Pode buscar ou mostrar, mas deve resolver para `nosnum` antes do detalhe. |
| `policy_ref` | referencia externa/operacional exibivel | Pode continuar simples, mas internamente sempre resolve para `PolicyLocator`. |

### 8.1 PolicyLocator interno

```text
PolicyLocator:
  provider = infocap
  codfil
  nosnum
```

Regras:

- `policy_ref` nunca nasce de `codigo` ou `codcli`;
- `numapo` e somente numero exibivel/buscavel e deve resolver para `nosnum`;
- detalhe sempre usa `codfil + nosnum`;
- `policy_ref` exibido ao operador pode continuar simples, mas a operacao interna deve carregar o locator completo para evitar colisao ou consulta na filial errada.

Proibido:

- `policy_ref = codigo`;
- `policy_ref = codcli`;
- CPF canonico derivado de campo generico quando o detalhe do cliente esta disponivel;
- tratar `numapo` como se fosse sempre o identificador de detalhe.

## 9. Status canonicos

O adapter deve usar somente estes status estaveis na fronteira canônica:

```text
found
ambiguous_customer
ambiguous_policy
source_limited
provider_auth_error
provider_timeout
unknown_shape
document_evidence_required
conflict_requires_human
```

## 10. Fluxo canonico obrigatorio

### 10.1 Busca por nome

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

### 10.2 Busca por CPF/CNPJ

```text
cpf_cnpj
-> /cliente_cpf?codfil=<codfil>&cpf_cnpj=<digits>
-> obter codigo/codfil candidato
-> /cliente?codfil=<codfil>&codigo=<codigo>
-> extrair cpf_cnpj canonico
-> /cliente_ligacoes?codigo=<codigo>
-> /documento por PolicyLocator(codfil, nosnum)
-> evidence pack
```

Excecao: se houver prova contratual documentada de que `/cliente_cpf` retorna exatamente o mesmo detalhe canonico de `/cliente`, essa equivalencia deve ser coberta por Golden antes de qualquer otimizacao. Sem esse Golden, `/cliente?codigo` e obrigatorio.

### 10.3 Busca por numero de apolice

```text
policy_number/numapo
-> /documentos?codfil=<codfil>&texto=<policy_number>
-> match exato por numapo/nosnum normalizados
-> resolver nosnum
-> /documento?codfil=<codfil>&nosnum=<nosnum>
-> evidence pack
```

### 10.4 Detalhe por policy_ref

```text
policy_ref
-> resolver para PolicyLocator(provider=infocap, codfil, nosnum)
-> /documento?codfil=<codfil>&nosnum=<nosnum>
-> preservar envelope restrito
-> evidence pack
```

## 11. Preservacao restrita do envelope

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

## 12. DTO interno e DTOs externos

### 12.1 DTO interno do adapter

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
    policy_locator
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

### 12.2 DTO para Core

Core autorizado pode receber dados completos da propria corretora, incluindo CPF/CNPJ, nome, numero de apolice, vigencias, premio, franquia, LMI, clausulas e assistencias, desde que venham de fonte rastreada.

Obrigatorio antes de expor dados completos ao Core:

- sessao autenticada;
- usuario vinculado a empresa;
- papel permitido;
- `company_id` resolvido server-side;
- capability ativa;
- conexao InfoCap saudavel da propria empresa.

O Core nao recebe token, segredo, senha, payload bruto irrestrito nem dados de outro tenant.

### 12.3 DTO para Even

Even recebe somente:

- `case_id`;
- policy evidence minima;
- status de verificacao;
- validade/seguradora/produto quando necessario ao caso;
- cobertura apenas como evidencia, nunca como promessa;
- campos mascarados quando nao forem estritamente necessarios.

### 12.4 DTO para Auxiliares

Auxiliares recebem apenas o subconjunto declarado pela capability do auxiliar. Um auxiliar sem `operational.infocap.policy_lookup.read` nao consulta InfoCap.

## 13. Regras de cobertura

- Cobertura operacional vem de InfoCap estruturada, policy snapshot, documento oficial da apolice, evidencia vinculada, `policy_ref` e validacao humana quando necessaria.
- RAG pode explicar termos e recuperar documento, mas nao confirma cobertura sozinho.
- A ausencia de `itens`, `coberturas`, clausulas, franquias ou premio deve ser retornada como ausencia honesta.
- O texto final deve dizer: "a fonte registra X", nao "o sinistro esta coberto", salvo decisao humana/corredor que autorize o estado operacional.

## 14. Codigos curtos como cobertura

Campos com valores como `P`, `A`, `C`, `S`, `N`, numeros isolados ou abreviacoes sem dicionario comprovado:

- nao podem virar nome de cobertura;
- devem ser preservados em `raw_code`, `type_code` ou campo equivalente;
- so podem ganhar label humano se houver dicionario documentado por provider;
- devem reduzir confianca do parser quando forem o unico sinal de cobertura.

## 15. Ambiguidade

O adapter deve exigir selecao quando:

- busca por nome retornar mais de um cliente plausivel;
- CPF retornar mais de um registro;
- numero de apolice bater em mais de um `nosnum`;
- houver mais de uma apolice ativa sem criterio explicito;
- `policy_ref` nao estiver na lista retornada para o cliente/caso.

Nao selecionar automaticamente por aproximacao fraca.

## 16. Prompt e LLM

A R1 nao altera prompts como solucao principal. O prompt pode continuar instruindo o Core a nao inventar, mas a garantia deve vir do adapter:

- tool retorna evidence pack validado;
- tool informa lacunas;
- tool nao transforma codigo em cobertura;
- tool nao entrega `policy_ref` errado;
- resposta final deve poder ser auditada contra o evidence pack.

## 17. Trace seguro

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

## 18. Feature flag e rollback

Permitido:

- uma feature flag temporaria para alternar o adapter canonico durante rollout;
- rollback para o caminho antigo congelado se Golden tests ou monitoramento falharem.

Proibido:

- segundo conector InfoCap;
- segundo runtime;
- HTTP Tool/MCP para substituir o adapter;
- schema grande ou armazenamento novo antes de prova de necessidade.

## 19. Golden tests obrigatorios

A matriz completa esta em `GOLDEN-TEST-MATRIX-INFOCAP.md`. A R1 nao passa sem:

- fixtures sinteticas;
- fixtures reais anonimizadas quando disponiveis;
- formato do JSON preservado;
- nenhuma PII real;
- cobertura de nome, CPF, homonimo, `numapo`, `nosnum`, envelope `/documento`, item `P`, ausencia de cobertura, Core/Even/Auxiliar e logs sem PII.

## 20. Criterios de aceite da R1

- Busca por nome sempre confirma cliente canonico via `/cliente?codigo` antes de usar CPF.
- Busca por CPF tambem chama `/cliente?codigo`, salvo equivalencia provada por Golden.
- CPF canonico vem de `cpf_cnpj` do detalhe do cliente.
- Toda leitura de detalhe usa `PolicyLocator(provider=infocap, codfil, nosnum)`.
- `numapo` e apenas exibivel/buscavel.
- Envelope de `/documento` nao e descartado antes da extracao de `itens`, `coberturas`, `parcelas`, `historico` e `acompanhamento`.
- Codigo curto como `P` nao vira cobertura.
- Ausencia de cobertura e declarada como ausencia.
- Core e Even recebem DTOs diferentes.
- Trace nao contem PII, token, senha ou payload bruto.
- Nenhum endpoint paralelo, runtime paralelo, RAG paralelo ou Vault paralelo foi criado.

## 21. APPLY -> VERIFY -> ROLLBACK

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

## 22. R1B - Implementacao canonica aplicada

R1B implementa o caminho canonico dentro de `backend/app/api/infocap_connector.py` e da tool existente `backend/app/agents/tools/infocap_tool.py`.

Implementado:

- busca por CPF e nome passa a confirmar o cliente em `/cliente?codfil&codigo` antes de usar `cpf_cnpj` e catalogo;
- `cpf_cnpj` do detalhe canonico do cliente e a fonte do documento do cliente no DTO interno;
- `PolicyLocator(provider=infocap, codfil, nosnum)` e montado para cada apolice com `nosnum`;
- `numapo` pode resolver para `nosnum`, mas nao chama `/documento` diretamente;
- `policy_ref` nunca nasce de `codigo` ou `codcli`;
- detalhe usa `codfil + nosnum`;
- envelope de `/documento` preserva metadados estruturais de `documento`, `historico`, `acompanhamento`, `parcelas` e `prod_docs`;
- `tabela_itens` fica marcado como campo desconhecido/classificavel;
- codigos curtos como `P`, `A` ou `C` nao viram cobertura;
- ausencia de cobertura estruturada retorna `structured_coverage_absent`;
- presenca de `url_apolice` vira somente `official_document_source_available=true`, sem expor URL;
- feature flag temporaria: `INFOCAP_CANONICAL_POLICY_READ`.

Nao implementado em R1B:

- download, fetch, OCR, Docling ou cache do documento oficial;
- alteracao de `graph.py`, prompts, Capability Registry, RAG, MinIO, Qdrant, Drive, Notion, WhatsApp ou Portal Browser;
- runtime, endpoint, tool ou conector paralelo.

## 23. Fora de escopo da SPEC-015A

- Prompt Efetivo no Portal Admin.
- Migracao completa de `tools_config`.
- Document Evidence por `policy_ref`.
- Ingestao automatica Docling -> Qdrant.
- Drive/Notion produtivos no Core.
- WhatsApp real.
- novos Auxiliares.
- Portal Browser operacional.
