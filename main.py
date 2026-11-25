"""
Trabalho SOFT B — Reconhecimento de objetos com IA
==================================================
Aplicação desktop que captura a webcam, executa o modelo YOLO-World em cada
frame e exibe o resultado anotado em uma interface Tkinter.

Pilha: Python + Ultralytics (YOLO-World) + OpenCV + Pillow + Tkinter

Módulos do projeto:
    modelo.py   -> vocabulário (categorias e nomes em português) e modelo
    desenho.py  -> desenho das caixas e etiquetas sobre o frame
    main.py     -> interface gráfica e controle da câmera (este arquivo)

Duas "linhas de trabalho" rodam ao mesmo tempo:
    thread principal (Tkinter)   webcam -> espelha -> BGR->RGB -> Pillow -> exibe
    thread de detecção           pega o frame mais recente -> modelo.predict
A detecção demora ~130 ms na CPU; se ela rodasse junto com a exibição, o
vídeo ficaria travado em ~7 FPS. Separando, o vídeo flui e as caixas se
atualizam no ritmo do modelo.
"""

import os
import sys
import time
import threading
from collections import Counter
from datetime import datetime

import tkinter as tk
from tkinter import messagebox

# Todos os caminhos do projeto (modelo, pasta weights/ do CLIP, capturas/) são
# relativos. Mudar para a pasta do script evita erro de "arquivo não
# encontrado" quando o programa é aberto a partir de outra pasta.
os.chdir(os.path.dirname(os.path.abspath(__file__)))

try:
    import cv2
    from PIL import Image, ImageTk
    from modelo import (
        CATEGORIAS, CLASSES, carregar_modelo, categoria_de, nome_em_portugues,
    )
    from desenho import cor_da_categoria, desenhar_deteccoes
except ImportError as erro:
    # Erro mais comum do projeto: programa aberto com um Python que não tem
    # as bibliotecas (fora do ambiente virtual).
    tk.Tk().withdraw()
    messagebox.showerror(
        "Dependência ausente",
        f"{erro}\n\nAbra o programa pelo arquivo Iniciar.bat: ele cria o "
        "ambiente e instala as bibliotecas sozinho.",
    )
    raise SystemExit(1)


# ----------------------------------------------------------------------------
# Configurações gerais
# ----------------------------------------------------------------------------
TITULO = "Trabalho SOFT B"
CONFIANCA_PADRAO = 0.25          # YOLO-World trabalha com confianças mais baixas
PASTA_CAPTURAS = "capturas"
INTERVALO_FRAME_MS = 10          # tempo entre uma atualização e a próxima
# Lado da imagem enviada ao modelo. 640 = mais preciso em objetos pequenos,
# porém mais lento (~190 ms); 320 = ~60 ms, mas perde detalhes. 480 equilibra.
TAMANHO_INFERENCIA = 480
LINHAS_LISTA = 8                 # quantas classes a lista lateral mostra

# Paleta do tema escuro — definida em um só lugar para manter consistência.
COR_FUNDO = "#0f1419"
COR_PAINEL = "#1a2029"
COR_PAINEL_2 = "#242c38"
COR_BORDA = "#2e3845"
COR_TEXTO = "#e6edf3"
COR_TEXTO_SUAVE = "#8b98a9"
COR_PRIMARIA = "#3b82f6"
COR_PRIMARIA_HOVER = "#2563eb"
COR_SUCESSO = "#22c55e"
COR_SUCESSO_ESCURO = "#166534"
COR_PERIGO = "#ef4444"
COR_PERIGO_HOVER = "#dc2626"
COR_ALERTA = "#f59e0b"

FONTE = "Segoe UI"

TEXTO_ATALHOS = "Espaço  iniciar/parar     F  salvar foto     M  espelhar"

# Escala da tela (1.0 = 100%, 1.5 = 150%, 2.0 = 200% no Windows). O Tkinter já
# aumenta as FONTES sozinho, mas medidas em pixels (largura do painel,
# espaçamentos, bolinhas) não. Sem isso, em telas com escala o texto cresce e
# não cabe mais nos espaços. Definida em Aplicacao.__init__.
ESCALA = 1.0


def px(valor):
    """Converte uma medida pensada para 100% na medida certa para esta tela."""
    return round(valor * ESCALA)


def interpolar_cor(cor_a, cor_b, t):
    """Retorna a cor intermediária entre cor_a (t=0) e cor_b (t=1).

    Usada pelas animações: em vez de trocar a cor de uma vez, a interface
    passa por alguns tons intermediários, o que dá a sensação de transição.
    """
    a = [int(cor_a[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(cor_b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(
        round(a[i] + (b[i] - a[i]) * t) for i in range(3)
    )


# ----------------------------------------------------------------------------
# Componentes visuais reutilizáveis
# ----------------------------------------------------------------------------
class Botao(tk.Button):
    """Botão plano que suaviza a troca de cor ao passar o mouse."""

    def __init__(self, pai, cor, cor_hover, **opcoes):
        super().__init__(
            pai,
            bg=cor,
            fg=COR_TEXTO,
            activebackground=cor_hover,
            activeforeground=COR_TEXTO,
            disabledforeground=COR_TEXTO_SUAVE,
            relief=tk.FLAT,
            bd=0,
            cursor="hand2",
            font=(FONTE, 11, "bold"),
            padx=px(22),
            pady=px(10),
            # Sem foco de teclado: senão a tecla Espaço "clicaria" o botão
            # focado E dispararia o atalho global ao mesmo tempo.
            takefocus=0,
            **opcoes,
        )
        self.cor = cor
        self.cor_hover = cor_hover
        self._animacao = None
        self.bind("<Enter>", lambda _: self._transicao(self.cor_hover))
        self.bind("<Leave>", lambda _: self._transicao(self.cor))

    def _transicao(self, destino, passos=6, intervalo_ms=16):
        if self["state"] == tk.DISABLED:
            return
        if self._animacao is not None:
            self.after_cancel(self._animacao)
        origem = self["bg"]

        def passo(i):
            if self["state"] == tk.DISABLED:
                return
            self.configure(bg=interpolar_cor(origem, destino, i / passos))
            if i < passos:
                self._animacao = self.after(intervalo_ms, passo, i + 1)

        passo(1)

    def definir_ativo(self, ativo):
        """Habilita/desabilita o botão e ajusta a aparência."""
        if ativo:
            self.configure(state=tk.NORMAL, bg=self.cor, cursor="hand2")
        else:
            self.configure(state=tk.DISABLED, bg=COR_PAINEL_2, cursor="arrow")


class Dica:
    """Tooltip: caixinha de ajuda que aparece ao parar o mouse sobre um widget.

    Mostra atalhos e explicações só quando o usuário procura por eles, sem
    poluir a tela com texto o tempo todo.
    """

    ATRASO_MS = 500

    def __init__(self, widget, texto):
        self.widget = widget
        self.texto = texto
        self._agendado = None
        self._caixa = None
        # O widget e seus filhos (ex.: o texto dentro de um chip) contam como
        # a mesma área para o tooltip.
        self._alvos = [widget, *widget.winfo_children()]
        for alvo in self._alvos:
            alvo.bind("<Enter>", self._agendar, add="+")
            alvo.bind("<Leave>", self._ao_sair, add="+")
            alvo.bind("<ButtonPress>", self._esconder, add="+")

    def _agendar(self, _evento=None):
        if self._caixa is None and self._agendado is None:
            self._agendado = self.widget.after(self.ATRASO_MS, self._mostrar)

    def _ao_sair(self, _evento=None):
        x, y = self.widget.winfo_pointerxy()
        if self.widget.winfo_containing(x, y) in self._alvos:
            return          # só passou da borda para um filho; continua dentro
        self._esconder()

    def _mostrar(self):
        self._agendado = None
        caixa = tk.Toplevel(self.widget)
        caixa.wm_overrideredirect(True)          # sem barra de título
        caixa.attributes("-topmost", True)
        caixa.configure(bg=COR_BORDA)
        tk.Label(
            caixa, text=self.texto, font=(FONTE, 9), bg=COR_PAINEL_2,
            fg=COR_TEXTO, justify=tk.LEFT, wraplength=px(320), padx=px(10), pady=px(6),
        ).pack(padx=1, pady=1)                   # 1 px de "borda"
        caixa.update_idletasks()

        # Abaixo do widget; se não couber na tela, acima dele.
        x = self.widget.winfo_rootx()
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + px(6)
        x = min(x, caixa.winfo_screenwidth() - caixa.winfo_reqwidth() - 8)
        if y + caixa.winfo_reqheight() > caixa.winfo_screenheight() - 48:
            y = self.widget.winfo_rooty() - caixa.winfo_reqheight() - 6
        caixa.wm_geometry(f"+{x}+{y}")
        self._caixa = caixa

    def _esconder(self, _evento=None):
        if self._agendado is not None:
            self.widget.after_cancel(self._agendado)
            self._agendado = None
        if self._caixa is not None:
            self._caixa.destroy()
            self._caixa = None


class Chip(tk.Frame):
    """Botão liga/desliga em formato de 'pílula', usado no filtro de categorias.

    Ligado: fundo destacado, borda e bolinha na cor da categoria.
    Desligado: apagado (cinza), para ficar claro que não será detectado.
    """

    def __init__(self, pai, texto, cor, ao_mudar):
        super().__init__(pai, highlightthickness=1, padx=px(10), pady=px(5),
                         cursor="hand2")
        self.cor = cor
        self.ativo = True
        self.ao_mudar = ao_mudar
        self._mouse_em_cima = False

        self.bolinha = tk.Canvas(self, width=px(10), height=px(10),
                                 highlightthickness=0, bd=0, cursor="hand2")
        self.bolinha.pack(side=tk.LEFT, padx=(0, px(6)))
        self.oval = self.bolinha.create_oval(1, 1, px(9), px(9), outline="")

        self.rotulo = tk.Label(self, text=texto, font=(FONTE, 10, "bold"),
                               cursor="hand2")
        self.rotulo.pack(side=tk.LEFT)

        for parte in (self, self.bolinha, self.rotulo):
            parte.bind("<Button-1>", self._clicar)
            parte.bind("<Enter>", lambda _: self._hover(True))
            parte.bind("<Leave>", lambda _: self._hover(False))
        self._pintar()

    def _clicar(self, _evento=None):
        self.definir(not self.ativo)
        self.ao_mudar()

    def _hover(self, dentro):
        self._mouse_em_cima = dentro
        self._pintar()

    def definir(self, ativo):
        self.ativo = ativo
        self._pintar()

    def _pintar(self):
        if self.ativo:
            fundo = COR_BORDA if self._mouse_em_cima else COR_PAINEL_2
            borda, bolinha, texto = self.cor, self.cor, COR_TEXTO
        else:
            fundo = COR_PAINEL if self._mouse_em_cima else COR_FUNDO
            borda, bolinha, texto = COR_BORDA, COR_BORDA, COR_TEXTO_SUAVE
        self.configure(bg=fundo, highlightbackground=borda, highlightcolor=borda)
        self.bolinha.configure(bg=fundo)
        self.bolinha.itemconfigure(self.oval, fill=bolinha)
        self.rotulo.configure(bg=fundo, fg=texto)


# ----------------------------------------------------------------------------
# Aplicação
# ----------------------------------------------------------------------------
class Aplicacao:
    """Centraliza o estado (janela, modelo, câmera) e o comportamento da app."""

    def __init__(self, janela):
        global ESCALA
        # 96 pixels por polegada = 100% no Windows.
        ESCALA = max(janela.winfo_fpixels("1i") / 96, 1.0)

        self.janela = janela
        self.janela.title(TITULO)
        self.janela.configure(bg=COR_FUNDO)
        self.janela.protocol("WM_DELETE_WINDOW", self.fechar)
        self._centralizar(px(1240), px(800))
        self.janela.minsize(
            min(px(1100), self.janela.winfo_screenwidth() - 40),
            min(px(660), self.janela.winfo_screenheight() - 90),
        )

        # --- Estado da aplicação -------------------------------------------
        self.modelo = None              # objeto YOLO (carregado em 2º plano)
        self.erro_modelo = None         # exceção ocorrida ao carregar
        self.mensagem_carregamento = "Carregando modelo"
        self.camera = None              # objeto cv2.VideoCapture
        self.camera_ativa = False       # estado lógico da captura (RF08/RF09)
        self.encerrando = False
        self.ultima_imagem = None       # último frame anotado (para salvar foto)
        self.ultimo_tempo = None
        self.fps = 0.0
        self.pulso = 0
        self._aviso_timer = None

        # --- Dados compartilhados com a thread de detecção -----------------
        # A trava garante que as duas threads não leiam/escrevam ao mesmo tempo.
        self.trava = threading.Lock()
        self.frame_para_detectar = None # frame mais recente (BGR, tamanho original)
        self.deteccoes_atuais = []      # último resultado publicado pela thread
        self.tempo_deteccao = 0.0       # duração do último predict, em segundos
        self.thread_deteccao = None
        # Variáveis do Tkinter (DoubleVar etc.) só podem ser lidas na thread
        # principal; a thread de detecção usa estas cópias simples.
        self.confianca_atual = CONFIANCA_PADRAO
        # Índices das classes que o predict deve considerar.
        # None = todas; [] = nenhuma categoria selecionada.
        self.classes_filtro = None

        self.confianca = tk.DoubleVar(value=CONFIANCA_PADRAO)
        self.indice_camera = tk.IntVar(value=0)
        self.espelhar = tk.BooleanVar(value=True)   # "modo selfie"

        self._construir_interface()
        self._configurar_atalhos()
        self._animar_abertura()

        # O modelo demora alguns segundos para carregar (e baixa na 1ª vez).
        # Carregar em outra thread mantém a janela respondendo (RF10).
        threading.Thread(target=self._carregar_modelo, daemon=True).start()
        self._aguardar_modelo()

    # ------------------------------------------------------------------------
    # Construção da interface
    # ------------------------------------------------------------------------
    def _centralizar(self, largura, altura):
        tela_largura = self.janela.winfo_screenwidth()
        tela_altura = self.janela.winfo_screenheight()
        # Em telas pequenas (ex.: notebook 1366x768) a janela se adapta.
        largura = min(largura, tela_largura - 40)
        altura = min(altura, tela_altura - 90)
        x = (tela_largura - largura) // 2
        y = max((tela_altura - altura) // 2 - 24, 0)
        self.janela.geometry(f"{largura}x{altura}+{x}+{y}")

    def _construir_interface(self):
        # A ordem importa: o rodapé é empacotado antes do corpo para nunca ser
        # "espremido" para fora da janela quando ela fica pequena.
        self._construir_cabecalho()
        self._construir_filtros()
        self._construir_rodape()
        self._construir_corpo()

    def _construir_cabecalho(self):
        cabecalho = tk.Frame(self.janela, bg=COR_FUNDO)
        cabecalho.pack(fill=tk.X, padx=px(28), pady=(px(20), px(10)))

        titulos = tk.Frame(cabecalho, bg=COR_FUNDO)
        titulos.pack(side=tk.LEFT)
        tk.Label(
            titulos, text=TITULO, font=(FONTE, 22, "bold"),
            bg=COR_FUNDO, fg=COR_TEXTO,
        ).pack(anchor="w")
        tk.Label(
            titulos,
            text=f"Reconhecimento de objetos com IA  ·  {len(CLASSES)} tipos "
                 f"de objeto em {len(CATEGORIAS)} categorias",
            font=(FONTE, 10), bg=COR_FUNDO, fg=COR_TEXTO_SUAVE,
        ).pack(anchor="w")

        # "Pílula" de status: bolinha colorida + texto (RF08)
        pilula = tk.Frame(cabecalho, bg=COR_PAINEL, padx=px(14), pady=px(7))
        pilula.pack(side=tk.RIGHT)

        self.ponto_status = tk.Canvas(
            pilula, width=px(12), height=px(12), bg=COR_PAINEL,
            highlightthickness=0,
        )
        self.ponto_status.pack(side=tk.LEFT, padx=(0, px(8)))
        self.ponto = self.ponto_status.create_oval(
            px(2), px(2), px(10), px(10), fill=COR_ALERTA, outline=""
        )

        self.texto_status = tk.Label(
            pilula, text="Carregando modelo", font=(FONTE, 10, "bold"),
            bg=COR_PAINEL, fg=COR_TEXTO,
        )
        self.texto_status.pack(side=tk.LEFT)

    def _construir_filtros(self):
        """Barra 'Detectar': um chip liga/desliga por categoria do vocabulário."""
        barra = tk.Frame(self.janela, bg=COR_FUNDO)
        barra.pack(fill=tk.X, padx=px(28), pady=(0, px(12)))

        tk.Label(
            barra, text="DETECTAR", font=(FONTE, 9, "bold"),
            bg=COR_FUNDO, fg=COR_TEXTO_SUAVE,
        ).pack(side=tk.LEFT, padx=(0, px(10)))

        self.chips = {}
        for categoria, itens in CATEGORIAS.items():
            chip = Chip(barra, categoria, cor_da_categoria(categoria),
                        self._ao_mudar_filtro)
            chip.pack(side=tk.LEFT, padx=(0, px(6)))
            # O tooltip lista os itens: o usuário descobre o que o app
            # reconhece sem precisar abrir o código.
            nomes = ", ".join(itens.values())
            Dica(chip, f"{categoria} ({len(itens)} itens):\n{nomes}")
            self.chips[categoria] = chip

        self.botao_todas = tk.Label(
            barra, text="Limpar seleção", font=(FONTE, 9, "underline"),
            bg=COR_FUNDO, fg=COR_PRIMARIA, cursor="hand2",
        )
        self.botao_todas.pack(side=tk.RIGHT)
        self.botao_todas.bind("<Button-1>", self._alternar_todas)

    def _construir_corpo(self):
        corpo = tk.Frame(self.janela, bg=COR_FUNDO)
        corpo.pack(fill=tk.BOTH, expand=True, padx=px(28))

        # Área do vídeo ------------------------------------------------------
        self.quadro_video = tk.Frame(
            corpo, bg=COR_PAINEL,
            highlightbackground=COR_BORDA, highlightthickness=1,
        )
        self.quadro_video.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.area_imagem = tk.Label(self.quadro_video, bg=COR_PAINEL)
        self.area_imagem.pack(fill=tk.BOTH, expand=True)

        self._construir_estado_vazio()

        # "Toast": mensagem curta e não bloqueante (ex.: "Foto salva em ...")
        # que flutua na base do vídeo e some sozinha.
        self.aviso = tk.Label(
            self.quadro_video, text="", font=(FONTE, 10), bg=COR_PAINEL_2,
            fg=COR_TEXTO, padx=px(14), pady=px(8),
        )

        # Painel lateral -----------------------------------------------------
        painel = tk.Frame(
            corpo, bg=COR_PAINEL, width=px(300),
            highlightbackground=COR_BORDA, highlightthickness=1,
        )
        painel.pack(side=tk.RIGHT, fill=tk.Y, padx=(px(18), 0))
        painel.pack_propagate(False)

        # Configurações vão para a base do painel ANTES do resto: se faltar
        # altura, quem encolhe é a lista de classes, nunca os controles.
        self._construir_configuracoes(painel)

        self._titulo_secao(painel, "Agora")
        blocos = tk.Frame(painel, bg=COR_PAINEL)
        blocos.pack(fill=tk.X, padx=px(18))
        blocos.columnconfigure((0, 1, 2), weight=1, uniform="bloco")
        self.valor_objetos = self._bloco_metrica(
            blocos, "objetos", 0, "Quantos objetos aparecem no quadro atual.")
        self.valor_fps = self._bloco_metrica(
            blocos, "FPS", 1,
            "Quadros por segundo exibidos.\n"
            "Verde: fluido  ·  Amarelo: aceitável  ·  Vermelho: lento")
        self.valor_inferencia = self._bloco_metrica(
            blocos, "ms/análise", 2,
            "Tempo que o modelo leva para analisar um quadro.\n"
            "Quanto menor, mais rápido as caixas acompanham o movimento.")

        self._titulo_secao(painel, "Classes detectadas")
        self._construir_lista_classes(painel)

    def _construir_estado_vazio(self):
        """Mensagem centralizada exibida enquanto a câmera está desligada.

        Um bom "estado vazio" diz o que está acontecendo e qual é o próximo
        passo, em vez de deixar só um retângulo escuro.
        """
        self.estado_vazio = tk.Frame(self.quadro_video, bg=COR_PAINEL)
        tk.Label(
            self.estado_vazio, text="◎", font=(FONTE, 44),
            bg=COR_PAINEL, fg=COR_BORDA,
        ).pack()
        self.titulo_vazio = tk.Label(
            self.estado_vazio, text="Preparando o modelo de IA",
            font=(FONTE, 16, "bold"), bg=COR_PAINEL, fg=COR_TEXTO,
        )
        self.titulo_vazio.pack(pady=px(4))
        self.subtitulo_vazio = tk.Label(
            self.estado_vazio,
            text="Na primeira execução isso pode levar alguns segundos.",
            font=(FONTE, 11), bg=COR_PAINEL, fg=COR_TEXTO_SUAVE,
        )
        self.subtitulo_vazio.pack()
        tk.Label(
            self.estado_vazio, text=TEXTO_ATALHOS, font=(FONTE, 9),
            bg=COR_PAINEL_2, fg=COR_TEXTO_SUAVE, padx=px(12), pady=px(6),
        ).pack(pady=(px(22), 0))
        self.estado_vazio.place(relx=0.5, rely=0.5, anchor="center")

    def _construir_lista_classes(self, painel):
        """Lista com bolinha de cor (= cor da caixa no vídeo) e quantidade.

        As linhas são criadas uma única vez e só têm o texto trocado a cada
        frame — recriar widgets 20 vezes por segundo deixaria a tela piscando.
        """
        tk.Label(
            painel,
            text="Homem/Mulher é uma estimativa visual do modelo e pode errar.",
            font=(FONTE, 8), bg=COR_PAINEL, fg=COR_TEXTO_SUAVE,
            wraplength=px(260), justify=tk.LEFT,
        ).pack(side=tk.BOTTOM, anchor="w", padx=px(18), pady=(px(6), 0))

        caixa = tk.Frame(painel, bg=COR_PAINEL)
        caixa.pack(fill=tk.BOTH, expand=True, padx=px(18))

        self.linhas_classes = []
        for _ in range(LINHAS_LISTA):
            linha = tk.Frame(caixa, bg=COR_PAINEL)
            linha.pack(fill=tk.X, pady=(0, px(3)))
            bolinha = tk.Canvas(linha, width=px(10), height=px(10),
                                bg=COR_PAINEL, highlightthickness=0)
            bolinha.pack(side=tk.LEFT, padx=(px(12), px(8)), pady=px(7))
            oval = bolinha.create_oval(1, 1, px(9), px(9), outline="",
                                       state="hidden")
            nome = tk.Label(linha, text="", font=(FONTE, 10), bg=COR_PAINEL,
                            fg=COR_TEXTO, anchor="w")
            nome.pack(side=tk.LEFT, fill=tk.X, expand=True)
            qtd = tk.Label(linha, text="", font=(FONTE, 10, "bold"),
                           bg=COR_PAINEL, fg=COR_TEXTO)
            qtd.pack(side=tk.RIGHT, padx=px(12))
            self.linhas_classes.append((linha, bolinha, oval, nome, qtd))

        self._mostrar_lista_vazia("A lista aparece quando a câmera ligar.")

    def _construir_configuracoes(self, painel):
        secao = tk.Frame(painel, bg=COR_PAINEL)
        secao.pack(side=tk.BOTTOM, fill=tk.X, pady=(0, px(16)))
        self._titulo_secao(secao, "Configurações")

        # Confiança mínima -------------------------------------------------
        linha_conf = tk.Frame(secao, bg=COR_PAINEL)
        linha_conf.pack(fill=tk.X, padx=px(18))
        rotulo_conf = tk.Label(
            linha_conf, text="Confiança mínima  ⓘ", font=(FONTE, 10),
            bg=COR_PAINEL, fg=COR_TEXTO_SUAVE,
        )
        rotulo_conf.pack(side=tk.LEFT)
        Dica(rotulo_conf,
             "Abaixo deste valor a detecção é descartada.\n"
             "Mais baixo: aparecem mais objetos (e mais erros).\n"
             "Mais alto: só aparece o que o modelo tem certeza.")
        self.valor_confianca = tk.Label(
            linha_conf, text=f"{CONFIANCA_PADRAO:.0%}",
            font=(FONTE, 10, "bold"), bg=COR_PAINEL, fg=COR_PRIMARIA,
        )
        self.valor_confianca.pack(side=tk.RIGHT)

        tk.Scale(
            secao, from_=0.05, to=0.90, resolution=0.05,
            orient=tk.HORIZONTAL, variable=self.confianca,
            command=self._ao_mudar_confianca, showvalue=0,
            # No Scale, "bg" é a cor do marcador que o usuário arrasta.
            bg=COR_PRIMARIA, troughcolor=COR_PAINEL_2,
            activebackground=COR_PRIMARIA_HOVER, highlightthickness=0, bd=0,
            sliderrelief=tk.FLAT, sliderlength=px(18), width=px(14),
            takefocus=0,
        ).pack(fill=tk.X, padx=px(18), pady=(px(2), px(10)))

        # Índice da câmera -------------------------------------------------
        linha_cam = tk.Frame(secao, bg=COR_PAINEL)
        linha_cam.pack(fill=tk.X, padx=px(18), pady=(0, px(8)))
        tk.Label(
            linha_cam, text="Câmera", font=(FONTE, 10),
            bg=COR_PAINEL, fg=COR_TEXTO_SUAVE,
        ).pack(side=tk.LEFT)
        self.seletor_camera = tk.Spinbox(
            linha_cam, from_=0, to=5, textvariable=self.indice_camera,
            width=4, font=(FONTE, 10, "bold"), bg=COR_PAINEL_2, fg=COR_TEXTO,
            buttonbackground=COR_PAINEL_2, insertbackground=COR_TEXTO,
            readonlybackground=COR_PAINEL_2,
            disabledbackground=COR_PAINEL, disabledforeground=COR_TEXTO_SUAVE,
            relief=tk.FLAT, bd=0, justify=tk.CENTER, state="readonly",
        )
        self.seletor_camera.pack(side=tk.RIGHT)
        Dica(self.seletor_camera,
             "0 = webcam principal. Use 1, 2... para câmeras externas.\n"
             "Só pode ser trocada com a câmera parada.")

        # Espelhar ---------------------------------------------------------
        tk.Checkbutton(
            secao, text="Espelhar imagem (modo selfie)", variable=self.espelhar,
            font=(FONTE, 10), bg=COR_PAINEL, fg=COR_TEXTO_SUAVE,
            activebackground=COR_PAINEL, activeforeground=COR_TEXTO,
            selectcolor=COR_PAINEL_2, highlightthickness=0, bd=0,
            cursor="hand2", takefocus=0,
        ).pack(anchor="w", padx=px(14))

    def _construir_rodape(self):
        rodape = tk.Frame(self.janela, bg=COR_FUNDO)
        rodape.pack(side=tk.BOTTOM, fill=tk.X, padx=px(28), pady=px(16))

        self.botao_iniciar = Botao(
            rodape, COR_PRIMARIA, COR_PRIMARIA_HOVER,
            text="▶  INICIAR CÂMERA", command=self.iniciar_camera,
        )
        self.botao_iniciar.pack(side=tk.LEFT)
        Dica(self.botao_iniciar,
             "Liga a webcam e começa a detecção.\nAtalho: Espaço")

        self.botao_parar = Botao(
            rodape, COR_PAINEL_2, COR_BORDA,
            text="■  PARAR CÂMERA", command=self.parar_camera,
        )
        self.botao_parar.pack(side=tk.LEFT, padx=(px(12), 0))
        Dica(self.botao_parar, "Desliga e libera a webcam.\nAtalho: Espaço")

        self.botao_foto = Botao(
            rodape, COR_PAINEL_2, COR_BORDA,
            text="◉  SALVAR FOTO", command=self.salvar_foto,
        )
        self.botao_foto.pack(side=tk.LEFT, padx=(px(12), 0))
        Dica(self.botao_foto,
             f"Salva o quadro atual, com as caixas, em {PASTA_CAPTURAS}/.\n"
             "Atalho: F")

        self.botao_sair = Botao(
            rodape, COR_PERIGO, COR_PERIGO_HOVER,
            text="SAIR", command=self.fechar,
        )
        self.botao_sair.pack(side=tk.RIGHT)

        # Até o modelo carregar nenhum botão de câmera faz sentido.
        self.botao_iniciar.definir_ativo(False)
        self.botao_parar.definir_ativo(False)
        self.botao_foto.definir_ativo(False)

    def _titulo_secao(self, pai, titulo):
        tk.Label(
            pai, text=titulo.upper(), font=(FONTE, 9, "bold"),
            bg=COR_PAINEL, fg=COR_TEXTO_SUAVE,
        ).pack(anchor="w", padx=px(18), pady=(px(16), px(6)))

    def _bloco_metrica(self, pai, legenda, coluna, dica):
        """Cria um 'cartão' com número grande + legenda; devolve o Label do número."""
        bloco = tk.Frame(pai, bg=COR_PAINEL_2, padx=px(10), pady=px(8))
        bloco.grid(row=0, column=coluna, sticky="nsew",
                   padx=(0 if coluna == 0 else px(3), 0 if coluna == 2 else px(3)))
        valor = tk.Label(bloco, text="—", font=(FONTE, 18, "bold"),
                         bg=COR_PAINEL_2, fg=COR_TEXTO)
        valor.pack(anchor="w")
        tk.Label(bloco, text=legenda, font=(FONTE, 8),
                 bg=COR_PAINEL_2, fg=COR_TEXTO_SUAVE).pack(anchor="w")
        Dica(bloco, dica)
        return valor

    # ------------------------------------------------------------------------
    # Atalhos de teclado
    # ------------------------------------------------------------------------
    def _configurar_atalhos(self):
        # bind na janela principal recebe as teclas de todos os widgets dela.
        self.janela.bind("<KeyPress-space>", self._atalho_iniciar_parar)
        for tecla in ("f", "F"):
            self.janela.bind(f"<KeyPress-{tecla}>", lambda _: self.salvar_foto())
        for tecla in ("m", "M"):
            self.janela.bind(f"<KeyPress-{tecla}>", self._atalho_espelhar)

    def _atalho_iniciar_parar(self, _evento=None):
        if self.camera_ativa:
            self.parar_camera()
        else:
            self.iniciar_camera()

    def _atalho_espelhar(self, _evento=None):
        self.espelhar.set(not self.espelhar.get())
        estado = "ligado" if self.espelhar.get() else "desligado"
        self.mostrar_aviso(f"Espelhamento {estado}")

    # ------------------------------------------------------------------------
    # Filtro de categorias
    # ------------------------------------------------------------------------
    def _ao_mudar_filtro(self):
        ativas = [cat for cat, chip in self.chips.items() if chip.ativo]
        todas = len(ativas) == len(self.chips)
        self.botao_todas.configure(
            text="Limpar seleção" if todas else "Selecionar todas"
        )
        self._recalcular_filtro()
        if not ativas:
            self.mostrar_aviso("Nenhuma categoria selecionada — nada será detectado.")

    def _alternar_todas(self, _evento=None):
        todas = all(chip.ativo for chip in self.chips.values())
        for chip in self.chips.values():
            chip.definir(not todas)
        self._ao_mudar_filtro()

    def _recalcular_filtro(self):
        """Traduz as categorias ligadas na lista de índices usada pelo predict.

        A atribuição de self.classes_filtro troca a lista inteira de uma vez,
        então a thread de detecção sempre lê uma lista completa e coerente.
        """
        if self.modelo is None:
            return
        ativas = {cat for cat, chip in self.chips.items() if chip.ativo}
        if len(ativas) == len(self.chips):
            self.classes_filtro = None          # todas: sem filtro
        else:
            self.classes_filtro = [
                indice for indice, prompt in self.modelo.names.items()
                if categoria_de(prompt) in ativas
            ]

    # ------------------------------------------------------------------------
    # Carregamento do modelo
    # ------------------------------------------------------------------------
    def _carregar_modelo(self):
        """Executa em outra thread. Só grava o resultado; a UI lê depois."""
        try:
            self.modelo = carregar_modelo(progresso=self._registrar_progresso)
        except Exception as erro:
            self.erro_modelo = erro

    def _registrar_progresso(self, mensagem):
        # Chamado pela thread de carregamento; a UI mostra em _aguardar_modelo.
        self.mensagem_carregamento = mensagem.rstrip(".")

    def _aguardar_modelo(self, passo=0):
        """Verifica a cada 300 ms se o modelo terminou de carregar."""
        if self.encerrando:
            return

        if self.erro_modelo is not None:
            messagebox.showerror(
                "Erro",
                f"Não foi possível carregar o modelo:\n{self.erro_modelo}",
            )
            self.fechar()
            return

        if self.modelo is not None:
            self._recalcular_filtro()
            self._definir_status("Câmera desligada", COR_TEXTO_SUAVE)
            self._mostrar_estado_vazio()
            self.botao_iniciar.definir_ativo(True)
            self.mostrar_aviso("Modelo carregado. Pronto para iniciar.")
            return

        pontos = "." * (passo % 4)
        self.texto_status.configure(text=f"{self.mensagem_carregamento}{pontos}")
        self.janela.after(300, self._aguardar_modelo, passo + 1)

    # ------------------------------------------------------------------------
    # Câmera (thread principal)
    # ------------------------------------------------------------------------
    def iniciar_camera(self):
        # Evita abertura duplicada (RF09) e uso sem modelo carregado.
        if self.camera_ativa or self.modelo is None:
            return

        indice = self.indice_camera.get()
        self._definir_status("Abrindo câmera…", COR_ALERTA)
        self.janela.update_idletasks()      # mostra o status antes de esperar

        # No Windows o backend DirectShow abre a câmera bem mais rápido.
        backend = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY
        camera = cv2.VideoCapture(indice, backend)

        if not camera.isOpened():
            camera.release()
            self._definir_status("Câmera desligada", COR_TEXTO_SUAVE)
            messagebox.showerror(
                "Erro",
                f"Não foi possível acessar a câmera {indice}.\n\n"
                "Verifique as permissões do Windows, feche outros programas\n"
                "que usam a webcam ou tente outro número de câmera.",
            )
            return

        self.camera = camera
        self.camera_ativa = True
        self.ultimo_tempo = time.perf_counter()
        self.fps = 0.0

        # Liga a thread que executa o modelo sem travar a interface.
        self.thread_deteccao = threading.Thread(
            target=self._detectar_em_segundo_plano, daemon=True
        )
        self.thread_deteccao.start()

        self.estado_vazio.place_forget()
        self._definir_status("Câmera ativa", COR_SUCESSO)
        self.botao_iniciar.definir_ativo(False)
        self.botao_parar.definir_ativo(True)
        self.botao_foto.definir_ativo(True)
        self.seletor_camera.configure(state="disabled")

        self._pulsar_status()
        self.atualizar_video()

    def atualizar_video(self):
        """Exibe um frame e agenda o próximo com after() (sem while True).

        Esta função nunca espera o modelo: ela entrega o frame novo para a
        thread de detecção e desenha as detecções mais recentes disponíveis.
        """
        if not self.camera_ativa:
            return

        sucesso, frame = self.camera.read()

        if not sucesso:
            messagebox.showerror("Erro", "Não foi possível capturar a imagem.")
            self.parar_camera()
            return

        # Espelha ANTES de entregar à thread: o modelo analisa a mesma imagem
        # que aparece na tela, então as caixas já saem na posição certa.
        if self.espelhar.get():
            frame = cv2.flip(frame, 1)

        with self.trava:
            self.frame_para_detectar = frame
            deteccoes = self.deteccoes_atuais
            tempo_deteccao = self.tempo_deteccao

        # OpenCV entrega BGR; Pillow/Tkinter esperam RGB.
        imagem = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        imagem, escala = self._ajustar_tamanho(imagem)

        deteccoes_na_tela = self._escalar_deteccoes(deteccoes, escala)
        self.ultima_imagem = desenhar_deteccoes(imagem, deteccoes_na_tela)

        imagem_tk = ImageTk.PhotoImage(self.ultima_imagem)
        self.area_imagem.configure(image=imagem_tk)
        self.area_imagem.image = imagem_tk       # mantém referência viva

        self._atualizar_estatisticas(deteccoes_na_tela, tempo_deteccao)
        self._atualizar_fps()

        self.janela.after(INTERVALO_FRAME_MS, self.atualizar_video)

    def parar_camera(self):
        self.camera_ativa = False

        # Espera a thread terminar o predict em andamento (no máximo ~0,2 s)
        # para não sobrar uma thread antiga rodando se a câmera for religada.
        if self.thread_deteccao is not None:
            self.thread_deteccao.join(timeout=2.0)
            self.thread_deteccao = None

        with self.trava:
            self.frame_para_detectar = None
            self.deteccoes_atuais = []
            self.tempo_deteccao = 0.0

        if self.camera is not None:
            self.camera.release()               # libera a webcam (RNF07)
            self.camera = None

        self.ultima_imagem = None
        self.area_imagem.configure(image="")
        self.area_imagem.image = None

        self.valor_fps.configure(text="—", fg=COR_TEXTO)
        self.valor_inferencia.configure(text="—")
        self.valor_objetos.configure(text="—")
        self._mostrar_lista_vazia("A lista aparece quando a câmera ligar.")

        self._definir_status("Câmera desligada", COR_TEXTO_SUAVE)
        if self.modelo is not None:
            self._mostrar_estado_vazio()
        self.botao_iniciar.definir_ativo(self.modelo is not None)
        self.botao_parar.definir_ativo(False)
        self.botao_foto.definir_ativo(False)
        self.seletor_camera.configure(state="readonly")

    def salvar_foto(self):
        if self.ultima_imagem is None:
            self.mostrar_aviso("Inicie a câmera antes de salvar uma foto.")
            return

        os.makedirs(PASTA_CAPTURAS, exist_ok=True)
        nome = datetime.now().strftime("captura_%Y-%m-%d_%H-%M-%S.jpg")
        caminho = os.path.join(PASTA_CAPTURAS, nome)

        try:
            self.ultima_imagem.save(caminho, quality=92)
        except OSError as erro:
            messagebox.showerror("Erro", f"Não foi possível salvar a foto:\n{erro}")
            return

        self._piscar_borda()
        self.mostrar_aviso(f"Foto salva em {caminho}")

    def fechar(self):
        if self.encerrando:
            return
        self.encerrando = True
        self.parar_camera()
        self.janela.destroy()

    # ------------------------------------------------------------------------
    # Detecção (thread separada)
    # ------------------------------------------------------------------------
    def _detectar_em_segundo_plano(self):
        """Laço da thread de detecção.

        Enquanto a câmera estiver ativa: pega o frame mais recente, roda o
        modelo e publica as detecções. Frames que chegam durante um predict
        são simplesmente pulados — sempre processamos o mais novo.
        """
        frame_anterior = None
        while self.camera_ativa:
            with self.trava:
                frame = self.frame_para_detectar
            if frame is None or frame is frame_anterior:
                time.sleep(0.005)               # nada novo ainda
                continue
            frame_anterior = frame

            classes = self.classes_filtro       # cópia local: lida uma vez só
            inicio = time.perf_counter()
            if classes == []:
                deteccoes = []                  # nenhuma categoria: nem roda a IA
            else:
                # agnostic_nms: uma pessoa não pode ser "Homem" e "Mulher" ao
                # mesmo tempo — fica só a caixa de maior confiança na região.
                # classes: só considera as categorias ligadas na barra.
                resultados = self.modelo.predict(
                    source=frame,
                    imgsz=TAMANHO_INFERENCIA,
                    conf=self.confianca_atual,
                    iou=0.5,
                    agnostic_nms=True,
                    classes=classes,
                    max_det=30,
                    verbose=False,
                )
                deteccoes = self._extrair_deteccoes(resultados[0].boxes)
            duracao = time.perf_counter() - inicio

            with self.trava:
                self.deteccoes_atuais = deteccoes
                self.tempo_deteccao = duracao

    def _extrair_deteccoes(self, caixas):
        """Converte as caixas do YOLO em dicionários com nome em português.

        As coordenadas ficam na escala do frame original; a thread principal
        as converte para o tamanho da tela em _escalar_deteccoes.
        """
        nomes = self.modelo.names
        deteccoes = []
        for (x1, y1, x2, y2), conf, classe in zip(
            caixas.xyxy.tolist(), caixas.conf.tolist(), caixas.cls.tolist()
        ):
            prompt = nomes[int(classe)]
            deteccoes.append({
                "caixa": (x1, y1, x2, y2),
                "nome": nome_em_portugues(prompt),
                "categoria": categoria_de(prompt),
                "confianca": conf,
            })
        return deteccoes

    # ------------------------------------------------------------------------
    # Auxiliares de exibição (thread principal)
    # ------------------------------------------------------------------------
    def _ajustar_tamanho(self, imagem):
        """Redimensiona para caber na área de vídeo; devolve (imagem, escala)."""
        largura = max(self.area_imagem.winfo_width(), 1)
        altura = max(self.area_imagem.winfo_height(), 1)
        escala = min(largura / imagem.width, altura / imagem.height)
        novo_tamanho = (
            max(1, int(imagem.width * escala)),
            max(1, int(imagem.height * escala)),
        )
        return imagem.resize(novo_tamanho, Image.BILINEAR), escala

    def _escalar_deteccoes(self, deteccoes, escala):
        return [
            {**det, "caixa": tuple(v * escala for v in det["caixa"])}
            for det in deteccoes
        ]

    def _mostrar_estado_vazio(self):
        self.titulo_vazio.configure(text="Câmera desligada")
        self.subtitulo_vazio.configure(
            text="Clique em INICIAR CÂMERA ou pressione Espaço para começar."
        )
        self.estado_vazio.place(relx=0.5, rely=0.5, anchor="center")

    def _pintar_linha(self, indice, nome="", qtd="", cor=None, fg=COR_TEXTO):
        """Preenche uma linha da lista; sem nome, a linha fica 'invisível'."""
        linha, bolinha, oval, rotulo_nome, rotulo_qtd = self.linhas_classes[indice]
        fundo = COR_PAINEL_2 if nome else COR_PAINEL
        linha.configure(bg=fundo)
        bolinha.configure(bg=fundo)
        bolinha.itemconfigure(oval, fill=cor or fundo,
                              state="normal" if cor else "hidden")
        rotulo_nome.configure(text=nome, bg=fundo, fg=fg)
        rotulo_qtd.configure(text=qtd, bg=fundo)

    def _mostrar_lista_vazia(self, mensagem):
        self._pintar_linha(0, mensagem, fg=COR_TEXTO_SUAVE)
        for i in range(1, LINHAS_LISTA):
            self._pintar_linha(i)

    def _atualizar_estatisticas(self, deteccoes, tempo_deteccao):
        self.valor_objetos.configure(text=str(len(deteccoes)))
        self.valor_inferencia.configure(
            text=f"{tempo_deteccao * 1000:.0f}" if tempo_deteccao else "—"
        )

        if self.classes_filtro == []:
            self._mostrar_lista_vazia("Nenhuma categoria selecionada.")
            return

        contagem = Counter((det["nome"], det["categoria"]) for det in deteccoes)
        if not contagem:
            self._mostrar_lista_vazia("Nenhum objeto detectado.")
            return

        # Mais frequentes primeiro; empate em ordem alfabética (a lista fica
        # estável e não troca de posição a cada frame).
        itens = sorted(contagem.items(), key=lambda par: (-par[1], par[0][0]))
        if len(itens) > LINHAS_LISTA:
            sobra = itens[LINHAS_LISTA - 1:]
            itens = itens[:LINHAS_LISTA - 1]
            itens.append(((f"+ {len(sobra)} outros", None),
                          sum(qtd for _, qtd in sobra)))

        for i in range(LINHAS_LISTA):
            if i < len(itens):
                (nome, categoria), qtd = itens[i]
                cor = cor_da_categoria(categoria) if categoria else None
                self._pintar_linha(i, nome, f"×{qtd}", cor)
            else:
                self._pintar_linha(i)

    def _atualizar_fps(self):
        agora = time.perf_counter()
        instantaneo = 1.0 / max(agora - self.ultimo_tempo, 1e-6)
        self.ultimo_tempo = agora
        # Média móvel: evita que o número fique "pulando" na tela.
        self.fps = instantaneo if self.fps == 0 else self.fps * 0.9 + instantaneo * 0.1
        # Cor como "semáforo": verde = fluido, amarelo = ok, vermelho = lento.
        if self.fps >= 15:
            cor = COR_SUCESSO
        elif self.fps >= 8:
            cor = COR_ALERTA
        else:
            cor = COR_PERIGO
        self.valor_fps.configure(text=f"{self.fps:.0f}", fg=cor)

    def _ao_mudar_confianca(self, valor):
        # Variáveis do Tkinter não podem ser lidas por outra thread; por isso
        # guardamos uma cópia simples (float) que a thread de detecção usa.
        self.confianca_atual = float(valor)
        self.valor_confianca.configure(text=f"{self.confianca_atual:.0%}")

    def _definir_status(self, texto, cor):
        self.texto_status.configure(text=texto)
        self.ponto_status.itemconfigure(self.ponto, fill=cor)

    def mostrar_aviso(self, texto, duracao_ms=3000):
        """Mostra uma mensagem discreta no rodapé e a desvanece depois."""
        if self._aviso_timer is not None:
            self.janela.after_cancel(self._aviso_timer)
        self.aviso.configure(text=texto, fg=COR_TEXTO)
        self.aviso.place(relx=0.5, rely=1.0, y=-px(16), anchor="s")
        self.aviso.lift()                       # fica por cima do vídeo
        self._aviso_timer = self.janela.after(duracao_ms, self._desvanecer_aviso)

    # ------------------------------------------------------------------------
    # Animações (motion) — todas usam after(), nunca bloqueiam a interface
    # ------------------------------------------------------------------------
    def _animar_abertura(self, passo=0, passos=14):
        """Fade-in da janela ao abrir."""
        try:
            self.janela.attributes("-alpha", passo / passos)
        except tk.TclError:
            return
        if passo < passos:
            self.janela.after(16, self._animar_abertura, passo + 1, passos)

    def _pulsar_status(self):
        """Faz a bolinha de status 'respirar' enquanto a câmera está ativa."""
        if not self.camera_ativa or self.encerrando:
            return
        self.pulso = (self.pulso + 1) % 24
        t = abs(self.pulso - 12) / 12          # vai de 0 → 1 → 0
        self.ponto_status.itemconfigure(
            self.ponto, fill=interpolar_cor(COR_SUCESSO, COR_SUCESSO_ESCURO, t)
        )
        self.janela.after(50, self._pulsar_status)

    def _piscar_borda(self, passo=0, passos=10):
        """Feedback visual rápido ao salvar foto: a borda do vídeo clareia e volta."""
        if self.encerrando:
            return
        cor = interpolar_cor(COR_TEXTO, COR_BORDA, passo / passos)
        self.quadro_video.configure(highlightbackground=cor, highlightcolor=cor)
        if passo < passos:
            self.janela.after(30, self._piscar_borda, passo + 1, passos)

    def _desvanecer_aviso(self, passo=0, passos=10):
        if self.encerrando:
            return
        self.aviso.configure(
            fg=interpolar_cor(COR_TEXTO, COR_PAINEL_2, passo / passos)
        )
        if passo < passos:
            self._aviso_timer = self.janela.after(
                30, self._desvanecer_aviso, passo + 1, passos
            )
        else:
            self.aviso.place_forget()
            self._aviso_timer = None


if __name__ == "__main__":
    # Deixa o texto nítido em telas com escala (125%, 150%) no Windows.
    if sys.platform == "win32":
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

    janela = tk.Tk()
    Aplicacao(janela)
    janela.mainloop()
