# asimtool

AI-powered developer & language toolkit — a standalone Python package extracted from [AsimAI](https://github.com/asimptot/AsimAI).

Wraps [g4f](https://github.com/xtekky/gpt4free) providers for grammar checking, translation, quizzes, bug-report formatting, PR reviews, trip planning, solar energy optimisation, and much more.

## Installation

```bash
pip install asimtool
```

With optional extras:

```bash
pip install asimtool[all]       # includes pypdf + langdetect
pip install asimtool[pdf]       # PDF text extraction only
pip install asimtool[language]  # auto-language detection for replies
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
| `check_grammar(text, tone)` | Grammar correction (formal/informal) |
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
| `ask_about_code(question, files)` | Q&A about a codebase |
| `generate_standup(notes, commit)` | Notes → spoken standup summary |

### 🎬 Entertainment

| Function | Description |
|---|---|
| `recommend_movie(media_type, genre)` | Movie/series recommendations by IMDB |
| `plan_trip(location, start, end)` | Detailed travel itinerary |
| `find_venue(zip1, zip2, country1, country2)` | Meeting venue at midpoint |
| `generate_lyrics(title, genre, mood, lang)` | Song lyrics generation |
| `optimize_solar(postal_code, country, date)` | Solar energy optimal hours (free APIs) |

### 🔧 Utility Tools

| Function | Description |
|---|---|
| `extract_text(file_path)` | PDF, DOCX, or image OCR |
| `transcribe(audio_path, api_key, lang)` | Audio → text (Groq Whisper) |
| `Chat()` | Stateful conversational AI |
| `suggest_reply(messages, tone)` | Professional reply suggestion |
| `image_to_prompt(image_path)` | Image → AI generation prompt |

## Advanced Usage

### Custom Providers

```python
from asimtool.core.provider import Provider, call_ai

# Use specific g4f providers
provider = Provider(["OperaAria", "AnyProvider"])

corrected = asimtool.check_grammar("bad text", provider=provider)
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

## Environment Variables

Some features need environment variables:

| Variable | Used By | Required? |
|---|---|---|
| `GROQ_API_KEY` | `transcribe()` | Yes, for transcription |
| `I2P_API_URL` | `image_to_prompt()` | Yes, for image analysis |
| `I2P_API_ORIGIN` | `image_to_prompt()` | Yes, for image analysis |
| `I2P_API_REFERER` | `image_to_prompt()` | Yes, for image analysis |

## Dependencies

- **g4f** — AI provider abstraction
- **requests** — HTTP client (solar, transcription, image-to-prompt)
- **feedparser** — Google News RSS parsing
- **pypdf** *(optional)* — PDF text extraction
- **langdetect** *(optional)* — Auto language detection for replies

## License

MIT — see [LICENSE](LICENSE) for details.
