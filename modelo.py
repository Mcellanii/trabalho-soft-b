"""
Camada de IA — vocabulário de classes e carregamento do modelo.

Usamos o YOLO-World, um detector de "vocabulário aberto": em vez das 80 classes
fixas do COCO, as classes são descritas em texto. O texto é em inglês porque o
codificador de texto (CLIP) foi treinado nesse idioma; o nome exibido na tela
fica em português.

Fluxo (acontece uma única vez):
    yolov8s-worldv2.pt  +  CLASSES (texto)  --CLIP-->  modelo_soft_b.pt

Depois disso a aplicação só carrega modelo_soft_b.pt e não precisa do CLIP.

Para recriar o modelo depois de editar CATEGORIAS:   python modelo.py
"""

import os

from ultralytics import YOLOWorld

MODELO_BASE = "yolov8s-worldv2.pt"      # baixado automaticamente (~26 MB)
MODELO_PERSONALIZADO = "modelo_soft_b.pt"

# Vocabulário organizado por categoria.
#   categoria -> { prompt em inglês (o que o modelo entende) : nome na tela }
#
# Dicas para escrever bons prompts:
#   * use o nome mais comum do objeto em inglês ("cell phone", não "smartphone");
#   * quando a palavra é ambígua, seja específico: "notebook" em inglês é
#     caderno, por isso usamos "spiral notebook" -> Caderno e "laptop" -> Notebook;
#   * cada prompt só pode aparecer uma vez no vocabulário inteiro.
CATEGORIAS = {
    "Pessoas": {
        "man": "Pessoa · Homem",
        "woman": "Pessoa · Mulher",
        "child": "Criança",
        "hand": "Mão",
    },
    "Acessórios": {
        "eyeglasses": "Óculos",
        "sunglasses": "Óculos de sol",
        "ring": "Aliança",
        "id badge": "Crachá",
        "wristwatch": "Relógio",
        "bracelet": "Pulseira",
        "necklace": "Colar",
        "earring": "Brinco",
        "baseball cap": "Boné",
        "hat": "Chapéu",
        "necktie": "Gravata",
        "face mask": "Máscara",
        "backpack": "Mochila",
        "handbag": "Bolsa",
        "wallet": "Carteira",
    },
    "Escritório": {
        "pencil": "Lápis",
        "pen": "Caneta",
        "highlighter": "Marca-texto",
        "eraser": "Borracha",
        "ruler": "Régua",
        "scissors": "Tesoura",
        "stapler": "Grampeador",
        "calculator": "Calculadora",
        "book": "Livro",
        "spiral notebook": "Caderno",
        "pencil case": "Estojo",
        "sticky note": "Post-it",
    },
    "Eletrônicos": {
        "cell phone": "Celular",
        "laptop": "Notebook",
        "tablet computer": "Tablet",
        "computer monitor": "Monitor",
        "keyboard": "Teclado",
        "computer mouse": "Mouse",
        "headphones": "Fone de ouvido",
        "earbuds": "Fone sem fio",
        "remote control": "Controle remoto",
        "game controller": "Controle de videogame",
        "camera": "Câmera",
        "charger": "Carregador",
        "usb flash drive": "Pendrive",
        "speaker": "Caixa de som",
    },
    "Cozinha": {
        "bottle": "Garrafa",
        "thermos": "Garrafa térmica",
        "mug": "Caneca",
        "cup": "Copo",
        "soda can": "Lata",
        "plate": "Prato",
        "bowl": "Tigela",
        "fork": "Garfo",
        "spoon": "Colher",
        "knife": "Faca",
    },
    "Alimentos": {
        "banana": "Banana",
        "apple": "Maçã",
        "orange": "Laranja",
        "bread": "Pão",
        "sandwich": "Sanduíche",
        "cookie": "Biscoito",
        "chocolate bar": "Chocolate",
    },
    "Casa": {
        "chair": "Cadeira",
        "couch": "Sofá",
        "potted plant": "Planta",
        "lamp": "Luminária",
        "wall clock": "Relógio de parede",
        "key": "Chave",
        "umbrella": "Guarda-chuva",
        "toothbrush": "Escova de dentes",
        "teddy bear": "Ursinho de pelúcia",
    },
    "Animais": {
        "dog": "Cachorro",
        "cat": "Gato",
        "bird": "Pássaro",
    },
}

# Versões "achatadas" do dicionário acima, montadas automaticamente:
#   CLASSES             prompt -> nome em português   ("pen" -> "Caneta")
#   CATEGORIA_DO_PROMPT prompt -> categoria            ("pen" -> "Escritório")
CLASSES = {}
CATEGORIA_DO_PROMPT = {}
for _categoria, _itens in CATEGORIAS.items():
    for _prompt, _nome in _itens.items():
        if _prompt in CLASSES:
            raise ValueError(f"Prompt repetido no vocabulário: {_prompt!r}")
        CLASSES[_prompt] = _nome
        CATEGORIA_DO_PROMPT[_prompt] = _categoria


def nome_em_portugues(prompt):
    """Converte o prompt do modelo ("eyeglasses") no nome exibido ("Óculos")."""
    return CLASSES.get(prompt, prompt)


def categoria_de(prompt):
    """Devolve a categoria de um prompt ("pen" -> "Escritório")."""
    return CATEGORIA_DO_PROMPT.get(prompt, "Outros")


def carregar_modelo(progresso=print):
    """Devolve o modelo pronto para predict().

    1. Se modelo_soft_b.pt existe e tem o vocabulário atual, usa ele.
    2. Senão, baixa o YOLO-World base, define as classes (isso usa o CLIP,
       baixado só nessa primeira vez) e salva o resultado em modelo_soft_b.pt.

    `progresso` é uma função que recebe mensagens de status (print na linha
    de comando; na interface, atualiza o texto de carregamento).
    """
    prompts = list(CLASSES)

    if os.path.exists(MODELO_PERSONALIZADO):
        modelo = YOLOWorld(MODELO_PERSONALIZADO)
        if list(modelo.names.values()) == prompts:
            return modelo
        progresso("Vocabulário mudou — recriando o modelo...")
    else:
        progresso("Criando modelo personalizado (só na primeira vez)...")

    modelo = YOLOWorld(MODELO_BASE)
    modelo.set_classes(prompts)
    modelo.save(MODELO_PERSONALIZADO)
    progresso(f"Modelo salvo em {MODELO_PERSONALIZADO}")

    # Recarrega do arquivo para garantir que o .pt salvo funciona sozinho.
    return YOLOWorld(MODELO_PERSONALIZADO)


if __name__ == "__main__":
    modelo = carregar_modelo()
    print(f"{len(modelo.names)} classes no modelo:")
    for indice, prompt in modelo.names.items():
        print(
            f"  {indice:2d}  {prompt:18s} -> {nome_em_portugues(prompt):22s}"
            f" [{categoria_de(prompt)}]"
        )
