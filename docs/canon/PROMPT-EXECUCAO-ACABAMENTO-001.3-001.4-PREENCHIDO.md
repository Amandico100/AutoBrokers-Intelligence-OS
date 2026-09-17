# PROMPT DE EXECUÇÃO — ACABAMENTO das EXTRA-001.3 e 001.4 · AAA FAST (protocolo v12.1) · PREENCHIDO em 17/09/2026

> Cole este texto inteiro num chat **NOVO** do Claude Code, modelo **Opus 5**, effort **high**, na árvore
> `AutoBrokers-FIX`. É uma execução pequena (💭 45–60 min), com duas tarefas fechadas. Nada a trocar.
> Leia antes: `CLAUDE.md` inteiro · `docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md` inteiro, UMA vez · as linhas
> D-PILOTO-* e D-PROTO-* de `docs/canon/FOUNDER-DECISIONS.md` · o template
> `docs/canon/reports/SPEC-EXECUTION-REPORT-TEMPLATE-FAST.md`. ⚠️ "v11.2", "opção B", "laço curto" são nomes
> históricos: o rito é só o do protocolo.

Você é o **EXECUTOR**. Uma sessão, do card ao push. Preflight (CLAUDE.md §2): `git fetch origin` ·
`HEAD..origin/main` = 0 · árvore limpa · registre o HEAD. Python de dentro de `backend/`, `PYTHONIOENCODING=utf-8`.
Branch: `feat/acabamento-001-3-001-4`. Autorizações: nenhuma mensagem a segurado, seguradora, grupo ou pessoa real;
banco só SELECT; nenhum segredo no chat, relatório ou commit; nunca `git add -A`.

## As duas tarefas

**T1 · O "um instante" à seguradora só quando há uma PESSOA do outro lado (EXTRA-001.4 D3).**
Hoje `perguntar_ao_segurado` em `backend/app/services/dispatch_router.py` (≈ linha 3153) envia
`HOLDING_A_SEGURADORA` à seguradora sempre que uma tela pede um dado que só o segurado sabe. Com o robô da URA do
outro lado, texto livre numa tela de dado pode ser lido como resposta inválida ou contar tentativa. Regra nova:
o holding sai **só** quando a sessão está na fase humana da seguradora (o mesmo critério que o hub
`insurer_dispatch_service.py` já usa para "humano da seguradora" / `state == "human_phase"`); com robô, **nada sai**
à seguradora — a pergunta vai ao segurado, a espera fica na sessão, e a resposta segue quando vier. O mesmo vale
para o holding do Vigia (`backend/app/tasks/dispatch_watchdog.py` ≈ linha 713, "D3 — o segurado não respondeu a
tempo"). Prove com o guarda que já existe (`backend/tests/test_o_humano_da_seguradora_e_atendido.py`): acrescente
o PAR — com robô, zero envios à seguradora; com pessoa, um holding — e a mutação que o deixa vermelho. Atualize o
comentário de `PERGUNTA_HOLDING_S` (a Allianz encerra por inatividade em ≈ 103 s): com robô, quem cobre a
inatividade é a reentrada do corredor, não o holding. Se ao ler o código você concluir que a reentrada NÃO cobre
o caso do robô, não invente outra coisa: registre como pendência com a medição e siga.

**T2 · O isolamento da 001.3 provado com DOIS tenants reais (P-E0013-08, CLAUDE.md §7).**
`company_internal_numbers` (migration `20260916_01`), o leitor `numeros_da_casa` em
`backend/app/services/o_grupo_so_o_que_importa.py` e a rota `app/api/dashboard/internal-numbers/route.ts` foram
provados com dublê. Escreva o teste com dois `company_id` reais lidos do banco (só contagens; nunca telefone ou
nome no teste), no molde de `backend/tests/test_o_pulso_360_nao_pertence_a_infocap.py` ou do guarda de dois tenants
da 001.6 (`G7` em `test_a_cobranca_chega_a_quem_deve.py`): o número cadastrado na corretora X não é "da casa" na
corretora Y; a guarda única `o_grupo_pode_saber` com a mesma conversa-molde em X e Y dá resultados independentes;
a rota recusa `company_id` alheio. Feche a pendência em `docs/canon/PENDENCIAS.md` com a prova, ou re-justifique.

## O laço (protocolo §5) e os tetos (§10)

① CARD (12 linhas) + BLOCO 0: 3 premissas no máximo (quem é o critério de "fase humana" hoje; quem chama o holding;
como o teste de dois tenants da 001.6 lê os tenants). ② BUILD, uma fatia só. ③ provas: compile, os guardas tocados,
mutação dos guardas novos, e a régua `backend/scripts/medir_rota.py --todas --com-espelho --comparar-com` a linha de
base commitada (nenhuma rota pode perder respondidas). ④ JUIZ: um subagente **Fable 5.1** read-only (o piso §3.2
vale: T1 muda o que SAI para a seguradora), com `docs/canon/pacotes/PACOTE-JUIZ.md`, o card, o diff, os comandos e
a lista de ataques. Lente do dado: NÃO. ⑤ conserto único. ⑥ suíte inteira UMA vez, depois do conserto, sozinha,
triada por diff contra a base; relatório ≤ 10 KB (`docs/canon/reports/SPEC-ACABAMENTO-001.3-001.4-EXECUTION-REPORT.md`,
no template FAST); `git push origin HEAD:main` com a saída colada; telemetria pelo script
`python backend/scripts/medir_execucao_claude_code.py --sessao atual`. Tetos: ≤ 120 turnos, ≤ 250 k de contexto,
≤ 2 agentes (juiz + confirmação se houver blocker). Nunca sessão nova; nunca "mais um agente".

Mensagem final ao Founder ≤ 12 linhas: o que mudou, o que ele deve Implantar, a nota 0–100 e a telemetria.
