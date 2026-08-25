# SPEC-087 — ROUTE SELF-HEALING LOOP
## A rota percebe que o mundo mudou, propõe a correção, prova que ficou melhor e só então pode ser publicada

**Produto:** AutoBrokers Intelligence OS  
**Status:** CANDIDATE SPEC — pronta para aquecimento AAA; ainda não executada  
**Data da redação:** 25/08/2026  
**Baseline observado durante a redação:** `main` em `8b49fdb337a6c37eb2ad181f5bad544a55dc0827`  
**Branch sugerida quando for executar:** `feat/spec087-route-self-healing-loop`  
**Absorve e supersede:** `SPEC-080-a-tela-que-o-atlas-viu-vira-passo-proposto.md`  
**Depende conceitualmente de:** SPEC-038, SPEC-050, SPEC-063, SPEC-077, SPEC-083, SPEC-084, SPEC-084.1, SPEC-084.2, SPEC-085 e SPEC-089 Candidate  
**Runtime preservado:** motor de corredor atual + Atlas + Sentinela + Simulador + Work OS + Smith; nenhum runtime paralelo  
**Primeiro escopo executável:** rotas conversacionais de seguradoras (WhatsApp/URA)  
**Contrato projetado para reuso:** portais/browser routes, APIs descobertas, outros canais  
**Research Pack:** `SPEC-087-route-self-healing-loop-RESEARCH-PACK.md`

---

# 0. RESULTADO EM UMA FRASE

> **Quando uma seguradora mudar uma tela, menu, pergunta, formulário ou contrato de rota, o AutoBrokers deve perceber a mudança, juntar a prova, propor um patch mínimo, testar esse patch contra o passado e contra os contratos atuais, medir antes/depois com a régua AAA, pedir aprovação humana autorizada, publicar em canário e desfazer sozinho se a mudança piorar a operação.**

A 087 transforma isto:

```text
SEGURADORA MUDA
↓
CORREDOR NÃO SABE
↓
ATENDIMENTO TRAVA
↓
ALGUÉM INVESTIGA
↓
ALTERA CÓDIGO
↓
TESTA
↓
DEPLOY
```

nisto:

```text
SEGURADORA MUDA
↓
OBSERVA
↓
DETECTA DRIFT
↓
EVIDENCE PACK
↓
PATCH CANDIDATE
↓
SANDBOX / REPLAY
↓
ASSESSMENT BEFORE/AFTER
↓
HUMANO AUTORIZADO
↓
CANARY
↓
OBSERVA
├─ MELHOROU → RELEASE
└─ REGREDIU → ROLLBACK AUTOMÁTICO
```

---

# 0.1 AS QUATRO DECISÕES DO FOUNDER JÁ APROVADAS

Entram como invariantes desta SPEC.

## D1 — Auto-propor e auto-testar: SIM. Auto-publicar: NÃO.

O sistema pode automaticamente:

- detectar;
- investigar;
- agrupar evidência;
- produzir hipótese;
- produzir patch candidato;
- executar replay;
- executar Simulador;
- executar a régua;
- executar mutation;
- produzir assessment;
- preparar canário.

O sistema NÃO pode tornar o patch runtime-active sem uma aprovação humana autorizada.

## D2 — Não hardcodar `Founder`

A permissão de publicação é uma capability:

```text
route_publish
```

Inicialmente pode estar apenas com Founder/Admin.

Depois pode ser delegada a um gestor/operador especializado.

## D3 — Melhoria incremental segura é publicável

Uma rota inteira NÃO precisa virar `AAA_READY` para receber uma melhoria.

Exemplo:

```text
before = 72
after  = 81
```

O patch pode ser aprovado se:

- corrige a unidade-alvo;
- não cria regressão;
- não derruba hard gate;
- não piora vizinhos;
- passa os gates específicos da operação;
- a evidência é suficiente;
- humano autorizado aprova.

A rota continua `NOT_READY` se ainda houver outros buracos.

## D4 — Rollback automático por regressão grave: SIM.

Promoção precisa de humano.

Rollback de um patch recém-publicado pode ser automático quando um circuit breaker objetivo prova regressão.

Rollback não é “a IA decidiu outra rota”.

É:

> **retornar para uma release humana anteriormente aprovada quando a nova release violou um gate de segurança.**

---

# 0.2 O QUE ESTA SPEC ABSORVE DA SPEC-080

A SPEC-080 foi escrita em 18/08/2026, nunca executada, e o controle de SPECs já a declara explicitamente como base da 087.

A tese que permanece:

> **o Atlas já viu uma tela que o corredor ignora; transformar esse conhecimento observado em proposta governada.**

A 080 já havia identificado quatro falhas estruturais importantes:

1. drift estrutural nunca chegava ao Alfaiate;
2. anchor gerada podia não casar com a normalização do motor;
3. writer/reader usavam namespaces diferentes de playbook;
4. `playbook_overlays` só sabia representar `noop`, não um passo real de resposta.

A 087 preserva o problema, mas muda a solução.

---

# 0.3 O QUE ESTA SPEC REVOGA DA SPEC-080

A 080 continha um ramo histórico de:

```text
drift cosmético
→ Alfaiate
→ Simulador
→ auto-aplica overlay
```

Isso deixa de ser permitido.

A regra única passa a ser:

```text
PROPOSTA pode ser automática.
TESTE pode ser automático.
PUBLICAÇÃO nunca é automática.
```

Até `noop` é uma mudança de comportamento do runtime.

Portanto:

> **nenhum `playbook_overlay.status='active'`, patch, release, mutation de rota ou equivalente pode nascer ativo por decisão automática.**

---

# 1. POR QUE ESTA SPEC EXISTE AGORA

## 1.1 A prova concreta

A SPEC-080 mediu um caso em que uma tela de assistência da Allianz já havia sido observada pelo Atlas:

```text
8 vezes
4 sessões
21 dias
```

e o corredor ainda não sabia responder.

A tela específica já foi corrigida manualmente.

O defeito de classe permaneceu:

```text
ATLAS SABE
≠
CORREDOR SABE
```

## 1.2 O problema cresceu depois da 080

Desde então, as SPECs 083–085 mudaram o que significa “patch seguro”.

Aprendemos que:

- teste que só casa regex pode estar verde enquanto o motor falha;
- medir pode alterar fonte se o teste for ruim;
- a régua pode premiar um buraco;
- 19 rotas que respondiam 100% das telas não passavam o contrato da Tool;
- formulários nativos podiam ficar fora do replay;
- mutação real é necessária;
- travamento precisa virar estado durável e visível;
- a rota de referência precisa ser medida pelo resultado, não por strings.

Logo:

> **Simulador verde sozinho não dá direito de publicar.**

---

# 2. O PROBLEMA DE PRODUTO

Uma seguradora pode mudar:

```text
texto
opção
ordem
menu
pergunta
campo
formulário
rótulo
fluxo
finalização
contrato de API
endpoint
estrutura de DOM
requisição de rede
```

Essas mudanças têm riscos diferentes.

Se tratarmos tudo como “drift”:

- cosmético pode gerar ruído;
- estrutural pode receber patch fraco;
- mudança de finalização pode abrir chamado errado;
- API nova pode ser ignorada;
- nome variável pode virar falsa rota nova;
- uma pergunta desconhecida pode virar constante chutada.

A 087 precisa transformar:

```text
DIFERENÇA OBSERVADA
```

em:

```text
HIPÓTESE DE MUDANÇA
+
PROVA
+
PATCH MÍNIMO
+
TESTE
+
GOVERNANÇA
```

---

# 3. PRINCÍPIO CENTRAL — SELF-HEALING NÃO É SELF-PUBLISHING

Definição AutoBrokers:

> **Self-healing é a capacidade de detectar, diagnosticar, propor, provar, aplicar com autorização e reverter com segurança.**

Não significa:

> “a IA modifica produção sozinha.”

O loop completo é:

```text
AUTOMÁTICO
detectar
diagnosticar
propor
testar
avaliar

HUMANO
aprovar

AUTOMÁTICO
publicar canário
observar
rollback se necessário
```

---

# 4. ESCOPO V1 — ROUTE KINDS

A 087 cria um contrato genérico, mas só liga o primeiro adaptador.

## 4.1 `conversation_route` — EXECUTÁVEL nesta SPEC

WhatsApp/URA:

- `corridor_playbooks.py`;
- Atlas observed maps;
- `route_drift`;
- `route_sentinel`;
- Simulador;
- motor real offline;
- corpus/replay;
- Tool Contract;
- SPEC-089 RouteAssessment.

## 4.2 `browser_route` — contrato preparado, NÃO auto-ativado

Portais:

- Browser Intelligence Lab;
- profiler;
- fixture/replay;
- CDP/HAR;
- portal capabilities.

A 087 pode definir interfaces comuns e provar uma fixture offline.

Não deve reescrever Portal Worker nem ligar browser self-modification.

Uma SPEC posterior poderá ativar o adapter com a mesma governança.

## 4.3 `api_route` — descoberta apenas

Quando tráfego mostra API estável:

- evidence pode incluir endpoint/schema;
- patch pode recomendar “migrar browser step para API capability”.

A adoção da API é outra aprovação/capability.

---

# 5. AUTORIDADES

| Responsabilidade | Autoridade |
|---|---|
| mapa observado | Atlas / observed events / ura maps |
| corredor runtime | `corridor_playbooks.py` + motor |
| diferenças | Sentinela / diff canônico |
| replay | corpus + Simulador + ferramentas 083/084 |
| avaliação AAA | SPEC-089 `RouteAssessment` |
| execução do patch candidate | sandbox/offline only |
| aprovação | Capability Registry / `route_publish` |
| release ativa | registry/version pointer governado |
| audit | Work Events / audit existente ou tabela dedicada mínima |
| secrets | Vault |
| deploy/runtime | mecanismos existentes |

Nenhum novo cérebro.

Nenhum segundo corredor.

---

# 6. O OBJETO MAIS IMPORTANTE — ROUTE PATCH CANDIDATE

## 6.1 Definição

> **Um Route Patch Candidate é uma proposta versionada e imutável de modificar uma rota, acompanhada da evidência que a originou e das provas que dizem o que melhora e o que pode piorar.**

Ele não altera produção.

## 6.2 Schema conceitual

```json
{
  "candidate_id": "...",
  "candidate_version": 1,
  "company_scope": "global|tenant",
  "route_kind": "conversation_route",
  "route_ref": "allianz-residencial-whatsapp@v1",
  "subservice_scope": ["eletricista"],
  "baseline_release_id": "...",
  "baseline_route_fingerprint": "...",

  "drift": {
    "type": "MENU_STRUCTURE",
    "signature": "...",
    "first_seen_at": "...",
    "last_seen_at": "...",
    "occurrences": 8,
    "sessions": 4,
    "companies": 1,
    "confidence": 0.98
  },

  "evidence_pack_ref": "...",

  "patch": {
    "operation": "ADD_STEP",
    "target": "...",
    "anchor": "...",
    "reply_strategy": "...",
    "slot": null,
    "guards": []
  },

  "assessment_before_ref": "...",
  "assessment_after_ref": "...",

  "test_manifest_ref": "...",
  "status": "TESTED_AWAITING_APPROVAL"
}
```

## 6.3 Imutabilidade

Depois que um candidate entra em `TESTED_AWAITING_APPROVAL`:

- não editar o payload;
- correção gera nova candidate version;
- approval referencia fingerprint exato.

Aprovação não é cheque em branco.

---

# 7. EVIDENCE PACK

## 7.1 Perguntas que precisa responder

Toda proposta deve mostrar:

```text
O QUE mudou?
ONDE?
QUANDO apareceu?
QUANTAS vezes?
EM QUANTAS sessões?
EM QUANTAS corretoras?
QUAL era a rota baseline?
QUAL comportamento atual?
QUAL comportamento observado funcionou?
QUAL é a fonte da resposta proposta?
QUAL é o risco de publicar?
```

## 7.2 Fontes possíveis

### Conversational route

- observed events;
- observed sessions;
- active Atlas map;
- prior Atlas map;
- successful real transcript;
- Espelho;
- Work Run;
- work events;
- current playbook;
- current route assessment;
- nearest working sibling route;
- human reply that succeeded;
- insurer message fingerprint.

### Browser route

- HAR;
- CDP network events;
- screenshots;
- DOM dump;
- console errors;
- response schemas;
- existing portal fixture;
- provider evidence.

## 7.3 Evidence hierarchy

Preferência:

```text
1. resultado real confirmado
2. múltiplas sessões consistentes
3. uma sessão completa
4. mapa observado
5. sibling route com mesmo contrato provado
6. inferência
```

Patch não pode transformar nível 6 em “fato”.

---

# 8. NORMALIZAÇÃO E FINGERPRINT

A 080 já provou que fingerprint ingênua do texto inteiro superconta telas.

Criar `RouteObservationFingerprint` com duas camadas.

## 8.1 Content fingerprint

Normaliza:

- whitespace;
- markdown decorativo;
- acento apenas quando contrato do motor faz isso;
- nomes/telefones/protocolos/datas;
- ids/session refs;
- valores reconhecidamente variáveis.

## 8.2 Structural fingerprint

Representa:

```text
kind
option count
normalized labels
input fields
action family
relative position
neighbor fingerprints
```

Assim:

```text
“Olá João”
“Olá Maria”
```

não são duas rotas.

## 8.3 Collision control

Mutation/teste deve provar que:

- variação cosmética colapsa;
- opção semanticamente diferente NÃO colapsa.

---

# 9. DRIFT TAXONOMY

Toda diferença recebe um tipo.

```text
COSMETIC_TEXT
INFORMATIONAL_SCREEN
MENU_LABEL
MENU_STRUCTURE
QUESTION
FIELD_REQUIRED
FIELD_OPTION_SET
FLOW_STRUCTURE
FORM_NATIVE
FINALIZATION
HANDOFF_BEHAVIOR
API_NETWORK
AUTH_SECURITY
UNKNOWN
```

## 9.1 Risk class

Mapear para:

```text
LOW
MEDIUM
HIGH
CRITICAL
```

Exemplos:

### LOW
- aviso informativo;
- texto não operacional.

### MEDIUM
- label/menu com resposta já provada.

### HIGH
- coleta de slot;
- galho novo;
- handoff;
- formulário.

### CRITICAL
- confirmação/finalização;
- cancelamento;
- cobertura;
- pagamento;
- dados de segurança;
- ação irreversível.

---

# 10. DETECTION ENGINE

## 10.1 Não criar outro observador

Reusar:

- Atlas;
- Sentinela;
- observed events;
- existing profiler quando aplicável.

## 10.2 Sentinela deixa de “aplicar”

A função do Sentinela passa a ser:

```text
COMPARE
↓
DEDUPE
↓
CLASSIFY
↓
CREATE/UPDATE DRIFT
↓
REQUEST CANDIDATE
```

Não:

```text
APPLY
```

## 10.3 `auto_applied`

Campos históricos podem permanecer por compatibilidade, mas:

```text
novo caminho nunca escreve true automaticamente.
```

---

# 11. DEDUPE DE DRIFT

Um mesmo problema não pode gerar 50 candidates.

Key conceitual:

```text
route_ref
+
structural_fingerprint
+
baseline_release_id
```

Quando o mesmo drift aparece:

- incrementa evidence;
- atualiza last_seen;
- adiciona sessão/corretora;
- fortalece confidence.

Não cria nova candidate se candidate aberta já cobre a mudança.

---

# 12. CANDIDATE GENERATOR

## 12.1 Deterministic-first

Antes de LLM:

- identificar step vizinho;
- identificar successful response;
- identificar slot;
- identificar route family;
- identificar equivalent sibling;
- identificar existing pattern.

## 12.2 LLM pode propor estrutura?

SIM, como candidato.

Nunca como verdade.

A LLM recebe:

- evidence pack redigido;
- contrato de patch;
- allowed operations;
- prohibited operations;
- sibling examples;
- route syntax.

Saída é validada por schema.

## 12.3 Candidate source

Registrar:

```text
deterministic
human_observed
llm_proposed
sibling_derived
api_discovered
```

---

# 13. PATCH OPERATIONS — VOCABULÁRIO FECHADO

V1:

```text
ADD_NOOP
ADD_STEP
MODIFY_ANCHOR
ADD_ANCHOR_VARIANT
ADD_OPTION_MAPPING
ADD_SLOT_CAPTURE
MODIFY_REPLY_STRATEGY
ADD_HANDOFF_TRIGGER
ADD_FINALIZE_GUARD
ADD_NATIVE_FLOW_MAPPING
DISABLE_STEP
REMOVE_STEP
```

`REMOVE_STEP` e `DISABLE_STEP` têm risco maior.

`ADD_FINALIZE_GUARD` pode ser melhoria segura, mas continua approval.

Operação fora do vocabulário:

```text
MANUAL_ENGINEERING
```

---

# 14. SLOT VS CONSTANT — REGRA HERDADA DA 080

Na dúvida entre:

```text
CONSTANT
```

e:

```text
SLOT
```

preferir:

```text
SLOT / HUMAN / SEM_CHUTE
```

até existir evidência.

Não inferir:

- local seguro;
- cobertura;
- aceite;
- idade;
- quantidade;
- confirmação;
- motivo;
- dados que mudam outcome.

---

# 15. PATCH SURFACE — NÃO CASAR A 087 COM `playbook_overlays`

A 080 assumia `playbook_overlays` como principal mecanismo.

O baseline atual ainda mostra que:

- tabela histórica foi desenhada para `noop`;
- writer e reader já tiveram namespace incompatível;
- anchor normalization já divergiu.

A 087 NÃO decreta antes do warm-up que overlays serão a release mechanism.

O executor deve comparar:

## Opção A — evoluir `playbook_overlays`

Bom se:

- runtime já lê;
- pode representar todas as operações necessárias;
- versioning/approval cabe sem segunda autoridade.

## Opção B — Route Release Registry

Patch compilado gera:

```text
release artifact
```

que o motor carrega em camada governada.

## Opção C — source patch versionado

Candidate aprovado gera alteração em source + tests + deploy.

Mais lento, mas mais auditável.

### Regra

Escolher a menor superfície que:

- é realmente lida pelo motor;
- possui version/fingerprint;
- suporta rollback atômico;
- não cria um corredor paralelo.

---

# 16. COMPILE STEP — CANDIDATE NÃO É RUNTIME FORMAT

Separar:

```text
RoutePatchCandidate
```

de:

```text
CompiledRoutePatch
```

O candidate é linguagem de governança.

O compiler traduz para a forma do runtime.

Assim a governança não fica amarrada para sempre a um dict Python/overlay.

---

# 17. SANDBOX

Todo candidate passa por sandbox sem tocar produção.

```text
BASELINE
↓
COMPILE CANDIDATE
↓
EPHEMERAL ROUTE VIEW
↓
TEST BATTERY
```

Não gravar active patch para “testar e depois apagar”.

Isso reabre o furo da SPEC-050.

---

# 18. TEST BATTERY — CAMADAS

## T0 — Schema / static

- candidate válido;
- operation permitida;
- target existe;
- anchor compila;
- nenhuma PII;
- namespace válido;
- route fingerprint confere.

## T1 — Target replay

As sessões que originaram o drift.

## T2 — Route corpus replay

Corpus inteiro da rota.

## T3 — Neighbor replay

Rotas/subservices que compartilham:

- playbook;
- anchor;
- slot;
- native flow;
- finalize;
- helper.

## T4 — Motor real offline

Teste chama o motor.

Nunca apenas regex/helper.

## T5 — Tool/Runtime Contract

A regra da 084.2.

O dado que o corredor exige precisa realmente chegar pelo contrato executável.

## T6 — Simulator

Mantém valor, mas não é gate único.

## T7 — Mutations

Patch precisa provar que o teste consegue reprová-lo.

## T8 — Security/PII/Tenant

Sem vazamento.

## T9 — RouteAssessment SPEC-089

Before/after.

---

# 19. INTEGRAÇÃO CANÔNICA COM SPEC-089

## 19.1 Assessment BEFORE

Rodar contra:

```text
baseline release
rubric version X
route fingerprint A
```

Guardar JSON completo.

## 19.2 Assessment AFTER

Rodar contra:

```text
ephemeral patched release
MESMA rubric version X
candidate fingerprint B
```

## 19.3 Não comparar score de rubricas diferentes

Se rubric mudou durante a avaliação:

```text
ASSESSMENT_INVALID
```

reexecutar before e after na mesma versão.

## 19.4 Certificação

SPEC-089 separa:

```text
score 0–100
```

de:

```text
AAA_READY
AAA_VALIDATED
```

A 087 preserva.

---

# 20. PATCH ELIGIBILITY — MELHORIA INCREMENTAL

Definir:

```text
PATCH_ELIGIBLE
```

se TODOS:

1. target defect reproduz BEFORE;
2. target defect some AFTER;
3. score after >= score before;
4. nenhum hard gate passa de PASS para FAIL/UNKNOWN;
5. nenhum blocker crítico novo;
6. neighbor regression = zero;
7. Tool/Runtime Contract não regride;
8. mutation específica consegue matar o patch;
9. evidence satisfaz piso do risk class;
10. candidate compila deterministicamente;
11. approval ainda não ocorreu.

`PATCH_ELIGIBLE` NÃO significa:

```text
AAA_READY
```

---

# 21. CRITICAL NON-COMPENSATION

Exemplo proibido:

```text
before 72
after  91

mas finalize guard FAIL
```

Resultado:

```text
NOT ELIGIBLE
```

Score não compensa gate.

Também:

```text
99 + UNKNOWN crítico = NOT ELIGIBLE
```

---

# 22. EVIDENCE FLOOR POR RISCO

Proposta inicial para warm-up/refutação.

## LOW

Pode usar:

- múltiplas observações;
- determinístico;
- no operational choice.

## MEDIUM

Exigir:

- ao menos uma sequência real coerente;
- ou sibling equivalence com contrato provado;
- replay completo.

## HIGH

Exigir:

- evidência real da resposta/efeito;
- ou revisão humana explícita da semântica;
- mutation;
- neighbors.

## CRITICAL

Nunca publicar apenas por inferência.

Exigir:

- evidência real confirmada;
- aprovação autorizada;
- canário extremamente limitado;
- rollback armado.

---

# 23. APROVAÇÃO — CAPABILITY `route_publish`

## 23.1 Actor

Usuário autorizado por tenant/global role.

## 23.2 Approval payload

Mostrar:

```text
Route
Drift
Before
After
O que muda
Por que
Fonte
Risk
Hard gates
Neighbor tests
Mutation
Canary plan
Rollback plan
```

## 23.3 Approval fingerprint

Approval referencia:

```text
candidate_id
candidate_version
compiled_patch_fingerprint
assessment_after_fingerprint
baseline_release_id
```

Mudou qualquer um:

```text
approval inválida
```

---

# 24. UX DE APROVAÇÃO — DOIS CLIQUES, MAS NÃO CEGA

Card mínimo:

```text
ALLIANZ · RESIDENCIAL · ELETRICISTA
Mudança detectada 8x em 4 sessões

PROBLEMA
A seguradora passou a perguntar:
“...”

ANTES
rota 72 · target FAIL

PATCH
quando aparecer X → responder Y
fonte: 3 respostas humanas bem-sucedidas

DEPOIS
rota 81 · target PASS
hard gates: todos preservados
vizinhos: 17/17 sem regressão
mutation: PASS

[ABRIR PROVA]
[APROVAR CANÁRIO]
[REJEITAR]
```

Não despejar centenas de telas.

---

# 25. REJEIÇÃO É DADO

Ao rejeitar:

```text
reason_code
comment
reviewer
```

Reason codes:

```text
WRONG_SEMANTICS
INSUFFICIENT_EVIDENCE
WRONG_SCOPE
TOO_RISKY
DUPLICATE
ROUTE_CHANGED_AGAIN
MANUAL_FIX_PREFERRED
OTHER
```

Isso alimenta melhorias futuras do candidate generator.

---

# 26. RELEASE MODEL

Toda promoção cria uma release.

```text
route_release_id
route_ref
parent_release_id
candidate_id
compiled_patch_ref
route_fingerprint
rubric_version
assessment_ref
approved_by
approved_at
release_state
```

States:

```text
APPROVED
CANARY
ACTIVE
ROLLED_BACK
SUPERSEDED
REJECTED
```

---

# 27. PONTE COM O RUNTIME

O runtime lê apenas:

```text
ACTIVE release
```

ou:

```text
CANARY release para scope permitido
```

Candidate nunca é lido.

Rejected nunca é lido.

Tested nunca é lido.

Isso implementa:

> proposta não aprovada é invisível ao motor por construção.

---

# 28. CANARY

## 28.1 Escopo inicial

Por:

```text
company
route
subservice
percentage / allowlist
```

Começar com allowlist explícita.

## 28.2 Não canariar em ação irreversível sem segurança

Para finalização crítica:

- pode observar match em shadow;
- pode executar até pre-finalize;
- side effect real segue gates superiores.

## 28.3 Canary window

Não definir duração universal na Candidate Spec.

A unidade correta pode ser:

```text
N execuções elegíveis
+
T mínimo
```

Warm-up mede volume.

---

# 29. SHADOW E SHADOW DIFFERENTIAL

Antes de enviar comportamento novo ao provider:

```text
BASELINE decision
vs
PATCHED decision
```

em paralelo lógico.

Guardar:

```text
same
improved
diverged
dangerous_divergence
```

Sem duplicar side effect.

Esse shadow pode ser usado nos primeiros eventos antes de promover CANARY para ACTIVE.

---

# 30. CIRCUIT BREAKER / ROLLBACK AUTOMÁTICO

## 30.1 Regra

Release nova deve carregar:

```text
rollback_to = parent_release_id
```

## 30.2 Triggers duros

Rollback automático se houver prova de:

```text
hard gate violation
tool contract regression
new needs_human spike acima de threshold seguro
new unanswered screen na unidade corrigida
wrong-finalize / forbidden side effect
tenant leak
PII violation
duplicate effect
fatal error introduced
```

Thresholds quantitativos não são inventados aqui; warm-up mede baseline.

## 30.3 Triggers suaves

Não rollback automático apenas por:

```text
score caiu 1 ponto
latência pequena
uma divergência explicável
```

Abre investigação.

## 30.4 Rollback action

Transação:

```text
new release → ROLLED_BACK
parent       → ACTIVE
```

Registrar:

```text
reason
evidence
metric
timestamp
```

Notificar `route_publish` operators.

---

# 31. POR QUE ROLLBACK PODE SER AUTOMÁTICO

A mudança nova já foi aprovada por humano.

A release anterior também.

Rollback não inventa uma terceira resposta.

Apenas volta ao último estado aprovado.

Esse é o limite de autonomia desta SPEC.

---

# 32. ROUTE DRIFT E ACTIVE MAP

Não confundir:

```text
Atlas active map
```

com:

```text
active route release
```

Atlas responde:

> **o que a seguradora mostrou.**

Route release responde:

> **como o AutoBrokers deve agir.**

Continuam objetos diferentes.

---

# 33. MAP PROMOTION

A 080 registrou conflito histórico sobre promoção de mapas.

A 087 não resolve isso por efeito colateral.

Warm-up deve identificar:

- quem promove `ura_maps.status=active`;
- qual gate atual;
- se active map é observado/consenso ou operacional.

Route candidate pode usar qualquer mapa com provenance.

Não precisa promover mapa só para produzir candidate.

---

# 34. ROUTE DRIFT CLASSIFIER — NÃO APENAS COSMETIC/STRUCTURAL

O atual `classify_severity` possui basicamente:

```text
cosmetic
structural
```

É pouco.

A 087 substitui/expande por taxonomy §9.

Compatibilidade pode manter severity agregada:

```text
cosmetic
structural
```

como derivada, não como única informação.

---

# 35. ALFAIATE — NOVO PAPEL

“Alfaiate” deixa de significar:

> componente que altera rota.

Passa a significar:

> **Route Patch Proposer/Compiler especializado.**

Pode manter o nome histórico internamente.

Mas sua autoridade termina em:

```text
Candidate + Compiled Candidate
```

Nunca ACTIVE.

---

# 36. BROWSER INTELLIGENCE — O QUE ABSORVER DA SPEC-077 E DO UPSTREAM

## 36.1 Browser Trace pattern

Browserbase `browser-trace` ensina um padrão valioso:

```text
automation client
+
read-only CDP observer
```

capturando:

- network;
- console;
- DOM;
- screenshots;
- page lifecycle.

AutoBrokers já decidiu na 077 não depender cegamente do `browse` CLI no runtime.

A 087 absorve o PADRÃO:

```text
passive trace
```

não necessariamente a implementação upstream.

## 36.2 Browser-to-API

Pattern:

```text
TRACE/HAR
↓
pair requests/responses
↓
template URLs
↓
infer schemas
↓
OpenAPI candidate
↓
coverage report
```

Uso na 087:

se browser route drift mostrar que operação real é API-backed:

criar evidence:

```text
api_candidate
confidence
coverage gaps
```

Não migrar automaticamente.

## 36.3 AutoBrowse

Pattern:

```text
task
↓
run
↓
trace
↓
improve strategy
↓
run again
↓
graduate after repeated reliability
```

A 087 absorve apenas:

> **uma mudança não se prova pelo mesmo run que a inspirou.**

Candidate deve vencer:

- origin session;
- route corpus;
- neighbor corpus;
- mutation/adversarial cases.

---

# 37. STAGEHAND v4 — O QUE APROVEITAR

Stagehand v4 possui self-healing actions.

Isso é útil para:

- browser adapter resiliente a seletor/DOM;
- comparação entre deterministic locator e semantic action;
- candidate evidence.

Não usar Stagehand self-healing como autoridade de publicação.

Se Stagehand conseguiu “achar outro botão”, isso é:

```text
OBSERVED_RECOVERY
```

e pode virar candidate.

Não vira rota canônica sozinho.

---

# 38. ROUTE PROFILER — CONCEITO FUTURO COMUM

Contrato:

```text
RouteProfiler
  observe()
  fingerprint()
  diff()
  evidence()
```

Adapters:

```text
ConversationRouteProfiler
BrowserRouteProfiler
ApiRouteProfiler
```

Nesta SPEC:

- Conversation = implementa;
- Browser = interface + fixture offline se barato;
- API = evidence only.

---

# 39. WORK OS — CANDIDATE COMO TRABALHO

Geração/teste de candidate pode ser Work Run:

```text
workflow_key = route.self_heal.assess
```

Benefícios:

- durável;
- custo;
- timeline;
- retries;
- artifacts;
- audit.

Não criar scheduler.

O gatilho pode vir da Sentinela.

---

# 40. IDEMPOTÊNCIA

Candidate creation key:

```text
route_candidate:{route_ref}:{baseline_release}:{drift_signature}
```

Publish key:

```text
route_publish:{candidate_id}:{compiled_fingerprint}
```

Rollback key:

```text
route_rollback:{release_id}:{trigger_fingerprint}
```

Dois workers:

uma candidate.

Dois clicks:

uma release.

Dois breakers:

um rollback.

---

# 41. CONCORRÊNCIA — BASELINE MUDOU DURANTE A REVISÃO

Cenário:

```text
Candidate A
baseline release 5

outro humano publica Candidate B
route vira release 6

humano abre Candidate A e aprova
```

A deve falhar:

```text
STALE_BASELINE
```

Nunca compilar patch antigo sobre estado novo silenciosamente.

Opções:

- rebase automático só como NOVA candidate;
- ou rejeitar/reavaliar.

---

# 42. ROUTE CHANGED AGAIN

Se o insurer mudou de novo enquanto candidate aguardava:

```text
drift fingerprint atual != evidence fingerprint
```

candidate:

```text
STALE_EVIDENCE
```

Precisa reexecutar.

---

# 43. SOURCE OF TRUTH DE RESPOSTA

Para propor resposta:

ordem preferida:

```text
1. current route rule já provada em sibling idêntico
2. successful human/AI response com outcome confirmado
3. repeated observed choice
4. official provider/API response
5. approved domain rule
6. LLM hypothesis
```

Nível 6 não publica HIGH/CRITICAL sem revisão semântica.

---

# 44. NEGATIVE EVIDENCE

Evidence Pack deve guardar também:

```text
tentativas que NÃO funcionaram
```

Exemplo:

- resposta “1” funcionou;
- resposta “Preciso de reparos...” falhou.

Isso evita candidate generator repetir hipótese rejeitada.

---

# 45. ROUTE NEIGHBOR GRAPH

Precisamos saber quem pode quebrar junto.

Construir derivação:

```text
step/helper/anchor/flow/slot
↓
quais routes usam
```

Não precisa tabela nova se pode derivar offline.

Antes de candidate:

```text
impact set
```

é calculado.

Test battery usa esse conjunto.

---

# 46. PATCH SCOPE MINIMIZATION

Regra:

> **o patch aprovado deve ser o menor que resolve o drift.**

Prioridade:

```text
route+subservice
↓
route
↓
family
↓
global helper
```

Só ampliar scope quando evidence provar equivalência.

---

# 47. GENERALIZATION TEST

Quando candidate propõe helper compartilhado:

provar:

```text
target route improves
+
all consumers tested
```

Sem isso:

não generalizar.

---

# 48. API DISCOVERY CONFIDENCE

`browser-to-api` upstream já produz coverage report.

AutoBrokers deve separar:

```text
endpoint observed
schema observed
auth observed
side effect semantics known
idempotency known
```

Mesmo OpenAPI com 100% de schema não significa safe action.

---

# 49. PII / SECURITY

Evidence deve ser redigida.

Não guardar:

- senha;
- token;
- cookie;
- CPF cru;
- cartão;
- session secret.

Screenshots/DOM/HAR podem conter PII.

Antes de persistir em artifact reutilizável:

```text
redaction
```

ou storage privado com ACL e retention curta, conforme autoridade atual.

Patch candidate usa refs/redacted snippets.

---

# 50. TENANT / GLOBAL LEARNING

A rota de seguradora tende a ser conhecimento global.

Mas evidence vem de tenants.

Candidate global pode usar:

- evidência anonimizada;
- fatos de rota;
- sem PII;
- sem expor origem operacional sensível.

Registrar:

```text
evidence_companies_count
```

sem necessariamente revelar nomes no card global.

---

# 51. HUMAN APPROVAL NÃO DEVE EXPOR PII

Operator card:

- seguradora;
- ramo;
- serviço;
- tela;
- resposta;
- route metrics.

Não precisa mostrar CPF/nome/telefone.

Quando inspeção de sessão for necessária:

use permissão específica e redaction.

---

# 52. AUDIT EVENTS

Eventos mínimos:

```text
route.drift_detected
route.drift_reobserved
route.candidate_created
route.candidate_compiled
route.candidate_test_started
route.candidate_test_failed
route.candidate_test_passed
route.assessment_before
route.assessment_after
route.candidate_eligible
route.candidate_rejected
route.publish_requested
route.publish_approved
route.publish_conflict
route.canary_started
route.canary_observation
route.release_activated
route.rollback_triggered
route.rollback_completed
route.release_superseded
```

---

# 53. MÉTRICAS

## Detecção

```text
drifts_detected
unique_drifts
duplicate_drifts_collapsed
time_first_seen_to_candidate
```

## Qualidade de candidate

```text
candidate_accept_rate
candidate_reject_rate
wrong_semantics_rate
insufficient_evidence_rate
stale_candidate_rate
```

## Teste

```text
target_replay_pass
neighbor_regression_count
mutation_kill_rate
assessment_delta
hard_gate_delta
```

## Release

```text
approval_time
canary_success_rate
rollback_rate
time_to_rollback
```

## Resultado

```text
time_drift_to_safe_fix
repeated_same_drift_after_release
needs_human_due_to_route_drift
route_regression_incidents
```

---

# 54. SLA NÃO É META INVENTADA

Não escrever:

```text
corrigir drift em 5 minutos
```

sem baseline.

A 087 primeiro mede:

```text
current drift-to-fix time
```

Depois metas podem nascer.

---

# 55. BLOCO 0 — WARM-UP / FORENSE

Antes da primeira edição:

1. confirmar HEAD e árvore;
2. ler SPEC-080 inteira;
3. ler 083, 084, 084.1, 084.2 reports;
4. ler SPEC-085/report;
5. carregar a Candidate SPEC-089 fornecida pelo Founder;
6. mapear `route_sentinel.py`;
7. mapear `playbook_tailor.py`;
8. mapear `ura_simulator.py`;
9. mapear `ura_map_service.py`;
10. mapear overlay reader em `corridor_playbooks.py`;
11. confirmar schema vivo de `playbook_overlays`;
12. medir quantas rows existem;
13. medir quantos `route_drift`;
14. medir severities/status;
15. verificar se qualquer auto-apply ocorreu;
16. medir active Atlas maps;
17. localizar promotion path de map;
18. localizar admin inbox/approval existente;
19. localizar Capability Registry/RBAC;
20. localizar `route_publish` equivalente;
21. medir current route assessments;
22. verificar P-226 / truth staleness da 089;
23. verificar route fingerprints reconstruíveis;
24. medir current corpus por route;
25. medir recurring drift candidates;
26. procurar source mutation em tests;
27. auditar scheduler/worker path;
28. auditar PII de screenshots/HAR/observed events;
29. verificar SPEC-077 state real;
30. verificar profiler/HAR importer atual.

---

# 56. PREMISSAS A REFUTAR NO WARM-UP

## P1
“playbook_overlays continua vazio.”

Medir.

## P2
“Nenhum auto-apply já ocorreu.”

Medir.

## P3
“Sentinela é o único writer de route_drift.”

Provar.

## P4
“Todo active map representa verdade mais nova.”

Provar.

## P5
“Simulador cobre native flows atuais.”

Tentar falsificar.

## P6
“RouteAssessment 089 consegue avaliar ephemeral candidate sem escrever fonte.”

Provar.

## P7
“Existe um seam único para compilar patch.”

Tentar falsificar.

## P8
“O Browser Intelligence Lab já possui os artifacts necessários para browser adapter.”

Medir.

---

# 57. BLOCO A — DESARMAR AUTO-APPLY HISTÓRICO

Objetivo:

```text
nenhum código atual consegue ativar route patch automaticamente.
```

- alterar Sentinela/Alfaiate;
- preservar detection;
- criar guard;
- migration apenas se necessário.

### Gate A

Mutation:

reativar `apply_auto_overlays`.

Teste deve reprovar.

---

# 58. BLOCO B — DRIFT V2 + FINGERPRINT

Implementar:

- taxonomy;
- structural fingerprint;
- dedupe;
- evidence counters;
- baseline release ref;
- route identity canônica.

### Gate B

Controles:

- nome variável = mesmo fingerprint;
- option diferente = fingerprint diferente;
- same drift repeated = uma linha/candidate.

---

# 59. BLOCO C — EVIDENCE PACK

Implementar builder.

### Gate C

Um evidence pack deve reproduzir:

- tela;
- route;
- count;
- sessions;
- observed successful reply;
- source;
- current behavior;
- before assessment.

Sem PII.

---

# 60. BLOCO D — PATCH CANDIDATE + COMPILER

Implementar candidate schema e operations.

Compiler não publica.

### Gate D

- invalid operation rejeitada;
- target inexistente rejeitado;
- route fingerprint stale rejeitado;
- compiled patch deterministic.

---

# 61. BLOCO E — EPHEMERAL SANDBOX

Implementar rota virtual/patched view.

É proibido:

```text
INSERT active
→ test
→ DELETE
```

### Gate E

Banco/runtime active permanece byte/logicamente igual durante o teste.

---

# 62. BLOCO F — TEST BATTERY

Rodar T0–T9.

Integrar neighbor graph.

### Gate F

Candidate de exemplo:

- before falha;
- after passa;
- vizinhos verdes;
- Tool Contract verde;
- mutation vermelha;
- assessment generated.

---

# 63. BLOCO G — SPEC-089 BEFORE/AFTER

Consumir `RouteAssessment`.

### Gate G

Provar:

```text
same rubric version
different route fingerprint
raw earned/max visível
hard gates comparados
```

Score impossível >100 deve falhar.

UNKNOWN crítico fail closed.

---

# 64. BLOCO H — APPROVAL `route_publish`

Criar/reusar inbox existente.

Não criar novo Portal Admin.

### Gate H

- unauthorized = 403;
- stale candidate = 409;
- modified fingerprint invalidates approval;
- approver sees before/after.

---

# 65. BLOCO I — RELEASE + CANARY

Implementar activation pointer/compiled patch path escolhido.

### Gate I

- candidate não-approved invisível;
- canary somente allowlist;
- parent release preservada;
- rollback pointer pronto.

---

# 66. BLOCO J — OBSERVATION + CIRCUIT BREAKER

Monitorar canary.

### Gate J

Inject regression:

```text
patch causes needs_human
```

Expected:

```text
rollback exactly once
parent active
event recorded
no second rollback
```

---

# 67. BLOCO K — END-TO-END SELF-HEALING

Caso sintético baseado em evidência real.

```text
observed unknown screen
↓
drift
↓
candidate
↓
before fail
↓
after pass
↓
approval
↓
canary
↓
successful route
↓
active
```

Segundo ensaio:

```text
bad canary
↓
breaker
↓
rollback
```

---

# 68. TEST MATRIX

| Teste | Obrigatório |
|---|---:|
| fingerprint normalization | sim |
| fingerprint collision negative | sim |
| drift dedupe | sim |
| evidence pack | sim |
| PII redaction | sim |
| candidate schema | sim |
| candidate immutable | sim |
| compiler deterministic | sim |
| ephemeral sandbox | sim |
| target replay | sim |
| full route replay | sim |
| neighbors | sim |
| real motor offline | sim |
| Tool Contract | sim |
| native flow | sim |
| Simulator | sim |
| mutation | sim |
| assessment before/after | sim |
| hard gate non-compensation | sim |
| approval permission | sim |
| stale baseline | sim |
| stale evidence | sim |
| double-click idempotency | sim |
| canary isolation | sim |
| rollback | sim |
| double rollback idempotency | sim |
| cross-tenant evidence | sim |
| no auto-publish | sim |
| regression pack 083–085 | sim |

---

# 69. MUTATIONS OBRIGATÓRIAS

## M1 — reativar auto-apply
Gate vermelho.

## M2 — candidate non-approved virar visible
Gate vermelho.

## M3 — remover baseline fingerprint check
Stale candidate passa → vermelho.

## M4 — normalizer colapsar opção semanticamente diferente
Collision test vermelho.

## M5 — pular Tool Contract
084.2 case volta a falso verde → vermelho.

## M6 — Score compensar hard gate
99 + FAIL aprovado → vermelho.

## M7 — neighbor test removido
shared helper regression passa → vermelho.

## M8 — mutation que não consegue matar patch
candidate não elegível.

## M9 — approval fingerprint ignorado
edited candidate publica → vermelho.

## M10 — rollback não idempotente
dois breakers → estado inválido → vermelho.

---

# 70. RED TEAM

Missão:

> **fazer uma rota errada chegar a CANARY/ACTIVE ou uma rota boa ser rollbackada sem evidência, sem os testes perceberem.**

Ataques:

- same text/different option;
- changing name/date;
- incomplete transcript;
- human reply not tied to outcome;
- sibling with similar wording but different semantics;
- candidate based on one accidental success;
- stale baseline;
- route changed again;
- hard gate UNKNOWN;
- rubric version changed between before/after;
- source mutation during test;
- test calls regex instead of motor;
- native flow omitted;
- finalization changed;
- `sem_chute` converted to constant;
- tenant data leak;
- PII in evidence;
- approval double click;
- rollback race;
- old candidate reactivated;
- active Atlas map stale.

---

# 71. FAILURE MODES

## F1 — Sentinela cria candidate para ruído
Fingerprint/dedupe/evidence floor.

## F2 — Candidate resolve target e quebra irmão
Neighbor graph.

## F3 — Candidate pontua mais e perde hard gate
Non-compensation.

## F4 — Candidate usa human reply que não foi bem-sucedida
Outcome-linked evidence.

## F5 — Baseline mudou
CAS / stale baseline.

## F6 — Rubrica mudou
Reassess both.

## F7 — Test alterou source
Tree integrity guard.

## F8 — Canary quebra
Circuit breaker.

## F9 — Circuit breaker mede volume muito baixo
Hard-event triggers separados de rate triggers.

## F10 — Rollback falha
parent release permanece artifact e operação é idempotente/retriable.

---

# 72. ROLLOUT

## Phase 0 — detection only

- novo fingerprint;
- evidence;
- sem candidate automation se necessário.

## Phase 1 — auto-candidate / no publish

Medir:

- qualidade;
- rejection reasons;
- false drift.

## Phase 2 — human-approved canary

Poucas routes.

## Phase 3 — controlled active

Expandir.

Browser adapter não entra automaticamente só porque conversation adapter funcionou.

---

# 73. FEATURE FLAGS

Mínimo:

```text
ROUTE_SELF_HEAL_DETECT_ENABLED
ROUTE_SELF_HEAL_CANDIDATE_ENABLED
ROUTE_SELF_HEAL_CANARY_ENABLED
ROUTE_SELF_HEAL_ROLLBACK_ENABLED
```

Não criar flag por insurer.

Kill switch global:

```text
ROUTE_SELF_HEAL_CANARY_ENABLED=false
```

não apaga active releases já aprovadas; apenas impede novas.

---

# 74. ROLLBACK DA PRÓPRIA SPEC

Se 087 tiver problema:

- desligar detection/candidate/canary;
- manter route baseline anterior;
- preservar audit/evidence;
- não apagar candidates;
- não promover overlay histórico;
- restaurar parent release quando necessário.

---

# 75. DEFINIÇÃO DE PRONTO

A SPEC-087 só fecha quando:

- [ ] SPEC-080 foi formalmente absorvida/superseded;
- [ ] nenhum auto-apply histórico continua ativo;
- [ ] Sentinela não publica;
- [ ] Alfaiate não publica;
- [ ] route drift taxonomy existe;
- [ ] fingerprint estrutural existe;
- [ ] fingerprint não superconta valores variáveis;
- [ ] drift dedupe existe;
- [ ] Evidence Pack existe;
- [ ] Evidence Pack não contém PII indevida;
- [ ] RoutePatchCandidate existe;
- [ ] candidate é imutável/versionado;
- [ ] baseline fingerprint existe;
- [ ] compiled patch separado de candidate;
- [ ] candidate nunca é runtime-active;
- [ ] sandbox é ephemeral;
- [ ] teste não precisa gravar patch ativo;
- [ ] target replay existe;
- [ ] full route replay existe;
- [ ] neighbor replay existe;
- [ ] teste chama motor real;
- [ ] native flow entra;
- [ ] Tool Contract entra;
- [ ] Simulador entra como uma estação, não juiz único;
- [ ] mutation entra;
- [ ] SPEC-089 assessment BEFORE existe;
- [ ] SPEC-089 assessment AFTER existe;
- [ ] mesma rubric version é exigida;
- [ ] score != certification preservado;
- [ ] hard gate não compensável preservado;
- [ ] patch incremental pode ser eligible sem AAA_READY;
- [ ] `route_publish` capability existe;
- [ ] Founder não está hardcoded;
- [ ] approval usa fingerprint;
- [ ] stale baseline rejeita;
- [ ] stale evidence rejeita;
- [ ] release possui parent;
- [ ] canary é scoped;
- [ ] candidate rejected é invisível;
- [ ] circuit breaker existe;
- [ ] rollback automático volta somente a release aprovada anterior;
- [ ] rollback é idempotente;
- [ ] events/audit completos;
- [ ] metrics existem;
- [ ] cross-tenant verde;
- [ ] PII verde;
- [ ] M1–M10 vermelhas quando mutadas;
- [ ] E2E good patch verde;
- [ ] E2E bad canary rollback verde;
- [ ] regression 083/084/084.1/084.2/085 verde;
- [ ] execution report produzido.

---

# 76. OBJETIVOS DE NEGÓCIO

A 087 deve:

1. reduzir tempo humano entre “seguradora mudou” e “rota corrigida”;
2. diminuir repetição de `needs_human` pelo mesmo drift;
3. transformar operação real em regressão;
4. preservar controle humano sobre conhecimento operacional;
5. evitar deploy manual para correções pequenas quando houver release surface segura;
6. criar trilha auditável de por que a rota mudou;
7. permitir expansão para muitas seguradoras sem uma pessoa revisar todo o corpus diariamente;
8. preparar o AutoBrokers para manter seu moat operacional vivo.

---

# 77. O QUE MUDA NO AUTOBROKERS

Antes:

```text
ATLAS = sabe o que aconteceu
CORREDOR = sabe o que fazer
```

mas a ponte é manual.

Depois:

```text
ATLAS
  observa
    ↓
SENTINELA
  detecta
    ↓
EVIDENCE
  prova
    ↓
ALFAIATE
  propõe
    ↓
SANDBOX
  testa
    ↓
SPEC-089
  mede
    ↓
HUMANO
  autoriza
    ↓
RELEASE
  canário
    ↓
OBSERVA
    ↓
ATIVA / ROLLBACK
```

---

# 78. O GANHO ESTRATÉGICO

Esta SPEC cria a primeira versão governada do:

# **AutoBrokers Learning Flywheel**

```text
OPERAÇÃO REAL
↓
EVIDÊNCIA
↓
CANDIDATO
↓
PROVA
↓
GOVERNANÇA
↓
MELHORIA
↓
OPERAÇÃO REAL MELHOR
```

Isso é diferente de RAG.

É diferente de memória.

É diferente de “agente aprendendo sozinho”.

É:

> **conhecimento operacional executável, versionado, testado e governado.**

---

# 79. REFERÊNCIAS INTERNAS

Leitura obrigatória sob demanda:

- `SPEC-080-a-tela-que-o-atlas-viu-vira-passo-proposto.md`
- `ESTADO-DAS-SPECS.md`
- `SPEC-083-a-regua-do-corredor.md`
- `SPEC-084.1-EXECUTION-REPORT.md`
- `SPEC-084.2-EXECUTION-REPORT.md`
- `SPEC-085-o-destravamento-nao-trava-em-silencio.md`
- `SPEC-085-EXECUTION-REPORT.md`
- Candidate `SPEC-089-a-regua-aaa-e-honesta.md`
- Candidate SPEC-089 Research Pack
- `backend/app/services/atlas/route_sentinel.py`
- `backend/app/services/playbook_tailor.py`
- `backend/app/services/ura_simulator.py`
- `backend/app/services/ura_map_service.py`
- `backend/app/services/corridor_playbooks.py`
- `backend/app/services/insurer_dispatch_service.py`
- `backend/scripts/rubrica.py`
- `backend/scripts/replay.py`
- `backend/scripts/regua_motor.py`
- `backend/scripts/verificar_mutacoes.py`
- `backend/tests/test_a_rubrica_e_honesta.py`
- `SPEC-077-browser-intelligence-lab-browserbase-skills.md`
- `SPEC-077-AUDIT.md`
- Protocolo AutoBrokers AAA v9

---

# 80. REFERÊNCIAS EXTERNAS

## Browserbase Skills — browser-trace

Padrão absorvido:

- observador CDP passivo;
- network/console/DOM/screenshots;
- separar observação de ação;
- trace por página.

## Browserbase Skills — browser-to-api

Padrão absorvido:

- replay-driven discovery;
- request/response pairing;
- URL templating;
- schema inference;
- OpenAPI candidate;
- coverage report.

## Browserbase Skills — autobrowse

Padrão absorvido:

- run;
- inspect trace;
- improve;
- rerun;
- only graduate after repeated reliability.

Não é dependência runtime da 087.

## Stagehand v4

Padrão absorvido:

- self-healing browser actions;
- semantic recovery;
- caching;
- better browser-agent runtime.

Self-healing action gera evidence/candidate, não auto-publish.

---

# 81. AQUECIMENTO SUGERIDO AO CLAUDE CODE / CODEX

Antes da primeira edição, responder com evidência:

1. Quantos `route_drift` existem agora?
2. Quantos foram `auto_applied=true`?
3. Quantos overlays existem?
4. Algum overlay é realmente lido hoje?
5. Quais kinds de overlay o motor consegue executar?
6. `anchor_from_text` casa hoje com `_norm`?
7. Writer/reader de `playbook_ref` usam o mesmo namespace?
8. Qual é o active map de cada insurer?
9. Quem promove map para active?
10. Quantos writers de route_drift existem?
11. Onde está a inbox mais adequada para route approval?
12. Existe permission/capability que podemos evoluir para `route_publish`?
13. Qual é a forma real da Candidate SPEC-089 no workspace do Founder?
14. A 089 roda sem editar corredor?
15. A 089 consegue avaliar duas route views no mesmo commit?
16. Como obter assessment before/after com mesma rubric version?
17. Quais hard gates são route-sensitive?
18. Como derivar neighbor impact set?
19. Quais helpers são compartilhados?
20. O Simulador cobre native flows?
21. Qual teste chama o motor e qual só chama regex?
22. Existe fonte mutation leak ainda?
23. Qual surface de release é menor: overlays, registry ou source patch?
24. Como fazer rollback atômico nessa surface?
25. Existe profiler/browser trace atual após SPEC-077?
26. Existe HarImporter?
27. Quais PII podem entrar em evidence?
28. Mostre uma candidate que a 080 publicaria mas a 087 deve rejeitar.
29. Mostre uma melhoria incremental segura numa rota NOT_READY.
30. Tente quebrar a tese desta SPEC.

---

# 82. COMANDO FINAL AO EXECUTOR

Não implemente “auto-healing” como:

```text
try
except
LLM
patch
```

Implemente como:

```text
OBSERVAÇÃO
+
VERSÃO
+
EVIDÊNCIA
+
CANDIDATO
+
COMPILAÇÃO
+
REPLAY
+
MUTAÇÃO
+
ASSESSMENT
+
APROVAÇÃO
+
CANÁRIO
+
ROLLBACK
```

A frase que governa a 087 é:

> **O AutoBrokers pode aprender sozinho o que provavelmente mudou. Só pode ensinar o runtime depois de provar, receber autorização e manter uma saída segura.**
