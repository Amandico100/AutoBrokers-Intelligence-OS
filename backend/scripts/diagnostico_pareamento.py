"""Por que ESTE canal nao pareia — a medicao que faltava. Somente LEITURA.

Rodar no console do contedor da API, em /app:

    python backend/scripts/diagnostico_pareamento.py
    python backend/scripts/diagnostico_pareamento.py --empresa <company_id>

NAO cria, NAO apaga, NAO desconecta, NAO grava nada. Tres GET por instancia.

POR QUE ESTE ARQUIVO EXISTE
---------------------------
06/08/2026. Uma atendente da Resulta passou dias sem parear. A investigacao
mediu os tokens do banco contra o provedor e achou 401 em todos — e concluiu que
a ENCRYPTION_KEY estava errada.

O experimento estava viciado: os tokens foram testados **como estao no banco**,
ou seja, CIFRADOS. Um ciphertext de 188 caracteres usado como `apikey` devolve
401 sempre, com qualquer chave, em qualquer provedor. Faltava a linha de
controle (CLAUDE.md 9.2): um token que se SABE bom, medido do mesmo jeito.

Este script e essa linha de controle. Ele abre o segredo dentro do processo —
onde a chave existe — e mede o provedor com o valor REAL. E imprime forma,
tamanho e veredito; nunca o valor (CLAUDE.md 13.3).
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _anatomia(valor: str) -> str:
    """A FORMA do segredo guardado — nunca o valor."""
    try:
        from app.services.whatsapp.integration_secrets import tem_forma_de_ciphertext
        cifrado = tem_forma_de_ciphertext(valor)
    except Exception:  # noqa: BLE001 — versao antiga do modulo
        cifrado = valor.startswith("Z0FBQUFB")
    if not cifrado:
        return f"{len(valor)} chars · PLAINTEXT legado (nunca foi cifrado)"
    try:
        miolo = base64.urlsafe_b64decode(base64.b64decode(valor).decode("ascii"))
        quando = datetime.datetime.fromtimestamp(
            int.from_bytes(miolo[1:9], "big"), datetime.timezone.utc)
        return f"{len(valor)} chars · Fernet v0x80 · cifrado em {quando.isoformat()}"
    except Exception:  # noqa: BLE001
        return f"{len(valor)} chars · tem forma de ciphertext"


async def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--empresa", default="", help="company_id; vazio = todas")
    args = p.parse_args()

    import httpx

    from app.core.database import get_supabase_client
    from app.services.whatsapp.integration_secrets import decrypt_integration_secret

    base = (os.getenv("EVOLUTION_GO_BASE_URL") or "").rstrip("/")
    global_key = os.getenv("EVOLUTION_GO_GLOBAL_KEY") or ""
    publico = (os.getenv("PUBLIC_BACKEND_URL") or os.getenv("BACKEND_PUBLIC_URL") or "").rstrip("/")

    print("=" * 78)
    print("CONFIGURACAO (presenca e tamanho — nunca o valor)")
    print("=" * 78)
    for nome, v in (("EVOLUTION_GO_BASE_URL", base), ("PUBLIC_BACKEND_URL", publico)):
        print(f"  {nome:<26} {v or '(VAZIO — _validate_config levanta configuration_error)'}")
    for nome in ("EVOLUTION_GO_GLOBAL_KEY", "ENCRYPTION_KEY"):
        v = os.getenv(nome) or ""
        print(f"  {nome:<26} {'presente, ' + str(len(v)) + ' chars' if v else '(VAZIO)'}")

    # A chave global e usada em /instance/create e /instance/all. `_validate_config`
    # so confere que ela NAO ESTA VAZIA — nunca que ela FUNCIONA. Aqui funciona.
    print("\n" + "=" * 78)
    print("A CHAVE GLOBAL FUNCIONA?  GET /instance/all")
    print("=" * 78)
    instancias_go = {}
    async with httpx.AsyncClient(timeout=20.0, base_url=base) as cli:
        try:
            r = await cli.get("/server/ok")
            print(f"  /server/ok            HTTP {r.status_code}  {(r.text or '')[:60]}")
            r = await cli.get("/instance/all", headers={"apikey": global_key})
            print(f"  /instance/all         HTTP {r.status_code}")
            if r.status_code == 401:
                print("  >> A CHAVE GLOBAL ESTA ERRADA. Todo /instance/create devolve 401,")
                print("     e o pareamento vira 'configuration_error' na tela. E ISTO.")
            elif r.status_code < 400:
                for row in (r.json() or {}).get("data", []) or []:
                    instancias_go[str(row.get("name") or "")] = row
                print(f"  >> {len(instancias_go)} instancias no provedor:")
                for nome, row in sorted(instancias_go.items()):
                    tem_tel = "COM telefone (jid)" if row.get("jid") else "SEM telefone (casca vazia)"
                    print(f"       {nome:<28} {tem_tel}")
        except Exception as e:  # noqa: BLE001
            print(f"  provedor inalcancavel: {type(e).__name__}")

    db = get_supabase_client()
    q = (db.client.table("integrations").select("*")
         .eq("provider", "evolution-go").eq("is_active", True))
    if args.empresa:
        q = q.eq("company_id", args.empresa)
    linhas = q.order("company_id").execute().data or []

    print("\n" + "=" * 78)
    print(f"AS {len(linhas)} LINHAS ATIVAS, MEDIDAS COM O TOKEN **DECIFRADO**")
    print("=" * 78)
    veredito = []
    async with httpx.AsyncClient(timeout=20.0, base_url=base) as cli:
        for ln in linhas:
            inst = str(ln.get("instance_id") or "")
            print(f"\n  {inst}  ({ln.get('purpose')}, empresa {str(ln.get('company_id'))[:8]}…)")
            print(f"    banco diz ......... {ln.get('channel_status')} · last_seen {ln.get('last_seen_at')}")
            print(f"    segredo guardado .. {_anatomia(str(ln.get('token') or ''))}")

            if inst in instancias_go:
                print(f"    existe no provedor . SIM · "
                      f"{'com telefone' if instancias_go[inst].get('jid') else 'SEM telefone'}")
            elif instancias_go:
                print("    existe no provedor . NAO — linha ORFA (o banco lembra, o provedor nao)")

            try:
                tok = decrypt_integration_secret(ln.get("token"), contexto=inst) or ""
            except Exception as e:  # noqa: BLE001
                print(f"    >> SEGREDO PERDIDO: {type(e).__name__}")
                print("       A ENCRYPTION_KEY atual nao abre este valor. Ver o passo 3 do")
                print("       relatorio: recadastrar exige APAGAR a instancia no provedor.")
                veredito.append((inst, "segredo_perdido"))
                continue
            print(f"    token decifrado ... {len(tok)} chars "
                  f"({'hex/uuid — forma esperada' if len(tok) <= 64 else 'GRANDE DEMAIS — suspeito'})")

            for caminho in ("/instance/status", "/instance/qr"):
                try:
                    r = await cli.get(caminho, headers={"apikey": tok})
                    corpo = ""
                    if caminho == "/instance/status" and r.status_code < 400 and r.content:
                        d = (r.json() or {}).get("data") or {}
                        corpo = f"  LoggedIn={bool(d.get('LoggedIn'))} Connected={bool(d.get('Connected'))}"
                    elif r.status_code >= 400:
                        corpo = f"  {(r.text or '')[:70]}"
                    print(f"    GET {caminho:<18} HTTP {r.status_code}{corpo}")
                    if caminho == "/instance/status":
                        veredito.append((inst, "token_ok" if r.status_code < 400 else f"http_{r.status_code}"))
                    elif r.status_code >= 400:
                        print("       >> ATENCAO: _refresh() trata 4xx em /instance/qr como FATAL")
                        print("          (pairing_orchestrator.py:1008) e devolve configuration_error.")
                except Exception as e:  # noqa: BLE001
                    print(f"    GET {caminho:<18} falhou: {type(e).__name__}")

    print("\n" + "=" * 78)
    print("VEREDITO")
    print("=" * 78)
    for inst, v in veredito:
        traducao = {
            "token_ok": "o token do banco E o token do provedor. A cripto esta certa.",
            "http_401": "o provedor NAO conhece este token — instancia precisa ser recriada.",
            "http_404": "a instancia nao existe no provedor — sera criada no proximo pareamento.",
            "segredo_perdido": "a ENCRYPTION_KEY nao abre o segredo — recadastro obrigatorio.",
        }.get(v, v)
        print(f"  {inst:<28} {traducao}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
