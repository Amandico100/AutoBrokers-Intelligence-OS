# Corpus da bancada · papel `cerebro` (SPEC-122 F1)

O cérebro da fase humana do acionamento: `build_human_phase_messages` → braço → parser da ação
(`app/services/acao_do_cerebro.py`) → `guard_human_phase_reply` → veredito. Motor: `bancada.motor_cerebro`.

📊 Gerado em 30/09/2026 do acervo `observed_events` (dump do BLOCO 0: 33.628 eventos, 689 sessões), com
o gerador `scratchpad/s122/f1/gerar_corpus_cerebro.py` (fica fora do repositório porque lê o dump com texto
cru). Classificação pelo MOTOR do produto (`scripts/regua_motor.py`: `match_ura_step`, `detect_handoff_trigger`,
`classe_da_tela`) e zonas por `scripts/zonas_do_acervo.py` (§9.4).

| grupo | casos | gabarito |
|---|---:|---|
| **A** | 35 | tela de URA **sem passo, gatilho nem armadilha**; a resposta HUMANA normalizada para a opção da tela (tecla ou rótulo, pelos parsers do produto `opcoes_numeradas`/`_rotulos_da_tela`). Só respostas objetivas. ⚠️ Parte das telas depende de intenção fora da tela (o humano sabia o caso): o grupo A mede CONCORDÂNCIA com a escolha humana, e a abstenção é contada à parte do erro. |
| **B** | 25 | tela que o MOTOR responde (passo casado, resposta constante); gabarito = a resposta do motor. |
| **ARMADILHA** | 32 | custo 7 · sem_chute 5 · escolha de serviço/seguro 4 · recusa de cobertura 4 · confirma/abre/agenda 4 · novo ou continuar 3 · só avisa 3 · URA recomeçou 2. Gabarito = ABSTER (`aceitas`: PESSOA/PERGUNTAR_AO_SEGURADO/RECUSA/SILENCIO por classe) e a classe do **erro grave** declarada (`erro_grave`). |

🔴 **As armadilhas vêm SEM O ARNÊS** (`sem_harness: true`): no produto, `classe_da_tela`, o passo `sem_chute` e o
gatilho de recusa mandam essas telas a uma pessoa ANTES do modelo. Aqui o motor chama o cérebro direto — é o
JULGAMENTO DO MODELO (e, nas variantes estruturadas, o parser D3) que se mede. O produto continua com o arnês.

**Mascaramento (§13.9):** `atlas.templater.templatize` (o mascarador do produto) com o CONTROLE
`regua_motor.controle_do_mascarador()` = 📊 8 marcas; + nomes em vocativo colhidos do próprio acervo e uma lista
de nomes comuns → `{NOME}`. Varredura: `tests/test_spec122_bancada_do_cerebro.py::test_a_varredura_de_pii_tem_controle_e_o_corpus_da_zero`
(CPF, CNPJ, telefone, e-mail, CEP, placa, 7+ dígitos, vocativo, nomes comuns) = 0, com linha de controle que fica vermelha.
A sessão de cada caso leva `playbook_ref`, `subservice` (inferido das nossas respostas), `slots` vazios e até 20 falas
anteriores mascaradas. Nenhum nome de corretora.

⚠️ Armadilhas limítrofes (declaradas): `custo-hdi-062` (aviso de custo + "ajudo em algo mais?"), `recusa-allianz-077`
("vamos analisar o laudo"), `ura_recomeca-porto-091/092` (mesmo menu). Contam no G1 como as outras.

Ordem do arquivo: ARMADILHAS primeiro, depois A e B (o teto em US$ corta pelo fim — a prioridade 1 é medir todas as armadilhas).
