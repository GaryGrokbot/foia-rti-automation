# FOIA/RTI Automation System

Automated transparency. Every public record request is free. Every denied request is appealable.

This system generates, files, tracks, and analyzes public records requests across multiple jurisdictions targeting animal agriculture transparency. It produces legally formatted requests with correct statutory citations, agency-specific contact information, fee waiver language, and deadline tracking.

## Supported Jurisdictions

| Jurisdiction | Law | Deadline | Generator |
|---|---|---|---|
| US Federal | FOIA, 5 U.S.C. Section 552 | 20 business days | `USFederalGenerator` |
| US States (12+) | State-specific statutes | Varies (3-20 days) | `USStateGenerator` |
| India | RTI Act 2005 | 30 calendar days | `IndiaRTIGenerator` |
| United Kingdom | FOI Act 2000 / EIR 2004 | 20 working days | `UKFOIGenerator` |
| European Union | Regulation 1049/2001 | 15 working days | `EURequestGenerator` |

## Features

- **Request Generation**: Legally formatted requests with correct citations, fee waiver language, and agency-specific details. 20+ US federal templates and 11+ India RTI templates included.
- **Multi-Agency Filing**: Batch filing across multiple agencies with rate limiting and tracking integration.
- **Deadline Tracking**: SQLAlchemy-backed database tracking every request from filing through final disposition. Calculates business-day deadlines accounting for holidays.
- **Alert Engine**: Automatic alerts for upcoming deadlines and overdue requests with jurisdiction-specific follow-up guidance.
- **Appeal Generation**: Auto-generated appeal letters with correct legal citations for each jurisdiction. Handles constructive denial (non-response), partial denial, and full denial.
- **Response Analysis**: Parse agency responses to extract page counts, exemptions cited, and fee assessments. Detect suspicious redaction patterns and exemption abuse.
- **MuckRock Integration**: File requests through the MuckRock platform API.
- **CLI Interface**: Full command-line interface for all operations.

## Installation

```bash
pip install -e .
```

## Quick Start

### Generate a FOIA Request

```bash
# US Federal FOIA to USDA-APHIS for inspection reports
foia-rti generate \
    --jurisdiction us-federal \
    --agency USDA-APHIS \
    --topic "Animal Welfare Act inspection reports for commercial dog breeders" \
    --from-date 2024-01-01 \
    --to-date 2025-12-31 \
    --template usda-aphis-inspection-reports \
    --output request.txt

# India RTI to AWBI for slaughterhouse inspections
foia-rti generate \
    --jurisdiction india \
    --agency AWBI \
    --topic "Slaughterhouse inspection compliance in Maharashtra" \
    --template awbi-slaughterhouse-inspections \
    --language english

# UK FOI to Food Standards Agency
foia-rti generate \
    --jurisdiction uk \
    --agency FSA \
    --topic "Slaughterhouse CCTV compliance audit results" \
    -r "CCTV inspection reports for all red meat slaughterhouses" \
    -r "Enforcement actions for CCTV non-compliance"
```

### Track Requests

```bash
# View all tracked requests
foia-rti track --list

# Check overdue requests
foia-rti track --overdue

# Update status
foia-rti track --id 42 --update-status acknowledged

# Add notes
foia-rti track --id 42 --add-note "Received acknowledgment email, assigned to J. Smith"
```

### Generate Appeals

```bash
# Appeal an overdue request
foia-rti appeal --id 42

# Appeal with specific grounds
foia-rti appeal --id 42 --grounds "Exemption (b)(5) improperly applied to factual material"
```

### View Statistics

```bash
foia-rti stats --alerts
```

### List Available Agencies and Templates

```bash
foia-rti list-agencies --jurisdiction us-federal
foia-rti list-templates --jurisdiction us-federal
```

## Python API

```python
from datetime import date
from foia_rti.generators import USFederalGenerator
from foia_rti.generators.generator_base import RequestContext
from foia_rti.tracker import TrackerDB, DeadlineCalculator

# Generate a request
gen = USFederalGenerator()
ctx = RequestContext(
    agency="USDA-FSIS",
    topic="Humane slaughter enforcement at XYZ Packing",
    jurisdiction="US-Federal",
    template_id="usda-fsis-humane-slaughter",
    date_range_start=date(2024, 1, 1),
    date_range_end=date(2025, 12, 31),
)
result = gen.generate(ctx)
print(result.text)

# Track it
db = TrackerDB()
req = db.create_request(
    agency=result.agency,
    jurisdiction=result.jurisdiction,
    topic=ctx.topic,
    request_text=result.text,
    date_filed=date.today(),
    deadline=DeadlineCalculator().calculate("US-Federal", date.today()),
)

# Check for overdue requests
overdue = db.get_overdue()
```

## Project Structure

```
foia_rti/
    generators/          # Request generators per jurisdiction
        generator_base.py    # Abstract base class
        us_federal.py        # US FOIA (USDA, EPA, FDA, OSHA)
        us_state.py          # State public records (12 states)
        india_rti.py         # India RTI Act 2005
        uk_foi.py            # UK FOI Act 2000
        eu_requests.py       # EU Regulation 1049/2001
    tracker/             # Request lifecycle tracking
        tracker.py           # SQLAlchemy models and CRUD
        deadlines.py         # Deadline calculation
        alerts.py            # Overdue/upcoming alerts
        appeals.py           # Appeal letter generation
    filers/              # Filing mechanisms
        email_filer.py       # Email formatting and sending
        batch_filer.py       # Multi-agency batch filing
        muckrock_integration.py  # MuckRock API client
    analysis/            # Response analysis
        response_parser.py   # Extract data from responses
        redaction_detector.py    # Flag exemption abuse
    cli.py               # Click CLI
templates/               # Pre-built request templates (JSON)
tests/                   # Test suite
```

## License

MIT. This software is provided for lawful transparency and accountability purposes.
