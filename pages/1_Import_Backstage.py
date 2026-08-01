import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Import Backstage",
    page_icon="📥",
    layout="wide",
)

st.title("📥 Import Backstage")

st.write(
    "Importez ici le fichier Excel téléchargé depuis le Backstage TikTok."
)

uploaded_file = st.file_uploader(
    "Sélectionnez votre export Backstage",
    type=["xlsx", "xls"],
)

if uploaded_file is not None:
    st.success("Le fichier a bien été sélectionné.")
    st.write(f"Nom du fichier : **{uploaded_file.name}**")
