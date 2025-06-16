import os, re, tempfile, requests, streamlit as st
from moviepy.editor import VideoFileClip, concatenate_videoclips
from pathlib import Path
import spacy
from dotenv import load_dotenv

# ---------------- Configurações ---------------- #
WORDS_PER_SEC   = 2.5          # ~150 wpm
MAX_RESULTS     = 1            # Vídeos por cena
HD_ONLY         = True         # Preferir arquivos HD
MIN_SECONDS     = 2            # Trecho mínimo
# ------------------------------------------------ #

# Carrega variáveis do .env (PEXELS_API_KEY)
load_dotenv()
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")

# ---------- Interface Streamlit ---------- #
st.set_page_config(page_title="Gerador de Vídeo • Pexels", page_icon="🎬")
st.title("🎬 Gerador de Vídeo (Pexels + MoviePy)")
st.markdown(
"""
Cole seu roteiro abaixo (separe cenas por linha em branco ou prefixo **Cena:**),
defina a velocidade da narração (palavras/min), clique **Gerar vídeo** e aguarde.
"""
)

script_text = st.text_area("✏️  Roteiro", height=300)
cols = st.columns(2)
wpm  = cols[0].number_input("Palavras por minuto", 100, 250, 150, 10)
generate_btn = cols[1].button("🚀 Gerar vídeo")

# ------------- Funções utilitárias ------------- #
@st.cache_resource(show_spinner=False)
def load_nlp():
    """Carrega o modelo spaCy. Faz download se necessário."""
    try:
        return spacy.load("pt_core_news_sm")
    except OSError:
        from spacy.cli import download
        download("pt_core_news_sm")
        return spacy.load("pt_core_news_sm")

def split_script(text: str):
    """Divide em blocos por linha em branco ou 'Cena:'."""
    parts = re.split(r"\n\s*\n|(?:^|\n)Cena\s*[:\-]", text, flags=re.I)
    return [p.strip() for p in parts if p.strip()]

def extract_keywords(block: str, n=3):
    """Extrai até n substantivos ou próprios para a busca."""
    nlp = load_nlp()
    doc = nlp(block)
    tokens = [t.text for t in doc if t.pos_ in {"NOUN", "PROPN"} and not t.is_stop]
    return " ".join(tokens[:n]) or " ".join(block.split()[:3])

def estimate_seconds(block: str, wpm: int):
    """Estimativa da duração da narração."""
    words = len(block.split())
    return max(MIN_SECONDS, int(words / (wpm / 60.0)))

def pexels_search(query):
    """Faz a busca de vídeos no Pexels."""
    if not PEXELS_API_KEY:
        st.error("⚠️ Defina PEXELS_API_KEY no .env ou variável de ambiente.")
        return []
    url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": PEXELS_API_KEY}
    params = {"query": query, "per_page": MAX_RESULTS}
    res = requests.get(url, headers=headers, params=params, timeout=20)
    res.raise_for_status()
    return res.json().get("videos", [])

def best_video_link(video_json):
    """Escolhe o melhor arquivo (HD se possível)."""
    files = sorted(video_json["video_files"], key=lambda f: f["height"], reverse=True)
    if HD_ONLY:
        files = [f for f in files if f["quality"] == "hd"] or files
    return files[0]["link"] if files else None

def download_video(url, out_path):
    """Baixa o vídeo com barra de progresso."""
    r = requests.get(url, stream=True, timeout=20)
    r.raise_for_status()
    total = int(r.headers.get("content-length", 0)) or None
    progress = st.progress(0)
    bytes_dl = 0
    with open(out_path, "wb") as f:
        for chunk in r.iter_content(8192):
            if chunk:
                f.write(chunk)
                bytes_dl += len(chunk)
                if total:
                    progress.progress(min(bytes_dl / total, 1.0))
    progress.empty()

def make_clip(path, duration):
    """Corta o início do vídeo no tamanho desejado."""
    clip = VideoFileClip(path)
    return clip.subclip(0, min(duration, clip.duration))

# ------------- Pipeline principal ------------- #
def process_scene(block, wpm, tmp_dir):
    query    = extract_keywords(block)
    duration = estimate_seconds(block, wpm)
    videos   = pexels_search(query)
    if not videos:
        st.error(f"Nenhum resultado para **{query}**")
        return None
    link = best_video_link(videos[0])
    if not link:
        st.error(f"Sem arquivo HD para **{query}**")
        return None
    local_path = Path(tmp_dir) / f"{videos[0]['id']}.mp4"
    download_video(link, local_path)
    return make_clip(local_path, duration)

def build_video(blocks, wpm):
    clips = []
    with tempfile.TemporaryDirectory() as tmp:
        for idx, block in enumerate(blocks, 1):
            st.write(f"Cena {idx}: _{extract_keywords(block)}_")
            clip = process_scene(block, wpm, tmp)
            if clip:
                clips.append(clip)
    if not clips:
        return None
    final = concatenate_videoclips(clips, method="compose")
    out_path = Path(tempfile.gettempdir()) / "roteiro_final.mp4"
    final.write_videofile(out_path, codec="libx264", fps=24, audio=False)
    return out_path

# ------------- Execução ------------- #
if generate_btn and script_text:
    with st.spinner("⏳ Gerando vídeo…"):
        scenes = split_script(script_text)
        st.success(f"{len(scenes)} cena(s) detectada(s).")
        video_path = build_video(scenes, wpm)
    if video_path and video_path.exists():
        st.video(str(video_path))
        with open(video_path, "rb") as f:
            st.download_button("📥 Baixar MP4", f, file_name="roteiro_final.mp4")
