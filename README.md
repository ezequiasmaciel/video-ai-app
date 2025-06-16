# 🎬 Pexels Video Maker

Gera automaticamente um vídeo `.mp4` a partir de um roteiro de texto.

## 🛠️ Recursos

- Divide o texto em cenas
- Extrai palavras-chave (com spaCy)
- Busca vídeos livres no [Pexels](https://www.pexels.com)
- Corta os clipes com MoviePy na duração estimada
- Concatena tudo num MP4 sem áudio

🎤 **Você adiciona a narração depois, com sua voz.**

---

## 🚀 Como usar localmente

```bash
git clone https://github.com/seu-usuario/pexels-video-maker.git
cd pexels-video-maker

python -m venv .venv
source .venv/bin/activate  # (Windows: .venv\Scripts\activate)

pip install -r requirements.txt
python -m spacy download pt_core_news_sm

cp .env.example .env
# edite o .env e insira sua chave do Pexels

streamlit run app.py
