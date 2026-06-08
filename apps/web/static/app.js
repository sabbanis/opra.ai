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

const MODULE_META = {
  crm: {
    name: "Customers",
    glyph: "CUS",
    view: "crm",
    color: "teal",
    signal: ["Accounts", "Pipeline", "Renewals"],
    description: "Revenue, renewals, and customer health",
    templateIds: ["crm_account", "crm_opportunity"],
  },
  issues: {
    name: "Delivery",
    glyph: "DLV",
    view: "issues",
    color: "blue",
    signal: ["Defects", "Incidents", "Releases"],
    description: "Product work, incidents, and release readiness",
    templateIds: ["issue_defect", "issue_incident", "issue_release"],
  },
  hr: {
    name: "People",
    glyph: "PPL",
    view: "hr",
    color: "rose",
    signal: ["Jobs", "Candidates", "Onboarding"],
    description: "Hiring, onboarding, employee changes, and time off",
    templateIds: ["hr_job", "hr_candidate", "hr_employee", "hr_time_off"],
  },
};

const TEMPLATE_DEFS = {
  crm_account: {
    module: "crm",
    label: "Account",
    object_type: "account",
    build: () => ({
      ...baseObject("acct_new_workspace", "account"),
      name: "New Workspace Account",
      stage: "qualified",
      industry: "software",
      arr: 125000,
      health: "green",
      renewal_date: "2026-12-31",
    }),
  },
  crm_opportunity: {
    module: "crm",
    label: "Opportunity",
    object_type: "opportunity",
    build: () => ({
      ...baseObject("opp_new_workspace", "opportunity"),
      account_id: "acct_acme",
      stage: "discovery",
      amount: 175000,
      probability: 0.35,
      close_date: "2026-10-31",
      discount_requested: 0,
      next_step: "Confirm decision process",
      approval_status: "not_required",
    }),
  },
  issue_defect: {
    module: "issues",
    label: "Defect",
    object_type: "defect",
    build: () => ({
      ...baseObject("defect_new_workspace", "defect"),
      tags: ["triage"],
      metadata: {
        title: "New workspace defect",
        severity: "medium",
        state: "triage",
        owner_team: "platform",
        next_step: "Reproduce locally",
      },
    }),
  },
  issue_incident: {
    module: "issues",
    label: "Incident",
    object_type: "incident",
    build: () => ({
      ...baseObject("incident_new_workspace", "incident"),
      tags: ["incident"],
      metadata: {
        title: "New local incident",
        severity: "low",
        state: "investigating",
        started_at: nowStamp(),
        next_step: "Capture timeline",
      },
    }),
  },
  issue_release: {
    module: "issues",
    label: "Release",
    object_type: "release",
    build: () => ({
      ...baseObject("release_new_workspace", "release"),
      tags: ["release"],
      metadata: {
        name: "Workspace release candidate",
        state: "candidate",
        target_date: "2026-07-01",
        readiness: "Workbench, approvals, publishing, activity",
      },
    }),
  },
  hr_job: {
    module: "hr",
    label: "Job",
    object_type: "job",
    build: () => ({
      ...baseObject("job_new_workspace", "job", "hr_private"),
      tags: ["hiring"],
      metadata: {
        title: "Workflow Operator",
        state: "open",
        hiring_manager: "ssabbani",
        focus: "Governed local operations",
      },
    }),
  },
  hr_candidate: {
    module: "hr",
    label: "Candidate",
    object_type: "candidate",
    build: () => ({
      ...baseObject("cand_new_workspace", "candidate", "hr_private"),
      tags: ["candidate"],
      metadata: {
        display_name: "New Candidate",
        stage: "screen",
        source: "referral",
        next_step: "Schedule interview",
      },
    }),
  },
  hr_employee: {
    module: "hr",
    label: "Employee",
    object_type: "employee",
    build: () => ({
      ...baseObject("emp_new_workspace", "employee", "hr_private"),
      tags: ["employee"],
      metadata: {
        display_name: "New Employee",
        role: "Operator",
        start_date: "2026-07-01",
        manager: "ssabbani",
      },
    }),
  },
  hr_time_off: {
    module: "hr",
    label: "Time Off",
    object_type: "time_off",
    build: () => ({
      ...baseObject("time_off_new_workspace", "time_off", "hr_private"),
      tags: ["pto"],
      metadata: {
        state: "requested",
        starts_on: "2026-07-10",
        ends_on: "2026-07-12",
        approver: "ssabbani",
      },
    }),
  },
};

const state = {
  activeModule: "crm",
  activeSkill: "pipeline-summary",
  recordModuleFilter: "",
  modules: [],
  accounts: [],
  opportunities: [],
  crmSummary: null,
  dashboardGeneratedAt: "",
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
    loadModules(),
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
  renderFlowState();
  setStatus("Workspace loaded");
}

async function loadModules() {
  const payload = await fetchJson("/modules");
  state.modules = payload.modules || [];
  renderObjectTypeFilter();
  renderModules();
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
  let query = "";
  if (filter) {
    query = `?object_type=${encodeURIComponent(filter)}`;
  } else if (state.recordModuleFilter) {
    query = `?module=${encodeURIComponent(state.recordModuleFilter)}`;
  }
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

function renderModules() {
  const totalRecords = state.modules.reduce((total, module) => total + module.record_count, 0);
  const approvalCount = openApprovalRequests().length;
  byId("moduleCommandSummary").textContent =
    `${state.modules.length} operating areas, ${totalRecords} work items, ${approvalCount} approvals waiting`;

  byId("moduleTiles").innerHTML = state.modules.map((module) => {
    const meta = moduleMeta(module.id);
    const topTypes = topTypeCounts(module).slice(0, 3);
    return `
      <button class="module-tile ${meta.color} ${state.activeModule === module.id ? "active" : ""}" type="button" data-module="${escapeHtml(module.id)}">
        <span class="module-glyph">${escapeHtml(meta.glyph)}</span>
        <span class="module-copy">
          <strong>${escapeHtml(meta.name)}</strong>
          <small>${escapeHtml(meta.description || module.label)}</small>
        </span>
        <span class="module-count">${module.record_count}</span>
        <span class="mini-bars" aria-hidden="true">
          ${topTypes.map(([, count]) => `<i style="--h:${barHeight(count, module.record_count)}%"></i>`).join("")}
        </span>
      </button>
    `;
  }).join("");

  renderModuleFocus();
  renderModuleDashboards();
  renderTemplates();
  renderFlowState();
  renderCompanyDashboard();
}

function renderModuleFocus() {
  const module = activeModule();
  if (!module) {
    return;
  }
  const meta = moduleMeta(module.id);
  const typeRows = module.object_types.map((objectType) => {
    const count = module.type_counts[objectType] || 0;
    return `
      <span>
        <strong>${escapeHtml(label(objectType))}</strong>
        <em>${count}</em>
      </span>
    `;
  }).join("");

  byId("activeModuleSummary").textContent = `${meta.name} / ${module.record_count} work items`;
  byId("moduleFocus").innerHTML = `
    <div class="module-focus-top ${meta.color}">
      <span class="module-glyph">${escapeHtml(meta.glyph)}</span>
      <div>
        <strong>${escapeHtml(meta.name)}</strong>
        <small>${escapeHtml(meta.signal.join(" / "))}</small>
      </div>
    </div>
    <div class="type-grid">${typeRows}</div>
    <div class="button-row flush">
      <button type="button" data-open-module="${escapeHtml(module.id)}">Open ${escapeHtml(meta.name)}</button>
      <button class="primary" type="button" data-open-records="${escapeHtml(module.id)}">Workbench</button>
    </div>
  `;
}

function renderModuleDashboards() {
  renderOperationalModule("issues");
  renderOperationalModule("hr");
}

function renderOperationalModule(moduleId) {
  const module = moduleById(moduleId);
  if (!module) {
    return;
  }
  byId(`${moduleId}BannerSummary`).textContent = `${module.record_count} work items / ${module.object_types.length} categories`;
  byId(`${moduleId}RecordSummary`).textContent = `${module.record_count} items`;
  byId(`${moduleId}Metrics`).innerHTML = module.object_types.map((objectType) => `
    <article class="module-metric">
      <span>${escapeHtml(label(objectType))}</span>
      <strong>${module.type_counts[objectType] || 0}</strong>
    </article>
  `).join("");
  byId(`${moduleId}RecordList`).innerHTML = module.records.map((record) => recordRow(record)).join("") ||
    `<p class="empty">No work items yet</p>`;
}

function renderTemplates() {
  const active = activeModule();
  if (active) {
    byId("starterSummary").textContent = `${moduleMeta(active.id).name} forms`;
    byId("starterTemplates").innerHTML = templateButtons(active.id);
  }
  byId("issuesTemplates").innerHTML = templateButtons("issues");
  byId("hrTemplates").innerHTML = templateButtons("hr");
}

function renderFlowState() {
  const active = activeModule();
  const proposalCount = state.proposals.length;
  const auditCount = state.auditEvents.length;
  const previewCount = state.prPreviews.length + state.issuePreviews.length;
  byId("liveFlowSummary").textContent = active
    ? `${moduleMeta(active.id).name} flow`
    : "Workspace state";
  byId("flowState").innerHTML = [
    ["Workbench", active ? active.record_count : state.objects.length],
    ["Approvals", proposalCount],
    ["Publishing", previewCount],
    ["Activity", auditCount],
  ].map(([labelText, value]) => `
    <button class="flow-state-item" type="button" data-flow-view="${flowView(labelText)}">
      <strong>${escapeHtml(String(value))}</strong>
      <span>${escapeHtml(labelText)}</span>
    </button>
  `).join("");
}

function renderCompanyDashboard() {
  const homeKpis = byId("homeKpis");
  if (!homeKpis) {
    return;
  }

  const totalRecords = state.modules.reduce((total, module) => total + module.record_count, 0);
  homeKpis.innerHTML = dashboardKpis(totalRecords).map((item) => `
    <button class="home-kpi ${escapeHtml(item.tone)}" type="button" data-flow-view="${escapeHtml(item.view)}">
      <span>${escapeHtml(item.label)}</span>
      <strong>${escapeHtml(item.value)}</strong>
      <small>${escapeHtml(item.detail)}</small>
    </button>
  `).join("");

  const priority = attentionItems().slice(0, 6);
  byId("prioritySummary").textContent = priority.length
    ? `${priority.length} signals need owner attention`
    : "No active risk signals";
  byId("priorityQueue").innerHTML = priority.map(queueItemRow).join("") ||
    emptyQueue("No urgent work right now", "Open Customers, Delivery, or People to continue operating.", "modules");

  const approvals = openApprovalRequests();
  byId("approvalSummary").textContent = approvals.length
    ? `${approvals.length} waiting for a decision`
    : `${state.proposals.length} total requests`;
  byId("approvalQueue").innerHTML = approvals.slice(0, 5).map((item) => {
    const proposal = item.proposal;
    return queueItemRow({
      tone: proposal.status === "rejected" ? "red" : "amber",
      category: "Approval",
      title: `${label(proposal.action)} ${label(proposal.object_type)}`,
      detail: `${proposal.object_id} / ${label(proposal.status)}`,
      proposalPath: item.path,
    });
  }).join("") || emptyQueue("No approvals waiting", "Create a change request from the Workbench.", "records");

  byId("activitySummary").textContent = state.auditEvents.length
    ? `${state.auditEvents.length} captured events`
    : "No activity captured yet";
  byId("activityPreview").innerHTML = recentActivityItems().map(queueItemRow).join("") ||
    emptyQueue("No activity yet", "Create, update, approve, or delete work to build history.", "records");
}

function dashboardKpis(totalRecords) {
  const summary = state.crmSummary || {};
  const atRiskCount = summary.at_risk_account_count ?? atRiskAccounts().length;
  const deliveryCount = activeDeliveryItems().length;
  const peopleCount = activePeopleItems().length;
  return [
    {
      label: "Revenue",
      value: money.format(summary.total_arr || 0),
      detail: `${state.accounts.length} customers / ${money.format(summary.open_pipeline_amount || 0)} open pipeline`,
      tone: "teal",
      view: "crm",
    },
    {
      label: "Customer Risk",
      value: String(atRiskCount),
      detail: atRiskCount === 1 ? "customer needs follow-up" : "customers need follow-up",
      tone: "amber",
      view: "crm",
    },
    {
      label: "Delivery",
      value: String(deliveryCount),
      detail: `${moduleById("issues")?.record_count || 0} delivery work items`,
      tone: "blue",
      view: "issues",
    },
    {
      label: "People",
      value: String(peopleCount),
      detail: `${moduleById("hr")?.record_count || 0} people work items`,
      tone: "rose",
      view: "hr",
    },
    {
      label: "Approvals",
      value: String(openApprovalRequests().length),
      detail: `${state.proposals.length} total change requests`,
      tone: "green",
      view: "proposals",
    },
    {
      label: "Activity",
      value: String(state.auditEvents.length),
      detail: `${totalRecords} governed work items`,
      tone: "neutral",
      view: "audit",
    },
  ];
}

function attentionItems() {
  return [
    ...atRiskAccounts().map((account) => ({
      tone: account.health === "red" ? "red" : "amber",
      category: "Customer follow-up",
      title: account.name || account.id,
      detail: `${label(account.health)} health / renewal ${account.renewal_date}`,
      view: "crm",
    })),
    ...openPipelineItems().slice(0, 2),
    ...activeDeliveryItems().slice(0, 3),
    ...activePeopleItems().slice(0, 3),
  ];
}

function atRiskAccounts() {
  return state.accounts.filter((account) =>
    ["yellow", "red"].includes(String(account.health || "").toLowerCase()) ||
    ["renewal_due", "renewal_proposal"].includes(String(account.stage || "").toLowerCase()),
  );
}

function openPipelineItems() {
  return state.opportunities
    .filter((opportunity) =>
      !["closed_won", "closed_lost", "renewed", "churned"].includes(opportunity.stage),
    )
    .map((opportunity) => ({
      tone: "teal",
      category: "Pipeline next step",
      title: opportunity.account_name || opportunity.account_id || opportunity.id,
      detail: `${money.format(opportunity.amount || 0)} / ${opportunity.next_step || label(opportunity.stage)}`,
      view: "crm",
    }));
}

function activeDeliveryItems() {
  const module = moduleById("issues");
  if (!module) {
    return [];
  }
  return module.records
    .filter((record) => activeRecordState(record))
    .map((record) => ({
      tone: deliveryTone(record),
      category: label(record.object_type),
      title: recordName(record.data || record),
      detail: recordDetail(record),
      path: record.path,
    }));
}

function activePeopleItems() {
  const module = moduleById("hr");
  if (!module) {
    return [];
  }
  return module.records
    .filter((record) => activeRecordState(record))
    .map((record) => ({
      tone: "rose",
      category: label(record.object_type),
      title: recordName(record.data || record),
      detail: recordDetail(record),
      path: record.path,
    }));
}

function activeRecordState(record) {
  const data = record.data || record;
  const metadata = data.metadata || {};
  const stateValue = String(metadata.state || metadata.stage || data.status || "").toLowerCase();
  return !["", "done", "closed", "resolved", "completed", "cancelled", "inactive"].includes(stateValue);
}

function deliveryTone(record) {
  const data = record.data || record;
  const metadata = data.metadata || {};
  const severity = String(metadata.severity || metadata.priority || "").toLowerCase();
  if (record.object_type === "incident" || ["critical", "high"].includes(severity)) {
    return "amber";
  }
  return "blue";
}

function recordDetail(record) {
  const data = record.data || record;
  const metadata = data.metadata || {};
  const facts = [
    metadata.state || metadata.stage || data.status,
    metadata.next_step || metadata.approver || metadata.target_date || metadata.start_window || metadata.starts_on,
  ].filter(Boolean);
  return facts.map((item) => label(item)).join(" / ") || label(data.status || "active");
}

function openApprovalRequests() {
  return state.proposals.filter((item) => {
    const proposal = item.proposal || {};
    return ["proposed", "requires_approval"].includes(proposal.status) ||
      (item.remaining_approvers || []).length > 0;
  });
}

function recentActivityItems() {
  return state.auditEvents.slice(0, 5).map((item) => {
    const event = item.event;
    return {
      tone: event.result === "completed" ? "green" : "amber",
      category: label(event.result || "activity"),
      title: `${label(event.action)} ${label(event.object_type)}`,
      detail: `${event.object_id} / ${event.actor}`,
      auditPath: item.path,
    };
  });
}

function queueItemRow(item) {
  let attribute = `data-flow-view="${escapeHtml(item.view || "modules")}"`;
  if (item.path) {
    attribute = `data-module-record-path="${escapeHtml(item.path)}"`;
  } else if (item.proposalPath) {
    attribute = `data-proposal-path="${escapeHtml(item.proposalPath)}"`;
  } else if (item.auditPath) {
    attribute = `data-audit-path="${escapeHtml(item.auditPath)}"`;
  }
  return `
    <button class="queue-item ${escapeHtml(item.tone || "neutral")}" type="button" ${attribute}>
      <span class="queue-chip">${escapeHtml(item.category)}</span>
      <strong>${escapeHtml(item.title)}</strong>
      <small>${escapeHtml(item.detail)}</small>
    </button>
  `;
}

function emptyQueue(title, detail, view) {
  return `
    <button class="queue-empty" type="button" data-flow-view="${escapeHtml(view)}">
      <strong>${escapeHtml(title)}</strong>
      <span>${escapeHtml(detail)}</span>
    </button>
  `;
}

function renderObjectTypeFilter() {
  const select = byId("objectTypeFilter");
  const current = select.value;
  const options = [`<option value="">All work items</option>`];
  state.modules.forEach((module) => {
    options.push(`<optgroup label="${escapeHtml(module.name)}">`);
    module.object_types.forEach((objectType) => {
      options.push(`<option value="${escapeHtml(objectType)}">${escapeHtml(label(objectType))}</option>`);
    });
    options.push("</optgroup>");
  });
  select.innerHTML = options.join("");
  select.value = [...select.options].some((option) => option.value === current) ? current : "";
}

function renderSummary(payload) {
  const summary = payload.summary;
  state.crmSummary = summary;
  state.dashboardGeneratedAt = payload.generated_at;
  byId("accountCount").textContent = summary.account_count;
  byId("totalArr").textContent = money.format(summary.total_arr);
  byId("openPipeline").textContent = money.format(summary.open_pipeline_amount);
  byId("weightedPipeline").textContent = money.format(summary.weighted_pipeline_amount);
  byId("atRisk").textContent = summary.at_risk_account_count;
  byId("generatedAt").textContent = `Generated ${payload.generated_at}`;
  renderCompanyDashboard();
}

function renderAccounts() {
  const rows = state.accounts.map((account) => `
    <tr>
      <td><strong>${escapeHtml(account.name)}</strong><span>${escapeHtml(account.id)}</span></td>
      <td><span class="pill">${escapeHtml(label(account.stage))}</span></td>
      <td><span class="pill ${escapeHtml(account.health)}">${escapeHtml(label(account.health))}</span></td>
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
  byId("opportunityCount").textContent = `${openRows.length} open deals`;
  const rows = openRows.map((opportunity) => `
    <tr>
      <td>
        <strong>${escapeHtml(opportunity.id)}</strong>
        <span>${escapeHtml(opportunity.next_step)}</span>
      </td>
      <td>${escapeHtml(opportunity.account_name || opportunity.account_id)}</td>
      <td><span class="pill">${escapeHtml(label(opportunity.stage))}</span></td>
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
  const scope = state.recordModuleFilter ? `${moduleMeta(state.recordModuleFilter).name} items` : "items";
  byId("objectCount").textContent = `${state.objects.length} ${scope}`;
  const rows = state.objects.map((object) => `
    <button class="list-row ${selectedClass(state.selectedObject, object.path)}" type="button" data-object-path="${escapeHtml(object.path)}">
      <span>
        <strong>${escapeHtml(recordName(object.data || object))}</strong>
        <small>${escapeHtml(label(object.object_type))} / ${escapeHtml(object.id)}</small>
      </span>
      <em>${escapeHtml(moduleMeta(object.module).name || "")}</em>
    </button>
  `);
  byId("objectList").innerHTML = rows.join("") || `<p class="empty">No work items yet</p>`;
}

async function selectObject(path) {
  const payload = await fetchJson(`/object?path=${encodeURIComponent(path)}`);
  state.selectedObject = payload;
  state.activeModule = payload.object ? moduleForObjectType(payload.object.object_type) || state.activeModule : state.activeModule;
  byId("selectedObjectTitle").textContent = recordName(payload.object);
  byId("selectedObjectPath").textContent = payload.path;
  byId("objectEditor").value = pretty(payload.object);
  byId("requestId").value = requestId("ui");
  byId("recordFields").value = "";
  setRecordAction("read");
  byId("recordResultSummary").textContent = "Work item loaded";
  byId("recordOutput").textContent = pretty({
    path: payload.path,
    hash: payload.hash,
  });
  renderObjects();
  renderModules();
}

function renderProposals() {
  byId("proposalCount").textContent = `${state.proposals.length} requests`;
  const rows = state.proposals.map((item) => {
    const proposal = item.proposal;
    return `
      <button class="list-row ${selectedClass(state.selectedProposal, item.path)}" type="button" data-proposal-path="${escapeHtml(item.path)}">
        <span>
          <strong>${escapeHtml(`${label(proposal.action)} ${label(proposal.object_type)}`)}</strong>
          <small>${escapeHtml(proposal.object_id)} / ${escapeHtml(proposal.id)}</small>
        </span>
        <em class="status-pill ${escapeHtml(proposal.status)}">${escapeHtml(label(proposal.status))}</em>
      </button>
    `;
  });
  byId("proposalList").innerHTML = rows.join("") || `<p class="empty">No approval requests yet</p>`;
  if (!state.selectedProposal && state.proposals.length) {
    selectProposal(state.proposals[0].path);
  } else {
    renderSelectedProposal();
  }
  renderCompanyDashboard();
}

function selectProposal(path) {
  state.selectedProposal = state.proposals.find((item) => item.path === path) || null;
  renderProposals();
  renderSelectedProposal();
}

function renderSelectedProposal() {
  const selected = state.selectedProposal;
  if (!selected) {
    byId("selectedProposalTitle").textContent = "Approval Request";
    byId("selectedProposalPath").textContent = "No request selected";
    byId("proposalFacts").innerHTML = "";
    byId("proposalOutput").textContent = "{}";
    return;
  }

  const proposal = selected.proposal;
  byId("selectedProposalTitle").textContent = `${label(proposal.action)} ${label(proposal.object_type)}`;
  byId("selectedProposalPath").textContent = selected.path;
  byId("proposalFacts").innerHTML = [
    ["Status", label(proposal.status)],
    ["Action", label(proposal.action)],
    ["Work Item", `${proposal.object_type}/${proposal.object_id}`],
    ["Decision", label(proposal.policy_decision)],
    ["Remaining", selected.remaining_approvers.join(", ") || "none"],
  ].map(([name, value]) => `
    <span><strong>${escapeHtml(name)}</strong>${escapeHtml(value)}</span>
  `).join("");
  byId("proposalOutput").textContent = pretty(selected);
}

function renderPreviews() {
  byId("prPreviewCount").textContent = `${state.prPreviews.length} drafts`;
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
  }).join("") || `<p class="empty">No change drafts yet</p>`;

  byId("issuePreviewCount").textContent = `${state.issuePreviews.length} drafts`;
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
  }).join("") || `<p class="empty">No tracker drafts yet</p>`;
  renderCompanyDashboard();
}

function renderAuditEvents() {
  byId("auditCount").textContent = `${state.auditEvents.length} events`;
  byId("auditList").innerHTML = state.auditEvents.map((item) => {
    const event = item.event;
    return `
      <button class="list-row ${selectedClass(state.selectedAuditEvent, item.path)}" type="button" data-audit-path="${escapeHtml(item.path)}">
        <span>
          <strong>${escapeHtml(label(event.action))} ${escapeHtml(label(event.object_type))}/${escapeHtml(event.object_id)}</strong>
          <small>${escapeHtml(event.actor)} - ${escapeHtml(event.timestamp)}</small>
        </span>
        <em class="status-pill ${escapeHtml(event.result)}">${escapeHtml(label(event.result))}</em>
      </button>
    `;
  }).join("") || `<p class="empty">No activity yet</p>`;
  if (!state.selectedAuditEvent && state.auditEvents.length) {
    selectAuditEvent(state.auditEvents[0].path);
  }
  renderCompanyDashboard();
}

function selectAuditEvent(path) {
  state.selectedAuditEvent = state.auditEvents.find((item) => item.path === path) || null;
  byId("auditPath").textContent = state.selectedAuditEvent ? state.selectedAuditEvent.path : "No activity selected";
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
  await Promise.all([loadModules(), loadObjects(), loadDashboard(), loadAuditEvents()]);
  if (result.stored_object) {
    await selectObject(result.stored_object);
  }
}

async function createObject() {
  setRecordAction("create");
  await governedWrite();
}

async function updateObject() {
  setRecordAction("update");
  await governedWrite();
}

async function deleteObject() {
  if (!state.selectedObject || !state.selectedObject.path) {
    throw new Error("Select a saved work item before deleting");
  }
  const object = state.selectedObject.object;
  const confirmed = window.confirm(`Delete ${object.object_type}/${object.id}? This removes the saved work item and records activity evidence.`);
  if (!confirmed) {
    setStatus("Delete cancelled");
    return;
  }

  setRecordAction("delete");
  const result = await fetchJson("/objects/delete", {
    method: "POST",
    body: {
      path: state.selectedObject.path,
      request_id: requestValue(),
    },
  });
  state.selectedObject = null;
  byId("selectedObjectTitle").textContent = "Work Item";
  byId("selectedObjectPath").textContent = "No item selected";
  byId("objectEditor").value = "";
  byId("recordFields").value = "";
  showRecordResult(result.deleted ? "Work item deleted" : `Delete ${result.decision}`, result);
  await Promise.all([loadModules(), loadObjects(), loadDashboard(), loadAuditEvents()]);
  renderFlowState();
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
  showRecordResult("Approval request created", result);
  await loadProposals();
  state.selectedProposal = state.proposals.find((item) => item.path === result.path) || result;
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
  await Promise.all([loadModules(), loadProposals(), loadObjects(), loadDashboard(), loadAuditEvents()]);
  state.selectedProposal = state.proposals.find((item) => item.path === result.path) || result;
  renderSelectedProposal();
  setStatus(`Approval request ${action} complete`);
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
  renderFlowState();
  setStatus("Publication draft written");
}

async function validatePr() {
  const selected = requireProposal();
  const result = await fetchJson(`/proposals/${selected.proposal.id}/validate-pr`, {
    method: "POST",
    body: {},
  });
  byId("proposalOutput").textContent = result.report || pretty(result);
  setStatus(result.valid ? "Draft check passed" : "Draft check failed");
}

async function createIssuePreview() {
  const result = await fetchJson("/github/issues", {
    method: "POST",
    body: issuePayload(false),
  });
  byId("issueResultSummary").textContent = `Created draft #${result.issue.number}`;
  await loadPreviews();
  renderFlowState();
}

async function updateIssuePreview() {
  const issueNumber = Number(byId("issueNumber").value);
  if (!issueNumber) {
    throw new Error("Draft number is required");
  }
  const result = await fetchJson(`/github/issues/${issueNumber}`, {
    method: "POST",
    body: issuePayload(true),
  });
  byId("issueResultSummary").textContent = `Updated draft #${result.issue.number}`;
  await loadPreviews();
  renderFlowState();
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
    throw new Error(`Work item JSON is invalid: ${error.message}`);
  }
  if (!object || typeof object !== "object" || Array.isArray(object)) {
    throw new Error("Work item JSON must be an object");
  }
  return { object };
}

function useTemplate(templateId) {
  const template = TEMPLATE_DEFS[templateId];
  if (!template) {
    throw new Error(`Unknown template: ${templateId}`);
  }
  const object = withUniqueId(template.build());
  state.activeModule = template.module;
  state.recordModuleFilter = template.module;
  state.selectedObject = null;
  byId("objectTypeFilter").value = "";
  byId("selectedObjectTitle").textContent = recordName(object);
  byId("selectedObjectPath").textContent = "New work item";
  byId("objectEditor").value = pretty(object);
  setRecordAction("create");
  byId("recordFields").value = "";
  byId("requestId").value = requestId("ui");
  byId("recordResultSummary").textContent = `${template.label} template loaded`;
  byId("recordOutput").textContent = pretty({
    module: template.module,
    object_type: template.object_type,
    action: "create",
  });
  activateView("records");
  renderModules();
}

function newRecordForActiveModule() {
  const meta = moduleMeta(state.activeModule);
  const templateId = meta.templateIds[0];
  if (!templateId) {
    throw new Error("No starter template is available for this module");
  }
  useTemplate(templateId);
}

async function reloadSelectedObject() {
  if (!state.selectedObject || !state.selectedObject.path) {
    throw new Error("No saved work item is selected");
  }
  await selectObject(state.selectedObject.path);
  setStatus("Work item reloaded");
}

function openRecordsForModule(moduleId) {
  state.activeModule = moduleId;
  state.recordModuleFilter = moduleId;
  state.selectedObject = null;
  byId("objectTypeFilter").value = "";
  activateView("records");
  loadObjects().catch((error) => setStatus(error.message));
  renderModules();
}

function openModule(moduleId) {
  state.activeModule = moduleId;
  activateView(moduleMeta(moduleId).view);
  renderModules();
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

function setRecordAction(action) {
  byId("recordAction").value = action;
  const mode = byId("recordMode");
  mode.textContent = label(action);
  mode.className = `record-mode ${action}`;
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
    throw new Error("No approval request selected");
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
  document.querySelectorAll("[data-flow-view]").forEach((button) => {
    button.classList.toggle("active", button.dataset.flowView === name);
  });
}

function activeModule() {
  return moduleById(state.activeModule) || state.modules[0] || null;
}

function moduleById(moduleId) {
  return state.modules.find((module) => module.id === moduleId);
}

function moduleMeta(moduleId) {
  const safeId = String(moduleId || "");
  return MODULE_META[moduleId] || {
    name: safeId || "Workspace",
    glyph: (safeId || "wrk").slice(0, 3).toUpperCase(),
    view: "modules",
    color: "teal",
    description: "",
    signal: [],
    templateIds: [],
  };
}

function moduleForObjectType(objectType) {
  const match = state.modules.find((module) => module.object_types.includes(objectType));
  return match ? match.id : "";
}

function topTypeCounts(module) {
  return Object.entries(module.type_counts)
    .sort((left, right) => right[1] - left[1]);
}

function barHeight(count, total) {
  if (!total) {
    return 18;
  }
  return Math.max(18, Math.round((count / total) * 100));
}

function templateButtons(moduleId) {
  return moduleMeta(moduleId).templateIds.map((templateId) => {
    const template = TEMPLATE_DEFS[templateId];
    return `
      <button class="template-button" type="button" data-template="${escapeHtml(templateId)}">
        <span>${escapeHtml(template.label)}</span>
        <strong>${escapeHtml(template.object_type)}</strong>
      </button>
    `;
  }).join("");
}

function recordRow(record) {
  return `
    <button class="module-record" type="button" data-module-record-path="${escapeHtml(record.path)}">
      <span>
        <strong>${escapeHtml(recordName(record.data || record))}</strong>
        <small>${escapeHtml(label(record.object_type))} / ${escapeHtml(record.id)}</small>
      </span>
      <em>${escapeHtml((record.data && record.data.status) || record.status || "")}</em>
    </button>
  `;
}

function recordName(record) {
  const metadata = record.metadata || {};
  return record.name || metadata.title || metadata.display_name || metadata.name || record.id || "";
}

function baseObject(id, objectType, visibility = "company") {
  const timestamp = nowStamp();
  return {
    id,
    object_type: objectType,
    owner: "ssabbani",
    created_by: "ssabbani",
    updated_by: "ssabbani",
    created_at: timestamp,
    updated_at: timestamp,
    version: 1,
    status: "active",
    visibility,
    links: [],
    tags: [],
    metadata: {},
  };
}

function withUniqueId(object) {
  const suffix = new Date().toISOString().replace(/[-:.TZ]/g, "").slice(8, 14).toLowerCase();
  return {
    ...object,
    id: `${object.id}_${suffix}`,
  };
}

function nowStamp() {
  return new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
}

function flowView(labelText) {
  if (labelText === "Workbench") {
    return "records";
  }
  if (labelText === "Approvals") {
    return "proposals";
  }
  if (labelText === "Publishing") {
    return "github";
  }
  return "audit";
}

function emptyRow(columns, text) {
  return `<tr><td colspan="${columns}">${escapeHtml(text)}</td></tr>`;
}

function label(value) {
  return String(value || "").replaceAll("_", " ");
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
  button.addEventListener("click", () => {
    if (MODULE_META[button.dataset.view]) {
      state.activeModule = button.dataset.view;
      renderModules();
    }
    activateView(button.dataset.view);
  });
});

document.querySelectorAll("[data-skill]").forEach((button) => {
  button.addEventListener("click", () => setActiveSkill(button.dataset.skill));
});

document.addEventListener("click", (event) => {
  const moduleButton = event.target.closest("[data-module]");
  if (moduleButton) {
    state.activeModule = moduleButton.dataset.module;
    renderModules();
    return;
  }

  const openModuleButton = event.target.closest("[data-open-module]");
  if (openModuleButton) {
    openModule(openModuleButton.dataset.openModule);
    return;
  }

  const openRecordsButton = event.target.closest("[data-open-records]");
  if (openRecordsButton) {
    openRecordsForModule(openRecordsButton.dataset.openRecords);
    return;
  }

  const templateButton = event.target.closest("[data-template]");
  if (templateButton) {
    try {
      useTemplate(templateButton.dataset.template);
    } catch (error) {
      setStatus(error.message);
    }
    return;
  }

  const moduleRecord = event.target.closest("[data-module-record-path]");
  if (moduleRecord) {
    selectObject(moduleRecord.dataset.moduleRecordPath)
      .then(() => activateView("records"))
      .catch((error) => setStatus(error.message));
    return;
  }

  const proposalButton = event.target.closest("[data-proposal-path]");
  if (proposalButton) {
    selectProposal(proposalButton.dataset.proposalPath);
    activateView("proposals");
    return;
  }

  const auditButton = event.target.closest("[data-audit-path]");
  if (auditButton) {
    selectAuditEvent(auditButton.dataset.auditPath);
    activateView("audit");
    return;
  }

  const flowButton = event.target.closest("[data-flow-view]");
  if (flowButton) {
    activateView(flowButton.dataset.flowView);
  }
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

byId("recordAction").addEventListener("change", () => {
  setRecordAction(byId("recordAction").value);
});

byId("identitySelect").addEventListener("change", () => {
  loadWorkspace().catch((error) => setStatus(error.message));
});

byId("objectTypeFilter").addEventListener("change", () => {
  state.recordModuleFilter = "";
  state.selectedObject = null;
  loadObjects().catch((error) => setStatus(error.message));
});

bindAsync("refreshButton", loadWorkspace);
bindAsync("newRecordButton", newRecordForActiveModule);
bindAsync("reloadObjectButton", reloadSelectedObject);
bindAsync("validateObjectButton", validateObject);
bindAsync("policyCheckButton", policyCheck);
bindAsync("createObjectButton", createObject);
bindAsync("updateObjectButton", updateObject);
bindAsync("createProposalButton", createProposal);
bindAsync("deleteObjectButton", deleteObject);
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
