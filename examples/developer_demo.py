"""Examples for asimtool developer tools."""

import asimtool

# ── Bug Description Improver ───────────────────────────────────
print("=== Bug Description ===")
bug = asimtool.improve_bug_description(
    "login page crashes when I click the submit button after entering wrong password 3 times"
)
print(bug)
print()

# ── Test Case Generator ───────────────────────────────────────
print("=== Test Cases ===")
table = asimtool.generate_test_cases(
    requirements="Users must be able to register with email and password. "
                 "Password must be at least 8 characters with one uppercase letter.",
    risk="Weak passwords could be accepted",
)
print(table)
print()

# ── PR Review ──────────────────────────────────────────────────
print("=== PR Review ===")
review = asimtool.review_pull_request(
    """diff --git a/auth.py b/auth.py
- def login(user, password):
-     return db.check(user, password)
+ def login(user, password):
+     if not user or not password:
+         return None
+     return db.check(user, password)"""
)
print(review)
print()

# ── Standup Summary ────────────────────────────────────────────
print("=== Standup ===")
standup = asimtool.generate_standup(
    "Fixed the payment flow bug. Started working on the new dashboard UI. "
    "Waiting for API spec from backend team."
)
print(standup)
