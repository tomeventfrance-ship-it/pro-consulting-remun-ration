import pandas as pd
import streamlit as st

from utils import (
    calculate_consultant_rewards,
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
    "backstage_raw_data": None,
    "backstage_filename": None,
    "detected_columns": None,
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


def clear_calculation_cache() -> None:
    """Supprime les anciens calculs après un nouvel import ou un changement de palier."""
    keys_to_clear = [
        "creator_results",
        "creator_signature",
        "consultant_results",
        "consultant_signature",
        "creator_payment_editor",
        "consultant_payment_editor",
    ]

    for key in keys_to_clear:
        st.session_state.pop(key, None)


def ensure_creator_results() -> pd.DataFrame:
    """Calcule ou récupère les résultats créateurs à jour."""
    creator_signature = (
        st.session_state.backstage_filename,
        int(st.session_state.creator_level),
    )

    if (
        "creator_results" not in st.session_state
        or st.session_state.get("creator_signature") != creator_signature
    ):
        creator_results = calculate_creator_rewards(
            st.session_state.backstage_data,
            int(st.session_state.creator_level),
        )

        creator_results["Mode paiement"] = "Diamants"

        st.session_state.creator_results = creator_results
        st.session_state.creator_signature = creator_signature

    return st.session_state.creator_results.copy()


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
        "👥 Consultants",
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

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Créateurs importés",
            len(st.session_state.backstage_data),
        )

        col2.metric(
            "Diamants générés",
            f"{st.session_state.backstage_data['Diamants'].sum():,.0f} 💎",
        )

        col3.metric(
            "Mois analysé",
            st.session_state.month,
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

    if st.session_state.backstage_data is not None:
        st.success(
            f"Export actuellement chargé : "
            f"{st.session_state.backstage_filename}"
        )

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

            is_new_file = (
                st.session_state.backstage_filename != uploaded_file.name
            )

            st.session_state.backstage_data = prepared_dataframe
            st.session_state.backstage_raw_data = raw_dataframe
            st.session_state.backstage_filename = uploaded_file.name
            st.session_state.detected_columns = detected_columns

            if is_new_file:
                clear_calculation_cache()

            st.success(
                "L’export Backstage est valide et a été préparé correctement."
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

    if st.session_state.backstage_data is not None:
        prepared_dataframe = st.session_state.backstage_data
        detected_columns = st.session_state.detected_columns or {}

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


# --------------------------------------------------
# PAGE PARAMÈTRES
# --------------------------------------------------

elif page == "⚙️ Paramètres":
    st.title("⚙️ Paramètres mensuels")

    st.info(
        "Ces quatre paliers sont indépendants et doivent être "
        "sélectionnés chaque mois."
    )

    previous_creator_level = st.session_state.creator_level
    previous_consultant_level = st.session_state.consultant_level

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
            creator_levels = [5, 7, 9, 13, 15]
            creator_level = st.selectbox(
                "Palier Créateurs atteint",
                options=creator_levels,
                index=creator_levels.index(
                    int(st.session_state.creator_level)
                ),
                format_func=lambda value: f"{value} %",
            )

            consultant_levels = [5, 7, 9, 11, 13]
            consultant_level = st.selectbox(
                "Palier Consultants atteint",
                options=consultant_levels,
                index=consultant_levels.index(
                    int(st.session_state.consultant_level)
                ),
                format_func=lambda value: f"{value} %",
            )

            manager_levels = [5, 7, 9, 11, 13]
            manager_level = st.selectbox(
                "Palier Managers atteint",
                options=manager_levels,
                index=manager_levels.index(
                    int(st.session_state.manager_level)
                ),
                format_func=lambda value: f"{value} %",
            )

            director_levels = [4, 5, 7, 8, 10, 11, 13]
            director_level = st.selectbox(
                "Palier Directeur atteint",
                options=director_levels,
                index=director_levels.index(
                    int(st.session_state.director_level)
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

        if (
            previous_creator_level != creator_level
            or previous_consultant_level != consultant_level
        ):
            clear_calculation_cache()

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


# --------------------------------------------------
# PAGE CRÉATEURS
# --------------------------------------------------

elif page == "💎 Créateurs":
    st.title("💎 Calcul des créateurs")

    if st.session_state.backstage_data is None:
        st.warning("Importez d’abord un export Backstage.")
        st.stop()

    creator_results = ensure_creator_results()

    total_creators = len(creator_results)
    rewarded_creators = int(
        (creator_results["Rémunération 💎"] > 0).sum()
    )
    total_reward_diamonds = int(
        creator_results["Rémunération 💎"].sum()
    )
    hierarchy_creators = int(
        (creator_results["Compté hiérarchie"] == "Oui").sum()
    )

    metric1, metric2, metric3, metric4 = st.columns(4)

    metric1.metric("Créateurs importés", total_creators)
    metric2.metric("Créateurs rémunérés", rewarded_creators)
    metric3.metric(
        "Total rémunérations",
        f"{total_reward_diamonds:,.0f} 💎",
    )
    metric4.metric(
        "Comptés pour la hiérarchie",
        hierarchy_creators,
    )

    st.divider()
    st.subheader("Modes de paiement")

    payment_table = creator_results[
        [
            "Pseudo",
            "Groupe",
            "Agent",
            "Diamants",
            "Rémunération 💎",
            "Mode paiement",
        ]
    ].copy()

    edited_payment_table = st.data_editor(
        payment_table,
        use_container_width=True,
        hide_index=True,
        disabled=[
            "Pseudo",
            "Groupe",
            "Agent",
            "Diamants",
            "Rémunération 💎",
        ],
        column_config={
            "Mode paiement": st.column_config.SelectboxColumn(
                "Mode paiement",
                options=["Diamants", "Facture €"],
                required=True,
            ),
            "Diamants": st.column_config.NumberColumn(
                "Diamants générés",
                format="%d 💎",
            ),
            "Rémunération 💎": st.column_config.NumberColumn(
                "Rémunération",
                format="%d 💎",
            ),
        },
        key="creator_payment_editor",
    )

    creator_results["Mode paiement"] = (
        edited_payment_table["Mode paiement"].values
    )

    coin_price = float(st.session_state.coin_pack_price) / 1000
    invoice_rate = float(st.session_state.invoice_rate)

    creator_results["Facture €"] = creator_results.apply(
        lambda row: int(
            row["Rémunération 💎"] * invoice_rate
        )
        if row["Mode paiement"] == "Facture €"
        else 0,
        axis=1,
    )

    creator_results["Coût diamants €"] = creator_results.apply(
        lambda row: round(
            row["Rémunération 💎"] * coin_price,
            2,
        )
        if row["Mode paiement"] == "Diamants"
        else 0.0,
        axis=1,
    )

    creator_results["Total déduction €"] = (
        creator_results["Facture €"]
        + creator_results["Coût diamants €"]
    )

    st.session_state.creator_results = creator_results

    total_invoices = int(
        creator_results["Facture €"].sum()
    )
    total_coin_cost = float(
        creator_results["Coût diamants €"].sum()
    )
    total_deduction = float(
        creator_results["Total déduction €"].sum()
    )

    st.subheader("Récapitulatif financier")

    total1, total2, total3 = st.columns(3)

    total1.metric(
        "Total factures",
        f"{total_invoices:,.0f} €",
    )
    total2.metric(
        "Coût des diamants",
        f"{total_coin_cost:,.2f} €",
    )
    total3.metric(
        "Déduction totale",
        f"{total_deduction:,.2f} €",
    )

    with st.expander(
        "Afficher le détail complet des calculs",
        expanded=False,
    ):
        st.dataframe(
            creator_results,
            use_container_width=True,
            hide_index=True,
        )


# --------------------------------------------------
# PAGE CONSULTANTS
# --------------------------------------------------

elif page == "👥 Consultants":
    st.title("👥 Calcul des consultants")

    if st.session_state.backstage_data is None:
        st.warning("Importez d’abord un export Backstage.")
        st.stop()

    creator_results = ensure_creator_results()

    consultant_signature = (
        st.session_state.backstage_filename,
        int(st.session_state.creator_level),
        int(st.session_state.consultant_level),
    )

    if (
        "consultant_results" not in st.session_state
        or st.session_state.get("consultant_signature")
        != consultant_signature
    ):
        consultant_results = calculate_consultant_rewards(
            creator_results=creator_results,
            consultant_level=int(
                st.session_state.consultant_level
            ),
            minimum_team_diamonds=200_000,
        )

        consultant_results["Inclure dans le calcul"] = "Oui"
        consultant_results["Mode paiement"] = "Diamants"

        st.session_state.consultant_results = consultant_results
        st.session_state.consultant_signature = consultant_signature

    consultant_results = (
        st.session_state.consultant_results.copy()
    )

    if consultant_results.empty:
        st.warning(
            "Aucun consultant n’a été détecté dans la colonne Agent."
        )
        st.stop()

    # Compatibilité si le tableau provient d’une ancienne session
    if "Inclure dans le calcul" not in consultant_results.columns:
        consultant_results["Inclure dans le calcul"] = "Oui"

    if "Mode paiement" not in consultant_results.columns:
        consultant_results["Mode paiement"] = "Diamants"

    total_consultants = len(consultant_results)
    rewarded_consultants = int(
        (consultant_results["Rémunération 💎"] > 0).sum()
    )
    total_eligible_diamonds = int(
        consultant_results["Diamants éligibles"].sum()
    )
    total_reward_diamonds = int(
        consultant_results["Rémunération 💎"].sum()
    )

    metric1, metric2, metric3, metric4 = st.columns(4)

    metric1.metric(
        "Consultants détectés",
        total_consultants,
    )
    metric2.metric(
        "Consultants rémunérés",
        rewarded_consultants,
    )
    metric3.metric(
        "Diamants éligibles",
        f"{total_eligible_diamonds:,.0f} 💎",
    )
    metric4.metric(
        "Total rémunérations",
        f"{total_reward_diamonds:,.0f} 💎",
    )

    st.divider()
    st.subheader("Rémunérations des consultants")

    payment_table = consultant_results[
        [
            "Consultant",
            "Inclure dans le calcul",
            "Créateurs rattachés",
            "Créateurs comptés",
            "Diamants éligibles",
            "Seuil atteint",
            "Taux",
            "Rémunération 💎",
            "Mode paiement",
        ]
    ].copy()

    edited_payment_table = st.data_editor(
        payment_table,
        use_container_width=True,
        hide_index=True,
        disabled=[
            "Consultant",
            "Créateurs rattachés",
            "Créateurs comptés",
            "Diamants éligibles",
            "Seuil atteint",
            "Taux",
            "Rémunération 💎",
        ],
        column_config={
            "Inclure dans le calcul": st.column_config.SelectboxColumn(
                "Inclure dans le calcul",
                options=["Oui", "Non"],
                required=True,
            ),
            "Mode paiement": st.column_config.SelectboxColumn(
                "Mode paiement",
                options=["Diamants", "Facture €"],
                required=True,
            ),
            "Diamants éligibles": st.column_config.NumberColumn(
                "Diamants éligibles",
                format="%d 💎",
            ),
            "Rémunération 💎": st.column_config.NumberColumn(
                "Rémunération",
                format="%d 💎",
            ),
            "Taux": st.column_config.NumberColumn(
                "Taux",
                format="%.2f",
            ),
        },
        key="consultant_payment_editor",
    )

    consultant_results["Inclure dans le calcul"] = (
        edited_payment_table["Inclure dans le calcul"].values
    )
    consultant_results["Mode paiement"] = (
        edited_payment_table["Mode paiement"].values
    )

    consultant_results.loc[
        consultant_results["Inclure dans le calcul"] == "Non",
        ["Taux", "Rémunération 💎"],
    ] = 0

    coin_price = float(st.session_state.coin_pack_price) / 1000
    invoice_rate = float(st.session_state.invoice_rate)

    consultant_results["Facture €"] = consultant_results.apply(
        lambda row: int(
            row["Rémunération 💎"] * invoice_rate
        )
        if row["Mode paiement"] == "Facture €"
        else 0,
        axis=1,
    )

    consultant_results["Coût diamants €"] = consultant_results.apply(
        lambda row: round(
            row["Rémunération 💎"] * coin_price,
            2,
        )
        if row["Mode paiement"] == "Diamants"
        else 0.0,
        axis=1,
    )

    consultant_results["Total déduction €"] = (
        consultant_results["Facture €"]
        + consultant_results["Coût diamants €"]
    )

    st.session_state.consultant_results = consultant_results

    total_invoices = int(
        consultant_results["Facture €"].sum()
    )
    total_coin_cost = float(
        consultant_results["Coût diamants €"].sum()
    )
    total_deduction = float(
        consultant_results["Total déduction €"].sum()
    )

    st.subheader("Récapitulatif financier")

    total1, total2, total3 = st.columns(3)

    total1.metric(
        "Total factures",
        f"{total_invoices:,.0f} €",
    )
    total2.metric(
        "Coût des diamants",
        f"{total_coin_cost:,.2f} €",
    )
    total3.metric(
        "Déduction totale",
        f"{total_deduction:,.2f} €",
    )

    with st.expander(
        "Afficher le détail complet",
        expanded=False,
    ):
        st.dataframe(
            consultant_results,
            use_container_width=True,
            hide_index=True,
        )
