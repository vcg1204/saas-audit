from flask import Response
import io
import csv
from flask import Flask, render_template, request, redirect, url_for
from database import get_connection
from datetime import date

app = Flask(__name__)

# ── Dashboard ──────────────────────────────────────────────────────────


@app.route("/")
def dashboard():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM subscriptions")
    subs = cur.fetchall()

    total_monthly = 0
    wasted_monthly = 0
    upcoming = []
    alerts = []

    for s in subs:
        if s["billing_cycle"] == "Annual":
            monthly = float(s["cost"]) / 12
        else:
            monthly = float(s["cost"])

        total_monthly += monthly

        if s["seats_paid"] and s["seats_used"] is not None:
            unused = float(s["seats_paid"]) - float(s["seats_used"])
            if unused > 0:
                waste = (unused / float(s["seats_paid"])) * monthly
                wasted_monthly += waste

        if s["renewal_date"]:
            days_left = (s["renewal_date"] - date.today()).days
            if 0 <= days_left <= 30:
                upcoming.append({**s, "days_left": days_left})

        if s["seats_paid"] and s["seats_used"] is not None:
            usage_pct = (float(s["seats_used"]) / float(s["seats_paid"])) * 100
            if usage_pct < 50:
                alerts.append({**s, "usage_pct": round(usage_pct, 1)})

    cur.close()
    conn.close()

    return render_template("dashboard.html",
                           total_monthly=round(total_monthly, 2),
                           wasted_monthly=round(wasted_monthly, 2),
                           total_subs=len(subs),
                           upcoming=upcoming,
                           alerts=alerts
                           )

# ── All subscriptions ──────────────────────────────────────────────────


@app.route("/subscriptions")
def subscriptions():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM subscriptions ORDER BY renewal_date ASC")
    subs = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("subscriptions.html", subs=subs)

# ── Add subscription ───────────────────────────────────────────────────


@app.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO subscriptions 
            (tool_name, category, cost, billing_cycle, seats_paid, seats_used, renewal_date, owner, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            request.form["tool_name"],
            request.form["category"],
            request.form["cost"],
            request.form["billing_cycle"],
            request.form["seats_paid"] or None,
            request.form["seats_used"] or None,
            request.form["renewal_date"] or None,
            request.form["owner"],
            request.form["notes"]
        ))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for("subscriptions"))
    return render_template("add.html")

# ── Delete subscription ────────────────────────────────────────────────


@app.route("/delete/<int:id>")
def delete(id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM subscriptions WHERE id = %s", (id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for("subscriptions"))

# ── Insights ───────────────────────────────────────────────────────────


@app.route("/insights")
def insights():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT category,
        SUM(CASE WHEN billing_cycle = 'Annual' THEN cost/12 ELSE cost END) as monthly_spend
        FROM subscriptions
        GROUP BY category
        ORDER BY monthly_spend DESC
    """)
    by_category = cur.fetchall()

    cur.execute("""
        SELECT tool_name, seats_paid, seats_used,
        ROUND((seats_used::numeric / seats_paid) * 100, 1) as usage_pct
        FROM subscriptions
        WHERE seats_paid > 0 AND seats_used IS NOT NULL
        ORDER BY usage_pct ASC
        LIMIT 5
    """)
    underused = cur.fetchall()

    cur.execute("""
        SELECT tool_name,
        CASE WHEN billing_cycle = 'Annual' THEN cost/12 ELSE cost END as monthly_cost
        FROM subscriptions
        ORDER BY monthly_cost DESC
        LIMIT 5
    """)
    expensive = cur.fetchall()

    cur.execute("""
        SELECT category, COUNT(*) as tool_count, 
        STRING_AGG(tool_name, ', ') as tools
        FROM subscriptions
        GROUP BY category
        HAVING COUNT(*) > 1
    """)
    overlaps = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("insights.html",
                           by_category=by_category,
                           underused=underused,
                           expensive=expensive,
                           overlaps=overlaps
                           )

# ── Edit subscription ──────────────────────────────────────────────────


@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):
    conn = get_connection()
    cur = conn.cursor()

    if request.method == "POST":
        cur.execute("""
            UPDATE subscriptions
            SET tool_name=%s, category=%s, cost=%s, billing_cycle=%s,
                seats_paid=%s, seats_used=%s, renewal_date=%s, owner=%s, notes=%s
            WHERE id=%s
        """, (
            request.form["tool_name"],
            request.form["category"],
            request.form["cost"],
            request.form["billing_cycle"],
            request.form["seats_paid"] or None,
            request.form["seats_used"] or None,
            request.form["renewal_date"] or None,
            request.form["owner"],
            request.form["notes"],
            id
        ))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for("subscriptions"))

    cur.execute("SELECT * FROM subscriptions WHERE id = %s", (id,))
    sub = cur.fetchone()
    cur.close()
    conn.close()
    return render_template("edit.html", sub=sub)


# ── Export to CSV ──────────────────────────────────────────────────────


@app.route("/export")
def export():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT tool_name, category, cost, billing_cycle, seats_paid, seats_used, renewal_date, owner, notes FROM subscriptions")
    subs = cur.fetchall()
    cur.close()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Tool Name", "Category", "Cost", "Billing Cycle",
                    "Seats Paid", "Seats Used", "Renewal Date", "Owner", "Notes"])
    for s in subs:
        writer.writerow([
            s["tool_name"], s["category"], s["cost"], s["billing_cycle"],
            s["seats_paid"], s["seats_used"], s["renewal_date"], s["owner"], s["notes"]
        ])

    output.seek(0)
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=subscriptions.csv"}
    )

# ── Recommendations ────────────────────────────────────────────────────


@app.route("/recommendations")
def recommendations():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM subscriptions")
    subs = cur.fetchall()
    cur.close()
    conn.close()

    recommendations = []
    total_savings = 0

    for s in subs:
        monthly = float(
            s["cost"]) / 12 if s["billing_cycle"] == "Annual" else float(s["cost"])

        # underused seats recommendation
        if s["seats_paid"] and s["seats_used"] is not None:
            seats_paid = float(s["seats_paid"])
            seats_used = float(s["seats_used"])
            usage_pct = (seats_used / seats_paid) * 100

            if usage_pct < 30:
                savings = monthly
                recommendations.append({
                    "tool": s["tool_name"],
                    "type": "Cancel",
                    "reason": f"Only {usage_pct:.0f}% of seats are being used. Consider cancelling entirely.",
                    "saving": round(savings, 2),
                    "severity": "red"
                })
                total_savings += savings

            elif usage_pct < 50:
                unused = seats_paid - seats_used
                savings = (unused / seats_paid) * monthly
                recommendations.append({
                    "tool": s["tool_name"],
                    "type": "Downgrade",
                    "reason": f"Only {usage_pct:.0f}% of seats used. Downgrade from {int(seats_paid)} to {int(seats_used)} seats and save ${savings:.0f}/month.",
                    "saving": round(savings, 2),
                    "severity": "orange"
                })
                total_savings += savings

        # renewal coming up - flag for review
        if s["renewal_date"]:
            days_left = (s["renewal_date"] - date.today()).days
            if 0 <= days_left <= 14:
                recommendations.append({
                    "tool": s["tool_name"],
                    "type": "Review Before Renewal",
                    "reason": f"Renews in {days_left} days. Review usage before auto-renewing.",
                    "saving": None,
                    "severity": "orange"
                })

    # overlap detection - same category, multiple tools
    cur = conn.cursor() if not conn.closed else get_connection().cursor()
    conn2 = get_connection()
    cur2 = conn2.cursor()
    cur2.execute("""
        SELECT category, STRING_AGG(tool_name, ', ') as tools, COUNT(*) as cnt
        FROM subscriptions
        GROUP BY category
        HAVING COUNT(*) > 1
    """)
    overlaps = cur2.fetchall()
    cur2.close()
    conn2.close()

    for o in overlaps:
        recommendations.append({
            "tool": o["tools"],
            "type": "Consolidate",
            "reason": f"You have {o['cnt']} tools in {o['category']}: {o['tools']}. Consider consolidating into one.",
            "saving": None,
            "severity": "red"
        })

    return render_template("recommendations.html",
                           recommendations=recommendations,
                           total_savings=round(total_savings, 2)
                           )


if __name__ == "__main__":
    app.run(debug=True)
