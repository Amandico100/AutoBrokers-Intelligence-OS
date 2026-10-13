'use client';

// SPEC-064 Bloco C.3 — a página de UM Auxiliar. SPEC-131-B — a CASCA de todo aplicativo (laudo de design §3):
//
//   cabeçalho (capa, ícone, nome, frase, selo, botão principal por estado, "Funciona com")
//   abas por `?aba=`: Início · Configurar · o trabalho feito (quem tem) · Dúvidas
//
// Este arquivo é o maestro: lê a aba da URL, decide o botão (`botaoPrincipal`), monta os passos do "Como começar"
// (`passosDoComoComecar`) e fala com a API de instalar/ligar/desligar. O desenho mora em
// components/aplicativos/casca/*; as abas próprias (Renovações, o Configurar da Renovação/Cotação/QCM) são de G2/G3
// e entram por import dinâmico (`ABAS_DO_APLICATIVO`).
//
// O Configurar dos aplicativos com rotina continua sendo o painel de hoje — `PainelDeRotinas`, a Cobrança intocada
// (D-131-19). 🔴 SPEC-078 C.4: o painel mora DENTRO da tela do aplicativo; nunca um link para outra página.

import { useMemo, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

import PainelDeRotinas from '@/components/auxiliares/PainelDeRotinas';
import { AbasDoAplicativo } from '@/components/aplicativos/casca/AbasDoAplicativo';
import { AbaDuvidas } from '@/components/aplicativos/casca/AbaDuvidas';
import { AbaInicio } from '@/components/aplicativos/casca/AbaInicio';
import { CabecalhoDoAplicativo } from '@/components/aplicativos/casca/CabecalhoDoAplicativo';
import {
  abaValida,
  abasDoAplicativo,
  botaoPrincipal,
  contagemDosPassos,
  LINK_CONECTORES,
  NOME_HUMANO_DA_CONEXAO,
  passosDoComoComecar,
  type AtividadeDoAplicativo,
  type ConexaoDoAplicativo,
  type FontesDoComoComecar,
  type ItemDoCatalogo,
} from '@/lib/auxiliaries/catalog';

interface Props {
  item: ItemDoCatalogo;
  podeLigar: { pode: boolean; motivo?: string };
  atividade: AtividadeDoAplicativo[];
  fontes: FontesDoComoComecar;
}

/** Os aplicativos do multicálculo trabalham no Agger — ele entra no "Funciona com" pela prontidão (o cofre). */
const USAM_O_AGGER = new Set(['renovacao', 'cotacao', 'quem-cobra-menos']);

function conexoesDoCabecalho(item: ItemDoCatalogo, fontes: FontesDoComoComecar): ConexaoDoAplicativo[] {
  const lista = [...item.conexoes];
  if (USAM_O_AGGER.has(item.slug)) {
    const p = fontes.prontidao?.find((x) => x.chave === 'agger_da_corretora');
    lista.push({
      slug: 'agger',
      nome: 'Agger',
      pronto: p ? p.estado === 'pronto' : null,
      onde: LINK_CONECTORES,
    });
  }
  return lista;
}

export default function AuxiliarDetalheClient({ item, podeLigar, atividade, fontes }: Props) {
  const router = useRouter();
  const busca = useSearchParams();
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState('');

  const abas = useMemo(() => abasDoAplicativo(item), [item]);
  const abaAtual = abaValida(abas, busca?.get('aba'));
  const passos = useMemo(() => passosDoComoComecar(item, fontes), [item, fontes]);
  const { prontos, total } = contagemDosPassos(passos);
  const botao = botaoPrincipal(item);
  const conexoes = useMemo(() => conexoesDoCabecalho(item, fontes), [item, fontes]);

  async function agir(action: 'install' | 'resume' | 'pause', opcoes?: { confirmado?: boolean }) {
    setOcupado(true);
    setErro('');
    try {
      const r = await fetch(`/api/dashboard/auxiliaries/${item.template_id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        // o "Ligar" que passou pela confirmação leva `confirmar_ligar` — sem ele a API não liga a Renovação (K1)
        body: JSON.stringify(opcoes?.confirmado ? { action, confirmar_ligar: true } : { action }),
      });
      const j = await r.json().catch(() => null);
      if (!r.ok || j?.ok === false) {
        // O servidor recusa por dois motivos com texto próprio: "em breve" e "falta conectar". Repassar o motivo é o
        // que evita o corretor achar que o produto está quebrado.
        //
        // 🔴 A causa técnica vem em `details` (📊 17/08/2026: o Founder via só `install_failed`; `details[0]` trazia
        // a mensagem exata do banco). SPEC-131-B (laudo de design §1, item 17): ela vai para o LOG, inteira, e a tela
        // fala português — o erro técnico cru na tela era o defeito 17.
        const tecnico = Array.isArray(j?.details) ? String(j.details[0] || '').trim() : '';
        if (tecnico || j?.error) console.error('[APLICATIVO]', item.slug, action, j?.error, tecnico);
        const faltando: string[] = Array.isArray(j?.faltando) ? j.faltando : [];
        const nomes = faltando.map(
          (s) => item.conectores_pendentes.find((c) => c.slug === s)?.nome ?? NOME_HUMANO_DA_CONEXAO[s] ?? 'uma conexão',
        );
        setErro(
          j?.detalhe ||
            (nomes.length ? `Conecte antes: ${nomes.join(', ')}.` : null) ||
            'Não deu para concluir agora. Tente de novo em instantes; se continuar, fale com o suporte.',
        );
        return;
      }
      if (action === 'install' && !item.sem_rotina && botao.tipo === 'acao' && botao.rotulo === 'Instalar') {
        // instalar abre o Configurar — é ali que se diz o que ele faz antes de ligar (laudo de design §3)
        router.push(`/dashboard/auxiliares/${item.slug}?aba=configurar`, { scroll: false });
      }
      router.refresh();
    } catch (e) {
      console.error('[APLICATIVO] falha de conexão', e);
      setErro('Sem conexão com o servidor agora. Tente de novo em instantes.');
    } finally {
      setOcupado(false);
    }
  }

  const ligado = item.estado === 'ligado';
  // Instalado ≠ ligado. Um aplicativo PAUSADO continua dono das rotinas dele, e é justamente pausado que a corretora
  // quer configurar antes de ligar (📊 17/08/2026: a Cobrança Feita instalada `inactive`, com uma rotina gravada que
  // era invisível pela interface).
  const instalado = ligado || item.estado === 'pausado';

  const configurarPadrao = instalado ? (
    <section className="space-y-4 pt-8">
      <div>
        <h2 className="text-lg font-semibold text-foreground">Rotinas deste aplicativo</h2>
        <p className="mt-0.5 text-sm text-muted-foreground">
          O que ele faz, quando e para quem. A configuração fica guardada mesmo desligado.
        </p>
      </div>
      <PainelDeRotinas auxiliarSlug={item.slug} auxiliarNome={item.nome} auxiliarLigado={ligado} />
    </section>
  ) : null;

  // Configurar com ponto de atenção quando o passo de configuração ainda falta
  const marcadas = passos.some((p) => (p.chave === 'configurar' || p.chave === 'servicos') && p.estado !== 'pronto')
    ? ['configurar']
    : [];

  return (
    <div>
      <CabecalhoDoAplicativo
        item={item}
        botao={botao}
        conexoes={conexoes}
        resumoDosPassos={`${prontos} de ${total} prontos`}
        ocupado={ocupado}
        erro={erro}
        motivoDeNaoLigar={
          item.estado_catalogo !== 'coming_soon' && item.estado !== 'falta_conectar' && !podeLigar.pode
            ? podeLigar.motivo
            : undefined
        }
        onAcao={agir}
        compacto={abaAtual !== 'inicio'}
      />

      <AbasDoAplicativo
        item={item}
        abas={abas}
        abaAtual={abaAtual}
        marcadas={marcadas}
        conteudo={{
          inicio: (
            <AbaInicio
              item={item}
              passos={passos}
              atividade={atividade}
              hrefDuvidas={`/dashboard/auxiliares/${item.slug}?aba=duvidas`}
            />
          ),
          configurar: configurarPadrao,
          duvidas: (
            <div className="pt-8">
              <AbaDuvidas faq={item.faq} />
            </div>
          ),
        }}
      />
    </div>
  );
}
