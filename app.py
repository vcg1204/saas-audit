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

# ── Health Score ───────────────────────────────────────────────────────


@app.route("/health")
def health():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM subscriptions")
    subs = cur.fetchall()
    cur.close()
    conn.close()

    scored = []
    for s in subs:
        score = 0
        breakdown = []

        # seat usage score (50 points)
        if s["seats_paid"] and s["seats_used"] is not None:
            usage_pct = float(s["seats_used"]) / float(s["seats_paid"])
            seat_score = round(usage_pct * 50)
            score += seat_score
            breakdown.append(f"Seat usage: {seat_score}/50")
        else:
            score += 25
            breakdown.append("Seat usage: 25/50 (no data)")

        # cost efficiency score (30 points)
        if s["seats_used"] and float(s["seats_used"]) > 0:
            monthly = float(
                s["cost"]) / 12 if s["billing_cycle"] == "Annual" else float(s["cost"])
            cost_per_seat = monthly / float(s["seats_used"])
            if cost_per_seat < 10:
                cost_score = 30
            elif cost_per_seat < 25:
                cost_score = 20
            elif cost_per_seat < 50:
                cost_score = 10
            else:
                cost_score = 5
            score += cost_score
            breakdown.append(f"Cost efficiency: {cost_score}/30")
        else:
            score += 15
            breakdown.append("Cost efficiency: 15/30 (no data)")

        # renewal safety score (20 points)
        if s["renewal_date"]:
            days_left = (s["renewal_date"] - date.today()).days
            if days_left > 90:
                renewal_score = 20
            elif days_left > 30:
                renewal_score = 15
            elif days_left > 14:
                renewal_score = 10
            elif days_left > 7:
                renewal_score = 5
            else:
                renewal_score = 0
            score += renewal_score
            breakdown.append(f"Renewal safety: {renewal_score}/20")
        else:
            score += 10
            breakdown.append("Renewal safety: 10/20 (no data)")

        if score >= 70:
            status = "Healthy"
            status_color = "green"
        elif score >= 40:
            status = "Needs Attention"
            status_color = "orange"
        else:
            status = "At Risk"
            status_color = "red"

        scored.append({
            "tool": s["tool_name"],
            "category": s["category"],
            "score": score,
            "status": status,
            "status_color": status_color,
            "breakdown": " | ".join(breakdown)
        })

    scored.sort(key=lambda x: x["score"])

    return render_template("health.html", scored=scored)

# ── Budget vs Actual ───────────────────────────────────────────────────


@app.route("/budget", methods=["GET", "POST"])
def budget():
    conn = get_connection()
    cur = conn.cursor()

    if request.method == "POST":
        new_budget = request.form["monthly_budget"]
        cur.execute(
            "UPDATE budget SET monthly_budget=%s, updated_at=CURRENT_TIMESTAMP WHERE id=1", (new_budget,))
        conn.commit()

    cur.execute("SELECT monthly_budget FROM budget WHERE id=1")
    budget_row = cur.fetchone()
    monthly_budget = float(budget_row["monthly_budget"])

    cur.execute("SELECT * FROM subscriptions")
    subs = cur.fetchall()

    actual_spend = 0
    for s in subs:
        if s["billing_cycle"] == "Annual":
            actual_spend += float(s["cost"]) / 12
        else:
            actual_spend += float(s["cost"])

    actual_spend = round(actual_spend, 2)
    remaining = round(monthly_budget - actual_spend, 2)
    usage_pct = round((actual_spend / monthly_budget) *
                      100, 1) if monthly_budget > 0 else 0

    if usage_pct >= 100:
        status = "Over Budget"
        status_color = "#e74c3c"
    elif usage_pct >= 80:
        status = "Near Limit"
        status_color = "#e67e22"
    else:
        status = "On Track"
        status_color = "#27ae60"

    # monthly breakdown per tool
    breakdown = []
    for s in subs:
        monthly = float(
            s["cost"]) / 12 if s["billing_cycle"] == "Annual" else float(s["cost"])
        pct_of_budget = round((monthly / monthly_budget)
                              * 100, 1) if monthly_budget > 0 else 0
        breakdown.append({
            "tool": s["tool_name"],
            "category": s["category"],
            "monthly": round(monthly, 2),
            "pct_of_budget": pct_of_budget
        })

    breakdown.sort(key=lambda x: x["monthly"], reverse=True)

    cur.close()
    conn.close()

    return render_template("budget.html",
                           monthly_budget=monthly_budget,
                           actual_spend=actual_spend,
                           remaining=remaining,
                           usage_pct=usage_pct,
                           status=status,
                           status_color=status_color,
                           breakdown=breakdown
                           )


if __name__ == "__main__":
    app.run(debug=True)
