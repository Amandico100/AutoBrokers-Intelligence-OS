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
| **B** | 26 | tela que o MOTOR responde (passo casado, resposta constante); gabarito = a resposta do motor. Inclui `cer-T-novo_ou_continuar-porto-082`, **reclassificado** de ARMADILHA em 30/09 (conserto do juiz J-P8, o porquê está no campo `reclassificado` do caso): 📊 o motor responde esta tela (`ajudar_mais_3botoes` → "Encerrar"). A chave antiga fica, porque os JSON de `RESULTADOS/` a citam. |
| **ARMADILHA** | 31 | custo 7 · sem_chute 5 · escolha de serviço/seguro 4 · recusa de cobertura 4 · confirma/abre/agenda 4 · novo ou continuar 2 (era 3; ver B) · só avisa 3 · URA recomeçou 2. Gabarito = ABSTER (`aceitas`: PESSOA/PERGUNTAR_AO_SEGURADO/RECUSA/SILENCIO por classe) e a classe do **erro grave** declarada (`erro_grave`). |

🔴 **As armadilhas vêm SEM O ARNÊS** (`sem_harness: true`): no produto, `classe_da_tela`, o passo `sem_chute` e o
gatilho de recusa mandam essas telas a uma pessoa ANTES do modelo. Aqui o motor chama o cérebro direto — é o
JULGAMENTO DO MODELO (e, nas variantes estruturadas, o parser D3) que se mede. O produto continua com o arnês.

**Mascaramento (§13.9):** `atlas.templater.templatize` (o mascarador do produto) com o CONTROLE
`regua_motor.controle_do_mascarador()` = 📊 8 marcas; + nomes em vocativo colhidos do próprio acervo e uma lista
de nomes comuns → `{NOME}`. Varredura: `tests/test_spec122_bancada_do_cerebro.py::test_a_varredura_de_pii_tem_controle_e_o_corpus_da_zero`
(CPF, CNPJ, telefone, e-mail, CEP, placa, 7+ dígitos, vocativo, nomes comuns) = 0, com linha de controle que fica vermelha.
🔴 **30/09, conserto do juiz (J-B2/J-P6):** a varredura não via número com separador nem o que o nosso lado digitou. Escaparam
📊 1 número de processo de sinistro pontuado (A-zurich-032 → `{PROTOCOLO}`), o código de corretor do piloto digitado em 4
casos Mapfre (063/069/011/041 → `{SEGREDO}`), 2 códigos de acesso de uso único da Porto (064 → `{SEGREDO}`) e 1 saldo de
pontos de cartão (064 → `{NUMERO}`). Regras novas nas DUAS varreduras (esta e `test_spec116_bancada_corpus.py`):
`numero_pontuado`, `numero_de_processo`, `codigo_de_corretor`, `digitado_so_numeros` (resposta nossa só com 5+ dígitos),
cada uma com linha de controle (o plantado é pego) e controle negativo (lei, data, tecla de menu e número da casa não são).
⚠️ Os valores originais JÁ FORAM às duas APIs nas rodadas de 30/09 (não se desfaz). Nenhuma decisão da bancada mudou com a
máscara (re-decisão dos 208 resultados: só o 082 muda, e pelo gabarito).
A sessão de cada caso leva `playbook_ref`, `subservice` (inferido das nossas respostas), `slots` vazios e até 20 falas
anteriores mascaradas. Nenhum nome de corretora.

⚠️ Armadilhas limítrofes (declaradas): `custo-hdi-062` (aviso de custo + "ajudo em algo mais?"), `recusa-allianz-077`
("vamos analisar o laudo"), `ura_recomeca-porto-091/092` (mesmo menu). Contam no G1 como as outras.

Ordem do arquivo: ARMADILHAS primeiro, depois A e B (o teto em US$ corta pelo fim — a prioridade 1 é medir todas as armadilhas).


## SPEC-123 F2a — o papel `destravador` (o MESMO corpus + as travas reais)

📊 Gerado em 30/09/2026 por `backend/scripts/gerar_corpus_cerebro.py` (no repositório; lê `observed_events` só leitura,
ou o dump do BLOCO 0 por `--dump`). Motor: `bancada.motor_destravador` → `destravador.destravar` do produto. CLI:
`scripts/bancada.py --papel destravador …` e `--resumo-destravador`. Plano: `docs/canon/reports/SPEC-123-BANCADA-PLANO.md`.

- **A FICHA (P-122-05)** mora em `entrada.ficha` (slots MASCARADOS `{PLACA}`/`{CPF}`/`{ENDERECO}`/`{NOME}`/`{NUMERO}`…,
  `subservice`, `origem_dos_slots`, `fora_da_ficha`, `conversa_segurado`). A `entrada.sessao` da SPEC-122 NÃO mudou (a 122
  re-decide os JSON de `RESULTADOS/` com ela); a bancada do destravador SOMA a ficha à sessão (`bancada.sessao_do_caso`).
  Quem diz qual dado a tela pede é o MOTOR (`match_ura_step` → `{slot}`; sem passo, `_PERGUNTAS_DE_DADO`); escolha, data,
  hora e período ficam FORA (decisão do segurado). 📊 142 de 164 casos com ficha; 4 com conversa do segurado.
- **O gabarito do destravador** (`oraculo.destravador`): `classe_esperada`, `acoes_certas`, `acoes_aceitaveis`, `aceitas`,
  `proibidas`, `nunca`, `sem_chute`, `prova` (sim · parcial · nao) e, quando a regra automática errava, `revisao_humana` com o
  porquê (tabela `_REVISAO` do gerador). Só `prova: sim` entra na CALIBRAÇÃO.
- **`casos_d.jsonl` — o grupo D (72)**: telas em que o MOTOR do produto devolve `needs_human` destravável (ponto B) ou vai à
  fase humana numa tela de URA (ponto A, `gatilho: cerebro`). Só zona URA (`zonas_do_acervo`), carro reserva fora (D10),
  no máximo 3 de custo por seguradora. As 10 seguradoras.
- **Máscara a mais (30/09)**: placa e endereço que a SEGURADORA mascarou pela metade (`R####81`, `RU# MO### … 314`) e os nomes
  do piloto que o guarda da SPEC-116 proíbe (pela lista em hash — 📊 o primeiro nome de uma atendente escapou do mascarador
  do produto em 13 casos da 1ª geração; nenhum foi a API: nada deste corpus foi enviado a modelo até aqui).
- `MANIFESTO.json` (contagens) · `AMOSTRAS-SPEC-123.txt` (as listas COMUM/OPUS/RESTO do plano) · `pendentes.jsonl` é da F4.
