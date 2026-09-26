# SPEC-117 · RELATÓRIO DE EXECUÇÃO — O atendimento nunca perde a apólice que encontrou

> 26/09/2026 · branch `spec/117-apolice-persistente` · commit inicial `79c9e80` (`origin/main`)
> Rito: **PROTOCOLO AUTOBROKERS AAA v13.2 · O FIO** (D-PROTO-13)
> 📊 medido (data, fonte, comando) · 💭 ilustrativo, **nunca citável como fato** — CLAUDE.md §12.1

---

## §0 · O EXECUTION CARD

```
OUTCOME ..............  a apólice que o atendimento encontrou fica no caso até o fim; o ramo oficial decide
                        a tecla da URA, a seguradora e o portal; nenhum dado pessoal cru chega ao modelo
RISCO ................  7/8 — ALCANCE 3 (o segurado) · REVERSIBILIDADE 2 · FREQUÊNCIA 2 (todo atendimento)
SUPERFÍCIE ...........  2/3
PISO APLICADO ........  CRÍTICO por EFEITO (§3.2): altera o que vai para insurer_dispatch e portal_action
NÍVEL ................  CRÍTICO · gerente Opus 5.5 · builders Opus 5.5 xhigh · juiz Opus 5.5 ‖ red team
                        Opus 5.5 (frescos, cegos um ao outro) + confirmação curta se houver blocker
O FIO ................  SPEC §1 · o TESTE DO FIO (F0) foi a 1ª entrega e NASCEU VERMELHO
PARALELISMO REAL .....  F1 ‖ F4a (arquivos disjuntos) · F2 → F3 em SÉRIE (as duas tocam nodes.py)
UNIDADES .............  5 fatias (F0–F4) + canário do Founder
COESÃO ...............  construtor + escrita durável + troca dos leitores na MESMA SPEC
TIME .................  2 builders · juiz ‖ red team · ESCALAÇÃO se o red team achar PII no rastro
REFERÊNCIA ...........  interna: o caminho `core` que JÁ funciona (linha de controle do F0) ·
                        `backend/tests/test_a_maquina_de_lavar_vai_ate_o_fim.py` · externa: SPEC §9
GATES ................  SPEC §6 (G1–G10)
O ELO ................  "o atendimento perde a apólice PORQUE a porta de identidade devolve None" —
                        📊 MEDIDO. "os 68,9 % são POR ISTO" — 📊 REFUTADO (B0.6)
FAIXA DE RELÓGIO .....  💭 4–8 h · teto 600 k de contexto no gerente
MIGRATION ............  📊 NENHUMA — B0.4
```

### 🔴 DESVIO DE PROTOCOLO, REGISTRADO

O protocolo v13 previa **gerente, juiz e red team Fable 5.1**. O Founder determinou, na abertura desta
SPEC, **Opus 5.5** nos três papéis e nos builders. O protocolo foi atualizado para **v13.2** e o porquê —
com o limite honesto de que **a troca é uma decisão, não uma medição** — está em
`docs/canon/PROTOCOLO-AAA-EVIDENCIAS.md`. 📊 `grep -c "Fable" docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md`
→ era `7`, ficou `0`. ⛔ **Nenhum gate foi reduzido:** juiz e red team seguem frescos, paralelos e cegos
um ao outro; a confirmação curta segue obrigatória depois de blocker; a mutação dos guardas novos segue
no passo ③.

⚠️ **FATO sobre o modelo desta sessão:** o gerente rodou com o identificador de modelo que o harness
expõe como `claude-opus-5`. A ferramenta de subagente deste harness aceita a família (`opus`), não uma
versão exata — logo **não há prova por comando de que o binário atrás dos builders e dos julgadores seja
5.5 e não 5**. O desvio pedido foi aplicado onde é verificável (o protocolo, o CLAUDE.md, os pacotes);
onde não é, está declarado aqui em vez de afirmado.

---

## §1 · O BLOCO 0 — o que foi medido antes de escrever código

### 1.1 Preflight (CLAUDE.md §2)

```
$ git fetch origin
$ git rev-list --count HEAD..origin/main      → 0     🔴 a árvore está em dia
$ git rev-list --count origin/main..HEAD      → 0
$ git branch --show-current                   → spec/116-reserva → spec/117-apolice-persistente (nova)
$ git rev-parse HEAD                          → 79c9e8031f8650e7cb2f3950a161fed2d6b41cd1
$ git status --short                          → 1 M (diff vazio: só fim de linha), 3 D e 8 ?? —
                                                 todas anotações do Founder (.TXT e propostas).
                                                 ⛔ PRESERVADAS: nenhuma foi commitada nem apagada.
```

### 1.2 As verificações B0.1–B0.7

| # | verificação | resultado 📊 | comando |
|---|---|---|---|
| B0.1 | a porta exige identidade crua | **SIM** — `nodes.py:423-425` | `grep -n "_safe_infocap_policy_context" backend/app/agents/nodes.py` |
| B0.2 | o papel do atendimento não é `core` | **SIM** — `infocap_tool.py:425-426` (`_unmasked → agent_role in ("", "core")`); `graph.py:473` passa o papel | `grep -n "_unmasked\|agent_role=" …` |
| B0.3 | o `client_ref` sai nos dois papéis | **SIM** — `infocap_connector.py:552-562`, FORA do `if unmasked` | `sed -n 541,578p backend/app/api/infocap_connector.py` |
| B0.4 | a coluna durável é `jsonb` | **SIM** — `jsonb`, `is_nullable=NO` ⇒ **NENHUMA migration** | MCP `execute_sql` (SÓ SELECT) em `information_schema.columns` |
| B0.5 | leitores/escritores do contexto | 12 em `nodes.py`, 1 em `state.py`, 3 na bancada · **escritor único**: `tool_node:2251` | `grep -rn "infocap_policy_context" backend/app --include=*.py` |
| B0.5b | testes que exercitam a regra do ramo | **ZERO** | `grep -rn "selected_policy_ramo" backend/tests` → vazio |
| B0.6 | quantos dos 68,9 % são deste defeito | **NENHUM** (ver §1.3) | `python` sobre `RESULTADOS/atendimento_N1_03af4327….json` |
| B0.7 | o teste do fio nasce vermelho | **SIM** — 4 failed, 2 passed | `pytest tests/test_o_atendimento_guarda_a_apolice.py -q` |

### 1.3 🔴 B0.6 — a medição que REFUTA metade da premissa herdada

**FATO** 📊 26/09/2026, grupo `03af4327-80c5-4ec6-b21b-624299cd8542`, braço de produção
`anthropic:claude-sonnet-5`, 30 casos / 90 tentativas, pass@1 = 68,9 %. **13 casos** com ao menos uma
reprovação, classificados pelo veredito que reprovou:

| grupo | casos | quais |
|---|---|---|
| **(a) apólice encontrada e não transportada** | **0** | — |
| (b) não chamou a ferramenta esperada, ou chamou outra | **9** | `cpf-para-brisa`, `humano-cancelar`, `humano-cade-guincho`, `humano-demora-vidro`, `humano-bati-carro`, `portal-lanterna`, `portal-parabrisa-reparo`, `portal-farol`, `risco-alagamento` |
| (c) outro — não pediu o CPF no texto | **4** | `sem-id-mecanico`, `sem-id-sinistro`, `sem-id-eletricista`, `sem-id-guincho-motor` |

**INFERÊNCIA:** o N1 é de **turno único**; por definição não há apólice anterior a transportar. Logo
**esta SPEC não promete mover os 68,9 %**, e qualquer afirmação nesse sentido precisa de outra medição.

**FATO** 📊 e o N2 confirma o defeito de forma direta: `contexto_da_apolice_por_turno` = `[[], [], …]` em
**10 de 10** trajetórias N2 do atendimento, em **todos** os braços — inclusive `duble:perfeito`, que
acerta 30/30. Grupo `a2fb9be0-d25c-4789-9846-38d7f76ad300`. Um modelo perfeito não salva um fato que o
produto não guarda.

### 1.4 O teste do fio, nascendo vermelho (F0)

```
$ cd backend && python -m pytest tests/test_o_atendimento_guarda_a_apolice.py -q --no-header
E  AssertionError: o atendimento encontrou a apólice e NÃO a guardou — o contexto voltou None
E  AssertionError: a apólice do cliente é RESIDENCIAL e o acionamento recebeu 'auto' —
                   o ramo oficial não venceu o palpite do modelo
E  AssertionError: a mensagem 'ok' apagou a apólice do caso
E  AssertionError: sem contexto não há o que auditar — ver o teste do fio
4 failed, 2 passed, 15 warnings in 19.28s
```

Os **2 verdes** são as linhas de controle, e elas são o que dá direito à conclusão (CLAUDE.md §9.2):
`test_a_fronteira_mascara_a_identidade_e_preserva_a_apolice` (a máscara funciona **e** a apólice chega
inteira no papel mascarado) e `test_linha_de_controle_no_core_o_contexto_ja_nascia` (o MESMO fio, o
MESMO motor, o MESMO documento, só o papel muda → verde). Sem o segundo, o defeito poderia ser da
consulta, do dublê ou do `tool_node`.

---

<!-- SEÇÕES §2 EM DIANTE: preenchidas ao fim da execução -->
