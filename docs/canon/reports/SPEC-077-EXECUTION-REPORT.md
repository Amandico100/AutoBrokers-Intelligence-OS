# SPEC-077 — Portal Intelligence Lab

**Relatório de execução** · 17/08/2026 · branch `feat/spec077-portal-intelligence-lab`

| | |
|---|---|
| Commit base | `daeda65` (SPEC-075 concluída) |
| Auditoria prévia | [SPEC-077-AUDIT.md](SPEC-077-AUDIT.md) |
| Migrations | **nenhuma** |
| Dependências novas | **nenhuma** |

---

## 1. O que mudou, em uma frase

Os 142 MB de HAR que dormiam em `docs/intake/` viraram **218 endpoints
documentados em 5 seguradoras** — e a ferramenta que fez isso encontrou o que eu
não tinha achado lendo com os olhos.

---

## 2. A auditoria mudou a SPEC, e ela estava certa

A SPEC-077 foi escrita antes de a 075 existir e contra um upstream que a
auditoria mostrou ser diferente do imaginado. Três correções:

### 🔴 O `browse` CLI saiu inteiro

📊 Cinco das oito skills do `browserbase/skills` dependem dele. E o
`package.json` dele aponta `repository` para dois repositórios que devolvem
**404** — o código que abre o CDP e captura os corpos **não é auditável**.

Não precisamos: 📊 confirmado nesta instalação que o Playwright já tem
`context.new_cdp_session`, `CDPSession.send/on/detach`, `context.route` e
`page.route`. **Zero Node, zero Browserbase, zero dependência nova.**

### 🔴 A ordem foi invertida: `browser-to-api` primeiro

A SPEC manda DeepTrace → captura → inferidor. Fizemos o contrário, e o motivo
decisivo é que **DeepTrace não ajuda a SPEC-076**: ele roda dentro do nosso
worker, e na 076 quem navega é o Founder, no Chrome dele, porque o robô ainda
não completa o fluxo.

HAR-first entrega hoje. E dá um conjunto de validação que nenhum trace novo
daria.

### 🟠 AutoBrowse e Browserbase Remote viraram pendência

O loop *"executa → lê trace → uma hipótese → repete"* **é o que já fazemos
nesta conversa**, com subagentes e juízes, e com julgamento humano no meio.
E 📊 não há um único portal medido que exija browser remoto — o anti-bot da
Allianz caiu com `--headless=new`.

---

## 3. O que o inferidor encontrou

### 3.1 🔴 Os endpoints que a SPEC-076 declara desconhecidos

A [SPEC-076](../specs/SPEC-076-vidros-do-pedido-ao-acompanhamento.md) §2.2 diz
que não há endpoint conhecido para escolher loja e agendar, e pede captura
manual. **Estavam no HAR desde a 074:**

```
GET  agendamentos/opcoes-disponiveis    DisponibilizarAgendamento,
                                        PermiteVistoriaMobile, ExibirAvisoVistoria
GET  agendamentos/datas-disponiveis     {"Mes":8,"Dias":[15,17,18,19,...]}
GET  agendamentos/horarios-disponiveis  TempoPermanencia:90, TempoServico:75, Blocos
POST lojas/consultar-distancias         {"Distancia":"9,2 km","TempoDuracao":"13 min"}
GET  atendimentos/livres-escolhas/validar  ValorFranquiaCredenciado: 195
```

Eu parei de ler os 58 MB no motor de perguntas. A máquina não para.

### 3.2 O host da API quase nunca é o host do portal

📊 Descoberta que mudou o modelo de dados:

| | navega em | API em |
|---|---|---|
| Maxpar | `abraseuatendimento.com.br` | `api.autoglass.com.br` (73 JSON) |
| **MAPFRE** | — | **`dwwngb2iz4xom.cloudfront.net`** (62) |
| **Yelum** | `novomeuespacocorretor…` | **`integracao.grupohdiseguros.com.br`** (37) |

As duas últimas eu não sabia. Nenhuma seria achada procurando por
`first_party` — para o classificador elas **são** terceiros, e de DNS elas são
mesmo.

### 3.3 O resultado

```
Maxpar    35 endpoints  ·  12 de escrita
MAPFRE    14
Yelum    115
Zurich    40
Tokio     14
─────────────
         218 endpoints, 0 PII bloqueante em todos
```

---

## 4. 🔴 O vazamento que eu abri, e o que ele ensinou

Construí o pipeline inteiro contra PII e abri uma porta lateral pelo campo mais
inocente do schema: `Forma.exemplos` guardava o valor **cru** e o emitia como
`examples`.

📊 O artefato gerado saiu com **410 achados de PII**: 340 chassis, 16 placas, 4
CPFs, 2 e-mails, 47 tokens. Destino: `docs/generated/`, que **é versionado** —
ao contrário de `docs/intake/`, que está no `.gitignore` exatamente por isso.

Três consertos, todos estruturais, e cada um encontrado só porque o anterior foi
medido:

**1. Redigir na COLETA, não na emissão.** Mesma regra dos cabeçalhos: o que
nunca entrou não vaza por um `print` de depuração. 2.101 KB → 94 KB.

**2. Usar o detector mais estrito disponível.** O `redigir_texto` da 073 **não
conhece chassi**; o `varredura_de_pii` da 075 conhece e valida a estrutura do
VIN. Dois VIN reais tinham atravessado o primeiro conserto.

**3. O CAMINHO também é PII.** A API da MAPFRE tem
`/api/1.0.0/client/12097137725_1/interactions`. O `normalizar_path` da 073
preserva número colado em palavra — a regra **certa** para distinguir `passo5`
de `passo6`, e a regra **errada** aqui.

E o conserto do terceiro ainda estava errado: eu exigia **exatamente** 11 ou 14
dígitos, e o segmento real limpo dá **12** (CPF + sufixo `_1`). A pergunta certa
não é *"este segmento É um CPF?"*, é *"este segmento CONTÉM um?"*.

---

## 5. O que foi construído

| Módulo | O que faz |
|---|---|
| `lab/trafego.py` | HAR e DeepTrace convergem para um formato só; cabeçalho sensível **não entra** |
| `lab/inferir.py` | Tráfego → OpenAPI 3.1 candidato, com confiança e lacunas |
| `lab/ciclo.py` | Escada `OBSERVED→…→APPROVED_MATERIAL` + detector de drift |
| `portal_worker/deep_trace.py` | Observador CDP **passivo**, allowlist de 10 métodos |
| `portals/injecao.py` | 15 falhas injetáveis no replay da 075 |
| `scripts/portal_factory.py` | `lab har`, `lab api-infer`, `lab drift`, `lab promote` |
| `scripts/gerar_matriz_de_portais.py` | matriz gerada (075) agora publica a chave canônica |

### O que garante que candidato não vira contrato

`promover()` recusa **salto de degrau mesmo com todas as evidências** — cada
degrau produz a prova que o seguinte exige. `APPROVED_MATERIAL` pede oito
evidências, incluindo aprovação do Founder. Não há caminho de código que chegue
lá sozinho.

E `pode_usar_em_producao(..., para_escrever=True)` só aceita
`APPROVED_MATERIAL`. Nada abaixo, nunca.

### O que garante que o DeepTrace não age

Uma **allowlist fechada de 10 métodos** e uma função por onde todo `send` passa.
`Input.*`, `Runtime.evaluate`, `Page.navigate`, `Fetch.*`, `Storage.*`,
`Network.setCookie` — todos recusados, com o motivo escrito. Método inventado
também é recusado: é allowlist, não blacklist.

---

## 6. Testes

| | |
|---|---|
| `test_spec077_portal_lab.py` | **108 asserções** |
| Mutações dirigidas | **13**, todas detectadas |

### As 13 mutações

| # | Mutação | Vermelhas |
|---|---|---|
| M1 | cabeçalho sensível passa a entrar | 6 |
| M2 | tudo vira obrigatório (1 amostra decide) | 3 |
| M3 | `x-enum-observado` vira `enum` de contrato | 2 |
| M4 | endpoint nasce aprovado | 3 |
| M5 | salto de degrau permitido | 2 |
| M6 | escrita aceita `APPROVED_READONLY` | 1 |
| M7 | campo que sumiu deixa de quebrar | 3 |
| M8 | um drift que quebra deixa de fechar | 2 |
| M9 | DeepTrace aceita qualquer método CDP | 9 |
| M10 | telemetria de APM deixa de ser reconhecida | 2 |
| M11 | `OPTIONS` de CORS volta a virar endpoint | 1 |
| M12 | host: telemetria volta a contar | 1 |
| M13 | um método de ação entra na allowlist | 1 |
| — | restaurado | **0** |

### Duas mutações me ensinaram algo

**A M12 não foi detectada na primeira rodada.** Eu tinha asserção sobre
`hosts_de_api` (de onde vem o JSON) e **nenhuma** sobre `host_portal` (quem é a
casa) — que é o campo que alimenta `classificar_origem`. Com ele errado, o
portal real vira `third_party` e o rastreador vira a casa. O buraco foi fechado
com o par que exercita o HAR sem documento nenhum.

**A M9 travou o teste** na primeira tentativa — mas a culpa foi da mutação, não
do teste: meu recorte engoliu constantes e o módulo nem importou. Refeita
corretamente, acende 9 vermelhas.

---

## 7. Gates

```
108/0  asserções da SPEC-077
218    suites verdes no backend
 17    vermelhas — as MESMAS pré-existentes no baseline daeda65
  0    tsc --noEmit
 13    mutações dirigidas, 13 detectadas
  0    erros no `portal_factory audit` e `validate`
  0    PII bloqueante nos 5 artefatos gerados
  0    dependências novas · 0 migrations · 0 runtimes novos
```

---

## 8. O que NÃO foi feito, e por quê

| Item | Motivo |
|---|---|
| AutoBrowse | pendência: exige `ANTHROPIC_API_KEY` + `browse` CLI; e o loop já é o que fazemos com subagentes |
| Browserbase Remote / `BrowserProvider` | pendência com gatilho: **zero portais medidos exigem** browser remoto |
| `webmcp-gen` | rejeitado: exige Stagehand |
| Browserbase Functions | rejeitado: seria um segundo runtime |
| `browse` CLI | rejeitado: fonte não auditável |
| `PortalNetworkPolicy` genérica | ficou para a próxima leva; o padrão do `vidros_api.host_permitido` já existe e é o modelo |
| Ligar DeepTrace em produção | nasce desligado; exige janela |

---

## 9. Declaração

**Nenhuma arquitetura paralela foi criada.** Um Portal Worker. Uma Factory (os
comandos `lab` entraram nela, não ao lado). Um registry. Um redator — o Lab
importa `redaction.py` e `replay.py`, não reimplementa. Um Work OS, intocado.

Nenhuma Skill de engenharia foi exposta ao corretor. Nenhum agente recebeu
browser, CDP, shell ou chave de terceiro.

---

## 10. FATO · INFERÊNCIA · RECOMENDAÇÃO

**FATO** — 108 asserções verdes; 13 mutações detectadas; 218 endpoints
descobertos em 5 seguradoras com 0 PII bloqueante; os 4 endpoints que a
SPEC-076 declara desconhecidos foram encontrados; `audit` e `validate` verdes;
218 suites verdes e 17 vermelhas pré-existentes; `tsc` exit 0.

**INFERÊNCIA** — o contrato inferido descreve o que **aconteceu nas capturas**.
Um campo opcional pode ser obrigatório numa borda que não capturamos; um `POST`
que respondeu 200 pode não ser idempotente. É por isso que tudo nasce
`OBSERVED` e a escada tem oito evidências no topo.

**RECOMENDAÇÃO** — usar os endpoints de agendamento descobertos para **reduzir**
o escopo da captura manual da SPEC-076: em vez de 3 capturas completas, o
Founder pode focar no que ainda falta de verdade — a **quarta captura**, dias
depois, que continua sendo a única forma de descobrir como se consulta um
atendimento antigo. Ver a atualização proposta em PENDÊNCIAS.
