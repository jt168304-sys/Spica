# Escuta continua no Android 14 (Moto G24)

Documento tecnico sobre o problema da escuta continua fora do app no Android 14, a causa raiz, por que as configuracoes do celular nao resolvem, e o passo a passo da correcao implementada no codigo.

---

## 1. Sintoma

A Spica usa reconhecimento de voz nativo do Android (`SpeechRecognizer`) para:

- ouvir no chat (app aberto, em primeiro plano)
- ouvir pela bolha flutuante em modo de escuta continua (app em segundo plano / overlay sobre outros apps)

Comportamento observado:

| Ambiente | Dentro do app | Fora do app (bolha / segundo plano) |
|---|---|---|
| Android 10 | Funciona | Funciona |
| Android 14 (Moto G24) | Funciona | Microfone **inicia** (LED/indicador acende), mas **nao capta voz** |

O usuario ja desativou, no aparelho:

- restricao de segundo plano
- otimizacao de bateria
- limitacoes de microfone nas configuracoes do sistema

Nada disso resolveu. Isso e esperado: o bloqueio **nao e** a tela de "apps em segundo plano" do usuario. E uma regra de privacidade do Android 12+ (endurecida no 14), aplicada pelo proprio sistema ao processo que grava o audio.

---

## 2. O que Nao e o problema

Antes de ir ao codigo, vale descartar o que o sintoma parece, mas nao e:

1. **Permissao `RECORD_AUDIO` negada**  
   Se estivesse negada, o microfone nem iniciaria. Aqui o indicador acende.

2. **Permissao "Exibir sobre outros apps" (`SYSTEM_ALERT_WINDOW`)**  
   A bolha aparece. Overlay funciona. O problema e so o audio.

3. **Otimizacao de bateria / "nao restringir segundo plano"**  
   O usuario ja desativou. No Android 14 o microfone em background e uma politica **separada** dessas telas.

4. **WakeLock**  
   Sem WakeLock a CPU dorme e o servico morre. Aqui o servico continua vivo e o mic "liga". Nao e morte do processo.

5. **Bug de Kivy `Clock` no `service.py`**  
   Ja existiu (callbacks com `usar_clock=True` nunca disparavam no processo do servico). Isso foi corrigido antes. O sintoma atual e diferente: o reconhecedor inicia, mas o audio chega vazio / `ERROR_NO_MATCH` (codigo 7, "Nao ouvi").

---

## 3. Causa raiz

### 3.1 Dois processos diferentes gravando audio

No Android, reconhecimento de voz tem dois caminhos:

**Caminho A — `SpeechRecognizer` (Google / Motorola)**

```
App Spica (UID da Spica)
    -> SpeechRecognizer.startListening()
        -> servico do Google (OUTRO UID / OUTRO processo)
            -> AudioRecord no processo do Google
            -> devolve texto para a Spica
```

O PCM **nao e gravado pela Spica**. Quem abre o microfone e o app/servico de reconhecimento do sistema.

**Caminho B — `AudioRecord` no proprio app**

```
App Spica (UID da Spica)
    -> AudioRecord.startRecording()
        -> PCM no mesmo UID
        -> app envia o WAV para transcrever (Whisper / Groq)
```

O PCM e gravado **no processo da Spica**.

### 3.2 A regra do Android 12+ / 14

A partir do Android 12 (API 31), e de forma dura no Android 14 (API 34):

> Um app so pode capturar microfone em segundo plano se estiver rodando um **Foreground Service** com `foregroundServiceType="microphone"` **e** a permissao `FOREGROUND_SERVICE_MICROPHONE`.

Se essa condicao nao for cumprida, o sistema:

- ainda deixa o `AudioRecord` / reconhecedor **iniciar** (por isso o LED acende)
- entrega **audio silenciado** (zeros) para o processo que nao tem o tipo FGS

Isso bate 1:1 com o relato: "o microfone inicia quando em segundo plano, mas nao capta a voz".

### 3.3 Por que o Google SpeechRecognizer quebra mesmo com FGS

Mesmo que a Spica suba um FGS tipo `microphone`, o `SpeechRecognizer` **grava no processo do Google**, nao no UID da Spica.

O tipo `microphone` do FGS **nao e herdado por outro app**. O Google, em segundo plano, recebe silêncio. A Spica recebe `onError(7)` (`ERROR_NO_MATCH`) ou resultado vazio — exatamente o "Nao ouvi" do `voice_service.py`.

No Android 10 essa politica ainda nao existia (ou era frouxa). Por isso la funciona dentro e fora do app com o mesmo `SpeechRecognizer`.

No Moto G24 (Android 14 + camada Motorola / Hello UI) a politica e aplicada de forma agressiva. OEM Motorola e conhecida por silenciar mic de background mesmo em cenarios em que outros fabricantes ainda deixam passar.

### 3.4 Segundo problema no codigo antigo: o FGS nunca subia

O `buildozer.spec` ja tinha:

```
android.permissions = ... FOREGROUND_SERVICE, FOREGROUND_SERVICE_MICROPHONE ...
android.services = Spicaservice:service.py:foreground:foregroundServiceType=microphone
```

Mas **nenhum ponto do Python chamava `ServiceSpicaservice.start()`**.

Fluxo antigo:

1. Usuario toca "Ativar Bolha" em `settings_screen.py`
2. A Activity cria o overlay (`SpicaOverlay.ligar_bolha()`)
3. Usuario ativa escuta continua no menu da bolha
4. `VoiceService.ouvir()` usa `SpeechRecognizer` com `PythonActivity.mActivity`
5. Usuario sai do app -> Activity vai para `on_pause`
6. `SpeechRecognizer` do Google tenta gravar em background **sem FGS tipo microphone no UID da Spica**
7. Sistema entrega silencio

O `service.py` so rodaria se o FGS fosse iniciado. Sem `start()`, o arquivo existia no APK e nunca executava no uso normal da bolha.

---

## 4. Arquitetura antiga (quebrada no 14)

```
[Activity / UI]
    overlay.py  -- escuta continua -->  voice_service.py
                                            |
                                            v
                                    SpeechRecognizer (Google)
                                            |
                                            v  (Android 14: audio = silencio)
                                    "Nao ouvi"

[service.py]
    declarado no buildozer.spec
    NUNCA iniciado pela Activity
```

Trecho critico antigo em `src/services/voice_service.py`:

- `SpeechRecognizer.createSpeechRecognizer(PythonActivity.mActivity)`
- `recognizer.startListening(intent)`
- tentativa de `requestAudioFocus` (nao resolve: o problema nao e foco de musica, e **privacidade de mic em background**)

Trecho critico antigo em `src/ui/screens/settings_screen.py`:

- `_ativar_bolha()` so ligava o overlay
- nao pedia `POST_NOTIFICATIONS`
- nao chamava o foreground service

---

## 5. Arquitetura nova (corrigida)

```
[Activity / UI]
    overlay.py  -- escuta continua -->  voice_service.py
                                            |
                        captura_local=True  |
                                            v
                                    listen_ipc.pedir_escuta()
                                            |
                    arquivo em cache/       v
                                    spica_listen.cmd

[Foreground Service — service.py]
    startForeground(..., FOREGROUND_SERVICE_TYPE_MICROPHONE)
    WakeLock
    loop:
        se existir spica_listen.cmd:
            AudioRecord no UID da Spica   <-- PCM real
            Whisper (Groq)                <-- texto
            escreve spica_listen.out

[Activity]
    le spica_listen.out
    segue o fluxo normal (Groq chat + TTS)
```

Pontos-chave:

1. Quem grava e a Spica (`AudioRecord`), nao o Google.
2. Quem grava esta num FGS com tipo `microphone`.
3. O overlay continua na Activity (ja funcionava).
4. A transcricao usa Whisper na Groq (`whisper-large-v3-turbo`, fallback `whisper-large-v3`), com a mesma API key ja configurada no app.

Limitacao honesta: escuta continua fora do app **depende de internet** (Whisper na nuvem). O `SpeechRecognizer` do Google funcionava offline no aparelho. No Android 14 esse caminho offline nao e confiavel em background. Nao ha API publica que entregue STT nativo **e** herde o FGS de microfone do app.

---

## 6. Passo a passo da correcao (codigo)

### Passo 1 — Declarar permissoes e o tipo do servico

Arquivo: `buildozer.spec`

Necessario:

```
android.permissions = INTERNET,RECORD_AUDIO,VIBRATE,FOREGROUND_SERVICE,FOREGROUND_SERVICE_MICROPHONE,WAKE_LOCK,CAMERA,READ_MEDIA_IMAGES,SYSTEM_ALERT_WINDOW,POST_NOTIFICATIONS

android.services = Spicaservice:service.py:foreground:foregroundServiceType=microphone
```

Por que cada uma:

| Permissao / chave | Para que |
|---|---|
| `RECORD_AUDIO` | Abrir o microfone (runtime, o usuario aceita) |
| `FOREGROUND_SERVICE` | Poder chamar `startForeground()` |
| `FOREGROUND_SERVICE_MICROPHONE` | Android 14 exige essa permissao **alem** do tipo no servico |
| `WAKE_LOCK` | Impedir a CPU de dormir no `service.py` |
| `POST_NOTIFICATIONS` | Android 13+ exige para a notificacao persistente do FGS |
| `SYSTEM_ALERT_WINDOW` | Bolha sobre outros apps |
| `foregroundServiceType=microphone` | O tipo que libera o mic em background |

Sem `FOREGROUND_SERVICE_MICROPHONE` + tipo `microphone`, o Android 14 lanca `SecurityException` ou silencia o audio.

Tambem em `src/utils/permissions.py`: pedir `POST_NOTIFICATIONS` no arranque, junto com `RECORD_AUDIO`.

### Passo 2 — Subir o FGS enquanto o app ainda esta visivel

Arquivo: `src/services/fg_service.py`

O Android 14 **proibe** iniciar um FGS tipo `microphone` a partir de background. Tem que subir com a Activity em primeiro plano (ao ativar a bolha, ao ligar escuta, ou no `on_pause` **antes** de perder o foco).

`iniciar_servico()`:

1. Resolve a classe gerada pelo python-for-android (`com.spica.spica.ServiceSpicaservice`)
2. Chama `ServiceSpicaservice.start(ctx, argumento)`
3. Se nao houver `.start`, cai para `startForegroundService(Intent)`

`promover_foreground_microfone(service)`:

O p4a pode chamar `startForeground(id, notification)` **sem o tipo**. No 14 isso nao libera o mic. O codigo chama de novo:

```
service.startForeground(9001, notificacao, 128)
```

`128` = `FOREGROUND_SERVICE_TYPE_MICROPHONE`.

A notificacao e obrigatoria. Sem ela o sistema mata o servico. Texto: "Spica / Escuta em segundo plano".

### Passo 3 — Chamar o FGS nos pontos certos da UI

Arquivo: `src/ui/screens/settings_screen.py` — `_ativar_bolha()`

1. Checa overlay (`canDrawOverlays`)
2. Pede `RECORD_AUDIO` e `POST_NOTIFICATIONS` se faltarem
3. Chama `iniciar_servico("escuta")` **antes** de criar a bolha
4. Liga o overlay na Activity

Arquivo: `src/core/app_manager.py` — `on_pause()`

Se a bolha estiver ligada, reforca `iniciar_servico("escuta")` no momento em que o usuario sai do app. Ainda conta como transicao a partir de primeiro plano.

Arquivo: `src/services/overlay.py` — `_alternar_escuta_continua()`

Ao ligar escuta continua, chama `iniciar_servico("escuta")` de novo (idempotente) e dispara o ciclo com `captura_local=True`.

### Passo 4 — Gravar PCM no processo do FGS (`AudioRecord`)

Arquivo: `src/services/mic_recorder.py`

- Fonte: `VOICE_RECOGNITION`, fallback `MIC`, fallback `CAMCORDER`
- 16 kHz, mono, PCM 16-bit (formato que o Whisper aceita bem)
- VAD simples por RMS:
  - espera fala ate 10 s
  - limiar ~280
  - corta apos ~1.15 s de silencio
  - maximo 8 s por utterance
- Escreve WAV em `getCacheDir()` (`spica_utt.wav`)

Se `getRecordingState()` nao for `RECORDSTATE_RECORDING`, aborta. Se o RMS maximo ficar abaixo do limiar, trata como audio silenciado pelo sistema (o sintoma antigo) e devolve `None`.

### Passo 5 — Transcrever com Whisper (Groq), nao com Google STT

Arquivo: `src/services/voice_service.py`

Dois caminhos em `ouvir()`:

- `captura_local=False` e Activity em foco: ainda pode usar `SpeechRecognizer` (chat dentro do app)
- `captura_local=True` (bolha / escuta continua): **nao** usa Google

Fluxo local:

1. Se **nao** estamos no processo do servico: sobe o FGS, espera ~0.4 s, pede a captura via IPC
2. Se o FGS responder, entrega o texto
3. Se o FGS nao responder a tempo, fallback: `AudioRecord` na propria Activity (melhor que silencio total; no G24 pode ainda vir mudo)

`_transcrever_whisper()`:

- `POST https://api.groq.com/openai/v1/audio/transcriptions`
- modelo `whisper-large-v3-turbo`, fallback `whisper-large-v3`
- `language=pt`
- usa a mesma `api_key` do `Settings`

### Passo 6 — IPC entre Activity e FGS

Arquivo: `src/services/listen_ipc.py`

Os dois processos nao compartilham memoria Python. Comunicam por arquivos no `cacheDir` do app (acessivel aos dois, mesmo UID):

| Arquivo | Quem escreve | Significado |
|---|---|---|
| `spica_listen.cmd` | Activity | "grave agora" |
| `spica_listen.out` | FGS | texto reconhecido ou `Nao ouvi` |

Timeout do pedido: 45 s (espera de fala + Whisper).

Arquivo: `service.py`

Depois de WakeLock + `promover_foreground_microfone`:

```
loop:
    se ha_pedido():
        AudioRecord.capturar_utterance()
        Whisper
        responder(texto)
    sleep 0.15s
```

O overlay **nao** e recriado no `service.py`. Duas bolhas (Activity + Service) geram conflito de `WindowManager`. Overlay fica so na Activity; o FGS so segura o tipo microphone e grava.

### Passo 7 — Encerrar direito

Ao fechar a bolha (`desligar_bolha`):

1. `escuta_continua = False`
2. `VoiceService.destruir()` (solta `AudioRecord`)
3. `parar_servico()` (`stopSelf()` se ja estamos no FGS)

Sem isso o FGS fica eterno com a notificacao na barra.

---

## 7. Passo a passo para testar no Moto G24

1. Gerar APK novo (GitHub Actions em `.github/workflows/build.yml` ou `buildozer android debug`). Sem rebuild, o aparelho continua no codigo antigo.

2. Instalar por cima (ou desinstalar antes, para limpar cache).

3. Abrir a Spica, conceder:
   - Microfone
   - Notificacoes (Android 13+)
   - Exibir sobre outros apps

4. Configuracoes -> **Ativar Bolha**.

5. Conferir a barra de notificacoes: tem que aparecer **"Spica — Escuta em segundo plano"** (ou "Spica escuta").  
   **Se essa notificacao nao existir, o Android 14 vai silenciar o mic.** Esse e o teste decisivo de que o FGS subiu com o tipo certo.

6. Sair do app (Home). A bolha permanece.

7. Toque na bolha -> **Falar / Ativar**.

8. Falar uma frase. Esperar ~1–3 s apos o silencio (VAD + Whisper). A Spica deve responder em voz alta.

9. Se falhar, olhar o log em Downloads: `spica_service_log.txt`.

Linhas que importam:

| Log | Significado |
|---|---|
| `Foreground service iniciado via start()` | FGS subiu |
| `startForeground(microphone) OK` | Tipo microphone aplicado |
| `pedindo captura ao FGS` | Activity pediu gravacao |
| `AudioRecord.startRecording state=3` | Mic realmente em RECORDING |
| `timeout sem fala (max_rms=0)` | Sistema ainda entregando silencio |
| `whisper: '...'` | Transcricao ok |
| `FGS nao respondeu` | IPC / servico nao esta rodando |

---

## 8. Se ainda nao captar voz no G24

Ordem de checagem:

1. **Notificacao do FGS visivel?**  
   Nao -> `iniciar_servico` falhou (classe errada, permissao, ou tentativa de start em background). Ver log `classe FGS:` e `Falha ao iniciar FGS`.

2. **`startForeground(microphone) OK` no log?**  
   Se so apareceu `startForeground() sem tipo OK`, o p4a/Android recusou o tipo 128. Conferir se o APK foi gerado com `foregroundServiceType=microphone` no manifest (nao basta o `.spec` se o cache do buildozer estiver velho — limpar `.buildozer` e rebuild).

3. **`max_rms=0` mesmo com FGS tipo microphone?**  
   OEM Motorola pode exigir:
   - Permissao de microfone em **"Permitir o tempo todo"** (nao so "enquanto o app estiver em uso"). No Android 14 isso aparece em Configuracoes -> Apps -> Spica -> Permissoes -> Microfone.
   - Desativar qualquer "protecao de privacidade" / "bloqueio de mic para apps em segundo plano" da Hello UI, se existir alem das opcoes genericas.

4. **Whisper HTTP 401 / 429**  
   Chave Groq ausente ou limite. A escuta continua nova **precisa** da key. Sem ela o chat por texto tambem ja nao funciona.

5. **Duas instancias de overlay**  
   Se a bolha duplicar, o toque pode estar na instancia errada. O `service.py` atual nao deve criar overlay.

---

## 9. Limitacao real do Android 14 (nao da para "desligar nas configuracoes")

O Google documenta isso como protecao de privacidade, nao como bug:

- Android 9–10: mic em background relativamente livre
- Android 11: package visibility (`<queries>` para `RecognitionService` — ja temos em `extra_manifest.xml`)
- Android 12: mic/camera em background so com FGS do tipo certo; indicador de privacidade na barra
- Android 13: `POST_NOTIFICATIONS`; FGS types mais rígidos
- Android 14: FGS tipo `microphone` **so pode ser iniciado em primeiro plano**; tipo especial `specialUse` foi restringido; audio de outro UID continua silenciado

Consequencia para assistentes tipo Spica:

**Nao existe** um jeito suportado de:

- usar o `SpeechRecognizer` do Google
- com o app fora de foco
- no Android 14
- e receber PCM de verdade

A unica via suportada e: **Foreground Service tipo microphone + captura no proprio UID**.

Workarounds que **nao** funcionam e nao devem ser tentados:

- overlay "falso primeiro plano" para enganar o SpeechRecognizer
- acessibilidade para gravar audio
- desabilitar Play Protect / "opcoes de desenvolvedor" como solucao
- pedir ao usuario so "irrestrito" na bateria (necessario, mas insuficiente)

O que o usuario **ainda precisa** no aparelho (complemento, nao substituto do codigo):

1. Microfone = Permitir o tempo todo (se o G24 mostrar essa opcao)
2. Notificacoes da Spica = permitidas
3. Bateria = Sem restricoes / Nao otimizar
4. Exibir sobre outros apps = ligado
5. Nao deslizar a notificacao persistente da Spica para fora (isso para o FGS)

---

## 10. Arquivos envolvidos nesta correcao

| Arquivo | Papel |
|---|---|
| `buildozer.spec` | Permissoes + FGS tipo microphone + `POST_NOTIFICATIONS` |
| `src/utils/permissions.py` | Pede notificacoes em runtime |
| `src/services/fg_service.py` | Start/stop do FGS e `startForeground(..., microphone)` |
| `service.py` | Processo do FGS: WakeLock, tipo mic, loop AudioRecord+Whisper |
| `src/services/mic_recorder.py` | Captura PCM / VAD / WAV |
| `src/services/listen_ipc.py` | Pedido Activity <-> resposta FGS |
| `src/services/voice_service.py` | Dual path: Google STT no chat, Whisper na escuta continua |
| `src/services/overlay.py` | Liga FGS e usa `captura_local=True` |
| `src/ui/screens/settings_screen.py` | Ativar bolha sobe o FGS com o app visivel |
| `src/core/app_manager.py` | Reforca FGS no `on_pause` |

---

## 11. Resumo em uma frase

No Android 14 o Google SpeechRecognizer grava em outro processo e recebe silencio; a Spica precisa gravar ela mesma, dentro de um Foreground Service tipo `microphone` iniciado ainda em primeiro plano, e transcrever o WAV (Whisper) — configuracoes de bateria/segundo plano do celular nao furam essa regra.
