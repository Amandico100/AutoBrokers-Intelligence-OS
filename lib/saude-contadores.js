/**
 * A regra que decide a COR dos contadores no painel de Saúde do sistema.
 *
 * 🔴 POR QUE ISTO É UM ARQUIVO SEPARADO, E EM `.js`
 * ================================================
 * 📊 06/08/2026, 21:09. A tela mostrava `erro:ImportError: 4510` e
 * `erro:APIError: 5612` em vermelho vivo. Os dois defeitos já estavam
 * corrigidos havia horas. O contador do Redis é acumulado — soma desde que o
 * servidor ligou e nunca zera — e a tela lia esse total como se fosse o agora.
 *
 * Ao consertar, escrevi o teste com uma CÓPIA desta função. A prova por mutação
 * denunciou na hora: quebrei a regra dentro da tela e o teste continuou verde,
 * porque ele exercitava a cópia. Um teste que testa a própria cópia do código
 * mede a si mesmo.
 *
 * Então a regra passou a morar aqui, num arquivo que a tela importa e o teste
 * importa. `.js` e não `.ts` por um motivo prático: o teste roda em Node puro
 * (`node scripts/*.test.mjs`), sem passo de compilação. Os tipos vêm por JSDoc,
 * que o TypeScript entende e o Node ignora.
 *
 * A REGRA
 * =======
 * A cor vem da janela de AGORA (10 minutos, que expira no Redis). O acumulado
 * é histórico e aparece apagado. Vermelho que fica aceso para sempre é vermelho
 * que se aprende a ignorar — e aí o dia em que ele significa alguma coisa,
 * ninguém olha.
 */

/**
 * @param {unknown} v
 * @returns {v is Record<string, number>}
 */
function ehMapa(v) {
  return Boolean(v) && typeof v === 'object' && !Array.isArray(v);
}

/**
 * Separa o que está acontecendo AGORA do que já aconteceu algum dia.
 *
 * Aceita os dois formatos de propósito: `{agora, total_desde_o_boot}` do
 * servidor atual e o mapa achatado do servidor antigo. Durante um deploy os
 * dois existem ao mesmo tempo, e um painel que quebra no meio do deploy é
 * inútil justamente na hora em que se olha para ele.
 *
 * @param {Record<string, unknown>} valor
 * @returns {{
 *   errosAgora: Array<[string, number]>,
 *   bonsAgora: Array<[string, number]>,
 *   errosNoTotal: Array<[string, number]>,
 *   vermelho: boolean,
 * }}
 */
export function lerContadores(valor) {
  const temFormatoNovo = 'agora' in valor || 'total_desde_o_boot' in valor;

  /** @type {Record<string, number>} */
  let agora = {};
  if (temFormatoNovo) {
    if (ehMapa(valor.agora)) agora = valor.agora;
  } else if (ehMapa(valor)) {
    agora = /** @type {Record<string, number>} */ (valor);
  }

  /** @type {Record<string, number>} */
  let total = {};
  if (temFormatoNovo && ehMapa(valor.total_desde_o_boot)) total = valor.total_desde_o_boot;

  // `Number(v) > 0` e não só a presença da chave: o Redis devolve a chave com
  // 0 quando o contador foi criado e zerado, e contar isso como erro
  // reacenderia o vermelho para sempre por outro caminho.
  const errosAgora = Object.entries(agora).filter(
    ([k, v]) => k.startsWith('erro') && Number(v) > 0,
  );
  const bonsAgora = Object.entries(agora).filter(
    ([k, v]) => !k.startsWith('erro') && k !== 'sem_atividade_nesta_janela' && Number(v) > 0,
  );
  const errosNoTotal = Object.entries(total).filter(([k]) => k.startsWith('erro'));

  return { errosAgora, bonsAgora, errosNoTotal, vermelho: errosAgora.length > 0 };
}
