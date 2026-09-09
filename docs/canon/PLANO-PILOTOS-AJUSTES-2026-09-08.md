# PLANO DE AJUSTES DOS PILOTOS — véspera dos atendimentos reais (08/09/2026)

> Onde o Founder confere o que foi prometido, o que foi feito e o que ficou. Nasceu da
> auditoria de 08/09/2026 (seis frentes read-only sobre `cffaa0e`) e da decisão do Founder
> de executar o essencial **sem o protocolo AAA** por limite de tokens (14% do pacote
> semanal), com builders Opus por unidade e o orquestrador como juiz. Página do Founder:
> https://claude.ai/code/artifact/defe331c-9399-4584-9d1c-2126a527cea0#duvidas

## 0. Estado medido antes de começar (📊 08/09/2026, 20h–22h)

- `main` = `cffaa0e` (07/09); impressão digital do smith-api no ar **bate** (382 arquivos).
- `/health` às 20h: freio armado · allowlist 1 número · finalize `test` · envio fechado.
  **Às 22h, depois de o Founder ajustar o EasyPanel: os quatro abertos.**
- Agentes de atendimento: 3/3 desligados. AutoFleet: 467 conversas abertas sem dono.
- Grupo "Suporte AutoFleet" cadastrado **na Resulta Seguros** por engano (21:48). AutoFleet
  continua sem destino de suporte → **P-PILOTO-10**.
- Portal de vidros: 39 jobs, todos da Resulta em julho, zero com protocolo; AutoFleet nunca rodou.
- Acervo da URA: 561 sessões; 18 novas desde o corpus de 23/08 que a régua não viu.

## 1. Executado hoje (branch `feat/pilotos-ajustes-essenciais-0909`)

| U | o quê | arquivos | estado |
|---|---|---|---|
| U1 | foto até 16 MB · vídeo vira contexto e o agente pede foto · frase humana na falha de áudio · envio ao WhatsApp fora do event loop · buffer processa conversas em paralelo (semáforo) | `webhook.py`, `buffer_processor.py`, `evolution_inbound.py` | ver §5 |
| U2 | dossiê do corredor em português (motivo, serviço, dados, link do caso) · trava de laço do formulário nativo (P-092-10) · falha do formulário instrumentada | `insurer_dispatch_service.py` | ver §5 |
| U3 | portal: screenshot em todo desfecho (inclusive sucesso) · url/tela/hora por passo · resumo humano | `portal_worker/worker.py`, `portal_worker/adaptive.py` | ver §5 · **exige reimplantar portal-worker** |
| U4 | Conectores → Portais mostra todos os acionamentos do portal (estado, protocolo, prova) | `app/api/dashboard/portal-jobs/route.ts`, `…/conectores/portais/page.tsx` | ver §5 · **exige reimplantar smith-web** |
| U5 | cartas do pós-acionamento como conhecimento GLOBAL (`--global`) · follow-up só entre 8h e 19h, ancorado no horário combinado | `publicar_cartas_0971.py`, `dispatch_router.py`, `acompanhamento.py` | ver §5 |

## 2. Fica para a semana (pendências P-PILOTO-*, em `PENDENCIAS.md`)

1. **P-PILOTO-01 · concorrência e isolamento por corretora** — 🔴 importante. Hoje: 1 processo,
   LLM sem timeout, uma corretora travada pode atrasar todas. Alvo: ≥4 atendimentos simultâneos
   por corretora sem interferência entre corretoras (worker por fila de tenant ou processos
   múltiplos + timeout no modelo + backpressure). Desenho antes do código.
2. **P-PILOTO-02 · portal na Fila e na Ficha** — elo `portal_jobs.work_run_id/conversation_id`
   preenchido no insert; `projetarCasos` lê `portal_jobs`; fase "no portal da seguradora";
   coluna durável `protocolo`.
3. **P-PILOTO-03 · documento do cliente visível na Ficha** — guardar a URL do PDF em `messages`.
4. **P-PILOTO-04 · checklist por tipo para sinistro, empresarial e condomínio** — no desenho de
   `conhecimento_de_assistencia`; escritor de `ficha.faltando`; entradas em `_TITULOS`. O agente
   tem de fazer a primeira parte do atendimento e entregar mastigado.
5. **P-PILOTO-05 · formulário nativo da Porto e da Azul** — sem schema; o primeiro acionamento
   real observado produz o schema; até lá a tela de formulário vai a handoff com dossiê.
6. **P-PILOTO-06 · regenerar corpus, régua, inventário e roteiro de coleta** após cada dia de
   piloto (`gerar_corpus_de_telas.py --todas` · `medir_rota.py --todas --com-espelho --formato
   markdown`) e trocar a frase "🧑 acesso ao Espelho" em `medir_rota.py`.
7. **P-PILOTO-07 · portal passo 7 de verdade** (loja/domicílio, agendamento) e anexo de fotos —
   depende do HAR + vídeo/prints depositados em `docs/intake/MATERIAIS/PORTAL VIDROS/`.
8. **P-PILOTO-08 · tela cega no portal** — tela de navegador desconhecida entra na fila de
   aprendizado (SPEC-087) como a URA.
9. **P-PILOTO-09 · arquivo de credenciais fora do repositório** — `docs/canon/CREDENCIAIS
   EASYPANEL.txt` não pode existir dentro da árvore; segredos colados no chat devem ser
   rotacionados quando conveniente.
10. **P-PILOTO-10 · grupo da AutoFleet no tenant certo** — apagar "Suporte AutoFleet" da Resulta
    e recriar dentro da AutoFleet, como principal.
11. **P-PILOTO-11 · canário Q1–Q6 da cobrança no implantado** — variáveis já estão no smith-api;
    rodar `POST /api/admin/canario/extra001` e colar em §6.3 do relatório da EXTRA-001.
12. **P-PILOTO-12 · teste de linguagem humana nos dois dossiês** (`problemas_de_lingua` aplicado a
    `_montar_dossie` e `build_handoff_dossier`).

## 3. Decisões do Founder registradas hoje (D-PILOTO-*, em `FOUNDER-DECISIONS.md`)

D-PILOTO-01 conhecimento de atendimento/pós-acionamento é GLOBAL · D-PILOTO-02 não encerrar as
467 conversas · D-PILOTO-03 ligar HDI/Yelum com o formulário (trava de laço entra hoje) ·
D-PILOTO-04 follow-up só entre 8h e 19h, ancorado no horário combinado · D-PILOTO-05 coleta
dirigida vai até a tela de confirmação e recusa; o protocolo fica para demanda real (decisão
delegada ao orquestrador) · D-PILOTO-06 executar o essencial sem AAA por limite de tokens.

## 4. Como conferir amanhã que o portal foi acionado de verdade

1. Conectores → Portais → seção "Acionamentos no portal" (U4): estado, protocolo, "Ver prova".
2. Conversas: o agente diz ao segurado o número do atendimento.
3. Atividades: o vigia do portal escreve quando algo para (fila > 4 min, rodando > 8 min).
4. Consulta direta (enquanto a Fila não lê o portal):
   ```sql
   select id, portal_key, journey, status, attempts, created_at, finished_at,
          evidence->>'protocolo' as protocolo, evidence->>'resumo' as resumo
   from portal_jobs where company_id = (select id from companies where company_name='AutoFleet')
   order by created_at desc limit 20;
   ```
5. Pré-condições: agente ligado · `PORTAL_REAL_ENABLED=true` e `PORTAL_EFEITO_MATERIAL_LIBERADO=true`
   **no portal-worker** (no smith-api já está) · `/health` com `vidro_sem_corredor_vai_ao_portal: true`.

## 5. Resultado da execução

**Commits na `main` (08/09, 22h–01h):** `e77f1c2` docs · `936d9dd` U4 · `4454599` U3 · `46743ca` guarda M24 ·
`21c5ed9` U2 · `b433a9f` U5 · `f3f9031` U2-conserto (guarda) · `fce1098` U1 · + este.

**Testes por unidade (saída real dos builders, conferida):** U1 `10 passed` + 63 arquivos relacionados sem
regressão vs baseline · U2 `16 passed` + `100 passed` (retomada, painel, formulário) · U3 `48 ok / 0 fail` +
10 mutações vermelhas · U4 `tsc --noEmit` exit 0 + `rotas-montam` OK (301 rotas) · U5 `24 passed` +
`156 passed`.

**Gates do juiz, em isolamento, depois de todos os commits (📊 08/09 ~00h40):**
`py_compile` dos 8 módulos tocados OK · `test_098_builder_b_unit` 80 passed · `test_a_central_diz_a_verdade`
530 ok · `test_o_sinistro_deixa_rastro` 249 ok · `test_a_cobranca_chega_a_quem_deve` 162 ok ·
`test_ninguem_fala_com_o_segurado_sem_o_agente_ligado` rc=0 · `test_quem_fala_primeiro_cala_o_outro` rc=0 ·
`test_o_caso_se_explica_sozinho` 109 ok · `test_o_travamento_vira_linha` + dossiê + retomada 75 passed ·
`test_spec073_portal_worker_mutations` 0 FALHOU.

**O que a suíte inteira mostrou e por que não vale como prova:** os builders rodaram `pytest tests/` em lote
com a árvore em edição concorrente (15 failed / 48 errors); os 48 erros eram de `test_098_builder_b_unit`,
que passa 80/80 isolado — poluição de `sys.modules["app"]` deixada por `test_o_sinistro_deixa_rastro`
(anotar como pendência de higiene de testes). ⚠️ A suíte inteira com árvore parada NÃO foi rodada hoje
(decisão de tokens, D-PILOTO-06); é a primeira coisa a fazer na próxima sessão com folga.

**Guardas que acusaram e foram atendidos:** `test_o_travamento_vira_linha` (família `formulario_em_laco`
sem triagem; motivo `formulario_envio_falhou` escrito longe do `needs_human`) · `[M2p]` da 097.1 passou a
congelar a janela do follow-up aberta · M24 do worker procurava o nome num comentário.

**Implantação (🧑):** smith-api → portal-worker (`PORTAL_EFEITO_MATERIAL_LIBERADO=true` no ambiente dele)
→ smith-web; depois `/health`, `publicar_cartas_0971.py --global --vivo`, grupo de suporte na AutoFleet.

**Achados dos builders que viraram pendência (acrescentar em PENDENCIAS na próxima sessão):** supressão do
follow-up fora da janela é perdida, não adiada (só `avisos == 0` fala) · `_dia_e_mes` compara em UTC ·
`webhook._responder_formulario_nativo` devolve bool e descarta o status do provedor · `dispatch_router`
:1210/:1973 grava `Motivo: {reason}` cru em `work_runs.result_summary` · `vidros_lanternas` não existe em
`portals` · bucket `portal-evidence` sem retenção · `test_o_sinistro_deixa_rastro` deixa `sys.modules`
sintético.
