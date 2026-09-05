# SPEC-097 · EXECUTION REPORT — A operação tem uma casa

> Branch `feat/spec097-casa` · base `origin/main` = `7f3f3eb` · protocolo v11.2 + opção B · marcha **CRÍTICO** · 05/09/2026 (mesma sessão da 096, por ordem
> do Founder: "emende direto") · orquestrador Fable 5.1 · SPEC `docs/canon/specs/SPEC-097-a-operacao-tem-uma-casa.md` v1.1.

## 0. EXECUTION CARD (protocolo §0.2)
```
OUTCOME ..............  o desfecho do atendimento deixa de ser deduzido do relógio (PARADO ≠ ENCERRADO; encerrado ⇔ resolvido_em escrito); o dono deixa de ser o
                        status (e a IA pausa quando alguém assume); o caso é o EPISÓDIO com elo para a conversa; Fila e Casos leem UMA projeção sem teto; o AGORA
                        e a timeline com hora e fonte
RISCO ................  7  (alcance: a corretora 2 · reversibilidade: dado/estado 2 — escreve resolvido_em/claimed_by/colunas novas · frequência: TODO atendimento 2 · +1 pela migration)
SUPERFÍCIE ...........  3  (Web + BFF + FastAPI (chamadores do corredor, webhook, chat) + Atlas + DB + UX principal do atendimento)
PISO APLICADO ........  §3.2: migration que ALTERA ESTRUTURA (3 colunas + FK + índice em attendance_sessions) + escrita no ciclo de vida em produção → CRÍTICO
NÍVEL ................  CRÍTICO
UNIDADES .............  0 (gate zero + régua) · U1 desfecho · U2 dono (+U2.3 pausar_ia) · U3 episódio (migration + backfill + Atlas) · U5 read model · U6 AGORA/timeline · E canário · G guardas
                        (U4 espera e U6.3 paginação SAÍRAM no aquecimento — E10/E18)
COESÃO ...............  U1+U2 juntas (são o contrato do estágio); U3 antes de U5 (a chave do read model); U5+U6 na tela/BFF; escritores python no backend
PARALELISMO REAL .....  2 escritores: builder backend (backend/**) ‖ builder tela+BFF (app/**, lib/**) — contrato = `attendance_sessions.conversation_id` + os escritores por episódio
TIME .................  investigador+pesquisador (Opus, 193k) · aquecimento (Opus, 160k) · desenhista · 2 builders · red team · lente DADO · lente verdade · juiz fresco · Sonnet mecânico
REFERÊNCIA ...........  interna: guardas da 096 (bloco [D] que sobe o router; [1]–[25] que executam rotas e componentes) · `test_o_atendimento_termina_e_o_produto_sabe.py` (086)
                        externa: SPEC §3 — Intercom (SLA como relógio; views como filtro), Front (um dono), Zendesk (trilho de contexto), Salesforce Case Timeline (Spring '26),
                        ServiceNow (activity stream como exibição), CQRS (read model; drag = comando) — reabertas em 05/09
GATES ................  gate zero (9 vermelhos na cópia limpa) · guardas G verdes · 12+ mutações · rotas montam · tsc · next build · next start + 1 request · suíte inteira ·
                        migration APPLY/VERIFY/ROLLBACK + advisors · backfill --dry-run/VERIFY · canário E · régua 0.2 depois · painel + juiz · push
O ELO ................  "a Fila encerra PORQUE o else do silêncio" → medido A (584 rotulados), medido B (`resolvido_em` 0/728), medido que B chega em A (rodando a MESMA
                        cascata sobre o acervo: 584 vêm do else). "com_equipe é inalcançável PORQUE o claim escreve status" → lido o único escritor + a ordem da cascata.
FAIXA DE RELÓGIO .....  6–8h   ORÇAMENTO ≤ 2,5 M (📊 a 096 estourou 28% por arnês: exigido do desenhista asserções que EXECUTAM)
```

## 0.1 Telemetria (protocolo §11)
```
começou 05/09 ~10:45 (branch) · primeira linha de código de produto: {A PREENCHER}
rodadas de painel: {A PREENCHER}
defeitos que o painel NÃO pegou e quem pegou: {A PREENCHER}
rodadas da bateria: {A PREENCHER}
nota 0–100 do orquestrador: {A PREENCHER}
```

## 1. O que a conversão mediu (e o que mudou o desenho)
- 🔴 📊 A Fila rotula **584 de 668** conversas (87,4%) "Atendimento encerrado" pelo ramo `else` do silêncio > 48 h; `resolvido_em` NULL em **728/728**; `status='closed'` = 0;
  e o MESMO payload devolve `semana.terminaram: 0, indisponivel: false`. Invariantes 8, 16 e 17 da própria proposta violadas hoje.
- 📊 `work_waits` = **0 linhas na vida** (esquema, FK e CHECK completos); os 3 chamadores de `abrir_espera`/`marcar_fim` só chamam com o espelho (`mirror_conversation_id`);
  4 acionamentos em 30 dias → U4 SAIU (P-097-ESPERA-COM-ESCRITOR).
- 📊 O único escritor de `claimed_by` grava `status='HUMAN_REQUESTED'` junto; a cascata testa status antes do dono → "está atendendo" inalcançável (latente: 1 claim na vida).
  E a IA pausa só por status (`webhook.py:628`, `chat.py:173,620`) → E6 obrigatória: `pausar_ia` por `claimed_by` também.
- 📊 1 telefone = 1 conversa perpétua (666/667; até 1.326 mensagens, 29 dias); `attendance_sessions` 12.755 (5,8 por contato; 56% com 2+ em 7 dias) sem `conversation_id`;
  só **57,8%** casam 1:1 por telefone → o caso é o EPISÓDIO; migration expand-first (conversation_id + resolvido_em + resolucao_motivo); órfãs continuam casos.
- 📊 Não há N+1; há teto fixo (`.limit(120)` sobre 448) e busca `filter()` no cliente → falso "nada encontrado".
- 📊 Documentos: 13 imagens e 0 áudios com URL em 25.061 mensagens; `documents` é RAG → D-097-07 vira pendência. Notas: já consolidadas. "Histórico": sobrou um label.
- Aquecimento: **nota 74**, 18 emendas (E1–E18) aplicadas; as 2 falsas assinadas (656 → 666; `.limit(200)` → `.limit(120)`) refutadas por comando; 3 números da §1 reproduzidos.
- Proposta: 📊 nota do investigador **62/100** — SPEC de leitura para um problema de escrita.

## 2. Decisões da execução (protocolo §9: nota, escolha, siga)
- episódio = `attendance_sessions` **85** × tabela `cases` nova 30 (motor paralelo) × caso = conversa 20 (o censo inverte).
- desfecho no EPISÓDIO (colunas na sessão, espelhado na conversa) **80** × órfã inelegível a ENCERRADO 55.
- U4 espera SAI desta marcha **80** × escritor sem evento 45 (4 acionamentos/30 d; FK barra o órfão).
- Fila por CONVERSA ativa (lotes de 1.000, contagem em memória) e Casos por episódio com cursor **75** × RPC de contagem (migration a mais) 50.

## 3. Commits
```
5850c43 SPEC v1.0 · ad71e57 dossiê · 806282a aquecimento/emendas (v1.1) · {A PREENCHER}
```
## 4. Gate zero
{A PREENCHER}
## 5. Migration
{A PREENCHER}
## 6. Guardas e mutações
{A PREENCHER}
## 7. O painel e o juiz
{A PREENCHER}
## 8. Canário vivo
{A PREENCHER}
## 9. O que ficou fora · pendências · a caixa do Founder
{A PREENCHER}
## 10. Declarações
- Nenhum motor paralelo: sem tabela de casos, sem event store, sem escritor novo de ciclo de vida além dos que existem (marcar_fim/claim) — só estendidos.
- Nenhuma mensagem saiu; nenhum agente ligado; InfoCap só leitura; nenhum segredo/PII impresso.
## 11. Entrega
{A PREENCHER}
