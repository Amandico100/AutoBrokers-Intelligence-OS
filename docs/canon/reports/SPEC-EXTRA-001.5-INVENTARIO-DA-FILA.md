# SPEC-EXTRA-001.5 · Inventário da fila de curadoria — tudo o que foi extraído, nada publicado

> 📊 **Medido em 18/09/2026**, por `SELECT` direto na base de produção (`insurer_assistance_plans` + `insurer_assistance_services`, juntadas a `normative_documents`). Nenhuma escrita foi feita.
>
> ✅ **Conferido em 18/09/2026 por segunda leitura:** nenhum número precisou ser corrigido. Foram reconferidas, uma a uma, as **81 linhas** (par seguradora × ramo, serviço, página, estado e nome do documento — **nenhuma divergência, nenhuma faltando, nenhuma a mais**), os totais (81 · 38 planos · 17 pares · 27 documentos · 33/73 `proposto` · 5/8 `rascunho` · 0 publicado), os 26 pares com zero linha, os 43 pares com documento, as 8 linhas e os 5 planos em `rascunho`, as 4 linhas presas sob plano reprovado, o teto de 60 da fila, os 19 itens da onda 3 e as três citações de arquivo do front. **Foram acrescentadas duas notas de rodapé** que faltavam para o número não ser lido errado: a marcada ⚑ na §1 de "O que NÃO temos" (o que a coluna *documentos no acervo* conta) e a marcada ⚑ logo abaixo (um dos 27 documentos não é condição geral). 📊 Varredura de dado pessoal sobre o arquivo inteiro (CPF, CNPJ, telefone, placa, e-mail, CEP, número de apólice): **zero ocorrências** — as únicas sequências longas de dígitos são números de processo SUSEP em nomes de arquivo, que são identificação pública de produto.

**O que é esta lista.** Cada linha abaixo é uma afirmação que o extrator leu num PDF de condições gerais e escreveu na base — *"a Bradesco Residencial Sob Medida tem chaveiro, página 41"*. **Nenhuma delas está publicada**: enquanto ninguém confirmar, o assistente responde "ainda não sei" ao segurado e nunca inventa um "não".

📊 **81 linhas de serviço**, em **38 planos**, de **17 pares seguradora × ramo**, tiradas de **27 documentos** distintos do acervo.

> ⚑ **Um dos 27 não é uma condição geral** (nota acrescentada na segunda leitura, 18/09/2026): 📊 26 são `condicoes_gerais` e **1 é `manual_do_segurado`** — o *Manual do Segurado — Bradesco Seguro Auto*, de onde saíram **5 das 6 linhas de Bradesco · Automóvel** (chaveiro, guincho, pane seca, táxi e troca de pneu, todas na página 43). Isso não invalida nada: o manual é publicado pela própria seguradora e a página está lá para conferir. Mas quem for aprovar essas cinco precisa saber que está conferindo um manual, não o contrato registrado na SUSEP — e que o contrato pode dizer outra coisa.

| estado | planos | linhas de serviço | o que significa |
|---|---|---|---|
| `proposto` | 33 | 73 | passou no verificador (o trecho estava mesmo na página) e **espera uma pessoa** |
| `rascunho` | 5 | 8 | o verificador **reprovou**; não entra na fila e não é publicável pela tela |
| `publicado` | 0 | 0 | — |

⚠️ **A fila da tela mostra no máximo 60 linhas por vez** (`TETO_DA_FILA`, `backend/app/api/assistance_plans.py`). Como há 73 em `proposto`, **13 não aparecem** — e como a consulta não tem `ORDER BY`, *quais* 13 ficam de fora muda de chamada para chamada. Esta lista aqui não tem teto: estão as 81.

---

## Como ler a tabela

* **coberto** — `SIM` = está incluído · `NÃO` = está explicitamente fora · `com condição` = incluído, mas com restrição escrita ao lado.
* **página** — a página do PDF onde a frase foi lida. É por ela que o assistente vai poder citar a fonte ao segurado.
* **estado** — `proposto` espera seu clique; `rascunho` foi reprovado pelo verificador e **precisa de reextração**, não de aprovação.
* **—** significa que o campo está vazio na base. Nada foi preenchido por suposição.

---

## Bradesco · Residencial — 17 linhas (15 proposto, 2 rascunho) · 10 planos

**De onde veio:**
* *Bradesco Residencial Sob Medida — Condições Gerais (mai/2024)* (ramo do documento: Residencial)
* *Bradesco Seguros residencial — Bilhete Residencial - CC.pdf* (ramo do documento: Residencial) — arquivo: `Bilhete Residencial - CC.pdf`
* *Bradesco Seguros residencial — Bilhete Residencial Pop - CC.pdf* (ramo do documento: Residencial) — arquivo: `Bilhete Residencial Pop - CC.pdf`
* *Bradesco Seguros residencial — CC - Residencial Sob Medida.pdf* (ramo do documento: Residencial) — arquivo: `CC - Residencial Sob Medida.pdf`
* *Bradesco Seguros residencial — CC-RESIDENCIAL POP.pdf* (ramo do documento: Residencial) — arquivo: `CC-RESIDENCIAL POP.pdf`
* *Bradesco Seguros residencial — CC-Residencial Antigo.pdf* (ramo do documento: Residencial) — arquivo: `CC-Residencial Antigo.pdf`
* *Bradesco e-Residencial — Condições Gerais (mar/2025)* (ramo do documento: Residencial) — arquivo: `CC - e-Residencial.pdf`

| plano (nível) | serviço | coberto | limite | carência | condição | documento | pág. | estado |
|---|---|---|---|---|---|---|---|---|
| Bradesco Seguros Residencial Sob Medida — Cobertura Acessória - Moradia Temporária (nível 1) | hospedagem | com condição | até o Limite Máximo de Garantia Contratado | — | Aplica-se caso o imóvel não possa permanecer ocupado em decorrência de sinistro coberto pelas Coberturas contratadas; despesas de refeição limitadas a 30% do LMG | Bradesco Seguros residencial — CC - Residencial Sob Medida.pdf | 27 | `proposto` |
| Bradesco Seguros Residencial — CC Residencial Sob Medida — Plano único (nível 1) | alagamento | SIM | Limite Máximo de Garantia Contratado | — | Cobertura de danos materiais causados por alagamento, inundação e enchente ou ruptura de encanamento externo ao imóvel | Bradesco Seguros residencial — CC - Residencial Sob Medida.pdf | 33 | `proposto` |
| Bradesco Bilhete Residencial Pop — Plano único (nível 1) | alagamento | NÃO | — | — | [reprovado] 'nao' de alagamento veio de cláusula de exclusão de risco de outra cobertura — precisa ser reextraído como condicionado | Bradesco Seguros residencial — Bilhete Residencial Pop - CC… | 32 | `rascunho` |
| Bradesco Residencial Sob Medida — Plano único (nível 1) | alagamento | com condição | — | — | [reprovado] trecho_nao_esta_na_pagina | Bradesco Residencial Sob Medida — Condições Gerais (mai/2024) | 114 | `rascunho` |
| Bradesco E Residencial — Plano único (nível 1) | alagamento | SIM | até o Limite Máximo de Garantia Contratado | — | Danos causados por entrada de água, enchentes, ruptura de encanamento de terceiros ou inundação de rios navegáveis | Bradesco e-Residencial — Condições Gerais (mar/2025) | 41 | `proposto` |
| Bradesco Residencial Sob Medida — Plano único (nível 1) | encanador | com condição | Mão de obra do prestador até, no máximo, R$250,00 (duzentos e cinquenta reais) por evento | — | 1 acionamento por evento; serviço prestado exclusivamente em tubulação aparente; não cobre canos de ferro e/ou cobre | Bradesco Residencial Sob Medida — Condições Gerais (mai/2024) | 114 | `proposto` |
| Bradesco Seguros Residencial — Plano único (nível 1) | granizo | com condição | até o Limite Máximo de Garantia Contratado | — | Cobertura de vidros aplicável em caso de chuva de granizo, desde que deixe vestígios materiais inequívocos e se trate de evento público e notório na localidade do sinistro. | Bradesco Seguros residencial — CC-RESIDENCIAL POP.pdf | 46 | `proposto` |
| Bradesco E Residencial — Plano único (nível 1) | granizo | com condição | até o Limite Máximo de Garantia Contratado | — | Danos materiais causados diretamente aos bens segurados exclusivamente em consequência de vendaval, furacão, tornado, ciclone, granizo, neve e geada | Bradesco e-Residencial — Condições Gerais (mar/2025) | 31 | `proposto` |
| Bradesco Compreensivo Residencial — Plano único (nível 1) | granizo | com condição | até o Limite Máximo de Garantia Contratado | — | Cobertura de vidros, espelhos ou mármores danificados por chuva de granizo, desde que deixe vestígios materiais inequívocos e se trate de evento público e notório na localidade do sinistro | Bradesco Seguros residencial — CC-Residencial Antigo.pdf | 32 | `proposto` |
| Bradesco Bilhete Residencial — Plano único (nível 1) | granizo | SIM | até o Limite Máximo de Garantia contratado | — | danos materiais causados diretamente aos bens segurados exclusivamente em consequência de vendaval, furacão, ciclone, tornado, granizo, neve e geada | Bradesco Seguros residencial — Bilhete Residencial - CC.pdf | 14 | `proposto` |
| Bradesco Bilhete Residencial Pop CC — Plano único (nível 1) | granizo | com condição | até o Limite Máximo de Garantia Contratado | — | Garante danos materiais causados diretamente aos bens segurados exclusivamente em consequência de vendaval, furacão, tornado, ciclone e granizo; exclui entrada de água por janelas/portas/aberturas e inundação/alagamento por transbordamento de rios ou enchentes | Bradesco Seguros residencial — Bilhete Residencial Pop - CC… | 28 | `proposto` |
| Bradesco Seguros Residencial POP — Plano único (nível 1) | granizo | SIM | até o Limite Máximo de Garantia Contratado | — | danos materiais causados diretamente aos bens segurados exclusivamente em consequência de vendaval, furacão, tornado, ciclone e granizo | Bradesco Seguros residencial — CC-RESIDENCIAL POP.pdf | 42 | `proposto` |
| Bradesco Bilhete Residencial Pop — Plano único (nível 1) | granizo | SIM | até o Limite Máximo de Garantia Contratado | — | Cobre danos aos vidros, espelhos ou mármores causados por chuva de granizo, desde que deixe vestígios materiais inequívocos e se trate de evento público e notório na localidade do sinistro. | Bradesco Seguros residencial — Bilhete Residencial Pop - CC… | 32 | `proposto` |
| Bradesco E Residencial — Plano único (nível 1) | hospedagem | com condição | até o limite do período indenitário contratado | — | Pago mensalmente mediante apresentação de comprovantes de despesas | Bradesco e-Residencial — Condições Gerais (mar/2025) | 31 | `proposto` |
| Bradesco Bilhete Residencial Pop — Plano único (nível 1) | vidros | com condição | até o Limite Máximo de Garantia Contratado | — | Cobre danos materiais causados aos vidros, espelhos ou mármores instalados no imóvel, provocados por ação de calor artificial, ato involuntário, choque térmico, chuva de granizo, imprudência ou culpa de terceiros e quebra espontânea; exclui arranhaduras, lascas, danos durante obras, desaparecimento/furto/roubo, desmoronamento, incêndio/raio/explosão, danos a terceiros, terremoto/maremoto/inundação e alagamento. | Bradesco Seguros residencial — Bilhete Residencial Pop - CC… | 32 | `proposto` |
| Bradesco Compreensivo Residencial — Plano único (nível 1) | vidros | com condição | até o Limite Máximo de Garantia Contratado | — | Danos materiais causados aos vidros, espelhos ou mármores, exclusivamente instalados no imóvel segurado, provocados por ação de calor artificial, ato involuntário de terceiros, choque térmico, chuva de granizo, imprudência ou culpa de terceiros e quebra espontânea | Bradesco Seguros residencial — CC-Residencial Antigo.pdf | 32 | `proposto` |
| Bradesco Seguros Residencial — Plano único (nível 1) | vidros | com condição | até o Limite Máximo de Garantia Contratado | — | Cobre danos materiais causados aos vidros, espelhos ou mármores, exclusivamente instalados no imóvel segurado, provocados por ação de calor artificial, ato involuntário dos empregados do segurado, choque térmico, chuva de granizo, imprudência ou culpa de terceiros e quebra espontânea. Não cobre arranhaduras e lascas, e danos durante obras ou reparos. | Bradesco Seguros residencial — CC-RESIDENCIAL POP.pdf | 46 | `proposto` |

## HDI · Automóvel — 9 linhas (9 proposto, 0 rascunho) · 3 planos

**De onde veio:**
* *HDI Seguros auto — CG HDI - PRODUTOS AUTO - 30.04.26.pdf* (ramo do documento: Automóvel) — arquivo: `CG HDI - PRODUTOS AUTO - 30.04.26.pdf`

| plano (nível) | serviço | coberto | limite | carência | condição | documento | pág. | estado |
|---|---|---|---|---|---|---|---|---|
| Ituran Com Seguro — Essencial (nível 1) | guincho | SIM | Sinistro e Pane: 300km, ou até R$ 120,00 por evento e R$ 360,00 por vigência | — | Sinistro e Pane | HDI Seguros auto — CG HDI - PRODUTOS AUTO - 30.04.26.pdf | 93 | `proposto` |
| Auto Básico — Essencial (nível 1) | hospedagem | SIM | Até R$ 100,00 por evento e R$ 200,00 por Vigência | — | — | HDI Seguros auto — CG HDI - PRODUTOS AUTO - 30.04.26.pdf | 93 | `proposto` |
| Auto Básico — Essencial (nível 1) | pane seca | SIM | Até R$ 100,00 por evento e R$ 200,00 por Vigência | — | — | HDI Seguros auto — CG HDI - PRODUTOS AUTO - 30.04.26.pdf | 93 | `proposto` |
| Auto Básico — Essencial (nível 1) | troca de pneu | SIM | 100km, ou Até R$ 65,00 por evento e R$ 130,00 por Vigência | — | — | HDI Seguros auto — CG HDI - PRODUTOS AUTO - 30.04.26.pdf | 93 | `proposto` |
| HDI Seguros Auto — Plano único (nível 1) | chaveiro | com condição | confecção de 1 (uma) chave simples (chave não codificada) | — | Abertura do veículo sem arrombamento e confecção de 1 chave simples quando tecnicamente possível | HDI Seguros auto — CG HDI - PRODUTOS AUTO - 30.04.26.pdf | 80 | `proposto` |
| HDI Seguros Auto — Plano único (nível 1) | guincho | com condição | CONFORME DESCRITOS NA CLAUSULA 2 - PLANOS, PRODUTOS E LIMITES DA ASSISTÊNCIA 24 HORAS | — | Guincho para remoção até oficina referenciada mais próxima ou de livre escolha, mediante constatação de impossibilidade de locomoção própria | HDI Seguros auto — CG HDI - PRODUTOS AUTO - 30.04.26.pdf | 80 | `proposto` |
| HDI Seguros Auto — Plano único (nível 1) | hospedagem | com condição | CONFORME DESCRITOS NA CLAUSULA 2 - PLANOS, PRODUTOS E LIMITES DA ASSISTÊNCIA 24 HORAS | — | Veículo impossibilitado de circular por pane ou sinistro a 50km ou mais do domicílio, conserto demorando mais de 24h (passeio/moto) ou 6h (caminhões), ou oficina não encontrada em funcionamento, desde que tenha usado Socorro/Reboque e não tenha usado Retorno ao Domicílio ou Continuação de Viagem | HDI Seguros auto — CG HDI - PRODUTOS AUTO - 30.04.26.pdf | 83 | `proposto` |
| HDI Seguros Auto — Plano único (nível 1) | pane seca | com condição | CONFORME DESCRITOS NA CLAUSULA 2 - PLANOS, PRODUTOS E LIMITES DA ASSISTÊNCIA 24 HORAS | — | Envio de socorro mecânico ou elétrico para conserto no local, em nível paliativo, quando tecnicamente possível | HDI Seguros auto — CG HDI - PRODUTOS AUTO - 30.04.26.pdf | 80 | `proposto` |
| HDI Seguros Auto — Plano único (nível 1) | troca de pneu | com condição | — | — | Somente quando um único pneu for danificado e houver estepe e acessórios adequados; caso contrário, remoção até borracharia | HDI Seguros auto — CG HDI - PRODUTOS AUTO - 30.04.26.pdf | 81 | `proposto` |

## Tokio Marine · Automóvel — 7 linhas (5 proposto, 2 rascunho) · 3 planos

**De onde veio:**
* *Tokio Marine auto — 202604 15414100335200474 - CG.pdf* (ramo do documento: Automóvel) — arquivo: `202604 15414100335200474 - CG.pdf`

| plano (nível) | serviço | coberto | limite | carência | condição | documento | pág. | estado |
|---|---|---|---|---|---|---|---|---|
| Tokio Marine Auto — Auto/Auto Clássico/Auto Roubo/Auto Roubo+Rastreador/Moto/Utilitário Carga/Auto Proteção Mensal/Moto Proteção Mensal/Utilitário Carga Proteção Mensal/Auto Frota (passeio, pick ups, motos e táxis) (nível 1) | guincho | com condição | — | — | [reprovado] trecho_nao_esta_na_pagina | Tokio Marine auto — 202604 15414100335200474 - CG.pdf | 26 | `rascunho` |
| Tokio Marine Auto — Auto/Auto Clássico/Auto Roubo/Auto Roubo+Rastreador/Moto/Utilitário Carga/Auto Proteção Mensal/Moto Proteção Mensal/Utilitário Carga Proteção Mensal/Auto Frota (passeio, pick ups, motos e táxis) (nível 1) | pane seca | com condição | — | — | [reprovado] trecho_nao_esta_na_pagina | Tokio Marine auto — 202604 15414100335200474 - CG.pdf | 26 | `rascunho` |
| Tokio Marine Caminhão — Caminhão/Auto Frota (Caminhões, rebocadores, reboques, semirreboques, vans, furgões, ambulâncias e ônibus) (nível 1) | guincho | com condição | 1 (um) reboque por evento, de até 800 km | — | Na ocorrência de acidente, enchente, roubo/furto ou incêndio com impossibilidade de circular | Tokio Marine auto — 202604 15414100335200474 - CG.pdf | 26 | `proposto` |
| Tokio Marine Caminhão — Caminhão/Auto Frota (Caminhões, rebocadores, reboques, semirreboques, vans, furgões, ambulâncias e ônibus) (nível 1) | pane seca | com condição | 1 (um) reboque por evento, de até 400 km | — | Na ocorrência de pane, com impossibilidade de conserto do veículo no local | Tokio Marine auto — 202604 15414100335200474 - CG.pdf | 26 | `proposto` |
| Tokio Marine Auto — Plano único (nível 1) | carro reserva | com condição | 2 dias | — | Necessário ter ocorrido utilização do reboque da Assistência, ou confirmação da pane pela oficina via orçamento por fax ou e-mail; não válido para Moto, Moto Proteção Mensal, Caminhão e Auto Frota para Motocicletas, Caminhões, Rebocadores, Reboques, Semirreboques, Vans, Furgões, Ambulâncias e Ônibus; somente em Território Nacional | Tokio Marine auto — 202604 15414100335200474 - CG.pdf | 32 | `proposto` |
| Tokio Marine Auto — Plano único (nível 1) | hospedagem | com condição | R$100,00 (cem reais) por dia, até o limite de R$200,00 (duzentos reais) por passageiro e por toda estadia | — | Se o veículo segurado estiver impossibilitado de circular em decorrência de pane, acidente, incêndio, roubo ou furto, e não sendo possível providenciar um meio de transporte alternativo | Tokio Marine auto — 202604 15414100335200474 - CG.pdf | 28 | `proposto` |
| Tokio Marine Auto — Plano único (nível 1) | táxi | com condição | até o limite oficial de passageiros permitido para o veículo | — | Veículo impossibilitado de circular por pane, acidente, incêndio, enchente, roubo ou furto, mediante comprovação do evento | Tokio Marine auto — 202604 15414100335200474 - CG.pdf | 33 | `proposto` |

## Bradesco · Automóvel — 6 linhas (6 proposto, 0 rascunho) · 2 planos

**De onde veio:**
* *Bradesco Seguro Auto — Condições Contratuais (abr/2023)* (ramo do documento: Automóvel) — arquivo: `CC.pdf`
* *Manual do Segurado — Bradesco Seguro Auto* (ramo do documento: Automóvel)

| plano (nível) | serviço | coberto | limite | carência | condição | documento | pág. | estado |
|---|---|---|---|---|---|---|---|---|
| Bradesco Seguro Auto — Plano único (nível 1) | chaveiro | com condição | até o limite máximo de R$ 100,00 (cem reais) por evento e até três eventos durante a vigência da apólice | — | somente será prestado dentro de municípios ou aglomerações urbanas; não será fornecida a chave codificada | Manual do Segurado — Bradesco Seguro Auto | 43 | `proposto` |
| Bradesco Seguro Auto — Plano único (nível 1) | guincho | com condição | apenas um serviço de reboque, por pane mecânica ou elétrica e três eventos para vigência da apólice | — | por pane mecânica ou elétrica | Manual do Segurado — Bradesco Seguro Auto | 43 | `proposto` |
| Bradesco Seguro Auto — Plano único (nível 1) | pane seca | SIM | — | — | veículo impossibilitado de locomoção por falta de combustível | Manual do Segurado — Bradesco Seguro Auto | 43 | `proposto` |
| Bradesco Seguro Auto — Plano único (nível 1) | táxi | com condição | limitado ao aluguel de 1 (um) táxi | — | em caso de pane ou acidente, desde que o local escolhido esteja situado dentro do município em que ocorreu o evento | Manual do Segurado — Bradesco Seguro Auto | 43 | `proposto` |
| Bradesco Seguro Auto — Plano único (nível 1) | troca de pneu | com condição | — | — | somente será prestado caso o Segurado disponha de pneu reserva no momento da solicitação, limitado apenas à troca do pneu | Manual do Segurado — Bradesco Seguro Auto | 43 | `proposto` |
| Bradesco Seguro Auto — Super Luxo (nível 3) | vidros | SIM | 2 (dois) acionamentos durante a vigência | — | Para brisa dianteiro e traseiro, vidros laterais, faróis, lanternas e retrovisores | Bradesco Seguro Auto — Condições Contratuais (abr/2023) | 159 | `proposto` |

## HDI · Residencial — 6 linhas (5 proposto, 1 rascunho) · 2 planos

**De onde veio:**
* *HDI Seguros residencial — CG_HDI Imobiliário Residencial - 15414.605587_2024-39 - v_1.3 - Susep - vigente a partir de xx.07.2026.pdf* (ramo do documento: Residencial) — arquivo: `CG_HDI Imobiliário Residencial - 15414.605587_2024-39 - v_1.3 - Susep - vigente a partir de xx.07.2026.pdf`
* *HDI Seguros residencial — Condições Contratuais HDI Residencial - 15414.002160_2005-11 v_2.7 - vigente a partir de 09.07.2026.pdf* (ramo do documento: Residencial) — arquivo: `Condições Contratuais HDI Residencial - 15414.002160_2005-11 v_2.7 - vigente a partir de 09.07.2026.pdf`

| plano (nível) | serviço | coberto | limite | carência | condição | documento | pág. | estado |
|---|---|---|---|---|---|---|---|---|
| HDI Seguros Residencial — Plano único (nível 1) | alagamento | NÃO | — | — | [reprovado] 'nao' de alagamento veio de cláusula de exclusão de risco de outra cobertura — precisa ser reextraído como condicionado | HDI Seguros residencial — Condições Contratuais HDI Residen… | 88 | `rascunho` |
| HDI Imobiliário Residencial — Plano único (nível 1) | eletricista | com condição | — | — | Envio de eletricista para realizar reparos necessários para o restabelecimento da energia elétrica ou para solucionar problemas elétricos, conforme evento previsto: Raio, danos elétricos (sobrecarga de energia), tomadas queimadas, interruptores defeituosos, lâmpadas ou reatores queimados, disjuntores e fusíveis danificados, chaves faca, troca de chuveiros ou resistência de chuveiro/torneiras (elétricos e não blindados). Exclui quebra de parede, teto ou piso e troca ou instalação de fiação. | HDI Seguros residencial — CG_HDI Imobiliário Residencial - … | 51 | `proposto` |
| HDI Seguros Residencial — Plano único (nível 1) | granizo | com condição | — | — | exceto se os eventos cobertos tenham danificado estes itens | HDI Seguros residencial — Condições Contratuais HDI Residen… | 88 | `proposto` |
| HDI Seguros Residencial — Plano único (nível 1) | hospedagem | com condição | até o limite contratado | — | Em caso de evento previsto na residência assistida como, roubo ou furto qualificado, incêndio, raio, explosão, desmoronamento, vendaval, granizo, fumaça, alagamento, impacto de veículos e queda de aeronaves e se for verificada a impossibilidade de habitação da Residência Assistida | HDI Seguros residencial — Condições Contratuais HDI Residen… | 96 | `proposto` |
| HDI Imobiliário Residencial — Plano único (nível 1) | hospedagem | com condição | — | — | Reserva e pagamento de hospedagem do segurado e seus familiares, caso ocorra um evento previsto que impossibilite a habitação do imóvel, dentre os eventos: Roubo ou furto qualificado, incêndio, raio, explosão, danos elétricos, desmoronamento, vendaval, granizo, fumaça, alagamento, impacto de veículos e queda de aeronaves. | HDI Seguros residencial — CG_HDI Imobiliário Residencial - … | 51 | `proposto` |
| HDI Seguros Residencial — Plano único (nível 1) | vidros | com condição | — | — | desde que com a efetiva caracterização da relação da causa e os danos aos vidros | HDI Seguros residencial — Condições Contratuais HDI Residen… | 88 | `proposto` |

## Azul · Automóvel — 5 linhas (4 proposto, 1 rascunho) · 2 planos

**De onde veio:**
* *Azul Seguro Auto — Condições Gerais* (ramo do documento: Automóvel) — arquivo: `Manual Azul Auto SEGURADO Setembro 2025 Versão SUSEP.pdf`
* *Azul Seguros auto — Manual Azul Seguro Auto Por Assinatura - Agosto 2026 SUSEP.pdf* (ramo do documento: Automóvel) — arquivo: `Manual Azul Seguro Auto Por Assinatura - Agosto 2026 SUSEP.pdf`

| plano (nível) | serviço | coberto | limite | carência | condição | documento | pág. | estado |
|---|---|---|---|---|---|---|---|---|
| Azul Seguro Auto Por Assinatura — Plano único (nível 1) | guincho | NÃO | não reembolsado nesta cobertura de Despesas de Salvamento | — | uso do guincho deve se restringir às cláusulas de Assistência 24 horas | Azul Seguros auto — Manual Azul Seguro Auto Por Assinatura … | 24 | `proposto` |
| Azul Seguro Auto Por Assinatura — Plano único (nível 1) | vidros | com condição | limita-se aos valores totais mencionados na tabela Limite Máximo de Indenização | — | Cobertura de vidros, faróis, lanternas e retrovisores sujeita a exclusões e limite de indenização; serviço deve ser realizado pelos canais digitais ou central de atendimento indicados | Azul Seguros auto — Manual Azul Seguro Auto Por Assinatura … | 29 | `proposto` |
| Azul Seguro Auto — Rede Referenciada sem Limite de KM (nível 1) | guincho | SIM | sem limite de utilização em caso de sinistro; para assistência: sem limite de km, máximo 4 utilizações por vigência, 1 por evento | — | Para o serviço de guincho, em caso de sinistro não há limite de utilização; demais serviços automotivos limitados a 4 utilizações por vigência | Azul Seguro Auto — Condições Gerais | 61 | `proposto` |
| Azul Seguro Auto — Rede Referenciada sem Limite de KM (nível 1) | pane seca | SIM | — | — | [reprovado] trecho_nao_esta_na_pagina | Azul Seguro Auto — Condições Gerais | 61 | `rascunho` |
| Azul Seguro Auto — Rede Referenciada sem Limite de KM (nível 1) | troca de pneu | com condição | sem limite de km, máximo 4 utilizações por vigência, 1 por evento | — | Serviço prestado desde que o Segurado disponha de pneu reserva em condições de uso; limitado à troca do pneu, excluindo reparo ou substituição | Azul Seguro Auto — Condições Gerais | 61 | `proposto` |

## Porto · Residencial — 4 linhas (4 proposto, 0 rascunho) · 1 plano

**De onde veio:**
* *Porto Seguro Residência Habitual, Premium e Veraneio — Condições Gerais* (ramo do documento: Residencial) — arquivo: `CG Res Habitual, Premium e Veraneio (PROTOCOLO)_dez_25.pdf`

| plano (nível) | serviço | coberto | limite | carência | condição | documento | pág. | estado |
|---|---|---|---|---|---|---|---|---|
| Porto Seguro Residência Habitual, Premium E Veraneio — Plano único (nível 1) | alagamento | SIM | até o Limite Máximo de Indenização contratado | — | prejuízos causados ao imóvel e/ou conteúdo decorrentes de alagamento, inundação e enchente resultantes de acúmulo de água nas ruas, por problemas de drenagem ou transbordamento de lagos e rios em decorrência de fortes chuvas, e danos elétricos causados por esses eventos | Porto Seguro Residência Habitual, Premium e Veraneio — Cond… | 39 | `proposto` |
| Porto Seguro Residência Habitual, Premium E Veraneio — Plano único (nível 1) | chaveiro residencial | com condição | 150 reais | — | Valor deduzido do Limite Máximo de Indenização do plano contratado, sujeito a disponibilidade e limite do plano. | Porto Seguro Residência Habitual, Premium e Veraneio — Cond… | 74 | `proposto` |
| Porto Seguro Residência Habitual, Premium E Veraneio — Plano único (nível 1) | eletricista | com condição | 150 reais | — | Valor deduzido do Limite Máximo de Indenização do plano contratado, sujeito a disponibilidade e limite do plano. | Porto Seguro Residência Habitual, Premium e Veraneio — Cond… | 74 | `proposto` |
| Porto Seguro Residência Habitual, Premium E Veraneio — Plano único (nível 1) | encanador | com condição | 150 reais | — | Valor deduzido do Limite Máximo de Indenização do plano contratado, sujeito a disponibilidade e limite do plano. | Porto Seguro Residência Habitual, Premium e Veraneio — Cond… | 74 | `proposto` |

## Yelum · Automóvel — 4 linhas (4 proposto, 0 rascunho) · 2 planos

**De onde veio:**
* *Yelum Seguradora auto — CG YELUM PRODUTOS AUTO - Marcada 30.04.26.pdf* (ramo do documento: Automóvel) — arquivo: `CG YELUM PRODUTOS AUTO - Marcada 30.04.26.pdf`

| plano (nível) | serviço | coberto | limite | carência | condição | documento | pág. | estado |
|---|---|---|---|---|---|---|---|---|
| Yelum Seguros Auto — LOCADORAS INTERMEDIÁRIO (nível 1) | chaveiro | SIM | — | — | Em caso de quebra ou perda das chaves do veículo, ou esquecimento das mesmas em seu interior | Yelum Seguradora auto — CG YELUM PRODUTOS AUTO - Marcada 30… | 142 | `proposto` |
| Yelum Seguros Auto — LOCADORAS INTERMEDIÁRIO (nível 1) | guincho | SIM | CONFORME DESCRITOS NA TABELA DE LIMITES DE ASSISTÊNCIA 24 CONSTANTE NESTE MANUAL | — | Em caso de sinistro que impossibilite a locomoção própria do veículo segurado | Yelum Seguradora auto — CG YELUM PRODUTOS AUTO - Marcada 30… | 142 | `proposto` |
| Yelum Seguros Auto — LOCADORAS INTERMEDIÁRIO (nível 1) | pane seca | SIM | CONFORME DESCRITOS NA TABELA DE LIMITES DE ASSISTÊNCIA 24 CONSTANTE NESTE MANUAL | — | Em caso de pane que impossibilite a locomoção própria do veículo | Yelum Seguradora auto — CG YELUM PRODUTOS AUTO - Marcada 30… | 142 | `proposto` |
| Yelum Seguradora Auto — Plano Vidros Intermediário (nível 1) | vidros | com condição | R$ 130,00 por evento e R$ 260,00 por vigência | — | Referenciada - Passeio, Pick-up Leve e Esportivo - Nacionais | Yelum Seguradora auto — CG YELUM PRODUTOS AUTO - Marcada 30… | 166 | `proposto` |

## Yelum · Residencial — 4 linhas (4 proposto, 0 rascunho) · 1 plano

**De onde veio:**
* *Yelum Seguradora residencial — 2_202606_CG_Yelum Residência.pdf* (ramo do documento: Residencial) — arquivo: `2_202606_CG_Yelum Residência.pdf`

| plano (nível) | serviço | coberto | limite | carência | condição | documento | pág. | estado |
|---|---|---|---|---|---|---|---|---|
| Yelum Residência — Plano único (nível 1) | alagamento | com condição | R$ 150,00 por evento / R$ 300,00 por vigência | — | Contenção emergencial de alagamento decorrente de ruptura ou entupimento da rede embutida de tubulação | Yelum Seguradora residencial — 2_202606_CG_Yelum Residência… | 97 | `proposto` |
| Yelum Residência — Plano único (nível 1) | eletricista | com condição | R$ 150,00 por evento / R$ 300,00 por vigência | — | Reparos emergenciais em curto circuito, tomadas queimadas, interruptores defeituosos, troca de lâmpadas simples, reatores, disjuntores, fusíveis, chaves facas, troca de chuveiros/resistências não blindados. Exclui quebra de parede, teto ou piso, troca/instalação de fiação, danos por raio, troca de refletores/lâmpadas em tubo/luminárias com reatores | Yelum Seguradora residencial — 2_202606_CG_Yelum Residência… | 98 | `proposto` |
| Yelum Residência — Plano único (nível 1) | encanador | com condição | R$ 150,00 por evento / R$ 300,00 por vigência | — | Reparos emergenciais em vazamento aparente em tubulações PVC de 1 a 4 polegadas ou dispositivos hidráulicos, limitado à contenção emergencial | Yelum Seguradora residencial — 2_202606_CG_Yelum Residência… | 97 | `proposto` |
| Yelum Residência — Plano único (nível 1) | vidros | com condição | R$ 150,00 por evento / R$ 150,00 por vigência | — | Reparo ou reposição de vidros de portas ou janelas externas de áreas comuns externas com até 4mm de espessura. Exclui vidros que não comprometam segurança, vidros coloridos/fumês/temperados/jateados/fora de linha e vidros internos | Yelum Seguradora residencial — 2_202606_CG_Yelum Residência… | 98 | `proposto` |

## Allianz · Residencial — 3 linhas (2 proposto, 1 rascunho) · 1 plano

**De onde veio:**
* *Allianz Residência — Manual do Segurado e Condições Gerais* (ramo do documento: Residencial) — arquivo: `Condições Gerais - Allianz Residência_06_2026_final.pdf`

| plano (nível) | serviço | coberto | limite | carência | condição | documento | pág. | estado |
|---|---|---|---|---|---|---|---|---|
| Allianz Residência — Plano único (nível 1) | alagamento | NÃO | — | — | [reprovado] 'nao' de alagamento veio de cláusula de exclusão de risco de outra cobertura — precisa ser reextraído como condicionado | Allianz Residência — Manual do Segurado e Condições Gerais | 86 | `rascunho` |
| Allianz Residência — Plano único (nível 1) | eletricista | com condição | de acordo com o limite estipulado em contrato | — | Reparo elétrico em tomadas, interruptores, disjuntores ou fiações de baixa tensão; não coberto durante deficiência da rede elétrica; não cobre retorno se local for tecnicamente irreparável; não cobre alvenaria | Allianz Residência — Manual do Segurado e Condições Gerais | 117 | `proposto` |
| Allianz Residência — Plano único (nível 1) | granizo | SIM | — | — | Cobertura para danos causados diretamente por granizo, com exclusão de danos por entrada de água de chuva/granizo em aberturas naturais | Allianz Residência — Manual do Segurado e Condições Gerais | 86 | `proposto` |

## Mapfre · Residencial — 3 linhas (2 proposto, 1 rascunho) · 3 planos

**De onde veio:**
* *Mapfre Residencial — Condições Contratuais v2.9* (ramo do documento: Residencial) — arquivo: `Residencial_V.3.2.pdf`
* *Mapfre residencial — 1.Seguro Residencial Conteúdo_V1.2.pdf* (ramo do documento: Residencial) — arquivo: `1.Seguro Residencial Conteúdo_V1.2.pdf`

| plano (nível) | serviço | coberto | limite | carência | condição | documento | pág. | estado |
|---|---|---|---|---|---|---|---|---|
| Mapfre residencial — Seguro Residencial Conteúdo_V1.2 — Cobertura Adicional de Quebra de Vidros, Espelhos e Aparelhos Sanitários (nível 1) | vidros | com condição | até o limite máximo de indenização contratado | — | Sempre que constar expressamente a inclusão desta cobertura na Apólice/Certificado individual, mediante o recebimento do Prêmio específico | Mapfre residencial — 1.Seguro Residencial Conteúdo_V1.2.pdf | 51 | `proposto` |
| Mapfre residencial — Seguro Residencial Conteúdo — Cobertura Adicional de Vendaval, Granizo e Impacto de Veículos Terrestres (nível 1) | granizo | com condição | — | — | [reprovado] trecho_nao_esta_na_pagina | Mapfre residencial — 1.Seguro Residencial Conteúdo_V1.2.pdf | 46 | `rascunho` |
| Mapfre Residencial — Condições Contratuais V2.9 — Plano único (nível 1) | vidros | com condição | até o limite máximo de indenização contratado | — | Cobertura adicional, aplicável somente se constar expressamente a inclusão desta cobertura na apólice/certificado, mediante recebimento do prêmio específico; sujeita a exclusões listadas na cláusula 3.1 | Mapfre Residencial — Condições Contratuais v2.9 | 63 | `proposto` |

## Tokio Marine · Condomínio — 3 linhas (3 proposto, 0 rascunho) · 1 plano

**De onde veio:**
* *Tokio Marine condominio — 15414100909200412 - CG.pdf* (ramo do documento: Condomínio) — arquivo: `15414100909200412 - CG.pdf`

| plano (nível) | serviço | coberto | limite | carência | condição | documento | pág. | estado |
|---|---|---|---|---|---|---|---|---|
| Tokio Marine Condominio — Plano único (nível 1) | alagamento | com condição | R$ 300,00 (trezentos reais) por evento, limitado a 2 (duas) utilizações na vigência da apólice | — | dano por água proveniente, súbita e imprevista, de rupturas ou entupimentos da rede interna de água | Tokio Marine condominio — 15414100909200412 - CG.pdf | 38 | `proposto` |
| Tokio Marine Condominio — Plano único (nível 1) | eletricista | com condição | — | — | problema elétrico relacionado a curto-circuito e/ou interrupção de energia elétrica em decorrência de evento coberto | Tokio Marine condominio — 15414100909200412 - CG.pdf | 38 | `proposto` |
| Tokio Marine Condominio — Plano único (nível 1) | encanador | com condição | R$ 300,00 (trezentos reais) por evento, limitado a 2 (duas) utilizações na vigência da apólice | — | vazamento em tubulações de PVC de 1 a 4 polegadas ou dispositivos hidráulicos, sem necessidade de equipamento de detecção eletrônica | Tokio Marine condominio — 15414100909200412 - CG.pdf | 38 | `proposto` |

## Tokio Marine · Residencial — 3 linhas (3 proposto, 0 rascunho) · 1 plano

**De onde veio:**
* *Tokio Marine residencial — 15414100910200439 - CG.pdf* (ramo do documento: Residencial) — arquivo: `15414100910200439 - CG.pdf`

| plano (nível) | serviço | coberto | limite | carência | condição | documento | pág. | estado |
|---|---|---|---|---|---|---|---|---|
| Tokio Marine Residencial — Plano único (nível 1) | alagamento | com condição | até o Limite Máximo de Indenização contratado | — | Cobre entrada d'água por vias públicas, enchente/inundação, danos elétricos decorrentes, água de ruptura de adutoras externas, aumento de volume de rios/lagos/represas; exclui infiltração, entupimentos, transbordamentos internos, rompimento de tubulações internas, entre outros. | Tokio Marine residencial — 15414100910200439 - CG.pdf | 20 | `proposto` |
| Tokio Marine Residencial — Plano único (nível 1) | encanador | com condição | 250 reais | — | Aplica-se a vazamento em tubulações aparentes em PVC de 1 a 4 polegadas, ou em dispositivos hidráulicos, e a vazamentos súbitos de rede interna; exclui quebra de parede/teto/piso, tubulações de esgoto e caixa de gordura, reparos definitivos, entre outros. | Tokio Marine residencial — 15414100910200439 - CG.pdf | 27 | `proposto` |
| Tokio Marine Residencial — Plano único (nível 1) | granizo | com condição | até o Limite Máximo de Indenização contratado | — | Somente estarão cobertos os danos por chuva e/ou granizo, quando houver entrada de água na edificação segurada, devido ao destelhamento do imóvel segurado | Tokio Marine residencial — 15414100910200439 - CG.pdf | 22 | `proposto` |

## Bradesco · Condomínio — 2 linhas (2 proposto, 0 rascunho) · 1 plano

**De onde veio:**
* *Bradesco Seguros condominio — CC Condomínio.pdf* (ramo do documento: Condomínio) — arquivo: `CC Condomínio.pdf`

| plano (nível) | serviço | coberto | limite | carência | condição | documento | pág. | estado |
|---|---|---|---|---|---|---|---|---|
| Bradesco Seguro Condomínio Sob Medida — Plano único (nível 1) | granizo | SIM | até o Limite Máximo de Garantia Contratado | — | Danos materiais causados aos vidros, espelhos, bancadas de granitos, mármores ou aglomerados de mármores, porcelanatos e quartzo por chuva de granizo | Bradesco Seguros condominio — CC Condomínio.pdf | 42 | `proposto` |
| Bradesco Seguro Condomínio Sob Medida — Plano único (nível 1) | vidros | com condição | até o Limite Máximo de Garantia Contratado | — | Cobre danos materiais a vidros, espelhos, bancadas de granito/mármore/quartzo instalados nas áreas comuns, causados por calor artificial, ato involuntário de condôminos/empregados, choque térmico, granizo, imprudência de terceiros ou quebra espontânea; e danos a anúncios/letreiros/painéis luminosos por causa externa | Bradesco Seguros condominio — CC Condomínio.pdf | 42 | `proposto` |

## Mapfre · Automóvel — 2 linhas (2 proposto, 0 rascunho) · 2 planos

**De onde veio:**
* *Mapfre Automóvel — Condições Contratuais v34.0* (ramo do documento: Automóvel) — arquivo: `CG Automóvel_ Casco _MAPFRE_ V.41.final.pdf`

| plano (nível) | serviço | coberto | limite | carência | condição | documento | pág. | estado |
|---|---|---|---|---|---|---|---|---|
| Mapfre Automóvel — Plano único (nível 1) | vidros | com condição | — | — | Franquia cobrada em caso de troca de vidro para-brisa, lateral, traseiro, farol, lanterna, retrovisor ou teto solar/panorâmico; reparo de vidros isento de franquia | Mapfre Automóvel — Condições Contratuais v34.0 | 83 | `proposto` |
| Mapfre Automóvel — Condições Contratuais V34.0 — Plano único (nível 1) | vidros | com condição | Substituição Para-brisa ou traseiro: Por peça 350,00/400,00/500,00; Por vigência 700,00/800,00/1.000,00 | — | Cessará o direito de utilizar o serviço, caso tenha excedido o limite máximo monetário de utilização dos serviços contratados na apólice | Mapfre Automóvel — Condições Contratuais v34.0 | 99 | `proposto` |

## Mapfre · Condomínio — 2 linhas (2 proposto, 0 rascunho) · 2 planos

**De onde veio:**
* *Mapfre condominio — 1.Seguro Condominio_CG_2.3.pdf* (ramo do documento: Condomínio) — arquivo: `1.Seguro Condominio_CG_2.3.pdf`

| plano (nível) | serviço | coberto | limite | carência | condição | documento | pág. | estado |
|---|---|---|---|---|---|---|---|---|
| Mapfre Condominio — Cobertura Adicional de Alagamento (nível 1) | alagamento | com condição | até o Limite Máximo de Indenização – LMI | — | Garante danos materiais causados por entrada de água, enchentes, ruptura de encanamentos externos, inundação e aumento de volume de rios, com exclusões e bens não garantidos especificados | Mapfre condominio — 1.Seguro Condominio_CG_2.3.pdf | 61 | `proposto` |
| Mapfre condominio — Cobertura Adicional de Quebra de Vidros (nível 1) | vidros | com condição | até o Limite Máximo de Indenização | — | danos causados por acidente de origem externa, desde que façam parte do projeto original do condomínio | Mapfre condominio — 1.Seguro Condominio_CG_2.3.pdf | 88 | `proposto` |

## Porto · Automóvel — 1 linha (1 proposto, 0 rascunho) · 1 plano

**De onde veio:**
* *Porto Seguro Auto, RCF-V e APP — Condições Gerais* (ramo do documento: Automóvel) — arquivo: `3402 - Porto Seguro CG144_Susep.pdf`

| plano (nível) | serviço | coberto | limite | carência | condição | documento | pág. | estado |
|---|---|---|---|---|---|---|---|---|
| Porto Seguro Auto, RCF V E APP — Plano único (nível 1) | vidros | com condição | — | — | Exclusivamente para o segmento Auto Private, cobertura de Roubo e Furto de Faróis, Lanternas e Retrovisores; exclusões gerais aplicáveis a outros segmentos | Porto Seguro Auto, RCF-V e APP — Condições Gerais | 74 | `proposto` |

---

## O que NÃO temos

### 1. Seguradoras com condições gerais no acervo, mas ramos sem nenhuma linha extraída

📊 As 8 seguradoras com documento `ingested` no acervo têm **43 pares seguradora × ramo** com documento. Em **26** deles o extrator não produziu **nenhuma** linha — ou não rodou, ou rodou e não achou o capítulo de assistência.

> ⚑ **O que a coluna "documentos no acervo" conta** (nota acrescentada na segunda leitura, 18/09/2026): só os documentos com estado `ingested`, que são os que estão **no ar, na busca**. Ela **não** conta as versões já aposentadas, que continuam guardadas no banco e no arquivo. Onde isso muda a leitura: 📊 Bradesco Vida aparece com **1** e a tabela tem **59** linhas de Bradesco Vida (53 aposentadas); Mapfre Vida aparece com 1 e tem 27; Tokio Vida aparece com 1 e tem 9. **Não é acervo perdido — é decisão:** 📊 91 versões de vida foram retiradas de propósito em 11/08/2026, depois de se medir que, de 132 conversas reais do Bradesco, 3 falavam de vida. O número certo para "o que está no ar" é o da coluna; o número certo para "o que já foi baixado um dia" é maior.

| seguradora | ramo | documentos no acervo | dos quais condições gerais | planos extraídos | linhas extraídas |
|---|---|---|---|---|---|
| Allianz | Automóvel | 2 | 2 | 0 | **0** |
| Allianz | Condomínio | 1 | 1 | 0 | **0** |
| Allianz | Empresarial | 2 | 2 | 0 | **0** |
| Allianz | Equipamentos | 1 | 1 | 0 | **0** |
| Allianz | Vida | 2 | 2 | 0 | **0** |
| Bradesco | Empresarial | 2 | 2 | 0 | **0** |
| Bradesco | Equipamentos | 3 | 3 | 0 | **0** |
| Bradesco | Garantia | 1 | 1 | 0 | **0** |
| Bradesco | Vida | 1 | 1 | 0 | **0** |
| Mapfre | Empresarial | 6 | 6 | 0 | **0** |
| Mapfre | Equipamentos | 6 | 6 | 0 | **0** |
| Mapfre | Garantia | 1 | 1 | 0 | **0** |
| Mapfre | Vida | 1 | 1 | 0 | **0** |
| Porto | Condomínio | 1 | 1 | 0 | **0** |
| Porto | Empresarial | 1 | 1 | 0 | **0** |
| Porto | Garantia | 1 | 1 | 0 | **0** |
| Porto | Vida | 1 | 1 | 0 | **0** |
| Tokio Marine | Empresarial | 2 | 2 | 0 | **0** |
| Tokio Marine | Equipamentos | 3 | 3 | 0 | **0** |
| Tokio Marine | Garantia | 1 | 1 | 0 | **0** |
| Tokio Marine | Vida | 1 | 1 | 0 | **0** |
| Yelum | Condomínio | 1 | 1 | 0 | **0** |
| Yelum | Empresarial | 1 | 1 | 0 | **0** |
| Yelum | Equipamentos | 1 | 1 | 0 | **0** |
| Yelum | Garantia | 1 | 1 | 0 | **0** |
| Yelum | Vida | 1 | 1 | 0 | **0** |

📊 **Os buracos, agrupados por ramo** — quantos pares seguradora × ramo têm PDF no acervo e nenhuma linha lida:

| ramo | pares com documento | pares com ZERO linha |
|---|---|---|
| Empresarial | 6 | **6** |
| Vida | 6 | **6** |
| Equipamentos | 5 | **5** |
| Garantia | 5 | **5** |
| Condomínio | 6 | **3** |
| Automóvel | 8 | **1** |
| Residencial | 7 | **0** |

⚠️ O padrão é nítido: **`empresarial`, `equipamentos`, `garantia` e `vida` estão em ZERO em todas as seguradoras que têm o PDF** — o extrator só foi rodado sobre `auto`, `residencial` e `condomínio`, e mesmo neles sobrou buraco (Allianz auto; Allianz, Porto e Yelum condomínio).

### 2. Seguradoras da carteira sem nenhuma condição geral no acervo

📊 Fonte: `docs/canon/providers/susep/fila-onda-3.json` (medido em 2026-09-17). São **19** itens, na ordem da carteira medida — não do alfabeto.

**2a. Siglas do sistema de gestão que ainda não foram conciliadas com uma seguradora canônica** — enquanto a sigla não é conciliada, **toda** a carteira daquela seguradora fica sem conhecimento:

| ordem na carteira | sigla | nome no sistema de gestão | o que falta |
|---|---|---|---|
| 1 | `MAP` | MAPFRE CAPITALIZACAO | conciliar sigla |
| 2 | `AXA` | AXA SEGURADORA | conciliar sigla |
| 3 | `MAG` | MAG - MONGERAL | conciliar sigla |
| 4 | `JUNT` | JUNTO SEGURADORA S.A. | conciliar sigla |
| 5 | `AIG` | AIG SEGURADORA | conciliar sigla |
| 6 | `ESSO` | ESSOR SEGUROS S.A. | conciliar sigla |
| 7 | `ITAU` | ITAU SEGUROS S/A | conciliar sigla |
| 8 | `BERK` | BERKLEY INTERNATIONAL BRASIL | conciliar sigla |
| 9 | `CHUB` | CHUBB DO | conciliar sigla |
| 10 | `FATO` | FATOR SEGURADORA | conciliar sigla |
| 11 | `JNS` | JNS SEGUROS | conciliar sigla |
| 12 | `MITS` | MITSUI SEGURADORA | conciliar sigla |

**2b. Seguradoras já conhecidas pelo sistema, mas sem nenhuma condição geral baixada:**

| ordem na carteira | seguradora | o que falta |
|---|---|---|
| 13 | Alfa | CG no corpus |
| 14 | Sompo | CG no corpus |
| 15 | Suhai | CG no corpus |
| 16 | SulAmérica | CG no corpus |
| 17 | Sura | CG no corpus |
| 18 | Unimed | CG no corpus |
| 19 | Zurich | CG no corpus |

---

## Rascunhos — o que o verificador **reprovou**

⚠️ Estas linhas **não aparecem na fila da tela** e **não podem ser publicadas por clique** (`publicar_servico` só aceita `proposto`). Elas precisam ser **reextraídas**, não aprovadas.

### As 8 linhas de serviço em `rascunho`

O motivo fica gravado no próprio campo `condição`, com o prefixo `[reprovado]`.

| seguradora | ramo | plano | serviço | pág. | motivo gravado |
|---|---|---|---|---|---|
| Allianz | Residencial | Plano único | alagamento | 86 | 'nao' de alagamento veio de cláusula de exclusão de risco de outra cobertura — precisa ser reextraído como condicionado |
| Azul | Automóvel | Rede Referenciada sem Limite de KM | pane seca | 61 | trecho_nao_esta_na_pagina |
| Bradesco | Residencial | Plano único | alagamento | 32 | 'nao' de alagamento veio de cláusula de exclusão de risco de outra cobertura — precisa ser reextraído como condicionado |
| Bradesco | Residencial | Plano único | alagamento | 114 | trecho_nao_esta_na_pagina |
| HDI | Residencial | Plano único | alagamento | 88 | 'nao' de alagamento veio de cláusula de exclusão de risco de outra cobertura — precisa ser reextraído como condicionado |
| Mapfre | Residencial | Cobertura Adicional de Vendaval, Granizo e Impacto de Veículos Terrestres | granizo | 46 | trecho_nao_esta_na_pagina |
| Tokio Marine | Automóvel | Auto/Auto Clássico/Auto Roubo/Auto Roubo+Rastreador/Moto/Utilitário Carga/Auto Proteção Mensal/Moto Proteção Mensal/Utilitário Carga Proteção Mensal/Auto Frota (passeio, pick ups, motos e táxis) | guincho | 26 | trecho_nao_esta_na_pagina |
| Tokio Marine | Automóvel | Auto/Auto Clássico/Auto Roubo/Auto Roubo+Rastreador/Moto/Utilitário Carga/Auto Proteção Mensal/Moto Proteção Mensal/Utilitário Carga Proteção Mensal/Auto Frota (passeio, pick ups, motos e táxis) | pane seca | 26 | trecho_nao_esta_na_pagina |

### Os planos em `rascunho`

🔴 **O motivo de um plano reprovado não é gravado em lugar nenhum.** `plano_para_rascunho` (`backend/app/services/knowledge/assistance_plans_base.py`) exige um motivo, mas só o escreve no log do processo — a tabela `insurer_assistance_plans` não tem campo para ele. Por isso a coluna abaixo não pode ser preenchida sem inventar.

| seguradora | ramo | produto | plano (nível) | pág. do plano | motivo gravado |
|---|---|---|---|---|---|
| Mapfre | Condomínio | Mapfre condominio | Cobertura Adicional de Quebra de Vidros (nível 1) | 88 | — *(não existe campo para gravá-lo)* |
| Mapfre | Residencial | Mapfre residencial — Seguro Residencial Conteúdo_V1.2 | Cobertura Adicional de Quebra de Vidros, Espelhos e Aparelhos Sanitários (nível 1) | 51 | — *(não existe campo para gravá-lo)* |
| Mapfre | Residencial | Mapfre residencial — Seguro Residencial Conteúdo | Cobertura Adicional de Vendaval, Granizo e Impacto de Veículos Terrestres (nível 1) | 46 | — *(não existe campo para gravá-lo)* |
| Tokio Marine | Automóvel | Tokio Marine Auto | Auto/Auto Clássico/Auto Roubo/Auto Roubo+Rastreador/Moto/Utilitário Carga/Auto Proteção Mensal/Moto Proteção Mensal/Utilitário Carga Proteção Mensal/Auto Frota (passeio, pick ups, motos e táxis) (nível 1) | 26 | — *(não existe campo para gravá-lo)* |
| Tokio Marine | Automóvel | Tokio Marine Caminhão | Caminhão/Auto Frota (Caminhões, rebocadores, reboques, semirreboques, vans, furgões, ambulâncias e ônibus) (nível 1) | 26 | — *(não existe campo para gravá-lo)* |

⚠️ Um plano em `rascunho` **congela as linhas de serviço penduradas nele**: mesmo que a linha esteja em `proposto` e você a aprove, `publicar_servico` publica o plano pai junto — e ele só sobe a partir de `proposto`. 📊 Há **4 linhas em `proposto` presas debaixo de planos em `rascunho`** (Mapfre Condomínio: 1, Mapfre Residencial: 1, Tokio Marine Automóvel: 2).

---

## Antes de mandar publicar: a fila não está aparecendo na tela

📊 18/09/2026, medido: o painel mostra **"60 linhas esperando revisão"** no topo e **"Nada esperando revisão"** no bloco de baixo. Os dois vêm de **chamadas diferentes**:

```
GET /api/assistance-plans/cobertura   ->  200, 2,3 s   {0, 8, 60}   <- o topo
GET /api/assistance-plans/fila        ->  60 itens, 65,3 s          <- o bloco de baixo
```

A segunda chamada baixa **24 PDFs do MinIO** para mostrar a página ao lado de cada linha. 📊 Medida daqui, ela leva **65,3 s** e devolve as 60 linhas com o texto da página — a base está certa, o dado existe.

**Por que ela não chega à tela em produção — inferência, com o que a sustenta.** Para grifar os termos do serviço na página, o endpoint lê o vocabulário versionado em `docs/canon/providers/susep/servicos-de-assistencia.json`. Três fatos medidos em 18/09/2026:

* 📊 `backend/Dockerfile` é `WORKDIR /app` + `COPY . .`, e o `/health` de produção publica `code_files: 396` — exatamente o número de arquivos `.py` dentro de `backend/app`. Logo, a imagem é construída **com a pasta `backend/` como raiz**, e o `docs/` do repositório **não está dentro dela**.
* 📊 Reproduzindo essa árvore (um `app/services/knowledge/` sem `docs/` ao lado), o resolvedor do vocabulário tenta **um** caminho, não acha, e levanta `VocabularioNaoEncontrado`.
* 📊 Nada no endpoint da fila captura essa exceção — ela sobe como **HTTP 500**. O endpoint da cobertura, o que alimenta os três números do topo, **não lê o vocabulário** e por isso continua respondendo 200.

Isso explica exatamente o que está na tela: o topo responde, o bloco de baixo não. ⚠️ Não foi possível confirmar chamando a produção com a chave interna a partir desta máquina — por isso está marcado como inferência, e não como medição.

🔴 **E o front trata qualquer falha dessa chamada como "não há nada"**: `app/api/dashboard/knowledge/planos/route.ts:43` transforma o erro num objeto sem `itens`, `KnowledgeClient.tsx:108` transforma o `itens` ausente numa lista vazia, e `FilaDeCuradoria.tsx:88` escreve *"Nada esperando revisão"*. Ninguém pergunta se a chamada deu certo — por isso a tela parece tranquila enquanto o contador logo acima diz 60.

**Esta lista existe para você conferir o conteúdo enquanto a tela é consertada.** Nenhuma das 81 linhas está publicada, e nenhuma chega a um cliente antes de alguém aprovar.














