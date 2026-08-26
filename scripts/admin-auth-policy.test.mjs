#!/usr/bin/env node
/** TA2-B — políticas de autorização puras (offline). */
import { canWriteTenantConfig, isPlatformMaster, canAdminReadCompany, canProvisionTenant, sameOriginOk, tenantCompanyConsistent, canToggleAttendanceAgent, decidirPatchDeAgente } from '../lib/admin/admin-auth-policy.ts';

let pass = 0, fail = 0; const failures = [];
function assert(n, c) { if (c) { pass++; console.log(`  ✓ ${n}`); } else { fail++; failures.push(n); console.log(`  ✗ ${n}`); } }

console.log('== TA2-B — admin auth policy ==\n');

// master de plataforma = master_admin SEM company
assert('master sem company é master', isPlatformMaster({ role: 'master_admin', companyId: null }) === true);
assert('master COM company NÃO é master de plataforma', isPlatformMaster({ role: 'master_admin', companyId: 'c1' }) === false);
assert('company_admin não é master', isPlatformMaster({ role: 'company_admin', companyId: 'c1' }) === false);

// escrita tenant
assert('owner escreve', canWriteTenantConfig({ role: null, isOwner: true }) === true);
assert('admin_company escreve', canWriteTenantConfig({ role: 'admin_company', isOwner: false }) === true);
assert('role comum NÃO escreve', canWriteTenantConfig({ role: 'member', isOwner: false }) === false);
assert('sem role/sem owner NÃO escreve', canWriteTenantConfig({ role: null, isOwner: false }) === false);

// leitura admin de empresa
assert('master lê qualquer empresa', canAdminReadCompany({ role: 'master_admin', sessionCompanyId: null, targetCompanyId: 'c9' }) === true);
assert('company_admin lê a PRÓPRIA', canAdminReadCompany({ role: 'company_admin', sessionCompanyId: 'c1', targetCompanyId: 'c1' }) === true);
assert('company_admin NÃO lê outra empresa', canAdminReadCompany({ role: 'company_admin', sessionCompanyId: 'c1', targetCompanyId: 'c2' }) === false);
assert('sessão sem papel NÃO lê', canAdminReadCompany({ role: null, sessionCompanyId: null, targetCompanyId: 'c1' }) === false);

// provisionamento só master
assert('só master provisiona', canProvisionTenant({ role: 'master_admin', companyId: null }) === true);
assert('company_admin NÃO provisiona', canProvisionTenant({ role: 'company_admin', companyId: 'c1' }) === false);

// [TA2-C] same-origin + consistência sessão×banco
console.log('\n[TA2-C] same-origin + consistência');
assert('sameOrigin: sem origin permite (defesa em profundidade)', sameOriginOk({ origin: null, host: 'app.com' }) === true);
assert('sameOrigin: host igual permite', sameOriginOk({ origin: 'https://app.com', host: 'app.com' }) === true);
assert('sameOrigin: host diferente bloqueia', sameOriginOk({ origin: 'https://evil.com', host: 'app.com' }) === false);
assert('sameOrigin: origin inválido bloqueia', sameOriginOk({ origin: 'not-a-url', host: 'app.com' }) === false);
assert('consistência: banco sem empresa bloqueia', tenantCompanyConsistent({ sessionCompanyId: 'c1', dbCompanyId: null }) === false);
assert('consistência: sessão sem empresa usa o banco', tenantCompanyConsistent({ sessionCompanyId: null, dbCompanyId: 'c1' }) === true);
assert('consistência: divergência bloqueia', tenantCompanyConsistent({ sessionCompanyId: 'c2', dbCompanyId: 'c1' }) === false);
assert('consistência: iguais ok', tenantCompanyConsistent({ sessionCompanyId: 'c1', dbCompanyId: 'c1' }) === true);


// ===========================================================================
// SPEC-093 BLOCO A — o papel `attendant`, e o portao POR CAMPO
// ===========================================================================
//
// 📊 O problema medido em 25/08/2026: `company_members` tem 8 admin_company e
// 2 member. O botao exige TENANT_WRITE_ROLES, entao `member` recebe 403 — e dar
// `admin_company` as duas abriria prompt, integracoes e billing junto.
//
// 🔴 As duas ULTIMAS asserceos sao LINHAS DE CONTROLE, e sao obrigatorias:
// sem elas, um bug que libere geral passa como sucesso (CLAUDE.md §9.3).

console.log('\n== SPEC-093 BLOCO A — o papel attendant ==\n');

const ATT = { role: 'attendant', isOwner: false };
const MEM = { role: 'member', isOwner: false };
const ADM = { role: 'admin_company', isOwner: false };

// o papel, isolado
assert('attendant PODE alternar atendimento', canToggleAttendanceAgent(ATT) === true);
assert('member NAO pode alternar', canToggleAttendanceAgent(MEM) === false);
assert('admin_company continua podendo alternar', canToggleAttendanceAgent(ADM) === true);
assert('attendant NAO escreve configuracao', canWriteTenantConfig(ATT) === false);

const decidir = (quem, agentRole, campos) =>
  decidirPatchDeAgente({ ...quem, agentRole, camposDoCorpo: campos });

// ① attendant alterna is_active -> permitido, e a acao e' toggle
assert('① attendant alterna is_active do ATENDIMENTO',
  decidir(ATT, 'attendance', ['is_active']).permitido === true);
assert('① e a acao e TOGGLE, nao config',
  decidir(ATT, 'attendance', ['is_active']).acao === 'toggle');

// ② attendant tenta QUALQUER outro campo -> 403
assert('② attendant NAO muda variables',
  decidir(ATT, 'attendance', ['variables']).permitido === false);
assert('② attendant NAO muda overrides',
  decidir(ATT, 'attendance', ['overrides']).permitido === false);
assert('② 🔴 corpo MISTO nao passa por baixo',
  decidir(ATT, 'attendance', ['is_active', 'variables']).permitido === false);
assert('② corpo VAZIO nao vira toggle',
  decidir(ATT, 'attendance', []).permitido === false);

// ②b — a condicao que a SPEC nao escreve: o agente CENTRAL nao e' dele
assert('②b 🔴 attendant NAO alterna o agente CORE',
  decidir(ATT, 'core', ['is_active']).permitido === false);

// ③ attendant de OUTRA corretora: a rota resolve a empresa pela SESSAO, nunca
//    pelo corpo — nao existe campo de empresa para forjar. A prova esta' no
//    guarda pytest que le a rota.

// ④ LINHA DE CONTROLE — member continua 403 no toggle
assert('④ CONTROLE: member continua 403 no toggle',
  decidir(MEM, 'attendance', ['is_active']).permitido === false);

// ⑤ LINHA DE CONTROLE — admin_company continua podendo TUDO
assert('⑤ CONTROLE: admin_company alterna',
  decidir(ADM, 'attendance', ['is_active']).permitido === true);
assert('⑤ CONTROLE: admin_company muda variables',
  decidir(ADM, 'attendance', ['variables']).permitido === true);
assert('⑤ CONTROLE: admin_company alterna o CORE',
  decidir(ADM, 'core', ['is_active']).permitido === true);
assert('⑤ CONTROLE: admin_company com corpo MISTO continua passando',
  decidir(ADM, 'attendance', ['is_active', 'variables']).permitido === true);

// e o dono, que nao tem papel nenhum
assert('owner sem papel alterna', decidir({ role: null, isOwner: true }, 'attendance', ['is_active']).permitido === true);

// ===========================================================================
// 🔴 OS DOIS ACHADOS DO PAINEL — e sao de PRODUTO, nao de estilo
// ===========================================================================

// (i) O `attendant` NAO PODE ESCREVER CONFIGURACAO — nem de tabela.
//
// ⚠️ O toggle dispara `ativarTodosOsCorredores`, que escreve
// `corridor_templates` e `tenant_corridors`. A rota dedicada a essa escrita
// exige `write: true`. Sem `escreveConfiguracao`, o papel criado para NAO abrir
// a configuracao instalaria 14 corredores em nome da corretora.
assert('🔴 attendant alterna mas NAO escreve configuracao',
  decidir(ATT, 'attendance', ['is_active']).escreveConfiguracao === false);
assert('🔴 CONTROLE: admin_company alterna E escreve configuracao',
  decidir(ADM, 'attendance', ['is_active']).escreveConfiguracao === true);
assert('🔴 CONTROLE: o dono tambem escreve configuracao',
  decidir({ role: null, isOwner: true }, 'attendance', ['is_active']).escreveConfiguracao === true);

// (ii) CORPO MISTO NAO ENGOLE O TOGGLE EM SILENCIO.
//
// ⚠️ Antes desta SPEC, `{is_active:false, variables:{}}` DESLIGAVA o agente (e
// descartava as variaveis). A primeira versao mandava tudo para o ramo `config`
// -- as variaveis eram aplicadas e o desligamento sumia com 200 OK. Quem clicou
// "desligar" lia sucesso e o robo continuava respondendo segurado.
const misto = decidir(ADM, 'attendance', ['is_active', 'variables']);
assert('🔴 corpo MISTO: a acao e config', misto.acao === 'config');
assert('🔴 corpo MISTO: mas o toggle TAMBEM acontece', misto.tambemAlterna === true);
assert('corpo so de config NAO alterna',
  decidir(ADM, 'attendance', ['variables']).tambemAlterna === false);
assert('corpo VAZIO nao alterna',
  decidir(ADM, 'attendance', []).tambemAlterna === false);
assert('CONTROLE: corpo so de toggle alterna',
  decidir(ADM, 'attendance', ['is_active']).tambemAlterna === true);
// e quem nao pode nao alterna nem misturado
assert('attendant com corpo MISTO nao alterna nada',
  decidir(ATT, 'attendance', ['is_active', 'variables']).tambemAlterna === false);

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f}`); process.exit(1); }
process.exit(0);
