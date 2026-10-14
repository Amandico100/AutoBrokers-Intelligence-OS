# Relatório de execução — SPEC-132-C: o WhatsApp do corretor (o mesmo chat principal, pelo WhatsApp dele — o atalho)

**SPEC:** `docs/canon/specs/SPEC-132-C-o-whatsapp-do-corretor.md` · 3ª de três no mesmo chat · executa a 131-0 parte B1 (PEDIR pelo
número verificado; D-131-0-11)
**Branch:** `spec/132-o-chat-e-a-cotacao` · **base** `285cadc` (= `origin/main` no preflight) · **último commit** `ce32e89` (push: §7)
**Gerente:** Opus 5.5 · protocolo AAA v13.2 · nível CRÍTICO (envia mensagem) · todos os subagentes `claude-opus-5-5` (telemetria §11)
**Estado final:** CONCLUÍDA, DESLIGADA (`ATALHO_WHATSAPP_LIGADO` ausente; o número do AutoBrokers ainda não foi pareado — T-171)

## 0.0 EXECUTION CARD
```
OUTCOME ........ o corretor salva o contato "AutoBrokers" e conversa com ele como com o chat principal: escreve, manda áudio, foto, PDF
                 — e recebe a mesma resposta (inclusive a Cotação Rápida: o resumo e o link); nada muda no número de ATENDIMENTO da
                 corretora nem no do Quem Cobra Menos
RISCO .......... 7 (corretora 2 · SAI DO PRÉDIO 3, mensagem enviada · todo uso 2)
SUPERFÍCIE ..... 2 (peça nova sobre peças que existem: webhook Evolution GO, empresa da plataforma, turno do CORE, chat_anexos)
PISO APLICADO .. CRÍTICO: envia mensagem · identidade por telefone (quem é quem) · company_id escolhido pelo NÚMERO
NÍVEL .......... CRÍTICO · builders Opus 5.5 · juiz ‖ red team · confirmação (houve blocker)
O FIO .......... Meu perfil → código de 6 dígitos (hash, 15 min, 1×) + wa.me "ATIVAR 123456" → o corretor manda do CELULAR DELE →
                 webhook → integração purpose=assistente → desvio ANTES do observer → código casa o número DECLARADO → verificado →
                 mensagem seguinte → membro → conversa channel=whatsapp_assistente → anexos → MESMO /chat/stream em processo → resposta
                 pela instância do AutoBrokers → (cotação) o Work Run grava em messages E envia pelo WhatsApp
UNIDADES ....... 3 fatias (C1 verificação · C2 o atalho · C3 costura) + 1 conserto (+ a Fila, `de42bed`)
COESÃO ......... o desvio, o turno e o envio juntos em `services/atalho/` (C2: um cinto único de saída)
PARALELISMO REAL C1 ‖ (as fatias da 132-A/B) → C2 → C3 costura (depois da B4: o envio da volta da cotação)
TIME ........... 3 builders · juiz ‖ red team · conserto único · confirmação · conserto do gerente (N1) · bateria · atualizador
REFERÊNCIA ..... interna: o desvio do QCM no webhook (133-A) e o canal da plataforma (`platform_canal`); externa: SPEC §8 (3 URLs)
GATES .......... fio · 2 corretoras · número desconhecido = silêncio · anti-laço (entrada E saída) · 6 mutações · rotas montam · bateria
O ELO .......... "o atalho responde com o MESMO cérebro do chat PORQUE chama o mesmo /chat/stream" → o fio prova `companyId`/`userId`
                 do turno = os do membro verificado (📊 texto com `companyId` de outra corretora → turno na corretora DELE)
FAIXA DE RELÓGIO declarada 💭 5–7 h · real 📊 ≈ 7 h 30 para as TRÊS SPECs juntas (14/10, 02:20 → ~09:50 de Brasília, telemetria
                 §11; a bateria ainda roda)
```
① painel de lentes: não (juiz ‖ red team pela conta do §3). ② auditoria externa: juiz ‖ red team frescos + confirmação nova.
③ pendência por valor marginal: P4/P5 do red team (`data.key` em lista → 500; texto de 1 MB sem corte antes do turno → cortado em 8000
no conserto), P7 do juiz (limpeza das tabelas de tentativa).

## 0.1 O protocolo — contas, laço, rebaixamentos, drenagem
| unidade | ALC | REV | FREQ | RISCO | SUP | piso | time |
|---|:---:|:---:|:---:|:---:|:---:|---|---|
| C1 a verificação + migration | 2 | 2 | 1 | 5 | 2 | identidade por telefone | builder |
| C2 o atalho | 3 | 3 | 2 | 8 | 2 | envia mensagem | builder |
| C3 costura (QR, volta da cotação) | 3 | 3 | 1 | 7 | 2 | envia mensagem | builder |

**O laço:** 1 volta + o conserto do N1 da confirmação. Saída: **só pendências** (confirmação 88, 3/3 fechados; N1 consertado pelo
gerente em `ce32e89`, 📊 `test_spec132c_verificacao` 40 passed).
**Rebaixamentos pelo gerente:** nenhum. **Promoveu** a P1 (juiz + red team: o código valia para QUALQUER remetente e não havia teto
global) a blocker de segurança do conserto.
**Pendências que a SPEC tocou:** nenhuma da lista antiga (a P-131B-08, a faixa de abas do Meu perfil, não mudou).

## 1. Resumo executivo (FATO)
- **Um número da PLATAFORMA "AutoBrokers"** para todos os corretores de todas as corretoras (D-132C-01): uma integração
  `purpose='assistente'` na empresa da plataforma (a mesma do QCM, outro número), com o QR no admin em "Canais: AutoBrokers — assistente
  dos corretores". Parear `assistente` numa corretora comum é recusado (`assistente_so_na_plataforma`).
- **Verificação por POSSE** (D-132C-02): o Meu perfil gera um código de 6 dígitos (só o hash no banco, 15 min, uso único) e o botão
  `wa.me/<número>?text=ATIVAR 123456`; o corretor manda do celular DELE; o código só vale do número que ele DECLAROU no perfil (conserto
  do P1: código vazado mandado de outro celular não troca a identidade), com teto por telefone e teto GLOBAL; um "ATIVAR" de número que
  ninguém declarou cala SEM contar no teto global (N1, `ce32e89`) — ninguém consegue desligar a ativação de todos.
- **O atalho** (C2): o desvio no webhook ANTES do observer, como o do QCM; número desconhecido = SILÊNCIO, sem registro de conteúdo
  (D-132C-03); fromMe, grupo, status e números de instâncias do produto ignorados; o turno é o MESMO `/chat/stream` chamado em processo
  com a identidade do membro (D-132C-04, sem agente novo); a conversa nasce com `channel='whatsapp_assistente'` (D-132C-05) e fica FORA
  da Central, do espelho e da Fila de atendimentos (`de42bed`); a mídia sobe ao Storage no prefixo da corretora e passa pelo
  `chat_anexos.preparar` da 132-A; membro de duas corretoras recebe a pergunta "qual corretora?" UMA vez por janela.
- **A volta da cotação** (C3): quando a conversa nasceu no WhatsApp, o Work Run `cotacao.chat` grava em `messages` E manda pelo número do
  AutoBrokers — uma vez (id fixo), só para a conversa do atalho, com teto de tempo real.
- **O cinto único da saída** (conserto do red team): todo envio do atalho passa por `enviar(db=…)`, que recusa destino que seja número de
  instância do produto e conta no teto de envios por dia (estado durável sem Redis, migration `_05`).

## 2. Escopo (FATO — commits)
`534005f` SPEC · C1 `9701b39`…`90b7578` · C2 `c2e71eb`…`6f649a7` · C3 `b1f3df7`…`26b1fb8` · conserto `f483871`…`20f7c33` · `de42bed` a
conversa do atalho fora da Fila · `ce32e89` N1. 📊 `git log 285cadc..HEAD --grep=spec-132-C` → 42 commits, 31 arquivos, +5.414 / −293.
**Entregas NÃO executadas:** o canário real (uma conversa pelo número do AutoBrokers) — espera o chip, o QR e a variável (T-171).

## 2.1 BLOCO 0 (📊 14/10)
Empresa `company_kind='platform_canal'` com a integração do QCM; desvio do QCM no webhook antes do observer; `whatsapp_trabalho_e164`
confirmado por CLIQUE (0 verificação por posse); `integrations.purpose` sem CHECK no banco (PRÉ da `_03`: 0 linhas); `conversations.channel`:
whatsapp 1.173 · web 86 · nulo 0.

## 4. Migrations (APLICADAS pelo gerente: psycopg, transação, `lock_timeout 5s`; sha256 do commit = cópia de trabalho)
| arquivo | versão | VERIFY |
|---|---|---|
| `20261014_03_spec132c_atalho_whatsapp.sql` | 📊 `20261014075717` | PRÉ 0 linhas (sem CHECK de purpose) → `1·1·1·2·2·2·0·0` (coluna `whatsapp_trabalho_verificado_em` · CHECK validado · índice único do número verificado · 2 tabelas com RLS · 2 índices dos códigos · FK + CHECK do hash · 0 policies · 0 grants públicos) · comportamental 4 recusas, 0 sobra |
| `20261014_05_spec132c_conserto.sql` | 📊 `20261014112744` | → `1·1·2·0·0` (`whatsapp_atalho_estado` com RLS · contador · 2 CHECKs · 0 policies · 0 grants públicos) |

## 5. Testes e gates (📊 saídas reais)
- Builders: C1 36 passed · C2 16 passed · C3 21 + 229 passed.
- Juiz (HEAD `26b1fb8`): `test_spec132c_o_fio` **22 passed** · `_o_atalho` **16 passed** · `_verificacao` **36 passed** ·
  `test_spec133a_o_fio` (QCM intacto) **17 passed** · 10 sondas próprias **10 passed**.
- Red team: 18 ataques no motor real (falsificar `Sender`/`participant`, LID sem e com `SenderAlt`, sem o 9º dígito, código vencido/2º
  uso/zero-width, ATIVAR de linha de outra corretora, parear `assistente` em corretora comum, segredo e telefone no log em DEBUG →
  todos `False`) — aguentaram, menos a saída sem anti-laço.
- Confirmação: `_o_fio` **24 passed** · `_o_atalho` **26 passed** · `_verificacao` **40 passed** · `test_spec133a_o_fio` **17 passed** ·
  ataques juiz+red team **6 failed, 22 passed** (os 6 = exatamente as sondas que AFIRMAVAM os defeitos fechados) · 4 sondas novas
  passed · md5 das fontes antes/depois conferido. Ativação sem o 9º dígito: declarado `+5521987650003`, ATIVAR de `+552187650003` →
  verificado (o "oi" seguinte roda na corretora certa).
- Mutações da régua: número NÃO verificado atendido · código usado 2× · código de A vincula B · mensagem do ATENDIMENTO ou do QCM cai
  no assistente · fromMe/grupo responde · membro de duas corretoras recebe dado da outra — + as do conserto (portão aberto com o banco
  instável, saída para instância do produto com controle U1 → 1 envio, código vazado de outro celular).
- §9.1: ver o relatório da 132-A §5 (mesmo HEAD; `/api/versao` 200).

## 6. Canário e rollout
**Nasce DESLIGADO.** Ligar (T-171): chip novo → Admin → Canais: AutoBrokers — assistente dos corretores → QR → `ATALHO_WHATSAPP_LIGADO=1`
no `smith-api` → cada corretor declara o número no Meu perfil → "Usar pelo WhatsApp" → manda o ATIVAR. Canário: uma conversa real com
o número do gerente; medir o LID do WhatsApp real.

## 7. Gate da SPEC
juiz **84** (1 blocker: o portão do assistente falhava ABERTO quando o banco não lia o tipo da empresa — a mensagem de número NÃO
verificado chegava ao `observer_tap`) + o P1 promovido ‖ red team **82 QUEBREI** (1: a volta da cotação mandava mensagem à LINHA de
atendimento de uma corretora, robô → robô) → **conserto único** (portão fechado; anti-laço na saída; código amarrado ao número
declarado; teto global; teto de envios por dia; "qual corretora?" uma vez; estado sem Redis; corte de 8000 caracteres) → **confirmação
88** (3/3; N1 aberto) → conserto do gerente `ce32e89` (N1). Push: na resposta ao Founder.

## 8. Mudanças além do texto da SPEC (CHANGE-ADDENDA 14/10)
ESSENCIAL: a conversa do atalho FORA da Fila de atendimentos (`lib/atendimento/casos.ts`, `de42bed`) — a SPEC falava da Central; a Fila
mostraria a conversa privada do corretor à equipe. ESSENCIAL: o canal `whatsapp_assistente` (D-132C-05) em vez de `whatsapp`.

## 9. Decisões
SPEC §7: **D-132C-01** um número da plataforma para todos (88) · **D-132C-02** verificação por posse (90) · **D-132C-03** desconhecido
= silêncio (85) · **D-132C-04** o mesmo CORE e a mesma conversa (92). Da execução: **D-132C-05** `channel='whatsapp_assistente'`
(88 × reusar `whatsapp` 35).

## 10. Riscos remanescentes (INFERÊNCIA)
- **Um número só para todas as corretoras:** se ele for banido, o atalho cai para todas (os tetos de envio existem para isso).
- **Evolution GO real** não exercitado: o formato do LID e do `SenderAlt` ao vivo, o Redis real (sem ele o dedup do webhook é pulado e a
  reentrega responderia 2×), a corrida do índice único no banco real.
- O limite de 240/min por IP do webhook GO vale para o mesmo servidor Evolution de todas as linhas: o assistente compete com o
  atendimento.
- Prompt injection no modelo real pelo WhatsApp não foi medida (a superfície é a mesma do chat do painel).

### 10.1 📋 CAIXA DO FOUNDER (detalhe em `TAREFAS-DO-FOUNDER.md`)
T-166 Implantar os 4 juntos · **T-171** o número do AutoBrokers: chip novo → QR → variável → cada corretor declara e ativa.

### 10.2 Pendências novas → `PENDENCIAS.md` P-132C-01…10
dedupe do webhook sem Redis · o corretor cujo número é a linha da corretora não recebe explicação · limpeza de
`whatsapp_atalho_tentativas`/`_estado` · guarda da trava por telefone · 240/min por IP · dígitos unicode no ATIVAR · LID real não
medido · canário real depois do QR · teto de envios × teto de turnos · (a Fila mostrava a conversa do atalho → ✅ consertado em `de42bed`, registrado fechado).

## 11. Impacto para o corretor
Salva "AutoBrokers" nos contatos, toca "Usar pelo WhatsApp" no perfil, manda a mensagem pronta — e daí em diante fala com o mesmo
AutoBrokers do painel pelo WhatsApp: pede uma cotação por áudio na rua, manda a foto da apólice, e recebe o resumo e o link da
apresentação ali mesmo. A conversa é dele: não aparece na Fila da equipe.

## 12. Declaração de integridade
Nenhum motor paralelo (CLAUDE.md §5): o turno é o `/chat/stream` (em processo), o leitor de anexo é o da 132-A, o envio é a instância
Evolution GO, o pareamento é o `pairing_orchestrator` que já existia (só aceita `assistente` na plataforma). O número de ATENDIMENTO e o
do QCM não mudaram (📊 `test_spec133a_o_fio` 17/17; o diff do `webhook.py` é um hunk só, o desvio do assistente). Nenhum segredo,
código ou telefone em claro em log (red team G1). Isolamento com duas corretoras e membro em duas.

## 13. ROLLBACK
Desligar sem reverter: tirar `ATALHO_WHATSAPP_LIGADO` do `smith-api` (o desvio só conta e cala; 📊 sonda A8: `atalho_desligado`,
0 envios). Código: `git revert` dos commits do §2. Banco: ROLLBACK da `_05` e da `_03` (nos arquivos; derrubam tabelas → índice →
CHECK → coluna, na ordem; o código cala sem elas).

## 📊 A BATERIA — quantas vezes ela rodou nesta SPEC
PENDENTE — o gerente preenche (a rodada inteira das três SPECs, em `scratchpad/bat132`, ainda roda).

## §11 A TELEMETRIA (`python backend/scripts/medir_execucao_claude_code.py --sessao atual`, rodado da raiz, 14/10 ~09:49 BRT, horários em UTC)
```
EXECUTOR (a sessão inteira, 132-A+B+C)     14/10 05:20  445 min  turnos 210  pico 634k  US$ 54.48  opus-5-5
  Builder C1 verificação WhatsApp          14/10 05:59   98 min  turnos  86  pico 237k  US$  8.74  opus-5-5
  Builder C2 o atalho WhatsApp             14/10 07:46   36 min  turnos  83  pico 311k  US$ 10.38  opus-5-5
  Builder C3 costura do atalho             14/10 08:23   73 min  turnos  97  pico 304k  US$ 11.88  opus-5-5
  Juiz da SPEC-132-C                       14/10 09:38   27 min  turnos  76  pico 271k  US$  9.10  opus-5-5
  Red team da SPEC-132-C                   14/10 09:38   32 min  turnos  46  pico 228k  US$  5.12  opus-5-5
  Conserto único da 132-C                  14/10 10:11   87 min  turnos 103  pico 368k  US$ 15.58  opus-5-5
  Confirmação 132-C                        14/10 11:37   47 min  turnos  31  pico 133k  US$  2.28  opus-5-5
  Bateria completa triada (as 3)           14/10 12:23   21 min  turnos  30  pico  94k  US$  1.61  opus-5-5
TOTAL da sessão: 32 agentes além do executor · turnos 2744 · ctx 649,4 M · US$ 386,25 (+ executor 54,48)
```
📊 Agentes da 132-C: US$ 63,08 (API-equivalente). Todos `opus-5-5`. Achados por mecanismo: o juiz (o portão que falhava aberto,
EXCLUSIVO; a Fila mostrando a conversa) · o red team (a saída sem anti-laço, EXCLUSIVO; o código não amarrado e sem teto global, também
do juiz) · a confirmação (N1, o teto global como interruptor, EXCLUSIVO). **API do produto:** 📊 0 chamadas pagas (dublês).

**Nota da execução: 86/100** (proposta pelo atualizador; o gerente fecha depois da bateria) — 3/3 blockers fechados com sondas que
viraram vermelhas e controle; QCM e atendimento intactos; desconta o Evolution real e o canário, que esperam o chip e o QR.
