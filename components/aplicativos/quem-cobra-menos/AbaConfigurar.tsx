'use client';

import type { PropsDaAba } from '@/lib/auxiliaries/catalog';
import { ConfigurarQcm } from '@/components/aplicativos/configurar/ConfigurarCotacaoEQcm';

/** SPEC-131-B G3 — a aba Configurar do aplicativo Quem Cobra Menos (slug `quem-cobra-menos`): só leitura — é o canal. */
export function AbaConfigurar(_props: Partial<PropsDaAba> = {}) {
  return <ConfigurarQcm />;
}

export default AbaConfigurar;
