// SPEC-131-B · G1 — o ícone linear de cada aplicativo, de cada categoria e de cada conexão (laudo de design §2.4).
//
// O NOME mora no banco (`auxiliary_templates.icon`) e em `lib/auxiliaries/catalog.ts` (APLICATIVO_VISUAL,
// CATEGORIAS) — que não pode importar lucide (o catálogo é lido por testes sem bundler e pelo servidor). Aqui o nome
// vira o componente. Um nome que não está aqui cai no ícone padrão: nunca um buraco no card.
//
// ⚠️ O laudo pedia estes ícones em `lib/icons.ts`; aquele arquivo não é desta fatia (um dono por arquivo). O mapa
// mora junto da casca, que é o único lugar que os desenha; a mudança para `lib/icons.ts` é uma linha de import.

import type { LucideIcon } from 'lucide-react';
import {
  BadgePercent,
  BookOpenCheck,
  Building2,
  CalendarClock,
  Calculator,
  ChartNoAxesCombined,
  Clock,
  Coins,
  Database,
  FileText,
  FolderCheck,
  HandCoins,
  HardDrive,
  HeartHandshake,
  LayoutGrid,
  MessageCircle,
  MessageSquareReply,
  Plug,
  Radar,
  ReceiptText,
  RefreshCcwDot,
  Scale,
  ScanText,
  ScrollText,
  ShieldCheck,
  Sunrise,
  TrendingUp,
  Umbrella,
  UserRoundCheck,
  UserSearch,
} from 'lucide-react';

export const ICONE_DO_APLICATIVO: Record<string, LucideIcon> = {
  BadgePercent,
  BookOpenCheck,
  CalendarClock,
  Calculator,
  ChartNoAxesCombined,
  Clock,
  Coins,
  FolderCheck,
  HandCoins,
  HeartHandshake,
  LayoutGrid,
  MessageSquareReply,
  Radar,
  ReceiptText,
  RefreshCcwDot,
  Scale,
  ScanText,
  ScrollText,
  ShieldCheck,
  Sunrise,
  TrendingUp,
  Umbrella,
  UserRoundCheck,
  UserSearch,
};

export function iconeDoAplicativo(nome: string | null | undefined): LucideIcon {
  return (nome && ICONE_DO_APLICATIVO[nome]) || LayoutGrid;
}

/** Conexões: InfoCap `Database` · Portal `Building2` · WhatsApp `MessageCircle` · Agger `Calculator` (laudo §2.4). */
const ICONE_DA_CONEXAO: Record<string, LucideIcon> = {
  infocap: Database,
  quiver: Database,
  insurance_portal: Building2,
  portal_browser: Building2,
  whatsapp_zapi: MessageCircle,
  agger: Calculator,
  google_drive: HardDrive,
  notion: FileText,
};

export function iconeDaConexao(slug: string): LucideIcon {
  return ICONE_DA_CONEXAO[slug] ?? Plug;
}
