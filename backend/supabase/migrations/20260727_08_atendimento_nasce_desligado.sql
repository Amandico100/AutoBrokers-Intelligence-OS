-- O agente de atendimento nasce DESLIGADO. Garantia no banco.
--
-- POR QUE
-- =======
-- `agents.is_active` tem default `true`. O blueprint do atendimento diz
-- `default_active: false` e o provisionamento respeita — mas isso depende de o
-- código passar pelo blueprint. Qualquer outro caminho (tela do Admin, script,
-- insert direto) criaria um agente de atendimento LIGADO, e o número da
-- corretora começaria a responder segurados sem ninguém ter clicado no botão.
--
-- Até 27/07/2026 havia uma rede: o pareamento executava
-- `agents.update({is_active: false})`. Ela foi removida porque tinha um efeito
-- colateral pior — **re-parear desligava um agente que estava trabalhando**, e
-- re-parear não é raro (telefone desligado, logout, QR vencido, troca de
-- aparelho). A corretora reconectava e o agente ficava mudo sem aviso.
--
-- A garantia certa é esta: nasce desligado, no banco, qualquer que seja o
-- caminho. Ligar continua sendo exclusividade do botão no dashboard, que faz
-- UPDATE — e o gatilho não toca em UPDATE.
--
-- Decisão do Founder, 27/07/2026:
--   "O AGENTE DE ATENDIMENTO NASCE DESLIGADO. ELE SÓ É LIGADO SE CLICAR NO
--    BOTÃO DEPOIS DE PAREADO."
--
-- APPLY   : este arquivo, idempotente
-- VERIFY  : bloco ao final (roda em transação que aborta — nada persiste)
-- ROLLBACK: rodapé, por nome exato

create or replace function public.tg_atendimento_nasce_desligado()
returns trigger language plpgsql as $fn$
begin
  -- Só o papel 'attendance'. O 'core' (o chat interno do corretor) precisa
  -- nascer ligado — desligá-lo entregaria uma corretora sem assistente.
  if lower(coalesce(new.agent_role, '')) = 'attendance'
     and coalesce(new.is_active, true) is true then
    new.is_active := false;
  end if;
  return new;
end $fn$;

drop trigger if exists atendimento_nasce_desligado on public.agents;
create trigger atendimento_nasce_desligado
  before insert on public.agents
  for each row execute function public.tg_atendimento_nasce_desligado();

-- ---------------------------------------------------------------------------
-- VERIFY — prova real, e aborta de propósito para não deixar lixo
-- ---------------------------------------------------------------------------
-- Executado em 27/07/2026 contra produção. Resultado:
--   gatilho instalado ...........: 1
--   atendimento criado com true ->: false
--   core criado com true ........->: true
--   lixo deixado ................: 0
--
-- do $$
-- declare v_ativo boolean; v_core boolean; v_empresa uuid; v_trg int;
-- begin
--   select count(*) into v_trg from pg_trigger
--    where tgname='atendimento_nasce_desligado' and not tgisinternal;
--   select id into v_empresa from companies where is_technical = true limit 1;
--   insert into agents (company_id, name, slug, agent_role, is_active)
--   values (v_empresa,'PROVA atendimento','prova-nasce-desligado','attendance',true)
--   returning is_active into v_ativo;
--   insert into agents (company_id, name, slug, agent_role, is_active)
--   values (v_empresa,'PROVA core','prova-core-ligado','core',true)
--   returning is_active into v_core;
--   if v_trg = 1 and v_ativo is false and v_core is true then
--     raise exception 'VERIFY OK -- abortando de proposito, nada persiste';
--   end if;
--   raise exception 'VERIFY FALHOU: trg=% atendimento=% core=%', v_trg, v_ativo, v_core;
-- end $$;

-- ---------------------------------------------------------------------------
-- ROLLBACK (não executar sem decisão registrada)
-- ---------------------------------------------------------------------------
--   drop trigger if exists atendimento_nasce_desligado on public.agents;
--   drop function if exists public.tg_atendimento_nasce_desligado();
