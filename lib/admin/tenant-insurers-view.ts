// TA2-B — visão de seguradoras para a corretora (PURO). Une os contatos globais
// (somente leitura) com o estado de corredores do tenant. A corretora NÃO edita
// contatos globais (catálogo curado da plataforma).
import type { ResolvedInsurerContact } from '@/lib/attendance/insurer-contacts-global-seed';
import type { CorridorCatalogItem } from '@/lib/admin/tenant-corridor-catalog';

const CHANNEL_LABEL: Record<string, string> = {
  assistencia_whatsapp: 'Assistência (WhatsApp)',
  assistencia_24h_auto: 'Assistência 24h — Auto',
  assistencia_24h_re: 'Assistência 24h — Residencial',
  sinistro_auto: 'Sinistro — Auto',
  sinistro_re: 'Sinistro — Residencial',
  vidros: 'Vidros',
};

export interface InsurerViewChannel { label: string; kind: 'whatsapp' | 'phone'; available: boolean; number: string | null }
export interface InsurerViewItem {
  insurer_key: string;
  display_name: string;
  active_corridors: number;
  has_active_corridor: boolean;
  channels: InsurerViewChannel[];
  glass_service_portal_url: string | null;
  notes: string | null;
}

export function buildInsurerView(contacts: ResolvedInsurerContact[], corridorItems: CorridorCatalogItem[]): InsurerViewItem[] {
  const activeByInsurer = new Map<string, number>();
  for (const it of corridorItems) {
    if (it.status === 'active' && it.insurer_key) activeByInsurer.set(it.insurer_key, (activeByInsurer.get(it.insurer_key) ?? 0) + 1);
  }
  return contacts.map((c) => {
    const active = activeByInsurer.get(c.insurer_key) ?? 0;
    return {
      insurer_key: c.insurer_key,
      display_name: c.display_name,
      active_corridors: active,
      has_active_corridor: active > 0,
      channels: c.channels
        .filter((ch) => ch.available)
        .map((ch) => ({ label: CHANNEL_LABEL[ch.channel] ?? ch.channel, kind: ch.kind, available: ch.available, number: ch.primary_digits })),
      glass_service_portal_url: c.glass_service_portal_url,
      notes: c.notes,
    };
  }).sort((a, b) => a.display_name.localeCompare(b.display_name));
}
