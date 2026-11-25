# Etapa 12.2 — Verifica se todas as bibliotecas foram instaladas no .venv.
# Execute: python testes/02_teste_importacoes.py
import cv2
import tkinter as tk
from PIL import Image, ImageTk
from ultralytics import YOLO

print("Importações realizadas com sucesso.")
print("OpenCV:", cv2.__version__)
print("Tkinter:", tk.TkVersion)
