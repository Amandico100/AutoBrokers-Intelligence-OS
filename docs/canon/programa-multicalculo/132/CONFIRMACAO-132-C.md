modelo: claude-opus-5-5

# CONFIRMAÇÃO do conserto da SPEC-132-C (o WhatsApp do corretor como atalho)

> Juiz NOVO, read-only. Pergunta única: **o conserto fechou os blockers e criou defeito novo?**
> Base `285cadc` → HEAD `bdfdfd0` (branch `spec/132-o-chat-e-a-cotacao`). O conserto são os commits
> `f483871..de42bed` (`fix(spec-132-C conserto)`). Migration `20261014_05` já aplicada (não rodei SQL).
> Data 📊 14/10/2026. Bateria em `scratchpad/confirma132c/bateria.sh`, saída em `scratchpad/confirma132c/saida.txt`.

## VEREDITO: FECHADOS 3/3 · nenhum defeito novo de nível blocker · 1 pendência nova (VALIOSA) · incidente íntegro

## 1. Os três blockers

| blocker | o conserto | prova (rodada nesta confirmação) | fechou? |
|---|---|---|---|
| **B1 (juiz)** portão do assistente falhava ABERTO | `webhook.py:2920-2925`: `purpose='assistente'` sem a plataforma confirmada → `return {"status":"ignored","reason":"atalho_nao_confirmado"}`; nunca segue para QCM/observer/pipeline | sonda do juiz `test_A2_eh_canal_falha…` (que AFIRMAVA o vazamento) agora **FALHA** = o vazamento sumiu; teste do repositório `test_o_portao_do_assistente_falha_fechado_com_o_banco_instavel` PASSA (dentro de `26 passed`) | **SIM** |
| **RT-132C-01** anti-laço só na entrada | `envio.py:296-306`: o cinto único `enviar` exige `db`, recusa destino `entrada.numero_do_produto` e reserva no teto de envios; todos os 11 chamadores no atalho passam `db=db` (grep: `entrada.py:244,303,330,340,345`, `turno.py:446,454,468,515`, `envio.py:329,361`) | `test_a_saida_nao_manda_para_instancia_do_produto` PASSA: U5 (linha da Alfa) → `False`, linha da Alfa e QCM → 0 envios; **controle U1** → sai 1 vez. Sonda K4: `sem db saiu: 0 \| com db saiu: 1` | **SIM** |
| **P1 (juiz+RT, promovido)** código não amarrado ao número declarado, sem teto global | `verificacao.py`: gerar exige número confirmado e o atalho ligado (`:259-266`); consumir só aceita remetente `_mesmo_telefone` do declarado (`:389-396`), não reescreve número nem `confirmado_em` (`:420-426`, UPDATE condicionado ao número); teto GLOBAL 💭 30/h (`:358-360`) | sondas `test_A3_codigo_vazado…`, `test_B2_codigo_nao_e_amarrado…`, `test_A4_forca_bruta…`, `test_B1_forca_bruta…` (que afirmavam o defeito) agora **FALHAM**; `test_o_codigo_vazado_mandado_de_outro_celular_nao_troca_a_identidade` PASSA (membro idêntico antes/depois + controle do número declarado verifica) | **SIM** |

As 6 sondas antigas que falham são exatamente as que afirmavam os defeitos (A2, A3, A4, A5[envio-lento — P4 do juiz, a volta agora tem teto real], B1, B2). As outras 22 passam.

## 2. A bateria (pela trava, um arquivo por vez)

```
test_spec132c_o_fio ......... 24 passed in 90.88s
test_spec132c_o_atalho ...... 26 passed in 17.40s
test_spec132c_verificacao ... 40 passed in 14.81s
test_spec133a_o_fio (QCM) ... 17 passed in 24.09s
ataques juiz+rt ............. 6 failed, 22 passed in 55.80s   (os 6 = os defeitos fechados)
sondas da confirmação ....... 4 passed in 14.47s
md5 das fontes antes/depois: conferido (nada mutado)
```

Não rodei os `--mutar` (o executor de mutação foi a causa do incidente; juiz read-only).

## 3. Regressões procuradas

| pergunta | resultado | evidência |
|---|---|---|
| o corretor legítimo ainda ativa (declara → código → ATIVAR do mesmo celular)? | **SIM** | `test_ativar_casa_o_codigo…` PASSA; sonda K3 PASSA |
| …e quando o WhatsApp entrega o JID **sem o 9º dígito** (contas antigas)? | **SIM** | sonda K1: declarado `+5521987650003`, ATIVAR de `+552187650003` → `[('5521987650003','Pronto, Pess')] \| verificado: True \| numero: +5521987650003`; o "oi" seguinte roda como `(BETA, U3)` (`_e164_de` canoniza antes do `.eq`) |
| QCM continua igual? | **SIM** | `test_spec133a_o_fio` 17 passed; `test_a_mesma_mensagem_ao_qcm_ou_ao_atendimento…` PASSA; o diff de `webhook.py` só toca o bloco do assistente (§4) |
| atendimento continua igual? | **SIM**, com uma ressalva latente | `casos.ts:489,640` ganhou `.neq('channel','whatsapp_assistente')`. `neq` do PostgREST também exclui `channel IS NULL`; a coluna tem default `'web'` (`schema_completo.sql:672`) e o builder mediu 📊 0 nulos em 14/10 → hoje não muda nada (pendência FUTURA: `or(channel.is.null,channel.neq.…)` se quiserem blindar) |
| "sem `db`, nada sai" quebrou envio legítimo? | **NÃO** | todos os chamadores de `atalho.envio.enviar/enviar_texto` passam `db` (grep acima); `canal.envio.enviar` (QCM) é outra função, assinatura `(db, company_id, …)`, intocada |
| a volta da cotação para o corretor normal ainda sai? | **SIM** | controle U1 do teste RT-01 → 1 envio |
| o perfil: trocar o número apaga a verificação? | **SIM** (já era) | `perfil_do_membro.py:184` zera `verificado_em` quando o número muda |

## 4. O INCIDENTE (trechos grudados no topo / ocorrência errada restaurada)

- `git diff 285cadc..HEAD -- backend/app/api/webhook.py`: **um único hunk** (`@@ -2893,6 +2893,37 @@`), só o desvio do
  assistente (C2 + conserto B1). O topo do arquivo é o original (docstring "Webhook API - Recebe mensagens do WhatsApp via
  Z-API" + imports). **Íntegro.**
- `entrada.py`: topo = docstring do módulo + imports; o diff do conserto é coerente (P2/P3/P4/P5); nenhuma função
  duplicada (`grep ^def | uniq -d` vazio); `ast.parse` OK nos 5 módulos do atalho. **Íntegro.**
- `verificacao.py`: o diff do conserto (`f483871~1..de42bed`) só contém as mudanças do P1 e do teto global, cada uma no
  lugar certo (`_consumir`: teto global → teto por telefone → código → membro ativo → número declarado → uso único →
  UPDATE só de `verificado_em`). Nenhuma ocorrência fora do lugar. **Íntegro.**
- `git status`: `backend/app` limpo (árvore = HEAD); nenhum commit posterior (`de42bed..HEAD`) tocou o atalho ou o webhook.

## 5. DEFEITO NOVO (pendência, não blocker)

### N1 · O teto GLOBAL de "ATIVAR" errados é um interruptor de desligar a ativação para TODAS as corretoras — VALIOSA

- **Onde:** `verificacao.py:358-360`. O teto global é conferido ANTES de tudo e conta qualquer remetente. 💭 6 números
  × 5 erradas/h = 30/h → a partir daí `_silencio("teto_global")` para todos, inclusive o corretor legítimo com o código
  certo (que não recebe o "Pronto" nem explicação). Sustentado a 30 mensagens/h, a ativação fica fora do ar.
- **Medição:** leitura do código (determinística: `>= TETO_GLOBAL…` devolve silêncio antes de procurar o código). A sonda
  K2 foi escrita (`confirma132c/test_confirma132c.py::test_K2…`) e passou, mas a linha impressa dela foi engolida pelo
  filtro da bateria — **o número não foi capturado**; trate como INFERÊNCIA forte, não 📊.
- **Teste do produto:** não vaza dado nem identidade (a segurança melhorou); muda o que chega ao corretor só sob ataque
  deliberado → pendência, não blocker.
- **Conserto sugerido (1 condição):** como agora o código só vale do número DECLARADO, um "ATIVAR" de número que não é
  `whatsapp_trabalho_e164` confirmado de NENHUM membro ativo nunca pode acertar — cale-o **sem contar** no teto global.
  O atacante deixa de gastar o orçamento de todos, e a força bruta continua impossível.

### Observações menores (FUTURA)
- `estado.TETO_DE_ENVIOS_POR_DIA = 300` 💭 por telefone e o teto de turnos é 200 💭: um uso pesado com respostas de 2+
  mensagens pode bater 300 envios antes de 200 turnos — os turnos seguem rodando (custo) e a `FRASE_DO_TETO` não sai.
- `numero_do_produto`/`reservar_envios` calam em erro de banco (fail-closed por desenho): num soluço do banco a volta da
  cotação se perde em silêncio (o resultado continua no chat do painel).

## 6. Confiança e o que ficou por medir

- ALTA para os 3 fechamentos (sondas antigas viraram vermelhas + testes do repositório com controle).
- Não medido: K2 com número capturado; ponta a ponta com Evolution real; a migration (já aplicada, não reverifiquei).

## NOTA: 88 / 100
Os três blockers fecharam com guarda que fica vermelha e controle; QCM e atendimento iguais; ativação legítima (com e sem o
9º dígito) funciona; incidente sem sequela. Perde pelo teto global que qualquer um com 6 números consegue usar para calar
a ativação de todos (N1) e pela K2 sem número capturado.
