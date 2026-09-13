# RESEARCH-PACK · SPEC-EXTRA-001.10 — O portal de vidros de ponta a ponta

> Companheiro de [`SPEC-EXTRA-001.10-o-portal-de-vidros-de-ponta-a-ponta.md`](SPEC-EXTRA-001.10-o-portal-de-vidros-de-ponta-a-ponta.md).
> **Só o que a proposta cita.** Toda linha de código foi **reaberta e conferida em
> 13/09/2026** (HEAD `a0bb5fe`). Todo número traz o comando que o produziu (§0.4 do
> protocolo). ⛔ Nenhum dado pessoal aparece aqui: CPF, placa, chassi, telefone,
> e-mail e nome estão mascarados na origem, pelos leitores do §3.

---

## §1 · As linhas do código, conferidas hoje — e as que divergiram do diagnóstico

| afirmação | linha conferida | comando | divergiu? |
|---|---|---|---|
| o docstring documenta o PATCH e ninguém o executa | `vidros_apifirst.py:20-23` | `grep -n "PATCH\|solicitantes\|corretores" portal_worker/journeys/vidros_apifirst.py` → **3 linhas, todas no docstring** | não |
| `SessaoVidros` não tem `atualizar_atendimento` | `vidros_sessao.py:139-237` | `grep -n "atualizar_atendimento" portal_worker/journeys/vidros_sessao.py` → **0** | não |
| a journey salta do POST ao questionário | `vidros_apifirst.py:225` (`criar_atendimento`) → `:275-279` (`QZ.rodar_questionario`) | leitura da função `abrir_atendimento_api` da linha 146 até a 363 | não |
| a fronteira material é fixa | `vidros_estado.py:232-238` | `grep -n "FRONTEIRA_" portal_worker/journeys/vidros_estado.py` | não — o diagnóstico dizia `:233`, e é onde está `FRONTEIRA_MATERIALIZAR` |
| a categoria já é extraída da chave composta | `vidros_api.py:258-281` (`partes_do_item_coberto`, índice 6) | `grep -n "CATEGORIA_\|def partes_do_item_coberto" portal_worker/journeys/vidros_api.py` | não |
| o hardcode de 3 slugs, um deles `ITAU` | `vidros_apifirst.py:102-106` | `sed -n '100,110p' portal_worker/journeys/vidros_apifirst.py` | não |
| o segundo mapa de seguradoras | `portal_params.py:68-88` (`_INSURER_ALIASES`, `LIBERTY → "Yelum"` em `:70`) | `sed -n '66,90p' app/agents/tools/portal_params.py` | não |
| quem digita o nome no autocomplete | `vidros_lanternas.py:1090-1108` (`_select_insurer_start`, `inp.fill(insurer)`) | `sed -n '1085,1112p' portal_worker/journeys/vidros_lanternas.py` | não |
| a régua de 10 cm | `vidros_lanternas.py:331-333` (`_LIMITE_CM = 10.0`) | `grep -n "_LIMITE_CM" portal_worker/journeys/vidros_lanternas.py` | 🟡 diagnóstico dizia `:334`; é **331-333** |
| o robô não escolhe loja, e por quê | `adaptive.py:932-970` | `sed -n '925,970p' portal_worker/adaptive.py` | 🔴 **divergiu**: o diagnóstico e P-PILOTO-07 citam `adaptive.py:1152-1163`; hoje o bloco está em **932-970** |
| o link de vistoria que a Regina cola à mão | `adaptive.py:125-145` | `sed -n '125,145p' portal_worker/adaptive.py` | não |
| a `description` da tool pede tudo | `portal_tool.py:123-137` | `sed -n '120,140p' app/agents/tools/portal_tool.py` | 🟡 diagnóstico dizia `:130`; o parágrafo é **125-135** |
| `TRANSPORTAVEIS` tem 6 campos | `portal_params.py:43-60` · o gate em `:178` | `sed -n '43,60p' app/agents/tools/portal_params.py` | não |
| o prompt pede só 3 coisas | `prompts.py:133` | `grep -n "portal_action\*\* IMEDIATAMENTE" app/core/prompts.py` → **133** | não |
| famílias sem específicas mapeadas | `perguntas_do_portal_de_vidros.py:355` | `grep -n "PECAS_SEM_ESPECIFICAS_MAPEADAS" app/services/perguntas_do_portal_de_vidros.py` | não |
| `_UNIVERSAIS` e as específicas | `:199-276` e `:288-352` | `grep -n "_UNIVERSAIS\|_ESPECIFICAS_POR_IDENTIDADE" app/services/perguntas_do_portal_de_vidros.py` | não |
| o Vigia só vê `vidros_lanternas` | `vigia_do_portal.py:306` | `grep -n "portal_key" app/tasks/vigia_do_portal.py` | não |
| a sessão só fala JSON | `vidros_sessao.py:108-121` (`JSON.stringify`, `Content-Type: application/json`) | `sed -n '103,125p' portal_worker/journeys/vidros_sessao.py` | 🟡 diagnóstico dizia `:105-119`; é **108-121** |
| vistoria: campo conhecido, valor não | `vidros_api.py:345-370` | `sed -n '345,370p' portal_worker/journeys/vidros_api.py` | não |
| `TipoAtendimento` só na Porto | `vidros_api.py:220-248` | `sed -n '218,250p' portal_worker/journeys/vidros_api.py` | não |
| o mapa `RELACAO_TITULAR` com `6: Corretor` | `vidros_api.py:296-305` | `sed -n '294,307p' portal_worker/journeys/vidros_api.py` | não |

### 1.1 📊 Os endpoints declarados e nunca chamados

```bash
cd backend
for ep in $(grep -o '^EP_[A-Z_]*' portal_worker/journeys/vidros_api.py); do
  n=$(grep -rn "$ep" --include=*.py . | grep -v "vidros_api.py:" | wc -l)
  [ "$n" = "0" ] && echo "NUNCA CHAMADO: $ep"
done
```

📊 **Saída em 13/09/2026 — 9 nunca chamados**, mais 2 já marcados `_NAO_MEDIDO`:

```
EP_CORRETORES · EP_SOLICITANTES · EP_REGRAS_REPARO · EP_TIPOS_TELEFONE ·
EP_UFS · EP_CIDADES · EP_CLIENTES_CIDADES · EP_ABANDONAR · EP_CANCELAR
(+ EP_FINALIZAR_NAO_MEDIDO · EP_VISTORIA_MOBILE_NAO_MEDIDO)
```

🟡 **Divergência:** o diagnóstico §10.2 item 4 diz **8**. O medido hoje é **9** —
`EP_REGRAS_REPARO` não estava na lista dele, e ele aparece no HAR de 14/08.

---

## §2 · As medições do acervo — os comandos, e o que voltou

Os três leitores read-only ficaram em
`<scratchpad>/ler_har.py`, `ler_resp.py`, `fronteira.py`. **Eles mascaram PII por
regex de nome de chave antes de imprimir** e nada foi copiado para o repositório.
⚠️ O executor que os reescrever deve mascarar também a chave `Documento` do
`PUT /atendimentos/corretores` — **ela é um CPF** e o nome não o denuncia.

### 2.1 🔴 O ELO: quando nasce o `CodigoAtendimento`

```bash
python - <<'PY'   # imprime só método, path e o campo CodigoAtendimento
# percorre entries, filtra path == /atendimentos ou /questionarios*, e imprime
# d.get("CodigoAtendimento") da resposta
PY
```

📊 **Saída, 13/09/2026, sobre os dois HAR da Yelum:**

```
#### LATARIA (CodigoItemCoberto "1|142|S|11335|1|0|L")
 111 POST   /atendimentos            -> 200   CodigoAtendimento=<chave ausente>
 119 GET    /atendimentos            -> 200   CodigoAtendimento=None
 156 GET    /atendimentos            -> 200   CodigoAtendimento=None
 204 PATCH  /atendimentos            -> 200   CodigoAtendimento=<chave ausente>
 213 GET    /atendimentos            -> 200   CodigoAtendimento=23232316   ← NASCEU
 249 GET    /atendimentos            -> 200   CodigoAtendimento=23232316
(zero POST /questionarios em toda a captura)

#### VIDRACARIA (CodigoItemCoberto "3|129|N|10700|1|0|V")   ← A LINHA DE CONTROLE
 129 POST   /atendimentos            -> 200   CodigoAtendimento=<chave ausente>
 136 GET    /atendimentos            -> 200   CodigoAtendimento=None
 173 GET    /atendimentos            -> 200   CodigoAtendimento=None
 229 PATCH  /atendimentos            -> 200   CodigoAtendimento=<chave ausente>
 234 GET    /atendimentos            -> 200   CodigoAtendimento=None        ← NÃO nasceu
 241 POST   /questionarios/perguntas -> 200
 253 POST   /questionarios/perguntas -> 200
 256 POST   /questionarios/perguntas -> 200
 258 POST   /questionarios/perguntas -> 204   (fim do questionário)
 265 POST   /questionarios/regras-reparo -> 200
 268 POST   /questionarios          -> 200
 271 GET    /atendimentos            -> 200   CodigoAtendimento=23087562   ← NASCEU
```

🔴 **Por que isto é uma causa e não uma coincidência (protocolo §0.3):** medi A (o
número nasce depois do PATCH, na lataria), medi B (o número **não** nasce depois do
PATCH, na vidraçaria), e medi que B **chega** em A — o mesmo `GET /atendimentos`,
imediatamente após o mesmo PATCH, dá resultado **oposto**, e a única coisa que muda
entre as duas capturas é a **categoria** do `CodigoItemCoberto`. A vidraçaria é a
linha de controle da lataria (CLAUDE.md §9.2).

### 2.2 As 7 escritas da lataria (HAR Yelum 1, 09/09/2026)

📊 Ordem real, só `POST`/`PUT`/`PATCH` a `api.autoglass.com.br`, sem `OPTIONS`:

```
1  POST  /atendimentos                     {Seguradora:"LIBERTY", NumeroDaApolice, DataSinistro,
                                            PlacaInformada, SufixoChassi:null, CpfCnpjSegurado,
                                            TipoAtendimento:null}
2  PUT   /atendimentos/corretores           {"Documento": "<CPF/CNPJ — 11 chars>"}
3  POST  /solicitantes                      {RelacaoTitular:"6", EmailSegurado, EmailTitularAplice,
                                            NomeSolicitante, CpfCnpjSolicitante, EmailCorretor:true,
                                            Telefones, TermoExibido:true, TermoAceito:false}
4  PATCH /atendimentos                      ← ver §2.3
5  POST  /atendimentos/{codigo}/vistorias-previas/processar   {"params":{}}
6  POST  /corretores-reclamacoes            {Atendimento, NomeCompleto, Cpf, Telefones, Email}
7  POST  /atendimentos/emitir-atendimento-formalizado/{codigo}      ← O COMPROVANTE
```

⚠️ **`lab har` conta 14 escritas.** São estas **7 + os 7 `OPTIONS` de preflight CORS**
que o browser dispara antes de cada uma. O gate G1 compara **as 7**.

### 2.3 🔴 O corpo do PATCH: 11 no contrato, 8 no fio

📊 **O contrato**, lido da função `atualizarAtendimento` do bundle:

```bash
grep -o '.\{0,60\}atualizarAtendimento.\{0,900\}' \
  "docs/intake/materiais/portal-vidros/YELUM/YELUM 1/AMANDOS 1_files/app-231e920f7d.min.js.baixados"
```

```js
atualizarAtendimento: function(o, t) { return e.patch(a + "atendimentos", {
  CodigoItemCoberto:         o.passo3.dados.QualItemDanificado.CodigoItemCoberto,
  ItemRemovido:              o.passo3.dados.ItemPermaneceVeiculo,
  EventoComposto:            o.passo3.dados.MaisDeUmItemDanificado,
  CodigoCidade:              o.passo3.dados.CidadeRealizacaoServico.Codigo,
  CodigoZona:                null != o.passo3.dados.ZonaRealizacaoServico
                               ? o.passo3.dados.ZonaRealizacaoServico.Codigo : null,
  CodigoObjetoCausa:         o.passo3.dados.ComoOcorreuDanoVeiculo.CodigoObjetoCausa,
  AvaliacaoDano:             o.passo3.dados.DetalhesSobreDanoAoVeiculo,
  PerimetroDano:             o.passo3.dados.OndeOcorreuDano,
  PolimentoFarol:            o.passo3.dados.PolidorFarol,
  Cep:                       o.passo3.dados.Cep,
  ServicosMartelinhoLataria: (t||[]).map(function(o){
                               return {CodigoServico: o.servico.Codigo,
                                       CodigoObjetoCausa: o.objetoCausa.Id}})
})}
```

📊 **O que saiu no fio, 2 de 2 capturas — 8 chaves:**

```
LATARIA     {"CodigoItemCoberto":"1|142|S|11335|1|0|L", "CodigoCidade":8350,
             "CodigoZona":null, "CodigoObjetoCausa":10, "AvaliacaoDano":"COLISAO…",
             "PerimetroDano":"U", "Cep":"<8c>",
             "ServicosMartelinhoLataria":[{"CodigoServico":26,"CodigoObjetoCausa":10},
                                          {"CodigoServico":15,"CodigoObjetoCausa":10}]}
VIDRAÇARIA  {"CodigoItemCoberto":"3|129|N|10700|1|0|V", "CodigoCidade":8214,
             "CodigoZona":null, "CodigoObjetoCausa":17, "AvaliacaoDano":"<68c>",
             "PerimetroDano":"U", "Cep":"<8c>", "ServicosMartelinhoLataria":[]}
```

🔴 **INFERÊNCIA (declarada como tal, e testável):** `ItemRemovido`, `EventoComposto`
e `PolimentoFarol` somem porque o AngularJS serializa com `JSON.stringify`, que
**descarta chaves `undefined`** — e as três leem `passo3.dados.X` sem ternário.
`CodigoZona` sobrevive porque o bundle a escreve com um ternário explícito para
`null`. **FATO:** em 2 de 2 capturas o corpo tem 8 chaves. **O gate G1 mede o fato,
não a inferência.**

### 2.4 Os 38 códigos, os 43 slugs, e os 5 que só existem no bundle

```bash
python - <<'PY'
# lê GET /seguradoras/ do HAR e faz a diferença contra o mapa do bundle
PY
```

📊 **13/09/2026:**

```
GET /seguradoras/ (09/09) ....... 38 códigos
ALFA ALIRO ALLIANZ AXA AZUL BANESTES BB BPSEGURADORA BRADESCO BVIX CAIXA DARWIN
GRINGO HDI INDIANA ITURAN JUSTOS LIBERTY MAPFRE MITSUI NEO PIER PORTO
RPSADMINISTRADORA SANCOR SANTANDERAUTO SEMPARAR SERASA SOMPO SPLITRISK SULAMERICA
TOKIOMARINE TOO TOYOTA USEBENS USEBENSNUBANK YOUSE ZURICH

mapa de rota do bundle .......... 43 slugs
só no bundle (5) ................ BLLU · GENERALI · GRUPO_HDI · ITAU · ZURICHSANTANDER
só na API (0) ................... —
```

🟡 **Divergência:** o diagnóstico §10.2 item 6 diz "+ 4 só no bundle" e lista
`BLLU, GENERALI, GRUPO_HDI, ZURICHSANTANDER`. São **5**: falta o `ITAU`. E isso
corrige a afirmação "`ITAU` não existe no portal" — 📊 ele **existe como rota** no
bundle (`ITAU:"itau"`); o que não existe é a oferta pela API. O defeito permanece,
com outra causa.

📊 Os três pares que decidem roteamento, literais do bundle:

```js
LIBERTY:"yelum"        // o estado do ui-router; os templates vêm de seguradoras/liberty/
GRUPO_HDI:"sompo"      // 🔴 quem "corrigir" para SOMPO manda o segurado para outra seguradora
SOMPO:"sompo-seguros"
```

📊 E o que o portal serve para a Yelum, no mesmo HAR:
`GET /app/paginas/seguradoras/liberty/menu-atendimento.html` →
`<title>Menu Atendimento - Liberty</title>`.

### 2.5 Os 77 endpoints do bundle

```bash
python - <<'PY'
# regex sobre o bundle: \.(get|post|put|patch|delete)\(\s*<var>\s*\+\s*"<path>"
PY
```

📊 **77 endpoints distintos.** Os que a proposta usa, com o corpo lido do bundle:

```
GET  agendamentos/opcoes-disponiveis     (sem params)
GET  agendamentos/datas-disponiveis      {CodigoProduto, CodigoCliente, Ano}
GET  agendamentos/horarios-disponiveis   {CodigoCliente, DataAgendamento, CodigoProduto}
POST agendamentos                        {CodigoCliente, DataDeAgendamento, Horario,
                                          CodigoProduto, QuantidadeTempoServico,
                                          QuantidadeTempoPermanencia, Encaixe}
POST direcionamentos                     {CodigoCliente, CodigoProduto, TipoCredenciado}
POST lojas/consultar-distancias          {CodigoAtendimento, Cep, Uf, Cidade, Logradouro, Bairro}
POST atendimentos-fotografias/web        FormData: "CodigoAtendimento" + N× "Imagens"
                                          transformRequest: angular.identity
                                          headers: {"Content-Type": undefined}
GET  atendimentos/vistoriamobile         ?telefone=<telefone>
PUT  atendimentos/corretores             {Documento}
PUT  atendimentos/cep                    {Cep}
PUT  atendimentos/cancelar               {codigoMotivoCancelamento, codigoAtendimento,
                                          observacaoMotivoCancelamento}
GET  cidades                             {UF, ExibeMunicipios, PolidorFarol}
GET  clientes/cidades                    {CodigoCidade, CodigoTipoScript, CodigoScript,
                                          Chassi, Reembolso}
GET  clientes/cidades-proximas           (mesmos params)
GET  atendimentos/servicos-itens         {CodigoScript, CodigoTipoScript}
GET  atendimentos/ofertas-polimentos-farois {codigoScript, codigoSeguradora, codigoTipoScript}
POST atendimentos/emitir-atendimento-formalizado/{codigo}
```

📊 **Achado extra, não citado na proposta mas útil ao executor:** o bundle tem uma
estrutura `regraDeBloqueio` com quatro travas por apólice —
`BloqueioAtendimentoPorReembolso`, `BloqueioAtendimentoPorEventoComposto`,
`BloqueioAtendimentoPorLataria`, `BloqueioAtendimentoPorTipoScript`. **Nenhuma é lida
pelo nosso código.** Vale uma pendência.

### 2.6 O portal diz que lataria não agenda

📊 `GET agendamentos/opcoes-disponiveis`, na captura de lataria:

```json
{"DisponibilizarAgendamento": false, "IrParaConclusaoDeAtendimento": true,
 "ExibirAvisoVistoria": false, "RealizarVistoria": false, "ExisteVistoriaCriada": false,
 "PermiteVistoriaMobile": false, "PermiteVistoriaLoja": false, "MensagemVistoria": "",
 "VistoriaOnline": false, "VistoriaFinalizada": false, "ExisteAgendamento": false,
 "ExisteOrdemServico": true, "BloqueadoPorFraude": false, "AceitaReparo": false,
 "GerarOrdemServicoGenesis": false, "OpcoesAgendamento": []}
```

### 2.7 Os catálogos variam por apólice, não por seguradora

📊 `GET /apolices/itens-cobertos` e a primeira `GET /motivos-dano` de cada HAR:

| captura | itens | categorias presentes | motivos |
|---|---|---|---|
| Yelum 09/09 | **21** | `L`, `V` | 7 |
| Yelum 14/08 | **30** | `L`, `U`, `V` | 12 |
| Porto 15/08 | **21** | `V` | 14 |

📊 Peças vistas nas três: `VIDRO PARABRISA`, `VIDRO DE PORTA`, `VIDRO DE JANELA`,
`VIDRO VIGIA (TRASEIRO)`, `FAROL PRINCIPAL CONVENCIONAL COM FEIXE EM LED`,
`FAROL MILHA/NEBLINA CONVENCIONAL`, `FAROL PRINCIPAL XENON`,
`FAROL PRINCIPAL LED ORIENTADO POR CÂMERA`.

### 2.8 As três perguntas do 80% que temos medidas (vidro de porta, Yelum)

📊 De `POST /questionarios/perguntas`, uma por rodada, `204` no fim:

```
Cod 4  (Tipo A)  "O VIDRO DANIFICADO TEM PELÍCULA DE CONTROLE SOLAR (INSULFILM)?"
                 SIM (1) · NÃO (2) · NÃO SABE (3)
Cod 39 (Tipo P)  "O VIDRO DANIFICADO É DA PORTA DIANTEIRA OU TRASEIRA?"
                 DIANTEIRA (123) · TRASEIRA (124) · NÃO SABE (125)
Cod 35 (Tipo O)  "QUAL O LADO DO ITEM DANIFICADO?"
                 NÃO SABE (40) · LADO DO CARONA (38) · LADO DO MOTORISTA (39)
```

⚠️ **`NumeroOrdem` é 0 em duas das três, e a ordem de `Respostas` não é a da tela**
(em `Cod 35`, "NÃO SABE" vem primeiro no array). **Nunca escolher opção por posição.**
O motor stateless reenvia o array inteiro a cada rodada — é o que torna o replay
offline possível.

### 2.9 A régua de 5/20 cm é de LATARIA

📊 `GET atendimentos/servicos-detalhes`, chamado **na captura de lataria**:

```json
[{"Codigo":1,"Tamanho":"MENOR QUE 05cm"},
 {"Codigo":2,"Tamanho":"ENTRE 5 E 20cm"},
 {"Codigo":3,"Tamanho":"MAIOR QUE 20cm"}]
```

🟡 **Refinamento do diagnóstico:** ele fala em "três réguas" para o trincado. São
**duas coisas diferentes**: 10 cm × moeda de 1 real é a contradição real (trincado de
para-brisa, decide troca × reparo); 5/20 cm é o **amassado de lataria**, e não
compete com nenhuma delas.

### 2.10 O preflight da Porto que morre sem cobertura

📊 `GET /apolices?…&Seguradora=PORTO&TipoAtendimento=2` → **400**:

```json
{"Message": "A apólice do veículo informado não possui cláusula de Roda, Pneu e
             Suspensão contratada", "Tipo": "RegraDeNegocioExcecao"}
```

Bate exatamente com `classificar_preflight` (`vidros_api.py:148+`) e com
`TIPO_REGRA_DE_NEGOCIO = "regradenegocioexcecao"` (`:129`). 📊 **Nenhum atendimento
nasceu** nessa captura — o preflight fez o trabalho dele.

### 2.11 O .docx da Regina

```bash
python -c "import zipfile,re; ..."   # lê word/document.xml e conta <w:p> com texto
```

📊 **64 parágrafos com texto · 8 blocos de dano · 23 perguntas distintas.**

Blocos: para-brisa · retrovisor · lanterna · farol · vidros de porta · para-choque ·
lataria/pintura · vigia.

🔴 **A pergunta que aparece em 8 de 8 blocos, além da data: a CIDADE para o serviço**
(parágrafos 14, 24, 28, 33, 39, 49, 56, 64). É o fundamento do slot bloqueante de
P0-5.

📊 As 23 distintas: placa · data · rodovia/urbano · relato · cidade · posição da
trinca · sensor de chuva · faixa degradê · tamanho da trinca (moeda de 1 real) ·
ADAS · capa pintada/fosca · lado · pisca · regulagem · capa na peça · bipartida
mala/carroceria · película · dianteira/traseira · vidro fixo · sobe-e-desce ·
para-choque dt/tr · quais peças · desembaçador térmico.

📊 E as duas frases dela que viram copy do robô (parágrafos 50 e 57):
*"A seguradora que indica a loja para serviço"* · *"Os danos deverão ser do mesmo
evento… As peças não são trocadas e sim reparadas."*

### 2.12 O que o laboratório da SPEC-077 diz do material

```bash
cd backend && PYTHONIOENCODING=utf-8 python scripts/portal_factory.py lab har \
  --arquivo "../docs/intake/materiais/portal-vidros/YELUM/YELUM 1/abraseuatendimento.com.br.har" \
  --host abraseuatendimento.com.br
```

📊 **Saída, 13/09/2026** (a ferramenta existe, roda, e **nunca foi usada sobre este
material** antes de hoje):

```
354 chamada(s) no arquivo · 188 depois de descartar ruído (83 asset · 83 telemetry)
host que NAVEGA: abraseuatendimento.com.br
host que SERVE API: api.autoglass.com.br (31 respostas JSON)
endpoints distintos: 41 · de ESCRITA: 14 · com forma inferível: 29
respostas JSON: 44 · com corpo capturado: 44
```

---

## §3 · O que **continua desconhecido** — e o roteiro de remedição

| lacuna | por que importa | quem destrava |
|---|---|---|
| 🔴 **O `POST agendamentos` nunca foi visto** | é o último clique da vidraçaria; sem ele o fluxo para em 99% | 🧑 captura nº 1 da Regina |
| 🔴 **O questionário do PARA-BRISA nunca foi capturado** | é a peça mais frequente; e é onde a régua real do trincado mora | 🧑 captura nº 1 |
| **O subfluxo de domicílio** | `AtendeServicoMovel:false` nas duas capturas; formas de pagamento nunca vistas | 🧑 captura nº 2 |
| **Vistoria e upload de foto** | `PermiteVistoriaMobile:false` em todas; o link nunca foi gerado | 🧑 captura nº 3 |
| **O freio é por job ou global?** | decide se o canário é seguro (Q-A do BLOCO 0) | 🤖 BLOCO 0 |
| **`itens-cobertos` exige Token?** | decide se a desambiguação de P1-4 cabe antes ou depois da fronteira A (Q-B) | 🤖 BLOCO 0 |
| **O autocomplete lista "Liberty" ou "Yelum"?** | decide se o caminho DOM está clicando na opção errada (Q-C) | 🤖 BLOCO 0, com a captura |
| **`regraDeBloqueio` (4 travas por apólice)** | o portal pode recusar lataria ou evento composto, e não lemos | 🤖 pendência nova |
| **`abandonar`, `finalizar`** | declarados no bundle, zero capturas | 🧑 qualquer captura que os exerça |
| **Bradesco** | qual dos dois portais aceita | 🧑 captura dupla (D-PILOTO-17) |
| **As outras 34 seguradoras** | P-50: zero evidência | 🧑 1 captura de passo 1 cada |

---

## §4 · As armadilhas que o aquecimento (§5.2 do protocolo) deve refutar

| a resposta óbvia | por que está **errada** |
|---|---|
| *"O corpo do PATCH tem 11 campos, é o contrato do bundle"* | 📊 no fio são **8** em 2 de 2 capturas. Mandar `null` nos 3 ausentes é inventar campo, e o gate G1 fica vermelho. |
| *"A fronteira material é o `POST /questionarios`"* | só para categoria `V`. Para `L` é o **PATCH**, e é assim que nasce o segundo atendimento pago. |
| *"`ITAU` não existe no portal, é só apagar"* | 📊 ele **existe como rota** no bundle. O defeito é que a API não o oferece — a correção é `ativa: False`, não o apagamento cego. |
| *"Yelum é Yelum"* | 📊 no portal ela é **`LIBERTY`**, com templates em `seguradoras/liberty/`. E o código digita "Yelum" num autocomplete. |
| *"`sompo` deve apontar para `SOMPO`"* | 📊 `GRUPO_HDI:"sompo"` e `SOMPO:"sompo-seguros"`. "Corrigir" manda o segurado para outra seguradora. |
| *"A régua do trincado tem três versões, escolha uma"* | 5/20 cm é **amassado de lataria**, não trincado. A contradição real é 10 cm × moeda. |
| *"Lataria não tem agendamento, é só um `if`"* | 📊 o portal **diz**: `DisponibilizarAgendamento:false`. Ler vence decorar. |
| *"O prompt está certo: CPF + data + relato"* | 📊 `TRANSPORTAVEIS` trava por **6** campos. O prompt é o mais errado dos três, e é o que o modelo lê primeiro. |
| *"`POST lojas/consultar-distancias` é POST, então é efeito material"* | é cálculo de rota. Armar o guard nele treina a equipe a ignorá-lo. |
| *"Basta escrever o contrato do agendamento a partir do bundle e liberar"* | ⛔ SPEC-077: CANDIDATE ≠ APPROVED. Sem captura, não sai — mesmo com as duas flags verdes. |
| *"`SessaoVidros.chamar` serve para o upload de foto"* | 📊 ela só faz JSON (`vidros_sessao.py:108-121`). Multipart exige um **segundo** caminho de `page.evaluate`. |
| *"O diagnóstico já mediu tudo, é só codar"* | 3 linhas citadas por ele **mudaram** (ver §1), e 2 números dele estavam errados (§1.1, §2.4). O BLOCO 0 remede. |

---

## §5 · A pesquisa externa — o que a proposta escolheu, e o que falta ao pesquisador

As 6 referências estão na §13 da proposta, cada uma com URL, o que modelamos, o que
rejeitamos e como o juiz inspeciona. 🔴 **O pesquisador da execução reabre cada uma e
escreve a data de reabertura na SPEC convertida** (protocolo §7.3).

**Dois pedidos específicos ao pesquisador:**

1. **`har-to-openapi`**: o pacote o nomeia; esta proposta **não afirma a URL do
   repositório canônico**, porque não a conferiu. O pesquisador confirma qual é, roda
   sobre o HAR da Yelum e compara a contagem de endpoints e de schemas com a de
   `lab api-infer`. Se a ferramenta externa inferir algo que a nossa não infere,
   **isso é um achado para a SPEC-077**, não um motivo para trocar de ferramenta.
2. **Optic** (`useoptic.com`) foi considerada e **não entrou** nas 6: o que ela
   resolve — diff de tráfego contra um OpenAPI versionado — é exatamente o que
   `lab drift` já faz. Se o pesquisador achar que ela faz algo que o `lab drift` não
   faz, ela entra no lugar da referência 6.

---

*Conferido em 13/09/2026 · worktree `AutoBrokers-FIX` · HEAD `a0bb5fe` ·
preflight: 0 atrás, 0 à frente da `origin/main`.*
