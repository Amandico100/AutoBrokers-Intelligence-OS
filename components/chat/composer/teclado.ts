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
