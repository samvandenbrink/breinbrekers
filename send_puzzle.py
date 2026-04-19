#!/usr/bin/env python3
"""Generate a Breinbreker puzzle and email it.

Reads SMTP configuration from environment variables:
    SMTP_HOST, SMTP_PORT (default 587), SMTP_USER, SMTP_PASSWORD,
    EMAIL_FROM (defaults to SMTP_USER), EMAIL_TO
"""

import io
import os
import smtplib
import sys
from contextlib import redirect_stdout
from email.message import EmailMessage

from breinbreker import display, generate


def _render(puzzle, solution) -> str:
    buf = io.StringIO()
    with redirect_stdout(buf):
        display(puzzle, solution)
    return buf.getvalue()


def build_email(puzzle, solution, sender: str, recipient: str) -> EmailMessage:
    puzzle_text = _render(puzzle, solution=None)
    full_text = _render(puzzle, solution=solution)

    msg = EmailMessage()
    msg["Subject"] = "Breinbreker van de week"
    msg["From"] = sender
    msg["To"] = recipient

    plain = (
        "Beste opa,\n\n"
        "Hier is je breinbreker voor deze week. Veel plezier met puzzelen!\n\n"
        f"{puzzle_text}\n\n\n"
        "--- De oplossing staat hieronder, alleen lezen als je klaar bent! ---\n\n\n"
        f"{full_text}"
    )
    msg.set_content(plain)

    html = (
        '<!DOCTYPE html><html><body style="font-family: sans-serif;">'
        "<p>Beste opa,</p>"
        "<p>Hier is je breinbreker voor deze week. Veel plezier met puzzelen!</p>"
        '<pre style="font-family: \'Courier New\', monospace; '
        'font-size: 16px; line-height: 1.4;">'
        f"{puzzle_text}</pre>"
        "<br><br><hr>"
        '<p style="color: #888;">De oplossing staat hieronder &mdash; '
        "alleen lezen als je klaar bent!</p><br><br>"
        '<pre style="font-family: \'Courier New\', monospace; '
        'font-size: 16px; line-height: 1.4;">'
        f"{full_text}</pre>"
        "</body></html>"
    )
    msg.add_alternative(html, subtype="html")
    return msg


def main() -> int:
    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ["SMTP_USER"]
    password = os.environ["SMTP_PASSWORD"]
    sender = os.environ.get("EMAIL_FROM", user)
    recipient = os.environ["EMAIL_TO"]

    [(puzzle, solution)] = generate(n=1)
    msg = build_email(puzzle, solution, sender, recipient)

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(user, password)
        server.send_message(msg)

    print(f"Sent puzzle to {recipient}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
