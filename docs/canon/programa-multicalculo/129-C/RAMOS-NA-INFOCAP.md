# Condomínio, Residencial e Empresarial na InfoCap: o que a carteira mostra

> SPEC-129-C · BLOCO 0 · investigação B0-b · medido em 11/10/2026, só leitura (GET) na conexão InfoCap `connected`
> (a da Resulta, ligada à corretora de ensaio). Nenhum CPF, CNPJ, nome ou telefone aparece aqui. Cada apólice é
> citada por `sha256(nosnum)[:10]`; as que vieram das conversas, por `conv-<sha256(pdf)[:12]>`.
> Os PDFs e o índice estão FORA do git, em `docs/intake/MULTICALCULO AGGER/129C-RAMOS/` (`INDICE.json`).

## 0. O achado que muda a SPEC

📊 **A InfoCap da Resulta quase não tem esses três ramos.** De 2015 a 2026, `/documentos_bi` (por `inivig`, `tipo_doc=TODOS`,
um ano por chamada) devolve **32.901 documentos**: Condomínio **0**, Residencial **12** (11 apólices e 1 endosso),
Empresarial **3**, Bilhete Residencial **0**. Ou seja, **15 documentos, 0,05 % da base**. O resto é AUTO, FROTA, CARTA VERDE, MOBI e PQRE.

As contraprovas, cada uma por um caminho diferente:

| prova | resultado 📊 |
|---|---|
| `/renovacoes` vigentes (`fimvig` de 11/10/2026 a 31/12/2031, `cancelado=F`) | 3.040 linhas: AUTO 2.972 · MOBI 33 · FROT 27 · **RESI 5 · EMPR 2 · COND 0** |
| `/renovacoes` com `codram=4` (Condomínio), 2025 a 2027, cancelados incluídos | **0** |
| `/documentos?texto=` com `CONDOMINIO`, `EDIFICIO`, `RESIDENCIAL` e `ASSOCIACAO` | **0** cada · `LTDA` → 223 (171 AUTO, 44 FROT, 2 EMPR) |
| `/lista_clientes?texto=` (busca pelo começo do nome) com `CONDOMINIO` e `EDIFICIO` | **0** clientes num cadastro de 16.290 |
| `codfil` 2 a 5 em `/documentos` e `/documentos_bi` | a API ignora o parâmetro: tudo vem como `codfil=1` (uma filial só) |
| permissões do usuário da API (`p*` no `/login`) | todas `T`: a falta **não** vem de perfil restrito |
| **79 dos 88** CPF/CNPJ válidos tirados das conversas de sinistro e assistência de "outros ramos" (as da Saionara) **são clientes na InfoCap** | os 518 documentos ligados a eles (`/cliente_ligacoes`) são AUTO 488 · FROT 16 · CTVE 10 · MOBI 4 · **RESI/COND/EMPR 0** |

**FATO:** os clientes de condomínio, residencial e empresarial da Resulta estão cadastrados na InfoCap, mas as apólices
desses ramos **não**. **INFERÊNCIA:** a carteira patrimonial é controlada fora da InfoCap (no Agger, nos portais das
seguradoras ou em planilha); a InfoCap da Resulta é, na prática, o sistema do AUTO. O retorno do Founder (10/10) partia de
outra premissa: *"a melhor forma de ver condomínio e empresarial é analisando a InfoCap"*. A medição desmente.
**RECOMENDAÇÃO:** a fonte dos ramos patrimoniais para a 129-C é o **histórico de negócios do Agger** (📊 672 condomínio,
182 empresarial e 115 residencial, segundo a 128) mais os **manuais da Resulta**, que estão para chegar.

⚠️ A base também guarda emissões de uma **segunda corretora do mesmo grupo**: dos 14 documentos patrimoniais com PDF, 10 foram emitidos por ela e 4 pela Resulta.
Uma conexão InfoCap pode carregar mais de uma SUSEP, e o vínculo apólice ↔ corretora tem de ler o corretor da
apólice, não presumir que é a dona da conexão (CLAUDE.md §13.9).

## 1. Seguradoras por ramo

📊 Comando: `ic.get("/documentos_bi", {datini, datfim, data:"INIVIG", tipo_doc:"TODOS"})` ano a ano de 2015 a 2026,
filtrando `ramo ∈ {COND, RESI, EMPR, BRES}`. "Vigente" = `inivig ≤ 11/10/2026 ≤ fimvig`. Mapa nome ↔ código da InfoCap
(`/ramos`): **CONDOMINIO = 4 (COND) · RESIDENCIAL = 2 (RESI) · EMPRESARIAL = 3 (EMPR) · BILHETE RESIDENCIAL = 45 (BRES)**.
Não bate com os códigos do Agger (16 / 2 / 18): o mapa é por sistema.

| ramo (InfoCap) | vigentes hoje | emitidas nos últimos 12 meses | renovadas nos últimos 12 meses* | todas desde 2015 |
|---|---|---|---|---|
| Condomínio (4) | **0** | 0 | 0 | **0** |
| Residencial (2) | **5**: HDI 4 · Porto 1 | 5: HDI 4 · Porto 1 | 2 (HDI → HDI) | 11 apólices + 1 endosso: **HDI 7 · Allianz 2 · Porto 2** |
| Empresarial (3) | **3**: Yelum 2† · Sura 1 | 3 | 0 | 3: Yelum 2† · Sura 1 |

\* Nenhuma linha traz `nosnum_ren`: a renovação foi reconhecida pelo mesmo cliente com apólice do mesmo ramo um ano antes.
† As duas "EMPR" da Yelum são **o mesmo documento** (mesmos PDFs, mesmo hash), cadastrado com dois códigos de cliente, e o
documento é um **Compreensivo Residencial** de apartamento para pessoa jurídica. O ramo da InfoCap está errado nas duas.
Corrigindo: Empresarial verdadeiro = **1** (Sura, ainda proposta), e Residencial ganha 1 apólice.

**Sobre "90 % é Allianz no residencial":** a InfoCap não permite confirmar nem desmentir. São 2 Allianz em 12, e as
duas venceram em fev/mar de 2026 sem renovação registrada. 💭 Isso combina com a carteira Allianz da Resulta morar fora da InfoCap.
Como sinal indireto (📊 n pequeno): nas 19 conversas de sinistro de "outros ramos", a seguradora mais citada é Allianz em 3,
Tokio em 1 e Porto em 1. Nas 14 de assistência, Yelum, Allianz e Tokio aparecem 2 vezes cada. Nas 6 com reguladoras, Allianz
aparece 2 vezes, as duas em **condomínio**.

## 3. Coberturas típicas por ramo

Fonte: os PDFs das apólices, baixados por `/documento_anexos` (a InfoCap entrega o arquivo num link do S3), mais 3 PDFs
de seguro patrimonial encontrados nas conversas do intake. 📊 O `/itens` traz `garantias[]` estruturadas (`garantia`, `impseg` = LMI,
`taxa`, `premio`, `franquia`, `percom`) em **só 4 dos 15** documentos, porque o resto depende de alguém lançar à mão. Onde existem,
batem com o PDF (conferido em 2 apólices). O `/documento` não traz LMI. **A fonte confiável é o PDF; `garantias[]`, quando vem,
é um atalho.** A amostra é pequena e vale como formato, não como estatística.

### 3.1 Residencial: 13 apólices distintas (11 da InfoCap, contando a Yelum reclassificada, e 1 Tokio das conversas)

| cobertura | aparece em | LMI mediano | faixa de LMI | franquia (participação obrigatória) |
|---|---|---|---|---|
| Incêndio / raio / explosão / fumaça (**a básica**) | 13/13 | R$ 100.000 | 30.000 – 3.450.000 | não há (HDI e Yelum: 10 %, mínimo R$ 350, só para queda de raio) |
| RC Familiar | 13/13 | R$ 6.000 | 5.000 – 260.000 | não há |
| Assistência 24 h | 13/13 | — | Especial / Completa / VIP / Essencial gratuita | — |
| Vendaval / granizo | 12/13 | R$ 8.000 | 6.000 – 550.000 | 10 % com mínimo de R$ 300 a 650 (Allianz: 15 %, mínimo R$ 700) |
| Perda ou pagamento de aluguel | 11/13 | R$ 3.000 | 3.000 – 120.000 | não há |
| Danos elétricos | 6/13 | R$ 20.000 | 5.000 – 700.000 | 10 % com mínimo de R$ 500 a 600 |
| Roubo / subtração de bens | 4/13 | ~R$ 22.500 | 5.000 – 320.000 | — |
| Quebra de vidros | 4/13 | ~R$ 17.500 | 9.000 – 37.500 | 10 %, mínimo R$ 150 |
| Ruptura de tubulações / vazamento | 3/13 | R$ 20.000 | 9.000 – 37.500 | 10 % com mínimo de R$ 500 a 800 |
| Impacto de veículos | 2/13 | — | 25.000 – 60.000 | 10 %, mínimo R$ 300 |
| Valor de novo (cláusula) | 2/13 | — | — | — |
| Tumultos · despesas extraordinárias · equipamentos eletrônicos · roubo fora do local | 1/13 cada (Allianz) | — | — | — |

⚠️ Seis das 13 são **HDI Duo**, um residencial **atrelado ao seguro auto** com pacote fixo (incêndio 30 mil, aluguel 3 mil,
vendaval 6 mil, RC 6 mil, assistência especial; prêmio total de R$ 166 a 198). O Duo puxa as medianas para baixo. Só nas 7 avulsas:
incêndio 7/7 (mediana R$ 500 mil), RC 7/7, vendaval 6/7, danos elétricos 6/7, aluguel 5/7, roubo 4/7, vidros 4/7, assistência 7/7.

- **Pacote padrão** (o que quase todas as avulsas têm): Incêndio + RC Familiar + Vendaval + Danos Elétricos + Aluguel +
  Assistência 24 h. Roubo e vidros entram em pouco mais da metade.
- **O mais em conta que aparece:** Porto básico com Incêndio R$ 100 mil + RC R$ 10 mil + Aluguel R$ 8 mil e assistência
  essencial gratuita, por 📊 R$ 247,88 de prêmio total. Entre os atrelados ao auto, o HDI Duo, por R$ 166 a 198.
- **Casa × apartamento:** casa 10 · apartamento 2 · Tokio sem o dado. **Habitual × veraneio:** habitual 12 · veraneio 1
  (Allianz, casa de praia).
- **Prêmio total** (InfoCap `pretot`, 12 apólices, a Yelum contada uma vez): mediana 📊 **R$ 222,95**, faixa R$ 166 a 2.253.
  Sem o Duo (6 apólices), mediana R$ 866,55, faixa R$ 248 a 2.253.
- A Tokio cota a mesma oferta com 3 assistências (📊 prêmio líquido de R$ 872,78, R$ 958,91 e R$ 1.242,59 para os mesmos LMIs):
  a assistência é um eixo de preço próprio.

### 3.2 Condomínio: 1 apólice (Tokio Marine, das conversas; nenhuma na InfoCap)

Residencial **vertical**, **sem elevador**, indenização por **valor de novo**, renovação sem sinistro, classe de bônus 5.
📊 Prêmio líquido R$ 8.320,17 · total R$ 8.934,20 · limite máximo de garantia R$ 21.380.000.

| cobertura | LMI | franquia |
|---|---|---|
| Incêndio / raio / explosão / fumaça / aeronave (**a básica**) | R$ 17.600.000 | — |
| Incêndio de bens dos condôminos | R$ 2.000.000 | — |
| RC do Síndico · RC do Condomínio | R$ 700.000 cada | — |
| Despesas com aluguel dos condôminos | R$ 250.000 | — |
| Vendaval / granizo | R$ 200.000 | 20 %, mínimo R$ 2.500 |
| RC Garagem compreensiva | R$ 100.000 | 10 %, mínimo R$ 1.500 |
| Ruptura de tanques e tubulações | R$ 80.000 | (cobrada) |
| Danos elétricos | R$ 40.000 | 20 %, mínimo R$ 4.000 |
| RC Portões automáticos | R$ 30.000 | 10 %, mínimo R$ 2.500 por portão e veículo |
| Roubo com arrombamento | R$ 10.000 | 10 %, mínimo R$ 200 |
| Quebra de vidros / anúncios | R$ 5.000 | 10 %, mínimo R$ 500 |
| Assistência 24 h | plano completo | — |

O que a apólice mostra que o formulário pede: tipo (residencial), estrutura (vertical), elevadores (sim ou não), tipo de
indenização (valor de novo) e bônus. **Não aparecem** área construída, número de unidades, blocos nem pavimentos: se o
Agger pedir esses campos, eles vêm do cadastro do condomínio ou do síndico, não da apólice anterior.
Outro sinal (📊 2 termos de reguladora nas conversas): há apólices **Allianz Condomínio** na carteira, e nenhuma está na InfoCap.

### 3.3 Empresarial: 1 proposta (Sura Compreensivo Empresarial)

Ocupação **"edifícios desocupados (imóvel totalmente desocupado)"**, uma loja; classe de ocupação 4 para incêndio e 3 para
vendaval; região SC 4; plano único; valor em risco (prédio) R$ 911.000; protecional: só extintores. 📊 Prêmio líquido R$ 1.242,75.

| cobertura | LMI | franquia |
|---|---|---|
| Incêndio / raio / explosão / aeronave / fumaça (básica, "única") | R$ 911.000 (= valor em risco) | 10 % dos prejuízos |
| Vendaval / granizo | R$ 50.000 | 10 %, mínimo R$ 1.500 |
| Impacto de veículos | R$ 30.000 | 10 %, mínimo R$ 300 |
| Danos elétricos (riscos comerciais) | R$ 20.000 | 10 %, mínimo R$ 3.000 |

Uma proposta de imóvel vazio **não serve** como "pacote padrão" do empresarial. O que ela mostra é o formulário:
atividade principal, ocupação/classe, região, valor em risco do prédio e do conteúdo (`Val Risco DM` / `LC`) e os protecionais.

## 4. A regra dos +15 % na renovação

📊 Na InfoCap só existem **2 pares** de anos seguidos (mesmo cliente, mesmo ramo, apólice que vence seguida da que começa):

| par | cobertura básica (incêndio) ano 1 → ano 2 | variação | prêmio total |
|---|---|---|---|
| HDI Duo, 10/2024 → 10/2025 | R$ 30.000 → R$ 30.000 | **0 %** | R$ 170,40 → 175,94 (+3,3 %) |
| HDI Duo, 03/2025 → 03/2026 | R$ 30.000 → R$ 30.000 | **0 %** | R$ 183,18 → 166,16 (−9,3 %) |

**Veredito: NÃO CONFIRMADO, e não dá para testar aqui.** n = 2, e os dois pares são de um produto de pacote fixo atrelado
ao auto, em que ninguém mexe na cobertura. A regra do Founder vale para as renovações que as comerciais montam (condomínio,
residencial avulso, empresarial), e essas não estão na InfoCap. Duas apólices das conversas são renovações (Tokio condomínio
e Tokio residencial), mas a apólice do ano anterior não está disponível. **RECOMENDAÇÃO:** medir os +15 % no histórico
de renovações do Agger (LMI do ano anterior × LMI cotado) ou esperar o manual. Até lá, tratar como **regra declarada pelo
Founder, não medida**, e guardá-la como parâmetro da corretora (percentual e coberturas a que se aplica), não fixa no código.
