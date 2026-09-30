# SPEC-123 — O agente destrava: decide com nota, pergunta ao segurado, registra e aprende

> Proposta PRONTA · 30/09/2026 · escrita no chat que executou as SPECs 121 e 122, com as decisões do Founder de 30/09.
> Rito: **AAA v13**, 🔴 CRÍTICO (o modelo passa a responder à seguradora e ao segurado). Agentes: **Opus 5.5 sempre**, até 4 ao
> mesmo tempo, até 50 por sessão. **Nota alvo > 90.** Executar INTEIRA no mesmo chat, junto com a SPEC-124, e fechar.
> ⛔ Nada de SPEC nova no meio: o que não couber vira pendência.

## 0. POR QUE ESTA SPEC EXISTE — o pedido do Founder, nas palavras dele

> *"Quanto mais os agentes resolverem sozinhos, sem travar, sem errar e sem precisar de humano, mais valiosos seremos. Se em
> 100 atendimentos chamarmos um humano 60 vezes, temos um valor; se chamarmos 10 vezes, temos um valor muito maior."*
> *"Determinístico até travar. Travou: está autorizado a pensar, investigar, entender, analisar e fazer o que precisar para
> destravar e continuar sem humano. Se tiver acima de 70% de certeza, decide e continua. Registra a decisão para a gente
> avaliar e ensinar. Pode errar no começo — as corretoras estão avisadas; o que não pode é ficar parado, podando modelos que
> hoje são fantásticos."*

**O que a SPEC-122 fez de errado (lição, não repetir):** ela usou "zero erro grave nas armadilhas" como porta para ligar.
📊 Nenhuma variante passou → nenhuma autonomia → nada mudou para o segurado. **Esta SPEC troca a porta:** o modelo decide
quando a nota dele passa do limiar, e o limiar é CALIBRADO por medição (quanto ele acerta de verdade em cada faixa de nota).
Erro reversível é aceito e vai para o diário; só o IRREVERSÍVEL é proibido.

**O que já existe e é a base (não refazer — CLAUDE.md §5):**
- o cérebro da fase humana: `webhook.py` (~1099) → `insurer_dispatch_service.build_human_phase_messages` → rota `dispatch`
  → `guard_human_phase_reply` → `dispatch_router.py` (~4020–4207);
- `backend/app/services/acao_do_cerebro.py` (SPEC-122): parser estrito da ação, proibições em código, compositor da
  variante V2, sombra, tabela `cerebro_modos` (off | sombra; `on` hoje recusado por constraint);
- `perguntar_ao_segurado` (`dispatch_router.py`) + `sem_chute` perguntável (Porto, HDI, Yelum, Zurich);
- a bancada `backend/app/services/evals/bancada.py` (papel `cerebro`), corpus `backend/tests/corpus/bancada/cerebro/`
  (92 casos reais mascarados), relatório `docs/canon/reports/SPEC-122-BANCADA.md`;
- o Model Router (`llm_papeis`/`llm_pricing`, SPEC-116): o destravador é um PAPEL novo ou a rota `dispatch` — nunca env.

## 1. O EXECUTION CARD

```
OUTCOME ........  quando o roteiro fixo trava no WhatsApp da seguradora, o agente DESTRAVA sozinho: conduz, responde com
                  o dado do caso, deduz com nota ≥ limiar (com segunda opinião de outro provedor) ou PERGUNTA ao segurado
                  (em TODAS as seguradoras, com retomada se a URA fechar); só chama pessoa no irreversível ou sem saída.
                  Toda decisão autônoma vai a um DIÁRIO legível por gente, com "certo/errado" que realimenta a bancada.
                  📊 meta: das travas reais medidas no BLOCO 0, a maioria resolvida sem humano (número no gate G4)
RISCO ..........  9 (ALCANCE seguradora e segurado 3 · REVERSIBILIDADE resposta enviada 3 · FREQUÊNCIA todo acionamento 3)
SUPERFÍCIE .....  3 (cérebro, roteador, conferente, bancada, tabela nova do diário, tela do painel, papéis de modelo)
PISO APLICADO ..  §3.2 — o modelo responde à seguradora e ao segurado; migration que altera dado e estrutura → CRÍTICO
NÍVEL ..........  🔴 CRÍTICO · builders Opus 5.5 xhigh · juiz ‖ red team Opus 5.5 · 1 conserto · confirmação
O FIO ..........  §2
PARALELISMO ....  F0 (mapa, só leitura) → F1 (política + destravador, dono do cérebro) ‖ F4 (diário: tabela + tela, arquivos
                  disjuntos) → F2 (bancada e calibração; usa F1) → F3 (ligar + ida e volta; usa F1/F2) → F5 (costura e
                  miudezas) — builders em paralelo SÓ com arquivos disjuntos listados
UNIDADES .......  6 fatias (§5)
COESÃO .........  "decidir, perguntar e registrar são UMA política num lugar só"
TIME ...........  ~6 builders frescos · juiz ‖ red team · confirmação · 1 investigador (F0) · atualizador de documentos
REFERÊNCIA .....  interna: SPEC-122-BANCADA.md (92 casos), TELAS-QUE-FALTAM-2026-09-30.md, os 6 laudos da 122 ·
                  externa: §7
GATES ..........  §6
O ELO ..........  "o humano é chamado porque o harness proíbe decidir, não porque o modelo não saberia" — medir A (quantas
                  travas por motivo, F0), B (quantas o destravador acerta na bancada, F2) e B→A (a trava real vira decisão
                  certa pelo fio real, teste do fio)
FAIXA DE RELÓGIO  💭 1 dia de relógio
ORÇAMENTO ......  API do produto: OpenAI ≤ US$ 2,00 · Anthropic ≤ US$ 2,00 nesta SPEC (saldo informado pelo Founder em 30/09:
                  OpenAI US$ 6 com teto de gasto US$ 3 no total das SPECs 123+124; Anthropic US$ 2,86). Lido do ledger,
                  parando sozinho. Precisar de mais → avisar o Founder na caixa, nunca gastar além
```

## 2. O FIO
segurado pede → agente coleta (o que é previsível, antes) → corredor responde a URA (determinístico PRIMEIRO, nada muda no
que já funciona) → **trava** (tela sem passo, dado que falta, `sem_chute`, `NAO_SEI`, recusa do conferente, tela
desconhecida) → **destravador**: contexto inteiro (caso + conversa com o segurado + 20 últimas telas + mapa Atlas da URA +
rotas irmãs + memória da corretora) → **classe da decisão** (§3) + nota 0–100 + motivo → **política em código** (aplica
limiar, segunda opinião, proibições) → age (responde à URA / pergunta ao segurado / chama pessoa) → **linha no diário**
(com explicação para gente) → resultado anotado (protocolo saiu? seguradora recusou? humano corrigiu?) → "certo/errado" no
painel → vira caso de bancada e, se for regra, carta de conhecimento.

## 3. DECISÕES (do Founder, 30/09 — são lei)

| # | decisão | nota |
|---|---|---|
| D1 | **As 5 classes** da decisão do destravador, aplicadas EM CÓDIGO: **CONDUZIR** (navegar: "Continuar", "quer seguir?", voltar ao menu quando se perdeu) → livre · **RESPONDER COM DADO DO CASO** (placa, endereço, "Sim, está no local") → livre · **DEDUZIR** (escolher a opção que corresponde ao relato) → só com nota ≥ limiar E segunda opinião concordando · **PERGUNTAR AO SEGURADO** → quando só ele sabe · **NUNCA SOZINHO** → aceitar custo ou pagamento, abrir sinistro, cancelar pedido, inventar CPF/número/dado → pergunta ao segurado (custo) ou pessoa. A lista do "nunca sozinho" é CURTA de propósito: só o irreversível | Founder |
| D2 | **Limiar inicial 70** para DEDUZIR; a calibração (F2) pode SUBIR por faixa se o acerto medido na faixa ficar < 90%. Nunca baixar abaixo de 70 sem ordem do Founder | Founder 70 |
| D3 | **Segunda opinião de OUTRO provedor** nas decisões DEDUZIR (ex.: 6.1 decide, Opus/Sonnet confere; ou o inverso). Concordam → age. Discordam → pergunta ao segurado se o dado é dele; senão pessoa. A bancada mede quantas vezes discordam | Founder "conselho de LLMs diferentes" |
| D4 | **Modelo do destravador = o de melhor custo-benefício que não erre**, decidido pela bancada (F2) com os TRÊS no MESMO prompt: `gpt-6.1-sol`, `claude-opus-5-5`, `claude-sonnet-5-5`. Regra de empate: diferença ≤ 1 erro grave e ≤ 5 pontos de acerto → o mais barato é o principal, o de outro provedor é a segunda opinião E a reserva | 80 |
| D5 | **Ligado de verdade** por seguradora/ramo, começando pelas de mais volume, sem período de sombra. `cerebro_modos` ganha `on` (a constraint da 122 sai por migration). A **sombra fica só como ferramenta** para uma seguradora/rota onde a calibração ficou ruim (acerto < 80% na faixa do limiar) — decidido pelo número, não por medo | 85 |
| D6 | **Ida e volta com o segurado em TODAS as seguradoras**, inclusive Allianz e Alfa: pergunta, espera até ~2 min (📊 URA da Allianz encerra com mediana 254 s, p10 183 s); resposta a tempo → segue; URA fechou → **retomada**: reabre o acionamento e percorre o roteiro com os dados completos. 🔴 Trava: NUNCA duplicar pedido — se a seguradora disser que já existe solicitação aberta, segue com a existente. F0 confere nas conversas reais se cada seguradora aceita reabrir; a que não aceitar → pessoa, com o motivo escrito | 80 |
| D7 | **O diário é para GENTE ler** (ordem do Founder): cada linha diz em português simples o que a seguradora perguntou, o que o agente fez, por quê, com que certeza, e o que aconteceu depois — sem jargão, sem nome de variável. Botões **certo / errado** (+ campo "o certo era…") | Founder |
| D8 | **Também vale para a decisão do agente de atendimento de passar para uma pessoa** (conversa com o segurado): o F0 conta os motivos reais de handoff; os que o destravador resolve sem humano (dúvida simples, dado que dá para perguntar) entram na política; sinistro, condomínio, empresarial e rota sem corredor continuam indo a pessoa | 80 |
| D9 | **Rotas com conversa gravada que ainda não atendem sozinhas** (📊 `docs/canon/reports/TELAS-QUE-FALTAM-2026-09-30.md`): o destravador cobre as telas órfãs; e o F0 reinvestiga especialmente `yelum/auto/guincho` (📊 26+ conversas — o Founder quer PRONTA) e as da Allianz residência que terminam em "vou transferir para um especialista" (dá para completar com o que temos? se não, pendência de acionamento real). As 5 perguntas às atendentes (Regina/Saionara) podem NÃO chegar: executar sem elas, com o destravador deduzindo ou perguntando ao segurado | 85 |
| D10 | O que continua FORA: carro reserva (em espera com o Founder), condomínio e empresarial (com a atendente), conversar com consultora humana da seguradora | Founder |

## 4. O BLOCO 0 (investigador, só leitura, antes de codar)
1. **O mapa das travas**, com contagem real (📊 comando ao lado de cada número): em `observed_events`/`work_events`/
   `conversations`, de 01/08 até hoje, cada ponto em que o sistema chamou humano ou parou: no acionamento (`sem_chute`,
   `classe_da_tela`, gatilhos de handoff, `NAO_SEI`, duas recusas do conferente, tela desconhecida, URA fechou) e no
   atendimento (`human_handoff_reason` por motivo). Ordenar por frequência: é a fila de ataque.
2. Para cada classe de trava: é reversível? cabe em CONDUZIR / RESPONDER / DEDUZIR / PERGUNTAR / NUNCA?
3. Reabertura por seguradora (D6): em quais conversas reais a URA fechou e alguém reabriu, e o que aconteceu (duplicou?).
4. `yelum/auto/guincho` e Allianz residência (D9): por que não atendem sozinhas HOJE (simulador + régua), tela a tela.
5. Estado de `cerebro_modos`, da rota `dispatch` e do saldo das APIs (1 chamada mínima de cada modelo antes de gastar).

## 5. AS FATIAS

**F1 · A política e o destravador** (dono: `acao_do_cerebro.py`, `insurer_dispatch_service.py` na região do cérebro,
`dispatch_router.py` na região do cérebro/pergunta)
- Função única `decidir_destravamento(...)` com as 5 classes (D1), o limiar (D2), a segunda opinião (D3) e as proibições
  do NUNCA em código (a lista da 122 fica, enxugada ao irreversível). Saída estruturada validada; nada cru vai à URA.
- O prompt do destravador (evolução da V2 da 122) com o contexto completo do §2 e a instrução de dar nota 0–100 e motivo
  curto. Escrito para modelo inteligente: diz o objetivo, as proibições e o que está em jogo — sem microgerenciar.
- A classe "conduzir × decidir" já existe (SPEC-120: `rotulo_e_de_navegacao`, `constante_justificada`): reusar.

**F2 · A bancada honesta e a calibração** (dono: `evals/bancada.py`, `scripts/bancada.py`, corpus)
- Os TRÊS modelos no MESMO prompt do destravador, nas 92 telas da 122 + os cenários reais de trava do F0 (telas órfãs,
  `sem_chute`, telas que hoje vão a pessoa) — com gabarito humano quando existir.
- Mede por modelo: acerto, erro grave, **acerto por faixa de nota (70–80, 80–90, 90–100)**, concordância entre provedores,
  quanto destrava sem humano, latência, custo do ledger. Escolhe modelo (D4) e limiar por faixa (D2) pelo número.
- Rodadas iterativas ("vá soltando e vendo", ordem do Founder): rodada 1 → ajusta prompt/política → rodada 2, dentro do
  orçamento.

**F3 · Ligar de verdade e a ida e volta em todas** (dono: `dispatch_router.py` região da pergunta, migration de `cerebro_modos`)
- Migration: `cerebro_modos` aceita `on`; liga `on` nas seguradoras/ramos que a F2 aprovou; sombra só onde a calibração pediu.
- Ida e volta em todas (D6) com retomada sem duplicar; teste com a tela real "já existe solicitação" de cada seguradora.

**F4 · O diário de decisões** (arquivos disjuntos: migration nova da tabela, rota de API, tela do painel admin)
- Tabela por corretora (company_id + RLS + filtro no código + teste com duas corretoras), uma linha por decisão autônoma:
  quando, seguradora, rota, a tela (mascarada no log, completa na tela do painel para a corretora dona), a classe, a
  decisão, a nota, o motivo, a segunda opinião, o resultado. Tela no painel admin legível por gente (D7) com filtros e
  "certo/errado/o certo era…".
- "Errado" gera um caso novo no corpus da bancada (pendente de revisão) e, quando for regra, rascunho de carta de
  conhecimento (proposta, nunca publicada sozinha).

**F5 · Costura e miudezas** (gerente + builder)
- Teste de COSTURA: uma trava real atravessa F1 → F3 → F4 (decisão → envio → linha no diário → "errado" → caso novo).
- 🧹 Testes que se contaminam (P-121-28): UM conftest que fotografa `sys.modules` e atributos dos pacotes antes de cada
  arquivo de teste e devolve depois; a bateria tem de rodar UMA vez só.
- 🧹 Tirar dos arquivos ATUAIS o número de processo e o código de corretor (`corridor_playbooks.py` comentário,
  `tests/corpus/telas_reais/zurich-auto.jsonl`, `tests/fixtures/mapfre_parcelas.py`, `docs/canon/portais/PORTAL-mapfre.md`);
  NÃO reescrever o histórico (decisão do Founder).
- 🧹 Carta do portão (P-121-04): "Portão eletrônico não é eletricista (eletricista = curto, disjuntor, tomada, bocal). Raio
  ou queda de energia que danificou o motor = sinistro de danos elétricos → pessoa." — gravada pelo caminho governado de
  cartas (fonte: resposta da atendente de residencial, 29/09).
- O documento dos corredores regerado (LEIA-ME do painel) com a verdade de hoje.

## 6. OS GATES
```
G1  🔴 nenhuma rota que hoje ATENDE SOZINHO muda de resposta (simulador antes × depois; régua em worktree separado)
G2  🔴 NUNCA SOZINHO: 0 violação na bancada e mutação que tira a proibição do código → vermelho
G3  calibração: na faixa de nota escolhida para agir, acerto medido ≥ 90% (se não, o limiar sobe até valer — reportar
    quanto de cobertura se perde)
G4  📊 destrava sem humano: dos cenários reais de trava do F0 na bancada, % resolvidos certo sem humano — reportar o número
    e o antes (hoje ≈ 0%: tudo vai a pessoa)
G5  diário: toda decisão autônoma do teste do fio gera UMA linha legível; duas corretoras não se veem; "errado" vira caso
G6  ida e volta: resposta a tempo segue; URA fechada → retomada; "já existe solicitação" → NÃO duplica (tela real)
G7  custo real ≤ orçamento, do ledger
G8  bateria completa UMA vez, 0 falhas novas contra docs/canon/reports/BATERIA-LINHA-DE-BASE.txt (40)
G9  toda constante nova com constante_justificada (CLAUDE.md §9.5); nenhuma autoridade nova de modelo fora do catálogo
```
Cada gate novo com MUTAÇÃO que o deixa vermelho.

## 7. O QUE O ESTADO DA ARTE FAZ (§7.3)
- Começar simples, dar ferramentas claras, medir antes de soltar: https://www.anthropic.com/engineering/building-effective-agents
  — modelamos: o destravador é UMA chamada com contexto completo e saída estruturada, não um agente livre.
- Modelos sabem, em boa parte, quando sabem — mas a confiança precisa ser calibrada: https://arxiv.org/abs/2207.05221 —
  modelamos: nota por faixa MEDIDA; rejeitamos: usar a nota crua como verdade.
- Autoconsistência / segunda opinião reduz erro de raciocínio: https://arxiv.org/abs/2203.11171 — modelamos: a segunda
  opinião de outro provedor só no DEDUZIR; rejeitamos: votar em tudo (custo e latência).
- Comportamento novo atrás de chave, medido: https://martinfowler.com/bliki/DarkLaunching.html — modelamos: `cerebro_modos`
  por seguradora; rejeitamos: sombra como etapa obrigatória (D5).

## 8. O QUE A EXECUÇÃO NÃO PODE FAZER
- Não reabrir decisões do §3. Não criar SPEC nova. Não criar segundo motor/scheduler/runtime (CLAUDE.md §5).
- Não usar "zero erro grave" como porta de ligar: a porta é a calibração (G3) + o NUNCA (G2).
- Não gastar além do orçamento; não mandar mensagem real; testes reais são do Founder (caixa).
