'use client';

import { useCallback, useEffect, useState } from 'react';

import { ESFORCO_PADRAO, type Esforco } from './tipos';

/**
 * SPEC-132-A · A1 — o esforço do turno, lembrado POR APARELHO (D-132A-08).
 *
 * O MESMO modelo do papel `chat_principal`, com mais ou menos raciocínio (D-132A-04): Rápido = `low`,
 * Equilibrado = `medium` (o de hoje), Máximo = `high`. O backend só aceita os três (B8); a tela também.
 *
 * ⚠️ O `localStorage` pode não existir (aba anônima, dados bloqueados, captura de tela): toda leitura e escrita é
 * em try/catch, e o padrão é Equilibrado. Um valor estranho guardado ("turbo", JSON, vazio) também vira Equilibrado.
 */
export const ESFORCOS: { valor: Esforco; rotulo: string; descricao: string }[] = [
  { valor: 'rapido', rotulo: 'Rápido', descricao: 'Responde na hora' },
  { valor: 'equilibrado', rotulo: 'Equilibrado', descricao: 'O padrão' },
  { valor: 'maximo', rotulo: 'Máximo', descricao: 'Pensa mais, demora mais' },
];

export const CHAVE_DO_ESFORCO = 'autobrokers.chat.esforco';

export function ehEsforco(valor: unknown): valor is Esforco {
  return valor === 'rapido' || valor === 'equilibrado' || valor === 'maximo';
}

type Armazem = Pick<Storage, 'getItem' | 'setItem'>;

function armazemDoNavegador(): Armazem | null {
  try {
    return typeof window !== 'undefined' && window.localStorage ? window.localStorage : null;
  } catch {
    return null;
  }
}

/** O esforço salvo no aparelho — ou Equilibrado, se não há, se é inválido, ou se o armazém falha. */
export function lerEsforcoSalvo(armazem: Pick<Storage, 'getItem'> | null = armazemDoNavegador()): Esforco {
  try {
    const salvo = armazem ? armazem.getItem(CHAVE_DO_ESFORCO) : null;
    return ehEsforco(salvo) ? salvo : ESFORCO_PADRAO;
  } catch {
    return ESFORCO_PADRAO;
  }
}

export function guardarEsforco(esforco: Esforco, armazem: Pick<Storage, 'setItem'> | null = armazemDoNavegador()): void {
  try {
    armazem?.setItem(CHAVE_DO_ESFORCO, esforco);
  } catch {
    /* sem armazém: vale só nesta aba */
  }
}

export function rotuloDoEsforco(esforco: Esforco): string {
  return ESFORCOS.find((e) => e.valor === esforco)?.rotulo ?? 'Equilibrado';
}

/**
 * O estado nasce Equilibrado e lê o aparelho DEPOIS de montar — ler no primeiro render faria o HTML do servidor
 * (sempre Equilibrado) discordar do cliente, e o React avisaria de hidratação.
 */
export function useEsforco(): [Esforco, (e: Esforco) => void] {
  const [esforco, setEsforcoEstado] = useState<Esforco>(ESFORCO_PADRAO);

  useEffect(() => {
    setEsforcoEstado(lerEsforcoSalvo());
  }, []);

  const setEsforco = useCallback((e: Esforco) => {
    const valido = ehEsforco(e) ? e : ESFORCO_PADRAO;
    setEsforcoEstado(valido);
    guardarEsforco(valido);
  }, []);

  return [esforco, setEsforco];
}
