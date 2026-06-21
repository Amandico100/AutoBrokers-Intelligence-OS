// Dados Globais — contatos oficiais de sinistro/assistência das seguradoras.
// SELF-CONTAINED. GLOBAIS e ATIVOS: o mesmo número vale para TODAS as corretoras
// (o segurado não muda). A corretora pode sobrescrever por tenant no futuro.
//
// Fonte: docs/intake/sinistro e assistencias - contatos.xlsx (intake oficial 2026-06).
// `raw` é o valor AUTORITATIVO da planilha (preserva opções de URA/menu).
// O número principal (sem menu) é derivado em insurer-contacts-registry (parsePrimaryNumber).
// Sufixos como "- 1-1-2" são opções de menu/URA (registradas, não usadas como número).
// NÃO são segredos: são linhas públicas de assistência/sinistro das seguradoras.

export interface InsurerContactSeed {
  insurer_key: string;
  display_name: string;
  // valores RAW da planilha (autoritativos)
  sinistro_auto: string | null;
  sinistro_re: string | null;
  assistencia_whatsapp: string | null; // canal WhatsApp da assistência
  assistencia_24h_auto: string | null;
  assistencia_24h_re: string | null;
  vidros: string | null;
  // LINK VIDROS = portal do PRESTADOR de vidros (frequentemente compartilhado entre seguradoras).
  glass_service_portal_url: string | null;
  notes: string | null;
}

export const INSURER_CONTACTS_SOURCE = 'autobrokers_intake_2026_06' as const;

export const INSURER_CONTACTS_GLOBAL_SEED: InsurerContactSeed[] = [
  { insurer_key: 'allianz', display_name: 'Allianz', sinistro_auto: '40901110 - 1-1-2', sinistro_re: '40901110-1-2-', assistencia_whatsapp: '11 4090-1444', assistencia_24h_auto: '08000130700', assistencia_24h_re: '08000177178', vidros: '08007011170', glass_service_portal_url: 'https://abraseuatendimento.com.br/#/', notes: null },
  { insurer_key: 'alfa', display_name: 'Alfa', sinistro_auto: '40032532 - 1-3', sinistro_re: '40032532-2-3', assistencia_whatsapp: '11 4393-1567', assistencia_24h_auto: '40032532 - 1', assistencia_24h_re: '40032532 -2-1', vidros: '40032532-1-2', glass_service_portal_url: 'https://abraseuatendimento.com.br/#/', notes: null },
  { insurer_key: 'azul', display_name: 'Azul', sinistro_auto: '08007030203 - cpf + 2', sinistro_re: '08007030203 cpf +3', assistencia_whatsapp: '21 3906-2985', assistencia_24h_auto: '08007030203', assistencia_24h_re: '08007030203', vidros: '08007030203', glass_service_portal_url: 'https://abraseuatendimento.com.br/#/', notes: null },
  { insurer_key: 'bradesco', display_name: 'Bradesco', sinistro_auto: '40042757 - 2-3', sinistro_re: '40042757 - 3-2', assistencia_whatsapp: '11 3003-1022', assistencia_24h_auto: '40042757-2-1', assistencia_24h_re: '40042757-3', vidros: '08007044441', glass_service_portal_url: 'https://www.agendeseuservico.com/', notes: null },
  { insurer_key: 'hdi', display_name: 'HDI', sinistro_auto: '30035390 - 2', sinistro_re: '30035390 - 2', assistencia_whatsapp: '08007754035', assistencia_24h_auto: '30035391-1-1', assistencia_24h_re: '30035390 -1-3', vidros: '08007773313', glass_service_portal_url: 'https://abraseuatendimento.com.br/#/', notes: null },
  { insurer_key: 'itau', display_name: 'Itaú', sinistro_auto: '08007270800 - 1 - 4', sinistro_re: '08007270800 -1 - 4', assistencia_whatsapp: '11 3003-9303', assistencia_24h_auto: '08007270800 -2', assistencia_24h_re: '08007270800 -2', vidros: '08007270800-1-4', glass_service_portal_url: 'https://abraseuatendimento.com.br/#/', notes: null },
  { insurer_key: 'mapfre', display_name: 'Mapfre', sinistro_auto: '08007754545', sinistro_re: '08007754545', assistencia_whatsapp: '11 4004-0101', assistencia_24h_auto: '08007754545', assistencia_24h_re: '08007754545-0', vidros: '08007754545', glass_service_portal_url: 'https://abraseuatendimento.com.br/#/', notes: 'Segurado digita o CPF e o sistema busca as opções de serviços.' },
  { insurer_key: 'porto', display_name: 'Porto', sinistro_auto: '08007270800-4', sinistro_re: '08007270800-4', assistencia_whatsapp: '11 3003-9303', assistencia_24h_auto: '08007270800-1', assistencia_24h_re: '08007270800-2', vidros: '08007270800', glass_service_portal_url: 'https://abraseuatendimento.com.br/#/', notes: 'Segurado digita o CPF e o sistema busca as opções de serviços.' },
  { insurer_key: 'tokio', display_name: 'Tokio Marine', sinistro_auto: '08003186546-4', sinistro_re: '08003186546-4', assistencia_whatsapp: '11 95302-2395', assistencia_24h_auto: '08003186546-1', assistencia_24h_re: '08003186546-2', vidros: '08007078005', glass_service_portal_url: 'https://abraseuatendimento.com.br/#/', notes: null },
  { insurer_key: 'yelum', display_name: 'Yelum', sinistro_auto: '40045423-2', sinistro_re: '40045423-2', assistencia_whatsapp: '11 3132-1001', assistencia_24h_auto: '40045423-1-1', assistencia_24h_re: '40045423-1-3', vidros: '08007014120', glass_service_portal_url: 'https://abraseuatendimento.com.br/#/', notes: null },
  { insurer_key: 'youse', display_name: 'Youse', sinistro_auto: '30035770', sinistro_re: '30035770', assistencia_whatsapp: null, assistencia_24h_auto: '30035770', assistencia_24h_re: '30035770', vidros: '30035770', glass_service_portal_url: 'https://abraseuatendimento.com.br/#/', notes: 'Um número para tudo, sem opções na URA. Sem WhatsApp de assistência ("não tem").' },
  { insurer_key: 'zurich', display_name: 'Zurich', sinistro_auto: '40204848-1', sinistro_re: '40204848-5', assistencia_whatsapp: '11 2890-2121', assistencia_24h_auto: '08007291400', assistencia_24h_re: '40204848-2', vidros: '0800 025 6303', glass_service_portal_url: 'https://abraseuatendimento.com.br/#/', notes: null },
];

// --- Registry (puro, self-contained) ----------------------------------------

export type InsurerContactChannelKey =
  | 'sinistro_auto' | 'sinistro_re' | 'assistencia_whatsapp'
  | 'assistencia_24h_auto' | 'assistencia_24h_re' | 'vidros';

export interface ParsedNumber {
  raw: string | null;
  primary_digits: string | null; // número principal (sem menu/URA), só dígitos
  has_menu: boolean;             // havia opções de menu/URA no raw
  available: boolean;            // false quando "não tem"
}

/**
 * Extrai o número principal (sem opções de menu/URA). `raw` continua autoritativo.
 * Marcadores de menu: " - ", "cpf", "+". Compactos ("40042757-2-1") são aparados
 * por comprimento conhecido (0800/0300=11; 40xx/30xx=8). WhatsApp "11 4090-1444"
 * é preservado (o "-1444" faz parte do número, não é menu).
 */
export function parsePrimaryNumber(raw: string | null | undefined): ParsedNumber {
  if (!raw || /n[aã]o tem/i.test(raw)) return { raw: raw ?? null, primary_digits: null, has_menu: false, available: false };
  let s = String(raw).trim();
  let hadMarker = false;
  const mIdx = s.search(/\s-\s|cpf|\s\+/i);
  if (mIdx >= 0) { hadMarker = true; s = s.slice(0, mIdx); }
  let digits = s.replace(/\D/g, '');
  let trimmed = false;
  if (/^(40|30)\d{2}/.test(digits) && digits.length > 8) { digits = digits.slice(0, 8); trimmed = true; }
  else if (/^(0800|0300)/.test(digits) && digits.length > 11) { digits = digits.slice(0, 11); trimmed = true; }
  return { raw, primary_digits: digits || null, has_menu: hadMarker || trimmed, available: Boolean(digits) };
}

export function normalizeInsurerKey(name: string | null | undefined): string | null {
  if (!name) return null;
  const k = String(name).normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();
  return k || null;
}

export interface ResolvedInsurerChannel { channel: InsurerContactChannelKey; kind: 'whatsapp' | 'phone'; raw: string | null; primary_digits: string | null; has_menu: boolean; available: boolean; }
export interface ResolvedInsurerContact {
  insurer_key: string;
  display_name: string;
  scope: 'global';
  is_active: true;
  source: typeof INSURER_CONTACTS_SOURCE;
  channels: ResolvedInsurerChannel[];
  glass_service_portal_url: string | null;
  notes: string | null;
}

const CHANNEL_KINDS: Record<InsurerContactChannelKey, 'whatsapp' | 'phone'> = {
  sinistro_auto: 'phone', sinistro_re: 'phone', assistencia_whatsapp: 'whatsapp',
  assistencia_24h_auto: 'phone', assistencia_24h_re: 'phone', vidros: 'phone',
};

function resolveSeed(s: InsurerContactSeed): ResolvedInsurerContact {
  const channels: ResolvedInsurerChannel[] = (Object.keys(CHANNEL_KINDS) as InsurerContactChannelKey[]).map((ch) => {
    const p = parsePrimaryNumber((s as any)[ch]);
    return { channel: ch, kind: CHANNEL_KINDS[ch], raw: p.raw, primary_digits: p.primary_digits, has_menu: p.has_menu, available: p.available };
  });
  return { insurer_key: s.insurer_key, display_name: s.display_name, scope: 'global', is_active: true, source: INSURER_CONTACTS_SOURCE, channels, glass_service_portal_url: s.glass_service_portal_url, notes: s.notes };
}

export function getInsurerContactsGlobal(): ResolvedInsurerContact[] {
  return INSURER_CONTACTS_GLOBAL_SEED.map(resolveSeed);
}

export function getInsurerContact(insurerKey: string | null | undefined): ResolvedInsurerContact | null {
  const k = normalizeInsurerKey(insurerKey);
  if (!k) return null;
  const s = INSURER_CONTACTS_GLOBAL_SEED.find((x) => x.insurer_key === k);
  return s ? resolveSeed(s) : null;
}

export type DispatchServiceType = 'residential_assistance' | 'auto_assistance' | 'sinistro_auto' | 'sinistro_re' | 'vidros' | 'electrician';

/**
 * Resolve o destino GLOBAL de acionamento por seguradora + tipo de serviço.
 * Residencial/eletricista → WhatsApp da assistência (fallback assistência 24h RE).
 */
export function resolveInsurerDispatchTarget(
  insurerKey: string | null | undefined,
  serviceType: DispatchServiceType,
  tenantOverride?: ResolvedInsurerChannel | null,
): { ok: boolean; insurer_key: string | null; channel: InsurerContactChannelKey | null; kind: 'whatsapp' | 'phone' | null; primary_digits: string | null; raw: string | null; source: 'tenant_override' | 'global' | 'none'; reason: string } {
  if (tenantOverride && tenantOverride.available) {
    return { ok: true, insurer_key: normalizeInsurerKey(insurerKey), channel: tenantOverride.channel, kind: tenantOverride.kind, primary_digits: tenantOverride.primary_digits, raw: tenantOverride.raw, source: 'tenant_override', reason: 'tenant_override' };
  }
  const contact = getInsurerContact(insurerKey);
  if (!contact) return { ok: false, insurer_key: normalizeInsurerKey(insurerKey), channel: null, kind: null, primary_digits: null, raw: null, source: 'none', reason: 'insurer_not_found' };

  const order: Record<DispatchServiceType, InsurerContactChannelKey[]> = {
    residential_assistance: ['assistencia_whatsapp', 'assistencia_24h_re'],
    electrician: ['assistencia_whatsapp', 'assistencia_24h_re'],
    auto_assistance: ['assistencia_24h_auto', 'assistencia_whatsapp'],
    sinistro_auto: ['sinistro_auto'],
    sinistro_re: ['sinistro_re'],
    vidros: ['vidros'],
  };
  for (const chKey of order[serviceType]) {
    const ch = contact.channels.find((c) => c.channel === chKey && c.available);
    if (ch) return { ok: true, insurer_key: contact.insurer_key, channel: ch.channel, kind: ch.kind, primary_digits: ch.primary_digits, raw: ch.raw, source: 'global', reason: 'global_default' };
  }
  return { ok: false, insurer_key: contact.insurer_key, channel: null, kind: null, primary_digits: null, raw: null, source: 'none', reason: 'no_channel_for_service' };
}

/** Agrupa seguradoras por portal de prestador (ex.: abraseuatendimento serve várias). */
export function getSharedServiceProviderPortals(): Array<{ portal_url: string; insurers: string[]; shared: boolean }> {
  const map = new Map<string, string[]>();
  for (const s of INSURER_CONTACTS_GLOBAL_SEED) {
    if (!s.glass_service_portal_url) continue;
    const arr = map.get(s.glass_service_portal_url) ?? [];
    arr.push(s.insurer_key);
    map.set(s.glass_service_portal_url, arr);
  }
  return Array.from(map.entries()).map(([portal_url, insurers]) => ({ portal_url, insurers, shared: insurers.length > 1 }));
}
