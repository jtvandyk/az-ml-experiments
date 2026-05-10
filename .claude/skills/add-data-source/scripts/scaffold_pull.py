#!/usr/bin/env python3
"""Scaffold a new data-pull notebook from the canonical template.

Reads `templates/data_pull_template.ipynb`, substitutes placeholders, writes
a new notebook at `<notebook-dir>/<NN>_pull_<source_key>.ipynb`.

Placeholders substituted:
  {{NN}}                  — two-digit notebook number
  {{SOURCE_NAME}}         — human-readable source name
  {{SOURCE_KEY}}          — snake_case key used in filename + ADLS path
  {{SOURCE_DESCRIPTION}}  — one-paragraph description for the title cell
  {{PROVIDER}}            — provider org (e.g. "World Bank", "IMF")
  {{SOURCE_URL}}          — homepage / API endpoint
  {{CADENCE}}             — release cadence (e.g. "Annual", "Monthly → annual")
"""
import argparse
import re
import sys
from pathlib import Path

PLACEHOLDERS = (
    "NN",
    "SOURCE_NAME",
    "SOURCE_KEY",
    "SOURCE_DESCRIPTION",
    "PROVIDER",
    "SOURCE_URL",
    "CADENCE",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--nn", required=True, help="Two-digit notebook number, e.g. 27")
    parser.add_argument("--source-name", required=True, help='Human name, e.g. "FAO Locust Watch"')
    parser.add_argument("--source-key", required=True, help="snake_case, e.g. fao_locust")
    parser.add_argument("--source-description", required=True,
                        help="One-paragraph description for the title cell")
    parser.add_argument("--provider", required=True, help='e.g. "World Bank", "IMF"')
    parser.add_argument("--source-url", required=True, help="Homepage or API endpoint URL")
    parser.add_argument("--cadence", required=True, help='e.g. "Annual", "Monthly → annual"')
    parser.add_argument("--notebook-dir", default="notebooks/01_data_pull",
                        help="Destination directory (default: notebooks/01_data_pull)")
    parser.add_argument("--template",
                        default=str(Path(__file__).parent.parent / "templates" / "data_pull_template.ipynb"),
                        help="Override template path")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite if destination already exists")
    args = parser.parse_args()

    # Validate inputs.
    if not re.fullmatch(r"\d{2}", args.nn):
        print(f"error: --nn must be two digits, got {args.nn!r}", file=sys.stderr)
        return 2
    if not re.fullmatch(r"[a-z][a-z0-9_]*", args.source_key):
        print(f"error: --source-key must be snake_case (lowercase + underscores), got {args.source_key!r}",
              file=sys.stderr)
        return 2

    template_path = Path(args.template)
    if not template_path.exists():
        print(f"error: template not found at {template_path}", file=sys.stderr)
        return 2

    text = template_path.read_text()

    subs = {
        "NN": args.nn,
        "SOURCE_NAME": args.source_name,
        "SOURCE_KEY": args.source_key,
        "SOURCE_DESCRIPTION": args.source_description,
        "PROVIDER": args.provider,
        "SOURCE_URL": args.source_url,
        "CADENCE": args.cadence,
    }
    for ph in PLACEHOLDERS:
        text = text.replace("{{" + ph + "}}", subs[ph])

    # Sanity: check no placeholders survived.
    leftover = re.findall(r"\{\{[A-Z_]+\}\}", text)
    if leftover:
        print(f"error: unsubstituted placeholders remain: {sorted(set(leftover))}", file=sys.stderr)
        return 2

    out_dir = Path(args.notebook_dir)
    if not out_dir.exists():
        print(f"error: notebook directory does not exist: {out_dir}", file=sys.stderr)
        return 2

    out_path = out_dir / f"{args.nn}_pull_{args.source_key}.ipynb"
    if out_path.exists() and not args.force:
        print(f"error: {out_path} already exists (use --force to overwrite)", file=sys.stderr)
        return 2

    out_path.write_text(text)
    print(f"Scaffolded: {out_path}")
    print()
    print("Next steps:")
    print(f"  1. Open {out_path}")
    print("  2. Replace cell-fetch's NotImplementedError body with the real download")
    print("  3. Adjust cell-clean if the source has unusual schema (sub-sectors, wide format, etc.)")
    print("  4. Smoke-test on a small year range")
    print(f"  5. Wire into 02/02 — add to RAW_PREFIXES (cell-3) and add a _join_iso3_source(\"{args.source_key}\") call")
    return 0


if __name__ == "__main__":
    sys.exit(main())
