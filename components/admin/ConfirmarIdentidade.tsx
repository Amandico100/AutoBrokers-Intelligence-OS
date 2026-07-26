'use client';

// SPEC-061 §7.4 — a caixa que pede a senha antes de uma ação que não se desfaz.
//
// Ela aparece quando o Command Gateway responde 428 (`Precondition Required`).
// Esse código existe exatamente para isto: não é "você não pode" (403) nem
// "seu pedido está errado" (400) — é "falta um passo antes".
//
// O texto explica POR QUE está pedindo. Uma caixa de senha sem motivo parece
// erro do sistema, e a pessoa fecha.
import { useState } from 'react';

export default function ConfirmarIdentidade({
  aberto,
  oQue,
  onConfirmado,
  onCancelar,
}: {
  aberto: boolean;
  /** A ação que disparou o pedido, em português. Ex.: "suspender a corretora". */
  oQue?: string;
  onConfirmado: () => void;
  onCancelar: () => void;
}) {
  const [senha, setSenha] = useState('');
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  if (!aberto) return null;

  async function confirmar(e: React.FormEvent) {
    e.preventDefault();
    setEnviando(true);
    setErro(null);
    try {
      const r = await fetch('/api/admin/control-plane/step-up', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ senha }),
      });
      const j = await r.json().catch(() => ({}));
      if (r.ok && j?.ok) {
        // A senha sai da memória assim que serve. Não há motivo para mantê-la.
        setSenha('');
        onConfirmado();
      } else {
        setErro(j?.mensagem || 'Senha incorreta.');
      }
    } catch {
      setErro('Não foi possível confirmar agora.');
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <form
        onSubmit={confirmar}
        className="w-full max-w-md rounded-xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-950 p-6 shadow-xl"
      >
        <h2 className="text-lg font-semibold">Confirme que é você</h2>
        <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-2">
          {oQue
            ? `Você está prestes a ${oQue}. Essa ação não se desfaz.`
            : 'Esta ação não se desfaz.'}{' '}
          Digite sua senha para continuar.
        </p>

        <input
          type="password"
          autoFocus
          value={senha}
          onChange={(e) => setSenha(e.target.value)}
          placeholder="Sua senha"
          className="mt-4 w-full px-3 py-2 rounded-md border border-neutral-300 dark:border-neutral-700 bg-transparent"
        />

        {erro && <p className="text-sm text-red-600 dark:text-red-400 mt-2">{erro}</p>}

        <p className="text-xs text-neutral-500 mt-3">
          A confirmação vale por 15 minutos. Depois disso, pedimos de novo.
        </p>

        <div className="flex gap-2 justify-end mt-5">
          <button
            type="button"
            onClick={onCancelar}
            className="text-sm px-3 py-1.5 rounded-md border border-neutral-300 dark:border-neutral-700"
          >
            Cancelar
          </button>
          <button
            type="submit"
            disabled={enviando || !senha}
            className="text-sm px-3 py-1.5 rounded-md bg-neutral-900 text-white dark:bg-neutral-100 dark:text-neutral-900 disabled:opacity-40"
          >
            {enviando ? 'Confirmando…' : 'Confirmar'}
          </button>
        </div>
      </form>
    </div>
  );
}
