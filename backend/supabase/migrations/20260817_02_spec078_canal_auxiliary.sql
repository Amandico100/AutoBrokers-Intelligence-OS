-- =============================================================
-- MIGRATION: spec078_canal_auxiliary
-- SPEC:      SPEC-078 — Bloco B, REDESENHADO depois de medir o banco vivo
-- AUTOR:     Claude Opus 5                     DATA: 2026-08-17
-- OBJETIVO:  Dar à corretora um jeito de AUTORIZAR, com os olhos abertos, que
--            os Auxiliares (cobrança, relatórios) enviem pelo número que ela
--            pareou — sem afrouxar a proibição da SPEC-063 D para ninguém.
--
-- APPLY:     ⛔ NÃO APLICADA. Escrita para o Founder aplicar.
-- VERIFY:    bloco ao final (SELECTs prontos, com a saída esperada).
-- ROLLBACK:  bloco ao final (`drop column`; a coluna é aditiva e isolada).
--
-- EXPAND-FIRST: sim  — só acrescenta coluna, com default que preserva o hoje.
-- DESTRUTIVA:   não  — nada é apagado, nada é reescrito, nada é ligado.
-- =============================================================

-- -------------------------------------------------------------------------
-- POR QUE UMA COLUNA, E NÃO UMA SEGUNDA LINHA EM `integrations`
--
-- O desenho original desta SPEC (§4, Decisão 2, nota 91) era criar uma linha
-- irmã `purpose='auxiliary'` para o mesmo número. 📊 Medido em 17/08/2026 no
-- projeto dcajcvlzcjbmyapmklil, ele NÃO CABE no schema:
--
--     integrations_provider_identifier_key  UNIQUE (provider, identifier)
--
-- E `identifier` não é o telefone: é o NOME DA INSTÂNCIA Evolution.
--
--     AMANDUS SEGUROS   evolution-go  observer  ab-obs-3aa75902a3-1  ativa
--     AutoFleet         evolution-go  observer  ab-obs-6c9c55e22f-1  ativa
--     Resulta Seguros   evolution-go  observer  ab-obs-04b5cdbc04-1  INATIVA
--
-- Duas linhas para o mesmo número exigiriam o MESMO `identifier` — é a mesma
-- instância — e bateriam na unique. Derivar um identifier novo
-- (`...-1#auxiliary`) seria escrever no banco o nome de uma instância que não
-- existe no Evolution, e `channel_identity.py` diz por que isso é caro: o nome
-- da instância é metade da chave de dedup de 📊 86.801 linhas de acervo.
--
-- **Duas linhas: nota 45.** Briga com a unique e inventa instância.
--
-- **Opt-in explícito: nota 88.** Uma linha, uma verdade. A proibição continua
-- sendo o padrão, e quem decide abrir a exceção é a corretora, não o código.
--
-- E isto não desfaz a SPEC-063 D — lê o motivo dela literalmente
-- (`integration_service.py:185-192`):
--
--     "Cobrança, follow-up e alerta sairiam pelo número que existe para ficar
--      calado. O segurado receberia mensagem de um número que nunca falou com
--      ele, e a corretora perderia o silêncio que pediu ao parear."
--
-- A proteção é contra SURPRESA, não contra envio. Aqui não há surpresa: alguém
-- clicou, num botão que descreve exatamente o que vai acontecer. O que continua
-- proibido — e continua proibido por omissão — é o sistema escolher sozinho.
-- -------------------------------------------------------------------------

-- 1. A coluna. `default false` é o ponto inteiro desta migration: no instante
--    seguinte ao APPLY, o comportamento do produto é byte a byte o de hoje.
--    Nenhuma das 📊 7 linhas existentes (2 ativas, as duas `observer`) ganha
--    canal de saída. Nenhum backfill liga nada — backfill que liga seria a
--    surpresa que a SPEC-063 D proíbe, entrando pela porta dos fundos.
alter table public.integrations
  add column if not exists permite_envio_de_auxiliar boolean not null default false;

-- 2. O que a coluna quer dizer, escrito no banco — para quem abrir a tabela
--    daqui a um ano sem esta migration na mão.
comment on column public.integrations.permite_envio_de_auxiliar is
  'SPEC-078 B: a corretora AUTORIZOU que os Auxiliares (cobranca, relatorios) '
  'enviem por este numero. So tem efeito em pode_enviar(..., para="auxiliar"). '
  'NAO libera resposta de atendimento (isso e o Agente de Atendimento) e NAO '
  'libera envio de plataforma. Default false: a proibicao da SPEC-063 D '
  'continua sendo o padrao para todo mundo.';

-- =============================================================
-- VERIFY — rodar DEPOIS do APPLY. Saída esperada ao lado de cada um.
--
-- (a) a coluna existe, é boolean, NOT NULL e default false
--     -> 1 linha: permite_envio_de_auxiliar | boolean | NO | false
--
-- select column_name, data_type, is_nullable, column_default
--   from information_schema.columns
--  where table_schema='public' and table_name='integrations'
--    and column_name='permite_envio_de_auxiliar';
--
-- (b) 🔴 NINGUÉM ganhou canal por causa desta migration
--     -> 0 linhas. Qualquer linha aqui é um backfill que não devia existir.
--
-- select id, company_id, purpose, identifier
--   from public.integrations where permite_envio_de_auxiliar is true;
--
-- (c) a foto de antes continua de pé (nada foi desativado nem trocado)
--     -> 📊 esperado em 17/08/2026: 7 linhas, 2 ativas, ambas purpose=observer
--
-- select count(*) total, count(*) filter (where is_active) ativas,
--        count(*) filter (where is_active and purpose='observer') observadores
--   from public.integrations;
--
-- (d) COMO LIGAR para uma corretora, quando o Founder decidir (não é parte do
--     APPLY — é o comando equivalente ao botão da tela):
--
-- update public.integrations set permite_envio_de_auxiliar = true
--  where company_id = '<uuid da corretora>' and provider = 'evolution-go'
--    and purpose = 'observer' and is_active = true;
-- =============================================================

-- =============================================================
-- ROLLBACK
--
-- A coluna é aditiva e não é lida por nada que exista antes desta SPEC, então
-- derrubá-la devolve o estado anterior sem perda: o único dado que ela guarda
-- é a própria autorização, e reverter a SPEC é justamente retirar a autorização.
--
-- alter table public.integrations drop column if exists permite_envio_de_auxiliar;
--
-- ⚠️ Se o rollback for parcial (código novo no ar, coluna fora), o
-- `pode_enviar(..., para="auxiliar")` lê `None` e devolve False: o produto volta
-- a não enviar. Fail-closed dos dois lados — nunca o contrário.
-- =============================================================
