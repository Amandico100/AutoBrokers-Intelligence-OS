import { redirect } from 'next/navigation';

/**
 * SPEC-131-B G3 (D-131-06) — "Serviços" saiu de Personalização: o que cada aplicativo faz mora na aba Configurar DELE.
 * O endereço antigo continua vivo (link salvo não some) e leva à Renovação. O backend (`/api/servicos-da-corretora`)
 * não mudou de lugar: a aba Configurar de cada aplicativo lê e grava pela mesma rota.
 */
export default function ServicosPage() {
  redirect('/dashboard/auxiliares/renovacao?aba=configurar');
}
