# Etapa 12.5 — Carrega o modelo YOLO. Na 1ª execução o arquivo yolo11n.pt é baixado.
# Execute: python testes/05_teste_yolo.py
from ultralytics import YOLO

print("Carregando modelo...")
modelo = YOLO("yolo11n.pt")
print("Modelo carregado.")
print("Quantidade de classes conhecidas:", len(modelo.names))
