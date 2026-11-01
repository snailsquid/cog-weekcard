import calendar
import re
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import discord
from redbot.core import Config, commands
from redbot.core.bot import Red

BACKGROUND = "#1e1f22"
PANEL = "#2b2d31"
TILE = "#313338"
MUTED = "#949ba4"
ACCENT = "#5865f2"
TRACK = "#3f4147"
DAY_DONE = "#26a641"
DAY_LEFT = "#383a40"
TODAY_BORDER = "#ffffff"

WIDTH = 800
GRID_WIDTH = WIDTH - 2 * 16 - 2 * 14  # card padding, panel padding
YEAR_LABEL = 44
ROW_GAP = 10
GRID_GAP = 3
MAX_CELL = 11
MAX_YEARS = 10

DATE_RE = re.compile(r"^(\d{4})(?:-(\d{1,2})(?:-(\d{1,2}))?)?$")


def parse_date(text: str, end: bool) -> date:
    """`YYYY`, `YYYY-MM` or `YYYY-MM-DD`. A partial date is its first day, or its last if `end`."""
    match = DATE_RE.match(text.strip())
    if not match:
        raise ValueError(f"`{text}` isn't a date. Use `YYYY`, `YYYY-MM` or `YYYY-MM-DD`.")
    year = int(match[1])
    month = int(match[2]) if match[2] else (12 if end else 1)
    if not 1 <= month <= 12:
        raise ValueError(f"`{text}`: no month {month}.")
    last = calendar.monthrange(year, month)[1]
    day = int(match[3]) if match[3] else (last if end else 1)
    if not 1 <= day <= last:
        raise ValueError(f"`{text}`: no day {day} in that month.")
    return date(year, month, day)


def resolve_range(today: date, start: Optional[str], end: Optional[str]) -> Tuple[date, date]:
    """The configured range; unset ends default to this calendar year."""
    first = date.fromisoformat(start) if start else date(today.year, 1, 1)
    last = date.fromisoformat(end) if end else date(today.year, 12, 31)
    return first, last


def week_progress(now: datetime) -> float:
    """Fraction of the ISO week (Monday 00:00 to Monday 00:00) that has passed."""
    start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    return min(1.0, (now - start) / timedelta(days=7))


def done_color(day: date) -> str:
    """Colour of a finished day. Later: vary the alpha (`#26a641` + `"80"`) with how many tasks
    were finished that day; Canvas blends translucent cells."""
    return DAY_DONE


def year_cells(year: int, first: date, last: date, today: date) -> List[Any]:
    """One calendar year, Monday-first, a column per week (GitHub style). Days outside
    [first, last] are None (invisible); finished days green, today outlined, the rest dim."""
    day = date(year, 1, 1)
    cells: List[Any] = [None] * day.weekday()
    while day.year == year:
        if not first <= day <= last:
            cells.append(None)
        elif day < today:
            cells.append(done_color(day))
        elif day == today:
            cells.append({"fill": DAY_LEFT, "border": TODAY_BORDER})
        else:
            cells.append(DAY_LEFT)
        day += timedelta(days=1)
    return cells


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'s' * (n != 1)}"


def left_label(today: date, first: date, last: date) -> str:
    end = f"{last.day} {last:%B %Y}"
    if today > last:
        return f"Reached {end}"
    if today < first:
        return f"Starts {first.day} {first:%B %Y}"
    weeks, days = divmod((last - today).days, 7)
    parts = [_plural(weeks, "week")] if weeks else []
    if days or not weeks:
        parts.append(_plural(days, "day"))
    return f"{' and '.join(parts)} left until {end}"


def _centered(*lines: Dict[str, Any]) -> Dict[str, Any]:
    return {"type": "column", "children": [{"type": "spacer"}, *lines, {"type": "spacer"}]}


def build_spec(now: datetime, first: date, last: date) -> Dict[str, Any]:
    """The Canvas spec for the card at `now` (timezone-aware), counting days in [first, last].
    One grid row per calendar year; the card grows with the range."""
    today = now.date()
    week = today.isocalendar()[1]
    progress = week_progress(now)
    years = {y: year_cells(y, first, last, today) for y in range(first.year, last.year + 1)}
    columns = max(-(-len(cells) // 7) for cells in years.values())
    grid_width = GRID_WIDTH - YEAR_LABEL - ROW_GAP
    cell = min(MAX_CELL, (grid_width + GRID_GAP) / columns - GRID_GAP)
    year_rows = [
        {"type": "row", "gap": ROW_GAP, "children": [
            {"type": "text", "text": str(year), "width": YEAR_LABEL, "size": 13, "weight": "bold",
             "color": MUTED, "valign": "middle"},
            {"type": "grid", "rows": 7, "cell": cell, "gap": GRID_GAP, "cell_radius": 2,
             "align": "start", "cells": cells},
        ]}
        for year, cells in years.items()
    ]
    return {
        "width": WIDTH,
        "scale": 2,
        "background": BACKGROUND,
        "root": {
            "type": "column", "padding": 16, "gap": 12,
            "children": [
                {"type": "box", "fill": PANEL, "radius": 14, "padding": 14, "child": {
                    "type": "column", "gap": 14,
                    "children": [
                        {"type": "row", "gap": 14, "height": 140, "children": [
                            {"type": "box", "flex": 1, "fill": TILE, "radius": 10, "child": _centered(
                                {"type": "text", "text": "WEEK", "size": 14, "weight": "bold",
                                 "color": MUTED, "align": "center"},
                                {"type": "text", "text": str(week), "size": 56, "weight": "bold",
                                 "align": "center", "line_height": 1.1},
                            )},
                            {"type": "box", "flex": 2, "fill": TILE, "radius": 10, "child": _centered(
                                {"type": "text", "text": f"{today:%A}", "size": 40, "weight": "bold",
                                 "align": "center", "line_height": 1.2},
                                {"type": "text", "text": f"{today.day} {today:%B %Y}", "size": 20,
                                 "color": MUTED, "align": "center"},
                            )},
                        ]},
                        {"type": "progress", "height": 40, "radius": 8, "value": progress,
                         "color": ACCENT, "track": TRACK, "size": 17, "weight": "bold",
                         "label": f"{progress:.0%} of the week"},
                    ],
                }},
                {"type": "box", "fill": PANEL, "radius": 14, "padding": [16, 14], "child": {
                    "type": "column", "gap": 10,
                    "children": [
                        {"type": "text", "text": left_label(today, first, last), "size": 18,
                         "weight": "medium", "align": "center"},
                        *year_rows,
                    ],
                }},
            ],
        },
    }


class Weekcard(commands.Cog):
    """A week-at-a-glance image: week number, date, week progress and a day grid counting down to
    a configurable date. Rendered by the Canvas cog; also offered to Morning as a section."""

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(self, identifier=749453674326, force_registration=True)
        self.config.register_global(start=None, end=None)  # ISO dates; None = this calendar year

    async def red_delete_data_for_user(self, **kwargs) -> None:
        return

    async def _timezone(self) -> ZoneInfo:
        """The owner's timezone from the Profile cog; UTC if it isn't loaded."""
        profile = self.bot.get_cog("Profile")
        return await profile.timezone() if profile is not None else ZoneInfo("UTC")

    async def card(self, now: datetime) -> Optional[discord.File]:
        """The card for `now` as a discord.File, or None if the Canvas cog isn't loaded."""
        canvas = self.bot.get_cog("Canvas")
        if canvas is None:
            return None
        settings = await self.config.all()
        first, last = resolve_range(now.date(), settings["start"], settings["end"])
        return await canvas.render_file(build_spec(now, first, last), f"week-{now:%G-W%V}.png")

    # ---- Morning section ----------------------------------------------------------------------

    def morning_sections(self) -> List[Dict[str, Any]]:
        return [{
            "key": "weekcard",
            "order": 10,
            "description": "week number, date, week progress, days left",
            "render": self.render_morning,
        }]

    async def render_morning(self, now: datetime) -> Optional[Dict[str, Any]]:
        file = await self.card(now)
        return {"files": [file]} if file else None

    # ---- commands -----------------------------------------------------------------------------

    @commands.group(name="weekcard", invoke_without_command=True)
    async def weekcard(self, ctx: commands.Context) -> None:
        """Show this week's card."""
        now = datetime.now(await self._timezone())
        async with ctx.typing():
            file = await self.card(now)
        if file is None:
            await ctx.send("The Canvas cog isn't loaded, so I can't draw the card.")
            return
        await ctx.send(file=file)

    async def _set_end(self, ctx: commands.Context, which: str, text: str) -> None:
        settings = await self.config.all()
        if text.lower() == "reset":
            settings[which] = None
        else:
            try:
                settings[which] = parse_date(text, end=which == "end").isoformat()
            except ValueError as e:
                await ctx.send(str(e))
                return
        today = datetime.now(await self._timezone()).date()
        first, last = resolve_range(today, settings["start"], settings["end"])
        if first > last:
            await ctx.send(f"The range would start ({first}) after it ends ({last}).")
            return
        if last.year - first.year >= MAX_YEARS:
            await ctx.send(f"The range can span at most {MAX_YEARS} calendar years.")
            return
        await self.config.set_raw(which, value=settings[which])
        await ctx.send(f"Counting days from **{first:%d %B %Y}** to **{last:%d %B %Y}**.")

    @weekcard.command(name="until")
    @commands.is_owner()
    async def weekcard_until(self, ctx: commands.Context, end: str) -> None:
        """Count down to a date: `YYYY`, `YYYY-MM` (end of that month) or `YYYY-MM-DD`.
        `reset` = end of the current year."""
        await self._set_end(ctx, "end", end)

    @weekcard.command(name="from")
    @commands.is_owner()
    async def weekcard_from(self, ctx: commands.Context, start: str) -> None:
        """Start the grid at a date: `YYYY`, `YYYY-MM` or `YYYY-MM-DD`.
        `reset` = start of the current year."""
        await self._set_end(ctx, "start", start)
