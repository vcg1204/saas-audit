# SaaS Subscription Audit Tool

A full-stack web application that helps companies track, analyse, and optimise their SaaS software spending.

## The Problem
Most companies have no centralised view of their SaaS subscriptions. Tools get forgotten, seats go unused, renewals catch teams off guard, and budgets get blown without anyone noticing.

## What This Tool Does
This application gives operations and finance teams a single place to manage their entire SaaS portfolio — tracking spend, detecting waste, scoring tool health, and generating vendor negotiation briefs automatically.

## Features

**Dashboard** — Central command view showing monthly spend, wasted spend, budget status, portfolio health summary, top recommendations, category breakdown, and upcoming renewals in one place.

**Subscription Management** — Add, edit, and delete subscriptions. Tracks tool name, category, cost, billing cycle, seat usage, renewal date, and owner. Export full data to CSV.

**Insights** — Monthly spend by category, most underused tools, top 5 most expensive tools, and overlap detection for tools in the same category.

**Health Scores** — Each tool scored out of 100 based on seat utilisation (50pts), cost efficiency per used seat (30pts), and renewal safety (20pts). Classified as Healthy, Needs Attention, or At Risk.

**Savings Recommendations** — Automatically generates cancel, downgrade, consolidate, or review recommendations with estimated monthly savings.

**Budget vs Actual** — Set a monthly SaaS budget and track actual spend in real time with On Track, Near Limit, or Over Budget status.

**Cost Per Employee** — Calculates what each tool costs per person per month. Flags tools as Reasonable, Moderate, or Expensive.

**Vendor Renewal Negotiation Briefs** — For tools approaching renewal, auto-generates a negotiation position with specific talking points based on usage and cost data.

## Tech Stack
- **Backend:** Python, Flask
- **Database:** PostgreSQL
- **Frontend:** HTML, CSS

## Setup

1. Clone the repository
2. Create and activate a virtual environment
```
python -m venv venv
venv\Scripts\activate
```
3. Install dependencies
```
pip install flask psycopg2-binary
```
4. Create a PostgreSQL database called `saas_audit` and run the SQL in `schema.sql`
5. Update `database.py` with your PostgreSQL credentials
6. Run the app
```
python app.py
```
7. Open `http://127.0.0.1:5000`