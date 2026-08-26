-- =============================================================
-- MIGRATION: spec090_blocoC_notas_da_atendente
-- SPEC:      SPEC-090 — BLOCO C (a anotação da Regina e da Saionara)
-- AUTOR:     execução Opus 5             DATA: 2026-08-26
-- OBJETIVO:  o que as duas observarem no primeiro dia do piloto **entra no
--            produto** em vez de morrer num caderno.
--
-- APPLY:     cria `notas_da_atendente`.
-- VERIFY:    o bloco VERIFY no fim deste arquivo (SQL executável).
-- ROLLBACK:  o bloco ROLLBACK no fim deste arquivo.
--
-- EXPAND-FIRST: sim  (só adiciona)
-- DESTRUTIVA:   não
-- =============================================================
--
-- 🔴 O QUE A MEDIÇÃO DERRUBOU DO DESENHO DA SPEC
--
-- A SPEC manda a Regina escrever `#nota …` **na conversa do segurado**, e diz
-- que o produto consome o prefixo: *"a mensagem é capturada, gravada e não
-- reenviada"*. O gate ② dela é *"🔴 ZERO chance de o `#nota` chegar ao
-- segurado"*.
--
-- 📊 **Medido em 26/08 — esse gate é inalcançável nesse caminho**, e a razão é
-- estrutural:
--
--     evolution_go_events.py:47   force_from_me = ev in ("sendmessage", …)
--     evolution_inbound.py:847    if from_me: return {**out, "skip": True,
--                                                     "skip_reason": "from_me"}
--
-- ⛔ **`fromMe` é o ECO de uma mensagem que o WhatsApp JÁ ENTREGOU.** Quando o
-- webhook chega, o segurado já leu. O produto não é o remetente, não está no
-- caminho, e não tem o que consumir — *"não reenviar"* é verdade e é
-- irrelevante, porque ninguém ia reenviar.
--
-- ⚠️ A SPEC trata isso como o risco *"se o prefixo escapar uma vez"*. **Não é
-- risco: é o comportamento padrão desse caminho.**
--
-- ---------------------------------------------------------------------------
-- ✅ E EXISTE UM CAMINHO ONDE O GATE ② É REAL
--
-- 📊 `POST /api/webhook/send-message` (`webhook.py:1475`) é o envio do PAINEL,
-- e ali **o produto É o remetente**: ele chama `whatsapp_service.send_message`.
-- Consumir o prefixo ali significa que a mensagem provadamente não sai — e o
-- teste consegue contar `platform_sends`, como o gate ② exige.
--
-- 🔴 **Por isso a coluna `origem` existe, e ela não é enfeite:**
--
--     painel     ⛔ NUNCA saiu. O produto interceptou antes de enviar.
--     whatsapp   ⚠️ JÁ FOI ENTREGUE quando o produto soube.
--
-- ⚠️ Sem essa coluna, as duas notas ficariam indistinguíveis, e um relatório
-- diria *"12 notas capturadas, nenhuma vazou"* sobre um dia em que sete foram
-- lidas pelo segurado. **Relatório confiante e falso é o defeito que esta SPEC
-- inteira existe para impedir.**
--
-- =============================================================
-- APPLY
-- =============================================================

CREATE TABLE IF NOT EXISTS public.notas_da_atendente (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),

  -- 🔴 §7 — toda tabela nova nasce com dono. A RLS é o fecho; o filtro no
  --    código é o que protege de verdade, porque o backend usa service role.
  company_id        uuid NOT NULL
                      REFERENCES public.companies (id) ON DELETE CASCADE,

  -- A que conversa a nota se refere. NULO é legítimo: ela pode anotar uma
  -- observação geral do dia.
  conversation_id   uuid,

  -- O acionamento, quando dá para saber. NULO é legítimo pelo mesmo motivo.
  work_run_id       uuid REFERENCES public.work_runs (id) ON DELETE SET NULL,

  -- 🔴 O TEXTO JÁ CHEGA MASCARADO. Quem mascara é `redaction_service`, o
  --    mascarador ÚNICO da casa (SPEC-087 BLOCO C). Uma nota é escrita por
  --    gente com pressa: *"o robô perguntou a placa ABC1D23 duas vezes"*.
  texto             text NOT NULL,

  -- Quem anotou. ⛔ NUNCA impresso em log, relatório ou artifact.
  autor_telefone    text,

  -- 🔴 OS VALORES DO CHECK, LISTADOS AQUI COMO O PROTOCOLO EXIGE:
  --      'painel'    ⛔ o produto interceptou — NUNCA saiu
  --      'whatsapp'  ⚠️ já entregue quando o produto soube
  origem            text NOT NULL,

  -- O que ela estava anotando, copiado do travamento mais recente quando há um.
  rota              text,
  tela              text,

  created_at        timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT ck_notas_atendente_origem
    CHECK (origem IN ('painel', 'whatsapp')),

  -- ⛔ Nota vazia não é nota. Um prefixo sozinho (`#nota` e mais nada) é
  --    engano de digitação, não observação.
  CONSTRAINT ck_notas_atendente_texto
    CHECK (length(btrim(texto)) > 0),

  -- 🔴 A MESMA FK COMPOSTA DO BLOCO A: a nota de uma corretora não pode
  --    apontar para conversa de outra. O banco recusa, com o filtro do
  --    código certo ou errado.
  CONSTRAINT fk_notas_atendente_conversa_mesma_corretora
    FOREIGN KEY (conversation_id, company_id)
    REFERENCES public.conversations (id, company_id) ON DELETE SET NULL
);

-- ⑥ *"o Claude Code consegue ler todas as notas de um dia numa query"*.
CREATE INDEX IF NOT EXISTS ix_notas_atendente_dia
  ON public.notas_da_atendente (company_id, created_at DESC);

CREATE INDEX IF NOT EXISTS ix_notas_atendente_conversa
  ON public.notas_da_atendente (company_id, conversation_id)
  WHERE conversation_id IS NOT NULL;

-- ⚠️ RLS LIGADA SEM POLICY É `deny all`, não "desprotegido" — ela FECHA a
--    tabela para quem não é service role. 🔴 O risco é o inverso, e é o que a
--    P-090-01 descreve: o backend ATRAVESSA a RLS inteira, e a única proteção
--    real é o `.eq("company_id")` no código.
ALTER TABLE public.notas_da_atendente ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE public.notas_da_atendente IS
  'SPEC-090 BLOCO C — o que a atendente humana observou durante o atendimento. '
  'origem=painel: o produto interceptou antes de enviar, a nota NUNCA saiu. '
  'origem=whatsapp: eco de mensagem que o WhatsApp JÁ havia entregue.';

-- =============================================================
-- VERIFY  (read-only, e o CONTROLE desfaz o que escreve)
-- =============================================================
--
-- V1 · a tabela existe, com RLS
--
--   select relname, relrowsecurity from pg_class where relname='notas_da_atendente';
--   -- esperado: notas_da_atendente | t
--
-- V2 · 🔴 OS VALORES DO CHECK
--
--   select conname, pg_get_constraintdef(oid) from pg_constraint
--    where conrelid='public.notas_da_atendente'::regclass and contype='c';
--   -- esperado: ck_notas_atendente_origem CHECK (origem IN ('painel','whatsapp'))
--   --           ck_notas_atendente_texto  CHECK (length(btrim(texto)) > 0)
--
-- V3 · 🔴 O CONTROLE — o banco RECUSA o que tem de recusar, E ACEITA o válido.
--      ⚠️ A transação é desfeita por `raise`: nada fica gravado.
--
--   do $$
--   declare v_a uuid; v_b uuid; v_conv_b uuid;
--           r_origem boolean := false; r_texto boolean := false;
--           r_cross  boolean := false; aceitou boolean := false;
--   begin
--     select company_id into v_b from conversations group by company_id
--      order by count(*) desc limit 1;
--     select company_id into v_a from conversations where company_id <> v_b
--      group by company_id order by count(*) desc limit 1;
--     select id into v_conv_b from conversations where company_id=v_b limit 1;
--
--     begin insert into notas_da_atendente (company_id, texto, origem)
--           values (v_a, 'teste', 'caderno');
--     exception when check_violation then r_origem := true; end;
--
--     begin insert into notas_da_atendente (company_id, texto, origem)
--           values (v_a, '   ', 'painel');
--     exception when check_violation then r_texto := true; end;
--
--     begin insert into notas_da_atendente (company_id, conversation_id, texto, origem)
--           values (v_a, v_conv_b, 'teste', 'painel');
--     exception when foreign_key_violation then r_cross := true; end;
--
--     begin insert into notas_da_atendente (company_id, texto, origem)
--           values (v_a, 'o robo perguntou duas vezes', 'painel');
--           aceitou := true;
--     exception when others then aceitou := false; end;
--
--     raise exception 'V3 || origem invalida RECUSADA? % || texto vazio RECUSADO? % '
--                     '|| cross-tenant RECUSADO? % || nota valida ACEITA? %',
--       r_origem, r_texto, r_cross, aceitou;
--   end $$;
--   -- esperado: t | t | t | t
--
-- V4 · ⑥ todas as notas de um dia, numa query
--
--   select date_trunc('day', created_at) dia, origem, count(*),
--          count(conversation_id) com_conversa
--     from notas_da_atendente
--    where company_id = $1 and created_at >= now() - interval '2 days'
--    group by 1, 2 order by 1 desc;
--
-- =============================================================
-- ROLLBACK
-- =============================================================
--
--   drop table if exists public.notas_da_atendente;
--
-- ⚠️ Apaga as notas. Não há de onde reconstruir: a mensagem original vive no
-- WhatsApp da atendente, e o Espelho guarda o texto, não a classificação.
