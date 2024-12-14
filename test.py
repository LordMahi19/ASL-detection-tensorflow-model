import cv2
import mediapipe as mp
import numpy as np
from multiprocessing import Process, Queue
from tensorflow.keras.models import load_model
from sklearn.preprocessing import LabelEncoder  # Import LabelEncoder

def process_frame(frame_queue, result_queue, model, le): # Add le to function arguments
    mp_hands = mp.solutions.hands
    mp_drawing = mp.solutions.drawing_utils
    mp_drawing_styles = mp.solutions.drawing_styles

    hands = mp_hands.Hands(static_image_mode=True, min_detection_confidence=0.3)

    while True:
        frame = frame_queue.get()
        if frame is None:
            break

        data_aux = []
        x_ = []
        y_ = []

        H, W, _ = frame.shape
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(frame_rgb)

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                mp_drawing.draw_landmarks(
                    frame, hand_landmarks, mp_hands.HAND_CONNECTIONS,
                    mp_drawing_styles.get_default_hand_landmarks_style(),
                    mp_drawing_styles.get_default_hand_connections_style())

                for i in range(len(hand_landmarks.landmark)):
                    x = hand_landmarks.landmark[i].x
                    y = hand_landmarks.landmark[i].y
                    x_.append(x)
                    y_.append(y)

                for i in range(len(hand_landmarks.landmark)):
                    x = hand_landmarks.landmark[i].x
                    y = hand_landmarks.landmark[i].y
                    data_aux.append(x - min(x_))
                    data_aux.append(y - min(y_))

            x1 = int(min(x_) * W) - 10
            y1 = int(min(y_) * H) - 10
            x2 = int(max(x_) * W) - 10
            y2 = int(max(y_) * H) - 10

            if len(data_aux) == 42: # Check if enough landmarks are detected
                try:
                    data_aux = np.asarray(data_aux).reshape(1, 42)
                    prediction = model.predict(data_aux)
                    predicted_character_index = np.argmax(prediction[0])
                    predicted_character = le.inverse_transform([predicted_character_index])[0] # Decode the prediction

                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 0), 4)
                    cv2.putText(frame, predicted_character, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 0, 0), 3, cv2.LINE_AA)
                except ValueError as e:
                    print(f"Prediction Error: {e}") # Print the error for debugging
                    cv2.putText(frame, "Error", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 0, 0), 3, cv2.LINE_AA)
            else:
                cv2.putText(frame, "No Hand Detected", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 0, 0), 3, cv2.LINE_AA)

        result_queue.put(frame)

def main():
    model = load_model('sign_language_model.h5')

    # Load the label encoder (important!)
    data = np.load("sign_language_dataset.npz")
    y_train = data['labels']
    le = LabelEncoder()
    le.fit(y_train) # Fit the LabelEncoder on the training labels

    cap = cv2.VideoCapture(0)
    frame_queue = Queue()
    result_queue = Queue()

    process = Process(target=process_frame, args=(frame_queue, result_queue, model, le)) # Pass le to process_frame
    process.start()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_queue.put(frame)
        processed_frame = result_queue.get()

        cv2.imshow('frame', processed_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    frame_queue.put(None)
    process.join()

    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()