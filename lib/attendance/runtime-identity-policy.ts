// Runtime Identity Policy (42B5G).
//
// Extração segura de documento (CPF/CNPJ) e mensagens da etapa de identidade.
// PURO, sem I/O. Valida apenas formato/tamanho neste batch (sem dígito verificador).
// NÃO consulta InfoCap, NÃO confirma cobertura, NÃO loga o número completo.

export type DocumentType = 'cpf' | 'cnpj' | null;

export interface DocumentExtraction {
  type: DocumentType;
  /** Apenas dígitos (11 = CPF, 14 = CNPJ). Nunca logar completo. */
  ref: string | null;
  valid: boolean;
}

/** Extrai CPF (11 dígitos) ou CNPJ (14 dígitos), com ou sem pontuação. */
export function extractDocument(message: string): DocumentExtraction {
  const text = message || '';

  // CNPJ primeiro (mais longo): 00.000.000/0000-00
  const cnpj = text.match(/\d{2}[.\s]?\d{3}[.\s]?\d{3}[/\s]?\d{4}[-\s]?\d{2}/);
  if (cnpj) {
    const ref = cnpj[0].replace(/\D/g, '');
    if (ref.length === 14) return { type: 'cnpj', ref, valid: true };
  }

  // CPF: 000.000.000-00
  const cpf = text.match(/\d{3}[.\s]?\d{3}[.\s]?\d{3}[-\s]?\d{2}/);
  if (cpf) {
    const ref = cpf[0].replace(/\D/g, '');
    if (ref.length === 11) return { type: 'cpf', ref, valid: true };
  }

  // Fallback: qualquer sequência de dígitos com 11 ou 14 números.
  const runs = (text.match(/\d[\d.\-/\s]*\d/g) || []).map((s) => s.replace(/\D/g, ''));
  const found = runs.find((d) => d.length === 11 || d.length === 14);
  if (found) return { type: found.length === 11 ? 'cpf' : 'cnpj', ref: found, valid: true };

  return { type: null, ref: null, valid: false };
}

/** Máscara para logs/diagnostics — NUNCA expor o documento completo. */
export function maskDocument(ref: string | null | undefined): string {
  const digits = (ref || '').replace(/\D/g, '');
  if (digits.length < 4) return '***';
  return `***${digits.slice(-2)} (len=${digits.length})`;
}

// Mensagens curtas, humanas, com motivo claro — sem termos internos.
export const IDENTITY_QUESTION =
  'Perfeito. Para eu localizar sua apólice antes de confirmar qualquer cobertura, pode me enviar o CPF do segurado?';

export const IDENTITY_CLARIFY =
  'Não consegui identificar o CPF. Pode me enviar só os números do CPF do segurado (11 dígitos)?';

export const IDENTITY_NEXT_STEP = 'Aguardar o CPF/CNPJ do segurado para localizar a apólice.';

export const POLICY_LOOKUP_MESSAGE =
  'Obrigado. Vou usar esse dado para localizar a apólice em fonte segura antes de confirmar cobertura ou seguir com acionamento.';

export const POLICY_NEXT_STEP =
  'Consultar apólice/cobertura em fonte confiável (InfoCap) — o lookup será implementado no próximo batch. Não confirmar cobertura nem acionar até a verificação.';
