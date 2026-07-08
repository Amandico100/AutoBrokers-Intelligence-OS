import { NextRequest, NextResponse } from 'next/server';

import { resolveSessionCompany, getSupabaseAdmin } from '@/lib/vault/server';
import { assertSameOrigin } from '@/lib/admin/admin-auth';
import { buildPortalJobRetryPatch, isRetryableHitlJob, sanitizePortalJob } from '@/lib/portal/hitl';

export const dynamic = 'force-dynamic';

const JOB_SELECT = 'id, company_id, portal_key, journey, status, evidence, screenshots, attempts, created_at, started_at, finished_at, error';

async function portalNameMap(supabase: ReturnType<typeof getSupabaseAdmin>, keys: string[]) {
  if (!keys.length) return {};
  const { data } = await supabase.from('portals').select('key, name').in('key', keys);
  const out: Record<string, string> = {};
  for (const row of data || []) out[String(row.key)] = String(row.name || row.key);
  return out;
}

export async function GET(req: NextRequest) {
  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ error: 'Nao autorizado' }, { status: 401 });
  const supabase = getSupabaseAdmin();
  const status = req.nextUrl.searchParams.get('status') || 'needs_human';
  const limit = Math.min(Math.max(Number(req.nextUrl.searchParams.get('limit') || 20), 1), 50);

  let q = supabase
    .from('portal_jobs')
    .select(JOB_SELECT)
    .eq('company_id', ctx.companyId)
    .order('created_at', { ascending: false })
    .limit(limit);
  if (status !== 'all') q = q.eq('status', status);

  const { data, error } = await q;
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });

  const rows = (data || []) as any[];
  const keys: string[] = [];
  const seen: Record<string, true> = {};
  for (const row of rows) {
    const key = String(row.portal_key || '');
    if (key && !seen[key]) {
      seen[key] = true;
      keys.push(key);
    }
  }
  const names = await portalNameMap(supabase, keys);
  return NextResponse.json({ jobs: rows.map((row) => sanitizePortalJob(row, names)) });
}

export async function POST(req: NextRequest) {
  const sameOrigin = assertSameOrigin(req);
  if (sameOrigin) return NextResponse.json({ error: sameOrigin.error }, { status: sameOrigin.status });

  const ctx = await resolveSessionCompany();
  if (!ctx) return NextResponse.json({ error: 'Nao autorizado' }, { status: 401 });
  const supabase = getSupabaseAdmin();
  const body = await req.json().catch(() => ({}));
  const action = String(body.action || '');
  const jobId = String(body.job_id || '');
  if (action !== 'retry' || !jobId) {
    return NextResponse.json({ error: 'action=retry e job_id sao obrigatorios' }, { status: 400 });
  }

  const { data: row, error: readError } = await supabase
    .from('portal_jobs')
    .select(JOB_SELECT)
    .eq('id', jobId)
    .eq('company_id', ctx.companyId)
    .maybeSingle();
  if (readError) return NextResponse.json({ error: readError.message }, { status: 500 });
  if (!row) return NextResponse.json({ error: 'job_not_found' }, { status: 404 });
  if (!isRetryableHitlJob(row, ctx.companyId)) {
    return NextResponse.json({ error: 'job_not_retryable' }, { status: 409 });
  }

  const patch = buildPortalJobRetryPatch(new Date().toISOString(), row.evidence || {});
  const { error: updateError } = await supabase
    .from('portal_jobs')
    .update(patch)
    .eq('id', jobId)
    .eq('company_id', ctx.companyId)
    .eq('status', 'needs_human');
  if (updateError) return NextResponse.json({ error: updateError.message }, { status: 500 });
  return NextResponse.json({ ok: true });
}
