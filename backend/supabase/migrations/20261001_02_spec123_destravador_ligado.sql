-- MIGRATION: 20261001_02_spec123_destravador_ligado
-- SPEC:      SPEC-123 (D5 do Founder: "ligado de verdade por seguradora/ramo, sem período de sombra")
-- AUTOR:     gerente da SPEC-123 (Opus 5.5), 01/10/2026
-- OBJETIVO:  ligar o destravador (`cerebro_modos.modo='on'`, limiar 70 = D2) para TODA corretora que tem agente de
--            atendimento, nas 10 seguradoras que têm corredor, ramo 'todos'. As corretoras vêm do BANCO (agents.agent_role
--            = 'attendance'), nunca por id ou nome no código (CLAUDE.md §13.9).
--
-- 📊 POR QUE É SEGURO LIGAR AGORA (01/10/2026):
--   · a bancada real (`docs/canon/reports/SPEC-123-BANCADA.md`): 0 erro grave no produto depois do conserto; o DEDUZIR
--     autônomo fica DESLIGADO em código (`destravador.DEDUZIR_AUTONOMO_CALIBRADO=False`, 6/14 de acerto com nota ≥ 70);
--     o que o `on` faz é CONDUZIR, RESPONDER COM DADO DO CASO, PERGUNTAR AO SEGURADO e NUNCA SOZINHO → pessoa;
--   · juiz + red team + confirmação: os 10 blockers fechados (`LAUDO-CONFIRMACAO-123`, nota 86);
--   · `select count(*) filter (where is_active) from agents where agent_role='attendance'` → 0 de 4: nada acontece até o
--     Founder ligar o agente de atendimento de uma corretora (e as travas de acionamento real continuam com ele).
--
-- APPLY:     o INSERT abaixo (idempotente: `on conflict` atualiza só o modo/limiar/motivo).
-- VERIFY:    select count(*) from cerebro_modos where modo='on' and ramo='todos' and limiar=70
--              → = 10 × (corretoras com agente de atendimento) [📊 01/10: 10 × 4 = 40]
--            select count(*) from cerebro_modos where modo <> 'on'  → 0
-- ROLLBACK:  delete from public.cerebro_modos where ligado_por = 'migration 20261001_02_spec123_destravador_ligado';
--            (sem linha = 'off' = o comportamento de antes, byte a byte — teste `test_spec123_ligacao_do_destravador`)
-- DESLIGAR UMA SEGURADORA (Founder): update public.cerebro_modos set modo='off' where insurer_key='<seguradora>';
-- EXPAND-FIRST: só linhas novas; nenhuma estrutura muda. DESTRUTIVA: não.

insert into public.cerebro_modos (company_id, insurer_key, ramo, modo, limiar, motivo, ligado_por)
select distinct a.company_id, s.insurer_key, 'todos', 'on', 70,
       'SPEC-123 D5: destravador ligado (DEDUZIR autônomo desligado em código até calibrar)',
       'migration 20261001_02_spec123_destravador_ligado'
from public.agents a
cross join (values ('allianz'),('alfa'),('azul'),('bradesco'),('hdi'),('mapfre'),('porto'),('tokio'),('yelum'),('zurich'))
     as s(insurer_key)
where a.agent_role = 'attendance' and a.company_id is not null
on conflict (company_id, insurer_key, ramo) do update
   set modo = excluded.modo, limiar = excluded.limiar, motivo = excluded.motivo,
       ligado_por = excluded.ligado_por, updated_at = now();
