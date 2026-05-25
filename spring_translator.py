from deep_translator import GoogleTranslator

SUPPORTED_LANGUAGE_EXAMPLES = {
    "english": "en",
    "spanish": "es",
    "french": "fr",
    "japanese": "ja",
    "korean": "ko",
    "chinese": "zh-CN",
    "german": "de",
    "russian": "ru",
    "arabic": "ar",
    "portuguese": "pt",
}


def normalize_language(language: str) -> str:
    language = language.strip().lower()
    return SUPPORTED_LANGUAGE_EXAMPLES.get(language, language)


async def translate_text(text: str, target_language: str, source_language: str = "auto"):
    target_language = normalize_language(target_language)
    source_language = normalize_language(source_language)

    translated = GoogleTranslator(
        source=source_language,
        target=target_language
    ).translate(text)

    return translated
