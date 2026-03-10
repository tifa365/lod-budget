#!/usr/bin/env python3
"""
Convert Berlin budget CSV to RDF/Turtle.

URI scheme:
  hhbe:EP_BE_{nr}          Einzelplan
  hhbe:Bereich_BE_{nr}     Bereich
  hhbe:Kapitel_BE_{nr}     Kapitel
  hh:Hauptgruppe_{nr}      Hauptgruppe
  hh:Obergruppe_{nr}       Obergruppe
  hh:Gruppe_{nr}           Gruppe
  hh:Hauptfunktion_{nr}    Hauptfunktion
  hh:Oberfunktion_{nr}     Oberfunktion
  hh:Funktion_{nr}         Funktion
  hhbe:{uuid5}             Titel  (seed: "{bereich}-{kapitel}-{titel}")
  hhbe:{uuid5}             Observation  (seed: "{bereich}-{kapitel}-{titel}-{jahr}")

Notes:
  - Leading zeros are stripped from Einzelplan and Kapitel codes so that URIs
    are consistent regardless of CSV source (e.g. "01" and "1" both map to
    hhbe:EP_BE_1). This is intentional normalization, not a data change.
  - Blank rows (missing Jahr) are silently skipped.
  - The IRIs generated here differ from those in the original 2022–2025 TTL,
    which was produced by an external tool with an unknown UUID scheme.
    Validation (bin/validate_conversion.py) proves semantic correctness of the
    data payload; IRI continuity with the historic file is not guaranteed.
"""

import csv
import sys
import uuid
import argparse
from pathlib import Path

from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, RDFS, OWL, XSD

HH      = Namespace("https://okfde.github.io/lod-budget-vocab/")
HHBE    = Namespace("https://berlin.github.io/lod-budget/")
CUBE    = Namespace("https://cube.link/")
META    = Namespace("https://cube.link/meta/")
SCHEMA  = Namespace("https://schema.org/")
SDMX    = Namespace("http://purl.org/linked-data/sdmx/2009/dimension#")
SH      = Namespace("http://www.w3.org/ns/shacl#")
WD      = Namespace("http://www.wikidata.org/entity/")

BERLIN = WD.Q64  # Wikidata URI for Berlin


def make_id(*parts):
    """Deterministic UUID5 from joined parts."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "-".join(parts)))


def build_graph(csv_path, encoding="iso-8859-1"):
    g = Graph()
    g.bind("cube",          CUBE)
    g.bind("hh",            HH)
    g.bind("hhbe",          HHBE)
    g.bind("meta",          META)
    g.bind("owl",           OWL)
    g.bind("rdfs",          RDFS)
    g.bind("schema",        SCHEMA)
    g.bind("sdmx-dimension", SDMX)
    g.bind("sh",            SH)
    g.bind("wd",            WD)
    g.bind("xsd",           XSD)

    _add_vocabulary(g)

    seen = set()

    with open(csv_path, encoding=encoding, newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            # Skip empty rows
            if not row.get("Jahr", "").strip():
                continue
            # Normalize embedded CRLF in field values
            row = {k: v.replace("\r\n", " ").replace("\r", " ") for k, v in row.items()}
            # Strip leading zeros from numeric codes (2026/2027 CSV uses e.g. "01", "0100")
            for col in ("Einzelplan", "Kapitel"):
                row[col] = str(int(row[col]))
            _process_row(g, row, seen)

    return g


def _add_vocabulary(g):
    """Vocabulary class definitions — matches the structure of the original TTL."""
    # hh:ArtDerAngabe
    g.add((HH.ArtDerAngabe, RDF.type, RDFS.Class))
    g.add((HH.ArtDerAngabe, SCHEMA.name, Literal("Art der Angabe", lang="de")))
    g.add((HH.ArtDerAngabe, SCHEMA.description, Literal("Ansatz/Soll/Ist.", lang="de")))

    # hh:Ausgabetitel
    g.add((HH.Ausgabetitel, RDF.type, RDFS.Class))
    g.add((HH.Ausgabetitel, OWL.equivalentClass, WD.Q760120))
    g.add((HH.Ausgabetitel, SCHEMA.name, Literal("Ausgabetitel", lang="de")))

    # hh:Bereich
    g.add((HH.Bereich, RDF.type, RDFS.Class))
    g.add((HH.Bereich, SCHEMA.name, Literal("Bereich", lang="de")))
    g.add((HH.Bereich, SCHEMA.description, Literal(
        "Im landeshaushalterischen Kontext bezeichnet der Begriff Bereich eine "
        "organisatorische Ebene oder Einheit innerhalb der Landesverwaltung, die in der "
        "Haushaltsstruktur als übergeordnete Gliederungsebene dient. Sie differenziert "
        "insbesondere zwischen der zentralen Landesebene und nachgeordneten "
        "Verwaltungseinheiten, denen eigenständige Haushaltsansätze zugeordnet werden können.",
        lang="de")))

    # hh:Einnahmetitel
    g.add((HH.Einnahmetitel, RDF.type, RDFS.Class))
    g.add((HH.Einnahmetitel, OWL.equivalentClass, WD.Q350205))
    g.add((HH.Einnahmetitel, SCHEMA.name, Literal("Einnahmetitel", lang="de")))

    # hh:Einzelplan
    g.add((HH.Einzelplan, RDF.type, RDFS.Class))
    g.add((HH.Einzelplan, RDF.type, META.Hierarchy))
    g.add((HH.Einzelplan, SH.path, _inverse_path(g, SCHEMA.isPartOf)))
    g.add((HH.Einzelplan, META.hierarchyRoot, HH.Einzelplan))
    g.add((HH.Einzelplan, META.nextInHierarchy, HH.Kapitel))
    g.add((HH.Einzelplan, SCHEMA.name, Literal("Einzelplan", lang="de")))
    g.add((HH.Einzelplan, SCHEMA.description, Literal(
        "In einem Einzelplan werden die Haushaltsmittel (Einnahmen, Ausgaben, "
        "Verpflichtungsermächtigungen, Planstellen und andere Stellen) veranschlagt.",
        lang="de")))

    # hh:Funktion
    g.add((HH.Funktion, RDF.type, RDFS.Class))
    g.add((HH.Funktion, SH.path, _inverse_path(g, SCHEMA.isPartOf)))
    g.add((HH.Funktion, META.nextInHierarchy, HH.Titel))
    g.add((HH.Funktion, SCHEMA.name, Literal("Funktion", lang="de")))
    g.add((HH.Funktion, SCHEMA.description, Literal(
        "Unterste Gliederungsebene des Funktionenplans. Sie entspricht einem "
        "Aufgabenbereich innerhalb einer öffentlichen Verwaltung.", lang="de")))

    # hh:Gruppe
    g.add((HH.Gruppe, RDF.type, RDFS.Class))
    g.add((HH.Gruppe, SH.path, _inverse_path(g, SCHEMA.isPartOf)))
    g.add((HH.Gruppe, META.nextInHierarchy, HH.Titel))
    g.add((HH.Gruppe, SCHEMA.name, Literal("Gruppe", lang="de")))
    g.add((HH.Gruppe, SCHEMA.description, Literal(
        "Unterste verbindliche Gliederungsebene des Gruppierungsplans.", lang="de")))

    # hh:Hauptfunktion
    g.add((HH.Hauptfunktion, RDF.type, RDFS.Class))
    g.add((HH.Hauptfunktion, RDF.type, META.Hierarchy))
    g.add((HH.Hauptfunktion, SH.path, _inverse_path(g, SCHEMA.isPartOf)))
    g.add((HH.Hauptfunktion, META.hierarchyRoot, HH.Hauptfunktion))
    g.add((HH.Hauptfunktion, META.nextInHierarchy, HH.Oberfunktion))
    g.add((HH.Hauptfunktion, SCHEMA.name, Literal("Hauptfunktion", lang="de")))
    g.add((HH.Hauptfunktion, SCHEMA.description, Literal(
        "Oberste Gliederungsebene des Funktionenplans.", lang="de")))

    # hh:Hauptgruppe
    g.add((HH.Hauptgruppe, RDF.type, RDFS.Class))
    g.add((HH.Hauptgruppe, RDF.type, META.Hierarchy))
    g.add((HH.Hauptgruppe, SH.path, _inverse_path(g, SCHEMA.isPartOf)))
    g.add((HH.Hauptgruppe, META.hierarchyRoot, HH.Hauptgruppe))
    g.add((HH.Hauptgruppe, META.nextInHierarchy, HH.Obergruppe))
    g.add((HH.Hauptgruppe, SCHEMA.name, Literal("Hauptgruppe", lang="de")))
    g.add((HH.Hauptgruppe, SCHEMA.description, Literal(
        "Oberste Gliederungsebene des Gruppierungsplans.", lang="de")))

    # hh:Kapitel
    g.add((HH.Kapitel, RDF.type, RDFS.Class))
    g.add((HH.Kapitel, SH.path, _inverse_path(g, SCHEMA.isPartOf)))
    g.add((HH.Kapitel, META.nextInHierarchy, HH.Titel))
    g.add((HH.Kapitel, SCHEMA.name, Literal("Haushaltskapitel", lang="de")))
    g.add((HH.Kapitel, SCHEMA.name, Literal("Kapitel", lang="de")))
    g.add((HH.Kapitel, SCHEMA.description, Literal(
        "Gliederungsebene unterhalb der Einzelpläne, d.h. Einzelpläne sind in "
        "verschiedene Kapitel untergliedert. Die Kapitel untergliedern sich ihrerseits "
        "in die einzelnen Titel.", lang="de")))

    # hh:Oberfunktion
    g.add((HH.Oberfunktion, RDF.type, RDFS.Class))
    g.add((HH.Oberfunktion, SH.path, _inverse_path(g, SCHEMA.isPartOf)))
    g.add((HH.Oberfunktion, META.nextInHierarchy, HH.Funktion))
    g.add((HH.Oberfunktion, SCHEMA.name, Literal("Oberfunktion", lang="de")))
    g.add((HH.Oberfunktion, SCHEMA.description, Literal(
        "Mittlere Gliederungsebene des Funktionenplans.", lang="de")))

    # hh:Obergruppe
    g.add((HH.Obergruppe, RDF.type, RDFS.Class))
    g.add((HH.Obergruppe, SH.path, _inverse_path(g, SCHEMA.isPartOf)))
    g.add((HH.Obergruppe, META.nextInHierarchy, HH.Gruppe))
    g.add((HH.Obergruppe, SCHEMA.name, Literal("Obergruppe", lang="de")))
    g.add((HH.Obergruppe, SCHEMA.description, Literal(
        "Mittlere Gliederungsebene des Gruppierungsplans.", lang="de")))

    # hh:Titel
    g.add((HH.Titel, RDF.type, RDFS.Class))
    g.add((HH.Titel, SCHEMA.name, Literal("Haushaltstitel", lang="de")))
    g.add((HH.Titel, SCHEMA.name, Literal("Titel", lang="de")))
    g.add((HH.Titel, SCHEMA.description, Literal(
        "Unterste Gliederungsebene des Haushaltsplans. Die Eindeutigkeit eines Titels "
        "ist jedoch nur durch Verknüpfung mit Haushaltsjahr, Kapitel und - im Falle von "
        "Berlin - dem Bereich gegeben.", lang="de")))

    # hh:Ansatz instance
    g.add((HH.Ansatz, RDF.type, HH.ArtDerAngabe))
    g.add((HH.Ansatz, SCHEMA.name, Literal("Ansatz", lang="de")))


def _inverse_path(g, prop):
    """Create a sh:inversePath blank node."""
    from rdflib import BNode
    bn = BNode()
    g.add((bn, SH.inversePath, prop))
    return bn


def _process_row(g, row, seen):
    ep      = row["Einzelplan"]
    bereich = row["Bereich"]
    kapitel = row["Kapitel"]
    titel   = row["Titel"]
    jahr    = row["Jahr"]

    ep_uri      = _ensure_einzelplan(g, seen, ep, row["Einzelplanbezeichnung"])
    bereich_uri = _ensure_bereich(g, seen, bereich, row["Bereichsbezeichnung"])
    kapitel_uri = _ensure_kapitel(g, seen, kapitel, row["Kapitelbezeichnung"], ep_uri)

    hg_uri  = _ensure_hauptgruppe(g, seen, row["Hauptgruppe"],  row["Hauptgruppenbezeichnung"])
    og_uri  = _ensure_obergruppe(g,  seen, row["Obergruppe"],   row["Obergruppenbezeichnung"], hg_uri)
    gr_uri  = _ensure_gruppe(g,      seen, row["Gruppe"],       row["Gruppenbezeichnung"],     og_uri)

    hf_uri  = _ensure_hauptfunktion(g, seen, row["Hauptfunktion"],  row["Hauptfunktionsbezeichnung"])
    of_uri  = _ensure_oberfunktion(g,  seen, row["Oberfunktion"],   row["Oberfunktionsbezeichnung"], hf_uri)
    fn_uri  = _ensure_funktion(g,      seen, row["Funktion"],       row["Funktionsbezeichnung"],     of_uri)

    titel_uri = _ensure_titel(g, seen, bereich, kapitel, titel,
                              row["Titelbezeichnung"], row["Typ"],
                              bereich_uri, kapitel_uri, gr_uri, fn_uri)

    _add_observation(g, bereich, kapitel, titel, jahr, row["Betrag"], titel_uri)


def _ensure_einzelplan(g, seen, nr, name):
    uri = HHBE[f"EP_BE_{nr}"]
    if uri not in seen:
        seen.add(uri)
        g.add((uri, RDF.type, HH.Einzelplan))
        g.add((uri, HH.nummer, Literal(nr)))
        g.add((uri, HH.vonBundesland, BERLIN))
        g.add((uri, SCHEMA.description, Literal(name, lang="de")))
    return uri


def _ensure_bereich(g, seen, nr, name):
    uri = HHBE[f"Bereich_BE_{nr}"]
    if uri not in seen:
        seen.add(uri)
        g.add((uri, RDF.type, HH.Bereich))
        g.add((uri, HH.nummer, Literal(nr)))
        g.add((uri, HH.vonBundesland, BERLIN))
        g.add((uri, SCHEMA.description, Literal(name, lang="de")))
    return uri


def _ensure_kapitel(g, seen, nr, name, ep_uri):
    uri = HHBE[f"Kapitel_BE_{nr}"]
    if uri not in seen:
        seen.add(uri)
        g.add((uri, RDF.type, HH.Kapitel))
        g.add((uri, HH.nummer, Literal(nr)))
        g.add((uri, SCHEMA.description, Literal(name, lang="de")))
        g.add((uri, SCHEMA.isPartOf, ep_uri))
    return uri


def _ensure_hauptgruppe(g, seen, nr, name):
    uri = HH[f"Hauptgruppe_{nr}"]
    if uri not in seen:
        seen.add(uri)
        g.add((uri, RDF.type, HH.Hauptgruppe))
        g.add((uri, HH.nummer, Literal(nr)))
        g.add((uri, SCHEMA.description, Literal(name, lang="de")))
    return uri


def _ensure_obergruppe(g, seen, nr, name, hg_uri):
    uri = HH[f"Obergruppe_{nr}"]
    if uri not in seen:
        seen.add(uri)
        g.add((uri, RDF.type, HH.Obergruppe))
        g.add((uri, HH.nummer, Literal(nr)))
        g.add((uri, SCHEMA.description, Literal(name, lang="de")))
        g.add((uri, SCHEMA.isPartOf, hg_uri))
    return uri


def _ensure_gruppe(g, seen, nr, name, og_uri):
    uri = HH[f"Gruppe_{nr}"]
    if uri not in seen:
        seen.add(uri)
        g.add((uri, RDF.type, HH.Gruppe))
        g.add((uri, HH.nummer, Literal(nr)))
        g.add((uri, SCHEMA.description, Literal(name, lang="de")))
        g.add((uri, SCHEMA.isPartOf, og_uri))
    return uri


def _ensure_hauptfunktion(g, seen, nr, name):
    uri = HH[f"Hauptfunktion_{nr}"]
    if uri not in seen:
        seen.add(uri)
        g.add((uri, RDF.type, HH.Hauptfunktion))
        g.add((uri, HH.nummer, Literal(nr)))
        g.add((uri, SCHEMA.description, Literal(name, lang="de")))
    return uri


def _ensure_oberfunktion(g, seen, nr, name, hf_uri):
    uri = HH[f"Oberfunktion_{nr}"]
    if uri not in seen:
        seen.add(uri)
        g.add((uri, RDF.type, HH.Oberfunktion))
        g.add((uri, HH.nummer, Literal(nr)))
        g.add((uri, SCHEMA.description, Literal(name, lang="de")))
        g.add((uri, SCHEMA.isPartOf, hf_uri))
    return uri


def _ensure_funktion(g, seen, nr, name, of_uri):
    uri = HH[f"Funktion_{nr}"]
    if uri not in seen:
        seen.add(uri)
        g.add((uri, RDF.type, HH.Funktion))
        g.add((uri, HH.nummer, Literal(nr)))
        g.add((uri, SCHEMA.description, Literal(name, lang="de")))
        g.add((uri, SCHEMA.isPartOf, of_uri))
    return uri


def _ensure_titel(g, seen, bereich, kapitel, nr, description, typ,
                  bereich_uri, kapitel_uri, gruppe_uri, funktion_uri):
    uri = HHBE[make_id(bereich, kapitel, nr)]
    if uri not in seen:
        seen.add(uri)
        titel_class = HH.Einnahmetitel if typ == "1" else HH.Ausgabetitel
        g.add((uri, RDF.type, titel_class))
        g.add((uri, RDF.type, HH.Titel))
        g.add((uri, HH.nummer, Literal(nr)))
        g.add((uri, SCHEMA.description, Literal(description, lang="de")))
        g.add((uri, SCHEMA.isPartOf, bereich_uri))
        g.add((uri, SCHEMA.isPartOf, kapitel_uri))
        g.add((uri, SCHEMA.isPartOf, gruppe_uri))
        g.add((uri, SCHEMA.isPartOf, funktion_uri))
    return uri


def _add_observation(g, bereich, kapitel, titel, jahr, betrag_str, titel_uri):
    uri = HHBE[make_id(bereich, kapitel, titel, jahr)]
    g.add((uri, RDF.type, CUBE.Observation))
    g.add((uri, SDMX.refPeriod, Literal(jahr, datatype=XSD.gYear)))
    g.add((uri, HH.betrag, Literal(int(betrag_str), datatype=XSD.integer)))
    g.add((uri, HH.finanzplanung, HH.Ansatz))
    g.add((uri, HH.titel, titel_uri))


def main():
    parser = argparse.ArgumentParser(description="Convert Berlin budget CSV to RDF/Turtle.")
    parser.add_argument("input", help="Input CSV file")
    parser.add_argument("-o", "--output", default="data/haushalt-be.ttl", help="Output TTL file")
    parser.add_argument("-e", "--encoding", default="iso-8859-1", help="CSV encoding")
    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f"Error: {args.input} not found", file=sys.stderr)
        sys.exit(1)

    print(f"Converting {args.input} ...")
    g = build_graph(args.input, args.encoding)
    g.serialize(destination=args.output, format="turtle")
    print(f"Written {len(g)} triples to {args.output}")


if __name__ == "__main__":
    main()
