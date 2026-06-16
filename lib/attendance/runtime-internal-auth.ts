// Auth interna Next↔Backend para rotas de runtime de atendimento (42W1).
//
// Permite que o bridge de WhatsApp (server-to-server) acione as MESMAS rotas
// do dashboard sem sessão de usuário, usando a chave interna + company_id no
// body. O caminho de sessão (dashboard) NÃO muda; este é um branch ADITIVO.
import type { NextRequest } from 'next/server';

/**
 * Resolve company_id quando a chamada é interna (sem sessão): exige
 * X-AutoBrokers-Internal-Key válida + body.company_id. Retorna null se não
 * for uma chamada interna válida (o chamador deve então cair no fluxo de sessão).
 */
export function resolveInternalCompanyId(request: NextRequest, body: any): string | null {
  const internalKey = process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY;
  const providedKey = request.headers.get('x-autobrokers-internal-key');
  if (
    internalKey &&
    providedKey &&
    providedKey === internalKey &&
    body &&
    typeof body.company_id === 'string' &&
    body.company_id
  ) {
    return body.company_id;
  }
  return null;
}
