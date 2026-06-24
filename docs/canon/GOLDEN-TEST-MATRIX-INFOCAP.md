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
| G02 | Homonimo | Nome retorna mais de um cliente plausivel | `customer_name` | `/lista_clientes` com 2+ candidatos | `multiple_matches` / exige selecao | Selecionar primeiro automaticamente |
| G03 | CPF direto | Busca por CPF/CNPJ | `cpf_cnpj` | `/cliente_cpf` com cliente | `codigo` e `cpf_cnpj` canonicos resolvidos | Aceitar `documento/doc/ni` como canonico se `cpf_cnpj` existe |
| G04 | Detalhe cliente | Cliente detalhado com `cpf_cnpj` | `codigo` | `/cliente?codigo` | CPF vem exclusivamente de `cpf_cnpj` e o fluxo CPF tambem chama `/cliente` | CPF herdado de apolice/documento |
| G05 | `numapo` -> `nosnum` | Numero exibivel resolve detalhe | `policy_number` | `/documentos` com `numapo` e `nosnum` | Seleciona por match e cria `PolicyLocator(codfil,nosnum)` | Chamar `/documento` usando `numapo` sem resolver |
| G06 | Multiplas apolices | Catalogo com varias apolices | `codigo` | `/cliente_ligacoes` 2+ docs | Lista opcoes com `policy_ref` exibivel e locator interno por `codfil+nosnum` | Criar `policy_ref` com `codigo/codcli` |
| G07 | Cancelada | Apolice cancelada | `policy_ref` | detalhe com status cancelado | `cancelled=true`, nao liberar cobertura operacional | Tratar como vigente |
| G08 | Vigente | Apolice vigente | `policy_ref` | vigencia/status ativo | `active_now=true` quando datas/status permitirem | Confirmar cobertura sem itens |
| G09 | Itens no topo | `/documento` com `itens` no topo do envelope | `policy_ref` | `{documento:[...], itens:[...]}` | Extrai `itens` sem perder envelope | Reduzir para `documento[0]` e perder itens |
| G10 | Coberturas no topo | `/documento` com `coberturas` no topo | `policy_ref` | `{documento:[...], coberturas:[...]}` | Extrai coberturas | Retornar cobertura ausente por descarte |
| G11 | Sem cobertura | `/documento` sem itens/coberturas/clausulas | `policy_ref` | documento sem listas de cobertura | Retorna ausencia honesta e `human_required` quando necessario | Inventar cobertura |
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
