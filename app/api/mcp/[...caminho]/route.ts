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
import { resolveSessionCompany, getSupabaseAdmin } from '@/lib/auxiliaries/server';

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

/**
 * 🔴 SPEC-098 · CONSERTO 1 (red team B1) — A CERCA AGENTE ↔ CORRETORA.
 *
 * 📊 Medido em 06/09/2026: a proxy conferia o `company_id` e descartava o que
 * vinha na URL, mas **nunca conferia o `agent_id`**. Um corretor logado
 * legítimo da corretora A pedia `/api/mcp/agent/<agente da B>/connections`: a
 * proxy resolvia `company_id = A` (verdadeiro), carimbava a chave interna, e o
 * backend não olhava a corretora naquelas rotas. Saía a lista de contas
 * conectadas da B — e com o `DELETE /connections/<id>`, a integração dela caía.
 *
 * O backend também foi fechado (é lá que a decisão final mora). Esta cerca é a
 * primeira porta: recusa antes de a chave interna ser carimbada, e devolve 403
 * em vez de deixar o pedido chegar ao FastAPI com o crachá da casa.
 *
 * ⛔ Erro de banco → 403. Não conseguir provar a posse não é prová-la.
 */
async function objetoDaCorretora(
  caminho: string[],
  busca: URLSearchParams,
  companyId: string,
): Promise<boolean> {
  const supabase = getSupabaseAdmin();

  // `agent/<agent_id>/…` e `oauth/url/<provider>?agent_id=…`
  const agentId =
    (caminho[0] === 'agent' && caminho[1]) || busca.get('agent_id') || null;
  if (agentId) {
    const { data, error } = await supabase
      .from('agents')
      .select('id')
      .eq('id', agentId)
      .eq('company_id', companyId)
      .maybeSingle();
    if (error || !data?.id) return false;
  }

  // `connections/<connection_id>` — a conexão não tem `company_id`; quem sabe
  // de quem ela é é o agente dela (dois saltos, o mesmo do backend).
  if (caminho[0] === 'connections' && caminho[1]) {
    const { data: conexao, error: e1 } = await supabase
      .from('agent_mcp_connections')
      .select('agent_id')
      .eq('id', caminho[1])
      .maybeSingle();
    if (e1 || !conexao?.agent_id) return false;
    const { data: dono, error: e2 } = await supabase
      .from('agents')
      .select('id')
      .eq('id', conexao.agent_id)
      .eq('company_id', companyId)
      .maybeSingle();
    if (e2 || !dono?.id) return false;
  }

  return true;
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

  // 🔴 A corretora conferida não basta: o OBJETO pedido também tem de ser dela.
  let dela = false;
  try {
    dela = await objetoDaCorretora(caminho, busca, quem.companyId);
  } catch (e) {
    console.error('[MCP PROXY] não deu para conferir de quem é o agente:', e);
    dela = false;
  }
  if (!dela) {
    return NextResponse.json(
      { detail: 'Este agente não é desta corretora.' },
      { status: 403 },
    );
  }

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
