import argparse

import cv2
from inference_sdk import InferenceHTTPClient


WORKSPACE = "arthurs-workspace-pjgli"
WORKFLOW = "seven-segment-multi-display-reader-1793736667455"
API_KEY = "Fgugzd9PwTSrd4HTF8Nm"
WINDOW = "Display reader | drag: select | p: read | r: reset | q: quit"

# Rectangle selection state
start_point = None
current_point = None
selected_roi = None  # (x, y, width, height)
dragging = False


def on_mouse(event, x, y, flags, userdata):
    global start_point, current_point, selected_roi, dragging

    if event == cv2.EVENT_LBUTTONDOWN:
        start_point = (x, y)
        current_point = (x, y)
        dragging = True

    elif event == cv2.EVENT_MOUSEMOVE and dragging:
        current_point = (x, y)

    elif event == cv2.EVENT_LBUTTONUP and dragging:
        dragging = False

        x1, x2 = sorted((start_point[0], x))
        y1, y2 = sorted((start_point[1], y))

        if x2 - x1 >= 10 and y2 - y1 >= 10:
            selected_roi = (x1, y1, x2 - x1, y2 - y1)
            print(f"Selected display area: {selected_roi}", flush=True)
        else:
            print("Selection too small; drag a larger rectangle.", flush=True)

        start_point = None
        current_point = None


def main():
    global selected_roi

    parser = argparse.ArgumentParser()
    parser.add_argument("--camera", type=int, default=0)
    args = parser.parse_args()

    client = InferenceHTTPClient(
        api_url="https://serverless.roboflow.com",
        api_key=API_KEY,
    )

    camera = cv2.VideoCapture(args.camera, cv2.CAP_DSHOW)
    if not camera.isOpened():
        raise SystemExit(f"Could not open webcam {args.camera}")

    cv2.namedWindow(WINDOW)
    cv2.setMouseCallback(WINDOW, on_mouse)

    print("Drag a box around the LCD digits, including the sign and decimal.")
    print("Press p to capture/read, r to reselect, or q to quit.")

    try:
        while True:
            ok, frame = camera.read()
            if not ok:
                print("Could not read a webcam frame.")
                break

            preview = frame.copy()

            if selected_roi is not None:
                x, y, w, h = selected_roi
                cv2.rectangle(preview, (x, y), (x + w, y + h), (0, 255, 0), 2)

            if dragging and start_point is not None and current_point is not None:
                cv2.rectangle(preview, start_point, current_point, (0, 255, 255), 2)

            cv2.imshow(WINDOW, preview)
            key = cv2.waitKey(1) & 0xFF

            if key == ord("q"):
                break

            if key == ord("r"):
                selected_roi = None
                print("Selection cleared; drag a new box.", flush=True)

            if key == ord("p"):
                if selected_roi is None:
                    print("Select a display area first.", flush=True)
                    continue

                # Send only the selected pixels, not the whole frame.
                x, y, w, h = selected_roi
                crop = frame[y:y + h, x:x + w]

                print("Reading captured display...", flush=True)
                try:
                    result = client.run_workflow(
                        workspace_name=WORKSPACE,
                        workflow_id=WORKFLOW,
                        images={"image": crop},
                        use_cache=True,
                    )

                    output = result[0] if isinstance(result, list) else result
                    print(output["readings"], flush=True)

                except Exception as error:
                    print(f"Reading failed: {error}", flush=True)

    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()