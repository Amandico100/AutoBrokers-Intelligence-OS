// SPEC-130-A (D-MC-74) — a IMAGEM da prévia do link da proposta (og:image).
//
// O robô do WhatsApp/Facebook lê a og:image da página `/r/<token>` e busca
// ESTE endereço. A imagem (PNG 1200×630) é gerada pelo backend a partir do
// modelo da proposta, sem dado pessoal: seguradora e preço da recomendada,
// quantas seguradoras foram comparadas, a marca da anfitriã.
//
// ⚠️ O `matcher` do middleware pula caminhos com ponto (`.*\..*`): esta rota não
// passa pelo login — e não precisa, ela se protege pelo token como a página.
// Buscar a imagem NÃO conta visualização (o backend nem sabe que é uma).
import { NextRequest } from 'next/server';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

function vazio(status: number): Response {
  return new Response(null, { status, headers: { 'Cache-Control': 'no-store' } });
}

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ token: string }> },
) {
  const { token } = await params;
  if (!token || token.length < 32 || !/^[A-Za-z0-9_-]+$/.test(token)) return vazio(404);

  const url = (
    process.env.NEXT_PUBLIC_API_URL ||
    process.env.BACKEND_URL ||
    process.env.NEXT_PUBLIC_BACKEND_URL ||
    ''
  ).replace(/\/+$/, '');
  const key = process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY || '';
  if (!url || !key) return vazio(503);

  try {
    const r = await fetch(`${url}/api/artifacts/shared/${encodeURIComponent(token)}/previa.png`, {
      headers: { 'X-Internal-Key': key },
      cache: 'no-store',
    });
    const tipo = r.headers.get('content-type') || '';
    if (!r.ok || !tipo.startsWith('image/png')) return vazio(404);
    const bytes = await r.arrayBuffer();
    return new Response(bytes, {
      status: 200,
      headers: {
        'Content-Type': 'image/png',
        // Sem dado pessoal, mas o link pode ser revogado: cache curto.
        'Cache-Control': 'public, max-age=600',
        'X-Content-Type-Options': 'nosniff',
        'X-Robots-Tag': 'noindex, nofollow, noarchive',
        'Content-Security-Policy': "default-src 'none'; frame-ancestors 'none'",
      },
    });
  } catch {
    return vazio(404);
  }
}
