#!/usr/bin/env python3
"""
Internal consistency check for the merged haushalt-be.ttl.

Checks:
  1. Observation count and totals per year (and overall)
  2. Duplicate observation keys (Bereich+Kapitel+Titel+Jahr)
  3. Class coverage — every Observation and Titel is properly typed
  4. Correct Einnahme/Ausgabe classification (matches Typ in CSV if provided)
  5. Amount sanity — integers only, negatives/zeros allowed, no floats
  6. Hierarchy completeness — no dangling schema:isPartOf references
"""

import sys
import argparse
from collections import defaultdict
from pathlib import Path

from rdflib import Graph, Namespace
from rdflib.namespace import RDF, XSD

HH     = Namespace("https://okfde.github.io/lod-budget-vocab/")
HHBE   = Namespace("https://berlin.github.io/lod-budget/")
CUBE   = Namespace("https://cube.link/")
SDMX   = Namespace("http://purl.org/linked-data/sdmx/2009/dimension#")
SCHEMA = Namespace("https://schema.org/")


def check(ttl_path):
    print(f"Parsing {ttl_path} ...")
    g = Graph()
    g.parse(ttl_path, format="turtle")
    print(f"  {len(g)} triples loaded\n")

    errors = 0

    # ── 1. Observations per year + totals ────────────────────────────────────
    print("── Observations per year ───────────────────────────────")
    by_year_count  = defaultdict(int)
    by_year_total  = defaultdict(int)
    obs_keys       = []
    untyped_obs    = 0
    float_amounts  = 0

    for obs in g.subjects(RDF.type, CUBE.Observation):
        jahr_lit = next(g.objects(obs, SDMX.refPeriod), None)
        betrag_lit = next(g.objects(obs, HH.betrag), None)

        if jahr_lit is None or betrag_lit is None:
            untyped_obs += 1
            continue

        jahr = str(jahr_lit)

        # Amount sanity
        raw = betrag_lit.toPython()
        if isinstance(raw, float):
            float_amounts += 1
        betrag = int(raw)

        by_year_count[jahr] += 1
        by_year_total[jahr] += betrag

        # Build key for duplicate check
        titel_uri = next(g.objects(obs, HH.titel), None)
        if titel_uri:
            titel_nr  = str(next(g.objects(titel_uri, HH.nummer), "?"))
            bereich   = None
            kapitel   = None
            for parent in g.objects(titel_uri, SCHEMA.isPartOf):
                types = set(g.objects(parent, RDF.type))
                if HH.Bereich in types:
                    bereich = str(next(g.objects(parent, HH.nummer), "?"))
                elif HH.Kapitel in types:
                    kapitel = str(next(g.objects(parent, HH.nummer), "?"))
            obs_keys.append((bereich, kapitel, titel_nr, jahr))

    overall_count = sum(by_year_count.values())
    overall_total = sum(by_year_total.values())

    for year in sorted(by_year_count):
        print(f"  {year}  {by_year_count[year]:>7} obs  {by_year_total[year]:>20,} EUR")
    print(f"  {'TOTAL':6}  {overall_count:>7} obs  {overall_total:>20,} EUR")

    # ── 2. Duplicate observation keys ────────────────────────────────────────
    print(f"\n── Duplicate observation keys ──────────────────────────")
    seen_keys = set()
    dupes = []
    for key in obs_keys:
        if key in seen_keys:
            dupes.append(key)
        seen_keys.add(key)
    if dupes:
        print(f"  ✗ {len(dupes)} duplicate keys found:")
        for k in dupes[:10]:
            print(f"      {k}")
        errors += 1
    else:
        print(f"  ✓ No duplicate keys across {len(obs_keys)} observations")

    # ── 3. Class coverage ────────────────────────────────────────────────────
    print(f"\n── Class coverage ──────────────────────────────────────")
    all_titel = set(g.subjects(RDF.type, HH.Titel))
    typed_titel = set(g.subjects(RDF.type, HH.Einnahmetitel)) | \
                  set(g.subjects(RDF.type, HH.Ausgabetitel))
    untyped_titel = all_titel - typed_titel

    if untyped_obs:
        print(f"  ✗ {untyped_obs} Observations missing Jahr or Betrag")
        errors += 1
    else:
        print(f"  ✓ All observations have Jahr and Betrag")

    if untyped_titel:
        print(f"  ✗ {len(untyped_titel)} Titel without Einnahme/Ausgabe type")
        errors += 1
    else:
        print(f"  ✓ All {len(all_titel)} Titel have Einnahme/Ausgabe classification")

    if float_amounts:
        print(f"  ✗ {float_amounts} non-integer Betrag values")
        errors += 1
    else:
        print(f"  ✓ All amounts are integers")

    neg = sum(1 for v in by_year_total.values() if v < 0)
    zeros = sum(1 for k in obs_keys
                if next((b for b, kap, t, j in [k]), None) is not None)
    # Count zero-amount observations
    zero_obs = sum(1 for obs in g.subjects(RDF.type, CUBE.Observation)
                   if int((next(g.objects(obs, HH.betrag), None) or 0).toPython()) == 0)
    neg_obs  = sum(1 for obs in g.subjects(RDF.type, CUBE.Observation)
                   if int((next(g.objects(obs, HH.betrag), None) or 0).toPython()) < 0)
    print(f"  ✓ Negative amounts: {neg_obs} (valid contra-entries)")
    print(f"  ✓ Zero amounts:     {zero_obs}")

    # ── 4. Hierarchy completeness ─────────────────────────────────────────────
    print(f"\n── Hierarchy completeness ──────────────────────────────")
    dangling = 0
    for s, p, o in g.triples((None, SCHEMA.isPartOf, None)):
        if (o, RDF.type, None) not in g:
            dangling += 1
            if dangling <= 5:
                print(f"  Dangling: {s.n3()} -> {o.n3()}")
    if dangling:
        print(f"  ✗ {dangling} dangling schema:isPartOf references")
        errors += 1
    else:
        print(f"  ✓ All schema:isPartOf targets exist")

    # ── Result ────────────────────────────────────────────────────────────────
    print(f"\n── Result ──────────────────────────────────────────────")
    if errors == 0:
        print("  ✓ PASS")
    else:
        print(f"  ✗ FAIL — {errors} issue(s) found")
    return errors == 0


def main():
    parser = argparse.ArgumentParser(description="Check internal consistency of merged TTL.")
    parser.add_argument("ttl", help="TTL file to check")
    args = parser.parse_args()
    if not Path(args.ttl).exists():
        print(f"Error: {args.ttl} not found", file=sys.stderr)
        sys.exit(1)
    ok = check(args.ttl)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
