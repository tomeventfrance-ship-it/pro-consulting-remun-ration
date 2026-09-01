"""Moteur isole des tournois Pro Consulting.

Ce module ne depend d'aucune donnee de remuneration. Toutes les operations
sensibles reverifient les droits avec les informations de l'utilisateur
connecte et utilisent des transactions PostgreSQL.
"""

import json
import re
import secrets
from datetime import date, datetime
from zoneinfo import ZoneInfo

import psycopg


TOURNAMENT_FORMATS = {"1v1", "2v2"}
TOURNAMENT_STATUSES = {
    "registration",
    "draw_ready",
    "validated",
    "in_progress",
    "finished",
    "archived",
}


def normalize_email(value):
    return str(value or "").strip().casefold()


def participant_key(value):
    value = str(value or "").strip().lstrip("@").strip()
    return " ".join(value.casefold().split())


def clean_participant_name(value):
    value = " ".join(str(value or "").strip().split())
    value = value.lstrip("@").strip()
    return value[:100]


def parse_participant_batch(value):
    """Accepte un pseudo par ligne ainsi que virgules et points-virgules."""
    candidates = re.split(r"[\n\r,;\t]+", str(value or ""))
    cleaned = []
    seen = set()
    for candidate in candidates:
        name = clean_participant_name(candidate)
        key = participant_key(name)
        if not key or key in seen:
            continue
        seen.add(key)
        cleaned.append(name)
    return cleaned


def _now():
    return datetime.now(ZoneInfo("Europe/Paris"))


def _json_value(value, fallback):
    if value is None:
        return fallback
    if isinstance(value, str):
        value = json.loads(value)
    return value


def _row_to_tournament(row):
    if row is None:
        return None
    columns = (
        "id",
        "title",
        "format",
        "scope_type",
        "owner_email",
        "owner_name",
        "status",
        "registration_deadline",
        "visible_to_managers",
        "solo_policy",
        "participants",
        "competitors",
        "matches",
        "waiting_participant",
        "draw_token",
        "version",
        "created_at",
        "updated_at",
        "updated_by",
    )
    tournament = dict(zip(columns, row))
    for key, fallback in (
        ("participants", []),
        ("competitors", []),
        ("matches", []),
        ("waiting_participant", None),
    ):
        tournament[key] = _json_value(tournament[key], fallback)
    for key in ("registration_deadline", "created_at", "updated_at"):
        if tournament[key] is not None:
            tournament[key] = str(tournament[key])
    return tournament


TOURNAMENT_SELECT = """
    SELECT
        id, title, format, scope_type, owner_email, owner_name, status,
        registration_deadline, visible_to_managers, solo_policy,
        participants, competitors, matches, waiting_participant,
        draw_token, version, created_at, updated_at, updated_by
    FROM pro_consulting_tournaments
"""


def initialize_tournament_database(database_url):
    """Cree uniquement les tables propres aux tournois."""
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS pro_consulting_tournaments (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    format TEXT NOT NULL CHECK (format IN ('1v1', '2v2')),
                    scope_type TEXT NOT NULL
                        CHECK (scope_type IN ('structure', 'branch')),
                    owner_email TEXT NOT NULL,
                    owner_name TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'registration',
                    registration_deadline DATE,
                    visible_to_managers BOOLEAN NOT NULL DEFAULT FALSE,
                    solo_policy TEXT NOT NULL DEFAULT 'waiting',
                    participants JSONB NOT NULL DEFAULT '[]'::jsonb,
                    competitors JSONB NOT NULL DEFAULT '[]'::jsonb,
                    matches JSONB NOT NULL DEFAULT '[]'::jsonb,
                    waiting_participant JSONB,
                    draw_token TEXT,
                    version INTEGER NOT NULL DEFAULT 1,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_by TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS pro_consulting_tournaments_owner
                ON pro_consulting_tournaments (owner_email, status)
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS pro_consulting_tournament_audit (
                    id BIGSERIAL PRIMARY KEY,
                    tournament_id TEXT NOT NULL REFERENCES
                        pro_consulting_tournaments(id) ON DELETE CASCADE,
                    actor_email TEXT NOT NULL,
                    action TEXT NOT NULL,
                    details JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS pro_consulting_tournament_audit_idx
                ON pro_consulting_tournament_audit
                    (tournament_id, created_at DESC)
                """
            )
        connection.commit()
    return True


def _audit(cursor, tournament_id, actor_email, action, details=None):
    cursor.execute(
        """
        INSERT INTO pro_consulting_tournament_audit (
            tournament_id, actor_email, action, details
        ) VALUES (%s, %s, %s, %s::jsonb)
        """,
        (
            tournament_id,
            normalize_email(actor_email),
            action,
            json.dumps(details or {}, ensure_ascii=False),
        ),
    )


def _can_view(tournament, user_email, user_role):
    email = normalize_email(user_email)
    if user_role == "admin":
        return True
    if user_role == "director":
        return (
            tournament["scope_type"] == "structure"
            or normalize_email(tournament["owner_email"]) == email
        )
    return bool(
        user_role == "performance_manager"
        and tournament["visible_to_managers"]
        and tournament["status"]
        in {"validated", "in_progress", "finished"}
    )


def _can_operate(tournament, user_email, user_role):
    email = normalize_email(user_email)
    return bool(
        user_role == "admin"
        or (
            user_role == "director"
            and (
                tournament["scope_type"] == "structure"
                or normalize_email(tournament["owner_email"]) == email
            )
        )
    )


def _can_finalize(tournament, user_email, user_role):
    """Le fondateur valide la structure; un directeur sa propre branche."""
    return bool(
        user_role == "admin"
        or (
            user_role == "director"
            and tournament["scope_type"] == "branch"
            and normalize_email(tournament["owner_email"])
            == normalize_email(user_email)
        )
    )


def list_tournaments(database_url, user_email, user_role):
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(TOURNAMENT_SELECT + " ORDER BY updated_at DESC")
            rows = cursor.fetchall()
    tournaments = [_row_to_tournament(row) for row in rows]
    return [
        tournament
        for tournament in tournaments
        if _can_view(tournament, user_email, user_role)
    ]


def load_tournament(database_url, tournament_id, user_email, user_role):
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(TOURNAMENT_SELECT + " WHERE id = %s", (tournament_id,))
            tournament = _row_to_tournament(cursor.fetchone())
    if tournament is None or not _can_view(tournament, user_email, user_role):
        raise PermissionError("Tournoi introuvable ou non autorise.")
    return tournament


def create_tournament(
    database_url,
    title,
    tournament_format,
    registration_deadline,
    creator_email,
    creator_name,
    creator_role,
):
    title = " ".join(str(title or "").strip().split())[:120]
    if not title:
        raise ValueError("Le titre du tournoi est obligatoire.")
    if tournament_format not in TOURNAMENT_FORMATS:
        raise ValueError("Format de tournoi invalide.")
    if creator_role not in {"admin", "director"}:
        raise PermissionError("Ce compte ne peut pas creer de tournoi.")
    scope_type = "structure" if creator_role == "admin" else "branch"
    tournament_id = secrets.token_hex(12)
    deadline = registration_deadline or None
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO pro_consulting_tournaments (
                    id, title, format, scope_type, owner_email, owner_name,
                    registration_deadline, updated_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    tournament_id,
                    title,
                    tournament_format,
                    scope_type,
                    normalize_email(creator_email),
                    str(creator_name or "").strip(),
                    deadline,
                    normalize_email(creator_email),
                ),
            )
            _audit(
                cursor,
                tournament_id,
                creator_email,
                "tournament_created",
                {"format": tournament_format, "scope": scope_type},
            )
        connection.commit()
    return tournament_id


def _load_locked(cursor, tournament_id):
    cursor.execute(TOURNAMENT_SELECT + " WHERE id = %s FOR UPDATE", (tournament_id,))
    tournament = _row_to_tournament(cursor.fetchone())
    if tournament is None:
        raise ValueError("Tournoi introuvable.")
    return tournament


def add_participants(
    database_url,
    tournament_id,
    names,
    actor_email,
    actor_name,
    actor_role,
):
    names = parse_participant_batch(names) if isinstance(names, str) else [
        clean_participant_name(name) for name in names
    ]
    names = [name for name in names if participant_key(name)]
    if not names:
        raise ValueError("Aucun pseudo valide n'a ete trouve.")
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            tournament = _load_locked(cursor, tournament_id)
            if not _can_operate(tournament, actor_email, actor_role):
                raise PermissionError("Ajout non autorise.")
            if tournament["status"] != "registration":
                raise ValueError("Les inscriptions sont fermees.")
            participants = list(tournament["participants"])
            existing = {
                participant_key(row.get("name"))
                for row in participants
                if isinstance(row, dict)
            }
            added = []
            duplicates = []
            timestamp = _now().isoformat(timespec="seconds")
            for name in names:
                key = participant_key(name)
                if key in existing:
                    duplicates.append(name)
                    continue
                existing.add(key)
                participant = {
                    "id": secrets.token_hex(8),
                    "name": name,
                    "added_by": normalize_email(actor_email),
                    "added_by_name": str(actor_name or "").strip(),
                    "added_at": timestamp,
                }
                participants.append(participant)
                added.append(name)
            cursor.execute(
                """
                UPDATE pro_consulting_tournaments
                SET participants = %s::jsonb, version = version + 1,
                    updated_at = CURRENT_TIMESTAMP, updated_by = %s
                WHERE id = %s
                """,
                (
                    json.dumps(participants, ensure_ascii=False),
                    normalize_email(actor_email),
                    tournament_id,
                ),
            )
            _audit(
                cursor,
                tournament_id,
                actor_email,
                "participants_added",
                {"added": added, "duplicates": duplicates},
            )
        connection.commit()
    return {"added": added, "duplicates": duplicates}


def remove_participant(
    database_url, tournament_id, participant_id, actor_email, actor_role
):
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            tournament = _load_locked(cursor, tournament_id)
            if not _can_operate(tournament, actor_email, actor_role):
                raise PermissionError("Suppression non autorisee.")
            if tournament["status"] != "registration":
                raise ValueError("Reouvrez les inscriptions avant de supprimer.")
            participants = list(tournament["participants"])
            removed = [row for row in participants if row.get("id") == participant_id]
            participants = [row for row in participants if row.get("id") != participant_id]
            if not removed:
                raise ValueError("Participant introuvable.")
            cursor.execute(
                """
                UPDATE pro_consulting_tournaments
                SET participants = %s::jsonb, version = version + 1,
                    updated_at = CURRENT_TIMESTAMP, updated_by = %s
                WHERE id = %s
                """,
                (
                    json.dumps(participants, ensure_ascii=False),
                    normalize_email(actor_email),
                    tournament_id,
                ),
            )
            _audit(cursor, tournament_id, actor_email, "participant_removed", {"name": removed[0].get("name")})
        connection.commit()


def _competitor(members):
    return {
        "id": secrets.token_hex(8),
        "members": [member["name"] for member in members],
        "label": " + ".join(member["name"] for member in members),
    }


def prepare_competitors(participants, tournament_format, solo_policy="waiting"):
    """Melange les inscrits puis cree individus ou duos sans biais de liste."""
    participants = [dict(row) for row in participants]
    randomizer = secrets.SystemRandom()
    randomizer.shuffle(participants)
    waiting_participant = None
    if tournament_format == "1v1":
        competitors = [_competitor([participant]) for participant in participants]
    elif tournament_format == "2v2":
        competitors = []
        while len(participants) >= 2:
            competitors.append(_competitor(participants[:2]))
            participants = participants[2:]
        if participants:
            if solo_policy == "solo":
                competitors.append(_competitor(participants))
            else:
                waiting_participant = participants[0]
    else:
        raise ValueError("Format de tournoi invalide.")
    # Tirage des adversaires independant du tirage des duos.
    randomizer.shuffle(competitors)
    return competitors, waiting_participant


def _round_label(competitor_count, match_count, round_number):
    if match_count == 1:
        return "Finale"
    if match_count == 2:
        return "Demi-finales"
    if match_count <= 4:
        return "Quarts de finale"
    if match_count <= 8:
        return "Huitiemes de finale"
    return "Premier tour" if round_number == 1 else f"Tour {round_number}"


def build_round(competitors, tournament_format, round_number):
    """Construit un tour sans favoriser l'ordre d'inscription."""
    competitors = [dict(row) for row in competitors]
    randomizer = secrets.SystemRandom()
    randomizer.shuffle(competitors)
    groups = []
    if tournament_format == "1v1" and len(competitors) % 2 == 1:
        if len(competitors) >= 3:
            groups.append(competitors[:3])
            competitors = competitors[3:]
    while len(competitors) >= 2:
        groups.append(competitors[:2])
        competitors = competitors[2:]
    if competitors:
        groups.append(competitors)

    label = _round_label(
        sum(len(group) for group in groups),
        len(groups),
        round_number,
    )
    matches = []
    for index, contestants in enumerate(groups, start=1):
        bye = len(contestants) == 1
        matches.append(
            {
                "id": secrets.token_hex(8),
                "round_number": round_number,
                "round_label": label,
                "match_number": index,
                "contestants": contestants,
                "winner_id": contestants[0]["id"] if bye else None,
                "date": "",
                "time": "",
                "bye": bye,
                "updated_by": "automatic" if bye else "",
                "updated_at": _now().isoformat(timespec="seconds") if bye else "",
            }
        )
    return matches


def finalize_draw(
    database_url,
    tournament_id,
    actor_email,
    actor_role,
    solo_policy="waiting",
    force_redraw=False,
    preview_only=False,
):
    if solo_policy not in {"waiting", "solo"}:
        raise ValueError("Gestion du participant seul invalide.")
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            tournament = _load_locked(cursor, tournament_id)
            if not _can_finalize(tournament, actor_email, actor_role):
                raise PermissionError("Tirage non autorise.")
            if tournament["status"] != "registration":
                if not (actor_role == "admin" and force_redraw):
                    raise ValueError("Le tirage est deja valide.")
            participants = [dict(row) for row in tournament["participants"]]
            minimum = 2 if tournament["format"] == "1v1" else 3
            if len(participants) < minimum:
                raise ValueError("Nombre de participants insuffisant.")

            competitors, waiting_participant = prepare_competitors(
                participants,
                tournament["format"],
                solo_policy,
            )
            if len(competitors) < 2:
                raise ValueError("Il faut au moins deux equipes pour lancer le tournoi.")
            matches = build_round(competitors, tournament["format"], 1)
            draw_token = secrets.token_hex(12)
            target_status = "draw_ready" if preview_only else "validated"
            cursor.execute(
                """
                UPDATE pro_consulting_tournaments
                SET status = %s, solo_policy = %s,
                    competitors = %s::jsonb, matches = %s::jsonb,
                    waiting_participant = %s::jsonb, draw_token = %s,
                    visible_to_managers = FALSE, version = version + 1,
                    updated_at = CURRENT_TIMESTAMP, updated_by = %s
                WHERE id = %s
                """,
                (
                    target_status,
                    solo_policy,
                    json.dumps(competitors, ensure_ascii=False),
                    json.dumps(matches, ensure_ascii=False),
                    json.dumps(waiting_participant, ensure_ascii=False),
                    draw_token,
                    normalize_email(actor_email),
                    tournament_id,
                ),
            )
            _audit(
                cursor,
                tournament_id,
                actor_email,
                (
                    "draw_preview_created"
                    if preview_only and not force_redraw
                    else "draw_restarted"
                    if force_redraw
                    else "draw_validated"
                ),
                {
                    "draw_token": draw_token,
                    "competitors": len(competitors),
                    "waiting": waiting_participant.get("name") if waiting_participant else None,
                },
            )
        connection.commit()
    return draw_token


def validate_prepared_draw(
    database_url, tournament_id, actor_email, actor_role
):
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            tournament = _load_locked(cursor, tournament_id)
            if not _can_finalize(tournament, actor_email, actor_role):
                raise PermissionError("Validation non autorisee.")
            if tournament["status"] != "draw_ready" or not tournament["matches"]:
                raise ValueError("Aucun tirage en attente de validation.")
            cursor.execute(
                """
                UPDATE pro_consulting_tournaments
                SET status = 'validated', version = version + 1,
                    updated_at = CURRENT_TIMESTAMP, updated_by = %s
                WHERE id = %s
                """,
                (normalize_email(actor_email), tournament_id),
            )
            _audit(cursor, tournament_id, actor_email, "draw_validated")
        connection.commit()


def _winner_from_match(match):
    return next(
        (
            dict(row)
            for row in match.get("contestants", [])
            if row.get("id") == match.get("winner_id")
        ),
        None,
    )


def _advance_if_complete(matches, tournament_format):
    current_round = max((row.get("round_number", 0) for row in matches), default=0)
    current_matches = [row for row in matches if row.get("round_number") == current_round]
    if not current_matches or any(not row.get("winner_id") for row in current_matches):
        return matches, "in_progress", None
    winners = [_winner_from_match(match) for match in current_matches]
    winners = [winner for winner in winners if winner]
    if len(winners) == 1:
        return matches, "finished", winners[0]
    next_round = build_round(winners, tournament_format, current_round + 1)
    return matches + next_round, "in_progress", None


def set_match_winner(
    database_url,
    tournament_id,
    match_id,
    winner_id,
    actor_email,
    actor_role,
):
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            tournament = _load_locked(cursor, tournament_id)
            if not _can_operate(tournament, actor_email, actor_role):
                raise PermissionError("Resultat non autorise.")
            if tournament["status"] not in {"validated", "in_progress", "finished"}:
                raise ValueError("Le tirage doit etre valide avant les resultats.")
            matches = [dict(row) for row in tournament["matches"]]
            target = next((row for row in matches if row.get("id") == match_id), None)
            if target is None or target.get("bye"):
                raise ValueError("Match introuvable ou automatiquement qualifie.")
            latest_round = max(row.get("round_number", 0) for row in matches)
            target_round = target.get("round_number", 0)
            if target_round != latest_round:
                if actor_role != "admin":
                    raise PermissionError("Seul le fondateur peut corriger un ancien tour.")
                matches = [row for row in matches if row.get("round_number", 0) <= target_round]
                target = next(row for row in matches if row.get("id") == match_id)
            allowed_winners = {row.get("id") for row in target.get("contestants", [])}
            if winner_id not in allowed_winners:
                raise ValueError("Le gagnant ne participe pas a ce match.")
            target["winner_id"] = winner_id
            target["updated_by"] = normalize_email(actor_email)
            target["updated_at"] = _now().isoformat(timespec="seconds")
            matches, status, champion = _advance_if_complete(matches, tournament["format"])
            cursor.execute(
                """
                UPDATE pro_consulting_tournaments
                SET matches = %s::jsonb, status = %s, version = version + 1,
                    updated_at = CURRENT_TIMESTAMP, updated_by = %s
                WHERE id = %s
                """,
                (
                    json.dumps(matches, ensure_ascii=False),
                    status,
                    normalize_email(actor_email),
                    tournament_id,
                ),
            )
            _audit(
                cursor,
                tournament_id,
                actor_email,
                "winner_recorded",
                {
                    "match_id": match_id,
                    "winner_id": winner_id,
                    "champion": champion.get("label") if champion else None,
                },
            )
        connection.commit()
    return status, champion


def update_match_schedule(
    database_url,
    tournament_id,
    match_id,
    match_date,
    match_time,
    actor_email,
    actor_role,
):
    if actor_role != "admin":
        raise PermissionError("Les dates et heures sont reservees au fondateur.")
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            tournament = _load_locked(cursor, tournament_id)
            matches = [dict(row) for row in tournament["matches"]]
            target = next((row for row in matches if row.get("id") == match_id), None)
            if target is None:
                raise ValueError("Match introuvable.")
            target["date"] = str(match_date or "").strip()[:20]
            target["time"] = str(match_time or "").strip()[:10]
            cursor.execute(
                """
                UPDATE pro_consulting_tournaments
                SET matches = %s::jsonb, version = version + 1,
                    updated_at = CURRENT_TIMESTAMP, updated_by = %s
                WHERE id = %s
                """,
                (
                    json.dumps(matches, ensure_ascii=False),
                    normalize_email(actor_email),
                    tournament_id,
                ),
            )
            _audit(cursor, tournament_id, actor_email, "schedule_updated", {"match_id": match_id})
        connection.commit()


def update_tournament_options(
    database_url,
    tournament_id,
    actor_email,
    actor_role,
    title=None,
    registration_deadline=None,
    visible_to_managers=None,
    archive=None,
):
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            tournament = _load_locked(cursor, tournament_id)
            owner_director = bool(
                actor_role == "director"
                and tournament["scope_type"] == "branch"
                and normalize_email(tournament["owner_email"])
                == normalize_email(actor_email)
            )
            if actor_role != "admin" and not owner_director:
                raise PermissionError("Modification non autorisee.")
            if actor_role != "admin" and (
                visible_to_managers is not None or archive is not None
            ):
                raise PermissionError(
                    "Visibilite et archivage reserves au fondateur."
                )
            new_title = tournament["title"] if title is None else " ".join(str(title).strip().split())[:120]
            deadline = tournament["registration_deadline"] if registration_deadline is None else registration_deadline
            visible = tournament["visible_to_managers"] if visible_to_managers is None else bool(visible_to_managers)
            status = "archived" if archive is True else tournament["status"]
            if archive is False and status == "archived":
                status = "finished" if tournament["matches"] else "registration"
            cursor.execute(
                """
                UPDATE pro_consulting_tournaments
                SET title = %s, registration_deadline = %s,
                    visible_to_managers = %s, status = %s,
                    version = version + 1, updated_at = CURRENT_TIMESTAMP,
                    updated_by = %s
                WHERE id = %s
                """,
                (new_title, deadline, visible, status, normalize_email(actor_email), tournament_id),
            )
            _audit(cursor, tournament_id, actor_email, "options_updated", {"visible": visible, "status": status})
        connection.commit()


def reopen_registrations(database_url, tournament_id, actor_email, actor_role):
    if actor_role != "admin":
        raise PermissionError("Seul le fondateur peut rouvrir les inscriptions.")
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            _load_locked(cursor, tournament_id)
            cursor.execute(
                """
                UPDATE pro_consulting_tournaments
                SET status = 'registration', competitors = '[]'::jsonb,
                    matches = '[]'::jsonb, waiting_participant = NULL,
                    draw_token = NULL, visible_to_managers = FALSE,
                    version = version + 1, updated_at = CURRENT_TIMESTAMP,
                    updated_by = %s
                WHERE id = %s
                """,
                (normalize_email(actor_email), tournament_id),
            )
            _audit(cursor, tournament_id, actor_email, "registrations_reopened")
        connection.commit()


def delete_tournament(
    database_url,
    tournament_id,
    actor_email,
    actor_role,
):
    """Supprime un tournoi et son journal, uniquement pour le fondateur."""
    if actor_role != "admin":
        raise PermissionError("Seul le fondateur peut supprimer un tournoi.")
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            tournament = _load_locked(cursor, tournament_id)
            deleted_title = tournament["title"]
            cursor.execute(
                "DELETE FROM pro_consulting_tournaments WHERE id = %s",
                (tournament_id,),
            )
            if cursor.rowcount != 1:
                raise RuntimeError("La suppression n'a pas ete confirmee.")
        connection.commit()
    return deleted_title


def tournament_tables(tournament):
    participants = [
        {
            "Créateur": row.get("name", ""),
            "Ajouté par": row.get("added_by_name") or row.get("added_by", ""),
            "Ajouté le": row.get("added_at", ""),
        }
        for row in tournament.get("participants", [])
    ]
    matches = []
    for match in tournament.get("matches", []):
        winner = _winner_from_match(match)
        matches.append(
            {
                "Tour": match.get("round_label", ""),
                "Match": match.get("match_number", ""),
                "Date": match.get("date", ""),
                "Heure": match.get("time", ""),
                "Adversaires": "  VS  ".join(
                    row.get("label", "") for row in match.get("contestants", [])
                ),
                "Gagnant": winner.get("label", "") if winner else "",
                "Exempté": "Oui" if match.get("bye") else "Non",
            }
        )
    return participants, matches
