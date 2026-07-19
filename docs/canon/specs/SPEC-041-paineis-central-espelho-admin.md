# SPEC-041 — Painéis da Central no Portal Admin (Espelho, Memórias, Replay, Aprovação)

> Aprovada pelo founder em 19/07/2026 ("quero executar já"). Executada pelo
> chat líder na sequência das 5 ondas da SPEC-040. Frontend Next.js do /admin
> (elementos nativos, tokens SPEC-036: #06080C/#0B0F15/#161D28, Geist,
> azul #7FB7E8, dourado #E2A94F, verde #43C08C, vermelho #E06B6B).

## Por quê

As APIs das 5 ondas existem e estão em produção, mas o founder só as acessa
por endpoint. Estes painéis transformam a inteligência em superfície visual e
dão o fluxo de APROVAÇÃO DE 1 CLIQUE (cards e playbooks) — o elo humano do
ciclo de auto-evolução.

## Entregas

1. **Página nova `/admin/espelho` — Espelho de Atendimento (centro de comando):**
   - Resumo vivo: sessões capturadas/destiladas, baseline humano interno
     (global e por corretora — NUNCA exposto à corretora), cards por status.
   - **Fila de aprovação de knowledge cards** (pending_review): texto,
     categoria/ramo/seguradora, checagem de PII visível; botões APROVAR
     (publica no RAG global na hora) e REJEITAR.
   - **Playbooks de conduta**: lista com status/versão/modelo; expandir mostra
     o conteúdo (objetivo, ficha de coleta, frases); DRAFT tem botão
     "Ativar (gate)" — roda o gate completo da Onda 4 e mostra o veredito do
     juiz; grupo com versão anterior tem "Rollback".
   - **Replay de atendimento**: sessões recentes (serviço/nota/corretora) →
     clique abre a timeline MASCARADA + resumo destilado.
   - **Contribuição por corretora** (efeito rede): sessões de URA + Parte 1
     capturadas/destiladas por corretora.
   - Botão "Rodar destilação agora" (POST /espelho/run) p/ verificação.
2. **Central de Agentes (`/admin/central-agentes`)**: cada card de agente ganha
   a MEMÓRIA (blocos do agent_memories — "o que o agente sabe"), colapsável.
3. **Acionamentos (`/admin/acionamentos`)**: seção "Histórico (replay)" — os
   acionamentos espelhados persistentes; clique abre a timeline + scorecard.
4. **Nav**: item "Espelho de Atendimento" no menu master admin.
5. **Backend de apoio**: GET `/api/admin/atlas/espelho/sessoes` (lista de
   sessões p/ o replay do painel).

## Regras

- Proxy existente `app/api/admin/atlas/[...path]` (GET+POST) — sem rota nova.
- Elementos NATIVOS no /admin (Radix com portal renderiza fora do tema).
- `npx tsc --noEmit` antes do commit; deploy smith-web + smoke `GET /` = 200.
- Nada de dado pessoal de segurado nos painéis (replay do atendimento é
  MASCARADO por construção — o cru fica no cofre).
