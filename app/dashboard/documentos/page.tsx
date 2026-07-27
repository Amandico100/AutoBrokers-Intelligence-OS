// SPEC-061 §6 — desfazendo uma DUPLICAÇÃO, não a separação.
//
// Esta era a tela de documentos do /admin. O dashboard já tinha a dele:
// `/dashboard/personalizacao/conhecimento` — "documentos e fontes privadas da
// sua corretora, com status real de processamento".
//
// Conferido antes de redirecionar: a tela da Personalização envia arquivo
// (`/api/dashboard/knowledge/upload`) e mostra o processamento. Não se perde
// função nenhuma.
//
// E se perde um defeito: esta tela tinha um botão "Sanitizar Documentos"
// apontando para `/admin/knowledge-base/sanitize`. Um link do dashboard para
// dentro do /admin devolve o corretor para a porta de entrada da plataforma —
// exatamente o vaivém que a §6 existe para acabar.
//
// O nome também melhora: para o corretor, o que importa não é que aquilo é um
// "documento" — é que aquilo é o CONHECIMENTO que o assistente vai usar.
//
// Código antigo: `git log --follow app/dashboard/documentos/page.tsx`.
import { redirect } from 'next/navigation';

export default function RedirecionaParaConhecimento() {
  redirect('/dashboard/personalizacao/conhecimento');
}
