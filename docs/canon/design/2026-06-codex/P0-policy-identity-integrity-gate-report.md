# P0 - Policy Identity Integrity Gate

> Status: implementado para commit P0.  
> R1C.2: preservado em stash, nao aplicado neste commit.  
> Provider real: nao chamado durante desenvolvimento.  
> Data: 2026-06-25.

## 1. Problema

Teste real indicou que uma apolice listada para um segurado podia abrir detalhe de outro cliente quando o numero humano informado coincidia com `nosnum` de outro documento.

Esse risco bloqueia PDF, cache documental, cobertura, assistencia, franquia, Docling, Qdrant e qualquer resposta operacional.

## 2. Causa tecnica

O fluxo de numero humano aceitava match por `numapo` ou por `nosnum`. Isso misturava:

- `numapo`: numero humano exibivel/digitado pelo corretor;
- `nosnum`: identificador tecnico interno da InfoCap.

## 3. Regra P0

Numero humano digitado pelo corretor significa somente `numapo`.

`nosnum` so pode ser usado quando vier em locator tecnico completo:

```text
infocap:<codfil>:<nosnum>
```

## 4. Implementacao

- Criado matcher humano por `numapo`.
- Criado selector de `PolicyLocator` por numero humano.
- Ajustado `_select_policy_locator` para aceitar `nosnum` somente com `codfil` explicito.
- Inserida pos-validacao de identidade antes de montar evidence pack:
  - `numapo` do detalhe igual ao solicitado;
  - locator usado igual ao item de catalogo;
  - detalhe compativel com cliente canonico quando disponivel.
- `identity_mismatch` falha fechado:
  - sem apolice;
  - sem segurado;
  - sem cobertura;
  - sem parcelas;
  - sem PDF;
  - sem cache;
  - sem evidence pack;
  - sem Docling/Qdrant;
  - sem dados para LLM.
- Adicionado contexto seguro no Smith para resolver follow-up pelo catalogo do cliente, sem locator tecnico.
- Adicionado modo master-only `policy_identity_integrity_audit` no diagnostico InfoCap existente.

## 5. Auditoria segura

O Portal Admin passa a oferecer:

```text
Auditar integridade de identidade da apolice
```

Entrada:

- CPF ou nome;
- numero humano da apolice.

Saida segura:

- `identity_status`;
- booleans de validacao;
- contagens;
- `reason_codes`.

Proibido no output:

- CPF;
- nome;
- numero da apolice;
- `codfil`;
- `nosnum`;
- locator;
- URL;
- token;
- payload;
- dados do segurado.

## 6. Testes

Foram adicionados Goldens offline para reproduzir a colisao:

```text
cliente A: numapo = 202623140269982
cliente B: nosnum = 202623140269982, numapo diferente
```

Resultado esperado: a consulta humana por `202623140269982` nunca pode abrir a apolice do cliente B.

## 7. Fora do escopo

Nao foram implementados:

- AssistanceProfile;
- resposta humana R1C.2;
- cache freshness;
- Docling;
- MinIO;
- Qdrant;
- novos auxiliares;
- Prompt Efetivo;
- migration/schema.

## 8. Teste real necessario

Apos revisao e deploy:

1. abrir nova conversa;
2. buscar Rafael por CPF;
3. listar apolices;
4. detalhar os tres numeros humanos testados;
5. rodar auditoria de identidade para cada numero.

Aceite: nenhuma apolice de outro cliente pode aparecer. Em qualquer divergencia, o sistema deve retornar `identity_mismatch`.
