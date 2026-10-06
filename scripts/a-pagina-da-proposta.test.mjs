// SPEC-130-A · F2a — a página da PROPOSTA no /r/: script SÓ pelo hash, prévia e "Quero fechar".
//
// Roda o GET REAL de `app/r/[token]/route.ts` e de `app/r/[token]/previa.png/route.ts`
// (TypeScript transpilado do disco, `next/server` real), com o BACKEND dublado em `fetch`
// — não um regex sobre o texto da rota (CLAUDE.md §9.4).
//
//   ① proposta: a CSP ganha `script-src '<hash>'` (o que o backend devolveu) e mais nada;
//      nunca 'unsafe-inline'; o User-Agent de quem abriu vai ao backend (G17)
//   ② relatório: CSP sem script nenhum — mesmo se o backend mandasse um hash
//   ③ hash fora do formato (tentativa de injetar diretiva) é DESCARTADO
//   ④ "Quero fechar" (`?fechar=<opção>`): POST ao backend, 302 só para https://wa.me/<dígitos>
//   ⑤ a imagem da prévia: só image/png do backend vira 200
//   🔴 mutações (um fator só, reconstruídas do fonte): sem o filtro do hash e sem a conferência do
//      wa.me, os guardas ③ e ④ ficam VERMELHOS — prova de que conseguem falhar (CLAUDE.md §9.3).
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import ts from 'typescript';

const require = createRequire(import.meta.url);
const RAIZ = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const { NextRequest } = require('next/server');

let pass = 0, fail = 0;
function assert(nome, cond, extra = '') {
  if (cond) { pass++; console.log(`  ✓ ${nome}`); }
  else { fail++; console.log(`  ✗ ${nome}${extra ? ' — ' + extra : ''}`); }
}

function carregar(fonte, nome) {
  const js = ts.transpileModule(fonte, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, esModuleInterop: true },
    fileName: nome,
  }).outputText;
  const mod = { exports: {} };
  const req = (id) => { if (id === 'next/server') return require('next/server'); throw new Error(`import nao previsto: ${id}`); };
  // eslint-disable-next-line no-new-func
  new Function('require', 'module', 'exports', js)(req, mod, mod.exports);
  return mod.exports;
}

const FONTE_ROTA = fs.readFileSync(path.join(RAIZ, 'app/r/[token]/route.ts'), 'utf8');
const FONTE_PREVIA = fs.readFileSync(path.join(RAIZ, 'app/r/[token]/previa.png/route.ts'), 'utf8');
const rota = carregar(FONTE_ROTA, 'route.ts');
const previa = carregar(FONTE_PREVIA, 'previa.route.ts');

const LINHA_FILTRO = "typeof h === 'string' && HASH_CSP.test(h)";
const LINHA_WAME = "u.protocol === 'https:' && u.hostname === 'wa.me' && /^\\/\\d{10,15}$/.test(u.pathname)";
const rotaSemFiltro = carregar(FONTE_ROTA.replace(LINHA_FILTRO, 'true'), 'route.SEM_FILTRO.ts');
const rotaSemWame = carregar(FONTE_ROTA.replace(LINHA_WAME, 'true'), 'route.SEM_WAME.ts');

const BASE = 'http://localhost:3000';
const TOKEN = 'tOkEnDaPrOpOsTa_de-teste_0123456789abcdefgh';
const HASH = 'sha256-JGyohBesjQwVIBLv52rb2Cn1P4E6l30KHcSA/Qw1ojQ=';
const UA = 'WhatsApp/2.23.20.0 A';

const env0 = { u: process.env.NEXT_PUBLIC_API_URL, k: process.env.BACKEND_INTERNAL_API_KEY };
process.env.NEXT_PUBLIC_API_URL = 'http://backend-falso.invalid';
process.env.BACKEND_INTERNAL_API_KEY = 'chave-falsa-de-teste';
const fetch0 = globalThis.fetch;
let pedidos = [];
function backend(resposta) {
  pedidos = [];
  globalThis.fetch = async (u, init = {}) => {
    pedidos.push({ url: String(u), init });
    const r = typeof resposta === 'function' ? resposta(String(u), init) : resposta;
    return r instanceof Response ? r : new Response(JSON.stringify(r), { status: 200, headers: { 'content-type': 'application/json' } });
  };
}
async function get(mod, caminho, ua) {
  const headers = ua ? { 'user-agent': ua } : {};
  return mod.GET(new NextRequest(BASE + caminho, { headers }), { params: Promise.resolve({ token: TOKEN }) });
}
const diretivas = (res) => (res.headers.get('content-security-policy') || '').split(/;\s*/);
const PAGINA = '<!doctype html><html><head></head><body>PROPOSTA</body></html>';

console.log('== a página da proposta no /r/ ==\n');
assert('🔴 as mutações foram mesmo aplicadas (um fator só cada)',
  FONTE_ROTA.includes(LINHA_FILTRO) && FONTE_ROTA.includes(LINHA_WAME));

try {
  // ① proposta
  {
    backend({ ok: true, html: PAGINA, kind: 'proposal', csp_script_hashes: [HASH] });
    const res = await get(rota, `/r/${TOKEN}`, UA);
    const d = diretivas(res);
    assert('proposta: 200 e o HTML do backend', res.status === 200 && (await res.text()) === PAGINA);
    assert("proposta: a CSP tem script-src com o hash do backend", d.includes(`script-src '${HASH}'`), d.join('; '));
    assert("proposta: default-src 'none' e img-src 'self' data: continuam", d.includes("default-src 'none'") && d.includes("img-src 'self' data:"));
    assert("proposta: nenhuma 'unsafe-inline' fora do style-src", !d.some((x) => x.includes('unsafe-inline') && !x.startsWith('style-src')), d.join('; '));
    assert('proposta: só UMA diretiva nova (script-src) em relação ao relatório', d.length === 8, `${d.length}: ${d.join('; ')}`);
    assert('o User-Agent de quem abriu vai ao backend (X-Visitante-User-Agent)',
      pedidos[0]?.init?.headers?.['X-Visitante-User-Agent'] === UA, JSON.stringify(pedidos[0]?.init?.headers));
  }
  // ② relatório
  {
    backend({ ok: true, html: '<p>RELATORIO</p>', kind: 'report' });
    const d = diretivas(await get(rota, `/r/${TOKEN}`));
    assert('relatório: CSP sem script-src', !d.some((x) => x.startsWith('script-src')), d.join('; '));
    assert('relatório: as 7 diretivas de antes', d.length === 7, d.join('; '));
    backend({ ok: true, html: '<p>RELATORIO</p>', kind: 'report', csp_script_hashes: [HASH] });
    const d2 = diretivas(await get(rota, `/r/${TOKEN}`));
    assert('relatório com hash vindo do backend: CONTINUA sem script (só proposal libera)', !d2.some((x) => x.startsWith('script-src')), d2.join('; '));
  }
  // ③ hash fora do formato
  {
    const ruim = `${HASH}' 'unsafe-inline`;
    backend({ ok: true, html: PAGINA, kind: 'proposal', csp_script_hashes: [ruim, 'sha256-curto'] });
    const d = diretivas(await get(rota, `/r/${TOKEN}`));
    assert('hash fora do formato é descartado: sem script-src, sem unsafe-inline', !d.some((x) => x.startsWith('script-src')) && !d.join(';').includes("'unsafe-inline' "), d.join('; '));
    const m = diretivas(await get(rotaSemFiltro, `/r/${TOKEN}`));
    assert('CONTROLE: sem o filtro do hash, a diretiva injetada PASSARIA (o guarda consegue falhar)',
      m.some((x) => x.startsWith('script-src') && x.includes('unsafe-inline')), m.join('; '));
  }
  // ④ "Quero fechar"
  {
    backend((u, init) => ({ ok: true, destino: 'https://wa.me/5548999990000?text=Ol%C3%A1' }));
    const res = await get(rota, `/r/${TOKEN}?fechar=recomendada`, UA);
    assert('fechar: 302 para o wa.me que o backend montou',
      res.status === 302 && res.headers.get('location') === 'https://wa.me/5548999990000?text=Ol%C3%A1', `${res.status} ${res.headers.get('location')}`);
    assert('fechar: POST ao /fechar com a opção no corpo (não visualiza a página)',
      pedidos.length === 1 && pedidos[0].url.endsWith(`/api/artifacts/shared/${TOKEN}/fechar`) && pedidos[0].init.method === 'POST'
      && JSON.parse(pedidos[0].init.body).opcao === 'recomendada', JSON.stringify(pedidos));
    assert('fechar: sem cache e sem referrer', res.headers.get('cache-control')?.includes('no-store') && res.headers.get('referrer-policy') === 'no-referrer');

    backend({ ok: true, destino: 'https://evil.example/5548999990000' });
    const evil = await get(rota, `/r/${TOKEN}?fechar=recomendada`);
    assert('fechar: destino que não é wa.me → 404 (nunca redirecionamento aberto)', evil.status === 404 && !evil.headers.get('location'));
    const mEvil = await get(rotaSemWame, `/r/${TOKEN}?fechar=recomendada`);
    assert('CONTROLE: sem a conferência do wa.me, o destino ruim PASSARIA', mEvil.status === 302, `${mEvil.status}`);

    backend(new Response('{"detail":"indisponivel"}', { status: 404 }));
    const des = await get(rota, `/r/${TOKEN}?fechar=inexistente`);
    assert('fechar: opção que o backend não conhece → 404', des.status === 404);

    backend({ ok: true, destino: 'https://wa.me/5548999990000' });
    for (const op of ['../x', 'a b', 'x'.repeat(65), '']) {
      const r = await get(rota, `/r/${TOKEN}?fechar=${encodeURIComponent(op)}`);
      assert(`fechar: opção fora do formato (${JSON.stringify(op.slice(0, 8))}) → 404 sem ir ao backend`, r.status === 404 && pedidos.length === 0, `${r.status} pedidos=${pedidos.length}`);
    }
  }
  // ⑤ a imagem da prévia
  {
    const png = new Uint8Array([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 1, 2, 3]);
    backend(new Response(png, { status: 200, headers: { 'content-type': 'image/png' } }));
    const res = await get(previa, `/r/${TOKEN}/previa.png`);
    const corpo = new Uint8Array(await res.arrayBuffer());
    assert('prévia: 200 image/png com os bytes do backend',
      res.status === 200 && res.headers.get('content-type') === 'image/png' && corpo.length === png.length && corpo[1] === 0x50);
    assert('prévia: pediu o /previa.png do backend com a chave interna',
      pedidos[0].url.endsWith(`/api/artifacts/shared/${TOKEN}/previa.png`) && pedidos[0].init.headers['X-Internal-Key'] === 'chave-falsa-de-teste');
    backend(new Response('<html>', { status: 200, headers: { 'content-type': 'text/html' } }));
    assert('prévia: backend que não devolve PNG → 404', (await get(previa, `/r/${TOKEN}/previa.png`)).status === 404);
    backend(new Response('', { status: 404 }));
    assert('prévia: link morto → 404', (await get(previa, `/r/${TOKEN}/previa.png`)).status === 404);
    const inval = await previa.GET(new NextRequest(`${BASE}/r/curto/previa.png`), { params: Promise.resolve({ token: 'curto' }) });
    assert('prévia: token fora do formato → 404', inval.status === 404);
  }
} finally {
  globalThis.fetch = fetch0;
  if (env0.u === undefined) delete process.env.NEXT_PUBLIC_API_URL; else process.env.NEXT_PUBLIC_API_URL = env0.u;
  if (env0.k === undefined) delete process.env.BACKEND_INTERNAL_API_KEY; else process.env.BACKEND_INTERNAL_API_KEY = env0.k;
}

console.log(`\n${pass} ok, ${fail} falha(s)`);
process.exit(fail ? 1 : 0);
