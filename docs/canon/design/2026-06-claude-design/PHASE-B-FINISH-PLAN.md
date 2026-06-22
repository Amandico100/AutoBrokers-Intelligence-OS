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

### Execução FB-1 — "Chat que conhece a corretora" + Conhecimento (o que te faz sentir o agente extraordinário)
1. **Seed Pack Global v1** (conhecimento curado do AutoBrokers: o que é Core/Even/Auxiliares, capacidades, releases/rollout, regras) — ingestão **master-only, idempotente, manual** (botão). *Sem dado sensível, sem cobertura.*
2. **Knowledge Readiness** (Global + Privado da corretora: nº docs/chunks/última indexação) — diagnóstico honesto, sem vazar tenant.
3. **Política de modelo** do Core: subir de `gpt-4o-mini` para um perfil "inteligência avançada" (com aviso de custo) — para o raciocínio sênior que você quer.
4. *(reuso)* A consciência de auxiliares no chat **já existe** (42A7); FB-1 amplia para "estado da corretora" (prontidão/agentes) **reusando** o mesmo mecanismo — sem tool paralela.

### Execução FB-2 — Operação, governança e higiene (deixar o Portal Admin "para humano")
5. **Provisionamento canônico + reconciliação** (DRY-RUN master): toda nova corretora nasce com Core+Even canônicos; empresas existentes (Resulta/Rafael) reconciliadas com snapshot/rollback (sem apagar).
6. **Higiene de dados de teste** (os "TESTE Runtime Smith Agent" da Rafael): lista master "Dados legados", arquivar com confirmação (nunca apagar/auto).
7. **Diagnóstico de Runtime** (master, por Core/Even): provider, modelo, saldo, LLM, RAG, memória, último erro — sem segredo. (Para de adivinhar.)
8. **FinOps real** por agente (uso real ou "indisponível" honesto; sem repasse ainda).
9. **Aprovadores** (tabela canônica `company_approvers` + RLS) — base de governança (sem ligar ação externa).

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
