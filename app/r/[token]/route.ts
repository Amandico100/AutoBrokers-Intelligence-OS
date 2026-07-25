// SPEC-057 — página pública de um relatório compartilhado.
//
// É uma rota e não uma página de propósito. O relatório já é um documento HTML
// completo, com seu próprio <head>, suas variáveis de marca e seu CSS de
// impressão. Renderizá-lo dentro do layout do Next criaria dois documentos
// aninhados: o CSS de impressão pararia de valer, a identidade da corretora
// competiria com a do produto, e o PDF sairia com o menu do dashboard.
//
// Servido cru, o que o cliente do corretor abre é exatamente o mesmo arquivo
// que o corretor viu e que vira PDF.
import { NextRequest } from 'next/server';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

const NEGADO = `<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Link indisponível</title>
<style>
  body{margin:0;min-height:100vh;display:grid;place-items:center;background:#0b0d10;
    color:#e8ecef;font:400 16px/1.6 -apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif}
  .c{max-width:34rem;padding:2.5rem;text-align:center}
  h1{font-size:1.35rem;margin:0 0 .75rem;font-weight:600;letter-spacing:-.02em}
  p{margin:0;color:#9aa4ad;font-size:.95rem}
</style></head>
<body><div class="c">
<h1>Este link não está mais disponível</h1>
<p>Ele pode ter expirado ou sido desativado por quem o enviou.
Peça um link novo a quem compartilhou o documento com você.</p>
</div></body></html>`;

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ token: string }> },
) {
  const { token } = await params;

  // Um token só pode ser base64url. Recusar formato inválido antes de ir ao
  // banco evita transformar esta rota em sonda de existência.
  if (!token || token.length < 32 || !/^[A-Za-z0-9_-]+$/.test(token)) {
    return new Response(NEGADO, {
      status: 404,
      headers: { 'Content-Type': 'text/html; charset=utf-8' },
    });
  }

  const url = (
    process.env.NEXT_PUBLIC_API_URL ||
    process.env.BACKEND_URL ||
    process.env.NEXT_PUBLIC_BACKEND_URL ||
    ''
  ).replace(/\/+$/, '');
  const key = process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY || '';

  if (!url || !key) {
    return new Response(NEGADO, {
      status: 503,
      headers: { 'Content-Type': 'text/html; charset=utf-8' },
    });
  }

  let html: string | null = null;
  try {
    const r = await fetch(`${url}/api/artifacts/shared/${encodeURIComponent(token)}`, {
      headers: { 'X-Internal-Key': key },
      cache: 'no-store',
    });
    if (r.ok) {
      const j = await r.json();
      if (j?.ok && typeof j.html === 'string') html = j.html;
    }
  } catch {
    html = null;
  }

  if (!html) {
    return new Response(NEGADO, {
      status: 404,
      headers: { 'Content-Type': 'text/html; charset=utf-8' },
    });
  }

  return new Response(html, {
    status: 200,
    headers: {
      'Content-Type': 'text/html; charset=utf-8',
      // Do outro lado do link há dado de segurado: nada de cache
      // compartilhado, e nada de indexação.
      'Cache-Control': 'private, no-store, max-age=0',
      'X-Robots-Tag': 'noindex, nofollow, noarchive',
      'Referrer-Policy': 'no-referrer',
      'X-Content-Type-Options': 'nosniff',
      // A peça é auto-suficiente: nenhum script, nenhuma fonte remota, nenhuma
      // imagem externa. A CSP abaixo é o que esse fato permite declarar — e o
      // que impede que um dado de terceiro injetado no relatório vire execução.
      'Content-Security-Policy': [
        "default-src 'none'",
        "img-src 'self' data:",
        "style-src 'unsafe-inline'",
        "font-src 'self' data:",
        "base-uri 'none'",
        "form-action 'none'",
        "frame-ancestors 'none'",
      ].join('; '),
    },
  });
}
