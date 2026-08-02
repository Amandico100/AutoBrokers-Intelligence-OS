// SPEC-064 Bloco B — redirecionamento permanente.
//
// "Meus auxiliares" era onde os Auxiliares de verdade moravam — sem link
// no menu, alcancaveis so por quem soubesse o endereco.
//
// O CONTEUDO FOI ABSORVIDO: nao existe mais separacao entre "a galeria" e
// "os meus". E uma tela so, com os ligados em cima.
//
// O arquivo continua existindo, e so redireciona, porque link salvo nao some
// quando a rota muda: favorito, e-mail antigo, documentacao velha, uma LLM
// lendo uma SPEC de tres semanas atras. Apagar transformaria cada um deles
// num 404.
import { redirect } from 'next/navigation';

export default function Redireciona() {
  redirect('/dashboard/auxiliares');
}
