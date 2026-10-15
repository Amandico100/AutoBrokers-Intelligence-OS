'use client';

import { useEffect, useRef, useState } from 'react';
import { CheckCircle2, Smartphone, WifiOff } from 'lucide-react';

import { BOTAO_PRIMARIO } from '@/components/aplicativos/casca/CardDoAplicativo';
import { Confirmar } from '@/components/aplicativos/casca/Confirmar';
import { cn } from '@/lib/utils';

import {
  criarPollDoQr,
  dataDaLinha,
  estadoDaLinha,
  fraseDoErro,
  lerLeituraDoQr,
  qrSeguro,
  type LeituraDoQr,
  type LinhaDoWhatsApp,
} from './useMeuPerfil';

/**
 * SPEC-131-0-B2 L3 — o bloco de cima do "Meu WhatsApp de trabalho": a pessoa conecta o PRÓPRIO WhatsApp lendo um QR
 * e conversa com o AutoBrokers na conversa "Mensagem para você". Só essa conversa é lida; nada vai para clientes.
 *
 * Estados (do servidor): desligada → nada aparece · nao_conectada → "Conectar meu WhatsApp" · aguardando_qr → o QR,
 * renovado a cada 4 s (para ao conectar, ao sair da tela e com a aba do navegador oculta) · conectada → número
 * MASCARADO que veio do servidor + "Desconectar" (com a confirmação da casa) · desconectada → a frase da SPEC §4 +
 * "Conectar de novo" · limite → "estamos no limite de conexões".
 */

const FOCO = 'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring';
const BOTAO_PRINCIPAL = cn('inline-flex h-11 items-center justify-center rounded-lg px-5 text-sm font-medium disabled:opacity-60', BOTAO_PRIMARIO, FOCO);
const BOTAO_SECUNDARIO =
  'inline-flex h-11 items-center justify-center rounded-lg border border-border px-4 text-sm font-medium text-foreground hover:bg-surface-2 disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring';

const ERRO_AO_CONECTAR = 'Não conseguimos preparar o código agora. Tente de novo em instantes.';
const ERRO_AO_DESCONECTAR = 'Não conseguimos desconectar agora. Tente de novo em instantes.';
const QR_EXPIROU = 'O código expirou antes da leitura. Toque em "Conectar meu WhatsApp" para gerar outro.';

const LINHA_VAZIA: Omit<LinhaDoWhatsApp, 'estado'> = { numero_mascarado: null, desde: null, motivo: null };

type Acoes = {
  aoConectar: () => void;
  aoCancelar: () => void;
  aoDesconectar: () => void;
};

/** o desenho de cada estado — sem efeitos, sem leitura (o container decide) */
export function VistaDaLinha({
  linha, qr, ocupado, erro, aviso, aoConectar, aoCancelar, aoDesconectar,
}: { linha: LinhaDoWhatsApp | null; qr: string | null; ocupado: boolean; erro: string; aviso: string } & Acoes) {
  if (!linha || linha.estado === 'desligada') return null;
  const imagem = qrSeguro(qr);

  return (
    <section aria-labelledby="linha-do-whatsapp-titulo" className="space-y-3 rounded-xl border border-border bg-surface p-4">
      <h3 id="linha-do-whatsapp-titulo" className="flex items-center gap-2 text-base font-semibold text-foreground">
        <Smartphone size={18} strokeWidth={1.6} aria-hidden />
        Conversar com o AutoBrokers pelo seu WhatsApp
      </h3>

      <div aria-live="polite" className="space-y-3">
        {linha.estado === 'nao_conectada' && (
          <>
            <p className="text-sm text-muted-foreground">
              Escreva, mande áudio, foto ou PDF na conversa &quot;Mensagem para você&quot; do seu WhatsApp e receba a
              resposta ali, como no chat. Só essa conversa é lida, e nada vai para os seus clientes.
            </p>
            <button type="button" onClick={aoConectar} disabled={ocupado} className={BOTAO_PRINCIPAL}>
              {ocupado ? 'Preparando o código…' : 'Conectar meu WhatsApp'}
            </button>
          </>
        )}

        {linha.estado === 'aguardando_qr' && (
          <>
            <p className="text-sm font-medium text-foreground">
              No celular: WhatsApp → Aparelhos conectados → Conectar um aparelho → aponte para este código.
            </p>
            <ul className="space-y-1 text-sm text-muted-foreground">
              <li><strong className="font-medium text-foreground">Android:</strong> toque nos três pontinhos (⋮), no alto, e depois em Aparelhos conectados.</li>
              <li><strong className="font-medium text-foreground">iPhone:</strong> toque em Configurações, embaixo, e depois em Aparelhos conectados.</li>
            </ul>
            {imagem ? (
              <div className="w-fit rounded-xl bg-white p-4 shadow-sm">
                {/* eslint-disable-next-line @next/next/no-img-element -- o QR é uma imagem de dados gerada a cada leitura */}
                <img src={imagem} alt="Código para conectar o seu WhatsApp ao AutoBrokers" width={256} height={256}
                  className="block h-64 w-64 max-w-full" />
              </div>
            ) : (
              <div className="flex h-64 w-64 max-w-full items-center justify-center rounded-xl border border-border bg-surface-2 p-4 text-center text-sm text-muted-foreground">
                Gerando o código…
              </div>
            )}
            <p className="text-sm text-muted-foreground">
              O código se renova sozinho. Deixe esta tela aberta até o celular confirmar.
            </p>
            <button type="button" onClick={aoCancelar} disabled={ocupado} className={BOTAO_SECUNDARIO}>
              Cancelar
            </button>
          </>
        )}

        {linha.estado === 'conectada' && (
          <>
            <p className="flex flex-wrap items-center gap-2 text-sm text-foreground">
              <CheckCircle2 size={16} strokeWidth={1.6} className="text-success" aria-hidden />
              <span className="font-medium">Conectado</span>
              {linha.numero_mascarado && <span className="tabular-nums">— {linha.numero_mascarado}</span>}
              {linha.desde && <span className="text-muted-foreground">· desde {dataDaLinha(linha.desde)}</span>}
            </p>
            <p className="text-sm text-muted-foreground">
              Abra a conversa &quot;Mensagem para você&quot; no seu WhatsApp e escreva como escreveria para um colega.
            </p>
            <Confirmar
              titulo="Desconectar o seu WhatsApp?"
              descricao={'O AutoBrokers deixa de ler e de responder na conversa "Mensagem para você". O seu WhatsApp continua funcionando normalmente no celular.'}
              acao="Desconectar" perigo onConfirmar={aoDesconectar}>
              <button type="button" disabled={ocupado} className={cn(BOTAO_SECUNDARIO, 'text-danger')}>
                {ocupado ? 'Desconectando…' : 'Desconectar'}
              </button>
            </Confirmar>
          </>
        )}

        {linha.estado === 'desconectada' && (
          <>
            <p className="flex items-start gap-2 text-sm text-foreground">
              <WifiOff size={16} strokeWidth={1.6} className="mt-0.5 shrink-0 text-muted-foreground" aria-hidden />
              <span>
                Seu WhatsApp desconectou do AutoBrokers{linha.desde ? ` em ${dataDaLinha(linha.desde)}` : ''}. Isso acontece
                quando o celular fica 14 dias sem internet ou quando o aparelho é removido em <em>Aparelhos conectados</em>.
              </span>
            </p>
            <button type="button" onClick={aoConectar} disabled={ocupado} className={BOTAO_PRINCIPAL}>
              {ocupado ? 'Preparando o código…' : 'Conectar de novo'}
            </button>
          </>
        )}

        {linha.estado === 'limite' && (
          <>
            <p className="text-sm text-foreground">Estamos no limite de conexões neste momento. Tente de novo mais tarde.</p>
            <button type="button" onClick={aoConectar} disabled={ocupado} className={BOTAO_SECUNDARIO}>
              {ocupado ? 'Tentando…' : 'Tentar de novo'}
            </button>
          </>
        )}

        {aviso && <p className="text-sm text-foreground dark:text-success" role="status">{aviso}</p>}
      </div>

      {erro && <p className="text-sm text-danger" role="alert">{erro}</p>}
    </section>
  );
}

async function lerQr(): Promise<LeituraDoQr | null> {
  try {
    const r = await fetch('/api/dashboard/meu-perfil/linha/qr', { cache: 'no-store' });
    if (!r.ok) return null;
    return lerLeituraDoQr(await r.json().catch(() => null));
  } catch {
    return null;
  }
}

/**
 * O container: conecta, cancela, desconecta e mantém o QR vivo. O estado mora no pai (`useLinhaDoWhatsApp`), para o
 * resto da aba saber se a linha está conectada.
 */
export function MinhaLinhaDoWhatsApp({
  linha, aoMudar, recarregar,
}: {
  linha: LinhaDoWhatsApp | null;
  /** troca o estado na hora (antes de o servidor confirmar) */
  aoMudar: (linha: LinhaDoWhatsApp) => void;
  /** lê o estado de novo no servidor */
  recarregar: () => void;
}) {
  const [qr, setQrLocal] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState('');
  const [aviso, setAviso] = useState('');
  const qrRef = useRef<string | null>(null);
  const recarregarRef = useRef(recarregar);
  useEffect(() => { recarregarRef.current = recarregar; }, [recarregar]);

  const setQr = (v: string | null) => { qrRef.current = v; setQrLocal(v); };
  const estado = linha?.estado ?? null;

  // o relógio do QR: só enquanto espera a leitura; para ao conectar, ao desmontar e com a aba oculta
  useEffect(() => {
    if (estado !== 'aguardando_qr') return;
    const guardarQr = (v: string | null) => { qrRef.current = v; setQrLocal(v); };
    const poll = criarPollDoQr({
      buscar: lerQr,
      aoLer: (l) => {
        if (l.estado === 'aguardando_qr') { guardarQr(l.qr); return; }
        guardarQr(null);
        if (l.estado === 'nao_conectada') setAviso(QR_EXPIROU);
        recarregarRef.current();
      },
      visivel: () => document.visibilityState !== 'hidden',
    });
    const aoTrocarDeAba = () => {
      if (document.visibilityState === 'hidden') poll.parar(); else poll.iniciar(true);
    };
    poll.iniciar(qrRef.current === null);
    document.addEventListener('visibilitychange', aoTrocarDeAba);
    return () => { poll.parar(); document.removeEventListener('visibilitychange', aoTrocarDeAba); };
  }, [estado]);

  const conectar = async () => {
    setOcupado(true); setErro(''); setAviso('');
    try {
      const res = await fetch('/api/dashboard/meu-perfil/linha/conectar', { method: 'POST', cache: 'no-store' });
      const j = (await res.clone().json().catch(() => ({}))) as { qr?: unknown; estado?: unknown };
      const voltou = estadoDaLinha(j.estado);
      if (voltou === 'limite') { setQr(null); aoMudar({ estado: 'limite', ...LINHA_VAZIA }); return; }
      if (!res.ok) { setErro(await fraseDoErro(res, ERRO_AO_CONECTAR)); return; }
      if (voltou && voltou !== 'aguardando_qr') { setQr(null); recarregar(); return; }
      setQr(qrSeguro(j.qr));
      aoMudar({ estado: 'aguardando_qr', ...LINHA_VAZIA });
    } catch {
      setErro(ERRO_AO_CONECTAR);
    } finally {
      setOcupado(false);
    }
  };

  const desconectar = async (ok: string) => {
    setOcupado(true); setErro(''); setAviso('');
    try {
      const res = await fetch('/api/dashboard/meu-perfil/linha/desconectar', { method: 'POST', cache: 'no-store' });
      if (!res.ok) { setErro(await fraseDoErro(res, ERRO_AO_DESCONECTAR)); return; }
      setQr(null);
      setAviso(ok);
      recarregar();
    } catch {
      setErro(ERRO_AO_DESCONECTAR);
    } finally {
      setOcupado(false);
    }
  };

  return (
    <VistaDaLinha
      linha={linha} qr={qr} ocupado={ocupado} erro={erro} aviso={aviso}
      aoConectar={conectar}
      aoCancelar={() => desconectar('')}
      aoDesconectar={() => desconectar('WhatsApp desconectado.')}
    />
  );
}

export default MinhaLinhaDoWhatsApp;
