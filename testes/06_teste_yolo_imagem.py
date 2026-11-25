# Etapa 12.6 — Executa o YOLO em uma imagem estática.
# Coloque uma foto em imagens/teste.jpg antes de rodar.
# Execute: python testes/06_teste_yolo_imagem.py
from ultralytics import YOLO

modelo = YOLO("yolo11n.pt")

resultados = modelo.predict(
    source="imagens/teste.jpg",
    conf=0.40
)

for resultado in resultados:
    print("Detecções:", len(resultado.boxes))
    for caixa in resultado.boxes:
        classe = resultado.names[int(caixa.cls)]
        confianca = float(caixa.conf)
        print(f"  - {classe}: {confianca:.2f}")
