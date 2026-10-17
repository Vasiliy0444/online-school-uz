"""Offline checks for credential protection and the fixed creative operation."""

from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from credentials import load_token, store_token, validate_token
from prepare_creative import build_command, main


class PreparationTests(unittest.TestCase):
    def test_private_token_round_trip(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "private" / "access-token"
            store_token("TEST_SYNTHETIC_TOKEN", path)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(load_token(path), "TEST_SYNTHETIC_TOKEN")
            path.chmod(0o644)
            with self.assertRaises(ValueError):
                load_token(path)

    def test_rejects_token_symlink_and_public_directory(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            source = base / "source"
            store_token("TEST_SYNTHETIC_TOKEN", source)
            link = base / "link"
            link.symlink_to(source)
            with self.assertRaises(OSError):
                load_token(link)
            base.chmod(0o755)
            with self.assertRaises(ValueError):
                load_token(source)
            base.chmod(0o700)

    def test_header_injection_rejected(self):
        with self.assertRaises(ValueError):
            validate_token("TEST\r\nInjected: secret")

    def test_creative_cannot_activate_ads_or_inject_flags(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            (base / "asset.png").write_bytes(b"synthetic offline fixture")
            spec = {"ad_account_id": "act_123", "page_id": "456", "name": "--status=ACTIVE",
                    "body": "$(do-not-execute)", "title": "Test", "image": "asset.png",
                    "link_url": "https://example.com/"}
            command = build_command(spec, base)
            self.assertIn("--status=PAUSED", command)
            self.assertNotIn("--status=ACTIVE", command)
            self.assertIn("--name=--status=ACTIVE", command)
            self.assertIn("--body=$(do-not-execute)", command)
            self.assertNotIn("TEST_SYNTHETIC_TOKEN", command)
            spec["status"] = "ACTIVE"
            with self.assertRaises(ValueError):
                build_command(spec, base)

    def test_rejects_ambiguous_or_credentialed_inputs(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            (base / "asset.png").touch()
            spec = {"ad_account_id": "act_123", "page_id": "456", "name": "Test",
                    "body": "Test", "title": "Test", "image": "asset.png",
                    "link_url": "https://user:secret@example.com/"}
            with self.assertRaises(ValueError):
                build_command(spec, base)
            spec["link_url"] = "https://example.com/"
            spec["video"] = "asset.mp4"
            with self.assertRaises(ValueError):
                build_command(spec, base)

    def test_rejects_malformed_url_cta_and_control_characters(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            (base / "asset.png").touch()
            spec = {"ad_account_id": "act_123", "page_id": "456", "name": "Test",
                    "body": "Test", "title": "Test", "image": "asset.png",
                    "link_url": "https://example.com/"}
            for url in ("https://example.com:invalid/", "https://example.com:99999/",
                        "https://example.com/with space", "https://exa\nmple.com/"):
                with self.subTest(url=url), self.assertRaises(ValueError):
                    build_command({**spec, "link_url": url}, base)
            for updates in ({"call_to_action": "NOT_A_META_CTA"}, {"body": "nul\x00text"}):
                with self.subTest(updates=updates), self.assertRaises(ValueError):
                    build_command({**spec, **updates}, base)

    def exercise_main(self, result=None, error=None):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            (base / "asset.png").touch()
            spec_file = base / "creative.json"
            spec_file.write_text(json.dumps({
                "ad_account_id": "act_123", "page_id": "456", "name": "Test",
                "body": "Test", "title": "Test", "image": "asset.png",
                "link_url": "https://example.com/",
            }), encoding="utf-8")
            stdout, stderr = io.StringIO(), io.StringIO()
            with patch("sys.argv", ["prepare_creative.py", "--spec", str(spec_file)]), \
                    patch("prepare_creative.load_token", return_value="TEST_SYNTHETIC_TOKEN"), \
                    patch("prepare_creative.subprocess.run", return_value=result, side_effect=error) as run, \
                    redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main()
            self.assertEqual(run.call_count, 1)
            self.assertNotIn("TEST_SYNTHETIC_TOKEN", " ".join(run.call_args.args[0]))
            self.assertIn("--status=PAUSED", run.call_args.args[0])
            self.assertEqual(run.call_args.kwargs["env"]["ACCESS_TOKEN"], "TEST_SYNTHETIC_TOKEN")
            self.assertEqual(run.call_args.kwargs["env"]["AD_ACCOUNT_ID"], "act_123")
            self.assertNotEqual(run.call_args.kwargs["cwd"], base)
            return exit_code, stdout.getvalue(), stderr.getvalue()

    def test_main_redacts_output_and_preserves_success(self):
        result = subprocess.CompletedProcess([], 0, "created TEST_SYNTHETIC_TOKEN\n",
                                             "warning TEST_SYNTHETIC_TOKEN\n")
        exit_code, stdout, stderr = self.exercise_main(result=result)
        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout, "created [REDACTED]\n")
        self.assertEqual(stderr, "warning [REDACTED]\n")

    def test_main_preserves_failure_and_does_not_retry(self):
        result = subprocess.CompletedProcess([], 7, "partial TEST_SYNTHETIC_TOKEN\n",
                                             "failed TEST_SYNTHETIC_TOKEN\n")
        exit_code, stdout, stderr = self.exercise_main(result=result)
        self.assertEqual(exit_code, 7)
        self.assertNotIn("TEST_SYNTHETIC_TOKEN", stdout + stderr)
        self.assertIn("Reconcile in Meta before retrying", stderr)

    def test_main_timeout_requires_reconciliation_without_echoing_buffers(self):
        error = subprocess.TimeoutExpired([], 600, output="TEST_SYNTHETIC_TOKEN",
                                          stderr="TEST_SYNTHETIC_TOKEN")
        exit_code, stdout, stderr = self.exercise_main(error=error)
        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout, "")
        self.assertNotIn("TEST_SYNTHETIC_TOKEN", stderr)
        self.assertIn("the write may have completed", stderr)


if __name__ == "__main__":
    unittest.main()
