const IDENTITIES = {
  founder: {
    username: "ssabbani",
    roles: ["founder"],
  },
  sales_rep: {
    username: "ssabbani",
    roles: ["sales_rep"],
  },
  sales_manager: {
    username: "ssabbani",
    roles: ["sales_manager"],
  },
};

const state = {
  activeSkill: "pipeline-summary",
  accounts: [],
  opportunities: [],
  skills: {},
  objects: [],
  selectedObject: null,
  proposals: [],
  selectedProposal: null,
  prPreviews: [],
  issuePreviews: [],
  auditEvents: [],
  selectedAuditEvent: null,
};

const money = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

function byId(id) {
  return document.getElementById(id);
}

function currentIdentity() {
  return IDENTITIES[byId("identitySelect").value] || IDENTITIES.founder;
}

function authHeaders() {
  const identity = currentIdentity();
  return {
    "X-Opra-User": identity.username,
    "X-Opra-Roles": identity.roles.join(","),
  };
}

async function fetchJson(path, options = {}) {
  const headers = { ...authHeaders(), ...(options.headers || {}) };
  const request = { ...options, headers };
  if (options.body !== undefined) {
    request.headers = {
      ...headers,
      "Content-Type": "application/json",
    };
    request.body = JSON.stringify(options.body);
  }

  const response = await fetch(path, request);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || data.summary || `Request failed: ${path}`);
  }
  return data;
}

function setStatus(message) {
  byId("statusLine").textContent = message;
}

async function loadWorkspace() {
  setStatus("Loading workspace");
  const results = await Promise.allSettled([
    loadDashboard(),
    loadObjects(),
    loadProposals(),
    loadPreviews(),
    loadAuditEvents(),
  ]);
  const rejected = results.find((result) => result.status === "rejected");
  if (rejected) {
    setStatus(rejected.reason.message);
    return;
  }
  setStatus("Workspace loaded");
}

async function loadDashboard() {
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
}

async function loadObjects() {
  const filter = byId("objectTypeFilter").value;
  const query = filter ? `?object_type=${encodeURIComponent(filter)}` : "";
  const payload = await fetchJson(`/objects${query}`);
  state.objects = payload.objects || [];
  renderObjects();
  if (!state.selectedObject && state.objects.length) {
    await selectObject(state.objects[0].path);
  }
}

async function loadProposals() {
  const payload = await fetchJson("/proposals");
  state.proposals = payload.proposals || [];
  renderProposals();
}

async function loadPreviews() {
  const [prs, issues] = await Promise.all([
    fetchJson("/github/previews/prs"),
    fetchJson("/github/previews/issues"),
  ]);
  state.prPreviews = prs.pull_requests || [];
  state.issuePreviews = issues.issues || [];
  renderPreviews();
}

async function loadAuditEvents() {
  const payload = await fetchJson("/audit/events");
  state.auditEvents = payload.events || [];
  renderAuditEvents();
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
  byId("skillOutput").textContent = pretty(result.data);
}

function renderObjects() {
  byId("objectCount").textContent = `${state.objects.length} files`;
  const rows = state.objects.map((object) => `
    <button class="list-row ${selectedClass(state.selectedObject, object.path)}" type="button" data-object-path="${escapeHtml(object.path)}">
      <span>
        <strong>${escapeHtml(object.name || object.id)}</strong>
        <small>${escapeHtml(object.object_type)} / ${escapeHtml(object.id)}</small>
      </span>
      <em>${escapeHtml(String(object.version || ""))}</em>
    </button>
  `);
  byId("objectList").innerHTML = rows.join("") || `<p class="empty">No records</p>`;
}

async function selectObject(path) {
  const payload = await fetchJson(`/object?path=${encodeURIComponent(path)}`);
  state.selectedObject = payload;
  byId("selectedObjectTitle").textContent = `${payload.object.object_type}/${payload.object.id}`;
  byId("selectedObjectPath").textContent = payload.path;
  byId("objectEditor").value = pretty(payload.object);
  byId("requestId").value = requestId("ui");
  byId("recordFields").value = "";
  byId("recordResultSummary").textContent = "Record loaded";
  byId("recordOutput").textContent = pretty({
    path: payload.path,
    hash: payload.hash,
  });
  renderObjects();
}

function renderProposals() {
  byId("proposalCount").textContent = `${state.proposals.length} files`;
  const rows = state.proposals.map((item) => {
    const proposal = item.proposal;
    return `
      <button class="list-row ${selectedClass(state.selectedProposal, item.path)}" type="button" data-proposal-path="${escapeHtml(item.path)}">
        <span>
          <strong>${escapeHtml(proposal.id)}</strong>
          <small>${escapeHtml(proposal.object_type)} / ${escapeHtml(proposal.object_id)}</small>
        </span>
        <em class="status-pill ${escapeHtml(proposal.status)}">${escapeHtml(proposal.status)}</em>
      </button>
    `;
  });
  byId("proposalList").innerHTML = rows.join("") || `<p class="empty">No proposals</p>`;
  if (!state.selectedProposal && state.proposals.length) {
    selectProposal(state.proposals[0].path);
  } else {
    renderSelectedProposal();
  }
}

function selectProposal(path) {
  state.selectedProposal = state.proposals.find((item) => item.path === path) || null;
  renderProposals();
  renderSelectedProposal();
}

function renderSelectedProposal() {
  const selected = state.selectedProposal;
  if (!selected) {
    byId("selectedProposalTitle").textContent = "Proposal";
    byId("selectedProposalPath").textContent = "No proposal selected";
    byId("proposalFacts").innerHTML = "";
    byId("proposalOutput").textContent = "{}";
    return;
  }

  const proposal = selected.proposal;
  byId("selectedProposalTitle").textContent = proposal.id;
  byId("selectedProposalPath").textContent = selected.path;
  byId("proposalFacts").innerHTML = [
    ["Status", proposal.status],
    ["Action", proposal.action],
    ["Object", `${proposal.object_type}/${proposal.object_id}`],
    ["Decision", proposal.policy_decision],
    ["Remaining", selected.remaining_approvers.join(", ") || "none"],
  ].map(([name, value]) => `
    <span><strong>${escapeHtml(name)}</strong>${escapeHtml(value)}</span>
  `).join("");
  byId("proposalOutput").textContent = pretty(selected);
}

function renderPreviews() {
  byId("prPreviewCount").textContent = `${state.prPreviews.length} files`;
  byId("prPreviewList").innerHTML = state.prPreviews.map((item) => {
    const preview = item.preview;
    const pullRequest = preview.pull_request || {};
    return `
      <button class="list-row" type="button" data-preview-path="${escapeHtml(item.path)}">
        <span>
          <strong>${escapeHtml(preview.proposal_id || pullRequest.title || item.path)}</strong>
          <small>${escapeHtml(pullRequest.url || item.path)}</small>
        </span>
        <em>${escapeHtml(preview.branch_name || "")}</em>
      </button>
    `;
  }).join("") || `<p class="empty">No PR previews</p>`;

  byId("issuePreviewCount").textContent = `${state.issuePreviews.length} files`;
  byId("issuePreviewList").innerHTML = state.issuePreviews.map((item) => {
    const issue = item.preview;
    return `
      <button class="list-row" type="button" data-issue-preview-path="${escapeHtml(item.path)}">
        <span>
          <strong>#${escapeHtml(issue.number)} ${escapeHtml(issue.title)}</strong>
          <small>${escapeHtml(issue.state)} - ${escapeHtml(item.path)}</small>
        </span>
        <em>${escapeHtml((issue.labels || []).join(", "))}</em>
      </button>
    `;
  }).join("") || `<p class="empty">No issue previews</p>`;
}

function renderAuditEvents() {
  byId("auditCount").textContent = `${state.auditEvents.length} files`;
  byId("auditList").innerHTML = state.auditEvents.map((item) => {
    const event = item.event;
    return `
      <button class="list-row ${selectedClass(state.selectedAuditEvent, item.path)}" type="button" data-audit-path="${escapeHtml(item.path)}">
        <span>
          <strong>${escapeHtml(event.action)} ${escapeHtml(event.object_type)}/${escapeHtml(event.object_id)}</strong>
          <small>${escapeHtml(event.actor)} - ${escapeHtml(event.timestamp)}</small>
        </span>
        <em class="status-pill ${escapeHtml(event.result)}">${escapeHtml(event.result)}</em>
      </button>
    `;
  }).join("") || `<p class="empty">No audit events</p>`;
  if (!state.selectedAuditEvent && state.auditEvents.length) {
    selectAuditEvent(state.auditEvents[0].path);
  }
}

function selectAuditEvent(path) {
  state.selectedAuditEvent = state.auditEvents.find((item) => item.path === path) || null;
  byId("auditPath").textContent = state.selectedAuditEvent ? state.selectedAuditEvent.path : "No event selected";
  byId("auditOutput").textContent = pretty(state.selectedAuditEvent || {});
  renderAuditEvents();
}

async function validateObject() {
  const payload = await recordPayload();
  const result = await fetchJson("/objects/validate", {
    method: "POST",
    body: { object: payload.object },
  });
  showRecordResult(result.valid ? "Validation passed" : "Validation failed", result);
}

async function policyCheck() {
  const payload = await recordPayload();
  const result = await fetchJson("/objects/policy-check", {
    method: "POST",
    body: {
      object: payload.object,
      action: byId("recordAction").value,
      fields: selectedFields(payload.object),
    },
  });
  showRecordResult(`Policy ${result.decision}`, result);
}

async function governedWrite() {
  const payload = await recordPayload();
  const result = await fetchJson("/objects/governed-write", {
    method: "POST",
    body: {
      object: payload.object,
      action: byId("recordAction").value,
      request_id: requestValue(),
      fields: selectedFields(payload.object),
    },
  });
  showRecordResult(result.committed ? "Write committed" : `Write ${result.decision}`, result);
  await Promise.all([loadObjects(), loadDashboard(), loadAuditEvents()]);
}

async function createProposal() {
  const payload = await recordPayload();
  const result = await fetchJson("/proposals", {
    method: "POST",
    body: {
      object: payload.object,
      action: byId("recordAction").value,
      request_id: requestValue(),
      fields: selectedFields(payload.object),
    },
  });
  showRecordResult("Proposal created", result);
  await loadProposals();
  state.selectedProposal = result;
  activateView("proposals");
  renderSelectedProposal();
}

async function proposalAction(action) {
  const selected = requireProposal();
  const body = action === "approve" || action === "reject"
    ? { reason: byId("proposalReason").value }
    : {};
  const result = await fetchJson(`/proposals/${selected.proposal.id}/${action}`, {
    method: "POST",
    body,
  });
  byId("proposalOutput").textContent = pretty(result);
  await Promise.all([loadProposals(), loadObjects(), loadDashboard(), loadAuditEvents()]);
  state.selectedProposal = state.proposals.find((item) => item.path === result.path) || result;
  renderSelectedProposal();
  setStatus(`Proposal ${action} complete`);
}

async function publishPrPreview() {
  const selected = requireProposal();
  const result = await fetchJson(`/proposals/${selected.proposal.id}/publish-pr`, {
    method: "POST",
    body: {
      base_branch: "main",
      repo_url: "https://github.com/local/opra.ai",
    },
  });
  byId("proposalOutput").textContent = pretty(result);
  await loadPreviews();
  setStatus("PR preview written");
}

async function validatePr() {
  const selected = requireProposal();
  const result = await fetchJson(`/proposals/${selected.proposal.id}/validate-pr`, {
    method: "POST",
    body: {},
  });
  byId("proposalOutput").textContent = result.report || pretty(result);
  setStatus(result.valid ? "PR check passed" : "PR check failed");
}

async function createIssuePreview() {
  const result = await fetchJson("/github/issues", {
    method: "POST",
    body: issuePayload(false),
  });
  byId("issueResultSummary").textContent = `Created #${result.issue.number}`;
  await loadPreviews();
}

async function updateIssuePreview() {
  const issueNumber = Number(byId("issueNumber").value);
  if (!issueNumber) {
    throw new Error("Issue number is required");
  }
  const result = await fetchJson(`/github/issues/${issueNumber}`, {
    method: "POST",
    body: issuePayload(true),
  });
  byId("issueResultSummary").textContent = `Updated #${result.issue.number}`;
  await loadPreviews();
}

function issuePayload(isUpdate) {
  const payload = {
    labels: csvValues(byId("issueLabels").value),
    assignees: csvValues(byId("issueAssignees").value),
  };
  const title = byId("issueTitle").value.trim();
  const body = byId("issueBody").value;
  const stateValue = byId("issueState").value;
  if (!isUpdate || title) {
    payload.title = title;
  }
  if (!isUpdate || body) {
    payload.body = body;
  }
  if (stateValue) {
    payload.state = stateValue;
  }
  return payload;
}

async function recordPayload() {
  let object;
  try {
    object = JSON.parse(byId("objectEditor").value);
  } catch (error) {
    throw new Error(`Record JSON is invalid: ${error.message}`);
  }
  if (!object || typeof object !== "object" || Array.isArray(object)) {
    throw new Error("Record JSON must be an object");
  }
  return { object };
}

function requestValue() {
  const value = byId("requestId").value.trim();
  if (value) {
    return value;
  }
  const generated = requestId("ui");
  byId("requestId").value = generated;
  return generated;
}

function requestId(prefix) {
  return `${prefix}_${new Date().toISOString().replace(/[-:.TZ]/g, "").slice(0, 14)}`;
}

function selectedFields(object) {
  const explicit = csvValues(byId("recordFields").value);
  if (explicit.length) {
    return explicit;
  }
  const changed = changedFields(state.selectedObject ? state.selectedObject.object : null, object);
  byId("recordFields").value = changed.join(",");
  return changed;
}

function changedFields(before, after) {
  if (!before || !after) {
    return [];
  }
  const keys = new Set([...Object.keys(before), ...Object.keys(after)]);
  return [...keys].filter((key) => JSON.stringify(before[key]) !== JSON.stringify(after[key]));
}

function requireProposal() {
  if (!state.selectedProposal) {
    throw new Error("No proposal selected");
  }
  return state.selectedProposal;
}

function showRecordResult(summary, payload) {
  byId("recordResultSummary").textContent = summary;
  byId("recordOutput").textContent = pretty(payload);
  setStatus(summary);
}

function setActiveSkill(name) {
  state.activeSkill = name;
  document.querySelectorAll("[data-skill]").forEach((button) => {
    button.classList.toggle("active", button.dataset.skill === name);
  });
  renderSkill();
}

function activateView(name) {
  document.querySelectorAll("[data-view]").forEach((button) => {
    button.classList.toggle("active", button.dataset.view === name);
  });
  document.querySelectorAll(".view").forEach((view) => {
    view.classList.toggle("active", view.id === `${name}View`);
  });
}

function emptyRow(columns, text) {
  return `<tr><td colspan="${columns}">${escapeHtml(text)}</td></tr>`;
}

function label(value) {
  return escapeHtml(String(value || "").replaceAll("_", " "));
}

function pretty(value) {
  return JSON.stringify(value || {}, null, 2);
}

function selectedClass(item, path) {
  return item && item.path === path ? "selected" : "";
}

function csvValues(value) {
  return String(value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function bindAsync(id, callback) {
  byId(id).addEventListener("click", () => {
    callback().catch((error) => setStatus(error.message));
  });
}

document.querySelectorAll("[data-view]").forEach((button) => {
  button.addEventListener("click", () => activateView(button.dataset.view));
});

document.querySelectorAll("[data-skill]").forEach((button) => {
  button.addEventListener("click", () => setActiveSkill(button.dataset.skill));
});

byId("objectList").addEventListener("click", (event) => {
  const row = event.target.closest("[data-object-path]");
  if (!row) {
    return;
  }
  selectObject(row.dataset.objectPath).catch((error) => setStatus(error.message));
});

byId("proposalList").addEventListener("click", (event) => {
  const row = event.target.closest("[data-proposal-path]");
  if (row) {
    selectProposal(row.dataset.proposalPath);
  }
});

byId("issuePreviewList").addEventListener("click", (event) => {
  const row = event.target.closest("[data-issue-preview-path]");
  if (!row) {
    return;
  }
  const item = state.issuePreviews.find((preview) => preview.path === row.dataset.issuePreviewPath);
  if (!item) {
    return;
  }
  const issue = item.preview;
  byId("issueNumber").value = issue.number || "";
  byId("issueTitle").value = issue.title || "";
  byId("issueBody").value = issue.body || "";
  byId("issueState").value = issue.state || "";
  byId("issueLabels").value = (issue.labels || []).join(",");
  byId("issueAssignees").value = (issue.assignees || []).join(",");
});

byId("auditList").addEventListener("click", (event) => {
  const row = event.target.closest("[data-audit-path]");
  if (row) {
    selectAuditEvent(row.dataset.auditPath);
  }
});

byId("objectEditor").addEventListener("input", () => {
  try {
    const object = JSON.parse(byId("objectEditor").value);
    byId("recordFields").value = changedFields(
      state.selectedObject ? state.selectedObject.object : null,
      object,
    ).join(",");
  } catch {
    return;
  }
});

byId("identitySelect").addEventListener("change", () => {
  loadWorkspace().catch((error) => setStatus(error.message));
});

byId("objectTypeFilter").addEventListener("change", () => {
  state.selectedObject = null;
  loadObjects().catch((error) => setStatus(error.message));
});

bindAsync("refreshButton", loadWorkspace);
bindAsync("validateObjectButton", validateObject);
bindAsync("policyCheckButton", policyCheck);
bindAsync("governedWriteButton", governedWrite);
bindAsync("createProposalButton", createProposal);
bindAsync("approveProposalButton", () => proposalAction("approve"));
bindAsync("rejectProposalButton", () => proposalAction("reject"));
bindAsync("applyProposalButton", () => proposalAction("apply"));
bindAsync("publishPrButton", publishPrPreview);
bindAsync("validatePrButton", validatePr);
bindAsync("createIssueButton", createIssuePreview);
bindAsync("updateIssueButton", updateIssuePreview);

loadWorkspace().catch((error) => {
  setStatus(error.message);
});
