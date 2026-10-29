from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import scripts.check_servers as check_servers
from scripts.validate_catalog import validate_ignore_list


class ValidateIgnoreListTests(unittest.TestCase):
    def test_accepts_valid_entries_and_comments(self) -> None:
        self.assertEqual(
            validate_ignore_list(
                "- [acme/listed](https://github.com/acme/listed)\n",
                "# ignored\nacme/rejected\n",
            ),
            [],
        )

    def test_reports_invalid_duplicate_and_listed_entries(self) -> None:
        errors = validate_ignore_list(
            "- [acme/listed](https://github.com/acme/listed)\n",
            "not-a-repository\nacme/rejected\nACME/REJECTED\nacme/listed\n",
        )
        self.assertEqual(len(errors), 3)
        self.assertIn("expected owner/repo", errors[0])
        self.assertIn("duplicate entry", errors[1])
        self.assertIn("already listed", errors[2])


class CheckServersTests(unittest.TestCase):
    def test_extract_repos_deduplicates_and_skips_self(self) -> None:
        readme = (
            "https://github.com/Acme/Example.git, "
            "https://github.com/acme/example/tree/main "
            "https://github.com/ppiova/mcp-servers-microsoft-ecosystem"
        )
        self.assertEqual(check_servers.extract_repos(readme), [("acme", "example")])

    @patch.object(check_servers, "gh_request")
    def test_validate_classifies_removed_archived_renamed_and_stale(self, request: MagicMock) -> None:
        request.side_effect = [
            (404, None),
            (200, {"full_name": "acme/archived", "archived": True}),
            (200, {"full_name": "new-owner/repo", "archived": False}),
            (
                200,
                {
                    "full_name": "acme/stale",
                    "archived": False,
                    "pushed_at": "2020-01-01T00:00:00Z",
                },
            ),
        ]

        results = [
            check_servers.validate("acme", "removed"),
            check_servers.validate("acme", "archived"),
            check_servers.validate("acme", "repo"),
            check_servers.validate("acme", "stale"),
        ]

        self.assertEqual(
            [result["status"] for result in results],
            ["removed", "archived", "renamed", "stale"],
        )

    @patch.object(check_servers, "gh_request")
    def test_discover_filters_known_ignored_and_archived_repositories(self, request: MagicMock) -> None:
        items = [
            {
                "full_name": "acme/known",
                "html_url": "https://github.com/acme/known",
                "stargazers_count": 100,
                "archived": False,
            },
            {
                "full_name": "acme/ignored",
                "html_url": "https://github.com/acme/ignored",
                "stargazers_count": 90,
                "archived": False,
            },
            {
                "full_name": "acme/archived",
                "html_url": "https://github.com/acme/archived",
                "stargazers_count": 80,
                "archived": True,
            },
            {
                "full_name": "acme/candidate",
                "html_url": "https://github.com/acme/candidate",
                "description": "Azure MCP server",
                "stargazers_count": 70,
                "archived": False,
            },
        ]

        def response(path: str, params: dict | None = None) -> tuple[int, list | dict]:
            if path == "/search/repositories":
                return 200, {"items": items}
            return 200, [{"name": "Dockerfile"}]

        request.side_effect = response

        candidates = check_servers.discover({"acme/known"}, {"acme/ignored"})

        self.assertEqual([item["full_name"] for item in candidates], ["acme/candidate"])
        self.assertTrue(candidates[0]["has_docker"])
        self.assertEqual(candidates[0]["section"], "Azure / Infrastructure & Management")


if __name__ == "__main__":
    unittest.main()
