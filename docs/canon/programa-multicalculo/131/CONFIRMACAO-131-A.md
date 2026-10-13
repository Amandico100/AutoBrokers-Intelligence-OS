# CONFIRMAÇÃO 131-A · juiz de confirmação (protocolo §6.1) · 13/10/2026

Modelo: claude-opus-5-5 · diff julgado: `cf12213..62f95a8` (17 arquivos, +1430/−68) · branch `spec/131-A-a-madrugada`
Mutação feita num worktree temporário em `62f95a8` (scratchpad, sem link; `.env` copiado; removido no fim). Árvore principal intocada.

## VEREDITO — PASS COM RESSALVAS (4/4 blockers fechados; 0 defeito novo que bloqueie; 3 menores)

## OS BLOCKERS
| blocker | estado | conserto | guarda VERMELHO sem o conserto (📊 13/10, worktree) |
|---|---|---|---|
| **RT-B1** desvio recalcula o que já saiu | **FECHADO** | `madrugada.py:783` `acompanhar` antes da lista + `:795` pula pedido com oferta ou cálculo `disparando/calculando` | sem as 2 linhas → `2 failed, 1 passed` (`test_rt_b1_o_desvio_nao_recalcula…`, `…nao_leva_o_que_esta_no_robo`); o 3º é controle (o desvio continua) |
| **J-B1** InfoCap fora → falta_dado, dia completo | **FECHADO** | `calcular_dia :706` (sem fonte → `pendente(sem_conexao)`, sem reavaliar) · `_avaliar :473` · `perfil_do_segurado :154/:163` (`FalhaDaInfocap`→`SemConexao`) · conferência tira `sem_conexao` do numerador e trata InfoCap VAZIA com itens do período como `sem_conexao` | 4 trechos revertidos → `2 failed` (`test_j_b1_infocap_fora_as_duas…`, `…falha_no_meio_do_perfil…`) |
| **J-B2** moto vira carro e volta toda noite | **FECHADO (com ressalva N1)** | moto pela InfoCap (`perfil_da_renovacao.py:319` marca → `pedido.de_apolice` → `ramo_nao_cotado`); moto pela placa (`agger_robo` `tipoVeic=='m'` → `veiculo_moto`, antes do POST); `falhou` definitivo não volta (`madrugada.py:552`); passageiro volta ≤ 2 noites e vira `pendente(precisa_de_voce)` (`:556`) | marca off → `6 failed, 1 passed` (5 parametrizações + o fio; o que passa é o controle do carro); retentativa off → `2 failed` (`test_j_b2_*`) |
| **J-B3** licença nunca gravada | **FECHADO no código, NÃO provado ao vivo** | `agger_sessao.py:349-353` lê `GET /usuario/current` e `POST /usuario/login/pdocs` interceptados; sem o `current` do app, UM `fetch` na página aberta (`:279`), nunca `goto` | leitura e GET off → `2 failed, 2 passed` (`test_b3_a_licenca_vem_do_current…`, `…um_get_na_sessao_aberta_nunca_goto`); os 2 verdes são de forma (extrator/motor) |

Controle sem mutação, mesmo worktree: `18 passed, 30 deselected` (rc 0).
📊 SELECT 13/10 (`multicalculo_eventos` desde 12/10): `licenca_agger` **0**, `prosseguiu_sessao` **0** — o conserto não está no ar
(branch não implantada). O guarda que o juiz pediu para o B3 (≥ 1 evento por conta logada) só se cumpre no canário depois do Implantar.

## OS 8 ARQUIVOS `test_spec131a_*` (um processo, árvore principal, HEAD 62f95a8)
`213 passed, 21 warnings in 1542.65s (0:25:42)`

## ATAQUES (pergunta 2)
- **(a) adoção do pedido do dia (J-P5)** — filtra `company_id` E `renovacao_id` (📊 SELECT: 0 pedidos com company ≠ a da renovação) e exclui o
  `pedido_id` atual, então o desvio de um `falhou` da mesma noite NÃO adota o pedido da dona. Nunca adota outra renovação/corretora. Ver N3.
- **(b) `falhou` definitivo / `precisa_de_voce`** — nenhum some: `_da_noite` mantém `falhou` enquanto `fimvig ≥ hoje`; `precisa_de_voce` é
  pendente com frase. ⚠️ Assimetria: `precisa_de_voce` CONTA como feito na completude, `falhou` definitivo não (N4).
- **(c) franquia NORMAL no `anterior`** — `presets.py:417`; `tipoFranquia` ∈ `CHAVES_DE_COBERTURA` e fora das `lidas` → vai em `nao_conferidas`
  (marcado). O `anterior` fica com franquia maior (preço menor, cobertura pior), mas marcado; a `franquia_reduzida` volta como 3ª opção. Sem defeito.
- **(d) janela/noite/marca** — `prosseguir_de<ate` dentro de 00:00–07:00 nos dois leitores (`config._janela_limpa`, `motor.prosseguir_na_madrugada`),
  então a "noite" de meio-dia a meio-dia tem um Prosseguir só. A marca é gravada ANTES do clique; falha na escrita → Cancelar (fail-closed). Se o clique
  falhar depois da marca, a noite perde o Prosseguir e o item vai ao desvio das 06:15: nada fica preso. ⚠️ A marca é `upsert ignore_duplicates`, então ela
  não é mutex entre dois grupos da mesma conta (já era assim; `_cabe_sessao` segura 1 sessão por conta).
- **(e) QCM 133-A** — `JS_PREPARAR` é compartilhado: moto no QCM/cotação agora recusa antes do POST (antes: ~16 recusas). O resultado é o mesmo (0 oferta),
  mas o texto diz "renove manualmente" fora da renovação (N2).
- **(f) `/usuario/current`** — `page.evaluate(fetch)` só devolve o status; o corpo é lido só pelo interceptador (`extrair_licenca`: só datas). Logs só com
  `type(e).__name__`. Teste: `GET /cotacoes == 1` (sem goto a mais). Sem defeito.
- **(g) completude** — numerador = calculadas + pendentes com motivo, MENOS `sem_conexao`. É mais estrita que a fórmula da SPEC §4 (o RT-P2 pedia decisão
  do Founder). Só está registrada no laudo do red team, não em `FOUNDER-DECISIONS`/`CHANGE-ADDENDA`. Registrar.

## DEFEITOS NOVOS (nenhum BLOCKER)
- **N1 · ESSENCIAL · a moto pela placa fica `falhou(veiculo_moto)` sem frase.** 📊 `frase_do_motivo('veiculo_moto')` = "veiculo moto";
  `_texto(...)` = `"… 1 falharam (veiculo moto: 1)"`. O mesmo com `veiculo_sem_combustivel`, que antes do conserto era `calculo_falhou` (com frase e
  retentativa) e agora é definitivo e cru. O guarda J-P7 não enumera os `veiculo_*` (`MOTIVOS_LEGIVEIS` do robô). E o item fica cotável + `falharam`,
  em vez de `pendente(ramo_nao_cotado)` (o conserto mínimo do J-B2), então a completude fica < 100 % até o fimvig. 💭 É o caminho que mais vai disparar:
  📊 `veiculo_nao_cotado('HONDA CG 160 FAN')` = None (a descrição real não casa) e o rótulo de moto da InfoCap não foi medido.
  **Teste do produto:** muda o texto do aviso e o estado no banco. Não é mentira (diz "moto"), por isso não bloqueia.
  **Conserto (≤ 5 linhas):** frase para `veiculo_moto`/`veiculo_sem_combustivel`, incluir `veiculo_*` no guarda J-P7, mapear `veiculo_moto` →
  `pendente(ramo_nao_cotado)` na derivação.
- **N2 · VALIOSA · QCM/cotação de moto recebem "renove manualmente".** `agger_robo.MOTIVOS_LEGIVEIS["veiculo_moto"]`. Texto por serviço.
- **N3 · FUTURA · a adoção pega pedido `fechado/falhou` do dia.** Numa 2ª rodada no MESMO dia (o canário com `ignorar_espera`), o recálculo legítimo
  é trocado pela adoção do pedido que já falhou. Em produção (uma noite por dia) não ocorre. Conserto: adotar só `aberto`/em voo.
- **N4 · decisão · `precisa_de_voce` conta como feito na completude** (o dia pode ficar "completo" depois da 3ª noite de falha passageira). O aviso
  agora traz sempre "N calculadas de M cotáveis", o que reduz o dano.
- **Guarda de forma:** `test_moto_pela_placa…` confere `"erro: 'veiculo_moto'" in js` (regex sobre o código, §9.4). O motor JS não roda no teste.

## NOTA — 86 / 100 · confiança 85 %
Os 4 blockers foram consertados, e cada um tem guarda que fica VERMELHO com o trecho revertido e linha de controle verde. Desconto: N1 (o caminho real da
moto sai cru e não cotável), o B3 ainda sem prova ao vivo e a mudança da fórmula sem registro.
