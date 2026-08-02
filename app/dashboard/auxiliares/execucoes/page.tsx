// SPEC-064 Bloco B — redirecionamento permanente.
//
// A execucao de um Auxiliar e uma das coisas que ja aconteceram.
//
// O CONTEUDO FOI ABSORVIDO: `auxiliary_runs` e uma das cinco fontes que
// Entregas le, no filtro "Trabalhos".
//
// O arquivo continua existindo, e so redireciona, porque link salvo nao some
// quando a rota muda: favorito, e-mail antigo, documentacao velha, uma LLM
// lendo uma SPEC de tres semanas atras. Apagar transformaria cada um deles
// num 404.
import { redirect } from 'next/navigation';

export default function Redireciona() {
  redirect('/dashboard/entregas?tipo=trabalho');
}
