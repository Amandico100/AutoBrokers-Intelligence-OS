/**
 * O que UM clique no botão LIGAR/DESLIGAR significa — SPEC-093 BLOCO D.1.
 *
 * 🔴 ARQUIVO SEM IMPORT NENHUM, DE PROPÓSITO — mesma escolha de
 * `admin-auth-policy.ts`, e pelo mesmo motivo: o gate roda esta decisão em
 * `node` puro. 📊 Medido em 25/08/2026: `tenant-agent-store.ts` importa por
 * alias `@/`, e `node` não resolve alias — um gate que precisasse dele seria um
 * gate que ninguém roda, que foi exatamente como `admin-auth-policy.test.mjs`
 * ficou sem executor por semanas.
 */

/**
 * Um toggle tem TRÊS desfechos, não dois: desligou, religou, e **não mudou
 * nada**.
 *
 * 🔴 O terceiro é o que mantém o gate ⑥ de pé — *"agente ligado o tempo todo →
 * ZERO saudações"*. Sem ele, apertar `ligar` num agente que já estava ligado
 * dispararia uma rodada de saudação do nada.
 *
 * ⚠️ `atual` pode ser `null` (linha antiga, coluna nunca escrita). Aqui nulo é
 * tratado como **desligado**, que é o que a coluna significa quando ninguém
 * nunca a escreveu — e a saudação não sai por isso: uma corretora que nunca
 * ligou o agente não tem conversa sem resposta para saudar.
 */
export function decidirTransicaoDoToggle(
  atual: boolean | null | undefined, pedido: boolean,
): { muda: boolean; religou: boolean; desligou: boolean } {
  const antes = atual === true;
  const muda = antes !== pedido;
  return { muda, religou: muda && pedido, desligou: muda && !pedido };
}
