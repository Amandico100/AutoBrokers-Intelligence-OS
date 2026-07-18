import { NextRequest } from 'next/server';
import { authenticatedProxy } from '@/lib/admin-proxy';

// SPEC-038: proxy da superfície ATLAS (Observador, mapas de URA) para o backend.
async function handler(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const { path } = await params;
  return authenticatedProxy(request, `/api/admin/atlas/${(path || []).join('/')}`);
}

export { handler as GET, handler as POST };
