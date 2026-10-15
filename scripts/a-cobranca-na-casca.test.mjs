#!/usr/bin/env node
// modelo: claude-opus-5-5
/**
 * A COBRANÇA NA CASCA — SPEC-139 · L2 (D-139-04). O ELO da SPEC: "a Cobrança não mudou PORQUE o Configurar novo
 * grava o MESMO corpo que o modal gravava".
 *
 * Rode: node scripts/a-cobranca-na-casca.test.mjs
 *
 * O que cada bloco prova (e o que NÃO prova):
 *   [1] DOURADO. Os mesmos cliques produzem o MESMO corpo de requisição (sha256 do JSON exato que vai no fetch):
 *       (a) a REFERÊNCIA — o código do modal como ele era em `5f9bdac` (PainelDeRotinas.tsx:458-634), transcrito
 *           aqui e conferido linha a linha contra o `git show` quando o git existe — produz os hashes DOURADOS
 *           cravados abaixo; (b) o código EXTRAÍDO (`components/aplicativos/cobranca-feita/formulario.ts`,
 *           transpilado e CHAMADO de verdade) produz os MESMOS hashes. E o botão Salvar trava nos mesmos estados.
 *   [2] A FIAÇÃO. Cada controle do formulário novo escreve a MESMA chave que o controle do modal escrevia (lido na
 *       fonte: o Next não roda aqui — declarado, CLAUDE.md §9.4), e as DUAS telas (o modal e a aba Configurar)
 *       gravam pelo MESMO caminho (`useFormularioDaRotina().salvar` → POST /api/dashboard/rotinas, corpo de
 *       `corpoDaGravacao`). Nenhuma monta corpo de gravação próprio.
 *   [3] COBRANÇAS. A rota de leitura do que saiu (`.../cobranca/enviadas`), EXECUTADA com um banco de mentira que
 *       honra os filtros e DUAS corretoras: só sai a linha da corretora da sessão; o nome do segurado sai mascarado;
 *       nenhum telefone. A RLS não está aqui de propósito — o que se prova é o filtro no CÓDIGO (CLAUDE.md §7).
 *   [4] O painel antigo continua funcionando com as peças extraídas (o modal usa o formulário extraído; a fila de
 *       pendências e o reenvio de teste continuam nele).
 *   Cada guarda tem PAR DE CONTROLE: a forma defeituosa (mutação em memória) tem de ficar VERMELHA (§9.2/§9.3).
 */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const RAIZ = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const ts = require('typescript');

let falhas = 0;
let pulados = 0;
const conferir = (nome, cond, detalhe = '') => {
  if (cond) { console.log(`  [ok] ${nome}`); return true; }
  falhas += 1; console.log(`  [FALHOU] ${nome}${detalhe ? `\n      ${detalhe}` : ''}`); return false;
};
const par = (nome, acusou, detalhe = '') => {
  if (acusou) { console.log(`  [ok] PAR ${nome} — o guarda acusou`); return true; }
  falhas += 1; console.log(`  [FALHOU] PAR ${nome} — o guarda NÃO acusou; ele não guarda nada${detalhe ? `\n      ${detalhe}` : ''}`);
  return false;
};
const pular = (nome, razao) => { pulados += 1; console.log(`  --   PULADO ${nome}\n      ${razao}`); };

const existe = (rel) => fs.existsSync(path.join(RAIZ, rel));
const ler = (rel) => (existe(rel) ? fs.readFileSync(path.join(RAIZ, rel), 'utf8') : '');
const semComentarios = (src) => src
  .replace(/\/\*[\s\S]*?\*\//g, '')
  .replace(/\{\/\*[\s\S]*?\*\/\}/g, '')
  .replace(/^\s*\/\/.*$/gm, '')
  .replace(/\s\/\/[^\n'"`]*$/gm, '');
const sha = (obj) => crypto.createHash('sha256').update(JSON.stringify(obj)).digest('hex');

/** Transpila um .ts e o executa; `requisitos` resolve os imports (só a borda é dublê). */
function carregar(fonte, nome, requisitos = {}) {
  const js = ts.transpileModule(fonte, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, esModuleInterop: true },
    fileName: nome,
  }).outputText;
  const mod = { exports: {} };
  const req = (m) => {
    if (m in requisitos) return requisitos[m];
    throw new Error(`${nome} importou ${m}, que este teste não oferece`);
  };
  // eslint-disable-next-line no-new-func
  new Function('require', 'module', 'exports', js)(req, mod, mod.exports);
  return mod.exports;
}

const FORMULARIO = 'components/aplicativos/cobranca-feita/formulario.ts';
const VISTA = 'components/aplicativos/cobranca-feita/FormularioDaRotina.tsx';
const HOOK = 'components/aplicativos/cobranca-feita/useFormularioDaRotina.ts';
const CONFIGURAR = 'components/aplicativos/cobranca-feita/AbaConfigurar.tsx';
const COBRANCAS = 'components/aplicativos/cobranca-feita/AbaCobrancas.tsx';
const PENDENCIAS = 'components/aplicativos/cobranca-feita/PendenciasDaCobranca.tsx';
const PAINEL = 'components/auxiliares/PainelDeRotinas.tsx';
const ROTA = 'app/api/dashboard/auxiliaries/cobranca/enviadas/route.ts';
const LEITURA = 'app/api/dashboard/auxiliaries/cobranca/enviadas/leitura.ts';
const BASE = '5f9bdac'; // a origin/main de onde a SPEC-139 partiu: o modal ANTES da extração

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
// [1] A REFERÊNCIA — o modal de 5f9bdac, transcrito. Cada linha marcada com ⟪ ⟫ é conferida contra o git abaixo.
// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
function referenciaDoModal(auxiliarSlug, auxiliarNome, portais) {
  const BILLING_KIND = 'billing_collection';
  const MODOS = ['test', 'none', 'equipe', 'cliente'];
  let form = { name: '', instructions: '', knowledge: '', kind: 'daily', time: '08:00', weekdays: '', minutes: 60, channel: 'whatsapp', number: '', config: {} };
  let editing = null;
  const derivar = () => {
    const billingConfig = form.config?.kind === BILLING_KIND ? form.config : null;
    const billingPortalKeys = billingConfig && Array.isArray(billingConfig.portal_keys)
      ? billingConfig.portal_keys.map((v) => String(v))
      : portais.filter((p) => p.automatizado && p.conectado).map((p) => p.key);
    const billingSendMode = String(billingConfig?.send_mode || 'test');
    const billingModoLegado = !!billingConfig && !MODOS.some((m) => m === billingSendMode);
    const billingTeamNumber = String(billingConfig?.team_number || '');
    const billingTeamDigitos = billingTeamNumber.replace(/\D/g, '');
    const billingConfirmacaoCliente = billingConfig?.confirmacao_cliente === true;
    const billingTestNumber = String(billingConfig?.test_number || '');
    return { billingConfig, billingPortalKeys, billingSendMode, billingModoLegado, billingTeamDigitos, billingConfirmacaoCliente, billingTestNumber };
  };
  const setBillingConfig = (patch) => {
    form = { ...form, config: { ...(form.config || {}), kind: BILLING_KIND, ...patch } }; // ⟪setBillingConfig⟫
  };
  return {
    abrirNovo(modelo) {
      if (modelo) {
        const t = modelo;
        const s = t.schedule_default || {};
        form = {
          name: auxiliarNome, instructions: t.instructions, knowledge: '',
          kind: s.kind === 'interval' ? 'interval' : 'daily', time: s.time || '08:00',
          weekdays: (s.weekdays && s.weekdays.length ? s.weekdays : [0, 1, 2, 3, 4]).join(','),
          minutes: s.minutes || 60, channel: t.delivery_default?.channel === 'none' ? 'none' : 'whatsapp',
          number: '', config: t.config_default || {},
        };
      } else {
        form = { name: auxiliarNome, instructions: '', knowledge: '', kind: 'daily', time: '08:00', weekdays: '0,1,2,3,4', minutes: 60, channel: 'none', number: '', config: {} };
      }
      editing = 'new';
    },
    abrirRotina(r) {
      form = {
        name: r.name, instructions: r.instructions, knowledge: r.knowledge || '',
        kind: r.schedule?.kind === 'interval' ? 'interval' : 'daily', time: r.schedule?.time || '08:00',
        weekdays: (r.schedule?.weekdays || []).join(','), minutes: r.schedule?.minutes || 60,
        channel: r.delivery?.channel || 'whatsapp', number: r.delivery?.number || '', config: (r.config || {}),
      };
      editing = r;
    },
    cobranca: setBillingConfig,
    campo(patch) { form = { ...form, ...patch }; },
    portal(key, marcado) {
      const semEle = derivar().billingPortalKeys.filter((k) => k !== key);
      setBillingConfig({ portal_keys: (marcado ? [...semEle, key] : semEle).sort() });
    },
    dia(valor) {
      const marcados = form.weekdays.split(',').map((x) => x.trim()).filter(Boolean);
      const ativo = marcados.includes(String(valor));
      const sem = marcados.filter((x) => x !== String(valor));
      const novos = ativo ? sem : [...sem, String(valor)];
      form = { ...form, weekdays: novos.sort((a, b) => Number(a) - Number(b)).join(',') };
    },
    corpo() {
      const { billingConfig, billingSendMode, billingTestNumber } = derivar();
      const schedule = form.kind === 'interval'
        ? { kind: 'interval', minutes: Number(form.minutes) }
        : {
            kind: 'daily', time: form.time,
            ...(form.weekdays.trim()
              ? { weekdays: form.weekdays.split(',').map((d) => parseInt(d.trim(), 10)).filter((n) => !isNaN(n)) }
              : {}),
          };
      const delivery = form.channel === 'whatsapp' ? { channel: 'whatsapp', number: form.number } : { channel: 'none' };
      const outgoingConfig = billingConfig && billingSendMode === 'test' && !billingTestNumber.trim() && form.channel === 'whatsapp'
        ? { ...(form.config || {}), test_number: form.number }
        : form.config;
      return {
        action: editing === 'new' ? 'create' : 'update',
        id: editing !== 'new' && editing ? editing.id : undefined,
        auxiliar: auxiliarSlug,
        name: form.name, instructions: form.instructions, knowledge: form.knowledge, schedule, delivery, config: outgoingConfig,
      };
    },
    travado(saving) {
      const d = derivar();
      return !!(
        saving
        || form.name.trim().length < 3
        || (!d.billingConfig && form.instructions.trim().length < 10)
        || (form.channel === 'whatsapp' && form.number.replace(/\D/g, '').length < 10)
        || (d.billingConfig && d.billingSendMode === 'test'
            && d.billingTestNumber.replace(/\D/g, '').length < 10
            && form.number.replace(/\D/g, '').length < 10)
        || (d.billingConfig && d.billingModoLegado)
        || (d.billingConfig && d.billingSendMode === 'equipe'
            && (d.billingTeamDigitos.length < 10 || d.billingTeamDigitos.length > 13))
        || (d.billingConfig && d.billingSendMode === 'cliente' && !d.billingConfirmacaoCliente)
      );
    },
  };
}

/** As linhas da referência que TÊM de existir, iguais, no modal de 5f9bdac (só espaços normalizados). */
const LINHAS_DA_REFERENCIA = [
  "const billingConfig = form.config?.kind === BILLING_KIND ? form.config : null;",
  ": portais.filter((p) => p.automatizado && p.conectado).map((p) => p.key);",
  "setBillingConfig({ portal_keys: (marcado ? [...semEle, key] : semEle).sort() });",
  "const billingSendMode = String(billingConfig?.send_mode || 'test');",
  "const billingTestNumber = String(billingConfig?.test_number || '');",
  "? { kind: 'interval', minutes: Number(form.minutes) }",
  "? { weekdays: form.weekdays.split(',').map((d) => parseInt(d.trim(), 10)).filter((n) => !isNaN(n)) }",
  "const delivery = form.channel === 'whatsapp' ? { channel: 'whatsapp', number: form.number } : { channel: 'none' };",
  "const outgoingConfig = billingConfig && billingSendMode === 'test' && !billingTestNumber.trim() && form.channel === 'whatsapp'",
  "? { ...(form.config || {}), test_number: form.number }",
  "action: editing === 'new' ? 'create' : 'update',",
  "id: editing !== 'new' && editing ? editing.id : undefined,",
  "auxiliar: auxiliarSlug,",
  "name: form.name, instructions: form.instructions, knowledge: form.knowledge, schedule, delivery, config: outgoingConfig,",
  "weekdays: (s.weekdays && s.weekdays.length ? s.weekdays : [0, 1, 2, 3, 4]).join(','),",
  "channel: t.delivery_default?.channel === 'none' ? 'none' : 'whatsapp',",
  "setForm({ name: auxiliarNome, instructions: '', knowledge: '', kind: 'daily', time: '08:00', weekdays: '0,1,2,3,4', minutes: 60, channel: 'none', number: '', config: {} });",
  "weekdays: (r.schedule?.weekdays || []).join(','),",
  "channel: r.delivery?.channel || 'whatsapp',",
  "weekdays: novos.sort((a, b) => Number(a) - Number(b)).join(','),",
  "|| (billingConfig && billingSendMode === 'cliente' && !billingConfirmacaoCliente)",
];

// Os dados de mentira (nenhum segurado, nenhum telefone real: a máscara de formato tem espaços)
const PORTAIS = [
  { key: 'allianz_corretor', name: 'Allianz', category: 'corretor', conectado: true, automatizado: true },
  { key: 'hdi_corretor', name: 'HDI', category: 'corretor', conectado: true, automatizado: false },
  { key: 'mapfre_corretor', name: 'Mapfre', category: 'corretor', conectado: true, automatizado: true },
  { key: 'porto_corretor', name: 'Porto', category: 'corretor', conectado: false, automatizado: true },
];
const MODELO = {
  name: 'Cobranca de boletos atrasados',
  instructions: 'Varre os portais, acha os inadimplentes e baixa os boletos.',
  schedule_default: { kind: 'daily', time: '09:30' },
  delivery_default: { channel: 'whatsapp' },
  config_default: { kind: 'billing_collection', send_mode: 'test', portal_keys: ['allianz_corretor'], attendant_name: 'Atendente Exemplo', max_boletos_por_execucao: 10 },
};
const MODELO_SEM_PORTAIS = { ...MODELO, config_default: { kind: 'billing_collection', send_mode: 'test' } };
const ROTINA_LEGADA = {
  id: 'rotina-legada', name: 'Cobrança', instructions: 'x', knowledge: null,
  schedule: { kind: 'daily', time: '07:15', weekdays: [0, 2, 4] }, delivery: { channel: 'whatsapp', number: '5547 9000 00003' },
  config: { kind: 'billing_collection', send_mode: 'live', portal_keys: ['allianz_corretor'], approval_required: true },
  is_active: false, last_run_at: null, next_run_at: null, consecutive_failures: 0,
};
const ROTINA_TESTE = {
  id: 'rotina-teste', name: 'Cobrança', instructions: 'x',
  schedule: { kind: 'daily', time: '08:00', weekdays: [] }, delivery: { channel: 'whatsapp', number: '55 47 90000-0004' },
  config: { kind: 'billing_collection', send_mode: 'test', portal_keys: ['mapfre_corretor'] },
  is_active: true, last_run_at: null, next_run_at: null, consecutive_failures: 0,
};
const ROTINA_GENERICA = {
  id: 'rotina-generica', name: 'Resumo', instructions: 'Resumo das notícias do mercado de seguros.', knowledge: 'tom formal',
  schedule: { kind: 'interval', minutes: 45 }, delivery: { channel: 'none' }, config: null,
  is_active: true, last_run_at: null, next_run_at: null, consecutive_failures: 0,
};

/** Os cenários: os MESMOS cliques nas duas implementações. */
const CENARIOS = [
  { nome: 'S1 nova pelo modelo → equipe, dias, relatório', slug: 'cobranca-feita', abrir: { novo: MODELO }, cliques: [
    { dia: 4 }, { dia: 5 }, { cobranca: { send_mode: 'equipe' } }, { cobranca: { team_number: '55 47 90000-0001' } },
    { cobranca: { attendant_name: 'Maria' } }, { campo: { channel: 'whatsapp' } }, { campo: { number: '55 47 90000-0002' } }] },
  { nome: 'S2 nova sem modelo → rotina genérica a cada 30 min', slug: 'tarefas-agendadas', abrir: { novo: null }, cliques: [
    { campo: { instructions: 'Resumo diário das notícias do mercado' } }, { campo: { kind: 'interval' } }, { campo: { minutes: 30 } }] },
  { nome: 'S3 rotina legada (live) → cliente confirmado, portal, mensagem com chave errada', slug: 'cobranca-feita', abrir: { rotina: ROTINA_LEGADA }, cliques: [
    { cobranca: { send_mode: 'cliente' } }, { cobranca: { confirmacao_cliente: true } }, { portal: ['hdi_corretor', true] },
    { cobranca: { message_template: 'Olá {primeiro_nome}, {nome_errado}' } }, { cobranca: { attendant_name: 'Ana' } }] },
  { nome: 'S4 teste sem número de simulação → o número do relatório vira o de teste; limites', slug: 'cobranca-feita', abrir: { rotina: ROTINA_TESTE }, cliques: [
    { cobranca: { max_boletos_por_execucao: 2 } }, { cobranca: { dias_entre_cobrancas_do_mesmo_segurado: 10 } }, { campo: { time: '06:45' } }] },
  { nome: 'S5 modelo sem portais → marca pelo que é operacional hoje', slug: 'cobranca-feita', abrir: { novo: MODELO_SEM_PORTAIS }, cliques: [
    { portal: ['mapfre_corretor', true] }, { portal: ['allianz_corretor', false] }, { cobranca: { test_number: '55 47 90000-0005' } },
    { cobranca: { send_mode: 'none' } }, { campo: { channel: 'none' } }] },
  { nome: 'S6 genérica existente → todos os dias desmarcados', slug: 'tarefas-agendadas', abrir: { rotina: ROTINA_GENERICA }, cliques: [
    { campo: { kind: 'daily' } }, { campo: { time: '10:00' } }, { campo: { knowledge: 'tom informal' } }] },
  { nome: 'S7 legado sem escolha → o botão trava (nada sai)', slug: 'cobranca-feita', abrir: { rotina: ROTINA_LEGADA }, cliques: [
    { campo: { time: '07:30' } }] },
];

/** 🔴 Os hashes DOURADOS: o corpo que o modal de 5f9bdac grava em cada cenário. Mudou um byte → vermelho. */
const DOURADO = {
  // 📊 15/10/2026 — produzidos pela REFERÊNCIA (o modal de 5f9bdac) com `node scripts/a-cobranca-na-casca.test.mjs`
  'S1 nova pelo modelo → equipe, dias, relatório': 'ea93bd1bb3f089c1aff6e32664627032e5ad8afd13806f76f510452885514fe4',
  'S2 nova sem modelo → rotina genérica a cada 30 min': 'a222164aa77b242c60f13b71a19f63bf640e6e5a0700d286ce0e1c3a31af4a45',
  'S3 rotina legada (live) → cliente confirmado, portal, mensagem com chave errada': '1728cf0af3b032918e04a1fa36b314eb524848efa741c02c42bdc743808a51d0',
  'S4 teste sem número de simulação → o número do relatório vira o de teste; limites': '7b6017fa5524d1b99eb1501c123ff620a3e8536529599ac3769a807a5b59cdc5',
  'S5 modelo sem portais → marca pelo que é operacional hoje': '966f7153a837c1de341b70ab719b18f7f8c06fb4a9f3c5bd7f527af3191a0eff',
  'S6 genérica existente → todos os dias desmarcados': 'ad1c694d7e20192ce8fbad5cda8071548a32d9608d7337b6676fe24af970d8c2',
  'S7 legado sem escolha → o botão trava (nada sai)': '553aa76193eef5e4cf070e865a971bd84c988a438997755d4208151ff3f7d64c',
};

function rodarReferencia(c) {
  const m = referenciaDoModal(c.slug, 'Cobrança Feita', PORTAIS);
  if (c.abrir.rotina) m.abrirRotina(c.abrir.rotina); else m.abrirNovo(c.abrir.novo);
  const travas = [m.travado(false)];
  for (const k of c.cliques) {
    if (k.dia !== undefined) m.dia(k.dia);
    else if (k.cobranca) m.cobranca(k.cobranca);
    else if (k.campo) m.campo(k.campo);
    else if (k.portal) m.portal(k.portal[0], k.portal[1]);
    travas.push(m.travado(false));
  }
  return { corpo: m.corpo(), travas };
}

function rodarExtraido(F, c) {
  let form;
  let editing;
  if (c.abrir.rotina) { form = F.formDaRotinaSalva(c.abrir.rotina); editing = c.abrir.rotina; }
  else { form = c.abrir.novo ? F.formDoModelo(c.abrir.novo, 'Cobrança Feita') : F.formEmBranco('Cobrança Feita'); editing = 'new'; }
  const travas = [F.salvarTravado(form, false, PORTAIS)];
  for (const k of c.cliques) {
    if (k.dia !== undefined) form = F.alternarDia(form, k.dia);
    else if (k.cobranca) form = F.comCobranca(form, k.cobranca);
    else if (k.campo) form = F.comCampo(form, k.campo);
    else if (k.portal) form = F.alternarPortal(form, PORTAIS, k.portal[0], k.portal[1]);
    travas.push(F.salvarTravado(form, false, PORTAIS));
  }
  return { corpo: F.corpoDaGravacao(form, editing, c.slug, PORTAIS), travas };
}

console.log('\n[1] DOURADO — os mesmos cliques, o MESMO corpo (sha256), no modal de antes e no formulário extraído');

let fonteBase = '';
try {
  fonteBase = execFileSync('git', ['show', `${BASE}:${PAINEL}`], { cwd: RAIZ, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] });
} catch { fonteBase = ''; }
const normalizar = (s) => s.replace(/\s+/g, ' ');
if (fonteBase) {
  const base = normalizar(fonteBase);
  const faltando = LINHAS_DA_REFERENCIA.filter((l) => !base.includes(normalizar(l)));
  conferir(`a referência é o modal de ${BASE}: as ${LINHAS_DA_REFERENCIA.length} linhas-chave estão lá, iguais`, faltando.length === 0,
    `não achei: ${faltando.join(' | ')}`);
  par('a conferência da referência acusa uma linha que o modal NÃO tinha',
    !base.includes(normalizar("auxiliar: auxiliarSlug, origem: 'configurar',")));
} else {
  pular(`a referência contra o git (${BASE})`, 'sem git ou sem o commit nesta cópia; os hashes cravados abaixo continuam valendo');
}

const fonteFormulario = ler(FORMULARIO);
let F = null;
if (!conferir(`o formulário extraído existe (${FORMULARIO})`, fonteFormulario.length > 0)) {
  // sem ele, o resto do bloco não tem o que medir
} else {
  F = carregar(fonteFormulario, 'formulario.ts');
}

const preencher = Object.values(DOURADO).some((v) => v === 'PREENCHER');
for (const c of CENARIOS) {
  const ref = rodarReferencia(c);
  const hRef = sha(ref.corpo);
  if (preencher) console.log(`      ${JSON.stringify(c.nome)}: '${hRef}',`);
  conferir(`${c.nome}: a referência dá o hash DOURADO`, DOURADO[c.nome] === hRef, `referência ${hRef} · dourado ${DOURADO[c.nome]}`);
  if (!F) continue;
  const ext = rodarExtraido(F, c);
  const hExt = sha(ext.corpo);
  conferir(`${c.nome}: o extraído dá o MESMO hash (${hExt.slice(0, 12)}…)`, hExt === DOURADO[c.nome],
    `extraído ${JSON.stringify(ext.corpo)}\n      referência ${JSON.stringify(ref.corpo)}`);
  conferir(`${c.nome}: o Salvar trava nos MESMOS passos (${ref.travas.map((x) => (x ? 'T' : '-')).join('')})`,
    JSON.stringify(ext.travas) === JSON.stringify(ref.travas), `extraído ${ext.travas} · referência ${ref.travas}`);
}
const s7 = rodarReferencia(CENARIOS[6]);
conferir('CONTROLE: o cenário legado termina TRAVADO (a régua consegue dizer "não salva")', s7.travas.at(-1) === true);
conferir('CONTROLE: o S1 termina LIBERADO (a régua consegue dizer "salva")', rodarReferencia(CENARIOS[0]).travas.at(-1) === false);

// PARES — a forma defeituosa do extraído fica VERMELHA (mutação 1 da SPEC, em memória)
if (F) {
  const mutacoes = [
    ['grava um campo a mais no corpo', "auxiliar: auxiliarSlug,", "auxiliar: auxiliarSlug, origem: 'configurar',"],
    ['perde o número de teste herdado do relatório', '? { ...(form.config || {}), test_number: form.number }', '? { ...(form.config || {}) }'],
    ['grava o modo em outra chave', "kind: BILLING_KIND,\n      ...patch,", "kind: BILLING_KIND,\n      ...patch, modo: patch.send_mode,"],
    ['troca a ordem das chaves do corpo', "action: editing === 'new' ? 'create' : 'update',\n    id: editing !== 'new' && editing ? editing.id : undefined,",
      "id: editing !== 'new' && editing ? editing.id : undefined,\n    action: editing === 'new' ? 'create' : 'update',"],
  ];
  for (const [nome, de, para] of mutacoes) {
    if (!fonteFormulario.includes(de)) { conferir(`a âncora da mutação "${nome}" existe`, false, de); continue; }
    const M = carregar(fonteFormulario.replace(de, para), 'formulario-mutado.ts');
    const algumMudou = CENARIOS.some((c) => sha(rodarExtraido(M, c).corpo) !== DOURADO[c.nome]);
    par(`o dourado acusa o formulário que ${nome}`, algumMudou);
  }
}

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
console.log('\n[2] A FIAÇÃO — os controles escrevem as mesmas chaves, e as duas telas gravam pelo mesmo caminho');

const chavesDaCobranca = (src) => new Set(Array.from(semComentarios(src).matchAll(/setBillingConfig\(\{\s*([a-z_]+):/g)).map((m) => m[1]));
const camposDoForm = (src) => new Set(Array.from(semComentarios(src).matchAll(/(?:\.\.\.form,|mudar\(\{)\s*([a-z_]+):/g)).map((m) => m[1]));
const ESPERADAS = ['attendant_name', 'confirmacao_cliente', 'dias_entre_cobrancas_do_mesmo_segurado', 'max_boletos_por_execucao',
  'message_template', 'send_mode', 'team_number', 'test_number'];
const vista = ler(VISTA);
if (fonteBase) {
  // no modal, as seguradoras também passavam por `setBillingConfig({ portal_keys: … })`; no extraído, por `alternarPortal`
  const doModal = [...chavesDaCobranca(fonteBase)].sort();
  conferir('as chaves que o modal de antes gravava são as esperadas (a régua leu o modal)',
    JSON.stringify(doModal) === JSON.stringify([...ESPERADAS, 'portal_keys'].sort()), `modal: ${doModal.join(', ')}`);
}
conferir('as seguradoras gravam `portal_keys` pelo `alternarPortal` extraído',
  /comCobranca\(form, \{ portal_keys:/.test(semComentarios(fonteFormulario)));
const daVista = [...chavesDaCobranca(vista)].sort();
conferir('cada controle da cobrança no formulário novo grava a MESMA chave do modal', JSON.stringify(daVista) === JSON.stringify(ESPERADAS),
  `formulário novo: ${daVista.join(', ') || '(nada)'} · esperado: ${ESPERADAS.join(', ')}`);
const camposVista = [...camposDoForm(vista)].sort();
const CAMPOS = ['channel', 'instructions', 'kind', 'knowledge', 'minutes', 'number', 'time'];
conferir('e os campos fora da cobrança são os mesmos (dias da semana pelo `alternarDia`)',
  JSON.stringify(camposVista) === JSON.stringify(CAMPOS) && /alternarDia\(d\.valor\)/.test(vista) && /alternarPortal\(p\.key/.test(vista),
  `formulário novo: ${camposVista.join(', ')}`);
par('a fiação acusa um controle que grava outra chave (mutação 1: "o Configurar grava um campo diferente")',
  [...chavesDaCobranca(vista.replace('setBillingConfig({ attendant_name:', 'setBillingConfig({ atendente:'))].sort().join() !== ESPERADAS.join());

const hook = semComentarios(ler(HOOK));
conferir('o hook grava na ÚNICA rota, com o corpo de `corpoDaGravacao`',
  /fetch\(ROTA_DAS_ROTINAS,/.test(hook) && /body:\s*JSON\.stringify\(corpoDaGravacao\(form, editing, auxiliarSlug, portais\)\)/.test(hook)
  && /ROTA_DAS_ROTINAS = '\/api\/dashboard\/rotinas'/.test(fonteFormulario));

const gravaPorFora = (src) => {
  const s = semComentarios(src);
  // gravação = um corpo com `action: 'create'|'update'` ou montado à mão; as ações da lista vão por `corpoDaAcao`
  return /action:\s*(?:editing|'create'|'update')/.test(s)
    || /JSON\.stringify\(\{[^}]*\b(?:schedule|delivery|config)\b/.test(s)
    || Array.from(s.matchAll(/body:\s*JSON\.stringify\(([A-Za-z_]+)/g)).some((m) => m[1] !== 'corpoDaAcao');
};
for (const [nome, rel] of [['o modal (PainelDeRotinas)', PAINEL], ['a aba Configurar', CONFIGURAR]]) {
  const src = ler(rel);
  if (!conferir(`${nome} existe`, src.length > 0, rel)) continue;
  conferir(`${nome} usa o formulário extraído e o hook`, /<FormularioDaRotina\b/.test(src) && /useFormularioDaRotina\(/.test(src));
  conferir(`${nome} grava pelo \`salvar()\` do hook`, /\.salvar\(\)/.test(semComentarios(src)));
  conferir(`${nome} NÃO monta corpo de gravação próprio`, !gravaPorFora(src));
}
const configurar = ler(CONFIGURAR);
par('o guarda acusa a aba Configurar com um POST de gravação montado à mão',
  gravaPorFora(`${configurar}\nfetch('/api/dashboard/rotinas', { method: 'POST', body: JSON.stringify({ action: 'update', id, config }) });`));
conferir('a aba Configurar só configura com o aplicativo instalado (sem ele a rotina nasceria noutro dono)',
  /if \(!item\??\.instalado\) \{?\s*return/.test(semComentarios(configurar)));

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
console.log('\n[3] COBRANÇAS — a leitura do que saiu, executada com duas corretoras');

/** As datas são relativas a hoje: o teste não envelhece. `to_phone` existe no banco de mentira para provar que não sai. */
const diasAtras = (n) => new Date(Date.now() - n * 86_400_000).toISOString();
const LINHAS = [
  { id: 'a1', company_id: 'corretora-a', status: 'aceito_pelo_canal', send_mode: 'real', modalidade: 'cliente', portal_key: 'allianz_corretor', recibo: '111', cliente_nome: 'Fulana de Tal Exemplo', to_phone: '5547900000099', to_last4: '0099', sent_at: diasAtras(1), created_at: diasAtras(1), encaminhado_ao_cliente_em: null, canario: false },
  { id: 'a2', company_id: 'corretora-a', status: 'entregue', send_mode: 'test', modalidade: 'test', portal_key: 'mapfre_corretor', recibo: '222', cliente_nome: 'Beltrano Exemplo', to_phone: '5547900000098', to_last4: '0098', sent_at: diasAtras(2), created_at: diasAtras(2), encaminhado_ao_cliente_em: null, canario: false },
  { id: 'b1', company_id: 'corretora-b', status: 'aceito_pelo_canal', send_mode: 'real', modalidade: 'cliente', portal_key: 'hdi_corretor', recibo: '333', cliente_nome: 'Cicrano Da Outra', to_phone: '5547900000097', to_last4: '0097', sent_at: diasAtras(1), created_at: diasAtras(1), encaminhado_ao_cliente_em: null, canario: false },
  { id: 'a0', company_id: 'corretora-a', status: 'aceito_pelo_canal', send_mode: 'real', modalidade: 'cliente', portal_key: 'allianz_corretor', recibo: '000', cliente_nome: 'Antiga Demais', to_phone: '5547900000096', to_last4: '0096', sent_at: diasAtras(200), created_at: diasAtras(200), encaminhado_ao_cliente_em: null, canario: false },
];

/** Um banco de mentira que HONRA os filtros (eq, gte, in, order, limit) e anota o que foi pedido. */
function bancoDeMentira(linhas) {
  const pedidos = [];
  return {
    pedidos,
    from(tabela) {
      const q = { tabela, filtros: [], colunas: '', ordem: null, limite: null };
      pedidos.push(q);
      const api = {
        select(c) { q.colunas = c; return api; },
        eq(col, v) { q.filtros.push(['eq', col, v]); return api; },
        gte(col, v) { q.filtros.push(['gte', col, v]); return api; },
        lte(col, v) { q.filtros.push(['lte', col, v]); return api; },
        in(col, v) { q.filtros.push(['in', col, v]); return api; },
        order(col, o) { q.ordem = [col, o]; return api; },
        limit(n) { q.limite = n; return api; },
        then(ok, erro) {
          let r = linhas.filter((l) => q.filtros.every(([op, col, v]) => (op === 'eq' ? l[col] === v
            : op === 'gte' ? String(l[col]) >= String(v) : op === 'lte' ? String(l[col]) <= String(v) : v.includes(l[col]))));
          if (q.ordem) r = [...r].sort((x, y) => (String(x[q.ordem[0]]) < String(y[q.ordem[0]]) ? 1 : -1) * (q.ordem[1]?.ascending ? -1 : 1));
          if (q.limite) r = r.slice(0, q.limite);
          const cols = q.colunas.split(',').map((x) => x.trim()).filter(Boolean);
          const dados = r.map((l) => Object.fromEntries(cols.map((cc) => [cc, l[cc]])));
          return Promise.resolve({ data: dados, error: null }).then(ok, erro);
        },
      };
      return api;
    },
  };
}

async function chamarRota(fonteRota, sessao, linhas, consulta = '') {
  const banco = bancoDeMentira(linhas);
  const leitura = carregar(ler(LEITURA), 'leitura.ts');
  const R = carregar(fonteRota, 'route.ts', {
    'next/server': { NextResponse: { json: (corpo, init) => ({ corpo, status: init?.status ?? 200 }) } },
    '@/lib/vault/server': { resolveSessionCompany: async () => sessao, getSupabaseAdmin: () => banco },
    './leitura': leitura,
  });
  const req = { nextUrl: new URL(`http://x/api/dashboard/auxiliaries/cobranca/enviadas${consulta}`) };
  const resp = await R.GET(req);
  return { ...resp, banco };
}

const fonteRota = ler(ROTA);
if (conferir(`a rota de leitura existe (${ROTA})`, fonteRota.length > 0) && conferir(`e o leitor puro (${LEITURA})`, ler(LEITURA).length > 0)) {
  const AGORA_FIXO = '2026-10-15T12:00:00Z';
  // a rota usa o relógio de verdade (as linhas são relativas a hoje); o "desde" exato é provado no leitor puro
  const fonteRotaFixa = fonteRota;
  const L = carregar(ler(LEITURA), 'leitura.ts');
  const A = await chamarRota(fonteRotaFixa, { companyId: 'corretora-a', userId: 'pessoa-a' }, LINHAS, '?periodo=90');
  const ids = (A.corpo?.itens || []).map((x) => x.id);
  conferir('a corretora A vê só as linhas DELA', A.status === 200 && ids.length > 0 && ids.every((id) => id.startsWith('a')), `ids: ${ids.join(', ')}`);
  conferir('e nenhuma da corretora B', !ids.includes('b1'));
  const B = await chamarRota(fonteRotaFixa, { companyId: 'corretora-b', userId: 'pessoa-b' }, LINHAS, '?periodo=90');
  const idsB = (B.corpo?.itens || []).map((x) => x.id);
  conferir('a corretora B vê só a linha dela', JSON.stringify(idsB) === JSON.stringify(['b1']), `ids: ${idsB.join(', ')}`);
  const pedido = A.banco.pedidos.find((p) => p.tabela === 'billing_sent_log');
  conferir('a rota lê `billing_sent_log` filtrando `company_id` pela SESSÃO', !!pedido && pedido.filtros.some(([op, c, v]) => op === 'eq' && c === 'company_id' && v === 'corretora-a'));
  conferir('a rota não pede o telefone inteiro (`to_phone`) nem o canário', !!pedido && !/to_phone|canario/.test(pedido.colunas), pedido?.colunas);
  const texto = JSON.stringify(A.corpo);
  conferir('o nome do segurado sai MASCARADO (nada do sobrenome inteiro)', !/Fulana de Tal|Tal Exemplo|Beltrano Exemplo/.test(texto) && /Fulana T\. E\./.test(texto), texto.slice(0, 300));
  conferir('nenhum telefone inteiro na resposta', !/\d{10,}/.test(texto.replace(/"(?:sent_at|quando|created_at)":"[^"]*"/g, '')));
  conferir('a linha de teste vem marcada como teste', (A.corpo?.itens || []).some((x) => x.id === 'a2' && x.teste === true));
  const A7 = await chamarRota(fonteRotaFixa, { companyId: 'corretora-a', userId: 'pessoa-a' }, LINHAS, '?periodo=qualquer-coisa');
  conferir('período inválido cai no padrão (30 dias), nunca "tudo"', A7.corpo?.periodo === 30, `periodo=${A7.corpo?.periodo}`);
  const sem = await chamarRota(fonteRotaFixa, null, LINHAS);
  conferir('sem sessão: 401 e nenhuma leitura', sem.status === 401 && sem.banco.pedidos.length === 0);
  conferir('o leitor mascara do jeito certo', L.mascararNome('Ana Maria Ribeiro') === 'Ana M. R.' && L.mascararNome('  ') === null && L.mascararNome('Prince') === 'Prince');
  conferir('o "desde" do período é calculado do relógio recebido', L.desdeDoPeriodo(7, new Date(AGORA_FIXO)) === '2026-10-08T12:00:00.000Z');

  // MUTAÇÃO 3 da SPEC: "Cobranças mostra linha de OUTRA corretora" — o filtro some do código
  const ancora = ".eq('company_id', ctx.companyId)";
  if (conferir('a âncora da mutação 3 existe na rota', fonteRota.includes(ancora))) {
    // TODAS as ocorrências: a primeira é a do comentário que explica o filtro (tirar só ela não mudaria nada)
    const M = await chamarRota(fonteRota.split(ancora).join(''),{ companyId: 'corretora-a', userId: 'pessoa-a' }, LINHAS, '?periodo=90');
    par('o guarda acusa a rota sem o filtro de corretora (linha da B aparece para a A)',
      (M.corpo?.itens || []).some((x) => x.id === 'b1'));
  }
}

const cobrancas = ler(COBRANCAS);
if (conferir(`a aba Cobranças existe (${COBRANCAS})`, cobrancas.length > 0)) {
  const s = semComentarios(cobrancas);
  conferir('ela lê da rota de leitura (e de nenhuma outra tabela)', /auxiliaries\/cobranca\/enviadas/.test(s) && !/supabase|\.from\('/.test(s));
  conferir('ela é só leitura (nenhum POST)', !/method:\s*'POST'/.test(s));
  conferir('ela tem filtro de período e estado vazio humano', /periodo/.test(s) && /Nenhuma cobrança/.test(s));
}

// ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
console.log('\n[4] O painel antigo continua inteiro, com as peças extraídas');
const painel = ler(PAINEL);
const painelSem = semComentarios(painel);
conferir('o modal continua no painel (abre, tem Cancelar e Salvar)', /editing !== null|f\.editing !== null/.test(painelSem) && /Cancelar/.test(painelSem));
conferir('o modal desenha o formulário extraído', /<FormularioDaRotina\b/.test(painelSem));
conferir('a fila de pendências continua no painel da Cobrança', /<PendenciasDaCobranca\b/.test(painelSem));
conferir('e o reenvio de teste também', /<LiberarReenvioDeTeste\b/.test(painelSem));
conferir('nenhuma cópia das regras ficou no painel (as constantes moram no formulário extraído)',
  !/const MODOS_COM_MOTOR =|const CHAVES_DA_MENSAGEM =|const MENSAGEM_PADRAO =/.test(painelSem));
conferir('a fila mora na aba Cobranças também ("Precisa de você")', /<PendenciasDaCobranca\b/.test(semComentarios(cobrancas)));
const pend = semComentarios(ler(PENDENCIAS));
conferir('a fila continua com as mesmas três rotas', /cobranca\/pendencias/.test(pend) && /auxiliaries\/cobranca\/\$\{acao\}/.test(pend)
  && /'encaminhado'/.test(pend) && /'liberar'/.test(pend));

console.log(falhas === 0
  ? `\nTODOS OS GUARDAS VERDES${pulados ? ` (${pulados} pulado(s))` : ''}\n`
  : `\n${falhas} GUARDA(S) VERMELHO(S)${pulados ? ` · ${pulados} pulado(s)` : ''}\n`);
process.exit(falhas === 0 ? 0 : 1);
