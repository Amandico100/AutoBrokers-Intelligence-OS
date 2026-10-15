-- =============================================================
-- MIGRATION: 20261016_02_spec139_a_duvida_da_cobranca
-- SPEC:      SPEC-139 — conserto A (o juiz B1: a Dúvida FALSA da Cobrança)
-- AUTOR:     builder do conserto A (claude-opus-5-5)        DATA: 2026-10-15
-- OBJETIVO:  as Dúvidas (`auxiliary_templates.faq`) que prometem o que o produto NÃO faz — só CONTEÚDO do catálogo
--            GLOBAL: nenhuma coluna, nenhuma trava, nenhum `catalog_state`, nada de corretora, nenhum envio.
--
-- 📊 ANTES (15/10/2026, psycopg `SET TRANSACTION READ ONLY`, scratchpad cA_banco.py — só SELECT):
--    cobranca-feita  md5(faq::text) = 86c0fae8a72c258c01246c04278bd8e7
--      · "O boleto sai sozinho para o cliente?" → "Sim, quando o aplicativo está ligado…" — FALSO em 3 dos 4 modos:
--        o modo padrão do modelo é `test` (só o número de teste), `none` não envia, `equipe` manda à atendente; só
--        `cliente` COM a confirmação chega ao segurado (`MODOS_COM_MOTOR`, formulario.ts; `billing_collection.py`).
--      · "De quais seguradoras…?" → "Hoje, da Allianz." — capacidade cravada em texto global, com o nome de UMA
--        seguradora (CLAUDE.md §13.9); as prontas vêm do portal conectado e do registry, e a tela já as calcula.
--    checklist-6h    md5(faq::text) = 400e6a4206e7625dda11780c7e1a2721
--      · "Quando ele chega?" → "às 6h" — FALSO: chega no horário do perfil (`deve_publicar_briefing`, tick.py), que o
--        Configurar escolhe; o padrão é 08:00 (`briefing_service.perfil`; 📊 3 de 3 perfis diários em {"time":"08:00"}).
--      · "Por que no máximo três itens?" — FALSO: o corte é `max_items` (📊 7 nos 3 perfis; `compor(max_itens=7)`).
--      · "Onde eu vejo?" → "e no canal que você escolher" — o Configurar não tem escolha de canal (📊 channels =
--        ["dashboard"] nos 3 perfis).
--    radar-mercado-regulacao  md5(faq::text) = 8f745d0a51e1ddfc08004dfe2fd680ce
--      · "Ele olha as fontes todo dia" — as da SUSEP são diárias, a do CNSP é SEMANAL (`FONTES_PADRAO`, radar.py).
--    As outras 11 (follow-up, resumo, tarefas-agendadas e os 8 "Em breve") foram conferidas contra o código e não
--    prometem o que não existe — ficam como estão.
--
-- APPLY (pelo GERENTE — o builder NÃO aplica; idempotente): cada UPDATE só casa o texto ANTIGO exato (o md5 do faq
--   inteiro): rodar de novo não casa nada; uma Dúvida que alguém já reescreveu nunca é sobrescrita.
--
-- VERIFY (read-only · esperado: 0 · 0 · 0 · 0 · 5 · 4 · 3 · 0):
--   select
--     (select count(*) from public.auxiliary_templates where slug = 'cobranca-feita' and faq::text ~* '(Sim, quando o aplicativo está ligado|Hoje, da Allianz)') cobranca_falsa,
--     (select count(*) from public.auxiliary_templates where faq::text ~* 'Allianz|Porto Seguro|Mapfre|Tokio|Yelum|HDI|Zurich|Bradesco|SulAm') seguradora_cravada,
--     (select count(*) from public.auxiliary_templates where slug = 'checklist-6h' and faq::text ~* '(às 6h|três itens|canal que você escolher)') checklist_falso,
--     (select count(*) from public.auxiliary_templates where slug = 'radar-mercado-regulacao' and faq::text like '%olha as fontes todo dia%') radar_falso,
--     (select jsonb_array_length(faq) from public.auxiliary_templates where slug = 'cobranca-feita') duvidas_cobranca,
--     (select jsonb_array_length(faq) from public.auxiliary_templates where slug = 'checklist-6h') duvidas_checklist,
--     (select jsonb_array_length(faq) from public.auxiliary_templates where slug = 'radar-mercado-regulacao') duvidas_radar,
--     (select count(*) from public.auxiliary_templates, jsonb_array_elements(coalesce(faq, '[]'::jsonb)) d
--        where is_active and (jsonb_typeof(d -> 'pergunta') <> 'string' or jsonb_typeof(d -> 'resposta') <> 'string')) duvida_malformada;
--
-- ROLLBACK (escrito ANTES; devolve os textos de 15/10, LITERAIS — lidos do banco com SELECT em READ ONLY):
--   update public.auxiliary_templates set faq = '[{"pergunta": "O boleto sai sozinho para o cliente?", "resposta": "Sim, quando o aplicativo está ligado: ele manda o boleto pelo WhatsApp da corretora, um de cada vez, espaçado. Desligado, nada sai."}, {"pergunta": "De quais seguradoras ele busca as parcelas vencidas?", "resposta": "Hoje, da Allianz. As outras seguradoras entram uma a uma."}, {"pergunta": "Por que os envios são espaçados?", "resposta": "De propósito, para não queimar o número da corretora."}, {"pergunta": "E o cliente sem WhatsApp válido?", "resposta": "Ele avisa você, para você cobrar do jeito de sempre."}, {"pergunta": "Onde vejo o que já saiu?", "resposta": "Na aba Cobranças: o que saiu, dia a dia, só da sua corretora."}]'::jsonb, updated_at = now()
--    where slug = 'cobranca-feita';
--   update public.auxiliary_templates set faq = '[{"pergunta": "Quando ele chega?", "resposta": "Todo dia de manhã, às 6h."}, {"pergunta": "Por que no máximo três itens?", "resposta": "Porque não é relatório: é o que precisa de você hoje, na ordem do que vale mais e do que dá para resolver no dia. O resto fica visível, sem ser empurrado."}, {"pergunta": "Onde eu vejo?", "resposta": "Na aba Hoje, aqui no aplicativo, e no canal que você escolher."}, {"pergunta": "De onde vêm os itens?", "resposta": "Das conversas de atendimento, da carteira e dos sinais do próprio AutoBrokers."}]'::jsonb, updated_at = now()
--    where slug = 'checklist-6h';
--   update public.auxiliary_templates set faq = '[{"pergunta": "De onde vêm os avisos?", "resposta": "Só de fonte oficial: SUSEP, CNSP e a legislação do setor. Manchete não vira aviso."}, {"pergunta": "Com que frequência?", "resposta": "Ele olha as fontes todo dia e entrega o Radar Regulatório uma vez por semana."}, {"pergunta": "O que conta como mudança?", "resposta": "Só o que altera texto de norma, prazo ou cobertura. Banner novo ou data de atualização trocada não vira aviso."}]'::jsonb, updated_at = now()
--    where slug = 'radar-mercado-regulacao';
--
-- EXPAND-FIRST: sim (nenhum DDL; só UPDATE de texto do catálogo global)
-- DESTRUTIVA:   não (o ROLLBACK devolve cada texto de antes, literal)
-- =============================================================

-- A Cobrança: a resposta por MODO de envio; as seguradoras vêm do portal conectado (nenhum nome fixo) -----------------
update public.auxiliary_templates set faq = '[
  {"pergunta": "O boleto sai sozinho para o cliente?", "resposta": "Depende do modo de envio que você escolher em Configurar. Em Teste, a mensagem e o boleto vão só para o seu número de teste, e o segurado nunca recebe nada. Em Somente relatório, nada é enviado. Em Encaminhar para minha equipe, a atendente recebe o pacote pronto e repassa ao cliente. Só em Enviar diretamente ao cliente, depois que você confirma, o segurado recebe pelo WhatsApp da corretora. E nada sai com o aplicativo desligado."},
  {"pergunta": "De quais seguradoras ele busca as parcelas vencidas?", "resposta": "Das que você marcar em Configurar, em Onde ele procura. Aparecem prontas as seguradoras que a sua corretora conectou e em que a cobrança automática já existe. Quando uma nova fica pronta, ela aparece lá para você marcar."},
  {"pergunta": "Por que os envios são espaçados?", "resposta": "De propósito, para não queimar o número da corretora."},
  {"pergunta": "E o cliente sem WhatsApp válido?", "resposta": "Ele avisa você, para você cobrar do jeito de sempre."},
  {"pergunta": "Onde vejo o que já saiu?", "resposta": "Na aba Cobranças: o que saiu, dia a dia, só da sua corretora."}
]'::jsonb, updated_at = now()
 where slug = 'cobranca-feita' and md5(faq::text) = '86c0fae8a72c258c01246c04278bd8e7';

-- O Checklist: o horário é o do Configurar; o corte de itens não é três; não há escolha de canal ------------------------
update public.auxiliary_templates set faq = '[
  {"pergunta": "Quando ele chega?", "resposta": "Todo dia, no horário que você escolher em Configurar. Se você não escolher, às 8h (horário de Brasília)."},
  {"pergunta": "Por que vêm poucos itens?", "resposta": "Porque não é relatório: é o que precisa de você hoje, na ordem do que vale mais e do que dá para resolver no dia. O resto fica visível, sem ser empurrado."},
  {"pergunta": "Onde eu vejo?", "resposta": "Na aba Hoje, aqui no aplicativo."},
  {"pergunta": "De onde vêm os itens?", "resposta": "Das conversas de atendimento, da carteira e dos sinais do próprio AutoBrokers."}
]'::jsonb, updated_at = now()
 where slug = 'checklist-6h' and md5(faq::text) = '400e6a4206e7625dda11780c7e1a2721';

-- O Radar: a frequência de cada fonte, como o código faz ----------------------------------------------------------------
update public.auxiliary_templates set faq = '[
  {"pergunta": "De onde vêm os avisos?", "resposta": "Só de fonte oficial: SUSEP, CNSP e a legislação do setor. Manchete não vira aviso."},
  {"pergunta": "Com que frequência?", "resposta": "Ele confere as fontes da SUSEP todo dia e as do CNSP toda semana, e entrega o Radar Regulatório uma vez por semana."},
  {"pergunta": "O que conta como mudança?", "resposta": "Só o que altera texto de norma, prazo ou cobertura. Banner novo ou data de atualização trocada não vira aviso."}
]'::jsonb, updated_at = now()
 where slug = 'radar-mercado-regulacao' and md5(faq::text) = '8f745d0a51e1ddfc08004dfe2fd680ce';
