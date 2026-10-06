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

// SPEC-130-A — a PROPOSTA (artefato `proposal`) leva UM script, liberado pelo
// HASH que o backend devolve (`csp_script_hashes`, calculado da constante do
// código — nunca do HTML guardado). Só esse formato passa; nada de
// 'unsafe-inline' para script, nunca. Relatório continua sem script nenhum.
const HASH_CSP = /^sha256-[A-Za-z0-9+/]{43}=$/;

// O "Quero fechar" é `?fechar=<opção>` na própria URL do link (o HTML guardado
// não conhece o token). O backend monta o destino a partir do MODELO e devolve;
// aqui só se confere que ele é mesmo o wa.me antes de redirecionar.
const OPCAO = /^[A-Za-z0-9_-]{1,64}$/;

function negado(status: number): Response {
  return new Response(NEGADO, {
    status,
    headers: { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store' },
  });
}

function destinoWhatsapp(destino: unknown): string | null {
  if (typeof destino !== 'string') return null;
  try {
    const u = new URL(destino);
    return u.protocol === 'https:' && u.hostname === 'wa.me' && /^\/\d{10,15}$/.test(u.pathname)
      ? u.toString()
      : null;
  } catch {
    return null;
  }
}

export async function GET(
  req: NextRequest,
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

  // O clique em "Quero fechar" (SPEC-130-A): registra e leva ao WhatsApp da
  // corretora. Não é visualização — nunca passa pelo caminho da página.
  const opcao = req.nextUrl.searchParams.get('fechar');
  if (opcao !== null) {
    if (!OPCAO.test(opcao)) return negado(404);
    let destino: string | null = null;
    try {
      const r = await fetch(`${url}/api/artifacts/shared/${encodeURIComponent(token)}/fechar`, {
        method: 'POST',
        headers: { 'X-Internal-Key': key, 'Content-Type': 'application/json' },
        body: JSON.stringify({ opcao }),
        cache: 'no-store',
      });
      if (r.ok) {
        const j = await r.json();
        if (j?.ok) destino = destinoWhatsapp(j.destino);
      }
    } catch {
      destino = null;
    }
    if (!destino) return negado(404);
    return new Response(null, {
      status: 302,
      headers: {
        Location: destino,
        'Cache-Control': 'private, no-store, max-age=0',
        'Referrer-Policy': 'no-referrer',
        'X-Robots-Tag': 'noindex, nofollow, noarchive',
      },
    });
  }

  let html: string | null = null;
  let hashes: string[] = [];
  try {
    const r = await fetch(`${url}/api/artifacts/shared/${encodeURIComponent(token)}`, {
      headers: {
        'X-Internal-Key': key,
        // Quem abriu: o robô que monta a prévia do link (WhatsApp, Facebook…)
        // não conta visualização (SPEC-130-A G17). Quem decide é o backend.
        'X-Visitante-User-Agent': (req.headers.get('user-agent') || '').slice(0, 512),
      },
      cache: 'no-store',
    });
    if (r.ok) {
      const j = await r.json();
      if (j?.ok && typeof j.html === 'string') {
        html = j.html;
        if (j.kind === 'proposal' && Array.isArray(j.csp_script_hashes)) {
          hashes = j.csp_script_hashes.filter((h: unknown) => typeof h === 'string' && HASH_CSP.test(h));
        }
      }
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
      // A peça é auto-suficiente: nenhuma fonte remota, nenhuma imagem externa,
      // e script SÓ o da proposta, pelo hash (relatório: nenhum). A CSP abaixo é
      // o que esse fato permite declarar — e o que impede que um dado de
      // terceiro injetado na peça vire execução.
      'Content-Security-Policy': [
        "default-src 'none'",
        ...(hashes.length ? [`script-src ${hashes.map((h) => `'${h}'`).join(' ')}`] : []),
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
