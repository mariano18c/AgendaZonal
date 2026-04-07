"""Integration tests — Offers CRUD."""
import pytest
from datetime import datetime, timezone, timedelta
from tests.conftest import _bearer


class TestCreateOffer:
    def test_create_offer(self, client, create_user, create_contact):
        owner = create_user()
        c = create_contact(user_id=owner.id)
        exp = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        r = client.post(f"/api/contacts/{c.id}/offers", headers=_bearer(owner),
                         json={"title": "Promo Verano", "discount_pct": 25,
                               "expires_at": exp})
        assert r.status_code == 201
        assert r.json()["title"] == "Promo Verano"
        assert r.json()["is_active"] is True

    def test_create_offer_not_owner(self, client, create_user, create_contact):
        c = create_contact()
        stranger = create_user()
        exp = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        r = client.post(f"/api/contacts/{c.id}/offers", headers=_bearer(stranger),
                         json={"title": "X", "expires_at": exp})
        assert r.status_code == 403

    def test_create_offer_unauthenticated(self, client, create_contact):
        c = create_contact()
        exp = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        r = client.post(f"/api/contacts/{c.id}/offers",
                         json={"title": "X", "expires_at": exp})
        assert r.status_code == 401


class TestListOffers:
    def test_list_offers(self, client, create_contact, create_offer):
        c = create_contact()
        create_offer(contact_id=c.id)
        r = client.get(f"/api/contacts/{c.id}/offers")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_list_offers_nonexistent(self, client):
        r = client.get("/api/contacts/99999/offers")
        assert r.status_code == 404


class TestUpdateOffer:
    def test_update_offer(self, client, create_user, create_contact, create_offer):
        owner = create_user()
        c = create_contact(user_id=owner.id)
        offer = create_offer(contact_id=c.id)
        exp = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        r = client.put(f"/api/contacts/{c.id}/offers/{offer.id}",
                        headers=_bearer(owner),
                        json={"title": "Updated Promo", "discount_pct": 10, "expires_at": exp})
        assert r.status_code == 200
        assert r.json()["title"] == "Updated Promo"

    def test_deactivate_offer(self, client, create_user, create_contact, create_offer):
        owner = create_user()
        c = create_contact(user_id=owner.id)
        offer = create_offer(contact_id=c.id)
        exp = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        r = client.put(f"/api/contacts/{c.id}/offers/{offer.id}",
                        headers=_bearer(owner),
                        json={"title": offer.title, "discount_pct": 1, "expires_at": exp})
        assert r.status_code == 200


class TestDeleteOffer:
    def test_delete_offer(self, client, create_user, create_contact, create_offer):
        owner = create_user()
        c = create_contact(user_id=owner.id)
        offer = create_offer(contact_id=c.id)
        r = client.delete(f"/api/contacts/{c.id}/offers/{offer.id}",
                           headers=_bearer(owner))
        assert r.status_code == 204

    def test_delete_offer_not_owner(self, client, create_user, create_contact, create_offer):
        c = create_contact()
        offer = create_offer(contact_id=c.id)
        stranger = create_user()
        r = client.delete(f"/api/contacts/{c.id}/offers/{offer.id}",
                           headers=_bearer(stranger))
        assert r.status_code == 403

    def test_delete_nonexistent_offer(self, client, create_user, create_contact):
        owner = create_user()
        c = create_contact(user_id=owner.id)
        r = client.delete(f"/api/contacts/{c.id}/offers/99999",
                           headers=_bearer(owner))
        assert r.status_code == 404


class TestOfferEdgeCases:
    """Additional offer edge cases — merged from tests_ant."""

    def test_create_offer_past_date_fails(self, client, create_user, create_contact):
        """Cannot create offer with past expiration date."""
        owner = create_user()
        c = create_contact(user_id=owner.id)
        past_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        r = client.post(f"/api/contacts/{c.id}/offers", headers=_bearer(owner),
                         json={"title": "Expired", "discount_pct": 10, "expires_at": past_date})
        assert r.status_code == 400

    def test_list_offers_excludes_expired(self, client, create_user, create_contact, db_session):
        """Expired offers should not appear in public listing."""
        from app.models.offer import Offer
        owner = create_user()
        c = create_contact(user_id=owner.id)
        past = datetime.now(timezone.utc) - timedelta(days=1)
        expired = Offer(
            contact_id=c.id, title="Expired Offer", description="Old",
            discount_pct=50, expires_at=past, is_active=True,
        )
        db_session.add(expired)
        db_session.commit()
        r = client.get(f"/api/contacts/{c.id}/offers")
        assert r.status_code == 200
        titles = [o["title"] for o in r.json()]
        assert "Expired Offer" not in titles

    def test_cannot_create_offer_for_others_contact(self, client, create_user, create_contact):
        """Non-owner should not be able to create offers for another user's contact."""
        owner = create_user(username="offer_owner", email="offer_owner@test.com")
        c = create_contact(user_id=owner.id)
        stranger = create_user(username="offer_stranger", email="offer_stranger@test.com")
        exp = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        r = client.post(f"/api/contacts/{c.id}/offers", headers=_bearer(stranger),
                         json={"title": "Hacker Offer", "discount_pct": 99, "expires_at": exp})
        assert r.status_code == 403
