import base64
import html
import io
import json
import os
import sys
import tempfile
import time
import zipfile
from pathlib import Path

import requests
import streamlit as st


VENDOR_PATH = Path(__file__).with_name("work") / "vendor"
if VENDOR_PATH.exists():
    sys.path.insert(0, str(VENDOR_PATH))


BASE_URL = "https://api.sarvam.ai"
ENV_PATH = Path(__file__).with_name(".env")
# Current supported replacements for the older IDs in the brief.
STT_MODEL = "saaras:v4"
LLM_MODEL = "sarvam-105b-conversations"
TTS_MODEL = "bulbul:v4-flash"
LANGUAGES = {
    "Hindi": "hi-IN", "Bengali": "bn-IN", "Tamil": "ta-IN", "Telugu": "te-IN",
    "Marathi": "mr-IN", "Gujarati": "gu-IN", "Kannada": "kn-IN", "Malayalam": "ml-IN",
    "Odia": "od-IN", "Punjabi": "pa-IN", "Assamese": "as-IN", "Bodo": "brx-IN",
    "Dogri": "doi-IN", "Kashmiri": "ks-IN", "Konkani": "kok-IN", "Maithili": "mai-IN",
    "Manipuri": "mni-IN", "Nepali": "ne-IN", "Sanskrit": "sa-IN", "Santali": "sat-IN",
    "Sindhi": "sd-IN", "Urdu": "ur-IN", "English": "en-IN",
}
TTS_LANGUAGES = {"hi-IN", "bn-IN", "ta-IN", "te-IN", "mr-IN", "gu-IN", "kn-IN", "ml-IN", "od-IN", "pa-IN", "en-IN"}


def load_local_env():
    if not ENV_PATH.exists():
        return
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            name, value = line.split("=", 1)
            os.environ.setdefault(name.strip(), value.strip().strip('"'))


load_local_env()


def get_api_key() -> str:
    key = os.getenv("SARVAM_API_KEY", "")
    if key:
        return key
    try:
        return st.secrets.get("SARVAM_API_KEY", "")
    except Exception:
        return ""


API_KEY = get_api_key()
st.set_page_config(page_title="Samjhao Mujhe", page_icon="🎓", layout="centered")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;600;700;800&display=swap');
:root { --ink:#19221c; --muted:#6a746d; --cream:#f8f5ed; --green:#185b46; --lime:#d9f277; --orange:#f28b54; }
.stApp { background:var(--cream); color:var(--ink); }
[data-testid="stHeader"] { background:transparent; }
.block-container { max-width:860px; padding:2.5rem 1.5rem 3rem; }
h1,h2,h3,p,span,label,button { font-family:Manrope,sans-serif; }
.hero { text-align:center; padding:1rem 0 1.5rem; }
.eyebrow { font:500 .72rem 'DM Mono',monospace; letter-spacing:.13em; color:var(--orange); text-transform:uppercase; }
.hero h1 { color:var(--green); font-size:clamp(2.4rem,8vw,4.6rem); line-height:1; letter-spacing:-.07em; margin:.6rem 0 .8rem; }
.hero p { color:var(--muted); font-size:1.05rem; line-height:1.6; margin:auto; max-width:600px; }
.tag { display:inline-block; border:1px solid #d6ddcf; border-radius:999px; padding:.35rem .7rem; margin:.8rem .2rem 0; font:500 .7rem 'DM Mono',monospace; color:var(--green); }
.card { background:#fffdf8; border:1px solid #e1e3da; border-radius:20px; padding:1.2rem 1.35rem; margin:1rem 0; }
.card-label { color:var(--orange); font:500 .7rem 'DM Mono',monospace; letter-spacing:.1em; text-transform:uppercase; }
.card-text { color:var(--ink); line-height:1.75; white-space:pre-wrap; margin-top:.45rem; }
.answer { background:var(--green); border:none; }
.answer .card-label { color:var(--lime); }
.answer .card-text { color:#f5f7ee; }
.note { background:#fff0df; border-left:4px solid var(--orange); border-radius:10px; padding:.75rem 1rem; color:#71411f; font-size:.88rem; margin-top:1rem; }
.stButton>button { background:#fffdf8; color:var(--green); border:1px solid #d6ddcf; border-radius:12px; font-weight:700; min-height:3rem; }
.stButton>button:hover { border-color:var(--green); color:var(--green); }
div[data-testid="stAudioInput"] { background:#fffdf8; border:1px solid #e1e3da; border-radius:16px; padding:.5rem; }
</style>
""", unsafe_allow_html=True)


def local_explanation(subject: str) -> str:
    examples = {
        "Physics": "Socho ek cricket ball ko tum bat se maarte ho. Uski velocity batati hai ki ball kitni tezi se aur kis direction mein ja rahi hai. Acceleration batata hai ki velocity kitni jaldi badal rahi hai. Yaad rakho: velocity motion ka status hai, acceleration us status ka change hai. Ab batao: agar car constant speed se seedhi chal rahi ho, to acceleration kya hoga?",
        "Chemistry": "Socho molecules ek busy kitchen mein ingredients jaise hain. Reaction tab hoti hai jab sahi ingredients sahi tarah milte hain. Catalyst ek helpful chef ki tarah reaction ko fast karta hai, lekin khud khatam nahi hota. Yaad rakho: catalyst activation energy kam karta hai. Ab batao: catalyst reaction ke end mein bachta hai ya consume ho jata hai?",
        "Math": "Socho trigonometry ek right triangle ka map hai. Sin opposite side ko hypotenuse se compare karta hai, cos adjacent side ko hypotenuse se, aur tan opposite ko adjacent se. Yaad rakho: SOH-CAH-TOA. Ab batao: agar angle aur hypotenuse pata ho, to kaunsi ratio useful hogi?",
        "Biology": "Socho cell ek chhota smart city hai. Nucleus uska control room hai, mitochondria power station hai, aur cell membrane security gate hai. Har organelle ka ek specific kaam hota hai. Yaad rakho: mitochondria energy banata hai. Ab batao: cell ka control room kaunsa organelle hai?",
    }
    return examples[subject]


def stt(audio_bytes: bytes, language_code: str) -> str:
    response = requests.post(f"{BASE_URL}/speech-to-text", headers={"api-subscription-key": API_KEY}, files={"file": ("doubt.wav", audio_bytes, "audio/wav")}, data={"model": STT_MODEL, "mode": "transcribe", "language_code": language_code}, timeout=60)
    response.raise_for_status()
    return response.json().get("transcript", "")


def explain(exam_name: str, subject: str, language_name: str, learning_mode: str, transcript: str) -> str:
    response = requests.post(
        f"{BASE_URL}/v1/chat/completions",
        headers={"api-subscription-key": API_KEY, "Content-Type": "application/json"},
        json={"model": LLM_MODEL, "messages": [
            {"role": "system", "content": f"You are a brilliant {subject} teacher for {exam_name} aspirants in India. Answer naturally in {language_name}, using its native script where appropriate. Learning mode: {learning_mode}. If the mode is Story se samjhao, start with a real-life analogy. If the mode is Exam ke steps, give a clear step-by-step method and a common mistake. If the mode is 30-second revision, give only the core idea, formula or memory trick, and one quick check question. Max 130 words. Be accurate, warm, and encouraging."},
            {"role": "user", "content": transcript},
        ], "max_tokens": 280, "temperature": 0.35},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def tts(text: str, language_code: str) -> bytes:
    response = requests.post(
        f"{BASE_URL}/text-to-speech",
        headers={"api-subscription-key": API_KEY, "Content-Type": "application/json"},
        json={"text": text[:2500], "language_code": language_code, "model": TTS_MODEL},
        timeout=60,
    )
    response.raise_for_status()
    return base64.b64decode(response.json()["audios"][0])


def parse_document(uploaded_file, language_code: str) -> str:
    from sarvamai import SarvamAI

    client = SarvamAI(api_subscription_key=API_KEY)
    job = client.doc_ai.parse(
        file=[(uploaded_file.name, uploaded_file, uploaded_file.type or "application/octet-stream")],
        language=language_code,
        output_format="md",
    )
    terminal = {"completed", "partially_completed", "failed", "rejected"}
    while True:
        status = client.doc_ai.get_status(job_id=job.job_id)
        if status.status.lower() in terminal:
            break
        time.sleep(3)
    if status.status.lower() not in {"completed", "partially_completed"}:
        raise RuntimeError(f"Document processing ended with status: {status.status}")
    download = client.doc_ai.get_download_url(job_id=job.job_id)
    archive = requests.get(download.url, timeout=60)
    archive.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(archive.content)) as bundle:
        markdown_name = next(name for name in bundle.namelist() if name.endswith(".md"))
        return bundle.read(markdown_name).decode("utf-8", errors="replace")


def transcribe_lecture(uploaded_file, language_code: str) -> str:
    from sarvamai import SarvamAI

    suffix = Path(uploaded_file.name).suffix or ".audio"
    with tempfile.TemporaryDirectory() as folder:
        audio_path = Path(folder) / f"lecture{suffix}"
        audio_path.write_bytes(uploaded_file.getvalue())
        client = SarvamAI(api_subscription_key=API_KEY)
        job = client.speech_to_text_job.create_job(model=STT_MODEL, mode="transcribe", language_code=language_code)
        job.upload_files(file_paths=[str(audio_path)])
        job.start()
        job.wait_until_complete(poll_interval=5, timeout=600)
        output_dir = Path(folder) / "output"
        output_dir.mkdir()
        job.download_outputs(output_dir=str(output_dir))
        for result_file in output_dir.glob("*.json"):
            data = json.loads(result_file.read_text(encoding="utf-8"))
            if data.get("transcript"):
                return data["transcript"]
        raise RuntimeError("Lecture transcript was empty")


st.markdown("""
<div class="hero">
  <div class="eyebrow">Voice-first learning for Bharat</div>
  <h1>Samjhao Mujhe 🎓</h1>
  <p>Apna doubt bolo. Ek story se samjho. Hindi mein yaad rakho.</p>
  <span class="tag">JEE + NEET</span><span class="tag">Hindi + Hinglish</span><span class="tag">Powered by Sarvam</span>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 🎓 Samjhao Mujhe")
    st.caption("Har doubt ka simple jawab.")
    st.divider()
    live_mode = st.toggle("Live Sarvam mode", value=False)
    st.info("Live mode off hai, taaki practice mein credits spend na hon. Final demo se pehle on karein.")
    st.divider()
    st.caption("A learning companion, not a replacement for your teacher.")

st.markdown("### 1. Apna exam choose karo")
exam_name = st.selectbox("Exam", ["JEE Main", "JEE Advanced", "NEET", "UPSC", "SSC CGL", "Banking (IBPS/SBI)", "CUET", "GATE", "State PSC", "Railways", "CAT", "Other competitive exam"], label_visibility="collapsed")
st.markdown("### 2. Subject choose karo")
subject = st.selectbox("Subject", ["Physics", "Chemistry", "Math", "Biology"], label_visibility="collapsed")
st.markdown("### 3. Bhasha choose karo")
language_name = st.selectbox("Language", list(LANGUAGES), index=0, label_visibility="collapsed")
language_code = LANGUAGES[language_name]
st.markdown("### 4. Kaise samajhna hai?")
learning_mode = st.selectbox("Learning mode", ["Story se samjhao", "Exam ke steps", "30-second revision"], label_visibility="collapsed")

examples = {
    "Physics": ["Velocity aur acceleration mein kya fark hai?", "Newton's third law ko simple example se samjhao."],
    "Chemistry": ["Catalyst reaction ko kaise fast karta hai?", "Mole concept ko kitchen example se batao."],
    "Math": ["Sin, cos aur tan kaise yaad rakhein?", "Quadratic equation ko graph se samjhao."],
    "Biology": ["Mitochondria ko powerhouse kyun kehte hain?", "Photosynthesis ko ek story se samjhao."],
}

st.markdown("### 5. Example doubt choose karo")
example_cols = st.columns(2)
for index, example in enumerate(examples[subject]):
    with example_cols[index]:
        if st.button(example, key=f"example_{subject}_{index}", use_container_width=True):
            st.session_state["doubt"] = example

st.markdown("### 6. Apna doubt bolo")
audio = st.audio_input("Mic se record karo") if live_mode else None
st.caption("Mic ke liye Live Sarvam mode on karein — ya neeche type karein.")
doubt = st.text_input("Text fallback", value=st.session_state.get("doubt", ""), placeholder="Ya yahan apna doubt type karo...", label_visibility="collapsed")
submit = st.button("✨ Samjhao Mujhe", type="primary", use_container_width=True)

if submit:
    if live_mode and not API_KEY:
        st.error(".env file mein SARVAM_API_KEY add karke Live Sarvam mode on karein.")
        st.stop()
    transcript = doubt.strip()
    if audio is not None:
        with st.spinner("Saaras aapki baat sun raha hai..."):
            try:
                transcript = stt(audio.getvalue(), language_code)
            except Exception as error:
                st.warning(f"Mic se transcript nahi mila: {error}")
    if not transcript:
        st.warning("Pehle doubt bolo ya type karo.")
        st.stop()
    if live_mode:
        with st.spinner("Sarvam teacher story bana raha hai..."):
            try:
                answer = explain(exam_name, subject, language_name, learning_mode, transcript)
            except Exception as error:
                st.error(f"Explanation request failed: {error}")
                st.stop()
    else:
        answer = local_explanation(subject)
    st.markdown(f'<div class="card"><div class="card-label">🎙️ Aapne poocha</div><div class="card-text">{html.escape(transcript)}</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="card answer"><div class="card-label">🧑‍🏫 Teacher ka jawab</div><div class="card-text">{html.escape(answer)}</div><div class="note">💡 Samajh na aaye toh isi topic par follow-up doubt poochho.</div></div>', unsafe_allow_html=True)
    if live_mode:
        with st.spinner("Bulbul jawab bol raha hai..."):
            try:
                if language_code not in TTS_LANGUAGES:
                    st.info("Is bhasha mein Saaras transcript aur text answer available hain; Bulbul voice support abhi selected languages tak hai.")
                else:
                    st.audio(tts(answer, language_code), format="audio/wav", autoplay=True)
            except Exception as error:
                st.warning(f"Audio answer unavailable: {error}")

st.divider()
st.markdown("### 📄 Learn from a PDF or picture")
st.caption("Upload a textbook page, handwritten question, diagram, or notes. Sarvam Vision will read it before the tutor explains it.")
document = st.file_uploader("Upload document", type=["pdf", "png", "jpg", "jpeg"], label_visibility="collapsed")
document_question = st.text_input("Document question", placeholder="Is page ko simple language mein samjhao...", label_visibility="collapsed")
learn_document = st.button("📚 Isse seekho", use_container_width=True)

if learn_document:
    if not document:
        st.warning("Pehle ek PDF ya picture upload karo.")
        st.stop()
    if not live_mode or not API_KEY:
        st.error("Document learning ke liye Live Sarvam mode on karo.")
        st.stop()
    with st.spinner("Sarvam Vision document padh raha hai..."):
        try:
            document_text = parse_document(document, language_code)
        except Exception as error:
            st.error(f"Document processing failed: {error}")
            st.stop()
    question = document_question.strip() or "Is document ko simple story aur key points ke saath samjhao."
    with st.spinner("Sarvam tutor is document ko samjha raha hai..."):
        try:
            answer = explain(exam_name, subject, language_name, learning_mode, f"DOCUMENT CONTENT:\n{document_text[:12000]}\n\nSTUDENT QUESTION:\n{question}")
        except Exception as error:
            st.error(f"Document explanation failed: {error}")
            st.stop()
    st.markdown(f'<div class="card"><div class="card-label">📄 Document se sawaal</div><div class="card-text">{html.escape(question)}</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="card answer"><div class="card-label">🧑‍🏫 Document tutor ka jawab</div><div class="card-text">{html.escape(answer)}</div></div>', unsafe_allow_html=True)
    if language_code in TTS_LANGUAGES:
        with st.spinner("Bulbul jawab bol raha hai..."):
            try:
                st.audio(tts(answer, language_code), format="audio/wav", autoplay=True)
            except Exception as error:
                st.warning(f"Audio answer unavailable: {error}")

st.divider()
st.markdown("### 🎧 Learn from a lecture")
st.caption("Upload a lecture audio file, then ask doubts directly against what was taught.")
lecture = st.file_uploader("Upload lecture audio", type=["wav", "mp3", "m4a", "aac", "ogg", "webm"], label_visibility="collapsed")
lecture_question = st.text_input("Lecture question", placeholder="Is lecture ka main concept kya tha?", label_visibility="collapsed")
ask_lecture = st.button("🎧 Transcribe lecture & ask", use_container_width=True)

if ask_lecture:
    if not lecture:
        st.warning("Pehle lecture audio upload karo.")
        st.stop()
    if not live_mode or not API_KEY:
        st.error("Lecture learning ke liye Live Sarvam mode on karo.")
        st.stop()
    with st.spinner("Saaras poora lecture transcribe kar raha hai..."):
        try:
            lecture_text = transcribe_lecture(lecture, language_code)
        except Exception as error:
            st.error(f"Lecture transcription failed: {error}")
            st.stop()
    st.markdown(f'<div class="card"><div class="card-label">🎧 Lecture transcript</div><div class="card-text">{html.escape(lecture_text[:6000])}</div></div>', unsafe_allow_html=True)
    question = lecture_question.strip() or "Is lecture ko simple points aur ek memory trick ke saath samjhao."
    with st.spinner("Sarvam tutor lecture se answer bana raha hai..."):
        try:
            answer = explain(exam_name, subject, language_name, learning_mode, f"LECTURE TRANSCRIPT:\n{lecture_text[:12000]}\n\nSTUDENT QUESTION:\n{question}")
        except Exception as error:
            st.error(f"Lecture explanation failed: {error}")
            st.stop()
    st.markdown(f'<div class="card answer"><div class="card-label">🧑‍🏫 Lecture tutor ka jawab</div><div class="card-text">{html.escape(answer)}</div></div>', unsafe_allow_html=True)
    if language_code in TTS_LANGUAGES:
        with st.spinner("Bulbul jawab bol raha hai..."):
            try:
                st.audio(tts(answer, language_code), format="audio/wav", autoplay=True)
            except Exception as error:
                st.warning(f"Audio answer unavailable: {error}")

st.markdown("<br><hr><p style='text-align:center;color:#7b847c;font:500 .72rem DM Mono,monospace'>2 MILLION JEE STUDENTS THINK IN HINDI · EVERY DOUBT DESERVES A SIMPLE ANSWER</p>", unsafe_allow_html=True)

