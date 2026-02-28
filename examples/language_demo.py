"""Basic examples for asimtool language features."""

import asimtool

# ── Grammar Check ──────────────────────────────────────────────
print("=== Grammar Check ===")
corrected = asimtool.check_grammar("me go store yesterday buy milk")
print(corrected)
print()

# ── Translation ────────────────────────────────────────────────
print("=== Translation ===")
translated = asimtool.translate("The weather is beautiful today", "German")
print(translated)
print()

# ── Word Translation ───────────────────────────────────────────
print("=== Word Translation ===")
result = asimtool.translate_word("Hund", "German", "English")
print(result)
print()

# ── Vocabulary Quiz ────────────────────────────────────────────
print("=== Vocabulary Quiz ===")
quiz = asimtool.generate_quiz("German", "A2", "English")
print(f"Word: {quiz['word']}")
print(f"Options: {quiz['options']}")
print(f"Correct: option #{quiz['correct']}")
print()

# ── News Headlines ─────────────────────────────────────────────
print("=== News ===")
news = asimtool.get_news("Germany", "English", "B1")
for item in news[:3]:
    print(f"  • {item}")
print()

# ── Vocabulary Builder ─────────────────────────────────────────
print("=== Vocabulary Builder ===")
words = asimtool.build_vocabulary("Hund, Katze, Vogel", "German", "English")
for w in words:
    print(f"  {w['word']}: {w['meaning']}")
    print(f"    Example: {w['example']}")
print()

# ── Listening Exercise ─────────────────────────────────────────
print("=== Listening Exercise ===")
exercise = asimtool.generate_listening("French", "B1", 2)
print(f"Passage: {exercise['passage'][:150]}...")
for q in exercise["questions"]:
    print(f"  Q: {q['question']}")
    for i, opt in enumerate(q["options"]):
        marker = "✓" if i == q["correct_index"] else " "
        print(f"    [{marker}] {opt}")
