"""
CashPilot Test Suite
Tests all end-to-end features, workflows, and calculations.
"""

import unittest
from datetime import date, timedelta
import app
from database import init_db, get_db_connection, seed_sample_data
from forecast import calculate_cash_forecast, simulate_whatif_scenario, generate_smart_alerts


class CashPilotTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = app.app.test_client()

    def setUp(self):
        # Refresh sample data for predictable test state
        seed_sample_data()

    def test_dashboard_metrics(self):
        """Test dashboard summary KPI figures and chart structure."""
        res = self.client.get("/api/dashboard")
        self.assertEqual(res.status_code, 200)
        data = res.json
        self.assertIn("current_cash_balance", data)
        self.assertIn("expected_cash_balance", data)
        self.assertIn("total_outstanding", data)
        self.assertIn("total_collected", data)
        self.assertIn("total_overdue", data)
        self.assertIn("chart", data)
        self.assertEqual(len(data["chart"]["labels"]), 6)
        self.assertGreater(data["total_outstanding"], 0)
        self.assertGreater(data["total_collected"], 0)

    def test_student_crud(self):
        """Test adding, listing, updating and querying students."""
        # Create student
        payload = {
            "name": "Oliver Queen",
            "subject_grade": "Grade 11 - Physics",
            "parent_name": "Moira Queen",
            "parent_phone": "+1 (555) 123-9876",
            "parent_email": "moira@example.com",
            "monthly_fee": 350.0,
            "billing_day": 10,
            "status": "Active",
            "notes": "Weekly lab exercises"
        }
        create_res = self.client.post("/api/students", json=payload)
        self.assertEqual(create_res.status_code, 201)
        student_id = create_res.json["id"]

        # Retrieve student
        get_res = self.client.get(f"/api/students/{student_id}")
        self.assertEqual(get_res.status_code, 200)
        self.assertEqual(get_res.json["name"], "Oliver Queen")

        # Update student
        payload["monthly_fee"] = 380.0
        update_res = self.client.put(f"/api/students/{student_id}", json=payload)
        self.assertEqual(update_res.status_code, 200)

        # Verify update
        get_res2 = self.client.get(f"/api/students/{student_id}")
        self.assertEqual(get_res2.json["monthly_fee"], 380.0)

    def test_invoice_create_and_pay(self):
        """Test invoice creation, sequential number generation, and mark as paid flow."""
        today = date.today().isoformat()
        due = (date.today() + timedelta(days=10)).isoformat()

        # 1. Create invoice
        inv_payload = {
            "student_id": 1,
            "amount": 320.0,
            "issue_date": today,
            "due_date": due,
            "description": "December 2026 Tuition Prep"
        }
        res = self.client.post("/api/invoices", json=inv_payload)
        self.assertEqual(res.status_code, 201)
        inv_id = res.json["id"]
        inv_num = res.json["invoice_number"]
        self.assertTrue(inv_num.startswith("INV-"))

        # 2. Mark invoice as paid
        pay_payload = {
            "paid_date": today,
            "payment_method": "Zelle/UPI",
            "notes": "Paid directly"
        }
        pay_res = self.client.post(f"/api/invoices/{inv_id}/pay", json=pay_payload)
        self.assertEqual(pay_res.status_code, 200)

        # 3. Verify status changed to Paid
        detail_res = self.client.get(f"/api/invoices/{inv_id}")
        self.assertEqual(detail_res.status_code, 200)
        self.assertEqual(detail_res.json["status"], "Paid")
        self.assertEqual(detail_res.json["payment_method"], "Zelle/UPI")

    def test_payment_reminder_generator(self):
        """Test generation of polite reminder templates and WhatsApp link."""
        # Test friendly template
        res = self.client.get("/api/reminders/generate?invoice_id=1&template=friendly")
        self.assertEqual(res.status_code, 200)
        data = res.json
        self.assertIn("Liam Chen", data["student_name"])
        self.assertIn("David Chen", data["body"])
        self.assertIn("https://wa.me/", data["whatsapp_url"])

        # Test overdue template
        res_od = self.client.get("/api/reminders/generate?invoice_id=1&template=overdue")
        self.assertEqual(res_od.status_code, 200)
        self.assertIn("Gentle Follow-Up", res_od.json["subject"])

    def test_cash_flow_forecast(self):
        """Test 30, 60, and 90-day cash projections."""
        res = self.client.get("/api/forecast")
        self.assertEqual(res.status_code, 200)
        data = res.json
        self.assertIn("day_30", data)
        self.assertIn("day_60", data)
        self.assertIn("day_90", data)
        self.assertIn("timeline", data)
        self.assertGreaterEqual(len(data["timeline"]), 30)
        self.assertIn("Healthy", data["health_status"])

    def test_whatif_scenario_simulation(self):
        """Test simulating a 15-day late payment scenario."""
        payload = {
            "invoice_id": 1,
            "delay_days": 15,
            "unexpected_expense": 50.0
        }
        res = self.client.post("/api/whatif", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json
        summary = data["impact_summary"]
        self.assertEqual(summary["delay_days"], 15)
        self.assertIn("timeline_comparison", data)
        self.assertGreater(len(data["timeline_comparison"]), 0)

    def test_smart_alerts(self):
        """Test smart detection of overdue payments and bills due."""
        res = self.client.get("/api/alerts")
        self.assertEqual(res.status_code, 200)
        alerts = res.json
        self.assertIsInstance(alerts, list)
        self.assertGreater(len(alerts), 0)
        # Should detect overdue invoices
        overdue_alerts = [a for a in alerts if a["type"] == "overdue_invoice"]
        self.assertGreater(len(overdue_alerts), 0)

    def test_expense_crud(self):
        """Test adding, listing, and paying expenses."""
        payload = {
            "title": "Highlighter Pack & Whiteboard Erasing Spray",
            "category": "Teaching Materials",
            "amount": 22.50,
            "due_date": date.today().isoformat(),
            "status": "Pending",
            "notes": "Office supplies"
        }
        res = self.client.post("/api/expenses", json=payload)
        self.assertEqual(res.status_code, 201)
        exp_id = res.json["id"]

        # Pay expense
        pay_res = self.client.post(f"/api/expenses/{exp_id}/pay", json={"paid_date": date.today().isoformat(), "payment_method": "Debit Card"})
        self.assertEqual(pay_res.status_code, 200)


if __name__ == "__main__":
    unittest.main()
