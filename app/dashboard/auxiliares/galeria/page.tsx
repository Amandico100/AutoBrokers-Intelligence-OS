// SPEC-013 — Galeria consolidada na página única de Auxiliares (sem telas duplicadas).
// A rota antiga redireciona para /dashboard/auxiliares/meus (catálogo + instalar + gerenciar).
import { redirect } from 'next/navigation';

export default function GaleriaRedirectPage() {
  redirect('/dashboard/auxiliares/meus');
}
