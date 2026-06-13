// Rótulos/tons compartilhados da UI de Atendimento. Puro, sem PII, sem I/O.
import type { StatusTone } from '@/components/patterns';

export const SUBCORRIDOR_LABEL: Record<string, string> = {
  electrician: 'Eletricista',
  plumber: 'Encanador',
  residential_locksmith: 'Chaveiro',
  unclogging: 'Desentupimento',
  home_appliances: 'Eletrodomésticos',
};

export function subcorridorLabel(key?: string | null): string | null {
  if (!key) return null;
  return SUBCORRIDOR_LABEL[key] || key;
}

export function priorityPill(p?: string | null): { tone: StatusTone; label: string } {
  switch (p) {
    case 'urgent':
      return { tone: 'danger', label: 'Prioridade urgente' };
    case 'high':
      return { tone: 'warning', label: 'Prioridade alta' };
    default:
      return { tone: 'neutral', label: `Prioridade ${p || 'normal'}` };
  }
}

export function verificationPill(v?: string | null): { tone: StatusTone; label: string } | null {
  if (!v) return null;
  if (v.startsWith('verified')) return { tone: 'success', label: 'Apólice verificada' };
  if (v === 'pending_human') return { tone: 'info', label: 'Apólice pendente' };
  if (v === 'not_applicable') return null;
  return { tone: 'warning', label: 'Apólice não verificada' };
}

export function riskTone(r?: string | null): StatusTone {
  if (r === 'critical' || r === 'high') return 'danger';
  if (r === 'medium') return 'warning';
  return 'neutral';
}

export function statusTone(status?: string | null): StatusTone {
  switch (status) {
    case 'closed':
      return 'success';
    case 'blocked':
    case 'cancelled':
      return 'danger';
    case 'handoff':
      return 'warning';
    case 'awaiting_approval':
    case 'action_prepared':
    case 'ready_for_dispatch':
      return 'info';
    default:
      return 'neutral';
  }
}

export function fmtDate(s?: string | null): string {
  if (!s) return '';
  const d = new Date(s);
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
}
