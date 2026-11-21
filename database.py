"""
CashPilot Database Module
Handles SQLite connection, schema definition, migration, status sync,
and realistic seed data generation for home tutors.
"""

import sqlite3
import os
from datetime import date, datetime, timedelta

# Database path in the project root (or /tmp for serverless cloud environments)
DB_DIR = os.path.dirname(os.path.abspath(__file__))

def resolve_db_path():
    """
    Resolves the writable database path.
    In serverless hosting (Netlify Functions, Vercel, AWS Lambda),
    the source code directory is read-only, so SQLite falls back to /tmp.
    """
    try:
        test_file = os.path.join(DB_DIR, ".test_write")
        with open(test_file, "w") as f:
            f.write("1")
        os.remove(test_file)
        return os.path.join(DB_DIR, "cashpilot.db")
    except (OSError, PermissionError):
        tmp_dir = "/tmp" if os.name != "nt" else os.environ.get("TEMP", "C:\\temp")
        return os.path.join(tmp_dir, "cashpilot.db")

DB_PATH = resolve_db_path()


def get_db_connection():
    """Returns a SQLite connection with row factory enabled for dict-like row access."""
    if not os.path.exists(DB_PATH):
        init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Initializes the SQLite database tables if they do not exist."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    # 1. Settings Table: Business & Cash Flow defaults
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            tutor_name TEXT NOT NULL DEFAULT 'Alex Morgan',
            business_name TEXT NOT NULL DEFAULT 'Apex Tutoring Studio',
            tutor_phone TEXT NOT NULL DEFAULT '+1 (555) 349-8201',
            tutor_email TEXT NOT NULL DEFAULT 'alex@apextutors.com',
            payment_info TEXT NOT NULL DEFAULT 'Zelle/UPI: alex@apextutors | Bank: Apex Academy, Acc: 894320912',
            currency_symbol TEXT NOT NULL DEFAULT '$',
            starting_cash_balance REAL NOT NULL DEFAULT 2450.0,
            min_safety_buffer REAL NOT NULL DEFAULT 1000.0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 2. Students Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            subject_grade TEXT NOT NULL,
            parent_name TEXT NOT NULL,
            parent_phone TEXT NOT NULL,
            parent_email TEXT,
            monthly_fee REAL NOT NULL,
            billing_day INTEGER NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'Active',
            notes TEXT,
            created_at DATE DEFAULT CURRENT_DATE
        );
    """)

    # 3. Invoices Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_number TEXT UNIQUE NOT NULL,
            student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
            amount REAL NOT NULL,
            issue_date DATE NOT NULL,
            due_date DATE NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending',
            description TEXT,
            paid_date DATE,
            payment_method TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 4. Expenses Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            due_date DATE NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending',
            paid_date DATE,
            payment_method TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.commit()

    # Ensure default settings row exists
    cursor.execute("SELECT COUNT(*) FROM settings")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO settings (id, tutor_name, business_name, tutor_phone, tutor_email, payment_info, currency_symbol, starting_cash_balance, min_safety_buffer)
            VALUES (1, 'Alex Morgan', 'Apex Tutoring Studio', '+1 (555) 349-8201', 'alex@apextutors.com', 'Zelle/UPI: alex@apextutors | Bank: Apex Academy, Acc: 894320912', '$', 2450.0, 1000.0)
        """)
        conn.commit()

    # Check if sample data is needed
    cursor.execute("SELECT COUNT(*) FROM students")
    student_count = cursor.fetchone()[0]
    conn.close()

    if student_count == 0:
        seed_sample_data()
    else:
        # Sync status on already existing data
        sync_invoice_statuses()


def sync_invoice_statuses():
    """
    Automatically marks any unpaid invoice whose due_date is earlier
    than today as 'Overdue'. Leaves 'Paid' invoices unchanged.
    """
    today_str = date.today().isoformat()
    conn = get_db_connection()
    conn.execute("""
        UPDATE invoices
        SET status = 'Overdue'
        WHERE status = 'Pending' AND due_date < ?
    """, (today_str,))
    conn.commit()
    conn.close()


def seed_sample_data():
    """
    Populates realistic sample data for home tutors.
    Uses relative dates based on date.today() so that whenever a user runs the demo,
    the overdue, due-today, and upcoming records are chronologically perfect.
    """
    today = date.today()
    today_str = today.isoformat()

    conn = get_db_connection()
    cursor = conn.cursor()

    # Clear existing data
    cursor.execute("DELETE FROM invoices")
    cursor.execute("DELETE FROM expenses")
    cursor.execute("DELETE FROM students")

    # Reset SQLite autoincrement counters
    cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('students', 'invoices', 'expenses')")

    # Sample Students (Independent Home Tutoring Context)
    students = [
        ("Liam Chen", "Grade 10 - Advanced Math & Physics", "David Chen", "+1 (555) 219-4821", "david.chen@example.com", 320.0, 5, "Active", "Prepares for state math olympiad. Tue & Thu sessions."),
        ("Sophia Patel", "Grade 8 - Pre-Algebra & General Science", "Ananya Patel", "+1 (555) 891-2304", "ananya.patel@example.com", 240.0, today.day, "Active", "Focusing on algebra fundamentals. Monday sessions."),
        ("Marcus Johnson", "Grade 12 - AP Calculus BC", "Sarah Johnson", "+1 (555) 438-9120", "sarah.j@example.com", 380.0, 1, "Active", "Intensive AP test prep. Very prompt with online payments."),
        ("Emily Zhang", "Grade 11 - SAT Math & Chemistry", "Kevin Zhang", "+1 (555) 762-3901", "kzhang99@example.com", 350.0, 25, "Active", "Weekend batches. Wants monthly progress reports."),
        ("Lucas Vance", "Grade 9 - High School Biology", "Elena Vance", "+1 (555) 604-1298", "elena.vance@example.com", 280.0, 2, "Active", "Wednesday evening sessions. In-person at home studio."),
        ("Aria Robinson", "Grade 7 - STEM Foundations", "Mark Robinson", "+1 (555) 310-7744", "mrobinson@example.com", 220.0, 12, "Active", "Hands-on projects and weekly problem sets."),
        ("Noah Kim", "Grade 10 - Geometry & Trigonometry", "Grace Kim", "+1 (555) 902-6611", "grace.kim@example.com", 290.0, 28, "Active", "Friday afternoon sessions.")
    ]

    cursor.executemany("""
        INSERT INTO students (name, subject_grade, parent_name, parent_phone, parent_email, monthly_fee, billing_day, status, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, students)
    conn.commit()

    # Retrieve inserted student IDs
    cursor.execute("SELECT id, name, monthly_fee FROM students ORDER BY id")
    stu_map = {row["name"]: (row["id"], row["monthly_fee"]) for row in cursor.fetchall()}

    # Sample Invoices: Mix of Paid, Overdue, Due Today, and Upcoming
    # Let's craft dates relative to today:
    d_overdue_16 = (today - timedelta(days=16)).isoformat()
    d_overdue_9 = (today - timedelta(days=9)).isoformat()
    d_due_today = today_str
    d_due_in_4 = (today + timedelta(days=4)).isoformat()
    d_due_in_9 = (today + timedelta(days=9)).isoformat()
    d_due_in_14 = (today + timedelta(days=14)).isoformat()

    # Past paid dates
    d_paid_early_this_month = (today - timedelta(days=18)).isoformat()
    d_paid_last_month = (today - timedelta(days=45)).isoformat()
    d_issue_recent = (today - timedelta(days=20)).isoformat()

    invoices = [
        # Overdue Invoice 1: Liam Chen ($320) - 16 days overdue
        ("INV-2026-101", stu_map["Liam Chen"][0], 320.0, (today - timedelta(days=31)).isoformat(), d_overdue_16, "Overdue", "November Tuition - 8 Math & Physics Sessions", None, None, "Second gentle reminder pending"),
        
        # Overdue Invoice 2: Aria Robinson ($220) - 9 days overdue
        ("INV-2026-102", stu_map["Aria Robinson"][0], 220.0, (today - timedelta(days=24)).isoformat(), d_overdue_9, "Overdue", "November STEM Foundations - 4 Sessions", None, None, "Parent requested reminder via SMS"),

        # Due Today: Sophia Patel ($240)
        ("INV-2026-103", stu_map["Sophia Patel"][0], 240.0, (today - timedelta(days=14)).isoformat(), d_due_today, "Pending", "November Tuition - Pre-Algebra & General Science", None, None, "Sent invoice on 14th"),

        # Upcoming Invoices: Emily Zhang ($350) due in 4 days
        ("INV-2026-104", stu_map["Emily Zhang"][0], 350.0, (today - timedelta(days=10)).isoformat(), d_due_in_4, "Pending", "November SAT Prep & Chemistry", None, None, "Regular monthly billing"),

        # Upcoming Invoices: Noah Kim ($290) due in 9 days
        ("INV-2026-105", stu_map["Noah Kim"][0], 290.0, (today - timedelta(days=7)).isoformat(), d_due_in_9, "Pending", "November Geometry & Trig Sessions", None, None, "Monthly billing"),

        # Paid Invoices this month: Marcus Johnson ($380)
        ("INV-2026-106", stu_map["Marcus Johnson"][0], 380.0, (today - timedelta(days=25)).isoformat(), (today - timedelta(days=19)).isoformat(), "Paid", "November AP Calculus BC Tuition", d_paid_early_this_month, "Zelle/UPI", "Paid promptly on receipt"),

        # Paid Invoices this month: Lucas Vance ($280)
        ("INV-2026-107", stu_map["Lucas Vance"][0], 280.0, (today - timedelta(days=26)).isoformat(), (today - timedelta(days=20)).isoformat(), "Paid", "November High School Biology Tuition", (today - timedelta(days=19)).isoformat(), "Bank Transfer", "Direct ACH transfer confirmed"),

        # Paid Invoices previous cycle: Marcus Johnson ($380)
        ("INV-2026-092", stu_map["Marcus Johnson"][0], 380.0, (today - timedelta(days=55)).isoformat(), (today - timedelta(days=48)).isoformat(), "Paid", "October AP Calculus BC Tuition", d_paid_last_month, "Zelle/UPI", "October fee settled"),

        # Paid Invoices previous cycle: Liam Chen ($320)
        ("INV-2026-093", stu_map["Liam Chen"][0], 320.0, (today - timedelta(days=58)).isoformat(), (today - timedelta(days=50)).isoformat(), "Paid", "October Math & Physics Tuition", (today - timedelta(days=49)).isoformat(), "Cash", "Received in person"),

        # Paid Invoices previous cycle: Lucas Vance ($280)
        ("INV-2026-094", stu_map["Lucas Vance"][0], 280.0, (today - timedelta(days=56)).isoformat(), (today - timedelta(days=50)).isoformat(), "Paid", "October Biology Tuition", (today - timedelta(days=50)).isoformat(), "Bank Transfer", "Monthly auto-transfer")
    ]

    cursor.executemany("""
        INSERT INTO invoices (invoice_number, student_id, amount, issue_date, due_date, status, description, paid_date, payment_method, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, invoices)

    # Sample Expenses: Real Home Tutor Overhead Costs
    expenses = [
        # Software & Tech: Zoom Pro (Paid)
        ("Zoom Pro Video Conferencing Plan", "Software & Tech", 15.99, (today - timedelta(days=20)).isoformat(), "Paid", (today - timedelta(days=20)).isoformat(), "Credit Card", "For remote tutoring days"),

        # Teaching Materials: Markers, Graph Paper, Lesson Sheets (Paid)
        ("Dry Erase Markers & Grid Paper Ream", "Teaching Materials", 32.50, (today - timedelta(days=12)).isoformat(), "Paid", (today - timedelta(days=12)).isoformat(), "Debit Card", "Bought at Office Depot"),

        # Travel: Fuel & Commute (Paid)
        ("In-Person Commute & Fuel Allowance", "Travel & Fuel", 55.00, (today - timedelta(days=6)).isoformat(), "Paid", (today - timedelta(days=6)).isoformat(), "Cash", "Home visits for student sessions"),

        # Software: Quizlet Plus & Kahoot Educator (Pending, Due in 3 days)
        ("Quizlet Teacher & Kahoot Pro Subscriptions", "Software & Tech", 42.00, (today + timedelta(days=3)).isoformat(), "Pending", None, None, "Annual educational tools renewal"),

        # Books & Printing: Calculus Practice Booklets (Pending, Due in 7 days)
        ("Calculus BC Exam Prep Workbooks (5 Copies)", "Books & Printing", 78.50, (today + timedelta(days=7)).isoformat(), "Pending", None, None, "Orders arriving from distributor"),

        # Workspace & Rent: Co-working Studio Room (Pending, Due in 12 days)
        ("Weekend Tutoring Studio Room Rental", "Workspace & Rent", 220.00, (today + timedelta(days=12)).isoformat(), "Pending", None, None, "Monthly room fee for small group batches"),

        # Travel: Monthly Transit Pass / Fuel (Pending, Due in 25 days)
        ("December Student Transit & Fuel", "Travel & Fuel", 60.00, (today + timedelta(days=25)).isoformat(), "Pending", None, None, "Planned transport budget")
    ]

    cursor.executemany("""
        INSERT INTO expenses (title, category, amount, due_date, status, paid_date, payment_method, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, expenses)

    conn.commit()
    conn.close()
    print("Database successfully seeded with realistic sample data!")


if __name__ == "__main__":
    init_db()
    print("Initialization finished.")
