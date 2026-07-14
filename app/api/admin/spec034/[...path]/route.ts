import { NextRequest } from 'next/server';
import { authenticatedProxy } from '@/lib/admin-proxy';

// Proxy das superfícies SPEC-034 (Central de Agentes, Acionamentos, Insights,
// Registro, Mapas) para o backend FastAPI.
async function handler(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const { path } = await params;
  return authenticatedProxy(request, `/api/admin/spec034/${(path || []).join('/')}`);
}

export { handler as GET, handler as POST };
