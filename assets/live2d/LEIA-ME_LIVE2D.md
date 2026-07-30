# Como terminar a integração do Live2D na Spica

## 1. Baixe o Cubism Core (obrigatório, e eu não posso fazer isso por você)

O `live2dcubismcore.min.js` é a engine de runtime da Live2D e é **proprietário** —
a licença deles não permite que terceiros redistribuam esse arquivo, então ele
não vem no pacote e eu não consigo baixá-lo automaticamente por você.

Passos:
1. Acesse https://www.live2d.com/en/sdk/download/web/
2. Baixe o **Cubism SDK for Web** (é gratuito, só precisa aceitar os termos).
3. Dentro do zip baixado, ache o arquivo `Core/live2dcubismcore.min.js`.
4. Copie esse arquivo para: `assets/live2d/live2dcubismcore.min.js`
   (ou seja, na mesma pasta onde está o `index.html` deste projeto).

Sem esse arquivo, a WebView carrega a página mas o modelo não anima
(vai dar erro de `live2dcubismcore is not defined` no `console` da WebView).

## 2. Conexão com a internet na primeira execução

O `index.html` carrega `pixi.js` e `pixi-live2d-display` via CDN (jsdelivr/cdnjs)
para não precisar embutir essas libs no APK. Isso significa que **o celular
precisa de internet na hora em que a bolha for aberta** (mesma exigência que
já existe para a API da Groq). Se quiser eliminar essa dependência de rede,
me avise — dá pra baixar os `.js` das duas libs e colocar local em
`assets/live2d/vendor/`, mesma lógica do Cubism Core.

## 3. Sobre a licença do modelo (おさげの少女 / osagegirl)

Segundo o `使い方.txt` que veio com o modelo: uso pessoal e VTuber liberado,
inclusive monetização de vídeo/live. **Proibido**: redistribuir os arquivos
do modelo isoladamente, uso comercial não autorizado da arte em si, e criar
produtos físicos centrados nela. Ou seja: pode usar na Spica à vontade, só
não vale publicar/redistribuir os arquivos do modelo separados do seu app.
Autor: プーン (https://twitter.com/pu__n) — não é obrigatório creditar, mas é
gentil deixar créditos em algum "sobre" do app.

## 4. O que já foi conectado no código Python (`src/services/overlay.py`)

- `ligar_bolha()` agora cria uma `android.webkit.WebView` transparente no
  lugar do antigo `ImageView`, carregando `assets/live2d/index.html`.
- `definir_avatar_png(falar=True/False)` — nome mantido por compatibilidade
  com o resto do código (TTS chama esse método) — agora injeta JS
  (`SpicaLive2D.falarSimples(...)`) que abre/fecha a boca em loop simples
  enquanto o TTS está falando.
- Novo método `definir_expressao("びっくり目")` para disparar as expressões
  que vieram com o modelo (`eyes_bikkuri`, `eyes_guruguru`, `eyes_zetubou`,
  `face_aozame`) — ainda não conectado a nenhum gatilho automático; dá pra
  chamar, por exemplo, quando a Spica "se assusta" com alguma resposta.
- Arraste da bolha e o menu de toque continuam funcionando exatamente como
  antes — `WebView` também é uma `View` normal do Android, então o mesmo
  `OnTouchListener` nativo que já existia se aplica sem mudança.

## 5. Próximo passo natural (lip-sync de verdade)

Hoje o `falarSimples()` é um abre/fecha de boca em intervalo fixo (120ms),
só pra ter movimento enquanto fala — não é sincronizado com a amplitude
real do áudio do TTS. Um lip-sync de verdade exigiria capturar a amplitude
do áudio do TTS Android em tempo real (não trivial, TTS nativo do Android
não expõe isso facilmente) ou trocar por um TTS que gere um arquivo de
áudio (em vez de falar direto), analisar a amplitude, e alimentar
`SpicaLive2D.setBoca(valor)` frame a frame. Se quiser seguir esse caminho
depois, me chama.
