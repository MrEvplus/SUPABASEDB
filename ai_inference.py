import streamlit as st
import pandas as pd
import requests
from utils import load_data_from_supabase

st.set_page_config(page_title="Domande AI", layout="wide")
st.title("🧠 Domande AI sul tuo Database")

HF_TOKEN = st.secrets["HUGGINGFACE_TOKEN"]
API_URL = "https://api-inference.huggingface.co/models/google/flan-t5-small"
HEADERS = {"Authorization": f"Bearer {HF_TOKEN}"}

def ask_huggingface(question, context):
    payload = {
        "inputs": f"Domanda: {question}\nContesto: {context[:3000]}"
    }
    response = requests.post(API_URL, headers=HEADERS, json=payload)
    try:
        return response.json()[0]['generated_text']
    except:
        return "⚠️ Errore nella risposta del modello Hugging Face."

df, campionato = load_data_from_supabase()
st.write(f"✅ Campionato selezionato: {campionato}")
st.write(f"📊 Partite disponibili: {df.shape[0]}")

question = st.text_input("✍️ Inserisci la tua domanda sul campionato:")
if question:
    with st.spinner("🤖 Sto elaborando la risposta con AI..."):
        context_text = df.head(100).to_string(index=False)
        risposta = ask_huggingface(question, context_text)
        st.success("✅ Risposta AI:")
        st.markdown(risposta)
