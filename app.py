import json

import pandas as pd
import psycopg
import streamlit as st
from datetime import datetime
from html import escape
from urllib.request import Request, urlopen
from xml.etree import ElementTree

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


st.markdown(
    """
    <style>
    :root {
        --pc-lagoon: #00d7c8;
        --pc-lagoon-light: #73fff0;
        --pc-teal: #007c86;
        --pc-teal-deep: #071c2b;
        --pc-sand: #e7b76a;
        --pc-gold: #ffc857;
        --pc-cream: #fff8ea;
        --pc-ink: #071b25;
        --pc-panel: rgba(8, 38, 52, 0.9);
        --pc-border: rgba(255, 200, 87, 0.38);
    }

    [data-testid="stSidebarNav"] {
        display: none !important;
    }

    [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(circle at 86% 8%, rgba(0, 215, 200, 0.22), transparent 30%),
            radial-gradient(circle at 10% 92%, rgba(255, 200, 87, 0.13), transparent 28%),
            linear-gradient(145deg, #071927 0%, #0a2636 48%, #0d3442 100%);
        color: var(--pc-cream);
    }

    [data-testid="stHeader"] {
        background: transparent;
    }

    [data-testid="stDecoration"] {
        background: linear-gradient(90deg, var(--pc-lagoon), var(--pc-gold));
    }

    .block-container {
        max-width: 1480px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }

    h1, h2, h3 {
        color: var(--pc-cream) !important;
        letter-spacing: -0.025em;
    }

    h1 {
        font-weight: 780 !important;
    }

    h2, h3 {
        font-weight: 700 !important;
    }

    a {
        color: var(--pc-lagoon-light) !important;
    }

    [data-testid="stSidebar"] {
        background:
            radial-gradient(circle at 20% 5%, rgba(0, 215, 200, 0.18), transparent 27%),
            linear-gradient(180deg, #071a28 0%, #0b2938 58%, #0d3a46 100%);
        border-right: 1px solid rgba(255, 200, 87, 0.34);
    }

    [data-testid="stSidebar"] [data-testid="stSidebarContent"] {
        padding-top: 1.15rem;
    }

    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] span {
        color: var(--pc-cream) !important;
    }

    [data-testid="stSidebar"] [role="radiogroup"] label {
        border: 1px solid transparent;
        border-radius: 12px;
        margin: 0.18rem 0;
        padding: 0.46rem 0.6rem;
        transition: all 0.2s ease;
    }

    [data-testid="stSidebar"] [role="radiogroup"] label:hover {
        background: rgba(0, 215, 200, 0.12);
        border-color: rgba(115, 255, 240, 0.42);
        transform: translateX(2px);
    }

    [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
        background: linear-gradient(
            90deg,
            rgba(0, 215, 200, 0.3),
            rgba(255, 200, 87, 0.17)
        );
        border-color: rgba(255, 200, 87, 0.56);
        box-shadow: inset 3px 0 0 var(--pc-gold);
    }

    [data-testid="stMetric"] {
        height: 100%;
        padding: 1.05rem 1.15rem;
        border: 1px solid var(--pc-border);
        border-radius: 17px;
        background: linear-gradient(
            145deg,
            rgba(12, 54, 70, 0.95),
            rgba(7, 29, 42, 0.88)
        );
        box-shadow: 0 12px 30px rgba(0, 8, 18, 0.32);
        backdrop-filter: blur(14px);
    }

    [data-testid="stMetricLabel"] {
        color: var(--pc-lagoon-light) !important;
        font-weight: 650;
    }

    [data-testid="stMetricValue"] {
        color: var(--pc-gold) !important;
        font-weight: 760;
    }

    [data-testid="stForm"],
    [data-testid="stExpander"] {
        border: 1px solid var(--pc-border) !important;
        border-radius: 18px !important;
        background: linear-gradient(
            145deg,
            rgba(12, 48, 62, 0.94),
            rgba(8, 32, 45, 0.88)
        );
        box-shadow: 0 14px 34px rgba(0, 8, 18, 0.3);
    }

    [data-testid="stForm"] {
        padding: 1.25rem 1.35rem;
    }

    [data-testid="stFileUploaderDropzone"] {
        border: 1px dashed rgba(115, 255, 240, 0.62);
        border-radius: 16px;
        background: rgba(0, 124, 134, 0.2);
    }

    [data-baseweb="input"] > div,
    [data-baseweb="select"] > div,
    [data-baseweb="textarea"] > div {
        border-color: rgba(115, 255, 240, 0.34) !important;
        border-radius: 11px !important;
        background-color: rgba(7, 29, 42, 0.82) !important;
    }

    [data-baseweb="input"] input,
    [data-baseweb="select"] input,
    [data-baseweb="textarea"] textarea {
        color: var(--pc-cream) !important;
    }

    [data-testid="stNumberInput"] button {
        color: var(--pc-gold) !important;
        border-color: rgba(239, 206, 136, 0.2) !important;
        background: rgba(255, 255, 255, 0.035) !important;
    }

    .stButton > button,
    .stDownloadButton > button,
    [data-testid="stFormSubmitButton"] > button {
        min-height: 2.75rem;
        border: 1px solid rgba(255, 200, 87, 0.78) !important;
        border-radius: 12px !important;
        background: linear-gradient(
            105deg,
            #f4b942 0%,
            #ffd166 52%,
            #00d7c8 145%
        ) !important;
        color: var(--pc-ink) !important;
        font-weight: 760 !important;
        box-shadow: 0 8px 22px rgba(0, 32, 36, 0.22);
        transition: transform 0.18s ease, box-shadow 0.18s ease;
    }

    [data-testid="stSidebar"] .stButton button p,
    [data-testid="stSidebar"] .stButton button span {
        color: var(--pc-ink) !important;
        font-weight: 800 !important;
    }

    .stButton > button:hover,
    .stDownloadButton > button:hover,
    [data-testid="stFormSubmitButton"] > button:hover {
        border-color: var(--pc-cream) !important;
        transform: translateY(-1px);
        box-shadow: 0 11px 26px rgba(0, 32, 36, 0.28);
    }

    .stButton > button:disabled,
    [data-testid="stFormSubmitButton"] > button:disabled {
        opacity: 0.55;
        transform: none;
    }

    [data-testid="stAlert"] {
        border-radius: 14px;
        border: 1px solid rgba(255, 255, 255, 0.12);
        box-shadow: 0 8px 22px rgba(0, 28, 32, 0.12);
    }

    [data-testid="stDataFrame"],
    [data-testid="stDataEditor"] {
        overflow: hidden;
        border: 1px solid var(--pc-border);
        border-radius: 16px;
        box-shadow: 0 14px 34px rgba(0, 25, 30, 0.18);
    }

    hr {
        border-color: rgba(239, 206, 136, 0.18) !important;
    }

    .pc-hero {
        position: relative;
        overflow: hidden;
        margin: 0 0 1.55rem;
        padding: 2.25rem 2.4rem;
        border: 1px solid rgba(255, 200, 87, 0.58);
        border-radius: 24px;
        background:
            radial-gradient(
                circle at 90% 18%,
                rgba(255, 248, 234, 0.2),
                transparent 24%
            ),
            linear-gradient(
                118deg,
                #071e2c 0%,
                #006f78 58%,
                #e7ad49 145%
            );
        box-shadow: 0 24px 52px rgba(0, 7, 18, 0.4);
    }

    .pc-hero::after {
        content: "◆";
        position: absolute;
        right: 3.2rem;
        top: 50%;
        color: rgba(247, 241, 229, 0.16);
        font-size: 7rem;
        line-height: 1;
        transform: translateY(-50%) rotate(45deg);
    }

    .pc-hero-kicker {
        margin-bottom: 0.55rem;
        color: var(--pc-gold);
        font-size: 0.78rem;
        font-weight: 800;
        letter-spacing: 0.17em;
        text-transform: uppercase;
    }

    .pc-hero h1 {
        position: relative;
        z-index: 1;
        margin: 0 0 0.55rem;
        max-width: 820px;
        color: #fffaf0 !important;
        font-size: clamp(2rem, 4vw, 3.3rem);
        line-height: 1.05;
    }

    .pc-hero p {
        position: relative;
        z-index: 1;
        max-width: 780px;
        margin: 0;
        color: rgba(247, 241, 229, 0.88);
        font-size: 1.04rem;
        line-height: 1.6;
    }

    .pc-sidebar-brand {
        margin: 0.2rem 0 1rem;
        padding: 1rem 1.05rem;
        border: 1px solid rgba(255, 200, 87, 0.46);
        border-radius: 17px;
        background: linear-gradient(
            145deg,
            rgba(12, 58, 72, 0.96),
            rgba(7, 29, 42, 0.9)
        );
        box-shadow: 0 12px 28px rgba(0, 7, 18, 0.34);
    }

    .pc-sidebar-logo {
        color: #fffaf0;
        font-size: 1.3rem;
        font-weight: 820;
        letter-spacing: -0.025em;
    }

    .pc-sidebar-logo span {
        color: var(--pc-gold) !important;
    }

    .pc-sidebar-tagline {
        margin-top: 0.25rem;
        color: rgba(247, 241, 229, 0.7) !important;
        font-size: 0.76rem;
        letter-spacing: 0.04em;
    }

    .pc-user-card {
        margin: 0 0 0.8rem;
        padding: 0.85rem 0.95rem;
        border-left: 3px solid var(--pc-gold);
        border-radius: 10px;
        background: linear-gradient(
            100deg,
            rgba(0, 124, 134, 0.22),
            rgba(7, 29, 42, 0.62)
        );
    }

    .pc-user-card strong {
        display: block;
        color: #fffaf0;
        font-size: 0.98rem;
    }

    .pc-user-card span {
        display: block;
        margin-top: 0.15rem;
        color: rgba(247, 241, 229, 0.7) !important;
        font-size: 0.78rem;
    }

    .pc-user-status {
        margin-bottom: 0.4rem;
        color: var(--pc-lagoon-light) !important;
        font-size: 0.72rem;
        font-weight: 760;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }

    @media (max-width: 760px) {
        .block-container {
            padding: 1rem 0.85rem 3rem;
        }

        .pc-hero {
            padding: 1.5rem 1.3rem;
            border-radius: 19px;
        }

        .pc-hero::after {
            right: 1rem;
            font-size: 4.4rem;
        }

        .pc-hero p {
            padding-right: 1.4rem;
            font-size: 0.94rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def render_brand_hero(title, subtitle, kicker="PRO CONSULTING"):
    st.markdown(
        f"""
        <section class="pc-hero">
            <div class="pc-hero-kicker">{escape(kicker)}</div>
            <h1>{escape(title)}</h1>
            <p>{escape(subtitle)}</p>
        </section>
        """,
        unsafe_allow_html=True,
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
    "coin_pack_price": 11.183,
    "invoice_rate": 0.0084,
    "charges_rate": 24.6,
    "exclusions": [],
    "director_branch_revenue_usd": 0.0,
    "director_branch_other_expenses": 0.0,
    "use_ecb_rate": True,
    "last_ecb_usd_to_eur": None,
    "last_ecb_rate_date": None,
}

GLOBAL_FINANCIAL_KEYS = (
    "coin_pack_price",
    "invoice_rate",
    "charges_rate",
)

BRANCH_PARAMETER_KEYS = (
    "month",
    "creator_level",
    "consultant_level",
    "manager_level",
    "director_level",
    "revenue_usd",
    "usd_to_eur",
    "other_expenses",
    "director_branch_revenue_usd",
    "director_branch_other_expenses",
    "use_ecb_rate",
)

for key, default_value in DEFAULT_VALUES.items():
    if key not in st.session_state:
        st.session_state[key] = default_value


def get_database_url():
    try:
        if "database" not in st.secrets:
            return None

        database = st.secrets["database"]
        database_url = str(database.get("url", "")).strip()
        return database_url or None
    except (FileNotFoundError, KeyError, TypeError):
        return None


@st.cache_resource(show_spinner=False)
def initialize_settings_database(database_url):
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS pro_consulting_settings (
                    scope TEXT PRIMARY KEY,
                    payload JSONB NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_by TEXT NOT NULL
                )
                """
            )
        connection.commit()

    return True


def load_persistent_scope(database_url, scope):
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT payload
                FROM pro_consulting_settings
                WHERE scope = %s
                """,
                (scope,),
            )
            row = cursor.fetchone()

    if row is None:
        return {}

    payload = row[0]
    if isinstance(payload, str):
        return json.loads(payload)
    return dict(payload)


def save_persistent_scopes(database_url, scopes, updated_by):
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            for scope, payload in scopes.items():
                cursor.execute(
                    """
                    INSERT INTO pro_consulting_settings (
                        scope,
                        payload,
                        updated_by
                    )
                    VALUES (%s, %s::jsonb, %s)
                    ON CONFLICT (scope)
                    DO UPDATE SET
                        payload = EXCLUDED.payload,
                        updated_at = CURRENT_TIMESTAMP,
                        updated_by = EXCLUDED.updated_by
                    """,
                    (
                        scope,
                        json.dumps(payload, ensure_ascii=False),
                        updated_by,
                    ),
                )
        connection.commit()


def normalize_email(value):
    return str(value or "").strip().lower()


def branch_settings_scope(user_email):
    return f"branch:{normalize_email(user_email)}"


def exclusions_scope(user_email):
    return f"exclusions:{normalize_email(user_email)}"


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


def apply_persistent_settings(database_url, user_email):
    initialize_settings_database(database_url)

    global_settings = load_persistent_scope(
        database_url,
        "global:financial",
    )
    branch_settings = load_persistent_scope(
        database_url,
        branch_settings_scope(user_email),
    )
    exclusions_settings = load_persistent_scope(
        database_url,
        exclusions_scope(user_email),
    )

    for key in GLOBAL_FINANCIAL_KEYS:
        if key in global_settings:
            st.session_state[key] = global_settings[key]

    for key in BRANCH_PARAMETER_KEYS:
        if key in branch_settings:
            st.session_state[key] = branch_settings[key]

    st.session_state.exclusions = clean_exclusions(
        exclusions_settings.get("rows", [])
    )


def show_estimation_notice():
    st.caption(
        "* Les rémunérations affichées sont des estimations calculées "
        "à partir des données importées et des paramètres enregistrés. "
        "Elles peuvent différer des montants définitifs réellement versés."
    )


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_ecb_usd_to_eur_rate():
    url = (
        "https://www.ecb.europa.eu/stats/eurofxref/"
        "eurofxref-daily.xml"
    )
    request = Request(url, headers={"User-Agent": "ProConsulting/1.0"})
    with urlopen(request, timeout=10) as response:
        xml_content = response.read()

    root = ElementTree.fromstring(xml_content)
    rate_date = None
    usd_per_eur = None

    for element in root.iter():
        if "time" in element.attrib:
            rate_date = element.attrib["time"]
        if element.attrib.get("currency") == "USD":
            usd_per_eur = float(element.attrib["rate"])

    if not rate_date or not usd_per_eur:
        raise ValueError("Le taux USD de la BCE est introuvable.")

    return 1 / usd_per_eur, rate_date


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
    diamond_total = dataframe.loc[
        dataframe["Mode paiement"] == "Diamants",
        "Rémunération 💎",
    ].sum()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(
        "Total à payer en diamants",
        f"{diamond_total:,.0f} 💎",
    )
    col2.metric(
        "Total factures",
        f"{dataframe['Facture €'].sum():,.0f} €",
    )
    col3.metric(
        "Coût des diamants",
        f"{dataframe['Coût diamants €'].sum():,.2f} €",
    )
    col4.metric(
        "Déduction totale",
        f"{dataframe['Total déduction €'].sum():,.2f} €",
    )


AUTHORIZED_USERS = {
    "tomeventfrance@gmail.com": {
        "name": "Thomas",
        "role": "admin",
        "direction": "Administration",
    },
    "a.stone.authorbusiness@gmail.com": {
        "name": "Biker",
        "role": "director",
        "direction": "Direction Biker",
    },
    "melvynschmidt2013@gmail.com": {
        "name": "Max",
        "role": "director",
        "direction": "Direction Max",
    },
    "moon441330@gmail.com": {
        "name": "Moon",
        "role": "director",
        "direction": "Direction Moon",
    },
    "vividirectrice@gmail.com": {
        "name": "Vivi",
        "role": "director",
        "direction": "Direction Vivi",
    },
}


def authentication_is_configured():
    try:
        if "auth" not in st.secrets:
            return False

        auth = st.secrets["auth"]
        if "google" not in auth:
            return False

        google = auth["google"]
        return all(
            auth.get(key)
            for key in ("redirect_uri", "cookie_secret")
        ) and all(
            google.get(key)
            for key in (
                "client_id",
                "client_secret",
                "server_metadata_url",
            )
        )
    except (FileNotFoundError, KeyError):
        return False


def login_screen():
    render_brand_hero(
        "Connexion sécurisée",
        "Accédez à votre espace de calcul avec l’adresse professionnelle "
        "autorisée pour votre direction.",
        "PRO CONSULTING • ESPACE PRIVÉ",
    )
    st.button(
        "Continuer avec Google",
        on_click=st.login,
        args=["google"],
        use_container_width=True,
        type="primary",
    )


if not authentication_is_configured():
    st.error(
        "La connexion sécurisée n’est pas encore configurée dans les "
        "Secrets Streamlit."
    )
    st.info(
        "Ajoutez la configuration Google dans les Secrets de "
        "l’application, puis redémarrez-la."
    )
    st.stop()

if not st.user.is_logged_in:
    login_screen()
    st.stop()

user_claims = st.user.to_dict()
current_user_email = normalize_email(
    user_claims.get("email")
    or user_claims.get("preferred_username")
    or user_claims.get("upn")
)
current_user_access = AUTHORIZED_USERS.get(current_user_email)

if current_user_access is None:
    st.error(
        "Accès refusé : cette adresse n’est pas autorisée à utiliser "
        "Pro Consulting."
    )
    if current_user_email:
        st.code(current_user_email)

    st.button(
        "Se déconnecter",
        on_click=st.logout,
        use_container_width=True,
    )
    st.stop()

current_user_role = current_user_access["role"]
current_user_name = current_user_access["name"]
current_user_direction = current_user_access["direction"]

if st.session_state.get("active_user_email") != current_user_email:
    for key in BRANCH_PARAMETER_KEYS:
        st.session_state[key] = DEFAULT_VALUES[key]

    st.session_state.exclusions = []
    st.session_state.backstage_data = None
    st.session_state.backstage_filename = None
    st.session_state.pop("backstage_raw_data", None)
    st.session_state.pop("detected_columns", None)
    st.session_state.pop("persistent_settings_loaded_for", None)
    reset_calculations()
    st.session_state.active_user_email = current_user_email

database_url = get_database_url()
persistent_settings_available = database_url is not None
persistent_settings_error = None

if persistent_settings_available:
    try:
        settings_session_key = f"settings:{current_user_email}"

        if (
            st.session_state.get("persistent_settings_loaded_for")
            != settings_session_key
        ):
            apply_persistent_settings(
                database_url,
                current_user_email,
            )
            st.session_state.persistent_settings_loaded_for = (
                settings_session_key
            )
    except Exception:
        persistent_settings_available = False
        persistent_settings_error = (
            "La base de paramètres est momentanément indisponible. "
            "Les valeurs de cette session restent utilisables, mais elles "
            "ne seront pas sauvegardées après la déconnexion."
        )


st.sidebar.markdown(
    """
    <div class="pc-sidebar-brand">
        <div class="pc-sidebar-logo"><span>◆</span> Pro Consulting</div>
        <div class="pc-sidebar-tagline">Pilotage & rémunérations</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.sidebar.markdown(
    f"""
    <div class="pc-user-card">
        <div class="pc-user-status">● Connecté</div>
        <strong>{escape(current_user_name)}</strong>
        <span>{escape(current_user_direction)}</span>
    </div>
    """,
    unsafe_allow_html=True,
)

st.sidebar.button(
    "🚪 Se déconnecter",
    on_click=st.logout,
    use_container_width=True,
)

admin_pages = [
    "🏠 Accueil",
    "📥 Import Backstage",
    "⚙️ Paramètres",
    "🛡️ Administration",
    "💎 Créateurs",
    "👥 Consultants",
    "📈 Responsables performance",
    "🏢 Directeur de branche",
]

director_pages = [
    "🏠 Accueil",
    "📥 Import Backstage",
    "⚙️ Paramètres",
    "🛡️ Administration",
    "💎 Créateurs",
    "👥 Consultants",
    "📈 Responsables performance",
    "🏢 Directeur de branche",
]

page = st.sidebar.radio(
    "Navigation",
    admin_pages if current_user_role == "admin" else director_pages,
)


if page == "🏠 Accueil":
    render_brand_hero(
        "Pilotez vos rémunérations",
        "Importez les données Backstage, contrôlez chaque niveau de "
        "rémunération et obtenez une vision claire de votre branche.",
        "PRO CONSULTING • TABLEAU DE BORD",
    )

    st.write(
        f"Bienvenue **{current_user_name}** — "
        f"{current_user_direction}"
    )

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
            raw_dataframe = pd.read_excel(
                uploaded_file,
                sheet_name=0,
            )
            prepared_dataframe, detected_columns = (
                prepare_backstage_data(raw_dataframe)
            )

            is_new_file = (
                uploaded_file.name
                != st.session_state.backstage_filename
            )

            st.session_state.backstage_data = prepared_dataframe
            st.session_state.backstage_raw_data = raw_dataframe
            st.session_state.backstage_filename = uploaded_file.name
            st.session_state.detected_columns = detected_columns

            if is_new_file:
                reset_calculations()

            st.success("L’export Backstage a été lu correctement.")

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

    if persistent_settings_available:
        st.success(
            "☁️ Sauvegarde permanente active : les paramètres de votre "
            "direction seront retrouvés après une déconnexion ou un "
            "redémarrage de l’application."
        )
    elif persistent_settings_error:
        st.warning(persistent_settings_error)
    else:
        st.warning(
            "La sauvegarde permanente n’est pas encore configurée. "
            "Les paramètres seront conservés uniquement pendant cette "
            "session."
        )

    financial_settings_locked = current_user_role != "admin"

    if financial_settings_locked:
        st.caption(
            "🔒 Les paramètres financiers sont définis par "
            "l’administrateur et ne peuvent pas être modifiés par "
            "un directeur."
        )

    with st.form("monthly_parameters"):
        left, right = st.columns(2)

        with left:
            month = st.text_input(
                "Mois calculé",
                st.session_state.month,
            )

            revenue_usd = st.number_input(
                "Chiffre d’affaires Backstage ($)",
                min_value=0.0,
                value=float(st.session_state.revenue_usd),
                step=100.0,
            )
