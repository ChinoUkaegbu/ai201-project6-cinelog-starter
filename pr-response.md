# PR Response Doc — CineLog Watchlist Feature

## AI Usage

<!-- Fill in at the end — how you used AI tools during this project -->

## Comment 1 — Rename

**What I did:** Renamed `save_to_watchlist()` to `add_to_watchlist()` in `watchlist_service.py` to match the project's `verb_to_noun` naming convention (consistent with `add_to_collection()`), and updated all call sites that referenced the old name (routes/tests/etc.).

**How I verified:** Used VSCode's "Rename Symbol" (F2) on the definition in `services/watchlist_service.py`, which updated the one call site in `routes/watchlist.py` (the import line and its use inside `add_film()`). After the rename, I ran a project-wide text search for the old name (`save_to_watchlist`) across the entire repo and confirmed zero remaining occurrences — the definition and its single call site were the only two references, and both now read `add_to_watchlist`.

## Comment 2 — Deduplication

**What I did:** Added deduplication logic to `add_to_watchlist()` in `services/watchlist_service.py`, following the same pattern used in `add_to_collection()` (`services/collection_service.py`). Introduced a new `AlreadyOnWatchlistError` exception (defined locally in `watchlist_service.py`, matching how `AlreadyInCollectionError` is defined locally in `collection_service.py`). Before creating a new `WatchlistEntry`, the function now queries for an existing entry matching `(user_id, film_id)` and raises `AlreadyOnWatchlistError` if one is found. The existing `FilmNotFoundError` check still runs first, unchanged. `get_watchlist()` was not modified, since the comment scoped this change to `add_to_watchlist()` only.

**How I verified:** Compared the new dedup block line-by-line against the equivalent block in `add_to_collection()` to confirm the same query shape (`filter_by(user_id=..., film_id=...).first()`) and control flow (check-then-raise before insert). Confirmed the docstring's `Raises` section was updated to document the new exception.

## Comment 3 — Missing test

**What I did:**

**How I verified:**

## Comment 4 — Default visibility

**My position:**

**Reasoning:**

**Tradeoff acknowledged:**

## Comment 5 — Sort order

**My position:**

**Reasoning:**

**Engagement with reviewer's point:**

## Comment 6 — Rebase

**What conflicted:**

**How I resolved it:**

**How I verified no conflict remains:**

## PR Description

<!-- Written at the end — feature overview, design decisions, manual testing steps -->
