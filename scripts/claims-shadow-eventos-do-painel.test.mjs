#!/usr/bin/env node
/**
 * SPEC-093-B · BLOCO B (lado NEXT) — gates ① ② ③ ⑥.
 *
 * 🔴 O DEFEITO QUE ESTE ARQUIVO EXISTE PARA IMPEDIR: um gesto da atendente que
 * não vira linha, ou que vira linha com o texto do segurado dentro.
 *
 * ⚠️ Ele chama o **MOTOR** (`criarRegistradorDaSombra`) com um cliente Supabase
 * FALSO, e afirma sobre o que chegou ao `insert` — nunca sobre o retorno da
 * função (CLAUDE.md §9.4). O registrador engole exceção de propósito: um INSERT
 * recusado pelo CHECK sumiria, e um teste que lesse o retorno ficaria verde.
 *
 * ⚠️ O vocabulário é lido do MESMO arquivo que o `route.ts` importa e que o
 * Python lê por caminho — `lib/atendimento/claims-shadow-vocab.json`. Aqui via
 * `readFileSync` porque o TypeScript do repo é 5.2.2 (sem `import … with
 * { type: 'json' }`) e o Node é 24 (que EXIGE o atributo em ESM): nenhuma das
 * duas formas serve aos dois, então o JSON entra por injeção nos dois lados.
 *
 *   node scripts/claims-shadow-eventos-do-painel.test.mjs
 */
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  anotacaoTemNumero,
  criarRegistradorDaSombra,
  validarGestoDaSombra,
} from '../lib/atendimento/claims-shadow.ts';

const RAIZ = join(dirname(fileURLToPath(import.meta.url)), '..');
const VOCAB = JSON.parse(
  readFileSync(join(RAIZ, 'lib', 'atendimento', 'claims-shadow-vocab.json'), 'utf8'),
);
const ROTA = readFileSync(
  join(RAIZ, 'app', 'api', 'dashboard', 'conversas', '[id]', 'route.ts'),
  'utf8',
);

let ok = 0;
const falhas = [];
function certo(nome, cond, detalhe = '') {
  if (cond) {
    ok++;
    console.log(`  ok    ${nome}`);
  } else {
    falhas.push(nome);
    console.log(`  FALHA ${nome}${detalhe ? `\n        ${detalhe}` : ''}`);
  }
}

/**
 * O cliente FALSO. Registra tudo o que passou por ele — é isso que dá direito à
 * conclusão: sem o registro, "0 inserts" pode ser um falso que não sabe ver um
 * insert (o bloco [8] prova que ele sabe).
 *
 * `sombraPorCompany`: qual `work_run` existe para cada `company_id`. É assim que
 * o teste de dois tenants funciona sem banco.
 */
function clienteFalso({ sombraPorCompany = {}, erroNoInsert = null } = {}) {
  const chamadas = { selects: [], inserts: [] };
  return {
    chamadas,
    from(tabela) {
      if (tabela === 'work_events') {
        return {
          insert(linha) {
            chamadas.inserts.push({ tabela, linha });
            return Promise.resolve({ error: erroNoInsert });
          },
        };
      }
      const filtros = {};
      const q = {
        select(colunas) {
          q.colunas = colunas;
          return q;
        },
        eq(coluna, valor) {
          filtros[coluna] = valor;
          return q;
        },
        order() {
          return q;
        },
        limit() {
          chamadas.selects.push({ tabela, colunas: q.colunas, filtros: { ...filtros } });
          const run = sombraPorCompany[filtros.company_id];
          const casa = run && filtros.conversation_id && filtros.workflow_key === 'claims.shadow';
          return Promise.resolve({ data: casa ? [{ id: run }] : [], error: null });
        },
      };
      return q;
    },
  };
}

const registrar = criarRegistradorDaSombra(VOCAB);
const A = { companyId: 'COMPANY-A', conversationId: 'CONV-1' };

console.log('='.repeat(78));
console.log('  OS GESTOS DA ATENDENTE VIRAM EVENTO -- SPEC-093-B BLOCO B (lado Next)');
console.log('='.repeat(78));

// ---------------------------------------------------------------------------
// [1] gate ① + ⑥ — cada gesto produz UMA linha, com o event_type do vocabulário
// ---------------------------------------------------------------------------
console.log('\n[1] com sombra, cada gesto grava UMA linha');
{
  const casos = [
    ['claims.humano_assumiu', { origem: 'dashboard' }, 'a atendente assumiu o caso'],
    ['claims.humano_devolveu', { origem: 'dashboard' }, 'a atendente devolveu o caso ao atendente IA'],
    ['claims.encerrado', { desfecho: 'desconhecido' }, 'o caso foi encerrado pela atendente'],
    ['claims.humano_respondeu', { canal: 'dashboard' }, 'a atendente respondeu pelo painel'],
    [
      'claims.nota_registrada',
      { origem: 'dashboard', tem_numero: true },
      'a atendente registrou uma anotação interna',
    ],
  ];
  for (const [eventType, payload, mensagem] of casos) {
    const cli = clienteFalso({ sombraPorCompany: { 'COMPANY-A': 'RUN-A' } });
    const r = await registrar(cli, { ...A, eventType, payload });
    const linha = cli.chamadas.inserts[0]?.linha;
    certo(
      `${eventType}: UMA linha em work_events`,
      cli.chamadas.inserts.length === 1,
      `inserts=${cli.chamadas.inserts.length} · retorno=${JSON.stringify(r)}`,
    );
    certo(`${eventType}: event_type do vocabulário`, linha?.event_type === eventType);
    certo(
      `${eventType}: actor_type '${VOCAB.eventos[eventType].ator}' do CHECK`,
      linha?.actor_type === VOCAB.eventos[eventType].ator &&
        VOCAB.atores_do_check.includes(linha?.actor_type),
    );
    certo(`${eventType}: work_run_id é a sombra achada`, linha?.work_run_id === 'RUN-A');
    certo(`${eventType}: company_id no INSERT (§7)`, linha?.company_id === 'COMPANY-A');
    certo(`${eventType}: message_human é o template`, linha?.message_human === mensagem);
    certo(`${eventType}: severity info`, linha?.severity === 'info');
    certo(
      `${eventType}: payload_redacted só com as chaves declaradas`,
      JSON.stringify(Object.keys(linha?.payload_redacted || {}).sort()) ===
        JSON.stringify([...VOCAB.eventos[eventType].payload].sort()),
      `veio ${JSON.stringify(linha?.payload_redacted)}`,
    );
  }
}

// ---------------------------------------------------------------------------
// [2] gate ③ — conversa SEM sombra não escreve nada. E o SELECT foi feito.
// ---------------------------------------------------------------------------
console.log('\n[2] sem sombra, o gesto NAO grava (nada de sombra retroativa)');
{
  const cli = clienteFalso({ sombraPorCompany: {} });
  const r = await registrar(cli, {
    ...A,
    eventType: 'claims.humano_assumiu',
    payload: { origem: 'dashboard' },
  });
  certo('ZERO inserts', cli.chamadas.inserts.length === 0);
  certo('o motivo é "conversa sem sombra"', r.gravado === false && r.motivo === 'conversa sem sombra');
  certo(
    'CONTROLE: o falso VIU o select (não é um falso cego)',
    cli.chamadas.selects.length === 1 && cli.chamadas.selects[0].tabela === 'work_runs',
    JSON.stringify(cli.chamadas.selects),
  );
  const f = cli.chamadas.selects[0].filtros;
  certo(
    'o SELECT filtra company_id + conversation_id + workflow_key',
    f.company_id === 'COMPANY-A' &&
      f.conversation_id === 'CONV-1' &&
      f.workflow_key === VOCAB.workflow_key,
    JSON.stringify(f),
  );
}

// ---------------------------------------------------------------------------
// [3] gate ② — payload só com chaves e valores do vocabulário
// ---------------------------------------------------------------------------
console.log('\n[3] payload fora do vocabulario e RECUSADO antes do banco');
{
  const recusas = [
    ['chave intrusa', 'claims.humano_assumiu', { origem: 'dashboard', texto: 'bateu o carro' }],
    ['SÓ a chave intrusa', 'claims.humano_assumiu', { texto: 'bateu o carro' }],
    ['valor fora do enum', 'claims.humano_assumiu', { origem: 'telepatia' }],
    ['qualificador ausente', 'claims.nota_registrada', { origem: 'dashboard' }],
    ['desfecho inventado', 'claims.encerrado', { desfecho: 'resolvido_no_zap' }],
    ['event_type inexistente', 'claims.humano_deu_bom_dia', { origem: 'dashboard' }],
    ['event_type que é do Python', 'claims.documento_recebido', { tipo_documento: 'cnh' }],
  ];
  for (const [nome, eventType, payload] of recusas) {
    const cli = clienteFalso({ sombraPorCompany: { 'COMPANY-A': 'RUN-A' } });
    const r = await registrar(cli, { ...A, eventType, payload });
    certo(
      `${nome}: ZERO inserts`,
      cli.chamadas.inserts.length === 0 && r.gravado === false,
      `inserts=${cli.chamadas.inserts.length} · ${JSON.stringify(r)}`,
    );
  }
  certo(
    'a recusa acontece ANTES do banco (nem o SELECT da sombra roda)',
    (await (async () => {
      const cli = clienteFalso({ sombraPorCompany: { 'COMPANY-A': 'RUN-A' } });
      await registrar(cli, {
        ...A,
        eventType: 'claims.humano_assumiu',
        payload: { origem: 'dashboard', texto: 'x' },
      });
      return cli.chamadas.selects.length;
    })()) === 0,
  );
}

// ---------------------------------------------------------------------------
// [4] MUTAÇÃO — texto livre por uma chave LEGÍTIMA
// ---------------------------------------------------------------------------
console.log('\n[4] MUTACAO: texto livre entrando por chave que o vocabulario aceita');
{
  // `ramo` e `seguradora_slug` não são enum: se a única regra fosse o tamanho,
  // uma frase curta passaria. Aqui a forma de slug é que barra.
  const frase = 'o cliente bateu o carro';
  const r = validarGestoDaSombra(VOCAB, 'claims.sombra_aberta', {
    confianca: 'alta',
    motivo: 'servico_sinistro',
    ramo: frase,
    seguradora_slug: 'porto',
  });
  certo(
    'uma FRASE em `ramo` (23 chars, < 64) é recusada pela forma de slug',
    r.ok === false,
    JSON.stringify(r),
  );
  const bom = validarGestoDaSombra(VOCAB, 'claims.encerrado', { desfecho: 'desconhecido' });
  certo('CONTROLE: o casador CONSEGUE aprovar (um gesto legítimo passa)', bom.ok === true);
}

// ---------------------------------------------------------------------------
// [5] gate ④ — DOIS TENANTS
// ---------------------------------------------------------------------------
console.log('\n[5] dois tenants: a sombra da A nao serve ao gesto da B');
{
  const cli = clienteFalso({ sombraPorCompany: { 'COMPANY-A': 'RUN-A' } });
  const naB = await registrar(cli, {
    companyId: 'COMPANY-B',
    conversationId: 'CONV-1',
    eventType: 'claims.humano_assumiu',
    payload: { origem: 'dashboard' },
  });
  certo('a B não grava na sombra da A', cli.chamadas.inserts.length === 0 && naB.gravado === false);

  const cli2 = clienteFalso({ sombraPorCompany: { 'COMPANY-A': 'RUN-A', 'COMPANY-B': 'RUN-B' } });
  await registrar(cli2, {
    companyId: 'COMPANY-B',
    conversationId: 'CONV-1',
    eventType: 'claims.humano_assumiu',
    payload: { origem: 'dashboard' },
  });
  certo(
    'CONTROLE: com sombra própria, a B grava — e no RUN dela',
    cli2.chamadas.inserts.length === 1 &&
      cli2.chamadas.inserts[0].linha.work_run_id === 'RUN-B' &&
      cli2.chamadas.inserts[0].linha.company_id === 'COMPANY-B',
  );
}

// ---------------------------------------------------------------------------
// [6] a sombra NUNCA derruba o gesto
// ---------------------------------------------------------------------------
console.log('\n[6] a sombra nunca lanca -- o gesto do painel nao depende dela');
{
  const cliQuebrado = {
    from() {
      throw new Error('banco fora do ar');
    },
  };
  let explodiu = false;
  let r = null;
  try {
    r = await registrar(cliQuebrado, {
      ...A,
      eventType: 'claims.humano_assumiu',
      payload: { origem: 'dashboard' },
    });
  } catch {
    explodiu = true;
  }
  certo('cliente que explode não propaga exceção', explodiu === false && r?.gravado === false);

  const cliErro = clienteFalso({
    sombraPorCompany: { 'COMPANY-A': 'RUN-A' },
    erroNoInsert: { message: 'violates check constraint' },
  });
  const r2 = await registrar(cliErro, {
    ...A,
    eventType: 'claims.humano_assumiu',
    payload: { origem: 'dashboard' },
  });
  certo(
    'INSERT recusado pelo banco vira `gravado:false` com o motivo, não silêncio',
    r2.gravado === false && String(r2.motivo).includes('check constraint'),
  );
}

// ---------------------------------------------------------------------------
// [7] `tem_numero` — o único resíduo da anotação
// ---------------------------------------------------------------------------
console.log('\n[7] tem_numero e um BOOLEANO, e o texto nao entra');
{
  certo('protocolo de 6+ dígitos → true', anotacaoTemNumero('#nota protocolo 4471902'));
  certo('5 dígitos não é protocolo → false', anotacaoTemNumero('#nota sala 12345') === false);
  certo('sem número → false', anotacaoTemNumero('#nota o robô repetiu a pergunta') === false);
  const cli = clienteFalso({ sombraPorCompany: { 'COMPANY-A': 'RUN-A' } });
  await registrar(cli, {
    ...A,
    eventType: 'claims.nota_registrada',
    payload: { origem: 'dashboard', tem_numero: anotacaoTemNumero('#nota protocolo 4471902 do José') },
  });
  const p = cli.chamadas.inserts[0].linha.payload_redacted;
  certo('o payload leva o booleano, não o número', p.tem_numero === true);
  certo(
    'nenhum valor do payload contém o texto da nota',
    !JSON.stringify(cli.chamadas.inserts[0].linha).includes('4471902') &&
      !JSON.stringify(cli.chamadas.inserts[0].linha).includes('José'),
    JSON.stringify(cli.chamadas.inserts[0].linha),
  );
}

// ---------------------------------------------------------------------------
// [8] CONTROLE do próprio falso — ele CONSEGUE ver um insert
// ---------------------------------------------------------------------------
console.log('\n[8] CONTROLE: o cliente falso enxerga um insert');
{
  const cli = clienteFalso();
  await cli.from('work_events').insert({ event_type: 'teste.controle' });
  certo(
    'um insert direto no falso aparece em `chamadas.inserts`',
    cli.chamadas.inserts.length === 1 &&
      cli.chamadas.inserts[0].linha.event_type === 'teste.controle',
  );
}

// ---------------------------------------------------------------------------
// [9] a FIAÇÃO existe na rota — o motor sem chamador não guarda nada
// ---------------------------------------------------------------------------
console.log('\n[9] a rota do painel chama o registrador nos cinco gestos');
{
  for (const evento of [
    'claims.humano_assumiu',
    'claims.humano_devolveu',
    'claims.encerrado',
    'claims.nota_registrada',
    'claims.humano_respondeu',
  ]) {
    certo(`route.ts registra ${evento}`, ROTA.includes(`eventType: '${evento}'`));
  }
  certo(
    'route.ts importa o vocabulário do arquivo único',
    ROTA.includes("from '@/lib/atendimento/claims-shadow-vocab.json'"),
  );
  certo(
    'CONTROLE: um event_type que a rota NÃO escreve não aparece no fonte',
    !ROTA.includes("eventType: 'claims.documento_recebido'"),
  );
}

console.log('\n' + '='.repeat(78));
console.log(`  ${ok} ok · ${falhas.length} falhas`);
if (falhas.length) console.log('  ' + falhas.join('\n  '));
console.log('='.repeat(78));
process.exit(falhas.length ? 1 : 0);
