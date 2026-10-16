// SPEC-129-D · conserto K2 (juiz B1 · red team B3) — as regras PURAS do formulário "As respostas do cliente" no
// detalhe de uma renovação de VIDA pendente. Sem import: o guarda `as-respostas-de-vida-chegam-a-tela.test.mjs` as chama.
//
// ⛔ NUNCA valor padrão: o rascunho nasce VAZIO (nem "Sim" nem "Não" marcado, renda em branco). Fumante, renda e esporte
//    são declaração do cliente — um "não" que ninguém disse pode fazer perder a garantia (Código Civil, art. 766).
// ⛔ Nada aqui é logado nem guardado no navegador (LGPD art. 11).

export type CampoDaResposta = 'fumante' | 'renda_mensal' | 'esporte_radical' | 'profissao_texto';

export interface RespostasDeVidaDoDetalhe {
  campos: CampoDaResposta[];
  aviso: string;
  ja_respondido: boolean;
}

export interface Rascunho {
  fumante: boolean | null;
  renda_mensal: string;
  esporte_radical: boolean | null;
  profissao_texto: string;
}

export const ROTULO_DO_CAMPO: Record<CampoDaResposta, string> = {
  fumante: 'O cliente fuma?',
  renda_mensal: 'Qual a renda mensal do cliente?',
  esporte_radical: 'Pratica esporte radical?',
  profissao_texto: 'Qual a profissão do cliente?',
};

/** O rascunho VAZIO — nada marcado. */
export function rascunhoVazio(): Rascunho {
  return { fumante: null, renda_mensal: '', esporte_radical: null, profissao_texto: '' };
}

/** O formulário aparece SÓ numa renovação de vida pendente que espera resposta (o backend manda os campos). */
export function mostraFormulario(d: { estado?: string | null; respostas_de_vida?: RespostasDeVidaDoDetalhe | null }) {
  return d.estado === 'pendente' && Boolean(d.respostas_de_vida) && (d.respostas_de_vida?.campos.length ?? 0) > 0;
}

/** "8.500,00" · "8500" · "R$ 8.500" → 8500. Vazio, negativo ou ilegível → null (nunca um número inventado). */
export function lerRenda(texto: string): number | null {
  const limpo = String(texto || '').replace(/[R$\s]/g, '');
  if (!limpo) return null;
  // com vírgula: o ponto é milhar ("8.500,00"); sem vírgula: ponto seguido de 3 dígitos também é milhar ("8.500")
  const normal = limpo.includes(',')
    ? limpo.replace(/\./g, '').replace(',', '.')
    : /^\d{1,3}(\.\d{3})+$/.test(limpo)
      ? limpo.replace(/\./g, '')
      : limpo;
  if (!/^\d+(\.\d{1,2})?$/.test(normal)) return null;
  const n = Number(normal);
  return Number.isFinite(n) && n >= 0 ? n : null;
}

/** O corpo do POST a partir do rascunho — só os campos pedidos, cada um respondido. Falta algum → o erro em português. */
export function corpoDoRascunho(
  r: Rascunho,
  campos: CampoDaResposta[],
): { ok: true; corpo: Record<string, unknown> } | { ok: false; erro: string } {
  const corpo: Record<string, unknown> = {};
  for (const c of campos) {
    if (c === 'fumante' || c === 'esporte_radical') {
      if (r[c] === null) return { ok: false, erro: `Responda: ${ROTULO_DO_CAMPO[c]}` };
      corpo[c] = r[c];
    } else if (c === 'renda_mensal') {
      const n = lerRenda(r.renda_mensal);
      if (n === null) return { ok: false, erro: 'Escreva a renda mensal em reais (ex.: 8.500,00).' };
      corpo.renda_mensal = n;
    } else if (c === 'profissao_texto') {
      const t = r.profissao_texto.trim();
      if (t.length < 2) return { ok: false, erro: 'Escreva a profissão do cliente.' };
      corpo.profissao_texto = t;
    }
  }
  return { ok: true, corpo };
}
