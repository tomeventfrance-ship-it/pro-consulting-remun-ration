import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Pro Consulting",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Menu principal
st.sidebar.title("💎 Pro Consulting")

page = st.sidebar.radio(
    "Navigation",
    [
        "🏠 Accueil",
        "📥 Import Backstage",
    ],
)

# Page Accueil
if page == "🏠 Accueil":
    st.title("💎 Pro Consulting")
    st.subheader("Calcul des rémunérations")

    st.success("L'application fonctionne correctement.")

    st.write(
        "Cette application permettra d'importer l'export Backstage "
        "et de calculer les rémunérations automatiquement."
    )

# Page Import Backstage
elif page == "📥 Import Backstage":
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
