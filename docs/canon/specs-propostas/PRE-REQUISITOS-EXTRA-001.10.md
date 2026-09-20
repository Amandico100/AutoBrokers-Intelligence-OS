# O que você precisa ter na mão ANTES de abrir o chat da EXTRA-001.10

> **Para:** Amandus (Founder) · **Escrito em:** 20/09/2026, sobre a `main` em `b3d88f1`
> **Assunto:** o portal de vidros de ponta a ponta — o que providenciar, em ordem, antes de colar o prompt
> `docs/canon/specs-propostas/PROMPT-DE-ABERTURA-EXTRA-001.10-PRONTO.md` num chat novo.

---

## Primeiro, a resposta direta à sua pergunta

> **"Preciso fazer um acionamento de para-brisa na Yelum?"**

**Para começar a SPEC, não. Para ela fechar 100 %, sim — e é a única coisa que só você (ou a Regina) consegue dar.**

Dividindo em português claro:

| o que | depende da captura de para-brisa? |
|---|---|
| **Lataria / martelinho na Yelum, do WhatsApp até o comprovante** | ❌ **Não.** Já temos a captura inteira (09/09). Esse é o caminho que fecha nesta SPEC, e é o canário. |
| Gravar peça, causa e cidade no portal (o `PATCH` que falta), cadastrar solicitante e corretor, mapa certo de seguradoras, cidade do serviço, o freio por job | ❌ Não. É código, sobre material que já existe. |
| **Mostrar** ao segurado as lojas, as distâncias, os dias e os horários | ❌ Não. A captura de 15/08 já traz a lista de lojas e o calendário. |
| Perguntas de retrovisor, farol, lanterna, para-choque | ❌ Não. A lista de peças de cada apólice já prova essas. |
| **Confirmar o agendamento** (o último clique: loja, dia e hora) | ✅ **Sim.** 📊 Em 4 capturas, esse POST **nunca saiu** — a Regina cancelou antes, e uma vez a grade voltou vazia. Sem ver uma vez, o código fica escrito e **desligado**. |
| Perguntas específicas de **para-brisa** (sensor de chuva, faixa degradê, ADAS) e de vigia (desembaçador) | ✅ Sim. O agente até pergunta, mas a resposta não tem como ir ao portal enquanto não virmos a tela. |
| A régua do trincado ("maior que uma moeda de 1 real" × os 10 cm que o código usa hoje) | ✅ Sim. A régua certa está escrita no texto da pergunta do portal, e essa tela é a do para-brisa. |
| Serviço a **domicílio** (técnico na casa do segurado) | ✅ Sim — e é uma captura **diferente** (a nº 2). |
| Anexar **fotos** e gerar o **link de vistoria** | ✅ Sim — captura nº 3, e precisa de uma apólice com vistoria habilitada. 📊 Nas capturas que temos, `PermiteVistoriaMobile` veio `false` em todas. |

**Conclusão prática:** abra o chat **hoje**, sem esperar. A execução começa por lataria. Se no meio do caminho
aparecer uma demanda real de para-brisa, a captura entra e a SPEC fecha mais. Se não aparecer, ela fecha com
vidraçaria em 99 % e o último clique escrito, testado offline e desligado — com o gatilho anotado para voltar.

🔴 **E o que você NÃO deve fazer:** inventar um acionamento de para-brisa só para capturar. Abrir um pedido no portal
**aciona uma loja de verdade** (D-PILOTO-05). Só com demanda real de um segurado. O detalhe está no
`docs/canon/specs-propostas/GUIA-DE-CAPTURA-PORTAL-DE-VIDROS.md`.

---

## OBRIGATÓRIO — sem isto o chat trava no meio

### 1. Os serviços implantados e no ar
**Por quê:** a SPEC termina com um acionamento real. Se o `portal-worker` estiver rodando código velho, o canário
prova a coisa errada. E há uma implantação **pendente desde a 001.7**.
**Tempo:** 10 min.
**O que fazer:** no EasyPanel, **Implantar** na ordem `smith-api` → `smith-worker` → `portal-worker` → `smith-web`.
**Como conferir:** no console do **smith-api**, dentro de `/app`:
```
python backend/scripts/conferir_o_que_esta_no_ar.py --ligar
```
Você quer ler **PODE LIGAR**. Se vier "NÃO PODE LIGAR", ele diz qual trava está fechada, uma por linha.
⚠️ Esse comando roda no **smith-api**. Comandos que citem `portal_worker` **não rodam lá** — o `portal_worker` mora
no contêiner `portal-worker`, que é outro. (📊 Foi exatamente isso que quebrou um comando entregue na 001.7.)

### 2. Uma apólice Yelum ativa, de veículo seu, com cobertura de **lataria/martelinho**
**Por quê:** é o canário. O robô vai abrir um pedido **de verdade** nessa apólice, até o comprovante.
**Tempo:** 5 min para confirmar com a Regina; mais tempo se precisar contratar.
**Como conferir:** a própria Regina entra no portal, passo 1, com o CPF e a placa; se a apólice aparece e a peça de
lataria está na lista de "Peça danificada", está bom. **Não precisa concluir** — parar no passo 1 não abre nada.

### 3. O CPF do titular dessa apólice, **por variável de ambiente**
**Por quê:** o robô precisa dele para o canário, e ele **nunca** pode ir para o chat, para o código ou para o
relatório.
**Tempo:** 2 min.
**O que fazer:** coloque no ambiente do `portal-worker` (não no chat, não em arquivo do repositório).
**Como conferir:** o executor confere **presença/ausência**, nunca o valor.

### 4. As credenciais do portal de vidros no cofre (Vault)
**Por quê:** sem elas o worker não entra no portal. O portal de vidros é público em parte, mas o fluxo completo usa a
conexão da corretora.
**Tempo:** 5 min (provavelmente já está: os acionamentos anteriores funcionaram).
**Como conferir:** o executor roda o `login check` do portal e reporta ✅/❌ — sem mostrar segredo.

### 5. Saber quais são os números de teste (TESTE-A / TESTE-B)
**Por quê:** nenhuma mensagem sai para pessoa real fora do canário. O agente conversa com o número de teste.
**Tempo:** 2 min.
**Como conferir:** já estão no ambiente; o executor confirma presença.

### 6. Sua decisão sobre **quem cancela** se o canário morrer no meio
**Por quê:** se o pedido nascer e o robô morrer depois, **ninguém reexecuta** (e isso está certo). Cancelar é mão
humana, pelo portal, e quem sabe fazer é a Regina.
**Tempo:** 1 min — é só combinar com ela que ela fica disponível na janela do canário.
**Como conferir:** ela confirma por mensagem que está por perto naquela hora.

---

## AJUDA MUITO — acelera, melhora a nota, mas não trava

### 7. 🔴 A captura nº 1 — para-brisa na Yelum até o agendamento confirmado
**Por quê:** é a única coisa que destrava o último clique de vidraçaria, as perguntas de para-brisa e a régua certa do
trincado. **Só vale com demanda real de um segurado.**
**Tempo:** o acionamento que a Regina já faria, mais ~5 min de preparo e ~2 min de exportação.
**Como fazer:** `docs/canon/specs-propostas/GUIA-DE-CAPTURA-PORTAL-DE-VIDROS.md` (o cartão de bolso) e
`docs/canon/guias/ROTEIRO-DE-CAPTURA-PORTAL-DE-VIDROS.md` (tela por tela).
**Como conferir que ficou certo:** o arquivo `.har` tem **10 MB ou mais** (um HAR de 200 KB foi exportado sem
conteúdo e não serve), e existe pelo menos um print da **grade de horários**.

### 8. A Regina disponível para ler a conversa do canário
**Por quê:** a máquina prova que o portal aceitou; só uma pessoa prova que a conversa soou humana.
**Tempo:** 10 min.
**Como conferir:** ela responde "eu mandaria essa mensagem" — ou aponta o que soou de robô.

### 9. Reativar os grupos de suporte das duas corretoras
**Por quê:** 📊 estão desativados desde 10/09 (P-E0017-01). Sem destino ativo, um handoff do portal não tem para onde
ir — e "tela desconhecida vira handoff" é um dos resultados desta SPEC.
**Tempo:** 5 min no painel.
**Como conferir:** `conferir_o_que_esta_no_ar.py --ligar` deixa de reclamar do destino de alerta.

### 10. As senhas da Allianz e da Mapfre renovadas
**Por quê:** não é desta SPEC, mas está aberto desde 18/08 e atrapalha toda medição de portal.
**Tempo:** 15 min.
**Como conferir:** o login check dessas duas passa.

---

## PODE VIR DEPOIS — não segure o chat por causa disto

- **Captura nº 2** — a mesma peça escolhendo **domicílio**, num CEP atendido (📊 nas duas capturas que temos, o portal
  respondeu `AtendeServicoMovel: false`, então nem apareceu).
- **Captura nº 3** — uma apólice **com vistoria habilitada**, até o upload da foto. É o que tira o link de vistoria
  da mão da Regina.
- **Capturas 4–7** — retrovisor, lanterna bipartida, farol, vigia: só o print da lista de peças aberta + a tela de
  80 %.
- **Captura 8** — "Consultar atendimento" e "Área do Segurado" (para o agente responder "como está meu pedido?").
- **Captura 9** — uma seguradora fora de Yelum/Porto (Allianz, HDI, Tokio, Mapfre, Azul), só até o passo 3.
- **Captura 10 — Bradesco.** 🔴 Já está decidido (D-PILOTO-17): **primeiro** uma captura no `abraseuatendimento` com o
  slug `bradesco`; o outro portal (`agendeseuservico`) só entra se a captura provar recusa. **Nenhuma linha de código
  para o Bradesco antes disso.**
- **Capturas 11–12** — lataria com mais de uma peça; roda/pneu na Porto **com** cobertura.
- As decisões de corte do piloto (D-E0017-03/04), que são da 001.7 e não bloqueiam esta.

---

## O que o material que você já depositou cobre — e o que falta

📊 Medido em 20/09/2026 em `docs/intake/materiais/portal-vidros/` — **365 arquivos, 208 MB**:

| pasta | data | o que tem | até onde vai |
|---|---|---|---|
| `YELUM/YELUM 1` | 09/09 | 1 HAR de 29 MB · 2 páginas salvas (passo 3 e a tela final de 100 %) · 4 prints | 🟢 **Lataria/martelinho ponta a ponta** — do início ao comprovante. Esse ramo não tem escolha de loja nem agendamento (a seguradora indica) |
| `YELUM/YELUM VIDROS ANTIGO` | 14–15/08 | 1 HAR de 26 MB · 5 páginas (passo 3, passo 5, 80 %, **99 % com a lista de lojas**, cancelado) · 3 PDFs · a explicação da Regina | 🟡 **Vidro de porta até um clique do fim**: lojas com distância e calendário apareceram; a grade de horários voltou vazia e ela cancelou |
| `PORTO` | 15/08 | 2 HAR (lanterna 22 MB, roda sem cobertura 10 MB) · 4 páginas salvas | 🟡 incompletos de propósito; provam que Porto e Yelum são o **mesmo motor** e mostram o preflight recusando por falta de cláusula |
| `PERGUNTAS QUE HUMANO FAZ…docx` | 12/09 | as perguntas que a Regina faz ao segurado, por tipo de dano | 🟢 vira a lista de perguntas do agente |

**O que NÃO existe em lugar nenhum do material** (e por isso está na lista de capturas):

```
❌ o questionário do PARA-BRISA          (só temos vidro de porta e lanterna) — é a peça mais comum
❌ a grade de horários com horário real  (📊 a única vez que apareceu veio vazia)
❌ o clique que CONFIRMA o agendamento   (nenhuma das 4 capturas chegou lá)
❌ o subfluxo de DOMICÍLIO inteiro       (formas de pagamento, dia/hora do técnico)
❌ o anexo de FOTOS e o link de vistoria (zero requisições de upload em tudo que temos)
❌ qualquer coisa do BRADESCO
❌ lataria com MAIS DE UMA peça · roda/pneu COM cobertura
❌ 34 das 38 seguradoras do portal       (temos Yelum e Porto; falta o passo 1 das outras)
```

---

## As variáveis de ambiente de que o portal depende

Por **nome** — os valores nunca aparecem aqui nem no chat. 📊 Conferidas no código em 20/09/2026:

**No contêiner `portal-worker`** (é ele quem abre o navegador e fala com o portal):

| nome | onde é lida | para que serve |
|---|---|---|
| `PORTAL_REAL_ENABLED` | `portal_worker/worker.py:263` | 🔴 o interruptor geral: com ela desligada, nada real acontece |
| `PORTAL_EFEITO_MATERIAL_LIBERADO` | `portal_worker/journeys/__init__.py:291` | 🔴 o freio da SPEC-073: libera as ações que **criam fato no mundo**. ⚠️ Hoje ela é global — ligar libera **todos** os jobs de vidros em voo naquele worker. É por isso que a SPEC constrói um **freio por job** (P0-6) **antes** do canário |
| `PORTAL_VIDROS_API_FIRST` | `portal_worker/journeys/vidros_apifirst.py:56` | liga o caminho novo. **Nasce desligada**; desligá-la é o rollback em uma linha |
| `PORTAL_VAULT_KEY` | `portal_worker/vault.py:11` | abre o cofre das credenciais do portal |
| `PORTAL_WORKER_CONCURRENCY` | `portal_worker/leases.py:305` | quantos jobs ao mesmo tempo |
| `PORTAL_HEADLESS_MODE` · `PORTAL_JOB_TIMEOUT_SECONDS` · `PORTAL_POLL_SECONDS` | `worker.py:335, 23, 21` | navegador sem tela, tempo limite, ritmo da fila |
| `PORTAL_PROXY_DEFAULT` / `PORTAL_PROXY_<CHAVE>` | `worker.py:1094` | saída de rede por portal |
| `PORTAL_VISION_ENABLED` · `_PROVIDER` · `_MODEL` | `perception.py:386, 397` · `adaptive.py:405` | o "olho" que lê a tela quando o texto não basta |

**No contêiner `smith-api`** (é ele quem cria o pedido e conversa com o segurado):

| nome | onde é lida | para que serve |
|---|---|---|
| `PORTAL_WORKER_URL` | `app/api/portal.py:87` | endereço do worker |
| `PORTAL_VAULT_KEY` | `app/services/portal_vault.py:16` | mesmo cofre, do outro lado |
| `PORTAL_EXECUTION_GATEWAY_MODE` · `PORTAL_GATEWAY_WAIT_S` | `app/services/portals/gateway.py:69, 60` | como e por quanto tempo a API espera o worker |
| `PORTAL_EVIDENCE_BUCKET` · `PORTAL_EVIDENCE_RETENTION_DAYS` · `PORTAL_EVIDENCE_PURGE_ENABLED` | `app/services/billing_collection.py:3108` e vizinhas | onde ficam as provas do que o robô fez, e por quanto tempo |

🔴 **Nenhuma variável nova nasce nesta SPEC.** O que muda é o **estado** das três primeiras — e elas voltam ao que
eram assim que o canário termina. O executor tem de **provar**, com saída colada, que voltaram.

---

## Em uma folha: a sua sequência

```
1. Implantar tudo no EasyPanel (10 min)
2. Rodar `conferir_o_que_esta_no_ar.py --ligar` no smith-api até dar PODE LIGAR
3. Reativar os grupos de suporte das duas corretoras (5 min)
4. Confirmar com a Regina a apólice Yelum de lataria do seu veículo de teste (5 min)
5. Pôr o CPF do titular no ambiente do portal-worker (2 min)
6. Combinar com a Regina a janela do canário — e que ela cancela pelo portal se algo morrer no meio (1 min)
7. Abrir o chat novo e colar o PROMPT-DE-ABERTURA-EXTRA-001.10-PRONTO.md
8. Em paralelo, se e quando aparecer um para-brisa de verdade: a captura nº 1, pelo guia
```

**Não espere o item 8 para fazer o item 7.**
