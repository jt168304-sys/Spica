# mic_recorder.py — Captura PCM no PROCESSO do app (AudioRecord).
#
# Por que isso existe: no Android 12+ (e de forma dura no 14 / Motorola), o
# SpeechRecognizer do Google grava em OUTRO processo. Esse processo nao herda
# o foregroundServiceType=microphone da Spica, entao o sistema entrega audio
# silenciado — o LED do mic acende, mas nao chega voz. AudioRecord roda no
# nosso UID e herda o FGS de microfone.
import os
import time
import wave
import threading

try:
    from jnius import autoclass
    HAS_ANDROID = True
except Exception:
    HAS_ANDROID = False

SAMPLE_RATE = 16000
LIMIAR_RMS = 280
MIN_FALA_S = 0.35
SILENCIO_FIM_S = 1.15
MAX_UTTERANCE_S = 8.0
TIMEOUT_ESPERA_S = 10.0
FRAME_MS = 100


class MicRecorder:
    def __init__(self):
        self._parar = threading.Event()
        self._recorder = None

    def cancelar(self):
        self._parar.set()
        self._soltar()

    def _soltar(self):
        rec = self._recorder
        self._recorder = None
        if rec is None:
            return
        try:
            rec.stop()
        except Exception:
            pass
        try:
            rec.release()
        except Exception:
            pass

    def _cache_dir(self):
        from jnius import autoclass
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        ctx = PythonActivity.mActivity
        return ctx.getCacheDir().getAbsolutePath()

    def _criar_recorder(self):
        from jnius import autoclass
        AudioRecord = autoclass("android.media.AudioRecord")
        AudioFormat = autoclass("android.media.AudioFormat")
        MediaRecorder = autoclass("android.media.MediaRecorder")

        canal = AudioFormat.CHANNEL_IN_MONO
        encoding = AudioFormat.ENCODING_PCM_16BIT
        min_buf = AudioRecord.getMinBufferSize(SAMPLE_RATE, canal, encoding)
        if min_buf <= 0:
            min_buf = SAMPLE_RATE
        buf = max(min_buf * 2, int(SAMPLE_RATE * 2 * FRAME_MS / 1000) * 4)

        fontes = [
            MediaRecorder.AudioSource.VOICE_RECOGNITION,
            MediaRecorder.AudioSource.MIC,
            MediaRecorder.AudioSource.CAMCORDER,
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

    def _rms(self, Array, jbuf, nbytes):
        nshorts = nbytes // 2
        if nshorts <= 0:
            return 0.0
        passo = max(1, nshorts // 40)
        total = 0
        count = 0
        i = 0
        while i < nshorts:
            b0 = Array.getByte(jbuf, i * 2) & 0xFF
            b1 = Array.getByte(jbuf, i * 2 + 1)
            s = b0 | ((b1 & 0xFF) << 8)
            if s >= 32768:
                s -= 65536
            total += s * s
            count += 1
            i += passo
        return (total / max(count, 1)) ** 0.5

    def capturar_utterance(self):
        """Bloqueia ate gravar uma fala (ou timeout). Devolve caminho WAV ou None."""
        if not HAS_ANDROID:
            return None
        from jnius import autoclass
        from src.utils.service_log import slog

        self._parar.clear()
        Array = autoclass("java.lang.reflect.Array")
        Byte = autoclass("java.lang.Byte")
        FileOutputStream = autoclass("java.io.FileOutputStream")
        AudioRecord = autoclass("android.media.AudioRecord")

        rec = self._criar_recorder()
        if rec is None:
            slog("AudioRecord nao inicializou")
            return None
        self._recorder = rec

        frame = int(SAMPLE_RATE * 2 * FRAME_MS / 1000)
        jbuf = Array.newInstance(Byte.TYPE, frame)
        pasta = self._cache_dir()
        pcm_path = os.path.join(pasta, "spica_utt.pcm")
        wav_path = os.path.join(pasta, "spica_utt.wav")
        fos = FileOutputStream(pcm_path)

        rec.startRecording()
        estado = rec.getRecordingState()
        slog("AudioRecord.startRecording state=%s (3=RECORDING)" % estado)
        if estado != AudioRecord.RECORDSTATE_RECORDING:
            try:
                fos.close()
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
                n = rec.read(jbuf, 0, frame)
                if n == AudioRecord.ERROR_INVALID_OPERATION or n == AudioRecord.ERROR_BAD_VALUE:
                    slog("AudioRecord.read erro=%s" % n)
                    break
                if n <= 0:
                    time.sleep(0.02)
                    continue
                rms = self._rms(Array, jbuf, n)
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
                        fos.write(jbuf, 0, n)
                        pcm_bytes += n
                    elif espera_s >= TIMEOUT_ESPERA_S:
                        slog("timeout sem fala (max_rms=%.0f)" % max_rms)
                        break
                else:
                    fos.write(jbuf, 0, n)
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
                fos.close()
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
