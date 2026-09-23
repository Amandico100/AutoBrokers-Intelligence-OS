# SPEC-EXTRA-002 — DÁ PARA COTAR E RENOVAR PELO AGGER?
## Investigação e prova do multicálculo · a fundação da Renovação Feita, da Cotação pelo Chat e do Comparador

**Status:** PROPOSTA — parte 1 (perícia) **executada em 22/09/2026**; parte 2 (prova ao vivo) **aguarda a caixa do Founder**.
**Modo:** 🧭 INVESTIGAÇÃO (protocolo §8) — medidor · cético · juiz do risco. A conta de risco não governa (§3.3).
**Baseline:** `AutoBrokers-FIX`, `origin/main` = `d8510df` (📊 `git rev-list --count HEAD..origin/main` → 0) · **Branch:** `docs/extra-002-investigacao-agger`
**Research Pack:** `SPEC-EXTRA-002-investigacao-prova-agger-RESEARCH-PACK.md` (toda afirmação 📊 daqui tem lá o comando e a fonte).
**Origem:** D-E001-09 (fila) · D-PILOTO-11 (porta de provider) · D-PILOTO-16 (EXTRA-002 como adaptador) · o rascunho "AUXILIAR DE RENOVAÇÃO" do Founder (18/09).
**Gera:** `SPEC-EXTRA-003-renovacao-feita.md` · `SPEC-EXTRA-004-cotacao-pelo-chat.md` · `SPEC-EXTRA-007-comparador-da-corretora.md` (propostas).

---

## 0. A resposta em uma tela

```text
O Agger é automatizável?        🟢 SIM, tecnicamente — a tela é uma API JSON: dispara, espera, lê.
                                🟡 COM DEPENDÊNCIA — anuência da Agger (ou API oficial) e um usuário robô
Cotação nova?                   🟡 mesmo motor; falta o questionário (quem responde é o cliente/corretor)
Renovação?                      🟡 para quem foi cotado no Agger no ano passado (o formulário inteiro volta —
                                   📊 visto em 2 de 2 casos; QUANTAS renovações têm esse histórico → E2)
                                🟡 para quem não foi: "precisa confirmar dado" — nunca "pronta"
Site comparador público?        🟡 possível sobre o mesmo motor; é o de MAIOR risco; vem por último
Promessa das 7h?                🟢 sustentável no volume dos pilotos, SE o Work OS ganhar espera durável
                                ❓ o número exato espera o experimento E3/E4
```

🔴 **O que mudou em relação à ideia inicial:**

| o Founder imaginou | a investigação achou | original | novo |
|---|---|:-:|:-:|
| o agente "entra no portal do Agger" pelo navegador, como na Allianz | a tela do Agger é só uma casca sobre uma API JSON; navegador seria o executor mais caro e frágil | 58 | **84–92** (API, com anuência/oficial) |
| o Agger entra como "adaptador de sistema de gestão" (D-PILOTO-16) | o Aggilizador é **multicálculo**, não gestão; é uma porta **nova e irmã**: `QuoteProvider`, não `PolicyDataProvider` | 40 | **90** |
| calcular às madrugadas e pronto | a cotação vale **5 dias** (📊 PDF da Ellen e Bradesco): calcula-se para apresentar **e** recalcula-se para fechar | 50 | **88** |
| "a melhor proposta" | "melhor" escondido num prompt é decisão comercial opaca; mostram-se **rótulos transparentes** | 30 | **94** |
| usar o login da Ellen | 🔴 **sessão única por usuário**: o robô derrubaria a Ellen | 40 | **95** (usuário robô) |

---

## 1. Problema e resultado

**Hoje** (📊 relato do Founder + intake): a corretora abre o Aggilizador, digita o CPF, descarta o modal de "CPF já cotado", completa o que falta, marca "é renovação", calcula, espera, copia os números para um Word/PDF de 3 colunas, escreve a mensagem do WhatsApp e envia. 📊 O PDF de referência tem até erro de digitação no nome da seguradora.

**Resultado desejado:** *"Quando sua equipe começar o dia, as renovações do ciclo já estão calculadas, comparadas e preparadas — e cada uma diz a verdade sobre o seu estado."*

**Esta SPEC entrega:** a PROVA de que isso é possível, o desenho que não duplica nada, e a sequência de SPECs. **Não entrega código de produto.**

---

## 2. O que a parte 1 (perícia, 22/09) já PROVOU — sem entrar ao vivo

Fontes: 3 HARs + 7 HTMLs + 6 PDFs do intake (📊 Research Pack §1–§3), laboratório SPEC-077 rodado sobre eles (📊 34 endpoints), e dois laudos read-only do código e do Supabase.

1. 📊 **Autenticação:** login por e-mail+senha → token JWT de **8 h**, enviado no cabeçalho `Authorization`; zero cookies. Sem captcha no login.
2. 📊 **Sessão única:** o segundo login envia `derrubaSessao`. Um usuário = uma sessão.
3. 📊 **Cálculo assíncrono:** `POST /calculo/calcularV2` responde em 1,5–1,9 s com `{idIntegracao, versao}`; o resultado vem por **polling** de `GET /calculo/cotacao/calculos/{id}/{versao}`.
4. 📊 **Tempo:** ofertas válidas completas em **30 s** e **229 s**; conjunto fechado em **420 s** e **413 s** (n = 2). 💭 Parece um corte do Agger em ~7 min — mas nos dois casos a última foi o Bradesco instável: pode ser **timeout por seguradora**, não teto global. E3 decide; até lá T é 💭.
5. 📊 **Resultado padronizado pelo próprio Agger:** prêmio, prêmio mensal, franquia, coberturas (casco, DM, DC, danos morais, APP, vidros, carro reserva, assistência), até 32 parcelamentos, **nº do cálculo na seguradora** e **PDF oficial** por seguradora.
6. 📊 **Erros com motivo** em 6 famílias: configuração (senha/permissão), comercial, aceitação, transitório.
7. 📊 **15 configurações de seguradora** na conta capturada (`calculo/seguradoras`), que viram **17 linhas de cálculo** por disparo (produtos a mais, ex.: Azul e Azul Assinatura); catálogo de 69 para "seguradora anterior"; 56 com status por ramo.
7a. 🔴 📊 **As senhas dos portais das seguradoras viajam em quase tudo:** `login/senha/loginWs/senhaWs` aparecem nas respostas de `cfg/seguradora/config`, `calculo/seguradoras`, `cotacao/versoes`, `negocio/{id}` e **em cada uma das 28 respostas de polling**, e no corpo do `calcularV2` (📊 varredura de chaves nos 2 HARs, 22/09). Qualquer integração recebe 15 senhas de terceiros a cada consulta — é a maior exigência de segurança do desenho (EXTRA-003 §3.5).
8. 📊 **Renovação = cotação marcada** (`renovacao=true` + bônus, sinistros, nº da apólice, seguradora anterior, fim de vigência anterior). Não há "botão renovar" que dispense o formulário.
9. 📊 **O formulário do ano anterior volta inteiro** por `GET /calculo/negocio/{uuid}` — inclusive o questionário de risco e o condutor, que **não existem na InfoCap**.
10. 📊 **Placa → veículo** (`buscaPlaca`), **CPF → pessoa** (`cadastros/cliente`), **CEP → endereço**: o Agger completa o que a InfoCap não tem.
11. 📊 **No AutoBrokers:** zero código de cotação; `renovacao-maxima` é só catálogo; a lista de renovações da InfoCap **já é lida** (`carteira_a_vencer`); Artifact Hub, marca e link público existem; o Work OS **não tem espera durável** nem retomada real.

---

## 3. Fronteiras — o que a prova ao vivo pode e não pode fazer

```text
✅ PODE                                         ⛔ NÃO PODE
login do USUÁRIO ROBÔ dedicado                  usar o login de uma pessoa da corretora
ler: negócios, cliente, placa, FIPE, status     proposta, emissão, aceite, pagamento, transmissão
disparar CÁLCULO de renovação real, do ciclo    enviar qualquer coisa a segurado
ler o resultado e baixar o PDF da seguradora    excluir, cancelar, alterar em massa
medir tempo, erro, paralelismo (subindo aos      contornar captcha, 2FA, bloqueio, proteção anti-robô
poucos, com linha de controle)                   ou limite de sessão — se bloquear, PARA e registra
```

🔴 **A condição de entrada da parte 2 é comercial, não técnica:** (a) **usuário robô** criado pela corretora no Aggilizador; (b) **anuência escrita da Agger** para acesso programático — ou a API oficial dela. **Sem (b), a parte 2 não roda automação nenhuma** — nem por API, nem por navegador: trocar o transporte não muda o fato de ser acesso automatizado sem autorização do fornecedor. Nesse caso, a EXTRA-002 fecha com o que a perícia provou e a D-E002-01 volta ao Founder.

🔴 **Proteção anti-robô:** 📊 o site carrega o sensor Akamai. Se a chamada de servidor for recusada, **isso é resultado da investigação** — a resposta é o acordo com a Agger, nunca o contorno.

---

## 4. Parte 2 — os cinco experimentos que fecham os ❓

Cada um com **linha de controle** (CLAUDE.md §9.2) e registro 📊 no relatório.

| exp. | pergunta | como | pare quando | controle |
|---|---|---|---|---|
| **E0** | quantas renovações AUTO por dia, por corretora? que campos a InfoCap preenche? | `carteira_a_vencer(hoje, hoje+365)` por corretora, agrupado por ramo e dia; amostra ≥ 50 apólices AUTO em `/itens` | tem mediana, máx. e p95 diários por corretora | o radar gravado de 18/08 (📊 297 em 90 d) tem de ser reproduzido |
| **E1** | o servidor autentica e lê? | 1 login do robô + `seguradoraStatus` + `negocio/busca/v2` | 1 leitura OK **ou** 1 recusa (para) | a mesma leitura pela tela, mesma hora |
| **E2** | quantas renovações têm cotação anterior no Agger? | cruzar os CPF/CNPJ da janela com `seguradoCotadoRecentemente` | % com e sem histórico | 3 casos conferidos à mão na tela |
| **E3** | quanto demora, de verdade? | **10 renovações reais do ciclo**, 5 às 20h e 5 às 02h | p50/p95 do conjunto útil e do fechado, por seguradora | 1 caso recalculado igual (mesma entrada, mesmo resultado?) |
| **E4** | quantos cálculos simultâneos por usuário? | 1 → 2 → 3 simultâneos; sobe só se o anterior passou sem erro | o 1º nível que degrada ou recusa | o nível 1 repetido no fim |

**Custo e risco dos experimentos:** 💭 ≤ 25 cálculos no total, todos de renovações que a corretora **precisa calcular de qualquer jeito**. 🔴 Cálculo não é proposta nem emissão, **mas sai do prédio**: 📊 cria uma versão nova no negócio do cliente no Agger ("Item calculado recentemente… será incorporada") e um número de cálculo em cada seguradora (`nroCalculo`). Por isso E3/E4 seguem o **piso CRÍTICO** (protocolo §3.2) mesmo em modo investigação:
- lista das renovações a calcular **autorizada por escrito pela corretora**, caso a caso;
- só usuário robô; nunca num negócio com versão humana de menos de 24 h;
- teto de 25 cálculos; relatório de cada um (quando, qual negócio, qual versão criada).

---

## 5. A PROMESSA DAS 7H — a equação

```text
N  = renovações AUTO que entram na janela do dia, por corretora     📊 ≈3,3/dia todos os ramos (Resulta, radar)
                                                                    ❓ fatia AUTO e pico → E0
C  = CÁLCULOS por noite = 2 × N × (1 + R)                           o recálculo de D-5 (D-E002-03) DOBRA: cada
                                                                    noite calcula quem entra em D-30 E quem entra em D-5
T  = do disparo ao conjunto fechado                                 💭 ~7 min (📊 413–420 s, n = 2, mesmo confundidor
                                                                    Bradesco — E3 mede); útil 📊 30–229 s
R  = acréscimo por nova tentativa (transitório)                     💭 ~15 % (📊 1–2 de 17 seguradoras instáveis por
                                                                    cálculo, em 2 de 2 cálculos)
P  = cálculos simultâneos por robô                                  ❓ → E4 (conservador: 1) · teto de hoje: 📊
                                                                    `WORK_TENANT_CONCURRENCY` padrão 2 por corretora e
                                                                    `WORK_WORKER_CONCURRENCY` padrão 3 no total
                                                                    (`backend/app/workers/smith_worker.py:40-41`)
W  = janela da madrugada (início → corte)                           proposta: 22h → 06h30 = 8,5 h
                                                                    ⚠️ W > o token de 8 h → relogin planejado sob lease

capacidade em CÁLCULOS    = W × 60 / T × P      =  510 / 7 × 1       ≈ 72 cálculos por noite (P = 1)
capacidade em RENOVAÇÕES  = cálculos / (2 × 1,15)                    ≈ 31 renovações por noite (P = 1)
                                                                       ≈ 63 com P = 2 (o teto por corretora de hoje)
```

💭 **Leitura:** com ~7 min por cálculo, **um** cálculo por vez, o recálculo de D-5 e ~15 % de nova tentativa, uma corretora comporta **~31 renovações AUTO por noite** — não 72 (72 era a conta em cálculos, sem D-5 e sem R). Os pilotos (📊 ≈3,3/dia todos os ramos na Resulta) cabem com folga ~9×. 💭 Uma corretora com 200/dia precisaria de P ≈ 7 na madrugada — ou de **espalhar o cálculo pelo dia anterior**: a data de renovação é conhecida com 30+ dias de antecedência, então **não há razão física para tudo acontecer às 3h**.

🔴 **Onde a escala quebra, e não é só no Agger:** hoje cada espera do AutoBrokers é um `sleep` que **segura a vaga do trabalhador** (laudo F1a §1.6). 💭 1.000 cálculos × 7 min = **117 horas-vaga por noite** com 3 vagas → impossível. Com **espera durável** (o run dorme no banco e acorda para consultar), o custo cai para as acordadas — mas cada acordada ainda ocupa **1 de 3 vagas globais**, no mesmo processo que atende a API: 💭 1.000 cálculos × ~28 consultas × ~2 s ÷ 3 vagas ≈ **5,2 h**. São **horas, não dias — limitado pelas vagas, que viram parâmetro** (não "minutos", como dizia a versão anterior). **A espera durável é o pré-requisito da promessa**, não um detalhe.

❓ **E o fornecedor:** 1.000 cálculos × 📊 28 pollings = **~28 mil requisições por noite** num backend que não é nosso, de um IP nosso, atrás do sensor Akamai (RP §2.2). Limite de chamadas é pergunta para a Agger (caixa #2), não suposição.

| cenário | renovações/dia (N) | cálculos/noite (2N × 1,15) | P | tempo (pior caso) | cabe em 22h–06h30? |
|---|---:|---:|:-:|---:|:-:|
| piloto | 10 | 23 | 1 | 2 h 41 | 🟢 |
| média | 50 | 115 | 1 | 13 h 25 | 🔴 (era 🟢) |
| média | 50 | 115 | 2 | 6 h 43 | 🟢 no teto de hoje (`WORK_TENANT_CONCURRENCY` 2), ❓ E4 |
| grande | 100 | 230 | 2 | 13 h 25 | 🔴 (era 🟢 com P = 3 — P = 3 **não existe** com o padrão de hoje) |
| grande | 100 | 230 | 4 | 6 h 43 | 🟡 só com a vaga por corretora virando parâmetro **e** E4 provando P = 4 |
| 100 corretoras × 10 | 1.000 | 2.300 | 1 cada | 2 h 41 por corretora; 💭 ~12 h de vagas globais (3) | 🔴 (era 🟢) → vagas globais como parâmetro (💭 12 vagas ≈ 3 h) + ❓ limite da Agger |

**O que se pode prometer já:** *"Às 7h, cada renovação do ciclo mostra o seu estado real: pronta · aguardando seguradora · precisa confirmar dado · precisa de revisão · falhou."* 🔴 **Nunca** "todas prontas" — 📊 em 2 de 2 cálculos, ao menos uma seguradora caiu por instabilidade.

**Custo (💭 fórmula; números por E3):** o cálculo é HTTP, sem navegador e sem LLM → custo de máquina ≈ zero. Armazenamento: 💭 ~11 PDFs × ~200 KB ≈ 2 MB por renovação → 1.000/mês ≈ 2 GB no MinIO. LLM: só o texto opcional da mensagem, 1 chamada curta por apresentação. **O custo que importa é a licença do usuário robô no Agger** (❓ comercial).

---

## 6. A arquitetura recomendada — nenhuma peça paralela

```text
INFOCAP /renovacoes ──► [já existe] FonteInfoCap.carteira_a_vencer / PolicyDataProvider
                                  │
Rotina diária da corretora ──► routines.config.workflow = "renewal.cycle"   (sem agendador novo)
                                  │
                         Work Run por renovação  (idempotency_key = company:apólice:ciclo)
                                  │
   prepare ─► submit ─► WAIT durável ─► collect ─► normalize ─► compare ─► artifact ─► review
      │         │           │              │            │
      │   QuoteProvider (porta NOVA, irmã do PolicyDataProvider)
      │         └── AggerQuoteAdapter  (transporte: API oficial | endpoints com anuência | navegador)
      │                 credencial: tenant_connections (connector_template "agger"), lock por usuário (Redis, molde LeaseDePortal)
      └── dados: apólice canônica + negócio anterior do Agger + lacunas → "precisa confirmar dado"
                                  │
                   Artifact Hub (template "renewal.proposal", marca da corretora, /r/[token])
```

| peça | existe | evolui | nasce |
|---|:-:|:-:|:-:|
| lista de renovações (InfoCap) | ✅ | | |
| agenda (routine_engine + `config.workflow`) | ✅ | | |
| Work Run, lease, idempotência | ✅ | | |
| **espera durável de run** ("acorde em 30 s") | | 🔧 `work_runs.wake_at` + estado de espera; o varredor que já existe reenfileira (📊 `work_waits` é espera de **conversa** — `conversation_id NOT NULL`, não se toca) | |
| **retomada sem refazer passo com efeito** | | 🔧 `executar_passo` respeita `succeeded` | |
| credencial do Agger por corretora | ✅ molde | 🔧 novo `connector_template` | |
| lock "um usuário = uma sessão" | ✅ molde | 🔧 chave por conexão Agger; token em Redis por conexão (EXTRA-003 §3.6) | |
| allowlist de saída (`egress_guard`) | ✅ | 🔧 ganha os hosts do conector (📊 `egress_guard.py:91`: vazia = DENY ALL) | |
| redação de segredos | ✅ `portal_worker/redaction.py` | 🔧 o Work OS passa a usá-la; o adaptador tira as senhas das seguradoras de toda resposta (EXTRA-003 §3.5) | |
| **porta `QuoteProvider` + modelo canônico de cotação** | | | 🆕 |
| **adaptador Agger** | | | 🆕 |
| Artifact + marca + link público | ✅ | 🔧 template novo, `white_label` lido, PDF | |
| aprovação antes de enviar | ⚠️ | 🔧 v1 não envia sozinho (modo A) | |

🔴 **Não nasce:** outro worker, outra fila, outro agendador, outro cofre, outro publicador, "Agente Renovador". Renovação é **Auxiliar + Rotina + Skill + Work Runs + Tools + Conexão + Artifact** (GLOSSÁRIO).

---

## 7. Os gates da investigação — estado ao fim da parte 1

| gate | pergunta | estado | evidência |
|---|---|:-:|---|
| G1 | autenticar no Agger | 🟡 PARCIAL | fluxo 📊 no HAR; não exercitado por nós → E1 |
| G2 | como a sessão funciona | ✅ PASS | JWT 8 h, `Authorization`, sessão única (RP §2.2) |
| G3 | criar/abrir cotação | ✅ PASS | `negocio`, `versoes`, `calcularV2` (RP §2.1) |
| G4 | dados obrigatórios | ✅ PASS | matriz de ~45 campos (RP §3); obrigatoriedade por seguradora ❓ |
| G5 | disparar cálculo seguro | ⏳ NÃO MEDIDO | humano disparou; nós, no E3 |
| G6 | obter o resultado | ✅ PASS | polling + estrutura (RP §2.3–2.4) |
| G7 | cotação × renovação | 🟡 PARCIAL | pelo formulário; sem HAR de seguro novo |
| G8 | aproveitar dados anteriores | ✅ PASS | `negocio/{uuid}` devolve o formulário inteiro |
| G9 | quais seguradoras | ✅ PASS (conta capturada) | 17 configuradas, 69 no catálogo; a 2ª conta → E1 |
| G10 | diferenças por seguradora | 🟡 PARCIAL | campos de config por seguradora vistos (`bradesco*`, `hdi*`, `tokio*`…); perguntas por seguradora ❓ |
| G11 | endpoints reutilizáveis | ✅ PASS | 34 endpoints — **não contratuais** |
| G12 | fallback de navegador | 🟡 PARCIAL | Portal Worker serve; custo 1 Chromium × 7 min |
| G13 | sessão/concorrência para capacidade | ❌ FAIL até E4 | sessão única 📊; paralelismo por sessão ❓ |
| G14 | InfoCap → cálculo | 🟡 PARCIAL | matriz feita; taxas de bônus/CI/FIPE → E0 |
| G15 | normalizar o resultado | ✅ PASS | o Agger já padroniza; modelo canônico na EXTRA-003 §4 |
| G16 | encaixe no Work OS | ✅ PASS com 2 lacunas nomeadas | espera durável, retomada |
| G17 | apresentação white-label | ✅ PASS com lacunas | template, `white_label` sem leitor, PDF, marca 1/3 |
| G18 | modelar as 7h | 🟡 PARCIAL | equação §5; N_auto e P → E0/E4 |
| G19 | o que não está provado | ✅ PASS | RP §8 |
| G20 | plano de SPECs | ✅ PASS | §8 |

**Fecha a EXTRA-002:** G1, G5, G13, G14, G18 verdes pelos experimentos E0–E4, com relatório.

---

## 8. A sequência de SPECs

```text
EXTRA-002  parte 2: prova ao vivo (E0–E4)           ~1 sessão, depois da caixa do Founder
    │
EXTRA-003  RENOVAÇÃO FEITA                          003-A = fatias 1–2, a FUNDAÇÃO · 003-B = fatias 3–5 (D-E002-06)
    │        1 o Work OS sabe esperar (espera durável + retomada)
    │        2 QuoteProvider + adaptador Agger + conexão
    │        3 o ciclo de renovação (dados, lacunas, cálculo, recálculo)
    │        4 a comparação honesta + a apresentação (Artifact)
    │        5 o painel das 7h + revisão + envio pelo corretor
EXTRA-004  COTAÇÃO PELO CHAT                        reusa 1–2 e 4; acrescenta a coleta conversacional
EXTRA-007  COMPARADOR DA CORRETORA (site público)   reusa tudo; acrescenta anonimato, consentimento, antiabuso
```

| decisão de forma | nota |
|---|:-:|
| a 003 dividida: **003-A "a fundação"** (fatias 1–2) e **003-B "o ciclo de renovação"** (fatias 3–5), um chat cada | **88** |
| a fundação vira uma proposta própria, com outro número, antes da 003 | 74 |
| uma 003 só, num chat | 70 |
| cada produto faz a sua integração | 15 (motor paralelo) |

| ordem | nota |
|---|:-:|
| 003 → 004 → 007 | **92** |
| 007 antes (o site "vende") | 30 — expõe o motor a anônimos antes de provado com corretor |

---

## 9. Riscos, sem esconder

| risco | prob. | efeito | resposta |
|---|:-:|---|---|
| a Agger não autoriza acesso programático | 💭 média | B **e** A fecham (automação sem autorização é a mesma coisa por API ou por navegador) | só C (oficial); sem C, a Renovação Feita não nasce sobre o Agger — reavaliar D (portais das seguradoras, onde a corretora já autoriza o robô) |
| mudança de API sem aviso | 💭 alta em 12 meses | cálculo quebra de madrugada | teste de contrato diário (1 leitura), alerta antes das 7h, painel honesto |
| licença do robô cobrada por usuário | 💭 alta | custo por corretora | pergunta comercial; entra no preço do Auxiliar |
| senha do robô expira (📊 `diasParaExpirarSenha`) | alta | noite perdida | alerta N dias antes; a corretora troca na tela de conexões |
| renovação sem cotação anterior no Agger | ❓ → E2 | cai para "confirmar dado" | coleta com o corretor/cliente (EXTRA-004 reusa) |
| seguradora fora de madrugada | ❓ → E3 | "aguardando seguradora" às 7h | nova tentativa até o corte; recalcular às 7h30 |
| o cálculo do robô "entra" no negócio que um humano está mexendo | 📊 "Item calculado recentemente" incorpora versão | confusão de versões | robô identificado; versão marcada; nunca mexe em negócio com versão humana < 24 h |
| cruzamento de corretora | — | P1 | conexão por `company_id`; lock por conexão; teste com 2 tenants (CLAUDE.md §7) |
| HAR com senhas vaza | baixa | senhas de 17 portais | P-E002-HAR · troca AGORA (caixa #5) |
| 🔴 **a Agger é dona dos DOIS elos** — a InfoCap (a lista de renovações) e o Aggilizador (o cálculo) | 💭 média | se ela negar acesso ou lançar a própria renovação automática (❓ a permissão `RENOVACOES_PENDENTES` aparece oculta no login, RP §6), cai o produto inteiro, não "um transporte" | pergunta direta na conversa comercial (caixa #2); decisão de produto do Founder se ela disser não |
| **a porta `QuoteProvider` ainda não está provada como porta** — há um só adaptador previsto | 📊 1 adaptador | isola o código, não o negócio; o `PolicyDataProvider` só virou porta de verdade com o 2º adaptador (`PdfOnlyProvider`) | nomear um 2º candidato (outro multicálculo, ou 2–3 seguradoras pelo Portal Worker) e a fixture de contrato que os dois passam |
| **perguntas que uma corretora grande fará** e que ainda não têm resposta | ❓ | venda travada | (a) calcular 15–17 seguradoras em TODA renovação mexe na **taxa de conversão de cotação** da corretora junto às seguradoras? (b) **várias filiais / várias contas** Agger: quem vê qual renovação, qual robô calcula? (c) que **fatia do mercado** usa Agger (e não outro multicálculo) — sem isso o produto é "para quem usa Agger" (CLAUDE.md §13.9) |

---

## 10. Decisões do Founder

**D-E002-01 · O caminho de integração com o Agger**
```text
C  pedir à Agger a API oficial / acordo de integração ........................ 92  (se existir)
B  usar os endpoints da própria tela, COM anuência escrita e usuário robô ..... 84
A  navegador preenchendo a tela como uma pessoa ............................... 58
D  cotar direto nos portais das seguradoras ................................... 25
eu recomendo: pedir C e B NA MESMA CONVERSA com a Agger. A engenharia é a mesma porta.
```

**D-E002-02 · Quem o robô é no Aggilizador**
```text
usuário robô dedicado por corretora (ex.: "AutoBrokers") ...................... 95
login de uma pessoa, só de madrugada .......................................... 35  (derruba a sessão dela; auditoria misturada)
```

**D-E002-03 · Quando calcular** (📊 a cotação vale 5 dias)
```text
apresentar em D-30 (estimativa) + recalcular em D-5 ou quando o cliente aceitar .. 88
um cálculo só em D-15 ............................................................. 68
um cálculo só em D-30 ............................................................. 40  (vence antes do fechamento)
o D-30/D-5 é configuração POR CORRETORA, não constante
```

**D-E002-04 · Quem envia ao cliente**
```text
A  o AutoBrokers prepara; o corretor revisa e envia ............................ 92  (v1)
C  casos simples automáticos, exceções humanas ................................. 70  (depois de 60 dias de A medidos)
B  envio automático por política ................................................ 35  (Approval hoje não funciona — laudo F1a §7)
```

**D-E002-05 · "A melhor proposta"**
```text
rótulos transparentes: menor preço · mais parecida com a atual · maior cobertura ·
menor franquia · destaque da corretora (escolhido por gente) ....................... 94
uma "recomendação" escolhida por IA ................................................ 30
```

**D-E002-06 · Como a 003 se divide** (CLAUDE.md §9: nenhuma SPEC em duas sessões; 💭 14–22 h não cabem num chat)
```text
003-A "a fundação" (fatias 1–2) → 003-B "o ciclo de renovação" (fatias 3–5), um chat cada .... 88
proposta própria, com outro número, para a fundação, antes da 003 ........................ 74
uma 003 só, num chat ...................................................................... 70
eu recomendo 003-A/003-B. Nenhuma fatia é "herdada" pela 004 (seria corte silencioso). Nome e número finais: seus.
```

**D-E002-07 · A posição na fila** (📊 fila vigente: 001.9 → 001.0 → triagem → EXTRA-002 → 099 → EXTRA-003)
```text
parte 2 da 002 assim que a caixa do Founder estiver feita; 003 logo depois da triagem ..... 78
manter 099 (canais) antes da 003 ...................................................... 65
```
💭 A diferença é pequena porque não medi o peso da 099; por isso vai a você.

**D-E002-08 · Reclassificar a D-PILOTO-16:** o Agger/Aggilizador entra como **`QuoteProvider`** (multicálculo), não como adaptador de gestão da SPEC-101. Um eventual "Agger ONE" de gestão continua cabendo na 101. → **90** × manter a D-PILOTO-16 como está **40**.

---

## 11. 📋 CAIXA DO FOUNDER — o que só a sua mão faz

| # | o que | por quê | custa esquecer | bloqueia? |
|---|---|---|---|---|
| 1 | **Confirmar a conexão "InfoCap RESULTA" dentro da Amandus** (21/09 20:29) | 📊 a carteira da Resulta está sendo lida sob outra corretora; a Resulta ficou sem conexão | P1 de isolamento; E0 não roda para a Resulta | **SIM, para E0** |
| 2 | Conversar com a Agger: API oficial? anuência para acesso programático? preço de 1 usuário robô? | D-E002-01 | a parte 2 não roda; a Renovação Feita não tem motor | **SIM, para E1–E4** |
| 3 | Criar o usuário robô no Aggilizador da Resulta (e da AutoFleet) | sessão única | derrubaria a Ellen | SIM, para E1 |
| 4 | Guardar a senha do robô no AutoBrokers (tela de conexões), nunca em arquivo | CLAUDE.md §7 e §13.3 | — | SIM, para E1 |
| 5 | 🔴 **TROCAR AGORA** a senha do usuário do Aggilizador que gravou as capturas **e** as senhas dos portais das seguradoras que aparecem nelas. Os HARs foram gravados na sessão de uma pessoa da corretora e contêm a senha dela no Aggilizador e as senhas dos portais (📊 RP §1, §2.1). Depois: extrair só as fixtures de RESPOSTA redigidas (EXTRA-003 §3.5) e apagar os HARs; nunca anexar a chat, drive ou e-mail | P-E002-HAR | senhas de uma pessoa e de ~15 portais de seguradora expostas | não (mas é a primeira coisa a fazer) |
| 6 | Rodízio recomendado das **credenciais de produção coladas no chat desta sessão** (chaves de API, banco, portais): elas passaram a existir em mais um lugar | CLAUDE.md §13.3 | segredo em lugar não controlado | não |
| 7 | Decidir D-E002-01 a 08 | §10 | — | não (há padrão recomendado) |

---

## 12. Definição de concluída (parte 2)

- [ ] E0–E4 rodados, cada um com linha de controle, números 📊 no relatório
- [ ] G1, G5, G13, G14, G18 verdes ou FAIL com causa
- [ ] a equação §5 refeita com N, T, P medidos
- [ ] nenhuma credencial, token, CPF ou placa em arquivo versionado (`grep` no diff)
- [ ] relatório com EXECUTION CARD e telemetria; `git push` com a saída colada
