# CashPilot 🚀
### The One-Person Business Back Office for Independent Home Tutors

> **CashPilot** is a modern, responsive web application engineered specifically for independent home tutors who manage student fees, monthly tuition billing, invoices, and overhead expenses without needing heavy or complicated accounting software.

---

## 🌟 Key Features

### 1. Command Dashboard
- **Expected Cash Balance KPI**: Calculates true expected liquidity by combining cash on hand + outstanding tuition inflows - pending overhead bills.
- **Financial Metrics**: Real-time totals for Money Collected, Total Outstanding, Overdue Invoices, and Upcoming Bills.
- **Monthly Income & Expense Chart**: Interactive bar chart powered by Chart.js showing 6-month historical cash performance.
- **Smart Attention Ribbon**: Surfaces urgent action items right at the top of the dashboard.
- **Recent Invoicing Ledger**: Displays live transactions with instant settlement actions.

### 2. Student & Fee Management
- **Complete Roster**: Student name, subject/grade level (e.g. *Grade 10 Math & Physics*), parent/guardian contact details (phone, email), and monthly fee rate.
- **Automated Fee Health**: Automatically evaluates each student's payment health (`Paid / Current`, `Pending Due`, `Overdue`).
- **Student History Ledger**: 1-click view of a student's full billing history, total invoiced, total collected, and remaining due.
- **Search & Filtering**: Instant search across students, parents, phone numbers, and active/inactive status.

### 3. Invoice Management & Billing
- **Sequential Auto-Numbering**: Automatically formats clean invoice IDs (e.g. `INV-2026-101`, `INV-2026-102`).
- **Student Auto-Fill**: Selecting a student automatically populates their pre-configured tuition fee.
- **Invoice Status Engine**: Auto-evaluates invoice status (`Paid`, `Pending`, `Overdue`) based on due dates.
- **Mark as Paid Flow**: Record settlement date, payment channel (Zelle/UPI, Bank Transfer, Cash, Cheque), and receipt notes.
- **Clean Printable Invoice**: Built-in modal formatted with receipt layout ready for `window.print()` or PDF export.

### 4. Payment Reminders Studio
- **No Awkward Conversations**: Pre-generates polite, customized reminder messages for parents.
- **Multiple Tone Templates**:
  - 🌸 **Friendly Nudge**: Warm, positive note highlighting the student's progress.
  - ⏰ **Due Today**: Courteous, timely heads-up for scheduled payments.
  - ⚠️ **Overdue Follow-Up**: Respectful but clear notice for overdue fees.
  - 📋 **Formal Statement**: Professional itemized statement for corporate or formal parents.
- **1-Click Copy to Clipboard**: One click with instant visual confirmation and toast feedback.
- **WhatsApp Web Deep Link**: Opens WhatsApp directly with the pre-filled message and parent's phone number.
- **Tutor Privacy Guarantee**: Messages are never sent automatically; the tutor retains full control.

### 5. Cash Flow Forecast (30, 60, 90 Days)
- **Predictive Horizon**: Dynamically models future cash balances across 30, 60, and 90-day windows.
- **Inflow & Outflow Modeling**: Combines pending invoices, active student monthly billing cycles, and scheduled bills.
- **Minimum Safety Reserve**: Tracks cash against an emergency buffer ($1,000 threshold) with automated warnings if a dip is predicted.
- **Plain-English Explanations**: Generates human-friendly bullet summaries explaining the numbers.

### 6. What-If Scenario Simulator
- **Stress-Test Liquidity**: Select any unpaid invoice and simulate the customer paying **15 days late**, **30 days late**, or defaulting.
- **Simulate Unexpected Bills**: Add an unexpected business expense (e.g., laptop repair $150) to evaluate tolerance.
- **Financial Impact Assessment**: Identifies maximum cash dip, lowest projected balance date, and safety buffer breaches.
- **Dual-Trajectory Chart**: Visualizes the baseline on-time plan versus the simulated late scenario side-by-side.
- **Actionable Advice**: Provides clear financial recommendations (e.g., *"Delay the workbook purchase by 1 week to preserve your $1,000 reserve"*).

### 7. Smart Alerts System
- **Real-Time Detection**: Automatically highlights overdue invoices, payments due today, and bills arriving in the next 7 days.
- **1-Click Action Buttons**: Jump directly to reminder generation or payment recording from the alert card.

### 8. Overhead Expense Management
- **Tutor Overhead Tracking**: Log expenses across categories: *Teaching Materials*, *Software & Tech (Zoom/Quizlet)*, *Travel & Fuel*, *Workspace & Rent*, *Books & Printing*, and *Other*.
- **Settlement Tracking**: Mark expenses as paid and record payment channels.

### 9. Sample Data & Demo Reset
- Pre-populated with realistic home tutoring students, mixed paid/overdue/upcoming invoices, and actual tutor overhead expenses.
- 1-click **Reset Demo** button allows judges to test and reset the application state anytime.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python Flask (RESTful JSON API + Jinja2) |
| **Database** | SQLite3 (`cashpilot.db` with foreign keys and auto-migration) |
| **Frontend** | Semantic HTML5, Modern CSS3 Design System, Vanilla JavaScript (ES6+) |
| **Charts** | Chart.js 4.4+ (Bundled offline + CDN fallback) |
| **Icons** | Lucide Icons (Bundled offline + CDN fallback) |
| **Typography** | Inter & Plus Jakarta Sans |

---

## 📁 Project Structure

```text
cashpilot/
├── app.py                   # Main Flask application and REST API endpoints
├── database.py              # SQLite schema, connection helper, seed data generator
├── forecast.py              # Cash flow forecast and what-if simulation engine
├── test_app.py              # Automated unit and integration test suite
├── requirements.txt         # Python dependencies (Flask>=3.0.0)
├── README.md                # Documentation and setup instructions
├── static/
│   ├── css/
│   │   └── style.css        # Modern SaaS CSS design system (Navy, Soft Purple, Emerald)
│   ├── js/
│   │   ├── app.js           # Core frontend controller, router, modals, CRUD, toasts
│   │   ├── charts.js        # Chart.js renderers (Income/Expense, Forecast, What-If)
│   │   └── reminders.js     # Payment reminder generator, clipboard copy, WhatsApp deep link
│   ├── vendor/
│   │   ├── chart.min.js     # Bundled Chart.js for offline reliability
│   │   └── lucide.min.js    # Bundled Lucide icons for offline reliability
│   └── favicon.svg          # CashPilot brand SVG favicon
└── templates/
    └── index.html           # Single-page SaaS dashboard layout
```

---

## 🚀 Quickstart & Local Setup Instructions

### Prerequisites
- Python 3.9+ (Python 3.10, 3.11, or 3.12 recommended)
- Modern web browser (Chrome, Edge, Firefox, Safari)

### Step 1: Clone or Navigate to the Project Directory
```bash
cd cashpilot
```

### Step 2: Create and Activate a Virtual Environment
**On Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

**On macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Run the Application
```bash
python app.py
```

### Step 5: Open in Your Browser
Visit:
```text
http://127.0.0.1:5000
```
The database (`cashpilot.db`) will initialize automatically on first startup and pre-populate realistic sample data.

---

## 🧪 Running the Automated Test Suite

To verify all features, API endpoints, forecasting math, and database operations:
```bash
python -m unittest test_app.py
```
Expected output:
```text
........
----------------------------------------------------------------------
Ran 8 tests in 0.287s

OK
```

---

## 📡 REST API Reference

| Endpoint | Method | Description |
|---|---|---|
| `GET /api/dashboard` | `GET` | High-level KPIs, cash balances, and 6-month chart data |
| `GET /api/students` | `GET` | List students with fee health status and search filters |
| `POST /api/students` | `POST` | Create a new student profile |
| `GET /api/students/<id>` | `GET` | Get student details and full invoice fee history |
| `PUT /api/students/<id>` | `PUT` | Update student profile |
| `DELETE /api/students/<id>` | `DELETE` | Delete a student and cascade associated invoices |
| `GET /api/invoices` | `GET` | List invoices with status filtering (`Paid`, `Pending`, `Overdue`) |
| `POST /api/invoices` | `POST` | Create an invoice with sequential numbering and auto-status |
| `POST /api/invoices/<id>/pay`| `POST` | Mark invoice as Paid with settlement date and method |
| `GET /api/invoices/<id>` | `GET` | Get detailed invoice with tutor profile for printing |
| `DELETE /api/invoices/<id>` | `DELETE` | Delete an invoice |
| `GET /api/reminders/generate`| `GET` | Generate polite reminder message with WhatsApp URL |
| `GET /api/forecast` | `GET` | 30, 60, and 90-day cash flow projections and explanations |
| `POST /api/whatif` | `POST` | Run what-if delay scenario simulation and impact analysis |
| `GET /api/alerts` | `GET` | Scan for overdue invoices, fees due today, and upcoming bills |
| `GET /api/expenses` | `GET` | List overhead expenses by category and status |
| `POST /api/expenses` | `POST` | Record a new overhead expense |
| `POST /api/expenses/<id>/pay`| `POST`| Mark an overhead expense as paid |
| `DELETE /api/expenses/<id>` | `DELETE`| Delete an overhead expense |
| `GET /api/settings` | `GET` | Retrieve tutor profile and cash reserve settings |
| `POST /api/settings` | `POST` | Update tutor profile, starting balance, and safety reserve |
| `POST /api/reset-data` | `POST` | Reset database with fresh demo sample data |

---

## 💡 Hackathon Evaluation Highlights
1. **Target-User Fit**: Built strictly around the mental model of a home tutor (students, parents, hourly/monthly fees, gentle communication).
2. **Zero Incomplete Buttons**: Every single button (Mark Paid, Remind, History, Edit, Delete, Simulate, Print) is wired end-to-end to SQLite and reactive UI updates.
3. **No External Internet Dependency**: Vendor JS libraries (Chart.js, Lucide) are bundled locally in `static/vendor/` with seamless CDN fallback.
4. **Clean Code & Architecture**: Decoupled database, calculation engine, REST API, and modern CSS variables design system.
