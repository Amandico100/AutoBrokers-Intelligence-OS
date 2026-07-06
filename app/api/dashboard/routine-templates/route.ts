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
    .select('id, name, description, category, instructions, schedule_default, delivery_default, required, is_active, sort_order')
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

  const items = (templates || []).map((t) => {
    const req = (t.required || {}) as Record<string, boolean>;
    const missing: { key: string; label: string; href?: string }[] = [];
    if (req.whatsapp && !hasWhatsapp) {
      missing.push({ key: 'whatsapp', label: 'Conectar WhatsApp', href: '/dashboard/personalizacao/conectores' });
    }
    // Portais ainda não estão disponíveis (SPEC-020) — informativo, não bloqueia.
    if (req.portal) {
      missing.push({ key: 'portal', label: 'Portais (em breve)' });
    }
    return { ...t, missing };
  });

  return NextResponse.json({ templates: items });
}
