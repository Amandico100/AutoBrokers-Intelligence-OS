// Seleção conversacional de apólice (42W1) — helper PURO, sem I/O, sem LLM.
//
// No dashboard a apólice é escolhida por botão; no WhatsApp o segurado responde
// por texto ("a primeira", "final 99", "97652", "a que vence em 2026"). Este
// helper resolve a escolha de forma DETERMINÍSTICA contra os matches já
// retornados pela InfoCap. Nunca inventa policy_ref; só aceita ref que está nos
// matches. Se ambíguo, não seleciona e pede esclarecimento.

export interface PolicyMatchLite {
  policy_ref: string;
  insurer_key?: string | null;
  product?: string | null;
  masked_policy_number?: string | null;
  valid_to?: string | null;
  active_now?: boolean | null;
  cancelled?: boolean | null;
}

export interface PolicySelectionResult {
  resolved: boolean;
  policy_ref: string | null;
  strategy:
    | 'explicit_ref'
    | 'masked_suffix'
    | 'date'
    | 'ordinal'
    | 'affirmative_single'
    | 'insurer_product'
    | 'none';
  ambiguous: boolean;
  reason: string;
}

const ORDINAL_WORDS: Record<string, number> = {
  primeira: 1, primeiro: 1, um: 1, uma: 1,
  segunda: 2, segundo: 2, dois: 2, duas: 2,
  terceira: 3, terceiro: 3, tres: 3, 'três': 3,
  quarta: 4, quarto: 4, quatro: 4,
  quinta: 5, quinto: 5, cinco: 5,
};

const AFFIRMATIVE_RE = /\b(sim|isso|essa|esse|pode ser|pode|esta|está|aceito|ok|confirmo|claro)\b/i;

function norm(s: string): string {
  return (s || '').toString().trim().toLowerCase();
}

function digitsOf(s?: string | null): string {
  return (s || '').replace(/\D/g, '');
}

/** Resolve a escolha de apólice a partir do texto do cliente. PURO/determinístico. */
export function resolvePolicySelectionFromCustomerReply(
  message: string,
  matches: PolicyMatchLite[],
): PolicySelectionResult {
  const list = Array.isArray(matches) ? matches.filter((m) => m && typeof m.policy_ref === 'string') : [];
  const m = norm(message);
  if (!m || list.length === 0) {
    return { resolved: false, policy_ref: null, strategy: 'none', ambiguous: false, reason: 'no_input_or_matches' };
  }
  const refs = new Set(list.map((x) => x.policy_ref));

  const decide = (cands: PolicyMatchLite[], strategy: PolicySelectionResult['strategy']): PolicySelectionResult | null => {
    const uniq = Array.from(new Set(cands.map((c) => c.policy_ref))).filter((r) => refs.has(r));
    if (uniq.length === 1) return { resolved: true, policy_ref: uniq[0], strategy, ambiguous: false, reason: strategy };
    if (uniq.length > 1) return { resolved: false, policy_ref: null, strategy, ambiguous: true, reason: `${strategy}_ambiguous` };
    return null;
  };

  // 1) policy_ref explícito (token idêntico a um ref dos matches).
  const tokens = m.split(/[^0-9a-zà-ú]+/i).filter(Boolean);
  const explicit = list.filter((x) => tokens.includes(norm(x.policy_ref)));
  let r = decide(explicit, 'explicit_ref');
  if (r) return r;

  // 2) "final 99" / "termina em 99" / "final ****99".
  const finalMatch = m.match(/\b(?:final|termina(?:\s+em)?|finaliza(?:\s+em)?|terminada\s+em)\D*(\d{2,6})\b/);
  if (finalMatch) {
    const suffix = finalMatch[1];
    const cands = list.filter((x) => {
      const md = digitsOf(x.masked_policy_number);
      const rd = digitsOf(x.policy_ref);
      return (md && md.endsWith(suffix)) || (rd && rd.endsWith(suffix));
    });
    r = decide(cands, 'masked_suffix');
    if (r) return r;
  }

  // 3) data/ano de vigência ("vence em 31/10/2026", "a de 2026").
  const dateToken = m.match(/\b(\d{2}\/\d{2}\/\d{4})\b/);
  const yearToken = m.match(/\b(20\d{2})\b/);
  if (dateToken || yearToken) {
    const cands = list.filter((x) => {
      const vt = norm(x.valid_to || '');
      if (!vt) return false;
      if (dateToken && vt.includes(dateToken[1])) return true;
      if (yearToken && digitsOf(vt).includes(yearToken[1])) return true;
      return false;
    });
    r = decide(cands, 'date');
    if (r) return r;
  }

  // 4) ordinal/número ("a primeira", "2", "opção 3").
  let idx: number | null = null;
  for (const w of tokens) {
    if (ORDINAL_WORDS[w]) { idx = ORDINAL_WORDS[w]; break; }
    if (/^[1-9]$/.test(w)) { idx = parseInt(w, 10); break; }
  }
  if (idx != null && idx >= 1 && idx <= list.length) {
    return { resolved: true, policy_ref: list[idx - 1].policy_ref, strategy: 'ordinal', ambiguous: false, reason: 'ordinal' };
  }
  if (idx != null) {
    return { resolved: false, policy_ref: null, strategy: 'ordinal', ambiguous: true, reason: 'ordinal_out_of_range' };
  }

  // 5) seguradora/produto quando desambigua sozinho.
  const ip = list.filter((x) => {
    const ins = norm(x.insurer_key || '');
    const prod = norm(x.product || '');
    return (ins && m.includes(ins)) || (prod && m.includes(prod));
  });
  r = decide(ip, 'insurer_product');
  if (r) return r;

  // 6) afirmativo quando só há UMA opção.
  if (list.length === 1 && AFFIRMATIVE_RE.test(m)) {
    return { resolved: true, policy_ref: list[0].policy_ref, strategy: 'affirmative_single', ambiguous: false, reason: 'affirmative_single' };
  }

  return { resolved: false, policy_ref: null, strategy: 'none', ambiguous: false, reason: 'unresolved' };
}

function humanInsurer(k?: string | null): string {
  const v = (k || '').toUpperCase();
  if (v === 'ALLI') return 'Allianz';
  return (k || 'Seguradora').toString();
}

/** Lista curta e mascarada de apólices para pedir a seleção ao cliente (humana). */
export function buildPolicyOptionsMessage(matches: PolicyMatchLite[]): string {
  const list = Array.isArray(matches) ? matches.slice(0, 5) : [];
  if (list.length === 0) return 'Não encontrei apólices para confirmar. Pode me passar o número da apólice?';
  const lines = list.map((x, i) => {
    const ins = humanInsurer(x.insurer_key);
    const prod = x.product ? ` ${x.product}` : '';
    const fin = x.masked_policy_number ? ` final ${x.masked_policy_number}` : '';
    const vig = x.cancelled
      ? ' — cancelada'
      : x.active_now === false
        ? ' — vencida'
        : x.valid_to
          ? ` — vigente até ${x.valid_to}`
          : '';
    return `${i + 1}) ${ins}${prod}${fin}${vig}`;
  });
  return `Encontrei mais de uma apólice. Qual delas devo usar?\n${lines.join('\n')}`;
}

/** Resposta humana após selecionar (sem expor número cru). */
export function buildPolicySelectedMessage(match: PolicyMatchLite | undefined): string {
  if (!match) return 'Perfeito, registrei a apólice. Vou seguir com os dados do atendimento.';
  const fin = match.masked_policy_number ? ` com final ${match.masked_policy_number}` : '';
  const vig = match.active_now === true ? ' Ela está vigente.' : '';
  return `Perfeito, selecionei a apólice${fin}.${vig} Vou seguir com os dados do atendimento.`;
}
