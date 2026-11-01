# 🧠 Samjhao Mujhe — Voice-First Doubt Solver for Bharat

> "Every Bloomberg terminal is in English. We built the one that speaks Hindi."

## What it does
Speak a JEE/NEET doubt in Hindi/Hinglish → get a simple explanation with an everyday analogy.

The app supports all 22 Indian constitutional languages plus English in the language selector and Saaras transcription. Text answers follow the selected language; Bulbul audio is available for its currently supported language set.

**Flow:** 🎙️ Saaras STT → 🧠 Sarvam 105B Conversations → 🔊 Bulbul TTS

## Setup
```bash
pip install -r requirements.txt
copy .env.example .env
# paste your key into .env
streamlit run app.py
```

## Deploy on Streamlit Cloud
1. Push to GitHub
2. Go to share.streamlit.io → New app
3. Add `SARVAM_API_KEY` in Secrets
4. Deploy!

## Sarvam APIs Used
- **Saaras v4** — optional Indic speech-to-text
- **Sarvam 105B Conversations** — final tutoring and explanation call
- **Bulbul v4 Flash** — optional Hindi text-to-speech

The app opens in local demo mode so UI work and rehearsals do not spend credits. Turn on **Live Sarvam mode** only for the final integrated demo.

## Run from a clean clone

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env
# Put SARVAM_API_KEY in .env, then:
streamlit run app.py
```

For Streamlit Cloud, add `SARVAM_API_KEY` under App Settings → Secrets. The app supports both local `.env` and Streamlit Secrets.

The repository must include `app.py`, `requirements.txt`, `.env.example`, and `README.md`. Never commit `.env` or Streamlit secrets.

