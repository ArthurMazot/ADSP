import cv2

# Inicializa a câmera padrão (índice 0)
cap = cv2.VideoCapture(0)
i = 0
while True:
  # Lê o frame da câmera
  ret, frame = cap.read()

  if not ret:
    break

  # Exibe o frame em uma janela
  cv2.imshow("Webcam - Pressione 'q' para sair", frame)

  # Interrompe o loop ao pressionar a tecla 'q'
  if cv2.waitKey(1) & 0xFF == ord("p"):
    cv2.imwrite(f'Teste{i}.jpg', frame)
    i+=1

  if cv2.waitKey(1) & 0xFF == ord("q"):
    break

# Libera a câmera e fecha as janelas
cap.release()
cv2.destroyAllWindows()
