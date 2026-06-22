// TA2-C — perfil da corretora (PURO, testável). Reusa colunas reais de `companies`.
// Sem tabela nova. Validação server-side; UF é dropdown; campos previsíveis controlados.

export const BR_UF = ['AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS','MG','PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO'];

export interface CompanyFieldSpec { key: string; label: string; input_kind: 'text' | 'select' | 'email' | 'cnpj'; options?: string[]; max_length: number; required?: boolean }

// Apenas colunas REAIS de companies (não expõe plano/flags/créditos/técnico).
export const COMPANY_PROFILE_FIELDS: CompanyFieldSpec[] = [
  { key: 'company_name', label: 'Nome da corretora', input_kind: 'text', max_length: 120, required: true },
  { key: 'legal_name', label: 'Razão social', input_kind: 'text', max_length: 160 },
  { key: 'cnpj', label: 'CNPJ', input_kind: 'cnpj', max_length: 18 },
  { key: 'primary_contact_name', label: 'Responsável operacional', input_kind: 'text', max_length: 120 },
  { key: 'primary_contact_email', label: 'E-mail de contato', input_kind: 'email', max_length: 160 },
  { key: 'primary_contact_phone', label: 'Telefone de contato', input_kind: 'text', max_length: 40 },
  { key: 'cep', label: 'CEP', input_kind: 'text', max_length: 12 },
  { key: 'street', label: 'Endereço', input_kind: 'text', max_length: 160 },
  { key: 'number', label: 'Número', input_kind: 'text', max_length: 20 },
  { key: 'complement', label: 'Complemento', input_kind: 'text', max_length: 80 },
  { key: 'neighborhood', label: 'Bairro', input_kind: 'text', max_length: 80 },
  { key: 'city', label: 'Cidade', input_kind: 'text', max_length: 80 },
  { key: 'state', label: 'UF', input_kind: 'select', options: BR_UF, max_length: 2 },
];

const CONTROL_CHARS = new RegExp('[\\u0000-\\u0008\\u000B\\u000C\\u000E-\\u001F\\u007F]', 'g');

export function onlyDigits(s: string): string { return (s || '').replace(/\D/g, ''); }

/** Validação real de CNPJ (14 dígitos + dígitos verificadores). */
export function isValidCNPJ(raw: string): boolean {
  const c = onlyDigits(raw);
  if (c.length !== 14 || /^(\d)\1{13}$/.test(c)) return false;
  const calc = (len: number) => {
    let sum = 0; let pos = len - 7;
    for (let i = len; i >= 1; i--) { sum += Number(c[len - i]) * pos--; if (pos < 2) pos = 9; }
    const r = sum % 11; return r < 2 ? 0 : 11 - r;
  };
  return calc(12) === Number(c[12]) && calc(13) === Number(c[13]);
}
export function isValidEmail(s: string): boolean { return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(s); }
export function isValidPhoneBR(s: string): boolean { const d = onlyDigits(s); return d.length >= 10 && d.length <= 13; }

export interface ProfileValidation { ok: boolean; errors: string[]; clean: Record<string, string> }

/** Sanitiza + valida apenas os campos permitidos (ignora qualquer outro). */
export function validateCompanyProfile(input: Record<string, unknown>): ProfileValidation {
  const errors: string[] = [];
  const clean: Record<string, string> = {};
  for (const f of COMPANY_PROFILE_FIELDS) {
    if (!(f.key in input)) continue;
    const raw = input[f.key];
    if (raw == null) { clean[f.key] = ''; continue; }
    if (typeof raw !== 'string') { errors.push(`${f.key}:tipo_invalido`); continue; }
    let v = raw.replace(CONTROL_CHARS, '').trim();
    if (v.length > f.max_length) { errors.push(`${f.key}:tamanho_maximo`); continue; }
    if (v === '') { if (f.required) errors.push(`${f.key}:obrigatorio`); else clean[f.key] = ''; continue; }
    if (f.input_kind === 'select' && f.options && !f.options.includes(v)) { errors.push(`${f.key}:opcao_invalida`); continue; }
    if (f.input_kind === 'email' && !isValidEmail(v)) { errors.push(`${f.key}:email_invalido`); continue; }
    if (f.input_kind === 'cnpj') { if (!isValidCNPJ(v)) { errors.push('cnpj:invalido'); continue; } v = onlyDigits(v); }
    if (f.key === 'primary_contact_phone' && !isValidPhoneBR(v)) { errors.push('primary_contact_phone:invalido'); continue; }
    clean[f.key] = v;
  }
  return { ok: errors.length === 0, errors, clean };
}
