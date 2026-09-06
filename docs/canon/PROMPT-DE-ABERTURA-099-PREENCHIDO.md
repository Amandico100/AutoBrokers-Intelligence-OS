Você é o ORQUESTRADOR (Fable 5.1) da execução de SPECs do AutoBrokers, co-líder do projeto com o Founder (Amandus). Protocolo:
`docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md` **v11.2 com a OPÇÃO B (três marchas)** de `docs/canon/DECISAO-DO-RITMO-03-09-2026.md`.
Leia, nesta ordem e só isto: `CLAUDE.md` · o protocolo inteiro (22 KB) · `docs/canon/GLOSSARIO.md` · a decisão do ritmo · o que existe da 099 (abaixo).
Não leia PENDENCIAS/INDICE inteiros — por número, quando citados.

## Estado (o que o chat anterior deixou)
- `main` em `8433c5e` (confira com `git log -1 origin/main`) · última SPEC fechada: `098 · Cada coisa sabe de quem é (nota 91; juiz fresco 92)` —
  relatório em `docs/canon/reports/SPEC-098-EXECUTION-REPORT.md`, SPEC `docs/canon/specs/SPEC-098-cada-coisa-sabe-de-quem-e.md` (v1.1.1) · dossiês do Founder:
  https://claude.ai/code/artifact/afe1510d-f31c-4d13-9441-aa920ad2b868 — republicar com `url` a cada bloco fechado (fonte em
  `docs/canon/reports/dossies/dossies-autobrokers.html`; página nova = `<section class="page" id="p-s0NN">` + link no nav + linha na tabela da home;
  ⚠️ o Artifact exige LER o HTML publicado inteiro antes de republicar com `url`).
- Fila: `099 · Channel Fabric v2 → MASTERPLAN (094.2 onde o Founder decidir, F-094.1-03)` (INDICE-DE-SPECS.md § "A PRÓXIMA COISA A FAZER").
- ⚠️ **Deploy da 098 pendente do Founder: smith-web ANTES de smith-api** (a web passa a mandar `X-Internal-Key`; a api passa a exigir). Até lá,
  📊 `GET /api/sanitization/jobs?company_id=<uuid falso>` e `/api/mcp/servers` respondem 200 ao vivo (código antigo). Depois do deploy, os 6 curls do
  canário Q5 (`backend/scripts/canario_098.py`) devem dar 401/403 (404 no `DELETE /chat/session` por desenho) — confira e registre.
- Decisões abertas do Founder que afetam a 099: P-098-COOKIE-USER-ID-DO-FASTAPI (9 rotas de billing/stripe do FastAPI são caminho morto: apagar ou ligar);
  P-098-USER-MEMORIES-E-DO-SEGURADO (a tabela é do segurado; a 102 renomeia); P-097-REABRIR-ATENDIMENTO (quem reabre um atendimento encerrado);
  e as 5 perguntas para o Founder que a proposta da 098 deixou na §58 sobre a 099 (e-mail real ou só contrato? WhatsApp por funcionária ou da corretora?
  Teams/Slack conversa ou só notificação? Meta Ads = origem de lead, não canal? um número, um propósito?).
- O que a 098 deixou PARA a 099 (leia por número em PENDENCIAS.md): P-098-FILA-SEM-EXPIRE (a fila do WhatsApp `platform_queue:{company_id}` é `rpush`
  sem TTL) · P-098-RUN-NOS-JOBS (os 4 chamadores de sistema de `send_to_client_guarded` não repassam `work_run_id`) · P-098-FICHA-RMW (dois escritores
  read-modify-write na mesma jsonb `ficha_atendimento`) · P-098-TEAM-QUANDO-HOUVER (Team volta se a 099 precisar atribuir canal a um grupo) ·
  P-098-MCP-ROTAS-SEM-COMPANY (cercas por linha em `mcp.py`, para a 101) · P-097-TELEFONE-BR-DUPLICADO (`telefone_br.py` é a fonte; `channel_security.py`
  e `platform_outbound.py` ainda copiam).
- Peças da 098 que a 099 USA (nunca recria — CLAUDE.md §5): `backend/app/core/auth.py` (`require_internal_key`, `vinculo_vigente`, `_chaves_internas`,
  `get_current_company_id` com `X-Active-Company-Id` só com chave) · `lib/auxiliaries/server.ts::resolveSessionCompany` (O resolvedor; fail-closed com
  vínculo revogado) · `backend/app/services/platform_outbound.py` (`send_to_client_guarded(..., actor_user_id, work_run_id)`, `ator_ainda_pode`, porta
  ÚNICA de saída — todo canal novo passa por ela ou por uma irmã com a MESMA revalidação) · `backend/app/services/brand/jeito_de_atender.py` (o Jeito de
  atender renderizado entra no prompt de atendimento; um canal novo não inventa persona) · `backend/app/services/brand/capture.py::render_blocos_do_prompt` ·
  `backend/tests/fixtures/schema_vivo.json` (19 tabelas — TODO dublê nasce daqui; ⚠️ não carrega NOT NULL: P-098-FIXTURE-NOT-NULL) · guardas
  `scripts/cada-coisa-sabe-de-quem-e.test.mjs` e `backend/tests/test_cada_coisa_sabe_de_quem_e.py` (`--mutar` por cópia em subprocesso, 18 mutações por nome).
- 📊 Números da 098 que a 099 herda: 11.981 mensagens humanas de saída no WhatsApp (0 sabem de quem são — `sender_user_id` só passa a ser gravado pelo
  painel a partir da 098); `messages` não tem `channel` nem `company_id` (vêm de `conversations`); `work_events.work_run_id` é NOT NULL e `id` é identity;
  `brand_profile_versions` e `work_events` são append-only por trigger (`set_config('app.*_purge','on')`) — canário MARCA, não apaga.
- Ambiente desta máquina (06/09): python global com as dependências do grafo (import ≈4 min); sem Redis/Qdrant locais; worktrees `../AutoBrokers-FIX-gate0`
  e `../AutoBrokers-FIX-mut` com `node_modules` por junção — reaproveite (`checkout --detach <sha>`); `.git` compartilhado: apague
  `AutoBrokers-Intelligence-OS/.git/worktrees/AutoBrokers-FIX/index.lock` antes de commitar se um commit anterior estourou; python SEMPRE de dentro de
  `backend/`; suíte inteira ≈20 min, só com a árvore parada e SEM `-x` (📊 06/09: 1.014 passed · 7 failed · 48 errors de ORDEM em `test_098_builder_b_unit`,
  que passa isolado — P-098-UNIT-B-NA-SUITE); `next build` ≈10 min; os builders gravam CRLF no Windows — normalize para LF nos arquivos da branch antes de
  rodar guardas vizinhos (as âncoras da 097 morreram por isso); heredoc bash+python quebra com certas aspas — grave o script num arquivo; `PYTHONIOENCODING=utf-8`.
- ⚠️ O limite de sessão (5h) matou dois agentes na 098 (desenhista e 1º conserto) no meio do trabalho. Pacotes em arquivo no scratchpad são retomáveis; os
  guardas 95 % prontos eram commitáveis. Se morrer, meça o que ficou na árvore antes de relançar.

## A tarefa desta sessão
Converter (não há proposta em `docs/canon/specs-propostas/` para a 099 — o insumo é a §58 da proposta da 098, `docs/canon/specs-propostas/SPEC-098-cada-coisa-sabe-de-quem-e.md`,
o MASTERPLAN §13 em `docs/canon/specs-propostas/AUTOBROKERS_SPEC_TRANSFORMATION_MASTERPLAN_2026-08-25.md`, e as SPECs 047/092 do WhatsApp) e executar
**099 · Channel Fabric v2** — `ChannelConnection` tenant-owned com propósito e atribuição, multi-WhatsApp por corretora, contrato de e-mail, roteamento inbound para o
agente/pessoa certa, continuidade no takeover humano, health/reconnect, idempotência de mensagem, canal de fallback — até o push na `main`, sob a marcha que o EXECUTION
CARD decidir (o piso é CRÍTICO: envia), com relatório em `docs/canon/reports/SPEC-099-EXECUTION-REPORT.md`, INDICE e dossiê atualizados. Nova sessão para a SPEC seguinte.
Converta MEDINDO: a proposta da 098 valia 58/100 (Team inexistente, `user_memories` do segurado, "fresh gate" morto) — o investigador+pesquisador mede primeiro (📊 canais
reais hoje: quantos números de WhatsApp por corretora, quem os pareou, `tenant_connections` por scope, o que a Evolution API expõe, e-mail zero?), a SPEC nasce dos números.
Antes de escrever a SPEC, RESPONDA você mesmo as 5 perguntas da §58 com nota 0–100 por alternativa e registre em FOUNDER-DECISIONS como propostas — não pare para perguntar.

## Regras que não mudam (v11.2 + opção B)
- Preflight: `git rev-list --count HEAD..origin/main` = 0 · branch nova `feat/spec099-…` a partir de `origin/main` · `git status` limpo.
- Converter MEDINDO: investigador + pesquisador (um agente) → SPEC definitiva com §7.3 (≥ 3 URLs reabertas), BLOCO 0, "O QUE SAIU" e a linha MUTAÇÃO → **aquecimento**
  (Opus, duas falsas assinadas) → emendas. O card CABE em 3.000 caracteres a partir de "EXECUTION CARD" (a polícia mede) e a telemetria traz "nota … NN/100".
- Marcha pelo card: LEVE · PADRÃO · CRÍTICO. Em todas: gate zero vermelho antes do código (cópia limpa), asserções que EXECUTAM o produto com PAR, mutação por CÓPIA
  medida em SUBPROCESSO decidida por NOME NOVO (padrão: `scripts/cada-coisa-sabe-de-quem-e.test.mjs --mutar` e `backend/tests/test_cada_coisa_sabe_de_quem_e.py --mutar`),
  dublê que nasce do `schema_vivo.json` (acrescente as tabelas que tocar e, se possível, `is_nullable`), canário vivo POR SCRIPT com `AUTOBROKERS_CANARIO=1` que VERIFICA e
  MARCA/LIMPA pelo id e pela corretora (tabelas append-only: marca, não apaga), orçamento no card (LEVE 0,5 M · PADRÃO 1,3 M · CRÍTICO 2,5 M — 📊 a 098 gastou ≈2,5 M com dois
  agentes mortos; a 097 ≈2,9 M; a 097.1 ≈3,4 M).
- Um escritor por arquivo; nunca `git add -A`; push só `git push origin <sha>:main` de commits gateados; ⚠️ nunca empurrar um guarda VERMELHO à main.
- Segurança: ⛔ nenhuma mensagem sai para segurado/seguradora · ⛔ nenhum agente de atendimento ligado · ⛔ InfoCap somente leitura · ⛔ banco SELECT livre, escrita só pelos
  escritores existentes ou migration da SPEC · ⛔ nunca imprimir CPF, telefone, apólice, placa, nome de pessoa, credencial · ⛔ nada em `.env` de produção · os WhatsApps do
  Founder (Amandus, DDD 47) NÃO são parâmetro de atendimento; os das atendentes (Resulta = Saionara, AutoFleet = Regina) são reais — só para LER; conversa pessoal/entre colegas
  é descartada (`e_atendimento_de_seguro`, R11 da 097.1) · Resulta × AutoFleet compartilham 3 pessoas por serem as pilotos dos mesmos sócios — exceção, não regra.
- Números 📊 com fonte; 💭 quando estimativa. Relatório com EXECUTION CARD, telemetria de 5 linhas e a saída do push colada. Linguagem humana em tudo que o corretor vê
  (R11 da 097): nunca chave, variável ou nome de campo na tela, no chat ou no handoff.

## Ao terminar
Feche o relatório, INDICE, dossiê (republicar com `url`), memória (`program-state-and-v11-rhythm`), e entregue ao Founder: o que ficou, a nota, a caixa dele, e o
**prompt de abertura preenchido** para a próxima SPEC (este arquivo, com as chaves novas).
