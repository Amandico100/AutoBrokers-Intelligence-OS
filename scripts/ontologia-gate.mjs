#!/usr/bin/env node
/**
 * O caso da ontologia rodando em MODO GATE — SPEC-078 C.8.
 *
 * `npm run test:ontologia` é para a mesa do desenvolvedor: sem credencial de
 * banco, ele pula os casos que precisam do banco e sai verde. Isso é razoável
 * ali e **inaceitável num gate** — o gate ficaria verde por não ter rodado, que
 * é o pior verde que existe.
 *
 * Este script liga `ONTOLOGIA_EXIGE_BANCO=1`, que transforma "pulei" em
 * "falhei". 📊 Provado em 17/08/2026:
 *
 *     com a exigência, sem credencial  → rc=1
 *     sem a exigência (controle)       → rc=0
 *
 * O par é o que dá direito à conclusão: a flag muda o resultado, e sem ela o
 * fluxo do dia a dia continua igual.
 *
 * Existe como `.mjs` e não como variável inline no `package.json` porque
 * `VAR=1 comando` não funciona no `cmd.exe`, e o projeto não tem `cross-env`
 * (📊 conferido no `package.json`). Inventar dependência para exportar uma
 * variável seria caro demais para o problema.
 */
import { spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';

const ALVO = 'backend/tests/test_ontologia_e_unica.py';
if (!existsSync(ALVO)) {
  console.error(`[ontologia-gate] nao achei ${ALVO}`);
  process.exit(1);
}

// `python` no Windows, `python3` onde ele não existir. Tenta na ordem e usa o
// primeiro que responde — sem isso o gate falha por motivo errado (interpretador
// ausente parece defeito de ontologia no relatório).
const candidatos = process.platform === 'win32' ? ['python', 'python3'] : ['python3', 'python'];
let usado = null;
for (const bin of candidatos) {
  const probe = spawnSync(bin, ['--version'], { stdio: 'ignore' });
  if (!probe.error && probe.status === 0) { usado = bin; break; }
}
if (!usado) {
  console.error('[ontologia-gate] nenhum interpretador Python encontrado (python, python3)');
  process.exit(1);
}

const r = spawnSync(usado, [ALVO], {
  stdio: 'inherit',
  env: { ...process.env, ONTOLOGIA_EXIGE_BANCO: '1' },
});
process.exit(r.status === null ? 1 : r.status);
