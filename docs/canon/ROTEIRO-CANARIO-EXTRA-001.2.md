# Roteiro do canário em produção — SPEC-EXTRA-001.2 · O agente lê tudo antes de falar

> **Quem conduz:** o Founder, pelos aparelhos **TESTE-A** (o segurado) e **TESTE-B** (a atendente, no caso 8)
> e pelo card *Agente* do painel (caso 7). **Quem prepara:** a execução da SPEC.
> ⛔ Nenhum caso toca segurado real, seguradora, atendente ou portal. ⛔ Nenhum tenant é ligado inteiro.
> **Quando:** depois de **Implantar `smith-api`** (e `smith-web`, pela frase de recusa no card Agente)
> com o commit final da SPEC. As migrations `20260914_07` e `20260914_08` já estão aplicadas (relatório §6).
>
> O relatório distingue **não testado** · **aprovado no canário técnico** · **validado pela atendente**.
> Este roteiro alimenta o segundo. As evidências entram no relatório **por alias e por contagem**
> (turnos, linhas, presença/ausência) — nunca com CPF, nome, telefone ou print sem redação.

## 0. Antes (§16 da proposta)

- [ ] SHA implantado de `smith-api` = commit final da SPEC (a tela do EasyPanel mostra; o `/health` **não** prova versão).
- [ ] `JANELA_SILENCIO_EXCECOES` contém **só** TESTE-A/TESTE-B (conferir pelo nome da variável, nunca pelo valor no chat).
- [ ] `companies.agent_enabled` continua **false** em todas; o canário anda só pela exceção de janela.
- [ ] `PRESENCA_DIGITANDO_LIGADA` **ausente ou `false`** nos casos 1–4 e 6–8; **`true` só durante o caso 5**, e volta para `false` depois. 🔴 Não ligar antes de o caso 1 passar.
- [ ] Nenhuma outra variável nova é obrigatória (`TURNO_TTL_SEGUNDOS` 90 · `TURNO_RENOVACOES_MAX` 3 · `JANELA_DADO_CURTO_SEGUNDOS` 3 · `JANELA_FRASE_COMPLETA_SEGUNDOS` 8 · `JANELA_FRASE_INACABADA_SEGUNDOS` 18 · `REPLANEJAMENTOS_MAX` 2 — todas com default).
- [ ] Antes de qualquer envio vivo: no Redis, `KEYS whatsapp_turno:*` vazio (nenhuma trava órfã de teste anterior).

## 1. Os casos — o que mandar e o que tem de sair

| # | onde | o que mandar (por alias) | o que prova | evidência a anotar |
|---|---|---|---|---|
| 1 🔴 | TESTE-A | **5 mensagens + 1 foto em 12 s** ("oi" · "meu carro quebrou" · "estou na marginal" · a foto do painel · "não liga" · "o que eu faço?") | **1 turno**, 1 resposta (até 4 balões pela humanização, que é outra régua), a foto reconhecida, nenhuma pergunta repetida, nenhum cumprimento no meio | 📊 contagem de turnos (esperado **1**); balões; a foto citada sim/não |
| 2 | TESTE-A | um CPF de teste **sozinho** | resposta em **~3 s** de espera, não 8 | segundos entre a mensagem e o "digitando"/resposta |
| 3 | TESTE-A | "o carro parou na" · **15 s depois** "marginal pinheiros sentido castelo" | **um** turno | contagem de turnos (esperado **1**) |
| 4 | TESTE-A | mais uma mensagem **enquanto o agente responde** ao caso 3 | ela entra na mesma resposta ou na seguinte — **nunca se perde, nunca duplica** | a mensagem foi respondida sim/não; respostas duplicadas (esperado **0**) |
| 5 | TESTE-A (com `PRESENCA_DIGITANDO_LIGADA=true`) | repetir o caso 3 | "digitando…" aparece enquanto pensa e **some** ao responder; numa conversa que o agente vai **calar** (TESTE-B tomou a conversa) → **nenhum** "digitando…" | presença vista sim/não nos dois cenários |
| 6 | TESTE-A | encerrar o assunto ("obrigado, resolvido") → voltar **dentro da janela** ("esqueci de perguntar uma coisa") → depois um **assunto novo** dias depois ou após o encerramento | dentro da janela: **sem** reapresentação; assunto novo: **uma** apresentação com o nome do agente **e da corretora** | cumprimentos fora da abertura (esperado **0**); a frase de apresentação redigida |
| 7 | card Agente + TESTE-A | trocar o nome do agente **no meio** de um assunto; depois tentar salvar um nome **igual ao de um membro da equipe** | no assunto atual nada muda; no seguinte **uma** linha dizendo que mudou; o nome colidente é **recusado com a frase** | as duas frases redigidas; HTTP da recusa (esperado **400**) |
| 8 | TESTE-B (a atendente) | responder pelo celular numa conversa de TESTE-A | a pausa vale (o agente cala), o silêncio aparece **no feed com motivo**, a mensagem de TESTE-B **não é gravada em dobro** | linhas em `messages` para aquele `wa_message_id` (esperado **1**); a linha do feed |

🔴 **O caso 5 (conversa calada → nenhuma presença) e o caso 8 são as linhas de controle** (CLAUDE.md §9.2): sem eles, "o agente lê tudo" pode ser um agente que nunca cala.

## 2. Depois

- Voltar `PRESENCA_DIGITANDO_LIGADA` para `false` (ou remover) — decisão de ligar de vez é 🧑 do Founder depois do relatório da atendente.
- Conferir no Redis: `KEYS whatsapp_turno:*` vazio e `KEYS whatsapp_buffer:*` vazio (nenhuma trava órfã).
- Conferir em `messages` que nenhum `wa_message_id` do canário aparece 2× na mesma conversa.
- Registrar cada caso no relatório §8 com evidência por alias e contagem.

## 3. O que só o Founder faz

1. Implantar `smith-api` e `smith-web`.
2. Mandar os casos 1–6 do TESTE-A; o 7 pelo card; o 8 do TESTE-B.
3. 🧑 Escolher o nome do agente da Resulta (D-PILOTO-12: a SPEC não decide).
4. 🧑 Depois do canário: decidir `PRESENCA_DIGITANDO_LIGADA=true` em produção.
