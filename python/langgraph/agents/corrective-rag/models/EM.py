from langchain_google_genai.embeddings import GoogleGenerativeAIEmbeddings
import streamlit as st

embedding = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001", google_api_key=st.secrets["GEMINI-API-KEY"]
)
