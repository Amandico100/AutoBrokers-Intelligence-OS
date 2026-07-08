import { NextRequest, NextResponse } from 'next/server';

import { resolveSessionCompany, getSupabaseAdmin } from '@/lib/vault/server';

export const dynamic = 'force-dynamic';

/**
 * SPEC-019 C — Galeria de rotinas prontas (routine_templates).
 * GET → { templates: [{ ...template, missing: [{key,label,href?}] }] }
 * `missing` = dependencias que a corretora ainda precisa conectar para o
 * modelo funcionar (ex.: WhatsApp). "Usar modelo" pre-preenche a Nova rotina.
 */
export async function GET(_req: NextRequest) {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ error: 'Não autorizado' }, { status: 401 });
  const supabase = getSupabaseAdmin();

  const { data: templates, error } = await supabase
    .from('routine_templates')
    .select('id, name, description, category, instructions, schedule_default, delivery_default, required, config_default, is_active, sort_order')
    .eq('is_active', true)
    .order('sort_order', { ascending: true });
  if (error) {
    console.error('[ROUTINE-TEMPLATES] list error:', error.message);
    return NextResponse.json(
      { error: 'Erro ao listar modelos (a migration routine_templates já foi aplicada?)' },
      { status: 500 },
    );
  }

  // Capacidades da corretora: o que "falta" para cada modelo rodar de verdade.
  const { data: integ } = await supabase
    .from('integrations')
    .select('id')
    .eq('company_id', ctx.companyId)
    .eq('is_active', true)
    .limit(1);
  const hasWhatsapp = !!(integ && integ.length);
  const { data: portalAccounts } = await supabase
    .from('portal_accounts')
    .select('portal_key, secret_encrypted, health')
    .eq('company_id', ctx.companyId);
  const connectedPortals = new Set(
    (portalAccounts || [])
      .filter((p) => !!p.secret_encrypted)
      .map((p) => String(p.portal_key || '')),
  );

  let hasInfocap = false;
  try {
    const { data: tpl } = await supabase
      .from('connector_templates')
      .select('id')
      .eq('slug', 'infocap')
      .eq('is_active', true)
      .maybeSingle();
    if (tpl?.id) {
      const { data: conns } = await supabase
        .from('tenant_connections')
        .select('id, status, encrypted_secret_ref')
        .eq('company_id', ctx.companyId)
        .eq('connector_template_id', tpl.id)
        .in('status', ['connected', 'configuring'])
        .limit(1);
      hasInfocap = !!(conns && conns.length && conns[0].encrypted_secret_ref);
    }
  } catch {
    hasInfocap = false;
  }

  const items = (templates || []).map((t) => {
    const req = (t.required || {}) as Record<string, boolean>;
    const cfg = (t.config_default || {}) as { portal_keys?: string[] };
    const missing: { key: string; label: string; href?: string }[] = [];
    if (req.whatsapp && !hasWhatsapp) {
      missing.push({ key: 'whatsapp', label: 'Conectar WhatsApp', href: '/dashboard/personalizacao/conectores' });
    }
    // SPEC-023: portal requerido olha credenciais reais conectadas.
    if (req.portal) {
      const needed = Array.isArray(cfg.portal_keys) && cfg.portal_keys.length ? cfg.portal_keys : ['allianz_corretor'];
      const ok = needed.some((key) => connectedPortals.has(key));
      if (!ok) {
        missing.push({ key: 'portal', label: 'Conectar portal da seguradora', href: '/dashboard/personalizacao/conectores/portais' });
      }
    }
    if (req.infocap && !hasInfocap) {
      missing.push({ key: 'infocap', label: 'Conectar sistema de gestão', href: '/dashboard/personalizacao/conectores' });
    }
    return { ...t, missing };
  });

  return NextResponse.json({ templates: items });
}
