# RUNBOOK — Teste HDI do Cartógrafo (+ app nativo) — para o executor (Opus/Fable)

> Escrito pelo Fable em 15/07/2026 com 1% de tokens, para o próximo executor
> assumir SEM perder nada. Leia TAMBÉM a memória persistente
> (`deploy-triggers-e-envs.md`) — ela tem os fatos operacionais e credenciais-chave.

## Estado ao escrever isto
- Evolution GO é o canal OFICIAL (main `1285fe5`): pareado (554796274743), inbound
  + foto + PDF + áudio VALIDADOS pelo founder ("TUDO FUNCIONOU PERFEITAMENTE").
- Cartógrafo v2 pronto (re-identificação, dados completos, saída p/ humano,
  detecção de FORMULÁRIO NATIVO → nó `app_form` + encerra ramo).
- `CARTOGRAPHER_MODE=1` já está nos envs. Dataset real em
  `backend/data/cartographer_test_data.json` (LOCAL, fora do git — combos com
  CPF/placa/endereços reais; hdi/auto existe).
- Teste HDI = 2 em 1: mapeia a URA E encontra a tela do app nativo.

## REGRAS ABSOLUTAS (o founder exige — não há exceção)
1. **NUNCA confirmar/finalizar um acionamento.** O freio `_FINALIZE_RE` responde
   "Sair"/cancela. Se qualquer dúvida, PARAR (stop endpoint) — nunca seguir.
2. **NUNCA entrar em fluxo de sinistro** (`_SINISTRO_RE` já bloqueia).
3. **Fornecer TODAS as informações pedidas** (o test_data COMPLETO vai no start:
   cpf, placa, endereços de origem/destino do pool, telefone_contato).
4. Humano entrar na conversa → saída educada e FIM definitivo (já automático).
5. Dispatch real SEMPRE tem prioridade sobre exploração.
6. **Só iniciar com liberação EXPLÍCITA do founder na conversa.**

## Sequência do teste (com o founder acompanhando no celular)
1. Pré-check (30s): `GET /health` = 200; GO `GET /instance/status` (apikey =
   token da instância) → `LoggedIn: true`; nenhuma exploração ativa
   (`GET /api/admin/spec034/cartographer/status`, header `X-Admin-API-Key`).
2. Montar `test_data` do combo hdi/auto do dataset local (campos: cpf, placa,
   cep, endereco_local/destino do `enderecos_pool`, telefone =
   `telefone_contato_padrao`).
3. Iniciar: `POST /api/admin/spec034/cartographer/start`
   `{company_id: "04b5cdbc-04cd-4ddf-8e4b-f43efb062fab", insurer_key: "hdi",
   ramo: "auto", test_data: {...}}` (header `X-Admin-API-Key`).
   Número da HDI vem do env `INSURER_CONTACT_HDI_ASSISTENCIA` (env > registro).
4. Monitorar a cada ~60s: `GET /cartographer/status` (tem transcript tail).
   Reportar ao founder no chat a cada avanço de tela.
5. **Ao aparecer `[FORMULARIO NATIVO: ...]`** (provável fim do fluxo, família
   Yelum): o Cartógrafo marca `app_form` e encerra o ramo — ISSO É SUCESSO do
   mapeamento. AÍ começa o teste do app nativo (abaixo).
6. Fim: mapa salvo como `proposed` (nunca ativa sozinho; 1 clique de aprovação).

## Teste do APP NATIVO (a missão da vantagem competitiva)
Quando o formulário nativo chegar, o webhook loga o protobuf completo (GO
entrega tudo). Capturar do evento: `listMessage`/`nativeFlowMessage` →
`flow_token`/`id`/rows. Tentar responder NO NOSSO código, nesta ordem:
1. `POST {GO}/send/list` — replicar seleção; ou os métodos já prontos do
   provider: `send_list_reply(to, row_id, title)` / `send_button_reply`.
2. Se não avançar: montar o `nfm_reply` (interactiveResponseMessage) e tentar
   pelos endpoints /send do GO (payload WhatsApp-padrão).
3. Registrar o veredito HONESTO (funciona / precisa patch / fallback micro-clique
   do cliente). NÃO prometer o que não passou no teste.

## PARADA DE SEGURANÇA (3 camadas — combinadas com o founder)
- **Camada 1 (founder digita "PARAR" no chat):** executor chama IMEDIATAMENTE
  `POST /api/admin/spec034/cartographer/stop` (header `X-Admin-API-Key`) —
  interrompe, salva mapas propostos, não manda mais nada. VALIDADO em 14/07.
- **Camada 2 (automática):** freios do código (finalize/sinistro/needs_data/
  humano/60 msgs/stall-watchdog 90s).
- **Camada 3 (físico, último recurso):** botão **Desconectar** no card WhatsApp
  do dashboard (novo, 14/07) — derruba o canal inteiro em 2 cliques; ou remover
  env `CARTOGRAPHER_MODE`.
- Atendimento durante o teste: allowlist só responde ao founder; dispatch real
  tem prioridade; espelho/Vigia continuam ativos.

## Depois do teste
Atualizar a memória (`deploy-triggers-e-envs.md`) com: telas mapeadas, onde o
app nativo apareceu, veredito do flow reply, e o que falta. Mapas ruins →
marcar `retired` (nunca deixar rota errada proposta).
