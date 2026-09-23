# SPEC-EXTRA-003 — RENOVAÇÃO FEITA
## Às 7h, cada renovação do ciclo está calculada, comparada e apresentável — e diz a verdade sobre o próprio estado

**Status:** PROPOSTA — **depende da parte 2 da EXTRA-002** (E0–E4). Números marcados ❓ são preenchidos por ela antes da conversão.
**Versão:** 1.0 · 22/09/2026 · **Baseline:** `origin/main` = `d8510df` · **Evidência:** `SPEC-EXTRA-002-investigacao-prova-agger-RESEARCH-PACK.md` (citado como RP).
**Auxiliar do catálogo:** `renovacao-maxima` (📊 `coming_soon`, 0 instalações) — esta SPEC o torna real. 💭 Nome comercial proposto: **"Renovação Feita"**, coerente com "Cobrança Feita".

---

## 0. Resultado

> O corretor abre o AutoBrokers às 7h e vê: **18 prontas · 3 aguardando seguradora · 2 precisam confirmar dado · 1 falhou**. Cada pronta tem uma apresentação com a marca da corretora, o seguro atual ao lado das opções novas, as diferenças destacadas, o motivo de cada seguradora que não entrou — e um botão para revisar e enviar.

🔴 **"Pronta" significa utilizável pela promessa comercial**, não "o job terminou" (§5).

### 0.1 EXECUTION CARD — proposto, a confirmar no BLOCO 0

```text
OUTCOME ........ renovações do ciclo calculadas no multicálculo, comparadas com o seguro atual,
                 apresentação white-label pronta; estado honesto às 7h; o corretor revisa e envia
RISCO .......... 8  (ALCANCE 3 o segurado recebe a apresentação · REVERSIBILIDADE 3 o cálculo SAI DO
                    PRÉDIO: cria versão no negócio do cliente no Agger e um `nroCalculo` em cada
                    seguradora — o ENVIO ao segurado é do corretor na v1 · FREQUÊNCIA 2 todo dia)
SUPERFÍCIE ..... 3  peça nova (porta de cotação) + evolução do Core (espera durável)
PISO ........... §3.2: credencial/sessão de terceiro (e as senhas das seguradoras, §3.5); o filtro
                 company_id; migration que altera ESTRUTURA de `work_runs` (fatia 1)
NÍVEL .......... CRÍTICO · builders Opus xhigh · juiz Fable ‖ red team Fable · lente do dado (outcome é número)
O FIO .......... §2 — o TESTE DO FIO é a 1ª entrega: 1 renovação real, da InfoCap ao Artifact, dublê só no HTTP do Agger
PARALELISMO .... fatia 1 (backend/app/services/work/*) ∥ fatia 2 (backend/app/providers/quote_*, connectors) — disjuntas
UNIDADES ....... 5 fatias (§7), em DUAS SPECs: 003-A (fatias 1–2) e 003-B (fatias 3–5) — §7.1
COESÃO ......... 3 e 4 compartilham o modelo canônico → série depois de 2
REFERÊNCIA ..... interna: PolicyDataProvider (porta+adaptador+CampoComOrigem), LeaseDePortal, renewals.radar,
                 `backend/tests/test_a_segunda_corretora_nao_ve_a_primeira.py` (o teste de 2 tenants);
                 observada: o PDF de 3 colunas da corretora (RP §7); externas §10
GATES .......... §8
O ELO .......... "pronta às 7h" liga o cálculo (A) ao que o corretor vê (B): medir que o estado da tela
                 VEM do resultado normalizado, não do status do run
FAIXA .......... 💭 14–22 h no total, 💭 6–9 h na 003-A e 💭 8–13 h na 003-B — cada uma num chat próprio
                 (CLAUDE.md §9: nenhuma SPEC em duas sessões). Nenhuma fatia migra para a 004.
```

---

## 1. Decisões que esta SPEC herda (da EXTRA-002 §10; a confirmar pelo Founder)

| ID | decisão recomendada | efeito aqui |
|---|---|---|
| D-E002-01 | Agger por API oficial ou endpoints com anuência; navegador só como transporte alternativo | o adaptador tem **transporte trocável** |
| D-E002-02 | usuário robô dedicado por corretora | a conexão é do robô; lock "1 sessão por conexão" |
| D-E002-03 | apresentar em D-30, recalcular em D-5 ou no aceite; **configurável por corretora** | dois momentos no ciclo (§3.4) |
| D-E002-04 | modo A: o corretor revisa e envia | nenhum envio automático nesta SPEC |
| D-E002-05 | rótulos transparentes, nunca "recomendação" de IA | §4.3 |
| D-E002-06 | dividir em 003-A "a fundação" (fatias 1–2) e 003-B "o ciclo de renovação" (fatias 3–5), um chat cada (88) | a 004 e a 007 importam a 003-A, não copiam; nome/número final é do Founder |

---

## 2. O FIO

| # | elo | peça | estado |
|---|---|---|---|
| 1 | a Rotina diária da corretora dispara | `routine_engine` → `bridge_rotina` com `routines.config.workflow="renewal.cycle"` (`workflows.py:333-347`) | EXISTE |
| 2 | lista das apólices que entram na janela | `FonteInfoCap.carteira_a_vencer(inicio, fim)` (`comercial/fonte_infocap.py:547`) atrás da porta | EXISTE · 🔧 filtro ramo AUTO |
| 3 | um Work Run **por renovação**, idempotente | `WorkRunService.criar(idempotency_key=f"renewal:{company_id}:{apolice_ref}:{ciclo}")` — `apolice_ref` é o localizador canônico (`policy_data_provider.py:728-760`); o nº humano da apólice não é único entre seguradoras | EXISTE |
| 4 | a apólice canônica | `PolicyDataProvider.detalhar_apolice` + `/itens` (veículo) | EXISTE · 🔧 chassi/FIPE saem do caminho depreciado |
| 5 | o negócio do ano anterior no Agger | `QuoteProvider.buscar_cotacao_anterior(cpf_cnpj, placa)` | 🆕 |
| 6 | a MATRIZ DE VERDADE monta a entrada e lista lacunas | `renewal/entrada.py` (§3) | 🆕 |
| 7 | lacuna bloqueante → estado "precisa confirmar dado" | Work Step `needs_input`, **sem** cálculo | 🆕 |
| 8 | disparo | `QuoteProvider.calcular(entrada, correlation_id)` → `POST calcularV2` | 🆕 |
| 9 | **espera durável** — o run dorme e acorda para consultar | `work_runs.wake_at` + estado de espera (ex.: `waiting`) + o varredor que já existe (`smith_worker._laco_manutencao`) — §7 fatia 1 | 🔧 evoluir |
| 10 | coleta incremental até o fechamento observado (💭 ~7 min, n = 2 — E3 mede) ou todas decididas | `QuoteProvider.consultar(ref)` | 🆕 |
| 11 | normalização → modelo canônico de cotação | `AggerQuoteAdapter` (§4) | 🆕 |
| 12 | nova tentativa só das seguradoras TRANSITÓRIAS | novo disparo restrito, até o corte da madrugada | 🆕 |
| 13 | comparação honesta com o seguro atual | `renewal/comparacao.py` (§4.3) | 🆕 |
| 14 | apresentação | Artifact Hub, template `renewal.proposal`, marca congelada, PDFs das seguradoras anexados | EXISTE · 🔧 template |
| 15 | estado final do ciclo | `renewal_state` derivado do resultado (§5) | 🆕 |
| 16 | painel das 7h | lista por estado na área do Auxiliar | 🔧 |
| 17 | revisão e envio pelo corretor | link `/r/[token]` (🔧 `white_label` passa a ser lido) + WhatsApp pelo canal da corretora, **ação humana** | EXISTE · 🔧 |
| 18 | resultado registrado | evento no run; aceite/recusa marcado pelo corretor | 🔧 |

🔴 **O teste do fio** atravessa 1→15 com o motor real e **dublê só no HTTP do Agger**, alimentado pelas respostas reais dos HARs **sanitizadas** (fixture mínima, sem PII). Nasce vermelho.

---

## 3. A entrada do cálculo — a matriz de verdade

### 3.1 Regra
```text
SISTEMA DE GESTÃO (InfoCap)  → vigência, nº da apólice, seguradora atual, cliente, situação de renovação
COTAÇÃO ANTERIOR (Agger)     → questionário de risco, condutor, garagem, uso, CEP de pernoite
DOCUMENTO OFICIAL (PDF)      → coberturas, limites, franquias do seguro ATUAL (D-PILOTO-11)
O AGGER NA HORA              → placa → FIPE/modelo/chassi · CPF → pessoa · CEP → endereço
```
📊 D-PILOTO-11 já fixou gestão = status/vigência/parcelas e PDF = cobertura. Esta SPEC acrescenta a 4ª fonte.

### 3.2 A matriz (📊 campos do formulário real — RP §3; ❓ taxas por E0)

| campo do cálculo | fonte 1 | fonte 2 | se faltar | confirmar? |
|---|---|---|---|---|
| CPF/CNPJ, nome | InfoCap (📊 99,2 %) | Agger `cadastros/cliente` | bloqueia | não |
| nascimento, sexo, estado civil (PF) | Agger cliente | InfoCap `/cliente_cpf` | bloqueia | não |
| placa, chassi | InfoCap `/itens` | cotação anterior | bloqueia | não |
| FIPE, modelo, ano | Agger `buscaPlaca` | InfoCap `/itens` | bloqueia | não |
| nº da apólice atual | InfoCap (📊 100 %) | — | bloqueia | não |
| seguradora atual | InfoCap (📊 100 %) → catálogo canônico SUSEP → id do Agger | — | bloqueia | não |
| **mapa id do Agger ↔ seguradora canônica SUSEP** | tabela versionada dos 69 ids de `seguradorasRenovacao` (unidade da **fatia 2**) | — | id sem mapa → "precisa de revisão" | não |
| fim de vigência atual | InfoCap (📊 100 %) | — | bloqueia | não |
| **vigência nova** (`vigenciaIni/Fim`) | derivada: início = fim da atual; fim = +1 ano | — | — | não (regra fixa, escrita ao lado do código) |
| **`tpCobertura` e % FIPE** (`pctAjuste`/`valReferenciado`) | **apólice atual** (PDF oficial) | cotação anterior | "precisa confirmar dado" | SIM se veio da fonte 2 |
| **bônus** | InfoCap `/itens` ❓ | cotação anterior + 1 classe se sem sinistro (classe 10 não sobe) | **confirmar** | SIM se derivado, e SEMPRE que a seguradora do cálculo ≠ a atual |
| **sinistros no período** (`sinistrosAnterior` é CONTAGEM) | cotação anterior + contagem confirmada | InfoCap dá só a **situação em texto** (`policy_data_provider.py:583`, "situacao_de_sinistro") — não é contagem | sem contagem confiável → **"precisa confirmar dado"** | SIM |
| **CEP de pernoite** | cotação anterior | ❌ | **precisa confirmar dado** | — |
| **condutor principal** (+habilitação, relação) | cotação anterior | ❌ | **precisa confirmar dado** | — |
| **idade do condutor / jovem condutor** | recalculada na data da vigência nova a partir do nascimento | — | mudou de faixa (ex.: residente fez 18, condutor saiu dos 25) → **"precisa confirmar dado"** | SIM se mudou |
| garagem ×3, uso, período, km, rastreador, antifurto | cotação anterior | ❌ | **precisa confirmar dado** | — |
| CI | InfoCap `/itens` ❓ | — | segue sem (📊 nulo nos 2 cálculos reais) | não |
| **limites e franquia por seguradora** (`calculos[]`: `isDanosMateriais`, `isDanosCorporais`, `isDanosMorais`, `isAppMorte`, `tipoFranquia`, `carroReserva`, `vidros`, `assist24hs`) | **a APÓLICE ATUAL** (PDF oficial, D-PILOTO-11) | `calculos[]` da cotação anterior | "precisa confirmar dado" | SIM se veio da fonte 2 |
| perfil-padrão da corretora no Agger | **2º pacote, opcional**, rotulado "perfil da corretora" | — | não calcula o 2º pacote | não |

🔴 **Por que os limites vêm da apólice atual:** se o cálculo usar o perfil-padrão da corretora (ex.: 💭 DM 100 mil) e o cliente tiver DM 200 mil no PDF, toda oferta sai "mais barata por cobrir menos" ou "não comparável". Com os limites espelhados da apólice, **"mais parecida com a atual" compara coisa comparável** (§4.3). ❓ Se o Agger aceita `calculos[]` alterado por chamada é pergunta do E3 (1 cálculo espelhado × 1 com o perfil-padrão, linha de controle).

🔴 **Regra que não se dobra:** campo derivado (ex.: bônus "anterior + 1") entra marcado `CampoComOrigem(origem="derivado")` e a apresentação **mostra** "bônus estimado — confirme". Nenhum campo de risco é **inventado** por LLM.

⚠️ **A FIPE muda todo mês** (`fipeModelo` devolve valores por mês, RP §2.1): a apresentação diz **o mês da tabela FIPE** usada em cada preço, e o recálculo de D-5 pode cair noutro mês.

### 3.3 Quando a renovação NÃO é calculada automaticamente
- sem cotação anterior no Agger **e** sem questionário respondido → "precisa confirmar dado" com a lista exata do que falta;
- a cotação anterior tem mais de 13 meses → idem (condutor/uso mudam);
- apólice que não é AUTO (v1);
- 🔴 **frota:** a v1 calcula apólice de **1 item**. Apólice com mais de um item em `/itens` → **"precisa de revisão"** (o formulário do Agger tem um veículo e um condutor principal — RP §3). ❓ Quantas apólices AUTO têm > 1 item, por corretora, o **E0** mede; um run por item fica para depois dessa medição.

### 3.4 Os dois momentos (D-E002-03)
```text
D-30  cálculo de APRESENTAÇÃO  → "calculado em 12/10, válido até 17/10 — valores podem mudar"
D-5   RECÁLCULO de fechamento   → ou quando o corretor marcar "cliente aceitou"
```

### 3.5 🔴 Os segredos que o multicálculo nos entrega

📊 As chaves `login/senha/loginWs/senhaWs`, **com valor**, aparecem nas RESPOSTAS de `cfg/seguradora/config`, `calculo/seguradoras`, `cotacao/versoes/{id}`, `negocio/{id}` (login/senha) e em **todas as 28** respostas de polling `cotacao/calculos/{id}/{v}`; e no CORPO do `POST calcularV2` (📊 varredura de chaves nos 2 HARs, 22/09). O AutoBrokers passaria a segurar as senhas dos portais de ~15 seguradoras **por corretora, a cada consulta**.

**Contrato (vale para o adaptador e para o Work OS, fatias 1–2):**
1. **Strip na borda do transporte.** O adaptador remove `login`, `senha`, `loginWs`, `senhaWs` — e toda chave da lista de redação existente (`CHAVES_SENSIVEIS`, `backend/portal_worker/redaction.py:44`) — de **TODA** resposta, antes de devolver qualquer coisa ao resto do código. Reutiliza `redigir()` (`redaction.py:141`); não copia.
2. **O corpo do `calcularV2` vive só em memória:** montado na hora a partir do perfil lido na hora, e **nunca** persistido, logado, posto em evento, step, attempt, artifact, fixture nem mensagem de exceção.
3. **`RefDeCalculo` e `ResultadoDeCotacao` não têm campo de credencial** — `RefDeCalculo` = `{idIntegracao, versao}`.
4. **O registro do Work OS passa a delegar à redação existente** (evoluir, não duplicar — CLAUDE.md §5): hoje `_redigir`/`_SEGREDO` (`backend/app/services/work/workflows.py:252-259`) não conhece `senha`, e `runs.evento` grava `"payload_redacted": payload or {}` (`runs.py:334`) sem redigir. Os dois passam a chamar `redigir_texto`/`redigir` de `portal_worker/redaction.py` — o nome `payload_redacted` passa a ser verdade.
5. **Fixtures de teste só com RESPOSTAS redigidas** — nunca o request do HAR (que tem as senhas).

**Gate G7, executável:** `tem_vazamento()` (`redaction.py:216`) sobre tudo que o teste do fio gravou — `work_events`, `work_attempts`, `work_steps`, o artifact — e sobre as fixtures do Agger → lista vazia. **Mutação:** remover o strip do adaptador (ou injetar `"senhaWs":"x"` numa exceção) → o guarda fica **vermelho**.

❓ Perguntar à Agger, na mesma conversa comercial, se existe disparo **sem** reenviar credenciais — é argumento a favor do caminho C.

### 3.6 🔴 A sessão única do robô sobrevive à espera durável

📊 Um usuário = uma sessão; o 2º login manda `derrubaSessao` (RP §2.2). Com a espera durável, o run acorda em **qualquer** worker (📊 `WORK_WORKER_CONCURRENCY` padrão 3, `smith_worker.py:40`). Se o token viver na memória do worker, o worker B reloga e derruba o A.

- **O token é estado da CONEXÃO, não do worker:** Redis por `(company_id, connection_id)`, TTL menor que as 8 h do JWT (💭 7 h), nunca em Postgres, nunca em log (CLAUDE.md §6: Redis = transitório).
- **Login SÓ sob o lease** no molde `LeaseDePortal` (`backend/portal_worker/leases.py:256` `chave_de_conta`, classe em `:363`), com chave **por conexão**.
- **Relogin antes de expirar**, planejado (a janela da madrugada, 💭 8,5 h, é maior que o token) — não como reação a falha. 401 → **um** relogin sob o mesmo lease.
- **Guarda:** 2 workers, 1 conexão, 3 esperas → **exatamente 1 login** no dublê. **Mutação:** tirar o lease → 2 logins → vermelho.

---

## 4. O modelo canônico de cotação — a porta `QuoteProvider`

### 4.1 Por que uma porta nova (e não o PolicyDataProvider)
`PolicyDataProvider` responde "o que o cliente TEM". Cotação responde "o que o cliente PODE TER". Mesmo padrão (porta · adaptador · `CampoComOrigem` · `CapacidadeDoProvider`), outro contrato. 🔴 Nenhuma tela consome JSON do Agger.

### 4.2 O contrato (nomes finais no BLOCO 0)
```text
QuoteProvider
  capacidade() → {calcula_auto, renovacao, cotacao_anterior, pdf, paralelismo_max}
  buscar_cotacao_anterior(company_id, cpf_cnpj, placa) → EntradaDeCotacao | None
  calcular(company_id, EntradaDeCotacao, correlation_id) → RefDeCalculo
  consultar(company_id, RefDeCalculo) → ResultadoParcial
  baixar_pdf(company_id, RefDeCalculo, oferta_id) → bytes

ResultadoDeCotacao
  ref · calculado_em · valido_ate · completo (bool) · provider_key
  ofertas[]:   OfertaDeSeguradora
     seguradora (chave SUSEP canônica) · produto · pacote (principal|alternativo|assinatura)
     premio_total · premio_mensal · franquia {valor, tipo}
     coberturas {casco_pct_fipe, danos_materiais, danos_corporais, danos_morais,
                 app_morte, app_invalidez, vidros, carro_reserva, assistencia, extras[]}
     parcelamentos[] {n, primeira, demais, forma, juros}
     renovacao_garantida · nro_calculo_seguradora · pdf_ref · alertas[] · observacoes[]
  nao_ofertadas[]: {seguradora, familia: configuracao|comercial|aceitacao|transitorio, motivo}
  pendentes[]:     {seguradora, desde}
```
📊 Cada campo tem origem no JSON real do Agger (RP §2.4) — **nada aqui é imaginado**. As 6 famílias de erro são as observadas.

### 4.3 A comparação honesta
```text
RÓTULOS (cálculo determinístico, sem LLM):
  menor preço · menor franquia · mais parecida com a atual · maior cobertura · melhor parcelamento
  destaque da corretora ← SÓ um humano marca
NÃO COMPARÁVEL quando: casco %FIPE diferente · franquia de tipo diferente · cobertura da atual ausente
  → aparece LADO A LADO, com a diferença escrita ("não inclui carro reserva, que você tem hoje")
DADO AUSENTE: célula "não informado pela seguradora", nunca "0" nem "—" ambíguo
```
"Mais parecida com a atual" = distância explícita sobre (casco, DM, DC, danos morais, APP, vidros, carro reserva, assistência) contra a apólice atual do **PDF oficial**; a fórmula fica escrita ao lado do código (CLAUDE.md §9.5). Como os limites do cálculo vêm **da mesma apólice** (§3.2), a comparação é entre coisas comparáveis; o pacote do perfil-padrão da corretora, quando pedido, aparece **separado e rotulado**.

**A "renovação garantida" da seguradora atual** (`renovacaoGarantida`, RP §2.4) aparece **separada** das cotações novas — é outra coisa (a proposta oficial que o cliente já recebe), não mais uma linha da tabela. E cada preço diz **quando foi calculado, até quando vale e o mês da tabela FIPE**.

---

## 5. O estado às 7h — sem mentira verde

| estado | quando | o corretor vê |
|---|---|---|
| ✅ **pronta** | ≥ 1 oferta válida · entrada sem campo derivado não confirmado · apresentação renderizada | "ver apresentação · revisar · enviar" |
| 🟡 **aguardando seguradora** | há seguradora TRANSITÓRIA dentro do corte, ou nenhuma oferta ainda | quais, desde quando, próxima tentativa |
| 🟡 **precisa confirmar dado** | lacuna bloqueante ou campo derivado | a lista do que falta; botão "responder" (e, na 004, "pedir ao cliente") |
| 🟡 **precisa de revisão** | todas não-ofertadas por ACEITAÇÃO, ou preço subiu > X % (configurável) | o motivo |
| 🔴 **falhou** | login do robô falhou, Agger fora, erro de contrato | a causa e **quem destrava** |

🔴 **Guarda:** `pronta` só é derivável de `ResultadoDeCotacao` + artifact renderizado. Mutação: forçar `status=completed` no run sem oferta → o guarda fica vermelho.

---

## 6. Falhas do mundo real

| falha | o sistema faz | o corretor vê | quem destrava | retoma? |
|---|---|---|---|---|
| login do robô falhou / senha expirou | para o ciclo da corretora, alerta às 22h | 🔴 "conexão Agger" | corretora (tela de conexões) | sim, no próximo tick |
| senha perto de expirar (📊 `diasParaExpirarSenha`) | alerta 7 dias antes | aviso | corretora | — |
| sessão derrubada por outro login | não acontece por nós: token por conexão em Redis, login só sob lease (§3.6); se vier de fora (uma pessoa usando o robô), 1 relogin sob o lease; se repetir, falha | 🔴 | corretora | sim |
| Agger fora / mudou a API | teste de contrato diário 1 leitura; tudo "falhou" com causa | 🔴 com causa | AutoBrokers | sim |
| seguradora instável | nova tentativa só dela até o corte | 🟡 | tempo | sim |
| seguradora com credencial ruim no Agger | "configuração" na lista | 🟡 lista de seguradoras a arrumar | corretora | — |
| cálculo duplicado | `correlation_id` = hash(run, momento); antes de redisparar, consulta versões do negócio | — | — | idempotente |
| worker morreu no meio | lease vence → retomada **sem** redisparar se `submit` já `succeeded` | — | — | sim (fatia 1) |
| 07:00 chegou e não terminou | o painel mostra o estado real; o ciclo continua até o corte configurado | 🟡 | tempo | sim |
| cliente mudou de carro | placa nova ≠ apólice → "precisa confirmar dado" | 🟡 | corretor | — |

---

## 7. As fatias

| fatia | entrega | arquivos (disjunção) | prova |
|---|---|---|---|
| **1 · O Work OS sabe esperar** | `work_runs.wake_at` + estado de espera (ex.: `waiting`); o **mesmo** varredor (`_laco_manutencao`) reenfileira `waiting` vencido **e** `retry_scheduled` com `next_attempt_at` vencido (cura o re-enfileirador que falta, RP §10.4 — sem 2º relógio); `executar_passo` não re-executa passo `succeeded` com efeito; `concluir()` deixa de ser incondicional (`smith_worker.py:385-393` sobrescreveria o estado de espera — o handler devolve uma sentinela "esperando"); `_transicionar` ganha compare-and-set `.eq("status", esperado)` (`runs.py:309-314`, hoje sem pré-condição); redação do Work OS delega a `portal_worker/redaction.py` (§3.5 item 4) | `backend/app/services/work/*`, `workers/smith_worker.py`, 1 migration expand-first (**CRÍTICA por piso**) | um run que espera 3× e retoma após matar o worker **sem** repetir o efeito; um cancelamento durante a espera não é atropelado; linha de controle com o código antigo |
| **2 · A porta e o adaptador** | `QuoteProvider`, `ResultadoDeCotacao`, `AggerQuoteAdapter` (transporte HTTP; navegador como alternativa declarada), `connector_template` "agger"; **o contrato dos segredos** (§3.5); **a sessão por conexão sob lease** (§3.6); **o mapa dos 69 ids do Agger → SUSEP**; **os hosts do multicálculo** (📊 `api-prod.aggilizador.com.br`, `api.multicalculo.net` — RP §2) liberados na allowlist do `egress_guard` **por conector** — evolução de configuração, não contorno (📊 `backend/app/core/egress_guard.py:91`: `allowed_hosts` vazio = DENY ALL); host fora da lista → `EgressBlocked` | `backend/app/providers/quote_*`, `providers/agger_*`, `api/*connector*`, configuração do egress | fixtures de RESPOSTAS redigidas dos 2 HARs → o mesmo resultado canônico; G3, G7, G10 |
| **3 · O ciclo** | workflow `renewal.cycle`: janela, run por apólice, matriz de verdade, lacunas, cálculo, espera, coleta, nova tentativa, recálculo D-5 — **e a governança** (GLOSSÁRIO: Rotina nunca existe sozinha): release do Auxiliar `renovacao-maxima` em `auxiliary_template_releases`, instalação por corretora em `tenant_auxiliaries`, a **Skill** do ciclo, a **Capability** de cálculo de cotação + `tool_definition`/release/binding. Nada de Rotina sem Auxiliar | `backend/app/renewal/*`, registro do workflow, seed de governança | teste do fio com a InfoCap dublada e o Agger dublado; a corretora sem o Auxiliar instalado **não** calcula; G9 |
| **4 · Comparação e apresentação** | rótulos, não-comparável, template `renewal.proposal` com seguro atual + opções + diferenças + parcelamento + validade + motivos; `white_label` lido; PDF por impressão | `renewal/comparacao.py`, `services/artifacts/templates.py`, `blocks.py`, `app/r/[token]` | juiz de design contra a referência observada (RP §7) e o DS-001; mobile 375 px |
| **5 · Painel, revisão, envio** | painel por estado; revisar; "enviar" = ação do corretor pelo canal da corretora; resultado marcado | frontend do Auxiliar, rota de envio | 🔧 `next start` + 1 requisição (CLAUDE.md §9.1); canário Amandus → Resulta → AutoFleet |

🔴 **`work_waits` NÃO é tocada.** 📊 Ela é espera de CONVERSA: `conversation_id NOT NULL` (`backend/supabase/migrations/20260826_05_spec086_blocoB_work_waits.sql:68`), `CHECK kind` em 3 valores de conversa (`:104`) e FK de isolamento `(conversation_id, company_id)` (`:121`). Um run de renovação não tem conversa; afrouxar a âncora afrouxaria uma trava de isolamento.

**Premissa do BLOCO 0 (com comando, no banco — não está no repositório):** o CHECK de `work_runs.status` aceita o novo estado? `select pg_get_constraintdef(oid) from pg_constraint where conrelid='public.work_runs'::regclass and contype='c';` — a definição ORIGINAL fica colada no relatório (é o ROLLBACK).

**A migration da fatia 1 — APPLY / VERIFY / ROLLBACK escritos ANTES de rodar** (CLAUDE.md §8; ler `MIGRATIONS-AUTHORITY.md` antes; nome final no BLOCO 0):
```sql
-- APPLY (idempotente, expand-first: nada antigo lê as peças novas)
alter table public.work_runs add column if not exists wake_at timestamptz;
-- só se o BLOCO 0 mostrar que o CHECK não aceita 'waiting': recriar o CHECK com o conjunto MEDIDO + 'waiting'
create index if not exists work_runs_waiting_wake_idx on public.work_runs (wake_at) where status = 'waiting';
-- VERIFY
--   coluna wake_at existe (information_schema.columns) → 1
--   pg_get_constraintdef do CHECK de status contém 'waiting'
--   o índice parcial existe (pg_indexes) → 1 · count(*) where status='waiting' → 0 logo após o APPLY
-- ROLLBACK (antes: nenhum run em 'waiting' — reenfileirar como 'queued')
update public.work_runs set status = 'queued', wake_at = null where status = 'waiting';
drop index if exists public.work_runs_waiting_wake_idx;
-- recriar o CHECK com a definição ORIGINAL colada no BLOCO 0
alter table public.work_runs drop column if exists wake_at;
```

### 7.1 Duas SPECs, um chat cada (D-E002-06)

A SPEC inteira não cabe num chat (💭 14–22 h; CLAUDE.md §9: nenhuma SPEC em duas sessões). Proposta:

| forma | nota |
|---|:-:|
| **003-A "a fundação"** (fatias 1–2: o Work OS sabe esperar + porta, adaptador, segredos, sessão, egress) → **003-B "o ciclo de renovação"** (fatias 3–5), cada uma num chat próprio, com card, juiz e push próprios | **88** |
| uma 003 só, num chat, correndo o risco de estourar o teto de contexto no meio | 70 |

A 003-A é a fundação que a 004 e a 007 importam. **Nenhuma fatia é "herdada" por outra SPEC** — isso seria corte de escopo silencioso (CLAUDE.md §11). O nome e o número finais são decisão do Founder.

---

## 8. Gates

G1 teste do fio verde · G2 retomada sem efeito duplicado (mutação: remover a checagem → vermelho) · G3 dois tenants com duas conexões Agger, nenhuma leitura cruzada, cache chaveado por `company_id` **e** `connection_id`, conexão arquivada nunca escolhida, PII zero na porta — no molde de `backend/tests/test_a_segunda_corretora_nao_ve_a_primeira.py` (mutação: tirar o filtro) · G4 `pronta` só com oferta + artifact (mutação §5) · G5 nenhum campo derivado sem marca na apresentação · G6 apresentação sem selo da plataforma com `white_label` · **G7 `tem_vazamento()` vazio sobre `work_events`, `work_attempts`, `work_steps`, artifact e fixtures** (mutação: remover o strip → vermelho — §3.5) · G8 canário real: 1 renovação por piloto calculada de madrugada, estado às 7h conferido pela **lente do dado** contra o Agger aberto na tela · **G9 modo A: zero efeito de mensagem** — o workflow do ciclo não chama nenhum emissor (WhatsApp, e-mail, publicador); o run não registra efeito de classe mensagem (mutação: inserir uma chamada de envio no workflow → vermelho) · **G10 sessão única:** 2 workers, 1 conexão → 1 login (mutação: tirar o lease → 2 logins — §3.6).

---

## 9. Fora desta SPEC

envio automático (D-E002-04 C/B) · ramos além de AUTO · cotação sem apólice anterior (→ 004) · site público (→ 007) · cross-sell (→ EXTRA-006) · alertas de aumento de preço como produto (→ ideia RP §11).

---

## 10. O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS

| URL | o que faz | o que MODELAMOS | o que REJEITAMOS | como o juiz inspeciona |
|---|---|---|---|---|
| https://aggilizador.com.br | multicálculo com abas de pacote e versões | a separação principal/alternativo/assinatura e o histórico de versões | a tabela sem o seguro atual | abrir um cálculo; comparar as abas com `pacote` |
| https://www.agger.com.br | dono do Aggilizador e da InfoCap | API/integração oficial antes de endpoint interno | acoplamento ao JSON | procurar área de integração |
| https://docs.temporal.io/workflows#durable-execution | execução durável: o workflow dorme e retoma sem repetir efeito | `work_runs.wake_at` + retomada que não repete passo concluído (fatia 1) | trazer o Temporal — o Work OS é a peça (CLAUDE.md §5) | ler a seção; comparar com o teste G2 |
| https://www.rfc-editor.org/rfc/rfc9110#name-idempotent-methods | semântica de idempotência | disparo com `correlation_id` estável e checagem antes de redisparar | "tenta de novo e vê" | a mutação de G2 |
| `docs/intake/…/MODELO DE APRESENTAÇÃO COM 3 OPÇÕES.pdf` (observada) | o que a corretora envia | seções, validade de 5 dias, observações de condutor/CEP/uso | digitação manual; sem seguro atual | abrir o PDF |

⚠️ Referências de UX de apresentação e de comparadores de mercado ficaram **pendentes** (P-E002-06) — o juiz de design, até lá, usa a referência observada + DS-001.

---

## 11. 📋 CAIXA DO FOUNDER (desta SPEC)

1. A caixa da EXTRA-002 (§11) feita — sobretudo o usuário robô e a resposta da Agger. **Bloqueia a fatia 2 real** (a fatia 1 não depende de nada).
2. Configurar a marca da AutoFleet (📊 `brand_profiles` vazio): logo e cores. Sem isso a apresentação dela sai com a marca-padrão.
3. Decidir o percentual de aumento que manda para "precisa de revisão" (💭 sugestão: 15 %).
