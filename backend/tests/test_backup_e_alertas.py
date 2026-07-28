"""O backup do storage e o alerta que chega em quem pode agir.

Por que o backup existe
-----------------------
O Supabase faz backup do Postgres pelo plano. O **MinIO não tinha rotina
nenhuma** — e é ele que guarda a única cópia de cada documento que a corretora
enviou. O Postgres guarda o *ponteiro*; o arquivo mora só ali.

Antes de 28/07/2026, o RPO real do storage era **"desde sempre"**.

As duas coisas que este teste protege
-------------------------------------
**1. O backup não pode apagar.** É a decisão mais importante do desenho. Um
"espelho" que replica exclusões é inútil justamente no caso que mais importa:
alguém apaga por engano, o espelho apaga junto, e o backup vira uma cópia fiel
do desastre.

**2. O alerta tem de chegar em quem pode agir.** Dois destinos diferentes, e
trocá-los estraga os dois:

    corretora  →  grupo do suporte humano. "Seu WhatsApp caiu" é problema dela.
    plataforma →  plantão. "O backup falhou" é problema seu — mandar isso para
                  o corretor troca confiança por ruído.
"""

from __future__ import annotations

import importlib.util
import os
import re
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FALHAS: list[str] = []

for _n, _p in (("app", ("app",)), ("app.services", ("app", "services")),
               ("app.services.backup", ("app", "services", "backup"))):
    if _n not in sys.modules:
        m = types.ModuleType(_n)
        m.__path__ = [os.path.join(RAIZ, *_p)]
        m.__package__ = _n
        sys.modules[_n] = m


def carregar(nome: str):
    caminho = os.path.join(RAIZ, *nome.split(".")) + ".py"
    spec = importlib.util.spec_from_file_location(nome, caminho)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nome] = mod
    spec.loader.exec_module(mod)
    return mod


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def _ler(*p: str) -> str:
    with open(os.path.join(RAIZ, *p), encoding="utf-8") as fh:
        return fh.read()


def _sem_comentario(fonte: str) -> str:
    """Só o CÓDIGO — sem `#` e sem docstring.

    Tirar apenas o `#` não bastou. As docstrings deste projeto explicam POR QUE
    uma coisa foi removida, e para isso precisam citar o nome dela — então o
    teste passou a acusar a explicação como se fosse o defeito.

    O que se cobra é o código. A explicação tem de continuar existindo, senão a
    próxima pessoa reintroduz o problema sem saber que ele já foi um.
    """
    aspas3 = chr(34) * 3
    sem_doc = re.sub(aspas3 + r"(?:.|\n)*?" + aspas3, "", fonte)
    return "\n".join(l for l in sem_doc.split("\n")
                     if not l.lstrip().startswith("#"))


B = carregar("app.services.backup.minio_backup")


def teste_o_backup_nunca_apaga():
    print("\n[1] O backup NUNCA apaga nada no destino")
    fonte = _sem_comentario(_ler("app", "services", "backup", "minio_backup.py"))
    for perigo in ("remove_object", "remove_objects", "delete_object",
                   "--remove", "remove_bucket"):
        checar(perigo not in fonte, f"não existe '{perigo}' no código",
               "espelho que replica exclusão é cópia fiel do desastre")
    # E o `conferir` precisa TRATAR o excedente como normal, não como erro:
    # objeto apagado na origem CONTINUA na cópia — é o ponto do backup.
    checar("preservados_alem_da_origem" in fonte,
           "objeto que sobrou no destino é reportado como preservado, não como divergência")


def teste_nasce_desligado_e_sem_configuracao_nao_roda():
    print("\n[2] Sem configuração completa, não roda — e diz o que falta")
    os.environ.pop(B.FLAG, None)
    checar(not B.ligado(), "sem a variável, o backup está desligado")
    r = B.executar()
    checar(r.get("ok") and "pulado" in r, "desligado devolve 'pulado', não erro",
           str(r))

    os.environ[B.FLAG] = "1"
    for k in ("MINIO_BACKUP_S3_ENDPOINT", "MINIO_BACKUP_S3_BUCKET",
              "MINIO_BACKUP_S3_ACCESS_KEY_ID", "MINIO_BACKUP_S3_SECRET_ACCESS_KEY"):
        os.environ.pop(k, None)
    try:
        r2 = B.executar()
        checar(r2.get("ok") is False, "ligado sem configuração não finge que copiou")
        checar("configuração" in str(r2.get("erro", "")).lower(),
               "e diz que a configuração está incompleta", str(r2))
    finally:
        os.environ.pop(B.FLAG, None)


def teste_o_log_nunca_carrega_segredo():
    print("\n[3] Log de backup não carrega chave nem conteúdo")
    # Log de backup é lido por muita gente e fica guardado por muito tempo.
    fonte = _ler("app", "services", "backup", "minio_backup.py")
    sem = _sem_comentario(fonte)
    # Nenhum logger recebendo a config ou o segredo.
    for perigo in ('logger.info("[Backup] %s", cfg',
                   'cfg["segredo"]', 'cfg["chave"]'):
        ocorrencias = [l for l in sem.split("\n")
                       if perigo in l and "logger" in l]
        checar(not ocorrencias, f"nenhum log com {perigo}", str(ocorrencias[:1]))
    # E o log de falha usa o NOME do objeto, nunca o conteúdo.
    checar("dado" not in re.findall(r"logger\.error\([^)]*\)", sem).__str__(),
           "log de falha não inclui o conteúdo do arquivo")


def teste_duas_execucoes_nao_se_atropelam():
    print("\n[4] Duas execuções ao mesmo tempo não dobram o egresso")
    fonte = _sem_comentario(_ler("app", "services", "backup", "minio_backup.py"))
    checar("nx=True" in fonte, "usa lock exclusivo no Redis")
    checar("LOCK_TTL_S" in fonte, "e o lock expira sozinho",
           "lock sem prazo trava o backup para sempre se o processo morrer")


def teste_falha_de_backup_alerta():
    print("\n[5] Backup que falha em silêncio é backup que não existe")
    fonte = _sem_comentario(_ler("app", "services", "backup", "minio_backup.py"))
    checar("_alertar" in fonte, "existe caminho de alerta")
    checar("if not resultado.get(\"ok\")" in fonte,
           "e ele dispara quando o resultado não é ok")


def teste_retentativa_com_espera_crescente():
    print("\n[6] Soluço de rede não vira uma hora sem cópia")
    tentativas = {"n": 0}

    def _instavel():
        tentativas["n"] += 1
        if tentativas["n"] < 3:
            raise RuntimeError("rede")
        return "ok"

    import time as _t
    original = _t.sleep
    _t.sleep = lambda _s: None  # não esperar de verdade no teste
    try:
        r = B._com_retentativa(_instavel, oque="teste")
        checar(r == "ok" and tentativas["n"] == 3,
               "insiste até conseguir", f"tentativas={tentativas['n']}")

        def _sempre_falha():
            raise RuntimeError("morto")
        try:
            B._com_retentativa(_sempre_falha, tentativas=2, oque="teste")
            checar(False, "desiste depois do limite")
        except RuntimeError:
            checar(True, "desiste depois do limite e propaga o erro")
    finally:
        _t.sleep = original


def teste_alerta_da_corretora_vai_para_o_suporte_humano():
    print("\n[7] O alerta da corretora chega no grupo do suporte humano")
    # Decisão do Founder: "quando conectar o suporte humano, o alerta já está
    # embutido junto. Não precisa nem falar nada."
    fonte = _sem_comentario(_ler("app", "services", "whatsapp", "alerts.py"))
    i = fonte.find("def _alert_destination")
    corpo = fonte[i: i + 2600] if i != -1 else ""
    checar("_support_contact" in corpo,
           "o alerta procura o destino do suporte humano")
    checar("use_support_destination" not in corpo,
           "e NÃO exige mais uma bandeira para isso",
           "bandeira que alguém precisa lembrar de ligar é alerta que não existe")
    # Ordem: destino explícito primeiro, suporte depois, fallback por último.
    pos_expl = corpo.find('target.get("number")')
    pos_sup = corpo.find("_support_contact")
    pos_fb = corpo.find("PLATFORM_ALERT_FALLBACK_NUMBER")
    checar(-1 < pos_expl < pos_sup < pos_fb,
           "a ordem é: explícito → suporte humano → plantão da plataforma",
           f"{pos_expl} {pos_sup} {pos_fb}")


def teste_alerta_de_plataforma_nao_vai_para_a_corretora():
    print("\n[8] 'O backup falhou' não é problema do corretor")
    fonte = _sem_comentario(_ler("app", "services", "whatsapp", "alerts.py"))
    i = fonte.find("async def alerta_de_plataforma")
    corpo = fonte[i: i + 1200] if i != -1 else ""
    checar(bool(corpo), "existe um caminho separado para alerta de plataforma")
    checar("PLATFORM_ALERT_FALLBACK_NUMBER" in corpo,
           "que vai para o plantão da plataforma")
    checar("_support_contact" not in corpo,
           "e NUNCA para o grupo da corretora",
           "mandar problema de infraestrutura para o corretor troca confiança "
           "por ruído")


def teste_backup_esta_agendado():
    print("\n[9] O backup roda sozinho, de hora em hora")
    fonte = _sem_comentario(_ler("app", "tasks", "buffer_processor.py"))
    checar("minio_backup" in fonte, "está no scheduler")
    checar('MINIO_BACKUP_INTERVAL_MINUTES", 60' in fonte,
           "com intervalo padrão de 60 minutos")
    i = fonte.find('id="minio_backup"')
    janela = fonte[max(0, i - 400): i + 200] if i != -1 else ""
    checar("max_instances=1" in janela,
           "e o scheduler não empilha execuções",
           "sem isso, um backup lento se sobrepõe ao próximo")


def main() -> int:
    print("=" * 70)
    print("BACKUP QUE NÃO APAGA, E ALERTA QUE CHEGA EM QUEM PODE AGIR")
    print("=" * 70)
    for teste in (teste_o_backup_nunca_apaga,
                  teste_nasce_desligado_e_sem_configuracao_nao_roda,
                  teste_o_log_nunca_carrega_segredo,
                  teste_duas_execucoes_nao_se_atropelam,
                  teste_falha_de_backup_alerta,
                  teste_retentativa_com_espera_crescente,
                  teste_alerta_da_corretora_vai_para_o_suporte_humano,
                  teste_alerta_de_plataforma_nao_vai_para_a_corretora,
                  teste_backup_esta_agendado):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {teste.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 70)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("O QUE FOI GUARDADO NÃO SE PERDE, E QUEM PRECISA SABER É AVISADO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
