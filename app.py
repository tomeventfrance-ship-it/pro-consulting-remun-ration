import pandas as pd
import streamlit as st

from utils import (
    calculate_creator_rewards,
    prepare_backstage_data,
)
st.set_page_config(
    page_title="Pro Consulting",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------------------------------
# MÉMOIRE TEMPORAIRE DE L’APPLICATION
# --------------------------------------------------

DEFAULT_VALUES = {
    "backstage_data": None,
    "backstage_filename": None,
    "month": "Août 2026",
    "creator_level": 9,
    "consultant_level": 9,
    "manager_level": 9,
    "director_level": 8,
    "revenue_usd": 0.0,
    "usd_to_eur": 0.92,
    "other_expenses": 0.0,
    "coin_pack_price": 11.30,
    "invoice_rate": 0.0084,
    "charges_rate": 24.6,
}

for key, default_value in DEFAULT_VALUES.items():
    if key not in st.session_state:
        st.session_state[key] = default_value


# --------------------------------------------------
# MENU PRINCIPAL
# --------------------------------------------------

st.sidebar.title("💎 Pro Consulting")

page = st.sidebar.radio(
    "Navigation",
    [
        "🏠 Accueil",
        "📥 Import Backstage",
        "⚙️ Paramètres",
        "💎 Créateurs",
    ],
)


# --------------------------------------------------
# PAGE ACCUEIL
# --------------------------------------------------

if page == "🏠 Accueil":
    st.title("💎 Pro Consulting")
    st.subheader("Calcul des rémunérations")

    if st.session_state.backstage_data is None:
        st.info("Aucun export Backstage n’a encore été importé.")
    else:
        st.success(
            f"Export chargé : {st.session_state.backstage_filename}"
        )

        st.metric(
            "Nombre de créateurs importés",
            len(st.session_state.backstage_data),
        )

    st.write(
        "Utilisez le menu de gauche pour importer l’export "
        "et renseigner les paramètres mensuels."
    )
# --------------------------------------------------
# PAGE IMPORT BACKSTAGE
# --------------------------------------------------

elif page == "📥 Import Backstage":
    st.title("📥 Import Backstage")

    st.write(
        "Sélectionnez le fichier Excel téléchargé depuis le Backstage TikTok."
    )

    uploaded_file = st.file_uploader(
        "Choisir l’export Backstage",
        type=["xlsx"],
        help="Le fichier doit être au format Excel .xlsx",
    )

    if uploaded_file is not None:
        try:
            raw_dataframe = pd.read_excel(
                uploaded_file,
                sheet_name=0,
            )

            prepared_dataframe, detected_columns = prepare_backstage_data(
                raw_dataframe
            )

            st.session_state.backstage_data = prepared_dataframe
            st.session_state.backstage_raw_data = raw_dataframe
            st.session_state.backstage_filename = uploaded_file.name
            st.session_state.detected_columns = detected_columns

            st.success(
                "L’export Backstage est valide et a été préparé correctement."
            )

            col1, col2, col3, col4 = st.columns(4)

            col1.metric(
                "Créateurs importés",
                len(prepared_dataframe),
            )

            col2.metric(
                "Diamants générés",
                f"{prepared_dataframe['Diamants'].sum():,.0f}",
            )

            col3.metric(
                "Total heures LIVE",
                f"{prepared_dataframe['Heures LIVE'].sum():,.1f} h",
            )

            col4.metric(
                "Colonnes détectées",
                len(detected_columns),
            )

            st.subheader("Données préparées")

            st.dataframe(
                prepared_dataframe.head(30),
                use_container_width=True,
                hide_index=True,
            )

            with st.expander(
                "Voir la correspondance des colonnes Backstage"
            ):
                for internal_name, original_name in detected_columns.items():
                    st.write(
                        f"**{internal_name}** → {original_name}"
                    )

        except ValueError as error:
            st.error(
                "L’export Backstage ne contient pas toutes les "
                "colonnes obligatoires."
            )
            st.code(str(error))

        except Exception as error:
            st.error(
                "Une erreur inattendue empêche la lecture du fichier."
            )
            st.code(str(error))
# --------------------------------------------------
# PAGE PARAMÈTRES
# --------------------------------------------------

elif page == "⚙️ Paramètres":
    st.title("⚙️ Paramètres mensuels")

    st.info(
        "Ces quatre paliers sont indépendants et doivent être "
        "sélectionnés chaque mois."
    )

    with st.form("monthly_settings"):
        st.subheader("Informations générales")

        column1, column2 = st.columns(2)

        with column1:
            month = st.text_input(
                "Mois analysé",
                value=st.session_state.month,
            )

            revenue_usd = st.number_input(
                "Chiffre d’affaires Backstage ($)",
                min_value=0.0,
                value=float(st.session_state.revenue_usd),
                step=100.0,
            )

            usd_to_eur = st.number_input(
                "Taux de conversion dollar → euro",
                min_value=0.0,
                value=float(st.session_state.usd_to_eur),
                step=0.01,
                format="%.4f",
            )

            other_expenses = st.number_input(
                "Autres dépenses (€)",
                min_value=0.0,
                value=float(st.session_state.other_expenses),
                step=10.0,
            )

        with column2:
            creator_level = st.selectbox(
                "Palier Créateurs atteint",
                options=[5, 7, 9, 13, 15],
                index=[5, 7, 9, 13, 15].index(
                    st.session_state.creator_level
                ),
                format_func=lambda value: f"{value} %",
            )

            consultant_level = st.selectbox(
                "Palier Consultants atteint",
                options=[5, 7, 9, 11, 13],
                index=[5, 7, 9, 11, 13].index(
                    st.session_state.consultant_level
                ),
                format_func=lambda value: f"{value} %",
            )

            manager_level = st.selectbox(
                "Palier Managers atteint",
                options=[5, 7, 9, 11, 13],
                index=[5, 7, 9, 11, 13].index(
                    st.session_state.manager_level
                ),
                format_func=lambda value: f"{value} %",
            )

            director_level = st.selectbox(
                "Palier Directeur atteint",
                options=[4, 5, 7, 8, 10, 11, 13],
                index=[4, 5, 7, 8, 10, 11, 13].index(
                    st.session_state.director_level
                ),
                format_func=lambda value: f"{value} %",
            )

        st.subheader("Paramètres financiers")

        column3, column4, column5 = st.columns(3)

        with column3:
            coin_pack_price = st.number_input(
                "Prix de 1 000 pièces TikTok (€)",
                min_value=0.0,
                value=float(st.session_state.coin_pack_price),
                step=0.10,
                format="%.2f",
            )

        with column4:
            invoice_rate = st.number_input(
                "Valeur facture par diamant (€)",
                min_value=0.0,
                value=float(st.session_state.invoice_rate),
                step=0.0001,
                format="%.4f",
            )

        with column5:
            charges_rate = st.number_input(
                "Charges sur le CA (%)",
                min_value=0.0,
                max_value=100.0,
                value=float(st.session_state.charges_rate),
                step=0.1,
                format="%.1f",
            )

        save_button = st.form_submit_button(
            "💾 Enregistrer les paramètres",
            type="primary",
            use_container_width=True,
        )

    if save_button:
        st.session_state.month = month
        st.session_state.creator_level = creator_level
        st.session_state.consultant_level = consultant_level
        st.session_state.manager_level = manager_level
        st.session_state.director_level = director_level
        st.session_state.revenue_usd = revenue_usd
        st.session_state.usd_to_eur = usd_to_eur
        st.session_state.other_expenses = other_expenses
        st.session_state.coin_pack_price = coin_pack_price
        st.session_state.invoice_rate = invoice_rate
        st.session_state.charges_rate = charges_rate

        st.success("Les paramètres mensuels ont été enregistrés.")

    st.divider()

    st.subheader("Récapitulatif actuel")

    summary1, summary2, summary3, summary4 = st.columns(4)

    summary1.metric(
        "Palier Créateurs",
        f"{st.session_state.creator_level} %",
    )

    summary2.metric(
        "Palier Consultants",
        f"{st.session_state.consultant_level} %",
    )

    summary3.metric(
        "Palier Managers",
        f"{st.session_state.manager_level} %",
    )

    summary4.metric(
        "Palier Directeur",
        f"{st.session_state.director_level} %",
    )
