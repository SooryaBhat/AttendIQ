# Voice register & match service (placeholder)
# ============================================================
#  AttendIQ — Voice Enrollment Service
#  File: backend/app/services/voice_service.py
#
#  Stack:  SpeechBrain (ECAPA-TDNN) + torchaudio + librosa
#  NO resemblyzer, NO webrtcvad — Windows-compatible only.
#
#  Model:  speechbrain/spkrec-ecapa-voxceleb
#          Architecture : ECAPA-TDNN
#          Output       : 192-dimensional L2-normalised embedding
#          Input        : 16 kHz mono float32 waveform
#
#  Pipeline:
#    1. Write audio bytes to a temp file
#    2. Load + resample to 16 kHz mono via torchaudio (primary)
#       with librosa as fallback for exotic formats
#    3. Validate duration and amplitude
#    4. Feed waveform to SpeechBrain EncoderClassifier.encode_batch()
#    5. Squeeze tensor → numpy float32 array (192,)
#    6. Serialize → JSON string
#    7. Upsert into biometric_enrollments (type="voice")
#    8. Set profiles.voice_enrolled = TRUE
# ============================================================

import json
import logging
import os
import tempfile
from uuid import uuid4

import librosa
import numpy as np
import torch
import torchaudio

from app.config import settings
from app.db.supabase_client import supabase
from app.models.biometric import VoiceEnrollResponse

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────

_MODEL_SOURCE    = "speechbrain/spkrec-ecapa-voxceleb"
_MODEL_SAVEDIR   = "pretrained_models/spkrec-ecapa-voxceleb"
_MODEL_VERSION   = "speechbrain_ecapa_tdnn_v1"
_TARGET_SR       = 16_000       # ECAPA-TDNN requires exactly 16 kHz
_EMBEDDING_SIZE  = 192          # ECAPA-TDNN lin_neurons=192 (verified from source)
_MIN_DURATION_S  = 2.0          # minimum speech for reliable embedding
_MAX_DURATION_S  = 60.0         # reject unreasonably long files

ALLOWED_AUDIO_TYPES = {
    "audio/wav",
    "audio/wave",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp3",
    "audio/ogg",
    "audio/flac",
    "audio/x-flac",
    "audio/webm",
}

# ── Model singleton ───────────────────────────────────────────
# EncoderClassifier is loaded once per process.
# First call downloads ~100 MB of weights from HuggingFace Hub
# and caches them in _MODEL_SAVEDIR. Subsequent starts are instant.

_encoder = None


def _get_encoder():
    """
    Lazily load the SpeechBrain ECAPA-TDNN speaker encoder.
    Singleton — loaded once per process lifetime.
    """
    global _encoder
    if _encoder is None:
        from speechbrain.inference.speaker import EncoderClassifier
        from speechbrain.utils.fetching import LocalStrategy

        logger.info(
            "Loading SpeechBrain ECAPA-TDNN model from '%s' "
            "(first call downloads ~100 MB — cached after that)...",
            _MODEL_SOURCE,
        )

        # Disable the HF symlink warning on Windows and force local copy usage.
        os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
        os.makedirs(_MODEL_SAVEDIR, exist_ok=True)

        _encoder = EncoderClassifier.from_hparams(
            source=_MODEL_SOURCE,
            savedir=_MODEL_SAVEDIR,
            run_opts={"device": "cpu"},   # CPU for Windows compatibility
            local_strategy=LocalStrategy.COPY_SKIP_CACHE,
        )
        logger.info("SpeechBrain ECAPA-TDNN model loaded.")
    return _encoder


# ── Audio loading ─────────────────────────────────────────────

def _load_audio_torchaudio(path: str) -> torch.Tensor:
    """
    Load audio with torchaudio, resample to 16 kHz mono.
    Returns: float32 tensor shape (samples,)
    """
    waveform, sr = torchaudio.load(path)

    # Convert to mono by averaging channels
    if waveform.shape[0] > 1:
        waveform = waveform.mean(dim=0, keepdim=True)

    # Resample if needed
    if sr != _TARGET_SR:
        resampler = torchaudio.transforms.Resample(orig_freq=sr, new_freq=_TARGET_SR)
        waveform = resampler(waveform)

    return waveform.squeeze(0)   # (samples,)


def _load_audio_librosa_fallback(path: str) -> torch.Tensor:
    """
    Fallback loader using librosa — handles more exotic formats.
    Returns: float32 tensor shape (samples,)
    """
    wav, _ = librosa.load(path, sr=_TARGET_SR, mono=True, dtype=np.float32)
    return torch.from_numpy(wav)


def _load_audio(audio_bytes: bytes, original_filename: str) -> torch.Tensor:
    """
    Write bytes to a temp file, load with torchaudio (fallback: librosa).
    Validates duration and amplitude.

    Returns:
        torch.Tensor: float32, shape (n_samples,), 16 kHz mono

    Raises:
        ValueError: Bad format, too short, too long, silent.
    """
    suffix = os.path.splitext(original_filename)[-1].lower() or ".wav"

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        try:
            wav_tensor = _load_audio_torchaudio(tmp_path)
            logger.debug("Loaded audio via torchaudio")
        except Exception as ta_err:
            logger.debug("torchaudio failed (%s), trying librosa fallback", ta_err)
            try:
                wav_tensor = _load_audio_librosa_fallback(tmp_path)
                logger.debug("Loaded audio via librosa fallback")
            except Exception as lb_err:
                raise ValueError(
                    f"Could not decode audio file '{original_filename}'. "
                    f"Accepted formats: WAV, MP3, OGG, FLAC. "
                    f"Detail: {lb_err}"
                ) from lb_err
    finally:
        os.unlink(tmp_path)

    # ── Duration validation ───────────────────────────────────
    duration_s = len(wav_tensor) / _TARGET_SR
    logger.debug("Audio: %.2f s, %d samples", duration_s, len(wav_tensor))

    if duration_s < _MIN_DURATION_S:
        raise ValueError(
            f"Recording is too short ({duration_s:.1f}s). "
            f"Please record at least {int(_MIN_DURATION_S)} seconds of clear speech."
        )
    if duration_s > _MAX_DURATION_S:
        raise ValueError(
            f"Recording is too long ({duration_s:.1f}s). "
            f"Maximum allowed is {int(_MAX_DURATION_S)} seconds."
        )

    # ── Silence check ─────────────────────────────────────────
    rms = float(wav_tensor.pow(2).mean().sqrt())
    logger.debug("Audio RMS: %.6f", rms)
    if rms < 1e-4:
        raise ValueError(
            "Recording appears to be silent. "
            "Please record in a quiet room and speak clearly into the microphone."
        )

    return wav_tensor


# ── Embedding generation ──────────────────────────────────────

def _generate_embedding(wav_tensor: torch.Tensor) -> np.ndarray:
    """
    Run ECAPA-TDNN to produce a 192-d speaker embedding.

    SpeechBrain encode_batch expects:
        wavs     : Tensor shape [batch, time]
        wav_lens : Tensor shape [batch]  — relative lengths (1.0 = full)

    Returns:
        np.ndarray: float32, shape (192,)
    """
    encoder = _get_encoder()

    # Add batch dimension: (samples,) → (1, samples)
    wavs = wav_tensor.unsqueeze(0)                    # [1, samples]
    wav_lens = torch.tensor([1.0])                    # full length

    with torch.no_grad():
        embeddings = encoder.encode_batch(wavs, wav_lens)   # [1, 1, 192]

    # Squeeze all batch/frame dims → (192,)
    vec: np.ndarray = embeddings.squeeze().cpu().numpy().astype(np.float32)

    if vec.shape != (_EMBEDDING_SIZE,):
        raise RuntimeError(
            f"Unexpected embedding shape {vec.shape}. "
            f"Expected ({_EMBEDDING_SIZE},). "
            f"Check model compatibility."
        )

    logger.debug(
        "Voice embedding: shape=%s norm=%.4f",
        vec.shape, float(np.linalg.norm(vec)),
    )
    return vec

def load_all_voice_encodings() -> list[dict]:
    """Load all active voice embeddings from biometric_enrollments."""
    resp = (
        supabase.table("biometric_enrollments")
        .select("student_id, encoding")
        .eq("type", "voice")
        .eq("is_active", True)
        .execute()
    )

    result = []
    for row in (resp.data or []):
        try:
            vec = np.array(json.loads(row["encoding"]), dtype=np.float32)
            result.append({"student_id": row["student_id"], "encoding": vec})
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(
                "Skipping corrupted voice encoding for student %s: %s",
                row["student_id"], e,
            )

    logger.debug("Loaded %d voice encodings", len(result))
    return result


def recognize_voice(audio_bytes: bytes, original_filename: str = "recording.wav") -> dict:
    """Recognize a voice recording against enrolled voice embeddings."""
    wav_tensor = _load_audio(audio_bytes, original_filename)
    query_embedding = _generate_embedding(wav_tensor)

    enrolled = load_all_voice_encodings()
    if not enrolled:
        return {"matched": False}

    embeddings = np.vstack([row["encoding"] for row in enrolled])
    # Embeddings are L2-normalized, so dot product is cosine similarity.
    similarities = embeddings.dot(query_embedding.astype(np.float32))
    best_index = int(np.argmax(similarities))
    best_score = float(similarities[best_index])

    if best_score >= 0.75:
        student_id = enrolled[best_index]["student_id"]
        return {
            "matched": True,
            "student_id": student_id,
            "confidence": round(best_score, 4),
        }

    return {"matched": False}

# ── File persistence ──────────────────────────────────────────

def _save_audio_file(audio_bytes: bytes, student_id: str, suffix: str) -> str:
    """Save raw audio to uploads/audio/ for audit. Returns file path."""
    upload_dir = settings.UPLOAD_DIR_AUDIO
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"{student_id}_voice{suffix}"
    path = os.path.join(upload_dir, filename)
    with open(path, "wb") as f:
        f.write(audio_bytes)
    return path


# ── Main service function ─────────────────────────────────────

def enroll_voice(
    student_id: str,
    audio_bytes: bytes,
    original_filename: str = "recording.wav",
) -> VoiceEnrollResponse:
    """
    Full voice enrollment pipeline.

    Args:
        student_id:        UUID string of the student.
        audio_bytes:       Raw bytes of the uploaded audio file.
        original_filename: Used to detect format suffix for temp file.

    Returns:
        VoiceEnrollResponse

    Raises:
        ValueError:   Student not found, bad audio, too short, silent.
        RuntimeError: DB write failure.
    """

    # ── Step 1: Validate student ──────────────────────────────
    profile_resp = (
        supabase.table("profiles")
        .select("id, full_name, role, voice_enrolled")
        .eq("id", student_id)
        .eq("role", "student")
        .single()
        .execute()
    )
    if not profile_resp.data:
        raise ValueError(f"Student with id '{student_id}' not found.")

    student = profile_resp.data
    logger.info(
        "Voice enrollment started — student: %s (%s)",
        student.get("full_name"), student_id,
    )

    # ── Step 2: Load and validate audio ──────────────────────
    wav_tensor = _load_audio(audio_bytes, original_filename)

    # ── Step 3: Generate 192-d ECAPA-TDNN embedding ───────────
    embedding: np.ndarray = _generate_embedding(wav_tensor)
    embedding_size = len(embedding)   # 192

    # ── Step 4: Serialize → JSON string ───────────────────────
    # float32 list → JSON TEXT → stored in biometric_enrollments.encoding
    # Loaded back via: np.array(json.loads(row["encoding"]), dtype=np.float32)
    embedding_json: str = json.dumps(embedding.tolist())

    # ── Step 5: Save audio file for audit ─────────────────────
    suffix = os.path.splitext(original_filename)[-1].lower() or ".wav"
    file_path = _save_audio_file(audio_bytes, student_id, suffix)

    # ── Step 6: Upsert biometric_enrollments ──────────────────
    # UNIQUE(student_id, type) in schema → upsert replaces on re-enrollment
    enrollment_row = {
        "id":            str(uuid4()),
        "student_id":    student_id,
        "type":          "voice",
        "encoding":      embedding_json,
        "file_path":     file_path,
        "model_version": _MODEL_VERSION,
        "is_active":     True,
    }

    upsert_resp = (
        supabase.table("biometric_enrollments")
        .upsert(enrollment_row, on_conflict="student_id,type")
        .execute()
    )

    if not upsert_resp.data:
        logger.error(
            "biometric_enrollments upsert returned no data for student %s", student_id
        )
        raise RuntimeError(
            "Voice embedding was computed but could not be saved. "
            "Check Supabase RLS policies on biometric_enrollments."
        )

    saved = upsert_resp.data[0] if isinstance(upsert_resp.data, list) else upsert_resp.data
    logger.info(
        "Voice enrollment record saved — student %s, enrollment_id=%s",
        student_id, saved.get("id", "?"),
    )

    # ── Step 7: Flip voice_enrolled flag on profile ───────────
    supabase.table("profiles").update(
        {"voice_enrolled": True}
    ).eq("id", student_id).execute()

    logger.info("voice_enrolled=TRUE set on profile for student %s", student_id)

    return VoiceEnrollResponse(
        success=True,
        student_id=student_id,
        embedding_size=embedding_size,
        message=f"Voice enrolled successfully for {student.get('full_name', student_id)}.",
    )


# ── Utility: load all voice encodings (used by attendance AI) ─

def load_all_voice_encodings(department_id: str | None = None) -> list[dict]:
    """
    Load all active voice encodings from biometric_enrollments.
    Optionally filter by department.

    Returns:
        [{"student_id": "...", "encoding": np.ndarray(192,)}, ...]

    Used by the voice attendance recognition pipeline.
    Cosine similarity against _VOICE_MATCH_THRESHOLD in config.
    """
    if department_id:
        profiles_resp = (
            supabase.table("profiles")
            .select("id")
            .eq("role", "student")
            .eq("department_id", department_id)
            .execute()
        )
        student_ids = [p["id"] for p in (profiles_resp.data or [])]
        if not student_ids:
            return []

        resp = (
            supabase.table("biometric_enrollments")
            .select("student_id, encoding")
            .eq("type", "voice")
            .eq("is_active", True)
            .in_("student_id", student_ids)
            .execute()
        )
    else:
        resp = (
            supabase.table("biometric_enrollments")
            .select("student_id, encoding")
            .eq("type", "voice")
            .eq("is_active", True)
            .execute()
        )

    result = []
    for row in (resp.data or []):
        try:
            vec = np.array(json.loads(row["encoding"]), dtype=np.float32)
            if vec.shape == (_EMBEDDING_SIZE,):
                result.append({"student_id": row["student_id"], "encoding": vec})
            else:
                logger.warning(
                    "Skipping voice encoding — unexpected shape %s for student %s",
                    vec.shape, row["student_id"],
                )
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning(
                "Skipping corrupted voice encoding for student %s: %s",
                row["student_id"], exc,
            )

    logger.debug("Loaded %d voice encodings", len(result))
    return result