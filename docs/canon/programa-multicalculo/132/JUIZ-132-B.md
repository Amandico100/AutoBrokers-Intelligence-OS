# JUIZ FRESCO — SPEC-132-B (a Cotação Rápida)

> modelo: claude-opus-5-5 · 14/10/2026 · branch `spec/132-o-chat-e-a-cotacao` · diff `285cadc..618ba14` (+ os commits da
> fatia E até `41e6896`, que não são objeto deste laudo) · read-only sobre o código · 📊 medido · 💭 inferência.

## 0. VEREDITO

**REPROVADO COM CONSERTO CURTO — NOTA 70/100.** A espinha está bem feita (identidade injetada pelo estado, uso único
do `confirmacao_id`, filtro `company_id` em toda leitura, mensagem idempotente, página de venda honesta, capability só
no core). Mas há **4 BLOCKERS medidos**, todos pelo teste do produto (§2: mudam o que chega ao segurado, à corretora
ou ao que sai do prédio), e todos com conserto pequeno.

## 1. O que eu rodei (saída real)

| comando | resultado |
|---|---|
| `pytest tests/test_spec132b_o_fio.py` | 📊 **7 passed** in 30.21s |
| `pytest tests/test_spec132b_a_conversa.py` | 📊 **18 passed** in 32.60s |
| `pytest tests/test_spec132b_a_pagina_de_venda.py` | 📊 **25 passed** in 123.43s |
| `pytest tests/test_spec132b_api_cotacoes.py` | 📊 **10 passed** in 47.70s |
| `node components/aplicativos/casca/a-loja-e-a-casca.test.mjs` | 📊 **203 OK** · "A LOJA E A CASCA: TODOS OS GUARDAS VERDES" |
| sondas do juiz `scratchpad/juizB/test_juiz_132b.py` (mundo do fio, dublê só na borda) | 📊 2 passed — e os dois provam defeito (B1, B4) |
| sondas `scratchpad/juizB_sonda.py` e `juizB_sonda2.py` (o `montar` REAL) | 📊 provam B2, B3 e P2 |

Todos pela trava (`pesado.sh`), um arquivo por vez. Nenhum arquivo do repositório foi tocado (só este laudo).

## 2. BLOCKERS

### B1 — O RECÁLCULO responde "Recalculado com a franquia reduzida" com a tabela e o link ANTIGOS
- **Teste do produto:** SIM — o corretor lê preço velho rotulado como novo e copia ao cliente a "Mensagem para o
  cliente" com os preços de antes, achando que são os da franquia reduzida.
- **Medição** (sonda `test_sonda_o_recalculo_mostra_o_preco_novo`, motor real + robô dublê + `publicar_cotacao` REAL):
  ```
  [AJUSTE] calculos ajuste: ['fechado'] ofertas do ajuste: 26
  --- msg 0: url=…/r/igQwJchz…   Pronto: 13 seguradoras responderam.
  | Recomendada | Azul | 3x R$ 809,77 sem juros | R$ 2.429,31 | R$ 5.128,00 |
  --- msg 1: url=…/r/igQwJchz…   Pronto: 13 seguradoras responderam. (Recalculado com a franquia reduzida.)
  | Recomendada | Azul | 3x R$ 809,77 sem juros | R$ 2.429,31 | R$ 5.128,00 |
  [AJUSTE] tabela IGUAL antes/depois do recálculo? True
  [AJUSTE] link IGUAL antes/depois? True
  ```
- **Causa:** `cotacao/workflow.py:322` republica a página pelo `publicar_cotacao`, que monta as opções por
  `comparacao.opcoes` — ela só lê os rankings `padrao`/`economica`/`completa_mais`/`minima`
  (`comparacao.py:1104-1108`); o `opcao='ajuste'` nunca entra (`comparacao.py:8`, por desenho da 130-A). O modelo sai
  idêntico, e `proposta.link_que_ainda_vale` (B4) devolve até o MESMO link. A régua não pegou porque o teste do
  ajuste (`test_spec132b_a_conversa.py:420`) roda com a publicação DUBLÊ e só confere a frase do disparo.
- **Conserto:** o run de ajuste responde com as ofertas DO CÁLCULO de ajuste (`ajuste_calculo_id` está no payload):
  a linha da opção ajustada (seguradora, parcela, à vista, franquia) contra a de antes — e, enquanto a página não
  souber mostrar o ajuste, NÃO repete o link/mensagem antiga como se fosse nova. Guarda: o fio com publicação REAL,
  ajuste, e a tabela tem de MUDAR (com a mutação "ignora o ajuste" deixando-o vermelho).

### B2 — "Economia" na página do cliente SEM apólice nenhuma, com um prêmio que o corretor nem conferiu
- **Teste do produto:** SIM — a página mostra ao cliente "R$ X a menos por ano — em relação ao seu seguro atual, que
  custa R$ Y" com Y escrito pelo MODELO. A SPEC §4.4 diz "só com a apólice atual LIDA (nunca sem prova)" e a mutação 5
  é exatamente "economia sem apólice".
- **Medição** (`juizB_sonda.py`, o `pedido_da_conversa.montar` real):
  ```
  S1  sem anexo: situacao: novo_com_apolice | apolice_atual: {'seguradora': 'Porto', 'premio_anual': 9000.0, 'origem': 'corretor'}
      o resumo que o corretor confere mostra o premio 9.000? False   → ['- Seguro atual: Porto']
  S1b com anexo: apolice_atual: {'seguradora': 'Porto', 'premio_anual': 12000.0, 'origem': 'documento'}
  ```
- **O caminho:** `cotacao_tool.py:79` (`premio_atual_anual` "se disse", campo do modelo) → `pedido_da_conversa.py:303-313`
  (vira `novo_com_apolice`; com ficha, rotulado `origem='documento'` embora o número NÃO venha da ficha — a ficha
  nunca é lida para o prêmio) → `workflow.py:193-195` → `publicar_cotacao` (`proposta.py`, `situacao =
  "novo_com_apolice" if apolice_atual`) → `proposta_cotacao_html._economia` (`:164-176`) não olha a origem. O teste da
  página (`test_economia_so_com_a_apolice…`) usa `APOLICE_CARA` e confirma que esse formato mostra a economia.
- **Conserto:** economia só com o prêmio LIDO pelo leitor da apólice (o `ficha` da 130-B) e `origem='documento'` de
  verdade; o prêmio declarado pelo corretor pode ir à mensagem dele, nunca à página do cliente — e, se ficar, tem de
  aparecer no resumo que ele confirma. Guarda: preparar SEM anexo com `premio_atual_anual` → a página servida não tem
  `id="h-eco"`.

### B3 — O pedido de um cliente sai com o CPF de OUTRO cliente da mesma conversa
- **Teste do produto:** SIM — o cálculo é criado no Agger (e nas seguradoras) com o nome da Maria e o CPF do João
  (dado pessoal de terceiro levado a outro pedido, CLAUDE.md §7 espírito/LGPD).
- **Medição** (`juizB_sonda2.py`): as falas cruas têm o pedido anterior do João (CPF 529.982.247-25) e o novo, da
  Maria, SEM CPF; o modelo não manda `cpf_cnpj`:
  ```
  completa: True | cpf do pedido da Maria: 52998224725
  ['- Cliente: Maria Ficticia — CPF ***.***.***-25, nascimento 03/04/1990, sexo feminino']
  ```
  Em vez de perguntar o CPF, a ferramenta completou o pedido com o único CPF das últimas 12 falas.
- **Causa:** `pedido_da_conversa.py:248-250` — o recurso ao texto cru roda MESMO quando o modelo não mandou CPF
  nenhum. Para nascimento e CEP o mesmo recurso só roda quando o modelo mandou algo (`:321-323`, `:332`). O caso de uso
  legítimo (o guardrail mascarou e o modelo mandou `"<CPF>"`, `test_…_achado_no_texto_cru`) continua coberto se a
  condição for a mesma.
- **Conserto (1 linha):** `if not doc and d.get("cpf_cnpj"):` antes de `unico_no_texto_cru("cpf", …)` (e, melhor,
  conferir os dígitos visíveis da máscara com o achado). Guarda: a sonda acima vira teste e exige "Faltam: … o CPF".

### B4 — O cálculo dispara sem o "sim" do corretor: o modelo pode encadear preparar → disparar no mesmo turno
- **Teste do produto:** SIM — sai do prédio (cria cálculo no Agger e nº de cálculo nas seguradoras) sem a confirmação
  que o contrato promete (D-132B-03, nota 92 contra "calcular direto 40") e que o CLAUDE.md §6 exige fora do prompt
  ("Approval não é frase de prompt").
- **Medição** (sonda `test_sonda_disparar_no_mesmo_turno_sem_um_sim`, `tool_node` REAL):
  ```
  [MESMO TURNO] falas do corretor na conversa: 1 -> ['cota o Onix 2022 placa ABC1D23 da Fulana']
  [MESMO TURNO] disparar respondeu: Calculando nas seguradoras no seu Agger — volto aqui …
  [MESMO TURNO] pedidos criados: 1
  ```
  O próprio guarda do fio faz isso (`test_spec132b_a_conversa.py:235-241`: `preparar` e `disparar` sem fala nenhuma
  no meio) e passa — o código não distingue.
- **Causa:** o `confirmacao_id` volta ao MODELO na saída do preparar (`cotacao_tool.py:209`) e `confirmacao.consumir`
  confere dono, conversa, validade e uso único — mas não que o CORRETOR falou depois do resumo. O "só com um sim" é
  só texto para o assistente (`:210-212`). O laço do LangGraph (agente → ferramenta → agente) permite as duas chamadas
  num turno.
- **Conserto:** `guardar` grava o instante (ou o id da última fala `role=user`); `consumir` só aceita se existe uma
  fala do corretor NESTA conversa DEPOIS dele (o `messages` já está lá — a `textos_crus_da_conversa` lê a mesma
  tabela). Guarda: a sonda acima exige recusa; com a fala "sim" semeada depois, dispara (controle).

## 3. PENDÊNCIAS (não mudam um byte sozinhas, ou mudam pouco — vão para o PENDENCIAS.md)

| # | o quê | evidência | destino |
|---|---|---|---|
| P1 | **A "comissão de entrada" do Configurar não vale para o CARRO.** A tela diz "A comissão da corretora com que o cálculo começa num cliente novo" (`RegrasDoCalculo.tsx:200`), mas no AUTO nenhum preset leva `percComissao` — "ela vem da conta / da negociação" (`portal_worker/multicalculo/presets.py:89`); o `comissao.entrada` só entra no RE (`porta.py:529`) e na negociação. A corretora muda o número e o preço do carro não muda. | leitura + grep `entrada` vazio em porta/motor/presets | ESSENCIAL: corrigir a frase (RE + negociação; no carro vale a da conta do Agger) ou passar a comissão no disparo AUTO |
| P2 | CPF **pontuado** na `descricao_do_veiculo` vai EM CLARO ao `work_runs.input_payload.risco` e à aba Cotações: o filtro `\d{6,}` (`workflow.py:144`) não pega `529.982.247-25`. | 📊 sonda S2: `'risco': 'Onix do CPF 529.982.247-25'`; controle sem pontos → removido | 1 linha: `sem_documento_inteiro`/`documento_valido` no `risco` |
| P3 | O ROLLBACK da `_04` apaga `tenant_capability_entitlements` da chave — linhas que a migration NÃO criou (o cabeçalho diz "remove só o que esta migration criou"). | `20261014_04…sql:37` | corrigir o texto ou tirar a linha |
| P4 | O FAQ aplicado no catálogo diz "Posso pedir a cotação pelo WhatsApp? **Em breve.**" — fica falso quando a 132-C ligar (mesmo branch). | `20261014_02…sql`, FAQ 4 | atualizar junto com a 132-C |
| P5 | Capacidade: o run segura um slot do worker por até 💭 6 min (`TETO_S`), com `WORK_WORKER_CONCURRENCY=3` e `WORK_TENANT_CONCURRENCY=2` (`smith_worker.py:49-50`): a 3ª cotação simultânea da corretora espera e a promessa "1 a 2 min" quebra; Rotinas e renovações também esperam. Mesmo padrão do `canal.cotacao`. | leitura | medir no canário; `dormir` entre consultas (como o canal faz no `:317`) |
| P6 | "Ver apresentação" sem link no run (caso `sem_publicar`) republica com QUEM CLICOU como "Quem vai cuidar de você"/"Quero fechar" e sem `apolice_atual`/`primeiro_nome` (`api/cotacoes.py:528`). | leitura | usar o `solicitante_user_id` e o payload do run |
| P7 | Configurar: escolher uma entrada IGUAL ao padrão do produto não é enviada (`ConfigurarCotacaoEQcm.tsx`), então volta à BASE da corretora (se ela tiver base diferente), não ao padrão — a tela relida mostra outro número. | leitura (D-B4-01) | comparar com o efetivo da base |
| P8 | 💭 Erro transitório no `acompanhar` grava "Não consegui terminar esta cotação" (`workflow.py:269`) antes de o erro subir; se o worker retentar e entregar, o corretor lê "não terminou" e depois "Pronto". | leitura, não medido | gravar o aviso só no `ao_desistir` |
| P9 | O cinto `sem_documento_inteiro` não pega CPF com espaços (`'CPF 529 982 247 25'` sai cru). As saídas das ferramentas não produzem esse formato hoje. | 📊 sonda S3 | baixa |

## 4. O QUE ESTÁ BOM (com evidência)

- **Identidade fora do modelo:** `nodes.py:3667-3677` descarta `company_id/conversation_id/user_id/session_id` do modelo
  e injeta os do estado, incondicionalmente; o fio passa `user_id`/`session_id` FALSOS e o estado vence (7 passed).
  `_turno` reconfere a conversa por `company_id`+`session_id`, o dono e o vínculo ativo (`cotacao_tool.py:112-142`).
- **Confirmação:** chave com `company_id`, conteúdo cifrado no cofre, dono/conversa conferidos SEM consumir, uso único
  pelo `DEL == 1` (`confirmacao.py:97-127`); mutações 1 e 2 ficam vermelhas.
- **A conta do Agger:** o canário lê `conta_exigida_id`/`conta_regra` do cálculo, não a frase (`test_…_a_conversa.py:244`);
  sem conta da pessoa → `cotacao_da_corretora` + aviso, mutação 3 vermelha.
- **Multi-tenant:** API filtra no banco e de novo no código (`_e_da_corretora`), mutação 6 vermelha; o fio prova
  B ↛ A em lista, detalhe e ferramenta. Proxy Next tira `company_id`/`user_id` da sessão e ignora o corpo.
- **Work OS:** `Concluido` só muda o `result_payload` de quem o devolve; `concluir(…, resultado=None)` grava `{}` como
  antes (`runs.py:828-830`) — outros workflows intactos. Mensagem com `id` uuid5(run+tipo): 2 execuções → 1 linha.
- **Capability:** binding só do `core`, global por papel; papel vazio → resolver devolve `{}` (`capability_resolver.py:68-70`);
  o grafo ainda confere o papel (`graph.py:601-606`).
- **Página de venda:** nas 6 amostras, 0 ocorrências de "Quem Cobra Menos"/"Nível 5"/"melhor das"/duelo/contagem;
  "N anos" só com `founded_year` (Vega sem ano → sem o fato); Google com fonte "ficha confirmada"; sem número → sem
  barra e "responda a mensagem em que recebeu este link"; "Nada é cobrado agora" na barra; nenhum CPF no HTML.
  O byte a byte da renovação/carteira/canal passa (`test_as_outras_paginas_nao_mudaram_byte_a_byte`).

## 5. MAIOR LACUNA DA RÉGUA

Os guardas da conversa rodam com a publicação **dublê** (`test_spec132b_a_conversa.py:192-212`), e o fio com a real
não exercita o **ajuste** nem a **apólice/economia** — por isso B1 e B2 atravessaram 60 testes verdes. E nenhum guarda
modela "o modelo encadeia as ferramentas sem o corretor falar" (B4): o próprio fio faz isso e passa.

## 6. CONFIANÇA

Alta nos 4 blockers (cada um reproduzido pelo código real, dublê só na borda). Não medido: o canário real, o tempo
real até a resposta, o comportamento do LLM de verdade (B4 depende de ele encadear — a sonda prova que o código
deixa), o `next start`/rotas montam (fora do meu pedido), o retry do worker em P8.
