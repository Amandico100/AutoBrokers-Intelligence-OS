# SPEC-074 — Portal de Vidros Maxpar/Autoglass ponta a ponta

**Relatório de execução** · 16/08/2026 · branch `feat/spec074-vidros-ponta-a-ponta`

| | |
|---|---|
| Commit base | `ffd1cd9` (head da SPEC-073) |
| Commit final | `190bc2d` |
| `origin/main` | `190bc2d` — fast-forward, 8 commits, 0 atrás |
| Commits | 8 (feature + docs + 1 merge da correção da cedilha da 073) |
| Diff | 20 files changed, 3944 insertions(+), 1 deletion(-) |
| Migrations | **nenhuma** |

---

## 1. O que a SPEC-074 entrega, em uma frase

O portal de vidros deixa de ser uma tela que o robô adivinha e passa a ser **um
contrato conhecido**: onde estão as duas fronteiras que criam coisa no mundo,
como se descobre que **não há cobertura antes de escrever qualquer coisa**, e o
que o segurado ouve quando o pedido dele existe mas o job caiu.

A frase que a 074 apaga do produto é **"não consegui abrir"** dita a alguém cujo
pedido já está aberto — a pior frase possível, porque convida a pedir de novo, e
o portal cobra por atendimento.

---

## 2. Método: por que este trabalho é medição, não leitura

📊 A base factual é a mineração de **58 MB de HAR** capturados do portal real, não
a leitura da tela nem a SPEC escrita antes da captura. Isso mudou conclusões:

- O portal é **API-first nativo** — AngularJS sobre 34 endpoints REST em
  `https://api.autoglass.com.br/atendimentos/api/web-app/`. O DOM é fachada.
- Existem **duas** fronteiras transacionais, não uma.
- A **ausência de cobertura chega num HTTP 400**, antes de qualquer escrita.
- O motor de perguntas é **stateless**: o cliente reenvia o acumulador inteiro a
  cada rodada, e `204 No Content` significa "acabou".

⚠️ **Uma afirmação minha foi corrigida no meio do caminho.** Eu havia relatado
"`TipoAtendimento` é null em 100% dos casos — fato negativo", com base apenas no
HAR da Yelum. O HAR da Porto mostrou `1` e `2`. A SPEC estava certa e eu tinha
generalizado de dado parcial. O código hoje tem `tipo_atendimento_para()`,
restrito à Porto, que era o que a evidência completa suportava.

---

## 3. Arquitetura — seis módulos, cada um com uma pergunta só

| Módulo | Linhas | A pergunta que ele responde |
|---|---|---|
| `journeys/vidros_api.py` | 370 | *O que o portal respondeu, e isso me deixa escrever?* |
| `journeys/vidros_sessao.py` | 251 | *Como eu falo com o portal sem virar um segundo runtime?* |
| `journeys/vidros_estado.py` | 290 | *O que existe na seguradora agora?* |
| `journeys/vidros_questionario.py` | 295 | *Qual é a próxima pergunta, e eu sei respondê-la?* |
| `journeys/vidros_apifirst.py` | 258 | *Dá para fazer tudo isso sem tela?* |
| `services/vidros_flow.py` | 249 | *Isso é caso de portal? É um pedido ou dois?* |

`vidros_sessao.py` segue o padrão da casa — `page.evaluate` com `fetch` de dentro
da página, como Yelum `_api`, MAPFRE `_api`, Tokio `_fetch_json` e Zurich `_api`.
**Nenhum motor paralelo foi criado**: sem cliente HTTP novo, sem runtime novo, sem
registry novo. As journeys entram no `JOURNEYS` existente.

---

## 4. As duas fronteiras materiais (o coração da SPEC)

```
   preflight ─────────────► GET apólice
   READ_ONLY                classificar_preflight() → 5 estados
                            só policy_ok tem pode_escrever = True
        │
        │  ◄── cobertura AUSENTE sai por aqui, num 400, sem ter escrito nada
        ▼
   FRONTEIRA 1 ───────────► POST /atendimentos
   MATERIAL                 → NumeroProtocolo (16 dígitos, interno) + Token
        │
        ▼
   questionário ──────────► POST /questionarios (stateless, acumulador inteiro)
   iterativo                204 No Content = acabou · MAX_RODADAS = 12
        │
        ▼
   FRONTEIRA 2 ───────────► POST /questionarios final
   MATERIAL                 → CodigoAtendimento (8 dígitos) — o número da TELA,
                              o que o segurado repete no telefone
```

Cada fronteira é **nomeada** ao guard da SPEC-073 (`FRONTEIRA_ABRIR`,
`FRONTEIRA_MATERIALIZAR`), com checkpoint `armed` **antes** do POST. O guard
recusa uma fronteira quando a esperada era a outra — mesmo sendo as duas
materiais e legítimas.

**Falha depois do POST não vira retry.** Vira `DESCONHECIDO` / `maybe_committed`,
e quem reconcilia é o Vigia. Retentar aqui é abrir o segundo pedido.

---

## 5. Máquina de estados — 8 estados, e o que cada um autoriza

| Estado | `safe_to_retry_open` | O que o segurado ouve |
|---|---|---|
| `pre_protocolo` | ✅ **sim** | — (nada existe ainda) |
| `protocolo_criado` | ❌ | "foi aberto, número X" |
| `atendimento_materializado` | ❌ | o número de 8 dígitos |
| `aguardando_escolha_do_segurado` | ❌ | convite a escolher a loja |
| `desconhecido` | ❌ | "FOI aberto, não consegui ler o número. **Não reexecute.**" |
| `cancelado` | ❌ | — |

**Um único estado libera reabrir.** A matriz de mutação M3 prova isso: forçar
`safe_to_retry_open = True` acende 5 vermelhas.

---

## 6. O roteador de canal: exclusão antes de inclusão

`resolver_canal()` tira a decisão de quatro lugares (prompt,
`insurer_dispatch_tool`, `portal_tool`, playbook) e põe numa regra só.

📊 O caso que motiva a ordem: *"quebrei o vidro na colisão"* tem as duas palavras.
O que manda é a **colisão** — isso é sinistro, não vidraçaria. Inclusão antes de
exclusão mandaria ao portal errado um caso que precisa de regulação.

E `separar_itens()` é **deliberadamente conservador**. O portal diz, em todas as
telas, que permite *"apenas a SELEÇÃO DE 1 (UM) ITEM POR ATENDIMENTO"*. Então
"motorista e carona" vira dois pedidos — mas plural vago ("quebraram os vidros")
devolve **um** item e deixa a pergunta para o atendente. Abrir dois pedidos por
interpretação de plural seria pior, e cada atendimento é cobrado.

---

## 7. Cuidado com o número de entradas nos portais

> Preocupação levantada explicitamente pelo Founder: *"o cuidado com o número de
> entradas dentro dos portais das seguradoras para não sermos bloqueados"*.

O que a 074 faz a respeito:

- **`MAX_CHAMADAS = 150`** por sessão em `vidros_sessao.py`, teto rígido.
- **`MAX_RODADAS = 12`** no questionário — um questionário que não converge para
  e pede humano, em vez de girar.
- **Preflight read-only barato antes de tudo**: a consulta de apólice descarta o
  caso sem cobertura sem abrir sessão de escrita.
- **O caminho API-first, quando ligado, reduz drasticamente as requisições**: uma
  chamada REST no lugar de uma navegação de tela com todos os seus assets.
- **A idempotência impede a segunda entrada**: chave `v2` incluindo o lado
  (P-79), e nenhum estado com pedido existente é retentável.

⚠️ **O que a 074 NÃO faz** e fica em PENDÊNCIAS: não existe rate-limit global por
portal por janela de tempo, nem backoff coordenado entre jobs concorrentes da
mesma corretora. Os tetos acima são **por sessão**, não por portal por hora.
Dez jobs simultâneos da mesma corretora são dez sessões, cada uma com seu teto.
Isso é trabalho de SPEC-075 (Capability Factory) e está registrado como tal.

---

## 8. Segurança

**Allowlist de host fechada.** A versão inicial usava `f"//{h}" in url`, e
`https://api.autoglass.com.br.evil.com/x` passava. Corrigida para extração real
de hostname com comparação por sufixo de ponto:

- ✅ `api.autoglass.com.br` passa · `app.abraseuatendimento.com.br` passa
- ❌ `api.autoglass.com.br.evil.com` recusado
- ❌ `169.254.169.254` (metadata de nuvem) recusado

**Fixtures sanitizadas.** 📊 Medido em 16/08 sobre `backend/tests/fixtures/vidros/`:
0 CPF formatado, 0 CNPJ formatado, 0 nomes originais, 0 chassis, 0 placas reais,
0 protocolos reais. O único e-mail é `teste@exemplo.com.br`, sintético.

**Multi-tenant.** A 074 não adiciona query nova a tabela multi-tenant. A chave de
idempotência inclui `company_id` — corretoras diferentes nunca colidem (provado
na V10).

---

## 9. Testes — 243 asserções novas

| Suite | Asserções |
|---|---|
| `test_spec074_vidros_api.py` | 87 |
| `test_spec074_vidros_fluxo.py` | 49 |
| `test_spec074_vidros_mutations.py` | 62 |
| `test_spec074_a_fronteira_material_executada.py` | 29 |
| `test_o_que_esta_no_ar_e_conferivel.py` | 16 |
| **total 074** | **243** |
| SPEC-073 (mantidas verdes) | 390 |

### 9.1 As seis mutações

📊 Rodadas em 16/08, cada uma restaurada por cópia de arquivo:

| # | Mutação | Vermelhas |
|---|---|---|
| M1 | preflight libera escrita em `coverage_absent` | 2 |
| M2 | questionário escolhe pela **posição** (1ª opção) | 3 |
| M3 | atendimento materializado vira retentável | 5 |
| M4 | roteador manda tudo ao portal (colisão junto) | 2 |
| M5 | chave de idempotência ignora o **lado** (P-79) | 1 |
| M6 | a flag API-first nasce **ligada** | 1 |
| M7 | guard sem checkpoint volta a ser **fail-open** | 3 |
| — | restaurado | **0** |

### 9.2 Cada bloco prova três coisas, não duas

O caso bom passa · o ruim é negado · **e os dois são diferentes**. Sem a
terceira, uma função que devolve sempre a mesma resposta passaria nas duas
primeiras — foi exatamente assim que a mutação #4 da SPEC-073 escapou da minha
matriz na primeira rodada.

### 9.3 A linha de controle

Uma bateria de negações não prova que o sistema ainda faz o trabalho. As 8
asserções finais provam que a 074 **não virou "nega tudo"**: apólice válida ainda
libera escrita, peça de vidro ainda vai ao portal, um item ainda é um pedido, o
questionário completo ainda chega ao 204.

---

## 9.4 Os juízes críticos, e o que eles acharam

Dois juízes adversariais rodaram sobre o código pronto e a bateria verde. Os dois
acharam defeito real. **Nenhum dos dois pôde medir** — um rodou sem shell — então
verifiquei cada achado no código antes de tocar em qualquer coisa.

**O juiz dos testes** apontou que os blocos V12 e V13 provavam a orquestração por
`inspect.getsource()`. 📊 Medi a mutação que ele propôs — trocar `return _r` por
`pass`, deixando a flag ligada e inerte — e a matriz ficou **62/0, verde**. Ele
estava certo.

**O juiz de efeito material** apontou dois caminhos para o segundo pedido pago.
Verifiquei os dois no código; os dois existiam. Viraram [CA-047](../CHANGE-ADDENDA.md)
e [CA-048](../CHANGE-ADDENDA.md).

**E o primeiro teste executável achou um terceiro**, que nenhum juiz viu: o
caminho API-first exigia `params["_seguradora_slug"]` e `params["_data_iso"]`, e
📊 `grep` no repositório inteiro mostra que **ninguém escrevia esses campos**. A
função devolvia `None` em 100% das chamadas. O caminho inteiro estava morto por
construção — e nenhum teste de texto podia ver, porque o código estava todo lá,
na ordem certa.

| # | Mutação | Vermelhas |
|---|---|---|
| J1 | flag ligada mas inerte (resultado descartado) | 2 |
| J3 | guard volta a ser fail-open sem runtime | 1 |
| J4 | ramo de `coverage_absent` removido | 2 |
| J5 | `protocolo` gravado só depois da fronteira B | 1 |
| J6 | fallback DOM sem o guarda de efeito | 1 |
| J7 | volta a exigir `_seguradora_slug` (caminho morto) | 12 |
| — | restaurado | **0** |

---

## 10. Gates

```
243/0   asserções da SPEC-074
390/0   asserções da SPEC-073, revalidadas depois de tudo
214     suites verdes no backend
 17     suites vermelhas — as MESMAS já provadas pré-existentes no
        baseline 5cac02f, em worktree descartável
  0     tsc --noEmit (exit 0)
```

As 17 vermelhas: `test_acionamento_sobrevive`, `test_destilador_nao_paga_duas_vezes`,
`test_golden_do_eletricista`, `test_handoff_chega_em_alguem`,
`test_o_acionamento_nao_trava`, `test_o_agente_responde_a_tela_inteira`,
`test_o_clique_nao_se_perde`, `test_o_que_acontece_quando_o_agente_liga`,
`test_spec017_dispatch`, `test_spec038_history`, `test_spec038_observer`,
`test_spec040_onda1_attendance_capture`, `test_spec040_onda3_distiller`,
`test_spec042_lapidador`, `test_spec049_pareamento_alerta_garimpo`,
`test_spec050_qr_variaveis_conhecimento_agentes`, `test_spec051_observer_agents`.

**Nenhuma delas é regressão da 074** — todas falham igual em `5cac02f`.

---

## 11. Erros meus, e o que cada um ensinou

**A cedilha.** `"avancar" in "avançar"` é `False`. Meu guard bloqueava o clique
legítimo dos 80%; com `confirm=true`, o pedido de vidros **nunca seria criado**.
Minhas fixtures usavam `"Avancar"` em ASCII, então a matriz não via. Foi também
falha de processo: depois do commit `e1575e8` eu rodei só as 6 suites da 073, não
o conjunto de vidros. Corrigido com `_sem_acento()` nos dois lados e texto
acentuado de verdade na matriz.

**Duas asserções minhas estavam erradas, não o código.** Uma procurava a palavra
`"reexecut"` quando o texto diz *"NÃO peça para eu abrir de novo"*. Outra
reprovava `"não consegui"` sem olhar o sentido — mas *"FOI aberto, só não conclui
a última etapa"* é honesto. Eu procurava a palavra que **eu** teria escrito, não a
que o produto escreveu. As duas passaram a checar sentido.

**Um fail-open que meu próprio teste declarou seguro.** O achado mais sério da
SPEC, e eu o encontrei **lendo a sequência real**, não pelo teste.

`_guard_do` devolvia, quando o runtime não vinha nos params,
`PortalActionGuard(material_liberado=bool(confirm))`. Guard construído solto não
tem checkpoint — e `_gravar` só persiste `if self._checkpoint is not None`. Logo,
com `confirm=True` e sem runtime, o `POST /atendimentos` sairia **sem que o banco
soubesse que havia um POST em curso**. Uma queda logo depois deixaria um
atendimento existindo na seguradora sem uma linha de evidência: `maybe_committed`
sem ninguém para reconciliar — o buraco exato que a SPEC-073 existe para fechar.

Em produção o worker sempre injeta `_runtime`. Mas *"sempre"* é uma suposição
sobre outro módulo, e fronteira material não se apoia em suposição.

**Por que meu bloco V13 não pegou:** ele provava a integração por **inspeção de
fonte** — *"o guard é chamado antes do POST"*. Verdade, e insuficiente: não dizia
nada sobre **o que esse guard responde**.

**E o teste que escrevi para cobri-lo estava errado duas vezes.** Na primeira,
chamei `acao_material_permitida` num guard solto — que recusa de qualquer jeito,
porque `acao_material_esperada` nasce vazia. A asserção passava pelo motivo
errado, e a mutação que devolvia o fail-open deu **61/0, verde**. Guarda que não
tem como falhar não guarda nada (CLAUDE.md §9.3). Na segunda, mirei no portão
errado: `acao_material_permitida` confere só o **rótulo**; quem confere a
liberação é `avaliar()`, que `before()` chama primeiro.

O teste final dá ao guard **toda chance de permitir** — nomeia a ação esperada —
para que a única coisa capaz de recusar seja `material_liberado`, e confere o
**motivo** da recusa, não só o booleano. M7 acende 3 vermelhas.

**O `git diff` que não provou nada.** Mutei `api_first_habilitado()` num arquivo
**untracked**, restaurei à mão e conferi com `git diff --quiet`, que respondeu
"idêntico". Arquivo untracked nunca aparece no diff. Só apareceu no `git status`
depois do commit seguinte; a restauração teve de ser verificada por inspeção
(4 funções, 258 linhas, tabela-verdade da flag com 10 valores).

---

## 12. Canário Amandus → Resulta → AutoFleet

🔵 **Não executado, por decisão de segurança.** Um canário real na 074 significa
**abrir um atendimento de vidro no nome de um segurado** num portal que cobra por
atendimento. Não existe ambiente de homologação do Maxpar disponível, e não há
como fazer um canário read-only da fronteira material — o preflight read-only já
roda, mas ele não exercita o que precisa de prova.

O que substitui o canário nesta SPEC: **replay offline** contra as fixtures
extraídas do HAR real (`SessaoDeQuestionarioFalsa` roda a sequência medida da
Porto de ponta a ponta até o 204) e a matriz de mutações.

📌 O canário real vai para PENDÊNCIAS com dono 🧑 Founder: precisa de um caso
verdadeiro que o segurado realmente queira abrir, ou de credencial de homologação.

---

## 13. Estado de produção

| Serviço | Precisa deploy? | Por quê |
|---|---|---|
| `portal-worker` | ✅ sim | `COPY backend/portal_worker` — 6 journeys mudaram |
| `smith-api` | ✅ sim | `COPY . .` — `vidros_flow`, `portal_params`, `vigia` |
| `smith-worker` | ✅ sim | mesma imagem; o Vigia roda no scheduler |
| `smith-web` | ❌ não | zero linhas de TS alteradas nesta SPEC |

Os três gatilhos foram disparados e responderam `Deploying...` (HTTP 200).

⚠️ **A verificação por SHA é impossível hoje**: `portal-worker` reporta
`build_sha: "unknown"` e `smith-api` reporta `git_commit: "nao-injetado"`. O
marcador utilizável é `build_time` no `/health` do portal-worker. Isso é um
defeito de observabilidade e vai para PENDÊNCIAS — a SPEC-073 pediu "build/git
SHA real e verificável" e o que existe hoje não é verificável.

**A flag `PORTAL_VIDROS_API_FIRST` nasce desligada.** Nada do caminho novo executa
em produção até alguém ligar. O caminho DOM provado roda byte-a-byte como rodava.

---

## 14. Rollback

Três níveis, do mais barato ao mais caro:

1. **Não precisa de rollback para o caminho novo** — ele está desligado. Se
   alguém ligar e der errado: remover `PORTAL_VIDROS_API_FIRST` e reiniciar.
2. **Reverter o comportamento sem reverter código**: os módulos novos são
   inertes sem a flag; só três pontos de integração ficam ativos
   (`portal_params.format_result`, `vigia_do_portal.diagnosticar`, o bloco em
   `vidros_lanternas`). Os três são aditivos e caem no ramo antigo quando não
   há `vidros_estado` no evidence — provado nos controles V06 e V07.
3. **Reverter tudo**: `git revert 57bff1a..ffd1cd9` e redeploy dos três serviços.

Sem migration ⇒ **sem rollback de banco**.

---

## 15. Declaração

**Nenhum motor paralelo foi criado.** Sem runtime novo, sem RAG novo, sem cliente
HTTP novo, sem registry novo, sem scheduler novo. `vidros_sessao.py` usa o padrão
`page.evaluate` + `fetch` já empregado por Yelum, MAPFRE, Tokio e Zurich. As
journeys entram no `JOURNEYS` existente. O guard é o da SPEC-073, reusado.

---

## 16. FATO · INFERÊNCIA · RECOMENDAÇÃO

**FATO** — 243 asserções novas verdes; 13 mutações detectadas e restauradas;
390 asserções da 073 revalidadas; 214 suites verdes e 17 vermelhas pré-existentes;
`tsc --noEmit` exit 0; `origin/main` em `57bff1a`; três deploys disparados com
HTTP 200; a flag nasce desligada em 10 valores de entrada testados; 0 CPF e 0 CNPJ
nas fixtures.

**INFERÊNCIA** — o contrato mapeado do HAR descreve o portal como ele estava nas
capturas. Portal muda. O caminho API-first **não foi exercitado contra o portal
real nesta SPEC** — só contra replay. É por isso que ele nasce desligado.

**RECOMENDAÇÃO** — ligar `PORTAL_VIDROS_API_FIRST` apenas em uma corretora, com um
caso real acompanhado ao vivo, e comparar o `CodigoAtendimento` devolvido com o
que a tela do portal mostra. Se bater, é o caminho que reduz entradas no portal e
descobre ausência de cobertura sem escrever nada. Se não bater, a flag volta a
`false` e nada foi perdido.
