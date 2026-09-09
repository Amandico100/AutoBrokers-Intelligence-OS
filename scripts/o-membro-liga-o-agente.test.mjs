// ===========================================================================
// O MEMBRO LIGA O AGENTE — decisão do Founder, 09/09/2026
// ===========================================================================
//
// 🔴 O PROBLEMA, MEDIDO
//
// A Regina e a Saionara são quem liga o agente de manhã e desliga quando saem.
// 📊 Elas estão em `company_members` como **`member`** — nunca foram
// cadastradas com o papel `attendant` que a SPEC-093 criou para elas. E
// `ATTENDANCE_TOGGLE_ROLES` não continha `member`: o botão devolvia
// **403 admin_required** para as duas pessoas que o produto precisa que o
// apertem.
//
// ⚠️ E o conserto NÃO pode ser "dar admin_company às duas": isso abriria
// prompt do agente, equipe, cobrança e chaves junto. O portão é por CAMPO.
//
// 🔴 ESTE ARQUIVO EXECUTA A ROTA E O `requireCompanyMember` DE VERDADE.
//
// Não é um teste da função pura — esse já existe em `admin-auth-policy.test.mjs`
// e continuaria verde com a rota desligada (foi exatamente o buraco que o painel
// achou na SPEC-093). Aqui a rota REAL roda sobre o `requireCompanyMember` REAL,
// sobre um banco falso — que é onde a fronteira de tenant realmente mora.
//
// ⛔ A LINHA DE CONTROLE OBRIGATÓRIA (CLAUDE.md §9.2) está no bloco ⑤: a MESMA
// rota, com a política ANTIGA (sem `member`), tem de dar 403. Sem ela, um "200"
// no bloco ① poderia vir de qualquer coisa — inclusive de um `if` que parou de
// ser avaliado — e o mérito seria creditado ao lugar errado.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import ts from 'typescript';

const RAIZ = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const CORRETORA_A = 'aaaaaaaa-1111-1111-1111-111111111111';
const CORRETORA_B = 'bbbbbbbb-2222-2222-2222-222222222222';
const REGINA = 'uuuuuuuu-3333-3333-3333-333333333333';

let pass = 0, fail = 0;
function assert(nome, cond) {
  if (cond) { pass++; } else { fail++; console.log('  x ' + nome); }
}

// ─────────────────────────────────────────────────────────────────────────────
// Carregador: TypeScript real, `require` falso.
// (o mesmo de `spec093-a-rota-do-botao.test.mjs` e `entregas-tudo-abre.test.mjs`)
// ─────────────────────────────────────────────────────────────────────────────
function transpilar(fonte, nome) {
  return ts.transpileModule(fonte, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020,
      esModuleInterop: true,
    },
    fileName: nome,
  }).outputText;
}

function executar(js, resolverImport) {
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

function carregarTS(rel, resolverImport = () => ({})) {
  const fonte = fs.readFileSync(path.join(RAIZ, rel), 'utf8');
  return executar(transpilar(fonte, rel), resolverImport);
}

const FONTE_POLITICA = fs.readFileSync(
  path.join(RAIZ, 'lib/admin/admin-auth-policy.ts'), 'utf8');

const politica = carregarTS('lib/admin/admin-auth-policy.ts');
const transicao = carregarTS('lib/admin/toggle-transicao.ts');
const historico = carregarTS('lib/admin/historico-do-botao.ts');

// 🔴 A POLÍTICA DE ANTES — o código antigo, para a linha de controle do ⑤.
// Reconstruída do FONTE atual removendo só `'member'` da lista, para que a
// diferença entre verde e vermelho seja UM fator e mais nenhum (§9.2).
const FONTE_ANTIGA = FONTE_POLITICA.replace(
  "export const ATTENDANCE_TOGGLE_ROLES = [...TENANT_WRITE_ROLES, 'attendant', 'member'];",
  "export const ATTENDANCE_TOGGLE_ROLES = [...TENANT_WRITE_ROLES, 'attendant'];");
const politicaAntiga = executar(
  transpilar(FONTE_ANTIGA, 'admin-auth-policy.ANTIGA.ts'), () => ({}));

assert('🔴 a política ANTIGA foi mesmo reconstruída (um fator só mudou)',
  FONTE_ANTIGA !== FONTE_POLITICA);

// ─────────────────────────────────────────────────────────────────────────────
// O banco falso. Só o que estas duas rotas tocam.
// ─────────────────────────────────────────────────────────────────────────────
function bancoFalso(estado) {
  const gravado = { agent_activities: [], agents: null };

  function tabela(nome) {
    const filtros = {};
    const api = {
      select: () => api,
      eq: (col, val) => { filtros[col] = val; return api; },
      maybeSingle: async () => ({ data: linha(nome, filtros), error: null }),
      insert: async (row) => {
        gravado[nome] = gravado[nome] || [];
        gravado[nome].push(row);
        return { data: null, error: null };
      },
      update: async (campos) => {
        gravado.agents = { ...campos, ...filtros };
        return { data: null, error: null };
      },
    };
    // `.update(...).eq(...).eq(...)` — o update só resolve no fim da corrente.
    api.update = (campos) => {
      const cadeia = {
        eq: (col, val) => { filtros[col] = val; return cadeia; },
        then: (resolve) => {
          gravado.agents = { ...campos, ...filtros };
          return Promise.resolve({ error: null }).then(resolve);
        },
      };
      return cadeia;
    };
    return api;
  }

  function linha(nome, f) {
    if (nome === 'company_members') {
      const m = estado.vinculos.find(
        (v) => v.user_id === f.user_id && v.company_id === f.company_id
          && v.status === (f.status ?? v.status));
      return m ? { company_id: m.company_id, role: m.role, is_owner: m.is_owner } : null;
    }
    if (nome === 'users_v2') {
      return estado.usuarios[f.id] ?? null;
    }
    if (nome === 'companies') {
      return estado.empresas[f.id] ? { company_name: estado.empresas[f.id] } : null;
    }
    return null;
  }

  return { supabase: { from: tabela }, gravado };
}

// ─────────────────────────────────────────────────────────────────────────────
// O cenário completo: sessão → requireCompanyMember REAL → rota REAL.
// ─────────────────────────────────────────────────────────────────────────────
const ESTADO = {
  vinculos: [
    // A Regina é MEMBRO da corretora A. E de mais nenhuma.
    { user_id: REGINA, company_id: CORRETORA_A, role: 'member', is_owner: false, status: 'active' },
  ],
  usuarios: {
    [REGINA]: { id: REGINA, first_name: 'Regina', last_name: 'Souza', company_id: CORRETORA_A, role: 'member', is_owner: false },
  },
  empresas: { [CORRETORA_A]: 'Resulta Seguros', [CORRETORA_B]: 'AutoFleet' },
};

async function patch({
  userId = REGINA, activeCompanyId = CORRETORA_A, body, agentKey = 'even',
  agenteLigado = false, usarPoliticaAntiga = false, vinculos = ESTADO.vinculos,
} = {}) {
  const { supabase, gravado } = bancoFalso({ ...ESTADO, vinculos });
  const feito = { setTenantAgentActive: null, patchTenantAgentConfig: null };

  const auth = carregarTS('lib/admin/admin-auth.ts', (id) => {
    if (id === 'next/headers') return { cookies: async () => ({}) };
    if (id === 'iron-session') {
      return { getIronSession: async () => ({ userId, activeCompanyId, companyId: activeCompanyId }) };
    }
    if (id === '@supabase/supabase-js') return { createClient: () => supabase };
    if (id === '@/lib/iron-session') return { adminSessionOptions: {}, sessionOptions: {} };
    if (id === '@/lib/admin/admin-auth-policy') return politica;
    return undefined;
  });

  const rota = carregarTS('app/api/dashboard/agents/[agentKey]/route.ts', (id) => {
    if (id === 'next/server') {
      return { NextResponse: { json: (b, init) => ({ body: b, status: init?.status ?? 200 }) } };
    }
    if (id === '@/lib/admin/admin-auth') return auth;
    if (id === '@/lib/admin/admin-auth-policy') {
      return usarPoliticaAntiga ? politicaAntiga : politica;
    }
    if (id === '@/lib/admin/tenant-agent-store') {
      return {
        roleForKey: (k) => (k === 'autobrokers' ? 'core' : k === 'even' ? 'attendance' : null),
        getTenantAgentConfig: async () => ({ ok: true }),
        patchTenantAgentConfig: async (_s, c, r, input) => {
          feito.patchTenantAgentConfig = { companyId: c, role: r, input };
          return { ok: true, config: {} };
        },
        // 🔴 A transição vem do MOTOR real (`toggle-transicao.ts`), não de um
        // `true` escrito à mão: é ele que decide se o clique foi evento — e
        // portanto se o histórico grava.
        setTenantAgentActive: async (_s, c, r, ativo) => {
          const t = transicao.decidirTransicaoDoToggle(agenteLigado, ativo);
          feito.setTenantAgentActive = { companyId: c, role: r, is_active: ativo };
          return {
            ok: true, is_active: ativo, religou: t.religou, mudou: t.muda,
            desligado_em: null,
          };
        },
      };
    }
    if (id === '@/lib/admin/tenant-corridor-store') {
      return { ativarTodosOsCorredores: async () => ({ ok: true, ativados: 14, respeitados: 0, ja_ativos: 0, sem_ancora: 0 }) };
    }
    if (id === '@/lib/admin/saudacao-religamento') {
      return { previaDaSaudacao: async () => ({ ok: true, total: 0 }) };
    }
    // 🔴 O ESCRITOR DO HISTÓRICO É O DE VERDADE — a linha que ele grava em
    // `agent_activities` é conferida no banco falso, não num dublê.
    if (id === '@/lib/admin/historico-do-botao') return historico;
    return undefined;
  });

  const req = { json: async () => body, headers: { get: () => null } };
  const r = await rota.PATCH(req, { params: Promise.resolve({ agentKey }) });
  return { status: r.status, corpo: r.body, feito, atividades: gravado.agent_activities };
}

console.log('\n== O membro liga o agente — 09/09/2026 ==\n');

// ---------------------------------------------------------------------------
// ① A REGINA LIGA O AGENTE DA PRÓPRIA CORRETORA
// ---------------------------------------------------------------------------
{
  const r = await patch({ body: { is_active: true } });
  assert('① membro de A LIGA o agente de A', r.status === 200);
  assert('① e o agente ligado foi o de ATENDIMENTO da corretora A',
    r.feito.setTenantAgentActive?.role === 'attendance'
    && r.feito.setTenantAgentActive?.companyId === CORRETORA_A
    && r.feito.setTenantAgentActive?.is_active === true);
  assert('① a resposta diz que ligou', r.corpo.is_active === true);

  // 🔴 O HISTÓRICO — a linha durável e legível.
  const a = r.atividades?.[0];
  assert('🔴 ① gravou UMA linha em agent_activities', r.atividades?.length === 1);
  assert('🔴 ① com o NOME de quem ligou, em português',
    a?.title === 'Regina Souza ligou o agente de atendimento');
  assert('🔴 ① na corretora certa', a?.company_id === CORRETORA_A);
  assert('🔴 ① e o detalhe nomeia a corretora',
    typeof a?.detail === 'string' && a.detail.includes('Resulta Seguros'));
  assert('① a categoria é uma das que o feed conhece',
    a?.category === 'atendimentos');
}

// ---------------------------------------------------------------------------
// ①b E DESLIGA — o desligamento também vira linha
// ---------------------------------------------------------------------------
{
  const r = await patch({ body: { is_active: false }, agenteLigado: true });
  assert('①b membro DESLIGA o agente', r.status === 200);
  assert('🔴 ①b e o desligamento também vira histórico',
    r.atividades?.[0]?.title === 'Regina Souza desligou o agente de atendimento');
}

// ---------------------------------------------------------------------------
// ①c CONTROLE — clique que não muda nada NÃO é evento
// ---------------------------------------------------------------------------
{
  const r = await patch({ body: { is_active: true }, agenteLigado: true });
  assert('①c CONTROLE: ligar um agente já ligado devolve 200', r.status === 200);
  assert('🔴 ①c CONTROLE: e NÃO grava linha nenhuma',
    (r.atividades?.length ?? 0) === 0);
}

// ---------------------------------------------------------------------------
// ② MEMBRO DE A NÃO LIGA O AGENTE DE B
// ---------------------------------------------------------------------------
{
  const r = await patch({ activeCompanyId: CORRETORA_B, body: { is_active: true } });
  assert('🔴 ② membro de A NÃO liga o agente de B', r.status === 403);
  assert('② o motivo é a falta de vínculo, não o papel',
    r.corpo.error === 'no_membership_active_company');
  assert('🔴 ② e NADA foi ligado', r.feito.setTenantAgentActive === null);
  assert('🔴 ② e nada foi para o histórico', (r.atividades?.length ?? 0) === 0);
}
{
  // ②b — e nem forjando o corpo: não existe campo de empresa para forjar.
  const r = await patch({
    activeCompanyId: CORRETORA_B,
    body: { is_active: true, company_id: CORRETORA_A },
  });
  assert('②b nem com `company_id` no corpo', r.status === 403);
}
{
  // ②c CONTROLE — a MESMA Regina, com vínculo em B, liga o agente de B.
  // É isto que prova que o 403 acima veio do vínculo e não de outra coisa.
  const r = await patch({
    activeCompanyId: CORRETORA_B,
    body: { is_active: true },
    vinculos: [...ESTADO.vinculos,
      { user_id: REGINA, company_id: CORRETORA_B, role: 'member', is_owner: false, status: 'active' }],
  });
  assert('②c CONTROLE: com vínculo em B, ela liga o de B', r.status === 200);
  assert('②c CONTROLE: e o toggle foi na corretora B',
    r.feito.setTenantAgentActive?.companyId === CORRETORA_B);
  assert('②c CONTROLE: e o histórico foi para a corretora B',
    r.atividades?.[0]?.company_id === CORRETORA_B);
}

// ---------------------------------------------------------------------------
// ③ O MEMBRO NÃO ALTERA O PROMPT — a abertura é SÓ do botão
// ---------------------------------------------------------------------------
{
  const r = await patch({ body: { variables: { attendant_name: 'Outro' } } });
  assert('🔴 ③ membro NÃO altera o prompt/nome do agente', r.status === 403);
  assert('③ e o motivo é papel', r.corpo.error === 'admin_required');
  assert('🔴 ③ e nada foi gravado', r.feito.patchTenantAgentConfig === null);
}
{
  const r = await patch({ body: { overrides: { llm_temperature: 0.9 } } });
  assert('③ membro NÃO altera o tom/temperatura', r.status === 403);
}
{
  // 🔴 ③c O CORPO MISTO NÃO PASSA POR BAIXO — nem liga, nem escreve.
  const r = await patch({ body: { is_active: true, variables: { x: 1 } } });
  assert('🔴 ③c membro com corpo MISTO é recusado inteiro', r.status === 403);
  assert('🔴 ③c e o agente NÃO foi ligado de tabela',
    r.feito.setTenantAgentActive === null);
  assert('🔴 ③c e a configuração NÃO foi escrita',
    r.feito.patchTenantAgentConfig === null);
}
{
  // ③d o agente CENTRAL não é dele.
  const r = await patch({ body: { is_active: true }, agentKey: 'autobrokers' });
  assert('③d membro NÃO alterna o agente CORE', r.status === 403);
}
{
  // ③e nem os corredores: quem não escreve configuração não instala 14 deles.
  const r = await patch({ body: { is_active: true } });
  assert('🔴 ③e o clique do membro NÃO liga corredor nenhum',
    r.corpo.corredores === null);
}

// ---------------------------------------------------------------------------
// ④ O ADMINISTRADOR CONTINUA PODENDO TUDO
// ---------------------------------------------------------------------------
{
  const adminA = [{ user_id: REGINA, company_id: CORRETORA_A, role: 'admin_company', is_owner: false, status: 'active' }];
  const lig = await patch({ body: { is_active: true }, vinculos: adminA });
  assert('④ admin_company continua ligando', lig.status === 200);
  assert('④ e o histórico registra o admin também',
    lig.atividades?.[0]?.title === 'Regina Souza ligou o agente de atendimento');
  assert('④ e o admin CONTINUA ligando os 14 corredores',
    lig.corpo.corredores?.ativados === 14);

  const cfg = await patch({ body: { variables: { x: 1 } }, vinculos: adminA });
  assert('④ admin_company continua escrevendo configuração', cfg.status === 200);
  assert('④ e a escrita aconteceu', cfg.feito.patchTenantAgentConfig !== null);
}

// ---------------------------------------------------------------------------
// 🔴 ⑤ A LINHA DE CONTROLE — O CÓDIGO ANTIGO FICA VERMELHO NO CASO ①
// ---------------------------------------------------------------------------
//
// A MESMA rota, o MESMO banco, a MESMA Regina. Um único fator muda: a lista
// `ATTENDANCE_TOGGLE_ROLES` sem `member`. Se este bloco desse 200, o verde do
// bloco ① não teria vindo da mudança — e o mérito estaria no lugar errado.
{
  const r = await patch({ body: { is_active: true }, usarPoliticaAntiga: true });
  assert('🔴 ⑤ CONTROLE: com a política ANTIGA, o membro leva 403',
    r.status === 403);
  assert('⑤ CONTROLE: e o motivo era exatamente `admin_required`',
    r.corpo.error === 'admin_required');
  assert('⑤ CONTROLE: e o agente NÃO era ligado',
    r.feito.setTenantAgentActive === null);
  assert('⑤ CONTROLE: e não havia histórico nenhum',
    (r.atividades?.length ?? 0) === 0);
}
{
  // ⑤b e a política antiga NÃO quebra o admin — prova que o dublê antigo é
  // uma política funcional, não um módulo quebrado que recusa tudo.
  const r = await patch({
    body: { is_active: true }, usarPoliticaAntiga: true,
    vinculos: [{ user_id: REGINA, company_id: CORRETORA_A, role: 'admin_company', is_owner: false, status: 'active' }],
  });
  assert('⑤b CONTROLE: a política antiga ainda deixava o admin passar',
    r.status === 200);
}

// ---------------------------------------------------------------------------
// ⑥ A FRASE, isolada — linguagem humana, sem jargão
// ---------------------------------------------------------------------------
{
  const on = historico.fraseDoBotao({ nome: 'Saionara', ligou: true, corretora: 'Resulta' });
  const off = historico.fraseDoBotao({ nome: 'Saionara', ligou: false, corretora: 'Resulta' });
  assert('⑥ ligou', on.title === 'Saionara ligou o agente de atendimento');
  assert('⑥ desligou', off.title === 'Saionara desligou o agente de atendimento');
  assert('⑥ e as duas frases são DIFERENTES', on.title !== off.title);
  for (const t of [on.title, off.title, on.detail, off.detail]) {
    assert('⑥ sem jargão técnico na frase',
      !/is_active|toggle|attendance|agent_role|payload|null/i.test(t));
  }
  const semNome = historico.fraseDoBotao({ nome: '', ligou: true, corretora: '' });
  assert('⑥ sem nome, a linha ainda é legível',
    semNome.title === 'Alguém da equipe ligou o agente de atendimento');
}

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
process.exit(fail ? 1 : 0);
