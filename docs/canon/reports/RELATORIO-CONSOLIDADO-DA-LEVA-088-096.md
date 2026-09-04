# RELATÓRIO CONSOLIDADO — a leva 088 → 096, sob um orquestrador e o protocolo v11/v11.1

> **Para quem lê só isto:** o que cada SPEC entregou, o número medido, a nota, o tempo, o que ficou
> pendente e o que o Founder precisa fazer. Os relatórios por SPEC continuam em `docs/canon/reports/`
> e valem como fonte; este é o índice com veredito. **Atualizado em 03/09/2026 ~21:10, ao pausar o protocolo para a decisão do ritmo.**
>
> Orquestrador: Fable 5.1 · subagentes: Opus 5 · início da leva: 02/09/2026 22:40 · árvore `AutoBrokers-FIX`

---

## 0. O PLACAR

| SPEC | o que entrega | nível | faixa → realizado | nota | estado | deploy |
|---|---|---|---|---|---|---|
| **PROTOCOLO v10 → v11** | um orquestrador, dieta de pacote, EXECUTION CARD, painel julga CÓDIGO, referência §7.3, guarda com polícia | — | 📊 ~2h | v10 auditada em **72/100** | ✅ 03/09 | docs |
| **088** A Central de Agentes diz a verdade (v2) | 18 trabalhadores com fonte de produção, 5 estados honestos, cache, Central nova | PADRÃO | 6–9h → 📊 **3h35** | **90** | ✅ push 03/09 02:28 | smith-api + smith-web |
| **091** Protocol/Process Factory | — | — | — | — | **ABSORVIDA** pela v11 (INDICE 03/09) | — |
| **093-B** O sinistro deixa rastro | sombra `claims.shadow` no Work OS, 10 eventos sem texto, digest de variantes, Central, admin | CRÍTICO | 8–13h → 📊 **7h15** | **88** | ✅ push 03/09 09:5x | smith-api + smith-web |
| **PROTOCOLO v11 → v11.1** | lente do DADO · pares mínimos · conserto salvo completo | — | 📊 20 min | — | ✅ push 03/09 | docs |
| **094** O Pulso 360 não pertence à InfoCap | censo InfoCap, CBIM, port/adapter, registry, Evidence Pack, tool, Artifact, canário ×3 | CRÍTICO | 14–18h → ≈9h em 3 janelas | **84** | ✅ push 03/09 ~21:00 | smith-api + APLICAR a migration de seed |
| **094.1** A fábrica de relatórios | convertida em 03/09 (propor métrica com Approval · 5 relatórios obrigatórios · SUSEP × carteira · protocolo COMO-NASCE-UM-RELATORIO) | CRÍTICO | 10–14h | — | **aguarda a decisão do ritmo** | — |
| **095** Artifact & Delivery Hub | proposta 9 | | | | fila | |
| **096** Chat runtime / interaction shell | proposta 10 | | | | fila | |
| **097 · 098** | propostas + research packs chegaram em 03/09 | | | | fila | |

📊 Todas as SPECs fechadas: `git rev-list --count origin/main..HEAD` = 0 no fim de cada uma; saída do `push` colada
no relatório de cada uma.

---

## 1. O QUE MUDOU NO MÉTODO — e o que isso custou e rendeu

**Antes (v10):** 40,6 KB de protocolo, 13 documentos de bootstrap (📊 864 KB / ≈220 mil tokens por agente),
um chat por SPEC, painel de juízes que rodou em 2 de 6 SPECs porque o pacote não carregava o protocolo.

**Depois (v11, 03/09):** 22 KB, um orquestrador que converte E executa, pacotes-modelo por papel, e um
guarda (`backend/tests/test_o_protocolo_tem_policia.py`, 42 ok) que reprova relatório sem EXECUTION CARD,
SPEC sem estado da arte e pacote sem protocolo.

📊 **O que as duas primeiras execuções mediram e a v11.1 absorveu:**

```
                              088 (PADRÃO)         093-B (CRÍTICO)
faixa declarada / realizada   6–9h / 3h35          8–13h / 7h15
painel                        3 lentes             4 lentes + red team
blockers únicos do painel     5                    7
conserto criou defeito?       não                  SIM — pego pelo juiz de confirmação (recall −9,5%)
auditoria externa             —                    2 blockers que NENHUMA das 5 frentes viu (só no DADO)
defeitos que o painel não viu 3 (bateria, orquestrador, builder)   2 (guarda do repo, orquestrador)
```

**Lição que virou regra:** quem julga o CÓDIGO aprova um dataset errado. Na 093-B, a única frente que
reconstruiu o outcome sobre o acervo real achou que a "variante de processo" era um histograma de
mensagens da atendente. A v11.1 põe essa lente no painel quando o outcome é número ou dataset.

---

## 2. SPEC-088 — A Central de Agentes diz a verdade · nota 90

**Entregou:** `AGENT_TASKS` com 18 trabalhadores, cada um com fonte de PRODUÇÃO (não só pulso), cinco
estados (SAUDÁVEL · PULSA SEM PRODUZIR · DESLIGADO · PARADO · NÃO MEDIDO), classificador
`central_de_agentes.py`, cache Redis 60 s, rota admin, Central redesenhada por grupos, 10 serviços com
`beat()` movido para onde o trabalho acontece. 📊 Guarda 509 ok; suíte 921/6 → conserto → verde.
**Ficou:** 9 pendências P-088-* (cadência do Tecelão 💭, três cards ⚪ que só se provam com Redis vivo,
harness de mutação que vaza). Relatório: `SPEC-088-EXECUTION-REPORT.md`.

## 3. SPEC-093-B — O sinistro deixa rastro · nota 88

**Entregou:** toda conversa que fala de sinistro vira um Work Run `claims.shadow` (sem fila, idempotente
por conversa), 10 tipos de evento sem texto livre (vocabulário único lido por Python e Next, sha256 igual
nos dois), gestos do painel e do celular como eventos, PDF do boletim como evento, digest diário em
variantes de ATIVIDADES (Celonis), sinais no trilho de inteligência **excluídos do briefing**, trabalhador
na Central, admin read-only. **Zero migration.** 📊 Guarda 249 ok · 934 passed na suíte · acionamento byte a
byte igual à `main`. Detector regex: 24 frases fixadas em pares, 0/14 falsos positivos.
**O laço:** painel 4 lentes + red team (7 blockers) → conserto → juiz de confirmação (1 defeito de recall
criado pelo conserto, consertado) → auditoria externa FAIL 71 (documento em PDF sem evento: 40,8% dos
arquivos de sinistro; variante = contagem de mensagens) → conserto → 249 ok.
**Ficou:** 24 pendências P-093B-* — as materiais: RAMO/SEGURADORA nunca preenchidos (variante degenera em
corretora × sequência), ECO do `humano_respondeu`, BUFFER de 8 s que pode perder o `fileName`, TELA da
atendente, LGPD com jurista, backfill de 2.187 sessões (decisão do Founder). Relatório:
`SPEC-093-B-EXECUTION-REPORT.md`.

## 4. SPEC-094 — O Pulso 360 não pertence à InfoCap · nota 84

**Conversão (03/09, ~1h30):** investigador + 6 referências reabertas + aquecimento (nota 74, 16 perguntas
medidas, 15 emendas aplicadas). Achados que mudaram a SPEC: não há carteira no banco (a 081 é 100%
read-through); o Intelligence Fabric já tem Finding/Evidence/Briefing e tem leis (`domain` derivado,
evidência obrigatória); o resolver por conexão já existe em `infocap_connector.py`; a credencial da InfoCap
não existe nesta máquina fora de `tenant_connections`; um nome de produtor real está num teste versionado.
**Execução (03/09, ≈9h em 3 janelas, ≈3,0 M tokens):** censo da CorpAPI pelas 3 conexões (86 GET; 18 rotas "negadas" não existem; `/sinistros`
existe com 5.729 registros; `val_r = val_c × per_r/100` provado; **P1: Amandus e Resulta são a mesma conta**); ELO (as tools da 081 devolvem
bloco citável); CBIM · port · adapter sobre o resolver existente · manifesto fail-closed · registry com 16 métricas versionadas e base temporal ·
Evidence Pack · tool `executive_intelligence` · template `executive.pulse360` + migration de seed · provider de referência. Painel v11.2 (2 lentes
+ red team: 12 blockers) → conserto → **juiz fresco com canário VIVO: FAIL 62 — a tool não rodava no grafo** (fakes que respondiam a `await`
esconderam isso de 366 asserções) → 2ª rodada → guarda 284 ok · canário 115 · suíte 933/6 (os 6 passam isolados). 📊 Canário vivo: Resulta
972 apólices · R$ 1.472.165,72 · cobertura 87%; AutoFleet 2.300 · R$ 1.746.002,17; Amandus recusada em 1,1 s; 2 Artifacts publicados.
**Ficou:** aplicar a seed (🧑), F-094-07 (🧑), 10 GET/≈80 s por pergunta, um Artifact por pergunta não-cacheada, mapa de produtor vazio,
`/producao` com parâmetro errado no conector de atendimento (P-094-PRODUCAO-500). Relatório: `SPEC-094-EXECUTION-REPORT.md`.

## 5. 094.1 convertida · 095, 096, 097, 098 na fila · protocolo PAUSADO

Ver `DECISAO-DO-RITMO-03-09-2026.md`: três sugestões com nota (A 78 · **B 88** · C 72; continuar como está 45). Nenhuma SPEC nova começa antes da decisão.

---

## 6. 🧑 O QUE O FOUNDER PRECISA FAZER

```
1. Implantar smith-api e smith-web (088 + 093-B + 094 estão na main) e APLICAR `backend/supabase/migrations/20260903_01_spec094_seed_template_pulse360.sql`
6. Decidir F-094-07 (Amandus = Resulta na CorpAPI), F-094-08 (InfoCap → Agger/Quiver), F-094-09 (escrita no InfoCap), F-094-10 (WhatsApp 01/10)
7. Escolher o RITMO (A · B · C) em DECISAO-DO-RITMO-03-09-2026.md
2. Rotacionar as chaves coladas no chat de 03/09 (Supabase service role, OpenAI, Anthropic, Twilio, CORP_INFOCAP_*)
3. Decidir: backfill das 2.187 sessões históricas com sinistro (F-093B-04) · handoff tool ligada (F-093B-05)
4. Decidir: nome de produtor no HISTÓRICO do git (F-094-05)
5. Piloto (≈ 08/09): a sombra grava desde o deploy com os agentes desligados; em 14 dias medir sombras × sessões com `sinistro`
```

## 7. Riscos remanescentes da leva
- Harness de mutação: `test_todos_os_guardas_script_rodam.py` deixa arquivo mutado quando um guarda estoura o tempo
  (P-088-MUT / P-093B-HARNESS) — a suíte inteira só é confiável com árvore parada e o harness restaura.
- Este ambiente não tem os requirements do backend (P-093B-REQS): ganchos que importam `app.api.webhook` só rodam por casca; no contêiner rodam.
- Nenhum motor paralelo foi criado em nenhuma SPEC da leva (declaração repetida em cada relatório).
