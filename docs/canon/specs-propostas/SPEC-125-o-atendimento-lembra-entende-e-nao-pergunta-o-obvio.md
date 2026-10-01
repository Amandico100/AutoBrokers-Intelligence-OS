# SPEC-125 — O atendimento lembra, entende e não pergunta o óbvio

> Proposta PRONTA · 01/10/2026 · escrita a partir da ordem do Founder de 01/10 e dos laudos `INV-ATENDIMENTO` (25 travas
> T1–T25, memória M1–M8, cenários C1–C16) e `INV-IDEIAS` (ideias 1 e 2). Branch `spec/125-o-atendimento-lembra-e-pensa`.
> Rito: **AAA v13 · O FIO**, 🔴 CRÍTICO. Agentes: **Opus 5.5 sempre**, sem teto de simultâneos (D-PROTO-17). **Nota exigida
> > 90**, juízes críticos. Executar INTEIRA no mesmo chat e fechar. ⛔ Nada de SPEC nova no meio: o que não couber vira pendência.

## 0. POR QUE ESTA SPEC EXISTE — o pedido do Founder, resumido

O agente de ATENDIMENTO (fala com o segurado no WhatsApp; papel `atendimento` = `gpt-6.1-sol` high, reserva Opus 5.5) foi
desenhado na era dos modelos fracos, com a política "erro zero; qualquer dúvida → humano". **Essa era acabou.** O Founder quer:

- **confiar no modelo**, deixá-lo PENSAR e DEDUZIR o óbvio (💭 "derrapei na chuva" → a pista estava molhada; não se pergunta);
- **nunca** repetir pergunta respondida, nem perguntar o que está na apólice ou já foi dito — nesta conversa **ou** em conversa
  anterior do mesmo telefone na mesma corretora;
- **lembrar da conversa INTEIRA** até o atendimento ser resolvido — *"lembrar de 3 ou 5 trocas é um absurdo"*: se houver 100
  mensagens, as 100 ficam disponíveis, também para o destravador;
- chamar a pessoa da corretora **só no grave** (sinistro, risco à vida, condomínio/empresarial, serviço sem corredor, pedido de pessoa);
- **rajada** (5 frases, ou 8 imagens + 1 explicação) → **UMA** resposta inteligente, nunca 5 encavaladas;
- identificar pelo **telefone** (mesma corretora): chamar pelo nome, aproveitar o CPF que já está na conversa (só confirmar);
- pode **reescrever** o prompt, simplificar, apagar o obsoleto — **nunca cortar o importante**; tudo tem de ficar MELHOR que hoje,
  e tem de haver como **DESFAZER** sem deploy. Custo menor é bônus.

**O que o laudo mediu e esta SPEC ataca (FATO, `INV-ATENDIMENTO` §0):**
- 📊 o agente vê **15 mensagens** (`AGENT_CONTEXT_WINDOW_SIZE = 15`, `backend/app/core/constants.py:38`; corte em
  `backend/app/agents/nodes.py:1700-1711`), e o `SystemMessage` que o grafo empurra a cada turno (`graph.py:1744` +
  `state.py:17`) ocupa vaga → **3 a 5 trocas** (prova: `add_messages` em 3 turnos → `['system','human','ai','system',…]`);
- 📊 as 60 mensagens que `langchain_service.py:414-431` busca **nunca chegam ao modelo**; as falas da atendente humana são
  invisíveis (`grep update_state app/` = 0);
- 📊 o fiscal `honestidade_do_handoff.py:118,133-189` transforma *"Pronto, acionei o guincho"* em *"Registrei seu pedido de
  atendimento humano…"* — frase **falsa** dita depois de um acionamento **real** (6 de 6 frases legítimas → True, 01/10);
- 📊 `company_memories` = 0 linhas; 300 de 314 `session_summaries` de WhatsApp têm `agent_id` nulo e o leitor filtra por
  `agent_id` (`memory_service.py:1210-1212`); a apólice só se consulta por CPF/nome/nº (`infocap_tool.py:323-325`);
- 📊 o prompt manda em três direções ("uma por vez" × "bloco de até 4" × "de uma vez só, até 12") e o fiscal de tamanho corta
  para 3 frases/450 chars (`o_fim_do_atendimento.py:2646-2651`);
- 📊 em **501 de 1.079** conversas de WhatsApp (46%) o agente já teria esquecido o começo (query `messages` × `conversations`).

📊 Contexto que torna a mudança barata **e** a medição obrigatória: os **4** agentes `attendance` estão `is_active=false`
(`select … from agents where agent_role in ('attendance','insured_external')`, 01/10) e só **364** falas do agente existem, quase
todas teste do Founder. Ninguém real é atendido hoje; não há acervo para comparar → a bancada do §5 é a régua.

**O que já existe e é a base (não refazer — CLAUDE.md §5):** a Bancada (`backend/app/services/evals/bancada.py`,
`backend/scripts/bancada.py`, níveis N1/N2, dublês `evals/dubles.py`, corpus `tests/corpus/bancada/atendimento/`); o buffer de
rajada com janela adaptativa 3/8/18 s (`message_buffer_service.py:268`, `janela_de_espera`) e a mídia do turno
(`webhook.py:825`, `_midia_do_turno`); a ficha (`attendance_ficha.py`); o diário (`services/diario_de_decisoes.py`, tabela
`diario_de_decisoes`, origem `atendimento` já aceita); o destravador e `cerebro_modos` (SPEC-123/124); o Model Router
(`llm_papeis`/`llm_pricing`).

## 1. O EXECUTION CARD

```
OUTCOME ........  o segurado conversa com um atendente que LEMBRA a conversa inteira (e a anterior, do mesmo telefone na
                  mesma corretora), o reconhece pelo nome, deduz o óbvio, não repergunta, responde a rajada UMA vez e só
                  chama pessoa no grave — sem perder nenhuma trava que impede mentira ou ação irreversível; a versão antiga
                  volta com UM update no banco. 📊 meta: bateria DEPOIS ≥ ANTES em todo cenário crítico e melhor no total (G1)
RISCO ..........  9 — ALCANCE segurado 3 · REVERSIBILIDADE mensagem enviada 3 · FREQUÊNCIA todo atendimento 2 = 8, +1 por
                  ordem do Founder ("mais importante do que parece", §3.2): o prompt e a memória de TODO atendimento mudam
SUPERFÍCIE .....  3 — memória, prompt, fiscais, identificação, buffer de rajada, diário, bancada, papéis do destravador
PISO APLICADO ..  §3.2 — ENVIA mensagem ao segurado; migrations que alteram estrutura/dado (diário, chave de versão, papéis,
                  padrão do destravador); a identificação pelo telefone mexe no filtro `company_id` → CRÍTICO
NÍVEL ..........  🔴 CRÍTICO · builders Opus 5.5 xhigh, frescos, um por fatia · juiz ‖ red team Opus 5.5 · 1 conserto ·
                  confirmação se houver blocker
O FIO ..........  §2 · o teste do fio (S0) é a 1ª entrega: o cenário C4 atravessa webhook → rajada → montagem → modelo →
                  fiscais → resposta pelo MOTOR real (dublê só na borda), nasce VERMELHO no prompt de hoje
PARALELISMO ....  S0 (bancada) ‖ S1 (T4) ‖ S5 (rajada) — arquivos disjuntos, listados no §5 → S2 → S3 → S4 → S6 → S7 → S8.
                  `nodes.py` e `graph.py` são HUB: só S2, S3, S4, S6, em SÉRIE
UNIDADES .......  9 fatias, S0–S8 (§5)
COESÃO .........  "lembrar" (S2) e "reconhecer" (S3) redefinem o que o prompt (S4) consome → em série; o diário (S6) registra
                  o que S3/S4 decidem → depois deles; migrations do diário e do destravador juntas em S6 (uma autoridade)
TIME ...........  gerente · 9 builders frescos · juiz ‖ red team · confirmação · atualizador de documentos · lente do dado
                  no G1 (reconfere o placar por caminho independente: as transcrições, não o JSON do runner)
REFERÊNCIA .....  interna: `test_a_maquina_de_lavar_vai_ate_o_fim.py` (atendimento ponta a ponta), `test_golden_do_eletricista.py`,
                  a LINHA DE BASE da S0 (o prompt de hoje, mesmos cenários, mesmo modelo) · externa: §7
GATES ..........  §6 (G1–G7), cada um com a MUTAÇÃO que o deixa vermelho
O ELO ..........  "o agente repergunta PORQUE esquece" — medir A (reperguntas na linha de base, checagem sem LLM), B (o
                  dado saiu da janela de 15 naquele turno) e B→A (o runner grava o histórico ENVIADO ao modelo no turno da
                  repergunta e mostra que a mensagem com o dado não estava lá). Idem T4: a resposta do C13 reescrita traz o
                  rastro do fiscal no mesmo turno
FAIXA DE RELÓGIO  💭 1 a 1,5 dia de relógio · tetos de turno e contexto da §10 do protocolo
ORÇAMENTO ......  OpenAI ≤ US$ 4,00 para TODOS os testes da SPEC · Anthropic ≤ US$ 0,30 (só o já previsto). Lido do LEDGER
                  `token_usage_logs` (`service_type='bancada'`, desde o 1º commit da SPEC); o runner PARA sozinho. Faltou →
                  caixa do Founder, nunca gastar além
```

## 2. O FIO

```
segurado escreve (texto, foto, áudio, documento — 1 ou N mensagens)
→ webhook.py (_handle_evolution_like_inbound) → message_buffer_service (janela_de_espera: a RAJADA fecha)
→ webhook.py:_midia_do_turno (descreve TODAS as fotos do turno, papel `visao`; transcreve áudio) → UM turno
→ IDENTIDADE (S3): telefone → mesma corretora → conversa anterior / apólice → "É o João?" (confirmação, nunca suposição)
→ MONTAGEM (graph.py:_build_initial_state): prompt NOVO enxuto (S4, versão lida da chave do banco) + ficha (com o que a
  apólice trouxe) + CASO ANTERIOR (resumos do mesmo telefone/corretora) + HISTÓRICO INTEIRO do atendimento em aberto, vindo de
  `messages` (segurado · agente · EQUIPE marcada), por tokens, sem SystemMessage no histórico (S2)
→ MODELO (papel `atendimento`) ⇄ ferramentas (InfoCap, insurer_dispatch, portal_action, human_handoff, knowledge_base_search)
→ FISCAIS: honestidade do handoff aceita o carimbo de acionamento (S1) · pergunta repetida com fonte ampliada (S3) · tamanho
  vira medição, regenera só > 2× (S4) · contrato de apólice mantém o veto
→ DIÁRIO: só nos momentos de julgamento (S6)
→ resposta → balloons (≤ 4) → WhatsApp — UMA resposta por rajada

destravador (acionamento travou na URA) → destravador.py:_conversa_do_segurado → recebe a MESMA conversa inteira do
atendimento em aberto (hoje `[-15:]`, destravador.py:441-476), pela MESMA fonte única de histórico da S2
```

## 3. DECISÕES (do Founder, 01/10 — são lei)

| # | decisão |
|---|---|
| D1 | **A conversa INTEIRA até o atendimento ser resolvido.** Fim do corte por contagem (T1): o histórico do atendimento em aberto entra inteiro, com teto por TOKENS grande (💭 ~80 mil tokens; o BLOCO 0 mede o p99 real e fixa o número com `constante_justificada`). Só acima do teto a parte MAIS ANTIGA vira resumo — nunca corte silencioso. O prompt de sistema **não** entra no histórico nem no checkpoint. As falas da EQUIPE entram, marcadas como da equipe (T3/M2). O destravador recebe a mesma conversa, pela mesma fonte. "Resolvido" = a fronteira que `o_fim_do_atendimento.py` já grava (`resolvido_em`); atendimentos anteriores entram como CASO ANTERIOR (D2) |
| D2 | **Identificação pelo telefone, na MESMA corretora.** Telefone → conversa anterior e/ou apólice desta corretora → chama pelo nome e reaproveita CPF/apólice, **só confirmando** ("É o João, da apólice do Onix?" — 💭). Telefone compartilhado: a 1ª confirmação expõe só o primeiro nome; o resto só depois do "sim". CPF reaproveitado aparece MASCARADO na saída (T19). Nada atravessa corretora (CLAUDE.md §7) |
| D3 | **Prompt novo enxuto.** Abre com o OBJETIVO e o JULGAMENTO ("resolva como a melhor atendente da corretora; pense antes de perguntar; o que foi dito, o que está na apólice e o que se deduz não se pergunta; pergunte só o que muda a próxima ação"); **UMA** lista curta do que não se cruza; nenhuma regra contraditória (T11 unificada: "pergunte o mínimo; o independente vai junto; o delicado vai sozinho"); T9 e T10 saem; descrições de ferramenta no padrão "deduza; pergunte só se o relato não decidir" (T14). **A versão antiga fica guardada e reativável SEM deploy**: chave governada no BANCO, por corretora (company_id + RLS + filtro no código), **nunca env** |
| D4 | **O fiscal da honestidade do handoff aceita acionamento confirmado (T4).** Aceita o carimbo de `insurer_dispatch`/`portal_action` (`dispatched`, protocolo); casa só verbos de transferência A PESSOA; nunca reescreve para "atendimento humano" quando ninguém pediu humano. A intenção (o caso de 17/08, "encaminhei" 4× sem encaminhar) continua VERMELHA |
| D5 | **Rajada → UMA resposta.** Texto em sequência e imagens + explicação viram um turno só; mensagem que chega com o turno em andamento entra NELE (ou o refaz antes de sair) — nunca uma 2ª resposta à mesma rajada. Reusa o buffer e a `_midia_do_turno` existentes |
| D6 | **O que se MANTÉM (não se corta):** T5 só relatar o que fez · T6 nunca inventar protocolo/prazo/agendamento · T7 cobertura só com evidência · T8 confirmar antes de acionar (só a FORMA muda: uma linha, sem reperguntar) · T15 pessoa no grave · T16 guincho por colisão = sinistro · T17 identidade · T18 vocabulário de URA proibido · T19 mascarar na SAÍDA · T21 regra dos 7 dias · T23 apresentação fora do modelo · T25 ≤ 4 balões · a segunda chance da SPEC-123 (`human_handoff.py`) · o destravador e o diário das SPECs 123/124. Afrouxa só: T15 "irritado após 2 tentativas" → "irritado E pedindo saída" |
| D7 | **Diário da conversa só nos momentos de julgamento** — não uma linha por mensagem: (1) deduziu um dado que a ferramenta pediu · (2) respondeu dúvida de cobertura/regra sem pessoa (com a fonte) · (3) decidiu NÃO chamar pessoa onde o código antigo chamaria · (4) chamou pessoa (o motivo). O resultado fecha a linha sozinho: segurado corrigiu · repetiu · pediu pessoa logo depois · fiscal da repetição disparou. 💭 1–3 linhas por atendimento. Escrito para GENTE ler |
| D8 | **Opus 5.5 na 2ª opinião e na reserva do destravador** (o Founder confirmou): `destravador_segunda` primário e `destravador` reserva = `claude-opus-5-5`, pelo caminho governado do Model Router (migration de `llm_papeis` + snapshot), nunca env |
| D9 | **Corretora NOVA nasce com o destravador ligado** (multi-tenant): quando uma corretora ganha agente de atendimento, as linhas `cerebro_modos` (`on`, limiar 70, ramo `todos`) nascem sozinhas — sem nome nem id no código (§13.9). "Sem linha = off" continua sendo o desfazer. O DEDUZIR autônomo segue desligado em código até calibrar (SPEC-123) |
| D10 | **O fiscal de tamanho vira MEDIÇÃO (T12):** registra o tamanho; regenera só acima de **2×** o teto. Explicar cobertura ou sinistro às vezes precisa de 5 frases |

## 4. O BLOCO 0 (gerente + 1 investigador read-only, ≤ 15 min de card, antes de codar)

Premissas que mudariam o DESENHO — cada número com o comando ao lado (§0.4):
1. A janela real: `add_messages` em 3 turnos (sistema na lista?) e quantos checkpoints/threads existem; onde o SystemMessage é gravado.
2. A fronteira "resolvido": quem ESCREVE `resolvido_em` hoje e se uma sessão (`whatsapp:{tel}:{empresa}:{agente}`, uma thread
   por telefone para sempre) tem mais de um atendimento — é o corte do D1.
3. `messages`: como a fala da equipe se distingue (`payload->>'origem'`), ordem, duplicatas com o checkpointer; p50/p90/p99 de
   TOKENS por atendimento em aberto (fixa o teto do D1).
4. InfoCap aceita busca por TELEFONE? (a resposta traz `telefone`, `infocap_tool.py:866`; a busca não). Se não: identificar pela
   conversa anterior do mesmo telefone na mesma corretora (nome, CPF já dito) e consultar a apólice pelo CPF.
5. O tamanho do prompt montado HOJE para um agente real (o laudo não mediu: o import trava sem infraestrutura) — rodar em
   worktree com a infraestrutura dublada.
6. Onde mora a chave de versão (D3): existe tabela/coluna governada por corretora que sirva? Consolidar antes de criar.
7. Rajada no acervo: intervalos entre mensagens de entrada consecutivas; quantas rajadas tiveram > 1 resposta do agente; fotos
   em sequência que fecharam a janela antes da explicação.
8. `diario_de_decisoes`: as constraints de `acao`/`resultado` (`pg_constraint`) e as linhas existentes.
9. `llm_papeis` VIVO de `destravador`/`destravador_segunda` (banco × snapshot) e quem cria agente de atendimento hoje (D9).
10. Ledger: gasto `service_type='bancada'` desde o início; 1 chamada mínima por modelo antes de gastar.
11. Testes que guardam a verdade velha (§9.3): `atd-n1-sem-id-eletricista` (`deve_conter: ["CPF"]`), "uma informação por vez",
    os da honestidade. A lição migra, não morre.

## 5. AS FATIAS

**S0 · A bancada do segurado simulado e a LINHA DE BASE** (dono: `backend/app/services/evals/bancada.py`,
`backend/scripts/bancada.py`, `backend/app/services/evals/dubles.py`, corpus novo `backend/tests/corpus/bancada/atendimento/conversa/`,
`MANIFESTO.json`) — ‖ S1 ‖ S5
- Nível **N3 "conversa"** na bancada que EXISTE (não um harness novo): chama `_build_initial_state` de verdade com o
  `agent_system_prompt` de um agente real (lido do banco, sem ativar), o bloco de acionamento, a conduta, a memória, o reencontro —
  o **prompt de produção real** (o defeito do `_estado_base`, `bancada.py:609-646`, morre aqui); dublês na borda (InfoCap,
  dispatch, portal, handoff), checkpointer em memória.
- **Segurado simulado** = `gpt-6-luna` com ROTEIRO por cenário (persona · o que sabe · o que só revela se perguntado · quando
  encerra), máx. 8 turnos. Personas calibradas pelo acervo (lidas localmente, nunca copiadas sem máscara); corretoras fictícias
  `{{CORRETORA:A}}`/`B` (§13.9).
- **Juiz barato** = `gpt-6-luna` com rubrica por critério (certo/errado/parcial + trecho) **+ checagens SEM LLM**, que decidem
  sempre que podem: perguntas contadas · repergunta (âncoras de `attendance_ficha.slots_reperguntados`) · ferramentas chamadas e
  proibidas · handoff sim/não · protocolo EXATO no texto · frase proibida "Registrei seu pedido de atendimento humano" · nº de
  respostas por rajada. Calibração: o gerente lê 10 transcrições e marca à mão; discordância do juiz > 20% → o juiz LLM não decide
  gate, só as checagens e a leitura humana.
- **Cenários:** os 16 do laudo (C1–C16; críticos C6, C7, C10, C13, C15, C16) + **C17** rajada de 5 frases → 1 resposta + **C18**
  8 imagens REAIS + 1 explicação → 1 resposta que usa o conteúdo das fotos. As imagens vêm do intake por caminho LOCAL passado ao
  runner (fora do repositório, nunca commitadas, nunca no relatório).
- **LINHA DE BASE** com o prompt de HOJE, mesmo modelo de iteração (`gpt-6-luna` como atendente), k=1 nos 18 + o controle C14 k=2.
  🔴 Linha de controle (§9.2/§9.3): **C4, C11 e C13 têm de FALHAR hoje** (se passarem, o cenário não testa o que diz) e C14 tem de
  sair igual nas duas versões.
- 💭 custo: Luna US$ 0,10/0,50 por M (📊 `llm_pricing`, 01/10) → 18 × 8 turnos × ~30 mil tokens ≈ US$ 0,5 por rodada.

**S1 · T4 — o fiscal aceita o acionamento** (dono: `backend/app/agents/honestidade_do_handoff.py` e os testes dele; ⛔ não toca
`nodes.py`) — ‖ S0 ‖ S5
- D4. Teste com as 6 frases do laudo (acionei/solicitei/chamei/…) com carimbo de dispatch → passam intactas; sem carimbo e sem
  handoff → continua reescrito; a conversa de 17/08 continua VERMELHA. Mutação: tirar o carimbo da lista → C13 volta a falhar.

**S2 · A memória: conversa inteira, uma fonte só** (dono: `nodes.py` região da janela/montagem, `graph.py` região do checkpoint,
`langchain_service.py` (código morto das 60), `core/constants.py`, `services/destravador.py` `_conversa_do_segurado`)
- **M1** histórico por tokens (D1), sem SystemMessage no checkpoint; **M2** fonte = `messages` com a equipe marcada; o
  checkpointer fica só para as ferramentas do turno; **T2** só `knowledge_base_search` é comprimido — resultado de apólice e de
  acionamento vira resumo estruturado na ficha (entrega para S3). O código morto das 60 sai.
- O destravador lê a MESMA conversa (fim do `[-15:]`), com o mesmo teto.
- Teste do fio: C4 (CPF na troca 1, pedido na 13) verde pelo motor real; mutação: voltar a janela para 15 → vermelho.

**S3 · Identidade e ficha** (dono: `agents/tools/infocap_tool.py`, `attendance_ficha.py`, `memory_service.py` região do leitor,
`o_fim_do_atendimento.py` região do reencontro, `graph.py` bloco CASO ANTERIOR, `nodes.py` fiscal da repetição) — depois de S2
- **M4** identificação pelo telefone (D2), com o resultado do BLOCO 0 item 4; **M3** a ficha ganha o que a apólice trouxe
  (veículo, placa mascarada, endereço do risco, assistências) e o resumo do último resultado de ferramenta; **M5** resumos sem
  filtro de `agent_id` para o atendimento, bloco CASO ANTERIOR no reencontro (T22 mantém "assunto novo", soma a memória);
  **M6** ferramenta `buscar_conversas_anteriores` (o modelo decide quando), só mesmo telefone + mesma corretora, 💭 até 12 meses.
- **T13** o fiscal da pergunta repetida compara também com o histórico e a apólice.
- 🔴 Dois tenants REAIS: o mesmo telefone em A e B → B nunca vê nome, CPF, resumo ou apólice de A (filtro no código, não só RLS).

**S4 · O prompt novo, o banco, o molde e a versão reativável** (dono: `app/core/prompts.py`, `agents/tools/portal_params.py` e
`insurer_dispatch_tool.py` (textos das ferramentas), `graph.py` conduta e prefetch de RAG, `nodes.py` fiscal de tamanho,
`frontend/…/agent-blueprints-canonical.ts`, migration da chave de versão) — depois de S3
- D3 + D10 + T24 (prefetch de RAG só nos melhores trechos, 💭 ≤ 8 mil chars; o modelo decide `knowledge_base_search`).
- `ATTENDANCE_BASE_PROMPT` de hoje fica INTACTO como versão `v1`; a nova é `v2`. A chave por corretora escolhe; sem linha = padrão
  declarado em código. O prompt do banco (`agents.agent_system_prompt`): o texto antigo é GUARDADO antes; só se reescreve onde o
  texto é igual ao molde (hash) — texto personalizado pela corretora não se sobrescreve, vai ao relatório.
- Migration com **APPLY/VERIFY/ROLLBACK escritos ANTES** (`MIGRATIONS-AUTHORITY.md`), expand-first, idempotente. Voltar à v1 = UM
  `update` de uma linha, valendo no próximo turno.
- Depois do gate, a chave passa à `v2` nas corretoras com agente de atendimento (o agente continua DESLIGADO).

**S5 · A rajada** (dono: `services/message_buffer_service.py`, `api/webhook.py` regiões do buffer e da `_midia_do_turno`) — ‖ S0 ‖ S1
- D5 pelo que o BLOCO 0 item 7 medir: foto sem legenda espera a explicação e cada foto nova renova a janela; mensagem que chega
  com o turno em andamento entra nele (ou o refaz antes do envio); as N fotos descritas em paralelo e entregues juntas ao turno.
  Teste pelo motor real com a sequência medida (5 textos; 8 fotos + 1 explicação) → UMA resposta; mutação: desligar o
  reaproveitamento → 2 respostas → vermelho.

**S6 · O diário da conversa e as chaves do destravador** (dono: migrations novas, `services/diario_de_decisoes.py`, os pontos de
escrita nas ferramentas/handoff, `app/dashboard/atendimentos/decisoes/page.tsx` se a tela precisar) — depois de S4
- D7: migration expand-first acrescenta `acao='respondeu_segurado'` e `resultado` `segurado_corrigiu`/`segurado_repetiu`; as 4
  escritas do D7; os sinais de resultado fecham a linha. Duas corretoras não se veem.
- D8: migration de `llm_papeis` (Opus 5.5) + snapshot regerado. D9: as linhas `cerebro_modos` nascem quando a corretora ganha agente
  de atendimento (gatilho no banco ou o único caminho de criação, o que o BLOCO 0 item 9 apontar). Cada migration com
  APPLY/VERIFY/ROLLBACK antes. Mexeu em `app/`? `npm run test:rotas-montam` + `next start` + 1 requisição (§9.1).

**S7 · A rodada DEPOIS e a confirmação no modelo de produção** (gerente + builder da bancada)
- Os mesmos 18 cenários, o mesmo modelo de iteração (Luna), a mesma semente de roteiro, com a `v2` → placar ANTES × DEPOIS por
  cenário. Iterar no prompt é permitido dentro do orçamento; cada volta reroda os 18.
- **Confirmação** com o atendente em `gpt-6.1-sol` high (o modelo de produção), k=1, nos 6 críticos + C3, C4, C11, C13, C17, C18 com
  a `v2` — 💭 ≈ US$ 2 (prompt menor + cache). Crítico que falha no Sol reprova a versão, mesmo verde no Luna.

**S8 · Costura e documentos** (gerente + atualizador)
- Teste de COSTURA: a saída REAL de cada fatia é a entrada da outra — rajada (S5) → identidade (S3) → histórico (S2) → prompt v2
  (S4) → acionamento confirmado sem reescrita (S1) → linha no diário (S6) → `update` da chave → `v1` byte a byte.
- Relatório (≤ 25 KB), PENDENCIAS, ESTADO, DECISIONS, TAREFAS-DO-FOUNDER (o roteiro do teste real), painel.

## 6. OS GATES

```
G1  🔴 bateria DEPOIS ≥ ANTES em TODO cenário crítico (C6 C7 C10 C13 C15 C16) e MELHOR no total (soma dos critérios dos 18),
    mesmo modelo, mesmos roteiros; C4, C11, C13 que falham ANTES passam DEPOIS; C14 (controle) igual. Lente do dado reconfere
    o placar lendo as transcrições. Mutação: rodar a "depois" com a v1 → o placar volta ao ANTES
G2  🔴 0 regressão nos ⚑ — as travas do D6 (T5 T6 T7 T8 T15 T16 T17 T18 T19 T21 T23 T25, a segunda chance, o destravador):
    cada uma tem teste ou checagem que a prova, e uma mutação que a tira → vermelho
G3  os testes do produto: `test_a_maquina_de_lavar_vai_ate_o_fim`, `test_golden_do_eletricista`, os da honestidade, da ficha,
    do buffer e das SPECs 123/124 verdes; teste que guardava verdade velha MUDA com a lição migrada (§9.3), nunca apagado
G4  desfazer prova: `update` da chave → o prompt montado da `v1` tem o MESMO hash que no commit base, sem deploy; e volta à v2.
    Mutação: o leitor ignora a chave → vermelho
G5  2 tenants reais: identidade, histórico, resumos, CASO ANTERIOR, diário e `cerebro_modos` novos — A nunca vê B. Mutação:
    tirar o filtro `company_id` do código → vermelho
G6  custo ≤ US$ 4,00 OpenAI (e ≤ US$ 0,30 Anthropic), do LEDGER, com a query no relatório
G7  bateria inteira UMA vez, depois do conserto, 0 falhas novas contra `docs/canon/reports/BATERIA-LINHA-DE-BASE.txt` (33)
```

## 7. O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS (§7.3)

- **https://sierra.ai/blog/benchmarking-ai-agents** (τ-bench; código https://github.com/sierra-research/tau2-bench) — um LLM
  simula o usuário com objetivo escondido e conversa com o agente real contra ferramentas; mede pass^k (📊 no artigo: < 50% em
  pass@1 caindo para ~25% em pass^8). **Modelamos:** o segurado simulado com roteiro e fatos que só revela se perguntado (S0).
  **Rejeitamos:** k=8 — o orçamento do Founder dá k=1 (k=2 no controle); a variância fica declarada como limite. **O juiz
  inspeciona:** abre 3 transcrições do N3 e confere que o simulador reagiu ao que o agente disse (falas não fixas).
- **https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents** — eval de agente conversacional precisa de um 2º
  LLM fazendo o usuário; o juiz LLM tem de ser calibrado com humanos; checagem determinística onde der. **Modelamos:** checagens
  sem LLM decidem o que podem; o juiz LLM só com calibração (≤ 20% de discordância). **Rejeitamos:** juiz de outro provedor caro
  (Opus) em toda rodada — não cabe nos US$ 0,30 da Anthropic; o juiz barato + leitura humana + linha de controle substituem.
  **O juiz inspeciona:** a planilha de calibração das 10 transcrições marcadas pelo gerente.
- **https://fin.ai/updates/cx-score** (Intercom CX Score) — nota 1–5 com o porquê em TODA conversa, critérios em linguagem
  natural. **Modelamos:** a rubrica do juiz em português de gente ("repetiu pergunta", "prometeu o que não fez", "pediu o que
  estava na apólice"). **Rejeitamos:** a nota em produção em 100% das conversas agora — é a ideia 1 do laudo, vira pendência
  (precisa do lote noturno e de conversas reais; hoje são 0). **O juiz inspeciona:** a rubrica no corpus N3 e um critério que
  reprova o caso de 17/08 reintroduzido.
- **https://sierra.ai/blog/agent-development-life-cycle** — conversas anotadas viram testes de regressão rodados antes de cada
  atualização. **Modelamos:** o "errado" do diário da conversa (S6) alimenta `diario_para_bancada.py` e vira cenário N3.
  **Rejeitamos:** bateria por cliente vivo a cada mudança — não há volume. **O juiz inspeciona:** um "errado" vira caso pendente.
- **https://arxiv.org/abs/2605.12894** — simuladores cooperativos e homogêneos enganam; personas variadas pegam mais defeito.
  **Modelamos:** personas difíceis (irritado, com pressa, que não diz que é condomínio, que manda rajada). **Rejeitamos:** gerar
  personas em massa — 18 roteiros escritos à mão a partir do acervo. **O juiz inspeciona:** C8, C15 e C17 têm comportamento não
  cooperativo no roteiro.

## 8. O QUE A EXECUÇÃO NÃO PODE FAZER

- Não reabrir as decisões do §3. Não criar SPEC nova. Não criar motor paralelo: a bancada, o buffer, a ficha, o diário, a memória e
  o Model Router são os que existem (CLAUDE.md §5).
- Não cortar nenhuma trava do D6. Não remover o fiscal T4 — consertá-lo. Não afrouxar régua nem alterar teste para passar.
- Nenhuma mensagem real sai; nenhum agente é ligado (`agents.is_active` fica como está). Banco: SELECT livre; escrita só por
  migration da fatia, com APPLY/VERIFY/ROLLBACK antes. Nunca `schema_completo.sql`/`upgrade_v6.2.sql`/`storage_buckets.sql`.
- Nunca imprimir PII: conversas e imagens do intake são usadas LOCALMENTE, nunca copiadas para o repositório sem máscara, nunca
  coladas no relatório. Nenhum nome de corretora, atendente ou segurado em código, teste ou corpus (§13.9).
- Não gastar além de US$ 4 OpenAI / US$ 0,30 Anthropic. Não usar env para escolher prompt ou modelo.
- `medir_rota.py` e testes que mutam a árvore só em worktree próprio (`C:\wtNN`). Nunca `git add -A`.

### O QUE SAIU (e vira pendência, com o que destrava)
- **Nota de experiência em 100% das conversas de produção** (ideia 1 do `INV-IDEIAS`, nota 90): depende de conversa real e do
  lote noturno → pendência; esta SPEC deixa a rubrica pronta para reuso.
- **Foto direto no modelo do atendimento** (laudo D7, nota 55 × 60): a SPEC-124 acabou de escolher o Luna por bancada — fica.
- **M8 `company_memories` no atendimento**: 📊 0 linhas hoje; não muda nada agora.
- **Ligar o agente para uma corretora com o diário em sombra 1 semana** (laudo §4.3 item 8): é do Founder, na caixa dele.
- **pass^k com k ≥ 4** e juiz Opus em toda rodada: fora do orçamento; limite declarado.
