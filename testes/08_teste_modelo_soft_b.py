# Etapa extra — Carrega o modelo personalizado (YOLO-World com as classes do
# projeto) e lista o vocabulário em português.
# Na 1ª execução baixa yolov8s-worldv2.pt (~26 MB) e o CLIP (~340 MB), e salva
# modelo_soft_b.pt. Nas seguintes, só carrega o arquivo salvo.
# Execute: python testes/08_teste_modelo_soft_b.py
import os
import sys

# Permite importar modelo.py mesmo rodando de dentro da pasta testes/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modelo import carregar_modelo, nome_em_portugues

print("Carregando modelo personalizado...")
modelo = carregar_modelo()
print("Modelo carregado.")
for indice, prompt in modelo.names.items():
    print(f"  {indice:2d}  {prompt:16s} -> {nome_em_portugues(prompt)}")
