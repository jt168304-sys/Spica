# ajuda_screen.py — Tela "Recursos da Spica": o que funciona hoje e o que vem depois.
from kivy.effects.scroll import ScrollEffect
from kivy.metrics import dp
from kivy.uix.scrollview import ScrollView
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen
from src.ui import tema as T
from src.ui.barra import criar_barra

FUNCIONA_HOJE = [
    ("Conversa", "Escreva ou fale com a Spica. Ela responde por texto e por voz, e a bolha flutuante aparece sobre outros apps."),
    ("Escuta em segundo plano", "Com a bolha ativa, ela continua ouvindo com o app minimizado. Para ela responder, chame pelo nome: \"Spica, ...\". Logo depois de uma pergunta dela, dá para responder sem o nome."),
    ("Pesquisa na web", "Pergunte coisas atuais, como \"quanto está o dólar hoje?\" ou \"quando sai o próximo episódio de ...?\". Ela pesquisa e cita a fonte."),
    ("Clima", "\"Como está o tempo em Recife?\" Mostra agora e a previsão de 3 dias."),
    ("Calculadora", "\"Quanto é 15% de 2300?\" ou \"1250 vezes 1,15 dividido por 12\"."),
    ("Imagens", "\"Cria uma imagem de ...\". Pode pedir formatos como wallpaper, celular, paisagem ou retrato. O botão de baixar salva na galeria."),
    ("Mapas de RPG", "\"Faz um mapa de masmorra com 6 salas\". Sai numerado e pronto para usar."),
    ("Anime e mangá", "\"Quando sai a próxima temporada de ...?\" e \"Quem é o personagem ...?\". Consulta o AniList."),
    ("Memória", "\"Lembra que eu gosto de café sem açúcar\". Para ver o que ela guardou: \"o que você sabe sobre mim?\". Para apagar: \"esquece ...\"."),
    ("Cofre de histórias e piadas", "\"Guarda essa piada: ...\". Depois: \"traz aquela piada sobre ...\". Para ver tudo: \"o que tem no meu cofre?\"."),
    ("Arquivos de texto", "Coloque seus .txt na pasta textos (em Android/data/com.spica.spica/files). Depois pergunte: \"o que tem no meu arquivo notas?\"."),
    ("Ver a imagem enviada", "Mande uma foto pelo ícone de imagem e pergunte o que quiser sobre ela."),
    ("Lembretes", "\"Me lembra às 15h de pagar a conta\". Cria o alarme no relógio do celular, sem tela."),
    ("Timers", "\"Timer de 25 minutos para estudar\". Inicia no relógio do celular."),
    ("Anotações", "\"Anota aí: comprar pão e café\" ou \"faz uma lista .txt para estudar\". Salva na pasta textos."),
    ("Agenda", "\"Marca estudo amanhã às 19h\". Abre a agenda com o evento pronto; você confirma lá."),
    ("Mensagens prontas", "\"Escreve uma mensagem para ... dizendo ...\". Abre as opções de envio com o texto; você escolhe o app e envia."),
    ("Lembrete do TikTok às 23h", "Se você não abriu o TikTok hoje e vinha abrindo nos dias anteriores, ela avisa. Precisa de acesso ao uso de apps ligado para a Spica."),
    ("Humor", "A Spica muda a expressão e o tom conforme a conversa. Pedir \"fica feliz\" não muda sozinho."),
]

PLANEJADO = [
    ("Cronogramas e rotina", "Um resumo do dia com clima, compromissos e estudo em ciclos de foco e pausa."),
    ("Análise de mensagens e grupos", "Ela resume o que importa das notificações de grupos. Só lê o que aparece como notificação."),
    ("Sugestões de resposta", "Ela sugere respostas no seu jeito de falar, para qualquer app. Você aprova antes de enviar."),
    ("Música", "Sugere trilhas para a cena que você descreve. Tocar exige um serviço de música."),
]


class AjudaScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        T.estilizar(self, md_bg_color=T.FUNDO)
        raiz = MDBoxLayout(orientation="vertical")
        T.estilizar(raiz, md_bg_color=T.FUNDO)
        raiz.add_widget(criar_barra(
            "Recursos da Spica",
            esquerda=("arrow-left", lambda: MDApp.get_running_app().navigate_to("configuracoes")),
        ))
        scroll = ScrollView(do_scroll_x=False, do_scroll_y=True, bar_width=dp(6),
                            scroll_type=["content", "bars"], scroll_timeout=150,
                            scroll_distance=dp(10), effect_cls=ScrollEffect)
        conteudo = MDBoxLayout(orientation="vertical", size_hint_y=None, padding=dp(20), spacing=dp(10))
        conteudo.bind(minimum_height=conteudo.setter("height"))
        conteudo.add_widget(self._linha("O que ela faz hoje", "titulo"))
        for nome, texto in FUNCIONA_HOJE:
            conteudo.add_widget(self._linha(nome, "item"))
            conteudo.add_widget(self._linha(texto, "corpo"))
        conteudo.add_widget(self._linha("Em breve", "titulo"))
        for nome, texto in PLANEJADO:
            conteudo.add_widget(self._linha(nome, "item"))
            conteudo.add_widget(self._linha(texto, "corpo"))
        scroll.add_widget(conteudo)
        raiz.add_widget(scroll)
        self.add_widget(raiz)

    def _linha(self, texto, estilo):
        cores = {"titulo": (T.MENTA, "H6"), "item": (T.CREME, "Subtitle1"), "corpo": (T.TEXTO_2, "Body2")}
        cor, fonte = cores[estilo]
        lbl = MDLabel(text=texto, font_style=fonte, size_hint_y=None, halign="left")
        T.estilizar(lbl, theme_text_color="Custom", text_color=cor)
        lbl.bind(width=lambda i, w: setattr(i, "text_size", (w, None)))
        lbl.bind(texture_size=lambda i, s: setattr(i, "height", s[1] + dp(6)))
        return lbl
