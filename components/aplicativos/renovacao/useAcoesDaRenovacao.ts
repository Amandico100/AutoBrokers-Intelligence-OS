'use client';

// SPEC-131-B · G2 — as três ações de uma renovação: Enviar pelo WhatsApp · Ver apresentação · Copiar a mensagem.
//
// ⛔ O PRODUTO NÃO ENVIA NADA. "Enviar pelo WhatsApp" pede ao backend o `wa.me` do cliente com a mensagem pronta e o
//    NAVEGADOR de quem clicou abre o WhatsApp DO APARELHO dele — a pessoa confere e toca enviar. O telefone só existe
//    dentro do link: esta tela não o mostra, não o guarda e não o registra.
// ⚠️ A janela nova é aberta NO CLIQUE (antes da resposta): aberta depois de um `await`, o bloqueador de pop-up a fecha.

import { useState } from 'react';

export type Resultado =
  | { tipo: 'aberto' }
  | { tipo: 'sem_telefone'; texto: string }
  | { tipo: 'copiado'; texto: string }
  | { tipo: 'copiar_a_mao'; texto: string }
  | { tipo: 'erro'; mensagem: string };

type Acao = 'enviar' | 'apresentar' | 'copiar';

async function postar(id: string, caminho: 'envio' | 'apresentacao', corpo?: object) {
  const res = await fetch(`/api/renovacoes/${encodeURIComponent(id)}/${caminho}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(corpo || {}),
    cache: 'no-store',
  });
  const j = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(typeof j?.error === 'string' ? j.error : 'Não deu certo agora. Tente de novo.');
  return j as Record<string, unknown>;
}

/** Abre uma aba em branco AGORA (no gesto do clique) e a solta do opener. Bloqueada → null (usa a mesma aba). */
function janelaNoClique(): Window | null {
  try {
    const w = window.open('', '_blank');
    if (w) w.opener = null;
    return w;
  } catch {
    return null;
  }
}

function irPara(janela: Window | null, url: string) {
  if (janela && !janela.closed) janela.location.href = url;
  else window.location.href = url;
}

export function useAcoesDaRenovacao(onMudou?: () => void) {
  const [ocupado, setOcupado] = useState<{ id: string; acao: Acao } | null>(null);
  const [resultado, setResultado] = useState<{ id: string; r: Resultado } | null>(null);

  const terminar = (id: string, r: Resultado) => {
    setResultado({ id, r });
    setOcupado(null);
    onMudou?.();
  };

  async function enviar(id: string) {
    if (ocupado) return;
    const janela = janelaNoClique();
    setOcupado({ id, acao: 'enviar' });
    try {
      const j = await postar(id, 'envio');
      if (typeof j.wa_me_url === 'string' && j.wa_me_url.startsWith('https://wa.me/')) {
        irPara(janela, j.wa_me_url);
        terminar(id, { tipo: 'aberto' });
      } else {
        janela?.close();
        terminar(id, { tipo: 'sem_telefone', texto: String(j.texto || '') });
      }
    } catch (e) {
      janela?.close();
      terminar(id, { tipo: 'erro', mensagem: (e as Error).message });
    }
  }

  async function apresentar(id: string) {
    if (ocupado) return;
    const janela = janelaNoClique();
    setOcupado({ id, acao: 'apresentar' });
    try {
      const j = await postar(id, 'apresentacao');
      const url = typeof j.url === 'string' ? j.url : '';
      if (!url) throw new Error('A apresentação não ficou pronta. Tente de novo.');
      irPara(janela, url);
      setOcupado(null);
      onMudou?.();
    } catch (e) {
      janela?.close();
      terminar(id, { tipo: 'erro', mensagem: (e as Error).message });
    }
  }

  /**
   * "Copiar a mensagem": a MESMA mensagem que vai no link. A cópia acontece no clique — o texto chega depois, por
   * isso o `ClipboardItem` com promessa (Safari exige o gesto); sem ele, `writeText` depois da resposta; e se o
   * navegador recusar as duas, o texto aparece na tela para copiar à mão.
   */
  async function copiar(id: string) {
    if (ocupado) return;
    setOcupado({ id, acao: 'copiar' });
    const pedido = postar(id, 'envio', { via: 'copiar' }).then((j) => {
      const t = String(j.texto || '');
      if (!t) throw new Error('A mensagem não ficou pronta. Tente de novo.');
      return t;
    });
    let texto = '';
    try {
      const podeComPromessa =
        typeof window !== 'undefined' && 'ClipboardItem' in window && Boolean(navigator.clipboard?.write);
      if (podeComPromessa) {
        const item = new ClipboardItem({
          'text/plain': pedido.then((t) => new Blob([t], { type: 'text/plain' })),
        });
        await navigator.clipboard.write([item]);
        texto = await pedido;
      } else {
        texto = await pedido;
        await navigator.clipboard.writeText(texto);
      }
      terminar(id, { tipo: 'copiado', texto });
    } catch (e) {
      try {
        texto = texto || (await pedido);
      } catch (e2) {
        terminar(id, { tipo: 'erro', mensagem: (e2 as Error).message });
        return;
      }
      try {
        await navigator.clipboard.writeText(texto);
        terminar(id, { tipo: 'copiado', texto });
      } catch {
        terminar(id, { tipo: 'copiar_a_mao', texto });
      }
      void e;
    }
  }

  return {
    enviar,
    apresentar,
    copiar,
    ocupado,
    resultado,
    limpar: () => setResultado(null),
  };
}
