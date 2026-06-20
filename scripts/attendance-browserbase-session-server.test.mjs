#!/usr/bin/env node
/** 43P-FINAL-2 — browserbase server session (offline, DI; connectUrl só em memória). */
import {
  createBrowserbaseSessionServer, getBrowserbaseSessionMeta, withBrowserbaseConnectUrl,
  closeBrowserbaseSessionServer, findServerSecrets,
} from '../lib/attendance/browserbase-session-server.ts';

let pass = 0, fail = 0; const failures = [];
function assert(n, c) { if (c) { pass++; console.log(`  ✓ ${n}`); } else { fail++; failures.push(n); console.log(`  ✗ ${n}`); } }

const env = { BROWSERBASE_API_KEY: 'k', BROWSERBASE_PROJECT_ID: 'p' };
const raw = { id: 'sess_1', status: 'RUNNING', region: 'us', expiresAt: '2026-06-30T00:00:00Z', connectUrl: 'wss://x?apiKey=SECRET', signingKey: 'SIGN' };
const transport = { create: async () => raw, get: async () => raw, close: async () => ({}) };

console.log('== 43P-FINAL-2 — Browserbase Session Server ==\n');

// [1] create devolve só metadados (sem connectUrl/signingKey).
{
  const meta = await createBrowserbaseSessionServer(env, transport);
  assert('create → session_id', meta.session_id === 'sess_1');
  assert('create NÃO expõe connectUrl/signingKey', !JSON.stringify(meta).includes('SECRET') && !JSON.stringify(meta).includes('SIGN') && !('connectUrl' in meta));
}

// [2] env ausente bloqueia create.
{
  let threw = false; try { await createBrowserbaseSessionServer({}, transport); } catch { threw = true; }
  assert('create sem env lança', threw === true);
}

// [3] getMeta sanitizado.
{
  const meta = await getBrowserbaseSessionMeta('sess_1', env, transport);
  assert('getMeta → status', meta.status === 'RUNNING');
  assert('getMeta sem segredo', findServerSecrets(meta).length === 0);
}

// [4] withConnectUrl passa connectUrl ao callback (em memória) e NÃO retorna segredo.
{
  let seen = null;
  const r = await withBrowserbaseConnectUrl('sess_1', env, async (connectUrl) => { seen = connectUrl; return { storage_ref: 'vault://ref/1', host: 'portal.x' }; }, transport);
  assert('callback recebeu connectUrl', typeof seen === 'string' && seen.includes('wss://'));
  assert('resultado ok', r.ok === true && r.result?.storage_ref === 'vault://ref/1');
  assert('resultado sem connectUrl', !JSON.stringify(r).includes('SECRET'));
}

// [5] withConnectUrl BLOQUEIA se o callback tentar retornar segredo.
{
  const r = await withBrowserbaseConnectUrl('sess_1', env, async () => ({ cookie: 'x', connectUrl: 'wss://leak' }), transport);
  assert('callback com segredo → bloqueado', r.ok === false && r.reason === 'secret_leak_blocked' && r.result === null);
}

// [6] connectUrl ausente → fail closed.
{
  const t2 = { ...transport, get: async () => ({ id: 'sess_1', status: 'RUNNING' }) };
  const r = await withBrowserbaseConnectUrl('sess_1', env, async () => ({ ok: true }), t2);
  assert('sem connectUrl → connect_url_unavailable', r.ok === false && r.reason === 'connect_url_unavailable');
}

// [7] close.
{
  const r = await closeBrowserbaseSessionServer('sess_1', env, transport);
  assert('close ok', r.closed === true);
  assert('findServerSecrets detecta connectUrl', findServerSecrets({ a: { connectUrl: 'x' } }).length > 0);
}

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f}`); process.exit(1); }
process.exit(0);
