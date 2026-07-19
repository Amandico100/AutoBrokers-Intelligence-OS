# SPEC-039 — Auditoria da Central de Agentes + Inteligência de Atendimento

> Fable, 19/07/2026. Auditoria profunda de TODOS os agentes + decisões
> estratégicas do founder (modelo, conversas do cliente, nome global do
> atendente). Documento executável por qualquer modelo. Achados verificados no
> código-fonte (não de memória).

## PARTE 1 — AUDITORIA DA CENTRAL DE AGENTES (13 agentes)

Verifiquei quem pulsa (`beat`), quem tem agendador, e o estado real de cada um.

| Agente | Pulsa? | Disparo | Estado | Achado |
|---|---|---|---|---|
| Observador | ✅ `beat` na captura | webhook (evento) | OK | — |
| Tecelão | ✅ `beat` na tecelagem | /weave + Sentinela | OK | — |
| Sentinela de Rotas | ✅ `beat` | **SÓ manual (/sentinela/run)** | ⚠️ **F1** | sem agendador → Atlas não se auto-atualiza sozinho |
| Espelho | ✅ | evento de dispatch | OK | — |
| Vigia + Sentinela | ✅ | APScheduler 20s | OK | — |
| Follow-up | ✅ | APScheduler 60s | OK | — |
| Garimpo | ✅ | APScheduler 1h | OK | — |
| Auditor | ✅ | APScheduler 30min | OK | — |
| Alfaiate | ✅ | via Auditor + Sentinela | OK | — |
| IA de Sugestões | ✅ | APScheduler 30min | OK | — |
| Cartógrafo | ✅ | sob demanda | OK | — |
| **Cérebro v2** | ❌ **NUNCA chama `beat`** | inline no dispatch | ⚠️ **F2** | mostra "nunca rodou" na Central mesmo funcionando |
| Even/atendente | n/a | runtime | ⚠️ **F3** | nome "Even" HARDCODED (ver Parte 3) |

### Falhas encontradas (prioridade)
- **F1 — Sentinela de Rotas sem agendador (ALTA).** Hoje o Atlas só se atualiza
  quando alguém clica "Sentinela". Para ter "vida própria" (founder), precisa de
  um job periódico (proposto: 1x/dia, consolidação noturna) no APScheduler do
  buffer. FIX: `scheduler.add_job(check_atlas_sentinela, seconds=86400)`.
- **F2 — Cérebro v2 não pulsa (MÉDIA/cosmética).** Ele decide nos desvios (roda
  no `insurer_dispatch_service`) mas nunca chama `beat("cerebro")` → Central
  mostra "AGUARDANDO/nunca rodou", passando impressão de agente morto. FIX:
  `beat("cerebro", 1)` quando o Cérebro escolhe uma opção em desvio.
- **F3 — "Even" hardcoded (ALTA — pedido explícito do founder).** Pontos:
  - `lib/admin/agent-health.ts`: força normalizar todo atendimento para "Even"
    (`attendance_name_not_even` + ação `rename_attendance_even`). ERRADO: cada
    corretora tem seu nome. FIX: remover a regra de normalização; o health só
    deve exigir que EXISTA um agente de atendimento, não que se chame "Even".
  - `backend/app/services/billing_collection.py`: `attendant_name` default
    "Even". FIX: default neutro ("nossa equipe" / nome da corretora do config).
  - Frontend labels ("Even (Atendimento)"): trocar por "Atendente (Atendimento)"
    ou o nome configurado da corretora.
  - Comentários com "Even" (llm_factory, observer_intake): inofensivos, podem
    ficar, mas idealmente "o atendente".

### Modelo dos agentes (força)
- **Dispatch (fase humana com a seguradora)**: env `DISPATCH_LLM_MODEL` =
  `claude-sonnet-5` (forte — ok). Fallback no código = `gpt-4o` se env ausente.
- **Cérebro v2 / Atendimento**: usa o modelo do agente; Core é promovido por
  `CORE_CHAT_MODEL`. Even/atendimento mantém o configurado.
- **Resolvedor do Atlas** (menus digitados): `ATLAS_PARSER_MODEL`=claude-sonnet-5.
- RECOMENDAÇÃO: manter tudo em Sonnet 5 como piso forte; ver Parte 2 p/ Opus.

## PARTE 2 — DECISÃO DE MODELO (Sonnet 5 vs Opus p/ o histórico)

Custo REAL medido: **R$ 0,50 por passada** cobrindo TODAS as seguradoras (o
modelo só toca o resíduo ambíguo do mapa consolidado — não lê as conversas).

- Opus custa ~5x o Sonnet no token → passada ~R$ 2,50 em vez de R$ 0,50.
- **Recomendação Fable: usar Opus SÓ na PRIMEIRA GRANDE INGESTÃO** (segunda, quando
  entram centenas de conversas históricas — a análise mais valiosa e única), e
  voltar para Sonnet 5 na manutenção contínua (drift do dia a dia). Justificativa:
  a primeira leitura define a base de todos os mapas; vale o modelo mais forte
  uma vez. Depois, Sonnet 5 mantém com qualidade a custo baixo.
- IMPLEMENTAÇÃO: já é só env. Segunda: `ATLAS_PARSER_MODEL=claude-opus-4-8`
  (+ `ATLAS_PARSER_PROVIDER=anthropic`). Após a ingestão: voltar a
  `claude-sonnet-5`. Zero mudança de código (o resolvedor lê o env).
- Custo teto da primeira ingestão com Opus: **< R$ 5** (founder aceitou).

## PARTE 3 — NOME GLOBAL DO ATENDENTE (corrigir "Even")

Regra canônica (founder, repetido): **"Even" é só o nome que a Resulta deu.**
O sistema NUNCA deve assumir "Even" — cada corretora nomeia o seu no dashboard.
Ver F3 (Parte 1) para os pontos exatos. Prioridade ALTA porque antes de onboardar
a AutoFleet, o health-check vai "sugerir renomear para Even" — errado.

## PARTE 4 — CONVERSAS CLIENTE↔ATENDENTE (a grande pergunta estratégica)

O founder perguntou: hoje só aproveitamos a conversa ATENDENTE↔SEGURADORA
(Parte 2 do atendimento). Devemos aproveitar também a conversa CLIENTE↔ATENDENTE
(Parte 1)? Minha análise:

### SIM, vale muito — mas com arquitetura SEPARADA (não misturar com o Atlas)
São dois tipos de inteligência DIFERENTES, e misturar estragaria os dois:
- **Atlas (URA)** = ESTRUTURA determinística de menu de máquina. Fiel, sem PII.
- **Parte 1 (cliente↔humano)** = LINGUAGEM natural: como um bom atendente
  ACOLHE, que perguntas faz para extrair CPF/placa/local, como conduz um
  sinistro delicado, como responde dúvida de apólice. É PLAYBOOK DE CONDUTA, não
  árvore de URA.

### O que fazer com ela (proposta — o agente "Espelho de Atendimento")
1. **Captura** (já temos!): o Observador no número da corretora já vê a Parte 1
   (cliente↔atendente). Hoje o filtro de borda DESCARTA porque só guarda
   seguradora. Ajuste: um segundo destino — conversas com NÚMEROS DE CLIENTE
   (não-seguradora, individuais) entram numa tabela `attendance_transcripts`
   (isolada por corretora, com PII, NUNCA global).
2. **Garimpo v2 estende p/ Parte 1**: extrai (a) FAQs reais dos clientes,
   (b) dados que o cliente já dá de bom grado vs os que o atendente precisa
   perguntar, (c) padrões de sinistro/assistência/apólice. Vira:
   - **Playbook de conduta por tipo** (assistência/sinistro/apólice) — instruções
     ao atendente-IA de COMO conduzir a Parte 1 (tom, ordem de perguntas,
     sensibilidade em sinistro).
   - **Knowledge cards** para o RAG (respostas a dúvidas frequentes).
3. **Auditor v2 estende p/ Parte 1**: nota de qualidade do atendimento humano;
   os transcritos-ouro (melhores atendimentos) viram exemplos few-shot.

### O que NÃO fazer (riscos que o founder intuiu)
- NÃO jogar transcritos crus no RAG global (PII + ruído "enche linguiça").
- NÃO deixar a Parte 1 contaminar o Atlas (URA) — são tabelas e agentes
  separados.
- Conteúdo destilado (playbooks/cards SEM PII) pode ir ao RAG global; transcrito
  cru fica isolado por corretora.

### O Chat Principal (Core) fica cego?
Hoje o Core busca no RAG (inclui global se `KNOWLEDGE_GLOBAL_SEARCH=1`), mas NÃO
tem visão operacional dos atendimentos em curso. PROPOSTA: dar ao Core uma tool
`resumo_atendimentos` (lê agent_activities/dispatch por corretora) — assim o
corretor pergunta no chat "como estão os acionamentos hoje?" e o Core responde.
Escopo: só a PRÓPRIA corretora (multi-tenant), read-only.

## PARTE 5 — PLANO DE EXECUÇÃO (ondas, para qualquer modelo executar)

- **Onda A — Correções da Central (baixo risco, alto valor):** F1 (agendador da
  Sentinela 1x/dia), F2 (beat do Cérebro), F3 (remover "Even" hardcoded).
- **Onda B — Modelo da ingestão:** env Opus p/ a 1ª grande ingestão de segunda,
  Sonnet 5 na manutenção (só env, sem código).
- **Onda C — Espelho de Atendimento (Parte 1):** tabela attendance_transcripts,
  segundo destino no Observador (números de cliente), Garimpo v2 + Auditor v2
  estendidos, playbooks de conduta + knowledge cards destilados (sem PII).
- **Onda D — Core operacional:** tool `resumo_atendimentos` no Chat Principal.
- **Bloco D (app nativo):** replicar o nfm_reply capturado p/ o atendente
  atravessar o formulário HDI/Yelum (independente destas ondas).

## PRÉ-REQUISITOS / DECISÕES DO FOUNDER
1. Modelo da 1ª ingestão: Opus (rec.) ou Sonnet 5? (custo < R$5 vs ~R$0,50)
2. Aprovar o Espelho de Atendimento (Onda C) — usar as conversas do cliente?
3. Aprovar dar visão operacional ao Chat Principal (Onda D)?
4. EVOLUTION_GO_GLOBAL_KEY já colado ✅ (onboarding destravado).
