# SPEC-089 — RESEARCH PACK
## A Régua AAA é Honesta

**Data:** 25/08/2026  
**Baseline do repositório consultado:** `8b49fdb337a6c37eb2ad181f5bad544a55dc0827`  
**Uso:** referência de investigação e decisões. Não deve entrar inteira no bootstrap do executor.  
**SPEC associada:** `SPEC-089-a-regua-aaa-e-honesta.md`

---

# 1. PERGUNTA CENTRAL

Como transformar a atual régua de corredores do AutoBrokers em um instrumento que:

- mede progresso;
- certifica release;
- resiste a false-pass;
- não premia ausência de evidência;
- não pune comportamento correto;
- não depende de verdades históricas congeladas;
- permanece auditável quando os critérios evoluem;
- diferencia “pronto em replay” de “validado no mundo real”;
- pode ser consumido futuramente por Route Self-Healing, Factories e MetaHarness?

---

# 2. CONCLUSÃO DA PESQUISA

A melhor solução não é:

> “arrumar a nota”.

É separar três funções:

```text
MEASUREMENT INSTRUMENT
        +
RELEASE GATE
        +
LIVE EVIDENCE
```

O score diz:

> **quanto das evidências aplicáveis conquistamos?**

Os gates dizem:

> **há alguma condição que proíbe chamar isto de pronto?**

A prova live diz:

> **o mundo real confirmou esta release?**

Essa separação é o ponto arquitetural principal da SPEC-089.

---

# 3. ESTADO REAL DO REPOSITÓRIO

## 3.1 SPEC-083

A SPEC-083 criou a régua depois de uma rota real passar e uma auditoria encontrar quatro furos.

Princípios preservados:

> **Ponto só se ganha contra o corpus.**

> **Teste de corredor chama o motor.**

A régua nasceu explicitamente para evitar “teste bonito que não prova produto”.

## 3.2 `rubrica.py`

No baseline:

```text
A Evidência ..... 20
B Cobertura ..... 35
C Segurança ..... 26
D Conhecimento .. 10
E Prova ......... 15
                  ---
                  106
```

O cabeçalho ainda fala em “PRONTIDÃO 100”.

Causa conhecida:

C7 acrescentou +6 ao eixo C posteriormente.

O objeto `Nota` atual calcula:

```text
pontos = soma dos earned aplicáveis
denominador = soma dos max aplicáveis
fracao = pontos / denominador
```

e o patamar:

```text
AAA >=95%
quase >=80%
parcial >=55%
esqueleto >=25%
```

Assim, `102/106` é ~96,2%, não 102%.

O problema é semanticamente mais profundo:

- instrumento evoluiu sem versionamento;
- documentação/testes ficaram presos em versão antiga;
- score virou autorização;
- critérios externos à soma apareceram depois.

## 3.3 Inventário atual

`INVENTARIO-DE-ROTAS.md`, gerado em 24/08/2026:

- 543 sessões;
- 10 seguradoras;
- 73 rotas;
- 19 rotas no patamar AAA;
- denominadores como 106, 100, 96, 94 e 88.

A decisão atual de mostrar denominador real é boa: evita esconder que rotas tiveram critérios inaplicáveis.

A SPEC-089 preserva isso:

```text
score_pct
+
raw earned / applicable max
+
profile
+
gates
```

## 3.4 SPEC-084.1

O Ensaio terminou com:

```text
1 → 19 rotas AAA
média ponderada 88,4%
```

e aproximadamente 21 consertos na própria régua.

Casos documentados:

- handoff correto contado como órfã;
- item impossível de ganhar;
- medir rota escrevendo no corredor;
- mutation commitada;
- janela de leitura vazando para vizinho;
- herança comprando crédito errado;
- native flow saindo do denominator.

Lição:

> **a régua é software de produção de decisão e precisa de avaliação própria.**

## 3.5 SPEC-084.2

Achado mais importante:

```text
19 rotas consideradas AAA
+
100% das telas respondidas
+
100% determinismo
+
0/19 passando o Tool Contract inicialmente
```

O corredor estava certo.

O contrato de entrada não conseguia carregar dados necessários.

Isso prova:

```text
route quality
!=
runtime executability
```

e justifica G5 como hard gate.

## 3.6 P-226

`test_a_rubrica_e_honesta.py` registra cinco `xfail(strict=True)`:

1. denominator antigo;
2. órfã permanente;
3. fixture/state envelhecido;
4. eixo E 15→9;
5. teto 100 hard-coded.

Eles representam drift da avaliação, não uma única falha.

---

# 4. ACHADO — CONTROLE QUE EXIGE PRODUTO IMPERFEITO

Um dos guardas atuais diz, essencialmente:

> “o replay precisa continuar achando alguma órfã; se não achar, talvez a medida tenha afrouxado.”

Isso foi útil como alerta temporário.

Mas é um anti-pattern permanente.

Se todas as órfãs forem corretamente eliminadas, o teste acusa a melhoria.

## Solução causal

```text
tela real conhecida
↓
RESPONDIDA

desliga o passo que responde
↓
ORFA_FUNCIONAL

restaura
↓
RESPONDIDA
```

Essa prova é superior porque mede **sensibilidade causal do instrumento**.

---

# 5. ACHADO — SCORE E GATE SÃO FUNÇÕES DIFERENTES

Uma soma ponderada é excelente para:

- mostrar progresso;
- priorizar;
- hill-climbing;
- explicar o que falta.

Ela é ruim para representar:

> “uma condição fatal”.

Exemplo:

```text
Safety 0
Coverage 100
Evidence 100
Proof 100
```

A média pode permanecer alta.

Mas um sistema que chuta resposta de segurança não é AAA.

Portanto:

```text
weighted diagnostic
+
binary release gates
```

é a arquitetura escolhida.

---

# 6. ANTHROPIC — DEMYSTIFYING EVALS FOR AI AGENTS

**Fonte:** Anthropic Engineering, 09/01/2026  
**Título:** *Demystifying evals for AI agents*

## 6.1 Outcome ≠ transcript

A taxonomia separa:

- task;
- trial;
- grader;
- transcript/trajectory;
- outcome;
- eval harness.

A lição:

um agente pode dizer que concluiu e o estado real dizer o contrário.

### Verticalização

Para `AAA_VALIDATED`:

```text
não basta:
“o chat disse que abriu”

precisa:
outcome real + referência verificável
```

## 6.2 Weighted / binary / hybrid

A Anthropic trata explicitamente essas estratégias como diferentes.

### Verticalização

AutoBrokers usa:

```text
weighted diagnostic
+
binary hard gates
```

## 6.3 Deterministic graders first

Onde houver estado/code/verificação determinística, priorizar isso.

### Verticalização

Corredores possuem:

- corpus;
- parser;
- motor;
- tool contract;
- mutation;
- expected outcomes.

Portanto LLM judge dentro da régua seria adicionar variância desnecessária.

## 6.4 Capability vs regression eval

Capability:

> “consegue fazer?”

Regression:

> “continua fazendo?”

Regression deve ser muito rigorosa.

### Verticalização

Score ajuda capability improvement.

Hard gate protege regression.

## 6.5 Golden cases

Ter caso conhecido que passa prova que o grader é solucionável.

### Verticalização

A rota da máquina de lavar é candidata a positive golden case, mas o warm-up precisa reproduzir.

## 6.6 Balanced cases

Testar positivos e negativos.

### Verticalização

Não basta:

```text
reconhece handoff
```

precisa:

```text
reconhece handoff real
NÃO reconhece resolução como handoff
```

## 6.7 Grader loopholes

Avaliações podem ser “jogadas”.

### Histórico AutoBrokers

Já aconteceu em formas equivalentes:

- comentário comprando crédito;
- campo declarado;
- herança;
- N/A;
- flow saindo da conta.

Por isso o Red Team da 089 recebe a missão:

> **consiga um falso AAA.**

## 6.8 pass@k / pass^k

Para sistemas voltados a clientes, consistência ao longo de tentativas importa.

### Verticalização

Não inventar estatística com 1 caso live.

Mas registry deve guardar tentativas para permitir análise futura.

---

# 7. LANGSMITH / AGENTEVALS — TRAJECTORY EVALUATION

**Fontes:** LangSmith docs, trajectory evaluation e evaluation approaches.

Modos comuns:

```text
strict
unordered
subset
superset
```

A lição:

> sequência exata não é sempre o que define sucesso.

Uma rota pode chegar ao outcome correto por caminhos válidos diferentes.

### Verticalização

AAA não exige:

> “repita exatamente a conversa da Clarissa”.

AAA exige:

- estados necessários;
- segurança;
- ausência de ações proibidas;
- outcome correto.

---

# 8. OPENAI — GRADERS

A API atual de graders diferencia/compõe:

- string checks;
- similarity;
- model scoring;
- multi-grader.

A lição útil aqui não é instalar nada.

É reforçar:

> **composição de avaliação deve ser explícita.**

A SPEC-089 explicita:

```text
credits
vs
gates
```

---

# 9. MUTATION TESTING

Referências:

- Stryker Mutator;
- Microsoft mutation testing guidance.

Princípio:

```text
introduzir defeito deliberado
↓
teste deve falhar
```

Também é importante não perseguir “100% mutation score” indiscriminadamente.

### Verticalização

Foco em mutações críticas:

- safety;
- protocol/outcome;
- Tool Contract;
- flow/handoff;
- N/A;
- fail-open do avaliador;
- live evidence identity.

Isso combina com o que o AutoBrokers já faz.

---

# 10. PROPERTY-BASED TESTING

Referência: Hypothesis.

Princípio:

> testar propriedades que devem ser verdadeiras para uma classe de inputs.

### Verticalização

Propriedades valiosas:

```text
score ∈ [0,100]
earned <= max
erro não aumenta score
UNKNOWN não certifica
N/A sempre tem motivo
```

Decisão:

não instalar Hypothesis só por esta SPEC.

Usar se já estiver disponível e trouxer ganho claro.

Caso contrário, fixtures/loops determinísticos.

---

# 11. FALSE PASS É A FALHA MAIS CARA

Para o AutoBrokers:

```text
FALSE FAIL
→ alguém investiga de novo

FALSE PASS
→ rota defeituosa pode chegar ao segurado
```

Portanto a certificação é desenhada para minimizar falso positivo de release.

O diagnóstico pode dar partial credit.

O release gate não.

---

# 12. ALTERNATIVAS DESCARTADAS

| alternativa | nota | por que não |
|---|---:|---|
| voltar pesos brutos para exatamente 100 | 45/100 | arbitrário; trata sintoma |
| `min(score, 100)` | 0/100 | esconde instrumento inválido |
| somente exibir 102/106 como 96,2 | 55/100 | não resolve gates/versioning/live |
| `AAA = score >=95` somente | 30/100 | falha crítica pode ser compensada |
| tudo binário, sem score | 70/100 | perde diagnóstico/hill-climbing |
| LLM-as-judge dentro da régua | 25/100 | variância desnecessária |
| framework de eval novo | 15/100 | autoridade paralela sem ganho |
| preservar 19 AAA como meta | 0/100 | incentiva gaming |
| consertar rota durante a 089 | 10/100 | mistura instrumento e objeto medido |

---

# 13. POR QUE SCORE NORMALIZADO + RAW DENOMINATOR

O inventário atual rejeita reescala por um motivo correto:

```text
61/86 = 71%
65/100 = 65%
```

A primeira rota pode parecer melhor porque teve menos critérios.

A solução não é abandonar score_pct.

É mostrar os dois:

```text
score diagnóstico .... 70,9%
raw .................. 61/86 aplicáveis
profile .............. RESOLVE
gates ................ ...
```

A comparação nunca deve ignorar profile/gates/applicability.

---

# 14. POR QUE PERFIL DE OUTCOME

O código atual reconhece casos em que a seguradora:

> encaminha por link

em vez de abrir protocolo naquele canal.

Cobrar protocolo é errado.

Dar o mesmo AAA também é errado.

Solução:

```text
diagnóstico universal
+
certificação compatível com a promessa
```

Nesta SPEC:

```text
RESOLVE → elegível a AAA
ENCAMINHA → não elegível a AAA
HANDOFF_BY_DESIGN → não elegível a AAA
```

Futuras SPECs podem criar certificações próprias para outros perfis.

---

# 15. POR QUE AAA_READY VS AAA_VALIDATED

Replay prova:

- parsing;
- coverage;
- deterministic decisions;
- safety;
- Tool Contract em ambiente controlado;
- mutation.

Replay não prova integralmente:

- rede real;
- Meta/WhatsApp real;
- bot real da seguradora naquele momento;
- sessão real;
- mudança de URA de última hora;
- external state.

Então:

```text
AAA_READY
= engineering proof

AAA_VALIDATED
= engineering proof + live outcome evidence
```

---

# 16. POR QUE ROUTE FINGERPRINT

Sem fingerprint:

```text
validamos uma release
↓
editamos a rota
↓
selo continua
```

Isso é falso.

Um hash estável do conteúdo operacional liga:

```text
evidence
↔
release realmente testada
```

Não precisa de infraestrutura pesada.

---

# 17. POR QUE TOOL CONTRACT É HARD GATE

A SPEC-084.2 é a evidência interna mais forte.

Antes do conserto:

```text
corredor bom
+
rubrica boa
+
input contract incapaz
=
produto não executa
```

Logo:

> uma rota “pronta para o AutoBrokers” precisa ser invocável pelo AutoBrokers real.

---

# 18. O TESTE MAIS IMPORTANTE DA SPEC-089

Não é:

```text
assert score <=100
```

É:

```text
rota excelente
score >=95

QUEBRA SOMENTE O TOOL CONTRACT

score continua alto
G5 cai
certification = NOT_READY
```

Se isso não acontecer, score e autorização continuam misturados.

---

# 19. SEGUNDO TESTE MAIS IMPORTANTE

```text
corredor sem órfãs
↓
desliga passo real
↓
surge órfã
↓
restaura
↓
zero órfãs novamente
```

Isso elimina o guarda que exige defeito permanente.

---

# 20. RISCOS

## R1 — overengineering

Mitigação:

- zero framework novo;
- zero LLM;
- zero DB esperado;
- reusar módulos.

## R2 — “caiu AAA, vamos arrumar rota”

Mitigação:

- corredor fora de escopo;
- queda gera pendência.

## R3 — fingerprint histórico inventado

Mitigação:

```text
historical_unbound
```

## R4 — N/A gaming

Mitigação:

- rule + reason + evidence;
- detector error = UNKNOWN.

## R5 — tudo virar hard gate

Mitigação:

hard gate somente quando descumprimento invalida a promessa AAA.

## R6 — perda de histórico

Mitigação:

- raw antigo preservado;
- rubric version;
- before/after no mesmo snapshot quando necessário.

---

# 21. O QUE O WARM-UP PRECISA DESCOBRIR

1. causa exata de E=9;
2. lista atual de outcomes `encaminha`;
3. se o fingerprint histórico da máquina de lavar é reconstruível;
4. se existe item impossível de ganhar;
5. se existe item sempre ganho;
6. se algum N/A atual é na verdade UNPROVEN;
7. se há outra superfície crítica fora do score além do Tool Contract;
8. se CLI já tem JSON reaproveitável;
9. quais arquivos mínimos precisam ser tocados;
10. se há qualquer mudança após baseline desta Candidate Spec.

---

# 22. REFERÊNCIAS INTERNAS INSPECIONADAS

- `backend/scripts/rubrica.py`
- `backend/scripts/medir_rota.py`
- `backend/tests/test_a_rubrica_e_honesta.py`
- `backend/tests/test_a_regua_nao_tem_furo.py`
- `docs/canon/specs/SPEC-083-a-regua-do-corredor.md`
- `docs/canon/specs/SPEC-084-a-fabrica-de-rotas.md`
- `docs/canon/specs/SPEC-084.1-o-ensaio.md`
- `docs/canon/reports/SPEC-084.1-EXECUTION-REPORT.md`
- `docs/canon/reports/SPEC-084.2-EXECUTION-REPORT.md`
- `docs/canon/reports/INVENTARIO-DE-ROTAS.md`
- `docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md`
- `docs/canon/PROTOCOLO-AAA-EVIDENCIAS.md`
- referências P-226 / SPEC-089 na frente da SPEC-085

---

# 23. REFERÊNCIAS EXTERNAS

## Anthropic
**Demystifying evals for AI agents**  
https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents

Uso:
- outcome vs trajectory;
- hybrid scoring;
- deterministic graders;
- golden cases;
- balanced cases;
- grader loopholes;
- pass@k/pass^k.

## LangSmith
**Trajectory evaluation**  
https://docs.langchain.com/langsmith/trajectory-evals

**Evaluation approaches**  
https://docs.langchain.com/langsmith/evaluation-approaches

Uso:
- strict/subset/superset;
- não congelar caminho exato quando há múltiplas soluções válidas.

## OpenAI
**Graders**  
https://platform.openai.com/docs/api-reference/graders

Uso:
- referência de composição explícita de graders.
- não será dependência da SPEC.

## Stryker Mutator
https://stryker-mutator.io/docs/

Uso:
- mutation testing;
- foco em critical mutants.

## Hypothesis
https://hypothesis.readthedocs.io/

Uso:
- property-based invariants;
- somente se já fizer sentido na base.

---

# 24. DECISÕES CONGELADAS

| decisão | resposta |
|---|---|
| score 0–100 | SIM |
| raw earned/max visível | SIM |
| score != certification | SIM |
| hard gates | SIM |
| certification binária | SIM |
| AAA_READY | SIM |
| AAA_VALIDATED | SIM |
| N/A com prova | SIM |
| UNKNOWN fail-closed | SIM |
| versionar rubrica | SIM |
| route fingerprint | SIM |
| live registry sem PII | SIM |
| Tool Contract gate | SIM |
| LLM judge na régua | NÃO |
| novo framework | NÃO |
| migration | NÃO esperada |
| preservar 19 AAA como meta | NÃO |
| alterar corredor para pontuar | NÃO |

---

# 25. IMPACTO NO ROADMAP

## SPEC-087

Poderá fazer:

```text
candidate patch
↓
assessment before/after
↓
hard gates
↓
só promove se não regredir
```

## SPEC-090

Candidato não vira rota pronta porque “tem 97”.

Precisa:

```text
profile elegível
+
AAA_READY
```

## SPEC-108

MetaHarness poderá consumir `RouteAssessment` JSON e rubric version.

---

# 26. VEREDITO

**Qualidade da ideia original “consertar a régua”: 100/100.**

Mas o conserto correto não é cosmético.

É fazer a régua evoluir de:

```text
pontuação + patamar
```

para:

```text
instrumento versionado
+
score diagnóstico
+
hard gates
+
evidência de release
+
certificação real
```

Esse desenho preserva o melhor da SPEC-083 e elimina a classe de problema revelada pelas SPECs 084.1 e 084.2.
