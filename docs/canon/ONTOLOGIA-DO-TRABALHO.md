# A ontologia do trabalho — as quatro palavras

> **Documento canônico.** Lido no bootstrap de sessão (CLAUDE.md §2), junto com
> as SPECs. **v1.0 · 02/08/2026 · SPEC-064 Bloco A.**
>
> **Revoga** a interpretação da SPEC-019 de que *"Auxiliares = Rotinas"*.

---

## Por que este documento existe

O Founder disse estar confuso com o produto. **A auditoria provou que a confusão
não era dele.** Havia três sistemas diferentes se chamando "Auxiliar", e o menu
chamava de Auxiliares justamente aquele que não era.

Estava escrito em código, em uma linha:

```python
# backend/app/services/billing_collection.py
f"Auxiliar de Cobranca - {routine.get('name')}"
```

**Uma Rotina que se apresenta como "Auxiliar" numa string.**

Este documento existe para que **você, o corretor e qualquer LLM** digam, sem
hesitar, o que é cada coisa e onde ela mora.

---

## As quatro palavras

| Termo | Uma linha | O teste para saber |
|---|---|---|
| **Skill** | *como* se faz uma coisa | se **dois trabalhadores diferentes** podem usar, é Skill |
| **Rotina** | *quando* o trabalho acontece | se cabe em **"toda terça às 8h"**, é Rotina |
| **Auxiliar** | *quem* faz o trabalho | se aparece em **"o que trabalha para mim"**, é Auxiliar |
| **Artifact** | *o que* foi entregue | se o corretor **abre, guarda ou manda ao cliente**, é Artifact |

### A regra que desfaz a confusão

> ## Auxiliar **TEM** Rotina. Auxiliar **NÃO É** Rotina.

O produto tinha invertido isso: chamou a Rotina de Auxiliar e escondeu o
Auxiliar numa página sem link no menu.

---

## Os corolários, que valem como regra escrita

```
1. Rotina nunca existe sozinha. Toda Rotina pertence a um Auxiliar.

2. Um Auxiliar pode ter zero, uma ou várias Rotinas.
   Zero é legítimo: um Auxiliar que só roda quando o corretor pede no chat.

3. Uma Rotina pode aparecer em mais de uma categoria — mas roda UMA VEZ.
   Categoria é etiqueta, não pasta.

4. Skill não tem dono nem agenda. É procedimento.

5. Artifact é sempre o resultado de alguém, nunca o próprio trabalho.

6. O mesmo Auxiliar, chamado pela Rotina ou pelo chat, faz a MESMA coisa
   e produz o MESMO Artifact. Dois caminhos, um motor.
```

---

## Onde cada coisa mora

```
CATÁLOGO GLOBAL          auxiliary_templates
   o que a plataforma oferece a todas as corretoras
   escrito pelo admin, nunca pela corretora

INSTALAÇÃO               tenant_auxiliaries
   o que ESTA corretora ligou, com a configuração DELA
   a sobreposição local nunca toca o global

AGENDA                   routines
   quando cada trabalho daquele Auxiliar acontece
   pertence sempre a um tenant_auxiliary

PROCEDIMENTO             skills · skill_releases
   como se faz. Sem dono, sem agenda, reusável

ENTREGA                  artifacts · artifact_versions
   o que ficou pronto, com link e histórico

EXECUÇÃO                 work_runs
   toda execução, de qualquer caminho, passa por aqui
```

---

## As três camadas — global, corretora, usuário

**Esta é a estrutura que o Founder pediu, e vale para tudo:** memórias,
conectores, skills, auxiliares, conhecimento.

```
┌─ GLOBAL ─────────────────────────────────────────────────────┐
│  o que a AutoBrokers oferece a TODAS as corretoras            │
│  catálogo de auxiliares · skills · ferramentas · MCPs         │
│  conhecimento curado · playbooks de conduta                   │
│  escrito só pelo admin de plataforma                          │
└──────────────────────────────────────────────────────────────┘
                            ↓ herda
┌─ CORRETORA ──────────────────────────────────────────────────┐
│  o que ESTA corretora tem, e só ela                           │
│  conexões e credenciais · memórias da corretora               │
│  quais auxiliares ligou e com que configuração                │
│  seus canais, seus números, seus corredores                   │
│  NUNCA visível a outra corretora                              │
└──────────────────────────────────────────────────────────────┘
                            ↓ herda
┌─ USUÁRIO ────────────────────────────────────────────────────┐
│  o que ESTE usuário da corretora tem                          │
│  memórias dele · preferências · canais próprios               │
│  o que os auxiliares já entregaram a ele                      │
└──────────────────────────────────────────────────────────────┘
```

**A regra de sobreposição, em uma frase:**

> **O de baixo sobrepõe o de cima. Mudar o de cima nunca apaga a sobreposição do
> de baixo. Mudar o de baixo nunca toca o de cima.**

---

## Os erros já cometidos — para não repetir

Cada um destes foi medido no sistema, não imaginado.

### 1. Chamar Rotina de Auxiliar no menu

`/dashboard/auxiliares` mostrava dois cards — *"Rotinas prontas"* e *"Minhas
rotinas"* — com o subtítulo *"Rotinas inteligentes que rodam sozinhas"*. Os
Auxiliares de verdade estavam em `/dashboard/auxiliares/meus`, **sem link no
menu.**

### 2. Promover Auxiliar a pilar de menu

**Briefing** e **Pesquisas** eram pilares de primeiro nível. Os dois são, por
definição, Auxiliar e Skill. E o comentário no mesmo arquivo dizia: *"a regra que
fica: **o menu não cresce**."*

### 3. Dar página própria ao auxiliar novo

A galeria tinha a rota dinâmica `[slug]` **e mais duas páginas escritas à mão** —
`follow-up-whatsapp` e `resumo-atendimentos`. Os dois únicos auxiliares reais
ganharam página própria ao lado do caminho genérico.

> **É assim que a bagunça se reproduz: cada peça nova acha que é exceção.**

### 4. Construir o motor e não ligar em nada

Medido em 02/08/2026:

```
tool_invocations ....... 0     research_requests ..... 0
work_effects ........... 0     company_memories ...... 0
briefings entregues .... 0     de 26 publicados
auxiliares rodando ..... 0     há 52 dias
```

**As máquinas existiam. Nenhuma estava ligada na outra.**

### 5. Deixar o campo mentir no nome

O extrator do portal batizava *valor de parcela vencida* como `premio` e
*comissão daquela parcela* como `comissao`. Um relatório inteiro foi lido errado
por causa disso, e a conclusão errada atravessou seis documentos.

> **Se o nome do campo mente, conserte o campo — não só o texto.**

---

## Como decidir onde uma coisa nova mora

```
É um procedimento que dois trabalhadores diferentes podem usar?
   → SKILL. Registra em skills. Sem dono, sem agenda.

É um trabalhador que o corretor liga e desliga?
   → AUXILIAR. Entra no catálogo global, visível a todas, desligado.

É "toda terça às 8h"?
   → ROTINA. Pertence a um Auxiliar. Nunca existe sozinha.

É o que o corretor abre, guarda ou manda ao cliente?
   → ARTIFACT. Aparece em Entregas, com link.

É um poder governável (pode ser negado, exige aprovação)?
   → CAPABILITY. Registra em capabilities, com provedor real.

Não é nenhum dos cinco?
   → PARE. Provavelmente é um dos cinco com outro nome.
     Se realmente não for, registre em FOUNDER-DECISIONS.md
     antes de criar a sexta coisa.
```

---

## O que nunca pode acontecer

```
✗ Rotina sem Auxiliar dono
✗ Auxiliar nascendo fora do catálogo
✗ Auxiliar novo com página escrita à mão
✗ Auxiliar nascendo ligado
✗ Auxiliar visível a uma corretora e invisível a outra sem decisão explícita
✗ configuração de corretora escrita no template global
✗ dois documentos com duas definições do mesmo termo
✗ tela mostrando coluna alimentada por tabela vazia
```

---

*Autoridade: CLAUDE.md §6 (ontologia) · SPEC-052 · SPEC-053 · SPEC-056 ·
SPEC-058 · SPEC-064.*
