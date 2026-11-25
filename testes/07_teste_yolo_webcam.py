# Etapa 13 — Integração YOLO + webcam, ainda sem Tkinter. Pressione "q" para sair.
# Execute: python testes/07_teste_yolo_webcam.py
import cv2
from ultralytics import YOLO

modelo = YOLO("yolo11n.pt")
camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("Não foi possível acessar a câmera.")
    raise SystemExit

while True:
    sucesso, frame = camera.read()

    if not sucesso:
        print("Falha na captura.")
        break

    resultados = modelo.predict(
        source=frame,
        conf=0.40,
        verbose=False
    )

    imagem_resultado = resultados[0].plot()

    cv2.imshow(
        "YOLO - Reconhecimento de Objetos",
        imagem_resultado
    )

    if (cv2.waitKey(1) & 0xFF) == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()
