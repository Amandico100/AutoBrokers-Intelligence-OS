// SPEC-093 BLOCO D.5 — a ponte Next → backend da prévia da saudação.
//
// 🔴 SÓ A PRÉVIA. ⛔ O ENVIO NÃO PASSA POR AQUI.
//
// 📊 O robô teve **4 conversas de WhatsApp em toda a história do produto** — a
// primeira vez que o envio rodar será a maior coisa que ele já mandou sozinho.
// A decisão do Founder é que o primeiro religamento de cada corretora **espera
// confirmação explícita**, e uma tela é o guarda mais barato que existe.
//
// ⚠️ Deixar o envio fora deste arquivo é deliberado: um `import` conveniente é
// como um botão vira automático sem ninguém decidir.
import { BackendUrlError, getBackendUrl } from '@/lib/backend-url';

/**
 * Quem receberia a saudação nesta corretora, e quantos.
 *
 * ⛔ Nunca manda mensagem. Devolve `null` quando o backend não respondeu — e
 * `null` **não** vira lista vazia silenciosa: a tela precisa poder dizer "não
 * consegui ler" em vez de mostrar zero e parecer que não há ninguém esperando.
 */
export async function previaDaSaudacao(companyId: string): Promise<unknown | null> {
  const internalKey = process.env.BACKEND_INTERNAL_API_KEY || process.env.ADMIN_API_KEY || '';
  if (!internalKey) {
    console.error('[SAUDACAO] chave interna do backend não configurada');
    return null;
  }
  let backendUrl: string;
  try {
    backendUrl = getBackendUrl();
  } catch (error) {
    if (error instanceof BackendUrlError) {
      console.error('[SAUDACAO] backend não configurado');
      return null;
    }
    throw error;
  }

  try {
    const res = await fetch(
      `${backendUrl}/api/saudacao-religamento/previa?company_id=${encodeURIComponent(companyId)}`,
      { headers: { 'X-AutoBrokers-Internal-Key': internalKey }, cache: 'no-store' },
    );
    if (!res.ok) {
      console.error(`[SAUDACAO] prévia respondeu ${res.status}`);
      return null;
    }
    return await res.json();
  } catch (error) {
    console.error('[SAUDACAO] falha ao ler a prévia:', error);
    return null;
  }
}
