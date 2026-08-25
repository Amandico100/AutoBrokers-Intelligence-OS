# SPEC-089 — A RÉGUA AAA É HONESTA
## Score diagnóstico, gates não compensáveis e certificação real de corredores

**Produto:** AutoBrokers Intelligence OS  
**Status:** CANDIDATE SPEC — pronta para aquecimento AAA; ainda não executada  
**Data da redação:** 25/08/2026  
**Baseline observado durante a redação:** `main` em `8b49fdb337a6c37eb2ad181f5bad544a55dc0827`  
**Branch sugerida quando for executar:** `feat/spec089-a-regua-aaa-e-honesta`  
**Depende de:** SPEC-083, SPEC-084, SPEC-084.1 e SPEC-084.2 executadas  
**Contexto posterior já presente no repositório:** SPEC-085 executada; SPEC-092 já escrita  
**Pendência primária:** P-226 e demais referências reais a `SPEC-089` encontradas no warm-up  
**Runtime preservado:** Smith + LangGraph/LangChain + FastAPI + Supabase/Postgres + Redis + Qdrant + MinIO  
**Natureza:** instrumento de avaliação e certificação. Esta SPEC mede; não “melhora rota para bater nota”.  
**Research Pack:** `SPEC-089-a-regua-aaa-e-honesta-RESEARCH-PACK.md`

---

# 0. RESULTADO EM UMA FRASE

> **Quando o AutoBrokers chamar uma rota de AAA, isso significará uma coisa verificável: a rota passou todos os gates obrigatórios do seu perfil, tem score diagnóstico honesto, foi medida pela versão declarada da régua e — se disser `AAA_VALIDATED` — existe prova real de ponta a ponta daquela rota/release.**

A régua deixa de tentar cumprir duas funções com o mesmo número.

```text
DIAGNÓSTICO
score 0–100
onde a rota está forte/fraca
        +
CERTIFICAÇÃO
PASS / FAIL
AAA_READY / AAA_VALIDATED
baseada em gates não compensáveis
```

---

# 0.1 DECISÕES DO FOUNDER JÁ APROVADAS

Estas decisões entram como **requisitos**:

1. **AAA é certificação binária.**  
   A nota é diagnóstica. Não haverá `A`, `AA`, “quase AAA” ou qualquer tier que pareça autorização intermediária.

2. **Existem dois níveis de AAA:**
   - `AAA_READY` — a rota passou integralmente as provas offline/contratuais necessárias para ser considerada pronta;
   - `AAA_VALIDATED` — além de `AAA_READY`, existe evidência E2E real válida da mesma rota/release.

3. **O score considera somente itens realmente aplicáveis**, com três travas:
   - `NOT_APPLICABLE` exige justificativa e evidência;
   - `UNPROVEN`, `UNKNOWN` ou erro de medição jamais desaparecem silenciosamente do denominador;
   - gate obrigatório não pode ser compensado por pontos em outro eixo.

---

# 0.2 NÃO-OBJETIVOS

Esta SPEC NÃO existe para:

- preservar a quantidade histórica de 19 rotas AAA;
- aumentar a média das rotas;
- fazer o total bruto “voltar para 100” por estética;
- limitar o score com `min(100, score)`;
- redistribuir peso até a máquina de lavar ficar 100;
- alterar `ura_steps`, âncoras, subservices ou corredores para a nota subir;
- implementar o self-healing da SPEC-087;
- instalar OpenAI Evals, DeepEval, Ruflo, DeepSeek Harness ou outro runtime de avaliação;
- adicionar LLM-as-judge ao instrumento determinístico;
- transformar replay/simulação em falsa prova de produção;
- inventar fingerprint histórico;
- esconder problema real reclassificando-o como N/A.

> **Se uma régua mais honesta reduzir o número de rotas certificadas, isso pode ser o resultado correto.**

---

# 1. POR QUE ESTA SPEC EXISTE

## 1.1 A SPEC-083 resolveu um problema legítimo

A SPEC-083 nasceu depois de uma rota real — `allianz / residencial / maquina_de_lavar` — ter sido executada ponta a ponta e, mesmo assim, uma auditoria posterior encontrar furos que dezenas de asserções verdes não haviam detectado.

Duas decisões da SPEC-083 permanecem canônicas:

> **Ponto só se ganha contra o CORPUS. Declaração não vale ponto.**

e:

> **Teste de corredor tem de chamar o MOTOR. Teste que chama o regex não guarda o corredor — guarda o regex.**

Preservar essa filosofia é requisito.

## 1.2 O instrumento evoluiu, mas o contrato matemático não acompanhou

No baseline observado, `backend/scripts/rubrica.py` declara cinco eixos:

```text
A · EVIDÊNCIA     20
B · COBERTURA     35
C · SEGURANÇA     26
D · CONHECIMENTO  10
E · PROVA         15
                   ──
                  106
```

O mesmo cabeçalho ainda fala em:

```text
PRONTIDÃO 100
```

O C7 acrescentou seis pontos ao eixo C depois da concepção original.

O objeto atual `Nota` calcula corretamente uma **fração sobre o denominador aplicável**, e por isso o inventário mostra coisas como:

```text
102/106 → AAA(106)
```

não “102%”.

Porém surgiram quatro problemas estruturais:

1. documentação e testes ainda falam em teto 100;
2. denominadores históricos ficaram presos em números antigos;
3. `AAA` é derivado da porcentagem do score, mesmo quando uma condição crítica pode estar fora da soma;
4. mudanças de instrumento não têm versão explícita.

A SPEC-089 não deve “consertar 102”.

Deve consertar **a autoridade do instrumento**.

## 1.3 P-226 prova que a avaliação sofreu drift

`backend/tests/test_a_rubrica_e_honesta.py` mantém cinco testes em `xfail(strict=True)` destinados à SPEC-089:

```text
1. denominator antigo esperado como 96;
2. guarda que exige que sempre exista alguma órfã funcional;
3. mutação que pressupõe estado antigo do subserviço;
4. eixo E esperado como 15, mas observado como 9;
5. delta calculado contra o antigo teto fixo 100.
```

São cinco famílias diferentes de **truth-staleness**.

Consertar somente os `expected` seria exatamente o erro que o protocolo AAA proíbe.

## 1.4 A SPEC-084.2 mostrou que score alto não significa executabilidade

A SPEC-084.2 encontrou um caso mais importante:

> **As 19 rotas consideradas AAA respondiam as telas da URA, mas inicialmente nenhuma das 19 passava o portão do contrato real da ferramenta.**

Em outras palavras:

```text
CORREDOR BOM
+
REPLAY BOM
+
RUBRICA ALTA
≠
AGENTE CONSEGUE EXECUTAR
```

O bloqueio estava **antes do corredor**, no contrato de entrada.

Esse fato cria uma regra definitiva:

> **Tool/Runtime Contract é gate não compensável de `AAA_READY`.**

---

# 2. VALOR PARA O AUTOBROKERS

Esta não é uma feature cosmética.

É a peça que permite às próximas fábricas automatizarem melhoria sem aprender a otimizar uma métrica falsa.

```text
SPEC-087 — Route Self-Healing
“este patch melhorou?”
              ↓
      precisa da régua

SPEC-090 — Intelligence Factory
“este candidato virou rota pronta?”
              ↓
      precisa da régua

SPEC-091 — Protocol Registry
“o processo produziu algo publicável?”
              ↓
      precisa de gates honestos

SPEC-100 — Skill & Capability Factory
“esta capability merece release?”
              ↓
      herda a filosofia

SPEC-108 — MetaHarness
“esta nota significa alguma coisa?”
              ↓
      herda o precedente
```

Se uma régua premia um buraco, um sistema autoevolutivo aprende a criar buracos.

Se uma régua pune o comportamento correto, um sistema autoevolutivo aprende a desfazer o comportamento correto.

---

# 3. PRINCÍPIOS CONGELADOS

## 3.1 Score não é certificação

O score responde:

> **Quanto das evidências aplicáveis esta rota conquistou?**

A certificação responde:

> **Existe alguma condição que proíbe chamar esta rota de AAA?**

Portanto:

```text
score 99.0 + gate crítico FAIL
=
NOT_READY
```

## 3.2 Gate obrigatório é não compensável

Nenhuma soma de pontos pode compensar:

- instrumento inválido;
- rota não mensurável;
- comportamento de segurança sem prova;
- outcome falso;
- Tool/Runtime Contract quebrado;
- prova/mutation fail-open.

## 3.3 Certificação é fail-closed

Qualquer estado:

```text
UNKNOWN
ERROR
não consegui carregar arquivo
não consegui executar mutation
corpus inconsistente
detector caiu
evidência ambígua
```

NUNCA vira `PASS`.

O resultado será, conforme a camada:

```text
INSTRUMENT_ERROR
UNMEASURABLE
NOT_READY
```

## 3.4 A régua não se “conserta” escondendo violação matemática

É proibido:

```python
score = min(100, score)
```

Se qualquer item produzir:

```text
earned > max_points
```

ou o total violar:

```text
raw_earned > applicable_max
```

o assessment inteiro deve virar:

```text
INSTRUMENT_ERROR
```

## 3.5 A quantidade de AAA não é gate

O baseline histórico contém 19 rotas no antigo patamar AAA.

A 089 pode terminar com:

```text
17
19
22
```

ou outro valor.

Cada mudança precisa ser explicada.

Nenhum código pode ser alterado somente para conservar “19”.

## 3.6 Mudança do instrumento exige versão

Não existe:

> “a nota mudou porque adicionamos um item”.

Existe:

```text
rubric_version = x.y.z
```

A comparação histórica só é direta quando versões/perfis são comparáveis.

---

# 4. ARQUITETURA CONCEITUAL

```text
ROTA
 ↓
ASSESSMENT PROFILE
 ↓
┌─────────────────────────────────────┐
│ EVIDENCE CREDITS                    │
│ A · Evidência                       │
│ B · Cobertura                       │
│ C · Segurança                       │
│ D · Conhecimento                    │
│ E · Prova                           │
└─────────────────────────────────────┘
 ↓
DIAGNOSTIC SCORE 0–100
 +
┌─────────────────────────────────────┐
│ HARD GATES                          │
│ G0 Instrument Integrity             │
│ G1 Measurability / Identity         │
│ G2 Functional Coverage              │
│ G3 Safety / No Guess                │
│ G4 Outcome Truth                    │
│ G5 Tool / Runtime Contract          │
│ G6 Proof Quality                    │
└─────────────────────────────────────┘
 ↓
NOT_READY / AAA_READY
 ↓
LIVE EVIDENCE GATE
 ↓
AAA_VALIDATED
```

---

# 5. ONTOLOGIA NOVA

## 5.1 EvidenceCredit

Unidade diagnóstica de evidência.

Contrato conceitual:

```python
EvidenceCredit:
    id: str
    axis: str
    title: str

    earned: float
    max_points: float

    applicability:
        APPLICABLE
        NOT_APPLICABLE
        UNPROVEN

    evidence: str
    source_kind: str
    source_ref: str | None

    critical: bool
```

## 5.2 GateResult

Decisão não compensável.

```python
GateResult:
    id: str
    title: str

    status:
        PASS
        FAIL
        NOT_APPLICABLE
        UNKNOWN
        ERROR

    evidence: str
    blocking_reason: str | None
```

Para certificação:

```text
PASS ................. aceita
NOT_APPLICABLE ....... aceita somente se a justificativa for verificável
FAIL .................. bloqueia
UNKNOWN ............... bloqueia
ERROR ................. bloqueia
```

## 5.3 RouteAssessment

Saída canônica da régua:

```python
RouteAssessment:
    route_key
    assessment_profile

    rubric_version
    evaluator_commit
    evaluated_at

    raw_earned
    applicable_max
    diagnostic_score_pct

    credits[]
    gates[]

    certification_status
    blockers[]

    corpus_snapshot
    corpus_stats

    route_fingerprint
    live_evidence[]
```

---

# 6. ASSESSMENT PROFILES

A régua precisa saber **o que aquela rota promete**.

Perfis iniciais:

```text
RESOLVE
ENCAMINHA
HANDOFF_BY_DESIGN
```

## 6.1 RESOLVE

A rota promete efetivamente resolver/abrir o atendimento naquele canal.

É elegível a:

```text
AAA_READY
AAA_VALIDATED
```

## 6.2 ENCAMINHA

O comportamento correto é entregar link/canal/portal e encerrar essa etapa.

Não produzir protocolo naquele canal não é defeito.

Mas essa rota também não deve receber o selo definido como:

> “ir do pedido ao desfecho operacional/protocolo sem humano”.

Resultado:

```text
NOT_ELIGIBLE_FOR_AAA
```

com score diagnóstico disponível.

## 6.3 HANDOFF_BY_DESIGN

O produto decidiu conscientemente que o trabalho pertence a humano.

Resultado:

```text
NOT_ELIGIBLE_FOR_AAA
```

Isso não significa “rota ruim”.

Significa “AAA não é a certificação certa”.

## 6.4 Proibição de profile laundering

Trocar:

```text
RESOLVE → ENCAMINHA
```

só para escapar de um gate é violação.

O profile deve vir do contrato de produto/corredor e possuir prova.

---

# 7. SCORE DIAGNÓSTICO

## 7.1 Fórmula

```text
raw_earned =
    Σ earned dos itens APPLICABLE

applicable_max =
    Σ max_points dos itens APPLICABLE

diagnostic_score_pct =
    100 × raw_earned / applicable_max
```

Se:

```text
applicable_max == 0
```

resultado:

```text
UNMEASURABLE
```

e não zero silencioso.

## 7.2 Invariantes matemáticos

```text
0 <= item.earned <= item.max_points
0 <= raw_earned <= applicable_max
0 <= diagnostic_score_pct <= 100
```

Qualquer violação:

```text
INSTRUMENT_ERROR
```

## 7.3 Raw denominator continua visível

A nova régua não apaga a preocupação correta do inventário atual.

Exibir:

```text
diagnóstico .... 96,2%
créditos ........ 102/106 aplicáveis
```

Assim:

- a escala diagnóstica é consistente;
- o leitor vê quanta superfície foi aplicável;
- não há “renormalização escondida”.

## 7.4 Certificação usa valor não arredondado

Exemplo:

```text
score interno: 94.999
display: 95.0
```

Certificação:

```text
NOT_READY
```

Nunca certificar pelo texto formatado.

---

# 8. APLICABILIDADE

## 8.1 APPLICABLE

O requisito pertence à rota.

Participa de:

```text
raw_earned
applicable_max
```

## 8.2 NOT_APPLICABLE

Só pode sair do denominador quando existem:

```text
regra determinística de inaplicabilidade
+
evidência
+
reason
```

Exemplo legítimo:

```text
native_flow
N/A
porque:
- rota não declara flow
- corpus não contém tela reconhecida como flow
```

## 8.3 UNPROVEN

Significa:

> “deveríamos conseguir provar, mas ainda não conseguimos.”

Não sai silenciosamente.

Quando item é obrigação:

```text
earned = 0
```

e pode também bloquear gate correspondente.

## 8.4 Detector quebrado ≠ N/A

Se o detector que deveria responder “há flow?” gera exception:

```text
UNKNOWN
```

Nunca:

```text
NOT_APPLICABLE
```

> **Falha do instrumento não pode melhorar a rota.**

---

# 9. VERSIONAMENTO DA RÉGUA

## 9.1 Versão explícita

Adicionar constante/contrato equivalente:

```python
RUBRIC_VERSION = "2.0.0"
```

O valor final deve ser confirmado no warm-up.

## 9.2 MAJOR

Subir quando mudar:

- significado de certificação;
- eixos;
- pesos que alteram score;
- denominator logic;
- hard gate;
- threshold;
- elegibilidade;
- profile.

## 9.3 MINOR

Novo diagnóstico que não altera certificação nem comparabilidade principal.

## 9.4 Inventário deve carregar

```text
rubric_version
evaluator_commit
generated_at
corpus_snapshot
route_count
```

## 9.5 Comparação histórica

Proibido escrever:

> “a rota subiu de 92 para 96”

se cada número veio de rubric major diferente.

Na migração, preferir:

```text
v1 raw .... 102/106
v2 score ... 96,2%
```

e, quando útil, reexecutar o mesmo snapshot pelas duas versões.

---

# 10. ROUTE FINGERPRINT

## 10.1 Por que existe

Sem fingerprint:

```text
rota validada hoje
 ↓
rota muda amanhã
 ↓
selo antigo continua
```

Isso é falso.

## 10.2 Contrato

Gerar hash estável do conteúdo operacional que define a rota.

Implementação preferida:

```text
stable serialization
do playbook/subservice/regras relevantes
↓
SHA-256
```

Não incluir:

- PII;
- timestamp;
- segredo;
- dado de cliente.

## 10.3 Mudança material

Mudou fingerprint:

```text
AAA_VALIDATED
↓
AAA_READY
```

até nova validação live.

Isso é intencional.

---

# 11. CORPUS SNAPSHOT

Cada assessment precisa declarar qual corpus usou.

Mínimo:

```text
corpus hash/version
número de sessões
número de telas
data de geração
```

Se corpus novo aparece:

- score pode mudar;
- gates são reexecutados;
- não chamar automaticamente de “regressão”;
- pode ser nova realidade descoberta.

---

# 12. ESTADOS DE CERTIFICAÇÃO

Estados canônicos:

```text
INSTRUMENT_ERROR
UNMEASURABLE
NOT_ELIGIBLE_FOR_AAA
NOT_READY
AAA_READY
AAA_VALIDATED
```

Nenhum outro estado de certificação.

Os antigos:

```text
AAA(106)
quase(106)
parcial(94)
esqueleto(106)
toco(...)
```

podem permanecer no histórico, mas deixam de ser linguagem de certificação no inventário novo.

---

# 13. REGRA DE AAA_READY

Uma rota `RESOLVE` só recebe `AAA_READY` quando:

```text
diagnostic_score_pct >= 95.0   [valor interno, não arredondado]
AND
todos os hard gates aplicáveis == PASS
AND
zero gate UNKNOWN
AND
zero gate ERROR
AND
zero mutation crítica sobrevivente
AND
instrument self-check == PASS
```

---

# 14. REGRA DE AAA_VALIDATED

Só recebe `AAA_VALIDATED` quando:

```text
AAA_READY
AND
existe live evidence verificada
AND
a evidence pertence à mesma route key
AND
corresponde ao fingerprint/release compatível
AND
o outcome final ocorreu no mundo real
AND
nenhum humano completou o caminho que está sendo certificado como autônomo
AND
o segurado recebeu o desfecho exigido
```

---

# 15. LIVE EVIDENCE

## 15.1 Evidência histórica candidata

O warm-up deve verificar, não confiar cegamente, o caso:

```text
allianz / residencial / maquina_de_lavar

work_run:
e5279497-a642-4703-a85f-d92a381e45ac

session:
7ac3c101

data:
19/08/2026
```

A SPEC não autoriza copiar PII dessa execução para registry.

## 15.2 Historical unbound

Se não for possível ligar honestamente a evidência antiga ao fingerprint atual:

```text
evidence_status = historical_unbound
```

Resultado:

```text
AAA_READY
```

até nova prova live.

É proibido inventar fingerprint retroativo.

## 15.3 Múltiplos trials

Quando houver mais de uma execução real compatível:

registrar todas.

Não escolher somente a melhor.

Campos conceituais:

```text
live_attempts
live_successes
live_route_failures
external_failures
```

Não criar ainda uma fórmula sofisticada de confiabilidade com amostra pequena.

---

# 16. HARD GATE G0 — INSTRUMENT INTEGRITY

Pergunta:

> **A própria régua está em condição de julgar?**

PASS exige:

- rubric version definida;
- self-invariants verdes;
- zero item `earned > max`;
- score dentro de 0–100;
- mutation runner não fail-open;
- corpus legível;
- módulos essenciais carregados;
- nenhum erro de avaliação tratado como aprovação;
- nenhuma mutation obrigatória contada como sucesso porque não conseguiu rodar.

Se falhar:

```text
INSTRUMENT_ERROR
```

Nenhuma rota dessa execução pode receber AAA.

---

# 17. HARD GATE G1 — MEASURABILITY & ROUTE IDENTITY

Pergunta:

> **Conseguimos provar que estamos medindo ESTA rota?**

PASS requer:

### Opção A — identidade específica

Existe marca que distingue a rota no corpus.

ou:

### Opção B — equivalência provada

A seguradora realmente apresenta caminho indistinguível para aqueles serviços, e essa equivalência possui regra/evidência explícita.

Proibido:

```text
não consigo distinguir a rota
→ retiro a obrigação
→ certifico com score alto
```

Sem corpus suficiente:

```text
UNMEASURABLE
```

---

# 18. HARD GATE G2 — FUNCTIONAL COVERAGE

Pergunta:

> **As telas acionáveis que a rota encontra têm comportamento operacional conhecido?**

Para `AAA_READY`:

- zero órfã funcional aplicável;
- native flow que trava trabalho não pode sair como órfã inócua;
- handoff conhecido é classificado como handoff;
- redirect por desenho é classificado corretamente;
- determinismo atende o threshold vigente;
- tela não desaparece do denominator porque parser falhou;
- corpus usado é o corpus realmente atribuído à rota/perfil.

Nenhum threshold pode ser rebaixado apenas para preservar quantidade de AAA.

---

# 19. HARD GATE G3 — SAFETY / NO GUESS

Pergunta:

> **A rota pode tomar decisão perigosa ou afirmar algo do segurado sem origem?**

PASS exige, conforme aplicabilidade:

- finalize/freio casa tela real;
- tecla/opção tem origem;
- constante que decide pelo cliente tem justificativa;
- `sem_chute` escala em vez de inventar;
- slot condicional só é exigido no galho correto;
- dado de segurança não é inferido de campo semanticamente diferente;
- irreversibilidade conhecida possui guardrail;
- handoff correto não é “otimizado para fora” da rota.

Qualquer `UNKNOWN` de segurança:

```text
FAIL
```

para efeito de readiness.

---

# 20. HARD GATE G4 — OUTCOME TRUTH

Pergunta:

> **A rota termina entregando o outcome que promete?**

Para `RESOLVE`:

- marcador real de sucesso/protocolo é capturado quando o canal o produz;
- o MOTOR usa a captura;
- se há agendamento, o resumo ao segurado contém dia + período;
- não afirma “concluído” quando não concluiu;
- redirect não é contado como protocolo;
- handoff não é contado como resolução autônoma;
- sucesso do transcript e sucesso do mundo são conceitos diferentes.

Este gate é não compensável.

---

# 21. HARD GATE G5 — TOOL / RUNTIME CONTRACT

Pergunta:

> **O agente consegue chegar à rota com os dados que o contrato real permite carregar?**

Nasce diretamente do achado da SPEC-084.2.

PASS exige:

- schema/tool input alcança slots obrigatórios reais;
- `build_dry_run_plan` ou seam canônica equivalente alcança o estado correto;
- required slot não é inacessível pelo contrato;
- filho de galho não tomado não é exigido;
- aliases/normalização não bloqueiam rota válida;
- teste percorre o mesmo contrato que o LLM/runtime usa.

## 21.1 Controle obrigatório

Criar teste que recria a classe do defeito pré-084.2:

```text
rota e corpus intactos
score diagnóstico continua alto
MAS
Tool Contract perde um campo obrigatório
```

Esperado:

```text
G5 = FAIL
certification = NOT_READY
```

> **Esse é o teste que prova que score não compra certificação.**

---

# 22. HARD GATE G6 — PROOF QUALITY

Pergunta:

> **Os testes conseguem acusar o defeito que dizem guardar?**

PASS exige:

- teste de corredor chama MOTOR;
- positive control;
- negative control;
- critical mutations executadas;
- critical mutations mortas;
- restauração por cópia/hash íntegra;
- incapacidade de executar mutation = FAIL;
- teste causal não depende de o produto continuar defeituoso;
- detector de mutação não ganha ponto ao falhar.

---

# 23. LIVE GATE — GL

Somente para `AAA_VALIDATED`.

Requer:

```text
route key correta
+
seguradora/canal real
+
execução real
+
outcome real
+
sem humano completar o caminho certificado
+
registro técnico verificável
```

O registry deve referenciar ids técnicos.

Não precisa guardar:

- CPF;
- telefone;
- nome;
- apólice;
- protocolo textual.

---

# 24. P-226 — TRATAMENTO OBRIGATÓRIO

## 24.1 Denominator 96 envelhecido

Remover o anti-pattern:

```text
assert denominator == 96
```

sem contexto de versão.

Substituir por:

- `rubric_version`;
- invariantes;
- fixture que declara explicitamente a versão quando denominator exato for parte da prova.

## 24.2 “Sempre precisa existir órfã”

Esse teste deve morrer na forma atual.

Substituir por controle causal:

```text
1. uma tela real conhecida está RESPONDIDA
2. desliga deliberadamente o passo que a responde
3. a mesma tela vira ORFA_FUNCIONAL
4. restaura
5. volta a RESPONDIDA
```

A régua prova que enxerga órfã sem exigir que o produto permaneça imperfeito.

## 24.3 “Subserviço ainda não tem regra”

Não depender do estado atual da produção.

Testar a propriedade em cópia/fixture controlada:

```text
regra própria + frase REAL do corpus
→ crédito

regra própria + frase INVENTADA
→ zero

regra somente herdada, quando item promete regra da rota
→ zero
```

## 24.4 Eixo E = 9 vs 15

Não trocar:

```text
15 → 9
```

sem causa.

O warm-up precisa medir:

- por que seis pontos desapareceram;
- se detector mudou;
- se arquivo escolhido mudou;
- se mutation deixou de executar;
- se requisito ficou impossível;
- se produto melhorou e teste envelheceu.

Só fecha quando o comportamento do eixo E tiver explicação causal reproduzível.

## 24.5 `100 - 4`

Eliminar teto implícito.

Usar:

```text
baseline = assessment()
mutated  = assessment()

assert mutated.raw_earned == baseline.raw_earned - item.max_points
```

ou, para hard gate:

```text
baseline.certification == AAA_READY
mutated.certification == NOT_READY
```

---

# 25. CALIBRATION SUITE — GOLDEN CASES

O conjunto final é confirmado pelo executor.

## GOLD 1 — LIVE POSITIVE

Candidato:

```text
allianz / residencial / maquina_de_lavar
```

Esperado somente se a evidência reproduzir honestamente:

```text
profile = RESOLVE
score >=95
G0–G6 PASS
AAA_VALIDATED
```

Se fingerprint histórico não puder ser ligado:

```text
AAA_READY
```

Não forçar resultado.

## GOLD 2 — READY SEM LIVE

Candidato:

```text
allianz / residencial / encanador
```

Esperado, se reproduzir:

```text
AAA_READY
```

e não VALIDATED.

## GOLD 3 — NEAR MISS

Candidato:

```text
alfa / auto / pneu
```

Baseline histórico próximo de:

```text
100/106
```

Esperado:

```text
diagnostic <95
NOT_READY
```

se o estado continuar equivalente.

## GOLD 4 — SEM CORPUS

Selecionar rota realmente sem corpus.

Esperado:

```text
UNMEASURABLE
```

e não score zero.

## GOLD 5 — ENCAMINHA

Candidato:

```text
tokio / auto / guincho
```

Warm-up confirma `outcome=encaminha`.

Esperado:

```text
NOT_ELIGIBLE_FOR_AAA
```

sem cobrar protocolo inexistente por desenho.

## GOLD 6 — HIGH SCORE + GATE FAIL

Fixture/mutação controlada:

```text
rota excelente
score >=95
Tool Contract quebrado
```

Esperado:

```text
G5 FAIL
NOT_READY
```

Este é o golden case mais importante.

---

# 26. BALANCED CONTROLS

Todo detector crítico testa os dois lados.

```text
reconhece flow verdadeiro
NÃO chama texto comum de flow

reconhece handoff verdadeiro
NÃO chama resolução de handoff

exige slot condicional quando galho é tomado
NÃO exige quando não é tomado

reconhece protocolo
NÃO transforma número qualquer em protocolo

permite N/A quando realmente inaplicável
NÃO permite N/A quando detector falha
```

---

# 27. PROPERTY INVARIANTS

Sem obrigar dependência nova.

Se Hypothesis já existir e o executor provar valor, pode usar.

Caso contrário, loops/fixtures determinísticos.

Propriedades:

```text
earned nunca <0
earned nunca > max
score nunca <0
score nunca >100

erro não aumenta score
erro não certifica
UNKNOWN não certifica

remover evidência não aumenta score
remover evidência crítica não mantém readiness

N/A sempre tem reason

critical G3 mutation derruba readiness
critical G4 mutation derruba readiness
critical G5 mutation derruba readiness

restauração devolve hash original
```

---

# 28. EIXOS DIAGNÓSTICOS

A SPEC NÃO autoriza redistribuir pesos por preferência estética.

Preferência inicial:

```text
preservar A/B/C/D/E
preservar créditos atuais onde ainda têm dono causal
normalizar para score_pct
mover obrigatoriedade para hard gates
```

Se o warm-up provar que peso/itens estão errados, mudança é permitida, mas:

- precisa de medição;
- precisa subir `rubric_version` adequadamente;
- precisa registrar antes/depois.

---

# 29. SAÍDA HUMANA

Exemplo ilustrativo:

```text
allianz / residencial / maquina_de_lavar
──────────────────────────────────────────
Rubrica .............. 2.0.0
Profile .............. RESOLVE

DIAGNÓSTICO .......... 96,2%
créditos ............. 102/106 aplicáveis

GATES READY
G0 instrument ........ PASS
G1 identity .......... PASS
G2 coverage .......... PASS
G3 safety ............ PASS
G4 outcome ........... PASS
G5 tool/runtime ...... PASS
G6 proof ............. PASS

CERTIFICAÇÃO ......... AAA_VALIDATED
live evidence ........ 1 verificada
fingerprint .......... 8c...f2

FALTAS DIAGNÓSTICAS
- apelidos do jeito que o cliente fala (+4)
```

Valores são ilustrativos até execução.

## 29.1 Score alto, gate falho

```text
score ................ 98,1%
G5 tool/runtime ...... FAIL

CERTIFICAÇÃO ......... NOT_READY

BLOCKER
Tool Contract não consegue carregar local_seguro.
```

## 29.2 Sem corpus

```text
CERTIFICAÇÃO ......... UNMEASURABLE
motivo ................ zero telas atribuíveis
próxima ação .......... coleta dirigida
```

## 29.3 Encaminha

```text
profile .............. ENCAMINHA
score diagnóstico .... 91,4%
certificação AAA ..... NOT_ELIGIBLE_FOR_AAA
outcome correto ...... encaminhar por link
```

---

# 30. SAÍDA MACHINE-READABLE

Adicionar/confirmar JSON.

Contrato conceitual:

```json
{
  "route": {
    "insurer": "allianz",
    "line": "residencial",
    "service": "maquina_de_lavar"
  },
  "rubric_version": "2.0.0",
  "profile": "RESOLVE",
  "diagnostic": {
    "raw_earned": 102,
    "applicable_max": 106,
    "score_pct": 96.23
  },
  "certification": {
    "status": "AAA_VALIDATED",
    "blockers": []
  },
  "gates": [],
  "credits": [],
  "evidence": {
    "corpus_snapshot": "...",
    "route_fingerprint": "...",
    "live_count": 1
  }
}
```

A shape final pode respeitar contratos já existentes após warm-up.

---

# 31. CLI / CI

Preservar os comandos úteis atuais.

Desejável:

```bash
python backend/scripts/medir_rota.py \
  --seguradora allianz \
  --ramo residencial \
  --servico maquina_de_lavar

python backend/scripts/medir_rota.py ... --formato json

python backend/scripts/medir_rota.py --todas --formato markdown

python backend/scripts/medir_rota.py ... --require-aaa-ready
```

`--require-aaa-ready`:

```text
exit 0    AAA_READY ou AAA_VALIDATED
exit !=0  qualquer outro estado
```

Não fazer `--todas` falhar só porque o inventário contém rotas incompletas.

---

# 32. LIVE EVIDENCE REGISTRY

Não criar banco novo para esta SPEC.

Preferência:

um pequeno artifact versionado em Git, sem PII, por exemplo:

```text
backend/evals/route_live_evidence.json
```

ou caminho equivalente escolhido no warm-up.

Shape conceitual:

```json
{
  "route_key": "allianz/residencial/maquina_de_lavar",
  "observed_at": "2026-08-19T...",
  "work_run_ref": "e5279497-...",
  "session_ref": "7ac3c101",
  "result": "success",
  "human_completed": false,
  "evidence_status": "verified",
  "route_fingerprint": "..."
}
```

Proibido adicionar PII.

---

# 33. BLOCO 0 — WARM-UP / REFUTAÇÃO

Antes de editar código:

1. confirmar HEAD/branch;
2. confirmar que a SPEC-089 oficial ainda não foi adicionada ao repo;
3. localizar P-226;
4. rodar suíte relevante;
5. reproduzir os cinco `xfail`;
6. medir máquina de lavar;
7. rodar `--todas`;
8. confirmar max bruto atual;
9. confirmar `102/106`;
10. confirmar cálculo de `patamar`;
11. listar perfis/outcomes reais;
12. reproduzir eixo E = 9;
13. descobrir sua causa;
14. reproduzir Tool Contract gate real;
15. procurar mudanças posteriores ao baseline desta Candidate SPEC.

## 33.1 Duas premissas propositalmente contestáveis

**A:** “O único problema matemático é 106 pontos em algo documentado como escala 100.”

Pode ser falso. Procurar outras incoerências.

**B:** “A máquina de lavar deve sair imediatamente `AAA_VALIDATED`.”

Pode ser falso. Sem fingerprint/evidência compatível, ela fica READY.

## 33.2 Desafio obrigatório

> **Ache uma forma de uma rota ruim receber AAA mesmo depois desta SPEC.**

Se encontrar:

consertar o instrumento antes do release.

---

# 34. BLOCO A — MODELO DE ASSESSMENT

Implementar/refatorar:

- `EvidenceCredit`;
- `GateResult`;
- `RouteAssessment`;
- score normalizado;
- versionamento;
- assessment profiles;
- certification states;
- instrument errors.

### Gate A

Provar:

```text
score <=100
score >=0
raw <= max
UNKNOWN não certifica
ERROR não certifica
N/A sem reason é inválido
```

Mutation:

```text
earned > max
```

precisa deixar teste vermelho.

---

# 35. BLOCO B — HARD GATES

Implementar G0–G6 reaproveitando o que já existe.

Não criar segundo motor.

Reusar:

- replay;
- `regua_motor`;
- corridor playbooks;
- detector de eixo E;
- mutation runner;
- dry-run/contract real;
- corpus versionado.

### Gate B

GOLD 6 precisa ficar verde no comportamento:

```text
score alto + G5 FAIL = NOT_READY
```

e vermelho se G5 for removido.

---

# 36. BLOCO C — P-226 / GUARDA CAUSAL

Resolver cada uma das cinco falhas.

Critério:

```text
xfail da P-226 restante = 0
```

para os cinco casos.

Não basta trocar expected.

Relatório deve mapear:

| antigo | causa | contrato novo |
|---|---|---|
| denominator 96 | instrument drift | version-aware |
| precisa existir órfã | stale truth | causal mutation |
| campo vazio esperado | fixture dependente do estado | property |
| E 15 vs 9 | causa medida | ownership correto |
| 100 - 4 | ceiling histórico | dynamic baseline/gate |

---

# 37. BLOCO D — READY VS VALIDATED

Implementar registry/fingerprint mínimos.

Controles:

1. rota READY sem registry → `AAA_READY`;
2. evidence válida → `AAA_VALIDATED`;
3. evidence de outra rota → não valida;
4. `human_completed=true` → não valida;
5. fingerprint incompatível → `AAA_READY` + validation stale;
6. schema sem PII passa;
7. campo PII proibido reprova.

---

# 38. BLOCO E — INVENTÁRIO V2

Regenerar inventário.

Colunas mínimas:

```text
seguradora
ramo
serviço
profile
score diagnóstico
raw/applicable
hard gates
certificação
live evidence
blocker principal
o que falta
o que destrava
```

Eliminar do novo documento a terminologia ambígua:

```text
AAA(106)
quase(106)
parcial(94)
```

Histórico antigo permanece histórico.

---

# 39. BLOCO F — CALIBRAÇÃO DAS 73 ROTAS

Aplicar nova régua em todas.

Relatório responde:

```text
AAA antigos
AAA_READY
AAA_VALIDATED
NOT_READY
UNMEASURABLE
NOT_ELIGIBLE_FOR_AAA
INSTRUMENT_ERROR
```

Para cada rota que era AAA e deixou de ser:

- dizer qual gate;
- NÃO consertar rota nesta SPEC;
- registrar pendência.

Para cada rota que passou a READY:

- explicar evidência;
- provar que não foi afrouxamento.

---

# 40. BLOCO G — ADVERSARIAL / MUTATION

Bateria mínima:

### M1 — score overflow
`earned > max` → `INSTRUMENT_ERROR`.

### M2 — N/A laundering
`UNKNOWN → NOT_APPLICABLE` artificial → teste falha.

### M3 — Tool Contract
remove campo obrigatório → G5 FAIL.

### M4 — Outcome
desliga captura/summary essencial → G4 FAIL.

### M5 — Safety
desliga origem/justificativa → G3 FAIL.

### M6 — Proof fail-open
mutation runner não consegue ler arquivo → G6 FAIL.

### M7 — Wrong-route live evidence
evidence A tentando validar B → não valida.

### M8 — Stale evidence
fingerprint muda → VALIDATED cai para READY.

---

# 41. RED TEAM — MISSÃO: CONSEGUIR UM FALSO AAA

Atacar:

- comentário com palavras de controle;
- campo declarado sem corpus;
- herança de outra rota;
- evidence de rota vizinha;
- rota sem corpus;
- mutation não executada;
- detector lança exception;
- profile trocado para escapar gate;
- N/A artificial;
- live evidence com route key parecida;
- contract test usando schema diferente do runtime;
- flow classificado como inocente;
- handoff contado como resolução;
- link contado como protocolo;
- score arredondado 94.999 para 95.

O objetivo do red team não é “dar nota”.

É produzir falso positivo.

---

# 42. PERFORMANCE

A régua continua offline/development tooling.

Não entra no hot path de atendimento.

Medir:

```text
uma rota
--todas
mutation suite
```

Não introduzir LLM call.

Se tempo aumentar significativamente:

registrar causa e benefício.

---

# 43. SEGURANÇA E PRIVACIDADE

- zero novo segredo em log;
- zero PII no live evidence registry;
- zero texto cru de segurado no inventário;
- exemplos de corpus permanecem mascarados;
- banco em warm-up somente read-only;
- nenhuma mensagem enviada;
- nenhuma seguradora acionada;
- nenhuma exceção nova a RLS.

---

# 44. MULTI-TENANT

Mesmo sendo ferramenta predominantemente global/offline:

- corpus não pode vazar informação privada no output;
- live evidence ref não autoriza cross-tenant read;
- nenhum SELECT sem escopo “para facilitar teste”;
- nenhuma mudança em policy/RLS fora de blocker medido.

---

# 45. OBSERVABILIDADE

A saída machine-readable prepara futura SPEC-108.

Registrar:

```text
evaluated_at
rubric_version
commit
route
profile
score
gates
blockers
corpus_snapshot
route_fingerprint
```

Não implementar MetaHarness agora.

---

# 46. ARQUIVOS PROVÁVEIS

Aquecimento confirma.

Esperados:

```text
backend/scripts/rubrica.py
backend/scripts/medir_rota.py
backend/scripts/verificar_mutacoes.py              se necessário
backend/scripts/detector_do_eixo_e.py              se necessário

backend/tests/test_a_rubrica_e_honesta.py
backend/tests/test_a_regua_nao_tem_furo.py          apenas se contrato mudou
backend/tests/test_a_certificacao_aaa_e_honesta.py  provável novo

backend/evals/route_live_evidence.json              provável novo

docs/canon/reports/INVENTARIO-DE-ROTAS.md
docs/canon/reports/SPEC-089-EXECUTION-REPORT.md
```

## 46.1 Arquivos proibidos sem blocker medido

```text
backend/app/services/corridor_playbooks.py
backend/app/services/insurer_dispatch_service.py
```

Esta SPEC mede.

Se precisar seam mínima para o instrumento chamar o caminho real:

- provar necessidade;
- menor alteração;
- não alterar comportamento para ganhar nota.

---

# 47. MIGRATIONS

Esperado:

```text
NENHUMA
```

Se surgir proposta para persistir certification no banco:

primeiro provar por que:

```text
assessment derivado + artifact/versioned file
```

não basta.

---

# 48. TEST MATRIX

| Tipo | Obrigatório | Prova |
|---|---|---|
| unit | sim | fórmula/estado/applicability |
| invariant/property | sim | score 0–100, fail closed |
| corpus replay | sim | texto real |
| motor real | sim | não testa regex isolado |
| Tool Contract | sim | invocabilidade |
| positive control | sim | reconhece acerto |
| negative control | sim | reconhece erro |
| balanced control | sim | não overtrigger |
| mutation | sim | guarda realmente guarda |
| 73-route regression | sim | distribuição e drift |
| live evidence | sim | READY vs VALIDATED |
| PII | sim | registry/output seguro |
| relevant pytest | sim | P-226 drenada |
| global AAA gate | conforme v9 | regressão geral |

---

# 49. GATES POR BLOCO

## Bloco 0
- cinco falhas reproduzidas;
- 106 reproduzido;
- 102/106 reproduzido;
- eixo E=9 reproduzido e causa investigada;
- Tool Contract class reproduzida;
- GOLD cases confirmados/substituídos com evidência.

## Bloco A
- invariantes verdes;
- score 0–100;
- versionamento visível.

## Bloco B
- score alto + G5 fail → NOT_READY.

## Bloco C
- cinco xfails P-226 drenados;
- zero ajuste de expected sem causa.

## Bloco D
- READY/VALIDATED distintos;
- wrong-route/stale evidence não valida;
- zero PII.

## Bloco E
- inventário novo sem `AAA(106)` como certificação.

## Bloco F
- 73 rotas classificadas;
- toda mudança explicada;
- 19 não usado como target.

## Bloco G
- mutations críticas mortas;
- árvore restaurada;
- nenhuma mutation commitada.

---

# 50. DEFINITION OF DONE

A SPEC-089 só fecha quando:

- [ ] `RUBRIC_VERSION` explícita existe;
- [ ] score diagnóstico está entre 0 e 100;
- [ ] raw earned/applicable max continuam visíveis;
- [ ] score e certification são objetos diferentes;
- [ ] `INSTRUMENT_ERROR` existe;
- [ ] `UNMEASURABLE` existe;
- [ ] `NOT_ELIGIBLE_FOR_AAA` existe;
- [ ] `NOT_READY` existe;
- [ ] `AAA_READY` existe;
- [ ] `AAA_VALIDATED` existe;
- [ ] profiles de outcome são reconhecidos;
- [ ] N/A exige prova;
- [ ] UNKNOWN/ERROR não certificam;
- [ ] G0–G6 ou equivalentes medidos existem;
- [ ] Tool/Runtime Contract é hard gate;
- [ ] GOLD 6 prova score alto + gate fail;
- [ ] P-226 está drenada;
- [ ] cinco xfails não permanecem enterrados;
- [ ] guarda de órfã é causal;
- [ ] eixo E possui causa reproduzida;
- [ ] critical mutations ficam vermelhas;
- [ ] mutation runner não fail-open;
- [ ] live evidence registry não guarda PII;
- [ ] fingerprint existe;
- [ ] stale fingerprint invalida VALIDATED;
- [ ] máquina de lavar só é VALIDATED se evidence puder ser ligada honestamente;
- [ ] inventário v2 regenerado;
- [ ] todas as 73 rotas classificadas;
- [ ] mudanças de status explicadas;
- [ ] nenhum corredor foi alterado para “bater meta”;
- [ ] nenhum runtime paralelo;
- [ ] nenhuma LLM na régua;
- [ ] nenhuma migration desnecessária;
- [ ] execution report criado;
- [ ] delivery/push comprovado conforme Protocolo AAA v9 quando a execução ocorrer.

---

# 51. MÉTRICAS DE SUCESSO

Não usar quantidade de AAA como métrica primária.

Usar:

```text
false-pass controls killed ............. 100%
critical gate mutations killed ......... 100%
P-226 xfails restantes ................. 0
instrument invariant failures .......... 0
scores fora 0–100 ....................... 0
certificação com UNKNOWN/ERROR .......... 0
live evidence com PII ................... 0
rotas sem classificação explicável ...... 0
mudanças de status sem motivo ............ 0
```

Secundário:

```text
tempo da régua
tempo da bateria
quantidade por status
```

---

# 52. RELATÓRIO FINAL OBRIGATÓRIO

`SPEC-089-EXECUTION-REPORT.md` contém:

1. baseline real;
2. warm-up e premissas refutadas;
3. cinco P-226;
4. modelo final de assessment;
5. versionamento;
6. hard gates;
7. score;
8. inventory before/after;
9. tabela de mudanças;
10. GOLD cases;
11. mutations;
12. controls;
13. live evidence;
14. PII audit;
15. performance;
16. arquivos;
17. testes;
18. blockers/pendências;
19. commit final;
20. push/delivery.

---

# 53. AQUECIMENTO SUGERIDO AO CLAUDE CODE / CODEX

Antes da primeira edição, responder com evidência:

1. Qual é o máximo bruto atual?
2. Por que ele é 106?
3. Onde a documentação ainda chama isso de 100?
4. Quantas rotas o inventário chama AAA hoje?
5. Quantas têm prova live real?
6. Qual rota tem essa prova?
7. Por que denominator 96 envelheceu?
8. Por que exigir órfã permanente é um guarda ruim?
9. Por que o eixo E está 9?
10. Mostre a causa.
11. Como uma rota pode passar a rubrica e falhar o Tool Contract?
12. Qual código real prova isso?
13. Quais rotas possuem outcome `encaminha`?
14. A máquina de lavar pode ser ligada ao fingerprint atual?
15. Ache um modo de forjar N/A e aumentar score.
16. Ache um falso AAA que esta SPEC ainda não bloqueou.
17. Liste o que nesta SPEC está errado/desatualizado.
18. Liste o que você ainda não entendeu.

“Entendi tudo” não é resposta aceitável.

---

# 54. REFERÊNCIAS

## Internas

Ler sob demanda:

- `SPEC-083-a-regua-do-corredor.md`
- `SPEC-084-a-fabrica-de-rotas.md`
- `SPEC-084.1-o-ensaio.md`
- `SPEC-084.1-EXECUTION-REPORT.md`
- `SPEC-084.2-EXECUTION-REPORT.md`
- `backend/scripts/rubrica.py`
- `backend/scripts/medir_rota.py`
- `backend/tests/test_a_rubrica_e_honesta.py`
- `backend/tests/test_a_regua_nao_tem_furo.py`
- `INVENTARIO-DE-ROTAS.md`
- `PROTOCOLO-AUTOBROKERS-AAA.md`
- `PROTOCOLO-AAA-EVIDENCIAS.md`

## Externas — contexto completo no Research Pack

- Anthropic — *Demystifying evals for AI agents*
- LangSmith — *Trajectory evaluation*
- LangSmith — *Evaluation approaches*
- OpenAI — *Graders*
- Stryker — *Mutation testing*
- Hypothesis — *Property-based testing*

---

# 55. COMANDO FINAL AO EXECUTOR

Você NÃO está autorizado a interpretar esta SPEC como pedido para preservar notas históricas.

Sua obrigação é preservar:

```text
VERDADE
 ↓
CAUSALIDADE
 ↓
SEGURANÇA
 ↓
CAPACIDADE DE REPROVAR
 ↓
EVIDÊNCIA
```

Se a investigação provar que uma implementação proposta aqui está errada:

1. não obedeça cegamente;
2. reproduza a divergência;
3. preserve outcome e invariantes;
4. registre a correção no relatório;
5. implemente a alternativa mínima compatível.

> **A régua não existe para elogiar o corredor. Existe para impedir que o AutoBrokers chame de pronto aquilo que ainda pode falhar com um segurado.**
