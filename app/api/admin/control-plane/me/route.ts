// SPEC-061 §7.2 e §8.4 — quem sou eu e o que posso ver.
//
// Esta rota substitui a leitura de `localStorage` que o layout do Admin fazia
// para decidir o que mostrar. A diferença não é de estilo: o `localStorage`
// pode ser editado por quem está na frente do navegador, e a lista de rotas
// protegidas vivia lá.
//
// O menu passa a ser DERIVADO das permissions — §8.4. Mostrar um item que
// devolve 403 ao ser clicado ensina o operador a duvidar da tela inteira, e
// uma tela em que não se confia deixa de ser usada.
import { NextResponse } from 'next/server';
import { resolverAutoridade } from '@/lib/admin/control-plane/authority';

export const dynamic = 'force-dynamic';

// §10 — a arquitetura de informação. Cada área abre com a permission que a
// sustenta: sem ela, o item nem é enviado ao navegador.
const AREAS: { chave: string; rotulo: string; href: string; permission: string }[] = [
  { chave: 'visao', rotulo: 'Visão geral', href: '/admin', permission: 'admin.overview.read' },
  { chave: 'inbox', rotulo: 'O que precisa de mim', href: '/admin/inbox', permission: 'admin.inbox.read' },
  { chave: 'corretoras', rotulo: 'Corretoras', href: '/admin/companies', permission: 'companies.read' },
  { chave: 'operacao', rotulo: 'Trabalhos em andamento', href: '/admin/trabalhos', permission: 'work_runs.read' },
  { chave: 'inteligencia', rotulo: 'O que o sistema percebeu', href: '/admin/inteligencia', permission: 'intelligence.read' },
  { chave: 'pesquisa', rotulo: 'O que buscamos na internet', href: '/admin/pesquisa', permission: 'research.read' },
  { chave: 'conhecimento', rotulo: 'Conhecimento', href: '/admin/knowledge-base', permission: 'knowledge.read' },
  { chave: 'conexoes', rotulo: 'Conexões', href: '/admin/connectors', permission: 'connections.read' },
  { chave: 'financeiro', rotulo: 'Financeiro', href: '/admin/finops', permission: 'finance.read' },
  { chave: 'governanca', rotulo: 'Quem pode o quê', href: '/admin/governanca', permission: 'audit.read' },
];

export async function GET() {
  const a = await resolverAutoridade();

  if (!a) {
    return NextResponse.json({ ok: false, error: 'no_admin_session' }, { status: 401 });
  }

  if (!a.temAcesso) {
    // Menu vazio é mais honesto que menu cheio de 403.
    return NextResponse.json({
      ok: true,
      temAcesso: false,
      papeis: [],
      permissions: [],
      menu: [],
      mensagem: 'Sua conta não tem papel administrativo ativo.',
    });
  }

  const visiveis = a.podeTudo ? AREAS : AREAS.filter((x) => a.permissions.has(x.permission));

  return NextResponse.json({
    ok: true,
    temAcesso: true,
    papeis: a.papeis,
    papeisLegiveis: a.papeisLegiveis,
    permissions: Array.from(a.permissions).sort(),
    // Quando a autoridade veio da rede de segurança, a tela precisa DIZER.
    // Um Admin que funciona sem o serviço de controle é um Admin cujas
    // concessões de papel não estão sendo lidas — e alguém precisa saber
    // disso antes de concluir que "não tem ninguém com papel".
    degradado: Boolean(a.degradado),
    avisoDegradado: a.degradado
      ? 'O serviço de controle não respondeu. Você está vendo tudo pelo acesso histórico de dono da plataforma; papéis atribuídos não estão sendo aplicados agora.'
      : null,
    menu: visiveis.map(({ permission, ...resto }) => resto),
  });
}
