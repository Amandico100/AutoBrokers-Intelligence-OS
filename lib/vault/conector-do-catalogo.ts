// SPEC-133-A.1 F3 — o que um clique num conector do catálogo ABRE.
//
// 📊 O DEFEITO, MEDIDO NA TELA (10/10/2026, retorno do Founder): "quando quero refazer e clico em InfoCap, se já
// estiver conectado, aparece para criar nova conexão… isso confunde". Em `conectores/page.tsx` o clique só olhava
// `status === 'connected'`: com a InfoCap em `configuring`, `error`, `disconnected` ou `draft` — exatamente o
// momento de "refazer" — caía em `openCreate(t)` e abria "Preparar InfoCap", que grava uma conexão NOVA ao lado
// da que existe. Cada "refazer" deixava mais uma.
//
// A regra, igual para todo conector desta tela (sem mudar o que eles gravam):
//   · JÁ existe uma conexão (qualquer status menos arquivada) → abre A EXISTENTE (estado, editar, reconectar,
//     desconectar). Nunca um formulário de "nova".
//   · não existe nenhuma → o formulário de nova.
//   · "adicionar outra" só num botão explícito, e só no conector que permite mais de uma (OAuth: uma da corretora
//     e uma pessoal — SPEC-044).

export type ConexaoMinima = {
  id: string;
  connector_template_id: string;
  status: string;
  technical_ref_id?: string | null;
  created_at?: string | null;
};

export type AcaoDoCatalogo =
  | { tipo: 'abrir'; connectionId: string; total: number }
  | { tipo: 'nova' };

/** Prioridade para escolher QUAL abrir quando há mais de uma: conectada > configurada > a mais antiga. */
function peso(c: ConexaoMinima): number {
  if (c.status === 'connected') return 0;
  if (c.technical_ref_id) return 1;
  return 2;
}

export function conexoesDoConector(templateId: string, conexoes: ConexaoMinima[] | null | undefined): ConexaoMinima[] {
  return (conexoes || [])
    .filter((c) => c.connector_template_id === templateId && c.status !== 'archived')
    .sort((a, b) => peso(a) - peso(b)
      || new Date(a.created_at || 0).getTime() - new Date(b.created_at || 0).getTime());
}

export function oQueOCatalogoAbre(templateId: string, conexoes: ConexaoMinima[] | null | undefined): AcaoDoCatalogo {
  const existentes = conexoesDoConector(templateId, conexoes);
  if (existentes.length > 0) return { tipo: 'abrir', connectionId: existentes[0].id, total: existentes.length };
  return { tipo: 'nova' };
}

/** O texto do botão do card — o mesmo critério do clique (um não pode dizer "Preparar" e o outro abrir). */
export function rotuloDoCartao(
  acao: AcaoDoCatalogo,
  opcoes: { conectaDeUmaVez?: boolean; conectada?: boolean } = {},
): string {
  if (acao.tipo === 'abrir') return opcoes.conectada ? 'Gerenciar conexão' : 'Abrir conexão';
  // OAuth e InfoCap conectam no mesmo gesto; os outros nascem em rascunho (sem credencial).
  return opcoes.conectaDeUmaVez ? 'Conectar' : 'Preparar conexão';
}
