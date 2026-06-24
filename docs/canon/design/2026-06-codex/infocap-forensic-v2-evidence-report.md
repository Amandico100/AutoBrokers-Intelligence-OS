# InfoCap Forensic V2 Evidence Report

> Status: **R0 DOCUMENTAL**
> Data: 2026-06-24
> Escopo: evidencia tecnica para SPEC-015A.
> Restricao: sem PII, sem tokens, sem credenciais, sem payload bruto de cliente.

## 1. Fontes auditadas

Reposititorio atual:

- `backend/app/api/infocap_connector.py`
- `backend/app/agents/tools/infocap_tool.py`
- `backend/app/agents/graph.py`
- `backend/app/core/prompts.py`
- `backend/app/api/chat.py`
- `backend/app/services/langchain_service.py`
- `app/api/chat/stream/route.ts`
- `app/dashboard/chat/page.tsx`
- `app/api/n8n/route.ts`
- `lib/n8nClient.ts`
- `lib/attendance/policy-evidence-pack.ts`
- `lib/attendance/connectors/infocap-policy-lookup.ts`
- `app/api/attendance/cases/[caseId]/runtime/policy-lookup/route.ts`
- `app/api/attendance/cases/[caseId]/runtime/policy-select/route.ts`
- `backend/app/services/document_service.py`
- `backend/app/services/ingestion_service.py`
- `backend/app/services/search_service.py`
- `backend/app/services/sanitization_service.py`
- `backend/app/api/documents.py`
- `backend/app/api/attendance_media.py`

ResultVision historico:

- `server/lib/policyDataProvider/corpInfocapPolicyDataProvider.ts`
- `server/lib/policyDataProvider/types.ts`
- consumidores de policy lookup/summary/answer composer.

Links de referencia historica:

- `https://github.com/Amandico100/ResultVision/tree/main`
- `https://github.com/Amandico100/ResultVision/tree/clean/agent-runtime-foundation-orphan`

## 2. Veredito forense

**COMPROVADO:** a InfoCap esta conectada ao Smith por tool/capability, mas o adapter atual nao preserva contrato forte de identidade, apolice e detalhe. O problema principal nao e falta de prompt nem falta de RAG; e perda/normalizacao incorreta antes do LLM.

**COMPROVADO:** o ResultVision antigo nao deve ser fonte operacional ativa, mas prova uma sequencia mais segura de leitura:

```text
nome/CPF
-> cliente
-> /cliente?codigo
-> cpf_cnpj canonico
-> /cliente_ligacoes
-> nosnum/numapo
-> /documento por nosnum
```

## 3. Evidencias principais no codigo atual

### 3.1 Busca por nome nao confirma cliente canonico

Em `backend/app/api/infocap_connector.py`, `infocap_lookup` usa `/lista_clientes` para nome, extrai o primeiro registro ou retorna multiplos, pega `codigo/codcli` e segue para `/cliente_ligacoes`.

Nao ha chamada comprovada para `/cliente?codigo` apos busca por nome.

Impacto:

- CPF pode vir da linha de busca, nao do detalhe canonico;
- homonimos e resultados aproximados ficam perigosos;
- a apolice pode ser ligada a uma identidade insuficientemente confirmada.

### 3.2 CPF vem de candidatos genericos

`_DOC_KEYS` aceita:

```text
cpf_cnpj, cpf, cnpj, documento, doc, cpfcnpj, cgccpf, ni
```

Impacto:

- CPF/CNPJ canonico pode ser substituido por outro identificador;
- o Core pode exibir documento errado se o provider trouxer campos similares.

### 3.3 `policy_ref` mistura papeis

No sanitizer atual, `policy_ref` pode ser derivado de `nosnum`, `codigo` ou `codcli`.

Impacto:

- `codigo/codcli` sao identificadores de cliente, nao de detalhe da apolice;
- `/documento?nosnum=<policy_ref>` pode receber identificador errado;
- uma apolice pode aparecer encontrada, mas o detalhe estar incorreto ou vazio.

### 3.4 Envelope de `/documento` pode ser descartado

O detalhe atual chama `/documento`, depois reduz a resposta via `_extract_documents` e usa `docs[0]`.

Se o provider responder:

```text
{
  documento: [...],
  itens: [...],
  coberturas: [...],
  parcelas: [...],
  historico: [...]
}
```

o adapter pode manter apenas `documento[0]` e perder as listas irmas.

Impacto:

- cobertura detalhada pode existir no envelope e nao chegar ao evidence pack;
- premio, parcelas, historico e acompanhamento podem ser perdidos;
- o LLM recebe "apolice localizada", mas sem detalhes.

### 3.5 Codigo curto pode virar cobertura

`_coverage_sections` e o espelho TS `collectSections` usam chaves genericas como `descricao`, `cobertura`, `garantia`, `nome`, `item`, `ramo` e `tipo`.

Impacto:

- se `item` ou `tipo` contiver apenas `P`, o sistema pode produzir "Cobertura: P";
- isso e parser bug, nao interpretacao inteligente.

### 3.6 LLM recebe evidencia incompleta

`InfocapPolicyLookupTool` resume o resultado e entrega texto ao modelo. `graph.py` vincula tools ao LLM e extrai a resposta final.

O prompt orienta a nao inventar, mas nao ha checagem deterministica pos-resposta que compare cada afirmacao com o evidence pack.

Impacto:

- resposta pode soar conclusiva mesmo quando a tool retornou lacuna;
- prompts nao devem ser usados para compensar parser incorreto.

## 4. Comparacao com ResultVision

| Responsabilidade | ResultVision | Sistema atual | Impacto |
| --- | --- | --- | --- |
| Nome -> cliente | Busca por nome e carrega detalhe por codigo | Busca por nome e segue sem `/cliente?codigo` | CPF canonico nao garantido |
| CPF canonico | `cpf_cnpj` do detalhe do cliente | `_DOC_KEYS` generico | CPF errado possivel |
| Catalogo | `/cliente_ligacoes?codigo` | `/cliente_ligacoes?codigo` | Parte preservada |
| `nosnum` | ID para detalhe `/documento` | Misturado em `policy_ref` com `codigo/codcli` | Detalhe errado possivel |
| `numapo` | Numero exibivel/buscavel | Pode concorrer com `nosnum` em policy number | Ambiguidade |
| `/documento` | Mapeia payload completo e raw subsets | Reduz para `docs[0]` | Coberturas/listas podem sumir |
| Coberturas | Extrai `itens/coberturas`; summary consome raw subsets | Extrai do objeto reduzido | Menos robusto |
| PDF | Leitura oficial existia como consumidor separado se houvesse acesso | Sem contrato PDF comprovado | JSON continua fonte operacional |

## 5. Trace do Chat Principal

```text
Dashboard Chat
-> /api/chat/stream
-> backend /chat/stream
-> LangChainService
-> graph.py
-> Capability Resolver
-> InfocapPolicyLookupTool
-> infocap_lookup / infocap_policy_detail
-> resumo da tool + data
-> LLM
-> resposta final
```

Separacao:

- provider: respostas InfoCap;
- adapter: normaliza e seleciona;
- evidence pack: estrutura para Core/Even;
- LLM: redacao final;
- logs: devem receber apenas trace seguro.

## 6. N8N

**COMPROVADO:** o chat textual atual envia para `/api/chat/stream`.

**COMPROVADO:** `/api/n8n` ainda existe como rota de compatibilidade e pode rotear para LangChain ou webhook conforme `use_langchain` e `webhook_url`.

Classificacao canonica:

```text
transport legacy / compatibilidade
nao runtime principal
nao caminho de leitura de apolices
nao fonte de verdade
congelado para novas funcionalidades
```

## 7. Documentos, Docling e RAG

Pipeline existente:

```text
DocumentService
-> MinIO
-> IngestionService
-> Qdrant
-> SearchService
-> KnowledgeBaseTool
```

Docling/sanitizacao:

```text
sanitization_service
-> MinIO
-> Docling microservice
-> markdown sanitizado
-> download/manual
```

Lacunas:

- Docling nao entra automaticamente na ingestao;
- documentos nao sao vinculados canonicamente a `policy_ref`;
- Attendance media extrai evidencia, mas nao vira Knowledge/Evidence por `policy_ref`;
- RAG nao corrige CPF ou parser InfoCap.

## 8. Riscos de producao

### Bloqueador

- `policy_ref` derivado de `codigo/codcli`.
- CPF canonico sem `/cliente?codigo` no fluxo por nome.
- perda do envelope de `/documento`.

### Alto

- codigo curto como `P` virar cobertura.
- LLM responder sobre evidencia incompleta.
- logs atuais poderem conter identificadores ou preview de resposta com dado sensivel.

### Medio

- `tools_config`, HTTP Tools e MCP ainda parcialmente fora da autoridade unica.
- N8N legacy confundido com runtime.
- Docling desconectado da ingestao automatica.

### Baixo

- comentarios antigos/desatualizados em partes do Attendance confundem manutencao.
- fixtures atuais nao cobrem todos os shapes reais.

## 9. Conclusao operacional

A primeira mudanca de producao apos o R0 deve ser exclusivamente a R1:

```text
Canonical InfoCap Policy Read Adapter
+ Golden tests
+ trace seguro
+ rollback por feature flag
```

Nao iniciar Prompt Efetivo, RAG documental, Drive/Notion, Auxiliares ou WhatsApp antes da base de leitura de apolice estar correta.
