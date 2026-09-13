# DIAGNÓSTICO DOS PILOTOS (09–11/09) E PLANO DA FAMÍLIA EXTRA — 12/09/2026

> **v2 · 13/09/2026.** §0–§5 são a primeira leitura (manhã de 12/09, 4 laudos). §7–§12 são a segunda leitura,
> com a parte cortada da mensagem do Founder, 3 laudos novos (cobrança, portal de vidros, humano na URA) e as
> decisões D-PILOTO-08…14. Onde §3 e §7–§11 divergem, **vale a segunda leitura**.

> Para o Founder decidir, e para o próximo chat converter em SPECs. Nasceu de quatro auditorias
> read-only (atendimento · chat principal e coberturas · handoff/vigia/cérebro · cobrança e mapa)
> sobre o banco de produção e o código em `05f46a9`. **Nada foi executado.** Onde diz 📊 há consulta
> ou `arquivo:linha`; onde diz 💭 é estimativa ou exemplo. Página do Founder: aba **Pilotos** do dossiê
> (https://claude.ai/code/artifact/afe1510d-f31c-4d13-9441-aa920ad2b868#pilotos).

## 0. A leitura honesta do que os testes foram

📊 O agente de atendimento ficou ligado **~1h53 em três dias**: 58 min na AutoFleet (09/09, 10:48–11:46) e
55 min na Resulta (10/09, 13:59–14:54, encerrados por "WhatsApp desconectado" e pela Saionara desligando).
Falou com **5 segurados reais**, todos da AutoFleet, **todos em conversas que a Regina já conduzia** — antes de a
janela de 7 dias existir (subiu às 20:51 de 09/09). A Regina pediu desculpa ao cliente 4 vezes. Na Resulta, os
atendimentos foram com números de teste. **0 acionamentos concluídos com protocolo pelo agente** (o único real
travou num menu e foi salvo à mão). A cobrança rodou 2 vezes em modo **teste**, para o número de teste, sem gravar
uma linha do ledger que a EXTRA-001 construiu: **a máquina da EXTRA-001 nunca foi ligada.**

Conclusão: os testes mediram menos o produto e mais **cinco defeitos estruturais que impediram o produto de ser
testado**. Os cinco têm causa localizada e conserto pequeno-a-médio. O que não dá para concluir dos testes é a
qualidade do agente em operação contínua — isso só um piloto de 3 dias inteiros, depois dos consertos, mede.

Notas dadas pelos auditores (0–100, por dimensão, com justificativa nos laudos): **atendimento 48** (apólice certa 50 ·
coleta e age 40 · aciona 25 · fala como humano 60 · sabe calar 45 · sabe pedir ajuda 55) · **chat principal 49**
(apólice certa 35 · uma rodada 25 · completude 45 · confiabilidade 80 · velocidade 60).

## 1. Os defeitos, cada um com causa e prova

### 1.1 A apólice errada, ou a lista inteira (chat e atendimento)
- 📊 Chat: **7 de 7** consultas por CPF listaram apólices vencidas (31 linhas); 5 de 7 perguntaram antes de responder;
  2 de 7 resolveram em 1 rodada. Atendimento: chamou de "ativa" uma Allianz vencida há 27 dias e pediu ao cliente
  que escolhesse; o cliente corrigiu o robô.
- **Causa 1 — a ferramenta manda listar e escolher no mesmo texto.** `infocap_tool.py:404-412` imprime
  `opcoes_de_apolice (liste TODAS…)` sobre `matches` sem filtrar vigência e com `policy_status` cru (o campo que
  `policy_answer_composer.py:279` documenta como "ativo até em apólice vencida há anos"); 48 linhas abaixo (`:453`)
  manda "escolha VOCÊ". O modelo obedece à primeira.
- **Causa 2 — o filtro certo existe e está desligado para o chat.** `_real_vigencia`/`_compose_options`
  (`policy_answer_composer.py:279-329`) esconde vencidas; a inferência de ramo (`_AUTO_INTENT_RE`/`_RESI_INTENT_RE`,
  `infocap_tool.py:25-33`) e a auto-seleção (`:200-230`) só rodam para `agent_role in (attendance, insured_external)`.
  O chat do painel é `core`. E `nodes.py:263-274` **anula** qualquer resposta que não liste todas as opções.
- **Causa 3 — a informação para escolher já vem na primeira chamada.** 📊 `/cliente_ligacoes` devolve `inivig`,
  `fimvig`, `ramo`, `cancelado` por documento; `infocap_connector.py:1315` emite `ambiguous_policy` sem olhar as datas.
- **Causa 4 — o prompt ensina a listar** em 3 de 4 instruções (`prompts.py:126, 185, 189, 206`); o `CORE_BASE_PROMPT`
  não tem uma linha sobre vigência ou ramo.
- **Causa 5 — a inferência de ramo só lê a mensagem atual** (`_product_hint_from_query(user_query)`): quando o cliente
  manda só o CPF, não roda. `chaveiro` só existe no regex de auto.

### 1.2 A apólice incompleta ("a InfoCap bloqueou")
- 📊 11 declarações de "não consigo/não retornou", 10 antes do conserto de 10/09 e 1 depois. O deploy entrou entre
  12:28 e 15:59 de 10/09.
- **Causa 1 — o cadastro do CORP é 23% da apólice.** Medido na HDI residencial da Saionara: `/itens` tem 6 garantias
  (prêmios somam **R$ 70,29**); o PDF tem 10 linhas e os prêmios somam **R$ 306,60 = exatamente o `preliq`** que o
  próprio `/documento` devolve. Faltam no CORP: Vendaval, Ruptura de Tubulações, Cláusula Valor Novo e
  **Assistências Essenciais (R$ 125,94 = 41% do prêmio)** — o item que o corretor mais pergunta. Uma franquia diverge
  (Danos Elétricos 550 no CORP × 600 no PDF).
- **Causa 2 — o PDF só é lido por palavra-chave.** `policy_document_evidence_requested`
  (`policy_document_evidence_service.py:132`) exige termos como "cobertura/franquia" **na última mensagem**; "quero
  detalhamento da apólice X" não casa. E `nodes.py:1018` manda só a última mensagem humana para `core`.
- **Causa 3 — campos da API nunca lidos:** `itens[].observacoes` (as franquias em prosa), `sit_renovacao_txt`
  ("APÓLICE VIGENTE…"), `sit_sinistro_txt`, `tabela_itens` (nome do plano), `/seguradoras` e `/ramos` (catálogo).
  `forma_pag` do cabeçalho diz Boleto enquanto as parcelas dizem Cartão (§12.1: campo que mente).
- **Causa 4 — o turno que some.** Duas vezes o agente respondeu "ainda não recebi uma pergunta sua": eram os dois
  maiores turnos do acervo (📊 120 e 128 chunks de RAG; 135k e 163k tokens de entrada). O bloco de contexto
  recuperado entra no system prompt sem teto (`graph.py:1395-1405`) e sepulta a pergunta.
- **Fonte de verdade (recomendação):** coberturas · LMI · franquias · cláusulas · plano de assistência → **PDF vence**;
  parcelas · quitação · status · sinistro · vigência · renovação → **CORP vence**. Reconciliar por rótulo, marcar origem
  por linha, mostrar as duas quando divergem, e **contar**: Σ prêmios das garantias ≠ `preliq` → sinal
  "cobertura incompleta no cadastro" (teria acendido vermelho nesta apólice).

### 1.3 O agente não sabe o que o plano cobre
- 📊 Condições gerais no corpus: 97 ingeridas, de **8 seguradoras**; a Resulta trabalha com **61**. Plano/nível de
  assistência estruturado (básico/VIP/premium, serviços, limites): **0 de 61**. Zurich, SulAmérica, Chubb, Itaú,
  Sompo, Suhai, Sura, Alfa, MetLife: nada. `knowledge_cards`: 857, 39 de assistência, 4 nomeiam seguradora.
  `assistance_policy.py:28` é uma constante com 3 serviços residenciais. Por isso o agente misturou Allianz auto com
  residencial e admitiu "não recuperei o detalhe fino do plano VIP".
- **A ligação apólice → condições gerais já é possível e ninguém faz:** o PDF diz o processo SUSEP
  (15414.002160/2005-11) e esse processo **já está no corpus**; `tabela_itens: "PACOTE"` e "Benefícios" dão o plano.

### 1.4 Respostas fragmentadas, perguntinhas, saudação fora de hora
- 📊 Rajadas de ≥2 mensagens do segurado em ≤30 s: **4 de 4 fragmentaram** (2 respostas cada). 10 perguntas para 8
  slots; `agua_escorrendo` perguntado 3 vezes depois de "já fechei o registro"; "vocês estão bem?" duas vezes.
  "Boa notícia começar o dia com você" na 30ª mensagem de um sinistro com vítima. Mensagens de até 760 caracteres.
  Abriu um caso chamando o cliente pelo nome de outra pessoa de 22 dias atrás (a thread por telefone nunca reinicia).
- **Causa exata da fragmentação:** debounce **por ociosidade** de 8 s (`message_buffer_service.py:158`): qualquer
  pausa de 9 s abre um segundo turno (as 3 rajadas medidas tinham 10, 12 e 22 s); **mídia não passa pelo buffer**
  (`webhook.py:1448-1451` dispara geração imediata); **não existe trava por conversa nem cancelamento** (zero `lock`
  no webhook; `buffer_processor` roda 6 em paralelo); a resposta velha é enviada de qualquer jeito.
- **Causa das perguntas repetidas:** a ficha guarda `apolice_confirmada: bool`, não os slots já respondidos
  (`attendance_ficha.py:132-141`); "nunca pergunte o que o cliente já disse" é só texto no prompt (`prompts.py:90`).
- **Causa da saudação:** `prompts.py:352-361` manda "SEMPRE se apresente na primeira mensagem" e o modelo lê "primeira
  minha"; o bloco de religamento (`o_fim_do_atendimento.py:1468`) nasceu depois do incidente e nunca foi exercitado.
- **Causa lateral grave:** 📊 30 pares de mensagem do segurado gravadas em duplicidade (caminho do agente + espelho,
  6–12 min depois) — o modelo relê a mesma pergunta como nova; e conversas partidas em duas linhas (telefone × LID)
  fazem a janela, o `HUMAN_REQUESTED` e a lista de exceções lerem a linha errada.

### 1.5 O grupo de suporte virou ruído
- 📊 Não existe contagem de envio ao grupo no banco (nenhum dossiê entra em `platform_sends`). Reconstruído pelos
  gatilhos: 7 mensagens em 77 min sobre **um** encanador da Resulta (3 dossiês por reabertura de sessão + 3 "espera
  vencida" de 10 em 10 min + 1 aviso de canal).
- **Causa 1 — o re-alerta de 6 h não pergunta se um humano está na conversa.** `handoff_watchdog.py:140-146`
  seleciona `status='HUMAN_REQUESTED'`; 📊 **58 de 58** conversas elegíveis tinham humano da corretora falando nos
  últimos 7 dias (uma com 865 mensagens humanas). 130 conversas viraram `HUMAN_REQUESTED` pelo espelho/claim, não
  pelo agente (`human_handoff_reason` vazio em todas): são os celulares da equipe capturados pelo observador.
- **Causa 2 — o dossiê picotado.** Existem dois dossiês; o de acionamento sai **sem `bloco_unico`** em três caminhos
  (`dispatch_router.py:3304`, `:201`, `dispatch_watchdog.py:315`) e quebra a cada 300 caracteres
  (`balloons.py:17`). O conserto de 18/08 foi aplicado num caminho só.
- **Causa 3 — 4 dígitos e link do painel por decisão escrita** (`telefone_curto`, `insurer_dispatch_service.py:3595`;
  `link_do_caso`), que o piloto provou errada: no celular, o número clicável custa um toque, o painel custa uma página.
- **Causa 4 — não existe lista de números da casa com efeito.** `alert_target.internal_numbers` e
  `observer_exclusions` estão vazias e só impedem a captura; `company_members` não tem telefone.
- **Não existe:** aviso de "atendimento concluído", resumo diário, registro contável de envio.

### 1.6 O corredor travou sozinho ("residência" em vez de "1")
- 📊 Reconstrução da sessão Allianz de 10/09 (`observed_events` 432614de…): o corredor mandou **"residência"** duas
  vezes (17:12 e 17:18) para o menu "1 Residencial · 2 Condomínio · 3 Empresarial". **Quem digitou "1" foi a Saionara,
  às 17:18:14.** O Cérebro nunca digitou. O caso morreu às 17:38 quando a atendente da Allianz chegou e ninguém
  respondeu.
- **Causa 1 — um slot que ninguém converte em dígito.** Passo `menu_qual_seguro_tres_opcoes`
  (`corridor_playbooks.py:370-381`) responde `{qual_seguro_opcao}`; a descrição pede "de que seguro ele fala — o da
  residência" (`:9653`, `insurer_dispatch_tool.py:310`); `_derivar_teclas_do_caso` (`insurer_dispatch_service.py:394`)
  deriva 25 slots `*_opcao` para tecla e **não este**. A SPEC-083 trocou a constante "1" (que mandava condomínio para
  residencial) por slot e não criou a derivação. O guarda `test_a_tecla_tem_a_forma_da_seguradora.py` lê o AST das
  derivações que existem — um slot nunca derivado é invisível para ele (12 asserções verdes com o defeito vivo).
- **Causa 2 — o Cérebro não sabe que foi recusado.** `_last_entry` devolve só "Vamos tentar novamente."; não existe
  estado "última resposta recusada"; `MAX_SENTINELA_ATTEMPTS=2` esgota em ~40 s de relógio; o handoff sai antes de
  qualquer tentativa inteligente.
- 📊 Auditoria dos 805 passos dos 14 corredores: **zero constantes** enviam palavra onde a tela pede número. O defeito
  está nos **slots**, não nas constantes. Riscos adjacentes: `azul-auto/menu_atendimento` envia "1" sem fallback numa
  tela onde 1 pode ser "Cancelar serviço"; dois passos `complemento` homônimos em porto-auto (o primeiro vence sempre).
- **Humano na URA hoje:** o corredor continua e **digita de novo** a tecla que a pessoa digitou (17:18:14 humano,
  17:18:16 corredor). Numa tela de confirmação, confirma duas vezes.

### 1.7 A cobrança que "não funcionou" nunca foi ligada
- 📊 1 rotina no banco (Resulta), 2 execuções (10 e 11/09), `send_mode=test`, `team_number=""`, 14 envios todos ao
  número de teste, `billing_sent_log` **vazio**, rotina desligada em 11/09 14:15 sem registro. Zero dos 20 itens do
  roteiro de validação executados. Canário Q1–Q6 nunca rodou.
- **Causa 1 — o modo teste desliga o ledger, a dedup e a retenção** (`billing_collection.py:1058-1064, 1191, 403,
  2351`): 4 boletos seguidos para o mesmo CNPJ, os mesmos 7 nos dois dias, tela de Pendências vazia (correta e
  mentindo). Um controle que não pode falhar (§9.2).
- **Causa 2 — a configuração não vira real sem `team_number`/`confirmacao_cliente`**, e a mensagem de retenção não
  descreve o caso ("configuração antiga").
- **Causa 3 — texto:** `{nome_atendente}` nunca preenchido ("Aqui é a nossa equipe, da Resulta"); `{numero_parcela}` em
  dois formatos; metade dos portais não entrega (Allianz tela desconhecida, Mapfre `failed` sem motivo, Zurich vazio);
  PII em texto claro em `routine_runs.output_full`.

### 1.8 O que já está certo (para não refazer)
Português do agente é bom, empático, honesto quando falha (o guarda de honestidade impediu mentir sobre handoff em
2 de 2 falhas). O julgamento de pedir humano em sinistro foi correto. A janela de 7 dias, quando exercitada (4
conversas na Resulta), calou 4 de 4. As rotas de personalização e de cobrança usam o resolvedor canônico de tenant;
**nenhum P0 cross-tenant** nas 47 rotas varridas. A pausa por intervenção humana, o conserto do `@lid`, membros
ligarem o agente, dossiê humano e piso de tokens estão na main desde 09–10/09 e **ainda não foram exercitados** com
segurado real.

## 2. Como executar: a forma (minha recomendação, nota 0–100)

| forma | nota | por quê |
|---|---|---|
| **SPECs coesas por domínio de defeito, sob AAA opção B, uma por chat novo, na ordem de dependência** | **90** | Cada SPEC tem gate próprio e canário vivo; o painel julga código e dado; "genérico" não passa porque a régua é a conversa real. Sete SPECs médias, não uma gigante nem trinta minúsculas. |
| Um lote único "consertar tudo" | 35 | Perde detalhe (o que você temeu), e uma janela morta mata tudo. |
| Um a um, 40 pendências | 40 | 40 aquecimentos e 40 painéis: caro, lento, e os defeitos são interdependentes (o LID split afeta janela, handoff e exceções). |

**Numeração:** as SPECs de correção são a continuação natural da EXTRA-001 ("a operação dos pilotos"). Proponho
**EXTRA-001.1 … EXTRA-001.8** (o projeto já usa decimais: 094.1, 097.1), sem renumerar EXTRA-002 Agger → 010.
Decisão sua. Onde a EXTRA-008/009 (Quiver/Segfy) colide com a 101 (fábrica de conectores), a arbitragem também é sua.

## 3. Os blocos (cada um vira uma SPEC no próximo chat)

Ordem (revista em §12): **001.0 → 001.6-P0 → 001.1 → 001.2 → 001.3 ∥ 001.4 → 001.6 → 001.7 piloto medido → 001.10 vidros ∥ 001.5 → 001.8 → 001.9.**
Marcha: CRÍTICO onde muda o que o segurado ou o corretor lê; PADRÃO onde é motor; LEVE onde é tela.

### EXTRA-001.1 · A apólice certa, inteira, em uma rodada — CRÍTICO 💭 8–12h (v2: +porta `PolicyDataProvider`, §7.3)
Objetivo: pergunta sobre apólice/cobertura → resposta na primeira rodada, da apólice **vigente do ramo deduzido**, com
todas as coberturas, limites, franquias, prêmio, parcelas e plano, e origem escrita.
- Vigência e cancelamento filtrados **no conector** antes de `ambiguous_policy` (`infocap_connector.py:1315`): sobrou 1 →
  `found` com `auto_selected_reason` e `historico_oculto: N` (§9.5: a escolha diz por quê).
- Inferência de ramo para **todos os papéis**, lendo ficha + últimas mensagens, não só `user_query`; `chaveiro` nos
  dois regex; 2+ vigentes do mesmo ramo = única situação em que se pergunta.
- Retirar "liste TODAS" do briefing (`infocap_tool.py:404-412, :474`); `policy_options` = lista filtrada; guarda
  `nodes.py:263` só exige listar quando restam 2+ vigentes do mesmo ramo; `CORE_BASE_PROMPT` ganha a regra.
- Só apólices vencidas quando o corretor pedir histórico; sem nenhuma vigente: "a última vigente foi X, até dd/mm".
- PDF oficial lido **sempre** que a pergunta é de apólice (não por palavra); 3 últimas mensagens humanas para `core`.
- Reconciliação CORP × PDF por rótulo, origem por linha, **contador de prêmio** (Σ garantias ≠ `preliq` → sinal);
  ler `observacoes`, `sit_renovacao_txt`, `sit_sinistro_txt`, `tabela_itens`; `forma_pag` das parcelas.
- Teto no bloco de contexto recuperado + pergunta repetida depois do bloco (mata o "não recebi sua pergunta").
- Gate: golden com a apólice HDI da Saionara (10 coberturas, LMG, 4 parcelas cartão) e a Allianz condomínio (15):
  vermelho se voltar a entregar 6 de 10 ou listar vencidas; canário vivo no chat da Resulta.

### EXTRA-001.2 · O agente lê tudo antes de falar — CRÍTICO 💭 6–9h
Objetivo: rajada de 5 mensagens + foto → **uma** resposta (no máximo duas), sem pergunta repetida, sem cumprimento
no meio, com identidade certa.
- Trava de turno por conversa (`SET NX EX 90`); mensagem que chega com a trava tomada volta ao buffer.
- Janela adaptativa: 8 s com pontuação final · 18 s frase inacabada · 3 s dado curto; teto 25 s.
- Mídia entra no buffer; re-planejamento (reler o buffer antes de gerar; mesclar); presença "digitando…".
- Ficha guarda os **slots já respondidos** do corredor; guarda que fica vermelho se um slot preenchido for perguntado.
- Apresentação condicional ao reencontro (resolve o conflito prompt × religamento); hierarquia de tamanho (3 frases,
  exceto lista documental / bloco de 4 / AVISAR); identidade da thread fixada a cada assunto novo.
- Dedupe do espelho por `wa_message_id`; **uma conversa por contraparte** (LID × telefone) + migration/CHECK das 174
  fantasmas (P-PILOTO-13); ordem `pausar_ia` antes da lista de exceções; todo silêncio no feed com motivo.
- Nome do agente: escolha livre da corretora, trocável; a SPEC garante que nunca confunde (D-PILOTO-12, §7.4).
- Gate: corpus de 20 rajadas reais do acervo (10/12/22 s medidos) → 1 resposta; mutação "trava desligada" vermelha.

### EXTRA-001.3 · O grupo só recebe o que importa — CRÍTICO 💭 7–10h
Objetivo: o grupo de suporte recebe **só** pedido de ajuda do agente, sinistro, conclusão e o resumo das 19h; nunca
sobre conversa que um humano já conduz nem sobre número da casa; uma mensagem, inteira, clicável.
- Guarda única "humano já está nesta conversa" (assumida · humano falou ≤ N dias · número da casa) consultada por
  **todo** gatilho de grupo (re-alerta 6 h, espera vencida, deadline, dossiês). 📊 zera 58 de 58 do piloto.
- **Lista de números da casa** com efeito real: telefone em `company_members` + `company_internal_numbers` (fixo,
  comercial, sócios), no **card Equipe** (nota 88 × Agente 62 × card próprio 71), com sub-bloco "números que o agente
  nunca atende"; efeito: nunca responde · nunca entra na Fila · nunca vai ao grupo · captura marcada `interno`.
- `bloco_unico` nos três caminhos; espera vencida = 1 aviso; `ura_silent`/`human_silent` viram linha do resumo;
  queda de canal vai ao dono, não ao grupo; reabertura de caso não fura o marcador de 6 h.
- Os quatro modelos (texto no laudo I3 §3.5): **🆘 PRECISO DE AJUDA** (etapa · o que aconteceu · resumo em parágrafo ·
  seguradora com `wa.me` · ramo/serviço · nome · CPF/CNPJ · data/hora · WhatsApp do segurado clicável — sem link do
  painel, sem últimas mensagens), **🚨 NOVO SINISTRO** (tipo · dados · resumo em 1–2 parágrafos · pontos de atenção ·
  WhatsApp), **✅ ATENDIMENTO CONCLUÍDO** (curto), **📊 ATENDIMENTOS REALIZADOS** às 19h (concluídas · sinistros ·
  precisei de ajuda · **eficiência conforme D-PILOTO-13, §7.5**: sinistro conta como sucesso; sucesso = até a
  mensagem do acionamento ao segurado; pós-acionamento fora).
  Formato do link: `https://wa.me/55DDDNÚMERO` sem `+`, número como chega no `user_phone`.
- Todo envio ao grupo em `platform_sends` (hoje a pergunta "quantas saíram?" não tem resposta).
- Gate de ligar o agente: sem destino ativo + canal conectado, o botão recusa com frase humana.
- Segurança que apareceu no caminho: 6 mutações sem papel/origem (portal-credentials, whatsapp-channel,
  support-destinations) — padrão pronto no repo, nota 95, entra aqui.
- Gate: reprodução do dia 10/09 sobre o acervo → 7 mensagens viram 2 (1 pedido de ajuda + 1 conclusão); mutação
  "guarda desligada" vermelha; canário no grupo de teste.

### EXTRA-001.4 · O corredor não trava sozinho — CRÍTICO 💭 6–8h
Objetivo: menu numerado nunca recebe palavra; "opção inválida" é reparada pelo motor; o Cérebro sabe que foi
recusado; humano na URA coordena em vez de duplicar.
- Regra B: **nenhum slot `*_opcao` chega cru à URA** — derivação obrigatória palavra → dígito (`qual_seguro_opcao`
  primeiro), guarda por passo que fica vermelho para slot sem derivação (o guarda atual lê só as derivações que existem).
- Regra A: "opção inválida / não entendi + menu numerado pendente + nossa última resposta não era dígito → reenvia o
  dígito do rótulo mais próximo", determinística, antes do Sentinela, uma vez por tela, sem consumir tentativa.
- Cérebro recebe `ultima_resposta_recusada` + `tela_com_menu_pendente`; tentativas contadas **por tela**, não por sessão.
- Humano da corretora na URA — **opção C (D-PILOTO-10)**: pausa de **60 s** (📊 medido contra 56 encerramentos
  reais, §11.4; 90 s perde os dois piores casos), renovada automaticamente a cada envio real à seguradora,
  máximo 2 renovações sem saída; uma mensagem ao grupo
  ("assumo de volta em 90 s · responda AGENTE para seguir agora · EU CUIDO para eu sair deste acionamento"); sem
  resposta, retoma lendo a tela atual; enquanto o humano está lá, nenhum gatilho de grupo dispara. (A "parar 7 dias" 35;
  B "continuar como hoje" 62.)
- Riscos adjacentes: `azul-auto/menu_atendimento` "1" sem fallback; `complemento` homônimos em porto-auto.
- Regenerar corpus, régua, inventário e roteiro (P-PILOTO-06); Porto/Azul: schema do formulário no 1º acionamento real.
- **Humano da SEGURADORA na URA (v2, §11.3):** âncora positiva de entrada na fase humana; `needs_human` reentra em
  `human_phase` quando um humano se apresenta (o defeito da Vivian, 10/09); perguntar ao segurado e voltar;
  relógio de fila ≠ relógio de humano sumido; encerramento da Allianz reconhecido; atos do agente registrados
  (hoje 0 linhas em toda a base).
- Gate: replay do acervo Allianz 10/09 pelo motor → "1" no menu de três opções; mutação vermelha com "residência";
  replay da sessão da Vivian → o resumo do caso sai em ≤ 30 s.

### EXTRA-001.5 · O agente sabe o que cada plano cobre — CRÍTICO 💭 10–14h, trilho paralelo (v2: níveis de assistência §7.6; chave nossa, não do sistema de gestão, §7.3)
Objetivo: "o segurado X tem carro reserva? cobre granizo?" → sim / não / não contratado / **não sabemos ainda**, com
a origem escrita, para toda seguradora que a corretora usa.
- Tabela `insurer_assistance_plans` (seguradora · ramo · produto · plano · serviço · coberto · limites · carência ·
  condições · **documento-fonte e página obrigatórios** · vigência · confiança), migration expand-first.
- Skill única `cobertura_e_assistencia`: apólice vigente do ramo → PDF → produto/plano (`tabela_itens`, Benefícios,
  SUSEP) → linha da tabela → prosa das condições gerais no RAG global. Substitui `assistance_policy.py` (vira fallback).
- Três ondas: (1) extrair das 97 CGs já indexadas (8 seguradoras); (2) ligar apólice → CG pelo processo SUSEP (já
  casa hoje); (3) coletar as ~12 seguradoras ausentes de maior carteira (`/seguradoras` e `/ramos` da CorpAPI como
  catálogo), com `doc_kind='manual_de_assistencia'` novo. Manutenção pelo `content_hash` que o corpus já revisita.
- Meta declarada e medida: hoje 10 de 61 seguradoras com CG e 0 de 61 com plano estruturado; toda resposta diz em
  qual estado está. "Não sabemos ainda" não é falha; "a fonte não retornou" é.
- Gate: 30 perguntas reais do acervo (carro reserva, granizo, chaveiro, vidros…) com resposta e origem; mutação
  "linha sem fonte aceita" vermelha.

### EXTRA-001.6 · A cobrança prova que funciona — PADRÃO 💭 6–9h — **reescrita em §9.4 (v2); o texto abaixo é a versão da manhã**
- Modo teste que **pode falhar**: ledger, dedup e retenção por telefone valem em teste (com marca), Pendências mostra o
  que aconteceria; agrupar parcelas por segurado (1 mensagem, N boletos); `{nome_atendente}` vira campo da tela;
  `{numero_parcela}` num formato; mensagem de retenção que descreve o caso; registro de ligar/desligar rotina.
- Portais: Allianz (tela pós-login), Mapfre (`failed` sem motivo), Zurich (200 vazio) com motivo legível.
- PII fora de `routine_runs.output_full`; canário Q1–Q6 no implantado; roteiro das atendentes executado.
- Gate: rotina da Resulta em modo **equipe** com `team_number` real (TESTE-B) → 3 mensagens; segunda execução → 0.

### EXTRA-001.7 · O piloto medido (não é código; é protocolo de operação) — LEVE
- Checklist de ligar (`/health` limpo, destino ativo, canal conectado, números da casa cadastrados, exceções só de teste).
- 3 dias inteiros com o agente ligado nas duas corretoras; medição diária automática: conversas atendidas, rajadas
  coalescidas, apólice certa em 1 rodada, acionamentos com protocolo, handoffs entregues, mensagens ao grupo por tipo,
  silêncios por motivo. Régua por dimensão publicada no dossiê. Só depois disso as notas de §0 deixam de ser palpite.

### EXTRA-001.8 · Uma corretora não trava a outra — CRÍTICO 💭 8–12h (P-PILOTO-01)
- Isolamento por tenant: fila/worker por corretora ou processos múltiplos, timeout e retry no modelo, backpressure,
  prova com duas corretoras e uma travada. Meta sua: ≥4 simultâneos por corretora, zero interferência.

### EXTRA-001.9 · O painel diz de quem é (rotas de Personalização) — LEVE, junto com a SPEC de painel
- Mover `agentes/even → corretora/agente-de-atendimento`, `equipe`, `conhecimento`, `custos` para `corretora/`, com
  redirects e um guarda que casa todo `href` interno contra a tabela de rotas (o `rotas-montam` não valida links);
  limpar "Even" da tela Prontidão. Nota: mover agora 34; junto com a SPEC de painel 88; não mover 55.

## 4. Decisões que só você toma — **decididas em 12/09, ver §7.1** (itens 8 e 9 ainda abertos)
1. Numeração: EXTRA-001.1…001.9 (recomendo) ou renumerar a família.
2. Lista de números da casa no **card Equipe** (recomendo) × card Agente × card próprio.
3. Humano na URA: **opção C** (90 s + AGENTE / EU CUIDO) — recomendo.
4. Fonte de verdade: PDF para coberturas/franquias/plano; CORP para parcelas/status — recomendo.
5. Nome do agente da Resulta ("Amanda" hoje) × identidade da atendente.
6. Eficiência do resumo diário = concluídas sozinho ÷ (concluídas + precisei de ajuda), sinistro fora — recomendo.
7. Janela do grupo = mesma janela de 7 dias do atendimento (uma regra só) — recomendo.
8. EXTRA-008/009 (Quiver/Segfy) × SPEC-101: qual número vence.
9. As cinco entregas de 08–10/09 que entraram na main sem SPEC (plano de pilotos, handoff/pausa, InfoCap, tokens,
   exceções) viram uma SPEC retroativa "EXTRA-001.0" com relatório, ou uma decisão registrada de que ficam como estão.

## 5. Pendências que este plano absorve
P-PILOTO-01 (→001.8) · 02, 03 (→ painel/001.3) · 04 (checklist sinistro/empresarial/condomínio → 001.3 dossiê de
sinistro + 001.5) · 05, 06 (→001.4) · 07, 08 (portal, mantêm) · 11 (→001.6) · 12 (→001.3) · 13, 15 (→001.2) ·
16, 17, 18 (→001.2/001.1) · 19 (🧑) · 20 (→001.1) · P-E001-* de canário (→001.6).

## 6. O que faltou nesta auditoria (resolvido em v2)
A mensagem de 12/09 chegou cortada em 50 mil caracteres. A parte restante foi reenviada e está tratada em §7–§11.

## 7. Segunda leitura (12/09, tarde): a parte cortada da mensagem e as decisões do Founder

A parte que faltava chegou. Ela trazia quatro assuntos que o plano da manhã não cobria ou cobria de raspão:
**leitura reforçada do PDF e os três níveis de pacote de assistência por seguradora**, **o humano da seguradora
que entra na URA**, **o portal de vidros com o material novo da Regina**, e **a cobrança em profundidade**
(mesmos boletos dois dias seguidos, mensagem picotada, Allianz e Mapfre sem entrar). Os quatro foram investigados
à tarde (laudos I5 vidros, I6 cobrança, I7 humano na URA) e entram abaixo. As decisões que você tomou ficam
registradas aqui e vão para `FOUNDER-DECISIONS.md` como D-PILOTO-08…14 quando a primeira SPEC abrir.

### 7.1 As decisões, e como cada uma muda o plano

| # | decisão sua | efeito no plano |
|---|---|---|
| D-PILOTO-08 | Numeração **EXTRA-001.1 … 001.9** mantida; blocos novos continuam a sequência (001.10, 001.11). | Nada renumera. EXTRA-002…010 ficam como estão. |
| D-PILOTO-09 | Lista de números da casa no **card Equipe**. | 001.3 fecha assim. |
| D-PILOTO-10 | Humano da corretora na URA: **opção C**, desde que o tempo caiba nos timeouts das seguradoras. | 001.4 ganha a medição dos timeouts reais (I7 §4) e o valor final sai medido, não chutado. |
| D-PILOTO-11 | Fonte de verdade **PDF para cobertura/franquia/plano, CORP para parcela/status**, mas **a arquitetura não pode nascer presa à InfoCap**: Quiver, Agger, Segfy entram por adaptador, e o agente **não depende** da lista de seguradoras/ramos do sistema de gestão. | 001.1 e 001.5 passam a exigir a **porta `PolicyDataProvider`** (§7.3). |
| D-PILOTO-12 | **Nome do agente é escolha livre da corretora**, trocável a qualquer hora; "Amanda" na Resulta é escolha da Saionara e fica. | 001.2 muda: não é "decidir o nome", é **garantir que o nome escolhido nunca confunda** (§7.4). |
| D-PILOTO-13 | Eficiência do resumo das 19h: **sinistro conta como sucesso**; sucesso = **até enviar ao segurado a mensagem do acionamento** (protocolo, link ou agendamento); pós-acionamento fora. | 001.3 muda a fórmula (§7.5). Uma objeção minha registrada lá. |
| D-PILOTO-14 | Execuções de **alta qualidade sem serem exorbitantemente longas**. | §8: AAA opção B na execução, laço leve na criação das SPECs, orçamento de tokens por SPEC. |

**13/09:** D-PILOTO-15 = SIM (001.0 existe); D-PILOTO-16, 17, 18, 19 e 20 decididas por delegação e registradas em
`FOUNDER-DECISIONS.md` (SPEC-101 = porta e EXTRA-002/008/009 = adaptadores; Bradesco pela captura dupla; cobrança em
`equipe`, N = 7 dias, reativar só depois do BLOCO 0 da 001.6; senhas na segunda não travam; criação neste chat, execução em chat novo).

### 7.2 Os dois itens que você não entendeu, explicados

**"Janela do grupo = mesma janela de 7 dias" (item 7 da §4).** Hoje o atendimento tem uma regra só para calar o
agente: *se um humano da corretora falou nesta conversa nos últimos N dias (N=7, ajustável por corretora), o
agente não responde* — a "última palavra humana manda". O que eu propus é que **o grupo de suporte use a mesma
régua**: se um humano falou naquela conversa nos últimos 7 dias, **nenhum aviso automático sobre ela vai ao grupo**
(nem re-alerta de 6 h, nem "espera vencida", nem dossiê). É o que zeraria as 58 mensagens do piloto, porque todas
eram sobre conversas que a Regina ou a Saionara já conduziam. A alternativa seria criar um segundo número (por
exemplo "grupo só cala por 24 h") — duas réguas para o mesmo fato, duas telas para configurar, e o atendente
precisando saber qual vale onde. **Uma regra, um número, um lugar para mudar.** Se um dia 7 dias for demais para o
grupo, muda-se o número da corretora, não a regra.

**"Cinco entregas sem SPEC → 001.0" (item 9 da §4).** Entre 08 e 10/09 cinco pacotes de código entraram na `main`
**sem SPEC, sem painel e sem relatório**, por sua ordem ("execute o essencial sem AAA"): o plano de ajustes dos
pilotos (mídia 16 MB, pausa por intervenção, rajadas em paralelo), o plano handoff+pausa (grupos por corretora,
janela de 7 dias, membros ligam o agente), a apólice item a item (InfoCap `/itens` + PDF), a resposta inteira
(piso de 8192 tokens + continuação) e as exceções da janela (números de teste). Eles **funcionam** (têm testes e
foram implantados), mas o canon não sabe que existem: `ESTADO-DAS-SPECS.md` não os lista, não há EXECUTION CARD,
não há relatório com "o que ficou de fora". A proposta "001.0" é **uma SPEC retroativa e curta** (💭 1–2 h, sem
código): um relatório que descreve os cinco pacotes, os testes que os guardam, os riscos que deixaram (P-PILOTO-*),
e os registra em `ESTADO-DAS-SPECS.md`. A alternativa é uma linha em `FOUNDER-DECISIONS.md` dizendo "ficam como
estão, documentados nos planos de 08 e 09/09". **Recomendo a 001.0** (nota 82 × 60): daqui a um mês ninguém vai
lembrar por que o webhook tem um `to_thread` ou por que existe `JANELA_SILENCIO_EXCECOES`, e a SPEC que mexer ali
vai precisar dessa história.

### 7.3 A arquitetura que não nasce presa à InfoCap (entra em 001.1 e 001.5)

Hoje a apólice chega ao agente por um caminho só: `infocap_tool.py` → `infocap_connector.py` → CorpAPI. A tool
conhece campos da InfoCap (`sit_renovacao_txt`, `tabela_itens`, `preliq`) e o prompt sabe que "a InfoCap" existe.
Se amanhã a AutoFleet migrar para Quiver, tudo isso se refaz.

O que as SPECs 001.1 e 001.5 passam a exigir:

- **Uma porta, `PolicyDataProvider`** (Python `Protocol`, em `backend/app/services/policy_provider/`), com cinco
  operações e um modelo canônico de saída: `buscar_cliente(doc|telefone|nome)`, `listar_apolices(cliente)`,
  `detalhar_apolice(id)` (itens, garantias, LMI, franquia, prêmio, parcelas, plano de assistência), `documento_oficial(id)`
  (bytes do PDF ou `None`), `parcelas_em_aberto(cliente)`. O modelo canônico (`Apolice`, `Cobertura`, `Parcela`,
  `PlanoDeAssistencia`) é **nosso**, com `origem` por campo (`corp`, `pdf`, `manual`) e `confianca`.
- **InfoCap vira o primeiro adaptador** (`InfoCapProvider`), envolvendo o conector que já existe. Nada é reescrito;
  o conector só deixa de ser chamado direto pela tool. Quiver, Agger (EXTRA-002) e Segfy entram como adaptadores
  novos, cada um com o seu corpus de telas/contratos. A SPEC-101 (fábrica de conectores) é onde a porta mora; as
  EXTRA-00x são adaptadores dela (**D-PILOTO-16, minha recomendação**).
- **A tool do agente e os prompts falam só com a porta.** Nenhum nome de sistema de gestão em prompt de produto;
  o briefing diz "sistema de gestão da corretora" e a origem escrita na resposta diz "apólice (PDF oficial)" ou
  "sistema de gestão". Guarda: teste que falha se `infocap`/`corpapi` aparecer em `core/prompts.py` ou nos textos
  de resposta.
- **Seguradoras e ramos são catálogo nosso**, não do sistema de gestão: a tabela de seguradoras (SUSEP como chave)
  e a de ramos ficam no AutoBrokers; o adaptador **mapeia** o código da InfoCap/Quiver para o nosso. A base de
  produtos e assistências (001.5) pendura na nossa chave, então ela vale para qualquer corretora com qualquer
  sistema, e uma corretora **sem** sistema de gestão (só PDFs) também é atendida: `PdfOnlyProvider` é o adaptador
  mínimo, e é ele que garante que o PDF é lido **sempre**, não só quando a CORP falha.
- **Reconciliação é da porta, não do adaptador**: `reconciliar(apolice_corp, apolice_pdf)` casa cobertura por
  rótulo normalizado, marca divergência, e o contador de prêmio (Σ garantias ≠ prêmio líquido) vira sinal de
  "o sistema de gestão está incompleto" — foi assim que descobrimos os 23%.

Custo: 💭 +2–3 h na 001.1 (a porta e o adaptador InfoCap) e zero na 001.5 (ela já nasce na chave nossa).
Nota da alternativa "deixa preso na InfoCap e refatora depois": 30 — refatorar depois custa a 001.5 inteira de novo.

### 7.4 O nome do agente: livre, trocável, e nunca confunde (entra em 001.2)

A regra vira produto: **a corretora escolhe o nome no card Agente** (já existe `agent_name`; hoje "Amanda" na Resulta,
"AutoFleet Assistente" na AutoFleet). O que a 001.2 garante, com guardas:

1. **A apresentação usa o nome escolhido** e diz que é assistente virtual da corretora, uma vez por assunto, nunca
   no meio de uma rajada, nunca no reencontro dentro da janela.
2. **Especialista = a atendente**: quando o agente diz "vou passar para a especialista", nomeia a atendente real
   (nome vem do card Equipe, de quem está de plantão), nunca o próprio nome.
3. **Trocar o nome não muda conversa em andamento**: a thread guarda o nome com que se apresentou; se mudar, o
   agente se reapresenta na próxima abertura de assunto ("agora me chamo X").
4. **Nome de agente não pode coincidir com nome de membro da equipe** — o card recusa com frase humana (é o único
   jeito de "Amanda, a assistente" e "Amanda, a atendente" não se confundirem no grupo e no dossiê).
5. Nos dossiês ao grupo, o agente assina sempre "🤖 agente" e a atendente aparece pelo nome — nunca o contrário.

### 7.5 Eficiência do resumo das 19h, com a sua definição (entra em 001.3)

Sua definição: **sucesso = o agente conduziu até enviar ao segurado a mensagem do acionamento** (protocolo, link ou
agendamento); **sinistro conta como sucesso** quando a coleta inicial foi feita e o dossiê saiu; pós-acionamento não
entra. Fórmula:

```
eficiência = (acionamentos com mensagem enviada + sinistros com dossiê entregue)
             ÷ (esses + atendimentos em que o agente pediu ajuda)
```

Fora do numerador e do denominador: conversas só de dúvida (sem acionamento), conversas que um humano já conduzia,
pós-acionamento, e as que caíram na janela. Cada uma dessas aparece no resumo como contagem própria ("12 dúvidas
respondidas · 3 já com a Regina"), para o número não esconder o volume.

**Minha objeção, registrada:** "pediu ajuda" tem dois casos que a fórmula trata igual. (a) O agente pediu ajuda
porque **não conseguiu** (URA travou, faltou dado) — é falha dele. (b) O agente pediu ajuda porque **a regra manda**
(sinistro com vítima, segurado pediu humano, valor acima do limite) — é acerto. Se os dois contam contra, o número
pune o agente por obedecer. Proposta: o dossiê **PRECISO DE AJUDA** já carrega `motivo`; a fórmula conta contra só
os motivos de incapacidade (`ura_travou`, `dado_faltante`, `sentinela_esgotou`); os motivos de regra ficam fora do
denominador e aparecem como "3 passados por regra". Nota da fórmula pura: 70; com a distinção: 88. Decisão sua.

### 7.6 Os três níveis de assistência por seguradora (reforça a 001.5)

Você deu o exemplo certo: a HDI tem "Assistência Essencial", e acima dela outros pacotes; o agente hoje não sabe
**qual** o segurado contratou nem o que cada um cobre, e responde genérico. A 001.5 passa a exigir explicitamente:

- `insurer_assistance_plans` tem a coluna **`nivel`** (1..N dentro do produto) além de `plano`, e a tabela de
  serviços por plano diz, por serviço, **limite** (km de guincho, dias de carro reserva, nº de acionamentos/ano),
  **carência** e **condição** ("só em caso de sinistro coberto").
- A apólice carrega o plano contratado (`tabela_itens` / linha "Assistência" do PDF) e o adaptador (§7.3) normaliza
  para a nossa chave `seguradora+produto+plano`.
- A resposta ao segurado diz o nível: "o seu plano é o Essencial da HDI: guincho até 200 km, sem carro reserva. O
  plano acima (Completo) teria carro reserva por 7 dias — a Regina pode orçar a troca na renovação." Esta última
  frase é o gancho comercial que você pediu no pós-acionamento, e só aparece se o plano superior existir na tabela.
- Onda 1 cobre as seguradoras que as duas corretoras mais usam (medir pela carteira InfoCap: Allianz, HDI, Porto,
  Yelum, Azul, Tokio, Bradesco, Mapfre, Zurich), com os três níveis de cada uma extraídos das condições gerais e do
  manual de assistência; a cada linha, **documento e página**.

## 8. O processo: quem escreve as SPECs, quem executa, e quanto custa

Sua pergunta tinha três partes: **quem escreve** (eu, que tenho tudo na cabeça, ou um chat novo), **AAA na criação**
(ou um laço mais simples) e **tokens** (não acabar antes da 001.9). Opções com nota:

| forma | nota | por quê |
|---|---|---|
| **A. Eu (este chat) escrevo as propostas de SPEC; cada SPEC é executada por um chat novo sob AAA opção B** | **91** | O contexto está aqui (4 laudos da manhã, 3 da tarde, decisões, linhas de código). Um chat novo gastaria 150–250k tokens só para reconstruir isso, por SPEC. A execução em chat novo é o rito que já funciona (EXTRA-001, 097…). |
| B. Chat novo escreve e executa cada SPEC | 55 | Reconstrução do contexto onze vezes; e o redator perde as decisões que só estão nesta conversa. |
| C. Eu escrevo e eu executo aqui | 40 | Este chat já está em ~40% de uso e uma execução AAA custa 1–2 M tokens; morreria na 001.3. |

**AAA na criação: não.** O protocolo AAA é desenhado para **execução** (painel julga código e dado; gate é teste
verde e canário). Para **escrever** uma proposta o que se precisa é: um investigador quando a proposta afirma algo
que ainda não foi medido, e **um revisor** que leia a proposta pronta com três perguntas (está completo? tem prova
com linha? o gate é verificável?). É o laço leve que usei nas propostas 097/098 e na EXTRA-001, e as execuções delas
não sofreram. Laço por SPEC:

```
1. eu escrevo a proposta (arquivo em docs/canon/specs-propostas/, no padrão SPEC-EXTRA-001)
2. um revisor Opus (read-only) devolve até 10 achados: lacuna · afirmação sem prova · gate não verificável
3. eu emendo; se um achado exigir medição nova, um investigador Opus de escopo fechado
4. você lê o resumo de 15 linhas no chat e diz "vai" — ou não
```

**Tokens (💭 estimativa por proposta, neste chat):** proposta 25–40k · revisor 60–100k (é ele quem lê o código) ·
emendas 10–15k. Onze propostas ≈ **1,1–1,7 M tokens**. Este chat tem folga para isso **desde que eu não execute
nada aqui** e não reabra investigações longas. Ordem de escrita = ordem de execução, para que, se o chat acabar
antes, o que falta seja o que vem por último (001.9 e 001.10, as mais leves). Se o chat cair antes de terminar,
o próximo chat lê este documento + as propostas já escritas e continua — por isso cada proposta é um arquivo
fechado, não um rascunho.

**O que cada chat executor recebe** (o pacote, nunca o canon): a proposta, o RESEARCH-PACK (os trechos dos laudos
I1–I7 que a SPEC usa, com as linhas), o `PROMPT-DE-ABERTURA` preenchido, e o card de execução com marcha
(CRÍTICO/PADRÃO/LEVE) e N de juízes. **Marcha por SPEC**, já fixada aqui para ninguém rediscutir:

| SPEC | marcha | juízes | por quê |
|---|---|---|---|
| 001.1 apólice certa | CRÍTICO | 3 | muda o que o corretor lê sobre dinheiro do cliente |
| 001.2 lê tudo antes de falar | CRÍTICO | 3 | muda cada resposta ao segurado |
| 001.3 grupo só o que importa | CRÍTICO | 3 | é o que a Regina e a Saionara veem o dia inteiro |
| 001.4 corredor não trava | CRÍTICO | 3 | é o acionamento em si |
| 001.5 base de produtos | PADRÃO | 2 | motor + dado; o gate é a tabela com fonte |
| 001.6 cobrança provada | PADRÃO | 2 | motor; o canário é o gate real |
| 001.7 piloto medido | LEVE | 1 | protocolo de operação, não código |
| 001.8 isolamento | CRÍTICO | 3 | infraestrutura que pode derrubar as duas corretoras |
| 001.9 rotas do painel | LEVE | 1 | tela |
| 001.10 portal de vidros ponta a ponta | CRÍTICO | 3 | efeito material em portal de seguradora |
| 001.0 retroativa | LEVE | 1 | relatório |

"Alta qualidade sem ser exorbitante" na prática: **o painel custa 4% do relógio; a bateria de testes custa 50%**
(medido, CLAUDE.md §2). O corte é na bateria: cada SPEC declara **no máximo 12 guardas novos**, todos sobre o motor
e o acervo real (§9.4), e proíbe teste que reimplementa a regra. Uma SPEC CRÍTICA cabe em 💭 6–10 h de relógio
e 1,2–2 M tokens no chat executor; PADRÃO 4–6 h; LEVE 1–2 h.

## 9. A cobrança, em profundidade (laudo I6, 13/09 — substitui a §1.7 e o bloco 001.6 da manhã)

### 9.1 O achado que reordena o bloco

📊 **Allianz e Mapfre não falharam por fragilidade de navegação: as duas senhas foram recusadas pelo portal.** O
investigador baixou os prints de desfecho dos jobs de 11/09 (`portal-evidence/{job}/00-desfecho-*.jpg`) e leu as telas:

| portal | o que a tela real diz | o que o sistema disse |
|---|---|---|
| Allianz | **"Acesso negado — Por favor, valide os dados introduzidos."** | `needs_human` · "tela pós-login não reconhecida" |
| Mapfre | **"Autenticação inválida!"** | `failed`, sem motivo |

A Allianz está assim **desde 18/08** (último `done` em 17/08; 34 `needs_human` acumulados; a sessão em
`portal_sessions` tem `verified_at=17/08` e `health='ok'` congelado, porque só se grava no sucesso). A Mapfre
**nunca funcionou** (2 jobs na história, os dois `failed`, 1 commit). Renovar as duas senhas é 🧑 sua, hoje;
a robustez de navegação é 🤖, depois — e a estrutura **não é uniformemente frágil**: Tokio, HDI e Yelum entraram
os dois dias; Zurich entrou e **reteve corretamente** (API devolveu vazio e ela recusou afirmar "está em dia").

### 9.2 Os defeitos, cada um com linha

| defeito | causa | linha |
|---|---|---|
| **Mesmos boletos dois dias** | em `test` a dedup é desligada por desenho (17/08) e o ledger não é lido nem gravado; `billing_sent_log` tem **0 linhas na história do banco** — o modo real nunca rodou | `billing_collection.py:1059-1065, 1178-1181, 1207-1215` |
| **4 mensagens ao mesmo CNPJ** | não existe chave por segurado em lugar nenhum: a fila filtra por boleto/vencimento/telefone e o laço itera parcela a parcela; não há "já cobrei este cliente esta semana" nem agrupamento | `fila_de_cobranca:362-441`, `ordenar_para_entrega:334-348`, laço `:1542` |
| **Mensagem picotada** | toda a cobrança passa por `send_message` sem `bloco_unico=True`, e o serviço quebra a cada ~300 caracteres em até 4 balões. 📊 O template de teste (525 ch) vira **3 balões + PDF = 4 mensagens por parcela**: em 10–11/09 saíram **≈28 mensagens por dia**, 16 delas sobre o mesmo segurado. Em `equipe` o desenho promete 3 e entregaria 5 | `billing_collection.py:1191`, `platform_outbound.py:1477`, `whatsapp/balloons.py:18-20` |
| **Governador subestima 4×** | grava 1 linha em `platform_sends` por parcela; o canal recebeu 4 | `billing_collection.py:1253-1262` |
| **"Aqui é a nossa equipe, da Resulta"** | `attendant_name` vazio no config → default "nossa equipe"; nenhum blocker avisa | `normalize_billing_config:502` |
| **Allianz "mente"** | a frase real "Acesso negado / valide os dados" **não está** na lista `_FAIL` de 7 frases; cai no fallback "tela pós-login não reconhecida". O teste consagra o erro: exercita a frase inventada "Usuario ou senha invalida" e afirma que tela de login é `needs_human` | `allianz_corretor.py:659-667, :704`; `tests/test_spec023_allianz_login.py:114, 120-121` |
| **Allianz: rede de segurança inalcançável** | `cobranca_sweep` retorna no `login_check` falho; o diagnóstico de sessão morta + relogin fresco mora **depois** e nunca executa | `allianz_corretor.py:3757-3759` vs `:3782-3796` |
| **`session_reused` mente** | grava `True` ao **injetar** o storage, não quando ele vale | `worker.py:812` |
| **Mapfre `failed` sem motivo** | a journey escreveu o motivo em `evidence.message`; o worker zera `error` e o relatório lê `error` — a linha vizinha (`needs_human`) lê `evidence.message` e funciona | `worker.py:944`, `billing_collection.py:2331` vs `:2329` |
| **Sessão nunca expira** | `verified_at` existe e nunca é comparado com o relógio; `portal_accounts.health` nasce `unknown` e **ninguém escreve** | `worker.py:271-304`, `app/api/portal.py:165` |
| **Sem retry/backoff/breaker/canário** | `attempts` incrementado e nunca lido; `available_at` lido e nunca escrito; zero `circuit`; `login_check` existe nos 6 portais e **nenhum produtor o enfileira**; watchdog de portal só olha vidros | `worker.py:1017, 1001`; `journeys/__init__.py:205-226`; `vigia_do_portal.py:306` |
| **Prova que ninguém abre** | o screenshot de desfecho é capturado e sobe; ninguém vê — o investigador foi o primeiro a abrir, 2 dias depois. A `tela_cega` da SPEC-087 só tem escritor da URA e **não tem leitor** (P-264) | `worker.py:884` |
| **PII na prova (P2 novo)** | o print da Mapfre grava o CPF do corretor em claro no bucket privado; `redaction.py` cobre o JSON, não a imagem | — |

📊 Fragilidade medida por journey (seletores por atributo/classe : por texto/papel · pontos de API):
Yelum 1:1 · 11 API · ✅ — Zurich 11:3 · 11 API · ✅ — Mapfre 6:3 · 8 API (login é DOM) — Tokio 7:2 · **0 API** · ✅ por
markup estável — HDI 4:0 — **Allianz 38:5 · 0 API · a mais frágil**. O que separa quem funciona de quem quebra é
API-first × DOM puro.

**Nota 0–100 do auxiliar nos dois dias: 36** (encontra inadimplentes 45 · pacote certo 40 · não repete 25 · portais
entram 30 · falha fala português 40). O motor difícil está bom (reserva atômica antes do efeito, retenção honesta da
Zurich, PDF como documento); **o que falha é tudo entre o motor e o humano**.

### 9.3 O que o estado da arte faz, e o que já existe aqui

Nada pede motor novo (§5 do CLAUDE.md): tudo cabe em `portal_jobs` + `portal_sessions` + `portal_accounts`.

1. **Health-check de sessão antes do trabalho** (o "setup project" do Playwright): a peça existe (`login_check` nos 6
   portais); falta o agendador que enfileira 6 jobs 30 min antes da rotina.
2. **TTL de sessão + `health` que muda** (`expired`/`fail` no primeiro insucesso).
3. **Seletores por papel/texto** (`getByRole`, `getByLabel`) — Allianz é a candidata (38:5).
4. **API-first onde há BFF** — Tokio e Allianz ainda são DOM puro.
5. **Retry com backoff + jitter e teto baixo** (entrada repetida bloqueia conta) — `available_at` já está na tabela.
6. **Circuit breaker por portal** — a Allianz gastou 100 s/dia por 25 dias para produzir a mesma linha.
7. **Tela desconhecida → screenshot + DOM → fila com leitor** — metade existe (o print); falta o DOM, a fila e alguém ver.
8. **Observabilidade por portal** na Central de Agentes: última verificação, taxa de sucesso 7 d, motivo da última falha.
9. **Credencial recusada é classe própria**, nunca "erro desconhecido" — porque a ação é humana e imediata.

### 9.4 EXTRA-001.6 reescrita · A cobrança prova que funciona — PADRÃO 💭 6–9h

Objetivo: a rotina roda em `equipe`, a atendente recebe **uma mensagem inteira por segurado** com N boletos, nunca o
mesmo boleto duas vezes, nunca o mesmo segurado mais de 1× por N dias; cada portal diz em português por que não
entrou; credencial recusada chega ao dono no mesmo dia.

- **P0 (2 linhas + 1 lista):** `bloco_unico=True` nos dois envios (`:1191`, `:1477`) e na nota interna; `:2331` lê
  `evidence.message`; "Acesso negado"/"valide os dados" entram em `_FAIL` da Allianz e o teste passa a exercitar o
  texto do acervo (`portal-evidence`), não frase inventada; varrer as 6 journeys rodando `interpret_login` contra os
  prints reais já guardados (§9.4 do CLAUDE.md: medir com a ferramenta que vai usar); blocker quando
  `attendant_name` está vazio.
- **Dedup por parcela sempre, inclusive em teste** (gravada com `send_mode='test'`), com a flag invertida: ela passa
  a **desligar** num dia de demonstração, não a ligar.
- **Agrupar por segurado**: `agrupar_por_segurado` entre `fila_de_cobranca:441` e `ordenar_para_entrega:334`
  (chave `cpf_cnpj`, fallback `cliente_nome|portal`); a reserva continua por parcela (`:1583`); 📊 4 envios ao mesmo
  CNPJ viram 1 mensagem + 4 PDFs.
- **"Não cobrar o mesmo segurado mais de 1× por N dias"** (N na tela, sugestão 7): `billing_sent_log` ganha a coluna
  `cpf_cnpj` (hoje não grava).
- **Sessão que expira**: TTL sobre `verified_at`; `health` marcado `expired` no primeiro `needs_human`/`failed` de
  login; `session_reused` passa a dizer a verdade (ou muda de nome — §12.1: nome errado reinfecta); Allianz move o
  diagnóstico de sessão morta para antes do `return` de `:3759`.
- **Canário diário de login** para os 6 portais antes da rotina; `available_at` + backoff; circuit breaker por portal
  após N falhas seguidas; `portal_accounts.health` escrito e mostrado na Central de Agentes.
- **Prova com leitor**: fila de telas desconhecidas de portal (print + DOM + hash), irmã da `tela_cega` da URA — e
  a SPEC só a cria **junto com o leitor** (a da URA tem escritor e não tem leitor, P-264). Redigir o print antes de
  subir (CPF do corretor em claro hoje).
- Governador conta balões reais; PII fora de `routine_runs.output_full`; canário Q1–Q6 no implantado; roteiro das
  atendentes executado.
- **Gate:** (1) teste que afirma 1 balão para o template real e consegue falhar; (2) `failed` com `error=NULL` e
  `evidence.message` preenchido → motivo aparece; (3) rotina da Resulta em `test` com dedup ligada, duas execuções →
  segunda = 0 envios; (4) em `equipe` com `team_number` real (TESTE-B): 1 mensagem por segurado + N PDFs;
  (5) `interpret_login` das 6 journeys contra os prints do acervo → nenhuma "tela não reconhecida" para tela de
  credencial recusada.

**🧑 O que só você faz, e bloqueia o resto (ordem):** renovar a senha da Allianz e a da Mapfre → reativar a rotina
(hoje `is_active=false`, `next_run_at=14/09`) → preencher o nome da atendente e o `team_number` (vazio; sem ele
`normalize_billing_config:471-476` retém a rotina inteira) → decidir `equipe` × `cliente` (`cliente` exige ainda
`confirmacao_cliente=true` e telefone com `contact_status` aceito; 📊 2 dos 7 inadimplentes estão sem telefone e
seriam retidos como tarefa da equipe) → dizer o N de "1 cobrança por segurado a cada N dias".

## 10. O portal de vidros com o material novo (laudo I5, 13/09 — bloco novo EXTRA-001.10)

### 10.1 O que o material que você depositou contém

📊 Lido em 13/09 (HAR por script de leitura, HTML, .docx por XML; PII mascarada, nada copiado):

| pasta | o que é | até onde vai |
|---|---|---|
| `YELUM/YELUM 1` (09/09) | HAR de 354 entradas (65 ao `api.autoglass`, 35 úteis, **7 de escrita**), 2 HTML (passo 3 e **tela final 100 %** com nº do atendimento, franquia e loja), 4 prints (2 são o mesmo arquivo), e **o bundle JavaScript inteiro do portal** | 🟢 **ponta a ponta — mas do ramo LATARIA/MARTELINHO**, que é o ramo que **não tem agendamento** (a seguradora indica a loja) |
| `YELUM VIDROS ANTIGO` (14–15/08) | HAR de 378 entradas (93 ao api, **14 de escrita**), 5 HTML (passo 3, 5, 80 %, **99 % com a lista de lojas**, cancelado), 3 PDFs só imagem | 🟡 vidro de porta até **um clique do fim**: lojas com distância, calendário com dias, grade de horários devolveu `Blocos: []` e a Regina cancelou. **O POST que confirma o agendamento nunca saiu** |
| `PORTO` (15/08) | 2 HAR: lanterna (abandonado no 80 %) e roda **sem cobertura** (a apólice não tinha a cláusula: 400 do portal, nenhum atendimento nasceu) | incompletos de propósito; provam o seletor exclusivo da Porto e o preflight |
| `PERGUNTAS QUE HUMANO FAZ….docx` | 64 parágrafos, 8 blocos de dano | transcrito e cruzado abaixo |

Sem vídeo; sem upload de foto (zero requisições a `vistoria.mobi`); o link de vistoria a Regina cola à mão.

### 10.2 O que o material ensina que o código não sabe

1. 🔴 **O robô nunca envia o `PATCH /atendimentos`** que grava peça, causa, cidade e local. `vidros_apifirst.py:23` documenta o passo; nenhum código o executa (`SessaoVidros` tem 9 métodos, nenhum `atualizar_atendimento`). Sem ele o questionário do portal não tem como nascer (ele deriva do `CodigoItemCoberto` que só o PATCH grava). **O caminho API-first, como está, não pode funcionar.**
2. 🔴 **A fronteira do efeito material muda de lugar por categoria**: para vidraçaria o pedido nasce no `POST /questionarios`; para lataria, **no próprio `PATCH`** (o passo 4 nem é carregado). `vidros_estado.py:233` fixa uma fronteira só — para lataria ela armaria no lugar errado, e é a receita de um segundo atendimento pago no nome do mesmo segurado.
3. 🔴 **O bundle do portal entrega o contrato do que falta** — todos ainda CANDIDATOS (SPEC-077), nenhum exercido em HAR: `POST agendamentos` (loja própria: cliente, data, horário, produto, tempos), `POST direcionamentos` (loja credenciada), `POST agendamentos/encaixes`, **`POST atendimentos-fotografias/web` (multipart — o anexo de fotos)**, `GET atendimentos/vistoriamobile?telefone=` (**gera o link de vistoria que a Regina cola à mão**), `PATCH atendimentos/finalizar`, e todo o subfluxo de domicílio (`transportes-proprios/*`, `servicos-moveis/ordens-servicos`, formas de pagamento).
4. 📊 **17 endpoints apareceram nos HAR e não existem no código** (lojas, distâncias, datas, horários, livre escolha, limites, colas rápidas, consulta de CEP, vistoria prévia, comprovante…), e **8 constantes de endpoint declaradas em `vidros_api.py` nunca são chamadas** (solicitantes, corretores, UFs, cidades, abandonar, cancelar): o robô não cadastra solicitante, não escolhe cidade e não sabe desistir.
5. **Porto e Yelum são a mesma SPA e a mesma API** (`abraseuatendimento` → `api.autoglass`): a única diferença medida é a Porto enviar `TipoAtendimento` e ter o passo 1 próprio — já modelado. **O que varia é o catálogo, e varia por apólice, não por seguradora** (📊 Yelum 21 × 30 itens em duas apólices; 7 × 12 × 14 causas por peça). Decorar catálogo é errado por construção.
6. 🔴 **Hardcodes errados**: `SLUGS_DE_SEGURADORA` tem 3 entradas para um portal de 38 seguradoras e inclui `ITAU`, **que não existe no portal** (quebra a promessa fail-closed); o bundle mapeia `sompo → GRUPO_HDI`; Yelum é `LIBERTY` e só o autocomplete sabe.

### 10.3 Veredito: dá para fechar ponta a ponta?

- 🟢 **Lataria/martelinho na Yelum: sim, hoje.** 100 % do fluxo medido, do preflight ao comprovante; não existe escolha de loja nem agendamento nesse ramo.
- 🟡 **Vidraçaria: até o 99 % hoje** (pedido aberto, franquia, lojas com endereço e distância, dias e horários reais apresentados ao segurado). **O último clique falta e não se inventa**: nunca vimos um bloco de horário (`Blocos: []`), nem `POST agendamentos`, nem `direcionamentos`, nem domicílio (`AtendeServicoMovel:false` nas duas capturas), nem `finalizar`, nem foto/vistoria (`PermiteVistoriaMobile:false` em todas). Codifica-se contra o contrato do bundle e **promove-se só depois de uma captura real** — a escada OBSERVED → CANDIDATE → APPROVED da SPEC-077.
- 🔴 **O questionário do para-brisa nunca foi capturado** (só vidro de porta e lanterna). É a peça mais frequente e a que a Regina mais pergunta.

### 10.4 As perguntas da Regina × o que o agente pergunta hoje

O achado que reorganiza tudo: **a maioria das perguntas dela não é o questionário do portal — é o que decide QUAL peça do catálogo escolher** (capa pintada ou fosca, com pisca, bipartida da mala ou da lateral, fixo ou sobe-e-desce, dianteiro ou traseiro). Hoje o agente pergunta "qual vidro foi?" em texto livre e o robô tenta casar contra 21–30 opções. As perguntas dela são o **funil de desambiguação que falta**.

| bloco | ela pergunta | o agente hoje | falta |
|---|---|---|---|
| universais (8 de 8) | placa · data · rodovia/urbano · relato · **cidade para a troca** | data ✅ · onde ✅ · relato ✅ · placa vem da InfoCap (certo) | 🔴 **`cidade_para_o_servico` não existe** — obrigatório no PATCH, o CEP da InfoCap é o de casa |
| para-brisa | posição da trinca · maior/menor que **moeda de 1 real** · sensor de chuva · faixa degradê · **ADAS** (sensor de faixa) | posição ✅ · tamanho ⚠️ (o código usa **10 cm**: duas réguas) | sensor de chuva, degradê, ADAS (a API tem `MensagemAdas`) |
| retrovisor | capa pintada/fosca · lado · pisca · regulagem manual/elétrica · capa ainda na peça | lado existe mas **só é oferecido para vidro de porta** | 4 perguntas que decidem o item do catálogo |
| farol | lado | lado ⚠️ | tipo (convencional/LED/xenon/milha) — **nem ela pergunta e o catálogo exige** |
| lanterna | lado · bipartida mala/carroceria | lado ⚠️ | bipartida, LED/halógena, neblina |
| vidro de porta | película · lado · dianteira/traseira · fixo ou sobe-e-desce | ✅ ✅ ✅ (batem com as perguntas reais do portal) | fixo × sobe-e-desce (decide `VIDRO DE PORTA` × `VIDRO DE JANELA` × `MÁQUINA`) |
| para-choque/lataria | dianteiro/traseiro · **quais peças** (várias) · mesmo evento · "a seguradora indica a loja" | nada | multi-peça (`ServicosMartelinhoLataria[]`), `EventoComposto`; e **não perguntar loja/domicílio** (o portal não oferece) |
| vigia | desembaçador · película | película existe mas `vigia` está em "sem específicas" | desembaçador |
| vistoria | "segue o link de vistoria… 2 dias úteis" | nada | gerar o link, anexar foto, conhecer o prazo |

O conjunto mínimo proposto (a regra de ouro: **perguntar só o que restringe o catálogo daquela apólice**, lendo `itens-cobertos` e `motivos-dano` **antes** de perguntar — hoje o código só os lê depois de já ter cobrado tudo):

```
SEMPRE      cpf_cnpj · data · peça (família) · relato · rodovia/urbano · cidade para o serviço
NUNCA       placa · chassi · CEP · endereço · versão (vêm do sistema de gestão)
DEPOIS do protocolo, e só se o portal oferecer:  loja × domicílio
por família: para-brisa (posição · tamanho · chuva · degradê · ADAS) · porta (lado · dianteira/traseira ·
película · fixo/sobe-desce) · vigia (película · desembaçador) · retrovisor (lado · capa · pisca · regulagem ·
capa na peça) · farol (lado · tipo) · lanterna (lado · posição · lâmpada) · para-choque (dt/tr · pintado) ·
lataria (lista de peças · mesmo evento; sem loja/domicílio)
```

### 10.5 EXTRA-001.10 · O portal de vidros de ponta a ponta — CRÍTICO 💭 10–14h (absorve P-PILOTO-07)

Objetivo: um acionamento de vidros na Yelum/Porto sai do WhatsApp do segurado e chega ao **comprovante** (lataria) ou
à **loja, dia e hora confirmados** (vidraçaria) sem a Regina; o agente pergunta só o que o catálogo daquela apólice
exige; foto e link de vistoria saem do robô, não da mão.

- **P0 (sem isto o API-first está morto ou é perigoso):** implementar `PATCH /atendimentos` (11 campos do contrato)
  e `POST /solicitantes` + `PUT /atendimentos/corretores` (obrigatórios em 3 de 3 HAR); **fronteira material
  calculada por categoria** (L → PATCH; V → `POST /questionarios`) no `vidros_estado`; remover `ITAU` e materializar
  os 38 códigos medidos em `GET /seguradoras/` (+ 4 só no bundle), com o caso `sompo → GRUPO_HDI` num teste que falha
  se alguém "corrigir"; **slot bloqueante `cidade_para_o_servico`** (UFs → cidades → clientes/cidades); reconciliar
  as três verdades sobre o que perguntar (`prompts.py:133` "só CPF+data+relato" × `portal_params.py:178` seis campos
  × `portal_tool.py:130` tudo).
- **P1 (fecha o ponta a ponta):** ler e **apresentar** lojas com distância, dias e horários reais ao segurado
  (`opcoes-disponiveis`, `consultar-distancias`, `datas-disponiveis`, `horarios-disponiveis`) — sem clicar; isso
  mantém a decisão de não sortear loja e elimina a razão dela. `POST agendamentos` / `direcionamentos` **atrás de
  flag e de aprovação humana**, CANDIDATE até haver captura. Perguntas específicas de retrovisor, farol, lanterna,
  vigia e para-choque no catálogo; **desambiguação guiada pelo catálogo** (ler antes de perguntar). **Ramo lataria
  como caminho próprio** (multi-peça, sem loja/domicílio). **Vistoria e fotos** pelo robô (`vistoriamobile?telefone=`
  gera o link; `atendimentos-fotografias/web` multipart anexa — precisa de um segundo caminho de `page.evaluate`).
- **P2:** uma régua só para o trincado (hoje três: 10 cm no código, moeda de 1 real na Regina, 5/20 cm num
  `servicos-detalhes` que é de lataria), com guarda que exige ZERO quando a régua não vem do portal; `abandonar` e
  `cancelar` como journeys reais (a Regina fez isso em 2 de 3 acionamentos); promover endpoints com
  `portal_factory.py lab api-infer` sobre os 4 HAR + `lab promote` em vez de contrato à mão (a ferramenta da SPEC-077
  nunca foi usada sobre este material); Bradesco: decidir se vai pelo `abraseuatendimento` (slug existe) ou pelo
  `agendeseuservico` (catálogo aponta, zero capturas) — **decisão sua, D-PILOTO-17**.
- **Gate:** (1) replay do HAR YELUM 1 pelo motor → mesma sequência de 7 escritas, mesmo corpo do PATCH; (2) guarda
  vermelho se `FRONTEIRA_MATERIALIZAR` for fixa; (3) teste que exige ZERO slug desconhecido pelo portal; (4) 20
  perguntas do .docx da Regina → slot existente com nome e família; (5) canário em produção: 1 acionamento de
  lataria na Yelum com o seu veículo de teste até o comprovante, com o freio `PORTAL_EFEITO_MATERIAL_LIBERADO`
  ligado só para esse job.

**Ordem de ataque:** Yelum lataria (fechável hoje) → Yelum vidraçaria (99 % hoje, 100 % após a captura nº 1) →
Porto (mesmo motor + `TipoAtendimento`) → Azul/Zurich (já têm corredor de WhatsApp para vidros) → as outras 34 do
`abraseuatendimento` (1 captura de passo 1 + `itens-cobertos` cada) → Bradesco (motor desconhecido, decisão antes
de código).

### 10.6 🧑 O que a Regina precisa capturar no próximo acionamento (DevTools aberto ANTES de "Iniciar atendimento", *Preserve log* ligado, "Save all as HAR **with content**" no fim)

| # | captura | por quê |
|---|---|---|
| **1** | 🔴 **Para-brisa, Yelum, até o fim, escolhendo LOJA num dia com agenda**: passo 3, **80 % inteiro**, passo 5, 99 %, **calendário com dias ativos, grade de horários, modal "Confirmar agendamento", tela pós-agendamento** | entrega de uma vez o questionário do para-brisa (chuva/degradê/ADAS) **e** o POST que confirma horário. Sem ela nada fecha |
| **2** | 🔴 A mesma peça escolhendo **DOMICÍLIO** num CEP atendido: card "Serviço a domicílio", distância, dia/hora do técnico, **formas de pagamento**, confirmação | todo o subfluxo de domicílio está no bundle e nunca foi exercido |
| **3** | Uma apólice **com vistoria habilitada**: aviso, telefone da vistoria, modal de fotos, **o upload**, vistoria finalizada | único caminho para o anexo de fotos e o link que ela cola à mão |
| 4–7 | **Retrovisor, lanterna bipartida, farol, vigia**: print da lista inteira de "Peça danificada" aberta + o 80 % | valida se capa/pisca/regulagem/tipo são itens do catálogo ou perguntas |
| 8 | Tela **Consultar atendimento** e a **Área do Segurado** | substitui o "vou ver com a seguradora" |
| 9 | **Uma seguradora fora de Yelum/Porto** (Allianz, HDI, Tokio, Mapfre, Azul), só até o passo 3 | prova que o motor é o mesmo (P-50: vidros sem evidência em 7 seguradoras) |
| 10 | **Bradesco no `agendeseuservico`**, do início ao protocolo | único portal de vidros fora do `abraseuatendimento`; zero capturas |
| 11–12 | Lataria com **mais de uma peça**; roda/pneu na Porto **com** cobertura | `EventoComposto` nunca preenchido; o único HAR de roda morre no 400 |

## 11. O humano da seguradora entra na URA (laudo I7, 13/09 — emenda ao bloco 001.4)

### 11.1 A resposta à sua pergunta: o que está determinado hoje

**A fase humana existe e é completa.** `human_phase` é um estado de primeira classe do motor
(`insurer_dispatch_service.py:64,119,150`), e a conversa oscila `ura ↔ human_phase` dentro da mesma sessão. Quando
um humano da seguradora se apresenta ("meu nome é", "me chamo", "como posso te ajudar", "darei continuidade"), o motor:

1. cola **uma vez, sem LLM**, o resumo do caso (`resumo_analista`, `:2915-2927`): titular e CPF, endereço da
   apólice, problema, telefone, período preferido;
2. responde **da ficha** qualquer pergunta cujo dado já está no caso (`responder_da_ficha`, `:2890`);
3. só então chama o **Cérebro** (`build_human_phase_messages`, `:3019`) para redigir 1–2 frases, com os dados do
   caso marcados "padrão — o cliente NÃO confirmou", as últimas 6 falas e a orientação do corredor;
4. passa o rascunho por um **guarda fail-closed** (`guard_human_phase_reply`, `:3296`): recusa `NAO_SEI`, recusa
   `SEM_RESPOSTA` se a tela pede algo, corta acima de 400 caracteres, recusa "protocolo" sem protocolo capturado,
   recusa **qualquer número de 5+ dígitos que não esteja nos slots** (não há guarda de CPF: o CPF do titular é
   entregue de propósito).
   Erro de redação ganha 1 refazimento; 2 recusas → `needs_human`.

Relógios (`dispatch_watchdog.py:32-38`): nós calados 30 s → Sentinela (2 tentativas); URA calada 120 s → alerta;
humano sumido 10 min → cutucada ("Seguimos por aqui no aguardo"); 20 min → grupo da corretora; sessão 45 min.
**Ele não chama o humano da corretora só porque um humano da seguradora entrou** — chama quando trava.

### 11.2 Por que ninguém respondeu à Vivian em 10/09 (reconstrução com horários)

| hora | o quê |
|---|---|
| 17:14:19 | run 1: Sentinela esgota no menu de três opções (o "residência") → `needs_human` |
| 17:17:21 | URA encerra por inatividade (**253 s** de silêncio) |
| 17:18:12 | run 2: alguém da corretora digita **"1"** à mão (`travamento.assumido`, ator `user`) e o fluxo anda |
| 17:19:30 | URA transfere ao especialista; motor grava `human_phase` (17:19:45, 17:20:02) |
| **17:21:35** | Sentinela trava na tela `complemento_referencia` (slot `ponto_referencia` ausente; o Cérebro responde `NAO_SEI` duas vezes, corretamente) → **`needs_human`** |
| **17:35:40** | Vivian se apresenta. **Zero eventos** do motor entre 17:21 e 18:09 |
| 17:38:18 | URA encerra "por falta de contato" |
| 18:09, 18:19, 18:29 | 3× `espera.vencida` ao grupo sobre uma conversa que a seguradora já tinha fechado |

🔴 **A causa é uma só: a sessão estava em `needs_human` catorze minutos antes de a Vivian falar, e `needs_human`
fecha as três portas de uma vez** — `handle_insurer_message` só converte `ura → human_phase`, nunca
`needs_human → human_phase` (`:2909`); o roteador exige `human_phase` para chamar o Cérebro
(`dispatch_router.py:2923`); e `needs_human` é estado terminal para o Vigia (`dispatch_watchdog.py:49,75`), então
nem Sentinela, nem cutucada, nem alerta. **O resumo estava pronto para sair**: rodando o motor sobre o texto exato
da Vivian, o gatilho "meu nome é" casa e a execução chega ao `resumo_analista`. Faltou o estado certo.

Hipóteses descartadas com prova: fase humana **foi** detectada (17:19:45); o agente desligado às 14:54 pela
Saionara é **irrelevante** (a rota da seguradora no webhook não passa por `attendance_agent_active`); a
intervenção da atendente é só crédito, não silencia nada.

Três defeitos novos que a reconstrução expôs:
- (a) 🔴 **A tela de encerramento da Allianz "Por falta de contato, estou encerrando" não é reconhecida** (a âncora
  `insurer_closed` cobre "encerrado por inatividade"); 📊 9 mensagens em 6 sessões. Custo: o run ficou
  `waiting_input` 50 min e queimou 3 alertas ao grupo sobre conversa morta.
- (b) 🔴 **A URA perguntou uma coisa que só o segurado sabe (ponto de referência) e não existe caminho para
  perguntar ao segurado e voltar**: 📊 todas as 8 chamadas de `send_to_client` no roteador são avisos, nenhuma
  pergunta e espera.
- (c) 🔴 **`work_events` com `agente.cerebro | agente.sentinela | agente.vigia`: 0 de 0 em toda a base.** O
  registro de atos do agente (SPEC-085 C.3, `registrar_ato_do_agente`, `dispatch_router.py:997`) **nunca gravou uma
  linha**. O desempenho do Cérebro é inauditável — e é o que mais atrapalha qualquer medição do piloto (001.7).

### 11.3 A regra que a 001.4 passa a escrever

| regra | hoje | o que a SPEC faz |
|---|---|---|
| âncora **positiva** de entrada na fase humana ("Vou transferir seu caso para um especialista", "Isso pode levar alguns instantes") | não existe; a transição é por **exclusão** (nada casou → humano) | passos declarados `noop` com `enters_human_phase: true`; guarda pelo motor sobre o texto do acervo |
| **`needs_human` deixa de ser surdo**: humano da seguradora se apresenta → reentra em `human_phase`, sai o resumo determinístico, o Vigia volta a vigiar | não existe | reentrada segura: o resumo não inventa nada e sai uma vez por sessão; o grupo recebe "a seguradora respondeu, retomei" só se já tinha recebido o pedido de ajuda |
| responder com os dados do caso em 1–3 frases, tom de atendente da corretora, até o protocolo | ✅ existe | mantém |
| **perguntar ao segurado o que falta e voltar** (ponto de referência, andar, portaria) | não existe | mecanismo novo com contrato: pergunta pelo canal do cliente, espera com prazo, mensagem à seguradora "um instante, confirmando com o segurado", e desfecho se ele não responder antes de a URA encerrar |
| relógio da espera pelo humano | cutucada 10 min, grupo 20 min, sem distinguir fila vazia de humano sumido | 📊 acervo Allianz (114 transferências, 50 atendentes distintos): **59 % chegam em < 10 s, mediana 3 s, p90 10,5 min, máx 49 min**. Cutucar em 2 min cutucaria fila vazia em ~30 % dos casos. Regra: **fila** (ninguém falou ainda) tem relógio próprio e longo; **cutucada** só depois de o humano ter falado ao menos uma vez; grupo em 20 min mantém |
| encerramento da Allianz reconhecido | não | âncora nova; teste que exige ZERO `human_phase` após a frase |
| atos do agente registrados | 0 linhas | `registrar_ato_do_agente` passa a gravar de verdade; guarda que conta ≥1 linha por sessão com Cérebro |

### 11.4 Opção C: o tempo, medido contra as URAs reais

📊 Acervo inteiro (32.588 eventos, 56 encerramentos por inatividade; relógio = última mensagem → tela de encerramento):

| seguradora | n | mín | mediana | p90 | máx |
|---|---|---|---|---|---|
| Allianz | 35 | **103 s** | 246 s | 304 s | 528 s |
| Yelum | 11 | 359 s | 478 s | 483 s | 484 s |
| Bradesco | 5 | 302 s | 306 s | 312 s | 312 s |
| Porto | 1 | **95 s** | — | — | — |
| HDI | 1 | 919 s | — | — | — |

Encerramentos com silêncio < 60 s: **0 de 56** · < 90 s: **0 de 56** · < 120 s: **2 de 56** (Porto 95 s, Allianz
103 s). A Allianz **não avisa** antes de encerrar; Yelum, HDI, Tokio e Bradesco avisam aos ~300–360 s. O caso de
10/09 (253 s) está na moda da Allianz.

| valor | nota | por quê |
|---|---|---|
| **60 s** | **92** | margem de 35 s sobre o pior caso (Porto) e 43 s sobre a Allianz; cabe o Cérebro (~4 s) e o ciclo de 20 s do Vigia |
| 90 s | 74 | 0 de 56 cortados — mas a margem sobre o pior caso é de 5 s, e como o Vigia roda a cada 20 s, 90 s viram até 110 s reais: os dois piores casos **são perdidos** |
| 120 s | 41 | 2 de 56 perdidos, medidos |

**Decisão que recomendo (fecha a D-PILOTO-10): 60 s, renovável — e a renovação é automática toda vez que a
atendente efetivamente envia algo à seguradora**, porque é esse envio que reinicia o relógio da URA do outro lado.
Pausa renovada sem saída é silêncio empilhado. Trava: no máximo **2 renovações sem saída** (120 s no total), depois
o corredor retoma sozinho mesmo com a pausa aberta — passar disso é entregar a sessão à inatividade, que foi
exatamente o desfecho das 17:17 e das 17:38 de 10/09.

## 12. A ordem final, o que só você faz, e o próximo passo

### 12.1 Os onze blocos, na ordem em que viram SPEC

| # | SPEC | marcha | 💭 relógio | depende de |
|---|---|---|---|---|
| 1 | **001.0** retroativa: as cinco entregas de 08–10/09 documentadas | LEVE | 1–2h | — (se D-PILOTO-15 = sim) |
| 2 | **001.6-P0** cobrança: `bloco_unico`, motivo da Mapfre, frases da Allianz, nome da atendente | PADRÃO | 2h | senhas renovadas (🧑) |
| 3 | **001.1** apólice certa + porta `PolicyDataProvider` | CRÍTICO | 8–12h | — |
| 4 | **001.2** lê tudo antes de falar + nome do agente | CRÍTICO | 6–9h | — |
| 5 | **001.3** grupo só o que importa + card Equipe + eficiência | CRÍTICO | 7–10h | 001.2 (uma conversa por contraparte) |
| 6 | **001.4** corredor não trava + humano na URA (60 s) + humano da seguradora | CRÍTICO | 8–11h | — (paralelo a 001.3) |
| 7 | **001.6** cobrança completa: dedup sempre, agrupar por segurado, sessão que expira, canário de login | PADRÃO | 6–9h | 001.6-P0 |
| 8 | **001.7** piloto medido (3 dias inteiros, régua por dimensão) | LEVE | protocolo | 001.1–001.4, 001.6 |
| 9 | **001.10** portal de vidros ponta a ponta | CRÍTICO | 10–14h | captura nº 1 da Regina para o 100 % de vidraçaria; lataria não depende |
| 10 | **001.5** base de produtos e assistências (3 níveis) | PADRÃO | 10–14h | 001.1 (a porta); trilho paralelo desde o início |
| 11 | **001.8** isolamento por corretora | CRÍTICO | 8–12h | — |
| 12 | **001.9** rotas do painel | LEVE | 1–2h | SPEC de painel |

### 12.2 O que só você faz — esta semana, antes de qualquer SPEC

1. **Senhas da Allianz e da Mapfre** nos portais de corretor (as duas estão recusadas; Allianz desde 18/08).
2. **Rotina de cobrança**: reativar (`is_active=false` hoje), preencher o nome da atendente e o `team_number`,
   decidir `equipe` × `cliente`, dizer o N de "1 cobrança por segurado a cada N dias".
3. **Regina: a captura nº 1** (para-brisa na Yelum até o horário confirmado, HAR *with content*) — é a única que
   destrava o 100 % da vidraçaria. As outras 11 capturas podem vir aos poucos.
4. ~~Decidir D-PILOTO-15/16/17~~ — decididas em 13/09 (§7.1).
5. ~~Eficiência~~ — decidida: distinção incapacidade × regra (D-PILOTO-13).
6. Ainda abertos de 09–10/09: `publicar_cartas_0971.py --global --vivo`; P-PILOTO-09 (arquivo de credenciais),
   17 (`llm_max_tokens` no banco), 19.

### 12.3 O próximo passo, em uma linha

Você responde às decisões de 12.2 (itens 4 e 5) e diz **"escreva as SPECs"**. Eu escrevo as onze propostas neste
chat, na ordem de 12.1, uma por vez, com o laço leve de §8 (proposta → revisor Opus → emendas → resumo de 15 linhas
para você). Cada proposta nasce em `docs/canon/specs-propostas/SPEC-EXTRA-001.x-….md` + RESEARCH-PACK + prompt de
abertura, no padrão da EXTRA-001. A execução de cada uma é em chat novo, sob AAA opção B, com a marcha da tabela
de §8. Nenhuma SPEC começa a ser executada antes de você ler o resumo dela.

## 13. ANÁLISE DE QUALIDADE — estamos usando um míssil para matar uma mosca?

Você pediu uma resposta sincera, com nota, sobre se o protocolo AAA e o laço de agentes estão em excesso. A resposta
curta: **os instrumentos estão certos; a dose desta semana está errada.** O que segue é a prova, com os números
do próprio projeto, depois a leitura do que a comunidade mede, e por fim a recomendação com nota.

### 13.1 O que o projeto já mediu a favor do protocolo (FATO)

| medição | onde está | o que diz |
|---|---|---|
| 📊 Painel de juízes em 2 de 6 SPECs: **com painel 47 achados · 22 defeitos de produto; sem painel 19 achados · 0 defeitos de produto** (3,7×) | CLAUDE.md §2, auditoria de 30/08 | O revisor separado do construtor acha o que o construtor não vê. |
| 📊 SPEC-093-B: a única frente que **reconstruiu o resultado sobre 1.851 sessões reais** achou os dois maiores defeitos (40,8 % dos PDFs de sinistro não viravam evento; a "variante" era um histograma) — o painel de código aprovou o dataset errado | dossiê 093-B | Quem julga só o código aprova dado errado. A lente do dado existe por isso. |
| 📊 SPEC-094: **366 asserções verdes com fakes** e a tool **não rodava no grafo**; só o juiz fresco com canário vivo achou | dossiê 094 | Um agente que constrói e testa a si mesmo se dá verde. O canário vivo é o gate que não mente. |
| 📊 O painel custa **~4 % do relógio**; a bateria de testes custa **~50 %** | CLAUDE.md §2 | O caro não é o juiz. É a bateria e, como esta semana mostrou, **os documentos**. |
| 📊 Esta semana, o revisor da 001.1 devolveu 1 BLOCKER real (um gate impossível de passar), 6 ESSENCIAIS com linha, 3 deles erros de medição do próprio redator | §13.4 abaixo | Um segundo par de olhos sobre a proposta paga, mas parte do que ele acha é custo que o tamanho da proposta criou. |

### 13.2 O que o projeto mediu contra a dose atual (FATO)

| medição | o que diz |
|---|---|
| 📊 **Duas janelas de 5 h esgotadas em fase de planejamento**; zero linha de produto entregue desde 10/09 | O gargalo hoje não é qualidade, é o relógio. |
| 📊 A tarde de 13/09: **10 agentes Opus em paralelo**, ~300 k tokens cada, esgotaram a janela em ~40 min. Paralelismo não reduz tokens — só reduz relógio, e o relógio é limitado pela janela de qualquer forma | Dez agentes ao mesmo tempo é a forma mais rápida de perder tudo de uma vez. Erro meu. |
| 📊 As propostas 001.1–001.4 têm **98–113 KB cada** (a EXTRA-001, modelo, tinha 48 KB); com RESEARCH-PACK e PROMPT, **~170 KB por SPEC**, ~1 MB para seis. Muitas são maiores que o código que descrevem | Documento maior que o diff é sinal de excesso (a comunidade cita exatamente isso). |
| 📊 Três arquivos por SPEC repetem ~40 % do conteúdo (o PROMPT é 90 % igual entre SPECs; o RESEARCH-PACK repete as linhas da proposta) | Redundância paga em criação e em leitura do executor. |
| 📊 As **cinco entregas de 08–10/09 sem AAA** (builders Opus + eu como juiz, testes por unidade) subiram em 2 dias, estão no ar, com 11 guardas rodando, 10 verdes. Os pilotos mostraram defeitos **de escopo e de produto** (a apólice errada, o grupo inundado, o "residência"), não defeitos de construção do que foi pedido | O laço leve **constrói bem o que se pede**. O que faltou foi entender o que pedir — e isso veio da auditoria (medição do acervo), não de painel. |
| 📊 Revisor da 001.1: dos 10 achados, 3 eram números de linha deslocados por uma unidade e 2 eram "desconhecidos" que o redator poderia ter medido | Parte da revisão é custo induzido por documento longo, não defeito de produto. |

### 13.3 A minha leitura (INFERÊNCIA, e a opinião que você pediu)

1. **O painel + juiz fresco + canário vivo não são o míssil. São a mira.** Os três casos acima (22 × 0; 40,8 %;
   366 verdes com a tool morta) são defeitos que **chegariam ao segurado ou ao corretor**. Nenhum deles foi achado
   pelo agente que construiu. Isso não é "o agente diz que ficou bom"; é o agente **medindo que não ficou**. Para
   o que muda o que o cliente lê, o que envia mensagem e o que mexe em dinheiro, essa mira vale o que custa.
   **Nota de manter o painel nas SPECs CRÍTICAS: 90.**
2. **O míssil é o resto do rito aplicado a tudo, e é o que estourou as janelas:** propostas de 100 KB, três
   arquivos por SPEC, pesquisa externa obrigatória em toda proposta, red team em SPEC de tela, aquecimento com 16
   perguntas em SPEC de relatório, e dez agentes em paralelo. Para uma SPEC LEVE (001.0, 001.7, 001.9) o AAA
   inteiro é **excesso medido**: o risco dessas entregas é zero para o segurado, e um Opus sozinho com um juiz
   entrega a mesma coisa. **Nota do AAA completo em SPEC LEVE: 35. Nota de Opus + 1 juiz em SPEC LEVE: 88.**
3. **"Opus sozinho daria 100/100"** — para CRÍTICO, não. A medição 366-verdes-tool-morta é a prova: o construtor
   se dá verde. **Nota de Opus sozinho em CRÍTICO: 55.** Para LEVE: **85**. Para PADRÃO (motor sem envio): **72**.
4. **O laço antigo "subagente + juízes críticos" era mais rápido e não era pior no que ele via.** Ele era pior no
   que ele **não via**: dado errado (lente do dado) e código que não roda no produto (canário vivo). Essas duas
   peças custam pouco (o painel é 4 % do relógio) e são o que separa "o agente disse que ficou bom" de "ficou".
   **Recomendo trazer o laço antigo de volta como a marcha PADRÃO**, com essas duas peças acopladas.
5. **O que sinto igual a você:** o rito virou burocracia quando passou a ser aplicado por reflexo. A regra do
   protocolo é "marcha por risco"; esta semana eu apliquei marcha CRÍTICA na **criação** das propostas, que é
   trabalho de escrita, não de produto. Isso foi erro de dose, meu.

### 13.4 O que muda a partir de agora (RECOMENDAÇÃO, já aplicada às SPECs que faltam)

| regra | antes (esta semana) | agora | nota |
|---|---|---|---|
| **Marcha por risco, de verdade** | tudo em CRÍTICO | CRÍTICO só onde envia mensagem, muda o que o cliente lê ou mexe em dinheiro (001.1, 001.2, 001.3, 001.4, 001.6, 001.10, 001.8); PADRÃO = 1 lente + juiz fresco + canário (001.5); LEVE = Opus + 1 juiz, sem painel, sem red team (001.0, 001.7, 001.9) | 90 |
| **Tamanho da proposta** | 100 KB + RP 50 KB + prompt 20 KB | proposta ≤ 40 KB com o research como apêndice; **um** PROMPT-modelo compartilhado + 1 página por SPEC | 88 |
| **Agentes em paralelo** | 10 | **≤ 4**, e um orçamento por janela: criação ≤ 1,5 M tokens, execução ≤ 2,5 M por SPEC | 92 |
| **Modelo por papel** | Opus em tudo | Opus para construir e para o juiz fresco; **Sonnet** para pesquisa na web, revisão de documento e inventário | 85 |
| **Bateria** | sem teto na prática | ≤ 12 guardas novos por SPEC, todos pelo motor sobre acervo real (já é D-PILOTO-14); proibido teste que reimplementa a regra | 90 |
| **Pesquisa externa** | obrigatória em toda proposta | só quando a SPEC introduz um padrão novo (porta, fila, breaker); reaproveitar as referências já citadas nas SPECs anteriores | 85 |
| **O que nunca sai** | — | juiz fresco + canário vivo em tudo que envia; lente do dado sempre que o resultado é dataset; EXECUTION CARD; `git push` com saída no relatório | 95 |

**Nota do que fizemos esta semana, do jeito que fizemos: 58/100.** Instrumentos certos, dose errada, duas janelas
perdidas. **Nota do "AAA dosado" acima: 88/100.** **Nota de voltar ao laço antigo para tudo: 70** — rápido, mas
a medição 22 × 0 diz que ele deixa passar defeito de produto onde dói. **A resposta à sua pergunta: não é
míssil para mosca; é míssil disparado em toda mosca.** O protocolo está certo e fica; a dose muda, e a mudança
começa nas cinco propostas que ainda faltam.

### 13.5 O que a comunidade mede e diz (pesquisa de 13/09; fontes em 13.6)

| fonte | o que mediu ou defendeu | condição em que vale |
|---|---|---|
| **Anthropic, "Building effective agents"** (orientação) | comece pela solução mais simples; o padrão avaliador-otimizador (crítico em laço) só vale com **critério claro de avaliação** e **melhora demonstrável a cada rodada** | sem critério e sem melhora medida, o laço é custo puro |
| **Anthropic, sistema de pesquisa multi-agente** (📊 medição interna) | orquestrador Opus + subagentes Sonnet bateu Opus sozinho em **90,2 %** num eval de pesquisa; custo: agente ≈ **4×** os tokens de um chat, multi-agente ≈ **15×** | só para tarefa paralelizável, com mais contexto do que cabe numa janela, e valor alto o bastante para pagar 15× |
| **MAST, "Why do multi-agent LLM systems fail?"** (📊 1.600+ traces, 14 modos de falha) | "ganhos em benchmarks são frequentemente mínimos"; falhas de design do sistema, desalinhamento entre agentes e **falha de verificação** | o aparato não paga se a verificação no fim é fraca |
| **Cognition, "Don't build multi-agents" → "What's actually working"** (opinião de produto, com retratação parcial) | agentes paralelos que **escrevem** ao mesmo tempo tomam decisões conflitantes; o que funciona: **revisor de contexto limpo** (pega o que o gerador saturado não vê), roteamento entre modelos, escrita single-threaded | vários contribuem inteligência; **um só escreve** |
| **"Nine judges, two effective votes"** (📊 arXiv 2605.29800) | painel de 9 juízes de 7 famílias dá elevação **nula ou negativa** sobre o melhor juiz sozinho (84,2 % vs 77,7 %): erros correlacionados; 9 opiniões ≈ **2 votos independentes** | diversidade de modelo importa mais que quantidade; painel homogêneo grande é desperdício |
| **"More rounds, more noise"** (📊 arXiv 2603.16244) + Self-Refine | o ganho vem nas **1–2 primeiras rodadas** de revisão; a 3ª satura e pode piorar | parar em duas rodadas |
| **Fowler/Thoughtworks, "agentic programming"** (experimento próprio) | paralelizar geração de código dependente força conserto prematuro ou conflito na fusão; "harness engineering" é custo real | paralelismo de escrita ajuda pouco em código |
| **Gap verificação × geração** (várias linhas) | verificar é mais barato e mais confiável que gerar de novo | 1 verificador antes de N geradores |

**Tabela de convergência:** tarefa sequencial de código → 1 agente forte, escrita única (1×) · exploração paralelizável → orquestrador + subagentes (15×, só se o valor pagar) · garantir qualidade → **1 revisor de contexto fresco**, não N (~2×) · rodadas de crítica → parar em 1–2 · critério objetivo (compila, responde 200, casa o regex no motor) → **teste determinístico, não juiz** · julgamento qualitativo → 1 juiz forte; painel só com famílias diferentes.

**O que isso diz do nosso protocolo, item a item:** o **juiz fresco com canário vivo** é o padrão mais defendido (Cognition, Anthropic, e a nossa medição 366-verdes-tool-morta) — fica. **Painel de 3 lentes do mesmo modelo** é o caso "nove juízes, dois votos": vale como lentes **de assunto diferente** (dado × código × produto — foi assim que a lente do dado achou o que as outras não acharam), não como três opiniões sobre a mesma coisa — fica só onde as lentes são de fato diferentes, e uma delas é sempre a do dado. **Red team + juiz de confirmação + auditoria externa** na mesma SPEC é a 3ª e 4ª rodada que a literatura mede como ruído — corta para PADRÃO, fica só em CRÍTICO com envio. **Dez agentes em paralelo escrevendo documentos** é exatamente o modo de falha da Cognition e do Fowler — cap de 4, e um só escreve por arquivo. **Guardas pelo motor** (§9.4/§9.5 do CLAUDE.md) são o "teste determinístico em vez de juiz" — é onde o projeto já está certo e barato.

### 13.6 Fontes
Anthropic — Building effective agents (anthropic.com/engineering/building-effective-agents) · Anthropic — How we built our multi-agent research system (anthropic.com/engineering/multi-agent-research-system) · Why Do Multi-Agent LLM Systems Fail? (arxiv.org/abs/2503.13657) · Cognition — Don't Build Multi-Agents (cognition.com/blog/dont-build-multi-agents) · Cognition — Multi-Agents: What's Actually Working (cognition.com/blog/multi-agents-working) · Martin Fowler — Agentic Programming (martinfowler.com/bliki/AgenticProgramming.html) e Pushing AI autonomy (martinfowler.com/articles/pushing-ai-autonomy.html) · Nine Judges, Two Effective Votes (arxiv.org/pdf/2605.29800) · More Rounds, More Noise (arxiv.org/pdf/2603.16244) · Self-Refine (arxiv.org/pdf/2303.17651) · LangChain — How and when to build multi-agent systems (langchain.com/blog/how-and-when-to-build-multi-agent-systems). Não encontrado: uma thread nomeada de Hacker News ou um post do Simon Willison com o termo "overkill" — a posição dele é caso a caso.
