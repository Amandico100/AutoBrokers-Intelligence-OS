'use client';

import type { PropsDaAba } from '@/lib/auxiliaries/catalog';
import { ConfigurarCotacao } from '@/components/aplicativos/configurar/ConfigurarCotacaoEQcm';

/** SPEC-131-B G3 — a aba Configurar do aplicativo Cotação (slug `cotacao`): o que a antiga tela "Serviços" tinha para ela. */
export function AbaConfigurar(_props: Partial<PropsDaAba> = {}) {
  return <ConfigurarCotacao />;
}

export default AbaConfigurar;
