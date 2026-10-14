export async function uploadVoiceMessage(audioBlob: Blob): Promise<string | null> {
  try {
    const formData = new FormData();
    formData.append('file', audioBlob, `${Date.now()}-${crypto.randomUUID()}.webm`);
    formData.append('bucket', 'voice-messages');

    const response = await fetch('/api/upload', {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      console.error('Error uploading audio:', error);
      return null;
    }

    const data = await response.json();
    // SPEC-132-A (A4) — a rota nunca devolveu `publicUrl`. O `voice-messages` não é público: a URL é a do proxy
    // autenticado (`url`), e sem ela a referência durável (`storagePath`). Nunca `undefined` calado.
    if (typeof data?.url === 'string' && data.url) return data.url;
    if (typeof data?.storagePath === 'string' && data.storagePath) return data.storagePath;
    return null;
  } catch (error) {
    console.error('Error in uploadVoiceMessage:', error);
    return null;
  }
}
