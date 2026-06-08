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
