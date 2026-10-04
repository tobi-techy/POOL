"""Conversation state machine: first text -> browsing -> picked -> quoted -> copying -> running.

The LLM (when keyed) voices these moves; the state machine owns them. Plain-English
in, explicit stage out. Money moves only on a consumed confirm token (quote.py).
"""
from __future__ import annotations

from app import pilots
from app.config import settings
from app.copyengine import record_copy, start_copy_texts
from app.db import get_user, set_user, user_copies
from app.quote import arm_confirm, build_quote, confirm_text, parse_amount, take_confirm

YES = {"yes", "yep", "yeah", "confirm", "do it", "let's go", "lets go", "copy"}
NO = {"no", "nope", "cancel", "stop", "skip", "not now"}


async def handle(db_path: str, phone: str, text: str) -> list[str]:
    u = get_user(db_path, phone)
    t = text.strip().lower()

    if u["stage"] == "new":
        set_user(db_path, phone, stage="browsing")
        return [pilots.intro_text(), _not_advice()]

    if _is(t, {"status", "portfolio", "how am i", "position", "doing", "holdings"}):
        return await _status(db_path, phone)

    if _is(t, {"stop", "pause"}):
        return ["paused — nothing will rebalance until you say go again. your funds stay where they are."]
    if "cash out" in t or "withdraw" in t:
        return ["cash-out starts with a fresh signature from your wallet (it expires in 10 min). "
                "say the word and i'll prepare it — i won't move anything until you sign."]

    if _is(t, {"news", "moving", "trend", "research", "happening", "earnings"}):
        return ["research worker goes live midweek — for now, which pilot do you want the latest picture on?"]

    pid = pilots.find_pilot(t)
    if u["stage"] == "confirm_pending":
        if t in YES or "yes" in t:
            return await _confirm_yes(db_path, phone)
        if t in NO:
            set_user(db_path, phone, stage="browsing")
            return ["no worries, nothing moved. want a different pilot, or a different amount?"]
        if pid:
            set_user(db_path, phone, stage="picked", picked_pilot=pid, pending_usd=0)
            return [pilots.explain_text(pid), "with how much?"]
        return ["i'm holding that quote — reply YES to copy, or NO to drop it."]

    if pid and u["stage"] in ("browsing", "picked"):
        set_user(db_path, phone, stage="picked", picked_pilot=pid, pending_usd=0)
        if u["stage"] == "picked" and u["picked_pilot"] == pid:
            return [pilots.explain_text(pid), "with how much?"]
        return [pilots.explain_text(pid), "with how much?"]

    if u["stage"] == "picked":
        if t in YES or "yes" in t:
            return ["you're on the list — i'll text you the second prices are back and we'll quote it properly. "
                    "want to hear how the copy works while you wait?"]
        if t in NO:
            set_user(db_path, phone, stage="browsing")
            return ["no worries. pelosi-style, buffett-style, or ai-chips — which one?"]
        amt = parse_amount(t)
        if amt is None:
            return ["how much do you want to start with? just say like twenty bucks."]
        if amt > settings.max_copy_usd:
            return [f"demo cap is ${settings.max_copy_usd:.0f} per copy — how about ${settings.max_copy_usd:.0f} to start?"]
        set_user(db_path, phone, pending_usd=amt)
        q = await build_quote(u["picked_pilot"], amt, db_path)
        if q.ok:
            arm_confirm(db_path, phone, q)
            set_user(db_path, phone, stage="confirm_pending")
        return confirm_text(q)

    if u["stage"] == "browsing":
        amt = parse_amount(t)
        if amt and u["picked_pilot"]:
            set_user(db_path, phone, stage="picked")
            return await handle(db_path, phone, text)
        return ["pick one and i'll walk you through it — pelosi-style, buffett-style, or ai-chips?"]

    copies = user_copies(db_path, phone)
    if copies:
        set_user(db_path, phone, stage="running")
        return await _status(db_path, phone)
    set_user(db_path, phone, stage="browsing")
    return [pilots.intro_text()]


async def _confirm_yes(db_path: str, phone: str) -> list[str]:
    c = take_confirm(db_path, phone)
    if not c:
        set_user(db_path, phone, stage="browsing")
        return ["that quote expired (they only live 10 min) — tell me the pilot and amount again and i'll re-quote."]
    set_user(db_path, phone, stage="running")
    record_copy(db_path, phone, c["pilot_id"], "quoted")
    return start_copy_texts(phone, c["pilot_id"], c["notional_usd"])


async def _status(db_path: str, phone: str) -> list[str]:
    copies = user_copies(db_path, phone)
    if not copies:
        return ["nothing enrolled yet on this number — pick a pilot first and we'll set it up. which one catches your eye?"]
    c = copies[0]
    p = pilots.PILOTS.get(c["pilot_id"], {"label": c["pilot_id"]})
    if c["portfolio_id"]:
        return [f"you're copying {p['label']} — portfolio {c['portfolio_id'][:8]}…, status {c['status']}. "
                "live values land with the copy engine Wednesday; your next rebalance follows the pilot's schedule."]
    return [f"you're queued on {p['label']} (status: {c['status']}) — enrollment opens wednesday, i'll text you. "
            "say STOP to drop the queue."]


def _is(t: str, keys: set[str]) -> bool:
    return any(k in t for k in keys)


def _not_advice() -> str:
    return ("quick note since it's money: i'm not an investment advisor. filings are delayed "
            "and tokenized prices can drift when the us market's shut. i'll show numbers, you decide.")
