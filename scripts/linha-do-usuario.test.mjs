// modelo: claude-opus-5-5
// ===========================================================================
// SPEC-131-0-B2 L3 — A LINHA DO USUÁRIO NA TELA (Meu perfil → WhatsApp de trabalho + a faixa do topo)
// ===========================================================================
//
// O que este arquivo prova, rodando o CÓDIGO REAL (TypeScript transpilado, `require` falso só na borda):
//   ① os 4 BFF (`app/api/dashboard/meu-perfil/linha/**`) mandam ao backend o company_id e o user_id DA SESSÃO —
//      com um corpo e uma query FORJADOS apontando para outra corretora, o backend recebe a da sessão;
//      sem sessão, ninguém é chamado; nos POST, a origem é conferida ANTES; e o que volta é só o contrato
//      (nenhum telefone em claro atravessa o BFF, mesmo que o backend mande um).
//   ② o bloco "Conversar com o AutoBrokers pelo seu WhatsApp" SOME no estado `desligada` (e sem leitura);
//      cada estado mostra a sua frase; o QR é imagem com texto alternativo humano; só o número MASCARADO aparece.
//   ③ o relógio do QR (`criarPollDoQr`) para ao conectar, ao parar (desmontar), com a aba oculta, e ignora a
//      resposta que chega depois de parado; e o componente desmonta chamando `parar` e tirando o ouvinte.
//   ④ a faixa do topo só aparece em `desconectada`, é dispensável por sessão e lê UMA vez (sem relógio).
//
// MUTAÇÃO (vermelho provado no relatório): o BFF `conectar` lendo `company_id` do corpo → ① fica VERMELHO.
//
// Rodar: node --test scripts/linha-do-usuario.test.mjs
//   (fora da árvore principal: NODE_PATH apontando para um node_modules com typescript, react e react-dom)

import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const RAIZ = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const requireReal = createRequire(import.meta.url); // honra o NODE_PATH (CJS)
const ts = requireReal('typescript');
const React = requireReal('react');
const jsxRuntime = requireReal('react/jsx-runtime');
const { renderToStaticMarkup } = requireReal('react-dom/server');

const ler = (rel) => fs.readFileSync(path.join(RAIZ, rel), 'utf8');
const existe = (rel) => fs.existsSync(path.join(RAIZ, rel));

/** tira comentários — o guarda olha o CÓDIGO, não a história contada nos comentários */
function semComentarios(fonte) {
  return fonte.replace(/\/\*[\s\S]*?\*\//g, '').replace(/(^|[^:'"`\w])\/\/[^\n]*/g, '$1');
}

// ─────────────────────────────────────────────────────────────────────────────
// Carregador: TypeScript/TSX real, `require` falso (o mesmo de o-membro-liga-o-agente.test.mjs)
// ─────────────────────────────────────────────────────────────────────────────
function carregarTS(rel, resolver = () => undefined) {
  const fonte = ler(rel);
  const js = ts.transpileModule(fonte, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, esModuleInterop: true,
      jsx: ts.JsxEmit.ReactJSX,
    },
    fileName: rel,
  }).outputText;
  const mod = { exports: {} };
  const req = (id) => {
    if (id === 'react') return React;
    if (id === 'react/jsx-runtime') return jsxRuntime;
    const r = resolver(id);
    if (r === undefined) throw new Error(`import não previsto no teste: ${id} (em ${rel})`);
    return r;
  };
  // eslint-disable-next-line no-new-func
  new Function('require', 'module', 'exports', js)(req, mod, mod.exports);
  return mod.exports;
}

// ─────────────────────────────────────────────────────────────────────────────
// ① OS BFF — a corretora e a pessoa vêm SÓ da sessão
// ─────────────────────────────────────────────────────────────────────────────
const SESSAO_A = { companyId: 'aaaaaaaa-1111-4111-8111-111111111111', userId: 'cccccccc-3333-4333-8333-333333333333' };
const FORJADA_B = { company_id: 'bbbbbbbb-2222-4222-8222-222222222222', user_id: 'dddddddd-4444-4444-8444-444444444444' };
const TELEFONE_FICTICIO = '5511900000001';

const ROTAS = {
  estado: { arq: 'app/api/dashboard/meu-perfil/linha/route.ts', metodo: 'GET', backend: '/api/linha-do-usuario/estado' },
  qr: { arq: 'app/api/dashboard/meu-perfil/linha/qr/route.ts', metodo: 'GET', backend: '/api/linha-do-usuario/qr' },
  conectar: { arq: 'app/api/dashboard/meu-perfil/linha/conectar/route.ts', metodo: 'POST', backend: '/api/linha-do-usuario/conectar' },
  desconectar: { arq: 'app/api/dashboard/meu-perfil/linha/desconectar/route.ts', metodo: 'POST', backend: '/api/linha-do-usuario/desconectar' },
};

/** o que o backend falso devolve — com um telefone em claro "vazado" de propósito, para provar o filtro do BFF */
const RESPOSTA_DO_BACKEND = {
  estado: { estado: 'conectada', numero_mascarado: '(11) 9••••-0001', desde: '2026-10-15T12:00:00Z', motivo: null, paired_phone_e164: TELEFONE_FICTICIO, numero: TELEFONE_FICTICIO },
  qr: { qr: 'data:image/png;base64,iVBORw0KGgo=', estado: 'aguardando_qr', paired_phone_e164: TELEFONE_FICTICIO },
  conectar: { tentativa_id: 't-1', qr: 'data:image/png;base64,iVBORw0KGgo=', instance_token: 'segredo-nao-sai', paired_phone_e164: TELEFONE_FICTICIO },
  desconectar: { ok: true, paired_phone_e164: TELEFONE_FICTICIO },
};

async function chamarBff(nome, { sessao = SESSAO_A, origemOk = true, backendCai = false, statusDoBackend = 200 } = {}) {
  const rota = ROTAS[nome];
  const chamadas = { backend: [], ordem: [] };
  const mod = carregarTS(rota.arq, (id) => {
    if (id === 'next/server') {
      return { NextResponse: { json: (body, init) => ({ body, status: init?.status ?? 200, headers: init?.headers ?? {} }) } };
    }
    if (id === '@/lib/admin/admin-auth') {
      return {
        assertSameOrigin: () => { chamadas.ordem.push('origem'); return origemOk ? null : { ok: false, status: 403, error: 'cross_origin_blocked' }; },
        requireCompanyMember: async (opts) => {
          chamadas.ordem.push('sessao');
          chamadas.opcoesDaSessao = opts;
          if (!sessao) return { ok: false, status: 401, error: 'no_session' };
          return { ok: true, ctx: { ...sessao, role: 'member', isOwner: false }, supabase: {} };
        },
      };
    }
    if (id === '@/lib/backend-url') return { getBackendUrl: () => 'http://backend.teste' };
    return undefined;
  });
  const fetchAntigo = globalThis.fetch;
  const chaveAntiga = process.env.BACKEND_INTERNAL_API_KEY;
  process.env.BACKEND_INTERNAL_API_KEY = 'chave-interna-de-teste';
  globalThis.fetch = async (url, init = {}) => {
    chamadas.backend.push({ url: String(url), init });
    if (backendCai) throw new Error('ECONNREFUSED');
    return {
      ok: statusDoBackend < 400, status: statusDoBackend,
      json: async () => (statusDoBackend < 400 ? RESPOSTA_DO_BACKEND[nome] : { detail: 'Estamos no limite de conexões neste momento.', estado: 'limite', paired_phone_e164: TELEFONE_FICTICIO }),
    };
  };
  // o pedido FORJADO: corpo e query dizem "corretora B"
  const urlForjada = `http://app.teste/api/dashboard/meu-perfil/linha?company_id=${FORJADA_B.company_id}&user_id=${FORJADA_B.user_id}`;
  const req = {
    method: rota.metodo,
    url: urlForjada,
    nextUrl: new URL(urlForjada),
    headers: { get: (h) => (h.toLowerCase() === 'origin' ? 'http://app.teste' : h.toLowerCase() === 'host' ? 'app.teste' : null) },
    json: async () => ({ ...FORJADA_B }),
    text: async () => JSON.stringify(FORJADA_B),
  };
  try {
    const handler = mod[rota.metodo];
    assert.equal(typeof handler, 'function', `${rota.arq} não exporta ${rota.metodo}`);
    const r = await handler(req);
    return { r, chamadas };
  } finally {
    globalThis.fetch = fetchAntigo;
    if (chaveAntiga === undefined) delete process.env.BACKEND_INTERNAL_API_KEY; else process.env.BACKEND_INTERNAL_API_KEY = chaveAntiga;
  }
}

/** o company_id e o user_id que o backend RECEBEU (query no GET, corpo no POST) */
function idsRecebidos({ url, init }) {
  const u = new URL(url);
  let corpo = {};
  try { corpo = init.body ? JSON.parse(init.body) : {}; } catch { corpo = {}; }
  return {
    company_id: corpo.company_id ?? u.searchParams.get('company_id'),
    user_id: corpo.user_id ?? u.searchParams.get('user_id'),
    tudo: `${url} ${init.body ?? ''}`,
  };
}

for (const nome of Object.keys(ROTAS)) {
  test(`① BFF ${nome}: a corretora e a pessoa vêm da SESSÃO, nunca do corpo nem da query`, async () => {
    assert.ok(existe(ROTAS[nome].arq), `falta o arquivo ${ROTAS[nome].arq}`);
    const { r, chamadas } = await chamarBff(nome);
    assert.equal(chamadas.backend.length, 1, 'o backend devia ser chamado uma vez');
    const c = chamadas.backend[0];
    assert.ok(c.url.startsWith(`http://backend.teste${ROTAS[nome].backend}`), `rota do backend errada: ${c.url}`);
    assert.equal(c.init.method ?? 'GET', ROTAS[nome].metodo);
    const ids = idsRecebidos(c);
    assert.equal(ids.company_id, SESSAO_A.companyId, 'o backend recebeu outra corretora que não a da sessão');
    assert.equal(ids.user_id, SESSAO_A.userId, 'o backend recebeu outra pessoa que não a da sessão');
    assert.ok(!ids.tudo.includes(FORJADA_B.company_id) && !ids.tudo.includes(FORJADA_B.user_id),
      'o valor FORJADO (corretora B) chegou ao backend');
    // a chave interna e o "sem cache"
    const h = c.init.headers ?? {};
    assert.equal(h['X-AutoBrokers-Internal-Key'], 'chave-interna-de-teste', 'falta a X-AutoBrokers-Internal-Key');
    assert.equal(c.init.cache, 'no-store', 'a chamada ao backend tem de ser no-store');
    assert.equal(r.status, 200);
    assert.equal(r.headers?.['Cache-Control'], 'no-store', 'a resposta do BFF tem de ser no-store');
    // nenhum telefone em claro nem segredo atravessa o BFF
    const saiu = JSON.stringify(r.body);
    assert.ok(!saiu.includes(TELEFONE_FICTICIO), `telefone em claro saiu pelo BFF ${nome}: ${saiu}`);
    assert.ok(!saiu.includes('segredo-nao-sai'), `campo fora do contrato saiu pelo BFF ${nome}`);
    // a sessão é de MEMBRO (não exige admin): a linha é da própria pessoa
    assert.equal(chamadas.opcoesDaSessao?.write, false);
  });

  test(`① BFF ${nome}: sem sessão, ninguém chama o backend`, async () => {
    const { r, chamadas } = await chamarBff(nome, { sessao: null });
    assert.equal(r.status, 401);
    assert.equal(chamadas.backend.length, 0);
  });

  test(`① BFF ${nome}: backend fora do ar → 502 com frase humana`, async () => {
    const { r } = await chamarBff(nome, { backendCai: true });
    assert.equal(r.status, 502);
    assert.ok(typeof r.body?.error === 'string' && /\s/.test(r.body.error) && !/backend/i.test(r.body.error),
      `a frase do 502 tem de ser de gente: ${JSON.stringify(r.body)}`);
  });

  test(`① BFF ${nome}: erro do backend passa o status e a frase, sem telefone`, async () => {
    const { r } = await chamarBff(nome, { statusDoBackend: 429 });
    assert.equal(r.status, 429);
    assert.equal(r.body?.estado, 'limite');
    assert.ok(!JSON.stringify(r.body).includes(TELEFONE_FICTICIO));
  });

  test(`① BFF ${nome}: o CÓDIGO não lê corpo, query nem formulário`, () => {
    const fonte = semComentarios(ler(ROTAS[nome].arq));
    assert.ok(!/req(uest)?\.json\s*\(|\.formData\s*\(|searchParams|nextUrl|req(uest)?\.text\s*\(|req(uest)?\.url/.test(fonte),
      `${ROTAS[nome].arq} lê algo do pedido além da origem`);
    assert.ok(/requireCompanyMember\(\{\s*write:\s*false\s*\}\)/.test(fonte));
    assert.ok(/X-AutoBrokers-Internal-Key/.test(fonte));
  });
}

for (const nome of ['conectar', 'desconectar']) {
  test(`① BFF ${nome} (POST): a ORIGEM é conferida antes da sessão; origem estranha não chama ninguém`, async () => {
    const ok = await chamarBff(nome);
    assert.deepEqual(ok.chamadas.ordem.slice(0, 2), ['origem', 'sessao']);
    const ruim = await chamarBff(nome, { origemOk: false });
    assert.equal(ruim.r.status, 403);
    assert.equal(ruim.chamadas.backend.length, 0);
    assert.ok(!ruim.chamadas.ordem.includes('sessao'));
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// Os componentes — renderizados de verdade (React 18, renderToStaticMarkup)
// ─────────────────────────────────────────────────────────────────────────────
const nada = () => null;
const icones = new Proxy({}, { get: () => nada });
function stubComum(id) {
  if (id === 'lucide-react') return icones;
  if (id === '@/components/aplicativos/casca/CardDoAplicativo') return { BOTAO_PRIMARIO: 'botao-primario' };
  if (id === '@/components/aplicativos/casca/Confirmar') {
    // o gatilho é o filho; o diálogo não abre no teste (só a sua existência importa)
    return { Confirmar: ({ children, titulo }) => React.createElement('span', { 'data-confirmar': titulo }, children) };
  }
  if (id === '@/lib/utils') return { cn: (...a) => a.filter(Boolean).join(' ') };
  if (id === '@/components/ui/skeleton') return { Skeleton: nada };
  if (id === 'next/link') return { __esModule: true, default: ({ href, children, ...p }) => React.createElement('a', { href, ...p }, children) };
  if (id === 'next/navigation') return { usePathname: () => '/dashboard/hoje' };
  return undefined;
}

let _perfil;
function perfilMod() {
  if (!_perfil) _perfil = carregarTS('components/perfil/useMeuPerfil.ts', stubComum);
  return _perfil;
}
function linhaMod() {
  return carregarTS('components/perfil/MinhaLinhaDoWhatsApp.tsx', (id) => (id === './useMeuPerfil' ? perfilMod() : stubComum(id)));
}
function faixaMod() {
  return carregarTS('components/avisos/FaixaDaLinha.tsx', (id) => (id === '@/components/perfil/useMeuPerfil' ? perfilMod() : stubComum(id)));
}

const LINHA = (estado, extra = {}) => ({ estado, numero_mascarado: null, desde: null, motivo: null, ...extra });
const desenhar = (Comp, props) => renderToStaticMarkup(React.createElement(Comp, props));
const semAcao = { aoMudar: () => {}, recarregar: () => {} };

test('② desligada (e sem leitura): o bloco NÃO aparece', () => {
  const { MinhaLinhaDoWhatsApp } = linhaMod();
  assert.equal(desenhar(MinhaLinhaDoWhatsApp, { linha: LINHA('desligada'), ...semAcao }), '');
  assert.equal(desenhar(MinhaLinhaDoWhatsApp, { linha: null, ...semAcao }), '');
  // CONTROLE: o mesmo componente, com a linha ofertada, DESENHA — o vazio acima veio do estado, não de um componente quebrado
  assert.ok(desenhar(MinhaLinhaDoWhatsApp, { linha: LINHA('nao_conectada'), ...semAcao }).length > 0);
});

test('② não conectada: título, frase curta e o botão "Conectar meu WhatsApp"', () => {
  const { MinhaLinhaDoWhatsApp } = linhaMod();
  const html = desenhar(MinhaLinhaDoWhatsApp, { linha: LINHA('nao_conectada'), ...semAcao });
  assert.match(html, /Conversar com o AutoBrokers pelo seu WhatsApp/);
  assert.match(html, /<button[^>]*>Conectar meu WhatsApp<\/button>/);
  assert.match(html, /aria-live="polite"/);
});

test('② aguardando o QR: o caminho no celular, o QR como imagem com texto humano, e Cancelar', () => {
  const { VistaDaLinha } = linhaMod();
  const qr = 'data:image/png;base64,iVBORw0KGgo=';
  const html = desenhar(VistaDaLinha, {
    linha: LINHA('aguardando_qr'), qr, ocupado: false, erro: '', aviso: '',
    aoConectar: () => {}, aoCancelar: () => {}, aoDesconectar: () => {},
  });
  assert.match(html, /No celular: WhatsApp → Aparelhos conectados → Conectar um aparelho → aponte para este código/);
  assert.match(html, /Android/);
  assert.match(html, /iPhone/);
  const img = html.match(/<img[^>]*>/)?.[0] ?? '';
  assert.ok(img.includes(`src="${qr}"`), 'o QR tem de ser a imagem que veio do servidor');
  assert.match(img, /alt="[^"]*WhatsApp[^"]*"/, 'o QR precisa de texto alternativo humano');
  const largura = Number(img.match(/width="(\d+)"/)?.[1] ?? 0);
  assert.ok(largura >= 240, `o QR precisa de ≥ 240 px (tem ${largura})`);
  assert.match(html, /bg-white/, 'o QR fica em fundo branco (o celular não lê QR no escuro)');
  assert.match(html, />Cancelar</);
  // um QR que NÃO é imagem de dados nunca vira src
  const ruim = desenhar(VistaDaLinha, {
    linha: LINHA('aguardando_qr'), qr: 'javascript:alert(1)', ocupado: false, erro: '', aviso: '',
    aoConectar: () => {}, aoCancelar: () => {}, aoDesconectar: () => {},
  });
  assert.ok(!/<img/.test(ruim), 'um "QR" que não é data:image virou <img>');
});

test('② conectada: só o número MASCARADO que veio do servidor — nenhum telefone em claro', () => {
  const { MinhaLinhaDoWhatsApp } = linhaMod();
  const html = desenhar(MinhaLinhaDoWhatsApp, {
    linha: { ...LINHA('conectada', { numero_mascarado: '(11) 9••••-0001', desde: '2026-10-15T12:00:00Z' }), numero: TELEFONE_FICTICIO, paired_phone_e164: TELEFONE_FICTICIO },
    ...semAcao,
  });
  assert.match(html, /Conectado/);
  assert.ok(html.includes('(11) 9••••-0001'), 'o número mascarado tem de aparecer');
  assert.match(html, /desde 15\/10\/2026/);
  assert.ok(!/900000001|9\s?0000-0001|90000-0001/.test(html), `telefone em claro na tela: ${html}`);
  assert.match(html, /Mensagem para você/);
  assert.match(html, /data-confirmar="[^"]+"[^>]*>.*Desconectar/s, 'o Desconectar passa pelo Confirmar da casa');
  // e o CÓDIGO não formata número nenhum: só repete o mascarado
  const fonte = semComentarios(ler('components/perfil/MinhaLinhaDoWhatsApp.tsx'));
  assert.ok(!/paired_phone|numero_e164|\bexibir\s*\(/.test(fonte), 'o componente da linha mexe em número em claro');
});

test('② desconectada: a frase da SPEC §4 e "Conectar de novo"; limite: a frase humana', () => {
  const { MinhaLinhaDoWhatsApp } = linhaMod();
  const html = desenhar(MinhaLinhaDoWhatsApp, { linha: LINHA('desconectada', { desde: '2026-10-01T15:00:00Z' }), ...semAcao });
  assert.match(html, /Seu WhatsApp desconectou do AutoBrokers em 01\/10\/2026\. Isso acontece quando o celular fica 14 dias sem internet ou quando o aparelho é removido em/);
  assert.match(html, /Aparelhos conectados/);
  assert.match(html, />Conectar de novo</);
  const lim = desenhar(MinhaLinhaDoWhatsApp, { linha: LINHA('limite'), ...semAcao });
  assert.match(lim, /Estamos no limite de conexões neste momento\. Tente de novo mais tarde\./);
});

test('② nenhuma frase da tela usa jargão (instância, webhook, JID, QR code, token)', () => {
  for (const arq of ['components/perfil/MinhaLinhaDoWhatsApp.tsx', 'components/avisos/FaixaDaLinha.tsx']) {
    const { MinhaLinhaDoWhatsApp } = arq.includes('Minha') ? linhaMod() : { MinhaLinhaDoWhatsApp: null };
    const htmls = MinhaLinhaDoWhatsApp
      ? ['nao_conectada', 'conectada', 'desconectada', 'limite', 'aguardando_qr'].map((e) => desenhar(MinhaLinhaDoWhatsApp, { linha: LINHA(e), ...semAcao }))
      : [desenhar(faixaMod().FaixaDaLinhaVista, { linha: LINHA('desconectada'), aoDispensar: () => {} })];
    for (const h of htmls) {
      const texto = h.replace(/<[^>]+>/g, ' ');
      assert.ok(!/inst[aâ]ncia|webhook|\bJID\b|\bLID\b|token|\bAPI\b/i.test(texto), `jargão na tela (${arq}): ${texto}`);
    }
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// ③ O RELÓGIO DO QR
// ─────────────────────────────────────────────────────────────────────────────
function relogioFalso() {
  const pendentes = new Map();
  let n = 0;
  return {
    pendentes,
    setTimeout: (fn, ms) => { const id = ++n; pendentes.set(id, { fn, ms }); return id; },
    clearTimeout: (id) => { pendentes.delete(id); },
    async disparar() {
      const [[id, t]] = [...pendentes.entries()];
      pendentes.delete(id);
      t.fn();
      await new Promise((r) => setImmediate(r));
      await new Promise((r) => setImmediate(r));
    },
  };
}

test('③ o relógio do QR lê a cada 4 s enquanto espera e PARA ao conectar', async () => {
  const { criarPollDoQr, INTERVALO_DO_QR_MS } = perfilMod();
  assert.equal(INTERVALO_DO_QR_MS, 4000);
  const relogio = relogioFalso();
  const respostas = [{ qr: 'data:image/png;base64,A', estado: 'aguardando_qr' }, { qr: null, estado: 'conectada' }];
  const lidas = [];
  let buscas = 0;
  const poll = criarPollDoQr({ buscar: async () => { buscas++; return respostas.shift(); }, aoLer: (l) => lidas.push(l), relogio, visivel: () => true });
  poll.iniciar();
  poll.iniciar(); // idempotente: não dobra o relógio
  assert.equal(relogio.pendentes.size, 1);
  assert.equal([...relogio.pendentes.values()][0].ms, 4000);
  await relogio.disparar();
  assert.equal(buscas, 1);
  // CONTROLE: aguardando → o relógio CONTINUA (prova que o "parou" abaixo pode falhar)
  assert.equal(relogio.pendentes.size, 1, 'esperando o QR, o relógio devia continuar');
  await relogio.disparar();
  assert.equal(buscas, 2);
  assert.equal(lidas.at(-1).estado, 'conectada');
  assert.equal(relogio.pendentes.size, 0, 'conectou e o relógio continuou');
  assert.equal(poll.ativo(), false);
});

test('③ parado (desmontou), a resposta em voo é ignorada e nada mais é agendado', async () => {
  const { criarPollDoQr } = perfilMod();
  const relogio = relogioFalso();
  let soltar;
  const lidas = [];
  const poll = criarPollDoQr({ buscar: () => new Promise((r) => { soltar = r; }), aoLer: (l) => lidas.push(l), relogio, visivel: () => true });
  poll.iniciar(true); // imediato
  await new Promise((r) => setImmediate(r));
  poll.parar();
  soltar({ qr: 'data:image/png;base64,B', estado: 'aguardando_qr' });
  await new Promise((r) => setImmediate(r));
  assert.equal(lidas.length, 0, 'a resposta chegou depois de desmontar e foi usada');
  assert.equal(relogio.pendentes.size, 0, 'parado e ainda agendou');
});

test('③ com a aba do navegador oculta, o relógio não busca e para', async () => {
  const { criarPollDoQr } = perfilMod();
  const relogio = relogioFalso();
  let buscas = 0;
  const poll = criarPollDoQr({ buscar: async () => { buscas++; return { qr: null, estado: 'aguardando_qr' }; }, aoLer: () => {}, relogio, visivel: () => false });
  poll.iniciar();
  await relogio.disparar();
  assert.equal(buscas, 0);
  assert.equal(relogio.pendentes.size, 0);
});

test('③ o componente liga o relógio só esperando o QR e, ao desmontar, para e tira o ouvinte da aba', () => {
  const fonte = semComentarios(ler('components/perfil/MinhaLinhaDoWhatsApp.tsx'));
  assert.ok(/criarPollDoQr\s*\(/.test(fonte), 'o componente não usa o relógio do QR');
  assert.ok(!/setInterval\s*\(/.test(fonte), 'relógio paralelo (setInterval) no componente');
  assert.match(fonte, /estado\s*!==\s*'aguardando_qr'\)\s*return/);
  assert.match(fonte, /addEventListener\(\s*'visibilitychange'/);
  const limpeza = fonte.match(/return\s*\(\)\s*=>\s*\{([^}]*)\}/)?.[1] ?? '';
  assert.match(limpeza, /\.parar\(\)/, 'a limpeza do efeito não para o relógio');
  assert.match(limpeza, /removeEventListener\(\s*'visibilitychange'/, 'a limpeza do efeito não tira o ouvinte da aba');
});

// ─────────────────────────────────────────────────────────────────────────────
// ④ A FAIXA DO TOPO
// ─────────────────────────────────────────────────────────────────────────────
test('④ a faixa só aparece em "desconectada"', () => {
  const { FaixaDaLinhaVista, faixaAparece } = faixaMod();
  for (const e of ['nao_conectada', 'aguardando_qr', 'conectada', 'limite', 'desligada']) {
    assert.equal(desenhar(FaixaDaLinhaVista, { linha: LINHA(e), aoDispensar: () => {} }), '', `a faixa apareceu em ${e}`);
    assert.equal(faixaAparece(LINHA(e), false, '/dashboard/hoje'), false);
  }
  assert.equal(faixaAparece(null, false, '/dashboard/hoje'), false);
  const html = desenhar(FaixaDaLinhaVista, { linha: LINHA('desconectada', { desde: '2026-10-01T15:00:00Z' }), aoDispensar: () => {} });
  assert.match(html, /Seu WhatsApp desconectou do AutoBrokers em 01\/10\/2026/);
  assert.match(html, /href="\/dashboard\/configuracoes\?aba=whatsapp"[^>]*>Conectar de novo</);
  assert.match(html, /aria-label="[^"]+"/, 'o fechar precisa de rótulo');
  // CONTROLE: em desconectada, aparece; dispensada, some; na própria tela do perfil, some (o bloco já diz)
  assert.equal(faixaAparece(LINHA('desconectada'), false, '/dashboard/hoje'), true);
  assert.equal(faixaAparece(LINHA('desconectada'), true, '/dashboard/hoje'), false);
  assert.equal(faixaAparece(LINHA('desconectada'), false, '/dashboard/configuracoes'), false);
});

test('④ a faixa lê UMA vez (sem relógio), guarda a dispensa com try/catch, e o layout a monta uma vez', () => {
  const fonte = semComentarios(ler('components/avisos/FaixaDaLinha.tsx'));
  assert.ok(!/setInterval\s*\(|setTimeout\s*\(|criarPollDoQr/.test(fonte), 'a faixa ganhou relógio');
  assert.equal((fonte.match(/buscarLinha\s*\(/g) ?? []).length, 1, 'a faixa devia ler a linha uma vez só');
  assert.match(fonte, /useEffect\([\s\S]*?\},\s*\[\]\s*\)/, 'a leitura é ao montar');
  const usos = fonte.match(/sessionStorage\.[gs]etItem/g) ?? [];
  assert.ok(usos.length >= 2);
  assert.equal((fonte.match(/try\s*\{[^}]*sessionStorage/g) ?? []).length, usos.length, 'todo acesso ao sessionStorage vai em try/catch');
  const layout = semComentarios(ler('app/dashboard/layout.tsx'));
  assert.equal((layout.match(/<FaixaDaLinha\b/g) ?? []).length, 1, 'o layout monta a faixa uma vez');
});

test('④ o "Meu WhatsApp de trabalho" monta o bloco no topo e não mente com a linha conectada', () => {
  const fonte = semComentarios(ler('components/perfil/MeuWhatsAppDeTrabalho.tsx'));
  assert.match(fonte, /<MinhaLinhaDoWhatsApp\b/);
  const iBloco = fonte.indexOf('<MinhaLinhaDoWhatsApp');
  const iTitulo = fonte.indexOf('Meu WhatsApp de trabalho</h3>');
  assert.ok(iBloco > 0 && iTitulo > 0 && iBloco < iTitulo, 'o bloco da linha vai no TOPO da aba');
  // a frase "não se conecta" só pode existir condicionada à linha NÃO conectada
  const i = fonte.indexOf('o AutoBrokers não se conecta a ele');
  if (i >= 0) {
    const antes = fonte.slice(Math.max(0, i - 600), i);
    assert.match(antes, /linhaConectada/, '"não se conecta" aparece sem olhar se a linha está conectada (§9.3)');
  }
});
