# Plano de testes

Baseado na seção 18 do roteiro. Preencha a tabela de registro a cada execução
e salve as capturas de tela nesta pasta (`ct01.png`, `ct03.png`, ...).

## Casos de teste

| Caso | Objetivo         | Procedimento                              | Resultado esperado                              |
| ---- | ---------------- | ----------------------------------------- | ----------------------------------------------- |
| CT01 | Inicialização    | Executar `python main.py`                 | Janela é aberta                                 |
| CT02 | Modelo           | Inicializar aplicação                     | YOLO carrega ou erro é informado                |
| CT03 | Webcam           | Clicar **Iniciar**                        | Câmera é aberta e imagem aparece                |
| CT04 | Detecção         | Apresentar objetos à câmera               | Classes/caixas aparecem                         |
| CT05 | Parada           | Clicar **Parar**                          | Atualização para e câmera é liberada            |
| CT06 | Reinício         | Iniciar após parar                        | Câmera volta a funcionar                        |
| CT07 | Saída            | Clicar **Sair**                           | Aplicação encerra sem manter webcam presa       |
| CT08 | Falha de câmera  | Bloquear/indisponibilizar a câmera        | Mensagem de erro é exibida                      |
| CT09 | Clique duplicado | Clicar **Iniciar** repetidamente          | Não são criadas múltiplas capturas              |
| CT10 | Responsividade   | Usar botões durante a execução            | Interface continua respondendo                  |

## Registro de execução

| Caso | Data       | Resultado obtido | Status            | Evidência  |
| ---- | ---------- | ---------------- | ----------------- | ---------- |
| CT01 |            |                  | [ ] OK  [ ] Falha | ct01.png   |
| CT02 |            |                  | [ ] OK  [ ] Falha |            |
| CT03 |            |                  | [ ] OK  [ ] Falha | ct03.png   |
| CT04 |            |                  | [ ] OK  [ ] Falha | ct04.png   |
| CT05 |            |                  | [ ] OK  [ ] Falha |            |
| CT06 |            |                  | [ ] OK  [ ] Falha |            |
| CT07 |            |                  | [ ] OK  [ ] Falha |            |
| CT08 |            |                  | [ ] OK  [ ] Falha |            |
| CT09 |            |                  | [ ] OK  [ ] Falha |            |
| CT10 |            |                  | [ ] OK  [ ] Falha |            |

## Atividade 2 — Teste de confiança

Use o slider **Confiança mínima** e registre o que muda em cada valor.

| conf | Objetos detectados | Falsos positivos? | Observações |
| ---- | ------------------ | ----------------- | ----------- |
| 0,20 |                    |                   |             |
| 0,40 |                    |                   |             |
| 0,60 |                    |                   |             |
| 0,80 |                    |                   |             |

Valor escolhido pelo grupo: ______  Justificativa: ______________________
