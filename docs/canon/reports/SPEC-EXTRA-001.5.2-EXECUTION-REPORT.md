# SPEC-EXTRA-001.5.2 · O documento vira base sem virar erro — RELATÓRIO DE EXECUÇÃO

> 20/09/2026 · primeira SPEC sob o **núcleo do AAA v13 em teste** (O FIO · julgamento paralelo · trava de 2 rodadas).
> Base `68b9dca` → núcleo v13 `e43aff3` → entrega `44719b6`. Branch `feat/extra-001-5-2-o-documento-vira-base`.

## EXECUTION CARD
```
OUTCOME ..............  um documento de condições gerais entra e a proposta de base nasce SEM os 5 padrões de erro medidos,
                        com o veredito de um conferente ao lado de cada linha na fila do curador
RISCO ................  4   (corretora 2 · dado gravado 2 · raramente 0)
SUPERFÍCIE ...........  2   (vários comportamentos + uma peça nova: o conferente)
PISO APLICADO ........  nenhum: nada é enviado; publicar continua ato humano; migration só ACRESCENTA coluna anulável
NÍVEL ................  PADRÃO · builders Opus 5 xhigh · juiz generalista Fable 5.1 ‖ red team Fable 5.1
UNIDADES .............  7 (A–G) em 3 fatias: ① A+B+C+D+E extrator v2 ‖ ② F conferente (paralelas, arquivos disjuntos) → ③ costura do fio + G
COESÃO ...............  A–E moram no MESMO arquivo-hub (o extrator); F é peça nova com contrato fixo (`conferir_linha`)
PARALELISMO REAL .....  fatias ① e ② ao mesmo tempo (2 builders, arquivos disjuntos, sem commit); juiz ‖ red team; conserto em 2 frentes
TIME .................  gerente Fable · 2 builders Opus · juiz + red team Fable · confirmação MECÂNICA (desvio declarado em §6)
REFERÊNCIA ...........  interna: `tests/test_extracao_nao_publica_sem_gente.py` (o padrão de teste de fio que já existia) e o gabarito
                        do leitor `reports/SPEC-EXTRA-001.5-LINHAS-CONFERIDAS.json` · externa: a da proposta (§7.3 não se repesquisa)
GATES ................  A–G da proposta + teste do fio vermelho→verde + mutação + os ataques dos juízes reexecutados
O ELO ................  "a linha nasce conferida PORQUE o extrator chama o conferente": medido — o teste do fio afirma sobre a linha
                        GRAVADA e sobre o que `fila_de_curadoria()` DEVOLVE, não sobre a função solta
FAIXA DE RELÓGIO .....  150 min (proposta: 💭 3–4 h) · teto 1,5× = 225
```

## 1. O que está entregue (📊 medido em 20/09/2026)
| unidade | estado | a prova |
|---|---|---|
| A · âncora de planos | ✅ mecanismo · 🔴 recall real baixo | sem âncora o extrator **não propõe** (zero chamadas ao modelo). 📊 Nos 27 PDFs reais: âncora por texto em **4/27, 0 falsas** (rodada 1: 9/27 com ≥ 4 FALSAS — "ANUAL/BIANUAL/TRIANUAL", sumário, nível invertido) |
| B · escopo da cláusula | ✅ | regex de exclusão casa 📊 **785/785** linhas "riscos excluídos" do acervo (era 235: faltava o acento que o `fitz` devolve) |
| C · limite com coluna | ✅ em fixture real · ⚠️ tabela da HDI ilegível por texto | o conferente ABSTÉM em vez de chutar a coluna (P-E00152-03) |
| D · produto e versão da capa | ✅ com crivo positivo | lixo de capa (13/27 na rodada 1) cai no título do cadastro + alerta; os 2 alertas de versão medidos acendem, o controle não |
| E · cobertura ≠ assistência | ✅ sem mexer na resposta ao segurado | 📊 12 perguntas `e43aff3` × `HEAD` idênticas (guarda no teste do fio) |
| F · o conferente no cano | ✅ honesto · 🔴 abaixo da promessa **na máquina** → ✅ resolvido por LEITOR HUMANO-MODELO (§10) | toda linha nasce com parecer; chega à tela. 📊 GATE F **honesto 29/81 = 35,8 %** (48 ABSTENÇÕES; onde não abstém: 29/33 = 87,9 %) · precisão do selo **9/12 = 75 %**. Na 2ª parte o papel de conferente passou a um **segundo leitor Opus** que conferiu 📊 **477/477** linhas contra a página |
| G · a fila limpa | ◐ metade → ✅ **na 2ª parte** | 📊 (1ª parte) 39 `proposto`, **0 sem veredito**, 23 `publicado` intactas; as 40 CORRIGIR não reentraram pela v2 (§5). 📊 (2ª parte, §10) as 39 antigas foram para **rascunho com motivo escrito** e a fila ficou com **8 linhas** (táxi da Azul) |

**O teste do produto, dito sem enfeite:** o Founder **ainda não** publica sem abrir o PDF. O que mudou é que o sistema parou de
fabricar ("Plano único", âncora falsa, selo verde em erro) e passou a **dizer o que não sabe**. É pré-requisito; não é o outcome inteiro.

## 2. Migration — `20260920_01_extra00152_veredito_do_conferente.sql` (APLICADA)
APPLY: 4 colunas anuláveis em `insurer_assistance_services` (`veredito_do_conferente`, `conferencia` jsonb, `conferido_em`,
`caminho_da_clausula`) + CHECK dos 3 vereditos + índice parcial. VERIFY 📊: 4 colunas `is_nullable=YES` · 1 CHECK · 1 índice ·
23 publicadas intactas. ROLLBACK escrito no cabeçalho (derruba as 4). Expand-first, idempotente.

## 3. O julgamento — UMA rodada, paralela (trava T1: `rodada 1/2`)
| mecanismo | tempo | achados MATERIAIS | exclusivos |
|---|---|---|---|
| teste do fio + mutação (builders) | — | 11 asserções vermelhas na costura (o veredito não chegava à fila) | o fio incompleto, ANTES do juiz |
| ⚖️ juiz generalista Fable (58/100) | 📊 14 min · US$ 2,80 | 3 blockers | **os 80,2 % eram detecção do rótulo "Plano único"** (honesto ≈ 54 %) · capa-lixo em 13/27 |
| 🗡️ red team Fable (55/100) | 📊 13 min · US$ 3,15 | 4 blockers | **o conferente carimbava CONFERE com o limite de OUTRA coluna e o trecho de OUTRO plano** · linha certa perdida por `nivel_nao_contiguo` |
| os dois (duplicata útil) | | vidros de AUTO desviado para chave sem linha (regressão ao SEGURADO) · âncora falha no acervo real | — |

Causa-raiz comum: **fixtures escritas à mão rotuladas "acervo"** (CLAUDE.md §9.4). Conserto único em 2 frentes paralelas; agora
as fixtures são 7 páginas REAIS em `backend/tests/corpus/condicoes_gerais/` (sem PII; a gravação recusa CPF/telefone/placa).

## 4. Bateria — 1 rodada inteira, em 2º plano
📊 `python -m pytest tests -q`: **42 failed · 1130 passed · 34 xfailed · 48 errors** em 2.985 s (linha de base da 001.5.1: 37 · 48).
⚠️ Rodou ENQUANTO os builders consertavam (o extrator ficou ≈10 min sem importar) — as 5 de diferença (`rubrica` ×2,
`guardas_script[base_de_planos]`, `guardas_script[sem_corredor_de_vidro]`, `arvore_ficou_limpa`) foram retriadas dirigidas
com a árvore parada (📊 20/09, 919 s): `guardas_script[base_de_planos]` ✅ passa · `arvore_ficou_limpa` = os builders editando ·
`guardas_script[sem_corredor_de_vidro]` continua FAILED por `XPASS(strict) P-226` — 📊 **idêntico na base `68b9dca`** (medido em
worktree descartável): pré-existente, é um xfail vencido a triar, não desta SPEC · `rubrica` ×2 continuam falhando: o arquivo e a
régua não importam nada deste diff (`grep` vazio), mas ❓ **não foram medidas na base** (15 min por rodada) — registrado como
P-E00152-06. Lição para o v13: a bateria parte **depois** do conserto, não durante.

## 5. O que ficou fora, e por quê → `PENDENCIAS.md`
```
P-E00152-01 🧑🔴 A chave da Anthropic do PRODUTO está sem crédito (📊 400 "credit balance is too low"). Bloqueia: a âncora por MODELO
               (Bradesco Auto = 9 planos por código; HDI Auto), a reentrada das 40 CORRIGIR (§6 da proposta: ≥ 32 iguais) e
               QUALQUER extração nova. ⚠️ É a mesma chave do chat: provável causa do "Não consegui gerar a resposta" de 17/09.
P-E00152-02 🤖 recall da âncora por texto 4/27. Com crédito: medir o caminho do modelo nos 27 e nos 5 controles (GATE A real).
P-E00152-03 🤖 tabela lida célula a célula pelo `fitz` (HDI p.90): a coluna do limite morre na extração. Pede `page.find_tables()`.
P-E00152-04 🤖🧑 o conferente não olha `condicao` (4 linhas do gabarito; 1 dos 3 selos errados); os outros 2 selos errados exigem
               leitura humana (categoria de veículo × plano; pane mecânica × pane seca).
P-E00152-05 🤖 as 39 linhas antigas não têm `trecho` gravado → nunca terão selo (só a reextração, que depende de 01, resolve);
               e `processar_documento` só é alcançável por CLI (não há API nem rotina) — declarado pelo red team.
P-E00152-06 🤖 3 falhas da bateria a triar: o xfail vencido P-226 do vidro (idêntico na base) e a rubrica ×2 (não medida na base) — §4.
```

## 6. Desvios declarados
- **Confirmação:** o teto de 12 agentes da sessão (hook) estava no fim — esta sessão também fez a auditoria do protocolo. Em vez
  de um 3º juiz, a confirmação foi MECÂNICA: os scripts de ataque dos próprios juízes reexecutados pelo gerente (§7). Não contornei o hook.
- Builder 2 escreveu o módulo antes do teste (o teste não nasceu vermelho); a mutação provou que ele consegue ficar vermelho.
- Builder 1 caiu por falha de rede no meio do conserto e foi retomado com o contexto intacto.
- O gerente lançou a bateria com `-x` por engano (parou na 1ª falha da linha de base) e relançou.

## 7. Confirmação mecânica (📊 reexecutado pelo gerente sobre `44719b6`)
```
test_o_documento_vira_base_sem_virar_erro   70 verdes · 0 vermelhas      test_extracao_nao_publica_sem_gente   40 · 0
test_o_conferente_concorda_com_o_leitor     47 verdes · 0 vermelhas      test_a_base_de_planos_nao_tem_dono    16 · 0
vidros2.py (red team B1)   ONTEM(e43aff3) == HOJE(HEAD) nas 12 linhas: servico=vidros · condicionado · origem=base
conf.py    (red team B2)   ERRO 1 → NAO_CONSEGUI · ERRO 2 → DIVERGE (plano) · ERRO 3 → NAO_CONSEGUI   (antes: CONFERE ×3)
acento.py                  o regex casa 785 de 785 (antes 235)
ancora.py / GATE A         4/27 com âncora · 0 falsas (antes ≥ 4 falsas)
```

## 8. Telemetria (`medir_execucao_claude_code.py --sessao atual`, só a parte da SPEC)
```
relógio            📊 ≈ 110 min do card ao conserto commitado (faixa 150) + fechamento
agentes            4 (2 builders Opus · juiz + red team Fable) · rodadas de julgamento: 1 · bateria: 1 rodada inteira
builder 1          135 turnos · pico 314 k · 28,3 M · US$ 16,90        builder 2   91 turnos · pico 238 k · 15,1 M · US$ 10,43
juiz               29 turnos · 14 min · US$ 2,80                        red team    35 turnos · 13 min · US$ 3,15
total da SPEC      📊 ≈ US$ 33 de agentes + a fração do gerente — contra a média medida de US$ 146 por SPEC (19 SPECs)
achados            fio (builders) 1 · juiz 3 (2 exclusivos) · red team 4 (2 exclusivos) · canário: —
```
**Nota da execução (estado final): 90/100** — critério: o outcome de negócio foi alcançado por outro caminho (§10) — a base saiu de
23 para 📊 **492 serviços publicados em 108 planos e 8 seguradoras**, cada linha com trecho literal conferido por máquina e por um
segundo leitor, e a Skill responde em 12 casos reais. Perde pontos porque o extrator AUTOMÁTICO continua com recall 4/27 e sem
crédito, 8 linhas ficaram retidas e o casamento do nome do plano com a apólice real ainda não foi medido (P-E00152-07).
**1ª parte: 84** — critério: tudo o que foi entregue está provado no acervo real e nada fabrica; perdeu pontos porque
o outcome inteiro da proposta (publicar sem abrir o PDF; as 40 reentrando) não foi alcançado — metade por falta de crédito na API.
Notas dos juízes na rodada única (antes do conserto): 58 e 55. Nenhum motor paralelo foi criado (o conferente estende `verificar`;
um leitor de PDF; um escritor do parecer).

## 9. Caixa do Founder
1. **Recarregar o crédito da chave Anthropic do produto** (console.anthropic.com → Billing). Bloqueia extração nova E provavelmente o chat.
2. Clicar **Implantar** no EasyPanel depois do push (a tela da fila ganha o selo do conferente). Nada a rodar no console.
3. Abrir a Fila de Curadoria: 37 linhas dizem "a página não confirma" com o campo que não bate; 35 delas por "Plano único".

## 10. SEGUNDA PARTE (20/09) — a base escrita por leitores do plano, sem API

**O rumo mudou, e por quê.** A 1ª parte parou num muro: o extrator do produto chama a API da Anthropic por conta própria, e a chave
está sem crédito. O Founder decidiu **não pôr crédito** e usar os **agentes do plano** para ler as condições gerais e escrever os
planos, publicando o que fosse conferido, com ele como revisor (D-E00152-01). Nenhuma chamada de API de modelo, nenhum motor paralelo.

**O método — 3 peneiras.** ① **escritor** Opus lê as páginas (📊 51 documentos, 13 milhões de caracteres, extraídos pelo MESMO
leitor do produto) e escreve plano, serviço, coberto, limite, condição, **página** e **trecho literal**; ② **máquina**: o carregador
`backend/scripts/carregar_destilacao_de_planos.py` só aceita a linha cujo trecho **existe literalmente** na página citada
(📊 477/477 passaram); ③ **segundo leitor** Opus, que não escreveu, confere TODAS as linhas; o escritor corrige e o leitor reconfere
só o que mudou. Publicação por `BASE.publicar_servico`, com revisor. 📊 4 escritores + 4 leitores, ≈ 2h20.

**O funil (📊):** 454 linhas na 1ª escrita → o leitor 2 aprovou **385** e apontou **69** → correção e faltantes → **477** no estado
final → **469 publicadas**, **8 retidas**, **0 descartadas** pela máquina. 14 bateram na chave única de nível e foram recarregadas
no próximo nível livre; 39 propostas do extrator v1 ("Plano único") foram para **rascunho** com o motivo escrito.

**A base hoje (📊 SELECT, 20/09): 492 serviços em 108 planos, 8 seguradoras, 20 pares seguradora × ramo** (antes: 23 serviços; Zurich, Alfa e outras não têm documento no acervo).

| seguradora | auto | condomínio | residencial | falta |
|---|---|---|---|---|
| allianz | 3 planos / 30 serv. | 1 / 3 | 3 / 15 | 🔴 Moto, Caminhão e Frota não destilados |
| azul | 10 / 67 (8 na fila) | — | — | ⚠️ táxi: limite fora do município |
| bradesco | 19 / 70 | 1 / 1 | 7 / 11 | ⚠️ condomínio não tem assistência 24h nos documentos |
| hdi | 7 / 39 | — | 5 / 20 | — |
| mapfre | 1 / 1 | 1 / 1 | 1 / 4 | 🔴 falta o manual da Assistência 24h do auto |
| porto | 4 / 20 | 4 / 12 | 8 / 32 | — |
| tokio | 2 / 19 | 2 / 9 | 7 / 30 | — |
| yelum | 15 / 78 | — | 7 / 30 | — |

**O que o segundo leitor pegou ANTES de publicar:** chaveiro de MOTO do Bradesco (a cláusula EXCLUI cópia de chave e a tabela
prometia R$ 400) · vidraceiro de assistência gravado como **cobertura** de vidros (24 linhas, 6 seguradoras) · carro reserva da
Yelum dado como "à parte" quando está na tabela (p.149) · guincho por PANE com km MENOR que por sinistro (Yelum, Tokio) · Azul
Livre Escolha sem dizer que é **reembolso com teto** (p.164) · Bradesco 2015 × 2023 · bloco RESIDENCIAL no manual de AUTO do
Bradesco · "planos" que eram só rótulo de seção.

**Ponta a ponta (📊 a Skill `responder_cobertura` contra a base real, 12 casos):** Tokio VIP chaveiro → R$ 200/evento · Yelum
SUPERIOR carro reserva → 10 diárias, ESSENCIAL → não coberto · Yelum BÁSICO guincho → as duas hipóteses (sinistro 300 km, pane
menor) · HDI VIP → sem limite em sinistro · Bradesco nº 43 → 200 km · Porto Conforto encanador → R$ 150, Veraneio Conforto
vidraceiro → não coberto · Allianz Essencial hospedagem → não coberto · Azul 37N → 500 km, reembolso com teto · Mapfre auto →
**"ainda não sei"** (correto). "vidraceiro" foi acrescentado ao vocabulário como sinônimo de vidros.

**O que continua faltando.** O teste passa o NOME EXATO do plano; em produção quem casa o nome é `identificar_plano`, lendo a
apólice — e isso **só o canário do Founder mede** (P-E00152-07). Seguem abertas: as 8 linhas de táxi da Azul (08), Mapfre/Allianz
sem documento (09), os níveis sem escada no documento (10), a assistência adicional em HDI/Yelum (11) e a decisão sobre aposentar
o extrator automático (12).
