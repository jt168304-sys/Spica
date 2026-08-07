# Spica

Assistente virtual para Android, feita em Python com Kivy/KivyMD. Roda como app normal e também como uma bolha flutuante com expressões próprias, que continua funcionando mesmo com o app fechado.

## O que ela faz

- Conversa por texto, usando `groq/compound` como motor de IA — já vem com busca web nativa embutida (a própria IA decide quando pesquisar, e cita a fonte).
- Entende imagens: você manda uma foto e ela analisa e responde sobre o conteúdo, usando `qwen/qwen3.6-27b` (visão).
- Ouve e responde em voz alta, usando o reconhecimento de voz e o motor de texto-para-voz nativos do Android.
- Sabe a data e hora reais do aparelho a cada resposta, sem precisar buscar isso na web.
- **Bolha flutuante com expressões**: fica na tela por cima de outros apps, muda de "cara" de acordo com o tom da própria resposta (a IA se autoclassifica em um de 6 humores — neutro, feliz, surpresa, confusa, triste, chocada — e a expressão muda sozinha). Dá pra arrastar ela pra qualquer lugar, e um toque rápido abre um menuzinho com as opções de falar, mutar ou fechar.
- Tema claro/escuro, alternável nas configurações.

## Como funciona por baixo dos panos

O app inteiro é Python puro, sem nenhuma linha de Java/Kotlin escrita à mão. O acesso às APIs nativas do Android (TextToSpeech, SpeechRecognizer, janela de overlay, WakeLock, seletor de imagens) é feito via [pyjnius](https://github.com/kivy/pyjnius), que permite chamar classes Java diretamente do Python.

Estrutura principal:

```
main.py                        Ponto de entrada da Activity (UI), inicializacao e captura de erros
service.py                     Servico de segundo plano (foreground service, mantem a bolha viva
                                mesmo com o app fechado)
buildozer.spec                 Configuracao de build para gerar o APK
extra_manifest.xml             Bloco <queries> exigido desde o Android 11 p/ SpeechRecognizer/TTS

src/
├── core/
│   └── app_manager.py         App principal: tema, telas, permissoes
├── ui/
│   ├── image_handler.py       Seletor de imagem (camera/galeria)
│   └── screens/
│       ├── chat_screen.py     Tela de conversa
│       └── settings_screen.py Configuracoes (API key, tema, voz, bolha)
├── services/
│   ├── groq_service.py        Chamadas a API da Groq (texto e visao) + sistema de humor
│   ├── mood_service.py        Le assets/expressoes/humor.json e extrai a tag [HUMOR:xxx]
│   │                          que a IA anexa em cada resposta
│   ├── tts_service.py         Texto-para-voz nativo do Android
│   ├── voice_service.py       Reconhecimento de voz nativo do Android
│   ├── overlay.py             Bolha flutuante (janela, arrastar, menu, expressoes)
│   └── web_service.py         Scraper de busca web (nao usado atualmente - o
│                              groq/compound ja resolve isso nativamente; guardado
│                              pra um futuro sistema de tool-calling local)
├── utils/
│   ├── logger.py
│   ├── service_log.py         Log em arquivo (pasta Download publica) que funciona
│   │                          tanto na Activity quanto no service.py
│   ├── permissions.py
│   └── thread_safe.py
└── config/
    └── settings.py            Configuracoes persistentes (JSON local)

assets/
├── expressoes/                 12 PNGs (6 humores x boca aberta/fechada) + humor.json
│                                (humor.json e livremente editavel, sem precisar mexer
│                                em codigo Python)
└── live2d/                     Modelo Live2D (WebView + pixi-live2d-display) - EM PAUSA,
                                 nao esta em uso ativo no momento (ver secao abaixo)
```

## Sobre o modelo Live2D (`assets/live2d/`)

Existe uma implementação alternativa da bolha usando um modelo Live2D de verdade (animação 3D-like, física de cabelo, etc), renderizado numa WebView via PixiJS + pixi-live2d-display. Ela está **pausada, não em uso** — bateu num bug ainda não resolvido na hora de carregar o modelo (erro `Cannot read properties of undefined`, que persistiu em duas bibliotecas diferentes testadas). O código continua no repositório, intacto, para retomar quando tivermos acesso a um debug mais profundo (via `chrome://inspect`, que já está habilitado no app). Enquanto isso, a bolha usa o sistema de PNGs por humor (`assets/expressoes/`), que é mais simples e comprovadamente estável.

## Build

O APK é gerado via GitHub Actions, usando Buildozer com python-for-android. O workflow está em `.github/workflows/`. Basta dar push na branch `main` ou disparar manualmente pela aba Actions do repositório.

Build local também funciona (só em Linux/WSL):

```bash
pip install buildozer
buildozer android debug
```

O APK final fica em `bin/`.

## Configuração

A Spica precisa de uma chave de API da Groq pra funcionar (gratuita):

1. Crie uma conta em [console.groq.com](https://console.groq.com)
2. Gere uma API Key
3. No app: Configurações → cole a chave

Pra usar a bolha flutuante, é preciso liberar manualmente a permissão "Exibir sobre outros apps" — o próprio app leva você até a tela certa nas Configurações.

## Requisitos

- Android 11 (API 30) ou superior é o alvo testado atualmente. Versões mais antigas (Android 10 e anteriores) podem ter instabilidade — em investigação, não é uma limitação definitiva.
- Conexão com internet (a IA roda na nuvem, não no aparelho).

## Estado atual

Em desenvolvimento ativo. Chat, visão, voz e bolha flutuante com expressões já funcionam de ponta a ponta, inclusive com o app em segundo plano (com ressalvas: escuta contínua fora do app funciona de forma intermitente, é uma limitação conhecida do `SpeechRecognizer` padrão do Android fora de foco de tela). Não há por enquanto notas, calculadora, tradutor ou outras ferramentas — o foco é só a assistente conversacional. Próximo passo planejado: leitura do sistema de arquivos do Android como contexto adicional para a IA.
