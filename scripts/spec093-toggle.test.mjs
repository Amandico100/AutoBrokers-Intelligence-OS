// ===========================================================================
// SPEC-093 BLOCO D.1 — o toggle tem TRÊS desfechos, não dois
// ===========================================================================
//
// 🔴 O terceiro — "não mudou nada" — é o que mantém o gate ⑥ de pé:
// *"agente ligado o tempo todo → ZERO saudações"*. Sem ele, apertar `ligar`
// num agente que já estava ligado dispararia uma rodada de saudação do nada.
//
// ⚠️ Este arquivo é rodado por `backend/tests/test_a_saudacao_do_religamento.py`,
// que está no `pytest tests/ -q` do `gate.yml`. 📊 Um `.test.mjs` sem executor
// já aconteceu neste repositório e ficou sem rodar por semanas.
import { decidirTransicaoDoToggle } from '../lib/admin/toggle-transicao.ts';

let pass = 0, fail = 0;
function assert(nome, cond) {
  if (cond) { pass++; } else { fail++; console.log('  x ' + nome); }
}
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);

const NADA = { muda: false, religou: false, desligou: false };
const RELIGOU = { muda: true, religou: true, desligou: false };
const DESLIGOU = { muda: true, religou: false, desligou: true };

console.log('\n== SPEC-093 BLOCO D.1 — a transição do toggle ==\n');

// 🔴 O GATE ⑥, EM CÓDIGO. É a linha de controle obrigatória da SPEC.
assert('⑥ CONTROLE: ligado → ligar NÃO é religamento',
  eq(decidirTransicaoDoToggle(true, true), NADA));
assert('⑥ CONTROLE: desligado → desligar não mexe em nada',
  eq(decidirTransicaoDoToggle(false, false), NADA));

assert('ligado → desligar É desligamento',
  eq(decidirTransicaoDoToggle(true, false), DESLIGOU));
assert('desligado → ligar É religamento',
  eq(decidirTransicaoDoToggle(false, true), RELIGOU));

// ⚠️ A coluna pode nunca ter sido escrita. Nulo é DESLIGADO — e a saudação não
// sai por isso: corretora que nunca ligou o agente não tem conversa sem
// resposta para saudar.
assert('null → ligar conta como religamento',
  eq(decidirTransicaoDoToggle(null, true), RELIGOU));
assert('undefined → ligar conta como religamento',
  eq(decidirTransicaoDoToggle(undefined, true), RELIGOU));
assert('null → desligar não muda nada',
  eq(decidirTransicaoDoToggle(null, false), NADA));

// 🔴 E os três desfechos são MUTUAMENTE EXCLUSIVOS. Sem isto, um bug que
// devolvesse `{religou:true, desligou:true}` passaria em todas as linhas acima.
for (const [a, b] of [[true, true], [true, false], [false, true], [false, false],
                      [null, true], [null, false]]) {
  const r = decidirTransicaoDoToggle(a, b);
  assert(`(${a}→${b}) religou e desligou nunca são os dois`,
    !(r.religou && r.desligou));
  assert(`(${a}→${b}) muda = religou || desligou`,
    r.muda === (r.religou || r.desligou));
}

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
process.exit(fail ? 1 : 0);
