# -*- coding: utf-8 -*-
"""Động cơ nhận diện khuôn mặt: phát hiện bằng Haar Cascade, nhận diện bằng
LBPH (Local Binary Patterns Histograms) — hoàn toàn dùng OpenCV, không cần dlib."""
import cv2
import os
import numpy as np
import json

import db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FACES_DIR = os.path.join(BASE_DIR, "faces")
MODEL_PATH = os.path.join(BASE_DIR, "models", "lbph_model.yml")
LABELMAP_PATH = os.path.join(BASE_DIR, "models", "label_map.json")
os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)

CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"


class FaceEngine:
    def __init__(self, confidence_threshold=None):
        self.detector = cv2.CascadeClassifier(CASCADE_PATH)
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        self.label_to_manv = {}
        # Nếu không truyền threshold, lấy từ cài đặt lưu trong DB (mặc định 55,
        # có thể chỉnh trong Cài đặt > Nhận diện khuôn mặt).
        self.threshold = confidence_threshold if confidence_threshold is not None else self._load_threshold()
        self.trained = False
        self._load()

    @staticmethod
    def _load_threshold():
        try:
            return int(db.get_setting("face_confidence_threshold", 45))
        except Exception:
            return 45

    def _load(self):
        if os.path.exists(MODEL_PATH) and os.path.exists(LABELMAP_PATH):
            try:
                self.recognizer.read(MODEL_PATH)
                with open(LABELMAP_PATH, "r", encoding="utf-8") as f:
                    self.label_to_manv = {int(k): v for k, v in json.load(f).items()}
                self.trained = True
            except Exception:
                self.trained = False

    def reload(self):
        """Tải lại model + label map + ngưỡng nhận diện mới nhất từ đĩa/DB.
        Gọi hàm này mỗi khi cần chắc chắn dùng đúng model/ngưỡng vừa cập nhật
        (ví dụ khi bật camera chấm công, hoặc sau khi admin đổi ngưỡng trong
        Cài đặt), vì việc thay đổi có thể diễn ra ở một trang khác trong cùng
        phiên chạy."""
        self.threshold = self._load_threshold()
        self._load()

    def detect_faces(self, frame_bgr):
        """Trả về list (x, y, w, h) các khuôn mặt phát hiện được trong khung hình."""
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        faces = self.detector.detectMultiScale(gray, scaleFactor=1.15, minNeighbors=5,
                                                minSize=(90, 90))
        return faces, gray

    def save_face_samples(self, ma_nv, frame_bgr, index, blur_threshold=60, min_face_size=110):
        """Cắt & lưu ảnh khuôn mặt để dùng huấn luyện. Có kiểm tra chất lượng
        cơ bản (chỉ 1 mặt trong khung, mặt đủ lớn, không bị mờ) để tránh nạp
        dữ liệu xấu làm mô hình dễ nhận nhầm người. Trả về 1 trong các mã:
        'ok', 'no_face', 'multiple_faces', 'too_small', 'blurry'."""
        faces, gray = self.detect_faces(frame_bgr)
        if len(faces) == 0:
            return "no_face"
        if len(faces) > 1:
            # Có nhiều hơn 1 mặt trong khung hình lúc đăng ký rất dễ lẫn dữ
            # liệu của 2 người vào cùng 1 nhãn -> yêu cầu chụp lại cho rõ.
            return "multiple_faces"
        x, y, w, h = faces[0]
        if w < min_face_size or h < min_face_size:
            return "too_small"
        face_crop = gray[y:y + h, x:x + w]
        blur_score = cv2.Laplacian(face_crop, cv2.CV_64F).var()
        if blur_score < blur_threshold:
            return "blurry"
        face_img = cv2.resize(face_crop, (200, 200))
        folder = os.path.join(FACES_DIR, ma_nv)
        os.makedirs(folder, exist_ok=True)
        cv2.imwrite(os.path.join(folder, f"{index:02d}.jpg"), face_img)
        return "ok"

    def train(self, ma_nv_to_label: dict):
        """Huấn luyện lại toàn bộ model LBPH từ thư mục faces/, ma_nv_to_label:
        {ma_nv: label_id}."""
        samples, labels = [], []
        for ma_nv, label in ma_nv_to_label.items():
            folder = os.path.join(FACES_DIR, ma_nv)
            if not os.path.isdir(folder):
                continue
            for fname in os.listdir(folder):
                img = cv2.imread(os.path.join(folder, fname), cv2.IMREAD_GRAYSCALE)
                if img is None:
                    continue
                samples.append(cv2.resize(img, (200, 200)))
                labels.append(label)
        if not samples:
            self.trained = False
            return False
        self.recognizer.train(samples, np.array(labels))
        self.recognizer.save(MODEL_PATH)
        self.label_to_manv = {v: k for k, v in ma_nv_to_label.items()}
        with open(LABELMAP_PATH, "w", encoding="utf-8") as f:
            json.dump({str(v): k for k, v in ma_nv_to_label.items()}, f, ensure_ascii=False)
        self.trained = True
        return True

    def self_test(self, ma_nv_to_label: dict):
        """Kiểm tra chất lượng sau khi huấn luyện: với mỗi nhân viên, cho
        chính các ảnh khuôn mặt của họ chạy lại qua model vừa train và tính
        % số ảnh nhận đúng ra chính họ (confidence <= ngưỡng hiện tại). Nhân
        viên có tỉ lệ thấp thường là dấu hiệu ảnh chụp lúc đăng ký không đạt
        chất lượng (quá ít ảnh, ảnh mờ, góc mặt giống người khác...) và dễ
        gây nhận nhầm khi chấm công thật. Trả về dict {ma_nv: (đúng, tổng, %)}."""
        results = {}
        for ma_nv, label in ma_nv_to_label.items():
            folder = os.path.join(FACES_DIR, ma_nv)
            if not os.path.isdir(folder):
                continue
            total, correct = 0, 0
            for fname in os.listdir(folder):
                img = cv2.imread(os.path.join(folder, fname), cv2.IMREAD_GRAYSCALE)
                if img is None:
                    continue
                img = cv2.resize(img, (200, 200))
                pred_label, conf = self.recognizer.predict(img)
                total += 1
                if pred_label == label and conf <= self.threshold:
                    correct += 1
            if total:
                results[ma_nv] = (correct, total, round(100 * correct / total, 1))
        return results

    def recognize(self, frame_bgr):
        """Trả về (ma_nv hoặc None, (x,y,w,h) hoặc None, confidence)."""
        faces, gray = self.detect_faces(frame_bgr)
        if len(faces) == 0:
            return None, None, None
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
        if not self.trained:
            return None, (x, y, w, h), None
        face_img = cv2.resize(gray[y:y + h, x:x + w], (200, 200))
        label, confidence = self.recognizer.predict(face_img)
        # LBPH: confidence thấp hơn = giống hơn
        if confidence <= self.threshold:
            ma_nv = self.label_to_manv.get(label)
            return ma_nv, (x, y, w, h), confidence
        return None, (x, y, w, h), confidence
