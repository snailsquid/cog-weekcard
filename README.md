# weekcard

Two image cards, drawn by the [Canvas](https://github.com/snailsquid/cog-canvas) cog (must be
loaded) and offered to [Morning](https://github.com/snailsquid/cog-morning) as sections:

- **life**: week number, day and date, and how much of the week has passed. Weeks are counted
  from college start (week 1 is the Monday–Sunday week containing it); the ISO week if the
  college dates aren't set or college hasn't started.
- **college**: the percentage of college finished (2 decimals, by the hour) as the headline, with
  days done / days left / weeks left beside it, a progress bar, and a week grid (one row per ISO
  year, a square per week; finished weeks green, this week outlined, weeks left dim). Kept wide so
  Discord shows it at the same width as the life card. Skipped until both college dates are set.

The timezone is the owner's, from the [Profile](https://github.com/snailsquid/cog-profile) cog (UTC
if it isn't loaded).

## Commands

| Command | Who | What |
|---|---|---|
| `[p]weekcard` | anyone | Posts the life card. |
| `[p]weekcard college` | anyone | Posts the college card. |
| `[p]weekcard college from <date>` | owner | When college started: `YYYY`, `YYYY-MM` (first day of month) or `YYYY-MM-DD`. |
| `[p]weekcard college until <date>` | owner | When it ends: `YYYY`, `YYYY-MM` (last day of month) or `YYYY-MM-DD`. |

The range spans at most 10 calendar years.

## Morning sections

| Key | Order | What |
|---|---|---|
| `life` | 10 | the life card |
| `college` | 11 | the college card (skipped if the dates aren't set) |

Offered through `morning_sections()`, drawn at Morning's send time.

## Events emitted

None.

## Public methods

| Method | What |
|---|---|
| `await cog.life_card(now) -> Optional[discord.File]` | Life card for a timezone-aware `datetime`; `None` if Canvas isn't loaded. |
| `await cog.college_card(now) -> Optional[discord.File]` | College card; `None` if Canvas isn't loaded or the dates aren't set. |
| `await cog.college_range() -> Optional[(date, date)]` | College start and end. |
| `cog.morning_sections()` | Morning's section hook. |

## Secrets

None.
