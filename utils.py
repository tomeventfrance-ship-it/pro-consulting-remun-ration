import math
import re
import unicodedata

import pandas as pd


# Noms possibles des colonnes de l’export Backstage
COLUMN_ALIASES = {
    "pseudo": [
        "Nom d'utilisateur du/de la créateur(trice)",
        "Nom d’utilisateur du/de la créateur(trice)",
    ],
    "groupe": [
        "Groupe",
    ],
    "agent": [
        "Agent",
    ],
    "diamants": [
        "Diamants",
    ],
    "duree_live": [
        "Durée de LIVE",
        "Duree de LIVE",
    ],
    "jours_valides": [
        "Jours de passage en LIVE valides",
    ],
    "statut_evolution": [
        "Statut d'évolution",
        "Statut d’évolution",
    ],
    "statut_echelon": [
        "Statut de l'échelon",
        "Statut de l’échelon",
    ],
}


def normalize_text(value: object) -> str:
    """
    Nettoie un texte pour faciliter la comparaison des noms de colonnes.
    """
    text = str(value or "").strip().lower()

    text = unicodedata.normalize("NFKD", text)
    text = "".join(
        character
        for character in text
        if not unicodedata.combining(character)
    )

    text = text.replace("’", "'")
    text = re.sub(r"\s+", " ", text)

    return text


def find_column(
    dataframe: pd.DataFrame,
    possible_names: list[str],
) -> str | None:
    """
    Recherche une colonne même si les accents ou espaces sont différents.
    """
    normalized_columns = {
        normalize_text(column): column
        for column in dataframe.columns
    }

    for possible_name in possible_names:
        normalized_name = normalize_text(possible_name)

        if normalized_name in normalized_columns:
            return normalized_columns[normalized_name]

    return None


def parse_live_duration(value: object) -> float:
    """
    Convertit une durée comme :
    52h 30min 10s
    en nombre d’heures décimal.
    """
    if value is None or pd.isna(value):
        return 0.0

    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip().lower()

    hours_match = re.search(r"(\d+(?:[.,]\d+)?)\s*h", text)
    minutes_match = re.search(r"(\d+(?:[.,]\d+)?)\s*min", text)
    seconds_match = re.search(r"(\d+(?:[.,]\d+)?)\s*s", text)

    hours = (
        float(hours_match.group(1).replace(",", "."))
        if hours_match
        else 0.0
    )

    minutes = (
        float(minutes_match.group(1).replace(",", "."))
        if minutes_match
        else 0.0
    )

    seconds = (
        float(seconds_match.group(1).replace(",", "."))
        if seconds_match
        else 0.0
    )

    return hours + (minutes / 60) + (seconds / 3600)


def floor_to_hundred(value: float) -> int:
    """
    Arrondit toujours à la centaine inférieure.

    Exemple :
    5 856,87 devient 5 800.
    """
    return math.floor(float(value) / 100) * 100


def prepare_backstage_data(
    dataframe: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, str]]:
    """
    Vérifie les colonnes obligatoires et prépare les données Backstage.

    Retourne :
    - un tableau propre ;
    - la correspondance entre nos noms internes
      et les colonnes de l’export.
    """
    detected_columns: dict[str, str] = {}
    missing_columns: list[str] = []

    for internal_name, possible_names in COLUMN_ALIASES.items():
        detected_column = find_column(
            dataframe=dataframe,
            possible_names=possible_names,
        )

        if detected_column is None:
            missing_columns.append(possible_names[0])
        else:
            detected_columns[internal_name] = detected_column

    if missing_columns:
        missing_text = "\n".join(
            f"- {column}"
            for column in missing_columns
        )

        raise ValueError(
            "Colonnes obligatoires absentes de l’export :\n"
            f"{missing_text}"
        )

    prepared_data = pd.DataFrame(
        {
            "Pseudo": dataframe[
                detected_columns["pseudo"]
            ].astype(str).str.strip(),

            "Groupe": dataframe[
                detected_columns["groupe"]
            ].fillna("Sans groupe").astype(str).str.strip(),

            "Agent": dataframe[
                detected_columns["agent"]
            ].fillna("").astype(str).str.strip(),

            "Diamants": pd.to_numeric(
                dataframe[detected_columns["diamants"]],
                errors="coerce",
            ).fillna(0),

            "Heures LIVE": dataframe[
                detected_columns["duree_live"]
            ].apply(parse_live_duration),

            "Jours valides": pd.to_numeric(
                dataframe[detected_columns["jours_valides"]],
                errors="coerce",
            ).fillna(0),

            "Statut évolution": dataframe[
                detected_columns["statut_evolution"]
            ].fillna("").astype(str).str.strip(),

            "Statut échelon": dataframe[
                detected_columns["statut_echelon"]
            ].fillna("").astype(str).str.strip(),
        }
    )

    # Suppression des lignes sans véritable pseudo
    prepared_data = prepared_data[
        prepared_data["Pseudo"].notna()
        & prepared_data["Pseudo"].ne("")
        & prepared_data["Pseudo"].ne("nan")
    ].copy()

    prepared_data["Diamants"] = (
        prepared_data["Diamants"]
        .round(0)
        .astype(int)
    )

    prepared_data["Jours valides"] = (
        prepared_data["Jours valides"]
        .round(0)
        .astype(int)
    )

    prepared_data["Heures LIVE"] = (
        prepared_data["Heures LIVE"]
        .round(2)
    )

    prepared_data.reset_index(
        drop=True,
        inplace=True,
    )

    return prepared_data, detected_columns
