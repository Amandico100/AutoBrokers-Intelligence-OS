// SPEC-132-A · A1 — O CHAT NOVO: a caixa que cabe no celular, lê o que se manda e copia a resposta.
//
// Roda com: node scripts/o-chat-novo.test.mjs   (ou `npm run test:chat-novo`; também passa por `node --test`)
//
// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
// O QUE ELE GUARDA — o BLOCO 0 da SPEC-132-A (📊 medido em 14/10/2026)
// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
//   B3   `useImageUpload.ts:104` lia um campo que a rota de upload NUNCA devolveu → o anexo sumia sem aviso
//   B9   textarea a 14 px (o iPhone dá zoom), `body{min-height:100vh}` contra o `h-[100dvh]` do casco, sem `viewport`
//   B10  0 "Copiar"; 0 foco no composer — o corretor digitava e nada aparecia
//   D-132A-01  o composer era renderizado em DOIS lugares da página e REMONTAVA na 1ª mensagem
//   D-132A-02  a barra de 6 atalhos do rodapé sai do celular
//   D-132A-08  o esforço lembrado no aparelho; valor estranho = Equilibrado
//
// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
// COMO FUNCIONA — sem rede, sem banco, sem navegador (o molde de o-chat-responde-e-continua.test.mjs)
// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
// Os arquivos REAIS são transpilados com o TypeScript do projeto e carregados com um `require` falso. Três modos:
//   · HTML real: `react-dom/server` desenha o Composer e a bolha de verdade (o placeholder, o Copiar, as fichas);
//   · React dublê com efeitos: o Composer roda os SEUS efeitos sobre um campo falso que conta `focus()`;
//   · a página inteira (`app/dashboard/chat/page.tsx`) sobre o dublê do teste do shell: o `fetch` ao
//     `/api/chat/stream` é registrado e o CORPO que a tela manda é conferido campo a campo.
// Dublê só na borda: a rede (`fetch`), o markdown (react-markdown é ESM puro), o toast e os ícones do avatar.
//
// MUTAÇÕES (o guarda fica VERMELHO com o defeito de volta — feitas em disco, restauradas por cópia; ver relatório):
//   1 `anexos.ts` volta a aceitar `publicUrl` como sucesso          → [5]
//   2 o foco ao abrir/trocar de conversa some do Composer             → [2]
//   3 o composer volta a ser renderizado em dois lugares da página    → [3]
//   4 o pedido deixa de levar `attachments`                           → [4]
//   5 a linha de Copiar some da bolha do AutoBrokers                  → [6]
//   6 a barra do rodapé volta ao casco                                → [7]
//   7 o esforço salvo é aceito sem conferir                           → [8]
//   8 `body{min-height:100vh}` volta                                  → [9]
//   SPEC-132 · A5 ([11] — a página VIVA; 9 no disco, 10–15 numa cópia via PAGINA_VIVA_SOB_TESTE=<cópia mutada>):
//   9  `juntarChegadas` sem o dedupe (`if (false)`)                    → [11] 11 vermelhos
//   10 a consulta não pausa com `document.hidden`                     → [11c]
//   11 sem o prazo de 10 min                                           → [11d]
//   12 `prometeuCalcular` liga para todo turno com texto              → [11b] 4 vermelhos
//   13 ao abrir, sem conferir a idade da promessa                      → [11e]
//   14 a espera nunca encerra ao chegar a resposta                     → [11a/c/e/g] 5 vermelhos
//   15 a mensagem de um humano encerra a espera                        → [11i]

import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const RAIZ = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const ts = require('typescript');
const ReactReal = require('react');
const { renderToStaticMarkup } = require('react-dom/server');

let falhas = 0;
function checar(cond, nome, detalhe = '') {
  if (cond) console.log(`  OK  ${nome}`);
  else {
    falhas += 1;
    console.log(`  X   ${nome}${detalhe ? `  — ${detalhe}` : ''}`);
  }
}
function fonte(rel) { return fs.readFileSync(path.join(RAIZ, rel), 'utf8'); }
function existe(rel) { return fs.existsSync(path.join(RAIZ, rel)); }

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
// O carregador: TypeScript real, `require` falso, módulos do projeto resolvidos por caminho.
// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
function resolverCaminho(id, deQuem) {
  let base;
  if (id.startsWith('@/')) base = path.join(RAIZ, id.slice(2));
  else if (id.startsWith('.')) base = path.resolve(path.dirname(deQuem), id);
  else return null;
  for (const ext of ['', '.ts', '.tsx', '/index.ts', '/index.tsx']) {
    const c = base + ext;
    if (fs.existsSync(c) && fs.statSync(c).isFile()) return c;
  }
  return null;
}

/**
 * Carrega um arquivo do projeto. `stubs(id, deQuem)` devolve o dublê de um import (ou `undefined` para seguir):
 * módulos npm sem dublê vêm do node_modules; módulos do projeto são carregados recursivamente (com cache).
 */
function criarCarregador({ React, stubs = () => undefined, jsx = true }) {
  const cache = new Map();
  function carregar(abs) {
    if (cache.has(abs)) return cache.get(abs).exports;
    const saida = ts.transpileModule(fs.readFileSync(abs, 'utf8'), {
      compilerOptions: {
        module: ts.ModuleKind.CommonJS,
        target: ts.ScriptTarget.ES2020,
        esModuleInterop: true,
        jsx: jsx ? ts.JsxEmit.React : ts.JsxEmit.None,
      },
      fileName: abs,
    }).outputText;
    const mod = { exports: {} };
    cache.set(abs, mod);
    const req = (id) => {
      const s = stubs(id, abs);
      if (s !== undefined) return s;
      if (id === 'react') return React;
      const projeto = resolverCaminho(id, abs);
      if (projeto) return carregar(projeto);
      if (id.startsWith('@/') || id.startsWith('.')) throw new Error(`import do projeto nao encontrado: ${id} (de ${abs})`);
      return require(id);
    };
    // eslint-disable-next-line no-new-func
    new Function('require', 'module', 'exports', 'React', saida)(req, mod, mod.exports, React);
    return mod.exports;
  }
  return (rel) => carregar(path.isAbsolute(rel) ? rel : path.join(RAIZ, rel));
}

/** Os dublês de borda para o HTML real. */
function stubsDeBorda(id) {
  if (id === 'sonner') { const t = () => {}; t.error = () => {}; t.success = () => {}; return { toast: t }; }
  if (id === 'next/link') {
    const Link = ({ href, children, ...resto }) => ReactReal.createElement('a', { href, ...resto }, children);
    return { __esModule: true, default: Link };
  }
  if (id === 'react-markdown') {
    // react-markdown é ESM puro: o dublê desenha o markdown CRU (o que se testa aqui é a bolha, não o parser)
    const Md = ({ children }) => ReactReal.createElement('div', { 'data-markdown': '' }, children);
    return { __esModule: true, default: Md };
  }
  if (id === 'remark-gfm') return { __esModule: true, default: () => {} };
  if (id === '@/components/ui/avatar') {
    const C = ({ children }) => ReactReal.createElement('span', null, children);
    return { Avatar: C, AvatarImage: () => null, AvatarFallback: C };
  }
  return undefined;
}

const carregarReal = criarCarregador({ React: ReactReal, stubs: stubsDeBorda });

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
// React dublê COM efeitos (para o foco): render → liga as refs aos elementos falsos → roda os efeitos.
// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
function criarReactComEfeitos() {
  let slots = [];
  let cursor = 0;
  let pendentes = [];
  const React = {
    useState(inicial) {
      const i = cursor++;
      if (!(i in slots)) slots[i] = { v: typeof inicial === 'function' ? inicial() : inicial };
      const s = slots[i];
      return [s.v, (nv) => { s.v = typeof nv === 'function' ? nv(s.v) : nv; }];
    },
    useRef(v) { const i = cursor++; if (!(i in slots)) slots[i] = { v: { current: v } }; return slots[i].v; },
    // como o React: a MESMA função enquanto as dependências não mudam (senão todo efeito que depende dela
    // rodaria a cada render, e o guarda do foco passaria por acaso)
    useCallback(fn, deps) { return React.useMemo(() => fn, deps); },
    useMemo(fn, deps) {
      const i = cursor++;
      const antes = slots[i];
      const igual = antes && deps && antes.deps && deps.length === antes.deps.length && deps.every((d, k) => Object.is(d, antes.deps[k]));
      if (!igual) slots[i] = { v: fn(), deps };
      return slots[i].v;
    },
    useImperativeHandle(ref, fn) { cursor++; if (ref && typeof ref === 'object') ref.current = fn(); },
    useEffect(fn, deps) {
      const i = cursor++;
      const antes = slots[i];
      const mudou = !antes || !deps || !antes.deps || deps.length !== antes.deps.length || deps.some((d, k) => !Object.is(d, antes.deps[k]));
      slots[i] = { deps, limpar: antes?.limpar };
      if (mudou) pendentes.push({ i, fn });
    },
    forwardRef(render) { const C = (props) => render(props, props.ref ?? null); C.render = render; return C; },
    memo(c) { return c; },
    createElement(tipo, props, ...filhos) { return { tipo, props: props || {}, filhos }; },
    Fragment: 'FRAGMENT',
  };
  React.useLayoutEffect = React.useEffect;
  function render(Comp, props) {
    cursor = 0;
    pendentes = [];
    const arvore = Comp(props);
    return arvore;
  }
  function rodarEfeitos() {
    for (const { i, fn } of pendentes) {
      if (typeof slots[i].limpar === 'function') slots[i].limpar();
      const r = fn();
      slots[i].limpar = typeof r === 'function' ? r : undefined;
    }
    pendentes = [];
  }
  return { React, render, rodarEfeitos };
}

function* nos(arvore) {
  if (arvore == null || typeof arvore !== 'object') return;
  if (Array.isArray(arvore)) { for (const x of arvore) yield* nos(x); return; }
  yield arvore;
  if (arvore.filhos) yield* nos(arvore.filhos);
  if (arvore.props && arvore.props.children) yield* nos(arvore.props.children);
}

// ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════
console.log('\n[1] A caixa: "Peça ao AutoBrokers", UM campo, 16 px (sem o zoom do iPhone), sem brilho que segue o mouse');
// ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════
const ComposerMod = carregarReal('components/chat/composer/Composer.tsx');
const htmlDoComposer = renderToStaticMarkup(ReactReal.createElement(ComposerMod.Composer, { onSendMessage: () => {} }));
checar(/placeholder="Peça ao AutoBrokers"/.test(htmlDoComposer), 'o placeholder é exatamente "Peça ao AutoBrokers"');
checar((htmlDoComposer.match(/<textarea/g) || []).length === 1, 'o composer desenha UM campo', `${(htmlDoComposer.match(/<textarea/g) || []).length} textarea(s)`);
const classeDoCampo = (/<textarea[^>]*class="([^"]*)"/.exec(htmlDoComposer) || [])[1] || '';
checar(/\btext-base\b/.test(classeDoCampo) && !/\btext-sm\b|\btext-xs\b/.test(classeDoCampo), 'o campo tem 16 px (text-base) e não 14 px', classeDoCampo);
checar(/aria-label="Adicionar fotos, arquivos e opções"/.test(htmlDoComposer), 'o "+" está na caixa');
checar(/aria-label="Gravar áudio"/.test(htmlDoComposer), 'vazia, a caixa mostra o microfone à direita');
const fontesDoComposer = fs.readdirSync(path.join(RAIZ, 'components/chat/composer'))
  .filter((f) => /\.tsx?$/.test(f)).map((f) => fonte(`components/chat/composer/${f}`)).join('\n');
checar(!/mousemove/.test(fontesDoComposer), 'nenhum ouvinte de mousemove (o brilho que seguia o mouse morreu)');
checar(!/Digite sua mensagem/.test(fontesDoComposer + fonte('app/dashboard/chat/page.tsx')), 'o placeholder antigo sumiu');
{
  // a caixa ENVIAR aparece quando há texto (o mesmo botão que era microfone)
  const comTexto = renderToStaticMarkup(ReactReal.createElement(ComposerMod.Composer, { onSendMessage: () => {}, initialText: 'Cotação do Onix' }));
  checar(/aria-label="Enviar"/.test(comTexto) && !/aria-label="Gravar áudio"/.test(comTexto), 'com texto, o microfone vira ENVIAR');
  const correndo = renderToStaticMarkup(ReactReal.createElement(ComposerMod.Composer, { onSendMessage: () => {}, turnStatus: 'streaming', onStop: () => {} }));
  checar(/aria-label="Parar a resposta"/.test(correndo), 'enquanto responde, o botão vira PARAR');
  checar(/Cotação do Onix<\/textarea>/.test(comTexto), '`?pergunta=` (initialText) nasce no campo');
}

// ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════
console.log('\n[2] O foco: o cursor está na caixa ao abrir, ao trocar de conversa e quando a resposta termina (notebook)');
// ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════
function medirFoco(arquivoDoComposer = 'components/chat/composer/Composer.tsx') {
  const { React, render, rodarEfeitos } = criarReactComEfeitos();
  const stubs = (id, deQuem) => {
    const b = stubsDeBorda(id);
    if (b !== undefined) return b;
    if (id === 'lucide-react') return new Proxy({}, { get: () => () => null });
    // os filhos do Composer são só elementos nesta árvore rasa (não são desenhados)
    if (/\/(FichaDeAnexo|FolhaDoMais|GravadorDeAudio)$/.test(id)) return new Proxy({}, { get: (_t, k) => (k === '__esModule' ? true : () => null) });
    return undefined;
  };
  const carregar = criarCarregador({ React, stubs });
  const globaisAntes = { window: globalThis.window, document: globalThis.document, raf: globalThis.requestAnimationFrame };
  globalThis.window = { addEventListener() {}, removeEventListener() {}, localStorage: null };
  globalThis.document = { activeElement: null, body: {} };
  globalThis.requestAnimationFrame = (fn) => { fn(0); return 0; };
  try {
    const { Composer } = carregar(arquivoDoComposer);
    let focos = 0;
    const campo = { value: '', style: {}, scrollHeight: 44, focus() { focos += 1; }, setSelectionRange() {} };
    const passo = (props) => {
      const arvore = render(Composer, props);
      for (const n of nos(arvore)) {
        if (n.tipo === 'textarea' && n.props.ref && typeof n.props.ref === 'object') n.props.ref.current = campo;
      }
      rodarEfeitos();
      return arvore;
    };
    const base = { onSendMessage() {}, focoKey: 'conversa-1', turnStatus: 'idle' };
    const arvore = passo(base);
    const aoAbrir = focos;
    passo({ ...base, focoKey: 'conversa-2' });
    const aoTrocar = focos - aoAbrir;
    passo({ ...base, focoKey: 'conversa-2', turnStatus: 'streaming' });
    const antesDoFim = focos;
    passo({ ...base, focoKey: 'conversa-2', turnStatus: 'complete' });
    const aoTerminar = focos - antesDoFim;
    const textarea = [...nos(arvore)].find((n) => n.tipo === 'textarea');
    return { aoAbrir, aoTrocar, aoTerminar, autoFocus: Boolean(textarea?.props.autoFocus) };
  } finally {
    globalThis.window = globaisAntes.window;
    globalThis.document = globaisAntes.document;
    globalThis.requestAnimationFrame = globaisAntes.raf;
  }
}
const ARQ_COMPOSER = process.env.COMPOSER_SOB_TESTE || 'components/chat/composer/Composer.tsx';
const foco = medirFoco(ARQ_COMPOSER);
console.log(`      focus() ao abrir: ${foco.aoAbrir} · ao trocar de conversa: ${foco.aoTrocar} · ao terminar a resposta: ${foco.aoTerminar}`);
checar(foco.aoAbrir >= 1, 'ao abrir o chat, o campo recebe o foco (o efeito, não só o atributo)');
checar(foco.autoFocus, 'o campo também nasce com autoFocus');
checar(foco.aoTrocar >= 1, 'ao trocar/criar conversa (focoKey muda), o foco volta para a caixa');
checar(foco.aoTerminar >= 1, 'quando a resposta termina (notebook), o foco volta para a caixa');

// ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════
console.log('\n[3] UM composer na página, na MESMA posição da árvore vazia e com conversa (não remonta na 1ª mensagem)');
// ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════
const AG = '33333333-3333-4333-8333-333333333333';
const UID = '11111111-1111-4111-8111-111111111111';
function respostaSSE(eventos) {
  const linhas = eventos.map((e) => `data: ${JSON.stringify(e)}\n\n`).join('') + 'data: [DONE]\n\n';
  const bytes = new TextEncoder().encode(linhas);
  let entregue = false;
  const body = new ReadableStream({ pull(c) { if (entregue) { c.close(); return; } c.enqueue(bytes); entregue = true; } });
  return { ok: true, status: 200, body, json: async () => ({}) };
}
/**
 * A página real sobre o dublê do teste do shell: `useState` semeado POR POSIÇÃO (0 = messages, 1 = turno,
 * 5/6/7 = agents/selectedAgentId/agentsLoaded — a mesma ordem que `o-chat-responde-e-continua` fixa).
 */
function montarPagina({ mensagens = [], turno = null, arquivo = 'app/dashboard/chat/page.tsx', seedsExtra = {}, toasts = null } = {}) {
  const seeds = { 5: [{ id: AG, name: 'Agente Alfa' }], 6: AG, 7: true, ...seedsExtra };
  if (mensagens.length) seeds[0] = mensagens;
  if (turno) seeds[1] = turno;
  let idx = 0;
  const React = {
    useState(inicial) {
      const i = idx++;
      const v = Object.prototype.hasOwnProperty.call(seeds, i) ? seeds[i] : typeof inicial === 'function' ? inicial() : inicial;
      return [v, () => {}];
    },
    useRef(v) { return { current: v }; },
    useCallback(fn) { return fn; },
    useEffect() {},
    createElement(tipo, props, ...filhos) { return { tipo, props: props || {}, filhos }; },
    Fragment: 'FRAGMENT',
  };
  const marcador = (nome) => {
    const f = function () { return null; };
    f.nome = nome;
    return f;
  };
  const MARCADORES = {
    '@/components/chat/ChatWelcome': { ChatWelcome: marcador('ChatWelcome') },
    '@/components/chat/LinhaDeAtividade': { LinhaDeAtividade: marcador('LinhaDeAtividade') },
    '@/components/chat/AvisoDoTurno': { AvisoDoTurno: marcador('AvisoDoTurno') },
    '@/components/chat/VoltarAoFim': { VoltarAoFim: marcador('VoltarAoFim') },
    '@/components/chat/composer/Composer': { Composer: marcador('Composer') },
    '@/components/MessageBubble': { MessageBubble: marcador('MessageBubble') },
    '@/components/TypingIndicator': { TypingIndicator: marcador('TypingIndicator') },
    '@/lib/supabase': { supabase: { channel: () => ({ on: () => ({ subscribe: () => ({}) }) }), removeChannel() {} } },
    '@/lib/types': {},
    '@/hooks/useUserId': { useUserId: () => ({ userId: UID, userAvatar: null, userName: 'Ana Teste', isLoading: false }) },
    sonner: { toast: { error(t) { if (toasts) toasts.push(String(t)); }, success() {} } },
  };
  const carregar = criarCarregador({
    React,
    stubs: (id) => {
      if (id in MARCADORES) return MARCADORES[id];
      if (id === '@/lib/chat/protocolo') return undefined; // o real
      return undefined;
    },
  });
  const pagina = carregar(arquivo);
  const arvore = pagina.default();
  return { arvore };
}
/** O caminho (índices + tipos) da raiz até o 1º nó que satisfaz `prever`. */
function caminhoAte(arvore, prever) {
  function busca(no, trilha) {
    if (no == null || typeof no !== 'object') return null;
    if (Array.isArray(no)) {
      for (let i = 0; i < no.length; i++) { const r = busca(no[i], [...trilha, `[${i}]`]); if (r) return r; }
      return null;
    }
    const nome = typeof no.tipo === 'string' ? no.tipo : no.tipo?.nome || 'Componente';
    const aqui = [...trilha, nome + (no.props?.key != null ? `#${no.props.key}` : '')];
    if (prever(no)) return aqui;
    return busca(no.filhos, aqui) || (no.props?.children ? busca(no.props.children, [...aqui, 'children']) : null);
  }
  return busca(arvore, []);
}
const ehComposer = (n) => n.props && typeof n.props.onSendMessage === 'function';
const msgsDeConversa = [
  { id: 'm-user-1', role: 'user', content: 'Qual o prêmio?', type: 'text', created_at: '2026-10-14T10:00:00Z', payload: { client_request_id: 'crid-1' } },
  { id: 'm-ab-1', role: 'assistant', content: 'O prêmio é **R$ 1.200**.', type: 'text', created_at: '2026-10-14T10:00:05Z', payload: { client_request_id: 'crid-1' } },
];
const ARQ_PAGINA = process.env.PAGINA_SOB_TESTE || 'app/dashboard/chat/page.tsx';
{
  const vazia = montarPagina({ arquivo: ARQ_PAGINA });
  const cheia = montarPagina({ mensagens: msgsDeConversa, arquivo: ARQ_PAGINA });
  const nVazia = [...nos(vazia.arvore)].filter(ehComposer).length;
  const nCheia = [...nos(cheia.arvore)].filter(ehComposer).length;
  checar(nVazia === 1 && nCheia === 1, 'exatamente UM composer na conversa vazia e UM na conversa com mensagens', `vazia=${nVazia} cheia=${nCheia}`);
  const cVazia = caminhoAte(vazia.arvore, ehComposer);
  const cCheia = caminhoAte(cheia.arvore, ehComposer);
  console.log(`      caminho do composer · vazia: ${cVazia && cVazia.join(' > ')}`);
  console.log(`      caminho do composer · cheia: ${cCheia && cCheia.join(' > ')}`);
  checar(cVazia && cCheia && cVazia.join('>') === cCheia.join('>'), 'o composer fica na MESMA posição da árvore nos dois estados (o React não o remonta)');
  // CONTROLE: o detector de posição CONSEGUE ver a diferença (o desenho antigo: em dois ramos distintos)
  const h = (t, p, ...f) => ({ tipo: t, props: p || {}, filhos: f });
  const C = { nome: 'Composer' };
  const antigoVazio = h('div', null, h('div', null, h('div', null, h(C, { onSendMessage() {} }))));
  const antigoCheio = h('div', null, h('FRAGMENT', null, h('div', null), h('div', null, h(C, { onSendMessage() {} }))));
  const a = caminhoAte(antigoVazio, ehComposer).join('>');
  const b = caminhoAte(antigoCheio, ehComposer).join('>');
  checar(a !== b, 'CONTROLE: o desenho antigo (composer em dois ramos) dá caminhos DIFERENTES');
}

// ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════
console.log('\n[4] O envio: `attachments` (só bucket/path/nome/mime/bytes) e `options.esforco` no POST /api/chat/stream');
// ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════
async function enviarPelaPagina(...args) {
  const chamadas = [];
  const fetchAntes = globalThis.fetch;
  globalThis.fetch = async (url, opts = {}) => {
    let body = null;
    try { body = opts.body ? JSON.parse(opts.body) : null; } catch { body = opts.body; }
    chamadas.push({ url: String(url), body });
    return respostaSSE([{ protocol: 'autobrokers.interaction.v1', seq: 1, type: 'turn.completed', turn: {}, payload: { status: 'complete' } }]);
  };
  const consoleAntes = { log: console.log, error: console.error };
  try {
    const { arvore } = montarPagina({ arquivo: ARQ_PAGINA });
    const composer = [...nos(arvore)].find(ehComposer);
    console.error = () => {};
    await composer.props.onSendMessage(...args);
  } finally {
    globalThis.fetch = fetchAntes;
    Object.assign(console, consoleAntes);
  }
  return chamadas.filter((c) => /\/api\/chat\/stream$/.test(c.url));
}
const ANEXO_PDF = {
  bucket: 'chat-docs', path: 'co-alfa/u-ana/chat-docs/0b6a.pdf', nome: 'apolice.pdf', mime: 'application/pdf', bytes: 182345,
  url: '/api/storage/chat-docs/co-alfa/u-ana/chat-docs/0b6a.pdf',
};
const ANEXO_FOTO = {
  bucket: 'chat-media', path: 'co-alfa/u-ana/chat-media/77aa.jpg', nome: 'placa.jpg', mime: 'image/jpeg', bytes: 90210,
  url: '/api/storage/chat-media/co-alfa/u-ana/chat-media/77aa.jpg', previewUrl: 'blob:local-1',
};
{
  const [pedido] = await enviarPelaPagina('Segue a apólice e a foto', [ANEXO_PDF, ANEXO_FOTO], { esforco: 'maximo' });
  const corpo = pedido?.body || {};
  console.log(`      corpo: ${JSON.stringify({ ...corpo, sessionId: '…', client_request_id: '…', assistantMessageId: '…' })}`);
  checar(Boolean(pedido), 'o envio chama POST /api/chat/stream');
  const esperado = [
    { bucket: 'chat-docs', path: ANEXO_PDF.path, nome: 'apolice.pdf', mime: 'application/pdf', bytes: 182345 },
    { bucket: 'chat-media', path: ANEXO_FOTO.path, nome: 'placa.jpg', mime: 'image/jpeg', bytes: 90210 },
  ];
  checar(JSON.stringify(corpo.attachments) === JSON.stringify(esperado), 'attachments = [{bucket, path, nome, mime, bytes}] — nem a URL nem a miniatura local saem da tela', JSON.stringify(corpo.attachments));
  // 15/10: a opção "Pesquisa na web" saiu (ela só mandava usar uma ferramenta que o Core nem tem — graph.py); o corpo
  // não leva mais `web_search`, e a pesquisa é decisão do modelo (`pesquisar_na_web`).
  checar(corpo.options && corpo.options.esforco === 'maximo' && !('web_search' in corpo.options), 'options = {esforco:"maximo"}, sem web_search', JSON.stringify(corpo.options));
  checar(!('imageUrl' in corpo) && !('fileUrl' in corpo) && !('fileName' in corpo), 'o chat novo não manda mais imageUrl/fileUrl/fileName');
  checar(corpo.chatInput === 'Segue a apólice e a foto' && typeof corpo.client_request_id === 'string' && corpo.client_request_id.length > 10, 'chatInput e client_request_id continuam no corpo');
  checar(!('companyId' in corpo) && !('userId' in corpo) && !('agentId' in corpo), 'nenhum companyId/userId/agentId no corpo (a corretora vem da sessão)');

  const [semNada] = await enviarPelaPagina('oi');
  checar(semNada && semNada.body.options.esforco === 'equilibrado' && Array.isArray(semNada.body.attachments) && semNada.body.attachments.length === 0, 'sem escolha: esforco "equilibrado" e attachments []', JSON.stringify(semNada && semNada.body.options));
  const [turbo] = await enviarPelaPagina('oi', [], { esforco: 'turbo' });
  checar(turbo && turbo.body.options.esforco === 'equilibrado', 'esforco "turbo" não sai da tela: vira "equilibrado"', JSON.stringify(turbo && turbo.body.options));
}

// ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════
console.log('\n[5] O anexo é lido pelo contrato NOVO: `{ok, bucket, path…}` — o campo fantasma `publicUrl` não existe');
// ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════
const ARQ_ANEXOS = process.env.ANEXOS_SOB_TESTE || 'components/chat/composer/anexos.ts';
const A = carregarReal(ARQ_ANEXOS);
{
  const alvos = [
    ...fs.readdirSync(path.join(RAIZ, 'components/chat/composer')).filter((f) => /\.tsx?$/.test(f)).map((f) => `components/chat/composer/${f}`),
    'app/dashboard/chat/page.tsx',
    'components/MessageBubble.tsx',
  ];
  const comPublicUrl = alvos.filter((rel) => /publicUrl/.test(rel === 'components/chat/composer/anexos.ts' ? fs.readFileSync(path.resolve(RAIZ, ARQ_ANEXOS), 'utf8') : fonte(rel)));
  checar(comPublicUrl.length === 0, 'nenhuma referência a `publicUrl` no composer, na página e na bolha', comPublicUrl.join(', '));
  checar(!existe('components/InputArea/hooks/useImageUpload.ts'), 'o leitor antigo (useImageUpload.ts) foi apagado');

  const ok = A.lerRespostaDoUpload(201, { ok: true, bucket: 'chat-docs', path: 'co-alfa/u/chat-docs/a.pdf', nome: 'a.pdf', mime: 'application/pdf', bytes: 10, url: '/api/storage/chat-docs/co-alfa/u/chat-docs/a.pdf' });
  checar(ok.ok === true && ok.anexo.path === 'co-alfa/u/chat-docs/a.pdf' && ok.anexo.bucket === 'chat-docs', '{ok:true, bucket, path…} → anexo pronto');
  const fantasma = A.lerRespostaDoUpload(201, { success: true, publicUrl: 'https://x.supabase.co/a.pdf', url: '/api/storage/x' });
  checar(fantasma.ok === false, 'uma resposta com `publicUrl` e sem {ok, bucket, path} NÃO é anexo (é erro visível)');
  const recusa = A.lerRespostaDoUpload(413, { ok: false, motivo: 'O arquivo passa de 20 MB.' });
  checar(recusa.ok === false && recusa.motivo === 'O arquivo passa de 20 MB.', 'o `motivo` da rota chega à ficha, palavra por palavra');
  const quebrada = A.lerRespostaDoUpload(500, null);
  checar(quebrada.ok === false && /Não consegui enviar este arquivo/.test(quebrada.motivo), 'rota quebrada → frase humana, nunca silêncio', quebrada.motivo);
  checar(A.lerRespostaDoUpload(401, {}).motivo.includes('sessão'), '401 → "Sua sessão expirou…"');

  checar(A.motivoParaRecusar('video.mov', 'video/quicktime', 1000) === 'Formato não aceito: .mov', 'formato estranho é avisado ANTES de subir');
  checar(A.motivoParaRecusar('grande.pdf', 'application/pdf', 21 * 1024 * 1024) === 'O arquivo passa de 20 MB.', 'mais de 20 MB é avisado ANTES de subir');
  checar(A.motivoParaRecusar('foto.HEIC', 'image/heic', 5000) === null && A.bucketDoArquivo('image/heic') === 'chat-media', 'HEIC passa e vai para chat-media');
  checar(A.bucketDoArquivo('audio/webm') === 'chat-docs' && A.bucketDoArquivo('application/pdf') === 'chat-docs', 'áudio e documento vão para chat-docs');
  checar(A.mimeDoArquivo('planilha.xls', '') === 'application/vnd.ms-excel' && A.mimeDoArquivo('nota.md', '') === 'text/markdown', 'o MIME que o navegador cala vem da extensão (.xls, .md)');
  const T = carregarReal('components/chat/composer/tipos.ts');
  checar(T.MAX_ARQUIVOS === 10 && T.MAX_BYTES === 20 * 1024 * 1024, 'os limites são 10 arquivos e 20 MB');
}

// ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════
console.log('\n[6] A bolha: Copiar em toda resposta do AutoBrokers; Tentar de novo só na ÚLTIMA; fichas na bolha do corretor');
// ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════
const ARQ_BOLHA = process.env.BOLHA_SOB_TESTE || 'components/MessageBubble.tsx';
const { MessageBubble } = carregarReal(ARQ_BOLHA);
const desenhar = (props) => renderToStaticMarkup(ReactReal.createElement(MessageBubble, props));
{
  const resposta = { id: 'a1', role: 'assistant', content: 'O prêmio é **R$ 1.200**.', type: 'text', created_at: '' };
  const pergunta = { id: 'u1', role: 'user', content: 'Qual o prêmio?', type: 'text', created_at: '' };
  checar(/aria-label="Copiar resposta"/.test(desenhar({ message: resposta })), 'a resposta do AutoBrokers tem o botão Copiar (aria-label)');
  checar(!/Copiar resposta/.test(desenhar({ message: pergunta })), 'a pergunta do corretor não tem Copiar');
  checar(!/Copiar resposta/.test(desenhar({ message: resposta, emCurso: true })), 'enquanto a resposta chega, o Copiar espera');
  checar(/aria-label="Tentar de novo"/.test(desenhar({ message: resposta, onRetry: () => {} })) && !/Tentar de novo/.test(desenhar({ message: resposta })), 'Tentar de novo aparece só quando a página o entrega (a última)');
  const tabela = desenhar({ message: { ...resposta, content: '| a | b |\n|---|---|\n| 1 | 2 |' } });
  checar(/data-markdown/.test(tabela), 'o markdown passa pelo leitor (tabelas roláveis via components.table)');
  checar(/overflow-x-auto/.test(fonte('components/MessageBubble.tsx')), 'a tabela mora num contêiner rolável (overflow-x-auto)');

  const comAnexos = desenhar({
    message: {
      id: 'u2', role: 'user', content: 'Segue', type: 'text', created_at: '',
      payload: { attachments: [
        { nome: 'apolice.pdf', mime: 'application/pdf', bytes: 182345, path: 'co-alfa/u-ana/chat-docs/0b6a.pdf' },
        { nome: 'placa.jpg', mime: 'image/jpeg', bytes: 90210, path: 'co-alfa/u-ana/chat-media/77aa.jpg' },
      ] },
    },
  });
  checar(/apolice\.pdf/.test(comAnexos) && /PDF · 178 KB/.test(comAnexos), 'a bolha do corretor mostra a ficha do PDF (nome, tipo, tamanho)', (comAnexos.match(/PDF[^<]*/) || [''])[0]);
  checar(/src="\/api\/storage\/chat-media\/co-alfa\/u-ana\/chat-media\/77aa\.jpg"/.test(comAnexos), 'depois de recarregar, a foto vem do proxy autenticado pelo path gravado (bucket deduzido do caminho)');

  // SPEC-132-A (A4, costura A3 → A1) — o backend grava a transcrição em `payload.transcricao` da PERGUNTA (não no
  // anexo), e o BFF grava o áudio sozinho como "[Anexo] nome". A bolha de voz mostra a transcrição; a marca, não.
  const soAudio = desenhar({
    message: {
      id: 'u3', role: 'user', content: '[Anexo] gravacao.webm', type: 'text', created_at: '',
      payload: {
        attachments: [{ nome: 'gravacao.webm', mime: 'audio/webm', bytes: 48000, path: 'co-alfa/u-ana/chat-docs/9f1c.webm', bucket: 'chat-docs' }],
        transcricao: 'qual o prazo da vistoria do carro',
      },
    },
  });
  checar(/qual o prazo da vistoria do carro/.test(soAudio), 'a bolha de voz mostra a transcrição gravada em payload.transcricao');
  checar(!/\[Anexo\]/.test(soAudio), 'a marca "[Anexo] nome" que o BFF grava não aparece como fala do corretor');
  const textoQueComeca = desenhar({ message: { id: 'u4', role: 'user', content: '[Anexo] foi o que escrevi', type: 'text', created_at: '' } });
  checar(/\[Anexo\] foi o que escrevi/.test(textoQueComeca), 'CONTROLE: sem anexo, o texto "[Anexo] …" é fala e aparece');

  const C = carregarReal('components/chat/composer/copiar.ts');
  const limpo = C.textoLimpoDoMarkdown('## Resumo\n**Prêmio** de `R$ 1.200` em *12x*\n\n| Seguradora | Prêmio |\n|---|---|\n| Alfa | 1.200 |\n\nVeja [o site](https://exemplo.com.br).');
  const esperado = 'Resumo\nPrêmio de R$ 1.200 em 12x\n\nSeguradora\tPrêmio\nAlfa\t1.200\n\nVeja o site (https://exemplo.com.br).';
  checar(limpo === esperado, 'Copiar leva o TEXTO LIMPO (sem **, #, crases; tabela em colunas)', JSON.stringify(limpo));
}
{
  // a PÁGINA entrega o onRetry só à ÚLTIMA resposta, e nunca enquanto o turno corre
  const bolhas = (montagem) => [...nos(montagem.arvore)].filter((n) => n.tipo && n.tipo.nome === 'MessageBubble');
  const conversa = [
    ...msgsDeConversa,
    { id: 'm-user-2', role: 'user', content: 'E em 10x?', type: 'text', created_at: '2026-10-14T10:01:00Z', payload: { client_request_id: 'crid-2' } },
    { id: 'm-ab-2', role: 'assistant', content: 'Em 10x fica R$ 120.', type: 'text', created_at: '2026-10-14T10:01:05Z', payload: { client_request_id: 'crid-2' } },
  ];
  const parada = bolhas(montarPagina({ mensagens: conversa, arquivo: ARQ_PAGINA }));
  const comRetry = parada.filter((b) => typeof b.props.onRetry === 'function').map((b) => b.props.message.id);
  checar(comRetry.length === 1 && comRetry[0] === 'm-ab-2', 'só a ÚLTIMA resposta recebe "Tentar de novo"', JSON.stringify(comRetry));
  const correndo = bolhas(montarPagina({
    mensagens: conversa, arquivo: ARQ_PAGINA,
    turno: { status: 'streaming', clientRequestId: 'crid-2', assistantMessageId: 'm-ab-2', userMessageId: null, stage: null, transport: 'ok', aviso: null, artifacts: [] },
  }));
  checar(correndo.every((b) => !b.props.onRetry) && correndo.find((b) => b.props.message.id === 'm-ab-2')?.props.emCurso === true, 'enquanto o turno corre: nenhum "Tentar de novo" e a última está emCurso');
}

// ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════
console.log('\n[7] O celular sem a barra de 6 atalhos do rodapé — a navegação é o ☰ do topo (D-132A-02)');
// ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════
const ARQ_CASCO = process.env.CASCO_SOB_TESTE || 'components/layout/TenantAppShell.tsx';
{
  const h = (t, p, ...f) => ({ tipo: t, props: p || {}, filhos: f });
  const React = { createElement: h, Fragment: 'FRAGMENT' };
  const nomes = [];
  const carregar = criarCarregador({
    React,
    stubs: (id) => {
      const nome = id.split('/').pop();
      nomes.push(id);
      const f = function () { return null; };
      f.nome = nome;
      return { [nome]: f, default: f, __esModule: true };
    },
  });
  const { TenantAppShell } = carregar(ARQ_CASCO);
  const arvore = TenantAppShell({ children: 'conteudo' });
  const componentes = [...nos(arvore)].map((n) => (typeof n.tipo === 'string' ? n.tipo : n.tipo?.nome));
  console.log(`      o casco desenha: ${componentes.join(', ')}`);
  checar(!componentes.includes('TenantBottomNav') && !nomes.some((i) => /BottomNav/.test(i)), 'o casco não importa nem desenha a barra do rodapé');
  checar(!componentes.includes('nav'), 'nenhum <nav> solto no casco (a navegação mora na sidebar e na gaveta do ☰)');
  checar(componentes.includes('TenantTopBar') && componentes.includes('TenantSidebar'), 'o topo (☰) e a sidebar continuam no casco');
  checar(/h-\[100dvh\]/.test(fonte(ARQ_CASCO)) && /overflow-hidden/.test(fonte(ARQ_CASCO)), 'o casco é 100dvh e não rola como um todo');
  const topo = fonte('components/layout/TenantTopBar.tsx');
  checar(/<TenantNav\b/.test(topo) && /Abrir menu/.test(topo) && /autobrokers:new-conversation/.test(topo), 'o ☰ do topo abre a gaveta (TenantNav) e o "+" da nova conversa continua no topo');
  checar(/PILLARS\.map\(renderItem\)/.test(fonte('components/layout/TenantNav.tsx')), 'a gaveta lista os pilares (PILLARS)');
  const nav = carregarReal('lib/navigation.ts');
  checar(Array.isArray(nav.PILLARS) && nav.PILLARS.length === 6, 'os 6 pilares continuam alcançáveis pela gaveta', String(nav.PILLARS?.length));
  checar(/h-11 w-11/.test(topo), 'os botões do topo têm 44 px de toque');
}

// ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════
console.log('\n[8] O esforço: Rápido · Equilibrado · Máximo, lembrado no aparelho; valor estranho = Equilibrado');
// ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════
const ARQ_ESFORCO = process.env.ESFORCO_SOB_TESTE || 'components/chat/composer/useEsforco.ts';
{
  const E = carregarReal(ARQ_ESFORCO);
  const armazem = (v) => ({ getItem: () => v });
  checar(E.lerEsforcoSalvo(armazem('turbo')) === 'equilibrado', '"turbo" guardado → Equilibrado');
  checar(E.lerEsforcoSalvo(armazem('"rapido"')) === 'equilibrado', 'JSON guardado ("\\"rapido\\"") → Equilibrado');
  checar(E.lerEsforcoSalvo(armazem(null)) === 'equilibrado' && E.lerEsforcoSalvo(null) === 'equilibrado', 'nada guardado / sem armazém → Equilibrado');
  checar(E.lerEsforcoSalvo({ getItem: () => { throw new Error('SecurityError'); } }) === 'equilibrado', 'armazém que LANÇA (aba anônima) → Equilibrado, sem quebrar');
  checar(E.lerEsforcoSalvo(armazem('maximo')) === 'maximo' && E.lerEsforcoSalvo(armazem('rapido')) === 'rapido', 'rapido/maximo guardados voltam como estão');
  let gravou = null;
  E.guardarEsforco('rapido', { setItem: (k, v) => { gravou = [k, v]; } });
  checar(gravou && gravou[1] === 'rapido', 'a escolha é gravada no aparelho');
  let lancou = false;
  try { E.guardarEsforco('maximo', { setItem: () => { throw new Error('QuotaExceeded'); } }); } catch { lancou = true; }
  checar(!lancou, 'gravar num armazém que lança não quebra a tela');
  checar(E.ESFORCOS.map((x) => `${x.rotulo}: ${x.descricao}`).join(' | ') === 'Rápido: Responde na hora | Equilibrado: O padrão | Máximo: Pensa mais, demora mais', 'os três rótulos e as frases do §4');
  // a pílula aparece ao lado do "+" só quando o esforço ≠ Equilibrado
  const fonteDoComposer = fonte('components/chat/composer/Composer.tsx');
  checar(/esforco !== 'equilibrado'/.test(fonteDoComposer) && /rotuloDoEsforco\(esforco\)/.test(fonteDoComposer), 'a pílula do esforço só aparece quando ≠ Equilibrado');
}

// ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════
console.log('\n[9] A tela não dança: viewport com interactive-widget e o body em 100dvh, nunca 100vh');
// ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════
const ARQ_CSS = process.env.CSS_SOB_TESTE || 'app/globals.css';
{
  const carregar = criarCarregador({
    React: ReactReal,
    stubs: (id) => {
      if (id === './globals.css') return {};
      if (id === 'next/font/google') return { Geist: () => ({ variable: 'g' }), Geist_Mono: () => ({ variable: 'gm' }) };
      if (id === '@/components/ui/sonner') return { Toaster: () => null };
      if (id === '@/components/theme-provider') return { ThemeProvider: ({ children }) => children };
      return undefined;
    },
  });
  const layout = carregar('app/layout.tsx');
  const v = layout.viewport || {};
  checar(v.width === 'device-width' && v.initialScale === 1 && v.viewportFit === 'cover' && v.interactiveWidget === 'resizes-content',
    'app/layout.tsx exporta viewport {device-width, 1, cover, resizes-content}', JSON.stringify(v));
  const css = fs.readFileSync(path.resolve(RAIZ, ARQ_CSS), 'utf8');
  const body = (/\n\s*body\s*\{([^}]*)\}/.exec(css) || [])[1] || '';
  checar(!/min-height:\s*100vh/.test(body), 'o body não tem min-height:100vh', body.replace(/\s+/g, ' ').trim());
  checar(/min-height:\s*100dvh/.test(body), 'o body usa min-height:100dvh');
}

// ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════
console.log('\n[10] O Enter: notebook envia (Shift+Enter quebra a linha); no celular Enter quebra a linha');
// ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════
{
  const K = carregarReal('components/chat/composer/teclado.ts');
  checar(K.deveEnviarNoEnter({ key: 'Enter', toque: false }) === true, 'notebook: Enter envia');
  checar(K.deveEnviarNoEnter({ key: 'Enter', shiftKey: true, toque: false }) === false, 'notebook: Shift+Enter quebra a linha');
  checar(K.deveEnviarNoEnter({ key: 'Enter', toque: true }) === false, 'celular: Enter quebra a linha (envia pelo botão)');
  checar(K.deveEnviarNoEnter({ key: 'Enter', isComposing: true, toque: false }) === false, 'durante a composição de acento/IME, Enter não envia');
  checar(K.deveEnviarNoEnter({ key: 'a', toque: false }) === false, 'CONTROLE: outra tecla não envia');
  const fc = fonte('components/chat/composer/Composer.tsx');
  checar(/onPaste=\{aoColar\}/.test(fc) && /clipboardData\?\.files/.test(fc), 'colar imagem/arquivo no campo anexa');
  const fp = fonte('app/dashboard/chat/page.tsx');
  checar(/onDrop=\{aoSoltar\}/.test(fp) && /adicionarArquivos\(arquivos\)/.test(fp), 'soltar arquivos sobre a conversa anexa');
}

// ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════
console.log('\n[11] A resposta que chega depois (SPEC-132 · A5): a cotação disparada no turno aparece SEM recarregar');
// ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════
// 📊 14/10/2026, produção: `messages` e `conversations` fora da publicação `supabase_realtime` (0 linhas) — o
// `postgres_changes` da página nunca recebe a mensagem que o Work Run `cotacao.chat` grava 1–6 min depois. A página
// REAL roda aqui sobre um React dublê COM estado e efeitos, um relógio falso (setTimeout/Date.now) e um `document`
// falso (`hidden` + `visibilitychange`); a rede é um servidor falso que guarda a conversa como o banco guardaria.
// Dublê só na borda: fetch, relógio, document, Supabase (o Realtime calado, como em produção), marcadores de UI.
const PROMESSA = 'Calculando nas seguradoras pela conta da corretora — volto aqui com o resultado em 1 a 2 minutos. Pode seguir conversando.';
const T0 = Date.parse('2026-10-14T13:00:00.000Z');
const LINHA_DA_ESPERA = 'Calculando a cotação… a resposta aparece aqui';

function criarRelogioFalso(inicio) {
  let agora = inicio;
  let seq = 0;
  const fila = new Map();
  return {
    agora: () => agora,
    setTimeout(fn, ms = 0) { const id = ++seq; fila.set(id, { t: agora + Math.max(0, Number(ms) || 0), fn }); return id; },
    clearTimeout(id) { fila.delete(id); },
    pendentes: () => fila.size,
    proximo(ate) {
      let melhor = null;
      for (const [id, x] of fila) if (x.t <= ate && (!melhor || x.t < melhor[1].t || (x.t === melhor[1].t && id < melhor[0]))) melhor = [id, x];
      if (!melhor) return null;
      fila.delete(melhor[0]);
      agora = Math.max(agora, melhor[1].t);
      return melhor[1].fn;
    },
    pular(t) { agora = Math.max(agora, t); },
  };
}

/** React dublê com estado POR POSIÇÃO de hook, efeitos com dependências e limpeza, e "sujo" quando um set muda algo. */
function criarReactVivo() {
  const slots = [];
  let cursor = 0;
  let pendentes = [];
  let sujo = false;
  const React = {
    useState(inicial) {
      const i = cursor++;
      if (!(i in slots)) slots[i] = { v: typeof inicial === 'function' ? inicial() : inicial };
      const s = slots[i];
      if (!s.set) s.set = (nv) => { const v = typeof nv === 'function' ? nv(s.v) : nv; if (!Object.is(v, s.v)) { s.v = v; sujo = true; } };
      return [s.v, s.set];
    },
    useRef(v) { const i = cursor++; if (!(i in slots)) slots[i] = { v: { current: v } }; return slots[i].v; },
    useCallback(fn, deps) { return React.useMemo(() => fn, deps); },
    useMemo(fn, deps) {
      const i = cursor++;
      const antes = slots[i];
      const igual = antes && deps && antes.deps && deps.length === antes.deps.length && deps.every((d, k) => Object.is(d, antes.deps[k]));
      if (!igual) slots[i] = { v: fn(), deps };
      return slots[i].v;
    },
    useEffect(fn, deps) {
      const i = cursor++;
      const antes = slots[i];
      const mudou = !antes || !deps || !antes.deps || deps.length !== antes.deps.length || deps.some((d, k) => !Object.is(d, antes.deps[k]));
      if (mudou) { pendentes.push({ i, fn, limpar: antes?.limpar }); slots[i] = { deps, limpar: antes?.limpar }; }
    },
    createElement(tipo, props, ...filhos) { return { tipo, props: props || {}, filhos }; },
    Fragment: 'FRAGMENT',
  };
  return {
    React,
    render(Comp) {
      cursor = 0; pendentes = []; sujo = false;
      const arvore = Comp();
      for (const p of pendentes) {
        if (typeof p.limpar === 'function') p.limpar();
        const r = p.fn();
        slots[p.i].limpar = typeof r === 'function' ? r : undefined;
      }
      return arvore;
    },
    sujo: () => sujo,
  };
}

function textoDaArvore(no) {
  if (no == null || typeof no === 'boolean') return '';
  if (typeof no === 'string' || typeof no === 'number') return String(no);
  if (Array.isArray(no)) return no.map(textoDaArvore).join('');
  return textoDaArvore(no.filhos) + textoDaArvore(no.props?.children);
}

/**
 * A página VIVA: sobe com a conversa `conversaInicial` no servidor falso, roda os efeitos (empresa, agentes, conversa),
 * e devolve como enviar uma mensagem (`eventosDoTurno` é o SSE que o backend responderia), avançar o relógio, esconder
 * a aba e mexer no "banco".
 */
async function montarPaginaViva({ conversaInicial = [], arquivo = ARQ_PAGINA } = {}) {
  const relogio = criarRelogioFalso(T0);
  const ouvintesDoDocumento = new Map();
  const doc = {
    hidden: false,
    activeElement: null,
    body: {},
    addEventListener(t, fn) { if (!ouvintesDoDocumento.has(t)) ouvintesDoDocumento.set(t, new Set()); ouvintesDoDocumento.get(t).add(fn); },
    removeEventListener(t, fn) { ouvintesDoDocumento.get(t)?.delete(fn); },
  };
  const banco = { mensagens: conversaInicial.map((m) => ({ ...m })) };
  let eventosDoTurno = [];
  let respostaDoTurno = '';
  const chamadas = [];
  const SESSAO = 'sessao-viva-1';
  let cridDoTurno = null;
  const fetchFalso = async (url, opts = {}) => {
    const u = String(url);
    chamadas.push({ url: u, t: relogio.agora() });
    if (u === '/api/chat/stream') { try { cridDoTurno = JSON.parse(opts.body).client_request_id; } catch { cridDoTurno = null; } }
    const json = (dados) => ({ ok: true, status: 200, json: async () => JSON.parse(JSON.stringify(dados)) });
    if (u === '/api/user/company-data') return json({ companyId: 'co-alfa', allowWebSearch: false });
    if (u === '/api/agents') return json({ agents: [{ id: AG, name: 'Agente Alfa' }] });
    if (u.startsWith('/api/conversations?session_id=')) {
      return json({ conversation: { id: 'conv-viva-1', agent_id: AG, session_id: SESSAO }, messages: banco.mensagens, has_more: false, cursor: null });
    }
    if (u === '/api/chat/stream') return respostaSSE(eventosDoTurno);
    return { ok: false, status: 404, json: async () => ({}) };
  };
  const { React, render, sujo } = criarReactVivo();
  const stubs = (id) => {
    if (id in MARCADORES_VIVOS) return MARCADORES_VIVOS[id];
    return undefined;
  };
  const carregar = criarCarregador({ React, stubs });
  const antes = {
    window: globalThis.window, document: globalThis.document, fetch: globalThis.fetch, raf: globalThis.requestAnimationFrame,
    setTimeout: globalThis.setTimeout, clearTimeout: globalThis.clearTimeout, now: Date.now, error: console.error,
  };
  const imediato = antes.setTimeout; // o laço de microtarefas do teste usa o relógio REAL (setImmediate)
  globalThis.window = {
    location: { search: `?session=${SESSAO}`, href: `http://teste.local/dashboard/chat?session=${SESSAO}` },
    history: { replaceState() {} },
    addEventListener() {}, removeEventListener() {},
  };
  globalThis.document = doc;
  globalThis.fetch = fetchFalso;
  globalThis.requestAnimationFrame = undefined;
  globalThis.setTimeout = relogio.setTimeout;
  globalThis.clearTimeout = relogio.clearTimeout;
  Date.now = relogio.agora;
  console.error = () => {};
  void imediato;
  const pagina = carregar(arquivo).default;
  let arvore = null;
  const assentar = async () => {
    for (let i = 0; i < 40; i++) {
      await new Promise((r) => setImmediate(r));
      if (sujo()) arvore = render(pagina);
    }
  };
  arvore = render(pagina);
  await assentar();
  const api = {
    banco,
    chamadas,
    arvore: () => arvore,
    bolhas: () => [...nos(arvore)].filter((n) => n.tipo && n.tipo.nome === 'MessageBubble').map((n) => n.props.message),
    linhaDaEspera: () => textoDaArvore(arvore).includes(LINHA_DA_ESPERA),
    consultas: () => chamadas.filter((c) => c.url.startsWith('/api/conversations?session_id=')).length,
    relogiosPendentes: () => relogio.pendentes(),
    agora: () => relogio.agora(),
    async enviar(texto, eventos, respostaGravada) {
      eventosDoTurno = eventos;
      respostaDoTurno = respostaGravada;
      const composer = [...nos(arvore)].find(ehComposer);
      await composer.props.onSendMessage(texto, [], {});
      // o "servidor" gravou a pergunta e a resposta do turno — com ids do BANCO (diferentes dos da tela) e o mesmo
      // `client_request_id`, como o BFF faz; é isso que a consulta traz de volta
      const crid = cridDoTurno;
      banco.mensagens.push(
        { id: `db-u-${banco.mensagens.length}`, conversation_id: 'conv-viva-1', role: 'user', content: texto, type: 'text', created_at: new Date(relogio.agora()).toISOString(), payload: { client_request_id: crid } },
        { id: `db-a-${banco.mensagens.length + 1}`, conversation_id: 'conv-viva-1', role: 'assistant', content: respostaDoTurno, type: 'text', created_at: new Date(relogio.agora()).toISOString(), payload: { client_request_id: crid } },
      );
      await assentar();
    },
    async avancar(ms) {
      const alvo = relogio.agora() + ms;
      for (let n = 0; n < 10000; n++) {
        const fn = relogio.proximo(alvo);
        if (!fn) break;
        fn();
        await assentar();
      }
      relogio.pular(alvo);
      await assentar();
    },
    async esconderAba(oculta) {
      doc.hidden = oculta;
      for (const fn of [...(ouvintesDoDocumento.get('visibilitychange') || [])]) fn();
      await assentar();
    },
    restaurar() {
      globalThis.window = antes.window; globalThis.document = antes.document; globalThis.fetch = antes.fetch;
      globalThis.requestAnimationFrame = antes.raf; globalThis.setTimeout = antes.setTimeout; globalThis.clearTimeout = antes.clearTimeout;
      Date.now = antes.now; console.error = antes.error;
    },
  };
  return api;
}
function arvoreMensagens(arvore) {
  return [...nos(arvore)].filter((n) => n.tipo && n.tipo.nome === 'MessageBubble').map((n) => n.props.message);
}
const marcadorVivo = (nome) => { const f = function () { return null; }; f.nome = nome; return f; };
const MARCADORES_VIVOS = {
  '@/components/chat/ChatWelcome': { ChatWelcome: marcadorVivo('ChatWelcome') },
  '@/components/chat/LinhaDeAtividade': { LinhaDeAtividade: marcadorVivo('LinhaDeAtividade') },
  '@/components/chat/AvisoDoTurno': { AvisoDoTurno: marcadorVivo('AvisoDoTurno') },
  '@/components/chat/VoltarAoFim': { VoltarAoFim: marcadorVivo('VoltarAoFim') },
  '@/components/chat/composer/Composer': { Composer: marcadorVivo('Composer') },
  '@/components/MessageBubble': { MessageBubble: marcadorVivo('MessageBubble') },
  '@/components/TypingIndicator': { TypingIndicator: marcadorVivo('TypingIndicator') },
  // o Realtime CALADO — como em produção (📊 0 linhas na publicação)
  '@/lib/supabase': { supabase: { channel: () => ({ on: () => ({ on: () => ({ subscribe: () => ({}) }), subscribe: () => ({}) }) }), removeChannel() {} } },
  '@/lib/types': {},
  '@/hooks/useUserId': { useUserId: () => ({ userId: UID, userAvatar: null, userName: 'Ana Teste', isLoading: false }) },
  sonner: { toast: { error() {}, success() {} } },
};
const ev = (seq, type, payload = {}) => ({ protocol: 'autobrokers.interaction.v1', seq, type, turn: {}, payload });
const turnoQueDisparou = (texto, chave = 'generic') => [
  ev(1, 'turn.accepted', {}),
  ev(2, 'stage.started', { key: chave, label: 'Trabalhando nisso…' }),
  ev(3, 'stage.completed', { key: chave }),
  ev(4, 'assistant.content.delta', { text: texto }),
  ev(5, 'assistant.content.completed', { content: texto }),
  ev(6, 'turn.completed', { status: 'complete' }),
];
const conversaAntiga = [
  { id: 'db-old-u', conversation_id: 'conv-viva-1', role: 'user', content: 'Oi', type: 'text', created_at: '2026-10-14T12:00:00.000Z', payload: { client_request_id: 'crid-antigo' } },
  { id: 'db-old-a', conversation_id: 'conv-viva-1', role: 'assistant', content: 'Olá! Em que posso ajudar?', type: 'text', created_at: '2026-10-14T12:00:03.000Z', payload: { client_request_id: 'crid-antigo' } },
];
const resultadoDaCotacao = (t, id = 'db-cotacao-pronta', tipo = 'pronta') => ({
  id, conversation_id: 'conv-viva-1', role: 'assistant', type: 'text', created_at: new Date(t).toISOString(),
  content: 'Pronto: 5 seguradoras responderam. Recomendada R$ 2.100,00 …',
  payload: { cotacao: { tipo, work_run_id: 'run-1', pedido_id: 'ped-1', estado: 'pronta', url: '/r/tok-falso' } },
});
/** Sem duplicata: cada `id` uma vez, e cada (client_request_id, role) uma vez. */
function duplicatas(lista) {
  const vistos = new Set();
  const dup = [];
  for (const m of lista) {
    const crid = m.payload?.client_request_id;
    const chave = crid ? `crid:${crid}:${m.role}` : `id:${m.id}`;
    if (vistos.has(chave)) dup.push(chave);
    vistos.add(chave);
  }
  return dup;
}

const ARQ_PAGINA_VIVA = process.env.PAGINA_VIVA_SOB_TESTE || ARQ_PAGINA;
{
  // (a) a cotação disparada: a espera liga, consulta a cada 6 s, junta a resposta UMA vez e para
  const p = await montarPaginaViva({ conversaInicial: conversaAntiga, arquivo: ARQ_PAGINA_VIVA });
  try {
    checar(p.bolhas().length === 2 && !p.linhaDaEspera(), 'a conversa abre com as 2 mensagens antigas e sem espera (a última não é uma promessa de cálculo)');
    const consultasAoAbrir = p.consultas();
    await p.enviar('sim', turnoQueDisparou(PROMESSA), PROMESSA);
    checar(p.linhaDaEspera(), 'depois do turno que disparou o cálculo: a linha "Calculando a cotação… a resposta aparece aqui" aparece');
    await p.avancar(5_000);
    const aos5s = p.consultas() - consultasAoAbrir;
    await p.avancar(1_000);
    const aos6s = p.consultas() - consultasAoAbrir;
    console.log(`      consultas à conversa depois do disparo · aos 5 s: ${aos5s} · aos 6 s: ${aos6s}`);
    checar(aos5s === 0 && aos6s === 1, 'a 1ª consulta é aos 6 s (e não antes)', `5s=${aos5s} 6s=${aos6s}`);
    checar(duplicatas(p.bolhas()).length === 0 && p.bolhas().length === 4, 'a consulta traz a pergunta e a resposta do turno com ids do banco — e NADA duplica (dedupe pelo id do envio)', `${p.bolhas().length} bolhas · dup=${duplicatas(p.bolhas()).join(',')}`);
    await p.avancar(12_000);
    const semResultado = p.consultas() - consultasAoAbrir;
    p.banco.mensagens.push(resultadoDaCotacao(p.agora()));
    await p.avancar(6_000);
    const comCotacao = p.bolhas().filter((m) => m.payload?.cotacao);
    console.log(`      consultas até o resultado: ${p.consultas() - consultasAoAbrir} · bolhas com payload.cotacao: ${comCotacao.length}`);
    checar(semResultado === 3, 'sem resposta ainda, a espera segue consultando (3 consultas em 18 s)', String(semResultado));
    checar(comCotacao.length === 1 && comCotacao[0].id === 'db-cotacao-pronta', 'a mensagem com payload.cotacao aparece UMA vez, sem recarregar');
    checar(arvoreMensagens(p.arvore()).at(-1)?.id === 'db-cotacao-pronta', 'ela entra no FIM da conversa');
    checar(!p.linhaDaEspera(), 'a linha "Calculando…" some quando a resposta chega');
    const aoChegar = p.consultas();
    await p.avancar(120_000);
    checar(p.consultas() === aoChegar && p.relogiosPendentes() === 0, 'e a espera PARA: 2 min depois, nenhuma consulta nova e nenhum relógio armado', `+${p.consultas() - aoChegar} consultas · ${p.relogiosPendentes()} relógio(s)`);
    checar(duplicatas(p.bolhas()).length === 0 && p.bolhas().length === 5, 'no fim: 5 bolhas, nenhuma duplicada', `${p.bolhas().length}`);
  } finally { p.restaurar(); }
}
{
  // (b) turnos comuns NÃO esperam — nem a recusa da ferramenta (que também passou pelo estágio)
  const casos = [
    ['um turno comum', 'O prêmio é R$ 1.200.', 'generic'],
    ['a recusa da cotacao_disparar', 'Esse ramo eu ainda não calculo por aqui — cote direto no Agger.', 'generic'],
    ['"o cálculo começou mas não consegui acompanhá-lo"', 'O cálculo começou, mas não consegui acompanhá-lo para responder aqui — o resultado fica em Cotação Rápida → Cotações.', 'generic'],
  ];
  for (const [nome, texto, chave] of casos) {
    const p = await montarPaginaViva({ conversaInicial: conversaAntiga, arquivo: ARQ_PAGINA_VIVA });
    try {
      const antes = p.consultas();
      await p.enviar('qual o prêmio?', turnoQueDisparou(texto, chave), texto);
      await p.avancar(60_000);
      checar(!p.linhaDaEspera() && p.consultas() === antes, `${nome}: nenhuma espera, nenhuma consulta em 60 s`, `+${p.consultas() - antes}`);
    } finally { p.restaurar(); }
  }
  // CONTROLE do estágio: com a chave `quote.calculating` (quando o catálogo nomear a ferramenta), um "calculando"
  // parafraseado TAMBÉM liga a espera — e o mesmo texto sem a chave não liga
  for (const [chave, liga] of [['quote.calculating', true], ['generic', false]]) {
    const p = await montarPaginaViva({ conversaInicial: conversaAntiga, arquivo: ARQ_PAGINA_VIVA });
    try {
      await p.enviar('sim', turnoQueDisparou('Certo, já estou calculando nas seguradoras.', chave), 'Certo, já estou calculando nas seguradoras.');
      checar(p.linhaDaEspera() === liga, `estágio "${chave}" + "calculando" parafraseado → ${liga ? 'espera' : 'não espera'}`);
    } finally { p.restaurar(); }
  }
}
{
  // (c) a aba oculta PAUSA (nenhuma consulta, nenhum relógio) e a volta consulta na hora
  const p = await montarPaginaViva({ conversaInicial: conversaAntiga, arquivo: ARQ_PAGINA_VIVA });
  try {
    await p.enviar('sim', turnoQueDisparou(PROMESSA), PROMESSA);
    await p.avancar(6_000);
    const antes = p.consultas();
    await p.esconderAba(true);
    await p.avancar(60_000);
    const oculta = p.consultas() - antes;
    checar(oculta <= 1 && p.relogiosPendentes() === 0, 'aba oculta: no máximo a volta em curso, depois NENHUMA consulta em 60 s e nenhum relógio armado', `+${oculta} · ${p.relogiosPendentes()} relógio(s)`);
    const naVolta = p.consultas();
    p.banco.mensagens.push(resultadoDaCotacao(p.agora()));
    await p.esconderAba(false);
    await p.avancar(0);
    checar(p.consultas() === naVolta + 1 && p.bolhas().filter((m) => m.payload?.cotacao).length === 1 && !p.linhaDaEspera(), 'aba visível de novo: consulta NA HORA e a resposta aparece');
  } finally { p.restaurar(); }
}
{
  // (d) o prazo: 10 min sem resposta → a espera para sozinha
  const p = await montarPaginaViva({ conversaInicial: conversaAntiga, arquivo: ARQ_PAGINA_VIVA });
  try {
    const antes = p.consultas();
    await p.enviar('sim', turnoQueDisparou(PROMESSA), PROMESSA);
    await p.avancar(9 * 60_000 + 54_000);
    const aos954 = p.consultas() - antes;
    const linhaAinda = p.linhaDaEspera();
    await p.avancar(6_000);
    const aos10 = p.consultas() - antes;
    await p.avancar(5 * 60_000);
    console.log(`      consultas · aos 9 min 54 s: ${aos954} · aos 10 min: ${aos10} · aos 15 min: ${p.consultas() - antes}`);
    checar(linhaAinda && aos954 === 99, 'até o prazo, uma consulta a cada 6 s (99 até 9 min 54 s) com a linha à vista', String(aos954));
    checar(!p.linhaDaEspera() && p.consultas() - antes === aos10 && aos10 === 99 && p.relogiosPendentes() === 0, 'aos 10 min a espera PARA: a linha some e nenhuma consulta depois', `${aos10} → ${p.consultas() - antes}`);
  } finally { p.restaurar(); }
}
{
  // (e) ao ABRIR: só a promessa de cálculo recente (< 10 min) e ainda sem payload.cotacao liga a espera
  const promessaGravada = (minutosAtras, extra = {}) => [
    ...conversaAntiga,
    { id: 'db-u-sim', conversation_id: 'conv-viva-1', role: 'user', content: 'sim', type: 'text', created_at: new Date(T0 - minutosAtras * 60_000 - 2000).toISOString(), payload: { client_request_id: 'crid-sim' } },
    { id: 'db-a-sim', conversation_id: 'conv-viva-1', role: 'assistant', content: PROMESSA, type: 'text', created_at: new Date(T0 - minutosAtras * 60_000).toISOString(), payload: { client_request_id: 'crid-sim', ...extra } },
  ];
  for (const [nome, conversa, liga] of [
    ['a promessa de 2 min atrás', promessaGravada(2), true],
    ['a promessa de 15 min atrás', promessaGravada(15), false],
    ['uma resposta que JÁ é a cotação', promessaGravada(2, { cotacao: { tipo: 'pronta' } }), false],
    ['um "calculando" qualquer (não é a frase da ferramenta)', [...conversaAntiga, { id: 'db-a-x', conversation_id: 'conv-viva-1', role: 'assistant', content: 'Estou calculando a média da carteira.', type: 'text', created_at: new Date(T0 - 60_000).toISOString(), payload: {} }], false],
  ]) {
    const p = await montarPaginaViva({ conversaInicial: conversa, arquivo: ARQ_PAGINA_VIVA });
    try {
      checar(p.linhaDaEspera() === liga, `ao abrir · ${nome} → ${liga ? 'espera' : 'não espera'}`);
      if (liga) {
        p.banco.mensagens.push(resultadoDaCotacao(p.agora()));
        await p.avancar(6_000);
        checar(p.bolhas().filter((m) => m.payload?.cotacao).length === 1 && !p.linhaDaEspera(), 'ao abrir · a resposta chega pela consulta e a espera termina');
      }
    } finally { p.restaurar(); }
  }
}
{
  // (f) a transcrição do áudio (o UPDATE que o Realtime não entrega) chega pela mesma consulta
  const p = await montarPaginaViva({ conversaInicial: conversaAntiga, arquivo: ARQ_PAGINA_VIVA });
  try {
    await p.enviar('', turnoQueDisparou(PROMESSA), PROMESSA);
    const daPergunta = p.banco.mensagens.at(-2);
    daPergunta.payload = { ...daPergunta.payload, transcricao: 'cota o onix do joão' };
    await p.avancar(6_000);
    const pergunta = p.bolhas().find((m) => m.role === 'user' && m.payload?.client_request_id === daPergunta.payload.client_request_id);
    checar(pergunta?.payload?.transcricao === 'cota o onix do joão' && duplicatas(p.bolhas()).length === 0, 'a transcrição gravada depois entra na bolha da pergunta (sem duplicá-la)', JSON.stringify(pergunta?.payload));
  } finally { p.restaurar(); }
}
{
  // (g) disparo + ajuste = DUAS respostas: a 1ª não encerra a espera, a 2ª sim — e nenhuma duplica
  const p = await montarPaginaViva({ conversaInicial: conversaAntiga, arquivo: ARQ_PAGINA_VIVA });
  try {
    await p.enviar('sim', turnoQueDisparou(PROMESSA), PROMESSA);
    const ajuste = 'Recalculando com a franquia reduzida pela conta da corretora — volto aqui com o resultado em 1 a 2 minutos.';
    await p.enviar('baixa a franquia', turnoQueDisparou(ajuste), ajuste);
    p.banco.mensagens.push(resultadoDaCotacao(p.agora(), 'db-cot-1'));
    await p.avancar(6_000);
    const depoisDa1 = p.linhaDaEspera();
    await p.avancar(12_000);
    p.banco.mensagens.push(resultadoDaCotacao(p.agora(), 'db-cot-2'));
    await p.avancar(6_000);
    const cot = p.bolhas().filter((m) => m.payload?.cotacao).map((m) => m.id);
    checar(depoisDa1 && !p.linhaDaEspera(), 'com disparo + ajuste, a espera segue depois da 1ª resposta e termina na 2ª');
    checar(JSON.stringify(cot) === '["db-cot-1","db-cot-2"]' && duplicatas(p.bolhas()).length === 0, 'cada resposta aparece UMA vez, mesmo com as consultas que vieram depois da 1ª', JSON.stringify(cot));
  } finally { p.restaurar(); }
}

{
  // (h) a rolagem do corretor: quem subiu para reler NÃO é puxado para o fim quando a resposta chega — vê o
  //     "Voltar ao fim" que já existe; quem estava no fim acompanha (CONTROLE)
  for (const [nome, longe] of [['rolou para cima', true], ['estava no fim', false]]) {
    const p = await montarPaginaViva({ conversaInicial: conversaAntiga, arquivo: ARQ_PAGINA_VIVA });
    try {
      await p.enviar('sim', turnoQueDisparou(PROMESSA), PROMESSA);
      const noDeRolagem = [...nos(p.arvore())].find((n) => typeof n.props?.onScroll === 'function');
      // 15/10: quem rola é a PRÓPRIA lista (`el.scrollTo`), não mais o `scrollIntoView` do fim — que rolava também
      // o <main> do casco e fazia a caixa subir (guarda: a-caixa-fica-no-rodape.test.mjs). A lição continua: conta-se
      // a puxada no nó que rola de verdade.
      let puxadas = 0;
      if (noDeRolagem?.props.ref) noDeRolagem.props.ref.current = { scrollHeight: 3000, scrollTop: longe ? 200 : 2450, clientHeight: 500, scrollTo() { puxadas += 1; } };
      noDeRolagem?.props.onScroll();
      p.banco.mensagens.push(resultadoDaCotacao(p.agora()));
      await p.avancar(6_000);
      const voltar = [...nos(p.arvore())].some((n) => n.tipo && n.tipo.nome === 'VoltarAoFim');
      const chegou = p.bolhas().some((m) => m.payload?.cotacao);
      checar(Boolean(noDeRolagem) && chegou && (longe ? puxadas === 0 && voltar : puxadas >= 1 && !voltar),
        `${nome}: a resposta chega e a tela ${longe ? 'NÃO rola (mostra "Voltar ao fim")' : 'acompanha até o fim'}`, `puxadas=${puxadas} voltar=${voltar}`);
    } finally { p.restaurar(); }
  }
}

{
  // (i) a mensagem de um HUMANO da equipe no meio da espera aparece, mas não é o resultado: a espera continua
  const p = await montarPaginaViva({ conversaInicial: conversaAntiga, arquivo: ARQ_PAGINA_VIVA });
  try {
    await p.enviar('sim', turnoQueDisparou(PROMESSA), PROMESSA);
    p.banco.mensagens.push({ id: 'db-humano', conversation_id: 'conv-viva-1', role: 'assistant', content: 'Oi, aqui é a Bia da equipe.', type: 'text', created_at: new Date(p.agora()).toISOString(), sender_user_id: 'u-bia-ficticia', payload: {} });
    await p.avancar(6_000);
    const humanoNaTela = p.bolhas().some((m) => m.id === 'db-humano');
    const aindaEspera = p.linhaDaEspera();
    p.banco.mensagens.push(resultadoDaCotacao(p.agora()));
    await p.avancar(6_000);
    checar(humanoNaTela && aindaEspera && !p.linhaDaEspera(), 'a mensagem de um humano aparece e NÃO encerra a espera; a da cotação, sim', `humano=${humanoNaTela} esperando=${aindaEspera}`);
  } finally { p.restaurar(); }
}

// ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════
console.log('\n[12] Conserto (juiz P4): o envio RECUSADO antes do turno devolve o texto e os anexos à caixa');
// ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════
// MUTAÇÕES (em disco, restauradas por cópia — ver o relatório do conserto):
//   16 o Composer ignora o `false` de onSendMessage (sem o restauro)          → [12b] 2 vermelhos
//   17 a página não devolve `false` no 403 do BFF (`recusaAntesDoTurno` → false) → [12a] 2 vermelhos
//   18 o Espaço num botão volta a ir para a caixa (sem a exceção do Espaço)      → [13] 2 vermelhos
async function enviarComResposta(resposta, { seedsExtra = {} } = {}) {
  const toasts = [];
  const fetchAntes = globalThis.fetch;
  const chamadas = [];
  globalThis.fetch = async (url, opts = {}) => {
    chamadas.push(String(url));
    if (/\/api\/chat\/stream$/.test(String(url))) return resposta();
    return { ok: false, status: 500, json: async () => ({}) };
  };
  const consoleAntes = { error: console.error };
  try {
    const { arvore } = montarPagina({ arquivo: ARQ_PAGINA, seedsExtra, toasts });
    const composer = [...nos(arvore)].find(ehComposer);
    console.error = () => {};
    const aceito = await composer.props.onSendMessage('Cotação do Onix 2020', [ANEXO_PDF], { esforco: 'rapido' });
    return { aceito, toasts, chamadas: chamadas.filter((u) => /\/api\/chat\/stream$/.test(u)).length };
  } finally {
    globalThis.fetch = fetchAntes;
    Object.assign(console, consoleAntes);
  }
}
const respostaJson = (status, corpo) => () => ({ ok: status < 400, status, json: async () => corpo, body: null });
{
  // (a) a PÁGINA diz ao composer se o envio foi aceito
  const recusado = await enviarComResposta(respostaJson(403, { ok: false, error: 'ANEXO_RECUSADO', motivo: 'Um dos anexos não pertence a esta corretora.', message: 'Um dos anexos não pertence a esta corretora.' }));
  console.log(`      403 do BFF → aceito=${recusado.aceito} · toast: ${recusado.toasts.join(' | ')}`);
  checar(recusado.aceito === false, '403 do BFF (antes de gravar) → onSendMessage resolve `false`', String(recusado.aceito));
  checar(recusado.toasts.some((t) => /não pertence a esta corretora/.test(t) && /voltou para a caixa/.test(t)), 'o aviso é o motivo HUMANO do BFF + "Sua mensagem voltou para a caixa."', recusado.toasts.join(' | '));
  const carregando = await enviarComResposta(respostaJson(200, {}), { seedsExtra: { 7: false } });
  checar(carregando.aceito === false && carregando.chamadas === 0, 'agentes ainda carregando → `false`, sem chamar o stream', `aceito=${carregando.aceito} chamadas=${carregando.chamadas}`);
  const doBackend = await enviarComResposta(respostaJson(429, { error: 'muitos turnos em voo', status: 429 }));
  checar(doBackend.aceito !== false, 'CONTROLE: o 4xx REPASSADO do backend (a pergunta já foi gravada) não devolve o texto — vale o "Tentar de novo"', String(doBackend.aceito));
  const ok = await enviarComResposta(() => respostaSSE([{ protocol: 'autobrokers.interaction.v1', seq: 1, type: 'turn.completed', turn: {}, payload: { status: 'complete' } }]));
  checar(ok.aceito === true, 'CONTROLE: o turno que começou → `true`', String(ok.aceito));
}

/** O Composer real sobre o React dublê com efeitos: anexa um PDF (XHR dublê), envia, e mede o que ficou na caixa. */
async function medirRestauro(resultadoDoEnvio, arquivoDoComposer = ARQ_COMPOSER) {
  const { React, render, rodarEfeitos } = criarReactComEfeitos();
  const stubs = (id) => {
    const b = stubsDeBorda(id);
    if (b !== undefined) return b;
    if (id === 'lucide-react') return new Proxy({}, { get: () => () => null });
    if (/\/(FichaDeAnexo|FolhaDoMais|GravadorDeAudio)$/.test(id)) return new Proxy({}, { get: (_t, k) => (k === '__esModule' ? true : () => null) });
    return undefined;
  };
  const carregar = criarCarregador({ React, stubs });
  const antes = { window: globalThis.window, document: globalThis.document, raf: globalThis.requestAnimationFrame, xhr: globalThis.XMLHttpRequest };
  globalThis.window = { addEventListener() {}, removeEventListener() {}, localStorage: null };
  globalThis.document = { activeElement: null, body: {} };
  globalThis.requestAnimationFrame = (fn) => { fn(0); return 0; };
  globalThis.XMLHttpRequest = class {
    constructor() { this.upload = {}; this.status = 0; this.responseText = ''; }
    open() {}
    abort() {}
    send(corpo) {
      const arquivo = corpo.get('file');
      setTimeout(() => {
        this.status = 201;
        this.responseText = JSON.stringify({ ok: true, bucket: 'chat-docs', path: `co-alfa/u-ana/chat-docs/${arquivo.name}`, nome: arquivo.name, mime: arquivo.type, bytes: arquivo.size, url: '/api/storage/x' });
        this.onload();
      }, 0);
    }
  };
  const espera = () => new Promise((r) => setTimeout(r, 5));
  try {
    const { Composer } = carregar(arquivoDoComposer);
    const ref = { current: null };
    const enviados = [];
    const campo = { value: '', style: {}, scrollHeight: 44, focus() {}, setSelectionRange() {} };
    const props = { onSendMessage: (t, a) => { enviados.push({ t, a }); return Promise.resolve(resultadoDoEnvio); }, initialText: 'Cotação do Onix 2020', focoKey: 'c1', turnStatus: 'idle', ref };
    const passo = () => {
      const arvore = render(Composer, props);
      for (const n of nos(arvore)) if (n.tipo === 'textarea' && n.props.ref && typeof n.props.ref === 'object') n.props.ref.current = campo;
      rodarEfeitos();
      return arvore;
    };
    passo();
    ref.current.adicionarArquivos([new File(['%PDF-1.4'], 'apolice.pdf', { type: 'application/pdf' })]);
    await espera();
    let arvore = passo();
    const enviar = [...nos(arvore)].find((n) => n.tipo === 'button' && n.props['aria-label'] === 'Enviar');
    enviar.props.onClick();
    arvore = passo();
    const logoDepois = [...nos(arvore)].find((n) => n.tipo === 'textarea').props.value;
    await espera();
    arvore = passo();
    const texto = [...nos(arvore)].find((n) => n.tipo === 'textarea').props.value;
    const fichas = [...nos(arvore)].filter((n) => n.props && n.props.nome === 'apolice.pdf').length;
    return { enviados, logoDepois, texto, fichas };
  } finally {
    globalThis.window = antes.window;
    globalThis.document = antes.document;
    globalThis.requestAnimationFrame = antes.raf;
    globalThis.XMLHttpRequest = antes.xhr;
  }
}
{
  // (b) o COMPOSER devolve o texto e os anexos quando a página diz `false`
  const recusa = await medirRestauro(false);
  console.log(`      recusado: enviou ${recusa.enviados.length}× (${recusa.enviados[0]?.a?.length ?? 0} anexo) · caixa logo depois: "${recusa.logoDepois}" · depois da recusa: "${recusa.texto}" + ${recusa.fichas} ficha(s)`);
  checar(recusa.enviados.length === 1 && recusa.enviados[0].a.length === 1 && recusa.logoDepois === '', 'o envio sai com o texto e o anexo, e a caixa esvazia na hora (como antes)');
  checar(recusa.texto === 'Cotação do Onix 2020', 'recusado → o TEXTO volta para a caixa', recusa.texto);
  checar(recusa.fichas === 1, 'recusado → o ANEXO volta para a caixa', String(recusa.fichas));
  const aceito = await medirRestauro(true);
  checar(aceito.texto === '' && aceito.fichas === 0, 'CONTROLE: aceito → a caixa continua vazia', `"${aceito.texto}" + ${aceito.fichas}`);
}

// ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════
console.log('\n[13] Conserto (juiz P3): o Espaço num botão APERTA o botão — não é desviado para a caixa');
// ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════
function medirTeclasForaDaCaixa(arquivoDoComposer = ARQ_COMPOSER) {
  const { React, render, rodarEfeitos } = criarReactComEfeitos();
  const stubs = (id) => {
    const b = stubsDeBorda(id);
    if (b !== undefined) return b;
    if (id === 'lucide-react') return new Proxy({}, { get: () => () => null });
    if (/\/(FichaDeAnexo|FolhaDoMais|GravadorDeAudio)$/.test(id)) return new Proxy({}, { get: (_t, k) => (k === '__esModule' ? true : () => null) });
    return undefined;
  };
  const carregar = criarCarregador({ React, stubs });
  const antes = { window: globalThis.window, document: globalThis.document, raf: globalThis.requestAnimationFrame };
  const ouvintes = [];
  globalThis.window = { addEventListener(t, fn) { if (t === 'keydown') ouvintes.push(fn); }, removeEventListener() {}, localStorage: null };
  const corpo = {};
  globalThis.document = { activeElement: null, body: corpo };
  globalThis.requestAnimationFrame = (fn) => { fn(0); return 0; };
  try {
    const { Composer } = carregar(arquivoDoComposer);
    let focos = 0;
    const campo = { value: '', style: {}, scrollHeight: 44, focus() { focos += 1; }, setSelectionRange() {} };
    const arvore = render(Composer, { onSendMessage() {}, focoKey: 'c1', turnStatus: 'idle' });
    for (const n of nos(arvore)) if (n.tipo === 'textarea' && n.props.ref && typeof n.props.ref === 'object') n.props.ref.current = campo;
    rodarEfeitos();
    const elemento = (tagName, role = null) => ({ tagName, isContentEditable: false, getAttribute: (k) => (k === 'role' ? role : null), closest: () => null });
    const tecla = (key, ativo) => {
      globalThis.document.activeElement = ativo;
      const antesDela = focos;
      for (const fn of ouvintes) fn({ key, ctrlKey: false, metaKey: false, altKey: false });
      return focos - antesDela;
    };
    return {
      espacoNoBotao: tecla(' ', elemento('BUTTON')),
      espacoNoLink: tecla(' ', elemento('A')),
      espacoNoPapelBotao: tecla(' ', elemento('DIV', 'button')),
      letraNoBotao: tecla('a', elemento('BUTTON')),
      espacoNoCorpo: tecla(' ', corpo),
    };
  } finally {
    globalThis.window = antes.window;
    globalThis.document = antes.document;
    globalThis.requestAnimationFrame = antes.raf;
  }
}
{
  const m = medirTeclasForaDaCaixa();
  console.log(`      focus() na caixa · Espaço em <button>: ${m.espacoNoBotao} · em <a>: ${m.espacoNoLink} · em [role=button]: ${m.espacoNoPapelBotao} · letra em <button>: ${m.letraNoBotao} · Espaço sem foco: ${m.espacoNoCorpo}`);
  checar(m.espacoNoBotao === 0, 'Espaço com o foco em "Copiar"/"Tentar de novo"/"+" NÃO vai para a caixa (o botão aciona)');
  checar(m.espacoNoLink === 0 && m.espacoNoPapelBotao === 0, 'idem num link e num elemento com papel de botão');
  checar(m.letraNoBotao >= 1 && m.espacoNoCorpo >= 1, 'CONTROLE: uma LETRA com o foco no botão, e o Espaço sem foco nenhum, continuam indo para a caixa', `letra=${m.letraNoBotao} corpo=${m.espacoNoCorpo}`);
  const K = carregarReal('components/chat/composer/teclado.ts');
  checar(K.teclaVaiParaACaixa({ key: 'Enter' }, null) === false, 'Enter nunca é desviado (não escreve um caractere)');
}

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
console.log(`\n${'='.repeat(78)}`);
if (falhas > 0) {
  console.log(`  ⛔ ${falhas} VERMELHO(S)`);
  process.exit(1);
}
console.log('VERDE — a caixa é uma só, nasce com o cursor, manda os anexos pelo contrato novo e copia a resposta.');
