// SPEC-133-A.1 (conserto, juiz P3-4) — a regra da senha que o admin dá a um membro da equipe.
//
// 📊 Antes: o padrão era a senha fixa "mudar123", e o servidor ainda a aceitava quando vinha no pedido (mínimo 6).
// Quem soubesse o e-mail de um membro novo entrava. A regra mora AQUI (pura, sem rede) para que o POST e o PATCH de
// `app/api/dashboard/team/route.ts` usem a MESMA — e para que o teste rode a regra real, não uma cópia.

export const SENHA_MEMBRO_MIN = 10;
export const SENHA_MEMBRO_MAX = 256;

// senhas conhecidas que nunca servem — a antiga padrão da casa, comparada sem caixa e sem espaço
const PROIBIDAS = new Set(['mudar123']);

/** `null` = aceita; texto = o motivo da recusa, para mostrar ao admin. */
export function recusaDaSenhaDoMembro(senha: unknown): string | null {
  const s = typeof senha === 'string' ? senha : '';
  if (!s) return 'Informe a senha.';
  if (PROIBIDAS.has(s.trim().toLowerCase().replace(/\s+/g, ''))) {
    return 'Essa senha é a antiga padrão e qualquer um a conhece — use outra (a tela já sugere uma aleatória).';
  }
  if (s.length < SENHA_MEMBRO_MIN) return `Senha muito curta (mínimo ${SENHA_MEMBRO_MIN} caracteres).`;
  if (s.length > SENHA_MEMBRO_MAX) return `Senha comprida demais (máximo ${SENHA_MEMBRO_MAX} caracteres).`;
  return null;
}
