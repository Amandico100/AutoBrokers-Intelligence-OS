// SPEC-064 Bloco B — redirecionamento permanente.
//
// Atividades respondia "o que ja aconteceu aqui?" — a mesma pergunta de
// Historico e de Pesquisas. Tres itens de menu para a mesma pergunta e como
// um menu vira lista.
//
// O CONTEUDO FOI ABSORVIDO: agent_activities e uma das cinco fontes que
// Entregas le, no filtro "Trabalhos".
//
// O arquivo continua existindo, e so redireciona, porque link salvo nao some
// quando a rota muda: favorito, e-mail antigo, documentacao velha, uma LLM
// lendo uma SPEC de tres semanas atras. Apagar transformaria cada um deles
// num 404.
import { redirect } from 'next/navigation';

// SPEC-095 A.1 (emenda E1) — e agora ele manda a LENTE junto.
//
// 📊 04/09/2026: dos 4 redirects que apontam para /dashboard/entregas, tres
// mandam `?tipo=` e este nao mandava nenhum. Com a lente padrao virando
// Relatorios, quem salvou o link de Atividades cairia numa lista onde as
// atividades nao aparecem — elas sao `tipo: 'trabalho'` na rota. Um redirect
// que leva a uma tela vazia e pior que um 404: o 404 explica.
export default function Redireciona() {
  redirect('/dashboard/entregas?tipo=tudo');
}
