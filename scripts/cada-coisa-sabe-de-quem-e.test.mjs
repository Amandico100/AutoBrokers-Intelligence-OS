// SPEC-098 — CADA COISA SABE DE QUEM É. O guarda do lado da TELA e do BFF,
// escrito ANTES do código (protocolo AAA v11.2 §4: quem faz a prova não faz a
// resposta — o DESENHISTA escreve o teste, os builders o deixam verde).
//
// 🔴 ESTE ARQUIVO NASCE VERMELHO, E É PARA NASCER. Em `821752f` (a cópia limpa
// `../AutoBrokers-FIX-gate0`) ele imprime os itens do GATE ZERO (BLOCO 0) que
// são do lado da tela/BFF:
//
//    (i)    `capture_status` tem ZERO leitores em `.tsx`             → [1]
//    (ii)   seis chaves de código aparecem na tela (R11 da 097)      → [2]
//    (iii)  `brand.py` serializa `erro`, a tela lê `error`           → [3]
//    (iv)   não existe seção "Jeito de atender"                      → [4]
//    (v)    billing/company-data/n8n agem na empresa PRIMÁRIA        → [5]
//    (vi)   as proxies chamam o smith-api SEM `X-Internal-Key`       → [6]
//    (vii)  `chat/session`, `users/status`, `bootstrap-tenant` sem autoridade → [7]
//    (viii) `leads/identify` é um oráculo público de PII             → [7-bis]
//    (ix)   a troca de empresa não reescreve o `localStorage`        → [8]
//    (x)    o envio humano do painel não grava `sender_user_id`      → [9]
//
// Um guarda que nasce verde não mediu nada (CLAUDE.md §9.3): tudo que já estiver
// verde em `821752f` é SUSPEITO e está anotado no relatório do desenhista.
//
// ─────────────────────────────────────────────────────────────────────────────
// O QUE ELE GUARDA — a medição de 06/09/2026 (SPEC-098 §1)
// ─────────────────────────────────────────────────────────────────────────────
//
//   📊 §1.1  `BrandIdentityClient.tsx` (632 linhas): `capture_status` e
//            `capture_error` com 0 leitores; `failed` com paleta-fallback
//            aparece como marca válida; seis vazamentos de chave de código.
//   📊 §1.1  `brand.py:108` serializa `erro`, a tela lê `error` (`:103`) — toda
//            falha vira "A captura não encontrou o suficiente": 500, site vazio
//            e "sem fonte" ficam indistinguíveis.
//   📊 §1.3  `getCompanyIdFromSession` está copiado em 3 arquivos de billing e
//            lê `users_v2.company_id` (a PRIMÁRIA). Um sócio com AutoFleet ativa
//            vê e ALTERA a assinatura da Resulta — pelo NEXT.
//   📊 §1.3  `leads/identify` devolve `name` e `isNew` sem sessão, cookie ou
//            cabeçalho, com service role: um oráculo que diz se um e-mail é
//            cliente de qualquer corretora, e entrega o nome.
//   📊 §1.3  `lib/session.ts:33` congela `companyId` por 7–30 dias e a troca de
//            empresa (`TenantNav.tsx:68`) não reescreve.
//   📊 §1.4  `messages.sender_user_id` 0/11.981 nas saídas humanas.
//
// Nenhum desses defeitos trava nada. Todos respondem 200 — CLAUDE.md §9.5.
//
// ─────────────────────────────────────────────────────────────────────────────
// COMO ELE FUNCIONA — sem rede, sem banco, sem servidor
// ─────────────────────────────────────────────────────────────────────────────
//
// O molde de 095/096/097: o produto é transpilado com o TypeScript do projeto,
// carregado com um `require` falso e EXECUTADO sobre dublês. O dublê de Supabase
// APLICA os filtros e REGISTRA cada consulta; `getIronSession` devolve a sessão
// que o teste escolhe; `fetch` é dublado e GUARDA OS CABEÇALHOS — é assim que
// [6] prova que a chave interna sai.
//
// 🔴 CADA ASSERÇÃO EXECUTA O PRODUTO (CLAUDE.md §9.4). Regex sobre a fonte
// aparece em UM lugar — [CTL] conferindo a FORMA da declaração das mutações.
//
// Arquivo que o builder ainda não escreveu: o guarda captura a AUSÊNCIA, mostra
// a CAUSA CRUA e REPROVA com mensagem — nunca estoura (protocolo §0.3), e nunca
// diz "ainda não existe" quando a causa foi outra.
//
// ⛔ SEGURANÇA
//   · Sem rede, sem banco, sem escrita: os dublês são memória pura.
//   · NENHUM nome de pessoa, CPF, telefone real, apólice, placa, senha ou token.
//     As corretoras são sentinelas ("Corretora Alfa", "Corretora Beta") e os
//     telefones começam em +55 11 90000-0001.
//   · DUAS corretoras SEMPRE: Alfa é a do teste, Beta existe para provar que
//     nada dela atravessa (CLAUDE.md §7 — o backend usa service role).
//
// Rodar:  npm run test:de-quem-e
//         node scripts/cada-coisa-sabe-de-quem-e.test.mjs
//         node scripts/cada-coisa-sabe-de-quem-e.test.mjs --mutar [ID]
//
// ─────────────────────────────────────────────────────────────────────────────
// 🔴 MUTAÇÕES — e elas RODAM
// ─────────────────────────────────────────────────────────────────────────────
//
// ⚠️ As 17 da SPEC v1.1 estão divididas entre os dois guardas, e a divisão tem
// razão: uma mutação julgada por um placar que não vê a asserção vermelha é
// carimbo. As 15 do BACKEND moram em `backend/tests/test_cada_coisa_sabe_de_quem_e.py`;
// as DUAS do Next moram aqui, porque é aqui que o vermelho aparece.
//
//   ancora      a string EXATA que existe no código do PRODUTO. ⛔ NUNCA em
//               comentário: comentário mutado não muda comportamento nenhum, e
//               a mutação ficaria verde por construção.
//   substituto  o defeito de volta, escrito por extenso.
//   vermelho    os NOMES de asserção que TÊM de ficar vermelhos.
//
// ⛔ A mutação é por CÓPIA e o restauro mora num `finally`: o arquivo volta byte
// a byte, e o runner CONFERE isso (hash antes/depois + `git status` idêntico).
// Rode com a árvore parada — enquanto os builders editam `app/` e `lib/`, o
// restauro apagaria a edição daquele segundo.
//
export const MUTACOES = [
  { id: 'M9-BIS', arquivo: 'app/api/leads/identify/route.ts',
    o_que: 'a resposta de `leads/identify` volta a trazer o `name` do lead',
    reprova: '[7-bis] (o oráculo público de PII volta — §1.3/E9)',
    // ⚠️ a âncora é a resposta do lead JÁ EXISTENTE (`route.ts:76`), não a do
    //    lead novo: era ela que carregava o `name` da pessoa, e é ela que
    //    responde "esta pessoa é cliente de vocês?".
    ancora: 'return NextResponse.json({ leadId: existing.id });',
    substituto: 'return NextResponse.json({ leadId: existing.id, isNew: false, name: existing.name });',
    vermelho: ['[7-bis] a resposta de `leads/identify` traz SÓ `leadId`'] },

  { id: 'M12', arquivo: 'components/layout/TenantNav.tsx',
    o_que: 'a troca de empresa volta a NÃO reescrever o `localStorage`',
    reprova: '[8] (o navegador guarda a corretora antiga por até 30 dias — §1.3/U4.c)',
    ancora: '        atualizarEmpresaNaSessaoLocal(j?.company_id || j?.companyId || null);',
    substituto: '        /* _MUTADO_098_M12 — a sessão local fica com a empresa antiga */',
    vermelho: ['[8] a troca de empresa REESCREVE `companyId`'] },
];

//: as 15 que moram no guarda irmão, em python.
export const MUTACOES_DO_IRMAO = 15;
/** Os 17 marcadores que a SPEC v1.1 §4 nomeia. Contar não basta: um `M16`
 *  inventado no lugar de `M13` daria a mesma soma e mediria outra coisa. */
export const MUTACOES_DA_SPEC = [
  'M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M6-BIS', 'M7', 'M8', 'M9', 'M9-BIS',
  'M10', 'M11', 'M12', 'M13', 'M14', 'M15',
];
/** As que os guardas ACRESCENTARAM, com o motivo escrito (§11: nada silencioso).
 *  `M-RAG` cobre o bloco [G-RAG] da §4 nota 6, que a SPEC pede e não numera. */
export const MUTACOES_ACRESCENTADAS = { 'M-RAG': '[G-RAG] · §4 nota 6 — a coleção do RAG' };
export const TOTAL_DE_MUTACOES_DA_SPEC = MUTACOES_DA_SPEC.length;

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const RAIZ = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const ts = require('typescript');

// ─────────────────────────────────────────────────────────────────────────────
// As sentinelas
// ─────────────────────────────────────────────────────────────────────────────
const CO_ALFA = 'co-alfa-0000-4000-8000-000000000001';
const CO_BETA = 'co-beta-0000-4000-8000-000000000002';
const U_SOCIO = 'u-socio-0000-4000-8000-000000000001';
const CONVERSA_A = '11111111-1111-4111-8111-111111111111';
const CHAVE_BOA = 'chave-interna-do-bff-098';
const TELEFONE = '5511900000001';

const CAMINHO_TELA = 'app/dashboard/personalizacao/corretora/identidade/BrandIdentityClient.tsx';
const CAMINHO_BFF_MARCA = 'app/api/dashboard/brand-identity/route.ts';
const CAMINHO_BFF_JEITO = 'app/api/dashboard/brand-identity/jeito/route.ts';
const CAMINHO_BILLING = 'app/api/billing/subscription/route.ts';
const CAMINHO_COMPANY_DATA = 'app/api/user/company-data/route.ts';
const CAMINHO_N8N = 'app/api/n8n/route.ts';
const CAMINHO_CHAT_SESSION = 'app/api/chat/session/route.ts';
const CAMINHO_USERS_STATUS = 'app/api/admin/users/status/route.ts';
const CAMINHO_BOOTSTRAP = 'app/api/admin/sandbox/bootstrap-tenant/route.ts';
const CAMINHO_LEADS = 'app/api/leads/identify/route.ts';
const CAMINHO_SESSION_TS = 'lib/session.ts';
const CAMINHO_TENANTNAV = 'components/layout/TenantNav.tsx';
const CAMINHO_CONVERSA = 'app/api/dashboard/conversas/[id]/route.ts';
const CAMINHO_MESSAGES = 'app/api/messages/route.ts';

/** As proxies que passam a mandar a chave interna (U4.a). */
const PROXIES_COM_CHAVE = [
  'app/api/sanitization/jobs/route.ts',
  'app/api/sanitization/jobs/[jobId]/route.ts',
  'app/api/sanitization/download/[jobId]/route.ts',
  'app/api/sanitization/upload/route.ts',
  'app/api/chat/session/route.ts',
];

/** 📊 §1.1 R11 — as chaves de código que NÃO podem aparecer na tela. */
const LISTA_NEGRA = ['google_business', 'HTTP 429', 'EgressBlockedError',
  'display_name', 'about_md', 'field_path', 'capture_status', 'tone_proposto'];

// ─────────────────────────────────────────────────────────────────────────────
// Ferramentas de arquivo
// ─────────────────────────────────────────────────────────────────────────────
function existe(rel) { return fs.existsSync(path.join(RAIZ, rel)); }
function fonte(rel) { return fs.readFileSync(path.join(RAIZ, rel), 'utf8'); }

/**
 * 🔴 A CAUSA CRUA (a lição da 096). "MODULO_AUSENTE" só quando o arquivo não
 * existe mesmo; qualquer outra falha aparece com o erro de verdade, porque
 * "ainda não existe" dito no lugar errado manda o builder procurar onde não é.
 */
function porQue(rel, erro) {
  if (!existe(rel)) return `MODULO_AUSENTE: \`${rel}\` ainda não foi escrito`;
  return `${erro && erro.name ? erro.name : 'Erro'}: ${erro && erro.message ? erro.message : erro}`;
}

function carregarTS(caminhoRelativo, resolverImport, opcoes = {}) {
  const saida = ts.transpileModule(fonte(caminhoRelativo), {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020,
      esModuleInterop: true,
      jsx: opcoes.jsx ?? ts.JsxEmit.None,
    },
    fileName: caminhoRelativo,
  }).outputText;
  const js = opcoes.reactGlobal ? `const React = ${opcoes.reactGlobal};\n${saida}` : saida;
  const mod = { exports: {} };
  const req = (id) => {
    const r = resolverImport(id);
    if (r === undefined) throw new Error(`import nao previsto no teste: ${id}`);
    return r;
  };
  // eslint-disable-next-line no-new-func
  new Function('require', 'module', 'exports', '__REACT__', js)(req, mod, mod.exports, opcoes.react);
  return mod.exports;
}

// ─────────────────────────────────────────────────────────────────────────────
// O dublê de Supabase — filtros APLICADOS e toda consulta REGISTRADA
// ─────────────────────────────────────────────────────────────────────────────
function valorDe(linha, coluna) {
  if (!/->/.test(String(coluna))) return linha[coluna];
  let v = linha;
  for (const p of String(coluna).split(/->>|->/).map((s) => s.replace(/^'|'$/g, '').trim())) {
    if (v == null) return undefined;
    v = v[p];
  }
  return v;
}

function dubleSupabase(linhasPorTabela, registro, falhar = new Set()) {
  function tabela(nome) {
    const consulta = {
      tabela: nome, op: 'select', colunas: '', opcoes: {},
      predicados: [], limite: null, payload: null,
    };
    registro.push(consulta);
    const cadeia = {};
    cadeia.select = (colunas, opcoes) => {
      if (!consulta.payload) consulta.op = 'select';
      consulta.colunas = String(colunas ?? '');
      consulta.opcoes = opcoes ?? {};
      return cadeia;
    };
    cadeia.insert = (payload) => { consulta.op = 'insert'; consulta.payload = payload; return cadeia; };
    cadeia.update = (payload) => { consulta.op = 'update'; consulta.payload = payload; return cadeia; };
    cadeia.upsert = (payload) => { consulta.op = 'upsert'; consulta.payload = payload; return cadeia; };
    cadeia.delete = () => { consulta.op = 'delete'; return cadeia; };
    for (const op of ['eq', 'neq', 'gt', 'gte', 'lt', 'lte', 'in', 'is', 'not']) {
      cadeia[op] = (coluna, valor, extra) => {
        consulta.predicados.push({ op, coluna, valor, extra });
        return cadeia;
      };
    }
    cadeia.or = (expr) => { consulta.predicados.push({ op: 'or', coluna: '(or)', valor: String(expr) }); return cadeia; };
    cadeia.ilike = (c, p) => { consulta.predicados.push({ op: 'ilike', coluna: c, valor: p }); return cadeia; };
    cadeia.order = () => cadeia;
    cadeia.limit = (n) => { consulta.limite = n; return cadeia; };
    cadeia.range = () => cadeia;

    const casa = (l, p) => {
      if (p.op === 'or') return true;
      const v = valorDe(l, p.coluna);
      switch (p.op) {
        case 'eq': return String(v) === String(p.valor);
        case 'neq': return String(v) !== String(p.valor);
        case 'in': return (p.valor ?? []).map(String).includes(String(v));
        case 'is': return p.valor === null || p.valor === 'null' ? v == null : v === p.valor;
        default: return true;
      }
    };
    const resolver = () => {
      if (falhar.has(nome)) {
        const e = new Error(`FONTE_INDISPONIVEL: a consulta a "${nome}" falhou (dublê)`);
        e.__fonte = nome;
        throw e;
      }
      if (consulta.op !== 'select') {
        const regs = Array.isArray(consulta.payload) ? consulta.payload : [consulta.payload];
        const saida = [];
        for (const r of regs) {
          const alvos = (linhasPorTabela[nome] ?? []).filter((l) => consulta.predicados.every((p) => casa(l, p)));
          if (consulta.op === 'update' && alvos.length) {
            for (const l of alvos) Object.assign(l, r);
            saida.push(...alvos.map((l) => ({ ...l })));
          } else if (consulta.op !== 'update' && consulta.op !== 'delete') {
            const linha = { id: `${nome.slice(0, 3)}-${(linhasPorTabela[nome] || []).length + 1}`, ...r };
            (linhasPorTabela[nome] = linhasPorTabela[nome] || []).push(linha);
            saida.push(linha);
          }
        }
        return saida;
      }
      let linhas = (linhasPorTabela[nome] ?? []).filter((l) => consulta.predicados.every((p) => casa(l, p)));
      if (consulta.limite != null) linhas = linhas.slice(0, consulta.limite);
      return linhas;
    };
    const corpo = () => {
      try {
        const linhas = resolver();
        const o = consulta.opcoes || {};
        return o.head
          ? { data: null, count: linhas.length, error: null }
          : { data: linhas, count: o.count ? linhas.length : null, error: null };
      } catch (e) {
        return { data: null, count: null, error: { message: String(e.message), code: 'FONTE_INDISPONIVEL' } };
      }
    };
    // 🔴 `.single()`/`.maybeSingle()` devolvem UM registro no cliente real. Um
    //    dublê que devolvesse a lista faria o produto estourar, e o guarda leria
    //    isso como defeito do produto.
    cadeia.maybeSingle = () => { const c = corpo(); return Promise.resolve({ data: (c.data || [])[0] ?? null, error: c.error }); };
    cadeia.single = () => {
      const c = corpo();
      const l = c.data || [];
      return Promise.resolve({ data: l[0] ?? null, error: c.error || (l.length ? null : { message: 'no rows' }) });
    };
    cadeia.then = (ok, err) => Promise.resolve(corpo()).then(ok, err);
    cadeia.catch = (f) => Promise.resolve(corpo()).catch(f);
    return cadeia;
  }
  return { from: tabela };
}

/** 📊 §1.4 — dois tenants, e um SÓCIO das duas (os 3 usuários com >1 vínculo). */
function mundo() {
  return {
    companies: [
      { id: CO_ALFA, name: 'Corretora Alfa', allow_web_search: false, webhook_url: 'https://n8n.invalid/alfa', use_langchain: false },
      { id: CO_BETA, name: 'Corretora Beta', allow_web_search: true, webhook_url: 'https://n8n.invalid/beta', use_langchain: false },
    ],
    users_v2: [
      { id: U_SOCIO, company_id: CO_ALFA, status: 'active', name: 'Socio Canario', email: 'socio@exemplo.invalid' },
    ],
    company_members: [
      { id: 'cm-1', company_id: CO_ALFA, user_id: U_SOCIO, role: 'admin_company', status: 'active' },
      { id: 'cm-2', company_id: CO_BETA, user_id: U_SOCIO, role: 'admin_company', status: 'active' },
    ],
    subscriptions: [
      { id: 'sb-alfa', company_id: CO_ALFA, status: 'active', current_period_end: null, plans: { id: 'pl', name: 'Alfa', price_brl: '100' } },
      { id: 'sb-beta', company_id: CO_BETA, status: 'active', current_period_end: null, plans: { id: 'pl', name: 'Beta', price_brl: '200' } },
    ],
    company_credits: [
      { company_id: CO_ALFA, balance_brl: '10' },
      { company_id: CO_BETA, balance_brl: '20' },
    ],
    conversations: [
      { id: CONVERSA_A, company_id: CO_ALFA, user_id: U_SOCIO,
        session_id: 'ss-098-1', channel: 'whatsapp',
        user_phone: TELEFONE, user_name: 'Segurado Canario', status: 'open',
        claimed_by: U_SOCIO, claimed_by_name: 'Socio Canario', resolvido_em: null,
        ficha_atendimento: {}, last_message_at: new Date().toISOString() },
    ],
    messages: [],
    leads: [{ id: 'ld-1', company_id: CO_ALFA, email: 'quem@exemplo.invalid', name: 'Nome Que Nao Pode Vazar' }],
    agents: [{ id: 'ag-alfa', company_id: CO_ALFA, agent_role: 'attendance', is_active: false }],
    documents: [],
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// O placar — três verbos (o molde de 095/096/097, protocolo §5)
// ─────────────────────────────────────────────────────────────────────────────
const falhas = [];
function checar(problemas, nome) {
  if (problemas.length === 0) { console.log(`  OK  ${nome}`); }
  else { falhas.push(nome); console.log(`  X   ${nome}`); for (const p of problemas) console.log(`        ${p}`); }
}
function controle(problemas, nome) {
  if (problemas.length > 0) { console.log(`  OK  CONTROLE ${nome} — o guarda acusou (${problemas.length})`); }
  else { falhas.push(`CONTROLE ${nome}`); console.log(`  X   CONTROLE ${nome} — o guarda NAO acusou; ele nao guarda nada`); }
}

// ─────────────────────────────────────────────────────────────────────────────
// Executar as rotas do Next sobre os dublês
// ─────────────────────────────────────────────────────────────────────────────
class NextResponseFalsa {
  static json(body, init) { return { __json: true, body, status: init?.status ?? 200 }; }
}
const NEXT_SERVER = { NextResponse: NextResponseFalsa, NextRequest: class {} };

async function silenciando(fn) {
  const orig = { log: console.log, error: console.error, warn: console.warn, info: console.info };
  console.log = console.error = console.warn = console.info = () => {};
  try { return await fn(); } finally { Object.assign(console, orig); }
}

/**
 * O resolvedor de imports comum. `sessao` é o que `resolveSessionCompany`
 * devolve; `ironSession` é o que `getIronSession` devolve — as rotas de billing
 * usam a SEGUNDA, e é aí que a empresa ATIVA se perde hoje.
 */
function resolvedor({ supabase, sessao, ironSession, fetchDublado, extras = {} }) {
  const resolver = (id) => {
    if (id in extras) return extras[id];
    if (id === 'next/server') return NEXT_SERVER;
    if (id === 'next/headers') return { cookies: async () => ({ get: () => undefined, set: () => {} }) };
    if (id === 'iron-session') return { getIronSession: async (_c, opcoes) => ironSession(opcoes) };
    if (id === '@supabase/supabase-js') return { createClient: () => supabase };
    if (id === '@/lib/vault/server' || id === '@/lib/auxiliaries/server') {
      return { resolveSessionCompany: async () => sessao, getSupabaseAdmin: () => supabase };
    }
    if (id === '@/lib/iron-session') {
      return {
        sessionOptions: { __qual: 'usuario' }, adminSessionOptions: { __qual: 'admin' },
        SessionData: class {}, AdminSessionData: class {},
      };
    }
    if (id === '@/lib/backend-url') {
      return { getBackendUrl: () => 'http://backend.local', BackendUrlError: class extends Error {} };
    }
    if (id === '@/lib/logger') {
      return { logSystemAction: async () => {}, getClientInfo: () => ({ ipAddress: '0.0.0.0', userAgent: 'guarda' }) };
    }
    if (id.startsWith('@/lib/admin/')) {
      // 🔴 os modulos REAIS: `assertSameOrigin`, `sameOriginOk` e
      //    `requireCompanyMember` sao parte do produto, e troca-los por `{}`
      //    faria o guarda medir um caminho que nao existe (a licao da 097:
      //    teste de corredor chama o MOTOR).
      const rel = `lib/admin/${id.slice('@/lib/admin/'.length)}.ts`;
      if (existe(rel)) return carregarTS(rel, resolver);
    }
    if (id === '@/lib/atendimento/a-nota-da-atendente') return carregarTS('lib/atendimento/a-nota-da-atendente.ts', () => ({}));
    if (id === '@/lib/atendimento/claims-shadow') return carregarTS('lib/atendimento/claims-shadow.ts', () => ({}));
    if (id === '@/lib/atendimento/claims-shadow-vocab.json') return { default: JSON.parse(fonte('lib/atendimento/claims-shadow-vocab.json')) };
    if (id === '@/lib/session') return carregarTS(CAMINHO_SESSION_TS, () => ({}));
    if (id.startsWith('@/lib/') || id.startsWith('@/components/') || id.startsWith('@/hooks/')) return {};
    return {};
  };
  return resolver;
}

/** Executa um handler de rota. NUNCA estoura: devolve `{ erro }` com a causa. */
async function executarRota(caminho, {
  metodo = 'GET', url = 'http://t.local/x', corpo = null, cabecalhos = {},
  linhas, sessao = null, ironSession = () => ({}), fetchDublado = null, extras = {},
  params = null,
} = {}) {
  const mundoDaVez = linhas || mundo();
  const registro = [];
  const chamadas = [];
  const supabase = dubleSupabase(mundoDaVez, registro);
  const fetchAnterior = globalThis.fetch;
  globalThis.fetch = async (u, init = {}) => {
    chamadas.push({ url: String(u), init, headers: { ...(init.headers || {}) } });
    if (fetchDublado) return fetchDublado(String(u), init);
    return { ok: true, status: 200, json: async () => ({ ok: true }) };
  };
  try {
    if (!existe(caminho)) return { erro: porQue(caminho), registro, chamadas, mundo: mundoDaVez };
    const rota = carregarTS(caminho, resolvedor({ supabase, sessao, ironSession, fetchDublado, extras }));
    const handler = rota[metodo];
    if (typeof handler !== 'function') {
      return { erro: `a rota \`${caminho}\` não exporta \`${metodo}\``, registro, chamadas, mundo: mundoDaVez };
    }
    const req = {
      method: metodo,
      url,
      nextUrl: new URL(url),
      headers: { get: (n) => cabecalhos[n] ?? cabecalhos[String(n).toLowerCase()] ?? null },
      json: async () => (corpo ?? {}),
      // ⚠️ as proxies de upload leem `formData()`. Sem isto elas caem no
      //    `catch` e o guarda leria "nao chamou o backend" como se fosse
      //    ausencia de chave -- medindo a coisa errada.
      formData: async () => {
        const fd = new FormData();
        fd.append('company_id', CO_ALFA);
        fd.append('file', new Blob(['documento sintetico']), 'sintetico.txt');
        return fd;
      },
      cookies: { get: () => undefined },
    };
    const ctx = params ? { params: Promise.resolve(params) } : undefined;
    const resposta = await silenciando(() => handler(req, ctx));
    return {
      status: resposta?.status ?? 200,
      corpo: resposta?.body ?? resposta,
      registro, chamadas, mundo: mundoDaVez,
    };
  } catch (e) {
    return { erro: porQue(caminho, e), registro, chamadas, mundo: mundoDaVez };
  } finally {
    globalThis.fetch = fetchAnterior;
  }
}

/** As corretoras que uma execução consultou — é assim que [5] mede o tenant. */
function empresasConsultadas(registro) {
  const ids = new Set();
  for (const c of registro) {
    for (const p of c.predicados || []) {
      // ⚠️ em `companies` a coluna da corretora chama-se `id`. Contar só
      //    `company_id` deixaria `user/company-data` e `n8n` -- que leem
      //    `companies` direto -- sem medição nenhuma.
      const eDaEmpresa = p.coluna === 'company_id'
        || (c.tabela === 'companies' && p.coluna === 'id');
      if (eDaEmpresa && p.op === 'eq') ids.add(String(p.valor));
    }
  }
  return [...ids];
}

// ─────────────────────────────────────────────────────────────────────────────
// A TELA, EXECUTADA — um React falso com o CONTRATO real do React 18
//
// (o molde da 095, `relatorios-dizem-o-que-sao.test.mjs` [13]–[16]): render →
// commit → flush dos efeitos na ordem de declaração; `useState(init)` só lê o
// inicializador na MONTAGEM; um `fetch` só resolve DEPOIS do flush síncrono.
// Devolve a ÁRVORE, e a árvore vira TEXTO — é sobre esse texto que [1], [2] e
// [4] falam. Nada é desenhado.
// ─────────────────────────────────────────────────────────────────────────────
function reactFalso() {
  let slots = [];
  let cursor = 0;
  let efeitos = [];
  let sujo = false;
  const filaDeRede = [];
  const elementos = [];

  function useState(inicial) {
    const i = cursor++;
    if (!(i in slots)) slots[i] = { v: typeof inicial === 'function' ? inicial() : inicial };
    const s = slots[i];
    return [s.v, (nv) => {
      const p = typeof nv === 'function' ? nv(s.v) : nv;
      if (!Object.is(p, s.v)) { s.v = p; sujo = true; }
    }];
  }
  function useRef(v) { const i = cursor++; if (!(i in slots)) slots[i] = { v: { current: v } }; return slots[i].v; }
  function useCallback(fn) { cursor++; return fn; }
  function useMemo(fn) { cursor++; return fn(); }
  function useEffect(fn, deps) {
    const i = cursor++;
    const antes = slots[i];
    const mudou = !antes || !deps || !antes.deps || deps.length !== antes.deps.length
      || deps.some((d, k) => !Object.is(d, antes.deps[k]));
    slots[i] = { deps };
    if (mudou) efeitos.push(fn);
  }
  function createElement(tipo, props, ...filhos) {
    const el = { tipo, props: props || {}, filhos };
    elementos.push(el);
    return el;
  }
  const React = {
    useState, useEffect, useLayoutEffect: useEffect, useRef, useCallback, useMemo,
    createElement, Fragment: 'FRAGMENT',
  };
  // 🔴 UM MINI-RECONCILIADOR, e ele é obrigatório.
  //
  // `createElement(AbaJeito, props)` devolve um NÓ, não a árvore dela: sem
  // expandir os componentes-função, a seção "Jeito de atender" simplesmente não
  // existe para o guarda — e o teste ficaria vermelho apontando para uma tela
  // que está certa (ou verde apontando para uma que está errada). Cada instância
  // tem o SEU armazém de hooks, endereçado pelo caminho na árvore: um `slots`
  // global embaralharia o estado dos filhos a cada render.
  const armazens = new Map();
  function expandir(no, caminho = 'r', profundidade = 0) {
    if (no == null || typeof no !== 'object' || profundidade > 40) return no;
    if (Array.isArray(no)) return no.map((n, i) => expandir(n, `${caminho}.${i}`, profundidade + 1));
    if (typeof no.tipo !== 'function') {
      const filhos = expandir([].concat(no.filhos || []), `${caminho}f`, profundidade + 1);
      const props = { ...(no.props || {}) };
      if (props.children) props.children = expandir([].concat(props.children), `${caminho}c`, profundidade + 1);
      return { ...no, props, filhos };
    }
    const chave = `${caminho}:${no.tipo.name || 'anon'}`;
    if (!armazens.has(chave)) armazens.set(chave, []);
    const meus = armazens.get(chave);
    const salvos = slots;
    const salvoCursor = cursor;
    slots = meus;
    cursor = 0;
    let saida = null;
    try {
      saida = no.tipo({ ...(no.props || {}), children: no.filhos });
    } catch (e) {
      saida = { tipo: 'span', props: {}, filhos: [`[COMPONENTE ${chave} ESTOUROU: ${e.message}]`] };
    } finally {
      slots = salvos;
      cursor = salvoCursor;
    }
    return expandir(saida, `${chave}>`, profundidade + 1);
  }

  return {
    React,
    expandir,
    estado: () => ({ slots, elementos, filaDeRede }),
    passo(Componente, props) {
      cursor = 0; efeitos = []; sujo = false; elementos.length = 0;
      let arvore = null;
      try { arvore = Componente(props || {}); } catch (e) { arvore = { __erro: e }; }
      for (const fn of efeitos.slice()) { try { fn(); } catch { /* efeito do produto */ } }
      return { arvore, sujo: () => sujo };
    },
    resetar() { slots = []; },
    limparRede: () => { while (filaDeRede.length) filaDeRede.shift()(); },
    enfileirar: (f) => filaDeRede.push(f),
  };
}

/** Todo o texto que uma árvore carrega — rótulos, filhos, placeholders, títulos. */
function textoDeArvore(no, vistos = new Set()) {
  if (no == null || no === false || no === true) return '';
  if (typeof no === 'string' || typeof no === 'number') return String(no) + ' ';
  if (Array.isArray(no)) return no.map((n) => textoDeArvore(n, vistos)).join('');
  if (typeof no === 'function') return '';
  if (typeof no !== 'object') return '';
  if (vistos.has(no)) return '';
  vistos.add(no);
  const p = no.props || {};
  const pedacos = [];
  for (const chave of ['title', 'subtitle', 'label', 'placeholder', 'alt', 'aria-label', 'value', 'name']) {
    if (typeof p[chave] === 'string') pedacos.push(p[chave] + ' ');
  }
  if (typeof p.type === 'string') pedacos.push(`[input:${p.type}] `);
  pedacos.push(textoDeArvore([].concat(no.filhos || [], p.children || []), vistos));
  return pedacos.join('');
}

/** Todos os nós de um tipo (por exemplo `input`) — para contar os rádios. */
function nosDe(no, tipo, achados = [], vistos = new Set()) {
  if (no == null || typeof no !== 'object') return achados;
  if (Array.isArray(no)) { for (const n of no) nosDe(n, tipo, achados, vistos); return achados; }
  if (vistos.has(no)) return achados;
  vistos.add(no);
  if (no.tipo === tipo) achados.push(no);
  nosDe([].concat(no.filhos || [], (no.props || {}).children || []), tipo, achados, vistos);
  return achados;
}

/** O perfil que a rota BFF devolveria para um `capture_status` qualquer. */
function perfilDe(status, extra = {}) {
  return {
    ok: true,
    profile: {
      id: 'bp-alfa', company_id: CO_ALFA,
      website_url: 'https://alfa.invalid', instagram_url: 'https://instagram.invalid/alfa',
      display_name: 'Corretora Alfa', legal_name: null, tagline: null,
      mission: null, about_md: null, services: null, differentiators: null,
      service_area: null, founded_year: null, susep_code: null, insurers: null,
      // 🔴 §1.1 — a paleta EXISTE mesmo nas linhas `empty`/`failed`: é por isso
      //    que hoje uma captura que FALHOU aparece como marca válida.
      palette: { primary: '#123456', scales: { primary: {} }, themes: { light: {} } },
      typography: null, visual_style: null, tone: {},
      capture_status: status, capture_error: extra.capture_error ?? null,
      completeness: 0, is_published: false,
      ...(extra.profile || {}),
    },
    provenance: extra.provenance ?? {
      display_name: { field_path: 'display_name', source_kind: 'website', source_detail: 'https://alfa.invalid', confidence: 0.85, human_edited: false },
    },
    sources: extra.sources ?? [
      { kind: 'website', url: 'https://alfa.invalid', status: 'fetched', http_status: 200, error: null },
      // 🔴 §1.1 — a fonte que falhou. Hoje ela chega à tela como
      //    `instagram` + `HTTP 429`; a R10 exige a frase de gente.
      { kind: 'instagram', url: 'https://instagram.invalid/alfa', status: 'blocked', http_status: 429, error: 'HTTP 429' },
      { kind: 'google_business', url: null, status: 'failed', http_status: null, error: 'EgressBlockedError' },
    ],
    assets: [],
    ...(extra.raiz || {}),
  };
}

/** Renderiza a tela de identidade num estado, clicando em todas as abas. */
async function renderizarTela(status, extra = {}) {
  if (!existe(CAMINHO_TELA)) return { erro: porQue(CAMINHO_TELA) };
  const r = reactFalso();
  const fetchAnterior = globalThis.fetch;
  const pedidos = [];
  globalThis.fetch = async (u, init = {}) => {
    pedidos.push({ url: String(u), init });
    const corpo = String(u).includes('brand-identity') ? perfilDe(status, extra) : { ok: true };
    return { ok: true, status: 200, json: async () => corpo };
  };
  try {
    const mod = carregarTS(CAMINHO_TELA, (id) => {
      if (id === 'react') return r.React;
      if (id === 'next/navigation') return { useRouter: () => ({ push() {}, refresh() {} }) };
      if (id === 'sonner') return { toast: { success() {}, error() {} } };
      if (id === '@/lib/session') return carregarTS(CAMINHO_SESSION_TS, () => ({}));
      if (id.startsWith('@/')) return new Proxy({}, { get: () => () => null });
      return {};
    }, { jsx: ts.JsxEmit.React, reactGlobal: '__REACT__', react: r.React });
    const Componente = mod.BrandIdentityClient || mod.default;
    if (typeof Componente !== 'function') {
      return { erro: `\`${CAMINHO_TELA}\` não exporta \`BrandIdentityClient\`` };
    }
    let ultimo = null;
    const rodar = async () => {
      ultimo = r.passo(Componente);
      let n = 0;
      // os efeitos disparam fetch; o fetch resolve em microtask.
      while (n++ < 6) {
        await Promise.resolve();
        ultimo = r.passo(Componente);
      }
      return ultimo;
    };
    await silenciando(rodar);
    // 🔴 As abas: o texto de UMA aba não é o texto da tela. O guarda CLICA em
    //    cada botão de aba (executando o `onClick` do produto) e junta tudo.
    const arvores = [r.expandir(ultimo.arvore)];
    const textos = [textoDeArvore(arvores[0])];
    const botoes = nosDe(arvores[0], 'button').filter((b) => typeof b.props?.onClick === 'function');
    for (const b of botoes) {
      try {
        b.props.onClick({ preventDefault() {}, stopPropagation() {} });
      } catch { /* o clique do produto pode pedir rede; o dublê responde */ }
      await Promise.resolve();
      const novo = await silenciando(async () => r.passo(Componente));
      novo.expandida = r.expandir(novo.arvore);
      arvores.push(novo.expandida);
      textos.push(textoDeArvore(novo.expandida));
      ultimo = novo;
    }
    // ⚠️ `arvores` guarda TODAS as passagens (uma por botão clicado, e as abas
    //    são botões). Procurar um rádio só na ÚLTIMA acharia a aba em que o
    //    guarda parou — nunca a que interessa.
    return { arvore: arvores[arvores.length - 1], arvores,
             texto: textos.join('\n'), textos, pedidos };
  } catch (e) {
    return { erro: porQue(CAMINHO_TELA, e) };
  } finally {
    globalThis.fetch = fetchAnterior;
  }
}

// ═════════════════════════════════════════════════════════════════════════════
// `--mutar [ID]` — O PAINEL DE MUTAÇÃO, E ELE RODA
// ═════════════════════════════════════════════════════════════════════════════
if (process.argv.includes('--mutar')) {
  const pedido = process.argv[process.argv.indexOf('--mutar') + 1];
  const alvo = pedido && !pedido.startsWith('--') ? String(pedido).toUpperCase() : null;
  const lista = alvo ? MUTACOES.filter((m) => m.id.toUpperCase() === alvo) : MUTACOES;
  if (alvo && !lista.length) {
    console.error(`⛔ não existe mutação "${alvo}" neste guarda. Ids: ${MUTACOES.map((m) => m.id).join(', ')}`);
    console.error('   (as outras 15 da SPEC moram em backend/tests/test_cada_coisa_sabe_de_quem_e.py)');
    process.exit(1);
  }

  const digest = (t) => crypto.createHash('sha256').update(t).digest('hex');
  const gitStatus = () => {
    const r = spawnSync('git', ['status', '--short'], { cwd: RAIZ, encoding: 'utf8' });
    return String(r.stdout || '').split('\n').map((l) => l.trim()).filter(Boolean).sort().join('\n');
  };

  const abrigo = fs.mkdtempSync(path.join(os.tmpdir(), 'mutar-098-'));
  const statusAntes = gitStatus();
  let emAberto = null;
  const restaurar = () => {
    if (!emAberto) return;
    try { fs.copyFileSync(emAberto.bak, emAberto.caminho); } catch { /* último recurso */ }
    emAberto = null;
  };
  process.on('exit', restaurar);
  for (const sinal of ['SIGINT', 'SIGTERM']) {
    process.on(sinal, () => { restaurar(); process.exit(130); });
  }

  console.log('='.repeat(78));
  console.log(`  🔴 PAINEL DE MUTAÇÃO — ${lista.length} do guarda da TELA · SPEC-098`);
  console.log('     (as outras 15 rodam em `python tests/test_cada_coisa_sabe_de_quem_e.py --mutar`)');
  console.log(`     backups em ${abrigo} · restauro por CÓPIA, sempre`);
  console.log('='.repeat(78));

  // 🔴 A LINHA DE BASE. Sem ela a mutação se creditaria pelo vermelho que JÁ
  //    existia — e no gate zero, onde quase tudo está vermelho, TODA mutação
  //    pareceria boa (CLAUDE.md §9.2).
  const vermelhosDe = (saida) => saida.split('\n')
    .filter((l) => /^\s{2}X\s/.test(l))
    .map((l) => l.replace(/^\s*X\s+/, '').trim());
  const corridaBase = spawnSync(process.execPath, [fileURLToPath(import.meta.url)], {
    cwd: RAIZ, encoding: 'utf8', maxBuffer: 64 * 1024 * 1024,
  });
  const base = new Set(vermelhosDe(String(corridaBase.stdout || '') + String(corridaBase.stderr || '')));
  console.log(`\n  linha de BASE (árvore como está): ${base.size} asserção(ões) já vermelha(s)`);

  const placar = [];
  const ausentes = [];
  for (const m of lista) {
    const caminho = path.join(RAIZ, m.arquivo);
    // ⚠️ O alvo pode ainda não existir: os builders escrevem em paralelo. Isso
    //    NÃO é mutação verde — é mutação que não pôde rodar, e o placar diz isso
    //    com todas as letras para não virar "passou".
    if (!fs.existsSync(caminho)) {
      ausentes.push(m.id);
      console.log(`\n  ⏳ PENDENTE   ${m.id}  ${m.arquivo}`);
      console.log(`               alvo ainda inexistente — o builder não escreveu o arquivo`);
      continue;
    }
    const original = fs.readFileSync(caminho, 'utf8');
    const hashAntes = digest(original);
    const bak = path.join(abrigo, `${m.id}.bak`);
    fs.writeFileSync(bak, original);
    const veredito = { id: m.id, arquivo: m.arquivo, faltando: [], vermelhos: 0, erro: null };
    try {
      const ocorrencias = original.split(m.ancora).length - 1;
      if (ocorrencias === 0) {
        ausentes.push(m.id);
        veredito.pendente = `ÂNCORA AUSENTE: \`${m.ancora.trim().slice(0, 60)}…\` não existe em ${m.arquivo} (o builder ainda não escreveu essa linha)`;
        throw new Error(veredito.pendente);
      }
      if (ocorrencias > 1) {
        throw new Error(`ÂNCORA AMBÍGUA: aparece ${ocorrencias}× em ${m.arquivo} (tem de ser 1; desça a âncora até ficar única)`);
      }
      // ⛔ âncora só em comentário não muda comportamento nenhum.
      const semComentario = original
        .split('\n').filter((l) => !/^\s*(\/\/|\*|\/\*)/.test(l)).join('\n');
      if (!semComentario.includes(m.ancora)) {
        throw new Error(`ÂNCORA SÓ EM COMENTÁRIO: mutá-la não muda comportamento nenhum (a lição que custou duas rodadas na 097.1)`);
      }
      emAberto = { caminho, bak };
      fs.writeFileSync(caminho, original.replace(m.ancora, () => m.substituto));
      const r = spawnSync(process.execPath, [fileURLToPath(import.meta.url)], {
        cwd: RAIZ, encoding: 'utf8', maxBuffer: 64 * 1024 * 1024,
      });
      const saida = String(r.stdout || '') + String(r.stderr || '');
      const vermelhos = vermelhosDe(saida);
      const novos = vermelhos.filter((v) => !base.has(v));
      veredito.vermelhos = novos.length;
      veredito.rc = r.status;
      veredito.faltando = (m.vermelho || []).filter((e) => !novos.some((v) => v.includes(e)));
      veredito.acusaram = (m.vermelho || []).filter((e) => novos.some((v) => v.includes(e)));
      if (!novos.length) veredito.faltando.push('(nenhum nome NOVO ficou vermelho com a mutação aplicada)');
    } catch (e) {
      veredito.erro = String(e.message);
    } finally {
      fs.copyFileSync(bak, caminho);
      emAberto = null;
    }
    const hashDepois = digest(fs.readFileSync(caminho, 'utf8'));
    if (hashDepois !== hashAntes) veredito.naoRestaurou = true;
    if (veredito.pendente) { placar.push(veredito); continue; }

    const ok = !veredito.erro && !veredito.faltando.length && !veredito.naoRestaurou;
    console.log(`\n${ok ? '  🔴 VERMELHA' : '  🟢 VERDE   '}  ${m.id}  ${m.arquivo}`);
    console.log(`               ${m.o_que}`);
    if (veredito.erro) console.log(`               ⛔ ${veredito.erro}`);
    else {
      console.log(`               ${veredito.vermelhos} asserção(ões) NOVA(s) vermelha(s) (rc=${veredito.rc})`);
      for (const nome of veredito.acusaram || []) console.log(`               ✔ acusou: ${nome}`);
      for (const nome of veredito.faltando) console.log(`               ✘ NÃO acusou: ${nome}`);
    }
    if (veredito.naoRestaurou) console.log('               ⛔ O ARQUIVO NÃO VOLTOU AO ORIGINAL — confira antes de seguir');
    placar.push(veredito);
  }

  const statusDepois = gitStatus();
  const vermelhas = placar.filter((v) => !v.pendente && !v.erro && !v.faltando.length && !v.naoRestaurou);
  const verdes = placar.filter((v) => !v.pendente && !vermelhas.includes(v));

  console.log(`\n${'='.repeat(78)}`);
  console.log(`  PLACAR — ${vermelhas.length} VERMELHA(S) POR NOME · ${verdes.length} VERDE(S) · ${ausentes.length} PENDENTE(S)`);
  if (verdes.length) {
    console.log('\n  🟢 AS VERDES (uma mutação que não deixa nada vermelho é edição, não mutação):');
    for (const v of verdes) console.log(`     - ${v.id}: ${v.erro || v.faltando.join(' | ')}`);
  }
  if (ausentes.length) {
    console.log(`\n  ⏳ PENDENTES (alvo ainda inexistente — vermelho ESPERADO do gate zero): ${ausentes.join(', ')}`);
  }
  if (statusDepois !== statusAntes) {
    console.log('\n  ⛔ A ÁRVORE MUDOU durante o painel:');
    console.log(`     antes: ${JSON.stringify(statusAntes)}`);
    console.log(`     depois: ${JSON.stringify(statusDepois)}`);
  } else {
    console.log(`\n  ✔ árvore idêntica antes e depois (\`git status --short\`, ${statusAntes ? statusAntes.split('\n').length : 0} linha(s))`);
  }
  console.log('='.repeat(78));
  process.exit(verdes.length || statusDepois !== statusAntes ? 1 : 0);
}

// ─────────────────────────────────────────────────────────────────────────────
// A execução
//
// ⚠️ As variáveis vêm ANTES de tudo: `app/api/dashboard/brand-identity/route.ts`
// devolve "Serviço de identidade não configurado" sem elas, e o guarda mediria a
// falta de configuração do MEU processo em vez do contrato do produto. ⛔ Valores
// de mentira — nenhum segredo real entra aqui.
// ─────────────────────────────────────────────────────────────────────────────
process.env.BACKEND_INTERNAL_API_KEY = CHAVE_BOA;
process.env.ADMIN_API_KEY = CHAVE_BOA;
process.env.NEXT_PUBLIC_API_URL = 'http://backend.local';
process.env.BACKEND_URL = 'http://backend.local';
process.env.NEXT_PUBLIC_SUPABASE_URL = 'http://supabase.local';
process.env.SUPABASE_SERVICE_ROLE_KEY = 'service-role-de-mentira-098';

console.log('='.repeat(78));
console.log('  CADA COISA SABE DE QUEM É — o guarda da TELA e do BFF  (SPEC-098)');
console.log('='.repeat(78));

// ══ [1] CADA ESTADO DA CAPTURA TEM CARA PRÓPRIA ══════════════════════════════
//
// 📊 §1.1: `capture_status` tem 0 leitores em `.tsx` e os estados `empty ·
// failed · partial · capturing · manual` são a MESMA tela. Pior: `palette` não é
// nula nas linhas `empty`, então uma captura que FALHOU aparece como marca
// válida. O guarda RENDERIZA os seis estados e compara os textos.
console.log('\n[1] OS ESTADOS DA CAPTURA — cada um com cara própria (R10)');
const ESTADOS = ['empty', 'capturing', 'partial', 'captured', 'failed', 'manual'];
const telas = {};
for (const e of ESTADOS) {
  telas[e] = await renderizarTela(e, e === 'failed'
    ? { capture_error: 'o site demorou demais para responder' }
    : {});
}
console.log('      📊 telas renderizadas: '
  + ESTADOS.map((e) => `${e}=${telas[e].erro ? 'ERRO' : (telas[e].texto || '').length}c/${telas[e].textos ? telas[e].textos.length : 0}passagens`).join(' · '));
function analisarEstados() {
  const p = [];
  const erro = ESTADOS.find((e) => telas[e].erro);
  if (erro) { p.push(telas[erro].erro); return p; }
  const assinaturas = new Map();
  for (const e of ESTADOS) {
    const t = (telas[e].texto || '').replace(/\s+/g, ' ').trim();
    const chave = crypto.createHash('sha256').update(t).digest('hex').slice(0, 12);
    if (!assinaturas.has(chave)) assinaturas.set(chave, []);
    assinaturas.get(chave).push(e);
  }
  for (const [, estados] of assinaturas) {
    if (estados.length > 1) {
      p.push(`os estados ${estados.join(' e ')} produzem EXATAMENTE a mesma tela — `
        + '`capture_status` não está sendo lido (§1.1: 0 leitores em .tsx)');
    }
  }
  // 🔴 `failed` não pode parecer marca pronta: a frase do erro tem de aparecer.
  const falhou = (telas.failed.texto || '');
  if (!falhou.includes('o site demorou demais')) {
    p.push('o estado `failed` não mostra o `capture_error` em português — hoje a paleta-fallback '
      + 'faz uma captura que FALHOU parecer marca válida (§1.1)');
  }
  return p;
}
checar(analisarEstados(), '[1] os seis `capture_status` produzem telas DIFERENTES, e `failed` diz por quê');

// 🔴 O CONTROLE DA RÉGUA: ela tem de saber dizer IGUAL e DIFERENTE. Sem as
//    duas metades, "todos diferentes" tanto pode ser a tela boa quanto uma régua
//    que devolve ruído a cada leitura (CLAUDE.md §9.2).
checar(await (async () => {
  const p = [];
  const outra = await renderizarTela('empty');
  const norm = (o) => (o.texto || '').replace(/\s+/g, ' ').trim();
  if (outra.erro) { p.push(outra.erro); return p; }
  if (norm(outra) !== norm(telas.empty)) {
    p.push('duas leituras do MESMO estado deram textos diferentes — a régua mede ruído, não a tela');
  }
  // ⚠️ A segunda metade NÃO pode ser "empty ≠ failed": isso é justamente o que
  //    [1] mede, e um controle que repete a asserção não controla nada. O que se
  //    prova aqui é que a régua ENXERGA diferença de conteúdo — e para isso vale
  //    um par que a tela já renderiza HOJE (o erro da fonte).
  const outroErro = await renderizarTela('empty', {
    sources: [{ kind: 'website', url: 'https://alfa.invalid', status: 'failed',
                http_status: 500, error: 'sentinela-de-controle-098' }],
  });
  if (outroErro.erro) { p.push(outroErro.erro); return p; }
  if (norm(outroErro) === norm(telas.empty)) {
    p.push('mudar o conteúdo da tela não mudou o texto medido — a régua não enxerga nada');
  }
  return p;
})(), '[1b] CONTROLE da régua: mesma tela = mesmo texto; telas diferentes = textos diferentes');

// ══ [2] ZERO CHAVE DE CÓDIGO NA TELA (R10/R11 da 097) ════════════════════════
console.log('\n[2] A TELA NÃO MOSTRA CHAVE DE CÓDIGO (R10 · R11 da 097)');
function analisarListaNegra() {
  const p = [];
  if (telas.failed.erro) { p.push(telas.failed.erro); return p; }
  const tudo = ESTADOS.map((e) => telas[e].texto || '').join('\n');
  for (const chave of LISTA_NEGRA) {
    if (tudo.includes(chave)) {
      const linha = tudo.split('\n').find((l) => l.includes(chave)) || '';
      p.push(`\`${chave}\` aparece na tela: …${linha.trim().slice(0, 120)}…`);
    }
  }
  return p;
}
checar(analisarListaNegra(), `[2] nenhuma das ${LISTA_NEGRA.length} chaves de código aparece na tela renderizada`);
controle((() => {
  const inventado = 'google_business HTTP 429 EgressBlockedError';
  return LISTA_NEGRA.filter((c) => inventado.includes(c)).map((c) => `a lista negra acusa \`${c}\``);
})(), '[2] a lista negra sabe acusar');

// ══ [3] O CONTRATO `erro` → `error` (U1.2/E14) ═══════════════════════════════
//
// 📊 §1.1: `brand.py:108` serializa `erro` e a tela lê `error` — TODA falha vira
// "A captura não encontrou o suficiente". O guarda EXECUTA o BFF com o backend
// dublado devolvendo `{ok:false, erro:"…"}` e cobra `error` na resposta.
console.log('\n[3] O CONTRATO DA FALHA — a rota BFF entrega `error`, que é o que a tela lê');
const FRASE_DO_BACKEND = 'o Instagram bloqueia a leitura automática — cole a bio ou os posts fixados';
const respostaBFF = await executarRota(CAMINHO_BFF_MARCA, {
  metodo: 'POST',
  corpo: {},
  extras: {
    '@/lib/admin/admin-auth': {
      requireCompanyMember: async () => ({ ok: true, ctx: { companyId: CO_ALFA, userId: U_SOCIO }, supabase: null }),
      assertSameOrigin: () => null,
    },
  },
  fetchDublado: async () => ({
    ok: false, status: 200,
    json: async () => ({ ok: false, status: 'failed', erro: FRASE_DO_BACKEND, avisos: [] }),
  }),
});
function analisarContrato(obs) {
  const p = [];
  if (obs.erro) { p.push(obs.erro); return p; }
  const corpo = obs.corpo || {};
  if (typeof corpo.error !== 'string' || !corpo.error.trim()) {
    p.push('a resposta que chega à tela não traz `error` (a tela lê `j?.error`) — veio '
      + `${JSON.stringify(corpo).slice(0, 220)}`
      + ' · o conserto pode ser no `brand.py` (serializar `error`) OU no BFF '
      + '(traduzir `erro`), mas a tela não pode receber uma falha sem `error`: '
      + '📊 §1.1, é assim que 500, site vazio e "sem fonte" viram a MESMA frase');
  } else if (!corpo.error.includes('Instagram')) {
    p.push(`a resposta traz \`error\` mas não a frase do backend: ${JSON.stringify(corpo.error)}`);
  }
  return p;
}
checar(analisarContrato(respostaBFF), '[3] `POST /api/dashboard/brand-identity` devolve `error` com a frase humana do backend');

// 🔴 O PAR: uma captura que DEU CERTO não pode vir com `error` preenchido.
const respostaOK = await executarRota(CAMINHO_BFF_MARCA, {
  metodo: 'POST',
  corpo: {},
  extras: {
    '@/lib/admin/admin-auth': {
      requireCompanyMember: async () => ({ ok: true, ctx: { companyId: CO_ALFA, userId: U_SOCIO }, supabase: null }),
      assertSameOrigin: () => null,
    },
  },
  fetchDublado: async () => ({
    ok: true, status: 200,
    json: async () => ({ ok: true, status: 'captured', erro: null, avisos: [], campos_propostos: ['mission'] }),
  }),
});
checar((() => {
  const c = respostaOK.corpo || {};
  if (respostaOK.erro) return [respostaOK.erro];
  return c.error ? [`a captura que DEU CERTO veio com \`error\`: ${JSON.stringify(c.error)}`] : [];
})(), '[3b] CONTROLE: a captura que deu certo NÃO traz `error` — o guarda distingue os dois casos');

// ══ [4] A SEÇÃO "JEITO DE ATENDER" (U2.4) ════════════════════════════════════
console.log('\n[4] A SEÇÃO "JEITO DE ATENDER" — cinco escolhas em português e a frase fixa');
const FRASE_FIXA = 'Não muda o que ele pode fazer';
const ESCOLHAS_EM_PORTUGUES = {
  saudação: ['afetiva', 'cordial', 'direta'],
  tratamento: ['você', 'senhor', 'nome'],
  emoji: ['sem emoji', 'pontual', 'à vontade'],
  formalidade: ['informal', 'cordial', 'formal'],
  explicação: ['passo a passo', 'direta'],
};
const JEITO_PROPOSTO = {
  saudacao: 'afetiva', tratamento: 'voce', emoji: 'pontual',
  formalidade: 'cordial', explicacao: 'passo_a_passo',
  principios: ['Explique antes de pedir documento'],
  termos_preferidos: ['cobertura'], evitar: ['letra miuda'],
  exemplos_aprovados: ['Oi! Vou te explicar passo a passo.'],
  evidencia: ['A gente explica passo a passo, sem pressa'],
};
// 🔴 DOIS mundos, porque a tela tem dois estados e o defeito mora nos dois: o
//    VAZIO ("ainda não declarado", R2 — nunca semeado) e o que TEM proposta,
//    onde vivem os cinco rádios, a origem, a evidência e a frase fixa.
const telaComProposta = await renderizarTela('manual', {
  profile: {
    tone: {}, tone_proposto: JEITO_PROPOSTO,
    tone_proposto_origem: 'leitura_do_site',
    tone_proposto_em: new Date().toISOString(),
    tone_evidencia: JEITO_PROPOSTO.evidencia,
  },
  raiz: { jeito: { ativo: {}, proposto: JEITO_PROPOSTO, origem: 'leitura_do_site',
                   evidencia: JEITO_PROPOSTO.evidencia, versoes: [] } },
});
console.log('      📊 tela com proposta: '
  + (telaComProposta.erro ? telaComProposta.erro : `${(telaComProposta.texto || '').length} caracteres`));

function analisarJeito() {
  const p = [];
  const obs = telaComProposta.erro ? telas.manual : telaComProposta;
  if (obs.erro) { p.push(obs.erro); return p; }
  const texto = (obs.texto || '').toLowerCase();
  if (!texto.includes('jeito de atender')) {
    p.push('a tela não tem a seção "Jeito de atender" (U2.4) — hoje as abas são '
      + 'Visual/Sobre/Presença/Origem e o `tone` não aparece em lugar nenhum');
    return p;
  }
  if (!(obs.texto || '').includes(FRASE_FIXA)) {
    p.push(`a frase fixa não está na tela: "…${FRASE_FIXA}…" (U2.4/G11 do Intercom)`);
  }
  // as cinco escolhas, com rótulo em PORTUGUÊS — nunca `senhor_senhora`.
  for (const [rotulo, valores] of Object.entries(ESCOLHAS_EM_PORTUGUES)) {
    const faltando = valores.filter((v) => !texto.includes(v));
    if (faltando.length === valores.length) {
      p.push(`a escolha "${rotulo}" não aparece com nenhum dos rótulos em português (${valores.join(' · ')})`);
    }
  }
  const radios = (obs.arvores || [obs.arvore])
    .flatMap((a) => nosDe(a, 'input'))
    .filter((i) => i.props?.type === 'radio');
  if (radios.length < 5) {
    p.push(`a tela tem ${radios.length} rádio(s); as cinco escolhas fechadas da R3 pedem pelo menos 5`);
  }
  return p;
}
checar(analisarJeito(), '[4] a seção "Jeito de atender": cinco escolhas em rádio, em português, e a frase fixa');

// 🔴 [4b] O ESTADO INICIAL É VAZIO E VISÍVEL (R2 — Soul semeada e não revisada é
//    pior que nenhuma). Sem proposta e com `tone` = `{}`, a tela tem de DIZER
//    isso, e não pode mostrar escolha nenhuma como se fosse da corretora.
checar((() => {
  const p = [];
  const obs = telas.manual;
  if (obs.erro) { p.push(obs.erro); return p; }
  const texto = (obs.texto || '').toLowerCase();
  if (!texto.includes('jeito de atender')) {
    p.push('a tela não tem a seção "Jeito de atender" (U2.4)');
    return p;
  }
  if (!/ainda n[ãa]o (foi )?declarado|ainda n[ãa]o declarou|nenhum jeito/.test(texto)) {
    p.push('com `tone` = `{}` e sem proposta, a tela não diz "ainda não declarado" (R2) — '
      + 'o estado inicial tem de ser VAZIO E VISÍVEL, nunca semeado');
  }
  return p;
})(), '[4b] sem jeito declarado, a tela diz "ainda não declarado" (R2 — nunca semeado)');

// ══ [5] A EMPRESA ATIVA VALE — billing, company-data e n8n ═══════════════════
//
// 📊 §1.3: as três cópias de `getCompanyIdFromSession` leem `users_v2.company_id`
// (a PRIMÁRIA). Um sócio com a BETA ativa vê e ALTERA a assinatura da ALFA.
// A sessão dublada abaixo é exatamente essa: primária = ALFA, ativa = BETA.
console.log('\n[5] A EMPRESA ATIVA VALE EM TODO LUGAR (R6) — sessão com ativa=BETA, primária=ALFA');
const ROTAS_DA_ATIVA = [
  [CAMINHO_BILLING, 'GET'],
  [CAMINHO_COMPANY_DATA, 'GET'],
  [CAMINHO_N8N, 'POST'],
];
async function comEmpresaAtiva(caminho, metodo, ativa) {
  return executarRota(caminho, {
    metodo,
    corpo: { message: 'oi', companyId: CO_ALFA },
    sessao: { userId: U_SOCIO, companyId: ativa || CO_ALFA },
    ironSession: (opcoes) => (opcoes && opcoes.__qual === 'admin'
      ? {}
      : { userId: U_SOCIO, companyId: CO_ALFA, activeCompanyId: ativa || undefined }),
  });
}
const observadas = [];
for (const [caminho, metodo] of ROTAS_DA_ATIVA) {
  const comAtiva = await comEmpresaAtiva(caminho, metodo, CO_BETA);
  const semAtiva = await comEmpresaAtiva(caminho, metodo, null);
  observadas.push({ caminho, comAtiva, semAtiva });
}
function analisarAtiva() {
  const p = [];
  for (const { caminho, comAtiva } of observadas) {
    if (comAtiva.erro) { p.push(`${caminho}: ${comAtiva.erro}`); continue; }
    const ids = empresasConsultadas(comAtiva.registro);
    if (!ids.length) {
      p.push(`${caminho}: nenhuma consulta filtrou por \`company_id\` — não dá para dizer em que corretora ela agiu`);
      continue;
    }
    if (ids.includes(CO_ALFA) && !ids.includes(CO_BETA)) {
      p.push(`${caminho}: agiu na corretora PRIMÁRIA (${ids.join(', ')}) com a BETA ativa — `
        + 'é o defeito do §1.3 (a cobrança na empresa errada)');
    } else if (!ids.includes(CO_BETA)) {
      p.push(`${caminho}: consultou ${ids.join(', ')} — a empresa ATIVA (BETA) não aparece`);
    }
  }
  return p;
}
checar(analisarAtiva(), '[5] billing/company-data/n8n agem na empresa ATIVA da sessão (R6/U4.b-Next)');

// 🔴 O CONTROLE: SEM empresa ativa escolhida, vale a primária — o comportamento
//    de hoje. Uma rota que sempre usasse a BETA passaria na asserção acima e
//    estaria igualmente errada.
checar((() => {
  const p = [];
  for (const { caminho, semAtiva } of observadas) {
    if (semAtiva.erro) continue;
    const ids = empresasConsultadas(semAtiva.registro);
    if (ids.length && !ids.includes(CO_ALFA)) {
      p.push(`${caminho}: sem empresa ativa deveria valer a primária (ALFA) e valeu ${ids.join(', ')}`);
    }
  }
  return p;
})(), '[5b] CONTROLE: SEM empresa ativa escolhida, vale a primária — como hoje');

// ══ [6] AS PROXIES MANDAM `X-Internal-Key` (U4.a) ═══════════════════════════
console.log('\n[6] AS PROXIES MANDAM A CHAVE INTERNA (R7/U4.a)');
const proxiesObservadas = [];
for (const caminho of PROXIES_COM_CHAVE) {
  for (const metodo of ['GET', 'POST', 'DELETE', 'PATCH']) {
    const obs = await executarRota(caminho, {
      metodo,
      url: `http://t.local${caminho.replace('/route.ts', '').replace('app', '')}?company_id=${CO_ALFA}`,
      corpo: { sessionId: 'ss-098-1', companyId: CO_ALFA },
      params: { jobId: 'jb-1' },
      cabecalhos: { origin: 'https://app.autobrokers.ai', host: 'app.autobrokers.ai' },
      sessao: { userId: U_SOCIO, companyId: CO_ALFA },
      ironSession: (opcoes) => (opcoes && opcoes.__qual === 'admin' ? {} : { userId: U_SOCIO, companyId: CO_ALFA }),
    });
    proxiesObservadas.push({ caminho, metodo, obs, chamou: !obs.erro && obs.chamadas.length > 0 });
  }
}
function analisarChave() {
  const p = [];
  const vistos = new Set();
  for (const { caminho, metodo, obs, chamou } of proxiesObservadas) {
    if (!chamou) continue;
    vistos.add(caminho);
    for (const c of obs.chamadas) {
      const cabecalhos = Object.fromEntries(
        Object.entries(c.headers || {}).map(([k, v]) => [String(k).toLowerCase(), v]),
      );
      if (!cabecalhos['x-internal-key']) {
        p.push(`${caminho} (${metodo}) chama ${c.url} SEM \`X-Internal-Key\` — depois da U4.a `
          + 'o smith-api recusa, e a tela quebra em silêncio');
      }
    }
  }
  for (const caminho of PROXIES_COM_CHAVE) {
    if (!vistos.has(caminho)) {
      const tentativas = proxiesObservadas
        .filter((o) => o.caminho === caminho)
        .map((o) => `${o.metodo}->${o.obs.erro ? o.obs.erro.slice(0, 70) : `status ${o.obs.status} ${JSON.stringify(o.obs.corpo).slice(0, 70)}`}`);
      p.push(`${caminho}: nenhuma execução chegou a chamar o backend · ${tentativas.join(' | ')}`);
    }
  }
  return p;
}
checar(analisarChave(), `[6] as ${PROXIES_COM_CHAVE.length} proxies mandam \`X-Internal-Key\` ao smith-api`);

// ══ [7] O CORPO NÃO É CREDENCIAL ════════════════════════════════════════════
console.log('\n[7] O CORPO NÃO ESCOLHE QUEM É (R6/R7)');
const semSessao = { userId: undefined, companyId: undefined };
const semAutoridade = [
  [CAMINHO_CHAT_SESSION, 'DELETE', { sessionId: 'ss-098-1', companyId: CO_BETA }],
  [CAMINHO_USERS_STATUS, 'POST', { userId: U_SOCIO, status: 'active', companyId: CO_BETA }],
  [CAMINHO_BOOTSTRAP, 'POST', { companyId: CO_BETA, name: 'Corretora Beta' }],
];
const semAutoridadeObs = [];
for (const [caminho, metodo, corpo] of semAutoridade) {
  semAutoridadeObs.push([caminho, metodo, await executarRota(caminho, {
    metodo, corpo, sessao: null, ironSession: () => semSessao,
    cabecalhos: { origin: 'https://app.autobrokers.ai', host: 'app.autobrokers.ai' },
    extras: {
      '@/lib/admin/admin-auth': {
        requireMasterAdmin: async () => ({ ok: false, status: 401, error: 'Não autorizado' }),
        requireCompanyMember: async () => ({ ok: false, status: 401, error: 'Não autorizado' }),
        assertSameOrigin: () => null,
        supabaseService: () => dubleSupabase(mundo(), []),
      },
    },
  })]);
}
function analisarSemAutoridade() {
  const p = [];
  for (const [caminho, metodo, obs] of semAutoridadeObs) {
    if (obs.erro) { p.push(`${caminho}: ${obs.erro}`); continue; }
    if (![401, 403].includes(obs.status)) {
      p.push(`${caminho} (${metodo}) sem sessão nem autoridade respondeu ${obs.status} — `
        + `tem de ser 401/403 (corpo: ${JSON.stringify(obs.corpo).slice(0, 140)})`);
    }
    const escritas = (obs.registro || []).filter((c) => c.op !== 'select');
    if (escritas.length) {
      p.push(`${caminho} (${metodo}) ESCREVEU sem autoridade: ${escritas.map((e) => `${e.op} ${e.tabela}`).join(', ')}`);
    }
  }
  return p;
}
checar(analisarSemAutoridade(), '[7] `chat/session`, `admin/users/status` e `bootstrap-tenant` recusam quem não tem autoridade');

// ══ [7-bis] `leads/identify` NÃO É UM ORÁCULO DE PII (E9) ═══════════════════
console.log('\n[7-bis] `leads/identify` — chave interna, e a resposta só traz `leadId`');
const CORPO_LEAD = { email: 'quem@exemplo.invalid', name: 'Alguem', companyId: CO_ALFA };
const leadSemChave = await executarRota(CAMINHO_LEADS, { metodo: 'POST', corpo: CORPO_LEAD });
const leadComChave = await executarRota(CAMINHO_LEADS, {
  metodo: 'POST', corpo: CORPO_LEAD, cabecalhos: { 'x-internal-key': CHAVE_BOA },
});
function analisarLeads() {
  const p = [];
  if (leadComChave.erro) { p.push(leadComChave.erro); return p; }
  if (!leadSemChave.erro && ![401, 403].includes(leadSemChave.status)) {
    p.push(`sem \`X-Internal-Key\` a rota respondeu ${leadSemChave.status} — `
      + `tem de ser 401 (corpo: ${JSON.stringify(leadSemChave.corpo).slice(0, 140)})`);
  }
  const corpo = leadComChave.corpo || {};
  const proibidos = Object.keys(corpo).filter((k) => k !== 'leadId' && k !== 'error');
  if (proibidos.length) {
    p.push(`a resposta traz ${proibidos.join(', ')} além de \`leadId\` — `
      + '`name` e `isNew` respondem "esta pessoa é cliente de vocês?", que ninguém de fora pode perguntar (E9)');
  }
  const texto = JSON.stringify(leadSemChave.corpo || {}) + JSON.stringify(corpo);
  if (texto.includes('Nome Que Nao Pode Vazar')) {
    p.push('o NOME do lead saiu na resposta — é o oráculo público de PII do §1.3');
  }
  return p;
}
checar(analisarLeads(), '[7-bis] a resposta de `leads/identify` traz SÓ `leadId`; sem chave, 401');
checar((() => {
  const c = leadComChave.corpo || {};
  if (leadComChave.erro) return [leadComChave.erro];
  return c.leadId
    ? []
    : ['com a chave certa a rota tem de CONTINUAR identificando o lead (senão o guarda '
      + `mediria uma rota morta) — veio status ${leadComChave.status} ${JSON.stringify(c).slice(0, 200)}`];
})(), '[7-bis-b] CONTROLE: com a chave certa a rota continua identificando o lead');

// ══ [8] A TROCA DE EMPRESA REESCREVE O QUE O NAVEGADOR GUARDA (U4.c) ════════
console.log('\n[8] A TROCA DE EMPRESA REESCREVE O `localStorage` (U4.c/WorkOS)');
function analisarTroca() {
  const p = [];
  if (!existe(CAMINHO_SESSION_TS)) { p.push(porQue(CAMINHO_SESSION_TS)); return p; }
  // um `localStorage` de mentira, e o motor REAL de `lib/session.ts`.
  const guardado = { smith_user_session: JSON.stringify({
    userId: U_SOCIO, email: 'socio@exemplo.invalid', firstName: 'Socio', lastName: 'Canario',
    planId: null, status: 'active', companyId: CO_ALFA,
    expiresAt: new Date(Date.now() + 7 * 864e5).toISOString(),
  }) };
  const anterior = globalThis.window;
  globalThis.window = {};
  globalThis.localStorage = {
    getItem: (k) => (k in guardado ? guardado[k] : null),
    setItem: (k, v) => { guardado[k] = String(v); },
    removeItem: (k) => { delete guardado[k]; },
  };
  try {
    const sessao = carregarTS(CAMINHO_SESSION_TS, () => ({}));
    const trocar = sessao.atualizarEmpresaNaSessaoLocal;
    if (typeof trocar !== 'function') {
      p.push('`lib/session.ts` não exporta `atualizarEmpresaNaSessaoLocal(companyId)` (U4.c) — '
        + 'hoje o `companyId` fica congelado no navegador por 7 a 30 dias (§1.3)');
      return p;
    }
    trocar(CO_BETA);
    const depois = JSON.parse(guardado.smith_user_session || '{}');
    if (depois.companyId !== CO_BETA) {
      p.push(`depois da troca o navegador ainda guarda \`companyId=${depois.companyId}\``);
    }
    // 🔴 E o `TenantNav` tem de CHAMAR isso. Sem a chamada, a função existe e
    //    não guarda nada — que é o defeito com outra roupa.
    if (existe(CAMINHO_TENANTNAV)) {
      const nav = fonte(CAMINHO_TENANTNAV)
        .split('\n').filter((l) => !/^\s*(\/\/|\*|\/\*)/.test(l)).join('\n');
      if (!nav.includes('atualizarEmpresaNaSessaoLocal(')) {
        p.push('`TenantNav.switchCompany` não chama `atualizarEmpresaNaSessaoLocal` — '
          + 'a função existe e ninguém a usa (§9.4: o que se afirma é o comportamento do MOTOR)');
      }
    }
  } catch (e) {
    p.push(porQue(CAMINHO_SESSION_TS, e));
  } finally {
    globalThis.window = anterior;
    delete globalThis.localStorage;
  }
  return p;
}
checar(analisarTroca(), '[8] a troca de empresa REESCREVE `companyId` no `localStorage`, e o `TenantNav` chama isso');

// ══ [9] O ENVIO HUMANO SABE DE QUEM É (R8/U5.a) ═════════════════════════════
console.log('\n[9] O ENVIO HUMANO GRAVA `sender_user_id` (R8) — 📊 hoje 0 de 11.981');
const envio = await executarRota(CAMINHO_CONVERSA, {
  metodo: 'POST',
  corpo: { action: 'send', text: 'oi, tudo certo com o seu chamado' },
  params: { id: CONVERSA_A },
  sessao: { userId: U_SOCIO, companyId: CO_ALFA },
  ironSession: () => ({ userId: U_SOCIO, companyId: CO_ALFA }),
});
const envioPeloMessages = await executarRota(CAMINHO_MESSAGES, {
  metodo: 'POST',
  corpo: { conversation_id: CONVERSA_A, role: 'user', content: 'pergunta do dono' },
  sessao: { userId: U_SOCIO, companyId: CO_ALFA },
  ironSession: () => ({ userId: U_SOCIO, companyId: CO_ALFA }),
});
function analisarAutorDaMensagem(obs, rotulo) {
  const p = [];
  if (obs.erro) { p.push(`${rotulo}: ${obs.erro}`); return p; }
  const inserts = (obs.registro || []).filter((c) => c.tabela === 'messages' && c.op === 'insert');
  if (!inserts.length) {
    p.push(`${rotulo}: nenhuma linha foi inserida em \`messages\` (status ${obs.status}, `
      + `corpo ${JSON.stringify(obs.corpo).slice(0, 140)})`);
    return p;
  }
  for (const i of inserts) {
    const carga = Array.isArray(i.payload) ? i.payload[0] : i.payload;
    if (!carga || !carga.sender_user_id) {
      p.push(`${rotulo}: a mensagem nasceu SEM \`sender_user_id\` — `
        + `📊 é o 0 de 11.981 do §1.4 (chaves: ${Object.keys(carga || {}).join(', ')})`);
    } else if (String(carga.sender_user_id) !== U_SOCIO) {
      p.push(`${rotulo}: \`sender_user_id\` = ${carga.sender_user_id}, e quem enviou foi ${U_SOCIO}`);
    }
  }
  return p;
}
checar([
  ...analisarAutorDaMensagem(envio, 'painel (`conversas/[id]` action=send)'),
  ...analisarAutorDaMensagem(envioPeloMessages, '`/api/messages` POST'),
], '[9] toda mensagem escrita por gente grava `sender_user_id` = o usuário da sessão');

// ══ [CTL] A DECLARAÇÃO DAS MUTAÇÕES ═════════════════════════════════════════
console.log('\n[CTL] a declaração das mutações');
function analisarMutacoes(lista, esperadas) {
  const p = [];
  const vistos = new Set();
  for (const m of lista) {
    if (vistos.has(m.id)) p.push(`marcador de mutação repetido: ${m.id}`);
    vistos.add(m.id);
    if (!m.ancora || !m.substituto) {
      p.push(`a mutação ${m.id} não tem \`ancora\`/\`substituto\` — ela é PROSA, e prosa não roda`);
      continue;
    }
    if (m.ancora === m.substituto) p.push(`a mutação ${m.id} troca a âncora por ela mesma — é edição, não mutação`);
    if (!Array.isArray(m.vermelho) || !m.vermelho.length) {
      p.push(`a mutação ${m.id} não declara NENHUM nome de asserção que tem de ficar vermelho`);
    }
    const soComentario = m.ancora.split('\n').every((l) => !l.trim() || l.trim().startsWith('//') || l.trim().startsWith('*'));
    if (soComentario) p.push(`a âncora de ${m.id} é só comentário — mutá-la não muda comportamento nenhum`);
    if (!existe(m.arquivo)) {
      p.push(`⏳ a mutação ${m.id} aponta para \`${m.arquivo}\`, que o builder ainda não escreveu`);
      continue;
    }
    const ocorrencias = fonte(m.arquivo).split(m.ancora).length - 1;
    if (ocorrencias > 1) {
      p.push(`a âncora de ${m.id} aparece ${ocorrencias}× em ${m.arquivo} — tem de aparecer no máximo 1`);
    }
  }
  if (esperadas != null && lista.length !== esperadas) {
    p.push(`MUTACOES tem ${lista.length} entradas; ${esperadas} são deste guarda`);
  }
  return p;
}
checar(analisarMutacoes(MUTACOES, 2),
  '[CTL] as 2 mutações deste guarda têm âncora em CÓDIGO, substituto e nome-vermelho declarado');
controle(analisarMutacoes([
  { id: 'CTL1', arquivo: CAMINHO_SESSION_TS, ancora: '// esta linha nao existe em lugar nenhum do produto', substituto: 'x', vermelho: ['[0]'] },
  { id: 'CTL2', arquivo: CAMINHO_SESSION_TS, o_que: 'prosa pura', reprova: 'nada' },
], null), '[CTL] mutações-controle: uma com âncora MORTA (e só comentário) e uma que é só prosa');

// 🔴 A CONTA COM O GUARDA IRMÃO — 2 aqui + 15 no python = as 17 da SPEC v1.1.
//    ⚠️ Isto lê a DECLARAÇÃO do outro arquivo (uma lista literal), que é a
//    exceção escrita da §9.4 — não substitui motor nenhum.
const CAMINHO_IRMAO = 'backend/tests/test_cada_coisa_sabe_de_quem_e.py';
checar((() => {
  if (!existe(CAMINHO_IRMAO)) return [`o guarda irmão \`${CAMINHO_IRMAO}\` não foi encontrado`];
  const py = fonte(CAMINHO_IRMAO);
  const bloco = py.slice(py.indexOf('MUTACOES = ['), py.indexOf('MUTACOES_DO_IRMAO'));
  const ids = [...bloco.matchAll(/^\s*"(M[0-9A-Z-]+)"\),?\s*$/gm)].map((m) => m[1]);
  const uniao = new Set([...ids, ...MUTACOES.map((m) => m.id)].map((x) => x.toUpperCase()));
  const p = [];
  const faltando = MUTACOES_DA_SPEC.filter((m) => !uniao.has(m));
  const sobrando = [...uniao].filter(
    (m) => !MUTACOES_DA_SPEC.includes(m) && !(m in MUTACOES_ACRESCENTADAS));
  if (faltando.length) p.push(`as mutações da SPEC v1.1 que NINGUÉM declara: ${faltando.join(', ')}`);
  if (sobrando.length) {
    p.push(`mutações declaradas que não são da SPEC nem estão na lista de acrescentadas `
      + `(§11 — nada silencioso): ${sobrando.join(', ')}`);
  }
  return p;
})(), `[CTL] ${MUTACOES.length} mutações aqui + ${MUTACOES_DO_IRMAO} no guarda python = as ${TOTAL_DE_MUTACOES_DA_SPEC} da SPEC`);

// ─────────────────────────────────────────────────────────────────────────────
console.log(`\n${'='.repeat(78)}`);
console.log(`  ${falhas.length} falha(s)`);
if (falhas.length > 0) {
  console.log(`\n  ⛔ ${falhas.length} VERMELHO:`);
  for (const f of falhas) console.log(`     - ${f}`);
  console.log('\n  🔴 Em `821752f` (a cópia limpa `../AutoBrokers-FIX-gate0`) esta lista É o');
  console.log('     GATE ZERO da SPEC-098 (BLOCO 0).');
  process.exit(1);
}
console.log('\nVERDE — a tela diz a verdade por estado, o jeito de atender é declarado em');
console.log('        português, a empresa ativa vale em todo lugar, o corpo não é credencial');
console.log('        e toda mensagem escrita por gente sabe de quem é.');
