# Spica

Assistente virtual para Android, feita em Python com Kivy/KivyMD. Roda como app normal e também como uma bolha flutuante que continua funcionando mesmo com o app fechado.

## O que ela faz

- Conversa por texto, usando a API da Groq (Llama 3.1) como motor de IA.
- Entende imagens: você manda uma foto e ela analisa e responde sobre o conteúdo.
- Ouve e responde em voz alta, usando o reconhecimento de voz e o motor de texto-para-voz nativos do Android.
- Tem uma bolha flutuante que fica na tela por cima de outros apps. Dá pra arrastar ela pra qualquer lugar, e um toque rápido abre um menuzinho com as opções de falar, mutar ou fechar. A conversa por voz através da bolha funciona mesmo com você fora do app.
- Tema claro/escuro, alternável nas configurações.

## Como funciona por baixo dos panos

O app inteiro é Python puro, sem nenhuma linha de Java/Kotlin escrita à mão. O acesso às APIs nativas do Android (TextToSpeech, SpeechRecognizer, janela de overlay, seletor de imagens) é feito via [pyjnius](https://github.com/kivy/pyjnius), que permite chamar classes Java diretamente do Python.

Estrutura principal:

```
main.py                        Ponto de entrada, inicializacao e captura de erros
service.py                     Servico de segundo plano (ainda nao usado pela build atual)
buildozer.spec                 Configuracao de build para gerar o APK

src/
├── core/
│   └── app_manager.py         App principal: tema, telas, permissoes
├── ui/
│   ├── image_handler.py       Seletor de imagem (camera/galeria)
│   └── screens/
│       ├── chat_screen.py     Tela de conversa
│       └── settings_screen.py Configuracoes (API key, tema, voz, bolha)
├── services/
│   ├── groq_service.py        Chamadas a API da Groq (texto e visao)
│   ├── tts_service.py         Texto-para-voz nativo do Android
│   ├── voice_service.py       Reconhecimento de voz nativo do Android
│   └── overlay.py             Bolha flutuante (janela, arrastar, menu, permissoes)
├── utils/
│   ├── logger.py
│   ├── permissions.py
│   └── thread_safe.py
└── config/
    └── settings.py            Configuracoes persistentes (JSON local)

assets/
├── boca_aberta.png             Avatar da bolha falando
└── boca_fechada.png            Avatar da bolha em silencio
```

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

- Android 7.0 (API 24) ou superior
- Conexão com internet (a IA roda na nuvem, não no aparelho)

## Estado atual

Em desenvolvimento ativo. Chat, visão, voz e bolha flutuante já funcionam de ponta a ponta, inclusive com o app em segundo plano. Não há por enquanto notas, calculadora, tradutor ou outras ferramentas — o foco é só a assistente conversacional.
