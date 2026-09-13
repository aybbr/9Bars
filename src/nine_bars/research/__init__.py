"""Coffee research: turn roaster pages into sourced, cited facts."""

from nine_bars.research.extractor import FactExtractor, NoopFactExtractor, PromptFactExtractor
from nine_bars.research.llm import ChatModel, DeepSeekChatModel
from nine_bars.research.researcher import WebResearcher

__all__ = [
    "ChatModel",
    "DeepSeekChatModel",
    "FactExtractor",
    "NoopFactExtractor",
    "PromptFactExtractor",
    "WebResearcher",
]
