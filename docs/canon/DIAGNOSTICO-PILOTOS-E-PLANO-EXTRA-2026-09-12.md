# DIAGNÓSTICO DOS PILOTOS (09–11/09) E PLANO DA FAMÍLIA EXTRA — 12/09/2026

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

Ordem: **001.1 → 001.2 → 001.3 ∥ 001.4 → 001.6 → piloto medido (001.7) → 001.5 (trilho paralelo, longa) → 001.8 → 001.9 leve.**
Marcha: CRÍTICO onde muda o que o segurado ou o corretor lê; PADRÃO onde é motor; LEVE onde é tela.

### EXTRA-001.1 · A apólice certa, inteira, em uma rodada — CRÍTICO 💭 6–9h
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
- Nome do agente da Resulta (💭 "Amanda" × Saionara) — decisão sua.
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
  precisei de ajuda · eficiência = concluídas sozinho ÷ (concluídas + ajuda); sinistro fora do denominador).
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
- Humano na URA — **opção C (nota 91)**: pausa de 90 s renovável a cada mensagem humana; uma mensagem ao grupo
  ("assumo de volta em 90 s · responda AGENTE para seguir agora · EU CUIDO para eu sair deste acionamento"); sem
  resposta, retoma lendo a tela atual; enquanto o humano está lá, nenhum gatilho de grupo dispara. (A "parar 7 dias" 35;
  B "continuar como hoje" 62.)
- Riscos adjacentes: `azul-auto/menu_atendimento` "1" sem fallback; `complemento` homônimos em porto-auto.
- Regenerar corpus, régua, inventário e roteiro (P-PILOTO-06); Porto/Azul: schema do formulário no 1º acionamento real.
- Gate: replay do acervo Allianz 10/09 pelo motor → "1" no menu de três opções; mutação vermelha com "residência".

### EXTRA-001.5 · O agente sabe o que cada plano cobre — CRÍTICO 💭 10–14h, trilho paralelo
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

### EXTRA-001.6 · A cobrança prova que funciona — PADRÃO 💭 4–6h
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

## 4. Decisões que só você toma (registro em FOUNDER-DECISIONS quando decidir)
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

## 6. O que faltou nesta auditoria
A mensagem do Founder de 12/09 chegou cortada em "o agente lê dentro da apólice ou não consegue ler o PDF… eu não
consigo entende". O que veio depois (provavelmente cobrança, renovação e outros pontos) não foi recebido e precisa
ser reenviado para entrar no plano.
