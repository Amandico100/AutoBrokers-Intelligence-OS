# SPEC-128 — A prova do Agger · relatório de execução

> 04/10/2026 · branch `spec/128-a-prova-do-agger` · base `c2e0bb9` · código até `9db6372` · rito AAA v13, 🔴 CRÍTICO pela soma ·
> SPEC `specs/SPEC-128-a-prova-do-agger.md` (v2.1) · resultado `programa-multicalculo/A-PROVA-DO-AGGER.md`

## EXECUTION CARD
```
OUTCOME ..............  o 129-B nasce de NÚMEROS: E0–E21 respondidos (E0 E2 E3 E5 E7 E16 E20 com 📊), capacidade, contrato do
                        cálculo auto provado contra fixtures saneadas, portão de preço pronto · nada muda para o segurado
RISCO ................  6 — ALCANCE 3 (CPF real "cotado recentemente" nas seguradoras) · REVERSIBILIDADE 3 (nº de cálculo na
                        seguradora) · FREQUÊNCIA 0
SUPERFÍCIE ...........  2 — peça nova (contrato + leitor no worker) + gerador sobre o redator único
PISO APLICADO ........  nenhum no código; o vazamento em fixture versionada é irreversível → red team de vazamento
NÍVEL ................  🔴 CRÍTICO · builders Opus 5.5 · juiz ‖ red team ‖ lente · confirmação · captador revisado 2× antes do 1º cálculo
O FIO ................  bruto (HAR / captura) → gerador → fixture → leitor → 22/12 e 21/11 (`test_o_fio_do_bruto_ao_leitor`)
PARALELISMO REAL .....  F1 builder (gerador, portal_worker/multicalculo, fixtures, 2 testes) ‖ F2 medidor ao vivo (só rascunho) → F3 gerente
UNIDADES .............  U1 fixtures · U2 contrato + leitor · U3 medições E0–E21 · U4 documento da prova
COESÃO ...............  U1+U2 juntas (o formato da fixture é a entrada do leitor)
TIME .................  gerente · builder F1 · medidor · revisor cego da SPEC · 2 revisores do captador · juiz ‖ red team ‖ lente ·
                        builder do conserto · confirmação
REFERÊNCIA ...........  interna `backend/portal_worker/redaction.py`, `fixtures/infocap_contract_shapes/` · externa SPEC §4 (5 URLs)
GATES ................  G1–G10 (SPEC §9), cada guarda novo com mutação vermelha
O ELO ................  "a fixture é segura PORQUE passou pelo gerador": diferencial contra o bruto 0 + G1 · o B1 mostrou que o elo
                        tinha um buraco (segredo nascido em texto livre) → fechado no redator, no gerador, no leitor e no G1
FAIXA DE RELÓGIO .....  💭 5–8 h · 📊 executor 231 min de relógio ativo; o laço inteiro ~7 h (o medidor 94 min, a bateria ~1h30)
```

## 1. O que mudou
- **Contrato do cálculo** `backend/portal_worker/multicalculo/{contrato,leitor_agger}.py`: pedido auto com os 16 obrigatórios medidos
  (E3), ajustes, ofertas sem login/senha/URL, 9 famílias de resposta (nova: **DADO**, D-128-02), rodadas e eventos (nova oferta,
  oferta atualizada, recusa, conjunto fechado uma vez). Mora no worker porque o adaptador da 129-B mora lá (📊 0 import de `app.*`).
- **Fixtures saneadas** `backend/tests/fixtures/agger/` (5 + MANIFESTO): 2 gravações de 18/09, a configuração, e 2 capturas ao vivo
  (16 cálculos), por `backend/scripts/agger_fixtures_saneadas.py` — lista branca por caminho, pseudônimo por ordem de aparição, URL
  e chave fora, diferencial contra o bruto. As gravações do intake **podem ser apagadas pelo Founder** (D-MC-35).
- **Redator único** ampliado: chave de API Google/AWS e parâmetro secreto em texto livre; `sem_url_nem_chave` opt-in.
- **Documento da prova** `programa-multicalculo/A-PROVA-DO-AGGER.md` e guarda G10.
- **Conserto colateral:** o relatório da 129-A escrevia a nota fora do formato da polícia do protocolo (G8 vermelho na main) → `3605da7`
  (reescrito).

## 2. As medições ao vivo (resumo; o detalhe está no documento da prova)
📊 16 cálculos de 25 (`grep -c '"m": "POST".*calcularV2' raw/*.jsonl` → 15 + 1) · AutoFleet 8,5 cálculos/dia útil · 1ª oferta 6 s,
80 % em 25–27 s, fecha em 64 s (26 de 227 nunca fecham) · comissão −5 pp = −1,5 a −7,6 % (Porto e Azul ignoram) · vidros até −27,6 %,
franquia até −18,1 % · 1 pacote por cálculo · 0 renovações da AutoFleet passam pelo Agger · plano "ilimitado".
**As regras do Founder, por máquina (captador de lista branca):** revisado 52 → conserto → 70 → consertos aplicados → 31/31 casos +
mutações + ensaios ao vivo barrados. 📊 G7: 0 negócios sumiram; 0 dos 98 negócios AUTO de pessoas mudou de versão; 3 negócios novos
(os de teste); logout das duas sessões às 19:11–19:12 (201); o aviso de sessão ativa nunca apareceu.

## 3. Julgamento
| peça | nota | o que achou |
|---|---|---|
| revisor cego da SPEC | 68 | 12 consertos (pseudônimo que o guarda acusaria; leitor fora do worker = 2º leitor; RISCO 6 → CRÍTICO) |
| revisores do captador | 52 → 70 | lista negra → lista branca; Service Worker; contador zerável; `pass` no negócio desconhecido |
| juiz | **72 REPROVA** | **B1**: chave de API de seguradora (`AIza…`) dentro de URL em `erros[]` na fixture `vivo_conta_b` (8×) + P1–P10 |
| red team | **62 QUEBREI** | o MESMO B1 (EXCLUSIVO de nenhum: os dois acharam) + leitor sem limpeza de URL, `numero()` com NaN/inf, eventos duplicados, crivo de nome estragando "Auto" |
| lente do dado | 84 | 0 divergência que mude decisão; 4 números corrigidos (comissão −1,5 a −7,6 %, 24–27 de 66, 0,05/dia, média × mediana) |
| confirmação | **88** | B1 FECHADO (36 commits com 0, G1 vermelho com URL sem esquema/codificada/chave solta); 0 blocker novo; 3 pendências → P-128-15/16/17 |

**O B1 e o histórico:** a chave entrou num commit LOCAL. 📊 `git ls-remote --heads origin spec/128-a-prova-do-agger` → vazio. O
histórico foi reescrito por plumbing (o blob trocado em 10 commits; árvore final idêntica; 📊 37 commits, 0 com `AIza…`) ANTES de
qualquer push. Lição: o elo "passou pelo gerador → é seguro" só olhava valores de campos sensíveis; segredo que **nasce** dentro de
texto livre escapava dos dois guardas.

## 4. Testes (saída real)
- `pytest test_agger_fixtures_sem_vazamento.py test_contrato_do_calculo_agger.py test_a_prova_do_agger_esta_completa.py
  test_o_protocolo_tem_policia.py -q` → 📊 **85 passed** (builder do conserto, 63,76 s).
- `agger_fixtures_saneadas.py --conferir` → r1 `0 de 990` · r2 `0 de 924` · config `0 de 232` · vivo_b `0 de 1198` · vivo_a `0 de 203`;
  idênticos ao disco. URL/chave nas fixtures: 📊 0 (eram 8/8).
- Mutações (uma vez, restauradas por cópia): G1 (CPF, `loginWs`, URL+key) · G3 (`premio > 0` → 27 ≠ 22) · G5 (regra tirada) · G10
  (sem o 📊 da E16) · captador (foto de antes, lista branca, negócio desconhecido) · 12 do conserto — **todas vermelhas**.

## 5. Bateria
📊 worktree limpo `C:/wt128` em `9db6372`, `cd backend && <venv>/python -m pytest tests -q -p no:cacheprovider` → **48 failed · 5.236
passed · 9 skipped · 31 xfailed · 1 xpassed em 5.829 s (1:37:09)**. 1ª tentativa abortada na coleta (122 erros: o `backend/.env`, ignorado
pelo git, não estava no worktree) — não conta como rodada. TRIAGEM NOMINAL contra a base (38): 35 iguais · 3 sumiram (não conferidas no
commit base: não é ganho) · **13 novas** = as MESMAS 13 de carga já triadas na 129-A (9 da SPEC-125, 3 `or_` no PostgREST real, árvore
limpa) → isoladas: 📊 `14 passed in 68.70s`; a "árvore limpa" falhou pelo arquivo de saída da própria bateria na raiz do worktree →
**0 regressões da SPEC-128**. Rodadas da bateria: 1.

## 6. Migrations
Nenhuma.

## 7. O que ficou fora (pendências P-128-*, com dono)
- P-128-01 🤖 E18: o que acontece quando o token de 3 h vence — sessões < 3 h (129-B mede sob a reserva).
- P-128-02 🧑 E7: 2 robôs da mesma conta — exige o 2º login (a reserva de 1 trabalho por login fica até lá).
- P-128-03 🤖 E12: o formato do "Imprimir" do Agger — `POST calculo/print` barrado pelo captador.
- P-128-04 🤖 E4: a busca externa de CPF falha às vezes (4 de 5) — o motor não pode depender dela.
- P-128-05 🤖 o contrato e o leitor não são chamados pelo produto — por desenho; a 129-B liga.
- P-128-06 🧑 credencial Bradesco da AutoFleet recusada em 39 cálculos ("Login ou senha incorreta").
- P-128-07 🧑 2 negócios de pessoas na Resulta "Calculando" desde 22–23/09.
- P-128-08 🤖 franquia, carro reserva e assistência (E5) não reconferidos por caminho independente (a lente não achou par puro).
- P-128-09 🤖 os scripts que geraram os números estão no rascunho da sessão (somem); o documento traz o comando e a fonte.
- P-128-10 🤖 G2 (diferencial) só roda onde há intake; na bateria roda o G1 (varredura estrutural + URL/chave).
- P-128-11 🧑 as assinaturas do Agger vencem (Resulta 13/10, limite 20/10; AutoFleet 21/10, limite 28/10) — conferir a renovação.
- P-128-12 🤖 a lista `busca/v2` não mostra cotações anteriores a 01/09 que o "CPF JÁ COTADO" mostra.
- P-128-13 🤖 a Mapfre deriva de preço entre recálculos iguais (+16 %) — o motor não usa a Mapfre para medir alavanca.
- P-128-14 🧑 decidir a D-128-03 (recálculo pelo corpo, de dentro da página) — a D-MC-28 exige o Founder.
- P-128-15/16/17 🤖 falsos positivos e 2 formas de segredo ainda não cobertas no apagador de URL/chave (confirmação) — 129-B.
- P-128-18 🧑 a chave do B1 só no reflog local; limpar com `git gc` é decisão do Founder.

## 8. Canário Amandus → Resulta → AutoFleet
Não se aplica: nada foi implantado que mude o produto (o contrato não é chamado; as fixtures são de teste). O "canário" desta SPEC
foram os próprios 16 cálculos, nas contas reais, sob o captador.

## 9. Declaração
Nenhum motor paralelo: o redator é o único (ampliado, não copiado); o contrato/leitor do Agger não existia (📊 `git grep -in -w agger
-- '*.py'` só achava comentários) e mora onde o adaptador da 129-B vai morar. Nenhuma migration, nenhuma mensagem, nenhum envio. Nada
apagado no Agger nem na InfoCap. Verba de modelo do produto: 📊 US$ 0,00 gastos (saldo US$ 4,00).

## 10. Telemetria — `python backend/scripts/medir_execucao_claude_code.py --sessao atual`
```
executor 231 min · 160 turnos · pico 482k · saída 213k · US$ 35,20 (opus-5-5)
builder F1 35 min/74 turnos/US$ 8,21 · medidor 94 min/168/US$ 21,81 · juiz 39 min/52/US$ 5,00 · red team 33/45/US$ 4,04 ·
lente 10/37/US$ 2,63 · conserto 40/56/US$ 5,95 · revisores 4 × US$ 0,24–0,99
TOTAL 10 agentes · 615 turnos · US$ 84,98 API-equivalente (tokens do Claude Code; não é a verba do produto)
achados por mecanismo: revisor cego 12 · revisores do captador 13 · prova mecânica (diferencial do gerador) 1 (nome comercial) ·
G5 ao vivo 24 respostas sem família · juiz B1 + 10 · red team B1 + 7 · lente 4 · EXCLUSIVO em blocker: nenhum (B1 dos dois)
rodadas da bateria: 1
nota do executor: 86/100 (critério: tudo medido com número e comando, nenhuma regra do Founder violada, o blocker fechado antes do push;
  menos: o B1 passou por três guardas meus e só o julgamento pegou) · juiz 72 · red team 62 · lente 84 · confirmação 88
```

## 11. Entrega
[PREENCHER: saída do push]
