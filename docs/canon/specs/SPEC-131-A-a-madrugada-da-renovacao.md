# SPEC-131-A — A madrugada da renovação: tudo calculado antes das 7h, nada esquecido

> **v1.0 · 12/10/2026** · gerente Opus 5.5 · branch `spec/131-A-a-madrugada` (base `2cd6168`) · rito AAA v13 · nível **CRÍTICO**.
> Fonte: [proposta](../specs-propostas/SPEC-131-O-APLICATIVO-DE-RENOVACAO.md) §0–§9 (o detalhe e as notas moram nela) · laudo
> [I1](../programa-multicalculo/131/LAUDO-I1-O-MOTOR-E-A-MADRUGADA.md) §1–§5 · BLOCO 0: [leituras](../programa-multicalculo/131/BLOCO0-131-A-LEITURAS.md)
> e [Agger ao vivo](../programa-multicalculo/131/BLOCO0-131-A-AGGER-AO-VIVO.md). 📊 medido · 💭 ilustrativo.

## 0. EXECUTION CARD
```
OUTCOME ........ todo dia, por corretora, antes das 7h: cada renovação que vence em ≤ antecedência (padrão 10 dias) está
                 CALCULADA no Agger certo (3 opções) ou PENDENTE com o motivo à vista; nenhuma esquecida; a corretora sabe
                 quantas, por quê, e o dia fica VERMELHO se a conferência achar uma que faltou.
RISCO .......... 7 · alcance corretora 2 · saiu do prédio 3 (calcularV2 no Agger; entra na conta de uma PESSOA) · todo dia 2
SUPERFÍCIE ..... 2 · peça nova (orquestrador + tabela) sobre motor/porta existentes
PISO ........... CRÍTICO: migration de estrutura · sessão de terceiro (Agger da pessoa) · filtro company_id
NÍVEL .......... CRÍTICO · builders Opus 5.5 xhigh · juiz ‖ red team Opus 5.5 · LENTE DO DADO (o outcome é número diário)
O FIO .......... §2 · teste do fio `backend/tests/test_spec131a_o_fio.py` = 1ª entrega, VERMELHO
PARALELISMO .... F1 ‖ F2 ‖ F3 (arquivos disjuntos, §5) → F4 costura + canário
UNIDADES ....... 4 fatias · COESÃO: a máquina de estados e a conferência juntas (F1); ramo+opções+CPF (F2); sessão+guarda+teto (F3)
TIME ........... 3 builders + 1 costura · juiz ‖ red team · lente do dado · confirmação se houver blocker
REFERÊNCIA ..... interna: `test_a_maquina_de_lavar_vai_ate_o_fim.py` · MIGRATIONS-AUTHORITY · CLAUDE.md §7 · externa: §8
GATES .......... fio verde · 7 mutações vermelhas (§6) · 2 corretoras · migration VERIFY · canário real · bateria vs linha de base
O ELO .......... "nada esquecido PORQUE a conferência relê a InfoCap" → a conferência não importa o montador (AST) + mutação 1
FAIXA .......... 💭 4–6 h · fatia ≤ 1h15 · contexto do builder ≤ 300 k
```

## 1. O contrato
**Muda:** um trabalho diário por corretora no Work OS existente (tick + `work_runs` com chave `renov:<passo>:<company>:<dia>` + espera
durável da 129-A) · 4 tabelas novas (§3) · ramo desconhecido → `RamoIndisponivel` · o pedido da renovação pela ficha com as 3 opções ·
`antecedencia_dias` 15 → **10** · a política de sessão da madrugada · teto de sessões e prioridade 7 · substituto (ausência) · CPF/CNPJ
inválido barrado antes da InfoCap.
**Não pode mudar:** QCM e cotação do chat (prioridade 5, nunca Prosseguir) · `dono_da_apolice` e a regra do dono (D-131-0-03/31) · o leitor
da 130-B (só consumido) · **o motor nunca cai CALADO no Agger da corretora** · **nada é enviado a cliente** · nenhum scheduler, executor,
fila ou ledger paralelo (CLAUDE.md §5) · `comercial/metricas/renovacao.py` (BI) segue leitor · Prosseguir NUNCA em conta `global`/`teste`.

## 2. O FIO
```
smith-worker → intelligence/tick.py (a cada 5 min, por corretora com o aplicativo de Renovação ligado, no fuso da corretora)
 ├ 00:30 Work Run "renovacao.preparar"  → renovacao.preparar_dia(company_id, dia)
 │    fonte_infocap.renovacoes_cruas(dia, dia+antecedência+margem)  [CPF/CNPJ inválido barrado antes — ponto único, F2]
 │    → upsert renovacoes (UNIQUE company_id,sistema,codfil,nosnum,fimvig; endosso que muda fimvig: item novo, o velho "substituida")
 │    → por item, EM SÉRIE: dono.dono_da_apolice → ficha (130-B) → pedido.de_apolice(…, ficha=, config=)
 │    → estado pronta | pendente(ramo_nao_cotado · falta_dado · sem_conexao · sem_pdf · sem_dono_e_sem_conta)
 ├ 02:00 "renovacao.calcular" → para cada pronta com fimvig − antecedência ≤ dia (o atraso de ontem entra hoje), ordem (ramo, fimvig):
 │    porta.calcular(servico='renovacao', prioridade=7, politica_de_sessao='madrugada', renovacao_id=…, dono_user_id, vence_em_dias)
 │    → qual_agger.decidir (dono · ausência→aviso ao substituto · corretora+aviso nomeado) → motor (teto de sessões; sessão da
 │      pessoa mantida entre os pedidos DELA; Prosseguir só nas travas do §4) → calcularV2 × opções
 │    → renovacoes: calculando → calculada | falhou(motivo) | aguardando_agger
 ├ 05:30 "renovacao.conferir" (conferencia_da_renovacao.py, NÃO importa o montador): renovacoes_cruas DE NOVO → esperadas × itens
 │    → renovacao_dias; falta → item criado + evento `esquecida_pela_preparacao` + dia VERMELHO; InfoCap fora → `sem_conexao` + alerta
 ├ 06:15 desvio: o que segue aguardando_agger/falhou passageiro → Agger da corretora COM aviso nomeado (nunca calado)
 └ 06:45 "renovacao.avisar" → o canal de aviso in-app que JÁ existe (BLOCO 0 A8): "N prontas no seu Agger · M pendentes (porquê) · K falharam"
```

## 3. Dados — migration `backend/supabase/migrations/20261013_01_spec131a_renovacoes.sql` (expand-only)
```
renovacoes(id uuid pk, company_id → companies, sistema, codfil, nosnum, fimvig date, UNIQUE(company_id,sistema,codfil,nosnum,fimvig),
  ramo_sigla, ramo_agger int null, seguradora_atual, premio_atual numeric null, cliente_nome_curto, documento_mascarado,
  documento_hmac, dono_user_id null, dono_motivo, responsavel_user_id null, estado, motivo null, pedido_id null → multicalculo_pedidos,
  conta_agger_id null, conta_motivo null, proposta_ref null, calcular_em date, canario bool default false, criado_em, atualizado_em,
  versao int default 1)                          ⛔ telefone e CPF/CNPJ em claro NUNCA; nome só o primeiro nome (exibição)
renovacao_eventos(id, company_id, renovacao_id → renovacoes ON DELETE CASCADE, de, para, por, motivo, dados jsonb, criado_em)
renovacao_dias(company_id, dia, estado, esperadas, calculadas, pendentes, falharam, faltaram, completude_pct, cotaveis,
  calculadas_de_cotaveis_pct, detalhes jsonb, PK(company_id, dia))
membro_ausencias(id, company_id, user_id, substituto_user_id, de date, ate date, criado_por, criado_em,
  CHECK(user_id <> substituto_user_id), CHECK(ate >= de), FK (user_id, company_id) e (substituto_user_id, company_id) → company_members)
ESTADOS ligados:    listada · pronta · pendente · calculando · calculada · falhou · aguardando_agger · apresentada · enviada · substituida
ESTADOS reservados: vista · em_negociacao · recalculo · aceita · emissao_pendente · emitida · registrada · recusada · perdida
CHECK estado ∈ (ligados ∪ reservados) · estado ∈ (pendente, falhou, perdida) ⇒ motivo NOT NULL
RLS ligada nas 4 (policy por company_id do membro) + FILTRO company_id no repositório + teste com DUAS corretoras (CLAUDE.md §7)
```
APPLY · VERIFY (o OBJETO: tabelas, CHECK, UNIQUE, RLS, índices `(company_id, estado)`, `(company_id, calcular_em)`) · ROLLBACK escritos no
cabeçalho ANTES de rodar. Aplicada pelo gerente via MCP depois do verde da F1.

## 4. As regras
- **Antecedência** padrão **10** (D-131-01), por corretora em `servicos.renovacao.antecedencia_dias`; margem de leitura 💭 +3 dias.
- **Janela** (fuso da corretora, 7 dias/semana): preparar 00:30 · calcular 02:00 · conferir 05:30 · desvio 06:15 · avisar 06:45 ·
  `prosseguir_de 01:00 · prosseguir_ate 06:30`. Configurável em `servicos.renovacao.janela`.
- **Ramo:** família desconhecida → `RamoIndisponivel(motivo="ramo_desconhecido")`; ramo fora do Agger → `ramo_nao_cotado`; o item vira
  `pendente` com "renove manualmente" e CONTA na completude. Nunca AUTO por omissão (mutação 3).
- **As 3 opções** (`servicos.renovacao.opcoes`, 1–3, padrão `["anterior","franquia_reduzida","completa_mais"]`): (a) **anterior** =
  coberturas do ano anterior IGUAIS OU MELHORES (AUTO: preset novo `anterior` montado da ficha, sempre para cima; campo que a ficha não traz
  → o valor do preset completo e a marca "não conferido"; RE: `coberturas_re(extras=ficha)` + Básica reajustada) · (b) **franquia reduzida**
  (AUTO `tipoFranquia` reduzida; já era reduzida → cede o lugar; RE: a típica do ramo) · (c) **completa+** (o que os clientes pedem:
  pequenos reparos, D-MC-69). ⛔ **nunca** `economica` nem `minima` na renovação (mutação 7).
- **Comissão:** `per_c` do ano anterior + `comissao_a_mais_pp` só se o BLOCO 0 A5 provou o campo; senão fica o padrão de hoje e a P-131A
  registra (D-131-16).
- **CPF/CNPJ** com dígito inválido (inclui `000…`) barrado no PONTO ÚNICO da consulta à InfoCap, para todo chamador (P-1310-02).
- **Qual Agger** (D-131-04/08): renovação = Agger do DONO; dono com ausência ativa → o cálculo segue no Agger dele e o AVISO vai ao
  substituto; sem dono/sem conta/desconectado → o da corretora COM aviso nomeado ao admin; senha recusada → recusa explícita.
- **A sessão de madrugada (D-131-03, revê D-131-0-05):** "Prosseguir" sobre sessão aberta SÓ se TODAS: dentro de `prosseguir_de…ate` ·
  `servico='renovacao'` · conta `uso='membro'` da PRÓPRIA pessoa dona · **1× por conta por noite** (evento `prosseguiu_sessao` em
  `multicalculo_eventos`, conferido por SELECT antes) · BLOCO 0 A1 medido sem derrubar mais que aquela sessão · aceite T-156 registrado
  (sem ele, a política fica DESLIGADA por conta). Se a pessoa voltar depois: **não prossegue de novo**: Cancelar, espera durável de
  **1 hora** (Founder, 12/10), tenta de novo até 06:15; depois, o Agger da corretora com aviso nomeado. A exceção é um sinal no
  `EstadoDaGuarda` que só a política da madrugada liga (mutação 4).
- **Fila:** tudo enfileirado de uma vez, ordem (ramo, fimvig); **prioridade 7** (cotação continua 5 e passa na frente); o motor serializa
  por LOGIN e paraleliza entre logins; **teto de sessões** por processo (padrão 6) e **por corretora (padrão 1** até o BLOCO 0 A4 medir 2
  logins da mesma corretora juntos — com 📊 0 Aggers de pessoa hoje o custo é zero); a sessão de uma pessoa fica aberta entre os pedidos
  DELA na noite e sai no fim da fila dela, e sempre até 06:30.
- **Completude** (por dia, gravada): `(calculadas + pendentes com motivo) ÷ esperadas` — meta 100 % — e `calculadas ÷ cotáveis`.
  `calculando` às 05:30 sem batida do motor NÃO conta como feito.
- **Aviso 06:45:** por pessoa (dono/substituto) e ao admin, pelo canal in-app existente; nunca publisher novo. Nada ao cliente.

## 5. Fatias (cada arquivo, UM dono; `backend/` implícito)
| fatia | entrega | arquivos (só estes) |
|---|---|---|
| **F1 · lista, tabela, conferência** | fio VERMELHO · migration · repositório · máquina de estados · preparar/calcular/conferir/avisar · tick | `supabase/migrations/20261013_01_spec131a_renovacoes.sql` · `app/services/multicalculo/renovacao.py` (NOVO: repositório + máquina) · `…/madrugada.py` (NOVO: os passos) · `…/conferencia_da_renovacao.py` (NOVO) · `app/services/intelligence/tick.py` · o registro de workflow que o BLOCO 0 A8 apontar · `tests/test_spec131a_o_fio.py` · `tests/test_spec131a_a_lista_e_a_conferencia.py` |
| **F2 · o pedido e a consulta certos** | ramo · preset `anterior` · extras · opções · comissão · config · CPF | `app/services/multicalculo/pedido.py` · `portal_worker/multicalculo/presets.py` · `app/services/multicalculo/config.py` · `app/comercial/fonte_infocap.py` + o ponto único de consulta por CPF (BLOCO 0) · `app/utils/documento_br.py` (NOVO, se não existir validador) · `tests/test_spec131a_o_pedido_da_renovacao.py` |
| **F3 · a madrugada no Agger** | política de sessão · guarda · teto · prioridade · sessão mantida · substituto · desvio | `portal_worker/multicalculo/motor.py` · `…/agger_sessao.py` · `…/agger_guarda.py` · `…/robos.py` · `app/services/multicalculo/qual_agger.py` · `…/porta.py` · `tests/test_spec131a_a_madrugada_no_agger.py` |
| **F4 · costura + canário** | fio VERDE · 7 mutações · canário | consertos nos arquivos acima (F4 é o dono depois que F1–F3 fecham) · `scripts/canario_madrugada_renovacao.py` · `tests/test_spec131a_costura.py` |

**Contrato fixo antes do paralelo:**
```python
# porta.py (F3)
calcular(..., servico, dono_user_id=None, vence_em_dias=None, prioridade: int | None = None,      # None = 5; renovação passa 7
         politica_de_sessao: str | None = None, renovacao_id: str | None = None) -> dict          # "madrugada" só madrugada.py
# qual_agger.py (F3)
decidir(..., servico, dono_user_id, substituto_user_id=None, forcar_corretora_motivo: str | None = None) -> Decisao
# pedido.py (F2)
de_apolice(apolice, perfil=None, *, ficha=None, config=None, exigir_completo=...)   # assinatura igual; as opções vêm da config
class RamoIndisponivel(Exception): motivo: Literal["ramo_nao_cotado", "ramo_desconhecido"]
# config.py (F2) — chaves lidas por F1 e F3
servicos.renovacao.antecedencia_dias = 10
servicos.renovacao.janela = {"preparar":"00:30","calcular":"02:00","conferir":"05:30","desvio":"06:15","avisar":"06:45",
                             "prosseguir_de":"01:00","prosseguir_ate":"06:30","retentativa_min":60}
servicos.renovacao.opcoes = ["anterior","franquia_reduzida","completa_mais"]
servicos.renovacao.teto_sessoes_corretora = 1 ; MULTICALCULO_TETO_SESSOES (env, processo) = 6
# documento_br.py (F2)
documento_valido(doc: str) -> bool        # CPF 11 / CNPJ 14, dígito verificador, rejeita repetidos
# renovacao.py/madrugada.py (F1): o estado do item é DERIVADO dos multicalculo_pedidos/_calculos (pull, nunca callback do motor):
#   o passo "calcular" fica em espera durável e relê a cada 10 min até tudo fechar ou 05:30
# migration (F1): multicalculo_pedidos + politica_de_sessao text (CHECK in ('madrugada')) + renovacao_id uuid → renovacoes;
#   CHECK de opcoes/opcao + 'anterior','franquia_reduzida' (nomes fixos; F2 os cria em presets.py, F3 em porta.OPCOES)
```
F1 usa dublê de `porta.calcular`/`de_apolice`; F4 liga o real.

## 6. A régua e a prova
- **Teste do fio** (motor REAL, dublê só na borda: InfoCap HTTP, Agger HTTP, modelo): do tick ao aviso, numa corretora com 5 renovações
  (1 AUTO, 2 RE, 1 VIND, 1 sigla desconhecida) → 3 `calculada`/`aguardando`, 2 `pendente` com motivo, completude 100 %.
- **Mutações (cada uma VERMELHA, em worktree próprio, restaura por cópia):** (1) um item some da lista congelada · (2) a conferência lê a
  lista congelada · (3) desconhecido → AUTO · (4) Prosseguir fora da janela ou em conta `global` · (5) renovação com prioridade 5 ·
  (6) um escritor grava estado reservado · (7) `economica`/`minima` numa renovação.
- **Isolamento:** duas corretoras na mesma madrugada; 0 linha cruzada (repositório filtra; teste lê com o filtro e sem).
- **Lente do dado:** a completude do canário reconferida por um 3º caminho (SELECT direto × nova leitura de `/renovacoes`).
- **Canário real** (F4, ≤ 5 itens, corretora de ensaio, InfoCap e Agger da própria corretora, relógio injetado na janela): completude
  100 % · ≥ 1 cotável calculada no Agger · ≥ 1 não cotável como pendência · 0 `calculando` órfão · 0 linha em outra corretora · nada enviado.
- **Verba de modelo:** ≤ 💭 US$ 1,00 (estimativa escrita no livro-caixa ANTES de cada rodada).

## 7. Decisões desta execução (além de D-131-01…28)
| # | decisão | nota | contra |
|---|---|---|---|
| D-131-29 | Retentativa de madrugada quando a pessoa voltou: **de hora em hora** até 06:15 (Founder 12/10 noite; era 20–30 min) | F | 20–30 min |
| D-131-30 | Teto por corretora **1** até medir A4 (sem Agger de pessoa hoje, custo zero); configurável | 82 | 3 sem medir 60 |
| D-131-31 | Canário com relógio injetado (fora do horário real), mesmas peças do produto | 85 | esperar a madrugada 60 |
| D-131-32 | Todo subagente desta execução declara o modelo na 1ª linha; se não for Opus 5.5, é descartado e outro Opus 5.5 refaz (Founder) | F | — |
| D-131-33 | 📊 pico de 42 renovações de UM dono num dia (Resulta, 11× a média): **teto por conta por noite** (12) + **antecipar** até 7 dias o que cabe na sobra; vencidas acima do teto entram mesmo assim e o aviso diz | 85 | começar 01:30 60 |
| D-131-34 | A1 medido: Prosseguir derruba SÓ aquela sessão (`derrubaSessao` = id do aviso); a guarda libera só esse id; o corpo do login (traz o token da outra sessão) nunca é gravado | 90 | — |
| D-131-35 | Canário na corretora REAL de origem dos dados (a de ensaio tem 0 Aggers): ≤ 5 itens, marcado, InfoCap em processo, nada enviado | 85 | cadastrar Agger no ensaio (1 login em 2 contas) 30 |
| D-131-36 | O login do Agger traz a data da licença: evento `licenca_agger` + aviso antes de vencer; vencida → falha com motivo humano | 85 | ignorar 40 |

## 8. O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS
1. **https://knowledge.hubspot.com/object-settings/set-up-and-customize-pipelines** · faz: estágios com campo exigido e ganho/perdido ·
   modelamos: `pendente/falhou/perdida` exigem motivo (CHECK) e a máquina inteira desde já · rejeitamos: valor ponderado · juiz: grava
   `pendente` sem motivo → o banco recusa.
2. **https://linear.app/docs/board-layout** · faz: colunas por estado · modelamos: o estado é DERIVADO do trabalho, nunca arrastado ·
   rejeitamos: mover à mão · juiz: nenhum escritor de estado fora da máquina (grep + mutação 6).
3. **https://int.ezlynx.com/solutions/renewals-client-retention** · faz: fila de renovações com antecedência · modelamos: a lista do
   dia e o prêmio anterior guardado (para o "hoje × renovação" da 131-B) · rejeitamos: o portal deles · juiz: `premio_atual` no canário.

## 9. Fora
Telas, página, envio, Ausência na tela → 131-B · negociar → 135 · emissão → SPEC própria · vida/moto → depois da 132 · P-1310-06 → 132.
