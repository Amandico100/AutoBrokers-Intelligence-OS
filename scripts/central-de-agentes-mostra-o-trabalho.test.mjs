// SPEC-088 BLOCO D — a Central mostra TODO trabalhador que o JSON mandar,
// no grupo que o JSON mandar, com o trabalho que o JSON mediu.
//
// O DEFEITO QUE ESTE GUARDA IMPEDE DE VOLTAR (📊 SPEC-088 §1.6, 03/09/2026):
//
//     page.tsx:16-20  COLORS ......... 9 ids
//     heartbeat.py    AGENT_TASKS .... 14 ids
//     sem cor: observador · tecelao · sentinela_rotas · espelho_atendimento · conselho
//
// Duas listas de agentes, e a segunda envelheceu em silêncio. A cura não é
// "atualizar a lista": é NÃO TER a lista. Este teste renderiza a tela de
// verdade — o mesmo `page.tsx`, transpilado pelo TypeScript do projeto e
// executado com o React do projeto — contra uma fixture de 21 trabalhadores
// que o frontend nunca viu, e confere que os 21 aparecem.
//
// COMO ELE FUNCIONA, e por que não é um teste de string sobre o código:
// ele não procura padrões no arquivo; ele chama `Central` (a função pura
// (status, memórias) → árvore) via `react-dom/server` e lê o HTML que sairia
// no navegador. CLAUDE.md §9.4: o que se afirma é o comportamento do MOTOR.
//
// E CADA AFIRMAÇÃO TEM LINHA DE CONTROLE (CLAUDE.md §9.2/§9.3): a mesma tela é
// renderizada com uma fixture SAUDÁVEL, onde "SEM GRUPO", "não instrumentado",
// "sem eixo de trabalho" e "ESTADO DESCONHECIDO" TÊM DE SUMIR. Um guarda que
// não tem como falhar não guarda nada.

import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const RAIZ = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const ts = require('typescript');
const { renderToStaticMarkup } = require('react-dom/server');

const PAGINA = 'app/admin/central-agentes/page.tsx';

// ─────────────────────────────────────────────────────────────────────────────
// Carregador: TSX real, React real. Nada de reimplementar a tela no teste.
//
// `Central` e `montarGrupos` não são exportados — uma página do App Router só
// pode exportar `default` e a lista fechada de campos de configuração (o Next
// gera `.next/types/app/**/page.ts` e QUALQUER export extra vira erro de tipo,
// que quebraria `next build`). Então o teste anexa os símbolos ao módulo
// depois da transpilação, no escopo em que eles já existem.
// ─────────────────────────────────────────────────────────────────────────────

function carregarPagina() {
  const fonte = fs.readFileSync(path.join(RAIZ, PAGINA), 'utf8');
  const js = ts.transpileModule(fonte, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020,
      jsx: ts.JsxEmit.ReactJSX,
      esModuleInterop: true,
    },
    fileName: PAGINA,
  }).outputText;

  const mod = { exports: {} };
  const req = (id) => {
    if (id === 'react' || id === 'react/jsx-runtime' || id === 'react/jsx-dev-runtime') return require(id);
    throw new Error(`import nao previsto no teste: ${id}`);
  };
  const anexo = '\nmodule.exports.__Central = Central;\nmodule.exports.__montarGrupos = montarGrupos;\n';
  new Function('module', 'exports', 'require', js + anexo)(mod, mod.exports, req);
  return mod.exports;
}

const pagina = carregarPagina();
const { createElement } = require('react');

function render(status, memorias = {}) {
  return renderToStaticMarkup(
    createElement(pagina.__Central, { status, memorias, carregando: false, erro: null }),
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Fixtures. Nenhum id daqui existe no `heartbeat.py` de hoje: é exatamente o
// ponto — trabalhador NOVO tem de aparecer sem tocar no frontend.
// ─────────────────────────────────────────────────────────────────────────────

const TRABALHO_CHEIO = {
  eixo: ['dominio.tarefa'],
  execucoes_24h: 3, execucoes_7d: 21, falhas_7d: 0,
  duracao_media_s: 9.9, fila_media_s: 35.7, artifacts_7d: 4,
  aprovacoes_pendentes: 1, travados: 0, custo_brl_30d: 12.5,
};

// 🔴 A FIXTURE É SUJA DE PROPÓSITO. Este é o texto que a rota mede HOJE
// (📊 SPEC-088, painel de 03/09: 13 de 18 cards imprimiam "· via redis", 14
// imprimiam "fonte: attendance_transcripts.created_at"). O contrato ganhou
// `fonte_rotulo` / `origem_rotulo` / `cadencia_humana`, mas a tela não pode
// depender deles para não vazar jargão: aqui eles NÃO vêm, e mesmo assim nada
// disso pode chegar ao Founder (DS-001 §6.7).
const SUJEIRA_DO_BACKEND = 'fonte work_runs.finished_at (completed), via redis, espera 1 dia(s)';

function ag(id, nome, estado, extras = {}) {
  return {
    id,
    nome,
    descricao: `o que ${nome} faz para a corretora`,
    cor: '#7FB7E8',
    grupo: extras.grupo === undefined ? extras.__grupo : extras.grupo,
    estado,
    motivo: `motivo declarado pelo backend para ${nome} — ${SUJEIRA_DO_BACKEND}`,
    pulso: { ultimo: '2026-09-03T00:01:03Z', origem: 'redis' },
    producao: { ultimo: '2026-08-26T00:05:34Z', fonte: 'attendance_transcripts.created_at', cadencia_esperada_s: 86400, limiar_s: 172800 },
    desligado: { declara: false, todas_desligadas: null, desde: null },
    trabalho: extras.trabalho === undefined ? TRABALHO_CHEIO : extras.trabalho,
    acoes_hoje: extras.acoes_hoje === undefined ? 3 : extras.acoes_hoje,
  };
}

function grupo(id, titulo, agentes) {
  return {
    id,
    titulo,
    proposito: `propósito do grupo ${titulo}`,
    resumo: `${agentes.filter((a) => a.estado === 'SAUDAVEL').length} de ${agentes.length} saudáveis`,
    agentes: agentes.map((a) => ({ ...a, grupo: a.grupo === null ? null : (a.grupo || id) })),
  };
}

// 21 trabalhadores em 4 grupos; o 21º chega SEM GRUPO (a mutação do gate ②).
const NOMES_1 = ['Zelador', 'Farol', 'Almanaque', 'Escrivão', 'Bússola'];
const NOMES_2 = ['Plantão', 'Triagem', 'Retorno'];
const NOMES_3 = ['Cartola', 'Prumo'];
const NOMES_4 = ['Peneira', 'Batedor', 'Contador', 'Relator', 'Corretivo', 'Vigia Novo', 'Semeador', 'Arquivista', 'Aferidor', 'Sineiro'];
const ORFAO = 'Achado Solto';

const ESTADOS_4 = ['SAUDAVEL', 'PARADO', 'PULSA_SEM_PRODUZIR', 'NAO_MEDIDO', 'DESLIGADO', 'SAUDAVEL', 'ESTADO_QUE_NAO_EXISTE', 'SAUDAVEL', 'PARADO', 'SAUDAVEL'];

const FIXTURE_21 = {
  gerado_em: '2026-09-03T02:10:00Z',
  cache_s: 60,
  grupos: [
    grupo('observa_registra', 'OBSERVA E REGISTRA', NOMES_1.map((n, i) => ag(`obs_${i}`, n, i === 0 ? 'PARADO' : 'SAUDAVEL'))),
    grupo('atende_agora', 'ATENDE AGORA', NOMES_2.map((n, i) => ag(`att_${i}`, n, i === 1 ? 'PULSA_SEM_PRODUZIR' : 'SAUDAVEL'))),
    grupo('mantem_rota', 'MANTÉM A ROTA CERTA', NOMES_3.map((n, i) => ag(`rot_${i}`, n, 'NAO_MEDIDO', i === 0 ? { trabalho: null } : {}))),
    grupo('aprende_avisa', 'APRENDE E AVISA', [
      // i === 2 (Contador): campos null, para "não instrumentado" ter de aparecer.
      // i === 4 (Corretivo): ⚪ DESLIGADO que EXECUTOU 1 vez em 24h — a contradição
      // que ficava escondida atrás do painel recolhido.
      ...NOMES_4.map((n, i) => ag(`apr_${i}`, n, ESTADOS_4[i],
        i === 2 ? { trabalho: { ...TRABALHO_CHEIO, custo_brl_30d: null, aprovacoes_pendentes: null } }
          : i === 4 ? { trabalho: { ...TRABALHO_CHEIO, execucoes_24h: 1, execucoes_7d: 1 } }
            : {})),
      // O órfão: `grupo: null`. Ele vem DENTRO de um grupo válido e mesmo assim
      // não pode ser adotado por ele — referência ⑥ (sem dono declarado aparece
      // "sem dono", nunca adotado por default).
      ag('orfao_0', ORFAO, 'PARADO', { grupo: null }),
    ]),
  ],
  // 🔴 CHAVES ASCII, como o backend as emite. A fixture antiga escrevia
  // 'aprovações' acentuado — uma chave que a rota nunca manda — e por isso o
  // mapeamento chave → nome de gente nunca foi exercido.
  nao_instrumentado: ['custo', 'aprovacoes', 'artifacts'],
  sem_card_por_decisao: [
    { workflow_key: 'test.wf', motivo: 'lixo de teste, 1 run' },
    { workflow_key: 'bridge.routine.execute', motivo: 'ponte de rotina, contada no auxiliar' },
  ],
};

// LINHA DE CONTROLE: mesma tela, casa arrumada. Tudo com grupo, tudo medido,
// nenhum estado desconhecido, nenhum campo null.
const FIXTURE_CONTROLE = {
  gerado_em: '2026-09-03T02:10:00Z',
  cache_s: 60,
  grupos: [
    grupo('observa_registra', 'OBSERVA E REGISTRA', NOMES_1.map((n, i) => ag(`obs_${i}`, n, 'SAUDAVEL'))),
    grupo('atende_agora', 'ATENDE AGORA', NOMES_2.map((n, i) => ag(`att_${i}`, n, 'SAUDAVEL'))),
  ],
  nao_instrumentado: [],
  sem_card_por_decisao: [],
};

const TODOS_OS_NOMES = [...NOMES_1, ...NOMES_2, ...NOMES_3, ...NOMES_4, ORFAO];

// ─────────────────────────────────────────────────────────────────────────────

let pass = 0, fail = 0; const falhas = [];
function assert(nome, cond) {
  if (cond) { pass++; console.log(`  ok   ${nome}`); }
  else { fail++; falhas.push(nome); console.log(`  X    ${nome}`); }
}

console.log('== SPEC-088 BLOCO D — a Central de Agentes mostra o trabalho ==\n');

const html = render(FIXTURE_21, { apr_0: { blocks: [{ key: 'k', content: 'bloco de memoria do Peneira', updated_at: '2026-09-01T00:00:00Z' }] } });

console.log('-- ① todo trabalhador do JSON aparece (21, nenhum conhecido pelo frontend)');
assert(`os 21 nomes aparecem (${TODOS_OS_NOMES.length} esperados)`, TODOS_OS_NOMES.every((n) => html.includes(`>${n}<`)));
assert('nenhum nome sumiu na dobra dos grupos', TODOS_OS_NOMES.filter((n) => html.includes(n)).length === 21);

console.log('\n-- ② o agente sem grupo NÃO é adotado: grupo sintético SEM GRUPO, em vermelho');
assert('o grupo SEM GRUPO aparece', html.includes('SEM GRUPO'));
assert('o órfão está DEPOIS do título SEM GRUPO', html.indexOf('SEM GRUPO') < html.lastIndexOf(ORFAO));
assert('SEM GRUPO é vermelho (#E06B6B)', /SEM GRUPO/.test(html) && html.slice(Math.max(0, html.indexOf('SEM GRUPO') - 400), html.indexOf('SEM GRUPO')).includes('E06B6B'));

console.log('\n-- ③ cada grupo tem título, propósito e a linha de resumo do JSON');
assert('os 4 títulos aparecem', ['OBSERVA E REGISTRA', 'ATENDE AGORA', 'MANTÉM A ROTA CERTA', 'APRENDE E AVISA'].every((t) => html.includes(t)));
assert('a ordem dos grupos é a ordem do array', html.indexOf('OBSERVA E REGISTRA') < html.indexOf('ATENDE AGORA')
  && html.indexOf('ATENDE AGORA') < html.indexOf('MANTÉM A ROTA CERTA')
  && html.indexOf('MANTÉM A ROTA CERTA') < html.indexOf('APRENDE E AVISA'));
assert('a linha de resumo vem do JSON', html.includes('4 de 5 saudáveis') && html.includes('2 de 3 saudáveis'));
assert('o resumo diz quantos cards a tela desenhou', html.includes('· 5 cards nesta tela'));

console.log('\n-- ④ o card mostra o motivo, e o painel TRABALHO com os números');
assert('o motivo do estado aparece', html.includes('motivo declarado pelo backend para Zelador'));
assert('os rótulos do painel TRABALHO aparecem', ['EXECUÇÕES 24H', 'EXECUÇÕES 7D', 'FALHAS 7D', 'DURAÇÃO MÉDIA', 'ESPERA NA FILA', 'ENTREGAS 7D', 'APROVAÇÕES ABERTAS', 'TRAVADOS', 'CUSTO 30D'].every((r) => html.includes(r)));
assert('os números medidos aparecem', html.includes('>21<') && html.includes('9,9') && html.includes('35,7'));
assert('null vira "não instrumentado", NUNCA zero', html.includes('não instrumentado'));
assert('sem eixo declarado vira "sem eixo de trabalho"', html.includes('sem eixo de trabalho'));
assert('o eixo do trabalho aparece', html.includes('dominio.tarefa'));

console.log('\n-- ⑤ os cinco estados, o desconhecido em vermelho, e o problema primeiro');
assert('os 5 rótulos de estado aparecem', ['PARADO', 'PULSA SEM PRODUZIR', 'NÃO MEDIDO', 'DESLIGADO', 'SAUDÁVEL'].every((r) => html.includes(r)));
assert('estado fora do contrato vira ESTADO DESCONHECIDO', html.includes('ESTADO DESCONHECIDO'));
// A ordem esperada dentro de APRENDE E AVISA, do pior para o melhor:
// desconhecido → PARADO → PULSA_SEM_PRODUZIR → NAO_MEDIDO → DESLIGADO → SAUDÁVEL
// (empate resolvido pelo nome). O órfão saiu deste grupo: ele está em SEM GRUPO.
const bloco4 = html.slice(html.indexOf('APRENDE E AVISA'), html.indexOf('SEM GRUPO'));
const pos = (n) => bloco4.indexOf(`>${n}<`);
const ORDEM_ESPERADA = ['Semeador', 'Aferidor', 'Batedor', 'Contador', 'Relator', 'Corretivo', 'Arquivista', 'Peneira', 'Sineiro', 'Vigia Novo'];
const desenhada = ORDEM_ESPERADA.map((n) => ({ n, i: pos(n) })).sort((a, b) => a.i - b.i).map((x) => x.n);
assert(`o problema vem primeiro dentro do grupo (${desenhada.join(' → ')})`,
  desenhada.join('|') === ORDEM_ESPERADA.join('|') && pos('Semeador') >= 0);
assert('o órfão saiu do grupo em que veio', pos(ORFAO) === -1);
assert('a barra do topo conta por ESTADO, não "alive"', html.includes('21 trabalhadores') && /\d+ SAUDÁVEL/.test(html));

console.log('\n-- ⑥ o que a tela NÃO mede fica escrito, e a memória continua lá');
assert('a chave ASCII vira nome de gente (custo · aprovacoes · artifacts)',
  html.includes('esta tela ainda não mede: custo por trabalhador · aprovações pendentes · entregas'));
assert('CONTROLE: a chave crua NÃO sobrou na tela', !html.includes('aprovacoes') && !html.includes('artifacts'));
assert('o que saiu por decisão fica DOBRADO, com a contagem à vista', html.includes('fora da tela por decisão (2)'));
assert('dobrado é dobrado: os 2 itens não estão no HTML',
  !html.includes('lixo de teste') && !html.includes('ponte de rotina'));
assert('o bloco MEMÓRIA continua no card certo', html.includes('MEMÓRIA (o que este agente sabe)'));

// ─────────────────────────────────────────────────────────────────────────────
// ⑦ NENHUM JARGÃO DE ENGENHARIA CHEGA AO FOUNDER — DS-001 §6.7.
//
// 📊 painel de 03/09/2026: 13 de 18 cards imprimiam "· via redis"; 14 imprimiam
// "fonte: attendance_transcripts.created_at"; a cadência dizia "1 dia(s)".
// A fixture acima manda essas três sujeiras DE PROPÓSITO e sem os rótulos
// humanos novos — então o que sai limpo saiu limpo por causa da tela.
// ─────────────────────────────────────────────────────────────────────────────

const PROIBIDAS = [
  ['redis', /redis/i],
  ['work_runs', /work_runs?\b/],
  ['workflow_key', /workflow_keys?\b/],
  ['null', /\bnull\b/],
  ['None', /\bNone\b/],
  ['(s) / (es)', /\(e?s\)/],
  ['.created_at', /\.created_at/],
  ['.finished_at', /\.finished_at/],
];
const jargaoEm = (txt) => PROIBIDAS.filter(([, re]) => re.test(txt)).map(([n]) => n);

console.log('\n-- ⑦ o Founder lê português de gente: nenhum termo de engenharia visível');
const achadosNoHtml = jargaoEm(html);
assert(`nenhum termo proibido no HTML renderizado (achados: ${achadosNoHtml.join(', ') || 'nenhum'})`, achadosNoHtml.length === 0);
// 🔴 LINHA DE CONTROLE do detector: ele TEM de acusar a sujeira crua. Sem isto,
// a asserção acima passaria mesmo com o detector quebrado.
const SUJO = 'pulso · via redis · fonte: work_runs.finished_at (completed) · attendance_transcripts.created_at · espera 1 dia(s) · workflow_key · null · None';
const achadosNaSujeira = jargaoEm(SUJO);
assert(`CONTROLE: o detector acusa a sujeira crua (${achadosNaSujeira.length} de ${PROIBIDAS.length})`, achadosNaSujeira.length === PROIBIDAS.length);
assert('CONTROLE: a fixture ENTREGOU a sujeira (o filtro é que a tirou)', jargaoEm(JSON.stringify(FIXTURE_21)).length >= 4);
assert('o nome da tabela virou "a produção dele"', html.includes('a produção dele'));
assert('a origem do pulso virou "o laço dele"', html.includes('o laço dele'));

console.log('\n-- ⑧ cadência em português: "1 dia", nunca "1 dia(s)"');
assert('a cadência de 86400s vira "1 dia"', html.includes('esperado a cada 1 dia'));
assert('nenhum "dia(s)" na tela', !html.includes('dia(s)'));
// O rótulo humano do backend, quando ele vier, é o que manda.
const COM_ROTULOS = {
  gerado_em: '2026-09-03T02:10:00Z',
  cache_s: 60,
  grupos: [grupo('atende_agora', 'ATENDE AGORA', [{
    ...ag('rot_x', 'Plantão', 'SAUDAVEL'),
    pulso: { ultimo: '2026-09-03T01:00:00Z', origem: 'redis', origem_rotulo: 'o laço dele', cadencia_humana: '1 hora' },
    producao: { ultimo: '2026-09-03T01:00:00Z', fonte: 'attendance_transcripts.created_at', fonte_rotulo: 'as conversas que ele gravou', cadencia_esperada_s: 86400, cadencia_humana: '7 dias', limiar_s: 172800 },
  }])],
  nao_instrumentado: [],
  sem_card_por_decisao: [],
};
const comRotulos = render(COM_ROTULOS);
assert('o rótulo humano do backend é usado', comRotulos.includes('as conversas que ele gravou'));
// E quando o rótulo humano vier no campo ANTIGO (`fonte`), ele também passa
// inteiro — jogar fora português por medo de tabela seria perder informação boa.
const PT_NO_CAMPO_ANTIGO = {
  ...COM_ROTULOS,
  grupos: [grupo('atende_agora', 'ATENDE AGORA', [{
    ...ag('rot_y', 'Plantão', 'SAUDAVEL'),
    pulso: { ultimo: '2026-09-03T01:00:00Z', origem: 'o laço dele' },
    producao: { ultimo: '2026-09-03T01:00:00Z', fonte: 'as telas capturadas ∪ os mapas de rota', cadencia_esperada_s: 3600, limiar_s: 7200 },
  }])],
};
const ptAntigo = render(PT_NO_CAMPO_ANTIGO);
assert('português no campo antigo passa inteiro, com o ∪ traduzido',
  ptAntigo.includes('as telas capturadas e os mapas de rota'));
assert(`CONTROLE: e ainda assim nenhum termo proibido (${jargaoEm(ptAntigo).join(', ') || 'nenhum'})`, jargaoEm(ptAntigo).length === 0);
assert('a cadência humana do backend é usada', comRotulos.includes('esperado a cada 7 dias') && comRotulos.includes('esperado a cada 1 hora'));
assert(`CONTROLE: com rótulos, também nenhum termo proibido (${jargaoEm(comRotulos).join(', ') || 'nenhum'})`, jargaoEm(comRotulos).length === 0);

console.log('\n-- ⑨ o grupo que dói se anuncia no título (o olho vai ao problema)');
assert('grupo com PARADO leva o marcador', html.includes('data-pior-estado="PARADO"'));
assert('grupo com PULSA SEM PRODUZIR leva o marcador', html.includes('data-pior-estado="PULSA_SEM_PRODUZIR"'));
assert('o marcador tem TEXTO, não só cor (DS-001 §13)', html.includes('AQUI DENTRO'));
// MANTÉM A ROTA CERTA só tem NAO_MEDIDO: não dói, não marca.
const blocoRota = html.slice(html.indexOf('MANTÉM A ROTA CERTA'), html.indexOf('APRENDE E AVISA'));
assert('CONTROLE: grupo só com NÃO MEDIDO NÃO leva marcador', !blocoRota.includes('data-pior-estado'));

console.log('\n-- ⑩ ⚪ DESLIGADO que executou: a contradição fica à vista, e o painel abre');
const cardCorretivo = html.slice(html.indexOf('>Corretivo<'), html.indexOf('>Arquivista<'));
assert('o card do desligado diz que executou', cardCorretivo.includes('executou 1 vez nas últimas 24h'));
assert('o painel TRABALHO dele vem ABERTO', cardCorretivo.includes('▾ TRABALHO') && cardCorretivo.includes('EXECUÇÕES 24H'));
// CONTROLE: sem execução, o mesmo estado ⚪ não inventa contradição nenhuma.
const DESLIGADO_MUDO = {
  gerado_em: '2026-09-03T02:10:00Z',
  cache_s: 60,
  grupos: [grupo('atende_agora', 'ATENDE AGORA', [{
    ...ag('des_0', 'Plantão', 'DESLIGADO'),
    trabalho: { ...TRABALHO_CHEIO, execucoes_24h: 0, execucoes_7d: 0 },
  }])],
  nao_instrumentado: [],
  sem_card_por_decisao: [],
};
const mudo = render(DESLIGADO_MUDO);
assert('CONTROLE: desligado SEM execução não mostra a linha', !mudo.includes('nas últimas 24h'));
assert('CONTROLE: e o painel dele continua recolhido', mudo.includes('▸ TRABALHO') && !mudo.includes('EXECUÇÕES 24H'));

console.log('\n-- ⑪ o relógio dos cards é o `gerado_em`, não o do navegador');
// A frase do `motivo` foi escrita no servidor. Se a idade ao lado dela contasse
// pelo relógio local, as duas discordariam — e um relógio adiantado dava tempo
// NEGATIVO. Aqui o `gerado_em` é de 2020: contado pelo navegador, a idade seria
// de milhares de dias; contada pela medição, é de 2 h.
const RELOGIO = {
  gerado_em: '2020-01-01T00:00:00Z',
  cache_s: 60,
  grupos: [grupo('atende_agora', 'ATENDE AGORA', [{
    ...ag('rel_0', 'Plantão', 'SAUDAVEL'),
    pulso: { ultimo: '2019-12-31T22:00:00Z', origem: null },
    // depois do `gerado_em`: um relógio dessincronizado não pode virar negativo
    producao: { ultimo: '2020-01-01T01:00:00Z', fonte: null, cadencia_esperada_s: 3600, limiar_s: 7200 },
  }])],
  nao_instrumentado: [],
  sem_card_por_decisao: [],
};
const relogio = render(RELOGIO);
assert('a idade do card é contada a partir da medição', relogio.includes('há 2 h'));
assert('CONTROLE: NÃO é contada pelo relógio do navegador', !/há \d{3,} dias<\/span>/.test(relogio.slice(relogio.indexOf('>Plantão<'))));
assert('futuro em relação à medição nunca vira tempo negativo', relogio.includes('há 0s') && !relogio.includes('há -'));

console.log('\n-- 🔴 LINHA DE CONTROLE: casa arrumada, os quatro avisos TÊM de sumir');
const controle = render(FIXTURE_CONTROLE);
assert('CONTROLE: nenhum "SEM GRUPO"', !controle.includes('SEM GRUPO'));
assert('CONTROLE: nenhum "não instrumentado"', !controle.includes('não instrumentado'));
assert('CONTROLE: nenhum "sem eixo de trabalho"', !controle.includes('sem eixo de trabalho'));
assert('CONTROLE: nenhum "ESTADO DESCONHECIDO"', !controle.includes('ESTADO DESCONHECIDO'));
assert('CONTROLE: nenhum rodapé de não medido', !controle.includes('esta tela ainda não mede'));
assert('CONTROLE: nenhum marcador de problema no título dos grupos', !controle.includes('data-pior-estado'));
assert(`CONTROLE: nenhum termo proibido (${jargaoEm(controle).join(', ') || 'nenhum'})`, jargaoEm(controle).length === 0);
assert('CONTROLE: os 8 nomes desta fixture aparecem', [...NOMES_1, ...NOMES_2].every((n) => controle.includes(`>${n}<`)));

console.log('\n-- 🔴 LINHA DE CONTROLE: sem JSON, a tela não inventa casa vazia verde');
const vazio = renderToStaticMarkup(createElement(pagina.__Central, { status: null, memorias: {}, carregando: false, erro: null }));
assert('CONTROLE: nenhum nome de agente sem JSON', TODOS_OS_NOMES.every((n) => !vazio.includes(n)));
assert('CONTROLE: a ausência de grupos é acusada como defeito', vazio.includes('A medição não devolveu nenhum grupo'));

console.log('\n-- 🔴 O frontend não tem lista de agente (referência ⑥ · o juiz roda o mesmo grep)');
const fonte = fs.readFileSync(path.join(RAIZ, PAGINA), 'utf8');
const CODIGO = fonte.split('\n').filter((l) => !l.trim().startsWith('//')).join('\n');
const IDS_REAIS = ['observador', 'tecelao', 'espelho_atendimento', 'cartografo', 'vigia_sentinela', 'cerebro', 'followup',
  'sentinela_rotas', 'alfaiate', 'garimpo', 'detector', 'auditor', 'sugestoes', 'conselho', 'briefing', 'medidor', 'agrupador'];
const vazados = IDS_REAIS.filter((id) => CODIGO.includes(id));
assert(`nenhum id de agente no código da página (achados: ${vazados.join(', ') || 'nenhum'})`, vazados.length === 0);
assert('CONTROLE: a leitura do arquivo não é vazia (acha o que existe)', CODIGO.includes('TRABALHO') && CODIGO.includes('montarGrupos'));

console.log(`\n${pass} ok · ${fail} falha(s)`);
if (fail > 0) { console.log(falhas.map((f) => `  - ${f}`).join('\n')); process.exit(1); }
