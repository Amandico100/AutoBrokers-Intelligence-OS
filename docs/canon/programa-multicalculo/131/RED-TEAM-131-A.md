# RED TEAM · SPEC-131-A · A madrugada da renovação

> 🗡️ red team fresco · modelo `claude-opus-5-5` · 13/10/2026 · branch `spec/131-A-a-madrugada` · diff `2cd6168..3ac24ef`
> Read-only no produto. Banco: só SELECT (projeto `dcajcvlzcjbmyapmklil`). Ataques que escrevem rodaram contra DUBLÊ
> (scripts em `scratchpad/redteam131a/`, fora do git). Nenhum Agger, nenhuma InfoCap, nenhuma mensagem.
> 📊 medido · 💭 inferência.

## VEREDITO — QUEBREI (1 blocker, 11 pendências)

## BLOCKER

### B1 · O desvio das 06:15 recalcula no Agger da CORRETORA uma renovação que JÁ saiu no Agger da dona, e avisa errado
**Teste do produto:** muda bytes no Agger da corretora (um 2º negócio com 2–3 `calcularV2` da mesma renovação), no banco
(`renovacoes.pedido_id` passa a apontar para o pedido do desvio; o negócio da dona fica órfão do item) e no aviso ao dono
("o Agger do dono não ficou livre até as 06:15", que é falso).

**Por quê.** O estado do item é DERIVADO por pull (`madrugada.acompanhar`), e só dois passos o derivam:
`workflow_calcular → _acompanhar_ou_dormir(ate_passo="conferir")`, que para às **05:30**, e
`workflow_desvio → _acompanhar`, que roda **depois** do `_desviar`. `desvio_dia` (`madrugada.py:654-688`) escolhe
`aguardando_agger` pelo estado GRAVADO, sem reler os cálculos. A retentativa do motor (`motor._pessoa_voltou`,
`motor.py` ~L1356–1389) põe o cálculo de volta com `disponivel_em = agora + 60 min` enquanto isso for `≤ 06:15`; a última
retentativa cai sempre em (05:15, 06:15]. 💭 Em ~75% das cadeias ela cai depois das 05:30. Se a dona já saiu do Agger,
o motor calcula NO AGGER DELA às 05:31–06:14; o item segue `aguardando_agger` na tabela; às 06:15
`_pedir(forcar=…)` → `porta._aberto_da_renovacao(cancelar=True)` só cancela pedido `aberto` e cálculos `na_fila`
(`repositorio.cancelar`, L96–105). Pedido `fechado`, ou com cálculo já no robô, segue vivo → pedido novo no Agger da
corretora.

**Reprodução** (dublê total: repositório, porta, InfoCap e avisos falsos; `madrugada.desvio_dia` e
`estado_derivado` são os REAIS):
```
cd backend && PYTHONIOENCODING=utf-8 python <scratchpad>/redteam131a/ataque_madrugada.py
== ATAQUE A: desvio 06:15 sobre item aguardando_agger cujo pedido JÁ FECHOU com 20 ofertas
estado_derivado do pedido velho: ('calculada', None)
desvio: {'desviados': 1, 'falharam': 0} | porta chamada: [('r1', 'renovacao_desvio_0615')] | transicoes: [('r1', 'calculando', None)]
aviso: ['1 renovação(ões) sua(s) foram calculadas no Agger da CORRETORA: o Agger do dono não ficou livre até as 06:15.']
```
Nenhum teste da SPEC cobre o caso: `test_a_dona_no_proprio_agger_vira_aguardando_e_o_desvio_vai_a_corretora_com_aviso`
(`test_spec131a_a_lista_e_a_conferencia.py:330`) só testa o pedido da dona ainda parado.
**Conserto mínimo:** em `desvio_dia`, rodar `acompanhar(db, cid, por=…)` ANTES de montar `alvo`; e, por item, pular
quando `_ler_o_pedido` mostrar cálculo em curso ou ofertas (estado derivado ≠ aguardando/falhou passageiro).
**Mutação de controle:** com o `acompanhar` antes, o ataque A deve dar `porta chamada: []`, o item `calculada` e nenhum
aviso de desvio.
📊 Hoje o alcance é 0: `portal_accounts` com `uso='membro'` = **0** (só `global` 2 e `teste` 2), e `tenant_auxiliaries`
com slug de renovação = **0**. O defeito sai junto com o primeiro Agger de pessoa instalado na 131-B.

## PENDÊNCIAS
| # | achado | onde | o que destrava |
|---|---|---|---|
| P1 | **A conferência dá "completo 100 %" com a InfoCap devolvendo vazio.** `_get` trata 404 como `{}` (e guarda no cache), e `renovacoes_cruas` devolve `[]`. Então esperadas = 0, `_pct(0,0)=100`, nenhum aviso. A tabela tinha 3 itens do período ainda `pronta`. 📊 dublê, ataque B: `{'estado': 'completo', 'esperadas': 0, 'completude_pct': 100.0} \| avisos: []`. O elo "InfoCap fora → sem_conexao, nunca 0" fura quando a falha vem como 404 ou como 200 vazio | `conferencia_da_renovacao.py:96-130`; `fonte_infocap.py` `_get` 404 | conferir também ao contrário: item da tabela com fimvig em [dia, dia+antecedência] e fora de `substituida` que não voltou da InfoCap → o dia não fica "completo" (`divergente`/`sem_conexao`) |
| P2 | **Dia "completo" com 0 calculadas.** Se o dono não abriu a InfoCap às 00:30, tudo fica `pendente(sem_conexao)`, e isso conta como feito. 📊 ataque C: `completo 100.0 · cotáveis 3 · calculadas/cotáveis 0.0`. Está na régua da SPEC (§4), mas o aviso das 06:45 mostra "completude 100.0%" | `conferencia_da_renovacao.py:139-158` | tirar `sem_conexao` do numerador, ou pôr "calculadas ÷ cotáveis" no aviso (decisão do Founder) |
| P3 | **A `franquia_reduzida` nunca aparece.** 📊 5/5 pedidos reais saíram com `opcoes=["anterior","completa_mais"]`. O `anterior` nasce do `_PADRAO`, que já tem `tipoFranquia=1` (reduzida); a ficha raramente diz "normal"; aí `_sem_repetidas` descarta a reduzida. A regra "já era reduzida, cede o lugar" vale sobre um valor SUPOSTO (não conferido). Resultado: a corretora recebe 2 opções, não as 3 do OUTCOME | `presets.py:404-416` | decidir se, sem a franquia lida na ficha, a reduzida vira "normal → reduzida" (opção real) ou se a SPEC passa a prometer 2 |
| P4 | **A janela do Prosseguir não tem trava de "madrugada".** `_janela_limpa` e `motor.janela_da_madrugada` só conferem HH:MM. Com `prosseguir_de 00:00 / ate 23:59`, `dentro_do_prosseguir` vale ao meio-dia, e a "noite" (meio-dia a meio-dia) deixa 2 Prosseguir no mesmo dia. 📊 `11h → noite 2026-10-14`, `13h → noite 2026-10-15`, as duas dentro. Exige o aceite (T-156), mas a tela da 131-B vai gravar essa config | `config.py:559-571`; `motor.py` `dentro_do_prosseguir`/`noite_da_madrugada` | prender `prosseguir_de/ate` a um intervalo noturno (ex.: dentro de 00:00–07:00) nos dois leitores |
| P5 | **"1× por noite" falha aberto.** O evento `prosseguiu_sessao` só é gravado DEPOIS de o login chegar a `/cotacoes` (`_depois_do_login`). Duas coisas apagam a marca: um timeout depois do clique e um erro de escrita (o `except` só registra no log). Sem a marca, o próximo grupo prossegue de novo na mesma noite | `motor.py` `_depois_do_login`, `agger_sessao._entrar` | gravar a marca ANTES do clique (reserva), ou na falha da escrita não prosseguir |
| P6 | A guarda aceita o Prosseguir com OUTRO `email` no corpo (só confere as chaves e o `derrubaSessao`). 📊 `email de outra conta → (True, 'prosseguir')`. O id amarra a sessão, então o risco é baixo | `agger_guarda.prosseguir_valido` | conferir `email` == o do 1º login do contexto |
| P7 | **Item `falhou` recalcula toda noite.** `ESTADOS_PREPARAVEIS` inclui `falhou`, e falhou → pronta → calculando. 📊 O item `4d9be9e8` já gerou 2 pedidos com 0 ofertas no canário (03:35 e 04:43). Uma recusa de todas as seguradoras se repete até o fimvig, gastando `calcularV2` todo dia. O motivo `calculo_fechado` também aparece cru no aviso ("calculo fechado") | `renovacao.py:59`; `madrugada._motivo_do_calculo` | teto de tentativas por item e frase humana para `calculo_*` |
| P8 | **Fila global de 50 linhas e teto 1 por corretora.** `_reservar` lê as 50 primeiras `na_fila` por (prioridade, criado_em). Grupos de uma corretora que esperam o teto não consomem nada, mas ocupam a cabeça da fila: 💭 a madrugada de uma corretora grande (📊 pico de 42 renovações de um dono, D-131-33) atrasa a das outras. A sessão "segurada" para a pessoa trava os outros logins da corretora por até 10 min (`OCIOSA_MAX_S`). É um teto, não um livelock | `motor.py` `_reservar` (L89 `LIMITE_DA_FILA=50`), `_cabe_sessao` | medir no canário de 2 corretoras; buscar a fila por corretora |
| P9 | **Implantar parcial.** Com smith-api novo e portal-worker velho, o motor velho ordena `anterior` em 9, e o negócio abre pela `completa_mais`. O montador velho não tem o combustível da F6: 📊 a 1ª rodada do canário deu 114 `seguradora_recusou` e 0 ofertas. Nada sai errado para o cliente, mas o dia enche de `falhou`. `ignorar_espera` só é ligado pelo `scripts/canario_madrugada_renovacao.py:429` (grep) | deploy | implantar os dois serviços juntos (anotar no roteiro) |
| P10 | **Frota e RCF-V viram AUTO por mapeamento explícito.** `FAMILIAS_DE_RAMO["auto"]` tem `frota`, `auto frota` e `rcfv`. Frota com a placa da apólice batendo num item: 💭 calcula 1 veículo de N e marca `calculada`. RCF-V: o `anterior` parte do preset completo (com casco). Não é a mutação 3 (não é por omissão) | `policy_data_provider.py:1284`; `perfil_da_renovacao._item_do_veiculo` | `pendente(ramo_nao_cotado)` para frota/rcfv na renovação, até medir |
| P11 | CLAUDE.md §13.9: o script de medição tem nomes de corretora como constante (`AGGER_AUTOFLEET_COTADOR_LOGIN`, `AGGER_RESULTA_COTADOR_*`) | `scripts/bloco0_131a_agger_ao_vivo.py:323,601,681` | ler por `company_id`/argumento |

## O QUE TENTEI E NÃO QUEBROU
- **Guarda do Prosseguir** (`ataque_guarda.py`, `agger_guarda.decidir` real). Passa: id exato e id em maiúsculas sem
  hífen. Barram: id errado, chave extra, sem a política, antes do 1º login, 2º Prosseguir, e o id trocado depois do 1º
  (`registrar_sessao_ativa` guarda só o 1º).
- **Conta global/teste.** Três travas: `Sessoes.obter` (uso membro e não teste), `_pode_prosseguir` (uso, `dono_user_id`,
  todos os cálculos com `conta_regra=renovacao_do_dono`) e o aceite. A porta recusa `politica_de_sessao` fora da
  renovação e junto do desvio. Retomada nunca prossegue.
- **Janela padrão no fuso.** 📊 00:59 BRT fora · 01:00 dentro · 06:29 dentro · 06:30 fora (instante passado em UTC).
  `briefing_profiles`: 📊 3 corretoras, todas `America/Sao_Paulo`, nenhuma com dois fusos. O motor e a madrugada leem a
  mesma fonte. O dia da chave `renov:<passo>:<company>:<dia>` é o dia local (`passos_na_janela`).
- **Token da outra sessão.** `_ler_login` só tira `data.id` e as datas da licença. Nenhum `logger` recebe o corpo.
  Nenhum `record_har`/tracing. A guarda registra só a URL saneada.
- **Prioridade.** `_da_madrugada` recusa prioridade abaixo da do serviço (7). O motor ordena por `prioridade` crescente
  (0 < 5 < 7). O recálculo fica em 7. O teto por corretora só vale com `madrugada=True` e não trava a cotação de dia. A
  sessão segurada fecha às 06:30 (`_segurar_para_a_pessoa` → `dentro_do_prosseguir`) e sempre em ≤ 10 min ociosa.
- **Isolamento.** Todo `.table()` de `renovacao.py`, `madrugada.py`, `conferencia_da_renovacao.py` e `qual_agger.py`
  filtra `company_id`/`solicitante_company_id` no banco E de novo em Python. A ausência filtra corretora e
  `user_id`, e a FK `(user_id, company_id)` impede o substituto de outra corretora.
- **Dado pessoal no banco** (📊 SELECT). `cliente_nome_curto`: 8/8 com 1 palavra. `documento_mascarado`:
  `***.***.***-99` 7 e `**.***.***/****-99` 1, os 8 com HMAC. `renovacao_eventos.dados` só tem as chaves
  `faltando` e `nao_conferidos`. 0 eventos com padrão de CPF, placa ou telefone. `multicalculo_pedidos` guarda o pedido
  cifrado. Grep do diff: só documentos sintéticos (`000…`, `529.982.247-25`) e a placa `AAA1A11`.
- **CPF inválido.** Os caminhos `/cliente_cpf`, `/busca_cpf` e `/producao?texto=` do `infocap_connector` passam por
  `_cpf_cnpj_ou_recusa`/`_recusa_documento_invalido` antes da rede.
- **Ramo.** Sigla fora do agrupamento → `RamoIndisponivel("ramo desconhecido")` (`pedido.py:742`). 📊 no canário,
  `MOBI` → `pendente(ramo_desconhecido)` 2/2.
- **Econômica e mínima** recusadas em três lugares: `conferir_opcoes_da_renovacao`, `_opcoes_validas` da config e a
  porta.
- **Idempotência.** UNIQUE + `upsert_da_lista` + `transicionar` idempotente. A porta devolve o pedido `aberto` da
  renovação (janela de crash). O desvio cancela o aberto. O tick usa a chave por passo e dia.
- **O fio.** O tick chama `_renovacoes`. Os 5 workflows estão registrados (`registrar_workflow`) e carregados por
  `carregar_extras`. 📊 `tenant_auxiliaries` com slug `renovacao`/`renovacao-maxima` = 0, então nada roda hoje.
  `aplicativo_ligado` filtra por `company_id`: quando a 131-B instalar, roda só na corretora que ligou.
- **Combustível no canal (133-A).** "gasolina" agora vira código 1 (lido no bundle, com o flex = 6 de controle). Nenhum
  teste do canal afirmava a recusa. Sem regressão a apontar.
- **Teste do fio e costura:** 📊 `pytest tests/test_spec131a_o_fio.py tests/test_spec131a_costura.py -q` (sem
  `SUPABASE_*` no ambiente) → `11 passed, 14 warnings in 181.38s`. Eles passam, e nenhum dos dois cobre o B1. Não rodei
  mutações: são do juiz.

## O ELO MAIS FRACO
O estado derivado por pull só é relido até as 05:30. Tudo o que o motor faz depois disso (a retentativa da dona) fica
invisível para o desvio das 06:15 e para a conferência.

## NOTA · 78 / 100 · confiança 85 %
