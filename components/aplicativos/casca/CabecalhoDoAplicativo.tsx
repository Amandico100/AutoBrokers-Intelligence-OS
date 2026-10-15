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
const BOTAO_BASE = 'inline-flex h-11 w-full items-center justify-center gap-2 rounded-lg px-5 text-sm font-medium transition-opacity disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto';

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
  /**
   * K3 (juiz de design 6): a capa grande é do Início. Nas outras abas o cabeçalho é COMPACTO — ícone, nome, selo e o
   * botão de ação (Ligar/Desligar) — para o trabalho subir: em Renovações a lista começa acima da dobra no celular.
   */
  compacto?: boolean;
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

function AcaoPrincipal({ item, botao, resumoDosPassos, ocupado, onAcao, compacto }: Omit<CabecalhoProps, 'conexoes' | 'erro'>) {
  // no cabeçalho compacto o botão mede o próprio texto (nunca a largura toda) — ao lado do nome
  const BOTAO = cn(BOTAO_BASE, compacto && 'w-auto px-4');
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

function Avisos({ botao, erro, motivoDeNaoLigar }: Pick<CabecalhoProps, 'botao' | 'erro' | 'motivoDeNaoLigar'>) {
  return (
    <>
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
    </>
  );
}

/** As abas de trabalho: ícone + nome + selo + a ação, numa linha só. Sem capa, sem "Funciona com" (moram no Início). */
function CabecalhoCompacto(props: CabecalhoProps) {
  const { item, botao, erro, motivoDeNaoLigar } = props;
  return (
    <header className="space-y-2" data-cabecalho="compacto">
      <div className="flex items-center gap-3 px-1">
        <TileDoIcone icone={item.icone} matiz={item.matiz} slug={item.slug} tamanho={48} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <h1 className="text-xl font-semibold tracking-tight text-foreground sm:text-2xl">{item.nome}</h1>
            <SeloDoAplicativo estado={item.estado} />
          </div>
          {item.headline && <p className="hidden truncate text-sm text-muted-foreground sm:block">{item.headline}</p>}
        </div>
        {/* só a AÇÃO (Ligar/Desligar/Instalar): o link "Configurar" e o "Em breve" já são a própria aba ou o Início */}
        {botao.tipo === 'acao' && (
          <div className="shrink-0">
            <AcaoPrincipal {...props} />
          </div>
        )}
      </div>
      {/* o "desligar não apaga nada" é do Início; aqui só o que impede ou deu errado */}
      <Avisos botao={botao.tipo === 'acao' && botao.fantasma ? { ...botao, fantasma: false } : botao} erro={erro} motivoDeNaoLigar={motivoDeNaoLigar} />
    </header>
  );
}

export function CabecalhoDoAplicativo(props: CabecalhoProps) {
  const { item, botao, conexoes, erro, motivoDeNaoLigar } = props;
  if (props.compacto) return <CabecalhoCompacto {...props} />;
  return (
    <header className="space-y-5" data-cabecalho="completo">
      <CapaGerada
        slug={item.slug}
        icone={item.icone}
        matiz={item.matiz}
        coverUrl={item.cover_url}
        className="aspect-[5/2] rounded-2xl border border-border sm:aspect-[4/1]"
        enquadramento="cabecalho"
      />
      <div className="flex flex-col gap-4 px-1 sm:flex-row sm:items-end sm:justify-between">
        <div className="flex min-w-0 flex-col gap-3 sm:flex-row sm:items-end">
          {/* SPEC-139 · D-139-L6-01 (costura): a capa GERADA (hoje a C · Cena, o ícone no selo) já é o ícone do aplicativo, grande, na cor
              dele — o tile ao lado repetia o MESMO desenho a dois dedos de distância (no celular, colado à placa). O tile
              só aparece quando a capa é a imagem do Founder (`cover_url`), que pode não trazer o ícone. (esconder 86 ×
              manter 55 × reposicionar 65 — capturas 1440/390, claro/escuro, 15/10/2026.) O cabeçalho compacto (as outras
              abas, sem capa) continua com o tile.
              K3 (juiz de design 3): `relative z-10` — sem ele a capa (relative, overflow-hidden) pinta POR CIMA do tile
              no celular e só a metade de baixo aparecia; o card da loja já fazia assim */}
          {item.cover_url && (
            <TileDoIcone icone={item.icone} matiz={item.matiz} slug={item.slug} tamanho={72} className="relative z-10 -mt-14 ml-3 ring-4 ring-background sm:-mt-10 sm:ml-4" />
          )}
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
              className={cn(BOTAO_BASE, 'border border-border bg-surface text-foreground hover:border-primary/40', FOCO)}
            >
              Abrir agora
            </Link>
          )}
        </div>
      </div>

      {/* Conserto B (juiz de design, "Em breve"): o que falta para existir já é a seção "Ainda não está pronto" do Início
          (a única aba de um "Em breve") — aqui ele aparecia DUAS vezes. O cabeçalho completo não repete o motivo. */}
      <Avisos botao={botao.tipo === 'desabilitado' && item.estado === 'em_breve' ? { ...botao, motivo: null } : botao} erro={erro} motivoDeNaoLigar={motivoDeNaoLigar} />

      <div className="px-1">
        <FuncionaCom conexoes={conexoes} />
      </div>
    </header>
  );
}

export default CabecalhoDoAplicativo;
