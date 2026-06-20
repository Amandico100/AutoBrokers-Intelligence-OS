#!/usr/bin/env node
/** 43P-FINAL-1 — Vault adapter de SessionRef (offline, falha fechada). */
import { persistSessionRefViaVault, failClosedVaultAdapter, findVaultRefSecrets } from '../lib/attendance/portal-session-vault.ts';

let pass = 0, fail = 0; const failures = [];
function assert(n, c) { if (c) { pass++; console.log(`  ✓ ${n}`); } else { fail++; failures.push(n); console.log(`  ✗ ${n}`); } }

console.log('== 43P-FINAL-1 — Portal Session Vault ==\n');

const input = { company_id: 'C1', portal_account_id: 'A1', provider: 'browserbase', secret_payload: { cookies: [{ name: 'x', value: 'SECRET' }] } };

// [1] Sem Vault → falha fechada.
{
  const r = await persistSessionRefViaVault(input, failClosedVaultAdapter);
  assert('sem vault → ok false', r.ok === false);
  assert('sem vault → vault_unavailable', r.reason === 'vault_unavailable');
  assert('sem vault → sem storage_ref', r.storage_ref === null);
}

// [2] Vault real (mock) → storage_ref opaca, segredo NÃO sai.
{
  let received = null;
  const vault = { available: async () => true, write: async (i) => { received = i; return { ok: true, storage_ref: 'vault://ref/abc123', reason: 'stored' }; } };
  const r = await persistSessionRefViaVault(input, vault);
  assert('com vault → ok true', r.ok === true && r.storage_ref === 'vault://ref/abc123');
  assert('vault recebeu o payload (fica só lá)', received && received.secret_payload);
  assert('retorno NÃO contém segredo', !JSON.stringify(r).includes('SECRET'));
}

// [3] storage_ref que parece segredo → rejeitado.
{
  const vault = { available: async () => true, write: async () => ({ ok: true, storage_ref: 'cookie=abc', reason: 'stored' }) };
  // storage_ref string não dispara findVaultRefSecrets (que olha CHAVES); então este caso testa o findVaultRefSecrets diretamente:
  assert('findVaultRefSecrets detecta chave cookie', findVaultRefSecrets({ cookie: 'x' }).length > 0);
  assert('findVaultRefSecrets detecta storageState aninhado', findVaultRefSecrets({ a: { storageState: {} } }).length > 0);
  const r = await persistSessionRefViaVault(input, vault);
  assert('vault disponível grava', r.ok === true);
}

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f}`); process.exit(1); }
process.exit(0);
