-- =============================================================
-- MIGRATION: 20261016_01_spec139_conteudo_dos_aplicativos
-- SPEC:      SPEC-139 — L4 · a casca para todos (o conteúdo da loja)
-- AUTOR:     builder L4 (claude-opus-5-5)            DATA: 2026-10-15
-- OBJETIVO:  todo aplicativo da loja ganha "Dúvidas" e frases em linguagem de gente — só CONTEÚDO do catálogo GLOBAL
--            (`auxiliary_templates`): nenhuma coluna, nenhuma trava, nenhum `catalog_state`, nada de corretora.
--
-- 📊 ANTES (15/10/2026, psycopg READ ONLY, scratchpad b1_l4.py / b1_l4e.py — só SELECT):
--    · 19 linhas; 18 ativas (9 available · 9 coming_soon) + renovacao-maxima inativa
--    · faq com ≥ 1 dúvida: só `renovacao` (5) e `cotacao` (7); as outras 16 com 0 (o "Em breve" sem a aba Dúvidas
--      que a SPEC §4.4 exige)
--    · frases que a tela mostra e que não são de gente: "Auxiliar que analisa… em modo dry-run" (follow-up),
--      "Auxiliar read-only… No MVP" (resumo), "Este auxiliar…" (4 descrições), o Radar sem acento ("regulacao",
--      "Nao", "so"), `tarefas-agendadas` com "O que faz" em TEXTO solto (a tela desenhava 3 linhas vazias) e a promessa
--      sem acento, e 9 "o que falta" com "decisão do Founder", "espelho da carteira", "API", "endpoint", "SES"
--
-- APPLY (pelo GERENTE — o builder NÃO aplica; idempotente; só UPDATE de conteúdo global):
--   A. `faq` dos 15 aplicativos sem dúvida (nunca `quem-cobra-menos`: a SPEC só muda a capa dele) — SÓ onde está vazio
--      (`faq is null or faq = '[]'`): a dúvida que alguém já escreveu nunca é sobrescrita; rodar de novo não faz nada.
--   B. frases: cada UPDATE só casa o texto ANTIGO (like/igualdade) — rodar de novo não casa nada.
--   C. "o que falta" dos 9 "Em breve" em linguagem de gente — só onde ainda está o texto antigo.
--   ⛔ NÃO muda `catalog_state` (o B1 mediu radar e tarefas-agendadas sem trabalho, mas os dois têm motor no
--      backend — research/radar.py e dono_da_rotina.py; virar "Em breve" é decisão registrada, não conteúdo).
--
-- VERIFY (read-only · esperado: 1 · 0 · 0 · 0 · 0 · 9 · 9):
--   select
--     (select count(*) from public.auxiliary_templates where is_active and status = 'active'
--        and (faq is null or jsonb_array_length(faq) = 0)) ativos_sem_duvida,                 -- só quem-cobra-menos
--     (select count(*) from public.auxiliary_templates where is_active
--        and (coalesce(description,'') || ' ' || coalesce(short_description,'') || ' ' || coalesce(missing_for_launch,''))
--            ~* '(Este auxiliar|Auxiliar que|Auxiliar read-only|dry-run|\mMVP\M|Founder|espelho da carteira|endpoint|Regulatorio)'
--     ) frases_de_maquina,
--     (select count(*) from public.auxiliary_templates where is_active
--        and jsonb_typeof(what_it_does) = 'array' and jsonb_typeof(what_it_does -> 0) = 'string') faz_em_texto_solto,
--     (select count(*) from public.auxiliary_templates, jsonb_array_elements(coalesce(faq, '[]'::jsonb)) d
--        where is_active and (jsonb_typeof(d -> 'pergunta') <> 'string' or jsonb_typeof(d -> 'resposta') <> 'string'))
--       duvida_malformada,
--     (select count(*) from public.auxiliary_templates where is_active and value_promise like 'Voce %') promessa_sem_acento,
--     (select count(*) from public.auxiliary_templates where is_active and catalog_state = 'available') disponiveis,
--     (select count(*) from public.auxiliary_templates where is_active and catalog_state = 'coming_soon') em_breve;
--
-- ROLLBACK (escrito ANTES; devolve os textos de 15/10 — os de antes estão LITERAIS abaixo):
--   update public.auxiliary_templates set faq = null, updated_at = now()
--    where slug in ('cobranca-feita','checklist-6h','follow-up-whatsapp','resumo-atendimentos','radar-mercado-regulacao',
--                   'tarefas-agendadas','caca-comissao','carteira-blindada','clientes-perdidos','contabilidade-pronta',
--                   'digitacao-zero','organizacao-completa','protecao-completa','resgatar-cliente','sinistralidade-avancada');
--   update public.auxiliary_templates set description = replace(description, 'Este aplicativo', 'Este auxiliar')
--    where slug in ('cobranca-feita','caca-comissao','clientes-perdidos','protecao-completa');
--   update public.auxiliary_templates set
--     short_description = 'Gera rascunhos humanos de follow-up para WhatsApp com aprovação humana.',
--     description = 'Auxiliar que analisa um atendimento, gera um rascunho seguro de follow-up e cria uma solicitação de aprovação humana em modo dry-run. Nenhuma mensagem real é enviada automaticamente.'
--    where slug = 'follow-up-whatsapp';
--   update public.auxiliary_templates set
--     description = 'Auxiliar read-only para transformar conversas da corretora em um resumo operacional claro, com tópicos, decisões, pendências e recomendações de acompanhamento. No MVP, não executa ações externas e não envia mensagens ao cliente.'
--    where slug = 'resumo-atendimentos';
--   update public.auxiliary_templates set
--     short_description = 'Avisa quando a regulacao de seguros muda, antes do cliente perguntar.',
--     description = E'Acompanha as fontes oficiais do setor — SUSEP, CNSP e legislacao — e avisa quando algo muda de verdade.\n\nUma vez por semana entrega o Radar Regulatorio: o que mudou, desde quando passa a valer e o que exige acao da corretora.\n\nNao dispara por manchete: so fonte oficial, e so mudanca que altera texto de norma, prazo ou cobertura. Banner novo ou data de atualizacao trocada nao vira aviso.'
--    where slug = 'radar-mercado-regulacao';
--   update public.auxiliary_templates set
--     what_it_does = '["Executa no horario que voce pediu, sem voce lembrar", "Guarda num lugar so tudo que voce pediu pelo chat", "Deixa voce pausar ou apagar qualquer uma quando quiser"]'::jsonb,
--     value_promise = 'Voce para de lembrar de pedir a mesma coisa toda semana.',
--     description = replace(description, 'Cada uma vira uma tarefa com horário próprio', 'Cada uma vira uma rotina com horário próprio')
--    where slug = 'tarefas-agendadas';
--   update public.auxiliary_templates as t set missing_for_launch = v.antigo
--   from (values
--     ('caca-comissao', 'Precisa da API da InfoCap liberada para comissão (hoje bloqueada) e do espelho da carteira.'),
--     ('carteira-blindada', 'Precisa do espelho da carteira e de decisão do Founder sobre a fonte de valor de veículo.'),
--     ('clientes-perdidos', 'Precisa do espelho da carteira com histórico de renovação.'),
--     ('contabilidade-pronta', 'Depende de decisão do Founder sobre até onde vai o conselho tributário (disclaimer, revisão por contador ou parceria).'),
--     ('digitacao-zero', 'Precisa da API de escrita da InfoCap e da leitura estruturada do PDF da apólice.'),
--     ('organizacao-completa', 'Precisa do espelho da carteira.'),
--     ('protecao-completa', 'Precisa do espelho da carteira e do enriquecimento por CNPJ.'),
--     ('resgatar-cliente', 'Precisa do funil de cotações da InfoCap (endpoint liberado, nunca chamado).'),
--     ('sinistralidade-avancada', 'Precisa da ingestão do SES da SUSEP e do espelho da carteira para o comparativo.')
--   ) as v(slug, antigo) where t.slug = v.slug;
--
-- EXPAND-FIRST: sim (nenhum DDL; só UPDATE de texto do catálogo global)
-- DESTRUTIVA:   não (o ROLLBACK devolve cada texto de antes, literal)
-- =============================================================

-- A. as Dúvidas — só onde ainda não há nenhuma (nunca sobrescreve a escrita por alguém) ---------------------------------
update public.auxiliary_templates as t set faq = v.faq, updated_at = now()
from (values
  ('cobranca-feita', '[
    {"pergunta": "O boleto sai sozinho para o cliente?", "resposta": "Sim, quando o aplicativo está ligado: ele manda o boleto pelo WhatsApp da corretora, um de cada vez, espaçado. Desligado, nada sai."},
    {"pergunta": "De quais seguradoras ele busca as parcelas vencidas?", "resposta": "Hoje, da Allianz. As outras seguradoras entram uma a uma."},
    {"pergunta": "Por que os envios são espaçados?", "resposta": "De propósito, para não queimar o número da corretora."},
    {"pergunta": "E o cliente sem WhatsApp válido?", "resposta": "Ele avisa você, para você cobrar do jeito de sempre."},
    {"pergunta": "Onde vejo o que já saiu?", "resposta": "Na aba Cobranças: o que saiu, dia a dia, só da sua corretora."}
  ]'::jsonb),
  ('checklist-6h', '[
    {"pergunta": "Quando ele chega?", "resposta": "Todo dia de manhã, às 6h."},
    {"pergunta": "Por que no máximo três itens?", "resposta": "Porque não é relatório: é o que precisa de você hoje, na ordem do que vale mais e do que dá para resolver no dia. O resto fica visível, sem ser empurrado."},
    {"pergunta": "Onde eu vejo?", "resposta": "Na aba Hoje, aqui no aplicativo, e no canal que você escolher."},
    {"pergunta": "De onde vêm os itens?", "resposta": "Das conversas de atendimento, da carteira e dos sinais do próprio AutoBrokers."}
  ]'::jsonb),
  -- o "Como funciona" que saiu da tela antiga (L3) vem para cá, sem jargão ("modo seguro", "dry-run" → o que acontece)
  ('follow-up-whatsapp', '[
    {"pergunta": "Como funciona?", "resposta": "Escolha um atendimento (ou só diga o objetivo), escolha o tom e peça o rascunho. Edite se quiser e crie o pedido de aprovação."},
    {"pergunta": "A mensagem sai sozinha para o cliente?", "resposta": "Não. Por enquanto, nenhuma mensagem sai de verdade para o cliente, nem depois de aprovada."},
    {"pergunta": "De onde ele tira o que escrever?", "resposta": "Do próprio atendimento: ele lê a conversa e escreve o retorno no tom que você escolheu."}
  ]'::jsonb),
  ('resumo-atendimentos', '[
    {"pergunta": "Como funciona?", "resposta": "Você escolhe o atendimento, ou deixa no automático. O AutoBrokers lê o histórico e devolve um resumo com o que ficou pendente e os próximos passos sugeridos, pronto para você revisar."},
    {"pergunta": "Ele responde ao cliente?", "resposta": "Não. Ele só lê as conversas e escreve o resumo. Nada sai para o cliente."},
    {"pergunta": "O que vem no resumo?", "resposta": "Os assuntos, as decisões, o que ficou pendente e os próximos passos."}
  ]'::jsonb),
  ('radar-mercado-regulacao', '[
    {"pergunta": "De onde vêm os avisos?", "resposta": "Só de fonte oficial: SUSEP, CNSP e a legislação do setor. Manchete não vira aviso."},
    {"pergunta": "Com que frequência?", "resposta": "Ele olha as fontes todo dia e entrega o Radar Regulatório uma vez por semana."},
    {"pergunta": "O que conta como mudança?", "resposta": "Só o que altera texto de norma, prazo ou cobertura. Banner novo ou data de atualização trocada não vira aviso."}
  ]'::jsonb),
  ('tarefas-agendadas', '[
    {"pergunta": "Como eu crio uma tarefa?", "resposta": "Pedindo no chat, do seu jeito: “todo dia às 8h me manda…”. Ela ganha um horário próprio e aparece aqui."},
    {"pergunta": "Posso pausar ou apagar?", "resposta": "Sim, qualquer uma, quando quiser."}
  ]'::jsonb),
  ('caca-comissao', '[
    {"pergunta": "Por que ainda não está pronto?", "resposta": "Falta a InfoCap liberar a leitura das comissões e o AutoBrokers ter a cópia completa da sua carteira para comparar. Quando estiver pronto, ele aparece em Disponíveis para você ligar."},
    {"pergunta": "Ele mexe no meu extrato?", "resposta": "Não. Ele só compara o extrato com o esperado e mostra onde não bateu, apólice por apólice."}
  ]'::jsonb),
  ('carteira-blindada', '[
    {"pergunta": "Por que ainda não está pronto?", "resposta": "Falta o AutoBrokers ter a cópia completa da sua carteira e escolher de onde vem o valor de referência dos veículos. Quando estiver pronto, ele aparece em Disponíveis para você ligar."},
    {"pergunta": "O que ele vai conferir?", "resposta": "As apólices emitidas na semana contra os dados do cliente: código de referência, uso declarado e vistoria pendente."}
  ]'::jsonb),
  ('clientes-perdidos', '[
    {"pergunta": "Por que ainda não está pronto?", "resposta": "Falta o AutoBrokers ter a cópia completa da sua carteira, com o histórico de renovações. Quando estiver pronto, ele aparece em Disponíveis para você ligar."},
    {"pergunta": "Como ele vai achar quem foi embora?", "resposta": "Procurando quem foi cliente e saiu sem cancelar, e ordenando por quanto cada um valia por ano."}
  ]'::jsonb),
  ('contabilidade-pronta', '[
    {"pergunta": "Por que ainda não está pronto?", "resposta": "Falta definir até onde vai a ajuda. Quando estiver pronto, ele aparece em Disponíveis para você ligar."},
    {"pergunta": "Ele vai dar conselho tributário?", "resposta": "Não. Ele entrega a conta feita e o relatório pronto para o seu contador conferir."}
  ]'::jsonb),
  ('digitacao-zero', '[
    {"pergunta": "Por que ainda não está pronto?", "resposta": "Falta a InfoCap permitir que o AutoBrokers grave no cadastro, e a leitura completa do PDF da apólice. Quando estiver pronto, ele aparece em Disponíveis para você ligar."},
    {"pergunta": "Ele vai gravar sem eu ver?", "resposta": "Não. Ele mostra o que preencheu para você conferir antes de gravar."}
  ]'::jsonb),
  ('organizacao-completa', '[
    {"pergunta": "Por que ainda não está pronto?", "resposta": "Falta o AutoBrokers ter a cópia completa da sua carteira. Quando estiver pronto, ele aparece em Disponíveis para você ligar."},
    {"pergunta": "Ele vai corrigir o cadastro sozinho?", "resposta": "Não. Ele propõe a correção e só aplica se você aprovar."}
  ]'::jsonb),
  ('protecao-completa', '[
    {"pergunta": "Por que ainda não está pronto?", "resposta": "Falta o AutoBrokers ter a cópia completa da sua carteira e consultar os dados das empresas pelo CNPJ. Quando estiver pronto, ele aparece em Disponíveis para você ligar."},
    {"pergunta": "Como ele vai escolher quem mostrar?", "resposta": "Cruzando quem você já atende com os ramos que a pessoa não tem, e priorizando pelo risco real, não pelo tamanho do seguro."}
  ]'::jsonb),
  ('resgatar-cliente', '[
    {"pergunta": "Por que ainda não está pronto?", "resposta": "Falta ligar a leitura das cotações da InfoCap. Quando estiver pronto, ele aparece em Disponíveis para você ligar."},
    {"pergunta": "O que ele vai avisar?", "resposta": "A cotação em que o cliente foi o último a falar, e o ex-cliente que chega à época de renovar com outra corretora."}
  ]'::jsonb),
  ('sinistralidade-avancada', '[
    {"pergunta": "Por que ainda não está pronto?", "resposta": "Falta trazer os números públicos da SUSEP e a cópia completa da sua carteira para comparar. Quando estiver pronto, ele aparece em Disponíveis para você ligar."},
    {"pergunta": "De onde vêm os números?", "resposta": "Do que a SUSEP publica: quanto cada seguradora arrecadou e quanto pagou de sinistro."}
  ]'::jsonb)
) as v(slug, faq)
where t.slug = v.slug
  and (t.faq is null or t.faq = '[]'::jsonb);

-- B. as frases que a tela mostra, em linguagem de gente (cada UPDATE só casa o texto ANTIGO) -----------------------------
update public.auxiliary_templates set description = replace(description, 'Este auxiliar', 'Este aplicativo'), updated_at = now()
 where slug in ('cobranca-feita', 'caca-comissao', 'clientes-perdidos', 'protecao-completa')
   and description like '%Este auxiliar%';

update public.auxiliary_templates set
  short_description = 'Escreve o rascunho do retorno pelo WhatsApp, no tom certo, para você revisar e aprovar.',
  description = 'Lê um atendimento e escreve o rascunho da mensagem de retorno, no tom que você escolher. Você edita e cria o pedido de aprovação. Por enquanto, nenhuma mensagem sai de verdade para o cliente.',
  updated_at = now()
 where slug = 'follow-up-whatsapp' and description like 'Auxiliar que analisa%';

update public.auxiliary_templates set
  description = 'Lê as conversas de atendimento da corretora e entrega um resumo claro: os assuntos, as decisões, o que ficou pendente e os próximos passos. Ele só lê: não faz nada fora daqui e não manda mensagem ao cliente.',
  updated_at = now()
 where slug = 'resumo-atendimentos' and description like 'Auxiliar read-only%';

update public.auxiliary_templates set
  short_description = 'Avisa quando a regulação de seguros muda, antes de o cliente perguntar.',
  description = E'Acompanha as fontes oficiais do setor — SUSEP, CNSP e legislação — e avisa quando algo muda de verdade.\n\nUma vez por semana entrega o Radar Regulatório: o que mudou, desde quando passa a valer e o que exige ação da corretora.\n\nNão dispara por manchete: só fonte oficial, e só mudança que altera texto de norma, prazo ou cobertura. Banner novo ou data de atualização trocada não vira aviso.',
  updated_at = now()
 where slug = 'radar-mercado-regulacao' and description like '%Radar Regulatorio%';

update public.auxiliary_templates set
  what_it_does = '[
    {"tarefa": "Executa no horário que você pediu, sem você lembrar", "frequencia": "no horário de cada tarefa"},
    {"tarefa": "Guarda num lugar só tudo o que você pediu pelo chat", "frequencia": "sempre"},
    {"tarefa": "Deixa você pausar ou apagar qualquer uma quando quiser", "frequencia": "quando você quiser"}
  ]'::jsonb,
  updated_at = now()
 where slug = 'tarefas-agendadas' and jsonb_typeof(what_it_does -> 0) = 'string';

update public.auxiliary_templates set value_promise = 'Você para de lembrar de pedir a mesma coisa toda semana.', updated_at = now()
 where slug = 'tarefas-agendadas' and value_promise = 'Voce para de lembrar de pedir a mesma coisa toda semana.';

update public.auxiliary_templates
   set description = replace(description, 'Cada uma vira uma rotina com horário próprio', 'Cada uma vira uma tarefa com horário próprio'),
       updated_at = now()
 where slug = 'tarefas-agendadas' and description like '%Cada uma vira uma rotina com horário próprio%';

-- C. "o que falta" dos "Em breve", sem jargão (aparece no botão desabilitado e em "Ainda não está pronto") --------------
update public.auxiliary_templates as t set missing_for_launch = v.novo, updated_at = now()
from (values
  ('caca-comissao', 'Precisa da API da InfoCap liberada para comissão (hoje bloqueada) e do espelho da carteira.',
   'Falta a InfoCap liberar a leitura das comissões e o AutoBrokers ter a cópia completa da sua carteira para comparar.'),
  ('carteira-blindada', 'Precisa do espelho da carteira e de decisão do Founder sobre a fonte de valor de veículo.',
   'Falta o AutoBrokers ter a cópia completa da sua carteira e escolher de onde vem o valor de referência dos veículos.'),
  ('clientes-perdidos', 'Precisa do espelho da carteira com histórico de renovação.',
   'Falta o AutoBrokers ter a cópia completa da sua carteira, com o histórico de renovações.'),
  ('contabilidade-pronta', 'Depende de decisão do Founder sobre até onde vai o conselho tributário (disclaimer, revisão por contador ou parceria).',
   'Falta definir até onde vai a ajuda: a conta pronta para o seu contador conferir, sem conselho tributário.'),
  ('digitacao-zero', 'Precisa da API de escrita da InfoCap e da leitura estruturada do PDF da apólice.',
   'Falta a InfoCap permitir que o AutoBrokers grave no cadastro, e a leitura completa do PDF da apólice.'),
  ('organizacao-completa', 'Precisa do espelho da carteira.',
   'Falta o AutoBrokers ter a cópia completa da sua carteira.'),
  ('protecao-completa', 'Precisa do espelho da carteira e do enriquecimento por CNPJ.',
   'Falta o AutoBrokers ter a cópia completa da sua carteira e consultar os dados das empresas pelo CNPJ.'),
  ('resgatar-cliente', 'Precisa do funil de cotações da InfoCap (endpoint liberado, nunca chamado).',
   'Falta ligar a leitura das cotações da InfoCap.'),
  ('sinistralidade-avancada', 'Precisa da ingestão do SES da SUSEP e do espelho da carteira para o comparativo.',
   'Falta trazer os números públicos da SUSEP e a cópia completa da sua carteira para comparar.')
) as v(slug, antigo, novo)
where t.slug = v.slug and t.missing_for_launch = v.antigo;
