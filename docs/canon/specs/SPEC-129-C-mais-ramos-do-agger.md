# SPEC-129-C — Mais ramos do Agger: Condomínio, Residencial e Empresarial

> ⚠️ ERRATA 11/10 (SPEC-131-0-A): a medição foi feita por uma conexão com o login da AutoFleet; a InfoCap da Resulta tem RE — ver programa-multicalculo/131-0/BLOCO0-INFOCAP-A-CONEXAO-TROCADA.md

> v1.0 · 11/10/2026 · gerente Opus 5.5 · branch `spec/129-C-mais-ramos` · base `8d468b4` · rito AAA v13 · 🔴 CRÍTICO por piso
> BLOCO 0 medido em `docs/canon/programa-multicalculo/129-C/` (BLOCO0-AGGER · BLOCO0-GRAVACAO · BLOCO0-INFOCAP · AGREGADO-POR-RAMO ·
> RAMOS-NA-INFOCAP) e as fixtures saneadas em `backend/tests/fixtures/agger_ramos/` (3 formulários + 9 gravações reais, 0 dado pessoal).
> Origem: D-MC-73 e o retorno do Founder de 10/10 (`programa-multicalculo/RETORNO-DO-FOUNDER-2026-10-10.md`).

## 1. EXECUTION CARD
```
OUTCOME ..............  o MESMO motor da 129-B calcula Condomínio (16), Residencial (2) e Empresarial (18) no Agger da corretora:
                        um pedido por ramo (o risco, os valores segurados, a atividade), as opções por ramo ("padrão" e "mais em
                        conta"), o corpo do calcularV2 de RE (coberturas em `cotacao.configuracoes`, a comissão do item), o leitor
                        das respostas de RE e a comparação pronta; a preferência de seguradoras por ramo por corretora e a regra de
                        renovação por ramo como CONFIGURAÇÃO; 1 cálculo real de conferência por ramo pela conta cotador@ da Resulta.
RISCO ................  7 — ALCANCE 2 · REVERSIBILIDADE 3 (cálculo real cria negócio no Agger da corretora) · FREQUÊNCIA 2
SUPERFÍCIE ...........  2 — o motor, o montador e o leitor da 129-B ganham o ramo
PISO APLICADO ........  §3.2 — robô em portal real (cálculo cria negócio) · dado de cliente real no canário (CNPJ/endereço)
NÍVEL ................  🔴 CRÍTICO · gerente Opus 5.5 · builders Opus 5.5 · juiz ‖ red team · conserto · confirmação
O FIO ................  PedidoDeCalculo(ramo, risco) → porta.calcular (faltando por ramo, opções por ramo, config) → motor
                        (o mesmo) → agger_robo (montagem de RE: sem placa/FIPE; endereço do risco; atividade por seguradora no
                        empresarial) → montador.js (RE: coberturas em configuracoes; comissão no item) → calcularV2 → leitor
                        (resultados[] de RE) → ofertas → comparacao (genérica por ramo) → ranking
                        · teste do fio: as 9 gravações reais como resposta do dublê do Agger, o pedido de cada ramo pela porta real
                        até as ofertas e o ranking; o corpo montado bate com a forma gravada
PARALELISMO REAL .....  F1 (portal_worker: contrato, presets, montador.js, agger_robo, leitor) ‖ F2 (app: pedido, porta, config,
                        comparacao) — contrato §3 → F3 costura + canário ao vivo (1 cálculo por ramo)
UNIDADES .............  U1 contrato por ramo · U2 presets/opções de RE · U3 montador RE · U4 robô RE (atividade empresarial) ·
                        U5 leitor RE · U6 pedido/porta por ramo · U7 config (preferências, renovação, comissão por ramo) ·
                        U8 comparação por ramo · U9 canário
COESÃO ...............  F1 = U1–U5 (o lado do portal) · F2 = U6–U8 (o lado do app) · F3 = U9 + o fio
TIME .................  gerente · B0-a ‖ B0-b ‖ B0-c (feitos) · F0 (Agger sempre ligado, feito) · F1 ‖ F2 · F3 · juiz ‖ red team ·
                        conserto · confirmação
REFERÊNCIA ...........  interna: a 129-B (motor, montador, robô, leitor), a 128 (a prova do Agger), a 130-A (comparação) ·
                        externa: o próprio app do Agger (bundle de 11/10, lido pelo B0-a) — §7.3
GATES ................  §5
O ELO ................  "o corpo que o robô monta para RE é o que o Agger aceita PORQUE a forma vem das gravações reais": o teste
                        compara o corpo montado com as 9 gravações; o canário prova no Agger de verdade
FAIXA DE RELÓGIO .....  💭 8–12 h
```

## 2. Decisões (pela maior nota; o Founder lê no fim)
| id | decisão | notas |
|---|---|---|
| D-129C-01 | o Agger da corretora fica SEMPRE ligado; horário/regras moram no auxiliar (F0, feito) | 92 |
| D-129C-02 | **a fonte das coberturas e das seguradoras de RE é o histórico do Agger**, não a InfoCap (📊 a InfoCap da Resulta tem 0 condomínio, 12 residencial, 3 empresarial em 32.901 documentos; o Agger tem 672/115/182 negócios) | 95 |
| D-129C-03 | **as opções de RE não têm valores segurados fixos**: os valores vêm do PEDIDO (a básica do risco); a opção varia as coberturas extras e a assistência — "padrão" (as coberturas típicas do ramo, 📊 AGREGADO) e "mais em conta" (só as essenciais + assistência básica) | 88 |
| D-129C-04 | **a atividade do empresarial é por seguradora**: o robô lê `getOptionsBySegFull` no momento do cálculo e escolhe o código de cada seguradora pela atividade do pedido (casamento de texto normalizado + uma tabela de sinônimos por classe — escritório, posto, oficina, clínica, beleza); seguradora sem atividade inequívoca sai do cálculo e é listada ("sem atividade compatível") | 85 × pedir humano sempre 50 |
| D-129C-05 | **a comissão de RE vai EXPLÍCITA no item** pela config por ramo (📊 o padrão do Agger no empresarial é 0 %); padrão do produto = o `comissao.entrada` da corretora, igual ao auto | 88 |
| D-129C-06 | **a regra de renovação por ramo é configuração** (`renovacao.reajuste_basica_pct` por ramo); padrão = 15 % (a palavra do Founder) — 📊 o Agger mostra +10 % como o mais comum no condomínio (16 de 41 pares; mediana +13,3 %): o Founder confirma o número | 80 |
| D-129C-07 | **preferência de seguradoras por ramo por corretora** em `multicalculo_config` (lista ordenada; vazia = todas as do ramo na conta); a comparação marca a preferida, nunca esconde as outras | 90 |
| D-129C-08 | **a página/proposta dos outros ramos fica para uma SPEC própria** (130-C) — a página de hoje é de carro; aqui entregam-se as ofertas comparadas e o ranking | 82 |
| D-129C-09 | **o canário usa 1 risco real por ramo** (dado de cliente da própria Resulta, autorizado pelo Founder em 10/10) pela conta cotador@ da Resulta; o negócio fica no Agger dela; nunca nada vai ao cliente | 85 |

## 3. O contrato F1 ↔ F2 — o pedido de RE
`PedidoDeCalculo` ganha `ramo` (31 auto · 16 condomínio · 2 residencial · 18 empresarial) e, para RE, um bloco `risco`:
```
risco = { cep, logradouro, numero, complemento?, bairro, cidade, uf,          # o endereço do risco (vai em configuracoes)
          tipo_imovel, construcao, uso?,                                      # códigos MEDIDOS (fixtures formulario_*)
          valor_basica,                                                       # a cobertura básica (incêndio) — do pedido
          extras: {codigo_cobertura: valor}?,                                 # opcional; senão as da opção
          # condomínio: tipo (vertical/horizontal/comercial), unidades?, elevador?, sisProtecaoIncendRoubo (códigos)
          # residencial: casa/apartamento, habitual/veraneio, imovelPossui* (booleanos)
          # empresarial: atividade (texto + cnae 7 dígitos), pavimento/localizacao (códigos texto), imovelPossui*
        }
segurado = { documento (CPF/CNPJ), nome, ... }  # condomínio: o segurado é PJ com endereço próprio
```
F1 é dono de `backend/portal_worker/multicalculo/contrato.py`; F2 constrói/valida o pedido em `backend/app/services/multicalculo/
{pedido,porta}.py` contra este contrato. Os códigos vêm SÓ das fixtures medidas (§9.5: cada constante diz por que está certa).

## 4. Fora (com dono)
a página/proposta de RE (130-C) · os demais ramos (vida, transporte…) · a InfoCap como fonte de RE (a carteira patrimonial está fora
dela — pergunta ao Founder: onde a Resulta lança essas apólices?) · os manuais da Resulta (atualizam presets e a regra de renovação).

## 5. Gates
G1 o teste do fio por ramo (as 9 gravações) · G2 o corpo montado de RE bate com a forma gravada (chaves de `configuracoes` e dos itens)
· G3 o auto continua byte a byte (o corpo da 129-B igual; os testes da 129-B/130-A verdes) · G4 a atividade do empresarial: casa ou sai
listada, nunca um código errado · G5 a comissão explícita no item · G6 a config por ramo com G8 (números só na config) · G7 o canário: 1
cálculo real por ramo, ofertas lidas, nenhuma exceção, logout · G8 nenhum dado pessoal em fixture/log · G9 bateria sem regressão.

## 7.3 O que o estado da arte faz
O próprio Agger (o app web, bundle lido em 11/10) é a referência do corpo; o histórico dos 45 negócios lidos é a referência das
coberturas e das seguradoras; os multicálculos de RE do mercado (💭 Segfy, Agger) seguem o mesmo padrão: risco + valores do segurado +
coberturas por seguradora.
