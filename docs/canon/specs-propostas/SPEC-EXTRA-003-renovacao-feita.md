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
RISCO .......... 7  (ALCANCE 3 o segurado recebe a apresentação · REVERSIBILIDADE 2 cálculo e estado
                    — o ENVIO é do corretor na v1 · FREQUÊNCIA 2 todo dia)
SUPERFÍCIE ..... 3  peça nova (porta de cotação) + evolução do Core (espera durável)
PISO ........... §3.2: credencial/sessão de terceiro; o filtro company_id; o Work OS
NÍVEL .......... CRÍTICO · builders Opus xhigh · juiz Fable ‖ red team Fable · lente do dado (outcome é número)
O FIO .......... §2 — o TESTE DO FIO é a 1ª entrega: 1 renovação real, da InfoCap ao Artifact, dublê só no HTTP do Agger
PARALELISMO .... fatia 1 (backend/app/services/work/*) ∥ fatia 2 (backend/app/providers/quote_*, connectors) — disjuntas
UNIDADES ....... 5 fatias (§7)
COESÃO ......... 3 e 4 compartilham o modelo canônico → série depois de 2
REFERÊNCIA ..... interna: PolicyDataProvider (porta+adaptador+CampoComOrigem), LeaseDePortal, renewals.radar;
                 observada: o PDF de 3 colunas da corretora (RP §7); externas §10
GATES .......... §8
O ELO .......... "pronta às 7h" liga o cálculo (A) ao que o corretor vê (B): medir que o estado da tela
                 VEM do resultado normalizado, não do status do run
FAIXA .......... 💭 14–22 h, em 2 sessões de gerente (fatias 1–2 · 3–5) — ⚠️ o protocolo pede 1 SPEC por
                 chat: se estourar 600 k, a 004 herda a fatia 5
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
| D-E002-06 | a fundação vive aqui (fatias 1–2) | a 004 e a 007 importam, não copiam |

---

## 2. O FIO

| # | elo | peça | estado |
|---|---|---|---|
| 1 | a Rotina diária da corretora dispara | `routine_engine` → `bridge_rotina` com `routines.config.workflow="renewal.cycle"` (`workflows.py:333-347`) | EXISTE |
| 2 | lista das apólices que entram na janela | `FonteInfoCap.carteira_a_vencer(inicio, fim)` (`comercial/fonte_infocap.py:547`) atrás da porta | EXISTE · 🔧 filtro ramo AUTO |
| 3 | um Work Run **por renovação**, idempotente | `WorkRunService.criar(idempotency_key=f"renewal:{company_id}:{apolice}:{ciclo}")` | EXISTE |
| 4 | a apólice canônica | `PolicyDataProvider.detalhar_apolice` + `/itens` (veículo) | EXISTE · 🔧 chassi/FIPE saem do caminho depreciado |
| 5 | o negócio do ano anterior no Agger | `QuoteProvider.buscar_cotacao_anterior(cpf_cnpj, placa)` | 🆕 |
| 6 | a MATRIZ DE VERDADE monta a entrada e lista lacunas | `renewal/entrada.py` (§3) | 🆕 |
| 7 | lacuna bloqueante → estado "precisa confirmar dado" | Work Step `needs_input`, **sem** cálculo | 🆕 |
| 8 | disparo | `QuoteProvider.calcular(entrada, correlation_id)` → `POST calcularV2` | 🆕 |
| 9 | **espera durável** — o run dorme e acorda para consultar | `work_waits kind='timer'` + varredor | 🔧 evoluir |
| 10 | coleta incremental até o corte do Agger (~7 min) ou todas decididas | `QuoteProvider.consultar(ref)` | 🆕 |
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
| seguradora atual | InfoCap (📊 100 %) → mapa para o id do Agger (`seguradorasRenovacao`, 69) | — | bloqueia | não |
| fim de vigência atual | InfoCap (📊 100 %) | — | bloqueia | não |
| **bônus** | InfoCap `/itens` ❓ | cotação anterior + 1 classe se sem sinistro | **confirmar** | SIM se derivado |
| **sinistros no período** | InfoCap sinal `sinistro` | — | assume o que a InfoCap diz | SIM se desconhecido |
| **CEP de pernoite** | cotação anterior | ❌ | **precisa confirmar dado** | — |
| **condutor principal** (+habilitação, relação) | cotação anterior | ❌ | **precisa confirmar dado** | — |
| garagem ×3, uso, período, km, rastreador, antifurto | cotação anterior | ❌ | **precisa confirmar dado** | — |
| CI | InfoCap `/itens` ❓ | — | segue sem (📊 nulo nos 2 cálculos reais) | não |
| perfil de coberturas por seguradora | configuração da corretora no Agger | — | usa a da corretora | não |

🔴 **Regra que não se dobra:** campo derivado (ex.: bônus "anterior + 1") entra marcado `CampoComOrigem(origem="derivado")` e a apresentação **mostra** "bônus estimado — confirme". Nenhum campo de risco é **inventado** por LLM.

### 3.3 Quando a renovação NÃO é calculada automaticamente
- sem cotação anterior no Agger **e** sem questionário respondido → "precisa confirmar dado" com a lista exata do que falta;
- a cotação anterior tem mais de 13 meses → idem (condutor/uso mudam);
- apólice que não é AUTO (v1).

### 3.4 Os dois momentos (D-E002-03)
```text
D-30  cálculo de APRESENTAÇÃO  → "calculado em 12/10, válido até 17/10 — valores podem mudar"
D-5   RECÁLCULO de fechamento   → ou quando o corretor marcar "cliente aceitou"
```

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
"Mais parecida com a atual" = distância explícita sobre (casco, DM, DC, danos morais, APP, vidros, carro reserva, assistência) contra a apólice atual do **PDF oficial**; a fórmula fica escrita ao lado do código (CLAUDE.md §9.5).

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
| sessão derrubada por outro login | nova sessão 1×; se repetir, falha | 🔴 | corretora | sim |
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
| **1 · O Work OS sabe esperar** | `work_waits kind='timer'` (ou coluna equivalente) + varredor que reenfileira; `executar_passo` não re-executa passo `succeeded` com efeito; `retry_scheduled` volta à fila | `backend/app/services/work/*`, `workers/smith_worker.py`, 1 migration expand-first | um run que espera 3× e retoma após matar o worker **sem** repetir o efeito; linha de controle com o código antigo |
| **2 · A porta e o adaptador** | `QuoteProvider`, `ResultadoDeCotacao`, `AggerQuoteAdapter` (transporte HTTP; navegador como alternativa declarada), `connector_template` "agger", lock por conexão | `backend/app/providers/quote_*`, `providers/agger_*`, `api/*connector*` | fixtures sanitizadas dos 2 HARs → o mesmo resultado canônico; dois tenants, duas conexões, zero cruzamento |
| **3 · O ciclo** | workflow `renewal.cycle`: janela, run por apólice, matriz de verdade, lacunas, cálculo, espera, coleta, nova tentativa, recálculo D-5 | `backend/app/renewal/*`, registro do workflow | teste do fio com a InfoCap dublada e o Agger dublado |
| **4 · Comparação e apresentação** | rótulos, não-comparável, template `renewal.proposal` com seguro atual + opções + diferenças + parcelamento + validade + motivos; `white_label` lido; PDF por impressão | `renewal/comparacao.py`, `services/artifacts/templates.py`, `blocks.py`, `app/r/[token]` | juiz de design contra a referência observada (RP §7) e o DS-001; mobile 375 px |
| **5 · Painel, revisão, envio** | painel por estado; revisar; "enviar" = ação do corretor pelo canal da corretora; resultado marcado | frontend do Auxiliar, rota de envio | 🔧 `next start` + 1 requisição (CLAUDE.md §9.1); canário Amandus → Resulta → AutoFleet |

---

## 8. Gates

G1 teste do fio verde · G2 retomada sem efeito duplicado (mutação: remover a checagem → vermelho) · G3 dois tenants com duas conexões Agger, nenhuma leitura cruzada (mutação: tirar o filtro) · G4 `pronta` só com oferta + artifact (mutação §5) · G5 nenhum campo derivado sem marca na apresentação · G6 apresentação sem selo da plataforma com `white_label` · G7 nenhuma PII/credencial em log, evidence ou artifact (grep) · G8 canário real: 1 renovação por piloto calculada de madrugada, estado às 7h conferido pela **lente do dado** contra o Agger aberto na tela.

---

## 9. Fora desta SPEC

envio automático (D-E002-04 C/B) · ramos além de AUTO · cotação sem apólice anterior (→ 004) · site público (→ 007) · cross-sell (→ EXTRA-006) · alertas de aumento de preço como produto (→ ideia RP §11).

---

## 10. O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS

| URL | o que faz | o que MODELAMOS | o que REJEITAMOS | como o juiz inspeciona |
|---|---|---|---|---|
| https://aggilizador.com.br | multicálculo com abas de pacote e versões | a separação principal/alternativo/assinatura e o histórico de versões | a tabela sem o seguro atual | abrir um cálculo; comparar as abas com `pacote` |
| https://www.agger.com.br | dono do Aggilizador e da InfoCap | API/integração oficial antes de endpoint interno | acoplamento ao JSON | procurar área de integração |
| https://docs.temporal.io/workflows#durable-execution | execução durável: o workflow dorme e retoma sem repetir efeito | "timer" + retomada que não repete passo concluído (fatia 1) | trazer o Temporal — o Work OS é a peça (CLAUDE.md §5) | ler a seção; comparar com o teste G2 |
| https://www.rfc-editor.org/rfc/rfc9110#name-idempotent-methods | semântica de idempotência | disparo com `correlation_id` estável e checagem antes de redisparar | "tenta de novo e vê" | a mutação de G2 |
| `docs/intake/…/MODELO DE APRESENTAÇÃO COM 3 OPÇÕES.pdf` (observada) | o que a corretora envia | seções, validade de 5 dias, observações de condutor/CEP/uso | digitação manual; sem seguro atual | abrir o PDF |

⚠️ Referências de UX de apresentação e de comparadores de mercado ficaram **pendentes** (P-E002-06) — o juiz de design, até lá, usa a referência observada + DS-001.

---

## 11. 📋 CAIXA DO FOUNDER (desta SPEC)

1. A caixa da EXTRA-002 (§11) feita — sobretudo o usuário robô e a resposta da Agger. **Bloqueia a fatia 2 real** (a fatia 1 não depende de nada).
2. Configurar a marca da AutoFleet (📊 `brand_profiles` vazio): logo e cores. Sem isso a apresentação dela sai com a marca-padrão.
3. Decidir o percentual de aumento que manda para "precisa de revisão" (💭 sugestão: 15 %).
