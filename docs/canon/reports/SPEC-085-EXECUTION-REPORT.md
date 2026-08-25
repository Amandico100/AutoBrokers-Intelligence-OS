# SPEC-085 · Relatório de execução — o destravamento não trava em silêncio

> Branch `feat/spec085-o-destravamento-nao-trava-em-silencio` · início `35cf0a7`
> Preflight §11: `HEAD..origin/main` = **0** · árvore limpa · `PYTHONIOENCODING=utf-8`
>
> 📊 medido · 💭 ilustrativo (`CLAUDE.md` §12.1). Número sem marca, aqui, é defeito.

---

# 📋 PARA O FOUNDER

> **Nada nesta caixa bloqueia a execução.** Ela é entregue inteira, uma vez, no fim.
> Cada linha diz o que é, o que você faz, o que custa esquecer, e se trava.

| # | o que é | o que você faz | custa se esquecer | trava? |
|---|---|---|:--:|:--:|
| **F-1** | 📊 **O freio de emergência não está mais armado.** `ACIONAMENTO_FREIO_DE_EMERGENCIA` sumiu do ambiente. Eram três freios em série (agente desligado · freio · gate); hoje são dois. `acionamento_liberado(agente LIGADO)` devolve **`True`**, quando antes o freio o derrubava. | decidir se o freio volta armado até o ensaio, ou se dois bastam | com o freio desarmado, escrever `INSURER_DISPATCH_LIVE=true` abre **envio real E finalização real** no `allianz-residencial` de uma vez — sem terceira rede | **NÃO** |
| **F-2** | ✅ **A duplicação de `INSURER_DISPATCH_LIVE` acabou.** O ambiente novo traz uma ocorrência de cada. Era P1 de configuração, e morreu. | nada — está feito | — | **NÃO** |
| **F-3** | 📊 **`CARTOGRAPHER_MODE=1` continua ligado** — o Cartógrafo manda WhatsApp **real** para seguradora, sem ninguém do outro lado esperando. É a P-32, aberta desde 03/08. | decidir se continua ligado | mensagem nossa chegando em seguradora sem contexto | **NÃO** |
| **F-4** | 🔴 **A régua da SPEC-083 devolve 102 numa escala de 100** e parou de achar órfã (5 asserções, `test_a_rubrica_e_honesta`). Uma régua assim **aprova o que deveria reprovar**, e o que ela aprova é rota que chega em segurado. | já decidido: é da **SPEC-089** | uma rota sobe sem estar pronta | **NÃO** |
| **F-5** | 🔴 **A trava que impede duas medições de corromper os 73 corredores não segura.** 📊 Uma mutação vazada desligou `schedule_agendado` no `allianz-residencial` — a âncora de *quando o prestador vem*, no corredor da única travessia ponta a ponta. O vazamento **sobrevive ao fim do pytest**. | saber que **`git add -A` neste repositório pode commitar uma mutação a qualquer momento** — adicione arquivo por nome | âncora morta = tela de URA que o corredor deixa de reconhecer = segurado sem socorro | **NÃO** |

---

# O que foi entregue, por fase

## FASE 0 · O travamento vira linha de banco — ✅ `bb71913`

**Migration `20260824_01_spec085_fase0_travamento_visivel.sql`**, aplicada, com
APPLY / VERIFY / ROLLBACK escritos **antes** de rodar:

| objeto | por quê |
|---|---|
| `work_steps.output_redacted` (jsonb) | o **gêmeo** mascarado da F1.2(i). 🔴 Nunca é lido pela restauração — mascarar `output_summary` faria um acionamento restaurado responder a máscara à URA. O porquê está no `COMMENT ON COLUMN`, não só aqui. |
| `work_runs.unblock_state` (text + CHECK) | `travado \| retomado_pelo_robo \| assumido_por_humano \| resolvido \| abandonado`. **NULL = nunca travou** — a linha de controle do §F0.3 item 2, escrita no schema. |
| `work_runs_travamento_idx` | parcial, por `company_id`. 📊 4 runs de acionamento contra 2.647 no total; índice cheio pagaria por 2.643 linhas que a Fila nunca olha. |
| 6 policies | `work_runs` · `work_steps` · `work_events`, `service_role` + `authenticated`. 📊 As três tinham RLS ligado e **zero policies** — `CLAUDE.md` §7: *"RLS sem policy não protege nada"*. Forma **copiada** de `human_support_destinations`, não inventada. |

📊 **VERIFY, 5 de 5:** as duas colunas · o CHECK · o índice · as 6 policies · e a
**linha de controle: 0 dos 2.647 runs existentes foi tocado.** Idempotência
provada por reaplicação: 6 policies continuam 6.

**O escritor está no PONTO DE ESTRANGULAMENTO, e isso é provado, não suposto.**
📊 São 19 sítios que escrevem `needs_human`; **17 vivem no motor**, que é núcleo
puro — `grep` por `get_supabase_client|db.client.table` nele devolve **vazio**.
Os outros dois (`dispatch_router:1453`, `dispatch_watchdog:299`) alcançam
`save_active_dispatch`. Instrumentar três, como a v1 da SPEC mandava, deixaria
13 famílias invisíveis — inclusive `sentinela_stall`, a única com prova em produção.

**`decidir_travamento` é PURA.** O gate cobra por FAMÍLIA de motivo, e dá para
percorrer as 16 sem banco, sem Redis e sem rede.

### Três decisões contra o texto da SPEC, com a nota

1. **A FASE 0 não grava PII nenhuma.** `output_redacted` nasce `NULL`; só a
   FASE 1 o preenche. Ampliar escrita de PII antes do mascarador é exatamente o
   que a ordem das fases (§4) existe para impedir.
2. **`human_review_tasks` recusada — 60/100 contra 92/100.** 📊 A §F0.1 e a P-225
   dizem que ela não tem escritor. **Tem:** `evals/juiz_llm.py:196`. Zero linhas
   porque nunca disparou. E `veredito boolean` + `amostra NOT NULL` são forma de
   **eval**; travamento não tem veredito booleano, tem desfecho de cinco estados.
3. **O BLOCO D não pode significar "ressuscitar depois das 6h".**
   `reconciliar_acionamentos_orfaos` já julgou e recusou isso **por escrito**,
   com o incidente da "sessão zumbi" de 12/07 atrás: restaura `monitoring`, não
   restaura `ura` nem `human_phase`. D é retomada **no instante do `needs_human`**.

### O gate da FASE 0, item por item — e o que NÃO fechou

| item do §F0.3 | estado | prova |
|---|---|---|
| 1b · conta FAMÍLIAS, não casos | ✅ | 16 famílias lidas do fonte pelo comando da SPEC; guarda compara com a triagem declarada e **quebra se aparecer família nova** |
| 2 · CONTROLE: acionamento bom não grava | ✅ | `test_CONTROLE_o_caminho_feliz_nao_marca_nada` percorre `ura → human_phase → ura → captured → monitoring → resolvido` e exige `None` em toda transição |
| 3 · o `reason` é o COMPLETO | ✅ | 📊 provado pela **produção**: `needs_human:missing_slots:problema_eletrico_opcao` já está gravado |
| 1 · a linha aparece no banco | ⏳ | exige escrita no banco — **fecha no ensaio G.1 com a AMANDUS** |
| 4 · dois tenants + mutação | ⏳ | exige o **leitor**, que nasce no BLOCO E |
| 5 · sobrevive ao TTL de 6h | ⏳ | por construção a linha é Postgres, não Redis; a **prova** é G.1 |

⚠️ **Não marco verde o que não medi.** Três dos seis fecham em G.

### O guarda, e o vermelho→verde

`tests/test_o_travamento_vira_linha.py` — 27 asserções, e ele **ataca a premissa
do próprio conserto**: o motor continua puro? os dois sítios de fora alcançam o
checkpoint? nenhuma família fica órfã?

📊 **Duas mutações, para provar que ele consegue falhar:**

```
mutação 1  tirar a chamada de _marcar_travamento    → 1 failed (o teste certo)
mutação 2  o gravador grava SEMPRE                  → 3 failed, os DOIS CONTROLES
restauração POR CÓPIA, conferida por sha256 (15e3d9ac…), 0 ocorrências de MUTACAO
verde de novo: 27 passed
```

---

## Achado fora de escopo, consertado: **o corredor voltava mutado de cada rodada**

📊 Quatro rodadas de `pytest tests/` na mesma árvore deram **2, 2, 7 e 11**
vermelhos — **conjuntos diferentes** — e todos os acusados passavam sozinhos.
Não era corrida, não era `.pyc` (rodada com `PYTHONDONTWRITEBYTECODE=1` e
`__pycache__` apagado), não era timeout (zero `passou de 120s`). Era isto:

```diff
  ALLIANZ_RESIDENCIAL_WHATSAPP_V1
- "schedule_agendado": (
+ "schedule_agendado_DESLIGADO": (
```

📊 Restaurada a linha, `test_a_maquina_de_lavar_vai_ate_o_fim` foi de
**107 verdes / 3 vermelhas** para **112 verdes / 0 vermelhas**, duas vezes.

🔴 **E o vazamento sobrevive ao fim do pytest** — `git status` acusou o arquivo
modificado segundos depois de a sessão sair, com 2 processos python ainda vivos.
As 8 janelas registradas são de guardas sem relação nenhuma entre si.

**O conserto, e o que ele NÃO é:** o arquivo é restaurado no meio da rodada, a
janela é registrada, e a **sessão** é reprovada no fim. ⚠️ A primeira versão
disto **acusava o guarda em cuja janela o arquivo mudou** — e o controle derrubou
a acusação: os três acusados passam limpos sozinhos, mesmo sha256. **Escrever a
acusação errada com mais confiança é pior que não ter checagem** (§9.3). O erro
ficou documentado no arquivo.

### A decisão do gate: **(a) — quarentena com o motivo, e o gate fica verde e VERDADEIRO**

O vermelho é **defeito conhecido e diagnosticado**, e **não é defeito que a
SPEC-085 conserte** (é triagem da P-226 sobre `test_duas_medicoes_nao_se_atropelam`).
Implementado separando dureza de informação:

```
test_a_arvore_ficou_limpa_no_fim    DURO, sem perdão — o produto tem de terminar
                                    byte a byte igual ao início
test_nenhuma_janela_ficou_suja      xfail(strict=False), com P-231 no motivo —
                                    é INTERMITENTE (8 janelas numa rodada, zero
                                    noutra), e strict quebraria nas limpas
```

🔴 Um gate permanentemente vermelho ensina todos a ignorá-lo. **O que é dureza
ficou duro; o que é informação ficou informação** — e as janelas continuam
aparecendo na saída.

---

## O CI

`gate.yml` ganha o job **`guardas`**, rodando `python -m pytest tests/ -q`.
**Um comando**, porque `pytest tests/` já inclui o meta-guarda — um passo
dedicado rodaria os 273 scripts duas vezes, ~3 min à toa.

Fecha o buraco que o aquecimento achou: 📊 **6 asserções de arquivos
pytest-nativos estavam vermelhas e nenhum executor as tocava** — nem o pytest
(que abortava a sessão), nem o meta-guarda (que os exclui de propósito), nem o
`broker_outcome_regression_pack`.

📊 **Suíte:** `305 passed · 45 xfailed · 1 failed` em 12m45 — e o `1 failed` era
o da sessão, agora em `xfail` com motivo.

---

## Pendências tocadas (§11.1)

| # | estado | o que mudou |
|---|---|---|
| P-34 | ✅ **MORREU** | a varredura de órfãos **está** registrada — `buffer_processor.py:370` |
| P-102 / P-116 | ✅ **FECHADA** | 📊 3 linhas, 2 corretoras; a **Resulta tem** destino ativo |
| P-30 | ✅ **MORREU** | 📊 zero compartilhamento entre corretoras; AutoFleet é *ausente*, não *recusado* |
| P-227 | ✅ **FECHADA** (duplicação) · ⚠️ **CONTINUA** (freio desarmado) | ver F-1 |
| P-31 / P-91 | ⚠️ **texto invertido** | dizem que o padrão é ABERTO; é FECHADO desde 14/08 |
| P-225 | ⚠️ **RE-JUSTIFICADA** | `human_review_tasks` **tem** escritor |
| P-226 | ⚠️ **cresceu e ficou visível** | cabeçalho e quarentena divergiam (151/14 vs 273/42) — corrigido |
| P-228 a P-231 | 🆕 | registradas |

---

## FASE 1 · O mascarador — e ele não era "uma linha"

A §F1.1 da SPEC já corrigia a v1: **não faltava uma chamada, faltava o
mascarador.** 📊 Os quatro do repositório foram lidos e nenhum serve:

| onde | o que faz | por que não serve |
|---|---|---|
| `egress_guard.redact_headers` | cabeçalho HTTP | não é PII, é segredo em header |
| `numero_pareado.mascarar` | `5547*****463` | 🔴 usa `*`, alfabeto de `_CARACTERE_DE_MASCARA` |
| `billing_collection._mascarar_documento` | `...1234` | privado da cobrança, e só sabe documento |
| `atlas/templater` | `{VALOR}` em texto | texto corrido, não dicionário tipado |

`pii_da_sessao` consolida **a decisão**, não o algoritmo: ele é o único lugar
que sabe que `titular_cpf` é documento e `eletrodomestico_opcao` não é PII.
Reusa o formato `...1234` que o Founder já aceitou, e é **fail-closed** —
campo desconhecido vira `{TEXTO:n}`.

### 🔴 E a conferência no banco pegou um vazamento MEU

Depois do backfill, medindo sem trazer um valor para a tela:

```
case_id CONTÉM o telefone do cliente ....... 12 de 12
comprimento do case_id ..................... 15, sempre
```

**O `case_id` deste produto é montado a partir do telefone do segurado.** Ele
tinha cara de identificador técnico e eu o declarei chave segura. ⚠️ **Um
`assert` sobre a lista de chaves não pegaria isso — só a conferência do DADO
pegou.** Corrigido, reescrito, e o VERIFY final:

```
gêmeo com o TELEFONE ..... 0      payload ainda tem CPF ......... 12/12
gêmeo com o CPF .......... 0      payload mascarado por engano ... 0
case_id em cauda ......... 12     corredor/serviço/fio .......... 12/12
```

**F1.4, os guardas ANTES do conserto:** 4 vermelhos de comportamento (*o CPF
atravessou inteiro · o telefone atravessou · o nome atravessou · o checkpoint
não grava o gêmeo*) e 6 verdes — que são os **controles**, e passam de
propósito: eles guardam contra mascarar DEMAIS.

---

## BLOCO A · O travamento deixa de sair como sucesso

A causa era **uma linha**: a reconciliação gravava `completed` fixo para as
quatro `FASES_ENCERRADAS`. `status_duravel_da_fase` **já** mapeava
`needs_human → waiting_input`. ⚠️ Tirar `needs_human` da lista seria o conserto
errado — ela tem três consumidores e o de `registrar_checkpoint` está CERTO.

### 📊 E a forma óbvia do filtro estava errada

```
sem filtro ......................................... 4 runs
.not_.like("error_code", "needs_human:%") .......... 0   🔴
.or_("error_code.is.null,error_code.not.like...") .. 2   ✅
```

`NOT (NULL LIKE ...)` é NULL, e NULL não passa. **A forma óbvia cega a varredura
exatamente para os órfãos que ela existe para achar — e não levanta erro
nenhum.** Só a medição contra o banco pegou.

**E a A.3 tinha uma metade que a SPEC não viu:** o `error_code` também nunca era
limpo ao CONCLUIR. Achado olhando as quatro linhas do banco.

**migration `20260824_02`**, aplicada. VERIFY, com a linha de controle:

```
cb6478f5  waiting_input · travado · SEM finished_at · 95% · resumo verdadeiro ✅
448d3f08  completed · error_code agora NULO · resto intacto                   ✅
373b8395  cancelled/human_phase   NÃO TOCADO                                  ✅
e5279497  completed/monitoring    NÃO TOCADO                                  ✅
```

---

## BLOCO B · As três cadeias, e a terceira é a única com prova

O caminho **C** (o Vigia) é o do `sentinela_stall` — um dos dois `needs_human`
duráveis da história. **E era o único que nunca falava com o segurado.**

- avisa o segurado, com o texto dependendo do desfecho do dossiê;
- 🔴 **UMA** implementação do marcador (`entregar_dossie_uma_vez`) para as duas
  cadeias — a §8 proíbe "um segundo marcador", e duas cópias da mesma regra é
  isso com outro nome;
- sem id de conversa, o aviso sai **sem** marcador — nunca
  `reivindicar_o_aviso(None)`, que gravaria `handoff_realerta:None`, uma chave
  **global** que calaria o handoff de TODAS as corretoras;
- `ausente` · `recusado` · `envio_falhou` são **três** estados, porque dão
  instruções opostas à corretora;
- o dossiê para de dizer *"ele JÁ foi avisado"* quando o envio estourou.

**CONTROLE:** os quatro alertas não-handoff do Vigia continuam saindo.

---

## BLOCO C · Primeiro exista o colega, depois se promete o colega

O aviso ao segurado **desceu para depois do dossiê**. ⚠️ A ordem não é estilo:
avisar primeiro obriga a escolher a frase antes de saber o que aconteceu, e a
única frase possível aí é a otimista.

A frase de FALHA passa por `afirma_transferencia` — o fiscal do caminho A —
**no gate**, que é onde um regex sobre constante serve para alguma coisa.

---

## BLOCO D · De uma família para as dezesseis

📊 A condição era `reason == "insurer_closed"`. Das 16 famílias, **uma** tinha
retomada. A regra que faltava é de negócio, e é uma frase:

> **Retomar só vale quando A CAUSA PODE TER MUDADO.**

| veredito | famílias |
|---|---|
| **retoma** | `insurer_closed` · `formulario_envio_falhou` |
| **direto ao humano** | `missing_slots` · `sem_chute` · `handoff_trigger` · `human_phase_guard` · `sentinela_stall` · `confirmacao_bloqueada` · `encaminhamento_sem_link` · `formulario_incompleto` · `formulario_nativo_desconhecido` |
| **não retoma** (falta conserto) | `conferencia_divergente` · `loop_guard` · `playbook_not_found` · `formulario_pronto_sem_flow_token` · `formulario_pronto_sem_transporte` |

🔴 **O padrão é `direto_ao_humano`.** Família nova sem veredito **quebra a
suíte** — o gate cobra o comando, não o texto.

⚠️ **E o BLOCO D NÃO é "ressuscitar depois das 6h".** Isso já foi julgado e
recusado, por escrito, em `reconciliar_acionamentos_orfaos`, com o incidente da
"sessão zumbi" de 12/07 atrás.

**O CONTROLE POSITIVO**, que o gate exige em letras maiúsculas: uma família
retomável retoma **uma** vez e não retoma duas; com protocolo capturado não
retoma nunca.

---

## BLOCOS E e F · A tela que destrava, e o `release` que parou de apagar

📊 O produto não tinha destravamento de acionamento: `dispatch_monitor.py` com
52 linhas e só GET, a página do admin em leitura pura, e **zero** eventos de
retomada em 26.803.

`POST /api/dashboard/acionamentos-travados` com **dois botões e não mais que
dois**. `assumir` é atômico (409 se outra pessoa chegou primeiro); `arquivar`
exige motivo escrito.

🔴 **A tela lê `output_redacted`, nunca `output_summary`** — e há guarda para
isso nos dois arquivos. É para isso que a FASE 1 criou a coluna.

**E.1, a armadilha:** a linha durável **SOMA** à fonte Redis. Substituir tiraria
da tela todo acionamento EM VOO e esvaziaria o dedup por telefone, fazendo as
conversas suprimidas voltarem duplicadas. Há controle para os dois.

**F.1, a escolha (b) — 90/100 contra 55/100:** `claimed_by` **já existe e já é
escrita** pelo `claim`. `HUMAN_REQUESTED + claimed_by NULL` = a IA pediu;
`+ claimed_by` = alguém assumiu. Zero migration, expand-first por natureza.

**F.2:** o select do Vigia nem pedia a coluna. Agora pede **e filtra**.

**E.4 / F.3 são o mesmo conserto:** o `release` devolvia sempre para `open`, e o
pedido sumia da Fila e do Vigia. Era o que tornava **mentira** a última
mensagem do Vigia — *"ela continua na Fila do painel, de lá ninguém a tira
sozinho"*. Agora, com handoff aberto, ele volta para a fila.

---

## BLOCO G · O ensaio, e a linha de controle

O roteiro roda **duas vezes** — entrando por `missing_slots` (caminho B) e por
`sentinela_stall` (caminho C). Sem a segunda, dá para fechar o ensaio verde
tendo pulado o B.0 inteiro.

🔴 **G.2, e é metade do arquivo:** a travessia do `e5279497` — o único
acionamento ponta a ponta da história — não pode produzir marca nenhuma. E há
o controle do controle: `decidir_travamento` **consegue** marcar, senão o
anterior passaria com o produto morto.

⚠️ **O que o ensaio NÃO prova, dito na cara:** o ensaio **live** contra o tenant
da AMANDUS, com linhas de verdade no banco, **não foi feito** — ele escreve, e a
trava é SELECT. Ele precisa do Founder. Os pontos que dependem de banco estão
provados por `test_acionamento_sobrevive`, com o dublê completo.

**G.4:** `test_handoff_chega_em_alguem` está **verde e fora da quarentena**.
📊 As duas asserções eram **vencidas**, não defeito de produto: uma procurava o
literal *"Não consegui abrir a transferência"* (hoje a constante
`FALHA_DO_HANDOFF`), a outra o rótulo *"Últimas mensagens"* (que a reescrita do
dossiê de 14/08 substituiu por `*CONVERSA*`).

---

## 🔴 Os defeitos que EU introduzi, e como cada um foi pego

Ficam registrados porque a SPEC pede separar fato de inferência — e porque um
relatório que só conta acertos ensina a confiar demais no próximo.

| defeito meu | como foi pego | onde está documentado |
|---|---|---|
| `case_id` declarado seguro, e ele carrega o telefone | **conferência do DADO**, não do código | `pii_da_sessao`, no comentário de `_CHAVES_SEGURAS` |
| o gêmeo dentro do `try` grande: um import falho derrubava o espelho durável inteiro | `test_acionamento_sobrevive` foi de 16 problemas para 2 | `dispatch_router`, antes de `redigido = ...` |
| a seam de envio nasceu **síncrona**, com `run_until_complete` dentro de um loop que já roda | revisão do meu próprio diff, antes de rodar | `entregar_dossie_uma_vez`, no docstring |
| `work_events` com três nomes de coluna errados, dentro de um `catch` mudo | conferência do schema | a rota, em `registrarEvento` |
| guardas estáticos lendo **comentário e docstring** — reprovaram consertos que existiam | os próprios guardas ficaram vermelhos | `_bloco` exige âncora ÚNICA; `_sem_comentario` tira docstring |
| a acusação de vazamento culpava **inocentes** | linha de controle: os três acusados passam sozinhos | meta-guarda, em "A PRIMEIRA VERSÃO DISTO ACUSAVA INOCENTE" |
| `monitoring != waiting_input` no meu próprio controle | o teste ficou vermelho e o motor estava certo | o ensaio, no `test_CONTROLE_o_acionamento_que_DEU_CERTO` |
