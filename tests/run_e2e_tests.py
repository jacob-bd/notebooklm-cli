#!/usr/bin/env python3
"""
NotebookLM CLI - End-to-End Test Runner

This script runs comprehensive tests against the NLM CLI to verify all
functionality works correctly before GA release.

Usage:
    python tests/run_e2e_tests.py
    python tests/run_e2e_tests.py --skip-interactive  # Skip Drive sync tests
    python tests/run_e2e_tests.py --keep-notebook     # Don't delete test notebook
"""

import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class TestStatus(Enum):
    PASSED = "✓"
    FAILED = "✗"
    SKIPPED = "○"
    WARNING = "⚠"


@dataclass
class TestResult:
    name: str
    status: TestStatus
    duration: float = 0.0
    output: str = ""
    error: str = ""


@dataclass
class TestContext:
    """Shared context across tests."""
    notebook_id: str = ""
    source_ids: list = field(default_factory=list)
    conversation_id: str = ""
    deep_task_id: str = ""
    fast_task_id: str = ""
    drive_doc_id: str = ""
    drive_doc_title: str = ""
    drive_doc_type: str = "doc"


class TestRunner:
    """E2E test runner for NLM CLI."""
    
    # Hardcoded test resources
    TEST_YOUTUBE_URL = "https://www.youtube.com/watch?v=d-PZDQlO4m4"
    TEST_URL = "https://en.wikipedia.org/wiki/Artificial_intelligence"
    
    def __init__(
        self,
        throttle_seconds: float = 2.0,
        skip_interactive: bool = False,
        keep_notebook: bool = False,
    ):
        self.throttle = throttle_seconds
        self.skip_interactive = skip_interactive
        self.keep_notebook = keep_notebook
        self.results: list[TestResult] = []
        self.ctx = TestContext()
        self.start_time = None
    
    def run_command(self, cmd: str, timeout: int = 120) -> tuple[int, str, str]:
        """Run a shell command and return (exit_code, stdout, stderr)."""
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", f"Command timed out after {timeout}s"
        except Exception as e:
            return -1, "", str(e)
    
    def run_nlm(self, args: str, timeout: int = 120) -> tuple[int, str, str]:
        """Run nlm command with args."""
        return self.run_command(f"nlm {args}", timeout)
    
    def throttle_wait(self):
        """Wait between API calls to avoid rate limits."""
        time.sleep(self.throttle)
    
    def print_header(self, text: str):
        """Print a section header."""
        print(f"\n{'='*60}")
        print(f"  {text}")
        print(f"{'='*60}\n")
    
    def print_result(self, result: TestResult):
        """Print a single test result."""
        status_color = {
            TestStatus.PASSED: "\033[92m",  # Green
            TestStatus.FAILED: "\033[91m",  # Red
            TestStatus.SKIPPED: "\033[93m", # Yellow
            TestStatus.WARNING: "\033[93m", # Yellow
        }
        reset = "\033[0m"
        
        color = status_color.get(result.status, "")
        print(f"  {color}{result.status.value}{reset} {result.name} ({result.duration:.2f}s)")
        
        if result.status == TestStatus.FAILED and result.error:
            for line in result.error.strip().split("\n")[:3]:
                print(f"      {line}")
    
    def run_test(self, name: str, cmd: str, check_fn=None, timeout: int = 120) -> TestResult:
        """Run a single test."""
        start = time.time()
        exit_code, stdout, stderr = self.run_nlm(cmd, timeout)
        duration = time.time() - start
        
        # Default check: exit code 0
        if check_fn:
            try:
                passed = check_fn(exit_code, stdout, stderr)
            except Exception as e:
                passed = False
                stderr = f"Check function error: {e}\n{stderr}"
        else:
            passed = exit_code == 0
        
        result = TestResult(
            name=name,
            status=TestStatus.PASSED if passed else TestStatus.FAILED,
            duration=duration,
            output=stdout,
            error=stderr if not passed else "",
        )
        
        self.results.append(result)
        self.print_result(result)
        self.throttle_wait()
        
        return result
    
    def skip_test(self, name: str, reason: str = "") -> TestResult:
        """Mark a test as skipped."""
        result = TestResult(
            name=name,
            status=TestStatus.SKIPPED,
            error=reason,
        )
        self.results.append(result)
        self.print_result(result)
        return result
    
    def extract_uuid(self, text: str) -> str | None:
        """Extract a UUID from text."""
        match = re.search(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', text)
        return match.group(0) if match else None
    
    def prompt_user(self, message: str) -> str:
        """Prompt user for input."""
        print(f"\n>>> {message}")
        return input(">>> ").strip()
    
    def pause_for_user(self, message: str):
        """Pause and wait for user to press Enter."""
        print(f"\n⏸️  {message}")
        input("   Press Enter to continue...")
    
    # =========================================================================
    # Pre-Test Setup
    # =========================================================================
    
    def setup(self) -> bool:
        """Interactive setup before running tests."""
        self.print_header("NLM CLI End-to-End Test Suite")
        
        print("This script will test all CLI commands against your NotebookLM account.")
        print("It will create a test notebook, add sources, and clean up afterward.\n")
        
        # Check auth
        print("Checking authentication...")
        exit_code, stdout, stderr = self.run_nlm("login --check")
        if exit_code != 0:
            print(f"\n❌ Authentication failed. Please run 'nlm login' first.")
            print(f"   Error: {stderr or stdout}")
            return False
        print(f"✓ {stdout.strip()}\n")
        
        # Prompt for Drive document
        print("-" * 50)
        print("DRIVE DOCUMENT SETUP")
        print("-" * 50)
        print("\nFor the staleness/sync test, you need a Google Drive document you can edit.")
        print("Example URL: https://docs.google.com/document/d/YOUR_DOC_ID/edit\n")
        
        drive_url = self.prompt_user("Enter your Drive document URL (or press Enter to skip Drive tests):")
        
        if drive_url:
            # Extract doc ID from URL
            match = re.search(r'/d/([a-zA-Z0-9_-]+)', drive_url)
            if match:
                self.ctx.drive_doc_id = match.group(1)
                self.ctx.drive_doc_title = self.prompt_user("Enter a title for this document:") or "Test Drive Doc"
                
                # Detect type
                if "slides" in drive_url:
                    self.ctx.drive_doc_type = "slides"
                elif "sheets" in drive_url:
                    self.ctx.drive_doc_type = "sheets"
                else:
                    self.ctx.drive_doc_type = "doc"
                
                print(f"\n✓ Drive doc configured: {self.ctx.drive_doc_id[:20]}...")
                print(f"\n⚠️  REMEMBER: Later you'll be asked to edit this document for the freshness test.")
                print("   Keep it open in another browser tab!")
            else:
                print("⚠️  Could not extract doc ID from URL. Drive tests will be skipped.")
        else:
            print("⚠️  No Drive document provided. Drive tests will be skipped.")
        
        print("\n" + "-" * 50)
        confirm = self.prompt_user("Ready to start tests? (y/n):").lower()
        return confirm in ("y", "yes", "")
    
    # =========================================================================
    # Test Groups
    # =========================================================================
    
    def test_group_1_auth(self):
        """Test Group 1: Authentication."""
        self.print_header("Test Group 1: Authentication")
        
        # Help
        self.run_test(
            "login --help",
            "login --help",
            lambda c, o, e: "--legacy" in o and "--check" in o,
        )
        
        # Check valid auth
        self.run_test(
            "login --check (valid)",
            "login --check",
            lambda c, o, e: "Authentication valid" in o or "Notebooks found" in o,
        )
    
    def test_group_2_create_notebook(self):
        """Test Group 2: Create test notebook."""
        self.print_header("Test Group 2: Setup - Create Test Notebook")
        
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        title = f"NLM CLI Test {timestamp}"
        
        result = self.run_test(
            "notebook create",
            f'notebook create "{title}"',
            lambda c, o, e: c == 0 and ("Created" in o or self.extract_uuid(o)),
        )
        
        # Extract notebook ID
        self.ctx.notebook_id = self.extract_uuid(result.output)
        if self.ctx.notebook_id:
            print(f"\n   📓 Test Notebook ID: {self.ctx.notebook_id}")
        else:
            print("\n   ❌ Failed to extract notebook ID!")
            return False
        
        # Verify
        self.run_test(
            "notebook get",
            f"notebook get {self.ctx.notebook_id}",
        )
        
        return True
    
    def test_group_3_start_deep_research(self):
        """Test Group 3: Start deep research (background task)."""
        self.print_header("Test Group 3: Start Deep Research (Background)")
        
        print("   Starting deep research - this runs in background while we do other tests...")
        
        result = self.run_test(
            "research start (deep)",
            f'research start "artificial intelligence applications" --mode deep --notebook-id {self.ctx.notebook_id}',
            timeout=30,
        )
        
        # Extract task ID if available
        task_match = re.search(r'Task ID: ([a-zA-Z0-9_-]+)', result.output)
        if task_match:
            self.ctx.deep_task_id = task_match.group(1)
            print(f"   🔬 Deep Research Task ID: {self.ctx.deep_task_id}")
    
    def test_group_4_sources(self):
        """Test Group 4: Source management."""
        self.print_header("Test Group 4: Source Management")
        
        # Add URL source
        self.run_test(
            "source add (URL)",
            f"source add {self.ctx.notebook_id} --url {self.TEST_URL}",
        )
        
        # Add YouTube source
        self.run_test(
            "source add (YouTube)",
            f"source add {self.ctx.notebook_id} --url {self.TEST_YOUTUBE_URL}",
        )
        
        # Add text source
        self.run_test(
            "source add (text)",
            f'source add {self.ctx.notebook_id} --text "Test content about machine learning and AI." --title "Test Text Doc"',
        )
        
        # Add Drive source if available
        if self.ctx.drive_doc_id:
            self.run_test(
                "source add (Drive)",
                f'source add {self.ctx.notebook_id} --drive {self.ctx.drive_doc_id} --title "{self.ctx.drive_doc_title}" --type {self.ctx.drive_doc_type}',
            )
        else:
            self.skip_test("source add (Drive)", "No Drive document provided")
        
        # List sources
        result = self.run_test(
            "source list",
            f"source list {self.ctx.notebook_id}",
        )
        
        # Extract source IDs
        for uuid in re.findall(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', result.output):
            if uuid not in self.ctx.source_ids:
                self.ctx.source_ids.append(uuid)
        
        if self.ctx.source_ids:
            print(f"\n   📎 Found {len(self.ctx.source_ids)} source(s)")
        
        # Test variations
        self.run_test("source list --json", f"source list {self.ctx.notebook_id} --json")
        self.run_test("source list --quiet", f"source list {self.ctx.notebook_id} --quiet")
        self.run_test("source list --drive", f"source list {self.ctx.notebook_id} --drive")
        self.run_test("source list --drive --skip-freshness", f"source list {self.ctx.notebook_id} --drive --skip-freshness")
        
        # Source operations on first source
        if self.ctx.source_ids:
            src_id = self.ctx.source_ids[0]
            self.run_test("source get", f"source get {src_id}")
            self.run_test("source describe", f"source describe {src_id}")
            self.run_test("source content", f"source content {src_id}")
            self.run_test("source content --output", f"source content {src_id} --output /tmp/nlm_test_content.txt")
    
    def test_group_5_notebook_operations(self):
        """Test Group 5: Notebook operations."""
        self.print_header("Test Group 5: Notebook Operations")
        
        # List variations
        self.run_test("notebook list", "notebook list")
        self.run_test("notebook list --json", "notebook list --json")
        self.run_test("notebook list --quiet", "notebook list --quiet")
        self.run_test("notebook list --title", "notebook list --title")
        self.run_test("notebook list --full", "notebook list --full")
        
        # Describe
        self.run_test(
            "notebook describe",
            f"notebook describe {self.ctx.notebook_id}",
        )
        
        # Rename
        self.run_test(
            "notebook rename",
            f'notebook rename {self.ctx.notebook_id} "NLM CLI Test - Renamed"',
        )
    
    def test_group_5b_config(self):
        """Test Group 5b: Configuration commands."""
        self.print_header("Test Group 5b: Configuration")
        
        self.run_test("config show", "config show")
        self.run_test("config show --json", "config show --json")
        self.run_test("config get default_profile", "config get default_profile")
    
    def test_group_6_query_chat(self):
        """Test Group 6: Query and chat configuration."""
        self.print_header("Test Group 6: Query & Chat")
        
        # Basic query
        result = self.run_test(
            "notebook query",
            f'notebook query {self.ctx.notebook_id} "What topics are covered in these sources?"',
            timeout=60,
        )
        
        # Extract conversation ID
        conv_match = re.search(r'Conversation ID: ([a-zA-Z0-9_-]+)', result.output)
        if conv_match:
            self.ctx.conversation_id = conv_match.group(1)
        
        # Follow-up query
        if self.ctx.conversation_id:
            self.run_test(
                "notebook query (follow-up)",
                f'notebook query {self.ctx.notebook_id} "Tell me more" --conversation-id {self.ctx.conversation_id}',
                timeout=60,
            )
        
        # Chat configuration
        self.run_test(
            "chat configure (learning_guide)",
            f"chat configure {self.ctx.notebook_id} --goal learning_guide",
        )
        
        self.run_test(
            "chat configure (custom prompt)",
            f'chat configure {self.ctx.notebook_id} --goal custom --prompt "Be concise"',
        )
        
        self.run_test(
            "chat configure (response length)",
            f"chat configure {self.ctx.notebook_id} --response-length shorter",
        )
    
    def test_group_7_content_generation(self):
        """Test Group 7: Content generation."""
        self.print_header("Test Group 7: Content Generation")
        
        print("   Generating content... (this may take a moment)\n")
        
        # Audio
        self.run_test(
            "audio create",
            f"audio create {self.ctx.notebook_id} --format brief --length short --confirm",
            timeout=60,
        )
        time.sleep(3)  # Extra throttle for generation
        
        # Report
        self.run_test(
            "report create",
            f'report create {self.ctx.notebook_id} --format "Briefing Doc" --confirm',
            timeout=60,
        )
        time.sleep(3)
        
        # Quiz
        self.run_test(
            "quiz create",
            f"quiz create {self.ctx.notebook_id} --count 2 --difficulty 2 --confirm",
            timeout=60,
        )
        
        # Flashcards
        self.run_test(
            "flashcards create",
            f"flashcards create {self.ctx.notebook_id} --difficulty medium --confirm",
            timeout=60,
        )
        
        # Mind map
        self.run_test(
            "mindmap create",
            f'mindmap create {self.ctx.notebook_id} --title "Test Mind Map" --confirm',
            timeout=60,
        )
        
        # Note: mindmap list is deprecated - use studio status which includes mindmaps
        
        # Studio status (includes all artifacts + mindmaps)
        self.run_test(
            "studio status",
            f"studio status {self.ctx.notebook_id}",
        )
        
        self.run_test(
            "studio status --full",
            f"studio status {self.ctx.notebook_id} --full",
        )
    
    def test_group_8_fast_research(self):
        """Test Group 8: Fast research (complete cycle)."""
        self.print_header("Test Group 8: Fast Research")
        
        result = self.run_test(
            "research start (fast)",
            f'research start "machine learning basics" --mode fast --notebook-id {self.ctx.notebook_id}',
            timeout=30,
        )
        
        # Extract task ID
        task_match = re.search(r'Task ID: ([a-zA-Z0-9_-]+)', result.output)
        if task_match:
            self.ctx.fast_task_id = task_match.group(1)
        
        # Wait for completion
        self.run_test(
            "research status (fast)",
            f"research status {self.ctx.notebook_id} --max-wait 90",
            timeout=120,
        )
        
        # Import first 2 sources
        if self.ctx.fast_task_id:
            self.run_test(
                "research import (fast)",
                f"research import {self.ctx.notebook_id} {self.ctx.fast_task_id} --indices 0,1",
            )
    
    def test_group_9_deep_research(self):
        """Test Group 9: Check deep research (should be done by now)."""
        self.print_header("Test Group 9: Deep Research Check")
        
        if not self.ctx.deep_task_id:
            self.skip_test("research status (deep)", "No deep research task started")
            return
        
        print("   Checking deep research status (may need to wait)...\n")
        
        self.run_test(
            "research status (deep)",
            f"research status {self.ctx.notebook_id} --max-wait 180",
            timeout=240,
        )
        
        self.run_test(
            "research import (deep)",
            f"research import {self.ctx.notebook_id} {self.ctx.deep_task_id}",
        )
    
    def test_group_10_drive_sync(self):
        """Test Group 10: Drive sync (interactive)."""
        self.print_header("Test Group 10: Drive Sync (Interactive)")
        
        if not self.ctx.drive_doc_id or self.skip_interactive:
            self.skip_test("source stale", "Drive tests skipped")
            self.skip_test("source sync", "Drive tests skipped")
            return
        
        # Initial freshness check
        self.run_test(
            "source stale (initial)",
            f"source stale {self.ctx.notebook_id}",
        )
        
        # Pause for user to edit document
        self.pause_for_user(
            "Please make a small edit to your Drive document now.\n"
            "   (Add a line of text, change a word, etc.)\n"
            "   Then press Enter to continue..."
        )
        
        time.sleep(5)  # Wait for Drive to sync
        
        # Check staleness
        self.run_test(
            "source stale (after edit)",
            f"source stale {self.ctx.notebook_id}",
        )
        
        # Sync
        self.run_test(
            "source sync",
            f"source sync {self.ctx.notebook_id} --confirm",
        )
        
        # Verify fresh
        self.run_test(
            "source stale (after sync)",
            f"source stale {self.ctx.notebook_id}",
        )
    
    def test_group_11_cleanup(self):
        """Test Group 11: Cleanup."""
        self.print_header("Test Group 11: Cleanup")
        
        if self.keep_notebook:
            print(f"   📓 Keeping test notebook: {self.ctx.notebook_id}")
            self.skip_test("notebook delete", "--keep-notebook flag set")
            return
        
        if not self.ctx.notebook_id:
            self.skip_test("notebook delete", "No notebook to delete")
            return
        
        self.run_test(
            "notebook delete",
            f"notebook delete {self.ctx.notebook_id} --confirm",
        )
    
    # =========================================================================
    # Main Runner
    # =========================================================================
    
    def run_all(self) -> int:
        """Run all test groups."""
        self.start_time = time.time()
        
        if not self.setup():
            print("\n❌ Setup cancelled or failed.")
            return 1
        
        try:
            self.test_group_1_auth()
            
            if not self.test_group_2_create_notebook():
                print("\n❌ Failed to create test notebook. Aborting.")
                return 1
            
            self.test_group_3_start_deep_research()
            self.test_group_4_sources()
            self.test_group_5_notebook_operations()
            self.test_group_5b_config()
            self.test_group_6_query_chat()
            self.test_group_7_content_generation()
            self.test_group_8_fast_research()
            self.test_group_9_deep_research()
            self.test_group_10_drive_sync()
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Tests interrupted!")
        finally:
            self.test_group_11_cleanup()
        
        self.print_summary()
        
        # Return exit code based on failures
        failed = sum(1 for r in self.results if r.status == TestStatus.FAILED)
        return 1 if failed > 0 else 0
    
    def print_summary(self):
        """Print test summary."""
        total_time = time.time() - self.start_time
        
        passed = sum(1 for r in self.results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in self.results if r.status == TestStatus.FAILED)
        skipped = sum(1 for r in self.results if r.status == TestStatus.SKIPPED)
        total = len(self.results)
        
        self.print_header("Test Summary")
        
        print(f"   Total:   {total}")
        print(f"   Passed:  \033[92m{passed}\033[0m")
        print(f"   Failed:  \033[91m{failed}\033[0m")
        print(f"   Skipped: \033[93m{skipped}\033[0m")
        print(f"   Time:    {total_time:.1f}s")
        
        if failed > 0:
            print("\n   Failed tests:")
            for r in self.results:
                if r.status == TestStatus.FAILED:
                    print(f"     - {r.name}")
        
        print()
        if failed == 0:
            print("   🎉 All tests passed! Ready for GA.")
        else:
            print(f"   ⚠️  {failed} test(s) failed. Please review and fix.")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="NLM CLI End-to-End Tests")
    parser.add_argument(
        "--skip-interactive",
        action="store_true",
        help="Skip tests that require user interaction (Drive sync)",
    )
    parser.add_argument(
        "--keep-notebook",
        action="store_true",
        help="Don't delete the test notebook after tests",
    )
    parser.add_argument(
        "--throttle",
        type=float,
        default=2.0,
        help="Seconds to wait between API calls (default: 2.0)",
    )
    
    args = parser.parse_args()
    
    runner = TestRunner(
        throttle_seconds=args.throttle,
        skip_interactive=args.skip_interactive,
        keep_notebook=args.keep_notebook,
    )
    
    exit_code = runner.run_all()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
