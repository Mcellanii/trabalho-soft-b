"""
Camada visual — desenha as detecções sobre o frame com Pillow.

Por que não usar results.plot() do Ultralytics?
  * Ele usa a fonte do OpenCV, que não tem acentos ("Óculos", "Crachá").
  * Não tem transparência nem cantos arredondados.

Aqui cada detecção vira: preenchimento translúcido + cantos em destaque
(estilo "mira") + etiqueta arredondada com nome em português e confiança.

A cor vem da CATEGORIA do objeto (Eletrônicos = ciano, Cozinha = rosa...).
A mesma cor aparece nos filtros e na lista lateral da interface, então o
usuário aprende a "ler" a tela pela cor.
"""

from PIL import Image, ImageDraw, ImageFont

# Uma cor por categoria, com matizes bem separados no círculo de cores para
# que duas categorias nunca fiquem parecidas. Tons claros (400) contrastam bem
# tanto com o vídeo quanto com o tema escuro da interface.
CORES_CATEGORIA = {
    "Pessoas": "#60a5fa",      # azul
    "Acessórios": "#fbbf24",   # âmbar
    "Escritório": "#a3e635",   # verde-limão
    "Eletrônicos": "#22d3ee",  # ciano
    "Cozinha": "#f472b6",      # rosa
    "Alimentos": "#f87171",    # vermelho
    "Casa": "#a78bfa",         # violeta
    "Animais": "#34d399",      # esmeralda
}
COR_PADRAO = "#94a3b8"          # cinza para categorias não listadas


def cor_da_categoria(categoria):
    return CORES_CATEGORIA.get(categoria, COR_PADRAO)


def _carregar_fonte(tamanho):
    # Tenta fontes do Windows com acento; cai na fonte padrão se não achar.
    for nome in ("seguisb.ttf", "segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(nome, tamanho)
        except OSError:
            continue
    return ImageFont.load_default(size=tamanho)


_fontes = {}            # cache: carregar fonte do disco a cada frame é lento


def fonte_para(largura_imagem):
    """Fonte proporcional à imagem: ~1/50 da largura (16 px numa imagem de 800).

    Em telas grandes ou com escala de 150%/200% o vídeo é exibido maior, e uma
    fonte de tamanho fixo ficaria minúscula.
    """
    tamanho = max(14, round(largura_imagem / 50))
    if tamanho not in _fontes:
        _fontes[tamanho] = _carregar_fonte(tamanho)
    return _fontes[tamanho]


def _hex_para_rgb(cor):
    return tuple(int(cor[i:i + 2], 16) for i in (1, 3, 5))


def _cor_clara(rgb):
    r, g, b = rgb
    return 0.299 * r + 0.587 * g + 0.114 * b > 150


def desenhar_deteccoes(imagem, deteccoes):
    """Recebe uma imagem RGB e uma lista de detecções; devolve a imagem anotada.

    Cada detecção é um dicionário:
        {"caixa": (x1, y1, x2, y2), "nome": "Óculos",
         "categoria": "Acessórios", "confianca": 0.87}
    As coordenadas já devem estar na escala da imagem recebida.
    """
    base = imagem.convert("RGBA")
    camada = Image.new("RGBA", base.size, (0, 0, 0, 0))
    desenho = ImageDraw.Draw(camada)

    # Caixas maiores primeiro: assim a etiqueta de um objeto pequeno (ex.: um
    # anel sobre a mão) fica por cima e não é escondida pela caixa grande.
    def area(det):
        x1, y1, x2, y2 = det["caixa"]
        return (x2 - x1) * (y2 - y1)

    fonte = fonte_para(base.width)
    for det in sorted(deteccoes, key=area, reverse=True):
        _desenhar_uma(desenho, base.size, det, fonte)

    return Image.alpha_composite(base, camada).convert("RGB")


def _desenhar_uma(desenho, tamanho, det, fonte):
    largura_img, _ = tamanho
    x1, y1, x2, y2 = (int(v) for v in det["caixa"])
    nome = det["nome"]
    rgb = _hex_para_rgb(cor_da_categoria(det.get("categoria")))
    # Espessuras e margens acompanham o tamanho da fonte (que acompanha a tela).
    u = fonte.size / 16

    # 1) preenchimento translúcido + contorno fino
    desenho.rounded_rectangle(
        (x1, y1, x2, y2), radius=round(8 * u),
        fill=rgb + (26,), outline=rgb + (120,), width=max(1, round(u)),
    )

    # 2) cantos em destaque
    c = int(max(14 * u, min(x2 - x1, y2 - y1) * 0.18))
    cantos = [
        [(x1, y1 + c), (x1, y1), (x1 + c, y1)],
        [(x2 - c, y1), (x2, y1), (x2, y1 + c)],
        [(x1, y2 - c), (x1, y2), (x1 + c, y2)],
        [(x2 - c, y2), (x2, y2), (x2, y2 - c)],
    ]
    for pontos in cantos:
        desenho.line(pontos, fill=rgb + (255,), width=round(3 * u), joint="curve")

    # 3) etiqueta: "Óculos  87%"
    texto = f"{nome}  {det['confianca']:.0%}"
    tx1, ty1, tx2, ty2 = desenho.textbbox((0, 0), texto, font=fonte)
    largura_texto, altura_texto = tx2 - tx1, ty2 - ty1
    margem = round(7 * u)
    afastamento = round(6 * u)

    ex1 = max(x1, 0)
    ey1 = y1 - altura_texto - 2 * margem - afastamento
    if ey1 < 0:                       # caixa encostada no topo: etiqueta por dentro
        ey1 = y1 + afastamento
    ex2 = ex1 + largura_texto + 2 * margem
    if ex2 > largura_img:             # não deixa a etiqueta sair pela direita
        ex1 = max(ex1 - (ex2 - largura_img), 0)
        ex2 = largura_img
    ey2 = ey1 + altura_texto + 2 * margem

    desenho.rounded_rectangle((ex1, ey1, ex2, ey2), radius=round(6 * u),
                              fill=rgb + (240,))
    cor_texto = (15, 20, 25, 255) if _cor_clara(rgb) else (255, 255, 255, 255)
    desenho.text(
        (ex1 + margem - tx1, ey1 + margem - ty1),
        texto, font=fonte, fill=cor_texto,
    )
