// SPEC-064 Bloco B — redirecionamento permanente.
//
// Pesquisa e SKILL do chat, nao pilar. Ha 7 skills de pesquisa registradas
// e ativas e ZERO pesquisas feitas — a tela existia esperando um trabalho
// que nasce na conversa.
//
// A TELA NAO SUMIU: mudou de casa para dentro de Entregas, que e onde o
// corretor procura o que ja foi feito.
//
// O arquivo continua existindo, e so redireciona, porque link salvo nao some
// quando a rota muda: favorito, e-mail antigo, documentacao velha, uma LLM
// lendo uma SPEC de tres semanas atras. Apagar transformaria cada um deles
// num 404.
import { redirect } from 'next/navigation';

export default function Redireciona() {
  redirect('/dashboard/entregas/pesquisas');
}
