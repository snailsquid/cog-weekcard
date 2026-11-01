import calendar
import re
from datetime import date, datetime, time, timedelta
from typing import Any, Dict, List, Optional
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
HIGHLIGHT = "#3fb950"

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


def week_progress(now: datetime) -> float:
    """Fraction of the ISO week (Monday 00:00 to Monday 00:00) that has passed."""
    start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    return min(1.0, (now - start) / timedelta(days=7))


def done_color(day: date) -> str:
    """Colour of a finished day. Later: vary the alpha (`#26a641` + `"80"`) with how many tasks
    were finished that day; Canvas blends translucent cells."""
    return DAY_DONE


def year_cells(year: int, first: date, last: date, today: date) -> List[Any]:
    """One ISO year, a cell per week. Weeks entirely outside [first, last] are None (invisible);
    finished weeks green, the current week outlined, the rest dim."""
    cells: List[Any] = []
    for week in range(1, date(year, 12, 28).isocalendar()[1] + 1):
        monday = date.fromisocalendar(year, week, 1)
        sunday = monday + timedelta(days=6)
        if sunday < first or monday > last:
            cells.append(None)
        elif sunday < today:
            cells.append(done_color(sunday))
        elif monday <= today:
            cells.append({"fill": DAY_LEFT, "border": TODAY_BORDER})
        else:
            cells.append(DAY_LEFT)
    return cells


def week_number(today: date, first: Optional[date]) -> int:
    """Week of `today` counted from the week containing `first` (week 1); the ISO week if there
    is no `first` or it is still ahead."""
    if first is None or today < first:
        return today.isocalendar()[1]
    return (today - (first - timedelta(days=first.weekday()))).days // 7 + 1


def _centered(*lines: Dict[str, Any]) -> Dict[str, Any]:
    return {"type": "column", "children": [{"type": "spacer"}, *lines, {"type": "spacer"}]}


def _card(*panels: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "width": WIDTH,
        "scale": 2,
        "background": BACKGROUND,
        "root": {"type": "column", "padding": 16, "gap": 12, "children": list(panels)},
    }


def build_life_spec(now: datetime, week: int) -> Dict[str, Any]:
    """Life card at `now` (timezone-aware): week number, day and date, week progress."""
    today = now.date()
    progress = week_progress(now)
    return _card({"type": "box", "fill": PANEL, "radius": 14, "padding": 14, "child": {
        "type": "column", "gap": 14,
        "children": [
            {"type": "row", "gap": 14, "height": 140, "children": [
                {"type": "box", "flex": 1, "fill": TILE, "radius": 10, "child": _centered(
                    {"type": "text", "text": "WEEK", "size": 14, "weight": "bold",
                     "color": MUTED, "align": "center"},
                    {"type": "text", "text": str(week), "size": 56,
                     "weight": "bold", "align": "center", "line_height": 1.1},
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
    }})


def range_progress(now: datetime, first: date, last: date) -> float:
    """Fraction of [first 00:00, the day after last 00:00) that has passed at `now`
    (timezone-aware), so it moves through the day."""
    start = datetime.combine(first, time(), now.tzinfo)
    end = datetime.combine(last + timedelta(days=1), time(), now.tzinfo)
    return min(1.0, max(0.0, (now - start) / (end - start)))


def _stat(value: str, label: str) -> Dict[str, Any]:
    return {"type": "box", "flex": 1, "fill": TILE, "radius": 8, "padding": [0, 14], "child": {
        "type": "row", "children": [
            {"type": "text", "text": value, "size": 20, "weight": "bold", "valign": "middle"},
            {"type": "text", "text": label, "size": 13, "color": MUTED, "align": "right",
             "valign": "middle"},
        ],
    }}


def build_college_spec(now: datetime, first: date, last: date) -> Dict[str, Any]:
    """College card at `now` (timezone-aware) for [first, last]: the percentage finished as the
    headline, days done/left, and a week grid with one row per ISO year."""
    today = now.date()
    progress = range_progress(now, first, last)
    done = min(max((today - first).days, 0), (last - first).days + 1)
    left = max((last - today).days, 0) if today >= first else (last - first).days
    weeks, days = divmod(left, 7)
    years = {
        y: year_cells(y, first, last, today)
        for y in range(first.isocalendar()[0], last.isocalendar()[0] + 1)
    }
    columns = max(len(cells) for cells in years.values())
    grid_width = GRID_WIDTH - YEAR_LABEL - ROW_GAP
    cell = min(MAX_CELL, (grid_width + GRID_GAP) / columns - GRID_GAP)
    year_rows = [
        {"type": "row", "gap": ROW_GAP, "children": [
            {"type": "text", "text": str(year), "width": YEAR_LABEL, "size": 13, "weight": "bold",
             "color": MUTED, "valign": "middle"},
            {"type": "grid", "rows": 1, "cell": cell, "gap": GRID_GAP, "cell_radius": 2,
             "align": "start", "cells": cells},
        ]}
        for year, cells in years.items()
    ]
    return _card(
        {"type": "box", "fill": PANEL, "radius": 14, "padding": [16, 14, 14, 14], "child": {
            "type": "column", "gap": 12,
            "children": [
                {"type": "row", "children": [
                    {"type": "text", "text": "COLLEGE", "size": 14, "weight": "bold",
                     "color": MUTED},
                    {"type": "text", "text": f"{first:%b %Y} – {last:%b %Y}", "size": 14,
                     "color": MUTED, "align": "right"},
                ]},
                {"type": "row", "gap": 12, "height": 140, "children": [
                    {"type": "box", "flex": 3, "fill": TILE, "radius": 10, "child": _centered(
                        {"type": "text", "text": f"{progress * 100:.2f}%", "size": 72,
                         "weight": "bold", "color": HIGHLIGHT, "align": "center",
                         "line_height": 1.05},
                        {"type": "text", "text": "of college finished", "size": 16,
                         "color": MUTED, "align": "center"},
                    )},
                    {"type": "column", "flex": 2, "gap": 8, "children": [
                        _stat(f"{done:,}", "days done"),
                        _stat(f"{left:,}", "days left"),
                        _stat(f"{weeks}w {days}d", f"until {last.day} {last:%b %Y}"),
                    ]},
                ]},
                {"type": "progress", "height": 12, "radius": 6, "value": progress,
                 "color": DAY_DONE, "track": TRACK},
            ],
        }},
        {"type": "box", "fill": PANEL, "radius": 14, "padding": [14, 14], "child": {
            "type": "column", "gap": 8, "children": year_rows,
        }},
    )


class Weekcard(commands.Cog):
    """Two cards, rendered by the Canvas cog and offered to Morning as sections: `life` (week
    number, date, week progress) and `college` (% finished and a countdown day grid)."""

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(self, identifier=749453674326, force_registration=True)
        # ISO dates; the college card is skipped until both are set.
        self.config.register_global(college_start=None, college_end=None)

    async def red_delete_data_for_user(self, **kwargs) -> None:
        return

    async def _timezone(self) -> ZoneInfo:
        """The owner's timezone from the Profile cog; UTC if it isn't loaded."""
        profile = self.bot.get_cog("Profile")
        return await profile.timezone() if profile is not None else ZoneInfo("UTC")

    async def _render(self, spec: Dict[str, Any], filename: str) -> Optional[discord.File]:
        canvas = self.bot.get_cog("Canvas")
        return await canvas.render_file(spec, filename) if canvas is not None else None

    async def life_card(self, now: datetime) -> Optional[discord.File]:
        """The life card for `now`, or None if the Canvas cog isn't loaded."""
        span = await self.college_range()
        week = week_number(now.date(), span[0] if span else None)
        return await self._render(build_life_spec(now, week), f"life-{now:%Y-%m-%d}.png")

    async def college_range(self) -> Optional[tuple]:
        """(first, last) dates of college, or None if not set."""
        settings = await self.config.all()
        if not (settings["college_start"] and settings["college_end"]):
            return None
        return date.fromisoformat(settings["college_start"]), date.fromisoformat(settings["college_end"])

    async def college_card(self, now: datetime) -> Optional[discord.File]:
        """The college card for `now`, or None if Canvas isn't loaded or the range isn't set."""
        span = await self.college_range()
        if span is None:
            return None
        return await self._render(build_college_spec(now, *span), f"college-{now:%Y-%m-%d}.png")

    # ---- Morning sections ---------------------------------------------------------------------

    def morning_sections(self) -> List[Dict[str, Any]]:
        return [
            {"key": "life", "order": 10, "description": "week number (from college start), date, week progress",
             "render": self._morning(self.life_card)},
            {"key": "college", "order": 11, "description": "% of college finished, days left",
             "render": self._morning(self.college_card)},
        ]

    @staticmethod
    def _morning(card):
        async def render(now: datetime) -> Optional[Dict[str, Any]]:
            file = await card(now)
            return {"files": [file]} if file else None

        return render

    # ---- commands -----------------------------------------------------------------------------

    async def _send(self, ctx: commands.Context, card) -> None:
        now = datetime.now(await self._timezone())
        async with ctx.typing():
            file = await card(now)
        if file is not None:
            await ctx.send(file=file)
        elif self.bot.get_cog("Canvas") is None:
            await ctx.send("The Canvas cog isn't loaded, so I can't draw the card.")
        else:
            p = ctx.clean_prefix
            await ctx.send(f"Set the college dates first: `{p}weekcard college from <date>` and "
                           f"`{p}weekcard college until <date>`.")

    @commands.group(name="weekcard", invoke_without_command=True)
    async def weekcard(self, ctx: commands.Context) -> None:
        """Show the life card (week number, date, week progress)."""
        await self._send(ctx, self.life_card)

    @weekcard.group(name="college", invoke_without_command=True)
    async def weekcard_college(self, ctx: commands.Context) -> None:
        """Show the college card (% finished, days left)."""
        await self._send(ctx, self.college_card)

    async def _set_college(self, ctx: commands.Context, which: str, text: str) -> None:
        settings = await self.config.all()
        try:
            settings[which] = parse_date(text, end=which == "college_end").isoformat()
        except ValueError as e:
            await ctx.send(str(e))
            return
        start, end = settings["college_start"], settings["college_end"]
        if start and end:
            first, last = date.fromisoformat(start), date.fromisoformat(end)
            if first > last:
                await ctx.send(f"College would start ({first}) after it ends ({last}).")
                return
            if last.year - first.year >= MAX_YEARS:
                await ctx.send(f"The range can span at most {MAX_YEARS} calendar years.")
                return
        await self.config.set_raw(which, value=settings[which])
        shown = [f"**{date.fromisoformat(d):%d %B %Y}**" if d else "*not set*" for d in (start, end)]
        await ctx.send(f"College: {shown[0]} to {shown[1]}.")

    @weekcard_college.command(name="from")
    @commands.is_owner()
    async def college_from(self, ctx: commands.Context, start: str) -> None:
        """When college started: `YYYY`, `YYYY-MM` (start of that month) or `YYYY-MM-DD`."""
        await self._set_college(ctx, "college_start", start)

    @weekcard_college.command(name="until")
    @commands.is_owner()
    async def college_until(self, ctx: commands.Context, end: str) -> None:
        """When college ends: `YYYY`, `YYYY-MM` (end of that month) or `YYYY-MM-DD`."""
        await self._set_college(ctx, "college_end", end)
