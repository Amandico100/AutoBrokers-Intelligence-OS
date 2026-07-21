# SPEC-049 — Pareamento limpo, aviso de queda robusto e Garimpo v2

> Executada em 21/07/2026 (pedidos do founder pós-testes da SPEC-048).

## 1. Bug do rename (Saionara→Fernanda falhava) — causa e fix

A SPEC-048 passou o formulário a editar o valor CRU com `{{variáveis}}` — mas o
guard anti-injeção (`TEMPLATE_INJECTION`) rejeitava QUALQUER `{{` em texto de
tenant. Resultado: qualquer save (até só trocar o nome) falhava com
`opening_message:template_injection` nas duas corretoras.

**Fix:** whitelist de variáveis seguras (`attendant_name`, `company_name`,
`business_hours`, `handoff_target`) permitida SÓ nos campos-template
(`opening_message`/`closing_message`). Qualquer outro `{{...}}`, em qualquer
campo, segue bloqueado — o guard continua fail-closed. Prova funcional no
teste (abre PASSA, `{{system_prompt}}` BLOQUEIA).

## 2. Variáveis protegidas na UI

Abertura/encerramento agora ficam TRAVADOS mostrando a prévia renderizada;
editar exige clicar em "Editar" e confirmar um aviso que explica as variáveis
("NÃO as apague nem digite nomes fixos"). "Restaurar padrão" continua como
rede de segurança.

## 3. Card de pareamento (WhatsAppChannelCard) reorganizado

- **Passo 1 — Conectar:** instruções numeradas + botão Gerar QR + QR. É a
  primeira coisa da tela.
- **Passo 2 (opcional) — Aviso de queda:** SEMPRE visível/editável (conectado
  ou não): (a) **Grupo do suporte humano** (o MESMO destino dos dossiês —
  `_support_contact`, aceita @g.us; recomendado), (b) outro número (validado
  no servidor: NUNCA o número pareado), (c) sem aviso.
- **Diagnóstico Evolution legado REMOVIDO da tela** (EVOLUTION_BASE_URL etc.
  era infra interna da plataforma e checava o provedor clássico — só
  confundia). O endpoint segue existindo para debugging interno.
- Verificado: nada do Evolution clássico influencia o pareamento — todos os
  fluxos (setup/qr/status/disconnect) checam `_go_enabled()` primeiro; o
  clássico só roda se o env WHATSAPP_CHANNEL_PROVIDER mudar.

## 4. Alerta de desconexão — de "existia no papel" para robusto

Já disparava no `connection.update` (close/logout), mas o envio dependia de
envs `PLATFORM_ALERT_WA_*` (não configurados) → falhava em silêncio. Agora:
- **Destino:** número configurado OU destino do suporte humano (grupo) OU
  `PLATFORM_ALERT_FALLBACK_NUMBER`.
- **Remetente:** instância-plataforma (envs, se existirem) → senão OUTRA
  integração ativa da mesma corretora (ex.: observador) → senão registra em
  **Atividades** ("WhatsApp desconectado — reconecte…"), nunca silencia.
- `POST /api/whatsapp-channel/set-alert` (+ proxy Next `action: set-alert`):
  configura/edita a qualquer momento; status expõe a config atual.
- Env opcional futuro: `PLATFORM_ALERT_WA_{BASE_URL,INSTANCE_ID,TOKEN,PROVIDER}`
  para um número dedicado de alertas da plataforma.

## 5. Celular desligado/sem internet — como funciona (multi-device)

O pareamento usa o modo multi-aparelho do WhatsApp: a instância é um
"aparelho conectado" INDEPENDENTE do celular. Celular sem bateria/internet →
**o atendimento continua funcionando normalmente**. Só desconecta se: (a) o
celular ficar ~14 dias sem conectar à internet, (b) alguém desconectar o
aparelho manualmente no WhatsApp, (c) troca de senha/segurança da conta.
Nesses casos o aviso de queda dispara. Se o NOSSO servidor reiniciar,
mensagens recebidas no intervalo são entregues pelo WhatsApp na reconexão e
processadas — nada se perde.

## 6. Conhecimento — auditoria (nenhuma seleção manual necessária)

Atendimento e Auxiliares/rotinas executam pelo MESMO grafo Smith
(`process_message`) com a MESMA tool `knowledge_base_search` → todo
conhecimento da corretora já fica disponível automaticamente para Core,
Atendimento e Auxiliares, sem seleção. Escopos: corretora (todos os agentes
da empresa) · pessoal (só o dono do documento, no Chat Principal) · global
AutoBrokers (curado, leitura). Únicas exceções por design: docs pessoais não
vazam para a equipe, e transcript de cliente NUNCA entra cru no RAG (só o
destilado mascarado).

## 7. Garimpo v2 — aprender de verdade com os corretores

v1 era só regex (custo zero, mas míope) e a "camada LLM" era promessa de
docstring. v2 implementada: 1 chamada BARATA por corretora/dia
(`GARIMPO_LLM_MODEL`, default Haiku 4.5; entrada ≤8k chars; ≤8 insights;
dedup; `source=garimpo_llm`; desligável `GARIMPO_LLM=0`), com kinds novos
`duvida_seguros` e `necessidade`. Tiering completo da inteligência: Haiku no
volume (garimpo), Sonnet no braçal (destilador estágio 1), Opus no estrutural
(playbooks estágio 2 + gate). Visível em Admin → Insights·Garimpo e no
Cockpit ("Voz do corretor").

## Invioláveis
- Guard de injeção continua fail-closed fora da whitelist.
- Alerta nunca sai pelo número que caiu.
- Garimpo nunca roda em conversa espelhada de seguradora; PII de segurado
  não entra em insight.
