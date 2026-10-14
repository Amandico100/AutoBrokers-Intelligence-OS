'use client';

import { useCallback, useEffect, useState } from 'react';

/**
 * SPEC-131-B G3 — a configuração de cada aplicativo (Cotação · Renovação · Quem Cobra Menos) lida e gravada pela MESMA
 * rota da antiga tela "Serviços" (`/api/dashboard/servicos` → `/api/servicos-da-corretora` → `multicalculo_config`,
 * lida pelo único leitor `config.py`). O backend não mudou de lugar; só a tela mudou de casa (D-131-06).
 * Nenhum número comercial aqui: padrões e faixas chegam do backend.
 */
export type Modo = 'calcular' | 'calcular_entregar' | 'calcular_entregar_negociar';
export type Excecao = { ramo?: string; valor_acima_de?: number; modo: Modo };
export type Preferencias = Record<string, (string | number)[]>;
export type Servico = 'cotacao' | 'renovacao' | 'qcm';
export type Efetivo = {
  modo: Modo;
  excecoes_do_modo: Excecao[];
  preferencias_de_seguradoras: Preferencias;
  conta_global_se_vence_em_dias?: number;
  antecedencia_dias?: number;
  reajuste_basica_pct?: Record<string, number | null>;
  opcoes?: string[];
  teto_por_conta_noite?: number;
  antecipar_ate_dias?: number;
  /** SPEC-131-B G5 — "Com qual conta" (D-131-04): o Agger do responsável (padrão) ou sempre o da corretora */
  conta?: ContaDaRenovacao;
  /** SPEC-132-B · B3 — a Cotação Rápida: TODAS as regras efetivas do cálculo (os mesmos leitores do motor e da página) */
  regras?: RegrasDaCotacao;
};
/** SPEC-132-B · B3 (D-132B-06) — as regras do cálculo da cotação como o backend as lê (`servicos_da_corretora._regras_da_cotacao`). */
export type RegrasDaCotacao = {
  comissao: { entrada?: number; autonomo_minimo?: number; piso?: number; passo_pp?: number; teto_pct?: number };
  comissao_por_ramo: Record<string, number | null>;
  validade_dias?: number;
  validade_por_seguradora: Record<string, number>;
  opcoes_no_whatsapp?: number;
  opcoes_na_pagina?: number;
  calculo_por_papel: Record<string, string>;
  alvo_abaixo_da_atual_pct: { minimo?: number; maximo?: number };
  ordem_do_mais_barato: string[];
  cortes_de_cobertura: Record<string, string>;
  coberturas_essenciais: Record<string, string[]>;
};
export type ContaDaRenovacao = 'responsavel' | 'corretora';
export type DadosServicos = {
  qcm_aderido: boolean;
  servicos: Servico[];
  editaveis: Servico[];
  ramos: { codigo: string; nome: string }[];
  comum: { preferencias_de_seguradoras: Preferencias };
  sobreposto: { servicos: Partial<Record<Servico, Record<string, unknown>>>; preferencias_de_seguradoras?: Preferencias | null };
  efetivo: Partial<Record<Servico, Efetivo>>;
  padrao: Partial<Record<Servico, Efetivo>>;
  faixas: {
    antecedencia_dias_max: number;
    conta_global_dias_max: number;
    teto_por_conta_noite?: [number, number];
    antecipar_ate_dias?: [number, number];
    opcoes_da_renovacao?: string[];
    contas_da_renovacao?: ContaDaRenovacao[];
    /** SPEC-132-B · B3 — o que a cotação pode calcular e as faixas de comissão de entrada e de validade */
    opcoes_da_cotacao?: string[];
    comissao_entrada_da_cotacao?: [number, number];
    validade_dias_da_cotacao?: [number, number];
  };
  /** SPEC-132-B · B3 — o que o backend JÁ aceita gravar na cotação (opcoes · comissao · validade); o resto só se mostra */
  editaveis_da_cotacao?: string[];
  versao?: string | null;
};

export const NOME_DO_SERVICO: Record<Servico, string> = {
  cotacao: 'Cotação Rápida',
  renovacao: 'Renovação Automática',
  qcm: 'Quem Cobra Menos',
};

export const reais = (v: number) =>
  v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 });

/** Uma cópia funda (o rascunho nunca divide objeto com o que veio do servidor). */
export const copia = <T,>(v: T): T => JSON.parse(JSON.stringify(v ?? null));

/** Leitura e gravação da config dos serviços. `salvar` devolve `true` quando gravou. */
export function useServicos() {
  const [dados, setDados] = useState<DadosServicos | null>(null);
  const [erro, setErro] = useState('');
  const [salvando, setSalvando] = useState(false);
  const [aviso, setAviso] = useState('');
  const [conflito, setConflito] = useState(false);

  const aplicar = useCallback((j: { servicos?: DadosServicos } | DadosServicos) => {
    const d = ('efetivo' in j ? j : j.servicos) as DadosServicos | undefined;
    if (d && d.efetivo) { setDados(d); setConflito(false); }
  }, []);

  const carregar = useCallback(() => {
    setErro('');
    fetch('/api/dashboard/servicos', { cache: 'no-store' })
      .then(async (r) => {
        const j = await r.json().catch(() => ({}));
        if (!r.ok) throw new Error(typeof j?.detail === 'string' ? j.detail : j?.error || '');
        aplicar(j);
      })
      .catch(() => setErro('Não conseguimos carregar a configuração agora.'));
  }, [aplicar]);

  useEffect(() => { carregar(); }, [carregar]);

  const salvar = useCallback(async (corpo: Record<string, unknown>, ok: string): Promise<boolean> => {
    if (!dados) return false;
    setAviso(''); setConflito(false); setSalvando(true);
    try {
      const res = await fetch('/api/dashboard/servicos', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...corpo, versao: dados.versao ?? null }),
      });
      const j = await res.json().catch(() => ({}));
      if (!res.ok) {
        if (res.status === 409) { setConflito(true); setAviso('Outra pessoa salvou antes. Recarregue para ver o que mudou.'); }
        else if (res.status === 403) setAviso('Só um administrador da corretora muda estas regras.');
        else setAviso(typeof j?.detail === 'string' ? j.detail : 'Não conseguimos salvar agora. Nada mudou.');
        return false;
      }
      aplicar(j);
      setAviso(ok);
      return true;
    } catch {
      setAviso('Não conseguimos salvar agora. Nada mudou.');
      return false;
    } finally {
      setSalvando(false);
    }
  }, [dados, aplicar]);

  return { dados, erro, carregar, salvar, salvando, aviso, setAviso, conflito };
}

/** Quem pode mudar as regras (só para a tela esconder a barra; quem decide é o servidor, pelo porteiro). */
export function usePodeGerir(): boolean | null {
  const [pode, setPode] = useState<boolean | null>(null);
  useEffect(() => {
    fetch('/api/dashboard/aggers-da-equipe', { cache: 'no-store' })
      .then((r) => r.json().catch(() => ({})))
      .then((j) => setPode(Boolean(j?.pode_gerir_todos)))
      .catch(() => setPode(false));
  }, []);
  return pode;
}
