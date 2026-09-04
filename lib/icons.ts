import {
  MessageCircle,
  Headphones,
  Workflow,
  Settings,
  SlidersHorizontal,
  History,
  LogOut,
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
  Check,
  X,
  Lock,
  Database,
  HardDrive,
  Receipt,
  Inbox,
  Briefcase,
  MessageSquare,
  Building2,
  LayoutGrid,
  Sunrise,
  CalendarDays,
  Activity,
  ScanSearch,
  Radar,
  Archive,
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
  personalizacao: SlidersHorizontal,

  // Áreas internas
  conectores: Plug,
  seguradoras: Shield,
  conhecimento: Library,
  equipe: Users,

  // Navegação secundária
  historico: History,
  configuracoes: Settings,
  sair: LogOut,

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

  // Padrões / permissões
  check: Check,
  negado: X,
  cadeado: Lock,
  banco: Database,
  drive: HardDrive,
  cobranca: Receipt,

  // Tipos de relatório (SPEC-095 A.2 — o mapa vive em lib/relatorios/tipos.ts,
  // que referencia estas chaves; o ícone em si mora aqui, como todos os outros)
  briefingDiario: Sunrise,
  resumoSemanal: CalendarDays,
  pulso: Activity,
  raioX: ScanSearch,
  radar: Radar,
  arquivado: Archive,

  // Módulos
  fila: Inbox,
  casos: Briefcase,
  conversas: MessageSquare,
  corretora: Building2,
  galeria: LayoutGrid,
} satisfies Record<string, LucideIcon>;

export type IconName = keyof typeof icons;
