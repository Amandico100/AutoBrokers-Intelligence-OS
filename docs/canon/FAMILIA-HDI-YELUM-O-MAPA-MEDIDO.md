# Família HDI + Yelum — o mapa medido

> **03/08/2026.** O roteiro real do menu de WhatsApp da família HDI/Yelum,
> extraído do Atlas. É o insumo da Fase 3: **não se obtém lendo código**, só
> medindo o que foi observado.
>
> 📊 Tudo aqui saiu de `ura_maps` (status `observed`) e `observed_events` no
> banco de produção `dcajcvlzcjbmyapmklil`.

---

## 1. O tamanho do problema

```
              nós   URA   humano   opções   cobertas   cobertura
HDI           440   387       53      225         82        36%
YELUM         545   492       53      277         95        34%
```

📊 **HDI 2.074 eventos em 38 sessões · Yelum 3.026 em 83.** Juntas, 5.100
eventos e 121 atendimentos observados — a segunda maior base do acervo, atrás
só da Allianz (que tem volume mas 📊 apenas 23 interativos, contra 1.951 da
família).

**A leitura:** o mapa é rico e a cobertura é baixa. Não falta observação —
falta o corredor saber responder ao que já foi observado. 📊 143 opções na HDI
e 182 na Yelum ainda não têm resposta declarada.

---

## 2. 📊 As duas são o mesmo bot — menos na porta

Verificado nó a nó: o texto dos menus é **literalmente igual** nas duas, com
uma exceção.

| | HDI | Yelum |
|---|---|---|
| **abertura** | *"Olá, seja bem-vindo ao atendimento digital de **Assistência 24 horas** do **Grupo HDI!**"* — informativo, **0 opções** | *"**Olá, tudo bem?** Seja Bem-vindo ao canal exclusivo para Segurado e Terceiros"* — menu, **3 opções** |
| **agora ou agendar** | *"Você está solicitando o atendimento para agora ou prefere agendar para um outro momento?"* | *"Você **quer** o atendimento para agora ou prefere agendar para outro momento?"* |
| **todo o resto** | idêntico | idêntico |

> ✅ O regex da família — `atendimento (?:para )?agora ou prefere agendar` —
> casa **as duas** redações. Verificado contra o texto literal de cada uma.
> Era o risco silencioso: um freio que só pega uma das irmãs deixa a outra
> passar direto pelo ponto sem volta.

**Consequência para o corredor:** a entrada precisa de tratamento por
seguradora; do segundo passo em diante, um roteiro só serve para as duas.

---

## 3. 📊 O roteiro real, na ordem observada

Cada linha é um nó do Atlas, com quantas vezes apareceu.

```
 8×  "Maria em qual dessas opções você se enquadra?"
        Sou segurado(a) · Sou corretor(a) · …                    IDENTIDADE
 7×  "Identifiquei em seu cadastro a placa {PLACA}. Deseja
        continuar com o atendimento para o veículo…"             CONFIRMA VEÍCULO
13×  "Você gostaria de solicitar serviços de assistência para
        seu *automóvel* ou *residência*?"                        RAMO
13×  "Pode me dizer o que aconteceu? … Pane ou Defeito …" (7)    SUBSERVIÇO
13×  "poderia me informar a cor do veículo de placa {PLACA}"
        Branco · Prata/Cinza · … (6)                             DADO
10×  "Selecione uma das opções para informar o endereço onde
        o veículo está agora. Digitar endereço · Compartilhar…"  DADO
20×  "Você confirma o endereço?"           Sim · Não · Voltar    CONFIRMAÇÃO
10×  "Você confirma este endereço?"        Sim · Não · Voltar    CONFIRMAÇÃO
10×  "…informe para onde devemos levar o veículo"  (3)           DESTINO
20×  "O número de telefone {CPF} está correto?"  Sim·Não·Voltar  CONFIRMAÇÃO
 9×  "…os ocupantes tem alguma das particularidades…"
        Criança · Idoso · Gestante · … (7)                       DADO
 7×  "…o veículo está em uma rodovia?"     Sim · Não · Voltar    DADO
 7×  "você é a pessoa que está local para acompanhar o serviço?" DADO
17×  "Deseja continuar este atendimento?"  Sim · Não             CONTINUIDADE
 9×  "Você está solicitando o atendimento para agora ou
        prefere agendar…"                                        🛑 DECISÃO
```

**E as duas que NÃO são rota** — pesquisa de satisfação, depois do atendimento:

```
 9×  "O quão satisfeito você está com o atendimento do Whatsapp?" (5)
 8×  "O que achou do atendimento prestado pelo nosso analista?"   (5)
```

> Contá-las como opções não cobertas **rebaixa a cobertura sem que exista
> trabalho a fazer**. É o mesmo defeito da Fase 0.6 (slogan, horário, "Voltar"),
> e aqui ele reaparece em duas opções × 5 escolhas × 2 seguradoras = **20
> opções fantasmas** nos 36%/34% acima.

---

## 4. O que isto diz sobre o trabalho

**A maior parte do roteiro é DADO, não escolha.** Cor do veículo, endereço,
telefone, ocupantes, rodovia, quem acompanha — tudo isso já está na ficha do
atendimento ou é pergunta fechada. É exatamente o que o **banco de respostas
determinístico** (Fase 0.9) resolve sem acordar o Cérebro.

**Três são confirmação pura** (`Sim · Não · Voltar`), e aparecem **50 vezes** —
o par mais frequente do mapa inteiro.

**Uma é o ponto sem volta:** *agora ou agendar*. 📊 É onde o freio precisa
segurar, e é por isso que ela **não** pode ser respondida pelo banco de
respostas — foi a correção que um subagente me apontou e estava certo.

---

## 5. O que fazer na Fase 3 — na ordem

```
3.1  descontar a NÃO-ROTA da cobertura      as 2 pesquisas de satisfação
     (20 opções fantasmas nas duas)          já existe o mecanismo da Fase 0.6

3.2  o par Sim/Não/Voltar como padrão       50 ocorrências, um tratamento só

3.3  ligar o banco de respostas aos 6       cor · endereço · telefone ·
     nós de DADO                             ocupantes · rodovia · acompanha

3.4  a entrada por seguradora               HDI informativo × Yelum menu de 3

3.5  medir de novo                          a cobertura tem de subir, e a
                                             conta tem de bater com 3.1
```

**O critério de pronto:** um acionamento de guincho da HDI percorrido do começo
ao fim em modo teste, sem parar em nenhum nó por falta de resposta declarada.

---

## 6. O que este documento NÃO prova

- 💭 Que a cobertura de 36% é o número certo depois de descontar a não-rota.
  Só a medição 3.5 diz.
- 🔴 Que o corredor **responde** certo nesses nós. O mapa diz o que a seguradora
  pergunta; o corredor é outro arquivo, e é o que a Fase 3 escreve.
- 🔴 Que a seguradora aceita as respostas. Isso é o teste ao vivo, e depende do
  formulário nativo já resolvido — ver
  [`O-FORMULARIO-NATIVO-RESOLVIDO.md`](O-FORMULARIO-NATIVO-RESOLVIDO.md) §7.
