/**
 * SPEC-132-B · B3 — como a lista de cotações pede ao backend, SEM a busca na URL (a mesma regra da aba Renovações,
 * juiz J-B1 da 131-B / D-131-49).
 *
 * 🔴 O texto da busca ("Nome, placa ou CPF") é dado pessoal. Na query string ele iria ao log de acesso, ao histórico
 * do navegador e a qualquer log de proxy. Por isso:
 *   navegador → Next   no cabeçalho `x-cotacoes-busca` (percent-encoded: o cabeçalho só aceita Latin-1)
 *   Next → backend     no cabeçalho `x-busca`, percent-encoded de novo (o backend, `busca_do_cabecalho`, decodifica)
 *   `q` na query       IGNORADO — nunca repassado
 *
 * Puro (sem import): o guarda `components/aplicativos/cotacao/a-cotacao-nao-vaza.test.mjs` o chama de verdade.
 */
export const CABECALHO_DA_BUSCA = 'x-cotacoes-busca';
export const CABECALHO_DA_BUSCA_NO_BACKEND = 'x-busca';

/** Os filtros que podem ir na query — nenhum identifica uma pessoa. `q` NÃO está aqui de propósito. */
export const ESTADOS_DO_FILTRO = ['calculando', 'pronta', 'sem_resposta'] as const;

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

/** A query (sem a busca, com `company_id`/`user_id` da SESSÃO) e os cabeçalhos extras (com a busca) do GET. */
export function pedidoDaLista(
  entrada: URLSearchParams,
  buscaCrua: string | null | undefined,
  s: SessaoDoPedido,
): { consulta: string; cabecalhos: Record<string, string> } {
  const pedido = entrada.get('escopo');
  const escopo = pedido === 'minhas' || pedido === 'todas' ? pedido : s.admin ? 'todas' : 'minhas';
  const p = new URLSearchParams({ company_id: s.companyId, user_id: s.userId, escopo });
  const estado = (entrada.get('estado') || '').trim();
  if ((ESTADOS_DO_FILTRO as readonly string[]).includes(estado)) p.set('estado', estado);
  const busca = lerBusca(buscaCrua);
  const cabecalhos: Record<string, string> = busca ? { [CABECALHO_DA_BUSCA_NO_BACKEND]: encodeURIComponent(busca) } : {};
  return { consulta: p.toString(), cabecalhos };
}
