// SPEC-133-A F4 (D-133A-10) — PARA ONDE o cartão do WhatsApp fala.
//
// O cartão (`WhatsAppChannelCard`) e o pareamento (`WhatsAppPairingFlow`) nasceram
// para UMA tela: o hub da corretora, que fala com `/api/dashboard/whatsapp-channel`
// e descobre a corretora pela SESSÃO. O portal admin precisa do MESMO cartão para
// ler o QR do Quem Cobra Menos, falando com `/api/admin/canais/whatsapp`.
//
// 🔴 Sem `endpoint`, tudo é como sempre foi — inclusive a chave da tentativa no
// `sessionStorage`. Com `endpoint`, a chave ganha o endereço: uma tentativa do
// admin nunca é retomada pela tela da corretora, nem o contrário.
//
// Puro de propósito: `scripts/o-qr-do-canal-no-admin.test.mjs` executa isto.

export const ENDPOINT_DAS_CORRETORAS = '/api/dashboard/whatsapp-channel';

const CHAVE_DA_TENTATIVA = 'autobrokers-whatsapp-observer-attempt';

export function endpointDoCartao(endpoint?: string | null): string {
  const limpo = (endpoint || '').trim();
  return limpo || ENDPOINT_DAS_CORRETORAS;
}

export function chaveDaTentativa(endpoint?: string | null): string {
  const alvo = endpointDoCartao(endpoint);
  return alvo === ENDPOINT_DAS_CORRETORAS ? CHAVE_DA_TENTATIVA : `${CHAVE_DA_TENTATIVA}:${alvo}`;
}

/** `GET` com `?a=b` — respeita um endpoint que já traga query. */
export function comQuery(endpoint: string, query: string): string {
  return `${endpoint}${endpoint.includes('?') ? '&' : '?'}${query}`;
}
