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
