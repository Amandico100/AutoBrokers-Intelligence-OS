// SPEC-064 Bloco B — redirecionamento permanente.
//
// A galeria era o terceiro clique para ver o que devia estar na primeira
// tela.
//
// O CONTEUDO FOI ABSORVIDO: o catalogo inteiro — ligados, disponiveis e em
// breve — abre direto em /dashboard/auxiliares.
//
// O arquivo continua existindo, e so redireciona, porque link salvo nao some
// quando a rota muda: favorito, e-mail antigo, documentacao velha, uma LLM
// lendo uma SPEC de tres semanas atras. Apagar transformaria cada um deles
// num 404.
import { redirect } from 'next/navigation';

export default function Redireciona() {
  redirect('/dashboard/auxiliares');
}
