# lembrete_tiktok.py — Lembrete das 23h para manter o "foguinho" do TikTok.
# Usa o acesso ao uso de apps (UsageStatsManager). Só avisa se você vinha abrindo o app nos últimos dias
# e não abriu hoje. Se a permissão não estiver ligada, avisa uma vez e fica quieta.
import datetime
import json
import os
import time

PACOTES_TIKTOK = ("com.zhiliaoapp.musically", "com.ss.android.ugc.trill")
HORA_LEMBRETE = 23
MIN_DIAS_FOGUINHO = 2


def _arquivo():
    base = os.environ.get("ANDROID_PRIVATE") or os.path.expanduser("~")
    return os.path.join(base, "tiktok_dias.json")


def _carregar():
    try:
        with open(_arquivo(), encoding="utf-8") as arq:
            return json.load(arq)
    except Exception:
        return {"dias": {}, "ultimo_check": "", "sem_permissao_avisado": ""}


def _salvar(dados):
    try:
        with open(_arquivo(), "w", encoding="utf-8") as arq:
            json.dump(dados, arq, ensure_ascii=False, indent=1)
    except Exception as e:
        print(f"[Spica/TikTok] salvar: {e}")


def _eh_tiktok(pacote):
    """Acha o TikTok pelo nome do pacote (funciona para a versão brasileira e a internacional)."""
    p = (pacote or "").lower()
    return p in PACOTES_TIKTOK or any(k in p for k in ("musically", "trill", "zhiliao", "ugc.trill"))


def abriu_hoje():
    """True = abriu, False = não abriu, None = sem permissão (ou não foi possível checar)."""
    try:
        from jnius import autoclass
        ctx = autoclass("org.kivy.android.PythonActivity").mActivity
        usm = ctx.getSystemService("usagestats")
        UsageStatsManager = autoclass("android.app.usage.UsageStatsManager")
        inicio_dia = datetime.datetime.combine(datetime.date.today(), datetime.time.min).timestamp() * 1000
        agora = time.time() * 1000
        stats = usm.queryUsageStats(UsageStatsManager.INTERVAL_DAILY, int(inicio_dia), int(agora))
        if stats is None or stats.size() == 0:
            return None                      # sem permissão: o Android devolve lista vazia
        for i in range(stats.size()):
            item = stats.get(i)
            if _eh_tiktok(str(item.getPackageName())) and item.getTotalTimeInForeground() > 0:
                return True
        return False
    except Exception as e:
        print(f"[Spica/TikTok] uso de apps: {e}")
        return None


def _notificar(texto):
    try:
        from plyer import notification
        notification.notify(title="Spica", message=texto, timeout=10)
    except Exception as e:
        print(f"[Spica/TikTok] notificação: {e}")


def checar_as_23h():
    """Chame a cada ~1 minuto a partir do serviço em segundo plano. Só age perto das 23h, uma vez por dia."""
    agora = datetime.datetime.now()
    if agora.hour != HORA_LEMBRETE or agora.minute > 5:
        return
    hoje = agora.date().isoformat()
    dados = _carregar()
    if dados.get("ultimo_check") == hoje:
        return
    dados["ultimo_check"] = hoje
    resultado = abriu_hoje()
    dias = dados.setdefault("dias", {})
    if resultado is None:
        if dados.get("sem_permissao_avisado") != hoje:
            dados["sem_permissao_avisado"] = hoje
            _notificar("Para eu lembrar do TikTok, ligue o acesso ao uso de apps da Spica nas configurações do Android.")
        _salvar(dados)
        return
    dias[hoje] = bool(resultado)
    _salvar(dados)
    if resultado:
        return
    # foguinho = dias seguidos abrindo, contando até ontem
    sequencia = 0
    dia = agora.date() - datetime.timedelta(days=1)
    while dias.get(dia.isoformat()):
        sequencia += 1
        dia -= datetime.timedelta(days=1)
    if sequencia >= MIN_DIAS_FOGUINHO:
        _notificar(f"Você ainda não abriu o TikTok hoje e está com {sequencia} dias de foguinho. Quer manter?")


def agendar_alarme_23h():
    """Agenda o lembrete pelo AlarmManager (funciona com o app e o serviço fechados).
    Pode ser chamada sempre: o Android substitui o agendamento anterior."""
    try:
        from jnius import autoclass
        ctx = autoclass("org.kivy.android.PythonActivity").mActivity
        autoclass("com.spica.spica.SpicaLembreteReceiver").agendar(ctx)
        return True
    except Exception as e:
        print(f"[Spica/TikTok] agendar alarme: {e}")
        return False
