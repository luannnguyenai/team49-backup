#!/usr/bin/env python3
"""
Discord Bot Testing Loop Script

Repeatedly:
1. Add a comment to tests/test_constants.py
2. Commit and push to save-ui
3. Create or update PR to main
4. Wait and loop

This script tests whether a Discord bot correctly detects PR creation and push events.
"""

import subprocess
import datetime
import time
import sys

# Configuration
TARGET_FILE = "tests/test_constants.py"
DELAY_SECONDS = 10
MAX_ITERATIONS = None  # None = infinite, set to int to limit

def run(cmd, check=True):
    """Execute shell command."""
    return subprocess.run(cmd, shell=True, check=check, capture_output=False)

def run_output(cmd):
    """Execute shell command and return output."""
    return subprocess.check_output(cmd, shell=True, text=True).strip()

def main():
    iteration = 0
    try:
        while True:
            if MAX_ITERATIONS and iteration >= MAX_ITERATIONS:
                print(f"\nReached max iterations ({MAX_ITERATIONS}). Exiting.")
                break

            iteration += 1
            ts = datetime.datetime.now().isoformat()

            print(f"\n{'='*70}")
            print(f"[Iteration {iteration}] {ts}")
            print(f"{'='*70}")

            # Step 1: Modify file
            print(f"[Step 1] Adding comment to {TARGET_FILE}...")
            with open(TARGET_FILE, "a") as f:
                f.write(f"\n# bot-test: iteration {iteration} at {ts}\n")
            print("✓ File modified")

            # Step 2: Commit
            print(f"[Step 2] Committing changes...")
            run(f'git add {TARGET_FILE}')
            run(f'git commit -m "test: bot trigger #{iteration} - {ts}"')
            print("✓ Committed")

            # Step 3: Push
            print(f"[Step 3] Pushing to origin/save-ui...")
            run('git push origin save-ui')
            print("✓ Pushed")

            # Step 4: PR check/create
            print(f"[Step 4] Checking for existing PR...")
            try:
                existing = run_output('gh pr list --head save-ui --base main --json number --jq "length"')
                pr_count = int(existing)
            except Exception as e:
                print(f"⚠ Warning: Could not check PR status: {e}")
                pr_count = 0

            if pr_count == 0:
                print("No existing PR found. Creating new PR...")
                run(f'gh pr create --base main --head save-ui '
                    f'--title "test: Discord bot test #{iteration}" '
                    f'--body "Automated test loop iteration {iteration}"')
                print("✓ PR created")
            else:
                print(f"✓ PR already open ({pr_count} found). Push will re-trigger bot.")

            # Step 5: Wait
            print(f"\n⏳ Waiting {DELAY_SECONDS}s before next iteration...")
            time.sleep(DELAY_SECONDS)

    except KeyboardInterrupt:
        print(f"\n\n{'='*70}")
        print(f"Test loop stopped by user after {iteration} iteration(s).")
        print(f"{'='*70}")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
