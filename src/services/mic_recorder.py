# mic_recorder.py — Captura de áudio PCM via AudioRecord com ByteBuffer (Android 14)
import os
import time
import wave
from kivy.utils import platform

SAMPLE_RATE = 16000
FRAME_MS = 30
LIMIAR_RMS = 450.0
SILENCIO_FIM_S = 1.2
MIN_FALA_S = 0.5
MAX_UTTERANCE_S = 15.0
TIMEOUT_ESPERA_S = 8.0

HAS_ANDROID = platform == "android"


class MicRecorder:

    def __init__(self):
        self._recorder = None
        self._parar = __import__("threading").Event()

    def cancelar(self):
        self._parar.set()

    def _soltar(self):
        if self._recorder is not None:
            try:
                self._recorder.stop()
            except Exception:
                pass
            try:
                self._recorder.release()
            except Exception:
                pass
            self._recorder = None

    def _cache_dir(self):
        try:
            from src.services.fg_service import _contexto
            ctx = _contexto()
            if ctx is not None:
                return ctx.getCacheDir().getAbsolutePath()
        except Exception:
            pass
        import tempfile
        return tempfile.gettempdir()

    def _criar_recorder(self):
        from jnius import autoclass
        AudioRecord = autoclass("android.media.AudioRecord")
        AudioFormat = autoclass("android.media.AudioFormat")

        canal = AudioFormat.CHANNEL_IN_MONO
        encoding = AudioFormat.ENCODING_PCM_16BIT
        min_buf = AudioRecord.getMinBufferSize(SAMPLE_RATE, canal, encoding)
        if min_buf <= 0:
            min_buf = SAMPLE_RATE
        buf = max(min_buf * 2, int(SAMPLE_RATE * 2 * FRAME_MS / 1000) * 4)

        fontes = [
            autoclass(r"android.media.MediaRecorder$AudioSource").VOICE_RECOGNITION,
            autoclass(r"android.media.MediaRecorder$AudioSource").MIC,
            autoclass(r"android.media.MediaRecorder$AudioSource").CAMCORDER,
        ]
        for fonte in fontes:
            rec = AudioRecord(fonte, SAMPLE_RATE, canal, encoding, buf)
            if rec.getState() == AudioRecord.STATE_INITIALIZED:
                return rec
            try:
                rec.release()
            except Exception:
                pass
        return None

    def _rms_bytes(self, data):
        nshorts = len(data) // 2
        if nshorts <= 0:
            return 0.0
        passo = max(1, nshorts // 40)
        total = 0
        count = 0
        for i in range(0, nshorts, passo):
            idx = i * 2
            s = data[idx] | (data[idx + 1] << 8)
            if s >= 32768:
                s -= 65536
            total += s * s
            count += 1
        return (total / max(count, 1)) ** 0.5

    def capturar_utterance(self):
        if not HAS_ANDROID:
            return None
        from jnius import autoclass
        from src.utils.service_log import slog

        self._parar.clear()
        AudioRecord = autoclass("android.media.AudioRecord")
        ByteBuffer = autoclass("java.nio.ByteBuffer")

        rec = self._criar_recorder()
        if rec is None:
            slog("AudioRecord nao inicializou")
            return None
        self._recorder = rec

        frame = int(SAMPLE_RATE * 2 * FRAME_MS / 1000)
        jbuf = ByteBuffer.allocateDirect(frame)
        pasta = self._cache_dir()
        pcm_path = os.path.join(pasta, "spica_utt.pcm")
        wav_path = os.path.join(pasta, "spica_utt.wav")
        f_pcm = open(pcm_path, "wb")

        rec.startRecording()
        estado = rec.getRecordingState()
        slog("AudioRecord.startRecording state=%s (3=RECORDING)" % estado)
        if estado != AudioRecord.RECORDSTATE_RECORDING:
            try:
                f_pcm.close()
            except Exception:
                pass
            self._soltar()
            slog("AudioRecord nao entrou em RECORDING")
            return None

        falando = False
        pcm_bytes = 0
        inicio_fala = None
        silencio_s = 0.0
        espera_s = 0.0
        max_rms = 0.0
        frames_com_sinal = 0

        try:
            while not self._parar.is_set():
                jbuf.clear()
                n = rec.read(jbuf, frame)
                if n == AudioRecord.ERROR_INVALID_OPERATION or n == AudioRecord.ERROR_BAD_VALUE:
                    slog("AudioRecord.read erro=%s" % n)
                    break
                if n <= 0:
                    time.sleep(0.02)
                    continue

                jbuf.rewind()
                raw_bytes = bytearray(n)
                jbuf.get(raw_bytes)

                rms = self._rms_bytes(raw_bytes)
                if rms > max_rms:
                    max_rms = rms
                if rms >= LIMIAR_RMS:
                    frames_com_sinal += 1

                if not falando:
                    espera_s += FRAME_MS / 1000.0
                    if rms >= LIMIAR_RMS:
                        falando = True
                        inicio_fala = time.time()
                        silencio_s = 0.0
                        f_pcm.write(raw_bytes)
                        pcm_bytes += n
                    elif espera_s >= TIMEOUT_ESPERA_S:
                        slog("timeout sem fala (max_rms=%.0f)" % max_rms)
                        break
                else:
                    f_pcm.write(raw_bytes)
                    pcm_bytes += n
                    if rms < LIMIAR_RMS:
                        silencio_s += FRAME_MS / 1000.0
                    else:
                        silencio_s = 0.0
                    dur = time.time() - inicio_fala
                    if silencio_s >= SILENCIO_FIM_S and dur >= MIN_FALA_S:
                        slog("fim de fala dur=%.2fs rms_max=%.0f" % (dur, max_rms))
                        break
                    if dur >= MAX_UTTERANCE_S:
                        slog("corta utterance no maximo %ss" % MAX_UTTERANCE_S)
                        break
        finally:
            try:
                f_pcm.close()
            except Exception:
                pass
            self._soltar()

        slog("captura encerrada pcm_bytes=%s max_rms=%.0f frames_sinal=%s" % (
            pcm_bytes, max_rms, frames_com_sinal))
        if pcm_bytes < SAMPLE_RATE * 2 * MIN_FALA_S:
            return None
        if max_rms < LIMIAR_RMS:
            slog("RMS baixo demais — audio silenciado pelo sistema ou sem voz")
            return None
        self._pcm_para_wav(pcm_path, wav_path, pcm_bytes)
        return wav_path

    def _pcm_para_wav(self, pcm_path, wav_path, nbytes):
        with open(pcm_path, "rb") as f:
            pcm = f.read(nbytes)
        with wave.open(wav_path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SAMPLE_RATE)
            w.writeframes(pcm)
