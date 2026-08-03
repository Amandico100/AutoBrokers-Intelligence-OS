# Plano de execução do Atendimento — a sequência inteira

> **03/08/2026.** A ordem em que o atendimento fica pronto, do que já está no ar
> ao que ainda falta. **Este documento existe para nada se perder entre sessões.**
>
> Regra: nada sai daqui sem estar **feito e provado**, ou sem uma decisão
> registrada. Marcar ✅ exige gate verde e deploy verificado.

---

## ✅ CONCLUÍDO E NO AR

### SPEC-063 Blocos A · B · H · D · P · V · S · G · C · E · F
```
A  quem atende          papel exigido · sem agente = SILÊNCIO · CPF pela tool
B  handoff              chega em alguém, com dossiê, destino único por corretora
H  higiene              buffer com tenant · porta legada fechada · 10 env
D  observer             proibido como canal de saída
P  provisionamento      a corretora nasce completa · AutoFleet deixou de ser muda
V  canal                heartbeat que confirma antes de contestar
S  a ficha              fase e slots persistidos — não repergunta
G  conduta              12 playbooks destilados chegam ao turno (teto 2.600)
C  governador           4-8 min · tetos · janela · domingo · freio
E  acionamento          sai do Redis e vira Work Run
F  corredores           13 (eram 11) · vidros Azul/Porto/Zurich · HDI e Porto
                        residenciais · encanador Allianz · pane seca como alias
```

### Fase 0 — os consertos estruturais (valem para TODAS as seguradoras)
```
0.1  o clique de botão   937 cliques + 23 do formulário eram gravados VAZIOS
0.2  o formulário        schema capturado vira corredor · HDI e Yelum, um objeto
0.3  o freio residencial vazava mais na Yelum (4x) que na HDI (1x)
0.4  a fase humana       23 formas, 61 ocorrências — o detector pegava 3
0.6  a não-rota          slogan, pesquisa, horário saem da conta
0.8  a página            lê o CÓDIGO · 13 cards por seguradora×ramo
0.9  o banco de respostas  CEP, telefone, cor, destino — na hora, da ficha
0.10 declaração antecipada  o corredor diz tudo que vai pedir ANTES
0.11 o envelope do flow   ecoado da captura, nunca adivinhado
```

---

## ⛔ BLOQUEADO — espera ação física

| # | O quê | Quem | Destrava |
|---|---|---|---|
| **B1** | **Parear os 3 WhatsApps** | 🧑 | o re-sync, e com ele a cobertura real. [`RUNBOOK-RESYNC-DO-ATLAS.md`](RUNBOOK-RESYNC-DO-ATLAS.md) com a linha de base gravada |
| **B2** | **InfoCap** | 🧑 | confirmar apólice. Sem isso o agente pergunta a placa ao cliente |
| **B3** | **Separar o grupo de suporte** | 🧑 | o handoff está RECUSADO nas duas corretoras que dividem um grupo |

---

## ➡️ A SEQUÊNCIA, na ordem

### FASE 1 · O transporte do formulário nativo — ✅ **RESOLVIDO 03/08/2026**

📊 **A mensagem sai, e o WhatsApp aceita.** Provado no ar entre dois números
nossos: `Type: "InteractiveResponseMessage"`, ID `3EB07C9C74F4A217DE0477`.

```
1.0  ✅ o envelope se ECOA da captura, nunca se adivinha
1.1  ✅ patch 0005 — POST /send/interactiveResponse (a 13ª rota, nossa)
1.2  ✅ o build roda o teste do codificador · 4 testes Go
1.3  ✅ patch 0006 — o embrulho vira bandeira, para poder ser MEDIDO
1.4  ✅ A PROVA — 6 formas, 5 recusadas com 479, 1 aceita
1.5  ✅ o embrulho vira o padrão · a rota vira o padrão · a ponte liga
```

**A resposta: `DocumentWithCaptionMessage`.** O mesmo embrulho que os botões
usam. Sem ele o servidor recusa a mensagem inteira com 479 — *"Invalid stanza
sent"* — em silêncio para o cliente e com um número para nós.

E o que fez a diferença metodológica: **a primeira tentativa da bateria era
controle.** Ela deu 479 igual à rodada anterior, então o mérito é do embrulho e
de mais nada. Sem controle, um acerto se credita ao lugar errado.

📊 Desbloqueia **4 seguradoras** que já usam formulário (Porto 12 · HDI 6 ·
Azul 4 · Yelum 2) e as **460 apólices de auto** (26,9% da carteira) nelas.

**O que ainda NÃO está provado:** que a seguradora aceita a nossa resposta no
meio de um atendimento real. Provamos o transporte, não o desfecho. É o que a
Fase 3 mede, família por família.

### FASE 2 · Recolher o que a Fase 0 plantou
```
2.1  parear (B1) → history-sync → VERIFICAR → apagar → retecer
2.2  medir a cobertura real de cada seguradora
```

### FASE 3 · Família por família, até fechar
```
HDI + YELUM     primeira: auditada, 3.598 eventos, mesmo flow
                completar pneu · chaveiro · CEP · agendamento · táxi ·
                caminhão (8 telas) · e o residencial inteiro (~15 passos)
PORTO + ITAÚ    2.883 eventos, a maior
ALLIANZ         73% de cobertura, a mais madura
AZUL            vidros ABRE aqui (única)
BRADESCO · ZURICH · TOKIO · MAPFRE · ALFA
```
Cada família: auditar pelo método → corrigir mapa → completar corredor →
provar em modo teste.

### FASE 4 · O portal de reparos a 100%
```
4.1  provar o passo 7 (loja/domicílio) — nunca foi exercitado
4.2  variante e lado de peça
```

### FASE 5 · A central de agentes, auditada
Vigia · Sentinela · Cérebro adaptativo · Follow-up · Sentinela de Rotas ·
Alfaiate. Verificar orquestração e prazos.

---

## 📦 DEPOIS DO ATENDIMENTO — planejado, não iniciado

```
RAG da AutoFleet      parear → destilar → curar as conversas que faltam
RAG da SUSEP          + condições gerais das seguradoras
SPEC-064 pendências   P-13 a P-29 em PENDENCIAS.md
SPEC-065 a 069        o acervo · o Descobridor · prontidão e go-live
telefonia (Twilio)    P-53, sem prioridade — só depois do WhatsApp a 100%
```

---

## O método, para repetir em cada seguradora

```
1  ler as duas conversas inteiras (corretora auto + corretora não-auto)
2  reconstruir a árvore real à mão, com os rótulos literais
3  comparar com o mapa: acertou · errou · não viu
4  separar não-rota (Voltar/Sair/pesquisa/slogan/fala de humano)
5  conferir âncora por âncora contra a tela real
6  medir: quantos acionamentos completos seriam refeitos
7  corrigir o ESTRUTURAL antes do local
```

> **A lição da HDI: 90% do problema era estrutural.** Consertar uma vez
> consertou todas as seguradoras. Sempre procure o estrutural primeiro.
