# SPEC-EXTRA-001.3 — O GRUPO SÓ RECEBE O QUE IMPORTA
## Uma guarda, quatro mensagens, e todo envio contado

**Produto:** AutoBrokers Intelligence OS.
**Status:** PROPOSTA PARA CONVERSÃO, AQUECIMENTO E EXECUÇÃO — não é SPEC canônica aprovada nem implementação realizada.
**Versão:** 1.0 · **Data:** 13/09/2026.
**Baseline medida nesta redação:** worktree `AutoBrokers-FIX`, `HEAD = a0bb5fef440eba394a9275671b1143f5025807ef`, branch `docs/diagnostico-pilotos-0912`. O BLOCO 0 remede a revisão do dia da execução.
**Branch sugerida:** `feat/spec-extra-001-3-grupo-so-o-que-importa`.
**Destino desta proposta:** `docs/canon/specs-propostas/SPEC-EXTRA-001.3-o-grupo-so-recebe-o-que-importa.md`.
**SPEC definitiva a criar pelo Fable:** `docs/canon/specs/SPEC-EXTRA-001.3-o-grupo-so-recebe-o-que-importa.md`.
**Research Pack:** `SPEC-EXTRA-001.3-o-grupo-so-recebe-o-que-importa-RESEARCH-PACK.md`.
**Prompt de abertura:** `docs/canon/specs-propostas/PROMPT-DE-ABERTURA-EXTRA-001.3.md`.
**Relatório a criar durante a execução:** `docs/canon/reports/SPEC-EXTRA-001.3-EXECUTION-REPORT.md`.
**Origem:** `docs/canon/DIAGNOSTICO-PILOTOS-E-PLANO-EXTRA-2026-09-12.md` §1.5, §3 bloco 001.3, §7.2, §7.5, §12.1 linha 5.
**Protocolo:** AUTOBROKERS AAA v11.2 + OPÇÃO B. Marcha **CRÍTICO**, **3 juízes** (fixada em §8 do diagnóstico; não se rediscute).
**Pendências absorvidas:** P-PILOTO-02 · P-PILOTO-03 · P-PILOTO-04 · P-PILOTO-12. Tocadas de raspão e drenadas por reavaliação: P-PILOTO-10, P-PILOTO-13, P-PILOTO-15.

---

## 0. Resultado e motivo

> O grupo de suporte da corretora recebe **quatro coisas e mais nada**: um pedido de ajuda do agente, um sinistro novo, um atendimento concluído, e o resumo das 19h. Nunca recebe aviso sobre uma conversa que um humano da corretora já está conduzindo. Nunca recebe nada sobre um número da própria casa. Cada mensagem chega **inteira, em um balão**, com o WhatsApp do segurado clicável. E toda mensagem que sai para o grupo fica registrada, para que a pergunta *"quantas saíram ontem?"* tenha resposta.

### 0.1 O que aconteceu, medido

📊 **10/09/2026, 17:14:18 → 18:29:59 UTC — 7 mensagens ao grupo da Resulta em 75,7 minutos, todas sobre UMA conversa.** Reconstruído em 13/09 cruzando `agent_activities` e `work_events`:

| hora (UTC) | o que o grupo recebeu | origem no código |
|---|---|---|
| 17:14:18 | Dossiê — acionamento travou | `dispatch_watchdog.py:437` |
| 17:21:34 | Dossiê — acionamento travou | `dispatch_watchdog.py:437` |
| 17:35:57 | Dossiê — Allianz | `dispatch_router.py:3312` |
| 17:50:39 | WhatsApp de atendimento desconectado | `whatsapp/alerts.py:255` |
| 18:09:58 | ⏳ ESPERA VENCIDA (aviso 1 de 3) | `handoff_watchdog.py:568` |
| 18:19:58 | ⏳ ESPERA VENCIDA (aviso 2 de 3) | `handoff_watchdog.py:568` |
| 18:29:59 | ⏳ ESPERA VENCIDA (aviso 3 de 3) | `handoff_watchdog.py:568` |

```sql
-- 📊 o comando que produziu a tabela (13/09/2026, SUPABASE_DB_URL, read-only)
with t as (
  select created_at, title from agent_activities
   where created_at >= '2026-09-10' and created_at < '2026-09-11'
     and (title ilike 'Dossi%' or title ilike '%desconectado%')
  union all
  select created_at, event_type from work_events where event_type='espera.vencida')
select count(*), min(created_at), max(created_at),
       extract(epoch from (max(created_at)-min(created_at)))/60 from t;
--  7 | 2026-09-10 17:14:18 | 2026-09-10 18:29:59 | 75,68
```

⚠️ **Correção ao diagnóstico:** ele diz *"7 mensagens em 77 min"*. A medição de hoje dá **75,7 min**. O 7 está certo; o 77 era arredondamento. Já corrigido aqui.

📊 **E a Saionara digitou "1" à mão às 17:18:14** (`work_events`, `travamento.assumido`, ator `user`, 10/09). Quer dizer: das 7 mensagens, **6 saíram depois de um humano da corretora já estar dentro daquela conversa.**

### 0.2 A arma carregada que ainda não disparou

📊 **58 de 58.** Medido em 13/09/2026 sobre produção:

```sql
-- elegíveis ao re-alerta de 6 h = HUMAN_REQUESTED + última mensagem do segurado
with ult as (select distinct on (m.conversation_id) m.conversation_id, m.role, m.created_at
             from messages m join conversations c on c.id=m.conversation_id
             where c.status='HUMAN_REQUESTED' order by m.conversation_id, m.created_at desc),
eleg as (select conversation_id, created_at as fim from ult where role='user'),
hum as (select e.conversation_id, e.fim,
          max(m.created_at) filter (where m.role='assistant'
            and lower(coalesce(m.payload->>'origem','')) in ('espelho','dashboard')) as ultima_humana
        from eleg e left join messages m on m.conversation_id=e.conversation_id group by 1,2)
select count(*) elegiveis,
       count(*) filter (where ultima_humana > fim - interval '7 days') humano_nos_7d
from hum;
--  58 | 58
```

| medição (13/09/2026) | valor |
|---|---|
| conversas em `HUMAN_REQUESTED` | **131** (AutoFleet 78 · Resulta 53) |
| elegíveis ao re-alerta (última palavra do segurado) | **58** |
| dessas, com humano da corretora falando nos 7 dias anteriores | **58 de 58** |

🔴 **ESTE NÚMERO JÁ DERIVOU, e o BLOCO 0 vai medir outro.** 📊 Na mesma tarde de 13/09, uma segunda passada deu **131 · 59 elegíveis · 72 caladas** — o acervo é vivo, e o espelho grava enquanto se mede. **58 e 59 são o mesmo fato em dois instantes.**

⛔ Por isso o `58` é **📊 datado, na prosa, e nunca na asserção de um guarda** (§12, G-A1 e G-A3): o teste afirma *"todas as elegíveis medidas no BLOCO 0 calam"*, com a linha de controle. Um guarda que fixe `58` fica vermelho na primeira mensagem nova e ensina a equipe a ignorar o guarda — que é literalmente o defeito que esta SPEC existe para consertar.
| `human_handoff_reason` vazio | **129 de 131** — quase nenhuma foi pedida pelo agente |
| origem das falas humanas gravadas | `espelho` **32.231** · `dashboard` **0** |

🔴 **FATO adicional, e ele muda a leitura:** `work_events` tem **0 linhas** de `handoff.realertado` em toda a base (`select count(*) from work_events where event_type like 'handoff%'` → `0`). Ou seja: **o re-alerta de 6 h nunca chegou a disparar sobre essas 58.**

📊 A razão medida: os destinos de suporte das duas pilotos estão **inativos** hoje (`select company_id, destination_type, is_primary, is_active from human_support_destinations` → Resulta `is_active=false`, AutoFleet `is_active=false`, só AMANDUS com um ativo), e os cinco `companies.agent_enabled` estão `false`.

**INFERÊNCIA de alta confiança:** o grupo está quieto por acidente de configuração, não por desenho. No instante em que a Saionara reativar o destino e ligar o agente — que é exatamente o que a EXTRA-001.7 manda fazer por três dias seguidos — a fila de 58 começa a drenar para o grupo, **a cada 6 horas**, mais o que o dia produzir.

⚠️ **E o número por passada não é 58.** `varrer_handoffs_parados` tem `.limit(_MAX_POR_PASSADA)` = **50** (`handoff_watchdog.py:45, :146`) e só olha conversas paradas há mais de `HANDOFF_ALERTA_MINUTOS` = **30 min** (:43, :108-112). Então o teto é **≤ 50 mensagens por passada**, e o resto vem na seguinte. 🔴 A diferença entre 58 e "≤ 50, em ondas" não muda a conclusão — muda a honestidade do número, e é por isso que está escrita.

### 0.3 As decisões do Founder já incorporadas — não se reabrem

| ID | Decisão que governa esta execução | onde entra |
|---|---|---|
| **D-PILOTO-08** | Numeração EXTRA-001.x mantida; nada renumera | cabeçalho |
| **D-PILOTO-09** | Lista de números da casa no **card Equipe** — não no card Agente, não em card próprio | BLOCO B |
| **D-PILOTO-13** | Eficiência das 19h: sinistro conta como sucesso; sucesso = até a mensagem do acionamento chegar ao segurado; pós-acionamento fora. **E a distinção foi decidida em 13/09:** só ajuda por **incapacidade** entra no denominador; ajuda por **regra** fica fora e aparece como contagem própria | BLOCO D.4 |
| **D-PILOTO-14** | Alta qualidade sem exorbitância: ≤ **12 guardas novos**, todos sobre o motor e o acervo real | §12 |
| **D-PILOTO-20** | Execução em chat novo, AAA opção B, marcha CRÍTICO com 3 juízes | §0.4 |
| **§7.2 do diagnóstico** | A janela do grupo é **a mesma** janela de N dias do atendimento. Uma regra, um número, um lugar para mudar. ⛔ Proibido criar um segundo número "só para o grupo" | BLOCO A |

### 0.4 EXECUTION CARD — enquadramento proposto, a confirmar no BLOCO 0

```text
OUTCOME .............. o grupo da corretora recebe 4 tipos de mensagem e mais nada; nenhuma
                       sobre conversa que um humano já conduz ou sobre número da casa;
                       uma mensagem inteira e clicável; todo envio contado
RISCO ................ 8 — ALCANCE 3 (o dossiê chega ao segurado indiretamente: é a decisão
                       da atendente sobre o caso dele) · REVERSIBILIDADE 3 (mensagem que sai
                       do prédio) · FREQUÊNCIA 2 (todo atendimento)
SUPERFÍCIE ........... 3 — são 11 pontos de envio ao grupo mapeados (§3.2) e a afirmação
                       "consigo apontar TODOS" é precisamente o que a SPEC tem de PROVAR
PISO APLICADO ........ AAA §3.2 três vezes: envia mensagem · migration que altera estrutura ·
                       autenticação e filtro company_id (BLOCO G)
NÍVEL ................ CRÍTICO — opção B. A soma (8) e o piso concordam
UNIDADES ............. 7 — A guarda única · B números da casa · C mensagem inteira ·
                       D os quatro modelos · E contabilidade · F gate de ligar · G autorização
COESÃO ............... A e C tocam os MESMOS arquivos de envio → um dono, serial.
                       B (migration + card Equipe) e G (rotas Next) são disjuntos de A/C/D.
                       D consome a guarda de A → depois de A.
PARALELISMO REAL ..... dois escritores no máximo: {A,C,D,E,F backend} e {B-UI, G rotas Next}.
                       ⛔ nunca dois em `human_handoff.py`, `dispatch_router.py` ou
                       `handoff_watchdog.py` — são arquivos-hub (AAA §3.4)
TIME ................. investigador+pesquisador (um) · desenhista · builder backend ·
                       builder painel · verificador mecânico · 3 lentes + red team ·
                       juiz fresco de confirmação+auditoria (AAA §6.1)
REFERÊNCIA ........... interna: `backend/tests/test_o_caso_se_explica_sozinho.py`
                       (`problemas_de_lingua`, a régua de língua humana) e
                       `backend/tests/corpus/telas_reais/`. Externa: as 5 de §19
GATES ................ G-A1 … G-G1 da §12, mais os gates canônicos do protocolo
GUARDAS NOVOS ........ 7 ARQUIVOS · 12 guardas nomeados · 💭 ~30 asserções (§12.1).
                       ⚠️ O teto de D-PILOTO-14 conta ARQUIVOS. G-F1/G-G1 é UM arquivo com
                       5 asserções: separá-lo em cinco não melhora a prova e estoura o teto
O ELO ................ "o grupo virou ruído PORQUE nenhum gatilho pergunta se um humano já
                       está na conversa" — A medido (7 mensagens, §0.1) · B medido (58 de 58,
                       §0.2) · 🔴 B CHEGA EM A: o BLOCO 0 tem de provar que os mesmos
                       gatilhos que produziram as 7 são os que leem (ou não leem) a guarda
FAIXA DE RELÓGIO ..... 💭 7–10 h. Faixa, nunca promessa (AAA §9.2)
ORÇAMENTO ............ alvo canônico CRÍTICO ≤ 2,5 M tokens de subagentes (AAA §10)
BLOCKER .............. pelo TESTE DO PRODUTO (AAA §2): BLOCO A, BLOCO C e BLOCO G mudam um
                       byte do que chega à corretora, ao banco ou à segurança → BLOCKER.
                       BLOCO B e D mudam o que a corretora lê → BLOCKER.
                       BLOCO E e F: E é o dado que responde "quantas saíram" → BLOCKER;
                       F é tela + recusa → BLOCKER (hoje ligar o agente sem destino produz
                       handoff que não chega a ninguém — medido em `main.py:876-921`)
```

---

## 1. AUTORIZAÇÃO DE TESTES — a fronteira de todo pacote desta SPEC

### 1.1 Allowlist explícita e privada

| Alias em toda evidência | Valor |
|---|---|
| **TESTE-A** | `[allowlist privada — nunca commitar]` |
| **TESTE-B** | `[allowlist privada — nunca commitar]` |

⛔ Os dois números reais moram **só** no prompt privado do chat executor e na configuração de teste (`JANELA_SILENCIO_EXCECOES`, `ATTENDANT_INBOUND_ALLOWLIST`). Nunca no canon, no relatório, no dossiê publicado, em fixture permanente, em log ou em screenshot.

### 1.2 O que está autorizado

- Implementar esta SPEC e rodar o AAA com as permissões vigentes do projeto.
- **Grupo de teste do canário:** um destino `whatsapp_group` **criado para o canário**, dentro de um tenant de teste, com apenas o Founder dentro. ⛔ Nunca os grupos operacionais "Suporte Resulta" / "Suporte AutoFleet".
- Mensagens entre TESTE-A e TESTE-B, em conexões cuja identidade efetiva foi conferida no ato.
- Consultas read-only ao banco de produção para contagens. ⛔ Nunca imprimir conteúdo de mensagem, telefone inteiro, CPF/CNPJ, nome de segurado, placa ou e-mail.

### 1.3 O que permanece proibido

1. Enviar qualquer coisa aos grupos de suporte operacionais da Resulta ou da AutoFleet.
2. Usar número operacional de corretora como remetente, mesmo para enviar ao Founder.
3. Contatar Saionara, Regina, segurados, seguradoras ou membros de equipe.
4. Ligar o agente de atendimento, o dispatch ou uma rotina globalmente numa corretora operacional para "fazer o canário funcionar".
5. Abrir sinistro, acionar assistência, entrar em portal de seguradora ou alterar apólice.
6. Apagar, desativar ou recriar destino de suporte operacional. ⚠️ Os destinos de Resulta e AutoFleet estão hoje `is_active=false`; **essa é a configuração atual do Founder e não se mexe nela** — se o canário precisar de um destino ativo, cria-se um **novo**, no tenant de teste, e ele é removido no "Depois" da §14.
7. Tratar a restrição do canário como licença para retirar controle de produção.

### 1.4 Verificação imediatamente antes de cada efeito

O guardião do canário confere, na ordem, **antes de cada envio**: ambiente · tenant · destino resolvido (`destination_ref`) **pertence ao tenant de teste** · identidade real do remetente · o destino está na allowlist do canário · tipo de operação permitido · orçamento de teste não estourado.

🔴 Se a identidade não puder ser confirmada, **não enviar**. ⛔ Não escolher outro destino automaticamente — que é exatamente o que `resolver_destino_de_suporte` faz por desenho (três fallbacks, `dispatch_router.py:2370-2396`), e por isso a trava do canário mora **no último ponto de efeito**, não na resolução.

### 1.5 Ação física do Founder

Se faltar o pareamento de um número de teste ou a criação do grupo de canário, o executor **completa tudo que não depende disso**, registra o gate como NÃO COMPROVADO e deixa o ato físico na Caixa do Founder (§22). ⛔ Ausência de canário nunca vira aprovação de produção.

---

## 2. Escopo completo e exclusões deliberadas

### Obrigatório nesta SPEC

1. **Uma** guarda "humano já está nesta conversa", consultada por **todos** os gatilhos de grupo (BLOCO A).
2. Lista de números da casa com **efeito quádruplo**, no card Equipe, com migration expand-first (BLOCO B).
3. Mensagem inteira em todos os caminhos; espera vencida com um aviso; queda de canal ao dono; reabertura que não fura o marcador (BLOCO C).
4. Os quatro modelos de mensagem, com copy completa e campo `motivo` classificado (BLOCO D).
5. Todo envio ao grupo contado, sem envenenar o governador de vazão (BLOCO E).
6. Gate de ligar o agente com recusa em frase humana (BLOCO F).
7. As 6 mutações sem papel/origem ganham `requireCompanyMember` + origem + auditoria (BLOCO G).
8. Prova de isolamento com **duas corretoras reais** para a guarda e para a lista de números.

### Fora desta SPEC, e quando volta

| Frente | Por que não entra | Gatilho de retorno |
|---|---|---|
| **A régua de eficiência publicada no dossiê** | O número nasce aqui; a régua por dimensão é o produto da 001.7 | EXTRA-001.7, depois dos 3 dias medidos |
| **Uma conversa por contraparte (LID × telefone)** | É o BLOCO de outra SPEC e mexe em migration de `conversations` | EXTRA-001.2; ver §21 para o que fazer se ela ainda não tiver subido |
| **Checklist estruturado de sinistro/empresarial/condomínio** (P-PILOTO-04) | A SPEC entrega o **modelo 🚨 NOVO SINISTRO** e o campo "pontos de atenção"; o **conteúdo** do checklist por tipo depende da base de produtos | EXTRA-001.5; o modelo já reserva o lugar |
| **Corredor que não trava, humano na URA (60 s)** | É a 001.4, paralela a esta | EXTRA-001.4 |
| **Relatório semanal e sugestões proativas** (`weekly_report.py`, `proactive_suggestions.py`) | Leem só o legado `acionamento_profile.suporte_humano_whatsapp` e **ignoram** `human_support_destinations` — defeito real, mas de outra superfície | 💭 pendência nova nesta SPEC; a corretora que só cadastrou pela tela nova não recebe os dois |
| **Aviso de queda de canal com reconexão automática** | Esta SPEC muda só o **destinatário** do aviso | SPEC de canais (099) |

⚠️ Nada do bloco "Obrigatório" sai em silêncio. Se a conversão mostrar conflito material, vai para `CHANGE-ADDENDA.md` classificado, com decisão do Founder (CLAUDE.md §11) — recorte unilateral não é "otimização AAA".

---

## 3. Autoridades preservadas e arquitetura — nenhum motor paralelo

🔴 **CLAUDE.md §5.** Esta SPEC **não cria**: escalonamento novo, fila de alertas nova, scheduler novo, ledger novo, resolvedor de destino novo, motor de janela novo. Tudo o que ela faz é **ligar peças que já existem e hoje não se falam**.

### 3.1 O que já existe e é reaproveitado, por arquivo

| Peça que já existe | Onde | Por que serve, e o que muda |
|---|---|---|
| **A janela de silêncio inteira** | `backend/app/services/o_fim_do_atendimento.py:944-1400` | `janela_de_silencio_dias()` (:1012), `ultima_palavra_humana()` (:1146), `silenciar_por_palavra_humana()` (:1194), `a_ia_deve_calar()` (:1325), `janela_de_mensagens()` (:1257). **É o motor do BLOCO A.** ⛔ Reimplementar a regra aqui seria motor paralelo E violaria §7.2 (uma régua só) |
| **Casar telefone com/sem 55 e nono dígito** | `o_fim_do_atendimento.py:1296` `_variantes_do_telefone` | Já é a autoridade do `JANELA_SILENCIO_EXCECOES` (commit `05f46a9`). **É o casador do BLOCO B** |
| **O resolvedor de destino** | `dispatch_router.py:2346` `resolver_destino_de_suporte` | Já recusa destino compartilhado entre corretoras (`_destino_e_compartilhado`, :2259-2343). Continua o único. ⚠️ `billing_collection.avisar_suporte_humano` (:243-292) é uma **segunda implementação** que pula essa recusa — o BLOCO E a funde na primeira |
| **A porta única de envio ao grupo** | `human_handoff.py:920-962` `_avisar_suporte` | **É o único envio ao grupo que já passa `bloco_unico=True`** (:951-956). O BLOCO C faz os outros passarem por ela ou copiarem o contrato |
| **O ledger de envios** | `platform_sends` (migration `20260720_02_spec045_platform_sends.sql`) + `record_platform_send` (`platform_outbound.py:312`) | É onde o BLOCO E grava. ⚠️ Ver §9.2 — a leitura do governador não filtra `kind` |
| **O diário contável** | `work_events` + `_anotar_no_diario` (`handoff_watchdog.py:446`) | Já tem `handoff.realertado`, `handoff.teto_de_lembretes`, `espera.vencida`. O BLOCO D acrescenta o `motivo` classificado à carga, e o BLOCO D.4 conta a eficiência **daqui** |
| **O agendador** | `buffer_processor.py:154-579` (APScheduler, 24 jobs) | O resumo das 19h entra como **mais um job neste agendador**, no padrão de `relatorio_semanal_check` (:243-247: intervalo curto + checagem interna de "já é hora / já saiu hoje"). ⛔ Nenhum scheduler novo |
| **O fuso da corretora** | `o_fim_do_atendimento.FUSO_DA_CORRETORA` e `fuso_da_corretora()` (`platform_outbound.py:638`) | As 19h são **locais da corretora** |
| **O padrão de autorização do painel** | `lib/admin/admin-auth.ts:68` `requireCompanyMember` + `:103` `assertSameOrigin` + `lib/vault/server.ts:55` `writeAudit` | **É o padrão pronto que o BLOCO G aplica.** Referência de uso correto: `app/api/dashboard/team/route.ts:46-50` |
| **A régua de língua humana** | `backend/tests/test_o_caso_se_explica_sozinho.py:1181` `problemas_de_lingua` | Hoje roda só nas cartas e na novidade ao cliente (P-PILOTO-12). O BLOCO D a faz rodar nos quatro modelos e no `_montar_dossie` |
| **O único escritor de "quem assumiu"** | `conversations.claimed_by` / `claimed_at` / `claimed_by_name` | A guarda do BLOCO A lê daqui; ⛔ não se cria estado novo de "assumida" |

### 3.2 Os 11 pontos de envio ao grupo — o mapa que a SUPERFÍCIE 3 exige

📊 Levantado em 13/09/2026 por varredura do backend. **`bloco_unico` está em 1 de 11.**

| # | arquivo:linha | o que manda | resolve destino por | `bloco_unico`? | lê a guarda? |
|---|---|---|---|---|---|
| 1 | `app/agents/tools/human_handoff.py:952` | dossiê de handoff (tool, re-alerta 6 h, espera vencida) | `resolver_destino_de_suporte` | ✅ | ❌ |
| 2 | `app/services/dispatch_router.py:3304` | `build_handoff_dossier` (caminho A) | `resolver_destino_de_suporte` (:3291) | ❌ | ❌ |
| 3 | `app/services/dispatch_router.py:201` | "o aviso de protocolo NÃO chegou ao segurado" | `resolver_destino_de_suporte` (:187) | ❌ | ❌ |
| 4 | `app/tasks/dispatch_watchdog.py:315` | `_support_alert`: dossiê do Sentinela, `ura_silent`, `human_silent_alert`, `never_started`, `deadline` | `resolver_destino_de_suporte` (:285) | ❌ | ❌ |
| 5 | `app/services/billing_collection.py:287-289` | avisos de cobrança e portal à equipe | 🔴 lê `human_support_destinations` **direto** (:269-274) | ❌ | ❌ |
| 6 | `app/services/regression_sentinel.py:100` | "QUALIDADE EM QUEDA" | `_support_contact` (:89) | ❌ | ❌ |
| 7 | `app/services/whatsapp/alerts.py:255` | "WhatsApp desconectado" | `_alert_destination` (:60-97) | ❌ | ❌ |
| 8 | `app/api/admin_spec034.py:241` | alerta de TESTE | `_support_contact` (:232) | ❌ | ❌ |
| 9 | `app/services/weekly_report.py:91` | relatório semanal | 🔴 só o legado `suporte_humano_whatsapp` | ❌ | ❌ |
| 10 | `app/services/proactive_suggestions.py:183` | sugestões semanais | 🔴 só o legado | ❌ | ❌ |
| 11 | `app/services/atlas/route_sentinel.py:498` | mudança de rota de seguradora | `_founder_alert_number()` — **não é destino de corretora** | ❌ | n/a |

🔴 **É este mapa que a guarda do BLOCO A tem de cobrir, e é ele que o guarda G-A2 congela:** um ponto de envio novo que não passe pela guarda faz o teste ficar vermelho.

### 3.3 Contrato lógico mínimo

```text
um gatilho quer falar com o grupo
  → PERGUNTA à guarda única:  (company_id, conversation_id | telefone) → pode?
      · a conversa está ASSUMIDA por alguém (claim fresco)?              cala
      · um humano da corretora falou nela nos últimos N dias?            cala
      · a contraparte é um NÚMERO DA CASA daquela corretora?             cala
      · o tipo de mensagem é ISENTO (sinistro, resumo diário)?           passa
  → resolve o destino (o resolvedor único, com company_id)
  → DEDUPLICA por (company_id, conversation_id, tipo) na janela do tipo
  → monta o MODELO (um dos quatro), com bloco_unico
  → envia
  → grava em platform_sends (kind `grupo_*`) E em work_events (com o motivo)
```

⚠️ Supabase é a verdade durável; Redis é lease e marcador; nenhum estado novo de conversa é criado. Todo acesso é `company_id`-scoped **no código**, não só na RLS (CLAUDE.md §7).

---

## 4. BLOCO 0 — converter medindo, antes de qualquer código de produto

> Este documento envelhece. 📊 O próprio diagnóstico que o originou já tinha duas afirmações vencidas (§4.1). O BLOCO 0 existe para que o número do executor vença o meu (AAA §5 ①).

1. **Preflight Git**, na ordem do CLAUDE.md §2: `git rev-list --count HEAD..origin/main` (**tem de ser 0**), `git rev-list --count origin/main..HEAD`, `git branch --show-current`, `git rev-parse HEAD`, `git status --short`. Registrar no relatório.
2. **Reabrir os 11 pontos de envio da §3.2** e conferir linha a linha. Se uma linha mudou, corrigir **aqui e no research pack**, e dizer qual era.
3. **Remedir os três números-âncora** com os comandos colados em §0.1, §0.2 e §7.1:
   - 7 mensagens em 75,7 min no dia 10/09;
   - 58 de 58 elegíveis com humano nos 7 dias;
   - o dossiê de acionamento vira **4 balões**.
   🔴 **E remedir o terceiro pelo MOTOR, não por SQL** (CLAUDE.md §9.4): o 58 acima foi medido em **SQL**, e a regra que vai rodar é **Python** (`ultima_palavra_humana`, que ainda exclui `#nota` e eco do agente — coisas que a minha query **não** exclui). Rodar `ultima_palavra_humana` sobre as mesmas 58 conversas e **dizer o número que sair**. Se der 55, é 55. 📊 Um padrão medido com um motor e aplicado com outro é um padrão sobre outra coisa.
4. **Ler `docs/canon/MIGRATIONS-AUTHORITY.md` inteiro** antes de qualquer SQL. Medir o schema vivo de `company_members`, `human_support_destinations`, `platform_sends`, `work_events` e `integrations.alert_target` por `information_schema` — não por suposição.
5. **Medir o governador** (§9.2): confirmar as **três** leituras sem filtro de `kind` em `_historico_sync` (`platform_outbound.py:606-610, :611-613, :614-616`) e que as duas últimas alimentam `maturidade_do_canal` (:697, def :424-441) → `teto_do_dia` (:444-445). Decidir a **allowlist** (ou a coluna `conta_na_cota`) **antes** de escrever a primeira linha nova, já contemplando `billing_nota`/`billing_doc` da 001.6.
5b. **Medir o buraco do `motivo_classe`** (§8.1): `grep -rn "motivo_classe" backend/app` e a contagem de `human_handoff_reason` preenchido. Se der 0 e 129-de-131 como em 13/09, **a regra de `desconhecido` da §8.4 é obrigatória** — e o limite de fatia (💭 30%) sai da sua medição, não do meu palpite.
6. **Inventariar os destinos e o estado dos agentes** sem publicar `destination_ref`: quantos destinos por corretora, quantos ativos, quantos `agent_enabled`.
7. **Medir o acervo do canário:** quantas conversas em cada corretora ficariam caladas pela guarda, e quantas continuariam falando. O número "quantas o grupo ainda receberia" é tão importante quanto o "quantas calam" — uma guarda que cala tudo é tão defeituosa quanto uma que não cala nada.
8. **Conferir o estado real de P-PILOTO-02, 03, 04, 12** e dar a cada uma `FECHADA` / `CONTINUA` / `MORREU` com prova (AAA §2).
9. **Rodar a suíte inteira uma vez** para ter a baseline de falhas pré-existentes (📊 P-PILOTO-20 diz que 4 guardas antigos de policy já quebram por import — não rotular como regressão).
10. **Converter** em SPEC definitiva com card, gates, mutação por bloco, §19 com as referências reabertas, "O QUE SAIU" e caixa do Founder.

**GATE B0:** matriz `premissa → observação nova → comando → decisão`, o mapa dos 11 pontos conferido, e a autorização do canário escrita. ⛔ Nenhum achado não reproduzido vira incidente confirmado.

**MUTAÇÃO B0:** o desenhista entrega ao aquecimento duas afirmações deliberadamente falsas (§6 do prompt de abertura). O executor tem de refutá-las com evidência.

### 4.1 O que eu já sei que está vencido no diagnóstico — corrija sem hesitar

| o diagnóstico §1.5 diz | o que medi em 13/09 |
|---|---|
| *"o re-alerta de 6 h não pergunta se um humano está na conversa"* | ⚠️ **Meia verdade.** Ele já pergunta **duas** coisas (`handoff_watchdog.py:180-197` "a última palavra foi do cliente?" e `:271-291` "o claim é fresco?"). O que ele **não** pergunta é a **janela de N dias** — e é só essa que faltava. 📊 73 das 131 já são caladas hoje pela regra de 21/08 |
| *"7 mensagens em 77 min"* | 📊 **75,7 min** |
| *"quebra a cada 300 caracteres"* | ⚠️ Não é a cada 300: `split_whatsapp_balloons` devolve o texto inteiro se couber em 300, e **acima disso parte por linha em branco**. 📊 Um dossiê de **429 caracteres** vira **4 balões** (136, 16, 69, 201) |
| *"`alert_target.internal_numbers` … só impedem a captura"* | ✅ Confirmado, e pior: 📊 nenhuma rota do backend **popula** essas listas (só `pairing_orchestrator.py:775-777` cria vazias por `setdefault`), e `whatsapp_channel.py:1124` **sobrescreve o objeto inteiro**, apagando as três chaves |
| *"`company_members` não tem telefone"* | ✅ Confirmado. 📊 7 colunas, nenhuma de contato; **uma** migration a cria (`20260721_01_spec047…sql:17-26`) e **nenhuma** a altera. O telefone da equipe vive em `users_v2.phone`, lido por `getTeam` (`lib/admin/tenant-overview-store.ts:17`) |
| *"P-PILOTO-10: a AutoFleet segue com zero destinos"* | ⚠️ **Vencida.** 📊 13/09: AutoFleet tem 1 destino próprio; Resulta tem 1. Os dois `is_active=false`. Reavaliar a pendência como FECHADA-com-ressalva |

---

## 5. BLOCO A — a guarda única "humano já está nesta conversa"

**Outcome do bloco:** nenhum gatilho automático fala com o grupo sobre uma conversa que já tem gente.

### 5.1 O contrato

Um módulo novo e pequeno — 💭 `backend/app/services/o_grupo_so_o_que_importa.py` — com **uma** função pública. ⛔ Ele **não** implementa regra nenhuma: ele **compõe** as que já existem.

```python
async def o_grupo_pode_saber(
    db,
    *,
    company_id: str,
    conversation_id: str = "",
    telefone: str = "",
    tipo: str,                       # 'pedido_de_ajuda' | 'sinistro' | 'conclusao'
                                     # | 'espera_vencida' | 'vigia' | 'resumo_diario'
    companhia: Any = None,
    agora=None,
) -> Tuple[bool, str]:
    """(pode_falar, motivo_em_português). 🔴 FAIL-OPEN por desenho — ver §5.4."""
```

As quatro perguntas, **nesta ordem**, e cada uma delegando:

| # | pergunta | quem responde hoje | resultado |
|---|---|---|---|
| 1 | o tipo é **isento**? | tabela de §5.3 | `True, ""` — atalho antes de qualquer I/O |
| 2 | a contraparte é **número da casa**? | BLOCO B, `e_numero_da_casa(company_id, telefone)` | `False, "é um número da própria corretora (<rótulo>)"` |
| 3 | a conversa está **assumida** por alguém, com claim fresco? | `conversations.claimed_by` + `claimed_at`, a mesma régua de idade de `handoff_watchdog.py:282-287` | `False, "<nome> assumiu esta conversa há <tempo>"` |
| 4 | um **humano da corretora** falou nela nos últimos N dias? | `janela_de_mensagens()` → `ultima_palavra_humana()` → `silenciar_por_palavra_humana(n_dias=janela_de_silencio_dias(companhia))` | `False, "<a frase que a janela já produz>"` |

🔴 **A pergunta 4 não tem número próprio.** Ela chama `janela_de_silencio_dias(companhia)` — a **mesma** função que decide se o agente cala com o segurado, com a **mesma** env (`JANELA_SILENCIO_HUMANO_DIAS=7`) e o **mesmo** override por corretora (`companies.acionamento_profile.janela_silencio_humano_dias`). §7.2 do diagnóstico: *uma regra, um número, um lugar para mudar*. ⛔ Criar `JANELA_DO_GRUPO_DIAS` reprova o bloco.

⚠️ **E `0` continua desligando a regra**, como já desliga no atendimento (`o_fim_do_atendimento.py:1021-1024`). Uma corretora que ponha 0 volta ao comportamento de hoje sem deploy — e o guarda G-A1 tem de provar que 0 realmente devolve as 58.

### 5.2 Quem passa a perguntar

Os **11 pontos** da §3.2, assim:

```
1  human_handoff.py:952        → a guarda entra DENTRO de `_avisar_suporte`, antes de resolver
                                  o destino. Cobre de uma vez: a tool, o re-alerta de 6 h e a
                                  espera vencida (os três chamadores, :1182, :351, :568)
2  dispatch_router.py:3304     → guarda antes de `entregar_dossie_uma_vez`
3  dispatch_router.py:201      → guarda em `_support_alert_seguro`
4  dispatch_watchdog.py:315    → guarda em `_support_alert`, uma vez, na entrada
5  billing_collection.py:287   → 🔴 funde em `resolver_destino_de_suporte` (hoje é a 2ª
                                  implementação e pula a recusa de destino compartilhado);
                                  a cobrança é sobre PARCELA, não sobre conversa: entra com
                                  `conversation_id=""` e cai só na pergunta 2
6  regression_sentinel.py:100  → tipo `vigia`, sem conversa: passa (é sobre a corretora)
7  whatsapp/alerts.py:255      → 🔴 BLOCO C: muda de destinatário, não de guarda
8  admin_spec034.py:241        → alerta de TESTE: mantém, é ferramenta de diagnóstico
9,10 weekly_report / proactive → fora do escopo (§2); pendência registrada
11 route_sentinel.py:498       → vai ao Founder, não ao grupo: não muda
```

🔴 **A guarda entra no ponto mais baixo possível de cada caminho.** Colocá-la no chamador é o que produz o 12º caminho que ninguém lembrou — e é o defeito que o guarda G-A2 existe para pegar.

### 5.3 O que a guarda **não** cala — e por quê está escrito

| tipo | passa mesmo com humano na conversa? | por quê |
|---|---|---|
| `pedido_de_ajuda` | ❌ não | se a atendente já está lá, ela não precisa ser chamada |
| `espera_vencida` | ❌ não | o prazo é de quem está com o caso; se ela está, ela sabe |
| `vigia` (`ura_silent`, `deadline`, `never_started`) | ❌ não | vira **linha do resumo das 19h** (BLOCO C.3) |
| **`sinistro`** | ✅ **SIM, sempre** | 🔴 um sinistro novo é notícia de negócio, não lembrete de fila. A corretora precisa saber que existe um sinistro **mesmo** que alguém já esteja conversando — e o §7.5 conta sinistro como sucesso justamente porque ele é o produto, não o incidente |
| **`conclusao`** | ✅ **SIM, sempre** | é o fechamento, e é curto. Calar a conclusão porque um humano participou apagaria justamente o caso em que houve trabalho humano — e é ele que alimenta o "3 já com a Regina" do resumo |
| **`resumo_diario`** | ✅ **SIM** | é uma mensagem por dia, sobre o dia, não sobre uma conversa |

⚠️ **Este é o ponto em que a guarda pode errar para o lado ruim.** Uma guarda que cala tudo é tão defeituosa quanto uma que não cala nada — CLAUDE.md §9.3, e a lição literal de `handoff_watchdog.py:241-243`: *"trocar um excesso de aviso por um silêncio é trocar um defeito por um pior"*. O gate G-A1 mede **os dois lados**.

### 5.4 Falha de leitura: FAIL-OPEN, e escrito

🔴 Se a guarda **não conseguir ler** (banco fora, timeout), ela devolve `(True, "não consegui conferir se há alguém na conversa")` e **loga**. O produto avisa demais em vez de calar.

⚠️ É o **oposto** da `a_ia_deve_calar`, que é fail-**closed** — e a assimetria é deliberada: falar por cima da atendente na frente do segurado é irreversível; mandar um aviso a mais ao grupo, não. O comentário de `handoff_watchdog.py:198-203` já escolheu assim, e esta SPEC **conserva a escolha**. ⛔ Um juiz que peça fail-closed aqui está pedindo silêncio de atendimento por falha de infraestrutura.

**GATE A (G-A1, G-A2 em §12).** **MUTAÇÃO A:** desligar a pergunta 4 da guarda → as 58 voltam → o teste fica **vermelho**.

---

## 6. BLOCO B — a lista de números da casa, no card Equipe

**Outcome do bloco:** a corretora escreve, num lugar só, quais números são da própria casa — e o agente nunca mais os atende, nunca os põe na Fila, nunca fala sobre eles no grupo, e marca a captura deles como interna.

**D-PILOTO-09 é lei:** card **Equipe** (nota 88 × card Agente 62 × card próprio 71). ⛔ Não se reabre.

### 6.1 De onde vêm os números — duas fontes, uma resposta

```
1. TELEFONE DOS MEMBROS       users_v2.phone dos membros ativos daquela corretora
                              (já existe, já é SELECIONADO por getTeam —
                               lib/admin/tenant-overview-store.ts:17-24)
2. NÚMEROS QUE NÃO SÃO DE     tabela NOVA `company_internal_numbers`:
   PESSOA COM LOGIN           o fixo, o comercial, o celular do sócio que não usa o painel
```

🔴 **⛔ NENHUMA coluna nova em `company_members`.** 📊 `users_v2.phone` está preenchido em **796 de 796** usuários e já chega à tela. Acrescentar telefone em `company_members` criaria uma segunda verdade sobre o mesmo fato — exatamente o defeito de `alert_target` (três escritores, três formas).

⚠️ **Mas preenchido não é utilizável:** 📊 nada prova o **formato** desses 796, nem que o número é WhatsApp. É por isso que o casamento é por `_variantes_do_telefone` (§6.3) e o guarda G-B1 leva um caso com telefone de membro **mal formatado** — com `+55`, sem `55`, com máscara, com e sem nono dígito.

📊 **Por que a tabela nova não é motor paralelo:** o conceito existe hoje **só** como chave dentro do JSONB `integrations.alert_target` (`internal_numbers`, `observer_exclusions`). Medido em 13/09:

- **nenhuma rota popula** as listas — `pairing_orchestrator.py:775-777` só cria arrays vazios por `setdefault`;
- **três formatos incompatíveis** convivem na mesma coluna, documentados no próprio código (`pairing_orchestrator.py:770-789`);
- `whatsapp_channel.py:1124` faz `update({"alert_target": target})` com `{"number": …}` e **apaga** `observer_scope`, `observer_exclusions` e `internal_numbers`;
- o único leitor é `attendance_capture.py:109-117`, e o efeito é **só** filtrar o que o Observador captura.

**INFERÊNCIA:** um JSONB sem schema, com três escritores de forma diferente, um deles destrutivo, e nenhuma tela, não é uma lista — é um lugar onde a informação some. A tabela nova **substitui** a chave `internal_numbers` (expand-first: a coluna continua lá e continua sendo lida, com o novo leitor na frente) e o `observer_exclusions` continua sendo o que sempre foi.

### 6.2 A tabela

```sql
create table if not exists public.company_internal_numbers (
  id           uuid primary key default gen_random_uuid(),
  company_id   uuid not null references public.companies(id) on delete cascade,
  phone        text not null,                       -- só dígitos, como chega no user_phone
  label        text not null,                       -- 💭 "fixo da loja", "comercial", "sócio"
  kind         text not null default 'outro'
               check (kind in ('fixo','comercial','socio','membro','outro')),
  created_by   uuid null references public.users_v2(id) on delete set null,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (company_id, phone)
);
```

🔴 **`unique (company_id, phone)` e não `unique (phone)`** — dois corretores diferentes podem ter o mesmo fixo de prédio, e o número de uma corretora **nunca** cala a outra (CLAUDE.md §7; guarda G-B2).

RLS habilitada; o backend usa service role, então **o filtro `company_id` no código é a proteção real**, não a policy.

### 6.3 A leitura, e o casamento

```python
async def numeros_da_casa(db, company_id: str) -> set[str]:
    """Dígitos normalizados: membros ativos (users_v2.phone) ∪ company_internal_numbers."""

def e_numero_da_casa(numeros: set[str], telefone: str) -> bool:
    """🔴 Usa `_variantes_do_telefone` de o_fim_do_atendimento.py:1296 — a MESMA
    autoridade que já casa com/sem 55 e com/sem nono dígito no
    `JANELA_SILENCIO_EXCECOES` (commit 05f46a9). ⛔ Não escrever outro casador."""
```

Cache por corretora com TTL curto no Redis (💭 60 s), invalidado na escrita. ⚠️ A lista é lida em caminho quente (todo inbound), e o custo é a única razão do cache — não a correção.

### 6.4 O efeito quádruplo — e ele é o bloco, não a tabela

| efeito | onde entra | como se prova |
|---|---|---|
| **nunca responde** | o portão do inbound de atendimento, junto de onde `a_ia_deve_calar` já é consultada | mensagem de um número da casa → 0 respostas do agente, e o motivo no feed |
| **nunca entra na Fila** | a projeção de casos (`lib/atendimento/casos.ts`, `projetarCasos`) | a conversa não aparece na Fila do painel |
| **nunca vai ao grupo** | pergunta 2 da guarda (§5.1) | qualquer gatilho sobre ela → `False` |
| **captura marcada `interno`** | `attendance_capture.py:109-117` passa a ler a tabela **além** do JSONB, e o Observador **marca** em vez de só descartar | `observed_events`/a conversa carregam a marca; o dado não some, fica rotulado |

🔴 **Os quatro juntos, ou o bloco não fechou.** 📊 Hoje o JSONB entrega só o quarto, e mesmo esse com a lista sempre vazia. O guarda G-B1 fica vermelho se um dos quatro for removido.

### 6.5 O card Equipe

Sub-bloco **"Números que o agente nunca atende"**, dentro de `app/dashboard/personalizacao/equipe/` (`TeamClient.tsx`), abaixo da lista de membros:

- os telefones dos **membros** aparecem em modo leitura, com a origem escrita ("vem do cadastro de <fulano>") e um aviso de que editar o membro muda o número;
- os números **sem login** são adicionados ali: telefone + rótulo + tipo, com remoção;
- 💭 **a frase que explica, e ela é o produto:** *"O agente nunca responde a estes números, nunca abre caso para eles e nunca fala sobre eles no grupo. Use para o fixo da loja, o comercial e os celulares de quem não tem login aqui."*
- ⚠️ máscara na exibição pelo mesmo critério de `maskDestinationRef` — a tela não é lugar de imprimir número inteiro sem necessidade.

Rotas novas: `GET`/`POST`/`DELETE` em `app/api/dashboard/internal-numbers/`, **já nascendo** com `assertSameOrigin` + `requireCompanyMember({write:true})` + `writeAudit` (o padrão do BLOCO G — uma rota nova que nasça no padrão velho reprova).

**GATE B (G-B1, G-B2).** **MUTAÇÃO B:** cadastrar o número da casa da corretora X e provar que uma conversa **da corretora Y** com o mesmo número continua atendida normalmente.

---

## 7. BLOCO C — uma mensagem, inteira, e uma vez

### 7.1 `bloco_unico` nos três caminhos

📊 **Medido em 13/09/2026** com o motor real (`build_handoff_dossier` + `split_whatsapp_balloons`), sobre uma sessão sintética sem PII:

```
caracteres do dossiê ....... 429
balões hoje ................ 4      (136 · 16 · 69 · 201)
TARGET_LEN=300  HARD_LEN=500  MAX_BALLOONS=4     (balloons.py:17-19)
```

💭 A sessão é sintética (montei o dicionário); **o motor e a contagem são reais**. O BLOCO 0 refaz a medição sobre uma sessão do acervo.

O desvio já existe e está pronto: `whatsapp_service.py:157-160` — `bloco_unico=True` chama `_fatiar_documento` (teto de 3500 caracteres, nunca parte no meio de uma linha) em vez de `split_whatsapp_balloons`. **O conserto é passar a flag nos três caminhos que não a passam** (`dispatch_router.py:3304`, `:201`, `dispatch_watchdog.py:315`) — e nos outros da §3.2 que mandarem texto estruturado.

⚠️ **O conserto de 18/08 foi aplicado num caminho só.** É por isso que o guarda G-C1 varre os **três**, e a mutação tira a flag de **um** para provar que ele vê.

### 7.2 Espera vencida = 1 aviso

📊 Hoje: `AVISOS_ATE_EXPIRAR = 3` (`o_fim_do_atendimento.py:478`); o job roda a cada 10 min (`buffer_processor.py:573-579`); no 10/09 saíram **3 avisos idênticos em 20 minutos**. Já existe o agrupamento por conversa (`handoff_watchdog.py:532-544`) — o que falta é o teto.

**O contrato novo:** **um** aviso ao grupo por vencimento de espera. Os avisos 2 e 3 **não somem**: viram linha do resumo das 19h ("2 esperas venceram e ninguém respondeu"). ⛔ O `AVISOS_ATE_EXPIRAR` **continua 3** para o ciclo interno de expiração — o que muda é quantos **chegam ao grupo**.

🔴 A distinção importa: quem corta o contador interno quebra `deve_expirar_a_conversa` (`o_fim_do_atendimento.py:870-876`) e a conversa nunca expira. O guarda tem de provar que a expiração continua acontecendo com **1** mensagem.

### 7.3 `ura_silent` e `human_silent` viram linha do resumo

📊 `dispatch_watchdog.py:31-38`: `URA_SILENT_ALERT_S=120`, `HUMAN_ALERT_S=1200`, `NEVER_STARTED_S=300`, `SESSION_DEADLINE_S=2700`. Cada um manda ao grupo **uma vez por sessão** (flags `wd_*`).

Passam a **não** ir ao grupo em tempo real. Viram evento contável (`work_events`, tipo `vigia.<finding>`) e **linha do resumo das 19h**: 💭 *"⏱️ 2 acionamentos ficaram esperando a URA e 1 passou do prazo da sessão."*

⚠️ **Exceção que fica:** `never_started` **continua** indo ao grupo na hora, porque significa *"o acionamento não começou"* — é o único dos quatro em que ninguém está trabalhando e o segurado está esperando do zero. 💭 Nota da alternativa "mandar os quatro para o resumo": 72; com a exceção: 88.

### 7.4 Queda de canal vai ao dono, não ao grupo

`whatsapp/alerts.py:255` passa a resolver o destinatário assim, nesta ordem:

```
1. `integrations.alert_target` com número explícito, se houver     (é o que a coluna
   FOI CRIADA para ser — o COMMENT da migration 20260703_01 diz literalmente
   "destino do alerta de desconexão (nunca o próprio número de atendimento)")
2. o telefone do MEMBRO `is_owner` daquela corretora (users_v2.phone)
3. ⚠️ se nenhum dos dois existir: o grupo, COM a frase dizendo por quê
```

💭 *"⚠️ O WhatsApp de atendimento da <corretora> caiu às 14:52 e o agente parou de responder. (Este aviso veio para o grupo porque não há um responsável cadastrado — cadastre em Personalização → Equipe.)"*

🔴 **O passo 3 é obrigatório e não é preguiça.** Um aviso de canal caído que não chega a ninguém é pior que um aviso no grupo errado: é o produto silenciosamente fora do ar. A frase que explica é o que impede o passo 3 de virar permanente.

### 7.5 Reabertura de caso não fura o marcador

📊 No 10/09 saíram **3 dossiês** (17:14, 17:21, 17:35) sobre a mesma conversa, em 21 minutos, porque a **sessão de acionamento** reabriu três vezes e o marcador de "já entreguei o dossiê" vive **na sessão** (`session["dossier_sent"]`, `dispatch_watchdog.py:437`).

**O contrato:** a chave de deduplicação passa a ser **`(company_id, conversation_id, tipo)`**, não `(sessão)`. A conversa é a unidade — é a mesma lição que `handoff_watchdog.py:522-537` já aprendeu para as esperas (*"a mesma conversa pode ter DUAS esperas ativas ao mesmo tempo… seis em trinta minutos"*).

Janelas por tipo (💭, a confirmar no BLOCO 0):

| tipo | janela de dedup | por quê |
|---|---|---|
| `pedido_de_ajuda` | a cadência do re-alerta (`HANDOFF_REALERTA_HORAS`, hoje 6 h) | é o mesmo pedido |
| `espera_vencida` | por vencimento (§7.2 **desta SPEC**) | um por prazo que virou |
| `sinistro` | 24 h | um sinistro por dia por conversa; dois sinistros diferentes no mesmo dia são 💭 caso raro e a SPEC prefere repetir a calar |
| `conclusao` | 24 h | uma conclusão por conversa por dia |
| `resumo_diario` | 1 por dia por corretora | por construção |

⚠️ **O marcador continua no Redis** (`human_handoff.reivindicar_o_aviso`, `_CHAVE_DO_MARCADOR`, `human_handoff.py:71,186-206`), e continua devolvendo a vez quando o envio falha (`_devolver_a_vez`, `handoff_watchdog.py:372`). O que muda é a **chave**, não o mecanismo. ⛔ Nada de tabela de dedup nova.

**GATE C (G-C1 … G-C4).** **MUTAÇÃO C:** voltar a chave para a sessão → os 3 dossiês do 10/09 voltam → vermelho.

---

## 8. BLOCO D — os quatro modelos

> 💭 **Toda a copy desta seção é ilustrativa** (CLAUDE.md §12.1). É o formato e os campos que são contrato; as palavras exatas passam pela régua de língua humana e podem melhorar. ⛔ O que **não** é ilustrativo: quais campos existem, quais não existem, e a ordem.

### 8.0 O que foi retirado, de propósito, e por quê

🔴 **Esta seção reverte duas decisões escritas da SPEC-071.** O executor precisa saber que é reversão deliberada, não esquecimento:

| o que sai | quem tinha decidido | por que sai agora |
|---|---|---|
| **as últimas mensagens da conversa** | SPEC-071 3.4, *"a conversa com autor de verdade"* (`human_handoff.py:783-794`) | 📊 No piloto, o dossiê com histórico virou 4 balões e a atendente lia o último, que é o menos importante. O resumo em parágrafo entrega o mesmo em 3 linhas |
| **o link do painel** | SPEC-071 3.4, *"não tinha link… e ela que procure na lista"* (`_link_da_conversa`, `human_handoff.py:804`) | 📊 §1.5 causa 3: no celular, **o número clicável custa um toque e o painel custa uma página**. O piloto provou a decisão errada |
| **`telefone_curto` (4 dígitos)** | `insurer_dispatch_service.py:3597`, por privacidade no histórico do grupo | o grupo é da própria corretora, o segurado é cliente dela, e 4 dígitos **impedem a ação**. O número inteiro volta — **clicável** |

⚠️ **O contra-argumento de `telefone_curto` continua válido para OUTRO lugar:** o dossiê fica no histórico do grupo para sempre. A mitigação é que os quatro modelos **não** levam CPF completo onde não é necessário (só o 🆘, que precisa dele para achar a apólice) e **nunca** levam o texto das mensagens.

**Gatilho de retorno:** se uma corretora pedir o link do painel de volta, ele volta como **preferência do destino** (`human_support_destinations.metadata`), não como padrão.

### 8.1 🆘 PRECISO DE AJUDA

**Quando:** o agente pediu humano — por incapacidade ou por regra.

```
🆘 *PRECISO DE AJUDA*
────────────────────
*Etapa:* acionamento de assistência — na URA da Allianz
*O que aconteceu:* o menu pediu para escolher entre três opções e eu não
consegui responder do jeito que ele aceita. Tentei duas vezes.

*Resumo:* O segurado tem um vazamento embaixo da pia da cozinha, começou hoje
de manhã e ele já fechou o registro. Confirmei a apólice residencial vigente,
peguei o endereço e ele prefere o período da tarde. Falta só escolher a opção
do menu e pegar o protocolo. Ele já sabe que alguém da equipe vai assumir.

*Seguradora:* Allianz → https://wa.me/5511XXXXXXXXX
*Ramo / serviço:* residencial · encanador
*Segurado:* Fulano de Tal
*CPF/CNPJ:* 000.000.000-00
*Quando:* 13/09 às 14:07
*WhatsApp do segurado:* https://wa.me/5547XXXXXXXXX
```

**Campos, e o contrato:**

| campo | obrigatório | origem |
|---|---|---|
| etapa | sim | a fase do caso em linguagem humana — ⛔ nunca `assistencia.residencial.encanador` |
| o que aconteceu | sim | uma ou duas frases, sem chave técnica |
| resumo | sim | **um parágrafo**, não campos soltos — evolui `_narrativa` (`human_handoff.py:771`) |
| seguradora + `wa.me` | quando houver | o WhatsApp da seguradora, do cadastro de contatos que já existe |
| ramo / serviço | quando houver | ficha |
| nome | sim | `conversations.user_name`, com a regra que já existe de não repetir o número (`human_handoff.py:761-763`) |
| CPF/CNPJ | quando houver | ficha |
| data/hora | sim | fuso da corretora |
| WhatsApp do segurado | **sim** | `https://wa.me/55DDDNÚMERO` |
| ⛔ link do painel | **não** | §8.0 |
| ⛔ últimas mensagens | **não** | §8.0 |

**O campo `motivo`, e ele é o que faz a conta das 19h existir:**

```
motivo_classe = 'incapacidade'   ura_travou · dado_faltante · sentinela_esgotou
motivo_classe = 'regra'          vitima · cliente_pediu_humano · valor_acima_do_limite
                                 · fora_do_escopo · segurado_irritado
```

🔴 **`motivo` não aparece no texto da mensagem** — ele vai na carga de `work_events` (`payload_redacted.motivo`, `payload_redacted.motivo_classe`). Quem lê no grupo lê *"o que aconteceu"*, que é prosa. Quem conta lê a chave. ⚠️ CLAUDE.md §12.1: se um dia o nome do campo mentir sobre o que ele guarda, conserta-se o **campo**.

🔴 **QUEM ESCREVE `motivo_classe` — e hoje NINGUÉM escreve.**

📊 Medido em 13/09: `human_handoff_reason` está **vazio em 129 de 131** conversas `HUMAN_REQUESTED`, e as 2 preenchidas são prosa livre. `grep -rn "motivo_classe" backend/app` → **0**. O campo não existe e não tem escritor designado.

**O escritor desta SPEC, nomeado:** o caminho que monta o 🆘 PRECISO DE AJUDA — `backend/app/agents/tools/human_handoff.py` (a tool `_arun`, :1182, e `_montar_dossie`, :710) — classifica `motivo` e `motivo_classe` **no ato de pedir ajuda**, e o BLOCO E os grava em `work_events.payload_redacted`. Os gatilhos automáticos que não sabem o motivo (re-alerta, espera vencida) gravam `desconhecido` **explicitamente**, nunca omitem a chave.

⚠️ **E um motivo desconhecido NÃO cai em `regra`.** Se caísse, hoje — com zero escritores — **todo** pedido de ajuda sairia do denominador e a eficiência das 19h daria ~100% sem medir nada, contra a regra desta própria SPEC (*número sem escritor vira "não medido", nunca estimativa*).

```
motivo_classe = 'desconhecido'   → fora do NUMERADOR e fora do DENOMINADOR,
                                   e com LINHA PRÓPRIA e visível no resumo
```

💭 No resumo: `📋 4 ajudas sem motivo classificado — a eficiência não as conta`.

🔴 **E o guarda fica vermelho quando a fatia de desconhecidos passa do limite:** 💭 **30%** dos pedidos de ajuda do dia (a confirmar no BLOCO 0 contra o volume real). Acima disso, o resumo **não publica o número de eficiência** — publica *"ainda não dá para medir: N de M pedidos de ajuda saíram sem motivo"*. ⛔ Um número que se calcula sobre a minoria classificada é pior que número nenhum, porque parece medição.

### 8.2 🚨 NOVO SINISTRO

**Quando:** o agente identificou um sinistro. ✅ Passa pela guarda **sempre** (§5.3).

```
🚨 *NOVO SINISTRO*
────────────────────
*Tipo:* colisão com terceiro
*Segurado:* Fulano de Tal · CPF 000.000.000-00
*Apólice:* Porto Seguro · auto · vigente até 12/03/2027
*Quando:* hoje, 13/09, por volta das 13h30, em Joinville

*Resumo:* O segurado bateu na traseira de outro carro numa avenida, com
chuva. Ninguém se feriu e os dois carros andam. Ele já trocou dados com o
outro motorista e mandou três fotos. O carro dele está com o para-choque
dianteiro amassado e o farol esquerdo quebrado.

*⚠️ Pontos de atenção:*
• há terceiro envolvido — precisa dos dados dele
• o segurado não sabe se tem cobertura para terceiros
• ainda não há boletim de ocorrência

*WhatsApp do segurado:* https://wa.me/5547XXXXXXXXX
```

⚠️ **"Pontos de atenção" é o lugar reservado para o checklist por tipo da P-PILOTO-04** (colisão, roubo, incêndio, empresarial, condomínio). Esta SPEC entrega **o lugar e o mecanismo**; o **conteúdo** por tipo vem com a base de produtos (EXTRA-001.5). 🔴 Enquanto não vier, o campo é preenchido com o que a ficha sabe que **falta** (`_o_que_falta`, `human_handoff.py:776`) — e diz que é isso. ⛔ Não inventar checklist clínico sem fonte.

### 8.3 ✅ ATENDIMENTO CONCLUÍDO

**Quando:** o caso fechou — protocolo entregue, agendamento confirmado, link enviado, ou o segurado disse que estava resolvido. ✅ Passa pela guarda sempre.

**Curto. Uma mensagem que ninguém precisa abrir.**

```
✅ *ATENDIMENTO CONCLUÍDO*
Fulano de Tal · encanador pela Allianz · protocolo 2026-1234567
Resolvido em 34 min, das 14:07 às 14:41. 🤖 agente
```

Variações 💭:
- sem protocolo: `link de agendamento enviado ao segurado`
- concluído por humano: `Resolvido pela Regina em 1h12.` — 🔴 **a atendente aparece pelo nome, o agente assina 🤖** (D-PILOTO-12, item 5)
- só dúvida: ⛔ **não manda nada.** Uma dúvida respondida vira **número no resumo**, nunca mensagem própria — senão o modelo ✅ vira o novo ruído

### 8.4 📊 ATENDIMENTOS REALIZADOS — às 19h

**Quando:** uma vez por dia, às **19h no fuso da corretora**, por corretora, se houve movimento. ⛔ Dia sem nada não manda mensagem dizendo que não houve nada.

```
📊 *ATENDIMENTOS REALIZADOS — 13/09*
────────────────────
*Eficiência: 85%*  (11 de 13)

✅ 9 acionamentos com a mensagem enviada ao segurado
🚨 2 sinistros com dossiê entregue
🆘 2 vezes precisei de ajuda porque não consegui
     • 1 a URA travou   • 1 faltou um dado que o segurado não tinha

Fora da conta:
📋 3 passados por regra (2 o segurado pediu humano · 1 tinha vítima)
📋 1 ajuda sem motivo classificado — a eficiência não a conta
💬 12 dúvidas respondidas
🤝 4 conversas que a equipe já conduzia
🔕 6 conversas em que fiquei em silêncio pela janela
⏱️ 2 acionamentos ficaram esperando a URA; 1 passou do prazo da sessão

🤖 agente
```

**A fórmula, exatamente como D-PILOTO-13 a fixou:**

```
              acionamentos com mensagem enviada ao segurado  +  sinistros com dossiê
eficiência = ───────────────────────────────────────────────────────────────────────
             os mesmos  +  ajudas cujo motivo_classe = 'incapacidade'
```

🔴 **Regras que o guarda G-D2 congela:**

1. Sucesso = **até a mensagem do acionamento chegar ao segurado** (protocolo, link **ou** agendamento). Pós-acionamento **fora** — o segurado que não respondeu ao follow-up não piora a nota.
2. **Sinistro conta como sucesso** quando a coleta inicial foi feita **e** o dossiê saiu.
3. **Só `motivo_classe='incapacidade'` entra no denominador.** *Ajuda por regra* fica fora — 🔴 *porque contar contra pune o agente por obedecer*, e é a objeção que o Founder aceitou (nota 88 × fórmula pura 70). E *ajuda sem motivo classificado* (`desconhecido`) fica fora **dos dois**, com linha própria — §8.1. ⛔ Desconhecido **não** é regra: tratá-lo como regra, com zero escritores hoje, daria ~100% de eficiência sem medir nada.
4. Dúvidas, conversas já com humano, caídas na janela e pós-acionamento aparecem como **contagem própria**, para o número não esconder o volume.
5. ⚠️ **Denominador zero não é 0%, é "sem acionamentos hoje".** Um dia só de dúvidas não tem eficiência — tem 12 dúvidas.

**De onde vem cada número:** `work_events` do dia, por `company_id`, pelos tipos que os blocos A–E gravam. ⛔ Nenhuma tabela de métrica nova; ⛔ nenhum recontar do zero sobre `messages`.

🔴 **E o resumo é onde o que foi calado reaparece.** Toda mensagem que a guarda suprimiu vira contagem aqui — as linhas 🤝, 🔕 e ⏱️ existem exatamente para isso. Nada é perdido; é **adiado** para uma linha (CLAUDE.md §11.1: *deixar pronto e desligado é aceitável; deixar pronto e não anotado, não*). Um resumo em que a soma das linhas "fora da conta" não bate com os `grupo.calado` do dia é um defeito, e o guarda G-D2 mede isso.

⚠️ **O executor vai descobrir que faltam escritores.** 📊 `work_events` com `agente.cerebro | agente.sentinela | agente.vigia`: **0 de 0 em toda a base** (§11.2c do diagnóstico) — e `handoff.realertado`: 0. Quando um número não tiver escritor, o resumo diz **"não medido"** e a pendência vai para `PENDENCIAS.md`. 🔴 **Nunca estimar.** Um resumo que inventa um número perde a corretora na primeira semana.

### 8.5 O formato do link, e ele tem guarda próprio

```
https://wa.me/55DDDNÚMERO       ⛔ sem +, sem espaço, sem parêntese, sem traço
```

📊 O número entra como chega em `conversations.user_phone` (dígitos), normalizado por `_variantes_do_telefone`. Se já vier com `55`, não duplica. Se vier com 10 dígitos (sem nono), o link sai assim mesmo e **não se inventa o nono dígito**.

⚠️ `_fone_bonito` (`human_handoff.py:463`) continua existindo para o texto **legível**; o link é outra coisa. Os dois no mesmo modelo: 💭 `*WhatsApp do segurado:* https://wa.me/5547XXXXXXXXX`.

### 8.6 Os quatro passam pela régua de língua humana

P-PILOTO-12: `problemas_de_lingua` (`test_o_caso_se_explica_sozinho.py:1181`) roda hoje só nas cartas e na novidade ao cliente. Passa a rodar sobre **os quatro modelos renderizados** e sobre `_montar_dossie`/`_dossie_de_pos_acionamento`. 🔴 Nada de chave técnica, nada de `snake_case`, nada de sigla interna no que a Regina lê.

**GATE D (G-D1, G-D2).** **MUTAÇÃO D:** devolver o link do painel a um modelo → G-D1 vermelho. Contar `vitima` no denominador → G-D2 vermelho (o número muda).

---

## 9. BLOCO E — todo envio ao grupo fica contado

### 9.1 O contrato

Toda saída para o grupo grava **uma linha por mensagem efetivamente enviada** em `platform_sends`:

```
company_id   a corretora
phone        o destination_ref do destino (o JID do grupo) — ⛔ nunca o telefone do segurado
kind         grupo_pedido_de_ajuda | grupo_sinistro | grupo_conclusao | grupo_resumo_diario
             | grupo_espera_vencida | grupo_vigia | grupo_queda_de_canal | grupo_cobranca
summary      💭 "pedido de ajuda — ura_travou — conversa <8 primeiros do id>"  (≤300, sem PII)
sent_at      quando saiu
```

⚠️ **O prefixo `grupo_` é só legibilidade.** 🔴 O que decide se a linha conta na cota do segurado **não é o prefixo** — é a allowlist de §9.2. Um `kind` novo que não esteja nela **não conta**, por padrão.

📊 Hoje: `platform_sends` tem **19 linhas na base inteira** (`billing` 18 · `acionamento_protocolo` 1), a mais recente de 11/09. **Zero de grupo.** A pergunta *"quantas mensagens o grupo recebeu ontem?"* não tem resposta em lugar nenhum — é o que `handoff_watchdog.py:418-421` já registra por escrito.

⚠️ **Uma linha por MENSAGEM, não por intenção.** 📊 O mesmo defeito está medido na cobrança (§9.2 do diagnóstico: *"grava 1 linha por parcela; o canal recebeu 4"*). Com `bloco_unico` do BLOCO C o número passa a ser 1 de verdade — mas o contador conta o que **saiu**, e o guarda G-E1 compara com o número de balões.

### 9.2 🔴 O ACHADO QUE PODE CALAR O ATENDIMENTO — e ele não estava no diagnóstico

📊 Medido em 13/09/2026 em `backend/app/services/platform_outbound.py`. **São TRÊS leituras sem filtro de `kind`, não uma** — e as três alimentam coisas diferentes:

```python
# :606-610  `recentes` — 26 h, para a cota da HORA e do DIA
recentes = (db.client.table("platform_sends").select("sent_at")
            .eq("company_id", str(company_id)).gte("sent_at", desde)
            .order("sent_at", desc=True).limit(1000).execute().data or [])
# :611-613  `primeiro` — a data do primeiro envio  →  dias_de_uso
# :614-616  `total_res` — count(*) de TODA a história  →  total
```

`recentes` governa a cota imediata (12/h · 20 novos/dia, SPEC-063 Bloco C). 🔴 **Mas `primeiro` e `total_res` alimentam `maturidade_do_canal(dias_de_uso, total)`** (chamada em **:697**, definida em **:424-441**), que exige *"≥ 30 dias de histórico **E** ≥ 200 envios registrados"* e decide o `teto_do_dia` (**:444-445**).

🔴 **As duas consequências, e a segunda é pior:**

1. **A cota imediata:** cada mensagem ao grupo consome a cota de mensagens ao **segurado**. Num dia movimentado, o resumo das 19h e os pedidos de ajuda empurram o governador ao teto e o produto **para de falar com clientes** — e o motivo seria invisível.
2. **A maturidade:** um canal que **nunca falou com um segurado** passa a "amadurecer" com mensagens internas e **sobe o teto diário**. É o contrário exato do que `maturidade_do_canal` existe para provar — o próprio docstring diz que volume sozinho mente. Um número novo ganharia reputação de veterano contando conversas consigo mesmo.

**O conserto, obrigatório antes da primeira linha nova, e ele é uma ALLOWLIST — não um prefixo.**

```
❌ excluir `kind LIKE 'grupo_%'`        frágil: qualquer kind interno futuro nasce inseguro
✅ contar SÓ os kind que FALAM COM O SEGURADO
```

⚠️ **Por que a inversão, e não o prefixo:** a EXTRA-001.6 (`SPEC-EXTRA-001.6:408-409, 430`) cria `billing_nota` — a **nota interna à atendente** — e `billing_doc`. `billing_nota` **não começa com `grupo_`** e, sob um filtro por prefixo, **consumiria a cota do segurado** exatamente como as mensagens de grupo. 📊 E a 001.6 mede o efeito: 7 parcelas de 5 segurados passam de 7 para **17 linhas** em `platform_sends`.

**O contrato:** uma constante única — 💭 `KINDS_QUE_CONTAM_NA_COTA_DO_SEGURADO = {"billing", "billing_doc", "acionamento_protocolo", …}` — aplicada às **três** leituras. 🔴 Alternativa equivalente e aceitável: coluna `conta_na_cota boolean not null default false` em `platform_sends`, preenchida pelo escritor. Em qualquer das duas, **o padrão é NÃO contar**, para que todo `kind` interno futuro nasça seguro.

🔴 **Guarda com linha de controle** (CLAUDE.md §9.3): o teste insere N linhas `grupo_*` **e** N linhas `billing_nota`, e prova que cota, `dias_de_uso` e `maturidade_do_canal` **não mexeram**; a linha de controle insere N linhas `billing` e prova que **mexem** — senão o teste estaria provando que o governador não funciona.

⚠️ **Contrato compartilhado com a 001.6.** A lista de `kind` é um arquivo-hub entre as duas SPECs. Quem executar primeiro cria a constante **já contemplando `billing_nota`/`billing_doc`**; quem executar depois acrescenta os seus. ⛔ Duas listas = a próxima regressão.

💭 Nota da alternativa "gravar os envios de grupo numa tabela própria": 45 — seria ledger paralelo (§5), e a pergunta do Founder é *"quantas saíram?"*, que tem de ter **uma** resposta.

### 9.3 O diário continua

`work_events` continua recebendo o evento **com significado** (`payload_redacted.motivo`, `motivo_classe`, `tipo`, `calou_porque` quando a guarda calou). **Os dois registros têm papéis diferentes e nenhum substitui o outro:**

```
platform_sends   quantas MENSAGENS saíram          (contabilidade do canal)
work_events      o que cada uma SIGNIFICAVA        (a conta das 19h, e a auditoria)
```

🔴 **E a guarda grava quando CALA.** Um silêncio sem rastro é indistinguível de um job que não rodou — e é exatamente como esta SPEC pode virar o próximo defeito invisível. Tipo 💭 `grupo.calado`, com `calou_porque`.

**GATE E (G-E1).** **MUTAÇÃO E:** remover o registro de um dos caminhos → a contagem não bate com os balões → vermelho.

---

## 10. BLOCO F — o gate de ligar o agente

📊 Hoje não existe. Medido em 13/09: ligar o agente é um `PUT /agents/{id}` genérico (`app/api/agents.py:260`, `agent_service.py:137-179`), e a **única** validação é de prompt. A checagem de destino existe, mas é **posterior e passiva**: `main.py:876-921` conta `corretoras_ligadas_sem_destino_de_suporte` no health — e a docstring (:879-884) registra o incidente que a criou (*agente ligado + zero destinos = 5 handoffs que não chegaram a ninguém*).

**O contrato:** ligar o agente de atendimento passa a exigir, **no ato**:

| pré-condição | como se verifica | frase de recusa 💭 |
|---|---|---|
| **destino de suporte ativo** | `resolver_destino_de_suporte(company_id)` devolve destino | *"Antes de ligar o agente, diga para onde ele pede ajuda. Cadastre o grupo da equipe em Personalização → Suporte humano."* |
| **canal conectado** | `integrations.channel_status` / o heartbeat que já roda (`channel_heartbeat_check`, `buffer_processor.py:519`) | *"O WhatsApp da corretora está desconectado. Conecte o número em Conectores → WhatsApp e tente de novo."* |

🔴 **Recusa em frase humana, com o caminho da tela junto.** ⛔ Nunca `destination_not_configured`, nunca código de erro cru na tela (CLAUDE.md, e a régua de língua do §8.6).

⚠️ **Desligar nunca é bloqueado.** Uma trava que impede **desligar** um agente é um produto que não obedece — e o botão de desligar é a saída de emergência da atendente.

⚠️ **E a trava é no ato de LIGAR, não no runtime.** `attendance_agent_active` (`attendance_capture.py:267-295`) continua sendo o portão fail-closed de runtime, e não muda. Misturar os dois é como se cria o produto que se desliga sozinho no meio de um atendimento porque o heartbeat piscou.

**GATE F (G-F1).** **MUTAÇÃO F:** apagar o destino ativo de um tenant de teste e tentar ligar pela rota → 400 com a frase; ligar com destino → 200.

---

## 11. BLOCO G — as 6 mutações ganham papel, origem e auditoria

### 11.1 O que está aberto hoje

📊 Medido em 13/09. Nenhuma das seis chama `requireCompanyMember`, nenhuma chama `assertSameOrigin`, nenhuma chama `writeAudit`.

⚠️ **E elas não autenticam todas do mesmo jeito** — a conclusão é a mesma, a prova é diferente, e o executor precisa das duas:

```
as 3 de `portal-credentials` / `whatsapp-channel`   `resolveSessionCompany()`
                                                    (`lib/auxiliaries/server.ts:31`)
as 3 de `support-destinations`                      `getIronSession` CRU + `companyIdDoSeletor()`
                                                    (`…/support-destinations/route.ts:25-27`)
```

🔴 **Nenhum dos dois caminhos devolve papel.** `resolveSessionCompany` devolve `{userId, companyId}`; `companyIdDoSeletor` devolve **só** `string | null` (`lib/attendance/support-destinations.ts:48`). A rota não tem o papel disponível **nem se quisesse checá-lo** — é causa estrutural, não esquecimento pontual. Por isso o conserto é trocar o resolvedor, não acrescentar um `if`.

| # | arquivo:linha | método | o que faz | o que um `member` comum consegue hoje |
|---|---|---|---|---|
| 1 | `app/api/attendance/support-destinations/route.ts:72` | POST | cria destino | **redirecionar o dossiê** (que leva CPF do segurado) para um destino próprio |
| 2 | `app/api/attendance/support-destinations/[destinationId]/route.ts:23` | PATCH | edita destino | idem, sobre o destino existente |
| 3 | `…/[destinationId]/route.ts:108` | DELETE | desativa destino | **deixar a corretora sem destino** — e os handoffs param de chegar |
| 4 | `app/api/dashboard/portal-credentials/route.ts:58` | POST | grava/rotaciona senha de portal de seguradora | trocar a credencial da corretora |
| 5 | `app/api/dashboard/portal-credentials/route.ts:78` | DELETE | apaga credencial | derrubar a cobrança e os portais |
| 6 | `app/api/dashboard/whatsapp-channel/route.ts:236` | POST | **6 ações num único body.action** (:244): `set-auxiliary-authorization` (:263), `set-alert` (:306), `disconnect` (:318), `retry`/`cancel` (:328), `pairing` (:349) | **desconectar o WhatsApp da corretora** |

🔴 **A #3 e a #6 são as que tocam esta SPEC diretamente:** a primeira apaga o destino que o BLOCO F acaba de exigir; a segunda derruba o canal cujo aviso de queda o BLOCO C acaba de redirecionar. Sem o BLOCO G, os dois blocos são trancas numa porta sem fechadura.

### 11.2 O padrão pronto, e ele é literal

```ts
// app/api/dashboard/team/route.ts:46-50  ← a referência que o juiz abre
export async function POST(req: NextRequest) {
  const xo = assertSameOrigin(req);
  if (xo) return NextResponse.json({ ok: false, error: xo.error }, { status: xo.status });
  const auth = await requireCompanyMember({ write: true });
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });
```

As seis passam a: `assertSameOrigin(req)` → `requireCompanyMember({ write: true })` → usar `auth.ctx.companyId` (⛔ nunca o `company_id` do corpo) → `writeAudit` (`lib/vault/server.ts:55`, que grava `actor_user_id`).

⚠️ **`requireCompanyMember({write:true})` exige `canWriteTenantConfig`** = `owner|admin|admin_company|master_admin` (`admin-auth-policy.ts:5,150`). 🔴 **Isto restringe quem pode mexer.** É intencional — mas o BLOCO 0 tem de **medir quem hoje usa essas telas** na Resulta e na AutoFleet (📊 `select role, is_owner, count(*) from company_members group by 1,2`) e a mudança entra na Caixa do Founder. ⛔ Se a Saionara for `member`, descobrir isso pelo suporte na segunda-feira é o defeito, não a trava.

💭 Alternativa medida: usar `ATTENDANCE_TOGGLE_ROLES` (`admin-auth-policy.ts:42`, que inclui `attendant` e `member`) para a #6 quando a ação for `disconnect`/`retry` — nota 70; usar `write:true` em todas — nota 85, porque destino de suporte e credencial de portal **são configuração de corretora**, não operação de atendimento.

### 11.3 E `support-destinations` escreve direto no Supabase

⚠️ Achado colateral: `lib/attendance/support-destinations.ts:20` usa `createClient(..., SUPABASE_SERVICE_ROLE_KEY)` e **escreve direto na tabela**, sem passar pelo backend Python (diferente de `portal-credentials`, que é proxy). Não é defeito por si — é o padrão de BFF do projeto — mas significa que **a única proteção dessas três rotas é o código delas**. RLS não protege nada contra service role (CLAUDE.md §7).

**GATE G (G-G1).** **MUTAÇÃO G:** remover `requireCompanyMember` de **uma** das seis → o teste que chama a rota como `member` recebe 200 em vez de 403 → vermelho.

---

## 12. Guardas e mutações — 12, o teto de D-PILOTO-14

> 🔴 Todos sobre o **MOTOR** e o **ACERVO REAL** (CLAUDE.md §9.4). ⛔ Proibido teste que reimplementa a regra: quem afirmar algo sobre a janela chama `ultima_palavra_humana`, **nunca** um regex sobre `payload`.
> 🔴 Cada guarda tem a mutação que o deixa **vermelho**, e a mutação roda em worktree próprio, restaurando por cópia (AAA §10).

| # | guarda | afirma, sobre o motor e o acervo | a mutação que o deixa vermelho |
|---|---|---|---|
| **G-A1** | `test_o_grupo_so_fala_de_quem_precisa.py` | Rodando `o_grupo_pode_saber` sobre o acervo: **todas as conversas elegíveis medidas no BLOCO 0 calam** — a asserção é contra o conjunto que o executor mediu, ⛔ nunca contra o literal `58` (§12.1). E a linha de controle: uma conversa **sem** palavra humana **passa** — senão o guarda provaria só que a função sempre devolve `False` | desligar a pergunta 4 → as elegíveis voltam a passar |
| **G-A2** | mesmo arquivo | **Todo** ponto que resolve destino de suporte passa pela guarda: varredura de AST sobre os 11 caminhos da §3.2, exigindo `o_grupo_pode_saber` no caminho de cada um | acrescentar um envio novo ao grupo sem a guarda → vermelho |
| **G-A3** | mesmo arquivo | `janela_de_silencio_dias` = **0** devolve **todas** as elegíveis medidas; e **não existe** no repositório nenhuma constante/env de janela só do grupo (`grep` por `JANELA_DO_GRUPO`, `GRUPO_SILENCIO`) | criar um segundo número → vermelho |
| **G-B1** | `test_o_numero_da_casa_nao_e_cliente.py` | Um número cadastrado produz **os quatro efeitos**: 0 respostas · fora da Fila · guarda `False` · captura marcada `interno`. 🔴 **E um caso com telefone de MEMBRO mal formatado** (📊 `users_v2.phone` está preenchido em 796/796, mas nada prova formato nem que é WhatsApp): com `+55`, sem `55`, com e sem nono dígito, com máscara — todos casam por `_variantes_do_telefone` | remover **um** dos quatro → vermelho; e aceitar só o formato canônico → o caso mascarado passa a ser atendido → vermelho |
| **G-B2** | mesmo arquivo | **Duas corretoras reais:** o número da casa da corretora X **não** cala a conversa igual na corretora Y | trocar o `eq(company_id)` por leitura global → vermelho |
| **G-C1** | `test_o_dossie_chega_inteiro.py` | Os **três** dossiês renderizados **a partir de uma sessão do ACERVO** (acionamento A, watchdog C, atendimento), passados pelo **caminho real de envio**, dão **1** balão. Controle: o mesmo texto **sem** `bloco_unico` dá **> 1** — ⚠️ a asserção é `> 1`, ⛔ nunca o literal `4` (💭 o 4 veio de 429 caracteres sintéticos e muda com o conteúdo) | tirar `bloco_unico` de **um** dos três → vermelho |
| **G-C2** | mesmo arquivo | Um vencimento de espera → **1** mensagem ao grupo; e a conversa **ainda expira** ao terceiro aviso interno | voltar a 3 mensagens → vermelho; cortar `AVISOS_ATE_EXPIRAR` → o teste da expiração fica vermelho |
| **G-C3** | mesmo arquivo | Replay das **3 reaberturas de sessão do 10/09** → **1** dossiê. Controle: duas conversas diferentes no mesmo minuto → **2** dossiês | chave de dedup por sessão → 3 dossiês → vermelho |
| **G-C4** | mesmo arquivo | Queda de canal vai ao dono; e **sem** dono cadastrado vai ao grupo **com a frase que explica** | mandar sempre ao grupo → vermelho |
| **G-D1** | `test_os_quatro_modelos_falam_portugues.py` | Os quatro modelos renderizados: `problemas_de_lingua` **vazia**; `wa.me/55…` presente e sem `+`; **ausência** de link de painel e de bloco de mensagens; ✅ curto (💭 ≤ 3 linhas) | devolver o link do painel ou uma chave técnica → vermelho |
| **G-D2** | `test_a_eficiencia_das_19h_diz_a_verdade.py` | A fórmula **reconstruída sobre `work_events` do acervo** (AAA §5 ④): ajuda por **regra** fora do denominador; sinistro no numerador; denominador 0 vira "sem acionamentos", não 0%. 🔴 **E `desconhecido` fica fora dos DOIS, com linha própria**; acima do limite de fatia (💭 30%) o resumo **não publica** o número | mover `vitima` para `incapacidade` → o número muda → vermelho; **e** tratar `desconhecido` como `regra` → a eficiência salta para ~100% com o acervo de hoje → vermelho |
| **G-E1** | `test_toda_mensagem_ao_grupo_e_contada.py` | Nº de linhas `grupo_*` em `platform_sends` = nº de mensagens que saíram. 🔴 **E as TRÊS leituras do governador ignoram o que não conta na cota**: depois de N linhas `grupo_*` **e** N `billing_nota`, a cota da hora, a do dia, `dias_de_uso` e **`maturidade_do_canal`** ficam iguais. Controle: N linhas `billing` **mexem** nas quatro | remover o registro de um caminho → vermelho; tirar o filtro de **qualquer uma** das três leituras → vermelho (a de `total_res` só aparece pela maturidade) |
| **G-F1 / G-G1** | `test_ligar_o_agente_tem_porteiro.py` | Ligar sem destino ativo → recusa com frase humana; com destino → liga. **E** as 6 rotas: chamada como `member` → **403**; sem header de origem → **403**; com `owner` → 200 e **uma linha de auditoria** | remover `requireCompanyMember` de uma das seis → 200 → vermelho |

### 12.1 🔴 A contagem, explícita — para ninguém estourar o teto ao "organizar"

```
ARQUIVOS DE GUARDA NOVOS ....  7   (o teto de D-PILOTO-14 conta ARQUIVOS: 12 é o limite)
LINHAS DESTA TABELA .........  13
GUARDAS NOMEADOS ............  12  (G-F1/G-G1 é UMA linha com dois nomes)
ASSERÇÕES DENTRO DELES ......  💭 ~30, e a última linha sozinha tem 5
                                  (recusa sem destino · liga com destino · member→403 ·
                                   sem origem→403 · owner→200 com auditoria)
```

⚠️ **G-F1/G-G1 é um arquivo só, de propósito:** o porteiro é uma ideia (*quem pode ligar, e quem pode configurar*) e as cinco afirmações são coesas. 🔴 **Um juiz que as separe em cinco arquivos não melhora a prova e estoura o teto de D-PILOTO-14** — se quiser separar, tem de dizer qual outro guarda sai.

⛔ **Nenhum guarda pode ficar verde por engano.** A SPEC-083 teve dois guardas verdes por detalhe de mutação; por isso cada linha acima nomeia a mutação **concreta**, e o relatório cola a **saída real** de cada mutação rodando e falhando.

---

## 13. Migrations

🔴 **Ler `docs/canon/MIGRATIONS-AUTHORITY.md` inteiro antes de escrever SQL.** Diretório canônico: `backend/supabase/migrations/`. Formato obrigatório do §7 daquele documento (cabeçalho com APPLY/VERIFY/ROLLBACK, EXPAND-FIRST, DESTRUTIVA).

**Uma migration nesta SPEC:** `company_internal_numbers`.

```sql
-- =============================================================
-- MIGRATION: company_internal_numbers
-- SPEC:      SPEC-EXTRA-001.3 — BLOCO B
-- OBJETIVO:  os números da própria corretora, com dono e rótulo
--
-- APPLY:     cria a tabela, o índice por (company_id, phone) e a RLS
-- VERIFY:    SQL read-only abaixo
-- ROLLBACK:  drop table (nova, sem leitor antes desta SPEC)
--
-- EXPAND-FIRST: sim — `integrations.alert_target.internal_numbers` CONTINUA
--               existindo e continua sendo lido por attendance_capture.py:109;
--               o leitor novo entra NA FRENTE, e a chave velha só é aposentada
--               numa SPEC futura, com backfill e prova
-- DESTRUTIVA:   não
-- =============================================================
```

**VERIFY** (SQL executável, não prosa):

```sql
select count(*) = 1 as tabela_existe
  from information_schema.tables
 where table_schema='public' and table_name='company_internal_numbers';

select count(*) = 1 as unique_por_corretora
  from pg_indexes
 where schemaname='public' and tablename='company_internal_numbers'
   and indexdef ilike '%UNIQUE%(company_id, phone)%';

select relrowsecurity as rls_ligada
  from pg_class where relname='company_internal_numbers';
```

**ROLLBACK:** `drop table if exists public.company_internal_numbers;` — seguro porque a tabela nasce nesta SPEC e o leitor do JSONB continua funcionando (expand-first).

⚠️ **Backfill:** 📊 hoje as listas `internal_numbers` estão **vazias em toda a base** — então não há backfill a fazer. 🔴 **Confirmar isso no BLOCO 0 por consulta**, não por leitura: se alguém tiver editado o JSONB à mão, o backfill entra e vira parte do APPLY.

⚠️ **Sem migration para `platform_sends`**: a tabela já tem `kind text not null` livre (`20260720_02_spec045_platform_sends.sql:7-17`), sem CHECK. Os `kind` novos entram como **dado**. ⛔ Não criar CHECK agora — congelaria a lista e a próxima SPEC teria de migrar para acrescentar um tipo.

---

## 14. Canário controlado em produção

### 🔴 A pré-condição que o canário tem de escrever ANTES de começar

📊 Medido em 13/09, e o executor **tem de remedir e colar no relatório antes do primeiro caso**:

```
human_support_destinations ........  4 linhas · 3 empresas · 1 ATIVA (nenhuma das pilotos)
companies.agent_enabled ...........  false em 5 de 5
work_events like 'handoff%' .......  0 linhas
```

⚠️ **Sem essa linha escrita, "0 mensagens ao grupo" será lido como "a guarda funcionou" — e não é: é o produto desligado.** Um canário que mede silêncio num sistema já mudo prova nada (CLAUDE.md §9.3: prove que o teste **consegue** ficar diferente).

**A ordem é obrigatória, e cada passo tem a sua prova:**

```
1. criar o destino do canário no tenant de teste          → resolver_destino_de_suporte devolve ELE
2. ligar o agente do tenant de teste                      → o gate do BLOCO F deixa (tem destino + canal)
3. medir a LINHA DE BASE: com o produto ligado e a guarda DESLIGADA, quantas mensagens sairiam
4. ligar a guarda e repetir                               → a diferença é o resultado
```

🔴 **O passo 3 é o que dá direito à conclusão** (CLAUDE.md §9.2: *a linha de controle é o que dá direito à conclusão*). ⛔ Sem ele, os 8 casos abaixo medem um sistema desligado.

### Antes

1. Identificar TESTE-A/TESTE-B em privado e conferir a conexão **real** do remetente — nome de instância não prova identidade.
2. Criar o **grupo de canário** (só o Founder dentro) e um destino `whatsapp_group` para ele, **no tenant de teste**. ⛔ Não tocar nos destinos de Resulta/AutoFleet, que estão `is_active=false` por decisão atual.
3. Provar as travas **com envio simulado** antes de qualquer envio vivo: o destino resolvido tem de ser o do canário, e um destino fora da allowlist tem de **recusar**.
4. Cadastrar TESTE-A como **número da casa** do tenant de teste (é o caso B).

### Casos mínimos — e cada um é um par com veredito oposto

| # | caso | o que tem de acontecer |
|---|---|---|
| **1** | **TESTE-A/B** conversa nova, agente pede ajuda | 🆘 chega ao grupo do canário, **1 balão**, `wa.me` clicável, sem link de painel |
| **2** | o Founder responde **pelo espelho** naquela conversa; o gatilho de re-alerta roda | **nada** chega ao grupo; `work_events` grava `grupo.calado` com o motivo |
| **3** | TESTE-A cadastrado como número da casa manda mensagem | agente **não responde**; **não** entra na Fila; **nada** no grupo; captura marcada `interno` |
| **4** | caso concluído | ✅ chega, curto |
| **5** | o resumo das 19h roda no fuso da corretora de teste | 📊 chega uma vez, com os números **reconciliáveis** com `work_events` do dia |
| **6** | destino desativado e tentativa de ligar o agente | recusa com a frase humana; reativado, liga |
| **7** | as 6 rotas chamadas como `member` | 403, e nada muda no banco |
| **8** | **par de controle:** conversa **sem** humano, pedido de ajuda | **chega** — prova que a guarda não cala tudo |

### Depois

Desativar o destino do canário, apagar as linhas de `company_internal_numbers` do tenant de teste **por id + company_id**, conferir que não ficou envio agendado, preservar `work_events`/`platform_sends` do canário **marcados** (⛔ append-only não se limpa por conveniência), e entregar as evidências com aliases.

⚠️ **Reversão de código não desfaz mensagem enviada.** O rollback para novos efeitos, preserva o registro e impede repetição.

---

## 15. Validação com Saionara e Regina

O Fable prepara roteiro e telas; **o Founder conduz**, pelos números de teste. ⛔ O executor não as contata.

O que se valida, e é a única pergunta que importa: **"você leria isso?"**

1. Os quatro modelos, impressos como chegam no celular — 💭 lidos em voz alta, sem explicação.
2. O resumo das 19h: o número faz sentido? A palavra "eficiência" não ofende?
3. O sub-bloco "Números que o agente nunca atende": elas sabem quais números cadastrar sem ajuda?
4. A frase de recusa de ligar o agente: ela diz o que fazer?
5. 🔴 A pergunta de controle: **"nos 3 dias de piloto, quantas dessas mensagens você teria ignorado?"**

Registrar o feedback só se realmente recebido. ⛔ Não bloquear o trabalho técnico esperando a agenda delas; ⛔ não declarar aceite antecipado. Distinguir sempre "não testado" / "aprovado no canário técnico" / "validado pela atendente".

---

## 16. Multi-tenant — a prova, não a promessa

CLAUDE.md §7. **O backend usa service role: RLS sem filtro no código não protege nada.**

| contrato novo | como o `company_id` chega | como se prova o isolamento |
|---|---|---|
| `o_grupo_pode_saber` | parâmetro **obrigatório**, sem default | G-A1 com duas corretoras: a mesma conversa-molde em X e Y, resultados independentes |
| `company_internal_numbers` | FK + `unique(company_id, phone)` + filtro no repositório | G-B2: número da casa de X não cala Y |
| `platform_sends` kind `grupo_*` | `company_id` da linha que originou | as contagens das 19h de X **não** somam as de Y |
| as 6 rotas do BLOCO G | `auth.ctx.companyId`, ⛔ nunca o corpo | teste de IDOR: trocar o `company_id` do body → 403 ou ignorado |
| resolvedor de destino | continua o único, e já recusa destino compartilhado (`_destino_e_compartilhado`) | 📊 P-PILOTO-10 é a prova histórica de que isso acontece de verdade |

⚠️ **As duas corretoras do teste são reais** (Resulta e AutoFleet existem no banco) e o teste é **read-only sobre elas**; a escrita vai para o tenant de teste. ⛔ Nunca copiar dado de uma corretora para outra "para montar teste".

---

## 17. Entrega, implantação e rollback

**Preflight e regressão** conforme CLAUDE.md §2 e AAA §10. ⛔ Nunca `git add -A`, force push, ou alterar guarda para obter verde.

🔴 **Entregar não é commitar. É empurrar:**

```bash
git rev-list --count origin/main..HEAD          # 0 = está no ar
git merge-base --is-ancestor origin/main HEAD && git push origin HEAD:main
```

A saída real do `push` e o SHA remoto vão **colados** no relatório (CLAUDE.md §2; §6.1 do protocolo: *a SPEC não está concluída enquanto a entrega não estiver escrita*).

**Serviços a implantar no EasyPanel** (o Founder clica; o executor entrega a lista e a ordem, medida — ⛔ não copiada de SPEC anterior):

```
smith-api   backend Python: guarda, números da casa, os quatro modelos,
            platform_sends, resumo das 19h, gate de ligar
web         painel Next: card Equipe, rotas de números internos, as 6 rotas do BLOCO G
```

**Variáveis de ambiente novas** — nome, sem valor:

| nome | o que faz | padrão |
|---|---|---|
| `RESUMO_DIARIO_HORA` | hora local do resumo | `19` |
| `RESUMO_DIARIO_ATIVO` | liga/desliga o resumo sem deploy | `true` |

⚠️ `JANELA_SILENCIO_HUMANO_DIAS` **já existe** e agora governa também o grupo — 🔴 **dizer isso ao Founder por escrito**, porque mudar esse número passa a ter dois efeitos.

**Rollback:** `RESUMO_DIARIO_ATIVO=false` desliga o resumo; `janela_silencio_humano_dias=0` na corretora devolve o comportamento de hoje **sem deploy**; a migration tem `drop table` seguro. 🔴 Os três caminhos de rollback existem porque esta SPEC **cala** coisas, e o modo de falha mais perigoso dela é calar demais.

**A tabela de marcos do relatório** (⛔ nenhum marco herda o anterior):

| marco | evidência exigida |
|---|---|
| Implementado e gateado | commit, 12 guardas verdes, 12 mutações vermelhas nomeadas, parecer independente |
| Entregue na main | SHA remoto + saída do `push` |
| Implantado | imagem/SHA por serviço + `/health` + uma requisição a `/api/…` |
| Validado no canário | os 8 casos de §14, por alias |
| Validado pelas pilotos | feedback real, registrado pelo Founder |
| Ativado nas linhas operacionais | **fora** desta autorização |

---

## 18. Documentação e acompanhamento obrigatórios

Um escritor por arquivo, **durante** a execução e a cada bloco fechado:

1. `docs/canon/specs/SPEC-EXTRA-001.3-….md` (a definitiva) e `docs/canon/reports/SPEC-EXTRA-001.3-EXECUTION-REPORT.md` pelo template, abrindo com o EXECUTION CARD e a telemetria de 5 linhas (AAA §11).
2. `docs/canon/ESTADO-DAS-SPECS.md` e `EXECUTION-MASTER-PLAN.md`, só nas seções afetadas.
3. `docs/canon/PENDENCIAS.md`: estado de P-PILOTO-02, 03, 04, 12 (`FECHADA`/`CONTINUA`/`MORREU`, com prova) e as novas — 💭 `weekly_report`/`proactive_suggestions` ignoram `human_support_destinations`; `whatsapp_channel.py:1124` apaga o `alert_target`; `handoff.realertado` com 0 linhas.
4. `docs/canon/FOUNDER-DECISIONS.md`: só se aparecer decisão nova. ⛔ Não reabrir D-PILOTO-09/13/14.
5. `docs/canon/CHANGE-ADDENDA.md`: tudo além do texto desta SPEC, classificado BLOCKER/ESSENCIAL/VALIOSA/FUTURA.
6. **O dossiê do Founder**, fonte versionada `docs/canon/reports/dossies/dossies-autobrokers.html`, publicado em
   https://claude.ai/code/artifact/afe1510d-f31c-4d13-9441-aa920ad2b868
   🔴 **Ler o HTML publicado inteiro antes de republicar com `url`**, preservar as páginas existentes, e conferir o link. Se não houver ferramenta/acesso, atualizar a fonte e registrar **"publicação do dossiê pendente"** com o arquivo e o passo exato. ⛔ Nunca alegar que atualizou. ⛔ Nunca publicar número de teste completo ou dado de cliente.

---

## 19. O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS

> AAA §7.3: 3 a 7 referências externas, cada uma com URL · o que faz · o que **modelamos** · o que **rejeitamos** · como o **juiz inspeciona**. 🔴 O pesquisador do Fable **reabre cada uma na conversão** e registra a data.

### E01 — Google SRE Book · cap. 6 "Monitoring Distributed Systems"

**URL:** https://sre.google/sre-book/monitoring-distributed-systems/ · reaberta em **13/09/2026** (canônica, sem redirecionamento).

**O que faz:** define o que um sistema de monitoração deve responder, separa **sintoma** de **causa**, e estabelece quando se tem o direito de interromper um ser humano.

**O que MODELAMOS:** a seção *"Tying These Principles Together"* traz, literalmente, a nossa guarda entre as perguntas de admissão de um alerta:

> *"Are other people getting paged for this issue, therefore rendering at least one of the pages unnecessary?"*
> *"Every page should be actionable."*

🔴 Modelamos isso como **pré-condição avaliada antes de compor a mensagem** — não como filtro de entrega — e na **mesma** função para os quatro emissores (re-alerta de 6 h, espera vencida, dossiê de reabertura, queda de canal). 📊 Pelo critério do próprio capítulo, **58 de 58** dos nossos re-alertas elegíveis são *unnecessary pages*: alguém já estava na conversa.

**O que REJEITAMOS:** os *four golden signals* (latency, traffic, errors, saturation) como régua. São métricas agregadas de serviço; o nosso sujeito é **uma** conversa de **um** segurado, não uma taxa. E rejeitamos "mande o subcrítico para o dashboard": a corretora não abre painel — o substituto é o resumo das 19h.

**Como o juiz inspeciona:** `grep -rn "o_grupo_pode_saber" backend/` tem de achar **uma** definição e os quatro emissores chamando-a; depois roda o teste que passa uma conversa com humano recente pelos quatro caminhos exigindo **0** mensagens, **com a linha de controle** (mesma conversa, sem humano) exigindo **1**. Se remover a guarda de um emissor não deixa o teste vermelho, o guarda é carimbo (CLAUDE.md §9.3).

### E02 — Google SRE Book · cap. 11 "Being On-Call"

**URL:** https://sre.google/sre-book/being-on-call/ · reaberta em **13/09/2026**.

**O que faz:** trata a carga de plantão como grandeza **medida e limitada**, com teto numérico auditável, e nomeia a sobrecarga operacional como falha do sistema, não da pessoa.

**O que MODELAMOS:** o capítulo fixa um teto e uma razão, com números publicados:

> *"the maximum number of incidents per day is 2 per 12-hour on-call shift"*
> *"Noisy alerts that systematically generate more than one alert per incident should be tweaked to approach a 1:1 alert/incident ratio."*

🔴 **A razão 1:1 é a régua desta SPEC inteira.** 📊 Em 10/09 saíram **7 mensagens sobre 1 incidente** — razão **7:1**, e concentradas em 75,7 minutos. "Espera vencida = 1 aviso" (§7.2), a chave de dedup por conversa (§7.5) e a morte do re-alerta em conversa com humano (§5) existem todos para trazer essa razão a 1:1. E o BLOCO E é o que torna a razão **mensurável**: um teto que ninguém conta é um teto que ninguém sabe que estourou.

**O que REJEITAMOS:** o aparato de plantão — escala rotativa, compensação, post-mortem obrigatório. A corretora não tem *on-call*, tem expediente. E rejeitamos o **número absoluto** (2 por 12 h) como constante nossa: é ponto de partida, calibrado sobre o acervo nos 3 dias da EXTRA-001.7. 💭 Importar o número de outra operação é o mesmo erro de medir com um motor e aplicar em outro.

**Como o juiz inspeciona:** roda a contagem de `platform_sends` `kind='grupo_%'` por conversa e por turno num dia do piloto e compara com **10/09 como linha de base (7 mensagens / 1 conversa / 75,7 min)**. Exige ≤ 1 aviso por conversa por evento.

### E03 — PagerDuty · Events API v2, "Send an Alert Event" (`dedup_key`)

**URL:** https://developer.pagerduty.com/docs/events-api-v2/trigger-events/ · reaberta em **13/09/2026**. ⚠️ A página é SPA e não responde a `fetch` simples; o texto foi lido em `…/trigger-events/index.html`, mesma URL canônica, mesmo conteúdo.

**O que faz:** define o endpoint `https://events.pagerduty.com/v2/enqueue` e a seção **Alert De-Duplication** — o contrato de como eventos repetidos viram **um** alerta em vez de N notificações.

**O que MODELAMOS:** a chave **e** a ação `acknowledge`, com a semântica escrita pela própria doc:

> *"Every alert event has a dedup_key: a string which identifies the alert triggered for the given event."*
> *"Submitting subsequent events with the same dedup_key will result in those events being applied to an open alert matching that dedup_key."*
> *"While an incident is acknowledged, it won't generate any additional notifications, even if it receives new trigger events. Use this event action to indicate that someone is presently working on the problem."*

🔴 **Duas coisas, e as duas são blocos desta SPEC.** A primeira é o conserto de §7.5: a chave é do **incidente** (`company_id, conversation_id, tipo`), não da execução que o detectou — três reaberturas de sessão são o **mesmo** problema, e foi assim que saíram 3 dossiês em 21 minutos. A segunda é o BLOCO A inteiro: **"humano respondeu" é o nosso `acknowledge`**, e a doc diz literalmente que, reconhecido, nenhum evento novo gera notificação.

**O que REJEITAMOS:** a regra de que um alerta resolvido **nunca** reabre — *"New trigger events with the same dedup_key as a resolved incident won't re-open the incident. Instead, a new incident will be created."* Numa corretora a **mesma** conversa volta dias depois e o corretor espera continuidade, não um caso novo: a nossa chave fecha por **janela** (a tabela de §7.5), não para sempre. E rejeitamos criar um estado de incidente paralelo: "alguém assumiu" já mora em `conversations.claimed_by` (CLAUDE.md §5).

**Como o juiz inspeciona:** abre a doc, confere o contrato da chave, e roda **G-C3** — replay das três reaberturas do 10/09 tem de dar **1**, e duas conversas diferentes no mesmo minuto têm de dar **2**. 🔴 E testa **reiniciar o processo no meio**: se a dedup morre com o worker, não é dedup — o marcador tem de ser o do Redis com TTL, não memória de processo.

### E04 — Prometheus Alertmanager · `inhibit_rules` e silences

**URL:** https://prometheus.io/docs/alerting/latest/configuration/ (seção `<inhibit_rule>`) e https://prometheus.io/docs/alerting/latest/alertmanager/ · reabertas em **13/09/2026**.

**O que faz:** dá o mecanismo formal de calar um alerta **porque outro fato já está valendo**:

> *"Inhibition is a concept of suppressing notifications for certain alerts if certain other alerts are already firing."*
> *"An inhibition rule mutes an alert (target) matching a set of matchers when an alert (source) exists that matches another set of matchers."*
> *"Both target and source alerts must have the same label values for the label names in the equal list."*

**O que MODELAMOS:** a inibição como relação **com chave de correlação declarada**, não como `if` espalhado. 🔴 **O nosso `equal` é a CONVERSA:** fonte = "humano da corretora ativo nesta conversa"; alvos = re-alerta, espera vencida e dossiê **daquela** conversa, e de nenhuma outra. É precisamente isso que impede o erro oposto — calar o grupo inteiro porque alguém respondeu em uma conversa.

**O que REJEITAMOS:** as **silences** como estão — *"Silences are configured in the web interface of the Alertmanager"*: silêncio manual, criado por quem está de plantão. A corretora não vai abrir tela para silenciar nada; o nosso silêncio é **inferido do fato observável** (o humano respondeu). E rejeitamos matchers por rótulo arbitrário: o nosso espaço é fechado (conversa · tipo · corretora), e generalizar seria construir um Alertmanager ao lado do que já temos (CLAUDE.md §5).

**Como o juiz inspeciona:** confere que a chave de igualdade é a **conversa**, e roda o teste de **duas conversas simultâneas do mesmo tenant**: humano responde só na A → **0** avisos da A e os avisos devidos da B. 🔴 É este teste que pega o defeito silencioso: um sistema que cala tudo passa em "parou de spammar" e reprova aqui. Depois repete com **dois tenants** (CLAUDE.md §7).

### E05 — Prometheus Alertmanager · `group_by` · `group_wait` · `group_interval` · `repeat_interval`

**URL:** https://prometheus.io/docs/alerting/latest/configuration/#route · reaberta em **13/09/2026**.

**O que faz:** define os quatro temporizadores que transformam N alertas em uma notificação — por que chave agrupar, quanto esperar antes da primeira, quando mandar as seguintes, e de quanto em quanto tempo **repetir** o que já foi dito.

> *"Grouping categorizes alerts of similar nature into a single notification."*
> *"How long to wait before repeating the last notification. Notifications are not repeated if any new alerts have fired or any firing alerts have resolved since the last group_interval."*

**O que MODELAMOS:** a separação entre **"tem novidade"** e **"estou repetindo"** — que é exatamente o que o re-alerta de 6 h não tem hoje. Os quatro papéis, mapeados:

```
group_by        → a conversa (a chave de dedup da E03)
group_wait      → a janela curta que junta a rajada inicial numa mensagem só
group_interval  → só há mensagem nova se houve FATO NOVO naquela conversa
repeat_interval → o resumo das 19h: a repetição do que continua parado, uma vez, num horário
```

📊 A régua contra o 10/09: **7 mensagens em 75,7 min sobre uma conversa sem nenhum fato novo** é repetição rodando como se fosse `group_interval`.

**O que REJEITAMOS:** os defaults publicados (30 s / 5 m / 4 h) como números nossos — são calibrados para *pager* de SRE, e o relógio da corretora é o expediente: o nosso "repeat" é um **horário fixo** (19h local), não um intervalo rolante. E rejeitamos o `group_wait` como atraso antes do **primeiro** aviso: 🔴 um pedido de ajuda do agente **não espera**, porque o segurado está do outro lado. O agrupamento age do **segundo** em diante.

**Como o juiz inspeciona:** replay do 10/09 sobre o novo agrupador — **1** mensagem onde saíram 7 — e confere que as outras 6 aparecem como **SUPRIMIDAS com motivo registrado** (`work_events` tipo `grupo.calado`), **não sumidas em silêncio**; e que o resumo das 19h **contém** as conversas suprimidas (CLAUDE.md §11.1: *pronto e desligado é aceitável; pronto e não anotado, não*). Roda por fim a **linha de controle**: uma conversa **com fato novo** dentro da janela tem de produzir mensagem nova — se não produzir, o agrupador virou mordaça.

---

## 20. O QUE SAIU E QUANDO VOLTA

| Frente | Motivo de não entrar | Gatilho de retorno |
|---|---|---|
| Régua de eficiência por dimensão publicada no dossiê | o número nasce aqui; a régua é produto da medição de 3 dias | EXTRA-001.7 |
| Uma conversa por contraparte (LID × telefone) + as 174 fantasmas | migration em `conversations` e CHECK de `resolucao_motivo`; é bloco da 001.2 | EXTRA-001.2 / P-PILOTO-13 |
| Conteúdo do checklist de sinistro por tipo | depende da base de produtos e assistências | EXTRA-001.5 — o **lugar** já está reservado em §8.2 |
| `weekly_report` e `proactive_suggestions` lendo `human_support_destinations` | outra superfície; risco de mexer em dois envios semanais sem gate próprio | pendência nova; SPEC de canais (099) ou a próxima que tocar esses arquivos |
| Aposentar `alert_target.internal_numbers` do JSONB | expand-first: o leitor velho continua | SPEC futura, com backfill e prova |
| Reconectar o canal automaticamente | esta SPEC só muda o **destinatário** do aviso | SPEC-099 |
| CHECK na coluna `platform_sends.kind` | congelaria a lista de tipos | quando a lista parar de crescer |

⛔ Nada do "Obrigatório" da §2 sai em silêncio. Recorte unilateral não é otimização AAA (CLAUDE.md §11).

---

## 21. Dependências, ordem e o que esta SPEC deixa para as seguintes

**Ordem canônica** (diagnóstico §12.1): 001.0 → 001.6-P0 → 001.1 → 001.2 → **001.3** ∥ 001.4 → 001.6 → 001.7 → 001.10 ∥ 001.5 → 001.8 → 001.9.

**Depende de:** **EXTRA-001.2** — *uma conversa por contraparte*.

🔴 **Por quê, e o que fazer se a 001.2 ainda não subiu:** a guarda do BLOCO A lê as mensagens **de uma conversa**. 📊 P-PILOTO-13: 174 conversas-fantasma nascidas de LID × telefone (106 AutoFleet, 68 Resulta) partem o histórico em duas linhas — e a janela leria a linha errada, concluindo "nenhum humano falou" sobre uma conversa que a Regina conduz na outra metade.

**Mitigação obrigatória se a 001.2 não estiver no ar quando esta executar:** a pergunta 4 da guarda passa a consultar **também** a conversa-irmã pela chave de contraparte normalizada (as variantes de `_variantes_do_telefone`), e o guarda G-A1 inclui **uma** das 174 fantasmas como caso. ⚠️ É mitigação, não conserto: o conserto é a 001.2, e a pendência continua com o número dela.

**Paralela a:** EXTRA-001.4 (corredor não trava). ⚠️ **Ponto de colisão declarado:** a 001.4 escreve a pausa de 60 s do humano na URA e diz *"enquanto o humano está lá, nenhum gatilho de grupo dispara"* — que é **a mesma guarda** desta SPEC, chamada de outro lugar. 🔴 Quem executar primeiro **cria** `o_grupo_pode_saber`; quem executar depois **chama**. ⛔ Duas implementações = motor paralelo, e as duas SPECs reprovam.

**Esta SPEC deixa prontos, para as seguintes:**

- para a **001.7** (piloto medido): os eventos contáveis e a fórmula — sem eles, as notas de §0 do diagnóstico continuam palpite;
- para a **001.4**: a guarda única, já com `company_id` e tipos;
- para a **001.5**: o campo "pontos de atenção" do modelo de sinistro, esperando o checklist;
- para a **001.6**: `billing_collection.avisar_suporte_humano` fundido no resolvedor único, com a recusa de destino compartilhado que hoje ele pula; **e a allowlist de `kind` que conta na cota do segurado** (§9.2), já contemplando `billing_nota` e `billing_doc`. ⚠️ **É arquivo-hub entre as duas SPECs:** quem executar primeiro cria a lista completa; quem executar depois acrescenta os seus. ⛔ Duas listas = a próxima regressão.

---

## 22. 📋 Caixa do Founder — o que só o Amandus faz

| # | o que é | o que destrava | bloqueia? |
|---|---|---|---|
| 1 | **Criar o grupo de canário** (só você dentro) e dizer qual é o tenant de teste | os 8 casos de §14 | não — o resto executa |
| 2 | **Decidir se `requireCompanyMember({write:true})` restringe quem você não quer restringir** (§11.2): se a Saionara ou a Regina forem `member`, elas param de poder mexer em destino de suporte e credencial de portal | o BLOCO G sem surpresa na segunda-feira | não — o executor mede quem é o quê e pergunta com o número na mão |
| 3 | **Reativar os destinos de suporte** da Resulta e da AutoFleet quando quiser voltar a ligar o agente (📊 os dois estão `is_active=false` hoje) | a EXTRA-001.7 | não bloqueia esta SPEC; bloqueia o piloto |
| 4 | **Dizer se 19h é a hora certa**, e se é a mesma para as duas corretoras | o BLOCO D.4 | não — 19h é o padrão e é env |
| 5 | **Ler os quatro modelos e dizer o que você cortaria** (§8) — 💭 a copy é ilustrativa de propósito | a validação com a Saionara e a Regina | não |
| 6 | **Confirmar que a janela de 7 dias passa a valer também para o grupo** — mudar esse número agora tem **dois** efeitos | nada; é aviso | não |

⛔ Nunca se para para entregar uma linha desta caixa (AAA §9 ③).

---

## 23. Definição final de conclusão — lista fechada e verificável

Esta SPEC está concluída quando **todas** as linhas abaixo tiverem evidência colada no relatório:

1. ☐ EXECUTION CARD no topo do relatório, dentro do limite do guarda, com RISCO e SUPERFÍCIE recalculados no BLOCO 0.
2. ☐ Os três números-âncora **remedidos** pelo executor (7 mensagens / 58 de 58 / 4 balões), e o de 58 remedido **pelo motor Python**, não por SQL — com o número que saiu, seja qual for.
3. ☐ **12 guardas** novos verdes, e **12 mutações** vermelhas, cada uma com a saída real da falha colada.
4. ☐ Os **11 pontos de envio** da §3.2 conferidos um a um, com o estado de cada um (passa pela guarda / isento com justificativa / fora de escopo com pendência).
5. ☐ A migration aplicada com **APPLY/VERIFY/ROLLBACK** e o VERIFY rodado **no banco**, com a saída.
6. ☐ Os quatro modelos renderizados e **colados no relatório** (com dados de teste), passando na régua de língua humana.
7. ☐ O resumo das 19h **reconciliável**: a soma das contagens bate com `work_events` do dia, e a eficiência recalculada à mão dá o mesmo.
8. ☐ Prova de isolamento com **duas corretoras**, para a guarda e para os números da casa.
9. ☐ As **três** leituras do governador ignoram o que não conta na cota — cota da hora, cota do dia, `dias_de_uso` e **`maturidade_do_canal`** inalterados após N linhas `grupo_*` **e** N `billing_nota` — com a linha de controle provando que N linhas `billing` **mexem** nas quatro.
9b. ☐ `motivo_classe` **tem escritor**, `desconhecido` fica fora dos dois lados da fórmula com linha própria, e acima do limite de fatia o resumo **não publica** o número de eficiência.
10. ☐ As 6 rotas com papel, origem e auditoria, e o teste de `member` → 403.
11. ☐ `git push origin HEAD:main` com a **saída real** colada e o SHA remoto conferido.
12. ☐ Canário: os 8 casos de §14, com aliases, **incluindo o par de controle** (caso 8).
13. ☐ Pendências P-PILOTO-02, 03, 04, 12 com estado e prova; pendências novas registradas.
14. ☐ Dossiê atualizado e publicado — **ou** "publicação pendente" com o arquivo e o passo exato.
15. ☐ O resumo ao Founder, em linguagem simples: *o que mudou no grupo · o que ele vai parar de receber · o que passou a receber · o que ainda não está medido · qual é a única próxima ação*.

⛔ "Pronto" não substitui evidência. Se um gate material faltar, o status é **PARCIAL** ou **BLOQUEADO**, nomeando qual.
