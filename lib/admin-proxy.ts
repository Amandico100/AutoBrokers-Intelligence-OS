import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const ADMIN_API_KEY = process.env.ADMIN_API_KEY || '';

/**
 * Proxy autenticado: encaminha request ao backend com X-Admin-API-Key.
 * Segue o mesmo padrão de app/api/admin/agents/company/[companyId]/route.ts
 */
export async function authenticatedProxy(
  request: NextRequest,
  backendPath: string,
): Promise<NextResponse> {
  try {
    // 1. Construir URL do backend preservando query params
    const url = new URL(backendPath, BACKEND_URL);
    request.nextUrl.searchParams.forEach((value, key) => {
      url.searchParams.set(key, value);
    });

    // 2. Preparar headers (mesmo padrão das rotas existentes)
    const headers: Record<string, string> = {
      'X-Admin-API-Key': ADMIN_API_KEY,
    };

    const contentType = request.headers.get('content-type');
    if (contentType && !contentType.includes('multipart/form-data')) {
      headers['Content-Type'] = contentType;
    }

    // 3. Preparar body
    let body: any = undefined;
    if (request.method !== 'GET' && request.method !== 'HEAD') {
      if (contentType?.includes('multipart/form-data')) {
        body = await request.formData();
      } else {
        body = await request.text();
      }
    }

    // 4. Forward ao backend
    const backendResponse = await fetch(url.toString(), {
      method: request.method,
      headers,
      body,
    });

    // 5. Retornar response
    const responseBody = await backendResponse.text();
    return new NextResponse(responseBody, {
      status: backendResponse.status,
      headers: {
        'Content-Type': backendResponse.headers.get('Content-Type') || 'application/json',
      },
    });
  } catch (error: any) {
    console.error('[ADMIN PROXY] Backend error:', error.message);
    return NextResponse.json({ error: 'Erro ao conectar com backend' }, { status: 502 });
  }
}
