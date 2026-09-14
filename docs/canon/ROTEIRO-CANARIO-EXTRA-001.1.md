# Roteiro do canário em produção — SPEC-EXTRA-001.1 · A apólice certa, inteira, em uma rodada

> **Quem conduz:** o Founder (chat `core` do painel da Resulta, conta dele; o caso 6 pelo aparelho **TESTE-A**).
> **Quem prepara:** a execução da SPEC. ⛔ Nenhum caso toca segurado real, seguradora, atendente ou portal.
> **Quando:** depois de **Implantar `smith-api`** (e `smith-web`, pela mudança em `app/api/admin/sandbox/bootstrap-tenant`)
> com o commit final da SPEC. A migration `20260914_06` já está aplicada (relatório §5).
>
> O relatório da SPEC distingue **não testado** · **aprovado no canário técnico** · **validado pela atendente**.
> Este roteiro alimenta o segundo. As evidências entram no relatório **por alias e por contagem**
> (número de linhas, presença/ausência) — nunca com CPF, nome, número de apólice ou print sem redação.

## 0. Antes (§12.1 da proposta)

- [ ] SHA implantado de `smith-api` = commit final da SPEC (a tela do EasyPanel mostra; o `/health` **não** prova versão).
- [ ] As exceções de janela (`JANELA_SILENCIO_EXCECOES`) contêm **só** TESTE-A/TESTE-B (conferir por nome da variável, nunca pelo valor no chat).
- [ ] O agente de atendimento continua **desligado** para todo mundo; o caso 6 usa só a exceção de janela de TESTE-A.
- [ ] Nenhuma variável de ambiente nova é obrigatória. Opcional: `TETO_DO_CONTEXTO_RECUPERADO_CHARS` (default 60000).

## 1. Os casos (§12.2) — o que colar e o que tem de sair

| # | onde | o que colar (por alias) | o que prova | evidência a anotar |
|---|---|---|---|---|
| 1 | chat `core` | o CPF do cliente que produziu a resposta de 4 linhas em 09/09 (3 vencidas/canceladas + 1 vigente) — só o CPF, nada mais | **1 rodada**, 0 vencidas listadas, a resposta diz **por que** é aquela apólice e que há histórico oculto | contagem de apólices citadas (esperado **1**); a frase do porquê; "histórico" mencionado sim/não |
| 2 | chat `core` | "Quais as coberturas da apólice residencial dele(a)?" para o CPF da apólice HDI do golden | **10 linhas** de cobertura com origem (cadastro × documento oficial), a **Assistências Essenciais** com origem documento, a **franquia de Danos Elétricos com as duas** (550 × 600), o aviso de cadastro incompleto e a forma de pagamento **cartão** | contagem de linhas (esperado **10**); as duas franquias presentes sim/não; forma de pagamento |
| 3 | chat `core` | um CPF sem nenhuma apólice vigente (📊 há 24 apólices vencidas nas 7 listagens de 09–11/09; escolha um cliente cujo histórico seja só vencidas — a execução não pode indicar qual sem PII) | a frase da §6.2 **com a data**: "A última apólice vigente foi a …, da …, que valeu até dd/mm/aaaa. Hoje não há nenhuma apólice vigente… Quer que eu liste o histórico?" | a frase literal redigida (número da apólice e nome fora) |
| 4 | chat `core` | um CPF com **2 vigentes do mesmo ramo** (se não houver na carteira, registrar "não há caso real" — o guarda M-B2 cobre o sintético) | pergunta **uma vez**, com as **duas vigentes** e nenhuma vencida | contagem de opções (esperado 2), vencidas listadas (esperado 0) |
| 5 | chat `core` | a pergunta que produziu o turno "ainda não recebi uma pergunta sua" em 10/09 (conversa com documento longo + base de conhecimento) | a resposta **responde a pergunta**; o `payload.turn` do turno grava `rag_chunks`/`rag_chars` | resposta responde sim/não; os dois números do turno |
| 6 | WhatsApp, **TESTE-A** | "meu carro quebrou" · (uma mensagem qualquer) · depois só o CPF | ramo deduzido da **conversa**, não da última frase: a ficha vem da apólice **auto**; resposta de atendimento, não relatório | a apólice escolhida é de auto sim/não; a resposta é conversa sim/não |
| 7 | chat `core` | "quantos clientes eu tenho?" | **linha de controle**: a tool de apólice **não** é chamada e o documento oficial **não** é lido (`tool_invocations` do turno sem `insurance.policy_lookup`) | `payload.turn.tool_calls` do turno (esperado: sem a tool de apólice) |

🔴 **O caso 7 é o que dá direito à conclusão** (CLAUDE.md §9.2). Sem ele, "leu o PDF em 7 de 7" pode ser um `return True`.

## 2. Depois (§12.3)

- Nada a desligar: nenhum agente foi ligado; a exceção de janela de TESTE-A já existia.
- Conferir em `tool_invocations` que as chamadas dos casos 1–6 estão ligadas ao turno (`trace_id` = `<sessão>|<client_request_id>`) e que `input_summary` **não** tem 11 dígitos (consulta do relatório §3).
- Registrar cada caso no relatório §7 com a evidência por alias e contagem.

## 3. O que só o Founder faz (§12.4)

1. Implantar `smith-api` e `smith-web`.
2. Colar os casos 1–5 e 7 no chat `core`; mandar o caso 6 do TESTE-A.
3. 🧑 Pedir à InfoCap o perfil que libera `/parcelas`, `/comissoes`, `/financeiro` (403 hoje, P-PILOTO-19) — não bloqueia; destrava `parcelas_em_aberto` de verdade.
