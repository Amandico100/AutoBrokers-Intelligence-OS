# Laudo pericial — SPA AngularJS Portal Vidros (YELUM LATARIA)

Arquivo principal analisado: `app-231e920f7d.min.js.download` (256.733 bytes, uma linha só).
Também verificados (sem ocorrência das chaves pedidas, salvo indicado): `componentes-92de4331fc.min.js.download`, `modules.e762be2b6b709245aabb.js.download`, `common.js.download`, `util.js.download`, `base.js.download`.
Base da API (variável `a`) = `i.enderecos.atendimentoweb` (injetada por `ApiService`/serviços — não achei o valor literal do host neste bundle, só a variável).

Todos os offsets abaixo são posições de caractere dentro do arquivo (`app-231e920f7d.min.js.download`), obtidos com Python `re.finditer` sobre o arquivo lido como uma string única.

---

## 1. AGENDAMENTO — POST "agendamentos"

**Regra:** o corpo é montado na função `Q(o)`→função interna (dentro do Passo5Controller), a partir de `P.blocoHorario` (o BLOCO de horário selecionado) e de `o` (o produto/cliente escolhido). `Encaixe` **não** vem de `QuantidadeDisponivel`, `PossuiEncaixeDisponivel` nem `SolicitacaoEncaixe` do bloco — vem de uma flag de UI `P.encaixe`, que só fica `true` quando `P.atendimento.passo5.agendamento.TipoAgendamento === "Encaixe"` (ou seja, a ABA/MODO que o usuário escolheu antes de escolher o horário, não um campo do próprio bloco de horário).

Trecho literal (offset ~213936-215193, service factory):
```
obterRegrasParaAgendamento:function(){return e.get(a+"agendamentos/opcoes-disponiveis").then(function(o){n.regrasParaAgendamento=o.data})},
obterDatasDisponiveisParaAgendamento:function(o){return e.get(a+"agendamentos/datas-disponiveis",{params:{CodigoProduto:o.CodigoProduto,CodigoCliente:o.CodigoCliente,Ano:o.Ano}})...},
obterHorariosDisponiveisParaAgendamento:function(o){return e.get(a+"agendamentos/horarios-disponiveis",{params:{CodigoCliente:o.CodigoCliente,DataAgendamento:o.DataAgendamento,CodigoProduto:o.CodigoProduto}})...},
agendarServicoEmLojaPropria:function(o){return e.post(a+"agendamentos",{CodigoCliente:o.CodigoCliente,DataDeAgendamento:o.DataDeAgendamento,Horario:o.Horario,CodigoProduto:o.CodigoProduto,QuantidadeTempoServico:o.QuantidadeTempoServico,QuantidadeTempoPermanencia:o.QuantidadeTempoPermanencia,Encaixe:o.Encaixe}).then(function(o){return n.agendamento=o.data})}
```

Trecho literal de quem monta o objeto `o` passado a `agendarServicoEmLojaPropria` (offset ~142470, dentro da função `Q`):
```
function(o){"Encaixe"===P.atendimento.passo5.agendamento.TipoAgendamento&&(P.encaixe=!0);
var n={CodigoCliente:o.CodigoCliente,DataDeAgendamento:moment(P.atendimento.passo5.agendamento.DataAgendamento).format("YYYY-MM-DD"),
Horario:P.atendimento.passo5.agendamento.HoraAgendamento,CodigoProduto:o.CodigoProduto,
QuantidadeTempoServico:P.blocoHorario.TempoServico,QuantidadeTempoPermanencia:P.blocoHorario.TempoPermanencia,
Encaixe:P.encaixe||!1};
return e.agendarServicoEmLojaPropria(n).then(function(){...
a.verificarRegrasAposAgendamentoDeServico(e.agendamento).then(function(o){o.ExibirTelaDeClonclusaoDeAtendimento&&F()})},
function(e){a.verificarRegrasCasoHouverErroAoTentarAgendarUmServico(e).then(function(e){e.ObterHorariosDisponiveis?L(o):F()})})}
```

**Filtro de disponibilidade (quais blocos o usuário pode escolher):** função `L(o)` chama `obterHorariosDisponiveisParaAgendamento`, monta `P.blocosDeHorarios` (todos), `P.blocosDeHorariosPadrao` (cópia) e `P.blocosDeHorariosEncaixe` (só os que têm `PossuiEncaixeDisponivel===true`). O que o usuário efetivamente pode selecionar na tela normal é:
```
P.horariosDisponiveisParaAgendamento=P.blocosDeHorariosPadrao.filter(function(o){return!o.Bloqueado}).map(function(o){return o.Horario})
```
`Bloqueado`/`BloqueadoEncaixe` vêm da função `I(o,e,a)`:
```
function I(o,e,a){var n=!1;(P.agendamentoResponse&&P.agendamentoResponse.EncaixeCeven&&"Sim"===P.agendamentoResponse.EncaixeCeven.Value||P.atendimento&&"Sim"===P.atendimento.EncaixeCeven||e&&"Sim"===e.EncaixeCeven)&&(n=!0);
var i=!1;i=a||n?0===o.QuantidadeEncaixeParametrizadoDisponivel:0===o.QuantidadeDisponivel;
...
return"Atendimento"===P.tipoDocumento&&P.loja&&!P.loja.EstoqueProprio&&P.loja.TemPeca?i||d:i}
```
Ou seja: um bloco fica bloqueado quando `QuantidadeDisponivel===0` (modo padrão) ou `QuantidadeEncaixeParametrizadoDisponivel===0` (modo encaixe/EncaixeCeven), combinado (OR) com um bloqueio por previsão de peça em loja sem estoque próprio.

**Resposta `{ServicoAgendado, ExibirPesquisaDeSatisfacao}`:** o achado é que **essas duas chaves específicas NÃO existem em nenhum ponto do bundle** (busquei `ServicoAgendado` — 0 ocorrências; `ExibirPesquisaDeSatisfacao` só aparece 1 vez, no local abaixo). O que existe é `verificarRegrasAposAgendamentoDeServico(a)`:
```
verificarRegrasAposAgendamentoDeServico:function(a){var r=o.defer();
(a={ExibirTelaDeClonclusaoDeAtendimento:!1}).ExibirPesquisaDeSatisfacao?
  i.exibirPesquisaSatisfacaoClienteVip().then(function(o){o?(a.ExibirTelaDeClonclusaoDeAtendimento=!0,r.resolve(a)):i.exibirAvisoClienteVipInsatisfeito().then(function(){e.inserirRegistroDeInsatisfacaoDeClienteVip().then(function(){a.ExibirTelaDeClonclusaoDeAtendimento=!0,r.resolve(a)})})}):
  (a.ExibirTelaDeClonclusaoDeAtendimento=!0,r.resolve(a));
return r.promise}
```
**FATO relevante:** o parâmetro `a` (que é `e.agendamento`, isto é, a resposta real do POST `agendamentos`) é **imediatamente sobrescrito** por `a={ExibirTelaDeClonclusaoDeAtendimento:!1}` antes de se ler `.ExibirPesquisaDeSatisfacao` — então essa leitura é sempre sobre o objeto novo, que nunca tem essa chave. Isso torna o ramo "pesquisa de satisfação Cliente VIP" **morto neste bundle**: na prática, toda chamada a esta função sempre cai no `else` e sempre resolve `{ExibirTelaDeClonclusaoDeAtendimento:true}`, independentemente do que a API tenha devolvido. (Isto é uma leitura do código tal como está — não testei em runtime; registrado como FATO de código, não como comportamento observado em produção.)

**"direcionamentos":** disparado por `direcionarServicoEmLojaCredenciada` (offset ~215193), chamada dentro da função que decide entre confecção automática de O.S. e direcionamento para loja credenciada, condicionada por `o.IdLoja`:
```
direcionarServicoEmLojaCredenciada:function(o){return e.post(a+"direcionamentos",{CodigoCliente:o.CodigoCliente,CodigoProduto:o.CodigoProduto,TipoCredenciado:o.TipoCredenciado}).then(function(o){return n.direcionamento=o.data})}
```
Call site (offset ~136902):
```
if(0!==o.IdLoja){const a={CodigoAtendimento:e.dadosDoAtendimento.CodigoAtendimento,IdLoja:o.IdLoja};return e.confeccionarOSAutomatica(a).then(Y)}
{const a={CodigoCliente:o.CodigoCliente,CodigoProduto:o.CodigoProduto,TipoCredenciado:o.TipoCredenciado};return e.direcionarServicoEmLojaCredenciada(a).then(Y)}
```
Ou seja: `direcionamentos` só é chamado quando `IdLoja===0` (nenhuma loja física escolhida) — o serviço é direcionado a um credenciado em vez de confeccionar O.S. automática numa loja.

---

## 2. ROTEADOR pós "agendamentos/opcoes-disponiveis" — função `M(o)`

Trecho literal completo (offset ~141712), na ordem exata do código:
```
function M(o){
  o.IrParaConclusaoDeAtendimento||o.ExisteVistoriaCriada||o.ExisteAgendamento||o.ExisteOrdemServico||o.VistoriaFinalizada
    ?F()
    :o.PermiteVistoriaAmbas
      ?P.ambasVistoria=!0
      :o.PermiteVistoriaLoja
        ?T(o)
        :o.PermiteVistoriaMobile
          ?k()
          :o.RealizarVistoria
            ?V()
            :o.DisponibilizarAgendamento
              ?T(o)
              :o.PermiteOpcaoVistoria
                ?(P.existeOpcaoVistoria=!0,e.validarVeiculoCarga(P.dadosSolicitante.Atendimento).then(function(o){n.exibirModalPrioridadeAtendimento(P.dadosSolicitante.Atendimento,o)}).catch(function(){n.exibirModalPrioridadeAtendimento(P.dadosSolicitante.Atendimento,!1)}))
                :F()
}
```
**Ordem das condições (a primeira verdadeira decide):**
1. `IrParaConclusaoDeAtendimento` OU `ExisteVistoriaCriada` OU `ExisteAgendamento` OU `ExisteOrdemServico` OU `VistoriaFinalizada` → `F()` (vai para a tela de conclusão do atendimento)
2. `PermiteVistoriaAmbas` → mostra as duas opções de vistoria (mobile e loja)
3. `PermiteVistoriaLoja` → `T(o)` (tela de agendamento/loja)
4. `PermiteVistoriaMobile` → `k()` (modo vistoria mobile)
5. `RealizarVistoria` → `V()`
6. `DisponibilizarAgendamento` → `T(o)`
7. `PermiteOpcaoVistoria` → marca `existeOpcaoVistoria=true`, valida se é veículo de carga e abre o modal "queremos entender sua necessidade" (`exibirModalPrioridadeAtendimento`)
8. Nenhuma das anteriores → `F()` (vai direto para conclusão)

**Chaves `BloqueadoPorFraude`, `BloqueadoIlhaNormal` e `GerarOrdemServicoGenesis`: NÃO ENCONTRADAS.** Procurei essas 3 strings exatas (case-sensitive) nos três arquivos JS (`app`, `componentes`, `modules`) e não há nenhuma ocorrência. Não fazem parte desta função nem de nenhuma outra neste bundle.

**Caso medido na lataria (BloqueadoIlhaNormal=true e PermiteOpcaoVistoria=true, resto false):** como `BloqueadoIlhaNormal` não é uma chave que `M(o)` lê, ela é irrelevante para o roteador — o código só olha para as chaves que existem na função. Com `PermiteOpcaoVistoria=true` e todas as chaves 1–6 falsas, o resultado é o ramo 7: `P.existeOpcaoVistoria=!0`, chama `validarVeiculoCarga` e depois `exibirModalPrioridadeAtendimento` (a tela "queremos entender sua necessidade", ver §4).

`T(o)` (chamada nos ramos 3 e 6), offset ~142956:
```
function T(o){o.IrParaConclusaoDeAtendimento?(...,Z()):(o.ExibirAvisoVistoria&&n.exibirDialogAvisoSobreAgendamentoVistoria(),o.ExibirAvisoVistoriaPorRegraDeFraude&&n.exibirDialogAvisoSobreAgendamentoVistoriaPorRegraDeFraude(),P.agendando=!0,P.agendamento=o,P.exibirTelaAgendamento=o.DisponibilizarAgendamento,P.opcoesAgendamento=o.OpcoesAgendamento,P.exibirCardServicoMovel=(P.opcoesAgendamento||[]).some(function(o){return null!=o&&"S"===o.DisponibilizaAgenda}),null!==P.opcoesAgendamento&&0!==P.opcoesAgendamento.length||l.vistoriaLojaCredenciada().then(function(){F()}))}
```
Nota: existe uma chave `ExibirAvisoVistoriaPorRegraDeFraude` (avisa sobre fraude ao agendar vistoria) — mas é diferente de `BloqueadoPorFraude`; não bloqueia nada, só mostra um diálogo de aviso.

---

## 3. VISTORIA — "receber link no celular OU vistoria em uma loja" e modal de fotos

**Opção "M" (online/link) e "L" (loja) — função `P.inserirSelecaoOpcaoVistoria(o)`**, offset ~138516:
```
P.inserirSelecaoOpcaoVistoria=function(o){
  if("M"===o)P.ocorrencia="SEGURADO TEM PREFER�NCIA POR REALIZAR VISTORIA ONLINE (LINK)";
  else{if("L"!==o)return;P.ocorrencia="SEGURADO TEM PREFER�NCIA POR REALIZAR VISTORIA EM LOJA"}
  var e={CodigoAtendimento:P.dadosSolicitante.Atendimento,Ocorrencia:P.ocorrencia};
  h.inserirOcorrenciaAtendimento(e).then(function(){F()})
}
```
(o `�` é o mojibake de `Ê`/`Ê`/acentos — o texto real é "SEGURADO TEM PREFERÊNCIA POR REALIZAR VISTORIA ONLINE (LINK)" / "... EM LOJA"). Essa função só grava a OCORRÊNCIA (POST `ocorrencias`) e chama `F()` — vai direto para a tela de conclusão. **Não é aqui** que o SPA chama `vistoriamobile` — essa é uma ação separada.

**Endpoint GET vistoriamobile (telefone) — botão "receber link no celular"**, `VistoriaService` (offset ~242416):
```
vistoriaMobileOnline:function(){return t.get(n+"atendimentos/vistoriamobileonline").then(function(i){e.dadosVistoriaMobileOnline=i.data})},
vistoriaMobilePosterior:function(i){return t.get(n+"atendimentos/vistoriamobile",{params:{telefone:i||""}})},
vistoriaFinalizada:function(){return t.get(n+"atendimentos/vistoriafinalizada").then(function(i){e.vistoriaEstaFinalizada=i.data})},
vistoriaLojaCredenciada:function(){return t.post(n+"atendimentos/vistoriacredenciado").then()}
```
**Correção ao enunciado da pergunta:** é um `GET`, não um POST, com `telefone` como querystring param — e o nome do endpoint é `atendimentos/vistoriamobile` (sem `?telefone=` fixo no código, o Angular monta a querystring a partir de `params`).

**`P.vistoriaMobileReceberLink`** (offset ~134000), o botão que dispara isso:
```
P.vistoriaMobileReceberLink=function(){
  P.ambasVistoria=!1;
  var o=function(o){l.vistoriaMobilePosterior(o).then(function(){F()})};
  if(!1===P.atendimento.PossuiTelefoneRecebeSMS){ /* abre modal para digitar telefone e chama o(telefone) ao confirmar */ }
  else o()
}
```
Se o atendimento já tem telefone que recebe SMS (`PossuiTelefoneRecebeSMS`), chama direto `vistoriaMobilePosterior()` sem telefone extra; senão, abre um modal para digitar telefone antes. Em ambos os casos, ao terminar, chama `F()` (vai para conclusão) — **não há uma tela intermediária de confirmação, o fluxo cai direto na tela final**.

**Modal de fotos (`atendimentos-fotografias`):**
Abertura, offset ~135705 (`P.abrirModalFotosVistoria`): abre `ModalFotosVistoriaController` com `template modal-fotos-vistoria.html`, passando `codigoAtendimento`. É chamado a partir de menus/telas de vistoria (é uma ação disponível ao usuário, não automática).

Envio (offset ~177219, dentro do controller):
```
a.anexarFotos=function(){
  if(!a.fotosVistoria||0===a.fotosVistoria.length)return void i.erro("Selecione pelo menos uma foto para enviar.");
  a.enviando=!0,
  t.inserirFotografiasAtendimento(r,a.fotosVistoria).then(function(){a.envioComSucesso=!0}).catch(function(){i.erro("Erro ao enviar as fotos. Por favor, tente novamente.")}).finally(function(){a.enviando=!1})
}
```
Serviço (offset ~219858):
```
inserirFotografiasAtendimento:function(o,t){
  var n=new FormData;
  n.append("CodigoAtendimento",o);
  for(var i=0;i<t.length;i++)n.append("Imagens",t[i]);
  return e.post(a+"atendimentos-fotografias/web",n,{transformRequest:angular.identity,headers:{"Content-Type":void 0}}).then(function(o){return o.data})
}
```
Regras de seleção de arquivo (offset ~177700, `selecionarArquivos`): apenas `image/jpeg`/`image/jpg`/`image/png`; tamanho máx. **5MB por foto** (`l.size>5242880`); limite de **10 fotos** (`a.fotosVistoria.length>=10`).

---

## 4. PRIORIDADE — POST "atendimentos-prioridades" ("queremos entender sua necessidade")

**Quando aparece:** exclusivamente pelo ramo 7 do roteador `M(o)` (§2) — quando nenhuma das opções de agenda/conclusão/vistoria é verdadeira mas `PermiteOpcaoVistoria` é. `n.exibirModalPrioridadeAtendimento(codigoAtendimento, veiculoCarga)` abre o `ModalPrioridadeAtendimentoController`, que tem **dois textos diferentes** dependendo de `veiculoCarga` (resultado de `GET atendimentos-prioridades/{codigo}` interpretado por `validarVeiculoCarga`):

Trecho literal (offset ~173445-174900):
```
const r=function(a){
  if(a)return{labelSelect:"Qual � a situa��o atual do ve�culo?",labelBotoes:"Existe uma data limite para resolver esse atendimento?",
    placeholderObservacao:"Exemplo: dependo do ve�culo para trabalhar, consulta agendada ou preciso resolver at� uma data espec�fica�",
    opcoesTipoEnvio:[{valor:"em_viagem_rota",descricao:"Est� em viagem/rota"},{valor:"saida_entrega_programada",descricao:"Tem sa�da ou entrega programada"},{valor:"parado_aguardando",descricao:"Est� parado aguardando atendimento"},{valor:"veiculo_pernoita_na_rua",descricao:"Ve�culo pernoita na rua"},{valor:"nao_esta_em_uso",descricao:"N�o est� em uso no momento"}],
    opcoesPrioridade:[{valor:"hoje",descricao:"Hoje"},{valor:"ate_2_dias",descricao:"At� 2 dias"},{valor:"esta_semana",descricao:"Esta semana"},{valor:"sem_data_limite",descricao:"N�o tenho data limite"}]};
  return{labelSelect:"O ve�culo � necess�rio para alguma situa��o com prazo ou impacto importante?",labelBotoes:"Existe uma data limite para resolver esse atendimento?",
    placeholderObservacao:"Exemplo: ve�culo carregado, entrega programada, motorista em rota, carga perec�vel, passageiros aguardando, ve�culo parado em outra cidade ou risco de atraso na opera��o.",
    opcoesTipoEnvio:[{valor:"trabalho_profissional",descricao:"Trabalho ou uso profissional"},{valor:"viagem_compromisso",descricao:"Viagem ou compromisso com data marcada"},{valor:"saude_rotina_familiar",descricao:"Sa�de ou rotina familiar essencial"},{valor:"veiculo_pernoita_na_rua",descricao:"Ve�culo pernoita na rua"},{valor:"nao_se_aplica",descricao:"N�o se aplica"}],
    opcoesPrioridade:[/* as mesmas 4 acima */]
}
```
(caracteres `�` = mojibake de acentos: "situação", "É", "não", "saúde", etc.)

**Opções fechadas (texto literal, descricao):**
- `TipoEnvio` (Situacao), quando `veiculoCarga=true`: "Está em viagem/rota" · "Tem saída ou entrega programada" · "Está parado aguardando atendimento" · "Veículo pernoita na rua" · "Não está em uso no momento"
- `TipoEnvio` (Situacao), quando `veiculoCarga=false`: "Trabalho ou uso profissional" · "Viagem ou compromisso com data marcada" · "Saúde ou rotina familiar essencial" · "Veículo pernoita na rua" · "Não se aplica"
- `Prioridade` (DataLimite), em ambos os casos: "Hoje" · "Até 2 dias" · "Esta semana" · "Não tenho data limite"

**Montagem do corpo enviado** (offset ~176050, `enviarResposta`):
```
const r=this.opcoesTipoEnvio.find(a=>a.valor===this.formulario.tipoEnvio),
      t=this.opcoesPrioridade.find(a=>a.valor===this.formulario.prioridade),
      s=t?t.descricao:(this.formulario.prioridade||"").replace(/_/g," "),
      l="sem_data_limite"===this.formulario.prioridade?"N�o tenho":s,
      c={CodigoAtendimento:e,Situacao:r?r.descricao:(this.formulario.tipoEnvio||"").replace(/_/g," "),DataLimite:l,Observacao:this.formulario.observacao};
o.salvarPrioridadeAtendimento(c).then(()=>{...})
```
Nota: quando `prioridade==="sem_data_limite"`, o `DataLimite` enviado é o texto **"Não tenho"** (truncado — não é o `descricao` completo "Não tenho data limite").

Serviço (offset ~220887):
```
salvarPrioridadeAtendimento:function(o){return e.post(a+"atendimentos-prioridades",{CodigoAtendimento:o.CodigoAtendimento,Situacao:o.Situacao,DataLimite:o.DataLimite,Observacao:o.Observacao}).then(function(o){return o.data})}
```
**É obrigatório?** O envio é bloqueado por validação de formulário Angular (`if(i&&i.$setSubmitted(),!i||i.$invalid)return`), então dentro do modal os campos são obrigatórios para o Confirmar funcionar. Mas a TELA em si só aparece condicionalmente (ramo 7 do roteador) — não é obrigatória para todo atendimento, só para os que caem nesse ramo específico.

---

## 5. `vistorias-previas/processar` e `corretores-reclamacoes`

**`vistorias-previas/processar`** — serviço `AtendimentosVistoriasPreviasService` (offset ~248355):
```
processarWebVistoriaPreviaAsync:function(e){return t.post(n+`/${e}/vistorias-previas/processar`,{params:{}}).then(function(e){return e.data})}
```
Chamada (offset ~140807), dentro da inicialização do Passo5Controller, **sempre disparada** (não há condicional antes dela):
```
S.processarWebVistoriaPreviaAsync(e.dadosDoAtendimento.CodigoAtendimento).then(function(){
  e.dadosDoAtendimento.VeiculoBlindado||(e.verificarReclamacaoCorretor(P.dadosSolicitante), g.verificarOferta(...).then(...), P.linkAreaSegurado=..., P.atendimento.PossuiTelefoneRecebeSMS=...),
  a.verificarRegrasParaRedirecionamentoParaDeAgendamento().then(function(o){P.consultandoDados=!1,P.agendamento=o,M(o)}),
  K()
})
```
**`corretores-reclamacoes`** (offset ~210872):
```
verificarReclamacaoCorretor:function(o){return e.post(a+"corretores-reclamacoes",o)}
```
Chamada com `P.dadosSolicitante` (dados de contato do solicitante) — **só quando `!e.dadosDoAtendimento.VeiculoBlindado`** (não é veículo blindado). Não tem `.then()` amarrado ao fluxo — é "fire-and-forget" (dispara e não espera).

**São necessários para o fluxo seguir?** Não. `a.verificarRegrasParaRedirecionamentoParaDeAgendamento().then(...M(o))` é chamado dentro do `.then()` de `processarWebVistoriaPreviaAsync`, mas o roteador `M(o)` não depende do resultado dessa chamada nem do de `corretores-reclamacoes` — ambos são passos paralelos/colaterais dentro do mesmo bloco, e o roteamento segue independente do que essas duas chamadas retornem (a única dependência real é o `.then()` externo de `processarWebVistoriaPreviaAsync`, cujo `.then()` só espera a Promise resolver, sem usar o valor resolvido).

---

## 6. CANCELAR — modal de cancelamento

**GET "motivos-cancelamento": existe no serviço, mas é código morto.**
```
recuperarMotivosCancelamento:function(){return e.get(a+"atendimentos/motivos-cancelamento").then(function(o){n.motivosCancelamento=o.data})}
```
Essa é a **única ocorrência** da string `recuperarMotivosCancelamento` no bundle inteiro — ou seja, a função é definida mas **nunca é chamada** por nenhum controller. O modal de cancelamento inicializa `r.motivosCancelamento={}` (vazio) e nunca o popula.

**`codigoMotivoCancelamento=39`** — é uma constante **fixa no código do controller** (não vem da lista de motivos, nem de seleção do usuário), offset ~167610:
```
r.cancelarAtendimento=function(e){
  var o="Ao confirmar o cancelamento, voc� n�o utilizar� o servi�o de sua seguradora para esse atendimento, deseja confirmar?";
  c.current.alteraTratativa&&(o="Ao confirmar o cancelamento, voc� n�o utilizar� o servi�o desse atendimento, deseja confirmar?");
  var s=n.confirm()...ok("Sim").cancel("N�o");
  n.show(s).then(function(){
    var e={codigoMotivoCancelamento:39,codigoAtendimento:r.codigoDoAtendimento,observacaoMotivoCancelamento:r.observacao};
    a.cancelarAtendimento(e).then(function(){toastr.success("Atendimento cancelado com sucesso!"),...})
  },function(){i.status="Segurado desistiu de cancelar o atendimento."})
}
```
Serviço (offset ~215995):
```
cancelarAtendimento:function(o){return e.put(a+"atendimentos/cancelar",{codigoMotivoCancelamento:o.codigoMotivoCancelamento,codigoAtendimento:o.codigoAtendimento,observacaoMotivoCancelamento:o.observacaoMotivoCancelamento})...}
```
**Mínimo de caracteres na observação: SIM, 20 caracteres — mas a validação está no HTML, não no JS minificado.** Encontrado no arquivo `Atendimento Web TELA DESEJA CANCELAR.html`:
```html
<p class="aw-modal-cancelamento__texto aw-modal-cancelamento__texto--ajuda">
    (Escreva pelo menos 20 caracteres)
</p>
<textarea ... maxlength="3800" md-maxlength="3800" minlength="20" ui-uppercased="" .../>
...
<button ... id="cancelar-atendimento-btn" ng-click="vm.cancelarAtendimento(...)"
  ng-disabled="(vm.observacao == undefined || vm.observacao == null || vm.observacao == '') || vm.observacao.length &lt; 20">
  Confirmar
</button>
```
Ou seja: o botão "Confirmar" fica desabilitado (`ng-disabled`) enquanto a observação estiver vazia OU tiver menos de 20 caracteres. Máximo 3.800 caracteres.

---

## 7. RETOMADA / CONSULTA

**Existe modo de reabrir atendimento existente.** Vários mecanismos encontrados:

**a) `token` como parâmetro de rota/estado ($stateParams), independente de POST "atendimentos":**
`Passo2Controller` injeta `$stateParams` (offset ~109543):
```
e.$inject=["AbraSeuAtendimentoService","$state","Analytics","$location","$stateParams","TokenService","$mdToast","DialogsPassosService","$scope"]
```
E no início de outro controller de passo (offset ~105467, mesmo padrão de injeção `$stateParams` como `n`, `TokenService` como `a`):
```
a.gravarTokenNoCookie(n.token)
```
ou seja: `TokenService.gravarTokenNoCookie($stateParams.token)` — o SPA lê um parâmetro `token` da URL/rota do Angular e grava direto no cookie, **sem precisar de um POST em "atendimentos"**. Isso é o mecanismo de link de retomada (ex.: link enviado por SMS/e-mail/WhatsApp com `?token=...` ou rota com esse param).

**b) De onde vem o token normalmente (fluxo novo):** `criarAtendimento` (POST "atendimentos", offset ~209531):
```
criarAtendimento:function(o){return e.post(a+"atendimentos",{Seguradora:o.seguradora,NumeroDaApolice:o.apolice.NumeroDaApolice,DataSinistro:o.DataSinistro,PlacaInformada:o.Placa.toUpperCase(),SufixoChassi:o.SufixoChassi,Origem:o.origem,CpfCnpjSegurado:o.CpfCnpj,NomeSegurado:o.NomeSegurado,TipoAtendimento:o.TipoAtendimento||null}).then(function(o){return n.atendimento=o.data,t.putObject("infoToken",n.atendimento),n})}
```
`t.putObject("infoToken", n.atendimento)` grava a **resposta inteira** do POST no cookie sob a chave `"infoToken"` (implica que a resposta de `atendimentos` tem um campo `.Token`, lido depois — ver abaixo).

**c) Não achei um endpoint dedicado que devolva token para um atendimento existente por placa+código, chassi ou CPF.** Procurei por variações (`token`, `Token`, endpoints com "token" no path) e não encontrei um GET/POST específico com esse propósito — o único jeito de obter token para retomada, no que este bundle mostra, é (a) o parâmetro de rota `token`, ou (b) criar um atendimento novo. Pode existir um endpoint assim que simplesmente não é usado por este SPA (fica em outro serviço/BFF) — não fica provado nem descartado pelo código-cliente.

**d) Onde o token é guardado:** cookie, via `$cookies` (Angular `ngCookies`), chave `"infoToken"`. Serviço `TokenService` (offset ~242334):
```
function e(e){return{gravarTokenNoCookie:function(n){e.putObject("infoToken",{Token:n})}}}
e.$inject=["$cookies"]
```
E o interceptor HTTP que usa esse cookie em toda chamada de API cujo `url` contenha `"api"` (offset ~204935):
```
request:function(e){if(e.url.indexOf("api")>0){var t=a.getObject("infoToken");t&&t.Token&&(e.headers.Token_Autorizacao=t.Token)}return e}
```
Ou seja: o header enviado é `Token_Autorizacao` (com underscore), lido de `$cookies.getObject("infoToken").Token`. **Não achei uso de `sessionStorage` nem `localStorage`** neste bundle (0 ocorrências de ambas as strings) — só cookie.

**e) O que a tela "ESSE ATENDIMENTO JÁ FOI FINALIZADO" verifica:** a string literal `"finalizado"` (em qualquer capitalização) **não existe em nenhum dos 5 arquivos JS verificados** (`app`, `componentes`, `modules`, `common`, `util`, `base` — todos 0 ocorrências). Isso indica fortemente que essa mensagem **não é um texto fixo do front**, e sim o texto genérico de erro vindo da API, mostrado pelo interceptor HTTP central (offset ~204983):
```
responseError:function(a){
  a.data&&a.data.Message
    ?t.get("$mdDialog").show(t.get("$mdDialog").alert({title:"Aten��o",textContent:a.data.Message,ok:"Fechar",...}))
    :t.get("$mdDialog").show(t.get("$mdDialog").alert({title:"Aten��o",textContent:"N�o foi poss�vel realizar esta opera��o, tente novamente mais tarde!",ok:"Fechar",...}));
  return e.reject(a)
}
```
**Ressalva honesta:** o print/HTML capturado mostra o botão como **"Ok"**, mas este interceptor genérico usa **"Fechar"**. Não encontrei, em nenhum dos JS analisados, um diálogo com título "Atenção" e botão "Ok" associado à palavra "finalizado". Então: a MECÂNICA (mostrar `Message` da resposta de erro da API dentro de um alert "Atenção") está provada; a correspondência exata de qual diálogo especificamente gerou aquele print com botão "Ok" **não está provada** — pode ser um alert diferente (não localizado) ou uma tela estática server-side. Marco como PARCIALMENTE ENCONTRADO / INFERÊNCIA razoável, não fato certo.

**f) Existe um controller dedicado a atendimento já existente/aberto:** `ModalAtendimentoAbertoExistenteController` (offset ~178956):
```
function e(e,n,t){this.fechar=function(){e.cancel()},this.consultarAtendimento=function(){n.open(t.enderecos.areaDoSegurado,"_system")}}
e.$inject=["$mdDialog","$window","ApiService"]
```
Disparado depois do POST `solicitantes`, checando se já existe atendimento aberto para o mesmo veículo/segurado (offset ~109202):
```
let o={Chassi:s.atendimento.apolice.Chassi,CpfCnpjSegurado:e.dadosDoAtendimento.CpfCnpjSegurado};
"S"==e.dadosDoAtendimento.IdtMovimento&&55==e.dadosDoAtendimento.CodigoSeguradora
  ?l.exibirAvisoParaProcurarCorretor()
  :e.verificarExistenciaAtendimentosAbertos(o).then(function(e){e&&l.exibirAtendimentoAbertoExistente()})
```
Serviço:
```
verificarExistenciaAtendimentosAbertos:function(o){return e.get(a+"atendimentos/atendimentos-abertos-existentes",{params:o}).then(function(o){return o.data})}
```
O modal, se acionado, oferece um botão que abre `enderecos.areaDoSegurado` (a Área do Segurado) numa nova aba/sistema — não é uma "retomada" dentro do próprio SPA, é um redirecionamento externo.

---

## 8. SOLICITANTE — POST "solicitantes"

**Objeto inicial** (offset ~105590, `Passo1Controller`/init):
```
s.solicitante={RelacaoTitular:null,EmailSegurado:null,EmailTitularAplice:null,NomeSolicitante:null,CpfCnpjSolicitante:null,EmailCorretor:null,Telefones:[],TermoExibido:!1,TermoAceito:!1}
```
**Preenchimento a partir dos dados do atendimento** (offset ~108250):
```
null!=e.dadosDoAtendimento.DescricaoRelacaoTitular&&(s.solicitante.RelacaoTitular=u.find(o=>o.Descricao==e.dadosDoAtendimento.DescricaoRelacaoTitular).Codigo.toString(),
  "1"!==s.solicitante.RelacaoTitular&&(s.solicitante.NomeSolicitante=e.dadosDoAtendimento.NomeContato,s.solicitante.CpfCnpjSolicitante=e.dadosDoAtendimento.CpfCnpjContato)),
s.solicitante.EmailCorretor=e.dadosDoAtendimento.EmailCorretor,
s.solicitante.EmailSegurado=e.dadosDoAtendimento.Email,
s.solicitante.EmailTitularAplice=e.dadosDoAtendimento.EmailTitularAplice,
e.dadosDoAtendimento.Telefones.length>0&&(s.solicitante.Telefones=[]),
e.dadosDoAtendimento.Telefones.forEach(e=>{s.solicitante.Telefones.push({Numero:e.Ddd+e.Numero,Tipo:e.Tipo,StatusEnvioWhatsapp:e.StatusEnvioWhatsapp})})
```
**FATO:** `EmailCorretor`, `EmailTitularAplice` e `StatusEnvioWhatsapp` (por telefone) são todos **copiados do backend** (`e.dadosDoAtendimento`) para o objeto solicitante — nenhum deles tem, neste bundle, um controle de UI (checkbox/toggle) que o usuário marque para definir `StatusEnvioWhatsapp=true`. Busquei `StatusEnvioWhatsapp` nos 3 bundles: só 2 ocorrências, ambas nesta mesma linha de cópia. **Não encontrei** onde o usuário "liga" o WhatsApp por telefone — é herdado do estado que já existe no atendimento.

**Envio** (offset ~106945, `s.salvarDados`):
```
s.salvarDados=function(){
  for(var t=s.solicitante.Telefones.length-1;t>=0;t--){s.solicitante.Telefones[t].Numero||s.solicitante.Telefones.splice(t,1)}
  return e.salvarDadosSolicitante(s.solicitante).then(function(){o.go(o.$current.parent.name+".passo3",{token:n.token})})
}
```
Serviço:
```
salvarDadosSolicitante:function(o){return e.post(a+"solicitantes",o).then(function(o){n.insatisfacaoClienteVip=o.data})}
```
Ou seja, **o objeto inteiro `s.solicitante`** é enviado como corpo — todas as chaves acima (menos telefones com `Numero` vazio, que são removidos antes de enviar).

**`TermoExibido`/`TermoAceito`** (offset ~107338): calculado, não fixo:
```
const e=!(!s.solicitante.EmailSegurado||!s.solicitante.EmailSegurado.trim()),
      o=!!s.solicitante.RelacaoTitular;
if(!e||!o)return s.solicitante.TermoExibido=!1,s.solicitante.TermoAceito=!1,!1;
const t="1"===s.solicitante.RelacaoTitular, i="6"===s.solicitante.RelacaoTitular,
      n=s.solicitante.EmailCorretor||!1,
      a=t&&!n||i&&n;
s.solicitante.TermoExibido=a,a||(s.solicitante.TermoAceito=!1);
return a
```
Traduzindo: o termo só é exibido quando há e-mail do segurado E relação com o titular selecionada, E ( (RelacaoTitular=="O Próprio" E **sem** e-mail de corretor) OU (RelacaoTitular=="Corretor" E **com** e-mail de corretor) ). Em qualquer outro caso, `TermoExibido=false` e `TermoAceito` é forçado a `false`.

**`RelacaoTitular` (código → texto)**, lista fechada, offset ~105850:
```
[{Descricao:"O Pr�prio",Codigo:1},{Descricao:"Conjuge",Codigo:2},{Descricao:"Filho",Codigo:3},{Descricao:"Outros",Codigo:5},{Descricao:"Corretor",Codigo:6}]
```
→ 1 = "O Próprio" · 2 = "Cônjuge" · 3 = "Filho" · 5 = "Outros" · 6 = "Corretor". **Nota:** não existe código 4 na lista (buraco na numeração, provavelmente um valor descontinuado no backend) — registrado como achado, não como suposição.

---

## 9. Outros endpoints de ESCRITA (POST/PUT/PATCH/DELETE) no fluxo, não listados acima

Levantamento exaustivo por regex sobre `e.post/put/patch/delete(a+"...")` e variações com template literal, no arquivo `app-231e920f7d.min.js.download` (nenhum desses verbos aparece nos outros dois bundles):

| Verbo | Endpoint | Quando dispara (achado no código) |
|---|---|---|
| POST | `atendimentos` | criação do atendimento (Passo1) — `criarAtendimento` |
| PATCH | `atendimentos` | `atualizarAtendimento` — atualização de dados do passo 3 (item danificado, evento composto, cidade etc.) |
| PATCH | `atendimentos/finalizar` | `finalizarAtendimento` |
| PATCH | `atendimentos/abandonar` | abandono de atendimento (achado no service; não rastreei o call site neste laudo) |
| PUT | `atendimentos/cancelar` | ver §6 |
| PUT | `atendimentos/cep` | atualização de CEP do atendimento |
| PUT | `atendimentos/corretores` | `salvarDadosCorretor`, body `{Documento:o}` |
| PUT | `atendimentos/alterar-reparo` | `alterarReparoAtendimento`, body `{Reparo:o}` |
| PUT | `atendimentos/prioriza-atendimento/{codigo}` | `priorizarAtendimento`, body `{Motivo,Observacao}` — distinto de `atendimentos-prioridades` (§4); não localizei call site no fluxo principal |
| POST | `atendimentos-negados` | `negarAtendimento`, body `{CodigoMotivoNegado, ObservacaoMotivoNegado}` |
| POST | `atendimentos-fotografias/web` | ver §3 |
| POST | `atendimentos/emitir-atendimento-formalizado/{codigo}` | `emitirAtendimentoFormalizado` |
| POST | `atendimentos/livres-escolhas` | `salvar` livre escolha de loja/prestador |
| POST | `atendimentos/livres-escolhas/cancelar` | `verificarCancelamentoLivreEscolha` |
| POST | `atendimentos/ofertas-status/` | `inserirOferta` (StatusAtendimentoService) — usado pelos modais de "como quer acompanhar" (e-mail/SMS/WhatsApp), §7 tangencial |
| POST | `atendimentos/polimentos-farois` | `salvarPolimentoFarol` |
| POST | `agendamentos/insatisfacao` | `inserirRegistroDeInsatisfacaoDeClienteVip` (chamado dentro de `verificarRegrasAposAgendamentoDeServico`, ver §1 — hoje inalcançável pela sobrescrita de `a`) |
| POST | `agendamentos/encaixes` | `enviarSolicitacaoEncaixe` — disparado pelo botão "Solicitação de Encaixe" (função `q`, offset ~146200) quando o horário desejado não tem vaga |
| POST | `questionarios/perguntas` | `recuperaPerguntasRespostas` |
| POST | `questionarios` | `salvarQuestionario` |
| POST | `questionarios/regras-reparo` | `obterRegrasParaReparo` |
| POST | `feedbacks` | `inserirFeedbackAtendimento`, body `{AvaliacaoTela,Nota,Tipo:"Geral",Path,Comentario,TagsVersaoPesquisa:[]}` |
| POST | `lojas/consultar-distancias` | `consultarDistancia`, body com Cep/Uf/Cidade/Logradouro/Bairro |
| POST | `ordens-servicos/confeccoes-automaticas/itens-servicos` | `confeccionarOSAutomatica` — ver §1 (ramo `IdLoja!==0`) |
| POST | `atendimentos/vistoriacredenciado` | `vistoriaLojaCredenciada` — ver §3/§2 |
| POST | `{base}/{codigo}/vistorias-previas/processar` | ver §5 |
| POST | `corretores-reclamacoes` | ver §5 |
| POST | `solicitantes` | ver §8 |
| POST | `atendimentos-prioridades` | ver §4 |
| POST | `agendamentos` | ver §1 |
| POST | `direcionamentos` | ver §1 |
| DELETE | `atendimentos/respostas` | `deletarAsRespostasDasPerguntasDoQuestionario` |
| POST | `atendimentos/respostas` | `OfertaDeReparoFoiRespondida`/`Respostas` do questionário |
| POST/PUT | `transportes-proprios/atendimentos` | serviço de transporte próprio (recuperar/inserir) — módulo separado, aparentemente para veículo reserva/guincho |
| POST | `servicos-moveis/ordens-servicos` | `gerarOS` do serviço móvel |

---

## Achados fora do escopo pedido (relevantes)

1. **Bug de código morto confirmado:** a checagem de `ExibirPesquisaDeSatisfacao` em `verificarRegrasAposAgendamentoDeServico` nunca pode ser verdadeira, porque o parâmetro que traria esse valor da API é sobrescrito antes de ser lido (ver §1). Mesma coisa para `agendamentos/insatisfacao` — inalcançável a partir daí.
2. **`recuperarMotivosCancelamento` é código morto** — a lista de motivos de cancelamento nunca é buscada nem exibida; o motivo enviado é sempre a constante `39`.
3. **`Token_Autorizacao` guardado em cookie, chave `infoToken`, contendo o objeto `atendimento` inteiro** (não só um token) — atenção para o que isso implica em termos de exposição de dado no cookie (fora do escopo pedido, mas relevante para quem for reimplementar).
4. **Regra especial hardcoded por seguradora**: `"S"==e.dadosDoAtendimento.IdtMovimento&&55==e.dadosDoAtendimento.CodigoSeguradora` desvia para "procurar corretor" em vez de checar atendimento aberto existente — `55` é um código de seguradora fixo no código-fonte do front (nome da seguradora não aparece, só o código numérico).
5. **Mojibake generalizado:** todo o bundle está em Latin-1 mal decodificado para UTF-8 (todos os acentos aparecem como `�` ou sequências corrompidas). Reproduzi os textos como estão no arquivo; a leitura "correta" (em português) foi inferida por contexto e indicada entre parênteses onde relevante.
6. **`ExibirAvisoVistoriaPorRegraDeFraude`** existe (dispara um diálogo de aviso), mas é diferente de `BloqueadoPorFraude` — não bloqueia, só avisa.
7. Variável base da API (`i.enderecos.atendimentoweb`) tem múltiplos ambientes citados no bundle: `atendimentos: ".../atendimentos/api/web-app/"`, `maxassist: "https://api.autoglass.com.br/maxassist-api/api/web-app/"`, `areaDoSegurado: "https://areadosegurado.maxpar.com"` (offset ~204600) — sugere que o mesmo front serve múltiplas seguradoras/backends via config de ambiente.

---

## Itens explicitamente NÃO ENCONTRADOS (com o que procurei)

- `ServicoAgendado` — 0 ocorrências nos 3 bundles JS.
- `BloqueadoPorFraude` — 0 ocorrências.
- `BloqueadoIlhaNormal` — 0 ocorrências.
- `GerarOrdemServicoGenesis` — 0 ocorrências.
- `sessionStorage` / `localStorage` — 0 ocorrências (só `$cookies`).
- Texto literal "finalizado" (qualquer caixa) — 0 ocorrências em `app`, `componentes`, `modules`, `common`, `util`, `base`.
- Endpoint dedicado a devolver token por placa+código/chassi/CPF para atendimento já existente — não localizado (não implica que não exista no backend, só que este SPA não faz essa chamada).
- Controle de UI que o usuário acione para definir `StatusEnvioWhatsapp=true` por telefone — não localizado; o campo só é copiado do backend.
