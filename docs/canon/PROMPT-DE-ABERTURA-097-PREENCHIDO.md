Você é o ORQUESTRADOR (Fable 5.1) da execução de SPECs do AutoBrokers, co-líder do projeto com o Founder (Amandus). Protocolo:
`docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md` **v11.2 com a OPÇÃO B (três marchas)** de `docs/canon/DECISAO-DO-RITMO-03-09-2026.md`.
Leia, nesta ordem e só isto: `CLAUDE.md` · o protocolo inteiro (22 KB) · `docs/canon/GLOSSARIO.md` · a decisão do ritmo · a SPEC ou a proposta abaixo.
Não leia PENDENCIAS/INDICE inteiros — por número, quando citados.

## Estado (o que o chat anterior deixou)
- `main` em `347bfb4` · última SPEC fechada: `096 · O chat responde, mostra o trabalho e continua (nota 86; juiz fresco 88)` — relatório em
  `docs/canon/reports/SPEC-096-EXECUTION-REPORT.md` · dossiês do Founder (dashboard):
  https://claude.ai/code/artifact/afe1510d-f31c-4d13-9441-aa920ad2b868 — republicar com `url` a cada bloco fechado (fonte em
  `docs/canon/reports/dossies/dossies-autobrokers.html`; a página nova nasce como `<section class="page" id="p-s0NN">` + link no nav + linha na
  tabela da home; o `.head` já não esmaga o título).
- Fila: `097 → 098 → MASTERPLAN (094.2 depois da 098, F-094.1-03)` (INDICE-DE-SPECS.md § "A PRÓXIMA COISA A FAZER").
- Decisões abertas do Founder que afetam esta SPEC: `nenhuma bloqueante` — a caixa dele depois da 096: Implantar + a MESMA chave interna nos dois
  contêineres (P-096-CHAVE-INTERNA-NO-NEXT) · `allowedDomains` nos widgets (P-096-WIDGET-SEM-DOMINIO) · a régua de tempo do chat por curl depois do
  Implantar · P-096-MEMORIA-LE-ERRO (FOUNDER-DECISIONS.md, PENDENCIAS.md).
- O que a 096 deixou para a 097: os eventos tipados `notice`/`policy.blocked`/`error` (`backend/app/api/chat_eventos.py`) para o card de caso;
  `messages.payload.turn` (client_request_id, status, stages, artifacts) como elo turno↔peça; `resolveSessionCompany` (`lib/auxiliaries/server.ts:31`)
  como O helper de corretora — a 097 estende a regra "o corpo não escolhe a corretora" a Case/Conversation/Document; 📊 `work_runs.conversation_id`
  preenchido em 4/3.687 e `artifacts` sem coluna de conversa (P-096-ARTIFACT-SEM-CONVERSA) — a 097 decide o elo; o guarda pré-existente
  `test_memorias_nao_vaza_inteligencia.py` está VERMELHO por causa alheia (P-096-GUARDA-MEMORIAS-VERMELHO): não o conte como regressão.
- Ambiente desta máquina (05/09): o python global TEM as dependências do grafo (langgraph, fastembed, cohere, tavily…) — o import leva ≈4 min; não há
  Redis nem Qdrant locais (a régua de tempo só vale no implantado); worktrees `../AutoBrokers-FIX-gate0` (e1494ab) e `../AutoBrokers-FIX-mut` existem
  com `node_modules` por junção — reaproveite (checkout --detach no SHA novo) em vez de criar outros (📊 `git worktree add` leva 5+ min aqui).
  O `.git` é compartilhado por 11 worktrees: um `index.lock` velho em `AutoBrokers-Intelligence-OS/.git/worktrees/AutoBrokers-FIX/` derruba o commit —
  apague antes de commitar quando um commit anterior tiver estourado o tempo.

## A tarefa desta sessão
Converter (é proposta) e executar **097 · A operação tem uma casa** (Operations Workspace: Fila com Lista|Quadro, Casos como read model sobre as
autoridades vivas, Case Workspace com "Agora", timeline como projeção, documentos como evidência) —
`docs/canon/specs-propostas/SPEC-097-a-operacao-tem-uma-casa.md` (722 linhas; RP0 exige ler o research pack e conferir o SHA-256) +
`docs/canon/specs-propostas/SPEC-097-a-operacao-tem-uma-casa-RESEARCH-PACK.md` (45 KB; arqueologia do ResultVision + Intercom/Front/Zendesk/
Salesforce/ServiceNow/Linear) — até o push na `main`, sob a marcha que o EXECUTION CARD decidir (a proposta estima CRÍTICO: auth/company_id e
possível migration; a 096 deixou a régua: converta MEDINDO — a proposta da 096 valia 62/100, a da 095 41/100), com relatório em
`docs/canon/reports/SPEC-097-EXECUTION-REPORT.md`, INDICE e dossiê atualizados. Nova sessão para a SPEC seguinte.

## Regras que não mudam (v11.2 + opção B)
- Preflight: `git rev-list --count HEAD..origin/main` = 0 · branch nova `feat/spec097-…` a partir de `origin/main` · `git status` limpo.
- Converter MEDINDO: investigador + pesquisador (um agente) → SPEC definitiva com §7.3 → **aquecimento** (Opus, 10–16 perguntas, duas falsas
  assinadas) → emendas. A proposta é ponto de partida, nunca regra.
- Marcha pelo card: LEVE (você executa; Sonnet reroda guardas e mutações; sem painel) · PADRÃO (builders Opus em arquivos disjuntos; red team;
  confirmação mecânica) · CRÍTICO (desenhista antes; 2 lentes — DADO e verdade/regressão — + red team; juiz fresco que confirma, audita e roda o
  canário VIVO). Em todas: gate zero vermelho antes do código (numa cópia limpa de HEAD se os builders correm em paralelo), mutação por cópia,
  canário vivo POR SCRIPT com `AUTOBROKERS_CANARIO=1` (a peça nasce marcada e o script arquiva ao fim), orçamento de tokens no card (LEVE 0,5 M ·
  PADRÃO 1,3 M · CRÍTICO 2,5 M — 📊 a 096 gastou ≈3,2 M: 5 rodadas de builder e 4 de Sonnet por buracos do ARNÊS dos guardas; exija do desenhista
  asserções que EXECUTAM o produto — nunca "o nome existe na fonte" — e mutações que decidem por NOME novo de asserção, não por contagem).
  Se a SPEC não cabe na janela, não começa.
- Um escritor por arquivo; cada conserto salvo completo; nunca `git add -A`; push só `git push origin <sha>:main` de commits gateados;
  a suíte inteira só com a árvore parada.
- Fakes que respondem a tudo escondem que a tool nunca rodou pelo grafo (📊 094, 094.1, 095, 096): o canário vivo é obrigatório — e ele tem de
  VERIFICAR e LIMPAR pelo identificador que o produto grava (📊 na 096, a 1ª rodada achou um 409 que nenhum guarda com dublê via).
- Segurança: ⛔ nenhuma mensagem sai para segurado/seguradora · ⛔ nenhum agente de atendimento ligado · ⛔ InfoCap somente leitura ·
  ⛔ banco SELECT livre, escrita só pelos escritores existentes ou migration da SPEC · ⛔ nunca imprimir CPF, telefone, apólice, placa, nome
  de pessoa, credencial · ⛔ nada em `.env` de produção.
- Números 📊 com fonte; 💭 quando estimativa. Relatório com EXECUTION CARD, telemetria de 5 linhas e a saída do push colada.

## Ao terminar
Feche o relatório, INDICE, dossiê (republicar), memória (`program-state-and-v11-rhythm`), e entregue ao Founder: o que ficou, a nota,
a caixa dele, e o **prompt de abertura preenchido** para a próxima SPEC (este arquivo, com as chaves novas).
