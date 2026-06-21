// TA2-A — espelho (read-only) da Effective Configuration de uma empresa para o
// Portal Admin (master). MESMA fonte canônica do Dashboard (sem duplicar dados).
import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { createClient } from '@supabase/supabase-js';
import { getTenantAgentConfig } from '@/lib/admin/tenant-agent-store';

export const dynamic = 'force-dynamic';

export async function GET(_req: NextRequest, { params }: { params: Promise<{ companyId: string }> }) {
  const cookieStore = await cookies();
  if (!cookieStore.get('smith_admin_session')) return NextResponse.json({ ok: false, error: 'Unauthorized' }, { status: 401 });
  const { companyId } = await params;
  if (!companyId) return NextResponse.json({ ok: false, error: 'companyId_required' }, { status: 400 });

  const supabase = createClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.SUPABASE_SERVICE_ROLE_KEY!, { auth: { persistSession: false } });
  const core = await getTenantAgentConfig(supabase, companyId, 'core');
  const attendance = await getTenantAgentConfig(supabase, companyId, 'attendance');
  return NextResponse.json({ ok: true, company_id: companyId, core, attendance, real_action_allowed: false });
}
