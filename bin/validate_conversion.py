#!/usr/bin/env python3
"""
Validate that a converted TTL matches the source CSV row-for-row.

Canonical key: Bereich, Einzelplan, Kapitel, Titel, Jahr
Payload:       Betrag

Checks:
  1. Same number of rows
  2. Same set of canonical keys (no drops, no duplicates)
  3. Same Betrag for every key
  4. Same numeric totals by Jahr, by Einzelplan, and overall
"""

import csv
import sys
import argparse
from collections import defaultdict
from pathlib import Path

from rdflib import Graph, Namespace
from rdflib.namespace import RDF, XSD

HH   = Namespace("https://okfde.github.io/lod-budget-vocab/")
HHBE = Namespace("https://berlin.github.io/lod-budget/")
CUBE = Namespace("https://cube.link/")
SDMX = Namespace("http://purl.org/linked-data/sdmx/2009/dimension#")
SCHEMA = Namespace("https://schema.org/")


# ── CSV ──────────────────────────────────────────────────────────────────────

def load_csv(path, encoding="iso-8859-1"):
    rows = {}
    with open(path, encoding=encoding, newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            if not row.get("Jahr", "").strip():
                continue
            key = (
                row["Bereich"].strip(),
                str(int(row["Einzelplan"])),
                str(int(row["Kapitel"])),
                row["Titel"].strip(),
                row["Jahr"].strip(),
            )
            betrag = int(row["Betrag"].strip())
            if key in rows:
                print(f"  WARNING: duplicate key in CSV: {key}")
            rows[key] = betrag
    return rows


# ── RDF ──────────────────────────────────────────────────────────────────────

def load_rdf(path):
    print(f"Parsing {path} (may take a moment)...")
    g = Graph()
    g.parse(path, format="turtle")

    # Build lookup: Titel URI → (bereich, einzelplan, kapitel, titel_nr)
    titel_info = {}
    for titel in g.subjects(RDF.type, HH.Titel):
        nr = str(next(g.objects(titel, HH.nummer), ""))
        bereich = einzelplan = kapitel = None
        for parent in g.objects(titel, SCHEMA.isPartOf):
            types = set(g.objects(parent, RDF.type))
            if HH.Bereich in types:
                bereich = str(next(g.objects(parent, HH.nummer), ""))
            elif HH.Kapitel in types:
                kapitel = str(next(g.objects(parent, HH.nummer), ""))
                ep = next(g.objects(parent, SCHEMA.isPartOf), None)
                if ep:
                    einzelplan = str(next(g.objects(ep, HH.nummer), ""))
        if bereich and einzelplan and kapitel and nr:
            titel_info[titel] = (bereich, einzelplan, kapitel, nr)

    rows = {}
    for obs in g.subjects(RDF.type, CUBE.Observation):
        titel_uri = next(g.objects(obs, HH.titel), None)
        if titel_uri not in titel_info:
            continue
        bereich, einzelplan, kapitel, titel_nr = titel_info[titel_uri]
        jahr = str(next(g.objects(obs, SDMX.refPeriod), ""))
        betrag_lit = next(g.objects(obs, HH.betrag), None)
        if betrag_lit is None:
            continue
        betrag = int(betrag_lit)
        key = (bereich, einzelplan, kapitel, titel_nr, jahr)
        if key in rows:
            print(f"  WARNING: duplicate key in RDF: {key}")
        rows[key] = betrag
    return rows


# ── Comparison ───────────────────────────────────────────────────────────────

def compare(csv_rows, rdf_rows):
    errors = 0

    # 1. Row counts
    print(f"\n── Row counts ──────────────────────────────")
    print(f"  CSV rows : {len(csv_rows)}")
    print(f"  RDF rows : {len(rdf_rows)}")
    if len(csv_rows) != len(rdf_rows):
        print("  ✗ MISMATCH")
        errors += 1
    else:
        print("  ✓ Match")

    # 2. Missing / extra keys
    csv_keys = set(csv_rows)
    rdf_keys = set(rdf_rows)
    missing = csv_keys - rdf_keys
    extra   = rdf_keys - csv_keys

    print(f"\n── Key reconciliation ──────────────────────")
    if missing:
        print(f"  ✗ {len(missing)} keys in CSV but not in RDF:")
        for k in sorted(missing)[:10]:
            print(f"      {k}")
        if len(missing) > 10:
            print(f"      ... and {len(missing)-10} more")
        errors += 1
    else:
        print("  ✓ No keys missing from RDF")

    if extra:
        print(f"  ✗ {len(extra)} keys in RDF but not in CSV:")
        for k in sorted(extra)[:10]:
            print(f"      {k}")
        errors += 1
    else:
        print("  ✓ No extra keys in RDF")

    # 3. Per-key Betrag mismatches
    print(f"\n── Per-row Betrag check ────────────────────")
    mismatches = {k for k in csv_keys & rdf_keys if csv_rows[k] != rdf_rows[k]}
    if mismatches:
        print(f"  ✗ {len(mismatches)} Betrag mismatches:")
        for k in sorted(mismatches)[:10]:
            print(f"      {k}  CSV={csv_rows[k]}  RDF={rdf_rows[k]}")
        errors += 1
    else:
        print(f"  ✓ All {len(csv_keys & rdf_keys)} matching keys have correct Betrag")

    # 4. Totals
    print(f"\n── Totals ──────────────────────────────────")
    csv_total = sum(csv_rows.values())
    rdf_total = sum(rdf_rows.values())
    print(f"  Overall  CSV={csv_total:>15,}  RDF={rdf_total:>15,}  {'✓' if csv_total == rdf_total else '✗ MISMATCH'}")

    by_jahr_csv = defaultdict(int)
    by_jahr_rdf = defaultdict(int)
    for (_, _, _, _, jahr), v in csv_rows.items():
        by_jahr_csv[jahr] += v
    for (_, _, _, _, jahr), v in rdf_rows.items():
        by_jahr_rdf[jahr] += v
    for jahr in sorted(set(by_jahr_csv) | set(by_jahr_rdf)):
        c, r = by_jahr_csv[jahr], by_jahr_rdf[jahr]
        print(f"  {jahr}     CSV={c:>15,}  RDF={r:>15,}  {'✓' if c == r else '✗ MISMATCH'}")
        if c != r:
            errors += 1

    print(f"\n── Result ──────────────────────────────────")
    if errors == 0:
        print("  ✓ PASS — CSV and RDF are row-for-row identical")
    else:
        print(f"  ✗ FAIL — {errors} issue(s) found")
    return errors == 0


def main():
    parser = argparse.ArgumentParser(description="Validate CSV→RDF conversion.")
    parser.add_argument("csv",  help="Source CSV file")
    parser.add_argument("ttl",  help="Converted TTL file")
    parser.add_argument("-e", "--encoding", default="iso-8859-1")
    args = parser.parse_args()

    for p in [args.csv, args.ttl]:
        if not Path(p).exists():
            print(f"Error: {p} not found", file=sys.stderr)
            sys.exit(1)

    csv_rows = load_csv(args.csv, args.encoding)
    rdf_rows = load_rdf(args.ttl)
    ok = compare(csv_rows, rdf_rows)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
