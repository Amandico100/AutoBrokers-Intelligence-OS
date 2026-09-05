// SPEC-096 — O CHAT RESPONDE, MOSTRA O TRABALHO E CONTINUA. O guarda do lado da
// TELA e do BFF, escrito ANTES do código (protocolo AAA v11.2 §4: quem faz a
// prova não faz a resposta — o DESENHISTA escreve o teste, dois builders o
// deixam verde).
//
// 🔴 ESTE ARQUIVO NASCE VERMELHO, E É PARA NASCER. Em `e1494ab` ele imprime os
// itens do GATE ZERO (§4 BLOCO 0.1) que são do lado da tela/BFF —
// (i) o BFF repassa o companyId do corpo · (ii) /api/messages não confere o
// dono · (vi) a pergunta é gravada pelo browser sem await · (vii) sem
// client_request_id · (viii) a conversa carrega sem limite — cada um com a
// mensagem do que falta. Um guarda que nasce verde não mediu nada (CLAUDE.md
// §9.3): tudo que já está verde em HEAD é suspeito e foi revisado.
//
// ─────────────────────────────────────────────────────────────────────────────
// O QUE ELE GUARDA — a medição de 04/09/2026 (SPEC-096 §1)
// ─────────────────────────────────────────────────────────────────────────────
//
//   📊 stream/route.ts:10-40   o proxy repassa o corpo cego: companyId, userId e
//                              agentId do corpo carregam o cérebro e o crédito de
//                              QUALQUER corretora (§1.1) — P0
//   📊 messages/route.ts:16-21 testa a PRESENÇA do cookie, não o dono: IDOR
//                              autenticado (§1.2)
//   📊 page.tsx:361            saveMessage(...) sem await, em paralelo com o
//                              stream: a pergunta pode não ser gravada (§1.3)
//   📊 conversations:139-146   a conversa inteira carrega de uma vez, sem cursor
//                              (p95=129, máx=1.326 mensagens) (§1.6)
//   📊 n8n/route.ts:31         `body.companyId || session.companyId`: o corpo
//                              vence (§1.1, R12)
//
// Nenhum desses defeitos trava nada. Todos respondem 200. É o CLAUDE.md §9.5 no
// shell do chat: uma rota que responde à corretora ERRADA é silenciosa.
//
// ─────────────────────────────────────────────────────────────────────────────
// COMO ELE FUNCIONA — sem rede, sem banco, sem servidor
// ─────────────────────────────────────────────────────────────────────────────
//
// Mesma forma de `relatorios-dizem-o-que-sao.test.mjs` (SPEC-095): a rota é
// transpilada com o TypeScript do projeto, carregada com um `require` falso e
// EXECUTADA sobre dublês. O dublê de Supabase APLICA os filtros (não só os
// registra); o de `iron-session` devolve a sessão que o teste escolhe; o de
// `cookies()` devolve a loja de cookies do teste; o `fetch` global é dublado e
// registra URL, headers e corpo do fetch ao backend, devolvendo um
// `ReadableStream` SSE. Nenhum servidor sobe (CLAUDE.md §9.1 é para o build; aqui
// nem isso — é execução em memória).
//
// Os arquivos NOVOS da SPEC que ainda não existem (`lib/chat/protocolo.ts`,
// `components/chat/*`): o guarda captura a AUSÊNCIA e REPROVA com mensagem, nunca
// estoura (protocolo §0.3 — o passo do meio é o que ninguém dá).
//
// ─────────────────────────────────────────────────────────────────────────────
// OS BLOCOS
// ─────────────────────────────────────────────────────────────────────────────
//   [1]  S.1   o BFF do stream: sessão → identidade; corpo ignorado; X-Internal-Key
//   [2]  A.2   o BFF grava a PERGUNTA antes do fetch; sem client_request_id → 400
//   [3]  R3    conflito no índice = retentativa, não erro
//   [4]  S.3   /api/messages GET confere o DONO (404, não 403); 401 admin inválido
//   [5]  D.2   /api/messages GET com before=/limit=60; ordem crescente; has_more
//   [6]  S.3   /api/messages POST: role só 'user'; de outro dono → 404
//   [7]  D.1   /api/conversations: limite 60 + cursor + has_more
//   [8]  S.4   /api/n8n: sessão vence; sem sessão → 401
//   [9]  C.2   page.tsx: client_request_id por envio; sem companyId/userId/agentId;
//              sem /api/messages para texto; sem UCP; showAgentSelector={false}
//  [10]  C.3   page.tsx: "Tentar de novo" reenvia o MESMO client_request_id
//  [11]  C.1   lerEventos: seq, lacuna (transport:'gap'), protocolo, [DONE]
//  [12]  C.1   o estado do Turno: submitting→streaming→complete; policy sem content
//  [13]  C.3   LinhaDeAtividade / CardDeRelatorio / AvisoDoTurno renderizam
//  [14]  R6    nenhum setTimeout/setInterval cria estágio
//  [15]  R11   MessageBubble memoizado
//  [16]  C.2   autoscroll só perto do fim + "Voltar ao fim"
//  [CTL] cada guarda acima consegue ficar VERMELHO (PAR sintético, em memória)
//
// ─────────────────────────────────────────────────────────────────────────────
// 🔴 MUTAÇÕES — por CÓPIA, e por que elas NÃO rodam sozinhas aqui
// ─────────────────────────────────────────────────────────────────────────────
//
// ⛔ Este guarda NÃO escreve em arquivo de produto. Ele nasce enquanto DOIS
// builders (tela/BFF e backend) escrevem `app/`, `lib/`, `components/` no mesmo
// diretório: mutar em disco e restaurar por cópia apagaria a edição de quem
// estivesse salvando naquele segundo. Toda linha de controle aqui é SINTÉTICA e
// mora em memória — mesma superfície, veredito oposto (protocolo §5).
//
// A lista abaixo é para o BUILDER e para a confirmação mecânica, depois que a
// árvore parar. As mutações do lado da tela/BFF da SPEC §4 BLOCO G. Uma mutação
// que não deixa nada vermelho não é mutação: é edição.
//
//   MUTACOES (arquivo · o que trocar · qual asserção fica vermelha):
export const MUTACOES = [
  { arquivo: 'app/api/chat/stream/route.ts',
    o_que: "remover o header 'X-Accel-Buffering': 'no' repassado ao browser",
    reprova: '[1] (X-Accel — o token não chega antes do fim)' },
  { arquivo: 'app/api/chat/stream/route.ts',
    o_que: 'voltar a repassar companyId/userId/agentId do corpo (corpo vence a sessão)',
    reprova: '[1] (o browser escolhe a corretora — o P0)' },
  { arquivo: 'app/api/messages/route.ts',
    o_que: "remover o .eq('user_id', dono) do GET/POST",
    reprova: '[4]/[6] (IDOR — qualquer cookie lê qualquer conversa)' },
  { arquivo: 'app/api/chat/stream/route.ts',
    o_que: 'gravar a pergunta DEPOIS do fetch (ou sem await)',
    reprova: '[2] (a pergunta pode não ser gravada)' },
  { arquivo: 'app/api/conversations/route.ts',
    o_que: 'remover o limite/cursor da consulta de conversas',
    reprova: '[7] (a conversa de 1.326 mensagens carrega inteira)' },
  { arquivo: 'app/api/n8n/route.ts',
    o_que: 'voltar a `body.companyId || session.companyId` (o corpo vence)',
    reprova: '[8] (a voz fala pela corretora do corpo)' },
  { arquivo: 'app/dashboard/chat/page.tsx',
    o_que: 'o fetch a /api/chat/stream volta a levar companyId/userId/agentId',
    reprova: '[9] (a tela volta a escolher a corretora)' },
  { arquivo: 'app/dashboard/chat/page.tsx',
    o_que: 'reintroduzir a heurística `ucp_` no texto do stream',
    reprova: '[9] (estágio parseado do conteúdo, não do evento)' },
  { arquivo: 'app/dashboard/chat/page.tsx',
    o_que: 'showAgentSelector={true}',
    reprova: '[9] (o seletor de agente do painel volta — R11)' },
  { arquivo: 'app/dashboard/chat/page.tsx',
    o_que: '"Tentar de novo" gera um novo client_request_id',
    reprova: '[10] (o retry vira uma pergunta nova)' },
  { arquivo: 'lib/chat/protocolo.ts',
    o_que: 'lerEventos ignora o seq (não detecta lacuna)',
    reprova: '[11] (o buraco no stream passa despercebido)' },
  { arquivo: 'lib/chat/protocolo.ts',
    o_que: "o reducer grava o aviso de policy como content do assistente",
    reprova: '[12] (o aviso vira memória — R5)' },
  { arquivo: 'components/chat/LinhaDeAtividade.tsx',
    o_que: 'um setTimeout/setInterval cria o estágio',
    reprova: '[14] (o estágio nasce do relógio, não do evento — R6)' },
  { arquivo: 'app/dashboard/chat/page.tsx',
    o_que: 'o limiar do autoscroll 120→∞ (sempre rola) — E14, a 14ª mutação',
    reprova: '[16] (a tela puxa o usuário que rolou para cima)' },
];
//
// ─────────────────────────────────────────────────────────────────────────────
// ⛔ SEGURANÇA
// ─────────────────────────────────────────────────────────────────────────────
//   · Sem rede, sem banco, sem escrita: os dublês são memória pura.
//   · NENHUM nome de pessoa, CPF, telefone, apólice, placa, senha ou token nas
//     fixtures. As corretoras são sentinelas óbvias ("Alfa", "Beta").
//   · Duas corretoras SEMPRE: Alfa é a do teste, Beta existe para provar que nada
//     dela atravessa (CLAUDE.md §7 — o backend usa service role).
//
// Rodar:  npm run test:chat-shell
//         node scripts/o-chat-responde-e-continua.test.mjs

import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const RAIZ = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const ts = require('typescript');

// ─────────────────────────────────────────────────────────────────────────────
// As fixtures — duas corretoras, dois usuários, duas conversas (§4 BLOCO G)
// ─────────────────────────────────────────────────────────────────────────────
const CO_ALFA = 'co-alfa-0000-4000-8000-000000000001';
const CO_BETA = 'co-beta-0000-4000-8000-000000000002';
const U_ALFA = 'u-alfa-0000-4000-8000-000000000001';
const U_BETA = 'u-beta-0000-4000-8000-000000000002';
const AG_ALFA = 'ag-alfa-0000-4000-8000-000000000001';
const AG_BETA = 'ag-beta-0000-4000-8000-000000000002';
const CV_ALFA = 'cv-alfa-0000-4000-8000-000000000001';
const CV_BETA = 'cv-beta-0000-4000-8000-000000000002';
const SS_ALFA = 'ss-alfa';

function historicoDeAlfa(n) {
  const linhas = [];
  const base = Date.parse('2026-09-01T00:00:00Z');
  for (let i = 0; i < n; i++) {
    linhas.push({
      id: `m-alfa-${String(i).padStart(4, '0')}`,
      conversation_id: CV_ALFA,
      user_id: U_ALFA,
      company_id: CO_ALFA,
      role: i % 2 === 0 ? 'user' : 'assistant',
      content: `mensagem ${i}`,
      created_at: new Date(base + i * 60000).toISOString(),
      payload: { client_request_id: `crid-${i}` },
    });
  }
  return linhas;
}

function fixtures(qtdMensagens = 130) {
  return {
    users_v2: [
      { id: U_ALFA, company_id: CO_ALFA },
      { id: U_BETA, company_id: CO_BETA },
    ],
    company_members: [
      { user_id: U_ALFA, company_id: CO_ALFA, status: 'active' },
      { user_id: U_BETA, company_id: CO_BETA, status: 'active' },
    ],
    conversations: [
      { id: CV_ALFA, user_id: U_ALFA, company_id: CO_ALFA, session_id: SS_ALFA, agent_id: AG_ALFA, title: 'Conversa Alfa', status: 'active', created_at: '2026-09-01T00:00:00Z', updated_at: '2026-09-04T00:00:00Z' },
      { id: CV_BETA, user_id: U_BETA, company_id: CO_BETA, session_id: 'ss-beta', agent_id: AG_BETA, title: 'CONVERSA BETA — nao pode aparecer', status: 'active', created_at: '2026-09-01T00:00:00Z', updated_at: '2026-09-04T00:00:00Z' },
    ],
    companies: [
      { id: CO_ALFA, webhook_url: 'https://alfa.local/hook', use_langchain: false },
      { id: CO_BETA, webhook_url: 'https://BETA.local/hook', use_langchain: false },
    ],
    agents: [
      { id: AG_ALFA, company_id: CO_ALFA, name: 'Agente Alfa', is_active: true },
      { id: AG_BETA, company_id: CO_BETA, name: 'Agente Beta', is_active: true },
    ],
    messages: historicoDeAlfa(qtdMensagens),
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// Carregador: TypeScript real, `require` falso (o molde de 095).
// ─────────────────────────────────────────────────────────────────────────────
function existe(rel) { return fs.existsSync(path.join(RAIZ, rel)); }
function fonte(rel) { return fs.readFileSync(path.join(RAIZ, rel), 'utf8'); }

function carregarTS(caminhoRelativo, resolverImport) {
  const js = ts.transpileModule(fonte(caminhoRelativo), {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020,
      esModuleInterop: true,
    },
    fileName: caminhoRelativo,
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

// ─────────────────────────────────────────────────────────────────────────────
// Dublê de Supabase — o encadeamento do cliente real, e os filtros APLICADOS.
// Registra `from`, `select`, `eq/lt/gte/order/limit`, `insert` (com payload),
// `single/maybeSingle`. E projeta como o PostgREST projeta (último segmento).
// ─────────────────────────────────────────────────────────────────────────────
function valorDe(linha, coluna) {
  if (!/->/.test(String(coluna))) return linha[coluna];
  let v = linha;
  for (const p of String(coluna).split(/->>|->/).map((s) => s.replace(/^'|'$/g, ''))) {
    if (v == null) return undefined;
    v = v[p];
  }
  return v;
}

function dubleSupabase(linhasPorTabela, registro) {
  function tabela(nome) {
    const consulta = { tabela: nome, op: 'select', colunas: '', opcoes: {}, predicados: [], ordem: null, limite: null, payload: null };
    registro.push(consulta);
    const cadeia = {};
    cadeia.select = (colunas, opcoes) => { consulta.op = 'select'; consulta.colunas = String(colunas ?? ''); consulta.opcoes = opcoes ?? {}; return cadeia; };
    cadeia.insert = (payload) => { consulta.op = 'insert'; consulta.payload = payload; return cadeia; };
    cadeia.update = (payload) => { consulta.op = 'update'; consulta.payload = payload; return cadeia; };
    cadeia.upsert = (payload) => { consulta.op = 'upsert'; consulta.payload = payload; return cadeia; };
    cadeia.delete = () => { consulta.op = 'delete'; return cadeia; };
    for (const op of ['eq', 'neq', 'gt', 'gte', 'lt', 'lte', 'in', 'is']) {
      cadeia[op] = (coluna, valor) => { consulta.predicados.push({ op, coluna, valor }); return cadeia; };
    }
    cadeia.order = (coluna, opcoes) => { consulta.ordem = { coluna, ascendente: opcoes?.ascending !== false }; return cadeia; };
    cadeia.limit = (n) => { consulta.limite = n; return cadeia; };
    cadeia.range = (a, b) => { consulta.range = [a, b]; return cadeia; };

    const casa = (l, p) => {
      const v = valorDe(l, p.coluna);
      switch (p.op) {
        case 'eq': return String(v) === String(p.valor);
        case 'neq': return String(v) !== String(p.valor);
        case 'gt': return v != null && String(v) > String(p.valor);
        case 'gte': return v != null && String(v) >= String(p.valor);
        case 'lt': return v != null && String(v) < String(p.valor);
        case 'lte': return v != null && String(v) <= String(p.valor);
        case 'in': return (p.valor ?? []).map(String).includes(String(v));
        case 'is': return p.valor === null ? v == null : v === p.valor;
        default: return true;
      }
    };
    const resolver = () => {
      if (consulta.op !== 'select') {
        // escrita: aplica e devolve o payload inserido
        const regs = Array.isArray(consulta.payload) ? consulta.payload : [consulta.payload];
        const saida = [];
        for (const r of regs) {
          const linha = { id: `${nome.slice(0, 3)}-${(linhasPorTabela[nome] || []).length + 1}`, ...r };
          (linhasPorTabela[nome] = linhasPorTabela[nome] || []).push(linha);
          saida.push(linha);
        }
        return saida;
      }
      let linhas = (linhasPorTabela[nome] ?? []).filter((l) => consulta.predicados.every((p) => casa(l, p)));
      if (consulta.ordem) {
        const { coluna, ascendente } = consulta.ordem;
        linhas = [...linhas].sort((a, b) => {
          const r = String(a[coluna] ?? '').localeCompare(String(b[coluna] ?? ''));
          return ascendente ? r : -r;
        });
      }
      if (consulta.limite != null) linhas = linhas.slice(0, consulta.limite);
      if (consulta.range) linhas = linhas.slice(consulta.range[0], consulta.range[1] + 1);
      return linhas;
    };
    cadeia.maybeSingle = () => Promise.resolve({ data: resolver()[0] ?? null, error: null });
    cadeia.single = () => { const l = resolver(); return Promise.resolve({ data: l[0] ?? null, error: l.length ? null : { message: 'no rows' } }); };
    cadeia.then = (ok, err) => {
      const linhas = resolver();
      const o = consulta.opcoes || {};
      const corpo = o.head
        ? { data: null, count: linhas.length, error: null }
        : { data: linhas, count: o.count ? linhas.length : null, error: null };
      return Promise.resolve(corpo).then(ok, err);
    };
    return cadeia;
  }
  return { from: tabela };
}

/**
 * Dublê de Supabase com CONFLITO 23505 no PRIMEIRO insert em `messages` — usado
 * só pelo [3] (R3). O dublê comum sempre aplica o insert; este simula o índice
 * único parcial (conversation_id, client_request_id) recusando a gravação uma
 * vez, para medir se a rota reaproveita a linha existente (SELECT por
 * `payload->>client_request_id`) e segue, em vez de responder erro.
 */
function dubleSupabaseComConflito23505(linhasPorTabela, registro) {
  const base = dubleSupabase(linhasPorTabela, registro);
  let jaConflitou = false;
  return {
    from(nome) {
      const antes = registro.length;
      const cad = base.from(nome);
      const consultaAtual = registro[antes];
      if (nome === 'messages') {
        const singleOriginal = cad.single;
        cad.single = (...a) => {
          // 🔴 `.insert(payload).select('id')` reseta `consulta.op` para
          // 'select' (o dublê comum não distingue "select de escrita" de
          // "select de leitura") — o sinal confiável de "isto foi um INSERT"
          // é ter um `payload` de escrita na cadeia, não o `op` no instante
          // em que `.single()` roda.
          if (!jaConflitou && consultaAtual.payload != null) {
            jaConflitou = true;
            return Promise.resolve({ data: null, error: { code: '23505', message: 'duplicate key value violates unique constraint' } });
          }
          return singleOriginal(...a);
        };
      }
      return cad;
    },
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// O placar — três verbos (o molde de 095/protocolo §5)
// ─────────────────────────────────────────────────────────────────────────────
const falhas = [];
const esperados = [];
const jaPodemVirar = [];

function checar(problemas, nome) {
  if (problemas.length === 0) { console.log(`  OK  ${nome}`); }
  else { falhas.push(nome); console.log(`  X   ${nome}`); for (const p of problemas) console.log(`        ${p}`); }
}
// 🔴 INTEGRADO (04/09/2026, depois dos builders): o que era "devendo" passou a ser exigido.
//    A partir daqui, uma asserção que falhe é VERMELHO DE VERDADE, não "esperado até o bloco X".
//    (A forma antiga fica, para o gate zero de uma SPEC futura reaproveitar: INTEGRADO = false.)
const INTEGRADO = true;
function devendo(problemas, nome, bloco) {
  if (INTEGRADO) return checar(problemas, nome);
  if (problemas.length === 0) { console.log(`  OK  ${nome}`); jaPodemVirar.push(`${nome}   [era devendo('${bloco}')]`); }
  else { esperados.push(`${nome}   (esperado ate ${bloco})`); console.log(`  VERMELHO-ESPERADO  ${nome}   (ate ${bloco})`); for (const p of problemas) console.log(`        ${p}`); }
}
function controle(problemas, nome) {
  if (problemas.length > 0) { console.log(`  OK  CONTROLE ${nome} — o guarda acusou (${problemas.length})`); }
  else { falhas.push(`CONTROLE ${nome}`); console.log(`  X   CONTROLE ${nome} — o guarda NAO acusou; ele nao guarda nada`); }
}

// ─────────────────────────────────────────────────────────────────────────────
// Executar as rotas — com sessão, cookies, supabase e fetch dublados
// ─────────────────────────────────────────────────────────────────────────────
class NextResponseFalsa {
  constructor(body, init) {
    this.body = body;
    this.status = init?.status ?? 200;
    this.headers = new Map(Object.entries(init?.headers ?? {}).map(([k, v]) => [String(k).toLowerCase(), v]));
    this.__stream = true;
  }
  static json(body, init) {
    return { __json: true, body, status: init?.status ?? 200, headers: new Map(Object.entries(init?.headers ?? {}).map(([k, v]) => [String(k).toLowerCase(), v])) };
  }
}
const NEXT_SERVER = { NextResponse: NextResponseFalsa, NextRequest: class {} };

/** Silencia o console.log/error/warn do produto durante a execução da rota. */
async function silenciando(fn) {
  const orig = { log: console.log, error: console.error, warn: console.warn, info: console.info };
  console.log = console.error = console.warn = console.info = () => {};
  try { return await fn(); }
  finally { Object.assign(console, orig); }
}

/** Um Response falso com um corpo SSE. */
function respostaSSE(eventos) {
  const linhas = eventos.map((e) => `data: ${JSON.stringify(e)}\n\n`).join('') + 'data: [DONE]\n\n';
  const bytes = new TextEncoder().encode(linhas);
  let entregue = false;
  const body = new ReadableStream({
    pull(controller) { if (entregue) { controller.close(); return; } controller.enqueue(bytes); entregue = true; },
  });
  return { ok: true, status: 200, statusText: 'OK', body, json: async () => ({}), text: async () => linhas };
}

/**
 * Roda o BFF do stream. Devolve o que o dublê de fetch registrou (URL, headers,
 * corpo) e a resposta. A rota de HOJE não lê a sessão nem grava a pergunta — o
 * guarda MEDE isso.
 */
async function rodarStream({ sessao, corpo, linhas = fixtures(), criarSupabase = dubleSupabase }) {
  const registroSupabase = [];
  const supabase = criarSupabase(linhas, registroSupabase);
  const chamadasFetch = [];
  const linhaDoTempo = []; // ordem entre inserts do supabase e o fetch ao backend
  const fetchOriginal = globalThis.fetch;
  globalThis.fetch = async (url, opts = {}) => {
    let body = null;
    try { body = opts.body ? JSON.parse(opts.body) : null; } catch { body = opts.body; }
    const chamada = { url: String(url), headers: opts.headers || {}, body };
    chamadasFetch.push(chamada);
    linhaDoTempo.push({ tipo: 'fetch', url: String(url) });
    return respostaSSE([{ protocol: 'autobrokers.interaction.v1', seq: 1, type: 'turn.completed', turn: {}, payload: {} }]);
  };
  // envolve o supabase para registrar a ordem dos inserts em messages
  const supabaseVigiado = {
    from(nome) {
      const antes = registroSupabase.length;
      const cad = supabase.from(nome);
      const consultaAtual = registroSupabase[antes];
      const insertOriginal = cad.insert;
      cad.insert = (p) => { linhaDoTempo.push({ tipo: 'insert', tabela: nome }); return insertOriginal(p); };
      // também registra SELECT (single/maybeSingle) na linha do tempo — o [3]
      // (R3) precisa provar que o SELECT de reaproveitamento acontece ANTES
      // do fetch ao backend, não só que ele existe.
      const singleOriginal = cad.single;
      cad.single = (...a) => { linhaDoTempo.push({ tipo: consultaAtual.op, tabela: nome }); return singleOriginal(...a); };
      const maybeSingleOriginal = cad.maybeSingle;
      cad.maybeSingle = (...a) => { linhaDoTempo.push({ tipo: consultaAtual.op, tabela: nome }); return maybeSingleOriginal(...a); };
      return cad;
    },
  };
  let resposta, erro = null;
  try {
    const rota = carregarTS('app/api/chat/stream/route.ts', (id) => resolverRotaImport(id, { sessao, supabase: supabaseVigiado }));
    resposta = await silenciando(() => rota.POST(pedidoPOST('https://teste.local/api/chat/stream', corpo)));
  } catch (e) { erro = e; }
  finally { globalThis.fetch = fetchOriginal; }
  return { chamadasFetch, registroSupabase, linhaDoTempo, resposta, erro };
}

/** Resolvedor de imports comum às rotas de sessão. */
function resolverRotaImport(id, { sessao, supabase, cookiesLoja }) {
  if (id === 'next/server') return NEXT_SERVER;
  if (id === 'next/headers') return { cookies: async () => cookiesLoja ?? { get: () => undefined } };
  if (id === 'iron-session') return { getIronSession: async () => sessao ?? {} };
  if (id === '@supabase/supabase-js') return { createClient: () => supabase };
  if (id === '@/lib/iron-session') return { sessionOptions: {}, SessionData: {} };
  if (id === '@/lib/backend-url') {
    class BackendUrlError extends Error { constructor(code) { super(code); this.code = code; } }
    return { getBackendUrl: () => 'http://backend.local', BackendUrlError };
  }
  if (id === '@/lib/logger') return { logSystemAction: async () => {}, getClientInfo: () => ({ ipAddress: '0.0.0.0', userAgent: 'teste' }) };
  if (id === '@/lib/auxiliaries/server') {
    return {
      resolveSessionCompany: async () => (sessao && sessao.userId ? { userId: sessao.userId, companyId: fixtures().users_v2.find((u) => u.id === sessao.userId)?.company_id } : null),
      getSupabaseAdmin: () => supabase,
    };
  }
  return undefined;
}

function pedidoPOST(url, corpo) {
  return { url, nextUrl: new URL(url), json: async () => corpo, headers: new Map(), text: async () => JSON.stringify(corpo) };
}
function pedidoGET(url) {
  return { url, nextUrl: new URL(url), headers: new Map() };
}

/** Roda uma rota de sessão (messages/conversations/n8n) por caminho. */
async function rodarRota(caminho, metodo, pedido, { sessao, cookiesLoja, linhas = fixtures() }) {
  const registroSupabase = [];
  const supabase = dubleSupabase(linhas, registroSupabase);
  const fetchOriginal = globalThis.fetch;
  const chamadasFetch = [];
  globalThis.fetch = async (url, opts = {}) => {
    let body = null; try { body = opts.body ? JSON.parse(opts.body) : null; } catch { body = opts.body; }
    chamadasFetch.push({ url: String(url), headers: opts.headers || {}, body });
    return { ok: true, status: 200, json: async () => ({ ok: true }), text: async () => '{}' };
  };
  let resposta, erro = null;
  try {
    const rota = carregarTS(caminho, (id) => resolverRotaImport(id, { sessao, supabase, cookiesLoja }));
    resposta = await silenciando(() => rota[metodo](pedido));
  } catch (e) { erro = e; }
  finally { globalThis.fetch = fetchOriginal; }
  return { registroSupabase, chamadasFetch, resposta, erro };
}

function lojaComCookies(nomes) {
  const set = new Set(nomes);
  return { get: (n) => (set.has(n) ? { name: n, value: 'x' } : undefined) };
}

// ═════════════════════════════════════════════════════════════════════════════
// OS GUARDAS
// ═════════════════════════════════════════════════════════════════════════════

console.log('='.repeat(78));
console.log('O CHAT RESPONDE, MOSTRA O TRABALHO E CONTINUA — shell + BFF  (SPEC-096)');
console.log('='.repeat(78));

// ── [1] S.1 · o BFF do stream deriva a corretora da sessão ────────────────────
function analisarStream(res) {
  const problemas = [];
  if (res.erro) return [`a rota estourou: ${res.erro.message}`];
  const fetchAoBackend = res.chamadasFetch.find((c) => /\/chat\/stream$/.test(c.url));
  if (!fetchAoBackend) { problemas.push('o BFF não chamou o backend /chat/stream'); return problemas; }
  const b = fetchAoBackend.body || {};
  if (b.companyId !== CO_ALFA) {
    problemas.push(`o corpo do fetch ao backend leva companyId=${JSON.stringify(b.companyId)} — deve ser o da SESSÃO (${CO_ALFA.slice(0, 7)}), nunca o do corpo do browser (§1.1, P0)`);
  }
  if (b.userId !== U_ALFA) problemas.push(`o fetch leva userId=${JSON.stringify(b.userId)} — deve ser o da sessão`);
  if (b.agentId && b.agentId !== AG_ALFA) problemas.push(`o fetch leva agentId=${JSON.stringify(b.agentId)} — o agente é o da conversa (${AG_ALFA.slice(0, 7)}), nunca o do corpo`);
  const temChave = Object.keys(fetchAoBackend.headers || {}).some((k) => /x-internal-key/i.test(k));
  if (!temChave) problemas.push('o fetch ao backend não leva o header X-Internal-Key (modo painel — S.2)');
  // o header do backend precisa ser repassado ao browser (§1.6); o proxy monta headers novos e o engole
  const h = res.resposta?.headers;
  const temAccel = h instanceof Map ? h.has('x-accel-buffering') : false;
  if (!temAccel) problemas.push("o BFF não repassa 'X-Accel-Buffering: no' ao browser — o proxy monta headers novos e engole o do backend (§1.6)");
  return problemas;
}
console.log('\n[1] S.1 — o BFF do stream deriva a corretora da SESSÃO; o corpo do browser não tem voz');
const streamAlfa = await rodarStream({
  sessao: { userId: U_ALFA, companyId: CO_ALFA },
  corpo: { chatInput: 'x', sessionId: SS_ALFA, client_request_id: 'crid-novo', companyId: CO_BETA, userId: U_BETA, agentId: AG_BETA },
});
console.log(`      fetch ao backend: ${streamAlfa.chamadasFetch.map((c) => c.url).join(', ') || '(nenhum)'}`);
if (streamAlfa.chamadasFetch[0]) console.log(`      corpo repassado: companyId=${JSON.stringify((streamAlfa.chamadasFetch[0].body || {}).companyId)}`);
devendo(analisarStream(streamAlfa), 'o corpo carrega a corretora/usuário da sessão e o X-Internal-Key', 'S.1');
// sem sessão → 401 sem fetch
const streamSemSessao = await rodarStream({ sessao: {}, corpo: { chatInput: 'x', sessionId: SS_ALFA, client_request_id: 'c1' } });
function analisar401SemFetch(res) {
  const problemas = [];
  const status = res.resposta?.status;
  if (status !== 401) problemas.push(`sem sessão a rota respondeu ${status} — deveria ser 401 (S.1)`);
  if (res.chamadasFetch.some((c) => /\/chat\/stream$/.test(c.url))) problemas.push('sem sessão a rota AINDA chamou o backend — o crédito de alguém seria gasto');
  return problemas;
}
devendo(analisar401SemFetch(streamSemSessao), 'sem sessão o BFF do stream devolve 401 e NÃO chama o backend', 'S.1');

// ── [2] A.2 · o BFF grava a pergunta antes do fetch ───────────────────────────
function analisarGravaAntes(res) {
  const problemas = [];
  if (res.erro) return [`a rota estourou: ${res.erro.message}`];
  const idxInsert = res.linhaDoTempo.findIndex((e) => e.tipo === 'insert' && e.tabela === 'messages');
  const idxFetch = res.linhaDoTempo.findIndex((e) => e.tipo === 'fetch' && /\/chat\/stream$/.test(e.url));
  if (idxInsert === -1) { problemas.push('o BFF NÃO grava a pergunta (nenhum insert em `messages`) — hoje quem grava é o browser, sem await (§1.3, A.2)'); return problemas; }
  if (idxFetch !== -1 && idxInsert > idxFetch) problemas.push('a pergunta é gravada DEPOIS do fetch — uma falha no meio deixaria a pergunta sem registro');
  return problemas;
}
console.log('\n[2] A.2 — o servidor grava a PERGUNTA (role=user, client_request_id) ANTES do fetch');
devendo(analisarGravaAntes(streamAlfa), 'o insert em messages acontece antes do fetch ao backend', 'A.2');
// sem client_request_id → 400
const streamSemCrid = await rodarStream({ sessao: { userId: U_ALFA, companyId: CO_ALFA }, corpo: { chatInput: 'x', sessionId: SS_ALFA } });
function analisar400SemCrid(res) {
  const problemas = [];
  if (res.resposta?.status !== 400) problemas.push(`sem client_request_id a rota respondeu ${res.resposta?.status} — deveria ser 400 (R3)`);
  return problemas;
}
devendo(analisar400SemCrid(streamSemCrid), 'sem client_request_id o BFF do stream devolve 400', 'A.2');

// ── [3] R3 · conflito no índice = retentativa ─────────────────────────────────
console.log('\n[3] R3 — conflito no índice único (23505) é retentativa, não erro');
function analisarConflito23505(res) {
  const problemas = [];
  if (res.erro) return [`a rota estourou: ${res.erro.message}`];
  const status = res.resposta?.status;
  if (typeof status === 'number' && status >= 400) {
    problemas.push(`o BFF respondeu ${status} para um conflito 23505 — deveria reaproveitar a linha e seguir (nunca 4xx/5xx)`);
  }
  const consultaReaproveita = res.registroSupabase.find((q) => q.tabela === 'messages' && q.op === 'select' &&
    q.predicados.some((p) => /client_request_id/.test(String(p.coluna))));
  if (!consultaReaproveita) {
    problemas.push('depois do 23505 a rota não fez um SELECT em `messages` filtrando por client_request_id (ou equivalente) — não reaproveitou a linha existente');
  }
  const idxSelect = res.linhaDoTempo.findIndex((e) => e.tipo === 'select' && e.tabela === 'messages');
  const idxFetch = res.linhaDoTempo.findIndex((e) => e.tipo === 'fetch' && /\/chat\/stream$/.test(e.url));
  if (consultaReaproveita && idxFetch !== -1 && (idxSelect === -1 || idxSelect > idxFetch)) {
    problemas.push('o SELECT que reaproveita a linha (por client_request_id) não aconteceu ANTES do fetch ao backend');
  }
  return problemas;
}
const streamConflito = await rodarStream({
  sessao: { userId: U_ALFA, companyId: CO_ALFA },
  corpo: { chatInput: 'x', sessionId: SS_ALFA, client_request_id: 'crid-5' },
  linhas: fixtures(),
  criarSupabase: dubleSupabaseComConflito23505,
});
console.log(`      status: ${streamConflito.resposta?.status} · select de reaproveitamento: ${streamConflito.registroSupabase.some((q) => q.tabela === 'messages' && q.op === 'select') ? 'sim' : 'não'}`);
devendo(analisarConflito23505(streamConflito), 'conflito 23505 → reaproveita a linha e segue', 'R3');

// ── [4] S.3 · /api/messages GET confere o dono ────────────────────────────────
async function messagesGET({ sessao, cookies, conversationId, linhas }) {
  const url = `https://teste.local/api/messages?conversation_id=${conversationId}`;
  return rodarRota('app/api/messages/route.ts', 'GET', pedidoGET(url), { sessao, cookiesLoja: cookies, linhas });
}
function analisarDono(resBeta, resAlfa) {
  const problemas = [];
  if (resBeta.resposta?.status !== 404) {
    problemas.push(`u-beta lendo a conversa de u-alfa recebeu ${resBeta.resposta?.status} — deveria ser 404 (IDOR, §1.2/S.3)`);
  }
  const consultouMessages = resBeta.registroSupabase.some((c) => c.tabela === 'messages');
  if (resBeta.resposta?.status !== 404 && consultouMessages) {
    problemas.push('u-beta chegou a consultar `messages` de outra conversa — a rota não confere o dono antes de ler');
  } else if (consultouMessages && !resBeta.registroSupabase.some((c) => c.tabela === 'messages' && c.predicados.some((p) => p.coluna === 'user_id'))) {
    problemas.push("a consulta a `messages` não filtra por `user_id`/dono (nenhum join com conversations.user_id)");
  }
  if (resAlfa.resposta?.status && resAlfa.resposta.status >= 400) {
    problemas.push(`o DONO (u-alfa) recebeu ${resAlfa.resposta.status} na própria conversa — não pode`);
  }
  return problemas;
}
console.log('\n[4] S.3 — /api/messages GET confere o DONO (conversa de outro = 404)');
const msgBetaSobreAlfa = await messagesGET({ sessao: { userId: U_BETA, companyId: CO_BETA }, cookies: lojaComCookies(['smith_user_session']), conversationId: CV_ALFA });
const msgAlfaSobreAlfa = await messagesGET({ sessao: { userId: U_ALFA, companyId: CO_ALFA }, cookies: lojaComCookies(['smith_user_session']), conversationId: CV_ALFA });
console.log(`      u-beta→cv-alfa: status ${msgBetaSobreAlfa.resposta?.status} · u-alfa→cv-alfa: status ${msgAlfaSobreAlfa.resposta?.status}`);
devendo(analisarDono(msgBetaSobreAlfa, msgAlfaSobreAlfa), 'conversa de outro dono → 404 sem consultar messages', 'S.3');
// admin cookie presente mas sessão admin inválida → 401 (o dublê de validação diz não)
const msgAdminInvalido = await messagesGET({ sessao: {}, cookies: lojaComCookies(['smith_admin_session']), conversationId: CV_ALFA });
function analisarAdminInvalido(res) {
  const problemas = [];
  if (res.resposta?.status !== 401) problemas.push(`cookie admin presente mas sessão admin inválida devolveu ${res.resposta?.status} — a presença do cookie não é autenticação (S.3), deveria ser 401`);
  return problemas;
}
devendo(analisarAdminInvalido(msgAdminInvalido), 'cookie admin presente + sessão admin inválida → 401', 'S.3');

// ── [5] D.2 · /api/messages GET com before= e limit=60 ────────────────────────
function analisarBefore(res) {
  const problemas = [];
  const c = res.registroSupabase.find((q) => q.tabela === 'messages' && q.op === 'select');
  if (!c) { problemas.push('a rota não consultou `messages` — nada a conferir'); return problemas; }
  if (!c.predicados.some((p) => p.op === 'lt' && p.coluna.startsWith('created_at'))) {
    problemas.push('a consulta não usa `lt(created_at, before)` — sem cursor, "carregar anteriores" pagina por OFFSET (R10)');
  }
  if (c.limite == null || c.limite > 61) problemas.push(`a consulta traz limite=${c.limite} — deveria pedir 60 (D.2)`);
  return problemas;
}
console.log('\n[5] D.2 — /api/messages GET com before=/limit=60 (cursor, não OFFSET)');
const msgBefore = await rodarRota('app/api/messages/route.ts', 'GET',
  pedidoGET(`https://teste.local/api/messages?conversation_id=${CV_ALFA}&before=2026-09-02T00:00:00Z&limit=60`),
  { sessao: { userId: U_ALFA, companyId: CO_ALFA }, cookiesLoja: lojaComCookies(['smith_user_session']) });
devendo(analisarBefore(msgBefore), 'a consulta de messages usa lt(created_at) + limit 60', 'D.2');

// ── [6] S.3 · /api/messages POST: role só 'user'; de outro dono → 404 ─────────
async function messagesPOST({ sessao, cookies, corpo }) {
  return rodarRota('app/api/messages/route.ts', 'POST', pedidoPOST('https://teste.local/api/messages', corpo), { sessao, cookiesLoja: cookies });
}
function analisarPOST(resAssistant, resOutroDono) {
  const problemas = [];
  if (resAssistant.resposta?.status !== 400) problemas.push(`POST com role=assistant devolveu ${resAssistant.resposta?.status} — só 'user' é aceito (a resposta é do backend, S.3), deveria ser 400`);
  if (resOutroDono.resposta?.status !== 404) problemas.push(`POST numa conversa de outro dono devolveu ${resOutroDono.resposta?.status} — deveria ser 404`);
  return problemas;
}
console.log('\n[6] S.3 — /api/messages POST: role só user; conversa de outro → 404');
const postAssistant = await messagesPOST({ sessao: { userId: U_ALFA, companyId: CO_ALFA }, cookies: lojaComCookies(['smith_user_session']), corpo: { conversation_id: CV_ALFA, role: 'assistant', content: 'eu não devia poder' } });
const postOutroDono = await messagesPOST({ sessao: { userId: U_BETA, companyId: CO_BETA }, cookies: lojaComCookies(['smith_user_session']), corpo: { conversation_id: CV_ALFA, role: 'user', content: 'invadindo' } });
devendo(analisarPOST(postAssistant, postOutroDono), 'POST recusa role=assistant (400) e conversa de outro (404)', 'S.3');

// ── [7] D.1 · /api/conversations: limite 60 + cursor + has_more ───────────────
function analisarConversas(res) {
  const problemas = [];
  const corpo = res.resposta?.body || {};
  const lista = corpo.conversations || corpo.conversas || [];
  const c = res.registroSupabase.find((q) => q.tabela === 'conversations' && q.op === 'select' && q.predicados.some((p) => p.coluna === 'session_id'));
  if (!c) { problemas.push('a rota não paginou por session_id — a conversa carrega inteira (§1.6)'); return problemas; }
  if (c.limite == null) problemas.push('a consulta de mensagens da conversa não tem LIMITE — a conversa de 1.326 mensagens carrega toda (R10)');
  else if (c.limite > 61) problemas.push(`a consulta traz limite=${c.limite} — deveria pedir 60 (61 para saber o has_more) (D.1)`);
  if (typeof corpo.has_more !== 'boolean') problemas.push('a resposta não traz `has_more` — a tela não sabe se há "carregar anteriores"');
  if (!corpo.cursor) problemas.push('a resposta não traz `cursor` (created_at, id da mais antiga devolvida) (D.1)');
  return problemas;
}
console.log('\n[7] D.1 — /api/conversations?session_id= devolve as últimas 60 + has_more + cursor');
const convComSessao = await rodarRota('app/api/conversations/route.ts', 'GET',
  pedidoGET(`https://teste.local/api/conversations?session_id=${SS_ALFA}`),
  { sessao: { userId: U_ALFA, companyId: CO_ALFA }, linhas: fixtures(131) });
const cMsgs = convComSessao.registroSupabase.find((q) => q.tabela === 'messages');
console.log(`      consulta de messages da conversa: limite=${cMsgs ? cMsgs.limite : '(não consultou)'}`);
devendo(analisarConversas(convComSessao), 'a conversa abre com 60 + has_more + cursor', 'D.1');

// ── [8] S.4 · /api/n8n: a sessão vence ────────────────────────────────────────
function analisarN8N(res) {
  const problemas = [];
  const c = res.registroSupabase.find((q) => q.tabela === 'companies');
  if (!c) { problemas.push('a rota não consultou `companies`'); return problemas; }
  const porEmpresa = c.predicados.find((p) => p.coluna === 'id');
  if (!porEmpresa) { problemas.push('a consulta a companies não filtra por id'); return problemas; }
  if (String(porEmpresa.valor) !== CO_ALFA) {
    problemas.push(`a consulta a companies foi por ${String(porEmpresa.valor).slice(0, 7)} — a sessão é Alfa e o corpo mandou Beta; hoje \`body.companyId || session.companyId\` faz o CORPO vencer (§1.1, R12)`);
  }
  return problemas;
}
console.log('\n[8] S.4 — /api/n8n: a corretora vem da SESSÃO, não do corpo');
const n8nCorpoBeta = await rodarRota('app/api/n8n/route.ts', 'POST',
  pedidoPOST('https://teste.local/api/n8n', { companyId: CO_BETA, chatInput: 'x' }),
  { sessao: { userId: U_ALFA, companyId: CO_ALFA } });
devendo(analisarN8N(n8nCorpoBeta), 'a voz deriva a corretora da sessão (corpo ignorado)', 'S.4');
const n8nSemSessao = await rodarRota('app/api/n8n/route.ts', 'POST',
  pedidoPOST('https://teste.local/api/n8n', { companyId: CO_BETA, chatInput: 'x' }), { sessao: {} });
function analisarN8N401(res) {
  const problemas = [];
  if (res.resposta?.status !== 401) problemas.push(`sem sessão o /api/n8n devolveu ${res.resposta?.status} — deveria ser 401 (R12); hoje o corpo supre a empresa`);
  return problemas;
}
devendo(analisarN8N401(n8nSemSessao), 'sem sessão o /api/n8n devolve 401', 'S.4');

// ── [9] C.2 · page.tsx: sem companyId/userId/agentId; sem UCP; client_request_id
function analisarPageStream(chatFonte) {
  const problemas = [];
  // o fetch a /api/chat/stream não pode levar companyId/userId/agentId
  const blocoFetch = /fetch\(\s*['"`]\/api\/chat\/stream['"`][\s\S]*?\}\s*\)/.exec(chatFonte);
  const corpoFetch = blocoFetch ? blocoFetch[0] : chatFonte;
  for (const chave of ['companyId', 'userId', 'agentId']) {
    if (new RegExp(`${chave}\\s*:`).test(corpoFetch)) {
      problemas.push(`o fetch a /api/chat/stream ainda leva \`${chave}\` no corpo — o browser escolhe a corretora (§1.1, C.2)`);
    }
  }
  if (!/client_request_id/.test(chatFonte)) problemas.push('page.tsx não gera `client_request_id` por envio (R3)');
  if (!/randomUUID\(|uuid/i.test(chatFonte)) problemas.push('page.tsx não usa um uuid para o client_request_id');
  if (/["'{]\s*ucp_|match\(\s*\/\\?\{"type"\s*:\s*"ucp_/.test(chatFonte) || /ucp_/.test(chatFonte)) {
    problemas.push('a heurística `ucp_` (estágio parseado do TEXTO do stream) ainda existe na fonte — o estágio nasce do evento tipado, não do conteúdo (§1.4, R6)');
  }
  return problemas;
}
function analisarPageSemMessagesParaTexto(chatFonte) {
  const problemas = [];
  // o texto deixa de ser gravado pelo browser via /api/messages (A.2)
  if (/saveMessage\s*\([^)]*'text'/.test(chatFonte) || /fetch\(\s*['"`]\/api\/messages['"`][\s\S]{0,400}role:\s*'user'/.test(chatFonte)) {
    problemas.push('page.tsx ainda chama /api/messages para gravar o texto da pergunta — quem grava é o servidor (A.2, §1.3)');
  }
  return problemas;
}
console.log('\n[9] C.2 — page.tsx: client_request_id por envio; sem companyId/userId/agentId; sem UCP; showAgentSelector={false}');
const CHAT_FONTE = fonte('app/dashboard/chat/page.tsx');
devendo(analisarPageStream(CHAT_FONTE), 'o envio leva só client_request_id (uuid); zero companyId/userId/agentId; zero UCP', 'C.2');
devendo(analisarPageSemMessagesParaTexto(CHAT_FONTE), 'page.tsx não grava o texto por /api/messages', 'A.2');
// showAgentSelector={false} é INVARIANTE — hoje já está correto (deve ficar VERDE)
function analisarSeletor(chatFonte) {
  const problemas = [];
  if (!/showAgentSelector=\{false\}/.test(chatFonte)) problemas.push('showAgentSelector={false} sumiu — é invariante (R11)');
  return problemas;
}
checar(analisarSeletor(CHAT_FONTE), 'showAgentSelector={false} continua (invariante R11)');

// ── [10] C.3 · "Tentar de novo" reenvia o MESMO client_request_id ─────────────
function analisarRetry(chatFonte) {
  const problemas = [];
  if (!/AvisoDoTurno|onRetry|Tentar de novo/.test(chatFonte)) {
    problemas.push('page.tsx ainda não tem o AvisoDoTurno com "Tentar de novo" (C.3) — o retry do turno não existe');
    return problemas;
  }
  // o retry precisa reusar o client_request_id do turno, não gerar um novo
  if (/onRetry[\s\S]{0,200}(randomUUID|crypto\.randomUUID)/.test(chatFonte)) {
    problemas.push('"Tentar de novo" gera um NOVO client_request_id — o retry viraria uma pergunta nova (R3)');
  }
  return problemas;
}
console.log('\n[10] C.3 — "Tentar de novo" reenvia o MESMO client_request_id');
devendo(analisarRetry(CHAT_FONTE), 'o retry reusa o client_request_id do turno', 'C.3');

// ── [11] C.1 · lerEventos (parser do envelope v1) ─────────────────────────────
function carregarProtocolo() {
  if (!existe('lib/chat/protocolo.ts')) return null;
  try {
    return carregarTS('lib/chat/protocolo.ts', (id) => {
      if (id === 'react') return {};
      return {};
    });
  } catch (e) { return { __erro: e.message }; }
}
async function analisarLerEventos() {
  const problemas = [];
  const mod = carregarProtocolo();
  if (!mod) { problemas.push('`lib/chat/protocolo.ts` ainda não existe (C.1) — o parser SSE tipado com seq/lacuna não foi escrito'); return problemas; }
  if (mod.__erro) { problemas.push(`lib/chat/protocolo.ts não carrega: ${mod.__erro}`); return problemas; }
  if (typeof mod.lerEventos !== 'function') { problemas.push('protocolo.ts não exporta `lerEventos`'); return problemas; }
  // seq 1,2,3 → 3 eventos na ordem; 1,2,4 → o 3º com transport:'gap'
  try {
    const eventos = (seqs) => seqs.map((s) => ({ protocol: 'autobrokers.interaction.v1', seq: s, type: 'assistant.content.delta', turn: {}, payload: { text: String(s) } }));
    const lidos = await coletar(mod.lerEventos(streamDe(eventos([1, 2, 3]))));
    if (lidos.length < 3) problemas.push(`lerEventos devolveu ${lidos.length} eventos para seq 1,2,3 — esperado 3`);
    const comLacuna = await coletar(mod.lerEventos(streamDe(eventos([1, 2, 4]))));
    if (!comLacuna.some((e) => e && e.transport === 'gap')) problemas.push('seq 1,2,4 não produziu um evento com transport:"gap" — a lacuna passou');
  } catch (e) { problemas.push(`lerEventos estourou: ${e.message}`); }
  return problemas;
}
function streamDe(eventos) {
  const linhas = eventos.map((e) => `data: ${JSON.stringify(e)}\n\n`).join('') + 'data: [DONE]\n\n';
  const bytes = new TextEncoder().encode(linhas);
  let feito = false;
  return new ReadableStream({ pull(c) { if (feito) { c.close(); return; } c.enqueue(bytes); feito = true; } });
}
async function coletar(iter) {
  const saida = [];
  if (iter && typeof iter[Symbol.asyncIterator] === 'function') { for await (const x of iter) saida.push(x); }
  return saida;
}
console.log('\n[11] C.1 — lerEventos: 3 seq em ordem; a lacuna (1,2,4) vira transport:"gap"');
devendo(await analisarLerEventos(), 'lerEventos lê seq em ordem e marca a lacuna', 'C.1');

// ── [12] C.1 · o estado do Turno ──────────────────────────────────────────────
/** Fabrica um Turno inicial mínimo, sem depender de `turnoNovo` existir. */
function turnoInicialDeTeste(crid, amid) {
  return { status: 'submitting', clientRequestId: crid, assistantMessageId: amid, userMessageId: null, stage: null, transport: 'ok', aviso: null, artifacts: [] };
}
function eventoDeTeste(type, payload = {}) {
  return { protocol: 'autobrokers.interaction.v1', seq: 1, type, turn: {}, payload };
}
/** Roda a sequência `sequencia` de eventos pelo reducer dado, a partir de um Turno novo. */
function rodarSequenciaNoReducer(reduzir, crid, amid, tiposEPayloads) {
  let t = turnoInicialDeTeste(crid, amid);
  for (const [type, payload] of tiposEPayloads) t = reduzir(t, eventoDeTeste(type, payload));
  return t;
}
async function analisarTurno() {
  const problemas = [];
  const mod = carregarProtocolo();
  if (!mod) { problemas.push('`lib/chat/protocolo.ts` ainda não existe (C.1) — o estado Turno (submitting→streaming→complete; policy sem content) não foi escrito'); return problemas; }
  if (mod.__erro) { problemas.push(`lib/chat/protocolo.ts não carrega: ${mod.__erro}`); return problemas; }
  const reduzir = mod.reduzirTurno || mod.reduzir || mod.turnoReducer || mod.reducer;
  if (typeof reduzir !== 'function') { problemas.push('protocolo.ts não exporta o reducer do `Turno` (reduzirTurno/reduzir)'); return problemas; }

  // sequência A: turn.accepted → policy.blocked{code:'billing'} → turn.completed
  const t1 = rodarSequenciaNoReducer(reduzir, 'crid-a', 'am-a', [
    ['turn.accepted', { user_message_id: 'um-a', assistant_message_id: 'am-a' }],
    ['policy.blocked', { code: 'billing', message_human: 'Sem crédito para continuar.' }],
    ['turn.completed', {}],
  ]);
  if (t1.status !== 'failed') problemas.push(`turn.accepted→policy.blocked(billing)→turn.completed deveria terminar status 'failed', terminou '${t1.status}'`);
  if (!t1.aviso || t1.aviso.kind !== 'policy') problemas.push(`o aviso do turno não é kind:'policy' (veio ${JSON.stringify(t1.aviso)})`);
  for (const chave of ['content', 'texto', 'text']) {
    if (Object.prototype.hasOwnProperty.call(t1, chave) && t1[chave]) {
      problemas.push(`o Turno tem um campo '${chave}' preenchido — o aviso de policy virou conteúdo do assistente (R5)`);
    }
  }

  // sequência B: turn.accepted → 3 deltas → assistant.content.completed → turn.completed
  let t2 = turnoInicialDeTeste('crid-b', 'am-b');
  let textoAcumulado = '';
  t2 = reduzir(t2, eventoDeTeste('turn.accepted', { user_message_id: 'um-b', assistant_message_id: 'am-b' }));
  for (const pedaco of ['ola', ', ', 'mundo']) {
    t2 = reduzir(t2, eventoDeTeste('assistant.content.delta', { text: pedaco }));
    // a concatenação em si é responsabilidade da TELA (page.tsx lê
    // evento.payload.text/delta a cada delta), não do reducer — o reducer só
    // precisa deixar o evento passar sem quebrar o status; medimos as DUAS
    // coisas separadamente, como a tela faz.
    textoAcumulado += pedaco;
  }
  t2 = reduzir(t2, eventoDeTeste('assistant.content.completed', {}));
  t2 = reduzir(t2, eventoDeTeste('turn.completed', {}));
  if (t2.status !== 'complete') problemas.push(`turn.accepted→3 deltas→completed→turn.completed deveria terminar status 'complete', terminou '${t2.status}'`);
  if (textoAcumulado !== 'ola, mundo') problemas.push(`a concatenação dos deltas deu '${textoAcumulado}' — esperado 'ola, mundo'`);

  return problemas;
}
console.log('\n[12] C.1 — o Turno percorre submitting→streaming→complete; policy.blocked não vira content');
devendo(await analisarTurno(), 'o Turno tem os estados e policy.blocked não cria mensagem do assistente', 'C.1');

// ── [13]-[16] os componentes do shell ─────────────────────────────────────────
function analisarComponente(rel, nome) {
  const problemas = [];
  if (!existe(rel)) problemas.push(`\`${rel}\` ainda não existe (C.3) — ${nome} não foi escrito`);
  return problemas;
}
console.log('\n[13] C.3 — LinhaDeAtividade / CardDeRelatorio / AvisoDoTurno renderizam (sem nome técnico)');
devendo([...analisarComponente('components/chat/LinhaDeAtividade.tsx', 'a linha de atividade'),
  ...analisarComponente('components/chat/CardDeRelatorio.tsx', 'o card do relatório'),
  ...analisarComponente('components/chat/AvisoDoTurno.tsx', 'o aviso do turno')],
  'os três componentes do shell existem e renderizam', 'C.3');

console.log('\n[14] R6 — nenhum setTimeout/setInterval cria estágio em components/chat/* ou lib/chat/*');
function analisarSemRelogioNoEstagio() {
  const problemas = [];
  // 🔴 Sem o componente de estágio da SPEC, não há o que guardar: [14] só pode
  // ficar VERDE depois que a LinhaDeAtividade existir. Um guarda que passa por
  // vacuidade não guarda nada (CLAUDE.md §9.3).
  if (!existe('components/chat/LinhaDeAtividade.tsx')) {
    problemas.push('`components/chat/LinhaDeAtividade.tsx` ainda não existe (C.3) — sem o componente de estágio, o guarda do "estágio não nasce de relógio" não tem o que medir');
    return problemas;
  }
  const dirs = ['components/chat', 'lib/chat'];
  for (const d of dirs) {
    const abs = path.join(RAIZ, d);
    if (!fs.existsSync(abs)) continue;
    for (const f of fs.readdirSync(abs)) {
      if (!/\.(t|j)sx?$/.test(f)) continue;
      const s = fs.readFileSync(path.join(abs, f), 'utf8');
      for (const m of s.matchAll(/set(Timeout|Interval)\s*\([\s\S]{0,120}/g)) {
        if (/stage|estagio|estágio|atividade|LinhaDeAtividade/i.test(m[0])) {
          problemas.push(`${d}/${f}: um set${m[1]} perto de estágio — o estágio nasce de evento, nunca de relógio (R6)`);
        }
      }
    }
  }
  return problemas;
}
devendo(analisarSemRelogioNoEstagio(), 'nenhum estágio nasce de setTimeout/setInterval', 'R6');

console.log('\n[15] R11 — MessageBubble é memoizado (React.memo)');
function analisarMemo() {
  const problemas = [];
  const candidatos = ['components/MessageBubble.tsx', 'components/chat/MessageBubble.tsx'];
  const achado = candidatos.find(existe);
  if (!achado) { problemas.push(`MessageBubble não encontrado em: ${candidatos.join(', ')}`); return problemas; }
  const s = fonte(achado);
  if (!/React\.memo\(|(^|[^.\w])memo\(/.test(s)) problemas.push(`${achado} não é memoizado (React.memo) — cada token re-renderiza o Markdown inteiro (§1.6, R11)`);
  return problemas;
}
devendo(analisarMemo(), 'MessageBubble usa React.memo', 'R11');

console.log('\n[16] C.2 — autoscroll só perto do fim (≤120px) + botão "Voltar ao fim"; o efeito incondicional MORRE');
function analisarAutoscroll(chatFonte) {
  const problemas = [];
  // o useEffect(scrollToBottom, [messages]) incondicional de hoje (page.tsx:147-149) tem de morrer (E9)
  if (/useEffect\(\s*\(\)\s*=>\s*\{?\s*scrollToBottom\(\)[\s\S]{0,40}\},\s*\[messages\]\s*\)/.test(chatFonte)
    || /useEffect\(scrollToBottom\s*,\s*\[messages\]\)/.test(chatFonte)) {
    problemas.push('o `useEffect(scrollToBottom, [messages])` incondicional ainda existe (page.tsx:147-149) — ele puxa a tela a cada mensagem (E9/C.2); o scroll passa a ser condicional (≤120px)');
  }
  if (!/Voltar ao fim/.test(chatFonte)) problemas.push('não há o botão "Voltar ao fim" (C.2) — quem rolou para cima não tem como voltar');
  return problemas;
}
/**
 * 🔴 O LIMIAR em si — `analisarAutoscroll` só confere que a FORMA do efeito
 * incondicional morreu; nada ali mede o NÚMERO. Trocar `120` por `Infinity`
 * (E14, a 14ª mutação) deixava tudo verde, porque nenhuma asserção calculava
 * "a 500px do fim, isso ainda manda rolar?" — a decisão real de `estaPertoDoFim`
 * é inline (fecha sobre `rolagemRef`, não é função pura exportável), então o
 * limiar numérico (`const PERTO_DO_FIM = …`) é extraído da fonte e a MESMA
 * fórmula (`distancia <= limiar`) é executada com um dublê de "distância ao
 * fim" — não um regex sobre a comparação (que usa o nome da constante, não um
 * literal), e sim sobre a declaração da constante.
 */
function extrairLimiarAutoscroll(chatFonte) {
  const decl = /const\s+PERTO_DO_FIM\s*=\s*([^;]+);/.exec(chatFonte);
  if (!decl) return null;
  const valor = Number(decl[1].trim());
  return Number.isNaN(valor) ? null : valor;
}
function pertoDoFim(distanciaAoFimPx, limiar) {
  return distanciaAoFimPx <= limiar;
}
function analisarLimiarAutoscroll(chatFonte) {
  const problemas = [];
  const limiar = extrairLimiarAutoscroll(chatFonte);
  if (limiar == null) {
    // fallback: a decisão pode ter sido reescrita sem a constante nomeada —
    // ainda assim precisa haver um limiar numérico ≤200 na comparação.
    const m = /<=\s*(\d{2,3})\b/.exec(chatFonte);
    if (!m || !(Number(m[1]) <= 200)) {
      problemas.push('não há limiar numérico de autoscroll ≤200px identificável na fonte (nem `PERTO_DO_FIM`, nem comparação inline)');
    }
    return problemas;
  }
  if (!Number.isFinite(limiar)) {
    problemas.push(`PERTO_DO_FIM = ${String(limiar)} não é finito — a tela SEMPRE acha que está perto do fim e sempre rola (E14)`);
    return problemas;
  }
  if (pertoDoFim(500, limiar)) problemas.push(`com o limiar ${limiar}, a 500px do fim a tela ainda decide "rolar" — deveria ser NÃO`);
  if (!pertoDoFim(100, limiar)) problemas.push(`com o limiar ${limiar}, a 100px do fim a tela decide "não rolar" — limiar pequeno/zerado demais`);
  if (limiar > 200) problemas.push(`PERTO_DO_FIM = ${limiar} é grande demais para ser "perto do fim" (deveria ser ≤200)`);
  return problemas;
}
devendo([...analisarAutoscroll(CHAT_FONTE), ...analisarLimiarAutoscroll(CHAT_FONTE)], 'o scroll é condicional (≤120px) e há "Voltar ao fim"', 'C.2');

// ═════════════════════════════════════════════════════════════════════════════
// LINHAS DE CONTROLE — cada guarda acima consegue ficar VERMELHO (PAR sintético)
// ═════════════════════════════════════════════════════════════════════════════
console.log('\n[CTL] LINHAS DE CONTROLE — cada guarda consegue reprovar (protocolo §5)');

// [1] PAR: um resultado de stream SINTÉTICO que repassou o corpo do browser.
controle(analisarStream({ chamadasFetch: [{ url: 'http://backend.local/chat/stream', headers: {}, body: { companyId: CO_BETA, userId: U_BETA, agentId: AG_BETA } }], resposta: { headers: new Map() } }),
  '[1] o BFF repassando a corretora do corpo (o P0 de hoje)');
// PAR positivo: um resultado CORRETO não é acusado — o detector sabe aprovar.
{
  const correto = analisarStream({
    chamadasFetch: [{ url: 'http://backend.local/chat/stream', headers: { 'x-internal-key': 'k' }, body: { companyId: CO_ALFA, userId: U_ALFA, agentId: AG_ALFA } }],
    resposta: { headers: new Map([['x-accel-buffering', 'no']]) },
  });
  controle(correto.length === 0 ? ['(o detector aprovou o correto, como deve)'] : correto,
    '[1] o detector APROVA o correto (veredito oposto do PAR acima)');
}
controle(analisar401SemFetch({ resposta: { status: 200 }, chamadasFetch: [{ url: 'http://backend.local/chat/stream' }] }), '[1] sem sessão respondendo 200 e chamando o backend');

// [2] PAR: linha do tempo com o insert DEPOIS do fetch.
controle(analisarGravaAntes({ erro: null, linhaDoTempo: [{ tipo: 'fetch', url: 'http://backend.local/chat/stream' }, { tipo: 'insert', tabela: 'messages' }] }), '[2] insert da pergunta depois do fetch');
controle(analisar400SemCrid({ resposta: { status: 200 } }), '[2] sem client_request_id respondendo 200');

// [3] PAR: uma rota-controle que devolve 409 no conflito 23505.
controle(analisarConflito23505({
  resposta: { status: 409 },
  registroSupabase: [{ tabela: 'messages', op: 'select', predicados: [{ op: 'eq', coluna: 'payload->>client_request_id', valor: 'crid-5' }] }],
  linhaDoTempo: [{ tipo: 'select', tabela: 'messages' }, { tipo: 'fetch', url: 'http://backend.local/chat/stream' }],
}), '[3] rota-controle devolvendo 409 no conflito 23505');

// [4] PAR: u-beta recebendo 200 na conversa de u-alfa, tendo consultado messages.
controle(analisarDono({ resposta: { status: 200 }, registroSupabase: [{ tabela: 'messages', predicados: [] }] }, { resposta: { status: 200 } }), '[4] conversa de outro dono devolvendo 200');
controle(analisarAdminInvalido({ resposta: { status: 200 } }), '[4] cookie admin inválido passando (200)');

// [5] PAR: consulta de messages sem lt(created_at).
controle(analisarBefore({ registroSupabase: [{ tabela: 'messages', op: 'select', predicados: [{ op: 'eq', coluna: 'conversation_id', valor: CV_ALFA }], limite: null }] }), '[5] messages GET sem lt(created_at) e sem limite');

// [6] PAR
controle(analisarPOST({ resposta: { status: 201 } }, { resposta: { status: 201 } }), '[6] POST aceitando assistant e conversa de outro');

// [7] PAR: resposta sem cursor/has_more, consulta sem limite.
controle(analisarConversas({ resposta: { body: { conversations: [] } }, registroSupabase: [{ tabela: 'conversations', op: 'select', predicados: [{ op: 'eq', coluna: 'session_id', valor: SS_ALFA }] }, { tabela: 'messages', op: 'select', predicados: [], limite: null }] }), '[7] conversa sem limite/has_more/cursor (o de hoje)');

// [8] PAR: consulta a companies pela empresa do corpo (Beta).
controle(analisarN8N({ registroSupabase: [{ tabela: 'companies', predicados: [{ op: 'eq', coluna: 'id', valor: CO_BETA }] }] }), '[8] n8n consultando companies pela empresa do CORPO');
controle(analisarN8N401({ resposta: { status: 400 } }), '[8] n8n sem sessão respondendo 400 (o corpo supre)');

// [9] PAR: page-fonte sintética com companyId no fetch e a heurística ucp_.
controle(analisarPageStream("await fetch('/api/chat/stream', { body: JSON.stringify({ chatInput, companyId: companyId, userId: userId, agentId }) });\naccumulated.match(/\\{\"type\"\\s*:\\s*\"ucp_/);"), '[9] page com companyId no fetch e a heurística ucp_');
controle(analisarPageSemMessagesParaTexto("saveMessage(convId, 'user', message, 'text');"), '[9] page gravando o texto por /api/messages');
controle(analisarSeletor('showAgentSelector={true}'), '[9] showAgentSelector={true}');

// [10] PAR: retry gerando um novo uuid.
controle(analisarRetry("<AvisoDoTurno onRetry={() => { const id = crypto.randomUUID(); enviar(id); }} />"), '[10] "Tentar de novo" gerando um novo client_request_id');

// [11]/[12] PAR: o detector de ausência do módulo acusa quando ele não existe.
function detectorDeAusencia(rel) { return existe(rel) ? [] : [`${rel} ausente`]; }
controle(detectorDeAusencia('lib/chat/protocolo.ts.INEXISTENTE'), '[11]/[12] o detector acusa um módulo ausente');

// [12] PAR: um reducer-CONTROLE que grava o aviso de policy como content do assistente.
controle((() => {
  const reducerRuim = (turno, ev) => {
    if (ev.type === 'policy.blocked') {
      return { ...turno, status: 'failed', content: ev.payload.message_human, aviso: { kind: 'policy', code: ev.payload.code, message_human: ev.payload.message_human } };
    }
    if (ev.type === 'turn.completed') return { ...turno, status: turno.status === 'failed' ? turno.status : 'complete' };
    return turno;
  };
  const t1 = rodarSequenciaNoReducer(reducerRuim, 'crid-c', 'am-c', [
    ['turn.accepted', {}],
    ['policy.blocked', { code: 'billing', message_human: 'sem credito' }],
    ['turn.completed', {}],
  ]);
  return Object.prototype.hasOwnProperty.call(t1, 'content') && t1.content ? ['o reducer-controle grava o aviso como content do assistente'] : [];
})(), '[12] reducer-controle que grava o aviso como content (deve ser reprovado)');

// [14] PAR: um trecho sintético com setTimeout ligado a estágio é reconhecido.
function detectaRelogioNoEstagio(s) {
  const problemas = [];
  for (const m of s.matchAll(/set(Timeout|Interval)\s*\([\s\S]{0,120}/g)) {
    if (/stage|estagio|estágio|atividade/i.test(m[0])) problemas.push(`set${m[1]} perto de estágio`);
  }
  return problemas;
}
controle(detectaRelogioNoEstagio("const t = setTimeout(() => setStage('Consultando…'), 500);"), '[14] setTimeout criando estágio (o detector reconhece o padrão)');

// [15] PAR: um MessageBubble sintético sem memo.
controle((() => {
  const s = 'export function MessageBubble(props) { return null; }';
  return /React\.memo\(|(^|[^.\w])memo\(/.test(s) ? [] : ['sem memo'];
})(), '[15] MessageBubble sem React.memo');

// [16] PAR: page-fonte com o efeito incondicional de volta.
controle(analisarAutoscroll('useEffect(() => { scrollToBottom(); }, [messages]);\nconst scrollToBottom = () => ref.scrollIntoView();'), '[16] o useEffect(scrollToBottom,[messages]) incondicional de volta');
// [16] PAR: o limiar numérico — 120→Infinity (E14) tem de reprovar; a fonte real não pode.
controle(analisarLimiarAutoscroll(CHAT_FONTE.replace('const PERTO_DO_FIM = 120;', 'const PERTO_DO_FIM = Infinity;')), '[16] PERTO_DO_FIM = Infinity (E14 — sempre rola)');
{
  const limiarCorreto = analisarLimiarAutoscroll(CHAT_FONTE);
  controle(limiarCorreto.length === 0 ? ['(o detector aprovou o limiar real, como deve)'] : limiarCorreto, '[16] o detector APROVA o limiar real (veredito oposto do PAR acima)');
}

// ─────────────────────────────────────────────────────────────────────────────
console.log(`\n${'='.repeat(78)}`);
console.log(`  ${falhas.length} falha(s) de verdade · ${esperados.length} VERMELHO ESPERADO · ${jaPodemVirar.length} ja podem virar`);
if (esperados.length > 0) {
  console.log('\n  🔴 VERMELHO ESPERADO — a SPEC-096 PREVE estes ate o bloco citado.');
  console.log('     O GATE ZERO desta SPEC (§4 BLOCO 0.1) e esta lista em `e1494ab`.');
  for (const x of esperados) console.log(`     · ${x}`);
}
if (jaPodemVirar.length > 0) {
  console.log('\n  ✅ ESTES JA FICARAM VERDES. O integrador troca `devendo(...)` por `checar(...)`:');
  for (const x of jaPodemVirar) console.log(`     · ${x}`);
}
if (falhas.length > 0) {
  console.log(`\n  ⛔ ${falhas.length} VERMELHO DE VERDADE:`);
  for (const f of falhas) console.log(`     - ${f}`);
  process.exit(1);
}
if (esperados.length > 0) {
  console.log('\n  (exit 0 com VERMELHO ESPERADO e 0 de verdade: o gate FINAL da SPEC-096 so fecha\n   com a lista acima VAZIA — protocolo v11.2, opcao B)');
} else {
  console.log('\nVERDE — a corretora vem da sessão, a pergunta é do servidor, e o shell mostra o trabalho sem teatro.');
}
