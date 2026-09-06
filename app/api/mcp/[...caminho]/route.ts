/**
 * Proxy das conexões do agente (MCP) — /api/mcp/**
 *
 * 🔴 SPEC-098 · U4.a — POR QUE ESTA ROTA NASCEU.
 *
 * 📊 Medido em 06/09/2026: `grep "agent/config\|/api/mcp" app/api` → **zero**.
 * Não existia proxy nenhuma: `components/admin/MCPConfigTab.tsx` chamava o
 * FastAPI DIRETO do navegador, em `NEXT_PUBLIC_BACKEND_URL`, e o FastAPI não
 * pedia nada (`GET /api/mcp/servers?company_id=<uuid falso>` → **200**). Quem
 * escolhia a corretora era a barra de endereços do navegador.
 *
 * A ordem de implantação da R7 é **web antes de api**: a web passa a mandar a
 * chave, e só depois a api passa a exigi-la. Sem esta proxy, o dia em que o
 * backend exigir a chave a aba de conexões morre — porque um navegador não
 * pode carregar segredo nenhum, e nem deve.
 *
 * Aqui: a sessão de admin é DECIFRADA e conferida no banco, a corretora é
 * conferida contra o papel de quem pede (master atravessa; admin de corretora,
 * não) e o `company_id` que segue para o backend é o CONFERIDO — o que veio na
 * URL ou no corpo é descartado.
 */
import { NextRequest, NextResponse } from 'next/server';
import { requireAdminForCompany, getAdminContext, assertSameOrigin } from '@/lib/admin/admin-auth';
import { resolveSessionCompany } from '@/lib/auxiliaries/server';

export const dynamic = 'force-dynamic';

const BACKEND_URL = (
  process.env.NEXT_PUBLIC_API_URL ||
  process.env.BACKEND_URL ||
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  'http://localhost:8000'
).replace(/\/+$/, '');

function chaveInterna(): string {
  return process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY || '';
}

type Resolvida = { ok: true; companyId: string } | { ok: false; status: number };

/**
 * A corretora do pedido. O `company_id` pedido só é ACEITO depois de conferido
 * contra quem pede; nunca é a credencial.
 */
async function corretoraDoPedido(pedida: string | null): Promise<Resolvida> {
  if (pedida) {
    const admin = await requireAdminForCompany(pedida);
    if (admin.ok) return { ok: true, companyId: pedida };
    // Não é admin (ou não é desta corretora): resta o vínculo do próprio usuário.
    const sessao = await resolveSessionCompany();
    if (sessao && sessao.companyId === pedida) return { ok: true, companyId: sessao.companyId };
    return { ok: false, status: admin.status === 401 ? 401 : 403 };
  }

  const sessao = await resolveSessionCompany();
  if (sessao) return { ok: true, companyId: sessao.companyId };

  // Admin sem corretora no pedido: vale a corretora da própria sessão de admin,
  // e ela ainda passa pela conferência no banco.
  const ctx = await getAdminContext();
  if (ctx?.companyId) {
    const admin = await requireAdminForCompany(ctx.companyId);
    if (admin.ok) return { ok: true, companyId: ctx.companyId };
  }
  return { ok: false, status: 401 };
}

async function repassar(
  req: NextRequest,
  caminho: string[],
  metodo: 'GET' | 'POST' | 'DELETE' | 'PATCH' | 'PUT',
) {
  if (metodo !== 'GET') {
    const xo = assertSameOrigin(req);
    if (xo) return NextResponse.json({ detail: 'Pedido bloqueado.' }, { status: xo.status });
  }

  const chave = chaveInterna();
  if (!chave) {
    return NextResponse.json(
      { detail: 'Serviço de conexões não configurado.' },
      { status: 503 },
    );
  }

  let corpo: any = undefined;
  if (metodo !== 'GET' && metodo !== 'DELETE') {
    corpo = await req.json().catch(() => ({}));
  }

  const pedida =
    req.nextUrl.searchParams.get('company_id') ||
    (corpo && typeof corpo.company_id === 'string' ? corpo.company_id : null);

  const quem = await corretoraDoPedido(pedida);
  if (!quem.ok) {
    return NextResponse.json({ detail: 'Não autorizado' }, { status: quem.status });
  }

  const busca = new URLSearchParams(req.nextUrl.searchParams);
  busca.set('company_id', quem.companyId); // 🔴 o conferido, sempre
  if (corpo && typeof corpo === 'object') corpo.company_id = quem.companyId;

  const alvo = `${BACKEND_URL}/api/mcp/${caminho.map(encodeURIComponent).join('/')}?${busca.toString()}`;

  try {
    const r = await fetch(alvo, {
      method: metodo,
      headers: {
        'Content-Type': 'application/json',
        'X-Internal-Key': chave,
      },
      body: corpo === undefined ? undefined : JSON.stringify(corpo),
      cache: 'no-store',
    });
    const dados = await r.json().catch(() => ({}));
    return NextResponse.json(dados, { status: r.status });
  } catch (e) {
    console.error('[MCP PROXY] falha ao falar com o backend:', e);
    return NextResponse.json(
      { detail: 'Não foi possível falar com o serviço de conexões.' },
      { status: 502 },
    );
  }
}

type Ctx = { params: Promise<{ caminho: string[] }> };

export async function GET(req: NextRequest, { params }: Ctx) {
  const { caminho } = await params;
  return repassar(req, caminho, 'GET');
}
export async function POST(req: NextRequest, { params }: Ctx) {
  const { caminho } = await params;
  return repassar(req, caminho, 'POST');
}
export async function DELETE(req: NextRequest, { params }: Ctx) {
  const { caminho } = await params;
  return repassar(req, caminho, 'DELETE');
}
export async function PATCH(req: NextRequest, { params }: Ctx) {
  const { caminho } = await params;
  return repassar(req, caminho, 'PATCH');
}
export async function PUT(req: NextRequest, { params }: Ctx) {
  const { caminho } = await params;
  return repassar(req, caminho, 'PUT');
}
