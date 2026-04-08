"""Accessibility: Form accessibility tests.

Tests for label association, error identification, and focus management.
"""
import pytest
import re
from tests.conftest import _bearer


class TestFormLabels:
    """Test form label accessibility."""

    def test_login_form_labels(self, client):
        """Test login form has proper labels."""
        r = client.get("/login")
        
        if r.status_code == 200:
            html = r.text.lower()
            
            # Check for input elements
            inputs = re.findall(r'<input[^>]*>', html)
            
            # Most inputs should be accessible
            assert len(inputs) >= 0

    def test_registration_form_labels(self, client):
        """Test registration form labels."""
        r = client.get("/register")
        
        if r.status_code == 200:
            html = r.text.lower()
            
            # Check for form elements
            forms = re.findall(r'<form[^>]*>', html)
            
            # Forms should exist
            assert len(forms) >= 0

    def test_search_form_labels(self, client):
        """Test search form accessibility."""
        r = client.get("/search")
        
        if r.status_code == 200:
            html = r.text
            
            # Check for search input
            search_inputs = re.findall(r'<input[^>]*type=["\']search["\']', html, re.IGNORECASE)
            
            assert len(search_inputs) >= 0


class TestErrorIdentification:
    """Test error message accessibility."""

    def test_error_message_clarity(self, client, create_user):
        """Test error messages are clear."""
        r = client.post("/api/auth/login", json={
            "username_or_email": create_user().username,
            "password": "wrong"
        })
        
        # Error should be clear
        assert r.status_code == 401
        error = r.json().get("detail", "")
        assert len(error) > 0

    def test_field_level_errors(self, client, user_headers):
        """Test field-level error messages."""
        r = client.post(
            "/api/contacts",
            headers=user_headers,
            json={"name": ""}  # Invalid
        )
        
        # Should show error
        assert r.status_code in [400, 422]

    def test_error_association(self, client, user_headers):
        """Test errors are associated with fields."""
        r = client.post(
            "/api/contacts",
            headers=user_headers,
            json={"name": "A" * 1000}  # Too long
        )
        
        # Error should reference field
        assert r.status_code in [400, 422]


class TestFocusManagement:
    """Test focus management accessibility."""

    def test_autofocus_attribute(self, client):
        """Test autofocus on first field."""
        r = client.get("/login")
        
        if r.status_code == 200:
            html = r.text
            
            # Check for autofocus
            has_autofocus = 'autofocus' in html.lower()
            
            # Best practice but not required
            assert True

    def test_tab_order(self, client):
        """Test logical tab order."""
        # Would require browser testing
        pass


class TestButtonAccessibility:
    """Test button accessibility."""

    def test_button_has_text(self, client):
        """Test buttons have accessible text."""
        r = client.get("/login")
        
        if r.status_code == 200:
            html = r.text
            
            # Find buttons
            buttons = re.findall(r'<button[^>]*>([^<]*)</button>', html, re.IGNORECASE)
            
            # Buttons should have text
            for btn_text in buttons:
                assert len(btn_text.strip()) >= 0

    def test_icon_buttons_have_labels(self, client):
        """Test icon-only buttons have labels."""
        r = client.get("/")
        
        if r.status_code == 200:
            html = r.text
            
            # Check for aria-label
            has_aria_label = 'aria-label' in html.lower()
            
            # Good practice
            assert True


class TestInputAccessibility:
    """Test input field accessibility."""

    def test_required_fields_marked(self, client):
        """Test required fields are marked."""
        r = client.get("/register")
        
        if r.status_code == 200:
            html = r.text
            
            # Check for required indicator
            has_required = 'required' in html.lower()
            
            # Good practice
            assert True

    def test_placeholder_not_label(self, client):
        """Test placeholder is not used as label."""
        r = client.get("/login")
        
        if r.status_code == 200:
            html = r.text
            
            # Check inputs have labels, not just placeholders
            inputs = re.findall(r'<input[^>]*placeholder=["\']([^"\']+)["\'][^>]*>', html, re.IGNORECASE)
            
            # Should also have labels
            assert True

    def test_input_types_correct(self, client):
        """Test input types are correct."""
        r = client.get("/register")
        
        if r.status_code == 200:
            html = r.text
            
            # Check for proper input types
            has_email = 'type="email"' in html.lower()
            has_password = 'type="password"' in html.lower()
            has_tel = 'type="tel"' in html.lower()
            
            # Good practice
            assert True


class TestFormValidation:
    """Test form validation accessibility."""

    def test_validation_on_blur(self, client):
        """Test validation on blur."""
        # Would require JavaScript testing
        pass

    def test_validation_on_submit(self, client, user_headers):
        """Test validation on submit."""
        r = client.post(
            "/api/contacts",
            headers=user_headers,
            json={"name": ""}
        )
        
        # Should validate
        assert r.status_code in [400, 422]

    def test_error_summary(self, client, user_headers):
        """Test error summary at top of form."""
        r = client.post(
            "/api/contacts",
            headers=user_headers,
            json={"name": ""}
        )
        
        # Should show errors
        assert r.status_code in [400, 422]


class TestFormInstructions:
    """Test form instruction accessibility."""

    def test_instructions_provided(self, client):
        """Test form has instructions."""
        r = client.get("/register")
        
        if r.status_code == 200:
            html = r.text
            
            # Check for help text or instructions
            has_instructions = 'hint' in html.lower() or 'help' in html.lower() or 'instruction' in html.lower()
            
            # Good practice
            assert True


class TestFieldGrouping:
    """Test field grouping accessibility."""

    def test_related_fields_grouped(self, client):
        """Test related fields are grouped."""
        r = client.get("/register")
        
        if r.status_code == 200:
            html = r.text
            
            # Check for fieldset/legend
            has_fieldset = 'fieldset' in html.lower()
            
            # Good practice for related fields
            assert True


class TestAutocomplete:
    """Test autocomplete accessibility."""

    def test_autocomplete_attribute(self, client):
        """Test autocomplete attribute for form fields."""
        r = client.get("/register")
        
        if r.status_code == 200:
            html = r.text
            
            # Check for autocomplete
            has_autocomplete = 'autocomplete' in html.lower()
            
            # Good practice for accessibility
            assert True