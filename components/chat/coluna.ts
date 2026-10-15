/**
 * A COLUNA DA CONVERSA — a largura que a lista de mensagens e a caixa de texto DIVIDEM.
 *
 * 📊 15/10/2026: a caixa tinha `max-w-[760px]` e a coluna das mensagens `max-w-3xl` (768 px) — duas réguas para a
 * mesma coluna, que podiam se separar a qualquer edição. Agora a régua é uma só, a do ChatGPT e do Claude.ai no
 * notebook: 48rem (768 px), centralizada. No celular a coluna é a tela inteira (o `max-w` não chega a agir).
 *
 * Guarda: `scripts/a-caixa-fica-no-rodape.test.mjs` exige que a caixa e a lista usem ESTA constante.
 */
export const COLUNA_DA_CONVERSA = 'mx-auto w-full max-w-3xl';
