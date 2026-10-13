/**
 * SPEC-131-B · conserto K2 (juiz J-B1) — como a lista de renovações pede ao backend, SEM a busca na URL.
 *
 * 🔴 O texto da busca ("Nome ou CPF") é dado pessoal. Na query string ele ia para o log de acesso do uvicorn
 * (`get_path_with_query_string`), para o histórico do navegador e para qualquer log de proxy — e o backend compara
 * o CPF por HMAC justamente para que ele nunca esteja em claro. Por isso:
 *   navegador → Next   no cabeçalho `x-renovacoes-busca` (percent-encoded: o cabeçalho só aceita Latin-1)
 *   Next → backend     no cabeçalho `x-busca`, percent-encoded de novo (o backend, `busca_do_cabecalho`, decodifica)
 *   `q` na query       IGNORADO — nunca repassado, venha de onde vier (link antigo, aba velha)
 *
 * Puro (sem import): o guarda `components/aplicativos/renovacao/a-busca-nao-vai-na-url.test.mjs` o chama de verdade.
 */
export const CABECALHO_DA_BUSCA = 'x-renovacoes-busca';
export const CABECALHO_DA_BUSCA_NO_BACKEND = 'x-busca';

/** Os filtros que podem ir na query — nenhum deles identifica uma pessoa. `q` NÃO está aqui de propósito. */
export const FILTROS_DA_QUERY = ['estado', 'ramo', 'de', 'ate', 'seguradora'] as const;

/** O texto da busca, decodificado e limpo: sem caractere de controle, no máximo 120 caracteres. */
export function lerBusca(cru: string | null | undefined): string {
  if (!cru) return '';
  let texto = cru;
  try {
    texto = decodeURIComponent(cru);
  } catch {
    // não veio percent-encoded — usa como chegou
  }
  // eslint-disable-next-line no-control-regex
  return texto.replace(/[\u0000-\u001F\u007F]/g, '').trim().slice(0, 120);
}

export interface SessaoDoPedido {
  companyId: string;
  userId: string;
  admin: boolean;
}

/** A query (sem a busca) e os cabeçalhos extras (com a busca) do GET ao backend. */
export function pedidoDaLista(
  entrada: URLSearchParams,
  buscaCrua: string | null | undefined,
  s: SessaoDoPedido,
): { consulta: string; cabecalhos: Record<string, string> } {
  const pedido = entrada.get('escopo');
  const escopo = pedido === 'minhas' || pedido === 'todas' ? pedido : s.admin ? 'todas' : 'minhas';
  const p = new URLSearchParams({ company_id: s.companyId, user_id: s.userId, escopo });
  for (const k of FILTROS_DA_QUERY) {
    const v = (entrada.get(k) || '').trim();
    if (v) p.set(k, v.slice(0, 120));
  }
  const busca = lerBusca(buscaCrua);
  const cabecalhos: Record<string, string> = busca ? { [CABECALHO_DA_BUSCA_NO_BACKEND]: encodeURIComponent(busca) } : {};
  return { consulta: p.toString(), cabecalhos };
}
