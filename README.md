# Trabalho SOFT B

Aplicação desktop em Python que captura a webcam, executa o modelo
**YOLO-World** em cada frame e mostra, em uma interface Tkinter, os objetos
detectados com caixa, nome em português e nível de confiança.

> Projeto prático de Engenharia de Software / Programação em Python.

## Integrantes

- Nome 1
- Nome 2

## Objetivo

Construir uma aplicação capaz de receber imagens continuamente de uma câmera,
aplicar um modelo de visão computacional sobre elas e apresentar o resultado em
uma interface gráfica **sem bloquear a interação do usuário**.

## O que a aplicação reconhece

São **74 tipos de objeto em 8 categorias**. Cada categoria tem uma cor, que é
usada nas caixas do vídeo, nos filtros e na lista lateral.

| Categoria    | Itens |
| ------------ | ----- |
| Pessoas      | Homem, Mulher, Criança, Mão |
| Acessórios   | Óculos, Óculos de sol, Aliança, Crachá, Relógio, Pulseira, Colar, Brinco, Boné, Chapéu, Gravata, Máscara, Mochila, Bolsa, Carteira |
| Escritório   | Lápis, Caneta, Marca-texto, Borracha, Régua, Tesoura, Grampeador, Calculadora, Livro, Caderno, Estojo, Post-it |
| Eletrônicos  | Celular, Notebook, Tablet, Monitor, Teclado, Mouse, Fone de ouvido, Fone sem fio, Controle remoto, Controle de videogame, Câmera, Carregador, Pendrive, Caixa de som |
| Cozinha      | Garrafa, Garrafa térmica, Caneca, Copo, Lata, Prato, Tigela, Garfo, Colher, Faca |
| Alimentos    | Banana, Maçã, Laranja, Pão, Sanduíche, Biscoito, Chocolate |
| Casa         | Cadeira, Sofá, Planta, Luminária, Relógio de parede, Chave, Guarda-chuva, Escova de dentes, Ursinho de pelúcia |
| Animais      | Cachorro, Gato, Pássaro |

O vocabulário fica em um único dicionário, `CATEGORIAS`, em
[`modelo.py`](modelo.py), no formato `prompt em inglês -> nome na tela`
(ex.: `"spiral notebook": "Caderno"`). Para adicionar ou remover objetos basta
editar o dicionário: o modelo é recriado automaticamente na próxima execução,
usando o CLIP que já está em `weights/clip/`.

> **Homem / Mulher** é uma estimativa visual feita pelo modelo a partir da
> aparência; ela pode errar e não deve ser tratada como informação confiável
> sobre a pessoa.

### Por que YOLO-World e não o YOLO11n?

O `yolo11n.pt` do roteiro só conhece as 80 classes do COCO — óculos, aliança,
crachá, lápis, caneta e relógio de pulso **não estão** nessa lista, e ele não
distingue homem de mulher. Treinar um modelo está fora do escopo (seção 4.2).
O YOLO-World é um detector de *vocabulário aberto*: as classes são descritas em
texto e codificadas pelo CLIP. Depois de definidas, o modelo é salvo em
`modelo_soft_b.pt` com o vocabulário embutido e roda sem o CLIP.

## Tecnologias

| Componente             | Responsabilidade                                     |
| ---------------------- | ---------------------------------------------------- |
| Python 3               | Orquestra toda a aplicação                           |
| OpenCV (`cv2`)         | Abre a webcam, captura frames e converte BGR → RGB   |
| Ultralytics YOLO-World | Executa a inferência e produz as detecções           |
| Pillow                 | Desenha caixas/etiquetas e converte para o Tkinter   |
| Tkinter                | Janela, botões, painel de estatísticas e exibição    |

## Arquitetura

```
[ USUÁRIO ] → [ Tkinter / main.py ] → [ classe Aplicacao ]
                                              │
                        ┌─────────────────────┴───────────────────┐
                        ▼                                         ▼
                 [ OpenCV ] captura                 [ modelo.py ] YOLO-World
                        └─────────────────────┬───────────────────┘
                                              ▼
                                [ frame BGR + caixas (x1,y1,x2,y2) ]
                                              ▼
                              [ desenho.py ] Pillow anota em português
                                              ▼
                                     [ Tkinter exibe ]
```

| Módulo        | Papel                                                        |
| ------------- | ------------------------------------------------------------ |
| `main.py`     | Interface, botões, estado da câmera, loop com `after()`      |
| `modelo.py`   | Dicionário `CLASSES` e `carregar_modelo()`                   |
| `desenho.py`  | `desenhar_deteccoes()` — visual moderno com fonte com acentos |

A atualização do vídeo usa `janela.after(...)`, nunca `while True`, para
preservar o loop de eventos do Tkinter. O modelo é carregado em uma thread
separada para a janela abrir imediatamente.

**Duas threads durante a captura.** O YOLO-World leva ~130 ms por frame na
CPU; se a detecção rodasse no mesmo fluxo que exibe a imagem, o vídeo ficaria
preso em ~7 FPS. Por isso a thread principal só captura, desenha e exibe
(~30 FPS), enquanto uma *thread de detecção* pega sempre o frame mais recente,
roda `predict()` e publica as caixas. As duas trocam dados por meio de um
`threading.Lock`. O painel mostra os dois números: **FPS** e
**Inferência (ms)**.

## Instalação

Dê dois cliques em **`Iniciar.bat`**. Na primeira execução em cada computador
ele cria o ambiente virtual e instala as bibliotecas sozinho (precisa de
internet e do Python 3.11 a 3.13 instalado); nas seguintes, só abre o programa.

O ambiente virtual fica **fora** da pasta do projeto, em
`%LOCALAPPDATA%\TrabalhoSOFTB\venv`. Um ambiente virtual só funciona no
computador em que foi criado e tem cerca de 1 GB, então ele não deve ser
copiado, sincronizado no OneDrive nem entregue junto com o trabalho.

Para instalar manualmente:

```powershell
py -3.12 -m venv "$env:LOCALAPPDATA\TrabalhoSOFTB\venv"
& "$env:LOCALAPPDATA\TrabalhoSOFTB\venv\Scripts\Activate.ps1"
python -m pip install -r requirements.txt
```

No VS Code o interpretador já vem apontado em `.vscode/settings.json`. Se
precisar escolher à mão: `Ctrl+Shift+P` → **Python: Select Interpreter** →
`%LOCALAPPDATA%\TrabalhoSOFTB\venv\Scripts\python.exe`.

### Modelo personalizado (`modelo_soft_b.pt`)

- Se o arquivo `modelo_soft_b.pt` estiver na pasta, nada mais é necessário.
- Se não estiver (ou se você editar `CLASSES`), a aplicação o cria sozinha na
  primeira execução. Isso baixa `yolov8s-worldv2.pt` (~26 MB) e o codificador
  CLIP (~340 MB) **uma única vez**, e precisa do pacote `clip`:

  ```powershell
  python -m pip install git+https://github.com/ultralytics/CLIP.git
  python modelo.py
  ```

## Execução

Sem abrir o VS Code: dê dois cliques em **`Iniciar.bat`** (ele usa o Python do
ambiente virtual automaticamente). Para ter um atalho na área de trabalho, clique com o
botão direito em `Iniciar.bat` → *Enviar para* → *Área de trabalho (criar atalho)*.

Pelo terminal:

```powershell
python main.py
```

## Testes por etapa

Os scripts da pasta `testes/` seguem a ordem do roteiro. Não avance enquanto
o teste da etapa atual apresentar erro.

| Etapa | Script                              | O que verifica                           |
| ----- | ----------------------------------- | ---------------------------------------- |
| 12.1  | `testes/01_teste_python.py`         | Interpretador correto (.venv)            |
| 12.2  | `testes/02_teste_importacoes.py`    | cv2, tkinter, PIL e ultralytics          |
| 12.3  | `testes/03_teste_tkinter.py`        | Janela Tkinter abre                      |
| 12.4  | `testes/04_teste_webcam.py`         | Webcam funciona sem YOLO (`q` para sair) |
| 12.5  | `testes/05_teste_yolo.py`           | Modelo base carrega                      |
| 12.6  | `testes/06_teste_yolo_imagem.py`    | Detecção em `imagens/teste.jpg`          |
| 13    | `testes/07_teste_yolo_webcam.py`    | YOLO + webcam, sem Tkinter               |
| extra | `testes/08_teste_modelo_soft_b.py`  | Modelo personalizado e classes em PT     |

## Funcionalidades

**Requisitos obrigatórios (RF01–RF10)**

- Iniciar / Parar câmera e Sair com liberação segura da webcam.
- Detecção em cada frame com caixa, classe em português e confiança.
- Indicador de estado da câmera (ativa / desligada / carregando modelo).
- Proteção contra abertura duplicada da câmera.
- Interface responsiva via `after()`; modelo carregado em segundo plano.
- Mensagens de erro compreensíveis (câmera indisponível, modelo, dependências).

**Atividades obrigatórias**

- Status da câmera na interface (Atividade 3).
- Contagem de objetos no frame atual (Atividade 4).
- Lista de classes detectadas com quantidade (Atividade 5).

**Desafios de evolução implementados**

- Botão **Salvar foto** com data e hora em `capturas/`.
- Estimativa de FPS.
- Controle de confiança por slider (0,05 a 0,90).
- Seleção do índice da câmera.
- Projeto separado em módulos (`main.py`, `modelo.py`, `desenho.py`).
- Visual das detecções: preenchimento translúcido, cantos em destaque e
  etiqueta arredondada com acentos (Pillow, em vez de `results.plot()`).
- Interface com tema escuro, painel de estatísticas e transições suaves
  (fade-in da janela, hover nos botões, pulso no indicador de status).

**Melhorias de UI/UX**

- **Filtro "Detectar"**: um chip liga/desliga por categoria. Ao passar o mouse,
  aparece a lista de itens da categoria. O filtro é aplicado com
  `predict(classes=...)`.
- **Cor por categoria**, igual no vídeo, nos chips e na lista lateral.
- **Lista de classes** com bolinha colorida e quantidade, ordenada pelas mais
  frequentes. As linhas são reaproveitadas a cada frame, sem piscar.
- **Cartões de métricas**: objetos, FPS (verde, amarelo ou vermelho conforme
  a fluidez) e tempo de cada análise.
- **Estado vazio**: com a câmera desligada, o app diz o que fazer em seguida e
  mostra os atalhos.
- **Atalhos de teclado**: `Espaço` inicia/para, `F` salva foto, `M` espelha.
- **Tooltips** explicando botões, confiança e métricas.
- **Espelhar imagem** (modo selfie), ligado por padrão.
- **Avisos tipo "toast"** flutuando sobre o vídeo, que somem sozinhos.
- O seletor de câmera fica bloqueado enquanto a câmera está ligada.
- **Escala de tela (DPI)**: a função `px()` ajusta medidas para 125%, 150% e
  200%, e as etiquetas do vídeo têm tamanho proporcional à imagem.

## Testes

O plano de testes CT01–CT10 e o registro de execução estão em
[`evidencias/PLANO_DE_TESTES.md`](evidencias/PLANO_DE_TESTES.md).
Capturas de tela devem ser salvas na pasta `evidencias/`.

## Dificuldades

| Problema                              | Causa                                        | Solução                                           |
| ------------------------------------- | -------------------------------------------- | ------------------------------------------------- |
| `No module named 'cv2'`               | Programa aberto fora do ambiente virtual     | Abrir pelo `Iniciar.bat` ou selecionar o interpretador do ambiente |
| Programa não abre em outro computador | `.venv` copiado de outra máquina não funciona | Ambiente fora da pasta, criado pelo `Iniciar.bat` em cada PC |
| COCO não tem óculos, aliança, crachá… | Vocabulário fixo de 80 classes               | Trocar para YOLO-World (vocabulário por texto)    |
| Acentos não aparecem nas etiquetas    | Fonte do OpenCV é só ASCII                   | Desenhar com Pillow + fonte TrueType              |
| Mesma pessoa marcada Homem e Mulher   | NMS por classe                               | `agnostic_nms=True` no `predict()`                |
| Câmera demora a abrir no Windows      | Backend MSMF padrão                          | Usar `cv2.CAP_DSHOW`                              |
| Janela trava ao abrir                 | Modelo carregado no construtor               | Carregar em thread e checar com `after()`         |
| Layout cortado em tela com escala 200% | Tk aumenta as fontes, mas não os pixels      | Função `px()` com a escala lida via `winfo_fpixels` |
| Cor de um objeto mudava a cada execução | `hash()` de texto é aleatório por processo   | Cor fixa por categoria                            |
| "notebook" detectava caderno          | Em inglês, *notebook* = caderno              | Prompts `laptop` → Notebook e `spiral notebook` → Caderno |
| Vídeo "travado" em ~5 FPS             | `predict()` no mesmo fluxo da exibição       | Thread de detecção + `imgsz=480`                  |

## Conclusão

Explique o que o grupo aprendeu sobre captura de vídeo, inferência com modelo
pré-treinado, vocabulário aberto, conversão de cores, loop de eventos e
organização em módulos.
