"""Language learning tools: grammar, translation, news, quiz, vocabulary, listening."""

from .grammar import check_grammar
from .translate import translate, translate_word
from .news import get_news
from .quiz import generate_quiz
from .vocabulary import build_vocabulary
from .listening import generate_listening

__all__ = [
    "check_grammar",
    "translate",
    "translate_word",
    "get_news",
    "vocabulary",
    "generate_quiz",
    "build_vocabulary",
    "generate_listening",
]
