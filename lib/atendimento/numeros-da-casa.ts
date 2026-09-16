// SPEC-EXTRA-001.3 — BLOCO B · os números da própria corretora, do lado do BFF.
//
// 🔴 **ISTO É UMA PORTA, NÃO UM SEGUNDO MOTOR** (CLAUDE.md §5). A autoridade da
// regra é `o_fim_do_atendimento._variantes_do_telefone` (Python, commit
// `05f46a9`) — a MESMA que casa com/sem `55` e com/sem nono dígito no
// `JANELA_SILENCIO_EXCECOES`. Esta é a tradução dela para o runtime em que a
// Fila é montada, porque `projetarCasos` roda em Node e não tem como chamar
// Python a cada abertura do painel.
//
// ⚠️ **E um padrão medido com um motor e aplicado com outro é um padrão sobre
// outra coisa** (CLAUDE.md §9.4). Por isso as duas implementações são
// confrontadas caso a caso pelo guarda
// `backend/tests/test_o_numero_da_casa_nao_e_cliente.py`, que roda as duas
// sobre a MESMA tabela de casos e exige resultado idêntico. Se divergirem, o
// guarda fica vermelho — que é a única forma honesta de ter a mesma regra em
// dois runtimes.
import type { SupabaseClient } from '@supabase/supabase-js';

/** As variantes de um telefone. Porta de `_variantes_do_telefone` (Python). */
export function variantesDoTelefone(telefone: unknown): Set<string> {
  let d = String(telefone ?? '').replace(/\D/g, '');
  if (!d) return new Set();
  if (d.startsWith('55') && d.length >= 12) d = d.slice(2);
  const out = new Set<string>([d]);
  if (d.length === 11 && d[2] === '9') {
    out.add(d.slice(0, 2) + d.slice(3)); // DDD + 9 + 8 dígitos → sem o nono
  } else if (d.length === 10) {
    out.add(d.slice(0, 2) + '9' + d.slice(2)); // DDD + 8 → com o nono
  }
  return out;
}

export function ehNumeroDaCasa(numeros: Set<string>, telefone: unknown): boolean {
  const alvo = variantesDoTelefone(telefone);
  if (!alvo.size || !numeros.size) return false;
  // ⚠️ `Array.from` e não `for…of` sobre o Set: o `target` deste tsconfig não
  // permite iterar Set direto (TS2802), e baixar a régua do projeto inteiro por
  // três laços seria trocar um defeito por um maior.
  return Array.from(alvo).some((v) => numeros.has(v));
}

/**
 * Os números da casa desta corretora, já em variantes.
 *
 * Duas fontes, uma resposta — as MESMAS da `numeros_da_casa` do backend:
 * `users_v2.phone` dos membros ativos ∪ `company_internal_numbers`.
 *
 * ⛔ Conjunto VAZIO no escuro: uma leitura ruim não pode sumir com os casos de
 * segurados de verdade da Fila.
 */
export async function carregarNumerosDaCasa(
  supabase: SupabaseClient,
  companyId: string,
): Promise<Set<string>> {
  const numeros = new Set<string>();
  if (!companyId) return numeros;
  try {
    const { data: vinculos } = await supabase
      .from('company_members')
      .select('user_id')
      .eq('company_id', companyId) // 🔴 CLAUDE.md §7
      .eq('status', 'active')
      .limit(500);
    const ids = (vinculos || []).map((v: any) => String(v.user_id)).filter(Boolean);
    if (ids.length) {
      const { data: pessoas } = await supabase
        .from('users_v2')
        .select('id, phone')
        .in('id', ids)
        .limit(500);
      for (const p of pessoas || []) {
        Array.from(variantesDoTelefone((p as any).phone)).forEach((v) => numeros.add(v));
      }
    }
  } catch (e) {
    console.warn('[NUMEROS DA CASA] membros não lidos', e);
  }
  try {
    const { data: internos } = await supabase
      .from('company_internal_numbers')
      .select('phone')
      .eq('company_id', companyId) // 🔴 CLAUDE.md §7
      .limit(500);
    for (const n of internos || []) {
      Array.from(variantesDoTelefone((n as any).phone)).forEach((v) => numeros.add(v));
    }
  } catch (e) {
    console.warn('[NUMEROS DA CASA] tabela não lida', e);
  }
  return numeros;
}
