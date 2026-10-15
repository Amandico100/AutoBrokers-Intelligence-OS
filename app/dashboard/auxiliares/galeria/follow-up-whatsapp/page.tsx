// SPEC-139 · L3 (P-16) — redirecionamento (307).
//
// A tela do Follow-up do WhatsApp (o rascunho que vai para aprovação) morava aqui. Agora ela é a aba "Follow-ups" do aplicativo, dentro da casca de todo aplicativo
// (/dashboard/auxiliares/[slug]?aba=): o conteúdo foi MOVIDO, inteiro, para components/aplicativos/.
//
// O arquivo continua existindo, e só redireciona, porque link salvo não some quando a rota muda: favorito, mensagem
// antiga, documentação velha. Apagar transformaria cada um deles num 404. 🔴 Nunca uma pasta dinâmica nova na mesma
// posição da árvore de rotas (CLAUDE.md §9.1) — a casca é a [slug] que já existe; a aba é QUERY.
import { redirect } from 'next/navigation';

export default function Redireciona() {
  redirect('/dashboard/auxiliares/follow-up-whatsapp?aba=follow-ups');
}