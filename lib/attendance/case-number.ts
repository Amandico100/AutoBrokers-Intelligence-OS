// Gera um case_number simples e único por empresa: ATD-YYYYMMDD-HHMMSS-XXXX.
// O índice único (company_id, case_number) garante unicidade no banco; aqui só
// produzimos um valor legível e suficientemente aleatório. Sem PII.
export function generateCaseNumber(date: Date = new Date()): string {
  const pad = (n: number, len = 2) => String(n).padStart(len, '0');
  const ymd = `${date.getFullYear()}${pad(date.getMonth() + 1)}${pad(date.getDate())}`;
  const hms = `${pad(date.getHours())}${pad(date.getMinutes())}${pad(date.getSeconds())}`;
  const rand = Math.floor(1000 + Math.random() * 9000); // 4 dígitos
  return `ATD-${ymd}-${hms}-${rand}`;
}
