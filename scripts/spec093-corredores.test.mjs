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

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
process.exit(fail ? 1 : 0);
