# LAUDO DO JUIZ FRESCO — SPEC-EXTRA-001.10.1 · A continuação do portal de vidros

Branch `feat/extra-001-10-1-a-continuacao-do-portal` · HEAD `c388872` · diff julgado: `git diff 4573a46 HEAD -- backend/` (28 arquivos, +6055/−644).
Read-only no repo. Tudo medido com o replay de HAR (`tests/_replay_vidros`), cofre Fernet gerado em memória, ZERO rede, ZERO banco (os testes da tool/vigia usam dublê e afirmam "zero chamadas ao cliente real" — A17). Scripts do juiz: `scratchpad/juiz/m1_har.py`, `m2_script.py`, `m3_ataques.py`. Nenhum dado pessoal ou token impresso.

## VEREDITO
**APROVADO COM 1 BLOCKER de conserto curto.** O fio existe e funciona: abertura → sessão cifrada → `continuar_atendimento` (mesmas fases, sem segundo motor) → `POST /agendamentos` / prioridade+ocorrência → confirmação LIDA do portal → mensagem honesta. G1–G11 verdes por comando. O blocker é uma porta de defesa em profundidade sobre efeito material irreversível: a continuação `agendar` já LÊ o agregado com "Agendado para" e mesmo assim emite um segundo `POST /agendamentos`.

## BLOCKERS

### B1 — A continuação `agendar` reenvia `POST /agendamentos` sobre um atendimento que o próprio agregado lido já diz "Agendado para"
**Onde:** `backend/portal_worker/journeys/vidros_continuacao.py:175-218` (lê `rg = ler_atendimento()` no passo 3 e, para `operacao == "agendar"`, chama `AF.agendar_escolha` sem olhar o `ScriptFinalizacao` que acabou de ler) e `backend/portal_worker/journeys/vidros_apifirst.py:1612-1623` (`agendar_escolha` só recusa pelas chaves de `opcoes-disponiveis` — `DisponibilizarAgendamento`/`_CONCLUSAO` — cujo valor DEPOIS de um agendamento tem **0 exercícios** no acervo: o HAR LATERAL não tem `GET opcoes-disponiveis` depois de [048]).
**Medição (m3_ataques.py, "cursor apos [049]"):** página de replay já vivida até o `GET /atendimentos` [049] ("Agendado para 22/09/2026 às 16:00"); continuação `agendar` com escolha 08:00 →
```
POST /agendamentos = 1   status=needs_human   stage=agendamento_nao_confirmado   escritas=[('POST','/agendamentos')]
```
e com o dublê que ecoa o POST no script (`Eco`), a 3ª chamada com a evidence VELHA da abertura e outra hora → `POSTs total=2 status=done tipo=agendado` — **dois agendamentos "confirmados"** no mesmo atendimento.
**Teste do produto (§2):** muda bytes na SEGURADORA (2º agendamento) e no SEGURADO (mensagem "Agendei" duas vezes) — mas só por um caminho de falha: a tool cai para a evidence da ABERTURA quando o SELECT da última continuação falha (`portal_tool.py:buscar_ultimo_estado_do_pedido`, `except Exception → return abertura`, **fail-open**), a abertura ainda diz `possivel=True/etapa=agendar`, o segurado pede "mudar o horário" (a própria mensagem de `agendado` convida: "Se precisar mudar o dia ou o horário, me avise por aqui", `portal_params.py`), o job `agendar` nasce com chave nova (outra escolha) e o motor POSTa de novo. Se o portal ainda publicar a agenda (não medido), é agendamento duplo, irreversível pela API. Três condições, mas duas delas são nossas e a prova para recusar já está em memória (`rg`). Classifico BLOCKER por §3.2 (envia) + §9.1 (integridade/efeito colateral) e porque o conserto é ≤ 30 min em 2 arquivos.
**Conserto (o executor reproduz antes):**
1. `vidros_continuacao.py`, depois de `ex.agregado = agregado`: se `API.script_de_finalizacao(agregado)["agendamento"]` existir e `operacao == "agendar"` → não chamar `agendar_escolha`; devolver `_concluir` com `ST.ler_conclusao(desfecho_anterior.roteador, agregado)` (tipo `agendado`, idempotência pela leitura — o que o §8.2 da SPEC promete).
2. `portal_tool.py:buscar_ultimo_estado_do_pedido`: no `except`, **não** devolver a abertura; devolver `{}`/sinal de "não sei" e a tool responder "não consegui conferir o estado do pedido; tente de novo em instantes" (fail-closed, mesma regra de `_envio_liberado`).
Mutação para o guarda: reintroduzir o POST com o agregado já agendado ⇒ VERMELHO.

## PENDÊNCIAS (registram-se; não travam)
- **P1 · PATCH /atendimentos reenviado na retomada antes do número.** Medido (m3, etapa `materializar`, cursor após o 1º PATCH): a continuação emite `PATCH /atendimentos` de novo (mesmo corpo) antes do questionário. É update idempotente por semântica e o corpo é igual; 0 exercícios de PATCH duplo no acervo. Fecha-se pulando o PATCH quando o agregado já traz `CodigoItemCoberto`/`CodigoCidade` iguais.
- **P2 · `blocos_livres` ignora `PossuiEncaixeDisponivel`.** O bundle (laudo §1, `P.blocosDeHorariosEncaixe`) só lista na aba de encaixe blocos com `PossuiEncaixeDisponivel===true`; o código oferece encaixe por `QuantidadeEncaixeParametrizadoDisponivel>0` só. 📊 No HAR [045] os dois conjuntos coincidem (8 = 8, `set(qe)==set(pe): True`), então hoje não muda nada; o dia em que divergirem o motor pode agendar num bloco que a tela não oferece. Conserto: `elif encaixe and b.get("PossuiEncaixeDisponivel") is True`.
- **P3 · A mensagem de `agendado` promete reagendar** ("Se precisar mudar o dia ou o horário, me avise por aqui") e reagendar está FORA (§3 "Sai"). Com a última continuação `concluido` a tool responde honesto ("quem conclui é a equipe"), então não mente — mas convida o caminho do B1. Trocar por "me avise por aqui que a nossa equipe ajusta com a loja".
- **P4 · `enfileirar_continuacao._viva()` em exceção segue para o INSERT** (a rede é o índice único — vale só para a MESMA chave). Coerente com B1-2: leitura falhou ⇒ não enfileirar.
- **P5 · `pode_repetir`/reler do contato refaz `PUT /atendimentos/corretores` já aceito** (`tipo_de_telefone_desconhecido`, `solicitante_recusado` ⇒ etapa `contato`). PUT idempotente; 0 exercícios de PUT duplo. Registrar.
- **P6 · `params->>_pedido_key` no `.eq()`** só foi provado no dublê; o padrão existe no produto (`relatorios_comerciais.py:382`, `chat.py:983`) — por medir uma vez no PostgREST real (G12/canário).
- **P7 · Pós-agendamento de `opcoes-disponiveis`** e **401 no meio da continuação** (depois do 200 inicial) não têm captura. O 401 tardio cai em `agendamento_nao_confirmado`/`vistoria_nao_confirmada` com `guard.incerto` — legível, mas é a equipe. Gatilho: captura.

## EVIDÊNCIA (comandos e saídas)
Gates (`cd backend && PYTHONIOENCODING=utf-8 python tests/<arq>.py`, todos `exit=0`):
`test_e001101_o_fio_da_continuacao` 78/0 · `test_e001101_a_costura_da_continuacao` 60/0 · `test_e001101_c_a_coleta_sem_domicilio` 37/0 · `test_e001101_c_a_tool_continua_o_pedido` 39/0 · `test_e001101_c_as_mensagens_da_continuacao` 86/0 · `test_e001101_c_o_vigia_rele_a_parada_tecnica` 25/0 · `test_e00110_a_escada_e_a_seguradora` 165/0 · `test_o_fio_do_portal_de_vidros` 66/0 (LAT, NOVO, ANT — G10) · `test_o_freio_de_vidros_nao_mata_a_cobranca` 33/0.
Regressão dirigida: `test_spec074_vidros_mutations` 67/0 · `test_spec075_contrato_da_factory` 151/0 · `test_e00110_c_*` 46/88/44 · `test_o_protocolo_volta_para_o_segurado`, `test_o_agente_entra_no_portal_sabendo`, `test_o_portal_nao_abre_duas_vezes_o_mesmo_pedido` OK.

Medições do juiz (3 números por amostra, m1/m2/m3):
- HAR LATERAL: 51 chamadas; [045] 40 blocos, ordem cronológica `True`, `Turno={'Value':'Manha'|'Tarde'}`, `QuantidadeDisponivel>0: 0`, encaixe: 8 (08,10,11,12,13,14,15,16), `EncaixeCeven=None`; [048] corpo 7 chaves `{CodigoCliente:int, 'DataDeAgendamento':'2026-09-22','Horario':'16:00',CodigoProduto:int,75,90,Encaixe:True}` → `{ServicoAgendado:True}`; [049] `script_de_finalizacao` → `{'data':'22/09/2026','horario':'16:00','permanencia':'01:30 Hrs.'}`, `tem_loja True`; `ler_conclusao([037],[049])` → `agendado` com loja/endereço/referência.
- HAR LATARIA2 (faixa 2): 36 chamadas; [029] `BloqueadoIlhaNormal=True PermiteOpcaoVistoria=True`; [031] `GET prioridades → 'false'`; [032] corpo `== API.PRIORIDADE_NEUTRA` **True**; [033] `Ocorrencia == API.OCORRENCIA_VISTORIA['loja']` **True** (byte a byte).
- D-E001101-02: pref manhã/21 → POST 1× `08:00` (=esperado por caminho independente), Encaixe True, dia 22; tarde/22 → `13:00` (=esperado); qualquer → `08:00`; **não casa** (a partir de 23/09) → `POSTs=0`, desfecho `agenda`, `customer_choice=True`, `continuacao={agendar, possivel True}`, `lojas[0].horarios={'22/09':['08:00','10:00','11:00',…]}`; período inválido → `POSTs=0`. Loja mais próxima por `_km` (1 loja no acervo — empate/ordem não exercido).
- G3/G6: `criar_atendimento` em `modo_continuacao` → `erro=continuacao_nao_cria_atendimento`, `chamadas_de_rede=0`; token do acervo presente (`True`) e ausente de 6 evidences + 4 mensagens (`False`), ausente da linha do job (`False`), cifra presente e abre o token com o cofre (`True`); `repr(SessaoVidros)` sem token.
- Idempotência: mesma escolha 2× → chaves iguais `True`; outra corretora ≠ `True`; outra hora ≠ `True`; sem protocolo → `''`. Mesma escolha 2× no motor com a evidence da 1ª → `sessao_indisponivel`, POST total 1 (a cifra é descartada em `concluido`).
- `pode_sair(caminho, metodo)`: `/agendamentos` POST True · `/agendamentos/encaixes|insatisfacao` POST **False** · `/atendimentos/livres-escolhas` POST **False** · `/direcionamentos` False · `emitir-atendimento-formalizado/{cod}` True · GET com query True.
- Vazio/nulo: sem `_continuacao`, `{}`, sem cifra, cifra lixo, operação desconhecida → `needs_human`, `rede=0`, cifra descartada, token não vaza (5/5).
- Dois tenants: `company_id` em `_aguardar`, `buscar_ultimo_estado_do_pedido` (filtro + segunda rede na linha), `enfileirar_continuacao._viva`, `_reler_evidencia`, update do vigia — lido no diff e coberto por `test_e001101_c_a_tool_continua_o_pedido` (B não acha a continuação de A).
- Worker (`worker.py:1153-1195, 1463-1545`): `continuar_atendimento` registrado MATERIAL (`journeys/__init__.py:256`), `motivo_para_barrar` com a journey própria (freio/allowlist valem); exceção após `armed/submitted` ⇒ `unknown` + `needs_human`, nunca requeue.
- Textos: "agendado" só com `confirmado_pelo_portal is True` (`_bloco_do_agendamento`); "eu agendo/continuo" só com `continuacao.possivel is True` (`texto_da_parada`, `_bloco_da_agenda`, vigia `_pode_continuar` exige `pedir_releitura` nas técnicas). `agendamento_nao_confirmado` é reler-não-automático (fora de `ESTAGIOS_TECNICOS`): nem tool nem vigia repetem o POST — medido pelo G1 CONTROLE do fio.
- Roteador: `BloqueadoIlhaNormal` saiu das travas por medição (0 ocorrências no bundle; [029] o portal seguiu). Ramo 7 → `vistoria_opcional`; ramo 8 só com script não vazio.

## MAIOR LACUNA
O estado do portal DEPOIS de um agendamento (o que `opcoes-disponiveis` e um 2º `POST /agendamentos` devolvem) não tem captura — a idempotência "pela leitura" de `agendar_escolha` apoia-se nisso. B1 fecha a porta com o que JÁ é medido ([049]).

## PRÓXIMA AÇÃO
Consertar B1 (2 arquivos, guarda com mutação), rerodar `test_e001101_o_fio_da_continuacao` + `test_e001101_c_a_tool_continua_o_pedido`; registrar P1–P7; confirmação curta (§6.1).

## CONFIANÇA e o que ficou por medir
Alta no fio (replay real + motor real, 9 gates por comando, ataques reproduzidos). Não medido: PostgREST real com `params->>_pedido_key`; portal depois do agendamento; 401 no meio da continuação; empate de distância entre lojas; canário G12 (Founder).

## NOTA: 86/100
Sólido, honesto nos textos, token nunca em claro, tenant filtrado, D-02 exato. Perde por um caminho de segundo POST irreversível que a própria leitura já permitia recusar, e pelo fail-open na tool.
