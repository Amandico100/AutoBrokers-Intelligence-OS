-- =============================================================
-- MIGRATION: 20261014_02_spec132b_cotacao_rapida
-- SPEC:      SPEC-132-B — B3 · o aplicativo (D-132B-06/07)
-- AUTOR:     builder B3 (Opus 5.5)            DATA: 2026-10-14
-- OBJETIVO:  os nomes que o Founder escolheu ("Cotação Rápida" e "Renovação Automática") e o texto da Cotação Rápida
--            (o que é, o que faz e as dúvidas reais do corretor) no catálogo GLOBAL de aplicativos.
--
-- 📊 ANTES (BLOCO 0 C10 da SPEC, 14/10/2026): `auxiliary_templates` slug `cotacao` name 'Cotação' ativo (faq nula) ·
--    slug `renovacao` name 'Renovação' ativo — as duas linhas nasceram na 20261014_01 (APLICADA; não se edita: §8.8).
--
-- APPLY (pelo GERENTE — o builder NÃO aplica; um arquivo, idempotente, expand-only, global):
--   A. `renovacao`: name 'Renovação' → 'Renovação Automática' (só o nome; a página do cliente continua dizendo
--      "Renovação do seguro" — ela não lê esta coluna).
--   B. `cotacao`: name → 'Cotação Rápida' · short_description · description · headline · what_it_does · value_promise ·
--      faq (7 perguntas). Nenhum nome de corretora ou de pessoa (CLAUDE.md §13.9). Cada UPDATE só toca a linha cujo
--      valor ainda é diferente (rodar de novo não muda nada, nem o updated_at).
--   ⛔ Nenhuma coluna, nenhuma trava, nenhum GRANT: só o TEXTO de duas linhas (o CHECK `ck_aux_templates_faq` exige
--      lista — o faq abaixo é lista).
--
-- VERIFY (read-only · esperado: 1 · 1 · 7 · 0 · 0):
--   select (select count(*) from public.auxiliary_templates where slug='cotacao' and name='Cotação Rápida'
--             and is_active and status='active') cotacao_rapida,
--          (select count(*) from public.auxiliary_templates where slug='renovacao' and name='Renovação Automática'
--             and is_active and status='active') renovacao_automatica,
--          (select jsonb_array_length(faq) from public.auxiliary_templates where slug='cotacao') duvidas_da_cotacao,
--          (select count(*) from public.auxiliary_templates where slug in ('cotacao','renovacao')
--             and name in ('Cotação','Renovação')) nomes_antigos,
--          (select count(*) from public.auxiliary_templates t, jsonb_array_elements(t.faq) d
--             where t.slug='cotacao' and (coalesce(d->>'pergunta','')='' or coalesce(d->>'resposta','')='')) duvida_vazia;
--
-- ROLLBACK (escrito ANTES; devolve EXATAMENTE os textos da 20261014_01):
--   update public.auxiliary_templates set name = 'Renovação', updated_at = now() where slug = 'renovacao';
--   update public.auxiliary_templates set
--     name = 'Cotação',
--     short_description = 'O cálculo de um seguro novo no Agger, com as regras que a corretora escolher.',
--     description = E'Quando alguém da corretora pede uma cotação, o AutoBrokers calcula no Agger e monta a comparação das opções para o cliente.\n\nAqui você escolhe as regras da cotação. Elas valem só para cotação: a renovação e o Quem Cobra Menos têm as regras deles.',
--     headline = 'O cálculo do seguro novo sai no Agger com as regras da sua corretora',
--     what_it_does = '[{"tarefa": "Calcula no Agger a cotação que alguém da corretora pediu", "frequencia": "quando você pedir"},
--       {"tarefa": "Monta a comparação das opções calculadas para o cliente", "frequencia": "a cada cotação"}]'::jsonb,
--     value_promise = 'As regras da cotação ficam num lugar só e valem só para cotação. Quando houver cotações calculadas pelo AutoBrokers, o número aparece aqui.',
--     faq = null,
--     updated_at = now()
--   where slug = 'cotacao';
--
-- EXPAND-FIRST: sim (só UPDATE de texto de catálogo; nenhuma estrutura)
-- DESTRUTIVA:   não (o ROLLBACK devolve os valores de antes, byte a byte)
-- =============================================================

-- A. a Renovação passa a se chamar Renovação Automática (D-132B-07, Founder) -----------------------------------------
update public.auxiliary_templates
   set name = 'Renovação Automática', updated_at = now()
 where slug = 'renovacao' and name is distinct from 'Renovação Automática';

-- B. a Cotação Rápida: o nome, o que é, o que faz e as dúvidas do corretor ----------------------------------------------
update public.auxiliary_templates as t
   set name = v.name, short_description = v.short_description, description = v.description, headline = v.headline,
       what_it_does = v.what_it_does, value_promise = v.value_promise, faq = v.faq, updated_at = now()
  from (values (
    'Cotação Rápida',
    'Peça no chat — escrevendo, mandando a apólice, uma foto ou um áudio — e receba a cotação pronta, com a apresentação para o cliente.',
    E'Peça no chat — escrevendo, mandando a apólice, uma foto ou um áudio — e receba a cotação pronta, com a apresentação para o cliente.\n\nO AutoBrokers pergunta só o que falta, mostra o resumo para você confirmar e calcula no seu Agger. Em poucos minutos volta, na mesma conversa, com as opções e o link da apresentação, com a cara da sua corretora, pronto para você mandar ao cliente. Nada sai sozinho para o cliente.',
    'Peça no chat e receba a cotação pronta, com a apresentação para mandar ao cliente',
    '[{"tarefa": "Entende o pedido escrito, a apólice, a foto do documento ou o áudio, e pergunta só o que falta", "frequencia": "a cada pedido"},
      {"tarefa": "Calcula no seu Agger as versões que a corretora escolheu", "frequencia": "quando você confirmar"},
      {"tarefa": "Volta na mesma conversa com as opções e o link da apresentação para o cliente", "frequencia": "a cada cotação"},
      {"tarefa": "Guarda cada cotação na aba Cotações, para você rever e enviar pelo seu WhatsApp", "frequencia": "sempre"}]'::jsonb,
    'Você pede em uma frase e recebe a cotação pronta para mandar. Quando houver cotações calculadas pelo AutoBrokers, o número aparece aqui.',
    '[{"pergunta": "De onde vem o cálculo?", "resposta": "Do Agger, o mesmo multicálculo que a sua corretora já usa. O AutoBrokers preenche o pedido, pede o cálculo às seguradoras habilitadas na conta e lê as respostas. Nenhum preço é inventado: o que aparece é o que cada seguradora devolveu."},
      {"pergunta": "Em qual Agger a cotação é feita?", "resposta": "No seu, se você conectou o seu Agger em Meu perfil: assim o cálculo já fica na sua conta. Se ainda não conectou, sai no Agger da corretora, e a resposta avisa."},
      {"pergunta": "Quanto tempo leva?", "resposta": "Costuma ficar pronta em 1 a 2 minutos. Algumas seguradoras demoram mais; se passar de alguns minutos, a resposta vem com as que já responderam."},
      {"pergunta": "Posso pedir a cotação pelo WhatsApp?", "resposta": "Em breve. Por enquanto, peça pelo chat do AutoBrokers, no computador ou no celular."},
      {"pergunta": "O que o cliente recebe?", "resposta": "Nada sozinho. Você recebe as opções e o link de uma apresentação com a marca da sua corretora. Você confere, copia a mensagem ou toca em Enviar pelo WhatsApp, e ela abre no seu próprio WhatsApp."},
      {"pergunta": "Posso ajustar as regras do cálculo?", "resposta": "Sim. Em Configurar você vê todas as regras da cotação e escolhe quais versões calcular, a comissão de entrada e por quantos dias a cotação vale. O resto segue o padrão do AutoBrokers."},
      {"pergunta": "Dá para cotar residencial, condomínio e empresarial?", "resposta": "Sim, além do carro. Nesses seguros a cotação compara as seguradoras pelas mesmas coberturas essenciais, para nenhuma parecer mais barata por cobrir menos."}]'::jsonb
  )) as v(name, short_description, description, headline, what_it_does, value_promise, faq)
 where t.slug = 'cotacao'
   and (t.name, t.short_description, t.description, t.headline, t.what_it_does, t.value_promise, t.faq)
       is distinct from (v.name, v.short_description, v.description, v.headline, v.what_it_does, v.value_promise, v.faq);
