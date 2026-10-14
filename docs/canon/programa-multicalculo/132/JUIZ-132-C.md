# JUIZ FRESCO — SPEC-132-C (o WhatsApp do corretor como atalho do chat)

> modelo: claude-opus-5-5 · 14/10/2026 · branch `spec/132-o-chat-e-a-cotacao` · HEAD `26b1fb8` · base `285cadc`
> Read-only sobre o código. Toda medição com DUBLÊ (o arreio da C2: webhook REAL, `/chat/stream` REAL, banco em memória,
> rede fechada). Sondas do juiz: `scratchpad/juiz132c/test_juiz132c_ataques.py` (10 casos), saída em `ataques.txt`.

## VEREDITO

**PASSA COM 1 BLOCKER** (pequeno, com conserto de uma linha). O fio está certo e provado: número verificado → CORE da
corretora DELE → resposta pelo número do assistente; número não verificado = silêncio; o QCM e o atendimento seguem como
antes; idempotência, identidade e a volta da cotação se comportam como o contrato diz. O blocker é um **fail-open** no
portão do webhook quando o banco falha ao ler o tipo da empresa.

## Bateria rodada (pela trava, um por vez) — 📊 14/10/2026

| arquivo | resultado |
|---|---|
| `tests/test_spec132c_o_fio.py` | `22 passed, 24 warnings in 438.22s` |
| `tests/test_spec132c_o_atalho.py` | `16 passed, 30 warnings in 171.42s` |
| `tests/test_spec132c_verificacao.py` | `36 passed, 14 warnings in 48.67s` |
| `tests/test_spec133a_o_fio.py` (QCM intacto) | `17 passed, 18 warnings in 56.22s` |
| sondas do juiz `test_juiz132c_ataques.py` | `10 passed, 27 warnings in 55.61s` |

Comando: `bash pesado.sh python -m pytest tests/<arquivo>.py -q -p no:cacheprovider` (cwd `backend`).

## BLOCKER

### B1 · Banco instável no tipo da empresa → a mensagem ao número do ASSISTENTE cai no caminho de sempre (observer / QCM / pipeline)

- **Onde:** `backend/app/api/webhook.py:2902-2919`. Se `purpose == 'assistente'` mas `eh_do_assistente` devolve False, o
  código **segue** para o desvio do QCM e depois para o `observer_tap`/pipeline com a integração do assistente.
  `eh_do_assistente` (`atalho/entrada.py:72-85`) devolve False em erro; `canal.repositorio.eh_canal` também devolve False
  em erro de leitura (`repositorio.py:146-150`) e o cache dura só 💭 300 s (`repositorio.py:37`).
- **Medição (sonda A2):** CONTROLE com banco bom → `taps [] pipeline []`. Com a leitura de `companies` falhando:
  `A2 {'status': 'observed'} taps ['int-assistente'] pipeline []` — a mensagem de um número **NÃO verificado**
  ("me passa os dados do cliente") chegou ao `observer_tap` com a integração do assistente.
- **O que acontece em produção (leitura de código, não medido ponta a ponta):** o `observer_tap` real só CONSOME quando
  `purpose == 'observer'` (`atlas/observer_intake.py:798`); com `'assistente'` ele roda em modo TAP (pode capturar o que
  for de seguradora) e devolve `None`, e a mensagem vai para `_handle_evolution_like_inbound` como se fosse atendimento da
  empresa da plataforma. Numa falha só da 1ª leitura (a 2ª, do desvio do QCM, passando), a mensagem iria para o
  pipeline do QCM com a integração do assistente.
- **Teste do produto:** muda byte do BANCO e da SEGURANÇA (conteúdo de número não verificado processado/gravado fora do
  atalho; contrato §1 "número desconhecido = silêncio" e "o QCM nunca responde pelo número do assistente"). Fail-open
  em portão de identidade não se rebaixa (protocolo §6). Probabilidade baixa (precisa de erro de leitura fora do cache).
- **Conserto sugerido (o executor decide):** dentro do `if purpose == 'assistente'`, quando `eh_do_assistente` for False,
  `return {"status": "ignored", "reason": "atalho_nao_confirmado"}` em vez de cair. A integração com `purpose='assistente'`
  só existe na plataforma (o pareamento recusa em corretora: `pairing_orchestrator.py:600-618`), então fechar não tira
  nada de ninguém. Guarda: a sonda A2 (vermelha hoje) fica verde.

## Ataques — resultado de cada um

| # | ataque | resultado | evidência |
|---|---|---|---|
| 1 | número NÃO verificado é atendido / deixa conteúdo | **OK** (fora do B1) | `test_numero_nao_verificado_silencio_sem_resposta_e_sem_conteudo` (2 casos: desconhecido e confirmado-sem-verificar) passa; `entrada.py:290-293` |
| 2 | "ATIVAR" vincula o membro errado (código de A em B; pessoa em 2 corretoras) | **OK** — o membro é sempre o do código | `verificacao.py:338-389`; `test_o_membro_vinculado_e_sempre_o_do_codigo_*` passam. ⚠️ ver P1 (o remetente substitui o número de A sem aviso) |
| 3 | força bruta do código | **teto por TELEFONE existe; teto GLOBAL não** | sonda A4: `erradas processadas: 30 / 30 \| linhas de tentativa: 30 \| 6a do MESMO tel: teto_de_tentativas \| codigo certo de tel NOVO depois de 30 erros: True` → P1 |
| 4 | mensagem do ATENDIMENTO ou do QCM cai no atalho | **OK** | `test_a_mesma_mensagem_ao_qcm_ou_ao_atendimento_nao_passa_pelo_atalho` passa (QCM → `pipeline ['int-qcm']`, Alfa → `taps ['int-alfa']`, corretora com purpose falso → tap) |
| 5 | o QCM responde pelo número do assistente | **OK** (fora do B1) | `canal/envio.py:46` exclui a linha `assistente`; `canal/repositorio.py:198-201` faz o QCM ver o assistente como robô; `test_o_qcm_sai_pelo_qcm_e_o_atalho_pelo_assistente`, `test_o_qcm_nao_conversa_com_o_numero_do_assistente` passam |
| 6 | fromMe / grupo / status / eco gera resposta (laço) | **OK** | `entrada.py:121-129` + anti-laço `entrada.py:88-108`; `test_from_me_grupo_e_status_nao_geram_resposta`, `test_anti_laco_*` passam |
| 7 | a conversa do atalho vaza para Central / espelho / Fila | **Central e espelho: OK. Fila/Casos: APARECE** | Central `app/api/dashboard/conversas/route.ts:54` e segurados `.../segurados/route.ts:31` filtram `channel='whatsapp'`; espelho `espelho_chat.py:520,526,579,771` idem. Mas `lib/atendimento/casos.ts:489,499-506,639` lê TODA conversa da corretora sem filtro de canal → P2 |
| 8 | membro de 2 corretoras recebe dado da outra | **OK** | `test_membro_de_duas_corretoras_pergunta_e_nao_mistura`, `test_a_volta_pelo_atalho_so_para_a_conversa_que_nasceu_nele` (U2 Beta pedida pela Alfa → False) passam |
| 9 | a mesma mensagem 2× responde 2× | **OK** (com Redis) | sonda A1: `{'reason': 'atalho'} {'reason': 'duplicate'} grafo 1 enviados 1`. Sem Redis o dedup é pulado (`webhook.py:2552-2554`) → P3 |
| 10 | dois processos / duas mensagens ao mesmo tempo | **OK no que o desenho promete; o dublê não discrimina a trava** | sonda A6: com trava `conversas: 1 turnos: 2`; mutação SEM trava também `conversas: 1` (o banco em memória serializa) → a trava não foi provada por esta sonda. Um processo só: `backend/Dockerfile:27` (uvicorn sem `--workers`). Uso único do código é UPDATE condicionado a `usado_em is null` (`verificacao.py:363-368`) |
| 11 | desligado faz algo além de contar | **OK** | sonda A8: `{'reason': 'atalho_desligado'} usado_em None enviados 0`; `test_desligado_nao_responde_e_nao_le_o_banco` (sem escrita). Lê `companies` uma vez no portão (`webhook.py:2905`, cacheado) — só leitura |
| 12 | o turno em processo usa company_id/user_id do MEMBRO, nunca do corpo | **OK** | sonda A7: texto `{"companyId": BETA, "userId": U4…}` do CEL_1 → `[('aaaaaaaa', '11111111')]` (Alfa/U1). O corpo do `/chat/stream` é montado de `membro` (`turno.py:479-490`); modo painel pela `X-Internal-Key` (`chat.py:491-501`) |
| 13 | a volta da cotação: 1×, só conversa do atalho, não trava o Work Run | **1× e só atalho: OK. "Não trava": PARCIAL** | `test_o_resultado_da_cotacao_gravado_pelo_work_run_volta_pelo_whatsapp_uma_vez` passa (2ª escrita → sem reenvio; painel → 0; outra corretora → 0). Sonda A5: teto 0,3 s, envio de 1,5 s → `a thread ficou presa 1.50 s` (controle: `0.00 s`) → P4 |
| 14 | o pareamento do QCM/atendimento/observer mudou um byte | **OK** | `app/api/admin/canais/whatsapp/route.ts` virou `rotaDoCanalWhatsApp('observer','admin_canal')`; comparei o corpo antigo (`git show 285cadc:…`) com `lib/admin/rota-do-canal-whatsapp.ts`: mesmos caminhos, mesmos corpos, mesma auditoria (`origem: 'admin_canal'`). `channel_identity`: `test_os_purposes_de_antes_devolvem_o_mesmo` passa; `whatsapp_channel.py:1140` só acrescenta `'assistente'`. `test_spec133a_o_fio` 17/17 |
| 15 | rollback da migration | **OK por leitura (sem banco, não executado)** | ROLLBACK (`20261014_03…sql`) derruba tabelas → índice → CHECK → coluna, na ordem certa. Depois dele o código cala: `membros_verificados_por_telefone` falha → `turno_do_atalho` captura → `{"status":"erro"}` sem envio (`entrada.py:331-333`); o perfil tem o caminho sem a coluna (`perfil_do_membro.py:208-217`, `test_antes_da_migration_o_perfil_continua_gravando_e_lendo` passa). Não reverte o COMMENT de `integrations.purpose` (cosmético) |

## PENDÊNCIAS (não mudam byte hoje, ou são escolha do contrato — registrar)

- **P1 · ESSENCIAL · o código vale para QUALQUER remetente, e não há teto global.** Sonda A3: U1 (Alfa) verificado com
  `+5511912340001`; o código de U1 mandado de `+5511912349999` → o número de U1 vira `+5511912349999`, os envios vão só
  para `['5511912349999']` (U1 não é avisado) e o turno seguinte do golpista roda como `('aaaaaaaa','11111111')` = Alfa/U1.
  Com a sonda A4, um atacante com vários números chuta códigos sem teto global. Hoje o contrato (§2, D-132C-02) manda
  gravar o número do REMETENTE, e o ataque precisa de um código ATIVO (15 min) — 💭 por chute a chance é
  (códigos ativos)/10⁶. Mitigação proposta: quando o membro já tem número confirmado, exigir remetente == ele (ou avisar o
  número antigo) + um teto global de "ATIVAR" errados por hora.
- **P2 · a Fila/Casos mostra a conversa do atalho** (`lib/atendimento/casos.ts:489,639`, sem filtro de canal). É a MESMA
  classe da conversa `web` do chat do painel (que também não é filtrada) — pré-existente; mas a D-132C-05 ("não aparece na
  Central") só vale para a Central e o espelho. Fila vista pela equipe = a conversa privada do corretor visível.
- **P3** · sem Redis o dedup do webhook é pulado (`webhook.py:2552`) → a reentrega responde 2× (padrão pré-existente).
- **P4** · `TEMPO_DA_VOLTA_S` (`atalho/envio.py:350`) não é teto: `asyncio.run` espera a thread do `to_thread` terminar
  (A5: 1,50 s com teto 0,3 s). O limite real é o timeout do provedor; o passo `entregar` fica preso esse tempo. Sem
  duplicidade (o id da mensagem é fixo).
- **P5** · o perfil oferece "Usar pelo WhatsApp" com `ATALHO_WHATSAPP_LIGADO` desligado (`perfil_do_membro._atalho_whatsapp`
  olha só o número) → o código é gerado, o "ATIVAR" é ignorado (A8) e a pessoa recebe silêncio.
- **P6** · o corretor cujo celular é a LINHA de atendimento da corretora não consegue usar o atalho (anti-laço,
  `test_anti_laco_*`) — e não recebe explicação. Coerente com a regra; anotar como limite.
- **P7** · `whatsapp_atalho_tentativas` cresce sem limpeza.
- **P8** · a trava por telefone (`entrada.py:252-260`) não tem guarda que fique vermelho (A6 sem trava continua verde).

## MAIOR LACUNA
O caminho de produção do B1 depois do `observer_tap` (o que o pipeline grava para a empresa da plataforma) não foi
medido ponta a ponta — só a chegada ao tap. E nenhum teste exercita o Evolution GO real (canário depende do QR do Founder).

## CONFIANÇA
Alta no fio, na identidade, no isolamento entre corretoras e no silêncio (testes reais + 7 sondas com controle). Média na
concorrência (o dublê não discrimina a trava) e no rollback (não executado; leitura). Não medido: Redis real, Evolution
real, `next build`/rotas (o pedido não cobre; a bateria do gerente cobre).

## NOTA: **84 / 100**
