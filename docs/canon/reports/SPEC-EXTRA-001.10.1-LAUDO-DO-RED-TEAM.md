# 🗡️ LAUDO DO RED TEAM — SPEC-EXTRA-001.10.1 · A continuação do portal de vidros

Branch `feat/extra-001-10-1-a-continuacao-do-portal` · HEAD `c388872` · alvo `git diff 4573a46 HEAD -- backend/` · 23/09/2026.
Read-only no repo. Tudo com o MOTOR real (tool `_arun` → `build_portal_params` → `portal_jobs` → worker de costura → journey → `format_result`/`mensagem_do_desfecho`/vigia), dublê só na borda: página = `PaginaDeReplay` sobre os HAR reais LATERAL/LATARIA2 (subclasse `PaginaHostil` injeta 401/500/corpo/alias de query), banco = `BancoDeMentira` do teste de costura com armadilha em `supabase.create_client` (📊 "alcancou o banco real: []" em todos os 6 scripts). Relógios da tool e do motor fixados no dia da captura (21/09/2026). Nenhum CPF/placa/token impresso (`_limpo`).

Scripts (em `scratchpad\redteam\`): `red_common.py` (harness), `a1_repost_e_dupla_escrita.py`, `a2_preferencia_hora.py`, `a3_indisponivel_transitorio.py`, `a4_reler_vs_escolha.py`, `a5_token_tenant_401.py`, `a6_dom_peca_encaixe.py`.
Comando: `cd backend && PYTHONIOENCODING=utf-8 python "<scratchpad>\redteam\aN_*.py"`.

⚠️ Defeito do meu harness corrigido no meio (registrado por honestidade): uma chamada que a tool RECUSA deixava a página hostil na fila e o job seguinte rodava com a página errada — A1.4/A1.7/A1.8 foram remedidos depois do conserto (`rodar_job` limpa a fila).

---

## BLOCKERS (o teste do produto §2 deu SIM)

### B1 · Preferência de agenda com HORA explícita vira "período" — o motor AGENDA o 1º bloco do período (efeito errado no portal)
**ATAQUE** `a2_preferencia_hora.py` [A2.1]/[A2.2]. Frases reais em `PP.normalizar_preferencia_agenda(frase, hoje=21/09)` e depois o fio inteiro (abertura LATERAL com `especificos.preferencia_agenda = "4 da tarde"`).
**SAÍDA medida (📊)**
```
'4 da tarde'             -> {'a_partir_de': '21/09/2026', 'periodo': 'tarde'}     (hora perdida)
'de tarde, umas 4 horas' -> {'a_partir_de': '21/09/2026', 'periodo': 'tarde'}
'hoje 15:30'             -> {'a_partir_de': '21/09/2026', 'periodo': 'qualquer'}  (hora perdida; 1º bloco do DIA)
'amanhã às 9'            -> {'a_partir_de': '22/09/2026', 'periodo': 'qualquer'}
'quarta 14h'             -> {'a_partir_de': '23/09/2026', 'periodo': 'qualquer'}
'quero a segunda loja'   -> {'a_partir_de': '28/09/2026', 'periodo': 'qualquer'}  ("segunda" = segunda-feira)
'16h' / 'às 16h' / 'só depois das 15h' -> {}   (por acaso: nenhuma palavra de período)
FIO [A2.2]: POST /agendamentos saiu: 1 · Horario: 13:00 · Encaixe: True   ← para quem disse "4 da tarde"
CONTROLE [A2.3]: 'pode ser de tarde' -> POST 13:00 (o desenho D-E001101-02: 1º bloco do período — certo SEM hora)
```
No replay o job termina `agendamento_nao_confirmado` porque o HAR real confirmou 16:00; no portal real o POST de 13:00 seria confirmado e o segurado leria "Agendei … 13:00".
**TESTE DO PRODUTO**: muda o que sai no portal (agendamento em hora que o segurado não pediu) ⇒ **BLOCKER**.
**Correção sugerida** (`portal_params.normalizar_preferencia_agenda`): se o texto contém hora explícita (`\b\d{1,2}\s*(h|hs|horas|:\d{2})\b`, `\b\d{1,2}\s+da\s+(manha|tarde|noite)\b`) ou a palavra "loja"/"lojas", devolver `{}` (cai em `agenda`, o segurado escolhe na lista). Guarda: as 7 frases acima ⇒ `{}`; os controles ('quarta de manhã', 'semana que vem', 'tanto faz', 'dia 30') seguem atravessando.

### B2 · A releitura do vigia (C4) AGENDA sozinha pela preferência antiga e IGNORA a escolha explícita que acabou de falhar por parada técnica
**ATAQUE** `a4_reler_vs_escolha.py`. (1) abertura com `preferencia_agenda="a partir de 23/09 de manhã"` (dia 23 sem agenda → `agenda`, lista mostrada, "Me diga o número da loja…"); (2) escolha explícita `{"loja":"1","dia":"22/09","horario":"16:00"}` → job `agendar`; página hostil: `opcoes-disponiveis` → 500 ⇒ `roteador_ilegivel`; a tool diz ao segurado "Já estou tentando de novo por aqui, pelo mesmo pedido"; (3) `VG.pedir_releitura(job)==True` → `VG.pedir_a_releitura` (real) enfileira o `reler`; a agenda do dia 23 "abriu" (alias 23→22 na query).
**SAÍDA medida (📊)**
```
params._continuacao do reler: {'operacao': 'reler', 'escolha': {}, 'respostas': {}}   ← a escolha 22/09 16:00 NÃO viaja
especificos herdados no reler: {'preferencia_agenda': {'a_partir_de': '23/09/2026', 'periodo': 'manha'}}
escritas do reler: [('POST','/lojas/consultar-distancias'), ('POST','/agendamentos')]
corpo do POST: {'DataDeAgendamento': '2026-09-23', 'Horario': '08:00', 'Encaixe': True}   ← ele escolheu 22/09 16:00
CONTROLE [A4.4]: o MESMO reler sem `preferencia_agenda` herdada -> nenhuma escrita material, desfecho `agenda`
```
Mesmo raiz em `a1_repost_e_dupla_escrita.py` [A1.5]: abertura agendou por preferência (13:00) e um `reler` sobre o pedido cujo agregado JÁ diz "Agendado para" volta a `POST /agendamentos` (13:00) — o motor decide escrever só por `DisponibilizarAgendamento` de `opcoes-disponiveis` (❓ nunca medido depois de um agendamento: o SPA não relê) e ignora o `ScriptFinalizacao` que acabou de ler no passo 3. [A1.4] idem com job `agendar` direto (15:00) sobre pedido "Agendado para 16:00": POST saiu. [A1.7] CONTROLE: com `ExisteAgendamento:true` o motor lê e não escreve — a flag do portal é hoje a ÚNICA defesa. (Pela TOOL esses dois caminhos são barrados: [A1.2]/[A1.3] a mesma ou outra escolha depois de `agendado` não gera job — a brecha é o vigia e qualquer job que chegue ao worker.)
**TESTE DO PRODUTO**: agendamento errado / duplicado no portal e "Agendei" com dia e hora que ele não escolheu ⇒ **BLOCKER**.
**Correção sugerida**: (a) `vidros_continuacao.continuar_atendimento`: operação `reler` NUNCA agenda por preferência (`fase_desfecho(ex, agendar_por_preferencia=False)` ou remover `preferencia_agenda` de `ex.especificos` no reler); (b) o reler de um job cuja `_continuacao.operacao=="agendar"` deve HERDAR a `escolha` (em `montar_job_de_continuacao`, `escolha = origem._continuacao.escolha` quando `operacao=="reler"`) e a journey trata `reler`+`escolha` como `agendar_escolha` — é isso que cumpre a promessa "já estou tentando de novo"; (c) defesa em profundidade em `vidros_estado._ramos_do_roteador`/`fase_desfecho`: `script["agendamento"]` presente no agregado ⇒ `conclusao` (agendado), antes de olhar `DisponibilizarAgendamento`. Guardas: A4.3 ⇒ zero POST ou POST 22/09 16:00; A1.4/A1.5 ⇒ zero POST.

### B3 · Um 500 transitório em `datas-disponiveis` vira "Esse horário acabou de ser ocupado" (falso) e a MESMA escolha fica presa para sempre
**ATAQUE** `a3_indisponivel_transitorio.py` [A3.2]/[A3.3]. Escolha 22/09 16:00 (está publicada); página hostil: `GET /agendamentos/datas-disponiveis` → 500. Depois, o portal volta ao normal e o segurado repete a mesma escolha.
**SAÍDA medida (📊)**
```
continuacao: needs_human horario_indisponivel · injetadas: [datas-disponiveis 500 ×2] · escritas materiais: []
agente recebeu: "...Esse horário acabou de ser ocupado na loja, então eu NÃO agendei nada. Me diz qual das opções de agora..."
2ª chamada (mesma escolha, portal OK): jobs de continuacao = 1 (nenhum novo) · POST /agendamentos = 0
agente recebeu: "Ja existe um atendimento aberto para este mesmo veiculo, peca e data do dano. NAO abri outro..." + o texto de horario_indisponivel
vigia pedir_releitura(job) = False (horario_indisponivel não é técnico) · diagnosticar(entregue) = None
```
Causa: `agendar_escolha` não distingue `rdias.ok==False` de "dia não listado" (`meses=[]` ⇒ `iso=""` ⇒ `indisponivel(...)`), e `enfileirar_continuacao._viva()` trata a continuação terminal `needs_human` (sem efeito) como "viva" pela mesma chave (`protocolo+op+escolha`) — G7 aplicado a uma tentativa que nunca chegou ao portal.
**TESTE DO PRODUTO**: mensagem falsa ao segurado + o horário que ele quer nunca mais pode ser pedido (só a equipe) ⇒ **BLOCKER**.
**Correção sugerida**: (a) em `agendar_escolha`, `not rdias.get("ok")` ou `_ler_blocos` com resposta `!ok` ⇒ parada TÉCNICA (`leitura_falhou`/`agenda_ilegivel` com motivo "o portal não respondeu a agenda"), nunca `horario_indisponivel`; (b) em `_continuar_ou_explicar`, montar a chave com `extra=str(atual["id"])` (a tentativa é sobre o ESTADO atual do pedido: G7 continua valendo porque a mesma resposta com a continuação em curso é pega ANTES, por `STATUS_EM_CURSO` em `buscar_ultimo_estado_do_pedido`) — ou `_viva()` ignorar terminais sem `critical_effect` submetido. Guarda: A3.3 ⇒ 2 jobs, 1 POST, sem "Ja existe".

### B4 · A peça "refinada" no campo de cima abre um SEGUNDO `POST /atendimentos` (pré-existente da 001.10; a continuação torna provável)
**ATAQUE** `a6_dom_peca_encaixe.py` [A6.2]: abertura com `peca="vidro de porta"`; segunda chamada, mesma placa/data, `peca="vidro da porta traseira esquerda"` (o que um LLM faz depois de "qual peça exatamente?"/`peca_ambigua`, apesar da instrução "o campo `peca` de cima fica IGUAL").
**SAÍDA medida (📊)** `jobs abrir: 2 · POST /atendimentos na 2a: 1` (a chave `v2:…` embute a peça normalizada; a proteção é só o texto do prompt).
**TESTE DO PRODUTO**: 2º atendimento real no nome do segurado ⇒ **BLOCKER por efeito** — mas o desenho (chave = corretora+placa+peça+data) é da 001.10 e o caso legítimo "outra peça = outro pedido" existe (`frase_de_pedido_ja_existente`). Decisão do gerente: aqui ou pendência com número.
**Correção sugerida** (barata, sem mudar a chave): em `_arun`, antes do insert de `abrir_atendimento`, buscar na MESMA `company_id` um job vivo com o mesmo `cpf_cnpj`+`placa`+`data_dano` (qualquer peça) cujo `evidence.continuacao.possivel is True` e `acao_esperada` começa com `responder:` — se existir, tratar a chamada como CONTINUAÇÃO desse pedido (a peça nova vai em `respostas.peca`) em vez de abrir outro. Guarda: A6.2 ⇒ 1 job abrir, 0 POST /atendimentos na 2ª.

### B5 · Caminho DOM (flag `PORTAL_VIDROS_API_FIRST` desligada = PRODUÇÃO hoje) ainda oferece DOMICÍLIO ao segurado — contra D-E001101-05
**ATAQUE** `a6_dom_peca_encaixe.py` [A6.1]: `VG.diagnosticar` de um job DOM em `aguardando_escolha_do_segurado` e `PP.format_result` de um job com só `protocolo`.
**SAÍDA medida (📊)**
```
vigia: "...Falta só você escolher onde prefere fazer o serviço: um técnico vai até você, ou você leva numa loja credenciada. Qual fica melhor?"
format_result: "...Confirme com o segurado onde o servico sera feito (tecnico a domicilio ou uma das lojas) — essa escolha e dele..."
```
(`app/tasks/vigia_do_portal.py` ramo `aguardando_escolha_do_segurado`; `portal_params.format_result` linha ~1959, `recomendacao` padrão.)
**TESTE DO PRODUTO**: o segurado lê uma oferta que o produto decidiu não fazer (domicílio) ⇒ **BLOCKER** (texto; 2 strings).
**Correção**: os dois textos passam a "escolher a loja credenciada" (sem domicílio).

---

## PENDÊNCIAS (não mudam byte hoje, ou dependem de decisão)

- **P1** `leitura_falhou` (GET /atendimentos 500/timeout na continuação) NÃO está em `ESTAGIOS_TECNICOS` ⇒ o vigia não relê (📊 [A3.4] `pedir_releitura=False`; a mesma escolha depois disso também fica presa pela chave — B3b resolve). C4 promete "parada técnica ⇒ continuação automática". Texto ao segurado é honesto ("a equipe assume") — por isso pendência. Correção: incluir `leitura_falhou` em `ESTAGIOS_TECNICOS`.
- **P2** `mapear_escolha_de_agenda` aceita `dia="31/02"` (📊 [A6.5] devolve escolha válida) → vai ao portal → `horario_indisponivel` com o texto "acabou de ser ocupado". Validar a data com `datetime` na tool.
- **P3** `normalizar_preferencia_agenda` pelo caminho DICT aceita data PASSADA (`01/01/2020` atravessa; o caminho texto recusa). Inofensivo (o motor começa em `hoje`), mas é regra em dois lugares.
- **P4** O motor confia SÓ em `opcoes-disponiveis` para decidir escrever depois de uma escrita (A1.4/A1.5/A1.6): para `agendar` o agregado prova ("Agendado para") e B2(c) fecha; para prioridade/ocorrência (ramo 7) o agregado não prova nada e a sessão é descartada na conclusão (📊 [A1.6] `reler` ⇒ `sessao_indisponivel`, 0 escritas) — fica com gatilho: captura de um reload do SPA depois da ocorrência.
- **P5** `test_e001101_a_costura_da_continuacao.py` estoura em Windows cp1252 no check `f` (emoji no `print`) — o teste não chega ao fim aqui (📊 `UnicodeEncodeError` na linha 668). `PYTHONIOENCODING=utf-8` ou `sys.stdout.reconfigure`.
- **P6** Chave do cofre: `PORTAL_VAULT_KEY` presente também no processo da tool (o mesmo módulo `portal_worker.vault` é importável do smith-api). Quem tem o banco + a env do smith-api decifra a sessão. Decisão de deploy, não defeito de código — registrar.

## O QUE ATACOU E NÃO QUEBROU (está bom)
- Token: nunca em claro em `portal_jobs`(params/evidence), `work_runs`, notificações, log de DEBUG, resposta ao agente — inclusive com o portal ECOANDO o token num 500 (📊 [A5.4] `tela_desconhecida.resumo=['Message','Token']`, só chaves). `sessao_cifrada` decifra pelo cofre; após 401 ou conclusão a cifra é apagada e `possivel=False` ([A5.2], [A1.6]).
- 401 na continuação: zero escritas, `sessao_expirada`, número de 8 dígitos na mensagem, "não promete eu continuo", vigia alerta só a equipe com o número, sem 2ª mensagem ao segurado, sem releitura; a chamada seguinte do segurado recebe a frase honesta com o número ([A5.2]/[A5.3]).
- G3: nenhum `POST /atendimentos` saiu de nenhuma continuação (todos os scripts).
- G7 pela tool: mesma escolha depois de `agendado` ⇒ 0 jobs, 0 POST; outra escolha depois de `agendado` ⇒ recusada ([A1.2]/[A1.3]).
- Dois tenants: linha-isca de B com o MESMO `_pedido_key` e a MESMA chave de continuação de A nunca é lida por A; chave embute a corretora ([A5.5]).
- Lista de lojas reordenada no portal entre a leitura e a escolha: o POST vai pelo `CodigoCliente` que ele viu, não pela posição ([A6.4]); "2" com uma loja só ⇒ `loja_fora_da_lista`; "4 da tarde" como horário ⇒ `horario_ilegivel` ([A6.5]).
- Encaixe: bloco livre nos dois modos ⇒ `Encaixe:false` (regra do bundle); `8:30` sem zero é descartado (conservador); virada de ano ⇒ janeiro em 2027; `31/02` em dict não atravessa a journey ([A6.3]).
- `ServicoAgendado:false` com "Agendado para" lido ⇒ parada conservadora `agendamento_nao_confirmado` ([A1.8]).

## MAIOR LACUNA (o que ficou por medir)
Comportamento REAL de `opcoes-disponiveis` depois de `POST /agendamentos` / `POST /ocorrencias` (❓): se o portal seguir publicando `DisponibilizarAgendamento`, B2(c) é a única defesa. Precisa de UMA captura: recarregar o SPA com o token depois de agendar.

## NOTA: 64/100
O fio feliz, a segurança do token, o 401, o isolamento por corretora e o G3 estão sólidos. Mas há três caminhos medidos em que o robô marca dia/hora que o segurado não pediu (B1, B2) ou lhe diz algo falso e trava a escolha dele (B3), mais um texto de produção que oferece o domicílio retirado (B5). Todos com correção pequena e guarda enunciada.
