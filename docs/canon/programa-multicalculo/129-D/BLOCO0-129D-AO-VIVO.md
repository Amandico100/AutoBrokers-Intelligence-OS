# BLOCO 0 da SPEC-129-D · M6 — o Agger AO VIVO (vida individual) · **INTERROMPIDO**

> 🔍 Medidor ao vivo (Opus 5.5) · 16/10/2026, 06:51–07:14 UTC (03:51–04:14 BRT), relógio desta máquina · branch `spec/129-D-vida`, HEAD `fa6e13e`.
> Conta: `agger-da-corretora` da corretora B (`f64ea768…`, `cotador@`, `uso=global`), credencial do COFRE do produto
> (`robos.candidatos` + `portal_worker.vault.decrypt`, a chave de produção só no processo), lease do robô tomada por CAS
> (`robos.adquirir`, dono `bloco0-129d:…`) e solta no fim. Guarda de PRODUÇÃO (`agger_guarda`) + embrulho: `calcularV2` só passa
> ARMADO e no máximo 1 vez (provado antes, fora do ar: sem armar → `medicao_calcular_nao_armado`; armado → 1 passa, o 2º barra;
> `?salvar=true` → `salvar_rascunho`). Script e saídas fora do git: `scratchpad/129d-m6/sessao_viva.py`.
> ⛔ Sem dado pessoal, sem senha, sem token. 📊 medido · 💭 estimativa.

## 0. Em uma tela
| | resultado |
|---|---|
| cotação de vida (`calcularV2`) | entradas 1–2 (Resulta): 📊 0 · **entrada 3 (AutoFleet, §5): 📊 1, HTTP 201, 0 de 7 com preço** |
| negócio de teste criado no Agger | Resulta: nenhum · **AutoFleet: 1** (`2a560ecf-c182-4adc-abc6-9d60d6e2d6e9`, §5) |
| corpo, resultado, formulário ao vivo | **medidos na entrada 3 (AutoFleet, §5)** → as 3 fixtures `agger_ramos/vida_*.json`; resposta COM PREÇO ainda não (7 de 7 "instabilidade") |
| AutoFleet (seguradoras de vida, formulário de AP/Mobi) | **medido na entrada 3 (§5)**: 8 seguradoras de vida; SURA fora do AP |
| 🔴 sessão aberta deixada no Agger | **SIM, provável**: a 1ª entrada logou e não saiu (ver §1); a 2ª viu o aviso de sessão ativa e cancelou |
| o que se salvou | o formulário de vida **no código público do app** (§3: códigos, caminhos no corpo, profissão por seguradora, agenciamento) — FATO do código, não do servidor |

## 1. O que aconteceu, entrada a entrada
| entrada | relógio (UTC) | o que houve | trocas de token (`login/pdocs`) | `calcularV2` | logout |
|---|---|---|---|---|---|
| **1** | 06:51:52 → morta 07:11:36 | o login **entrou** (a pilha do processo, `python -m asyncio pstree`, mostrava `Sessoes._entrar → _completar_licenca`, que só roda depois de `/cotacoes` + tokens) e **travou ali**: o MEU ouvinte de rede lia o corpo da mesma resposta `GET /usuario/current` que o `_ler_licenca` do produto já lia — 2 leituras do mesmo corpo → as duas `Response.body()` esperaram para sempre. 20 min parado; processo morto; lease solta à mão (📊 `robo_dono: None, estado: ativo`) | não registrado (o processo morreu antes de gravar) · 💭 2, o padrão do app | 📊 0 (nunca armado) | **NÃO** — sem página viva para clicar "Sair" |
| **2** | 07:13:08 → 07:13:51 | ouvinte consertado (não lê corpo de `/usuario/*` nem de OPTIONS). 📊 `POST api-prod/usuario/login` → **201** às 07:13:50 e o **aviso de sessão ativa** → o `Sessoes.obter` do produto clicou **só "Cancelar"** (`SessaoOcupada`) → PAREI | 📊 0 | 📊 0 | não se aplica (não entrou) |

🔴 **CORRIGIDO pela entrada 3 (§5): a trava é do PRODUTO, não do meu ouvinte.** Na entrada 3 o ouvinte já não lia nenhum corpo de
`/usuario/*`, e a pilha (`python -m asyncio pstree <pid>`) mostrou de novo **só** a tarefa do produto parada:
`Sessoes._completar_licenca → _ler_licenca → Response.json → Response.body` (agger_sessao.py:288/332), 16 min sem voltar.
📊 2 de 2 logins de hoje nesta máquina (Windows, Python 3.14, Chromium headless local). `_completar_licenca` faz
`await asyncio.gather(*leituras)` **sem prazo** → se um corpo não chega, o `obter` nunca devolve a sessão e o robô fica logado,
parado, sem logout. 💭 Não sei se acontece no contêiner Linux do worker (o canário 129-C de 11/10 é anterior ao conserto C2 da 131-A,
que criou essa leitura). RECOMENDAÇÃO ao gerente: prazo (`asyncio.wait_for`, ~5 s) no `gather` das leituras da licença — a licença
é aviso, nunca pode prender o login.

### O que a sessão aberta faz (e o que o Founder faz)
- 💭 A sessão da entrada 1 fica aberta no servidor até o Agger a vencer (o vencimento NÃO é medido — P-128-01; o A-PROVA §10 viu o
  aviso reaparecer 3 h depois de uma sessão fantasma).
- Enquanto isso, o motor de produção, se pegar este robô, verá o mesmo aviso → `SessaoOcupada` → marca a conta `ocupada` 30 min e
  tenta de novo (`robos.TRANSICOES_DO_MOTOR`). 📊 Nenhum cálculo em andamento no banco às 06:49 UTC (último `multicalculo_calculos`
  de 13/10) e 📊 `renovacoes` = 0 linhas: hoje ninguém depende deste robô.
- 🧑 Para limpar já: entrar no aggilizador.com.br com o `cotador@` da corretora B → no aviso "já há uma sessão ativa", **Prosseguir**
  → depois **Sair** (menu do usuário, canto superior direito). A sessão fantasma é do robô, não de uma pessoa.

## 2. O que NÃO foi medido (e o que cada item exige)
1. O corpo exato do `calcularV2` de vida (chaves de `cotacao`, `configuracoes`, itens por seguradora, comissão, `percAgenciamentoVida`) → 1 cotação ao vivo.
2. A resposta de vida (prêmio, capital, coberturas ecoadas, rótulos, recusas por seguradora) → a mesma cotação.
3. Os 47 campos na tela da conta (os 24 fora da fixture) e a resposta da busca de profissão (`getOptionsBySegFull?executionType=9`) → sessão ao vivo, sem calcular.
4. As seguradoras de vida habilitadas e comissão/agenciamento padrão, nas DUAS contas (`GET calculo/seguradoras` ∩ `app/seguradoraStatus.vidaStatus`).
5. Mobi: se a SURA aparece no formulário de Acidentes Pessoais da AutoFleet (`acidentesPessoaisIndividualStatus`).
→ 💭 Refazer depois que a sessão fantasma sair (Founder §1, ou o vencimento), com o `sessao_viva.py` consertado. O rito: 1 entrada por
conta, o comando `cmd/NNN.py` por passo, logout pela tela, `calcularV2` armado uma vez.

## 3. O formulário de vida NO CÓDIGO do app (FATO do JS público, sem login — não é gravação)
Fonte: `curl https://aggilizador.com.br/login` → `main-CXWGZUOJ.js` + 158 chunks (3 rodadas de `grep -o 'chunk-[A-Z0-9]{8}\.js'`), 16/10
03:43 BRT. O formulário de vida mora em `chunk-JH62WK2I.js`; o status por seguradora em `chunk-LWOFFNIV.js`/`chunk-6OMK5F6Y.js`.
Comando-base: `grep -o '.\{300\}isFumante.\{300\}' chunk-JH62WK2I.js` e o extrator do rascunho (`static{this.<lista>=` antes de
`static get executionType(){return 9}`).

| campo | códigos / forma (do código) | caminho no rascunho (`preencheDraft`) |
|---|---|---|
| `ramo` | `valoresEstaticosDraft = {ramo: 91}` | `cotacao.ramo` |
| `sexo` | `F` Feminino · `M` Masculino | `segurado.sexo` |
| `estadoCivil` | 1 Solteiro(a) · 2 Casado(a) · 3 Separado(a) · 4 Divorciado(a) · 5 Viúvo(a) · 6 União Estável | `segurado.estadoCivil` |
| `isFumante` | `simOuNao`: `true` Sim · `false` Não (sem padrão, `required`) | **`configuracoes.fumante`** |
| `rendaMensal`, `altura`, `peso` | renda obrigatória (máscara de moeda); altura `×100` (cm), peso inteiro | `segurado.rendaMensal/altura/peso` |
| `praticaEsporteRadical` | lista de 📊 49 esportes, **0 = "Não contratado"** (o padrão da tela, `informacoesDefault.perfil`); vai o `value` | `configuracoes.praticaEsporteRadical` |
| `profissao` | 🔴 **por seguradora**, como a atividade do empresarial: busca `getOptionsBySegFull(executionType=9, texto ≥ 3)` → o corretor escolhe UMA opção por seguradora (`selecionarProfissao(opção, seguradoraId)`); seguradora sem profissão escolhida sai do cálculo ("Não é possível calcular nesta seguradora porque não há uma profissão selecionada") | rascunho `buscaPorSeguradora.profissao = {seguradoraId: {Key, Value}}` (tirado antes do envio) → no item: `valoresAjusteSeguradora.profissao` (lido de volta por `preencheProfissoesSelecionadas`) |
| `assistMorte` (capital de Morte, obrigatório) | faixas 30 mil–300 mil (passo 10 mil) · 325 mil–1 mi (50 mil) · 1,1–2 mi (100 mil); padrão da tela **50 mil** | **`configuracoes.isAppMorte`** |
| `isAppMorteAcidental` · `isAppInvalidez` · `isInvalidezDoenca` | 0–2 mi nas mesmas faixas; padrão 0 | `configuracoes.<mesmo nome>` |
| `isDespesasMedicasHospitalares` (DIH) | diárias 0–100 (25) · 150–400 (50) · 500–1.300 (100) | `configuracoes.isDespesasMedicasHospitalares` |
| `valorDIT` | diárias, idem | `configuracoes.DIT = {qtdDiarias: null, valor}` |
| `valorDoencasGraves` | 0–2 mi | `configuracoes.isDoencasGravesGrupo = {qtdDoencas: null, valor}` |
| `assistFuneral` | 0 Sem Assistência · 1 Individual · 2 Familiar (padrão 0) | `configuracoes.funeral = {tipo, valor: null}` |
| `vigenciaIni` | data | `vigenciaIni` |
| **Agenciamento %** | campo da etapa Vigência (0–999), replicado a TODAS as seguradoras (`setarAgenciamentos`) | **`calculos[].percAgenciamento`** — só nos ramos VIDA, VIDA_GLOBAL e ACIDENTES_PESSOAIS (padrão `t.percAgenciamento ?? 0`) |
| comissão | a tela exige comissão em toda seguradora marcada ("É necessário informar a comissão de todas as seguradoras selecionadas") | `calculos[].percComissao` (o mesmo campo do auto/RE) |

Outros fatos do código: o envio é o MESMO `POST calculo/calcularV2` `{cotacao, negocio, correlationId, corretoraId?}` sem query (o
`?salvar=true` é só "Salvar"); depois a tela lê `GET pdocs calculo/cotacao/calculos/{idIntegracao}/{versao}` a cada 5–30 s até tudo
pronto. O status global por seguradora é `app/seguradoraStatus` com a chave **`vidaStatus`** (vida individual), `vidaGlobalStatus` e
**`acidentesPessoaisIndividualStatus`** (AP). O formulário de AP busca profissão em `executionType` **9 e 13** e junta. A lista
estática de 📊 136 profissões do código **não é usada** no envio (`objSelects.profissoes: void 0`) e não tem "Analista de sistemas".
⚠️ Tudo isto diz o que a TELA monta; o que o servidor aceita, os rótulos do resultado e as recusas só a cotação ao vivo diz (§2).

## 4. O que ficou no mundo
- Agger: 📊 0 cálculo, 0 negócio, 0 escrita fora de login (2 `POST usuario/login`, um por entrada). 1 sessão do robô possivelmente aberta (§1).
- Banco: só a lease do robô (`portal_accounts.robo_dono/robo_batida_em`), tomada e solta nas duas entradas (📊 `robo_dono: None, estado: ativo` depois).
- Repositório: só este laudo. Nada commitado.

## 5. Entrada 3 — AutoFleet (decisão do gerente: nota 75 × esperar a sessão da Resulta 60)
> 📊 16/10/2026, 07:18:17 → 07:48:16 UTC. Conta `agger-da-corretora` da AutoFleet (`624cc84d…`, robô `uso=global`), credencial do
> cofre, lease por CAS (solta no fim: 📊 `lease_liberada: true`). A conta da Resulta **não foi tocada**. Dados do segurado: os de TESTE
> do pacote (nome "TESTE AUTOBROKERS", **CPF GERADO** com dígito válido — semente fixa, não é de pessoa conhecida —, 10/05/1985, M,
> casado, CEP 89201-000, não fumante, renda R$ 8.000, esporte "Não contratado", capital de Morte R$ 100.000, vigência 17/10/2026).

### 5.1 Em uma tela
| | resultado |
|---|---|
| login | 📊 entrou, e **travou na leitura da licença do produto** (§1, corrigido) por 16 min. Destravei SEM matar: `sys.remote_exec` (Python 3.14) cancelou só a tarefa `_ler_licenca` e, como o laço estava ocioso, derrubei o renderer da aba (`Stop-Process` no `chrome-headless-shell --type=renderer`) para um evento acordar o Python; o `gather(return_exceptions=True)` devolveu e o `obter` entregou a sessão (📊 `login_em 07:34:38Z`, `login_s 975`). Abri uma aba NOVA no MESMO contexto (a guarda é do contexto; as credenciais do app moram no `localStorage`, `getCredenciais`) → `/cotacoes` logado. ⚠️ Essa recarga é **fora do rito**: trocas de token = 📊 **4** (`login/pdocs` 201 ×4; o teto do rito é 2) |
| aviso de sessão ativa | 📊 não apareceu |
| seguradoras de vida (global ∩ conta) | 📊 **8**: Allianz 5 · Bradesco 1 · HDI 4 · Mapfre 3 · Porto 8 · Tokio 11 · Yelum (Liberty Site) 12 · Zurich 7 — todas `ativo` e `credenciaisValidas` |
| global `vidaStatus == 1` (`GET pdocs/app/seguradoraStatus/`) | 📊 13: Bradesco 1 · Mapfre 3 · HDI 4 · Allianz 5 · Zurich 7 · Porto 8 · Tokio 11 · Liberty Site 12 · SulAmérica 17 · Icatu 25 · Unimed 33 · MetLife 34 · Centauro 40 |
| comissão / agenciamento padrão na conta (`GET api-prod/calculo/seguradoras`) | 📊 `percComissaoVida` **0** e `percAgenciamentoVida` **0** nas 8 (HDI não tem a chave `percAgenciamentoVida`) |
| `calcularV2` | 📊 **1** · **HTTP 201** · `{idIntegracao, versao: 1}` · sem query · clique 07:40:46Z (relógio desta máquina; o servidor gravou `dataHoraEnvio 07:39:33Z` — 📊 ~73 s de diferença, como na 129-C) |
| resultado | 📊 **0 de 7 com preço**: as 7 voltaram `retorno=true, retornoErro=true, premio 0`, sem `resultados`, com a MESMA frase — *"A seguradora está apresentando instabilidade no momento. Por favor, tente novamente mais tarde."* — ≈ 6,5 min depois do clique (58 leituras de `calculos/{ref}/1` pela própria tela). Nenhuma 2ª tentativa (regra) |
| Acidentes Pessoais (sem calcular) | 📊 a tela lista **Allianz · HDI · Mapfre · Porto · Yelum**; **a SURA NÃO aparece** — e o global dá `acidentesPessoaisIndividualStatus = -1` para a SURA (24), embora ela esteja ativa na conta → **MOBI fora de vez** (D-129D-03 confirmada) |
| logout | 📊 pela tela, `deslogaSessao` **201** às 07:48:16Z |
| guarda | 📊 barradas 68: `escrita_fora_da_api` 50 · `leitura_fora_do_agger` 11 · `leitura_destrutiva` 5 · `escrita_fora_da_lista_branca` 2 (`postResearchUri` do app); `calcularV2` 1, `prosseguir` 0 |
| **negócio de TESTE criado** (para o Founder apagar, se quiser) | AutoFleet · `idIntegracao` **`2a560ecf-c182-4adc-abc6-9d60d6e2d6e9`** · `negocioId` `ab5f3c40-10f1-4caa-a22f-63a9f6579704` · versão 1 · criado 16/10 07:39:32Z · segurado "TESTE AUTOBROKERS" |

### 5.2 O formulário (📊 DOM da tela, `vida_formulario.json`)
Uma página só (sem etapas): **24 campos com nome** + 1 seletor "Replicar para" + o painel de seguradoras (a fixture antiga dizia "47
campos": contava todo input da página, como nos outros ramos). Obrigatórios na tela: `cpf, nome, dataNasc, sexo, estadoCivil, cep,
isFumante, rendaMensal, praticaEsporteRadical, vigenciaIni, assistMorte` (11) — `profissao` aparece como "Busca por profissão*", mas
é por seguradora (sem ela, a seguradora sai). Padrões ao abrir: esporte "Não contratado", vigência = hoje, Agenciamento 0, coberturas
R$ 0,00, funeral "Sem Assistência"; seguradoras marcadas ao abrir: só **Bradesco e HDI** (as outras desabilitadas até haver profissão);
a tela **exige comissão > 0** em toda seguradora marcada ("O campo Comissão é obrigatório" com 0).
🔴 **A tela replica o capital de Morte para Morte acidental e IPA** (`controlerCampos.REPLICAR_COBERTURAS`): digitei só a Morte
(R$ 100.000) e o corpo saiu com `isAppMorteAcidental 100000` e `isAppInvalidez 100000`. → a opção "mais em conta" (só Morte) tem de
mandar MA/IPA = 0 EXPLÍCITOS; o robô não pode copiar o que a tela faz.

### 5.3 A profissão (📊 `GET pdocs/calculo/getOptionsBySegFull?executionType=9&filterText=Analista%20de%20sistemas`)
Forma: `[{seguradora, KeyValue: [{Key, Value, Description}]}]`, 📊 13 blocos (as 13 do global de vida). O que a tela escolheu:
| seguradora | opções | escolhida | casamento |
|---|---:|---|---|
| HDI 4 | 1 | "Analista de sistemas" (Key 10183) | exato |
| Porto 8 | 1 | "ANALISTA DE SISTEMAS" (Key 3023) | exato (caixa) |
| Allianz 5 | 1 | "Analista de sistemas de automação" (3201198) | ⚠️ aproximado — a única opção |
| Tokio 11 | 1 | "Analista de sistemas de automação" (1409) | ⚠️ aproximado |
| Yelum 12 | 1 | "Analista de sistemas de automacao" (212415) | ⚠️ aproximado |
| Zurich 7 | 1 | "Analista de sistemas de automação" (532) | ⚠️ aproximado |
| Mapfre 3 | 0 | — ("Pesquisa não encontrou nenhuma profissão") | ficou FORA do cálculo |
| Bradesco 1 | (sem bloco) | — | não exige profissão: entra marcada |
→ 💭 Para a D-129D-06 ("casamento inequívoco"): "única opção" ≠ "mesma profissão". Em 4 de 6 a única opção era OUTRA profissão
(automação). A regra precisa de igualdade normalizada, não de "só uma opção voltou".

### 5.4 O corpo (📊 `vida_calcularV2_corpo.json`)
| chave | valor gravado (saneado) |
|---|---|
| envelope | `{cotacao, negocio: null, correlationId}` — sem `corretoraId` |
| `cotacao.ramo` · `tipo` · `integracaoInfo` | 91 · 5 · 1 |
| `cotacao.vigenciaIni` | ISO UTC com a hora herdada (`…T17:47:20.353Z`, a mesma hora vista nos RE da 129-C) |
| `cotacao.segurado` | `nome, cpfCnpj (só dígitos), estadoCivil 2 (número), dataNasc ISO, sexo "M", cep (dígitos), uf, cidade, bairro, logradouro (do CEP), fone, fone1, email, altura null, peso null, rendaMensal 8000 (número)` — **sem profissão** |
| `cotacao.configuracoes` | `fumante false · praticaEsporteRadical 0 · isAppMorte 100000 · isAppMorteAcidental 100000 · isAppInvalidez 100000 · isDespesasMedicasHospitalares 0 · isInvalidezDoenca 0 · funeral {tipo 0, valor null} · DIT {qtdDiarias null, valor 0} · isDoencasGravesGrupo {qtdDoencas null, valor 0}` + restos de RE nulos (`imovelCep, imovelAlarme, rouboCondomino, sisProtecaoIncendRoubo`) |
| `cotacao.calculos[]` | 📊 7 itens (as marcadas); config da seguradora (credenciais → redigidas) + `percComissao 10` (escolha do TESTE) + `percDesconto 0` + **`percAgenciamento 0`** + `percAgenciamentoVida 0` (da config) + **`valoresAjusteSeguradora.profissao {Key, Value, Description}`** (6 de 7; Bradesco `null`) |

### 5.5 Arquivos
`backend/tests/fixtures/agger_ramos/vida_formulario.json` · `vida_calcularV2_corpo.json` · `vida_resultado.json` (1 item pendente de
amostra, os 7 itens finais com a recusa e a versão gravada). Saneamento (`scratchpad/129d-m6/sanear.py`): CPF → `<cpf#1>`, nome →
`<nome#1>`, CEP → `<cep#1>`, endereço → `<endereco#n>`, ids → `<id#n>`, config/credencial das seguradoras → `<redacted:…>`.
📊 Varredura do gravador (CPF, nome, e-mail, CEP 8920x, `bearer`/senha em claro) = **0** nos 3; `grep -c -i "autofleet|cotador|ellen|amandus"`
= 0 (o único "resulta" é a palavra "resultados").

### 5.6 O que ainda NÃO está medido
1. **Uma resposta de vida COM PREÇO**: os rótulos de prêmio, capital e coberturas ecoadas que o leitor terá de ler. 📊 Hoje às 07:4x
   as 7 seguradoras deram a mesma "instabilidade". 💭 Uma frase idêntica nas 7 parece erro do Agger/integração (ou a hora: madrugada),
   não recusa de risco; a regra proíbe a 2ª tentativa aqui. Fica para o canário da V3 (D-129D-11), em horário comercial.
2. As seguradoras de vida da **Resulta** (a sessão aberta da entrada 1 impede, §1).
3. A trava da licença no contêiner Linux (§1).
