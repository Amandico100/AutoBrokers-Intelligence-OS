# SPEC-EXTRA-001.7 — O PILOTO MEDIDO
## Três dias inteiros, uma régua por dia, e nenhuma nota por palpite

**Produto:** AutoBrokers Intelligence OS.
**Status:** PROPOSTA PARA CONVERSÃO, AQUECIMENTO E EXECUÇÃO — não é SPEC canônica aprovada nem implementação realizada.
**Versão:** 1.0 · **Data:** 13/09/2026.
**Baseline medida nesta redação:** worktree `AutoBrokers-FIX`, `HEAD = 70da0e9d67a7881ff58dcebc4b0c320e6e7ca725`, branch `docs/diagnostico-pilotos-0912`, 📊 `HEAD..origin/main = 0` e `origin/main..HEAD = 0` (13/09). O BLOCO 0 remede no dia da execução.
**Branch sugerida:** `feat/spec-extra-001-7-piloto-medido`.
**Research Pack:** `SPEC-EXTRA-001.7-o-piloto-medido-RESEARCH-PACK.md` · **Prompt:** `PROMPT-DE-ABERTURA-EXTRA-001.7.md`.
**SPEC definitiva a criar:** `docs/canon/specs/SPEC-EXTRA-001.7-o-piloto-medido.md` · **Relatório:** `docs/canon/reports/SPEC-EXTRA-001.7-EXECUTION-REPORT.md`.
**Origem:** `DIAGNOSTICO-PILOTOS-E-PLANO-EXTRA-2026-09-12.md` §0, §3 bloco 001.7, §7.5, §12.1 linha 8, §13.
**Protocolo:** AAA v11.2 + OPÇÃO B. Marcha **LEVE**, **1 juiz fresco** (fixada em §8 do diagnóstico, reafirmada em §13.4) — 🔴 e esse juiz é a **lente do DADO** (§0.3).
**Depende de** 001.1, 001.2, 001.3, 001.4 e 001.6 **no ar**. Sem elas a régua roda e imprime "não medido" em quase tudo — honesto e inútil.
**Pendências:** absorve P-PILOTO-06. Toca e devolve com o que destrava: P-PILOTO-11, P-PILOTO-18.

---

## 0. Resultado e motivo

> **Três dias inteiros com o agente ligado nas duas corretoras, uma régua publicada a cada dia, e as notas por dimensão deixando de ser palpite.** Esta SPEC não conserta o agente — as cinco anteriores fazem isso. Ela constrói o **instrumento** que diz se consertaram, e o **protocolo humano** que faz os três dias acontecerem sem ninguém desligar o produto no meio da tarde sem deixar registro.

### 0.1 O que aconteceu, e por que falta um instrumento

📊 Os testes de 09–11/09 duraram **~1h53 de agente ligado em três dias**: 5 segurados reais, **0 acionamentos com protocolo**, nenhuma linha de ledger de cobrança (diagnóstico §0). As notas que fecharam aquele diagnóstico — **atendimento 48** (apólice certa 50 · coleta e age 40 · aciona 25 · fala como humano 60 · sabe calar 45 · sabe pedir ajuda 55) e **chat 49** — saíram da leitura de auditores sobre um acervo de duas horas. São a melhor leitura possível daquele material; **não são medição**, e o diagnóstico as chama de palpite.

🔴 **E o número que abre o diagnóstico não é reconstruível.** 📊 Medido em 13/09 contra produção: não existe `agents.ligado_em`, `admin_audit_events` tem **0 linhas na vida inteira**, e `system_logs` no período tem 7 linhas, nenhuma de mudança de agente. O mais perto é a janela da primeira à última resposta — que **contradiz** o `desligado_em` gravado (📊 a corretora B respondeu até 19:04 do dia em que consta desligada às 11:46 local). *"1h53"* é inferência de auditor, não fato do banco.

| o diagnóstico afirma | a fonte permite reconstruir? |
|---|---|
| **0 acionamentos com protocolo** | ✅ **sim, por duas fontes** — 📊 `work_steps.step_type='dispatch_phase'` 5 no período, `output_summary->'captured'` vazio em 16 de 17 da vida; `platform_sends` com `kind` de protocolo: **1 na vida, em 19/08**, zero no período |
| **7 boletos repetidos nos dois dias** | ✅ **sim** — 📊 `platform_sends`: 14 no período, **7 em 10/09 e 7 em 11/09**, uma corretora só |
| **1h53 de agente ligado** | ⛔ **não** — sem evento de liga/desliga, sem auditoria administrativa |
| **5 segurados reais** | ⚠️ **em parte** — 📊 `observed_events` só tem `direction ∈ {in,out}`; `out` mistura agente e humano da corretora |

⚠️ **O elo, e ele é modesto de propósito:** *o piloto não mediu o produto **porque** o produto não escreve o que um piloto precisa ler.* A metade que já escreve (acionamento, cobrança, conversas) é medível hoje; a que falta tem dono nomeado nas SPECs irmãs, e a régua **nomeia o dono em vez de estimar o número**.

### 0.2 Decisões do Founder já incorporadas — não se reabrem

| decisão | como entra |
|---|---|
| **D-PILOTO-13** | Eficiência = a fórmula da 001.3 §8.4, com `motivo_classe` `incapacidade` × `regra` × `desconhecido`, e **sem publicar o número quando os desconhecidos passam do limite de fatia**. 🔴 A régua **importa** o cálculo; não tem fórmula própria (§7). |
| **D-PILOTO-14** | Marcha LEVE, ≤ 12 guardas — esta SPEC declara **6 arquivos**, metade do teto, porque quase tudo aqui é leitura. |
| **D-PILOTO-02** | A Regina responder pelo celular **pausa o agente naquela conversa, e isso é o desejado**. O cartão da §9.1 escreve isso para ela. |
| **D-PILOTO-18** | A rotina de cobrança só reativa depois do P0 da 001.6. A régua **lê**; não liga rotina nenhuma. |
| **D-PILOTO-20** | Execução em chat novo, AAA opção B, com a marcha do §8. |

### 0.3 EXECUTION CARD — proposto, a confirmar no BLOCO 0

```text
OUTCOME .......... 3 dias com o agente ligado nas duas corretoras, régua diária publicada
                   por corretora, e nota por dimensão que sai de contagem com fonte
                   nomeada — ou a palavra "não avaliada"
RISCO ............ 3 — ALCANCE 2 (a corretora: o cartão que a Regina lê e o relatório que
                   o Founder decide em cima) · REVERSIBILIDADE 0 (nada fica: dois scripts
                   read-only, dois eventos e documentos) · FREQUÊNCIA 1 (uma vez por dia)
SUPERFÍCIE ....... 1 — um comportamento (contar) em lugares que eu LISTO: a tabela de
                   FONTES do §6.2 nomeia, por métrica, tabela, coluna e escritor.
                   🔴 CONDICIONAL: se o BLOCO 0 não nomear o escritor de TODA linha,
                   a SUPERFÍCIE vira 2 e a marcha sobe para PADRÃO
PISO APLICADO .... NENHUM. Não envia · sem migration · não toca autenticação nem o filtro
                   company_id do produto · não lê de uma corretora para escrever noutra.
                   🔴 Se a conversão precisar de migration ou de envio, o piso CRÍTICO
                   da AAA §3.2 dispara e a marcha sobe — registra-se e sobe, não negocia
NÍVEL ............ LEVE — a soma (3) só concorda porque a SUPERFÍCIE é 1. ⚠️ RISCO 3
                   sozinho chamaria PADRÃO; a marcha LEVE está FIXADA em §8 do diagnóstico
JUIZ ............. 1 fresco, e ele é a LENTE DO DADO (AAA §5 ④): o outcome desta SPEC É um
                   número, então o juiz RECONSTRÓI a régua sobre o acervo com SQL próprio e
                   diz se ela mente. Nota: juiz-do-dado 90 × juiz genérico 65 ×
                   subir a PADRÃO por duas lentes 70 (não há diff que peça a segunda)
UNIDADES ......... 6 — A checklist · B régua · C eficiência importada · D publicação ·
                   E protocolo humano · F critério de saída
COESÃO ........... A e B compartilham a camada de leitura (regua_motor) → um dono, serial.
                   C consome B; D consome B e C. E e F são documento, disjuntos
PARALELISMO ...... dois escritores no máximo: {A,B,C,D backend} e {E,F documento}.
                   ⛔ nunca dois em backend/scripts/regua_motor.py
TIME ............. investigador+pesquisador (um) · builder · verificador mecânico ·
                   1 juiz fresco = lente do DADO. ⛔ sem painel, sem red team (§13.4)
REFERÊNCIA ....... interna: regua_0971.py (a régua que IMPORTA o motor) e rubrica.py (nota
                   determinística com portão anti-fraude). Externa: as 2 de §14
GATES ............ G-A1 … G-E1 da §11 · GUARDAS: 6 ARQUIVOS, 💭 ~22 asserções
O ELO ............ "o piloto não mediu o produto PORQUE o produto não escreve o que um
                   piloto precisa ler" — A medido (as notas de §0 vieram de leitura) ·
                   B medido (5 das 10 métricas têm ZERO escritores na vida do banco) ·
                   🔴 B CHEGA EM A: o BLOCO 0 prova, métrica a métrica, que é a ausência
                   do escritor que impede contar — não uma consulta mal escrita
RELÓGIO .......... 💭 3–5 h de código e documento + os 3 dias de calendário do piloto, que
                   não são relógio de execução. ORÇAMENTO: 💭 ≤ 600 k tokens
BLOCKER .......... pelo TESTE DO PRODUTO (AAA §2): A é BLOCKER (checklist que diz "pode
                   ligar" quando não pode manda o agente ao segurado sem destino de
                   suporte); B e C são BLOCKER (o relatório que o PRODUTO gera para a
                   corretora). D, E e F são documento: PENDÊNCIA
```

---

## 1. AUTORIZAÇÃO DE TESTES

| Alias em toda evidência | Valor |
|---|---|
| **TESTE-A** · **TESTE-B** | `[allowlist privada — nunca commitar]` |

⛔ Os números reais moram **só** no prompt privado do chat executor e no ambiente (`JANELA_SILENCIO_EXCECOES`). Nunca no canon, relatório, dossiê, fixture, log ou screenshot.

**Autorizado:** implementar os dois scripts e os seis guardas e rodá-los **contra produção em leitura**; consultas read-only para **contagens e agregações**; rodar o checklist num **ambiente de teste com a trava armada** (é o gate G-A1); publicar o relatório e a página do dossiê.

**Proibido:** (1) **ligar ou desligar o agente de qualquer corretora** — 🧑 ligar é ato do Founder (§16); o executor implementa o registro do gesto, não dá o gesto; (2) enviar qualquer mensagem, a quem for — ⛔ esta SPEC **não envia nada**, e é isso que mantém o piso da AAA §3.2 desarmado; (3) alterar configuração de corretora operacional (destino, canal, allowlist, janela, rotina); (4) escrever, apagar ou corrigir linha de produção — as únicas escritas novas são os dois eventos do §6.5, e nascem do gesto humano; (5) imprimir ou gravar CPF, CNPJ, telefone (inteiro **ou** últimos dígitos), nome, placa, e-mail, credencial ou conteúdo de mensagem; (6) **estimar um número que não tem escritor** — 🔴 a proibição central (§6.3).

**Antes de cada leitura de produção:** ambiente · conexão de leitura · consulta é agregação (`count`, `min`, `max`, `sum`, `group by`) e **não** `select` de texto livre · `company_id` no `where` ou no `group by`. 🔴 Consulta que traga `text`, `content`, `summary`, `message_human`, `phone` ou `output_full` **não roda** — nem "só para olhar".

**Ação física do Founder:** os três dias dependem dele (§16). ⛔ **Ausência do piloto nunca vira aprovação.** Se não couberem na execução, o executor entrega os instrumentos, roda a linha de controle sobre 09–11/09, e deixa o gate como **NÃO COMPROVADO** com o ato na Caixa do Founder.

---

## 2. Escopo e exclusões deliberadas

**Obrigatório:** (A) `backend/scripts/checklist_de_ligar.py` read-only, verde/vermelho **por corretora**, exit ≠ 0 no vermelho · (B) `backend/scripts/regua_do_piloto.py`, contagens por corretora e por dia, sem PII, com "não medido" de primeira classe e **linha de controle** sobre 09–11/09 · (C) eficiência **importada** da 001.3 · (D) publicação em `reports/` e no dossiê · (E) protocolo de operação escrito · (F) critério de saída com régua de nota · e os **dois escritores mínimos** do §6.5.

| o que sai | por quê | quando volta |
|---|---|---|
| **Rotina do produto rodando a régua às 19h30** | 💭 mais uma peça de agendamento para um evento de 3 dias; o `routine_engine` já existe e é onde ela penduraria. Nota: comando por dia **85** × Rotina **45** × cron no EasyPanel **60** | quando o piloto virar operação contínua |
| **Painel de métricas na tela** | aqui é arquivo e dossiê; tela é a 097 | 097, com a régua como fonte |
| **`company_id` na Central de Agentes** | 📊 `central_de_agentes.py:636` diz, escrito, que é agregado de plataforma sem dado por corretora. Recortá-la é mudar a SPEC-088 | SPEC-088.1, se e quando |
| **Backfill do que não foi gravado em 09–11/09** | não há fonte; inventar é o defeito que esta SPEC existe para impedir | nunca |
| **Nota do chat como gate de saída** | o chat é território da 001.1 | 001.1 |

---

## 3. Autoridades preservadas — nenhum motor paralelo

🔴 **Esta SPEC não cria motor: cria dois clientes de motores existentes.** Conferido em 13/09:

| peça | arquivo:linha | o que se faz com ela |
|---|---|---|
| **camada única de import do motor** | `backend/scripts/regua_motor.py:180-184` (`supabase()`), `:168-178` (`tem_banco()`), `:220-250` (paginação de `observed_events`) | 🔴 os dois scripts **importam daqui**. ⛔ Nenhum abre cliente Supabase próprio — regra que o arquivo declara (SPEC-083 §5.4) |
| **a régua que chama o motor** | `backend/scripts/regua_0971.py:1-30` | referência de **forma**: sem LLM, determinística, `--fixture`, guarda provando a identidade do objeto importado |
| **nota determinística por eixo** | `backend/scripts/rubrica.py:1-30` | referência de **forma** do §10: âncoras explícitas, portão contra ponto por declaração |
| **o que aconteceu ontem, por corretora** | `backend/app/services/o_dia_de_ontem.py:207-215` (conversas), `:501-507` (`work_events` por `company_id` + `event_type`) | a régua **importa**; ⛔ não reconta conversas do zero sobre `messages` |
| **os estados da Central** | `backend/app/core/central_de_agentes.py:53` — `SAUDAVEL · PULSA_SEM_PRODUZIR · DESLIGADO · PARADO · NAO_MEDIDO` | 🔴 **`NAO_MEDIDO` já é estado de primeira classe do produto.** A régua usa a mesma palavra com o mesmo sentido |
| **`/health` da API** | `backend/app/main.py:924`, `:489` (`_sinais_do_codigo`), `:697-698`, `:715-717`, `:731-737`, `:980-986` | o checklist **lê**; ⛔ não reimplementa verificação que já esteja lá |
| **conferidor do que está no ar** | `backend/scripts/conferir_o_que_esta_no_ar.py:46`, `:75` (exit 0/1/2) | o checklist **chama** e adota a mesma convenção de saída |
| **registro de ato do agente** | `backend/app/services/dispatch_router.py:997`; chamadores `:2967`, `:3057` | os dois eventos do §6.5 usam **este** helper. ⛔ Nenhuma função nova de gravação |
| **contador de envios** | `backend/app/services/platform_outbound.py:301-312` (`_record_send_sync` → `platform_sends`) | a régua **lê** `kind`; ⛔ não cria tabela de métrica |
| **régua de língua humana** | `backend/tests/test_o_caso_se_explica_sozinho.py` (`problemas_de_lingua`) | fonte da dimensão *fala como humano* (§10.1) |

⚠️ **Fronteira com a 001.3:** ela é dona de `grupo.*`, `motivo_classe`, do resumo das 19h e da fórmula de eficiência. Esta SPEC **lê** e **não escreve** nada disso. Se a 001.3 não estiver no ar, a régua imprime `NÃO MEDIDO` nessas linhas e nomeia a dona — comportamento correto, não falha.

---

## 4. BLOCO 0 — converter medindo

🔴 **Este documento envelhece.** Todo número tem data; o executor remede e **o número dele vence** (AAA §5 ①).

1. **Preflight Git** (CLAUDE.md §2), com as duas contagens. `HEAD` no relatório.
2. **Quais SPECs irmãs estão no ar** — 001.1, 001.2, 001.3, 001.4, 001.6: na `main`? implantadas? 🔴 A resposta muda quantas linhas da tabela de FONTES saem `NÃO MEDIDO`, e é a primeira coisa do relatório.
3. **Remedir a tabela de FONTES (§6.2) linha a linha**, com o comando ao lado (AAA §0.4): tabela existe? coluna existe? **quantas linhas na vida inteira?** Zero na vida = sem escritor.
4. **Conferir o literal do `kind`.** ⚠️ A leitura do banco em 13/09 devolveu `kind='billing'`; `backend/app/services/billing_collection.py:43` declara a constante usada no `record_platform_send`. Uma régua que filtra pelo literal errado conta zero e parece verdade. `select kind, count(*) from platform_sends group by 1`, e **o literal medido vai para o script** com o comando no comentário.
5. **Fixar o relógio.** 📊 `observed_events` no período tem **4.083** linhas por `created_at` e **243** por `wa_timestamp` — 17×. A régua declara qual usa, por métrica; G-B2 congela a escolha.
6. **Mapear os apelidos.** 📊 5 companies: A=`04b5cdbc…`, B=`6c9c55e2…`, C=`3aa75902…` e duas técnicas. ⚠️ `C` é a que `regua_motor.py:287` exclui como `_AMANDUS_COMPANY_ID` — **e é a única com destino de suporte ativo**. Confirmar qual é qual **antes** de escrever o relatório.
7. **Reproduzir a linha de controle (§6.4)** antes de escrever o BLOCO B inteiro. Se os números não voltarem, o defeito é da consulta, não da fonte.
8. **Medir o buraco do `motivo_classe`** como a 001.3 §4 manda — é o que diz se a régua consegue publicar eficiência de algum dia.
9. **Conferir se `PORTAL_EFEITO_MATERIAL_LIBERADO` já aparece em algum `/health`.** 📊 Em 13/09 não aparecia: a env é lida só em `backend/portal_worker/journeys/__init__.py:291`, portão em `:302`. Se outra SPEC já a expôs, o §6.5b some.

**O que pode estar vencido — corrija sem hesitar:** um inventário desta redação apontou `dispatch_router.py:2476/:2566` como chamadores de `registrar_ato_do_agente`; 🔴 **conferi: os reais são `:2967` e `:3057`** — confira de novo. · O diagnóstico §1.7 diz *"2 execuções"* da cobrança; 📊 13/09 devolveu **2 `ok` em 10/09 e 2 em 11/09** em `routine_runs` — **conferir por `routine_id` antes de citar**. · `grupo.calado` é citado como evento existente e 📊 **não existe**: hoje o silêncio da janela vira linha de feed (`o_fim_do_atendimento.py:1411`, decidido em `:1325`). Quem cria o evento é a 001.3.

---

## 5. BLOCO A — o checklist de ligar

```bash
cd backend
PYTHONIOENCODING=utf-8 python scripts/checklist_de_ligar.py --corretora <slug|id>
PYTHONIOENCODING=utf-8 python scripts/checklist_de_ligar.py --todas
```

Uma linha por item, `[ok]` / `[FALHOU]`, mais um `VEREDITO`. **Exit 0** só se tudo verde; **1** no vermelho; **2** se a corretora não existe — a convenção de `conferir_o_que_esta_no_ar.py:75-80`.

🔴 A régua de um checklist é a do Google SRE (§18 E02): *"a importância de cada pergunta tem de ser substanciada, idealmente por um desastre de lançamento anterior."* **Item sem desastre atrás não entra.**

| # | item | onde se lê | o desastre que o justifica |
|---|---|---|---|
| **C1** | `/health` responde e o **freio** está no estado esperado | `main.py:697-698` (`acionamento_env_aberta`, `freio_de_emergencia_armado`) | ligar com o freio em estado desconhecido é acionar sem saber |
| **C2** | `finalize` e **allowlist** no modo do piloto | `main.py:715-717`, `:731-732` | ⚠️ **`allowlist_descartes` NÃO é critério**: `main.py:733-736` diz, escrito, que o contador é **por processo** e `0` não significa "nada foi barrado" — usá-lo daria verde falso |
| **C3** | **destino de suporte ativo para ESTA corretora** | `main.py:980-986` (`corretoras_ligadas_sem_destino_de_suporte`) | 📊 **4 destinos, 1 ativo, e o ativo é o da corretora de teste** (`3aa75902…`): as duas do piloto sem destino, um pedido de ajuda não chegaria a ninguém. 🔴 **`None` é VERMELHO**, nunca verde — `main.py:984-986` devolve `None` no erro de propósito |
| **C4** | **canal conectado** | estado da conexão de WhatsApp da corretora | 📊 o teste da Resulta em 10/09 terminou com *"WhatsApp desconectado"* |
| **C5** | **números da casa cadastrados** (001.3) | tabela de números internos | 📊 130 conversas viraram `HUMAN_REQUESTED` por captura dos celulares da equipe |
| **C6** | **exceções da janela são só de teste** | env `JANELA_SILENCIO_EXCECOES` (`o_fim_do_atendimento.py:1293`) | a lista existe para os dois números do Founder; um número de segurado ali **fura a janela de silêncio de um cliente real**. 🔴 Item do gate G-A1 |
| **C7** | **agente `attendance` ativo** | `agents.agent_role='attendance'` + `is_active` | 📊 4 agentes `attendance`, **`is_active=false` nos 4** em 13/09: ligar seria um botão que não liga nada |
| **C8** | **o que está no ar é o do repositório** | `conferir_o_que_esta_no_ar.py:46-72` (`code_fingerprint`) | 📊 quatro reimplantações do mesmo commit, todas verdes na tela (CLAUDE.md §2) |
| **C9** | **os escritores da régua existem** | a tabela de FONTES (§6.2), contando linhas na vida | medir três dias e descobrir no quarto que metade não gravou nada |

⚠️ **C9 não bloqueia o ligar**: imprime **AMARELO** e lista, nominalmente, o que a régua não vai conseguir medir naqueles três dias — informação para o Founder decidir se vale ligar assim.

⛔ O checklist não liga nada, não corrige nada, não envia nada, e **não imprime número de telefone nem os últimos dígitos**: o item de canal diz *"conectado"* ou *"desconectado"*, nunca qual número. **GATE A (G-A1).**

---

## 6. BLOCO B — a régua diária

```bash
cd backend
PYTHONIOENCODING=utf-8 python scripts/regua_do_piloto.py --corretora <slug|id> --dia 2026-09-22
PYTHONIOENCODING=utf-8 python scripts/regua_do_piloto.py --todas --de 2026-09-09 --ate 2026-09-11
PYTHONIOENCODING=utf-8 python scripts/regua_do_piloto.py --explicar-fontes
PYTHONIOENCODING=utf-8 python scripts/regua_do_piloto.py --fixture      # sem banco
```

Markdown (padrão) ou `--formato json`. Uma tabela por corretora por dia. 🔴 **Só contagens.**

### 6.1 As dez linhas

| # | linha | o que conta |
|---|---|---|
| 1 | **minutos com o agente ligado** | soma dos intervalos `agente.ligado → agente.desligado` do dia (§6.5a) |
| 2 | **conversas atendidas pelo agente** | conversas com ao menos uma resposta do agente e sem humano conduzindo |
| 3 | **rajadas → respostas** | rajadas (≥2 mensagens do segurado em ≤30 s) e quantas respostas cada uma gerou (001.2) |
| 4 | **apólice certa em 1 rodada** | turnos de apólice com origem escrita, vigente do ramo, sem desambiguação (001.1) |
| 5 | **acionamentos com mensagem ao segurado** | protocolo, link ou agendamento enviado (001.4) |
| 6 | **sinistros com dossiê** | coleta inicial feita e dossiê entregue (001.3) |
| 7 | **ajudas por `motivo_classe`** | `incapacidade` · `regra` · `desconhecido` (001.3) |
| 8 | **mensagens ao grupo por tipo, e `grupo.calado`** | os quatro modelos da 001.3, mais o que a guarda calou |
| 9 | **silêncios por motivo** | janela · pausa por intervenção · número da casa (001.2/001.3) |
| 10 | **cobrança** | enviadas · retidas · **repetidas (meta: 0)** · portais que entraram (001.6) |

E uma derivada: **eficiência do dia** (§7).

### 6.2 A tabela de FONTES — o coração desta SPEC

🔴 **Cada linha declara, no código, de onde vem e quem escreve.** `--explicar-fontes` imprime esta tabela, e é ela que o juiz do dado reconstrói.

| # | tabela · coluna | escritor | 📊 estado em 13/09 |
|---|---|---|---|
| 1 | `work_events.event_type ∈ {agente.ligado, agente.desligado}` | **esta SPEC** (§6.5a) | ⛔ não existe |
| 2 | `conversations.status` + `messages.role` | existe | ✅ 📊 110 conversas no período (49 `open/whatsapp`, 48 `HUMAN_REQUESTED`) |
| 3 | `messages.created_at` (janela de 30 s) | existe, derivável | ⚠️ derivável; 001.2 dá a marca explícita |
| 4 | `messages.payload->'turn'` (origem da apólice) | **001.1** | ⛔ 📊 **81 turnos com a chave em toda a vida**; `finish_reason` em **4**, todas de 10/09 |
| 5 | `work_steps.step_type='dispatch_phase'` + `platform_sends.kind` de protocolo | existe; **001.4** completa | ⚠️ 📊 17 na vida, 5 no período; `captured` vazio em 16 de 17 |
| 6 | `work_runs.outcome_type='claims.shadow'` + dossiê ao grupo | **001.3** | ⚠️ 📊 3 no período; o dossiê não é contado |
| 7 | `work_events.payload_redacted.motivo_classe` | **001.3** | ⛔ 📊 `grep -rn "motivo_classe" backend/app` = 0 |
| 8 | `platform_sends.kind` de grupo + `work_events` `grupo.calado` | **001.3** | ⛔ 📊 `grupo.*` = **0 na vida**; `platform_sends` não tem `destination_id` |
| 9 | `work_events` de silêncio | **001.2/001.3** | ⛔ 📊 hoje só vira linha de feed (`o_fim_do_atendimento.py:1411`) |
| 10 | `billing_sent_log` + `platform_sends.kind` de cobrança | **001.6** | ⚠️ 📊 `billing_sent_log` = **0 na vida**; `platform_sends` conta 14 no período |

### 6.3 🔴 A regra que governa o script: "não medido" nunca é zero

```
a tabela existe?  a coluna existe?  há linha na VIDA inteira?
   não a qualquer uma   →   NÃO MEDIDO (escritor: <SPEC> · <tabela.coluna>)
   sim às três, e o dia deu zero   →   0
```

⚠️ **Zero e "não medido" contam histórias opostas.** *Zero acionamentos* é um dia ruim; *acionamentos não medidos* é um instrumento cego. Trocar um pelo outro publica um fracasso que não houve, ou esconde um que houve. É o princípio do `absent()` do Prometheus (§18 E01), e a palavra é a que o produto já usa: `NAO_MEDIDO` (`central_de_agentes.py:53`). **GATE B1 (G-B1).**

### 6.4 A linha de controle — 09 a 11/09

> CLAUDE.md §9.2: *"a linha de controle é o que dá direito à conclusão."* Uma régua que só roda para a frente não tem como estar errada.

`--todas --de 2026-09-09 --ate 2026-09-11` tem de devolver, sem ajuste manual:

| o que | 📊 esperado (medido em 13/09) |
|---|---|
| acionamentos com protocolo | **0** nos três dias |
| envios de cobrança | **14** — 7 em 10/09, 7 em 11/09, uma corretora só |
| linhas de `billing_sent_log` | **0** |
| minutos com o agente ligado | **NÃO MEDIDO** — 🔴 *"a fonte não permite: não há evento de liga/desliga antes desta SPEC; `admin_audit_events` tem 0 linhas"* |
| eficiência do dia | **NÃO MEDIDO** — sem `motivo_classe` |

🔴 **O quarto e o quinto valem tanto quanto os três primeiros.** Uma régua que devolvesse "1h53" para 09/09 estaria inventando, e G-B2 fica vermelho se ela devolver qualquer número ali. **GATE B2 (G-B2).**

### 6.5 Os dois escritores mínimos — o único código de produto

**a) `agente.ligado` / `agente.desligado` em `work_events`.** No ponto único onde `agents.is_active` é alternado, chamar o helper que já existe (`dispatch_router.py:997`) com `company_id`, o ator e o motivo quando houver. ⛔ Sem tabela nova, sem migration: `work_events` já tem `event_type`, `actor_type`, `payload_redacted`.

> **Por que é obrigatório:** sem isso, *"3 dias inteiros com o agente ligado"* é a afirmação de alguém, e o próximo diagnóstico repete o que este viveu. 📊 Hoje só existe `agents.desligado_em`, e ele **contradiz** o acervo (§0.1). Nota: evento no ponto do gesto **88** × inferir pela janela de mensagens **35** × não medir **20**.

**b) `efeito_material_liberado` no `/health` do portal-worker.** Chave booleana em `backend/portal_worker/main.py:115-149`, lendo o mesmo `_ENV_EFEITO_MATERIAL` de `journeys/__init__.py:291`. 📊 Hoje o freio material **não é observável de fora de nenhum `/health`** — o checklist não consegue dizer se ele está armado, e "não consigo ver o freio" é vermelho, não verde.

⚠️ Os dois somam 💭 ~25 linhas de produto. Se qualquer um exigir migration, **o piso CRÍTICO da AAA §3.2 dispara** e a marcha sobe.

---

## 7. BLOCO C — a eficiência é a da 001.3, e ninguém a reescreve

```
             acionamentos com mensagem ao segurado  +  sinistros com dossiê
eficiência = ────────────────────────────────────────────────────────────────
                     os mesmos  +  ajudas com motivo_classe = 'incapacidade'
```

🔴 **As quatro regras que vêm junto e não se renegociam:** `regra` fora do denominador · `desconhecido` fora dos **dois**, com linha própria · denominador zero é *"sem acionamentos hoje"*, **não 0%** · acima do limite de fatia de desconhecidos a régua **não publica** o número e escreve *"ainda não dá para medir: N de M pedidos de ajuda saíram sem motivo"*.

⚠️ Sem a 001.3 no ar, a linha sai `NÃO MEDIDO (escritor: EXTRA-001.3 · work_events.payload_redacted.motivo_classe)` — a régua **não** improvisa fórmula de transição.

> 🔴 **Por que importar e não copiar:** duas cópias divergem no dia em que uma muda, e o grupo lê 85% às 19h enquanto o dossiê lê 78% às 19h30 — e ninguém sabe qual é o produto. É o defeito que `backend/scripts/regua_0971.py:15-22` documenta: *"um classificador próprio aqui mediria o classificador próprio, e não o produto."* Nota: importar **95** × copiar **20**. **GATE C (G-C1).**

---

## 8. BLOCO D — publicação

1. **Um arquivo por dia:** `docs/canon/reports/PILOTO-MEDIDO-<AAAA-MM-DD>.md`, gerado pelo script (`--publicar`): a tabela das dez linhas por corretora · a eficiência (ou o motivo de não publicar) · as notas do §10 · uma seção **Relatos** que o Founder preenche com o que a Regina e a Saionara mandaram (§9) · e o comando exato que produziu o arquivo, no rodapé (AAA §0.4).
2. **O consolidado:** `docs/canon/reports/PILOTO-MEDIDO-CONSOLIDADO.md`, três dias lado a lado e a decisão do §10.2.
3. **O dossiê:** a página `#pilotos` (`docs/canon/reports/dossies/dossies-autobrokers.html`, seção `p-pilotos`, linhas 996–1161) ganha um bloco **"7 · O piloto medido"** com os KPIs do consolidado; os quatro KPIs de 09–11/09 viram a coluna "antes". 🔴 **Republicar o artifact na URL existente** (`https://claude.ai/code/artifact/afe1510d-f31c-4d13-9441-aa920ad2b868`), nunca criar outro.
4. ⛔ **Nada do que o script imprime passa por edição manual antes de ir ao arquivo.** "Automática" quer dizer exatamente isto: ninguém digita número.

---

## 9. BLOCO E — o protocolo dos três dias

### 9.1 O cartão da Regina e da Saionara (💭 copy proposta)

```text
O AGENTE ESTÁ LIGADO — 22, 23 e 24/09, das 8h às 19h

✅ Se você responder pelo celular numa conversa, o agente CALA naquela conversa
   e não volta sozinho. É de propósito: a última palavra é sua.
   Se quiser que ele volte ali, peça ao Amandus — hoje não há comando para
   religar, e a gente prefere avisar a fingir que tem.

✅ Se algo sair errado, mande no grupo uma mensagem começando com  #erro
   e diga em UMA frase o que aconteceu. Exemplo:
   "#erro o robô mandou a apólice da residência para quem perguntou do carro"
   ⛔ Não cole CPF, telefone nem nome. Para apontar a conversa, diga só a hora.

⛔ O que atrapalha a medição:
   · desligar o agente sem avisar  (foi o que encerrou o teste de 10/09 às 14:54)
   · mudar configuração no meio do dia
   · usar um número da casa para testar — ele está na lista e o agente não responde

🔴 O agente errar é o que estamos medindo. Erro reportado vale mais que dia calmo.
```

### 9.2 O cartão do Founder — quando desligar

**Desliga na hora, qualquer um basta:** (1) mensagem a um segurado com dado de **outro** segurado, ou identidade trocada — é P0, CLAUDE.md §10 (4); (2) acionamento aberto sem o segurado pedir; (3) mais de 💭 6 mensagens ao grupo em uma hora sobre a **mesma** conversa (o padrão medido de 10/09 foi 7 em 75,7 min); (4) canal caído sem voltar em 💭 15 min; (5) qualquer envio a número que não é do piloto.

🔴 **E desligar é um ato registrado:** o gesto grava `agente.desligado` com motivo (§6.5a) e o motivo vira linha do relatório do dia. ⚠️ *Desligar sem registro é o que tornou "1h53" impossível de reconstruir.*

### 9.3 O ritmo

| quando | quem | o quê |
|---|---|---|
| véspera, fim da tarde | 🤖 | `checklist_de_ligar.py --todas` → verde, ou a lista do que falta |
| dia, 8h | 🧑 Founder | liga o agente nas duas corretoras |
| dia, 19h | produto (001.3) | o resumo das 19h chega ao grupo |
| dia, 19h30 | 🤖 | `regua_do_piloto.py --todas --dia <hoje> --publicar` + colar os `#erro` em Relatos |
| dia, fim | 🤖 | P-PILOTO-06: `gerar_corpus_de_telas.py --todas` → `medir_rota.py --todas --com-espelho --formato markdown` → `roteiro_de_coleta.py` |
| 4º dia | 🤖 + 🧑 | consolidado, notas do §10, dossiê, decisão |

---

## 10. BLOCO F — o critério de saída

### 10.1 A régua de cada dimensão

A partir do valor medido `x` e de duas âncoras declaradas (`x60`, `x90`):

```
x ≥ x60 :  nota = 60 + 30 × (x − x60) / (x90 − x60)      presa em [0, 100]
x < x60 :  nota = 60 × x / x60
```

🔴 **Dimensão cuja fonte saiu `NÃO MEDIDO` não recebe nota: recebe `NÃO AVALIADA`** — a regra do protocolo §7 escrita ao contrário (*sem referência inspecionável, a dimensão é "não avaliada", nunca "aprovada"*).

| dimensão (nota de §0) | `x` medido | `x60` | `x90` | fonte / dona |
|---|---|---|---|---|
| **apólice certa** (50) | % de perguntas de apólice respondidas na 1ª rodada, da vigente do ramo, com origem escrita | 60 % | 90 % | linha 4 · 001.1 |
| **coleta e age** (40) | % de rajadas que viraram **uma** resposta | 60 % | 95 % | linha 3 · 001.2 |
| **aciona** (25) | % de acionamentos que terminaram com mensagem ao segurado | 50 % | 85 % | linha 5 · 001.4 |
| **fala como humano** (60) | achados de `problemas_de_lingua` no dia (invertido) | 4 | 0 | régua de língua · 001.3 |
| **sabe calar** (45) | mensagens ao grupo sobre conversa com humano + respostas a número da casa (invertido) | 3 | 0 | linhas 8 e 9 · 001.3 |
| **sabe pedir ajuda** (55) | % de pedidos com `motivo_classe` ≠ `desconhecido` | 70 % | 95 % | linha 7 · 001.3 |

⚠️ **O chat principal** (apólice certa 35 · uma rodada 25 · completude 45 · confiabilidade 80 · velocidade 60) é medido pela mesma régua sobre `messages.payload->'turn'` e **publicado**, mas 🔴 **não decide a saída**: ele é o gate da 001.1, e duas SPECs decidindo pelo mesmo número é como nasce o desacordo.

### 10.2 A decisão

```
as 6 AVALIADAS · nenhuma < 60 · média ≥ 75   →  segue para EXTRA-002 (Agger)
alguma < 60                                  →  abre correção na SPEC DONA da dimensão
alguma NÃO AVALIADA                          →  o piloto NÃO mediu. A SPEC dona da fonte
                                                volta antes de repetir os 3 dias.
                                                ⛔ Nenhum número do dia entra no dossiê
                                                como nota
```

⚠️ **A comparação com 48 é ilustrativa, não aritmética.** As notas de §0 vieram de leitura qualitativa sobre 1h53; as desta régua, de contagem sobre 3 dias. 💭 *"subiu de 48 para 79"* compara duas coisas diferentes com o mesmo rótulo — o relatório escreve **"48 (leitura, 09–11/09) → 79 (medido, 22–24/09, 6 de 6 dimensões avaliadas)"**. **GATE F (G-E1).**

---

## 11. Guardas e mutações — 6 arquivos, metade do teto

| guarda | arquivo | o que prova (sobre o MOTOR e o ACERVO real) | a mutação que o deixa VERMELHO |
|---|---|---|---|
| **G-A1** | `test_o_checklist_de_ligar_fica_vermelho.py` | **Par de veredito oposto:** ambiente de teste com `JANELA_SILENCIO_EXCECOES` = só os dois aliases → C6 **verde**; com um terceiro número → C6 **vermelho** e `exit 1`. E `corretoras_ligadas_sem_destino_de_suporte = None` → C3 **vermelho** | fazer C6 aceitar qualquer número (o par perde o veredito oposto) → vermelho; tratar `None` como verde → vermelho |
| **G-B1** | `test_a_regua_diz_nao_medido.py` | **Par:** métrica com escritor e dia vazio → `0`; métrica sem escritor → `NÃO MEDIDO` com a SPEC dona nomeada. A afirmação é sobre a **saída renderizada**, não sobre função interna | trocar `NÃO MEDIDO` por `0` → o par colapsa → vermelho |
| **G-B2** | `test_a_regua_reproduz_o_piloto_de_setembro.py` | **Linha de controle** sobre o acervo: `--de 2026-09-09 --ate 2026-09-11` devolve 0 protocolos, 14 cobranças, 0 no ledger e **`NÃO MEDIDO` nos minutos ligados**. E a **prova de dois tenants**: soma por corretora = total, nenhuma linha da A na B | tirar o filtro `company_id` de uma consulta → a soma não bate → vermelho; devolver qualquer número nos minutos ligados de 09/09 → vermelho |
| **G-C1** | `test_a_eficiencia_da_regua_e_a_da_001_3.py` | A régua **importa** o cálculo da 001.3 — identidade do objeto por `is`, como `regua_0971.py` faz — e o número muda quando a classificação da 001.3 muda | copiar a fórmula para o script → o número deixa de mudar → vermelho; publicar eficiência com desconhecidos acima do limite → vermelho |
| **G-D1** | `test_o_piloto_medido_nao_vaza.py` | **Par:** a saída real dos dois scripts sobre o acervo passa por um detector de CPF/CNPJ/telefone/e-mail/placa; um texto de controle com telefone falso **é barrado** (prova que o detector dispara) | deixar `platform_sends.phone` chegar a uma linha da saída → vermelho |
| **G-E1** | `test_as_notas_tem_regua.py` | **Par:** dimensão com fonte medida → nota pela fórmula de âncoras; fonte `NÃO MEDIDO` → `NÃO AVALIADA`. E mudar a contagem de entrada muda a nota | dar nota a dimensão sem fonte → vermelho; fixar a nota num literal → a segunda asserção não muda → vermelho |

🔴 **Nenhum guarda reimplementa a regra que testa** (CLAUDE.md §9.4): todos chamam o script ou a função do produto e afirmam sobre a **saída**. ⛔ Proibido helper local que refaça a fórmula de eficiência ou a classificação de fonte.

---

## 12. Migrations, multi-tenant, canário

**Migrations: nenhuma.** `work_events` já tem `event_type`, `actor_type`, `severity`, `message_human`, `payload_redacted` (escritores em `backend/app/services/work/runs.py:325` e `dispatch_router.py:689`); os dois eventos do §6.5a são valores novos numa coluna existente, e o `/health` do portal-worker é um dicionário Python. 🔴 Se a conversão concluir que precisa de SQL, abre `docs/canon/MIGRATIONS-AUTHORITY.md` **antes da primeira linha**, escreve APPLY / VERIFY / ROLLBACK antes de rodar, e **sobe a marcha** (piso CRÍTICO da AAA §3.2).

**Multi-tenant — a prova, não a promessa.** (1) Os dois scripts exigem `--corretora` ou `--todas`: ⛔ não existe execução sem recorte. (2) **Toda** consulta tem `company_id` no `where` ou no `group by`; G-B2 prova por soma. (3) O relatório do dia é **um arquivo por corretora**, nunca as duas misturadas. (4) A corretora de teste (`3aa75902…`, o `_AMANDUS_COMPANY_ID` de `regua_motor.py:287`) aparece **nomeada** em `--todas`, nunca excluída em silêncio. (5) 🔴 O backend usa service role: **a RLS não protege contra um `where` esquecido** (CLAUDE.md §7) — a prova é o guarda, não a policy.

**Canário.** Esta SPEC não envia nada, então não há canário de envio. **Antes:** `checklist_de_ligar.py --todas` com tudo vermelho documentado (é o estado de 13/09), saída colada no relatório. **Casos:** (1) checklist em ambiente de teste com a trava armada → vermelho e `exit 1`; (2) o mesmo sem a trava → verde; (3) a régua sobre 09–11/09 reproduzindo a linha de controle; (4) a régua sobre um dia real das duas corretoras, com as linhas sem escritor saindo `NÃO MEDIDO`. **Depois:** os dois eventos do §6.5a aparecendo em `work_events` no primeiro liga/desliga real, com `company_id` certo.

🔴 **O que este canário NÃO prova: que o piloto aconteceu.** Os três dias são ato do Founder (§21). O executor prova que o **instrumento** funciona; o número vem depois, e o gate fica **NÃO COMPROVADO** até os três dias existirem. ⛔ Instrumento pronto nunca vira "piloto aprovado".

---

## 13. Validação, entrega e acompanhamento

O cartão da §9.1 é lido pela Regina e pela Saionara **antes do primeiro dia**, e o executor não fala com nenhuma das duas (§1): 🧑 quem entrega é o Founder. O que volta é emenda no cartão, não discussão de arquitetura. ⚠️ *"Como faço o agente voltar nesta conversa?"* já tem resposta escrita (hoje: não tem comando) e vira **pendência nomeada**, não remendo no meio do piloto.

```bash
git rev-list --count HEAD..origin/main     # 🔴 tem de ser 0
git rev-list --count origin/main..HEAD     # o que ainda não subiu
git merge-base --is-ancestor origin/main HEAD && git push origin HEAD:main
```

🔴 **Entregar não é commitar; é empurrar** (CLAUDE.md §2), com a saída do `push` colada no relatório. **Implantar:** `smith-api` (os dois eventos) e **`portal-worker`** (`efeito_material_liberado`); scripts e guardas não se implantam. **Env novas: nenhuma.** **Rollback:** reverter o commit — scripts são read-only e os eventos são aditivos. ⚠️ Não mexe em `app/`, `middleware.ts` nem `next.config.js`: o gate de rotas do CLAUDE.md §9.1 não se aplica; aplica-se **`/health` respondendo depois do deploy** — uma requisição, não um build verde.

**Documentação obrigatória:** relatório pelo template **abrindo com o EXECUTION CARD** · `ESTADO-DAS-SPECS.md` e `EXECUTION-MASTER-PLAN.md`, só as linhas afetadas · `PENDENCIAS.md`: **P-PILOTO-06 fecha** (§9.3) com a prova, **P-PILOTO-18 continua** com o que destrava (a linha 4 precisa das tool calls no turno), **P-PILOTO-11 continua** apontando para 001.6, e **toda métrica que terminar `NÃO MEDIDO` vira pendência com a SPEC dona nomeada** · `CHANGE-ADDENDA.md`: os dois escritores do §6.5 como **ESSENCIAL**, com problema, evidência e consequência · `FOUNDER-DECISIONS.md` se o Founder fixar datas ou mudar uma âncora do §10.1 · dossiê republicado na URL existente.

---

## 14. O que o estado da arte faz, e o que modelamos

> §13.4 do diagnóstico: pesquisa externa **só quando a SPEC introduz padrão novo**. Aqui são dois: *ausência não é zero* e *checklist de lançamento*. Duas fontes, reabertas em **13/09/2026**.

**E01 · Prometheus — `absent()` e `absent_over_time()`** · https://prometheus.io/docs/prometheus/latest/querying/functions/
*O que faz:* `absent()` devolve **vetor vazio** quando a série tem elementos e **um vetor de 1 elemento com valor 1** quando não tem; a doc diz que é *"útil para alertar quando nenhuma série temporal existe para um dado nome de métrica e combinação de rótulos"*.
*O que MODELAMOS:* a ausência é um **valor próprio**, alertável, distinto de zero — a regra do §6.3 e o estado `NAO_MEDIDO` do §6.2.
*O que REJEITAMOS:* a função e o modelo de séries temporais. Não há Prometheus aqui, e adotar um por dez contagens diárias seria motor paralelo (CLAUDE.md §5).
*Como o juiz inspeciona:* abre a doc, confere as duas frases, e roda a régua contra um dia sem escritor — a linha tem de dizer `NÃO MEDIDO`, não `0`.

**E02 · Google SRE Book, cap. 27 — "Reliable Product Launches at Scale"** · https://sre.google/sre-book/reliable-product-launches/
*O que faz:* descreve a Launch Coordination Checklist e a regra que a governa — *"a importância de cada pergunta tem de ser substanciada, idealmente por um desastre de lançamento anterior"* — e exige instrução concreta e executável.
*O que MODELAMOS:* a coluna *"o desastre que o justifica"* do §5 — 🔴 item sem falha medida atrás **não entra**; e a convergência para infraestrutura já endurecida, por isso C3 lê `corretoras_ligadas_sem_destino_de_suporte`, que já existe, em vez de refazer a conferência.
*O que REJEITAMOS:* o papel de Launch Coordination Engineer e a revisão semestral — uma equipe de uma pessoa e um piloto de três dias não sustentam nem um nem outro.
*Como o juiz inspeciona:* abre o capítulo e confere que **cada** um dos 9 itens do §5 aponta uma falha medida de 09–11/09.

---

## 15. O que saiu, dependências, e a fila

| saiu | gatilho de retorno |
|---|---|
| Rotina automática da régua | o piloto virar operação contínua |
| Métricas na tela | SPEC-097 |
| Central de Agentes por corretora | SPEC-088.1, se e quando |
| Nota do chat como critério de saída | 001.1 |
| Comando para religar o agente numa conversa pausada | pendência nomeada; decisão do Founder depois do piloto |

**Depende de** 001.1, 001.2, 001.3, 001.4 e 001.6 **no ar** — e a dependência é **verificável**: o BLOCO 0 passo 2 conta quantas das 10 linhas têm escritor. 💭 Com menos de 7 medíveis, o piloto mede pouco demais para valer três dias, e a recomendação ao Founder é adiar — **recomendação, não parada** (CLAUDE.md §10).

**Deixa para as seguintes:** a régua vira o **gate de aceite** de 001.10, 001.5 e 001.8 — as três passam a ter número de operação real em vez de teste verde. E o consolidado decide se a fila segue para **EXTRA-002 (Agger)**.

---

## 16. 📋 Caixa do Founder

1. **Ligar o agente nas duas corretoras**, nos três dias, das 8h às 19h. 🔴 Sem este ato nada disto mede coisa alguma.
2. **Escolher e fixar as três datas** (dias úteis consecutivos, depois de 001.1–001.4 e 001.6 implantadas).
3. **Ativar o destino de suporte de cada corretora** — 📊 hoje o único ativo é o da corretora de teste.
4. **Entregar o cartão da §9.1** à Regina e à Saionara e recolher o que voltar.
5. **Confirmar o nome do agente de cada corretora** antes do primeiro dia (D-PILOTO-12).
6. **Desligar quando um dos cinco critérios da §9.2 disparar** — e dizer o motivo, que vira linha do relatório.
7. Decidir, ao fim, a saída do §10.2.

---

## 17. Definição final de conclusão — lista fechada e verificável

1. ☐ `checklist_de_ligar.py` existe, roda por corretora, imprime os 9 itens e sai `0/1/2`.
2. ☐ G-A1 verde, **com a mutação executada** e a saída colada no relatório.
3. ☐ `regua_do_piloto.py` existe, roda por corretora e por dia, imprime as 10 linhas e `--explicar-fontes`.
4. ☐ **Toda** linha sem escritor sai `NÃO MEDIDO` com a SPEC dona nomeada — G-B1 verde com mutação.
5. ☐ **A linha de controle 09–11/09 reproduz** 0 protocolos, 14 cobranças, 0 no ledger e `NÃO MEDIDO` nos minutos ligados — G-B2 verde com mutação.
6. ☐ A eficiência é **importada** da 001.3, provada por identidade — G-C1 verde com mutação.
7. ☐ **PII zero** na saída dos dois scripts sobre o acervo real, com o par de controle — G-D1 verde com mutação.
8. ☐ As notas saem da fórmula de âncoras; fonte ausente vira `NÃO AVALIADA` — G-E1 verde com mutação.
9. ☐ Os dois escritores do §6.5 no ar, com `agente.ligado`/`agente.desligado` em `work_events` no primeiro gesto real.
10. ☐ **Prova de dois tenants**: soma por corretora = total, nenhuma linha cruzada.
11. ☐ Cartão da Regina/Saionara e cartão do Founder escritos, entregues e emendados com o que voltou.
12. ☐ Três dias realizados, com `PILOTO-MEDIDO-<data>.md` publicado em cada um — **ou** o gate registrado como **NÃO COMPROVADO** com o ato na Caixa do Founder.
13. ☐ Consolidado publicado, notas com o `x` medido ao lado, e a decisão do §10.2 escrita.
14. ☐ Dossiê `#pilotos` atualizado e **republicado na URL existente**.
15. ☐ Relatório com EXECUTION CARD, `git push` com a saída colada, pendências drenadas (P-PILOTO-06 fechada; 11 e 18 com o que destrava), e a declaração de que **nenhum motor paralelo foi criado**.
