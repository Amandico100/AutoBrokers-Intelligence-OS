// SPEC-139 · L3 (P-16) — redirecionamento (307).
//
// A tela do Resumo de atendimentos morava aqui. Agora ela é a aba "Resumos" do aplicativo, dentro da casca de todo aplicativo
// (/dashboard/auxiliares/[slug]?aba=): o conteúdo foi MOVIDO, inteiro, para components/aplicativos/.
//
// O arquivo continua existindo, e só redireciona, porque link salvo não some quando a rota muda: favorito, mensagem
// antiga, documentação velha. Apagar transformaria cada um deles num 404. 🔴 Nunca uma pasta dinâmica nova na mesma
// posição da árvore de rotas (CLAUDE.md §9.1) — a casca é a [slug] que já existe; a aba é QUERY.
import { redirect } from 'next/navigation';

export default function Redireciona() {
  redirect('/dashboard/auxiliares/resumo-atendimentos?aba=resumos');
}