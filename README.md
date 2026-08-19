# Audio Accent Converter & DSP Web Tool 🎙️🔊

An interactive audio processing tool and Flask web application that applies Digital Signal Processing (DSP) algorithms—including pitch shifting, formant adjustment, cutoff filtering, and equalization—to simulate speech accent variations in real-time audio clips.

---

## 🌟 Key Features

- **DSP Accent Profiles**: Configurable audio filter pipelines for American English, British English, Indian English, Australian English, French, and Spanish speech characteristics.
- **Audio Processing Engine**: Powered by `Pydub` and `NumPy` for low-pass/high-pass filtering, dynamic gain adjustment, frequency EQ boosting, and pitch manipulation.
- **RESTful API Backend**: Flask framework with `flask-cors` exposing endpoints for audio file upload, accent transformation, and audio stream playback.
- **Web Audio Interface**: Dynamic web UI allowing users to upload speech samples, apply accent profiles, and preview transformed audio side-by-side.

---

## 📁 Repository Structure

```
accent-converter/
├── app.py              # Flask server and DSP audio conversion engine
├── requirements.txt    # Python package dependencies
├── static/             # Frontend HTML/CSS/JS web dashboard interface
├── uploads/            # Temporary storage for uploaded raw audio clips
└── outputs/            # Processed converted audio exports
```

---

## 📦 Requirements & Setup

1. **Prerequisites**: Python 3.9+ and `FFmpeg` installed on system PATH (required by Pydub).

2. **Installation**:
   ```bash
   git clone https://github.com/harishkumaran2005/audio-accent-converter.git
   cd audio-accent-converter
   pip install -r requirements.txt
   ```

3. **Run Application**:
   ```bash
   python app.py
   ```
   Open your browser at `http://localhost:5000`.

---

## 📄 License
This project is open-source under the [MIT License](LICENSE).
