// SPEC-132-B · B3 — a aba Cotações: a busca ("Nome, placa ou CPF") NUNCA vai na URL (a regra J-B1 da 131-B, D-131-49),
// o "Copiar a mensagem" copia a mensagem COMPLETA (RT-B2) e as ações falam com /api/cotacoes. O MESMO guarda da aba
// Renovações (`renovacao/a-busca-nao-vai-na-url.test.mjs`), sobre os arquivos da cotação.
//
// Roda com: node components/aplicativos/cotacao/a-cotacao-nao-vaza.test.mjs
//
// COMO FUNCIONA — sem rede: `app/api/cotacoes/pedido.ts` é transpilado e CHAMADO de verdade com um CPF sintético; a tela
// (`AbaCotacoes.tsx`) e o hook das ações são lidos como texto. LINHA DE CONTROLE (CLAUDE.md §9.2/§9.3): cada guarda roda
// também contra a forma DEFEITUOSA e tem de ficar VERMELHO nela.

import fs from 'node:fs';
import path from 'node:path';
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

// 💭 CPF SINTÉTICO (dígitos verificadores válidos, de ninguém), uma placa e um nome de exemplo
const CPF = '52998224725';
const CPF_FORMATADO = '529.982.247-25';
const PLACA = 'ABC1D23';
const NOME = 'Cliente Exemplo da Conceição';
const SESSAO = { companyId: 'empresa-a', userId: 'pessoa-a', admin: false };

function guardaDoProxy(P) {
  const erros = [];
  for (const busca of [CPF, CPF_FORMATADO, NOME, PLACA]) {
    const entrada = new URLSearchParams({ escopo: 'todas', estado: 'pronta', q: busca });
    const { consulta, cabecalhos } = P.pedidoDaLista(entrada, encodeURIComponent(busca), SESSAO);
    const url = `/api/cotacoes?${consulta}`;
    const digitos = busca.replace(/\D/g, '');
    if (/(^|[?&])q=/.test(url)) erros.push(`'q' na query: ${url}`);
    if (digitos.length >= 6 && url.replace(/\D/g, '').includes(digitos)) erros.push(`os dígitos da busca na URL: ${url}`);
    if (/Exemplo|Concei|ABC1D23/i.test(decodeURIComponent(url))) erros.push(`o texto da busca na URL: ${url}`);
    if (decodeURIComponent(cabecalhos['x-busca'] || '') !== busca) erros.push(`x-busca = ${JSON.stringify(cabecalhos['x-busca'])}`);
    if (!/escopo=todas/.test(url) || !/estado=pronta/.test(url)) erros.push(`os filtros que podem ir sumiram: ${url}`);
  }
  return erros;
}

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
console.log('\n[1] O proxy (app/api/cotacoes/pedido.ts, chamado de verdade): a busca vai no cabeçalho, nunca na query');
const fontePedido = ler('app/api/cotacoes/pedido.ts');
const P = carregarFonte(fontePedido, 'pedido.ts');
const erros = guardaDoProxy(P);
checar(erros.length === 0, 'CPF, CPF formatado, nome e placa: nada da busca na URL, a busca inteira em x-busca', erros.join(' | '));
const { consulta: semBusca, cabecalhos: semCab } = P.pedidoDaLista(new URLSearchParams({ estado: 'qualquer' }), null, SESSAO);
checar(Object.keys(semCab).length === 0 && /company_id=empresa-a/.test(semBusca) && /escopo=minhas/.test(semBusca) && !/estado=/.test(semBusca),
  'sem busca: nenhum cabeçalho extra; company_id/escopo da SESSÃO; estado fora da lista não passa', `${semBusca}`);
checar(P.CABECALHO_DA_BUSCA === 'x-cotacoes-busca', 'o cabeçalho do navegador é o da cotação');

const ancora = 'return { consulta: p.toString(), cabecalhos };';
checar(fontePedido.includes(ancora), 'a âncora da mutação existe no pedido.ts (senão o controle não prova nada)');
const mutado = carregarFonte(fontePedido.replace(ancora, `if (busca) p.set('q', busca); ${ancora}`), 'pedido-mutado.ts');
checar(guardaDoProxy(mutado).length > 0, 'CONTROLE: a mutação que devolve `q` à query deixa o guarda VERMELHO');

const rota = semComentario(ler('app/api/cotacoes/route.ts'));
checar(/pedidoDaLista\(/.test(rota) && /CABECALHO_DA_BUSCA/.test(rota) && !/['"]q['"]/.test(rota),
  'a rota usa o pedidoDaLista e o cabeçalho; nenhum "q" literal nela');
const comum = semComentario(ler('app/api/cotacoes/comum.ts'));
checar(/company_id: s\.companyId/.test(comum) && /user_id: s\.userId/.test(comum) && !/corpo\?\.company_id|corpo\.company_id/.test(comum),
  'as ações mandam company_id/user_id da SESSÃO (o corpo do navegador só passa `via`)');

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
console.log('\n[2] A tela (AbaCotacoes.tsx): a busca fica no estado e vai no cabeçalho — nunca na URL da página');
function guardaDaTela(fonte) {
  const c = semComentario(fonte);
  const e = [];
  if (/\.set\(\s*['"]q['"]/.test(c)) e.push("põe 'q' num URLSearchParams");
  for (const m of c.matchAll(/\bq\s*:\s*([^,}\n]+)/g)) if (m[1].trim() !== 'null') e.push(`mudar({ q: ${m[1].trim()} })`);
  if (/busca\.get\(\s*['"]q['"]\s*\)/.test(c)) e.push("lê a busca da URL (busca.get('q'))");
  if (!/CABECALHO_DA_BUSCA\]\s*:\s*encodeURIComponent\(/.test(c)) e.push('não manda a busca no cabeçalho');
  if (!/from '@\/app\/api\/cotacoes\/pedido'/.test(c)) e.push('o cabeçalho não é o da cotação');
  return e;
}
const tela = ler('components/aplicativos/cotacao/AbaCotacoes.tsx');
checar(guardaDaTela(tela).length === 0, 'nenhum `q` com valor na URL; a busca vai no cabeçalho da cotação', guardaDaTela(tela).join(' | '));
checar(guardaDaTela("mudar({ q: textoDaBusca.trim() || null }); p.set('q', q);").length >= 2,
  'CONTROLE: o defeito sintético (a busca na URL) deixa o guarda VERMELHO');
checar(guardaDaTela(tela.replace("from '@/app/api/cotacoes/pedido'", "from '@/app/api/renovacoes/pedido'")).length >= 1,
  'CONTROLE: o cabeçalho da Renovação no lugar do da cotação deixa o guarda VERMELHO');

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
console.log('\n[3] As ações: falam com /api/cotacoes e "Copiar a mensagem" copia a COMPLETA (`texto`), nunca a curta');
function guardaDoHook(fonte) {
  const c = semComentario(fonte);
  const corpo = c.slice(c.indexOf('async function copiar'), c.indexOf('return {', c.indexOf('async function copiar')));
  const e = [];
  if (!/fetch\(`\/api\/cotacoes\//.test(c) || /\/api\/renovacoes/.test(c)) e.push('o hook não fala (só) com /api/cotacoes');
  if (!corpo) e.push('copiar() não encontrado');
  if (/texto_curto/.test(c)) e.push('o hook lê texto_curto');
  if (!/j\.texto\b/.test(corpo)) e.push('copiar() não lê j.texto');
  return e;
}
const hook = ler('components/aplicativos/cotacao/useAcoesDaCotacao.ts');
checar(guardaDoHook(hook).length === 0, 'o hook usa /api/cotacoes e `texto` (a completa)', guardaDoHook(hook).join(' | '));
checar(guardaDoHook(hook.replace(/String\(j\.texto \|\| ''\)/g, "String(j.texto_curto || '')")).length > 0,
  'CONTROLE: trocar para texto_curto deixa o guarda VERMELHO');
checar(guardaDoHook(hook.replace('/api/cotacoes/', '/api/renovacoes/')).length > 0,
  'CONTROLE: o hook apontando para a Renovação deixa o guarda VERMELHO');

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
console.log('\n[4] Nenhum telefone na tela: a aba e o detalhe nunca mostram nem guardam o número do cliente');
const telas = ['AbaCotacoes.tsx', 'DetalheDaCotacao.tsx', 'tipos.ts', 'useAcoesDaCotacao.ts'].map((f) => semComentario(ler(`components/aplicativos/cotacao/${f}`)));
const comTelefone = telas.filter((c) => /telefone|celular_do_cliente|localStorage/i.test(c.replace(/sem_telefone/g, '')));
checar(comTelefone.length === 0, 'nenhum campo de telefone e nenhum localStorage nas telas da cotação');
checar(/telefone/i.test('cliente.telefone'), 'CONTROLE: o detector acha um telefone quando ele aparece');

console.log(falhas === 0 ? '\nCOTAÇÕES: A BUSCA FICA FORA DA URL, NADA VAZA E O COPIAR LEVA A MENSAGEM INTEIRA: TODOS OS GUARDAS VERDES\n' : `\n${falhas} GUARDA(S) VERMELHO(S)\n`);
process.exit(falhas === 0 ? 0 : 1);
