// A CAIXA FICA NO RODAPÉ — e tem a largura da conversa.
//
// Roda com: node --test scripts/a-caixa-fica-no-rodape.test.mjs   (ou `npm run test:caixa-no-rodape`)
//
// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
// O DEFEITO (relato do Founder, 15/10/2026, notebook ~1280 px): "a caixa de texto sobe na tela — um pouco na 1ª
// pergunta, mais na 2ª… e agora está lá em cima", com a tela preta vazia abaixo dela.
//
// O FIO, elo a elo (📊 medido no Chromium headless a 1280×800 com o tailwind.config.ts real; réplica das classes):
//   1 `MessageBubble.tsx` — cada resposta tem `<span class="sr-only" aria-live>` (o "Copiado"): position:absolute.
//   2 `chat/page.tsx` — a lista que rola (`ref={rolagemRef}`) NÃO era posicionada; o bloco que contém o `absolute`
//     era o `<div relative>` de FORA da lista → o span escapava do recorte da lista e esticava o `<main>` do casco.
//   3 `TenantAppShell.tsx` — `<main overflow-hidden>`: o corretor não rola, mas o NAVEGADOR rola por programa.
//   4 `chat/page.tsx` — `fimDaLista.scrollIntoView()` (bloco `start`) rola TODOS os ancestrais roláveis: o <main>
//     subia o que o span tinha esticado. Topo da caixa: 730 → 730 → 495 → 145 → 40 px em 5 perguntas.
//   Cada conserto SOZINHO segura a caixa em 730 px (as duas linhas de controle da medição); os dois ficam.
//
// O QUE ESTE GUARDA EXIGE (lê os arquivos-fonte; sem rede, sem node_modules):
//   (a) a lista que rola é `relative` (contém os seus `absolute`) e a rolagem até o fim mexe SÓ nela
//       (`el.scrollTo`), nunca `scrollIntoView`; a centralização da tela vazia só vale com `vazia`.
//   (b) a caixa e a coluna das mensagens têm a MESMA largura máxima (a de `components/chat/coluna.ts`).
//   (c) no notebook (sm+) o campo tem altura mínima confortável (≥ 52 px).
//
// MUTAÇÃO (vermelho provado no relatório): os arquivos de antes (`git show HEAD:…`) postos no lugar → (a)(b)(c) caem.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const RAIZ = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const ler = (rel) => fs.readFileSync(path.join(RAIZ, rel), 'utf8');

/** tira comentários (bloco e linha) — o guarda olha o CÓDIGO, não a história contada nos comentários */
function semComentarios(fonte) {
  return fonte
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/(^|[^:'"`\w])\/\/[^\n]*/g, '$1');
}

const PAGINA = 'app/dashboard/chat/page.tsx';
const COMPOSER = 'components/chat/composer/Composer.tsx';
const COLUNA = 'components/chat/coluna.ts';

/** o `className` da abertura de tag que contém `marca` (literal "…" ou {`…`} / {cn(…)}) */
function classeDaTag(fonte, marca) {
  const i = fonte.indexOf(marca);
  if (i < 0) return null;
  const abre = fonte.lastIndexOf('<', i);
  const fecha = fonte.indexOf('>', i);
  const tag = fonte.slice(abre, fecha + 1);
  const m = /className=(?:"([^"]*)"|\{([\s\S]*?)\}\s*(?:[a-zA-Z-]+=|\/?>))/.exec(tag);
  return m ? (m[1] ?? m[2]) : null;
}

/** a largura máxima que uma expressão de classe resolve (literal, ou a constante da coluna) */
function larguraMaxima(expr) {
  if (expr == null) return null;
  if (/COLUNA_DA_CONVERSA/.test(expr)) {
    if (!fs.existsSync(path.join(RAIZ, COLUNA))) return 'COLUNA_DA_CONVERSA sem coluna.ts';
    const constante = /COLUNA_DA_CONVERSA\s*=\s*'([^']*)'/.exec(ler(COLUNA));
    expr = `${expr} ${constante ? constante[1] : ''}`;
  }
  const larguras = expr.match(/(?:^|[\s'"`])(max-w-[\w[\].-]+)/g)?.map((s) => s.trim().replace(/^['"`]/, '')) ?? [];
  return larguras.length === 1 ? larguras[0] : larguras.join('+') || null;
}

test('(a) a lista que rola contém os seus `absolute` (é `relative`)', () => {
  const pagina = semComentarios(ler(PAGINA));
  const classe = classeDaTag(pagina, 'ref={rolagemRef}');
  assert.ok(classe, 'não achei a lista que rola (`ref={rolagemRef}`) em chat/page.tsx');
  assert.match(classe, /overflow-y-auto/, 'a lista que rola deixou de rolar');
  assert.match(
    classe,
    /(^|\s)relative(\s|$)/,
    `a lista que rola não é posicionada: o sr-only do "Copiado" (MessageBubble) escapa dela e estica o <main> — className="${classe}"`,
  );
});

test('(a) rolar até o fim mexe SÓ na lista — nunca `scrollIntoView` (que rola o <main> do casco)', () => {
  const pagina = semComentarios(ler(PAGINA));
  assert.ok(!/\.scrollIntoView\s*\(/.test(pagina), 'chat/page.tsx voltou a usar scrollIntoView: ele rola TODOS os ancestrais, inclusive o <main overflow-hidden>');
  const corpo = /const scrollToBottom = \(\) => \{([\s\S]*?)\n  \};/.exec(pagina);
  assert.ok(corpo, 'não achei `scrollToBottom` em chat/page.tsx');
  assert.match(corpo[1], /rolagemRef\.current/, 'scrollToBottom tem de rolar a própria lista (rolagemRef)');
  assert.match(corpo[1], /\.scrollTo\s*\(/, 'scrollToBottom tem de usar `el.scrollTo` na lista');
});

test('(a) a tela vazia é a ÚNICA que centraliza; com mensagens, a lista cresce e a caixa fica embaixo', () => {
  const pagina = semComentarios(ler(PAGINA));
  // toda ocorrência de justify-center no contêiner da conversa está dentro de um ramo `vazia ? '…'`
  const raiz = classeDaTag(pagina, 'onDragEnter={aoEntrarArrastando}');
  assert.ok(raiz, 'não achei a coluna da conversa (a que recebe o arrastar)');
  assert.match(raiz, /\bh-full\b/);
  assert.match(raiz, /\bflex-col\b/);
  assert.match(raiz, /\$\{vazia \? '[^']*lg:justify-center[^']*' : ''\}/, 'o centralizar da tela vazia saiu do ramo `vazia`');
  assert.doesNotMatch(raiz.replace(/\$\{vazia \?[^}]*\}/g, ''), /justify-center|justify-end/, 'a coluna centraliza mesmo com mensagens');
  assert.match(pagina, /vazia \? 'flex flex-1 flex-col lg:flex-none' : 'flex-1'/, 'com mensagens, a área da lista tem de ser `flex-1` (é ela que cresce)');
  assert.match(pagina, /<div className="shrink-0[^"]*">\s*<Composer/, 'a caixa deixou de ser a faixa fixa (`shrink-0`) do rodapé');
});

test('(b) a caixa e a coluna das mensagens têm a MESMA largura máxima (≈ 48rem)', () => {
  const pagina = semComentarios(ler(PAGINA));
  const composer = semComentarios(ler(COMPOSER));
  const daCaixa = larguraMaxima(classeDaTag(composer, 'data-composer=""'));
  // a coluna das mensagens: a 1ª tag depois da lista que rola
  const depois = pagina.slice(pagina.indexOf('ref={rolagemRef}'));
  const daColuna = larguraMaxima(classeDaTag(depois.slice(depois.indexOf('>') + 1), '<div'));
  assert.equal(daCaixa, daColuna, `caixa ${daCaixa} ≠ coluna ${daColuna}`);
  assert.equal(daCaixa, 'max-w-3xl', `a largura comum tem de ser max-w-3xl (48rem), achei ${daCaixa}`);
  assert.match(composer, /COLUNA_DA_CONVERSA/, 'a caixa não usa a constante da coluna');
  assert.match(pagina, /COLUNA_DA_CONVERSA/, 'a lista não usa a constante da coluna');
});

test('(c) no notebook (sm+) o campo tem altura mínima confortável', () => {
  const composer = semComentarios(ler(COMPOSER));
  const campo = /<textarea[\s\S]*?className=\{cn\(([\s\S]*?)\)\}/.exec(composer);
  assert.ok(campo, 'não achei o campo da caixa');
  const m = /sm:min-h-\[(\d+)px\]/.exec(campo[1]);
  assert.ok(m, 'o campo não tem altura mínima própria no notebook (sm:min-h-[…px])');
  assert.ok(Number(m[1]) >= 52, `sm:min-h-[${m[1]}px] é baixo demais (< 52 px)`);
  // o celular não muda: a linha única de 44 px continua sendo a base
  assert.match(campo[1], /'block min-h-11 min-w-0 flex-1/, 'a base do celular (min-h-11, uma linha) mudou');
});
