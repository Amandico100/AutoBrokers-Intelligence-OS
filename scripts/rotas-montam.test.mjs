// A tabela de rotas do Next.js precisa MONTAR.
//
// Em 02/08/2026 o produto ficou 1h40 fora do ar — 500 em TODAS as rotas — e
// nenhum gate pegou: `next build` passou (287 rotas, 135 páginas), `tsc`
// passou, os 111 testes passaram, a imagem Docker foi construída com sucesso e
// o contêiner escreveu `Ready in 1253ms`. Na linha seguinte:
//
//     [Error: You cannot use different slug names for the same dynamic path
//             ('templateId' !== 'slug').]
//         at getSortedRoutes (next/dist/shared/lib/router/utils/sorted-routes)
//         at DefaultRouteMatcherManager.reload (...)
//
// Causa: `app/api/dashboard/auxiliaries/[slug]/config/` nasceu ao lado de
// `app/api/dashboard/auxiliaries/[templateId]/`. O Next.js exige UM nome de
// parâmetro por posição. Sem tabela de rotas, o servidor não tem o que
// responder — e devolve 500 até no 404.
//
// O sintoma enganava de fora: `public/` continuava servindo 200, porque o
// servidor de estáticos não passa pelo roteador. Parecia "telas quebradas".
// Era o produto inteiro.
//
// Este teste chama a MESMA função que estourou, com as rotas reais lidas do
// disco. Se `getSortedRoutes` retorna, a tabela monta. É a única verificação
// barata que enxerga o que o build não enxerga.

import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const RAIZ = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const APP = path.join(RAIZ, 'app');

const { getSortedRoutes } = require('next/dist/shared/lib/router/utils/sorted-routes');

/** Reproduz o mapeamento pasta → URL do App Router. */
function rotasDoDisco() {
  const rotas = [];
  const ARQUIVOS_DE_ROTA = ['route.ts', 'route.tsx', 'route.js', 'page.tsx', 'page.ts', 'page.js'];

  (function anda(dir, url) {
    for (const entrada of fs.readdirSync(dir, { withFileTypes: true })) {
      if (!entrada.isDirectory()) continue;
      const nome = entrada.name;
      const sub = path.join(dir, nome);

      // `_privadas` não viram rota; `(grupos)` não entram na URL.
      if (nome.startsWith('_')) continue;
      if (nome.startsWith('(') && nome.endsWith(')')) { anda(sub, url); continue; }
      if (nome.startsWith('@')) { anda(sub, url); continue; }   // slots paralelos

      const novaUrl = `${url}/${nome}`;
      const arquivos = fs.readdirSync(sub);
      if (ARQUIVOS_DE_ROTA.some((a) => arquivos.includes(a))) rotas.push(novaUrl);
      anda(sub, novaUrl);
    }
  })(APP, '');

  return rotas;
}

const falhas = [];
function checar(condicao, nome, detalhe = '') {
  if (condicao) {
    console.log(`  OK  ${nome}`);
  } else {
    falhas.push(detalhe ? `${nome} — ${detalhe}` : nome);
    console.log(`  X   ${nome}  ${detalhe}`);
  }
}

console.log('='.repeat(68));
console.log('A TABELA DE ROTAS MONTA — build verde nao e prova de que sobe');
console.log('='.repeat(68));

const rotas = rotasDoDisco();
console.log(`\n[1] Rotas lidas de app/: ${rotas.length}`);
checar(rotas.length > 100, 'a varredura encontrou rotas',
       `so ${rotas.length} — a leitura do disco provavelmente quebrou`);

console.log('\n[2] getSortedRoutes aceita a arvore inteira');
let erro = null;
let ordenadas = [];
try {
  ordenadas = getSortedRoutes(rotas);
} catch (e) {
  erro = e;
}
checar(erro === null, 'a tabela de rotas monta',
       erro ? `${erro.message} — o servidor devolveria 500 em TUDO` : '');
if (!erro) console.log(`      ${ordenadas.length} rotas ordenadas`);

// A regressão específica, nomeada — para ninguém a reintroduzir sem perceber.
console.log('\n[3] A regressao de 02/08 continua fechada');
const base = path.join(APP, 'api', 'dashboard', 'auxiliaries');
checar(!fs.existsSync(path.join(base, '[slug]')),
       'a pasta [slug] nao voltou para auxiliaries/',
       'ela conviveu com [templateId] e derrubou o site');
checar(fs.existsSync(path.join(base, '[auxiliar]', 'route.ts')) &&
       fs.existsSync(path.join(base, '[auxiliar]', 'config', 'route.ts')),
       'as duas rotas dividem o segmento [auxiliar]');

console.log('\n' + '='.repeat(68));
if (falhas.length) {
  console.log(`${falhas.length} PROBLEMA(S):`);
  for (const f of falhas) console.log(`  - ${f}`);
  process.exit(1);
}
console.log('A TABELA DE ROTAS MONTA');
process.exit(0);
