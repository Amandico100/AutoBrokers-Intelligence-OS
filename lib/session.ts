import { UserV2 } from './types';

const SESSION_KEY = 'smith_user_session';
const SESSION_EXPIRY_DAYS = 7;

export interface SessionData {
  userId: string;
  email: string;
  firstName: string;
  lastName: string;
  planId: string | null;
  status: string;
  companyId: string | null;
  companyStatus?: string | null;
  webhookUrl?: string | null;
  expiresAt: string;
}

export function createSession(
  user: UserV2,
  rememberMe: boolean = false,
  companyData?: { status: string; webhook_url: string } | null,
): SessionData {
  const expiryDays = rememberMe ? 30 : SESSION_EXPIRY_DAYS;
  const expiresAt = new Date(Date.now() + expiryDays * 24 * 60 * 60 * 1000).toISOString();

  const sessionData: SessionData = {
    userId: user.id,
    email: user.email,
    firstName: user.first_name,
    lastName: user.last_name,
    planId: user.plan_id,
    status: user.status || 'pending',
    companyId: user.company_id || null,
    companyStatus: companyData?.status || null,
    webhookUrl: companyData?.webhook_url || null,
    expiresAt,
  };

  if (typeof window !== 'undefined') {
    localStorage.setItem(SESSION_KEY, JSON.stringify(sessionData));
  }

  return sessionData;
}

export function getSession(): SessionData | null {
  if (typeof window === 'undefined') {
    return null;
  }

  const sessionStr = localStorage.getItem(SESSION_KEY);
  if (!sessionStr) {
    return null;
  }

  try {
    const session: SessionData = JSON.parse(sessionStr);

    if (new Date(session.expiresAt) < new Date()) {
      clearSession();
      return null;
    }

    return session;
  } catch {
    clearSession();
    return null;
  }
}

export function clearSession(): void {
  if (typeof window !== 'undefined') {
    localStorage.removeItem(SESSION_KEY);
  }
}

/**
 * 🔴 SPEC-098 · U4.c — TROCAR DE EMPRESA REESCREVE O QUE O NAVEGADOR GUARDA.
 *
 * 📊 Medido em 06/09/2026 (`lib/session.ts:33`): `companyId` é gravado no login
 * e vale 7 a 30 dias. Quem trocava de empresa no seletor via o servidor mudar
 * (a sessão do cookie passa a apontar para a nova) e o navegador continuar com
 * a ANTIGA guardada. Nenhuma tela reclamava: uma parte da tela falava por uma
 * corretora e a outra parte, pela outra — e a conta de qual estava certa era do
 * corretor.
 *
 * Passar `null` APAGA a chave inteira: sessão sem empresa é melhor que sessão
 * com a empresa errada.
 */
export function atualizarEmpresaNaSessaoLocal(companyId: string | null): void {
  if (typeof window === 'undefined') return;
  const sessionStr = localStorage.getItem(SESSION_KEY);
  if (!sessionStr) return;
  try {
    const session: SessionData = JSON.parse(sessionStr);
    if (companyId === null) {
      clearSession();
      return;
    }
    session.companyId = companyId;
    localStorage.setItem(SESSION_KEY, JSON.stringify(session));
  } catch {
    // Sessão ilegível é sessão que não serve para nada — some com ela.
    clearSession();
  }
}

export function isAuthenticated(): boolean {
  return getSession() !== null;
}

export function requireAuth(): SessionData {
  const session = getSession();
  if (!session) {
    if (typeof window !== 'undefined') {
      window.location.href = '/login';
    }
    throw new Error('Not authenticated');
  }
  return session;
}
