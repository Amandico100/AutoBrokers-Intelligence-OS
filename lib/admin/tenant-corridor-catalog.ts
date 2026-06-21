// TA2-B — montagem PURA do catálogo de corredores (testável, sem I/O).
// Regra de composição: GLOBAL disponível ≠ TENANT instalado/ativo. O template é
// o catálogo; tenant_corridors é o estado por corretora. Não copia o template.

export interface CorridorTemplateRow {
  id: string;
  scope: string | null;
  corridor_key: string | null;
  subcorridor_key: string | null;
  display_name: string | null;
  insurer_key: string | null;
  line_kind: string | null;
  macro_service: string | null;
  service_type: string | null;
  readiness: string | null;
  requires_action_engine: boolean | null;
  requires_dispatch_packet: boolean | null;
  allowed_channels: unknown;
  is_active: boolean | null;
}
export interface TenantCorridorRow { corridor_template_id: string; status: string | null }

export type CorridorUiStatus = 'available' | 'active' | 'paused' | 'needs_channel' | 'needs_portal';

export interface CorridorCatalogItem {
  template_id: string;
  title: string;
  insurer_key: string | null;
  line_kind: string | null;
  macro_service: string | null;
  subcorridor_key: string | null;
  status: CorridorUiStatus;
  installed: boolean;
  requirements: string[];   // pré-requisitos legíveis
  next_step: string;        // próximo passo humano
}

function humanTitle(t: CorridorTemplateRow): string {
  if (t.display_name && t.display_name.trim()) return t.display_name.trim();
  const base = [t.insurer_key, t.line_kind, t.subcorridor_key].filter(Boolean).join(' — ');
  return base || t.corridor_key || 'Corredor';
}

function channelsArray(v: unknown): string[] {
  return Array.isArray(v) ? v.filter((x) => typeof x === 'string') as string[] : [];
}

/** Deriva requisitos legíveis a partir do template (sem expor campos técnicos). */
export function corridorRequirements(t: CorridorTemplateRow): string[] {
  const reqs: string[] = [];
  const channels = channelsArray(t.allowed_channels);
  if (channels.includes('whatsapp')) reqs.push('Canal WhatsApp conectado');
  if (channels.includes('portal') || t.service_type === 'portal') reqs.push('Portal da seguradora conectado');
  if (t.requires_action_engine) reqs.push('Ação externa requer aprovação');
  if (t.readiness && /portal/i.test(t.readiness)) reqs.push('Portal da seguradora conectado');
  return Array.from(new Set(reqs));
}

/** Constrói o catálogo unindo templates (catálogo) + ativações do tenant (estado). */
export function buildCorridorCatalog(templates: CorridorTemplateRow[], activations: TenantCorridorRow[]): CorridorCatalogItem[] {
  const byTemplate = new Map<string, string>(); // template_id -> status
  for (const a of activations) if (a.corridor_template_id) byTemplate.set(a.corridor_template_id, (a.status ?? 'active'));

  return templates
    .filter((t) => t.is_active !== false)
    .map((t) => {
      const act = byTemplate.get(t.id) ?? null;
      const installed = act !== null;
      const requirements = corridorRequirements(t);
      let status: CorridorUiStatus;
      let next_step: string;
      if (act === 'active') { status = 'active'; next_step = requirements.length ? 'Conclua os pré-requisitos para operar com segurança.' : 'Pronto para uso quando a Even estiver ativa.'; }
      else if (act === 'paused') { status = 'paused'; next_step = 'Retome o corredor quando quiser voltar a usá-lo.'; }
      else { status = 'available'; next_step = 'Ative este corredor para disponibilizá-lo à corretora.'; }
      return {
        template_id: t.id,
        title: humanTitle(t),
        insurer_key: t.insurer_key ?? null,
        line_kind: t.line_kind ?? null,
        macro_service: t.macro_service ?? null,
        subcorridor_key: t.subcorridor_key ?? null,
        status, installed, requirements, next_step,
      };
    })
    .sort((a, b) => a.title.localeCompare(b.title));
}

/** Resolve o novo status a partir da ação do usuário (puro). */
export function nextCorridorStatus(action: string): 'active' | 'paused' | null {
  if (action === 'activate' || action === 'resume') return 'active';
  if (action === 'pause') return 'paused';
  return null;
}
