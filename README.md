# asimtool

AI-powered developer & language toolkit — a standalone Python package extracted from [AsimAI](https://github.com/asimptot/AsimAI).

Wraps [g4f](https://github.com/xtekky/gpt4free) providers for grammar checking, translation, quizzes, bug-report formatting, PR reviews, trip planning, solar energy optimisation, and much more.

## Installation

```bash
pip install asimtool
```

With optional extras:

```bash
pip install asimtool[all]       # includes all optional extras
pip install asimtool[pdf]       # PDF text extraction only
pip install asimtool[ocr]       # PDF OCR for scanned documents
pip install asimtool[language]  # auto-language detection for replies
pip install asimtool[docx]      # robust DOCX extraction
pip install asimtool[tts]       # text-to-speech (Microsoft Neural voices)
```

## Quick Start

```python
import asimtool

# Grammar check
corrected = asimtool.check_grammar("me go store yesterday")
print(corrected)

# Translation
translated = asimtool.translate("Hello world", "German")
print(translated)

# Vocabulary quiz
quiz = asimtool.generate_quiz("German", "A2", "English")
print(f"Word: {quiz['word']}, Options: {quiz['options']}")
```

## Features

### 🔤 Language Learning

| Function | Description |
|---|---|
| `check_grammar(text, tone)` | Grammar correction (formal/informal/human) |
| `translate(text, target_language)` | Full text translation |
| `translate_word(word, source, target)` | Single word with explanation |
| `get_news(country, language, level)` | News headlines translated by CEFR level |
| `generate_quiz(language, level, options_lang)` | Vocabulary MCQ with 4 options |
| `build_vocabulary(words, word_lang, meaning_lang)` | Word meanings + example sentences |
| `generate_listening(language, level, num_q)` | Passage + comprehension questions |

### 🛠️ Developer Tools

| Function | Description |
|---|---|
| `improve_bug_description(text)` | Structure a bug report with template |
| `generate_test_cases(requirements, risk, code)` | Markdown table of test cases |
| `review_pull_request(pr_text)` | AI code review (understands diffs) |
| `validate_specsheet(text)` | Spec validation from tester POV |
| `validate_requirements(req, risk, commit)` | Requirements vs code analysis |
| `ask_about_code(question, files)` | Q&A about a codebase (paste files) |
| `ask_about_project(question, root)` | Agent mode — explores a folder read-only (`list_dir`, `read_file`, `grep`, `git_diff`) |
| `security_recon(target)` | Stage 1 of the Strix scanner: attack-surface map |
| `security_scan(target, mode)` | Stage 2: ranked findings with PoC + remediation |
| `security_scan_site(url)` | Live-site scan: headers, sensitive-path probes, AI findings |
| `generate_standup(notes, commit)` | Notes → spoken standup summary |

### 🎬 Entertainment

| Function | Description |
|---|---|
| `recommend_movie(media_type, genre)` | Movie/series recommendations by IMDB |
| `plan_trip(location, start, end)` | Detailed travel itinerary |
| `find_venue(zip1, zip2, country1, country2)` | Meeting venue at midpoint |
| `generate_lyrics(title, genre, mood, lang)` | Song lyrics generation |
| `optimize_solar(postal_code, country, date)` | Solar energy optimal hours (free APIs) |
| `compare_cost_of_living(country, salary)` | Year-over-year price comparison |

### 🔧 Utility Tools

| Function | Description |
|---|---|
| `extract_text(file_path)` | PDF, DOCX, or image OCR (Groq vision) |
| `transcribe(audio_path, api_key, lang)` | Audio → text (Groq Whisper; mp3/wav/m4a/aac/caf/…) |
| `Chat()` | Stateful conversational AI |
| `suggest_reply(messages, tone)` | Professional reply suggestion (formal/human) |
| `image_to_prompt(image_path)` | Image → AI generation prompt |
| `tailor_cv(cv_text, job_description)` | Tailor CV to job description |
| `generate_cover_letter(job_description, cv_text, tone)` | Cover letter in the job ad's language |
| `text_to_speech(text, lang, rate)` | Neural TTS (14 languages, edge-tts) |

## Advanced Usage

### Custom Providers

```python
from asimtool.core.provider import Provider, call_ai

# Use specific g4f providers
provider = Provider(["Yqcloud", "Aura"])

corrected = asimtool.check_grammar("bad text", provider=provider)
```

Provider names that your installed g4f does not know are skipped, and the
default pool is used as a last resort. Override the defaults entirely with an
environment variable:

```bash
export ASIMTOOL_PROVIDERS="Yqcloud,ChatgptFree"
```

### Direct AI Calls

```python
from asimtool import call_ai, call_ai_json

# Plain text response
answer = call_ai("What is Python?", model="gpt-4o")

# Parsed JSON response
data = call_ai_json('Return JSON: {"name": "test"}', model="grok_3")
```

### Chat with History

```python
from asimtool import Chat

chat = Chat(assistant_name="MyBot")
print(chat.send("Hello!"))
print(chat.send("Tell me a joke"))
print(chat.send("Now in Dutch", response_language="Dutch"))
chat.clear()
```

### Solar Optimizer (No AI, No API Key)

```python
from asimtool import optimize_solar

result = optimize_solar("1011", country="NL")
print(f"Location: {result['location']}")
print(f"Weather: {result['weather']['description']}")
for h in result['optimal_hours'][:3]:
    print(f"  {h['time']} — {h['efficiency']}% efficiency")
```

### CV Tailoring

```python
from asimtool import tailor_cv

# From text
result = tailor_cv(cv_text="...", job_description="...")

# From file
result = tailor_cv(cv_file="my_cv.pdf", job_description="...")
print(result)
```

### Text-to-Speech (14 Languages)

```python
from asimtool import text_to_speech

# Generate speech in Turkish
audio = text_to_speech("Merhaba dünya!", lang="tr")
with open("output.mp3", "wb") as f:
    f.write(audio)

# English with faster rate
audio = text_to_speech("Hello world!", lang="en", rate=0.2)
```

Supported languages: en, tr, nl, fr, de, it, es, sv, ar, ja, zh, pt, ru, ko

### Agent Mode: Ask About a Project on Disk

```python
from asimtool import ask_about_project

# The model explores the folder with read-only tools, then answers.
answer = ask_about_project("Where is the DB connection configured?", ".")
print(answer)

# Optional: watch every tool call
def log(tool, args, result):
    print(f"[{tool}] {args} -> {len(result)} chars")

ask_about_project("What changed in the working tree?", ".", on_tool_call=log)
```

### AI Security Scanner (Strix-style)

```python
from asimtool import security_recon, security_scan, security_scan_site

code = open("app.py", encoding="utf-8").read()

# Stage 1 — attack surface
recon = security_recon(code)
print(recon["attack_surface"])

# Stage 2 — findings, sorted by severity
report = security_scan(code, mode="deep", recon=recon)
for f in report["findings"]:
    print(f"[{f['severity']}] {f['title']} @ {f['location']}")

# Live website (SSRF-guarded, public URLs only)
site_report = security_scan_site("example.com")
```

### Cover Letter

```python
from asimtool import generate_cover_letter

letter = generate_cover_letter(
    "We are hiring a Python developer…",   # written in the job ad's language
    cv_file="my_cv.pdf",
    tone="enthusiastic",
)
```

### Cost of Living Comparison

```python
from asimtool import compare_cost_of_living

# Basic comparison
result = compare_cost_of_living("Netherlands")
print(result)

# With salary purchasing power analysis
result = compare_cost_of_living("Turkey", salary_current="45000", salary_previous="35000")
```

## Environment Variables

Some features need environment variables:

| Variable | Used By | Required? |
|---|---|---|
| `GROQ_API_KEY` | `transcribe()`, `extract_text()`, `call_ai()` fallback | Yes, for transcription, OCR, and LLM fallback |
| `GROQ_MODEL` | `call_ai()` fallback | No — pins one chat model (default: `openai/gpt-oss-120b`, then `openai/gpt-oss-20b`, `qwen/qwen3.8-27b`) |
| `GROQ_OCR_MODEL` | `extract_text()` OCR | No — pins the vision model (default: `qwen/qwen3.8-27b`) |
| `GROQ_API_BASE` | all Groq calls | No — defaults to `https://api.groq.com/openai/v1` |
| `ASIMTOOL_PROVIDERS` | g4f provider selection | No — comma-separated provider names |
| `I2P_API_URL` | `image_to_prompt()` | Yes, for image analysis |
| `I2P_API_ORIGIN` | `image_to_prompt()` | Yes, for image analysis |
| `I2P_API_REFERER` | `image_to_prompt()` | Yes, for image analysis |

## Dependencies

- **g4f** — AI provider abstraction
- **requests** — HTTP client (solar, transcription, image-to-prompt)
- **feedparser** — Google News RSS parsing
- **pypdf** *(optional)* — PDF text extraction
- **pymupdf** *(optional)* — PDF OCR rendering for scanned documents
- **Pillow** *(optional)* — Image processing for OCR
- **python-docx** *(optional)* — Robust DOCX text extraction
- **langdetect** *(optional)* — Auto language detection for replies and grammar
- **edge-tts** *(optional)* — Microsoft Neural text-to-speech (14 languages)

## Testing

```bash
python -m unittest discover -s tests -v
```

The suite runs fully offline (AI calls are mocked) and covers the provider
resolution, JSON parsing, security-scan parsing/SSRF guard, agent tool layer
and the CV/cover-letter helpers.

## License

MIT — see [LICENSE](LICENSE) for details.
