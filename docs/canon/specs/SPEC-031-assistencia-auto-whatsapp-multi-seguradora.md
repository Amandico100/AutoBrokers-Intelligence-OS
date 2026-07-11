# SPEC-031 — Assistência AUTO ponta a ponta no WhatsApp (multi-seguradora)

**Autor**: Fable 5 (líder técnico) · 2026-07-10 · **Status**: em execução (janela AutoFleet/InfoCap-auto)
**Reusa**: SPEC-017 (atendente + dispatch engine + corridor_playbooks) — **é PROIBIDO criar motor paralelo**.

> O corredor residencial Allianz já funciona com este mesmo motor (`insurer_dispatch_service` +
> `corridor_playbooks` + `dispatch_router` + tool `insurer_dispatch`). Auto é o MESMO motor com
> **playbooks novos (dados versionados)** minerados das conversas reais da AutoFleet com as
> seguradoras. Nada de worker novo, fila nova, cérebro novo.

## 1. Objetivo
Cliente manda mensagem no WhatsApp da corretora pedindo **guincho, bateria, pneu ou chaveiro** para o
carro. O atendente (agente `attendance`, mesmo grafo Smith) entende, identifica a apólice na InfoCap
(CPF → veículo/placa/seguradora), coleta o que falta de forma humanizada, e **aciona a assistência da
seguradora certa pelo WhatsApp dela** — respondendo a URA automaticamente — **parando ANTES da
confirmação final** (o acionamento real que despacha um prestador só acontece com a corretora junto).
Depois, **acompanha o cliente** até o serviço ser resolvido.

Vidros continua indo pelo `portal_action` (abraseuatendimento) — não é escopo aqui.

## 2. Seguradoras (evidência das conversas reais AutoFleet)
| Seguradora | Canal assist. | Contato (WhatsApp) | URA mineração | Playbook |
|---|---|---|---|---|
| **Allianz** | WhatsApp 24h | 1140901444 | forte (menu Auto→serviço) | `allianz-auto-whatsapp@v1` |
| **Porto** | WhatsApp 24h | (0800 7270800 / wa) | **muito forte** (guincho completo) | `porto-auto-whatsapp@v1` |
| **HDI** | WhatsApp 24h | (0800 7773313 / wa) | **muito forte** (guincho completo) | `hdi-auto-whatsapp@v1` |
| **Yelum** (ex-Liberty, grupo HDI desde 2024 — MESMO bot da HDI) | WhatsApp | 1131321001 | prints reais + família HDI | `yelum-auto-whatsapp@v2` |
| **Tokio** | WhatsApp 24h | 11 95302-2395 | fraca (42 linhas) — nasce conservador | `tokio-auto-whatsapp@v1` |

Contato HDI corrigido pelo founder (2026-07-11): WhatsApp oficial **551155020700**
(`INSURER_CONTACT_HDI_ASSISTENCIA=551155020700`).

Contato real vem de env por seguradora (`INSURER_CONTACT_<KEY>_ASSISTENCIA`), com fallback para o
`INSURER_CONTACT_ALLIANZ_ASSISTENCIA_24H` legado (Allianz). Nunca hard-coded no playbook.

## 3. Subserviços auto (comuns)
`guincho` (reboque) · `bateria` (recarga/pane elétrica) · `pneu` (troca/borracheiro) · `chaveiro`
(chaveiro do veículo). Vidro → portal, fora daqui.

Slots (união; cada subserviço exige um subconjunto):
`titular_cpf`, `veiculo_placa`*, `veiculo_descricao`*, `local_atual` (onde o carro está),
`local_destino` (só guincho — para onde levar), `problema_descricao`, `quando` (agora|agendar),
`pessoa_no_local`, `telefone_contato`, `ponto_referencia?`. (* = InfoCap resolve; o LLM NUNCA inventa.)

## 4. Como funciona (mesma máquina, playbook novo)
1. Atendente identifica a apólice (InfoCap por CPF) → descobre **seguradora** e **veículo/placa**.
2. Coleta o que falta (local atual, destino se guincho, o que houve, quando, quem está no local).
3. Chama `insurer_dispatch(insurer_key=<seguradora>, subservice=<...>, slots)`.
4. Motor: abre a conversa na seguradora, responde a URA por **âncoras determinísticas** onde é estável;
   onde varia (endereço livre, menus que mudam) usa o **cérebro adaptativo guardado** (já existente).
5. **FREIO DE FINALIZAÇÃO** (novo, obrigatório): quando a URA chega no passo que **confirma/abre** o
   serviço de fato, o motor **NÃO confirma** — vira `needs_human` (aprovação) com o transcript pronto.
   A corretora aperta o botão final. Isso satisfaz "até o último passo a parar" e "só apertar o botão".
6. Captura protocolo/OS + link de acompanhamento por âncora real (nunca inventa).
7. **Pós-acionamento**: o atendente informa o cliente (protocolo + link + instruções) e **acompanha**
   até resolver (pós-cobrança/acompanhamento reusa o mesmo agente — não cria fluxo paralelo).

## 5. Freio de finalização = TRAVA DE TESTE (decisão do founder, 2026-07-11)
O freio NÃO é HITL permanente: ele existe SÓ para os testes (a IA executa o fluxo
inteiro na seguradora e CANCELA antes de abrir o serviço — nada de acionamento de
mentira). Corredor VALIDADO roda ponta a ponta SEM humano.

- `finalize_anchors` por playbook = detecção do passo em que a seguradora vai
  CONFIRMAR/ABRIR de verdade (regex dos textos REAIS 2026: Allianz/Alfa "Podemos
  confirmar o atendimento?", Porto "Como você quer prosseguir?/Confirmar solicitação",
  Bradesco "Posso confirmar a abertura", Azul "Tudo está correto?", Zurich "Podemos
  confirmar a solicitação", HDI/Yelum antes do trecho que abre sozinho).
- **Modo TESTE (default)**: ao casar um finalize_anchor → `test_aborted` +
  `finalize_abort_reply` do playbook (Allianz/Alfa "SAIR", Porto "Sair e não agendar",
  Azul "4", HDI/Yelum "Sair", Bradesco "Não", Zurich silêncio) + aviso a quem testa.
- **Modo LIVE**: `DISPATCH_FINALIZE_MODE=live` (global) ou
  `DISPATCH_FINALIZE_LIVE_PLAYBOOKS=ref1,ref2` (graduação corredor a corredor).
  O freio não trava: a confirmação é respondida pelos próprios `ura_steps`
  (ex.: "podemos confirmar o atendimento" → "1") e o fluxo completa até o protocolo.
- 2ª camada: o cérebro adaptativo (fase humana) recebe a regra por modo — teste:
  NAO_SEI na confirmação; live: confirmar quando o RESUMO confere com o caso.
- Humano SÓ em: sinistro, sem-corredor, ou travamento real → dossiê + aviso ao cliente.
- `INSURER_DISPATCH_LIVE` continua sendo o gate de ENVIO (nada sai com ele off).
- Pós-protocolo: sessão vira `monitoring` (24h) — updates da seguradora ("prestador
  a caminho", agendamento) são repassados ao cliente; pesquisas são ignoradas.
- Multi-cliente: as URAs LEMBRAM o CPF do último atendimento (o WhatsApp é da
  corretora) → todo corredor re-identifica SEMPRE (nunca aciona no cliente anterior).

## 6. Disciplina (house-style)
- Playbooks = dados versionados em `corridor_playbooks.py` (como o residencial). Motor puro, testável.
- Testes: replay das URAs reais (offline, sem rede) → resposta determinística certa + captura + freio.
  importlib/stubs/`check()`/ASCII/sem pytest. Frontend não é tocado.
- Deploy: commit feat → merge `--no-ff` main → push → trigger EasyPanel (smith-api). Gate liga o founder.

## 7. Critérios de aceite
- [ ] `insurer_dispatch(insurer_key=porto|hdi|allianz|yelum|tokio, subservice=guincho, ...)` monta o
      plano dry-run correto por seguradora (sequência de respostas coerente com a URA real).
- [ ] Motor responde a URA por âncora onde é estável e cai no cérebro adaptativo onde varia.
- [ ] Freio de finalização pausa ANTES de confirmar o serviço, em modo LIVE, sem exceção.
- [ ] Protocolo/OS + link capturados só por âncora real.
- [ ] Atendente coleta com humanização, usa InfoCap, e acompanha o cliente até encerrar.
- [ ] Nenhum prestador é despachado sem a corretora apertar o botão final.
