// SPEC-013 Fase B P4 — classificação da empresa (para a UI distinguir Studio/Knowledge de cliente).
import { NextRequest, NextResponse } from 'next/server';
import { requireAdminForCompany, supabaseService } from '@/lib/admin/admin-auth';
import { getCompanyKind } from '@/lib/admin/company-kind-store';

export const dynamic = 'force-dynamic';

export async function GET(_req: NextRequest, { params }: { params: Promise<{ companyId: string }> }) {
  const { companyId } = await params;
  if (!companyId) return NextResponse.json({ ok: false, error: 'companyId_required' }, { status: 400 });
  const auth = await requireAdminForCompany(companyId);
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });
  const company_kind = await getCompanyKind(supabaseService(), companyId);
  return NextResponse.json({ ok: true, company_id: companyId, company_kind });
}
