// A tela mora em `components/memorias/CerebroDeMemorias.tsx` e e servida por
// DUAS rotas, de proposito:
//
//   /dashboard/memorias                 o pilar do menu (SPEC-081, temporario)
//   /dashboard/personalizacao/memorias  o endereco canonico da SPEC-064
//
// Antes a primeira era um `redirect()` para a segunda. Vira renderizacao
// direta porque o item de menu precisa de um endereco PROPRIO: com o
// redirecionamento, o corretor clicava em Memorias e o realce acendia em
// Personalizacao -- `isActiveRoute` casa por prefixo, e
// `/dashboard/personalizacao/memorias` comeca com `/dashboard/personalizacao`.
//
// Nenhum link antigo quebra: as duas rotas respondem, com a mesma tela.
import CerebroDeMemorias from '@/components/memorias/CerebroDeMemorias';

export default function Pagina() {
  return <CerebroDeMemorias />;
}
