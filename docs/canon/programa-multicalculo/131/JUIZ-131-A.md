# ⚖️ JUIZ · SPEC-131-A · A madrugada da renovação

> Juiz fresco Opus 5.5 (`claude-opus-5-5`) · 13/10/2026 · read-only · diff `2cd6168..3ac24ef` (36 arquivos, +9190/−123) ·
> banco: só SELECT (MCP, projeto dcajcvlzcjbmyapmklil) · código que alcança banco: só com dublê. 📊 medido · 💭 ilustrativo.

## VEREDITO — **FAIL** (3 blockers; a estrutura está boa, o que falha é o que chega à corretora)

A espinha está certa e bem guardada: migration conforme o VERIFY, máquina de estados com CAS (estado + versão),
filtro `company_id` em toda leitura do repositório **e** a segunda trava em Python, idempotência por chave
`renov:<passo>:<company>:<dia>`, conferência independente do montador, Prosseguir com sete travas e sinal estreito na
guarda, nenhum dado pessoal em claro no banco. Os três blockers são do mesmo tipo: **o produto diz à corretora uma
coisa que não é verdade**: um motivo errado, uma moto tratada como carro e um aviso de licença que nunca dispara.

## BLOCKERS

### B1 · A InfoCap cai entre 00:30 e 02:00 → toda `pronta` vira `pendente(falta_dado)` e o dia sai "completo"
- **Medição (dublê, sem banco):** `madrugada._avaliar(item AUTO pronto, fonte=None)` → `pendente falta_dado faltando=13`
  (`scratchpad/juiz_infocap_fora.py`). O caminho: `calcular_dia` (madrugada.py:596-601) captura a falha da fonte e põe
  `fonte = None`. O comentário diz *"as prontas esperam a próxima chamada"*, mas o laço seguinte chama `_pedir` assim
  mesmo. Depois, `perfil_do_segurado` (madrugada.py:153) devolve None com `fonte=None` e `_avaliar` (:452-454) grava
  `falta_dado` com os 13 nomes.
- **O mesmo sintoma já está no banco:** 📊 `renovacao_dias` 2026-10-12 (canário) = `completo · 100.00 % · calculadas 0 ·
  pendentes 3`, das quais 2 são `falta_dado` com os **16** campos do perfil em `faltando` (o perfil não veio). A conferência conta
  `pendente` com motivo como feito (conferencia_da_renovacao.py:148).
- **Teste do produto:** sim. O ESTADO e o MOTIVO no banco mudam, e o aviso da corretora também (hoje: "falta um dado
  da apólice", completude 100 %, quando o certo é "a InfoCap não respondeu" e o dia incompleto). → **BLOCKER.**
- **Conserto mínimo:** no `calcular_dia`, sem fonte o item NÃO é reavaliado: fica `pronta` ou vai para `pendente(sem_conexao)`.
  Em `_avaliar`, perfil `None` por falha da InfoCap vira `sem_conexao`, nunca `falta_dado`. O guarda é um teste com a
  fonte que levanta exceção às 02:00 e que tem de ficar VERMELHO no código de hoje.

### B2 · Moto dentro da sigla AUTO é calculada como CARRO, falha calada como `calculo_fechado` e volta toda noite
- **Medição (SELECT):** renovação `4d9be9e8` (AUTO, ramo 31) → 2 pedidos (`0387bde9`, `e52e9faf`), 0 ofertas. No
  `e52e9faf` aparecem as recusas *"NUM PORTAS INVALIDO PARA MOTOCICLETAS"*, *"Moto - Carro reserva (Veículo) deve ser
  informado"* e *"Ramo divergente do selecionado"* (2 de cada), e o item terminou em `falhou · calculo_fechado`. O laudo I1
  (:179) diz que o código 31 cobre "Carro, Caminhão E Motocicleta", e a SPEC §9 deixa moto **fora** ("vida/moto → depois da 132").
  `grep -i "moto\|categoria\|especie"` em `pedido.py`, `madrugada.py`, `perfil_da_renovacao.py`, `motor.py` e `montador.js`
  não acha nada: não há detecção.
- **Volta toda noite:** `falhou` está em `ESTADOS_PREPARAVEIS` (renovacao.py:59). No canário, o mesmo item fez
  `falhou → pronta → calculando → falhou` (eventos 04:43 e 04:52). Até sair da janela, o mesmo calcularV2 condenado
  vai a ~15 seguradoras a cada madrugada.
- **Gate do canário (SPEC §6 "completude 100 %"):** 📊 75,00 %, e a única falha é esta moto.
- **Teste do produto:** sim. Muda o banco (`pendente ramo_nao_cotado` em vez de `falhou`), muda o aviso ("renove
  manualmente: moto" em vez de "1 falhou" sem motivo) e muda o efeito externo (calcularV2 no Agger). → **BLOCKER.**
- **Conserto mínimo:** o `buscaPlaca`/FIPE já está na mão do montador. Se o tipo for moto, recusar ANTES do POST com um
  motivo próprio, no molde do `veiculo_sem_combustivel` da F6. A renovação mapeia esse motivo para `pendente(ramo_nao_cotado)`.
  À parte, um teto de retentativa para `falhou` não passageiro (ver P2).

### B3 · D-131-36 (licença do Agger) nunca disparou ao vivo: 📊 0 eventos `licenca_agger`
- **Medição (SELECT):** `multicalculo_eventos` desde 12/10: `seguradora_recusou` 114 · `nova_oferta` 74 ·
  `conjunto_fechado` 10. **`licenca_agger` 0 · `prosseguiu_sessao` 0.** Houve logins reais: os dois runs do canário com
  motor real (00:36 e 01:46 −03) vieram depois do commit F3 (`96d178e`, 22:05 −03), o que mostra o código no ar.
  `_depois_do_login` (motor.py:1254, :1274) só grava se `sessao.licenca` não estiver vazio, e `extrair_licenca` lê só a resposta
  do POST `/usuario/login` (agger_sessao.py:263-276). O BLOCO 0 mediu a licença da AutoFleet em **`/usuario/current`**
  (BLOCO0-AGGER-AO-VIVO.md:18). O teste (`test_..._datas_da_licenca`) usa um corpo sintético.
- **Por que importa agora:** 📊 BLOCO 0: a AutoFleet tem `licenca` **2026-10-20** e `dataLimiteCalculo` 2026-10-27. Faltam ≤ 7 dias,
  então o aviso "vence em até 7 dias" já devia estar no ar.
- **Teste do produto:** sim. O aviso da corretora muda; sem ele, quando a licença vencer, a madrugada falha toda noite sem dizer por quê. → **BLOCKER.**
- **Conserto mínimo:** ler a licença onde ela foi medida (`/usuario/current`, GET já liberado pela guarda?), ou provar
  com um login real que o corpo do POST a traz. O guarda é o mesmo SELECT acima, que tem de dar ≥ 1 evento por conta logada.

## PENDÊNCIAS (não bloqueiam; cada uma com o que destrava)
- **P1 · A 3ª opção `franquia_reduzida` (📊 0 em 5 pedidos) segue a REGRA.** Não é defeito do código, mas, na prática, o efeito é
  morto. `anterior = _PADRAO ∪ lidas` (presets.py:408-409), e `_PADRAO.tipoFranquia = 1` (reduzida). Quando a ficha não diz a
  franquia, o `anterior` já sai reduzido **por suposição** e a `franquia_reduzida` fica idêntica, por isso
  `_sem_repetidas` a corta (:388-394). Só sobrevive quando a ficha diz "normal" (o teste `FICHA_A` prova isso). O canário rodou
  **sem o PDF** (docstring do canário), e o cadastro não trouxe a palavra. O que destrava: medir, em fichas reais COM PDF,
  quantas trazem a franquia legível (P-130B-12), e decidir se, com a franquia não conferida, a 3ª opção vira a "normal"
  (mais barata) ou se o aviso diz "2 opções: a franquia da apólice não foi lida".
- **P2 · Retentativa noturna sem teto** de `falhou` definitivo (`calculo_fechado`), em renovacao.py:59 combinado com madrugada.py:482.
  Destrava: N tentativas por item, ou só os `MOTIVOS_PASSAGEIROS`.
- **P3 · O teste do fio fecha os cálculos com `fechar_com_ofertas`, não com o motor REAL** (a SPEC §6 pede "motor REAL").
  A porta e o `de_apolice` são reais (test_spec131a_o_fio.py:311-323). O canário cobriu o motor real. Destrava: aceitar
  por escrito ou ligar o motor com robô dublê.
- **P4 · Comissão:** recusas no canário por comissão (📊 f07cea99: "ultrapassa o máximo de (30%)", "27 - Comissão não permitida",
  "deve estar entre 5% a 30%"; ebe82705: "DESCONTO X COMISSÃO"). Isso é o `per_c` anterior + `comissao_a_mais_pp` acima do teto da
  seguradora, ofertas perdidas. Destrava: o teto por seguradora (D-131-16).
- **P5 · `efeito="idempotente"` no disparo não é estrito:** uma queda entre `porta.calcular` e `transicionar("calculando")`
  (madrugada.py:541-551) gera um 2º pedido na retomada. Janela pequena; destrava: chave de idempotência no pedido por (renovacao_id, dia).
- **P6 · A ficha (com PDF) é lida 2× por item pronto por noite** (preparar + `_pedir`), em todas as noites da janela. O custo de
  modelo em produção NÃO foi medido (o canário rodou sem PDF). 💭 há cache documental (infocap_connector.py:~2304).
- **P7 · `calculo_fechado`/`calculo_falhou` não têm frase humana** (`FRASE_DO_MOTIVO` cai no `replace("_"," ")`), e o aviso
  diz só "K falharam", sem o porquê.
- **P8 · §13.9:** `scripts/bloco0_131a_agger_ao_vivo.py:323,600-604,681-684` usa nomes de corretora em variáveis de ambiente
  e rótulos (script de medição avulso, não produto).
- **P9 · A completude conta `pendente(falta_dado)` como feito** (é a fórmula da SPEC). O número que diz a verdade é
  `calculadas ÷ cotáveis` (📊 10-12: 0,00 %), e o aviso devia dá-lo em destaque.

## EVIDÊNCIA
| gate / ataque | comando | resultado |
|---|---|---|
| migration VERIFY | SELECT do cabeçalho (13 colunas) + `schema_migrations` | 📊 `4·4·1·1·1·1·2·1·1·1·1·2·0` = o esperado · versão `20261013003843` aplicada |
| testes 131-A (6 arq.) + 1310_f3 | `pytest tests/test_spec131a_*.py tests/test_spec1310_f3_contas.py -q` | 📊 **182 passed**, 23 warnings em 906,9 s · EXIT=0 |
| mutação 3 (desconhecido→AUTO) | `scratchpad/juiz_mutacoes.py` (em memória, controle antes) | controle VERDE → mutação **VERMELHO** (`DID NOT RAISE RamoIndisponivel`) |
| mutação 7 (econômica) | idem | controle VERDE → mutação **VERMELHO** (AssertionError; com a opção aceita: KeyError) |
| duas corretoras | test_spec131a_a_lista_e_a_conferencia.py:50 + leitura de `renovacao.py` (todo `listar/por_id/por_chave/dia/eventos` com `.eq(company_id)` e o refiltro em Python) + `_ler_o_pedido` `.eq(solicitante_company_id)` | sem cruzamento · banco: 📊 0 renovações fora da AutoFleet |
| concorrência | `transicionar`: `update … .eq(estado,de).eq(versao,v)` → `ConcorrenciaPerdida` (renovacao.py:432) | CAS presente |
| idempotência | chave `renov:<passo>:<cid>:<dia>` (tick.py diff) · UNIQUE do item · `de==para` sem mudança = no-op | OK |
| rollback | ROLLBACK do cabeçalho recusa com dado presente | 📊 hoje há 8 renovações canário: o rollback **recusa** (correto) |
| o produto chama? | `workflows.carregar_extras` + `@registrar_workflow` + `tick._renovacoes` · `INTELLIGENCE_TICK` padrão "1" | sim · 📊 0 `tenant_auxiliaries` de renovação ativos, 0 `work_runs renovacao.*`: hoje nada roda em produção |
| Prosseguir | motor.py:1218-1251 (7 travas, SELECT do 1×/noite, aceites vazios = desligado) · guarda: `prosseguir_valido` só `{email,senha,derrubaSessao}` = id do aviso deste contexto | correto · 📊 0 `prosseguiu_sessao` (nenhum Agger de pessoa) |
| dado pessoal | SELECT: doc com ≥ 3 dígitos, nome com espaço, dígitos longos em `dados`/`detalhes`/eventos | 📊 0 · 0 · 0 · 0 · HMAC presente nas 8 |
| canário órfãos | calc não terminal / renovação em voo | 📊 0 / 0 |
| `premio_atual` (SPEC §8) | SELECT | 📊 8/8 com prêmio |
| regressão 133-A (combustível) | leitura de montador.js / contrato.py | o mapa amplia (Flex = 6 mantido). A recusa antecipada só cobre o caso que a seguradora já recusava (📊 64/64). **Bateria não rodada por mim** |

**3 números 📊 reproduzidos:** (1) 0 de 5 pedidos com `franquia_reduzida` (todos `[anterior, completa_mais]`) ✓ ·
(2) completude 75,00 % = (2 calculadas + 1 pendente) ÷ 4, e calculadas÷cotáveis = 2/3 = 66,67 % ✓ ·
(3) 64/64 recusas "É necessário informar o tipo de combustível" (32 em `c388abf6` + 32 em `0387bde9`) ✓.

**LENTE DO DADO (meu SELECT):** o dia 2026-10-13 tem os 4 itens criados ≥ 03:33 UTC (filtro do canário): `2804e0c3`
calculada · `01e53c4d` calculada · `67fde58a` pendente `ramo_desconhecido` (MOBI) · `4d9be9e8` falhou. Isso dá 3/4 = **75,00 %**,
igual ao gravado, e a medida (04:52:52) vem depois da última transição (04:52:40). ⚠️ Sem o filtro, a tabela tem **7** itens
com `fimvig` em [13/10, 23/10]: os 3 de 13/10 de rodadas anteriores (2 `falta_dado` com o faltando do código pré-F6,
1 MOBI). Em produção eles entrariam: 6/7 = 85,7 %. Os dois números são honestos para a sua lista. O canário mede a lista filtrada.

## MAIOR LACUNA
O B1 e o P9 juntos: a completude, que é o OUTCOME da SPEC, pode dar **100 % num dia em que nada foi calculado** e a
InfoCap caiu. 📊 Isso já aconteceu uma vez no banco (10-12). Um número que fica verde quando o trabalho não aconteceu é
o defeito do §9.5 ("casar a tela não é responder certo").

## PRÓXIMA AÇÃO
Conserto único B1 + B2 + B3, cada um com um guarda que nasce VERMELHO no código de hoje. Depois, um canário de 1 noite com
moto e com a InfoCap derrubada às 02:00, e a confirmação (§6.1).

## CONFIANÇA — 80
Medido: VERIFY, canário por SELECT, mutações 3 e 7, cenário InfoCap-fora com dublê, código do Prosseguir e da guarda.
**Por medir:** a bateria inteira (regressão 129-B/133-A do montador e de `infocap_lookup`, que agora recusa documento
inválido) · o custo de modelo com PDF · se o corpo do POST de login traz mesmo a licença (B3 é inferência forte sobre 0
eventos; a causa exata não foi isolada) · se o item `4d9be9e8` é moto pela placa ou se a placa veio errada (as duas
hipóteses dão o mesmo blocker) · o Prosseguir ao vivo (0 Aggers de pessoa).

## NOTA — 72
