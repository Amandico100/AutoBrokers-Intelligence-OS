// SEC-001 — PII & secret redaction. PURO, self-contained (sem imports
// cross-module em runtime). Usado para sanitizar logs/traces/relatórios/audit.
// NUNCA deixar passar CPF/CNPJ/telefone/email/token/senha/cookie/storageState/
// OTP/apikey/client_token/vault_ref/storage_ref/destination_ref/base64 grande.

// Chaves cujo VALOR é sempre segredo (redigir o valor inteiro).
export const SECRET_KEYS = [
  'password', 'senha', 'pass', 'pwd', 'token', 'client_token', 'access_token', 'refresh_token',
  'cookie', 'cookies', 'storage_state', 'storagestate', 'otp', 'mfa_code', 'code',
  'secret', 'apikey', 'api_key', 'authorization', 'bearer', 'private_key', 'certificate_pem',
  'vault_ref', 'storage_ref', 'destination_ref', 'encrypted_secret_ref',
];

const CPF = /\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b/g;
const CNPJ = /\b\d{2}\.?\d{3}\.?\d{3}\/?\d{4}-?\d{2}\b/g;
const EMAIL = /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/g;
const PHONE = /\b(?:\+?55\s?)?\(?\d{2}\)?\s?9?\d{4}[-\s]?\d{4}\b/g;
const LONG_DIGITS = /\d[\d.\-/\s]{9,}\d/g;
const OTP = /\b\d{4,8}\b/g;
const BIG_BASE64 = /\b[A-Za-z0-9+/]{40,}={0,2}\b/g;

/** Redige PII/segredos em uma string. PURO. */
export function redactPII(input: string | null | undefined): string {
  if (input == null) return '';
  let s = String(input);
  s = s.replace(CNPJ, '[cnpj]')
    .replace(CPF, '[cpf]')
    .replace(EMAIL, '[email]')
    .replace(PHONE, '[phone]')
    .replace(BIG_BASE64, '[blob]')
    .replace(LONG_DIGITS, '[num]')
    .replace(OTP, '[otp]');
  return s;
}

/** Redige profundamente: valores de chaves-segredo viram [redacted]; strings passam por redactPII. */
export function redactDeep(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(redactDeep);
  if (value && typeof value === 'object') {
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
      if (SECRET_KEYS.includes(k.toLowerCase())) { out[k] = '[redacted]'; continue; }
      out[k] = redactDeep(v);
    }
    return out;
  }
  if (typeof value === 'string') return redactPII(value);
  return value;
}

/** Detecta chaves-segredo presentes (recursivo). PURO. */
export function findSecretKeys(obj: unknown, path = ''): string[] {
  const hits: string[] = [];
  if (!obj || typeof obj !== 'object') return hits;
  for (const [k, v] of Object.entries(obj as Record<string, unknown>)) {
    if (SECRET_KEYS.includes(k.toLowerCase())) hits.push(path ? `${path}.${k}` : k);
    if (v && typeof v === 'object') hits.push(...findSecretKeys(v, path ? `${path}.${k}` : k));
  }
  return hits;
}

/** Detecta PII em qualquer string do objeto (após redação NÃO deve sobrar nada). */
export function hasPII(value: unknown): boolean {
  const raw = typeof value === 'string' ? value : JSON.stringify(value ?? '');
  return CPF.test(raw) || CNPJ.test(raw) || EMAIL.test(raw) || PHONE.test(raw)
    // reset lastIndex (regex global)
    || (CPF.lastIndex = CNPJ.lastIndex = EMAIL.lastIndex = PHONE.lastIndex = 0, false);
}
