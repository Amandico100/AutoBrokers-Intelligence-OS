// SPEC-061 §6 — desfazendo uma DUPLICAÇÃO, não a separação.
//
// Esta tela era o "Gerenciar Agentes IA" do /admin. Eu a movi para cá achando
// que estava mudando de casa. Não estava: a casa já existia.
//
// O `/dashboard/personalizacao` já tinha, desde a SPEC-045, uma tela feita PARA
// a corretora — com linguagem de gente ("Criatividade" no lugar de
// `temperature`), trilha de navegação, e sem botão de criar nem de apagar.
// Mover esta para cá não organizou nada: passou a haver duas telas de agente no
// mesmo dashboard, e a que ficou visível era a errada.
//
// Ela trazia "Criar Novo Agente" e uma lixeira. A lixeira apagava
// `autobrokers-sandbox` — o agente ATIVO que É o chat da corretora. Um corretor
// curioso desligaria o próprio produto sem entender o que fez.
//
// Decisão do Founder em 27/07/2026: o motor de construir agentes fica no
// /admin, onde já está (`/admin/companies/<id>/agents`), para a plataforma
// personalizar quando um cliente pedir. A corretora vê só o que é dela.
//
// O código antigo não se perdeu: `git log --follow app/dashboard/agente/page.tsx`.
import { redirect } from 'next/navigation';

export default function RedirecionaParaMeuAgente() {
  redirect('/dashboard/personalizacao/agentes/autobrokers');
}
