'use client';

// SPEC-131-B · G1 — o cabeçalho de todo aplicativo (laudo de design §3): capa, tile do ícone, nome, frase, selo,
// "Funciona com" (ícone + NOME HUMANO + ✓/!) e o botão principal POR ESTADO (instalar ≠ ligar, SPEC-078).
//
// O botão é decidido por `botaoPrincipal` (puro, testado). "Ligar" pede uma confirmação curta com o "N de M
// prontos" do Como começar (DS-001 §8.6 permite modal para confirmar) — e, na Renovação, diz o que começa a
// acontecer de madrugada. "Desligar" é fantasma e diz que não apaga nada.

import Link from 'next/link';
import { AlertTriangle, Check, Loader2 } from 'lucide-react';

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { cn } from '@/lib/utils';
import type { BotaoPrincipal, ConexaoDoAplicativo, ItemDoCatalogo } from '@/lib/auxiliaries/catalog';
import { CapaGerada } from './CapaGerada';
import { BOTAO_PRIMARIO, SeloDoAplicativo, TileDoIcone } from './CardDoAplicativo';
import { iconeDaConexao } from './icones';

const FOCO = 'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background';
const BOTAO = 'inline-flex h-11 w-full items-center justify-center gap-2 rounded-lg px-5 text-sm font-medium transition-opacity disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto';

export interface CabecalhoProps {
  item: ItemDoCatalogo;
  botao: BotaoPrincipal;
  /** as conexões do "Funciona com" (as do catálogo + as que só o servidor sabe, como o Agger) */
  conexoes: ConexaoDoAplicativo[];
  /** "2 de 5 prontos" — mostrado na confirmação de Ligar */
  resumoDosPassos: string;
  ocupado: boolean;
  erro: string;
  motivoDeNaoLigar?: string;
  /** `confirmado`: veio da confirmação "Ligar …?" — a API exige `confirmar_ligar` para LIGAR a Renovação (K1) */
  onAcao: (acao: 'install' | 'resume' | 'pause', opcoes?: { confirmado?: boolean }) => void;
}

function FuncionaCom({ conexoes }: { conexoes: ConexaoDoAplicativo[] }) {
  if (conexoes.length === 0) return null;
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-sm text-muted-foreground">Funciona com</span>
      {conexoes.map((c) => {
        const Icone = iconeDaConexao(c.slug);
        const conteudo = (
          <>
            <Icone className="h-4 w-4" strokeWidth={1.6} aria-hidden="true" />
            <span>{c.nome}</span>
            {c.pronto === true && <Check className="h-3.5 w-3.5 text-success" strokeWidth={2} aria-label="conectado" />}
            {c.pronto === false && <AlertTriangle className="h-3.5 w-3.5 text-warning" strokeWidth={1.6} aria-label="falta conectar" />}
          </>
        );
        const classe = 'inline-flex h-11 sm:h-8 items-center gap-1.5 rounded-full border border-border bg-surface px-3 text-sm text-foreground';
        return c.pronto === false && c.onde ? (
          <Link key={c.slug} href={c.onde} className={cn(classe, 'hover:border-primary/40', FOCO)} data-conexao={c.slug}>
            {conteudo}
          </Link>
        ) : (
          <span key={c.slug} className={classe} data-conexao={c.slug}>
            {conteudo}
          </span>
        );
      })}
    </div>
  );
}

function AcaoPrincipal({ item, botao, resumoDosPassos, ocupado, onAcao }: Omit<CabecalhoProps, 'conexoes' | 'erro'>) {
  if (botao.tipo === 'desabilitado') {
    return (
      <button type="button" disabled className={cn(BOTAO, 'border border-border bg-surface-2 text-muted-foreground')}>
        {botao.rotulo}
      </button>
    );
  }
  if (botao.tipo === 'link') {
    return (
      <Link href={botao.href} scroll={false} className={cn(BOTAO, BOTAO_PRIMARIO, FOCO)}>
        {botao.rotulo}
      </Link>
    );
  }
  const icone = ocupado ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : null;
  if (botao.fantasma) {
    return (
      <button
        type="button"
        onClick={() => onAcao(botao.acao)}
        disabled={ocupado}
        className={cn(BOTAO, 'border border-border bg-transparent text-foreground hover:border-danger/40', FOCO)}
      >
        {icone}
        {botao.rotulo}
      </button>
    );
  }
  if (!botao.confirmar) {
    return (
      <button type="button" onClick={() => onAcao(botao.acao)} disabled={ocupado} className={cn(BOTAO, BOTAO_PRIMARIO, FOCO)}>
        {icone}
        {botao.rotulo}
      </button>
    );
  }
  const renovacao = item.slug === 'renovacao';
  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <button type="button" disabled={ocupado} className={cn(BOTAO, BOTAO_PRIMARIO, FOCO)}>
          {icone}
          {botao.rotulo}
        </button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Ligar {item.nome}?</AlertDialogTitle>
          <AlertDialogDescription asChild>
            <div className="space-y-2 text-sm text-muted-foreground">
              <p>Como começar: {resumoDosPassos}.</p>
              <p>
                {renovacao
                  ? 'A partir da próxima madrugada, ele calcula as renovações dos próximos dias no Agger de quem cuida de cada cliente. Nada sai para o cliente sem você.'
                  : 'A partir daqui ele trabalha sozinho, nos horários que você configurou.'}
              </p>
              <p>Você pode desligar quando quiser — desligar não apaga nada.</p>
            </div>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel className="h-11">Agora não</AlertDialogCancel>
          <AlertDialogAction className={cn('h-11', BOTAO_PRIMARIO)} onClick={() => onAcao(botao.acao, { confirmado: true })}>
            Ligar
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

export function CabecalhoDoAplicativo(props: CabecalhoProps) {
  const { item, botao, conexoes, erro, motivoDeNaoLigar } = props;
  return (
    <header className="space-y-5">
      <CapaGerada
        icone={item.icone}
        matiz={item.matiz}
        coverUrl={item.cover_url}
        className="aspect-[5/2] rounded-2xl border border-border sm:aspect-[4/1]"
        marca={180}
      />
      <div className="flex flex-col gap-4 px-1 sm:flex-row sm:items-end sm:justify-between">
        <div className="flex min-w-0 flex-col gap-3 sm:flex-row sm:items-end">
          <TileDoIcone icone={item.icone} matiz={item.matiz} tamanho={72} className="-mt-14 ml-3 ring-4 ring-background sm:-mt-10 sm:ml-4" />
          <div className="min-w-0 space-y-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">{item.nome}</h1>
              <SeloDoAplicativo estado={item.estado} />
            </div>
            {item.headline && <p className="text-base text-foreground-2">{item.headline}</p>}
          </div>
        </div>
        <div className="flex w-full shrink-0 flex-col gap-2 sm:w-auto sm:items-end">
          <AcaoPrincipal {...props} />
          {item.tela_de_execucao && item.estado_catalogo === 'available' && (
            <Link
              href={item.tela_de_execucao}
              className={cn(BOTAO, 'border border-border bg-surface text-foreground hover:border-primary/40', FOCO)}
            >
              Abrir agora
            </Link>
          )}
        </div>
      </div>

      {botao.tipo === 'desabilitado' && botao.motivo && (
        <p className="px-1 text-sm text-muted-foreground">{botao.motivo}</p>
      )}
      {botao.tipo === 'acao' && botao.fantasma && (
        <p className="px-1 text-sm text-muted-foreground">
          Desligar não apaga nada — a configuração e o histórico ficam.
        </p>
      )}
      {motivoDeNaoLigar && <p className="px-1 text-sm text-foreground-2">{motivoDeNaoLigar}</p>}
      {erro && (
        <p role="alert" className="px-1 text-sm text-danger">
          {erro}
        </p>
      )}

      <div className="px-1">
        <FuncionaCom conexoes={conexoes} />
      </div>
    </header>
  );
}

export default CabecalhoDoAplicativo;
