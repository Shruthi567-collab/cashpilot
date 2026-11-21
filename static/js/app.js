/**
 * CashPilot – The One-Person Business Back Office
 * Main Frontend Application Controller
 * Handles Navigation, State Management, CRUD Operations, Modals, and Toasts.
 */

// Global Application State
const CashPilot = {
  currentView: "dashboard",
  currency: "$",
  students: [],
  invoices: [],
  expenses: [],
  settings: {},
  forecastData: null
};

// ============================================================================
// Initialization on DOM Ready
// ============================================================================
document.addEventListener("DOMContentLoaded", async () => {
  // Initialize Lucide icons if available
  if (window.lucide) {
    lucide.createIcons();
  }

  // Set today's date in header indicator
  updateHeaderDate();

  // Load Settings & Profile
  await loadSettings();

  // Load initial view (Dashboard)
  await navigateTo("dashboard");

  // Event Listeners for modals, sidebar, and forms
  setupEventListeners();
});

function updateHeaderDate() {
  const el = document.getElementById("headerTodayDate");
  if (el) {
    const today = new Date();
    const options = { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' };
    el.textContent = today.toLocaleDateString(undefined, options);
  }
}

// ============================================================================
// Navigation & Router
// ============================================================================
async function navigateTo(viewName, param = null) {
  CashPilot.currentView = viewName;

  // Update navigation items active state
  document.querySelectorAll(".nav-item").forEach(item => {
    item.classList.toggle("active", item.getAttribute("data-view") === viewName);
  });

  // Toggle View sections
  document.querySelectorAll(".view-section").forEach(sec => {
    sec.classList.remove("active-view");
  });

  const targetView = document.getElementById(`view-${viewName}`);
  if (targetView) {
    targetView.classList.add("active-view");
  }

  // Update header title and breadcrumb
  updateHeaderTitle(viewName);

  // Close mobile sidebar if open
  const sidebar = document.querySelector(".sidebar");
  if (sidebar && sidebar.classList.contains("mobile-open")) {
    sidebar.classList.remove("mobile-open");
  }

  // View-specific data fetching
  switch (viewName) {
    case "dashboard":
      await loadDashboard();
      break;
    case "students":
      await loadStudents();
      break;
    case "invoices":
      await loadInvoices();
      break;
    case "reminders":
      await initReminderStudio(param);
      break;
    case "forecast":
      await loadForecast(30);
      break;
    case "whatif":
      await initWhatIfSimulator(param);
      break;
    case "alerts":
      await loadSmartAlertsView();
      break;
    case "expenses":
      await loadExpenses();
      break;
    case "settings":
      await loadSettingsView();
      break;
  }

  // Re-render icons for newly injected markup
  if (window.lucide) {
    lucide.createIcons();
  }
}

function updateHeaderTitle(viewName) {
  const titles = {
    dashboard: { title: "Command Dashboard", breadcrumb: "CashPilot / Overview" },
    students: { title: "Student Roster & Fees", breadcrumb: "CashPilot / Students" },
    invoices: { title: "Invoices & Tuition Billing", breadcrumb: "CashPilot / Invoices" },
    reminders: { title: "Payment Reminders Studio", breadcrumb: "CashPilot / Communication" },
    forecast: { title: "Cash Flow Forecasting", breadcrumb: "CashPilot / Cash Flow" },
    whatif: { title: "What-If Scenario Simulator", breadcrumb: "CashPilot / Planning" },
    alerts: { title: "Smart Action Alerts", breadcrumb: "CashPilot / Alerts" },
    expenses: { title: "Business Expenses & Overhead", breadcrumb: "CashPilot / Expenses" },
    settings: { title: "Profile & Business Settings", breadcrumb: "CashPilot / Settings" }
  };

  const meta = titles[viewName] || { title: "CashPilot", breadcrumb: "Back Office" };
  const h2 = document.getElementById("pageHeaderTitle");
  const bc = document.getElementById("pageHeaderBreadcrumb");
  if (h2) h2.textContent = meta.title;
  if (bc) bc.textContent = meta.breadcrumb;
}

// ============================================================================
// 1. Dashboard Module
// ============================================================================
async function loadDashboard() {
  try {
    const [dashRes, alertsRes] = await Promise.all([
      fetch("/api/dashboard"),
      fetch("/api/alerts")
    ]);

    const data = await dashRes.json();
    const alerts = await alertsRes.json();

    // 1. Update KPI Cards
    const cur = data.currency || "$";
    CashPilot.currency = cur;

    document.getElementById("kpiExpectedCash").textContent = `${cur}${data.expected_cash_balance.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    document.getElementById("kpiCurrentCash").textContent = `${cur}${data.current_cash_balance.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    document.getElementById("kpiOutstanding").textContent = `${cur}${data.total_outstanding.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    document.getElementById("kpiOutstandingCount").textContent = `${data.outstanding_count} pending invoices`;

    document.getElementById("kpiCollected").textContent = `${cur}${data.total_collected.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    document.getElementById("kpiCollectedCount").textContent = `${data.collected_count} invoices paid`;

    document.getElementById("kpiOverdue").textContent = `${cur}${data.total_overdue.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    document.getElementById("kpiOverdueCount").textContent = `${data.overdue_count} overdue`;

    document.getElementById("kpiUpcomingBills").textContent = `${cur}${data.upcoming_bills.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    document.getElementById("kpiUpcomingBillsCount").textContent = `${data.upcoming_bills_count} bills pending`;

    // 2. Render Income vs Expense Chart
    if (data.chart) {
      renderIncomeExpenseChart(data.chart.labels, data.chart.income, data.chart.expenses);
    }

    // 3. Render Top Dashboard Alert Banner if overdue or high-priority items exist
    renderDashboardAlertBanner(alerts);

    // 4. Update sidebar alert pill count
    const badgeEl = document.getElementById("sidebarAlertBadge");
    if (badgeEl) {
      const urgentCount = alerts.filter(a => a.level === "danger" || a.level === "warning").length;
      badgeEl.textContent = urgentCount;
      badgeEl.style.display = urgentCount > 0 ? "inline-flex" : "none";
    }

    // 5. Render Recent Activity Table
    renderDashboardRecentActivity(data.recent_activity || []);

  } catch (err) {
    console.error("Failed to load dashboard data:", err);
    showToast("Error loading dashboard metrics", "danger");
  }
}

function renderDashboardAlertBanner(alerts) {
  const container = document.getElementById("dashboardAlertBannerContainer");
  if (!container) return;

  const urgentAlerts = alerts.filter(a => a.level === "danger" || a.level === "warning");
  if (urgentAlerts.length === 0) {
    container.innerHTML = "";
    return;
  }

  const top = urgentAlerts[0];
  container.innerHTML = `
    <div class="alert-banner">
      <div class="alert-banner-content">
        <div class="alert-banner-icon">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
        </div>
        <div class="alert-banner-text">
          <h4>Smart Attention: ${top.title}</h4>
          <p>${top.message}</p>
        </div>
      </div>
      <div style="display: flex; gap: 8px;">
        <button class="btn btn-sm btn-primary" onclick="handleAlertAction('${top.action_type}', ${top.target_id})">${top.action_label}</button>
        <button class="btn btn-sm btn-outline" onclick="navigateTo('alerts')">View All (${alerts.length})</button>
      </div>
    </div>
  `;
}

function renderDashboardRecentActivity(items) {
  const tbody = document.getElementById("dashboardRecentTableBody");
  if (!tbody) return;

  if (items.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" class="empty-state"><p class="empty-state-text">No recent transactions recorded yet.</p></td></tr>`;
    return;
  }

  tbody.innerHTML = items.map(inv => {
    const badgeClass = inv.status === "Paid" ? "badge-success" : (inv.status === "Overdue" ? "badge-danger" : "badge-warning");
    return `
      <tr>
        <td class="primary-cell">${inv.invoice_number}</td>
        <td>${inv.student_name}</td>
        <td class="amount-cell">${CashPilot.currency}${inv.amount.toFixed(2)}</td>
        <td>${inv.status === "Paid" ? `Paid on ${inv.paid_date}` : `Due ${inv.due_date}`}</td>
        <td><span class="badge ${badgeClass}"><span class="badge-dot"></span>${inv.status}</span></td>
      </tr>
    `;
  }).join("");
}

// ============================================================================
// 2. Student Management Module
// ============================================================================
async function loadStudents() {
  const search = document.getElementById("studentSearchInput")?.value || "";
  const status = document.getElementById("studentStatusFilter")?.value || "All";

  try {
    const res = await fetch(`/api/students?q=${encodeURIComponent(search)}&status=${encodeURIComponent(status)}`);
    const students = await res.json();
    CashPilot.students = students;

    const tbody = document.getElementById("studentsTableBody");
    const countEl = document.getElementById("studentsCountBadge");
    if (countEl) countEl.textContent = `${students.length} Students`;

    if (!tbody) return;

    if (students.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="7" class="empty-state">
            <div class="empty-state-icon">
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
            </div>
            <h4 class="empty-state-title">No Students Found</h4>
            <p class="empty-state-text">Add your first home tutoring student or adjust your search filters.</p>
            <button class="btn btn-sm btn-primary" onclick="openAddStudentModal()">+ Add New Student</button>
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = students.map(s => {
      const statusBadge = s.status === "Active" ? "badge-success" : "badge-neutral";
      return `
        <tr>
          <td>
            <div class="primary-cell">${s.name}</div>
            <div class="sub-cell">${s.subject_grade}</div>
          </td>
          <td>
            <div class="primary-cell">${s.parent_name}</div>
            <div class="sub-cell">${s.parent_phone}</div>
          </td>
          <td class="amount-cell">${CashPilot.currency}${s.monthly_fee.toFixed(2)} / mo</td>
          <td>Day ${s.billing_day} of month</td>
          <td>
            <span class="badge badge-${s.payment_badge}">
              <span class="badge-dot"></span>${s.payment_status}
            </span>
          </td>
          <td><span class="badge ${statusBadge}"><span class="badge-dot"></span>${s.status}</span></td>
          <td class="actions-cell">
            <button class="btn btn-sm btn-outline" title="View Fee History" onclick="viewStudentDetails(${s.id})">History</button>
            <button class="btn btn-sm btn-primary" title="Create Invoice" onclick="quickCreateInvoiceForStudent(${s.id}, '${s.name}', ${s.monthly_fee})">+ Invoice</button>
            <button class="btn btn-sm btn-outline" title="Edit Student" onclick="openEditStudentModal(${s.id})">Edit</button>
            <button class="btn btn-sm btn-danger-outline" title="Delete Student" onclick="confirmDeleteStudent(${s.id}, '${s.name}')">Delete</button>
          </td>
        </tr>
      `;
    }).join("");

    if (window.lucide) lucide.createIcons();

  } catch (err) {
    console.error("Failed to load students:", err);
  }
}

function openAddStudentModal() {
  document.getElementById("studentModalTitle").textContent = "Add New Student";
  document.getElementById("studentForm").reset();
  document.getElementById("studentEditId").value = "";
  openModal("studentModal");
}

async function openEditStudentModal(studentId) {
  try {
    const res = await fetch(`/api/students/${studentId}`);
    const s = await res.json();
    if (s.error) return showToast(s.error, "danger");

    document.getElementById("studentModalTitle").textContent = `Edit Student: ${s.name}`;
    document.getElementById("studentEditId").value = s.id;
    document.getElementById("studentNameInput").value = s.name;
    document.getElementById("studentSubjectInput").value = s.subject_grade;
    document.getElementById("studentParentNameInput").value = s.parent_name;
    document.getElementById("studentParentPhoneInput").value = s.parent_phone;
    document.getElementById("studentParentEmailInput").value = s.parent_email || "";
    document.getElementById("studentFeeInput").value = s.monthly_fee;
    document.getElementById("studentBillingDayInput").value = s.billing_day;
    document.getElementById("studentStatusInput").value = s.status;
    document.getElementById("studentNotesInput").value = s.notes || "";

    openModal("studentModal");
  } catch (err) {
    showToast("Failed to fetch student details", "danger");
  }
}

async function handleStudentFormSubmit(e) {
  e.preventDefault();
  const editId = document.getElementById("studentEditId").value;
  const payload = {
    name: document.getElementById("studentNameInput").value.trim(),
    subject_grade: document.getElementById("studentSubjectInput").value.trim(),
    parent_name: document.getElementById("studentParentNameInput").value.trim(),
    parent_phone: document.getElementById("studentParentPhoneInput").value.trim(),
    parent_email: document.getElementById("studentParentEmailInput").value.trim(),
    monthly_fee: parseFloat(document.getElementById("studentFeeInput").value),
    billing_day: parseInt(document.getElementById("studentBillingDayInput").value, 10),
    status: document.getElementById("studentStatusInput").value,
    notes: document.getElementById("studentNotesInput").value.trim()
  };

  const url = editId ? `/api/students/${editId}` : "/api/students";
  const method = editId ? "PUT" : "POST";

  try {
    const res = await fetch(url, {
      method: method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();

    if (!res.ok) {
      showToast(data.error || "Failed to save student", "danger");
      return;
    }

    closeModal("studentModal");
    showToast(data.message, "success");
    await loadStudents();
    await loadDashboard(); // refresh KPI counts
  } catch (err) {
    showToast("Network error while saving student", "danger");
  }
}

async function viewStudentDetails(studentId) {
  try {
    const res = await fetch(`/api/students/${studentId}`);
    const s = await res.json();
    if (s.error) return showToast(s.error, "danger");

    document.getElementById("studentDetailTitle").textContent = `${s.name} - Tuition History`;
    document.getElementById("studentDetailMeta").innerHTML = `
      <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 16px;">
        <div class="impact-metric-box">
          <div class="impact-metric-title">Total Invoiced</div>
          <div class="impact-metric-val">${CashPilot.currency}${s.total_billed.toFixed(2)}</div>
        </div>
        <div class="impact-metric-box success">
          <div class="impact-metric-title">Total Collected</div>
          <div class="impact-metric-val">${CashPilot.currency}${s.total_paid.toFixed(2)}</div>
        </div>
        <div class="impact-metric-box ${s.total_pending > 0 ? 'warning' : ''}">
          <div class="impact-metric-title">Total Due</div>
          <div class="impact-metric-val">${CashPilot.currency}${s.total_pending.toFixed(2)}</div>
        </div>
      </div>
      <p style="font-size: 13px; color: var(--navy-600); margin-bottom: 14px;">
        <strong>Parent:</strong> ${s.parent_name} (${s.parent_phone}) &nbsp;|&nbsp; <strong>Subject:</strong> ${s.subject_grade}
      </p>
    `;

    const invTbody = document.getElementById("studentDetailInvoicesBody");
    if (s.invoices.length === 0) {
      invTbody.innerHTML = `<tr><td colspan="5" class="empty-state"><p class="empty-state-text">No invoices created for this student yet.</p></td></tr>`;
    } else {
      invTbody.innerHTML = s.invoices.map(inv => `
        <tr>
          <td class="primary-cell">${inv.invoice_number}</td>
          <td>${inv.description || "Tuition"}</td>
          <td class="amount-cell">${CashPilot.currency}${inv.amount.toFixed(2)}</td>
          <td>Due ${inv.due_date}</td>
          <td><span class="badge ${inv.status === 'Paid' ? 'badge-success' : (inv.status === 'Overdue' ? 'badge-danger' : 'badge-warning')}"><span class="badge-dot"></span>${inv.status}</span></td>
        </tr>
      `).join("");
    }

    openModal("studentDetailModal");
  } catch (err) {
    showToast("Error retrieving student history", "danger");
  }
}

async function confirmDeleteStudent(studentId, name) {
  if (!confirm(`Are you sure you want to remove student "${name}" and all their invoices?`)) return;

  try {
    const res = await fetch(`/api/students/${studentId}`, { method: "DELETE" });
    const data = await res.json();
    showToast(data.message, "success");
    await loadStudents();
    await loadDashboard();
  } catch (err) {
    showToast("Failed to delete student", "danger");
  }
}

// ============================================================================
// 3. Invoice Management Module
// ============================================================================
async function loadInvoices() {
  const search = document.getElementById("invoiceSearchInput")?.value || "";
  const status = document.getElementById("invoiceStatusFilter")?.value || "All";

  try {
    const res = await fetch(`/api/invoices?q=${encodeURIComponent(search)}&status=${encodeURIComponent(status)}`);
    const invoices = await res.json();
    CashPilot.invoices = invoices;

    const tbody = document.getElementById("invoicesTableBody");
    if (!tbody) return;

    if (invoices.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="7" class="empty-state">
            <div class="empty-state-icon">
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
            </div>
            <h4 class="empty-state-title">No Invoices Found</h4>
            <p class="empty-state-text">Create tuition invoices to track student fees and generate payment reminders.</p>
            <button class="btn btn-sm btn-primary" onclick="openCreateInvoiceModal()">+ Create New Invoice</button>
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = invoices.map(inv => {
      const badgeClass = inv.status === "Paid" ? "badge-success" : (inv.status === "Overdue" ? "badge-danger" : "badge-warning");
      const isPaid = inv.status === "Paid";

      return `
        <tr>
          <td>
            <div class="primary-cell">${inv.invoice_number}</div>
            <div class="sub-cell">${inv.issue_date}</div>
          </td>
          <td>
            <div class="primary-cell">${inv.student_name}</div>
            <div class="sub-cell">${inv.parent_name} (${inv.parent_phone})</div>
          </td>
          <td>${inv.description || "Monthly Tuition"}</td>
          <td class="amount-cell">${CashPilot.currency}${inv.amount.toFixed(2)}</td>
          <td>
            <div>${inv.due_date}</div>
            ${inv.paid_date ? `<div class="sub-cell">Paid: ${inv.paid_date} (${inv.payment_method})</div>` : ''}
          </td>
          <td><span class="badge ${badgeClass}"><span class="badge-dot"></span>${inv.status}</span></td>
          <td class="actions-cell">
            ${!isPaid ? `
              <button class="btn btn-sm btn-success" title="Mark as Paid" onclick="openMarkPaidModal(${inv.id}, '${inv.invoice_number}', ${inv.amount})">✓ Mark Paid</button>
              <button class="btn btn-sm btn-purple" title="Generate Polite Reminder" onclick="navigateTo('reminders', ${inv.id})">💬 Remind</button>
            ` : `
              <span style="font-size: 12px; color: var(--green-600); font-weight: 600; padding: 4px 6px;">Settled</span>
            `}
            <button class="btn btn-sm btn-outline" title="Print/View Invoice" onclick="viewPrintableInvoice(${inv.id})">View/Print</button>
            <button class="btn btn-sm btn-danger-outline" title="Delete Invoice" onclick="confirmDeleteInvoice(${inv.id}, '${inv.invoice_number}')">×</button>
          </td>
        </tr>
      `;
    }).join("");

    if (window.lucide) lucide.createIcons();

  } catch (err) {
    console.error("Failed to load invoices:", err);
  }
}

async function openCreateInvoiceModal() {
  document.getElementById("invoiceForm").reset();

  // Populate student selector
  const select = document.getElementById("invoiceStudentSelect");
  select.innerHTML = "<option value=''>-- Select Student --</option>";

  try {
    const res = await fetch("/api/students");
    const students = await res.json();
    students.forEach(s => {
      const opt = document.createElement("option");
      opt.value = s.id;
      opt.textContent = `${s.name} ($${s.monthly_fee.toFixed(2)} / mo - ${s.subject_grade})`;
      opt.dataset.fee = s.monthly_fee;
      select.appendChild(opt);
    });

    // Set today's date as default issue date and 14 days later as due date
    const today = new Date();
    const dueDate = new Date();
    dueDate.setDate(today.getDate() + 14);

    document.getElementById("invoiceIssueDateInput").value = today.toISOString().split("T")[0];
    document.getElementById("invoiceDueDateInput").value = dueDate.toISOString().split("T")[0];
    document.getElementById("invoiceDescInput").value = `${today.toLocaleString('default', { month: 'long' })} Tuition Sessions`;

    openModal("invoiceModal");
  } catch (err) {
    showToast("Error loading students for invoice creation", "danger");
  }
}

function handleInvoiceStudentSelectChange() {
  const select = document.getElementById("invoiceStudentSelect");
  const selectedOpt = select.options[select.selectedIndex];
  if (selectedOpt && selectedOpt.dataset.fee) {
    document.getElementById("invoiceAmountInput").value = selectedOpt.dataset.fee;
  }
}

function quickCreateInvoiceForStudent(studentId, name, fee) {
  openCreateInvoiceModal().then(() => {
    const select = document.getElementById("invoiceStudentSelect");
    select.value = studentId;
    document.getElementById("invoiceAmountInput").value = fee;
  });
}

async function handleInvoiceFormSubmit(e) {
  e.preventDefault();
  const payload = {
    student_id: document.getElementById("invoiceStudentSelect").value,
    amount: parseFloat(document.getElementById("invoiceAmountInput").value),
    issue_date: document.getElementById("invoiceIssueDateInput").value,
    due_date: document.getElementById("invoiceDueDateInput").value,
    description: document.getElementById("invoiceDescInput").value.trim(),
    notes: document.getElementById("invoiceNotesInput").value.trim()
  };

  try {
    const res = await fetch("/api/invoices", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();

    if (!res.ok) {
      showToast(data.error || "Failed to create invoice", "danger");
      return;
    }

    closeModal("invoiceModal");
    showToast(data.message, "success");
    await loadInvoices();
    await loadDashboard();
  } catch (err) {
    showToast("Network error creating invoice", "danger");
  }
}

function openMarkPaidModal(invoiceId, invNum, amount) {
  document.getElementById("markPaidInvoiceId").value = invoiceId;
  document.getElementById("markPaidDetailsText").textContent = `Recording payment for Invoice #${invNum} ($${amount.toFixed(2)})`;
  document.getElementById("markPaidDateInput").value = new Date().toISOString().split("T")[0];
  openModal("markPaidModal");
}

async function handleMarkPaidSubmit(e) {
  e.preventDefault();
  const invoiceId = document.getElementById("markPaidInvoiceId").value;
  const payload = {
    paid_date: document.getElementById("markPaidDateInput").value,
    payment_method: document.getElementById("markPaidMethodSelect").value,
    notes: document.getElementById("markPaidNotesInput").value.trim()
  };

  try {
    const res = await fetch(`/api/invoices/${invoiceId}/pay`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();

    if (!res.ok) {
      showToast(data.error || "Payment recording failed", "danger");
      return;
    }

    closeModal("markPaidModal");
    showToast(data.message, "success");
    await loadInvoices();
    await loadDashboard();
  } catch (err) {
    showToast("Error processing payment", "danger");
  }
}

async function viewPrintableInvoice(invoiceId) {
  try {
    const res = await fetch(`/api/invoices/${invoiceId}`);
    const inv = await res.json();
    if (inv.error) return showToast(inv.error, "danger");

    const tutor = inv.tutor_profile || {};
    const cur = tutor.currency_symbol || "$";

    const container = document.getElementById("printableInvoiceContainer");
    container.innerHTML = `
      <div class="printable-invoice">
        <div class="invoice-print-header">
          <div>
            <h2 style="font-size: 20px; font-weight: 800; color: var(--navy-900);">${tutor.business_name || "Apex Tutoring Studio"}</h2>
            <p style="font-size: 13px; color: var(--navy-600);">${tutor.tutor_name || "Alex Morgan"} &bull; ${tutor.tutor_phone || ""}</p>
            <p style="font-size: 12px; color: var(--navy-500);">${tutor.tutor_email || ""}</p>
          </div>
          <div class="invoice-print-meta">
            <h2>INVOICE</h2>
            <p style="font-size: 14px; font-weight: 700; color: var(--purple-700);">#${inv.invoice_number}</p>
            <p style="font-size: 12px; color: var(--navy-500);">Issue Date: ${inv.issue_date}</p>
            <p style="font-size: 12px; font-weight: 600; color: ${inv.status === 'Overdue' ? 'var(--rose-600)' : 'var(--navy-700)'};">Due Date: ${inv.due_date}</p>
          </div>
        </div>

        <div class="invoice-parties">
          <div class="party-box">
            <h4>Billed To (Parent / Guardian)</h4>
            <div style="font-weight: 700; font-size: 14px;">${inv.parent_name}</div>
            <div>Student: <strong>${inv.student_name}</strong></div>
            <div style="font-size: 12px; color: var(--navy-600);">${inv.parent_phone}</div>
            ${inv.parent_email ? `<div style="font-size: 12px; color: var(--navy-600);">${inv.parent_email}</div>` : ''}
          </div>
          <div class="party-box">
            <h4>Course / Subject</h4>
            <div style="font-weight: 600;">${inv.subject_grade}</div>
            <div style="margin-top: 6px;">Status: <span class="badge ${inv.status === 'Paid' ? 'badge-success' : 'badge-warning'}">${inv.status}</span></div>
          </div>
        </div>

        <table class="invoice-items-table">
          <thead>
            <tr>
              <th>Description</th>
              <th style="text-align: right;">Amount</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>
                <div style="font-weight: 600;">${inv.description || "Monthly Tutoring Fee"}</div>
                <div style="font-size: 12px; color: var(--navy-500);">${inv.notes || "Professional home tutoring sessions"}</div>
              </td>
              <td style="text-align: right; font-weight: 700; font-size: 14px;">${cur}${inv.amount.toFixed(2)}</td>
            </tr>
          </tbody>
        </table>

        <div class="invoice-total-summary">
          <div class="total-summary-box">
            <div class="total-summary-row">
              <span>Subtotal:</span>
              <span>${cur}${inv.amount.toFixed(2)}</span>
            </div>
            <div class="total-summary-row grand-total">
              <span>Total Due:</span>
              <span>${cur}${inv.amount.toFixed(2)}</span>
            </div>
          </div>
        </div>

        <div class="invoice-payment-instructions">
          <div style="font-weight: 700; margin-bottom: 4px; color: var(--navy-900);">Settlement Instructions:</div>
          <div>${tutor.payment_info || "Bank transfer or Zelle / UPI"}</div>
        </div>
      </div>
    `;

    openModal("printableInvoiceModal");
  } catch (err) {
    showToast("Failed to load invoice for printing", "danger");
  }
}

async function confirmDeleteInvoice(invoiceId, invNum) {
  if (!confirm(`Are you sure you want to delete Invoice #${invNum}?`)) return;

  try {
    const res = await fetch(`/api/invoices/${invoiceId}`, { method: "DELETE" });
    const data = await res.json();
    showToast(data.message, "success");
    await loadInvoices();
    await loadDashboard();
  } catch (err) {
    showToast("Failed to delete invoice", "danger");
  }
}

// ============================================================================
// 4. Cash Flow Forecast Module
// ============================================================================
async function loadForecast(horizonDays = 30) {
  try {
    const res = await fetch("/api/forecast");
    const data = await res.json();
    CashPilot.forecastData = data;

    // Update active horizon buttons
    document.querySelectorAll(".forecast-tab-btn").forEach(btn => {
      btn.classList.toggle("active", parseInt(btn.dataset.horizon, 10) === horizonDays);
    });

    const cur = data.currency || "$";
    const horizonKey = `day_${horizonDays}`;
    const horizonObj = data[horizonKey] || data.day_30;

    // Update high-level forecast metric cards
    document.getElementById("forecastCurrentBal").textContent = `${cur}${data.current_balance.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    document.getElementById("forecastProjectedBal").textContent = `${cur}${horizonObj.projected_balance.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;

    const netChangeEl = document.getElementById("forecastNetChange");
    const isPositive = horizonObj.net_change >= 0;
    netChangeEl.textContent = `${isPositive ? '+' : ''}${cur}${horizonObj.net_change.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    netChangeEl.style.color = isPositive ? "var(--green-600)" : "var(--rose-600)";

    document.getElementById("forecastInflows").textContent = `${cur}${horizonObj.inflows.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    document.getElementById("forecastOutflows").textContent = `${cur}${horizonObj.outflows.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;

    document.getElementById("forecastMinBal").textContent = `${cur}${data.min_balance.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    document.getElementById("forecastMinDate").textContent = `Lowest on ${data.min_balance_date}`;

    const healthBadge = document.getElementById("forecastHealthBadge");
    healthBadge.className = `badge badge-${data.health_badge}`;
    healthBadge.innerHTML = `<span class="badge-dot"></span>${data.health_status}`;

    // Render Chart
    renderCashForecastChart(data.timeline, horizonDays);

    // Render Explanations
    const expContainer = document.getElementById("forecastExplanationsList");
    if (expContainer && data.explanations) {
      expContainer.innerHTML = data.explanations.map(bullet => `
        <li style="margin-bottom: 8px; font-size: 13px; line-height: 1.5;">${bullet.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')}</li>
      `).join("");
    }

  } catch (err) {
    console.error("Forecast fetch failed:", err);
    showToast("Error calculating cash forecast", "danger");
  }
}

// ============================================================================
// 5. What-If Scenario Simulator Module
// ============================================================================
async function initWhatIfSimulator(preselectedInvoiceId = null) {
  const select = document.getElementById("whatifInvoiceSelect");
  if (!select) return;

  try {
    const res = await fetch("/api/invoices");
    const invoices = await res.json();
    const unpaid = invoices.filter(inv => inv.status === "Pending" || inv.status === "Overdue");

    select.innerHTML = "";
    if (unpaid.length === 0) {
      select.innerHTML = "<option value=''>No unpaid invoices to simulate</option>";
      return;
    }

    unpaid.forEach(inv => {
      const opt = document.createElement("option");
      opt.value = inv.id;
      opt.textContent = `${inv.student_name} ($${inv.amount.toFixed(2)} - ${inv.invoice_number})`;
      select.appendChild(opt);
    });

    if (preselectedInvoiceId) {
      select.value = preselectedInvoiceId;
    }

    // Run simulation with initial defaults
    await runWhatIfSimulation();

  } catch (err) {
    console.error("Failed to init whatif simulator:", err);
  }
}

async function runWhatIfSimulation() {
  const select = document.getElementById("whatifInvoiceSelect");
  const invoiceId = select ? select.value : null;
  const delayDays = parseInt(document.getElementById("whatifDelaySelect").value, 10) || 15;
  const extraExpense = parseFloat(document.getElementById("whatifExtraExpenseInput").value) || 0.0;

  if (!invoiceId) {
    showToast("Please choose an unpaid invoice to simulate", "danger");
    return;
  }

  try {
    const res = await fetch("/api/whatif", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        invoice_id: invoiceId,
        delay_days: delayDays,
        unexpected_expense: extraExpense
      })
    });

    const data = await res.json();
    if (data.error) {
      showToast(data.error, "danger");
      return;
    }

    // Render impact summary
    const summary = data.impact_summary;
    const cur = CashPilot.currency || "$";

    const badgeEl = document.getElementById("whatifSeverityBadge");
    badgeEl.className = `badge badge-${summary.badge}`;
    badgeEl.innerHTML = `<span class="badge-dot"></span>${summary.severity}`;

    document.getElementById("whatifStudentInfo").textContent = `Simulating: ${summary.student_name}'s payment of ${cur}${summary.amount.toFixed(2)} delayed by ${summary.delay_days} days`;
    document.getElementById("whatifBaseMin").textContent = `${cur}${summary.base_min_balance.toFixed(2)}`;
    document.getElementById("whatifSimMin").textContent = `${cur}${summary.simulated_min_balance.toFixed(2)}`;

    const dipEl = document.getElementById("whatifCashDip");
    dipEl.textContent = `-${cur}${summary.max_cash_dip.toFixed(2)}`;

    const recBox = document.getElementById("whatifRecommendationBox");
    recBox.innerHTML = `<strong>Financial Recommendation:</strong> ${summary.action_recommendation}`;

    // Render Side-by-Side Comparison Chart
    renderWhatIfComparisonChart(data.timeline_comparison);

  } catch (err) {
    console.error("Simulation run error:", err);
    showToast("Failed to calculate scenario impact", "danger");
  }
}

// ============================================================================
// 6. Smart Alerts Module
// ============================================================================
async function loadSmartAlertsView() {
  try {
    const res = await fetch("/api/alerts");
    const alerts = await res.json();

    const container = document.getElementById("smartAlertsListContainer");
    if (!container) return;

    if (alerts.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon" style="background: var(--green-50); color: var(--green-600);">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
          </div>
          <h4 class="empty-state-title">No Urgent Action Items</h4>
          <p class="empty-state-text">All invoices are up-to-date and no immediate bills require attention today. Excellent cash discipline!</p>
        </div>
      `;
      return;
    }

    container.innerHTML = alerts.map(a => `
      <div class="alert-card ${a.level}">
        <div class="alert-card-left">
          <div class="alert-type-icon">
            ${a.level === 'danger' ? `
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
            ` : (a.level === 'warning' ? `
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 14 14"/></svg>
            ` : `
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect width="20" height="14" x="2" y="5" rx="2"/><line x1="2" x2="22" y1="10" y2="10"/></svg>
            `)}
          </div>
          <div>
            <div class="alert-title">${a.title}</div>
            <div class="alert-desc">${a.message}</div>
            <div class="alert-meta">
              <span><strong>Amount:</strong> ${CashPilot.currency}${a.amount.toFixed(2)}</span>
              <span><strong>Due:</strong> ${a.due_date}</span>
            </div>
          </div>
        </div>
        <div>
          <button class="btn btn-sm btn-primary" onclick="handleAlertAction('${a.action_type}', ${a.target_id})">${a.action_label}</button>
        </div>
      </div>
    `).join("");

    if (window.lucide) lucide.createIcons();

  } catch (err) {
    console.error("Alerts view error:", err);
  }
}

function handleAlertAction(actionType, targetId) {
  if (actionType === "reminder") {
    navigateTo("reminders", targetId);
  } else if (actionType === "mark_paid") {
    // Open payment modal for invoice
    fetch(`/api/invoices/${targetId}`).then(r => r.json()).then(inv => {
      openMarkPaidModal(inv.id, inv.invoice_number, inv.amount);
    });
  } else if (actionType === "pay_expense") {
    openPayExpenseModal(targetId);
  }
}

// ============================================================================
// 7. Expense Management Module
// ============================================================================
async function loadExpenses() {
  const search = document.getElementById("expenseSearchInput")?.value || "";
  const cat = document.getElementById("expenseCategoryFilter")?.value || "All";
  const status = document.getElementById("expenseStatusFilter")?.value || "All";

  try {
    const res = await fetch(`/api/expenses?q=${encodeURIComponent(search)}&category=${encodeURIComponent(cat)}&status=${encodeURIComponent(status)}`);
    const expenses = await res.json();
    CashPilot.expenses = expenses;

    const tbody = document.getElementById("expensesTableBody");
    if (!tbody) return;

    if (expenses.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="6" class="empty-state">
            <div class="empty-state-icon">
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect width="20" height="14" x="2" y="5" rx="2"/><line x1="2" x2="22" y1="10" y2="10"/></svg>
            </div>
            <h4 class="empty-state-title">No Expenses Recorded</h4>
            <p class="empty-state-text">Keep track of software, books, teaching materials, and transport costs.</p>
            <button class="btn btn-sm btn-primary" onclick="openAddExpenseModal()">+ Add Overhead Expense</button>
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = expenses.map(exp => {
      const isPaid = exp.status === "Paid";
      const badgeClass = isPaid ? "badge-success" : "badge-warning";
      return `
        <tr>
          <td>
            <div class="primary-cell">${exp.title}</div>
            <div class="sub-cell">${exp.notes || ""}</div>
          </td>
          <td><span class="badge badge-purple">${exp.category}</span></td>
          <td class="amount-cell">${CashPilot.currency}${exp.amount.toFixed(2)}</td>
          <td>${exp.due_date}</td>
          <td><span class="badge ${badgeClass}"><span class="badge-dot"></span>${exp.status}</span></td>
          <td class="actions-cell">
            ${!isPaid ? `
              <button class="btn btn-sm btn-success" title="Mark Paid" onclick="openPayExpenseModal(${exp.id}, '${exp.title}', ${exp.amount})">✓ Pay</button>
            ` : `
              <span style="font-size: 12px; color: var(--green-600); font-weight: 600; padding: 4px 6px;">Paid</span>
            `}
            <button class="btn btn-sm btn-danger-outline" title="Delete Expense" onclick="confirmDeleteExpense(${exp.id}, '${exp.title}')">×</button>
          </td>
        </tr>
      `;
    }).join("");

    if (window.lucide) lucide.createIcons();

  } catch (err) {
    console.error("Failed to load expenses:", err);
  }
}

function openAddExpenseModal() {
  document.getElementById("expenseForm").reset();
  document.getElementById("expenseDueDateInput").value = new Date().toISOString().split("T")[0];
  openModal("expenseModal");
}

async function handleExpenseFormSubmit(e) {
  e.preventDefault();
  const payload = {
    title: document.getElementById("expenseTitleInput").value.trim(),
    category: document.getElementById("expenseCategoryInput").value,
    amount: parseFloat(document.getElementById("expenseAmountInput").value),
    due_date: document.getElementById("expenseDueDateInput").value,
    status: document.getElementById("expenseStatusInput").value,
    notes: document.getElementById("expenseNotesInput").value.trim()
  };

  try {
    const res = await fetch("/api/expenses", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();

    if (!res.ok) {
      showToast(data.error || "Failed to record expense", "danger");
      return;
    }

    closeModal("expenseModal");
    showToast(data.message, "success");
    await loadExpenses();
    await loadDashboard();
  } catch (err) {
    showToast("Error creating expense", "danger");
  }
}

function openPayExpenseModal(expenseId, title, amount) {
  document.getElementById("payExpenseId").value = expenseId;
  document.getElementById("payExpenseDetailsText").textContent = title ? `Settling expense: ${title} ($${amount.toFixed(2)})` : "Settling expense payment";
  document.getElementById("payExpenseDateInput").value = new Date().toISOString().split("T")[0];
  openModal("payExpenseModal");
}

async function handlePayExpenseSubmit(e) {
  e.preventDefault();
  const expId = document.getElementById("payExpenseId").value;
  const payload = {
    paid_date: document.getElementById("payExpenseDateInput").value,
    payment_method: document.getElementById("payExpenseMethodSelect").value
  };

  try {
    const res = await fetch(`/api/expenses/${expId}/pay`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    closeModal("payExpenseModal");
    showToast(data.message, "success");
    await loadExpenses();
    await loadDashboard();
  } catch (err) {
    showToast("Error recording expense payment", "danger");
  }
}

async function confirmDeleteExpense(expenseId, title) {
  if (!confirm(`Are you sure you want to delete expense "${title}"?`)) return;

  try {
    const res = await fetch(`/api/expenses/${expenseId}`, { method: "DELETE" });
    const data = await res.json();
    showToast(data.message, "success");
    await loadExpenses();
    await loadDashboard();
  } catch (err) {
    showToast("Failed to delete expense", "danger");
  }
}

// ============================================================================
// 8. Settings & Profile Module
// ============================================================================
async function loadSettings() {
  try {
    const res = await fetch("/api/settings");
    const s = await res.json();
    CashPilot.settings = s;
    CashPilot.currency = s.currency_symbol || "$";

    // Update Sidebar footer profile preview
    const tutorNameEl = document.getElementById("sidebarTutorName");
    const bizNameEl = document.getElementById("sidebarBizName");
    const avatarEl = document.getElementById("sidebarTutorAvatar");

    if (tutorNameEl) tutorNameEl.textContent = s.tutor_name || "Alex Morgan";
    if (bizNameEl) bizNameEl.textContent = s.business_name || "Home Tutoring";
    if (avatarEl && s.tutor_name) avatarEl.textContent = s.tutor_name.charAt(0);

  } catch (err) {
    console.error("Failed to load settings:", err);
  }
}

async function loadSettingsView() {
  await loadSettings();
  const s = CashPilot.settings;

  document.getElementById("settingsTutorName").value = s.tutor_name || "";
  document.getElementById("settingsBizName").value = s.business_name || "";
  document.getElementById("settingsPhone").value = s.tutor_phone || "";
  document.getElementById("settingsEmail").value = s.tutor_email || "";
  document.getElementById("settingsPaymentInfo").value = s.payment_info || "";
  document.getElementById("settingsStartingCash").value = s.starting_cash_balance || 2450.0;
  document.getElementById("settingsSafetyBuffer").value = s.min_safety_buffer || 1000.0;
  document.getElementById("settingsCurrency").value = s.currency_symbol || "$";
}

async function handleSettingsFormSubmit(e) {
  e.preventDefault();
  const payload = {
    tutor_name: document.getElementById("settingsTutorName").value.trim(),
    business_name: document.getElementById("settingsBizName").value.trim(),
    tutor_phone: document.getElementById("settingsPhone").value.trim(),
    tutor_email: document.getElementById("settingsEmail").value.trim(),
    payment_info: document.getElementById("settingsPaymentInfo").value.trim(),
    starting_cash_balance: parseFloat(document.getElementById("settingsStartingCash").value),
    min_safety_buffer: parseFloat(document.getElementById("settingsSafetyBuffer").value),
    currency_symbol: document.getElementById("settingsCurrency").value.trim()
  };

  try {
    const res = await fetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();

    if (!res.ok) {
      showToast(data.error || "Failed to update settings", "danger");
      return;
    }

    showToast(data.message, "success");
    await loadSettings();
    await loadDashboard();
  } catch (err) {
    showToast("Error updating settings", "danger");
  }
}

async function confirmResetDemoData() {
  if (!confirm("Reset demo data? This will restore realistic sample students, invoices, and expenses for judges to explore.")) {
    return;
  }

  try {
    const res = await fetch("/api/reset-data", { method: "POST" });
    const data = await res.json();
    showToast(data.message, "success");
    await loadSettings();
    await navigateTo(CashPilot.currentView);
  } catch (err) {
    showToast("Error resetting sample data", "danger");
  }
}

// ============================================================================
// Modal & Toast Helpers
// ============================================================================
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.add("active");
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.remove("active");
}

function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <span>${message}</span>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(12px)";
    toast.style.transition = "all 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

function setupEventListeners() {
  // Mobile sidebar toggle
  const menuBtn = document.getElementById("mobileMenuBtn");
  const sidebar = document.querySelector(".sidebar");
  if (menuBtn && sidebar) {
    menuBtn.addEventListener("click", () => {
      sidebar.classList.toggle("mobile-open");
    });
  }

  // Close modals on overlay backdrop click
  document.querySelectorAll(".modal-overlay").forEach(overlay => {
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) {
        overlay.classList.remove("active");
      }
    });
  });

  // Reminder Template Radio Switcher
  document.querySelectorAll("input[name='reminderTemplate']").forEach(radio => {
    radio.addEventListener("change", () => {
      document.querySelectorAll(".template-radio-label").forEach(lbl => lbl.classList.remove("selected"));
      radio.closest(".template-radio-label")?.classList.add("selected");
      loadReminderContent();
    });
  });
}
