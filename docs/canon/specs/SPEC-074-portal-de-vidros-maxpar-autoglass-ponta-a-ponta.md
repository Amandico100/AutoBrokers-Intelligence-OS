# SPEC-074 — Portal de Vidros ponta a ponta
## Maxpar/Autoglass · roteamento correto · coleta antes do portal · API-first · 80% seguro · protocolo/franquia/vistoria · continuidade sem duplicidade · consulta e preparação do go-live com Regina

> **Status:** proposta de execução — executar somente depois da SPEC-073 estar verde
> **Criado em:** 15/08/2026
> **Branch sugerida:** `feat/spec074-vidros-ponta-a-ponta`
> **Base remota analisada:** `main @ 0ffcbed44ba012d9a41e23823729837b6defd076`
> **Projeto Supabase lido:** `dcajcvlzcjbmyapmklil`
> **Autoridade superior:** `CLAUDE.md` + decisões vigentes do Founder + SPEC-071 + SPEC-073
> **Princípio central:** melhorar o corredor de vidros usando o Portal Worker existente; não criar um segundo motor e não quebrar cobrança, portais autenticados, idempotência, HITL ou isolamento multi-tenant.

---

# 0. DECISÃO DESTA SPEC

Esta SPEC fecha o **corredor de atendimento de vidros** como uma capacidade real do AutoBrokers.ai.

O resultado esperado não é “o robô clicar melhor”. O resultado esperado é:

```text
conversa com o segurado
→ identificar corretamente o trabalho
→ localizar a apólice real na InfoCap
→ saber tudo que já pode ser sabido antes de abrir o portal
→ escolher o canal correto
→ abrir o Portal de Vidros correto
→ conferir que é a apólice/veículo corretos
→ responder o que é fato sem LLM
→ ler dinamicamente o que o portal realmente oferece
→ usar inteligência apenas onde há julgamento
→ parar fechado quando houver ambiguidade material
→ confirmar o pedido somente quando o gate real permitir
→ registrar o efeito material antes/depois dele
→ capturar imediatamente protocolo + franquia + link de vistoria
→ nunca duplicar um atendimento já aberto
→ continuar/acompanhá-lo pelo próprio atendimento existente
→ devolver ao agente e ao humano um resultado completo e acionável
```

A SPEC-073 torna o **Portal Worker transversalmente robusto**. A SPEC-074 usa essa fundação para tornar o **Portal de Vidros excelente de ponta a ponta**, sem transformar uma necessidade específica em arquitetura paralela.

## O que esta SPEC NÃO autoriza

Ela não autoriza o Claude Code a:

- reescrever o Portal Worker do zero;
- criar outro browser worker para Maxpar/Autoglass;
- criar outro “agente de vidros” concorrendo com Smith/Core/atendimento;
- instalar um framework browser-agent por cima do que já funciona sem prova de ganho;
- remover o caminho determinístico atual;
- remover a trava do 80%;
- reexecutar um atendimento que talvez já tenha sido criado;
- clicar em cancelamento, reagendamento, escolha de agenda ou outra mutação material só para “testar”;
- inventar endpoint interno do Maxpar/Autoglass;
- transformar captura real com PII em fixture versionada;
- criar tabela nova apenas para guardar dados que já cabem em `portal_jobs.evidence`, `params`, sessions ou storage existente;
- mexer na Cobrança Feita para facilitar esta SPEC.

---

# 1. LEITURA OBRIGATÓRIA ANTES DE EDITAR CÓDIGO

O executor deve ler, nesta ordem:

1. `CLAUDE.md`;
2. `docs/canon/EXECUTION-MASTER-PLAN.md`;
3. `docs/canon/FOUNDER-DECISIONS.md`;
4. `docs/canon/MIGRATIONS-AUTHORITY.md`;
5. `docs/canon/specs/SPEC-071-atendimento-ponta-a-ponta-e-go-live.md`;
6. a SPEC-073 já implementada e o relatório final dela;
7. `docs/canon/O-PORTAL-DE-VIDROS-TELA-POR-TELA.md`;
8. `backend/portal_worker/worker.py`;
9. `backend/portal_worker/journeys/__init__.py`;
10. `backend/portal_worker/journeys/vidros_lanternas.py`;
11. `backend/portal_worker/adaptive.py`;
12. `backend/app/agents/tools/portal_tool.py`;
13. `backend/app/agents/tools/portal_params.py`;
14. `backend/app/services/perguntas_do_portal_de_vidros.py`;
15. `backend/app/agents/tools/insurer_dispatch_tool.py`;
16. `backend/app/services/insurer_dispatch_service.py`;
17. `backend/app/tasks/vigia_do_portal.py`;
18. testes atuais de vidros e de cobrança.

## Regra de autoridade

Quando houver divergência:

```text
medição mais nova
> decisão vigente do Founder
> documento canônico mais novo
> SPEC antiga
> comentário antigo de código
> memória de conversa
```

Código atual que contradiz evidência mais nova deve ser corrigido. Documento antigo que descreve um estado já superado deve ser atualizado na mesma SPEC.

---

# 2. PREFLIGHT OBRIGATÓRIO

Antes de qualquer alteração:

```bash
git rev-parse --show-toplevel
git branch --show-current
git rev-parse HEAD
git status --short
git log -5 --oneline
```

O executor deve registrar no relatório:

```text
repo real:
branch:
HEAD:
working tree:
commit remoto usado como base:
SPEC-073 encontrada? sim/não
SPEC-073 está implementada? sim/não
flags novas da SPEC-073 presentes? sim/não
```

### Proibição

Se houver trabalho local não commitado, o Claude **não pode** resetar, limpar, trocar branch destrutivamente nem fazer pull que sobrescreva o estado.

A SPEC-074 só começa depois de resolver a posição real da SPEC-073. Se ela ainda não foi implementada, esta SPEC permanece pronta, mas **não é executada por cima do worker antigo como se a 073 já existisse**.

---

# 3. BASELINE MEDIDO QUE ESTA SPEC NÃO PODE DISTORCER

## 3.1 O portal público real

O mapa canônico mede `https://abraseuatendimento.com.br` como portal operado por Maxpar/Grupo Autoglass, atendendo múltiplas seguradoras por uma mesma aplicação.

A página institucional oficial da Autoglass/Maxpar consultada em 15/08/2026 expõe atualmente, no mínimo:

- abrir atendimento;
- consulta de atendimento;
- reagendar atendimento;
- alterar data;
- status do atendimento;
- vistoria para seguro auto;
- seleção de múltiplas seguradoras.

**Fonte externa oficial consultada:** `https://institucional.autoglass.com.br/maxpar/`.

Isso prova que o domínio de trabalho é maior que “clicar até gerar protocolo”. Existe um ciclo de vida do atendimento. Esta SPEC prepara o Portal Worker para utilizá-lo sem inventar telas nem endpoints ainda não medidos.

## 3.2 O que já existe no código e deve ser preservado

O sistema já possui:

- `portal_action` como ferramenta do agente;
- busca de fatos reais na InfoCap;
- `normalize_insurer`;
- `build_portal_params`;
- catálogo `perguntas_do_portal_de_vidros.py`;
- transporte de `especificos`;
- composição de descrição com mínimo do portal;
- `vidros_lanternas.abrir_atendimento`;
- caminho adaptativo;
- vocabulário de peça e matching conservador;
- trava da tela de 80%;
- `confirm` nascendo `False` e sendo liberado pelo mesmo gate do agente;
- idempotência do pedido;
- leitura de protocolo;
- leitura de franquia;
- leitura de link de vistoria;
- registro imediato desses dados em `evidence`;
- Vigia do Portal;
- sessão/cookies e controles transversais do Portal Worker;
- após SPEC-073, checkpoint de efeito, discovery, profiler, redaction e percepção em camadas.

Nada disso é “código provisório a jogar fora”. Esta SPEC compõe o que existe.

## 3.3 O histórico de 39 jobs NÃO é métrica da versão atual

Produção ainda contém:

```text
portal_key=vidros_lanternas
journey=abrir_atendimento
1 done
5 failed
33 needs_human
último desses jobs: julho/2026
```

Esses 39 jobs pertencem à fase de construção/teste do corredor antigo. Eles servem para **autópsia de falhas históricas**, não para declarar que a versão atual tem 2,5% de sucesso.

A SPEC deve manter essa observação explícita em documentação e testes para evitar que um executor “otimize” controles corretos em resposta a uma métrica que não mede a versão atual.

## 3.4 O pedido nasce antes de o fluxo terminar

Fato canônico:

- o protocolo aparece no passo 7;
- ele aparece **antes da escolha final de loja/agenda**;
- a partir desse instante o pedido já existe;
- repetir o fluxo cria outro pedido.

Esse fato governa todo desenho de retry, continuação, recovery e status.

## 3.5 Um atendimento aceita um item

Fato medido no próprio portal:

```text
1 atendimento = 1 item para troca/reparo
```

Se o segurado tiver dois itens/lados danificados, o AutoBrokers precisa tratá-los como unidades distintas de trabalho. Não pode abrir um e responder “pronto” como se ambos tivessem sido tratados.

## 3.6 O registry tem um nome legado que não deve ser “consertado” destrutivamente

Hoje a journey executada usa:

```text
vidros_lanternas.abrir_atendimento
```

Enquanto o catálogo de `portals` do banco contém chaves mais descritivas como:

```text
vidros_abraseuatendimento
vidros_agendeseuservico
```

Isso é uma inconsistência semântica real, mas **não autoriza rename destrutivo**. Existem jobs, testes, vigia, idempotência e código referenciando `vidros_lanternas`.

A estratégia desta SPEC é **alias compatível**, não big-bang rename.

## 3.7 Não há conta Maxpar/Autoglass guardada hoje

Consulta read-only de 15/08/2026 em `portal_accounts` não encontrou conta cujo `portal_key` contenha `vidro`, `maxpar` ou `autoglass`.

Consequência:

- o portal público continua sem credencial;
- qualquer “portal Maxpar do corretor” autenticado precisa ser **medido antes de ser automatizado**;
- o executor não deve inventar URL, login, conta ou fluxo privado;
- a ausência dessa credencial não bloqueia todos os blocos anteriores.

---

# 4. DEFINIÇÃO DE “PONTA A PONTA” PARA ESTA SPEC

“Ponta a ponta” não significa um script monolítico de 80 cliques. Significa que cada estado do trabalho tem dono, entrada, saída, checkpoint e continuação correta.

## Estado desejado

```text
INTAKE
  ↓
POLICY_RESOLUTION
  ↓
PORTAL_ROUTE_RESOLUTION
  ↓
PRECHECK_COMPLETE
  ↓
PORTAL_OPENED
  ↓
POLICY_CONFIRMED
  ↓
DYNAMIC_QUESTIONS
  ↓
READY_TO_CONFIRM_80
  ↓
MATERIAL_CONFIRMATION
  ↓
REQUEST_CREATED
  ↓
PROTOCOL_CAPTURED
  ↓
SERVICE_COMPLETION_PENDING ou SERVICE_COMPLETED
  ↓
STATUS_TRACKABLE
```

Cada transição deve ser observável.

## O que deve estar pronto antes do teste final com Regina

O código deve estar pronto para:

1. receber o pedido do agente;
2. dividir múltiplos itens corretamente;
3. coletar previamente os dados necessários;
4. resolver seguradora e cobertura;
5. selecionar Portal vs WhatsApp vs handoff;
6. abrir o portal público;
7. atravessar o fluxo conhecido;
8. tratar popup/variações de forma medida ou adaptativa;
9. chegar ao 80%;
10. confirmar somente com autorização real;
11. proteger o efeito contra duplicação;
12. capturar os três dados finais já conhecidos;
13. estruturar continuação do mesmo atendimento;
14. consultar/acompanhá-lo quando a forma exata estiver medida;
15. entregar dossiê completo se aparecer algo não mapeado.

## O que legitimamente pode continuar dependendo da execução com Regina

Somente aquilo que **não existe em nenhuma fonte disponível hoje**, principalmente:

- telas reais depois de determinadas escolhas finais;
- campos de agenda/domicílio ainda não medidos;
- fluxo privado que Regina chama de “portal Maxpar do corretor”, se ele exigir login não disponível no sistema;
- inputs exatos da tela “Consultar atendimento” se o portal não os revelar em discovery sem um caso real;
- variações específicas de peça/seguradora que nunca apareceram em captura real.

A SPEC não inventa essas partes. Ela constrói o mecanismo para **medir uma vez e incorporar sem reescrever o motor**.

---

# 5. REGRAS INVIOLÁVEIS

## R1 — Cobrança é linha de controle

Nenhuma alteração desta SPEC pode fazer regressão em:

- Allianz cobrança;
- HDI cobrança;
- Tokio cobrança;
- Yelum cobrança;
- MAPFRE cobrança;
- Zurich cobrança;
- registry de cobrança;
- `billing_collection.py`;
- sessões autenticadas;
- storage de boletos;
- idempotência de cobrança;
- governança de envio.

A SPEC-074 não precisa alterar esses módulos para “facilitar” vidros.

## R2 — um único Portal Worker

Maxpar/Autoglass entra no mesmo:

```text
portal_jobs
→ portal_worker
→ JOURNEYS
→ JourneyResult
→ evidence
→ HITL/checkpoints
```

Sem fila paralela, sem serviço paralelo, sem tabela paralela de jobs.

## R3 — API-first não significa API inventada

Ordem:

```text
1. observar a aplicação real
2. identificar chamadas reais pelo profiler da SPEC-073
3. provar vínculo com a mesma sessão
4. reproduzir somente leitura quando possível
5. aprovar o contrato
6. usar API para o que ela realmente faz
7. browser continua como sessão/fallback quando necessário
```

Nunca:

```text
“parece REST, então vou tentar /api/atendimentos”
```

## R4 — fato não passa por modelo

CPF, placa, versão, chassi, CEP, cidade, UF, seguradora, apólice, nome e dados da corretora são fatos. Se existem em InfoCap/perfil, são transcritos/validados.

## R5 — julgamento não vira `first option`

Peça, causa, lado, posição do trincado, tamanho, cobertura, tipo de serviço, loja, agenda e qualquer decisão que altere o atendimento não podem cair em “primeira opção válida”.

## R6 — “Não sabe” só existe quando o segurado realmente não sabe

O robô não usa “Não sabe” para avançar.

## R7 — confirmação material não é ação de percepção

Visão/LLM pode propor. O `PortalActionGuard` da SPEC-073 é quem permite ou veta.

## R8 — efeito incerto fecha a porta para retry

Se clicou no 80% e não é possível provar se o pedido nasceu:

```text
MAYBE_COMMITTED
→ needs_human
→ não reenfileirar do zero
```

## R9 — o protocolo manda

Encontrou protocolo = pedido existe.

A partir daí:

- nunca iniciar outro atendimento para “continuar”;
- nunca tratar como tentativa falha;
- nunca apagar evidência de erro anterior;
- toda continuação precisa referenciar o atendimento existente.

## R10 — resultado ao segurado não pode inventar o ausente

Se leu protocolo e não leu franquia, fala protocolo e não fala franquia.

Se leu link, entrega o link **literal**, sem reescrever, encurtar ou “melhorar”.

## R11 — sem acesso privado, não há automação privada fictícia

O executor pode preparar adapter/contrato/testes sintéticos. Não pode declarar “Maxpar corretor concluído” sem uma medição autenticada real.

## R12 — multi-tenant sempre explícito

Todo lookup de job, session, account, profile, status ou evidência filtra `company_id` quando aplicável.

---

# 6. ARQUITETURA DE DOMÍNIO — O ATENDIMENTO NÃO É UM CLIQUE

Criar uma camada de domínio **leve e testável**, sem novo framework.

Arquivo sugerido:

```text
backend/app/services/vidros_flow.py
```

ou, se já existir módulo equivalente após SPEC-073, **estender o existente**.

## 6.1 `VidrosWorkItem`

Representa UM item físico por atendimento:

```python
@dataclass(frozen=True)
class VidrosWorkItem:
    item_id: str
    family: str
    piece_text: str
    side: str | None
    position: str | None
    damage_description: str
```

Não persistir necessariamente como tabela. Pode ser payload.

### Objetivo

Se o cliente disser:

```text
“quebraram os dois vidros das portas do lado esquerdo”
```

a camada deve detectar que o portal talvez exija mais de um atendimento e devolver **plano de trabalho explícito**, em vez de mandar tudo como uma string.

## 6.2 `VidrosFlowPlan`

```python
{
  "policy": {...},
  "insurer": {...},
  "channel": "abraseuatendimento|agendeseuservico|whatsapp|human",
  "items": [...],
  "known_facts": {...},
  "questions_for_customer": [...],
  "provider_gaps": [...],
  "ready": true|false,
  "reason": "..."
}
```

## 6.3 Não criar um segundo catálogo de peças

A identidade de peça continua sendo a existente em `vidros_lanternas.py`.

Se a SPEC-073 mover esse vocabulário para módulo comum, a 074 usa o novo único dono. Nunca copia a tabela.

---

# 7. BLOCO A — CONGELAR O CORREDOR ATUAL ANTES DE EVOLUIR

## Objetivo

Provar o que funciona hoje antes de mudar a semântica.

## A1. Testes atuais obrigatórios

Executar e registrar, no mínimo:

- `test_o_portal_de_vidros_traz_os_tres.py`;
- `test_o_80_por_cento_sabe_o_que_pergunta.py`;
- `test_o_protocolo_volta_para_o_segurado.py`;
- `test_o_portal_nao_abre_duas_vezes_o_mesmo_pedido.py`;
- `test_o_agente_entra_no_portal_sabendo.py`;
- `test_sem_corredor_de_vidro_nao_e_beco.py`;
- `test_spec020_portal_action.py`;
- testes do Portal Worker trazidos pela SPEC-073;
- testes das journeys de cobrança.

## A2. Snapshot de contratos

Registrar em teste de contrato:

```text
portal_action
portal_action input atual
portal_action result atual
vidros_lanternas.abrir_atendimento
JourneyResult
portal_jobs campos usados
idempotency_key semantics
vigia do portal
```

## A3. Não alterar sem compatibilidade

Campos novos na tool devem ser opcionais.

Journey nova de continuação não pode tornar inválidos jobs antigos.

## Gate A

```text
[ ] baseline verde
[ ] cobrança verde
[ ] nenhum arquivo vivo sobrescrito sem justificativa
[ ] contrato antigo ainda aceito
```

---

# 8. BLOCO B — ROTEADOR: PORTAL, WHATSAPP OU HUMANO

Hoje há lógica espalhada que reconhece “família com portal”, mas o produto precisa decidir o canal como **capacidade**, não por lista informal de palavras.

## B1. Resolver o trabalho antes de escolher a ferramenta

Entrada:

```text
seguradora
ramo
serviço/subserviço
peça
apólice
```

Saída:

```text
portal_publico
portal_especifico
whatsapp_corredor
human_handoff
```

## B2. Regra de prioridade

Quando existir corredor web medido e apropriado para aquele serviço:

```text
Portal oficial medido
> WhatsApp/URA apenas quando ele for o canal correto
> handoff quando nenhum corredor seguro existir
```

Isso não quer dizer que “portal é sempre melhor”. Quer dizer que a mesma decisão não pode ficar duplicada em prompt, `insurer_dispatch_tool`, `portal_tool` e playbook.

## B3. Família inicial

Preservar o conjunto hoje aceito:

- vidros;
- para-brisa;
- vigia;
- retrovisor;
- farol/farolete;
- lanterna;
- película quando vinculada ao atendimento.

### Porto: roda/pneu/suspensão

O mapa atual prova apenas que Porto exibe uma cobertura separada para roda/pneu/suspensão. **Não generalizar isso para outras seguradoras.**

Essa capacidade fica como:

```text
supported_if_measured(porto, coverage)
```

até a captura real completar as telas.

## B4. `vidros_agendeseuservico`

Existe no catálogo do banco, mas não há nesta base analisada um mapa equivalente ao de `abraseuatendimento` provando que o fluxo é intercambiável.

Portanto:

- não fundir os dois por nome;
- não apontar ambos para a mesma journey por chute;
- criar alias/capability somente após teste de reconhecimento;
- se Bradesco exigir outro motor, tratar como provider exception dentro do mesmo Portal Worker.

## B5. Alias seguro para o nome legado

Após SPEC-073, adicionar resolução de alias compatível, por exemplo:

```text
vidros_lanternas              → capability legacy aceita
vidros_abraseuatendimento     → mesma capability quando comprovado
```

Não migrar/editar jobs históricos.

## Gate B

Mutações que devem falhar:

1. remover família de retrovisor;
2. mandar colisão/sinistro geral para portal de vidros;
3. mandar roda/pneu de Yelum para fluxo da Porto;
4. fazer fallback silencioso para Allianz/qualquer seguradora;
5. ignorar `company_id`.

---

# 9. BLOCO C — FICHA DO ACIONAMENTO 2.0: ENTRAR NO PORTAL JÁ SABENDO

O maior ganho de qualidade não é “IA melhor dentro do browser”. É **não abrir o browser até o atendimento estar pronto**.

## C1. Unificar o pré-check

`perguntas_do_portal_de_vidros.py` continua dono das perguntas conhecidas do portal.

A SPEC deve transformá-lo em um preflight que devolve quatro conjuntos diferentes:

```python
{
  "facts_ready": [...],
  "ask_customer": [...],
  "provider_missing": [...],
  "dynamic_inside_portal": [...]
}
```

### Por que quatro

- `facts_ready`: já temos;
- `ask_customer`: o segurado sabe e deve responder;
- `provider_missing`: InfoCap/perfil deveria fornecer; não incomodar cliente;
- `dynamic_inside_portal`: depende de opções que só existem para aquela peça/seguradora/tela.

## C2. Tudo que pode ser coletado antes deve voltar pela tool

O schema de `PortalActionInput` precisa transportar **todas as respostas que ele manda o agente perguntar**.

Regra de contrato:

> pergunta que não tem campo de retorno é proibida.

Se o catálogo disser ao agente para perguntar `X`, deve existir caminho testado:

```text
resposta WhatsApp
→ tool input
→ portal_params
→ params
→ journey
→ campo real
```

## C3. `especificos` continua extensível

Não transformar cada nova pergunta do portal em nova coluna/tabela.

Pode continuar como dicionário governado, mas deve haver:

- nomes canônicos;
- validadores;
- origem da resposta;
- normalização controlada;
- teste de transporte fim a fim.

## C4. Multi-item

Antes de criar job:

```text
1 item claro → segue
2+ itens claros → gerar N unidades de atendimento
ambíguo → perguntar antes
```

Não abrir N automaticamente em live sem o agente deixar claro para o segurado que serão N solicitações.

## C5. Descrição

Preservar `compor_descricao`.

Nunca pedir ao cliente “fale mais para chegar em 30 caracteres” se o sistema já consegue compor fielmente a partir do relato.

## Gate C

Testes obrigatórios:

- pergunta feita → resposta chega ao portal;
- resposta já na InfoCap não é perguntada;
- provider gap não vira pergunta ao segurado;
- peça desconhecida não gera perguntas inventadas;
- dois itens não viram um;
- descrição fica entre os limites do portal;
- “não informado” não conta como resposta.

---

# 10. BLOCO D — CONFIRMAÇÃO DE APÓLICE/VEÍCULO ANTES DE PROSSEGUIR

O modal “Dados da apólice” é um **gate de identidade**.

## D1. Criar comparador determinístico

Arquivo sugerido:

```text
backend/portal_worker/journeys/vidros_identity.py
```

ou função comum no módulo existente.

Comparar o que o portal mostrou com os dados InfoCap:

- nome do segurado, quando disponível;
- placa mascarada ou completa;
- apólice mascarada ou completa;
- veículo;
- últimos 6 do chassi.

## D2. Comparação consciente de máscara

Não exigir igualdade literal quando o portal mascara.

Exemplos:

```text
Q***A91 pode casar com QAB1A91 por prefixo/sufixo permitido
******261149211 pode casar pelo sufixo consistente
últimos 6 do chassi = igualdade exata
```

A regra precisa ser explícita e testável. Nunca “parece parecido”.

## D3. Divergência

Qualquer divergência material:

```text
needs_human
reason=policy_identity_mismatch
```

com evidência redigida, sem clicar Confirmar.

## D4. Segurança

Visão/LLM não pode dar override nesse gate.

## Gate D

Mutation tests:

- trocar 1 dígito dos 6 finais do chassi → bloqueia;
- trocar sufixo da apólice → bloqueia;
- máscara legítima → passa;
- ausência de um campo não inventa igualdade;
- dois veículos candidatos → bloqueia.

---

# 11. BLOCO E — PORTAL PÚBLICO API-FIRST, BROWSER COMO SESSÃO E PROVA

Este bloco usa a infraestrutura da SPEC-073.

## E1. Rodar Discovery Mode sem efeito material

Entrar no fluxo com `confirm=false` e profiler ligado.

Capturar somente:

- hosts;
- métodos;
- paths sanitizados;
- schema estrutural de request/response;
- correlação tela → request;
- status code;
- nomes de campos não sensíveis;
- fingerprints.

Nunca versionar:

- CPF real;
- placa real;
- nome real;
- bearer token;
- cookie;
- UUID de atendimento real se isso expuser o cliente;
- HTML/HAR bruto com PII.

## E2. Candidatos de API

Classificar chamadas em:

```text
READ_ONLY_DATA
FORM_STATE
MATERIAL_CREATE
MATERIAL_UPDATE
TELEMETRY
STATIC
UNKNOWN
```

Somente chamadas reproduzidas com a mesma sessão e resultado compreendido viram adapter.

## E3. Preferir API em tarefas de leitura

Se o app expuser de forma legítima dados estruturados para:

- seguradoras;
- coberturas;
- apólice;
- opções de dropdown;
- perguntas condicionais;
- lojas;
- status;
- protocolo/franquia/link;

preferir leitura estruturada à raspagem de texto, mantendo browser como fallback.

## E4. Criação/alteração continua protegida

Mesmo que exista endpoint claro de criação:

```text
API não significa sem gate
```

O `PortalActionGuard` e o checkpoint da SPEC-073 continuam obrigatórios.

## E5. Sem endpoint aprovado

Se não houver API reutilizável, nada falha arquiteturalmente. O DOM semantic + adaptive + visão continuam sendo a escada oficial.

## Gate E

```text
[ ] nenhuma credencial vazou
[ ] fixture sanitizada
[ ] candidate API separado de approved API
[ ] nenhuma mutação foi disparada no discovery
[ ] browser fallback continua verde
```

---

# 12. BLOCO F — TELA INICIAL, SEGURADORA E COBERTURA

## F1. Seleção de seguradora sem clique ingênuo

O código atual digita o nome e clica na primeira opção visível.

Isso deve evoluir para:

1. ler opções reais;
2. normalizar marca;
3. exigir match único/confiante;
4. selecionar a opção exata;
5. validar a rota/slug resultante.

Se duas opções forem plausíveis:

```text
needs_human
```

não “primeira opção”.

## F2. Slug não é verdade de negócio

`yelum`, `tokio`, `porto` na URL são identificadores da aplicação. Não inferir cobertura a partir deles sem prova.

## F3. Porto — seleção de cobertura

Quando a Porto exibir:

```text
Vidros/faróis/lanternas/retrovisores
Roda/pneu/suspensão
```

selecionar conforme o trabalho já classificado.

Se aparecer opção nova ou nomenclatura ambígua, pausar com lista real.

## F4. Outras seguradoras

Não assumir que a cobertura Porto existe nelas.

## Gate F

- Yelum selecionada não vira outra marca;
- Liberty normaliza para Yelum sem falsificar dados;
- Porto escolhe cobertura coerente;
- cobertura desconhecida bloqueia;
- seleção com 2 matches não clica.

---

# 13. BLOCO G — POPUP “QUEREMOS ENTENDER MELHOR SUA NECESSIDADE”

A SPEC-071 registra que a Regina mostrou um popup que aparece em atendimentos e que o robô ainda não modelava corretamente.

## G1. Não codificar cinco opções por memória

A informação disponível diz que existem **cinco opções**, mas esta base não contém os cinco textos completos medidos.

Portanto o executor deve:

1. capturar a tela real no primeiro discovery elegível;
2. registrar as cinco opções **exatamente como aparecem**;
3. criar fixture sanitizada;
4. só então codificar matching determinístico.

## G2. Regra conhecida

A SPEC-071 registra a orientação operacional:

```text
para-choque / lataria / pequeno reparo → caminho de loja
outros casos observados → pode haver fluxo por link/vistoria
```

Essa orientação vira **hipótese a confirmar com a tela real**, não constante cega antes da captura.

## G3. Matching

O popup deve usar o mesmo princípio do resto do sistema:

```text
pedido do segurado
× opções reais da tela
→ match explicado
```

Sem match confiante:

```text
needs_human + opcoes + pedido_do_segurado
```

## G4. Não deixar LLM decidir regra física irreversível

A visão pode identificar visualmente o popup ou transcrever opções. A escolha final deve passar pelo classificador/matcher e pelo action validator.

## Gate G

A SPEC não fecha este bloco como “medido” até existirem as cinco labels reais.

Se não houver caso real autorizado antes do go-live, o código deve pelo menos:

- detectar semanticamente o popup;
- listar opções;
- escolher apenas quando houver match confiante;
- parar de forma útil quando não houver.

Isso já evita travamento e chute.

---

# 14. BLOCO H — PASSO 3/4/5: PREENCHIMENTO DETERMINÍSTICO + OPÇÕES REAIS

## H1. Solicitante

Preservar:

```text
relação = Corretor
nome = perfil da corretora
e-mail = perfil da corretora
CNPJ = corretora
telefone = corretora
```

Não usar dados do segurado no campo do solicitante por engano.

## H2. WhatsApp updates

Preservar decisão do Founder:

- não marcar a caixa se ela enviar para o telefone do solicitante/corretora;
- só habilitar se existir campo separado e comprovado para telefone do segurado;
- avisar o segurado antes.

## H3. Peça

Usar `explicar_match`/vocabulário único.

## H4. Causa

A lista muda por peça e seguradora.

Regra:

```text
NUNCA decorar globalmente
LER as opções reais
MATCH com o relato
```

## H5. Local

Urbano/rodoviário somente quando essa for a pergunta real. Se a tela variar, ler.

## H6. Estado/cidade/CEP

- UF por sigla;
- cidade conforme autocomplete;
- CEP real da InfoCap;
- autocomplete precisa selecionar a sugestão, não apenas preencher texto.

## H7. Campos dinâmicos

Cada select deve registrar:

```text
label
opções reais
pedido original
match escolhido
score/motivo
```

Esse log deve ser redigido quando tiver PII.

---

# 15. BLOCO I — 80%: QUESTION ENGINE DINÂMICO E SEM CHUTE

O 80% é a tela mais sensível porque a próxima confirmação pode criar o pedido.

## I1. Ordem progressiva

O engine deve respeitar que perguntas surgem após respostas anteriores.

Loop:

```text
capture state
→ existe pergunta crítica não respondida?
→ procurar resposta já conhecida
→ se não, matcher contra resposta coletada
→ se faltar resposta humana legítima, parar
→ aplicar uma resposta
→ recapturar
```

Não tentar preencher todas de uma vez com um snapshot antigo.

## I2. Vidro de porta — baseline conhecido

Perguntas medidas:

- película;
- porta dianteira/traseira;
- lado motorista/carona.

## I3. Para-brisa — baseline conhecido

Perguntas medidas:

- posição do trincado;
- maior/menor que 10 cm;
- versão do veículo em caso observado.

## I4. Versão do veículo é fato

Se a InfoCap contém a versão, o sistema responde deterministicamente.

## I5. Outras peças

Retrovisor, farol, lanterna, vigia, teto e demais variações ainda não têm catálogo completo medido.

O comportamento correto é:

```text
ler pergunta real
→ verificar se resposta já existe
→ match seguro
→ visão/adaptive se necessário
→ needs_human com pergunta/opções se ainda incerto
```

Nunca inventar catálogo.

## I6. “Não sabe”

Somente se o segurado efetivamente respondeu que não sabe.

## I7. Validação antes do 80%

Antes de liberar a confirmação material, rodar um `ready_to_commit` determinístico:

```python
{
  "policy_identity_ok": True,
  "one_item_only": True,
  "critical_questions_complete": True,
  "no_unknown_required_fields": True,
  "customer_answers_traceable": True,
  "idempotency_clear": True,
  "agent_gate_live": True,
  "action_guard_allows": True
}
```

Qualquer `False` impede envio.

## Gate I

Mutation tests devem matar:

1. usar `Não sabe` como default;
2. trocar motorista por carona;
3. trocar dianteira por traseira;
4. maior por menor;
5. usar versão inventada;
6. clicar com required field vazio;
7. ignorar pergunta nova;
8. permitir `force choose` em crítico.

---

# 16. BLOCO J — O CLIQUE QUE CRIA O PEDIDO: TRANSAÇÃO EXTERNA SEGURA

Este bloco depende diretamente do `PortalActionGuard` e checkpoint da SPEC-073.

## J1. Antes do clique

Persistir checkpoint incremental no próprio job/evidence:

```json
{
  "effect": {
    "kind": "MATERIAL_SIDE_EFFECT",
    "operation": "create_glass_service_request",
    "state": "INTENT_RECORDED",
    "idempotency_key": "...",
    "at": "...",
    "screen_fingerprint": "..."
  }
}
```

Sem PII desnecessária.

## J2. No clique

O executor de browser/API só recebe permissão se:

```text
confirm=true
AND action guard approved
AND idempotency gate clear
AND identity gate green
```

## J3. Depois do clique

Assim que houver evidência de criação:

```text
protocolo
ou tela inequívoca de atendimento criado
ou resposta estruturada aprovada da API
```

persistir:

```text
COMMITTED
```

antes de navegar adiante.

## J4. Se cair entre clique e resposta

Estado:

```text
MAYBE_COMMITTED
```

O worker:

- não reexecuta;
- não chama `abrir_atendimento` de novo;
- encaminha para reconciliação/consulta;
- tenta localizar o atendimento existente via `Consultar atendimento` quando essa capability estiver provada;
- caso contrário, pede revisão humana.

## J5. Protocolo encontrado é prova superior

Se protocolo aparecer em qualquer desfecho:

```text
status técnico pode ser failed/needs_human
mas business state = REQUEST_CREATED
```

O resultado ao agente precisa refletir isso.

## Gate J

Mutation tests:

- matar checkpoint antes do clique → teste falha;
- transformar MAYBE_COMMITTED em retry → teste falha;
- requeue job com protocolo → teste falha;
- remover idempotency → teste falha;
- perder company_id → teste falha.

---

# 17. BLOCO K — A TELA DO PEDIDO: PROTOCOLO + FRANQUIA + VISTORIA

Este é um dos trechos já melhorados e não pode regredir.

## K1. Uma leitura, três fatos

Na primeira tela que prove criação, extrair na **mesma leitura coerente**:

```text
protocolo
franquia
link_vistoria
```

## K2. Protocolo

Não capturar número solto.

Deve estar semanticamente associado ao rótulo de atendimento/protocolo.

## K3. Franquia

Não usar qualquer `R$` da página.

O valor precisa estar associado ao rótulo de franquia/participação obrigatória e passar pela validação existente.

## K4. Link

Somente domínio de vistoria aprovado/medido.

Não pegar rodapé, política, mapa ou qualquer URL genérica.

## K5. Entrega ao agente

O resultado estruturado deve incluir separadamente:

```json
{
  "request_created": true,
  "protocol": "...",
  "franchise": "...",
  "inspection_url": "...",
  "service_location_state": "...",
  "continuation_required": true
}
```

A frase humana pode ser composta depois, mas os dados estruturados não podem se perder em texto.

## K6. Link literal

O link deve sair para o segurado exatamente como recebido.

## Gate K

Preservar integralmente `test_o_portal_de_vidros_traz_os_tres.py` e ampliar com testes de payload estruturado.

---

# 18. BLOCO L — PÓS-PROTOCOLO: CONTINUAR O MESMO ATENDIMENTO, NUNCA ABRIR OUTRO

Este é o principal fechamento arquitetural da SPEC-074.

Hoje o sistema já entende que o pedido existe quando vê o protocolo, mas a continuação do serviço precisa ser modelada como **outra capacidade sobre o mesmo pedido**.

## L1. Capabilities novas

No registry do Portal Worker, criar somente quando seus contratos estiverem medidos:

```text
vidros_lanternas.consultar_atendimento
vidros_lanternas.continuar_atendimento
```

ou nomes equivalentes orientados à capacidade.

**Não criar `abrir_atendimento_2`.**

## L2. `resume_locator`

Quando o protocolo surgir, registrar o mínimo necessário para tentar retomar o pedido existente:

```json
{
  "protocol": "...",
  "provider": "maxpar_autoglass",
  "insurer": "...",
  "current_route": "...",
  "flow_uuid": "...",
  "resume_strategy": "direct|consult|unknown"
}
```

Somente campos não sensíveis e necessários.

## L3. Descobrir como retomar — não assumir

No primeiro caso autorizado, testar de forma controlada:

1. o URL `passo5/<uuid>` é retomável numa nova sessão?
2. exige storage/session anterior?
3. `Consultar atendimento` localiza pelo protocolo?
4. exige CPF/placa/outro identificador?
5. existe API read-only de consulta?

A primeira estratégia que funcionar de forma estável e segura vira contrato.

## L4. Loja versus domicílio

A preferência do segurado deve chegar coletada antes do portal:

```text
domicilio
loja
```

Mas a decisão final depende da disponibilidade real.

### Domicílio pedido e disponível

A continuação pode avançar para a tela de agenda **somente depois que essa tela estiver medida**.

### Domicílio pedido e indisponível

O agente precisa dizer isso ao segurado e apresentar as alternativas reais de loja.

### Loja

Não escolher loja pelo segurado.

Retornar lista estruturada:

```json
[
  {
    "name": "...",
    "address": "...",
    "distance": "...",
    "availability_hint": "...",
    "provider_id": "..."
  }
]
```

Somente campos realmente disponíveis.

## L5. Nunca deixar browser aberto esperando conversa

Não manter um processo Playwright pendurado por minutos esperando o segurado escolher.

O job deve terminar com estado:

```text
REQUEST_CREATED_AWAITING_CUSTOMER_CHOICE
```

A continuação abre uma **nova execução sobre o mesmo atendimento**, usando `resume_locator`/consulta.

## L6. Idempotência diferente

A chave de continuação precisa identificar:

```text
company + provider + protocol + continuation_operation
```

Nunca reutilizar a chave de “criar pedido” como se fosse uma nova criação.

## Gate L

- continuação não chama `abrir_atendimento`;
- protocolo obrigatório;
- job antigo com protocolo não requeue para início;
- escolha de loja ausente não é inventada;
- browser não fica vivo aguardando WhatsApp.

---

# 19. BLOCO M — CONSULTAR ATENDIMENTO E ACOMPANHAR STATUS

A página oficial atual expõe consulta/status. O mapa canônico também já observou “Consultar atendimento”.

Essa é a saída correta para reconciliar:

- job que caiu depois do commit;
- segurado perguntando andamento;
- atendimento criado fora da janela da tool;
- continuação depois de escolha humana;
- acompanhamento pós-abertura.

## M1. Primeiro mapear os inputs reais

Discovery deve responder:

```text
quais identificadores pede?
protocolo?
CPF?
placa?
data?
seguradora?
```

Não inventar.

## M2. Capability read-only primeiro

Implementar primeiro:

```text
consultar_atendimento
```

com resultado estruturado:

```json
{
  "found": true,
  "protocol": "...",
  "status": "...",
  "next_step": "...",
  "appointment": {...},
  "inspection": {...},
  "can_reschedule": true,
  "raw_labels": [...]
}
```

Somente campos observados.

## M3. Reagendamento e alteração de data

São mutações materiais.

Mesmo que a página oficial ofereça, a SPEC-074 **não deve ativá-las automaticamente** sem:

- tela medida;
- regra de negócio;
- autorização do segurado;
- action guard;
- checkpoint;
- idempotência;
- teste de reconciliação.

Pode deixar adapter/protocolo preparado, mas feature flag desligada até medição com Regina.

## M4. Status humano

O agente nunca deve traduzir status desconhecido inventando significado.

Manter:

```text
status_raw
status_normalized somente se mapeado
```

## Gate M

- consulta não cria pedido;
- consulta não cancela;
- consulta não reageenda;
- job MAYBE_COMMITTED tenta consulta antes de criar outro;
- status desconhecido é devolvido sem chute.

---

# 20. BLOCO N — “PORTAL MAXPAR DO CORRETOR”: MEDIR ANTES DE AUTOMATIZAR

A SPEC-071 registra a prática da Regina: depois de determinado ponto ela entra no **portal Maxpar do corretor** para obter/acompanhar informação, inclusive link.

A base atual não contém credencial nem mapa autenticado desse portal.

## N1. Tratar como corredor autenticado do MESMO Portal Worker

Quando houver acesso medido, ele entra no padrão já usado por Allianz/HDI/Tokio/Yelum/MAPFRE/Zurich:

```text
portals
portal_accounts
Vault
portal_sessions
account_label se houver múltiplas identidades
Portal Worker
journey/capability
```

Não criar login próprio em arquivo `.env` nem hardcode.

## N2. Descoberta inicial

Com Regina/Founder ou credencial disponibilizada:

1. confirmar URL real de login;
2. identificar owner/provider;
3. capturar login e pós-login;
4. verificar captcha/2FA;
5. descobrir como localizar atendimento existente;
6. descobrir como recuperar link/status;
7. mapear chamadas de rede com profiler;
8. separar leitura de mutação;
9. produzir fixture sanitizada;
10. só então registrar capability.

## N3. Não assumir que `portaldocliente.autoglass.com.br` é o mesmo portal

Existe portal B2B oficial da Autoglass, mas esta SPEC não conclui que ele é o exato “portal Maxpar do corretor” usado pela Regina sem medição.

Isso precisa ser provado na sessão real.

## N4. Conta

Como não há `portal_account` hoje para Maxpar/Autoglass:

- nenhum seed de senha;
- nenhum placeholder falso;
- criar conta somente após o Founder fornecer a credencial legítima;
- segredo criptografado pelo Vault;
- nunca logar senha/HAR completo.

## N5. Escopo ideal da primeira capability privada

Priorizar **leitura**:

```text
buscar atendimento existente
→ obter link/status/dados que o público não entrega
```

Não começar automatizando cancelamento/reagendamento.

## Gate N

O bloco só pode ser marcado `MEASURED_GREEN` se existir captura autenticada real. Caso contrário:

```text
READY_FOR_REGINA_MEASUREMENT
```

Isso é uma pendência externa legítima e **não invalida os blocos anteriores**.

---

# 21. BLOCO O — CONTRATO DO AGENTE: UM FLUXO EM ETAPAS, NÃO UMA CAIXA-PRETA

`portal_action` deve continuar sendo a ferramenta reconhecida pelo agente, mas precisa devolver estados de negócio mais claros.

## O1. Compatibilidade

Não quebrar chamadas antigas.

Se for necessário adicionar operação:

```python
operation: Optional[Literal[
  "open",
  "continue",
  "consult"
]] = "open"
```

ou desenho equivalente.

## O2. Result envelope

Padronizar saída estruturada antes de compor frase:

```json
{
  "business_state": "...",
  "request_created": false,
  "protocol": null,
  "franchise": null,
  "inspection_url": null,
  "customer_choice_needed": null,
  "available_options": [],
  "status": null,
  "human_needed": false,
  "human_reason": null,
  "safe_to_retry_open": false
}
```

## O3. Estados mínimos

```text
NEEDS_CUSTOMER_INFO
PROVIDER_DATA_MISSING
READY_TO_OPEN
OPENING
READY_TO_CONFIRM
REQUEST_CREATED
REQUEST_CREATED_AWAITING_CHOICE
COMPLETED
MAYBE_CREATED_RECONCILIATION_REQUIRED
NEEDS_HUMAN
FAILED_BEFORE_EFFECT
```

## O4. `safe_to_retry_open`

Esse booleano não é cosmético.

Regras:

```text
falhou antes de qualquer efeito → pode ser true
checkpoint intent sem clique → pode ser true se reconciliado
MAYBE_COMMITTED → false
protocolo existe → false
REQUEST_CREATED → false
```

## O5. Mensagem humana

`format_result` deve ser derivado do envelope.

Nunca o inverso.

## O6. Heads-up ao segurado

Preservar comunicação de espera enquanto o portal roda, mas alinhar ao estado real:

- “vou abrir” quando ainda está tentando;
- “abri” somente com prova;
- “preciso que você escolha” quando o atendimento já existe;
- nunca “não consegui abrir” se existe protocolo.

---

# 22. BLOCO P — VIGIA DO PORTAL 2.0 PARA ESTADOS DE NEGÓCIO

O Vigia atual é valioso e não deve ser substituído.

## P1. Ele precisa entender `request_created`

Se job técnico falhar depois de protocolo:

```text
não enviar ao segurado “não consegui abrir”
```

Mensagem correta é equivalente a:

```text
“o atendimento foi aberto, mas preciso concluir a próxima etapa”
```

## P2. MAYBE_COMMITTED

O Vigia deve priorizar reconciliação/consulta e alertar suporte:

```text
não reexecute
verifique atendimento existente
```

## P3. Awaiting customer choice

Não alertar como falha operacional enquanto estiver legitimamente aguardando uma escolha do segurado.

## P4. Timeout

Timeout de browser não é automaticamente falha de negócio.

## Gate P

Mutation tests:

- protocolo + failed → mensagem de “não abriu” deve reprovar;
- waiting choice → não vira incidente;
- no protocol + failed_before_effect → handoff normal;
- maybe committed → reexecução proibida.

---

# 23. BLOCO Q — VISÃO MULTIMODAL REAL SOMENTE ONDE AGREGA

A SPEC-073 cria a camada transversal. A 074 define onde ela é útil em vidros.

## Usos legítimos

- popup visual não capturado semanticamente;
- desenho do veículo usado apenas para confirmar contexto, não para inventar peça;
- botão/overlay que DOM não expõe de forma útil;
- tela desconhecida após mudança de frontend;
- erro visual/captcha;
- agenda renderizada sem estrutura acessível.

## Usos ilegítimos

- ler CPF que já está no payload;
- escolher peça sem relato;
- escolher loja;
- escolher data/hora pelo segurado;
- autorizar o clique do 80%;
- bypass de CAPTCHA/2FA;
- substituir comparador de apólice.

## Validação

Toda ação multimodal proposta passa por:

```text
allowed action?
target exists?
critical field?
customer actually answered?
material side effect?
```

Sem validação = não executa.

---

# 24. BLOCO R — EVIDÊNCIA QUE PERMITE CORRIGIR EM MINUTOS

Um `needs_human` bom tem que responder sem reabrir o portal:

```text
onde parou?
o que a tela perguntou?
quais opções existiam?
o que o segurado disse?
o que o sistema tentou?
o pedido já existe?
qual é o protocolo?
qual foi o último checkpoint?
qual tela/fingerprint mudou?
```

## Envelope sugerido

```json
{
  "business_state": "...",
  "step": "...",
  "screen": {
    "url_class": "...",
    "heading": "...",
    "fingerprint": "..."
  },
  "question": "...",
  "options": [],
  "customer_intent": {},
  "match": {},
  "effect": {},
  "protocol": "...",
  "franchise": "...",
  "inspection_url": "...",
  "resume": {},
  "drift": {}
}
```

PII e segredos passam pelo redactor da SPEC-073.

---

# 25. BLOCO S — TESTES OFFLINE, CONTRATO, INTEGRAÇÃO E MUTAÇÃO

A qualidade desta SPEC é provada principalmente **sem portal real**.

## S1. Fixtures

Criar fixtures sanitizadas para:

- seleção de seguradora;
- modal de apólice;
- passo 20%;
- passo 50%;
- localização;
- 80% vidro lateral;
- 80% para-brisa;
- popup novo quando capturado;
- protocolo/franquia/vistoria;
- lista de lojas;
- consulta/status quando capturado;
- tela desconhecida.

## S2. Testes puros

Cobrir:

- identidade de peça;
- split multi-item;
- perguntas faltantes;
- match de seguradora;
- coverage selection;
- masked identity compare;
- critical match;
- `ready_to_commit`;
- business state;
- safe retry;
- resume strategy;
- status normalization.

## S3. Testes de integração do worker

Com Playwright local/fixture:

```text
open → 80% sem confirm = needs_human
open → confirm autorizado → protocolo
protocol → não reinicia open
continue sem protocolo → bloqueia
consult = read-only
```

## S4. Mutation matrix obrigatória

No mínimo estas mutações devem ser mortas:

1. `company_id` removido de lookup;
2. idempotência removida;
3. protocolo ignorado no retry;
4. `MAYBE_COMMITTED` reenfileirado;
5. `confirm` default vira true;
6. gate do agente ignorado;
7. policy identity mismatch permitido;
8. first option em peça crítica;
9. first option em lado;
10. first option em cobertura;
11. `Não sabe` usado automaticamente;
12. dois itens viram um;
13. link genérico aceito como vistoria;
14. qualquer `R$` aceito como franquia;
15. número solto aceito como protocolo;
16. consulta chama criação;
17. continuação chama criação;
18. browser fica aguardando cliente;
19. popup desconhecido é clicado por chute;
20. status desconhecido é normalizado inventando;
21. provider gap vira pergunta ao cliente;
22. apólice mascarada incompatível passa;
23. alteração de agenda sem guard;
24. dados de uma tenant aparecem na outra;
25. erro pós-protocolo diz “não abriu”.

## S5. Controle da cobrança

Rodar suite de cobrança depois das mutações de vidros.

O objetivo não é porque o código de cobrança foi alterado — é provar que as mudanças transversais de Portal Worker não tocaram o que já funciona.

---

# 26. BLOCO T — GATE LIVE EM DEGRAUS

Nenhum live test começa pelo fim.

## T0 — offline

Tudo verde sem rede externa.

## T1 — public portal, somente leitura/início sem efeito

Com caso autorizado:

- selecionar seguradora;
- localizar apólice;
- conferir modal;
- navegar até antes do 80%;
- profiler/discovery;
- `confirm=false`.

## T2 — 80% sem criar

Provar:

- todas perguntas tratadas;
- nenhum chute;
- `ready_to_commit` verde;
- action guard recusa commit porque `confirm=false`.

## T3 — criação real com autorização explícita

Somente Founder + apólice real + Regina quando necessário.

Antes de clicar, registrar no chat:

```text
SEGURADORA:
APÓLICE:
ITEM:
CONFIRM REAL:
IDEMPOTENCY KEY:
```

Depois:

- protocolo;
- franquia se existir;
- link se existir;
- business state;
- checkpoint COMMITTED.

## T4 — continuação

Usar o mesmo atendimento.

Nunca criar outro para testar continuação.

## T5 — consulta

Fechar browser e provar que o atendimento existente pode ser encontrado novamente pelo mecanismo medido.

## T6 — portal privado Maxpar, se acesso disponível

Somente leitura no primeiro teste.

---

# 27. ROLLBACK

## Rollback de feature

Toda capacidade nova deve estar atrás de flags/config compatível quando alterar comportamento live, por exemplo:

```text
PORTAL_VIDROS_V2_ENABLED=false
PORTAL_VIDROS_API_FIRST=false
PORTAL_VIDROS_CONTINUATION_ENABLED=false
PORTAL_VIDROS_CONSULT_ENABLED=false
PORTAL_MAXPAR_PRIVATE_ENABLED=false
```

Nomes finais podem seguir padrão já introduzido pela SPEC-073; não duplicar flags equivalentes.

## Rollback esperado

Desligar a 074 deve devolver:

```text
portal_action antigo
→ abrir_atendimento legado
→ trava 80%
→ comportamento conhecido
```

sem tocar em cobrança.

## Não fazer rollback de dados apagando evidência

Atendimento/protocolo já criado é fato histórico. Rollback de código nunca remove ou “zera” evidência do job.

---

# 28. BANCO E MIGRATIONS

## Regra padrão: ZERO schema novo

A expectativa desta SPEC é usar:

- `portal_jobs`;
- `evidence`;
- `params`;
- `idempotency_key`;
- `portal_sessions`;
- `portal_accounts` somente quando houver conta real;
- storage existente.

## Se aparecer necessidade real de schema

O executor deve primeiro provar por escrito:

```text
qual estado não cabe em estrutura existente?
por que JSON/evidence não serve?
qual query/index real exige coluna?
qual o ganho concreto?
```

Só então seguir `MIGRATIONS-AUTHORITY.md`.

Nenhuma migration histórica é reaplicada.

---

# 29. ARQUIVOS ESPERADOS

A lista abaixo é direção, não licença para criar todos automaticamente.

## Prováveis alterações

```text
backend/app/agents/tools/portal_tool.py
backend/app/agents/tools/portal_params.py
backend/app/agents/tools/insurer_dispatch_tool.py
backend/app/services/perguntas_do_portal_de_vidros.py
backend/app/tasks/vigia_do_portal.py
backend/portal_worker/journeys/__init__.py
backend/portal_worker/journeys/vidros_lanternas.py
backend/portal_worker/adaptive.py   # somente integração com fundação 073; não reescrever
```

## Prováveis novos módulos leves

```text
backend/app/services/vidros_flow.py
backend/portal_worker/journeys/vidros_identity.py
backend/portal_worker/journeys/vidros_resume.py
```

Criar apenas se reduzirem duplicação real.

## Novos testes

Sugestão:

```text
backend/tests/test_spec074_vidros_flow.py
backend/tests/test_spec074_vidros_identity_gate.py
backend/tests/test_spec074_vidros_multi_item.py
backend/tests/test_spec074_vidros_80_commit_guard.py
backend/tests/test_spec074_vidros_resume.py
backend/tests/test_spec074_vidros_consulta.py
backend/tests/test_spec074_vidros_router.py
backend/tests/test_spec074_vidros_mutations.py
backend/tests/fixtures/vidros/... sanitizadas
```

## Docs

Atualizar:

```text
docs/canon/O-PORTAL-DE-VIDROS-TELA-POR-TELA.md
docs/canon/PENDENCIAS.md
```

Adicionar relatório:

```text
docs/canon/reports/SPEC-074-IMPLEMENTATION-REPORT.md
```

ou padrão vigente de reports.

---

# 30. ARQUIVOS QUE NÃO DEVEM SER REESCRITOS POR ESTA SPEC

Salvo bug transversal provado pelos gates:

```text
backend/app/services/billing_collection.py
backend/portal_worker/journeys/allianz_corretor.py
backend/portal_worker/journeys/hdi_corretor.py
backend/portal_worker/journeys/tokio_corretor.py
backend/portal_worker/journeys/yelum_corretor.py
backend/portal_worker/journeys/mapfre_corretor.py
backend/portal_worker/journeys/zurich_corretor.py
```

“Reorganizar enquanto estou aqui” não é justificativa.

---

# 31. SEQUÊNCIA RETA DE EXECUÇÃO PARA O CLAUDE CODE

Executar nesta ordem. Não pular para live porque “parece fácil”.

## PASSO 1 — preflight

Registrar repo/branch/HEAD/status e confirmar SPEC-073 implementada.

## PASSO 2 — ler autoridade

Ler os arquivos da seção 1.

## PASSO 3 — medir banco read-only

Confirmar:

- jobs de vidros;
- schema real de `portal_jobs`;
- nenhum account Maxpar/Autoglass;
- aliases de `portals`;
- estado atual do agente/gates sem alterar.

## PASSO 4 — baseline tests

Rodar vidros + Portal Worker + cobrança.

## PASSO 5 — criar `VidrosFlowPlan`

Sem browser.

## PASSO 6 — multi-item

Resolver 1 item por atendimento.

## PASSO 7 — roteador

Portal × WhatsApp × handoff + aliases compatíveis.

## PASSO 8 — ficha 2.0

Garantir que toda pergunta feita volta pela tool.

## PASSO 9 — identity gate

Modal de apólice/veículo.

## PASSO 10 — integrar runtime da SPEC-073

Discovery/profiler/action guard/checkpoint.

## PASSO 11 — seleção inicial robusta

Seguradora/cobertura por opção real.

## PASSO 12 — popup desconhecido seguro

Detectar/listar/match; não inventar labels.

## PASSO 13 — passos 20/50/local

Determinístico onde for fato; match real onde for escolha.

## PASSO 14 — question engine 80%

Progressivo, sem `first option` em crítico.

## PASSO 15 — `ready_to_commit`

Gate determinístico completo.

## PASSO 16 — material effect

Checkpoint + action guard + MAYBE_COMMITTED.

## PASSO 17 — trio final

Protocolo + franquia + link.

## PASSO 18 — business state/result envelope

Separar estado técnico de estado de negócio.

## PASSO 19 — Vigia 2.0

Pós-protocolo não pode dizer “não abriu”.

## PASSO 20 — estrutura de continuação

`resume_locator`, capability e idempotência própria.

## PASSO 21 — estrutura de consulta

Read-only, sem inventar inputs ainda não medidos.

## PASSO 22 — Maxpar privado

Preparar adapter/contrato; só marcar medido com credencial/captura real.

## PASSO 23 — mutation suite

Matar as 25 mutações mínimas.

## PASSO 24 — regressão cobrança

Tudo verde.

## PASSO 25 — documentation truth

Atualizar mapa e pendências separando:

```text
MEASURED
INFERRED
READY_TO_MEASURE
FOUNDER/REGINA REQUIRED
```

## PASSO 26 — deploy com flags off

Subir sem mudar comportamento live.

## PASSO 27 — canário read-only/dry-run

Somente com autorização e sem criar pedido.

## PASSO 28 — parar

Não executar o clique live final sem autorização explícita do Founder.

---

# 32. GATES AUTOMÁTICOS POR BLOCO

```text
A baseline ..................... testes antigos + cobrança verdes
B router ....................... nenhum canal errado
C preflight .................... nenhuma pergunta sem retorno
D identity ..................... carro/apólice errados bloqueados
E profiler/API ................. zero segredo + zero mutação
F seguradora/cobertura ......... match único
G popup ........................ detecta e não chuta
H formulário ................... fatos determinísticos
I 80% .......................... críticas completas
J commit ....................... checkpoint + idempotência
K trio final ................... protocolo/franquia/link corretos
L continuação .................. mesmo atendimento
M consulta ..................... read-only
N Maxpar privado ............... medido OU pendência externa explícita
O contrato agente .............. business state correto
P Vigia ........................ mensagem coerente
Q visão ........................ validator obrigatório
R evidence ..................... dossiê acionável
S testes/mutações ............... verde
T live ......................... somente com autorização
```

Um bloco verde libera o próximo automaticamente. Founder não precisa aprovar cada bloco offline.

---

# 33. CRITÉRIOS DE ACEITE FINAIS

## Arquitetura

- [ ] continua existindo um único Portal Worker;
- [ ] vidros não ganhou worker/fila/tabela paralela;
- [ ] SPEC-073 continua sendo a fundação transversal;
- [ ] registry é fonte de capabilities;
- [ ] alias legado é compatível;
- [ ] cobrança permanece intacta.

## Conversa/preflight

- [ ] agente sabe o que perguntar antes de abrir;
- [ ] nenhuma pergunta sem campo de retorno;
- [ ] não pergunta versão/CEP/placa se a InfoCap já trouxe;
- [ ] multi-item é detectado;
- [ ] descrição é composta sem incomodar o segurado.

## Portal

- [ ] seguradora é selecionada por match único;
- [ ] coverage Porto não vaza para outras marcas;
- [ ] modal de apólice é realmente conferido;
- [ ] popup desconhecido não é clicado no escuro;
- [ ] dropdowns críticos usam opções reais;
- [ ] tela desconhecida gera dossiê útil.

## 80% e efeito

- [ ] `confirm=false` nunca cria;
- [ ] `confirm=true` ainda exige todos os gates;
- [ ] checkpoint vem antes do efeito;
- [ ] MAYBE_COMMITTED não retry;
- [ ] protocolo bloqueia reabertura;
- [ ] idempotência preservada.

## Resultado

- [ ] protocolo entregue quando existe;
- [ ] franquia entregue somente quando lida;
- [ ] link literal entregue somente quando lido;
- [ ] business state não depende apenas de status técnico;
- [ ] erro pós-protocolo não diz “não abriu”.

## Continuação

- [ ] não mantém browser esperando cliente;
- [ ] continuação referencia protocolo/atendimento existente;
- [ ] lista de lojas não é escolhida pelo robô;
- [ ] consulta é read-only;
- [ ] retry de criação nunca é usado como “continuação”.

## Maxpar privado

- [ ] nenhuma URL/login foi inventado;
- [ ] se acesso real existir, usa Vault/session/account padrão;
- [ ] se não existir acesso, fica `READY_FOR_REGINA_MEASUREMENT` sem fingir conclusão.

## Segurança

- [ ] zero token/cookie/senha em evidence;
- [ ] zero fixture com PII real;
- [ ] zero cross-tenant;
- [ ] mutações críticas mortas.

## Regressão

- [ ] Allianz cobrança verde;
- [ ] HDI cobrança verde;
- [ ] Tokio cobrança verde;
- [ ] Yelum cobrança verde;
- [ ] MAPFRE cobrança verde;
- [ ] Zurich cobrança verde;
- [ ] worker health verde.

---

# 34. O QUE DEVE FICAR PARA A REGINA / FOUNDER — E SOMENTE ISSO

Ao terminar a implementação offline/dry-run, produzir uma checklist externa curta.

Exemplo de saída aceitável:

```text
REGINA / FOUNDER — MEDIÇÕES FINAIS

[ ] autorizar UMA apólice real para criação controlada
[ ] confirmar a tela/popup real que ainda não apareceu no discovery
[ ] mostrar o fluxo final depois da escolha domicílio/loja
[ ] escolher UMA opção real de loja/agenda para mapear continuidade
[ ] demonstrar o “portal Maxpar do corretor” e fornecer acesso legítimo, se necessário
[ ] abrir “Consultar atendimento” em um caso real para medir identificadores/status
```

O objetivo é que **não sobrem tarefas de engenharia genéricas para Regina**. Ela só fornece a realidade que ninguém consegue deduzir sem executar um atendimento real.

---

# 35. RELATÓRIO FINAL OBRIGATÓRIO

O Claude Code deve terminar a SPEC com um relatório contendo:

## Git

```text
branch inicial
HEAD inicial
commits da SPEC
HEAD final
arquivos alterados
```

## Banco

```text
queries read-only executadas
writes executados (esperado: nenhum schema; seeds somente se legitimamente necessários)
migrations: nenhuma OU justificativa completa
```

## Testes

```text
baseline antes
novos testes
mutation score / mutações mortas
regressão cobrança
```

## Portal Worker

```text
flags
runtime path
checkpoint path
retry rules
```

## Vidros

```text
route resolver
preflight
multi-item
identity gate
80%
commit guard
protocolo/franquia/link
continuação
consulta
```

## Medição

Tabela:

| capability | estado | prova |
|---|---|---|
| abrir atendimento até 80 | MEASURED | ... |
| commit real | NOT_RUN/MEASURED | ... |
| trio final | FIXTURE/MEASURED | ... |
| continuação | READY/MEASURED | ... |
| consultar | READY/MEASURED | ... |
| Maxpar privado | READY_FOR_REGINA_MEASUREMENT/MEASURED | ... |

## Pendências

Somente pendências que precisam de mundo real, com pergunta exata para Regina/Founder.

---

# 36. DEFINIÇÃO DE SUCESSO

A SPEC-074 está tecnicamente concluída quando o AutoBrokers deixa de tratar o Portal de Vidros como “um formulário que o robô tenta preencher” e passa a tratá-lo como **um workflow externo transacional governado**.

Isso significa:

```text
sabe antes de entrar
não inventa
decide o canal certo
confere a identidade
lê opções reais
usa IA só onde precisa
protege o clique irreversível
sabe se o pedido nasceu
nunca abre duas vezes
captura o que o cliente precisa
continua o mesmo atendimento
consegue reconciliar/consultar
para com dossiê útil quando o mundo real ainda não foi medido
```

E a prova de que essa evolução foi bem feita é dupla:

1. **o Portal de Vidros fica muito mais completo e pronto para o teste final com Regina**;
2. **o Auxiliar de Cobrança e todas as journeys já prontas continuam funcionando exatamente como antes ou melhor.**

Essa segunda prova é obrigatória. Uma arquitetura que melhora vidros quebrando cobrança não é evolução do Portal Worker; é regressão.

---

# 37. HANDOFF PARA A PRÓXIMA SPEC

Após a 074, a próxima SPEC não deve criar mais infraestrutura browser genérica.

A fundação já será:

```text
SPEC-073 = Portal Worker robusto e transversal
SPEC-074 = primeiro workflow transacional complexo plenamente modelado
```

A próxima SPEC deve usar essa base para **generalizar a fábrica de novas capabilities/portais para agentes e auxiliares**, com contrato de onboarding rápido, replay por fixtures, profiler, shadow/dry-run, canário, score de cobertura e documentação automática — sem reescrever cada portal como projeto artesanal.

Essa será a ponte para o objetivo maior do AutoBrokers.ai: o Portal Worker deixar de ser um conjunto de automações isoladas e virar uma **plataforma de execução externa para qualquer agente/auxiliar autorizado**, mantendo cobrança e vidros como linhas de controle reais.
