import {
  MessageCircle,
  Headphones,
  Workflow,
  Settings,
  Plug,
  Shield,
  Library,
  Users,
  Plus,
  Search,
  ArrowUp,
  ChevronRight,
  ChevronLeft,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Clock,
  ShieldCheck,
  AlertCircle,
  Mail,
  FileText,
  RefreshCw,
  Filter,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

/**
 * Mapa lógico de ícones do produto (base: lucide-react).
 * Use sempre via `@/components/ui/Icon` para padronizar traço/tamanho.
 * Novos ícones entram AQUI, nunca soltos no JSX.
 */
export const icons = {
  // Pilares de navegação
  autobrokers: MessageCircle,
  atendimentos: Headphones,
  auxiliares: Workflow,
  personalizacao: Settings,

  // Áreas internas
  conectores: Plug,
  seguradoras: Shield,
  conhecimento: Library,
  equipe: Users,

  // Ações de chat / navegação
  novaConversa: Plus,
  buscar: Search,
  enviar: ArrowUp,
  avancar: ChevronRight,
  voltar: ChevronLeft,

  // Status (ver §3 do HANDOFF-001)
  success: CheckCircle,
  warning: AlertTriangle,
  danger: XCircle,
  pendente: Clock,
  aprovacao: ShieldCheck,
  alerta: AlertCircle,

  // Domínio / conectores comuns
  whatsapp: MessageCircle, // lucide não tem marca WhatsApp; design usa message-circle
  email: Mail,
  documento: FileText,
  renovacao: RefreshCw,
  filtros: Filter,
} satisfies Record<string, LucideIcon>;

export type IconName = keyof typeof icons;
