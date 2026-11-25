# Etapa 12.4 — Mostra a webcam com OpenCV, sem YOLO. Pressione "q" para sair.
# Execute: python testes/04_teste_webcam.py
import cv2

camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("Erro: não foi possível acessar a câmera.")
    raise SystemExit

while True:
    sucesso, frame = camera.read()

    if not sucesso:
        print("Erro ao capturar frame.")
        break

    cv2.imshow("Teste da Webcam", frame)

    if (cv2.waitKey(1) & 0xFF) == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()
