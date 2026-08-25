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
