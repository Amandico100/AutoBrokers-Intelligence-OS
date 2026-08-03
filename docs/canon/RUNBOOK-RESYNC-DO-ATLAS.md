# Runbook — recolher o que a Fase 0 plantou

> **03/08/2026.** A leitura do clique foi consertada e está em produção. Os
> dados **já capturados** continuam cegos: o conserto vale para a leitura, não
> reescreve o passado. Este runbook recolhe.
>
> ⛔ **Bloqueado até o pareamento.** 📊 Em 03/08 os três observadores estão
> `disconnected` — o `history-sync` puxa da instância conectada, e não há
> nenhuma. **Rodar agora não traz nada.**

---

## A linha de base, gravada antes (📊 03/08/2026)

```
cliques de botão vindos do histórico ......... 947
    destes, COM id legível ................... 0        ← o defeito
respostas de formulário nativo ............... 24       ← também cegas
eventos observados, no total ................. 17.488
arestas rotuladas apenas "→" (10 mapas) ...... 1.805 de 4.999  (36,1%)
```

**Depois do re-sync, `com_id` tem de subir de 0.** Se continuar 0, o sync não
trouxe nada e **não se apaga nada**.

---

## A sequência — e a ordem NÃO é a intuitiva

⚠️ O banco usa `ON CONFLICT DO NOTHING`. **Re-sincronizar nunca corrige uma
linha existente.** As boas entram *ao lado* das quebradas. Por isso a
verificação vem antes de apagar, sempre.

### 1 · Parear os WhatsApps 🧑
Sem instância conectada não há histórico para puxar.

### 2 · Confirmar que o conserto está no ar 🤖
```sql
-- tem de existir pelo menos um evento novo COM id
select count(*) from observed_events
 where msg_type in ('button_reply','flow_reply')
   and coalesce(interactive->>'id','') <> ''
   and source = 'live';
```
Se der 0 depois de alguma conversa real, **pare**: o conserto não está ativo e
o re-sync só duplicaria o problema.

### 3 · Puxar o histórico 🤖
```
POST /api/admin/atlas/observer/history-sync     (master admin)
body: {"count": N}
```
Exige `EVOLUTION_GO_BASE_URL` e `EVOLUTION_GO_INSTANCE_TOKEN`.

### 4 · VERIFICAR antes de apagar 🤖 — o passo que não se pula
```sql
select count(*) as com_id from observed_events
 where source='history_sync' and msg_type='button_reply'
   and interactive->>'id' is not null;
```
**Era 0. Se continuar 0, NÃO APAGUE NADA** — o WhatsApp pode já não guardar
aquelas mensagens, e apagar deixaria menos do que havia.

### 5 · Só então apagar as cegas 🤖
Os **dois** critérios juntos, nunca um só:
```sql
delete from observed_events
 where interactive->>'id' is null
   and created_at < '<momento exato do re-sync>';
```

### 6 · Retecer 🤖
```
POST /api/admin/atlas/weave        (sem body = todas as seguradoras)
```
Idempotente. Só aqui a cobertura passa a significar alguma coisa.

---

## O que NÃO é recuperável

📊 **20 eventos `source='live'`** (14 observados + 6 de transcrição). O
`history-sync` não os traz — eles nasceram do webhook. **Não apague.** Daqui
para frente nascem certos.

## O que esperar depois

📊 Recuperáveis: **1.603** linhas em `observed_events` + **430** em
`attendance_transcripts` (esta só se a integração tiver escopo
`insurers_and_clients`).

E a pergunta *"por que 440 telas se a URA tem ~90 menus?"* se resolve **aqui**,
não no denominador: com o detector de fase humana corrigido, o handoff dispara
20× mais cedo, `nodes_humano` sobe muito acima de 53 e `nodes_ura` cai.
