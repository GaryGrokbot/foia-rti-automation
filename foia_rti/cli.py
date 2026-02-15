"""
CLI interface for the FOIA/RTI Automation System.

Commands:
    generate  — Generate a public records request
    file      — File a request via email or batch
    track     — View and update tracked requests
    appeal    — Generate an appeal letter
    stats     — Show request statistics and alerts
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import click

from foia_rti import __version__


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------

@click.group()
@click.version_option(version=__version__, prog_name="foia-rti")
@click.option("--db", default="sqlite:///foia_tracker.db", help="Database URL for the tracker.")
@click.pass_context
def cli(ctx: click.Context, db: str) -> None:
    """FOIA/RTI Automation System — generate, file, track, and appeal public records requests."""
    ctx.ensure_object(dict)
    ctx.obj["db_url"] = db


# ---------------------------------------------------------------------------
# generate
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--jurisdiction", "-j", required=True,
              type=click.Choice(["us-federal", "us-state", "india", "uk", "eu"], case_sensitive=False),
              help="Legal jurisdiction.")
@click.option("--agency", "-a", required=True, help="Target agency (e.g., USDA-APHIS, EPA, AWBI).")
@click.option("--topic", "-t", required=True, help="Topic or subject of the request.")
@click.option("--state", "-s", default=None, help="US state abbreviation (for us-state jurisdiction).")
@click.option("--template", default=None, help="Pre-built template ID to use.")
@click.option("--records", "-r", multiple=True, help="Specific records to request (repeatable).")
@click.option("--keywords", "-k", multiple=True, help="Search keywords (repeatable).")
@click.option("--facilities", "-f", multiple=True, help="Facility names (repeatable).")
@click.option("--from-date", default=None, help="Start of date range (YYYY-MM-DD).")
@click.option("--to-date", default=None, help="End of date range (YYYY-MM-DD).")
@click.option("--name", default="Open Paws Research", help="Requester name.")
@click.option("--org", default="Open Paws", help="Requester organization.")
@click.option("--email", default="", help="Requester email.")
@click.option("--no-fee-waiver", is_flag=True, help="Do not request a fee waiver.")
@click.option("--expedited", is_flag=True, help="Request expedited processing (US Federal only).")
@click.option("--output", "-o", default=None, help="Output file path (default: stdout).")
@click.option("--json-output", is_flag=True, help="Output as JSON instead of plain text.")
@click.option("--language", default="english", help="Language for India RTI (english/hindi).")
@click.pass_context
def generate(
    ctx: click.Context,
    jurisdiction: str,
    agency: str,
    topic: str,
    state: Optional[str],
    template: Optional[str],
    records: tuple[str, ...],
    keywords: tuple[str, ...],
    facilities: tuple[str, ...],
    from_date: Optional[str],
    to_date: Optional[str],
    name: str,
    org: str,
    email: str,
    no_fee_waiver: bool,
    expedited: bool,
    output: Optional[str],
    json_output: bool,
    language: str,
) -> None:
    """Generate a public records request."""
    from foia_rti.generators.generator_base import RequestContext
    from foia_rti.generators.us_federal import USFederalGenerator
    from foia_rti.generators.us_state import USStateGenerator
    from foia_rti.generators.india_rti import IndiaRTIGenerator
    from foia_rti.generators.uk_foi import UKFOIGenerator
    from foia_rti.generators.eu_requests import EURequestGenerator

    # Parse dates
    date_start = _parse_date(from_date) if from_date else None
    date_end = _parse_date(to_date) if to_date else None

    # Determine jurisdiction string for context
    juris_str = jurisdiction.upper().replace("-", "_")
    if jurisdiction.lower() == "us-federal":
        juris_str = "US-Federal"
    elif jurisdiction.lower() == "us-state":
        juris_str = state.upper() if state else "US-State"
    elif jurisdiction.lower() == "india":
        juris_str = "India"
    elif jurisdiction.lower() == "uk":
        juris_str = "UK"
    elif jurisdiction.lower() == "eu":
        juris_str = "EU"

    context = RequestContext(
        agency=agency,
        topic=topic,
        jurisdiction=juris_str,
        requester_name=name,
        requester_organization=org,
        requester_email=email,
        date_range_start=date_start,
        date_range_end=date_end,
        specific_records=list(records),
        keywords=list(keywords),
        facilities=list(facilities),
        fee_waiver=not no_fee_waiver,
        expedited_processing=expedited,
        template_id=template,
    )

    # Select generator
    gen_map = {
        "us-federal": USFederalGenerator,
        "us-state": USStateGenerator,
        "india": IndiaRTIGenerator,
        "uk": UKFOIGenerator,
        "eu": EURequestGenerator,
    }

    generator = gen_map[jurisdiction.lower()]()

    if jurisdiction.lower() == "india":
        result = generator.generate(context, language=language)
    else:
        result = generator.generate(context)

    # Output
    if json_output:
        output_text = json.dumps(result.to_dict(), indent=2, ensure_ascii=False)
    else:
        output_text = result.text

    if output:
        Path(output).write_text(output_text, encoding="utf-8")
        click.echo(f"Request written to {output}")
    else:
        click.echo(output_text)

    # Show metadata
    if not json_output:
        click.echo("\n--- Request Metadata ---")
        click.echo(f"Jurisdiction: {result.jurisdiction}")
        click.echo(f"Legal Basis: {result.legal_basis}")
        click.echo(f"Estimated Deadline: {result.estimated_deadline_days} days")
        click.echo(f"Filing Method: {result.filing_method}")
        click.echo(f"Fee Notes: {result.fee_notes}")


# ---------------------------------------------------------------------------
# file
# ---------------------------------------------------------------------------

@cli.command(name="file")
@click.option("--request-file", "-f", required=True, help="Path to generated request text file.")
@click.option("--agency-email", "-e", required=True, help="Agency FOIA email address.")
@click.option("--subject", "-s", default=None, help="Email subject line.")
@click.option("--smtp-host", default="smtp.gmail.com", help="SMTP server host.")
@click.option("--smtp-port", default=587, type=int, help="SMTP server port.")
@click.option("--smtp-user", default=None, help="SMTP username.")
@click.option("--smtp-pass", default=None, help="SMTP password.")
@click.option("--from-address", default=None, help="Sender email address.")
@click.option("--dry-run", is_flag=True, help="Preview without sending.")
@click.option("--track/--no-track", default=True, help="Track in database.")
@click.pass_context
def file_request(
    ctx: click.Context,
    request_file: str,
    agency_email: str,
    subject: Optional[str],
    smtp_host: str,
    smtp_port: int,
    smtp_user: Optional[str],
    smtp_pass: Optional[str],
    from_address: Optional[str],
    dry_run: bool,
    track: bool,
) -> None:
    """File a request via email."""
    from foia_rti.filers.email_filer import EmailFiler, EmailConfig, EmailMessage

    request_text = Path(request_file).read_text(encoding="utf-8")

    config = EmailConfig(
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        username=smtp_user or "",
        password=smtp_pass or "",
        from_address=from_address or smtp_user or "",
    )

    filer = EmailFiler(config)
    msg = EmailMessage(
        to=agency_email,
        subject=subject or "Public Records Request",
        body_text=request_text,
        from_address=config.from_address,
        from_name=config.from_name,
    )

    result = filer.send(msg, dry_run=dry_run)
    click.echo(json.dumps(result, indent=2))

    if track and not dry_run and result.get("status") == "sent":
        from foia_rti.tracker.tracker import TrackerDB, RequestStatus
        db = TrackerDB(ctx.obj["db_url"])
        req = db.create_request(
            agency=agency_email,
            jurisdiction="unknown",
            topic=subject or "Public Records Request",
            request_text=request_text,
            date_filed=date.today(),
            status=RequestStatus.FILED,
            filing_method="email",
        )
        click.echo(f"Tracked as request #{req.id}")


# ---------------------------------------------------------------------------
# track
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--list", "list_all", is_flag=True, help="List all tracked requests.")
@click.option("--overdue", is_flag=True, help="Show only overdue requests.")
@click.option("--id", "request_id", type=int, default=None, help="Show details for a specific request.")
@click.option("--update-status", type=str, default=None,
              help="Update status (filed, acknowledged, complete, denied, etc.).")
@click.option("--add-note", type=str, default=None, help="Add a note to a request.")
@click.option("--jurisdiction", "-j", default=None, help="Filter by jurisdiction.")
@click.option("--agency", "-a", default=None, help="Filter by agency name.")
@click.pass_context
def track(
    ctx: click.Context,
    list_all: bool,
    overdue: bool,
    request_id: Optional[int],
    update_status: Optional[str],
    add_note: Optional[str],
    jurisdiction: Optional[str],
    agency: Optional[str],
) -> None:
    """View and manage tracked FOIA/RTI requests."""
    from foia_rti.tracker.tracker import TrackerDB, RequestStatus

    db = TrackerDB(ctx.obj["db_url"])

    if request_id and update_status:
        try:
            status = RequestStatus(update_status)
        except ValueError:
            click.echo(f"Invalid status. Options: {[s.value for s in RequestStatus]}")
            return
        req = db.update_status(request_id, status)
        if req:
            click.echo(f"Updated request #{req.id} to status: {req.status.value}")
        else:
            click.echo(f"Request #{request_id} not found.")
        return

    if request_id and add_note:
        req = db.add_note(request_id, add_note)
        if req:
            click.echo(f"Note added to request #{req.id}.")
        else:
            click.echo(f"Request #{request_id} not found.")
        return

    if request_id:
        req = db.get_request(request_id)
        if req:
            click.echo(f"Request #{req.id}")
            click.echo(f"  Agency:       {req.agency}")
            click.echo(f"  Jurisdiction: {req.jurisdiction}")
            click.echo(f"  Topic:        {req.topic}")
            click.echo(f"  Status:       {req.status.value}")
            click.echo(f"  Date Filed:   {req.date_filed}")
            click.echo(f"  Deadline:     {req.deadline}")
            click.echo(f"  Overdue:      {req.is_overdue()}")
            days = req.days_until_deadline()
            if days is not None:
                click.echo(f"  Days Left:    {days}")
            if req.docs_received:
                click.echo(f"  Docs Received: {req.docs_received}")
            if req.notes:
                click.echo(f"  Notes:\n{req.notes}")
        else:
            click.echo(f"Request #{request_id} not found.")
        return

    if overdue:
        requests = db.get_overdue()
        if not requests:
            click.echo("No overdue requests.")
            return
        click.echo(f"Overdue requests ({len(requests)}):")
        for req in requests:
            days = req.days_until_deadline()
            click.echo(
                f"  #{req.id} | {req.agency[:40]:40s} | "
                f"{req.status.value:15s} | {abs(days or 0)} days overdue"
            )
        return

    # Default: list all
    requests = db.list_requests(jurisdiction=jurisdiction, agency=agency)
    if not requests:
        click.echo("No tracked requests.")
        return

    click.echo(f"Tracked requests ({len(requests)}):")
    for req in requests:
        days = req.days_until_deadline()
        days_str = f"{days}d" if days is not None else "N/A"
        click.echo(
            f"  #{req.id:4d} | {req.jurisdiction:15s} | {req.agency[:35]:35s} | "
            f"{req.status.value:15s} | deadline: {days_str}"
        )


# ---------------------------------------------------------------------------
# appeal
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--id", "request_id", type=int, required=True, help="Request ID to appeal.")
@click.option("--grounds", "-g", default="", help="Specific grounds for the appeal.")
@click.option("--name", default="Open Paws Research", help="Requester name.")
@click.option("--org", default="Open Paws", help="Organization.")
@click.option("--email", default="", help="Contact email.")
@click.option("--output", "-o", default=None, help="Output file path.")
@click.pass_context
def appeal(
    ctx: click.Context,
    request_id: int,
    grounds: str,
    name: str,
    org: str,
    email: str,
    output: Optional[str],
) -> None:
    """Generate an appeal letter for a denied or overdue request."""
    from foia_rti.tracker.tracker import TrackerDB
    from foia_rti.tracker.appeals import AppealGenerator

    db = TrackerDB(ctx.obj["db_url"])
    req = db.get_request(request_id)
    if req is None:
        click.echo(f"Request #{request_id} not found.")
        return

    generator = AppealGenerator()

    if req.is_overdue() and not grounds:
        text = generator.generate_appeal_for_nonresponse(
            req, requester_name=name, requester_org=org, requester_email=email
        )
    else:
        text = generator.generate_appeal(
            req, grounds=grounds, requester_name=name,
            requester_org=org, requester_email=email
        )

    if output:
        Path(output).write_text(text, encoding="utf-8")
        click.echo(f"Appeal written to {output}")
    else:
        click.echo(text)


# ---------------------------------------------------------------------------
# stats
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--alerts", is_flag=True, help="Show active alerts.")
@click.option("--within-days", default=7, type=int, help="Alert threshold in days.")
@click.pass_context
def stats(ctx: click.Context, alerts: bool, within_days: int) -> None:
    """Show request statistics and alerts."""
    from foia_rti.tracker.tracker import TrackerDB
    from foia_rti.tracker.alerts import AlertEngine

    db = TrackerDB(ctx.obj["db_url"])
    stats_data = db.get_stats()

    click.echo("=== FOIA/RTI Tracker Statistics ===")
    click.echo(f"Total requests: {stats_data['total']}")
    click.echo(f"Overdue: {stats_data['overdue']}")
    click.echo("\nBy status:")
    for status, count in stats_data.get("by_status", {}).items():
        click.echo(f"  {status:25s}: {count}")

    if alerts:
        engine = AlertEngine(db)
        all_alerts = engine.check_all()
        if not all_alerts:
            click.echo("\nNo active alerts.")
        else:
            click.echo(f"\n=== Active Alerts ({len(all_alerts)}) ===")
            for alert in all_alerts:
                click.echo(alert.format_text())


# ---------------------------------------------------------------------------
# list-agencies
# ---------------------------------------------------------------------------

@cli.command(name="list-agencies")
@click.option("--jurisdiction", "-j", required=True,
              type=click.Choice(["us-federal", "us-state", "india", "uk", "eu"], case_sensitive=False))
def list_agencies(jurisdiction: str) -> None:
    """List known agencies for a jurisdiction."""
    from foia_rti.generators.us_federal import USFederalGenerator
    from foia_rti.generators.us_state import USStateGenerator
    from foia_rti.generators.india_rti import IndiaRTIGenerator
    from foia_rti.generators.uk_foi import UKFOIGenerator
    from foia_rti.generators.eu_requests import EURequestGenerator

    gen_map = {
        "us-federal": USFederalGenerator,
        "us-state": USStateGenerator,
        "india": IndiaRTIGenerator,
        "uk": UKFOIGenerator,
        "eu": EURequestGenerator,
    }

    generator = gen_map[jurisdiction.lower()]()
    agencies = generator.get_agencies()

    click.echo(f"\nAgencies ({jurisdiction.upper()}):\n")
    for key, details in agencies.items():
        name = details.get("full_name", key)
        email = details.get("email", details.get("foi_email", "N/A"))
        notes = details.get("notes", "")
        click.echo(f"  {key}")
        click.echo(f"    Name:  {name}")
        click.echo(f"    Email: {email}")
        if notes:
            click.echo(f"    Notes: {notes[:100]}")
        click.echo()


# ---------------------------------------------------------------------------
# list-templates
# ---------------------------------------------------------------------------

@cli.command(name="list-templates")
@click.option("--jurisdiction", "-j", required=True,
              type=click.Choice(["us-federal", "india"], case_sensitive=False))
def list_templates(jurisdiction: str) -> None:
    """List pre-built request templates."""
    from foia_rti.generators.us_federal import USFederalGenerator
    from foia_rti.generators.india_rti import IndiaRTIGenerator

    gen_map = {
        "us-federal": USFederalGenerator,
        "india": IndiaRTIGenerator,
    }

    generator = gen_map[jurisdiction.lower()]()
    templates = generator.list_templates()

    if not templates:
        click.echo("No templates found. Ensure template JSON files exist in the templates/ directory.")
        return

    click.echo(f"\nTemplates ({jurisdiction.upper()}):\n")
    for t in templates:
        click.echo(f"  {t['id']}")
        click.echo(f"    {t['name']}")
        if t.get("description"):
            click.echo(f"    {t['description'][:100]}")
        click.echo()


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _parse_date(s: str) -> date:
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        raise click.BadParameter(f"Invalid date format: {s}. Use YYYY-MM-DD.")


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
