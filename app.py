import streamlit as st

st.set_page_config(
    page_title="Pro Consulting",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("💎 Pro Consulting")
st.subheader("Calcul des rémunérations")

st.success("L'application fonctionne correctement.")

st.write(
    "Cette première version servira à importer l'export Backstage "
    "et à calculer les rémunérations."
)
 
