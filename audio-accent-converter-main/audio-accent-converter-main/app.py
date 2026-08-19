"""
Accent Conversion Tool - Flask Backend
Handles audio upload, accent simulation via DSP (pitch/formant shifting with Pydub + numpy),
and serves the converted audio back to the frontend.
"""

import os
import uuid
import numpy as np
from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
from pydub import AudioSegment
from pydub.effects import low_pass_filter, high_pass_filter
import io

app = Flask(__name__, static_folder="static")
CORS(app)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
OUTPUT_FOLDER = os.path.join(os.path.dirname(__file__), "outputs")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# ──────────────────────────────────────────────
# Accent profiles – each profile applies a chain
# of DSP effects to *simulate* an accent shift.
# ──────────────────────────────────────────────
ACCENT_PROFILES = {
    "american": {
        "label": "American English",
        "pitch_shift": 0,        # semitones
        "speed_factor": 1.0,
        "low_pass": 8000,
        "high_pass": 80,
        "eq_boost_hz": 2500,
        "eq_boost_db": 2,
    },
    "british": {
        "label": "British English",
        "pitch_shift": 1,
        "speed_factor": 0.97,
        "low_pass": 7500,
        "high_pass": 100,
        "eq_boost_hz": 3000,
        "eq_boost_db": 3,
    },
    "australian": {
        "label": "Australian English",
        "pitch_shift": -1,
        "speed_factor": 1.03,
        "low_pass": 7000,
        "high_pass": 90,
        "eq_boost_hz": 2000,
        "eq_boost_db": 2,
    },
    "indian": {
        "label": "Indian English",
        "pitch_shift": 2,
        "speed_factor": 0.95,
        "low_pass": 6500,
        "high_pass": 120,
        "eq_boost_hz": 3500,
        "eq_boost_db": 4,
    },
    "irish": {
        "label": "Irish English",
        "pitch_shift": 1,
        "speed_factor": 1.05,
        "low_pass": 7200,
        "high_pass": 85,
        "eq_boost_hz": 2800,
        "eq_boost_db": 3,
    },
    "southern_us": {
        "label": "Southern US",
        "pitch_shift": -2,
        "speed_factor": 0.92,
        "low_pass": 6800,
        "high_pass": 75,
        "eq_boost_hz": 2200,
        "eq_boost_db": 2,
    },
}


def _shift_pitch(audio: AudioSegment, semitones: int) -> AudioSegment:
    """Shift pitch by changing sample rate then resampling back."""
    if semitones == 0:
        return audio
    factor = 2 ** (semitones / 12.0)
    new_rate = int(audio.frame_rate * factor)
    shifted = audio._spawn(audio.raw_data, overrides={"frame_rate": new_rate})
    return shifted.set_frame_rate(audio.frame_rate)


def _change_speed(audio: AudioSegment, factor: float) -> AudioSegment:
    """Speed up / slow down without pitch correction."""
    if factor == 1.0:
        return audio
    new_rate = int(audio.frame_rate * factor)
    return audio._spawn(audio.raw_data, overrides={"frame_rate": new_rate}).set_frame_rate(audio.frame_rate)


def _eq_boost(audio: AudioSegment, center_hz: int, boost_db: int) -> AudioSegment:
    """Very simple EQ boost around a frequency band."""
    band = high_pass_filter(audio, center_hz - 500)
    band = low_pass_filter(band, center_hz + 500)
    boosted = audio.overlay(band + boost_db)
    return boosted


def convert_accent(audio: AudioSegment, target_accent: str) -> AudioSegment:
    """Apply DSP chain for the requested accent profile."""
    profile = ACCENT_PROFILES.get(target_accent)
    if not profile:
        return audio

    result = _shift_pitch(audio, profile["pitch_shift"])
    result = _change_speed(result, profile["speed_factor"])
    result = low_pass_filter(result, profile["low_pass"])
    result = high_pass_filter(result, profile["high_pass"])
    result = _eq_boost(result, profile["eq_boost_hz"], profile["eq_boost_db"])
    return result


def get_waveform_data(audio: AudioSegment, num_points: int = 200) -> list:
    """Return amplitude envelope for waveform visualisation."""
    samples = np.array(audio.get_array_of_samples(), dtype=np.float64)
    if audio.channels == 2:
        samples = samples[::2]
    chunk = max(1, len(samples) // num_points)
    peaks = []
    for i in range(0, len(samples), chunk):
        segment = samples[i:i + chunk]
        peaks.append(float(np.max(np.abs(segment))))
    max_peak = max(peaks) if peaks else 1
    return [round(p / max_peak, 4) for p in peaks]


# ───── Routes ─────

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/static/<path:path>")
def static_files(path):
    return send_from_directory("static", path)


@app.route("/api/accents", methods=["GET"])
def list_accents():
    return jsonify({k: v["label"] for k, v in ACCENT_PROFILES.items()})


@app.route("/api/upload", methods=["POST"])
def upload_audio():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    file = request.files["audio"]
    file_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename)[1] or ".wav"
    save_path = os.path.join(UPLOAD_FOLDER, f"{file_id}{ext}")
    file.save(save_path)

    try:
        audio = AudioSegment.from_file(save_path)
        waveform = get_waveform_data(audio)
        return jsonify({
            "file_id": file_id,
            "filename": file.filename,
            "duration": round(len(audio) / 1000, 2),
            "channels": audio.channels,
            "sample_rate": audio.frame_rate,
            "waveform": waveform,
            "ext": ext,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/convert", methods=["POST"])
def convert():
    data = request.json
    file_id = data.get("file_id")
    ext = data.get("ext", ".wav")
    target = data.get("target_accent", "british")

    src = os.path.join(UPLOAD_FOLDER, f"{file_id}{ext}")
    if not os.path.exists(src):
        return jsonify({"error": "File not found"}), 404

    try:
        audio = AudioSegment.from_file(src)
        converted = convert_accent(audio, target)
        out_id = str(uuid.uuid4())
        out_path = os.path.join(OUTPUT_FOLDER, f"{out_id}.wav")
        converted.export(out_path, format="wav")

        waveform = get_waveform_data(converted)
        return jsonify({
            "output_id": out_id,
            "duration": round(len(converted) / 1000, 2),
            "waveform": waveform,
            "accent": ACCENT_PROFILES[target]["label"],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/download/<output_id>", methods=["GET"])
def download(output_id):
    src_path = os.path.join(OUTPUT_FOLDER, f"{output_id}.wav")
    if not os.path.exists(src_path):
        return jsonify({"error": "Not found"}), 404

    fmt = request.args.get("format", "wav").lower()
    if fmt not in ("wav", "mp3", "ogg"):
        fmt = "wav"

    if fmt == "wav":
        return send_file(src_path, as_attachment=True, download_name="converted_audio.wav")

    # Convert to requested format on-the-fly
    audio = AudioSegment.from_wav(src_path)
    buf = io.BytesIO()
    audio.export(buf, format=fmt)
    buf.seek(0)
    mime = "audio/mpeg" if fmt == "mp3" else "audio/ogg"
    return send_file(buf, as_attachment=True, download_name=f"converted_audio.{fmt}", mimetype=mime)


@app.route("/api/preview/<file_id>", methods=["GET"])
def preview_original(file_id):
    for f in os.listdir(UPLOAD_FOLDER):
        if f.startswith(file_id):
            return send_file(os.path.join(UPLOAD_FOLDER, f), mimetype="audio/wav")
    return jsonify({"error": "Not found"}), 404


@app.route("/api/preview_output/<output_id>", methods=["GET"])
def preview_output(output_id):
    path = os.path.join(OUTPUT_FOLDER, f"{output_id}.wav")
    if not os.path.exists(path):
        return jsonify({"error": "Not found"}), 404
    return send_file(path, mimetype="audio/wav")


if __name__ == "__main__":
    app.run(debug=True, port=5000)
