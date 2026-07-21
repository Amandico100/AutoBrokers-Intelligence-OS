// SPEC-036 Etapa 2 — upload de conhecimento PELA CORRETORA (dashboard).
// Mesma esteira do admin (backend /documents/upload), mas com o company_id
// travado na sessão do usuário — cada corretora só alimenta o próprio cofre.
import { NextRequest, NextResponse } from 'next/server';
import { requireCompanyMember } from '@/lib/admin/admin-auth';

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || process.env.BACKEND_URL || 'http://localhost:8000';

export const dynamic = 'force-dynamic';

export async function POST(req: NextRequest) {
  const auth = await requireCompanyMember({ write: true });
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });

  try {
    const incoming = await req.formData();
    const file = incoming.get('file');
    const agentId = String(incoming.get('agent_id') || '');
    if (!file || !agentId) {
      return NextResponse.json({ ok: false, error: 'Arquivo e agente são obrigatórios.' }, { status: 400 });
    }
    const fd = new FormData();
    fd.set('file', file);
    fd.set('company_id', auth.ctx.companyId);
    fd.set('agent_id', agentId);
    // Linguagem do corretor: sem jargão — a estratégia fica automática (semântica).
    fd.set('strategy', 'semantic');
    // SPEC-044: destino do conhecimento — corretora (default) ou pessoal.
    // O DONO é sempre o usuário da sessão (nunca vem do formulário).
    if (String(incoming.get('target') || '') === 'personal') {
      fd.set('scope', 'personal');
      fd.set('owner_user_id', String(auth.ctx.userId || ''));
    }

    const res = await fetch(new URL('/documents/upload', BACKEND_URL), { method: 'POST', body: fd });
    const body = await res.text();
    return new NextResponse(body, { status: res.status, headers: { 'Content-Type': 'application/json' } });
  } catch (e) {
    return NextResponse.json({ ok: false, error: 'Falha ao enviar o documento.' }, { status: 502 });
  }
}

export async function GET() {
  // Agentes da corretora para o vínculo do documento (nome amigável).
  const auth = await requireCompanyMember({ write: false });
  if (!auth.ok) return NextResponse.json({ ok: false, error: auth.error }, { status: auth.status });
  const { data } = await auth.supabase
    .from('agents')
    .select('id, name')
    .eq('company_id', auth.ctx.companyId)
    .order('name');
  return NextResponse.json({ ok: true, agents: data || [] });
}
