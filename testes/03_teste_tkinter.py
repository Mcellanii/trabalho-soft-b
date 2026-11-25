# Etapa 12.3 — Abre uma janela simples para confirmar que o Tkinter funciona.
# Execute: python testes/03_teste_tkinter.py
import tkinter as tk

janela = tk.Tk()
janela.title("Teste Tkinter")
janela.geometry("400x200")

texto = tk.Label(janela, text="Tkinter funcionando!")
texto.pack(pady=50)

janela.mainloop()
