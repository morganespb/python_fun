import os
import threading
import time
import urllib.request

import numpy as np

# hidden webcam + mediapipe in a background thread.
# sketches only read the results, never the picture.
#   Tracker("hand")    .hands  list of (21, 3) arrays, x and y in 0..1
#   Tracker("segment") .mask   (h, w) array, 1 = person
# everything is mirrored, so right is right.

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = "https://storage.googleapis.com/mediapipe-models/"
MODELS = {
    "hand": ("hand_landmarker.task", "hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task"),
    "segment": ("selfie_segmenter.tflite", "image_segmenter/selfie_segmenter/float16/latest/selfie_segmenter.tflite"),
}


def model(kind):
    name, path = MODELS[kind]
    local = os.path.join(ROOT, "models", name)
    if not os.path.exists(local):
        print("downloading", name)
        os.makedirs(os.path.dirname(local), exist_ok=True)
        urllib.request.urlretrieve(URL + path, local)
    return local


def detector(kind):
    import mediapipe as mp
    from mediapipe.tasks.python import BaseOptions, vision

    base = BaseOptions(model_asset_path=model(kind))
    video = vision.RunningMode.VIDEO
    if kind == "hand":
        # low thresholds: finds hands more easily, keeps them while they move
        opts = vision.HandLandmarkerOptions(base_options=base, running_mode=video, num_hands=2,
                                            min_hand_detection_confidence=0.3,
                                            min_hand_presence_confidence=0.3,
                                            min_tracking_confidence=0.3)
        return mp, vision.HandLandmarker.create_from_options(opts)
    opts = vision.ImageSegmenterOptions(base_options=base, running_mode=video, output_confidence_masks=True)
    return mp, vision.ImageSegmenter.create_from_options(opts)


def detect(mp, det, kind, rgb, ms):
    img = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))
    if kind == "hand":
        res = det.detect_for_video(img, ms)
        return [np.array([(p.x, p.y, p.z) for p in hand], np.float32) for hand in res.hand_landmarks]
    return np.array(det.segment_for_video(img, ms).confidence_masks[-1].numpy_view(), np.float32).squeeze()


class Tracker(threading.Thread):
    def __init__(self, kind="hand", camera=0, width=960):
        super().__init__(daemon=True)
        self.kind, self.camera, self.width = kind, camera, width
        self.hands, self.mask, self.image = [], None, None
        self.status, self.ok, self.updated, self.stopped = "starting camera", False, 0.0, False
        self.start()

    def run(self):
        try:
            import cv2
            mp, det = detector(self.kind)
        except Exception as e:
            self.status = f"no tracker ({e.__class__.__name__})"
            return
        cap = cv2.VideoCapture(self.camera)
        if not cap.isOpened():
            self.status = "no camera (check camera permission)"
            return
        self.status, self.ok = "camera on, hidden", True
        t0, last = time.perf_counter(), -1
        while not self.stopped:
            good, frame = cap.read()
            if not good:
                time.sleep(0.01)
                continue
            frame = cv2.flip(frame, 1)
            h, w = frame.shape[:2]
            if w > self.width:
                frame = cv2.resize(frame, (self.width, h * self.width // w))
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            ms = max(last + 1, int((time.perf_counter() - t0) * 1000))  # must always go up
            last = ms
            out = detect(mp, det, self.kind, rgb, ms)
            self.image = rgb
            if self.kind == "hand":
                self.hands = out
            else:
                self.mask = out
            self.updated = time.perf_counter()
        cap.release()
        det.close()

    @property
    def fresh(self):
        return self.ok and time.perf_counter() - self.updated < 0.5

    def stop(self):
        self.stopped = True
