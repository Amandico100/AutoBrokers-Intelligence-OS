'use client';

import { useCallback, useEffect, useState } from 'react';
import { CalendarClock, Loader2, Lock, MessageCircle, Plug, Save, SlidersHorizontal, User } from 'lucide-react';
import { toast } from 'sonner';

import { useUserId } from '@/hooks/useUserId';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { AvatarUpload } from '@/components/AvatarUpload';
import { ThemeToggle } from '@/components/ThemeToggle';
import { DetailHeader } from '@/components/patterns';
import { icons } from '@/lib/icons';
import { MinhasConexoes } from '@/components/perfil/MinhasConexoes';
import { MeuWhatsAppDeTrabalho } from '@/components/perfil/MeuWhatsAppDeTrabalho';
import { MinhaAusencia } from '@/components/perfil/MinhaAusencia';
import { useMeuPerfil } from '@/components/perfil/useMeuPerfil';
import { BOTAO_PRIMARIO } from '@/components/aplicativos/casca/CardDoAplicativo';

/**
 * "Meu perfil" — a camada da PESSOA (SPEC-064 Bloco B). SPEC-131-B G3 (laudo I2 §5, D-131-07/08/41): Dados · Minhas
 * conexões (o MEU Agger) · Meu WhatsApp de trabalho (só o número, confirmado) · Ausência (período + OUTRA pessoa) ·
 * Segurança · Aparência. "Uso e custos" é da CORRETORA e saiu daqui: mora em Personalização → Custos.
 * A aba vem de `?aba=` (para os links "mudar" do aplicativo abrirem direto aqui).
 */
const ABAS = [
  { id: 'dados', rotulo: 'Dados', icone: User },
  { id: 'conexoes', rotulo: 'Minhas conexões', icone: Plug },
  { id: 'whatsapp', rotulo: 'WhatsApp de trabalho', icone: MessageCircle },
  { id: 'ausencia', rotulo: 'Ausência', icone: CalendarClock },
  { id: 'seguranca', rotulo: 'Segurança', icone: Lock },
  { id: 'aparencia', rotulo: 'Aparência', icone: SlidersHorizontal },
] as const;
type Aba = (typeof ABAS)[number]['id'];
const eAba = (v: string | null): v is Aba => ABAS.some((a) => a.id === v);

export default function MeuPerfilPage() {
  const { userId } = useUserId();
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [aba, setAba] = useState<Aba>('dados');
  const { perfil, carregar: recarregarPerfil } = useMeuPerfil();

  const [profile, setProfile] = useState({
    first_name: '', last_name: '', email: '', phone: '', cpf: '', birth_date: '', avatar_url: '',
  });
  const [passwords, setPasswords] = useState({ current: '', new: '', confirm: '' });

  // `?aba=` lido no navegador (sem useSearchParams: a página não precisa de Suspense para pré-renderizar)
  useEffect(() => {
    try {
      const v = new URLSearchParams(window.location.search).get('aba');
      if (eAba(v)) setAba(v);
    } catch { /* fica Dados */ }
  }, []);

  const trocarAba = (v: string) => {
    if (!eAba(v)) return;
    setAba(v);
    try {
      const url = new URL(window.location.href);
      url.searchParams.set('aba', v);
      window.history.replaceState(null, '', url.toString());
    } catch { /* a aba muda mesmo sem a URL */ }
  };

  const loadProfile = useCallback(async () => {
    try {
      const response = await fetch('/api/user/profile?full=true');
      if (!response.ok) throw new Error('Failed to load profile');
      const data = await response.json();
      setProfile({
        first_name: data.first_name || '', last_name: data.last_name || '', email: data.email || '',
        phone: data.phone || '', cpf: data.cpf || '', birth_date: data.birth_date || '', avatar_url: data.avatar_url || '',
      });
    } catch {
      toast.error('Não conseguimos carregar os seus dados.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => { if (userId) loadProfile(); }, [userId, loadProfile]);

  const handleUpdateProfile = async () => {
    setIsSaving(true);
    try {
      const response = await fetch('/api/user/profile', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          first_name: profile.first_name, last_name: profile.last_name, phone: profile.phone, avatar_url: profile.avatar_url,
        }),
      });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.error || 'Não conseguimos salvar.');
      }
      toast.success('Dados salvos.');
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : 'Não conseguimos salvar.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleChangePassword = async () => {
    if (!passwords.current || !passwords.new || !passwords.confirm) { toast.warning('Preencha os três campos de senha.'); return; }
    if (passwords.new !== passwords.confirm) { toast.error('A nova senha e a confirmação não conferem.'); return; }
    if (passwords.new.length < 6) { toast.error('A nova senha precisa ter pelo menos 6 caracteres.'); return; }
    setIsSaving(true);
    try {
      const response = await fetch('/api/auth/change-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userId, currentPassword: passwords.current, newPassword: passwords.new }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error || 'Não conseguimos trocar a senha.');
      toast.success('Senha trocada.');
      setPasswords({ current: '', new: '', confirm: '' });
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : 'Não conseguimos trocar a senha.');
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center bg-background text-muted-foreground">
        <Loader2 className="mr-2 h-6 w-6 animate-spin" aria-hidden /> Carregando…
      </div>
    );
  }

  const cartao = 'space-y-6 rounded-xl border border-border bg-surface p-4 sm:p-6';

  return (
    <div className="h-full overflow-y-auto bg-background text-foreground">
      <div className="mx-auto w-full max-w-4xl space-y-6 px-4 py-6 sm:px-6 sm:py-10">
        <DetailHeader
          icon={icons.configuracoes}
          title="Meu perfil"
          subtitle="Seus dados, as suas conexões, o WhatsApp em que você atende e as suas ausências."
        />

        <Tabs value={aba} onValueChange={trocarAba} className="w-full">
          <div className="-mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0">
            <TabsList className="inline-flex h-auto w-max gap-1 border border-border bg-muted p-1">
              {ABAS.map((a) => (
                <TabsTrigger key={a.id} value={a.id}
                  className="min-h-11 whitespace-nowrap px-3 sm:min-h-10 text-sm data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-sm">
                  <a.icone className="mr-2 h-4 w-4" strokeWidth={1.6} aria-hidden /> {a.rotulo}
                </TabsTrigger>
              ))}
            </TabsList>
          </div>

          <TabsContent value="dados" className="mt-6">
            <section className={cartao}>
              <div className="flex items-center gap-6">
                {userId && (
                  <AvatarUpload
                    currentImageUrl={profile.avatar_url}
                    onUpload={(url) => setProfile({ ...profile, avatar_url: url })}
                    uploadPath="users"
                    entityId={userId}
                    size="h-24 w-24"
                    fallback={`${profile.first_name} ${profile.last_name}`}
                  />
                )}
                <div>
                  <h2 className="text-base font-semibold text-foreground">Foto de perfil</h2>
                  <p className="text-sm text-muted-foreground">Toque na imagem para trocar.</p>
                </div>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="perfil-nome" className="text-foreground">Nome</Label>
                  <Input id="perfil-nome" value={profile.first_name}
                    onChange={(e) => setProfile({ ...profile, first_name: e.target.value })} className="bg-background" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="perfil-sobrenome" className="text-foreground">Sobrenome</Label>
                  <Input id="perfil-sobrenome" value={profile.last_name}
                    onChange={(e) => setProfile({ ...profile, last_name: e.target.value })} className="bg-background" />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="perfil-telefone" className="text-foreground">Telefone de contato</Label>
                <Input id="perfil-telefone" value={profile.phone} inputMode="tel"
                  onChange={(e) => setProfile({ ...profile, phone: e.target.value })} className="bg-background" />
                <p className="text-sm text-muted-foreground">
                  O WhatsApp em que você atende os clientes fica na aba WhatsApp de trabalho.
                </p>
              </div>
              <div className="grid gap-4 sm:grid-cols-3">
                <div className="space-y-2">
                  <Label htmlFor="perfil-email" className="text-foreground">E-mail</Label>
                  <Input id="perfil-email" value={profile.email} disabled className="bg-muted text-muted-foreground" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="perfil-cpf" className="text-foreground">CPF</Label>
                  <Input id="perfil-cpf" value={profile.cpf} disabled className="bg-muted text-muted-foreground" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="perfil-nascimento" className="text-foreground">Data de nascimento</Label>
                  <Input id="perfil-nascimento" type="date" value={profile.birth_date} disabled
                    className="block w-full bg-muted text-muted-foreground" />
                </div>
              </div>
              <p className="text-sm text-muted-foreground">E-mail, CPF e data de nascimento não se mudam por aqui.</p>
              <div className="flex justify-end">
                <Button onClick={handleUpdateProfile} disabled={isSaving} className={`h-11 ${BOTAO_PRIMARIO}`}>
                  {isSaving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden /> : <Save className="mr-2 h-4 w-4" aria-hidden />}
                  Salvar dados
                </Button>
              </div>
            </section>
          </TabsContent>

          <TabsContent value="conexoes" className="mt-6">
            <MinhasConexoes />
          </TabsContent>

          <TabsContent value="whatsapp" className="mt-6">
            <section className={cartao}>
              <MeuWhatsAppDeTrabalho perfil={perfil} onMudou={recarregarPerfil} />
            </section>
          </TabsContent>

          <TabsContent value="ausencia" className="mt-6">
            <section className={cartao}>
              <MinhaAusencia perfil={perfil} onMudou={recarregarPerfil} />
            </section>
          </TabsContent>

          <TabsContent value="seguranca" className="mt-6">
            <section className={cartao}>
              <div className="space-y-1">
                <h2 className="text-base font-semibold text-foreground">Trocar a senha</h2>
                <p className="text-sm text-muted-foreground">Para sua segurança, confirme a senha atual.</p>
              </div>
              <div className="max-w-md space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="senha-atual" className="text-foreground">Senha atual</Label>
                  <Input id="senha-atual" type="password" autoComplete="current-password" value={passwords.current}
                    onChange={(e) => setPasswords({ ...passwords, current: e.target.value })} className="bg-background" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="senha-nova" className="text-foreground">Nova senha</Label>
                  <Input id="senha-nova" type="password" autoComplete="new-password" value={passwords.new}
                    onChange={(e) => setPasswords({ ...passwords, new: e.target.value })} className="bg-background" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="senha-confirma" className="text-foreground">Confirme a nova senha</Label>
                  <Input id="senha-confirma" type="password" autoComplete="new-password" value={passwords.confirm}
                    onChange={(e) => setPasswords({ ...passwords, confirm: e.target.value })} className="bg-background" />
                </div>
                <Button onClick={handleChangePassword} disabled={isSaving} className={`h-11 w-full ${BOTAO_PRIMARIO}`}>
                  {isSaving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden /> : <Lock className="mr-2 h-4 w-4" aria-hidden />}
                  Trocar a senha
                </Button>
              </div>
            </section>
          </TabsContent>

          <TabsContent value="aparencia" className="mt-6">
            <section className={cartao}>
              <div className="flex items-center justify-between gap-4">
                <div>
                  <h2 className="text-base font-semibold text-foreground">Modo de cor</h2>
                  <p className="text-sm text-muted-foreground">Alterna entre claro e escuro.</p>
                </div>
                <ThemeToggle />
              </div>
            </section>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
