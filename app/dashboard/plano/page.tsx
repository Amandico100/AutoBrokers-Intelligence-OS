// SPEC-061 §6 + SPEC-062 §4 — desfazendo uma DUPLICAÇÃO, e fechando uma porta
// que não deveria estar aberta.
//
// Esta era a tela "Meu Plano" do /admin. O dashboard já tinha a dele:
// `/dashboard/personalizacao/custos` — "saldo e consumo reais da sua corretora,
// por agente, por pessoa e por modelo", com a frase que importa no rodapé:
// *"valores reais do seu consumo. Nenhum custo é estimado ou inventado."*
//
// Mas aqui não era só duplicação. Esta tela oferecia ASSINATURA:
//
//     POST /api/billing/checkout/subscription
//     POST /api/billing/portal
//
// com `STRIPE_SECRET_KEY=sk_test_..._placeholder_do_not_use_...` e um
// `success_url` apontando para `/admin/billing`, endereço que não existe mais.
// Um corretor que clicasse em "assinar" receberia um erro de pagamento vindo do
// nada — num produto cujo catálogo comercial o Founder ainda não aprovou.
//
// A SPEC-062 §4 lei 17 é explícita: a venda não começa antes do catálogo
// comercial aprovado. Enquanto `BILLING_ENFORCEMENT` estiver desligado, a
// corretora vê o que CONSOME. O que ela PAGA aparece quando houver preço.
//
// A tela inteira está preservada em git e volta quando o catálogo existir:
// `git log --follow app/dashboard/plano/page.tsx`.
import { redirect } from 'next/navigation';

export default function RedirecionaParaCustos() {
  redirect('/dashboard/personalizacao/custos');
}
