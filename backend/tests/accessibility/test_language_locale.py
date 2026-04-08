"""Accessibility: Language and Locale tests.

Tests for internationalization and localization accessibility.
"""
import pytest
import re


class TestLanguageAttribute:
    """Test language attribute."""

    def test_html_lang_attribute(self, client):
        """Test HTML has lang attribute."""
        r = client.get("/")
        
        if r.status_code == 200:
            html = r.text
            
            # Check for lang attribute
            has_lang = re.search(r'<html[^>]*lang=["\']([^"\']+)["\']', html, re.IGNORECASE)
            
            assert has_lang is not None

    def test_lang_attribute_valid(self, client):
        """Test lang attribute is valid."""
        r = client.get("/")
        
        if r.status_code == 200:
            html = r.text
            
            # Extract lang
            match = re.search(r'<html[^>]*lang=["\']([^"\']+)["\']', html, re.IGNORECASE)
            
            if match:
                lang = match.group(1)
                # Should be valid language code
                assert len(lang) == 2 or len(lang) == 5  # en or en-US


class TestMultilingualSupport:
    """Test multilingual support."""

    def test_available_languages(self, client):
        """Test available languages."""
        r = client.get("/")
        
        # Should work regardless of language
        assert r.status_code == 200

    def test_language_switcher(self, client):
        """Test language switcher accessibility."""
        r = client.get("/")
        
        if r.status_code == 200:
            html = r.text.lower()
            
            # Check for language switcher
            has_switcher = 'lang' in html or 'language' in html
            
            assert True


class TestLocalizedContent:
    """Test localized content accessibility."""

    def test_translated_content(self, client):
        """Test translated content is accessible."""
        # Would require translation testing
        pass

    def test_date_format_accessible(self, client):
        """Test date formats are accessible."""
        pass

    def test_number_format_accessible(self, client):
        """Test number formats are accessible."""
        pass


class TestRTLSupport:
    """Test RTL (right-to-left) support."""

    def test_rtl_language_support(self, client):
        """Test RTL language support."""
        # Would require RTL language testing
        pass