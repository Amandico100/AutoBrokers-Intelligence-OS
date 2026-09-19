'use client';

// SPEC-036 Etapa 2 / SPEC-050 — a corretora alimenta o próprio cérebro.
// SPEC-050: sem "qual assistente vai usar" (o conhecimento é da corretora e
// TODOS os assistentes usam automaticamente) e lista em linguagem humana —
// nome legível, origem, status em português. Zero jargão técnico.

import { useCallback, useEffect, useRef, useState } from 'react';
import { FileText, Loader2 } from 'lucide-react';
// SPEC-EXTRA-001.5 BLOCO D — a base GLOBAL de planos de assistência ao lado do
// conhecimento da corretora. São duas coisas diferentes na mesma tela, e a
// legenda de cada bloco diz qual é qual: o que ESTA corretora subiu, e o que o
// mercado inteiro escreveu nas condições gerais.
import { CoberturaDePlanos } from './CoberturaDePlanos';
import { FilaDeCuradoria } from './FilaDeCuradoria';

type Doc = { file_name: string; file_type: string | null; status: string; scope: string; knowledge_class: string | null; visibility: string | null; chunks: number; created_at: string | null };
type Data = { documents: Doc[]; total: number; ready: number };

function statusInfo(s: string): { label: string; cls: string } {
  if (/ready|done|completed|processed|ingested/i.test(s)) return { label: 'Pronto para uso', cls: 'text-emerald-600' };
  if (/error|fail/i.test(s)) return { label: 'Falhou — envie de novo', cls: 'text-red-600' };
  return { label: 'Processando…', cls: 'text-amber-600' };
}

/** Nome/origem legíveis. Apólices importadas do sistema da corretora chegam
 * como "infocap-policy-<código>.pdf" — humano nenhum reconhece isso. */
function humanize(doc: Doc): { title: string; source: string } {
  const name = doc.file_name || 'Documento';
  const m = name.match(/^infocap-policy-([0-9a-f]{6})/i);
  if (m) {
    return {
      title: `Apólice do sistema da corretora (…${m[1]})`,
      source: 'Importada automaticamente da InfoCap durante um atendimento',
    };
  }
  const cleaned = name.replace(/\.(pdf|docx|txt|md|csv)$/i, '').replace(/[-_]+/g, ' ').trim();
  const source = doc.scope === 'personal'
    ? 'Só você vê este documento'
    : doc.knowledge_class === 'connector' || /^connector$/i.test(String(doc.visibility || ''))
      ? 'Importado automaticamente por um conector'
      : 'Enviado pela equipe da corretora';
  return { title: cleaned.charAt(0).toUpperCase() + cleaned.slice(1), source };
}

function fmtWhen(iso: string | null): string {
  if (!iso) return '';
  return new Date(iso).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: '2-digit' });
}

export function KnowledgeClient() {
  const [d, setD] = useState<Data | null>(null);
  const [target, setTarget] = useState<'company' | 'personal'>('company');
  const [file, setFile] = useState<File | null>(null);
  const [sending, setSending] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [planos, setPlanos] = useState<any | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const load = useCallback(() => {
    fetch('/api/dashboard/knowledge').then((r) => r.json()).then((j) => { if (j?.ok) setD(j); }).catch(() => {});
  }, []);

  const loadPlanos = useCallback(() => {
    fetch('/api/dashboard/knowledge/planos')
      .then((r) => r.json())
      .then((j) => { if (j?.ok) setPlanos(j); })
      .catch(() => {});
  }, []);

  useEffect(() => { load(); loadPlanos(); }, [load, loadPlanos]);

  const send = async () => {
    if (!file || sending) return;
    setSending(true);
    setMsg(null);
    try {
      const fd = new FormData();
      fd.set('file', file);
      fd.set('target', target); // SPEC-044: corretora (todos) ou pessoal (só você)
      const res = await fetch('/api/dashboard/knowledge/upload', { method: 'POST', body: fd });
      if (res.ok) {
        setMsg('Documento recebido! Em alguns minutos ele entra no conhecimento de todos os seus assistentes.');
        setFile(null);
        if (fileRef.current) fileRef.current.value = '';
        setTimeout(load, 4000);
      } else {
        const j = await res.json().catch(() => null);
        setMsg(j?.error || j?.detail || 'Não consegui enviar. Tente novamente.');
      }
    } catch {
      setMsg('Não consegui enviar. Tente novamente.');
    } finally {
      setSending(false);
    }
  };

  if (!d) return <p className="text-sm text-muted-foreground">Carregando…</p>;

  // 🔴 SPEC-EXTRA-001.5.1 (D2) — `cobertura.ok` e `fila.ok`, não `|| []`.
  //
  // Até 19/09/2026 esta linha era `fila.itens || []`: uma chamada que falhou e
  // uma fila realmente vazia viravam A MESMA COISA, e a tela dizia "Nada
  // esperando revisão" enquanto o backend devolvia 500. O erro agora viaja
  // inteiro até o componente, que tem um estado próprio para ele.
  const cobertura = planos?.cobertura || {};
  const fila = planos?.fila || {};
  const coberturaOk = cobertura?.ok === true;
  // 🔴 SPEC-EXTRA-001.5.1 (E19) — quem CURA é a AutoBrokers, não a corretora.
  //
  // A base de planos é de todas (D-PILOTO-01): deixar um admin de uma corretora
  // publicar "o Essencial da HDI não inclui vidros" era dar a ela a palavra
  // final sobre o contrato das outras. A fila some daqui — ela é ferramenta de
  // quem cura — e fica a frase que explica por que não há botão. ⚠️ A tela NÃO
  // esconde o conhecimento: a cobertura continua visível, em leitura.
  const podeCurar = planos?.curadoria_permitida === true;

  return (
    <div className="space-y-4">
      {planos && (
        <>
          {coberturaOk ? (
            <CoberturaDePlanos linhas={cobertura.linhas || []} resumo={cobertura.resumo} />
          ) : (
            <div className="rounded-lg border border-border bg-card p-4">
              <p className="text-sm font-medium text-foreground">
                Não consegui carregar o que as apólices cobrem agora.
              </p>
              <p className="mt-1 text-[11px] text-faint">
                Isso não quer dizer que a base esteja vazia — quer dizer que não deu para
                consultá-la neste momento.
              </p>
              <button
                type="button"
                onClick={loadPlanos}
                className="mt-2 h-7 rounded-md border border-border px-3 text-xs text-foreground"
              >
                Tentar de novo
              </button>
            </div>
          )}
          {podeCurar ? (
            <FilaDeCuradoria fila={fila} onMudou={loadPlanos} />
          ) : (
            <p className="rounded-lg border border-border bg-card px-4 py-3 text-[11px] text-faint">
              {planos?.aviso ||
                'Este conhecimento é de todas as corretoras e é mantido pela AutoBrokers.'}{' '}
              Você lê aqui o que cada plano cobre; quem publica e corrige é a equipe da
              AutoBrokers, para que a mesma resposta valha para todo mundo.
            </p>
          )}
        </>
      )}

      <div className="rounded-lg border border-border bg-card p-4">
        <p className="text-sm text-foreground">
          Conhecimento da corretora: <span className="font-semibold">{d.total}</span> documento(s), {d.ready} pronto(s) para uso.
        </p>
        <p className="mt-1 text-[11px] text-faint">
          Tudo que entra aqui vira memória de TODOS os seus assistentes automaticamente — AutoBrokers,
          Atendimento e Auxiliares. Não precisa escolher nada. Documentos de outras corretoras nunca aparecem aqui.
        </p>
      </div>

      <div className="rounded-lg border border-border bg-card p-4 space-y-3">
        <p className="text-sm font-medium text-foreground">Adicionar conhecimento</p>
        <input
          ref={fileRef}
          type="file"
          accept=".pdf,.docx,.txt,.md,.csv"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
          className="block w-full text-xs text-muted-foreground file:mr-3 file:rounded-md file:border-0 file:bg-primary file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-primary-foreground"
        />
        {/* SPEC-044: destino do conhecimento — em linguagem humana */}
        <div className="flex gap-2">
          {([
            { id: 'company', label: '🏢 Da corretora', hint: 'todos os assistentes e a equipe usam' },
            { id: 'personal', label: '👤 Só para mim', hint: 'ninguém mais vê' },
          ] as const).map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setTarget(t.id)}
              className={`flex-1 rounded-md border px-3 py-2 text-left text-xs transition-colors ${
                target === t.id
                  ? 'border-primary/50 bg-primary/5 text-foreground'
                  : 'border-border bg-background text-muted-foreground hover:text-foreground'
              }`}
            >
              <span className="block font-medium">{t.label}</span>
              <span className="block text-[10px] opacity-80">{t.hint}</span>
            </button>
          ))}
        </div>
        <div className="flex items-center justify-end">
          <button
            onClick={send}
            disabled={!file || sending}
            className="h-8 rounded-md bg-primary px-4 text-xs font-medium text-primary-foreground disabled:opacity-40"
          >
            {sending ? 'Enviando…' : 'Enviar'}
          </button>
        </div>
        <p className="text-[10px] text-faint">PDF, DOCX, TXT, MD ou CSV (até 10MB). O processamento é automático — sem configuração.</p>
        {msg && <p className="text-[11px] text-foreground">{msg}</p>}
      </div>

      {d.documents.length === 0 ? (
        <p className="text-sm text-muted-foreground">Nenhum documento ainda — suba o primeiro acima e veja o cérebro da corretora nascer.</p>
      ) : (
        <div className="rounded-lg border border-border bg-card divide-y divide-border">
          {d.documents.map((doc, i) => {
            const h = humanize(doc);
            const st = statusInfo(doc.status);
            return (
              <div key={i} className="flex items-center gap-3 p-3">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-border bg-surface-2 text-muted-foreground">
                  {st.label === 'Processando…' ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileText className="h-4 w-4" />}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-foreground">{h.title}</p>
                  <p className="truncate text-[11px] text-faint">{h.source}</p>
                </div>
                <div className="shrink-0 text-right">
                  <p className={`text-[11px] font-medium ${st.cls}`}>{st.label}</p>
                  {doc.created_at && <p className="text-[10px] text-faint">{fmtWhen(doc.created_at)}</p>}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
