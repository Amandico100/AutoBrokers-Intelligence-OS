#!/usr/bin/env node
/** Dados Globais — contatos globais de seguradoras (offline, puro). */
import {
  INSURER_CONTACTS_GLOBAL_SEED, getInsurerContactsGlobal, getInsurerContact,
  parsePrimaryNumber, resolveInsurerDispatchTarget, getSharedServiceProviderPortals, normalizeInsurerKey,
} from '../lib/attendance/insurer-contacts-global-seed.ts';

let pass = 0, fail = 0; const failures = [];
function assert(n, c) { if (c) { pass++; console.log(`  ✓ ${n}`); } else { fail++; failures.push(n); console.log(`  ✗ ${n}`); } }

console.log('== Dados Globais — Insurer Contacts ==\n');

// [1] seed completo (13 seguradoras da planilha) e ativo/global.
assert('12 seguradoras no seed', INSURER_CONTACTS_GLOBAL_SEED.length === 12);
{
  const all = getInsurerContactsGlobal();
  assert('todos global + ativo', all.every((c) => c.scope === 'global' && c.is_active === true));
  assert('todos com 6 canais', all.every((c) => c.channels.length === 6));
}

// [2] parser de número principal (sem menu).
assert('menu " - " removido (40901110)', parsePrimaryNumber('40901110 - 1-1-2').primary_digits === '40901110');
assert('menu marca has_menu', parsePrimaryNumber('40901110 - 1-1-2').has_menu === true);
assert('compacto 40042757-2-1 → 40042757', parsePrimaryNumber('40042757-2-1').primary_digits === '40042757');
assert('compacto 08007270800-1-4 → 08007270800', parsePrimaryNumber('08007270800-1-4').primary_digits === '08007270800');
assert('cpf marcador 08007030203', parsePrimaryNumber('08007030203 - cpf + 2').primary_digits === '08007030203');
assert('whatsapp 11 4090-1444 preservado', parsePrimaryNumber('11 4090-1444').primary_digits === '1140901444');
assert('whatsapp 11 95302-2395 preservado', parsePrimaryNumber('11 95302-2395').primary_digits === '11953022395');
assert('0800 025 6303 → 08000256303', parsePrimaryNumber('0800 025 6303').primary_digits === '08000256303');
assert('08007754545-0 → 08007754545', parsePrimaryNumber('08007754545-0').primary_digits === '08007754545');
assert('"não tem" → indisponível', parsePrimaryNumber('não tem').available === false);

// [3] getInsurerContact + normalização de chave.
assert('Allianz por chave', getInsurerContact('allianz')?.display_name === 'Allianz');
assert('normaliza acento (Itaú→itau)', normalizeInsurerKey('Itaú') === 'itau');
assert('youse sem whatsapp', getInsurerContact('youse')?.channels.find((c) => c.channel === 'assistencia_whatsapp')?.available === false);

// [4] resolver de despacho por serviço.
{
  const r = resolveInsurerDispatchTarget('allianz', 'residential_assistance');
  assert('residencial Allianz → whatsapp assistência', r.ok && r.channel === 'assistencia_whatsapp' && r.kind === 'whatsapp' && r.primary_digits === '1140901444' && r.source === 'global');
  const e = resolveInsurerDispatchTarget('allianz', 'electrician');
  assert('eletricista → mesmo destino residencial', e.ok && e.channel === 'assistencia_whatsapp');
  const y = resolveInsurerDispatchTarget('youse', 'residential_assistance');
  assert('youse sem whatsapp → fallback 24h RE', y.ok && y.channel === 'assistencia_24h_re' && y.primary_digits === '30035770');
  const ov = resolveInsurerDispatchTarget('allianz', 'residential_assistance', { channel: 'assistencia_whatsapp', kind: 'whatsapp', raw: '11 0000-0000', primary_digits: '1100000000', has_menu: false, available: true });
  assert('override de tenant tem precedência', ov.source === 'tenant_override' && ov.primary_digits === '1100000000');
  const nf = resolveInsurerDispatchTarget('seguradora_inexistente', 'residential_assistance');
  assert('seguradora inexistente → not found', nf.ok === false && nf.reason === 'insurer_not_found');
}

// [5] portal de prestador compartilhado (abraseuatendimento serve várias).
{
  const shared = getSharedServiceProviderPortals();
  const abrase = shared.find((s) => s.portal_url.includes('abraseuatendimento'));
  assert('abraseuatendimento é compartilhado entre várias seguradoras', Boolean(abrase) && abrase.shared === true && abrase.insurers.length > 1);
}

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f}`); process.exit(1); }
process.exit(0);
