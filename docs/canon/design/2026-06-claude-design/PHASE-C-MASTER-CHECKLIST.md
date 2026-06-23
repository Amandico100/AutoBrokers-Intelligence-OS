# Fase C — Checklist mestre até 100% em produção (handoff para auditoria)

> Data: 2026-06-23. Autoritativo. Base: [SPEC-014](../../SPEC-014-capability-registry-knowledge-os.md), [auditoria](phase-c-capability-recon-audit.md), [progresso C1](PHASE-C-C1-PROGRESS-AND-HANDOFF.md).
> Legenda: ✅ feito · 🔌 pendente de código (eu) · 🔑 depende de você (env/credencial/deploy) · 🧪 teste a fazer.

## 0. Commits da Fase C (auditar nesta ordem)
```
e01fa74 SPEC-014 + auditoria (plano congelado)
df61639 C1(1) registry core (catálogo+matriz+resolver) + runbook SPEC-014-01 + teste 21/21
17c20c7 C1(2) cockpit de capabilities (folded) + busca web normalizada (Core on / Even off)
16304e1 C1(3) poderes do Core (control_plane + infocap) + InfoCap base_url GLOBAL + conexão Resulta
```
Runbooks a aplicar no deploy: **SPEC-014-01** (registry) ; **SPEC-014-02** (InfoCap — modelo p/ novas corretoras; a da Resulta já existe). *(spec-013-07/08 já aplicados.)*

## 1. CHAT PRINCIPAL (Core) → 100% produção
- [x] Modelo forte (gpt-4o) + prompt sênior (não engessado).
- [x] Busca web (Tavily) — código + flags normalizadas (Core on, Even off). 🔑 **falta só `TAVILY_API_KEY` no backend** (você já colocou). 🧪 testar.
- [x] Capability Registry + cockpit (governança de quem usa o quê).
- [x] Control Plane Read (Core conhece a corretora: auxiliares, conexões, saldo, conhecimento).
- [x] InfoCap governado para o Core (consulta de apólice por CPF/nome, sanitizado).
- [ ] 🔌 Conhecimento robusto (RAG curado + Seed Pack) — **próximo (C1 Knowledge OS)**.
- [ ] 🔌 Leitura de documento sob demanda (Docling como tool do Core) — opcional, próximo.
- 🔑 **Aplicar SPEC-014-01** para a governança por corretora (entitlements) ficar 100%.
- 🔑 **Deploy** do backend (as tools novas do Core só entram após deploy).

## 2. ATENDENTE (Even) — Assistência/Sinistro + corredor Eletricista → 100% produção
- [x] Runtime de atendimento (corredores, identidade, macro-estados, consentimento, handoff).
- [x] InfoCap completo (lookup/probe/policy-detail + evidence pack) ligado ao atendimento.
- [x] InfoCap base_url GLOBAL + conexão da Resulta criada (status `configuring`).
- [ ] 🔑 **Credencial InfoCap da Resulta** (login/senha) via tela segura → status `connected`.
- [ ] 🔑 **Z-API**: pagar/reativar + webhook seguro (`WHATSAPP_WEBHOOK_*`, `ATTENDANCE_WHATSAPP_ENABLED=true`, `ATTENDANCE_BRIDGE_URL`).
- [ ] 🔌🧪 **Corredor Eletricista ponta a ponta**: entrada → identidade (CPF) → InfoCap (apólice/cobertura) → evidência → decisão → preparar/abrir assistência (com approval) → resolução. *Validar com caso real após credencial + Z-API.*
- [ ] 🔌 Skills de negócio em Portais (status/cobrança/abertura) sobre o Portal Browser existente — **C2**.

## 3. AUXILIARES → 100% produção
- [x] Mecanismo de publicar/instalar (Fase B) + matriz de capabilities (teto por papel).
- [ ] 🔌 **Biblioteca dos 5 primeiros** (C2): pesquisa (web), resumo (conhecimento+memória), follow-up (WhatsApp), cobrança (conectores+portal billing), leitura de documentos (Docling) — cada um declara as capabilities mínimas.
- [ ] 🔌 Conectar capability resolver ao runtime do auxiliar (anexar tools pela declaração) — **C2**.

## 4. CONECTORES / APLICATIVOS (estilo ChatGPT) → produção
- [x] Vault + aprovações + auditoria (backend + UI).
- [x] MCP servers + OAuth **prontos no backend**: Google Drive, Google Calendar, Slack, GitHub.
- [x] InfoCap (conector próprio) global + por corretora.
- [ ] 🔌 **Galeria de conectores + connect OAuth no Dashboard** (categorizada: produtividade/pesquisa/vendas/comunicação) — **C2** (o backend já existe; falta a UI de conectar e o token por tenant no Vault).
- [ ] 🔌 Apps importantes a incluir (ordem sugerida): Google Drive, Gmail, Google Calendar, Notion, Slack, WhatsApp (Z-API), InfoCap, Portais seguradora. *(Composio/Nango: NÃO agora — decisão SPEC-014.)*

## 5. KNOWLEDGE OS / RAG → produção
- [x] Infra: Qdrant + MinIO + rerank (Cohere) + ingestion + escopo global/privado + Docling.
- [ ] 🔌 **Seed Pack Global** (conteúdo curado AutoBrokers) — C1 Knowledge OS.
- [ ] 🔌 **RAG global curado + RAG privado por corretora** (curadoria/publicação) — C1.
- [ ] 🔌 **Memória escopada** (empresa/usuário/caso) como capability — C1.
- [ ] 🔌🧪 **Evals** de Core/Even/RAG (a fonte certa é usada?) — C1/transversal.

## 6. GOVERNANÇA / QUALIDADE / PRODUÇÃO (transversal)
- [x] Postura: ligar em produção mantendo só guardrails legais (consentimento, approval p/ escrita, sem afirmar cobertura sem evidência).
- [x] Kill switches / approvals / consentimento (já existem).
- [ ] 🔌 FinOps por capability/tool (uso por agente já existe; falta por capability).
- [ ] 🔌 Limites por plano + observabilidade por ferramenta.
- [ ] 🧪 Teste de isolamento entre tenants (Rafael não vê dados da Resulta).
- [ ] 🧪 Simulação de falha de provider (InfoCap/Tavily fora → degrada com mensagem, não quebra).
- [ ] 🧪 LGPD operacional (mascaramento/retenção — InfoCap já mascara).

## 7. SUAS TAREFAS AGORA (🔑) — para ligar o que já está pronto
1. **Aplicar `SPEC-014-01`** (registry: capabilities/bindings/entitlements + seed).
2. **`TAVILY_API_KEY`** no backend (feito) — revogar/gerar nova (foi colada no chat).
3. **Credencial InfoCap da Resulta**: Dashboard da Resulta → Conectores → InfoCap → login `resulta@api.com.br` + senha → salva (cifra no Vault, vira `connected`). *(base_url já é global.)*
4. **Deploy** do backend + frontend (slice 3 + cockpit).
5. (Quando for ao C2) Z-API paga + webhook; credencial AllianzNet; rotacionar chave Browserbase.

## 8. TESTES QUE VOCÊ DEVE FAZER (🧪) — aceite
1. **Core busca web**: "quais as últimas notícias sobre seguros no Brasil?" → responde com fontes.
2. **Core conhece a corretora**: "minha corretora está pronta? quais auxiliares e conexões eu tenho?" → usa control_plane (auxiliares/conexões/saldo reais).
3. **Core InfoCap** (após credencial): "consulta a apólice do CPF X" → retorna seguradora/produto/vigência mascarados, ou "não encontrei".
4. **Cockpit** (Admin → Empresa → Agentes → Capacidades): Core mostra busca web "ligada", InfoCap "conectar"→depois ativo; botão Sincronizar idempotente.
5. **Atendimento eletricista** (após InfoCap + Z-API): caso real ponta a ponta.
6. **Isolamento**: confirmar que a Resulta só enxerga InfoCap da Resulta (Rafael separado).

## 9. PRÓXIMOS PASSOS (minha recomendação de ordem)
1. **Você**: aplicar SPEC-014-01 + credencial InfoCap Resulta + deploy + rodar os testes §8 (1–4).
2. **Eu (C1 Knowledge OS)**: Seed Pack + RAG curado + memória escopada + evals — robustez do conhecimento.
3. **Eu (C2)**: galeria de conectores OAuth no Dashboard + 5 Auxiliares + Skills de Portal + WhatsApp/Z-API ao vivo → corredor eletricista ponta a ponta.
4. **Transversal**: FinOps por capability, limites por plano, isolamento, simulação de falha, observabilidade.
```
ESTADO: Core ~90% (falta RAG curado + deploy) · Atendimento ~80% (falta credencial InfoCap + Z-API) ·
Auxiliares ~50% (mecanismo pronto; biblioteca = C2) · Conectores ~70% (backend pronto; UI OAuth = C2) ·
Knowledge OS ~40% (infra pronta; conteúdo/evals = C1).
```
