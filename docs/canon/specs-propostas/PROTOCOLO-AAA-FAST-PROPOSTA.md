# PROTOCOLO AUTOBROKERS AAA — v12 · AAA FAST (PROPOSTA)

> **Um escritor, um juiz, um relógio.** Proposta de 16/09/2026; substitui o laço da v11.2 §3.1–§5 e
> §10 quando o Founder aprovar (D-PROTO-01). O porquê e a medição estão em
> [`AUDITORIA-PROTOCOLO-AAA-2026-09-16.md`](AUDITORIA-PROTOCOLO-AAA-2026-09-16.md). Só regras aqui.
> **O que a v11.2 tem e NÃO está reescrito abaixo continua valendo:** §0.2 card · §0.3 o elo ·
> §0.4 a regra do comando · §2 o teste do produto · §3 as duas contas e o piso · §6 o juiz ·
> §7 a referência · §9 a licença de autonomia · §9.3 atividade não é progresso.

## 0. A REGRA DE UMA LINHA

> ## Quem escreve é um só. Quem julga não viu escrever. Quem estoura o relógio não chama mais ninguém.

## 1. 🔴 A SESSÃO — onde a execução mora

```
UMA SESSÃO NOVA POR SPEC (ou por FATIA), no Claude Code, modelo OPUS 5, contexto nascendo vazio.
⛔ NENHUM orquestrador acompanhando a execução. Quem executa é quem escreve.
   📊 o orquestrador Fable de 900 k–980 k de contexto custava ≈ metade de cada SPEC e não escrevia código.
O Fable é o co-líder: decide, audita, escreve protocolo — em OUTRO chat, antes e depois. Nunca turno a turno.
```

## 2. O NÍVEL — pela conta da v11.2 §3 (RISCO × SUPERFÍCIE, piso §3.2), e o ritual novo

| nível | executor | juiz fresco | lente do dado | red team | rodadas |
|---|---|---|---|---|---|
| **LEVE** (R 0–1 · S 0–1) | Opus 5 `medium`/`high` | nenhum (só provas mecânicas) | não | não | 0 |
| **PADRÃO** (R 2–5 ou S 2) | Opus 5 `high` | **Opus 5** | por gatilho §6 | não | 1 |
| **CRÍTICO** (R 6+ ou S 3 ou piso) | Opus 5 `xhigh` (`max` só se a unidade for de raciocínio: concorrência, algoritmo) | **Fable 5.1** | por gatilho §6 | só por gatilho §6 | 1 (+ confirmação curta por gatilho) |

```
🔴 o effort NÃO é alavanca de custo aqui. 📊 saída = ≈6 % do gasto; turno × contexto = o resto.
   Não se baixa effort para economizar. Baixa-se turno e contexto.
```

## 3. 🔴 O LAÇO — seis passos, uma volta

```
① CARD + BLOCO 0 MÍNIMO   ≤ 15 min · 5–10 premissas cuja falsidade mudaria o DESENHO, cada uma com o
                          comando ao lado (§0.4). Não se reaudita número que não muda decisão.
② BUILD                   UM escritor. Fatia por fatia; commit por fatia (arquivo por arquivo, nunca -A).
                          Guarda novo nasce VERMELHO antes do conserto e VERDE depois (linha de controle).
③ PROVA MECÂNICA          py_compile/tsc · guardas da superfície tocada · mutação dos guardas NOVOS, uma vez ·
                          `npm run test:rotas-montam` + `next start` + 1 requisição se mexeu em app/, middleware,
                          next.config ou env · VERIFY da migration contra o OBJETO. FAIL volta ao ②, nunca ao juiz.
④ JUIZ FRESCO             subagente READ-ONLY, contexto limpo. Recebe: o card · o contrato da SPEC · o diff ·
                          os comandos dos gates · a LISTA DE ATAQUES (§4). Nunca a narrativa do executor.
                          Devolve até 10 achados, cada um com o TESTE DO PRODUTO e a medição. Uma passada.
⑤ CONSERTO ÚNICO          o EXECUTOR conserta tudo junto e reroda SÓ os gates afetados. Achado não consertado
                          vira pendência escrita com o que destrava. Não entra outro builder.
⑥ ENTREGA                 suíte inteira UMA vez, em 2º plano, triada por DIFF contra a linha de base versionada ·
                          relatório ≤ 15 KB no template FAST · pendências/decisões/addenda numa passada, um commit ·
                          `git push origin HEAD:main` com a saída colada · telemetria do script (§7) colada.
                          Dossiê republicado FORA do caminho crítico.
```

### 3.1 Fatias
```
SPEC com ≥ 3 unidades ou > 40 KB roda em FATIAS INTERNAS, mesma SPEC, mesmo relatório, mesma branch.
fatia = ② → ③ → commit. O juiz roda UMA vez, sobre o diff acumulado, no fim.
contexto do executor passou de 300 k? fecha a fatia verde, commita, handoff ≤ 20 linhas no relatório,
próxima fatia em SESSÃO NOVA. ⛔ nunca "continuar" com 600 k de contexto.
```

## 4. O JUIZ — o que ele carrega, além da v11.2 §6

```
LISTA DE ATAQUES (obrigatória, em toda marcha com juiz):
  dado vazio / nulo · duas corretoras ao mesmo tempo (company_id) · a mesma mensagem duas vezes
  (idempotência) · dois processos ao mesmo tempo (concorrência) · rollback da migration · o produto
  CHAMA este caminho? (rode-o) · regressão direta do diff · efeito externo (mensagem, portal, dinheiro)
FORMA: VEREDITO · BLOCKERS (teste do produto + medição) · PENDÊNCIAS · EVIDÊNCIA · MAIOR LACUNA · NOTA
🔴 se estiver bom, diga que está bom. Reproduza 3 números por amostra (§0.4). Não reroda todas as mutações.
⛔ juiz retomado é proibido. Segunda rodada só pelo gatilho §6.
```

## 5. 🔴 OS TETOS — e como se aplicam durante a execução

| | LEVE | PADRÃO | CRÍTICO | fatia de CRÍTICO gigante |
|---|---|---|---|---|
| relógio | ≤ 40 min | ≤ 75 min | ≤ 2h30 | ≤ 1h15 |
| turnos do executor | ≤ 80 | ≤ 160 | ≤ 250 | ≤ 250 |
| contexto do executor | ≤ 200 k | ≤ 250 k | ≤ 300 k | ≤ 300 k |
| agentes além do executor | 0 | 1 | 2 (juiz + 1 investigador read-only Sonnet 5) | 2 |
| juiz: turnos · contexto | — | ≤ 60 · ≤ 200 k | ≤ 80 · ≤ 250 k | idem |
| entrada lida | ≤ 25 KB | ≤ 40 KB | ≤ 40 KB + apêndice sob demanda | idem |
| relatório | ≤ 8 KB | ≤ 12 KB | ≤ 15 KB | idem |

```
APLICAÇÃO (nada disto é frase de relatório):
  env     CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS=2 · CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=1   (.claude/settings.json)
  hook    PreToolUse[Agent]: conta chamadas na sessão; a 4ª é BLOQUEADA (exit 2, "teto de agentes do AAA FAST")
  hook    PreToolUse[Bash pytest]: filtra a saída para falhas (o exemplo oficial de code.claude.com/docs/en/costs)
  status  a status line mostra o contexto; o executor confere em CADA gate. Passou → §3.1
  relógio 1,5× a faixa do card sem blocker aberto → para de construir, entrega a fatia verde, registra o resto.
          ⛔ a resposta a "estourou" NUNCA é "mais um agente".
  medição AAA-FAST-medir-execucao.py sobre a sessão, 8 linhas coladas no relatório. Sem elas = SPEC aberta.
🔴 DELEGAÇÃO: não delegue o que termina em poucas chamadas; não delegue a verificação do próprio trabalho;
   investigador só para varredura grande e realmente paralela, READ-ONLY, Sonnet 5, um.
```

## 6. ESCALAÇÃO — só por gatilho escrito no card ou na caixa do Founder

| peça | entra quando (qualquer um) |
|---|---|
| **lente do dado** (Opus 5, read-only, reconstrói o outcome por SELECT sobre o acervo) | outcome é NÚMERO, DATASET ou relatório que a corretora lê · migration que ALTERA DADO · a SPEC afirma percentuais do acervo |
| **confirmação pós-conserto** (juiz novo, mesmo modelo, ≤ 20 turnos, só o diff do conserto) | o juiz achou ≥ 1 BLOCKER em código que ENVIA, filtra `company_id` ou grava por migration |
| **red team dedicado** (Fable 5.1, read-only) | autenticação/sessão · cross-tenant · dinheiro/cobrança real · ação irreversível a terceiro |
| **consulta ao Fable antes do BUILD** (≤ 15 turnos) | a SPEC deixa decisão de arquitetura em aberto (SUPERFÍCIE 3 real) |
| **segundo juiz** (família diferente) | o primeiro reprovou com ≥ 2 blockers materiais E a SPEC envia ou toca tenant |
| **AAA completo v11.2** (painel 3 lentes + red team + lente + confirmação) | incidente P0/P1 · mudança ampla de arquitetura · migration DESTRUTIVA · o Founder disse "é mais importante do que parece" · o juiz reprovou DUAS vezes com blocker material |

```
⛔ nunca entram, nem por gatilho: aquecimento de 16 perguntas · conversão da proposta · pesquisador externo
   (as referências vêm da proposta) · integrador (um escritor não precisa integrar) · builders paralelos.
```

## 7. A TELEMETRIA — oito linhas, coladas no relatório pelo script

```
relógio total · e por fase (①–⑥)          turnos e contexto de pico: executor, juiz, cada extra
tokens de contexto processados · saída     custo API-equivalente (US$) por agente e total
nº de agentes                              achados por mecanismo: executor · prova mecânica · juiz · lente ·
                                           canário — com a marca EXCLUSIVO em cada blocker
nota do executor (0–100, critério em 1 linha) · nota do juiz
```

## 8. ANTI-BLOAT — as regras que impedem a volta às 15 h

```
1. nenhuma peça entra no laço padrão sem blocker EXCLUSIVO medido em 2 SPECs, registrado em EVIDENCIAS
2. nenhuma rodada além da 1ª sem gatilho (📊 rodadas extras: +62 % de falsos positivos)
3. o card cabe em 12 linhas; se não cabe, é SPEC demais para uma fatia
4. quando uma regra errar duas vezes, muda-se o NÚMERO — e a mudança nunca acrescenta papel; troca um por outro
5. proposta ≤ 40 KB; o executor lê §0 + as unidades; o resto é apêndice sob demanda
6. mutação só nos guardas NOVOS, uma vez; a lista de falhas pré-existentes da suíte vive versionada
7. este documento cabe em 10 KB; o guarda `test_o_protocolo_tem_policia.py` mede o núcleo
```

## 9. QUEM DECIDE

**O executor, sozinho, sempre** (v11.2 §9: nota 0–100 às opções, escolhe a maior, registra, segue).
O Founder recebe a CAIXA no relatório. Se precisar ser chamado no meio, o protocolo falhou.
