# 🏁 LAUDO DE CONFIRMAÇÃO (§6.1) — SPEC-EXTRA-001.10.1 · A continuação do portal de vidros

Juiz de confirmação (Fable 5.1, read-only), 24/09/2026. Diff julgado: `git diff c7a84da 3b43fc8 -- backend/` (10 arquivos, +1009/−63).
Dublês: banco em memória + armadilha em `supabase.create_client` (harness do red team) + replay dos HAR LATERAL/LATARIA2. 📊 `alcancou o banco real: []` nas 2 rodadas. Nenhum dado pessoal impresso.
Scripts: `scratchpad/confirmacao/c_ataques.py` (36 ok / 6 "falhas" — 5 são do MEU cenário/regex, ver §Evidência), `c2_ataques.py` (11 ok / 1 falha real), `saida-*.txt`, `rerun-redteam.txt`.

## VEREDITO
**O conserto NÃO criou defeito.** Os 6 ataques focados no diff (irmão · concluir-se-já-agendado · hora · chave com id do job · fail-closed · textos) não acharam regressão: o refino da peça não abre 2º `POST /atendimentos`; cancelado e "outro número" vencem o "Agendado para"; a mesma escolha com continuação em curso continua 1 job; a abertura de pedido novo não depende da leitura das continuações; duas corretoras isoladas; textos ao segurado sem `{ [ None` e sem domicílio.
**Mas dois blockers foram fechados só PARCIALMENTE, com o MESMO efeito de produto dos originais:**
- **RED B1 (hora explícita)** — fechado para dígitos; **hora por extenso e "e meia" ainda viram período** e o motor POSTa o 1º bloco do período. 📊 `"4 e meia da tarde"` → `POST /agendamentos Horario=13:00` (C3.fio). ⇒ **BLOCKER remanescente, conserto curto.**
- **RED B4 (peça reescrita)** — fechado para irmão em `responder:<slot>`; **o cenário que o red team MEDIU (1º pedido em `agendar`) continua abrindo o 2º atendimento**. 📊 A6.2 do red team rerodado no HEAD: `jobs abrir: 2 · POST /atendimentos na 2a: 1` — VERMELHO. ⇒ **decisão ESCRITA do gerente** (o red team já ofereceu "aqui ou pendência com número").

JUIZ B1, RED B2(a)(b)(c), RED B3, RED B5, P1–P4 do juiz e P1–P3 do red: **fechados e medidos** (§Evidência).

## BLOCKERS

### CB1 · Hora dita POR EXTENSO ou com "e meia" perde a hora → o motor agenda o 1º bloco do período (mesmo efeito do RED B1)
**Onde:** `backend/app/agents/tools/portal_params.py::_hora_dita` (só regex com dígitos; `_MANHA/_TARDE` ainda decidem o período quando a hora não casa) → `normalizar_preferencia_agenda` devolve `{periodo: "tarde"}` sem `horario` → `vidros_apifirst._agendar_pela_preferencia` casa `casam = [turno == periodo]` → `_agendar_no_portal` POSTa o 1º bloco.
**Medição (📊 `python - <<EOF` com `PP.normalizar_preferencia_agenda(f, hoje=21/09)`):**
```
'quatro da tarde'        -> {'periodo': 'tarde'}   HORA PERDIDA     'duas da tarde'   -> {'periodo': 'tarde'}  HORA PERDIDA
'às quatro da tarde'     -> {'periodo': 'tarde'}   HORA PERDIDA     'dez da manhã'    -> {'periodo': 'manha'}  HORA PERDIDA
'4 e meia da tarde'      -> {'periodo': 'tarde'}   HORA PERDIDA     'tres da tarde'   -> {'periodo': 'tarde'}  HORA PERDIDA
'quatro e meia da tarde' -> {'periodo': 'tarde'}   HORA PERDIDA     'duas horas da tarde' -> {'periodo':'tarde'} HORA PERDIDA
'de tarde, lá pelas quatro' -> {'periodo': 'tarde'} HORA PERDIDA    'cinco e quinze da tarde' -> HORA PERDIDA
CONTROLES: '3 da tarde' -> 15:00 · '2 horas da tarde' -> 14:00 · 'umas 4 da tarde' -> 16:00 · 'as quatro' -> {} (lista)
FIO (c_ataques.py C3.fio): '4 e meia da tarde' -> preferencia gravada {periodo: tarde} · POST /agendamentos = 1 · Horario = 13:00
```
**Teste do produto (§2):** muda o que sai no portal — agendamento às 13:00 para quem disse "quatro e meia da tarde". É exatamente o efeito que fez o RED B1 ser blocker; "quatro da tarde" é a forma mais comum de dizer a hora no WhatsApp.
**Conserto (o executor reproduz antes):** em `_hora_dita`, (a) traduzir número por extenso (`uma..doze`, `meia`=30 depois de "e") antes das regex, e (b) **fail-closed**: se sobrar uma palavra-número ou "e meia/e quinze/e quarenta" ao lado de uma palavra de período sem hora casada → devolver `("", False, True)` (ilegível ⇒ `{}` ⇒ lista). Guarda: as 10 frases acima ⇒ `horario` certo ou `{}` — **nunca só período**; mutação: remover (b) ⇒ VERMELHO em `"quatro da tarde"`.

### CB2 · RED B4 fechado só para `responder:<slot>`: o cenário MEDIDO pelo red team (1º pedido em `agendar`) continua abrindo o 2º atendimento
**Onde:** `backend/app/agents/tools/portal_tool.py::_pedido_irmao_esperando_resposta` — `if not (continuacao_possivel(ev) and operacao == "responder"): continue`.
**Medição:** 📊 `a6_dom_peca_encaixe.py` (red team) no HEAD: `[A6.2] jobs abrir: 2 · POST /atendimentos na 2a: 1 · [FALHOU]`. 📊 `c2_ataques.py` D1: 1º pedido `done/agenda` + peça "vidro da porta traseira esquerda" **sem** `escolha_agenda` ⇒ `aberturas=2 POST /atendimentos=1`; **com** `escolha_agenda` (a chamada é inequivocamente a RESPOSTA do 1º) ⇒ idem `aberturas=2 POST=1`.
**Teste do produto:** 2º atendimento real no nome do segurado (o mesmo do laudo do red). Não é defeito NOVO (desenho da 001.10); mas o relatório não pode dizer "B4 fechado".
**Classificação e decisão que o gerente escreve (⚖️ classifico, 🔧 ele decide):**
- (a) **85/100** — estender o guarda ao irmão em `agendar` **quando a chamada traz `escolha_agenda`** (é resposta, nunca peça nova: ~10 linhas em `_pedido_irmao_esperando_resposta`, `operacao in ("responder","agendar") and (operacao=="responder" or esp.get("escolha_agenda"))`) e registrar a peça reescrita SEM escolha em `agendar` como pendência numerada (o caso legítimo "outra peça = outro pedido" existe e o guarda não sabe distinguir).
- (b) **60/100** — pendência com número, sem mudar byte (como o red ofereceu).
Em qualquer caso: o guarda A6.2 do red team fica vermelho ou é reescrito com a verdade nova — não se apaga.

## PENDÊNCIAS (registram-se; não travam)
- **CP1 · A peça LEGÍTIMA vira resposta do 1º pedido** (c2 D2/D3): com o 1º pedido em `responder:peca`, "parabrisa" (payload válido, D0) é dobrado como `respostas={"peca":"parabrisa"}` — o atendimento do vidro de porta seguiria com a peça trocada; em `responder:pelicula` o parabrisa fica PRESO (0 escritas, agente ouve "PARADO esperando"). É a troca que o red team propôs (2º POST era pior) e o agente é avisado ("Se for OUTRA peca de verdade, conclua este pedido primeiro"). Registrar em PENDENCIAS.md; instrução de prompt do agente: nunca chamar a tool com peça nova enquanto há pergunta pendente.
- **CP2 · Guarda do irmão é fail-open sem 2ª rede** (c C1.5): busca cai ⇒ `None` ⇒ 2º `POST /atendimentos` sai (📊 `aberturas: 2 POST: 1`). Documentado no docstring; diferente do `_buscar_pedido_vivo`, aqui o índice único NÃO protege (chave diferente). Aceitável hoje; anotar.
- **CP3 · Mesma escolha pela TOOL depois de `leitura_falhou` ⇒ "Ja existe um atendimento"** (📊 red A3.4 no HEAD, FALHOU): `acao_esperada=reler` cai no `else` de `_continuar_ou_explicar`. O VIGIA resolve (relê e, pelo B2(b), herda a escolha) — mas só na janela de 30 min da sessão e uma vez por job. A frase ao agente é enganosa ("NAO abri outro") — trocar por "já estou relendo". Não é novo.
- **CP4 · "Agendei o serviço ✅" sem POST nosso** (c2 D6): agregado que vira "Agendado para" ENTRE a leitura do passo 3 e o desfecho de um `responder` ⇒ `_ramos_do_roteador → conclusao` sem `ja_estava_agendado` ⇒ título "Agendei" com `agendamento_enviado` ausente. Janela de segundos (ou humano agendando no portal ao mesmo tempo); efeito só no texto. Conserto trivial: `mensagem_do_desfecho` usa "já está agendado" quando `evidence.agendamento_enviado` não existe.
- **CP5 · Regressões pequenas e inofensivas de `normalizar_preferencia_agenda`:** `"a partir de 23"` → `{}` (antes provavelmente 23/09; agora vira "relativa"); `"às 4"`/`"quinta às 3"` → 04:00/03:00 (nenhuma loja publica ⇒ lista, 📊 C3.fio `POST=0 desfecho=agenda`); `"entre 14h e 16h"` → 14:00 (dentro do intervalo dito); `"16h30 ou 17h"` → 16:30 (uma das duas). Nenhuma marca hora que ele não disse.
- **CP6 · Controle A4.4 do red team ficou VERMELHO por verdade vencida** (o reler agora HERDA a escolha e POSTa 22/09 16:00 — a escolha dele, 📊 A4.3 ok). O guarda deve migrar (CLAUDE.md §9.3), não morrer.
- **CP7 · `_limpo` do harness não mascara nome/endereço da LOJA** (saiu em D6/A4.3). É dado público do portal, não do segurado — mas os laudos não devem reimprimir.

## EVIDÊNCIA (comandos e saídas)
```
cd backend && PYTHONIOENCODING=utf-8 python tests/test_e001101_o_conserto_nao_repete_nem_adivinha.py  -> 48 verdes · 0 vermelhas
  test_e001101_c_a_tool_continua_o_pedido -> 50/0 · test_e001101_o_fio_da_continuacao -> 78/0 · test_e001101_a_costura_da_continuacao -> 60/0
red team rerodado no HEAD (cwd backend): A1 11/0 · A2(novo) 12/0 · A3 8/1 (A3.4=CP3) · A4 11/1 (A4.4=CP6) · A5 15/0 · A6 9/1 (A6.2=CB2)
c_ataques.py  -> PASS=36 FAIL=6 · alcancou o banco real: []
   C1.1 refino da peca: aberturas 1 · continuacoes 1 · POST /atendimentos 0 · respostas {'peca': 'vidro da porta traseira esquerda'}   (RED B4 responder: FECHADO)
   C1.4 duas corretoras: A abre o seu (POST 1), B sem continuacao; _pedido_irmao(...)=None                                            (isolamento OK)
   C1.5 busca do irmao cai: pedido novo abre (POST 1); com irmao parado + busca caindo: aberturas 2 POST 1                              (CP2)
   C2.1 escolha 08:00 sobre 'Agendado para 16:00': POST /agendamentos 0 · "Seu serviço já está agendado ✅" 16:00, sem 'Agendei'        (JUIZ B1: FECHADO)
   C2.2 Cancelado=true + 'Agendado para': stage atendimento_cancelado · POST 0 · segurado nao le 'agendado'                            (OK)
   C2.3 CodigoAtendimento de outro numero: sessao_de_outro_atendimento · POST 0                                                        (OK)
   C2.4 'Agendado para' sem loja no script: tipo agendado, mensagem sem { [ None, sem 'Loja:' vazia                                    (OK)
   C3   50 frases (tabela em saida-c_ataques.txt): digitos OK; relativas {} ; 24h/às 25 {} ; 'dia 4' = data, nao hora; 'as 10 lojas' {}
   C3.fio 'às 4' -> POST 0 desfecho agenda · 'meio-dia' -> POST 1 Horario 12:00 · '4 e meia da tarde' -> POST 1 Horario 13:00           (CB1)
   C4.1 mesma escolha com continuacao queued: 1 job · C4.2 depois de agenda_nao_respondeu: 2 jobs, 1 POST, agendado · C4.3 depois de agendado: 0 job 0 POST  (RED B3: FECHADO)
   C5.1 pedido novo com SELECT das continuacoes caindo: abre (POST 1) · C5.2 existente + SELECT caindo: 0 job, 0 notificacao, 'Nao consegui conferir'  (fail-closed OK)
   C6   vigia: "...em qual loja credenciada prefere..." · format_result DOM sem domicilio · notificacoes limpas                          (RED B5: FECHADO)
   As 6 "falhas": C1.2/C1.3/C1.6 = meu payload 'parabrisa' sem os 7 slots (tool recusou ANTES do guarda; refeito em c2 D2–D4, ok);
                  C4.2/C6×2 = meu regex pegou "[para a equipe, nao mande ao segurado]" (bloco do AGENTE; o texto ao segurado esta limpo).
c2_ataques.py -> PASS=11 FAIL=1 · D1 (CB2) · D2/D3 (CP1) · D4/D5 controles: parabrisa abre o seu com o 1o em agendar/reler · D6 (CP4, a unica falha)
```
Reproduzidos 3 números por amostra (§0.4): C2.1 `0 POST / 16:00 / sem Agendei`; C3.fio `1 POST / 13:00 / periodo tarde`; A6.2 `2 abrir / 1 POST / chave v2:…`.

## MAIOR LACUNA
O comportamento REAL do portal depois de `POST /agendamentos` (o que `opcoes-disponiveis` publica) segue sem captura — a defesa é a leitura do "Agendado para" ([049]), agora em 3 portas (passo 4 da continuação, `_agendar_no_portal`, `_ramos_do_roteador`). E o replay REUTILIZA o último `GET /atendimentos` do HAR ([049]) quando a leitura bate na barreira: nos meus C1.1/D2 a continuação terminou "agendado" sem POST — artefato do replay, não do motor (0 escritas medidas).

## PRÓXIMA AÇÃO
1. CB1: conserto em `_hora_dita` (extenso + "e meia", fail-closed) + guarda com mutação; rerodar `test_e001101_o_conserto_nao_repete_nem_adivinha` e o A2 novo. ≤ 30 min, 1 arquivo + 1 teste.
2. CB2: decisão escrita do gerente ((a) 85 · (b) 60); se (a), ~10 linhas em `_pedido_irmao_esperando_resposta` + guarda A6.2 migrado.
3. CP1–CP7 → PENDENCIAS.md / CHANGE-ADDENDA; A4.4 migra (§9.3).
4. 🔴 §6.1: esta foi a rodada 1 de confirmação; `backend/scripts/rodada_do_juiz.py` conta. A 3ª é escalação.

## CONFIANÇA e o que ficou por medir
Alta nos 6 ataques do diff (tudo por comando, dublê provado: `alcancou o banco real: []`). Não medi: o vigia REAL enfileirando o `reler` herdado (só `pedir_releitura=True` e `montar_job_de_continuacao` — o red A4.3 cobre o fio); o caminho DOM (`PORTAL_VIDROS_API_FIRST` desligada) além dos dois textos; `rodada_do_juiz.py`.

## NOTA: 78/100
O conserto é limpo e não regrediu nada; JUIZ B1, RED B2, B3, B5 fechados com medição. Desconto: B1 do red fechado só para dígitos (o efeito no portal continua para "quatro da tarde") e B4 fechado só para `responder` (o cenário medido pelo red segue vermelho).
