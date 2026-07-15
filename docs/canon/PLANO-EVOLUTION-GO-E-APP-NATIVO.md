# PLANO — Evolution GO oficial + resolver o APP nativo (HDI/Yelum)

## Parte 1 — Migrar TUDO para Evolution GO (decisão do founder 14/07: fazer já)

### Passo a passo (você pareia; eu faço o resto)
1. **Você — no painel do Evolution GO** (`autobrokers-intelligence-os-evolution-go-teste`):
   - em Configurações → Webhook: URL = `https://autobrokers-intelligence-os-autobrokers-smith-api.golhpm.easypanel.host/api/webhook/evolution` (ou o endpoint atual do webhook), marcar evento **MESSAGE** (e CONNECTION/QRCODE);
   - deixar a instância `autobrokers-go-teste` pronta (ainda desconectada).
2. **Eu — no código do Smith:** apontar a integração da Resulta para o GO
   (provider `evolution-go`, base_url do GO, token de instância) e garantir que o
   adapter de saída (send_text/send_media) e o parser de entrada do GO estejam
   ligados. Como o GO é compatível com a API Baileys, o adapter Evolution atual
   é reaproveitável com ajuste de base_url/headers — mudança de config, não de
   arquitetura.
3. **Você — parear:** eu gero o QR pelo GO; você escaneia com o WhatsApp da
   Resulta (desconecta do Evolution API antigo primeiro — 1 número = 1 instância).
4. **Nós — validar:** 1 atendimento de teste ponta a ponta pelo GO (Even + espelho).
5. **Rollback (5 min):** repontar a integração para a Evolution API antiga.

### O que muda para o cliente: nada (mesmo número). O que ganhamos: velocidade,
estabilidade, botões/listas nativos e — o principal — o protobuf COMPLETO das
mensagens de formulário nativo (a chave para a Parte 2).

## Parte 2 — Atravessar o APP nativo (formulário dentro do WhatsApp)

**O problema:** HDI/Yelum (mesmo bot) terminam num `nativeFlowMessage` — um mini-app
que, no WhatsApp real, exige o usuário CLICAR e preencher. A Evolution API não
expunha os parâmetros para responder isso programaticamente.

**A missão (founder): resolver no NOSSO código, sem tocar no fork da Evolution.**
Caminho técnico, em ordem de tentativa:

1. **Responder o flow via envio nativo do GO.** O WhatsApp aceita uma
   `interactive` de resposta a flow/list (`nfm_reply` / `listResponseMessage` com
   o `flow_token`/`id` que VIÊM no protobuf de entrada). O GO recebe esses campos
   (validado 11/07). Se o GO expõe um `/send/interactive` (ou aceita o payload no
   `/send/text` estendido), montamos a resposta no nosso adapter — **puro código
   nosso**, sem mexer no fork. Já capturamos `flow_id/flow_token` no
   `evolution_inbound._interactive_from_message`.
2. **Se o endpoint não existir no GO:** o payload de saída ainda é WhatsApp-padrão;
   testamos enviar via o `/send/` genérico com o JSON do `nfm_reply`. É onde o
   teste com o GO conectado prova o que funciona (não dá para saber sem o número).
3. **Fallback só se 1 e 2 falharem:** naquela ÚNICA tela, o atendente monta o
   resumo e pede ao cliente para tocar/confirmar (micro-handoff cirúrgico, 1 clique
   do cliente, não do humano interno) — muito melhor que handoff total. Mas a meta
   é 1/2 funcionarem.

**Por que não dá para garantir hoje:** o teste do passo 1/2 exige o GO **conectado**
com um número. Por isso a Parte 1 vem primeiro. Assim que parear, este é o
**primeiro teste** que rodo — e trago o veredito real (funciona / precisa de patch /
fallback).

## Ordem
Parte 1 (parear GO) → validar atendimento normal → teste do flow_response no app
nativo (HDI/Yelum) → veredito. Só então retomamos o mapeamento em massa pelo GO.
