#!/usr/bin/env node
/**
 * SPEC-093-B · BLOCO B gate ⑤ — o lado NEXT do vocabulário da sombra.
 *
 * 🔴 O DEFEITO QUE ESTE ARQUIVO EXISTE PARA IMPEDIR: dois vocabulários.
 * Os escritores da sombra moram em dois stacks — Python (`webhook.py`,
 * `a_nota_da_atendente.py`, `o_fim_do_atendimento.py`) e Next
 * (`app/api/dashboard/conversas/[id]/route.ts`, o botão **Assumir**, que é 📊 o
 * gesto humano REAL do piloto: `tools_config.human_handoff.enabled` está false ou
 * ausente nos 8 agentes, medido em 03/09/2026). Se cada lado escrever a sua lista
 * de `event_type`, a variante do digest agrupa metade dos casos e ninguém percebe:
 * as duas listas ficam verdes separadamente.
 *
 * 📊 O Next NÃO importa nada de `backend/` (20 ocorrências, todas em string ou
 * comentário). O precedente é o inverso: `lib/admin/portao-do-prompt.contract.json`,
 * importado pelo Next via `@/` (`provision-tenant.ts:57`, com `resolveJsonModule` no
 * tsconfig) e lido pelo Python por caminho a partir da raiz
 * (`test_o_portao_vale_no_backend.py:72`). O vocabulário da sombra segue esse
 * precedente — e este arquivo prova que o caminho do `@/` de fato resolve.
 *
 * ⚠️ Este teste NÃO compara o hash contra um valor escrito aqui: um hash fixo no
 * código vira verdade vencida a cada edição do vocabulário (CLAUDE.md §9.3). Ele
 * IMPRIME o sha256, e o bloco [1] do guarda Python imprime o mesmo — o integrador
 * cola os dois lado a lado no relatório. Um hash diferente é dois arquivos.
 *
 *   node scripts/claims-shadow-vocab.test.mjs
 */
import { createHash } from 'node:crypto';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const RAIZ = join(dirname(fileURLToPath(import.meta.url)), '..');
const CAMINHO = join(RAIZ, 'lib', 'atendimento', 'claims-shadow-vocab.json');

let ok = 0;
const falhas = [];
function certo(nome, cond, detalhe = '') {
  if (cond) { ok++; console.log(`  ok    ${nome}`); }
  else { falhas.push(nome); console.log(`  FALHA ${nome}${detalhe ? `\n        ${detalhe}` : ''}`); }
}

console.log('='.repeat(78));
console.log('  O VOCABULARIO DA SOMBRA E UM SO -- SPEC-093-B BLOCO B gate 5 (lado Next)');
console.log('='.repeat(78));

certo('lib/atendimento/claims-shadow-vocab.json existe', existsSync(CAMINHO),
  'no lib/, nunca no backend/: o Next nao importa nada de backend/');
if (!existsSync(CAMINHO)) { process.exit(1); }

const bruto = readFileSync(CAMINHO, 'utf8');
let v = null;
try { v = JSON.parse(bruto); certo('o vocabulario e JSON valido', true); }
catch (e) { certo('o vocabulario e JSON valido', false, String(e)); process.exit(1); }

// ⚠️ Os eventos e os 6 atores estao escritos AQUI, no lado Next, de proposito:
// um teste que lesse a lista do proprio arquivo que ele valida nao guarda nada.
// Sao a §5 da SPEC transcrita, e o CHECK real de work_events.
//
// 🔴 v2 — `claims.seguradora_respondeu` SAIU, e a lista passou de 11 para 10.
// 📊 Medido em 03/09/2026: ZERO escritores do evento nos dois stacks (`grep`
// devolvia so o template do Python e as duas transcricoes de teste). Um evento
// prometido e nunca escrito manda o leitor do digest procurar um dado que nao
// existe -- e a espera `esperando_seguradora` que o alimentaria tambem nao tem
// escritor (P-093B-SEGURADORA). ⛔ A lista muda porque o FATO mudou; manter a
// afirmacao vencida so ensinaria a ignorar teste (CLAUDE.md §9.3).
const EVENTOS = [
  'claims.sombra_aberta', 'claims.handoff_pedido', 'claims.humano_assumiu',
  'claims.humano_devolveu', 'claims.humano_respondeu', 'claims.nota_registrada',
  'claims.documento_recebido',
  'claims.espera_aberta', 'claims.espera_satisfeita', 'claims.encerrado',
];
// 📊 CHECK de work_events.actor_type, lido do banco em 03/09/2026.
// `human` NAO esta na lista: o Postgres recusa o INSERT, e o escritor engole a recusa.
const ATORES = ['system', 'worker', 'user', 'agent', 'admin', 'provider'];
// 🔴 v2 — `motivo_enum` ganhou enum. Antes ele era a UNICA chave de payload sem
// enum e sem ser inteiro: aceitava qualquer slug de ate 64 chars, e o digest
// agrupava por um valor que ninguem fechava.
const ENUMS = ['confianca', 'motivo', 'motivo_enum', 'origem', 'canal',
  'tipo_documento', 'kind', 'desfecho'];

const eventos = Object.keys(v.eventos || {}).sort();
certo('os 10 eventos da §5 (v2, sem seguradora_respondeu) estao la, nem a mais nem a menos',
  JSON.stringify(eventos) === JSON.stringify([...EVENTOS].sort()),
  `veio ${JSON.stringify(eventos)}`);
certo('o vocabulario esta na versao 2', Number(v.versao) === 2, `veio ${v.versao}`);
certo('`claims.seguradora_respondeu` NAO esta mais no vocabulario',
  !Object.prototype.hasOwnProperty.call(v.eventos || {}, 'claims.seguradora_respondeu'),
  'zero escritores medidos em 03/09/2026 -- P-093B-SEGURADORA');
// 🔴 O que o red team achou: `tem_numero` significava coisas diferentes nos dois
// stacks. A regra agora esta ESCRITA no vocabulario, que e o unico lugar que os
// dois leem.
certo('o vocabulario descreve `tem_numero` (a regra que os dois stacks compartilham)',
  typeof v.descricoes?.tem_numero === 'string' && v.descricoes.tem_numero.includes('6,'),
  `veio ${JSON.stringify(v.descricoes?.tem_numero)}`);
certo('a FORMA DE SLUG esta declarada no vocabulario (o Python e o TS usam a mesma)',
  v.forma_de_slug === '^[a-z0-9][a-z0-9_.-]*$', `veio ${JSON.stringify(v.forma_de_slug)}`);

const foraDoCheck = Object.entries(v.eventos || {})
  .filter(([, d]) => !ATORES.includes(d.ator)).map(([e, d]) => `${e}:${d.ator}`);
certo('TODO ator esta no CHECK de work_events', foraDoCheck.length === 0,
  `fora do CHECK: ${foraDoCheck.join(', ')}`);

certo('os 8 enums da §5 (v2, com motivo_enum) estao la',
  JSON.stringify(Object.keys(v.enums || {}).sort()) === JSON.stringify([...ENUMS].sort()),
  `veio ${JSON.stringify(Object.keys(v.enums || {}).sort())}`);

const semPayload = Object.entries(v.eventos || {})
  .filter(([, d]) => !Array.isArray(d.payload)).map(([e]) => e);
certo('todo evento declara a lista de chaves de payload', semPayload.length === 0,
  `sem payload: ${semPayload.join(', ')} -- sem argumentos, "pediu documento" e "pediu BO" colidem`);

certo("o vocabulario declara workflow_key='claims.shadow'", v.workflow_key === 'claims.shadow');

// O CAMINHO DO `@/` RESOLVE? E o que faz o route.ts do painel conseguir importar.
let tsconfig = null;
try { tsconfig = JSON.parse(readFileSync(join(RAIZ, 'tsconfig.json'), 'utf8').replace(/^\s*\/\/.*$/gm, '')); }
catch { /* deixa null; o gate abaixo reprova com a razao visivel */ }
certo('tsconfig tem resolveJsonModule (o Next consegue importar o .json)',
  Boolean(tsconfig?.compilerOptions?.resolveJsonModule));
certo("tsconfig mapeia '@/*' para a raiz do repo",
  JSON.stringify(tsconfig?.compilerOptions?.paths?.['@/*'] || []).includes('./*'),
  "sem o alias, `@/lib/atendimento/claims-shadow-vocab.json` nao resolve no route.ts");

// 🔴 CONTROLE: os casadores CONSEGUEM ficar vermelhos.
const ruim = { eventos: { 'claims.x': { ator: 'human', payload: [] } } };
certo('CONTROLE: um `ator: human` sintetico e RECUSADO',
  Object.entries(ruim.eventos).filter(([, d]) => !ATORES.includes(d.ator)).length === 1);
certo('CONTROLE: uma lista de eventos incompleta REPROVA',
  JSON.stringify(['claims.encerrado']) !== JSON.stringify([...EVENTOS].sort()));

const sha = createHash('sha256').update(readFileSync(CAMINHO)).digest('hex');
console.log(`\n  📊 sha256 do vocabulario lido pelo NEXT: ${sha}`);
console.log('     (o bloco [1] de backend/tests/test_o_sinistro_deixa_rastro.py imprime');
console.log('      o mesmo numero. Diferente = dois arquivos, e o gate B5 esta quebrado.)');

console.log('\n' + '='.repeat(78));
console.log(`  ${ok} ok · ${falhas.length} falhas`);
console.log('='.repeat(78));
process.exit(falhas.length ? 1 : 0);
