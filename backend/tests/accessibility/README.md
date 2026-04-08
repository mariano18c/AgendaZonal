# Accessibility Tests

## Purpose

WCAG 2.1 AA compliance and accessibility testing:

- **WCAG Compliance** (`test_wcag_compliance.py`) - Perceivable, operable, understandable, robust
- **Screen Reader** (`test_screen_reader.py`) - Screen reader compatibility
- **Keyboard Navigation** (`test_keyboard_navigation.py`) - Full keyboard operability
- **Color Contrast** (`test_color_contrast.py`) - Automated contrast validation
- **Form Accessibility** (`test_form_accessibility.py`) - Labels, errors, focus
- **ARIA Validation** (`test_aria_validation.py`) - Proper ARIA attribute usage
- **Responsive** (`test_responsive_accessibility.py`) - Mobile accessibility
- **Language/Locale** (`test_language_locale.py`) - i18n/l10n accessibility

## Running Tests

```bash
# Run all accessibility tests
pytest tests/accessibility/ -v

# Run WCAG tests
pytest tests/accessibility/test_wcag_compliance.py -v
```

## Markers

- `-m accessibility` - All accessibility tests

## Notes

- Most tests analyze HTML structure
- Full accessibility testing requires browser-based tools
- Use `accessibility_checker` fixture for custom checks