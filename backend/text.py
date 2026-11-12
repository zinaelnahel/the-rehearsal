"""Shared accent-insensitive text normalization for matching and retrieval."""
import unicodedata


def normalize(text):
    return ''.join(character for character in unicodedata.normalize('NFD', text.lower())
                   if unicodedata.category(character) != 'Mn')
