/**
 * CashPilot Payment Reminders Module
 * Generates polite, customizable reminders with 1-click clipboard copy
 * and WhatsApp deep-link generation.
 */

let currentReminderData = null;

/**
 * Initializes the Reminders Studio dropdown and templates.
 */
async function initReminderStudio(preselectedInvoiceId = null) {
  const selectEl = document.getElementById("reminderInvoiceSelect");
  if (!selectEl) return;

  try {
    const res = await fetch("/api/invoices");
    const invoices = await res.json();

    // Filter to unpaid invoices (Pending or Overdue)
    const unpaid = invoices.filter(inv => inv.status === "Pending" || inv.status === "Overdue");

    selectEl.innerHTML = "";

    if (unpaid.length === 0) {
      selectEl.innerHTML = "<option value=''>No unpaid invoices found</option>";
      document.getElementById("reminderMessageArea").value = "All student accounts are currently settled! 🎉";
      return;
    }

    unpaid.forEach(inv => {
      const opt = document.createElement("option");
      opt.value = inv.id;
      const statusLabel = inv.status === "Overdue" ? "⚠️ OVERDUE" : "DUE";
      opt.textContent = `${inv.student_name} (${statusLabel} - $${inv.amount.toFixed(2)} - Due ${inv.due_date})`;
      selectEl.appendChild(opt);
    });

    // Select the requested invoice if provided, otherwise the first unpaid invoice
    if (preselectedInvoiceId) {
      selectEl.value = preselectedInvoiceId;
    }

    // Load reminder content for the selected invoice
    await loadReminderContent();
  } catch (err) {
    console.error("Error loading reminder invoices:", err);
  }
}

/**
 * Fetches and displays the reminder text based on the selected invoice and template.
 */
async function loadReminderContent() {
  const selectEl = document.getElementById("reminderInvoiceSelect");
  const invoiceId = selectEl ? selectEl.value : null;

  if (!invoiceId) return;

  // Determine active template
  const activeRadio = document.querySelector("input[name='reminderTemplate']:checked");
  const templateType = activeRadio ? activeRadio.value : "friendly";

  try {
    const res = await fetch(`/api/reminders/generate?invoice_id=${invoiceId}&template=${templateType}`);
    const data = await res.json();

    if (data.error) {
      showToast(data.error, "danger");
      return;
    }

    currentReminderData = data;

    // Update UI elements
    const messageArea = document.getElementById("reminderMessageArea");
    if (messageArea) {
      messageArea.value = data.body;
    }

    const parentNameBadge = document.getElementById("reminderParentName");
    if (parentNameBadge) {
      parentNameBadge.textContent = `${data.parent_name} (${data.parent_phone})`;
    }

    const whatsappBtn = document.getElementById("reminderWhatsappBtn");
    if (whatsappBtn) {
      whatsappBtn.href = data.whatsapp_url;
    }
  } catch (err) {
    console.error("Failed to generate reminder:", err);
  }
}

/**
 * Copies the current reminder message to the user's system clipboard.
 */
async function copyReminderToClipboard() {
  const messageArea = document.getElementById("reminderMessageArea");
  if (!messageArea || !messageArea.value.trim()) {
    showToast("No reminder message to copy", "danger");
    return;
  }

  const textToCopy = messageArea.value;

  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(textToCopy);
    } else {
      // Fallback for non-https/local sandboxes
      messageArea.select();
      document.execCommand("copy");
    }

    // Visual button feedback
    const copyBtn = document.getElementById("copyReminderBtn");
    if (copyBtn) {
      const origHtml = copyBtn.innerHTML;
      copyBtn.innerHTML = `
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
        Copied to Clipboard!
      `;
      copyBtn.classList.remove("btn-primary");
      copyBtn.classList.add("btn-success");

      setTimeout(() => {
        copyBtn.innerHTML = origHtml;
        copyBtn.classList.remove("btn-success");
        copyBtn.classList.add("btn-primary");
        if (window.lucide) lucide.createIcons();
      }, 2200);
    }

    showToast("Payment reminder copied to clipboard! Ready to paste into SMS or WhatsApp.", "success");
  } catch (err) {
    console.error("Clipboard copy failed:", err);
    showToast("Could not copy automatically. Please select text and copy manually.", "danger");
  }
}

/**
 * Updates WhatsApp link when the user edits the message directly in textarea.
 */
function handleReminderTextareaChange() {
  const messageArea = document.getElementById("reminderMessageArea");
  const whatsappBtn = document.getElementById("reminderWhatsappBtn");
  if (!messageArea || !whatsappBtn || !currentReminderData) return;

  const phone = currentReminderData.parent_phone.replace(/[^0-9]/g, "");
  const encoded = encodeURIComponent(messageArea.value);
  whatsappBtn.href = phone ? `https://wa.me/${phone}?text=${encoded}` : `https://wa.me/?text=${encoded}`;
}
