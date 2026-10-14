// SPEC-132-A · A2 — o UPLOAD do chat e o BFF do turno com ANEXOS.
//
// Roda o POST REAL de `app/api/upload/route.ts` e de `app/api/chat/stream/route.ts` (TypeScript transpilado
// do disco, `next/server` real, `lib/storage/resolver.ts` real) — dublês SÓ na borda: a sessão, o Storage
// (`uploadObject`), o Supabase do BFF e o fetch ao backend. Nunca um regex sobre o texto da rota (CLAUDE.md §9.4).
//
//   ① upload: `ok:true` + `path` com o prefixo `<company_id da SESSÃO>/` + os campos antigos (avatars/voz)
//   ② HEIC (image/heic e application/octet-stream com .heic), .xls, .csv do Windows, áudio do MediaRecorder
//   ③ 21 MB → 413 com `motivo` humano · .exe → 415 · sem sessão → 401 · avatars continua em 5 MB
//   ④ BFF: `attachments` com path de OUTRA corretora → 403, nada gravado, backend não chamado
//   ⑤ BFF: o anexo válido é repassado ao backend e gravado em `messages.payload.attachments` (sem conteúdo);
//      a pergunta sem texto vira "[Anexo] nome"; `esforco` fora do conjunto é descartado
//   🔴 mutações (em MEMÓRIA, um fator só, reconstruídas do fonte): sem a conferência do prefixo no BFF, o path
//      alheio PASSARIA; sem o mapa de extensão, o HEIC do Android seria recusado (o guarda consegue falhar — §9.3).
//
// Rodar: node scripts/o-upload-do-chat.test.mjs
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

function transpilar(fonte, nome) {
  return ts.transpileModule(fonte, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, esModuleInterop: true },
    fileName: nome,
  }).outputText;
}
function carregar(fonte, nome, resolver) {
  const mod = { exports: {} };
  const req = (id) => {
    if (id === 'next/server') return require('next/server');
    if (id === 'crypto') return require('node:crypto');
    const r = resolver(id);
    if (r) return r;
    throw new Error(`import nao previsto: ${id}`);
  };
  // eslint-disable-next-line no-new-func
  new Function('require', 'module', 'exports', transpilar(fonte, nome))(req, mod, mod.exports);
  return mod.exports;
}

const RESOLVER_REAL = carregar(fs.readFileSync(path.join(RAIZ, 'lib/storage/resolver.ts'), 'utf8'), 'resolver.ts', () => null);

// Duas corretoras FICTÍCIAS (CLAUDE.md §13.9 — nenhum nome real).
const CO_A = 'aaaaaaaa-1320-4a00-8000-00000000000a';
const CO_B = 'bbbbbbbb-1320-4b00-8000-00000000000b';
const U_A = 'cccccccc-1320-4c00-8000-00000000000c';

// ─────────────────────────────────────────────────────────────────────────────
// o UPLOAD
// ─────────────────────────────────────────────────────────────────────────────
const FONTE_UPLOAD = fs.readFileSync(path.join(RAIZ, 'app/api/upload/route.ts'), 'utf8');
let sessaoDoUpload = { companyId: CO_A, userId: U_A };
let gravados = [];
let erroDoStorage = null;
function resolverUpload(id) {
  if (id === '@/lib/storage/resolver') return RESOLVER_REAL;
  if (id === '@/lib/admin/admin-auth') {
    return {
      requireCompanyMember: async () => (sessaoDoUpload
        ? { ok: true, ctx: { companyId: sessaoDoUpload.companyId, userId: sessaoDoUpload.userId } }
        : { ok: false, status: 401, error: 'no_session' }),
      getAdminContext: async () => null,
    };
  }
  if (id === '@/lib/storage/signed') {
    return {
      uploadObject: async ({ ref, body, contentType }) => {
        if (erroDoStorage) return { error: erroDoStorage };
        gravados.push({ ...ref, bytes: body.length, contentType });
        return { path: ref.path };
      },
    };
  }
  return null;
}
const upload = carregar(FONTE_UPLOAD, 'upload.route.ts', resolverUpload);

const LINHA_DO_MAPA = 'if (formato && (declarado === formato.mime || formato.aliases.includes(declarado) || MIME_GENERICO.has(declarado))) {';
const uploadSemMapa = carregar(FONTE_UPLOAD.replace(LINHA_DO_MAPA, 'if (false) {'), 'upload.SEM_MAPA.ts', resolverUpload);

const PNG = new Uint8Array([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 0, 0, 0, 13]);
const HEIC = new Uint8Array([0, 0, 0, 24, 0x66, 0x74, 0x79, 0x70, 0x68, 0x65, 0x69, 0x63, 0, 0, 0, 0]); // ....ftypheic
const OLE = new Uint8Array([0xd0, 0xcf, 0x11, 0xe0, 0xa1, 0xb1, 0x1a, 0xe1, 0, 0, 0, 0]);
const WEBM = new Uint8Array([0x1a, 0x45, 0xdf, 0xa3, 0x9f, 0x42, 0x86, 0x81]);
const MZ = new Uint8Array([0x4d, 0x5a, 0x90, 0x00]);

async function subir(mod, { bytes, nome, tipo, bucket = 'chat-media' }) {
  const fd = new FormData();
  fd.append('file', new File([bytes], nome, { type: tipo }));
  fd.append('bucket', bucket);
  const res = await mod.POST(new NextRequest('http://localhost:3000/api/upload', { method: 'POST', body: fd }));
  let corpo = null;
  try { corpo = await res.json(); } catch { /* sem JSON */ }
  return { status: res.status, corpo };
}

console.log('== o upload do chat ==\n');
assert('🔴 a mutação do mapa de extensão foi mesmo aplicada (um fator só)', FONTE_UPLOAD.includes(LINHA_DO_MAPA));

{
  gravados = [];
  const r = await subir(upload, { bytes: PNG, nome: 'foto do carro.png', tipo: 'image/png' });
  const c = r.corpo || {};
  assert('PNG: 201 e ok:true', r.status === 201 && c.ok === true, JSON.stringify(r));
  assert(`o path começa com o prefixo da corretora DA SESSÃO (${CO_A.slice(0, 8)}…/)`, typeof c.path === 'string' && c.path.startsWith(`${CO_A}/`), c.path);
  assert('o path é <company>/<usuário>/<bucket>/<uuid>.<ext>', new RegExp(`^${CO_A}/${U_A}/chat-media/[0-9a-f-]{36}\\.png$`).test(c.path || ''), c.path);
  assert('o contrato novo: bucket · path · nome · mime · bytes · url', c.bucket === 'chat-media' && c.nome === 'foto do carro.png'
    && c.mime === 'image/png' && c.bytes === PNG.length && c.url === `/api/storage/chat-media/${(c.path || '').split('/').map(encodeURIComponent).join('/')}`, JSON.stringify(c));
  assert('os campos antigos continuam (success · storagePath · filePath · fileName · mimeType · size)', c.success === true
    && c.storagePath === `chat-media/${c.path}` && c.filePath === c.path && c.fileName === c.nome && c.mimeType === 'image/png' && c.size === PNG.length);
  assert('sem publicUrl (o contrato não tem esse campo)', !('publicUrl' in c));
  assert('o Storage recebeu o MESMO path e o tipo canônico', gravados.length === 1 && gravados[0].path === c.path && gravados[0].contentType === 'image/png');
}
{
  sessaoDoUpload = { companyId: CO_B, userId: U_A };
  const r = await subir(upload, { bytes: PNG, nome: 'b.png', tipo: 'image/png' });
  assert('outra sessão, outra corretora: o prefixo é o DELA', r.corpo?.path?.startsWith(`${CO_B}/`), r.corpo?.path);
  sessaoDoUpload = { companyId: CO_A, userId: U_A };
}
{
  const r1 = await subir(upload, { bytes: HEIC, nome: 'IMG_0001.HEIC', tipo: 'image/heic' });
  assert('HEIC (image/heic, do iPhone): aceito', r1.status === 201 && r1.corpo?.mime === 'image/heic', JSON.stringify(r1));
  const r2 = await subir(upload, { bytes: HEIC, nome: 'IMG_0002.heic', tipo: 'application/octet-stream' });
  assert('HEIC como application/octet-stream (Android): aceito pela extensão', r2.status === 201 && r2.corpo?.mime === 'image/heic', JSON.stringify(r2));
  const m = await subir(uploadSemMapa, { bytes: HEIC, nome: 'IMG_0002.heic', tipo: 'application/octet-stream' });
  assert('CONTROLE: sem o mapa de extensão, o HEIC do Android seria RECUSADO (o guarda consegue falhar)', m.status === 415, `${m.status}`);
  const r3 = await subir(upload, { bytes: PNG, nome: 'falso.heic', tipo: 'image/heic' });
  assert('".heic" que não é HEIC (sem ftyp): 415 com motivo humano', r3.status === 415 && /não confere/.test(r3.corpo?.motivo || ''), JSON.stringify(r3.corpo));
}
{
  const xls = await subir(upload, { bytes: OLE, nome: 'carteira.xls', tipo: 'application/vnd.ms-excel', bucket: 'chat-docs' });
  assert('.xls: aceito no chat-docs', xls.status === 201 && xls.corpo?.mime === 'application/vnd.ms-excel', JSON.stringify(xls.corpo));
  const csv = await subir(upload, { bytes: new TextEncoder().encode('nome;valor\nA;1\n'), nome: 'lista.csv', tipo: 'application/vnd.ms-excel', bucket: 'chat-docs' });
  assert('.csv que o Windows manda como application/vnd.ms-excel: aceito como text/csv', csv.status === 201 && csv.corpo?.mime === 'text/csv', JSON.stringify(csv.corpo));
  const voz = await subir(upload, { bytes: WEBM, nome: 'gravacao.webm', tipo: 'audio/webm;codecs=opus', bucket: 'chat-docs' });
  assert('áudio do MediaRecorder (audio/webm;codecs=opus): aceito como audio/webm', voz.status === 201 && voz.corpo?.mime === 'audio/webm', JSON.stringify(voz.corpo));
  const m4a = await subir(upload, { bytes: new Uint8Array([0, 0, 0, 32, 0x66, 0x74, 0x79, 0x70, 0x4d, 0x34, 0x41, 0x20]), nome: 'audio.m4a', tipo: 'audio/x-m4a', bucket: 'chat-docs' });
  assert('.m4a (audio/x-m4a): aceito como audio/mp4', m4a.status === 201 && m4a.corpo?.mime === 'audio/mp4', JSON.stringify(m4a.corpo));
}
{
  gravados = [];
  const grande = new Uint8Array(21 * 1024 * 1024);
  grande.set(PNG);
  const r = await subir(upload, { bytes: grande, nome: 'enorme.png', tipo: 'image/png' });
  assert('21 MB → 413 com motivo "O arquivo passa de 20 MB."', r.status === 413 && r.corpo?.ok === false && r.corpo?.motivo === 'O arquivo passa de 20 MB.', JSON.stringify(r.corpo));
  assert('21 MB: nada foi ao Storage', gravados.length === 0);
  const quase = new Uint8Array(19 * 1024 * 1024);
  quase.set(PNG);
  const ok = await subir(upload, { bytes: quase, nome: 'grande.png', tipo: 'image/png' });
  assert('19 MB no chat → aceito (o teto do chat é 20 MB, não mais 5)', ok.status === 201, `${ok.status}`);
  const av = await subir(upload, { bytes: new Uint8Array(6 * 1024 * 1024).fill(0).map((v, i) => (i < 4 ? [0xff, 0xd8, 0xff, 0xe0][i] : 0)), nome: 'eu.jpg', tipo: 'image/jpeg', bucket: 'avatars' });
  assert('avatars continua em 5 MB (6 MB → 413 "passa de 5 MB")', av.status === 413 && /5 MB/.test(av.corpo?.motivo || ''), JSON.stringify(av.corpo));
}
{
  const exe = await subir(upload, { bytes: MZ, nome: 'programa.exe', tipo: 'application/x-msdownload', bucket: 'chat-docs' });
  assert('.exe → 415 "Formato não aceito: .exe"', exe.status === 415 && exe.corpo?.motivo === 'Formato não aceito: .exe', JSON.stringify(exe.corpo));
  const disfarcado = await subir(upload, { bytes: MZ, nome: 'apolice.pdf', tipo: 'application/pdf', bucket: 'chat-docs' });
  assert('programa disfarçado de .pdf → 415 (magic bytes) com frase humana', disfarcado.status === 415 && /programa/.test(disfarcado.corpo?.motivo || ''), JSON.stringify(disfarcado.corpo));
  sessaoDoUpload = null;
  const sem = await subir(upload, { bytes: PNG, nome: 'a.png', tipo: 'image/png' });
  assert('sem sessão → 401 com motivo', sem.status === 401 && sem.corpo?.ok === false && !!sem.corpo?.motivo, JSON.stringify(sem.corpo));
  sessaoDoUpload = { companyId: CO_A, userId: U_A };
  erroDoStorage = 'The object exceeded the maximum allowed size';
  const st = await subir(upload, { bytes: PNG, nome: 'a.png', tipo: 'image/png' });
  assert('o Storage recusa por tamanho (limite do bucket) → 413 humano, não 500 genérico', st.status === 413 && /limite/.test(st.corpo?.motivo || ''), JSON.stringify(st.corpo));
  erroDoStorage = null;
  const vazio = await subir(upload, { bytes: new Uint8Array(0), nome: 'nada.txt', tipo: 'text/plain', bucket: 'chat-docs' });
  assert('arquivo vazio → 400 com motivo', vazio.status === 400 && /vazio/.test(vazio.corpo?.motivo || ''), JSON.stringify(vazio.corpo));
}

// ─────────────────────────────────────────────────────────────────────────────
// o BFF do turno
// ─────────────────────────────────────────────────────────────────────────────
console.log('\n== o BFF do turno com anexos ==\n');
const FONTE_BFF = fs.readFileSync(path.join(RAIZ, 'app/api/chat/stream/route.ts'), 'utf8');
const LINHA_DO_PREFIXO = 'return segmentos[0] === companyId;';

function dubleSupabase(registro) {
  return {
    from(tabela) {
      const q = { tabela, op: 'select', filtros: [], payload: null };
      registro.push(q);
      const cad = {
        select() { return cad; },
        eq(c, v) { q.filtros.push([c, v]); return cad; },
        limit() { return cad; },
        insert(p) { q.op = 'insert'; q.payload = p; return cad; },
        update(p) { q.op = 'update'; q.payload = p; return cad; },
        async maybeSingle() {
          if (tabela === 'agents') return { data: { id: 'dddddddd-1320-4d00-8000-00000000000d' }, error: null };
          return { data: null, error: null };
        },
        async single() {
          if (tabela === 'conversations') return { data: { id: 'conv-1', agent_id: 'dddddddd-1320-4d00-8000-00000000000d' }, error: null };
          return { data: { id: 'msg-1' }, error: null };
        },
        then(ok) { return Promise.resolve({ data: null, error: null }).then(ok); },
      };
      return cad;
    },
  };
}
function carregarBff(fonte, registro) {
  return carregar(fonte, 'stream.route.ts', (id) => {
    if (id === '@/lib/auxiliaries/server') {
      return { resolveSessionCompany: async () => ({ userId: U_A, companyId: CO_A }), getSupabaseAdmin: () => dubleSupabase(registro) };
    }
    if (id === '@/lib/backend-url') {
      class BackendUrlError extends Error {}
      return { getBackendUrl: () => 'http://backend.invalid', BackendUrlError };
    }
    return null;
  });
}
const fetch0 = globalThis.fetch;
async function turno(fonte, corpo) {
  const registro = [];
  const chamadas = [];
  globalThis.fetch = async (u, init = {}) => {
    chamadas.push({ url: String(u), body: JSON.parse(init.body || '{}'), headers: init.headers || {} });
    return new Response('data: {"type":"turn.completed"}\n\n', { status: 200, headers: { 'content-type': 'text/event-stream' } });
  };
  const err0 = console.error; console.error = () => {};
  try {
    const rota = carregarBff(fonte, registro);
    const res = await rota.POST(new NextRequest('http://localhost:3000/api/chat/stream', {
      method: 'POST', body: JSON.stringify(corpo), headers: { 'content-type': 'application/json' },
    }));
    let json = null;
    if ((res.headers.get('content-type') || '').includes('application/json')) json = await res.json();
    return { status: res.status, json, registro, chamadas };
  } finally { globalThis.fetch = fetch0; console.error = err0; }
}
const anexoDe = (co, extra = {}) => ({ bucket: 'chat-docs', path: `${co}/${U_A}/chat-docs/11111111-2222-4333-8444-555555555555.pdf`, nome: 'apolice.pdf', mime: 'application/pdf', bytes: 1234, ...extra });
const base = { client_request_id: 'req-132a-1', sessionId: '99999999-1320-4900-8000-000000000009' };

assert('🔴 a mutação do prefixo foi mesmo aplicada (um fator só)', FONTE_BFF.includes(LINHA_DO_PREFIXO));
{
  const r = await turno(FONTE_BFF, { ...base, chatInput: 'leia', attachments: [anexoDe(CO_B)] });
  assert('path de OUTRA corretora → 403 com motivo', r.status === 403 && r.json?.ok === false && /não pertence/.test(r.json?.motivo || ''), JSON.stringify(r.json));
  assert('403: o backend NÃO foi chamado', r.chamadas.length === 0);
  assert('403: nada foi gravado (nem conversa, nem pergunta)', !r.registro.some((q) => q.op === 'insert' || q.op === 'update'), JSON.stringify(r.registro.map((q) => q.op + ':' + q.tabela)));
  const m = await turno(FONTE_BFF.replace(LINHA_DO_PREFIXO, 'return true;'), { ...base, chatInput: 'leia', attachments: [anexoDe(CO_B)] });
  assert('CONTROLE: sem a conferência do prefixo, o path alheio PASSARIA ao backend', m.status === 200 && m.chamadas.length === 1, `${m.status}`);
}
{
  const fuga = await turno(FONTE_BFF, { ...base, chatInput: 'x', attachments: [anexoDe(CO_A, { path: `${CO_A}/../${CO_B}/x/y.pdf` })] });
  assert('path com ".." que começa com o prefixo certo → 403 (não escapa)', fuga.status === 403, `${fuga.status}`);
  const balde = await turno(FONTE_BFF, { ...base, chatInput: 'x', attachments: [anexoDe(CO_A, { bucket: 'portal-evidence' })] });
  assert('bucket fora do chat (portal-evidence) → 400', balde.status === 400 && balde.chamadas.length === 0, `${balde.status}`);
  const onze = await turno(FONTE_BFF, { ...base, chatInput: 'x', attachments: Array.from({ length: 11 }, () => anexoDe(CO_A)) });
  assert('11 anexos → 400 "até 10"', onze.status === 400 && /até 10/.test(onze.json?.motivo || ''), JSON.stringify(onze.json));
}
{
  const r = await turno(FONTE_BFF, {
    ...base, chatInput: '', attachments: [anexoDe(CO_A), anexoDe(CO_A, { bucket: 'chat-media', nome: 'foto.jpg', mime: 'image/jpeg', path: `${CO_A}/${U_A}/chat-media/66666666-2222-4333-8444-555555555555.jpg` })],
    options: { web_search: true, esforco: 'turbo', deep: true }, companyId: CO_B,
  });
  const ida = r.chamadas[0]?.body || {};
  assert('o anexo válido: 200 e o backend chamado UMA vez', r.status === 200 && r.chamadas.length === 1, `${r.status} ${r.chamadas.length}`);
  assert('o backend recebe attachments [{bucket, path, nome, mime, bytes}] — os mesmos 2', Array.isArray(ida.attachments) && ida.attachments.length === 2
    && ida.attachments[0].path === anexoDe(CO_A).path && ida.attachments[1].bucket === 'chat-media' && ida.attachments[0].bytes === 1234, JSON.stringify(ida.attachments));
  assert('a corretora do backend é a da SESSÃO, não a do corpo', ida.companyId === CO_A, ida.companyId);
  assert('options: esforco "turbo" e chaves desconhecidas são DESCARTADOS; web_search passa', JSON.stringify(ida.options) === '{"web_search":true}', JSON.stringify(ida.options));
  const pergunta = r.registro.find((q) => q.tabela === 'messages' && q.op === 'insert')?.payload || {};
  assert('a pergunta sem texto vira "[Anexo] apolice.pdf, foto.jpg"', pergunta.content === '[Anexo] apolice.pdf, foto.jpg', pergunta.content);
  const lista = pergunta.payload?.attachments || [];
  assert('messages.payload.attachments: {nome, mime, bytes, path} de cada um, sem conteúdo nem URL', lista.length === 2
    && lista[0].nome === 'apolice.pdf' && lista[0].mime === 'application/pdf' && lista[0].bytes === 1234 && lista[0].path === anexoDe(CO_A).path
    && !JSON.stringify(lista).includes('/api/storage') && !lista.some((a) => 'conteudo' in a || 'url' in a), JSON.stringify(lista));
  assert('o client_request_id continua no payload da pergunta', pergunta.payload?.client_request_id === 'req-132a-1');
}
{
  for (const esforco of ['rapido', 'equilibrado', 'maximo']) {
    const r = await turno(FONTE_BFF, { ...base, chatInput: 'oi', options: { esforco } });
    assert(`esforco "${esforco}" passa ao backend`, r.chamadas[0]?.body?.options?.esforco === esforco, JSON.stringify(r.chamadas[0]?.body?.options));
  }
  const legado = await turno(FONTE_BFF, { ...base, chatInput: 'veja', imageUrl: 'https://exemplo.test/a.jpg', fileUrl: 'https://exemplo.test/b.pdf', fileName: 'b.pdf' });
  const ida = legado.chamadas[0]?.body || {};
  assert('o caminho antigo (imageUrl/fileUrl/fileName) continua passando — o widget', legado.status === 200 && ida.imageUrl === 'https://exemplo.test/a.jpg'
    && ida.fileUrl === 'https://exemplo.test/b.pdf' && ida.fileName === 'b.pdf' && !('attachments' in ida), JSON.stringify(ida));
  const msg = legado.registro.find((q) => q.tabela === 'messages' && q.op === 'insert')?.payload || {};
  assert('sem anexos, o payload da pergunta não ganha attachments', !('attachments' in (msg.payload || {})), JSON.stringify(msg.payload));
}

console.log(`\n${pass} ok, ${fail} falha(s)`);
process.exit(fail ? 1 : 0);
