"""
CashPilot – The One-Person Business Back Office
Main Flask application serving REST API and responsive SaaS dashboard.
Designed for independent home tutors.
"""

import os
from datetime import date, datetime, timedelta
import urllib.parse
from flask import Flask, render_template, request, jsonify, send_from_directory

from database import init_db, get_db_connection, sync_invoice_statuses, seed_sample_data
from forecast import calculate_cash_forecast, simulate_whatif_scenario, generate_smart_alerts

# Initialize Flask application with absolute paths for Vercel/cloud serverless environments
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(
    __name__,
    static_folder=os.path.join(BASE_DIR, "static"),
    template_folder=os.path.join(BASE_DIR, "templates")
)
app.config["SECRET_KEY"] = "cashpilot-hackathon-2026-secret-key"

# Ensure database and sample data are ready at startup
init_db()


# -----------------------------------------------------------------------------
# Web Page Route
# -----------------------------------------------------------------------------

@app.route("/")
def index():
    """Renders the main CashPilot SaaS dashboard single-page interface."""
    # Sync statuses so any invoice past its due date becomes 'Overdue'
    sync_invoice_statuses()
    return render_template("index.html")


@app.route("/static/<path:filename>")
def custom_static(filename):
    """Explicit fallback for static assets in cloud serverless deployments."""
    return send_from_directory(os.path.join(BASE_DIR, "static"), filename)


@app.route("/favicon.ico")
def favicon():
    """Serves the SVG favicon for browsers requesting standard favicon.ico."""
    return send_from_directory(
        os.path.join(BASE_DIR, "static"),
        "favicon.svg",
        mimetype="image/svg+xml"
    )


# -----------------------------------------------------------------------------
# 1. Dashboard API
# -----------------------------------------------------------------------------

@app.route("/api/dashboard", methods=["GET"])
def get_dashboard_data():
    """
    Returns high-level KPI metrics, financial summary, and monthly
    income vs expense chart dataset.
    """
    sync_invoice_statuses()
    db = get_db_connection()
    today = date.today()

    # Settings & Cash balance
    settings = db.execute("SELECT * FROM settings WHERE id = 1").fetchone()
    current_cash = float(settings["starting_cash_balance"]) if settings else 2450.0
    currency = settings["currency_symbol"] if settings else "$"
    safety_buffer = float(settings["min_safety_buffer"]) if settings else 1000.0

    # Total Outstanding Payments (Pending + Overdue)
    outstanding_row = db.execute("""
        SELECT COALESCE(SUM(amount), 0) as total, COUNT(*) as count
        FROM invoices
        WHERE status IN ('Pending', 'Overdue')
    """).fetchone()
    total_outstanding = float(outstanding_row["total"])
    outstanding_count = int(outstanding_row["count"])

    # Total Money Collected (Paid invoices)
    collected_row = db.execute("""
        SELECT COALESCE(SUM(amount), 0) as total, COUNT(*) as count
        FROM invoices
        WHERE status = 'Paid'
    """).fetchone()
    total_collected = float(collected_row["total"])
    collected_count = int(collected_row["count"])

    # Overdue Invoices
    overdue_row = db.execute("""
        SELECT COALESCE(SUM(amount), 0) as total, COUNT(*) as count
        FROM invoices
        WHERE status = 'Overdue'
    """).fetchone()
    total_overdue = float(overdue_row["total"])
    overdue_count = int(overdue_row["count"])

    # Upcoming Bills / Expenses (Pending expenses)
    upcoming_bills_row = db.execute("""
        SELECT COALESCE(SUM(amount), 0) as total, COUNT(*) as count
        FROM expenses
        WHERE status = 'Pending'
    """).fetchone()
    total_upcoming_bills = float(upcoming_bills_row["total"])
    upcoming_bills_count = int(upcoming_bills_row["count"])

    # Paid expenses total
    paid_expenses_row = db.execute("""
        SELECT COALESCE(SUM(amount), 0) as total
        FROM expenses
        WHERE status = 'Paid'
    """).fetchone()
    total_paid_expenses = float(paid_expenses_row["total"])

    # Expected Cash Balance:
    # Current cash on hand + expected tuition collections - upcoming scheduled bills
    expected_cash_balance = current_cash + total_outstanding - total_upcoming_bills

    # Monthly Income & Expenses for Chart (last 6 calendar months)
    # Generate month labels from 5 months ago to current month
    chart_months = []
    month_labels = []
    income_data = []
    expense_data = []

    # Current year and month
    curr_year = today.year
    curr_month = today.month

    for offset in range(5, -1, -1):
        m = curr_month - offset
        y = curr_year
        while m <= 0:
            m += 12
            y -= 1
        month_str = f"{y:04d}-{m:02d}"
        month_label = datetime(y, m, 1).strftime("%b %Y")
        chart_months.append(month_str)
        month_labels.append(month_label)

        # Monthly income (paid invoices in that month)
        inc_res = db.execute("""
            SELECT COALESCE(SUM(amount), 0) as total
            FROM invoices
            WHERE status = 'Paid' AND strftime('%Y-%m', paid_date) = ?
        """, (month_str,)).fetchone()["total"]

        # Monthly expense (paid expenses in that month)
        exp_res = db.execute("""
            SELECT COALESCE(SUM(amount), 0) as total
            FROM expenses
            WHERE status = 'Paid' AND strftime('%Y-%m', paid_date) = ?
        """, (month_str,)).fetchone()["total"]

        income_data.append(round(float(inc_res), 2))
        expense_data.append(round(float(exp_res), 2))

    # Recent Transactions / Activity feed (latest 5 events)
    recent_invoices = db.execute("""
        SELECT i.id, i.invoice_number, i.amount, i.due_date, i.status, i.paid_date, s.name as student_name
        FROM invoices i
        JOIN students s ON i.student_id = s.id
        ORDER BY i.created_at DESC
        LIMIT 5
    """).fetchall()

    recent_activity = [dict(row) for row in recent_invoices]

    db.close()

    return jsonify({
        "current_cash_balance": round(current_cash, 2),
        "expected_cash_balance": round(expected_cash_balance, 2),
        "total_outstanding": round(total_outstanding, 2),
        "outstanding_count": outstanding_count,
        "total_collected": round(total_collected, 2),
        "collected_count": collected_count,
        "total_overdue": round(total_overdue, 2),
        "overdue_count": overdue_count,
        "upcoming_bills": round(total_upcoming_bills, 2),
        "upcoming_bills_count": upcoming_bills_count,
        "total_paid_expenses": round(total_paid_expenses, 2),
        "safety_buffer": round(safety_buffer, 2),
        "currency": currency,
        "chart": {
            "labels": month_labels,
            "income": income_data,
            "expenses": expense_data
        },
        "recent_activity": recent_activity
    })


# -----------------------------------------------------------------------------
# 2. Student Management API
# -----------------------------------------------------------------------------

@app.route("/api/students", methods=["GET"])
def list_students():
    """Returns all students with calculated fee payment status, search & filter."""
    sync_invoice_statuses()
    query = request.args.get("q", "").strip().lower()
    status_filter = request.args.get("status", "All").strip()

    db = get_db_connection()
    sql = """
        SELECT s.*,
               COALESCE((SELECT COUNT(*) FROM invoices i WHERE i.student_id = s.id AND i.status = 'Overdue'), 0) as overdue_invoices_count,
               COALESCE((SELECT COUNT(*) FROM invoices i WHERE i.student_id = s.id AND i.status = 'Pending'), 0) as pending_invoices_count,
               COALESCE((SELECT SUM(amount) FROM invoices i WHERE i.student_id = s.id AND i.status IN ('Pending', 'Overdue')), 0) as total_due
        FROM students s
        WHERE 1=1
    """
    params = []

    if status_filter in ("Active", "Inactive"):
        sql += " AND s.status = ?"
        params.append(status_filter)

    if query:
        sql += """ AND (
            LOWER(s.name) LIKE ? OR
            LOWER(s.parent_name) LIKE ? OR
            LOWER(s.parent_phone) LIKE ? OR
            LOWER(s.subject_grade) LIKE ?
        )"""
        params.extend([f"%{query}%"] * 4)

    sql += " ORDER BY s.name ASC"
    rows = db.execute(sql, params).fetchall()

    students = []
    for row in rows:
        item = dict(row)
        # Determine human-friendly payment health badge
        if item["overdue_invoices_count"] > 0:
            item["payment_status"] = "Overdue"
            item["payment_badge"] = "danger"
        elif item["pending_invoices_count"] > 0:
            item["payment_status"] = "Pending Due"
            item["payment_badge"] = "warning"
        else:
            item["payment_status"] = "Paid / Current"
            item["payment_badge"] = "success"

        students.append(item)

    db.close()
    return jsonify(students)


@app.route("/api/students", methods=["POST"])
def create_student():
    """Adds a new student with input validation."""
    data = request.get_json() or {}

    # Validation
    name = data.get("name", "").strip()
    subject_grade = data.get("subject_grade", "").strip()
    parent_name = data.get("parent_name", "").strip()
    parent_phone = data.get("parent_phone", "").strip()
    parent_email = data.get("parent_email", "").strip()
    notes = data.get("notes", "").strip()
    status = data.get("status", "Active").strip()

    try:
        monthly_fee = float(data.get("monthly_fee", 0))
        if monthly_fee <= 0:
            return jsonify({"error": "Monthly tuition fee must be greater than 0"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid monthly tuition fee value"}), 400

    try:
        billing_day = int(data.get("billing_day", 1))
        if not (1 <= billing_day <= 31):
            billing_day = 1
    except (ValueError, TypeError):
        billing_day = 1

    if not name or not parent_name or not parent_phone or not subject_grade:
        return jsonify({"error": "Please provide student name, subject/grade, parent name, and contact phone"}), 400

    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO students (name, subject_grade, parent_name, parent_phone, parent_email, monthly_fee, billing_day, status, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, subject_grade, parent_name, parent_phone, parent_email, monthly_fee, billing_day, status, notes))
    student_id = cursor.lastrowid
    db.commit()
    db.close()

    return jsonify({"success": True, "id": student_id, "message": f"Student '{name}' added successfully"}), 201


@app.route("/api/students/<int:student_id>", methods=["GET"])
def get_student(student_id):
    """Retrieves single student detail with full invoice fee history."""
    db = get_db_connection()
    student = db.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    if not student:
        db.close()
        return jsonify({"error": "Student not found"}), 404

    invoices = db.execute("""
        SELECT * FROM invoices
        WHERE student_id = ?
        ORDER BY due_date DESC
    """, (student_id,)).fetchall()

    student_data = dict(student)
    student_data["invoices"] = [dict(inv) for inv in invoices]
    student_data["total_billed"] = sum(float(inv["amount"]) for inv in invoices)
    student_data["total_paid"] = sum(float(inv["amount"]) for inv in invoices if inv["status"] == "Paid")
    student_data["total_pending"] = sum(float(inv["amount"]) for inv in invoices if inv["status"] in ("Pending", "Overdue"))

    db.close()
    return jsonify(student_data)


@app.route("/api/students/<int:student_id>", methods=["PUT"])
def update_student(student_id):
    """Updates an existing student."""
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    subject_grade = data.get("subject_grade", "").strip()
    parent_name = data.get("parent_name", "").strip()
    parent_phone = data.get("parent_phone", "").strip()
    parent_email = data.get("parent_email", "").strip()
    notes = data.get("notes", "").strip()
    status = data.get("status", "Active").strip()

    try:
        monthly_fee = float(data.get("monthly_fee", 0))
        billing_day = int(data.get("billing_day", 1))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid fee or billing day format"}), 400

    if not name or not parent_name or not parent_phone:
        return jsonify({"error": "Required fields missing"}), 400

    db = get_db_connection()
    db.execute("""
        UPDATE students
        SET name = ?, subject_grade = ?, parent_name = ?, parent_phone = ?, parent_email = ?,
            monthly_fee = ?, billing_day = ?, status = ?, notes = ?
        WHERE id = ?
    """, (name, subject_grade, parent_name, parent_phone, parent_email, monthly_fee, billing_day, status, notes, student_id))
    db.commit()
    db.close()

    return jsonify({"success": True, "message": f"Student '{name}' updated successfully"})


@app.route("/api/students/<int:student_id>", methods=["DELETE"])
def delete_student(student_id):
    """Deletes student and associated invoices."""
    db = get_db_connection()
    db.execute("DELETE FROM students WHERE id = ?", (student_id,))
    db.commit()
    db.close()
    return jsonify({"success": True, "message": "Student removed successfully"})


# -----------------------------------------------------------------------------
# 3. Invoice Management API
# -----------------------------------------------------------------------------

def generate_next_invoice_number(db):
    """Auto-generates a clean sequential invoice number, e.g. INV-2026-108."""
    year = date.today().year
    row = db.execute("SELECT invoice_number FROM invoices ORDER BY id DESC LIMIT 1").fetchone()
    if row and row["invoice_number"]:
        try:
            parts = row["invoice_number"].split("-")
            seq = int(parts[-1]) + 1
            return f"INV-{year}-{seq:03d}"
        except Exception:
            pass
    return f"INV-{year}-101"


@app.route("/api/invoices", methods=["GET"])
def list_invoices():
    """Returns invoices with filtering by status and search by student/invoice #."""
    sync_invoice_statuses()
    status_filter = request.args.get("status", "All").strip()
    student_id = request.args.get("student_id", "").strip()
    query = request.args.get("q", "").strip().lower()

    db = get_db_connection()
    sql = """
        SELECT i.*, s.name as student_name, s.parent_name, s.parent_phone, s.parent_email, s.subject_grade
        FROM invoices i
        JOIN students s ON i.student_id = s.id
        WHERE 1=1
    """
    params = []

    if status_filter in ("Paid", "Pending", "Overdue"):
        sql += " AND i.status = ?"
        params.append(status_filter)

    if student_id and student_id.isdigit():
        sql += " AND i.student_id = ?"
        params.append(int(student_id))

    if query:
        sql += """ AND (
            LOWER(i.invoice_number) LIKE ? OR
            LOWER(s.name) LIKE ? OR
            LOWER(s.parent_name) LIKE ? OR
            LOWER(i.description) LIKE ?
        )"""
        params.extend([f"%{query}%"] * 4)

    sql += " ORDER BY i.due_date DESC, i.id DESC"
    rows = db.execute(sql, params).fetchall()

    invoices = [dict(row) for row in rows]
    db.close()
    return jsonify(invoices)


@app.route("/api/invoices", methods=["POST"])
def create_invoice():
    """Creates a new invoice with auto-generated sequential number and validation."""
    data = request.get_json() or {}

    student_id = data.get("student_id")
    description = data.get("description", "").strip()
    issue_date = data.get("issue_date", date.today().isoformat()).strip()
    due_date = data.get("due_date", "").strip()
    notes = data.get("notes", "").strip()

    try:
        student_id = int(student_id)
        amount = float(data.get("amount", 0))
        if amount <= 0:
            return jsonify({"error": "Invoice amount must be greater than 0"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid student ID or amount"}), 400

    if not due_date:
        return jsonify({"error": "Due date is required"}), 400

    db = get_db_connection()

    # Check student existence
    student = db.execute("SELECT id, name FROM students WHERE id = ?", (student_id,)).fetchone()
    if not student:
        db.close()
        return jsonify({"error": "Selected student does not exist"}), 400

    # Auto-generate invoice number if not provided
    invoice_number = data.get("invoice_number", "").strip()
    if not invoice_number:
        invoice_number = generate_next_invoice_number(db)

    # Calculate initial status (Overdue if due date < today)
    status = "Pending"
    if due_date < date.today().isoformat():
        status = "Overdue"

    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO invoices (invoice_number, student_id, amount, issue_date, due_date, status, description, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (invoice_number, student_id, amount, issue_date, due_date, status, description, notes))
    db.commit()
    inv_id = cursor.lastrowid
    db.close()

    return jsonify({
        "success": True,
        "id": inv_id,
        "invoice_number": invoice_number,
        "message": f"Invoice {invoice_number} created successfully!"
    }), 201


@app.route("/api/invoices/<int:invoice_id>/pay", methods=["POST"])
def mark_invoice_as_paid(invoice_id):
    """Marks an invoice as Paid, recording paid_date and payment_method."""
    data = request.get_json() or {}
    paid_date = data.get("paid_date", date.today().isoformat()).strip()
    payment_method = data.get("payment_method", "Bank Transfer").strip()
    notes = data.get("notes", "").strip()

    db = get_db_connection()
    inv = db.execute("SELECT invoice_number, amount FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
    if not inv:
        db.close()
        return jsonify({"error": "Invoice not found"}), 404

    db.execute("""
        UPDATE invoices
        SET status = 'Paid', paid_date = ?, payment_method = ?, notes = COALESCE(NULLIF(?, ''), notes)
        WHERE id = ?
    """, (paid_date, payment_method, notes, invoice_id))
    db.commit()
    db.close()

    return jsonify({
        "success": True,
        "message": f"Invoice {inv['invoice_number']} for ${inv['amount']:,.2f} marked as Paid via {payment_method}."
    })


@app.route("/api/invoices/<int:invoice_id>", methods=["GET"])
def get_invoice_details(invoice_id):
    """Retrieves full invoice details with tutor business profile for printable view."""
    db = get_db_connection()
    row = db.execute("""
        SELECT i.*, s.name as student_name, s.parent_name, s.parent_phone, s.parent_email, s.subject_grade
        FROM invoices i
        JOIN students s ON i.student_id = s.id
        WHERE i.id = ?
    """, (invoice_id,)).fetchone()

    if not row:
        db.close()
        return jsonify({"error": "Invoice not found"}), 404

    settings = db.execute("SELECT * FROM settings WHERE id = 1").fetchone()
    inv_dict = dict(row)
    inv_dict["tutor_profile"] = dict(settings) if settings else {}

    db.close()
    return jsonify(inv_dict)


@app.route("/api/invoices/<int:invoice_id>", methods=["DELETE"])
def delete_invoice(invoice_id):
    """Deletes an invoice."""
    db = get_db_connection()
    db.execute("DELETE FROM invoices WHERE id = ?", (invoice_id,))
    db.commit()
    db.close()
    return jsonify({"success": True, "message": "Invoice deleted successfully"})


# -----------------------------------------------------------------------------
# 4. Payment Reminders API
# -----------------------------------------------------------------------------

@app.route("/api/reminders/generate", methods=["GET"])
def generate_payment_reminder():
    """
    Generates polite, customizable reminder messages.
    Includes student name, parent name, amount, due date, payment instructions,
    and a ready-to-click WhatsApp deep link.
    """
    invoice_id = request.args.get("invoice_id")
    template_type = request.args.get("template", "friendly").lower()

    if not invoice_id:
        return jsonify({"error": "Invoice ID is required"}), 400

    db = get_db_connection()
    row = db.execute("""
        SELECT i.*, s.name as student_name, s.parent_name, s.parent_phone, s.subject_grade
        FROM invoices i
        JOIN students s ON i.student_id = s.id
        WHERE i.id = ?
    """, (invoice_id,)).fetchone()

    settings = db.execute("SELECT * FROM settings WHERE id = 1").fetchone()
    db.close()

    if not row:
        return jsonify({"error": "Invoice not found"}), 404

    tutor_name = settings["tutor_name"] if settings else "Alex Morgan"
    payment_info = settings["payment_info"] if settings else "Zelle / Bank Transfer"
    currency = settings["currency_symbol"] if settings else "$"

    student_name = row["student_name"]
    parent_name = row["parent_name"]
    amount_str = f"{currency}{row['amount']:,.2f}"
    due_date = row["due_date"]
    inv_num = row["invoice_number"]
    phone = row["parent_phone"].replace(" ", "").replace("-", "").replace("(", "").replace(")", "")

    # Clean date representation
    try:
        due_obj = datetime.strptime(due_date, "%Y-%m-%d")
        due_formatted = due_obj.strftime("%B %d, %Y")
    except Exception:
        due_formatted = due_date

    # Craft polite reminder messages
    if template_type == "due_today":
        subject = f"Friendly Reminder: {student_name}'s Tuition Due Today"
        body = (
            f"Hi {parent_name}, hope you're having a wonderful week! 😊\n\n"
            f"This is a quick friendly reminder that {student_name}'s tuition fee of {amount_str} "
            f"for {row['subject_grade']} (Invoice #{inv_num}) is scheduled for today, {due_formatted}.\n\n"
            f"Payment Options:\n{payment_info}\n\n"
            f"Please let me know once completed. Thank you so much for your continued support!\n\n"
            f"Warm regards,\n{tutor_name}"
        )
    elif template_type == "overdue":
        subject = f"Gentle Follow-Up: Overdue Fee for {student_name}"
        body = (
            f"Hello {parent_name},\n\n"
            f"I hope you're doing well. Just reaching out regarding invoice #{inv_num} for {student_name} "
            f"({row['subject_grade']}) in the amount of {amount_str}, which was due on {due_formatted}.\n\n"
            f"If you've already sent this, please kindly ignore this note! Otherwise, you can easily settle via:\n"
            f"{payment_info}\n\n"
            f"If you need any adjustments or have questions about the sessions, please feel free to text or call me.\n\n"
            f"Thank you,\n{tutor_name}"
        )
    elif template_type == "formal":
        subject = f"Invoice Statement #{inv_num} - {student_name}"
        body = (
            f"Dear {parent_name},\n\n"
            f"Please find below the tuition invoice summary for {student_name}:\n"
            f"• Invoice: #{inv_num}\n"
            f"• Course: {row['subject_grade']}\n"
            f"• Amount Due: {amount_str}\n"
            f"• Due Date: {due_formatted}\n\n"
            f"Settlement Instructions:\n{payment_info}\n\n"
            f"Thank you for partnering in {student_name}'s academic progress.\n\n"
            f"Sincerely,\n{tutor_name}"
        )
    else:  # 'friendly' default
        subject = f"Upcoming Tuition Reminder for {student_name}"
        body = (
            f"Hi {parent_name}! Hope you and {student_name} are having a great week! 🌟\n\n"
            f"{student_name} has been doing wonderful work in our tutoring sessions. "
            f"This is a gentle heads-up that invoice #{inv_num} for {amount_str} is due on {due_formatted}.\n\n"
            f"Payment Details:\n{payment_info}\n\n"
            f"Thank you as always for your support!\n\n"
            f"Best,\n{tutor_name}"
        )

    # Build WhatsApp URL
    encoded_text = urllib.parse.quote(body)
    whatsapp_url = f"https://wa.me/{phone}?text={encoded_text}" if phone else f"https://wa.me/?text={encoded_text}"

    return jsonify({
        "invoice_id": row["id"],
        "invoice_number": inv_num,
        "student_name": student_name,
        "parent_name": parent_name,
        "parent_phone": row["parent_phone"],
        "amount": row["amount"],
        "due_date": due_date,
        "template": template_type,
        "subject": subject,
        "body": body,
        "whatsapp_url": whatsapp_url
    })


# -----------------------------------------------------------------------------
# 5. Cash Flow Forecast API
# -----------------------------------------------------------------------------

@app.route("/api/forecast", methods=["GET"])
def get_cash_forecast():
    """Returns 30, 60, and 90-day cash flow projections and charts."""
    sync_invoice_statuses()
    forecast = calculate_cash_forecast()
    return jsonify(forecast)


# -----------------------------------------------------------------------------
# 6. What-If Scenario Simulator API
# -----------------------------------------------------------------------------

@app.route("/api/whatif", methods=["POST"])
def run_whatif_scenario():
    """
    Simulates late payment on an unpaid invoice and computes
    impact on cash liquidity and safety buffer.
    """
    sync_invoice_statuses()
    data = request.get_json() or {}

    invoice_id = data.get("invoice_id")
    delay_days = data.get("delay_days", 15)
    unexpected_expense = float(data.get("unexpected_expense", 0.0))

    if not invoice_id:
        return jsonify({"error": "Please select an unpaid invoice to simulate"}), 400

    result = simulate_whatif_scenario(invoice_id, delay_days, unexpected_expense)
    if "error" in result:
        return jsonify(result), 404

    return jsonify(result)


# -----------------------------------------------------------------------------
# 7. Smart Alerts API
# -----------------------------------------------------------------------------

@app.route("/api/alerts", methods=["GET"])
def get_smart_alerts():
    """Returns detected overdue payments, payments due today, and upcoming bills."""
    sync_invoice_statuses()
    alerts = generate_smart_alerts()
    return jsonify(alerts)


# -----------------------------------------------------------------------------
# 8. Expense Management API
# -----------------------------------------------------------------------------

@app.route("/api/expenses", methods=["GET"])
def list_expenses():
    """Returns expenses with category and status filtering."""
    category_filter = request.args.get("category", "All").strip()
    status_filter = request.args.get("status", "All").strip()
    query = request.args.get("q", "").strip().lower()

    db = get_db_connection()
    sql = "SELECT * FROM expenses WHERE 1=1"
    params = []

    if category_filter != "All":
        sql += " AND category = ?"
        params.append(category_filter)

    if status_filter in ("Paid", "Pending"):
        sql += " AND status = ?"
        params.append(status_filter)

    if query:
        sql += " AND (LOWER(title) LIKE ? OR LOWER(category) LIKE ?)"
        params.extend([f"%{query}%", f"%{query}%"])

    sql += " ORDER BY due_date DESC, id DESC"
    rows = db.execute(sql, params).fetchall()

    expenses = [dict(row) for row in rows]
    db.close()
    return jsonify(expenses)


@app.route("/api/expenses", methods=["POST"])
def create_expense():
    """Creates a new overhead expense."""
    data = request.get_json() or {}
    title = data.get("title", "").strip()
    category = data.get("category", "Teaching Materials").strip()
    due_date = data.get("due_date", date.today().isoformat()).strip()
    notes = data.get("notes", "").strip()
    status = data.get("status", "Pending").strip()

    try:
        amount = float(data.get("amount", 0))
        if amount <= 0:
            return jsonify({"error": "Expense amount must be greater than 0"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid amount value"}), 400

    if not title or not category:
        return jsonify({"error": "Expense title and category are required"}), 400

    paid_date = date.today().isoformat() if status == "Paid" else None

    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO expenses (title, category, amount, due_date, status, paid_date, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (title, category, amount, due_date, status, paid_date, notes))
    exp_id = cursor.lastrowid
    db.commit()
    db.close()

    return jsonify({"success": True, "id": exp_id, "message": f"Expense '{title}' recorded successfully!"}), 201


@app.route("/api/expenses/<int:expense_id>/pay", methods=["POST"])
def mark_expense_as_paid(expense_id):
    """Marks an expense as paid."""
    data = request.get_json() or {}
    paid_date = data.get("paid_date", date.today().isoformat()).strip()
    payment_method = data.get("payment_method", "Bank/Card").strip()

    db = get_db_connection()
    exp = db.execute("SELECT title, amount FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    if not exp:
        db.close()
        return jsonify({"error": "Expense not found"}), 404

    db.execute("""
        UPDATE expenses
        SET status = 'Paid', paid_date = ?, payment_method = ?
        WHERE id = ?
    """, (paid_date, payment_method, expense_id))
    db.commit()
    db.close()

    return jsonify({"success": True, "message": f"Expense '{exp['title']}' marked as paid!"})


@app.route("/api/expenses/<int:expense_id>", methods=["DELETE"])
def delete_expense(expense_id):
    """Deletes an expense record."""
    db = get_db_connection()
    db.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    db.commit()
    db.close()
    return jsonify({"success": True, "message": "Expense removed"})


# -----------------------------------------------------------------------------
# 9. Settings & Demo Reset API
# -----------------------------------------------------------------------------

@app.route("/api/settings", methods=["GET"])
def get_settings():
    """Returns tutor profile and cash flow configuration."""
    db = get_db_connection()
    settings = db.execute("SELECT * FROM settings WHERE id = 1").fetchone()
    db.close()
    return jsonify(dict(settings) if settings else {})


@app.route("/api/settings", methods=["POST"])
def update_settings():
    """Updates tutor settings and cash balance."""
    data = request.get_json() or {}
    tutor_name = data.get("tutor_name", "").strip()
    business_name = data.get("business_name", "").strip()
    tutor_phone = data.get("tutor_phone", "").strip()
    tutor_email = data.get("tutor_email", "").strip()
    payment_info = data.get("payment_info", "").strip()
    currency_symbol = data.get("currency_symbol", "$").strip()

    try:
        starting_cash_balance = float(data.get("starting_cash_balance", 2450.0))
        min_safety_buffer = float(data.get("min_safety_buffer", 1000.0))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid balance or safety buffer number"}), 400

    db = get_db_connection()
    db.execute("""
        UPDATE settings
        SET tutor_name = ?, business_name = ?, tutor_phone = ?, tutor_email = ?,
            payment_info = ?, currency_symbol = ?, starting_cash_balance = ?, min_safety_buffer = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = 1
    """, (tutor_name, business_name, tutor_phone, tutor_email, payment_info, currency_symbol, starting_cash_balance, min_safety_buffer))
    db.commit()
    db.close()

    return jsonify({"success": True, "message": "Settings saved successfully!"})


@app.route("/api/reset-data", methods=["POST"])
def reset_demo_data():
    """Resets and reseeds database with fresh realistic demo data."""
    seed_sample_data()
    return jsonify({"success": True, "message": "Sample data successfully refreshed!"})


# -----------------------------------------------------------------------------
# Application Runner
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    # Local dev server for CashPilot
    print("==================================================================")
    print(" 🚀 CashPilot – The One-Person Business Back Office")
    print(" Server starting on http://127.0.0.1:5000")
    print("==================================================================")
    app.run(host="127.0.0.1", port=5000, debug=True)
