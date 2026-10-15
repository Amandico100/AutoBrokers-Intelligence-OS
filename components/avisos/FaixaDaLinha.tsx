'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';
import { WifiOff, X } from 'lucide-react';

import { BOTAO_PRIMARIO } from '@/components/aplicativos/casca/CardDoAplicativo';
import {
  EVENTO_LINHA_MUDOU,
  buscarLinha,
  dataDaLinha,
  lerLinha,
  type LinhaDoWhatsApp,
} from '@/components/perfil/useMeuPerfil';
import { cn } from '@/lib/utils';

/**
 * SPEC-131-0-B2 L3 (D-132F-04) — a faixa do topo do painel quando o WhatsApp da pessoa DESCONECTOU do AutoBrokers.
 * A desconexão é avisada SÓ NA TELA. Nos outros estados, nada. Lê o estado UMA vez, ao montar (sem relógio); se a
 * pessoa reconecta no Meu perfil, a aba avisa pelo evento `EVENTO_LINHA_MUDOU`. Dispensável por sessão do navegador
 * (a dispensa vale para AQUELA desconexão: uma nova desconexão mostra a faixa de novo).
 */

const PREFIXO_DA_DISPENSA = 'ab:faixa-da-linha:dispensada';
/** na própria tela do Meu perfil o bloco da linha já diz o mesmo — a faixa não repete */
const TELA_DO_PERFIL = '/dashboard/configuracoes';

export function chaveDaDispensa(linha: LinhaDoWhatsApp): string {
  return `${PREFIXO_DA_DISPENSA}:${linha.desde ?? 'sem-data'}`;
}

function lerDispensa(chave: string): boolean {
  try { return window.sessionStorage.getItem(chave) === '1'; } catch { return false; }
}

function gravarDispensa(chave: string) {
  try { window.sessionStorage.setItem(chave, '1'); } catch { /* sem armazenamento: some só até recarregar */ }
}

export function faixaAparece(linha: LinhaDoWhatsApp | null, dispensada: boolean, caminho: string | null): boolean {
  if (linha?.estado !== 'desconectada' || dispensada) return false;
  return !(caminho ?? '').startsWith(TELA_DO_PERFIL);
}

export function FaixaDaLinhaVista({ linha, aoDispensar }: { linha: LinhaDoWhatsApp | null; aoDispensar: () => void }) {
  if (!linha || linha.estado !== 'desconectada') return null;
  return (
    <div role="status" aria-live="polite" className="border-b border-border bg-surface px-4 py-3">
      <div className="mx-auto flex max-w-5xl flex-col gap-3 sm:flex-row sm:items-center">
        <p className="flex min-w-0 flex-1 items-start gap-2 text-sm text-foreground">
          <WifiOff size={16} strokeWidth={1.6} className="mt-0.5 shrink-0 text-muted-foreground" aria-hidden />
          <span>
            Seu WhatsApp desconectou do AutoBrokers{linha.desde ? ` em ${dataDaLinha(linha.desde)}` : ''}. Isso acontece
            quando o celular fica 14 dias sem internet ou quando o aparelho é removido em <em>Aparelhos conectados</em>.
          </span>
        </p>
        <div className="flex shrink-0 items-center gap-2">
          <Link href="/dashboard/configuracoes?aba=whatsapp"
            className={cn('inline-flex h-11 items-center justify-center rounded-lg px-4 text-sm font-medium', BOTAO_PRIMARIO,
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring')}>
            Conectar de novo
          </Link>
          <button type="button" onClick={aoDispensar} aria-label="Fechar este aviso"
            className="inline-flex h-11 w-11 items-center justify-center rounded-md text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
            <X size={16} strokeWidth={1.6} aria-hidden />
          </button>
        </div>
      </div>
    </div>
  );
}

export function FaixaDaLinha() {
  const caminho = usePathname();
  const [linha, setLinha] = useState<LinhaDoWhatsApp | null>(null);
  const [dispensada, setDispensada] = useState(false);

  useEffect(() => {
    let viva = true;
    const guardar = (l: LinhaDoWhatsApp | null) => {
      if (!viva) return;
      setDispensada(l?.estado === 'desconectada' ? lerDispensa(chaveDaDispensa(l)) : false);
      setLinha(l);
    };
    buscarLinha().then(guardar);
    const aoMudar = (e: Event) => guardar(lerLinha((e as CustomEvent<unknown>).detail));
    window.addEventListener(EVENTO_LINHA_MUDOU, aoMudar);
    return () => { viva = false; window.removeEventListener(EVENTO_LINHA_MUDOU, aoMudar); };
  }, []);

  if (!linha || !faixaAparece(linha, dispensada, caminho)) return null;
  return (
    <FaixaDaLinhaVista linha={linha} aoDispensar={() => { gravarDispensa(chaveDaDispensa(linha)); setDispensada(true); }} />
  );
}

export default FaixaDaLinha;
