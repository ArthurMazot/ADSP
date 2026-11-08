# Leitura automática de displays de multímetros na calibração

**Autores:** Sophia Mendes e Arthur Mazot

---

**Objetivo geral:** propor uma solução para capturar, interpretar e registrar automaticamente as leituras exibidas no display de multímetros portáteis durante a calibração, reduzindo a leitura visual e a anotação manual feitas pelo operador e favorecendo a automação, a rastreabilidade e a padronização do processo.

---

## Histórico

<details>
<summary><strong>Hipótese 1</strong> (27 a 29 de outubro): treinar um modelo próprio</summary>

Os integrantes do grupo realizaram testes em Python para validar o acesso à câmera, com o objetivo de criar e treinar um modelo de aprendizado para identificar os números do display.

O acesso à câmera foi feito com a biblioteca **OpenCV** (`opencv-python`, módulo `cv2`):
- `cv2.VideoCapture` abre a webcam, com o backend DirectShow (`cv2.CAP_DSHOW`), que só existe no Windows, e lê os quadros.
- `cv2.imshow` mostra a imagem ao vivo, e o callback de mouse (`cv2.setMouseCallback`) permite ao usuário arrastar um retângulo sobre o display.
- O recorte (ROI) é obtido pelo fatiamento do quadro (`frame[y:y+h, x:x+w]`), de modo que só o display seja analisado.

Porém, treinar um modelo de forma eficiente exige:
- **Variedade de multímetros**, que não estava à nossa disposição.
- **Quantidade mínima de imagens.** A documentação da Ultralytics (YOLO) recomenda cerca de 1500 imagens e 10 000 instâncias rotuladas por classe. Mesmo na estimativa mais otimista, a equipe da Roboflow sugere pelo menos 50 imagens representativas por classe só para o primeiro modelo.
- **Rotulagem manual** de cada imagem de treino.

Sem variedade de equipamentos, com a necessidade de reunir e rotular muitas imagens à mão, essa linha de solução se tornou insustentável para o prazo do projeto.

**Referências:**
- Ultralytics, [Tips for Best Training Results](https://docs.ultralytics.com/yolov5/tutorials/tips-for-best-training-results)
- Roboflow, [fórum: quantidade de imagens por classe](https://discuss.roboflow.com/t/roboflow-3-0-and-yolo-8-11-transfer-learning-advice-needed/10152)

</details>

<details>
<summary><strong>Hipótese 2</strong> (3 a 5 de novembro): estudar soluções existentes</summary>

Os integrantes estudaram as estruturas de OCR para sete segmentos, a começar por [YOLO App OCR](https://mpolinowski.github.io/docs/IoT-and-Machine-Learning/ML/2022-02-18--yolo-app-ocr/2022-02-18/).

A abordagem em MATLAB, [Train Custom OCR Model to Detect Seven-Segment Digits](https://www.mathworks.com/help/vision/ug/train-custom-ocr-model-to-detect-seven-segment-digits.html), exigia o **Computer Vision Toolbox**, que não existe nas licenças MATLAB disponíveis. Mesmo assim, o exemplo também depende de rotulagem manual: usa 119 imagens de displays de medidores de energia, rotuladas à mão, e chega a cerca de 89% de acurácia por caractere.

Os alunos então se dividiram para estudar as demais estruturas compartilhadas pelo professor e para pesquisar individualmente:
- bases de imagens de multímetros diversos (a maioria paga);
- modelos já prontos;
- APIs de reconhecimento.

Nessas pesquisas, encontramos o workflow **Seven Segment Multi-Display Reader**, hospedado no Roboflow, que recebe a imagem do display e devolve as leituras. O protótipo o chama pelo `inference-sdk` (`InferenceHTTPClient.run_workflow`), enviando só o recorte do display e lendo o campo `readings` da resposta.

**Diferença em relação ao YOLO:** o YOLO é uma arquitetura de detecção de objetos que precisaríamos treinar, com dados nossos, e depois integrar. O workflow do Roboflow é uma solução já treinada e hospedada, usada por API, que dispensa treino e infraestrutura própria. Não comparamos os dois em desempenho, já que não treinamos um YOLO próprio.

**Por que escolhemos o workflow:** ao estudar a implementação das duas opções, workflow nos coloca diretamente no ponto que importa para o projeto, que é testar a leitura em displays reais, sem passar semanas montando e rotulando uma base de imagens que não temos. Também exige poucas linhas de código para integrar com a câmera. Em troca, passamos a depender de um serviço externo (internet e chave de API) e não controlamos o modelo por dentro.

</details>

---

## Abordagem / Metodologia

Com a identificação dos números do display resolvida, a peça central está definida. Para que a solução sirva na calibração, porém, ela precisa de um contato amigável com o usuário. Por isso a proposta é um **front simples em Python** (inicialmente com Tkinter, a confirmar), organizado em três etapas.

<details>
<summary><strong>1. Calibração da visualização</strong></summary>

Antes de calibrar o multímetro, o operador verifica se a câmera enxerga bem o display:
- Seleciona a área do display, desenhando um retângulo (e, como melhoria, um retângulo automático que encontre a parte do multímetro que mostra os números).
- O sistema faz um **teste de qualidade da imagem**, mesmo antes de passar pelo identificador: luminosidade, reflexo, contraste e nitidez do recorte.
- Esses valores podem ser comparados a uma imagem de exemplo em condições ideais, para indicar o que falta ajustar.

</details>

<details>
<summary><strong>2. Configuração da captura</strong></summary>

O operador define:
- **Intervalo de tempo** entre as capturas (fixo).
- **Limite de imagens** a capturar.
- **Arquivo de log**, com as colunas: tempo, número, unidade, ponto de calibração, ciclo, status da leitura (ok, duvidosa ou falha) e caminho da imagem capturada.
- Campos **opcionais**: ponto de calibração, ciclo e valor mínimo/máximo esperado. Quando em branco, as colunas ficam vazias e o alerta de faixa não é usado.

</details>

<details>
<summary><strong>3. Captura e acompanhamento</strong></summary>

Ao iniciar a captura:
- O valor lido é atualizado em uma caixa na tela e gravado no log.
- Periodicamente, o teste de qualidade da imagem é repetido.
- O sistema emite **alertas** para:
  - leitura vazia ou ilegível;
  - salto brusco entre leituras;
  - reflexo ou luminosidade fora da faixa;
  - câmera possivelmente movida;
  - valor fora do mínimo/máximo definido (opcional).

</details>

---

## Cronograma

<details>
<summary><strong>Implementação</strong> (10/11 e 12/11)</summary>

- **Arthur:** implementação do modelo, com as funções de captura e o resultado no terminal.
- **Sophia:** implementação da calibração da visualização, com as funções para identificar a área de foco (retângulo desenhado), reflexo e luminosidade, também no terminal por enquanto.

</details>

<details>
<summary><strong>Implementação</strong> (17/11 e 19/11)</summary>

- **Arthur:** funções do sistema de arquivos de log.
- **Sophia:** front, com a janela de interação com o usuário.

</details>

<details>
<summary><strong>Resultados</strong> (24/11 e 26/11)</summary>

- **Arthur e Sophia:** testes, resultados e relatório.

</details>
