# Plano de Fechamento da Fase B — finito, organizado, com linha de chegada

> **Por que parecia não acabar:** cada rodada de "Fase B" virou um prompt de 5 blocos + 30 testes (≈ 5 batches), e eu fatiei. **Solução:** congelar o escopo abaixo. Nada de "mais Fase B" depois disto. São **2 execuções focadas** restantes + aceite. Esta é a fonte da verdade do que falta.
> **Data:** 2026-06-22 · **Base:** `a79aa46` + esta limpeza de UX.

## ✅ JÁ PRONTO (não mexer mais)
- Studio (empresa-plataforma) + **AutoBrokers Global** + **Even Global** (Source Agents).
- **Releases imutáveis** (SHA-256, secret-scan) + **rollout/rollback atômico** Studio→corretora (canary testado ao vivo).
- **Taxonomia** Source/Tenant; **Auxiliares com release** + lifecycle isolado por tenant.
- **Chat Principal inteligente** (P0): Core raciocina + usa conhecimento geral + RAG complementa (não limita); Even evidence-first. ⏳ *aguardando seu aceite: "capital da Itália" → "Roma".*
- **Editor global real** no Blueprint Center (construtor completo do Smith no Source Agent).
- **Proteção de instância**: Core/Even na seção canônica; Even visível mesmo inativa; sem editor técnico errado.
- **(esta limpeza)** Auxiliares com **caminho único** (fim da Galeria duplicada); empty-state e rótulos claros.

## 🎯 O QUE FALTA — exatamente 2 execuções (sem novos blocos depois)

### Execução FB-1 — inteligência do Chat Principal ✅ FEITO (commit 6c5cb8a)
1. ✅ **Modelo mais forte para o Core** (`gpt-4o`, temporário, configurável via `CORE_CHAT_MODEL`; Even/Auxiliares mantêm o seu). Não engessa — só sobe o teto.
2. ✅ **Knowledge Readiness** já existe (TA2-C: `/api/dashboard/knowledge` + tela Conhecimento) — sem página nova.
3. ✅ **Consciência de auxiliares no chat** já existe (42A7) — não duplicar.
4. ↪️ **Seed Pack Global / RAG robusto: adiado de propósito** (decisão do Founder) para a fase de evolução de cada agente — é conteúdo/poder, não infra.

### Execução FB-2 — SIMPLIFICAR o Portal Admin + operação/governança (estilo Smith, "para humano")
0. **SIMPLIFICAÇÃO DA NAVEGAÇÃO (prioridade do Founder):** menos camadas e "página que leva a página"; organizar no **sidebar** como o Smith era; menos termos de dev. Auditar e **enxugar**, não acrescentar.
5. **Reconciliação canônica** (DRY-RUN master): nova corretora nasce com Core+Even; Resulta/Rafael reconciliadas com snapshot/rollback (inclui normalizar **"SERGIO" → "Even"** mantendo role=attendance; sem apagar).
6. **Higiene de dados de teste** (os "TESTE Runtime Smith Agent" da Rafael): lista master "Dados legados", arquivar com confirmação.
7. **Diagnóstico de Runtime** (master, por Core/Even): provider, modelo, saldo, LLM, RAG, memória, último erro — sem segredo.
8. **FinOps real** por agente (uso real ou "indisponível" honesto; sem repasse ainda).
9. **Aprovadores** (`company_approvers` + RLS) — base de governança (sem ligar ação externa).

## 🚫 NÃO entra na Fase B (é Fase C / trilhas externas)
Capability Registry, Composio/Nango, Firecrawl/Notion/Drive/InfoCap/Quiver, Browserbase/Portais reais, Z-API/WhatsApp real. **Só depois** da Fase B encerrada.

## Linha de chegada (aceite da Fase B)
```
[ ] Chat: "capital da Itália" → "Roma" (P0 — você testa)
[ ] Chat: "quais auxiliares eu tenho / minha corretora está pronta?" → responde do estado real (FB-1)
[ ] Seed Pack Global instalado + readiness honesto (FB-1)
[ ] Nova corretora nasce com Core+Even; Resulta/Rafael reconciliadas (FB-2)
[ ] Diagnóstico de Runtime visível; FinOps real; Aprovadores com RLS (FB-2)
[ ] Portal Admin sem duplicação, navegável por humano
→ FASE B ENCERRADA → Fase C (conectores)
```

Cada execução vem com testes + tsc=0 + build verde + commit. **Depois de FB-1 e FB-2, a Fase B é declarada encerrada e não reabre.**
