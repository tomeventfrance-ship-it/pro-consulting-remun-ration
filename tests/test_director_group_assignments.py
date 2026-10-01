"""Régressions des droits d’import, sans connexion aux données de production.

L’application Streamlit exécute son interface dès l’import. On charge donc
uniquement les fonctions testées depuis son AST.
"""

import ast
import copy
import json
from pathlib import Path
import re
from types import SimpleNamespace
import unicodedata
import unittest
from unittest.mock import Mock
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"
ADMIN_EMAIL = "tomeventfrance@gmail.com"
MAX_EMAIL = "melvynschmidt2013@gmail.com"
BIKER_EMAIL = "a.stone.authorbusiness@gmail.com"
MAX_GROUPS = [
    "DIRECTION MAX", "MANAGER ALPHA", "MANAGER ROMAIN", "MANAGER CHRIS"
]


def load_functions():
    names = {
        "normalize_email", "director_management_scope", "collaborator_access_scope",
        "clean_collaborator_access_records", "build_authorized_users",
        "default_director_management_config", "clean_director_management_config",
        "normalize_group_name", "merge_director_group_assignments",
        "save_director_group_assignments", "queue_director_group_assignment",
        "validate_director_import_groups",
    }
    constants = {
        "BASE_AUTHORIZED_USERS", "COLLABORATOR_ROLE_LABELS",
        "DIRECTOR_MANAGEMENT_PROFILES",
    }
    nodes = []
    for node in ast.parse(APP_PATH.read_text()).body:
        if isinstance(node, ast.FunctionDef) and node.name in names:
            nodes.append(node)
        elif isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id in constants
            for target in node.targets
        ):
            nodes.append(node)
    namespace = {
        "re": re, "unicodedata": unicodedata, "json": json,
        "datetime": datetime, "ZoneInfo": ZoneInfo,
    }
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(APP_PATH), "exec"), namespace)
    return namespace


class FakeCursor:
    def __init__(self, database):
        self.database = database
        self.response = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, query, parameters):
        self.database.queries.append(query)
        if "SELECT payload" in query:
            self.response = (copy.deepcopy(self.database.working),)
        elif "UPDATE pro_consulting_settings" in query:
            self.database.working = json.loads(parameters[0])
            self.response = (
                None if self.database.fail_confirmation
                else (copy.deepcopy(self.database.working),)
            )

    def fetchone(self):
        return self.response


class FakeDatabase:
    def __init__(self, payload, fail_confirmation=False):
        self.payload = copy.deepcopy(payload)
        self.working = copy.deepcopy(payload)
        self.fail_confirmation = fail_confirmation
        self.queries = []
        self.committed = False

    def __enter__(self):
        return self

    def __exit__(self, exception_type, *args):
        if exception_type:
            self.working = copy.deepcopy(self.payload)
        return False

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        self.payload = copy.deepcopy(self.working)
        self.committed = True


class FakeSessionState(dict):
    def __setattr__(self, name, value):
        self[name] = value


class DirectorGroupTests(unittest.TestCase):
    def setUp(self):
        self.functions = load_functions()
        self.payload = {
            "directors": {
                MAX_EMAIL: {
                    "groups": MAX_GROUPS[:-1], "revenue_usd": 2325.36,
                    "other_expenses": 84.5, "note": "à conserver",
                },
                BIKER_EMAIL: {
                    "groups": ["MANAGER BIKER"], "revenue_usd": 800,
                    "other_expenses": 12,
                },
            },
            "saved_at": "2026-09-30", "extra_metadata": {"keep": True},
        }
        self.fresh = {
            "admin:director_management": copy.deepcopy(self.payload),
            "admin:collaborator_access": {"collaborators": []},
        }
        self.cached_loader = Mock(return_value=copy.deepcopy(self.fresh))
        self.fresh_loader = Mock(side_effect=lambda *args: copy.deepcopy(self.fresh))
        self.functions.update({
            "initialize_settings_database": Mock(),
            "load_authorization_payloads": self.cached_loader,
            "load_persistent_scopes": self.fresh_loader,
            "AUTHORIZED_USERS": {MAX_EMAIL: {"role": "director", "groups": MAX_GROUPS}},
        })

    def validate(self, groups, email=MAX_EMAIL):
        return self.functions["validate_director_import_groups"](
            pd.DataFrame({"Groupe": groups}), email, "test-database"
        )

    def test_added_chris_is_allowed_despite_stale_cached_rights(self):
        self.fresh["admin:director_management"]["directors"][MAX_EMAIL]["groups"] = MAX_GROUPS
        result = self.validate(MAX_GROUPS)
        self.assertTrue(result["valid"], result)
        self.cached_loader.assert_not_called()
        self.fresh_loader.assert_called_once()

    def test_removed_group_is_rejected_despite_stale_session_rights(self):
        result = self.validate(MAX_GROUPS)
        self.assertFalse(result["valid"])
        self.assertEqual(result["unexpected_groups"], ["MANAGER CHRIS"])

    def test_another_directors_group_stays_forbidden(self):
        result = self.validate(MAX_GROUPS[:-1] + ["MANAGER BIKER"])
        self.assertFalse(result["valid"])
        self.assertEqual(result["unexpected_groups"], ["MANAGER BIKER"])

    def test_missing_assigned_group_still_blocks_import(self):
        result = self.validate(MAX_GROUPS[:2])
        self.assertFalse(result["valid"])
        self.assertEqual(result["missing_groups"], ["MANAGER ROMAIN"])

    def test_database_failure_blocks_import(self):
        self.fresh_loader.side_effect = RuntimeError("database unavailable")
        result = self.validate(MAX_GROUPS)
        self.assertFalse(result["valid"])
        self.assertIn("ne peuvent pas être relus", result["error"])

    def test_managed_director_uses_fresh_collaborator_assignments(self):
        self.fresh["admin:collaborator_access"]["collaborators"] = [{
            "email": "new@example.com", "name": "New", "role": "director",
            "active": True, "groups": ["MANAGER NEW"],
        }]
        self.assertTrue(self.validate(["MANAGER NEW"], "new@example.com")["valid"])

    def test_group_absent_from_current_export_is_preserved(self):
        cleaned = self.functions["clean_director_management_config"](
            self.payload["directors"], ["DIRECTION MAX"]
        )
        self.assertEqual(cleaned[MAX_EMAIL]["groups"], MAX_GROUPS[:-1])
        self.assertEqual(cleaned[MAX_EMAIL]["revenue_usd"], 2325.36)
        self.assertEqual(cleaned[MAX_EMAIL]["other_expenses"], 84.5)

    def test_group_spelling_maps_to_current_export_without_losing_assignments(self):
        self.payload["directors"][MAX_EMAIL]["groups"] = [
            " MANAGER  CHRIS ", "manager chris", "MANAGER ROMAIN"
        ]
        cleaned = self.functions["clean_director_management_config"](
            self.payload["directors"], ["Manager Chris"]
        )
        self.assertEqual(cleaned[MAX_EMAIL]["groups"], ["Manager Chris", "MANAGER ROMAIN"])

    def test_group_addition_preserves_finances_metadata_and_other_directors(self):
        original = copy.deepcopy(self.payload)
        merged = self.functions["merge_director_group_assignments"](
            self.payload, {MAX_EMAIL: MAX_GROUPS}
        )
        self.assertEqual(merged["directors"][MAX_EMAIL]["groups"], MAX_GROUPS)
        self.assertEqual(merged["directors"][MAX_EMAIL]["revenue_usd"], 2325.36)
        self.assertEqual(merged["directors"][MAX_EMAIL]["other_expenses"], 84.5)
        self.assertEqual(merged["directors"][MAX_EMAIL]["note"], "à conserver")
        self.assertEqual(merged["directors"][BIKER_EMAIL], original["directors"][BIKER_EMAIL])
        self.assertEqual(merged["extra_metadata"], original["extra_metadata"])
        self.assertEqual(self.payload, original)

    def test_group_removal_does_not_remove_financial_rows(self):
        merged = self.functions["merge_director_group_assignments"](
            self.payload, {MAX_EMAIL: []}
        )
        self.assertEqual(merged["directors"][MAX_EMAIL]["groups"], [])
        self.assertEqual(merged["directors"][MAX_EMAIL]["revenue_usd"], 2325.36)

    def test_conflict_checks_normalized_names_and_preserves_source(self):
        original = copy.deepcopy(self.payload)
        with self.assertRaises(ValueError):
            self.functions["merge_director_group_assignments"](
                self.payload, {MAX_EMAIL: MAX_GROUPS + [" responsable performance : biker "]}
            )
        self.assertEqual(self.payload, original)

    def attach_database(self, fail_confirmation=False):
        database = FakeDatabase(self.payload, fail_confirmation)
        connect = Mock(return_value=database)
        self.functions["psycopg"] = SimpleNamespace(connect=connect)
        return database, connect

    def test_save_locks_and_confirms_groups_without_saving_financial_drafts(self):
        database, connect = self.attach_database()
        confirmed = self.functions["save_director_group_assignments"](
            "test-database", {MAX_EMAIL: MAX_GROUPS}, ADMIN_EMAIL
        )
        self.assertTrue(database.committed)
        self.assertEqual(confirmed["directors"][MAX_EMAIL]["revenue_usd"], 2325.36)
        self.assertEqual(confirmed["directors"][MAX_EMAIL]["groups"], MAX_GROUPS)
        self.assertTrue(any("FOR UPDATE" in query for query in database.queries))
        self.cached_loader.clear.assert_called_once()

    def test_director_cannot_assign_groups(self):
        database, connect = self.attach_database()
        with self.assertRaises(PermissionError):
            self.functions["save_director_group_assignments"](
                "test-database", {MAX_EMAIL: MAX_GROUPS}, MAX_EMAIL
            )
        connect.assert_not_called()

    def test_widget_callback_queues_groups_and_keeps_financial_drafts(self):
        session = FakeSessionState({
            "admin_director_groups_max": MAX_GROUPS,
            "admin_director_revenue_max": 9999.99,
        })
        self.functions["st"] = SimpleNamespace(session_state=session)
        self.functions["queue_director_group_assignment"](
            MAX_EMAIL, "admin_director_groups_max"
        )
        self.assertEqual(session["pending_director_group_assignments"], {
            MAX_EMAIL: MAX_GROUPS,
        })
        self.assertEqual(session["admin_director_revenue_max"], 9999.99)
        self.assertIsNot(
            session["pending_director_group_assignments"][MAX_EMAIL],
            session["admin_director_groups_max"],
        )

    def test_failed_confirmation_rolls_back_and_keeps_previous_rights(self):
        database, connect = self.attach_database(fail_confirmation=True)
        with self.assertRaises(RuntimeError):
            self.functions["save_director_group_assignments"](
                "test-database", {MAX_EMAIL: MAX_GROUPS}, ADMIN_EMAIL
            )
        self.assertFalse(database.committed)
        self.assertEqual(database.payload, self.payload)
        self.cached_loader.clear.assert_not_called()


if __name__ == "__main__":
    unittest.main()
