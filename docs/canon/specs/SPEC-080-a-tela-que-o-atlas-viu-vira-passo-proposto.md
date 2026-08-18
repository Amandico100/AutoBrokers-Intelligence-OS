---
status: "PRONTA PARA EXECUÇÃO — escrita em 18/08/2026"
spec: "SPEC-080"
titulo: "A tela que o Atlas já viu vira passo PROPOSTO — e só o Founder a liga"
criada_em: "2026-08-18"
branch_sugerida: "feat/spec080-a-tela-que-o-atlas-viu-vira-passo-proposto"
repo: "Amandico100/AutoBrokers-Intelligence-OS"
baseline_observada: "0b676f200bdf91742bef96be3e2b1775a559c32d (feat/spec078-cobranca-funciona-e-entrega-aparece)"
supabase_producao: "dcajcvlzcjbmyapmklil"
depende_de: "SPEC-034 Onda 2 (Simulador) e Onda 4 (Alfaiate/overlays) · SPEC-038 (Atlas, Sentinela, route_drift) · SPEC-050 (o gate roda ANTES da escrita) · SPEC-061 (Portal Admin, Caixa de Entrada, RBAC) · SPEC-063 (higiene do mapa)"
deploy_esperado: "smith-api (backend) + smith-web (tela de aprovação). Nenhuma mudança em portal-worker."
migration_esperada: "1 — ALTER expand-first em playbook_overlays. Nunca CREATE: a tabela existe em produção sem arquivo (versão 20260714001905)."
custo_de_api_esperado: "ZERO. Nenhuma peça desta SPEC chama LLM."
---

# SPEC-080 — A tela que o Atlas já viu vira passo PROPOSTO, e só o Founder a liga

> **Resultado desta SPEC, em uma frase:** quando a URA de uma seguradora mostra
> uma tela de menu que o corredor não sabe responder, o sistema **propõe** o
> passo que falta — com a tela, a resposta sugerida, a prova de quantas vezes
> aquilo já aconteceu e o veredito do Simulador — e o Founder aprova ou recusa
> em dois cliques. **Nada entra no playbook sozinho. Nunca.**
>
> **Regra de ouro:** esta SPEC não cria motor novo. O Alfaiate existe, o
> Simulador existe, a tabela de overlay existe, a tela do Atlas existe e a
> Caixa de Entrada existe. Todos estão **desligados, desalinhados ou mudos**.
> Esta SPEC os alinha e coloca um humano no meio.

---

# 0. Por que esta SPEC existe agora

## 0.1 A tela que parou um acionamento real

Em **18/08/2026, 01:51:33**, num acionamento de eletricista residencial da
Allianz, a URA mandou isto:

```text
*Importante:* Esse serviço de eletricista está disponível apenas para reparos
elétricos na residência

*1 -* Preciso de reparo elétrico para residência
*2 -* Preciso de reparos elétricos em aparelhos ou eletrodomésticos.
```

📊 Medido em 18/08/2026 (`observed_events`, projeto `dcajcvlzcjbmyapmklil`):

```sql
select count(*) as vezes, min(created_at) as primeira, max(created_at) as ultima,
       count(distinct session_id) as sessoes, count(distinct company_id) as corretoras
  from observed_events
 where insurer_key='allianz'
   and text ilike '%servi%o de eletricista est%dispon%vel apenas para reparos el%tricos%';
```

```text
vezes  primeira                    ultima                      sessoes  corretoras
   8   2026-07-28 14:04:06+00      2026-08-18 01:59:07+00            4           1
```

**O Atlas já tinha visto essa tela oito vezes, ao longo de 21 dias.** O mapa
ativo da Allianz contém o texto — 📊 `ura_maps.id = b4f74d51-2d89-42ad-931a-b2d77e15bbce`,
`status='active'`, e `map::text ilike '%eletricista%'` → `true`.

**O corredor não sabia.** E não sabia porque **a ponte entre "o Atlas sabe" e
"o corredor sabe" não existe para telas novas de menu.**

## 0.2 O que NÃO se deve concluir daquele incidente

> ⚠️ **Correção de leitura, obrigatória antes de qualquer bloco.**

Seria cômodo escrever "o corredor travou 248 segundos porque a ponte não
existe". **Isso é falso**, e o commit `8aa15be` de 17/08/2026 já mediu a
verdade: foram **quatro defeitos em série**, e a tela ausente era só o
primeiro.

```text
01:51:33  Allianz manda a tela
01:51:42  nenhum passo casa  → vai para o cérebro          ← DEFEITO 1 (esta SPEC)
01:51:52  o cérebro RESPONDEU certo; o guarda reprovou por
          `too_long`; o log prometeu retentativa e nada
          foi rechamado                                    ← DEFEITO 2 (corrigido)
01:52:21  o Sentinela respondeu "1" — CERTO — e o envio
          caiu em integration=None, exceção engolida       ← DEFEITO 3 (corrigido)
01:55:41  "encerrado por inatividade"                      ← DEFEITO 4 (corrigido)
```

**Os defeitos 2, 3 e 4 já estão consertados** (`8aa15be`). Esta SPEC executa
**apenas o defeito 1**, e o executa na forma geral: não a tela do eletricista,
mas a **classe** de telas que o Atlas viu e o corredor ignora.

📊 E a tela do eletricista **já foi consertada à mão** — `corridor_playbooks.py`
ganhou três passos (`tipo_de_reparo_eletrico`, `o_que_aconteceu`,
`descricao_detalhada`) no mesmo commit. **Esta SPEC não a conserta de novo.**
Ela transforma o conserto manual num procedimento governado, para as próximas.

## 0.3 O tamanho real do problema

📊 Medido em 18/08/2026 — telas de menu distintas já observadas, por seguradora
(impressão digital = `md5` do texto com espaços normalizados; heurística de
menu = linha começando por dígito seguido de `-`, com 2+ hifens no texto):

```sql
with menus as (
  select insurer_key, md5(regexp_replace(text,'\s+',' ','g')) as fp, count(*) as vezes
    from observed_events
   where direction='in' and text is not null
     and text ~ '(^|\n)\s*\*?\s*[0-9]{1,2}\s*\*?\s*-'
     and (length(text) - length(replace(text, '-', ''))) >= 2
   group by 1,2
)
select insurer_key, count(*) as telas_menu_distintas, sum(vezes) as avistamentos
  from menus group by 1 order by 2 desc;
```

```text
allianz   301 telas   1981 avistamentos
porto      50 telas    156
alfa       28 telas     67
zurich     24 telas     37
azul       22 telas     39
yelum       8 telas     53
bradesco    3 telas     12
hdi         3 telas     14
mapfre      1 tela       1
```

> ⚠️ **Este número é uma cota superior grosseira, não uma fila de trabalho.**
> A impressão digital é o texto inteiro: duas redações da mesma pergunta contam
> como duas telas, e uma tela com o nome do profissional embutido conta uma vez
> por profissional. **Não se pode citar "440 telas faltando".** O que ele prova
> é só isto, e basta: **a fila é grande demais para um humano varrer à mão, e
> grande demais para despejar na mesa do Founder sem teto.**

## 0.4 A causa estrutural — quatro curtos-circuitos, cada um fatal sozinho

📊 Todos verificados no código em 18/08/2026, commit `0b676f2`.

### C1 · A tela nova de menu nunca chega ao Alfaiate

`route_sentinel.classify_severity` (`backend/app/services/atlas/route_sentinel.py:120`)
devolve **só** `"structural"` ou `"cosmetic"`. Tela nova cujo nó tem
`kind in ("menu","pergunta","app_form")` → `"structural"` (linha 132-133).

E o Alfaiate só é chamado no ramo `cosmetic`
(`route_sentinel.py:201-204`). Estrutural vai para alerta ao Founder.

📊 A consequência, medida:

```sql
select severity, status, count(*) from route_drift group by 1,2;
```

```text
structural   escalated   4
```

**Quatro drifts registrados. Quatro estruturais. Zero cosméticos.**
O ramo que chama o Alfaiate **nunca foi executado uma única vez.**

### C2 · A âncora que o Alfaiate gera não casa com nada

`playbook_tailor.anchor_from_text` (`playbook_tailor.py:58-62`) devolve
`re.escape(texto[:60])` — do texto **cru**.

Mas `match_ura_step` (`corridor_playbooks.py:2578`) casa contra `_norm(mensagem)`
(`corridor_playbooks.py:71-77`), que **remove acentos, remove o asterisco de
negrito e passa para minúsculas**.

📊 Provado por execução, 18/08/2026:

```text
$ python -c "<anchor_from_text + _norm, ver §Bloco B>"
sem acento               ancora casa? False
   ancora  = \*Importante:\*\ Esse\ servico\ de\ eletricista\ esta\ disponivel\ ap
   _norm   = importante: esse servico de eletricista esta disponivel apenas para re
COM acento (texto real)  ancora casa? False
```

**Nas duas formas, `False`.** O asterisco escapado e os acentos estão na
âncora e não estão no texto normalizado. Mesmo que o Alfaiate rodasse, **todo
overlay que ele escrevesse seria letra morta.**

### C3 · O escritor e o leitor usam nomes de playbook diferentes

| | valor | origem |
|---|---|---|
| **escreve** | `allianz:todos` | `route_sentinel.py:203` — `f"{insurer_key}:{ramo}"` |
| **lê** | `allianz-residencial-whatsapp@v1` | `corridor_playbooks.py:2276` — `f"{playbook_id}@v{version}"` |

📊 `grep '"playbook_id"' corridor_playbooks.py` → `allianz-residencial-whatsapp`,
`hdi-residencial-whatsapp`, `porto-residencial-whatsapp`,
`yelum-residencial-whatsapp`, `f"{insurer_key}-auto-whatsapp"`.

**Os dois espaços de nomes nunca se cruzam.** `_OVERLAY_CACHE.get(ref)` erraria
mesmo com a linha gravada e a âncora certa.

### C4 · O overlay não tem como dizer "responda 1"

Este é o mais importante, e é invisível até se ler o renderizador.

`corridor_playbooks.get_playbook` (linhas 2308-2323) injeta overlays assim:

```python
extra = [
    {"step": f"overlay_noop_{i}", "anchor": str(o.get("anchor") or ""),
     "reply": "", "noop": True, "notes": str(o.get("note") or "Alfaiate")}
    for i, o in enumerate(overlays) if o.get("anchor")
]
```

`"reply": ""`, `"noop": True` — **fixos, no código.** E a tabela acompanha:

📊 `information_schema.columns` para `playbook_overlays`, 18/08/2026 — **8
colunas**:

```text
id · playbook_ref · kind (default 'noop') · anchor · note
status (default 'active') · source (default 'alfaiate') · created_at
```

**Não existe coluna de resposta.** Não existe coluna de slot, de evidência, de
decisor, de motivo. O vocabulário inteiro do overlay é *"ignore esta tela"*.

> **Um overlay pode calar o corredor diante de uma tela. Nunca pode fazê-lo
> responder.** Aprovar uma proposta hoje não teria efeito nenhum — e é por isso
> que o leitor é o item mais importante desta SPEC, não a proposta.

📊 E o resultado combinado dos quatro:

```sql
select count(*) from playbook_overlays;   -->  0
```

**Zero linhas, em todas as corretoras, desde sempre. O Alfaiate nunca escreveu
uma linha.**

## 0.5 O que o Founder decidiu, textualmente

> *"Nunca automático. Escrever passo errado no playbook é pior que não escrever
> — abriria o chamado errado no nome de um segurado real."*

Esta frase é a **invariante I1** desta SPEC e não é negociável por nota de
0 a 100.

---

# 1. Autoridade — antes de tocar em uma linha

```text
CLAUDE.md (processo)  — §9 método · §9.2 controle · §9.3 mutação · §12.1 📊/💭
→ SPEC-052 · SPEC-053
→ docs/canon/O-ATLAS-E-UM-SO-E-E-DE-TODAS.md        ← o Bloco G depende deste
→ docs/canon/O-ATLAS-E-PARA-QUEM-ESCREVE-O-CORREDOR.md  ← §5 CONFLITA, ver §2.2
→ docs/canon/PORTAIS-E-CORREDORES.md · GLOSSARIO.md
→ docs/canon/MIGRATIONS-AUTHORITY.md                ← antes de qualquer SQL
→ SPEC-034 Onda 2 (Simulador) e Onda 4 (Alfaiate)
→ SPEC-050 (o gate roda ANTES da escrita — não afrouxar)
→ SPEC-061 §10 (proibido criar hub novo no Portal Admin)
```

---

# 2. Preflight

## 2.1 O preflight de sempre

```bash
git rev-parse --show-toplevel      # AutoBrokers-FIX
git branch --show-current
git rev-parse HEAD                 # registrar no relatório
git status --short                 # limpo ao iniciar
```

## 2.2 🔴 O conflito canônico que precisa de decisão ANTES do Bloco C

**FATO.** `docs/canon/O-ATLAS-E-PARA-QUEM-ESCREVE-O-CORREDOR.md` §5 diz, numa
tabela intitulada *"O que fica DESLIGADO, e por quanto tempo"*:

| Peça | Estado que o documento manda | 📊 Estado real em 18/08/2026 |
|---|---|---|
| promover mapa para `active` | 🔴 **não fazer** | **feito** — 10 mapas `active`, 10 seguradoras |
| Sentinela de Rotas | 🟡 "roda e é inerte, `route_drift` = 0 linhas" | **viva** — 4 drifts gravados |
| Alfaiate | 🔴 **não ligar** | continua sem rodar (por C1, não por decisão) |

```sql
select status, count(*) as mapas, count(distinct insurer_key) as seguradoras
  from ura_maps group by 1;
-- active 10 mapas / 10 seguradoras · superseded 280 · retired 19
select count(*) from route_drift;   -- 4
```

**O documento canônico descreve um mundo que não existe mais.** A justificativa
que ele dá para manter tudo desligado — *"📊 Nunca aconteceu um acionamento.
`work_runs` com `workflow_key ilike '%acionamento%'` = 0 linhas"* — também
venceu: houve acionamento real em 18/08/2026, e é dele que nasce esta SPEC.

**INFERÊNCIA.** O motivo original de manter o Alfaiate desligado era
*"escreve overlay em playbook sozinho"*. Esta SPEC **remove esse motivo**: com
`status='proposto'`, o Alfaiate deixa de escrever no playbook e passa a escrever
numa fila de propostas que ninguém lê até o Founder aprovar.

**RECOMENDAÇÃO — parada legítima, CLAUDE.md §10(3).** Antes do Bloco C, o
executor **registra em `FOUNDER-DECISIONS.md`** e obtém decisão explícita sobre:

```text
D-a  O Alfaiate volta a ser executado, restrito a PROPOR (status='proposto'),
     sem nenhum caminho de auto-aplicação para telas de menu?
D-b  O §5 de O-ATLAS-E-PARA-QUEM-ESCREVE-O-CORREDOR.md é atualizado para
     descrever o estado real (10 mapas ativos, Sentinela viva)?
```

> **Por que isto é parada e não nota de 0 a 100:** CLAUDE.md §12.1 ensina que
> documento canônico que descreve um bloqueio já removido **não protege — ensina
> a ignorar o documento**. Executar contra um canônico vencido sem corrigi-lo
> repete exatamente o defeito que o próprio repositório documenta.

## 2.3 O preflight de estado

```sql
-- 1. A fila de propostas começa vazia.
select status, count(*) from playbook_overlays group by 1;
-- ESPERADO hoje: zero linhas.

-- 2. Nenhum agente de atendimento ligado (a SPEC não os liga).
select c.company_name, a.name from agents a join companies c on c.id=a.company_id
 where a.agent_role='attendance' and a.is_active = true;
-- ESPERADO: zero linhas.
```

---

# 3. Definições que não podem ser misturadas

| Palavra | Significado nesta SPEC |
|---|---|
| **Atlas** | os mapas de URA observados. `ura_maps`. **Global, de todas as corretoras** |
| **Corredor** | o roteiro que responde a URA. `corridor_playbooks.py`. **Código, não dado** |
| **Passo** (`ura_step`) | `{step, anchor, reply, requires, noop, only_subservices, notes}` — dict dentro de `ura_steps` |
| **Overlay** | linha de `playbook_overlays` que ACRESCENTA um passo ao playbook em runtime, sem deploy |
| **Proposta** | overlay com `status='proposed'`. **Invisível ao motor por construção** |
| **Âncora** | a regex que reconhece a tela. Casada contra `_norm(texto)` — sem acento, sem `*`, minúscula |
| **Constante** | resposta fixa no overlay. A escolha pertence à **corretora** ou à **seguradora** |
| **Slot** | resposta preenchida pelo caso. A escolha pertence ao **atendimento**. **É o default** |
| **Simulador** | `ura_simulator.simulate()`. Repassa telas reais ao motor, offline. **Não é rede** |
| **Drift** | diferença entre o mapa ativo e o observado. `route_drift`. **Grão errado para aprovar** |

> **"Alfaiate automático" é nome proibido nesta SPEC.** O Alfaiate propõe. Quem
> aplica é o Founder.

---

# 4. Invariantes — se uma delas quebrar, a SPEC falhou

```text
I1  Nenhum passo entra no playbook sem aprovação humana explícita. NUNCA.
I2  Proposta não aprovada é invisível ao motor. Não por disciplina — por filtro.
I3  Na dúvida entre constante e slot, é SLOT. Sempre. Sem exceção configurável.
I4  A máquina só propõe âncora LITERAL. Alternação e curinga são escrita humana.
I5  Overlay nunca sobrepõe passo escrito à mão: entra DEPOIS na lista ordenada.
I6  Nenhuma peça desta SPEC chama LLM. Custo de API = zero.
I7  Nada perto da confirmação final vira proposta. Nem para revisão.
I8  Nenhum dado de segurado é persistido na proposta. Só texto templatizado.
I9  Nenhum motor paralelo. O Alfaiate, o Simulador e a tela do Atlas são os que existem.
```

---

# 5. A arquitetura, em uma figura

```text
observed_events            ura_maps (active)          corridor_playbooks.py
  (o que a URA disse)        (o mapa tecido)            (os passos escritos à mão)
        │                          │                            │
        └──────────┬───────────────┘                            │
                   ▼                                            │
        BLOCO C · RECONCILIADOR  ────────── match_ura_step ──────┘
        "que tela de menu o acervo tem                  (nenhum passo casa?)
         que nenhum passo responde?"
                   │
                   ▼
        BLOCO D · DISCERNIMENTO          constante  ou  slot
        (as respostas humanas variaram?)
                   │
                   ▼
        BLOCO E · SIMULADOR (portão diferencial)
        controle: hoje a tela fica `unanswered`
        candidato: com o overlay ela é respondida, e nada mais diverge
                   │
                   ▼
        playbook_overlays  status='proposed'   ◀── invisível ao motor
                   │
                   ▼
        BLOCO F · O FOUNDER DECIDE   (/admin/atlas → aba Propostas + Caixa de Entrada)
                   │
          aprovar ─┴─ recusar
             │            └──> status='rejected' + motivo
             ▼
        status='active'
                   │
                   ▼
        refresh_overlay_cache() ──> _OVERLAY_CACHE ──> get_playbook() ──> o corredor responde
                   │
                   ▼
        BLOCO G · REVERSÃO: 'active' → 'reverted', sem deploy
```

---

# 6. BLOCO A — O overlay aprende a responder

**Gate:** `get_playbook()` monta um passo que RESPONDE a partir de uma linha de
`playbook_overlays`, e o teste de mutação prova que o guarda consegue ficar
vermelho.

> Este bloco é o **primeiro** porque sem ele todo o resto é teatro: uma proposta
> aprovada não teria como virar resposta (C4).

## A.1 — A migration

**Diretório canônico:** `backend/supabase/migrations/`.
**Arquivo:** `20260818_01_spec080_o_overlay_sabe_responder.sql`

> 🔴 **É `ALTER`, nunca `CREATE`.** `playbook_overlays` existe em produção e
> **não tem arquivo no repositório** — foi aplicada pela versão
> `20260714001905 spec034_onda4_tailor_auditor`, listada em
> `MIGRATIONS-AUTHORITY.md` §4 entre as nove versões órfãs. Recriar a tabela
> apagaria o objeto vivo.

```sql
-- =============================================================
-- MIGRATION: o_overlay_sabe_responder
-- SPEC:      SPEC-080 — Bloco A
-- AUTOR:     <executor>            DATA: 2026-08-18
-- OBJETIVO:  dar ao overlay vocabulário para RESPONDER uma tela, e para
--            carregar a proposta, a evidência e a decisão humana.
--
-- APPLY:     acrescenta 12 colunas a public.playbook_overlays, um CHECK de
--            kind, um CHECK de status, e dois índices de leitura.
-- VERIFY:    ver bloco VERIFY abaixo (SQL executável).
-- ROLLBACK:  ver bloco ROLLBACK abaixo.
--
-- EXPAND-FIRST: sim — só adiciona. Nenhuma coluna existente muda de tipo,
--               de default ou de nulidade. O leitor atual continua
--               funcionando sem alteração.
-- DESTRUTIVA:   não
-- =============================================================

-- ---------- APPLY ----------
ALTER TABLE public.playbook_overlays
  ADD COLUMN IF NOT EXISTS reply             text,
  ADD COLUMN IF NOT EXISTS requires          jsonb  NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS only_subservices  jsonb  NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS insurer_key       text,
  ADD COLUMN IF NOT EXISTS ramo              text,
  ADD COLUMN IF NOT EXISTS tela              text,
  ADD COLUMN IF NOT EXISTS evidencia         jsonb  NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS simulador         jsonb  NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS decidido_por      text,
  ADD COLUMN IF NOT EXISTS decidido_em       timestamptz,
  ADD COLUMN IF NOT EXISTS motivo_da_decisao text,
  ADD COLUMN IF NOT EXISTS drift_id          uuid;

COMMENT ON COLUMN public.playbook_overlays.reply IS
  'Resposta do passo. Vazio/NULL quando kind=noop. Template com {slot} quando kind=slot.';
COMMENT ON COLUMN public.playbook_overlays.requires IS
  'Array JSON de nomes de slot exigidos. Alimenta missing_slots_for_subservice: '
  'um slot aqui passa a ser COBRADO do caso ANTES do acionamento comecar.';
COMMENT ON COLUMN public.playbook_overlays.tela IS
  'Texto TEMPLATIZADO da tela (do no do mapa), nunca observed_events.text cru. '
  'CLAUDE.md secao 7: dado de segurado nao entra aqui.';
COMMENT ON COLUMN public.playbook_overlays.evidencia IS
  'Prova: {vezes, sessoes, primeira, ultima, event_ids[], respostas_humanas{}}.';

-- kind: o vocabulario fechado. 'noop' continua sendo o default historico.
ALTER TABLE public.playbook_overlays
  DROP CONSTRAINT IF EXISTS playbook_overlays_kind_check;
ALTER TABLE public.playbook_overlays
  ADD CONSTRAINT playbook_overlays_kind_check
  CHECK (kind IN ('noop', 'reply', 'slot'));

-- status: 'active' e o default historico e NAO muda (expand-first).
ALTER TABLE public.playbook_overlays
  DROP CONSTRAINT IF EXISTS playbook_overlays_status_check;
ALTER TABLE public.playbook_overlays
  ADD CONSTRAINT playbook_overlays_status_check
  CHECK (status IN ('proposed', 'active', 'rejected', 'reverted'));

-- Um overlay que responde PRECISA ter resposta. Um noop nao pode ter.
ALTER TABLE public.playbook_overlays
  DROP CONSTRAINT IF EXISTS playbook_overlays_reply_coerente;
ALTER TABLE public.playbook_overlays
  ADD CONSTRAINT playbook_overlays_reply_coerente
  CHECK (
    (kind = 'noop' AND (reply IS NULL OR reply = ''))
    OR (kind IN ('reply','slot') AND reply IS NOT NULL AND reply <> '')
  );

-- Nao propor duas vezes a mesma tela para o mesmo playbook.
CREATE UNIQUE INDEX IF NOT EXISTS uq_playbook_overlays_ref_anchor_vivo
  ON public.playbook_overlays (playbook_ref, anchor)
  WHERE status IN ('proposed', 'active');

-- A leitura de runtime filtra status='active'.
CREATE INDEX IF NOT EXISTS idx_playbook_overlays_ativos
  ON public.playbook_overlays (status, playbook_ref);
```

**VERIFY** — SQL executável, saída real registrada no relatório:

```sql
-- 1. As 12 colunas existem, com os defaults certos.
select column_name, data_type, is_nullable, column_default
  from information_schema.columns
 where table_schema='public' and table_name='playbook_overlays'
   and column_name in ('reply','requires','only_subservices','insurer_key','ramo',
                       'tela','evidencia','simulador','decidido_por','decidido_em',
                       'motivo_da_decisao','drift_id')
 order by column_name;
-- ESPERADO: 12 linhas.

-- 2. Os tres CHECK existem.
select conname from pg_constraint
 where conrelid='public.playbook_overlays'::regclass and contype='c'
 order by conname;
-- ESPERADO: inclui playbook_overlays_kind_check, _status_check, _reply_coerente.

-- 3. O CHECK de coerencia MORDE (prova que a trava consegue reprovar).
do $$
begin
  insert into public.playbook_overlays (playbook_ref, kind, anchor, reply)
  values ('__verify__', 'reply', '__verify__', '');
  raise exception 'FALHOU: aceitou kind=reply com reply vazio';
exception when check_violation then
  raise notice 'OK: o CHECK de coerencia mordeu';
end $$;

-- 4. Nada foi perdido.
select count(*) from public.playbook_overlays;
-- ESPERADO: o mesmo numero de antes (hoje, 0).
```

**ROLLBACK** — escrito antes de aplicar:

```sql
DROP INDEX IF EXISTS public.uq_playbook_overlays_ref_anchor_vivo;
DROP INDEX IF EXISTS public.idx_playbook_overlays_ativos;
ALTER TABLE public.playbook_overlays
  DROP CONSTRAINT IF EXISTS playbook_overlays_reply_coerente,
  DROP CONSTRAINT IF EXISTS playbook_overlays_status_check,
  DROP CONSTRAINT IF EXISTS playbook_overlays_kind_check;
ALTER TABLE public.playbook_overlays
  DROP COLUMN IF EXISTS reply,            DROP COLUMN IF EXISTS requires,
  DROP COLUMN IF EXISTS only_subservices, DROP COLUMN IF EXISTS insurer_key,
  DROP COLUMN IF EXISTS ramo,             DROP COLUMN IF EXISTS tela,
  DROP COLUMN IF EXISTS evidencia,        DROP COLUMN IF EXISTS simulador,
  DROP COLUMN IF EXISTS decidido_por,     DROP COLUMN IF EXISTS decidido_em,
  DROP COLUMN IF EXISTS motivo_da_decisao,DROP COLUMN IF EXISTS drift_id;
```

> ⚠️ O ROLLBACK é **destrutivo por natureza** (derruba colunas). Só é aplicável
> enquanto não houver overlay `active` em produção. Depois disso, a reversão
> correta é a do **Bloco G** (`status='reverted'`), não o DDL.

**Sobre RLS.** 📊 `pg_policies` para `playbook_overlays` → **zero linhas**;
`20260721_01_spec047_rls_e_company_members.sql:10` habilita RLS sem policy, de
propósito: a tabela é de **service role apenas**, e `anon`/`authenticated` não
têm acesso nenhum. Esta SPEC **não altera isso** e não adiciona policy — ver
§12 para o porquê multi-tenant.

## A.2 — `get_playbook()` passa a renderizar três formas

`backend/app/services/corridor_playbooks.py:2308-2323`. O bloco `extra` deixa de
ser fixo em `noop`:

```python
def _passo_de_overlay(o: Dict[str, Any], i: int) -> Optional[Dict[str, Any]]:
    """Um overlay vira passo. `noop` cala; `reply` responde; `slot` exige o caso.

    🔴 A ORDEM é a proteção (CLAUDE.md §9.2, mutação M4b do commit 8aa15be):
    o passo entra DEPOIS de todos os escritos à mão, e `match_ura_step` para no
    primeiro que casa. Um overlay NUNCA sequestra uma tela que já tem dono.
    """
    anchor = str(o.get("anchor") or "")
    if not anchor:
        return None
    kind = str(o.get("kind") or "noop")
    passo: Dict[str, Any] = {
        "step": f"overlay_{kind}_{i}",
        "anchor": anchor,
        "notes": str(o.get("note") or "Alfaiate"),
        "overlay_id": str(o.get("id") or ""),   # rastreabilidade: qual proposta respondeu
    }
    if kind == "noop":
        passo.update({"reply": "", "noop": True})
        return passo
    passo["reply"] = str(o.get("reply") or "")
    requires = o.get("requires") or []
    if requires:
        passo["requires"] = [str(x) for x in requires]
    only = o.get("only_subservices") or []
    if only:
        passo["only_subservices"] = [str(x) for x in only]
    return passo
```

**Nada mais muda no motor.** `match_ura_step`, `render_reply` e
`missing_slots_for_subservice` já sabem lidar com `reply`, `requires` e
`only_subservices` — 📊 são as mesmas chaves que os 14 playbooks escritos à mão
usam (`corridor_playbooks.py:254-255` é o precedente exato:
`"reply": "{profissional_opcao}"`, `"requires": ["profissional_opcao"]`).

## A.3 — `refresh_overlay_cache()` passa a trazer as colunas novas

`backend/app/services/conversation_auditor.py:115`:

```python
.select("id, playbook_ref, kind, anchor, note, reply, requires, only_subservices")
.eq("status", "active")
```

**O filtro `status='active'` não muda** — e é ele que dá a invariante I2 de
graça: uma proposta nasce `proposed`, e **o motor nunca a vê**. Não é
disciplina, é o `WHERE`.

## A.4 — A latência da aprovação

📊 **FATO:** `refresh_overlay_cache()` só é chamada por `check_auditor()`
(`conversation_auditor.py:132`), que roda **1×/dia**
(`buffer_processor.py:154-160`). Um overlay aprovado levaria até 24 h para
valer, e o Founder concluiria que a aprovação não funcionou.

Duas mudanças, ambas pequenas:

1. A rota de decisão (Bloco F) chama `refresh_overlay_cache()` logo após gravar.
2. `refresh_overlay_cache()` ganha agendamento próprio, a cada
   `OVERLAY_CACHE_REFRESH_MINUTES` (padrão **15**), independente do Auditor.

> ⚠️ **Cache é por processo.** `_OVERLAY_CACHE` é um global de módulo
> (`corridor_playbooks.py:2300`). Com N réplicas de `smith-api`, o refresh na
> rota atualiza **uma** delas. O agendamento periódico é o que cobre as outras —
> por isso ele não é opcional, e por isso o teto de 15 min é o contrato honesto
> a comunicar na tela ("vale em até 15 minutos"), não "vale agora".

## A.5 — Teste e mutação

**Arquivo:** `backend/tests/test_o_overlay_aprovado_faz_o_corredor_responder.py`
**Script:** `npm run test:overlay-responde`

| # | Asserção |
|---|---|
| 1 | overlay `kind='noop'` → passo com `noop=True` e `reply=''` (**controle**: o comportamento antigo não regrediu) |
| 2 | overlay `kind='reply'`, `reply='1'` → `match_ura_step` acha o passo e `render_reply` devolve `"1"` |
| 3 | overlay `kind='slot'`, `reply='{o_que_aconteceu}'`, `requires=['o_que_aconteceu']` → sem o slot, `render_reply` devolve `ok=False, missing=['o_que_aconteceu']` — **não chuta** |
| 4 | com o slot preenchido, devolve o valor do caso |
| 5 | `missing_slots_for_subservice` passa a exigir `o_que_aconteceu` |
| 6 | **ordem**: uma tela que JÁ tem passo à mão continua casando o passo à mão, mesmo com overlay de âncora mais larga |
| 7 | `_OVERLAY_CACHE` vazio → `get_playbook` devolve o playbook idêntico ao original (`is` na lista `ura_steps`) |

**Mutações que provam que o guarda consegue ficar vermelho** (CLAUDE.md §9.3):

| Mutação | Esperado |
|---|---|
| **M1** — `_passo_de_overlay` volta a forçar `noop=True` | asserções 2, 3, 4, 5 **vermelhas** |
| **M2** — o overlay entra ANTES dos passos à mão (`extra + base`) | asserção 6 **vermelha** |
| **M3** — `render_reply` passa a chutar `""` em vez de `missing` | asserção 3 **vermelha** |
| **M4** — o filtro `status='active'` vira `status<>'x'` | um overlay `proposed` aparece no cache → asserção nova (I2) **vermelha** |
| **M5 (controle)** — trocar `notes` por `note` no dict do passo | **VERDE** — provando que o teste mede comportamento, não forma |

> **Sobre a M5:** ela existe para o mesmo fim da M4 do commit `8aa15be`, que
> ficou verde e foi informativa. Um teste que ficasse vermelho ao renomear um
> campo cosmético estaria medindo a forma do dict, não o comportamento do motor.

---

# 7. BLOCO B — Os três curtos-circuitos do Alfaiate

**Gate:** uma âncora gerada pela máquina casa a tela real do acervo; o ref
escrito é o ref que o motor procura; e a tela nova de menu chega ao Alfaiate.

## B.1 — A âncora nasce contra o texto NORMALIZADO (C2)

`playbook_tailor.anchor_from_text` passa a normalizar antes de escapar:

```python
def anchor_from_text(text: str) -> str:
    """Âncora LITERAL a partir do texto normalizado da tela.

    🔴 Casa contra `_norm(mensagem)` — sem acento, sem `*`, minúscula. Escapar o
    texto CRU produzia `\\*Importante:\\*\\ Esse\\ servi\\ço…`, que não casa nada.
    📊 Provado por execução em 18/08/2026: as duas formas devolviam False.

    🔴 E é literal DE PROPÓSITO (invariante I4). `re.escape` não produz `|`, `.`
    nem `*` — logo a âncora da máquina **não tem como ser gulosa** e não pode
    engolir a confirmação final. Alternação é escrita humana, e só.
    """
    from app.services.corridor_playbooks import _norm

    bruto = _norm(str(text or "")).strip()
    trecho = _TRECHO_ESTAVEL.sub(" ", bruto)[:60].strip()
    return re.escape(trecho) if len(trecho) >= 20 else ""
```

Duas regras acompanham:

- `_TRECHO_ESTAVEL` colapsa espaços/quebras (a URA reformata a mesma tela).
- **`len(trecho) >= 20`**: âncora curta demais é gulosa por acidente. 💭 Exemplo
  ilustrativo: `"o que aconteceu?"` tem 16 caracteres e apareceria em telas de
  ramos diferentes. Abaixo do piso, **não se propõe** — vira pendência, não
  palpite.

## B.2 — O ref escrito é o ref que o motor procura (C3)

`route_sentinel.py:203` deixa de montar `f"{insurer_key}:{ramo}"` e passa a usar
a autoridade que já existe:

```python
from app.services.corridor_playbooks import resolve_playbook_ref
playbook_ref = resolve_playbook_ref(insurer_key, line_kind=ramo)
if not playbook_ref:
    return None   # seguradora sem corredor escrito: nada a propor
```

📊 `resolve_playbook_ref` (`corridor_playbooks.py:2435`) é a função que o motor
usa; usar a mesma nos dois lados fecha a classe em vez de consertar um caso.

> ⚠️ **`ramo` do Atlas é `'todos'`** (📊 `RAMO_COMPLETO = "todos"`,
> `ura_map_service.py:194`; e os 10 mapas ativos têm `ramo='todos'`), enquanto
> `resolve_playbook_ref` espera `auto` | `residencial`. **Uma tela observada
> pode pertencer a mais de um corredor da mesma seguradora.** A regra:
> **propõe-se para o corredor cujo acervo contém a tela**, determinado por
> `observed_sessions.ramo`/`servico` das sessões que a produziram. Tela vista em
> sessões de dois ramos gera **duas propostas independentes**, cada uma com sua
> evidência. Nenhuma proposta "vale para os dois".

## B.3 — A tela nova de menu chega ao Alfaiate (C1)

`classify_severity` **não muda** — a classificação `structural` está certa, e um
menu novo continua exigindo olho humano. O que muda é o que se faz com ela:

```python
# route_sentinel.check_insurer, hoje linhas 200-208
if severity == "cosmetic":
    gate = await _alfaiate_with_gate(...)        # auto-aplica noop, como hoje
elif severity == "structural" and _propostas_ligadas():
    # NÃO auto-aplica. Só PROPÕE, e a proposta nasce invisível.
    await propor_passos(playbook_ref, active_map, observed_map, drift_id=...)
```

**A diferença que importa:** o ramo cosmético continua chamando
`apply_auto_overlays` (escreve `status='active'`); o ramo estrutural chama
`propor_passos`, que escreve **`status='proposed'`** e nada mais. O alerta ao
Founder continua sendo emitido.

📊 O balde certo já existe e já está correto: `classify_diff`
(`playbook_tailor.py:29-55`) separa `auto` / `approval` / `never`, e o balde
`approval` é definido como *"telas novas COM opções ou menus alterados"* —
exatamente o alvo. Hoje ele só vira texto em `render_patch_report` e é jogado
fora. **Esta SPEC persiste o balde `approval` que já é calculado.**

## B.4 — Teste e mutação

**Arquivo:** `backend/tests/test_a_ancora_da_maquina_casa_a_tela_de_verdade.py`
**Script:** `npm run test:ancora-da-maquina`

Roda contra **os textos reais do acervo** (mesmo método de
`test_o_corredor_conhece_a_tela_que_esta_na_frente.py`), com fixture das 8
ocorrências da tela do eletricista.

| # | Asserção |
|---|---|
| 1 | `anchor_from_text(tela_real)` casa `_norm(tela_real)` — **e a versão antiga NÃO casa** (linha de controle: prova que o conserto é o que mudou) |
| 2 | a âncora gerada **não** contém `|`, `.` , `+`, `*` fora de escape (I4) |
| 3 | a âncora gerada **não** casa a tela de confirmação final da Allianz (controle anti-guloso) |
| 4 | texto com menos de 20 caracteres úteis → `""` |
| 5 | `resolve_playbook_ref('allianz', 'residencial')` devolve um ref presente em `list_playbooks()` |
| 6 | `f"{insurer_key}:{ramo}"` **não** está em `list_playbooks()` — o namespace antigo era mesmo inútil |

| Mutação | Esperado |
|---|---|
| **M1** — `anchor_from_text` volta a `re.escape(texto_cru[:60])` | asserção 1 **vermelha** |
| **M2** — o piso de 20 caracteres cai para 5 | asserções 3 e 4 **vermelhas** |
| **M3** — a âncora passa a juntar as opções com `|` | asserção 2 **vermelha**, e 3 provavelmente também |
| **M4 (controle)** — mudar o limite de 60 para 55 caracteres | **VERDE** — o teste mede casamento, não comprimento |

---

# 8. BLOCO C — O Detector: a tela órfã vira proposta

**Gate:** rodando contra o acervo real, o detector encontra a tela do
eletricista, produz uma proposta com evidência, e **não** produz proposta para
nenhuma tela que já tem passo.

## C.1 — Por que o `route_drift` é o grão errado

📊 Os quatro drifts existentes, medidos em 18/08/2026:

```sql
select insurer_key, severity, status, summary, created_at from route_drift order by created_at;
```

```text
allianz  structural  escalated  "99 telas novas, 216 removidas, 0 menus alterados"   11/08
porto    structural  escalated  "143 telas novas, 126 removidas, 0 menus alterados"  11/08
allianz  structural  escalated  "30 telas novas, 0 removidas, 0 menus alterados"     14/08
tokio    structural  escalated  "13 telas novas, 14 removidas, 0 menus alterados"    14/08
```

**Ninguém aprova "99 telas novas".** O drift é a unidade de *detecção de
mudança*; ela não é a unidade de *decisão*. E a dedupe por assinatura
(`route_sentinel.py:152`, SHA-256 sobre o diff inteiro, com claim de 90 dias)
faz com que um drift enorme **suprima** todos os seguintes daquela seguradora
— inclusive um que trouxesse uma única tela crítica.

> **A unidade de aprovação é UMA TELA.** É a única granularidade em que "sim" e
> "não" significam alguma coisa.

📊 E note a coluna que fecha o argumento: nos quatro, `changed_options` = **0**.
A classificação `structural` veio inteira do caminho *"tela nova com
`kind` menu/pergunta/app_form"* — que é exatamente a classe que esta SPEC ataca.

## C.2 — O Reconciliador

**Arquivo novo:** `backend/app/services/atlas/reconciliador_de_telas.py`

> **Por que é arquivo novo e não motor paralelo (CLAUDE.md §5):** ele não
> executa, não agenda, não publica e não decide. É uma **consulta** que compara
> dois artefatos existentes (acervo × playbook) e escreve na tabela de propostas
> que já existe. Nenhuma peça do runtime muda de dono.

```python
async def telas_orfas(insurer_key: str, ramo: str, *, dias: int = 30,
                      minimo_de_sessoes: int = 3) -> List[TelaOrfa]:
    """Telas de MENU que o acervo tem e que nenhum passo do corredor responde.

    Determinístico, offline, sem LLM. O caminho quente do acionamento NÃO é
    tocado: isto roda fora dele, sobre o que já foi gravado.
    """
```

Pipeline, em cinco filtros e nesta ordem:

```text
1. CANDIDATAS   observed_events das últimas `dias`, direction='in',
                insurer_key = alvo, agrupadas por impressão digital do texto
                normalizado. Só entram as que `opcoes_da_tela()` extrai >= 2 opções.
                  ↑ reusa corridor_playbooks.opcoes_da_tela (linha 3283), que já
                    conhece os TRÊS formatos reais: `*1 -* Sim`, `Botão 1: Agora`
                    e a lista sem número da Porto/Azul.

2. ÓRFÃS        match_ura_step(get_playbook(ref), tela) is None
                  ↑ a pergunta é feita ao MOTOR, não a uma cópia da lógica dele.

3. VETO FINAL   descarta se `_FINALIZE_HINT` casa (playbook_tailor.py:25:
                confirmar|prosseguir|tudo está correto|agendamento)  → I7
                descarta se a tela casa qualquer `finalize_anchors` do playbook.

4. VETO DE PII  a tela persistida é a TEMPLATIZADA do nó do mapa; se não houver
                nó correspondente, a tela é mascarada pelo mascarador existente.
                Nenhum `observed_events.text` cru é gravado.               → I8

5. PISO         >= `minimo_de_sessoes` sessões distintas. Uma tela vista uma vez
                é ruído; três vezes é padrão.
```

O que sai:

```python
@dataclass
class TelaOrfa:
    playbook_ref: str
    tela: str                      # templatizada
    anchor: str                    # anchor_from_text(tela)
    opcoes: List[Tuple[str, str]]  # [(tecla, rótulo)]
    vezes: int
    sessoes: int
    primeira: datetime
    ultima: datetime
    event_ids: List[str]           # até 20, para auditoria
    respostas_humanas: Dict[str, int]   # {"1": 4, "2": 1} — insumo do Bloco D
```

## C.3 — De onde vem `respostas_humanas`

Duas fontes, nesta ordem de preferência:

1. **O mapa** — `ura_maps.map.paths[].steps[].c` guarda a tecla que o humano
   apertou naquele nó. 📊 É a mesma fonte que `_script_from_observed`
   (`route_sentinel.py:281-295`) usa para montar o script do Simulador, e o
   `weaver` ordena `paths` por data ascendente de propósito.
2. **O acervo** — o primeiro `observed_events` com `direction='out'` na mesma
   `session_id` depois do evento da tela, quando o texto for uma tecla curta.

> Se as duas discordarem, **vale o acervo** e a divergência é registrada na
> `evidencia`. O mapa é derivado; o acervo é o fato.

## C.4 — Quando roda

Junto do Sentinela, que já é agendado a cada
`ATLAS_INCREMENTAL_INTERVAL_MINUTES` (📊 padrão 15,
`buffer_processor.py:188-197`), e sob o mesmo claim de Redis — **não se cria
scheduler novo** (CLAUDE.md §5).

## C.5 — Teste e mutação

**Arquivo:** `backend/tests/test_a_tela_que_ninguem_responde_vira_proposta.py`
**Script:** `npm run test:tela-orfa`

Fixtures: os textos reais do acervo, incluindo os 📊 8 eventos da tela do
eletricista (ids `c09f1300…`, `8e16936a…`, `9d004520…`, `9f64fa3d…`,
`af3da6ec…`, `d9ba09d2…`, `e7c4ee33…`, `1b6568d4…`).

| # | Asserção |
|---|---|
| 1 | a tela do eletricista é detectada como órfã **contra o playbook de 04/08** (antes do conserto à mão) |
| 2 | **linha de controle**: contra o playbook de HOJE, que já tem o passo, ela **não** é detectada |
| 3 | a tela de confirmação final **nunca** é detectada, nem sem passo (I7) |
| 4 | uma tela informativa sem opções não é detectada (é assunto do balde `auto`) |
| 5 | tela vista em 1 sessão só não é detectada (piso) |
| 6 | a `tela` gravada não contém CPF, telefone nem placa — varredura por regex (I8) |
| 7 | `respostas_humanas` da tela do eletricista bate com o acervo |

> **A asserção 2 é a que dá direito à conclusão.** Sem ela, um detector que
> devolvesse *todas* as telas passaria na asserção 1 e pareceria funcionar.

| Mutação | Esperado |
|---|---|
| **M1** — remover o filtro `match_ura_step is None` | asserção 2 **vermelha** |
| **M2** — remover o veto `_FINALIZE_HINT` | asserção 3 **vermelha** |
| **M3** — piso de sessões vai a 1 | asserção 5 **vermelha** |
| **M4** — gravar `observed_events.text` cru em vez do templatizado | asserção 6 **vermelha** |
| **M5 (controle)** — `dias` de 30 para 45 | **VERDE** — a janela não é o que protege |

---

# 9. BLOCO D — 🔴 O Discernimento: constante ou slot

**Gate:** a regra é executável, tem teste, e o default seguro é demonstrável.

> Este é o bloco em que um erro abre o chamado errado no nome de um segurado
> real. Ele é curto de propósito: **regra curta é regra auditável.**

## D.1 — O princípio, em uma frase

```text
A escolha é CONSTANTE quando pertence à SEGURADORA ou à CORRETORA.
A escolha é SLOT      quando pertence ao CASO.
Na dúvida, é do caso.
```

Isto é o mesmo teste do `O-ATLAS-E-UM-SO-E-E-DE-TODAS.md` §5, aplicado a uma
tecla em vez de a um nó de mapa:

| Tela | A quem pertence a escolha | Veredito |
|---|---|---|
| *"1 - reparo elétrico para residência / 2 - aparelhos e eletrodomésticos"* | à **seguradora**: a própria tela avisa que o serviço só cobre a residência. E à **corretora**: ela aciona para a casa | **constante `"1"`** |
| *"O que aconteceu? 1 - Casa sem energia / 2 - Curto circuito"* | ao **caso**: é o tipo do defeito | **slot, obrigatoriamente** |
| *"Para quando precisa? 1 - Agora / 2 - Agendar"* | à **corretora**: quem escreve para a corretora quer agora | constante `"1"` — 📊 e já é assim no código (`corridor_playbooks.py:279-284`) |

📊 Esta distinção **já foi feita à mão e está no repositório**: o commit
`8aa15be` acrescentou `tipo_de_reparo_eletrico` com `reply: "1"` e
`o_que_aconteceu` **sem `reply` fixo**, com o comentário
*"SEM `reply` FIXO. Esta escolhe o TIPO DE DEFEITO: tecla errada abre chamado
errado."* **Esta SPEC não inventa a regra — ela codifica a que um humano já
aplicou corretamente.**

## D.2 — A regra executável

Um princípio não é auditável; um predicado é. `constante_e_proponivel()`
devolve `True` **somente** se **todas** as condições valerem:

```text
G1  n_respostas_humanas_distintas == 1
G2  n_sessoes_com_resposta        >= 3
G3  n_opcoes_da_tela              <= 4
G4  nenhum rótulo casa _VOCABULARIO_DO_CASO
G5  a tela não casa _FINALIZE_HINT nem finalize_anchors
```

Qualquer falha → **slot**. Sem exceção, sem parâmetro, sem env var.

**G1 é o coração, e é empírico.** Se em todas as sessões reais o humano apertou
a mesma tecla, a escolha era política. Se variou, era fato do caso — e a
variação **é a prova**, não uma opinião sobre a semântica do rótulo.

**G4 é o cinto de segurança**, porque G1 pode mentir com pouca amostra: três
sessões de "casa sem energia" não fazem de "casa sem energia" a política da
corretora.

```python
_VOCABULARIO_DO_CASO = re.compile(
    r"o que aconteceu|qual (?:o |e o )?(?:tipo|motivo|problema|defeito)"
    r"|curto[- ]circuito|sem energia|vazamento|entupi|infiltra"
    r"|qual (?:o |a )?(?:local|comodo|ambiente)"
    r"|quantos|qual (?:o |a )?(?:marca|modelo|cor|placa)"
    r"|descreva|informe (?:o |a )",
    re.IGNORECASE)
```

> 💭 A lista acima é **ilustrativa na composição, normativa na função**: ela vai
> crescer. O que não pode mudar é o sentido do erro — **acrescentar termo
> empurra para slot; nunca para constante.** Um termo esquecido produz uma
> proposta de constante que o Founder ainda vai ver e pode recusar. Um termo a
> mais produz um slot desnecessário, que só pede um dado a mais. **Os dois erros
> não custam o mesmo, e a regra é assimétrica de propósito.**

## D.3 — Como fica o slot

```python
{"kind": "slot",
 "reply": "{o_que_aconteceu}",
 "requires": ["o_que_aconteceu"]}
```

**Consequência que precisa estar no gate:** 📊
`missing_slots_for_subservice` (`corridor_playbooks.py:3162-3180`) soma os
`requires` dos passos aos `required_slots` do subserviço. **Um slot aprovado
passa a ser cobrado do caso ANTES de o acionamento começar** — e é exatamente
esse o desenho certo, pela lição já escrita no próprio arquivo (linhas
3151-3158): sem isso, *"a sessão nascia `ready_to_send`, o acionamento começava,
e o corredor travava no meio da conversa, com a URA rodando e o cronômetro
correndo."*

O nome do slot vem de `_optional_keys()` quando houver correspondência; caso
contrário é derivado da tela e **fica registrado na proposta**, para o Founder
ver que nome novo vai passar a ser pedido.

## D.4 — Teste e mutação

**Arquivo:** `backend/tests/test_constante_so_quando_a_escolha_nao_e_do_caso.py`
**Script:** `npm run test:constante-ou-slot`

| # | Caso | Esperado |
|---|---|---|
| 1 | eletricista residência × eletrodoméstico, humanos sempre "1", 4 sessões | **constante** |
| 2 | *"O que aconteceu?"*, humanos sempre "1", 4 sessões | **slot** — G4 vence G1 |
| 3 | *"O que aconteceu?"*, humanos "1" e "2" | **slot** — G1 e G4 |
| 4 | tela boa, mas só 2 sessões | **slot** — G2 |
| 5 | tela boa, 7 opções | **slot** — G3 |
| 6 | tela de confirmação final | **nem proposta** — G5 / I7 |
| 7 | **controle**: caso 1 com uma única resposta divergente injetada | vira **slot** |

> **A asserção 7 é a linha de controle do bloco.** Ela prova que G1 consegue
> mudar o veredito — sem ela, um predicado que devolvesse "constante" sempre
> passaria nos casos 1 e 6.

| Mutação | Esperado |
|---|---|
| **M1** — remover G4 | caso 2 **vermelho** |
| **M2** — remover G1 | caso 3 e caso 7 **vermelhos** |
| **M3** — G2 cai para 1 sessão | caso 4 **vermelho** |
| **M4** — inverter o default (dúvida → constante) | casos 2, 3, 4, 5, 7 **vermelhos** |
| **M5 (controle)** — G3 sobe de 4 para 5 opções | **VERDE** com 7 opções; prova que o caso 5 não depende do número exato |

---

# 10. BLOCO E — O Simulador como portão diferencial

**Gate:** nenhuma proposta chega ao Founder sem duas rodadas do Simulador — uma
de controle e uma de candidato — e o resultado das duas fica gravado.

## E.1 — O que o Simulador é

📊 `backend/app/services/ura_simulator.py`, 85 linhas, `simulate(playbook_ref,
subservice, slots, script)`. Docstring: *"Puro — roda sem WhatsApp, sem Redis,
sem rede."* Dirige o motor real (`insurer_dispatch_service`) contra um script de
telas gravadas e devolve:

```python
{"ok": bool,                 # not divergences and not unanswered
 "reached_finalize": bool,
 "divergences": [...],       # respondeu DIFERENTE do humano
 "unanswered_screens": [...],# não respondeu nada
 "final_state": str}
```

**A propriedade que faz dele o portão certo:** `expected` é a resposta que **um
humano de verdade deu e que funcionou**. O Simulador não pergunta se a proposta
é bonita; pergunta se ela reproduz o que já deu certo.

## E.2 — O portão é DIFERENCIAL (CLAUDE.md §9.2)

Uma rodada só não autoriza conclusão nenhuma. São duas:

```text
RODADA A — CONTROLE      playbook atual            × script observado
           EXIGE:        a tela alvo aparece em `unanswered_screens`
           se não aparecer → a proposta é DESNECESSÁRIA, descarta-se em silêncio

RODADA B — CANDIDATO     playbook + overlay candidato × mesmo script
           EXIGE:        (1) a tela alvo SAIU de `unanswered_screens`
                         (2) len(divergences) não aumentou em relação a A
                         (3) a resposta emitida == a resposta do humano
```

**Aprova só quem passa nas três de B, tendo passado na exigência de A.**
Qualquer outra combinação → a proposta nasce marcada `simulador: reprovado` e
**não vai à fila do Founder** — vai para o relatório, para inspeção.

> **A rodada A é o que dá direito à conclusão.** Sem ela, uma proposta poderia
> ser creditada por consertar algo que já não estava quebrado — e o Founder
> aprovaria um passo inútil achando que consertou um buraco.

Fail-closed, como já é hoje (`route_sentinel.py:267`): **sem Simulador, sem
proposta.**

## E.3 — Dois defeitos do chamador atual, que este bloco conserta

📊 **E.3.a — o subserviço está pregado em `"guincho"`.**
`route_sentinel.py:261`: `sim = simulate(playbook_ref, "guincho", {}, script)`.
Para um corredor residencial isso é o subserviço errado, e `only_subservices`
faria passos legítimos serem pulados. Passa a vir de
`observed_sessions.servico` da sessão que gerou o script, com
`canonical_subservice()` por cima.

📊 **E.3.b — o script sai só do último caminho.**
`_script_from_observed` usa `paths[-1]`. Para validar uma tela específica, o
script tem de ser o do caminho **que contém aquela tela** — do contrário a
rodada A não a mostra como `unanswered` e a proposta é descartada por engano.
Passa a escolher o caminho mais recente **que contenha o nó alvo**.

## E.4 — Teste e mutação

**Arquivo:** `backend/tests/test_o_portao_do_simulador_e_diferencial.py`
**Script:** `npm run test:portao-simulador`

| # | Asserção |
|---|---|
| 1 | com o playbook de 04/08 e o script real do eletricista, a rodada A marca a tela como `unanswered` |
| 2 | com o overlay candidato `reply="1"`, a rodada B a remove de `unanswered` |
| 3 | a rodada B **não** aumenta `divergences` |
| 4 | a resposta emitida é `"1"` — igual à do humano no acervo |
| 5 | **controle**: se a rodada A já estiver limpa, a proposta é descartada e nada é gravado |
| 6 | overlay com resposta ERRADA (`"2"`) → rodada B gera divergência → **reprovado** |
| 7 | Simulador indisponível (exceção) → nenhuma proposta escrita (fail-closed) |

| Mutação | Esperado |
|---|---|
| **M1** — remover a exigência da rodada A | asserção 5 **vermelha** |
| **M2** — aceitar `divergences` que aumentaram | asserção 6 **vermelha** |
| **M3** — `except: passed = True` no lugar do fail-closed | asserção 7 **vermelha** |
| **M4** — voltar `subservice` para `"guincho"` fixo | asserções 1 e 2 **vermelhas** no corredor residencial |
| **M5 (controle)** — trocar `paths[-1]` por `paths[0]` numa seguradora de um caminho só | **VERDE** — prova que E.3.b só morde com múltiplos caminhos |

---

# 11. BLOCO F — A Decisão: onde o Founder aprova

**Gate:** o Founder vê a tela da URA, a resposta proposta, a evidência e o
veredito do Simulador; clica um dos dois botões; e o efeito é verificável no
banco e no motor.

## F.1 — Onde mora — e onde NÃO mora

📊 **Não se cria hub novo.** `SPEC-061 §10` proíbe (documentado em
`app/admin/layout.tsx:255-270`). A tela já existe:
`app/admin/atlas/page.tsx` (915 linhas) já renderiza o painel
*"🔔 Mudanças de menu detectadas"* (linhas 644-660) com o selo `⚠ revisar` —
**um selo que hoje não tem botão nenhum.** É exatamente o buraco que esta SPEC
preenche.

Entra uma **aba "Propostas"** dentro de `/admin/atlas`, no dialeto visual do
próprio arquivo.

📊 **E o aviso não sai por WhatsApp.** `route_sentinel._alert_founder` manda
mensagem pelo *"primeiro canal elegível"* varrendo `companies`
(`_canal_de_plataforma`, linha 337) — ou seja, o aviso de que a Porto mudou um
botão sairia pelo WhatsApp de uma corretora qualquer. A decisão do Founder,
registrada em `O-ATLAS-E-PARA-QUEM-ESCREVE-O-CORREDOR.md` §6, é literal:

> *"O Atlas é para inteligência interna do nosso sistema de atendimento. […] O
> aviso mora no **Portal Admin**, e em lugar nenhum mais. Nunca no canal de um
> tenant."*

📊 E o alerta atual **nunca chegou** — o comentário em `route_sentinel.py:311-326`
registra que um `TypeError` engolido fez com que *"o alerta de mudança
estrutural do Atlas nunca chegou ao Founder — nem uma vez."*

**Portanto:** o aviso de proposta pendente entra na **Caixa de Entrada** do
Portal Admin, que é o lugar canônico para "o que precisa de mim" — uma nova
`fonte` em `CaixaDeEntrada.montar()`
(`backend/app/services/control_plane/inbox.py`), com `href` para
`/admin/atlas?aba=propostas`, `severidade='medium'`,
`permission_para_agir='knowledge.curate'`, e `company_id=None` (é aviso de
plataforma, não de corretora). **Nenhum notificador paralelo** — a docstring
em `inbox.py:320-329` já proíbe explicitamente.

O front precisa registrar a `fonte` nova em `NOME_DA_FONTE`
(`app/admin/inbox/page.tsx:36-43`), senão a etiqueta sai como slug cru.

## F.2 — O que o cartão mostra

Cada proposta, um cartão. Sem agrupamento por drift — o grão é a tela (§C.1).

```text
┌────────────────────────────────────────────────────────────────────┐
│ ALLIANZ · residencial            proposta há 2 h    ✅ Simulador OK │
├────────────────────────────────────────────────────────────────────┤
│ A TELA DA URA                                                      │
│   Importante: Esse serviço de eletricista está disponível apenas   │
│   para reparos elétricos na residência                             │
│     1 - Preciso de reparo elétrico para residência                 │
│     2 - Preciso de reparos elétricos em aparelhos ou eletro...     │
│                                                                    │
│ RESPOSTA PROPOSTA        "1"      ← CONSTANTE                      │
│   por quê: em 4 de 4 sessões o humano apertou 1; a própria tela    │
│   diz que o serviço só cobre a residência; 2 opções; nenhum rótulo │
│   descreve o caso.                                                 │
│                                                                    │
│ EVIDÊNCIA                                                          │
│   8 avistamentos · 4 sessões · 28/07/2026 → 18/08/2026             │
│   respostas humanas: {"1": 4}          [ver os 8 eventos]          │
│                                                                    │
│ SIMULADOR                                                          │
│   controle (playbook atual)  → tela SEM resposta   ✓ esperado      │
│   candidato (com o passo)    → responde "1", 0 divergências  ✓     │
│                                                                    │
│              [ Aprovar ]        [ Recusar ]                        │
└────────────────────────────────────────────────────────────────────┘
```

Quando o veredito for **slot**, a linha da resposta muda e diz o que passa a
ser exigido:

```text
│ RESPOSTA PROPOSTA    {o_que_aconteceu}   ← SLOT                    │
│   por quê: os rótulos descrevem o TIPO DO DEFEITO. Tecla errada    │
│   abre chamado errado.                                             │
│   ⚠ Aprovar isto faz o atendimento passar a PEDIR "o que           │
│     aconteceu" antes de acionar a Allianz residencial.             │
```

> 💭 O texto acima é **copy ilustrativa**. Os números dentro dele, no produto,
> vêm da coluna `evidencia` — nunca são escritos à mão.

## F.3 — Os dois botões

| Botão | Efeito |
|---|---|
| **Aprovar** | `status: 'proposed' → 'active'`, grava `decidido_por`, `decidido_em`. Dispara `refresh_overlay_cache()` |
| **Recusar** | `status: 'proposed' → 'rejected'`, **exige `motivo` com ≥ 5 caracteres** |

📊 A exigência de motivo na recusa copia a convenção medida em
`/admin/aprovacoes` — a rota já a impõe. **Recusa sem motivo é informação
perdida:** a mesma tela voltará a ser proposta na rodada seguinte, e sem o
motivo ninguém sabe por que foi recusada da primeira vez.

> **Consequência do motivo:** uma tela `rejected` **não é reproposta** enquanto
> a evidência não mudar materialmente (nova resposta humana distinta, ou
> mudança do texto da tela). O índice único parcial de A.1 cobre
> `('proposed','active')` de propósito — `rejected` fica de fora para permitir
> a reproposta legítima, e o freio é lógico, no reconciliador.

## F.4 — As rotas

Vocabulário: 📊 **inglês no banco, português na UI** — é a convenção medida em
todo o produto (`approval_requests` usa `pending/approved/rejected`; os campos
do BFF são `itens`, `mensagem`, `motivo`).

```text
GET  /api/admin/atlas/propostas
POST /api/admin/atlas/propostas/{id}/decidir     body: {acao, motivo}
```

Ambas via o proxy que já existe — `app/api/admin/atlas/[...path]/route.ts`,
que usa `authenticatedProxy` e recusa sessão de tenant (403). No FastAPI,
`backend/app/api/admin_atlas.py`, com `Depends(require_master_admin)`, como
todas as outras 25 rotas do Atlas.

> ⚠️ **Decisão a registrar (nota 0-100, CLAUDE.md §14 da SPEC-078):** as rotas do
> Atlas hoje **não** passam pelo control plane e não têm chave `atlas.*` em
> `rbac.py`. **Opção A** — criar `atlas.propose`/`atlas.decide`: nota 60
> (correto a prazo, mas alarga o RBAC numa SPEC que não é de RBAC).
> **Opção B** — manter `require_master_admin` como as demais rotas do Atlas e
> usar `knowledge.curate` só no item da Caixa de Entrada: **nota 85** — é o que
> o Atlas já faz, e não cria um segundo padrão de autorização no mesmo arquivo.
> **Executar B**, registrar em `CHANGE-ADDENDA.md`, e abrir pendência para A.

## F.5 — Teste e mutação

**Arquivo:** `backend/tests/test_so_o_founder_liga_um_passo.py`
**Script:** `npm run test:so-o-founder-liga`
**Front:** `npm run test:rotas-montam` + `next start` + requisição real
(CLAUDE.md §9.1 — esta SPEC mexe em `app/`).

| # | Asserção |
|---|---|
| 1 | proposta `proposed` **não** aparece em `refresh_overlay_cache()` (I2) |
| 2 | **controle**: a mesma linha em `active` **aparece** — prova que 1 mede o filtro, não a ausência da linha |
| 3 | aprovar move para `active`, grava `decidido_por` e `decidido_em` |
| 4 | recusar sem motivo → 400, e o status **continua** `proposed` |
| 5 | recusar com motivo → `rejected` + motivo gravado |
| 6 | sessão de tenant na rota → **403** |
| 7 | sem sessão → **401** |
| 8 | aprovar duas vezes (mesma proposta) é idempotente — não duplica passo |

| Mutação | Esperado |
|---|---|
| **M1** — `refresh_overlay_cache` deixa de filtrar `status` | asserção 1 **vermelha** |
| **M2** — o motivo deixa de ser exigido | asserção 4 **vermelha** |
| **M3** — a rota troca `require_master_admin` por nada | asserções 6 e 7 **vermelhas** |
| **M4 (controle)** — mudar o texto da mensagem de erro | **VERDE** |

---

# 12. BLOCO G — Reversão, freios, multi-tenant e custo

## G.1 — Reversão sem deploy

Um overlay que se mostre errado é desligado pela mesma tela:
`status: 'active' → 'reverted'`. Vale no próximo refresh de cache (≤ 15 min,
§A.4). **Nenhum deploy, nenhuma migration, nenhum código.**

📊 E há uma segunda camada, que já existe: os overlays entram **depois** dos
passos escritos à mão (§A.2, I5). Um overlay ruim pode fazer o corredor
responder uma tela que ficaria calada; **não** pode alterar uma tela que já
tem passo. O pior caso é o comportamento de antes da aprovação.

**Freio geral:** `PLAYBOOK_OVERLAYS_ENABLED` (padrão `1` — preserva o
comportamento de hoje). Em `0`, `refresh_overlay_cache` esvazia o cache e o
motor volta ao playbook de código, inteiro, na próxima rodada.

## G.2 — Os interruptores

| Env var | Padrão | O que faz |
|---|---|---|
| `ALFAIATE_PROPOSTAS_ENABLED` | **`0`** (desligado) | liga o Reconciliador e a escrita de propostas |
| `ALFAIATE_PROPOSTAS_POR_RODADA` | **`0`** (nada) | teto de propostas escritas por rodada |
| `PLAYBOOK_OVERLAYS_ENABLED` | `1` (ligado) | o motor lê overlays aprovados |
| `OVERLAY_CACHE_REFRESH_MINUTES` | `15` | frequência do refresh |

📊 O padrão `0` nos dois primeiros copia o padrão medido de
`DESTILADOR_TETO_POR_RODADA` (`attendance_distiller.py:88`), e pela mesma razão
escrita lá: **um teto que nasce fechado não gasta nada por engano.** A SPEC
entrega isto **pronto e desligado** — o que CLAUDE.md §11.1 chama de aceitável,
desde que anotado.

> ⚠️ **Não usar `_env_int` para o teto.** 📊 `_env_int` faz `max(1, ...)` e
> transformaria um freio fechado em "uma proposta por rodada" — foi exatamente o
> defeito documentado em `attendance_distiller.py:79-86`. Ler com
> `max(0, int(os.getenv(...) or 0))`.

## G.3 — O teto existe para proteger a atenção, não a carteira

📊 **O custo de API desta SPEC é ZERO.** Cada peça:

| Peça | Chama LLM? | Evidência |
|---|---|---|
| Alfaiate (`playbook_tailor.py`) | **não** | 122 linhas, `import re`, nenhum cliente de modelo. `O-ATLAS-E-PARA-QUEM-ESCREVE-O-CORREDOR.md` §5: *"não é uma IA — é uma expressão regular"* |
| Reconciliador (novo) | **não** | SQL + `opcoes_da_tela` + `match_ura_step` |
| Discernimento | **não** | cinco predicados |
| Simulador | **não** | *"Puro — roda sem WhatsApp, sem Redis, sem rede"* |
| Tela de aprovação | **não** | React + duas rotas |

Comparação, para dimensionar o que está sendo evitado — 📊 `token_usage_logs`,
últimos 30 dias, medido em 18/08/2026:

```sql
select service_type, model_name, count(*) as chamadas,
       round(avg(total_cost_usd)::numeric,5) as custo_medio_usd
  from token_usage_logs where created_at > now() - interval '30 days'
 group by 1,2 order by chamadas desc;
```

```text
chat  claude-sonnet-5   4394 chamadas   US$ 0,00285 médio
chat  claude-opus-5       46 chamadas   US$ 0,07439 médio
```

**Uma proposta desta SPEC custa US$ 0,00000.** O único consumo é Postgres.

> **Então por que existe teto?** Porque o recurso escasso não é dinheiro — é o
> Founder. 📊 O acervo tem até 301 impressões digitais de menu só na Allianz
> (§0.3). Um reconciliador sem teto abriria centenas de cartões e a fila
> **deixaria de ser lida** — o que reproduz, com mais passos, o silêncio atual.
>
> **O teto é o produto, não a economia.** Recomendação de partida: `3`, e as
> propostas ordenadas por `vezes × sessoes` decrescente — a tela que mais
> aparece é a que mais custa não ter.

## G.4 — Multi-tenant: um overlay aprovado vale para todas

**Sim, e o desenho é deliberado.**

📊 `playbook_overlays` **não tem `company_id`** — nem `ura_maps`, nem
`route_drift`. Os corredores também não: `corridor_playbooks.py` é código,
igual para todas as corretoras.

A justificativa é o teste do `O-ATLAS-E-UM-SO-E-E-DE-TODAS.md` §5:

```text
Este dado descreve a SEGURADORA?             → é do Atlas, é global, agregue.
Este dado descreve a CORRETORA ou quem atende? → NÃO entra. Vem da configuração.
```

*"O menu da Porto é o mesmo para a Resulta, para a AutoFleet e para a corretora
que entrar em dezembro."* A âncora que reconhece a tela e as opções que ela
oferece descrevem a **seguradora**. São globais, e devem ser.

**E é o Bloco D que torna a globalidade segura.** Repare na engrenagem:

```text
escolha que pertence ao CASO      → SLOT → preenchido por corretora, por caso
escolha que pertence à SEGURADORA → constante global, e é fato dela
escolha que pertence à CORRETORA  → constante... e AQUI mora o risco
```

**INFERÊNCIA, declarada como tal:** hoje as três corretoras vivas
(Amandus, Resulta, AutoFleet) acionam para o mesmo tipo de cliente, e a política
*"acionamos para a casa do segurado"* vale para as três. **Não há evidência de
que valha para uma corretora futura.**

**Mitigação, e ela é concreta:**

1. G4 (`_VOCABULARIO_DO_CASO`) empurra para slot tudo que descreve o caso —
   que é a maior parte do risco.
2. G2 (≥ 3 sessões) exige que a política tenha sido exercida de fato.
3. A tela de aprovação mostra **de qual corretora veio cada sessão da
   evidência**. Constante proposta a partir de uma corretora só é declarada como
   tal no cartão, e o Founder decide sabendo disso.
4. Se depois se descobrir que uma constante era política de uma corretora, o
   conserto é **rebaixá-la a slot** — reversível em minutos por G.1.

**O que esta SPEC NÃO faz:** overlay por corretora. Não há coluna, não há caso
de uso medido, e criá-la agora quebraria a doutrina do Atlas por uma hipótese.
**Vai para `PENDENCIAS.md` com o gatilho nomeado** (§14, P-217).

## G.5 — Teste

**Arquivo:** `backend/tests/test_o_overlay_desliga_sem_deploy.py`
**Script:** `npm run test:overlay-reversivel`

| # | Asserção |
|---|---|
| 1 | `reverted` some do cache no refresh seguinte |
| 2 | **controle**: `active` continua no cache — prova que 1 mede o status |
| 3 | `PLAYBOOK_OVERLAYS_ENABLED=0` esvazia o cache |
| 4 | teto `0` → nenhuma proposta escrita, e o log diz por quê |
| 5 | teto `3` com 10 candidatas → exatamente 3, as de maior `vezes × sessoes` |
| 6 | `ALFAIATE_PROPOSTAS_POR_RODADA` não passa por `_env_int` (teto fechado continua fechado) |
| 7 | a tabela não tem `company_id` e nenhuma consulta desta SPEC filtra por corretora |

| Mutação | Esperado |
|---|---|
| **M1** — `reverted` deixa de ser filtrado | asserção 1 **vermelha** |
| **M2** — o teto passa por `_env_int` | asserção 6 **vermelha** |
| **M3** — ordenação por `created_at` em vez de `vezes × sessoes` | asserção 5 **vermelha** |

---

# 13. O teste de aceitação — a única prova que importa

Tudo acima é meio. **Isto é o fim.** A SPEC só fica verde quando esta sequência
inteira funcionar, com saída real registrada:

```text
 1. Restaurar o playbook residencial da Allianz ao estado de 04/08/2026
    (SEM os três passos acrescentados à mão em 8aa15be) — numa cópia de teste,
    nunca no arquivo de produção.
 2. Rodar o Reconciliador contra o acervo real da Allianz.
 3. A tela do eletricista aparece como órfã, com 8 avistamentos e 4 sessões.
 4. O Discernimento a classifica CONSTANTE "1", com o porquê escrito.
 5. A tela seguinte ("O que aconteceu?") é classificada SLOT.
       ↑ os passos 4 e 5 juntos são a prova do Bloco D. Um só não prova nada.
 6. O Simulador roda as duas rodadas: controle mostra `unanswered`; candidato
    responde "1" sem divergir.
 7. As duas propostas aparecem em /admin/atlas → Propostas, e na Caixa de Entrada.
 8. RECUSAR a primeira sem motivo → 400, continua `proposed`.
 9. APROVAR a primeira → `active`; em até 15 min o corredor responde "1"
    àquela tela, provado por um acionamento simulado ponta a ponta.
10. A aprovação do SLOT faz o atendimento passar a exigir `o_que_aconteceu`
    antes de acionar.
11. REVERTER a primeira → o corredor volta a não responder aquela tela.
```

**O passo 11 é tão obrigatório quanto o 9.** Um sistema que só sabe ligar não
está pronto.

**E a linha de controle da SPEC inteira:** com
`ALFAIATE_PROPOSTAS_ENABLED=0`, repetir os passos 2-3 e verificar que
**nenhuma linha** é escrita em `playbook_overlays`. É o par que prova que o
interruptor é interruptor, e não decoração.

---

# 14. O que fica em `PENDENCIAS.md`

Próximo ID livre: 📊 **P-215** (o último em uso é P-214).

| ID | Título | Dono | O que destrava |
|---|---|---|---|
| **P-215** | O `route_drift` continua com grão de diff, e 4 drifts `escalated` nunca foram lidos | 🤖 execução | decidir se `route_drift` vira histórico e a fila vira só `playbook_overlays`; hoje o Founder tem 4 avisos abertos que ninguém pode acionar |
| **P-216** | `_alert_founder` manda WhatsApp pelo canal de uma corretora qualquer | 🤖 execução | contradiz `O-ATLAS…CORREDOR.md` §6. Esta SPEC leva o aviso à Caixa de Entrada mas **não remove** o WhatsApp — remover é mudança de comportamento fora do texto |
| **P-217** | Não existe overlay por corretora | 🧑 Founder | gatilho nomeado: a primeira vez que uma constante aprovada se mostrar política de UMA corretora. Antes disso, criar a coluna quebra a doutrina do Atlas por hipótese |
| **P-218** | As rotas do Atlas não passam pelo control plane (sem chave `atlas.*` no `rbac.py`) | 🤖 execução | decisão F.4, opção A. Custa: auditoria e step-up não alcançam as decisões do Atlas |
| **P-219** | `ALFAIATE_PROPOSTAS_ENABLED` e o teto nascem em `0` | 🧑 Founder | ligar exige o Founder escolher o teto. Custa esquecer: a SPEC inteira fica inerte, exatamente como o Alfaiate ficou desde 14/07/2026 |
| **P-220** | O cache de overlay é por processo | 🤖 execução | com N réplicas, a janela real de propagação é o `OVERLAY_CACHE_REFRESH_MINUTES`, não o clique. Destrava com cache compartilhado (Redis) ou invalidação por evento |
| **P-221** | `classify_severity` tem uma linha morta (`route_sentinel.py:134`) | 🤖 execução | `return "cosmetic" if (added or ...) else "cosmetic"` — os dois braços iguais. Não é defeito de comportamento; é defeito de leitura |

---

# 15. O que NÃO entra nesta SPEC

| | Por quê |
|---|---|
| **Aplicar passo automaticamente**, em qualquer classe | I1. É a proibição que organiza o documento inteiro |
| **Reescrever o corredor do eletricista** | já foi feito à mão em `8aa15be`. Esta SPEC generaliza, não repete |
| **Overlay por corretora** | P-217, com gatilho nomeado |
| **Remover o alerta por WhatsApp** | P-216 — mudança de comportamento fora do texto pedido |
| **Mudar `classify_severity`** | a classificação está certa. O que estava errado era o destino |
| **Promover ou despromover mapas** | é assunto da SPEC-063 e da decisão D-b do §2.2 |
| **Criar `atlas.*` no RBAC** | P-218, opção A, nota 60 |
| **Apagar `route_drift`** | P-215. Não se apaga tabela viva numa SPEC de funcionalidade |

---

# 16. Gates

| Bloco | Gate |
|---|---|
| **A** | migration com VERIFY de saída real; `get_playbook` renderiza as 3 formas; M1-M5 com os vermelhos previstos |
| **B** | a âncora da máquina casa a tela real **e a versão antiga não casa**; ref resolvido por `resolve_playbook_ref` |
| **C** | detecta a tela do eletricista contra o playbook antigo **e não a detecta contra o atual** |
| **D** | os 7 casos, incluindo o controle (asserção 7); M4 (inverter o default) deixa 5 casos vermelhos |
| **E** | as duas rodadas gravadas; proposta descartada quando a rodada A já está limpa |
| **F** | `proposed` invisível ao motor **e** `active` visível, no mesmo teste; 401/403; `test:rotas-montam` + `next start` respondendo |
| **G** | reversão sem deploy; teto fechado não escreve nada |
| **FINAL** | os 11 passos do §13, com saída real, **incluindo o 11 e a linha de controle** |

**Gate de infraestrutura** (CLAUDE.md §8): APPLY / VERIFY / ROLLBACK escritos
**antes** de rodar — estão em §A.1. `apply_migration` via MCP 📊 não é
transacional: cada statement é idempotente por si.

**Gate de aplicação** (CLAUDE.md §9.1): esta SPEC mexe em `app/`. Build verde
não é prova de que a aplicação sobe. `npm run test:rotas-montam` +
`next start` + uma requisição a `/api/admin/atlas/propostas` que **executa
código**, nunca um arquivo estático.

**Gate de decisão** (§2.2): D-a e D-b registradas em `FOUNDER-DECISIONS.md`
**antes** do Bloco C.

**Relatório final:** template canônico
(`docs/canon/reports/SPEC-EXECUTION-REPORT-TEMPLATE.md`), com commit inicial e
final, migration com saída real, canário Amandus → Resulta → AutoFleet, riscos
remanescentes, e a declaração de que nenhum motor paralelo foi criado.

---

# 17. Ordem de execução

```text
§2.2  DECISÃO D-a / D-b        ← trava tudo. Não começar o Bloco C sem ela.

A  O overlay responde      ─┐  A é pré-requisito de TODOS: sem vocabulário de
                            │  resposta, aprovar não faz nada (C4).
B  Os curtos-circuitos     ─┤  independente de C/D/E, pode ir em paralelo com A
                            │
C  O Detector              ─┤  depende de B.1 (âncora) e B.2 (ref)
D  O Discernimento         ─┤  depende de C (precisa das respostas humanas)
E  O Portão                ─┘  depende de A (o overlay candidato precisa existir)

F  A Decisão                   depende de A, C, D, E — é a vitrine dos quatro
G  Reversão e freios           depende de A e F
```

**A dependência que não pode ser invertida:** **A antes de F.** Entregar a tela
de aprovação antes de o motor saber ler uma resposta produziria o pior
resultado possível — um Founder clicando "Aprovar" em passos que nunca
responderiam nada, e concluindo que o sistema mente.

---

# 18. Separação FATO · INFERÊNCIA · RECOMENDAÇÃO

**FATO** (medido em 18/08/2026, projeto `dcajcvlzcjbmyapmklil`, commit `0b676f2`):

- `playbook_overlays` = 0 linhas; 8 colunas; sem coluna de resposta; RLS sem policy.
- `route_drift` = 4 linhas, 4 `structural`, 4 `escalated`, 0 `cosmetic`.
- `ura_maps` = 10 `active` em 10 seguradoras; 280 `superseded`; 19 `retired`.
- A tela do eletricista: 8 avistamentos, 4 sessões, 1 corretora, 28/07 → 18/08.
- O Alfaiate não chama LLM; o Simulador não usa rede.
- `anchor_from_text` não casa `_norm` — provado por execução.
- Escritor e leitor de overlay usam namespaces de `playbook_ref` diferentes.
- `get_playbook` força `noop=True` e `reply=""` no código.
- `O-ATLAS-E-PARA-QUEM-ESCREVE-O-CORREDOR.md` §5 descreve um estado que não existe mais.

**INFERÊNCIA** (raciocínio, não medição):

- Os quatro curtos-circuitos são independentes; consertar um só não produziria
  efeito observável. Isto é dedução a partir do código, não experimento — e o
  experimento que a confirma é o §13.
- A globalidade dos overlays é segura *porque* o Bloco D empurra para slot tudo
  que pertence ao caso. Se G4 estiver incompleto, a premissa enfraquece.
- 💭 O teto de partida `3` é hipótese sobre a atenção do Founder, não medição.

**RECOMENDAÇÃO:**

- Executar §2.2 antes de tudo. Um canônico vencido não se contorna; corrige-se.
- Ligar `ALFAIATE_PROPOSTAS_ENABLED` **só depois** do §13 completo, e numa
  seguradora só (Allianz), com teto `3`, por uma semana, antes de alargar.
- Não remover `route_drift` nesta SPEC. Ele passa a ser histórico de mudança;
  a fila de trabalho passa a ser `playbook_overlays`. Consolidar depois (P-215).
