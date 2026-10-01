-- =============================================================
-- MIGRATION: 20260930_04_spec123_diario_de_decisoes
-- SPEC:      SPEC-123 — F4 · o diário de decisões
-- AUTOR:     builder F4 (Opus 5.5 xhigh)      DATA: 2026-09-30
-- OBJETIVO:  uma linha por decisão que o agente tomou SOZINHO (destravou uma
--            trava), legível por gente, com "certo/errado" que realimenta a
--            bancada e, quando é regra, um rascunho de carta.
--
-- APPLY:     cria `public.diario_de_decisoes` (vazia), 5 índices, RLS ligada
--            com ZERO policy e revoke de anon/authenticated.
-- VERIFY:    o bloco VERIFY no fim deste arquivo (SQL executável). O V2 é
--            ADVERSARIAL e roda num DO que termina em `raise exception` — a
--            transação inteira é desfeita por construção, e a mensagem do erro
--            é o placar.
-- ROLLBACK:  o bloco ROLLBACK no fim deste arquivo (a tabela nasce vazia; o
--            rollback recusa rodar se já houver linha).
--
-- EXPAND-FIRST: sim  (só adiciona; nenhuma tabela existente muda)
-- DESTRUTIVA:   não
-- =============================================================
--
-- 🔴 POR QUE TABELA PRÓPRIA, E NÃO `work_events`:
--    `work_events` é append-only (trigger) — o veredito "certo/errado", o
--    "o certo era…", o resultado e o carimbo de "virou caso" são ATUALIZAÇÕES
--    da mesma decisão. Em `work_events` fica só um evento CURTO
--    (`cerebro.decisao`) com o `diario_id`, para a linha do tempo do acionamento.
--
-- 🔴 POR CORRETORA (CLAUDE.md §7): `company_id` NOT NULL, FK composta com o
--    acionamento e com a conversa (uma decisão não aponta para o acionamento de
--    OUTRA corretora — o banco recusa), RLS ligada sem policy, e o filtro por
--    `company_id` no CÓDIGO em toda leitura/escrita
--    (`backend/app/services/diario_de_decisoes.py`,
--    `app/api/dashboard/decisoes/route.ts`).
--
-- ⚠️ `veredito_por` SEM FK: é o `users_v2.id` de quem avaliou, e o precedente da
--    casa (`normative_documents.approved_by`, MANIFEST) é não pendurar o dado
--    numa linha de usuário — apagar a pessoa não pode apagar (CASCADE) nem
--    travar (RESTRICT) o aprendizado.
--
-- ⚠️ `tela_mascarada` / `valor_mascarado`: o texto passa por
--    `acao_do_cerebro.higienizar_para_o_rastro` ANTES de chegar aqui. O nome da
--    coluna diz o que ela guarda (CLAUDE.md §12.1).

create table if not exists public.diario_de_decisoes (
  id                     uuid        primary key default gen_random_uuid(),
  company_id             uuid        not null references public.companies(id) on delete cascade,
  work_run_id            uuid,
  conversation_id        uuid,
  chave_idempotencia     text        not null,
  origem                 text        not null,
  seguradora             text        not null default '',
  ramo                   text        not null default '',
  rota                   text        not null default '',
  servico                text        not null default '',
  gatilho                text        not null default '',
  tela_hash              text        not null default '',
  tela_mascarada         text        not null default '',
  classe                 text        not null,
  acao                   text        not null,
  valor_mascarado        text        not null default '',
  nota                   smallint,
  limiar                 smallint,
  motivo                 text        not null default '',
  explicacao_para_gente  text        not null,
  modelo                 text        not null default '',
  segunda_opiniao        jsonb,
  modo                   text        not null,
  resultado              text        not null default 'pendente',
  resultado_em           timestamptz,
  veredito               text,
  o_certo_era            text,
  sugere_regra           boolean     not null default false,
  veredito_por           uuid,
  veredito_em            timestamptz,
  virou_caso_em          timestamptz,
  caso_chave             text,
  carta_rascunho_id      uuid,
  created_at             timestamptz not null default now(),

  constraint uq_diario_idempotencia unique (company_id, chave_idempotencia),

  -- 🔴 a decisão aponta para o acionamento/conversa DA MESMA corretora.
  --    `ON DELETE SET NULL (col)` (Postgres 15+; 📊 o banco é 17.6): apagar o
  --    acionamento não apaga o aprendizado, e não tenta anular `company_id`.
  constraint fk_diario_run_mesma_corretora
    foreign key (work_run_id, company_id) references public.work_runs(id, company_id)
    on delete set null (work_run_id),
  constraint fk_diario_conversa_mesma_corretora
    foreign key (conversation_id, company_id) references public.conversations(id, company_id)
    on delete set null (conversation_id),
  constraint fk_diario_carta_rascunho
    foreign key (carta_rascunho_id) references public.knowledge_cards(id) on delete set null,

  constraint ck_diario_origem   check (origem in ('acionamento', 'atendimento', 'portal')),
  constraint ck_diario_classe   check (classe in ('conduzir', 'responder_com_dado', 'deduzir',
                                                  'perguntar_ao_segurado', 'nunca_sozinho')),
  constraint ck_diario_acao     check (acao in ('respondeu_ura', 'perguntou_segurado',
                                                'chamou_pessoa', 'nao_agiu')),
  constraint ck_diario_nota     check (nota is null or nota between 0 and 100),
  -- D2 do Founder: o limiar nunca fica abaixo de 70 (o mesmo CHECK de `cerebro_modos.limiar`).
  constraint ck_diario_limiar   check (limiar is null or limiar between 70 and 100),
  constraint ck_diario_modo     check (modo in ('on', 'sombra')),
  -- em sombra o agente NÃO age: a linha que diz "sombra" e "respondeu" mente.
  constraint ck_diario_sombra_nao_agiu check (modo <> 'sombra' or acao = 'nao_agiu'),
  constraint ck_diario_resultado check (resultado in ('pendente', 'protocolo_saiu', 'seguradora_recusou',
                                                      'humano_corrigiu', 'ura_fechou')),
  constraint ck_diario_resultado_em check ((resultado = 'pendente') = (resultado_em is null)),
  constraint ck_diario_veredito check (veredito is null or veredito in ('certo', 'errado')),
  constraint ck_diario_veredito_em check ((veredito is null) = (veredito_em is null)),
  -- "errado" sem dizer o que era o certo não ensina nada (D7).
  constraint ck_diario_errado_tem_o_certo
    check (veredito is distinct from 'errado' or length(btrim(coalesce(o_certo_era, ''))) >= 3),
  constraint ck_diario_explicacao check (length(btrim(explicacao_para_gente)) >= 10),
  constraint ck_diario_caso_coerente check ((virou_caso_em is null) = (caso_chave is null)),
  -- só "errado" vira caso de bancada.
  constraint ck_diario_caso_so_de_errado check (virou_caso_em is null or veredito = 'errado'),
  constraint ck_diario_chave check (length(chave_idempotencia) between 8 and 200)
);

comment on table public.diario_de_decisoes is
  'SPEC-123 F4 — o diário de decisões: uma linha por decisão autônoma do agente (destravador), por corretora, em português de gente (explicacao_para_gente), com veredito certo/errado da corretora. "errado" vira caso pendente de bancada (virou_caso_em/caso_chave) e, se for regra, rascunho de carta com status proposta_diario (carta_rascunho_id) — nunca publicado sozinho. Escritor: backend/app/services/diario_de_decisoes.py.';
comment on column public.diario_de_decisoes.tela_mascarada is
  'O texto da tela da seguradora JÁ MASCARADO por acao_do_cerebro.higienizar_para_o_rastro (nunca o cru).';
comment on column public.diario_de_decisoes.explicacao_para_gente is
  'A frase que a corretora lê (D7): o que a seguradora perguntou, o que o agente fez, por quê, com que certeza. Sem jargão, sem nome de variável.';
comment on column public.diario_de_decisoes.veredito_por is
  'users_v2.id de quem avaliou. Sem FK de propósito (precedente normative_documents.approved_by).';

-- -------------------------------------------------------------
-- ÍNDICES
-- -------------------------------------------------------------
-- a lista da tela: por corretora, mais novas primeiro, cursor (created_at, id)
create index if not exists ix_diario_company_criado
  on public.diario_de_decisoes (company_id, created_at desc, id desc);
-- "sem avaliação" — o filtro padrão da tela
create index if not exists ix_diario_company_sem_veredito
  on public.diario_de_decisoes (company_id, created_at desc)
  where veredito is null;
-- cobre a FK composta e o `marcar_resultado` (por acionamento)
create index if not exists ix_diario_run_fk
  on public.diario_de_decisoes (work_run_id, company_id)
  where work_run_id is not null;
-- cobre a FK composta da conversa (lição da SPEC-098: índice que começa por
-- company_id não cobre FK procurada por conversation_id)
create index if not exists ix_diario_conversa_fk
  on public.diario_de_decisoes (conversation_id, company_id)
  where conversation_id is not null;
-- a fila do `diario_para_bancada.py`: errados que ainda não viraram caso
create index if not exists ix_diario_errado_sem_caso
  on public.diario_de_decisoes (company_id, created_at)
  where veredito = 'errado' and virou_caso_em is null;
-- cobre a FK da carta
create index if not exists ix_diario_carta_fk
  on public.diario_de_decisoes (carta_rascunho_id)
  where carta_rascunho_id is not null;

-- -------------------------------------------------------------
-- RLS — LIGADA, sem policy (nega anon/authenticated; service role passa).
-- ⚠️ CLAUDE.md §7: isto é a REDE. O filtro real é o `company_id` no código.
-- -------------------------------------------------------------
alter table public.diario_de_decisoes enable row level security;
revoke all on table public.diario_de_decisoes from anon, authenticated;

-- =============================================================
-- VERIFY  (rodar DEPOIS do APPLY)
-- =============================================================
-- V1) a tabela existe, com RLS ligada, zero policy, sem grant para anon/authenticated,
--     os 16 CHECKs, as 3 FKs e os 6 índices:
--
-- select c.relrowsecurity rls,
--        (select count(*) from pg_policies p where p.schemaname='public' and p.tablename='diario_de_decisoes') policies,
--        (select count(*) from information_schema.role_table_grants g
--          where g.table_schema='public' and g.table_name='diario_de_decisoes'
--            and g.grantee in ('anon','authenticated')) grants_publicos,
--        (select count(*) from pg_constraint k where k.conrelid=c.oid and k.contype='c') checks,
--        (select count(*) from pg_constraint k where k.conrelid=c.oid and k.contype='f') fks,
--        (select count(*) from pg_indexes i where i.schemaname='public' and i.tablename='diario_de_decisoes') indices,
--        (select count(*) from public.diario_de_decisoes) linhas
--   from pg_class c where c.oid = 'public.diario_de_decisoes'::regclass;
--   → rls=t · policies=0 · grants_publicos=0 · checks=16 · fks=4 (companies + run + conversa + carta) ·
--     indices=8 (pk + unique + 6) · linhas=0
--
-- V2) ADVERSARIAL — cada CHECK/FK CONSEGUE recusar, e a linha completa é ACEITA
--     (controle). Termina em `raise exception`: NADA fica gravado.
--
-- do $$
-- declare
--   a uuid; b uuid; run_a uuid; placar text := '';
--   cols text := 'company_id, chave_idempotencia, origem, classe, acao, explicacao_para_gente, modo';
--   casos text[][] := array[
--     array['origem',        $v$'verify-origem-01','chute','deduzir','respondeu_ura','Explicacao de teste longa.','on'$v$, '23514'],
--     array['classe',        $v$'verify-classe-01','acionamento','chutar','respondeu_ura','Explicacao de teste longa.','on'$v$, '23514'],
--     array['acao',          $v$'verify-acao-0001','acionamento','deduzir','cantou','Explicacao de teste longa.','on'$v$, '23514'],
--     array['modo_off',      $v$'verify-modo-0001','acionamento','deduzir','respondeu_ura','Explicacao de teste longa.','off'$v$, '23514'],
--     array['sombra_agiu',   $v$'verify-sombra-01','acionamento','deduzir','respondeu_ura','Explicacao de teste longa.','sombra'$v$, '23514'],
--     array['explicacao',    $v$'verify-explic-01','acionamento','deduzir','respondeu_ura','curta','on'$v$, '23514'],
--     array['chave_curta',   $v$'curta','acionamento','deduzir','respondeu_ura','Explicacao de teste longa.','on'$v$, '23514'],
--     array['duplicata',     $v$'verify-controle-0001','acionamento','deduzir','respondeu_ura','Explicacao de teste longa.','on'$v$, '23505']
--   ];
--   extras text[][] := array[
--     array['nota_101',        'nota',                                 '101',                               '23514'],
--     array['limiar_69',       'limiar',                               '69',                                '23514'],
--     array['resultado',       'resultado, resultado_em',              $v$'chute', now()$v$,                '23514'],
--     array['resultado_em',    'resultado',                            $v$'protocolo_saiu'$v$,              '23514'],
--     array['veredito',        'veredito, veredito_em',                $v$'talvez', now()$v$,               '23514'],
--     array['veredito_em',     'veredito',                             $v$'certo'$v$,                       '23514'],
--     array['errado_sem_certo','veredito, veredito_em, o_certo_era',   $v$'errado', now(), ' x '$v$,        '23514'],
--     array['caso_de_certo',   'veredito, veredito_em, virou_caso_em, caso_chave', $v$'certo', now(), now(), 'k'$v$, '23514'],
--     array['caso_sem_chave',  'veredito, veredito_em, o_certo_era, virou_caso_em', $v$'errado', now(), 'era o 2', now()$v$, '23514']
--   ];
--   i int; sqlst text; cn text;
-- begin
--   select id into a from public.companies order by id limit 1;
--   select id into b from public.companies where id <> a order by id limit 1;
--   select id into run_a from public.work_runs where company_id = a order by created_at desc limit 1;
--
--   execute format('insert into public.diario_de_decisoes (%s, nota, limiar) values (%L, %s, 88, 70)',
--                  cols, a, $v$'verify-controle-0001','acionamento','deduzir','respondeu_ura','A seguradora perguntou algo e o agente respondeu.','on'$v$);
--   placar := placar || 'controle=aceita;';
--   if run_a is not null then
--     insert into public.diario_de_decisoes (company_id, work_run_id, chave_idempotencia, origem, classe, acao, explicacao_para_gente, modo)
--     values (a, run_a, 'verify-controle-run-A', 'acionamento', 'conduzir', 'respondeu_ura', 'Controle: o run da MESMA corretora.', 'on');
--     placar := placar || 'controle_run_mesma=aceita;';
--   end if;
--   insert into public.diario_de_decisoes (company_id, chave_idempotencia, origem, classe, acao, explicacao_para_gente, modo, veredito, veredito_em, o_certo_era, virou_caso_em, caso_chave)
--   values (a, 'verify-controle-errado', 'acionamento', 'deduzir', 'respondeu_ura', 'Controle: errado com o certo.', 'on', 'errado', now(), 'era a opcao 2', now(), 'diario-x');
--   placar := placar || 'controle_errado=aceita;';
--
--   for i in 1 .. array_length(casos, 1) loop
--     begin
--       execute format('insert into public.diario_de_decisoes (%s) values (%L, %s)', cols, a, casos[i][2]);
--       placar := placar || casos[i][1] || '=NAO_RECUSOU;';
--     exception when others then
--       sqlst := SQLSTATE; get stacked diagnostics cn = CONSTRAINT_NAME;
--       placar := placar || casos[i][1] || case when sqlst = casos[i][3] then '=ok(' || cn || ');' else '=ERRO_' || sqlst || ';' end;
--     end;
--   end loop;
--   for i in 1 .. array_length(extras, 1) loop
--     begin
--       execute format('insert into public.diario_de_decisoes (%s, %s) values (%L, %s, %s)', cols, extras[i][2], a,
--                      $v$'verify-extra-$v$ || i || $v$-xx','acionamento','deduzir','respondeu_ura','Explicacao de teste longa.','on'$v$,
--                      extras[i][3]);
--       placar := placar || extras[i][1] || '=NAO_RECUSOU;';
--     exception when others then
--       sqlst := SQLSTATE; get stacked diagnostics cn = CONSTRAINT_NAME;
--       placar := placar || extras[i][1] || case when sqlst = extras[i][4] then '=ok(' || cn || ');' else '=ERRO_' || sqlst || ';' end;
--     end;
--   end loop;
--   if run_a is not null then
--     begin
--       insert into public.diario_de_decisoes (company_id, work_run_id, chave_idempotencia, origem, classe, acao, explicacao_para_gente, modo)
--       values (b, run_a, 'verify-run-cruzado', 'acionamento', 'deduzir', 'respondeu_ura', 'Explicacao de teste longa.', 'on');
--       placar := placar || 'run_de_outra_corretora=NAO_RECUSOU;';
--     exception when foreign_key_violation then get stacked diagnostics cn = CONSTRAINT_NAME; placar := placar || 'run_de_outra_corretora=ok(' || cn || ');'; end;
--   end if;
--   raise exception 'VERIFY_PLACAR %', placar;
-- end $$;
--   → 📊 rodado em 30/09/2026 (MCP execute_sql), o erro devolvido É o placar:
--   VERIFY_PLACAR controle=aceita;controle_run_mesma=aceita;controle_errado=aceita;
--   origem=ok(ck_diario_origem);classe=ok(ck_diario_classe);acao=ok(ck_diario_acao);
--   modo_off=ok(ck_diario_modo);sombra_agiu=ok(ck_diario_sombra_nao_agiu);explicacao=ok(ck_diario_explicacao);
--   chave_curta=ok(ck_diario_chave);duplicata=ok(uq_diario_idempotencia);nota_101=ok(ck_diario_nota);
--   limiar_69=ok(ck_diario_limiar);resultado=ok(ck_diario_resultado);resultado_em=ok(ck_diario_resultado_em);
--   veredito=ok(ck_diario_veredito);veredito_em=ok(ck_diario_veredito_em);
--   errado_sem_certo=ok(ck_diario_errado_tem_o_certo);caso_de_certo=ok(ck_diario_caso_so_de_errado);
--   caso_sem_chave=ok(ck_diario_caso_coerente);run_de_outra_corretora=ok(fk_diario_run_mesma_corretora);
--   (cada recusa pela SUA constraint — o nome vem de GET STACKED DIAGNOSTICS)
--
-- V3) nada ficou: select count(*) from public.diario_de_decisoes;  → 0

-- =============================================================
-- ROLLBACK  (só se a tabela estiver VAZIA — ela guarda aprendizado da corretora)
-- =============================================================
-- do $$ begin
--   if exists (select 1 from public.diario_de_decisoes) then
--     raise exception 'ROLLBACK recusado: o diário já tem decisões gravadas';
--   end if;
-- end $$;
-- drop table if exists public.diario_de_decisoes;
