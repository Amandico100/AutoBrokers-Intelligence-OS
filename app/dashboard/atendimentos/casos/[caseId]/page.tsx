import CaseDetailClient from './CaseDetailClient';

export const metadata = { title: 'Caso · Atendimentos' };

export default async function CaseDetailPage({ params }: { params: Promise<{ caseId: string }> }) {
  const { caseId } = await params;
  return <CaseDetailClient caseId={caseId} />;
}
