// Helpers de apresentação do Vault (pills, ícones, datas). Pure functions, client-safe.
import type { LucideIcon } from 'lucide-react';

import { icons } from '@/lib/icons';
import type { StatusTone } from '@/components/patterns';

export function riskPill(risk?: string): { tone: StatusTone; label: string } {
  switch (risk) {
    case 'low':
      return { tone: 'success', label: 'Risco baixo' };
    case 'medium':
      return { tone: 'info', label: 'Risco médio' };
    case 'high':
      return { tone: 'warning', label: 'Risco alto' };
    case 'critical':
      return { tone: 'danger', label: 'Risco crítico' };
    default:
      return { tone: 'neutral', label: risk || '—' };
  }
}

export function connectionStatusPill(status?: string): { tone: StatusTone; label: string } {
  switch (status) {
    case 'connected':
      return { tone: 'success', label: 'Conectado' };
    case 'draft':
      return { tone: 'neutral', label: 'Rascunho' };
    case 'configuring':
      return { tone: 'info', label: 'Configurando' };
    case 'error':
    case 'blocked':
      return { tone: 'danger', label: status === 'error' ? 'Com erro' : 'Bloqueado' };
    case 'disconnected':
      return { tone: 'neutral', label: 'Desconectado' };
    case 'revoked':
      return { tone: 'warning', label: 'Revogado' };
    default:
      return { tone: 'neutral', label: status || '—' };
  }
}

export function approvalStatusPill(status?: string): { tone: StatusTone; label: string } {
  switch (status) {
    case 'pending':
      return { tone: 'info', label: 'Pendente' };
    case 'approved':
      return { tone: 'success', label: 'Aprovado' };
    case 'rejected':
      return { tone: 'danger', label: 'Rejeitado' };
    case 'executed':
      return { tone: 'success', label: 'Executado' };
    case 'failed':
      return { tone: 'danger', label: 'Falhou' };
    case 'expired':
      return { tone: 'neutral', label: 'Expirado' };
    case 'cancelled':
      return { tone: 'neutral', label: 'Cancelado' };
    default:
      return { tone: 'neutral', label: status || '—' };
  }
}

const SLUG_ICONS: Record<string, LucideIcon> = {
  whatsapp_zapi: icons.whatsapp,
  google_drive: icons.drive,
  notion: icons.documento,
  infocap: icons.seguradoras,
  quiver: icons.seguradoras,
  insurance_portal: icons.seguradoras,
  internal_conversations: icons.conversas,
  internal_documents: icons.documento,
};

export function slugIcon(slug?: string): LucideIcon {
  return (slug && SLUG_ICONS[slug]) || icons.conectores;
}

export function fmtDateTime(s?: string | null): string {
  if (!s) return '';
  const d = new Date(s);
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleString('pt-BR');
}

// SPEC-014 C-FIX-1 (E): linguagem humana para AÇÕES e ATORES (corretor não vê termo técnico).
const ACTION_LABELS: Record<string, { label: string; help: string; sensitive: boolean }> = {
  read: { label: 'Consultar informações', help: 'Apenas ler dados (ex.: consultar apólice). Não altera nada.', sensitive: false },
  draft_message: { label: 'Preparar mensagem para revisão', help: 'Monta um rascunho para um humano revisar. Não envia sozinho.', sensitive: false },
  test_connection: { label: 'Testar conexão', help: 'Verifica se a conexão está funcionando.', sensitive: false },
  send_message: { label: 'Enviar mensagem', help: 'Envia de verdade (ex.: WhatsApp). Pede confirmação.', sensitive: true },
  write: { label: 'Criar ou alterar', help: 'Grava/edita dados no app (ex.: escrever no Notion). Pede confirmação.', sensitive: true },
  create_event: { label: 'Criar compromisso', help: 'Cria evento no calendário. Pede confirmação.', sensitive: true },
};
export function actionLabel(action: string): string {
  return ACTION_LABELS[action]?.label ?? action;
}
export function actionHelp(action: string): string {
  return ACTION_LABELS[action]?.help ?? '';
}
export function actionIsSensitive(action: string): boolean {
  return ACTION_LABELS[action]?.sensitive ?? false;
}

const SUBJECT_LABELS: Record<string, string> = {
  autobrokers: 'Chat Principal',
  atendimento: 'Atendimento (Even)',
  tenant_auxiliary: 'Auxiliares',
};
export function subjectLabel(subject: string): string {
  return SUBJECT_LABELS[subject] ?? subject;
}
