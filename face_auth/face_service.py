import os
import json
import cv2
import numpy as np
import base64
from io import BytesIO
from PIL import Image
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime
import time

FACE_MATCH_THRESHOLD = float(os.getenv("FACE_MATCH_THRESHOLD", "0.75"))
MIN_FRAMES = 15
EMBEDDING_SIZE = 512

_face_analysis = None

def get_face_analysis():
    global _face_analysis
    if _face_analysis is None:
        try:
            from insightface.app import FaceAnalysis
            _face_analysis = FaceAnalysis(name='buffalo_s', providers=['CPUExecutionProvider'])
            _face_analysis.prepare(ctx_id=0, det_size=(224, 224))
        except Exception as e:
            print(f"[FaceAuth] Erro ao carregar FaceAnalysis: {e}")
            raise
    return _face_analysis


# Model will be loaded lazily on first use via get_face_analysis()


def decode_frame(base64_string):
    if "," in base64_string:
        base64_string = base64_string.split(",")[1]
    img_bytes = base64.b64decode(base64_string)
    nparr = np.frombuffer(img_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return frame


def extract_landmarks_from_face(face):
    if hasattr(face, 'landmark_2d_106'):
        return face.landmark_2d_106.tolist()
    if hasattr(face, 'landmark_3d_68'):
        return face.landmark_3d_68.tolist()
    if hasattr(face, 'landmark_2d_68'):
        return face.landmark_2d_68.tolist()
    if hasattr(face, 'kps'):
        kps = face.kps
        return kps.tolist() if hasattr(kps, 'tolist') else None
    return None


def detect_and_extract(frame, extract_landmarks=False):
    app = get_face_analysis()
    faces = app.get(frame)
    if len(faces) == 0:
        return None, None, None
    face = faces[0]
    embedding = face.normed_embedding.tolist() if hasattr(face, 'normed_embedding') else face.embedding.tolist()
    bbox = face.bbox.astype(int).tolist() if hasattr(face, 'bbox') else None
    landmarks = None
    head_pose = None
    if extract_landmarks:
        landmarks = extract_landmarks_from_face(face)
        if hasattr(face, 'head_pose'):
            pose = face.head_pose
            if hasattr(pose, 'tolist'):
                pose = pose.tolist()
            if isinstance(pose, (list, tuple)) and len(pose) >= 3:
                head_pose = {"yaw": float(pose[0]), "pitch": float(pose[1]), "roll": float(pose[2])}
    det_score = float(face.det_score) if hasattr(face, 'det_score') else 1.0
    return embedding, bbox, {
        "landmarks": landmarks,
        "head_pose": head_pose,
        "det_score": det_score
    }


def compute_eye_aspect_ratio(eye_landmarks):
    if len(eye_landmarks) < 6:
        return 0.0
    A = np.linalg.norm(np.array(eye_landmarks[1]) - np.array(eye_landmarks[5]))
    B = np.linalg.norm(np.array(eye_landmarks[2]) - np.array(eye_landmarks[4]))
    C = np.linalg.norm(np.array(eye_landmarks[0]) - np.array(eye_landmarks[3]))
    ear = (A + B) / (2.0 * C)
    return float(ear)


def validate_blink(landmarks_list):
    left_eye_indices = [36, 37, 38, 39, 40, 41]
    right_eye_indices = [42, 43, 44, 45, 46, 47]
    for landmarks in landmarks_list:
        if landmarks and len(landmarks) > 47:
            left_ear = compute_eye_aspect_ratio([landmarks[j] for j in left_eye_indices])
            right_ear = compute_eye_aspect_ratio([landmarks[j] for j in right_eye_indices])
            if left_ear < 0.18 and right_ear < 0.18:
                return True
    return False


def check_liveness_movement(bbox_history):
    non_none = [b for b in bbox_history if b]
    if len(non_none) < 5:
        return False
    movements = []
    for i in range(1, len(non_none)):
        dx = abs(non_none[i][0] - non_none[i-1][0])
        dy = abs(non_none[i][1] - non_none[i-1][1])
        movements.append(dx + dy)
    avg_movement = sum(movements) / len(movements)
    return avg_movement > 2.0


def check_liveness_head_pose(pose_history):
    non_none = [p for p in pose_history if p]
    if len(non_none) < 5:
        return False
    yaw_values = [p.get('yaw', 0) for p in non_none]
    yaw_range = max(yaw_values) - min(yaw_values)
    return yaw_range > 5.0


def process_frames_for_biometric_registration(frames_base64):
    embeddings = []
    bbox_history = []
    landmarks_list = []
    pose_history = []
    total_frames = len(frames_base64)

    for i, frame_b64 in enumerate(frames_base64):
        frame = decode_frame(frame_b64)
        if frame is None:
            continue

        extract_extra = (i % 2 == 0) or (i == total_frames - 1)
        embedding, bbox, extra = detect_and_extract(frame, extract_landmarks=extract_extra)

        if embedding is not None:
            if extract_extra:
                embeddings.append(embedding)
            bbox_history.append(bbox)
            if extra:
                landmarks_list.append(extra.get("landmarks"))
                pose_history.append(extra.get("head_pose"))

    if len(embeddings) < 3:
        return {"success": False, "error": f"Rosto detectado em apenas {len(embeddings)} de {total_frames} frames. Tente novamente com melhor iluminação."}

    has_blink = validate_blink(landmarks_list)
    has_movement = check_liveness_movement(bbox_history)
    head_movement = check_liveness_head_pose(pose_history)

    if not has_blink and not has_movement:
        return {"success": False, "error": "Nenhuma movimentação facial detectada. Pisque os olhos ou mova a cabeça durante a captura."}

    liveness_score = 0.0
    if has_blink:
        liveness_score += 0.5
    if has_movement:
        liveness_score += 0.25
    if head_movement:
        liveness_score += 0.25

    avg_embedding = np.mean(embeddings, axis=0).tolist()

    return {
        "success": True,
        "embedding": avg_embedding,
        "samples": len(embeddings),
        "liveness_score": liveness_score,
        "has_blink": has_blink,
        "has_movement": has_movement,
        "has_head_movement": head_movement
    }


def process_login_frame(frame_base64):
    frame = decode_frame(frame_base64)
    if frame is None:
        return {"success": False, "error": "Frame inválido."}
    embedding, bbox, extra = detect_and_extract(frame, extract_landmarks=False)
    if embedding is None:
        return {"success": False, "error": "Nenhum rosto detectado. Posicione seu rosto no centro."}
    return {
        "success": True,
        "embedding": embedding,
        "det_score": extra["det_score"] if extra else 1.0
    }


def compare_embeddings(login_embedding, stored_embedding):
    login_np = np.array(login_embedding).reshape(1, -1)
    stored_np = np.array(stored_embedding).reshape(1, -1)
    similarity = cosine_similarity(login_np, stored_np)[0][0]
    return float(similarity)


def match_face(login_embedding, stored_embeddings, threshold=None):
    if threshold is None:
        threshold = FACE_MATCH_THRESHOLD
    best_similarity = 0.0
    for stored in stored_embeddings:
        sim = compare_embeddings(login_embedding, stored)
        if sim > best_similarity:
            best_similarity = sim
    return {
        "match": best_similarity >= threshold,
        "similarity": best_similarity,
        "threshold": threshold
    }
