'use client';

// SPEC-064 Bloco C.3 — a página de UM Auxiliar.
//
// Antes só existia um modal de configuração: nada explicava o que a coisa faz
// nem por que vale a pena. Modal serve para uma decisão; isto é uma leitura.
//
// A ordem das seções não é estética. É a ordem em que o corretor decide:
// o que é → o que faz → o que eu ganho → de onde vem o dado → ligo?

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Loader2, Plug, Power, PauseCircle } from 'lucide-react';

import { CATEGORIAS, type ItemDoCatalogo } from '@/lib/auxiliaries/catalog';
import PainelDeRotinas from '@/components/auxiliares/PainelDeRotinas';

interface Props {
  item: ItemDoCatalogo;
  podeLigar: { pode: boolean; motivo?: string };
}

function Secao({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <section className="space-y-2">
      <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {titulo}
      </h2>
      {children}
    </section>
  );
}

export default function AuxiliarDetalheClient({ item, podeLigar }: Props) {
  const router = useRouter();
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState('');

  async function agir(action: 'install' | 'pause' | 'resume') {
    setOcupado(true);
    setErro('');
    try {
      const r = await fetch(`/api/dashboard/auxiliaries/${item.template_id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action }),
      });
      const j = await r.json();
      if (!r.ok || j?.ok === false) {
        // O servidor recusa por dois motivos, e os dois têm texto próprio:
        // "em breve" e "falta conectar". Repassar o motivo é o que evita o
        // corretor achar que o produto está quebrado.
        //
        // 🔴 E quando o motivo NÃO tem texto próprio, o servidor manda a causa
        // real em `details` — e esta tela a descartava.
        //
        // 📊 Medido em 17/08/2026: o Founder viu `install_failed` na tela, sem
        // mais nada. A resposta HTTP trazia, em `details[0]`, a mensagem exata
        // do banco ("Could not find the 'display_name' column…"). Duas telas de
        // distância entre o sintoma e a causa, por uma linha que não lia um
        // campo que já vinha pronto.
        //
        // O detalhe técnico não é bonito para o corretor, mas é honesto — e a
        // alternativa medida foi pior: um slug em inglês que não explica nada.
        const tecnico = Array.isArray(j?.details)
          ? String(j.details[0] || '').trim()
          : '';
        setErro(
          j?.detalhe ||
            (j?.faltando ? `Conecte antes: ${j.faltando.join(', ')}.` : null) ||
            (tecnico ? `Não foi possível concluir — ${tecnico}` : null) ||
            j?.error ||
            'Não foi possível concluir.',
        );
        return;
      }
      router.refresh();
    } catch {
      setErro('Falha de conexão.');
    } finally {
      setOcupado(false);
    }
  }

  const ligado = item.estado === 'ligado';
  // Instalado ≠ ligado. Um Auxiliar PAUSADO continua dono das rotinas dele, e
  // é justamente pausado que a corretora quer configurar antes de ligar.
  //
  // 📊 Medido em 17/08/2026: a Resulta tem a Cobrança Feita instalada com
  // status `inactive` (= "pausado" na tela) e UMA rotina de cobrança com o
  // número de teste e a mensagem já gravados. Com a seção presa em `ligado`,
  // essa rotina era invisível pela interface — existia no banco e em lugar
  // nenhum na tela.
  const instalado = ligado || item.estado === 'pausado';

  return (
    <div className="space-y-8">
      {/* 1 · TÍTULO E HEADLINE */}
      <div>
        <div className="flex flex-wrap items-center gap-2">
          {item.categorias.map((c) => {
            const cat = CATEGORIAS[c];
            if (!cat) return null;
            return (
              <span
                key={c}
                className="rounded-md border border-border bg-surface-2 px-1.5 py-0.5 text-[10px] text-muted-foreground"
              >
                {cat.emoji} {cat.rotulo}
              </span>
            );
          })}
        </div>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight text-foreground">{item.nome}</h1>
        {item.headline && (
          <p className="mt-1 text-base text-muted-foreground">{item.headline}</p>
        )}
      </div>

      {/* 2 · O QUE É */}
      {item.descricao && (
        <Secao titulo="O que é">
          <div className="space-y-2 text-sm leading-relaxed text-muted-foreground">
            {item.descricao.split('\n\n').map((p, i) => (
              <p key={i}>{p}</p>
            ))}
          </div>
        </Secao>
      )}

      {/* 3 · O QUE ELE FAZ */}
      {item.o_que_faz.length > 0 && (
        <Secao titulo="O que ele faz">
          <ul className="space-y-2">
            {item.o_que_faz.map((t, i) => (
              <li
                key={i}
                className="flex items-start justify-between gap-3 rounded-lg border border-border bg-surface px-3 py-2"
              >
                <span className="text-sm text-foreground">{t.tarefa}</span>
                <span className="shrink-0 rounded-full border border-border bg-surface-2 px-2 py-0.5 text-[10px] text-muted-foreground">
                  {t.frequencia}
                </span>
              </li>
            ))}
          </ul>
        </Secao>
      )}

      {/* 4 · O QUE VOCÊ GANHA
          Quando ainda não há número medido, o texto diz o que SERÁ medido.
          Nunca inventa valor — CLAUDE.md §12.1. */}
      {item.promessa && (
        <Secao titulo="O que você ganha">
          <p className="rounded-lg border border-border bg-surface-2 px-3 py-2.5 text-sm text-foreground">
            {item.promessa}
          </p>
        </Secao>
      )}

      {/* 5 · DE ONDE ELE TIRA A INFORMAÇÃO */}
      {item.fontes.length > 0 && (
        <Secao titulo="De onde ele tira a informação">
          <div className="flex flex-wrap gap-1.5">
            {item.fontes.map((f) => (
              <span
                key={f}
                className="rounded-md border border-border bg-surface px-2 py-1 text-xs text-muted-foreground"
              >
                {f.replace(/_/g, ' ')}
              </span>
            ))}
          </div>
          <p className="text-[11px] text-faint">
            Você precisa saber o que o Auxiliar acessa. Nada aqui sai da sua corretora.
          </p>
        </Secao>
      )}

      {/* CONEXÕES — a peça que o Founder pediu:
          conectou uma vez, serve a todos os Auxiliares. */}
      {(item.conectores_pendentes.length > 0 || item.conectores_prontos.length > 0) && (
        <Secao titulo="Conexões que ele usa">
          <div className="space-y-2">
            {item.conectores_prontos.map((c) => (
              <div
                key={c}
                className="flex items-center gap-2 rounded-lg border border-emerald-500/25 bg-emerald-500/5 px-3 py-2"
              >
                <Plug className="h-3.5 w-3.5 text-emerald-600" />
                <span className="text-sm text-foreground">{c.replace(/_/g, ' ')}</span>
                <span className="ml-auto text-[11px] font-medium text-emerald-600">conectado</span>
              </div>
            ))}
            {item.conectores_pendentes.map((c) => (
              <Link
                key={c.slug}
                href={c.onde}
                className="flex items-center gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 transition-colors hover:bg-amber-500/20"
              >
                <Plug className="h-3.5 w-3.5 text-amber-600" />
                <span className="text-sm text-foreground">{c.nome}</span>
                <span className="ml-auto text-[11px] font-medium text-amber-600">conectar →</span>
              </Link>
            ))}
          </div>
          <p className="text-[11px] text-faint">
            A conexão é da corretora: depois de conectada, qualquer Auxiliar que precisar dela
            usa a mesma — você não conecta duas vezes.
          </p>
        </Secao>
      )}

      {/* 6 · LIGAR / CONFIGURAR */}
      <Secao titulo={ligado ? 'Controle' : 'Ligar'}>
        {erro && <p className="text-sm text-danger">{erro}</p>}

        {item.estado_catalogo === 'coming_soon' ? (
          <div className="rounded-lg border border-border bg-surface-2 px-3 py-3">
            <p className="text-sm font-medium text-foreground">Ainda não está pronto</p>
            {item.falta_para_existir && (
              <p className="mt-1 text-xs text-muted-foreground">{item.falta_para_existir}</p>
            )}
            <button
              disabled
              className="mt-3 cursor-not-allowed rounded-md border border-border bg-surface px-3 py-2 text-sm text-faint"
            >
              Em breve
            </button>
          </div>
        ) : ligado ? (
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => agir('pause')}
              disabled={ocupado}
              className="inline-flex items-center gap-1.5 rounded-md border border-border bg-surface px-3 py-2 text-sm font-medium text-foreground transition-colors hover:border-primary/40 disabled:opacity-60"
            >
              {ocupado ? <Loader2 className="h-4 w-4 animate-spin" /> : <PauseCircle className="h-4 w-4" />}
              Desligar
            </button>
            <span className="text-xs text-muted-foreground">
              Desligar não apaga nada. O histórico e a configuração ficam.
            </span>
          </div>
        ) : (
          <div className="space-y-2">
            <button
              onClick={() => agir(item.instalado ? 'resume' : 'install')}
              disabled={ocupado || !podeLigar.pode}
              className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {ocupado ? <Loader2 className="h-4 w-4 animate-spin" /> : <Power className="h-4 w-4" />}
              Ligar este Auxiliar
            </button>
            {!podeLigar.pode && podeLigar.motivo && (
              <p className="text-xs text-amber-600">{podeLigar.motivo}</p>
            )}
          </div>
        )}
      </Secao>

      {/* 7 · EXECUTAR AGORA — para os que têm tela própria de execução */}
      {item.tela_de_execucao && item.estado_catalogo === 'available' && (
        <Secao titulo="Executar agora">
          <Link
            href={item.tela_de_execucao}
            className="inline-flex items-center gap-1.5 rounded-md border border-border bg-surface px-3 py-2 text-sm font-medium text-foreground transition-colors hover:border-primary/40"
          >
            Abrir a tela deste Auxiliar →
          </Link>
          <p className="text-[11px] text-faint">
            Este Auxiliar também roda sob demanda, sem esperar a rotina.
          </p>
        </Secao>
      )}

      {/* 8 · ROTINAS DESTE AUXILIAR
          🔴 SPEC-078 C.4 — o painel de configuração MORA AQUI agora.
          Antes isto era um LINK para `/dashboard/auxiliares/rotinas`, uma
          página autônoma que listava as rotinas de toda a corretora e tinha um
          botão "Nova rotina" sem dono. Era a quarta das quatro rotas que a
          SPEC-064 §B.3 mandou absorver, e a única que não tinha sido — e o
          botão dela foi o que produziu a rotina órfã de 17/08 às 13:01.
          O possessivo do título já estava certo desde o começo. Agora o
          conteúdo corresponde a ele. */}
      {instalado && (
        <Secao titulo="Rotinas deste Auxiliar">
          <PainelDeRotinas
            auxiliarSlug={item.slug}
            auxiliarNome={item.nome}
            auxiliarLigado={ligado}
          />
        </Secao>
      )}

      {/* 9 · HISTÓRICO */}
      <Secao titulo="Histórico">
        {item.ultima_execucao ? (
          <p className="text-sm text-muted-foreground">
            Última execução em{' '}
            {new Date(item.ultima_execucao).toLocaleString('pt-BR')}.{' '}
            <Link href="/dashboard/entregas" className="text-primary underline">
              Ver tudo que ele entregou
            </Link>
          </p>
        ) : (
          <p className="text-sm text-muted-foreground">
            Ainda não rodou nenhuma vez.
          </p>
        )}
      </Secao>
    </div>
  );
}
