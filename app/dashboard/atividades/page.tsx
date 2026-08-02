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

export default function Redireciona() {
  redirect('/dashboard/entregas');
}
