# SPEC-128 — A prova do Agger

> SPEC executável · 04/10/2026 · v2 (revisor cego: 68, 12 consertos aplicados) · PROGRAMA MULTICÁLCULO, passo 2. Ficha:
> `programa-multicalculo/PLANO-MESTRE-MULTICALCULO.md` §4 (SPEC-128), §1.2, §5, §8. Rito **AAA v13**, 🔴 **CRÍTICO pela soma**
> (RISCO 6) + lente do dado por gatilho. Branch
> `spec/128-a-prova-do-agger` · base `c2e0bb9`. Absorve a EXTRA-002 parte 2. Insumos: `specs-propostas/SPEC-EXTRA-002-*`
> (perícia de 22/09 e notas ao vivo de 23/09). Autorização: D-MC-23 (corretoras) + Founder 04/10 (login da Ellen até existir o
> do robô; pode calcular; **nunca apagar nada** no Agger nem na InfoCap; verba de modelo US$ 4,00 para o programa inteiro).

## 0. POR QUE ESTA SPEC EXISTE

O motor (129-B) vai calcular sozinho no Agger. Antes de construí-lo, é preciso **medir** o que ele precisa: quanto tempo o
cálculo leva, quantas ofertas vêm, quanto cada alavanca baixa o preço, se duas opções saem de um cálculo só, quantos cálculos
por dia cada corretora faz, o que a InfoCap preenche numa renovação. Hoje esses números são n = 2 (as gravações de 18/09) ou
não existem. E o motor precisa de um **contrato** (entrada, resultado aos poucos, ajuste) provado contra respostas reais —
sem dado pessoal e sem senha no repositório.

## 1. O EXECUTION CARD

```
OUTCOME ..............  o 129-B nasce de NÚMEROS: tabela de capacidade + E0–E21 respondidos (E0 E2 E3 E5 E7 E16 E20 com
                        número) + contrato do cálculo auto provado contra fixtures saneadas NA MAIN + as perguntas do portão
                        de preço (D-MC-45) prontas. Nada muda para o segurado; a corretora ganha a base da renovação feita
RISCO ................  6 — ALCANCE 3 (o cálculo usa o CPF REAL de um segurado e o registra como "cotado recentemente" em
                        📊 até 17 seguradoras) · REVERSIBILIDADE 3 (número de cálculo na seguradora, sob o código da corretora —
                        sai do prédio) · FREQUÊNCIA 0 (medição única)
SUPERFÍCIE ...........  2 — peça nova (contrato + leitor) e um gerador de fixtures sobre o redator que já existe
PISO APLICADO ........  nenhum do §3.2 no CÓDIGO (não envia, não migra, não autentica). 🧑 o VAZAMENTO em fixture versionada é
                        irreversível no histórico (a SPEC-120 teve de reescrever a main) → red team com missão de vazamento
NÍVEL ................  🔴 CRÍTICO (a soma vence) · builder Opus 5.5 xhigh fresco · juiz ‖ red team Opus 5.5 · LENTE DO DADO
                        (gatilho: o outcome é NÚMERO que a corretora vai ler, §8) · confirmação se houver blocker · 🔴 o
                        CAPTADOR (§5 U3) é revisto por agente fresco ANTES do 1º calcularV2 (a ação irreversível vem antes do juiz)
O FIO ................  §2 · TESTE DO FIO (F1, 1ª entrega, nasce VERMELHO): gravação bruta → gerador → fixture saneada →
                        leitor do contrato → 22 ofertas / 12 seguradoras (R1) e 21/11 (R2), 0 segredo na saída
PARALELISMO REAL .....  F1 (builder: scripts/agger_fixtures_saneadas.py, portal_worker/multicalculo/*, tests/fixtures/agger/*,
                        tests/test_agger_*.py) ‖ F2 (gerente, AO VIVO: só scratchpad, nenhum arquivo do repo) → F3 costura
                        (o gerente roda o gerador sobre as capturas ao vivo; o builder não toca o que F3 gera)
UNIDADES .............  U1 fixtures saneadas · U2 contrato + leitor · U3 medições E0–E21 · U4 documento da prova (§7)
COESÃO ...............  U1+U2 juntas (o formato da fixture É a entrada do leitor — uma redefine o que a outra consome, §3.4)
TIME .................  gerente (F2, F3, entrega) · 1 builder · revisor cego da SPEC (feito: 68) · revisor do captador ·
                        juiz ‖ red team ‖ lente · confirmação se blocker · atualizador
REFERÊNCIA ...........  interna: `backend/portal_worker/redaction.py` (o redator único: `redigir`, `tem_vazamento`) ·
                        `backend/tests/fixtures/infocap_contract_shapes/` (fixture de contrato já na main) · externa: §10
GATES ................  §9 (G1–G10), cada guarda novo com a MUTAÇÃO que o deixa vermelho
O ELO ................  "a fixture é segura PORQUE passou pelo gerador": A sem segredo (tem_vazamento=[]) · B gerado pelo script
                        · B→A: o DIFERENCIAL — cada valor sensível do BRUTO procurado na saída → 0 (G2). E "o leitor serve ao
                        motor PORQUE reproduz o que a tela mostrou": a contagem do leitor = a contagem independente (lente)
FAIXA DE RELÓGIO .....  💭 5–8 h de relógio (o cálculo leva 📊 413–420 s para fechar; ≈ 10–14 cálculos) · F1 ≤ 1h15 · tetos §10
```

## 2. O FIO

```
① BRUTO          docs/intake/MULTICALCULO AGGER/{RENOVAÇÃO 1,RENOVAÇÃO 2,GERAL}/*.har (fora do git, .gitignore:113)
                 + capturas ao vivo do gerente: JSONL {t,m,u,s,req,body} no scratchpad (nunca no repo)
② GERADOR        backend/scripts/agger_fixtures_saneadas.py: lê ① → PROJEÇÃO POR LISTA BRANCA (só as chaves do contrato) →
                 pseudônimo determinístico das pessoas → redaction.redigir() por cima → DIFERENCIAL contra ① → grava ③
③ FIXTURE        backend/tests/fixtures/agger/*.json + MANIFESTO.json (origem, data, nº de entradas, hash do bruto)
④ LEITOR         backend/portal_worker/multicalculo/leitor_agger.py: ler_rodada(json) → RodadaDoCalculo;
                 eventos_entre(anterior, nova) → [Evento] (nova oferta · seguradora recusou · conjunto fechado)
⑤ CONTRATO       backend/portal_worker/multicalculo/contrato.py: PedidoDeCalculoAuto · Ajuste · Oferta · RespostaDaSeguradora
                 (família E10) · RodadaDoCalculo · Evento — o que o MulticalculoProvider (129-B, D-MC-37) implementa
⑥ PROVA          backend/tests/test_agger_fixtures_sem_vazamento.py (G1) · test_contrato_do_calculo_agger.py (G3)
⑦ NÚMEROS        docs/canon/programa-multicalculo/A-PROVA-DO-AGGER.md (E0–E21, capacidade, portão de preço) · G10
```
🔴 **Por que no worker:** a imagem do worker copia só `backend/portal_worker` (`portal_worker/Dockerfile:28`) e o worker importa
📊 0 módulos de `app.*` (`grep -rln "from app\." portal_worker` → vazio); o app já importa do worker em 📊 10 arquivos
(`grep -rln "from portal_worker" app`). O adaptador da 129-B mora no worker: o leitor TEM de estar lá, senão nasce um 2º leitor
(CLAUDE.md §5). A porta `MulticalculoProvider` (API, 129-B) importa os tipos de `portal_worker.multicalculo.contrato`.
🔴 Ninguém do produto chama ④/⑤ ainda — **por desenho**: quem os liga é o adaptador da 129-B. A SPEC registra isso como pendência
de costura (P-128-xx), não como defeito.

## 3. BLOCO 0 — premissas medidas (04/10/2026)

| # | premissa | 📊 medida | comando |
|---|---|---|---|
| 1 | o login da Ellen (Resulta) está livre | sem o aviso de sessão ativa; `/cotacoes` em 52,2 s, formulário em 22,3 s | navegador vivo `--headless=new` (channel chromium), 17:3x |
| 2 | as gravações estão íntegras | 402 · 439 · 259 entradas; 28 consultas de acompanhamento em R1 e em R2; 1 `calcularV2` em R1 | `har_census.py` (scratchpad) |
| 3 | a última rodada reproduz o plano | R1: 22 ofertas (prêmio > 0) de 12 seguradoras; R2: 21 de 11 (17 seguradoras consultadas; 16 com `resultados` em R1, 27 itens — **item ≠ oferta**) | script inline sobre o HAR |
| 4 | o redator sozinho não basta | `tem_vazamento` devolve `[]` para nome de pessoa, nascimento, chassi e login de seguradora sem `@`; pega CPF | `python -c "from portal_worker.redaction import tem_vazamento…"` |
| 5 | não existe código do Agger | 3 arquivos citam a palavra, todos comentário (`infocap_connector.py:397`, `policy_data_provider.py:548…`) | `git grep -in -w agger -- '*.py'` |
| 6 | a conta da Resulta | 5 licenças (`qtdeLicenca`), 6 usuários ativos, 14 seguradoras configuradas, comissão por seguradora em `cfg/seguradora/config` | captura do login, só formas (`shape_of`) |
| 7 | o intake fica fora do git | `.gitignore:113 docs/intake/` | `git check-ignore -v` |
| 8 | Playwright local | 1.61.0 + chromium-1228 | `python -m playwright --version` |
| 9 | 🔴 o motor MUDOU de endereço desde 23/09 | a lista e o motor saem de `pdocs.aggilizador.com.br` (não mais `api.multicalculo.net`) | listener de `request` no navegador vivo |
| 10 | o token do motor dura 3 h | JWT com `iat` e `expires` (ms): 10.800 s; traz `dataLimiteCalculo` = fim da assinatura | decodificação SÓ das datas |
| 11 | falso positivo do redator | timestamp de 13 dígitos e uuid → `['cartao']`; prêmio "1234.56" e data ISO → `[]`; `<cpf#0001>` → `[]` | `python -c "…tem_vazamento…"` |
| 12 | o volume AUTO não está onde se pensava | Resulta: 841 negócios em 365 dias, só 8 AUTO (1 em 90 dias); AutoFleet: 82 AUTO em 30 dias, 1 usuária | busca/v2 paginada, só GET, só contagem |
| 13 | a autorização | D-MC-23 TOMADA (`FOUNDER-DECISIONS.md:2251`) + Founder 04/10 no chat · 7 PDFs em `APOLICES/` (`ls \| wc -l`) | — |

## 4. O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS

1. **HAR 1.2** — http://www.softwareishard.com/blog/har-12-spec/ · formato das gravações · MODELAMOS: ler `log.entries[].request/response.content.text`
   · REJEITAMOS: versionar HAR (traz cookie, header e corpo inteiros) · JUIZ: abre um HAR e confere os campos lidos.
2. **VCR.py — filtrar dado sensível na gravação** — https://vcrpy.readthedocs.io/en/latest/advanced.html#filter-sensitive-data-from-the-request
   · MODELAMOS: o filtro roda ANTES de gravar a fixture, nunca depois · REJEITAMOS: o replay de rede nos testes (o leitor é puro)
   · JUIZ: o gerador grava só depois do diferencial.
3. **Microsoft Presidio — anonimização por operador "replace"** — https://microsoft.github.io/presidio/anonymizer/
   · MODELAMOS: pseudônimo determinístico (o mesmo CPF vira o mesmo CPF sintético, para as fixtures continuarem coerentes) ·
   REJEITAMOS: detecção por NLP (usamos lista branca de chaves, determinística) · JUIZ: roda o gerador 2× e compara (idempotência).
4. **Pact — contrato a partir de interações gravadas** — https://docs.pact.io/
   · MODELAMOS: o teste do consumidor (o leitor) roda contra respostas reais gravadas · REJEITAMOS: a verificação no provedor
   (o Agger não coopera) · JUIZ: o teste do contrato lê SÓ fixture, nunca rede.
5. **Playwright — eventos de rede** — https://playwright.dev/python/docs/network
   · MODELAMOS: `page.on("response")` — o app autentica e nós só LEMOS (D-MC-28, interceptação) · REJEITAMOS: reconstruir o
   token · JUIZ: o relatório mostra que a captura ao vivo veio de `on("response")`.

## 5. AS UNIDADES

### U1 · Fixtures saneadas (builder, F1)
- **Gerador** `backend/scripts/agger_fixtures_saneadas.py` — entradas: os 3 HAR e JSONL de captura ao vivo (`{t,m,u,s,req,body}`).
  Saída em `backend/tests/fixtures/agger/`. 🔴 G2 só roda onde o intake existe (a máquina do gerente) — **declarado**; na bateria
  roda G1, que lê só a fixture.
- **Lista branca por CAMINHO COMPLETO até a folha**, por endpoint — nunca por chave de topo: o `calcularV2` carrega as 📊 17 senhas
  de seguradora em objetos que também têm a comissão. Caminho fora da lista = **descartado**. Endpoints: `calcularV2` (pedido),
  `cotacao/calculos/{id}/{versao}` (TODAS as rodadas, com `t_s` relativo ao pedido — nunca timestamp absoluto), `negocio/{id}`,
  `cotacao/versoes/{id}`, `negocio/busca/v2` (só contagens), `cfg/seguradora/config` (seguradora, ativo, QUAIS campos de código
  existem), `seguradorasRenovacao`, `fipeModelo`.
- **Pseudônimo por ORDEM DE APARIÇÃO** (o 1º valor visto vira `<cpf#0001>`, o 2º `<cpf#0002>`…), sem chave — determinístico,
  idempotente e não inversível (um HMAC com chave no repositório seria enumerável: ~10⁹ CPFs). Formato que nenhum padrão do
  redator casa (BLOCO 0 #11). Vale para CPF/CNPJ, nome de pessoa, nascimento, telefone, e-mail, placa, chassi, renavam, CEP,
  endereço, `nroCalculo`, `idIntegracao`, id de negócio/usuário/corretora (uuid → `<negocio#0001>`), e o caminho e a query de URL.
- **Toda folha numérica** de caminho sensível vira string ANTES de qualquer conferência (o redator não olha inteiro:
  `redaction.py:163`).
- **Some sempre**: `login`, `senha`, `loginWs`, `senhaWs`, `Authorization`, token, `pathPdf`/URL de PDF, `usuario` da config.
- **Comissão e desconto por seguradora** são dado comercial: na fixture viram valores CANÔNICOS (presença e tipo mantidos; o número
  real só aparece agregado no documento da prova).
- **Texto livre** (`retornoErro`, mensagens): crivo de nome (cada parte de nome de pessoa/corretora do bruto com ≥ 4 letras,
  normalizada sem acento e minúscula, é trocada) e depois `redigir()`.
- Depois: `tem_vazamento()` = `[]` ou o gerador **aborta** (timestamps e uuids já convertidos: o falso positivo do BLOCO 0 #11 some).
- 🔴 **DIFERENCIAL (G2), automático:** o conjunto procurado é TODA folha do bruto descartada como segredo ou pseudonimizada (não uma
  lista à mão), com ≥ 4 caracteres, em três formas (como veio · só dígitos · minúscula sem acento), MAIS cada parte de nome com ≥ 4
  letras, MAIS as identidades da conta lidas do próprio bruto (razão social, CNPJ e SUSEP da corretora, código de corretor, nome e
  e-mail do usuário do Agger). Achou 1 na saída → aborta e imprime só o TIPO e o caminho. Imprime `diferencial: 0 de N`. Exclui (e
  conta) valores que também são folha MANTIDA (nome de seguradora, rótulo de cobertura).
- **Nenhum nome de corretora, de funcionária ou de cliente** em fixture, MANIFESTO, código ou teste (CLAUDE.md §13.9): as contas
  são `conta_a`/`conta_b`.
- `MANIFESTO.json`: arquivo, origem (rótulo `gravacao_r1`…, nunca caminho com nome de cliente), nº de rodadas, sha256 do bruto.
- 🔴 Idempotente: rodar 2× produz bytes iguais.

### U2 · Contrato + leitor (builder, F1, mesma fatia)
- `backend/portal_worker/multicalculo/__init__.py`, `contrato.py`, `leitor_agger.py`. Sem rede, sem banco, sem import de `app.*`.
- **Por ramo:** todo tipo carrega `ramo` (📊 31 = auto no Agger); v1 implementa o auto; o residencial (E13) entra como mapa.
  Nenhum nome de corretora no código (CLAUDE.md §13.9). O cálculo **não** se chama "quote" (D-MC-37).
- `PedidoDeCalculoAuto`: os campos do `calcularV2` agrupados (segurado · veículo · pernoite · condutor · renovação/bônus ·
  coberturas · pacotes · comissão/desconto por seguradora), cada um com `obrigatorio: bool | None` (None = a 128 ainda não mediu;
  F3 preenche com E3).
- `Ajuste`: `tipo` ∈ {comissao, desconto, assistencia, carro_reserva, vidros, franquia, percentual_fipe, cobertura} + `valor`.
- `Oferta`: seguradora, pacote, prêmio total, prêmio mensal, franquia (valor, tipo), coberturas (lista branca), parcelamentos,
  `tem_pdf: bool`, `numero_calculo_presente: bool`. **Nunca** login/senha/URL de PDF. Comissão em campo separado
  `comissao_percentual` marcado INTERNO (nunca vai para cliente — o adaptador da 129-B corta).
- `RespostaDaSeguradora.familia` ∈ {OFERTA, CREDENCIAL, PERMISSAO, ACEITACAO, COMERCIAL, INSTABILIDADE, PENDENTE, DESCONHECIDA}
  (E10). As regras de classificação nascem das mensagens REAIS das fixtures; cada regra cita a fixture que a justifica.
- `RodadaDoCalculo`: `t_s`, por seguradora o estado, `fechado: bool`. `eventos_entre(a, b)` → eventos reais (a narração da
  D-MC-50 só pode nascer daqui).
- **Oferta = item de `resultados[]` com prêmio > 0** (BLOCO 0 #3: item ≠ oferta).

### U3 · As medições ao vivo (gerente, F2 — modo INVESTIGAÇÃO, §3.3)
Conta: **Resulta** (login da Ellen) e, para E0/E14/E21, também **AutoFleet** (login da Ellen da AutoFleet), cada uma só se o
login estiver livre. **Regras (Founder):** se aparecer o aviso de sessão ativa → `Cancelar` e parar naquela conta (nunca
`Prosseguir`); nunca apagar negócio, cotação ou cliente; nunca `Recalcular` negócio criado por pessoa (o teste nasce em negócio
NOVO, com a observação/nome marcando "TESTE AUTOBROKERS" se o formulário tiver campo para isso — D-MC-47); nunca tentar senha
errada (E19). Clientes de teste: só as apólices de `docs/intake/MULTICALCULO AGGER/APOLICES/` (autorizadas).
**Teto: 25 cálculos** (`calcularV2`). Plano 💭 ≈ 10–14, na conta da **Resulta** (📊 8 AUTO em 365 dias: o teste não se mistura
com o trabalho de ninguém); na AutoFleet, **0 cálculos** salvo a comparação E8/E21 (no máximo 2, autorizados pelo Founder 04/10).
🔴 **O CAPTADOR** (scratchpad, revisto por agente fresco antes do 1º cálculo) impõe as regras por máquina, não por disciplina:
`context.route` + `context.on("response")` em TODA aba (a E7 abre 2) que (1) conta e **aborta o 26º** `calcularV2`; (2) **bloqueia**
todo `DELETE` e toda rota com `exclu|delet|remov|arquiv` (E17 é só observado); (3) **recusa** `calcularV2`/salvar cujo id de negócio
esteja em `uuids_antes` (negócio de pessoa); (4) antes de cada cálculo confere que a sessão está viva (se outra pessoa entrar, a
nossa cai — e não se reentra por cima). Mutações provadas em ensaio: o 26º é barrado; um uuid de `uuids_antes` é barrado; um
DELETE é barrado. **G7** por conjunto, não por total (pessoas trabalham ao mesmo tempo): `uuids_antes ⊆ uuids_depois` e nº de
versões inalterado em todo uuid que não é de teste.
**CPF:** só os das apólices autorizadas. 🔴 Proibido CPF sintético com DV válido (pode ser de uma pessoa real).

| E | como se mede | calcula? |
|---|---|---|
| E0 | negócios AUTO (`ramo=31`) por dia, nas duas contas, pela lista (busca/v2), últimos 💭 60 dias; e renovações AUTO por dia na InfoCap | não |
| E1 | aviso de sessão; tempo do login; validade dos dois tokens (só `iat`/`exp` do JWT, nunca o token) | não |
| E2 | dados de uma apólice da InfoCap (Resulta, só leitura) × campos do formulário: quais preenche, quais faltam; % das renovações da janela com negócio anterior no Agger (cruzamento por CPF, só contagem) | 1 |
| E3 | formulário do zero: campos obrigatórios (validação da tela) e o fluxo até o Calcular | 1 |
| E4 | CPF obrigatório? DV inválido (dígitos repetidos — nunca CPF inventado com DV válido)? CPF fora do cadastro da conta (um das apólices autorizadas que a conta nunca cotou)? o que o Agger devolve pelo CPF (só os NOMES dos campos) | não |
| E5 | 2 perfis × alavancas, mudando UMA por vez (pacotes quando possível — E20): comissão, assistência, carro reserva, vidros, franquia, % FIPE; prêmio por seguradora e o tempo do ajuste | 6–9 |
| E7 | 2 cálculos ao mesmo tempo na mesma sessão (2 abas). "2 usuários robô da MESMA conta em paralelo" (§5) exige um 2º login que não existe → **parcial**, pendência, com a consequência na reserva (`worker.py:1716-1725`, um trabalho por login) | 0 extra (junto com E5) |
| E9 | tempos com n ≥ 10 lendo versões já calculadas (`tempoResposta`), sem calcular | não |
| E12 | o "Imprimir" do Agger e o PDF da seguradora (existe? formato?) | não |
| E13 | o formulário de residencial, só mapeado | não |
| E14 | por seguradora: que campos de código/documento existem em cada conta (PF/PJ) — só presença | não |
| E15 | cota de cálculos do plano; a consulta de CPF é cobrada? | não |
| E16 | comissão **e desconto** por cálculo: dá para mudar no pedido? efeito no prêmio mudando só cada um | junto com E5 |
| E17 | como se apaga um negócio (onde fica o botão, o que ele chama) — **observado, nunca executado** | não |
| E18 | o token de 3 h: o app renova? o que acontece quando vence | não |
| E19 | o bloqueio por senha errada: os campos (`tentativasInvalidasSenha`, `bloqueioPreventivo`) e a guarda que o motor terá | não |
| E20 | 2 opções (completa e econômica) num cálculo só, por "Configurar pacotes"; e as 3 opções do modelo da corretora | junto com E5 |
| E21 | quais seguradoras respondem em cada conta (Resulta pelos cálculos; AutoFleet pela config e por versões já calculadas, sem calcular) | 0–2 |

### U4 · O documento da prova (gerente, F3)
`docs/canon/programa-multicalculo/A-PROVA-DO-AGGER.md`: E0–E21 (cada um: resposta, 📊 número com data e comando/tela, o que
muda no 129-B) · **tabela de capacidade** (cálculos/dia por login, tempo até a 1ª oferta, até 80 %, até fechar; simultaneidade;
licenças) · contrato em uma página · **as perguntas do portão de preço (D-MC-45)** com os números das alavancas · a lista dos
negócios de teste criados (cliente mascarado, data, hora) para o Founder decidir apagar · as **decisões D-128-xx** (o que a medição
decidiu para o 129-B). O relatório final repete o portão de preço.

## 6. O QUE NÃO ENTRA
O robô de ponta a ponta, a porta `MulticalculoProvider`, o adaptador no `portal-worker`, a reserva de login (129-B) · ler apólice
(130-B) · nenhuma migration · nenhum envio · nenhum gasto de modelo previsto (💭 US$ 0,00; se precisar, estimativa no livro-caixa
ANTES) · apagar as gravações do intake (D-MC-35, é do Founder).

## 7. AS FATIAS
| fatia | quem | arquivos (DONO ÚNICO) | sai quando |
|---|---|---|---|
| F1 | builder | `backend/scripts/agger_fixtures_saneadas.py` · `backend/portal_worker/multicalculo/{__init__,contrato,leitor_agger}.py` · `backend/tests/fixtures/agger/*` · `backend/tests/test_agger_fixtures_sem_vazamento.py` · `backend/tests/test_contrato_do_calculo_agger.py` | G1–G4 verdes, commit por arquivo |
| F2 | gerente | só scratchpad (capturas, prints) | E0–E21 medidos, ≤ 25 cálculos |
| F3 | gerente | roda o gerador de F1 sobre as capturas (arquivos novos `vivo_*.json` em `fixtures/agger/`) · `A-PROVA-DO-AGGER.md` · `backend/tests/test_a_prova_do_agger_esta_completa.py` (G10) · ajuste de `obrigatorio` em `contrato.py` (só os valores) | G5–G10 verdes |

## 8. ATAQUES QUE O JUIZ E O RED TEAM RECEBEM
Fixture com valor do bruto (nome, CPF, placa, login de seguradora, senha, token, URL de PDF, nº de cálculo) · chave nova que a
lista branca deixa passar · gerador não idempotente · leitor com `resultados` nulo, `premio` 0/nulo/string, seguradora sem
`retornoErro`, rodada vazia, rodada fora de ordem · evento duplicado entre rodadas iguais · família DESCONHECIDA escondida · nome de
corretora no código · número do documento da prova sem comando · cálculo acima do teto · negócio de pessoa recalculado.

## 9. GATES
| # | gate | comando | MUTAÇÃO que o deixa vermelho |
|---|---|---|---|
| G1 | toda fixture: `tem_vazamento=[]` em TODA profundidade; caminhos ⊂ lista branca; nenhum nome de corretora | `pytest backend/tests/test_agger_fixtures_sem_vazamento.py` | numa CÓPIA: `"senha":"x"` aninhado / CPF / caminho fora da lista / nome de corretora → FAIL; CONTROLE: fixture limpa → PASS |
| G2 | diferencial contra o bruto = 0 (só na máquina com intake — declarado) | `python backend/scripts/agger_fixtures_saneadas.py --conferir` | desligar o pseudônimo do nome → o diferencial acusa o caminho |
| G3 | leitor: R1 = 22/12, R2 = 21/11; 0 chave proibida em `Oferta`; famílias classificadas | `pytest backend/tests/test_contrato_do_calculo_agger.py` | trocar `premio > 0` por `resultados` não vazio → 27 ≠ 22 |
| G4 | idempotência do gerador | rodar 2× + `git diff --stat` vazio | ordem de aparição embaralhada → diff |
| G5 | as fixtures ao vivo passam G1/G2 | G1/G2 sobre `vivo_*` | a mesma de G1, sobre uma `vivo_*` |
| G6 | cálculos ≤ 25, por máquina | o captador aborta o 26º · contagem de `POST calcularV2` nas capturas no relatório | teto 0 num ensaio → o 1º é barrado |
| G7 | nada apagado; nenhum negócio de pessoa tocado | `uuids_antes ⊆ uuids_depois` + versões inalteradas fora do conjunto de teste | DELETE e uuid alheio barrados pelo captador (ensaio) |
| G8 | polícia do protocolo e py_compile | `pytest backend/tests/test_o_protocolo_tem_policia.py` | — (guarda antigo, já com controle) |
| G9 | os números do documento conferem por caminho independente | lente do dado (recontagem própria nas capturas e nas fixtures) | — (é a própria conferência) |
| G10 | o documento da prova está completo | `pytest backend/tests/test_a_prova_do_agger_esta_completa.py` (E0–E21 presentes; 📊 com comando em E0 E2 E3 E5 E7 E16 E20) | apagar o 📊 da E16 numa cópia → FAIL |

## 10. O QUE SAIU
(preenchido na entrega: o que ficou de fora e por quê, com a pendência P-128-xx de cada um)
