/**
 * Quem entra no lote do "ligar tudo" — SPEC-093 BLOCO G.
 *
 * 🔴 ARQUIVO SEM IMPORT NENHUM, DE PROPÓSITO. 📊 `tenant-corridor-store.ts`
 * importa por alias `@/`, e `node` não resolve alias: um gate que precisasse
 * dele seria um gate que ninguém roda — que é exatamente como
 * `admin-auth-policy.test.mjs` ficou sem executor por semanas.
 *
 * A decisão inteira do bloco cabe aqui, sem banco e sem rede.
 */

export type EstadoDoCorredor = {
  /** `corridor_id` do catálogo do código. */
  corridorId: string;
  /** A âncora nova desta corretora, ou `null` quando não deu para criar. */
  anchorId: string | null;
  /** As âncoras LEGADAS do mesmo corredor. */
  legado?: string[];
};

export type LoteDeAtivacao = {
  /** As âncoras que recebem `status='active'`. */
  ativar: string[];
  /** Corredores que ficaram como estavam por escolha da corretora. */
  respeitados: string[];
  /** Corredores que já estavam ativos. */
  jaAtivos: string[];
  /** Corredores sem âncora — não se inventa ativação para eles. */
  semAncora: string[];
};

/**
 * 🔴 **A ESCOLHA DA CORRETORA VENCE, E É A PARTE QUE IMPORTA.**
 *
 * Um corredor que ela **pausou de propósito NÃO volta sozinho**. Sem isso, o
 * dashboard desfaz a escolha dela toda manhã — e ela não tem como saber, porque
 * o botão diz "ligar tudo" e faz exatamente isso.
 *
 * ⚠️ A regra é por **linha de ativação existente**, não por status calculado:
 * só entra no lote quem **não tem ativação nenhuma**. Quem já está `active`
 * também fica de fora, e é o que torna o botão **idempotente de graça** — não
 * por um `if` extra que alguém pode remover sem quebrar nada.
 *
 * ⚠️ E as âncoras LEGADAS contam. A corretora que pausou "Allianz Residencial"
 * pelo cartão pausou as duas linhas (`setTenantCorridorStatus` faz isso de
 * propósito); ignorá-las aqui religaria uma delas, e a próxima leitura mostraria
 * o cartão ativo de novo — desfazendo a escolha dela por um caminho que ninguém
 * olha.
 *
 * ## ④ RETOMABILIDADE
 *
 * 🔴 Esta função é **pura e total**: o mesmo estado devolve o mesmo lote,
 * quantas vezes rodar. Uma rodada interrompida no meio deixa um estado
 * PARCIAL — parte das âncoras criada, parte das ativações gravada — e chamar de
 * novo sobre esse estado parcial devolve exatamente o que falta. **O fim é o
 * mesmo de uma rodada limpa.**
 */
export function decidirLoteDeAtivacao(
  corredores: EstadoDoCorredor[],
  statusPorAncora: Record<string, string | null | undefined>,
): LoteDeAtivacao {
  const lote: LoteDeAtivacao = { ativar: [], respeitados: [], jaAtivos: [], semAncora: [] };

  for (const c of corredores) {
    if (!c.anchorId) {
      // Sem âncora não se inventa ativação: seria uma linha apontando para
      // corredor que o motor não sabe executar.
      lote.semAncora.push(c.corridorId);
      continue;
    }
    const todas = [c.anchorId, ...(c.legado ?? [])]
      .filter((id, i, arr) => arr.indexOf(id) === i);
    const estados = todas
      .map((id) => statusPorAncora[id])
      .filter((v) => v !== undefined && v !== null);

    if (estados.length > 0) {
      // 🔴 JÁ EXISTE DECISÃO SOBRE ESTE CORREDOR. Ela fica.
      if (estados.some((v) => String(v) === 'active')) lote.jaAtivos.push(c.corridorId);
      else lote.respeitados.push(c.corridorId);
      continue;
    }
    lote.ativar.push(c.anchorId);
  }
  return lote;
}
