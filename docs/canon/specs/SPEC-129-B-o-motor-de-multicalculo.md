# SPEC-129-B — O motor de multicálculo

> SPEC executável · 05/10/2026 · **v1.1** (revisor cego: 62 → 21 consertos aplicados, §11) · PROGRAMA MULTICÁLCULO, passo 3 (fila
> D-MC-61). Ficha: `programa-multicalculo/PLANO-MESTRE-MULTICALCULO.md` §4 (SPEC-129-B) e §5 · números:
> `programa-multicalculo/A-PROVA-DO-AGGER.md`. Rito **AAA v13**, 🔴 **CRÍTICO por piso** (§3.2: sessão/autenticação em portal de
> terceiro, ler de uma corretora e escrever noutra, migration de estrutura e de quem pode ler). Branch `spec/129-B-o-motor` · base
> `420e848`. Decisões do Founder executadas: D-128-03 ✅ · D-MC-24/26/37/41/42/47/53/56/60 · logins (PASSAGEM §8): CONSTRUIR e
> TESTAR com o login da Ellen; USO REAL só com login de robô (T-120).

## 0. POR QUE ESTA SPEC EXISTE

A 128 provou o Agger e deixou o contrato do cálculo (`backend/portal_worker/multicalculo/`) — e 📊 **nenhum chamador**
(`git grep -n "multicalculo" -- 'backend/app/*.py'` → 0, 05/10). O AutoBrokers **não sabe calcular**: a renovação (131), a cotação no
chat (132) e o Quem Cobra Menos (133-A) dependem de uma porta que peça "calcule este pedido nas corretoras X e Y, padrão e econômica"
e receba as ofertas **aos poucos**, sem saber qual login rodou.

Existe e serve (📊 lido em 05/10): cofre (`portal_worker/vault.py` e o gêmeo `app/services/portal_vault.py`, a mesma chave), lease
de conta em Redis (`portal_worker/leases.py`), travas conta × corretora (`worker.py:1203-1262`), redator (`redaction.py`), resolver
de conta (`app/services/portals/resolver.py`), leitor + lista branca por endpoint (`leitor_agger.py:127`). O que impede usar o laço
de hoje: `run_lote` faz `asyncio.gather` do lote inteiro (`worker.py:1795`) — **um cálculo de 7 min seguraria a cobrança e os vidros**
(D-MC-42: fila e navegador próprios).

## 1. O EXECUTION CARD

```
OUTCOME ..............  qualquer parte do produto chama `MulticalculoProvider.calcular(...)` e recebe, por eventos, as ofertas de
                        cada seguradora em cada corretora pedida — padrão e econômica juntas, corretoras em PARALELO, um robô por
                        corretora, isolados; recalcula com ajuste (nova versão do mesmo negócio, a partir da versão CERTA);
                        renovação a partir da ficha da InfoCap; sobrevive à morte do worker sem recalcular; nenhuma senha de
                        seguradora sai da página; o PDF da seguradora copiado para o nosso armazenamento. 📊 meta ao vivo:
                        2 corretoras × 2 opções, 1º evento ≤ 15 s, quadro ≤ 60 s, 0 `calcularV2` repetido na retomada,
                        0 senha em qualquer coluna de texto das 5 tabelas
RISCO ................  7 — ALCANCE 2 (a corretora: negócios na conta dela) · REVERSIBILIDADE 3 (nº de cálculo na seguradora,
                        "CPF cotado recentemente") · FREQUÊNCIA 2 (todo pedido de cotação dos dois produtos)
SUPERFÍCIE ...........  2 — peça nova (porta + motor + robô) sobre peças que existem
PISO APLICADO ........  §3.2 — sessão em portal de terceiro · o canal lê ofertas de N corretoras · migration de estrutura e GRANT
NÍVEL ................  🔴 CRÍTICO · gerente Opus 5.5 · builders Opus 5.5 xhigh frescos · juiz ‖ red team Opus 5.5 · confirmação se
                        houver blocker · lente do dado no canário (números do relatório por SELECT próprio)
O FIO ................  §2 · TESTE DO FIO (F4): porta → banco → motor → robô → Chromium REAL → Agger DUBLÊ (servidor local com as
                        fixtures da 128) → leitor → ofertas/eventos → `consultar`
PARALELISMO REAL .....  F1 ‖ F2 ‖ F3 com arquivos DISJUNTOS (§7) → F4 costura → gerente: canário ao vivo fora do horário da Ellen
UNIDADES .............  U1 banco · U2 porta + pedido (inclusive da InfoCap) · U3 robô Agger · U4 motor · U5 cofre de 2 chaves ·
                        U6 comandos do Founder e canário
COESÃO ...............  U1+U2 (o contrato do banco é o da porta) · U3+U5 (o robô e o cofre) · U4 contra a INTERFACE do §6.4
TIME .................  gerente · revisor cego (feito: 62) · medidor ao vivo (BLOCO 0) · builders F1 F2 F3 · costura F4 ·
                        juiz ‖ red team · confirmação (gatilho: ≥ 1 blocker)
REFERÊNCIA ...........  interna: `leases.py` (lease com dono) · `worker.py:1203-1262` · `leitor_agger.LISTA_BRANCA_POR_ENDPOINT` ·
                        o captador da 128 · `test_contrato_do_calculo_agger.py` · externa: §5 (6 URLs)
GATES ................  §9 (G1–G15), cada guarda novo com a MUTAÇÃO que o deixa vermelho
O ELO ................  "a retomada não recalcula PORQUE o checkpoint vem antes do acompanhamento": A (0 POST na retomada) pelo
                        contador do dublê · B (negócio+versão no banco antes do 1º GET) · B→A: matar o motor DEPOIS do checkpoint e
                        ANTES do fechamento, religar, contar POSTs E eventos (G6)
FAIXA DE RELÓGIO .....  💭 9–13 h · canário só FORA do horário da Ellen (≥ 19h30 ou ≤ 7h) · fatias ≤ 1h15
```

## 2. O FIO

```
① app/services/multicalculo/porta.py: MulticalculoProvider.calcular(company_id=SOLICITANTE, pedido, corretoras, opcoes, origem)
     autoriza (corretora == solicitante OU solicitante é `platform_canal` com adesão ATIVA) · resolve as coberturas de cada opção
     (preset ou explícitas) · cifra o pedido · grava 1 pedido + (corretoras × opções) cálculos `na_fila` com prioridade e prazo
② migration 20261005_01: multicalculo_pedidos · _calculos (a FILA) · _ofertas · _eventos · _adesoes · portal_accounts.robo_* · portals
③ portal_worker/main.py startup → multicalculo/motor.py: laco_do_motor()  (laço e navegador PRÓPRIOS; o poll_loop intocado)
④ motor.reservar(): grupos (pedido, corretora) `na_fila` por prioridade · robos.escolher(corretora) · LEASE DO ROBÔ NO BANCO
     (CAS em portal_accounts.robo_dono/robo_batida_em) · CAS na_fila→disparando com dono+batida
⑤ agger_sessao.Sessoes.obter(conta) → contexto com a GUARDA antes da 1ª aba; login pela TELA; aviso de sessão ativa → Cancelar
⑥ motor decifra o pedido → agger_robo.disparar(sessao, pedido, coberturas) → corpo montado DENTRO da página → POST calcularV2 →
     sessao.registrar_negocio(ref) → 🔴 CHECKPOINT negocio_ref+versao (calculando) ANTES do 1º GET · a econômica = versão do mesmo
⑦ agger_robo.acompanhar(sessao, disparo, anterior) → GET calculos/{negocio}/{versao} DENTRO da página, filtrado em JS pela lista
     branca `cotacao_calculos` → leitor_agger.ler_rodada → eventos_entre(anterior, nova) → ao_evento → upsert oferta + evento (únicos)
     · quadro_pronto aos `quadro_s` (padrão 60) ou tudo respondido · cauda até 480 s → conjunto_fechado → PDFs copiados
⑧ porta.consultar(company_id, pedido_id, desde) → eventos + ofertas, filtrados por company_id (comissão só para a dona)
⑨ porta.recalcular(company_id, calculo_id, ajuste) → cálculo `ajuste` com origem_calculo_id, MESMA corretora (D-MC-41) →
     robo.recalcular(sessao, negocio, versao_base=origem.versao, ajuste) depois de conferir D-MC-47
```

## 3. DECISÕES (vêm decididas, com nota — o Founder confirma se quiser)

| # | decisão | notas |
|---|---|---|
| D-129B-01 | **A fila é a tabela `multicalculo_calculos`**, não `portal_jobs`: o worker NO AR (código antigo) pega qualquer `portal_jobs` `queued` e o marcaria `failed: journey desconhecida` antes do Implantar; tabela nova ele não vê. O laço vive no MESMO serviço `portal-worker`, com as mesmas peças — fila própria por D-MC-42, não executor paralelo (CLAUDE.md §5) | 85 × `portal_jobs` filtrado 60 |
| D-129B-02 | **Nenhuma senha de seguradora entra no Python:** o corpo do `calcularV2` é montado por JavaScript DENTRO da página (config + pedido saneado) e TODA leitura do robô (`calculos/…`, `versoes/…`, config) é feita dentro da página e filtrada em JS pela lista branca do endpoint antes de voltar ao Python. O redator é a 2ª rede, não a 1ª | 92 × montar no Python 30 |
| D-129B-03 | **Padrão e econômica no MESMO negócio:** a padrão abre (ids nulos); a econômica sai logo como versão do mesmo negócio, sem esperar a padrão fechar (📊 E7: 2 recálculos simultâneos no mesmo negócio, versões distintas, sem colisão) | 85 × dois negócios 70 |
| D-129B-04 | **A conta de PESSOA só serve a pedido de TESTE, e só no canário:** `robo_estado='teste'` só atende `origem='teste'`; a porta só aceita `origem='teste'` com `AUTOBROKERS_CANARIO=1` no processo; conta `teste` exige `robo_janela` (CHECK); `SessaoOcupada` numa conta `teste` → `pausado` (Cancelar e PARAR, PASSAGEM §8); a sessão fecha ao sair da janela | 92 |
| D-129B-05 | **O canal é uma empresa técnica `platform_canal`** (D-MC-26), nome começando por "AutoBrokers" (o mascarador do Atlas usa a 1ª palavra de cada empresa, `templater.py:1439-1451`; "AutoBrokers" já está lá pelas 2 técnicas de hoje). Lê ofertas de outra corretora SÓ com adesão ativa E `company_kind='platform_canal'` conferido na porta, no `aderir` e no recálculo. Adesões nascem pelo comando do Founder, por id (§13.9) | 88 × "sem canal" 40 |
| D-129B-06 | **Retomada sem recalcular:** `calculando` com batida vencida no banco → outro motor RETOMA só o acompanhamento, com a rodada anterior montada das ofertas gravadas; `disparando` com batida vencida → `incerto` (nunca re-POST) | 90 |
| D-129B-07 | **Freios:** conta de robô por hora (coluna, padrão 💭 60) · corretora por hora e geral (env `MULTICALCULO_TETO_CORRETORA_HORA`, `MULTICALCULO_TETO_GERAL_HORA`) · seguradora por dia SÓ MEDIR (view, D-MC-53) · senha errada: 1 tentativa → `bloqueado` + evento · fila com `prioridade` (canal 0, auxiliar 5) e `expira_em` (canal 💭 10 min, auxiliar 💭 24 h → `expirado`); `consultar` devolve a posição na fila | 85 |
| D-129B-08 | **Os presets de cobertura são RASCUNHO** (`presets.py`, 💭, D-MC-54): padrão = RCF 200/200/20 mil, APP 5 mil, franquia reduzida, vidros completos, reserva 15 dias, assistência completa; econômica = franquia normal, vidros básicos, reserva 7 dias, assistência básica, RCF/APP intactos. A PORTA resolve as coberturas de cada opção e grava em `calculos.coberturas`; a 130-A troca os presets depois do portão de preço | 80 |
| D-129B-09 | **O motor nasce DESLIGADO:** `MULTICALCULO_MOTOR_LIGADO` (padrão falso) + `PORTAL_REAL_ENABLED` + `GLOBAL_KILL_SWITCH` a cada volta. Sem conta de robô, ligado não faz nada | 95 |
| D-129B-10 | **A lease do ROBÔ mora no BANCO**, não no Redis: CAS em `portal_accounts.robo_dono/robo_batida_em` (batida a cada 20 s, vence em 💭 90 s) e, por cálculo, `multicalculo_calculos.dono/batida_em`. 📊 Sem Redis, `LeaseDePortal.adquirir` devolve `True` (`leases.py:415-419`) — inaceitável para um login de sessão única. A P-198 (Redis real) CONTINUA para o `portal_jobs`; o motor não depende dela. Mudança de desenho registrada em CHANGE-ADDENDA (ESSENCIAL) | banco 85 × Redis obrigatório 65 (sem canário local, sem prova da P-198) |
| D-129B-11 | **`portals.agger` nasce `is_active=false`** e a rota `POST /credentials` recusa `agger`: a tela de credenciais (`api/portal.py:170-185`) faria upsert por (empresa, portal, rótulo) e trocaria o login do robô pelo de uma pessoa. Gatilho no banco: `username`/`secret_encrypted` mudou numa conta de robô → `robo_estado='pausado'` | 90 |

## 4. BLOCO 0 — premissas que mudariam o desenho (gerente, 05/10, com o comando)

| # | premissa | medida | muda o quê |
|---|---|---|---|
| P1 | não existe conta do Agger | 📊 `select portal_key,count(*) from portal_accounts group by 1` → 8 portais × 2, nenhum `agger` | a migration cria `portals.agger` e as colunas robo_* |
| P2 | não existe empresa do canal | 📊 `select company_name,company_kind,is_technical from companies` → 2 técnicas; CHECK `companies_company_kind_check` = client · platform_knowledge · platform_blueprint_studio | drop + add do CHECK na mesma transação; o ROLLBACK traz o texto de `pg_get_constraintdef` |
| P3 | tabelas do portal sem policy | 📊 `pg_policies` 0 em portal_accounts/jobs, RLS ligada | tabelas novas: RLS ligada, sem policy, REVOKE de anon/authenticated, filtro no código, teste com 2 tenants |
| P4 | FK composta conta × corretora existe | 📊 `fk_portal_jobs_account_same_company (account_id, company_id)` · `uq_portal_accounts_id_company` | `multicalculo_calculos` usa a mesma |
| P5 | o laço de hoje junta o lote | 📊 `worker.py:1795` `await asyncio.gather(...)` | D-129B-01 |
| P6 | o leitor lê `calculos/{negocio}/{versao}` | 📊 fixture `vivo_conta_b.json` `rodadas[].corpo` = lista por seguradora | ⑦ |
| P7 | as leituras trazem senhas | 📊 a 128: 17/17 senhas no corpo, 28/28 nas consultas; `leitor_agger.py:21-23` | D-129B-02 |
| P8 | `redaction.tem_vazamento` não pega `loginWs`/URL | 📊 revisor: `tem_vazamento({'loginWs':'X'})` → `[]` | a saída usa a lista branca + `CHAVES_PROIBIDAS_NA_OFERTA` + `tem_url_ou_chave` |
| P9 | sem Redis, a lease libera tudo | 📊 `leases.py:415-419, 441-442, 480-486`; sem Redis local (`which redis-server` → nada) | D-129B-10 |
| P10 | `companies` tem iteradores pelo produto | 📊 `git grep -ln 'table("companies")' -- app` → 27 arquivos | F1 prova que a empresa técnica nova não dispara rotina, modelo pago, mensagem nem cobrança (as 2 técnicas de hoje são a linha de controle) |
| P11 | **montar o corpo sem a tela funciona** | ⏳ medidor M1 — §4.1 | se NÃO: o 1º disparo preenche a tela (fallback); o recálculo segue pelo corpo |
| P12 | **a hipótese do CPF em 2 corretoras** | ⏳ medidor M2 — §4.1 | informa o portão da 133-B |

### 4.1 O que o medidor ao vivo mediu
_(o gerente preenche ao voltar o laudo: M0 config × corpo, GETs de placa/CPF, marcador do negócio, usuário por versão; M1; M2; M3)_

## 5. O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS

| URL | o que faz | o que MODELAMOS | o que REJEITAMOS e por quê | COMO O JUIZ INSPECIONA |
|---|---|---|---|---|
| https://kubernetes.io/docs/concepts/architecture/leases/ | lease com dono + duração + renovação | a lease do robô e do cálculo: dono + batida + vencimento, no banco | lock anônimo; lease que "concede tudo" quando o armazenamento cai | G4/G6: dois motores, um dono; dono morto → retomada |
| https://www.postgresql.org/docs/current/sql-select.html#SQL-FOR-UPDATE-SHARE | fila em tabela | a fila em tabela com claim por CAS (`update … where status='na_fila'`), como `_tentar_claim` | `SKIP LOCKED` exige SQL direto; o worker fala PostgREST | G4 |
| https://cryptography.io/en/latest/fernet/#cryptography.fernet.MultiFernet | cifra com a 1ª chave, decifra com qualquer | os DOIS cofres (worker e smith-api) com `PORTAL_VAULT_KEY` + `PORTAL_VAULT_KEY_ANTERIOR` (P-182) | recifrar tudo na troca | G9 |
| https://playwright.dev/python/docs/network#modify-requests | `route` intercepta e aborta | a GUARDA de escrita (lista branca) antes da 1ª aba, como o captador da 128 | lista negra (o revisor da 128 deu 52) | G3 |
| https://docs.stripe.com/api/idempotent_requests | idempotência no efeito externo | checkpoint ANTES de acompanhar; disparo incerto nunca se repete sozinho | retry automático do POST | G6 |
| https://docs.temporal.io/workflows#deterministic-constraints | retomar do último ponto gravado | a retomada refaz só LEITURA, a partir do estado gravado | reexecutar o passo que teve efeito | G6 |

## 6. AS UNIDADES

### U1 · O banco — `20261005_01_spec129b_motor.sql` (F1)
Formato do MIGRATIONS-AUTHORITY §7 (APPLY/VERIFY/ROLLBACK ANTES; idempotente; expand-first; não destrutiva).
- `companies_company_kind_check` passa a admitir `platform_canal` (drop + add na mesma transação, a regra `kind_e_tecnica` intocada);
  insere `'AutoBrokers Canal de Cotação'`, `is_technical=true`, `status='active'` com `insert … where not exists (select 1 from
  companies where company_kind='platform_canal')`. ROLLBACK: o texto exato de `pg_get_constraintdef` de HOJE; recusa se houver dado.
- `portals`: `agger`, `category='multicalculo'`, `cred_kind='login_password'`, **`is_active=false`** (D-129B-11).
- `portal_accounts` + `robo_estado text null` (CHECK ativo · pausado · bloqueado · ocupada · teste) · `robo_teto_por_hora int null`
  (1–600) · `robo_janela jsonb null` (CHECK: `robo_estado='teste'` ⇒ janela não nula) · `robo_ocupada_ate` · `robo_dono text` ·
  `robo_batida_em timestamptz`. Nulo = conta que não é de robô (as 16 de hoje). Gatilho BEFORE UPDATE: `username` ou
  `secret_encrypted` mudou e `robo_estado is not null` → `robo_estado='pausado'`.
- `multicalculo_adesoes(id, canal_company_id, corretora_company_id → companies, ativa, criada_em, desativada_em,
  unique(canal, corretora), CHECK canal ≠ corretora)`.
- `multicalculo_pedidos(id, company_id [SOLICITANTE] → companies, origem CHECK (auxiliar · canal · teste), ramo, opcoes text[],
  corretoras uuid[], pedido_cifrado NOT NULL, cpf_hmac, quadro_s int default 60, status (aberto · fechado · cancelado), criado_em,
  atualizado_em, unique(id, company_id))`.
- `multicalculo_calculos` (a FILA): `id, pedido_id, solicitante_company_id` com FK composta `(pedido_id, solicitante_company_id) →
  pedidos(id, company_id)` CASCADE · `company_id` [corretora de registro] · `opcao` (padrao · economica · ajuste) · `coberturas
  jsonb NOT NULL` · `status` CHECK (na_fila · disparando · calculando · fechado · falhou · incerto · cancelado · expirado) ·
  `account_id` + FK `(account_id, company_id) → portal_accounts(id, company_id)` · `negocio_ref`, `versao`, `origem_calculo_id`,
  `ajuste jsonb`, `prioridade int`, `expira_em`, `disponivel_em`, `tentativas`, `dono`, `batida_em`, `disparado_em`,
  `primeira_oferta_em`, `quadro_pronto_em`, `fechado_em`, `erro`, `criado_em` · `unique(id, pedido_id, company_id,
  solicitante_company_id)` · CHECK `calculando`/`fechado` ⇒ `negocio_ref` e `versao` · índice da fila `(prioridade, disponivel_em)
  where status='na_fila'`.
- `multicalculo_ofertas(…, calculo_id, pedido_id, company_id, solicitante_company_id)` com FK COMPOSTA para as 4 colunas de
  `calculos` · `seguradora, seguradora_codigo, pacote, tipo_de_pacote, premio_total NOT NULL CHECK > 0, premio_mensal,
  franquia_valor, franquia_tipo, coberturas jsonb, parcelamentos jsonb, tem_pdf, pdf_path, alertas text[], comissao_percentual
  [INTERNO], recebida_em, atualizada_em` · `unique(calculo_id, seguradora_codigo, pacote, tipo_de_pacote)`.
- `multicalculo_eventos(id identity, calculo_id, pedido_id, company_id, solicitante_company_id)` com a MESMA FK composta · `tipo,
  seguradora, seguradora_codigo, pacote, tipo_de_pacote, familia, oferta_id, chave text NOT NULL, t_s, criado_em` ·
  `unique(calculo_id, chave)` (chave = tipo + seguradora + pacote + tipo_de_pacote + prêmio em centavos, ou `conjunto_fechado`) ·
  índice `(pedido_id, id)`.
- view `multicalculo_seguradora_dia` `with (security_invoker=on)` (dia, corretora, seguradora, cálculos, ofertas, recusas por família).
- Nas 5 tabelas e na view: RLS ligada, sem policy, `revoke all … from anon, authenticated` (a lição de `20260727_03`).

### U2 · A porta — `backend/app/services/multicalculo/` (F1)
`porta.py: class MulticalculoProvider` (molde `backend/app/providers/policy_data_provider.py:1904`: `company_id` keyword-only, 1º):
- `calcular(*, company_id, pedido, corretoras=None, opcoes=("padrao","economica"), coberturas=None, origem, quadro_s=60)` —
  `corretoras=None` → só a própria. Cada corretora: `== company_id` OU (`company_id` é `platform_canal` E adesão ativa); qualquer
  outra → `NaoAutorizado` ANTES de gravar linha. `origem='teste'` só com `AUTOBROKERS_CANARIO=1` (D-129B-04). `origem='canal'` com
  perfil ausente (garagem, uso, km, jovem) → `PerfilIncompleto` (D-MC-59: no canal se PERGUNTA); `auxiliar` → marcado `assumido`
  (D-128-07). Os 16 obrigatórios da E3 (`contrato.CAMPOS_DO_PEDIDO_AUTO`) → `PedidoIncompleto(campos)`. Resolve as coberturas por
  opção (preset ou explícitas) e grava em cada cálculo. Cifra com `app/services/portal_vault.py` (mesma chave do worker).
  `cpf_hmac` = HMAC-SHA256 com `MULTICALCULO_HMAC_KEY` (nunca o hash sem sal de `journeys/__init__.py:352-369`).
- `consultar(*, company_id, pedido_id, desde_evento=0) -> Andamento` — só pedido DESTE `company_id`; eventos > desde, ofertas
  (menor preço primeiro), estado por corretora × opção, posição na fila. `comissao_percentual` só quando `company_id` == corretora
  da oferta (o canal recebe `None`).
- `recalcular(*, company_id, calculo_id, ajuste)` — o cálculo é de pedido deste `company_id`; reconfere a adesão se for o canal;
  cria `opcao='ajuste'`, `origem_calculo_id`, MESMA corretora (D-MC-41), coberturas = as da origem + o ajuste.
- `capacidades(ramo)` · `cancelar(*, company_id, pedido_id)`.
- `pedido.py`: `PedidoDeCalculo` (saneado) + `de_apolice(apolice: policy_data_provider.Apolice, perfil)` — a RENOVAÇÃO a partir da
  ficha da InfoCap (📊 E2: traz veículo, placa, chassi, anos, FIPE, bônus, nascimento, sexo, CEP; faltam estado civil, condutor,
  questionário, CEP de pernoite, RCF/APP → `assumido` ou perguntado conforme a origem).

### U3 · O robô do Agger — `backend/portal_worker/multicalculo/` (F2)
- `agger_guarda.py` — `decidir(metodo, url, corpo, ctx)` PURA + `instalar(contexto, ctx)`: leitura em `*.aggilizador.com.br` passa;
  escrita SÓ: `POST usuario/login` (1 por contexto; corpo sem `derrub|forç|prosseg|encerr|nova sess`) · `POST usuario/login/pdocs`
  (≤ 6 por HORA) · `POST usuario/deslogaSessao` · `POST calculo/calcularV2` (ids nulos = negócio novo; ids preenchidos só se o
  negócio está em `ctx.negocios_do_robo`). Tudo o mais abortado e contado; WebSocket fechado; `service_workers="block"`.
- `agger_sessao.py` — `Sessoes`/`Sessao` (§6.4): contexto por conta reaproveitado (login 📊 5–52 s, E1); guarda antes da 1ª aba;
  login pela tela; aviso de sessão ativa → **Cancelar** → `SessaoOcupada`; senha recusada → `CredencialRecusada` (1 tentativa);
  token capturado do header de `pdocs`, renovado navegando quando faltar < 20 min das 3 h (E18); `registrar_negocio(ref)`;
  `fechar()` = logout. A senha decifrada só existe dentro de `obter()`.
- `agger_robo.py` — `disparar`, `acompanhar`, `recalcular(…, versao_base)`, `pessoa_mexeu_recentemente`, `copiar_pdfs` (§6.4).
  TODA leitura e montagem dentro da página; o que volta ao Python já passou pela lista branca do endpoint em JS, e de novo em Python
  (`Oferta` + `CHAVES_PROIBIDAS_NA_OFERTA` + `redaction.tem_url_ou_chave`) — achou algo proibido → descarta e emite `erro_de_leitura`.
  PDF: baixado DENTRO da página (a URL nunca sai) e devolvido em bytes.
- `presets.py` — os presets 💭 com o porquê ao lado de cada constante (CLAUDE.md §9.5).

### U4 · O motor — `backend/portal_worker/multicalculo/{motor,robos}.py` + `main.py` (F3)
- `laco_do_motor()` — task própria no startup, NAVEGADOR PRÓPRIO; D-129B-09; kill switch a cada volta; nunca derruba o processo.
- `robos.escolher(supa, corretora_id, origem)` — `portal_accounts` `portal_key='agger'`, `.eq("company_id", corretora)`, estado
  (`teste` só com `origem='teste'`), janela, teto/hora, `robo_ocupada_ate` vencido, CAS da lease do robô no banco (D-129B-10). Não
  usa `resolver_conta`: ele recusa quando há > 1 conta (`resolver.py`, "ambígua"), e > 1 robô é exatamente o rodízio.
- `reservar()` → grupos (pedido, corretora) por prioridade; `expira_em` vencido → `expirado`; freios; CAS de TODOS os cálculos do
  grupo `na_fila→disparando` (dono + batida).
- `executar_grupo` — decifra o pedido (`portal_worker.vault`); carrega `negocios_do_robo` da corretora do banco; dispara a padrão →
  checkpoint → dispara a econômica no mesmo negócio → checkpoint → acompanha as duas em paralelo; cada evento → upsert oferta +
  insert evento (chave única: repetido = no-op); fechou → copia PDFs (`multicalculo/{company}/{calculo}/{oferta}.pdf` pelo
  `_upload_portal_blob` que já existe) → `fechado`. Batida a cada 20 s no cálculo e no robô; perdeu a posse → para de gravar.
  Grupos de corretoras diferentes EM PARALELO; a mesma conta, um grupo por vez (P-128-02).
- Retomada (D-129B-06) a cada volta. Sessão fora da janela da conta → `fechar()`.
- Exceções → estado: `SessaoOcupada` → `ativo` vira `ocupada` (💭 30 min, cálculos voltam à fila); `teste` vira `pausado` e os
  cálculos `falhou` · `CredencialRecusada` → `bloqueado` + evento `robo_bloqueado` · `DisparoIncerto` → `incerto` ·
  `DisparoRecusado` → `falhou` com o motivo. Nenhuma mensagem sai nesta SPEC.

### U5 · O cofre de 2 chaves (F2: `portal_worker/vault.py` · F1: `app/services/portal_vault.py`)
`MultiFernet([PORTAL_VAULT_KEY, PORTAL_VAULT_KEY_ANTERIOR?])` nos DOIS cofres (P-182). Sem a anterior, idêntico a hoje.

### U6 · Os comandos do Founder e o canário (F4 escreve; o gerente roda ao vivo)
- `backend/scripts/multicalculo_robo.py` — `cadastrar --corretora <uuid> --rotulo <texto> --usuario <email> [--estado ativo|teste]
  [--teto N] [--janela seg-sex,07:00-20:00]` (senha por `getpass` ou `MULTICALCULO_SENHA`, cifrada; nunca em argumento) · `pausar` ·
  `listar` (sem senha) · `aderir --canal <uuid> --corretora <uuid>` (recusa se o canal não for `platform_canal`) · `apagar-senha`.
  É o comando da T-120. Provado DENTRO do contêiner do worker (protocolo §5②, ambiente de uso).
- `backend/scripts/multicalculo_canario.py` — exige `AUTOBROKERS_CANARIO=1`: pedido `teste` pelo canal para 2 corretoras × 2 opções,
  motor no processo (navegador local), eventos impressos sem dado pessoal, recálculo com ajuste a partir da padrão, morte/retomada,
  renovação de uma ficha InfoCap (só se a apólice autorizada existir na InfoCap; senão declarado), isolamento por SELECT, varredura
  de senha em TODAS as colunas de texto. Ao fim: contas `teste` → `pausado`, senha apagada, logout.

### 6.4 A INTERFACE entre F2 e F3 (as duas fatias codificam contra ela)
```python
# portal_worker/multicalculo/agger_sessao.py
class SessaoOcupada(Exception): ...        # o aviso de sessão ativa apareceu e foi CANCELADO
class CredencialRecusada(Exception): ...   # login/senha recusados (1 tentativa)
class Sessoes:
    def __init__(self, navegador, *, url_base: str = "https://aggilizador.com.br"): ...
    async def obter(self, conta: dict, *, senha: str, negocios_do_robo: set[str]) -> "Sessao": ...
    async def fechar(self, conta_id: str) -> None: ...      # logout + fecha o contexto
    async def fechar_todas(self) -> None: ...
class Sessao:
    conta_id: str
    def registrar_negocio(self, negocio_ref: str) -> None: ...   # a guarda passa a aceitar este negócio
    def contagem_de_escritas(self) -> dict: ...                   # {"calcularV2": n, "barradas": m} — G3/G6
# portal_worker/multicalculo/agger_robo.py
class DisparoIncerto(Exception): ...       # o POST PODE ter saído (timeout, rede): nunca repetir
class DisparoRecusado(Exception): ...      # nada saiu, ou o servidor recusou com resposta clara
@dataclass(frozen=True)
class Disparo: negocio_ref: str; versao: int; t0: float
async def disparar(sessao, pedido: dict, coberturas: dict, *, negocio_ref: str | None = None) -> Disparo: ...
     # registra o negócio na sessão antes de devolver
async def acompanhar(sessao, disparo: Disparo, *, ao_evento, anterior: RodadaDoCalculo | None = None,
                     quadro_s: float = 60, teto_s: float = 480, intervalo_s: float = 3,
                     ao_quadro=None) -> RodadaDoCalculo: ...
     # ao_evento(evento: Evento) -> awaitable · ao_quadro() -> awaitable, uma vez
async def recalcular(sessao, negocio_ref: str, *, versao_base: int, ajuste: Ajuste) -> Disparo: ...
async def pessoa_mexeu_recentemente(sessao, negocio_ref: str, *, horas: int = 24,
                                    versoes_do_robo: set[int]) -> bool: ...
async def copiar_pdfs(sessao, disparo: Disparo) -> dict[tuple, bytes]: ...   # (seguradora_codigo, pacote, tipo) -> bytes
```
`pedido` = dict DECIFRADO pelo MOTOR (`PedidoDeCalculo.para_dict()`), só em memória. `coberturas` = `calculos.coberturas`.

## 7. AS FATIAS (arquivos DISJUNTOS — um dono por arquivo)

| fatia | arquivos (DONO ÚNICO) | entra | sai quando |
|---|---|---|---|
| **F1** banco + porta | `backend/supabase/migrations/20261005_01_spec129b_motor.sql` · `backend/app/services/multicalculo/{__init__,porta,repositorio,pedido}.py` · `backend/app/services/portal_vault.py` · `backend/app/api/portal.py` (só a recusa de `agger`) · `backend/tests/test_spec129b_a_porta.py` · `backend/tests/test_spec129b_o_banco.py` | já | VERIFY no banco real em transação desfeita; G1 G2 G7 G13(porta) verdes; P10 provado |
| **F2** robô + cofre do worker | `backend/portal_worker/multicalculo/{agger_guarda,agger_sessao,agger_robo,presets}.py` · `backend/portal_worker/vault.py` · `backend/tests/test_spec129b_o_robo.py` · `backend/tests/dubles/agger_dublê.py` | o laudo do medidor (§4.1) | contra o Agger DUBLÊ num Chromium real; G3 G5 G9 verdes |
| **F3** motor | `backend/portal_worker/multicalculo/{motor,robos}.py` · `backend/portal_worker/main.py` · `backend/tests/test_spec129b_o_motor.py` | já (dublê do robô pela §6.4) | G4 G6 G8 G10 G14 verdes |
| **F4** costura | `backend/tests/test_spec129b_o_fio.py` · `backend/scripts/{multicalculo_robo,multicalculo_canario}.py` · `backend/supabase/migrations/MANIFEST.md` | F1+F2+F3 | TESTE DO FIO verde com o motor e o robô REAIS; G11 G13 |
| **gerente** | APPLY da migration · canário · docs · relatório | F4 + fora do horário da Ellen | G12 G15 |

## 8. O QUE NÃO ENTRA
Comparar, recomendar, proposta, página (130-A) · ler apólice por foto (130-B) · ciclo de renovação (131) · conversa (132/133) · as
REGRAS de negócio entre corretoras — empate, rodízio comercial, quantas por pedido (133-B; aqui só a mecânica do paralelo e a
autorização por adesão) · residencial (E13) · rodízio AO VIVO entre 2 robôs da mesma corretora (não existe o 2º login, P-128-02; o
rodízio é provado em teste automático, G14) · mudar a reserva para 2 cálculos por login · qualquer mensagem · custo de modelo:
o motor não chama modelo (📊 meta zero; o relatório mede `grep` de cliente de LLM nos arquivos novos → 0).

## 9. GATES (cada guarda novo com a MUTAÇÃO que o deixa vermelho)

| # | o quê | como | mutação |
|---|---|---|---|
| G1 | isolamento, DOIS tenants | A não lê pedido/oferta de B; canal sem adesão → `NaoAutorizado` sem linha; corretora `client` com "adesão" forjada → recusada; canal com adesão lê as duas | tirar o `.eq("company_id")` do `consultar` → vermelho; tirar o `company_kind` → vermelho |
| G2 | comissão interna | canal recebe `None`; a dona, o valor | devolver sempre → vermelho |
| G3 | a guarda | escrita fora da lista abortada; calcularV2 com negócio que não é do robô abortado; econômica depois de `registrar_negocio` passa; 2º login abortado; 7º pdocs na hora abortado | "calcularV2 passa sempre" → vermelho |
| G4 | um cálculo, um dono | dois motores, um cálculo `na_fila` → 1 claim; dois motores, um robô → 1 lease | tirar o filtro de status do CAS → vermelho |
| G5 | nenhuma senha sai da página | o Agger dublê devolve `loginWs/senhaWs/senha/token/URL de PDF` no config, versões e resultados: 0 no retorno de TODO `page.evaluate` (espia), 0 no banco dublê, 0 nos eventos, 0 no `caplog` | devolver a resposta crua do GET → vermelho |
| G6 | retomada sem recalcular | matar depois do checkpoint; religar: contador de `calcularV2` igual, eventos SEM duplicar, cálculo fecha | checkpoint depois do acompanhamento → vermelho; `anterior=None` → eventos duplicam → vermelho |
| G7 | o banco | VERIFY em transação desfeita: CHECKs, FK composta (conta de outra corretora → recusada; oferta com corretora trocada → recusada), unique do evento, gatilho que pausa o robô, REVOKE | — (o VERIFY tem controle) |
| G8 | convivência | com o motor ocupado 30 s, `run_lote` roda um job dublê e volta em < 2 s | rodar o grupo dentro do `run_lote` → vermelho |
| G9 | cofre de 2 chaves (os dois) | cifrado com a anterior decifra; cifra nova sai na atual | — |
| G10 | estados da conta | teto/hora, janela, `teste` só com `origem='teste'`, `teste`+ocupada → `pausado`, `bloqueado` não retenta, `expira_em` → `expirado`, origem `teste` sem `AUTOBROKERS_CANARIO` → recusada | aceitar `teste` em `auxiliar` → vermelho |
| G11 | O TESTE DO FIO | porta.calcular → banco dublê → motor REAL → robô REAL → Chromium REAL → Agger DUBLÊ → leitor → `consultar` com as ofertas da fixture (contagem igual à do leitor puro), padrão e econômica, 2 corretoras | leitor → lista vazia → vermelho |
| G12 | ao vivo (gerente) | 2 corretoras × 2 opções pelo canal; recálculo da PADRÃO com ajuste; morte/retomada; isolamento por SELECT; 0 senha em TODA coluna de texto das 5 tabelas (incl. `erro`, `alertas`); lease sem Redis | — |
| G13 | renovação | `de_apolice` sobre a fixture InfoCap (`tests/fixtures/infocap_contract_shapes/`) → pedido com `renovacao=true`, campos `assumido` marcados; no dublê vira cálculo; ao vivo se houver apólice autorizada na InfoCap | ignorar o bônus → vermelho |
| G14 | rodízio | 2 robôs da mesma corretora, 2 pedidos → os dois usados em paralelo; um `ocupada` → o outro | sempre o 1º → vermelho |
| G15 | o comando do Founder | `multicalculo_robo.py cadastrar/listar/pausar` rodado no contêiner do worker (ou a imagem local) | — |

## 10. ATAQUES QUE O JUIZ E O RED TEAM RECEBEM
dado vazio/nulo no pedido · company_id cruzado na porta, no motor, nas FKs compostas, no `aderir` · o mesmo evento 2× · dois motores
no mesmo cálculo e no mesmo robô · worker morto em cada estado · Redis fora · a guarda deixa passar escrita? (DELETE, `excluir`,
telemetria, 2ª aba, websocket, 2º login) · a senha sai por algum caminho (exceção com corpo, `repr`, evento, evidência, log, retorno
de `evaluate`) · o motor prende o laço do portal? · a conta `teste` (pessoa) atende pedido real? · a tela de credenciais troca o
robô? · o canal lê corretora sem adesão? · a empresa técnica nova dispara rotina/modelo/mensagem? · rollback da migration · o
produto CHAMA este caminho? (nesta SPEC só o canário e os testes: declarado, P-129B-02 — o 1º chamador é a 130-A/131/133-A).

## 11. O QUE O REVISOR CEGO ACHOU (62/100) E O QUE MUDOU
Todos os 21 itens aplicados: 1 saída por lista branca (P8) · 2 leituras dentro da página (D-129B-02, G5) · 3 lease no banco
(D-129B-10) · 4 `anterior` + chave única de evento · 5 `versao_base` · 6 `registrar_negocio` · 7 nome do canal + P10 · 8
`security_invoker` + REVOKE · 9 `is_active=false` + gatilho (D-129B-11) · 10 D-129B-04 reforçada · 11 `company_kind` conferido · 12 FKs
compostas · 13 `where not exists` + ROLLBACK do texto real · 14 renovação (G13), rodízio (G14), PDF DENTRO do escopo (U3/U4), P-198
CONTINUA com o porquê (D-129B-10, CHANGE-ADDENDA) · 15 interface fixada · 16 `quadro_s` 60 · 17 prioridade + `expira_em` · 18 canal
pergunta o perfil · 19 pdocs por hora · 20 G12 varre tudo; o G11 usa banco dublê (declarado: CHECK/FK/unique vêm do G7 e do canário)
· 21 referências corrigidas; os 2 cofres; custo de modelo = 0 medido. Os arquivos soltos na raiz (`app/`, `portal_worker/`,
`tests/`) são anteriores a esta sessão e não são tocados (CLAUDE.md §13.5).
