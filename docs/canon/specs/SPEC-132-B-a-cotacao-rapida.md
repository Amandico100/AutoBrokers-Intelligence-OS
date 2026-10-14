# SPEC-132-B — A Cotação Rápida: o corretor pede no chat, recebe a cotação na tela e um link de VENDA com a cara da corretora

> **v1.0 · 14/10/2026** · gerente Opus 5.5 · branch `spec/132-o-chat-e-a-cotacao` (D-132B-00) · rito AAA v13.2 · **CRÍTICO**.
> Fonte: PLANO-MESTRE §SPEC-132 · pedido do Founder de 14/10 · D-131-04/21/42/47 · D-131-0-05/11 · SITUACOES-DE-ENTRADA (E1, E2, E4,
> E7, E8, E13, E14) · as frentes do BLOCO 0 (§2.1). Absorve a SPEC-EXTRA-004. 📊 medido · 💭 ilustrativo.

## 0. EXECUTION CARD
```
OUTCOME ........ o corretor escreve no chat (ou manda a apólice, a foto do documento, um áudio) "cota o Onix do João…"; o AutoBrokers
                 pergunta SÓ o que falta, mostra o resumo, ele confirma, e em ~1–2 min volta NA MESMA CONVERSA a cotação resumida
                 (3 opções) + o link de uma APRESENTAÇÃO DE VENDA com a cara da corretora, pronto para copiar e mandar ao cliente.
                 O cálculo sai no Agger DELE (Meu perfil) e, sem ele, no da corretora — com aviso. O aplicativo "Cotação Rápida"
                 fica completo (Início · Configurar · Cotações · Dúvidas) e a Renovação passa a se chamar "Renovação Automática".
RISCO .......... 7 · segurado 3 (a página de venda) · sai do prédio 3 (cria cálculo no Agger e nº de cálculo nas seguradoras) · semanal 1
SUPERFÍCIE ..... 2 · vários comportamentos sobre peças que existem (motor, qual_agger, proposta, casca de aplicativo)
PISO ........... CRÍTICO: cálculo que sai do prédio · sessão do Agger de uma PESSOA · filtro company_id · migration de catálogo
NÍVEL .......... CRÍTICO · builders Opus 5.5 xhigh · juiz ‖ red team · juiz de DESIGN da página (meta ≥ 90, Founder pediu perto de 100)
O FIO .......... §2 · `backend/tests/test_spec132b_o_fio.py` = 1ª entrega da B4, VERMELHO
PARALELISMO .... B1 ‖ B2 ‖ B3 (arquivos disjuntos, §5) → B4 costura (registro da ferramenta e do router, depois da 132-A)
GATES .......... fio · 2 corretoras · mutações · tsc · rotas montam + next start + /api/cotacoes · design ≥ 90 · canário real · bateria
REFERÊNCIA ..... interna: a "carteira" da 130-A (📊 91) e a página de renovação da 131-B (📊 93); o QCM (o que NÃO copiar); externa: §8
O ELO .......... "a cotação sai no Agger DO CORRETOR porque ele está no Meu perfil" → o canário lê `multicalculo_pedidos.conta_id` e o
                 `qual_agger` auditado, nunca o texto da resposta
FAIXA .......... 💭 7–10 h · fatia ≤ 1h15
```

## 1. O contrato
**Muda:** uma ferramenta de COTAÇÃO no agente CORE (preparar → confirmar → calcular → ajustar) · o pedido a partir da conversa, da
placa (FIPE/ano/combustível) e da apólice anexada (ficha 130-B, `situacao=novo_com_apolice`) · um Work Run que espera o motor e
ESCREVE A RESPOSTA NA MESMA CONVERSA (`work_runs.conversation_id` → `messages`, que a tela já ouve pelo Realtime) · a página de
COTAÇÃO = página de VENDA nova (template único, identidade de cada corretora) · o aplicativo "Cotação Rápida" com a aba Cotações e a
API `/api/cotacoes` · o Configurar da cotação mostrando as REGRAS do cálculo (e editando as seguras) · os nomes "Cotação Rápida" e
"Renovação Automática".
**Não pode mudar:** o motor (`MulticalculoProvider`, `motor.py`) — só é CHAMADO com `servico="cotacao"` · `qual_agger.decidir` (já tem
o ramo da cotação: a pessoa → a corretora com aviso) · a página do QCM (marca isenta) e a de RENOVAÇÃO (D-131-42: copy nunca cruzada) ·
**o produto não envia nada ao cliente**: o link vai para o CORRETOR copiar/mandar · nunca apagar cálculo de pessoa no Agger · nada de
"Quem Cobra Menos", "Nível 5" ou duelo entre corretoras na página da corretora.

## 2. O FIO
```
chat: "cota o Onix 2022 placa ABC1D23 do João, CPF…, nasc…, CEP…" (+ anexos da 132-A) → agente CORE → ferramenta
`cotacao_preparar(campos)` → pedido.de_conversa / de_ficha → PedidoDeCalculo.faltando() → (falta? o agente pergunta SÓ o que falta,
numa mensagem) → completo: resumo + `confirmacao_id` (vale 30 min, uma vez) → corretor "sim" → `cotacao_disparar(confirmacao_id)` →
porta.calcular(company_id, pedido, servico="cotacao", solicitante_user_id=<quem pediu>) → qual_agger: a conta DELE ou a da corretora
(+ aviso) → multicalculo_pedidos + fila → Work Run `cotacao.chat` (conversation_id) responde já "Calculando em N seguradoras…" →
espera (porta.consultar; quadro fecha ou 💭 6 min) → comparacao → proposta.publicar_cotacao → /r/<token> (página de VENDA) →
`messages` (assistant) na MESMA conversa: resumo de 3 opções + o link + "Copiar a mensagem para o cliente" → aba Cotações mostra o item
```

## 2.1 BLOCO 0 (14/10/2026)
| # | premissa | estado | o que muda |
|---|---|---|---|
| C1 | existe ferramenta de cotação no chat? | 📊 0 (grep `multicalc|cotac` em `agents/tools/`: só uma lista de palavras em `graph.py:748`); `servico="cotacao"` sem chamador | nasce aqui, chamando a porta |
| C2 | as regras | 📊 `config.PADRAO_DO_PRODUTO` (`config.py:34-223`) + `multicalculo_config` (📊 0 linhas nas 3 corretoras, 14/10); a tela edita só modo/exceções/preferidas (`config.py:806-807`) | Configurar mostra TODAS as regras efetivas e edita opções, comissão de entrada e validade |
| C3 | qual Agger | 📊 `qual_agger.py:319-340`: sem conta da pessoa → `cotacao_da_corretora` + aviso; nunca recusa | a ferramenta repassa `solicitante_user_id`; o aviso vai na resposta |
| C4 | placa supre FIPE/ano/combustível | 📊 `SERVICOS_EM_QUE_A_PLACA_SUPRE = ("renovacao",)` (`pedido.py:110`); o canal já busca pela placa | a cotação entra no conjunto, pela MESMA busca |
| C5 | apólice anexada → pedido | 📊 `pedido.de_apolice` sempre `renovacao=True`, chamador único `madrugada.py`; o anexo do chat vira só TEXTO | função irmã `de_ficha` (novo com apólice) que reusa o miolo |
| C6 | volta à conversa | 📊 `work_runs.conversation_id` existe (migration `20260826_02`); 0 escritores em `messages` ao fim de run; a tela ouve `postgres_changes` (`chat/page.tsx:243`) | o Work Run grava a mensagem do assistente |
| C7 | tempo do motor | 📊 LAUDO-I1: 1ª oferta 6 s · 80 % em 27 s · fecha em 64 s · p90 406 s; RE 46–48 s | promessa "1 a 2 minutos", corte em 💭 6 min com o que chegou |
| C8 | a marca na página | 📊 `brand_profiles`: Resulta publicada (logo, SUSEP, tagline, site, about/missão; sem `founded_year`, sem `contact.whatsapp`, `differentiators` vazio); AutoFleet publicada (2011) ; Google só por `google_confirmado` | a página usa só o que existe; bloco sem dado SOME (nunca inventa) |
| C9 | InfoCap nas corretoras | 📊 14/10 gerente: Resulta e AutoFleet com a SUA conexão `connected/healthy`; a de ensaio arquivada | o cliente da carteira (E11) pode ser lido — fica para pendência |
| C10 | catálogo | 📊 `auxiliary_templates`: `cotacao` 'Cotação' ativo, `renovacao` 'Renovação' ativo | migration de nomes + FAQ da cotação |

## 3. Dados — migration `backend/supabase/migrations/20261014_02_spec132b_cotacao_rapida.sql` (expand-only, aplicada pelo gerente)
- `auxiliary_templates`: `name` 'Cotação Rápida' (slug `cotacao`) e 'Renovação Automática' (slug `renovacao`); `faq` e frase da Cotação.
- Nenhuma tabela nova: a cotação do chat É um `multicalculo_pedidos` (`servico='cotacao'`, `solicitante_user_id`) + um `work_runs`
  (`workflow='cotacao.chat'`, `conversation_id`) + o artefato `proposal.quote`. Se faltar coluna para ligar pedido ↔ conversa ↔ artefato,
  vai em `work_runs.payload`/`result` (nunca em coluna nova sem necessidade). APPLY · VERIFY · ROLLBACK escritos antes.

## 4. O desenho
- **A conversa:** a ferramenta devolve ao modelo o que falta em linguagem de gente ("Faltam: data de nascimento e CEP onde o carro
  dorme"); o modelo pergunta tudo numa mensagem; nunca pede o que já veio (placa supre o carro; a apólice supre quase tudo). O resumo
  antes de calcular: cliente (CPF mascarado), carro, CEP, uso, condutor, as opções que vão ser calculadas, "no seu Agger"/"no Agger da
  corretora (você ainda não conectou o seu)". Confirmação explícita ("sim", "pode", "calcula"); um `confirmacao_id` dispara UMA vez.
- **A resposta pronta (no chat):** "Pronto: 11 seguradoras responderam." + tabela de 3 linhas (Recomendada · Mais em conta · Mais
  completa: seguradora, parcela, à vista, franquia) + "Apresentação para o cliente: <link>" + um bloco "Mensagem para o cliente" curto
  (o que ele copia e manda). O Copiar da 132-A copia tudo; o bloco da mensagem é o que importa.
- **A página de COTAÇÃO = venda (template único, a cara de cada corretora):** a ordem (cada bloco sem dado some):
  1. **Cabeçalho da marca** — logo, nome, "Corretora de seguros · SUSEP nº" (autoridade), cor da marca.
  2. **Hero** — "{Nome}, a cotação do seu {carro} está pronta" · "Comparamos {N reais} seguradoras para você — sem custo e sem
     compromisso" · o cartão da RECOMENDADA com a parcela em destaque, à vista, franquia e "Por que recomendamos" (1 linha).
  3. **As 3 opções** — Recomendada · Mais em conta · Mais completa (carrossel no celular, lado a lado no notebook) + "Comparar coberturas".
  4. **Economia** — só com a apólice atual lida: "R$ X a menos por ano que o seu seguro atual" (nunca sem prova).
  5. **Por que fechar com a {corretora}** — fatos: anos de mercado (`founded_year`), SUSEP, nº de seguradoras com quem trabalha, nota do
     Google CONFIRMADA, os diferenciais que a corretora escreveu; e o papel do corretor (ele representa VOCÊ diante da seguradora).
  6. **Quem vai cuidar de você** — o corretor que cotou (nome, função, WhatsApp de trabalho confirmado) → senão a corretora.
  7. **Como funciona depois do sim** — 3 passos verdadeiros para qualquer seguradora (fala com a gente → proposta e, se a seguradora
     pedir, vistoria → apólice no seu e-mail).
  8. **Se acontecer alguma coisa** — sinistro e assistência 24 h (texto da config).
  9. **Perguntas que todo mundo faz antes de fechar** — por que corretora · se eu bater o carro · o preço muda? (válido até a DATA real) ·
     como pago · posso cancelar? · preciso de vistoria? · meus dados estão seguros? (respostas honestas, configuráveis por corretora).
  10. **Fecho** — "Preços válidos até {data}" (nunca cronômetro) · "Nada é cobrado agora." · barra fixa [Quero fechar] [Tirar uma dúvida].
  11. **Rodapé legal** — SUSEP, "sujeito à aceitação da seguradora", como comparamos, validade.
  ⛔ nunca: "Quem Cobra Menos", "Nível 5", duelo/ranking entre corretoras, "a melhor das N" sem ser a 1ª do ranking, número inventado,
  depoimento inventado, contagem regressiva. Visual: a linguagem da "carteira" (Instrument Sans, cartões, AA claro/escuro, imprime,
  funciona sem JS) com a paleta da corretora.
- **O aplicativo "Cotação Rápida"** (a casca da 131-B): **Início** (o que é: "peça no chat ou no WhatsApp e receba a cotação pronta
  para mandar"; Como começar: Agger da corretora · o MEU Agger · as regras); **Configurar** (O que fazer · As regras do cálculo: quais
  opções, comissão de entrada, validade — o resto mostrado como "padrão do AutoBrokers" · Seguradoras preferidas · Exceções); **Cotações**
  (lista: cliente, carro/risco, quando, quem pediu, estado — Calculando · Pronta · Sem resposta —, a melhor parcela; Minhas · Todas;
  detalhe com [Ver apresentação] [Copiar mensagem] [Enviar pelo WhatsApp] (wa.me no aparelho de quem clica, como a renovação) e
  "Abrir no Agger"); **Dúvidas**.

## 5. Fatias (cada arquivo, UM dono)
| fatia | entrega | arquivos |
|---|---|---|
| **B1 · a cotação na conversa** | ferramenta, pedido da conversa/placa/ficha, confirmação, Work Run que responde na conversa, ajuste | `backend/app/agents/tools/cotacao_tool.py` (NOVO) · `backend/app/services/cotacao/*` (NOVOS: `pedido_da_conversa.py`, `confirmacao.py`, `workflow.py`, `resposta.py`) · `backend/app/services/multicalculo/pedido.py` (placa na cotação + `de_ficha`) · `backend/app/services/work/workflows.py` (só o registro do `cotacao.chat`) · `backend/tests/test_spec132b_a_conversa.py` (NOVO) |
| **B2 · a página de venda** | template de cotação, `publicar_cotacao`, mensagem para o cliente, guardas no HTML servido | `backend/app/services/artifacts/proposta_cotacao_html.py` (NOVO) · `backend/app/services/artifacts/proposta_html.py` (só o desvio para a cotação) · `backend/app/services/artifacts/templates.py` (só se o desvio exigir) · `backend/app/services/multicalculo/proposta.py` · `backend/app/services/multicalculo/mensagem.py` · `backend/app/services/multicalculo/config.py` (chaves `cotacao.pagina.*` e as editáveis da cotação) · `backend/tests/test_spec132b_a_pagina_de_venda.py` (NOVO) · os testes antigos de página que mudarem por verdade vencida (§9.3) |
| **B3 · o aplicativo** | migration, catálogo, aba Cotações, Configurar com regras, API, nomes | `backend/supabase/migrations/20261014_02_spec132b_cotacao_rapida.sql` · `lib/auxiliaries/catalog.ts` · `components/aplicativos/cotacao/*` · `components/aplicativos/configurar/*` · `components/aplicativos/renovacao/AbaConfigurar.tsx` (só o nome) · `components/aplicativos/casca/a-loja-e-a-casca.test.mjs` · `app/api/cotacoes/**` (NOVOS) · `backend/app/api/cotacoes.py` (NOVO) · `backend/app/api/servicos_da_corretora.py` · `backend/tests/test_spec132b_api_cotacoes.py` (NOVO) |
| **B4 · costura** | registro da ferramenta no grafo e do router; o fio; canário; exemplos publicados | `backend/app/agents/graph.py` (só o registro) · `backend/app/main.py` (só o router) · `backend/tests/test_spec132b_o_fio.py` |

**Contratos:** B2 exporta `async publicar_cotacao(company_id, pedido_id, *, pessoa_user_id, apolice_atual=None, db=None) -> {token,
url, artifact_id, resumo}` e `mensagem_de_cotacao(modelo, link) -> {texto, texto_curto}` · B1 chama os dois e
`porta.calcular(..., servico="cotacao", solicitante_user_id=…)` · B3 lê `multicalculo_pedidos` (servico='cotacao') + `work_runs`
(`cotacao.chat`) + o artefato, e chama `publicar_cotacao` no "Ver apresentação" quando ainda não houver link.

## 6. A régua
- **Fio:** da frase do corretor (modelo DUBLÊ que chama a ferramenta) ao `messages` do assistente na MESMA conversa com o link, motor
  com o Agger DUBLÊ na borda, e o HTML SERVIDO pelo `/r/` é a página de VENDA.
- **Mutações** (cada mutação VERMELHA uma vez): (1) disparar sem confirmação · (2) o mesmo `confirmacao_id` dispara 2× · (3) `solicitante_user_id` some (vai sempre à
  corretora) · (4) a página de cotação mostra "Quem Cobra Menos"/"Nível 5"/duelo · (5) número sem prova ("economia" sem apólice, "N
  anos" sem `founded_year`) · (6) a API de cotações devolve item de OUTRA corretora · (7) CPF cru na resposta do chat.
- **Isolamento:** ferramenta, Work Run e API com duas corretoras.
- **Canário real** (gerente, verba): 1 cotação AUTO pela corretora de ensaio ou pela de origem com a conta de robô, sem enviar nada a
  cliente; 📊 tempo até a resposta na conversa; a conta usada lida do banco.
- **Juiz de design:** a página de venda servida, celular e notebook, claro e escuro, com a marca de DUAS corretoras; o aplicativo.
- **Exemplos para o Founder:** a página de RENOVAÇÃO e a de COTAÇÃO publicadas com a identidade da corretora-piloto, dados fictícios e a
  faixa "Exemplo — dados fictícios".
- **Verba:** 💭 ≤ US$ 1,00 (canário + exemplos).

## 7. Decisões desta SPEC
| # | decisão | nota | contra |
|---|---|---|---|
| D-132B-00 | 132-A e 132-B no MESMO branch (construídas em paralelo na mesma árvore) | 80 | dois branches em série 60 (+2 h) |
| D-132B-01 | A página de COTAÇÃO vira página de VENDA nova (template único com a marca de cada corretora); a "carteira" segue só onde já é usada | 88 | remendar a carteira 65 |
| D-132B-02 | Bloco sem dado SOME; nenhum diferencial, nota, ano ou economia inventados | 95 | textos padrão "de efeito" 30 |
| D-132B-03 | Confirmação explícita com `confirmacao_id` de uso único (30 min) antes de calcular | 92 | calcular direto 40 |
| D-132B-04 | A resposta volta na MESMA conversa (Work Run grava `messages`) | 90 | "veja em Entregas" 45 |
| D-132B-05 | O link vai ao CORRETOR (copiar / wa.me do aparelho dele); o produto não manda nada ao cliente | 92 | enviar direto 20 |
| D-132B-06 | Configurar mostra TODAS as regras efetivas; edita só opções, comissão de entrada e validade (o resto: "padrão do AutoBrokers") | 82 | editar tudo 55 · só mostrar 70 |
| D-132B-07 | Nomes: "Cotação Rápida" e "Renovação Automática" (Founder) | F | — |
| D-132B-08 | Exemplos com a marca real + faixa "Exemplo — dados fictícios" | 85 | sem faixa 50 (pode circular como real) |

## 8. O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS
1. **https://www.lemonade.com/car** · faz: cotação em minutos, preço em destaque e um passo claro · modelamos: o hero com a parcela e
   o próximo passo · rejeitamos: o "100 % digital, sem corretor" (aqui o corretor é o diferencial) · juiz: acha a parcela e o CTA acima
   da dobra no celular.
2. **https://www.youse.com.br/seguro-auto/** · faz: planos lado a lado com coberturas e "mais escolhido" · modelamos: Recomendada ·
   Mais em conta · Mais completa · rejeitamos: selo "mais escolhido" sem dado · juiz: conta 3 cartões e confere o "por que".
3. **https://www.nngroup.com/articles/trustworthy-design/** · faz: confiança por fatos verificáveis, contato humano e transparência ·
   modelamos: SUSEP, anos, quem cuida de você, validade real · rejeitamos: selos genéricos · juiz: cada fato tem origem no banco.
4. **https://baymard.com/blog/perceived-security-of-payment-form** · faz: sinais de segurança perto da decisão · modelamos: "Nada é
   cobrado agora" e "seus dados" junto do botão · rejeitamos: cadeados decorativos · juiz: o texto está na barra fixa.
5. **https://www.nngroup.com/articles/comparison-tables/** · faz: ≤ 5 itens, atributos consistentes · modelamos: "Comparar coberturas"
   com as mesmas linhas para as 3 · rejeitamos: tabela de 16 seguradoras aberta · juiz: conta colunas no celular.

## 9. O QUE SAIU (fora desta SPEC, com destino)
O WhatsApp do corretor como atalho do chat → **132-C** · o cliente da carteira (E11, cadastro da InfoCap) e a cotação de outra corretora
como alvo (E5) → pendência com destino 133-B/135 · negociar com o cliente → 135 · RE na página de venda além do que a comparação já
traz → 130-C · vida e moto → 129-D.
