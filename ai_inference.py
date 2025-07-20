import streamlit as st
import pandas as pd
import requests

def run_ai_inference(df, db_selected):
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
        except Exception as e:
            return f"⚠️ Errore nella risposta del modello Hugging Face: {e}"

    st.write(f"📊 Campionato selezionato: **{db_selected}**")
    st.write(f"📁 Righe disponibili nel database: {df.shape[0]}")

    question = st.text_input("✍️ Inserisci la tua domanda sul campionato")

    if question:
        with st.spinner("🤖 Elaborazione della risposta..."):
            context = df.head(100).to_string(index=False)
            answer = ask_huggingface(question, context)
            st.success("✅ Risposta AI:")
            st.markdown(answer)
