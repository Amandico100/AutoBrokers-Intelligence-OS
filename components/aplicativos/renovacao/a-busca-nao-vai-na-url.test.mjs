// SPEC-131-B · conserto K2 — a busca ("Nome ou CPF") NUNCA vai na URL (juiz J-B1), e o "Copiar a mensagem" copia a
// mensagem COMPLETA (red team RT-B2).
//
// Roda com: node components/aplicativos/renovacao/a-busca-nao-vai-na-url.test.mjs
//
// COMO FUNCIONA — sem rede: `app/api/renovacoes/pedido.ts` (o que a rota Next manda ao backend) é transpilado com o
// TypeScript do projeto e CHAMADO de verdade com um CPF sintético; a tela (`AbaRenovacoes.tsx`) e o hook das ações são
// lidos como texto (o que eles põem na URL e o que copiam).
//
// LINHA DE CONTROLE (CLAUDE.md §9.2/§9.3): cada guarda roda também contra a forma DEFEITUOSA — a cópia mutada do
// `pedido.ts` que devolve `q` na query, e a versão da tela de antes do conserto (o defeito histórico) — e tem de ficar
// VERMELHO nela.

import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const RAIZ = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..', '..');
const ts = require('typescript');

let falhas = 0;
function checar(cond, nome, detalhe = '') {
  if (cond) console.log(`  OK  ${nome}`);
  else {
    falhas += 1;
    console.log(`  X   ${nome}${detalhe ? `  — ${detalhe}` : ''}`);
  }
}

function carregarFonte(fonte, nome) {
  const js = ts.transpileModule(fonte, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
    fileName: nome,
  }).outputText;
  const mod = { exports: {} };
  // eslint-disable-next-line no-new-func
  new Function('require', 'module', 'exports', js)(() => { throw new Error('pedido.ts tem de ser puro'); }, mod, mod.exports);
  return mod.exports;
}

const ler = (rel) => fs.readFileSync(path.join(RAIZ, rel), 'utf8');
const semComentario = (fonte) =>
  fonte.split('\n').filter((l) => !/^\s*(\/\/|\*|\/\*)/.test(l)).join('\n').replace(/\{\/\*[\s\S]*?\*\/\}/g, '');

// 💭 CPF SINTÉTICO (dígitos verificadores válidos, de nenhum cliente) e um nome de exemplo
const CPF = '52998224725';
const CPF_FORMATADO = '529.982.247-25';
const NOME = 'Cliente Exemplo da Conceição';
const SESSAO = { companyId: 'empresa-a', userId: 'pessoa-a', admin: false };

/** O guarda do proxy: a busca vai no cabeçalho `x-busca` e NADA dela aparece na query. */
function guardaDoProxy(P) {
  const erros = [];
  for (const [busca, esperado] of [[CPF, CPF], [CPF_FORMATADO, CPF_FORMATADO], [NOME, NOME]]) {
    // o navegador manda percent-encoded; um link VELHO ainda traz `q` na query — e ele tem de ser ignorado
    const entrada = new URLSearchParams({ escopo: 'todas', estado: 'calculada', q: busca });
    const { consulta, cabecalhos } = P.pedidoDaLista(entrada, encodeURIComponent(busca), SESSAO);
    const url = `/api/renovacoes?${consulta}`;
    const digitos = busca.replace(/\D/g, '');
    if (/(^|[?&])q=/.test(url)) erros.push(`'q' na query: ${url}`);
    if (digitos.length >= 6 && url.replace(/\D/g, '').includes(digitos)) erros.push(`os dígitos da busca na URL: ${url}`);
    if (/Exemplo|Concei/i.test(decodeURIComponent(url))) erros.push(`o nome na URL: ${url}`);
    // percent-encoded (o cabeçalho só leva Latin-1; o backend decodifica em `busca_do_cabecalho`)
    if (decodeURIComponent(cabecalhos['x-busca'] || '') !== esperado) erros.push(`x-busca = ${JSON.stringify(cabecalhos['x-busca'])} (esperado ${JSON.stringify(esperado)})`);
    if (!/escopo=todas/.test(url) || !/estado=calculada/.test(url)) erros.push(`os filtros que podem ir sumiram: ${url}`);
  }
  return erros;
}

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
console.log('\n[1] O proxy (app/api/renovacoes/pedido.ts, chamado de verdade): a busca vai no cabeçalho, nunca na query');
const fontePedido = ler('app/api/renovacoes/pedido.ts');
const P = carregarFonte(fontePedido, 'pedido.ts');
const erros = guardaDoProxy(P);
checar(erros.length === 0, 'CPF, CPF formatado e nome: zero dígitos/nome na URL, a busca inteira em x-busca', erros.join(' | '));
const { consulta: semBusca, cabecalhos: semCab } = P.pedidoDaLista(new URLSearchParams(), null, SESSAO);
checar(Object.keys(semCab).length === 0 && /company_id=empresa-a/.test(semBusca) && /escopo=minhas/.test(semBusca),
  'sem busca: nenhum cabeçalho extra; company_id/escopo da SESSÃO', `${semBusca} ${JSON.stringify(semCab)}`);
checar(P.lerBusca('%E0%A4%A') === '%E0%A4%A' && P.lerBusca('a\u0000b\u001Fc') === 'abc' && P.lerBusca('x'.repeat(300)).length === 120,
  'lerBusca: tolera percent-encoding quebrado, tira caractere de controle, corta em 120');
const acento = P.pedidoDaLista(new URLSearchParams(), encodeURIComponent('Conceição Ő'), SESSAO).cabecalhos['x-busca'];
checar(acento === encodeURIComponent('Conceição Ő') && /^[\x20-\x7E]+$/.test(acento),
  'x-busca vai percent-encoded (ASCII puro no cabeçalho) e volta igual, com acento e fora do Latin-1', String(acento));

// CONTROLE: a cópia mutada que põe a busca de volta na query TEM de ficar vermelha
const ancora = 'return { consulta: p.toString(), cabecalhos };';
checar(fontePedido.includes(ancora), 'a âncora da mutação existe no pedido.ts (senão o controle não prova nada)');
const mutado = carregarFonte(fontePedido.replace(ancora, `if (busca) p.set('q', busca); ${ancora}`), 'pedido-mutado.ts');
checar(guardaDoProxy(mutado).length > 0, 'CONTROLE: a mutação que devolve `q` à query deixa o guarda VERMELHO');

const rota = semComentario(ler('app/api/renovacoes/route.ts'));
checar(/pedidoDaLista\(/.test(rota) && /CABECALHO_DA_BUSCA/.test(rota) && !/['"]q['"]/.test(rota),
  'a rota usa o pedidoDaLista e o cabeçalho; nenhum "q" literal nela');

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
console.log('\n[2] A tela (AbaRenovacoes.tsx): a busca fica no estado e vai no cabeçalho — nunca na URL da página');
function guardaDaTela(fonte) {
  const c = semComentario(fonte);
  const erros = [];
  if (/\.set\(\s*['"]q['"]/.test(c)) erros.push("põe 'q' num URLSearchParams");
  // `mudar({ q: <algo> })` só é permitido com null (apagar a busca velha de um link antigo)
  for (const m of c.matchAll(/\bq\s*:\s*([^,}\n]+)/g)) if (m[1].trim() !== 'null') erros.push(`mudar({ q: ${m[1].trim()} })`);
  if (/busca\.get\(\s*['"]q['"]\s*\)/.test(c)) erros.push("lê a busca da URL (busca.get('q'))");
  if (!/CABECALHO_DA_BUSCA\]\s*:\s*encodeURIComponent\(/.test(c)) erros.push('não manda a busca no cabeçalho x-renovacoes-busca');
  return erros;
}
const tela = ler('components/aplicativos/renovacao/AbaRenovacoes.tsx');
const errosTela = guardaDaTela(tela);
checar(errosTela.length === 0, 'nenhum `q` com valor na URL; a busca vai no cabeçalho', errosTela.join(' | '));
let antiga = null;
try {
  antiga = execFileSync('git', ['show', '66feb3e:components/aplicativos/renovacao/AbaRenovacoes.tsx'], { cwd: RAIZ, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] });
} catch {
  antiga = null;
}
if (antiga) checar(guardaDaTela(antiga).length >= 2, 'CONTROLE: a tela de ANTES do conserto (66feb3e, o defeito J-B1) deixa o guarda VERMELHO', guardaDaTela(antiga).join(' | '));
else checar(guardaDaTela("mudar({ q: textoDaBusca.trim() || null }); p.set('q', q);").length >= 2, 'CONTROLE (sem git): o defeito sintético deixa o guarda VERMELHO');

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
console.log('\n[3] "Copiar a mensagem" copia a mensagem COMPLETA (`texto`), nunca a curta do link (RT-B2)');
function guardaDoCopiar(fonte) {
  const c = semComentario(fonte);
  const corpo = c.slice(c.indexOf('async function copiar'), c.indexOf('return {', c.indexOf('async function copiar')));
  const erros = [];
  if (!corpo) erros.push('copiar() não encontrado');
  if (/texto_curto/.test(corpo)) erros.push('copiar() lê texto_curto');
  if (!/j\.texto\b/.test(corpo)) erros.push('copiar() não lê j.texto');
  if (/texto_curto/.test(c)) erros.push('o hook lê texto_curto em algum lugar (o "sem telefone" também mostra a completa)');
  return erros;
}
const hook = ler('components/aplicativos/renovacao/useAcoesDaRenovacao.ts');
checar(guardaDoCopiar(hook).length === 0, 'copiar() e o "sem telefone" usam `texto` (a completa)', guardaDoCopiar(hook).join(' | '));
checar(guardaDoCopiar(hook.replace(/String\(j\.texto \|\| ''\)/g, "String(j.texto_curto || '')")).length > 0,
  'CONTROLE: trocar para texto_curto deixa o guarda VERMELHO');

console.log(falhas === 0 ? '\nA BUSCA FICA FORA DA URL E O COPIAR LEVA A MENSAGEM INTEIRA: TODOS OS GUARDAS VERDES\n' : `\n${falhas} GUARDA(S) VERMELHO(S)\n`);
process.exit(falhas === 0 ? 0 : 1);
