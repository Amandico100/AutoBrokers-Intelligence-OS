#!/usr/bin/env node
/**
 * SPEC-131-0-B3 · F4 — a tela Custos em português, com dado honesto.
 *
 * Roda o código REAL (a view pura e o coletor do servidor com um cliente falso
 * só na borda do banco). Quatro perguntas:
 *   1. "Tokens" e "Even" não aparecem como texto de tela (mutação 7).
 *   2. linhas de DUAS corretoras → conta só a pedida (a view e o coletor).
 *   3. sem lançamento no razão → "A cobrança por uso ainda não começou" e
 *      nenhum R$ sai do custo do provedor (USD).
 *   4. rótulos humanos para os modelos medidos em 15/10.
 */
import { registerHooks } from 'node:module';
import { readFileSync } from 'node:fs';
import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';

const RAIZ = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

// O coletor importa '@/lib/...' (alias do Next). Só a borda de resolução é trocada.
registerHooks({
  resolve(spec, ctx, next) {
    if (spec.startsWith('@/')) {
      const alvo = path.join(RAIZ, spec.slice(2));
      const comExt = /\.[cm]?[jt]sx?$/.test(alvo) ? alvo : `${alvo}.ts`;
      return next(pathToFileURL(comExt).href, ctx);
    }
    return next(spec, ctx);
  },
});

const view = await import('../lib/admin/tenant-usage-view.ts');
const store = await import('../lib/admin/tenant-usage-store.ts');
const { buildUsoDaCorretora, rotuloDoModelo, rotuloDoAssistente, palavrasAproximadas } = view;

let pass = 0, fail = 0; const failures = [];
function assert(n, c) { if (c) { pass++; console.log(`  ✓ ${n}`); } else { fail++; failures.push(n); console.log(`  ✗ ${n}`); } }

const ler = (rel) => readFileSync(path.join(RAIZ, rel), 'utf8');
const semComentarios = (src) => src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/(^|[^:'"`])\/\/.*$/gm, '$1');

/** Texto que pode chegar à tela: literais de string e texto entre tags JSX. */
function textosDeTela(src, jsx = true) {
  const s = semComentarios(src);
  const out = [];
  for (const m of s.matchAll(/'([^'\n]*)'|"([^"\n]*)"|`([^`]*)`/g)) out.push(m[1] ?? m[2] ?? m[3] ?? '');
  if (jsx) for (const m of s.matchAll(/[>}]([^<>{}=]+)(?=[<{])/g)) out.push(m[1]);
  return out;
}
const PROIBIDO = /\bEven\b|\bTokens?\b|\btokens\b/;
const achaProibido = (src, jsx = true) => textosDeTela(src, jsx).filter((t) => PROIBIDO.test(t));

const A = '3aa75902-a3d5-4c5d-ac4b-66cbfbc782fe';
const B = '6c9c55e2-2f30-4ca2-a1ef-4ef464ed1b4a';
const agora = new Date().toISOString();
const log = (company_id, extra = {}) => ({ company_id, agent_id: null, model_name: 'gpt-6-luna', service_type: 'chat', input_tokens: 900, output_tokens: 100, total_cost_usd: 7.77, details: {}, created_at: agora, ...extra });

console.log('== SPEC-131-0-B3 F4 — Custos em português ==\n');

// ── 1. "Tokens" e "Even" fora da tela ───────────────────────────────────────
console.log('1. palavras que não existem no produto');
for (const rel of [
  'app/dashboard/personalizacao/corretora/custos/UsageClient.tsx',
  'app/dashboard/personalizacao/corretora/custos/page.tsx',
  'lib/admin/tenant-usage-store.ts',
  'lib/admin/tenant-usage-view.ts',
]) {
  const achados = achaProibido(ler(rel), rel.endsWith('.tsx'));
  assert(`${rel}: nenhum "Even"/"Tokens" em texto de tela${achados.length ? ` → ${JSON.stringify(achados.slice(0, 3))}` : ''}`, achados.length === 0);
}
// CONTROLE: o detector consegue ficar vermelho, e não confunde identificador com texto.
assert('controle: o detector pega um rótulo "Even" reintroduzido', achaProibido(`const r = role === 'attendance' ? 'Even' : 'x';`, false).length === 1);
assert('controle: o detector pega "tokens" em texto JSX', achaProibido('<span>{n} tokens</span>').length === 1);
assert('controle: identificador d.tokens não é texto de tela', achaProibido('const x = d.tokens + 1;').length === 0);
const sofia = { id: 'ag-1', name: 'Sofia', agent_role: 'attendance', company_id: A };
assert('atendimento leva o nome do banco ("Sofia")', rotuloDoAssistente(sofia) === 'Sofia');
assert('atendimento sem nome → "Atendimento"', rotuloDoAssistente({ ...sofia, name: null }) === 'Atendimento');
assert('core → "AutoBrokers" (mesmo se o banco disser "AutoBrokers Sandbox")', rotuloDoAssistente({ id: 'c', name: 'AutoBrokers Sandbox', agent_role: 'core', company_id: A }) === 'AutoBrokers');
assert('sem agente → "Outros usos"', rotuloDoAssistente(null) === 'Outros usos (sem assistente)');

// ── 2. isolamento: duas corretoras ──────────────────────────────────────────
console.log('\n2. duas corretoras, conta só a pedida');
const agentes = [
  { id: 'core-a', name: 'AutoBrokers Sandbox', agent_role: 'core', company_id: A },
  { id: 'att-a', name: 'Sofia', agent_role: 'attendance', company_id: A },
  { id: 'core-b', name: 'AutoBrokers', agent_role: 'core', company_id: B },
];
const logsMisturados = [
  log(A, { agent_id: 'core-a' }), log(A, { agent_id: 'att-a', model_name: 'claude-sonnet-5' }), log(A, { model_name: 'text-embedding-3-small' }),
  log(B, { agent_id: 'core-b' }), log(B), log(B), log(B), log(B),
  log(null), log(null),
];
const vA = buildUsoDaCorretora({ companyId: A, credits: null, ledger: [], logs: logsMisturados, agents: agentes, people: [] });
const vB = buildUsoDaCorretora({ companyId: B, credits: null, ledger: [], logs: logsMisturados, agents: agentes, people: [] });
assert(`A conta 3 chamadas (deu ${vA.uso.chamadas})`, vA.uso.chamadas === 3);
assert(`controle: B conta 5 com as MESMAS linhas (deu ${vB.uso.chamadas})`, vB.uso.chamadas === 5);
assert('linha sem corretora não entra em ninguém', vA.uso.chamadas + vB.uso.chamadas === 8);
assert('agente de OUTRA corretora não vira assistente de A', !vA.por_assistente.some((g) => g.rotulo === 'AutoBrokers' && g.chamadas > 1));
assert('A por assistente: AutoBrokers · Sofia · Outros usos', ['AutoBrokers', 'Sofia', 'Outros usos (sem assistente)'].every((r) => vA.por_assistente.some((g) => g.rotulo === r && g.chamadas === 1)));

// o coletor do servidor: filtra no banco E na view
function clienteFalso(tabelas, { respeitaFiltro = true } = {}) {
  const chamadas = [];
  return {
    chamadas,
    from(tabela) {
      const q = { tabela, eq: [], lt: [], range: null };
      chamadas.push(q);
      const linhas = () => {
        let rows = tabelas[tabela] ?? [];
        if (respeitaFiltro) for (const [c, v] of q.eq) rows = rows.filter((r) => r[c] === v);
        if (respeitaFiltro) for (const [c, v] of q.lt) rows = rows.filter((r) => Number(r[c]) < v);
        if (q.range) rows = rows.slice(q.range[0], q.range[1] + 1);
        return rows;
      };
      const b = {
        select: () => b, gte: () => b, order: () => b, limit: () => b, in: () => b,
        eq: (c, v) => { q.eq.push([c, v]); return b; },
        lt: (c, v) => { q.lt.push([c, v]); return b; },
        range: (de, ate) => { q.range = [de, ate]; return b; },
        maybeSingle: async () => ({ data: linhas()[0] ?? null, error: null }),
        then: (ok, ko) => Promise.resolve({ data: linhas(), error: null }).then(ok, ko),
      };
      return b;
    },
  };
}
const banco = { token_usage_logs: logsMisturados, agents: agentes, credit_transactions: [], company_credits: [], users_v2: [] };
const fiel = clienteFalso(banco);
const gA = await store.gatherUsage(fiel, A);
const qLogs = fiel.chamadas.filter((q) => q.tabela === 'token_usage_logs');
assert('coletor: toda consulta a token_usage_logs filtra company_id = A', qLogs.length > 0 && qLogs.every((q) => q.eq.some(([c, v]) => c === 'company_id' && v === A)));
assert('coletor: toda consulta (créditos, razão, agentes) filtra company_id = A', fiel.chamadas.filter((q) => q.tabela !== 'users_v2').every((q) => q.eq.some(([c, v]) => c === 'company_id' && v === A)));
assert(`coletor: A = 3 chamadas (deu ${gA.uso?.chamadas})`, gA.uso?.chamadas === 3);
const surdo = clienteFalso(banco, { respeitaFiltro: false });
const gSurdo = await store.gatherUsage(surdo, A);
assert(`banco que ignora o filtro: a view ainda conta só A (deu ${gSurdo.uso?.chamadas})`, gSurdo.uso?.chamadas === 3);

// ── 3. dinheiro só do razão ─────────────────────────────────────────────────
console.log('\n3. dinheiro só do razão; nunca do custo do provedor');
const cliente = ler('app/dashboard/personalizacao/corretora/custos/UsageClient.tsx');
assert('a frase "A cobrança por uso ainda não começou na sua conta." está na tela', cliente.includes('A cobrança por uso ainda não começou na sua conta.'));
assert('a tela não lê nenhum campo em dólar', !/usd/i.test(semComentarios(cliente)));
assert('sem razão: cobrança não começou', vA.cobranca.comecou === false && vA.cobranca.total_brl === 0);
const json = JSON.stringify(vA);
assert('nenhum valor do custo do provedor (7,77 USD × 3) aparece na view', !/usd/i.test(json) && !json.includes('7.77') && !json.includes('23.31'));
assert('sem linha em company_credits → sem cartão de saldo (null, não R$ 0,00)', vA.saldo === null);
const comRazao = buildUsoDaCorretora({
  companyId: A,
  credits: { balance_brl: 21.5, alert_80_sent: false, alert_100_sent: false },
  ledger: [
    { company_id: A, agent_id: 'core-a', type: 'usage', amount_brl: -3.5, created_at: agora },
    { company_id: A, agent_id: null, type: 'bonus', amount_brl: 25, created_at: agora },
    { company_id: B, agent_id: null, type: 'usage', amount_brl: -99, created_at: agora },
  ],
  logs: logsMisturados, agents: agentes, people: [],
});
assert(`controle: com débito no razão, cobrado = R$ 3,50 (deu ${comRazao.cobranca.total_brl})`, comRazao.cobranca.comecou === true && comRazao.cobranca.total_brl === 3.5);
assert('controle: bônus não é cobrança, e o débito da B não entra', comRazao.cobranca.lancamentos === 1);
assert('controle: com linha em company_credits o saldo aparece', comRazao.saldo?.balance_brl === 21.5);
const jaCobrou = buildUsoDaCorretora({ companyId: A, credits: null, ledger: [], logs: [], agents: [], people: [], cobrancaJaComecou: true });
assert('já houve débito antes dos 30 dias → R$ 0,00 honesto, não a frase', jaCobrou.cobranca.comecou === true && jaCobrou.cobranca.total_brl === 0);

// ── 4. rótulos humanos ──────────────────────────────────────────────────────
console.log('\n4. rótulos humanos de modelo');
const esperado = {
  'gpt-6-luna': 'OpenAI · GPT-6 Luna',
  'claude-sonnet-5': 'Anthropic · Claude Sonnet 5',
  'gpt-6-sol': 'OpenAI · GPT-6 Sol',
  'gpt-6.1-sol': 'OpenAI · GPT-6.1 Sol',
  'claude-sonnet-5-5': 'Anthropic · Claude Sonnet 5.5',
  'text-embedding-3-small': 'Busca no conhecimento',
  'claude-opus-5-5': 'Anthropic · Claude Opus 5.5',
  'gpt-4o-mini': 'OpenAI · GPT-4o mini',
  'gpt-4o-mini-2024-07-18': 'OpenAI · GPT-4o mini',
  'gpt-4o': 'OpenAI · GPT-4o',
  'gpt-6-astra': 'OpenAI · GPT-6 Astra',
  'gpt-5.6-terra': 'OpenAI · GPT-5.6 Terra',
  'claude-haiku-4-5-20251001': 'Anthropic · Claude Haiku 4.5',
  'rerank-multilingual-v3.0': 'Busca no conhecimento',
  'whisper-1': 'OpenAI · Transcrição de áudio',
};
for (const [m, r] of Object.entries(esperado)) assert(`${m} → "${r}" (deu "${rotuloDoModelo(m)}")`, rotuloDoModelo(m) === r);
assert('desconhecido da OpenAI → provedor + nome cru', rotuloDoModelo('gpt-9-nova') === 'OpenAI · gpt-9-nova');
assert('desconhecido da Anthropic → provedor + nome cru', rotuloDoModelo('claude-mythos-1') === 'Anthropic · claude-mythos-1');
assert('provedor desconhecido → "Outro modelo"', rotuloDoModelo('foo-model') === 'Outro modelo' && rotuloDoModelo(null) === 'Outro modelo');
assert('busca no conhecimento agrupa embedding e rerank', comRazao.por_modelo.filter((g) => g.rotulo === 'Busca no conhecimento').length === 1);

// ── volume em palavras (≈ ¾ de palavra por pedaço) ──────────────────────────
console.log('\n5. volume em palavras, nunca "tokens"');
assert(`1.141.062 pedaços → "≈ 856 mil palavras" (deu "${palavrasAproximadas(1141062)}")`, palavrasAproximadas(1141062) === '≈ 856 mil palavras');
assert(`1.600.000 → "≈ 1,2 milhão de palavras" (deu "${palavrasAproximadas(1600000)}")`, palavrasAproximadas(1600000) === '≈ 1,2 milhão de palavras');
assert(`4.000.000 → "≈ 3 milhões de palavras" (deu "${palavrasAproximadas(4000000)}")`, palavrasAproximadas(4000000) === '≈ 3 milhões de palavras');
assert(`800 → "≈ 600 palavras" (deu "${palavrasAproximadas(800)}")`, palavrasAproximadas(800) === '≈ 600 palavras');
assert('zero → "nenhuma palavra"', palavrasAproximadas(0) === 'nenhuma palavra');

// ── por pessoa só com atribuição ────────────────────────────────────────────
console.log('\n6. por pessoa só quando há atribuição');
assert('sem details.user_id → sem quebra por pessoa', vA.por_pessoa.length === 0);
const comPessoa = buildUsoDaCorretora({
  companyId: A, credits: null, ledger: [], agents: agentes,
  logs: [log(A, { details: { user_id: 'u1' } }), log(A, { details: { user_id: 'u1' } }), log(B, { details: { user_id: 'u9' } })],
  people: [{ id: 'u1', nome: 'Rafael Lima' }],
});
assert('com details.user_id → "Rafael Lima" com 2 respostas, e o u9 da B não aparece', comPessoa.por_pessoa.length === 1 && comPessoa.por_pessoa[0].rotulo === 'Rafael Lima' && comPessoa.por_pessoa[0].chamadas === 2);

// ── 7. a promessa "por pessoa" (conserto K2, BLOCKER de design) ─────────────
// 📊 15/10: 0 registros com details.user_id → a seção "Por pessoa" fica vazia. O subtítulo não pode prometer o que a
// tela não mostra, e a tela diz que ainda não separa por pessoa em vez de sumir calada. Roda o COMPONENTE REAL
// (TSX transpilado, React renderizando; só o `useState`/`useEffect` trocados na borda para entregar os dados).
console.log('\n7. "por pessoa": nada prometido que a tela não mostra');
const { createRequire } = await import('node:module');
const requireReal = createRequire(import.meta.url);
const ts = requireReal('typescript');
const ReactReal = requireReal('react');
const jsxRuntime = requireReal('react/jsx-runtime');
const { renderToStaticMarkup } = requireReal('react-dom/server');
function desenharUso(dados) {
  const js = ts.transpileModule(ler('app/dashboard/personalizacao/corretora/custos/UsageClient.tsx'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, esModuleInterop: true, jsx: ts.JsxEmit.ReactJSX },
  }).outputText;
  let n = 0;
  const reactFalso = { ...ReactReal, useEffect: () => {}, useState: () => [n++ === 0 ? dados : false, () => {}] };
  const mod = { exports: {} };
  const req = (id) => (id === 'react' ? reactFalso : id === 'react/jsx-runtime' ? jsxRuntime : (() => { throw new Error(`import não previsto: ${id}`); })());
  // eslint-disable-next-line no-new-func
  new Function('require', 'module', 'exports', js)(req, mod, mod.exports);
  return renderToStaticMarkup(ReactReal.createElement(mod.exports.UsageClient));
}
const FRASE_SEM_PESSOA = 'Ainda não separamos o uso por pessoa da equipe.';
const htmlSemPessoa = desenharUso({ ...vA, ok: true });
assert('sem atribuição: a tela diz que ainda não separa por pessoa', htmlSemPessoa.includes(FRASE_SEM_PESSOA));
assert('sem atribuição: nenhum título "Por pessoa" vazio', !/>Por pessoa</.test(htmlSemPessoa));
const htmlComPessoa = desenharUso({ ...comPessoa, ok: true });
assert('controle: com atribuição, "Por pessoa" e "Rafael Lima" aparecem, sem a frase', />Por pessoa</.test(htmlComPessoa) && htmlComPessoa.includes('Rafael Lima') && !htmlComPessoa.includes(FRASE_SEM_PESSOA));
const htmlSemUso = desenharUso({ ...buildUsoDaCorretora({ companyId: A, credits: null, ledger: [], logs: [], agents: [], people: [] }), ok: true });
assert('sem uso nenhum: só "Nenhum uso…", sem a frase de pessoa', htmlSemUso.includes('Nenhum uso da IA registrado') && !htmlSemUso.includes(FRASE_SEM_PESSOA));
const subtitulo = /subtitle="([^"]*)"/.exec(ler('app/dashboard/personalizacao/corretora/custos/page.tsx'))?.[1] ?? '';
const prometePessoa = (s) => /por pessoa/i.test(s);
assert('controle: o detector pega o subtítulo antigo', prometePessoa('nos últimos 30 dias — por assistente, por pessoa e por modelo — e'));
assert(`o subtítulo não promete "por pessoa" (a seção pode estar vazia) → "${subtitulo}"`, subtitulo.length > 0 && !prometePessoa(subtitulo));
// P9: rótulo dos cartões e rodapé com contraste (nada de `text-faint` em letra pequena)
assert('nenhum texto da tela em text-faint (contraste < 4,5:1)', !/text-faint/.test(ler('app/dashboard/personalizacao/corretora/custos/UsageClient.tsx')));

console.log(`\n== Resumo: ${pass} passaram, ${fail} falharam ==`);
if (fail > 0) { for (const f of failures) console.log(`  - ${f}`); process.exit(1); }
process.exit(0);
