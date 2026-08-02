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
    "exclusions": [],
}

for key, default_value in DEFAULT_VALUES.items():
    if key not in st.session_state:
        st.session_state[key] = default_value


def normalize_email(value):
    return str(value or "").strip().lower()


def clean_exclusions(rows):
    cleaned = []
    seen = set()

    for row in rows:
        email = normalize_email(row.get("Adresse e-mail", ""))
        if not email or email in seen:
            continue

        seen.add(email)
        cleaned.append(
            {
                "Adresse e-mail": email,
                "Exclure consultants": bool(
                    row.get("Exclure consultants", True)
                ),
                "Exclure responsables performance": bool(
                    row.get("Exclure responsables performance", True)
                ),
            }
        )

    return cleaned


def excluded_emails(scope):
    column = {
        "consultants": "Exclure consultants",
        "responsables": "Exclure responsables performance",
    }[scope]

    return {
        normalize_email(row.get("Adresse e-mail", ""))
        for row in st.session_state.exclusions
        if row.get(column, False)
    }


def reset_calculations():
    for key in (
        "creator_results",
        "creator_signature",
        "consultant_results",
        "consultant_signature",
        "creator_payment_editor",
        "consultant_payment_editor",
    ):
        st.session_state.pop(key, None)


def financial_columns(dataframe):
    result = dataframe.copy()
    coin_price = float(st.session_state.coin_pack_price) / 1000
    invoice_rate = float(st.session_state.invoice_rate)

    result["Facture €"] = result.apply(
        lambda row: int(row["Rémunération 💎"] * invoice_rate)
        if row["Mode paiement"] == "Facture €"
        else 0,
        axis=1,
    )
    result["Coût diamants €"] = result.apply(
        lambda row: round(row["Rémunération 💎"] * coin_price, 2)
        if row["Mode paiement"] == "Diamants"
        else 0.0,
        axis=1,
    )
    result["Total déduction €"] = (
        result["Facture €"] + result["Coût diamants €"]
    )
    return result


def show_financial_summary(dataframe):
    st.subheader("Récapitulatif financier")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total factures", f"{dataframe['Facture €'].sum():,.0f} €")
    col2.metric(
        "Coût des diamants",
        f"{dataframe['Coût diamants €'].sum():,.2f} €",
    )
    col3.metric(
        "Déduction totale",
        f"{dataframe['Total déduction €'].sum():,.2f} €",
    )


st.sidebar.title("💎 Pro Consulting")

page = st.sidebar.radio(
    "Navigation",
    [
        "🏠 Accueil",
        "📥 Import Backstage",
        "⚙️ Paramètres",
        "🛡️ Administration",
        "💎 Créateurs",
        "👥 Consultants",
    ],
)


if page == "🏠 Accueil":
    st.title("💎 Pro Consulting")
    st.subheader("Calcul des rémunérations")

    if st.session_state.backstage_data is None:
        st.info("Aucun export Backstage n’a encore été importé.")
    else:
        st.success(f"Export chargé : {st.session_state.backstage_filename}")
        st.metric(
            "Nombre de créateurs importés",
            len(st.session_state.backstage_data),
        )

    st.write(
        "Utilisez le menu de gauche pour importer l’export et calculer "
        "les rémunérations."
    )


elif page == "📥 Import Backstage":
    st.title("📥 Import Backstage")

    if st.session_state.backstage_data is not None:
        st.success(
            f"Fichier actuellement chargé : "
            f"{st.session_state.backstage_filename}"
        )

    uploaded_file = st.file_uploader(
        "Choisir l’export Backstage",
        type=["xlsx"],
        help="Le fichier doit être au format Excel .xlsx",
    )

    if uploaded_file is not None:
        try:
            raw_dataframe = pd.read_excel(uploaded_file, sheet_name=0)
            prepared_dataframe, detected_columns = prepare_backstage_data(
                raw_dataframe
            )

            is_new_file = (
                uploaded_file.name != st.session_state.backstage_filename
            )
            st.session_state.backstage_data = prepared_dataframe
            st.session_state.backstage_raw_data = raw_dataframe
            st.session_state.backstage_filename = uploaded_file.name
            st.session_state.detected_columns = detected_columns

            if is_new_file:
                reset_calculations()

            st.success("L’export Backstage a été lu correctement.")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Créateurs importés", len(prepared_dataframe))
            col2.metric(
                "Diamants générés",
                f"{prepared_dataframe['Diamants'].sum():,.0f}",
            )
            col3.metric(
                "Total heures LIVE",
                f"{prepared_dataframe['Heures LIVE'].sum():,.1f} h",
            )
            col4.metric("Colonnes détectées", len(detected_columns))

            st.subheader("Aperçu des données préparées")
            st.dataframe(
                prepared_dataframe.head(30),
                use_container_width=True,
                hide_index=True,
            )

        except ValueError as error:
            st.error("Certaines colonnes obligatoires sont absentes.")
            st.code(str(error))
        except Exception as error:
            st.error("Une erreur empêche la lecture du fichier.")
            st.code(str(error))


elif page == "⚙️ Paramètres":
    st.title("⚙️ Paramètres mensuels")
    st.info(
        "Les quatre paliers sont indépendants et doivent être "
        "sélectionnés chaque mois."
    )

    with st.form("monthly_parameters"):
        left, right = st.columns(2)

        with left:
            month = st.text_input("Mois calculé", st.session_state.month)
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

        with right:
            creator_level = st.selectbox(
                "Palier Créateurs atteint",
                [4, 7, 9, 11, 13, 15],
                index=[4, 7, 9, 11, 13, 15].index(
                    int(st.session_state.creator_level)
                ),
            )
            consultant_level = st.selectbox(
                "Palier Consultants atteint",
                [5, 7, 9, 11, 13],
                index=[5, 7, 9, 11, 13].index(
                    int(st.session_state.consultant_level)
                ),
            )
            manager_level = st.selectbox(
                "Palier Responsables performance atteint",
                [5, 7, 9, 11, 13],
                index=[5, 7, 9, 11, 13].index(
                    int(st.session_state.manager_level)
                ),
            )
            director_level = st.selectbox(
                "Palier Directeur atteint",
                [4, 5, 7, 8, 10, 11, 13],
                index=[4, 5, 7, 8, 10, 11, 13].index(
                    int(st.session_state.director_level)
                ),
            )

        st.subheader("Paramètres financiers")
        fin1, fin2, fin3 = st.columns(3)
        coin_pack_price = fin1.number_input(
            "Prix de 1 000 pièces TikTok (€)",
            min_value=0.0,
            value=float(st.session_state.coin_pack_price),
            step=0.10,
        )
        invoice_rate = fin2.number_input(
            "Valeur facture par diamant (€)",
            min_value=0.0,
            value=float(st.session_state.invoice_rate),
            step=0.0001,
            format="%.4f",
        )
        charges_rate = fin3.number_input(
            "Charges sur le CA (%)",
            min_value=0.0,
            max_value=100.0,
            value=float(st.session_state.charges_rate),
            step=0.1,
        )

        save_parameters = st.form_submit_button(
            "💾 Enregistrer les paramètres",
            use_container_width=True,
        )

    if save_parameters:
        old_levels = (
            st.session_state.creator_level,
            st.session_state.consultant_level,
        )
        st.session_state.month = month
        st.session_state.revenue_usd = revenue_usd
        st.session_state.usd_to_eur = usd_to_eur
        st.session_state.other_expenses = other_expenses
        st.session_state.creator_level = creator_level
        st.session_state.consultant_level = consultant_level
        st.session_state.manager_level = manager_level
        st.session_state.director_level = director_level
        st.session_state.coin_pack_price = coin_pack_price
        st.session_state.invoice_rate = invoice_rate
        st.session_state.charges_rate = charges_rate

        if old_levels != (creator_level, consultant_level):
            reset_calculations()

        st.success("Les paramètres mensuels ont été enregistrés.")


elif page == "🛡️ Administration":
    st.title("🛡️ Administration des exclusions")
    st.write(
        "Ajoutez, modifiez ou supprimez une adresse à tout moment. "
        "Une ligne supprimée est automatiquement réintégrée aux calculs."
    )

    exclusions_dataframe = pd.DataFrame(
        st.session_state.exclusions,
        columns=[
            "Adresse e-mail",
            "Exclure consultants",
            "Exclure responsables performance",
        ],
    )

    edited_exclusions = st.data_editor(
        exclusions_dataframe,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config={
            "Adresse e-mail": st.column_config.TextColumn(
                "Adresse e-mail",
                help="Adresse exacte présente dans l’export Backstage.",
            ),
            "Exclure consultants": st.column_config.CheckboxColumn(
                "Exclure consultants",
                default=True,
            ),
            "Exclure responsables performance": (
                st.column_config.CheckboxColumn(
                    "Exclure responsables performance",
                    default=True,
                )
            ),
        },
        key="exclusions_editor",
    )

    if st.button(
        "💾 Enregistrer les exclusions",
        type="primary",
        use_container_width=True,
    ):
        st.session_state.exclusions = clean_exclusions(
            edited_exclusions.to_dict("records")
        )
        st.session_state.pop("consultant_results", None)
        st.session_state.pop("consultant_signature", None)
        st.session_state.pop("consultant_payment_editor", None)
        st.success(
            f"{len(st.session_state.exclusions)} exclusion(s) enregistrée(s)."
        )
        st.rerun()

    if st.session_state.exclusions:
        st.caption(
            "Les exclusions Consultants sont déjà actives. Celles des "
            "responsables performance seront appliquées automatiquement "
            "dès l’ajout de leur page de calcul."
        )
    else:
        st.info("Aucune adresse n’est actuellement exclue.")


elif page == "💎 Créateurs":
    st.title("💎 Calcul des créateurs")

    if st.session_state.backstage_data is None:
        st.warning("Importez d’abord un export Backstage.")
        st.stop()

    creator_signature = (
        st.session_state.backstage_filename,
        st.session_state.creator_level,
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

    creator_results = st.session_state.creator_results.copy()

    metric1, metric2, metric3, metric4 = st.columns(4)
    metric1.metric("Créateurs importés", len(creator_results))
    metric2.metric(
        "Créateurs rémunérés",
        int((creator_results["Rémunération 💎"] > 0).sum()),
    )
    metric3.metric(
        "Total rémunérations",
        f"{creator_results['Rémunération 💎'].sum():,.0f} 💎",
    )
    metric4.metric(
        "Comptés pour la hiérarchie",
        int((creator_results["Compté hiérarchie"] == "Oui").sum()),
    )

    st.divider()
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
            )
        },
        key="creator_payment_editor",
    )

    creator_results["Mode paiement"] = edited_payment_table[
        "Mode paiement"
    ].values
    creator_results = financial_columns(creator_results)
    st.session_state.creator_results = creator_results
    show_financial_summary(creator_results)

    with st.expander("Afficher le détail complet des calculs"):
        st.dataframe(
            creator_results,
            use_container_width=True,
            hide_index=True,
        )


elif page == "👥 Consultants":
    st.title("👥 Calcul des consultants")

    if st.session_state.backstage_data is None:
        st.warning("Importez d’abord un export Backstage.")
        st.stop()

    creator_signature = (
        st.session_state.backstage_filename,
        st.session_state.creator_level,
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

    exclusion_signature = tuple(sorted(excluded_emails("consultants")))
    consultant_signature = (
        st.session_state.backstage_filename,
        st.session_state.creator_level,
        st.session_state.consultant_level,
        exclusion_signature,
    )

    if (
        "consultant_results" not in st.session_state
        or st.session_state.get("consultant_signature")
        != consultant_signature
    ):
        consultant_results = calculate_consultant_rewards(
            creator_results=st.session_state.creator_results,
            consultant_level=int(st.session_state.consultant_level),
            minimum_team_diamonds=200_000,
        )
        consultant_results["Mode paiement"] = "Diamants"
        st.session_state.consultant_results = consultant_results
        st.session_state.consultant_signature = consultant_signature

    consultant_results = st.session_state.consultant_results.copy()

    if consultant_results.empty:
        st.warning("Aucun consultant n’a été détecté dans la colonne Agent.")
        st.stop()

    excluded = excluded_emails("consultants")
    consultant_results["Inclure dans le calcul"] = consultant_results[
        "Consultant"
    ].map(lambda value: "Non" if normalize_email(value) in excluded else "Oui")

    excluded_mask = (
        consultant_results["Inclure dans le calcul"] == "Non"
    )
    consultant_results.loc[
        excluded_mask,
        ["Taux", "Rémunération 💎"],
    ] = 0

    metric1, metric2, metric3, metric4 = st.columns(4)
    metric1.metric("Consultants détectés", len(consultant_results))
    metric2.metric(
        "Consultants rémunérés",
        int((consultant_results["Rémunération 💎"] > 0).sum()),
    )
    metric3.metric(
        "Diamants éligibles",
        f"{consultant_results.loc[~excluded_mask, 'Diamants éligibles'].sum():,.0f} 💎",
    )
    metric4.metric(
        "Total rémunérations",
        f"{consultant_results['Rémunération 💎'].sum():,.0f} 💎",
    )

    st.divider()
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
            "Inclure dans le calcul",
            "Créateurs rattachés",
            "Créateurs comptés",
            "Diamants éligibles",
            "Seuil atteint",
            "Taux",
            "Rémunération 💎",
        ],
        column_config={
            "Mode paiement": st.column_config.SelectboxColumn(
                "Mode paiement",
                options=["Diamants", "Facture €"],
                required=True,
            )
        },
        key="consultant_payment_editor",
    )

    consultant_results["Mode paiement"] = edited_payment_table[
        "Mode paiement"
    ].values
    consultant_results = financial_columns(consultant_results)
    st.session_state.consultant_results = consultant_results
    show_financial_summary(consultant_results)

    with st.expander("Afficher le détail complet"):
        st.dataframe(
            consultant_results,
            use_container_width=True,
            hide_index=True,
        )
