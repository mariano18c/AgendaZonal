# Spec: Merge Additional Tests from tests_ant to tests

## Status: ✅ COMPLETED

**Completion Date**: 2026-04-07
**Final Coverage**: 90.98%
**Tests Passed**: 692 passed, 3 skipped, 1 xfailed

## Context

The project has two test suites:
- **`.backend/tests`**: 34 test files (current production suite)
- **`backend/tests_ant`**: 68 test files (extended suite with additional coverage)

Both share identical infrastructure (SQLite :memory: with StaticPool, pytest, TestClient, same conftest.py pattern). The `tests_ant` suite contains significant additional coverage that is NOT present in the main suite.

## Goal

Incorporate all high-value, non-duplicate tests from `tests_ant` into `.backend/tests` to create a single, comprehensive test suite.

## Completed Work

### Phase 1: Security Tests ✅
- Created `tests/security/test_business_logic.py` with all business logic tests
- Created `tests/security/test_ethical_hacking.py` with path traversal, SSRF, header injection tests
- Extended `tests/security/test_access_control.py` with privilege escalation tests
- Created `tests/security/test_info_disclosure.py` with security headers tests
- Created `tests/security/test_cookie_security.py` (tests skipped - TestClient limitation)

### Phase 2: Robustness Tests ✅
- Extended `tests/robustness/test_edge_cases.py` with special characters tests
- Extended `tests/robustness/test_upload.py` with validation tests
- Extended `tests/robustness/test_dos.py` with DoS resistance tests
- Created `tests/robustness/test_jwt_edge_cases.py`
- Created `tests/robustness/test_sqlite_contention.py`

### Phase 3: Integration Tests ✅
- Created `tests/integration/test_phone_search.py`
- Created `tests/integration/test_geo_search.py`
- Created `tests/integration/test_public_endpoints.py`
- Created `tests/integration/test_db_integrity.py`
- Extended `tests/integration/test_admin.py`, `test_contacts.py`, `test_notifications.py`, `test_reports.py`, `test_reviews.py`, `test_offers.py`

### Phase 4: DB Integrity & Coverage ✅
- All DB integrity tests implemented
- Reviews batch fetch tests added
- Analytics & admin tests extended

### conftest.py Extensions
Added to `.backend/tests/conftest.py`:
- `auth_headers()` - Create active users directly in DB (avoids pending user issue)
- `contact_factory` - Create contacts directly in DB
- `change_factory` - Create pending changes
- `bootstrap_admin_once` - Idempotent admin bootstrap
- Extended `jwt_helpers` with more edge case tokens

## Acceptance Criteria Results

| Criterion | Status |
|-----------|--------|
| No duplicate tests | ✅ |
| Fixture compatibility | ✅ |
| All tests pass | ✅ (692 passed) |
| No conftest changes needed | ✅ (extended conftest.py) |
| Naming conventions | ✅ |
| No breaking changes | ✅ |

## Final Stats

- **Files merged**: 12 new test files created, 8 existing files extended
- **Total tests**: 692 passed (was ~500 before)
- **Coverage**: 90.98% (was ~75% before)
- **Unique username handling**: Fixed by using `auth_headers()` with UUID suffix

## Phases

### Phase 1: Security Tests (PRIORITY — HIGHEST)

#### 1.1 JWT Algorithm Confusion & Edge Cases
**Source**: `tests_ant/robustness/test_jwt_edge_cases.py`
**Target**: New file `tests/robustness/test_jwt_edge_cases.py`

| Test | Description | Status in tests |
|------|-------------|-----------------|
| `test_algorithm_confusion_hs384` | HS384 instead of HS256 → 401 | ✅ Already in tests (as `wrong_algo`) |
| `test_empty_sub_claim` | Empty 'sub' claim → 401 | ❌ Missing |
| `test_missing_exp_claim` | Token without 'exp' → 200 or 401 | ❌ Missing |
| `test_future_dated_exp` | Far-future expiration → 200 | ❌ Missing |
| `test_none_algorithm_rejected` | 'none' algorithm → 401 | ❌ Missing |
| `test_no_algorithm_details_in_error` | Error messages don't leak algo | ❌ Missing |

**Also from `tests_ant/security/test_advanced_security.py`**:
| Test | Description | Status in tests |
|------|-------------|-----------------|
| `test_none_algorithm_attack` | Manual JWT with alg=none | ❌ Missing |
| `test_negative_user_id` | Token with sub="-1" → 401 | ❌ Missing |
| `test_float_user_id` | Token with sub="1.5" → 401 | ❌ Missing |
| `test_huge_user_id` | Token with sub=2^63-1 → 401 | ❌ Missing |

#### 1.2 Privilege Escalation
**Source**: `tests_ant/security/test_advanced_security.py` (TestPrivilegeEscalation)
**Target**: Extend `tests/security/test_access_control.py`

| Test | Description | Status in tests |
|------|-------------|-----------------|
| `test_role_injection_on_register` | role=admin in register ignored | ❌ Missing |
| `test_jwt_claim_manipulation_role` | Forged JWT with role=admin claim | ❌ Missing |
| `test_bootstrap_admin_replay` | Bootstrap admin only works once | ❌ Missing |
| `test_cannot_change_own_role` | Admin can't change own role | ❌ Missing |
| `test_moderator_cannot_access_admin_user_mgmt` | Mod can't list users | ✅ Partially covered |
| `test_moderator_cannot_create_users` | Mod can't create users | ❌ Missing |

#### 1.3 Data Exfiltration
**Source**: `tests_ant/security/test_advanced_security.py` (TestDataExfiltration)
**Target**: Extend `tests/security/test_access_control.py`

| Test | Description | Status in tests |
|------|-------------|-----------------|
| `test_cannot_access_other_user_contacts` | Edit/delete other's contacts | ✅ Already covered |
| `test_cannot_view_other_user_leads` | View other's leads | ✅ Already covered |
| `test_cannot_access_other_user_offers` | Modify other's offers | ✅ Partially covered |
| `test_cannot_access_other_user_schedules` | Modify other's schedules | ❌ Missing |
| `test_deactivated_user_token_rejected` | Token rejected after deactivation | ❌ Missing |
| `test_csv_export_does_not_leak_passwords` | CSV export no sensitive data | ❌ Missing |

#### 1.4 Cookie Security
**Source**: `tests_ant/security/test_advanced_security.py` (TestAuthBypassAdvanced)
**Target**: New file `tests/security/test_cookie_security.py`

| Test | Description | Status in tests |
|------|-------------|-----------------|
| `test_cookie_cannot_be_read_by_js` | HttpOnly flag validation | ❌ Missing |
| `test_cookie_samesite_lax` | SameSite flag validation | ❌ Missing |

#### 1.5 Information Disclosure
**Source**: `tests_ant/security/test_advanced_security.py` (TestInformationDisclosure)
**Target**: New file `tests/security/test_info_disclosure.py`

| Test | Description | Status in tests |
|------|-------------|-----------------|
| `test_no_stack_trace_on_500` | No traceback in errors | ❌ Missing |
| `test_no_db_path_in_errors` | No DB paths in errors | ❌ Missing |
| `test_no_internal_paths_in_404` | No internal paths in 404 | ❌ Missing |
| `test_security_headers_present` | X-Content-Type-Options, X-Frame-Options, CSP | ❌ Missing |
| `test_server_header_not_leaked` | No uvicorn/fastapi/python in Server header | ❌ Missing |
| `test_rate_limit_headers_on_api` | X-RateLimit headers present | ❌ Missing |

#### 1.6 Injection Attacks — Advanced
**Source**: `tests_ant/security/test_advanced_security.py` (TestInjectionAttacks)
**Target**: Extend `tests/security/test_sql_injection.py` or new file

| Test | Description | Status in tests |
|------|-------------|-----------------|
| `test_sqlite_pragma_injection` | PRAGMA injection via search | ❌ Missing |
| `test_header_injection` | CRLF header injection | ❌ Missing |
| `test_json_type_confusion` | Array instead of object → 422 | ❌ Missing |
| `test_multipart_injection` | Malformed multipart handling | ❌ Missing |
| `test_path_traversal_in_static` | Path traversal in static files | ❌ Missing |
| `test_null_byte_injection` | Null byte in URL | ❌ Missing |
| `test_unicode_normalization_attack` | Homoglyph attack | ❌ Missing |

#### 1.7 Business Logic Attacks
**Source**: `tests_ant/security/test_business_logic.py` + `tests_ant/security/test_advanced_security.py`
**Target**: New file `tests/security/test_business_logic.py`

| Test | Description | Status in tests |
|------|-------------|-----------------|
| `test_report_own_contact_rejected` | Can't report own contact | ❌ Missing |
| `test_cannot_report_twice` | Duplicate report rejected | ❌ Missing |
| `test_three_reports_flags_contact` | 3 reports → auto-flag | ❌ Missing |
| `test_cannot_review_own_contact` | Can't review own contact | ❌ Missing |
| `test_cannot_review_same_contact_twice` | Duplicate review rejected | ❌ Missing |
| `test_rating_must_be_1_to_5` | Rating validation | ❌ Missing |
| `test_unapproved_reviews_not_public` | Unapproved reviews hidden | ❌ Missing |
| `test_offer_cannot_expire_in_past` | Past expiry rejected | ❌ Missing |
| `test_offer_discount_must_be_1_to_99` | Discount range validation | ❌ Missing |
| `test_expired_offers_not_listed` | Expired offers filtered | ❌ Missing |
| `test_non_owner_cannot_verify_change` | Only owner verifies changes | ❌ Missing |
| `test_create_offer_with_past_expiry` | Past expiry on create | ❌ Missing |
| `test_review_rating_manipulation` | Rating integrity check | ❌ Missing |
| `test_max_pending_changes_limit` | MAX_PENDING_CHANGES enforced | ❌ Missing |
| `test_contact_status_manipulation` | User can't change status | ❌ Missing |

### Phase 2: Robustness Tests (PRIORITY — HIGH)

#### 2.1 Special Characters
**Source**: `tests_ant/robustness/test_special_chars.py`
**Target**: Extend `tests/robustness/test_edge_cases.py`

| Test | Description | Status in tests |
|------|-------------|-----------------|
| `test_null_byte_in_search_query` | Null byte in search → no crash | ❌ Missing |
| `test_control_characters_in_name` | Control chars in name | ✅ Partially covered |
| `test_rtl_override_character` | RTL override → 201 | ❌ Missing |
| `test_zero_width_joiner` | ZWJ sequences → 201 | ❌ Missing |
| `test_null_byte_in_url_path` | Null byte in URL path | ❌ Missing |
| `test_unicode_bom_in_search` | Unicode BOM in search | ❌ Missing |

#### 2.2 Upload Validation
**Source**: `tests_ant/robustness/test_upload_validation.py`
**Target**: Extend `tests/robustness/test_upload.py`

| Test | Description | Status in tests |
|------|-------------|-----------------|
| `test_oversized_file_rejected` | >5MB file → 400/413/422 | ❌ Missing |
| `test_fake_jpeg_rejected` | Text file as .jpg → 400/422 | ✅ Already covered |
| `test_empty_file_rejected` | Empty file → 400/422 | ❌ Missing |

#### 2.3 DoS Resistance
**Source**: `tests_ant/security/test_advanced_security.py` (TestDOSResistance)
**Target**: Extend `tests/robustness/test_dos.py`

| Test | Description | Status in tests |
|------|-------------|-----------------|
| `test_massive_search_query` | 50K char query → no crash | ❌ Missing |
| `test_regex_dos_in_search` | ReDoS patterns → no hang | ❌ Missing |
| `test_rapid_login_attempts` | 50 rapid logins → no crash | ❌ Missing |
| `test_concurrent_reads_same_endpoint` | ThreadPool concurrent reads | ❌ Missing |
| `test_huge_pagination_skip` | skip=999999999 → no memory issue | ✅ Already covered |
| `test_zero_limit` | limit=0 → empty results | ❌ Missing |
| `test_negative_limit` | limit=-1 → rejected | ✅ Already covered |

#### 2.4 SQLite Contention
**Source**: `tests_ant/robustness/test_sqlite_contention.py`
**Target**: New file `tests/robustness/test_sqlite_contention.py`

| Test | Description | Status in tests |
|------|-------------|-----------------|
| `test_concurrent_writes_graceful_handling` | Concurrent writes → no stack traces | ❌ Missing |
| `test_no_internal_error_on_contention` | No SQLite details in errors | ❌ Missing |

### Phase 3: Integration Tests (PRIORITY — MEDIUM)

#### 3.1 Phone Search
**Source**: `tests_ant/integration/test_phone_search.py`
**Target**: New file or extend existing search tests

| Test | Description | Status in tests |
|------|-------------|-----------------|
| `test_search_finds_partial_match` | Partial phone match | ❌ Missing |
| `test_minimum_phone_length` | Min length validation → 422 | ❌ Missing |
| `test_no_results_returns_empty` | No results → [] | ❌ Missing |
| `test_suspended_contacts_not_shown` | Suspended filtered out | ❌ Missing |
| `test_active_and_suspended_filter` | Active shown, suspended hidden | ❌ Missing |

#### 3.2 Geo Search
**Source**: `tests_ant/integration/test_geo_search.py`
**Target**: Extend existing geo tests

| Test | Description | Status in tests |
|------|-------------|-----------------|
| `test_geo_search_returns_nearby` | 20km radius returns correct contacts | ❌ Missing |
| `test_geo_search_sorted_by_distance` | Results sorted by distance | ❌ Missing |
| `test_geo_search_includes_distance_km` | distance_km field present | ❌ Missing |
| `test_geo_search_small_radius` | 5km excludes distant contacts | ❌ Missing |
| `test_geo_search_with_text` | Geo + text combined | ❌ Missing |
| `test_geo_search_with_category` | Geo + category combined | ❌ Missing |
| `test_search_without_geo_still_works` | Text search backward compatible | ❌ Missing |
| `test_search_no_filters_returns_400` | No filters → 400 | ❌ Missing |
| `test_geo_search_invalid_coords_returns_400` | Invalid coords → 400 | ❌ Missing |
| `test_geo_search_only_lat_uses_text` | lat without lon → text search | ❌ Missing |

#### 3.3 Pending Changes Workflow
**Source**: `tests_ant/integration/test_pending_changes.py`
**Target**: Extend `tests/integration/test_changes.py`

| Test | Description | Status in tests |
|------|-------------|-----------------|
| `test_verificar_cambio_pendiente` | Verify pending change | ❌ Missing |
| `test_rechazar_cambio_pendiente` | Reject pending change | ❌ Missing |
| `test_eliminar_cambio_por_creador` | Creator can delete own change | ❌ Missing |
| `test_no_eliminar_cambio_de_otro` | Non-creator can't delete → 403 | ❌ Missing |
| `test_historial_registra_cambios` | History records changes | ❌ Missing |
| `test_historial_requiere_autenticacion` | History requires auth → 401 | ❌ Missing |

#### 3.4 Offers CRUD
**Source**: `tests_ant/integration/test_audit_gaps.py` (TestOffersCRUD)
**Target**: Extend `tests/integration/test_offers.py`

| Test | Description | Status in tests |
|------|-------------|-----------------|
| `test_create_offer` | POST creates offer | ✅ Partially covered |
| `test_create_offer_past_date_fails` | Past expiry → 400 | ❌ Missing |
| `test_list_offers` | GET lists active offers | ✅ Partially covered |
| `test_list_offers_excludes_expired` | Expired offers filtered | ❌ Missing |
| `test_update_offer` | PUT updates offer | ❌ Missing |
| `test_delete_offer` | DELETE removes offer | ❌ Missing |
| `test_cannot_create_offer_for_others_contact` | Non-owner → 403 | ❌ Missing |

#### 3.5 Audit Gaps & Public Endpoints
**Source**: `tests_ant/integration/test_audit_gaps.py`
**Target**: New file or extend existing

| Test | Description | Status in tests |
|------|-------------|-----------------|
| `test_export_requires_auth` | Export → 401 without auth | ✅ Partially covered |
| `test_export_csv_with_auth` | CSV export with auth | ❌ Missing |
| `test_export_json_with_auth` | JSON export with auth | ❌ Missing |
| `test_export_invalid_format` | Invalid format → 422 | ❌ Missing |
| `test_transfer_ownership_requires_new_owner_id` | Missing field → 422 | ❌ Missing |
| `test_transfer_ownership_rejects_invalid_id` | Invalid ID → 422 | ❌ Missing |
| `test_update_schedules_validates_day_of_week` | Invalid day → 422 | ❌ Missing |
| `test_update_schedules_accepts_valid_data` | Valid schedule data | ❌ Missing |
| `test_list_schedules_returns_formatted_data` | Formatted day names | ❌ Missing |
| `test_dashboard_returns_metrics` | Dashboard metrics | ❌ Missing |
| `test_slug_redirect` | /c/{slug} → 301 redirect | ❌ Missing |
| `test_slug_not_found` | Nonexistent slug → 404 | ❌ Missing |
| `test_health_endpoint` | /health → status ok | ❌ Missing |
| `test_public_users_returns_active_users` | Public users list | ❌ Missing |
| `test_public_users_excludes_inactive` | Inactive users excluded | ❌ Missing |
| `test_list_contacts_pagination` | Pagination support | ❌ Missing |
| `test_list_contacts_by_category` | Category filter | ❌ Missing |
| `test_related_businesses_no_geo` | Related without geo → [] | ❌ Missing |
| `test_lead_registration_optional_auth` | Leads with/without auth | ❌ Missing |
| `test_lead_requires_contact_exist` | Leads → 404 if no contact | ❌ Missing |
| `test_notifications_requires_auth` | Notifications → 401 | ❌ Missing |
| `test_vapid_public_key_public` | VAPID key public endpoint | ❌ Missing |
| `test_utilities_public_endpoint` | Utilities public endpoint | ❌ Missing |
| `test_utilities_requires_admin_for_create` | Utilities create → admin | ❌ Missing |
| `test_report_requires_auth` | Report → 401 | ❌ Missing |
| `test_admin_reports_requires_admin` | Admin reports → 403 | ❌ Missing |
| `test_admin_contact_status_requires_admin` | Status change → admin | ❌ Missing |

### Phase 4: DB Integrity & Coverage (PRIORITY — LOW)

#### 4.1 Database Integrity
**Source**: `tests_ant/integration/test_db_integrity.py`
**Target**: New file `tests/integration/test_db_integrity.py`

| Test | Description | Status in tests |
|------|-------------|-----------------|
| `test_pragma_foreign_keys_on` | PRAGMA foreign_keys=1 | ❌ Missing |
| `test_production_pragma_listener` | Production PRAGMA listener | ❌ Missing |
| `test_get_db_generator` | get_db() yields/closes session | ❌ Missing |
| `test_contact_with_invalid_category_fails` | FK violation on category | ❌ Missing |
| `test_contact_with_invalid_user_fails` | FK violation on user | ❌ Missing |
| `test_delete_contact_removes_changes` | Cascade delete changes | ❌ Missing |
| `test_delete_contact_removes_history` | Cascade delete history | ❌ Missing |
| `test_contact_create_sets_user_id` | user_id set on create | ❌ Missing |
| `test_pending_changes_count_decrements_on_verify` | Count decrements on verify | ❌ Missing |
| `test_pending_changes_count_decrements_on_reject` | Count decrements on reject | ❌ Missing |
| `test_pending_changes_count_never_negative` | Count >= 0 | ❌ Missing |

#### 4.2 Reviews Batch Fetch (N+1 validation)
**Source**: `tests_ant/integration/test_audit_gaps.py` (TestReviewsBatchFetch)
**Target**: Extend `tests/integration/test_reviews.py`

| Test | Description | Status in tests |
|------|-------------|-----------------|
| `test_list_reviews_with_multiple_reviews` | Reviews with usernames (batch fetch) | ❌ Missing |

#### 4.3 Analytics & Admin
**Source**: `tests_ant/integration/test_audit_gaps.py` (TestAnalyticsExport, TestAdminAnalytics)
**Target**: Extend `tests/integration/test_admin.py`

| Test | Description | Status in tests |
|------|-------------|-----------------|
| `test_export_csv_requires_auth` | Export → 401 | ❌ Missing |
| `test_export_csv_requires_admin` | Export → 403 for user | ❌ Missing |
| `test_export_csv_returns_csv` | Admin gets CSV | ❌ Missing |
| `test_analytics_requires_auth` | Analytics → 401 | ❌ Missing |
| `test_analytics_returns_data` | Admin gets analytics | ❌ Missing |

## Acceptance Criteria

1. **No duplicate tests**: Every test added must not already exist in `.backend/tests`
2. **Fixture compatibility**: All tests must use fixtures from `.backend/tests/conftest.py` (not `tests_ant/conftest.py`)
3. **All tests pass**: `pytest backend/tests/` must pass with 0 failures
4. **No conftest changes needed**: Tests should work with existing conftest.py, or conftest.py should be extended minimally
5. **Naming conventions**: Follow existing naming patterns (`test_` prefix, class-based grouping)
6. **No breaking changes**: Existing tests must continue to pass

## Implementation Rules

1. **Do NOT copy-paste blindly**: Adapt each test to use the main conftest.py fixtures
2. **Key fixture differences to handle**:
   - `tests_ant` uses `database_session` alias → use `db_session` from main conftest
   - `tests_ant` uses `auth_headers()` factory function → main conftest has `user_headers`, `admin_headers`, `mod_headers` as fixtures
   - `tests_ant` has `contact_factory`, `change_factory` → may need to add these to main conftest
   - `tests_ant` `create_user` takes positional args → main conftest uses keyword-only args
3. **Merge, don't duplicate**: If a test already exists in main suite, skip it
4. **Group logically**: Place tests in the appropriate category (security, robustness, integration, unit)

## Estimated Impact

- **New test files to create**: ~6-8
- **Existing files to extend**: ~10-12
- **Estimated new tests**: ~100+
- **Estimated total tests after merge**: ~200+
