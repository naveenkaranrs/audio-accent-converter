/**
 * Accent Converter – Frontend Logic
 * Handles file upload, accent selection, conversion API calls,
 * waveform rendering, and audio playback.
 */

const API = "";

// ── State ──
let uploadedFile = null;
let fileId = null;
let fileExt = null;
let selectedAccent = null;
let outputId = null;

// ── DOM refs ──
const dropZone       = document.getElementById("dropZone");
const fileInput       = document.getElementById("audioFileInput");
const fileInfo        = document.getElementById("fileInfo");
const fileName        = document.getElementById("fileName");
const fileMeta        = document.getElementById("fileMeta");
const removeBtn       = document.getElementById("removeFile");
const waveOriginal    = document.getElementById("waveOriginal");
const waveformOrig    = document.getElementById("waveformOrig");
const accentGrid      = document.getElementById("accentGrid");
const convertBtn      = document.getElementById("convertBtn");
const loader          = document.getElementById("loader");
const resultSection   = document.getElementById("resultSection");
const origPlayer      = document.getElementById("origPlayer");
const convPlayer      = document.getElementById("convPlayer");
const waveConv        = document.getElementById("waveformConv");
const downloadBtn     = document.getElementById("downloadBtn");
const newBtn          = document.getElementById("newBtn");
const accentLabel     = document.getElementById("accentLabel");

// ── Accent flag mapping ──
const FLAGS = {
  american:    "🇺🇸",
  british:     "🇬🇧",
  australian:  "🇦🇺",
  indian:      "🇮🇳",
  irish:       "🇮🇪",
  southern_us: "🤠",
};

// ── Init ──
document.addEventListener("DOMContentLoaded", () => {
  loadAccents();
  createParticles();
  bindEvents();
});

function bindEvents() {
  dropZone.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", handleFileSelect);
  dropZone.addEventListener("dragover",  e => { e.preventDefault(); dropZone.classList.add("drag-over"); });
  dropZone.addEventListener("dragleave", () => dropZone.classList.remove("drag-over"));
  dropZone.addEventListener("drop", e => {
    e.preventDefault();
    dropZone.classList.remove("drag-over");
    if (e.dataTransfer.files.length) {
      fileInput.files = e.dataTransfer.files;
      handleFileSelect();
    }
  });
  removeBtn.addEventListener("click", resetUpload);
  convertBtn.addEventListener("click", startConversion);
  downloadBtn.addEventListener("click", downloadResult);
  newBtn.addEventListener("click", resetAll);
}

// ── Load accent options from backend ──
async function loadAccents() {
  try {
    const res = await fetch(`${API}/api/accents`);
    const data = await res.json();
    accentGrid.innerHTML = "";
    for (const [key, label] of Object.entries(data)) {
      const el = document.createElement("div");
      el.className = "accent-option";
      el.dataset.accent = key;
      el.innerHTML = `
        <div class="accent-option__flag">${FLAGS[key] || "🌍"}</div>
        <div class="accent-option__label">${label}</div>
        <div class="accent-option__check">✓</div>
      `;
      el.addEventListener("click", () => selectAccent(key, el));
      accentGrid.appendChild(el);
    }
  } catch {
    accentGrid.innerHTML = '<p style="color:var(--text-muted)">Could not load accents. Is the server running?</p>';
  }
}

function selectAccent(key, el) {
  document.querySelectorAll(".accent-option").forEach(o => o.classList.remove("selected"));
  el.classList.add("selected");
  selectedAccent = key;
  updateConvertBtn();
}

// ── File handling ──
async function handleFileSelect() {
  const file = fileInput.files[0];
  if (!file) return;
  uploadedFile = file;

  fileName.textContent = file.name;
  fileMeta.textContent = `${(file.size / 1024).toFixed(1)} KB`;
  fileInfo.classList.add("show");
  dropZone.style.display = "none";

  // Upload to server
  const form = new FormData();
  form.append("audio", file);
  try {
    const res = await fetch(`${API}/api/upload`, { method: "POST", body: form });
    const data = await res.json();
    if (data.error) { alert(data.error); return; }

    fileId = data.file_id;
    fileExt = data.ext;
    fileMeta.textContent = `${(file.size / 1024).toFixed(1)} KB · ${data.duration}s · ${data.sample_rate} Hz`;

    renderWaveform(waveformOrig, data.waveform, "var(--accent)");
    waveOriginal.classList.add("show");
  } catch (err) {
    alert("Upload failed – is the server running?");
    console.error(err);
  }
  updateConvertBtn();
}

function resetUpload() {
  uploadedFile = null; fileId = null; fileExt = null;
  fileInput.value = "";
  fileInfo.classList.remove("show");
  waveOriginal.classList.remove("show");
  dropZone.style.display = "";
  updateConvertBtn();
}

// ── Waveform rendering ──
function renderWaveform(container, data, color) {
  container.innerHTML = "";
  const max = Math.max(...data);
  data.forEach((v, i) => {
    const bar = document.createElement("div");
    bar.className = "waveform__bar";
    const h = Math.max(3, (v / max) * 100);
    bar.style.height = h + "%";
    bar.style.background = `linear-gradient(to top, ${color}, var(--purple))`;
    bar.style.animationDelay = `${i * 5}ms`;
    container.appendChild(bar);
  });
}

// ── Conversion ──
function updateConvertBtn() {
  convertBtn.disabled = !(fileId && selectedAccent);
}

async function startConversion() {
  if (!fileId || !selectedAccent) return;

  resultSection.classList.remove("show");
  loader.classList.add("show");
  convertBtn.disabled = true;

  try {
    const res = await fetch(`${API}/api/convert`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ file_id: fileId, ext: fileExt, target_accent: selectedAccent }),
    });
    const data = await res.json();
    loader.classList.remove("show");

    if (data.error) { alert(data.error); convertBtn.disabled = false; return; }

    outputId = data.output_id;
    accentLabel.textContent = data.accent;

    origPlayer.src = `${API}/api/preview/${fileId}`;
    convPlayer.src = `${API}/api/preview_output/${outputId}`;

    renderWaveform(waveConv, data.waveform, "var(--purple)");
    resultSection.classList.add("show");
    resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (err) {
    loader.classList.remove("show");
    alert("Conversion failed.");
    console.error(err);
  }
  convertBtn.disabled = false;
}

// ── Download ──
async function downloadResult() {
  if (!outputId) return;
  const fmt = document.getElementById("formatSelect").value;
  const url = `${API}/api/download/${outputId}?format=${fmt}`;
  try {
    downloadBtn.textContent = "⏳ Preparing…";
    downloadBtn.disabled = true;
    const res = await fetch(url);
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `converted_audio.${fmt}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(a.href);
  } catch (err) {
    alert("Download failed.");
    console.error(err);
  } finally {
    downloadBtn.textContent = "⬇ Download";
    downloadBtn.disabled = false;
  }
}

// ── Reset ──
function resetAll() {
  resetUpload();
  selectedAccent = null;
  outputId = null;
  document.querySelectorAll(".accent-option").forEach(o => o.classList.remove("selected"));
  resultSection.classList.remove("show");
  loader.classList.remove("show");
}

// ── Floating particles ──
function createParticles() {
  const container = document.getElementById("particles");
  for (let i = 0; i < 30; i++) {
    const p = document.createElement("div");
    p.className = "particle";
    p.style.left = Math.random() * 100 + "%";
    p.style.animationDelay = Math.random() * 8 + "s";
    p.style.animationDuration = 6 + Math.random() * 6 + "s";
    if (Math.random() > 0.5) p.style.background = "var(--purple)";
    container.appendChild(p);
  }
}
