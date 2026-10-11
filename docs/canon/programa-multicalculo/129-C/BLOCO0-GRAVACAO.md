# BLOCO 0 · SPEC-129-C · B0-c — a gravação dos negócios de Condomínio, Residencial e Empresarial

> Investigador B0-c (Opus 5.5), 11/10/2026. Repositório intocado (branch `spec/129-C-mais-ramos`, nada escrito nele).
> Sem senha e sem dado pessoal neste laudo. Fixtures: `scratchpad/b0c-129c/gravacao_{condominio,residencial,empresarial}_{1,2,3}.json`.
> Agregado pedido pelo gerente: `scratchpad/b0c-129c/AGREGADO-POR-RAMO.md` (+ `agregado.json`, `agregado2.json`).

## 0. Como foi lido (rota A do B0-a)
| | |
|---|---|
| login | de PESSOA (autorizado pelo Founder), pela tela; senha só no ambiente do processo e apagada dele logo após o login. 📊 entrou em 32,1 s, **sem aviso de sessão ativa** |
| guarda | `agger_guarda` de produção + embrulho: toda escrita fora de `usuario/login`, `login/pdocs`, `deslogaSessao` barrada; **qualquer URL com calcular/salvar/excluir/delet barrada até em GET** |
| leitura | nenhuma navegação nem clique: `fetch` GET dentro da página com o token que o app já tinha (`Sessao.avaliar`), nos MESMOS endpoints que a tela usa ao abrir um negócio (bundle do app: `getCalculos` = `GET pdocs calculo/cotacao/versoes/{idIntegracao}`; depois `GET pdocs calculo/cotacao/calculos/{idIntegracao}/{versao}`); lista por `GET pdocs calculo/negocio/busca/v2?ramos=<16|2|18>&periodo=730` |
| saneamento | o cru viveu só na memória do processo; credenciais redigidas DENTRO da página (`coletarSegredos/redigirSegredos` do montador + chave secreta → `<redacted:credencial>`); em Python, pseudônimos por chave (`<doc#n>`, `<nome#n>`, `<endereco#n>`, `<cep#n>`, `<fone#n>`, `<email#n>`, `<usuario#n>`, `<id#n>`), config de seguradora (códigos de corretor, sucursal, matrícula, conta, susep, login) → `<redacted:config>`, PDF → `<removido:pdf>`, crivo de nome em texto livre; formato original dos campos trocados em `_formato_dos_campos_trocados` (ex. `##############`, `#####-###`) |
| relógio | 01:05:41 → 01:24:55. 📊 `calcularV2` = **0** · trocas de token (`pdocs`) = **2** · ~221 GETs · barradas = 30, todas telemetria (Google/Clarity/Refiner) · logout pela tela **True** |

## 1. Quantos negócios foram lidos
📊 **15 por ramo** (10 mais recentes, 3–27 dias; 5 de 367–417 dias) com todas as versões e a resposta + pares de renovação
(📊 41 condomínio, 7 empresarial, 2 residencial) + as versões de 13 negócios com 2+ versões. Gravações completas saneadas:
**3 por ramo** (2 recentes + 1 antigo, as com mais seguradoras com preço: cond 5/7 · 5/6 · 6/8; resid 8/8 · 8/8 · 9/10; empr 7/8 · 5/9 · 7/11).
⚠️ Os antigos foram **migrados** ao Aggilizador novo em 03/09/2026: o item deles tem 26 chaves (sem config da seguradora),
vigência sem `.000Z` e o erro "não foi migrada para o novo aggilizador" — servem para preço/coberturas, **não** como modelo de corpo.

## 2. Respostas por ramo
**A versão gravada (`versoes/{ref}`) = o corpo do `calcularV2` + o que o servidor acrescenta.** Mesmo envelope nos três ramos:
`ramo` (16 | 2 | 18) · `tipo` 5 · `tipoSeguro` 1 · `origem` 1 · `segurado` · `configuracoes` · `calculos[]` · `vigenciaIni/Fim` ·
`renovacao` · `bonusAnterior` · `sinistrosAnterior` · `seguradoraAnteriorId` · `numeroRenovacao` · `vigFimAnterior` + campos do
servidor (`id`, `idIntegracao`, `negocioId`, `versao`, `correlationId`, `customer*`, `usuarioId`, `results.{main,alternatives,all,porAssinatura,ofertaCruzada}.{errors,successes}` vazios, `calculosEnviados/Recebidos`…). **Sem** `automoveis`/`tpCobertura`/`CI`.

| pergunta | Condomínio (16) | Residencial (2) | Empresarial (18) |
|---|---|---|---|
| chaves do item de `calculos[]` (recentes) | 📊 **100** em comum: config da seguradora (`seguradora`, `nome`, `nomeSeguradora`, `seguradoraTxt`, `ativo`, `selected`, `tipoConfig`, `credenciaisValidas`, `code…eighthCode`, `bradesco*`, `hdi*`, `tokio*`, `allianz*`, `liberty*`, `portoSusep`, `susep`, `loginWs`, `senhaWs`…) + **todos** os `percComissao*`/`percDesconto*`/`percAgenciamento*` + `percComissao2/3` + resultado gravado (`premio`, `premioMensal`, `valorFranquia`, `resultados`, `erros`, `alertas`, `retorno`, `retornoErro`, `tempoResposta`, `executionGuid`, `dtCalculo`…) | 📊 **105** (as do condomínio + `mapfre*`, `libertyCodigoCorretor/Filial/Filiais/Corretores/CpfCnpj/TokenEretorno`) | 📊 **102** + **`valoresAjusteSeguradora`** |
| coberturas no item? | **não** — nenhuma chave de cobertura no item (confirma o B0-a): tudo em `cotacao.configuracoes` | idem | idem |
| comissão efetiva | 📊 vai em **`percComissao`** do item (20 · 22 · 25 · 30 · 35) e volta em `resultados[].coberturas.percComissao`; `percComissaoCond` fica 10 (o padrão da config) | `percComissao` 10–30; `percComissaoResid` 10 | `percComissao` 10–50; `percComissaoEmpres` = 0 em todas — **não é a comissão usada** |
| vigência | `vigenciaIni/Fim/vigFimAnterior` ISO UTC com ms: 📊 `2026-10-31T17:47:20.353Z` (recentes; ⚠️ as 4 recentes olhadas têm a MESMA hora `17:47:20.353Z` em dias diferentes — 💭 hora herdada pelo app, irrelevante para o servidor); migrados `2025-09-23T00:00:00`; às vezes `vigenciaIniTxt` `dd/mm/aaaa` | idem | idem |
| equipamentos | **códigos** em `configuracoes.sisProtecaoIncendRoubo` (📊 `[1]` 10 · `[1,7]` 4 · `[1,2,7]` 1 — Extintores 1, Hidrantes 2, CFTV 7) | **booleanos** `imovelPossuiAlarme/AlarmeMonitorado/CercaEletrica/CircuitoFechado/Grades/PorteiroEletronico/Vigilancia24hs`; `sisProtecaoIncendRoubo` null | booleanos `imovelPossuiExtintor/Hidrante/Sprinkler/DetectorFumaca/BrigadaIncendio/…`; `sisProtecaoIncendRoubo` null |
| bem | `imovelAtividade` (1 Residencial em 12/15), `ocupacao`, `estruturaCondominio` 1, `qtdBlocos`, `pavimentos`, `qtdElevadores` (⚠️ às vezes **texto** "2"/"15"), `anoFundacao` (texto), `areaConstruida`, `qtdFuncionarios`, `condominio` (= RC condomínio), `modalidade` | `imovelTipoResidencia` 1/3, `imovelUso` 1/2, `imovelConstrucao` 1/4/3, `imovelObjetoSegurado` 3, `seguradoProprietario`, `zonaRural`, `areaRisco` | `cnae` (texto, 7 dígitos), `imovelConstrucao`, `imovelPavimentacao` "0"/"2" (texto), `imovelLocalEstabelecimento` "0", `anoConstrucao`, `imovelObjetoSegurado`, `isGuardaVeiculo {valor, vagas, franquia}` |
| atividade | — | — | **por seguradora**: `calculos[].valoresAjusteSeguradora.imovelAtividadeProfissionalLocal = {Key, Value, Description: null}` — 📊 ex. Bradesco `{"Key":"1,1.8.711","Value":"700.11 - Consultório ou clínica de estética"}`, Porto `{"Key":"230","Value":"CABELEIREIROS, SALAO DE BELEZA E/OU ESTETICA"}`, Tokio `{"Key":"2344","Value":"ESCRITORIOS"}`, Chubb `{"Key":"38,74,3",…}`, HDI `{"Key":"700160",…}` |
| segurado | `tipoPessoa` J (15/15); leva **endereço do segurado** (`cep`, `logradouro`, `numero`, `bairro`, `cidade`, `uf`) além do endereço do risco em `configuracoes.imovel*` | `tipoPessoa` F; `resid*`, `dataNasc`, `sexo`, `estadoCivil` | J 14 / F 1; `cnae` também no segurado |
| `resultados[]` | 📊 **1 resultado por item** (94/94); chaves: `premio`, `premioMensal`, `parcelamentos[{parcelas, premioPrimeiraParc, premioDemaisParc, tipoPag, valorIof}]`, `franquia`, `franquias`, `identificacao`, `packageType` (0/null), `principal`, `selected`, `nroCalculo`, `codigoIdentificacaoSeg`, `renovacaoGarantida`, `erros`, `alertas`, `observacoes`, `pathPdf`, `pdfFileNameAgger`, `coberturas{…}` | idem (129/129) | idem (121/121) |
| coberturas na resposta | `resultados[].coberturas` com as chaves de RE ecoadas (`isDanosIncendioRaioExplosao`, `…Cond`, `isValorSindico`, `isValorCondominio`, `rouboCondomino`, `garagista*`, `assist24hs` **como texto do plano** — "Assist. 24 Horas Condominio Superior" —, `valorDeNovo` "Sim"/"Não"/1, `imovelObjetoSegurado` texto, `coberturaCompartilhada` "18,22,28\|19,13", `percComissao`) | idem com `isDanosEquipamentosEletronicos`, `recomposicaoDocumentos`… | idem com `lucroCessante`, `rouboFurtoDeValores`, `isGuardaVeiculo`… |
| franquia | 📊 **0 em todas** (`resultados[].franquia` 94/94 e `valorFranquia` do item 94/94) | 0 em 129/129 | 0 em 121/121 |
| nome do pacote | `identificacao`: "Principal" na maioria; Porto "PLANO BRONZE/OURO REDE REFERENCIADA…"; Bradesco "Bradesco Condominio" | Allianz "Personalizado", Liberty "Pacote Intermediário/Básica", Porto "PLANO ESSENCIAL GRATUITO…" | Porto "Porto Empresa", Bradesco/Zurich/Alfa "… Empresa" |
| item sem `resultados` com prêmio | 📊 0 | 0 | 0 |
| famílias de erro | ver AGREGADO §1: credencial, aceitação, **limite de cobertura (LMI/LMR)**, renovação/cadastro, migração | + construção (madeira/inferior), veraneio | + **atividade** (inválida/bloqueada/declinada), **comissão** (acima do máximo/faixa) |

**Diferenças em relação ao auto (o que a 129-C muda):** (1) cobertura em `configuracoes`, não no item (o `Object.assign(it, cob)` do
montador não serve); (2) a comissão vai em `percComissao` do item como no auto, mas o valor tem de vir do pedido/config DO RAMO
(`percComissaoEmpres`=0 na conta — mandar 0 seria a comissão real); (3) sem veículo/condutor/FIPE/placa; segurado PJ no condomínio e
com endereço; (4) empresarial carrega a atividade por seguradora no item; (5) resposta: 1 resultado por item, **franquia sempre 0**
(o leitor não precisa da `valorFranquia` de RE para nada hoje — 📊 344/344 zero), coberturas ecoadas com chaves de RE e a assistência
como **texto do plano**; (6) campos com tipo frouxo (`qtdElevadores`, `pavimentos`, `anoFundacao`, `imovelPavimentacao` texto ou número).

## 3. Varredura de dado pessoal (nas 9 fixtures + agregados + saídas + log, `b0c-129c/varrer.py`)
```
email 0 · cpf 0 · cnpj 0 · fone 0 · cep 0 · endereco_com_numero 0 · inteiro_11_ou_14_digitos 0 · "ellen|resultaseguros|Resulta@" 0
TOTAL = 0 em 24 arquivos
```

## 4. O que só um cálculo NOVO responde
1. **Quais chaves do item o cliente MANDA** — a versão gravada mistura o enviado com o que o servidor grava (resultado, `executionGuid`,
   `dtCalculo`…); o corpo exato do `calcularV2` de RE só aparece interceptando um POST (o "786/786" do auto não transfere).
2. Se o servidor aceita o corpo montado pelo robô no RE (e o recálculo por corpo = versão nova).
3. A conta do `cotador@`: as mesmas seguradoras dão preço com ela? (HDI "inválida" no teste guardado, mas com preço nos negócios recentes da pessoa.)
4. A comissão do empresarial que a conta manda por padrão (0 %) — e as recusas "comissão acima do máximo" por seguradora.
5. Atividade escolhida pelo robô (o `Key` por seguradora vem de `getOptionsBySegFull`, B0-a) — aceita ou "atividade inválida".
6. Validações do servidor do Agger (mínimos, tipos frouxos) — nos 45 lidos, toda recusa veio da seguradora, nenhuma do Agger.

## 5. Arquivos
`b0c-129c/gravacao_{condominio,residencial,empresarial}_{1,2,3}.json` (fixtures saneadas, parcelamentos cortados em 4) ·
`AGREGADO-POR-RAMO.md` · `agregado.json` · `agregado2.json` · `esquema.txt` (só caminhos de chave e tipos) · `servidor.py`
(sessão de leitura) · `analise.py` (saneador/agregador) · `varrer.py` (varredura) · `cmd/*.py|out` (comandos e saídas, sem dado pessoal).
