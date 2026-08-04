#!/usr/bin/env node
/**
 * O GUARDA DA LISTA DE ESTADOS DO ACIONAMENTO — Python ↔ TypeScript.
 *
 * `lib/attendance/dispatch-states.ts` é um ESPELHO de
 * `backend/app/services/insurer_dispatch_service.py`. Espelho não avisa quando
 * o original muda: 📊 em 03/08/2026 o backend ganhou `encaminhado` e
 * `resolvido` — os dois desfechos de SUCESSO do produto — e o TypeScript
 * inteiro seguiu sem conhecê-los. O preço (auditoria de 04/08) foi uma tela que
 * mentia: caso encerrado com sucesso exibido como "Conversando com a seguradora
 * agora", contado como trabalho em andamento, e fora do filtro "Concluídos".
 *
 * Este teste lê o PYTHON — o arquivo de verdade, não uma cópia dele — e compara
 * com o TypeScript. O dia em que o backend criar um estado que o front não
 * conhece, ele fica vermelho ANTES de a tela mentir.
 *
 * ⚠ Ele NÃO roda no CI: 📊 `.github/workflows/gate.yml` executa dois passos e
 * nenhum `.mjs`. Rode `npm run test:atendimento-estados` antes de mexer na
 * máquina de estados. (Mudar o gate é decisão do Founder — CLAUDE.md §10.)
 */
import { createRequire } from 'node:module';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const require = createRequire(import.meta.url);
const RAIZ = join(dirname(fileURLToPath(import.meta.url)), '..');

const PY = 'backend/app/services/insurer_dispatch_service.py';
const TS = 'lib/attendance/dispatch-states.ts';

/**
 * O node não carrega TypeScript direto — 📊 `scripts/agent-health.test.mjs` já
 * morreu no import por isso, antes da primeira asserção. Transpilar com a API
 * do próprio `typescript` (que já é dependência) executa o módulo DE VERDADE,
 * e não uma tradução dele feita à mão.
 */
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

// Comentários fora antes de qualquer coisa: o que sobra é só declaração, e um
// parêntese dentro de um comentário deixa de poder fechar uma tupla cedo demais.
const fontePy = readFileSync(join(RAIZ, PY), 'utf8').replace(/#[^\n]*/g, '');

function bloco(declaracao, abre, fecha) {
  const i = fontePy.indexOf(declaracao);
  if (i < 0) return null;
  const ini = fontePy.indexOf(abre, i);
  const fim = fontePy.indexOf(fecha, ini);
  if (ini < 0 || fim < 0) return null;
  return fontePy.slice(ini + 1, fim);
}

/** Uma tupla/lista Python de strings, na ordem em que está escrita. */
function tuplaPy(declaracao) {
  const b = bloco(declaracao, '(', ')');
  return b === null ? null : [...b.matchAll(/["']([a-z_]+)["']/g)].map((m) => m[1]);
}

/** As CHAVES de um dict Python (o `"x":` — nunca o valor). */
function chavesPy(declaracao) {
  const b = bloco(declaracao, '{', '}');
  return b === null ? null : [...b.matchAll(/["']([a-z_]+)["']\s*:/g)].map((m) => m[1]);
}

let pass = 0, fail = 0; const failures = [];
function assert(n, c, detalhe) {
  if (c) { pass++; console.log(`  ok   ${n}`); return; }
  fail++; failures.push(n);
  console.log(`  X    ${n}${detalhe ? `\n         ${detalhe}` : ''}`);
}

const diff = (a, b) => a.filter((x) => !b.includes(x));
const mesmoConjunto = (a, b) => diff(a, b).length === 0 && diff(b, a).length === 0;
const explica = (a, b) => {
  const faltando = diff(a, b), sobrando = diff(b, a);
  return [
    faltando.length ? `só no Python: ${faltando.join(', ')}` : '',
    sobrando.length ? `só no TypeScript: ${sobrando.join(', ')}` : '',
  ].filter(Boolean).join(' · ') || `mesma lista, ORDEM diferente:\n         py: ${a.join(', ')}\n         ts: ${b.join(', ')}`;
};

console.log('== Estados do acionamento — o Python e o TypeScript dizem a mesma coisa? ==\n');

const {
  DISPATCH_STATES,
  DISPATCH_STATES_ENCERRADOS,
  STAGE_BY_DISPATCH_STATE,
  DISPATCH_STATE_META,
  ATTENDANCE_STAGES,
  STAGE_META,
  stageFromDispatchState,
  dispatchStateMeta,
  isDispatchStateEncerrado,
} = carregarTS(TS);

const estadosPy = tuplaPy('DISPATCH_STATES =');
const encerradasPy = tuplaPy('FASES_ENCERRADAS =');
const emVooPy = tuplaPy('FASES_EM_VOO =');

// Um guarda que passa quando não consegue ler a fonte não guarda nada: se a
// declaração mudar de forma, isto tem que ficar VERMELHO, não verde.
console.log('-- a fonte foi mesmo lida --');
assert(`${PY}: DISPATCH_STATES encontrada`, Array.isArray(estadosPy) && estadosPy.length > 0);
assert(`${PY}: FASES_ENCERRADAS encontrada`, Array.isArray(encerradasPy) && encerradasPy.length > 0);
assert(`${PY}: FASES_EM_VOO encontrada`, Array.isArray(emVooPy) && emVooPy.length > 0);
assert(`${TS}: DISPATCH_STATES exportada`, Array.isArray(DISPATCH_STATES) && DISPATCH_STATES.length > 0);
if (fail > 0) {
  console.log('\nNão dá para comparar o que não foi lido. Corrija o parser ou a declaração.');
  process.exit(1);
}

const estadosTs = [...DISPATCH_STATES];

console.log('\n-- a lista, estado por estado --');
assert('mesmo CONJUNTO de estados', mesmoConjunto(estadosPy, estadosTs), explica(estadosPy, estadosTs));
assert('mesma ORDEM (o TS diz ser espelho literal da máquina)',
  estadosPy.join('|') === estadosTs.join('|'), explica(estadosPy, estadosTs));

console.log('\n-- os encerrados --');
assert('FASES_ENCERRADAS == DISPATCH_STATES_ENCERRADOS',
  mesmoConjunto(encerradasPy, [...DISPATCH_STATES_ENCERRADOS]),
  explica(encerradasPy, [...DISPATCH_STATES_ENCERRADOS]));
assert('em voo + encerradas cobrem a lista inteira (nenhum estado órfão no Python)',
  mesmoConjunto([...emVooPy, ...encerradasPy], estadosPy),
  explica(estadosPy, [...emVooPy, ...encerradasPy]));

// O defeito que originou tudo isto, dito como asserção: o backend considera o
// trabalho ACABADO e a tela mostra "acionando".
for (const e of encerradasPy) {
  const stage = stageFromDispatchState(e);
  assert(`encerrado '${e}' NÃO aparece como trabalho em voo`,
    stage === 'concluido' || stage === 'precisa_de_voce',
    `estágio na tela: '${stage}'`);
  assert(`encerrado '${e}' é reconhecido por isDispatchStateEncerrado`, isDispatchStateEncerrado(e));
}
for (const e of emVooPy) {
  assert(`em voo '${e}' NÃO aparece como concluído`, stageFromDispatchState(e) !== 'concluido');
}

console.log('\n-- nenhum estado cai no fallback (o cinza silencioso) --');
// `dispatchStateMeta` devolve "Acionando" para o que não conhece. Era assim que
// um caso `encaminhado` era descrito ao corretor como conversa em andamento.
for (const e of estadosPy) {
  const meta = dispatchStateMeta(e);
  assert(`'${e}' tem rótulo próprio (não o fallback)`,
    Boolean(DISPATCH_STATE_META[e]) && meta.label === DISPATCH_STATE_META[e].label,
    `label devolvido: '${meta.label}'`);
  assert(`'${e}' tem estágio declarado`, Boolean(STAGE_BY_DISPATCH_STATE[e]));
  assert(`o estágio de '${e}' existe em ATTENDANCE_STAGES`,
    ATTENDANCE_STAGES.includes(STAGE_BY_DISPATCH_STATE[e]));
}
for (const s of ATTENDANCE_STAGES) {
  assert(`estágio '${s}' tem rótulo em STAGE_META`, Boolean(STAGE_META[s]));
}

console.log('\n-- os mapas do próprio Python cobrem a lista --');
// 📊 Foi exatamente isto que faltou em 03/08: `resolvido` nasceu fora de
// `STATUS_WORK_RUN_POR_FASE` e o Work Run do caso nunca fechava.
for (const [nome, chaves] of [
  ['STATUS_WORK_RUN_POR_FASE', chavesPy('STATUS_WORK_RUN_POR_FASE')],
  ['_ORDEM_DAS_FASES', chavesPy('_ORDEM_DAS_FASES')],
]) {
  assert(`${nome} foi lido`, Array.isArray(chaves) && chaves.length > 0);
  if (Array.isArray(chaves)) {
    assert(`${nome} cobre todos os estados`, diff(estadosPy, chaves).length === 0,
      `sem entrada: ${diff(estadosPy, chaves).join(', ')}`);
  }
}

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) {
  for (const f of failures) console.log(`  - ${f}`);
  console.log(`\nA lista canônica é ${PY}. Ajuste ${TS} para espelhá-la —`);
  console.log('e lembre que os mapas do TS são exaustivos por tipo: dar rótulo,');
  console.log('estágio e tom ao estado novo faz parte de acrescentá-lo.');
  process.exit(1);
}
process.exit(0);
