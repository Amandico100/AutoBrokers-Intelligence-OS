# RELATÓRIO — Programa Multicálculo · passo 0.5 · registro + o link `/r/` + o conhecimento global anônimo

**04/10/2026** · branch `programa-mc/passo-0.5` · commit inicial `e7f76df` (= `origin/main`, 📊 `git rev-list --count HEAD..origin/main` → 0) ·
executor/gerente Opus 5.5 · rito CRÍTICO pelo piso (D-MC-48) · plano: [`programa-multicalculo/PLANO-MESTRE-MULTICALCULO.md`](../programa-multicalculo/PLANO-MESTRE-MULTICALCULO.md)

## EXECUTION CARD

```text
OUTCOME .............. (1) o canon passa a ter o plano v2.4, as decisões D-MC-08…50 e a fila nova; (2) o cliente do corretor abre o
                       link /r/<token> do relatório sem cair no login, com o CSP da própria página; (3) o link sai COM endereço em
                       produção; (4) o conhecimento destilado das conversas continua GLOBAL e nada identificável entra nele
RISCO ................ 6 — alcance corretora/segurado 3 · reversibilidade 2 · frequência 1
SUPERFÍCIE ........... 2 — middleware (quem precisa de sessão) + o porteiro do dado global + o endereço do link
PISO APLICADO ........ CRÍTICO (§3.2: sessão; dado que atravessa corretoras) — D-MC-48
NÍVEL ................ CRÍTICO · gerente Opus 5.5 · builders Opus 5.5 · juiz Opus 5.5 ‖ red team Opus 5.5 · confirmação
O FIO ................ middleware.ts (publicPrefixes) → app/r/[token]/route.ts → /api/artifacts/shared/{token}; report_tool/api.artifacts
                       → base_publica_do_app → /r/<token>; attendance_distiller._save_playbook_draft_sync → curadoria_cartas.
                       anonimizar_para_o_global → insert conduct_playbooks
PARALELISMO REAL ..... builder A (middleware.ts, scripts/, package.json) ‖ builder B (backend/) — arquivos disjuntos
UNIDADES ............. U1 registro no canon · U2 /r/ público · U3 endereço do link · U4 porteiro do global (P-E0018-14)
COESÃO ............... U2 e U3 são o mesmo link, mas arquivos de camadas diferentes (Next × FastAPI) — fatias separadas
TIME ................. 2 builders ‖ → juiz ‖ red team → conserto único (2 builders ‖) → confirmação. Escalação: nenhuma
REFERÊNCIA ........... interna: CLAUDE.md §9.1/§9.3/§9.4 e `lib/public-url.ts` (validação de origem); externa: Next.js middleware
                       https://nextjs.org/docs/app/building-your-application/routing/middleware · CSP frame-ancestors
                       https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Security-Policy/frame-ancestors ·
                       Referrer-Policy https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Referrer-Policy
GATES ................ testes novos verdes + mutação vermelha + controle; §9.1 (rotas montam + servidor responde); 18/18 playbooks
                       reais gravados íntegros; bateria triada contra a linha de base
O ELO ................ "o cliente abre o link" = middleware libera E a rota serve E o link tem endereço — medidos os três
FAIXA DE RELÓGIO ..... 💭 2–3 h · real ver telemetria
```

## 1. O que mudou

| unidade | o que mudou | prova |
|---|---|---|
| U1 | plano v2.4 em `programa-multicalculo/` (cópia fiel, 📊 sha256 igual ao anexo); D-MC-08…50 em FOUNDER-DECISIONS (tomadas × propostas); fila nova em EXECUTION-MASTER-PLAN, ESTADO-DAS-SPECS e INDICE-DE-SPECS; D-E002-01/02/07 e a ordem da D-FILA-01 marcadas como substituídas; mapa de testes recontado (📊 95 pendentes: A 48 · B 0 · C 47) | `491de31` |
| U2 | `/r/` em `publicPrefixes`; o middleware não sobrescreve CSP nem Referrer-Policy em `/r/` (a rota declara `default-src 'none'`, `frame-ancestors 'none'`, `no-referrer`) | `4ecd829` `ef27187` `29f23c4` · `npm run test:link-do-relatorio` 24/24 |
| U3 | `base_publica_do_app()`: PUBLIC_APP_URL > NEXT_PUBLIC_APP_URL > SMITH_WEB_URL > FRONTEND_URL, só http/https, recusa localhost/host interno, fica a origem. 📊 o `smith-api` de produção só tem as duas últimas → o link saía VAZIO | `54d7c42` `5e22750` `d7a20c7` · 16 PASS |
| U4 | porteiro `anonimizar_para_o_global` (estende `curadoria_cartas`, reusa `templatize` e `PADROES_PII`) no único escritor da `conduct_playbooks`: corretora por variante (inteiro, núcleo, handle/domínio), palavra genérica nunca é marca, nome de pessoa em contexto (587 prenomes), placa/telefone/CPF que os motores soltavam, números públicos intactos, lista de corretoras sempre relida (senão não grava), grupo recusado só volta com material novo (marcador no Redis). Tabela continua global (D-MC-39) | `fb1656a`…`17115aa`, `d0b9928` `8f4dcc9` `e3fdbcf` `196772e` `966c6df` `00d53b0` · 96/0 · 📊 18/18 playbooks reais gravados, 0 campo alterado |

📊 Medições só leitura em produção (04/10): `artifact_shares` = **0 linhas** (nenhum relatório foi compartilhado até hoje — o link nunca chegou a cliente);
`conduct_playbooks` = 18 linhas, **0** com CPF, e-mail, telefone, placa ou nome de corretora. Inventário de trabalhos presos (para a 129-A):
`intelligence.detect_signals` queued 20 (desde 28/07) · `intelligence.measure_outcomes` queued 1 · `claims.shadow` running 3 · `metric.proposal`
waiting_approval 2 · `acionamento.seguradora` waiting_input 1 · `retry_scheduled` 0.

## 2. Julgamento

| peça | veredito | o que achou |
|---|---|---|
| juiz | PASS com pendências · **84** | laço de custo do grupo recusado; o card prometia mais do que o porteiro entregava em nomes; placa minúscula; leitores de endereço divergentes |
| red team | **QUEBREI · 62** | Q1 middleware apagava o CSP da rota; Q2 corretora em domínio/handle e nome que começa com seguradora; Q3 nome de pessoa; Q4 corretora de nome genérico barrava todo `ramo=auto` |
| conserto único | 2 builders ‖ | tudo fechado, inclusive as pendências baratas; limites declarados no código |
| confirmação (§6.1) | NÃO CONFIRMA · **80** | o conserto não criou defeito (o `templatize` das mensagens: 18/18 frases idênticas ao antes); Q1, Q3, Q4 fechados; **Q2 aberto em parte** — corretora de nome todo genérico ("Porto Real") vazava na forma curta e no domínio colado |
| conserto pós-confirmação | prova mecânica (a 3ª rodada de juiz seria escalação, §6.1) | a sonda da própria confirmação: 📊 **6 VAZOU → 0**; teste 112/0; mutações M1/M1b/M2/M3 vermelhas; 18/18 playbooks reais íntegros (`4991925` `9740db5` `ec1f647` `3a3f78f` `13f5905`) |

## 3. Testes (saída real)

- `npm run test:link-do-relatorio` → 24 ok, 0 falhas · mutação (`/NUNCA/`) → 3 falhas · `npm run test:rotas-montam` → 307 rotas, A TABELA MONTA
- §9.1: `next build` + `next start` reais num app mínimo com os mesmos `middleware.ts`/`route.ts`, backend falso local → `GET /r/<token>` 200 com `content-security-policy: default-src 'none'; … frame-ancestors 'none'` e `referrer-policy: no-referrer`; `/dashboard` → 307 `/login`. O build completo do repo nesta máquina passa de 44 min e o worker de tipos cai (P-MC05-04)
- `test_o_conhecimento_global_sai_anonimo.py` 96/0 (12 mutações vermelhas) · `test_o_link_do_relatorio_tem_endereco.py` 16/0 · onda3 25/0 · lapidador 13/0 · onda5 13/0 · weaver 27/0 · `test_nenhum_nome_de_gente_em_dado_global` verde
- bateria: ver §4

## 4. Confirmação e bateria

Confirmação: ver §2. **Bateria** (worktree limpo `C:\wt05`, HEAD `00d53b0`, `pytest tests -q -p no:cacheprovider`): 📊 **47 failed · 5059 passed ·
8 skipped · 31 xfailed · 1 xpassed em 1:31:26**. Triagem nominal contra `BATERIA-LINHA-DE-BASE.txt` (28): 28 iguais · 0 sumiram · 19 novas →
isoladas no HEAD `13f5905`: **10 passam** (ordem/carga) · **2 XPASS(strict)** — o `onda3_distiller` e o `lapidador` estavam na quarentena do
meta-guarda e o conserto os fez passar → tirados da quarentena (`d8849df`, 2 passed) · **7 falham iguais no commit base `e7f76df`** (📊 7 failed,
4 passed) = pré-existentes, de ambiente do worktree limpo (Redis local, `node_modules`) ou vindas da 126/127 → **0 regressões**. Linha de base atualizada.

## 5. O que ficou fora (pendências P-MC05-*)

Ver `PENDENCIAS.md`, seção P-MC05.

## 6. Declaração

Nenhum motor paralelo: o porteiro estende `curadoria_cartas` e reusa `templatize`/`PADROES_PII`; o endereço é uma função na peça de artefatos.
Nenhuma migration. Nenhum segredo em arquivo versionado (📊 `grep` por chaves e senhas nos arquivos commitados → 0). Canário: não se aplica
(nenhum envio); a prova no ar é o `curl` do Founder depois do Implantar.

## 7. Telemetria — `python backend/scripts/medir_execucao_claude_code.py --sessao atual`

```text
EXECUTOR (sessão inteira, inclui a validação do plano de 03/10)  830 min  turnos 100  pico 579k  ctx 40.7M  saída 190k  US$ 34.47  opus-5-5
passo 0.5: builders A 77 min US$ 2.98 · B 71 min US$ 6.40 · juiz 9 min US$ 2.28 · red team 13 min US$ 3.60 · conserto F-A 9 min US$ 1.04 ·
  conserto F-B 40 min US$ 9.94 · confirmação 11 min US$ 1.18 · conserto final 9 min US$ 1.84 (todos opus-5-5)
TOTAL da sessão: 14 agentes · 998 turnos · ctx 181.5M · US$ 121.49 (equivalente de API do Claude Code — NÃO é a verba do produto)
verba de API do PRODUTO (US$ 4,00 do Founder): US$ 0,00 gasto — nenhuma chamada de modelo do produto neste passo
achados por mecanismo: executor 1 (link sem endereço em produção, exclusivo) · juiz 4 pendências · red team 4 blockers (Q1–Q4, exclusivos) ·
  confirmação 1 blocker residual (Q2 parcial, exclusivo) · bateria 2 XPASS(strict)
rodadas da bateria: 1 (+ isolamento das 19 novas no HEAD e no commit base)
nota do executor: 90 (critério: os 4 blockers do red team e o residual da confirmação fechados com prova; §9.1 com app mínimo, não o repo inteiro)
nota do juiz: 84 · red team 62 · confirmação 80 (antes do conserto final, que fechou o residual com a sonda dela: 6 → 0)
⚠️ pico do executor 579k > teto 300k — a sessão carregou a validação inteira do plano; a 129-A vai para chat novo
```
