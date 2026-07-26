// SPEC-061 §6.3 — redirecionamento permanente.
//
// Esta tela ("Configurar Agente") era da CORRETORA e morava em /admin. §6 exige a
// separação definitiva das superfícies: /admin é a administração da
// plataforma; a corretora trabalha no /dashboard, que é a casa dela.
//
// O arquivo continua existindo, e só redireciona, porque link salvo não some
// quando a rota muda: e-mail de convite, favorito no navegador, mensagem
// antiga no WhatsApp. Apagar a rota transformaria cada um deles num 404.
//
// Quando a telemetria mostrar que ninguém mais chega por aqui, este arquivo
// pode sair. Antes disso, não.
import { redirect } from 'next/navigation';

export default function RedirecionaParaAgente() {
  redirect('/dashboard/agente');
}
