# Roteiro de teste do Espelho — Amandus Seguros

**Para:** Founder · **Data:** 06/08/2026 · **Commit no ar:** `17aaefa`

> **Por que a Amandus e não a Resulta ou a AutoFleet:** o número pareado será o
> seu, numa corretora que não tem atendimento real acontecendo. Nada do que você
> fizer aqui toca no WhatsApp de trabalho da Regina nem da Saionara.

📊 Verificado antes de escrever este roteiro: a Amandus está com
`observer_scope = insurers_and_clients`, então conversa com número comum **é**
capturada. Sem isso, o teste falharia por configuração e pareceria defeito.

---

## O que você vai precisar

- **Seu celular** (o que vai parear na Amandus)
- **Um segundo WhatsApp** — outro celular, ou pedir a alguém que te mande
  mensagem. É ele que faz o papel do "segurado".
- O dashboard aberto na **Amandus Seguros** (seletor de empresa, canto inferior)

---

## PASSO 1 — Parear

1. Dashboard → **Personalização → Corretora → WhatsApp**
2. Confira que a empresa selecionada é **AMANDUS SEGUROS**
3. Clique em **Conectar número (QR code)**
4. No seu celular: WhatsApp → Configurações → Dispositivos conectados →
   **Conectar dispositivo** → aponte para o QR

**✅ O que tem de acontecer:** o cartão vira **Conectado** e, ao lado, aparece o
seu número mascarado — algo como `5547*****463`.

**❌ Se o QR não aparecer:** pare e me diga. É o defeito que passamos o dia
consertando e eu preciso saber.

---

## PASSO 2 — A conversa aparece no chat

Do **segundo WhatsApp**, mande uma mensagem para o número que você acabou de
parear. Sugestão, para ficar fácil de achar depois:

> `Teste 1 — bom dia, quero saber do meu seguro`

Espere **até 1 minuto** e vá em **Atendimentos → Conversas**.

**✅ O que tem de acontecer:**
- a conversa aparece na lista da esquerda, com o número do segundo WhatsApp
- ao abrir, a mensagem está lá

**❌ Se não aparecer:** me avise. Vou olhar se a mensagem chegou no acervo — se
chegou e não virou conversa, o problema é a ponte e é meu.

---

## PASSO 3 — Responder pelo dashboard

Na conversa aberta, escreva no campo de resposta:

> `Teste 2 — respondendo pelo dashboard`

**✅ O que tem de acontecer:**
- a mensagem chega no **segundo WhatsApp**, vinda do seu número pareado
- ela aparece **UMA vez** no chat do dashboard

**❌ Se aparecer DUAS vezes:** é o "eco" — a mensagem vai ao WhatsApp e volta
pelo webhook. Tem guarda para isso, mas se falhar eu preciso saber.

---

## PASSO 4 — Responder pelo CELULAR e ver aparecer no chat

Agora **pelo seu celular** (não pelo dashboard), responda na mesma conversa:

> `Teste 3 — respondendo pelo celular`

Volte ao dashboard e abra a conversa.

**✅ O que tem de acontecer:** a mensagem que você digitou no celular aparece no
chat do dashboard, do mesmo lado das outras respostas suas.

Este passo é o que prova que a Regina pode trabalhar pelo celular **e** o
dashboard mostrar tudo — que era o pedido central.

---

## PASSO 5 — A conversa "assumida" (o freio do agente)

Ainda no dashboard, olhe a conversa depois do Passo 4.

**✅ O que tem de acontecer:** ela aparece como **assumida por um humano**
(status muda; costuma aparecer como "Atendente pelo celular").

**Por que isso importa:** é a garantia de que, no dia em que o agente estiver
ligado, ele **para de responder aquele cliente** assim que uma pessoa entra na
conversa. Duas pessoas respondendo o mesmo segurado é o defeito que isso evita.

⚠️ Neste teste o agente está **desligado** (como em todas as corretoras), então
não há ninguém para calar. O que estamos conferindo é que a marca é registrada.

---

## PASSO 6 — Áudio e imagem (o que ainda NÃO funciona)

Mande um **áudio** do segundo WhatsApp.

**✅ O que tem de acontecer:** aparece uma mensagem no chat dizendo `[audio]`.

**⚠️ Isso é o esperado por enquanto.** A mensagem existe e é visível, mas não
toca. Está registrado como **P-119** e resolvemos depois — decisão sua.

---

## Se algo falhar, o que me mandar

Não precisa diagnosticar. Só me diga:

1. **Qual passo** falhou (1 a 6)
2. **O que você viu** na tela
3. **A hora aproximada**

Com a hora eu acho a mensagem no banco e sei dizer em que ponto ela parou:
chegou no provedor? virou acervo? virou conversa? É meia dúzia de consultas.

---

# ANEXO — Comando para trazer as conversas da AutoFleet

Isto é **separado do teste** e você pode rodar quando quiser.

📊 A AutoFleet tem **32.128 mensagens capturadas nos últimos 7 dias** e o chat
dela está vazio, porque a ponte só age em mensagem nova e nenhuma chegou desde o
deploy. Este comando leva ao chat o que já foi capturado.

**No console do EasyPanel**, contêiner `autobrokers-smith-api`, pasta `/app`:

```bash
python -c "
import asyncio
from app.services.atlas.espelho_chat import trazer_conversas_ja_capturadas
print(asyncio.run(trazer_conversas_ja_capturadas(
    company_id='6c9c55e2-2f30-4ca2-a1ef-4ef464ed1b4a', dias=3)))
"
```

**O que ele faz:** lê as conversas capturadas dos últimos 3 dias e as escreve no
chat. **Não envia nada pelo WhatsApp. Não liga agente nenhum.** É leitura do
acervo e escrita no chat, nada mais.

**O que você deve ver:** algo como
`{'ok': True, 'lidas': 1830, 'levadas': 1830, 'dias': 3}`

Depois disso, abra **Atendimentos → Conversas** com a **AutoFleet** selecionada.

**É seguro rodar duas vezes** — ele reconhece o que já levou e não duplica. Se
ficar em dúvida se rodou, rode de novo.

Se quiser a semana inteira, troque `dias=3` por `dias=7`. 📊 São 301 conversas
distintas em 7 dias; a lista mostra as mais recentes primeiro.
