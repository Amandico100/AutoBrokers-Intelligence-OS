'use client';

// SPEC-139 · L2 — o ESTADO do formulário de uma rotina, extraído do `PainelDeRotinas` (D-139-04). O modal do painel e
// a aba Configurar da Cobrança usam ESTE hook: o mesmo estado, os mesmos cliques (as funções puras de `formulario.ts`)
// e a MESMA gravação — um POST a `/api/dashboard/rotinas` com `corpoDaGravacao`. Nenhuma das duas telas monta corpo
// por conta própria; o teste dourado (`scripts/a-cobranca-na-casca.test.mjs`) cobra isso na fonte.

import { useCallback, useEffect, useMemo, useState } from 'react';

import {
  FORM_INICIAL,
  ROTA_DAS_ROTINAS,
  alternarDia as alternarDiaNoForm,
  alternarPortal as alternarPortalNoForm,
  comCampo,
  comCobranca,
  corpoDaGravacao,
  derivarDaCobranca,
  erroDaGravacao,
  formDaRotinaSalva,
  formDoModelo,
  formEmBranco,
  modeloDoAplicativo,
  motivoParaNaoSalvar,
  portaisDaResposta,
  type Edicao,
  type FormDaRotina,
  type ModeloDeRotina,
  type PortalOpcao,
} from './formulario';

export interface ResultadoDaGravacao {
  ok: boolean;
  /** o status HTTP (0 = sem conexão) */
  status: number;
  erro?: string;
}

export function useFormularioDaRotina({ auxiliarSlug, auxiliarNome }: { auxiliarSlug: string; auxiliarNome: string }) {
  const [form, setForm] = useState<FormDaRotina>(FORM_INICIAL);
  const [editing, setEditing] = useState<Edicao | null>(null);
  const [saving, setSaving] = useState(false);
  const [portais, setPortais] = useState<PortalOpcao[]>([]);
  // O backend não conseguiu confirmar contra o runtime implantado. A tela avisa em vez de fingir que sabe.
  const [cobrancaDegradada, setCobrancaDegradada] = useState(false);

  // As seguradoras que ESTA corretora conectou. Uma chamada só, na montagem: a lista muda em Conectores, não aqui.
  useEffect(() => {
    let vivo = true;
    (async () => {
      try {
        const res = await fetch('/api/dashboard/portal-credentials', { cache: 'no-store' });
        const j = await res.json();
        if (!vivo || !res.ok) return;
        const { portais: lidos, degradada } = portaisDaResposta(j);
        setCobrancaDegradada(degradada);
        setPortais(lidos);
      } catch {
        if (vivo) setPortais([]);
      }
    })();
    return () => { vivo = false; };
  }, []);

  /** O modelo de rotina deste aplicativo, pelo `kind` (sobrevive a reseed do template). */
  const carregarModelo = useCallback(async (): Promise<ModeloDeRotina | null> => {
    try {
      const res = await fetch('/api/dashboard/routine-templates', { cache: 'no-store' });
      const j = await res.json();
      return modeloDoAplicativo((j.templates || []) as ModeloDeRotina[], auxiliarSlug);
    } catch {
      return null; // o corretor ainda pode criar do zero
    }
  }, [auxiliarSlug]);

  /**
   * Abre o formulário: uma rotina que existe (como está gravada) ou uma nova — que NASCE PREENCHIDA pelo modelo do
   * aplicativo (SPEC-078 D). Devolve o estado aberto, para quem precisa guardá-lo como base (o "Descartar").
   */
  const abrir = useCallback(async (r: Edicao): Promise<FormDaRotina> => {
    let novo: FormDaRotina;
    if (r === 'new') {
      const modelo = await carregarModelo();
      novo = modelo ? formDoModelo(modelo, auxiliarNome) : formEmBranco(auxiliarNome);
    } else {
      novo = formDaRotinaSalva(r);
    }
    setForm(novo);
    setEditing(r);
    return novo;
  }, [auxiliarNome, carregarModelo]);

  const fechar = useCallback(() => setEditing(null), []);

  const derivados = useMemo(() => derivarDaCobranca(form, portais), [form, portais]);

  // Os cliques: cada um é uma função pura de `formulario.ts`.
  const setBillingConfig = useCallback((patch: Record<string, unknown>) => setForm((f) => comCobranca(f, patch)), []);
  const mudar = useCallback((patch: Partial<FormDaRotina>) => setForm((f) => comCampo(f, patch)), []);
  const alternarPortal = useCallback(
    (key: string, marcado: boolean) => setForm((f) => alternarPortalNoForm(f, portais, key, marcado)),
    [portais],
  );
  const alternarDia = useCallback((valor: number) => setForm((f) => alternarDiaNoForm(f, valor)), []);
  /** Volta a um estado guardado (o "Descartar" do Configurar). */
  const restaurar = useCallback((f: FormDaRotina) => setForm(f), []);

  const motivo = motivoParaNaoSalvar(form, portais);

  /** Grava na ÚNICA rota das rotinas, com o corpo de `corpoDaGravacao`. Quem chama decide o que fazer depois. */
  const salvar = useCallback(async (): Promise<ResultadoDaGravacao> => {
    if (!editing) return { ok: false, status: 0, erro: 'Nada aberto para salvar.' };
    setSaving(true);
    try {
      const res = await fetch(ROTA_DAS_ROTINAS, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(corpoDaGravacao(form, editing, auxiliarSlug, portais)),
      });
      const j = await res.json().catch(() => ({}));
      if (!res.ok) return { ok: false, status: res.status, erro: erroDaGravacao(j) };
      return { ok: true, status: res.status };
    } catch {
      return { ok: false, status: 0, erro: 'Sem conexão com o servidor agora. Tente de novo em instantes.' };
    } finally {
      setSaving(false);
    }
  }, [editing, form, auxiliarSlug, portais]);

  return {
    form, editing, saving, portais, cobrancaDegradada, derivados, motivo,
    abrir, fechar, setBillingConfig, mudar, alternarPortal, alternarDia, restaurar, salvar,
  };
}

export type FormularioDaRotinaAberto = ReturnType<typeof useFormularioDaRotina>;
