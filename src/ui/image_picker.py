# image_picker.py — Seletor de imagem com câmera e galeria
import os
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.uix.modalview import ModalView
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.label import MDLabel
from kivymd.uix.card import MDCard
from kivymd.uix.filemanager import MDFileManager


class ImagePicker(ModalView):
    """Popup para escolher entre câmera, galeria ou arquivos."""

    def __init__(self, on_image=None, **kwargs):
        super().__init__(**kwargs)
        self.on_image_callback = on_image
        self.size_hint = (0.9, None)
        self.height = dp(260)
        self.background_color = [0, 0, 0, 0]

        self.file_manager = MDFileManager(
            exit_manager=lambda x: self.file_manager.close(),
            select_path=self._arquivo_selecionado,
            preview=True,
            ext=[".jpg", ".jpeg", ".png"]
        )

        self._construir_ui()

    def _construir_ui(self):
        card = MDCard(
            orientation="vertical",
            padding=dp(20),
            spacing=dp(12),
            radius=[dp(20)],
            elevation=10,
        )

        card.add_widget(MDLabel(
            text="Adicionar Imagem",
            font_style="H6",
            halign="center",
            size_hint_y=None,
            height=dp(40)
        ))

        # Botões de opção
        opcoes = MDBoxLayout(orientation="horizontal", size_hint_y=None,
                             height=dp(90), spacing=dp(12))

        for icon, label, acao in [
            ("camera",        "Câmera",   self._abrir_camera),
            ("image-multiple", "Galeria",  self._abrir_galeria),
            ("folder-open",   "Arquivos", self._abrir_arquivos),
        ]:
            btn_card = MDCard(
                orientation="vertical",
                size_hint=(1, 1),
                radius=[dp(12)],
                elevation=2,
                ripple_behavior=True,
            )
            from kivymd.uix.button import MDIconButton
            btn_card.add_widget(MDIconButton(
                icon=icon, icon_size=dp(30),
                pos_hint={"center_x": 0.5},
                disabled=True
            ))
            btn_card.add_widget(MDLabel(
                text=label, font_style="Caption",
                halign="center", size_hint_y=None, height=dp(22)
            ))
            btn_card.bind(on_release=lambda x, a=acao: a())
            opcoes.add_widget(btn_card)

        card.add_widget(opcoes)
        card.add_widget(MDFlatButton(
            text="Cancelar",
            size_hint_y=None, height=dp(40),
            pos_hint={"center_x": 0.5},
            on_release=lambda x: self.dismiss()
        ))

        self.add_widget(card)

    def _abrir_camera(self):
        self.dismiss()
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.CAMERA, Permission.WRITE_EXTERNAL_STORAGE])
            from kivy.uix.camera import Camera
            _CameraCapture(on_foto=self._arquivo_selecionado).open()
        except Exception as e:
            # Fallback para galeria se câmera não disponível
            self._abrir_galeria()

    def _abrir_galeria(self):
        self.dismiss()
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.READ_EXTERNAL_STORAGE])
        except Exception:
            pass
        pasta = "/sdcard/DCIM" if os.path.exists("/sdcard/DCIM") else (
            "/sdcard" if os.path.exists("/sdcard") else os.path.expanduser("~")
        )
        Clock.schedule_once(lambda dt: self.file_manager.show(pasta), 0.3)

    def _abrir_arquivos(self):
        self.dismiss()
        pasta = "/sdcard" if os.path.exists("/sdcard") else os.path.expanduser("~")
        Clock.schedule_once(lambda dt: self.file_manager.show(pasta), 0.3)

    def _arquivo_selecionado(self, caminho):
        self.file_manager.close()
        ext = os.path.splitext(caminho)[1].lower()
        if ext in ['.png', '.jpg', '.jpeg'] and self.on_image_callback:
            self.on_image_callback(caminho)
        else:
            if self.on_image_callback:
                self.on_image_callback(None)


class _CameraCapture(ModalView):
    """Tela de captura com câmera."""

    def __init__(self, on_foto=None, **kwargs):
        super().__init__(**kwargs)
        self.on_foto = on_foto
        self.size_hint = (1, 1)
        self._caminho_foto = None

        layout = MDBoxLayout(orientation="vertical")

        try:
            from kivy.uix.camera import Camera
            self.camera = Camera(play=True, resolution=(640, 480))
            layout.add_widget(self.camera)
        except Exception:
            layout.add_widget(MDLabel(
                text="Câmera não disponível",
                halign="center", font_style="H6"
            ))
            self.camera = None

        botoes = MDBoxLayout(size_hint_y=None, height=dp(60), spacing=dp(10), padding=dp(8))
        botoes.add_widget(MDFlatButton(text="Cancelar", on_release=lambda x: self.dismiss()))
        botoes.add_widget(MDRaisedButton(text="Tirar Foto", on_release=self._capturar))
        layout.add_widget(botoes)
        self.add_widget(layout)

    def _capturar(self, *args):
        if not self.camera:
            self.dismiss()
            return
        try:
            import time
            pasta = "/sdcard/Pictures/Spica" if os.path.exists("/sdcard") else "/tmp"
            os.makedirs(pasta, exist_ok=True)
            caminho = os.path.join(pasta, f"foto_{int(time.time())}.png")
            self.camera.export_to_png(caminho)
            self.dismiss()
            if self.on_foto and os.path.exists(caminho):
                Clock.schedule_once(lambda dt: self.on_foto(caminho), 0.3)
        except Exception as e:
            self.dismiss()
