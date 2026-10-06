# SPEC-130-A — A comparação, a proposta e a página "uau"

> v1.0 · 06/10/2026 · Programa Multicálculo, passo 4 (base das duas linhas) · rito AAA v13, 🔴 CRÍTICO por piso ·
> branch `spec/130-A-a-proposta` · ficha: `programa-multicalculo/PLANO-MESTRE-MULTICALCULO.md` §4 "SPEC-130" (130-A) ·
> decisões: D-MC-44, 55, 60, 62–74 (`FOUNDER-DECISIONS.md`) · insumo: `programa-multicalculo/ESTRATEGIA-COMERCIAL-DAS-CORRETORAS.md`

## 1. EXECUTION CARD
```
OUTCOME ..............  um pedido do motor (129-B) vira PROPOSTA: as ofertas comparadas igual-com-igual (as NÃO comparáveis à
                        parte), a corretora vencedora entre as parceiras, 2–3 opções por situação com nota 0–100 e motivos, a
                        validade, a mensagem de WhatsApp pronta (2 opções + o link, D-MC-74) e a página "uau" ÚNICA no /r/,
                        vestida da marca da corretora anfitriã (a vencedora). Serve a 133-A, a 131 e a 132. Para QUALQUER ramo.
RISCO ................  7 — ALCANCE 3 (o segurado abre a página) · REVERSIBILIDADE 2 (link público + migration) · FREQUÊNCIA 2
SUPERFÍCIE ...........  2 — peças novas sobre o Artifact Hub, a marca e a porta do motor, que já existem
PISO APLICADO ........  §3.2 — migration nova (estrutura + RLS) · link público com dado do cliente · lê a marca/oferta de uma
                        corretora (a anfitriã) para a página do canal (outra company)
NÍVEL ................  🔴 CRÍTICO · gerente Opus 5.5 · builders Opus 5.5 xhigh · juiz ‖ red team · confirmação se houver blocker
O FIO ................  porta.consultar (ofertas+eventos) → comparacao.comparar → proposta.montar (situação, opções, nota,
                        anfitriã+marca+prova social, validade) → artifacts (kind 'proposal': criar→render→publicar→compartilhar)
                        → /r/<token> (route.ts, CSP com o hash do NOSSO script) → página; e proposta → mensagem.whatsapp(link)
                        · teste do fio `test_spec130a_o_fio.py`: pedido REAL do canário (dublê só no Supabase/HTTP) → URL →
                        o HTML servido tem as 3 opções, a anfitriã certa, 0 comissão, 0 produto diferente no ranking
PARALELISMO REAL .....  F1 (comparação+config+negociação) ‖ F2 (página+rota) — arquivos disjuntos (§6) → F3 costura
UNIDADES .............  U1 comparação · U2 configuração + manual de negociação + migration · U3 funções da porta (mais barato,
                        alvo) · U4 a proposta (modelo da página) · U5 a página + o /r/ · U6 a mensagem do WhatsApp · U7 publicar +
                        comando + canário
COESÃO ...............  U1+U2+U3 (o comparador lê a config; a negociação usa os dois) · U5 sozinha contra o CONTRATO §5 ·
                        U4+U6+U7 (consomem os dois lados)
TIME .................  gerente · 3 designers (D0) + painel de críticos · F1 · F2 · F3 · juiz ‖ red team · confirmação
REFERÊNCIA ...........  interna: Artifact Hub (`services/artifacts/`), marca (`services/brand/capture.py:snapshot_para_artefato`),
                        porta (`services/multicalculo/porta.py`), `/r/` (`app/r/[token]/route.ts`) · externa §8
GATES ................  §9
O ELO ................  "a página mostra só o comparável PORQUE o comparador separa antes de ranquear": o teste do fio afirma
                        sobre o HTML SERVIDO (não sobre a função) que nenhum produto diferente aparece no ranking
FAIXA DE RELÓGIO .....  💭 8–12 h (inclui o desenho AAA da página e 1 pergunta ao Founder)
```

## 2. O que muda para quem usa
- **Segurado:** recebe no WhatsApp 1–2 mensagens curtas (as 2 melhores opções + 1 linha-resumo + o link) e abre uma página no
  celular: o resultado no topo, um carrossel de ARRASTAR com 3 opções (o próximo cartão aparece pela borda), "comparar lado a
  lado", todas as seguradoras comparáveis do menor ao maior, as de produto diferente numa linha com o porquê, a corretora como
  "anfitriã" (só dado verdadeiro), o sinistro, as dúvidas reais e o botão fixo "Quero fechar" (WhatsApp da corretora).
- **Corretora:** a página veste a identidade dela (logo, cores, tema auditado do cadastro `brand_profiles`); sem marca cadastrada,
  um visual neutro digno + aviso na caixa dela. Tudo que é número comercial é CONFIGURAÇÃO dela (com padrão do produto).
- **133-A / 131 / 132:** ganham `montar_proposta`, `publicar_proposta`, `mensagem_whatsapp`, `ordem_do_mais_barato`,
  `cotacao_alvo` e o manual de negociação como dado.

## 3. O que NÃO pode mudar
O motor e o robô da 129-B (só leitura deles) · o `/r/` dos relatórios (CSP sem script continua para eles) · nenhuma mensagem sai
(o envio é da 133-A) · nenhum cálculo novo no Agger nos testes (o canário usa os 104 preços já no banco) · a comissão nunca chega
à página nem à mensagem · nenhum nome de corretora no código (CLAUDE.md §13.9).

## 4. As unidades
### U1 · A comparação — `backend/app/services/multicalculo/comparacao.py` (puro)
- `classificar(oferta) -> Classe` : COMPLETA (compreensiva, casco = 100 % FIPE, prêmio anual) · DIFERENTE com motivo humano:
  "não cobre batida no seu carro" (roubo/furto/incêndio), "só cobre danos a terceiros" (RCF), "paga só N % da tabela FIPE"
  (casco < 100), "preço de assinatura mensal" (Azul por Assinatura e todo `premio_total` que é mensal — P-129B-06) · para outros
  ramos a regra vem por ramo (tabela de regras por ramo; auto = 31 hoje, os demais caem em "comparável se mesma configuração").
- `comparar(ofertas, eventos, *, config) -> Comparacao`: melhor oferta por seguradora × corretora × opção; ranking das COMPLETAS
  (menor primeiro); `diferentes` (agrupado, sem duplicata); `nao_responderam` (família → frase humana: INSTABILIDADE "sistema da
  seguradora indisponível", ACEITACAO "não aceitou este perfil", CREDENCIAL/PERMISSAO "não foi possível consultar", PENDENTE "não
  respondeu a tempo"; ⛔ nunca o texto cru da seguradora); `entre_corretoras` (melhor completa de cada parceira, a VENCEDORA =
  menor; empate pela regra da config).
- `opcoes(comparacao, *, situacao, apolice_atual=None, config)` (D-MC-66/69): sem apólice → Recomendada (menor completa) ·
  Outra completa (2ª menor completa; "Menor franquia" se a menor franquia do quadro for de outra seguradora) · Mais em conta (menor
  econômica comparável) · com apólice → "Igual à sua atual" (mesma seguradora e mesma cobertura se houver, senão a menor com a
  mesma cobertura) + Recomendada + Mais em conta · renovação → idem com "Sua renovação". Cada opção: `nota` 0–100 + `motivos`
  (fatos com número: posição no preço, franquia, carro reserva, assistência) + `o_que_muda` em relação à recomendada.
- A NOTA: determinística, pesos na config (preço, franquia, coberturas), nunca acima de 100, sempre com ≥ 2 motivos verdadeiros.
### U2 · Configuração, manual e migration
- `config.py`: `PADRAO_DO_PRODUTO` (ÚNICO lugar com os números de D-MC-62…72: comissões 15/12/10, alvo 10–15 %, validade padrão
  5 dias, lembretes, pesos da nota, presets por opção, quantas opções no WhatsApp = 2) + `carregar(company_id)` = padrão ⊕ a linha
  da corretora. 🔴 `grep` dos números fora de `config.py` = defeito.
- `manual_de_negociacao.py`: alavancas na ordem D-MC-67 com limites (D-MC-68: ≤ 12 % sozinho, 10 % só com o corretor), objeções
  reais (§1.5 da estratégia) com resposta curta, as 3 estratégias por situação — como DADO (dict), consumido pela 133-A.
- Migration `backend/supabase/migrations/20261006_01_spec130a_config.sql`: tabela `multicalculo_config (company_id pk → companies,
  config jsonb, atualizado_em, atualizado_por)` + RLS + policy de leitura/escrita por company + COMMENT. APPLY/VERIFY/ROLLBACK no
  arquivo, escritos ANTES.
### U3 · As funções da porta
`MulticalculoProvider.ordem_do_mais_barato(company_id=, oferta_ref=)` → a lista de `Ajuste` na ordem D-MC-67 que a seguradora
OBEDECE (Porto/Azul/Itaú: desconto antes da comissão — a lista vem da config, não do código) · `cotacao_alvo(company_id=, pedido_id=,
alvo=, seguradora=None, aprovado_pelo_corretor=False)` → planeja (puro, `negociacao.py`) e dispara os recálculos pela porta já
existente (`recalcular`), em paralelo, e devolve a combinação que chega no alvo com a MAIOR comissão; abaixo do piso autônomo
(12 %) sem `aprovado_pelo_corretor` → devolve `precisa_aprovacao` com o que o corretor aprovaria; corte de cobertura → listado.
### U4 · A proposta — `proposta.py`
`montar_proposta(company_id=, pedido_id=, situacao=, apolice_atual=None, primeiro_nome=None) -> dict` no CONTRATO §5: chama a porta
(`consultar`, que já corta a comissão para quem não é dono), a comparação, as opções, a anfitriã (a vencedora; para pedido de
corretora = ela mesma) com a marca de `snapshot_para_artefato` da ANFITRIÃ (só se `is_published`; senão neutro) e a prova social
SÓ do que estiver no cadastro/config confirmado (Google: nota + nº + data + fonte, só com a ficha CONFIRMADA na config — 📊 a busca
por nome achou outra empresa para uma das corretoras, 06/10), a validade (`hoje + min(validade das seguradoras do quadro)`, dias da
config por seguradora; padrão 5), o aviso legal.
### U5 · A página e o /r/
- `backend/app/services/artifacts/proposta_html.py`: `render_proposta(modelo) -> (html, hash_do_script)` a partir do DESENHO
  APROVADO pelo Founder (D0). Um arquivo, CSS inline, o NOSSO script inline (sempre o mesmo texto → hash fixo), dados num
  `<script type="application/json">`, logo embutido em `data:`, todo texto escapado. Funciona SEM JavaScript (carrossel por CSS
  scroll-snap; `<details>`); o script só melhora (pontos, teclado, o "Quero fechar" acompanha a opção, comparar). Impressão (PDF pelo
  navegador) com CSS de impressão. `og:title/og:description` sem dado pessoal.
- Artifact Hub: template `proposal.quote` (kind `proposal`, audience client) registrado em `templates.py`; versão nova por ajuste.
- `app/r/[token]/route.ts`: quando o artefato é `proposal`, a CSP inclui `script-src 'sha256-<hash>'` (o hash que o backend
  devolve); relatórios continuam sem script. Nada de `unsafe-inline` para script.
### U6 · A mensagem — `mensagem.py`
`mensagem_whatsapp(modelo, link) -> list[str]` (D-MC-74): balão 1 = resumo + as 2 opções (`*negrito*`, `_itálico_`, ≤ 2 emojis,
"das N que cotei", nunca "o mais barato do mercado") · balão 2 = o link + validade + 1 linha da anfitriã (só dado verdadeiro). ≤ 700
caracteres no total.
### U7 · Publicar, comando, canário
`publicar_proposta(company_id=, pedido_id=, ...) -> {url, token, artifact_id, versao, mensagem}` (criar → render → publicar →
compartilhar, validade do link = a da proposta + folga da config) · comando `python -m app.services.multicalculo.comando_proposta
--pedido <id>` (o Founder roda no contêiner) · canário: o pedido real `d0bb15ba` → URL aberta por HTTP real no `next start` local.

## 5. O CONTRATO da página (o modelo que U4 produz e U5 consome)
O formato de `scratchpad/design/dados_pagina.json` (cenário único, não dois): `origem` (corretora|canal) · `cliente.primeiro_nome` ·
`veiculo` (ou `bem` para outros ramos: rótulo + descrição) · `situacao` · `resumo{seguradoras_cotadas, com_preco_comparavel,
com_produto_diferente, nao_responderam, corretoras_comparadas?}` · `opcoes[3]{id, rotulo, seguradora, produto, premio_anual,
parcelas{vezes,valor}, franquia{valor,tipo}, coberturas[{chave,nome,valor}], nota, motivos[], o_que_muda[]}` · `ranking[]` ·
`produto_diferente[]` · `nao_responderam[]` · `entre_corretoras[]?` · `anfitria{nome, marca_cadastrada, logo_data_url, tema_claro,
tema_escuro, cidade, desde, susep, google?, whatsapp, sinistro[]?}` · `faq[]` · `validade_ate` · `aviso_legal` · `cta{whatsapp_url,
texto_por_opcao}`. Ausente = não aparece (nunca "—" inventado).

## 6. As fatias e os arquivos (cada arquivo, um dono)
- **D0 · o desenho** (gerente + 3 designers + críticos, scratchpad): 3 direções → painel cego → a melhor refeita até ≥ 90 → o
  Founder escolhe (a ÚNICA pergunta da SPEC).
- **F1** (U1+U2+U3): `services/multicalculo/{comparacao,config,manual_de_negociacao,negociacao}.py`, `porta.py` (só as 2 funções
  novas), a migration, `tests/test_spec130a_{a_comparacao,a_config,a_negociacao}.py`.
- **F2** (U5): `services/artifacts/proposta_html.py`, `services/artifacts/templates.py` (o template novo), `app/r/[token]/route.ts`,
  `tests/test_spec130a_a_pagina.py`, `tests/rota_r_proposta.test.ts` (ou o equivalente que o app usa).
- **F3** (U4+U6+U7, costura): `services/multicalculo/{proposta,mensagem,comando_proposta}.py`, `tests/test_spec130a_o_fio.py`.

## 7. Decisões desta SPEC (D-130A-*, com nota)
| # | decisão | nota |
|---|---|---|
| D-130A-01 | a página é um ARTEFATO `proposal` do Artifact Hub servido pelo `/r/` (não uma página Next paralela) | 88 × página Next 70 (2º caminho de entregável, CLAUDE.md §5) |
| D-130A-02 | script só por HASH na CSP, e a página funciona sem ele | 86 × sem script 72 (sem pontos/teclado/CTA que acompanha) × `unsafe-inline` 30 |
| D-130A-03 | comparável = compreensiva + casco 100 % + prêmio anual; o resto é "produto diferente" com o motivo | 90 |
| D-130A-04 | vencedora entre corretoras = a menor RECOMENDADA (completa); empate pela config (padrão: a de maior nota no Google, senão a ordem de adesão) | 80 |
| D-130A-05 | validade = hoje + menor validade do quadro (dias por seguradora na config; padrão 5 = o menor medido, n = 4); 📊 06/10 os PDFs do negócio de 05/10 não vieram (0 copiados) → medir no 1º cálculo real | 78 |
| D-130A-06 | registro de oportunidade e consentimento (ficha) MUDA para a 133-A, onde o consentimento é colhido na conversa; a proposta publicada + o pedido já são o registro da oportunidade nesta SPEC (CHANGE-ADDENDA, ESSENCIAL) | 80 × fazer aqui sem a conversa 55 |
| D-130A-07 | o PDF do servidor (D-MC-43) fica para quando houver render fora do worker; nesta SPEC o PDF é o "imprimir" do navegador com CSS de impressão | 75 |
| D-130A-08 | a remuneração da corretora (CNSP 382) é uma opção da config, DESLIGADA até o jurídico | 70 · 🧑 caixa do Founder |

## 8. O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS
- https://www.lemonade.com — seguro sem atrito · MODELAMOS: frases curtas em 1ª pessoa, uma ação por tela · REJEITAMOS: ilustração
  própria pesada · JUIZ: abre a home no celular e compara o tom do topo.
- https://www.airbnb.com.br/rooms (qualquer anúncio) — o bloco "anfitrião" · MODELAMOS: logo, anos, avaliação com nº e fonte ·
  REJEITAMOS: selo de "superhost" inventado · JUIZ: compara o bloco da anfitriã.
- https://www.apple.com/br/iphone/compare/ — comparação lado a lado · MODELAMOS: linhas alinhadas entre as opções · REJEITAMOS:
  tabela de 40 linhas · JUIZ: abre "comparar lado a lado" e confere o alinhamento.
- https://stripe.com/br — acabamento de cartões · MODELAMOS: profundidade e borda com luz · REJEITAMOS: gradiente animado · JUIZ: screenshot.
- https://linear.app — tipografia e números · MODELAMOS: algarismos tabulares, hierarquia · JUIZ: screenshot dos preços.
- https://www.minutoseguros.com.br e https://www.policygenius.com — comparadores · REJEITAMOS: excesso de texto e de tabela.
- https://web.dev/articles/css-scroll-snap — carrossel por CSS · MODELAMOS: scroll-snap com o próximo cartão aparecendo, sem biblioteca.
- https://developer.mozilla.org/docs/Web/HTTP/Headers/Content-Security-Policy/script-src — script por hash · MODELAMOS: `'sha256-…'`.

## 9. GATES
G1 o teste do fio verde (HTML servido) · G2 comparação: as 104 ofertas reais → 0 "diferente" no ranking, Azul por Assinatura fora,
vencedora = a menor completa · G3 0 comissão no modelo, no HTML e na mensagem (duas corretoras) · G4 a marca: Resulta com o tema
dela, AutoFleet neutra, nenhum nome de corretora no código · G5 a página: 390 px sem rolagem horizontal, AA, funciona sem JS, CSP
servida com o hash certo e SEM `unsafe-inline` de script (rota real no `next start`) · G6 a mensagem ≤ 700 caracteres, 2 opções,
sem frase proibida · G7 migration VERIFY · G8 `grep` dos números comerciais fora de `config.py` = 0 · G9 `npm run test:rotas-montam`
+ `next start` + 1 requisição `/api/...` + 1 `/r/<token>` real · G10 cada guarda novo com mutação vermelha · G11 bateria em 2 metades.
