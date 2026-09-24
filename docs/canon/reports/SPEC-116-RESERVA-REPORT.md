# SPEC-116-RESERVA · reserva cross-provider nos caminhos P0 (24/09/2026)

## EXECUTION CARD
```
OUTCOME ...... se o provedor do modelo principal cair (429 · 5xx · timeout · conexão · breaker aberto), os 4 caminhos
               P0 respondem pelo modelo de OUTRA empresa; erro nosso (400/contrato) nunca troca de modelo.
BASE ......... origin/main ccb2b0d · branch spec/116-reserva · builder único Opus 5.5 (economia: sem subagentes, sem web)
GATES ........ migration com APPLY/VERIFY/ROLLBACK + asserção · testes dirigidos · mutação 1× nos guardas novos
```

## Mapa (migration `backend/supabase/migrations/20260924_02_spec116_reserva_p0.sql` — escrita, aplicação pelo gerente)
| papel | primário | reserva |
|---|---|---|
| atendimento | openai/gpt-6-sol high | anthropic/claude-opus-5-5 (esforço padrão) |
| chat_principal | openai/gpt-6-sol medium | anthropic/claude-opus-5-5 (padrão) |
| portal_decisao | openai/gpt-6-sol medium | anthropic/claude-opus-5-5 (padrão) |
| dispatch | anthropic/claude-opus-5-5 | openai/gpt-6-sol high |

Os outros 21 papéis seguem sem reserva (📊 24/09, SELECT via MCP: 25/25 reservas nulas antes). A trava vigente
(`llm_papeis_so_modelo_governado`, 20260924_01) aceita as 4 linhas: os dois modelos são APPROVED, permitem `pii`, e
`high` está nos níveis do Sol. A asserção final aborta se ≠ 4 reservas ou se alguma não for cross-provider.

## O helper — `backend/app/factories/llm_factory.py::invocar_com_reserva(papel, mensagens, *, company_id, …)`
Resolve a rota → breaker do primário aberto → reserva direto · chama o primário → só se `motivo_de_reserva(exc)` não-nulo
(429/5xx/timeout/conexão) chama a reserva UMA vez com `metadata.motivo_reserva` (o `CostCallbackHandler` grava
`reserva_usada=true` + motivo) · 400/contrato sobe · rota sem reserva → o erro sobe (sem fallback calado).
Callsites: `webhook.py` (fase humana), `dispatch_watchdog._adaptive_reply`, `dispatch_router.o_cerebro_ja_sabe` (o `llm`
injetado dos testes continua valendo). Os três são **chamadas únicas de decisão, sem tools**, e nada com efeito roda antes
da chamada (só leitura do mapa de URA/fontes) — nada a repetir. Em `o_cerebro_ja_sabe` o `wait_for(20 s)` cobre primário
+ reserva: um primário que estoura 20 s não chega à reserva (a reserva cobre as falhas rápidas).

## Portal (`backend/portal_worker/modelo_do_portal.py`)
DEFEITO achado: `decidir` trocava para a reserva em QUALQUER falha (inclusive 400/404). Agora
`ModeloDoPortalIndisponivel.transitoria` (408/409/429/5xx, `httpx.TransportError`, timeout, conexão) é a única falha que
autoriza a reserva. Chat/atendimento: não reescrito (`nodes._invocar_o_modelo` já fazia a regra).

## Testes (saída real)
- `tests/test_spec116_reserva_p0.py` (19) — dispatch pela função de produção: 429/5xx/timeout/conexão → Sol high responde,
  UMA vez, ledger com motivo · 400 não troca · breaker aberto → primário 0 chamadas · controle sem reserva ·
  `o_cerebro_ja_sabe` · forma: 0 `papel="dispatch"` direto · chat: 5xx/timeout/conexão antes/depois da tool, breaker da
  OpenAI, histórico sanitizado (raciocínio do Sol não chega ao Opus) · resolver com o mapa · snapshot com banco fora.
- `tests/test_spec116_reserva_portal.py` (7) — 429/500/503/timeout/conexão → Opus decide uma vez; 400/404 não troca.
- `test_spec116_f3b_portal.py::test_erro_do_provedor_nao_vira_chamada_ao_mini` — premissa "rota sem reserva" agora explícita.
- Suítes relacionadas (f2 ×4, f3b portal/plataforma, conserto_unico, o_fio_do_modelo, model_policy,
  nenhum_modelo_fora_do_catalogo, f3a ×2, f4): **165 passed, 1 skipped, 1 failed** + **46 passed**.
  O 1 vermelho é `test_banco_fora_o_snapshot_ainda_traz_a_reserva` — **espera o snapshot regenerado** depois de aplicar.

## Mutações (1× cada, restauradas por cópia)
M1 helper aceita 400 → `test_dispatch_400…` VERMELHO · M2 helper sem breaker → `…breaker_aberto…` VERMELHO ·
M3 portal ignora `transitoria` → 400/404 VERMELHOS · M4 portal classifica timeout/conexão como não-transitório →
timeout/conexão VERMELHOS.

## Envs residuais
`rg DISPATCH_LLM_PROVIDER|DISPATCH_LLM_MODEL|ATLAS_PARSER_MODEL` em `backend/app`: 0 leitores (só comentários/descrições).
Tarefa do Founder S116.11: apagar as três do EasyPanel (smith-api e smith-worker).

## Depende do gerente
1) aplicar `20260924_02` + VERIFY · 2) `python scripts/gerar_snapshot_de_modelos.py --banco` (e a cópia do portal-worker,
se a imagem levar a própria) · 3) rodar `test_spec116_reserva_p0.py` de novo (o teste do snapshot fica verde).

## BLOCKED_BY_CREDIT
LIVE_FAILOVER_TEST: nenhuma chamada real a OpenAI/Anthropic (crédito). Provado só com dublê na borda.

## Desvio declarado
Sem juiz ‖ red team (economia de franquia, ordem do Founder). Prova = testes dirigidos + 4 mutações.
Nenhum motor paralelo: o helper usa a fábrica, o resolver, o breaker e o ledger existentes.
