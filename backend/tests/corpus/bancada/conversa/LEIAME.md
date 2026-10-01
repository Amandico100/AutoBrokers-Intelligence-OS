# conversa — o segurado simulado (SPEC-125 S0, nível N3)

Uma CONVERSA inteira: um modelo barato faz o papel do segurado (persona, objetivo escondido, fatos do caso) e
conversa com o AGENTE DE ATENDIMENTO REAL — `graph.invoke_agent` com o `_build_initial_state` de produção —, com
dublês só na borda (banco, linha do agente, busca de cartas, MCP, visão, ferramentas). O fio e o que cada juiz
mede estão no cabeçalho da seção `SPEC-125 S0` de `app/services/evals/bancada.py`.

- `casos.jsonl` — 16 cenários do laudo INV-ATENDIMENTO §5.2 (C1–C16; críticos: C6, C7, C10, C13, C15, C16) + 2
  rajadas (R1: 5 frases; R2: 8 fotos + 1 texto, com as descrições como o produto as recebe da visão). Gerado por um
  script de rascunho a partir de fatos FICTÍCIOS; nenhum CPF, placa, telefone ou nome real — só marcadores
  (`{{CPF:C1}}`), materializados na hora (`dubles.materializar`).
- `agente_molde.json` — o molde do produto (`lib/admin/agent-blueprints-canonical.ts`, EVEN_ATTENDANCE_BLUEPRINT
  v2) com as variáveis padrão. `--agente-id <uuid>` troca pelo prompt REAL de um agente (só SELECT, nunca liga).
- Os estados das ferramentas vêm de um caso N2 de `atendimento/` (`dubles_de`) e o cenário só sobrescreve o que muda.

## O cenário
`fatos.<chave>`: `valor`, `fonte` (`apolice` · `telefone` · `conversa` · `conversa_anterior` · `abertura` ·
`deduzivel` = conhecido antes do 1º turno; `segurado` = conhecido quando ele disser), `perguntas` (regex sobre o
texto SEM acento que identifica o agente PEDINDO o fato), `conhecido_com`, `nota` (para o simulador).
`roteiro.falas_fixas`: as primeiras rajadas, literais (string = texto; `{"imagem": "<descrição>"}` = foto).
`gabarito`: `pessoa` (obrigatoria · proibida · livre), `efeitos_exatos`, `efeitos_proibidos`,
`max_perguntas_antes_da_pessoa`, `protocolo_exato`, `deve_conter_algum`, `nao_deve_conter`, `sem_ferramenta`,
`tool_proibida_com`, `nao_afirmar_cobertura`, `max_baloes_por_turno`, `criterios_llm`.

## Rodar (o teto é do LEDGER, `details.papel='conversa'`, relido durante a rodada)
    cd backend
    python scripts/bancada.py --papel conversa --braco openai:gpt-6-luna:low --cenarios C14 --k 1 --teto-provedor 0.05 --ledger-desde <ISO> --saida <scratch>/conv.json
    python scripts/bancada.py --resumo-conversa "<scratch>/conv*.json" [--recalcular]

⚠️ Esperado FALHAR no prompt de hoje (laudo): C4 (janela de 15 mensagens), C11 (sem identificação por telefone),
C13 (o fiscal da honestidade reescreve o acionamento).
