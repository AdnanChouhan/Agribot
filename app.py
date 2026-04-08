import os
import streamlit as st # pyright: ignore[reportMissingImports]
import google.generativeai as genai # pyright: ignore[reportMissingImports]
from PIL import Image
from dotenv import load_dotenv # pyright: ignore[reportMissingImports]

load_dotenv()

API_KEY = "YOUR API KEY HERE"
DEFAULT_MODEL = "gemini-1.5-flash"

st.set_page_config(page_title="AgriBot", page_icon="🌱", layout="wide", initial_sidebar_state="collapsed")

try:
    with open("style.css", "r", encoding="utf-8") as stylesheet:
        st.markdown(f'<style>{stylesheet.read()}</style>', unsafe_allow_html=True)
except FileNotFoundError:
    pass

st.markdown("""
<div class="custom-header">
    <h1>🌱 AgriBot</h1>
    <p>AI-Based Plant Disease Detection</p>
</div>
""", unsafe_allow_html=True)

if not API_KEY:
    st.error("⚠️ System Error: GEMINI_API_KEY missing.")
    st.stop()

genai.configure(api_key=API_KEY)

@st.cache_data(ttl=3600)
def fetch_models():
    try:
        return [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    except Exception:
        return [DEFAULT_MODEL]

models = fetch_models()
idx = models.index(DEFAULT_MODEL) if DEFAULT_MODEL in models else 0

with st.sidebar:
    st.header("Settings")
    model_pref = st.selectbox("Choose Model", options=models, index=idx)
    lang_pref = st.selectbox("Language", options=["English", "Hindi", "Bengali", "Telugu", "Marathi"])

if ("chat_session" not in st.session_state or 
    st.session_state.get("current_model") != model_pref or 
    st.session_state.get("current_lang") != lang_pref):
    
    st.session_state.current_model = model_pref
    st.session_state.current_lang = lang_pref
    
    rules = f"""You are AgriBot. DIRECTIVE: 
    1. Communicate in {lang_pref} using extremely simple language for farmers. 
    2. Accept basic greetings politely. 
    3. ONLY answer agriculture, farming, crops, soil, and plant disease queries. Decline all others."""
    
    try:
        model = genai.GenerativeModel(model_pref, system_instruction=rules)
    except:
        model = genai.GenerativeModel(model_pref)
        
    st.session_state.chat_session = model.start_chat(history=[])
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg.get("image"):
            st.image(msg["image"], caption="Image Context", width=300)
        st.markdown(msg["content"])

st.markdown("---")
uploader_col, _ = st.columns([1.5, 5]) 

with uploader_col:
    img_file = st.file_uploader("📂 Target Image", type=["jpg", "jpeg", "png"], label_visibility="collapsed")

def send_prompt(prompt, img=None):
    with st.chat_message("assistant"):
        placeholder = st.empty()
        res_text = ""
        try:
            payload = [img, prompt] if img else prompt
            for chunk in st.session_state.chat_session.send_message(payload, stream=True):
                if chunk.text:
                    res_text += chunk.text
                    placeholder.markdown(res_text + "▌")
            placeholder.markdown(res_text)
            st.session_state.messages.append({"role": "assistant", "content": res_text})
        except Exception as e:
            st.error(f"Error: {e}")

if img_file and st.session_state.get("last_uploaded_image") != img_file.name:
    st.session_state.last_uploaded_image = img_file.name
    leaf_img = Image.open(img_file)
    p = "Analyze this crop image, state the disease, suggest treatments, and append your Prediction Accuracy % at the very end."
    
    st.session_state.messages.append({"role": "user", "content": p, "image": leaf_img})
    with st.chat_message("user"):
        st.image(leaf_img, caption="Image Context", width=300)
        st.markdown(p)
    send_prompt(p, leaf_img)
elif img_file and st.session_state.get("last_uploaded_image") == img_file.name:
    pass 
else:
    if "last_uploaded_image" in st.session_state:
        del st.session_state.last_uploaded_image

if not st.session_state.messages:
    st.markdown("### ✨ Try asking about:")
    cols = st.columns(3)
    prompts = [
        (" What soil is best for Rice?", "What soil conditions are best for Rice?"),
        (" Prevent Tomato Blight", "How to prevent early blight in tomatoes?"),
        (" Irrigation for Sugarcane", "What are sugarcane water requirements?")
    ]
    for col, (label, query) in zip(cols, prompts):
        with col:
            if st.button(label):
                st.session_state.messages.append({"role": "user", "content": query})
                st.rerun()

user_msg = st.chat_input("Ask a question about your crops...")
if user_msg:
    with st.chat_message("user"):
        st.markdown(user_msg)
    st.session_state.messages.append({"role": "user", "content": user_msg})
    send_prompt(user_msg)
