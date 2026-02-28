"""Examples for asimtool utility tools."""

import asimtool

# ── Text Extraction ────────────────────────────────────────────
# Uncomment to use:
# text = asimtool.extract_text("document.pdf")
# print(text[:500])

# ── Chat ───────────────────────────────────────────────────────
print("=== Chat ===")
chat = asimtool.Chat(assistant_name="Merlin")
print(chat.send("Hello! What can you help me with?"))
print(chat.send("Can you explain what Python decorators are?"))
chat.clear()
print()

# ── Reply Suggestion ───────────────────────────────────────────
print("=== Reply Suggestion ===")
reply = asimtool.suggest_reply(
    messages=["Can we reschedule our meeting to Thursday?"],
    tone="formal",
)
print(reply)
print()

# ── Transcription (requires GROQ_API_KEY) ─────────────────────
# Uncomment to use:
# transcript = asimtool.transcribe("meeting.mp3", language="en")
# print(transcript)

# ── Image to Prompt (requires I2P_API_URL env vars) ───────────
# Uncomment to use:
# prompt = asimtool.image_to_prompt("photo.jpg")
# print(prompt)
