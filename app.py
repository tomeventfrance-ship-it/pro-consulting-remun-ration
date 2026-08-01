import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Pro Consulting",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialisation de la mémoire temporaire de l'application
if "backstage_data" not in st.session_state:
    st.session_state.backstage_data = None

if "backstage_filename" not in st.session_state:
    st.session_state.backstage_filename = None


# Menu principal
st.sidebar.title("💎 Pro Consulting")

page = st.sidebar.radio(
    "Navigation",
    [
        "🏠 Accueil",
        "📥 Import Backstage",
    ],
)


# PAGE ACCUEIL
if page == "🏠 Accueil":
    st.title("💎 Pro Consulting")
    st.subheader("Calcul des rémunérations")

    if st.session_state.backstage_data is None:
        st.info("Aucun export Backstage n'a encore été importé.")
    else:
        st.success(
            f"Export chargé : {st.session_state.backstage_filename}"
        )

        st.metric(
            "Nombre de créateurs importés",
            len(st.session_state.backstage_data),
        )

    st.write(
        "Utilisez le menu de gauche pour importer l'export Backstage."
    )


# PAGE IMPORT BACKSTAGE
elif page == "📥 Import Backstage":
    st.title("📥 Import Backstage")

    st.write(
        "Sélectionnez le fichier Excel téléchargé depuis le Backstage TikTok."
    )

    uploaded_file = st.file_uploader(
        "Choisir l'export Backstage",
        type=["xlsx"],
        help="Le fichier doit être au format Excel .xlsx",
    )

    if uploaded_file is not None:
        try:
            dataframe = pd.read_excel(
                uploaded_file,
                sheet_name=0,
            )

            # Enregistrement temporaire dans l'application
            st.session_state.backstage_data = dataframe
            st.session_state.backstage_filename = uploaded_file.name

            st.success("L'export Backstage a été lu correctement.")

            col1, col2, col3 = st.columns(3)

            col1.metric(
                "Nombre de lignes",
                len(dataframe),
            )

            col2.metric(
                "Nombre de colonnes",
                len(dataframe.columns),
            )

            col3.metric(
                "Fichier",
                uploaded_file.name,
            )

            st.subheader("Aperçu de l'export")

            st.dataframe(
                dataframe.head(20),
                use_container_width=True,
                hide_index=True,
            )

            with st.expander("Afficher les colonnes détectées"):
                for column in dataframe.columns:
                    st.write(f"• {column}")

        except Exception as error:
            st.error(
                "Impossible de lire ce fichier Excel."
            )

            st.code(str(error))
