---
status: "PRONTA PARA EXECUÇÃO — solicitada pelo Founder em 15/08/2026"
spec: "SPEC-073"
titulo: "Portal Worker 2.0 — Hardening transversal, Portal Profiler, Discovery Mode, percepção em camadas e zero regressão"
criada_em: "2026-08-15"
branch_sugerida: "feat/spec073-portal-worker-hardening"
repo: "Amandico100/AutoBrokers-Intelligence-OS"
baseline_main_observada: "0ffcbed44ba012d9a41e23823729837b6defd076"
supabase_producao: "dcajcvlzcjbmyapmklil"
deploy_esperado: "portal-worker"
migration_esperada: "nenhuma"
---

# SPEC-073 — Portal Worker 2.0
## Hardening transversal, Portal Profiler, Discovery Mode, percepção em camadas e zero regressão

> **Regra central desta SPEC:** o Portal Worker deve ficar mais inteligente e mais resiliente **sem mudar o que já funciona**. Cobrança, downloads de boletos, sessões persistidas, jornadas autenticadas e o acionamento atual de vidros são patrimônio do produto. Esta SPEC não reescreve esses fluxos; ela coloca uma camada de execução, observabilidade e segurança **por baixo e ao redor deles**.

---

# 0. Decisão desta SPEC

Esta SPEC cria a fundação compartilhada para que o mesmo `portal-worker` consiga executar, com segurança e previsibilidade:

- Auxiliares que entram em portais de corretor, como **Cobrança Feita**;
- agentes de atendimento que acionam portais públicos, como **vidros/faróis/lanternas**;
- jornadas futuras de renovação, consulta, documentos, sinistro, assistência e outras capacidades;
- portais com HTML tradicional;
- portais SPA com APIs internas;
- portais protegidos por Akamai/Cloudflare/DataDome;
- telas que mudam parcialmente;
- telas inesperadas em que o caminho determinístico não basta;
- casos em que uma ação material pode criar algo irreversível e, portanto, **não pode ser repetida às cegas**.

A arquitetura-alvo é:

```text
portal_job
  ↓
portal-worker existente
  ↓
Journey existente do registry
  ↓
camadas de resolução, sempre nesta ordem

0. fato conhecido por código
1. API legítima do próprio portal, quando a journey conhece/prova a API
2. DOM semântico + Playwright determinístico
3. adaptive textual sobre estado estruturado
4. visão multimodal real sobre screenshot + DOM mínimo
5. HITL humano com evidência suficiente

NUNCA:
  chute de opção crítica
  retry cego depois de efeito material
  segundo motor paralelo
  segundo registry
  nova arquitetura só para uma seguradora
```

A SPEC seguinte, **SPEC-074**, usa esta fundação para tornar o portal de vidros Maxpar/AutoGlass realmente dinâmico e API-first com Yelum + Porto como casos medidos. A parte final de loja/domicílio/dia/hora e a equivalência final do `vistoria.mobi` serão fechadas com a captura real da Regina, sem bloquear a execução desta SPEC-073.

---

# 1. Autoridade e leitura obrigatória antes de qualquer alteração

O executor deve ler, nesta ordem, antes de editar código:

1. `CLAUDE.md`
2. `docs/canon/EXECUTION-MASTER-PLAN.md`
3. `docs/canon/FOUNDER-DECISIONS.md`
4. `docs/canon/MIGRATIONS-AUTHORITY.md`
5. `docs/canon/PORTAIS-E-CORREDORES.md`
6. `docs/canon/PENDENCIAS.md`
7. `docs/canon/specs/SPEC-020*` e a implementação atual do Portal Worker
8. `docs/canon/specs/SPEC-023-portais-autenticados-hitl-cobranca.md`
9. `docs/canon/specs/SPEC-065*` — acionamento de vidros ponta a ponta
10. `docs/canon/specs/SPEC-070-cobranca-multi-seguradora.md`
11. `docs/canon/specs/SPEC-071-atendimento-ponta-a-ponta.md`
12. esta SPEC.

Se um documento antigo contradizer **código atual + banco vivo + decisão posterior do Founder**, registrar o conflito e usar a autoridade mais recente. Não reviver trava, arquitetura ou suposição vencida só porque um texto antigo ainda contém a frase.

---

# 2. Preflight obrigatório — sem destruir estado local

Antes de qualquer `checkout`, `pull`, `reset`, merge ou criação de branch:

```bash
git rev-parse --show-toplevel
git branch --show-current
git rev-parse HEAD
git status --short
git fetch origin
git rev-parse origin/main
```

Esperado para a pasta canônica de execução:

```text
AutoBrokers-Opus-Exec
```

## Regras

- **NÃO** executar `git reset --hard`.
- **NÃO** apagar stash, untracked ou alteração local para “limpar”.
- Se houver mudança local que possa ser perdida, preservar primeiro.
- Criar uma única branch para a SPEC:

```text
feat/spec073-portal-worker-hardening
```

- Uma SPEC = uma branch = um relatório final = um gate final.
- Não pedir aprovação manual entre todos os blocos. Gate verde → segue para o próximo bloco, conforme D6.

---

# 3. Estado factual que NÃO pode ser regredido

## 3.1 Portal Worker atual

O worker atual já possui mecanismos importantes e **eles permanecem**:

- `portal_jobs` como fila durável;
- claim `queued -> running`;
- timeout duro por journey via `PORTAL_JOB_TIMEOUT_SECONDS`;
- recuperação de job órfão;
- Playwright/Chromium;
- `--headless=new` para portais que bloqueiam o headless clássico;
- User-Agent sem `HeadlessChrome`;
- locale `pt-BR` e timezone `America/Sao_Paulo`;
- proxy configurável por portal;
- cofre de credenciais;
- `portal_sessions` com `storage_state` e `sessionStorage` criptografados;
- `account_label` para contas em que um login pode enxergar mais de uma corretora;
- bucket privado `portal-evidence`;
- HITL com screenshot;
- `JourneyResult(status, captured, screenshots, message)`;
- registry único `JOURNEYS` em `backend/portal_worker/journeys/__init__.py`.

Nada disso será substituído por Stagehand, Skyvern, Browser Use, outro worker ou “framework mais moderno”. Pode-se absorver boas ideias, não trocar um sistema provado por dependência nova sem ganho medido.

## 3.2 Registry atual de cobrança

Na `main` observada, `JOURNEYS` já registra `cobranca_sweep` para:

```text
allianz_corretor
hdi_corretor
tokiomarine_corretor
yelum_corretor
mapfre_corretor
zurich_corretor
```

`portais_com_cobranca()` deriva a capacidade **do registry**. Não criar uma segunda lista independente.

## 3.3 Verdade do banco em 15/08/2026

Projeto Supabase:

```text
AutoBrokers Intelligence OS
dcajcvlzcjbmyapmklil
```

Contagens observadas:

```text
portals ................ 17
portal_accounts ........ 16
portal_jobs ............ 106
billing_sent_log ....... 4
auxiliary_templates .... 15
tenant_auxiliaries ..... 3
routines ............... 1
```

Os 17 portais cadastrados estão ativos; são 15 portais de corretor e 2 portais públicos de vidros.

Distribuição histórica de `portal_jobs` observada:

```text
allianz_corretor / cobranca_sweep   done 22 · needs_human 34
hdi_corretor / cobranca_sweep       done 3  · failed 2
tokiomarine_corretor / cobrança     done 3
yelum_corretor / cobrança           done 2
zurich_corretor / cobrança          done 1
vidros_lanternas / abrir_atendimento done 1 · failed 5 · needs_human 33
```

### AVISO IMPORTANTE — NÃO INTERPRETAR MAL OS 39 JOBS DE VIDROS

Os `33 needs_human + 5 failed` são majoritariamente **histórico de desenvolvimento e travas deliberadas enquanto o fluxo estava sendo construído**. O Founder esclareceu que a execução feita **depois de o fluxo estar finalizado** chegou ao final e retornou no WhatsApp; portanto esses 38 jobs antigos **NÃO** são métrica válida da qualidade atual.

O executor NÃO deve criar um projeto de “corrigir 38 falhas” baseado nessa estatística. Eles servem apenas como material histórico para encontrar classes de erro já conhecidas.

## 3.4 Cobrança Feita — preservar integralmente

Existe um único template:

```text
Cobrança Feita
slug: cobranca-feita
```

Existe uma rotina instalada em Resulta, hoje inativa e em modo de teste. O fato de a configuração atual listar apenas Allianz **não redefine a capacidade do worker** — o registry já suporta mais portais.

O serviço `backend/app/services/billing_collection.py` já protege comportamentos que não podem regredir:

- uma única rotina global, não um Auxiliar por seguradora;
- coleta e entrega separadas;
- carência mínima de 48h;
- sem data legível => não envia;
- ordenação de dívida antiga antes da nova;
- sem boleto por regra da seguradora => tarefa humana, sem promessa falsa ao segurado;
- `billing_sent_log` como anti-duplicação de envio;
- governador de saída para não disparar rajadas no WhatsApp;
- interrupção segura e retomada posterior sem reenviar o que já saiu.

**A SPEC-073 não muda nenhuma dessas regras de negócio.**

---

# 4. Problemas que esta SPEC precisa resolver

## P1 — o “Vision” atual não é visão multimodal real

Hoje `adaptive.capture_state()` serializa DOM e `decide_next_action()` envia texto/JSON ao modelo. Isso é uma boa camada semântica, mas o modelo **não recebe a imagem real da tela**.

Consequência: elementos visualmente óbvios, overlays, banners, modais, canvas, ícones, estados de seleção e alterações que não aparecem bem no DOM podem continuar invisíveis.

## P2 — `PORTAL_DISCOVERY_MODE` ainda não existe

O modo solicitado pelo Founder:

```text
PORTAL_DISCOVERY_MODE=true
```

precisa ser implementado. Ele deve observar a realidade do portal, comparar com o que a journey conhece e produzir evidência útil **sem transformar o portal em ambiente de teste transacional**.

## P3 — não existe Portal Profiler transversal

As jornadas foram descobertas manualmente com HAR, HTML, DevTools e inspeção. Isso funcionou, mas ainda não há uma camada do worker que automaticamente capture, de forma segura:

- Network relevante;
- endpoints candidatos;
- status/content-type/timing;
- DOM semântico;
- assinatura de tela;
- screenshot quando necessário;
- sequência de ações;
- mudança de tela;
- drift.

## P4 — o recovery de job órfão é seguro para leitura, mas perigoso depois de efeito material

Hoje `recover_stale_jobs()` reenvia uma primeira execução órfã para `queued` com base em idade/tentativas.

Isso é correto para:

```text
listar parcelas
baixar PDF
consultar apólice
abrir página
```

Mas é perigoso se o processo morrer depois de:

```text
criar atendimento
agendar serviço
cancelar atendimento
alterar forma de pagamento
enviar algo à seguradora
```

Se o efeito aconteceu e a resposta se perdeu, recomeçar do zero pode duplicar a operação.

## P5 — ainda existe o conceito de “force choose”

`adaptive.py` possui `_FORCE_CHOOSE`, que pode instruir o modelo a escolher a primeira opção válida quando não houver relato claro.

O código atual já protege vários selects críticos, mas a regra arquitetural precisa ser absoluta:

> **Nenhum dado crítico do segurado, dano, cobertura, peça, lado, causa, local, oficina, data, horário, pagamento ou efeito irreversível é escolhido por posição de lista.**

Campos puramente de formato podem ter default determinístico **declarado por código**. Não por um LLM “forçado”.

## P6 — não existe uma classificação comum de efeito

O worker precisa distinguir semanticamente:

```text
READ_ONLY
REVERSIBLE_UI
MATERIAL_SIDE_EFFECT
```

HTTP `POST` não significa necessariamente efeito material: exportar relatório pode ser POST e continuar read-only. A classificação é da **capacidade**, não do verbo HTTP.

## P7 — observabilidade ainda é resultado, não trajetória

Hoje existe `evidence`, screenshots e logs. Falta uma trajetória compacta e estruturada que responda rapidamente:

```text
qual camada resolveu?
qual endpoint mudou?
qual tela era esperada?
onde o DOM divergiu?
houve chamada de visão?
houve efeito material?
o efeito foi confirmado ou ficou incerto?
por que caiu para humano?
```

---

# 5. Regras invioláveis da implementação

## R1 — um único motor

Não criar:

- `portal-worker-v2`;
- segundo polling loop;
- segunda tabela de jobs;
- segundo registry;
- “worker de visão” separado;
- “worker de discovery” separado.

Tudo entra no `portal-worker` atual como infraestrutura compartilhada.

## R2 — compatibilidade do contrato

A assinatura existente continua válida:

```python
journey_fn(page, params, evidence) -> JourneyResult
```

`JourneyResult` continua aceitando:

```text
status = done | needs_human | failed
captured
screenshots
message
```

Não fazer migração em massa de todas as journeys só para passar um novo objeto.

## R3 — runtime novo entra de forma aditiva

O worker pode injetar em `params` uma chave reservada:

```python
params["_runtime"] = PortalRuntimeContext(...)
```

Jornadas antigas ignoram e continuam funcionando.

Jornadas novas ou modernizadas podem consumir:

```python
runtime = params.get("_runtime")
```

Isso permite evoluir sem quebrar Allianz/HDI/Tokio/Yelum/MAPFRE/Zurich.

## R4 — sem schema novo nesta SPEC

Usar primeiro o que já existe:

```text
portal_jobs.evidence jsonb
portal_jobs.screenshots jsonb
portal-evidence bucket
portal_jobs.idempotency_key
portal_jobs.company_id
portal_jobs.account_id
portal_sessions
```

Se durante a execução surgir uma necessidade REAL de nova coluna/tabela, o executor deve provar por que o estado existente é insuficiente. Não criar tabela “porque fica mais limpo”.

Caso alguma migration passe a ser realmente necessária:

- seguir `MIGRATIONS-AUTHORITY.md`;
- diretório `backend/supabase/migrations/`;
- expand-first;
- VERIFY e ROLLBACK escritos antes;
- nunca reaplicar migrations históricas.

## R5 — captura privada nunca vira fixture bruta

É proibido commitar:

- `.har` real;
- HTML real de cliente;
- cookie;
- Authorization;
- JWT;
- `storage_state`;
- senha;
- CPF real;
- placa real;
- nome real;
- número de apólice real;
- boleto real.

Fixtures são sintéticas ou anonimizadas.

## R6 — fato conhecido não passa por modelo

Preservar e ampliar a regra já existente em `adaptive.py`:

> **o que tem um único valor correto e já é conhecido pelo sistema é preenchido por código.**

Modelo entra para julgamento semântico, não para transcrever CPF, nome, e-mail, telefone, UF, CEP, apólice ou dado já resolvido.

## R7 — modelo não autoriza efeito material

Texto LLM e visão multimodal podem:

- reconhecer tela;
- interpretar pergunta;
- selecionar uma opção real com base em dado conhecido;
- apontar próximo elemento.

Eles **não** podem, sozinhos, liberar:

- `submit` que cria atendimento;
- agendamento;
- cancelamento;
- mudança financeira;
- envio a seguradora;
- aceite contratual.

A autorização vem de regra determinística do runtime/journey e dos parâmetros governados.

## R8 — desconhecido falha fechado

Se não houver confiança suficiente:

```text
needs_human + evidência
```

Nunca:

```text
“primeira opção”
“provavelmente é isso”
retry infinito
```

---

# 6. Arquitetura a implementar

## 6.1 Novo `PortalRuntimeContext`

Criar, preferencialmente:

```text
backend/portal_worker/runtime.py
```

Estrutura mínima:

```python
@dataclass
class PortalRuntimeContext:
    job_id: str
    company_id: str
    portal_key: str
    journey: str
    account_id: str | None
    account_label: str
    discovery_mode: bool
    vision_enabled: bool
    evidence: dict
    profiler: PortalProfiler
    guard: PortalActionGuard
    checkpoint: Callable[..., Awaitable[None]]
```

### Regras

- não conter senha;
- não conter Authorization serializável;
- não implementar lógica de negócio de seguradora;
- não substituir `params`;
- não ser salvo no banco;
- ser criado uma única vez por `_run_job`.

## 6.2 Validação explícita de identidade antes de abrir browser

O banco já possui isolamento por `company_id`, mas o worker deve adicionar defesa em profundidade.

Ao carregar `portal_accounts`:

```text
job.company_id == account.company_id
job.portal_key == account.portal_key
```

Se qualquer um divergir:

```text
status = failed
classe = tenant_or_portal_mismatch
browser NÃO abre
credencial NÃO é usada
```

Para MAPFRE e qualquer portal multiempresa, `account_label` continua obrigatório como identidade de trabalho.

---

# 7. Bloco A — Congelar a linha de base de regressão

## Objetivo

Antes de melhorar o motor, registrar precisamente o que já funciona e criar uma rede que reprova qualquer tentativa de “modernizar” quebrando produção.

## Ações

### A1. Inventário automático do registry

Criar teste que prova que, no início da SPEC, continuam existindo pelo menos:

```text
allianz_corretor.cobranca_sweep
hdi_corretor.cobranca_sweep
tokiomarine_corretor.cobranca_sweep
yelum_corretor.cobranca_sweep
mapfre_corretor.cobranca_sweep
zurich_corretor.cobranca_sweep
vidros_lanternas.abrir_atendimento
```

O teste deve permitir **adição**, nunca exigir igualdade absoluta se outra journey legítima entrar antes do merge.

### A2. Contract test do `JourneyResult`

Provar que uma journey antiga continua podendo devolver o mesmo objeto sem conhecer runtime/profiler/vision.

### A3. Contract test do worker

Com runtime novo desligado:

```text
job queued
→ claim running
→ chama journey antiga
→ escreve done/needs_human/failed
```

igual ao comportamento anterior.

### A4. Golden tests da cobrança

Rodar e preservar as suítes atuais relevantes, incluindo as já existentes para:

```text
Tokio
Yelum
MAPFRE
Zurich
registro global da cobrança
worker hardening
portal base
```

E acrescentar uma suíte agregadora:

```text
backend/tests/test_spec073_zero_regressao_portais.py
```

Ela não reimplementa os parsers das seguradoras; apenas prova os contratos externos.

### A5. Cobrança como canário

A SPEC só fecha se a modernização transversal provar que **não alterou**:

- `portais_com_cobranca()`;
- coleta de itens;
- download de PDFs;
- `sem_boleto_por_regra`;
- carência de 48h;
- ordenação;
- anti-duplicação;
- separação coleta/entrega;
- governador de envio.

## Gate A

```text
baseline registrado
+ testes existentes verdes
+ nenhum arquivo de journey reescrito sem necessidade
```

Se o baseline já estiver vermelho antes da mudança, registrar como preexistente e separar do escopo; não mascarar.

---

# 8. Bloco B — Checkpoint transacional e recuperação sem duplicidade

Este é o hardening mais importante desta SPEC.

## B1. Classificação de ações

Criar:

```text
backend/portal_worker/guardrails.py
```

Tipos:

```python
READ_ONLY = "read_only"
REVERSIBLE_UI = "reversible_ui"
MATERIAL_SIDE_EFFECT = "material_side_effect"
```

Exemplos:

```text
READ_ONLY
  login
  navegar
  filtrar
  consultar
  listar
  baixar PDF
  exportar relatório

REVERSIBLE_UI
  preencher campo ainda não enviado
  abrir dropdown
  selecionar opção local antes da confirmação

MATERIAL_SIDE_EFFECT
  criar atendimento
  agendar
  cancelar
  alterar pagamento
  converter débito/cartão em boleto
  enviar solicitação
  confirmar mudança contratual
```

**Semântica vence verbo HTTP.** POST de exportação pode ser `READ_ONLY`.

## B2. `PortalActionGuard`

API proposta:

```python
await runtime.guard.before(
    action="create_attendance",
    action_class=MATERIAL_SIDE_EFFECT,
    details={...dados não sensíveis...},
)
```

Regras:

- discovery mode => `MATERIAL_SIDE_EFFECT` sempre bloqueado;
- ação material sem liberação explícita da journey => bloqueada;
- visão/LLM não pode elevar permissão;
- a journey continua dona de decidir **qual** ação material existe.

## B3. Checkpoint ANTES do efeito

Antes de executar ação material, persistir no próprio `portal_jobs.evidence`:

```json
{
  "critical_effect": {
    "name": "create_attendance",
    "phase": "armed",
    "armed_at": "...",
    "fingerprint": "...",
    "resume_policy": "reconcile_before_retry"
  }
}
```

`fingerprint` nunca contém PII bruta. Deve usar hash de identidade semântica suficiente para auditoria.

## B4. Checkpoint depois do envio

Assim que a UI/API efetivamente disparar:

```text
phase = submitted
```

Assim que existir prova autoritativa:

```text
phase = confirmed
receipt/protocolo/codigo seguro = registrado
```

Se a chamada sair e a resposta ficar incerta:

```text
phase = unknown
```

## B5. Mudança obrigatória no stale recovery

Hoje um stale job é reenfileirado na primeira ocorrência. Depois desta SPEC:

```text
sem critical_effect
  → comportamento antigo permanece

critical_effect.confirmed
  → NÃO reexecutar a criação; job deve ser reconciliado/encerrado conforme journey

critical_effect.armed/submitted/unknown
  → NUNCA recomeçar do passo 1 automaticamente
  → needs_human com motivo "efeito material incerto"
  → futura SPEC pode fornecer reconciler automático
```

Isso protege cobrança read-only **e** prepara o acionamento de vidros para não duplicar pedido.

## B6. Persistência incremental

Adicionar no runtime uma função `checkpoint()` que atualiza `portal_jobs.evidence` durante a execução.

Não esperar o `JourneyResult` final para gravar algo crítico.

### Regra

A informação cuja perda pode causar repetição material precisa chegar ao banco **antes** do próximo clique perigoso.

## Gate B

Testar crash simulado em três pontos:

```text
1. antes de armar efeito       → pode recomeçar
2. depois de armed/submitted   → NÃO recomeça automaticamente
3. depois de confirmed         → não cria de novo
```

Controle obrigatório:

```text
job read-only órfão continua sendo recuperado como hoje
```

---

# 9. Bloco C — `PORTAL_DISCOVERY_MODE`

## C1. Flags

Implementar:

```text
PORTAL_DISCOVERY_MODE=false
PORTAL_DISCOVERY_RAW_TRACE=false
PORTAL_PROFILER_ENABLED=true
```

Regras:

- `PORTAL_DISCOVERY_MODE=false` é o padrão;
- discovery pode ser ligado por ambiente sem mudar journey;
- `RAW_TRACE` continua `false` em produção;
- nenhuma flag contém segredo.

Também permitir override por job **somente reduzindo poder**, nunca elevando:

```text
env discovery=true  → job não pode desligar a trava material
env discovery=false → um job técnico explicitamente marcado pode pedir profiler,
                       mas não ganha permissão material por causa disso
```

## C2. O que discovery significa

Discovery é:

```text
observar
medir
comparar
explicar divergência
sugerir o próximo adapter
```

Discovery NÃO é:

```text
clicar em tudo
criar atendimento de teste
mudar pagamento
cancelar
agendar
```

## C3. Saída esperada

Em `evidence.discovery`:

```json
{
  "enabled": true,
  "screen_signature": "...",
  "expected_signature": "...",
  "drift": "none|cosmetic|semantic|critical|unknown",
  "network_candidates": [],
  "fallback_path": [],
  "unknown_elements": [],
  "recommendation": "..."
}
```

Nada de HTML inteiro.

## C4. “discovery → compare → exceção”

O ciclo correto pedido pelo Founder será:

```text
journey executa caminho conhecido
→ profiler observa
→ compara assinatura atual x assinatura conhecida
→ classifica mudança
→ se mudança é segura e genérica, motor adaptativo consegue seguir
→ se exige regra nova, evidence produz o delta exato
→ executor humano/Claude acrescenta a exceção testada
→ nova fixture impede regressão
```

**Não implementar autoedição de código em produção.** A exceção precisa virar código/teste versionado.

## Gate C

Com discovery ligado em fixture sintética contendo botão material:

```text
profiler captura
vision pode reconhecer
DOM pode ler
MAS guard impede o clique material
```

---

# 10. Bloco D — Portal Profiler: Network + DOM + Screenshot + Trace

Criar:

```text
backend/portal_worker/profiler.py
```

O profiler é **passivo**. Ele observa eventos do `page/context`; não intercepta nem altera requests como comportamento padrão.

## D1. Network profiler

Escutar, no mínimo:

```text
request
response
requestfailed
framenavigated
```

Para cada request relevante, gravar somente:

```text
method
host
path normalizado
resource_type
status
content_type
latency_ms quando possível
request_size aproximado
response_size aproximado
origem first_party | asset | telemetry | third_party | unknown
```

## D2. Nunca persistir headers sensíveis

Blacklist mínima:

```text
authorization
cookie
set-cookie
x-api-key
proxy-authorization
client-secret
access-token
refresh-token
jwt
senha/password
```

Mesmo em discovery.

## D3. Body por estrutura, não por conteúdo

Para JSON, persistir uma **shape**:

```json
{
  "cpf": "<string>",
  "placa": "<string>",
  "itens": "<array:21>"
}
```

Não persistir:

```text
CPF real
placa real
nome
telefone
apólice
endereço
JWT
```

Quando o corpo é indispensável para entender a API, a journey pode declarar uma allowlist de campos de negócio seguros ou criar fixture anonimizada offline.

## D4. Identificação de candidatos de API

O profiler deve destacar, sem afirmar automaticamente que pode replayar:

```text
XHR/fetch
JSON/PDF
primeira parte
endpoint repetido após ação de tela
endpoint que retorna catálogo/opções/perguntas/documento
```

Saída:

```json
{
  "method": "POST",
  "path": "/questionarios/perguntas",
  "status": 204,
  "confidence": "candidate",
  "reason": "first_party xhr + response state changed"
}
```

O uso real da API será implementado por journey específica na SPEC-074, não magicamente pelo profiler.

## D5. DOM semantic snapshot

Reaproveitar e evoluir `capture_state()` sem duplicar outro extrator.

Assinatura da tela deve usar elementos de sentido:

```text
URL/route
heading
labels de input
select labels
opções visíveis
botões visíveis
campos obrigatórios vazios
modal/dialog visível
marcas de erro/sucesso
```

Gerar `screen_fingerprint` a partir da forma sanitizada.

IDs dinâmicos como `input_1`, UUID e números de sessão não podem dominar o hash.

## D6. Screenshot seletivo

Screenshot é capturado quando:

- tela desconhecida;
- drift semântico/critical;
- `needs_human`;
- visão real for chamada;
- discovery explicitamente pedir.

Não tirar screenshot em cada passo por padrão.

Preferência para novo profiler:

```text
upload em portal-evidence
→ evidence guarda path
```

Evitar base64 gigante no JSON de `portal_jobs`.

Não é obrigatório migrar screenshots HITL antigas nesta SPEC; compatibilidade primeiro.

## D7. Trace

Criar trace **sanitizado e estruturado**:

```json
[
  {"n":1,"layer":"dom","action":"fill","target":"placa","result":"filled"},
  {"n":2,"layer":"network","event":"POST /api/...","status":200},
  {"n":3,"layer":"dom","screen":"passo2","drift":"none"}
]
```

Limitar tamanho. Sugestão:

```text
máx. 80 eventos por job
strings truncadas
sem DOM bruto
sem body bruto
```

`PORTAL_DISCOVERY_RAW_TRACE=true` pode habilitar Playwright Trace apenas em ambiente técnico autorizado. O ZIP bruto:

- nunca vai para Git;
- nunca é exigido para produção;
- pode conter PII, portanto é material privado.

## Gate D

Fixture com Authorization + Cookie + CPF + placa:

```text
profiler vê a requisição
mas o artefato final contém ZERO desses valores brutos
```

---

# 11. Bloco E — Percepção em camadas e visão multimodal real

Criar:

```text
backend/portal_worker/perception.py
```

Sem transformar isso num segundo agente.

## E1. Escada única de percepção

```text
L0 — fatos determinísticos
L1 — API conhecida da própria aplicação
L2 — DOM semântico
L3 — modelo textual com estado estruturado
L4 — visão multimodal com screenshot + DOM mínimo
L5 — humano
```

### Princípio

Subir de camada só quando a anterior **não consegue resolver com confiança**.

Isso reduz:

- custo;
- latência;
- aleatoriedade;
- envio desnecessário de imagem/PII para modelo.

## E2. Não quebrar o adaptive atual

`run_adaptive()` continua existindo.

A mudança é extrair a decisão de percepção para uma interface comum, preservando o caminho textual atual como fallback compatível.

Interface proposta:

```python
class PortalPerceptionProvider(Protocol):
    async def decide(
        self,
        *,
        state: dict,
        screenshot: bytes | None,
        goal: str,
        collected: dict,
        history: list,
    ) -> dict: ...
```

## E3. Visão multimodal real

Quando L3 falhar, a tela for desconhecida ou o DOM não representar bem o estado:

```text
captura screenshot
+ recorte/viewport necessário
+ resumo DOM pequeno
+ objetivo
+ lista de ações permitidas
→ modelo multimodal
```

A resposta continua no MESMO schema de ações:

```json
{"action":"fill|select|click|check|ask_human", "target":"...", "value":"...", "reason":"..."}
```

Não criar schema novo só para visão.

## E4. Validador determinístico depois do modelo

Antes de executar qualquer ação proposta por texto ou visão:

1. target existe na tela atual;
2. opção existe na lista real quando aplicável;
3. valor crítico não foi inventado;
4. ação não viola `PortalActionGuard`;
5. ação não repete um passo que já deu sucesso sem mudança de estado;
6. botão material exige autorização determinística.

Se falhar:

```text
não executa
registra reject_reason
sobe de camada ou needs_human
```

## E5. Provider não pode ser arquitetura

A integração deve ser trocável por env/config.

Manter compatibilidade com o provedor atualmente usado e criar interface para benchmark posterior.

Candidatos citados pelo Founder para avaliação na SPEC-074, **se estiverem realmente disponíveis na conta/API na data da execução**:

```text
GPT-5.6 Terra + visão
Gemini 3.7 Flash
```

Não hardcodar decisão comercial nesta SPEC.

O benchmark deve escolher por:

```text
acerto da próxima ação
0 falso positivo de ação material
respeito às opções reais
taxa de ask_human correta
latência
custo
conformidade de JSON
```

## E6. Privacidade da visão

Screenshot de portal pode conter PII.

`PORTAL_VISION_ENABLED` só pode ficar `true` quando:

- chave/provider configurado;
- política de dados do provider for aceitável para o ambiente;
- não houver logging do payload de imagem;
- screenshot não for persistido em serviço público;
- somente o mínimo necessário for enviado.

Se visão estiver desligada:

```text
L0-L3 continuam funcionando
→ depois HITL
```

Ou seja, visão é melhoria aditiva, nunca dependência que derruba o worker.

## E7. Gancho futuro para WhatsApp

A função de percepção de imagem deve receber `bytes` + contexto, não depender diretamente de `page.screenshot()` internamente.

Assim, no futuro, o mesmo interpretador pode analisar **uma imagem recebida pelo canal de WhatsApp** sem duplicar o motor multimodal.

**NÃO ligar isso ao WhatsApp nesta SPEC.** O canal de WhatsApp não “enxerga a interface do aplicativo” por magia; ele poderá analisar mídia recebida quando o fluxo de atendimento for explicitamente conectado a esta camada.

## Gate E

Com provider de visão mockado:

```text
imagem sugere clicar em “Confirmar” material
→ guard recusa
```

Com imagem sugerindo uma opção que não existe no DOM:

```text
→ ação rejeitada
```

Com provider fora do ar:

```text
→ sem crash do worker
→ HITL honesto
```

---

# 12. Bloco F — retirar o chute e tratar tela desconhecida corretamente

## F1. `_FORCE_CHOOSE`

O comportamento atual deve ser alterado.

Objetivo final:

```text
nenhuma regra genérica diz “escolha a primeira opção”
```

Campos de formato que realmente admitem qualquer valor devem ser resolvidos por código, como já ocorre com:

```text
relação = Corretor
tipo de telefone = valor permitido e explicitamente tolerante
```

Não usar LLM para simular default.

## F2. Select crítico

Consolidar a regra:

```text
match confiante → seleciona
sem match → devolve opções reais
resposta do segurado presente → tenta casar
sem dado suficiente → ask_human
```

Nunca:

```text
reais[0]
```

para campo crítico.

## F3. Tela desconhecida

Criar classificador simples, baseado em assinatura, sem IA como primeira opção:

```text
KNOWN
DRIFT_COSMETIC
DRIFT_SEMANTIC
UNKNOWN
CRITICAL_UNKNOWN
```

### `DRIFT_COSMETIC`

Exemplo:

```text
texto auxiliar mudou, anchors principais continuam
```

Pode seguir e registrar.

### `DRIFT_SEMANTIC`

Exemplo:

```text
novo campo obrigatório
nova pergunta
nova opção
```

Tentar perception ladder.

### `CRITICAL_UNKNOWN`

Exemplo:

```text
novo botão de confirmar
mudança de pagamento
cancelamento
termo de aceite
nova fronteira de submit
```

Pode ser diagnosticado por visão, mas **não executado automaticamente** até existir regra/teste.

## F4. Sem progresso

Atual `run_adaptive()` já para após repetições idênticas. Evoluir:

```text
1º insucesso → ler estado de novo
2º insucesso equivalente → visão multimodal, se habilitada
3º sem progresso → HITL com profiler + screenshot + pergunta/opções
```

Não gastar 22 passos repetindo a mesma ação.

## Gate F

Mutation test deve reprovar se alguém reintroduzir:

```text
primeira opção em campo crítico
force choose genérico
loop de ação já bem-sucedida
```

---

# 13. Bloco G — API legítima da aplicação como primeira classe, sem atalho inseguro

Esta SPEC cria a **infraestrutura**, não migra todas as journeys de uma vez.

## G1. Princípio

Quando um portal SPA já usa uma API para realizar uma consulta, o caminho preferido é:

```text
browser obtém sessão legítima
→ journey observa a própria aplicação
→ reutiliza sessão/token em memória
→ chama endpoint read-only/provado
```

Isso é diferente de:

```text
inventar token
burlar login
hardcodar Authorization
usar endpoint de outro tenant
```

## G2. `PortalApiSession`

Dentro do runtime/perception, oferecer utilitário opcional que consegue:

- extrair cookies do contexto;
- copiar headers **apenas em memória**;
- executar request com a sessão atual;
- nunca devolver segredo para `evidence`;
- escopar host permitido ao portal atual;
- bloquear host externo não aprovado.

Não converter todas as journeys agora.

## G3. Network candidate != API aprovada

O profiler pode descobrir um endpoint.

Ele só vira adapter da journey depois de:

```text
reproduzir com sessão legítima
provar resposta
provar tenant correto
provar sem efeito material indevido
criar parser puro
criar fixture anonimizada
```

Esse é o padrão que já funcionou na cobrança.

## Gate G

Teste deve provar:

```text
runtime não persiste Authorization
runtime não chama host fora da allowlist
falha da API pode cair para DOM sem matar a journey
```

---

# 14. Bloco H — evidência que ensina, sem vazar

## H1. Estrutura padrão

Ao final de qualquer job modernizado, `evidence` deve poder responder:

```json
{
  "runtime": {
    "portal_key": "...",
    "journey": "...",
    "discovery": false,
    "vision": false
  },
  "execution": {
    "layers_used": ["deterministic", "dom"],
    "fallback_count": 0,
    "screen_drifts": 0,
    "network_errors": 0
  },
  "critical_effect": null,
  "profiler": {
    "screens": 4,
    "requests_relevant": 7,
    "api_candidates": 1
  }
}
```

Jornadas antigas podem continuar com evidence menor. A estrutura é aditiva.

## H2. Redactor único

Criar um único sanitizador para profiler/logs.

Deve mascarar pelo menos:

```text
CPF/CNPJ
telefone
e-mail
placa
Authorization
Cookie/JWT
tokens
senha
linha digitável/cartão
```

Para debug de matching, preferir:

```text
hash
length
type
schema keys
```

## H3. Logs

Logs operacionais podem dizer:

```text
[PORTAL] job X portal=mapfre_corretor layer=api screen=receipts status=200
```

Nunca:

```text
senha=...
token=...
cpf=...
Authorization=...
```

## Gate H

Teste automático com payload “armadilha” contendo todos os tipos acima. Zero deve aparecer na saída persistida.

---

# 15. Bloco I — health e observabilidade sem instalar nova stack

Não instalar Grafana, Prometheus ou OpenTelemetry só por esta SPEC.

O worker já tem `/health` com build/versionamento. Evoluir de forma compacta para expor apenas estado não sensível:

```json
{
  "status": "ok",
  "build_sha": "...",
  "portal_real_enabled": true,
  "discovery_mode": false,
  "profiler_enabled": true,
  "vision_enabled": false,
  "job_timeout_seconds": 1200
}
```

Sem listar credenciais, proxies completos ou contas.

Logs por job devem incluir:

```text
portal_key
journey
status
elapsed_ms
layer_final
fallback_count
drift_count
critical_effect_phase, se houver
```

Isso resolve a pergunta operacional antes de criar infraestrutura de métricas nova.

## Gate I

`/health` continua subindo mesmo com:

```text
sem chave de visão
sem discovery
sem portal job
```

---

# 16. Bloco J — matriz de mutações obrigatória

Criar uma suíte dedicada, por exemplo:

```text
backend/tests/test_spec073_portal_worker_mutations.py
```

Não precisa de framework de mutation testing; pode usar monkeypatch/AST/guardas como o projeto já faz.

A implementação só é considerada robusta se as seguintes mutações forem detectadas:

| ID | Mutação que DEVE reprovar |
|---|---|
| M01 | discovery permite `MATERIAL_SIDE_EFFECT` |
| M02 | ação material acontece sem checkpoint `armed` |
| M03 | stale job com `critical_effect=unknown` volta para `queued` |
| M04 | stale job read-only deixa de ser recuperado |
| M05 | `job.company_id != account.company_id` é aceito |
| M06 | `job.portal_key != account.portal_key` é aceito |
| M07 | `Authorization` entra em evidence |
| M08 | `Cookie` entra em evidence |
| M09 | CPF/placa brutos entram no profiler |
| M10 | visão propõe opção inexistente e ela é clicada |
| M11 | visão propõe “Confirmar” material e bypassa o guard |
| M12 | `_FORCE_CHOOSE` volta a permitir primeira opção crítica |
| M13 | `_apply_select` escolhe primeira opção crítica |
| M14 | três ações sem progresso continuam até o teto sem escalar |
| M15 | provider de visão fora do ar derruba o processo |
| M16 | registry perde uma das journeys de cobrança já existentes |
| M17 | `portais_com_cobranca()` passa a usar lista hardcoded paralela |
| M18 | `JourneyResult` antigo deixa de funcionar |
| M19 | profiler altera/intercepta request por padrão |
| M20 | raw HAR/trace é gravado em Git/fixture sem sanitização |
| M21 | checkpoint só é escrito no fim do job |
| M22 | `critical_effect=confirmed` permite recriar operação em retry |

### Linha de controle

A suíte também precisa provar o contrário:

```text
login continua permitido
consulta continua permitida
download de PDF continua permitido
select tolerante explicitamente classificado continua usando default determinístico
worker sem vision continua funcionando
worker sem discovery continua funcionando
```

---

# 17. Bloco K — regressão completa da cobrança

Este bloco é **gate de produto**, não só de unit test.

## K1. Offline

Rodar todas as suítes de portal/cobrança relevantes e a regressão global.

No mínimo localizar e incluir as suítes existentes que cobrem:

```text
portal-worker base
worker hardening
Allianz
HDI
Tokio
Yelum
MAPFRE
Zurich
cobrança alcança todas as seguradoras
billing_collection
vidros/adaptive
```

Não hardcodar uma lista incompleta se o repo tiver mais testes na data da execução: descobrir por path/marker e registrar o conjunto realmente rodado.

## K2. Live read-only — uma vez, no gate final

Objetivo: provar que a infraestrutura transversal não matou os portais reais.

Sem enviar WhatsApp.

Executar, onde houver credencial autorizada, um canário **somente leitura** representando classes diferentes:

```text
Allianz  → controle histórico
HDI      → anti-bot/headless novo
Yelum ou Tokio → SPA/API
MAPFRE   → multiempresa/account_label, se a conta estiver disponível
Zurich   → journey nova já registrada
```

Se rodar todos os suportados for operacionalmente barato, rodar todos.

Para cobrança:

```text
coletar
validar item
validar PDF quando existir
NÃO chamar entrega ao segurado
```

### Critério de PDF

Quando o portal disser que existe documento e o download for bem-sucedido:

```text
começa com %PDF
size > 0
path privado existe
```

Não exigir que todos os itens tenham boleto; regra de seguradora pode legitimamente não emitir.

## K3. Cobrança não pode mudar de semântica

Comparar antes/depois:

```text
mesma entrada de fixture
→ mesma classificação de vencimento
→ mesma decisão enviar/reter
→ mesmo anti-duplicate
```

## Gate K

Se qualquer journey de cobrança regredir, **a SPEC não fecha**, mesmo que discovery/vision estejam perfeitos.

---

# 18. Bloco L — rollout controlado

## L1. Deploy inicial

Deploy do `portal-worker` com:

```text
PORTAL_DISCOVERY_MODE=false
PORTAL_VISION_ENABLED=false
PORTAL_PROFILER_ENABLED=true
```

O primeiro deploy tem comportamento funcional equivalente ao anterior; adiciona segurança/profiling passivo.

## L2. Canário

Ordem:

```text
1. health/build SHA
2. fixture/offline
3. job read-only controlado
4. cobrança read-only
5. vidros até uma fronteira NÃO material, se houver caso autorizado
```

## L3. Discovery

Só depois:

```text
PORTAL_DISCOVERY_MODE=true
```

em execução técnica/caso controlado.

Provar:

```text
capturou evidência útil
não efetuou ação material
não vazou segredo
```

## L4. Visão

Ativar `PORTAL_VISION_ENABLED=true` somente depois de:

- provider configurado;
- teste de privacidade;
- replay de screenshot;
- mutation M10/M11 verde.

No início, visão deve ser usada no portal de vidros/adaptive, **não obrigatoriamente nas journeys de cobrança** que já são determinísticas e estáveis.

---

# 19. Rollback

Como não há migration prevista, rollback deve ser simples.

## Rollback imediato por flag

```text
PORTAL_DISCOVERY_MODE=false
PORTAL_VISION_ENABLED=false
```

Profiler pode permanecer se provado passivo; se houver problema:

```text
PORTAL_PROFILER_ENABLED=false
```

## Rollback de imagem

Reimplantar o build anterior do `portal-worker`.

## Regra

Não apagar `evidence` novo para “voltar ao passado”. É dado de auditoria; o código antigo simplesmente ignora chaves extras.

---

# 20. Arquivos esperados

## Novos

```text
backend/portal_worker/runtime.py
backend/portal_worker/guardrails.py
backend/portal_worker/profiler.py
backend/portal_worker/perception.py
backend/tests/test_spec073_runtime.py
backend/tests/test_spec073_guardrails.py
backend/tests/test_spec073_profiler.py
backend/tests/test_spec073_perception.py
backend/tests/test_spec073_zero_regressao_portais.py
backend/tests/test_spec073_portal_worker_mutations.py
```

## Alterados — provável

```text
backend/portal_worker/worker.py
backend/portal_worker/adaptive.py
backend/portal_worker/main.py
backend/portal_worker/journeys/__init__.py   # somente se necessário para compatibilidade/teste; não criar segundo registry
```

## Alterados — somente se o bloco realmente exigir

```text
backend/portal_worker/journeys/vidros_lanternas.py
```

As journeys de cobrança **não devem ser editadas em massa** para “adotar runtime”. Elas só mudam se um teste provar necessidade concreta.

---

# 21. Arquivos que NÃO devem ser reescritos nesta SPEC

Salvo bug diretamente causado pela infraestrutura desta SPEC:

```text
backend/portal_worker/journeys/allianz_corretor.py
backend/portal_worker/journeys/hdi_corretor.py
backend/portal_worker/journeys/tokio_corretor.py
backend/portal_worker/journeys/yelum_corretor.py
backend/portal_worker/journeys/mapfre_corretor.py
backend/portal_worker/journeys/zurich_corretor.py
backend/app/services/billing_collection.py
```

A cobrança é controle de regressão, não território para refatoração cosmética.

---

# 22. Critérios de aceite finais

A SPEC-073 só fecha quando **TODOS** forem verdadeiros:

## Arquitetura

- [ ] continua existindo um único `portal-worker`;
- [ ] continua existindo um único registry de journeys;
- [ ] runtime é aditivo e journeys antigas funcionam sem conhecê-lo;
- [ ] nenhuma nova tabela/motor/fila foi criada sem necessidade medida.

## Segurança transacional

- [ ] toda ação material que usar o novo runtime passa pelo guard;
- [ ] checkpoint `armed` é persistido antes do efeito;
- [ ] resultado incerto nunca causa retry cego;
- [ ] stale read-only continua recuperável;
- [ ] account/company/portal mismatch falha antes de usar credencial.

## Discovery/Profiler

- [ ] `PORTAL_DISCOVERY_MODE` existe e nasce false;
- [ ] discovery não permite efeito material;
- [ ] Network + DOM + screenshot seletivo + trace sanitizado funcionam;
- [ ] Authorization/Cookie/PII não aparecem no artefato;
- [ ] profiler gera candidatos de API sem automaticamente executá-los.

## Percepção

- [ ] current DOM adaptive continua funcionando;
- [ ] existe visão multimodal REAL como fallback opcional;
- [ ] visão usa o mesmo action schema;
- [ ] ação de visão passa por validador e guard;
- [ ] provider indisponível degrada para HITL, não crash;
- [ ] nenhuma opção crítica é escolhida por posição.

## Cobrança

- [ ] Allianz continua funcionando;
- [ ] HDI continua funcionando;
- [ ] Tokio continua funcionando;
- [ ] Yelum continua funcionando;
- [ ] MAPFRE continua registrada e seus testes continuam verdes;
- [ ] Zurich continua funcionando;
- [ ] `portais_com_cobranca()` continua derivado do registry;
- [ ] `billing_collection.py` mantém as regras atuais;
- [ ] nenhum WhatsApp real foi enviado durante o gate técnico.

## Operação

- [ ] `/health` expõe flags não sensíveis;
- [ ] build SHA do deploy é verificável;
- [ ] flags de rollback funcionam;
- [ ] mutation matrix verde;
- [ ] relatório final registra testes executados, canários e qualquer vermelho preexistente.

---

# 23. O que esta SPEC deixa deliberadamente para a SPEC-074

Esta fundação NÃO tenta fechar o domínio do portal de vidros no mesmo bloco.

A SPEC-074 deverá usar este runtime para implementar, sem adivinhação:

```text
Maxpar/AutoGlass API-first
Yelum + Porto como dois casos medidos
TipoAtendimento 1/2
coverage_absent como estado de negócio
catálogo real por apólice/sessão
Question Engine dinâmico
/questionarios/perguntas até 204
fronteira de 80%
protocolo interno x CodigoAtendimento final
franquia
LinkVistoriaMobile/vistoria.mobi
consultar atendimento
loja x domicílio
```

E deixar um bloco explicitamente marcado `PENDENTE DE EVIDÊNCIA DA REGINA` para:

```text
qual request cria/define CodigoAtendimento final
fluxo real pós-criação
loja/domicílio
dia/hora
PermiteVistoriaMobile
LinkVistoriaMobile final
comparação link automático x link que Regina copia
```

Essa pendência **não bloqueia** escrever nem executar o restante da SPEC-074.

---

# 24. Sequência reta de execução para o Claude Code

O Claude deve executar exatamente nesta ordem:

```text
0. preflight Git + ler autoridades
1. congelar baseline de testes e registry
2. implementar runtime aditivo
3. implementar guard + checkpoint
4. consertar stale recovery transacional
5. implementar discovery mode
6. implementar profiler sanitizado
7. implementar perception interface
8. adicionar visão multimodal real opcional
9. remover/chancelar force-choose crítico
10. implementar unknown-screen escalation
11. reforçar redaction/evidence/health
12. rodar mutation matrix
13. rodar regressão completa portal/cobrança
14. canário live read-only, sem WhatsApp
15. deploy portal-worker com discovery/vision off
16. provar build SHA + health
17. habilitar discovery em caso técnico e provar zero side effect
18. registrar relatório final e atualizar docs
```

Não abrir frente paralela de UI, marketing, RAG, WhatsApp, Auxiliares ou billing enquanto estiver executando esta SPEC.

---

# 25. Relatório final obrigatório

Ao terminar, produzir relatório contendo:

```text
commit inicial
commit final
branch
arquivos alterados
nenhuma/qual migration
serviço deployado
build SHA observado
suítes e quantidades
mutações M01-M22
resultado dos canários por portal
zero regressão da cobrança
flags finais do ambiente
qualquer pendência real
```

Separar:

```text
📊 MEDIDO
💭 INFERIDO/RECOMENDADO
```

Não declarar “100% robusto” só porque os testes passaram. Declarar exatamente as classes que foram provadas e as que permanecem dependentes da SPEC-074/Regina.

---

# 26. Definição de sucesso

A SPEC terá alcançado seu objetivo quando o Portal Worker deixar de ser apenas “um conjunto de journeys que funcionam” e passar a ser uma **infraestrutura operacional resiliente**:

> quando o caminho conhecido funciona, ele é rápido e determinístico; quando a API está disponível, usa dados estruturados; quando o DOM muda, reconhece; quando o DOM não basta, enxerga; quando não sabe, para com evidência; e quando uma ação pode criar algo irreversível, jamais repete sem saber o que aconteceu.

E tudo isso deve ser verdadeiro **sem quebrar um único boleto que já conseguimos coletar hoje**.

