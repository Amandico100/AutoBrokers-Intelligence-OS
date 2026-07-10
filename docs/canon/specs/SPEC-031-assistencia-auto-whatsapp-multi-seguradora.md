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
| **Yelum** (ex-Liberty) | WhatsApp/tel | 08007014120 | parcial | `yelum-auto-whatsapp@v1` |
| **Tokio** | WhatsApp 24h | 08007078005 | parcial | `tokio-auto-whatsapp@v1` |

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

## 5. Freio de finalização (segurança inegociável)
- `finalize_anchors` por playbook (regex dos passos de confirmação REAL, minerados das conversas).
- `handle_insurer_message`: se casar um finalize_anchor e a sessão NÃO tiver `finalize_approved=True`,
  transita para `needs_human` com `reason=finalize_gate` (transcript + próximo passo prontos).
- `INSURER_DISPATCH_LIVE=true` libera responder a URA de verdade, MAS o freio de finalização continua —
  são gates independentes. Só um humano (ou aprovação explícita) passa do freio.
- Autônomo/noturno: NUNCA passar do freio. Teste real de ponta a ponta só com a corretora presente.

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
