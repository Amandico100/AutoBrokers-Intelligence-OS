'use client';

// SPEC-EXTRA-001.5 · BLOCO D ① — o que o assistente já sabe sobre os planos.
//
// 🔴 A régua conta SEGURADORA × RAMO, nunca linhas. 40 linhas de um ramo só não
// são cobertura: são um ramo só, bem descrito. Contar linhas é o defeito que
// `tests/test_cobertura_nao_mente_para_cima.py` documenta (📊 Allianz: painel
// 63 %, real 37 %) — quem lê "63 %" não vai atrás do que falta.
//
// ⚠️ Linguagem HUMANA: nada de nome de tabela, coluna, SQL ou chave interna.

type Linha = { insurer_key: string; ramo: string; planos: number; servicos: number; estado: string };
type Resumo = {
  seguradora_ramo_com_plano_publicado: number;
  seguradoras_com_condicao_geral: number;
  itens_na_fila: number;
};

const NOME: Record<string, string> = {
  allianz: 'Allianz', azul: 'Azul', bradesco: 'Bradesco', hdi: 'HDI', mapfre: 'Mapfre',
  porto: 'Porto', tokio: 'Tokio Marine', yelum: 'Yelum', alfa: 'Alfa', sompo: 'Sompo',
  suhai: 'Suhai', sulamerica: 'SulAmérica', sura: 'Sura', zurich: 'Zurich', itau: 'Itaú',
};
const RAMO: Record<string, string> = {
  auto: 'Automóvel', residencial: 'Residencial', condominio: 'Condomínio',
  empresarial: 'Empresarial', vida: 'Vida', equipamentos: 'Equipamentos',
  garantia: 'Garantia', responsabilidade_civil: 'Responsabilidade civil', geral: 'Geral',
};

export function humanizarSeguradora(k: string): string {
  return NOME[k] || (k || '').replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}
export function humanizarRamo(k: string): string {
  return RAMO[k] || (k || '').replace(/_/g, ' ');
}

export function CoberturaDePlanos({ linhas, resumo }: { linhas: Linha[]; resumo?: Resumo }) {
  const publicadas = linhas.filter((l) => l.estado === 'publicada');

  return (
    <div className="rounded-lg border border-border bg-card p-4 space-y-3">
      <div>
        <p className="text-sm font-medium text-foreground">O que o assistente já sabe sobre os planos</p>
        <p className="mt-1 text-[11px] text-faint">
          Isto é o que ele pode afirmar sobre carro reserva, guincho, vidros e chaveiro citando a
          página das condições gerais. Onde não houver nada publicado, ele responde que ainda não
          sabe — e nunca inventa um &quot;não&quot;.
        </p>
        {/* 🔴 BLOCO D ③ — a base é de todas. Dito em uma linha, sem jargão. */}
        <p className="mt-1 text-[11px] text-faint">
          Esta base é a mesma para todas as corretoras: o que a apólice de uma seguradora cobre não
          muda de corretora para corretora. Trocar de empresa aqui em cima não muda nada nesta lista.
        </p>
      </div>

      {resumo && (
        <div className="grid grid-cols-3 gap-2 text-center">
          {/* 🔴 Os três números que é tentador juntar, separados (SPEC §9). */}
          {[
            { n: resumo.seguradora_ramo_com_plano_publicado, t: 'seguradora e ramo com plano publicado' },
            { n: resumo.seguradoras_com_condicao_geral, t: 'seguradoras com condições gerais no acervo' },
            { n: resumo.itens_na_fila, t: 'linhas esperando revisão' },
          ].map((c) => (
            <div key={c.t} className="rounded-md border border-border bg-background p-2">
              <p className="text-lg font-semibold text-foreground">{c.n}</p>
              <p className="text-[10px] leading-tight text-faint">{c.t}</p>
            </div>
          ))}
        </div>
      )}

      {publicadas.length === 0 ? (
        // 🔴 BLOCO D ④ — estado vazio HONESTO. Nada de "0%" que pareça falha do
        // produto, nada de barra cheia que pareça pronto.
        <p className="text-sm text-muted-foreground">
          Nenhum plano publicado ainda. Enquanto isso, o assistente responde &quot;ainda não sei&quot;
          às perguntas de cobertura — que é a resposta certa até alguém revisar a primeira linha.
        </p>
      ) : null}

      {linhas.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="text-faint">
              <tr>
                <th className="py-1 pr-3 font-normal">Seguradora</th>
                <th className="py-1 pr-3 font-normal">Ramo</th>
                <th className="py-1 pr-3 font-normal">Planos</th>
                <th className="py-1 pr-3 font-normal">Serviços</th>
                <th className="py-1 font-normal">Situação</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {linhas.map((l, i) => (
                <tr key={`${l.insurer_key}-${l.ramo}-${i}`}>
                  <td className="py-1.5 pr-3 text-foreground">{humanizarSeguradora(l.insurer_key)}</td>
                  <td className="py-1.5 pr-3 text-muted-foreground">{humanizarRamo(l.ramo)}</td>
                  <td className="py-1.5 pr-3 text-muted-foreground">{l.planos || '—'}</td>
                  <td className="py-1.5 pr-3 text-muted-foreground">{l.servicos || '—'}</td>
                  <td className="py-1.5">
                    {l.estado === 'publicada' ? (
                      <span className="text-emerald-600">Condições gerais lidas e revisadas</span>
                    ) : (
                      <span className="text-amber-600">🔴 nenhuma linha publicada</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
