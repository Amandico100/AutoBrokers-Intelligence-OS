// ===========================================================================
// SPEC-131-0 parte A · F1 — MEMBROS: funções de trabalho, papel fechado, UMA fonte do papel
// ===========================================================================
//
// 🔴 O DEFEITO QUE ESTE ARQUIVO GUARDA (mapa do código §0.2, 11/10/2026)
// O login grava `activeCompanyId = null`; sem empresa ativa, `requireCompanyMember` lia o papel de `users_v2.role` —
// mas o PATCH da equipe muda `company_members.role`. Quem fosse rebaixado de Administrador para Membro continuava
// administrando. Agora o papel vem SÓ do vínculo (`company_members`) da empresa primária, e sem vínculo ativo nega.
//
// 🔴 COMO: a rota REAL (`app/api/dashboard/team/route.ts`) roda sobre o `requireCompanyMember` REAL e a política REAL,
// sobre um banco falso com DUAS corretoras e com os CHECKs do banco — os do `company_members` LIDOS DA MIGRATION
// (`20261011_02_spec1310_membros.sql`), o do `users_v2.role` medido no catálogo. Dublê só na borda: sessão, hash,
// URL do backend e o `fetch` do desligamento do Agger.
//
// ⛔ LINHA DE CONTROLE (CLAUDE.md §9.2/§9.3): o bloco ③ mede o papel nos DOIS sentidos (users_v2 admin × vínculo
// membro, e o contrário). Se o código voltar a ler `users_v2.role`, os dois ficam vermelhos — o guarda consegue falhar.
// §13.9: corretora_a/corretora_b, membro_a/membro_b — nenhum nome real.
import fs from 'node:fs';
import path from 'node:path';
import nodeCrypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import ts from 'typescript';

const RAIZ = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

let pass = 0, fail = 0;
function assert(nome, cond) {
  if (cond) { pass++; } else { fail++; console.log('  x ' + nome); }
}
const igual = (a, b) => JSON.stringify(a) === JSON.stringify(b);

// ─────────────────────────────────────────────────────────────────────────────
// Carregador: TypeScript real, `require` falso (o mesmo de o-membro-liga-o-agente.test.mjs)
// ─────────────────────────────────────────────────────────────────────────────
function carregarTS(rel, resolver = () => undefined) {
  const fonte = fs.readFileSync(path.join(RAIZ, rel), 'utf8');
  const js = ts.transpileModule(fonte, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, esModuleInterop: true },
    fileName: rel,
  }).outputText;
  const mod = { exports: {} };
  const req = (id) => {
    const r = resolver(id);
    if (r === undefined) throw new Error(`import nao previsto no teste: ${id}`);
    return r;
  };
  new Function('require', 'module', 'exports', js)(req, mod, mod.exports);
  return mod.exports;
}

const P = carregarTS('lib/admin/admin-auth-policy.ts');
const senha = carregarTS('lib/admin/senha-do-membro.ts');
const overview = carregarTS('lib/admin/tenant-overview-store.ts');

// ─────────────────────────────────────────────────────────────────────────────
// Os CHECKs do banco: os de company_members LIDOS DA MIGRATION; o de users_v2 medido (users_v2_role_check)
// ─────────────────────────────────────────────────────────────────────────────
const SQL = fs.readFileSync(path.join(RAIZ, 'backend/supabase/migrations/20261011_02_spec1310_membros.sql'), 'utf8')
  .split('\n').filter((l) => !l.trimStart().startsWith('--')).join('\n');
const listaDoSQL = (re) => { const m = SQL.match(re); return m ? [...m[1].matchAll(/'([a-z_]+)'/g)].map((x) => x[1]) : null; };
const PAPEIS_DO_BANCO = listaDoSQL(/add constraint ck_company_members_role\s+check \(role in \(([^)]*)\)\)/i);
const FUNCOES_DO_BANCO = listaDoSQL(/add constraint ck_company_members_funcoes\s+check \(funcoes <@ array\[([^\]]*)\]/i);
const PAPEIS_USERS_V2 = ['admin_company', 'member']; // 📊 pg_get_constraintdef(users_v2_role_check), 11/10/2026

const CHECKS = {
  company_members: (l) => (PAPEIS_DO_BANCO.includes(l.role) ? null : 'ck_company_members_role')
    ?? ((l.funcoes ?? []).every((f) => FUNCOES_DO_BANCO.includes(f)) ? null : 'ck_company_members_funcoes'),
  users_v2: (l) => (l.role == null || PAPEIS_USERS_V2.includes(l.role) ? null : 'users_v2_role_check'),
};

// ─────────────────────────────────────────────────────────────────────────────
// O banco falso: filtros APLICADOS, colunas PROJETADAS (ler `role` de quem só pediu `company_id` dá undefined),
// CHECKs, e o esquema (uma coluna que não existe → 42703, como o PostgREST).
// ─────────────────────────────────────────────────────────────────────────────
function bancoFalso(semente, { esquema = {}, falhaEm = null } = {}) {
  const t = JSON.parse(JSON.stringify(semente));
  const escritas = [];
  let seq = 0;
  function from(nome) {
    const filtros = [];
    let colunas = null, op = 'select', payload = null, conflito = null;
    const linhas = () => (t[nome] ||= []);
    const casa = (l) => filtros.every(([tipo, c, v]) => (tipo === 'eq' ? l[c] === v : tipo === 'in' ? v.includes(l[c]) : (l[c] ?? null) === v));
    const projetar = (l) => {
      if (!colunas || colunas === '*') return { ...l };
      const o = {};
      for (const c of colunas.split(',').map((s) => s.trim())) o[c] = l[c];
      return o;
    };
    const erroDeColuna = () => {
      const ok = esquema[nome];
      if (!ok || !colunas) return null;
      const falta = colunas.split(',').map((s) => s.trim()).find((c) => !ok.includes(c));
      return falta ? { code: '42703', message: `column ${nome}.${falta} does not exist` } : null;
    };
    const checar = (l) => { const e = CHECKS[nome]?.(l); return e ? { code: '23514', message: `violates check constraint "${e}"` } : null; };
    async function executar() {
      if (falhaEm && falhaEm(nome, op)) return { data: null, error: { code: 'XX000', message: 'banco caiu' } };
      const ec = erroDeColuna();
      if (ec) return { data: null, error: ec };
      if (op === 'select') return { data: linhas().filter(casa).map(projetar), error: null };
      if (op === 'insert') {
        const nova = { id: `${nome}-${++seq}`, ...payload };
        const e = checar(nova); if (e) return { data: null, error: e };
        linhas().push(nova); escritas.push({ tabela: nome, op, payload });
        return { data: [projetar(nova)], error: null };
      }
      if (op === 'upsert') {
        const chaves = conflito.split(',');
        const atual = linhas().find((l) => chaves.every((k) => l[k] === payload[k]));
        const nova = atual ? { ...atual, ...payload } : { id: `${nome}-${++seq}`, ...payload };
        const e = checar(nova); if (e) return { data: null, error: e };
        if (atual) Object.assign(atual, payload); else linhas().push(nova);
        escritas.push({ tabela: nome, op, payload });
        return { data: null, error: null };
      }
      if (op === 'update') {
        const alvo = linhas().filter(casa);
        for (const l of alvo) { const e = checar({ ...l, ...payload }); if (e) return { data: null, error: e }; }
        for (const l of alvo) Object.assign(l, payload);
        escritas.push({ tabela: nome, op, payload, filtros: [...filtros], afetadas: alvo.length });
        return { data: null, error: null };
      }
      if (op === 'delete') {
        const fica = linhas().filter((l) => !casa(l));
        escritas.push({ tabela: nome, op, filtros: [...filtros], afetadas: linhas().length - fica.length });
        t[nome] = fica;
        return { data: null, error: null };
      }
      throw new Error('op desconhecida ' + op);
    }
    const q = {
      select(c) { colunas = c; return q; },
      insert(p) { op = 'insert'; payload = p; return q; },
      upsert(p, o) { op = 'upsert'; payload = p; conflito = o?.onConflict; return q; },
      update(p) { op = 'update'; payload = p; return q; },
      delete() { op = 'delete'; return q; },
      eq(c, v) { filtros.push(['eq', c, v]); return q; },
      in(c, v) { filtros.push(['in', c, v]); return q; },
      is(c, v) { filtros.push(['is', c, v]); return q; },
      order() { return q; },
      limit() { return q; },
      async maybeSingle() { const r = await executar(); return { data: r.data?.[0] ?? null, error: r.error }; },
      async single() { const r = await executar(); return { data: r.data?.[0] ?? null, error: r.error ?? (r.data?.length ? null : { code: 'PGRST116' }) }; },
      then(res, rej) { return executar().then(res, rej); },
    };
    return q;
  }
  return { supabase: { from }, tabelas: t, escritas };
}

// ─────────────────────────────────────────────────────────────────────────────
// O mundo: DUAS corretoras
// ─────────────────────────────────────────────────────────────────────────────
const A = 'aaaaaaaa-0000-4000-8000-00000000000a';
const B = 'bbbbbbbb-0000-4000-8000-00000000000b';
const ADMIN_A = 'u0000000-0000-4000-8000-0000000000a1';
const MEMBRO_A = 'u0000000-0000-4000-8000-0000000000a2';
const OUTRO_ADMIN_A = 'u0000000-0000-4000-8000-0000000000a3';
const ADMIN_B = 'u0000000-0000-4000-8000-0000000000b1';
const MEMBRO_B = 'u0000000-0000-4000-8000-0000000000b2';
const DUPLO = 'u0000000-0000-4000-8000-0000000000d1'; // admin em A, primária B (administra B)

const usuario = (id, company_id, role, extra = {}) => ({
  id, company_id, role, is_owner: false, email: `${id.slice(-2)}@exemplo.test`, first_name: `pessoa_${id.slice(-2)}`,
  last_name: '', phone: '0', status: 'active', last_login_at: null, deleted_at: null, ...extra,
});
const vinculo = (user_id, company_id, role, extra = {}) => ({
  id: `cm-${user_id.slice(-2)}-${company_id.slice(-1)}`, user_id, company_id, role, is_owner: false, status: 'active',
  funcoes: [], created_at: '2026-10-01T00:00:00Z', ...extra,
});
const MUNDO = {
  users_v2: [
    usuario(ADMIN_A, A, 'admin_company'), usuario(MEMBRO_A, A, 'member'), usuario(OUTRO_ADMIN_A, A, 'admin_company'),
    usuario(ADMIN_B, B, 'admin_company'), usuario(MEMBRO_B, B, 'member'), usuario(DUPLO, B, 'admin_company'),
  ],
  company_members: [
    vinculo(ADMIN_A, A, 'admin_company'), vinculo(MEMBRO_A, A, 'member', { funcoes: ['calculista'] }),
    vinculo(OUTRO_ADMIN_A, A, 'admin_company'), vinculo(DUPLO, A, 'admin_company'),
    vinculo(ADMIN_B, B, 'admin_company'), vinculo(MEMBRO_B, B, 'member', { funcoes: ['comercial'] }),
    vinculo(DUPLO, B, 'admin_company'),
  ],
  portal_accounts: [],
};
const ESQUEMA_PRE_MIGRATION = {
  company_members: ['id', 'user_id', 'company_id', 'role', 'is_owner', 'status', 'created_at'],
};

// ─────────────────────────────────────────────────────────────────────────────
// A sessão → requireCompanyMember REAL → rota REAL
// ─────────────────────────────────────────────────────────────────────────────
function carregarAuth(banco, sessao) {
  return carregarTS('lib/admin/admin-auth.ts', (id) => {
    if (id === 'next/headers') return { cookies: async () => ({}) };
    if (id === 'iron-session') return { getIronSession: async () => ({ ...sessao }) };
    if (id === '@supabase/supabase-js') return { createClient: () => banco.supabase };
    if (id === '@/lib/iron-session') return { adminSessionOptions: {}, sessionOptions: {} };
    if (id === '@/lib/admin/admin-auth-policy') return P;
    return undefined;
  });
}

const chamadasAoBackend = [];
let respostaDoBackend = async () => ({ ok: true, status: 200 });
process.env.BACKEND_INTERNAL_API_KEY = 'chave-de-teste-nao-secreta';

async function rota(metodo, { sessao, corpo = {}, banco }) {
  const auth = carregarAuth(banco, sessao);
  const mod = carregarTS('app/api/dashboard/team/route.ts', (id) => {
    if (id === 'next/server') return { NextResponse: { json: (b, init) => ({ body: b, status: init?.status ?? 200 }) } };
    if (id === '@/lib/admin/admin-auth') return auth;
    if (id === '@/lib/admin/admin-auth-policy') return P;
    if (id === '@/lib/admin/tenant-overview-store') return overview;
    if (id === '@/lib/admin/senha-do-membro') return senha;
    if (id === '@/lib/auth') return { hashPassword: async (s) => `hash-de-${String(s).length}-caracteres` };
    if (id === 'crypto') return nodeCrypto;
    if (id === '@/lib/backend-url') return { getBackendUrl: () => 'http://backend.teste' };
    return undefined;
  });
  const fetchOriginal = globalThis.fetch;
  globalThis.fetch = async (url, init) => {
    chamadasAoBackend.push({ url, init, vinculosNaHora: banco.tabelas.company_members.map((v) => `${v.user_id}|${v.company_id}`) });
    return respostaDoBackend();
  };
  const erroOriginal = console.error; console.error = () => {};
  try {
    const req = { json: async () => corpo, headers: { get: () => null } };
    return await mod[metodo](req);
  } finally {
    globalThis.fetch = fetchOriginal; console.error = erroOriginal;
  }
}
const sessaoSemEmpresaAtiva = (userId, companyId = null) => ({ userId, activeCompanyId: null, companyId });
const vinculoDe = (banco, u, c) => banco.tabelas.company_members.find((v) => v.user_id === u && v.company_id === c);
const usuarioDe = (banco, u) => banco.tabelas.users_v2.find((x) => x.id === u);

console.log('\n== SPEC-131-0 A · F1 — membros ==\n');

// ① A POLÍTICA — listas fechadas, uma fonte; função não dá acesso
{
  assert('① PAPEIS_DE_ACESSO é a lista fechada', igual([...P.PAPEIS_DE_ACESSO], ['owner', 'admin_company', 'member', 'attendant']));
  assert('① FUNCOES_DE_TRABALHO é a lista fechada', igual([...P.FUNCOES_DE_TRABALHO], ['comercial', 'calculista', 'negociador']));
  assert('① a equipe dá todos os papéis menos o de dono', igual([...P.PAPEIS_QUE_A_EQUIPE_DA], ['admin_company', 'member', 'attendant']));
  assert('① papel inventado / legado não é aceito pela equipe',
    P.papelQueAEquipeDa('owner') === null && P.papelQueAEquipeDa('admin') === null && P.papelQueAEquipeDa('gerente') === null
    && P.papelQueAEquipeDa(undefined) === null);
  assert('① papel válido é aceito', P.papelQueAEquipeDa('attendant') === 'attendant');
  const l = P.lerFuncoes(['negociador', 'comercial', 'comercial']);
  assert('① funções: repetida vira uma, ordem oficial', l.ok && igual(l.funcoes, ['comercial', 'negociador']));
  assert('① funções: lista vazia = nenhuma', igual(P.lerFuncoes([]), { ok: true, funcoes: [] }));
  assert('① funções: desconhecida RECUSA o pedido inteiro', P.lerFuncoes(['comercial', 'vendedor']).ok === false);
  assert('① funções: texto solto não é lista', P.lerFuncoes('comercial').ok === false);
  for (const f of P.FUNCOES_DE_TRABALHO) {
    assert(`① ⛔ a função ${f} NÃO dá acesso`,
      !P.canWriteTenantConfig({ role: f, isOwner: false }) && !P.canToggleAttendanceAgent({ role: f, isOwner: false })
      && !P.TENANT_WRITE_ROLES.includes(f) && !P.ATTENDANCE_TOGGLE_ROLES.includes(f));
  }
  assert('① espelho legado: atendente vira membro (users_v2_role_check)', P.papelNoCadastroLegado('attendant') === 'member');
  assert('① espelho legado: administrador fica administrador', P.papelNoCadastroLegado('admin_company') === 'admin_company');
  assert('① a ajuda é a frase de gente pedida',
    P.AJUDA_DAS_FUNCOES === 'Comercial: tem carteira e Agger próprio. Calculista: monta cálculos, não fala com cliente. Negociador: conversa com o cliente.');
  assert('① rótulos humanos', P.ROTULO_DO_PAPEL.admin_company === 'Administrador' && P.ROTULO_DO_PAPEL.member === 'Membro'
    && P.ROTULO_DO_PAPEL.attendant === 'Atendente');
}

// ② O BANCO E A POLÍTICA TÊM A MESMA LISTA
{
  assert('② a migration tem o CHECK do papel', Array.isArray(PAPEIS_DO_BANCO));
  assert('② a migration tem o CHECK das funções', Array.isArray(FUNCOES_DO_BANCO));
  assert('② papel: banco = política', igual(PAPEIS_DO_BANCO, [...P.PAPEIS_DE_ACESSO]));
  assert('② funções: banco = política', igual(FUNCOES_DO_BANCO, [...P.FUNCOES_DE_TRABALHO]));
  // controle: o banco falso RECUSA de verdade (o CHECK consegue falhar)
  assert('② controle: o CHECK falso recusa papel inventado', CHECKS.company_members({ role: 'admin', funcoes: [] }) !== null);
  assert('② controle: o CHECK falso recusa função inventada', CHECKS.company_members({ role: 'member', funcoes: ['vendedor'] }) !== null);
}

// ③ UMA FONTE DO PAPEL — requireCompanyMember sem empresa ativa
async function exigir(sessao, write, banco) {
  return carregarAuth(banco, sessao).requireCompanyMember({ write });
}
{
  // 🔴 O GUARDA: users_v2 diz administrador; o vínculo (rebaixado) diz membro → a ESCRITA é negada
  const b1 = bancoFalso(MUNDO);
  vinculoDe(b1, OUTRO_ADMIN_A, A).role = 'member';
  assert('🔴 ③ precondição: users_v2.role ainda diz admin_company', usuarioDe(b1, OUTRO_ADMIN_A).role === 'admin_company');
  const r1 = await exigir(sessaoSemEmpresaAtiva(OUTRO_ADMIN_A), true, b1);
  assert('🔴 ③ rebaixado só no vínculo → escrita NEGADA (403 admin_required)', r1.ok === false && r1.status === 403 && r1.error === 'admin_required');
  const r1l = await exigir(sessaoSemEmpresaAtiva(OUTRO_ADMIN_A), false, b1);
  assert('③ e a leitura diz o papel do VÍNCULO', r1l.ok && r1l.ctx.role === 'member' && r1l.ctx.companyId === A);

  // ⛔ CONTROLE NO SENTIDO CONTRÁRIO: users_v2 diz membro; o vínculo diz administrador → a escrita PASSA
  const b2 = bancoFalso(MUNDO);
  vinculoDe(b2, MEMBRO_A, A).role = 'admin_company';
  const r2 = await exigir(sessaoSemEmpresaAtiva(MEMBRO_A), true, b2);
  assert('⛔ ③ controle: promovido só no vínculo → escrita PERMITIDA', r2.ok === true && r2.ctx.role === 'admin_company');

  // is_owner também vem do vínculo
  const b3 = bancoFalso(MUNDO);
  usuarioDe(b3, MEMBRO_A).is_owner = true;
  const r3 = await exigir(sessaoSemEmpresaAtiva(MEMBRO_A), true, b3);
  assert('③ users_v2.is_owner sozinho NÃO dá escrita', r3.ok === false && r3.status === 403);

  // falha FECHADA: sem vínculo ativo na primária
  const b4 = bancoFalso(MUNDO);
  b4.tabelas.company_members = b4.tabelas.company_members.filter((v) => !(v.user_id === ADMIN_A && v.company_id === A));
  const r4w = await exigir(sessaoSemEmpresaAtiva(ADMIN_A), true, b4);
  const r4r = await exigir(sessaoSemEmpresaAtiva(ADMIN_A), false, b4);
  assert('🔴 ③ sem vínculo na primária → nega a escrita', r4w.ok === false && r4w.status === 403 && r4w.error === 'no_membership_primary_company');
  assert('🔴 ③ sem vínculo na primária → nega até a leitura', r4r.ok === false && r4r.status === 403);

  const b5 = bancoFalso(MUNDO);
  vinculoDe(b5, ADMIN_A, A).status = 'suspended';
  const r5 = await exigir(sessaoSemEmpresaAtiva(ADMIN_A), false, b5);
  assert('③ vínculo não ativo → nega', r5.ok === false && r5.status === 403);

  // o banco falhou ao ler o vínculo → nega (nunca cai em users_v2)
  const b6 = bancoFalso(MUNDO, { falhaEm: (tabela) => tabela === 'company_members' });
  const r6 = await exigir(sessaoSemEmpresaAtiva(ADMIN_A), false, b6);
  assert('🔴 ③ erro do banco no vínculo → nega (falha fechada)', r6.ok === false && r6.status === 403);

  // o vínculo é o DA EMPRESA PRIMÁRIA: o DUPLO é admin em A, mas a primária é B → a sessão sem escolha vale B
  const b7 = bancoFalso(MUNDO);
  vinculoDe(b7, DUPLO, B).role = 'member';
  const r7 = await exigir(sessaoSemEmpresaAtiva(DUPLO), true, b7);
  assert('③ o vínculo lido é o da PRIMÁRIA (B), não o de outra corretora (A)', r7.ok === false && r7.error === 'admin_required');

  // empresa ativa (seletor): continua do vínculo daquela empresa, e sem vínculo nega
  const r8 = await exigir({ userId: MEMBRO_A, activeCompanyId: B, companyId: B }, false, bancoFalso(MUNDO));
  assert('③ empresa ativa sem vínculo → 403', r8.ok === false && r8.error === 'no_membership_active_company');
  const r9 = await exigir({ userId: DUPLO, activeCompanyId: A, companyId: A }, true, bancoFalso(MUNDO));
  assert('③ empresa ativa com vínculo admin → escreve em A', r9.ok === true && r9.ctx.companyId === A);
  const r10 = await exigir(sessaoSemEmpresaAtiva(ADMIN_A, B), false, bancoFalso(MUNDO));
  assert('③ sessão diz B, banco diz A → 403 (inalterado)', r10.ok === false && r10.error === 'session_company_divergent');
}

// ④ A ROTA DA EQUIPE — duas corretoras
{
  // GET
  const b = bancoFalso(MUNDO);
  const g = await rota('GET', { sessao: sessaoSemEmpresaAtiva(ADMIN_A), banco: b });
  const ids = (g.body.members ?? []).map((m) => m.user_id).sort();
  assert('④ GET: só a equipe de A', igual(ids, [ADMIN_A, MEMBRO_A, OUTRO_ADMIN_A, DUPLO].sort()));
  const ma = g.body.members.find((m) => m.user_id === MEMBRO_A);
  assert('④ GET: as funções vêm do vínculo', igual(ma?.funcoes, ['calculista']));
  assert('④ GET: o rótulo do papel é o da política (uma fonte)',
    g.body.members.every((m) => m.role_label === P.ROTULO_DO_PAPEL[m.role]));
  assert('④ GET: admin pode gerir', g.body.can_manage === true);

  // GET antes da migration: a lista NÃO some
  const bp = bancoFalso(MUNDO, { esquema: ESQUEMA_PRE_MIGRATION });
  const gp = await rota('GET', { sessao: sessaoSemEmpresaAtiva(ADMIN_A), banco: bp });
  assert('④ GET sem a coluna nova: a equipe continua aparecendo, sem funções',
    gp.body.members?.length === 4 && gp.body.members.every((m) => igual(m.funcoes, [])));
}
{
  // PATCH funções
  const b = bancoFalso(MUNDO);
  const r = await rota('PATCH', { sessao: sessaoSemEmpresaAtiva(ADMIN_A), banco: b,
    corpo: { user_id: MEMBRO_A, role: 'member', funcoes: ['negociador', 'comercial'] } });
  assert('④ PATCH: admin de A marca as funções de um membro de A', r.status === 200 && igual(vinculoDe(b, MEMBRO_A, A).funcoes, ['comercial', 'negociador']));
  assert('④ PATCH: escreveu filtrando a corretora', b.escritas.some((e) => e.tabela === 'company_members' && e.op === 'update'
    && e.filtros.some(([, c, v]) => c === 'company_id' && v === A)));

  const b2 = bancoFalso(MUNDO);
  const r2 = await rota('PATCH', { sessao: sessaoSemEmpresaAtiva(ADMIN_A), banco: b2,
    corpo: { user_id: MEMBRO_A, first_name: 'nome_novo', funcoes: ['vendedor'] } });
  assert('④ PATCH: função inventada → 400', r2.status === 400);
  assert('④ PATCH: e nada foi gravado pela metade (nem o nome)', b2.escritas.length === 0 && usuarioDe(b2, MEMBRO_A).first_name !== 'nome_novo');

  const b3 = bancoFalso(MUNDO);
  const r3 = await rota('PATCH', { sessao: sessaoSemEmpresaAtiva(MEMBRO_A), banco: b3, corpo: { user_id: MEMBRO_A, funcoes: ['comercial'] } });
  assert('④ PATCH: membro comum não altera nem as próprias funções (403)', r3.status === 403 && b3.escritas.length === 0);

  // 🔴 DUAS CORRETORAS: o admin de A não alcança o membro de B
  const b4 = bancoFalso(MUNDO);
  const r4 = await rota('PATCH', { sessao: sessaoSemEmpresaAtiva(ADMIN_A), banco: b4,
    corpo: { user_id: MEMBRO_B, role: 'admin_company', funcoes: ['negociador'] } });
  assert('🔴 ④ admin de A no membro de B → 404', r4.status === 404);
  assert('🔴 ④ e o vínculo de B está intacto', vinculoDe(b4, MEMBRO_B, B).role === 'member' && igual(vinculoDe(b4, MEMBRO_B, B).funcoes, ['comercial'])
    && b4.escritas.length === 0);

  const b5 = bancoFalso(MUNDO);
  const r5 = await rota('PATCH', { sessao: sessaoSemEmpresaAtiva(ADMIN_A), banco: b5, corpo: { user_id: MEMBRO_A, role: 'admin' } });
  assert('④ PATCH: papel fora da lista → 400 (nunca troca calado)', r5.status === 400 && b5.escritas.length === 0);
}
{
  // 🔴 O FIO DO DEFEITO, DE PONTA A PONTA: rebaixar pela rota e a pessoa perde a escrita sem trocar de corretora
  const b = bancoFalso(MUNDO);
  const r = await rota('PATCH', { sessao: sessaoSemEmpresaAtiva(ADMIN_A), banco: b, corpo: { user_id: OUTRO_ADMIN_A, role: 'member' } });
  assert('🔴 ④ rebaixar pela rota: vínculo vira membro', r.status === 200 && vinculoDe(b, OUTRO_ADMIN_A, A).role === 'member');
  assert('④ e o espelho legado acompanha (A é a primária)', usuarioDe(b, OUTRO_ADMIN_A).role === 'member');
  const depois = await exigir(sessaoSemEmpresaAtiva(OUTRO_ADMIN_A), true, b);
  assert('🔴 ④ e a pessoa rebaixada NÃO escreve mais', depois.ok === false && depois.error === 'admin_required');

  // espelho SÓ na primária: DUPLO é admin em A mas a primária é B
  const b2 = bancoFalso(MUNDO);
  const r2 = await rota('PATCH', { sessao: sessaoSemEmpresaAtiva(ADMIN_A), banco: b2, corpo: { user_id: DUPLO, role: 'member' } });
  assert('④ rebaixar em A quem é de B: o vínculo de A muda', r2.status === 200 && vinculoDe(b2, DUPLO, A).role === 'member');
  assert('🔴 ④ mas users_v2 (primária B) e o vínculo de B NÃO mudam',
    usuarioDe(b2, DUPLO).role === 'admin_company' && vinculoDe(b2, DUPLO, B).role === 'admin_company');

  // atendente: o vínculo guarda attendant, o espelho guarda member (o users_v2_role_check recusaria attendant)
  const b3 = bancoFalso(MUNDO);
  const r3 = await rota('PATCH', { sessao: sessaoSemEmpresaAtiva(ADMIN_A), banco: b3, corpo: { user_id: MEMBRO_A, role: 'attendant' } });
  assert('④ virar Atendente: vínculo attendant, espelho member', r3.status === 200
    && vinculoDe(b3, MEMBRO_A, A).role === 'attendant' && usuarioDe(b3, MEMBRO_A).role === 'member');
}
{
  // POST
  const b = bancoFalso(MUNDO);
  const r = await rota('POST', { sessao: sessaoSemEmpresaAtiva(ADMIN_A), banco: b,
    corpo: { email: 'nova_pessoa@exemplo.test', first_name: 'membro_novo', role: 'attendant', funcoes: ['negociador'], password: 'senha-de-teste-1' } });
  const novo = b.tabelas.users_v2.find((u) => u.email === 'nova_pessoa@exemplo.test');
  assert('④ POST: Atendente nova é criada (antes: 500 no users_v2_role_check)', r.status === 200 && Boolean(novo));
  assert('④ POST: espelho legado member, vínculo attendant com a função', novo?.role === 'member'
    && vinculoDe(b, novo?.id, A)?.role === 'attendant' && igual(vinculoDe(b, novo?.id, A)?.funcoes, ['negociador']));
  assert('④ POST: a senha nunca é gravada em texto', !JSON.stringify(b.tabelas).includes('senha-de-teste-1'));

  const b2 = bancoFalso(MUNDO);
  const r2 = await rota('POST', { sessao: sessaoSemEmpresaAtiva(ADMIN_A), banco: b2,
    corpo: { email: 'outra@exemplo.test', first_name: 'x', funcoes: ['vendedor'], password: 'senha-de-teste-1' } });
  assert('④ POST: função inventada → 400 e ninguém é criado', r2.status === 400 && b2.escritas.length === 0);

  const b3 = bancoFalso(MUNDO);
  vinculoDe(b3, OUTRO_ADMIN_A, A).is_owner = true;
  const r3 = await rota('POST', { sessao: sessaoSemEmpresaAtiva(ADMIN_A), banco: b3,
    corpo: { email: usuarioDe(b3, OUTRO_ADMIN_A).email, first_name: 'x', role: 'member', password: 'senha-de-teste-1' } });
  assert('④ POST: re-adicionar quem já está na equipe → 409, e o dono não é rebaixado',
    r3.status === 409 && vinculoDe(b3, OUTRO_ADMIN_A, A).is_owner === true && vinculoDe(b3, OUTRO_ADMIN_A, A).role === 'admin_company');

  const b4 = bancoFalso(MUNDO);
  const r4 = await rota('POST', { sessao: sessaoSemEmpresaAtiva(ADMIN_A), banco: b4,
    corpo: { email: usuarioDe(b4, MEMBRO_B).email, first_name: 'x', role: 'member', funcoes: ['calculista'], password: 'senha-de-teste-1' } });
  assert('④ POST: alguém de B entra também em A (vínculo novo em A; o de B intacto)', r4.status === 200
    && igual(vinculoDe(b4, MEMBRO_B, A)?.funcoes, ['calculista']) && igual(vinculoDe(b4, MEMBRO_B, B).funcoes, ['comercial']));
}
{
  // DELETE — o vínculo sai; o Agger pessoal é desligado pelo backend; NUNCA esta rota escreve as contas
  chamadasAoBackend.length = 0;
  respostaDoBackend = async () => ({ ok: true, status: 200 });
  const b = bancoFalso(MUNDO);
  const r = await rota('DELETE', { sessao: sessaoSemEmpresaAtiva(ADMIN_A), banco: b, corpo: { user_id: MEMBRO_A } });
  const c = chamadasAoBackend[0];
  assert('④ DELETE: o vínculo de A saiu', r.status === 200 && !vinculoDe(b, MEMBRO_A, A));
  assert('④ DELETE: chamou o backend UMA vez, no endpoint da F3', chamadasAoBackend.length === 1
    && c.url === 'http://backend.teste/api/portal/aggers-da-equipe/desligar-membro' && c.init.method === 'POST');
  assert('④ DELETE: com a chave interna no cabeçalho', c.init.headers['X-AutoBrokers-Internal-Key'] === 'chave-de-teste-nao-secreta');
  assert('🔴 ④ DELETE: o corpo leva a corretora da SESSÃO e a pessoa', igual(JSON.parse(c.init.body), { company_id: A, user_id: MEMBRO_A }));
  assert('④ DELETE: o vínculo já tinha saído quando o backend foi chamado', !c.vinculosNaHora.includes(`${MEMBRO_A}|${A}`));
  assert('④ DELETE: agger_pendente false quando o backend respondeu', r.body.agger_pendente === false);
  assert('⛔ ④ DELETE: nenhuma escrita em portal_accounts', !b.escritas.some((e) => e.tabela === 'portal_accounts'));

  respostaDoBackend = async () => { throw new Error('backend fora do ar'); };
  const b2 = bancoFalso(MUNDO);
  const r2 = await rota('DELETE', { sessao: sessaoSemEmpresaAtiva(ADMIN_A), banco: b2, corpo: { user_id: MEMBRO_A } });
  assert('🔴 ④ DELETE com o backend fora: o vínculo sai MESMO ASSIM e agger_pendente true',
    r2.status === 200 && r2.body.ok === true && r2.body.agger_pendente === true && !vinculoDe(b2, MEMBRO_A, A));

  respostaDoBackend = async () => ({ ok: false, status: 500 });
  const b3 = bancoFalso(MUNDO);
  const r3 = await rota('DELETE', { sessao: sessaoSemEmpresaAtiva(ADMIN_A), banco: b3, corpo: { user_id: MEMBRO_A } });
  assert('④ DELETE com o backend respondendo erro: agger_pendente true', r3.status === 200 && r3.body.agger_pendente === true);

  chamadasAoBackend.length = 0;
  respostaDoBackend = async () => ({ ok: true, status: 200 });
  const b4 = bancoFalso(MUNDO);
  const r4 = await rota('DELETE', { sessao: sessaoSemEmpresaAtiva(ADMIN_A), banco: b4, corpo: { user_id: MEMBRO_B } });
  assert('🔴 ④ DELETE: admin de A no membro de B → 404, B intacto e o backend NÃO é chamado',
    r4.status === 404 && Boolean(vinculoDe(b4, MEMBRO_B, B)) && chamadasAoBackend.length === 0);

  const b5 = bancoFalso(MUNDO);
  const r5 = await rota('DELETE', { sessao: sessaoSemEmpresaAtiva(MEMBRO_A), banco: b5, corpo: { user_id: OUTRO_ADMIN_A } });
  assert('④ DELETE: membro comum não remove ninguém (403)', r5.status === 403 && b5.escritas.length === 0);

  const fonteDaRota = fs.readFileSync(path.join(RAIZ, 'app/api/dashboard/team/route.ts'), 'utf8');
  assert('⛔ ④ a rota não cita a tabela das contas de portal', !/portal_accounts/.test(fonteDaRota));
}

// ⑤ A TELA — etiquetas clicáveis, a ajuda, os rótulos da política, o aviso do Agger pendente
{
  const tela = fs.readFileSync(path.join(RAIZ, 'app/dashboard/personalizacao/corretora/equipe/TeamClient.tsx'), 'utf8');
  assert('⑤ a tela usa as listas e rótulos da política', /from '@\/lib\/admin\/admin-auth-policy'/.test(tela)
    && /FUNCOES_DE_TRABALHO\.map/.test(tela) && /PAPEIS_QUE_A_EQUIPE_DA\.map/.test(tela) && /ROTULO_DO_PAPEL\[p\]/.test(tela));
  assert('⑤ as funções são botões que alternam (aria-pressed)', /aria-pressed=\{marcada\}/.test(tela) && /alternarFuncao\(f\)/.test(tela));
  assert('⑤ a linha de ajuda é a da política', /\{AJUDA_DAS_FUNCOES\}/.test(tela));
  assert('⑤ a tela manda as funções no POST e no PATCH', (tela.match(/role: form\.role, funcoes/g) || []).length === 2);
  assert('⑤ a lista mostra as funções de cada pessoa', /<EtiquetasDeFuncao funcoes=\{m\.funcoes\} \/>/.test(tela));
  assert('⑤ a tela avisa quando o Agger ficou pendente', /j\.agger_pendente/.test(tela) && /data-aviso-agger-pendente/.test(tela));
  assert('⑤ nenhum rótulo de papel escrito à mão sobrou', !/<option value="(member|attendant|admin_company)">/.test(tela));
}

// ⑥ conserto 131-0 A (juiz P5) — as SUGESTÕES do sistema de gestão (nomes dos produtores da InfoCap + uma ida à
// InfoCap por abertura) só para quem administra. A rota REAL sobre o requireCompanyMember REAL.
{
  async function sugestoes(sessao, banco) {
    const auth = carregarAuth(banco, sessao);
    const mod = carregarTS('app/api/dashboard/equipe/sistema-de-gestao/route.ts', (id) => {
      if (id === 'next/server') return { NextResponse: { json: (b, init) => ({ body: b, status: init?.status ?? 200 }) } };
      if (id === '@/lib/admin/admin-auth') return auth;
      if (id === '@/lib/vault/server') return { resolveSessionCompany: async () => ({ userId: sessao.userId, companyId: A }) };
      if (id === '@/lib/admin/porteiro-de-configuracao') return { porteiroDeConfiguracao: async () => null, registrarNaAuditoria: async () => {} };
      if (id === '@/lib/backend-url') return { getBackendUrl: () => 'http://backend.teste' };
      return undefined;
    });
    const fetchOriginal = globalThis.fetch;
    globalThis.fetch = async (url) => {
      chamadasAoBackend.push({ url });
      return { ok: true, status: 200, json: async () => ({ status: 'ok', produtores: [] }) };
    };
    try {
      const req = { nextUrl: { searchParams: new URLSearchParams('o=sugestoes') }, headers: { get: () => null } };
      return await mod.GET(req);
    } finally {
      globalThis.fetch = fetchOriginal;
    }
  }
  chamadasAoBackend.length = 0;
  const r1 = await sugestoes(sessaoSemEmpresaAtiva(MEMBRO_A), bancoFalso(MUNDO));
  assert('🔴 ⑥ membro comum NÃO lê as sugestões (403) e a InfoCap não é chamada',
    r1.status === 403 && chamadasAoBackend.length === 0);
  const r2 = await sugestoes(sessaoSemEmpresaAtiva(ADMIN_A), bancoFalso(MUNDO));
  assert('⑥ controle: o administrador lê as sugestões da corretora DELE',
    r2.status === 200 && chamadasAoBackend.length === 1
    && chamadasAoBackend[0].url === `http://backend.teste/api/contas-da-corretora/sistema-de-gestao/sugestoes?company_id=${A}`);
}

console.log(`${pass} ok, ${fail} falha(s)`);
process.exit(fail ? 1 : 0);
