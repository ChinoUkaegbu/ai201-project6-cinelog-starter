# PR Response Doc — CineLog Watchlist Feature

## AI Usage

<!-- Fill in at the end — how you used AI tools during this project -->

I used an AI assistant (Claude) in two main ways.

**Codebase orientation and bug-catching.** Early on, I had it summarize `models.py` and `collection_service.py` so I understood the existing naming and error-handling patterns before writing the watchlist code. After rebasing onto `main`, `git rebase` reported success with no conflicts, but the assistant caught that `WatchlistEntry` had actually been silently dropped from `models.py` — something the success message gave no indication of.

**Stress-testing Comments 4 and 5.** For Comment 4 (default visibility), I gave it my position — `public=True`, since CineLog is a community app — and it drafted the full reasoning/tradeoff argument, which I used close to as-written. For Comment 5 (sort order), the position was mine from the start (keep alphabetical, so I don't lose track of older items), but the assistant raised a counterargument I hadn't considered — that `get_collection()` already sorts by date-added, so date-added would be more consistent across features. I engaged with that directly and still landed on alphabetical, since collection and watchlist serve different purposes.

## Comment 1 — Rename

**What I did:** Renamed `save_to_watchlist()` to `add_to_watchlist()` in `watchlist_service.py` to match the project's `verb_to_noun` naming convention (consistent with `add_to_collection()`), and updated all call sites that referenced the old name (routes/tests/etc.).

**How I verified:** Used VSCode's "Rename Symbol" (F2) on the definition in `services/watchlist_service.py`, which updated the one call site in `routes/watchlist.py` (the import line and its use inside `add_film()`). After the rename, I ran a project-wide text search for the old name (`save_to_watchlist`) across the entire repo and confirmed zero remaining occurrences — the definition and its single call site were the only two references, and both now read `add_to_watchlist`.

## Comment 2 — Deduplication

**What I did:** Added deduplication logic to `add_to_watchlist()` in `services/watchlist_service.py`, following the same pattern used in `add_to_collection()` (`services/collection_service.py`). Introduced a new `AlreadyOnWatchlistError` exception (defined locally in `watchlist_service.py`, matching how `AlreadyInCollectionError` is defined locally in `collection_service.py`). Before creating a new `WatchlistEntry`, the function now queries for an existing entry matching `(user_id, film_id)` and raises `AlreadyOnWatchlistError` if one is found. The existing `FilmNotFoundError` check still runs first, unchanged. `get_watchlist()` was not modified, since the comment scoped this change to `add_to_watchlist()` only.

**How I verified:** Compared the new dedup block line-by-line against the equivalent block in `add_to_collection()` to confirm the same query shape (`filter_by(user_id=..., film_id=...).first()`) and control flow (check-then-raise before insert). Confirmed the docstring's `Raises` section was updated to document the new exception.

## Comment 3 — Missing test

**What I did:** Created `tests/test_watchlist.py` and added `test_add_to_watchlist_nonexistent_film_raises`, the watchlist equivalent of `test_add_to_collection_nonexistent_film_raises` in `tests/test_collection.py`. It follows the same fixture and assertion structure: an `app` fixture (in-memory SQLite via `create_app`) and a `sample_user` fixture, then a `pytest.raises(FilmNotFoundError)` block calling `add_to_watchlist()` with a film id that doesn't exist in the database. No `sample_film` fixture is used, matching the reference test, since the case being tested is specifically that the film does _not_ exist.

One deviation from the reference test: I used an integer sentinel (`999999`) for the fake film id instead of a UUID string, since `Film.id` is `db.Integer` in this branch's `models.py`. The original test's UUID-string sentinel appears to be a forward-reference to the main-branch refactor (int → UUID) rather than something that matches this branch's current schema.

**How I verified:** Ran the test directly:

```
pytest tests/test_watchlist.py -v
```

Result: `1 passed in 1.16s`.

## Comment 4 — Default visibility

**My position:** Watchlist entries should default to `public=True`.

**Reasoning:** CineLog is a community film-tracking app — the value of a "watchlist" feature in a social context comes largely from other users being able to see what you're planning to watch, not just what you've already watched. A private-by-default watchlist would make the feature behave like a personal to-do list that happens to live in a shared app, rather than something that feeds the app's social/discovery loop (e.g. seeing that a friend wants to watch a film you also want to watch, or browsing what's trending among people you follow). Defaulting to public also means most users — who won't go out of their way to change a privacy setting — end up participating in that shared layer without extra friction, which is the behavior we want to optimize for: passive, low-effort visibility that makes the community aspect of the app work by default rather than by opt-in.

**Tradeoff acknowledged:** The cost is that some users won't realize their watchlist is visible to others until it already has been — a watchlist can reveal things about someone's taste, mood, or interests (e.g. genre binges, a niche or embarrassing pick) that they didn't consciously choose to share, in a way that's arguably more exposing than a _watched_ list, since it reflects intent rather than a completed, already-public-ish action. A private-by-default approach would avoid that, at the cost of most watchlists sitting invisible and unused as a social feature, since most users don't proactively flip privacy toggles. We're accepting the first risk to avoid the second.

## Comment 5 — Sort order

**My position:** Keeping the current alphabetical sort (`Film.title.asc()`), rather than switching to date-added order.

**Reasoning:** A watchlist isn't a feed you skim once and move past — it's a backlog you return to repeatedly, either to decide what to watch next or to check whether you already added something. Sorting by recency means anything added early keeps sinking further down as the list grows, which works against the actual purpose of a watchlist: not forgetting the things you meant to get to. Alphabetical gives every entry a stable, predictable position regardless of when it was added, so finding something specific doesn't depend on remembering when you added it. That stability matters more here than surfacing "what's new," since the watchlist has no natural endpoint the way a feed does — there's no "caught up" state to optimize for.

**Engagement with reviewer's point:** The recency argument is real for a lot of list UIs, and for many apps, "what did I just add" is the more common question. There's also a consistency argument in the same direction I want to be upfront about even though I'm not adopting it: `get_collection()` already sorts by `date_added.desc()`, so date-added order would make sort behavior match across collection and watchlist. But I'd argue the two lists serve different mental models — collection is a historical log, where chronology _is_ the point (it's a record of when you watched things); watchlist is a working backlog, where findability is the point (it's a record of what you still want to get to). Matching their sort order for consistency's sake would optimize for something neither list actually needs. Given that, I'd rather keep alphabetical here — but I'm glad to revisit if usage shows people mostly care about "what did I just add" rather than "where's the thing I added last month."

## Comment 6 — Rebase

**What conflicted:** `main` had merged a refactor migrating `Film.id` (and all `film_id` foreign keys) from `db.Integer` to `db.String(36)` UUIDs. My `feature/watchlist` branch predated that refactor and still assumed integer film ids throughout — in `models.py` (`WatchlistEntry.film_id`), `watchlist_service.py` and `routes/watchlist.py` (docstrings describing `film_id` as an int), and `tests/test_watchlist.py` (a fake-id sentinel of `999999`).

The rebase itself (`git fetch origin` + `git rebase origin/main`) completed with no conflict markers reported. That turned out to be misleading rather than reassuring: because `WatchlistEntry` was a class that only existed on my branch, git had no equivalent hunk on `main` to conflict against, and the automatic merge of `models.py` silently dropped the `WatchlistEntry` class entirely instead of keeping it alongside the refactored `Film`/`CollectionEntry`. So the real "conflict" wasn't a textual one shown by git — it was a missing class plus a semantic mismatch (int ids vs. the new UUID ids) that I only found by manually diffing the post-rebase files against what I expected, rather than trusting the "successfully rebased" message.

**How I resolved it:**

- Re-added `WatchlistEntry` to `models.py` in its original position, with `film_id` changed from `db.Column(db.Integer, ...)` to `db.Column(db.String(36), db.ForeignKey("film.id"), ...)` to match the refactored `Film.id`.
- Updated the `film_id` docstring in `watchlist_service.py`'s `add_to_watchlist()` from `film_id (int): ID of the film. (Note: integer — pre-refactor)` to `film_id (str): UUID of the film.` No functional code changes were needed there — `db.session.get(Film, film_id)` and the `filter_by(film_id=film_id)` dedup check both work with either type since they just pass the value through; only the documentation was stale.
- Updated the `Body:` docstring comment in `routes/watchlist.py`'s `add_film()` from `{ "film_id": <int> }` to `{ "film_id": <str> }  # UUID`.
- Updated `tests/test_watchlist.py`'s `fake_film_id` from the integer sentinel `999999` to a UUID-shaped string (`"00000000-0000-0000-0000-000000000000"`), matching the sentinel style already used in `test_collection.py`'s equivalent test, since an integer no longer represents a plausible "doesn't exist" id against a UUID-keyed column.

**How I verified no conflict remains:** Ran the full test suite after making these changes:

```
pytest -v
```

All tests passed, including `test_add_to_watchlist_nonexistent_film_raises`. Also confirmed the rebase produced a linear history with no merge commits:

```
git log --oneline --merges
```

returned no output, confirming `feature/watchlist` is a clean rebase onto `origin/main` rather than a merge.

---

## Final Commit History

After rewriting history with `git rebase -i HEAD~9` (rewording two non-conventional commits — `feat: add watchlist model and endpoints` and `refactor: rename save_to_watchlist to add_to_watchlist` — and leaving the rest as-is since each already represented one logical, conventionally-formatted change):

```
git log --oneline
```

![Final commit history](./commit_history.png)

All commits above `origin/main` use conventional-commit prefixes (`feat:`, `fix:`, `test:`, `docs:`, `refactor:`), and no merge commits appear anywhere in the log.

## PR Description

<!-- Written at the end — feature overview, design decisions, manual testing steps -->

### What this PR does

Adds a watchlist feature to CineLog, letting users save films they intend to watch later, separate from their existing collection of films they've already watched. This includes:

- A `WatchlistEntry` model (`user_id`, `film_id`, `date_added`, `public`)
- `add_to_watchlist(user_id, film_id)` and `get_watchlist(user_id)` in `services/watchlist_service.py`, following the same structure and error-handling conventions as the existing `collection_service.py`
- `GET /watchlist/<user_id>` and `POST /watchlist/<user_id>/add` endpoints in `routes/watchlist.py`
- Deduplication so a film can't be added to the same user's watchlist twice (`AlreadyOnWatchlistError`)
- A test suite in `tests/test_watchlist.py`

### Design decisions

Two decisions came up during review and are documented in full (with reasoning and tradeoffs) in `pr-response.md`, Comments 4 and 5:

- **Default visibility (`public=True`):** Watchlist entries are public by default, optimizing for CineLog's community/discovery use case — most users won't manually flip a privacy toggle, so a public default is what makes the social layer of the app actually work. The tradeoff (unintentional exposure of a user's taste/interests) is acknowledged and accepted.
- **Sort order (alphabetical by title):** `get_watchlist()` sorts alphabetically rather than by date-added. A watchlist is treated as a findability-first backlog rather than a recency feed — users return to it to locate something specific, and alphabetical order keeps every entry's position stable regardless of when it was added, unlike a recency sort which buries older entries as the list grows.

### How to manually test

1. Start the app locally and ensure the database is created (`db.create_all()` or your existing setup script).
2. Create a user, e.g. via the existing user-creation flow or directly in a Python shell:

```python
   from models import User
   from app import db
   user = User(username="testuser", email="test@example.com")
   db.session.add(user)
   db.session.commit()
   print(user.id)
```

3. Create a film the same way (or use an existing one), and note its `id` (a UUID string).
4. Add a film to the watchlist:

```
   POST /watchlist/<user_id>/add
   Body: { "film_id": "<film-uuid>" }
```

Expect a `201` response with the new watchlist entry.

5. View the watchlist:

```
   GET /watchlist/<user_id>
```

Expect a `200` response with a list containing the film you added, sorted alphabetically by title if you add more than one.

6. Confirm deduplication: repeat step 4 with the same `user_id`/`film_id` pair. Expect the request to fail rather than silently create a second entry.

7. Confirm the nonexistent-film case: repeat step 4 with a `film_id` that doesn't exist in the database. Expect the request to fail rather than create an entry.

---

## Stretch Features

### `remove_from_watchlist()`

**What I did:**
Added `remove_from_watchlist(user_id, film_id)` to `services/watchlist_service.py`, following the same pattern as `remove_from_collection()` in `collection_service.py`: look up the existing entry for `(user_id, film_id)`, raise a dedicated exception (`NotOnWatchlistError`, mirroring `NotInCollectionError`) if none exists, otherwise delete it and commit, returning `True`. Also added two tests in `tests/test_watchlist.py`:

- `test_remove_from_watchlist_deletes_entry` — adds a film to the watchlist, removes it, and confirms the `WatchlistEntry` no longer exists in the database.
- `test_remove_from_watchlist_not_present_raises` — confirms removing a film that was never added raises `NotOnWatchlistError` rather than silently succeeding or raising a generic error.

**How I verified:**
Ran the full test suite:

```
pytest -v
```

All tests passed, including both new removal tests.

---

## Bug Fix — Missing `WatchlistEntry` Relationships

**What happened:**
While manually testing the feature end-to-end (per the "How to manually test" steps in this PR description), adding a film to a watchlist and then calling `GET /watchlist/<user_id>` raised:

```
AttributeError: 'WatchlistEntry' object has no attribute 'film'
```

`CollectionEntry` gets its `.film` attribute from `Film.collection_entries = db.relationship("CollectionEntry", backref="film", lazy=True)` in `models.py`, but no equivalent relationship existed for `WatchlistEntry`. `get_watchlist()` calls `entry.film.to_dict()`, which only worked once the relationship actually existed and was exercised with real data — none of the existing tests happened to call `get_watchlist()` after adding a film with the film relationship in play, so it went undetected until manual testing.

**What I did:**
Added two relationships to `models.py`, matching the existing `CollectionEntry` pattern:

- `Film.watchlist_entries = db.relationship("WatchlistEntry", backref="film", lazy=True)` — fixes the actual bug, giving `WatchlistEntry` instances a `.film` attribute.
- `User.watchlist_entries = db.relationship("WatchlistEntry", backref="user", lazy=True)` — not required by any current code path (nothing calls `.user` on a `WatchlistEntry` or `.watchlist_entries` on a `User` yet), but added proactively for consistency with `User.collection_entries`, since it's the same class of gap.

**How I verified:**
Restarted the server, repeated the manual test flow (add a film to the watchlist, then `GET /watchlist/<user_id>`), and confirmed the endpoint now returns the expected film list instead of a 500 error. Also re-ran the full test suite to confirm the new relationships didn't change any existing behavior.
