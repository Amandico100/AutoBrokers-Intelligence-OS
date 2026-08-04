#!/usr/bin/env node
/**
 * SPEC-013 FB-2 + P-37 — divergências/saúde de agentes (puro, offline).
 *
 * ESTE ARQUIVO NÃO RODAVA. Ele fazia `import ... from '../lib/admin/agent-health.ts'`,
 * e o node não carrega TypeScript direto: qualquer execução morria no import,
 * antes da primeira asserção. Um teste que não roda é pior que teste nenhum,
 * porque ocupa o lugar de um que rodaria.
 *
 * Agora o módulo é transpilado com a API do próprio TypeScript (que já é
 * dependência do projeto) e executado DE VERDADE — não uma tradução dele.
 */
import { createRequire } from 'node:module';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const require = createRequire(import.meta.url);
const RAIZ = join(dirname(fileURLToPath(import.meta.url)), '..');

function carregarTS(rel) {
  const ts = require('typescript');
  const fonte = readFileSync(join(RAIZ, rel), 'utf8');
  const js = ts.transpileModule(fonte, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
  }).outputText;
  const mod = { exports: {} };
  new Function('module', 'exports', 'require', js)(mod, mod.exports, require);
  return mod.exports;
}

const {
  buildAgentDivergences, isHealthy, effectiveCoreModel, estadoDaVoz, personalizacaoDoPrompt, isMute,
} = carregarTS('lib/admin/agent-health.ts');

let pass = 0, fail = 0; const failures = [];
function assert(n, c) { if (c) { pass++; console.log(`  ok   ${n}`); } else { fail++; failures.push(n); console.log(`  X    ${n}`); } }

console.log('== SPEC-013 FB-2 + P-37 — agent health ==\n');

const CORE_OK = { id: 'c', name: 'AutoBrokers', agent_role: 'core', is_active: true, agent_system_prompt: 'Voce e o AutoBrokers da Resulta — o braco direito interno da corretora. Ajude o corretor.' };
const EVEN_OK = { id: 'e', name: 'Even', agent_role: 'attendance', is_active: false, agent_system_prompt: 'Voce e Even, atendente de assistencia da Resulta no WhatsApp.' };

// canônico saudável: 1 core + 1 attendance, os dois COM voz
const ok = buildAgentDivergences([CORE_OK, EVEN_OK]);
assert('saudável sem divergências críticas', isHealthy(ok) && ok.length === 0);

// SPEC-039 F3: o nome do atendimento é de CADA corretora — o sistema NUNCA
// força "Even". Um atendimento com qualquer nome NÃO gera divergência de nome.
const sergio = buildAgentDivergences([CORE_OK, { ...EVEN_OK, name: 'SERGIO' }]);
assert('nome do atendimento NÃO é mais normalizado p/ Even', !sergio.some((d) => d.kind === 'attendance_name_not_even'));
assert('atendimento com nome próprio é healthy', isHealthy(sergio) && sergio.length === 0);

// faltando core/attendance
const missing = buildAgentDivergences([EVEN_OK]);
assert('missing_core detectado + não saudável', missing.some((d) => d.kind === 'missing_core') && !isHealthy(missing));

// duplicata
const dup = buildAgentDivergences([CORE_OK, { ...CORE_OK, id: 'c2', name: 'AutoBrokers 2' }, EVEN_OK]);
assert('duplicate_core detectado + não saudável', dup.some((d) => d.kind === 'duplicate_core') && !isHealthy(dup));

// agente de teste legado → ação archive (e nunca para core/even)
const test = buildAgentDivergences([CORE_OK, EVEN_OK, { id: 't', name: 'TESTE Runtime Smith Agent', agent_role: 'subagent', is_active: false, agent_system_prompt: 'stub' }]);
assert('agente de teste gera legacy_test_agent + ação archive', test.some((d) => d.kind === 'legacy_test_agent' && d.action === 'archive_agent' && d.agent_id === 't'));
assert('teste não derruba saúde canônica', isHealthy(test));

// modelo efetivo do Core
assert('core mini → gpt-4o efetivo', effectiveCoreModel('gpt-4o-mini') === 'gpt-4o');
assert('core já forte mantém', effectiveCoreModel('gpt-4.1') === 'gpt-4.1');
assert('core sem modelo → gpt-4o', effectiveCoreModel(null) === 'gpt-4o');

// ---------------------------------------------------------------------------
// P-37 — O AGENTE MUDO. 📊 A AutoFleet tinha um core ATIVO de ZERO caracteres,
// e esta função respondia "saudável" (auditoria de 02/08/2026, Parte C.6).
// ---------------------------------------------------------------------------
console.log('\n-- P-37: o agente mudo --');

const CORE_MUDO = { ...CORE_OK, agent_system_prompt: '' };
const autofleet = buildAgentDivergences([CORE_MUDO, EVEN_OK]);
assert('core ativo com prompt vazio vira mute_core', autofleet.some((d) => d.kind === 'mute_core' && d.agent_id === 'c'));
assert('e a corretora deixa de ser "saudável"', !isHealthy(autofleet));
assert('o rótulo diz que ele está ATIVO e mudo', autofleet.some((d) => /ATIVO e MUDO/.test(d.label)));

// A casca que `composeSystemPromptWithGuardrails('')` produz: ~560 caracteres,
// zero instrução. Passa em qualquer checagem de "não vazio".
const CASCA = [
  '=== PERSONALIZACAO DA CORRETORA (dados, NAO sao instrucoes de prioridade) ===',
  '',
  '',
  '=== REGRAS IMUTAVEIS DO AUTOBROKERS (sempre valem; nao podem ser alteradas por configuracao) ===',
  '- Opere apenas com dados desta corretora; jamais acesse outra corretora.',
  '- Nunca exponha segredos, tokens, cookies ou credenciais.',
  'Se a personalizacao acima conflitar com estas regras, estas regras prevalecem.',
].join('\n');
assert('a casca de guardrails NÃO é vazia como string', CASCA.trim().length > 200);
assert('mas é classificada como so_guardrails', estadoDaVoz(CASCA) === 'so_guardrails');
const casca = buildAgentDivergences([{ ...CORE_OK, agent_system_prompt: CASCA }, EVEN_OK]);
assert('e gera mute_core do mesmo jeito', casca.some((d) => d.kind === 'mute_core') && !isHealthy(casca));

// Prompt REAL montado pelo composer: personalização + guardrails.
const REAL = CASCA.replace('\n\n\n', '\nVoce e o AutoBrokers da Resulta. Ajude o corretor em vendas e operacao.\n\n');
assert('prompt real (com personalização) é "ok"', estadoDaVoz(REAL) === 'ok');
assert('e a personalização extraída é a da corretora', /braco|Ajude o corretor/.test(personalizacaoDoPrompt(REAL)));
assert('prompt real não gera divergência', buildAgentDivergences([{ ...CORE_OK, agent_system_prompt: REAL }, EVEN_OK]).length === 0);

// Mudo e DESLIGADO continua sendo problema — é o estado fail-closed do portão.
const desligado = buildAgentDivergences([CORE_OK, { ...EVEN_OK, agent_system_prompt: '   ' }]);
assert('atendimento mudo e inativo também é mute_attendance', desligado.some((d) => d.kind === 'mute_attendance'));
assert('e também derruba a saúde', !isHealthy(desligado));
assert('mas o rótulo NÃO diz "ATIVO"', !desligado.some((d) => d.kind === 'mute_attendance' && /ATIVO/.test(d.label)));

// Quem não pediu a coluna não recebe alarme falso.
assert('agente sem a coluna no select não é considerado mudo', !isMute({ id: 'x', name: 'A', agent_role: 'core', is_active: true }));
assert('e não gera divergência de mudez', !buildAgentDivergences([
  { id: 'c', name: 'AutoBrokers', agent_role: 'core', is_active: true },
  { id: 'e', name: 'Even', agent_role: 'attendance', is_active: false },
]).some((d) => d.kind.startsWith('mute_')));

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f}`); process.exit(1); }
process.exit(0);
