"""Her voice. Tonight: canned conversational replies (no key needed).

When LLM_API_KEY + LLM_MODEL are set, route here through one tool-calling
model instead. Tools feed facts; she formats short human texts. Money never
moves from this module — confirms are checked in main.py.
"""
from __future__ import annotations

PILOTS_INTRO = (
    "hey, i'm pool. i help you copy investor-style portfolios in tokenized stocks on bnb chain. "
    "right now you can copy three: pelosi-style (from public disclosures, delayed), "
    "buffett-style (from 13f filings, delayed), and ai-chips. "
    "which one do you want? and with how much? small is fine, like twenty bucks."
)

DISCLAIMER = (
    "quick note since it's money: i'm not an investment advisor. filings are delayed "
    "and tokenized prices can drift from the us price when the market's shut. "
    "i'll always show you the numbers and you decide."
)


def reply(text: str, phone: str) -> list[str]:
    t = text.strip().lower()
    if any(w in t for w in ("pilot", "who can i copy", "copy", "pelosi", "buffett", "chip", "people", "options")):
        return [PILOTS_INTRO, DISCLAIMER]
    if any(w in t for w in ("portfolio", "how am i", "status", "position", "doing")):
        return ["nothing enrolled yet on this number — pick a pilot first and we'll set up your copy. which one catches your eye?"]
    if any(w in t for w in ("news", "moving", "trend", "nvda", "research", "happening")):
        return ["research goes live with the news worker midweek — for tonight i can show you live pilot prices. which pilot?"]
    if t in ("hi", "hey", "hello", "yo", "start"):
        return [PILOTS_INTRO]
    return [
        "got you. talk to me normally — like \"put me on the pelosi one with twenty bucks\" or \"how's my portfolio?\". "
        "tonight i can show pilots and live prices; copying goes live wednesday. who do you want to copy?"
    ]
