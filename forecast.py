"""
CashPilot Forecast & Simulation Engine
Calculates 30, 60, and 90-day cash flow projections and runs
interactive What-If delay scenarios for independent home tutors.
"""

from datetime import date, datetime, timedelta
import sqlite3
from database import get_db_connection


def calculate_cash_forecast(db=None):
    """
    Computes a comprehensive cash flow forecast for 30, 60, and 90 days.
    Integrates current cash balance, pending invoices, recurring student fees,
    and scheduled expenses.
    """
    close_db = False
    if db is None:
        db = get_db_connection()
        close_db = True

    today = date.today()

    # 1. Fetch current settings (starting balance, safety buffer, currency)
    settings = db.execute("SELECT * FROM settings WHERE id = 1").fetchone()
    starting_balance = float(settings["starting_cash_balance"]) if settings else 2450.0
    safety_buffer = float(settings["min_safety_buffer"]) if settings else 1000.0
    currency = settings["currency_symbol"] if settings else "$"

    # 2. Fetch all unpaid invoices (Pending and Overdue)
    unpaid_invoices_rows = db.execute("""
        SELECT i.id, i.invoice_number, i.amount, i.due_date, i.status, s.name as student_name
        FROM invoices i
        JOIN students s ON i.student_id = s.id
        WHERE i.status IN ('Pending', 'Overdue')
        ORDER BY i.due_date ASC
    """).fetchall()

    unpaid_invoices = [dict(row) for row in unpaid_invoices_rows]

    # 3. Fetch active students for future cycle projections (months 2 and 3)
    active_students_rows = db.execute("""
        SELECT id, name, monthly_fee, billing_day
        FROM students
        WHERE status = 'Active'
    """).fetchall()
    active_students = [dict(row) for row in active_students_rows]

    # 4. Fetch pending expenses
    pending_expenses_rows = db.execute("""
        SELECT id, title, category, amount, due_date
        FROM expenses
        WHERE status = 'Pending'
        ORDER BY due_date ASC
    """).fetchall()
    pending_expenses = [dict(row) for row in pending_expenses_rows]

    # 5. Fetch recurring monthly expense average (from both paid and pending to estimate months 2 and 3)
    monthly_recurring_expenses = db.execute("""
        SELECT COALESCE(SUM(amount), 0) as total_expenses
        FROM expenses
    """).fetchone()["total_expenses"]
    # Estimate base recurring monthly overhead if specific future expenses are not yet logged
    estimated_monthly_overhead = max(180.0, float(monthly_recurring_expenses) * 0.5)

    # 6. Build 90-day daily cash trajectory
    # Create daily events for inflows and outflows
    daily_inflows = {today + timedelta(days=i): 0.0 for i in range(91)}
    daily_outflows = {today + timedelta(days=i): 0.0 for i in range(91)}

    # Map unpaid invoices to inflow days
    for inv in unpaid_invoices:
        inv_due = datetime.strptime(inv["due_date"], "%Y-%m-%d").date()
        # If invoice is overdue, assume expected payment within 2 days from today
        expected_date = today + timedelta(days=2) if inv_due < today else inv_due
        if expected_date in daily_inflows:
            daily_inflows[expected_date] += float(inv["amount"])

    # Project future monthly student billings for Days 31-90
    # For day 31 to 90, active students will be billed on their billing_day
    for student in active_students:
        fee = float(student["monthly_fee"])
        b_day = int(student["billing_day"])
        for day_offset in range(1, 91):
            check_date = today + timedelta(days=day_offset)
            # If day_offset > 28, consider recurring monthly fee on student billing day
            if day_offset > 28 and check_date.day == min(b_day, 28):
                daily_inflows[check_date] += fee

    # Map pending expenses to outflow days
    for exp in pending_expenses:
        exp_due = datetime.strptime(exp["due_date"], "%Y-%m-%d").date()
        expected_date = today if exp_due < today else exp_due
        if expected_date in daily_outflows:
            daily_outflows[expected_date] += float(exp["amount"])

    # For days 31-90, add smoothed recurring overhead (e.g. utilities, software renewal)
    overhead_per_day = estimated_monthly_overhead / 30.0
    for day_offset in range(31, 91):
        check_date = today + timedelta(days=day_offset)
        daily_outflows[check_date] += overhead_per_day

    # Calculate cumulative daily cash balance trajectory
    timeline = []
    current_bal = starting_balance
    min_balance = starting_balance
    min_balance_date = today.isoformat()

    day_30_balance = starting_balance
    day_60_balance = starting_balance
    day_90_balance = starting_balance

    total_inflows_30 = 0.0
    total_outflows_30 = 0.0
    total_inflows_60 = 0.0
    total_outflows_60 = 0.0
    total_inflows_90 = 0.0
    total_outflows_90 = 0.0

    for i in range(91):
        d = today + timedelta(days=i)
        inflow = daily_inflows[d]
        outflow = daily_outflows[d]
        current_bal = current_bal + inflow - outflow

        if current_bal < min_balance:
            min_balance = current_bal
            min_balance_date = d.isoformat()

        if i <= 30:
            total_inflows_30 += inflow
            total_outflows_30 += outflow
            if i == 30:
                day_30_balance = current_bal
        if i <= 60:
            total_inflows_60 += inflow
            total_outflows_60 += outflow
            if i == 60:
                day_60_balance = current_bal
        if i <= 90:
            total_inflows_90 += inflow
            total_outflows_90 += outflow
            if i == 90:
                day_90_balance = current_bal

        # Sample every 3-5 days for cleaner charts or include all key points
        timeline.append({
            "date": d.isoformat(),
            "day_index": i,
            "label": d.strftime("%b %d"),
            "balance": round(current_bal, 2),
            "inflow": round(inflow, 2),
            "outflow": round(outflow, 2),
            "safety_buffer": safety_buffer
        })

    # Health status evaluation
    if min_balance < 0:
        health_status = "Critical Deficit"
        health_badge = "danger"
    elif min_balance < safety_buffer:
        health_status = "Buffer Warning"
        health_badge = "warning"
    else:
        health_status = "Healthy Buffer"
        health_badge = "success"

    # Human-friendly explanation bullets
    explanations = [
        f"**30-Day Outlook**: Starting at {currency}{starting_balance:,.2f}, projected inflows of {currency}{total_inflows_30:,.2f} versus outflows of {currency}{total_outflows_30:,.2f} lead to a forecasted balance of **{currency}{day_30_balance:,.2f}**.",
        f"**Safety Reserve**: Your lowest projected balance across 90 days is **{currency}{min_balance:,.2f}** (on {min_balance_date}). {'This stays safely above your reserve.' if min_balance >= safety_buffer else f'Warning: Dips below your {currency}{safety_buffer:,.2f} emergency reserve.'}",
        f"**90-Day Trajectory**: Over 90 days, regular active student tuition brings total inflows to {currency}{total_inflows_90:,.2f}, generating a strong final balance of **{currency}{day_90_balance:,.2f}**."
    ]

    result = {
        "current_balance": round(starting_balance, 2),
        "safety_buffer": round(safety_buffer, 2),
        "currency": currency,
        "health_status": health_status,
        "health_badge": health_badge,
        "min_balance": round(min_balance, 2),
        "min_balance_date": min_balance_date,
        "day_30": {
            "projected_balance": round(day_30_balance, 2),
            "net_change": round(day_30_balance - starting_balance, 2),
            "inflows": round(total_inflows_30, 2),
            "outflows": round(total_outflows_30, 2)
        },
        "day_60": {
            "projected_balance": round(day_60_balance, 2),
            "net_change": round(day_60_balance - starting_balance, 2),
            "inflows": round(total_inflows_60, 2),
            "outflows": round(total_outflows_60, 2)
        },
        "day_90": {
            "projected_balance": round(day_90_balance, 2),
            "net_change": round(day_90_balance - starting_balance, 2),
            "inflows": round(total_inflows_90, 2),
            "outflows": round(total_outflows_90, 2)
        },
        "explanations": explanations,
        "timeline": timeline
    }

    if close_db:
        db.close()

    return result


def simulate_whatif_scenario(invoice_id, delay_days=15, unexpected_expense=0.0):
    """
    Simulates what happens when a specific student's payment is delayed by X days.
    Returns side-by-side comparison between the baseline cash flow and the delayed scenario.
    """
    db = get_db_connection()
    today = date.today()

    # 1. Fetch the target invoice
    invoice = db.execute("""
        SELECT i.*, s.name as student_name, s.parent_name
        FROM invoices i
        JOIN students s ON i.student_id = s.id
        WHERE i.id = ?
    """, (invoice_id,)).fetchone()

    if not invoice:
        db.close()
        return {"error": "Invoice not found"}

    target_inv = dict(invoice)
    amount = float(target_inv["amount"])

    # 2. Get baseline forecast
    base_forecast = calculate_cash_forecast(db)
    currency = base_forecast["currency"]
    safety_buffer = base_forecast["safety_buffer"]

    # 3. Compute modified inflows for the simulation
    # Original due date or expected payment date
    inv_due = datetime.strptime(target_inv["due_date"], "%Y-%m-%d").date()
    orig_date = today + timedelta(days=2) if inv_due < today else inv_due
    delayed_date = orig_date + timedelta(days=int(delay_days))

    # Reconstruct trajectory with the payment shifted
    base_timeline = base_forecast["timeline"]
    simulated_timeline = []

    current_sim_bal = base_forecast["current_balance"]
    min_sim_bal = current_sim_bal
    min_sim_date = today.isoformat()

    # Extract base timeline values and shift the target amount
    for item in base_timeline:
        d = datetime.strptime(item["date"], "%Y-%m-%d").date()
        inflow = item["inflow"]
        outflow = item["outflow"]

        # If today is original date, subtract target amount
        if d == orig_date:
            inflow = max(0.0, inflow - amount)

        # If today is the delayed date, add target amount
        if d == delayed_date:
            inflow = inflow + amount

        # If unexpected expense is specified and occurs on day 5:
        if unexpected_expense > 0 and d == today + timedelta(days=5):
            outflow += float(unexpected_expense)

        current_sim_bal = current_sim_bal + inflow - outflow

        if current_sim_bal < min_sim_bal:
            min_sim_bal = current_sim_bal
            min_sim_date = d.isoformat()

        simulated_timeline.append({
            "date": item["date"],
            "label": item["label"],
            "base_balance": item["balance"],
            "simulated_balance": round(current_sim_bal, 2),
            "difference": round(current_sim_bal - item["balance"], 2),
            "safety_buffer": safety_buffer
        })

    # Financial Impact Analysis
    max_liquidity_dip = round(amount, 2)
    buffer_breached = min_sim_bal < safety_buffer
    buffer_deficit = round(safety_buffer - min_sim_bal, 2) if buffer_breached else 0.0

    # Impact assessment
    if min_sim_bal < 0:
        severity = "High Risk - Cash Deficit"
        badge = "danger"
        action_text = f"CRITICAL: Delay of {currency}{amount:,.2f} creates an overdraft! Immediate follow-up with {target_inv['parent_name']} required. Postpone non-essential expenses."
    elif buffer_breached:
        severity = "Moderate - Buffer Breached"
        badge = "warning"
        action_text = f"WARNING: Delay dips cash below your {currency}{safety_buffer:,.2f} safety buffer by {currency}{buffer_deficit:,.2f} on {min_sim_date}. Send a polite reminder today."
    else:
        severity = "Low Risk - Buffer Safe"
        badge = "success"
        action_text = f"SAFE: Your safety reserve remains protected. You have adequate cash buffer to absorb a {delay_days}-day delay without missing any planned expenses."

    impact_summary = {
        "invoice_number": target_inv["invoice_number"],
        "student_name": target_inv["student_name"],
        "parent_name": target_inv["parent_name"],
        "amount": amount,
        "delay_days": int(delay_days),
        "original_payment_date": orig_date.isoformat(),
        "simulated_payment_date": delayed_date.isoformat(),
        "base_min_balance": base_forecast["min_balance"],
        "simulated_min_balance": round(min_sim_bal, 2),
        "simulated_min_date": min_sim_date,
        "severity": severity,
        "badge": badge,
        "buffer_breached": buffer_breached,
        "buffer_deficit": buffer_deficit,
        "max_cash_dip": max_liquidity_dip,
        "action_recommendation": action_text
    }

    db.close()

    return {
        "impact_summary": impact_summary,
        "timeline_comparison": simulated_timeline
    }


def generate_smart_alerts():
    """
    Scans the database for overdue invoices, invoices due today,
    upcoming bills in the next 7 days, and cash buffer risk triggers.
    Returns categorized actionable smart alerts.
    """
    db = get_db_connection()
    today = date.today()
    today_str = today.isoformat()
    next_week_str = (today + timedelta(days=7)).isoformat()

    alerts = []

    # 1. Overdue Invoices Alerts
    overdue_rows = db.execute("""
        SELECT i.id, i.invoice_number, i.amount, i.due_date, s.name as student_name, s.parent_name, s.parent_phone
        FROM invoices i
        JOIN students s ON i.student_id = s.id
        WHERE i.status = 'Overdue'
        ORDER BY i.due_date ASC
    """).fetchall()

    for row in overdue_rows:
        due = datetime.strptime(row["due_date"], "%Y-%m-%d").date()
        days_late = (today - due).days
        alerts.append({
            "type": "overdue_invoice",
            "level": "danger",
            "title": f"Overdue Payment: {row['student_name']}",
            "amount": float(row["amount"]),
            "message": f"Invoice #{row['invoice_number']} for ${row['amount']:,.2f} is {days_late} days past due.",
            "due_date": row["due_date"],
            "days_late": days_late,
            "target_id": row["id"],
            "student_name": row["student_name"],
            "parent_name": row["parent_name"],
            "parent_phone": row["parent_phone"],
            "action_type": "reminder",
            "action_label": "Generate Reminder"
        })

    # 2. Payments Due Today Alerts
    due_today_rows = db.execute("""
        SELECT i.id, i.invoice_number, i.amount, s.name as student_name, s.parent_name
        FROM invoices i
        JOIN students s ON i.student_id = s.id
        WHERE i.status = 'Pending' AND i.due_date = ?
    """, (today_str,)).fetchall()

    for row in due_today_rows:
        alerts.append({
            "type": "due_today",
            "level": "warning",
            "title": f"Fee Due Today: {row['student_name']}",
            "amount": float(row["amount"]),
            "message": f"${row['amount']:,.2f} tuition fee is scheduled for collection today.",
            "due_date": today_str,
            "target_id": row["id"],
            "student_name": row["student_name"],
            "action_type": "mark_paid",
            "action_label": "Record Payment"
        })

    # 3. Upcoming Expenses (Next 7 days)
    upcoming_expenses_rows = db.execute("""
        SELECT id, title, category, amount, due_date
        FROM expenses
        WHERE status = 'Pending' AND due_date BETWEEN ? AND ?
        ORDER BY due_date ASC
    """, (today_str, next_week_str)).fetchall()

    for row in upcoming_expenses_rows:
        alerts.append({
            "type": "upcoming_expense",
            "level": "info",
            "title": f"Upcoming Bill: {row['title']}",
            "amount": float(row["amount"]),
            "message": f"${row['amount']:,.2f} ({row['category']}) due on {row['due_date']}.",
            "due_date": row["due_date"],
            "target_id": row["id"],
            "action_type": "pay_expense",
            "action_label": "Pay Bill"
        })

    db.close()
    return alerts
