#!/usr/bin/env node
/**
 * O GUARDA DA INSTALAÇÃO DE AUXILIAR — TypeScript ↔ schema real.
 *
 * 📊 Em 17/08/2026 o Founder não conseguia instalar a Cobrança Feita. A tela
 * dizia `install_failed` e mais nada. Eram TRÊS defeitos empilhados, todos da
 * mesma família — o TypeScript escrevendo no banco coisas que o banco não
 * aceita, e a tela jogando fora a mensagem que explicava:
 *
 *   1. o INSERT mandava `display_name`, coluna que NÃO EXISTE  → PGRST204
 *   2. o status `awaiting_runtime` não passa no CHECK           → 23514
 *   3. `uninstall` gravava `uninstalled`, idem                  → 23514
 *
 * Os três só apareciam em runtime, contra o banco. `tsc` passa em todos:
 * `.insert({...})` aceita qualquer objeto. É por isso que este guarda existe —
 * ele lê a FONTE e compara com o schema medido, sem precisar de conexão.
 *
 * ⚠ Ele NÃO roda no CI (📊 `.github/workflows/gate.yml` não executa `.mjs`).
 * Rode `npm run test:auxiliares-instalacao` ao mexer na instalação.
 */
import { createRequire } from 'node:module';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const require = createRequire(import.meta.url);
const RAIZ = join(dirname(fileURLToPath(import.meta.url)), '..');

const STORE = 'lib/admin/tenant-auxiliary-store.ts';
const TELA = 'app/dashboard/auxiliares/[slug]/AuxiliarDetalheClient.tsx';
const ROTINAS = 'app/dashboard/auxiliares/rotinas/page.tsx';

/**
 * 📊 As colunas REAIS de `public.tenant_auxiliaries`, lidas de
 * `information_schema.columns` no projeto `dcajcvlzcjbmyapmklil` em
 * 17/08/2026 03:5x UTC.
 *
 * Esta lista é uma CÓPIA, e cópia envelhece. Ela está aqui porque a tabela é
 * uma das aplicadas sem arquivo de migration (MIGRATIONS-AUTHORITY §4): não há
 * fonte no repositório para ler. Ao alterar a tabela, atualize aqui na mesma
 * mão — é exatamente esse o passo que ninguém deu quando `display_name` sumiu.
 */
const COLUNAS_REAIS = new Set([
  'id', 'company_id', 'template_id', 'slug', 'name', 'status', 'config',
  'permissions', 'installed_by', 'installed_at', 'last_run_at', 'created_at',
  'updated_at', 'visibility', 'owner_user_id', 'release_id',
  'current_revision', 'health', 'health_reason', 'work_pattern',
]);

/** 📊 `pg_get_constraintdef` de `tenant_auxiliaries_status_check`, mesma data. */
const STATUS_DO_CHECK = ['inactive', 'active', 'paused', 'disabled', 'archived'];

let falhas = 0;
const ok = (n) => console.log(`  ✓ ${n}`);
const falhar = (n, d) => { falhas++; console.log(`  ✗ ${n}\n      ${d}`); };
function conferir(nome, cond, detalhe) { cond ? ok(nome) : falhar(nome, detalhe); }

function ler(rel) { return readFileSync(join(RAIZ, rel), 'utf8'); }

/**
 * Executa o TypeScript de verdade, transpilando com o próprio `typescript`.
 * (Padrão de `scripts/atendimento-estados.test.mjs`: testar o módulo, não uma
 * tradução dele feita à mão.) Os imports do store são apagados antes — só
 * queremos as funções puras, e `@/...` o node não resolve.
 */
function carregarFuncoesPuras(rel) {
  const ts = require('typescript');
  const fonte = ler(rel)
    .replace(/^\s*import[\s\S]*?from\s+['"][^'"]+['"];?\s*$/gm, '')
    .replace(/^\s*import\s+['"][^'"]+['"];?\s*$/gm, '');
  const js = ts.transpileModule(fonte, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
  }).outputText;
  const mod = { exports: {} };
  new Function('module', 'exports', 'require', js)(mod, mod.exports, require);
  return mod.exports;
}

/**
 * O corpo do `.insert({...})`: da abertura até o fecho, contando chaves.
 * Regex simples pararia no primeiro `}` de um objeto aninhado (`config: {…}`).
 */
function corpoDoInsert(fonte) {
  const i = fonte.indexOf(".insert({");
  if (i < 0) return null;
  let nivel = 0, j = i + '.insert('.length;
  for (; j < fonte.length; j++) {
    if (fonte[j] === '{') nivel++;
    else if (fonte[j] === '}' && --nivel === 0) return fonte.slice(i, j + 1);
  }
  return null;
}

/**
 * As chaves de primeiro nível escritas no objeto (ignora as aninhadas).
 *
 * ⚠️ A primeira versão disto quebrava linha a linha, e por isso NÃO via uma
 * chave escrita na mesma linha da abertura (`.insert({ display_name: …`). A
 * asserção "nenhuma coluna inventada" passava — pelo motivo errado. Foi a
 * linha de CONTROLE lá embaixo que acusou; nenhum olho meu.
 *
 * Agora varre caractere a caractere: uma chave só conta se estiver na
 * profundidade 1 e vier logo depois de `{` ou de `,` — o que descarta o `:` de
 * um ternário, que também aparece no topo.
 */
function chavesDeTopo(corpo) {
  const limpo = corpo.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/[^\n]*/g, '');
  const chaves = [];
  let nivel = 0, aspas = null, token = '', podeSerChave = false;
  for (let i = 0; i < limpo.length; i++) {
    const c = limpo[i];
    if (aspas) { if (c === aspas && limpo[i - 1] !== '\\') aspas = null; continue; }
    if (c === "'" || c === '"' || c === '`') { aspas = c; token = ''; continue; }
    if (c === '{' || c === '[' || c === '(') { nivel += c === '{' ? 1 : 0; token = ''; podeSerChave = c === '{'; continue; }
    if (c === '}' || c === ']' || c === ')') { nivel -= c === '}' ? 1 : 0; token = ''; podeSerChave = false; continue; }
    if (c === ',') { token = ''; podeSerChave = true; continue; }
    if (c === ':') {
      if (nivel === 1 && podeSerChave && /^[A-Za-z_][A-Za-z0-9_]*$/.test(token)) chaves.push(token);
      token = ''; podeSerChave = false; continue;
    }
    if (/\s/.test(c)) continue;
    token += c;
  }
  return chaves;
}

// ---------------------------------------------------------------------------
console.log('\n1 · O INSERT só escreve colunas que existem');

const fonteStore = ler(STORE);
const corpo = corpoDoInsert(fonteStore);
conferir('achou o corpo do .insert', Boolean(corpo), `não encontrei .insert({ em ${STORE}`);

if (corpo) {
  const inventadas = chavesDeTopo(corpo).filter((c) => !COLUNAS_REAIS.has(c));
  conferir(
    'nenhuma coluna inventada',
    inventadas.length === 0,
    `o INSERT manda campo(s) que a tabela não tem: ${inventadas.join(', ')} — ` +
    'isso vira PGRST204 e a tela mostra "install_failed"',
  );

  // 🔴 CONTROLE (CLAUDE.md §9.3) — a asserção acima só vale se ela CONSEGUIR
  // ficar vermelha. Injetamos o campo exato que causou o bug e exigimos que o
  // guarda o acuse. Sem esta linha, um `chavesDeTopo` quebrado passaria calado.
  const envenenado = corpo.replace('.insert({', '.insert({ display_name: tpl.name,');
  const pegou = chavesDeTopo(envenenado).includes('display_name');
  conferir(
    'CONTROLE: o guarda detecta display_name reintroduzido',
    pegou,
    'o guarda NÃO viu `display_name` de volta — ele não guarda nada',
  );
}

// ---------------------------------------------------------------------------
console.log('\n2 · Todo status gravado passa no CHECK do banco');

const { statusValidoNoBanco, STATUS_ACEITOS_PELO_BANCO, REMOVIDOS } =
  carregarFuncoesPuras(STORE);

conferir(
  'a lista no TS é a mesma do CHECK medido',
  JSON.stringify([...STATUS_ACEITOS_PELO_BANCO].sort()) === JSON.stringify([...STATUS_DO_CHECK].sort()),
  `TS=${[...(STATUS_ACEITOS_PELO_BANCO || [])].join('|')} vs banco=${STATUS_DO_CHECK.join('|')}`,
);

// Todos os valores que o TypeScript sabe produzir, incluindo os três que o
// banco não conhece, e um inventado.
const QUE_O_TS_PRODUZ = [
  'active', 'paused', 'inactive', 'disabled', 'archived',
  'awaiting_runtime', 'uninstalled', 'error', 'valor_que_ninguem_previu',
];
const escapou = QUE_O_TS_PRODUZ
  .map((s) => [s, statusValidoNoBanco(s)])
  .filter(([, saida]) => !STATUS_DO_CHECK.includes(saida));
conferir(
  'nenhum status escapa do CHECK',
  escapou.length === 0,
  escapou.map(([e, s]) => `${e} → ${s}`).join(', '),
);

conferir(
  'awaiting_runtime vira inactive (instalado, ainda não trabalha)',
  statusValidoNoBanco('awaiting_runtime') === 'inactive',
  `virou ${statusValidoNoBanco('awaiting_runtime')}`,
);
conferir(
  'uninstalled vira archived (sai de cena sem apagar histórico)',
  statusValidoNoBanco('uninstalled') === 'archived',
  `virou ${statusValidoNoBanco('uninstalled')}`,
);
conferir(
  'desconhecido NUNCA nasce ligado',
  statusValidoNoBanco('qualquer_coisa') !== 'active',
  'um status que ninguém previu virou `active` — um Auxiliar liga sozinho',
);
conferir(
  'REMOVIDOS cobre os dois vocabulários',
  REMOVIDOS?.has('uninstalled') && REMOVIDOS?.has('archived'),
  'um Auxiliar removido responderia "já instalado" e nunca mais voltaria',
);

// Os TRÊS pontos de escrita têm de passar pelo tradutor. Contar é o que pega
// um quarto ponto criado no futuro sem ele.
const escritas = (fonteStore.match(/status:\s*(statusValidoNoBanco\(|gravavel)/g) || []).length;
conferir(
  'os 3 pontos de escrita usam o tradutor',
  escritas >= 3,
  `só ${escritas} de 3 (insert, reinstall, changeStatus) passam por statusValidoNoBanco`,
);

// ---------------------------------------------------------------------------
console.log('\n3 · A tela mostra a CAUSA, não o slug');

const fonteTela = ler(TELA);
conferir(
  'AuxiliarDetalheClient lê `details`',
  /j\?\.details|j\.details/.test(fonteTela),
  'a tela ignora `details` — o motivo real do erro morre antes de chegar ao corretor',
);
conferir(
  'o store manda `details` no install_failed',
  /error:\s*'install_failed',\s*details:/.test(fonteStore),
  'o store devolve `install_failed` sem a mensagem do banco',
);

// ---------------------------------------------------------------------------
console.log('\n4 · Existe caminho até a tela de configuração');

// 🔴 ESTE BLOCO FOI REESCRITO EM 17/08/2026, e a lição MIGROU (CLAUDE.md §9.3).
//
// Ele provava que existia um LINK do Auxiliar para uma página de rotinas — e
// isso era verdade até a SPEC-078 C.4 absorver aquela página. O link não existe
// mais porque o painel de configuração passou a morar DENTRO da tela do
// Auxiliar. Manter a afirmação antiga ensinaria a ignorar teste vermelho.
//
// A pergunta que importa é a mesma de antes, e continua sendo feita: **o
// corretor consegue chegar na configuração?** Só que agora a resposta certa é
// "sim, sem sair da página", e é isso que se verifica.
const fonteRotinas = ler(ROTINAS);
conferir(
  'a rota solta virou stub de redirect (SPEC-078 C.4)',
  /redirect\(/.test(fonteRotinas) && fonteRotinas.split('\n').length < 60,
  `${fonteRotinas.split('\n').length} linhas — deveria ser um stub`,
);
conferir(
  'a configuração mora DENTRO da tela do Auxiliar',
  /<PainelDeRotinas/.test(fonteTela),
  'sem o painel embutido, o corretor volta a não ter onde configurar',
);
conferir(
  'e o painel sabe de qual Auxiliar é (a rotina nasce com dono)',
  /auxiliarSlug=\{item\.slug\}/.test(fonteTela),
  'ONTOLOGIA:51 — Rotina nunca existe sozinha',
);

// ---------------------------------------------------------------------------
console.log(falhas === 0
  ? '\n✅ TODOS OS GUARDAS VERDES\n'
  : `\n❌ ${falhas} GUARDA(S) VERMELHO(S)\n`);
process.exit(falhas === 0 ? 0 : 1);
