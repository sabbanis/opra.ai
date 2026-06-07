const DEV_HEADERS = {
  "X-Company-OS-User": "ssabbani",
  "X-Company-OS-Roles": "sales_rep",
};

const state = {
  activeSkill: "pipeline-summary",
  accounts: [],
  opportunities: [],
  skills: {},
};

const money = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

function byId(id) {
  return document.getElementById(id);
}

async function fetchJson(path) {
  const response = await fetch(path, { headers: DEV_HEADERS });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || data.summary || `Request failed: ${path}`);
  }
  return data;
}

async function loadDashboard() {
  byId("statusLine").textContent = "Loading CRM data";
  const [summary, accounts, opportunities, pipeline, renewal, opportunityView] =
    await Promise.all([
      fetchJson("/crm/summary"),
      fetchJson("/crm/accounts"),
      fetchJson("/crm/opportunities"),
      fetchJson("/crm/skills/pipeline-summary"),
      fetchJson("/crm/skills/renewal-health"),
      fetchJson("/crm/skills/opportunity-view"),
    ]);

  state.accounts = accounts.accounts || [];
  state.opportunities = opportunities.opportunities || [];
  state.skills = {
    "pipeline-summary": pipeline,
    "renewal-health": renewal,
    "opportunity-view": opportunityView,
  };

  renderSummary(summary);
  renderAccounts();
  renderOpportunities();
  renderSkill();
  byId("statusLine").textContent = "CRM data loaded";
}

function renderSummary(payload) {
  const summary = payload.summary;
  byId("accountCount").textContent = summary.account_count;
  byId("totalArr").textContent = money.format(summary.total_arr);
  byId("openPipeline").textContent = money.format(summary.open_pipeline_amount);
  byId("weightedPipeline").textContent = money.format(summary.weighted_pipeline_amount);
  byId("atRisk").textContent = summary.at_risk_account_count;
  byId("generatedAt").textContent = `Generated ${payload.generated_at}`;
}

function renderAccounts() {
  const rows = state.accounts.map((account) => `
    <tr>
      <td><strong>${escapeHtml(account.name)}</strong><span>${escapeHtml(account.id)}</span></td>
      <td><span class="pill">${label(account.stage)}</span></td>
      <td><span class="pill ${escapeHtml(account.health)}">${label(account.health)}</span></td>
      <td>${money.format(account.arr)}</td>
      <td>${escapeHtml(account.renewal_date)}</td>
      <td>${money.format(account.open_pipeline_amount)}</td>
    </tr>
  `);
  byId("accountsTable").innerHTML = rows.join("") || emptyRow(6, "No accounts");
}

function renderOpportunities() {
  const openRows = state.opportunities.filter(
    (opportunity) =>
      !["closed_won", "closed_lost", "renewed", "churned"].includes(opportunity.stage),
  );
  byId("opportunityCount").textContent = `${openRows.length} open records`;
  const rows = openRows.map((opportunity) => `
    <tr>
      <td>
        <strong>${escapeHtml(opportunity.id)}</strong>
        <span>${escapeHtml(opportunity.next_step)}</span>
      </td>
      <td>${escapeHtml(opportunity.account_name || opportunity.account_id)}</td>
      <td><span class="pill">${label(opportunity.stage)}</span></td>
      <td>${money.format(opportunity.amount)}</td>
      <td>${money.format(opportunity.weighted_amount)}</td>
      <td>${escapeHtml(opportunity.close_date)}</td>
    </tr>
  `);
  byId("opportunitiesTable").innerHTML = rows.join("") || emptyRow(6, "No open opportunities");
}

function renderSkill() {
  const result = state.skills[state.activeSkill];
  if (!result) {
    return;
  }
  byId("skillSummary").textContent = result.summary;
  byId("skillOutput").textContent = JSON.stringify(result.data, null, 2);
}

function emptyRow(columns, text) {
  return `<tr><td colspan="${columns}">${escapeHtml(text)}</td></tr>`;
}

function label(value) {
  return escapeHtml(String(value || "").replaceAll("_", " "));
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function setActiveSkill(name) {
  state.activeSkill = name;
  document.querySelectorAll("[data-skill]").forEach((button) => {
    button.classList.toggle("active", button.dataset.skill === name);
  });
  renderSkill();
}

document.querySelectorAll("[data-skill]").forEach((button) => {
  button.addEventListener("click", () => setActiveSkill(button.dataset.skill));
});

byId("refreshButton").addEventListener("click", () => {
  loadDashboard().catch((error) => {
    byId("statusLine").textContent = error.message;
  });
});

loadDashboard().catch((error) => {
  byId("statusLine").textContent = error.message;
});
