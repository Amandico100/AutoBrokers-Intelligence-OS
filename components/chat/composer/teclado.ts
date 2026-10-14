/**
 * SPEC-132-A · A1 — o Enter. No notebook, Enter envia e Shift+Enter quebra a linha. No celular (toque), Enter
 * quebra a linha e quem envia é o botão — é o que o teclado do celular promete, e é o que ChatGPT e Claude fazem.
 * Durante a composição de acentos/IME (`isComposing`), o Enter é da composição, nunca do envio.
 */
export function deveEnviarNoEnter(e: {
  key: string;
  shiftKey?: boolean;
  isComposing?: boolean;
  toque: boolean;
}): boolean {
  if (e.key !== 'Enter') return false;
  if (e.isComposing) return false;
  if (e.shiftKey) return false;
  return !e.toque;
}

/** O aparelho é de toque (ponteiro grosso, sem hover)? Sem `matchMedia` (servidor, teste) = notebook. */
export function aparelhoDeToque(): boolean {
  try {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return false;
    return window.matchMedia('(pointer: coarse)').matches && !window.matchMedia('(hover: hover)').matches;
  } catch {
    return false;
  }
}

/** Uma tecla que escreve um caractere (para levar o foco à caixa quando o corretor começa a digitar fora dela). */
export function teclaQueEscreve(e: { key: string; ctrlKey?: boolean; metaKey?: boolean; altKey?: boolean }): boolean {
  return e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey;
}

/** O elemento com o foco, no que importa para decidir se a tecla vai para a caixa. */
export interface ElementoComFoco {
  tagName?: string;
  isContentEditable?: boolean;
  getAttribute?: (nome: string) => string | null;
  closest?: (seletor: string) => unknown;
}

/** Papéis que o Espaço ACIONA (o navegador aperta o botão; não é texto). */
const PAPEIS_QUE_O_ESPACO_ACIONA = new Set(['button', 'link', 'checkbox', 'switch', 'menuitem', 'tab', 'option', 'radio']);

/**
 * A tecla apertada FORA da caixa deve levar o foco para ela? (o corretor começou a digitar no meio da conversa)
 *
 * 🔴 Conserto da SPEC-132-A (juiz P3): o Espaço num botão ("Copiar", "Tentar de novo", "+", a barra lateral) é o
 * jeito de APERTAR o botão pelo teclado — levá-lo para a caixa fazia o botão não acionar. Espaço em botão, link ou
 * controle com papel de botão fica com eles; as letras continuam indo para a caixa.
 */
export function teclaVaiParaACaixa(
  e: { key: string; ctrlKey?: boolean; metaKey?: boolean; altKey?: boolean },
  ativo: ElementoComFoco | null,
  corpo: unknown = null,
): boolean {
  if (!teclaQueEscreve(e)) return false;
  if (!ativo || ativo === corpo) return true;
  const tag = String(ativo.tagName || '').toUpperCase();
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || ativo.isContentEditable) return false;
  if (typeof ativo.closest === 'function' && ativo.closest('[role="dialog"]')) return false;
  if (e.key === ' ') {
    if (tag === 'BUTTON' || tag === 'A' || tag === 'SUMMARY') return false;
    const papel = typeof ativo.getAttribute === 'function' ? String(ativo.getAttribute('role') || '') : '';
    if (PAPEIS_QUE_O_ESPACO_ACIONA.has(papel.toLowerCase())) return false;
  }
  return true;
}
