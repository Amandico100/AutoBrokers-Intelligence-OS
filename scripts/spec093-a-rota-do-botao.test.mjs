// ===========================================================================
// SPEC-093 BLOCO A/G — a ROTA do botão, executada de verdade
// ===========================================================================
//
// 🔴 ESTE ARQUIVO EXISTE PORQUE O PAINEL ACHOU O BURACO.
//
// A SPEC moveu a autorização de `requireCompanyMember({ write: true })` para um
// `if` dentro da rota — e **nenhum teste executava a rota**. Os guardas só
// conferiam que a string da chamada existia no fonte. Com isso, a mutação
//
//     -  if (!decisao.permitido) {
//     +  if (false && !decisao.permitido) {
//
// deixava os 47 gates da política verdes (a função pura não mudou) e os guardas
// pytest verdes (`decidirPatchDeAgente(` continua no arquivo) — e **qualquer
// `member` da corretora passava a escrever prompt e variáveis do agente**, que
// era exatamente o que o `write: true` barrava antes.
//
// ⚠️ E o harness já existia: `entregas-tudo-abre.test.mjs` carrega uma rota com
// `carregarTS` e mocka `@/lib/admin/admin-auth`. O gate comportamental era
// possível e não tinha sido escrito.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import ts from 'typescript';

const RAIZ = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const EMPRESA = '11111111-1111-1111-1111-111111111111';

let pass = 0, fail = 0;
function assert(nome, cond) {
  if (cond) { pass++; } else { fail++; console.log('  x ' + nome); }
}

// ─────────────────────────────────────────────────────────────────────────────
// Carregador: TypeScript real, `require` falso. (Mesmo de entregas-*.test.mjs)
// ─────────────────────────────────────────────────────────────────────────────
function carregarTS(rel, resolverImport) {
  const fonte = fs.readFileSync(path.join(RAIZ, rel), 'utf8');
  const js = ts.transpileModule(fonte, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020,
      esModuleInterop: true,
    },
    fileName: rel,
  }).outputText;
  const mod = { exports: {} };
  const req = (id) => {
    const r = resolverImport(id);
    if (r === undefined) throw new Error(`import nao previsto no teste: ${id}`);
    return r;
  };
  // eslint-disable-next-line no-new-func
  new Function('require', 'module', 'exports', js)(req, mod, mod.exports);
  return mod.exports;
}

const politica = carregarTS('lib/admin/admin-auth-policy.ts', () => ({}));

// ─────────────────────────────────────────────────────────────────────────────
// O cenário: um PATCH, com quem, com que corpo — e o que o produto FEZ.
// ─────────────────────────────────────────────────────────────────────────────
async function patch({ role, isOwner = false, body, agentKey = 'even' }) {
  const feito = {
    setTenantAgentActive: null,
    patchTenantAgentConfig: null,
    ativarTodosOsCorredores: null,
    previaDaSaudacao: null,
    registrarBotaoDoAgente: null,
  };

  const rota = carregarTS('app/api/dashboard/agents/[agentKey]/route.ts', (id) => {
    if (id === 'next/server') {
      return { NextResponse: { json: (b, init) => ({ body: b, status: init?.status ?? 200 }) } };
    }
    if (id === '@/lib/admin/admin-auth') {
      return {
        assertSameOrigin: () => null,
        requireCompanyMember: async () => ({
          ok: true,
          ctx: { userId: 'u1', companyId: EMPRESA, role, isOwner },
          supabase: {},
        }),
      };
    }
    if (id === '@/lib/admin/admin-auth-policy') return politica;
    if (id === '@/lib/admin/tenant-agent-store') {
      return {
        roleForKey: (k) => (k === 'autobrokers' ? 'core' : k === 'even' ? 'attendance' : null),
        getTenantAgentConfig: async () => ({ ok: true }),
        patchTenantAgentConfig: async (_s, _c, _r, input) => {
          feito.patchTenantAgentConfig = input;
          return { ok: true, config: {} };
        },
        setTenantAgentActive: async (_s, _c, r, ativo) => {
          feito.setTenantAgentActive = { role: r, is_active: ativo };
          return { ok: true, is_active: ativo, religou: ativo, mudou: true, desligado_em: null };
        },
      };
    }
    if (id === '@/lib/admin/tenant-corridor-store') {
      return {
        ativarTodosOsCorredores: async () => {
          feito.ativarTodosOsCorredores = true;
          return { ok: true, ativados: 14, respeitados: 0, ja_ativos: 0, sem_ancora: 0 };
        },
      };
    }
    if (id === '@/lib/admin/historico-do-botao') {
      return {
        registrarBotaoDoAgente: async (_s, arg) => {
          feito.registrarBotaoDoAgente = arg;
          return { ok: true };
        },
      };
    }
    if (id === '@/lib/admin/saudacao-religamento') {
      return {
        previaDaSaudacao: async () => {
          feito.previaDaSaudacao = true;
          return { ok: true, total: 3 };
        },
      };
    }
    return undefined;
  });

  const req = { json: async () => body, headers: { get: () => null } };
  const r = await rota.PATCH(req, { params: Promise.resolve({ agentKey }) });
  return { status: r.status, corpo: r.body, feito };
}

console.log('\n== SPEC-093 — a ROTA do botão, executada ==\n');

// ---------------------------------------------------------------------------
// 🔴 A AUTORIZAÇÃO ACONTECE DE VERDADE
// ---------------------------------------------------------------------------
{
  const r = await patch({ role: 'member', body: { variables: { x: 1 } } });
  assert('🔴 `member` NÃO escreve configuração', r.status === 403);
  assert('🔴 e nada foi gravado', r.feito.patchTenantAgentConfig === null);
}
{
  // 🔴 O FATO MUDOU EM 09/09/2026 (decisão do Founder), E O TESTE MUDA COM ELE.
  //
  // A Regina e a Saionara são **Membro** em `company_members` — nunca foram
  // cadastradas como `attendant`. São elas que ligam o agente de manhã e
  // desligam quando saem. A afirmação vencida ("member NÃO alterna") não some:
  // ela MIGRA para o que continua verdadeiro logo abaixo — `member` não
  // escreve configuração, e um papel desconhecido não alterna nada.
  const r = await patch({ role: 'member', body: { is_active: true } });
  assert('🔴 `member` LIGA o agente de atendimento', r.status === 200);
  assert('🔴 e o agente FOI ligado', r.feito.setTenantAgentActive?.is_active === true);
  assert('🔴 e o histórico registrou quem ligou',
    r.feito.registrarBotaoDoAgente?.ligou === true);
}
{
  // 🔴 A LINHA DE CONTROLE que dá direito à conclusão acima: a rota CONSEGUE
  // recusar um toggle. Sem ela, um `if` desligado deixaria tudo verde.
  const r = await patch({ role: 'visitante', body: { is_active: true } });
  assert('CONTROLE: papel desconhecido NÃO alterna', r.status === 403);
  assert('CONTROLE: e o agente não foi ligado', r.feito.setTenantAgentActive === null);
  assert('CONTROLE: e nada foi para o histórico',
    r.feito.registrarBotaoDoAgente === null);
}
{
  const r = await patch({ role: 'attendant', body: { variables: { x: 1 } } });
  assert('`attendant` NÃO escreve configuração', r.status === 403);
  assert('e nada foi gravado', r.feito.patchTenantAgentConfig === null);
}
{
  // CONTROLE — prove que a rota CONSEGUE deixar passar.
  const r = await patch({ role: 'admin_company', body: { variables: { x: 1 } } });
  assert('CONTROLE: `admin_company` escreve configuração', r.status === 200);
  assert('CONTROLE: e a escrita aconteceu', r.feito.patchTenantAgentConfig !== null);
}

// ---------------------------------------------------------------------------
// ① a atendente aperta o botão, e só o botão
// ---------------------------------------------------------------------------
{
  const r = await patch({ role: 'attendant', body: { is_active: true } });
  assert('① `attendant` liga o atendimento', r.status === 200);
  assert('① e o agente FOI ligado', r.feito.setTenantAgentActive?.is_active === true);
  assert('① no papel `attendance`', r.feito.setTenantAgentActive?.role === 'attendance');
  assert('🔴 ① e ele NÃO ligou corredor nenhum',
    r.feito.ativarTodosOsCorredores === null);
  assert('① mas a prévia da saudação volta para a tela',
    r.feito.previaDaSaudacao === true);
}
{
  const r = await patch({ role: 'attendant', body: { is_active: true }, agentKey: 'autobrokers' });
  assert('①b `attendant` NÃO alterna o agente CORE', r.status === 403);
}

// ---------------------------------------------------------------------------
// 🔴 G — quem configura liga os 14; quem só aperta o botão, não
// ---------------------------------------------------------------------------
{
  const r = await patch({ role: 'admin_company', body: { is_active: true } });
  assert('G: `admin_company` religa E liga os corredores',
    r.feito.ativarTodosOsCorredores === true);
  assert('G: a resposta traz a contagem', r.corpo.corredores?.ativados === 14);
}
{
  const r = await patch({ role: 'admin_company', body: { is_active: false } });
  assert('G: DESLIGAR não liga corredor nenhum',
    r.feito.ativarTodosOsCorredores === null);
  assert('G: e a prévia da saudação também não sai ao desligar',
    r.feito.previaDaSaudacao === null);
}

// ---------------------------------------------------------------------------
// 🔴 O BOOLEANO — `Boolean("false") === true`
// ---------------------------------------------------------------------------
{
  const r = await patch({ role: 'admin_company', body: { is_active: 'false' } });
  assert('🔴 `"false"` NÃO liga o agente', r.feito.setTenantAgentActive === null);
  assert('🔴 e a resposta recusa em vez de fingir', r.status === 400);
}
{
  const r = await patch({ role: 'admin_company', body: { is_active: 1 } });
  assert('🔴 `1` também não passa por booleano', r.status === 400);
}

// ---------------------------------------------------------------------------
// 🔴 CORPO MISTO — o toggle não é engolido em silêncio
// ---------------------------------------------------------------------------
{
  const r = await patch({
    role: 'admin_company', body: { is_active: false, variables: { x: 1 } },
  });
  assert('🔴 misto: o agente FOI desligado',
    r.feito.setTenantAgentActive?.is_active === false);
  assert('🔴 misto: e as variáveis TAMBÉM foram aplicadas',
    r.feito.patchTenantAgentConfig?.variables?.x === 1);
  assert('🔴 misto: a resposta diz que o toggle aconteceu',
    r.corpo.alternado?.is_active === false);
  assert('misto: e devolve 200', r.status === 200);
}
{
  // CONTROLE — corpo só de config não alterna nada.
  const r = await patch({ role: 'admin_company', body: { variables: { x: 1 } } });
  assert('CONTROLE: corpo só de config não toca no botão',
    r.feito.setTenantAgentActive === null);
  assert('CONTROLE: e não devolve `alternado`', r.corpo.alternado === undefined);
}

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
process.exit(fail ? 1 : 0);
