# Fase C — Progresso C1 + Handoff (relatório para o Founder e para o novo chat)

> Data: 2026-06-23. Base: [SPEC-014](../../SPEC-014-capability-registry-knowledge-os.md) + [auditoria](phase-c-capability-recon-audit.md). Princípio: **usar o que existe, ligar em produção, sem estrutura paralela.**

## 1. O que foi FEITO nesta sessão (no `main`)
- **Auditoria enterprise (código real)** — ~80% da Fase C já existe no Smith. `e01fa74`.
- **SPEC-014 congelada** (arquitetura única, catálogo, matriz, decisões). `e01fa74`.
- **Composio: decidido NÃO** (direto/interno; closed-source/fraco multi-tenant; já temos os conectores).
- **Capability Registry — núcleo** (`lib/capabilities/registry.ts`: catálogo 19 + matriz + resolver; teste 21/21) + runbook das tabelas `SPEC-014-01-capability-registry.sql`. `df61639`.
- **Cockpit de Capabilities (folded em Empresa→Agentes)** — mostra o que Core/Even/Auxiliares podem usar, status (ligado / precisa conectar / off), e botão **"Sincronizar acessos do runtime"**. API `agent/capabilities` (GET diagnóstico + POST sync/entitlement). *(este commit)*
- **Produção — normalização da busca web** (executada direto no banco, segura/reversível): **Core com web ON** (corretoras reais), **Even com web OFF** (matriz). Corrigiu inconsistência real encontrada (Even estava com web=true, Core com web=false).

## 2. Status da SUA checklist (o que já existe / falta)
**Bloco Capability/Knowledge**
- [x] SPEC de Capability Registry — SPEC-014.
- [x] Capability Registry — núcleo + cockpit prontos; **tabelas: aplicar runbook SPEC-014-01**.
- [~] Seed Pack Global — infra de RAG existe; **conteúdo curado = próximo slice C1**.
- [~] RAG global robusto / [~] RAG privado por corretora — **infra pronta** (Qdrant/MinIO/rerank/knowledge_scope); falta curadoria/seed.
- [~] Memory scopes reais — **existe** (`memory_service`); expor como capability governada = próximo slice.
- [~] Control Plane Read — capability definida; **wiring no runtime do Core (Python) = slice 3**.
- [x] Diagnóstico de capabilities — cockpit (GET resolve).
- [~] FinOps por capability/tool — uso por agente já existe (TA2-C); **por capability = próximo slice**.
- [x] Busca web — **pronta**; falta só você setar `TAVILY_API_KEY` (flags já normalizadas).
- [x] InfoCap somente leitura — **conector completo**; falta credencial da Resulta + **tool do Core no runtime (slice 3)**.
- [~] OAuth por tenant — **backend pronto** (MCP servers+OAuth Drive/Calendar/Slack/GitHub); **UI de conectar no Dashboard = C2**.
- [x] Decisão Composio/Nango/direto — **direto/interno**.

**Bloco externo (depende de você / C2):** Z-API (pagar/webhook/canary), AllianzNet (credencial), Browserbase (rotacionar chave), canary portal + SessionRef, Allianz Residencial Eletricista ponta a ponta.

**Bloco governança/qualidade:** kill switches/consentimento/approval **já existem**; **evals reais, isolamento entre tenants, simulação de falha de provider, custo por capability, limites por plano = C1/C2 (transversal)**.

**Skills de Portais / Knowledge OS / Biblioteca de Auxiliares:** no roadmap da SPEC-014 (§10/§9/§11). Skills de Portal + Auxiliares = **C2**; Knowledge OS = **C1**.

## 3. TAREFAS QUE VOCÊ PRECISA FAZER (para tudo funcionar em produção)
1. **Aplicar runbook `SPEC-014-01-capability-registry.sql`** (cria capabilities/bindings/entitlements + seed). *(spec-013-07/08 você já aplicou.)*
2. **Setar no backend (EasyPanel) a env `TAVILY_API_KEY`** com a sua chave Tavily. *(NÃO está no repositório, por segurança.)* → busca web do Core liga na hora.
3. **InfoCap da Resulta**: cadastrar credencial + `base_url` na tela de conector (Dashboard → Conectores → InfoCap). Sem isso, InfoCap fica "needs_connection".
4. **Deploy** do backend + frontend (para o cockpit e os próximos slices entrarem).
5. (C2, quando chegar lá) Pagar/reativar **Z-API**; credencial **AllianzNet**; rotacionar chave **Browserbase**.

## 4. O QUE TESTAR (aceite de produção)
- **Chat Core**: perguntar algo atual ("notícias de hoje sobre…") → deve usar busca web (após `TAVILY_API_KEY`).
- **Cockpit** (Admin → Empresa → Agentes → "Capacidades"): Core mostra busca web "ligada"; Even **sem** busca web; InfoCap "conectar" até cadastrar credencial.
- **Sincronizar acessos**: botão deixa Core com web e Even sem web (idempotente).
- **InfoCap** (após credencial): no atendimento, lookup de apólice por CPF retorna evidência sanitizada.
- **Diagnóstico & manutenção**: modelo do Core (gpt-4o), saldo, conhecimento.

## 5. PRÓXIMOS PASSOS (minha opinião, em ordem)
1. **Slice 3 do C1 — Poderes do Core no runtime (Python, precisa de deploy):** anexar ao Core, governado pelo Registry, as tools **InfoCap (read)**, **Control Plane Read** (estado da corretora: corredores, auxiliares, conexões, custos) e **leitura de documentos (Docling)**. É o que transforma o Core em "braço direito" de verdade. *(Busca web já fica pronta antes disso.)*
2. **Knowledge OS (C1):** Seed Pack Global curado + curadoria do RAG global + memória escopada + 1ª bateria de evals (Core/Even). Robustez do conhecimento que você quer.
3. **C2 — Conectores tenant + Auxiliares + Skills de Portal:** UI de conectar OAuth (Drive/Calendar/Slack/GitHub direto), **5 Auxiliares robustos** (pesquisa, resumo, follow-up, cobrança, leitura de docs), **Skills de Portal** (apólice/status/cobrança/assistência/abertura com approval) sobre o Portal Browser existente, WhatsApp/Z-API ao vivo.
4. **Transversal:** custo por capability, limites por plano, evals contínuos, teste de isolamento entre tenants, simulação de falha de provider.

## 6. Commits desta fase (para auditoria)
```
e01fa74 docs(spec): SPEC-014 + auditoria (plano Fase C congelado)
df61639 feat(capabilities): C1 (1/n) registry core (catalog + matriz + resolver) + runbook + teste 21/21
<este>  feat(capabilities): C1 (2/n) cockpit de capabilities + normalização da busca web (Core on / Even off)
```
Runbooks a aplicar no deploy: **SPEC-014-01** (Fase C). *(spec-013-07/08 já aplicados.)*
