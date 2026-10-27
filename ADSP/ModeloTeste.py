import cv2
from ultralytics import YOLO

# 1. Carrega o modelo treinado customizado
model = YOLO("best.pt")

# 2. Captura de vídeo (0 para webcam ou caminho do arquivo de vídeo)
cap = cv2.VideoCapture(0)

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    # Executa a detecção no frame atual
    results = model(frame, verbose=False)
    
    detections = []
    
    for result in results:
        for box in result.boxes:
            # Obtém coordenadas, confiança e classe
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0])
            cls = int(box.cls[0])
            class_name = model.names[cls]
            
            if conf > 0.5:  # Filtro de confiança
                # Armazena a coordenada X central e o nome da classe (o dígito)
                x_center = (x1 + x2) / 2
                detections.append((x_center, class_name, (x1, y1, x2, y2)))

    # 3. Ordena os dígitos da esquerda para a direita com base no X central
    detections.sort(key=lambda item: item[0])
    
    # Monta a string final do valor do multímetro
    valor_multimetro = "".join([item[1] for item in detections])
    
    # 4. Desenha os resultados na tela
    for _, class_name, (x1, y1, x2, y2) in detections:
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(frame, class_name, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
    if valor_multimetro:
        cv2.putText(frame, f"Leitura: {valor_multimetro}", (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

    # Exibe o frame
    cv2.imshow("Leitura de Multimetro com YOLO", frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
