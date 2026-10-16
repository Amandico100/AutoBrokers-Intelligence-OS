/**
 * SPEC-129-D · conserto K2 (red team B3) — o corpo que a rota Next manda ao backend com as respostas de vida do cliente.
 *
 * 🔴 `company_id` e `user_id` vêm SEMPRE da sessão: o que o navegador mandar nesses nomes é IGNORADO. Do navegador só
 *    passam as quatro respostas, cada uma no tipo certo (sim/não é booleano, a renda é número, a profissão é texto) —
 *    qualquer outra chave (um `estado`, uma `coluna`) não atravessa.
 * ⛔ Nada é presumido: a resposta que não veio não vira "não". ⛔ Nada aqui é logado (fumante e renda: LGPD art. 11).
 *
 * Puro (sem import): o guarda `components/aplicativos/renovacao/as-respostas-de-vida-chegam-a-tela.test.mjs` o chama.
 */
export const CAMPOS_DA_RESPOSTA = ['fumante', 'renda_mensal', 'esporte_radical', 'profissao_texto'] as const;

export interface SessaoDasRespostas {
  companyId: string;
  userId: string;
}

export function corpoDasRespostas(corpo: unknown, s: SessaoDasRespostas): Record<string, unknown> {
  const c = (corpo && typeof corpo === 'object' ? corpo : {}) as Record<string, unknown>;
  const saida: Record<string, unknown> = {};
  if (typeof c.fumante === 'boolean') saida.fumante = c.fumante;
  if (typeof c.esporte_radical === 'boolean') saida.esporte_radical = c.esporte_radical;
  if (typeof c.renda_mensal === 'number' && Number.isFinite(c.renda_mensal)) saida.renda_mensal = c.renda_mensal;
  if (typeof c.profissao_texto === 'string' && c.profissao_texto.trim()) {
    saida.profissao_texto = c.profissao_texto.trim().slice(0, 120);
  }
  // por ÚLTIMO: a sessão vence qualquer `company_id`/`user_id` que o navegador tenha posto no corpo
  return { ...saida, company_id: s.companyId, user_id: s.userId };
}
