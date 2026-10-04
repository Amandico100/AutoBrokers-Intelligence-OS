# Inventário dos testes do Founder — 04/10/2026

> Fonte: `TAREFAS-DO-FOUNDER.md` (T-01 a T-103), o que o Founder fez em 03/10 e **SELECT só leitura** no banco de produção em
> 04/10 (UTC) — `agents`, `human_support_destinations`, `company_internal_numbers`, `integrations`, `tenant_connections`,
> `llm_papeis`, `cerebro_modos`, `schema_migrations`, `diario_de_decisoes`, `tool_invocations`, `portal_jobs`,
> `token_usage_logs`. Nenhum dado pessoal foi lido para fora. O passo a passo está em `../ROTEIRO-DE-TESTES-DO-FOUNDER.md`.

## O placar

| estado | quantos | o que quer dizer |
|---|---|---|
| ✅ já feito antes (01/10) | 2 | T-01, T-05 |
| **FEITO agora** (03–04/10, com prova) | **8** | T-02 T-06 T-82 T-91 T-92 T-98 T-99 T-102 |
| **ATRASADO e ainda vale — no roteiro** | **62** | encaixado nas sessões P · 1 · V · 2 · 1b · C · S · F |
| **ATRASADO e ainda vale — fora do roteiro** | **23** | precisa de caso real, de 2ª corretora de teste, da equipe ou vem depois (vida real) |
| **COBERTO** por outro teste | **5** | T-27 T-29 T-40 T-67 T-86 |
| **MORREU** (a peça mudou) | **2** | T-31 T-83 |
| **FUTURO** (depende de SPEC/material que não existe) | **1** | T-97 |
| **total aberto em 03/10** | **101** | 103 − T-01 − T-05 |

## FEITO (a prova)

| T | prova |
|---|---|
| T-02 | o Founder conferiu em 03/10: `smith-api` e `portal-worker` = `main a87b2e7`; `portal-worker` build 03/10 17:36 (≥ 24/09) |
| T-06 | 📊 04/10 SELECT `llm_papeis` com reserva: **8** linhas (as 7 de 01/10 + `confirmacao` gpt-6-luna → claude-sonnet-5-5, da 126) |
| T-82 | Implantar coberto pelo da 126/127 (sobe a `main` inteira); 📊 04/10 SELECT `agents`: 4 de atendimento, todos `v2`, todos `is_active = false` |
| T-91 | o Founder em 03/10; 📊 04/10 as duas migrations `20261002202210` e `20261002202302` estão em `schema_migrations` |
| T-92 | o Founder em 03/10: `confirmacao | gpt-6-luna | medium | claude-sonnet-5-5 | low` e `on | false | 40`; 📊 04/10 confere |
| T-98 | autorizado pelo Founder em 03/10; a rodada é do gerente (não é tarefa dele) |
| T-99 | o Founder em 03/10: `portal-worker` e `smith-api` no ar = `a87b2e7` |
| T-102 | autorizado pelo Founder em 03/10; a rodada é do gerente |

## ATRASADO — no roteiro (62)

| T | passo | nota |
|---|---|---|
| T-100 | P1 | 📊 03/10 a corretora de ensaio é a única com `falta_documento = true` — **trava o vidro** nela |
| T-08 · T-07 | P2 | `DISPATCH_FINALIZE_MODE=test` é pré-requisito de toda a Conversa 1; T-07 é faxina opcional na mesma sentada |
| T-23 | P2 · P7 · 2.9 | (2) grupo de canário: 📊 ativo desde 26/09 · (4) linha pareada: 📊 `paired` · (1) allowlist e (3) número da casa: 📊 0 números da casa |
| T-55 | P2 · P3 | autorizado (D-124-F); feito junto, um Implantar só |
| T-03 · T-04 | P5 · P6 | |
| T-65 | P8 | ⚠️ o porteiro do botão pode liberar sem conferir (P-E0017-06) — o passo diz o que fazer |
| T-24 · T-25 | P9 · P10 | 📊 04/10 0 de 4 agentes ligados |
| T-54 | P11 | o gerente roda |
| T-26 · T-28 · T-84 · T-35 · T-36 · T-69 | 1.1–1.6 | T-28: a espera de "~3 s" virou "até ~45 s" (a rajada da 125 espera o segurado terminar) |
| T-87 · T-30 · T-34 | 1.7–1.9 | T-34 opcional (precisa de `PRESENCA_DIGITANDO_LIGADA`) |
| T-93 | 1.10–1.15 · 2.3 | "pode deixar", "manda não", "sim, quanto custa?", "prefiro amanhã" não acionam; "pode mandar" e "👍" acionam |
| T-43 · T-51 | 1.16 | só se a URA pedir algo do segurado / se o robô parar |
| T-94 · T-60 | 1.17–1.19 · 2.5 | no modo de teste pode não haver protocolo — o passo manda anotar |
| T-101 · T-56 · T-57 · T-58 | V1–V13 | marcador `VISTORIA-REGINA` no V9 |
| T-96 | V12 (controle, 2 apólices) · 2.6–2.7 | |
| T-95 · T-88 | 2.1–2.4 · 2.6 | |
| T-62 | 2.9 | |
| T-85 · T-37 · T-47 (a) | 1.21–1.22 | T-37/T-47 só se o CPF-1 tiver residencial (Allianz para o T-47) |
| T-89 · T-32 · T-90 · T-33 · T-61 | 1.23–1.27 | T-90 virou pedido ao gerente (o roteiro só tem SELECT) |
| T-09 a T-21 · T-38 · T-66 · T-70 | C1–C16 | 🔴 na **corretora de ensaio**, não na Resulta: 📊 04/10 só ela tem a InfoCap `connected/healthy` |
| T-43 (4) · T-53 (parte) | C14 | `/admin/decisoes` com o nome da corretora |
| T-52 · T-64 | S · S0 | |
| T-68 · T-75 · T-76 | F1–F6 | |

## ATRASADO — fora do roteiro (23)

| T | por quê |
|---|---|
| T-41 T-42 T-44 T-45 T-46 T-48 T-49 T-50 T-63 (e a parte b do T-47) | acionamento **até o protocolo**: só existe com `DISPATCH_FINALIZE_MODE=live` (o prestador vem de verdade) e com uma apólice de cada seguradora. T-41/T-42 (digitar na URA) quebrariam a Conversa 1. T-48 ainda espera `INSURER_CONTACT_YELUM_CARRO_RESERVA` |
| T-39 · T-53 (as duas corretoras) | precisa de uma **2ª corretora de teste com número próprio** — 📊 04/10 não existe (só a de ensaio tem linha de teste; as outras são clientes reais) |
| T-22 · T-59 · T-71 · T-103 | com a equipe / com caso real de vidro / fotos reais cobertas |
| T-72 · T-73 · T-74 | cobrança: 📊 04/10 a Resulta está **sem** conexão InfoCap ativa (`disconnected`) — o gerente confere antes onde ela roda |
| T-77 · T-78 · T-79 · T-80 · T-81 | a vida real (checklist de verdade, ligar no piloto, 3 dias, veredito) — só depois do roteiro verde |

## COBERTO (5)

| T | por qual | por quê |
|---|---|---|
| T-27 | T-87 (passo 1.9) | "5 mensagens + 1 foto" é o caso menor da rajada da 125 (5 frases + 3 fotos) |
| T-29 | T-87 (passo 1.7) | a frase partida com 15 s de pausa está dentro da rajada |
| T-40 | passo 1.15 | em `DISPATCH_FINALIZE_MODE=test` o robô vai até a confirmação e recusa — é o T-40 (se a seguradora do CPF-1 for de menu numerado; senão, fica com os acionamentos por seguradora) |
| T-67 | T-60 (passo 1.18) | "conversa sem pessoa, pedido de ajuda → o alerta chega" é o mesmo caso |
| T-86 | T-93 (passos 1.10–1.15) | o "só aciona depois do sim" da 125 é a mesma cadeia que a 126 endureceu |

## MORREU (2)

| T | por quê |
|---|---|
| T-31 | a "janela" de reapresentação virou **assunto** (125/126: apresenta-se uma vez por assunto; assunto novo = N dias de silêncio ou caso resolvido). O que sobra é observado no 1.1 e no 1.21 |
| T-83 | a medição que ele pedia (críticos da 125 no Sol) **já foi feita** dentro da SPEC-126 (📊 11 de 12); o resto é a T-98 |

## FUTURO — depende de SPEC ou de material que ainda não existe

| o quê | depende de |
|---|---|
| **T-97** botões "✅ Pode acionar / ✏️ Corrigir" | o corpo do `/send/button` do Evolution Go + um celular real mostrando o botão, e uma execução que os ligue |
| o portal **escolher sozinho** (peça, causa, cidade) | a rodada da T-102 (em curso) e ≥ 10 gravações da Porto (T-103) |
| a ponte do DOM, a retomada R3, cidade/UF antes do POST | pendências P-127-01…24 — SPEC nova |
| o DEDUZIR religar no WhatsApp | ≥ 10 casos por seguradora (P-126-06) |
| programa **multicálculo** (SPEC-128+) · Agger parte 2 (H.2–H.4) · EXTRA-001.9 | o plano novo (outro chat) · anuência da Agger · **não será executada agora** |
