import { redirect } from 'next/navigation';

// SPEC-139 (EXTRA-001.9): a Equipe é da CORRETORA e mora dentro dela.
// O endereço antigo continua respondendo (307) para não quebrar favorito nem link
// guardado. ⛔ Nunca pasta dinâmica nova nesta posição (CLAUDE.md §9.1).
// O guarda: scripts/links-internos-casam-rotas.test.mjs.
export default function RedirecionaParaAEquipe() {
  redirect('/dashboard/personalizacao/corretora/equipe');
}
