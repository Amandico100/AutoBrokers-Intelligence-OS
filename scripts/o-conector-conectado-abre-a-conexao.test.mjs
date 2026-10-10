// ===========================================================================
// O CONECTOR JÁ CONECTADO ABRE A CONEXÃO — SPEC-133-A.1 F3 (retorno do Founder, 10/10/2026)
// ===========================================================================
//
// 📊 O DEFEITO, MEDIDO NA TELA: "quando quero refazer e clico em InfoCap, se já estiver conectado, aparece para
// criar nova conexão… isso confunde". O clique do catálogo (`conectores/page.tsx`) só abria a existente com
// `status === 'connected'`; em `configuring` / `error` / `disconnected` / `draft` caía em `openCreate(t)` e
// gravava uma conexão NOVA ao lado.
//
// Este arquivo EXECUTA o módulo real (`lib/vault/conector-do-catalogo.ts`, transpilado pelo `typescript`) e
// confere que a PÁGINA decide por ele — e não por uma cópia da regra.
//
// ⛔ CONTROLE (CLAUDE.md §9.2/§9.3): a regra ANTIGA (só `connected` abre), aplicada aos mesmos casos, tem de
// dar "nova" para a InfoCap com erro — prova que o guarda consegue ficar vermelho.
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

const M = carregarTS('lib/vault/conector-do-catalogo.ts');
const INFOCAP = 'tpl-infocap', DRIVE = 'tpl-drive';
const c = (id, tpl, status, extra = {}) => ({ id, connector_template_id: tpl, status, created_at: '2026-10-01T00:00:00Z', ...extra });

// ① nenhuma conexão → "nova"
assert('sem conexão → nova', M.oQueOCatalogoAbre(INFOCAP, []).tipo === 'nova');
assert('lista nula → nova', M.oQueOCatalogoAbre(INFOCAP, null).tipo === 'nova');

// ② QUALQUER status não arquivado → abre a existente (o caso do Founder: "refazer")
for (const st of ['connected', 'configuring', 'error', 'disconnected', 'draft']) {
  const a = M.oQueOCatalogoAbre(INFOCAP, [c('x1', INFOCAP, st)]);
  assert(`InfoCap em ${st} → abre a existente`, a.tipo === 'abrir' && a.connectionId === 'x1');
}

// ③ arquivada não conta; conexão de OUTRO conector não conta
assert('arquivada → nova', M.oQueOCatalogoAbre(INFOCAP, [c('x1', INFOCAP, 'archived')]).tipo === 'nova');
assert('de outro conector → nova', M.oQueOCatalogoAbre(INFOCAP, [c('d1', DRIVE, 'connected')]).tipo === 'nova');

// ④ várias (legado de cliques antigos): abre a conectada, depois a configurada, depois a mais antiga
const varias = [
  c('rasc', INFOCAP, 'draft', { created_at: '2026-09-01T00:00:00Z' }),
  c('conf', INFOCAP, 'error', { technical_ref_id: 'ref', created_at: '2026-09-05T00:00:00Z' }),
  c('ok', INFOCAP, 'connected', { created_at: '2026-09-09T00:00:00Z' }),
];
const v = M.oQueOCatalogoAbre(INFOCAP, varias);
assert('várias → a conectada', v.tipo === 'abrir' && v.connectionId === 'ok' && v.total === 3);
assert('sem conectada → a configurada', M.oQueOCatalogoAbre(INFOCAP, varias.slice(0, 2)).connectionId === 'conf');

// ⑤ o texto do botão segue o MESMO critério do clique
assert('botão: existente conectada', M.rotuloDoCartao({ tipo: 'abrir', connectionId: 'x', total: 1 }, { conectada: true }) === 'Gerenciar conexão');
assert('botão: existente não conectada', M.rotuloDoCartao({ tipo: 'abrir', connectionId: 'x', total: 1 }, {}) === 'Abrir conexão');
assert('botão: nova InfoCap/OAuth', M.rotuloDoCartao({ tipo: 'nova' }, { conectaDeUmaVez: true }) === 'Conectar');
assert('botão: nova rascunho', M.rotuloDoCartao({ tipo: 'nova' }, {}) === 'Preparar conexão');

// ⑥ a PÁGINA decide pelo módulo — e a regra antiga sumiu
const pagina = readFileSync(join(RAIZ, 'app/dashboard/personalizacao/conectores/page.tsx'), 'utf8');
assert('página importa oQueOCatalogoAbre', /import \{[^}]*oQueOCatalogoAbre[^}]*\} from '@\/lib\/vault\/conector-do-catalogo'/.test(pagina));
assert('página abre a existente antes de qualquer "nova"', /acao\.tipo === 'abrir'\) \{ abrirExistente\(acao\.connectionId\)/.test(pagina));
assert('a regra antiga (só connected abre) saiu', !/if \(connected\) \{ setTab\('connections'\); return; \}/.test(pagina));
const iAbrir = pagina.indexOf("acao.tipo === 'abrir'");
const iCriar = pagina.indexOf('openCreate(t);');
assert('o "abrir" vem antes do openCreate no clique', iAbrir > 0 && iCriar > iAbrir);
assert('o Agger da corretora está no catálogo', pagina.includes('AggerDaCorretoraModal') && pagina.includes('title="Agger da corretora"'));

// ⑦ CONTROLE: a regra ANTIGA, sobre o caso do Founder, daria "nova" — o guarda consegue ficar vermelho
const regraAntiga = (tpl, lista) => {
  const st = (lista || []).find((x) => x.connector_template_id === tpl && x.status !== 'archived')?.status;
  return st === 'connected' ? 'abrir' : 'nova';
};
assert('CONTROLE: regra antiga com InfoCap em erro → nova', regraAntiga(INFOCAP, [c('x1', INFOCAP, 'error')]) === 'nova');
assert('CONTROLE: regra nova no mesmo caso → abrir', M.oQueOCatalogoAbre(INFOCAP, [c('x1', INFOCAP, 'error')]).tipo === 'abrir');

console.log(`\no-conector-conectado-abre-a-conexao: ${pass} ok, ${fail} falha(s)`);
process.exit(fail ? 1 : 0);
