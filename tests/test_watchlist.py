"""
tests/test_watchlist.py — CineLog

Tests for the watchlist service.
"""

import pytest
from app import create_app, db
from models import User, Film, WatchlistEntry
from services.watchlist_service import (
    add_to_watchlist,
    remove_from_watchlist,
    get_watchlist,
    AlreadyOnWatchlistError,
    NotOnWatchlistError,
)
from services.collection_service import FilmNotFoundError


@pytest.fixture
def app():
    """Create an isolated test app with an in-memory database."""
    app = create_app(config={
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def sample_user(app):
    """A user to use in tests."""
    with app.app_context():
        user = User(username="testuser", email="test@example.com")
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def sample_film(app):
    """A film to use in tests."""
    with app.app_context():
        film = Film(title="Paddington 2", year=2017, genre="Comedy")
        db.session.add(film)
        db.session.commit()
        return film.id


# ── Nonexistent film ─────────────────────────────────────────────────────────

def test_add_to_watchlist_nonexistent_film_raises(app, sample_user):
    """
    Adding a film_id that doesn't exist in the database should raise
    FilmNotFoundError, not a database integrity error.
    """
    with app.app_context():
        fake_film_id = "00000000-0000-0000-0000-000000000000"

        with pytest.raises(FilmNotFoundError):
            add_to_watchlist(user_id=sample_user, film_id=fake_film_id)


# ── Removal ──────────────────────────────────────────────────────────────────

def test_remove_from_watchlist_deletes_entry(app, sample_user, sample_film):
    """
    Removing a film that's on the watchlist should delete its WatchlistEntry.
    """
    with app.app_context():
        add_to_watchlist(user_id=sample_user, film_id=sample_film)

        result = remove_from_watchlist(user_id=sample_user, film_id=sample_film)
        assert result is True

        # Confirm it's actually gone
        remaining = WatchlistEntry.query.filter_by(
            user_id=sample_user, film_id=sample_film
        ).first()
        assert remaining is None


def test_remove_from_watchlist_not_present_raises(app, sample_user, sample_film):
    """
    Removing a film that was never added to the watchlist should raise
    NotOnWatchlistError, not silently succeed.
    """
    with app.app_context():
        with pytest.raises(NotOnWatchlistError):
            remove_from_watchlist(user_id=sample_user, film_id=sample_film)


# ── get_watchlist end-to-end ──────────────────────────────────────────────────

def test_get_watchlist_returns_added_film_with_correct_fields(app, sample_user, sample_film):
    """
    get_watchlist() should return the film's data merged with watchlist
    metadata (date_added, public) after a film has actually been added.

    This specifically exercises the WatchlistEntry -> Film relationship
    (entry.film.to_dict()) with real data, which previously raised
    AttributeError because Film had no relationship pointing back to
    WatchlistEntry (see "Bug Fix — Missing WatchlistEntry Relationships"
    in this doc). Adding a film and then calling get_watchlist() end-to-end,
    rather than only checking the WatchlistEntry row directly, is what
    would have caught that bug before it reached manual testing.
    """
    with app.app_context():
        add_to_watchlist(user_id=sample_user, film_id=sample_film)

        watchlist = get_watchlist(sample_user)

        assert len(watchlist) == 1
        entry = watchlist[0]
        assert entry["id"] == sample_film
        assert entry["title"] == "Paddington 2"
        assert "date_added" in entry
        assert entry["public"] is True