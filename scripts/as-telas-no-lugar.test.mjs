// modelo: claude-opus-5-5
//
// SPEC-139 · L3 — as telas no lugar (P-16): o Checklist das 6h, o Follow-up do WhatsApp e o Resumo de atendimentos
// viram a aba do TRABALHO de cada aplicativo na casca `/dashboard/auxiliares/<slug>?aba=`, e cada endereço antigo
// redireciona para lá.
//
// Roda com: node scripts/as-telas-no-lugar.test.mjs
//
// O que este teste afirma (e como):
//   [1] cada `page.tsx` antiga, EXECUTADA (transpilada com o TypeScript do projeto, `next/navigation` trocado por um
//       dublê que registra o destino), chama `redirect()` para o endereço novo — o motor é a própria página, não um
//       regex sobre ela. Mutação 5 da SPEC (tire um redirect → 404): fica VERMELHO.
//   [2] o componente movido faz as MESMAS chamadas de dados (rotas de API, ações do POST, funções de `lib/*/api`) que
//       a tela antiga fazia. A tela antiga é lida do commit-base pelo git (a LINHA DE CONTROLE: o extrator acha, na
//       tela antiga, exatamente a lista escrita aqui — prova que a lista não foi inventada e que o extrator funciona).
//   [3] nenhuma pasta dinâmica nova na árvore de `auxiliares` (CLAUDE.md §9.1), e nenhuma pasta estática com o slug
//       de um destes aplicativos tem `page.tsx` na raiz (ela engoliria a casca `[slug]`).
//   [4] cada aba é um módulo que a casca sabe carregar (`<pasta>/Aba<Nome>`, export default, 'use client').
//   [5] COSTURA com a L4 (quando ela registrar): `ABAS_DO_APLICATIVO` aponta para estes módulos com estes ids.
//
// MUTACAO_DE_TESTE (só para a régua): `TELAS_SOB_TESTE_RAIZ=<pasta>` lê as páginas e componentes de outra raiz.

import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const RAIZ = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const RAIZ_SOB_TESTE = process.env.TELAS_SOB_TESTE_RAIZ ? path.resolve(process.env.TELAS_SOB_TESTE_RAIZ) : RAIZ;
const ts = require('typescript');

/** O commit anterior à SPEC-139: a tela antiga ainda inteira (📊 `git log -1 --format=%H origin/main`, 15/10/2026). */
const COMMIT_BASE = '5f9bdacb8edb49990c9bd76eb891dcdebdc725d9';

let falhas = 0;
function checar(cond, nome, detalhe = '') {
  if (cond) console.log(`  OK  ${nome}`);
  else {
    falhas += 1;
    console.log(`  X   ${nome}${detalhe ? `  — ${detalhe}` : ''}`);
  }
}

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
// O contrato da L3 (o que a L4 registra em ABAS_DO_APLICATIVO)
// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
const TELAS = [
  {
    slug: 'checklist-6h',
    antiga: 'app/dashboard/auxiliares/checklist-6h/hoje/page.tsx',
    destino: '/dashboard/auxiliares/checklist-6h?aba=hoje',
    abas: { hoje: 'checklist-6h/AbaHoje', configurar: 'checklist-6h/AbaConfigurar' },
    // 📊 lidas da tela antiga em COMMIT_BASE (o [2] reconfere pelo git)
    chamadas: [
      'fetch:/api/dashboard/briefing',
      'fetch:/api/dashboard/briefing?aba=${qual}',
      'acao:gerar',
      'acao:preferencias',
      'acao:responder_finding',
      'acao:responder_recomendacao',
    ],
  },
  {
    slug: 'follow-up-whatsapp',
    antiga: 'app/dashboard/auxiliares/galeria/follow-up-whatsapp/page.tsx',
    destino: '/dashboard/auxiliares/follow-up-whatsapp?aba=follow-ups',
    abas: { 'follow-ups': 'follow-up-whatsapp/AbaFollowUps' },
    chamadas: [
      'api:createApprovalRequest',
      'api:draftFollowUpWhatsapp',
      'api:fetchConnectorTemplates',
      'api:fetchPermissions',
      'api:fetchResumoConversations',
      'api:fetchTenantConnections',
      'lit:auxiliary_follow_up_whatsapp',
      'lit:whatsapp_send_message_dry_run',
      'lit:whatsapp_zapi',
    ],
  },
  {
    slug: 'resumo-atendimentos',
    antiga: 'app/dashboard/auxiliares/galeria/resumo-atendimentos/page.tsx',
    destino: '/dashboard/auxiliares/resumo-atendimentos?aba=resumos',
    abas: { resumos: 'resumo-atendimentos/AbaResumos' },
    chamadas: ['api:fetchResumoConversations', 'api:fetchRun', 'api:runResumoAtendimentos'],
  },
];

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
// O extrator de chamadas de dados — o mesmo para a tela antiga e para os componentes novos
// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
function semComentarios(fonte) {
  return fonte.replace(/\/\*[\s\S]*?\*\//g, '').replace(/(^|[^:'"`])\/\/.*$/gm, '$1');
}

/** As chamadas de dados de uma fonte TSX: URLs de fetch, ações do POST, funções de `@/lib/<x>/api` CHAMADAS, e os
 *  literais que decidem o que a ação faz (slug do conector, action_type, source). */
function chamadasDe(fonte) {
  const f = semComentarios(fonte);
  const achadas = new Set();
  for (const m of f.matchAll(/fetch\(\s*[`'"]([^`'"]+)[`'"]/g)) achadas.add(`fetch:${m[1]}`);
  for (const m of f.matchAll(/acao:\s*'([a-z_]+)'/g)) achadas.add(`acao:${m[1]}`);
  for (const m of f.matchAll(/import\s*\{([^}]+)\}\s*from\s*'@\/lib\/[a-z-]+\/api'/g)) {
    for (const nome of m[1].split(',').map((s) => s.trim().replace(/^type\s+/, '')).filter(Boolean)) {
      if (new RegExp(`\\b${nome}\\(`).test(f.replace(m[0], ''))) achadas.add(`api:${nome}`);
    }
  }
  for (const lit of ['whatsapp_zapi', 'whatsapp_send_message_dry_run', 'auxiliary_follow_up_whatsapp']) {
    if (f.includes(`'${lit}'`)) achadas.add(`lit:${lit}`);
  }
  return achadas;
}

function lerDoGit(rel) {
  try {
    return execFileSync('git', ['show', `${COMMIT_BASE}:${rel}`], {
      cwd: RAIZ,
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'ignore'],
    });
  } catch {
    return null;
  }
}

function lerSobTeste(rel) {
  const p = path.join(RAIZ_SOB_TESTE, rel);
  return fs.existsSync(p) ? fs.readFileSync(p, 'utf8') : null;
}

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
// Executar a página antiga com `next/navigation` de dublê
// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
class Redirecionou extends Error {
  constructor(destino) {
    super(`NEXT_REDIRECT ${destino}`);
    this.destino = destino;
  }
}

async function destinoDaPagina(rel) {
  const fonte = lerSobTeste(rel);
  if (fonte === null) return { erro: 'o arquivo não existe (404 para link salvo)' };
  const js = ts.transpileModule(fonte, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020,
      jsx: ts.JsxEmit.ReactJSX,
      esModuleInterop: true,
    },
    fileName: rel,
  }).outputText;
  const mod = { exports: {} };
  const req = (id) => {
    if (id === 'next/navigation') {
      return {
        redirect: (d) => {
          throw new Redirecionou(d);
        },
        permanentRedirect: (d) => {
          throw new Redirecionou(`PERMANENTE ${d}`);
        },
        notFound: () => {
          throw new Error('notFound()');
        },
      };
    }
    // Uma página que só redireciona não importa mais nada; qualquer outro import (React, componentes) é a tela
    // antiga ainda inteira no lugar.
    throw new Error(`a página importa '${id}' — não é só um redirect`);
  };
  try {
    // eslint-disable-next-line no-new-func
    new Function('require', 'module', 'exports', js)(req, mod, mod.exports);
    const pagina = mod.exports.default;
    if (typeof pagina !== 'function') return { erro: 'sem export default' };
    await pagina({ params: Promise.resolve({}), searchParams: Promise.resolve({}) });
    return { erro: 'a página renderizou sem redirecionar' };
  } catch (e) {
    if (e instanceof Redirecionou) return { destino: e.destino, fonte };
    return { erro: String(e?.message || e) };
  }
}

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
console.log('\n[1] Cada endereço antigo redireciona (307) para a aba do trabalho na casca');
for (const t of TELAS) {
  const r = await destinoDaPagina(t.antiga);
  checar(r.destino === t.destino, `${t.antiga} → ${t.destino}`, r.erro || `foi para ${r.destino}`);
  if (r.fonte) {
    checar(!/^\s*['"]use client['"]/m.test(r.fonte), `${t.antiga} é server component (redirect() dá 307 no servidor)`);
  }
}

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
console.log('\n[2] O componente movido faz as MESMAS chamadas de dados que a tela antiga');
for (const t of TELAS) {
  const antiga = lerDoGit(t.antiga);
  const esperadas = new Set(t.chamadas);
  if (antiga === null) {
    console.log(`  ..  sem git/commit-base: a linha de controle de ${t.slug} não roda (confere só a lista escrita)`);
  } else {
    const daAntiga = chamadasDe(antiga);
    const iguais = daAntiga.size === esperadas.size && [...daAntiga].every((c) => esperadas.has(c));
    checar(
      iguais,
      `CONTROLE: o extrator acha na tela antiga (${COMMIT_BASE.slice(0, 7)}) exatamente as ${esperadas.size} chamadas escritas (${t.slug})`,
      `achou ${[...daAntiga].sort().join(', ')}`,
    );
  }
  const novas = new Set();
  let faltandoArquivo = false;
  for (const mod of Object.values(t.abas)) {
    const fonte = lerSobTeste(`components/aplicativos/${mod}.tsx`);
    if (fonte === null) {
      faltandoArquivo = true;
      checar(false, `components/aplicativos/${mod}.tsx existe`);
      continue;
    }
    for (const c of chamadasDe(fonte)) novas.add(c);
  }
  if (faltandoArquivo) continue;
  const perdidas = [...esperadas].filter((c) => !novas.has(c));
  checar(perdidas.length === 0, `${t.slug}: as ${esperadas.size} chamadas da tela antiga estão nas abas novas`, `perdidas: ${perdidas.join(', ')}`);
  const inventadas = [...novas].filter((c) => !esperadas.has(c));
  checar(inventadas.length === 0, `${t.slug}: nenhuma chamada de dados nova (movido, não reescrito)`, `novas: ${inventadas.join(', ')}`);
}

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
console.log('\n[3] Nenhuma pasta dinâmica nova, e nenhuma pasta estática engole a casca (CLAUDE.md §9.1)');
const AUX = path.join(RAIZ_SOB_TESTE, 'app', 'dashboard', 'auxiliares');
function dinamicas(dir, rel = '') {
  const achadas = [];
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (!e.isDirectory()) continue;
    const r = rel ? `${rel}/${e.name}` : e.name;
    if (e.name.includes('[')) achadas.push(r);
    achadas.push(...dinamicas(path.join(dir, e.name), r));
  }
  return achadas;
}
const PERMITIDAS = ['[slug]', 'galeria/[slug]'];
const achadas = dinamicas(AUX).sort();
checar(
  achadas.length === PERMITIDAS.length && achadas.every((d, i) => d === PERMITIDAS[i]),
  `as pastas dinâmicas de auxiliares/ são só ${PERMITIDAS.join(' e ')}`,
  `achadas: ${achadas.join(', ')}`,
);
checar(achadas.length >= 1, 'CONTROLE: o varredor acha pasta dinâmica (se achasse 0, o guarda não mediria nada)');
for (const t of TELAS) {
  checar(
    !fs.existsSync(path.join(AUX, t.slug, 'page.tsx')),
    `não existe app/dashboard/auxiliares/${t.slug}/page.tsx (a rota estática engoliria a casca do aplicativo)`,
  );
  checar(
    !fs.existsSync(path.join(AUX, t.slug, 'layout.tsx')),
    `não existe app/dashboard/auxiliares/${t.slug}/layout.tsx`,
  );
}

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
console.log('\n[4] Cada aba é um módulo que a casca carrega (`<pasta>/Aba<Nome>`, export default, cliente)');
// a mesma forma que `components/aplicativos/casca/AbasDoAplicativo.tsx` aceita (FORMA_DO_COMPONENTE)
const FORMA = /^([a-z0-9-]+)\/Aba([A-Za-z0-9]+)$/;
const casca = fs.readFileSync(path.join(RAIZ, 'components', 'aplicativos', 'casca', 'AbasDoAplicativo.tsx'), 'utf8');
checar(casca.includes(FORMA.source), 'CONTROLE: a forma deste teste é a da casca');
for (const t of TELAS) {
  for (const [id, mod] of Object.entries(t.abas)) {
    const fonte = lerSobTeste(`components/aplicativos/${mod}.tsx`);
    checar(FORMA.test(mod) && mod.startsWith(`${t.slug}/`), `${t.slug}?aba=${id} → '${mod}' tem a forma da casca`);
    if (fonte === null) continue;
    checar(/^\s*['"]use client['"]/.test(fonte), `${mod}.tsx é 'use client'`);
    checar(/export\s+default\s+function\s+Aba[A-Za-z0-9]+/.test(fonte), `${mod}.tsx exporta default a aba`);
    // a casca já dá o cabeçalho, a largura e a rolagem: a aba não pode trazer a página antiga em volta
    checar(!/h-full overflow-y-auto/.test(fonte) && !/<DetailShell/.test(fonte), `${mod}.tsx não traz a moldura da página antiga`);
  }
}

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
console.log('\n[5] Costura com a L4: o catálogo aponta para estas abas (quando registrar)');
const catalogo = fs.readFileSync(path.join(RAIZ, 'lib', 'auxiliaries', 'catalog.ts'), 'utf8');
const bloco = (catalogo.split('export const ABAS_DO_APLICATIVO')[1] || '').split('\n};')[0];
for (const t of TELAS) {
  const re = new RegExp(`['"]?${t.slug}['"]?\\s*:\\s*\\[([\\s\\S]*?)\\]`, 'm');
  const m = re.exec(bloco);
  if (!m) {
    console.log(`  ..  ${t.slug}: a L4 ainda não registrou em ABAS_DO_APLICATIVO (a costura confere na L6)`);
    continue;
  }
  for (const [id, mod] of Object.entries(t.abas)) {
    checar(
      new RegExp(`id:\\s*'${id}'[^}]*componente:\\s*'${mod}'`).test(m[1]),
      `ABAS_DO_APLICATIVO['${t.slug}'] tem { id: '${id}', componente: '${mod}' }`,
    );
  }
}

console.log(`\n${falhas === 0 ? 'AS TELAS ESTÃO NO LUGAR' : `${falhas} FALHA(S)`}`);
process.exit(falhas === 0 ? 0 : 1);
