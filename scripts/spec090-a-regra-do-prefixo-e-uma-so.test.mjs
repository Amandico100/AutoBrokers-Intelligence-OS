/**
 * A regra do prefixo existe em DOIS lugares — e este guarda é o que torna isso
 * honesto. SPEC-090, BLOCO C.
 *
 * 🔴 POR QUE A DUPLICAÇÃO EXISTE
 *
 * A decisão de verdade mora em `backend/app/services/a_nota_da_atendente.py`.
 * ⛔ Ela precisa existir no TypeScript também porque o proxy do painel escreve
 * DUAS vezes ANTES de chamar o backend — e uma delas é a que estraga tudo:
 *
 *     app/api/dashboard/conversas/[id]/route.ts
 *         "Auto-claim: enviar como humano PAUSA A IA e marca o dono."
 *
 * 🔴 Sem a cópia, escrever `#nota …` no painel pausaria o atendimento — o
 * *"anotar viraria assumir"* que o BLOCO C existe para impedir, e no pior lugar
 * possível: o painel é o ÚNICO caminho em que o produto garante que a nota não
 * sai para o segurado.
 *
 * ⚠️ **§5 diz que duas listas que precisam concordar divergem** — e a que fica
 * para trás é justamente a que deixa passar o erro. Este arquivo é o olho que
 * impede isso: ele lê os DOIS fontes e fica vermelho quando eles discordam.
 *
 * Uso:  node scripts/spec090-a-regra-do-prefixo-e-uma-so.test.mjs
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const RAIZ = join(dirname(fileURLToPath(import.meta.url)), '..');
const PY = join(RAIZ, 'backend', 'app', 'services', 'a_nota_da_atendente.py');
const TS = join(RAIZ, 'lib', 'atendimento', 'a-nota-da-atendente.ts');
const PROXY = join(RAIZ, 'app', 'api', 'dashboard', 'conversas', '[id]', 'route.ts');

let passou = 0;
const falhas = [];
function check(nome, ok, detalhe = '') {
  if (ok) { passou++; console.log(`  [ok] ${nome}`); }
  else { falhas.push([nome, detalhe]); console.log(`  [FALHOU] ${nome}`); }
}

const py = readFileSync(PY, 'utf8');
const ts = readFileSync(TS, 'utf8');
const proxy = readFileSync(PROXY, 'utf8');

console.log('== SPEC-090 BLOCO C — a regra do prefixo é UMA SÓ ==\n');

// ---------------------------------------------------------------------------
// 🔴 OS DOIS PADRÕES TÊM DE SER O MESMO
// ---------------------------------------------------------------------------
const mPy = py.match(/_PREFIXO_NO_COMECO = re\.compile\(r"([^"]+)",\s*re\.I\)/);
const mTs = ts.match(/return \/([^/]+)\/i\.test/);

check('o padrão do Python foi encontrado', !!mPy, py.slice(0, 200));
check('o padrão do TypeScript foi encontrado', !!mTs, ts.slice(0, 200));

if (mPy && mTs) {
  check('🔴 os DOIS padrões são idênticos', mPy[1] === mTs[1],
        `python: ${mPy[1]}\n  typescript: ${mTs[1]}`);
  check('os dois são insensíveis a maiúscula (o teclado capitaliza)',
        py.includes('re.I') && ts.includes('/i.test'));
  check('os dois ancoram no COMEÇO absoluto (sem \\s* antes)',
        mPy[1].startsWith('^#nota') && mTs[1].startsWith('^#nota'),
        `python: ${mPy[1]} | ts: ${mTs[1]}`);
}

// ---------------------------------------------------------------------------
// 🔴 E O COMPORTAMENTO BATE, caso a caso
// ---------------------------------------------------------------------------
// ⚠️ Comparar os textos dos padrões não basta: dois regex idênticos usados de
//    formas diferentes (`match` vs `search`) dão respostas diferentes. Aqui o
//    que se compara é a RESPOSTA.
const CASOS = [
  ['#nota o robô perguntou a placa duas vezes', true],
  ['#Nota o robô errou', true],
  ['#NOTA o robô errou', true],
  ['#nota: dois pontos servem', true],
  ['#nota- traço serve', true],
  ['o robô errou #nota', false],
  ['  #nota com espaço antes', false],
  ['\n#nota depois de quebra', false],
  ['#notas do dia', false],
  ['#notavel', false],
  ['Bom dia, já estou vendo seu caso', false],
  ['', false],
];

const { ehAnotacao } = await import(
  'file://' + TS.replace(/\\/g, '/').replace(/\.ts$/, '.ts')
).catch(async () => {
  // ⚠️ Node não importa `.ts` direto em toda versão. A alternativa é avaliar o
  //    padrão extraído — o que este guarda quer é a RESPOSTA, não o módulo.
  const re = new RegExp(mTs[1], 'i');
  return { ehAnotacao: (t) => re.test(String(t ?? '')) };
});

for (const [entrada, esperado] of CASOS) {
  const obtido = ehAnotacao(entrada);
  check(`TS: ${JSON.stringify(entrada).slice(0, 42)} → ${esperado}`,
        obtido === esperado, `obtido ${obtido}`);
}

// ---------------------------------------------------------------------------
// 🔴 O PROXY USA A REGRA — e nos três lugares que importam
// ---------------------------------------------------------------------------
check('o proxy importa a regra em vez de reescrevê-la',
      proxy.includes("from '@/lib/atendimento/a-nota-da-atendente'"));
check('🔴 o proxy NÃO tem um segundo regex de #nota',
      !/\/\^?#nota/.test(proxy.replace(/\/\/.*$/gm, '')),
      'há um regex de prefixo dentro do proxy — é a terceira cópia');

// ⛔ o auto-claim (que PAUSA A IA) não pode rodar para nota
//
// ⚠️ Casa o CÓDIGO, não a palavra. 📊 A primeira versão fazia
//    `proxy.split('Auto-claim')[1]` e pegava a menção no CABEÇALHO do arquivo —
//    a quinta vez nesta SPEC que uma asserção leu a prosa em vez do código.
const claim = proxy.slice(proxy.indexOf('const { error: claimErr }'), 400 +
                          proxy.indexOf('const { error: claimErr }'));
check('🔴 o auto-claim NÃO roda quando é anotação',
      /const \{ error: claimErr \} = ehNota \? \{ error: null \} : await supabase/
        .test(proxy),
      claim.slice(0, 220));

// ⛔ e `delivered` não pode dizer que a nota foi entregue
check('🔴 `delivered` é falso para anotação',
      /delivered\s*=\s*res\.ok\s*&&\s*!ehNota/.test(proxy),
      (proxy.match(/delivered = [^;]+;/g) || []).join(' | '));

// e a mensagem entra marcada
check('a mensagem gravada carrega `nota_interna`',
      /nota_interna:\s*ehNota/.test(proxy));

// ---------------------------------------------------------------------------
// 🔴 LINHA DE CONTROLE — prove que este guarda CONSEGUE ficar vermelho
// ---------------------------------------------------------------------------
{
  const divergente = ts.replace(mTs?.[1] ?? '', '^#anotacao');
  const m = divergente.match(/return \/([^/]+)\/i\.test/);
  check('CONTROLE: o guarda detecta padrões diferentes',
        !!m && m[1] !== (mPy?.[1] ?? ''),
        'se isto falhar, a comparação acima não compara nada');
}
{
  // 🔴 CONTROLE do guarda acima: com a exceção removida, ele TEM de reprovar.
  const semGuarda = proxy.replace(
    'const { error: claimErr } = ehNota ? { error: null } : await supabase',
    'const { error: claimErr } = await supabase');
  check('CONTROLE: o guarda detecta o auto-claim SEM a exceção',
        !/const \{ error: claimErr \} = ehNota \? \{ error: null \} : await supabase/
          .test(semGuarda) && semGuarda !== proxy,
        'o teste do auto-claim não tem como falhar — ele não guarda nada');
}

console.log(`\n== Resumo: ${passou} passaram, ${falhas.length} falharam ==`);
if (falhas.length) {
  for (const [n, d] of falhas) console.log(`  - ${n}: ${d}`);
  process.exit(1);
}
