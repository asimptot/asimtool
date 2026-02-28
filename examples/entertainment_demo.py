"""Examples for asimtool entertainment features."""

import asimtool

# ── Movie Recommendations ──────────────────────────────────────
print("=== Movie Recommendations ===")
movies = asimtool.recommend_movie("movie", "sci-fi")
for m in movies[:5]:
    print(f"  {m['title']} ({m['year']}) — IMDB: {m['rating']}")
print()

# ── Trip Planner ───────────────────────────────────────────────
print("=== Trip Plan ===")
plan = asimtool.plan_trip("Rome", "2025-08-01", "2025-08-03")
for row in plan.split("\n")[:5]:
    print(f"  {row}")
print()

# ── Song Lyrics ────────────────────────────────────────────────
print("=== Song Lyrics ===")
lyrics = asimtool.generate_lyrics(
    title="Midnight City",
    genre="synthwave",
    mood="nostalgic and dreamy",
    language="English",
)
print(lyrics[:400])
print()

# ── Solar Optimizer (no AI needed — uses free weather APIs) ────
print("=== Solar Optimizer ===")
solar = asimtool.optimize_solar("1011", country="NL")
print(f"Location: {solar['location']}")
print(f"Weather: {solar['weather']['description']} ({solar['weather']['temp']}°C)")
print(f"Daylight: {solar['sun_times']['daylight_hours']} hours")
print("Top hours:")
for h in solar["optimal_hours"][:3]:
    print(f"  {h['time']} — {h['efficiency']}% efficiency (angle: {h['sun_angle']}°)")
