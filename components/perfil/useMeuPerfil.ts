'use client';

import { useCallback, useEffect, useState } from 'react';

/**
 * SPEC-131-B G3 — o que "Meu perfil" lê da corretora ativa (`/api/dashboard/meu-perfil`): o MEU WhatsApp de trabalho,
 * as MINHAS ausências, as que eu cubro e as OUTRAS pessoas ativas da corretora (para escolher quem cobre).
 */
export type Ausencia = { id: string; de: string; ate: string; user_id: string; nome: string; ativa: boolean };
/**
 * SPEC-131-0-B3 (D-1310B3-01) — o número de trabalho EFETIVO, decidido num ponto só no backend: o PAREADO quando o
 * WhatsApp da pessoa está conectado nesta corretora (`origem: 'linha'`), senão o DIGITADO e confirmado, senão nenhum.
 * É ele que o cliente recebe no "Quero renovar". Backend antigo não manda `efetivo`: a tela trata como antes.
 */
export type OrigemDoNumero = 'linha' | 'digitado';
export type NumeroEfetivo = { numero: string | null; origem: OrigemDoNumero | null };
export type MeuPerfil = {
  whatsapp_trabalho: {
    numero: string | null;
    confirmado_em: string | null;
    confirmado: boolean;
    disponivel?: boolean;
    verificado_em?: string | null;
    verificado?: boolean;
    efetivo?: NumeroEfetivo | null;
  };
  ausencias: Ausencia[];
  cubro: Ausencia[];
  pessoas: { user_id: string; nome: string }[];
  ausencia_disponivel?: boolean;
  duracao_maxima_dias?: number;
  eu: string;
  pode_gerir_todos: boolean;
};

export function useMeuPerfil() {
  const [perfil, setPerfil] = useState<MeuPerfil | null>(null);
  const [erro, setErro] = useState('');

  const carregar = useCallback(async () => {
    setErro('');
    try {
      const r = await fetch('/api/dashboard/meu-perfil', { cache: 'no-store' });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) { setErro('Não conseguimos carregar agora.'); return; }
      setPerfil(j as MeuPerfil);
    } catch {
      setErro('Não conseguimos carregar agora.');
    }
  }, []);

  useEffect(() => { carregar(); }, [carregar]);
  return { perfil, erro, carregar };
}

/** A frase de erro que veio do servidor (já em português) ou uma genérica. */
export async function fraseDoErro(res: Response, generica: string): Promise<string> {
  const j = await res.json().catch(() => ({}));
  if (typeof j?.detail === 'string') return j.detail;
  if (typeof j?.error === 'string' && /\s/.test(j.error)) return j.error;
  return generica;
}

/** o `efetivo` que veio do servidor, só se estiver no contrato; ausente ou torto → `null` (a tela trata como antes) */
export function lerEfetivo(v: unknown): NumeroEfetivo | null {
  if (!v || typeof v !== 'object') return null;
  const o = v as Record<string, unknown>;
  const origem = o.origem === 'linha' || o.origem === 'digitado' ? o.origem : null;
  const numero = typeof o.numero === 'string' && /\d/.test(o.numero) ? o.numero : null;
  return { numero, origem };
}

const digitos = (v: string | null | undefined) => String(v ?? '').replace(/\D/g, '');

/** o celular brasileiro pareado pode vir sem o nono dígito (o WhatsApp guarda assim contas antigas): a mesma pessoa */
function chaveDoNumero(v: string | null | undefined): string {
  const d = digitos(v);
  return d.startsWith('55') && d.length === 13 && d[4] === '9' ? `${d.slice(0, 4)}${d.slice(5)}` : d;
}

export function mesmoNumero(a: string | null | undefined, b: string | null | undefined): boolean {
  const ka = chaveDoNumero(a);
  return Boolean(ka) && ka === chaveDoNumero(b);
}

/**
 * O número MASCARADO no mesmo desenho do servidor (`5511*****001`: quatro primeiros, cinco estrelas sempre, três
 * últimos) — assim o número de reserva e o conectado se leem lado a lado.
 */
export function mascararNumero(v: string | null | undefined): string | null {
  const d = digitos(v);
  if (!d) return null;
  if (d.length <= 7) return `${d.slice(0, 2)}*****`;
  return `${d.slice(0, 4)}*****${d.slice(-3)}`;
}

export const dataBR = (iso: string) => {
  const [a, m, d] = iso.slice(0, 10).split('-');
  return a && m && d ? `${d}/${m}/${a}` : iso;
};

/**
 * SPEC-131-0-B2 L3 — "a linha do usuário": o PRÓPRIO WhatsApp da pessoa conectado ao AutoBrokers (lido por QR), em que
 * ela conversa com o AutoBrokers na conversa consigo mesma ("Mensagem para você"). O estado vem do BFF
 * `/api/dashboard/meu-perfil/linha` (company_id e user_id SÓ da sessão). O número vem MASCARADO do servidor: a tela
 * nunca recebe nem formata o número em claro.
 */
export type EstadoDaLinha = 'nao_conectada' | 'aguardando_qr' | 'conectada' | 'desconectada' | 'limite' | 'desligada';
export type LinhaDoWhatsApp = {
  estado: EstadoDaLinha;
  numero_mascarado: string | null;
  desde: string | null;
  motivo: string | null;
};
export type LeituraDoQr = { qr: string | null; estado: EstadoDaLinha };

const ESTADOS_DA_LINHA: readonly EstadoDaLinha[] = ['nao_conectada', 'aguardando_qr', 'conectada', 'desconectada', 'limite', 'desligada'];
/** o evento que avisa a faixa do topo quando a linha muda nesta aba (sem relógio) */
export const EVENTO_LINHA_MUDOU = 'autobrokers:linha-mudou';
/** o QR é lido de novo a cada 4 s enquanto a pessoa aponta o celular */
export const INTERVALO_DO_QR_MS = 4000;

const texto = (v: unknown): string | null => (typeof v === 'string' && v.trim() ? v : null);

export function estadoDaLinha(v: unknown): EstadoDaLinha | null {
  return typeof v === 'string' && (ESTADOS_DA_LINHA as readonly string[]).includes(v) ? (v as EstadoDaLinha) : null;
}

/** só o contrato: estado, número MASCARADO, desde, motivo — qualquer outro campo é deixado para trás */
export function lerLinha(j: unknown): LinhaDoWhatsApp | null {
  const o = (j && typeof j === 'object' ? j : {}) as Record<string, unknown>;
  const estado = estadoDaLinha(o.estado);
  if (!estado) return null;
  return { estado, numero_mascarado: texto(o.numero_mascarado), desde: texto(o.desde), motivo: texto(o.motivo) };
}

/** o QR só vale como imagem de dados; qualquer outra coisa não vira `src` */
export function qrSeguro(v: unknown): string | null {
  return typeof v === 'string' && /^data:image\/(png|jpeg|gif|webp);base64,[A-Za-z0-9+/=]+$/.test(v) ? v : null;
}

export function lerLeituraDoQr(j: unknown): LeituraDoQr | null {
  const o = (j && typeof j === 'object' ? j : {}) as Record<string, unknown>;
  const estado = estadoDaLinha(o.estado);
  return estado ? { qr: qrSeguro(o.qr), estado } : null;
}

/** a data no fuso de Brasília (o servidor manda em UTC) */
export function dataDaLinha(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return dataBR(iso);
  try {
    return d.toLocaleDateString('pt-BR', { timeZone: 'America/Sao_Paulo', day: '2-digit', month: '2-digit', year: 'numeric' });
  } catch {
    return dataBR(iso);
  }
}

/** uma leitura do estado da linha; erro ou resposta fora do contrato → `null` (o bloco e a faixa não aparecem) */
export async function buscarLinha(): Promise<LinhaDoWhatsApp | null> {
  try {
    const r = await fetch('/api/dashboard/meu-perfil/linha', { cache: 'no-store' });
    if (!r.ok) return null;
    return lerLinha(await r.json().catch(() => null));
  } catch {
    return null;
  }
}

export function avisarLinhaMudou(linha: LinhaDoWhatsApp | null) {
  try {
    window.dispatchEvent(new CustomEvent<LinhaDoWhatsApp | null>(EVENTO_LINHA_MUDOU, { detail: linha }));
  } catch { /* sem janela (servidor): não há faixa a avisar */ }
}

export function useLinhaDoWhatsApp() {
  const [linha, setLinhaLocal] = useState<LinhaDoWhatsApp | null>(null);
  const [carregada, setCarregada] = useState(false);

  const setLinha = useCallback((l: LinhaDoWhatsApp | null) => {
    setLinhaLocal(l);
    avisarLinhaMudou(l);
  }, []);

  const carregar = useCallback(async () => {
    const l = await buscarLinha();
    setLinha(l);
    setCarregada(true);
  }, [setLinha]);

  useEffect(() => { carregar(); }, [carregar]);
  return { linha, carregada, setLinha, carregar };
}

type Relogio = { setTimeout: (fn: () => void, ms: number) => unknown; clearTimeout: (id: unknown) => void };

/**
 * O relógio do QR: lê de novo a cada `intervaloMs` ENQUANTO o estado for `aguardando_qr`. Para sozinho quando o estado
 * muda (conectou, expirou), quando a aba do navegador está oculta e quando `parar()` é chamado (o componente desmontou);
 * a resposta que chega depois de parado é jogada fora. Um agendamento por vez (sem `setInterval`, nunca sobrepõe).
 */
export function criarPollDoQr(opts: {
  buscar: () => Promise<LeituraDoQr | null>;
  aoLer: (leitura: LeituraDoQr) => void;
  intervaloMs?: number;
  relogio?: Relogio;
  visivel?: () => boolean;
}) {
  const intervalo = opts.intervaloMs ?? INTERVALO_DO_QR_MS;
  const relogio: Relogio = opts.relogio ?? {
    setTimeout: (fn, ms) => globalThis.setTimeout(fn, ms),
    clearTimeout: (id) => globalThis.clearTimeout(id as ReturnType<typeof globalThis.setTimeout>),
  };
  const visivel = opts.visivel ?? (() => true);
  let ativo = false;
  let geracao = 0;
  let agendado: unknown = null;

  const parar = () => {
    ativo = false;
    geracao += 1;
    if (agendado !== null) relogio.clearTimeout(agendado);
    agendado = null;
  };

  const agendar = (ms: number) => {
    const minha = geracao;
    agendado = relogio.setTimeout(() => { agendado = null; void passo(minha); }, ms);
  };

  const passo = async (minha: number) => {
    if (!ativo || minha !== geracao) return;
    if (!visivel()) { parar(); return; }
    let leitura: LeituraDoQr | null = null;
    try { leitura = await opts.buscar(); } catch { leitura = null; }
    if (!ativo || minha !== geracao) return; // parou enquanto a leitura estava em voo
    if (leitura) {
      opts.aoLer(leitura);
      if (leitura.estado !== 'aguardando_qr') { parar(); return; }
    }
    if (ativo && minha === geracao) agendar(intervalo);
  };

  const iniciar = (imediato = false) => {
    if (ativo) return;
    ativo = true;
    geracao += 1;
    if (imediato) void passo(geracao); else agendar(intervalo);
  };

  return { iniciar, parar, ativo: () => ativo };
}
