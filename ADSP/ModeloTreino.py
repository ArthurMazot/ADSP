from ultralytics import YOLO

# Carrega um modelo pré-treinado (ex: yolo11n.pt ou yolo8n.pt)
model = YOLO('yolo11n.pt')

# Inicia o treinamento
results = model.train(
    data='C:\Users\a.mazot\Documents\PlatformIO\Projects\ADSP\data.yaml',
    epochs=100,
    imgsz=640,
    batch=16
)