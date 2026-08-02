-- =============================================================
-- MIGRATION: spec064_seed_catalogo
-- SPEC:      SPEC-064 — Bloco D (o catálogo) + D.5 (a Cobrança vira Auxiliar)
-- AUTOR:     lider tecnico            DATA: 2026-08-02
-- OBJETIVO:  o catálogo global que TODA corretora enxerga — 15 auxiliares,
--            todos desligados, os que não existem com a descrição já escrita.
--
-- APPLY:     1. reescreve os 3 templates ativos com a copy de catálogo
--            2. cria 'checklist-6h' (o Briefing vira Auxiliar)
--            3. cria 'cobranca-feita' (a Rotina vira Auxiliar — D.5)
--            4. cria os 10 'coming_soon' com descrição completa
--
-- VERIFY:    select catalog_state, count(*) from public.auxiliary_templates
--             where status = 'active' group by 1;
--            -- esperado: available=5, coming_soon=10
--
--            select slug from public.auxiliary_templates
--             where status='active'
--               and (headline is null or headline = ''
--                    or categories = '{}'::text[]
--                    or value_promise is null);
--            -- esperado: 0 linhas (nenhum campo de catálogo vazio)
--
-- ROLLBACK:  delete from public.auxiliary_templates
--             where slug in ('checklist-6h','cobranca-feita','caca-comissao',
--               'contabilidade-pronta','clientes-perdidos','protecao-completa',
--               'resgatar-cliente','renovacao-maxima','sinistralidade-avancada',
--               'carteira-blindada','organizacao-completa','digitacao-zero')
--               and not exists (select 1 from public.tenant_auxiliaries t
--                                where t.template_id = auxiliary_templates.id);
--            update public.auxiliary_templates
--               set headline=null, categories='{}'::text[], data_sources='{}'::text[],
--                   what_it_does='[]'::jsonb, value_promise=null, missing_for_launch=null
--             where slug in ('radar-mercado-regulacao','resumo-atendimentos','follow-up-whatsapp');
--
-- EXPAND-FIRST: sim — nenhum registro é apagado. Os 3 archived de teste
--               continuam intocados; a limpeza deles é a migration 04.
-- DESTRUTIVA:   não
-- =============================================================
--
-- NOTA SOBRE OS SLUGS
-- -------------------
-- O `slug` NÃO muda, nem para os que ganharam nome novo. `tenant_auxiliaries`
-- referencia por slug, e a própria rota de edição do admin declara o slug
-- imutável ("evita quebrar instalações por slug"). O que muda é o `name` — o
-- que o corretor lê. Slug é chave técnica; nome é produto.
--
-- NOTA SOBRE OS NÚMEROS  (CLAUDE.md §12.1)
-- ----------------------
-- Nenhum `value_promise` de auxiliar 'coming_soon' traz número. Eles dizem o
-- que SERÁ medido. Inventar "recupera R$ 2.000/mês" aqui seria repetir
-- exatamente o erro que a auditoria de 02/08 encontrou: número ilustrativo
-- formatado como número medido, citado três documentos depois como fato.

-- -------------------------------------------------------------
-- 1. Os três que já existem ganham copy de catálogo
-- -------------------------------------------------------------

update public.auxiliary_templates set
  name        = 'Primeira Mão',
  headline    = 'Você sabe da mudança na regra antes do seu cliente perguntar',
  categories  = array['negociacao']::text[],
  catalog_state = 'available',
  data_sources  = array['susep','cnsp','legislacao']::text[],
  what_it_does  = '[
    {"tarefa": "Acompanha SUSEP, CNSP e legislação do setor", "frequencia": "diária"},
    {"tarefa": "Entrega o Radar Regulatório: o que mudou, desde quando vale, o que exige ação", "frequencia": "semanal"}
  ]'::jsonb,
  value_promise = 'Chegar antes. Vai ser medido quantas mudanças de norma o sistema entrega antes de a corretora ouvir de outra fonte.',
  category      = 'mercado'
where slug = 'radar-mercado-regulacao';

update public.auxiliary_templates set
  name        = 'Resumo do Dia',
  headline    = 'Você lê em dois minutos o que levou o dia inteiro para acontecer',
  categories  = array['tempo_livre']::text[],
  catalog_state = 'available',
  data_sources  = array['conversas']::text[],
  what_it_does  = '[
    {"tarefa": "Lê a conversa de atendimento inteira", "frequencia": "sob demanda"},
    {"tarefa": "Extrai decisões, pendências e próximos passos", "frequencia": "sob demanda"}
  ]'::jsonb,
  value_promise = 'O tempo de ler a conversa inteira. Vai ser medido o tempo entre o fim do atendimento e o corretor saber o que ficou pendente.',
  category      = 'atendimento'
where slug = 'resumo-atendimentos';

update public.auxiliary_templates set
  name        = 'Follow-up Certo',
  headline    = 'A mensagem de retorno sai no tom certo, e você só aprova',
  categories  = array['cliente_blindado']::text[],
  catalog_state = 'available',
  data_sources  = array['conversas']::text[],
  what_it_does  = '[
    {"tarefa": "Lê o atendimento e escreve o rascunho do retorno", "frequencia": "sob demanda"},
    {"tarefa": "Pede sua aprovação antes de qualquer envio", "frequencia": "sempre"}
  ]'::jsonb,
  value_promise = 'O retorno que não é esquecido. Vai ser medido quantos follow-ups saem e em quanto tempo.',
  category      = 'Comunicação'
where slug = 'follow-up-whatsapp';

-- -------------------------------------------------------------
-- 2. O Briefing vira Auxiliar (SPEC-064 A.3)
-- -------------------------------------------------------------
-- Ele já tinha tudo o que define um Auxiliar: agenda, configuração por
-- empresa (`briefing_profiles`), execução durável (`work_runs`) e saída
-- (`briefing_publications`). Faltava reconhecê-lo como Auxiliar em vez de
-- pilar de menu.

insert into public.auxiliary_templates
  (slug, name, headline, categories, catalog_state, data_sources, what_it_does,
   value_promise, category, short_description, description, icon, status,
   execution_mode, trigger_type, requires_human_approval, uses_external_actions,
   is_active, default_config, permissions)
values (
  'checklist-6h',
  'Checklist das 6h',
  'Você abre o dia sabendo exatamente o que precisa de você',
  array['dinheiro_que_volta','dinheiro_novo','cliente_blindado','negociacao','protecao_carteira','tempo_livre']::text[],
  'available',
  array['conversas','carteira','sinais_do_sistema']::text[],
  '[
    {"tarefa": "Reúne o que aconteceu ontem e o que vence hoje", "frequencia": "diária, às 6h"},
    {"tarefa": "Separa o que precisa de você do que já foi resolvido", "frequencia": "diária"},
    {"tarefa": "Entrega no painel, e no canal que você escolher", "frequencia": "diária"}
  ]'::jsonb,
  'A primeira hora do dia. Vai ser medido quantos itens do checklist viram ação no mesmo dia.',
  'briefing',
  'O que precisa de você hoje, num lugar só.',
  'Todo dia de manhã, reúne o que aconteceu na corretora e separa o que exige decisão sua do que já andou sozinho.

Não é relatório: é uma lista curta — no máximo três itens no diário — ordenada pelo que vale mais e pelo que dá para resolver hoje. O que não cabe fica no backlog visível, nunca empurrado.',
  'aprovacao',
  'active',
  'scheduled', 'scheduled',
  false, false, true,
  '{"runtime": {"kind": "workflow", "workflow": "intelligence.daily_briefing"},
    "visibility": {"type": "global"},
    "horario_padrao": "06:00",
    "teto_itens_diario": 3}'::jsonb,
  '{}'::jsonb
)
on conflict (slug) do update set
  name = excluded.name, headline = excluded.headline,
  categories = excluded.categories, catalog_state = excluded.catalog_state,
  data_sources = excluded.data_sources, what_it_does = excluded.what_it_does,
  value_promise = excluded.value_promise, default_config = excluded.default_config;

-- -------------------------------------------------------------
-- 3. A Cobrança vira Auxiliar — SPEC-064 D.5 (acrescentado pela auditoria)
-- -------------------------------------------------------------
-- A auditoria de 02/08 encontrou a inversão da ontologia escrita em código:
--
--     f"Auxiliar de Cobranca - {routine.get('name')}"
--
-- Uma Rotina que se apresentava como "Auxiliar" numa string. No banco ela
-- estava em `routines` (desligada, só na Resulta) e não em
-- `tenant_auxiliaries`. O Founder pediu explicitamente que ela apareça para
-- TODAS as corretoras poderem ativar.
--
-- Aqui nasce o template global. A migration 03 liga a Rotina existente ao
-- Auxiliar — ela não some, muda de dono.

insert into public.auxiliary_templates
  (slug, name, headline, categories, catalog_state, data_sources, what_it_does,
   value_promise, category, short_description, description, icon, status,
   execution_mode, trigger_type, requires_human_approval, uses_external_actions,
   is_active, default_config, permissions)
values (
  'cobranca-feita',
  'Cobrança Feita',
  'O boleto chega ao cliente antes de a apólice cancelar',
  array['tempo_livre','dinheiro_que_volta']::text[],
  'available',
  array['portal_seguradora','whatsapp']::text[],
  '[
    {"tarefa": "Entra no portal da seguradora e busca quem está com parcela vencida", "frequencia": "configurável"},
    {"tarefa": "Baixa o boleto de cada um", "frequencia": "a cada varredura"},
    {"tarefa": "Manda ao cliente pelo WhatsApp, espaçado, sem rajada", "frequencia": "a cada varredura"},
    {"tarefa": "Avisa você de quem não tem WhatsApp válido", "frequencia": "a cada varredura"}
  ]'::jsonb,
  'A parcela que seria perdida e a hora de ir atrás dela. Vai ser medido quantos boletos saem, quantos são pagos depois do envio, e quanto de comissão deixou de ser cancelada.',
  'cobranca',
  'Busca o inadimplente no portal, manda o boleto e avisa você do que não deu.',
  'A seguradora só libera sua comissão quando o cliente paga a parcela. Se ele atrasa, a comissão não é gerada — e você costuma descobrir quando a apólice já foi cancelada.

Este auxiliar entra no portal da seguradora, encontra quem está com parcela vencida, baixa o boleto e manda ao cliente. Os envios são espaçados de propósito, para não queimar o número da corretora.

Hoje funciona na Allianz. As outras seguradoras entram uma a uma.',
  'success',
  'active',
  'scheduled', 'scheduled',
  true, true, true,
  '{"runtime": {"kind": "workflow", "workflow": "bridge.routine.execute"},
    "visibility": {"type": "global"},
    "portais": ["allianz_corretor"],
    "max_boletos_por_execucao": 10,
    "exige_aprovacao_para_enviar": true}'::jsonb,
  '{"capabilities": ["operational.portal.billing.read", "operational.whatsapp.send"]}'::jsonb
)
on conflict (slug) do update set
  name = excluded.name, headline = excluded.headline,
  categories = excluded.categories, catalog_state = excluded.catalog_state,
  data_sources = excluded.data_sources, what_it_does = excluded.what_it_does,
  value_promise = excluded.value_promise, default_config = excluded.default_config,
  permissions = excluded.permissions;

-- -------------------------------------------------------------
-- 4. Os dez que ainda não existem — com a descrição já escrita
-- -------------------------------------------------------------
-- Por que entram agora: para que você, eu e qualquer LLM futura saibamos ONDE
-- cada coisa vai morar antes de construí-la. Sem isso, o próximo auxiliar
-- nasce numa página nova — que é exatamente como a galeria acabou com duas
-- páginas escritas à mão ao lado da rota dinâmica.
--
-- `missing_for_launch` é o que falta. Torna o catálogo um mapa de roadmap
-- legível pelo Founder, em vez de uma promessa vaga.

insert into public.auxiliary_templates
  (slug, name, headline, categories, catalog_state, data_sources, what_it_does,
   value_promise, missing_for_launch, category, short_description, description,
   icon, status, execution_mode, trigger_type, requires_human_approval,
   uses_external_actions, is_active, default_config, permissions)
values
  ('caca-comissao', 'Caça-Comissão',
   'Confere, apólice por apólice, se a seguradora pagou o que devia',
   array['dinheiro_que_volta']::text[], 'coming_soon',
   array['infocap','portal_seguradora']::text[],
   '[{"tarefa": "Compara o extrato de comissão da seguradora com o esperado da sua carteira", "frequencia": "mensal"},
     {"tarefa": "Aponta a apólice onde não bateu, com a diferença em reais", "frequencia": "mensal"}]'::jsonb,
   'A diferença entre o que foi pago e o que era devido. Vai ser medido em reais, apólice por apólice, contra o extrato.',
   'Precisa da API da InfoCap liberada para comissão (hoje bloqueada) e do espelho da carteira.',
   'financeiro', 'Confere o extrato de comissão contra o esperado.',
   'A conferência de comissão é feita à mão, quando é feita — e leva um ou mais dias por mês. Este auxiliar compara linha a linha e mostra só onde não bateu.',
   'auxiliares', 'active', 'scheduled', 'scheduled', false, false, true,
   '{"runtime": {"kind": "none"}, "visibility": {"type": "global"}}'::jsonb, '{}'::jsonb),

  ('contabilidade-pronta', 'Contabilidade Pronta',
   'O relatório do seu contador sai pronto, com a conta já feita',
   array['dinheiro_que_volta']::text[], 'coming_soon',
   array['infocap','carteira']::text[],
   '[{"tarefa": "Confere anexo do Simples, fator R e retenções", "frequencia": "mensal"},
     {"tarefa": "Monta o relatório no formato que o contador usa", "frequencia": "mensal"}]'::jsonb,
   'O que se paga a mais por enquadramento errado. Vai ser medido contra o que foi efetivamente recolhido.',
   'Depende de decisão do Founder sobre até onde vai o conselho tributário (disclaimer, revisão por contador ou parceria).',
   'financeiro', 'Anexo, fator R e retenção — com o relatório pronto.',
   'Não damos conselho tributário: entregamos a conta feita e o relatório pronto para o seu contador conferir.',
   'auxiliares', 'active', 'scheduled', 'scheduled', true, false, true,
   '{"runtime": {"kind": "none"}, "visibility": {"type": "global"}}'::jsonb, '{}'::jsonb),

  ('clientes-perdidos', 'Clientes Perdidos',
   'Quem renovou com você por anos e hoje não tem nada',
   array['dinheiro_novo']::text[], 'coming_soon',
   array['infocap','carteira']::text[],
   '[{"tarefa": "Encontra quem foi cliente e saiu sem cancelar formalmente", "frequencia": "mensal"},
     {"tarefa": "Ordena por quanto aquele cliente valia por ano", "frequencia": "mensal"}]'::jsonb,
   'A carteira que saiu sem ninguém perceber. Vai ser medido o prêmio anual de cada cliente que sumiu.',
   'Precisa do espelho da carteira com histórico de renovação.',
   'comercial', 'Quem foi cliente por anos e hoje não tem nada com você.',
   'Cliente não avisa que foi embora: ele só não renova. Este auxiliar acha quem sumiu e diz quanto ele valia.',
   'auxiliares', 'active', 'scheduled', 'scheduled', false, false, true,
   '{"runtime": {"kind": "none"}, "visibility": {"type": "global"}}'::jsonb, '{}'::jsonb),

  -- ATENÇÃO AO NOME: a SPEC-064 D.2 chamava este auxiliar de "Venda Casada".
  -- Venda casada é prática PROIBIDA pelo CDC art. 39, I. Vender um produto de
  -- corretagem com esse nome é problema jurídico e de reputação, não de gosto.
  -- Renomeado para "Proteção Completa", que descreve o mesmo trabalho pelo
  -- lado do cliente: ele já é seu e está exposto num risco que você não cobre.
  ('protecao-completa', 'Proteção Completa',
   'Seu cliente está descoberto num risco que você poderia cobrir',
   array['dinheiro_novo']::text[], 'coming_soon',
   array['infocap','carteira','receita_federal']::text[],
   '[{"tarefa": "Cruza quem você já atende com os ramos que ele não tem", "frequencia": "mensal"},
     {"tarefa": "Prioriza pelo risco real, não pelo tíquete", "frequencia": "mensal"}]'::jsonb,
   'A receita que já está na sua carteira. Vai ser medido o prêmio potencial por gap de ramo identificado.',
   'Precisa do espelho da carteira e do enriquecimento por CNPJ.',
   'comercial', 'Quem já é seu e só tem um produto.',
   'O cliente que só tem auto com você provavelmente tem casa, empresa ou vida com outra pessoa — ou com ninguém. Este auxiliar mostra onde ele está descoberto.',
   'auxiliares', 'active', 'scheduled', 'scheduled', false, false, true,
   '{"runtime": {"kind": "none"}, "visibility": {"type": "global"}}'::jsonb, '{}'::jsonb),

  ('resgatar-cliente', 'Resgatar Cliente',
   'A cotação que esfriou e o ex-cliente na hora certa de voltar',
   array['dinheiro_novo']::text[], 'coming_soon',
   array['infocap','conversas']::text[],
   '[{"tarefa": "Acha cotação onde o cliente foi o último a falar", "frequencia": "semanal"},
     {"tarefa": "Avisa quando um ex-cliente entra na janela de renovação do concorrente", "frequencia": "semanal"}]'::jsonb,
   'A venda que parou no meio. Vai ser medido quantas cotações frias voltam a andar depois do aviso.',
   'Precisa do funil de cotações da InfoCap (endpoint liberado, nunca chamado).',
   'comercial', 'Cotação que esfriou e ex-cliente na janela de revanche.',
   'Cotação não morre: ela esfria. E ex-cliente tem uma data por ano em que está disposto a ouvir você de novo.',
   'auxiliares', 'active', 'scheduled', 'scheduled', false, false, true,
   '{"runtime": {"kind": "none"}, "visibility": {"type": "global"}}'::jsonb, '{}'::jsonb),

  ('renovacao-maxima', 'Renovação Máxima',
   'Você sabe do aumento que o cliente não vai aceitar antes de ele ver',
   array['cliente_blindado']::text[], 'coming_soon',
   array['infocap','carteira','susep']::text[],
   '[{"tarefa": "Calcula a variação da renovação antes de o cliente receber", "frequencia": "diária"},
     {"tarefa": "Separa quem vai reclamar de quem vai aceitar", "frequencia": "diária"},
     {"tarefa": "Aponta a renovação órfã — a que vence sem ninguém ter falado", "frequencia": "diária"}]'::jsonb,
   'A renovação que se perde por surpresa. Vai ser medida a taxa de retenção antes e depois do aviso.',
   'Precisa do espelho da carteira com vigências e do valor de referência do bem.',
   'comercial', 'O aumento que ele não vai aceitar, calculado antes.',
   'A renovação se perde no dia em que o cliente abre o boleto e leva um susto. Saber antes é a diferença entre negociar e perder.',
   'auxiliares', 'active', 'scheduled', 'scheduled', false, false, true,
   '{"runtime": {"kind": "none"}, "visibility": {"type": "global"}}'::jsonb, '{}'::jsonb),

  ('sinistralidade-avancada', 'Sinistralidade Avançada',
   'Você entra na negociação sabendo qual seguradora vai apertar',
   array['negociacao']::text[], 'coming_soon',
   array['susep','carteira']::text[],
   '[{"tarefa": "Calcula a sinistralidade de cada seguradora por ramo e por estado", "frequencia": "mensal"},
     {"tarefa": "Compara a SUA carteira com a média da seguradora", "frequencia": "mensal"}]'::jsonb,
   'O argumento na mesa. Vai ser medido em pontos de comissão negociados depois do relatório.',
   'Precisa da ingestão do SES da SUSEP e do espelho da carteira para o comparativo.',
   'mercado', 'Qual seguradora vai apertar, e por que sua carteira vale mais.',
   'A SUSEP publica de graça quanto cada seguradora arrecadou e quanto pagou de sinistro. Quem tem esse número entra na renovação de comissão com evidência, não com opinião.',
   'auxiliares', 'active', 'scheduled', 'scheduled', false, false, true,
   '{"runtime": {"kind": "none"}, "visibility": {"type": "global"}}'::jsonb, '{}'::jsonb),

  ('carteira-blindada', 'Carteira Blindada',
   'O erro na apólice aparece agora, e não no dia do sinistro',
   array['protecao_carteira']::text[], 'coming_soon',
   array['infocap','carteira','fipe']::text[],
   '[{"tarefa": "Confere as apólices emitidas na semana contra os dados do cliente", "frequencia": "semanal"},
     {"tarefa": "Aponta código de referência errado, uso não declarado e vistoria pendente", "frequencia": "semanal"}]'::jsonb,
   'A indenização que seria glosada. Vai ser medida a diferença em reais de cada divergência encontrada.',
   'Precisa do espelho da carteira e de decisão do Founder sobre a fonte de valor de veículo.',
   'operacional', 'Uso não declarado, valor errado, apólice sem vistoria.',
   'O erro de emissão é descoberto no sinistro — meses depois, quando não dá mais para consertar por endosso. Conferir na semana da emissão custa nada.',
   'auxiliares', 'active', 'scheduled', 'scheduled', false, false, true,
   '{"runtime": {"kind": "none"}, "visibility": {"type": "global"}}'::jsonb, '{}'::jsonb),

  ('organizacao-completa', 'Organização Completa',
   'Seu cadastro para de mentir para você',
   array['tempo_livre']::text[], 'coming_soon',
   array['infocap','carteira','whatsapp']::text[],
   '[{"tarefa": "Acha contato inválido, cadastro duplicado e apólice parada na entrega", "frequencia": "semanal"},
     {"tarefa": "Propõe a correção, e só aplica se você aprovar", "frequencia": "semanal"}]'::jsonb,
   'O trabalho que se perde falando com quem não recebe. Vai ser medido o percentual de contatos válidos antes e depois.',
   'Precisa do espelho da carteira.',
   'operacional', 'Contato inválido, cadastro duplicado, apólice parada.',
   'Metade das cobranças que não chegam não é inadimplência: é telefone errado. Cadastro sujo faz todo o resto do sistema trabalhar à toa.',
   'auxiliares', 'active', 'scheduled', 'scheduled', true, false, true,
   '{"runtime": {"kind": "none"}, "visibility": {"type": "global"}}'::jsonb, '{}'::jsonb),

  ('digitacao-zero', 'Digitação Zero',
   'A apólice entra no sistema sozinha, e você só confere',
   array['tempo_livre']::text[], 'coming_soon',
   array['documentos','infocap']::text[],
   '[{"tarefa": "Lê o PDF da apólice que a seguradora mandou", "frequencia": "a cada apólice"},
     {"tarefa": "Preenche o cadastro no sistema da corretora", "frequencia": "a cada apólice"},
     {"tarefa": "Mostra o que preencheu para você conferir antes de gravar", "frequencia": "sempre"}]'::jsonb,
   'As horas de digitação por mês. Vai ser medido o tempo por apólice, antes e depois.',
   'Precisa da API de escrita da InfoCap e da leitura estruturada do PDF da apólice.',
   'operacional', 'Lê o PDF da apólice e preenche o sistema.',
   'A definição estatal do trabalho do auxiliar de seguros tem sete verbos, e todos são de transcrição: transmitir, calcular, conferir, cadastrar, preencher, registrar. É o trabalho que a máquina faz melhor.',
   'auxiliares', 'active', 'scheduled', 'scheduled', true, false, true,
   '{"runtime": {"kind": "none"}, "visibility": {"type": "global"}}'::jsonb, '{}'::jsonb)

on conflict (slug) do update set
  name = excluded.name, headline = excluded.headline,
  categories = excluded.categories, catalog_state = excluded.catalog_state,
  data_sources = excluded.data_sources, what_it_does = excluded.what_it_does,
  value_promise = excluded.value_promise,
  missing_for_launch = excluded.missing_for_launch,
  short_description = excluded.short_description,
  description = excluded.description;
