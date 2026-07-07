# ROADMAP DE EXECUÇÃO — SPECs, chats e ordem (2026-07-07)

Mapa mestre: o que existe, quem executa, em que chat, em que ordem. Atualizar conforme avança.

## Estado das SPECs

| SPEC | O quê | Estado | Onde executar |
|------|-------|--------|---------------|
| 016 | Policy Intelligence Core (InfoCap) | ✅ Base pronta | — |
| 017 | Atendente WhatsApp (Smith) | ✅ Produção | — |
| 019 | Rotinas/auxiliares (galeria, executor, knowledge) | ✅ Feito | — |
| 020 | Motor de portais (F3) + Camada 2 (LLM-visão) | ✅ **Acionamento vidros estável (para nos 80%)**. Falta: teste WhatsApp ponta a ponta + passo pós-80% (aprovar→enviar) quando o founder liberar o gate | **Este chat** (fechar) |
| 021 F4 | Camada 3 — memórias/aprendizado (learning_notes) | 📝 Prompt de chat novo pronto (`PROMPT-NOVO-CHAT-SPEC021-CAMADA3.md`) | **Chat novo** |
| 021 F5 | Metering + Firecrawl + model picker | 📝 Na SPEC-021, depois da F4 | Chat novo (junto da F4) |
| 022 | Reorg IA Seguradoras-cêntrica (UI) | 📝 Doc criado (`specs/SPEC-022-...md`) | Comigo aqui **ou** chat novo (menor risco) |
| 023 | **Portais autenticados (login/CAPTCHA/2FA HITL) + Cobrança** | 📝 **Criada agora** (`specs/SPEC-023-...md` + `PROMPT-NOVO-CHAT-SPEC023-...md`) | **Chat novo** |

## Ordem recomendada

1. **AGORA (este chat)** — Teste WhatsApp do acionamento vidros (com o swap InfoCap → AutoFleet). Fecha a
   SPEC-020 na prática. Baixo esforço, valida tudo que foi construído.
2. **SPEC-023 (portais autenticados + Cobrança)** — chat novo. É o **maior valor de negócio** que você quer
   (auxiliar de cobrança) e depende só do motor, que já está pronto e robusto.
3. **SPEC-021 Camada 3 (aprendizado)** — chat novo. Deixa o motor mais esperto ao longo do tempo (cada
   decisão nova vira caminho rápido). Pode ir depois ou em paralelo à 023.
4. **SPEC-022 (reorg UI)** — comigo aqui ou chat novo. É organização de interface, menor risco; encaixa
   quando quiser, não bloqueia nada.

## Chat novo vs. continuar aqui

- **Chat novo**: SPEC-023 e SPEC-021 (trabalho grande, contexto próprio, cada um com prompt pronto).
- **Aqui ou chat novo**: SPEC-022 (menor).
- **Aqui**: fechar o teste do vidros (SPEC-020).

## Prompts prontos para colar em chat novo
- Camada 3 / memórias: `docs/canon/PROMPT-NOVO-CHAT-SPEC021-CAMADA3.md`
- Portais + cobrança: `docs/canon/PROMPT-NOVO-CHAT-SPEC023-PORTAIS-COBRANCA.md`
- Reorg: `docs/canon/specs/SPEC-022-reorg-seguradoras-centrica.md` (se for chat novo, cole a SPEC + peça o plano antes)

## Quem executa
Sempre **Opus 4.8** como executor (este assistente), Fable audita depois. Um chat por frente grande, pra o
contexto não estourar. Você abre o chat, cola o prompt correspondente, e o executor reporta o entendimento
antes de mexer em código.
