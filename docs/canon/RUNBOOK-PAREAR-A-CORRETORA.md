# Parear o WhatsApp de uma corretora — o passo a passo

> **04/08/2026.** A Saionara (Resulta) e a Regina (AutoFleet) vão parear os
> **celulares oficiais de atendimento** das corretoras.
> Irmão do [`RUNBOOK-PAREAR-SEM-CONTAMINAR.md`](RUNBOOK-PAREAR-SEM-CONTAMINAR.md),
> que trata do caso oposto: parear um telefone **pessoal**. **Os dois casos têm
> regras diferentes — confira qual é o seu antes de seguir.**
> **Autoridade:** [D-Observador-02](FOUNDER-DECISIONS.md) · [D-Canal-01](FOUNDER-DECISIONS.md)

---

## O que muda em relação ao telefone pessoal

| | Telefone pessoal | **Telefone da corretora** |
|---|---|---|
| O que é | prova técnica | 🟢 **canal oficial de atendimento** |
| Escopo | `insurers_only` | 🟢 **`insurers_and_clients`** |
| Conversas com segurado | não devem ser gravadas | 🟢 **são o material das cartas** |
| Onde mora o cuidado | na **captura** | 🟢 na **destilação** |

Decisão do Founder, literal:

> *"Sempre que for conectado um WhatsApp no atendimento e acionamento da
> corretora, esse celular deve ser tratado como telefone oficial de atendimento
> e deve baixar as conversas. Mas é preciso ter cuidado com conversas pessoais
> que não vão aumentar a inteligência do nosso cérebro — não precisamos ter
> milhões de cartas."*

---

## Antes de chamar a Saionara e a Regina

Tudo abaixo foi conferido em 04/08. Marque o que ainda não estiver feito.

| # | Item | Estado |
|---|---|---|
| 1 | Escopo `insurers_and_clients` nas três integrações | ✅ gravado |
| 2 | Grupo de suporte **por corretora** (não compartilhado) | 🧑 **falta** — o Founder vai criar |
| 3 | Agentes de atendimento **desligados** | ✅ os quatro |
| 4 | Modo observação mudo de verdade | ✅ dois furos fechados |
| 5 | Cruzamento de tenant fechado | ✅ |
| 6 | Reconector automático no ar | ✅ |
| 7 | Repareamento **sem duplicar** o que já foi baixado | ⏳ em execução |

🔴 **O item 2 é o único que bloqueia o handoff.** Sem grupo próprio, *"quero
falar com uma pessoa"* não aciona ninguém — o roteador recusa destino
compartilhado de propósito, para não entregar o CPF de um segurado na corretora
errada.

---

## O passo a passo

### 1 · O Founder cria os grupos (uma vez, por corretora)

Um grupo de WhatsApp **por corretora**, com as pessoas que atendem. Depois,
cada corretora aponta o dela em **Personalização → Corretora → Suporte humano**.

📊 Os dois compartilhados foram removidos em 04/08. A AMANDUS já tem o dela e
não foi tocada.

### 2 · Cada corretora pareia o próprio número

Na conta dela: **Personalização → Corretora → WhatsApp → Gerar QR code**.

O que ela vai ver, e o que cada coisa significa:

```
"Desconectado"    ainda não pareou            -> mostra o QR
"Reconectando…"   a sessão existe, o socket caiu -> NÃO precisa fazer nada
"Conectado"       está funcionando
```

⚠️ **Se aparecer "Conectado" sem ela ter pareado**, pare e me chame. Significa
que outra sessão está viva naquele canal — foi o que aconteceu com a Regina em
29/07.

### 3 · O celular continua funcionando normalmente

Ninguém precisa mudar rotina. A atendente segue respondendo pelo celular; o
sistema observa e aprende, **em silêncio**.

### 4 · Conferir que capturou

Depois de alguns minutos de conversa real, eu confiro:
- as conversas novas aparecendo em `attendance_transcripts`
- **sem duplicar** o que já estava lá
- e nenhuma mensagem saindo pelo número pareado

### 5 · O agente continua DESLIGADO

📊 Os quatro estão `is_active = false`, e é assim que ficam. O botão
**"Ligar agente"** existe e está visível — mas ele só é apertado quando o
Founder decidir.

> Enquanto estiver desligado: o agente **não atende segurado, não aciona
> seguradora por WhatsApp e não abre portal de vidros.** Os agentes de bastidor
> (Observador, Tecelão do Atlas, Vigias) trabalham normalmente, calados.

---

## Quando apertar "Ligar agente"

**Só depois de:** grupo de suporte próprio configurado (item 2) e a allowlist de
entrada esvaziada ([P-86] — hoje ela atende só um número, o que é ótimo para
teste e armadilha no go-live).

E aí, no mesmo instante:
- o agente responde os segurados
- aciona as seguradoras pelos corredores ativos
- abre atendimento no portal de vidros, **ponta a ponta**
- e chama gente quando trava

---

## O que NÃO fazer

1. **Parear sem grupo de suporte próprio.** O handoff é a última rede.
2. **Ligar o agente com a allowlist preenchida.** Ele atende um número e ignora
   o resto **em silêncio** — botão verde, nada acontecendo.
3. **Gerar QR novo quando a tela diz "Reconectando…".** O QR novo invalida a
   sessão boa e obriga a corretora a pegar o celular de novo.
4. **Rodar a destilação antes de conferir que não duplicou.** Ver
   [`RUNBOOK-A-NOITE-DA-DESTILACAO.md`](RUNBOOK-A-NOITE-DA-DESTILACAO.md).
