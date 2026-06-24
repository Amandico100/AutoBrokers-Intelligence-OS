# R1A - InfoCap Contract Capture Gate Report

> Status: implementado como preparacao para R1B.
> Data: 2026-06-24.
> Escopo: captura contratual segura da cadeia InfoCap e harness inicial de Goldens.

## 1. Arquivos alterados

- `backend/app/api/infocap_connector.py`
- `app/api/attendance/connectors/infocap/probe/route.ts`
- `app/admin/companies/[companyId]/agents/page.tsx`
- `backend/tests/test_infocap_contract_capture.py`
- `backend/tests/fixtures/infocap_contract_shapes/policy_chain_top_level_lists.json`
- `docs/canon/SPEC-015A-canonical-infocap-policy-read-adapter.md`
- `docs/canon/GOLDEN-TEST-MATRIX-INFOCAP.md`
- `docs/canon/PROGRAM-RECOVERY-F0-F2.md`
- `docs/canon/SMITH-RUNTIME-TOOL-AUTHORITY-MAP.md`
- `docs/canon/design/2026-06-codex/infocap-forensic-v2-evidence-report.md`

## 2. Componentes reutilizados

- endpoint existente `POST /attendance/connectors/infocap/probe`;
- `backend/app/api/infocap_connector.py`;
- `tenant_connections`;
- `connector_templates`;
- Vault via `encrypted_secret_ref`;
- conexao InfoCap existente;
- auth master/admin existente;
- diagnostico existente em Empresa -> Agentes -> Diagnostico & manutencao.

## 3. Nenhuma estrutura paralela criada

Nao foi criado:

- conector InfoCap paralelo;
- runtime paralelo;
- RAG paralelo;
- parser paralelo;
- storage paralelo;
- Vault paralelo;
- migration;
- tabela nova;
- pagina nova;
- novo sistema de tools.

## 4. Endpoints cobertos pelo probe

O modo `policy_chain_contract` cobre:

```text
A. initial_search.cliente_cpf ou initial_search.lista_clientes
B. customer_detail.cliente
C. policy_catalog.cliente_ligacoes
D. policy_detail.documento
```

O detalhe de apolice so e chamado quando houver:

- exatamente um cliente nao ambiguo;
- `codigo` e `codfil` suficientes para `/cliente`;
- catalogo de apolices;
- uma unica apolice elegivel ou `policy_ref/nosnum` informado pelo operador.

Se houver varias apolices e nenhuma referencia for informada, o probe retorna `ambiguous_policy` sem escolher silenciosamente.

## 5. Dados proibidos

O probe nao pode retornar, logar ou persistir:

- CPF/CNPJ;
- nome;
- email;
- telefone;
- endereco;
- numero de apolice;
- `nosnum`;
- `codigo`;
- `codfil`;
- valores de premio;
- valores de cobertura;
- token;
- senha;
- payload bruto;
- preview de payload.

Pode retornar nomes de chaves, tipos, contagens, flags booleanas e hashes de shape.

## 6. Como o Founder deve rodar

Depois do deploy:

1. Portal Admin.
2. Empresas.
3. Resulta Seguros.
4. Agentes.
5. Diagnostico & manutencao.
6. Abrir `Diagnosticar contrato InfoCap`.
7. Escolher CPF ou Nome.
8. Informar um segurado de teste que possui apolice.
9. Informar a referencia da apolice quando houver.
10. Clicar em `Executar`.
11. Copiar somente o JSON estrutural exibido.

## 7. Formato do resultado esperado

Trazer de volta somente a estrutura abaixo, sem valores reais:

```json
{
  "ok": true,
  "provider": "infocap",
  "mode": "policy_chain_contract",
  "status": "found",
  "auth_http_status": 200,
  "candidate_count": 1,
  "document_count": 1,
  "detected_policy_fields": {
    "codigo_present": true,
    "codfil_present": true,
    "cpf_cnpj_present": true,
    "nosnum_present": true,
    "numapo_present": true,
    "items_present": true,
    "coverages_present": false,
    "premiums_present": false,
    "deductibles_present": false,
    "clauses_present": false,
    "installments_present": true,
    "history_present": true,
    "assistance_present": false
  },
  "endpoints": [
    {
      "logical_endpoint": "initial_search.cliente_cpf",
      "http_status": 200,
      "raw_type": "object",
      "top_level_keys": ["cliente"],
      "nested_key_paths": ["cliente", "cliente[]", "cliente[].codigo"],
      "types_by_key": {
        "cliente": "array"
      },
      "list_keys": ["cliente"],
      "counts": {
        "cliente": 1
      },
      "sample_keys": {
        "cliente": ["codigo", "codfil", "cpf_cnpj"]
      },
      "array_key_detected": "cliente",
      "shape_hash": "hash",
      "parse_status": "ok"
    }
  ]
}
```

Os arrays acima sao exemplos de chaves. O resultado real deve preservar apenas nomes de chaves, tipos, hashes e contagens.

## 8. R1B continua bloqueada

R1B nao deve iniciar ate que o resultado real do R0.5 confirme:

- qual endpoint de busca retorna cliente utilizavel;
- se `/cliente_cpf` e `/cliente` tem shapes equivalentes ou nao;
- onde aparecem `codigo`, `codfil` e `cpf_cnpj`;
- onde aparecem `nosnum` e `numapo`;
- se `/documento` traz `itens` e/ou `coberturas` no topo do envelope ou dentro de `documento`;
- onde aparecem premio, franquia, LMI/importancia segurada, clausulas, parcelas, historico, acompanhamento e assistencias;
- se ha shape desconhecido que exige tratamento especifico.

## 9. Campos a confirmar no resultado real

- `codigo_present`
- `codfil_present`
- `cpf_cnpj_present`
- `nosnum_present`
- `numapo_present`
- `items_present`
- `coverages_present`
- `premiums_present`
- `deductibles_present`
- `clauses_present`
- `installments_present`
- `history_present`
- `assistance_present`
- `array_key_detected` por endpoint
- `top_level_keys` de `/documento`
- `sample_keys` de cada lista
- `shape_hash` por endpoint

