// ===========================================================================
// A SENHA DO MEMBRO DA EQUIPE — SPEC-133-A.1 (conserto, juiz P3-4, 10/10/2026)
// ===========================================================================
//
// 📊 O DEFEITO: o servidor aceitava "mudar123" (a antiga senha padrão, que qualquer um conhece) quando ela vinha no
// pedido — o mínimo era 6. E a senha que ele gerava (`senha_provisoria`) voltava na resposta e a tela a jogava fora.
//
// Este arquivo EXECUTA a regra real (`lib/admin/senha-do-membro.ts`, transpilada pelo `typescript`) e confere que a
// rota decide por ela no POST e no PATCH — não por uma cópia — e que a tela mostra a senha devolvida.
//
// ⛔ CONTROLE (CLAUDE.md §9.3): a regra ANTIGA (`length >= 6`) aceita "mudar123" — prova que o guarda consegue falhar.
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

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

let pass = 0, fail = 0;
function assert(nome, cond) {
  if (cond) { pass++; } else { fail++; console.log('  x ' + nome); }
}

const M = carregarTS('lib/admin/senha-do-membro.ts');
const recusa = M.recusaDaSenhaDoMembro;

// ① a antiga padrão nunca serve — em qualquer caixa, com espaço
for (const s of ['mudar123', 'MUDAR123', ' Mudar123 ', 'mudar 123']) assert(`"${s}" recusada`, recusa(s) !== null);
// ② curta, vazia, comprida
assert('9 caracteres recusada', recusa('abcdefgh9') !== null);
assert('vazia recusada', recusa('') !== null && recusa(undefined) !== null && recusa(null) !== null);
assert('257 recusada', recusa('x'.repeat(257)) !== null);
// ③ CONTROLE do lado de cá: as boas passam (o guarda não recusa tudo)
assert('10 caracteres aceita', recusa('abcdefgh10') === null);
assert('a gerada pela tela (12) aceita', recusa('Kp3xQ9mZt7Hw') === null);
assert('256 aceita', recusa('x'.repeat(256)) === null);
assert('"mudar1234567" (só começa igual) aceita', recusa('mudar1234567') === null);
// ④ CONTROLE §9.3: a regra antiga deixava passar o que a nova recusa
const regraAntiga = (s) => (String(s || '').length < 6 ? 'curta' : null);
assert('controle: a regra antiga aceitava "mudar123"', regraAntiga('mudar123') === null && recusa('mudar123') !== null);

// ⑤ a ROTA decide pela regra — no POST e no PATCH — e o mínimo antigo sumiu
const rota = readFileSync(join(RAIZ, 'app/api/dashboard/team/route.ts'), 'utf8');
assert('a rota importa a regra', /from '@\/lib\/admin\/senha-do-membro'/.test(rota));
const corpo = (nome) => rota.slice(rota.indexOf(`export async function ${nome}`)).split(/\nexport async function /)[0];
assert('POST usa a regra', /recusaDaSenhaDoMembro\(password\)/.test(corpo('POST')));
assert('PATCH usa a regra', /recusaDaSenhaDoMembro\(body\.password\)/.test(corpo('PATCH')));
assert('o mínimo 6 sumiu', !/length\s*<\s*6/.test(rota));
assert('a senha gerada no servidor passa da regra (randomBytes(12) base64url = 16)', /randomBytes\(12\)\.toString\('base64url'\)/.test(rota));

// ⑥ a TELA mostra a senha devolvida, uma vez, com o botão copiar
const tela = readFileSync(join(RAIZ, 'app/dashboard/personalizacao/equipe/TeamClient.tsx'), 'utf8');
assert('a tela lê senha_provisoria', /j\.senha_provisoria/.test(tela));
assert('a tela mostra a senha', /data-senha-provisoria/.test(tela) && /\{criada\.senha\}/.test(tela));
assert('a tela tem o botão copiar', /navigator\.clipboard\.writeText\(criada\.senha\)/.test(tela));
assert('a senha some ao fechar', /const close = \(\) => \{[^}]*setCriada\(null\)/.test(tela));
assert('nenhum console.* com senha', !/console\.\w+\([^)]*senha/i.test(tela) && !/console\.\w+\([^)]*password/i.test(rota));

console.log(`${pass} ok, ${fail} falha(s)`);
process.exit(fail ? 1 : 0);
