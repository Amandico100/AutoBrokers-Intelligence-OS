# BATCH 1.5 — Purga de legado e-commerce (UCP/Shopify/Storefront) + resíduos

> Programa: `docs/canon/FABLE_RECOVERY_PROGRAM.md` (Onda 1.5)
> Autor do batch: Fable (líder técnico) · Executor: Codex
> Natureza: **remoção mecânica de código morto**, sem mudança de comportamento
> para o produto de seguros. Zero criatividade: seguir exatamente este documento.

## Objetivo

Remover do AutoBrokers todo o legado de e-commerce herdado do Smith V6.2
(UCP/Shopify/Storefront) e resíduos de demo, porque e-commerce NÃO é roadmap do
produto (Decision Ledger D6). Isso reduz superfície de ataque, custo de tokens
(bloco de prompt de commerce), ruído para futuros modelos e peso do grafo.

## Regras invioláveis do batch

1. Trabalhar em branch nova: `chore/batch-1.5-legacy-purge`, criada de `main`.
2. **PROIBIDO tocar** em qualquer arquivo destes caminhos (mesmo que pareça
   relacionado): `backend/app/api/infocap_connector.py`, `backend/app/agents/nodes.py`
   (exceto as 2 edições listadas abaixo), `backend/app/agents/tools/infocap_tool.py`,
   `backend/app/services/policy_*`, `backend/app/services/assistance_policy.py`,
   `backend/app/providers/**`, `backend/app/core/feature_flags.py`, `lib/attendance/**`,
   `backend/tests/test_infocap_*`, `backend/tests/test_spec016*`, `docs/canon/**`
   (exceto marcar este batch como concluído no final).
3. **PROIBIDO**: criar migration; alterar banco; mexer em prompts de seguro;
   renomear coisas "de brinde"; refatorar além do que está listado; deletar a
   tabela `ucp_connections` do banco (fica órfã, documentada — limpeza de dados
   é outra onda).
4. Nenhum arquivo novo além do relatório final do batch.
5. Se qualquer verificação falhar e a causa não for óbvia, PARAR e reportar —
   não "consertar" improvisando.

## Parte A — Remoção UCP/Shopify/Storefront (backend)

### A1. Deletar arquivos inteiros

```text
backend/app/agents/tools/shopify_catalog_tool.py
backend/app/agents/tools/storefront_catalog_tool.py
backend/app/agents/tools/ucp_factory.py
backend/app/api/ucp.py
backend/app/schemas/ucp_manifest.py
backend/app/services/shopify_auth.py
backend/app/services/shopify_catalog.py
backend/app/services/storefront_mcp.py
backend/app/services/ucp_discovery.py
backend/app/services/ucp_service.py
backend/app/services/ucp_transport.py
backend/app/services/ucp_providers/        (pasta inteira)
```

### A2. Editar `backend/app/main.py`

- Remover o import do `ucp_router` e a linha `app.include_router(ucp_router, prefix="/api", tags=["UCP Commerce"])`.

### A3. Editar `backend/app/agents/graph.py`

- Remover o bloco inteiro `=== UCP TOOLS (Commerce - Dinâmicas) ===` (o `try` que
  importa `UCPToolFactory` e faz `tools.extend(ucp_tools)`).
- Remover o bloco inteiro `=== UCP INSTRUCTIONS ===` em `_build_initial_state`
  (o `try` que consulta `ucp_connections` e injeta o prompt "## 🛒 SISTEMA DE
  COMMERCE (UCP)").

### A4. Editar `backend/app/agents/nodes.py` (ÚNICAS edições permitidas neste arquivo)

- Remover o ramo `elif tool_name.startswith("shopify_") or tool_name.startswith("ucp_"):`
  (injeção de agent_id para UCP tools) dentro de `tool_node`. Nada mais.

### A5. Varredura de referências restantes (backend)

- Rodar `grep -rniE "ucp|shopify|storefront" backend/app` e remover somente
  imports/exports/refs mortos que apontem para os arquivos deletados
  (ex.: `backend/app/agents/tools/__init__.py`, `backend/app/api/agents.py`,
  `backend/app/core/config.py` — settings UCP/SHOPIFY se existirem).
- ATENÇÃO: NÃO remover a definição da tabela em migrations históricas
  (`backend/supabase/migrations/**` é intocável).

## Parte B — Frontend (somente referências mortas)

- Rodar `grep -rniE "ucp|shopify|storefront" app components lib types hooks`.
- Remover componentes/rotas/refs exclusivos de commerce (ex.: renderização de
  `ucp_product_list`/carrossel de produto, páginas de conexão UCP, tipos UCP).
- Regra: se um componente for compartilhado (usado também fora de commerce),
  remover apenas o uso de commerce, não o componente.

## Parte C — Resíduos de demo (verificar-então-remover)

Para cada item: provar com grep que nada referencia, depois deletar. Se houver
referência ativa, NÃO deletar — listar no relatório.

```text
app/sandbox/                    (página de showcase de padrões)
lib/mock/tenant-modules.ts      (mock)
public/smith-logo.png
public/smith-logo1.png
public/"Design sem nome (23).png"
public/"Design sem nome (26).png"
```

**FORA deste batch (não tocar)**: `app/embed/`, `public/widget.js` (podem ser o
widget de chat embutido — decisão na Onda 3), tudo de n8n/voz (congelado, Onda 3).

## Verificação obrigatória (todas precisam passar)

```bash
# 1. Suíte Python completa — 100% verde, mesmos totais de antes do batch:
for f in backend/tests/test_*.py; do python "$f"; done

# 2. Zero referências de commerce no código ativo do backend:
grep -rniE "ucp|shopify|storefront" backend/app || echo LIMPO   # deve imprimir LIMPO

# 3. Frontend compila:
npm run typecheck && npm run build

# 4. Compilação Python dos arquivos editados:
python -m py_compile backend/app/main.py backend/app/agents/graph.py backend/app/agents/nodes.py
```

## Entrega

1. Commits pequenos por parte (A, B, C), mensagens `chore(purge): ...`.
2. NÃO fazer merge na main e NÃO fazer deploy — abrir a branch e reportar:
   arquivos deletados/editados, saída das 4 verificações, itens da Parte C que
   ficaram (com o grep que provou uso), e qualquer desvio.
3. Rollback do batch inteiro = descartar a branch.
