#!/usr/bin/env node
/**
 * A ROTINA MORA DENTRO DO AUXILIAR — SPEC-078 Blocos C.4, D e E.
 *
 * 📊 O achado que motivou tudo isto, medido em 17/08/2026: a SPEC-064 §B.3
 * mandou absorver QUATRO rotas. Três viraram stub de redirect com a frase
 * "O CONTEUDO FOI ABSORVIDO" — `galeria`, `meus`, `execucoes`. A quarta,
 * `auxiliares/rotinas`, seguiu viva com 706 linhas e um botão "Nova rotina"
 * numa lista sem dono. Foi dele que saiu a rotina órfã das 13:01 daquele dia.
 *
 * Este guarda existe para que a quarta não volte. Ele lê a FONTE — não há como
 * um teste de comportamento perceber que uma tela reapareceu.
 *
 * Rode: `npm run test:rotina-no-auxiliar`
 */
import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const RAIZ = join(dirname(fileURLToPath(import.meta.url)), '..');
const ler = (rel) => readFileSync(join(RAIZ, rel), 'utf8');

/**
 * O arquivo SEM comentários.
 *
 * 🔴 Isto não é detalhe de implementação, é a diferença entre guardar o motor e
 * guardar a etiqueta. Duas asserções deste arquivo ficaram vermelhas na
 * primeira rodada porque casaram com as palavras "Nova rotina" e "0=seg"
 * dentro de comentários que EXPLICAM que aquilo foi removido. O código estava
 * certo; o guarda é que lia prosa.
 *
 * O mesmo defeito apareceu na auditoria do Bloco B, num guarda que casava com
 * um rótulo de tela em vez do tratador. Vale a regra: guarda de fonte lê
 * CÓDIGO. Onde a intenção for verificar o texto de um comentário, isso tem de
 * ser dito com todas as letras.
 */
const semComentarios = (src) =>
  src
    .replace(/\/\*[\s\S]*?\*\//g, '')     // /* … */ e /** … */
    .replace(/\{\/\*[\s\S]*?\*\/\}/g, '') // {/* … */} do JSX
    .replace(/^\s*\/\/.*$/gm, '')         // // linha inteira
    .replace(/\s\/\/[^\n'"`]*$/gm, '');   // // no fim da linha

const STUB = 'app/dashboard/auxiliares/rotinas/page.tsx';
const PAINEL = 'components/auxiliares/PainelDeRotinas.tsx';
const DETALHE = 'app/dashboard/auxiliares/[slug]/AuxiliarDetalheClient.tsx';
const API = 'app/api/dashboard/rotinas/route.ts';
const REENVIO = 'app/api/dashboard/auxiliaries/cobranca/liberar-reenvio/route.ts';
const MOTOR = 'backend/app/services/billing_collection.py';

let falhas = 0;
const conferir = (nome, cond, detalhe = '') => {
  if (cond) { console.log(`  [ok] ${nome}`); return true; }
  falhas++; console.log(`  [FALHOU] ${nome}${detalhe ? '\n      ' + detalhe : ''}`); return false;
};

// ---------------------------------------------------------------------------
console.log('\n1 - A quarta rota foi absorvida, como as tres irmas');

const stub = ler(STUB);
conferir('a rota virou stub (menos de 60 linhas)', stub.split('\n').length < 60,
  `${stub.split('\n').length} linhas`);
conferir('e ela REDIRECIONA em vez de renderizar', /redirect\(/.test(stub));
conferir('com a mesma frase das irmas: "ABSORVIDO"', /ABSORVIDO/i.test(stub));
conferir('o botao "Nova rotina" NAO existe mais na rota solta',
  !/Nova rotina/.test(semComentarios(stub)),
  'era ele que criava rotina sem dono');

for (const irma of ['galeria', 'meus', 'execucoes']) {
  const p = `app/dashboard/auxiliares/${irma}/page.tsx`;
  if (existsSync(join(RAIZ, p))) {
    conferir(`CONTROLE: a irma \`${irma}\` continua sendo um stub (o padrao existe)`,
      /redirect\(/.test(ler(p)));
  }
}

// ---------------------------------------------------------------------------
console.log('\n2 - O painel mora dentro do Auxiliar, e sabe de quem e');

const painel = ler(PAINEL);
const detalhe = ler(DETALHE);

conferir('a tela do Auxiliar RENDERIZA o painel (nao linka para outra pagina)',
  /<PainelDeRotinas/.test(detalhe) && /from '@\/components\/auxiliares\/PainelDeRotinas'/.test(detalhe));
conferir('e nao sobrou link para a rota absorvida',
  !/auxiliares\/rotinas\?auxiliar=/.test(detalhe),
  'o link antigo levava a lista de TODAS as rotinas da corretora');
conferir('o painel recebe o slug do Auxiliar', /auxiliarSlug/.test(painel));
conferir('e MANDA o dono ao criar (ONTOLOGIA:51)', /auxiliar:\s*auxiliarSlug/.test(painel));
conferir('a listagem pede so as rotinas DELE', /rotinas\?auxiliar=/.test(painel));

const api = ler(API);
conferir('a API filtra por dono quando recebe `?auxiliar=`',
  /searchParams\.get\('auxiliar'\)/.test(api) && /eq\('tenant_auxiliary_id'/.test(api));
conferir('slug inexistente devolve VAZIO, nunca a lista inteira',
  /__inexistente__/.test(api),
  'um filtro que falha para o aberto mostraria as rotinas de todos');
conferir('o create grava `tenant_auxiliary_id`', /tenant_auxiliary_id:\s*dono\.id/.test(api));

// ---------------------------------------------------------------------------
console.log('\n3 - Nenhum campo do modal existe sem ter efeito');

conferir('`instructions` e LEITURA em Auxiliar com motor proprio',
  /billingConfig \?[\s\S]{0,400}?whitespace-pre-wrap/.test(painel),
  'o campo e inerte em cobranca: routine_engine desvia antes do prompt');
conferir('`knowledge` SUMIU da cobranca', /\{!billingConfig && \([\s\S]{0,300}?Conhecimento/.test(painel));
conferir('o nome da rotina e o do Auxiliar (fixo)', /name:\s*auxiliarNome/.test(painel));
conferir('e o campo de nome nao e mais editavel',
  !/setForm\(\{ \.\.\.form, name: e\.target\.value \}\)/.test(painel));

conferir('o seletor de dias substituiu a caixa de texto',
  /DIAS_DA_SEMANA\.map/.test(painel) && !/0=seg/.test(semComentarios(painel)));
conferir('a mensagem mostra o PADRAO quando nao ha salva',
  /\|\| MENSAGEM_PADRAO/.test(painel),
  'o textarea abria vazio e o corretor nunca via o que ia sair');
conferir('e avisa sobre chave que nao existe',
  /chavesDesconhecidas/.test(painel),
  'chave errada SOME da frase em vez de aparecer como texto');
conferir('existe pre-visualizacao da mensagem real', /previaDaMensagem/.test(painel));

conferir('o erro aparece DENTRO do modal', /erroDoModal/.test(painel));
conferir('e o botao trava sem numero de WhatsApp',
  /form\.number\.replace\(\/\\D\/g, ''\)\.length < 10/.test(painel));

// ---------------------------------------------------------------------------
console.log('\n4 - O seletor so oferece modo que TEM motor');

// 🔴 Estas tres assercoes foram REESCRITAS depois que a mutacao M2 ficou VERDE.
//
// A versao anterior testava `!/value="live"/` — o formato do `<option>` ANTIGO,
// que ja nao existe — e contava quantas vezes 'test' e 'none' apareciam. Botar
// `{ valor: 'live' }` de volta em MODOS_COM_MOTOR nao mexia em nenhuma das
// duas: o guarda passava e o seletor oferecia um modo sem motor.
//
// Agora ele LE a lista de verdade e compara o conjunto inteiro. Um valor novo
// ali dentro fica vermelho, seja qual for.
const modosDeclarados = Array.from(
  (painel.match(/MODOS_COM_MOTOR = \[[\s\S]*?\] as const;/) || [''])[0]
    .matchAll(/valor:\s*'([a-z_]+)'/g),
).map((m) => m[1]);

conferir('a lista de modos foi encontrada', modosDeclarados.length > 0,
  'sem isto as duas assercoes abaixo passariam sobre uma lista vazia');
conferir('o seletor oferece EXATAMENTE `test` e `none`',
  JSON.stringify([...modosDeclarados].sort()) === JSON.stringify(['none', 'test']),
  `oferece: ${modosDeclarados.join(', ') || '(nada)'}`);
conferir('nenhum modo sem motor (`live`, `approval`) esta na lista',
  !modosDeclarados.includes('live') && !modosDeclarados.includes('approval'),
  `oferece: ${modosDeclarados.join(', ')}`);
conferir('e o `<option>` antigo com `live` tambem nao voltou',
  !/value="live"/.test(semComentarios(painel)) && !/value="approval"/.test(semComentarios(painel)));
conferir('o campo `approval_required` sumiu da tela',
  !/setBillingConfig\(\{ approval_required/.test(painel));

// 🔴 CONTROLE do bloco 4 — as assercoes acima sao TODAS negativas ("nao
// existe"), e um arquivo vazio passaria em todas. Esta linha exige que o
// seletor de modo de envio EXISTA e esteja ligado ao motor.
conferir('CONTROLE: o seletor de modo de envio existe e grava `send_mode`',
  /setBillingConfig\(\{ send_mode: e\.target\.value \}\)/.test(painel)
  && /MODOS_COM_MOTOR\.map/.test(painel));

// ---------------------------------------------------------------------------
console.log('\n5 - O reenvio de teste nunca toca em envio real');

const reenvio = ler(REENVIO);
conferir('a rota de liberar reenvio existe', reenvio.length > 0);
conferir('ela apaga SO `send_mode = test`', /\.eq\('send_mode', 'test'\)/.test(reenvio));
conferir('e e escopada por corretora (§7)', /\.eq\('company_id', ctx\.companyId\)/.test(reenvio));

// 🔴 CONTROLE — prova que o guarda acima detecta a remocao do filtro. Sem
// isto, um `.eq` que sumisse passaria porque a string ainda apareceria num
// comentario em outro lugar do arquivo.
const envenenado = reenvio.replace(".eq('send_mode', 'test')", ".eq('x','y')");
conferir('CONTROLE: o guarda acusa se o filtro de `test` for removido',
  !/\.eq\('send_mode', 'test'\)/.test(envenenado));

// A chave de dedup do motor precisa continuar sendo a que a rota apaga.
const motor = ler(MOTOR);
conferir('a chave de dedup do motor continua `(company_id, recibo, send_mode)`',
  /on_conflict="company_id,recibo,send_mode"/.test(motor),
  'se ela mudar, o botao de reenvio passa a limpar a coisa errada');

// ---------------------------------------------------------------------------
console.log(falhas === 0
  ? '\nTODOS OS GUARDAS VERDES\n'
  : `\n${falhas} GUARDA(S) VERMELHO(S)\n`);
process.exit(falhas === 0 ? 0 : 1);
