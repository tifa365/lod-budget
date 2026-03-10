# CSV to RDF Conversion Guide

## From Berlin Budget CSV to Linked Open Data

This guide explains how we transform Berlin's budget data from a flat CSV file into rich, interconnected Linked Open Data (LOD). By the end, you'll understand not just *how* we do it, but *why* each decision matters.

---

## 🎯 The Goal

Transform this:
```csv
ID;Typ;Bezeichnung;Bereich;...;Jahr;BetragTyp;Betrag
1;2;Verfassungsorgane;30;...;2024;Soll;1000
```

Into this:
```turtle
hhbe:titel-123 a hh:Einnahmetitel ;
    schema:name "Verfassungsorgane"@de ;
    hh:nummer "11961" ;
    schema:isPartOf hhbe:Bereich_BE_30 .

hhbe:obs-456 a cube:Observation ;
    hh:titel hhbe:titel-123 ;
    sdmx-dimension:refPeriod "2024"^^xsd:gYear ;
    hh:betrag 1000 .
```

---

## 📚 Understanding the Data Model

### Key Concepts and Terminology

Before diving into the technical mappings, let's understand the essential concepts of Berlin's budget system:

#### Namespace Prefixes
- **`hh:`** = "Haushalt" (Budget) - The [OKF Germany vocabulary](https://okfde.github.io/lod-budget-vocab/) for German public budgets
- **`hhbe:`** = "Haushalt Berlin" - Berlin-specific budget instances and data
- **`cube:`** = [RDF Data Cube](https://www.w3.org/TR/vocab-data-cube/) - W3C standard for statistical data
- **`schema:`** = [Schema.org](https://schema.org/) - General web vocabulary for descriptions and names

#### Berlin's Unique Budget System
Berlin uses **"Erweiterte Kameralistik"** (Extended Cameralistic Accounting) - a hybrid system that combines:
- Traditional cash-based accounting (Kameralistik)
- Cost-performance calculation (Kosten-Leistungsrechnung)
- Product-based management
- Partial asset accounting

This makes Berlin unique among German states - while others use double-entry bookkeeping (Doppik), Berlin enhanced its traditional system instead of replacing it.

#### The Three-Level Hierarchy

**1. Einzelplan (Budget Section)**
- Top-level organizational units (e.g., EP 01 = Parliament, EP 03-15 = Senate departments)
- Berlin's 12 districts each get their own Einzelplan (31-42)
- Think of it as "which department gets the money"

**2. Kapitel (Chapter)**
- Sub-divisions within each Einzelplan
- Systematic numbering: ..01-09 for programs, ..10 for miscellaneous, ..11 for central administration
- Groups related activities within a department

**3. Titel (Budget Line Item)**
- The atomic unit - a specific purpose for spending/receiving money
- 5-digit number unique within its Kapitel
- Examples: 11961 = "Tax refunds", 42701 = "Construction measures"

#### Classification Systems

**Gruppierungsplan (Economic Classification)**
Answers "What type of expense/income is this?"
- **Hauptgruppe** (Main Group): 1-digit codes (1=Personnel, 4=Current transfers, etc.)
- **Obergruppe** (Upper Group): 2-digit refinement
- **Gruppe** (Group): 3-digit specific category

**Funktionenplan (Functional Classification)**
Answers "What government function does this serve?"
- **Hauptfunktion** (Main Function): Major government areas
- **Oberfunktion** (Upper Function): Sub-areas
- **Funktion** (Function): Specific government tasks (e.g., 311 = General schools)

#### Financial Concepts

**Einnahmetitel vs. Ausgabetitel**
- **Einnahmetitel** = Revenue items (money coming IN)
- **Ausgabetitel** = Expense items (money going OUT)
- Determined by the `Typ` field: 1 = Revenue, 2 = Expense

**Budget Types (BetragTyp)**
- **Ansatz/Soll** = Planned/budgeted amount (what we expect to spend/receive)
- **Ist** = Actual amount (what was really spent/received)
- **Nachtrag** = Supplementary budget (mid-year adjustments)

The CSV contains only "Soll" (planned) amounts for 2024/2025.

### The CSV Structure

Berlin's budget CSV contains 27 columns representing a hierarchical budget structure:

#### Basic Information (Columns 1-3)
| Column | Description | RDF Mapping |
|--------|-------------|-------------|
| `ID` | Row identifier | Not used (we generate UUIDs) |
| `Typ` | Income/Expense type (1=Income, 2=Expense) | Determines class (`Einnahmetitel`/`Ausgabetitel`) |
| `Bezeichnung` | General description | `schema:name` on main entity |

#### Organizational Hierarchy (Columns 4-9)
| Column | Description | RDF Mapping |
|--------|-------------|-------------|
| `Bereich` | District/Department code (30-42) | Links to `hh:Bereich` instance |
| `Bereichsbezeichnung` | District/Department name | `schema:name` on `hh:Bereich` |
| `Einzelplan` | Budget section code | Links to `hh:Einzelplan` instance |
| `Einzelplanbezeichnung` | Budget section name | `schema:name` on `hh:Einzelplan` |
| `Kapitel` | Chapter code | Links to `hh:Kapitel` instance |
| `Kapitelbezeichnung` | Chapter name | `schema:name` on `hh:Kapitel` |

#### Expense Classification (Columns 10-15)
| Column | Description | RDF Mapping |
|--------|-------------|-------------|
| `Hauptgruppe` | Main group code (1-9) | Links to `hh:Hauptgruppe` instance |
| `Hauptgruppenbezeichnung` | Main group name | `schema:name` on `hh:Hauptgruppe` |
| `Obergruppe` | Upper group code | Links to `hh:Obergruppe` instance |
| `Obergruppenbezeichnung` | Upper group name | `schema:name` on `hh:Obergruppe` |
| `Gruppe` | Group code (3-digit) | Links to `hh:Gruppe` instance |
| `Gruppenbezeichnung` | Group name | `schema:name` on `hh:Gruppe` |

#### Functional Classification (Columns 16-21)
| Column | Description | RDF Mapping |
|--------|-------------|-------------|
| `Hauptfunktion` | Main function code | Links to `hh:Hauptfunktion` instance |
| `Hauptfunktionsbezeichnung` | Main function name | `schema:name` on `hh:Hauptfunktion` |
| `Oberfunktion` | Upper function code | Links to `hh:Oberfunktion` instance |
| `Oberfunktionsbezeichnung` | Upper function name | `schema:name` on `hh:Oberfunktion` |
| `Funktion` | Function code (3-digit) | Links to `hh:Funktion` instance |
| `Funktionsbezeichnung` | Function name | `schema:name` on `hh:Funktion` |

#### Budget Line Details (Columns 22-24)
| Column | Description | RDF Mapping |
|--------|-------------|-------------|
| `Titelart` | Title type | Validates against `Typ` field |
| `Titel` | Budget line number (5-digit) | `hh:nummer` property on `hh:Titel` |
| `Titelbezeichnung` | Budget line description | `schema:description` on `hh:Titel` |

#### Financial Data (Columns 25-27)
| Column | Description | RDF Mapping |
|--------|-------------|-------------|
| `Jahr` | Budget year (2024/2025) | `sdmx-dimension:refPeriod` on observation |
| `BetragTyp` | Amount type (always "Soll") | Maps to `hh:finanzplanung hh:Ansatz` |
| `Betrag` | Amount in euros | `hh:betrag` on observation |

### Understanding the Hierarchical Relationships

The genius of Berlin's budget system lies in its **dual classification**:

1. **Institutional Path** (WHO spends): Einzelplan → Kapitel → Titel
   - Example: Senate Finance Dept → Central Admin → Office Supplies

2. **Economic Path** (WHAT type): Hauptgruppe → Obergruppe → Gruppe
   - Example: Operating Expenses → Administrative Expenses → Office Materials

3. **Functional Path** (WHY/PURPOSE): Hauptfunktion → Oberfunktion → Funktion
   - Example: General Services → Central Administration → Financial Administration

This triple classification allows queries like:
- "How much do ALL departments spend on office supplies?" (via Gruppe)
- "What's the education budget across ALL districts?" (via Funktion)
- "What does District Mitte spend in total?" (via Bereich)

### The RDF Model

We use two complementary vocabularies:

1. **[OKF Budget Vocabulary](https://okfde.github.io/lod-budget-vocab/)** (`hh:`)
   - Defines budget-specific concepts
   - Provides hierarchical structure
   - German public finance standard

2. **[RDF Data Cube](https://www.w3.org/TR/vocab-data-cube/)** (`cube:`)
   - W3C standard for statistical data
   - Enables OLAP-style analysis
   - Integrates with BI tools

---

## 🔄 The Conversion Process

### Step 1: Parse the CSV

```python
import csv
import uuid
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, RDFS, XSD

# Define namespaces
HH = Namespace("https://okfde.github.io/lod-budget-vocab/")
HHBE = Namespace("https://berlin.github.io/lod-budget/")
CUBE = Namespace("https://cube.link/")
SCHEMA = Namespace("https://schema.org/")

# Read CSV with proper encoding
with open('budget.csv', 'r', encoding='iso-8859-1') as f:
    reader = csv.DictReader(f, delimiter=';')
    for row in reader:
        process_row(row)
```

**Key decisions:**
- ✅ Use `iso-8859-1` encoding for German characters
- ✅ Semicolon delimiter (European standard)
- ✅ Generate UUIDs for stable URIs

### Step 2: Create Hierarchical Entities

Each CSV row references multiple hierarchical levels. We create or reference:

```python
def create_hierarchies(row, graph):
    # Create/reference Bereich (District/Department)
    bereich_uri = HHBE[f"Bereich_BE_{row['Bereich']}"]
    if not (bereich_uri, RDF.type, HH.Bereich) in graph:
        graph.add((bereich_uri, RDF.type, HH.Bereich))
        graph.add((bereich_uri, SCHEMA.name, 
                   Literal(row['Bereichsbezeichnung'], lang='de')))
    
    # Create/reference Einzelplan (Budget Section)
    einzelplan_uri = HHBE[f"Einzelplan_BE_{row['Einzelplan']}"]
    if not (einzelplan_uri, RDF.type, HH.Einzelplan) in graph:
        graph.add((einzelplan_uri, RDF.type, HH.Einzelplan))
        graph.add((einzelplan_uri, SCHEMA.name,
                   Literal(row['Einzelplanbezeichnung'], lang='de')))
    
    # Continue for Kapitel, Hauptgruppe, etc...
```

**Why this matters:**
- 🔗 Creates reusable entities (DRY principle)
- 📊 Enables hierarchical queries
- 🌐 Links budget items across departments

### Step 3: Create Budget Line Items (Titel)

Each unique budget line becomes a `Titel` entity:

```python
def create_titel(row, graph):
    # Generate stable UUID from deterministic data
    titel_id = generate_uuid(
        row['Bereich'], 
        row['Einzelplan'],
        row['Kapitel'],
        row['Titel']
    )
    
    titel_uri = HHBE[f"titel-{titel_id}"]
    
    # Determine type based on Typ field
    titel_type = HH.Einnahmetitel if row['Typ'] == '1' else HH.Ausgabetitel
    
    # Add type and properties
    graph.add((titel_uri, RDF.type, titel_type))
    graph.add((titel_uri, RDF.type, HH.Titel))
    graph.add((titel_uri, HH.nummer, Literal(row['Titel'])))
    graph.add((titel_uri, SCHEMA.description, 
               Literal(row['Titelbezeichnung'], lang='de')))
    
    # Link to hierarchies
    graph.add((titel_uri, SCHEMA.isPartOf, bereich_uri))
    graph.add((titel_uri, SCHEMA.isPartOf, einzelplan_uri))
    graph.add((titel_uri, SCHEMA.isPartOf, kapitel_uri))
    
    return titel_uri
```

**Design choices:**
- 🔑 Deterministic UUIDs ensure consistency across runs
- 🏷️ Dual typing (specific + general) for flexible queries
- 🔗 Multiple `isPartOf` links for different hierarchies

### Step 4: Create Observations

Each row represents a financial observation:

```python
def create_observation(row, titel_uri, graph):
    # Generate unique observation ID
    obs_id = str(uuid.uuid4())
    obs_uri = HHBE[obs_id]
    
    # Create observation
    graph.add((obs_uri, RDF.type, CUBE.Observation))
    
    # Link to dimensions
    graph.add((obs_uri, HH.titel, titel_uri))
    graph.add((obs_uri, SDMX.refPeriod, 
               Literal(row['Jahr'], datatype=XSD.gYear)))
    
    # Add measure
    graph.add((obs_uri, HH.betrag, 
               Literal(int(row['Betrag']), datatype=XSD.integer)))
    
    # Add metadata
    graph.add((obs_uri, HH.finanzplanung, HH.Ansatz))
```

**Why Data Cube?**
- 📊 Standard statistical model
- 🔍 Enables SPARQL aggregations
- 📈 Compatible with visualization tools

---

## 🎨 Complete Example

Let's trace a real budget item through the system to see how everything connects:

### Real-World Scenario: School Renovation in Mitte
Imagine Berlin budgets €2.5 million for renovating elementary schools in the Mitte district.

### Input CSV Row:
```csv
12345;2;Schulbaumaßnahmen;31;Mitte;40;Bezirk Mitte;4010;Schulverwaltung;7;Baumaßnahmen;70;Hochbau;700;Neu-, Um- und Erweiterungsbauten;2;Bildungswesen;21;Schulen;211;Allgemeinbildende Schulen;Ausgabetitel;70001;Kleine Neu-, Um- und Erweiterungsbauten;2024;Soll;2500000
```

Breaking this down:
- **WHO**: District Mitte (Bereich 31) → School Administration (Kapitel 4010)
- **WHAT**: Construction (Hauptgruppe 7) → Building Construction (Gruppe 700)
- **WHY**: Education (Hauptfunktion 2) → Schools (Funktion 211)
- **SPECIFIC**: Small construction projects (Titel 70001)
- **WHEN/HOW MUCH**: €2.5M planned for 2024

### Output RDF (Turtle):
```turtle
# The Bereich (District/Department)
hhbe:Bereich_BE_30 a hh:Bereich ;
    schema:name "Hauptverwaltung"@de ;
    rdfs:seeAlso lor:bez_01 .  # Link to geographic data

# The Einzelplan (Budget Section)  
hhbe:Einzelplan_BE_1 a hh:Einzelplan ;
    schema:name "Abgeordnetenhaus"@de ;
    meta:hierarchyRoot hh:Einzelplan ;
    meta:nextInHierarchy hh:Kapitel .

# The Kapitel (Chapter)
hhbe:Kapitel_BE_100 a hh:Kapitel ;
    schema:name "Abgeordnetenhaus"@de ;
    schema:isPartOf hhbe:Einzelplan_BE_1 .

# The Titel (Budget Line Item)
hhbe:4a83f879-7309-563f-9e8c-df8fe1a3d628 a hh:Einnahmetitel, hh:Titel ;
    hh:nummer "11961" ;
    schema:description "Erstattung von Steuerbeträgen"@de ;
    schema:isPartOf hhbe:Bereich_BE_30,
                    hhbe:Einzelplan_BE_1,
                    hhbe:Kapitel_BE_100,
                    hh:Gruppe_119 .

# The Observation (Actual Amount)
hhbe:0000daec-7aad-5266-93ae-82805e8c43fd a cube:Observation ;
    sdmx-dimension:refPeriod "2024"^^xsd:gYear ;
    hh:betrag 1000 ;
    hh:finanzplanung hh:Ansatz ;
    hh:titel hhbe:4a83f879-7309-563f-9e8c-df8fe1a3d628 .
```

---

## 🚀 Running the Converter

### Basic Usage

```bash
python bin/csv_to_rdf.py \
    --input csv-opendata_doppelhaushalt_2024_2025.csv \
    --output data/haushalt-be.ttl
```

### Advanced Options

```bash
python bin/csv_to_rdf.py \
    --input budget.csv \
    --output budget.ttl \
    --format turtle \              # Output format (turtle, ntriples, jsonld)
    --validate \                   # Validate against SHACL shapes
    --stats \                      # Print conversion statistics
    --encoding iso-8859-1 \        # Input encoding
    --delimiter ';' \              # CSV delimiter
    --base-uri https://berlin.github.io/lod-budget/
```

---

## 🔍 Validation & Quality Checks

### 1. Completeness Check
```python
def validate_completeness(csv_file, rdf_graph):
    csv_count = count_csv_rows(csv_file)
    rdf_count = count_observations(rdf_graph)
    
    if csv_count != rdf_count:
        print(f"⚠️  Warning: CSV has {csv_count} rows, "
              f"but RDF has {rdf_count} observations")
        print(f"📊 Completeness: {rdf_count/csv_count*100:.1f}%")
```

### 2. Data Integrity
```sparql
# Check for orphaned observations
SELECT ?obs WHERE {
    ?obs a cube:Observation .
    FILTER NOT EXISTS { ?obs hh:titel ?titel }
}
```

### 3. Hierarchical Consistency
```sparql
# Ensure all Titel have required hierarchies
SELECT ?titel WHERE {
    ?titel a hh:Titel .
    FILTER NOT EXISTS { ?titel schema:isPartOf ?kapitel }
}
```

---

## 📊 Query Examples

### Total Budget by Year
```sparql
SELECT ?year (SUM(?amount) as ?total) WHERE {
    ?obs a cube:Observation ;
         sdmx-dimension:refPeriod ?year ;
         hh:betrag ?amount .
} GROUP BY ?year ORDER BY ?year
```

### Expenses by District
```sparql
SELECT ?district ?name (SUM(?amount) as ?total) WHERE {
    ?obs a cube:Observation ;
         hh:titel/schema:isPartOf ?district ;
         hh:betrag ?amount .
    ?district a hh:Bereich ;
              schema:name ?name .
} GROUP BY ?district ?name ORDER BY DESC(?total)
```

---

## 🐛 Common Issues & Solutions

### Issue: German Characters Corrupted
**Solution:** Ensure ISO-8859-1 encoding when reading CSV
```python
open('file.csv', 'r', encoding='iso-8859-1')
```

### Issue: Duplicate Entities
**Solution:** Use deterministic UUID generation
```python
def generate_uuid(*args):
    data = '-'.join(str(arg) for arg in args)
    return str(uuid.uuid5(uuid.NAMESPACE_URL, data))
```

### Issue: Memory Usage with Large Files
**Solution:** Process in chunks
```python
for chunk in pd.read_csv('file.csv', chunksize=10000):
    process_chunk(chunk)
    graph.serialize('output.ttl', format='turtle', append=True)
```

---

## 🎓 Learn More

- [RDF Primer](https://www.w3.org/TR/rdf11-primer/) - Understanding RDF basics
- [SPARQL Tutorial](https://www.w3.org/TR/sparql11-query/) - Querying your data
- [Data Cube Vocabulary](https://www.w3.org/TR/vocab-data-cube/) - Statistical LOD
- [Berlin Open Data](https://daten.berlin.de/) - Source datasets

---

## 📝 License

This documentation is published under [CC-BY 4.0](https://creativecommons.org/licenses/by/4.0/). The code examples are under [MIT License](https://opensource.org/licenses/MIT).