# ✈️ Flight Booking Database

> **TL;DR:** The database behind a small airline: which airports, planes, flights, seats, tickets and sales exist, and the rules that keep that data consistent. We designed it on paper (Part 1), then built it in **PostgreSQL** with triggers, ~46 000 rows of realistic test data, a small **REST API in Python/Flask** to search flights, buy tickets and check in, analytics queries (OLAP) and indexes to make them fast (Part 2). University project for *Databases* at Instituto Superior Técnico.

---

## What is this, in plain words?

Every airline website needs a database: a structured place where the system stores flights, planes and tickets, and that refuses data that makes no sense (for example, selling more first-class tickets than there are first-class seats).

This project goes through the whole life of such a database:

1. **Design it** on paper.
2. **Build it** in a real database system.
3. **Fill it** with test data.
4. **Use it** from a small web application.
5. **Analyse** the data and **optimise** the queries.

## Part 1: Designing the data model ([`part1-data-model/`](part1-data-model/))

- **Entity-Relationship model:** a diagram of the "things" in the problem (airport, plane, seat, flight, ticket, sale, ...) and how they relate.
- **Integrity rules** that the diagram alone cannot express, e.g. "an airport has at most 5 terminals" or "a flight's arrival must be after its departure".
- **Conversion to tables** (relational model).
- **Relational algebra** queries.

📄 Report: [`report-part1.pdf`](part1-data-model/report-part1.pdf) (in Portuguese)

## Part 2: Building and using it ([`part2-sql/`](part2-sql/))

Everything is documented step by step in the notebook [`report.ipynb`](part2-sql/report.ipynb) (SQL + explanations, in Portuguese):

| Step | What we did |
|---|---|
| Integrity constraints | PL/pgSQL **triggers** that, for example, block a check-in if the seat class doesn't match the ticket class, or block selling more tickets than seats. |
| Test data | A script that fills every table consistently: ≥10 airports, many planes, flights over several months, tickets and sales ([`data/populate.sql`](part2-sql/data/populate.sql)). |
| REST API | A **Flask** web service ([`app/app.py`](part2-sql/app/app.py)) with endpoints to list airports, list departures from an airport, find flights between two cities, **buy tickets** and **check in**. All writes run inside transactions. |
| Views | A materialized view `estatisticas_voos` that joins the most important flight information in one place. |
| Analytics (OLAP) | Queries that find the busiest routes, analyse revenue by country / city / year / month, and look for weekly patterns in first vs. second class passengers, using `ROLLUP` and window functions (`OVER`). |
| Indexes | B-tree indexes chosen for those analytics queries, justified with `EXPLAIN ANALYZE`. |

### API endpoints

| Method | URL | What it does |
|---|---|---|
| GET | `/` or `/aeroporto` | List all airports |
| GET | `/voos/<departure>` | Flights leaving an airport in the next 12 hours |
| GET | `/voos/<departure>/<arrival>` | Next 3 flights with free seats between two airports |
| POST | `/compra/<flight_id>` | Buy one or more tickets |
| POST | `/checkin/<ticket_id>` | Check in and get a seat assigned |

## How to run it

You need **PostgreSQL** and **Python 3**.

```bash
# 1. Create the database and load schema + data
createdb aviacao
psql aviacao -f part2-sql/data/schema.sql
psql aviacao -f part2-sql/data/populate.sql

# 2. Run the API
cd part2-sql/app
pip install -r requirements.txt
export DATABASE_URL="postgres://<user>:<password>@localhost/aviacao"
flask run --port 8080

# 3. Try it
curl http://localhost:8080/aeroporto
```

To run the triggers, views and analytics, open `part2-sql/report.ipynb` in Jupyter (it uses the `%sql` magic: `pip install jupysql psycopg`) and run the cells in order. The first code cell connects to the course's Docker database; change that connection string to your own.

## Project structure

```
part1-data-model/
  report-part1.pdf     # E-R model, relational schema, relational algebra
part2-sql/
  report.ipynb         # Triggers, views, OLAP queries, indexes (with explanations)
  data/schema.sql      # Table definitions (provided by the course)
  data/populate.sql    # Our test data
  app/                 # Flask REST API (based on the course's app template)
```

## Authors

Vasco Caetano and group colleagues, Instituto Superior Técnico.

## Context

- **Course:** Databases (Bases de Dados), Instituto Superior Técnico, University of Lisbon
- **Stack:** PostgreSQL, PL/pgSQL, SQL (OLAP), Python, Flask, Jupyter
- The base table schema and the Flask app template were provided by the course; the app template keeps its original license in `part2-sql/app/LICENSE.md`.
