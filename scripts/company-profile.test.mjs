#!/usr/bin/env node
/** TA2-C — perfil da corretora (puro, offline). */
import { validateCompanyProfile, isValidCNPJ, isValidEmail, isValidPhoneBR, COMPANY_PROFILE_FIELDS, BR_UF } from '../lib/admin/company-profile.ts';

let pass = 0, fail = 0; const failures = [];
function assert(n, c) { if (c) { pass++; console.log(`  ✓ ${n}`); } else { fail++; failures.push(n); console.log(`  ✗ ${n}`); } }

console.log('== TA2-C — company profile ==\n');

// CNPJ
assert('CNPJ válido aceito', isValidCNPJ('11444777000161') === true);
assert('CNPJ com máscara aceito', isValidCNPJ('11.444.777/0001-61') === true);
assert('CNPJ repetido rejeitado', isValidCNPJ('11111111111111') === false);
assert('CNPJ DV errado rejeitado', isValidCNPJ('11444777000160') === false);
assert('CNPJ curto rejeitado', isValidCNPJ('123') === false);

// email/phone
assert('email válido', isValidEmail('a@b.com') === true);
assert('email inválido', isValidEmail('a@b') === false);
assert('telefone BR válido', isValidPhoneBR('(11) 99999-8888') === true);
assert('telefone curto inválido', isValidPhoneBR('123') === false);

// UF dropdown
assert('UF é select com 27 estados', COMPANY_PROFILE_FIELDS.find((f) => f.key === 'state').input_kind === 'select' && BR_UF.length === 27);

// validação composta
const bad = validateCompanyProfile({ company_name: '', cnpj: '123', primary_contact_email: 'x', state: 'ZZ' });
assert('nome obrigatório vazio bloqueia', bad.ok === false && bad.errors.includes('company_name:obrigatorio'));
assert('cnpj inválido bloqueia', bad.errors.includes('cnpj:invalido'));
assert('email inválido bloqueia', bad.errors.includes('primary_contact_email:email_invalido'));
assert('UF fora da lista bloqueia', bad.errors.includes('state:opcao_invalida'));

const good = validateCompanyProfile({ company_name: 'Resulta Seguros', cnpj: '11.444.777/0001-61', primary_contact_email: 'op@resulta.com', primary_contact_phone: '11999998888', state: 'SP', city: 'São Paulo' });
assert('entrada válida passa', good.ok === true);
assert('CNPJ é normalizado para dígitos', good.clean.cnpj === '11444777000161');
assert('UF válida mantida', good.clean.state === 'SP');

// ignora campos não permitidos (plano/flags/credits)
const sneaky = validateCompanyProfile({ company_name: 'X', plan_type: 'premium', credits_limit: 999999, id: 'hack' });
assert('campos proibidos são ignorados', !('plan_type' in sneaky.clean) && !('credits_limit' in sneaky.clean) && !('id' in sneaky.clean));

// control chars removidos
const ctrl = validateCompanyProfile({ company_name: 'Res' + String.fromCharCode(0) + 'ulta' });
assert('control chars removidos do nome', ctrl.ok === true && ctrl.clean.company_name === 'Resulta');

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f}`); process.exit(1); }
process.exit(0);
