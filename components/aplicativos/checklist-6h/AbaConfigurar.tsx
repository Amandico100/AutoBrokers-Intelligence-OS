'use client';

// SPEC-139 · L3 (P-16) — a aba Configurar do aplicativo Checklist das 6h (`/dashboard/auxiliares/checklist-6h?aba=configurar`).
// O conteúdo é a antiga sub-aba "Preferências" da tela `app/dashboard/auxiliares/checklist-6h/hoje/page.tsx`, MOVIDO
// (não reescrito): a mesma leitura (`/api/dashboard/briefing?aba=preferencias`) e a MESMA gravação (`POST
// /api/dashboard/briefing` com `acao: 'preferencias'`, o mesmo corpo). O `company_id` vem da sessão, na rota — nunca
// daqui. Carregada pela casca por import dinâmico (ABAS_DO_APLICATIVO).

import { useCallback, useEffect, useState } from 'react';

import { BOTAO_PRIMARIO } from '@/components/aplicativos/casca/CardDoAplicativo';

export default function AbaConfigurar() {
  const [dados, setDados] = useState<any>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState('');

  const carregar = useCallback(async (qual: string) => {
    setCarregando(true);
    setErro('');
    try {
      const j = await fetch(`/api/dashboard/briefing?aba=${qual}`).then((r) => r.json());
      if (j?.ok === false) setErro(j.error || 'Não foi possível carregar.');
      setDados(j);
    } catch {
      setErro('Não foi possível carregar o briefing.');
    }
    setCarregando(false);
  }, []);

  useEffect(() => {
    carregar('preferencias');
  }, [carregar]);

  const agir = useCallback(
    async (corpo: Record<string, unknown>) => {
      try {
        await fetch('/api/dashboard/briefing', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(corpo),
        });
        await carregar('preferencias');
      } catch {
        setErro('A ação não foi registrada. Tente de novo.');
      }
    },
    [carregar],
  );

  return (
    <div className="space-y-5">
      {erro && (
        <p className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-foreground">
          {erro}
        </p>
      )}

      {carregando ? (
        <div className="rounded-xl border border-border bg-card p-10 text-center text-sm text-muted-foreground">
          Carregando…
        </div>
      ) : (
        <Preferencias dados={dados} agir={agir} />
      )}
    </div>
  );
}

// ==========================================================================
function Preferencias({
  dados,
  agir,
}: {
  dados: any;
  agir: (c: Record<string, unknown>) => void;
}) {
  const perfil = dados?.perfil?.perfil ?? {};
  const [horario, setHorario] = useState<string>(perfil?.schedule_spec?.time || '08:00');
  const [detalhe, setDetalhe] = useState<string>(perfil?.detail_level || 'standard');
  const [maxPush, setMaxPush] = useState<number>(Number(perfil?.max_pushes_per_day ?? 3));
  const [ativo, setAtivo] = useState<boolean>(perfil?.is_active !== false);
  const [salvo, setSalvo] = useState(false);

  async function salvar() {
    await agir({
      acao: 'preferencias',
      cadencia: 'daily',
      campos: {
        schedule_spec: { time: horario },
        detail_level: detalhe,
        max_pushes_per_day: maxPush,
        is_active: ativo,
      },
    });
    setSalvo(true);
    setTimeout(() => setSalvo(false), 2500);
  }

  return (
    <div className="space-y-5">
      <section className="rounded-xl border border-border bg-card p-5">
        <h2 className="text-sm font-semibold text-foreground">Como você quer receber</h2>
        <p className="mt-1 text-xs text-muted-foreground">
          Fora do horário combinado, só assunto crítico interrompe. O resto espera o próximo
          briefing.
        </p>

        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <label className="block">
            <span className="text-xs font-medium text-foreground">Horário do briefing diário</span>
            <input
              type="time"
              value={horario}
              onChange={(e) => setHorario(e.target.value)}
              className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground"
            />
          </label>

          <label className="block">
            <span className="text-xs font-medium text-foreground">Nível de detalhe</span>
            <select
              value={detalhe}
              onChange={(e) => setDetalhe(e.target.value)}
              className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground"
            >
              <option value="minimal">Só o essencial</option>
              <option value="standard">Padrão</option>
              <option value="detailed">Detalhado</option>
            </select>
          </label>

          <label className="block">
            <span className="text-xs font-medium text-foreground">
              Máximo de avisos por dia (fora do briefing)
            </span>
            <input
              type="number"
              min={0}
              max={20}
              value={maxPush}
              onChange={(e) => setMaxPush(Number(e.target.value))}
              className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground"
            />
          </label>

          <label className="flex items-center gap-2 self-end">
            <input
              type="checkbox"
              checked={ativo}
              onChange={(e) => setAtivo(e.target.checked)}
              className="h-4 w-4"
            />
            <span className="text-sm text-foreground">Briefing diário ligado</span>
          </label>
        </div>

        <div className="mt-4 flex items-center gap-3">
          <button
            onClick={salvar}
            className={`inline-flex h-11 items-center rounded-lg px-4 text-sm font-medium sm:h-9 ${BOTAO_PRIMARIO}`}
          >
            Salvar
          </button>
          {salvo && <span className="text-xs text-muted-foreground">Salvo.</span>}
        </div>

        <p className="mt-4 text-xs text-muted-foreground">
          Alerta de segurança e risco crítico continua chegando mesmo com o briefing pausado.
        </p>
      </section>
    </div>
  );
}
