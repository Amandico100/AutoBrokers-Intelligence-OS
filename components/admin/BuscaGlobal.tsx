'use client';

// SPEC-061 §11.3 — command palette.
//
// Com oito hubs e ~40 telas, procurar no menu ainda custa. A busca resolve o
// caso em que a pessoa **já sabe o que quer** e só precisa chegar lá — que é a
// maioria das vezes depois da primeira semana.
//
// Ela é governada: o servidor só procura no que a pessoa pode ver, e devolve
// DESTINO, nunca conteúdo. Uma busca que devolvesse trecho de conversa seria um
// vazamento com aparência de conveniência.
import { useCallback, useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';

type Resultado = { tipo: string; titulo: string; detalhe?: string; href: string };

export default function BuscaGlobal() {
  const router = useRouter();
  const [aberto, setAberto] = useState(false);
  const [termo, setTermo] = useState('');
  const [resultados, setResultados] = useState<Resultado[]>([]);
  const [ativo, setAtivo] = useState(0);
  const campo = useRef<HTMLInputElement>(null);

  // Ctrl+K / Cmd+K abre; Esc fecha. É a convenção que a pessoa já traz de
  // outras ferramentas — inventar um atalho próprio seria uma coisa a mais
  // para aprender.
  useEffect(() => {
    function tecla(e: KeyboardEvent) {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setAberto((v) => !v);
      }
      if (e.key === 'Escape') setAberto(false);
    }
    window.addEventListener('keydown', tecla);
    return () => window.removeEventListener('keydown', tecla);
  }, []);

  useEffect(() => {
    if (aberto) setTimeout(() => campo.current?.focus(), 30);
    else {
      setTermo('');
      setResultados([]);
      setAtivo(0);
    }
  }, [aberto]);

  const procurar = useCallback(async (q: string) => {
    if (q.trim().length < 2) {
      setResultados([]);
      return;
    }
    try {
      const r = await fetch(`/api/admin/control-plane/search?q=${encodeURIComponent(q)}`, {
        cache: 'no-store',
      });
      const j = await r.json();
      setResultados(j?.resultados ?? []);
      setAtivo(0);
    } catch {
      setResultados([]);
    }
  }, []);

  // Espera a pessoa parar de digitar. Sem isso, uma palavra de oito letras
  // dispara oito consultas e as respostas chegam fora de ordem.
  useEffect(() => {
    const t = setTimeout(() => procurar(termo), 180);
    return () => clearTimeout(t);
  }, [termo, procurar]);

  function irPara(r: Resultado) {
    setAberto(false);
    router.push(r.href);
  }

  if (!aberto) {
    return (
      <button
        onClick={() => setAberto(true)}
        className="w-full text-left text-sm px-3 py-2 rounded-md border border-neutral-300 dark:border-neutral-700 text-neutral-500 hover:bg-neutral-50 dark:hover:bg-neutral-900"
      >
        Buscar… <span className="float-right text-xs opacity-60">Ctrl K</span>
      </button>
    );
  }

  return (
    <div
      className="fixed inset-0 z-50 bg-black/40 p-4 pt-[12vh]"
      onClick={() => setAberto(false)}
    >
      <div
        className="mx-auto max-w-xl rounded-xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-950 shadow-xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <input
          ref={campo}
          value={termo}
          onChange={(e) => setTermo(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'ArrowDown') {
              e.preventDefault();
              setAtivo((i) => Math.min(i + 1, resultados.length - 1));
            }
            if (e.key === 'ArrowUp') {
              e.preventDefault();
              setAtivo((i) => Math.max(i - 1, 0));
            }
            if (e.key === 'Enter' && resultados[ativo]) irPara(resultados[ativo]);
          }}
          placeholder="Corretora, Skill, ferramenta ou tela…"
          className="w-full px-4 py-3 bg-transparent border-b border-neutral-200 dark:border-neutral-800 outline-none"
        />

        {termo.trim().length >= 2 && resultados.length === 0 && (
          <p className="px-4 py-6 text-sm text-neutral-500">Nada encontrado.</p>
        )}

        <ul className="max-h-80 overflow-y-auto">
          {resultados.map((r, i) => (
            <li key={`${r.tipo}-${r.titulo}-${i}`}>
              <button
                onMouseEnter={() => setAtivo(i)}
                onClick={() => irPara(r)}
                className={`w-full text-left px-4 py-2.5 flex items-center gap-3 ${
                  i === ativo ? 'bg-neutral-100 dark:bg-neutral-900' : ''
                }`}
              >
                <span className="text-xs px-2 py-0.5 rounded bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400 shrink-0">
                  {r.tipo}
                </span>
                <span className="min-w-0">
                  <span className="block truncate">{r.titulo}</span>
                  {r.detalhe && (
                    <span className="block text-xs text-neutral-500 font-mono truncate">
                      {r.detalhe}
                    </span>
                  )}
                </span>
              </button>
            </li>
          ))}
        </ul>

        <p className="px-4 py-2 text-xs text-neutral-500 border-t border-neutral-200 dark:border-neutral-800">
          ↑↓ para navegar · Enter para abrir · Esc para fechar
        </p>
      </div>
    </div>
  );
}
