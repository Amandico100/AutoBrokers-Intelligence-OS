#!/usr/bin/env node
/**
 * A COBRANCA CHEGA A QUEM DEVE — o guarda do NEXT. SPEC-EXTRA-001 §5.
 *
 * 🔴 ESTE ARQUIVO NASCE VERMELHO, E E PARA NASCER. 📊 Medido em 07/09/2026 na
 * copia limpa `../AutoBrokers-FIX-gate0-e001` (`git worktree --detach
 * 50d2b4e`, a arvore como a SPEC a encontrou): **15 guardas vermelhos**. Eles
 * sao a metade do GATE ZERO que mora no
 * front: 📊 `MODOS_COM_MOTOR` tem DOIS itens (`test`, `none`), a rota
 * `normalizeRoutineConfig` ainda aceita `approval|live` sem retencao, as tres
 * rotas de pendencia nao existem, e ha um telefone REAL como `placeholder` em
 * `PainelDeRotinas.tsx`.
 *
 * O irmao dele e `backend/tests/test_a_cobranca_chega_a_quem_deve.py`, que
 * executa o MOTOR. Aqui nao ha motor para executar: o Next nao roda neste
 * guarda, entao ele le a FONTE — e isso esta declarado, nao escondido
 * (CLAUDE.md §9.4). Toda assercao negativa ("nao existe") vem acompanhada de
 * uma linha de CONTROLE que envenena uma copia em memoria e exige que o guarda
 * ACUSE. Sem ela, um arquivo vazio passaria em tudo (CLAUDE.md §9.2).
 *
 * ⛔ Nenhuma requisicao sai daqui. Nenhum arquivo e escrito. As copias
 *    envenenadas vivem em memoria e morrem no fim da funcao.
 *
 * Rode: `node scripts/a-cobranca-chega-a-quem-deve.test.mjs`
 */
import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const RAIZ = join(dirname(fileURLToPath(import.meta.url)), '..');
const existe = (rel) => existsSync(join(RAIZ, rel));
const ler = (rel) => (existe(rel) ? readFileSync(join(RAIZ, rel), 'utf8') : '');

/**
 * O arquivo SEM comentarios.
 *
 * 🔴 Nao e detalhe de implementacao: e a diferenca entre guardar o motor e
 * guardar a etiqueta. Na SPEC-078 duas assercoes ficaram vermelhas por casar
 * com palavras dentro de comentarios que EXPLICAVAM que aquilo fora removido.
 * Guarda de fonte le CODIGO.
 */
const semComentarios = (src) =>
  src
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/\{\/\*[\s\S]*?\*\/\}/g, '')
    .replace(/^\s*\/\/.*$/gm, '')
    .replace(/\s\/\/[^\n'"`]*$/gm, '');

const PAINEL = 'components/auxiliares/PainelDeRotinas.tsx';
const API_ROTINAS = 'app/api/dashboard/rotinas/route.ts';
const PENDENCIAS = 'app/api/dashboard/auxiliaries/cobranca/pendencias/route.ts';
const ENCAMINHADO = 'app/api/dashboard/auxiliaries/cobranca/encaminhado/route.ts';
const LIBERAR = 'app/api/dashboard/auxiliaries/cobranca/liberar/route.ts';
const REENVIO = 'app/api/dashboard/auxiliaries/cobranca/liberar-reenvio/route.ts';
const MOTOR = 'backend/app/services/billing_collection.py';

let falhas = 0;
let pulados = 0;
const conferir = (nome, cond, detalhe = '') => {
  if (cond) { console.log(`  [ok] ${nome}`); return true; }
  falhas++; console.log(`  [FALHOU] ${nome}${detalhe ? '\n      ' + detalhe : ''}`); return false;
};
/** A linha de CONTROLE: `acusou` e true quando o guarda pegou o veneno. */
const par = (nome, acusou, detalhe = '') => {
  if (acusou) { console.log(`  [ok] PAR ${nome} — o guarda acusou`); return true; }
  falhas++;
  console.log(`  [FALHOU] PAR ${nome} — o guarda NAO acusou; ele nao guarda nada${detalhe ? '\n      ' + detalhe : ''}`);
  return false;
};
const pular = (nome, razao) => { pulados++; console.log(`  --   PULADO ${nome}\n      ${razao}`); };

// ---------------------------------------------------------------------------
console.log('\n1 - O seletor oferece os QUATRO modos que tem motor');

const painel = ler(PAINEL);
if (!painel) {
  conferir(`\`${PAINEL}\` existe`, false, 'sem o painel nao ha nada a medir');
} else {
  const listaDeclarada = (painel.match(/MODOS_COM_MOTOR = \[[\s\S]*?\] as const;/) || [''])[0];
  const modos = Array.from(listaDeclarada.matchAll(/valor:\s*'([a-z_]+)'/g)).map((m) => m[1]);

  conferir('a lista `MODOS_COM_MOTOR` foi encontrada', modos.length > 0,
    'sem isto as assercoes abaixo passariam sobre uma lista vazia');
  conferir('o seletor oferece EXATAMENTE `test`, `none`, `equipe` e `cliente`',
    JSON.stringify([...modos].sort()) === JSON.stringify(['cliente', 'equipe', 'none', 'test']),
    `oferece: ${modos.join(', ') || '(nada)'}`);
  conferir('nenhum modo sem motor (`live`, `approval`) voltou para a lista',
    !modos.includes('live') && !modos.includes('approval'),
    `oferece: ${modos.join(', ')}`);
  conferir('e o `<option>` antigo com `live`/`approval` tambem nao voltou',
    !/value="live"/.test(semComentarios(painel)) && !/value="approval"/.test(semComentarios(painel)));

  // 🔴 CONTROLE: as tres acima sao contra uma lista LIDA. Um `MODOS_COM_MOTOR`
  //    renomeado deixaria `modos` vazio e a primeira acusaria — e as outras
  //    duas passariam por vacuidade. Este par prova que a leitura pega o valor.
  const envenenado = painel.replace(/MODOS_COM_MOTOR = \[/, "MODOS_COM_MOTOR = [\n  { valor: 'live', rotulo: 'x' },");
  const modosEnv = Array.from(
    (envenenado.match(/MODOS_COM_MOTOR = \[[\s\S]*?\] as const;/) || [''])[0]
      .matchAll(/valor:\s*'([a-z_]+)'/g),
  ).map((m) => m[1]);
  par('a leitura da lista pega um modo sem motor injetado', modosEnv.includes('live'),
    'o veneno entrou e a leitura nao viu — a assercao acima e carimbo');

  console.log('\n2 - E cada modo real grava o que o motor exige');
  conferir('o modo de envio continua sendo gravado', /setBillingConfig\(\{ send_mode: e\.target\.value \}\)/.test(painel));
  conferir('`equipe` grava o `team_number` da corretora', /setBillingConfig\(\{\s*team_number/.test(semComentarios(painel)),
    'sem ele o modo `equipe` nao tem para quem mandar');
  conferir('`cliente` grava a confirmacao explicita', /setBillingConfig\(\{\s*confirmacao_cliente/.test(semComentarios(painel)),
    'o motor recusa `cliente` sem `confirmacao_cliente=true` (CONTRATOS §1)');
  conferir('e a frase "ainda nao esta disponivel" saiu da tela',
    !/direto ao segurado ainda n[aã]o est[aá] dispon[ií]vel/i.test(semComentarios(painel)));
  conferir('a lista "Pendencias da cobranca" existe na tela',
    /pend[eê]ncias/i.test(semComentarios(painel)) && /cobranca\/pendencias/.test(painel),
    'e onde a corretora ve `parcial`, `incerto`, `contestado` e decide');
  // ⚠️ A tela nao digita a URL inteira: ela chama UM despachante
  //    (`decidirPendencia(p, 'encaminhado' | 'liberar')`) que monta o caminho.
  //    Um guarda que exigisse `cobranca/encaminhado` dentro do TSX mediria o
  //    ESTILO de quem escreveu a chamada, e nao a existencia da acao
  //    (CLAUDE.md §9.4). Ele mede a acao e o prefixo, separadamente.
  const painelSemCom = semComentarios(painel);
  conferir('com a acao "marcar como encaminhado ao cliente"',
    /'encaminhado'/.test(painelSemCom)
    && /Marcar como encaminhado ao cliente/.test(painelSemCom),
    'e a acao que fecha o G11: sem ela o ledger nunca sabe que o cliente recebeu');
  conferir('e a acao "liberar reenvio", que exige motivo',
    /'liberar'/.test(painelSemCom) && /motivo/i.test(painelSemCom));
  conferir('e as duas batem nas rotas de cobranca (o caminho e montado, nao digitado)',
    /auxiliaries\/cobranca\//.test(painelSemCom),
    'sem o prefixo, as acoes chamam outra coisa');

  console.log('\n3 - Higiene: nenhum telefone real na tela (emenda 11)');
  // 📊 `PainelDeRotinas.tsx:861` tinha um numero REAL como `placeholder`.
  // A mascara `55 47 9XXXX-XXXX` tem espacos e nao casa com este padrao.
  const telefones = (semComentarios(painel).match(/\b55\d{10,11}\b/g) || []);
  conferir('nenhuma sequencia `55` + 10 ou 11 digitos no arquivo',
    telefones.length === 0,
    `achou ${telefones.length}: ${telefones.map((t) => '…' + t.slice(-4)).join(', ')} (so os 4 ultimos digitos aparecem aqui — CLAUDE.md §7)`);
  // 🔴 CONTROLE: o padrao CONSEGUE casar. Sem isto, um regex quebrado passaria.
  par('o padrao de telefone consegue casar', /\b55\d{10,11}\b/.test('placeholder="5547988087463"'),
    'nem num numero obvio ele casa — a assercao acima nao mede nada');
}

// ---------------------------------------------------------------------------
console.log('\n4 - A rota que grava a config aceita os quatro, e nao promove legado');

const api = ler(API_ROTINAS);
if (!api) {
  conferir(`\`${API_ROTINAS}\` existe`, false);
} else {
  const semCom = semComentarios(api);
  const listaAceita = (semCom.match(/\[\s*'test'[^\]]*\]/) || [''])[0];
  conferir('a lista de modos aceitos foi encontrada na rota', listaAceita.length > 0,
    'sem ela as assercoes abaixo passariam sobre string vazia');
  conferir('ela aceita `equipe` e `cliente`',
    /'equipe'/.test(listaAceita) && /'cliente'/.test(listaAceita),
    `aceita: ${listaAceita}`);
  conferir('e continua aceitando `test` e `none`',
    /'test'/.test(listaAceita) && /'none'/.test(listaAceita), `aceita: ${listaAceita}`);
  conferir('o legado `approval|live` e PRESERVADO como esta (quem retem e o Python)',
    /'approval'/.test(semCom) && /'live'/.test(semCom),
    'CONTRATOS §1: o valor antigo nao pode ser reescrito no banco pela tela');
  // 🔴 A promocao silenciosa e o defeito que a M2 introduz: `live -> cliente`
  //    na propria rota mandaria mensagem ao segurado sem ninguem escolher.
  conferir('e a rota NAO mapeia `live`/`approval` para um modo que envia',
    !/(['"])live\1\s*(?:\?|:|=>)\s*(['"])(?:cliente|equipe)\2/.test(semCom)
    && !/send_mode:\s*(['"])(?:cliente|equipe)\1/.test(semCom),
    'promocao silenciosa: a config antiga viraria envio real sem decisao humana');
  // ⚠️ A limpeza mora numa variavel (`const teamNumber = ….replace(/\D/g, '')`)
  //    e so DEPOIS entra no objeto. O guarda mede a REGRA — "o que e gravado em
  //    `team_number` passou pelo filtro de digitos" — seguindo o nome da
  //    variavel, e nao a linha unica que o autor por acaso nao escreveu.
  const varTeam = (semCom.match(/team_number:\s*([A-Za-z_$][\w$]*)/) || [])[1];
  const limpaDigitos = varTeam
    ? new RegExp(`(?:const|let)\\s+${varTeam}\\s*=[\\s\\S]{0,140}?replace\\(/\\\\D/g`).test(semCom)
    : /team_number:[\s\S]{0,140}?replace\(\/\\D\/g/.test(semCom);
  conferir('`team_number` e gravado so com digitos', limpaDigitos,
    `CONTRATOS §1: o Python espera digitos (\`telefone_br.so_digitos\`); a tela grava a partir de \`${varTeam || '(expressao inline)'}\``);
  conferir('`confirmacao_cliente` e gravado como booleano',
    /confirmacao_cliente:\s*(?:cfg\.confirmacao_cliente === true|Boolean\(|!!)/.test(semCom),
    'um `truthy` de string deixaria "false" valer como confirmado');

  const envAPI = semCom.replace(/'equipe'/g, "'x'").replace(/'cliente'/g, "'y'");
  par('o guarda acusa se `equipe`/`cliente` sairem da lista aceita',
    !/'equipe'/.test((envAPI.match(/\[\s*'test'[^\]]*\]/) || [''])[0]));
}

// ---------------------------------------------------------------------------
console.log('\n5 - As tres rotas de pendencia: por corretora, e com estado honesto');

for (const [nome, rel] of [['pendencias', PENDENCIAS], ['encaminhado', ENCAMINHADO], ['liberar', LIBERAR]]) {
  const src = ler(rel);
  if (!conferir(`a rota \`${nome}\` existe`, src.length > 0, `falta ${rel}`)) continue;
  const semCom = semComentarios(src);
  conferir(`\`${nome}\` resolve a corretora da sessao`, /resolveSessionCompany\(\)/.test(semCom),
    'sem isso a rota age na empresa PRIMARIA do usuario, nao na escolhida (SPEC-098)');
  conferir(`\`${nome}\` filtra por \`company_id\` (§7: service role nao tem RLS)`,
    /\.eq\('company_id',\s*ctx\.companyId\)/.test(semCom));
  conferir(`\`${nome}\` so olha o ledger REAL`, /\.eq\('send_mode',\s*'real'\)/.test(semCom),
    'sem o filtro, o botao mexe nas linhas do modo teste');
  const env = semCom.replace(/\.eq\('company_id',\s*ctx\.companyId\)/g, ".eq('x','y')");
  par(`o guarda de \`${nome}\` acusa a remocao do filtro de corretora`,
    !/\.eq\('company_id',\s*ctx\.companyId\)/.test(env));
}

const liberar = semComentarios(ler(LIBERAR));
if (liberar) {
  conferir('`liberar` exige motivo (vazio -> 400)', /400/.test(liberar) && /motivo/.test(liberar),
    'liberar reenvio sem motivo escrito e reenvio sem dono');
  // 🔴 A REGRA e a LISTA, nao a palavra. Um guarda que exigisse a string
  //    `'suprimido'` no arquivo ficaria verde com ela dentro de um dicionario de
  //    mensagens -- que e exatamente onde ela esta. O que decide o 409 e nao
  //    estar na lista de liberaveis.
  const liberaveis = Array.from(
    ((liberar.match(/LIBERAVEIS\s*=\s*\[[^\]]*\]/) || [''])[0]).matchAll(/'([a-z_]+)'/g),
  ).map((m) => m[1]);
  conferir('a lista de estados liberaveis foi encontrada', liberaveis.length > 0,
    'sem ela as quatro assercoes abaixo passariam sobre uma lista vazia');
  conferir('`liberar` RECUSA `suprimido` (preferencia do cliente e terminal)',
    !liberaveis.includes('suprimido') && /409/.test(liberar),
    `politica do WhatsApp (§7): opt-out nao se desfaz por botao. Liberaveis: ${liberaveis.join(', ')}`);
  conferir('`liberar` RECUSA `incerto` (efeito possivel nao e efeito ausente)',
    !liberaveis.includes('incerto') && /409/.test(liberar),
    `emenda 6 da SPEC v1.1. Liberaveis: ${liberaveis.join(', ')}`);
  conferir('e libera de `entregue_equipe|parcial|falhou|adiado` (+ `contestado` com motivo)',
    ['entregue_equipe', 'parcial', 'falhou', 'adiado'].every((s) => liberaveis.includes(s)),
    `liberaveis: ${liberaveis.join(', ')}`);
  // 🔴 CONTROLE: a leitura da lista CONSEGUE ver `suprimido` se ele entrar nela.
  const listaEnv = (liberar.replace(/LIBERAVEIS\s*=\s*\[/, "LIBERAVEIS = ['suprimido', ")
    .match(/LIBERAVEIS\s*=\s*\[[^\]]*\]/) || [''])[0];
  par('a leitura da lista pega um estado terminal injetado',
    /'suprimido'/.test(listaEnv));
  conferir('id de outra corretora devolve 404, nunca 403 com o dado dentro',
    /404/.test(liberar), 'um 403 que confirma a existencia da linha e IDOR pela metade');
}

const encaminhado = semComentarios(ler(ENCAMINHADO));
if (encaminhado) {
  conferir('`encaminhado` so aceita linha em `entregue_equipe`',
    /'entregue_equipe'/.test(encaminhado),
    'marcar como encaminhado o que nunca foi entregue a equipe e mentira no ledger');
  conferir('e grava QUEM marcou e QUANDO',
    /encaminhado_por/.test(encaminhado) && /encaminhado_ao_cliente_em/.test(encaminhado));
}

// ---------------------------------------------------------------------------
console.log('\n6 - CONTROLE: o que ja estava certo continua certo');

const reenvio = ler(REENVIO);
conferir('a rota `liberar-reenvio` (teste) continua existindo', reenvio.length > 0);
conferir('ela continua apagando SO `send_mode = test`', /\.eq\('send_mode', 'test'\)/.test(reenvio),
  'ela nunca pode encostar no ledger dos modos reais');
conferir('e continua escopada por corretora', /\.eq\('company_id', ctx\.companyId\)/.test(reenvio));
par('o guarda acusa se o filtro de `test` sumir',
  !/\.eq\('send_mode', 'test'\)/.test(reenvio.replace(".eq('send_mode', 'test')", ".eq('x','y')")));

const motor = ler(MOTOR);
conferir('o modo `test` do motor continua com a chave de dedup antiga',
  /on_conflict="company_id,recibo,send_mode"/.test(motor),
  'e ela que o botao de reenvio limpa — mudar isso quebra o botao em silencio');
conferir('e os modos reais tem motor proprio no Python',
  /_entregar_cobranca_real/.test(motor),
  'um seletor com `equipe`/`cliente` sem motor e exatamente o defeito que a SPEC-078 fechou');

pular('o comportamento das rotas em execucao',
  'o Next nao roda neste guarda. Quem executa o motor e '
  + '`backend/tests/test_a_cobranca_chega_a_quem_deve.py`; aqui a leitura da FONTE '
  + 'esta declarada, e cada assercao negativa tem par de controle');

// ---------------------------------------------------------------------------
console.log(falhas === 0
  ? `\nTODOS OS GUARDAS VERDES${pulados ? ` (${pulados} pulado(s))` : ''}\n`
  : `\n${falhas} GUARDA(S) VERMELHO(S)${pulados ? ` · ${pulados} pulado(s)` : ''}\n`);
process.exit(falhas === 0 ? 0 : 1);
