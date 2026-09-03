import re
from typing import List, Optional
from rapidfuzz import process, fuzz
import nltk
from nltk.corpus import wordnet


try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('wordnet', quiet=True)


class PureDynamicCategoryResolver:
    def __init__(self):
        self._categories: List[str] = []
        self._category_tokens: dict[str, set[str]] = {}

    def sync_catalog_categories(self, categories: List[str]) -> None:
        self._categories = [c for c in categories if c]
        self._category_tokens = {}

        for cat in self._categories:
            
            words = set(re.findall(r'\w+', cat.lower()))
            
            
            expanded_tokens = set(words)
            for word in words:
                for syn in wordnet.synsets(word):
                    for lemma in syn.lemmas():
                        expanded_tokens.add(lemma.name().lower().replace('_', ' '))

            self._category_tokens[cat] = expanded_tokens
    _STOPWORDS = {
    "a","an","and","are","the","is","which","what","who",
    "for","of","to","in","on","with","me","please","show",
    "available","brands","brand"
}
    def resolve(self, text: str) -> Optional[str]:
        if not self._categories:
            return None

        query_words = {
        w for w in re.findall(r'\w+', text.lower())
        if w not in self._STOPWORDS and len(w) > 2
    }
        
        
        expanded_query = set(query_words)
        for word in query_words:
            for syn in wordnet.synsets(word):
                for lemma in syn.lemmas():
                    expanded_query.add(lemma.name().lower().replace('_', ' '))

        
        best_cat = None
        highest_overlap = 0

        for cat, cat_tokens in self._category_tokens.items():
            
            overlap = len(expanded_query.intersection(cat_tokens))
            if overlap > highest_overlap:
                highest_overlap = overlap
                best_cat = cat

        if best_cat and highest_overlap >= 2:
            return best_cat

        
        match = process.extractOne(
            text,
            self._categories,
            scorer=fuzz.token_set_ratio,
            score_cutoff=60,
        )

        return match[0] if match else None


def is_brand_request(text: str) -> bool:
    text_lower = text.lower()
    brand_keywords = [
        "brand", "brands", "manufacturer", "manufacturers", 
        "maker", "makers", "who makes", "companies"
    ]
    return any(k in text_lower for k in brand_keywords)