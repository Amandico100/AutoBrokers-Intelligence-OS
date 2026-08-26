/**
 * A anotação da atendente, do lado do painel — SPEC-090, BLOCO C.
 *
 * 🔴 **POR QUE ESTA REGRA EXISTE DUAS VEZES**
 *
 * A decisão de verdade mora no backend, em
 * `backend/app/services/a_nota_da_atendente.py`. ⛔ Ela precisa existir aqui
 * também porque o proxy do painel faz **duas escritas antes** de chamar o
 * backend, e uma delas é a que estraga tudo:
 *
 * ```
 * app/api/dashboard/conversas/[id]/route.ts:162
 *     "Auto-claim: enviar como humano PAUSA A IA e marca o dono."
 * ```
 *
 * 🔴 **Sem esta função, escrever `#nota …` no painel pausaria o atendimento** —
 * que é exatamente o *"anotar viraria assumir"* que o BLOCO C existe para
 * impedir. E é o pior lugar para isso acontecer: o painel é o único caminho em
 * que o produto consegue garantir que a nota **não sai** para o segurado, então
 * é ali que a Regina e a Saionara devem escrever.
 *
 * 📊 Foi a TERCEIRA vez que este mesmo defeito apareceu nesta SPEC:
 *
 * ```
 * 1. pausar_por_intervencao_humana   (webhook)  — a SPEC viu
 * 2. note_manual_outbound            (webhook)  — a SPEC NÃO viu
 * 3. o auto-claim do painel          (aqui)     — a SPEC NÃO viu 🔴
 * ```
 *
 * ⚠️ **E a duplicação é honesta porque tem guarda:**
 * `scripts/spec090-a-regra-do-prefixo-e-uma-so.test.mjs` lê os DOIS arquivos e
 * fica vermelho se eles discordarem. Duas regras que precisam concordar
 * divergem — a menos que alguém esteja olhando.
 */

/** O prefixo combinado. 🔴 Tem de ser idêntico ao do Python. */
export const PREFIXO_DA_NOTA = '#nota';

/**
 * `#nota …` no **começo absoluto** da mensagem?
 *
 * ⚠️ **Sem `\s*` antes do `#`** — um espaço antes já derruba, e é assim que a
 * SPEC pede. ⛔ `"o robô errou #nota"` não é nota: é intervenção, e tem de
 * pausar a IA como qualquer mensagem humana.
 *
 * ⚠️ **Insensível a maiúscula**, e não é frouxidão: 📊 teclado de celular
 * capitaliza a primeira letra, e `#Nota` virando intervenção custaria as duas
 * coisas de uma vez — pausar o robô **e** mandar o bastidor para o segurado.
 *
 * ⚠️ E exige separador depois: `#notas` é outra palavra.
 */
export function ehAnotacao(texto: unknown): boolean {
  return /^#nota(?=[\s:,\-–—]|$)/i.test(String(texto ?? ''));
}
