# Relatório de execução — SPEC-130-B: a ficha única da apólice

**SPEC:** `docs/canon/specs/SPEC-130-B-a-ficha-unica-da-apolice.md` · proposta `specs-propostas/SPEC-130-B-A-FICHA-UNICA-DA-APOLICE.md`
**Branch:** `spec/130-B-a-ficha-unica` · **base** `4bfd562` (= `origin/main`, 0 atrás, 0 pendente) · **final** ver §7 (push)
**Gerente:** Opus 5.5 · protocolo AAA v13.2 · nível CRÍTICO

## 0.0 EXECUTION CARD
```
OUTCOME ........ a apólice LIDA INTEIRA de qualquer seguradora, com "conferida (a soma bate com o prêmio)" ou "não conferida";
                 o PDF do segurado nunca mais cru ao modelo; toda leitura registrada
RISCO .......... 8 (alcance 3 · reversibilidade 3 · frequência 2)
SUPERFÍCIE ..... 2 (vários comportamentos, lugares listados)
NÍVEL .......... CRÍTICO · builders Opus 5.5 xhigh · juiz Opus 5.5 ‖ red team Opus 5.5
PISO ........... CRÍTICO: PII a modelo · migration de dado (llm_papeis) · resposta ao segurado
UNIDADES ....... U1 fio · U2 texto tolerante + registro · U3 cascata · U4 fontes · U5 renovação · U6 bancada
COESÃO ......... cascata + juiz + máscara + registro + campos novos da ficha = um contrato → F1 inteira
PARALELISMO .... 4 builders simultâneos (F1 motor ‖ F2 fontes ‖ F3 anexos ‖ F4 renovação), arquivos disjuntos, contrato no §4
                 da SPEC; F5 costura + bancada em série
TIME ........... 5 builders · juiz ‖ red team (cegos) · 1 builder de conserto · confirmação · atualizador de documentos
REFERÊNCIA ..... `reconciliar` / `_contador_de_premio` e as 11 apólices que fechavam (o juiz abriu e reproduziu); externa: §8 da SPEC
GATES .......... testes da SPEC · 3 mutações do §6 · régua das 32 · migration pelo VERIFY · bateria
O ELO .......... "a ficha fecha" medido pelo CÓDIGO DO PRODUTO sobre os BYTES REAIS e conferido pelo `/documento` (caminho
                 independente); o juiz recalculou a tolerância à mão sobre o JSON (0 divergência)
FAIXA DE RELÓGIO  declarada 💭 4h30–6h · real ≈ 7h de relógio (19:33 → ~02:30), estourada pela lentidão da máquina (import ~60 s,
                 bateria > 2 h) e por uma volta de confirmação com blocker
```
① painel: não (CRÍTICO pede juiz ‖ red team + lente por gatilho; a lente de PII foi exercida pelo red team, item 2) · ② auditoria
externa: juiz e red team frescos + confirmação · ③ pendência por valor marginal: P-130B-03 (variação do modelo), P-130B-10.

## 1. Resumo executivo (FATO)
- 📊 **A régua** (código do produto sobre os bytes reais das 32 apólices de 11/10; `scripts/regua_ficha_da_apolice.py`;
  `tests/corpus/bancada/RESULTADOS/ficha_da_apolice_20261012.json` + `_20261012_confirmacao.json`): **antes 11/32 → 24/28 com PDF**
  (RESI 7/7 · COND 6/8 · EMPR 5/7 · AUTO 6/6); as **11 de controle intactas, todas pelo regex, custo 0**; **0 pipeline caído**
  (Sura e Yelum leem pela reserva PyMuPDF); o PDF **escaneado** da Porto lido pela visão (16 páginas, ao centavo); 4/32 sem PDF.
  ⚠️ Meta de COND (≥ 7) **não batida**: 6/8 — a tabela da Tokio vem quebrada pelo PyPDF2 e o juiz por linha recusa (P-130B-01).
- O leitor é UM, dentro do serviço que existia (nenhum motor paralelo): regex → juiz do prêmio → modelo (papel novo
  `leitura_de_apolice`, texto mascarado, trecho literal de uma linha com rótulo e prêmio conferidos) → juiz → visão (só página sem
  texto, sem limite) → juiz. Leitura guardada por hash + `LEITOR_VERSAO=130B.2`; modelo com orçamento de 20 s e 2º plano com trava.
- Fontes: `/documento_anexos` (📊 +1/32), o prêmio do CORP ao juiz, `/itens?data=`. Anexo do WhatsApp/chat pelo mesmo leitor.
- 📊 Custo de modelo da SPEC inteira: **US$ 0,0983** (79 chamadas, `token_usage_logs service_type='bancada_130b'`).

## 2. Escopo por fatia (FATO — commits arquivo a arquivo)
| fatia | o que entregou | testes |
|---|---|---|
| F1 o motor | páginas tolerantes · cascata · juiz `fecha_o_premio` · máscara · 2º plano com trava Redis · leitura guardada · docling fora do laço · teto por tipo · `ApoliceDocumental`+3 campos · sinal `documento_nao_conferido` · migration + snapshot | `test_spec130b_o_motor.py` 20 · `o_fio.py` |
| F2 as fontes | `/documento_anexos` · `premio_liquido_esperado` · `/itens?data=` · a porta lê a leitura · bloco `documento` na tool · marca "não conferida" no atendimento | `fontes_do_corp.py` 38 |
| F3 os anexos | `vision_service.conteudo_do_anexo` → `ler_anexo_de_seguro` → `ficha_para_o_modelo`; segurado: só a ficha; corretor: ficha + texto mascarado | `anexos.py` 17 |
| F4 a renovação | `de_apolice` para AUTO e RE pela ficha; lista do que falta; nunca inventa | `renovacao_le_a_ficha.py` 16 |
| F5 costura + régua | recorder grava o bloco `documento` (P-LEITOR-04) · ficha com 0 linhas acende o sinal · `/itens` do veículo com data · nome do arquivo mascarado · régua · capacidade SUPORTADA · 2 consertos do motor medidos (prêmio colado na Tokio; PyMuPDF `sort=True` na Sura) | `costura.py` 19 |
| conserto único | B1 juiz por linha · B2 erro passageiro não final · B3 sinistro/BO/orçamento ≠ apólice · B4 sem falsa promessa · J1 J2 J3 J5 J6 P2 P4 P7 | `conserto.py` 40 (38 vermelhos no código antigo) |
| confirmação | o rótulo da linha de baixo tem de estar no do modelo · visão nunca traz limite | `confirmacao.py` 5 |

## 3. Arquivos alterados
📊 `git diff --stat 4bfd562..HEAD -- backend/app` → 14 arquivos, +2.974/−162. Produto: `services/policy_document_evidence_service.py`,
`services/document_service.py`, `providers/policy_data_provider.py`, `providers/infocap_policy_provider.py`, `api/infocap_connector.py`,
`agents/tools/infocap_tool.py`, `agents/nodes.py` (só `_sem_objeto_do_risco`), `api/webhook.py` (só o ramo de documento), `api/chat.py`,
`services/vision_service.py`, `services/multicalculo/pedido.py`, `services/multicalculo/config.py` (docstring),
`services/skills/invocation_recorder.py`, `factories/modelos_snapshot.json`. Novos: a migration, `scripts/regua_ficha_da_apolice.py`,
8 arquivos `tests/test_spec130b_*.py`, 3 resultados da régua. `frontend/` e `portal_worker/` não mudaram.

## 4. Migrations
`20261011_05_spec130b_papel_leitura_de_apolice.sql` — INSERT de 1 rota em `llm_papeis` (`on conflict do nothing` + asserção).
APPLY/VERIFY/ROLLBACK escritos no arquivo ANTES. 📊 antes: `count(*) where papel='leitura_de_apolice'` = 0 → APLICADA 11/10 pelo MCP →
VERIFY 1 (a linha: luna medium / sonnet-5-5 medium / pii / alto / v1) ✅ · VERIFY 2 (a trava recusa Luna `low`, aceita `medium`, sobra 0)
✅ · VERIFY 3 (`gerar_snapshot_de_modelos.py --banco --conferir` → em dia; `resolver('leitura_de_apolice')` → gpt-6-luna medium pii /
claude-sonnet-5-5 medium) ✅. ROLLBACK: `delete from llm_papeis where papel='leitura_de_apolice'` (o código cai para "não fechou").

## 5. Testes
- 📊 SPEC + regressão dirigida, depois do conserto: **424 passed em 581 s** (builder do conserto) · depois da confirmação:
  `test_spec130b_conserto.py` + `confirmacao.py` **45 passed** (gerente) · `conserto`+`o_motor`+`costura`+`o_fio`+`confirmacao`:
  84 passed + 1 verdade vencida atualizada (§9.3).
- Mutações: as 3 do §6 da SPEC (PyMuPDF no caminho do regex · juiz sempre fecha · sem máscara) **VERMELHAS**; F2 8/8, F3 3/3,
  F4 2/2, F5 12/12, conserto 26/26, confirmação 2/2 vermelhas (o controle continua verde).
- Bateria: ver o bloco 📊 A BATERIA no fim.

## 6. Canário e rollout
Nada liga sozinho no ar até o Founder clicar Implantar no `smith-api` e no `smith-worker`. Depois disso a cascata vale para toda
consulta de apólice (o modelo só nas que o regex não fecha). Desligar o modelo e a visão: `LEITOR_APOLICE_MODELO=0` no `smith-api`.
Canário de produção (a primeira leitura real) não rodou: depende do Implantar (T-154). Amandus → Resulta → AutoFleet: a régua mediu
as duas carteiras reais por API, sem gravar nada.

## 7. Gate da SPEC
Juiz **84** (1 blocker) ‖ red team **58** QUEBREI (4 blockers) → conserto único → confirmação **80** (1 defeito novo + 1 lacuna,
consertados pelo gerente com teste e mutação; régua das 7 afetadas idêntica). Bateria: 0 regressão em aberto (ver o bloco da bateria). **Push: `git push origin HEAD:main` → `4bfd562..9e58675  HEAD -> main`, 0 pendente.**
**Nota do executor: 87/100** — o outcome foi medido nos bytes reais (24/28, 11 intactas) e 6 blockers fechados com prova; abaixo de 90
pela meta de COND não batida (6/8), pela leitura real em produção ainda não provada (falta Implantar) e pela variação do modelo.

## 8. Mudanças além do texto da SPEC (CHANGE-ADDENDA)
A mudança de escopo da 130-B foi ACEITA pelo Founder (11/10). Entraram pela confirmação/conserto: `nodes.py` (`_sem_objeto_do_risco`),
`invocation_recorder.py`, `multicalculo/config.py` (docstring). Fora: P-130B-01…14.

## 9. Decisões
D-130B-01…17 em `FOUNDER-DECISIONS.md` (as do conserto: D-130B-13 rótulo embrulhado em 2 linhas com o rótulo de baixo no do modelo ·
14 nascimento mascarado pelo rótulo · 15 linha que não fecha não passa por cima do cadastro · 16 versão 130B.2 · 17 SUPORTADA).
Nesta rodada também: D-1311-02 a fila TOMADA pelo Founder (cobrança no fim); senhas Allianz/Mapfre gravadas no cofre (T-146).

## 10. Riscos remanescentes
- **INFERÊNCIA:** a taxa de 24/28 é de UMA amostra (32, semente 1311); o modelo varia entre rodadas (P-130B-03).
- A visão confere só a soma (sem limite agora; P-130B-09). · Sem Redis não há 2º plano (P-130B-06; produção tem Redis).
- O anexo do WhatsApp pode atrasar a resposta até 40 s (+20) (P-130B-04).
- Limite inteiro sem separador e sem `R$` (ex.: `LMI 15000000`) é mascarado como número e fica "indisponível" (não errado) — pendência
  da confirmação, registrar.

## 11. Impacto para o corretor
O chat e o atendimento passam a ler as coberturas de Tokio, Allianz empresarial, Sura, Yelum, HDI auto e PDFs escaneados, e dizem
quando a leitura NÃO bateu com o prêmio ("não afirme que a lista está completa"). O PDF que o segurado manda vira uma ficha.

## 12. Estado do Master Plan
130-B ✅ → próxima: **131 renovação** (liga `de_apolice(…, ficha=, config=)` e a pré-leitura das renovações do mês, P-130B-11).

## 13. ROLLBACK da SPEC inteira
`git revert` dos commits `8beabf9..<final>` + o ROLLBACK da migration. Nenhum dado de cliente foi escrito (só a rota do modelo
e, ao Implantar, `documents.metadata` e a ficha no MinIO, que o código antigo ignora). Desligamento sem revert: `LEITOR_APOLICE_MODELO=0`.

## 📊 A BATERIA — quantas vezes ela rodou nesta SPEC
UMA rodada válida, depois do conserto, worktree limpo `C:/wt130b` em `4296e48`, em duas metades pela pasta `tests` (o
`collect_ignore` só vale assim — a 1ª tentativa, com os arquivos um a um, morreu na coleta: `SystemExit` de um guarda-script):
```
m1: 15 failed · 1489 passed · 2 skipped (44 min)      m2: 22 failed · 4769 passed · 7 skipped · 31 xfailed (51 min)
TRIAGEM NOMINAL contra BATERIA-LINHA-DE-BASE.txt: m1 15/15 na base · m2 19/22 na base · 3 novas:
  test_spec116_reserva_p0::test_o_resolver_devolve_a_reserva_do_mapa → REGRESSÃO desta SPEC (o papel novo com reserva fora do
     mapa do guarda) → o papel entrou no mapa com o precedente da 133-A → verde
  test_spec129c_conserto_app::test_basica_renovada_aplica_o_reajuste_do_ramo → REGRESSÃO (a docstring reescrita perdeu
     "chamada pela 131") → frase devolvida → verde (66 passed com renovacao_le_a_ficha)
  test_spec1310_f1_migration::test_o_comportamento_contra_o_codigo_roda_no_node → CARGA: isolado, 1 passed em 6 s
→ 0 regressões em aberto. A lista da linha de base não muda.
```

## §11 A TELEMETRIA (`python backend/scripts/medir_execucao_claude_code.py --sessao atual`, 12/10 ~04:00 UTC)
```
relógio .......... executor 332 min até a medição (19:12 → ~00:45 BRT; a bateria corre depois) · fases: BLOCO 0 + SPEC ~40 min ·
                   F1‖F2‖F3‖F4 80–194 min (paralelo) · F5 61 min · juiz ‖ red team 22/21 min · conserto 108 min · confirmação 7 min
turnos / pico .... executor 147 / 485k · F1 96/322k · F2 110/291k · F3 97/225k · F4 65/238k · F5 146/358k · juiz 64/252k ·
                   red team 62/277k · conserto 102/409k · confirmação 18/124k · atualizador 46/165k
tokens ........... contexto 213,3 M (agentes) + 50,3 M (executor) · saída 0,21 M + 141 k
US$ API-equiv. ... executor 33,10 · agentes 131,97 · TOTAL ≈ US$ 165 (+ US$ 0,0983 de modelo do PRODUTO na régua)
agentes .......... 10 além do executor
achados .......... executor/BLOCO 0: latência 123 s → 2º plano; o mascarador do canal apaga dinheiro · prova mecânica (régua F5):
                   prêmio colado na Tokio, coluna a coluna na Sura · juiz: B1 (EXCLUSIVO? não — o red team também) · red team: B2, B3,
                   B4 (EXCLUSIVOS) · confirmação: rótulo de outra linha na regra das 2 linhas + limite da visão (EXCLUSIVOS)
bateria .......... 1 rodada válida em 2 metades (a 1ª tentativa morreu na coleta: arquivos passados um a um furam o collect_ignore)
nota ............. executor 87 (outcome medido em bytes reais; COND abaixo da meta; produção ainda não provada) · juiz 84 · red team 58 ·
                   confirmação 80
```

**Declaração:** nenhum motor paralelo foi criado (o leitor é o `policy_document_evidence_service` de antes; o modelo pelo Model Router;
o arquivo pelo `DocumentService`/MinIO). Nenhuma mensagem enviada; nenhum portal; InfoCap só GET.
