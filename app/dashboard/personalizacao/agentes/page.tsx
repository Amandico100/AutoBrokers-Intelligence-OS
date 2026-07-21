import { redirect } from 'next/navigation';

// SPEC-045: a etapa intermediária "Agentes" morreu — o card AutoBrokers é
// direto na grade e o Agente de Atendimento vive dentro de Corretora.
export default function AgentesPage() {
  redirect('/dashboard/personalizacao');
}
