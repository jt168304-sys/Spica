# acoes.py — ações no celular da Spica. Só devolve ok:true quando o Android aceitou o pedido.
# Se nenhum app puder atender (ou o Android recusar), devolve erro com o motivo.
import datetime
import os
import re


def _autoclass():
    try:
        from jnius import autoclass
        return autoclass
    except Exception:
        return None


def _intent(acao):
    AC = _autoclass()
    if AC is None:
        raise RuntimeError("isso só funciona no celular (fora dele não há relógio nem calendário)")
    return AC("android.content.Intent")(acao)


def _iniciar(intent):
    """Abre o app. Se o Android não tiver app para isso, a exceção sobe com o motivo real."""
    AC = _autoclass()
    if AC is None:
        raise RuntimeError("isso só funciona no celular")
    ctx = AC("org.kivy.android.PythonActivity").mActivity
    intent.addFlags(0x10000000)  # FLAG_ACTIVITY_NEW_TASK
    ctx.startActivity(intent)     # síncrono: ActivityNotFoundException aparece aqui, não some


def criar_lembrete(hora, mensagem=""):
    m = re.match(r"^\s*(\d{1,2})\s*[:h]\s*(\d{2})?\s*$", str(hora or ""))
    if not m:
        return {"ok": False, "erro": "a hora precisa ser como 15:30 ou 15h"}
    h, mi = int(m.group(1)), int(m.group(2) or 0)
    if not (0 <= h <= 23 and 0 <= mi <= 59):
        return {"ok": False, "erro": "hora inválida"}
    i = _intent("android.intent.action.SET_ALARM")
    i.putExtra("android.intent.extra.alarm.HOUR", h)
    i.putExtra("android.intent.extra.alarm.MINUTES", mi)
    i.putExtra("android.intent.extra.alarm.MESSAGE", (mensagem or "Lembrete da Spica")[:120])
    i.putExtra("android.intent.extra.alarm.SKIP_UI", False)   # mostra o relógio: você vê que foi criado
    _iniciar(i)
    return {"ok": True, "resultado": f"o app de relógio foi aberto com o alarme das {h:02d}:{mi:02d}"}


def criar_timer(minutos, mensagem=""):
    try:
        minutos_f = float(minutos)
    except (TypeError, ValueError):
        return {"ok": False, "erro": "informe a duração em minutos"}
    seg = int(minutos_f * 60)
    if not 1 <= seg <= 24 * 3600:
        return {"ok": False, "erro": "o timer precisa ficar entre 1 minuto e 24 horas"}
    i = _intent("android.intent.action.SET_TIMER")
    i.putExtra("android.intent.extra.alarm.LENGTH", seg)
    i.putExtra("android.intent.extra.alarm.MESSAGE", (mensagem or "Timer da Spica")[:120])
    i.putExtra("android.intent.extra.alarm.SKIP_UI", False)
    _iniciar(i)
    return {"ok": True, "resultado": f"o app de relógio foi aberto com o timer de {int(minutos_f)} minuto(s)"}


def criar_evento(titulo, inicio, minutos=60, descricao=""):
    dt = None
    for formato in ("%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M"):
        try:
            dt = datetime.datetime.strptime(str(inicio or "").strip(), formato)
            break
        except ValueError:
            pass
    if dt is None:
        return {"ok": False, "erro": "o início precisa ser como 2026-10-20 19:00"}
    AC = _autoclass()
    if AC is None:
        raise RuntimeError("isso só funciona no celular")
    ini = int(dt.timestamp() * 1000)
    fim = ini + int(float(minutos or 60)) * 60000
    eventos = AC("android.provider.CalendarContract$Events")
    i = _intent("android.intent.action.INSERT")
    i.setData(eventos.CONTENT_URI)
    i.putExtra("title", (titulo or "Evento")[:150])
    i.putExtra("description", (descricao or "")[:800])
    i.putExtra("beginTime", AC("java.lang.Long")(ini))
    i.putExtra("endTime", AC("java.lang.Long")(fim))
    _iniciar(i)
    return {"ok": True, "resultado": f"o calendário foi aberto com '{titulo}' em {dt:%d/%m %H:%M}; falta você salvar"}


def criar_texto(nome, conteudo):
    from src.services import arquivos
    caminho = arquivos.escrever(nome, conteudo)
    return {"ok": True, "resultado": f"anotação salva como {os.path.basename(caminho)} na pasta textos"}


def preparar_mensagem(texto):
    if not (texto or "").strip():
        return {"ok": False, "erro": "o texto está vazio"}
    AC = _autoclass()
    if AC is None:
        raise RuntimeError("isso só funciona no celular")
    i = _intent("android.intent.action.SEND")
    i.setType("text/plain")
    i.putExtra("android.intent.extra.TEXT", texto[:2000])
    _iniciar(AC("android.content.Intent").createChooser(i, "Enviar com"))
    return {"ok": True, "resultado": "as opções de envio foram abertas com o texto; você escolhe o app e envia"}
