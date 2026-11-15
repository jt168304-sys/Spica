# acoes.py — ações no celular da Spica. Só devolve ok:true quando o Android recebeu o pedido COMPLETO.
# Números e textos vão num Bundle (putInt/putString/putLong): o putExtra do pyjnius escolhe o tipo errado
# (long em vez de int) e o relógio ignorava a hora e a duração.
import datetime
import os
import re
import time


def _jnius():
    try:
        import jnius
        return jnius
    except Exception:
        raise RuntimeError("isso só funciona no celular")


def _ctx():
    return _jnius().autoclass("org.kivy.android.PythonActivity").mActivity


def _montar(acao, ints=None, strings=None, bools=None, longs=None):
    j = _jnius()
    intent = j.autoclass("android.content.Intent")(acao)
    pacote = j.autoclass("android.os.Bundle")()
    for chave, valor in (ints or {}).items():
        pacote.putInt(chave, int(valor))
    for chave, valor in (strings or {}).items():
        pacote.putString(chave, str(valor))
    for chave, valor in (bools or {}).items():
        pacote.putBoolean(chave, bool(valor))
    for chave, valor in (longs or {}).items():
        pacote.putLong(chave, int(valor))
    intent.putExtras(pacote)
    return intent


def _iniciar(intent):
    intent.addFlags(0x10000000)  # FLAG_ACTIVITY_NEW_TASK
    _ctx().startActivity(intent)


def _mostrar_lista(acao):
    """Abre a lista de alarmes/timers para a pessoa conferir. Falhar aqui não é erro da ação."""
    try:
        time.sleep(0.7)
        _iniciar(_montar(acao))
    except Exception as e:
        print(f"[Spica/Acao] lista {acao}: {e}")


def _interpretar_inicio(texto):
    """Aceita '2026-11-14 09:00', '14/11/2026 09:00', 'amanhã às 9h', 'hoje 19:30', '9h da manhã'."""
    bruto = str(texto or "").strip()
    for formato in ("%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M"):
        try:
            return datetime.datetime.strptime(bruto, formato)
        except ValueError:
            pass
    t = bruto.lower()
    for a, b in (("ã", "a"), ("á", "a"), ("é", "e"), ("ê", "e"), ("í", "i"), ("ó", "o")):
        t = t.replace(a, b)
    m = re.search(r"(\d{1,2})\s*(?:[:h]\s*(\d{2})?)", t)
    if not m:
        return None
    h, mi = int(m.group(1)), int(m.group(2) or 0)
    if ("tarde" in t or "noite" in t) and h < 12:
        h += 12
    if h > 23 or mi > 59:
        return None
    agora = datetime.datetime.now()
    dia = agora.date() + datetime.timedelta(days=1) if "amanha" in t else agora.date()
    dt = datetime.datetime.combine(dia, datetime.time(h, mi))
    if "amanha" not in t and "hoje" not in t and dt < agora:
        dt += datetime.timedelta(days=1)
    return dt


def criar_lembrete(hora, mensagem=""):
    m = re.match(r"^\s*(\d{1,2})\s*[:h]\s*(\d{2})?\s*$", str(hora or ""))
    if not m:
        return {"ok": False, "erro": "a hora precisa ser como 15:30 ou 15h"}
    h, mi = int(m.group(1)), int(m.group(2) or 0)
    if not (0 <= h <= 23 and 0 <= mi <= 59):
        return {"ok": False, "erro": "hora inválida"}
    intent = _montar("android.intent.action.SET_ALARM",
                     ints={"android.intent.extra.alarm.HOUR": h, "android.intent.extra.alarm.MINUTES": mi},
                     strings={"android.intent.extra.alarm.MESSAGE": (mensagem or "Lembrete da Spica")[:120]},
                     bools={"android.intent.extra.alarm.SKIP_UI": True})
    _iniciar(intent)
    _mostrar_lista("android.intent.action.SHOW_ALARMS")
    return {"ok": True, "resultado": f"alarme enviado ao relógio para {h:02d}:{mi:02d}; a lista de alarmes foi aberta para você conferir"}


def criar_timer(minutos, mensagem=""):
    try:
        minutos_f = float(minutos)
    except (TypeError, ValueError):
        return {"ok": False, "erro": "informe a duração em minutos"}
    seg = int(minutos_f * 60)
    if not 1 <= seg <= 24 * 3600:
        return {"ok": False, "erro": "o timer precisa ficar entre 1 minuto e 24 horas"}
    intent = _montar("android.intent.action.SET_TIMER",
                     ints={"android.intent.extra.alarm.LENGTH": seg},
                     strings={"android.intent.extra.alarm.MESSAGE": (mensagem or "Timer da Spica")[:120]},
                     bools={"android.intent.extra.alarm.SKIP_UI": True})
    _iniciar(intent)
    _mostrar_lista("android.intent.action.SHOW_TIMERS")
    return {"ok": True, "resultado": f"timer de {seg // 60} min {seg % 60} s enviado ao relógio; a tela de timers foi aberta para você conferir"}


def criar_evento(titulo, inicio, minutos=60, descricao=""):
    dt = _interpretar_inicio(inicio)
    if dt is None:
        return {"ok": False, "erro": "não entendi o horário; diga o dia e a hora, por exemplo 'amanhã às 9h'"}
    j = _jnius()
    ini = int(dt.timestamp() * 1000)
    fim = ini + int(float(minutos or 60)) * 60000
    intent = _montar("android.intent.action.INSERT",
                     strings={"title": (titulo or "Evento")[:150], "description": (descricao or "")[:800]},
                     longs={"beginTime": ini, "endTime": fim})
    intent.setData(j.autoclass("android.provider.CalendarContract$Events").CONTENT_URI)
    _iniciar(intent)
    return {"ok": True, "resultado": f"o calendário foi aberto com '{titulo}' em {dt:%d/%m às %H:%M}; falta você tocar em salvar"}


def criar_texto(nome, conteudo):
    from src.services import arquivos
    caminho = arquivos.escrever(nome, conteudo)
    return {"ok": True, "resultado": f"anotação salva como {os.path.basename(caminho)} na pasta textos"}


def preparar_mensagem(texto):
    if not (texto or "").strip():
        return {"ok": False, "erro": "o texto está vazio"}
    j = _jnius()
    Intent = j.autoclass("android.content.Intent")
    intent = _montar("android.intent.action.SEND", strings={"android.intent.extra.TEXT": texto[:2000]})
    intent.setType("text/plain")
    titulo = j.cast("java.lang.CharSequence", j.autoclass("java.lang.String")("Enviar com"))
    _iniciar(Intent.createChooser(intent, titulo))
    return {"ok": True, "resultado": "as opções de envio foram abertas com o texto; você escolhe o app e envia"}
