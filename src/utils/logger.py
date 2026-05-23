# logger.py — Log em arquivo e terminal
import logging, os


class WindLogger:
    _ok = False

    def __init__(self, nome="WindIA"):
        if not WindLogger._ok:
            os.makedirs("data", exist_ok=True)
            logging.basicConfig(
                level=logging.INFO,
                format="[%(asctime)s] %(levelname)s: %(message)s",
                datefmt="%H:%M:%S",
                handlers=[logging.FileHandler("data/wind.log", encoding="utf-8"),
                          logging.StreamHandler()]
            )
            WindLogger._ok = True
        self._log = logging.getLogger(nome)

    def info(self, m):    self._log.info(m)
    def warning(self, m): self._log.warning(m)
    def error(self, m):   self._log.error(m)
