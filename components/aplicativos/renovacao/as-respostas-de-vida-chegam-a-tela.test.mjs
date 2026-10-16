// SPEC-129-D · conserto K2 (juiz B1 · red team B3) — o detalhe de uma renovação de VIDA pendente MOSTRA as perguntas e
// o formulário "As respostas do cliente" — e SÓ nela; nada vem marcado; o proxy só repassa as respostas, com a empresa e
// a pessoa da SESSÃO.
//
// Roda com: node components/aplicativos/renovacao/as-respostas-de-vida-chegam-a-tela.test.mjs
//
// COMO FUNCIONA — sem rede: os módulos PUROS (`regrasDasRespostas.ts` da tela e `app/api/renovacoes/respostas.ts` do
// proxy) são transpilados com o TypeScript do projeto e CHAMADOS de verdade; o detalhe e o formulário (.tsx) são lidos
// como texto (o que eles renderizam e de onde vem o estado inicial).
//
// LINHA DE CONTROLE (CLAUDE.md §9.2/§9.3): cada guarda roda também contra a forma DEFEITUOSA (o rascunho com "Não"
// pré-marcado, o formulário sem a condição, o proxy que repassa o company_id do navegador) e tem de ficar VERMELHO.

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
  new Function('require', 'module', 'exports', js)(() => { throw new Error(`${nome} tem de ser puro`); }, mod, mod.exports);
  return mod.exports;
}

const ler = (rel) => fs.readFileSync(path.join(RAIZ, rel), 'utf8');
const semComentario = (fonte) =>
  fonte.split('\n').filter((l) => !/^\s*(\/\/|\*|\/\*)/.test(l)).join('\n').replace(/\{\/\*[\s\S]*?\*\/\}/g, '');

// o detalhe como a API o devolve (o JSON de `test_spec129d_conserto_app.py`): vida pendente, as três perguntas
const VIDA_PENDENTE = {
  estado: 'pendente',
  perguntas: ['O cliente fuma?', 'Qual a renda mensal do cliente?', 'Pratica esporte radical? Qual?'],
  avisos: ['Algumas coberturas da apólice não foram reconhecidas — confira antes de cotar.'],
  respostas_de_vida: { campos: ['fumante', 'renda_mensal', 'esporte_radical'], aviso: 'Estas respostas são do cliente: confirme com ele.', ja_respondido: false },
};

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
console.log('\n[1] As regras do formulário (regrasDasRespostas.ts, chamado de verdade)');
const fonteTela = ler('components/aplicativos/renovacao/regrasDasRespostas.ts');
const T = carregarFonte(fonteTela, 'regrasDasRespostas.ts');

function guardaDoFormulario(T) {
  const erros = [];
  if (!T.mostraFormulario(VIDA_PENDENTE)) erros.push('não mostra na vida pendente');
  for (const [nome, d] of [
    ['calculada', { ...VIDA_PENDENTE, estado: 'calculada' }],
    ['pronta', { ...VIDA_PENDENTE, estado: 'pronta' }],
    ['sem campos (o AUTO)', { estado: 'pendente', respostas_de_vida: null }],
    ['sem a chave', { estado: 'pendente' }],
    ['campos vazios', { ...VIDA_PENDENTE, respostas_de_vida: { ...VIDA_PENDENTE.respostas_de_vida, campos: [] } }],
  ]) if (T.mostraFormulario(d)) erros.push(`mostra em: ${nome}`);
  const vazio = T.rascunhoVazio();
  if (vazio.fumante !== null || vazio.esporte_radical !== null || vazio.renda_mensal !== '' || vazio.profissao_texto !== '') {
    erros.push(`o rascunho nasce com valor: ${JSON.stringify(vazio)}`);
  }
  // nada respondido → nada sai (nunca um "não" por padrão)
  const r0 = T.corpoDoRascunho(vazio, VIDA_PENDENTE.respostas_de_vida.campos);
  if (r0.ok) erros.push(`o rascunho vazio virou corpo: ${JSON.stringify(r0.corpo)}`);
  return erros;
}
const errosForm = guardaDoFormulario(T);
checar(errosForm.length === 0, 'o formulário aparece SÓ na vida pendente com campos; nasce VAZIO; vazio não vira corpo', errosForm.join(' | '));

const ok = T.corpoDoRascunho({ fumante: false, renda_mensal: '8.765,43', esporte_radical: false, profissao_texto: '' },
  VIDA_PENDENTE.respostas_de_vida.campos);
checar(ok.ok && JSON.stringify(ok.corpo) === JSON.stringify({ fumante: false, renda_mensal: 8765.43, esporte_radical: false }),
  'respondido: o "Não" dito vai como false e a renda em reais vira número (só os campos pedidos)', JSON.stringify(ok));
checar(T.lerRenda('8500') === 8500 && T.lerRenda('R$ 8.500') === 8500 && T.lerRenda('8.500,5') === 8500.5
  && T.lerRenda('-3') === null && T.lerRenda('abc') === null && T.lerRenda('') === null,
  'lerRenda: 8500 · R$ 8.500 · 8.500,5; negativo, texto e vazio → null (nunca um número inventado)');
const semRenda = T.corpoDoRascunho({ fumante: true, renda_mensal: '', esporte_radical: false, profissao_texto: '' }, ['fumante', 'renda_mensal']);
checar(!semRenda.ok && /renda/i.test(semRenda.erro), 'falta a renda → o erro em português, nada sai', JSON.stringify(semRenda));

// CONTROLE: o rascunho com "Não" pré-marcado (o defeito que a SPEC proíbe) deixa o guarda VERMELHO
const ancora = 'return { fumante: null, renda_mensal: \'\', esporte_radical: null, profissao_texto: \'\' };';
checar(fonteTela.includes(ancora), 'a âncora da mutação existe (senão o controle não prova nada)');
const mutado = carregarFonte(fonteTela.replace(ancora, "return { fumante: false, renda_mensal: '', esporte_radical: false, profissao_texto: '' };"), 'mutado.ts');
checar(guardaDoFormulario(mutado).length > 0, 'CONTROLE: "Não" pré-marcado no rascunho deixa o guarda VERMELHO');
const ancoraMostra = "return d.estado === 'pendente' &&";
checar(fonteTela.includes(ancoraMostra), 'a âncora da condição existe');
const semCondicao = carregarFonte(fonteTela.replace(ancoraMostra, 'return true ||'), 'sem-condicao.ts');
checar(guardaDoFormulario(semCondicao).length > 0, 'CONTROLE: o formulário sem a condição deixa o guarda VERMELHO');

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
console.log('\n[2] O detalhe (DetalheDaRenovacao.tsx) e o formulário (RespostasDeVida.tsx): o que chega à tela');
function guardaDoDetalhe(fonte, form) {
  const c = semComentario(fonte);
  const f = semComentario(form);
  const erros = [];
  if (!/d\.perguntas/.test(c) || !/perguntas\.map\(/.test(c)) erros.push('o detalhe não renderiza d.perguntas');
  if (!/d\.avisos/.test(c) || !/avisos\.map\(/.test(c)) erros.push('o detalhe não renderiza d.avisos');
  if (!/\{mostraFormulario\(d\)\s*&&[^}]*<RespostasDeVida/.test(c)) erros.push('o formulário não está atrás de mostraFormulario(d)');
  if (/<RespostasDeVida/.test(c.replace(/\{mostraFormulario\(d\)\s*&&[^}]*<RespostasDeVida/, ''))) erros.push('há um <RespostasDeVida> fora da condição');
  if (!/useState<Rascunho>\(rascunhoVazio\)/.test(f)) erros.push('o formulário não nasce do rascunhoVazio');
  if (/defaultChecked|defaultValue|checked=\{true\}|aria-checked=\{true\}/.test(f)) erros.push('valor pré-marcado no formulário');
  if (!/pedido\.aviso/.test(f)) erros.push('o aviso "Estas respostas são do cliente" não aparece');
  if (/localStorage|sessionStorage|console\./.test(f)) erros.push('o formulário guarda/loga a resposta');
  if (!/h-11/.test(f)) erros.push('os alvos não têm 44 px');
  if (!/\/respostas-de-vida/.test(f)) erros.push('não posta na rota da sessão');
  return erros;
}
const detalhe = ler('components/aplicativos/renovacao/DetalheDaRenovacao.tsx');
const form = ler('components/aplicativos/renovacao/RespostasDeVida.tsx');
const errosDet = guardaDoDetalhe(detalhe, form);
checar(errosDet.length === 0, 'perguntas e avisos renderizados; o formulário só atrás de mostraFormulario(d), vazio, com o aviso', errosDet.join(' | '));
checar(guardaDoDetalhe(detalhe.replace(/\{mostraFormulario\(d\)\s*&&\s*d\.respostas_de_vida\s*&&/, '{d.respostas_de_vida &&'), form).length > 0,
  'CONTROLE: o formulário sem a condição no detalhe deixa o guarda VERMELHO');
checar(guardaDoDetalhe(detalhe, form.replace('useState<Rascunho>(rascunhoVazio)', 'useState<Rascunho>({ ...rascunhoVazio(), fumante: false })')).length > 0,
  'CONTROLE: o formulário com "Não" pré-marcado deixa o guarda VERMELHO');
checar(guardaDoDetalhe(detalhe.replace(/perguntas\.map\(/g, 'nada.map('), form).length > 0,
  'CONTROLE: o detalhe sem renderizar as perguntas deixa o guarda VERMELHO');

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
console.log('\n[3] O proxy (app/api/renovacoes/respostas.ts, chamado de verdade): a empresa e a pessoa da SESSÃO');
const fonteProxy = ler('app/api/renovacoes/respostas.ts');
const P = carregarFonte(fonteProxy, 'respostas.ts');
const SESSAO = { companyId: 'empresa-a', userId: 'pessoa-a' };
function guardaDoProxy(P) {
  const erros = [];
  const c = P.corpoDasRespostas({ company_id: 'empresa-b', user_id: 'pessoa-b', estado: 'pronta', coluna: 'fechada',
    fumante: false, renda_mensal: 8765.43, esporte_radical: false }, SESSAO);
  if (c.company_id !== 'empresa-a' || c.user_id !== 'pessoa-a') erros.push(`a empresa/pessoa do navegador passou: ${JSON.stringify(c)}`);
  if ('estado' in c || 'coluna' in c) erros.push(`chave estranha atravessou: ${JSON.stringify(c)}`);
  if (c.fumante !== false || c.esporte_radical !== false || c.renda_mensal !== 8765.43) erros.push(`as respostas não passaram: ${JSON.stringify(c)}`);
  const t = P.corpoDasRespostas({ fumante: 'nao', renda_mensal: '8765', esporte_radical: null }, SESSAO);
  if ('fumante' in t || 'renda_mensal' in t || 'esporte_radical' in t) erros.push(`tipo errado virou resposta: ${JSON.stringify(t)}`);
  return erros;
}
checar(guardaDoProxy(P).length === 0, 'a sessão vence o corpo; nenhuma chave estranha; tipo errado não vira resposta', guardaDoProxy(P).join(' | '));
const ancoraProxy = 'return { ...saida, company_id: s.companyId, user_id: s.userId };';
checar(fonteProxy.includes(ancoraProxy), 'a âncora do proxy existe');
const proxyMutado = carregarFonte(fonteProxy.replace(ancoraProxy, 'return { company_id: s.companyId, user_id: s.userId, ...saida, ...(corpo as object) };'), 'proxy-mutado.ts');
checar(guardaDoProxy(proxyMutado).length > 0, 'CONTROLE: o proxy que repassa o corpo do navegador deixa o guarda VERMELHO');
const rota = semComentario(ler('app/api/renovacoes/[id]/respostas-de-vida/route.ts'));
checar(/corpoDasRespostas\(corpo, s\)/.test(rota) && /sessaoDaCorretora\(\)/.test(rota) && /assertSameOrigin\(req\)/.test(rota),
  'a rota usa a sessão, a mesma origem e o corpoDasRespostas');

console.log(falhas === 0 ? '\nAS PERGUNTAS CHEGAM À TELA E A RESPOSTA VOLTA PELA SESSÃO: TODOS OS GUARDAS VERDES\n' : `\n${falhas} GUARDA(S) VERMELHO(S)\n`);
process.exit(falhas === 0 ? 0 : 1);
