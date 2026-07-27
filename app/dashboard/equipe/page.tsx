// SPEC-061 §6 — desfazendo uma DUPLICAÇÃO, não a separação.
//
// Esta era a tela de equipe do /admin (o cabeçalho do arquivo antigo dizia
// literalmente `// app/admin/team/page.tsx`). Eu a movi para cá sem ver que o
// dashboard já tinha a dele: `/dashboard/personalizacao/equipe`, feita na
// SPEC-045 para a corretora, com trilha de navegação e a pergunta certa no
// subtítulo — "quem tem acesso à sua corretora, com papel e status".
//
// Conferido antes de redirecionar: a tela da Personalização convida (POST),
// edita papel (PATCH) e remove (DELETE). Não se perde função nenhuma.
//
// Duas telas de equipe no mesmo dashboard não é organização — é uma escolha
// que o corretor não deveria precisar fazer.
//
// Código antigo: `git log --follow app/dashboard/equipe/page.tsx`.
import { redirect } from 'next/navigation';

export default function RedirecionaParaEquipe() {
  redirect('/dashboard/personalizacao/equipe');
}
