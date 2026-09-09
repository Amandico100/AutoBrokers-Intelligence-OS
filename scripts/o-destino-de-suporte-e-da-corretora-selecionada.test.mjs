#!/usr/bin/env node
/**
 * O DESTINO DE SUPORTE É DA CORRETORA SELECIONADA — guarda da U1 do
 * `docs/canon/PLANO-HANDOFF-E-PAUSA-2026-09-09.md` (§1-A e §3 U1).
 *
 * 📊 Medido em 09/09/2026: as rotas de Suporte humano resolviam o tenant por
 * `users_v2.company_id` (a corretora PRIMÁRIA do usuário), ignorando o seletor.
 * Efeito na tela do piloto: os dois grupos apareciam nas DUAS corretoras, a
 * AutoFleet ficava sem destino, e o "Desativar" agia na linha da corretora
 * errada — com 200, que é o defeito mais caro que existe aqui.
 *
 * 🔴 Este guarda CHAMA OS HANDLERS DE VERDADE (CLAUDE.md §9.4): importa
 * `route.ts` com hooks de módulo (`node:module` `registerHooks`) que trocam
 * `next/server`, `next/headers`, `iron-session` e `@supabase/supabase-js` por
 * dublês. `resolveSessionCompany` (`lib/auxiliaries/server.ts`) e
 * `companyIdDoSeletor` (`lib/attendance/support-destinations.ts`) rodam como
 * estão no disco — nenhuma regra é reimplementada aqui.
 *
 * ⛔ Nenhuma requisição de rede sai daqui, nenhuma linha de banco é tocada,
 *    nenhum arquivo é escrito. O "banco" é um objeto em memória.
 *
 * A LINHA DE CONTROLE (CLAUDE.md §9.2/§9.3): o mesmo pedido roda com o
 * "resolvedor cego ao seletor" — a sessão sem `activeCompanyId`, que é
 * exatamente o que o `getCompanyId` antigo enxergava (a primária A). Se os
 * resultados NÃO virarem com a mutação, as asserções não medem o resolvedor.
 *
 * Rode: `node scripts/o-destino-de-suporte-e-da-corretora-selecionada.test.mjs`
 */
import { registerHooks } from 'node:module';
import { pathToFileURL } from 'node:url';
import { existsSync, readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const RAIZ = join(dirname(fileURLToPath(import.meta.url)), '..');

// O aviso de "typeless package.json" é do type-stripping do Node ao ler `.ts`;
// não é achado deste guarda e só polui a saída.
process.removeAllListeners('warning');
process.on('warning', () => {});

// ---------------------------------------------------------------------------
// Dublês de módulo. Tudo que NÃO é regra de tenant vira dublê; tudo que É regra
// de tenant (as rotas, `support-destinations.ts`, `auxiliaries/server.ts`) roda
// do disco.
// ---------------------------------------------------------------------------
const DUBLES = new Map([
  [
    'next/server',
    `export class NextRequest {}
     export const NextResponse = {
       json(body, init) {
         return { status: (init && init.status) || 200, async json() { return body; } };
       },
     };`,
  ],
  ['next/headers', `export async function cookies() { return { get: () => undefined }; }`],
  ['iron-session', `export async function getIronSession() { return globalThis.__SESSAO; }`],
  ['@supabase/supabase-js', `export function createClient() { return globalThis.__SUPA; }`],
  [
    '@/lib/iron-session',
    `export const sessionOptions = { password: 'x'.repeat(32), cookieName: 'ab' };
     export const SessionData = undefined;`,
  ],
  [
    '@/lib/attendance/connectors/infocap-policy-lookup',
    `export async function diagnoseInfocapConnection(companyId) {
       globalThis.__DIAG_COMPANY = companyId;
       return { template_found: true, tenant_connection_found: true, status: 'ok', ready_for_real_lookup: true };
     }`,
  ],
]);

registerHooks({
  resolve(spec, ctx, next) {
    if (DUBLES.has(spec)) return { url: `duble:${spec}`, shortCircuit: true, format: 'module' };
    if (spec.startsWith('@/')) {
      const base = join(RAIZ, spec.slice(2));
      for (const ext of ['.ts', '.tsx', '/index.ts']) {
        if (existsSync(base + ext)) return { url: pathToFileURL(base + ext).href, shortCircuit: true };
      }
    }
    return next(spec, ctx);
  },
  load(url, ctx, next) {
    if (url.startsWith('duble:')) {
      return { format: 'module', source: DUBLES.get(url.slice('duble:'.length)), shortCircuit: true };
    }
    return next(url, ctx);
  },
});

// ---------------------------------------------------------------------------
// Placar
// ---------------------------------------------------------------------------
let falhas = 0;
const conferir = (nome, cond, detalhe = '') => {
  if (cond) {
    console.log(`  [ok] ${nome}`);
    return true;
  }
  falhas++;
  console.log(`  [FALHOU] ${nome}${detalhe ? `\n      ${detalhe}` : ''}`);
  return false;
};
const par = (nome, acusou, detalhe = '') => {
  if (acusou) {
    console.log(`  [ok] CONTROLE ${nome} — o resultado virou com a mutação`);
    return true;
  }
  falhas++;
  console.log(`  [FALHOU] CONTROLE ${nome} — nada mudou; a asserção acima é carimbo${detalhe ? `\n      ${detalhe}` : ''}`);
  return false;
};

// ---------------------------------------------------------------------------
// Supabase de mentira: um objeto por tabela, filtros `eq`/`neq` de verdade.
// ---------------------------------------------------------------------------
const A = 'company-A-primaria';
const B = 'company-B-do-seletor';
const C = 'company-C-vinculo-revogado';
const USUARIO = 'u-socio';

function bancoNovo() {
  return {
    users_v2: [{ id: USUARIO, company_id: A }],
    company_members: [
      { user_id: USUARIO, company_id: A, status: 'active' },
      { user_id: USUARIO, company_id: B, status: 'active' },
      // Nenhuma linha para C: é o vínculo revogado.
    ],
    tenant_connections: [],
    human_support_destinations: [
      {
        id: 'dest-da-A',
        company_id: A,
        name: 'Grupo Suporte da A',
        destination_type: 'whatsapp_group',
        channel_provider: 'evolution',
        destination_ref: '11111111111111@g.us',
        display_ref: '111111****11@g.us',
        is_primary: true,
        is_active: true,
        priority_order: 0,
        silence_minutes: 0,
      },
      {
        id: 'dest-da-B',
        company_id: B,
        name: 'Grupo Suporte da B',
        destination_type: 'whatsapp_group',
        channel_provider: 'evolution',
        destination_ref: '22222222222222@g.us',
        display_ref: '222222****22@g.us',
        is_primary: true,
        is_active: true,
        priority_order: 0,
        silence_minutes: 0,
      },
    ],
  };
}

function supabaseDeMentira(db) {
  const executar = (st, modo) => {
    const linhas = db[st.tabela] || (db[st.tabela] = []);
    const casa = (r) => st.filtros.every(([op, c, v]) => (op === 'eq' ? r[c] === v : r[c] !== v));
    let data;
    if (st.op === 'insert') {
      const novas = st.payload.map((p, i) => ({ id: p.id || `novo-${linhas.length + i + 1}`, ...p }));
      linhas.push(...novas);
      data = novas;
    } else if (st.op === 'update') {
      data = linhas.filter(casa);
      for (const r of data) Object.assign(r, st.payload);
    } else {
      data = linhas.filter(casa);
    }
    if (modo === 'muitas') return Promise.resolve({ data, error: null });
    return Promise.resolve({ data: data[0] ?? null, error: null });
  };

  const construtor = (tabela) => {
    const st = { tabela, op: 'select', filtros: [], payload: null };
    const api = {
      select() { return api; },
      insert(rows) { st.op = 'insert'; st.payload = rows; return api; },
      update(fields) { st.op = 'update'; st.payload = fields; return api; },
      eq(c, v) { st.filtros.push(['eq', c, v]); return api; },
      neq(c, v) { st.filtros.push(['neq', c, v]); return api; },
      order() { return api; },
      limit() { return api; },
      maybeSingle() { return executar(st, 'uma'); },
      single() { return executar(st, 'uma'); },
      then(ok, erro) { return executar(st, 'muitas').then(ok, erro); },
    };
    return api;
  };

  return { from: (tabela) => construtor(tabela) };
}

/** Prepara sessão + banco para UM pedido e devolve o banco para inspeção. */
function cenario({ userId = USUARIO, activeCompanyId = null } = {}) {
  const db = bancoNovo();
  globalThis.__SUPA = supabaseDeMentira(db);
  globalThis.__SESSAO = userId ? { userId, ...(activeCompanyId ? { activeCompanyId } : {}) } : {};
  globalThis.__DIAG_COMPANY = undefined;
  return db;
}

const pedidoGet = (qs = '?active=all') => ({ url: `http://local/api/attendance/support-destinations${qs}` });
const pedidoCorpo = (body) => ({ url: 'http://local/api/attendance/support-destinations', json: async () => body });
const rota = (destinationId) => ({ params: Promise.resolve({ destinationId }) });

const { GET, POST } = await import('@/app/api/attendance/support-destinations/route');
const { PATCH, DELETE } = await import('@/app/api/attendance/support-destinations/[destinationId]/route');
const { GET: DIAGNOSTICS } = await import('@/app/api/attendance/connectors/infocap/diagnostics/route');

const corpo = async (res) => ({ status: res.status, body: await res.json() });
const nomes = (body) => (body.destinations || []).map((d) => d.name).sort();

console.log('\n== O destino de suporte é da corretora SELECIONADA (PLANO 09/09 · U1) ==');

// ---------------------------------------------------------------------------
console.log('\n1 - CONTROLE: quem nunca tocou no seletor continua vendo a primária');

cenario({});
{
  const { status, body } = await corpo(await GET(pedidoGet()));
  conferir('GET sem `activeCompanyId` responde 200', status === 200, JSON.stringify(body));
  conferir(
    'e lista APENAS os destinos da corretora primária (A)',
    JSON.stringify(nomes(body)) === JSON.stringify(['Grupo Suporte da A']),
    `listou: ${nomes(body).join(', ') || '(nada)'}`,
  );
}

// ---------------------------------------------------------------------------
console.log('\n2 - Com a B no seletor, a tela é da B — e só da B');

cenario({ activeCompanyId: B });
{
  const { status, body } = await corpo(await GET(pedidoGet()));
  conferir('GET com a B selecionada responde 200', status === 200, JSON.stringify(body));
  conferir(
    'lista APENAS o destino da B — o da A não aparece na tela da B',
    JSON.stringify(nomes(body)) === JSON.stringify(['Grupo Suporte da B']),
    `listou: ${nomes(body).join(', ') || '(nada)'} — 📊 era isto que fazia os dois grupos aparecerem nas duas corretoras`,
  );
}

// 🔴 CONTROLE da 2: o MESMO pedido com o resolvedor cego ao seletor (= o
//    `getCompanyId` antigo, que só via `users_v2.company_id`).
cenario({});
{
  const { body } = await corpo(await GET(pedidoGet()));
  par(
    'a lista muda quando o resolvedor ignora o seletor',
    JSON.stringify(nomes(body)) === JSON.stringify(['Grupo Suporte da A']),
    `com o resolvedor cego a lista deveria ser a da A; veio: ${nomes(body).join(', ')}`,
  );
}

// ---------------------------------------------------------------------------
console.log('\n3 - O POST grava na corretora do seletor');

{
  const db = cenario({ activeCompanyId: B });
  const { status, body } = await corpo(
    await POST(
      pedidoCorpo({
        name: 'Novo grupo da B',
        destination_type: 'whatsapp_group',
        channel_provider: 'evolution',
        destination_ref: '33333333333333@g.us',
      }),
    ),
  );
  conferir('POST responde 201', status === 201, JSON.stringify(body));
  const nova = db.human_support_destinations.find((d) => d.name === 'Novo grupo da B');
  conferir('a linha nasceu com `company_id` da B', Boolean(nova) && nova.company_id === B, `company_id=${nova && nova.company_id}`);
  conferir(
    'e o `destination_ref` cru NÃO volta na resposta',
    !JSON.stringify(body).includes('33333333333333'),
    'a rota devolveu o ref cru — segredo em resposta',
  );
}

// ---------------------------------------------------------------------------
console.log('\n4 - PATCH e DELETE num id da A, com a B selecionada, dão 404');

{
  const db = cenario({ activeCompanyId: B });
  const { status, body } = await corpo(await PATCH(pedidoCorpo({ name: 'sequestrado' }), rota('dest-da-A')));
  conferir('PATCH em `dest-da-A` responde 404', status === 404, `status=${status} body=${JSON.stringify(body)}`);
  const alvo = db.human_support_destinations.find((d) => d.id === 'dest-da-A');
  conferir('e a linha da A ficou INTACTA', alvo.name === 'Grupo Suporte da A', `name=${alvo.name}`);
}

{
  const db = cenario({ activeCompanyId: B });
  const { status, body } = await corpo(await DELETE(pedidoCorpo({}), rota('dest-da-A')));
  conferir('DELETE em `dest-da-A` responde 404', status === 404, `status=${status} body=${JSON.stringify(body)}`);
  const alvo = db.human_support_destinations.find((d) => d.id === 'dest-da-A');
  conferir(
    'e o destino da A continua ATIVO — o "Desativar" não age na corretora errada',
    alvo.is_active === true,
    '📊 09/09: foi assim que o grupo da Resulta caiu enquanto o sócio olhava a tela da AutoFleet',
  );
}

// 🔴 CONTROLE da 4a: o 404 tem de ser do TENANT, não um 404 de sempre.
{
  const db = cenario({ activeCompanyId: B });
  const { status } = await corpo(await PATCH(pedidoCorpo({ name: 'renomeado pela B' }), rota('dest-da-B')));
  conferir('PATCH no próprio destino da B responde 200', status === 200, `status=${status}`);
  conferir(
    'e o nome mudou de verdade',
    db.human_support_destinations.find((d) => d.id === 'dest-da-B').name === 'renomeado pela B',
  );
}

// 🔴 CONTROLE da 4b: com o resolvedor cego ao seletor, o MESMO PATCH em
//    `dest-da-A` passa (era o 200 de 09/09).
{
  const db = cenario({});
  const { status } = await corpo(await PATCH(pedidoCorpo({ name: 'sequestrado' }), rota('dest-da-A')));
  par(
    'o PATCH cross-tenant volta a passar quando o seletor é ignorado',
    status === 200 && db.human_support_destinations.find((d) => d.id === 'dest-da-A').name === 'sequestrado',
    `status=${status} — se continuasse 404 o guarda estaria medindo outra coisa`,
  );
}

// ---------------------------------------------------------------------------
console.log('\n5 - Vínculo revogado NÃO cai na primária');

cenario({ activeCompanyId: C });
{
  const { status, body } = await corpo(await GET(pedidoGet()));
  conferir('GET com vínculo revogado responde 403', status === 403, `status=${status} body=${JSON.stringify(body)}`);
  conferir(
    'e NÃO vaza a lista da corretora primária',
    !JSON.stringify(body).includes('Grupo Suporte da A'),
    'cair na primária devolveria dado da corretora errada com 200',
  );
  conferir(
    'a mensagem é humana e diz o que fazer',
    typeof body.error === 'string' && /seletor/i.test(body.error) && !/undefined|null/.test(body.error),
    `mensagem: ${body.error}`,
  );
}

cenario({ activeCompanyId: C });
{
  const { status } = await corpo(await POST(pedidoCorpo({ name: 'x', destination_type: 'email', destination_ref: 'a@b.com' })));
  conferir('POST com vínculo revogado responde 403 (não escreve)', status === 403, `status=${status}`);
}
cenario({ activeCompanyId: C });
{
  const { status } = await corpo(await DELETE(pedidoCorpo({}), rota('dest-da-A')));
  conferir('DELETE com vínculo revogado responde 403', status === 403, `status=${status}`);
}

console.log('\n6 - Sem sessão, 401 — e o 401 continua sendo 401');
cenario({ userId: null });
{
  const { status } = await corpo(await GET(pedidoGet()));
  conferir('GET sem `userId` responde 401', status === 401, `status=${status}`);
}

// ---------------------------------------------------------------------------
console.log('\n7 - O diagnóstico do InfoCap também é da corretora do seletor');

cenario({ activeCompanyId: B });
{
  const { status } = await corpo(await DIAGNOSTICS({ url: 'http://local/api/attendance/connectors/infocap/diagnostics' }));
  conferir('diagnostics responde 200', status === 200, `status=${status}`);
  conferir(
    'e o diagnóstico rodou sobre a B, não sobre a primária A',
    globalThis.__DIAG_COMPANY === B,
    `rodou sobre: ${globalThis.__DIAG_COMPANY}`,
  );
}

cenario({ activeCompanyId: C });
{
  const { status } = await corpo(await DIAGNOSTICS({ url: 'http://local/api/attendance/connectors/infocap/diagnostics' }));
  conferir('diagnostics com vínculo revogado responde 403', status === 403, `status=${status}`);
  conferir('e nem chega a diagnosticar nada', globalThis.__DIAG_COMPANY === undefined);
}

// ---------------------------------------------------------------------------
console.log('\n8 - O resolvedor antigo não pode voltar pela porta dos fundos');

const semComentarios = (src) =>
  src
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/\{\/\*[\s\S]*?\*\/\}/g, '')
    .replace(/^\s*\/\/.*$/gm, '');

const ARQUIVOS = [
  'lib/attendance/support-destinations.ts',
  'app/api/attendance/support-destinations/route.ts',
  'app/api/attendance/support-destinations/[destinationId]/route.ts',
  'app/api/attendance/connectors/infocap/diagnostics/route.ts',
];
const acusaUsersV2 = (src) => /users_v2/.test(semComentarios(src));
for (const rel of ARQUIVOS) {
  const src = readFileSync(join(RAIZ, rel), 'utf8');
  conferir(`\`${rel}\` não lê \`users_v2\` para achar a corretora`, !acusaUsersV2(src));
}
// 🔴 CONTROLE: a leitura acima tem de conseguir ficar VERMELHA.
{
  const envenenado = readFileSync(join(RAIZ, ARQUIVOS[0]), 'utf8').replace(
    'export const SEM_CORRETORA_NA_SESSAO',
    "const volta = (s) => s.from('users_v2');\nexport const SEM_CORRETORA_NA_SESSAO",
  );
  par('o guarda de fonte acusa um `users_v2` reintroduzido', acusaUsersV2(envenenado));
}

// ---------------------------------------------------------------------------
console.log('\n9 - A tela marca o destino desativado e avisa quando não há nenhum');

const TELA = 'app/dashboard/personalizacao/corretora/suporte-humano/HumanSupportSettingsClient.tsx';
const tela = semComentarios(readFileSync(join(RAIZ, TELA), 'utf8'));
conferir("o destino inativo é rotulado 'Desativado'", /label=\{d\.is_active \? 'Ativo' : 'Desativado'\}/.test(tela));
conferir('e fica visualmente apagado', /d\.is_active \? '' : 'opacity-60'/.test(tela));
conferir(
  'a lista vazia avisa que nenhum handoff sai',
  /Esta corretora ainda não tem destino de suporte\. Enquanto isso, nenhum handoff sai\./.test(tela),
);
par('o texto lido é o da tela (e não casa com a frase antiga)', !/Nenhum destino configurado ainda/.test(tela));

// ---------------------------------------------------------------------------
console.log(`\n== ${falhas === 0 ? 'TUDO VERDE' : `${falhas} FALHA(S)`} ==`);
process.exit(falhas === 0 ? 0 : 1);
