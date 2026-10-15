'use client';

// SPEC-EXTRA-001.3 — BLOCO B · "Números que o agente nunca atende".
//
// D-PILOTO-09 é lei: este sub-bloco mora no card **Equipe**, abaixo da lista de
// membros — não no card Agente e não num card próprio (nota 88 × 62 × 71).
//
// 🔴 O que faz este bloco existir é o EFEITO QUÁDRUPLO, e a frase abaixo é o
// produto: a corretora precisa saber o que acontece quando ela cadastra um
// número, sem ter de perguntar ao suporte.
//
// ⚠️ Os telefones dos MEMBROS aparecem em modo LEITURA, com a origem escrita:
// eles vêm do cadastro da pessoa, e editar o membro é que muda o número. Uma
// segunda verdade sobre o mesmo fato é exatamente o defeito de `alert_target`
// (três escritores, três formas).

import { useCallback, useEffect, useState } from 'react';
import { Loader2, Plus, X } from 'lucide-react';

type Numero = { id: string; label: string; kind: string; phone_mascarado: string };
type MembroComFone = { id: string; nome: string; phone_mascarado: string };

const TIPOS: Array<{ v: string; rotulo: string }> = [
  { v: 'fixo', rotulo: 'Fixo da loja' },
  { v: 'comercial', rotulo: 'Comercial' },
  { v: 'socio', rotulo: 'Sócio' },
  { v: 'outro', rotulo: 'Outro' },
];

const inputCls =
  'mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground';

export function NumerosDaCasa() {
  const [numeros, setNumeros] = useState<Numero[] | null>(null);
  const [membros, setMembros] = useState<MembroComFone[]>([]);
  const [abrindo, setAbrindo] = useState(false);
  const [form, setForm] = useState<Record<string, string>>({ kind: 'fixo' });
  const [busy, setBusy] = useState(false);
  const [aviso, setAviso] = useState('');

  const carregar = useCallback(async () => {
    try {
      const j = await fetch('/api/dashboard/internal-numbers', { cache: 'no-store' }).then((r) =>
        r.json(),
      );
      if (j?.ok) {
        setNumeros(j.numeros || []);
        setMembros(j.membros || []);
      } else {
        setNumeros([]);
      }
    } catch {
      setNumeros([]);
    }
  }, []);
  useEffect(() => {
    carregar();
  }, [carregar]);

  const salvar = async () => {
    setBusy(true);
    setAviso('');
    try {
      const r = await fetch('/api/dashboard/internal-numbers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone: form.phone, label: form.label, kind: form.kind || 'outro' }),
      });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) {
        // ⚠️ A frase que volta do servidor é a que a pessoa lê. ⛔ Nunca um
        // código de erro cru na tela.
        setAviso(String(j?.error || 'Não consegui salvar agora.'));
        return;
      }
      setForm({ kind: 'fixo' });
      setAbrindo(false);
      await carregar();
    } finally {
      setBusy(false);
    }
  };

  const remover = async (id: string) => {
    setBusy(true);
    try {
      await fetch(`/api/dashboard/internal-numbers?id=${encodeURIComponent(id)}`, {
        method: 'DELETE',
      });
      await carregar();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mt-6 rounded-xl border border-border bg-card p-4">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-sm font-medium text-foreground">
          Números que o agente nunca atende
        </h3>
        <button
          onClick={() => setAbrindo((v) => !v)}
          className="inline-flex items-center gap-1.5 rounded-lg border border-primary/40 bg-brand-soft px-2.5 py-1.5 text-xs font-medium text-primary"
        >
          {abrindo ? <X className="h-3.5 w-3.5" /> : <Plus className="h-3.5 w-3.5" />}
          {abrindo ? 'Cancelar' : 'Adicionar número'}
        </button>
      </div>

      {/* 💭 A frase que explica, e ela é o produto. */}
      <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
        O agente nunca responde a estes números, nunca abre caso para eles e nunca fala sobre eles
        no grupo. Use para o fixo da loja, o comercial e os celulares de quem não tem login aqui.
      </p>

      {abrindo && (
        <div className="mt-3 space-y-2 rounded-lg border border-border/70 bg-background/60 p-3">
          <label className="block text-[12px]">
            <span className="text-muted-foreground">Telefone com DDD</span>
            <input
              value={form.phone || ''}
              onChange={(e) => setForm((p) => ({ ...p, phone: e.target.value }))}
              placeholder="47 99999-0001"
              className={inputCls}
            />
          </label>
          <label className="block text-[12px]">
            <span className="text-muted-foreground">Como você chama este número</span>
            <input
              value={form.label || ''}
              onChange={(e) => setForm((p) => ({ ...p, label: e.target.value }))}
              placeholder="fixo da loja"
              className={inputCls}
            />
          </label>
          <label className="block text-[12px]">
            <span className="text-muted-foreground">Tipo</span>
            <select
              value={form.kind || 'fixo'}
              onChange={(e) => setForm((p) => ({ ...p, kind: e.target.value }))}
              className={inputCls}
            >
              {TIPOS.map((t) => (
                <option key={t.v} value={t.v}>
                  {t.rotulo}
                </option>
              ))}
            </select>
          </label>
          {aviso && <p className="text-xs text-red-500">{aviso}</p>}
          <button
            onClick={salvar}
            disabled={busy}
            className="inline-flex items-center gap-1.5 rounded-lg border border-primary/40 bg-brand-soft px-3 py-2 text-sm font-medium text-primary disabled:opacity-50"
          >
            {busy && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            Adicionar
          </button>
        </div>
      )}

      <ul className="mt-3 space-y-1.5">
        {(numeros || []).map((n) => (
          <li
            key={n.id}
            className="flex items-center justify-between gap-3 rounded-lg border border-border/60 px-3 py-2 text-sm"
          >
            <span className="text-foreground">
              {n.label} <span className="text-muted-foreground">· {n.phone_mascarado}</span>
            </span>
            <button
              onClick={() => remover(n.id)}
              disabled={busy}
              className="text-xs text-red-500 transition-colors hover:underline disabled:opacity-50"
            >
              remover
            </button>
          </li>
        ))}
        {numeros !== null && numeros.length === 0 && (
          <li className="rounded-lg border border-dashed border-border/60 px-3 py-3 text-xs text-muted-foreground">
            Nenhum número cadastrado ainda.
          </li>
        )}
      </ul>

      {membros.length > 0 && (
        <div className="mt-4 border-t border-border/60 pt-3">
          <p className="text-[12px] font-medium text-foreground">
            Telefones da equipe, já incluídos
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            Estes vêm do cadastro de cada pessoa. Para mudar um deles, edite o membro na lista
            acima.
          </p>
          <ul className="mt-2 flex flex-wrap gap-1.5">
            {membros.map((m) => (
              <li
                key={m.id}
                className="rounded-md border border-border/60 px-2 py-1 text-[11px] text-muted-foreground"
              >
                {m.nome || 'membro'} · {m.phone_mascarado}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
