/**
 * SPEC-078 C.4/C.5 — O CONTEUDO FOI ABSORVIDO pela tela de cada Auxiliar.
 *
 * Esta rota era uma página de 706 linhas com botão "Nova rotina", listando as
 * rotinas de TODA a corretora sem dizer de quem era cada uma. Ela é a quarta
 * das quatro rotas que a SPEC-064 §B.3 mandou absorver — e a única que não
 * tinha sido. As três irmãs (`galeria`, `meus`, `execucoes`) viraram stubs
 * como este em 02/08/2026.
 *
 * 📊 O preço de ela ter sobrevivido, medido em 17/08/2026: `ONTOLOGIA:51` diz
 * "Rotina nunca existe sozinha", e o botão "Nova rotina" numa lista sem dono
 * criava exatamente isso. A rotina órfã das 13:01 daquele dia saiu dele.
 *
 * O conteúdo foi para `components/auxiliares/PainelDeRotinas.tsx`, renderizado
 * dentro de `/dashboard/auxiliares/[slug]` na seção "Rotinas deste Auxiliar".
 * O possessivo do título faz o trabalho que o cânone pede: diz que é Rotina, e
 * diz de quem.
 *
 * 🔴 E o histórico foi JUNTO. Esta página era o único lugar que mostrava
 * `routine_runs` (📊 32 execuções). Fazer o redirect sem levá-lo para Entregas
 * faria este comentário mentir — e "conteúdo absorvido" sobre conteúdo que
 * sumiu é exatamente o defeito que a SPEC-064 §J.2.4 mandou eliminar.
 *
 * ⚠️ O redirect FICA. Apagar a rota devolveria 404 para quem tem o link
 * salvo, e o gate B2 da SPEC-064 trata isso como vermelho.
 */
import { redirect } from 'next/navigation';

export const dynamic = 'force-dynamic';

export default function RotinasAbsorvidasPage() {
  redirect('/dashboard/auxiliares');
}
