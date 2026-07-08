#!/usr/bin/env node
/** SPEC-023 P2 - dashboard HITL helpers (pure/offline). */
import {
  buildPortalJobRetryPatch,
  isRetryableHitlJob,
  sanitizePortalJob,
} from '../lib/portal/hitl.ts';

let pass = 0;
let fail = 0;
const failures = [];

function assert(name, cond, detail) {
  if (cond) {
    pass++;
    console.log(`  [ok] ${name}`);
  } else {
    fail++;
    failures.push([name, detail]);
    console.log(`  [X] ${name}${detail ? `: ${JSON.stringify(detail)}` : ''}`);
  }
}

console.log('== SPEC-023 P2 - Portal HITL dashboard helpers ==\n');

const row = {
  id: 'job-1',
  company_id: 'company-1',
  portal_key: 'allianz_corretor',
  journey: 'login_check',
  status: 'needs_human',
  params: { username: 'SHOULD_NOT_LEAK', password: 'SECRET' },
  evidence: {
    message: 'portal pediu CAPTCHA/2FA',
    url: 'https://www.allianznet.com.br/private/home',
    hitl: { required: true, kind: 'captcha_2fa', resume_mode: 'requeue_after_human' },
    debug_dom: '<input value="SECRET">',
  },
  screenshots: ['data:image/jpeg;base64,abc'],
  attempts: 2,
  created_at: '2026-07-08T00:00:00Z',
  started_at: '2026-07-08T00:01:00Z',
  finished_at: '2026-07-08T00:02:00Z',
  error: null,
};

const sanitized = sanitizePortalJob(row, { allianz_corretor: 'Allianz' });
assert('sanitize mantem id/status', sanitized.id === 'job-1' && sanitized.status === 'needs_human', sanitized);
assert('sanitize adiciona portal_name', sanitized.portal_name === 'Allianz', sanitized);
assert('sanitize mantem screenshot', sanitized.screenshot === 'data:image/jpeg;base64,abc', sanitized);
assert('sanitize expõe mensagem segura', sanitized.message === 'portal pediu CAPTCHA/2FA', sanitized);
assert('sanitize remove params', !JSON.stringify(sanitized).includes('SHOULD_NOT_LEAK'), sanitized);
assert('sanitize remove debug_dom', !JSON.stringify(sanitized).includes('debug_dom') && !JSON.stringify(sanitized).includes('SECRET'), sanitized);

assert('needs_human da mesma empresa pode retry', isRetryableHitlJob(row, 'company-1') === true);
assert('outra empresa nao pode retry', isRetryableHitlJob(row, 'company-2') === false);
assert('status done nao pode retry', isRetryableHitlJob({ ...row, status: 'done' }, 'company-1') === false);

const patch = buildPortalJobRetryPatch('2026-07-08T01:00:00Z', row.evidence);
assert('retry patch re-enfileira', patch.status === 'queued' && patch.error === null, patch);
assert('retry patch limpa tempos de execucao', patch.started_at === null && patch.finished_at === null, patch);
assert('retry patch registra requested_at no evidence', patch.evidence.hitl.retry_requested_at === '2026-07-08T01:00:00Z', patch);

console.log(`\n== ${pass} ok / ${fail} fail ==`);
if (fail > 0) {
  for (const [name, detail] of failures) console.log(`  FALHOU: ${name} ${detail ? JSON.stringify(detail) : ''}`);
  process.exit(1);
}
process.exit(0);
