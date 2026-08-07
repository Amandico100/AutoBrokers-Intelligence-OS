/**
 * O vermelho do painel de saúde é do AGORA — nunca do histórico.
 *
 * A HISTÓRIA
 * ==========
 * 📊 06/08/2026, 21:09. A tela `Admin → Operação → Saúde do sistema` mostrava:
 *
 *     erro:ImportError: 4510      em vermelho vivo
 *     erro:APIError:    5612      em vermelho vivo
 *
 * Os DOIS defeitos que produziram esses números já estavam corrigidos havia
 * horas. Nenhum deles estava acontecendo. O contador do Redis é acumulado: ele
 * soma desde que o servidor ligou e nunca zera. O painel lia esse total como se
 * fosse o presente.
 *
 * O Founder perguntou, com razão: *"erro no Saúde do sistema continua vermelho
 * e dando erro. Por que isso acontece?"*
 *
 * O backend já separava as duas coisas — `agora` (janela de 10 minutos, que
 * expira) e `total_desde_o_boot` (que só cresce). Quem achatava era a tela.
 *
 * POR QUE ISSO É GRAVE, E NÃO COSMÉTICO
 * =====================================
 * É o mesmo defeito que o próprio arquivo já documentava sobre o freio de
 * emergência: **vermelho que fica aceso para sempre é vermelho que se aprende
 * a ignorar.** Um painel de saúde que mente sobre o presente é pior que não
 * ter painel — ele dá a sensação de já ter olhado.
 *
 * O QUE ESTE ARQUIVO GUARDA
 * =========================
 * A regra `a cor vem da janela de agora`, exercitada como LÓGICA e não como
 * texto. Um guarda que só procura uma frase no arquivo fica verde por uma
 * linha que ninguém executa.
 */

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const RAIZ = join(dirname(fileURLToPath(import.meta.url)), '..');
const problemas = [];

function checar(condicao, oQue, evidencia = '') {
  const marca = condicao ? '  OK ' : '  X  ';
  console.log(`${marca} ${oQue}${evidencia ? `  (${evidencia})` : ''}`);
  if (!condicao) problemas.push(oQue);
}

// A REGRA VEM DO ARQUIVO QUE A TELA USA — não de uma cópia.
//
// A primeira versão deste teste duplicava a função aqui. A prova por mutação
// denunciou: quebrei a regra dentro da tela e o teste continuou verde, porque
// media a cópia. Um teste que testa a própria cópia do código mede a si mesmo.
import { lerContadores } from '../lib/saude-contadores.js';

console.log('='.repeat(70));
console.log('O VERMELHO DO PAINEL É DO AGORA, NÃO DO HISTÓRICO');
console.log('='.repeat(70));

console.log('\n[1] O caso real de 06/08 às 21:09');
// 📊 Os números exatos que estavam na tela do Founder.
const comoEstavaNaTela = {
  agora: { mensagem_nova: 12, ja_estava: 8 },
  total_desde_o_boot: {
    'erro:ImportError': 4510,
    'erro:APIError': 5612,
    'erro:RemoteProtocolError': 5,
    mensagem_nova: 1126,
    ja_estava: 1040,
  },
};
const lido = lerContadores(comoEstavaNaTela);
checar(lido.vermelho === false,
  'com 10.127 erros no histórico e ZERO agora: a linha fica VERDE',
  'os defeitos foram corrigidos; a tela precisa dizer isso');
checar(lido.errosNoTotal.length === 3,
  'e o histórico continua visível — apagado, não escondido',
  'esconder o passado tiraria a única pista de um defeito que volta');

console.log('\n[2] CONTROLE — o painel AINDA consegue ficar vermelho');
// Sem esta seção, "nunca pintar de vermelho" passaria no teste acima, e o
// painel viraria um enfeite que diz ok para tudo.
const errandoAgora = lerContadores({
  agora: { 'erro:APIError': 3, mensagem_nova: 1 },
  total_desde_o_boot: { 'erro:APIError': 5615 },
});
checar(errandoAgora.vermelho === true,
  'CONTROLE — 3 erros nos últimos 10 minutos: VERMELHO',
  errandoAgora.errosAgora.map(([k]) => k).join(', '));

const soUmErro = lerContadores({ agora: { 'erro:ImportError': 1 }, total_desde_o_boot: {} });
checar(soUmErro.vermelho === true,
  'CONTROLE — um único erro na janela já acende',
  'o limiar é 1, não uma média');

console.log('\n[3] CONTROLE — zero não é erro');
// O Redis devolve a chave com 0 quando o contador foi criado e zerado. Contar
// isso como erro reacenderia o vermelho para sempre por outro caminho.
const zerado = lerContadores({
  agora: { 'erro:APIError': 0, mensagem_nova: 5 },
  total_desde_o_boot: { 'erro:APIError': 5612 },
});
checar(zerado.vermelho === false,
  'CONTROLE — `erro:APIError: 0` na janela não acende nada',
  'zero erro é zero erro, mesmo com a chave presente');

console.log('\n[4] O formato antigo continua sendo entendido');
// Durante um deploy os dois formatos existem ao mesmo tempo. Um painel que
// quebra no meio do deploy é inútil justamente na hora em que se olha para ele.
const formatoAntigo = lerContadores({ 'erro:APIError': 12, mensagem_nova: 40 });
checar(formatoAntigo.vermelho === true,
  'servidor antigo (mapa achatado) ainda acende vermelho',
  'não dá para tratar servidor velho como servidor saudável');

const antigoLimpo = lerContadores({ mensagem_nova: 40, ja_estava: 3 });
checar(antigoLimpo.vermelho === false,
  'CONTROLE — e servidor antigo sem erro fica verde',
  'senão o suporte ao formato antigo seria "sempre vermelho"');

console.log('\n[5] A tela usa MESMO a janela de agora para escolher a cor');
// A checagem que impede este arquivo de virar teatro: as duas asserções acima
// exercitam uma cópia da regra. Esta confere que o componente aplica a regra.
const fonte = readFileSync(join(RAIZ, 'app/admin/saude/page.tsx'), 'utf8');
const comandos = fonte.split('\n').filter((l) => !l.trim().startsWith('*') && !l.trim().startsWith('//')).join('\n');

checar(comandos.includes('ContadoresDoEspelho'),
  'o componente dedicado existe');
// A regra vale para TODO mapa de contadores, não só para o do espelho: o
// próximo contador que alguém adicionar não pode herdar o vermelho eterno.
checar(/typeof valor === 'object'[\s\S]{0,900}<ContadoresDoEspelho/.test(comandos),
  'e o `Estado` genérico delega TODO mapa de contadores a ele',
  'conserto que vale para um caso é remendo');
checar(/errosAgora[\s\S]{0,400}bg-red-600/.test(comandos),
  'o vermelho é decidido por `errosAgora`',
  'e não por `Object.entries` do mapa inteiro');
const regra = readFileSync(join(RAIZ, 'lib/saude-contadores.js'), 'utf8');
checar(regra.includes('total_desde_o_boot'),
  'a regra entende o campo `total_desde_o_boot` do servidor');
checar(/errosNoTotal[\s\S]{0,400}text-muted-foreground/.test(comandos),
  'e a tela mostra o total apagado, como histórico',
  'esconder o passado tiraria a pista de um defeito que volta');
checar(!/chave\.startsWith\('erro'\)/.test(comandos.split('function Estado')[1] || ''),
  'CONTROLE — o `Estado` genérico não pinta mais contador de vermelho',
  'era ele que achatava agora e histórico na mesma cor');

console.log(`\n${'='.repeat(70)}`);
if (problemas.length) {
  console.log(`${problemas.length} PROBLEMA(S):`);
  problemas.forEach((p) => console.log(`  - ${p}`));
  process.exit(1);
}
console.log('TUDO VERDE — o painel fala do presente.');
process.exit(0);
