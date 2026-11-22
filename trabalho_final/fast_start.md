# Setup

Rode o `run.py`. Ele cuida do resto (Python 3.11.9, ambiente virtual e dependências). Você só precisa de um Python 3.8 ou mais novo para executá-lo, não precisa ser o 3.11.9.

## Rodar

```powershell
python run.py
```

Na primeira execução, o `run.py`:

1. Procura o **Python 3.11.9** (versão exata). Se não houver, baixa sozinho (via `uv`, numa pasta local, sem instalar nada no sistema).
2. Cria o ambiente virtual `.venv`.
3. Instala as dependências do `requirements.txt`.
4. Abre o programa.

Nas próximas vezes, ele só abre o programa. A primeira execução demora mais, por causa do download e da instalação.

## Outros usos

O programa abre a interface (`multimeter_calibration_GUI.py`), com três abas: **1 · Visualização**, **2 · Configuração** e **3 · Captura**.

Os logs (CSV) e as imagens ficam na pasta `logs`. Na aba 2 você pode desligar o log, dar um nome ao arquivo (se já existir, as leituras são acrescentadas) ou deixar o nome em branco para criar `leituras_AAAAMMDD_HHMMSS.csv` a cada captura. Também dá para cadastrar alertas por valor (por exemplo, leitura ≥ 5 ou leitura ≤ 1).

Para usar a lógica pelo terminal, sem a interface (por exemplo, só o teste de qualidade da imagem):

```powershell
python run.py multimeter_calibration_api.py --quality-only
```

## Requisitos

- Windows, com webcam (a câmera é aberta com DirectShow).
- Internet: para baixar o Python e as dependências na primeira vez, e para a leitura do display, que usa o workflow do Roboflow.
- Chave da API do Roboflow no arquivo `config.json`, na pasta do projeto (ele não vai para o Git). Se não existir, copie o `config.example.json` para `config.json` e preencha:

```json
{ "roboflow_api_key": "sua-chave" }
```

  Também funciona digitar a chave na aba **2 · Configuração** (marcando "Gravar no config.json" para guardá-la) ou usar a variável de ambiente `ROBOFLOW_API_KEY`.

## Problemas comuns

- **`python` não é reconhecido:** instale o Python em python.org e marque "Add Python to PATH", ou use `py run.py`.
- **Quer recriar o ambiente do zero:** apague a pasta `.venv` e rode `python run.py` de novo.
- **Câmera não abre:** feche outros programas que usem a webcam. Se houver mais de uma, o índice padrão é 0.
