modelo: claude-opus-5-5

# SPEC-129-D — Vida Individual no multicálculo (o mesmo motor, um pedido e um preset para o ramo 91)

> **v1.0 · 16/10/2026** · redator Opus 5.5 (gerente) · branch `spec/129-D-vida` (da `origin/main` depois do push da 131-0-B3) · AAA v13 ·
> **CRÍTICO** por piso (robô em portal real: cálculo cria negócio no Agger da corretora). Fonte: as palavras do Founder de 15/10 · D-131-28 ·
> D-131-38 · D-129C-08/09 · o molde da [129-C](SPEC-129-C-mais-ramos-do-agger.md). BLOCO 0 em `docs/canon/programa-multicalculo/129-D/`.
> 📊 medido · 💭 ilustrativo.

## 0. EXECUTION CARD
```
OUTCOME ........ o MESMO motor da 129-B/129-C calcula Vida Individual (ramo 91) no Agger da corretora: um pedido de vida, as opções
                 "padrão" e "mais em conta", o corpo do calcularV2 de vida, o leitor do resultado e a comparação pronta. Na RENOVAÇÃO,
                 repete o capital e as coberturas da apólice atual (do PDF — nunca inventa); o que nenhuma fonte tem (fumante, renda,
                 esporte radical) vira "falta dado" para o comercial, nunca um palpite. Na COTAÇÃO NOVA, o corretor informa os
                 obrigatórios. TUDO atrás de MULTICALCULO_VIDA_LIGADO (ausente = vida continua "renove manualmente", como hoje).
RISCO .......... 7 · corretora 2 · cálculo real cria negócio no Agger 3 · toda noite de renovação 2
SUPERFÍCIE ..... 2 · o motor, o montador e o leitor ganham o ramo
PISO ........... CRÍTICO: robô em portal real · dado de vida (saúde/renda) é sensível (LGPD art. 11)
NÍVEL .......... CRÍTICO · builders Opus 5.5 xhigh · juiz ‖ red team Opus 5.5 · confirmação se blocker
O FIO .......... §2 · o teste do fio = a gravação real do BLOCO 0 como resposta do dublê do Agger, o pedido de vida pela porta real até
                 as ofertas e o ranking; o corpo montado bate com a forma gravada (1ª entrega da V3, VERMELHO)
PARALELISMO .... V1 (portal_worker) ‖ V2 (app) — contrato §3 → V3 costura + canário
GATES .......... fio · corpo = gravação · auto e RE byte a byte · chave desligada = nada muda · 2 corretoras · bateria · canário ao vivo
O ELO .......... "o corpo de vida que o robô monta é o que o Agger aceita PORQUE vem da gravação real" → teste do fio + canário
FAIXA .......... 💭 6–9 h
```

## 1. O contrato
**Muda:** o ramo 91 no contrato do portal_worker, no preset, no montador, no robô, no leitor, no pedido, na porta, na madrugada da
renovação (com a chave ligada), na config por ramo (preferência de seguradoras, comissão e agenciamento de vida) e na comparação.
**Não pode mudar:** o auto (31) e o RE (16/2/18) byte a byte · nenhuma EMISSÃO (só cotação) · nada vai ao cliente · a página/proposta de
vida (130-C, D-129C-08) · com a chave AUSENTE, a vida segue `ramo_nao_cotado` exatamente como hoje.

## 2. O FIO
```
renovação: InfoCap /renovacoes (VIND) → madrugada (chave ligada) → ficha única 130-B lê o PDF da apólice (capital, coberturas)
           + /cliente (sexo, nascimento, estado civil, CEP, profissão) → PedidoDeCalculo(ramo=91, vida={...}) → porta.calcular
           (faltando por ramo) → motor (o mesmo) → agger_robo (formulário de vida; profissão pela busca do Agger) → montador.js (corpo de
           vida) → calcularV2 → leitor (resultados de vida) → ofertas → comparação → ranking → item da renovação
cotação nova: chat/Cotação Rápida → pedido de vida com os 12 obrigatórios → a mesma porta → … → ofertas
```

## 2.1 BLOCO 0 (📊 16/10/2026 — investigador read-only, sem cálculo; laudo `129-D/BLOCO0-129D-LEITURA.md`)
| # | premissa | medição | o que muda no desenho |
|---|---|---|---|
| M1 | volume de vida | Resulta (login `resulta@`): VIND 11 (últ. 90 d) / 11 (próx. 90) · VGRP 11/12 · API 9/4 · AutoFleet: vida 0 | vida individual primeiro (D-129D-01) |
| M1b | moto tem volume? | AutoFleet AUTO próx. 90 d: `/itens` de 679/684 → categoria "Moto" 3 (regex do produto: 4 = 0,6 %); Resulta 0 | moto FORA (D-129D-02) |
| M1c | MOBI é moto? | AutoFleet MOBI 13/15, SURA 28/28, nome "MOBILIDADE", `/itens` vazio · Resulta "MOB" = IMOBILIÁRIA | MOBI fora; o Agger não tem a entrada (D-129D-03) |
| M2 | a apólice atual traz o capital? | 22 VIND da Resulta: `/itens` só em 8 (15 garantias, 14 com capital); PDF da apólice em 19/22; `/cliente`: sexo 19 · nascimento 15 · estado civil 11 · endereço 21 · profissão 7; NINGUÉM traz fumante, renda, esporte, beneficiários | capital/coberturas do PDF; o resto falta dado (D-129D-04/05) |
| M3 | o formulário de vida do Agger | 47 campos, 12 obrigatórios (cpf · nome · dataNasc · sexo · estadoCivil · cep · isFumante · rendaMensal · profissao (busca) · praticaEsporteRadical · vigenciaIni · assistMorte); a fixture registrou só 23; config por seguradora tem `percAgenciamentoVida` | os 24 campos restantes e o corpo vêm da gravação ao vivo (M6) |
| M4 | onde o 91 entra | `contrato.py:22-32,266-415,432-463,492-514` · `presets.py:151-272` · `montador.js:79,89,187,206` (todo ramo ≠ 31 cai no RE) · `agger_robo.py:61,296-303,857-858` · `leitor_agger.py:126-174,329-413,498-541` · `pedido.py:34,567-575,770-842,1030-1047` · `porta.py:68,406-417,513-559` · `madrugada.py:338-346,425-430,482-492` · `policy_data_provider.py:1283-1295` (VGRP na família de VIND!) · `config.py` · `comparacao.py` · `multicalculo_pedidos.ramo` sem CHECK (sem migration) | as fatias §5 |
| M5 | ficha única lê vida? | o leitor não depende do ramo, mas `madrugada.py:482-492` corta pela sigla ANTES — nunca rodou em PDF de vida | V2 deixa passar com a chave; o canário lê 1 PDF real |
| M6 | **AO VIVO** (1 cotação de vida, conta `cotador@` da Resulta, dados de TESTE, nunca emissão) | seguradoras de vida habilitadas · o corpo do `calcularV2` de vida · os 24 campos · códigos de sexo/estado civil/fumante/profissão · rótulos e recusas do resultado | as constantes de V1 (§9.5: cada uma diz por que está certa) |

## 3. O contrato V1 ↔ V2 — o pedido de vida
```
PedidoDeCalculo(ramo=91, segurado={cpf, nome, data_nascimento, sexo, estado_civil, cep, profissao_texto, profissao_codigo_infocap?},
                vida={capital_morte, coberturas_extras: {codigo: capital}?, fumante: bool|None, renda_mensal: Decimal|None,
                      esporte_radical: bool|None, vigencia_inicio, origem: 'renovacao'|'cotacao'})
```
`None` em fumante/renda/esporte = FALTA DADO (a porta devolve `faltando`), nunca um padrão. Os códigos vêm SÓ da gravação (M6).

## 4. Regras de vida (D-129D-xx; as que o Founder confirma depois estão marcadas 🧑)
- **Renovação:** capital de morte e coberturas = os da apólice atual, lidos do PDF pela ficha única; sem PDF ou sem capital legível →
  `pendente(falta_dado)` com "renove manualmente — não achei o capital da apólice atual". 🧑 reajuste do capital na renovação: padrão 0 %
  (repete), configurável por corretora.
- **Fumante, renda, esporte radical:** nenhuma fonte tem → `falta_dado` com as três perguntas ao comercial; NUNCA presumir "não fumante"
  (declaração falsa pode anular o seguro de vida). 🧑 se a corretora quiser uma regra (ex.: repetir o que a seguradora tinha), é config.
- **Profissão:** o texto da InfoCap casado com a busca do Agger (normalizado); sem casamento inequívoco → `falta_dado`.
- **"Padrão" × "mais em conta":** padrão = o capital e as coberturas da apólice (ou do pedido); mais em conta = só morte (+ a assistência
  funeral básica, se a gravação mostrar que é obrigatória) com o MESMO capital — nunca capital menor sem o corretor pedir.
- **Comissão e agenciamento:** explícitos no item pela config por ramo; padrão = o que o Agger da corretora já tem por seguradora (lido),
  nunca um número inventado.

## 5. Fatias (cada arquivo, UM dono)
| fatia | entrega | arquivos |
|---|---|---|
| **V1 · o portal** | contrato 91 + preset + montador + robô + leitor | `backend/portal_worker/multicalculo/{contrato,presets}.py` · `…/montador.js` · `…/agger_robo.py` · `…/leitor_agger.py` · fixtures `backend/tests/fixtures/agger_ramos/vida_*` (saneadas) · `backend/tests/test_spec129d_portal_vida.py` |
| **V2 · o app** | pedido, porta, madrugada (chave), config, comparação, família VGRP≠VIND | `backend/app/services/multicalculo/{pedido,porta,madrugada,config,comparacao,perfil_da_renovacao}.py` · `backend/app/providers/policy_data_provider.py` (só a família) · `backend/tests/test_spec129d_app_vida.py` |
| **V3 · costura + canário** | o fio + 1 cálculo real pelo robô | `backend/tests/test_spec129d_o_fio.py` · `backend/scripts/multicalculo_canario.py` (só o ramo 91) |

## 6. A régua
**Mutações:** (1) fumante `None` vira `False` → a porta TEM de recusar · (2) capital inventado quando o PDF não traz · (3) o auto/RE muda um
byte (os testes da 129-B/129-C) · (4) chave ausente e a vida passa · (5) VGRP tratada como VIND · (6) seguradora fora da preferência
escondida (a comparação marca, nunca esconde).
**Isolamento:** duas corretoras (a preferência e a comissão de A não vazam para B). **Canário:** 1 cálculo real de vida pela conta da
Resulta (dados de TESTE; ofertas lidas; logout); nada ao cliente. **Verba** de API do produto ≤ US$ 0,30 (o Agger não cobra por cálculo).

## 7. Decisões desta SPEC
| # | decisão | nota | contra |
|---|---|---|---|
| D-129D-01 | Vida INDIVIDUAL primeiro (📊 Resulta 11+11 VIND); vida em grupo depois (Vida Global ≠ apólice coletiva — medir) | 90 | VIND+VGRP juntas 50 |
| D-129D-02 | Moto FORA: 📊 4 de 684 AUTO (0,6 %) na AutoFleet, 0 na Resulta; segue "renove manualmente" (D-131-38) | 88 | fazer agora 35 |
| D-129D-03 | MOBI fora: é a Mobilidade da SURA (📊 28/28), nenhuma das 13 entradas do Agger cota | 92 | AP no lugar 30 (não é o mesmo produto) |
| D-129D-04 | Renovação repete capital e coberturas do PDF da apólice (ficha única 130-B); sem leitura → falta dado | 88 | pedir sempre ao corretor 55 · capital padrão 5 (§13.6) |
| D-129D-05 | Fumante/renda/esporte sem fonte → falta dado, NUNCA presumir | 90 | presumir "não" 20 |
| D-129D-06 | Profissão pela busca do Agger com casamento inequívoco; senão falta dado | 80 | código fixo 40 |
| D-129D-07 | VGRP separada de VIND na família (`policy_data_provider`) antes de ligar o 91 | 90 | deixar junto 10 |
| D-129D-08 | Comissão e agenciamento de vida explícitos, padrão = o do Agger da corretora | 82 | 0 % do Agger 40 |
| D-129D-09 | Chave `MULTICALCULO_VIDA_LIGADO` (ausente = nada muda); ligar é do Founder | 92 | ligar já 20 |
| D-129D-10 | Proposta/página de vida na 130-C | 82 | aqui 40 (escopo) |
| D-129D-11 | O BLOCO 0 grava 1 cotação real pela UI; o canário faz 1 pelo robô — 2 cotações de teste no total, nunca emissão | 85 | só a do BLOCO 0 60 (o robô ficaria sem prova ao vivo) |

## 8. O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS
1. **https://www.gov.br/susep/pt-br/assuntos/meu-futuro-seguro/seguros/seguro-de-vida** · faz: explica capital segurado, coberturas e
   declaração de saúde do seguro de vida · modelamos: o capital é escolha do segurado, a declaração é dele · rejeitamos: presumir
   fumante/renda · juiz: mutação 1.
2. **https://www.planalto.gov.br/ccivil_03/leis/2002/l10406compilada.htm** (Código Civil, art. 766) · faz: declaração inexata pode fazer
   perder a garantia · modelamos: "falta dado" em vez de palpite · rejeitamos: preencher por padrão · juiz: D-129D-05 no código.
3. **https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm** (LGPD, art. 11) · faz: dado de saúde é sensível ·
   modelamos: fumante/renda nunca em log, fixture ou mensagem · rejeitamos: gravar a declaração fora do pedido · juiz: grep de log/fixture.
4. **https://aggilizador.com.br** (o app do Agger, a gravação do BLOCO 0) · faz: o formulário e o `calcularV2` de vida · modelamos: o corpo
   exato da gravação · rejeitamos: inferir campos · juiz: teste "corpo = gravação".

## 9. O QUE SAI (com destino)
Página/proposta de vida → 130-C · vida em grupo (VGRP) e AP → SPEC própria depois de medir Vida Global/Acidentes Pessoais · moto → quando
o volume pedir · MOBI → portal da SURA, se um dia valer · ligar a chave → Founder (tarefa).
