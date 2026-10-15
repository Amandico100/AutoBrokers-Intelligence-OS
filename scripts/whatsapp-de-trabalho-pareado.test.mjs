// modelo: claude-opus-5-5
// ===========================================================================
// SPEC-131-0-B3 F2 — A ABA "WhatsApp de trabalho": o PAREADO é o principal; o digitado é a reserva
// ===========================================================================
//
// O que este arquivo prova, rodando o CÓDIGO REAL (TSX transpilado, React renderizando; `require` falso só na borda):
//   ① conectado, a aba diz "Este é o seu WhatsApp de trabalho" (número MASCARADO + desde) e o formulário do número
//      digitado fica RECOLHIDO; sem conexão, o principal é "Conectar meu WhatsApp" e o digitado vira
//      "Não quer conectar? Informe só o número" (aberto só se já houver número digitado); linha indisponível → o
//      formulário volta a ser o principal.
//   ② nada promete envio a cliente como LIGADO: cobrança e renovação aos clientes só aparecem DEPOIS de
//      "Quando a sua corretora ligar"; o "Quero renovar" só é atribuído ao pareado quando o backend diz
//      `efetivo.origem === 'linha'` (backend antigo, sem `efetivo` → a tela não afirma o que não sabe).
//   ③ os dois BFF REPASSAM `whatsapp_trabalho.efetivo` e `pessoas[i].whatsapp_trabalho_origem` sem inventar; a
//      Situação da equipe diz "WhatsApp conectado" / "informado" / "não informado" pela origem.
//   ④ nenhum jargão nem nome interno na tela (Even, Jarvis, instância, linha, QR code, token…).
//
// MUTAÇÃO (relatório): tirar o "Este é o seu WhatsApp de trabalho" do estado conectado → ① fica VERMELHO.
//
// Rodar: node --test scripts/whatsapp-de-trabalho-pareado.test.mjs

import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const RAIZ = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const requireReal = createRequire(import.meta.url);
const ts = requireReal('typescript');
const React = requireReal('react');
const jsxRuntime = requireReal('react/jsx-runtime');
const { renderToStaticMarkup } = requireReal('react-dom/server');

const ler = (rel) => fs.readFileSync(path.join(RAIZ, rel), 'utf8');

function carregarTS(rel, resolver = () => undefined) {
  const js = ts.transpileModule(ler(rel), {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, esModuleInterop: true, jsx: ts.JsxEmit.ReactJSX,
    },
    fileName: rel,
  }).outputText;
  const mod = { exports: {} };
  const req = (id) => {
    if (id === 'react') return React;
    if (id === 'react/jsx-runtime') return jsxRuntime;
    const r = resolver(id);
    if (r === undefined) throw new Error(`import não previsto no teste: ${id} (em ${rel})`);
    return r;
  };
  // eslint-disable-next-line no-new-func
  new Function('require', 'module', 'exports', js)(req, mod, mod.exports);
  return mod.exports;
}

const nada = () => null;
const icones = new Proxy({}, { get: () => nada });
function stubComum(id) {
  if (id === 'lucide-react') return icones;
  if (id === '@/components/aplicativos/casca/CardDoAplicativo') return { BOTAO_PRIMARIO: 'botao-primario' };
  if (id === '@/components/aplicativos/casca/Confirmar') {
    return { Confirmar: ({ children, titulo, descricao }) => React.createElement('span', { 'data-confirmar': titulo, 'data-descricao': descricao }, children) };
  }
  if (id === '@/lib/utils') return { cn: (...a) => a.filter(Boolean).join(' ') };
  if (id === '@/components/ui/skeleton') return { Skeleton: () => React.createElement('div', { 'data-skeleton': '' }) };
  return undefined;
}

const perfilReal = carregarTS('components/perfil/useMeuPerfil.ts', stubComum);

/** a aba inteira, com a linha num estado dado (o hook da linha é a única borda trocada) */
function desenharAba({ linha, perfil }) {
  const perfilMod = {
    ...perfilReal,
    useLinhaDoWhatsApp: () => ({ linha, carregada: true, setLinha: () => {}, carregar: () => {} }),
  };
  const linhaMod = carregarTS('components/perfil/MinhaLinhaDoWhatsApp.tsx', (id) => (id === './useMeuPerfil' ? perfilMod : stubComum(id)));
  const abaMod = carregarTS('components/perfil/MeuWhatsAppDeTrabalho.tsx', (id) => {
    if (id === './useMeuPerfil') return perfilMod;
    if (id === './MinhaLinhaDoWhatsApp') return linhaMod;
    return stubComum(id);
  });
  return renderToStaticMarkup(React.createElement(abaMod.MeuWhatsAppDeTrabalho, { perfil, onMudou: () => {} }));
}

const PAREADO = '5511900000001';
const DIGITADO = '5548988887777';
const LINHA = (estado, extra = {}) => ({ estado, numero_mascarado: null, desde: null, motivo: null, ...extra });
const CONECTADA = LINHA('conectada', { numero_mascarado: '5511*****001', desde: '2026-10-15T12:00:00Z' });
const PERFIL = (wt = {}, extra = {}) => ({
  whatsapp_trabalho: { numero: null, confirmado_em: null, confirmado: false, disponivel: true, ...wt },
  ausencias: [], cubro: [], pessoas: [], eu: 'u', pode_gerir_todos: false, ...extra,
});
const COM_DIGITADO = { numero: DIGITADO, confirmado: true, confirmado_em: '2026-10-01T10:00:00Z' };
const texto = (html) => html.replace(/<[^>]+>/g, ' ').replace(/&quot;/g, '"').replace(/\s+/g, ' ');
/** o <details> que guarda o número digitado (ou null) */
const detalhes = (html) => /<details\b[^>]*>[\s\S]*?<\/details>/.exec(html)?.[0] ?? null;
const abreDetalhes = (html) => /<details\b[^>]*\bopen\b/.test(html);

// ─────────────────────────────────────────────────────────────────────────────
// ① o pareado é o principal
// ─────────────────────────────────────────────────────────────────────────────
test('① conectado: "Este é o seu WhatsApp de trabalho", o número MASCARADO, desde quando, e o digitado RECOLHIDO', () => {
  const html = desenharAba({
    linha: CONECTADA,
    perfil: PERFIL({ ...COM_DIGITADO, efetivo: { numero: PAREADO, origem: 'linha' } }),
  });
  const t = texto(html);
  assert.match(t, /Este é o seu WhatsApp de trabalho/);
  assert.match(t, /5511\*{5}001/);
  assert.match(t, /desde 15\/10\/2026/);
  assert.ok(!t.includes(PAREADO) && !/9\s?0000-0001/.test(t), 'o número pareado apareceu em claro');
  // o digitado diferente vira reserva, MASCARADO na frase
  assert.match(t, /O número 5548\*{5}777 que você informou antes fica guardado como reserva\./);
  const d = detalhes(html);
  assert.ok(d, 'o formulário do número digitado devia estar num bloco recolhível');
  assert.ok(!abreDetalhes(html), 'conectado, o número digitado fica RECOLHIDO');
  assert.ok(html.indexOf('Este é o seu WhatsApp de trabalho') < html.indexOf('<details'), 'o pareado vem ANTES da reserva');
  assert.match(html, /data-confirmar="Desconectar o seu WhatsApp\?"/);
});

test('① conectado com o MESMO número digitado: nenhuma frase de reserva', () => {
  const html = desenharAba({
    linha: CONECTADA,
    perfil: PERFIL({ ...COM_DIGITADO, numero: PAREADO, efetivo: { numero: PAREADO, origem: 'linha' } }),
  });
  assert.ok(!/fica guardado como reserva/.test(texto(html)));
});

test('① não conectado: título, "Conectar meu WhatsApp" como principal e "Não quer conectar? Informe só o número" recolhido', () => {
  const html = desenharAba({ linha: LINHA('nao_conectada'), perfil: PERFIL() });
  const t = texto(html);
  assert.match(t, /Seu WhatsApp de trabalho/);
  assert.match(t, /Conecte o WhatsApp que você usa com os clientes\. Ele passa a ser o seu número de trabalho no AutoBrokers\./);
  assert.match(html, /<button[^>]*>Conectar meu WhatsApp<\/button>/);
  const d = detalhes(html);
  assert.ok(d, 'falta o bloco recolhido do número digitado');
  assert.match(d, /<summary[^>]*>[\s\S]*Não quer conectar\? Informe só o número[\s\S]*<\/summary>/);
  assert.ok(!abreDetalhes(html), 'sem número digitado, o bloco começa fechado');
  assert.ok(html.indexOf('Conectar meu WhatsApp') < html.indexOf('<details'), 'o pareamento vem ANTES do número digitado');
  assert.ok(!/Este é o seu WhatsApp de trabalho/.test(t), 'sem conexão a tela não pode dizer que este é o WhatsApp de trabalho');
});

test('① não conectado, com número digitado e confirmado: o bloco "Não quer conectar?" já vem ABERTO', () => {
  const html = desenharAba({
    linha: LINHA('nao_conectada'),
    perfil: PERFIL({ ...COM_DIGITADO, efetivo: { numero: DIGITADO, origem: 'digitado' } }),
  });
  assert.ok(abreDetalhes(html), 'já há número digitado e nenhuma conexão: o bloco abre');
  assert.match(texto(detalhes(html)), /Não quer conectar\? Informe só o número/);
});

test('① indisponível para esta pessoa (desligada) ou sem leitura: o formulário do número é o PRINCIPAL', () => {
  for (const linha of [LINHA('desligada'), null]) {
    const html = desenharAba({ linha, perfil: PERFIL() });
    const t = texto(html);
    assert.equal(detalhes(html), null, 'sem conexão possível, nada fica recolhido');
    assert.ok(!/Conectar meu WhatsApp|Não quer conectar/.test(t));
    assert.match(t, /Seu WhatsApp de trabalho/);
    assert.match(html, /<form\b/);
    assert.match(t, /Confirmo que este é o WhatsApp em que eu atendo os clientes\./);
  }
});

test('① desconectado (caiu): a frase de hoje e "enquanto isso" o número de reserva, mascarado', () => {
  const html = desenharAba({
    linha: LINHA('desconectada', { desde: '2026-10-01T15:00:00Z' }),
    perfil: PERFIL({ ...COM_DIGITADO, efetivo: { numero: DIGITADO, origem: 'digitado' } }),
  });
  const t = texto(html);
  assert.match(t, /Seu WhatsApp desconectou do AutoBrokers em 01\/10\/2026/);
  assert.match(t, /Enquanto isso, o "Quero renovar" usa o número de reserva 5548\*{5}777\s?\./);
  const sem = texto(desenharAba({ linha: LINHA('desconectada'), perfil: PERFIL() }));
  assert.match(sem, /Enquanto isso, o "Quero renovar" vai para o número da corretora\./);
});

// ─────────────────────────────────────────────────────────────────────────────
// ② nenhuma promessa do que não está ligado
// ─────────────────────────────────────────────────────────────────────────────
test('② "Para que ele serve hoje" × "Quando a sua corretora ligar" × "Fica de fora": cobrança a cliente só no DEPOIS', () => {
  const t = texto(desenharAba({ linha: CONECTADA, perfil: PERFIL({ efetivo: { numero: PAREADO, origem: 'linha' } }) }));
  const iHoje = t.indexOf('Para que ele serve hoje');
  const iDepois = t.indexOf('Quando a sua corretora ligar');
  const iFora = t.indexOf('Fica de fora');
  assert.ok(iHoje >= 0 && iDepois > iHoje && iFora > iDepois, `ordem das três partes: ${iHoje} ${iDepois} ${iFora}`);
  const hoje = t.slice(iHoje, iDepois);
  const depois = t.slice(iDepois, iFora);
  assert.match(hoje, /Mensagem para você/);
  assert.match(hoje, /Quero renovar/);
  assert.ok(!/cobran[çc]a|aviso/i.test(hoje), `promessa de envio no "hoje": ${hoje}`);
  assert.match(depois, /[Aa]visos do AutoBrokers/);
  assert.match(depois, /[Cc]obrança e renovação/);
  assert.match(t.slice(iFora), /O atendimento aos segurados continua no número da corretora/);
});

test('② backend antigo (sem `efetivo`): a tela não atribui o "Quero renovar" ao pareado nem fala em reserva', () => {
  const t = texto(desenharAba({ linha: CONECTADA, perfil: PERFIL(COM_DIGITADO) }));
  assert.match(t, /Este é o seu WhatsApp de trabalho/);
  const hoje = t.slice(t.indexOf('Para que ele serve hoje'), t.indexOf('Quando a sua corretora ligar'));
  assert.ok(!/Quero renovar/.test(hoje), `sem o efetivo, "Quero renovar" no pareado é palpite: ${hoje}`);
  assert.ok(!/fica guardado como reserva/.test(t));
  // e com o efetivo dizendo "digitado" (ex.: conexão inativa no banco), também não
  const t2 = texto(desenharAba({ linha: CONECTADA, perfil: PERFIL({ ...COM_DIGITADO, efetivo: { numero: DIGITADO, origem: 'digitado' } }) }));
  assert.ok(!/Quero renovar/.test(t2.slice(t2.indexOf('Para que ele serve hoje'), t2.indexOf('Quando a sua corretora ligar'))));
});

test('② sem conexão, a frase "o AutoBrokers não se conecta a ele" continua; conectado, ela NÃO aparece', () => {
  const sem = texto(desenharAba({ linha: LINHA('desligada'), perfil: PERFIL(COM_DIGITADO) }));
  assert.match(sem, /o AutoBrokers não se conecta a ele/);
  const com = texto(desenharAba({ linha: CONECTADA, perfil: PERFIL({ ...COM_DIGITADO, efetivo: { numero: PAREADO, origem: 'linha' } }) }));
  assert.ok(!/não se conecta a ele/.test(com), 'conectado, "não se conecta" é mentira');
});

// ─────────────────────────────────────────────────────────────────────────────
// ③ os BFF repassam; a Situação da equipe lê a origem
// ─────────────────────────────────────────────────────────────────────────────
async function chamarGet(arq, respostaDoBackend) {
  const mod = carregarTS(arq, (id) => {
    if (id === 'next/server') return { NextResponse: { json: (body, init) => ({ body, status: init?.status ?? 200 }) } };
    if (id === '@/lib/admin/admin-auth') {
      return {
        assertSameOrigin: () => null,
        requireCompanyMember: async () => ({ ok: true, ctx: { companyId: 'c-1', userId: 'u-1', role: 'admin', isOwner: true } }),
      };
    }
    if (id === '@/lib/admin/admin-auth-policy') return { canWriteTenantConfig: () => true };
    if (id === '@/lib/backend-url') return { getBackendUrl: () => 'http://backend.teste' };
    return undefined;
  });
  const antigo = globalThis.fetch;
  globalThis.fetch = async () => ({ ok: true, status: 200, json: async () => structuredClone(respostaDoBackend) });
  try { return await mod.GET(); } finally { globalThis.fetch = antigo; }
}

test('③ BFF meu-perfil: `efetivo` atravessa igual; sem ele no backend, o BFF não inventa', async () => {
  const efetivo = { numero: PAREADO, origem: 'linha' };
  const r = await chamarGet('app/api/dashboard/meu-perfil/route.ts', PERFIL({ ...COM_DIGITADO, efetivo }));
  assert.equal(r.status, 200);
  assert.deepEqual(r.body.whatsapp_trabalho.efetivo, efetivo);
  const antigo = await chamarGet('app/api/dashboard/meu-perfil/route.ts', PERFIL(COM_DIGITADO));
  assert.equal(antigo.body.whatsapp_trabalho.efetivo, undefined);
});

test('③ BFF situação: `whatsapp_trabalho_origem` atravessa igual, pessoa por pessoa', async () => {
  const pessoas = [
    { user_id: 'a', nome: 'A', whatsapp_trabalho_origem: 'linha', whatsapp_trabalho_confirmado: true },
    { user_id: 'b', nome: 'B', whatsapp_trabalho_origem: 'digitado', whatsapp_trabalho_confirmado: true },
    { user_id: 'c', nome: 'C', whatsapp_trabalho_origem: null, whatsapp_trabalho_confirmado: false },
  ];
  const r = await chamarGet('app/api/dashboard/equipe/situacao/route.ts', { pessoas });
  assert.deepEqual(r.body.pessoas.map((p) => p.whatsapp_trabalho_origem), ['linha', 'digitado', null]);
});

test('③ Situação da equipe: "WhatsApp conectado" · "informado" · "não informado" pela origem; backend antigo como hoje', () => {
  const mod = carregarTS('app/dashboard/personalizacao/corretora/equipe/SituacaoDaEquipe.tsx', stubComum);
  assert.equal(typeof mod.sinalDoWhatsApp, 'function', 'SituacaoDaEquipe devia exportar sinalDoWhatsApp');
  const s = (o, c) => mod.sinalDoWhatsApp({ whatsapp_trabalho_origem: o, whatsapp_trabalho_confirmado: c });
  assert.deepEqual(s('linha', true), { tom: 'ok', texto: 'WhatsApp conectado' });
  assert.deepEqual(s('digitado', true), { tom: 'ok', texto: 'WhatsApp de trabalho informado' });
  assert.deepEqual(s(null, false), { tom: 'neutro', texto: 'WhatsApp de trabalho não informado' });
  // backend antigo (sem a origem): o confirmado decide, como hoje; null = a coluna não existe → nada
  assert.deepEqual(mod.sinalDoWhatsApp({ whatsapp_trabalho_confirmado: true }), { tom: 'ok', texto: 'WhatsApp de trabalho informado' });
  assert.equal(mod.sinalDoWhatsApp({ whatsapp_trabalho_confirmado: null }), null);
  const fonte = ler('app/dashboard/personalizacao/corretora/equipe/SituacaoDaEquipe.tsx');
  assert.match(fonte, /sinalDoWhatsApp\(p\)/, 'a lista não usa o sinal pela origem');
});

// ─────────────────────────────────────────────────────────────────────────────
// ④ sem jargão, sem nome interno
// ─────────────────────────────────────────────────────────────────────────────
test('④ nenhum estado da aba usa jargão ou nome interno (Even, Jarvis, Smith, instância, linha, QR code, token)', () => {
  const casos = [
    { linha: null, perfil: PERFIL() },
    { linha: LINHA('desligada'), perfil: PERFIL(COM_DIGITADO) },
    { linha: LINHA('nao_conectada'), perfil: PERFIL(COM_DIGITADO) },
    { linha: LINHA('aguardando_qr'), perfil: PERFIL() },
    { linha: CONECTADA, perfil: PERFIL({ ...COM_DIGITADO, efetivo: { numero: PAREADO, origem: 'linha' } }) },
    { linha: LINHA('desconectada'), perfil: PERFIL(COM_DIGITADO) },
    { linha: LINHA('limite'), perfil: PERFIL() },
  ];
  const JARGAO = /\bEven\b|Jarv[iy]s|\bSmith\b|inst[aâ]ncia|\blinha\b|QR\s*code|\btoken\b|webhook|\bE\.?164\b|pareamento/i;
  assert.ok(JARGAO.test('a instância') && JARGAO.test('Even') && !JARGAO.test('o seu WhatsApp de trabalho'), 'CONTROLE do detector');
  for (const c of casos) {
    const html = desenharAba(c);
    const t = texto(html) + ' ' + [...html.matchAll(/(?:aria-label|alt|data-descricao|data-confirmar)="([^"]*)"/g)].map((m) => m[1]).join(' ');
    assert.ok(!JARGAO.test(t), `jargão na tela (${c.linha?.estado ?? 'sem leitura'}): ${t.match(JARGAO)?.[0]}`);
  }
});
