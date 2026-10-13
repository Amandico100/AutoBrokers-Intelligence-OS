'use client';

import { useCallback, useEffect, useState } from 'react';

/**
 * SPEC-131-B G3 — o que "Meu perfil" lê da corretora ativa (`/api/dashboard/meu-perfil`): o MEU WhatsApp de trabalho,
 * as MINHAS ausências, as que eu cubro e as OUTRAS pessoas ativas da corretora (para escolher quem cobre).
 */
export type Ausencia = { id: string; de: string; ate: string; user_id: string; nome: string; ativa: boolean };
export type MeuPerfil = {
  whatsapp_trabalho: { numero: string | null; confirmado_em: string | null; confirmado: boolean; disponivel?: boolean };
  ausencias: Ausencia[];
  cubro: Ausencia[];
  pessoas: { user_id: string; nome: string }[];
  ausencia_disponivel?: boolean;
  duracao_maxima_dias?: number;
  eu: string;
  pode_gerir_todos: boolean;
};

export function useMeuPerfil() {
  const [perfil, setPerfil] = useState<MeuPerfil | null>(null);
  const [erro, setErro] = useState('');

  const carregar = useCallback(async () => {
    setErro('');
    try {
      const r = await fetch('/api/dashboard/meu-perfil', { cache: 'no-store' });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) { setErro('Não conseguimos carregar agora.'); return; }
      setPerfil(j as MeuPerfil);
    } catch {
      setErro('Não conseguimos carregar agora.');
    }
  }, []);

  useEffect(() => { carregar(); }, [carregar]);
  return { perfil, erro, carregar };
}

/** A frase de erro que veio do servidor (já em português) ou uma genérica. */
export async function fraseDoErro(res: Response, generica: string): Promise<string> {
  const j = await res.json().catch(() => ({}));
  if (typeof j?.detail === 'string') return j.detail;
  if (typeof j?.error === 'string' && /\s/.test(j.error)) return j.error;
  return generica;
}

export const dataBR = (iso: string) => {
  const [a, m, d] = iso.slice(0, 10).split('-');
  return a && m && d ? `${d}/${m}/${a}` : iso;
};
