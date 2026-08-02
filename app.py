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
    "director_branch_revenue_usd": 0.0,
    "director_branch_other_expenses": 0.0,
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
        "responsable_results",
        "responsable_signature",
        "creator_payment_editor",
        "consultant_payment_editor",
        "responsable_payment_editor",
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


RESPONSABLE_RATES = {
    5: 0.010,
    7: 0.015,
    9: 0.018,
    11: 0.020,
    13: 0.025,
}

DIRECTOR_RATES = {
    4: 0.04,
    5: 0.05,
    7: 0.07,
    8: 0.09,
    10: 0.11,
    11: 0.13,
    13: 0.15,
}


def floor_to_hundred(value):
    return int(float(value) // 100 * 100)


def calculate_responsable_rewards(
    creator_results,
    responsable_level,
    minimum_group_diamonds=600_000,
):
    required_columns = {
        "Groupe",
        "Diamants",
        "Compté hiérarchie",
    }
    missing_columns = required_columns.difference(creator_results.columns)
    if missing_columns:
        raise ValueError(
            "Colonnes manquantes pour calculer les responsables : "
            + ", ".join(sorted(missing_columns))
        )

    data = creator_results.copy()
    data["Groupe"] = data["Groupe"].fillna("").astype(str).str.strip()
    data = data[data["Groupe"].ne("") & data["Groupe"].ne("nan")]

    rate = RESPONSABLE_RATES.get(int(responsable_level), 0.0)
    rows = []

    for responsable, group in data.groupby("Groupe", dropna=False):
        eligible = group[group["Compté hiérarchie"] == "Oui"]
        eligible_diamonds = int(eligible["Diamants"].sum())
        threshold_reached = eligible_diamonds >= minimum_group_diamonds
        reward = (
            floor_to_hundred(eligible_diamonds * rate)
            if threshold_reached
            else 0
        )

        rows.append(
            {
                "Responsable performance": responsable,
                "Créateurs rattachés": len(group),
                "Créateurs comptés": len(eligible),
                "Diamants éligibles": eligible_diamonds,
                "Seuil atteint": "Oui" if threshold_reached else "Non",
                "Taux": rate if threshold_reached else 0.0,
                "Rémunération 💎": reward,
            }
        )

    result = pd.DataFrame(rows)
    if not result.empty:
        result.sort_values(
            "Diamants éligibles",
            ascending=False,
            inplace=True,
        )
        result.reset_index(drop=True, inplace=True)
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
        "📈 Responsables performance",
        "🏢 Directeur de branche",
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

    if st.session_state.backstage_data is not None:
        backstage = st.session_state.backstage_data
        detected_rows = []

        if "Agent" in backstage.columns:
            for value in backstage["Agent"].dropna().unique():
                email = normalize_email(value)
                if email and email != "nan":
                    detected_rows.append(
                        {"Adresse détectée": email, "Emplacement": "Agent"}
                    )

        if "Groupe" in backstage.columns:
            for value in backstage["Groupe"].dropna().unique():
                email = normalize_email(value)
                if email and email != "nan":
                    detected_rows.append(
                        {"Adresse détectée": email, "Emplacement": "Groupe"}
                    )

        if detected_rows:
            detected_dataframe = pd.DataFrame(detected_rows).drop_duplicates()
            with st.expander(
                "🔎 Voir toutes les adresses détectées dans l’export"
            ):
                st.dataframe(
                    detected_dataframe.sort_values(
                        ["Emplacement", "Adresse détectée"]
                    ),
                    use_container_width=True,
                    hide_index=True,
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
                "E-mail ou nom du groupe",
                help=(
                    "Saisissez l’adresse exacte de la colonne Agent ou le "
                    "nom exact présent dans la colonne Groupe."
                ),
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
        st.session_state.pop("responsable_results", None)
        st.session_state.pop("responsable_signature", None)
        st.session_state.pop("responsable_payment_editor", None)
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


elif page == "📈 Responsables performance":
    st.title("📈 Calcul des responsables performance")

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

    exclusion_signature = tuple(sorted(excluded_emails("responsables")))
    responsable_signature = (
        st.session_state.backstage_filename,
        st.session_state.creator_level,
        st.session_state.manager_level,
        exclusion_signature,
    )

    if (
        "responsable_results" not in st.session_state
        or st.session_state.get("responsable_signature")
        != responsable_signature
    ):
        responsable_results = calculate_responsable_rewards(
            creator_results=st.session_state.creator_results,
            responsable_level=int(st.session_state.manager_level),
            minimum_group_diamonds=600_000,
        )
        responsable_results["Mode paiement"] = "Diamants"
        st.session_state.responsable_results = responsable_results
        st.session_state.responsable_signature = responsable_signature

    responsable_results = st.session_state.responsable_results.copy()

    if responsable_results.empty:
        st.warning(
            "Aucun responsable performance n’a été détecté dans la "
            "colonne Groupe."
        )
        st.stop()

    excluded = excluded_emails("responsables")
    responsable_results["Inclure dans le calcul"] = responsable_results[
        "Responsable performance"
    ].map(lambda value: "Non" if normalize_email(value) in excluded else "Oui")

    excluded_mask = responsable_results["Inclure dans le calcul"] == "Non"
    responsable_results.loc[
        excluded_mask,
        ["Taux", "Rémunération 💎"],
    ] = 0

    metric1, metric2, metric3, metric4 = st.columns(4)
    metric1.metric("Responsables détectés", len(responsable_results))
    metric2.metric(
        "Responsables rémunérés",
        int((responsable_results["Rémunération 💎"] > 0).sum()),
    )
    metric3.metric(
        "Diamants éligibles",
        f"{responsable_results.loc[~excluded_mask, 'Diamants éligibles'].sum():,.0f} 💎",
    )
    metric4.metric(
        "Total rémunérations",
        f"{responsable_results['Rémunération 💎'].sum():,.0f} 💎",
    )

    st.divider()
    payment_table = responsable_results[
        [
            "Responsable performance",
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
            "Responsable performance",
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
        key="responsable_payment_editor",
    )

    responsable_results["Mode paiement"] = edited_payment_table[
        "Mode paiement"
    ].values
    responsable_results = financial_columns(responsable_results)
    st.session_state.responsable_results = responsable_results
    show_financial_summary(responsable_results)

    with st.expander("Afficher le détail complet"):
        st.dataframe(
            responsable_results,
            use_container_width=True,
            hide_index=True,
        )


elif page == "🏢 Directeur de branche":
    st.title("🏢 Calcul du directeur de branche")

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

    all_creator_results = st.session_state.creator_results.copy()
    available_groups = sorted(
        value
        for value in all_creator_results["Groupe"]
        .fillna("")
        .astype(str)
        .str.strip()
        .unique()
        if value and value.lower() != "nan"
    )

    st.subheader("Composition de la branche")
    selected_groups = st.multiselect(
        "Cochez les responsables performance appartenant à cette branche",
        options=available_groups,
        default=available_groups,
        help=(
            "Si l’export contient uniquement la branche du directeur, "
            "laissez tous les responsables cochés."
        ),
        key="director_selected_groups",
    )

    if not selected_groups:
        st.warning("Sélectionnez au moins un responsable performance.")
        st.stop()

    input1, input2 = st.columns(2)
    revenue_usd = input1.number_input(
        "Chiffre d’affaires Backstage de la branche ($)",
        min_value=0.0,
        value=float(st.session_state.director_branch_revenue_usd),
        step=100.0,
        key="director_revenue_input",
    )
    branch_other_expenses = input2.number_input(
        "Autres dépenses propres à la branche (€)",
        min_value=0.0,
        value=float(st.session_state.director_branch_other_expenses),
        step=10.0,
        key="director_expenses_input",
    )
    st.session_state.director_branch_revenue_usd = revenue_usd
    st.session_state.director_branch_other_expenses = branch_other_expenses

    branch_creators = all_creator_results[
        all_creator_results["Groupe"].isin(selected_groups)
    ].copy()
    if "Mode paiement" not in branch_creators.columns:
        branch_creators["Mode paiement"] = "Diamants"
    branch_creators = financial_columns(branch_creators)

    branch_consultants = calculate_consultant_rewards(
        creator_results=branch_creators,
        consultant_level=int(st.session_state.consultant_level),
        minimum_team_diamonds=200_000,
    )
    if not branch_consultants.empty:
        branch_consultants["Mode paiement"] = "Diamants"
        consultant_exclusions = excluded_emails("consultants")
        consultant_excluded_mask = branch_consultants["Consultant"].map(
            lambda value: normalize_email(value) in consultant_exclusions
        )
        branch_consultants.loc[
            consultant_excluded_mask,
            ["Taux", "Rémunération 💎"],
        ] = 0
        branch_consultants = financial_columns(branch_consultants)

    branch_responsables = calculate_responsable_rewards(
        creator_results=branch_creators,
        responsable_level=int(st.session_state.manager_level),
        minimum_group_diamonds=600_000,
    )
    if not branch_responsables.empty:
        branch_responsables["Mode paiement"] = "Diamants"
        responsable_exclusions = excluded_emails("responsables")
        responsable_excluded_mask = branch_responsables[
            "Responsable performance"
        ].map(lambda value: normalize_email(value) in responsable_exclusions)
        branch_responsables.loc[
            responsable_excluded_mask,
            ["Taux", "Rémunération 💎"],
        ] = 0
        branch_responsables = financial_columns(branch_responsables)

    revenue_eur = revenue_usd * float(st.session_state.usd_to_eur)
    charges_eur = revenue_eur * float(st.session_state.charges_rate) / 100
    creator_cost = float(branch_creators["Total déduction €"].sum())
    consultant_cost = (
        float(branch_consultants["Total déduction €"].sum())
        if not branch_consultants.empty
        else 0.0
    )
    responsable_cost = (
        float(branch_responsables["Total déduction €"].sum())
        if not branch_responsables.empty
        else 0.0
    )
    net_profit_before_director = max(
        0.0,
        revenue_eur
        - charges_eur
        - creator_cost
        - consultant_cost
        - responsable_cost
        - branch_other_expenses,
    )
    director_rate = DIRECTOR_RATES.get(
        int(st.session_state.director_level),
        0.0,
    )
    director_reward = net_profit_before_director * director_rate
    remaining_after_director = (
        net_profit_before_director - director_reward
    )

    st.divider()
    st.subheader("Résultat de la branche")
    result1, result2, result3, result4 = st.columns(4)
    result1.metric("CA converti", f"{revenue_eur:,.2f} €")
    result2.metric(
        f"Charges ({st.session_state.charges_rate:.1f} %)",
        f"− {charges_eur:,.2f} €",
    )
    result3.metric(
        "Bénéfice avant directeur",
        f"{net_profit_before_director:,.2f} €",
    )
    result4.metric(
        f"Rémunération directeur ({director_rate * 100:.0f} %)",
        f"{director_reward:,.2f} €",
    )

    summary = pd.DataFrame(
        [
            ("Chiffre d’affaires converti", revenue_eur),
            ("Charges sur le CA", -charges_eur),
            ("Rémunérations créateurs", -creator_cost),
            ("Rémunérations consultants", -consultant_cost),
            ("Rémunérations responsables performance", -responsable_cost),
            ("Autres dépenses de la branche", -branch_other_expenses),
            ("Bénéfice avant directeur", net_profit_before_director),
            ("Rémunération du directeur", -director_reward),
            ("Bénéfice restant", remaining_after_director),
        ],
        columns=["Élément", "Montant €"],
    )
    st.dataframe(
        summary,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Montant €": st.column_config.NumberColumn(format="%.2f €")
        },
    )

    with st.expander("Voir les groupes sélectionnés"):
        st.write(selected_groups)
        st.caption(
            f"{len(branch_creators)} créateur(s), "
            f"{len(branch_consultants)} consultant(s) et "
            f"{len(branch_responsables)} responsable(s) pris en compte."
        )
