// modelo: claude-opus-5-5
//
// ⚠️ HARNESS TEMPORÁRIO DE CAPTURA — SPEC-139 · L6. Apagar ao fim da SPEC (como o da SPEC-131-B).
//
// `/embed/` é público (middleware: o widget) — por isso o juiz de design captura sem login. A página NÃO lê banco nem
// sessão: monta as telas reais da loja com dados de EXEMPLO (`dados-de-exemplo.ts`), e todo `fetch` a `/api/` é
// respondido em memória pelo próprio harness (`HarnessDaLoja.tsx`). `loja` é pasta ESTÁTICA ao lado de `[agentId]` —
// um nome de parâmetro só por posição (CLAUDE.md §9.1).

import { Suspense } from 'react';

import HarnessDaLoja from './HarnessDaLoja';

export const dynamic = 'force-dynamic';

export const metadata = { robots: { index: false, follow: false } };

export default function HarnessDaLojaPage() {
  return (
    <Suspense fallback={null}>
      <HarnessDaLoja />
    </Suspense>
  );
}
