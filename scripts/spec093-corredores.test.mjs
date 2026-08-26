// ===========================================================================
// SPEC-093 BLOCO G — um clique liga os 14, e a escolha da corretora vence
// ===========================================================================
//
// 📊 Medido em `build_corridor_catalog()`, que é a fonte da tela: **14 cartões**
// (10 seguradoras · auto 10 + residencial 4) somando 73 subserviços. Os 73
// aparecem como TEXTO dentro do cartão, nunca como coisa clicável.
//
// ⚠️ Este arquivo é rodado por `backend/tests/test_um_clique_liga_os_corredores.py`,
// que está no `pytest tests/ -q` do `gate.yml`.
import { decidirLoteDeAtivacao } from '../lib/admin/corridor-bulk-decision.ts';

let pass = 0, fail = 0;
function assert(nome, cond) {
  if (cond) { pass++; } else { fail++; console.log('  x ' + nome); }
}
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);

// Os 14 cartões, com uma âncora cada.
const CATORZE = Array.from({ length: 14 }, (_, i) => ({
  corridorId: `corredor-${i}`, anchorId: `anc-${i}`, legado: [],
}));

console.log('\n== SPEC-093 BLOCO G — ligar todos os corredores ==\n');

// -------------------------------------------------------------------------
// ① a corretora liga o agente → os 14 corredores disponíveis ficam ativos
// -------------------------------------------------------------------------
{
  const r = decidirLoteDeAtivacao(CATORZE, {});
  assert('① os 14 entram no lote', r.ativar.length === 14);
  assert('① e nenhum sobra em outro balde',
    r.respeitados.length === 0 && r.jaAtivos.length === 0 && r.semAncora.length === 0);
  assert('① o lote são as ÂNCORAS, não os corridor_id',
    r.ativar[0] === 'anc-0' && r.ativar[13] === 'anc-13');
}

// -------------------------------------------------------------------------
// ② 🔴 um corredor pausado À MÃO antes disso CONTINUA pausado
//    (é aqui que mora a mutação obrigatória do bloco)
// -------------------------------------------------------------------------
{
  const r = decidirLoteDeAtivacao(CATORZE, { 'anc-3': 'paused' });
  assert('② o pausado NÃO entra no lote', !r.ativar.includes('anc-3'));
  assert('② e é contado como respeitado', eq(r.respeitados, ['corredor-3']));
  assert('② os outros 13 ligam', r.ativar.length === 13);
}
{
  // ⚠️ E o pausado pela âncora LEGADA também. A corretora que pausou pelo
  // cartão pausou as duas linhas; ignorar a legada religaria uma delas, e a
  // próxima leitura mostraria o cartão ativo de novo.
  const comLegado = CATORZE.map((c, i) =>
    i === 5 ? { ...c, legado: ['anc-velha-5'] } : c);
  const r = decidirLoteDeAtivacao(comLegado, { 'anc-velha-5': 'paused' });
  assert('② o pausado pela âncora LEGADA também é respeitado',
    !r.ativar.includes('anc-5') && eq(r.respeitados, ['corredor-5']));
}
{
  // 🔴 LINHA DE CONTROLE: prove que o balde `respeitados` CONSEGUE ficar vazio.
  // Sem ela, um bug que respeitasse tudo passaria nas duas asserções acima.
  const r = decidirLoteDeAtivacao(CATORZE, {});
  assert('② CONTROLE: sem pausa nenhuma, respeitados fica VAZIO',
    r.respeitados.length === 0 && r.ativar.length === 14);
}

// -------------------------------------------------------------------------
// ③ ligar duas vezes → nada muda (idempotente)
// -------------------------------------------------------------------------
{
  const primeira = decidirLoteDeAtivacao(CATORZE, {});
  // depois de gravar, todas as âncoras estão `active`
  const depois = Object.fromEntries(primeira.ativar.map((id) => [id, 'active']));
  const segunda = decidirLoteDeAtivacao(CATORZE, depois);
  assert('③ a segunda rodada não grava nada', segunda.ativar.length === 0);
  assert('③ e conta os 14 como já ativos', segunda.jaAtivos.length === 14);
  const terceira = decidirLoteDeAtivacao(CATORZE, depois);
  assert('③ a terceira é igual à segunda', eq(segunda, terceira));
}

// -------------------------------------------------------------------------
// ④ 🔴 derrube no meio e RETOME: o fim é o mesmo de uma rodada limpa
// -------------------------------------------------------------------------
{
  // A queda: 6 âncoras criadas e gravadas, 8 corredores ainda sem âncora.
  const parcial = CATORZE.map((c, i) => (i < 6 ? c : { ...c, anchorId: null }));
  const meio = decidirLoteDeAtivacao(parcial, {});
  assert('④ a rodada interrompida grava só o que conseguiu', meio.ativar.length === 6);
  assert('④ e os 8 sem âncora ficam nomeados, não silenciados',
    meio.semAncora.length === 8);

  // A retomada: as âncoras que faltavam existem agora, e as 6 já estão ativas.
  const gravado = Object.fromEntries(meio.ativar.map((id) => [id, 'active']));
  const retomada = decidirLoteDeAtivacao(CATORZE, gravado);
  assert('④ a retomada grava exatamente os 8 que faltavam',
    retomada.ativar.length === 8);

  // 🔴 O FIM É O MESMO DE UMA RODADA LIMPA.
  const limpa = decidirLoteDeAtivacao(CATORZE, {});
  const fimInterrompido = new Set([...meio.ativar, ...retomada.ativar]);
  const fimLimpo = new Set(limpa.ativar);
  assert('④ 🔴 interrompido+retomado == rodada limpa',
    fimInterrompido.size === fimLimpo.size
      && [...fimLimpo].every((id) => fimInterrompido.has(id)));

  // e a retomada é ela mesma idempotente
  const gravado2 = Object.fromEntries(
    [...fimInterrompido].map((id) => [id, 'active']));
  assert('④ retomar de novo não grava nada',
    decidirLoteDeAtivacao(CATORZE, gravado2).ativar.length === 0);
}
{
  // ⚠️ E a queda NÃO pode religar quem estava pausado. Este é o cruzamento de
  // ② com ④ — o caso em que uma retomada apagaria a escolha da corretora.
  const parcial = CATORZE.map((c, i) => (i < 6 ? c : { ...c, anchorId: null }));
  const meio = decidirLoteDeAtivacao(parcial, { 'anc-3': 'paused' });
  const gravado = Object.fromEntries(meio.ativar.map((id) => [id, 'active']));
  const retomada = decidirLoteDeAtivacao(CATORZE, { ...gravado, 'anc-3': 'paused' });
  assert('④+② a retomada NÃO religa o pausado',
    !meio.ativar.includes('anc-3') && !retomada.ativar.includes('anc-3'));
}

// -------------------------------------------------------------------------
// ⑥ dois tenants: ligar tudo em A não liga nada em B
// -------------------------------------------------------------------------
{
  // As âncoras são POR CORRETORA — a de A nunca aparece no estado de B. O que
  // esta decisão garante é que ela nunca INVENTA uma: sem âncora, sem ativação.
  const semAncora = CATORZE.map((c) => ({ ...c, anchorId: null }));
  const r = decidirLoteDeAtivacao(semAncora, {});
  assert('⑥ sem âncora não se inventa ativação nenhuma', r.ativar.length === 0);
  assert('⑥ e os 14 saem NOMEADOS em semAncora', r.semAncora.length === 14);

  // 🔴 CONTROLE: os mesmos 14, COM âncora, ligam. Sem esta linha, um bug que
  // nunca ligasse nada passaria na asserção acima.
  assert('⑥ CONTROLE: com âncora, os mesmos 14 ligam',
    decidirLoteDeAtivacao(CATORZE, {}).ativar.length === 14);
}

// -------------------------------------------------------------------------
// A função é PURA e TOTAL — o mesmo estado devolve o mesmo lote, sempre
// -------------------------------------------------------------------------
{
  const estado = { 'anc-1': 'paused', 'anc-2': 'active', 'anc-9': null };
  const a = decidirLoteDeAtivacao(CATORZE, estado);
  const b = decidirLoteDeAtivacao(CATORZE, estado);
  assert('pura: duas chamadas, o mesmo lote', eq(a, b));
  assert('`null` é ausência de decisão, e liga', a.ativar.includes('anc-9'));
  assert('lista vazia não estoura',
    eq(decidirLoteDeAtivacao([], {}),
       { ativar: [], respeitados: [], jaAtivos: [], semAncora: [] }));
  // todo corredor cai em EXATAMENTE um balde
  const total = a.ativar.length + a.respeitados.length + a.jaAtivos.length
    + a.semAncora.length;
  assert('todo corredor cai em exatamente um balde', total === 14);
}


// ===========================================================================
// 🔴 `ativarTodosOsCorredores` EXECUTADA — o buraco que o juiz achou
// ===========================================================================
//
// ⚠️ A decisão pura acima estava bem guardada; a FUNÇÃO DE IO não era executada
// por teste nenhum. `spec093-a-rota-do-botao.test.mjs` mocka o store inteiro, e
// o que sobrava eram guardas de texto-fonte em pytest — nenhum mencionava
// `sem_ancora`.
//
// 🔴 A mutação de uma linha `sem_ancora: lote.semAncora.length` → `sem_ancora: 0`
// passava a suíte inteira verde e desfazia o conserto do painel: o "ligou tudo
// que ligou nada" voltava a ser mudo, porque `route.ts` só grita quando
// `corredores.sem_ancora > 0`.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import ts from 'typescript';

const RAIZ2 = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const EMPRESA = '11111111-1111-1111-1111-111111111111';

function carregarTS2(rel, resolverImport) {
  const fonte = fs.readFileSync(path.join(RAIZ2, rel), 'utf8');
  const js = ts.transpileModule(fonte, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020,
      esModuleInterop: true,
    }, fileName: rel,
  }).outputText;
  const mod = { exports: {} };
  const req = (id) => {
    const r = resolverImport(id);
    if (r === undefined) throw new Error(`import nao previsto: ${id}`);
    return r;
  };
  // eslint-disable-next-line no-new-func
  new Function('require', 'module', 'exports', js)(req, mod, mod.exports);
  return mod.exports;
}

// O dublê de Supabase: só os verbos que este caminho usa.
function dubleSupabase(tabelas, registro) {
  const q = (tabela) => {
    const filtros = [];
    let op = null, linhas = null, campos = null;
    const self = {
      select: () => self,
      insert: (l) => { op = 'insert'; linhas = Array.isArray(l) ? l : [l]; return exec(); },
      upsert: (l, o) => { op = 'upsert'; linhas = Array.isArray(l) ? l : [l]; campos = o; return exec(); },
      eq: (c, v) => { filtros.push(['eq', c, v]); return self; },
      in: (c, v) => { filtros.push(['in', c, v]); return self; },
      or: () => self,
      limit: () => self,
      maybeSingle: () => exec(),
      then: (res) => exec().then(res),
    };
    function casa(l) {
      return filtros.every(([t, c, v]) =>
        t === 'eq' ? String(l[c]) === String(v)
          : t === 'in' ? v.map(String).includes(String(l[c]))
            : true);
    }
    async function exec() {
      const tab = tabelas[tabela] ?? (tabelas[tabela] = []);
      registro.push({ tabela, op: op ?? 'select', filtros, linhas, campos });
      if (op === 'insert' || op === 'upsert') {
        if (tabelas[`__falha_${tabela}`]) return { data: null, error: { message: 'boom' } };
        for (const l of linhas) tab.push({ ...l, id: l.id ?? `id-${tab.length}-${tabela}` });
        return { data: linhas, error: null };
      }
      return { data: tab.filter(casa), error: null };
    }
    return self;
  };
  return { from: (t) => q(t) };
}

const CATORZE_CODIGO = Array.from({ length: 14 }, (_, i) => ({
  corridor_id: `corredor-${i}`, title: `Corredor ${i}`, insurer_key: 'allianz',
  line_kind: 'auto', channel: 'whatsapp', playbook_ref: `pb-${i}`,
}));

async function ligarTudo(tabelas, { catalogo = CATORZE_CODIGO } = {}) {
  const registro = [];
  const gritos = [];
  const supabase = dubleSupabase(tabelas, registro);
  // 🔴 O `console.error` É PARTE DO PRODUTO AQUI, e por isso é capturado.
  // ⚠️ Sem isto, desligar o grito do "ligou tudo que ligou nada" passava verde:
  // a resposta HTTP tem o número, mas quem opera lê o LOG.
  const errOriginal = console.error;
  console.error = (...a) => { gritos.push(a.map(String).join(' ')); };
  const store = carregarTS2('lib/admin/tenant-corridor-store.ts', (id) => {
    if (id === '@supabase/supabase-js') return {};
    if (id === '@/lib/backend-url') {
      return { getBackendUrl: () => 'http://x', BackendUrlError: class extends Error {} };
    }
    if (id === '@/lib/admin/tenant-corridor-catalog') {
      return {
        buildCorridorCatalog: (c) => c,
        corridorIdForTemplateKey: (k) => k,
        foldActivationStatus: () => null,
        nextCorridorStatus: (a) => (a === 'pause' ? 'paused' : 'active'),
      };
    }
    if (id === '@/lib/admin/corridor-bulk-decision') {
      return { decidirLoteDeAtivacao };
    }
    return undefined;
  });
  globalThis.fetch = async () => ({
    ok: true, json: async () => ({ corridors: catalogo }),
  });
  process.env.BACKEND_INTERNAL_API_KEY = 'k';
  let r;
  try {
    r = await store.ativarTodosOsCorredores(supabase, EMPRESA, 'u1');
  } finally {
    console.error = errOriginal;
  }
  return { r, registro, tabelas, gritos };
}

console.log('\n-- ativarTodosOsCorredores, executada --\n');

{
  const t = { corridor_templates: [], tenant_corridors: [] };
  const { r, tabelas, gritos } = await ligarTudo(t);
  assert('IO: liga os 14 e diz quantos', r.ok === true && r.ativados === 14);
  assert('IO: nenhum ficou sem âncora', r.sem_ancora === 0);
  assert('IO: 14 âncoras criadas', tabelas.corridor_templates.length === 14);
  assert('IO: e 14 ativações', tabelas.tenant_corridors.length === 14);
  assert('IO: toda ativação carrega a corretora',
    tabelas.tenant_corridors.every((l) => l.company_id === EMPRESA));
  // 🔴 CONTROLE: rodada limpa NÃO grita. Sem esta linha, um `console.error`
  // incondicional passaria na asserção do grito lá embaixo.
  assert('CONTROLE: rodada limpa não grita nada',
    gritos.filter((g) => g.includes('sem âncora')).length === 0);
}
{
  // 🔴 O CASO DO CONSERTO: o INSERT das âncoras falha inteiro.
  const t = { corridor_templates: [], tenant_corridors: [], __falha_corridor_templates: true };
  const { r, gritos } = await ligarTudo(t);
  assert('🔴 âncoras falharam: ativados é 0', r.ativados === 0);
  assert('🔴 e `sem_ancora` DIZ que os 14 ficaram de fora', r.sem_ancora === 14);
  assert('⚠️ `ok` continua true — falhar aqui não desfaz o toggle', r.ok === true);
  // 🔴 E O LOG GRITA. Quem opera lê o log, não o corpo da resposta.
  assert('🔴 o log diz que 14 de 14 ficaram sem âncora',
    gritos.some((g) => g.includes('14 de 14') && g.includes('NÃO foram ativados')));
}
{
  // ② a escolha da corretora vence, pelo caminho de IO
  const t = {
    corridor_templates: [{ id: 'anc-3', company_id: EMPRESA, corridor_key: 'corredor-3' }],
    tenant_corridors: [{ company_id: EMPRESA, corridor_template_id: 'anc-3', status: 'paused' }],
  };
  const { r, tabelas } = await ligarTudo(t);
  assert('② IO: o pausado é respeitado', r.respeitados === 1 && r.ativados === 13);
  assert('② IO: e a linha dele NÃO foi tocada',
    tabelas.tenant_corridors.find((l) => l.corridor_template_id === 'anc-3').status === 'paused');
}
{
  // ③ idempotente pelo caminho de IO
  const t = { corridor_templates: [], tenant_corridors: [] };
  await ligarTudo(t);
  const { r } = await ligarTudo(t);
  assert('③ IO: a segunda rodada não grava nada', r.ativados === 0);
  assert('③ IO: e conta os 14 como já ativos', r.ja_ativos === 14);
}
{
  // ⑥ 🔴 DOIS TENANTS, NO CAMINHO DE IO. A âncora da OUTRA corretora tem o
  // mesmo `corridor_key` — se o filtro por empresa sumir da leitura, ela é
  // reaproveitada e a ativação da Resulta aponta para a linha da AutoFleet.
  const OUTRA = '22222222-2222-2222-2222-222222222222';
  const t = {
    corridor_templates: CATORZE_CODIGO.map((c, i) => ({
      id: `alheia-${i}`, company_id: OUTRA, corridor_key: c.corridor_id,
    })),
    tenant_corridors: [],
  };
  const { r, tabelas } = await ligarTudo(t);
  assert('⑥ IO: as 14 âncoras da outra corretora NÃO são reaproveitadas',
    r.ativados === 14);
  assert('⑥ IO: e 14 âncoras NOVAS foram criadas para esta',
    tabelas.corridor_templates.filter((l) => l.company_id === EMPRESA).length === 14);
  assert('⑥ IO: nenhuma ativação aponta para âncora alheia',
    tabelas.tenant_corridors.every((l) => !String(l.corridor_template_id).startsWith('alheia-')));
  assert('⑥ IO: e as linhas da outra corretora ficaram intactas',
    tabelas.tenant_corridors.every((l) => l.company_id === EMPRESA));
}
{
  // catálogo indisponível: não inventa ativação nenhuma
  const t = { corridor_templates: [], tenant_corridors: [] };
  const { r } = await ligarTudo(t, { catalogo: [] });
  assert('sem catálogo, nada é gravado',
    r.ok === false && r.error === 'catalogo_indisponivel');
  assert('e nenhuma âncora foi criada', t.corridor_templates.length === 0);
}

console.log(`\n== Resumo FINAL: ${pass} passaram, ${fail} falharam ==`);
process.exit(fail ? 1 : 0);
