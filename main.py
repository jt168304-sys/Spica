# main.py — Porta de Entrada e Redirecionador de Logs (Spica v16)
import os, sys, traceback, socket

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Função para envio de logs manuais
def salvar_log(msg):
    print(f"[SPICA_LOG] {msg}")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.5)
        sock.sendto(f"{msg}\n".encode("utf-8"), ("127.0.0.1", 9999))
        sock.close()
    except Exception:
        pass

# REDIRECIONADOR MÁGICO: Tudo que o Kivy printar internamente vai para o Termux
class TermuxStream:
    def __init__(self, stream_original, prefixo):
        self.stream_original = stream_original
        self.prefixo = prefixo
    def write(self, data):
        self.stream_original.write(data)
        if data.strip(): # Evita enviar linhas em branco vazias
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.sendto(f"{self.prefixo} {data.strip()}\n".encode("utf-8"), ("127.0.0.1", 9999))
                sock.close()
            except Exception:
                pass
    def flush(self):
        self.stream_original.flush()

# Ativa o redirecionamento total de logs nativos do Python/Kivy
sys.stdout = TermuxStream(sys.stdout, "⚪ [STDOUT]")
sys.stderr = TermuxStream(sys.stderr, "🔴 [STDERR]")

# Interceptador global para capturar falhas antes de morrer
def handler(tp, val, tb):
    erro = "".join(traceback.format_exception(tp, val, tb))
    salvar_log(f"💥 CRASH GLOBAL DETECTADO:\n{erro}")
    # Força a limpeza do motor de voz se o app cair
    _limpeza_emergência()
    sys.__excepthook__(tp, val, tb)

sys.excepthook = handler

def _limpeza_emergência():
    """Tenta desligar os hardwares nativos do Android em caso de crash ou fechamento brusco."""
    try:
        from src.services.voice_service import VoiceService
        if VoiceService._instancia and VoiceService._instancia.recognizer:
            VoiceService._instancia.recognizer.destroy()
            salvar_log("🔹 [Limpeza] Hardware do VoiceService liberado.")
    except Exception:
        pass

salvar_log("🚀 === Spica iniciando no dispositivo ===")

try:
    from kivy.config import Config
    Config.set("graphics", "resizable", "1")
    Config.set("graphics", "width", "400")
    Config.set("graphics", "height", "700")
    Config.set("kivy", "log_level", "warning")
    Config.set("input", "mouse", "mouse,multitouch_on_demand")
    salvar_log("🔹 Config Kivy OK")

    from kivy.core.window import Window
    Window.softinput_mode = "below_target"
    salvar_log("🔹 Window OK")

    salvar_log("🔹 Tentando importar WindApp...")
    from src.core.app_manager import WindApp
    salvar_log("🔹 WindApp importado com SUCESSO!")

    if __name__ == "__main__":
        salvar_log("▶️ Executando WindApp().run()...")
        try:
            app_instance = WindApp()
            salvar_log("🔹 Instância do WindApp criada. Dando run()...")
            app_instance.run()
            salvar_log("⏹️ run() encerrado normalmente")
        except BaseException as e_kivy:
            salvar_log(f"💥 ERRO SEGURO CAPTURADO NO RUN (BaseException):\n{traceback.format_exc()}")
            raise
        finally:
            # Executado sempre no encerramento normal do ciclo de vida do Kivy
            _limpeza_emergência()
            salvar_log("👋 === Spica encerrada e recursos limpos ===")
            
except BaseException as e:
    salvar_log(f"❌ ERRO CRÍTICO NA INICIALIZAÇÃO (BaseException):\n{traceback.format_exc()}")
    _limpeza_emergência()
    raise
