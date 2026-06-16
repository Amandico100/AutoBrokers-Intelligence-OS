// Invocação IN-PROCESS de route handlers de runtime (42W1.1).
//
// Por que existe: o bridge de WhatsApp precisa acionar as MESMAS rotas do
// dashboard (reply/policy-lookup/policy-select/step/dispatch-dry-run). Fazer
// isso via self-fetch HTTP (Next chamando a própria origem) é frágil em produção
// (deployment protection / resolução de origin) e foi a causa do 42W1 retornar
// vazio. Aqui chamamos o handler diretamente, no MESMO processo, sem rede.
//
// O handler recebe um NextRequest sintetizado com a chave interna no header e o
// company_id no body — ativando o branch de auth interna das rotas. NÃO altera
// o fluxo de sessão do dashboard.
import { NextRequest } from 'next/server';

type RouteHandler = (req: NextRequest, ctx: { params: Promise<any> }) => Promise<Response>;

export interface InvokeResult {
  ok: boolean;
  status: number;
  json: any;
}

export async function invokeRuntimeHandler(
  handler: RouteHandler,
  opts: { caseId?: string; body: Record<string, unknown>; internalKey: string },
): Promise<InvokeResult> {
  try {
    const req = new NextRequest('https://internal.invoke/runtime', {
      method: 'POST',
      headers: { 'content-type': 'application/json', 'x-autobrokers-internal-key': opts.internalKey },
      body: JSON.stringify(opts.body ?? {}),
    });
    const ctx = { params: Promise.resolve(opts.caseId ? { caseId: opts.caseId } : {}) };
    const res = await handler(req, ctx);
    const json = await res.json().catch(() => ({}));
    return { ok: res.ok, status: res.status, json };
  } catch (e: any) {
    return { ok: false, status: 0, json: { error: e?.message || 'invoke_failed' } };
  }
}
