// SPEC-064 Bloco C — redirecionamento permanente.
//
// Esta era a página de "detalhe genérico para Auxiliares sem página dedicada".
// Ela existia porque o detalhe morava DENTRO da galeria — e a galeria era o
// terceiro clique a partir de "Auxiliares".
//
// Agora o detalhe é `/dashboard/auxiliares/[slug]`: uma rota só, para todos,
// alimentada pelo catálogo global, com o que o corretor precisa para decidir
// (o que faz, o que ele ganha, de onde vem o dado, o que falta conectar).
// Esta virou a mesma coisa com outro endereço, e duas telas para a mesma
// pergunta é como um produto vira labirinto.
//
// O arquivo continua existindo, e só redireciona, porque link salvo não some
// quando a rota muda: favorito, mensagem antiga, documentação velha. Apagar
// transformaria cada um deles num 404.
import { redirect } from 'next/navigation';

export default async function RedirecionaParaOAuxiliar({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  redirect(`/dashboard/auxiliares/${slug}`);
}
