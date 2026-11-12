"""Vérifie les retraits d’accès sans utiliser les comptes de production."""

import copy
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

import pandas as pd

from test_director_group_assignments import (
    ADMIN_EMAIL,
    BIKER_EMAIL,
    MAX_EMAIL,
    FakeDatabase,
    load_functions,
)


ACCESS_SCOPE = "admin:collaborator_access"
DIRECTOR_SCOPE = "admin:director_management"
MANAGER_EMAIL = "manager@example.com"
ADDED_DIRECTOR_EMAIL = "director@example.com"


class CollaboratorDepartureTests(unittest.TestCase):
    def setUp(self):
        self.functions = load_functions()
        self.original = {
            ACCESS_SCOPE: {
                "collaborators": [
                    {
                        "email": MANAGER_EMAIL,
                        "name": "Responsable Test",
                        "role": "performance_manager",
                        "groups": ["MANAGER CHRIS"],
                        "active": True,
                        "note": "historique à conserver",
                    },
                    {
                        "email": ADDED_DIRECTOR_EMAIL,
                        "name": "Directeur Test",
                        "role": "director",
                        "groups": ["AUTRE GROUPE"],
                        "active": True,
                    },
                ],
                "other_metadata": "à conserver",
            },
            DIRECTOR_SCOPE: {
                "directors": {
                    MAX_EMAIL: {
                        "groups": ["MANAGER CHRIS"],
                        "revenue_usd": 1250.0,
                        "other_expenses": 75.0,
                    },
                    BIKER_EMAIL: {
                        "groups": ["MANAGER BIKER"],
                        "revenue_usd": 950.0,
                    },
                },
            },
            f"backstage:{MAX_EMAIL}": {"filename": "export.xlsx"},
            f"exclusions:{MAX_EMAIL}": {"rows": []},
        }
        self.database = FakeDatabase({}, scopes=self.original)
        self.connect = Mock(return_value=self.database)
        self.cached = Mock(return_value=copy.deepcopy(self.original))
        self.functions.update({
            "initialize_settings_database": Mock(),
            "load_authorization_payloads": self.cached,
            "load_persistent_scopes": self.load_current_scopes,
            "psycopg": SimpleNamespace(connect=self.connect),
        })

    def load_current_scopes(self, database_url, scopes):
        return {
            scope: copy.deepcopy(self.database.scopes.get(scope, {}))
            for scope in scopes
        }

    def set_status(self, email, active, actor=ADMIN_EMAIL, groups=None):
        return self.functions["update_authorization_scope"](
            "test-database", ACCESS_SCOPE, actor,
            lambda payloads: self.functions["change_collaborator_status"](
                payloads, email, active, groups
            ),
        )

    def authorized_users(self):
        users, error = self.functions["build_authorized_users"](
            "test-database", refresh=True
        )
        self.assertIsNone(error)
        return users

    def test_archived_original_director_loses_access_and_leaves_active_view(self):
        self.set_status(f" {MAX_EMAIL.upper()} ", False)
        users = self.authorized_users()
        self.assertNotIn(MAX_EMAIL, users)
        self.assertIn(BIKER_EMAIL, users)
        self.assertIn(MANAGER_EMAIL, users)
        profiles = self.functions["active_director_profiles"](users)
        self.assertNotIn(MAX_EMAIL, [profile["email"] for profile in profiles])
        self.assertEqual(
            self.database.scopes[DIRECTOR_SCOPE], self.original[DIRECTOR_SCOPE]
        )
        self.assertEqual(
            self.database.scopes[f"backstage:{MAX_EMAIL}"],
            self.original[f"backstage:{MAX_EMAIL}"],
        )
        self.assertEqual(
            self.database.scopes[f"exclusions:{MAX_EMAIL}"],
            self.original[f"exclusions:{MAX_EMAIL}"],
        )
        self.cached.assert_not_called()
        import_result = self.functions["validate_director_import_groups"](
            pd.DataFrame({"Groupe": ["MANAGER CHRIS"]}),
            MAX_EMAIL,
            "test-database",
        )
        self.assertFalse(import_result["valid"])

    def test_archiving_manager_or_added_director_preserves_each_profile(self):
        for email in (MANAGER_EMAIL, ADDED_DIRECTOR_EMAIL):
            self.set_status(email, False)
        self.assertNotIn(MANAGER_EMAIL, self.authorized_users())
        self.assertNotIn(ADDED_DIRECTOR_EMAIL, self.authorized_users())
        original_rows = self.original[ACCESS_SCOPE]["collaborators"]
        archived_rows = self.database.scopes[ACCESS_SCOPE]["collaborators"]
        self.assertEqual(archived_rows, [{**row, "active": False} for row in original_rows])
        self.assertEqual(
            self.database.scopes[ACCESS_SCOPE]["other_metadata"], "à conserver"
        )

    def test_other_updates_do_not_restore_an_archived_access(self):
        self.set_status(MAX_EMAIL, False)
        self.set_status(MANAGER_EMAIL, False)
        update = self.functions["update_collaborator_profiles"]
        self.functions["update_authorization_scope"](
            "test-database", ACCESS_SCOPE, ADMIN_EMAIL,
            lambda payloads: update(payloads, [{
                "email": "new@example.com", "name": "Nouvelle personne",
                "role": "performance_manager", "groups": ["NOUVEAU GROUPE"],
            }], create=True),
        )
        users = self.authorized_users()
        self.assertNotIn(MAX_EMAIL, users)
        self.assertNotIn(MANAGER_EMAIL, users)
        self.assertIn("new@example.com", users)
        previous = copy.deepcopy(self.database.scopes)
        with self.assertRaises(ValueError):
            self.functions["update_authorization_scope"](
                "test-database", ACCESS_SCOPE, ADMIN_EMAIL,
                lambda payloads: update(
                    payloads, [self.original[ACCESS_SCOPE]["collaborators"][0]]
                ),
            )
        self.assertEqual(self.database.scopes, previous)

    def test_restore_returns_existing_role_and_group_access(self):
        for email in (MAX_EMAIL, MANAGER_EMAIL):
            self.set_status(email, False)
            self.set_status(email, True)
        users = self.authorized_users()
        self.assertEqual(users[MAX_EMAIL]["groups"], ["MANAGER CHRIS"])
        self.assertEqual(users[MANAGER_EMAIL]["role"], "performance_manager")
        self.assertEqual(users[MANAGER_EMAIL]["groups"], ["MANAGER CHRIS"])

    def test_legacy_inactive_account_can_restore_with_a_group(self):
        record = self.database.scopes[ACCESS_SCOPE]["collaborators"][0]
        record.update({"active": False, "groups": []})
        self.database.working = copy.deepcopy(self.database.scopes)
        self.assertNotIn(MANAGER_EMAIL, self.authorized_users())
        with self.assertRaises(ValueError):
            self.set_status(MANAGER_EMAIL, True)
        self.set_status(MANAGER_EMAIL, True, groups=["MANAGER CHRIS"])
        self.assertEqual(self.authorized_users()[MANAGER_EMAIL]["groups"], ["MANAGER CHRIS"])

    def test_group_reassignment_preserves_archive_and_prevents_double_access(self):
        self.set_status(MAX_EMAIL, False)
        self.functions["save_director_group_assignments"](
            "test-database", {BIKER_EMAIL: ["MANAGER BIKER", "Manager : Chris"]},
            ADMIN_EMAIL, financial_rows={
                BIKER_EMAIL: {"revenue_usd": 1025.0, "other_expenses": 10.0}
            },
        )
        self.assertEqual(
            self.database.payload["directors"][MAX_EMAIL],
            self.original[DIRECTOR_SCOPE]["directors"][MAX_EMAIL],
        )
        self.assertEqual(self.database.payload["directors"][BIKER_EMAIL]["revenue_usd"], 1025.0)
        with self.assertRaisesRegex(ValueError, "Groupes déjà attribués à Biker"):
            self.set_status(MAX_EMAIL, True)
        self.assertNotIn(MAX_EMAIL, self.authorized_users())

    def test_founder_cannot_be_archived_and_manager_cannot_change_access(self):
        with self.assertRaises(PermissionError):
            self.set_status(MAX_EMAIL, False, actor=MANAGER_EMAIL)
        self.connect.assert_not_called()
        with self.assertRaises(ValueError):
            self.set_status(ADMIN_EMAIL, False)
        self.assertEqual(self.database.scopes, self.original)
        self.assertIn(ADMIN_EMAIL, self.authorized_users())

    def test_failed_status_save_keeps_all_previous_access(self):
        self.database.fail_confirmation = True
        with self.assertRaises(RuntimeError):
            self.set_status(MAX_EMAIL, False)
        self.assertEqual(self.database.scopes, self.original)
        self.cached.clear.assert_not_called()
        self.assertIn(MAX_EMAIL, self.authorized_users())

    def test_unavailable_database_does_not_fall_back_to_old_director_access(self):
        self.functions["load_persistent_scopes"] = Mock(side_effect=RuntimeError())
        users, error = self.functions["build_authorized_users"](
            "test-database", refresh=True
        )
        self.assertTrue(error)
        self.assertEqual(set(users), {ADMIN_EMAIL})

    def test_push_delivery_filters_removed_accounts_before_fetching_devices(self):
        self.set_status(MAX_EMAIL, False)
        self.set_status(MANAGER_EMAIL, False)
        self.functions["get_or_create_web_push_keys"] = Mock(return_value={})
        self.functions["send_collective_chat_push_notifications"](
            "test-database", ADMIN_EMAIL, "Admin", "Message test", 123
        )
        recipient_emails, = self.database.parameters[-1]
        self.assertIn(BIKER_EMAIL, recipient_emails)
        self.assertNotIn(ADMIN_EMAIL, recipient_emails)
        self.assertNotIn(MAX_EMAIL, recipient_emails)
        self.assertNotIn(MANAGER_EMAIL, recipient_emails)


if __name__ == "__main__":
    unittest.main()
