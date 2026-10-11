# LAUDO — Prints do dashboard CORP / InfoCap (modo INVESTIGAÇÃO, read-only)

> Investigador read-only · 11/10/2026 · nenhum arquivo do repositório alterado.
> Fonte: `docs/intake/PRINTS INFOCAP-CORP/` (ignorada pelo git: `git check-ignore` → `.gitignore:113:docs/intake/`; `git ls-files` → 0 arquivos).
> Regra de PII: nenhum nome de cliente, CPF, CNPJ, telefone, e-mail ou placa neste laudo. Produtores (funcionários) aparecem por **código + iniciais**.

## EXECUTION CARD (investigação, §3.3 — conta de risco dispensada)
```
OUTCOME ........ saber o que o dashboard do CORP mostra que a API não entrega, e o que capturar no navegador
RISCO .......... 0 (leitura de imagens) · SUPERFÍCIE 3 (território não mapeado) → MODO INVESTIGAÇÃO
NÍVEL .......... investigador read-only, Opus 5.5, sem juiz (não há mudança)
O ELO .......... "o CORP clássico dos prints é a Resulta" → medi A (tela) e B (números), e cruzei os números
                 com a AutoFleet (§1.3). Não há login de corretora visível no CORP clássico: é INFERÊNCIA.
GATES .......... cada fato cita o print; número medido com 📊 e a fonte
```

## 0. O acervo — o que tem lá (FATO)
- 📊 `ls` → 49 imagens `image*.png` + `33.png`/`34.png`/`35.png` + 1 `.md` em `TELAS DASHBOARD INFOCAP/`; 3 imagens em `IMAGENS CORP INFOCAP/`.
- 📊 `md5sum` → os `33/34/35.png` das duas pastas são **byte a byte iguais** (`00e7f9…`, `8436ab…`, `53b488…`). São **mosaicos** (pranchas de contato) dos mesmos prints `image*.png` — nada novo neles.
- Os prints são **antigos**: o relógio da barra de tarefas marca **30/06/2025 22:26–23:42** (CORP clássico, `image.png`…`image 21.png`) e **01/07/2025 11:47–12:57** (CorpNow, `image 22`…`image 49`). 📊 15 meses antes de hoje.
- O `.md` cita `image 50`…`image 54` (Google Meu Negócio): **não existem** na pasta.
- Legendas do `.md` desalinhadas: "CONSULTA DE DOCUMENTOS" está sobre `image 1.png`, que é a **grade de clientes**; "CONTROLE DE COMISSÕES" está sobre `image 2.png`, que é a **busca de documentos**. **Não há print de "Controle de Comissões"** (o mais próximo é o INCORP, `image 15`). No "Exemplo 3", `image 39–42` são de **outro documento** (nosso nº 95385), não do cancelado 95303/96072 de `image 36–38`.

---

## 1. Qual corretora / usuário / filial cada print mostra

### 1.1 Há DOIS sistemas diferentes nos prints
| | CORP clássico | CorpNow |
|---|---|---|
| prints | `image.png` … `image 21.png` | `image 22.png` … `image 49.png` |
| endereço | `corpnuvem-46.ddns.net/software/html5.html` (todos) | `corpnow.com.br/#/dashboard`, `#/busca`, `#/apolice/…`, `#/endosso/…`, `#/renovacoes`, `#/seguradoras` |
| usuário | canto superior direito **"Matr - [usuário do Founder]"** (`image.png`, `1`, `2`, `4`, `15`–`21`); combo **"[usuário do Founder]"** na Central de Negócios (`image 3`) | barra lateral **".RAFAEL"**, e-mail do domínio **@autofleetseguros.com.br** (`image 22`–`49`) |
| corretora na tela | **nenhum nome de corretora aparece** em nenhuma tela | **"AUTO FLEET R CORRETORA DE SEGU"** escrito na barra lateral (`image 22`–`49`) |
| filial | "Filial: MATR" (`image 3`); coluna Filial = MATR (`image 1`, `2`); filtro Filial MATR **travado** (`image 5`, `6`) | campo "Filial: MATR" no documento (`image 26`, `31`, `36`, `37`) |

**FATO:** os prints do CorpNow são **da AutoFleet** — o nome está na tela. Todos os documentos que aparecem são do ramo AUTOMOVEL (`image 24`, `25`, `26`, `31`, `36`, `45`, `46`).

**FATO:** **MATR** aparece nos dois sistemas → é o nome-padrão da filial nº 1 de cada base (provavelmente "Matriz"). **Não serve para distinguir corretora.**

### 1.2 O CORP clássico é a Resulta? — INFERÊNCIA forte (nota 85/100)
Nenhuma tela do CORP clássico tem o nome da corretora. Os indícios:
1. **Título da aba do navegador.** Com o ícone do CORP, a aba ativa do clássico começa com "R" (`image.png`, `1`, `2`); nos prints do CorpNow a aba vizinha, com o mesmo ícone, se chama **"Resu…"** (`image 23`–`49`), ao lado de outra chamada "Corp". O título da página do clássico parece ser o nome da base: "Resu[lta]".
2. **Mistura de ramos.** Ranking de prêmio 2025 (`image 9`): EMPR 29,3 % · COND 14,5 % · SAUD 14,0 % · CAPI 10,5 % · ENGE 9,0 % · RC 4,3 % · **AUTO 3,8 %**. A busca de documentos (`image 2`) mostra RESI, COND, CAPI, VIND, EMPR, VGRP; a de sinistros (`image 4`) mostra EMPR, COND, ONIB, ENGE. É uma base de ramos **não-auto**.
3. **🔴 O cruzamento (o ELO).** Os números do clássico **não batem** com os da AutoFleet no CorpNow no mesmo mês, então as bases são outras:
   - 📊 prêmio de **jul/24**: clássico **2.084k** (`image 7`, barra Jul/24) × CorpNow AutoFleet **≈ R$ 1,2 mi** no dia 31 da curva "Anterior (2024)" (`image 22`, `23`).
   - 📊 documentos de **jul/24**: clássico **603** (`image 13`) × CorpNow AutoFleet **≈ 340** (`image 22`, barra "Anterior (2024)").

   Duas bases diferentes. Uma é a AutoFleet (o nome está na tela), e a outra tem perfil não-auto e aba "Resu…" → **Resulta**.

⚠️ **FATO que destoa da premissa "a Resulta só faz não-auto":** em 06/2025 a base clássica ainda tinha **AUTO em 3,8 % do prêmio 2025** (`image 9`), **3,7 % da comissão** (`image 12`) e **3,9 % dos documentos de jun/25** (`image 14`). Pode ser carteira residual, anterior à separação por imposto. Os prints são de 15 meses atrás e **não provam** como a base está hoje.

### 1.3 Achado fora do escopo, importante — o nº interno ("nosso número") se repete entre as duas bases
📊 Resulta (clássico) em 30/06/2025: nosso nº **96672–96688** (`image 2`). 📊 AutoFleet (CorpNow) em 01/07/2025: nosso nº **94323, 95106, 95303, 95385, 96072** (`image 26`, `31`, `36`, `37`, `39`). As faixas **se sobrepõem**, então o mesmo `nosnum` pode existir nas duas bases.
**RECOMENDAÇÃO:** toda chave, cache ou vínculo de documento InfoCap no produto deve ser **(company_id, conexão, codfil, nosnum)**, nunca só o `nosnum`. É o mesmo tipo de defeito da conexão "InfoCap RESULTA" que estava com o login da AutoFleet: um número sozinho não diz de que base veio.

### 1.4 Um identificador de base na URL do CorpNow — INFERÊNCIA
Toda URL de documento da AutoFleet tem a forma `#/apolice/DOCUMENTOS_2024090009_1_<nosnum>` (`image 26`–`42`), e o endosso usa `#/endosso/DOCUMENTOS_2024090009_1_96072` (`image 38`). Lendo a forma: `2024090009` **constante** = provável código da base ou licença da AutoFleet no InfoCap; `1` = codfil; o último número = nosnum. Se a Resulta tiver outro código nessa posição, ele **identifica a base sem ambiguidade**. Vale capturar (§7).

---

## 2. O MAPA do sistema

### 2.1 CORP clássico (Resulta, 30/06/2025)
**Moldura:** menu `Arquivos · Movimentos · Consultas · Ferramentas · Aplicativos · Sistema · Ajuda`. Barra de ícones: clientes, documentos (com submenu), "Busca – Tempo de execução", negociações, sinistro (submenu **Incluir Sinistro / Consultar Sinistro**, `image 4`), financeiro (submenu), consulta, gráficos, Multi, calculadora, celular, sair (`image.png`, `1`).

| tela | print | o que mostra · CAMPOS |
|---|---|---|
| **Cadastro de Clientes** | `image.png`, `image 1` | abas **Grade · Cadastro · Contatos · Perfil · Observações · Anexos · Dados Bancários**; "Mostrar Inativos"; "Usar Filtros Avançados"; colunas **Filial, Código, Nome, Pessoa (F/J), Dt. Nascimento, Idade, Sexo, Empresa, Venc. CNH, CPF/CNPJ, Telefone**; legenda "Cliente Inativo". 📊 **14.540 registros** na busca "A" (`image 1`) |
| **Busca de Documentos** | `image 2` | modos **Busca Por Documento / Busca Geral**; checkbox **"Buscar também por documentos antigos"**; colunas **Filial, Nosso Nº, Situação (ícone colorido), Tipo (ícone), Nome, Seguradora, Ramo, Dt. Proposta, Início Vig., Fim Vig., Nº Apólice, N…** (cortada). Linhas em cinza itálico com ícone "X" (cancelado/antigo). Apólice ainda sem número = "0" |
| **Central de Negócios** (pipeline) | `image 3` | abas **Oportunidades · Negociações (contador vermelho "0") · Multi**; filtros **Temperatura** (3 ícones: frio/morno/quente), **Status** (5 ícones), **Campanha**, **"Em andamento"**, **Tipo**, **Período** por **"Próxima Ação"** (Personalizado, Inicial/Final), **"Filial: MATR"**, combo de **usuário "[usuário do Founder]"**, "Salvar filtros ao sair do programa"; visões **Grade (Lista) · Funil de Vendas · Gráfico**; atalhos **Hoje · Nos Dias Próximos (0) · Esta Semana · Este Mês**; colunas **Código, Temp., Status, Lig., Multi, Cliente, Seguradora, Ramo, Tipo, Próx. Ação, Próx. Ação Descrição** (a grade estava vazia) |
| **Consulta de Sinistro** | `image 4` | busca com janela padrão **"Últimos 180 dias"**; abas 📊 **Pendentes 9 · Em Andamento 4 · Encerrados 59**; filtro "Todos"; colunas **Nosso Nº, Tipo ("S"), Segurado/Terceiro, E-mail, Seg., Ramo, Apólice, Endosso, Nº Sinistro, Ocorrência, Aviso**; botões **+SINISTRO · +ATENDIMENTO · +TERCEIRO** |
| **Gerenciador de Relatórios** | `image 5`, `6` | árvore: **Documentos** (Solicitação de Emissão, Propostas Grade por Produtor, Propostas Grade, Propostas, Novos, **Renovações**, **Não Renovados**, Vencimento de Parcelas) · **Clientes** (Dados Cadastrais, Extrato, Aniversários, Maiores-Top, com Documentos, Vencimento de Habilitação) · **Comissões** (Recebidas, Pendentes, Diferenças, Fechamento, **Repasse ao Produtor**, Comissões por Documento) · **Fluxo de Caixa** (Extrato Diário, Mapa Mensal de Categorias, Mapa de Saldos, Mapa Financeiro de Categorias) · **Sinistros** (Geral, Geral-Grade, Individual) · **Gerenciais** › Pacotes (Análise por Atividade) › Automóvel (Garantias, Cadastrados) › Comissões (Recebidas, Pendentes) › Propostas (Produtor x Tipo de Ramo, Produtor x Seguradora, Comparativo entre Períodos, Análise de Desempenho, Análise Mensal de Produção, **Análise de Renovações**, Acompanhamento de Produção, Análise da Carteira por Cliente). **Filtros comuns:** Seguradora, **Filial (MATR, travado)**, Canal de Vendas, Ramo, **Empresa (Todas, travado)**, Cliente, **Agente**, **Grupo de Produtores**, **Comissão Direta/Indireta (travado)**. **Filtros específicos:** Período Inicial/Final, Data = "Início de Vigência", Situação da Proposta, Tipo de Documento. Exporta Excel/PDF/e-mail |
| **Gráficos e métricas** | `image 7`–`14` | abas **Prêmio Base · Comissão · Qtde de Docs**; **Produção Total · Ranking**; **Análise Anual / Mensal**; cartões **Produção Total, Novos, Renovações, Faturas, Endossos** com variação contra o ano anterior; cartão de **meta** ("0 % ATINGIDA — MUITO ABAIXO DA META"); comparativo diário ou mensal contra o ano anterior; demonstrativo de 12 meses ou de 10 anos; rankings de **Seguradoras, Ramos, Produtores** (barras empilhadas Renovações/Novos/Faturas/Endossos). 📊 Prêmio 2025 até jun = **6.874.481,71** (`image 8`); jun/25 = **1.217.443,08** (`image 7`); comissão 2025 = **1.225.860,64** (`image 11`) |
| **INCORP** (importação das seguradoras) | `image 15` | abas **Propostas · Comissões (0) · Histórico de Comissões**; botões **Importar / Eliminar**; Tipo de Ação (Todos/Importados/Eliminados), Período, Seg., Cliente; colunas **Códi., Nº Incorp, Ação, NN°, Seg., Cliente, Apo./End., Parcela, Dt. Import., Fil., Vl. Recebido, Dt. Receb., Usuário**. 📊 **26.228 registros** |
| **Multicálculo** | `image 16`–`21` | passos **Segurado · Automóvel · Perfil · Seguro** + botão "CALCULAR NO MULTI". A aba Seguro tem o bloco **RENOVAÇÃO**: "Esta é uma renovação", Início/Final Vig. anterior, Seguradora anterior, Número Apólice Anterior, Código Interno (CI), Quantidade de sinistros, Bônus de renovação (`image 21`) |
| Fluxo de Caixa (ao fundo) | `image.png`, `16` | "Consulta de Fluxo de Caixa": Grade, colunas Nº Mov., Origem/Destino, Nº Cheque, Categoria |

### 2.2 CorpNow (AutoFleet, 01/07/2025)
Menu lateral com **apenas 4 itens: Produção · Busca · Renovações · Seguradoras** (`image 22`). Não tem negócios, sinistros, financeiro, tarefas, relatórios, usuários nem filiais.

| tela | print | CAMPOS |
|---|---|---|
| **Produção** | `image 22`, `23` | mês (setas); cartões **Prêmio, Comissões, Documentos**, ano anterior × atual dia a dia; o tooltip mostra os dois valores ("Dia 22/julho", `image 23`) |
| **Busca › Apólices** | `image 24`, `25` | toggle **"Apenas vigentes"**; cartão com ramo, Apólice, **"(COM SINISTRO)"** + alerta, Seguradora, Vigência, **"Item 1 de 1"** (veículo + placa), Telefone (com tipo: pessoal/residencial/comercial), Email; bloco **"Situação de cancelamento: Apólice cancelada"** (`image 25`) |
| **Apólice › Documento** | `26`, `31`, `36` | **Filial, Nosso número, Fone, Email, Seguradora, Vigência, Apólice, Proposta, Prêmio líquido, Comissão % (R$), Acompanhamento, Sinistralidade, Observações**; link CLIENTE; faixa **"APÓLICE CANCELADA"**; card **Endossos** (título, **Tipo "X - ENDOSSO CANCELAMENTO DE APÓLICE"**, Vigência Inicial, link ENDOSSO). Valores de **Acompanhamento** vistos: "Emitido e não recebido" (`26`), "Recebido e não entregue ao cliente" (`31`, `36`), "Pendente de emissão - prazo normal" (`37`). **Sinistralidade**: "APÓLICE SEM SINISTRO" (`26`) · "1 SINISTRO (1 PROCESSO) • 1 EM ANDAMENTO 1 ATENDIMENTO" (`31`) |
| **Endosso** (tela roxa) | `37`, `38` | as mesmas 5 abas; o endosso tem **nosso número próprio** (96072) e vigência própria; "Sem parcelas." (`38`) |
| **Apólice › Parcelas** | `27`, `32`, `39` | Parcela n · **Forma de pagamento** (Cartão de Crédito / Boleto Bancário) · Dt. Vencimento · Valor Vencimento · **Dt. Quitação · Valor Quitação**. Na apólice cancelada (`39`): todas as parcelas com quitação 19/05/2025 e **valor 0,00** (baixa por cancelamento) |
| **Apólice › Produtores** | `28`, `33`, `40` | ver §4 |
| **Apólice › Itens** | `29`, `34`, `41` | FIPE, Veículo, Zero Km, Ano, Placa, Chassi, Renavam, Passag., Cor, Combustível, Categoria · **Dados do Seguro**: Código Interno (CI), Cobertura, Franquia, Classe Bônus, Valor de Mercado, Observações · **Garantias** (nome + LMI + Franquia, por exemplo CASCO, RCF, APP, VIDROS, CARRO RESERVA 15 DIAS, ASSISTÊNCIA 24HS) · toggle **"Atualizados"** → "ITEM ATUALIZADO 1" (o item depois de endosso, `41`) |
| **Apólice › Anexos** | `30`, `35`, `42` | lista de **PDFs** ("PROPOSTA …", "APÓLICE_…_1", "OUTRO_2") |
| **Busca › Clientes** (tela amarela) | `43` | cartão com tipo de pessoa (ícone pessoa/maleta), telefone com tipo, e-mail |
| **Cliente** | `44`, `45` | abas **Cliente · Contatos · Documentos · Anexos**; Cód., Dt. Nascimento (idade), Sexo, Estado Civil, Escolaridade, vários **Telefones (padrão)**, Email 1 (padrão), Observações; **Documentação**: Pessoa, CPF, RG (número, órgão), **Habilitação** (CNH, Categoria, Vencimento, 1ª Habilitação); **vários Endereços Residenciais** com "Ver no mapa / Traçar rota"; Documentos **Vigentes / Não Vigentes**, com histórico desde 2012 (`45`) |
| **Renovações** | `46` | ver §3 |
| **Seguradoras** | `47`–`49` | por cia: **Telefone 1, Telefone 2, Telefone Assist. 24h, Observações** (o modal "olho" abre texto livre com contatos de sinistro, vidros, comercial e cobrança, `49`) |

---

## 3. RENOVAÇÕES — como a tela filtra
**FATO (CorpNow, `image 46`):** o **único filtro é o mês** (setas ←/→ em "Jul/2025"). Cada linha mostra **nome do segurado, seguradora, "Vigência: dd/mm/aaaa"** (o fim de vigência), **ramo (AUTO + ícone)** e o alerta **"Apólice com sinistro"**. **Não há** filtro de ramo, produtor, situação ou filial, e **não há** coluna de status de renovação. O `.md` confirma: "filtro apenas por mês"; o clique abre a apólice.

**FATO (CORP clássico):**
- Relatórios **Documentos › Renovações**, **Documentos › Não Renovados** e **Gerenciais › Propostas › Análise de Renovações** existem (`image 5`, `6`). Os filtros desses relatórios **não foram printados**; o que aparece é o de "Solicitação de Emissão": Seguradora, Filial, Canal de Vendas, Ramo, Empresa, Cliente, Agente, Grupo de Produtores, Comissão Direta/Indireta, Período, Data (Início de Vigência), Situação da Proposta, Tipo de Documento. INFERÊNCIA: os de renovação provavelmente usam a mesma moldura de filtros comuns.
- Os gráficos separam **Novos × Renovações × Faturas × Endossos** em valor e quantidade, inclusive por produtor (`image 7`–`14`). Então o sistema **classifica cada documento** como novo ou renovação.
- O multicálculo marca **"Esta é uma renovação"** e guarda a apólice anterior, a seguradora anterior, o CI, a quantidade de sinistros e o bônus (`image 21`).
- A Central de Negócios tem fila **por usuário** (combo "[usuário do Founder]"), Temperatura, Status, Campanha, Tipo e "Próxima Ação" com período (`image 3`). INFERÊNCIA: é aqui que uma renovação vira oportunidade trabalhada; o combo **Tipo** pode ter "Renovação", mas **não foi aberto** no print.

**NÃO VISTO em nenhum print:** campos com os nomes `renovacao_situacao` ou `situacao_multi`, e uma fila de renovação **por produtor**. A "situação" que a tela mostra é o **ícone colorido** na coluna Situação da busca de documentos (`image 2`), sem legenda.

**Conceitos que a API pode não expor:** "Não Renovados" (renovação perdida), "Análise de Renovações", a classificação Novo/Renovação/Fatura/Endosso, e a oportunidade com temperatura, status, campanha e próxima ação.

## 4. PRODUTORES / REPASSE
**FATO (CorpNow, aba Produtores — `image 28`, `33`, `40`):** cada produtor do documento é um cartão:
`<NOME> - <PAPEL>` · **Agente** (AUTO FLEET) · **Participação** (100,00 %) · **"Repasse sobre custo de apólice" X % (R$ Y)**.
- Papéis escritos **dentro do nome**: **EXECUTIVO, INDICADOR, FECHADOR(A)** (`image 28`, `33`, `40`).
- 📊 O R$ é **X % da COMISSÃO**, não do prêmio, apesar do rótulo dizer "custo de apólice". Conferido: 35 % × R$ 1.003,63 = **351,27** (`image 28` × `26`); 5 % × 752,65 = **37,63**; 3 % × 752,65 = **22,58** (`image 33` × `31`).
- Um mesmo documento soma vários repasses: `image 28` = 35 + 5 + 3 + 5 + 7 = **55 %** da comissão.
- Um parceiro (concessionária) aparece como produtor **sem linha de repasse** (`image 40`); outro tem 35 % (`image 28`).
- **A mesma pessoa aparece como DOIS cadastros de produtor**, um por papel: "L.G. - EXECUTIVO" e "L.G.A. - INDICADOR" no mesmo documento (`image 33`); "K. - FECHADORA" e "K. - INDICADOR" (`image 28`).

**FATO (CORP clássico, ranking — `image 9`–`14`):** os produtores aparecem como `<código>-<nome> <papel> <líder>`, por exemplo "247-M. CONSULTORA GUIGA", "248-M. CONSULTORA RAFA", "126-M. RAFA FECHADORA", "127-M. GUIGA FECHADORA", "17-L.G.A. – FECHADOR", "13-R.L.S. – FECHADOR", "155-SEG SUL SEGUROS".
**INFERÊNCIA (85):** o cadastro de produtor do InfoCap é **um código por (pessoa × papel × equipe/líder)**. Papel e equipe **não são campos**: estão escritos no nome. Para montar uma "fila do comercial X", o produto precisa **agrupar códigos por pessoa** a partir do nome ou de um de-para por corretora, guardado no banco por `company_id` (CLAUDE.md §13.9), nunca fixo no código.

**Caixa "Ind." (indireto): NÃO aparece em nenhum print.** O mais próximo é o filtro **"Comissão: Direta / Indireta"** (travado) dos relatórios (`image 5`, `6`), junto com **Agente** e **Grupo de Produtores**.

**Vínculo produtor ↔ usuário do sistema: NÃO visto.** Há o usuário "[usuário do Founder]" (login, "Matr - [usuário do Founder]") e o produtor "13-R.L.S. – FECHADOR", mas nenhuma tela liga os dois. Os filtros usam **usuário** na Central de Negócios (`image 3`) e **produtor/agente/grupo** nos relatórios (`image 5`): são entidades separadas. A coluna "Usuário" do INCORP (`image 15`) é quem fez a importação.

## 5. O que o dashboard mostra e NÃO tem rota óbvia na API
Rotas conhecidas: /login /cliente_cpf /lista_clientes /cliente_ligacoes /documentos /documento /documentos_bi /renovacoes /prod_docs /produtores /agentes /itens /cotacoes /atendimentos /seguradoras /ramos /negocio /negocios_andamento /cliente. O mapa do repositório (`backend/app/data/global_knowledge/infocap-corpapi-mapa.md`) lista como **NEGADAS no perfil padrão**: /parcelas, /comissao, /comissoes, /financeiro, /titulos, /contas_receber, /contas_pagar, /fluxo_caixa, /faturamento, /vendedores, /usuarios, /propostas, /sinistro, /endossos, /tarefas, /agenda, /cias, /filiais.

| no dashboard | print | rota provável | situação |
|---|---|---|---|
| **Anexos/PDF** da apólice e do cliente | `30`, `35`, `42`, `44` | nenhuma | **sem rota conhecida** |
| **Endossos** ligados à apólice (tipo, título, vigência, nº próprio) | `36`–`38` | /endossos (**negada**) | parcial: o /documento pode trazer o endosso como outro nosnum |
| **Sinistralidade** e lista de sinistros (Pendentes/Em andamento/Encerrados, nº sinistro, ocorrência, aviso, terceiro) | `4`, `31`, `24` | /sinistro (**negada**); `sin_situacao` em /cliente_ligacoes | parcial: só a situação |
| **Acompanhamento** do documento ("Emitido e não recebido"…) | `26`, `31`, `37` | ? | **não mapeado** |
| **Quitação** de parcela (data e valor pagos) | `27`, `32`, `39` | /documento (parcelas) · /parcelas (**negada**) | conferir se o /documento traz a quitação |
| **Repasse por produtor no documento** (% e R$) | `28`, `33`, `40` | **/prod_docs** é a candidata | conferir se traz papel e % |
| **Garantias** (LMI/franquia), Classe Bônus, CI, item **atualizado** | `29`, `34`, `41` | /itens | conferir garantias e "atualizado" |
| **Oportunidades** (temperatura, status, campanha, próxima ação, funil) | `3` | /negocio, /negocios_andamento, /cotacoes | parcial; "Oportunidades" ≠ "Negociações" |
| **Meta** de produção ("0 % atingida") | `7`–`14` | nenhuma | sem rota |
| Classificação **Novo/Renovação/Fatura/Endosso** e rankings | `7`–`14` | /documentos_bi? | conferir |
| **INCORP** (importação de propostas e comissões das seguradoras) | `15` | /comissoes (**negada**) | sem rota |
| **Fluxo de caixa**, comissões recebidas/pendentes/repasse | `5`, `16` | **negadas** | — |
| Relatórios **Não Renovados** e **Análise de Renovações** | `5`, `6` | /renovacoes (só o calendário?) | conferir |
| Cliente: RG, **CNH (venc.)**, escolaridade, vários endereços, contatos, dados bancários, observações, perfil | `1`, `44` | /cliente, /cliente_cpf | parcial |
| Seguradora: telefones, assistência 24h, **observações** (contatos de sinistro/cobrança) | `47`–`49` | /seguradoras (61 códigos) | conferir se traz contatos e observações |
| **Usuários, permissões de perfil, filiais, empresa** | `5`, `3` | /usuarios, /filiais (**negadas**) | sem acesso |

## 6. Indícios de BLOQUEIO ou ESCOPO
- **Filial travada:** o filtro "Filial: MATR" fica **cinza/desabilitado** nos relatórios (`image 5`, `6`). INFERÊNCIA: a base tem uma filial só, ou o perfil do usuário está preso a ela.
- **Multiempresa existe no modelo:** o filtro **"Empresa: Todas" (cinza)** nos relatórios (`image 5`, `6`) e a coluna **"Empresa"** no cadastro de clientes (`image.png`, `1`). INFERÊNCIA: é o mesmo conceito que o `email_multi` do login da API (uma conta com acesso a mais de uma empresa). **Nenhuma tela mostra um seletor de empresa.**
- **Comissão Direta/Indireta cinza** (`image 5`): bloqueada por perfil ou só sem uso.
- **Central de Negócios por usuário:** combo "[usuário do Founder]" (`image 3`); pode limitar a visão ao próprio usuário.
- **Janelas padrão que escondem dado:** a busca de sinistro abre em **"Últimos 180 dias"** (`image 4`); a busca de documentos esconde **documentos antigos** a não ser que se marque a caixa (`image 2`); o CorpNow tem **"Apenas vigentes"** (`image 24`, `45`). 🔴 RECOMENDAÇÃO: conferir se as rotas /documentos e /cliente_ligacoes da API têm o mesmo corte padrão. Uma contagem pela API pode estar **truncada pelo padrão**, como a conclusão errada sobre o condomínio da Resulta.
- **CorpNow:** ao lado do e-mail do usuário há um **ícone de seta circular** (`image 22`–`49`). INFERÊNCIA: é "sair" ou **"trocar empresa/conta"**. Vale clicar com o F12 aberto (§7).
- Usuário logado em dois sistemas ao mesmo tempo, no mesmo navegador, com abas "Corp" e "Resu…" (`image 23`): o Founder trabalha nas duas bases lado a lado, e é fácil cadastrar a conexão com o login trocado.

## 7. RECOMENDAÇÃO — o que o Founder deve capturar no navegador
**Primeiro, um FATO de arquitetura (INFERÊNCIA 80):** o CORP clássico roda em `…ddns.net/software/html5.html`. Parece um **programa de desktop transmitido para o navegador**: menus estilo Windows, botões Inserir/Excluir/Salvar e janelas MDI (`image.png`). Num HAR dele devem aparecer **frames de WebSocket de desenho de tela**, não JSON de dados. Valor baixo. O **CorpNow** (`corpnow.com.br/#/…`) é um app web de página única com rotas `#/` e chama um backend por XHR/fetch: **é aqui que o HAR rende.**

**Passo a passo (CorpNow, logado com o usuário da RESULTA):**
1. Chrome → F12 → aba **Network** → marcar **Preserve log** e **Disable cache** → filtro **Fetch/XHR** (depois repetir com **WS**, para ver se há WebSocket).
2. Fazer **logout** e **login de novo** (para pegar o `POST` de login: token, `email_multi`, lista de empresas, `codfil`, permissões).
3. Clicar no **ícone de seta circular** ao lado do e-mail (é troca de empresa?).
4. **Produção** → avançar e voltar um mês.
5. **Renovações** → mês atual → avançar 2 meses.
6. **Busca › Apólices**: digitar "COND" e depois "RESI", com e sem **"Apenas vigentes"**.
7. Abrir **uma apólice de condomínio** → abas **Documento, Parcelas, Produtores, Itens, Anexos** → **clicar num PDF** (ver a URL de download e se ela pede token).
8. Abrir uma apólice **COM SINISTRO** e uma **cancelada com endosso** → clicar no card do **Endosso**.
9. **Busca › Clientes** → abrir um cliente → **Contatos, Documentos, Anexos**.
10. **Seguradoras** → clicar no olho de uma.
11. Repetir o passo 7 com o **login da AutoFleet** (só a abertura de uma apólice), para comparar o código `DOCUMENTOS_<código>_1_…`.
12. Botão direito na lista → **"Save all as HAR with content"**.

**O que procurar nas requisições:**
- **Host:** é `api.corpnuvem.com` ou outro backend (por exemplo `api.corpnow…`)? Se for outro, ele pode ter rotas que o nosso perfil de API não tem.
- **Caminhos e parâmetros:** rotas de anexo, endosso, sinistro, renovação e "acompanhamento"; se aparecem `codfil` e o código da base (`2024090009` na AutoFleet).
- **Cabeçalhos:** `Authorization`, algum `x-empresa`/`empresa`/`multi`; se o token é o mesmo tipo do `/login` da API.
- **Respostas:** campos `situacao`, `acompanhamento`, `sinistralidade`, `renovacao_situacao`, papel do produtor e % de repasse; se as listas vêm **paginadas ou cortadas** (vigentes, 180 dias).

⚠️ **O HAR leva token e dados pessoais.** Não pode entrar no git. Salvar fora do repositório (ou em `docs/intake/`, que já está no `.gitignore`), não colar em chat e trocar a senha depois, se for o caso.

**Necessário ou útil?**
- **ÚTIL — nota 72/100 para fazer agora.** A API já responde o essencial (clientes, documentos, itens, renovações, produtores).
- **Passa a NECESSÁRIO (nota 90)** se a próxima SPEC precisar de **PDF da apólice, endossos, sinistralidade, acompanhamento ou meta**: nenhum deles tem rota conhecida, e o HAR do CorpNow é o caminho mais barato para descobrir se existe uma.
- **HAR do CORP clássico: nota 25** (deve mostrar só pintura de tela). Fazer só um minuto, para confirmar o transporte.
- **Mais barato que o HAR, e decisivo (nota 85):** um print do **combo "Tipo" aberto** na Central de Negócios, e o **relatório "Renovações" e "Não Renovados" com os filtros visíveis**, no CORP clássico da Resulta. Isso responde a pergunta 3 sem engenharia reversa.

## 8. Fora do escopo, mas importante
1. **nosnum se repete entre as bases** (§1.3): risco de cruzar corretoras se alguma chave usar só o nosnum. Relevante para CLAUDE.md §7.
   **FATO (código):** a chave técnica de apólice é `sha256("infocap:<codfil>:<nosnum>")[:24]` (`backend/app/services/policy_facts.py:90` `_locator_hash`; usada por `backend/app/services/policy_context.py:298` `chave_da_apolice`). O locator aceito pelo conector é `infocap:<codfil>:<nosnum>` (`backend/app/api/infocap_connector.py:582,593`). **Nem company_id nem a conexão entram no hash**, e `codfil=1` é igual nas duas bases.
   **ELO NÃO MEDIDO:** não verifiquei se toda tabela ou cache que guarda essa chave também filtra por `company_id`. Se filtrar, não há vazamento; se algum lugar procurar só pela chave, duas apólices de corretoras diferentes colidem. **RECOMENDAÇÃO:** o gerente confere com `grep -rn "policy_locator_hash\|chave_da_apolice" backend/app` e com as consultas que leem essa chave.
2. **A Resulta tinha AUTO em 06/2025** (3,8 % do prêmio): a regra "Resulta = não-auto" pode ter exceções residuais; não usar o ramo como prova de base.
3. **Janelas padrão** (vigentes, 180 dias, "documentos antigos") podem truncar contagens: conferir o mesmo na API antes de concluir "não tem".
4. **O rótulo "Repasse sobre custo de apólice" mente**: o % incide sobre a **comissão** (📊 três contas batem). Se o produto copiar o rótulo, vai copiar o erro (CLAUDE.md §12.1).
5. Os prints da pasta têm muita PII de clientes; a pasta está fora do git (`.gitignore:113`), e assim deve continuar.
