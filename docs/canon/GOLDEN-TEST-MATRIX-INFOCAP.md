# GOLDEN-TEST-MATRIX-INFOCAP

> Status: **R0 DOCUMENTAL**
> Data: 2026-06-24
> Uso: matriz obrigatoria para a Fase R1 / SPEC-015A.
> Dados: somente fixtures sinteticas ou reais anonimizadas; nunca PII real.

## 1. Regras de fixture

- Preservar shape real do JSON quando fixture real anonimizada existir.
- Trocar CPF/CNPJ, nomes, telefones, emails, enderecos, placas, numeros de apolice e IDs sensiveis por valores sinteticos.
- Manter chaves originais, tipos, arrays, aninhamentos e casos dificeis.
- Nao commitar payload bruto de cliente.
- Nao incluir token, senha, base_url privada ou segredo.
- Cada fixture deve declarar `source_shape`, `anonymization_level`, `expected_parser_status` e `risk_case`.

## 2. Convencao de nomes

```text
infocap_customer_name_single.json
infocap_customer_name_homonym.json
infocap_customer_cpf_detail.json
infocap_policy_catalog_multiple.json
infocap_policy_detail_top_level_itens.json
infocap_policy_detail_item_code_p.json
```

## 3. Matriz Golden

| ID | Fixture | Objetivo | Entrada | Shape minimo | Resultado esperado | Nao pode acontecer |
| --- | --- | --- | --- | --- | --- | --- |
| G01 | Nome unico | Busca por nome com cliente correto | `customer_name` | `/lista_clientes` com 1 candidato + `/cliente` | Adapter chama detalhe do cliente e usa `cpf_cnpj` canonico | Usar CPF da linha de busca como fonte final |
| G02 | Homonimo | Nome retorna mais de um cliente plausivel | `customer_name` | `/lista_clientes` com 2+ candidatos | `ambiguous_customer` / exige selecao | Selecionar primeiro automaticamente |
| G03 | CPF direto | Busca por CPF/CNPJ | `cpf_cnpj` | `/cliente_cpf` com cliente | `codigo` e `cpf_cnpj` canonicos resolvidos | Aceitar `documento/doc/ni` como canonico se `cpf_cnpj` existe |
| G04 | Detalhe cliente | Cliente detalhado com `cpf_cnpj` | `codigo` | `/cliente?codigo` | CPF vem exclusivamente de `cpf_cnpj` e o fluxo CPF tambem chama `/cliente` | CPF herdado de apolice/documento |
| G05 | `numapo` -> `nosnum` | Numero exibivel resolve detalhe | `policy_number` | `/documentos` com `numapo` e `nosnum` | Seleciona por match e cria `PolicyLocator(codfil,nosnum)` | Chamar `/documento` usando `numapo` sem resolver |
| G06 | Multiplas apolices | Catalogo com varias apolices | `codigo` | `/cliente_ligacoes` 2+ docs | Lista opcoes com `policy_ref` exibivel e locator interno por `codfil+nosnum` | Criar `policy_ref` com `codigo/codcli` |
| G07 | Cancelada | Apolice cancelada | `policy_ref` | detalhe com status cancelado | `cancelled=true`, nao liberar cobertura operacional | Tratar como vigente |
| G08 | Vigente | Apolice vigente | `policy_ref` | vigencia/status ativo | `active_now=true` quando datas/status permitirem | Confirmar cobertura sem itens |
| G09 | Itens no topo | `/documento` com `itens` no topo do envelope | `policy_ref` | `{documento:[...], itens:[...]}` | Extrai `itens` sem perder envelope | Reduzir para `documento[0]` e perder itens |
| G10 | Coberturas no topo | `/documento` com `coberturas` no topo | `policy_ref` | `{documento:[...], coberturas:[...]}` | Extrai coberturas | Retornar cobertura ausente por descarte |
| G11 | Sem cobertura | `/documento` sem itens/coberturas/clausulas | `policy_ref` | documento sem listas de cobertura | Retorna `structured_coverage_absent` e ausencia honesta | Inventar cobertura |
| G12 | `item = P` | Codigo curto em campo de item/tipo | `policy_ref` | `itens:[{item:"P"}]` ou equivalente | Preserva como codigo bruto, nao label | Responder "Cobertura: P" |
| G13 | Franquia | Franquia explicita | `policy_ref` | chave de franquia em cobertura/detalhe | DTO traz franquia com fonte | Colocar franquia em cobertura sem label |
| G14 | LMI | Limite maximo/Importancia segurada | `policy_ref` | `lmi`, `limite`, `importancia_segurada` | DTO normaliza valor e origem | Confundir premio com LMI |
| G15 | Premio | Premio/parcela | `policy_ref` | `premio`, `parcelas` | DTO separa premio e parcelas | Chamar premio de cobertura |
| G16 | Clausula | Clausula/condicao explicita | `policy_ref` | `clausulas` ou texto estruturado | DTO preserva clausula e fonte | Confirmar cobertura sem considerar clausula |
| G17 | Assistencia | Assistencia residencial/auto explicita | `policy_ref` | `assistencias` ou item equivalente | DTO traz assistencia como assistencia | Misturar assistencia com cobertura securitaria sem label |
| G18 | Conflito InfoCap x documento | Documento oficial diverge da InfoCap | `policy_ref` + documento | evidence pack + doc evidence | Estado exige validacao humana | Escolher uma fonte automaticamente |
| G19 | Core DTO | Core interno autorizado | usuario interno | DTO interno completo | Core recebe campos completos permitidos | Mascarar indevidamente dado que a tool retornou |
| G20 | Even DTO | Even externa | caso vinculado | DTO externo minimo | Even recebe minimo e nao confirma cobertura | Expor CPF completo/PII desnecessaria |
| G21 | Auxiliar DTO | Auxiliar com capability limitada | auxiliar | capability declarada | Recebe apenas subset permitido | Herdar tools/dados do Core sem declaracao |
| G22 | Isolamento tenant | Duas empresas | `company_id` A/B | conexoes separadas | Nunca cruza tenant | Reusar conexao ou dado de outro tenant |
| G23 | Logs sem PII | Trace completo | qualquer fluxo | logs/trace | Somente hashes, shapes, contagens | CPF/nome/token/payload bruto em log |
| G24 | Rollback | Feature flag | flag on/off | adapter antigo congelado | Alterna sem novo conector/runtime | Criar outro caminho operacional |
| G25 | Provider error | Erro de auth/provider | qualquer fluxo | 401/timeout/shape invalido | Erro seguro, sem segredo | Logar senha/token/resposta bruta |
| G26 | Apolice encontrada sem detalhe | Catalogo sem `/documento` util | `codigo` | lista docs, detalhe falha | Pode listar, mas nao interpretar cobertura | Marcar "pronta para cobertura" |
| G27 | Shape inesperado | Array em chave nao prevista | qualquer | shape variado | `parse_status=unknown_shape`, trace seguro | Selecionar lista aleatoria como cobertura |
| G28 | Busca por policy_ref invalido | `policy_ref` fora dos matches | `policy_ref` | lista anterior nao contem ref | Rejeita e exige relookup/selecao | Consultar detalhe sem validar origem |
| G29 | Contract Capture Gate | Probe seguro da cadeia completa | CPF ou nome de teste | `/cliente_cpf|/lista_clientes` -> `/cliente` -> `/cliente_ligacoes` -> `/documento` | Retorna apenas chaves, tipos, hashes e contagens | Retornar CPF, nome, numero, `codigo`, `codfil`, `nosnum` ou payload bruto |
| G30 | Status canonico | Ambiguidade e limites de fonte | shapes sinteticos | multiplos clientes/apolices, timeout, auth, unknown shape | Usa enum estavel: `found`, `ambiguous_customer`, `ambiguous_policy`, `source_limited`, `provider_auth_error`, `provider_timeout`, `unknown_shape`, `document_evidence_required`, `conflict_requires_human` | Status livre/ad hoc |
| G31 | Fonte oficial sem URL exposta | `/documento` com `acompanhamento.emissao.url_apolice` | `policy_ref` | URL presente no envelope | `official_document_source_available=true` sem retornar URL | Expor URL ao chat/log/LLM |
| G32 | Parcelas com origem | `/documento` com `parcelas[]` | `policy_ref` | `datvenc`, `datquit`, `vlvenc`, `vlquit`, `forma_pagamento` | Parcelas normalizadas com `source_fields` | Misturar parcela com cobertura |
| G33 | Financeiros sem semantica inventada | `/documento` com `preliq`, `pretot`, etc. | `policy_ref` | campos financeiros do provider | Retorna `provider_field` e `semantic_status=provider_field_unclassified` | Chamar campo desconhecido de premio total/LMI/franquia |
| G34 | Resolver unico de conexao | Multiplas `tenant_connections` | Chat, detail e probe | uma valida, arquivadas, sem Vault e duplicadas | Todos usam a mesma regra backend | Tool escolher primeira conexao por conta propria |
| G35 | Conexao ambigua | Duas conexoes InfoCap elegiveis | qualquer consulta | 2+ elegiveis | `ambiguous_connection` e nenhuma chamada silenciosa | Escolher mais recente |
| G36 | Locator obrigatorio no detalhe | `policy_ref` simples sem `codfil` validado | detalhe | `nosnum`/`numapo` cru | Retorna limite de fonte ou exige locator resolvido | Chamar `/documento` com `codfil` padrao |
| G37 | Produto nao e cobertura | Produto/ramo residencial ou auto | detalhe sem itens | somente `produto`, `ramo`, `descricao` | `structured_coverage_absent`, `assistance_signals` vazio/unknown | Gerar assistencia/eletricista por produto |
| G38 | Opcoes deterministicas | Multiplas apolices | busca sem ref | catalogo 2+ docs | Texto inclui ate 10 opcoes com seguradora, produto, vigencia, status e numero humano quando valido | LLM escolher sozinho ou exigir locator tecnico |
| G39 | Tool aceita numero humano | Schema da tool | `policy_number` | numero humano da apolice | Tool aceita argumento proprio | Forcar numero humano em `policy_ref` |
| G40 | Numero humano resolve locator | `/documentos` com `numapo` e `nosnum` | `policy_number` | match exato por `numapo` | Resolve `PolicyLocator(codfil,nosnum)` antes do detalhe | Chamar `/documento` com `numapo` direto |
| G41 | Numero humano ambiguo | `/documentos` com 2 matches exatos | `policy_number` | 2+ docs | `ambiguous_policy` com opcoes | Escolher primeiro |
| G42 | Numero invalido | `numapo=0` ou placeholder | listagem/detalhe | numero invalido | Exibe "numero nao retornado pela InfoCap" | Mostrar "Numero: 0" |
| G43 | Output guard InfoCap | Tool retorna contrato operacional | resposta final LLM | LLM omite opcoes ou diz erro tecnico | Smith substitui/completa pela resposta deterministica | Perder opcoes ou inventar erro tecnico |
| G44 | Ausencia de cobertura no chat | `/documento` sem cobertura | pergunta de cobertura | `structured_coverage_absent=true` | Resposta declara ausencia de itens estruturados | Afirmar eletricista/assistencia/incendio/franquia |
| G45 | R1C.0 sem URL oficial | `/documento` sem `url_apolice` | audit mode | detalhe da apolice sem fonte documental | `official_document_url_present=false` e blocker seguro | Inventar fonte documental |
| G46 | R1C.0 PDF valido | `url_apolice` retorna PDF | audit mode | content-type PDF e magic `%PDF` | `retrieval_status=retrieved`, paginas e anchors seguros | Retornar URL, texto do PDF ou payload |
| G47 | R1C.0 HTML/login | `url_apolice` retorna HTML de login | audit mode | HTML com login/senha | `retrieval_status=html_login`, `recommended_r1c_transport=portal_required` | Tratar HTML como PDF |
| G48 | R1C.0 auth mode | PDF requer Authorization/cookie | audit mode | tentativas com token/cookie | `auth_mode_required` controlado | Expor token, cookie ou header |
| G49 | R1C.0 redirect HTTPS | URL redireciona para HTTPS externo | audit mode | redirect seguro limitado | `final_origin_class=external_https` e transporte recomendado | Seguir HTTP inseguro ou expor host completo |
| G50 | R1C.0 oversized | Documento maior que limite | audit mode | content-length acima do maximo | `retrieval_status=unsupported` e blocker `document_too_large` | Baixar arquivo grande inteiro |
| G51 | R1C.0 PDF criptografado | PDF contem `/Encrypt` | audit mode | PDF protegido | `pdf_encrypted=true`, `source_fetch_safe_for_r1c=false` | Enviar para Docling mesmo assim |
| G52 | R1C.0 PDF sem texto | PDF nativo/escaneado sem camada textual | audit mode | PDF sem anchors/texto | `text_layer_status=absent`, candidato a Docling/OCR futuro | Concluir cobertura sem OCR/evidencia |
| G53 | R1C.0 sem vazamento | Qualquer resultado de auditoria | audit mode | URLs, cookies, token e PII sinteticos | Saida contem so classes, booleanos, contagens e buckets | Logar/exibir URL, CPF, nome, numero, `codfil`, `nosnum`, token, cookie ou payload |
| G54 | Backend master-only | Audit mode sem marcador master | `official_document_source_audit` | chamada interna sem header master | bloqueio antes de resolver conexao/provider | Executar auditoria por usuario nao master |
| G55 | SSRF bloqueado | URL oficial maliciosa | audit mode | localhost, loopback, private IP, link-local, metadata | `source_fetch_blocker` seguro | Fazer request para rede interna |
| G56 | Redirect cross-origin sem credenciais | PDF redireciona para host externo HTTPS | audit mode | 302 externo | Authorization/cookie removidos no destino externo | Vazar credenciais para outro origin |
| G57 | Redirect HTTP bloqueado | URL HTTPS redireciona para HTTP | audit mode | 302 para HTTP | `unsafe_redirect` | Seguir HTTP |
| G58 | Tamanho bloqueado | Content-Length ou streaming grande | audit mode | arquivo acima do limite | `document_too_large` | Ler arquivo inteiro em memoria |
| G59 | Tempfile cleanup | Arquivo temporario usado pela auditoria | audit mode | sucesso, erro ou timeout | arquivo removido em `finally` | Deixar PDF temporario no disco |
| G60 | Sem escrita em storage | Auditoria documental | audit mode | qualquer resultado | nenhuma chamada a Docling/MinIO/Qdrant/Supabase/DocumentService | Persistir conteudo nesta etapa |
| G61 | UX sem company_id manual | Card Portal Admin | UI | seletor no card existente | usa `companyId` da rota e nao pede ID manual | Founder copiar ID pelo Console |
| G62 | Output sem dados sensiveis | Resultado de auditoria | audit mode | URL, token, CPF, nome, numero e locators sinteticos | output nao contem dados sensiveis | Expor PII, host integral, URL, token, cookie, `codfil`, `nosnum` ou payload |
| G63 | Classificacao documental combinada | PDF real, PDF sem texto, HTML/login, criptografado, nao PDF | audit mode | respostas sinteticas | status/magic/text_layer/transport corretos | Tratar HTML/ZIP/imagem como apolice lida |

## 4. Goldens de fluxo

### F01 - Nome ate evidencia

```text
nome
-> /lista_clientes
-> /cliente?codigo
-> cpf_cnpj canonico
-> /cliente_ligacoes
-> /documento por nosnum
-> evidence pack valido
```

Aceite:

- `customer.cpf_cnpj.source_endpoint = /cliente`;
- `policy_ref = nosnum`;
- `coverage_sections` so contem labels humanas comprovadas.

### F02 - CPF ate evidencia

```text
cpf_cnpj
-> /cliente_cpf
-> /cliente?codigo obrigatorio
-> /cliente_ligacoes
-> /documento
```

Aceite:

- CPF final igual ao `cpf_cnpj` canonico anonimizado;
- se houver multiplos clientes, fluxo para ambiguidade;
- nenhuma PII em log.

### F03 - Numero de apolice ate detalhe

```text
numapo
-> /documentos?texto
-> resolve nosnum
-> /documento?nosnum
```

Aceite:

- `numapo` aparece como display;
- `nosnum` vira parte do `PolicyLocator`;
- `policy_ref` exibivel nunca usa `codigo/codcli`;
- detalhe nunca usa `codigo/codcli`.

### F04 - Ausencia honesta

```text
/documento sem cobertura
-> evidence pack com lacuna
-> Core informa ausencia da fonte
-> Even pede validacao/handoff quando sensivel
```

Aceite:

- sem invencao;
- sem "P" como cobertura;
- mensagem orienta proximo passo.

## 5. Goldens de seguranca

| ID | Verificacao | Esperado |
| --- | --- | --- |
| S01 | Logs de sucesso | Sem CPF, nome, token, senha, payload bruto |
| S02 | Logs de erro | Sem resposta bruta do provider quando contiver conteudo sensivel |
| S03 | Fixtures | Somente sinteticas/anonimizadas |
| S04 | DTO Even | Minimo necessario ao caso |
| S05 | DTO Core | Completo apenas para usuario interno autorizado |
| S06 | Auxiliar | Dados restritos por capability |
| S07 | Isolamento | `company_id` A nunca acessa conexao B |
| S08 | Rollback | Feature flag nao cria segundo conector |

## 6. Goldens que nao pertencem a R1

Estes ficam para R2/R3:

- Prompt Efetivo no Portal Admin.
- Migracao completa de `tools_config`.
- Ingestao Docling automatica.
- Documento oficial vinculado a `policy_ref`.
- Drive/Notion produtivos.
- WhatsApp real.
- Portal Browser real.

## 7. Cobertura R1B implementada no harness offline

O teste `backend/tests/test_infocap_contract_capture.py` agora cobre:

- `result_count` de `documentos.documentos`;
- identidade canonica por `/cliente` e `cpf_cnpj`;
- `codigo/codcli` nunca virando `policy_ref`;
- `PolicyLocator(provider=infocap, codfil, nosnum)`;
- `numapo` resolvendo para `nosnum`;
- codigo curto `P` nao virando cobertura;
- preservacao estrutural de envelope;
- parcelas com `source_fields`;
- financeiros com `provider_field`;
- `tabela_itens` como campo desconhecido;
- `structured_coverage_absent`;
- `official_document_source_available` sem URL;
- `document_evidence_required` sem fetch/processamento do documento.

## 8. Cobertura R1B.1 implementada no harness offline

O teste `backend/tests/test_infocap_contract_capture.py` tambem cobre:

- uma unica definicao de `_build_evidence_pack`, `_coverage_sections`, `_summarize` e `_summarize_detail`;
- ausencia de `_find_conn_id` local na tool;
- rota Next do probe delegando selecao de conexao ao backend;
- resolver backend escolhendo uma conexao elegivel e recusando zero/duas elegiveis;
- conexao arquivada/inativa e conexao sem Vault ignoradas;
- `policy_locator_ref` no formato `infocap:<codfil>:<nosnum>`;
- `ramo`/`produto` residencial sem assistencia positiva;
- produto auto/eletrico sem sinal de eletricista;
- opcoes deterministicas em ambiguidade;
- nenhuma chamada a provider real.

## 9. Cobertura R1B.2 implementada no harness offline

Os testes `backend/tests/test_infocap_contract_capture.py` e `backend/tests/test_infocap_policy_output_guard.py` cobrem:

- schema/runtime da tool aceitando `policy_number`;
- `numapo` resolvendo para `PolicyLocator`;
- multiplos matches exatos retornando `ambiguous_policy`;
- numero `0` nao sendo exibido como numero valido;
- opcoes de ambiguidade usando numero humano, sem exigir locator tecnico por padrao;
- helper de debug podendo expor locator interno quando necessario;
- output guard impedindo que a LLM apague opcoes;
- output guard impedindo conversao de cobertura ausente em "erro tecnico";
- roteamento do Smith encerrando a resposta operacional de InfoCap sem reescrita livre pela LLM;
- nenhuma chamada a provider real.
