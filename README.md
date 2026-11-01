# weekcard

A week-at-a-glance image: ISO week number, day and date, how much of the week has passed, and a
GitHub-style day grid counting down to a configurable date (one row per calendar year, a column
per week; finished days green, today outlined, days left dim). The card grows with the range.

Drawn by the [Canvas](https://github.com/snailsquid/cog-canvas) cog, which must be loaded. The
timezone is the owner's, from the [Profile](https://github.com/snailsquid/cog-profile) cog (UTC if
it isn't loaded).

## Commands

| Command | Who | What |
|---|---|---|
| `[p]weekcard` | anyone | Posts the card for right now. |
| `[p]weekcard until <date>` | owner | Count down to `YYYY`, `YYYY-MM` (end of month) or `YYYY-MM-DD`. `reset` = end of this year (default). |
| `[p]weekcard from <date>` | owner | Start the grid at a date (start of month/year for partial dates). `reset` = start of this year (default). |

The range spans at most 10 calendar years.

## Morning section

Offers the `weekcard` section (order 10) to [Morning](https://github.com/snailsquid/cog-morning)
through `morning_sections()`, drawn at Morning's send time.

## Events emitted

None.

## Public methods

| Method | What |
|---|---|
| `await cog.card(now) -> Optional[discord.File]` | The card for a timezone-aware `datetime`; `None` if Canvas isn't loaded. |
| `cog.morning_sections()` | Morning's section hook. |

## Secrets

None.
