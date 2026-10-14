/**
 * SPEC-132-A · A1 — o Copiar de cada resposta. Copia o TEXTO LIMPO: sem `**`, `#`, crases e a sintaxe de link, e
 * com as tabelas em colunas separadas por tabulação (colam como tabela no Excel e no Google Planilhas, e como linhas
 * legíveis no WhatsApp). O modelo é o Copiar por mensagem do Open WebUI (SPEC §8.4).
 */
export function textoLimpoDoMarkdown(markdown: string): string {
  if (!markdown) return '';
  const linhas = markdown.replace(/\r\n?/g, '\n').split('\n');
  const saida: string[] = [];
  let dentroDeCodigo = false;

  for (const bruta of linhas) {
    if (/^\s*(```|~~~)/.test(bruta)) {
      dentroDeCodigo = !dentroDeCodigo;
      continue;
    }
    if (dentroDeCodigo) {
      saida.push(bruta);
      continue;
    }
    let linha = bruta;

    // tabela: a linha separadora some; as células viram colunas com tabulação
    if (/^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$/.test(linha) && linha.includes('-') && linha.includes('|')) continue;
    if (/^\s*\|.*\|\s*$/.test(linha)) {
      const celulas = linha.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map((c) => limparEmLinha(c.trim()));
      saida.push(celulas.join('\t'));
      continue;
    }

    linha = linha.replace(/^\s{0,3}#{1,6}\s+/, ''); // títulos
    linha = linha.replace(/^\s{0,3}>\s?/, ''); // citação
    linha = linha.replace(/^(\s*)[*+]\s+/, '$1- '); // marcadores viram "- "
    if (/^\s*([-*_])(\s*\1){2,}\s*$/.test(linha)) continue; // régua horizontal
    saida.push(limparEmLinha(linha));
  }

  return saida.join('\n').replace(/\n{3,}/g, '\n\n').trim();
}

function limparEmLinha(texto: string): string {
  return texto
    .replace(/!\[([^\]]*)\]\([^)]*\)/g, '$1') // imagem → o texto alternativo
    .replace(/\[([^\]]+)\]\(([^)\s]+)[^)]*\)/g, (_m, rotulo: string, url: string) => (rotulo === url ? url : `${rotulo} (${url})`))
    .replace(/`([^`]+)`/g, '$1')
    .replace(/(\*\*|__)(?=\S)([\s\S]*?\S)\1/g, '$2')
    .replace(/(^|[^\w*])\*(?=\S)([^*\n]*?\S)\*(?!\w)/g, '$1$2')
    .replace(/(^|[^\w_])_(?=\S)([^_\n]*?\S)_(?!\w)/g, '$1$2')
    .replace(/~~(?=\S)([\s\S]*?\S)~~/g, '$1')
    .replace(/<br\s*\/?>/gi, ' ');
}

/** Copia para a área de transferência. Sem a API moderna (http, navegador antigo), cai no `execCommand`. */
export async function copiarTexto(texto: string): Promise<boolean> {
  try {
    if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(texto);
      return true;
    }
  } catch {
    /* tenta o caminho antigo */
  }
  try {
    if (typeof document === 'undefined') return false;
    const area = document.createElement('textarea');
    area.value = texto;
    area.setAttribute('readonly', '');
    area.style.position = 'fixed';
    area.style.opacity = '0';
    document.body.appendChild(area);
    area.select();
    const ok = document.execCommand('copy');
    document.body.removeChild(area);
    return ok;
  } catch {
    return false;
  }
}
