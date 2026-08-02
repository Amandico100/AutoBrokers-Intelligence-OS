// SPEC-064 Bloco B — redirecionamento permanente.
//
// Memoria e configuracao de como o sistema lembra de voce — personalizacao,
// nao pilar.
//
// A TELA NAO SUMIU: mudou de endereco, inteira.
//
// O arquivo continua existindo, e so redireciona, porque link salvo nao some
// quando a rota muda: favorito, e-mail antigo, documentacao velha, uma LLM
// lendo uma SPEC de tres semanas atras. Apagar transformaria cada um deles
// num 404.
import { redirect } from 'next/navigation';

export default function Redireciona() {
  redirect('/dashboard/personalizacao/memorias');
}
