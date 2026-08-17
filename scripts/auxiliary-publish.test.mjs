#!/usr/bin/env node
/** SPEC-013 B1 — publish guard + lifecycle de Auxiliar (puro, offline). */
import {
  canPublishAgentAsGlobalAuxiliary, publishBlockReason,
  nextTenantAuxStatus, tenantAuxStatusLabel, TENANT_AUX_STATES,
} from '../lib/admin/auxiliary-publish.ts';

let pass = 0, fail = 0; const failures = [];
function assert(n, c) { if (c) { pass++; console.log(`  ✓ ${n}`); } else { fail++; failures.push(n); console.log(`  ✗ ${n}`); } }

console.log('== SPEC-013 B1 — auxiliary publish/lifecycle ==\n');

// publish guard
assert('global_auxiliary do Studio publica', canPublishAgentAsGlobalAuxiliary({ companyKind: 'platform_blueprint_studio', studioSourceKind: 'global_auxiliary' }) === true);
assert('Core (global_core) NÃO publica', canPublishAgentAsGlobalAuxiliary({ companyKind: 'platform_blueprint_studio', studioSourceKind: 'global_core' }) === false);
assert('Even (global_attendance) NÃO publica', canPublishAgentAsGlobalAuxiliary({ companyKind: 'platform_blueprint_studio', studioSourceKind: 'global_attendance' }) === false);
assert('subagent NÃO publica', canPublishAgentAsGlobalAuxiliary({ companyKind: 'platform_blueprint_studio', studioSourceKind: 'source_subagent' }) === false);
assert('empresa cliente NÃO publica como global', canPublishAgentAsGlobalAuxiliary({ companyKind: 'client', studioSourceKind: 'global_auxiliary' }) === false);

assert('motivo: fora do Studio', publishBlockReason({ companyKind: 'client', studioSourceKind: 'global_auxiliary' }) === 'fonte_precisa_ser_studio');
assert('motivo: core/even', publishBlockReason({ companyKind: 'platform_blueprint_studio', studioSourceKind: 'global_core' }) === 'core_ou_even_nao_publicavel');
assert('motivo: subagent', publishBlockReason({ companyKind: 'platform_blueprint_studio', studioSourceKind: 'source_subagent' }) === 'subagent_nao_publicavel');
assert('motivo: ok = null', publishBlockReason({ companyKind: 'platform_blueprint_studio', studioSourceKind: 'global_auxiliary' }) === null);

// lifecycle
//
// 🔴 REESCRITO EM 17/08/2026. Este bloco guardava uma verdade VENCIDA e por
// isso não pegou o defeito que o Founder encontrou na tela.
//
// 📊 O que aconteceu: o botão "Ligar este Auxiliar" devolveu `acao_invalida`
// numa Cobrança Feita `inactive`. A regra antiga dizia "resume só de `paused`"
// — e o teste AFIRMAVA isso, em voz alta, como se fosse a coisa certa. A
// palavra `inactive` não aparecia em nenhuma das duas.
//
// A causa é a divergência de vocabulário: estas funções falavam a língua do
// TypeScript (`awaiting_runtime`, `uninstalled`) e o banco fala outra
// (`inactive`, `paused`, `archived`). A escrita já era traduzida por
// `statusValidoNoBanco()`; a LEITURA não era.
//
// CLAUDE.md §9.3: quando o fato muda, o teste muda com ele, e a lição migra.
// O que este bloco protege continua sendo o mesmo — que ação inválida devolva
// null — só que agora na língua certa, e com o caso que faltava.

assert('5 estados (a lingua do CHECK do banco)', TENANT_AUX_STATES.length === 5);
assert('os 5 sao os do banco',
  JSON.stringify([...TENANT_AUX_STATES].sort())
  === JSON.stringify(['active', 'archived', 'disabled', 'inactive', 'paused']));

// 🔴 O CASO QUE FALTAVA — e que quebrou na mão do Founder.
assert('inactive -> resume LIGA (era `acao_invalida`)',
  nextTenantAuxStatus('inactive', 'resume') === 'active');
assert('disabled -> resume LIGA (alguem olhou e liberou)',
  nextTenantAuxStatus('disabled', 'resume') === 'active');
assert('paused -> resume LIGA', nextTenantAuxStatus('paused', 'resume') === 'active');

assert('active -> pause PAUSA', nextTenantAuxStatus('active', 'pause') === 'paused');
assert('uninstall arquiva', nextTenantAuxStatus('active', 'uninstall') === 'archived');
assert('paused -> uninstall arquiva', nextTenantAuxStatus('paused', 'uninstall') === 'archived');

// CONTROLE: a funcao CONSEGUE recusar. Sem estas, uma funcao que devolvesse
// 'active' para tudo passaria em todas as assercoes acima.
assert('CONTROLE: ligar o que ja esta ligado e invalido',
  nextTenantAuxStatus('active', 'resume') === null);
assert('CONTROLE: pausar o que nao esta trabalhando e invalido',
  nextTenantAuxStatus('inactive', 'pause') === null);
assert('CONTROLE: arquivado nao pausa, nao liga, nao arquiva de novo',
  nextTenantAuxStatus('archived', 'pause') === null
  && nextTenantAuxStatus('archived', 'resume') === null
  && nextTenantAuxStatus('archived', 'uninstall') === null);

// Os termos antigos continuam entrando — chamador legado nao quebra.
assert('termo antigo `awaiting_runtime` e traduzido e LIGA',
  nextTenantAuxStatus('awaiting_runtime', 'resume') === 'active');
assert('termo antigo `uninstalled` e arquivado: nao aceita mais acao',
  nextTenantAuxStatus('uninstalled', 'resume') === null);
assert('status desconhecido nunca vira active sozinho',
  nextTenantAuxStatus('coisa_que_ninguem_previu', 'pause') === null);

assert('label honesto', tenantAuxStatusLabel('inactive') === 'Instalado, desligado'
  && tenantAuxStatusLabel('active') === 'Pronto'
  && tenantAuxStatusLabel('awaiting_runtime') === 'Instalado, desligado');

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f}`); process.exit(1); }
process.exit(0);
