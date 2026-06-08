const PERSONAS = {
  owner: {
    label: "Owner",
    roles: ["founder"],
    views: ["onboarding", "modules", "crm", "issues", "hr", "records", "proposals", "github", "audit", "users"],
    modules: ["crm", "issues", "hr"],
    templates: ["crm_account", "crm_opportunity", "issue_defect", "issue_incident", "issue_release", "hr_job", "hr_candidate", "hr_employee", "hr_time_off"],
    landingView: "onboarding",
    summary: "Full Company OS access",
  },
  company_os_admin: {
    label: "Company OS Admin",
    roles: ["company_os_admin"],
    views: ["onboarding", "modules", "crm", "issues", "hr", "records", "proposals", "github", "audit", "users"],
    modules: ["crm", "issues", "hr"],
    templates: ["crm_account", "crm_opportunity", "issue_defect", "issue_incident", "issue_release", "hr_job", "hr_candidate", "hr_employee", "hr_time_off"],
    landingView: "onboarding",
    summary: "System operations, approvals, publishing, and evidence",
  },
  customer_lead: {
    label: "Customer Lead",
    roles: ["customer_lead", "sales_manager"],
    views: ["onboarding", "crm", "records", "proposals", "audit"],
    modules: ["crm"],
    templates: ["crm_account", "crm_opportunity"],
    landingView: "onboarding",
    summary: "Customer pipeline, renewals, approvals, and CRM work items",
  },
  customer_operator: {
    label: "Customer Operator",
    roles: ["customer_operator", "sales_rep"],
    views: ["onboarding", "crm", "records", "proposals", "audit"],
    modules: ["crm"],
    templates: ["crm_opportunity"],
    landingView: "onboarding",
    summary: "Customer accounts, open deals, and CRM work changes",
  },
  engineering_lead: {
    label: "Engineering Lead",
    roles: ["engineering_lead"],
    views: ["onboarding", "issues", "records", "proposals", "audit"],
    modules: ["issues"],
    templates: ["issue_defect", "issue_incident", "issue_release"],
    landingView: "onboarding",
    summary: "Delivery work, incidents, releases, and evidence",
  },
  support_engineer: {
    label: "Support Engineer",
    roles: ["support_engineer"],
    views: ["onboarding", "issues", "records", "proposals", "audit"],
    modules: ["issues"],
    templates: ["issue_defect", "issue_incident"],
    landingView: "onboarding",
    summary: "Defects, incidents, RCAs, and support evidence",
  },
  people_ops: {
    label: "People Ops",
    roles: ["people_ops"],
    views: ["onboarding", "hr", "records", "proposals", "audit"],
    modules: ["hr"],
    templates: ["hr_job", "hr_candidate", "hr_employee", "hr_time_off"],
    landingView: "onboarding",
    summary: "Hiring, onboarding, employee changes, and people requests",
  },
  hiring_manager: {
    label: "Hiring Manager",
    roles: ["hiring_manager"],
    views: ["onboarding", "hr", "records", "proposals", "audit"],
    modules: ["hr"],
    templates: ["hr_job", "hr_candidate"],
    landingView: "onboarding",
    summary: "Open roles, candidates, interviews, and onboarding requests",
  },
};

const ROLE_LABELS = {
  founder: "Owner",
  company_os_admin: "Company OS Admin",
  customer_lead: "Customer Lead",
  customer_operator: "Customer Operator",
  engineering_lead: "Engineering Lead",
  support_engineer: "Support Engineer",
  people_ops: "People Ops",
  hiring_manager: "Hiring Manager",
  sales_manager: "Customer Lead",
  sales_rep: "Customer Operator",
};

const ONBOARDING_GUIDES = {
  owner: {
    mission: "You own the operating system: users, modules, approvals, publishing, and audit evidence.",
    workflow: ["Sign in", "Review Company OS", "Assign users", "Unblock work", "Publish evidence"],
    firstSteps: [
      "Sign in with UID owner and passcode demo.",
      "Open Users and confirm every test user has a clear persona.",
      "Open Home and review Needs Attention, Approvals, and Recent Activity.",
      "Open each module once: Customers, Delivery, and People.",
      "Create one safe test work item from Workbench and confirm the result appears in Activity.",
    ],
    dailyFlow: [
      "Start in Home and scan risk, approvals, and recent evidence.",
      "Open Users when a new operator needs access or a persona must change.",
      "Open Approvals when a request is waiting for an owner-level decision.",
      "Open Publishing when a reviewed proposal should become a draft pull request or tracker item.",
      "End in Activity and confirm important work left an evidence trail.",
    ],
    boundaries: [
      "Do not use shared demo users for real company data.",
      "Give users the narrowest persona that lets them do their job.",
      "Treat People data as sensitive even in the local preview.",
    ],
    success: [
      "You can explain who can access each module.",
      "You can add a user and choose the right persona.",
      "You can find the audit record for a completed change.",
    ],
  },
  company_os_admin: {
    mission: "You keep the workspace clean: user setup, operating evidence, approvals, and local system checks.",
    workflow: ["Sign in", "Check users", "Inspect modules", "Run workflow", "Verify evidence"],
    firstSteps: [
      "Sign in with UID admin and passcode demo.",
      "Open Users and confirm the owner plus module operators are present.",
      "Open Home and look for incomplete approvals or empty activity.",
      "Open Workbench and load an existing work item without changing it.",
      "Open Activity and confirm the workspace history is readable.",
    ],
    dailyFlow: [
      "Refresh the workspace before reviewing work.",
      "Check Users before adding, removing, or changing access.",
      "Use Workbench for controlled create, update, validate, policy check, and delete actions.",
      "Use Approvals to move proposed work through approve, reject, and apply states.",
      "Use Activity to confirm actions are recorded.",
    ],
    boundaries: [
      "Do not grant Owner unless the person truly owns system-level decisions.",
      "Do not bypass Workbench for governed business changes.",
      "Do not publish drafts before checking proposal status.",
    ],
    success: [
      "Every user has a named persona.",
      "Every important work item has a validation or policy result.",
      "Publishing and Activity views agree with the latest workflow state.",
    ],
  },
  customer_lead: {
    mission: "You manage customer health, pipeline movement, renewal risk, and customer approvals.",
    workflow: ["Sign in", "Review customers", "Prioritize deals", "Approve changes", "Confirm activity"],
    firstSteps: [
      "Sign in with UID customer_lead and passcode demo.",
      "Open Customers and read the customer table from left to right.",
      "Check Booked ARR, Open pipeline, Weighted pipeline, and Needs follow-up.",
      "Open Workbench and choose Account or Opportunity only.",
      "Open Approvals and check whether customer work is waiting for your decision.",
    ],
    dailyFlow: [
      "Start in Customers and look for yellow or red health.",
      "Open the opportunity list and read the next step on each open deal.",
      "Use Workbench when account or opportunity data must change.",
      "Use Approvals when a customer change requires a decision.",
      "Use Activity to confirm customer work was recorded.",
    ],
    boundaries: [
      "Stay in Customers, Workbench, Approvals, and Activity.",
      "Do not create Delivery or People records.",
      "Do not approve work you do not understand from the customer context.",
    ],
    success: [
      "You know which customer needs follow-up.",
      "You know the next step for the highest value open opportunity.",
      "You can approve or reject a customer request with a reason.",
    ],
  },
  customer_operator: {
    mission: "You keep customer records and opportunities current without changing system settings.",
    workflow: ["Sign in", "Review accounts", "Capture deal work", "Run checks", "Confirm activity"],
    firstSteps: [
      "Sign in with UID customer_operator and passcode demo.",
      "Open Customers and find Acme Corp.",
      "Open Workbench and choose Opportunity.",
      "Review the generated fields before creating or updating anything.",
      "Run Validate or Policy Check before creating a proposal.",
    ],
    dailyFlow: [
      "Start in Customers and identify the account or deal to update.",
      "Use Workbench to capture the change.",
      "Use Validate to catch missing or malformed fields.",
      "Use Policy Check to see whether the change can be committed or needs approval.",
      "Use Activity to confirm completed work.",
    ],
    boundaries: [
      "Do not use Users, Delivery, People, or Publishing.",
      "Do not change owner/admin records.",
      "Use proposals when policy says approval is required.",
    ],
    success: [
      "You can create a customer opportunity proposal.",
      "You can explain the policy result.",
      "You can find your customer work in Activity.",
    ],
  },
  engineering_lead: {
    mission: "You manage delivery work, incidents, releases, and engineering approvals.",
    workflow: ["Sign in", "Review delivery", "Capture work", "Decide readiness", "Verify evidence"],
    firstSteps: [
      "Sign in with UID engineering_lead and passcode demo.",
      "Open Delivery and review defects, incidents, releases, and RCAs.",
      "Open Workbench and choose Defect, Incident, or Release.",
      "Create a safe delivery work item and inspect the policy decision.",
      "Open Activity and confirm the delivery event is visible.",
    ],
    dailyFlow: [
      "Start in Delivery and sort urgent work from routine work.",
      "Capture new incidents or defects in Workbench.",
      "Update releases only when readiness is clear.",
      "Use Approvals for delivery changes that need a decision.",
      "Check Activity before ending a review.",
    ],
    boundaries: [
      "Do not manage Users unless you are also Owner or Company OS Admin.",
      "Do not create People or Customer records from this persona.",
      "Keep incident notes factual and action-oriented.",
    ],
    success: [
      "Open delivery work is visible and current.",
      "Release readiness is captured in a governed record.",
      "Incident or defect changes leave audit evidence.",
    ],
  },
  support_engineer: {
    mission: "You capture support defects, incidents, and RCA evidence so delivery work is traceable.",
    workflow: ["Sign in", "Triage issue", "Capture evidence", "Check policy", "Close loop"],
    firstSteps: [
      "Sign in with UID support_engineer and passcode demo.",
      "Open Delivery and read the current work list.",
      "Open Workbench and choose Defect or Incident.",
      "Fill in severity, state, owner team, and next step.",
      "Run Validate before creating the work item.",
    ],
    dailyFlow: [
      "Start in Delivery and identify what needs triage.",
      "Use Workbench to record a defect or incident.",
      "Keep next step short and specific.",
      "Use Approvals only when policy requires a decision.",
      "Use Activity to verify the support event exists.",
    ],
    boundaries: [
      "Do not create releases unless your persona changes.",
      "Do not work in Customers or People.",
      "Do not put secrets or customer-sensitive details into demo data.",
    ],
    success: [
      "A support issue has severity, state, owner team, and next step.",
      "The issue validates cleanly.",
      "The event is visible in Activity.",
    ],
  },
  people_ops: {
    mission: "You operate hiring, onboarding, employee changes, policy acknowledgments, and time off.",
    workflow: ["Sign in", "Review people work", "Capture request", "Check policy", "Confirm activity"],
    firstSteps: [
      "Sign in with UID people_ops and passcode demo.",
      "Open People and review jobs, candidates, employees, onboarding, and time off.",
      "Open Workbench and choose Job, Candidate, Employee, or Time Off.",
      "Review visibility before saving any People work item.",
      "Open Activity and confirm People work is recorded.",
    ],
    dailyFlow: [
      "Start in People and identify the next hiring or employee action.",
      "Use Workbench to capture the request.",
      "Validate the record before asking for approval.",
      "Use Approvals for changes that need a People decision.",
      "Confirm the event in Activity.",
    ],
    boundaries: [
      "Treat People records as sensitive.",
      "Do not create Customer or Delivery records.",
      "Do not add users unless you have Owner or Company OS Admin access.",
    ],
    success: [
      "People work is captured with the right state and next step.",
      "Sensitive records use the right visibility.",
      "You can trace the request in Activity.",
    ],
  },
  hiring_manager: {
    mission: "You manage open roles, candidates, interviews, offers, and onboarding requests.",
    workflow: ["Sign in", "Review hiring", "Capture candidate", "Request decision", "Track evidence"],
    firstSteps: [
      "Sign in with UID hiring_manager and passcode demo.",
      "Open People and focus on jobs, candidates, interviews, offers, and onboarding.",
      "Open Workbench and choose Job or Candidate.",
      "Fill in stage, source, and next step before saving.",
      "Use Activity to confirm hiring work is recorded.",
    ],
    dailyFlow: [
      "Start in People and identify the role or candidate to move.",
      "Use Workbench to record the next hiring step.",
      "Keep candidate next steps specific.",
      "Use Approvals when an offer or onboarding request needs a decision.",
      "Review Activity to confirm the hiring record changed.",
    ],
    boundaries: [
      "Do not manage system users.",
      "Do not change customer or delivery records.",
      "Do not put real candidate personal data in demo records.",
    ],
    success: [
      "A hiring item has a clear stage and next step.",
      "The hiring item validates cleanly.",
      "The hiring action is visible in Activity.",
    ],
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
        hiring_manager: currentIdentity().username,
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
        manager: currentIdentity().username,
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

const CORE_FIELDS = new Set([
  "id",
  "object_type",
  "owner",
  "created_by",
  "updated_by",
  "created_at",
  "updated_at",
  "version",
  "status",
  "visibility",
  "links",
  "tags",
  "metadata",
]);

const FIELD_LABELS = {
  id: "Work item ID",
  object_type: "Type",
  owner: "Owner",
  status: "Status",
  visibility: "Visibility",
  version: "Version",
  tags: "Tags",
  name: "Name",
  stage: "Stage",
  industry: "Industry",
  arr: "ARR",
  renewal_date: "Renewal date",
  account_id: "Customer account",
  amount: "Amount",
  probability: "Probability",
  close_date: "Close date",
  discount_requested: "Discount requested",
  next_step: "Next step",
  approval_status: "Approval status",
  "metadata.title": "Title",
  "metadata.display_name": "Name",
  "metadata.name": "Name",
  "metadata.state": "State",
  "metadata.stage": "Stage",
  "metadata.severity": "Severity",
  "metadata.priority": "Priority",
  "metadata.owner_team": "Owner team",
  "metadata.next_step": "Next step",
  "metadata.started_at": "Started at",
  "metadata.target_date": "Target date",
  "metadata.readiness": "Readiness",
  "metadata.outcome": "Outcome",
  "metadata.source": "Source",
  "metadata.approver": "Approver",
  "metadata.start_window": "Start window",
  "metadata.starts_on": "Starts on",
  "metadata.ends_on": "Ends on",
  "metadata.hiring_manager": "Hiring manager",
  "metadata.focus": "Focus",
  "metadata.notes": "Notes",
  "metadata.role": "Role",
  "metadata.start_date": "Start date",
  "metadata.manager": "Manager",
};

const TYPE_FIELD_PATHS = {
  account: ["name", "stage", "industry", "arr", "health", "renewal_date", "status", "visibility", "tags"],
  opportunity: ["account_id", "stage", "amount", "probability", "close_date", "discount_requested", "next_step", "approval_status", "status", "visibility", "tags"],
  component: ["metadata.name", "metadata.owner_team", "metadata.state", "status", "visibility", "tags"],
  defect: ["metadata.title", "metadata.severity", "metadata.state", "metadata.owner_team", "metadata.next_step", "status", "visibility", "tags"],
  feature_request: ["metadata.title", "metadata.priority", "metadata.state", "metadata.outcome", "status", "visibility", "tags"],
  incident: ["metadata.title", "metadata.severity", "metadata.state", "metadata.started_at", "metadata.next_step", "status", "visibility", "tags"],
  rca: ["metadata.title", "metadata.state", "metadata.outcome", "metadata.next_step", "status", "visibility", "tags"],
  release: ["metadata.name", "metadata.state", "metadata.target_date", "metadata.readiness", "status", "visibility", "tags"],
  candidate: ["metadata.display_name", "metadata.stage", "metadata.source", "metadata.next_step", "status", "visibility", "tags"],
  employee: ["metadata.display_name", "metadata.role", "metadata.start_date", "metadata.manager", "status", "visibility", "tags"],
  interview: ["metadata.display_name", "metadata.stage", "metadata.next_step", "status", "visibility", "tags"],
  job: ["metadata.title", "metadata.state", "metadata.hiring_manager", "metadata.focus", "status", "visibility", "tags"],
  offer: ["metadata.state", "metadata.approver", "metadata.start_window", "metadata.notes", "status", "visibility", "tags"],
  onboarding: ["metadata.display_name", "metadata.state", "metadata.next_step", "status", "visibility", "tags"],
  policy_ack: ["metadata.display_name", "metadata.state", "metadata.next_step", "status", "visibility", "tags"],
  time_off: ["metadata.state", "metadata.starts_on", "metadata.ends_on", "metadata.approver", "status", "visibility", "tags"],
};

const SELECT_OPTIONS = {
  status: ["active", "draft", "inactive"],
  visibility: ["company", "hr_private"],
  health: ["green", "yellow", "red"],
  stage: ["qualified", "active_customer", "discovery", "proposal", "technical_interview", "screen", "open"],
  approval_status: ["not_required", "pending_finance", "approved"],
  "metadata.state": ["triage", "ready", "monitoring", "investigating", "candidate", "draft", "requested", "open", "active", "complete"],
  "metadata.stage": ["screen", "technical_interview", "panel", "offer", "hired"],
  "metadata.severity": ["low", "medium", "high", "critical"],
  "metadata.priority": ["low", "medium", "high"],
};

const NUMBER_FIELDS = new Set(["arr", "amount", "probability", "discount_requested", "version"]);
const DATE_FIELDS = new Set(["renewal_date", "close_date", "metadata.target_date", "metadata.start_window", "metadata.starts_on", "metadata.ends_on", "metadata.start_date"]);
const LONG_TEXT_FIELDS = new Set(["next_step", "metadata.next_step", "metadata.readiness", "metadata.outcome", "metadata.focus", "metadata.notes"]);
const SESSION_KEY = "opraSessionId";

const state = {
  sessionId: localStorage.getItem(SESSION_KEY) || "",
  currentUser: null,
  users: [],
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

function currentPersona() {
  const persona = state.currentUser ? state.currentUser.persona : "owner";
  return PERSONAS[persona] || PERSONAS.owner;
}

function currentIdentity() {
  const persona = currentPersona();
  if (!state.currentUser) {
    return {
      username: "anonymous",
      roles: [],
    };
  }
  return {
    username: state.currentUser.uid,
    roles: state.currentUser.roles || persona.roles,
  };
}

function authHeaders() {
  const identity = currentIdentity();
  const headers = {
    "X-Opra-User": identity.username,
    "X-Opra-Roles": identity.roles.join(","),
  };
  if (state.sessionId) {
    headers["X-Opra-Session"] = state.sessionId;
  }
  return headers;
}

function applyPersonaShell() {
  if (!state.currentUser) {
    byId("sessionActions").hidden = true;
    document.querySelector(".tabbar").hidden = true;
    byId("personaStrip").hidden = true;
    activateView("auth");
    return;
  }
  const persona = currentPersona();
  ensurePersonaScope();
  byId("sessionActions").hidden = false;
  document.querySelector(".tabbar").hidden = false;
  byId("personaStrip").hidden = false;
  byId("sessionUser").innerHTML = `
    <strong>${escapeHtml(state.currentUser.display_name || state.currentUser.uid)}</strong>
    <span>${escapeHtml(persona.label)}</span>
  `;
  byId("personaStrip").innerHTML = `
    <span>${escapeHtml(persona.label)}</span>
    <strong>${escapeHtml(persona.summary)}</strong>
  `;
  renderOnboarding();
  document.querySelectorAll("[data-view]").forEach((button) => {
    button.hidden = !persona.views.includes(button.dataset.view);
  });
  if (!persona.views.includes(activeViewName())) {
    activateView(persona.landingView);
  }
}

function ensurePersonaScope() {
  const persona = currentPersona();
  if (!persona.modules.includes(state.activeModule)) {
    state.activeModule = persona.modules[0] || "crm";
  }
  if (state.recordModuleFilter && !persona.modules.includes(state.recordModuleFilter)) {
    state.recordModuleFilter = persona.modules.length === 1 ? persona.modules[0] : "";
  }
  if (!state.recordModuleFilter && persona.modules.length === 1) {
    state.recordModuleFilter = persona.modules[0];
  }
}

function activeViewName() {
  const active = document.querySelector(".view.active");
  return active ? active.id.replace(/View$/, "") : "modules";
}

function visibleModules() {
  const allowed = currentPersona().modules;
  return state.modules.filter((module) => allowed.includes(module.id));
}

function visibleModuleIds() {
  return currentPersona().modules;
}

function visibleTemplateIds(moduleId) {
  const personaTemplates = currentPersona().templates;
  return moduleMeta(moduleId).templateIds.filter((templateId) => personaTemplates.includes(templateId));
}

function personaAllowsModule(moduleId) {
  return visibleModuleIds().includes(moduleId);
}

function personaAllowsTemplate(templateId) {
  return currentPersona().templates.includes(templateId);
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
  applyPersonaShell();
  if (!state.currentUser) {
    setStatus("Sign-in required");
    return;
  }
  setStatus("Loading workspace");
  const results = await Promise.allSettled([
    loadModules(),
    personaAllowsModule("crm") ? loadDashboard() : resetCustomerState(),
    loadObjects(),
    loadProposals(),
    currentPersona().views.includes("github") ? loadPreviews() : resetPreviews(),
    loadAuditEvents(),
    currentPersona().views.includes("users") ? loadUsers() : resetUsers(),
  ]);
  const rejected = results.find((result) => result.status === "rejected");
  if (rejected) {
    setStatus(rejected.reason.message);
    return;
  }
  applyPersonaShell();
  renderFlowState();
  setStatus("Workspace loaded");
}

async function resetCustomerState() {
  state.accounts = [];
  state.opportunities = [];
  state.crmSummary = null;
  state.dashboardGeneratedAt = "";
  state.skills = {};
}

async function resetUsers() {
  state.users = [];
  renderUsers();
}

async function resetPreviews() {
  state.prPreviews = [];
  state.issuePreviews = [];
  renderPreviews();
}

async function restoreSession() {
  applyPersonaShell();
  if (!state.sessionId) {
    setStatus("Sign-in required");
    return;
  }
  try {
    const payload = await fetchJson("/auth/me");
    state.currentUser = payload.user;
    await loadWorkspace();
  } catch (error) {
    clearSession();
    applyPersonaShell();
    setStatus(error.message);
  }
}

async function loginUser() {
  const payload = await fetchJson("/auth/login", {
    method: "POST",
    body: {
      uid: byId("loginUid").value.trim(),
      passcode: byId("loginPasscode").value,
    },
  });
  state.sessionId = payload.session_id;
  state.currentUser = payload.user;
  localStorage.setItem(SESSION_KEY, state.sessionId);
  byId("loginPasscode").value = "";
  await loadWorkspace();
}

async function registerUser() {
  const payload = await fetchJson("/auth/register", {
    method: "POST",
    body: {
      uid: byId("registerUid").value.trim(),
      passcode: byId("registerPasscode").value,
      display_name: byId("registerDisplayName").value.trim(),
      email: byId("registerEmail").value.trim(),
      persona: byId("registerPersona").value,
    },
  });
  byId("registerSummary").textContent = `${payload.user.uid} registered`;
  byId("loginUid").value = payload.user.uid;
  byId("registerPasscode").value = "";
  setStatus("User registered");
}

async function logoutUser() {
  if (state.sessionId) {
    await fetchJson("/auth/logout", { method: "POST", body: {} }).catch(() => ({}));
  }
  clearSession();
  applyPersonaShell();
  setStatus("Signed out");
}

function clearSession() {
  state.sessionId = "";
  state.currentUser = null;
  state.users = [];
  state.selectedObject = null;
  state.selectedProposal = null;
  state.selectedAuditEvent = null;
  state.recordModuleFilter = "";
  localStorage.removeItem(SESSION_KEY);
}

async function loadUsers() {
  const payload = await fetchJson("/users");
  state.users = payload.users || [];
  renderUsers();
}

function renderOnboarding() {
  if (!state.currentUser) {
    return;
  }
  const persona = currentPersona();
  const guide = ONBOARDING_GUIDES[state.currentUser.persona] || ONBOARDING_GUIDES.owner;
  byId("onboardingTitle").textContent = `${persona.label} Onboarding`;
  byId("onboardingSummary").textContent = persona.summary;
  byId("onboardingMission").textContent = guide.mission;
  byId("dailyFlowSummary").textContent = `${persona.label} operating rhythm`;
  byId("boundarySummary").textContent = `${persona.label} access boundaries`;
  byId("successSummary").textContent = "You are ready when these are true";
  byId("personaWorkflow").innerHTML = renderWorkflowMap(guide.workflow);
  byId("firstStepsList").innerHTML = guide.firstSteps.map(instructionRow).join("");
  byId("dailyFlowList").innerHTML = guide.dailyFlow.map(instructionRow).join("");
  byId("boundaryList").innerHTML = guide.boundaries.map(instructionRow).join("");
  byId("successList").innerHTML = guide.success.map(instructionRow).join("");
}

function renderWorkflowMap(steps) {
  return steps.map((step, index) => `
    <span class="journey-node ${escapeHtml(workflowTone(index))}">
      <strong>${escapeHtml(step)}</strong>
      <small>${String(index + 1).padStart(2, "0")}</small>
    </span>
    ${index < steps.length - 1 ? `<span class="journey-link"></span>` : ""}
  `).join("");
}

function workflowTone(index) {
  return ["identity", "scope", "work", "decision", "evidence"][index] || "work";
}

function instructionRow(text) {
  return `<li>${escapeHtml(text)}</li>`;
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
  ensurePersonaScope();
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
  ensurePersonaScope();
  const modules = visibleModules();
  const totalRecords = modules.reduce((total, module) => total + module.record_count, 0);
  const approvalCount = openApprovalRequests().length;
  byId("moduleCommandSummary").textContent =
    `${modules.length} operating areas, ${totalRecords} work items, ${approvalCount} approvals waiting`;

  byId("moduleTiles").innerHTML = modules.map((module) => {
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
  if (personaAllowsModule("issues")) {
    renderOperationalModule("issues");
  }
  if (personaAllowsModule("hr")) {
    renderOperationalModule("hr");
  }
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
  byId("issuesTemplates").innerHTML = personaAllowsModule("issues") ? templateButtons("issues") : "";
  byId("hrTemplates").innerHTML = personaAllowsModule("hr") ? templateButtons("hr") : "";
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

  const totalRecords = visibleModules().reduce((total, module) => total + module.record_count, 0);
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
  const views = currentPersona().views;
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
  ].filter((item) => views.includes(item.view));
}

function attentionItems() {
  return [
    ...(personaAllowsModule("crm") ? atRiskAccounts().map((account) => ({
      tone: account.health === "red" ? "red" : "amber",
      category: "Customer follow-up",
      title: account.name || account.id,
      detail: `${label(account.health)} health / renewal ${account.renewal_date}`,
      view: "crm",
    })) : []),
    ...(personaAllowsModule("crm") ? openPipelineItems().slice(0, 2) : []),
    ...(personaAllowsModule("issues") ? activeDeliveryItems().slice(0, 3) : []),
    ...(personaAllowsModule("hr") ? activePeopleItems().slice(0, 3) : []),
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
    const moduleId = moduleForObjectType(proposal.object_type);
    if (moduleId && !personaAllowsModule(moduleId)) {
      return false;
    }
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

function renderRecordForm(object) {
  const form = byId("recordForm");
  if (!object) {
    form.innerHTML = emptyReport("No work item selected", "Waiting for work item details.");
    return;
  }

  const isSaved = Boolean(state.selectedObject && state.selectedObject.path);
  const fields = editableFields(object, isSaved);
  const facts = [
    ["Type", label(object.object_type)],
    ["ID", object.id],
    ["Owner", object.owner],
    ["Version", object.version],
    ["Updated", object.updated_at],
  ];
  form.innerHTML = `
    <div class="record-report-top">
      ${facts.map(([name, value]) => factTile(name, value)).join("")}
    </div>
    <div class="record-edit-grid">
      ${fields.map(renderRecordField).join("")}
    </div>
  `;
}

function editableFields(object, isSaved) {
  const paths = [];
  const add = (path) => {
    if (!paths.includes(path)) {
      paths.push(path);
    }
  };

  add("id");
  add("object_type");
  add("owner");
  (TYPE_FIELD_PATHS[object.object_type] || []).forEach(add);

  Object.keys(object).forEach((key) => {
    if (!CORE_FIELDS.has(key)) {
      add(key);
    }
  });
  Object.keys(object.metadata || {}).forEach((key) => add(`metadata.${key}`));

  return paths.map((path) => ({
    path,
    label: fieldLabel(path),
    value: fieldValue(object, path),
    readonly: (path === "id" && isSaved) || path === "object_type",
  }));
}

function renderRecordField(field) {
  const value = field.path === "tags"
    ? (Array.isArray(field.value) ? field.value.join(", ") : "")
    : field.value ?? "";
  const disabled = field.readonly ? " disabled" : "";
  const common = `data-field-path="${escapeHtml(field.path)}"${disabled}`;
  if (SELECT_OPTIONS[field.path]) {
    const options = selectOptions(field.path, value);
    return `
      <label class="field record-field">
        <span>${escapeHtml(field.label)}</span>
        <select ${common}>${options}</select>
      </label>
    `;
  }
  if (LONG_TEXT_FIELDS.has(field.path)) {
    return `
      <label class="field record-field span-2">
        <span>${escapeHtml(field.label)}</span>
        <textarea ${common}>${escapeHtml(value)}</textarea>
      </label>
    `;
  }
  const type = NUMBER_FIELDS.has(field.path) ? "number" : DATE_FIELDS.has(field.path) ? "date" : "text";
  const step = field.path === "probability" ? ` step="0.01" min="0" max="1"` : "";
  return `
    <label class="field record-field">
      <span>${escapeHtml(field.label)}</span>
      <input type="${type}"${step} value="${escapeHtml(value)}" ${common}>
    </label>
  `;
}

function selectOptions(path, currentValue) {
  const values = [...SELECT_OPTIONS[path]];
  if (currentValue && !values.includes(String(currentValue))) {
    values.unshift(String(currentValue));
  }
  return values.map((value) => `
    <option value="${escapeHtml(value)}" ${String(currentValue) === value ? "selected" : ""}>${escapeHtml(label(value))}</option>
  `).join("");
}

function updateObjectFromField(control) {
  const path = control.dataset.fieldPath;
  if (!path || control.disabled) {
    return;
  }
  const object = editorObject();
  if (!object) {
    return;
  }
  setFieldValue(object, path, parseFieldValue(path, control.value));
  byId("objectEditor").value = pretty(object);
  byId("selectedObjectTitle").textContent = recordName(object);
  byId("recordFields").value = changedFields(
    state.selectedObject ? state.selectedObject.object : null,
    object,
  ).join(",");
}

function editorObject() {
  try {
    const object = JSON.parse(byId("objectEditor").value || "{}");
    return object && typeof object === "object" && !Array.isArray(object) ? object : null;
  } catch {
    return null;
  }
}

function fieldValue(object, path) {
  return path.split(".").reduce((value, part) => {
    if (value && typeof value === "object") {
      return value[part];
    }
    return undefined;
  }, object);
}

function setFieldValue(object, path, value) {
  const parts = path.split(".");
  let target = object;
  parts.slice(0, -1).forEach((part) => {
    if (!target[part] || typeof target[part] !== "object" || Array.isArray(target[part])) {
      target[part] = {};
    }
    target = target[part];
  });
  target[parts[parts.length - 1]] = value;
}

function parseFieldValue(path, rawValue) {
  if (path === "tags") {
    return csvValues(rawValue);
  }
  if (NUMBER_FIELDS.has(path)) {
    const numeric = Number(rawValue);
    return Number.isFinite(numeric) ? numeric : 0;
  }
  return rawValue;
}

function fieldLabel(path) {
  return FIELD_LABELS[path] || label(path.split(".").pop());
}

function renderRecordResultReport(summary, payload) {
  if (!payload || !Object.keys(payload).length) {
    return emptyReport("No result yet", "No checks or changes have run.");
  }
  const facts = [
    ["Outcome", summary],
    ["Decision", payload.decision],
    ["Valid", payload.valid === undefined ? payload.validation?.valid : payload.valid],
    ["Work item", payload.object_type && payload.object_id ? `${payload.object_type}/${payload.object_id}` : ""],
    ["Stored at", payload.stored_object || payload.path],
    ["Activity", payload.audit_event],
  ].filter(([, value]) => value !== undefined && value !== "");
  const issues = payload.issues || payload.validation?.issues || [];
  const reasons = payload.reasons || [];
  return `
    <div class="report-body">
      <div class="report-facts">${facts.map(([name, value]) => factTile(name, displayValue(value))).join("")}</div>
      ${issues.length ? reportSection("Issues", issues.map((item) => displayValue(item))) : ""}
      ${reasons.length ? reportSection("Reasons", reasons.map((item) => displayValue(item))) : ""}
    </div>
  `;
}

function renderProposalReport(selected) {
  if (!selected) {
    return emptyReport("No approval request selected", "Approval queue idle.");
  }
  const proposal = selected.proposal;
  const before = proposal.before || null;
  const after = proposal.after || {};
  const changes = changeRows(before, after);
  const facts = [
    ["Requested by", proposal.created_by],
    ["Created", proposal.created_at],
    ["Target", proposal.target_path],
    ["Required approvers", displayApprovers(proposal.required_approvers || [])],
    ["Remaining", displayApprovers(selected.remaining_approvers)],
  ];
  return `
    <div class="report-body">
      <section class="report-section">
        <h3>Decision Summary</h3>
        <p>${escapeHtml(label(proposal.action))} ${escapeHtml(label(proposal.object_type))} ${escapeHtml(proposal.object_id)} is ${escapeHtml(label(proposal.status))} with policy decision ${escapeHtml(label(proposal.policy_decision))}.</p>
      </section>
      <div class="report-facts">${facts.map(([name, value]) => factTile(name, value)).join("")}</div>
      ${renderChangeReport(before, changes)}
      ${proposal.reasons?.length ? reportSection("Policy Reasons", proposal.reasons) : ""}
    </div>
  `;
}

function renderChangeReport(before, changes) {
  if (!changes.length) {
    return reportSection("Changes", [before ? "No field-level changes detected." : "New work item will be created."]);
  }
  const rows = changes.slice(0, 18).map((item) => `
    <tr>
      <th>${escapeHtml(fieldLabel(item.path))}</th>
      <td>${escapeHtml(displayValue(item.before))}</td>
      <td>${escapeHtml(displayValue(item.after))}</td>
    </tr>
  `).join("");
  return `
    <section class="report-section">
      <h3>${before ? "Proposed Changes" : "New Work Item"}</h3>
      <div class="table-wrap">
        <table class="change-table">
          <thead>
            <tr>
              <th>Field</th>
              <th>Before</th>
              <th>After</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    </section>
  `;
}

function renderActivityReport(item) {
  if (!item) {
    return emptyReport("No activity captured yet", "Workspace history is empty.");
  }
  const event = item.event;
  const facts = [
    ["Result", label(event.result)],
    ["Actor", event.actor],
    ["Action", label(event.action)],
    ["Work item", `${event.object_type}/${event.object_id}`],
    ["Request", event.request_id],
    ["Source", label(event.source_interface)],
    ["Captured", event.timestamp],
  ];
  return `
    <div class="report-body">
      <div class="report-facts">${facts.map(([name, value]) => factTile(name, value)).join("")}</div>
      ${renderChangeReport(event.before || null, changeRows(event.before || null, event.after || null))}
    </div>
  `;
}

function changeRows(before, after) {
  if (!after && !before) {
    return [];
  }
  const beforeFlat = flattenReportFields(before || {});
  const afterFlat = flattenReportFields(after || {});
  const keys = new Set([...Object.keys(beforeFlat), ...Object.keys(afterFlat)]);
  return [...keys]
    .sort((left, right) => reportFieldRank(left) - reportFieldRank(right) || left.localeCompare(right))
    .filter((key) => JSON.stringify(beforeFlat[key]) !== JSON.stringify(afterFlat[key]))
    .map((key) => ({
      path: key,
      before: beforeFlat[key],
      after: afterFlat[key],
    }));
}

function flattenReportFields(object) {
  const flat = {};
  if (!object || typeof object !== "object") {
    return flat;
  }
  Object.entries(object).forEach(([key, value]) => {
    if (["links", "created_by", "updated_by"].includes(key)) {
      return;
    }
    if (key === "metadata" && value && typeof value === "object") {
      Object.entries(value).forEach(([metadataKey, metadataValue]) => {
        flat[`metadata.${metadataKey}`] = metadataValue;
      });
      return;
    }
    if (value && typeof value === "object" && !Array.isArray(value)) {
      flat[key] = JSON.stringify(value);
      return;
    }
    flat[key] = value;
  });
  return flat;
}

function reportFieldRank(path) {
  const order = ["name", "metadata.title", "metadata.display_name", "stage", "metadata.stage", "status", "health", "amount", "arr", "metadata.state"];
  const index = order.indexOf(path);
  return index === -1 ? 100 : index;
}

function factTile(name, value) {
  return `
    <span class="fact-tile">
      <strong>${escapeHtml(name)}</strong>
      <em>${escapeHtml(displayValue(value))}</em>
    </span>
  `;
}

function reportSection(title, rows) {
  return `
    <section class="report-section">
      <h3>${escapeHtml(title)}</h3>
      <ul>${rows.map((row) => `<li>${escapeHtml(displayValue(row))}</li>`).join("")}</ul>
    </section>
  `;
}

function emptyReport(title, detail) {
  return `
    <div class="empty-report">
      <strong>${escapeHtml(title)}</strong>
      <span>${escapeHtml(detail)}</span>
    </div>
  `;
}

function renderDraftCheckReport(result) {
  const lines = String(result.report || "")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
  const facts = [
    ["Outcome", result.valid ? "passed" : "failed"],
    ["Decision", result.decision],
    ["Proposal", result.proposal_id],
  ].filter(([, value]) => value !== undefined && value !== "");
  return `
    <div class="report-body">
      <div class="report-facts">${facts.map(([name, value]) => factTile(name, value)).join("")}</div>
      ${lines.length ? reportSection("Draft Check", lines) : ""}
    </div>
  `;
}

function renderObjectTypeFilter() {
  const select = byId("objectTypeFilter");
  const current = select.value;
  const options = [`<option value="">All work items</option>`];
  visibleModules().forEach((module) => {
    options.push(`<optgroup label="${escapeHtml(moduleMeta(module.id).name)}">`);
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
  const openRows = openOpportunityRows();
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

function openOpportunityRows() {
  return state.opportunities.filter(
    (opportunity) =>
      !["closed_won", "closed_lost", "renewed", "churned"].includes(opportunity.stage),
  );
}

function renderSkill() {
  const result = state.skills[state.activeSkill];
  if (!result) {
    return;
  }
  byId("skillSummary").textContent = result.summary;
  byId("skillReport").innerHTML = renderCrmSkillReport(result);
  byId("skillOutput").textContent = pretty(result.data);
}

function renderCrmSkillReport(result) {
  const data = result.data || {};
  if (state.activeSkill === "pipeline-summary") {
    return renderPipelineReport(data);
  }
  if (state.activeSkill === "renewal-health") {
    return renderRenewalReport(data);
  }
  if (state.activeSkill === "opportunity-view") {
    return renderOpenDealsReport(data);
  }
  return renderGenericReport(data);
}

function renderPipelineReport(data) {
  const summary = data.summary || state.crmSummary || {};
  const opportunities = data.top_opportunities || data.opportunities || state.opportunities;
  const facts = [
    ["Customers", summary.account_count ?? state.accounts.length],
    ["Open deals", summary.opportunity_count ?? openOpportunityRows().length],
    ["Open pipeline", money.format(summary.open_pipeline_amount || 0)],
    ["Weighted", money.format(summary.weighted_pipeline_amount || 0)],
    ["At risk", summary.at_risk_account_count ?? atRiskAccounts().length],
  ];
  return `
    <div class="report-body">
      <div class="report-facts">${facts.map(([name, value]) => factTile(name, value)).join("")}</div>
      ${opportunityReportTable("Top Open Deals", opportunities)}
    </div>
  `;
}

function renderRenewalReport(data) {
  const accounts = data.accounts || data.at_risk_accounts || atRiskAccounts();
  const facts = [
    ["Accounts needing attention", accounts.length],
    ["Total customers", state.accounts.length],
    ["Booked ARR", money.format((state.crmSummary || {}).total_arr || 0)],
  ];
  const rows = accounts.map((account) => `
    <tr>
      <td><strong>${escapeHtml(account.name || account.id)}</strong><span>${escapeHtml(account.id || "")}</span></td>
      <td><span class="pill ${escapeHtml(account.health || "")}">${escapeHtml(label(account.health || "unknown"))}</span></td>
      <td>${escapeHtml(account.renewal_date || "none")}</td>
      <td>${money.format(account.open_pipeline_amount || 0)}</td>
    </tr>
  `).join("") || emptyRow(4, "No renewal risk");
  return `
    <div class="report-body">
      <div class="report-facts">${facts.map(([name, value]) => factTile(name, value)).join("")}</div>
      <section class="report-section">
        <h3>Renewal Attention</h3>
        <div class="table-wrap">
          <table class="change-table">
            <thead>
              <tr><th>Customer</th><th>Health</th><th>Renewal</th><th>Pipeline</th></tr>
            </thead>
            <tbody>${rows}</tbody>
          </table>
        </div>
      </section>
    </div>
  `;
}

function renderOpenDealsReport(data) {
  const opportunities = data.opportunities || data.open_opportunities || openOpportunityRows();
  const total = opportunities.reduce((sum, item) => sum + Number(item.amount || 0), 0);
  const weighted = opportunities.reduce((sum, item) => sum + Number(item.weighted_amount || 0), 0);
  const facts = [
    ["Open deals", opportunities.length],
    ["Pipeline", money.format(total)],
    ["Weighted", money.format(weighted)],
  ];
  return `
    <div class="report-body">
      <div class="report-facts">${facts.map(([name, value]) => factTile(name, value)).join("")}</div>
      ${opportunityReportTable("Open Deals", opportunities)}
    </div>
  `;
}

function opportunityReportTable(title, opportunities) {
  const rows = opportunities.map((opportunity) => `
    <tr>
      <td><strong>${escapeHtml(opportunity.account_name || opportunity.account_id || opportunity.id)}</strong><span>${escapeHtml(opportunity.id || "")}</span></td>
      <td><span class="pill">${escapeHtml(label(opportunity.stage || ""))}</span></td>
      <td>${money.format(opportunity.amount || 0)}</td>
      <td>${money.format(opportunity.weighted_amount || 0)}</td>
      <td>${escapeHtml(opportunity.close_date || "")}</td>
    </tr>
  `).join("") || emptyRow(5, "No open deals");
  return `
    <section class="report-section">
      <h3>${escapeHtml(title)}</h3>
      <div class="table-wrap">
        <table class="change-table">
          <thead>
            <tr><th>Deal</th><th>Stage</th><th>Amount</th><th>Weighted</th><th>Close</th></tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    </section>
  `;
}

function renderGenericReport(data) {
  if (!data || !Object.keys(data).length) {
    return emptyReport("No report data", "Report returned no rows.");
  }
  const facts = Object.entries(data)
    .filter(([, value]) => typeof value !== "object")
    .slice(0, 6);
  return `
    <div class="report-body">
      <div class="report-facts">${facts.map(([name, value]) => factTile(label(name), value)).join("")}</div>
    </div>
  `;
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
  renderRecordForm(payload.object);
  byId("requestId").value = requestId("ui");
  byId("recordFields").value = "";
  setRecordAction("read");
  byId("recordResultSummary").textContent = "Work item loaded";
  byId("recordResultReport").innerHTML = renderRecordResultReport("Work item loaded", {
    path: payload.path,
    hash: payload.hash,
    object_type: payload.object.object_type,
    object_id: payload.object.id,
  });
  byId("recordOutput").textContent = pretty({
    path: payload.path,
    hash: payload.hash,
  });
  renderObjects();
  renderModules();
}

function renderProposals() {
  const proposals = visibleProposals();
  byId("proposalCount").textContent = `${proposals.length} requests`;
  const rows = proposals.map((item) => {
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
  if (state.selectedProposal && !proposals.some((item) => item.path === state.selectedProposal.path)) {
    state.selectedProposal = null;
  }
  if (!state.selectedProposal && proposals.length) {
    selectProposal(proposals[0].path);
  } else {
    renderSelectedProposal();
  }
  renderCompanyDashboard();
}

function selectProposal(path) {
  state.selectedProposal = visibleProposals().find((item) => item.path === path) || null;
  renderProposals();
  renderSelectedProposal();
}

function visibleProposals() {
  return state.proposals.filter((item) => {
    const moduleId = moduleForObjectType(item.proposal?.object_type);
    return !moduleId || personaAllowsModule(moduleId);
  });
}

function renderSelectedProposal() {
  const selected = state.selectedProposal;
  if (!selected) {
    byId("selectedProposalTitle").textContent = "Approval Request";
    byId("selectedProposalPath").textContent = "No request selected";
    byId("proposalFacts").innerHTML = "";
    byId("proposalReport").innerHTML = renderProposalReport(null);
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
    ["Remaining", displayApprovers(selected.remaining_approvers)],
  ].map(([name, value]) => `
    <span><strong>${escapeHtml(name)}</strong>${escapeHtml(value)}</span>
  `).join("");
  byId("proposalReport").innerHTML = renderProposalReport(selected);
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
  } else if (!state.auditEvents.length) {
    byId("auditReport").innerHTML = renderActivityReport(null);
    byId("auditOutput").textContent = "{}";
  }
  renderCompanyDashboard();
}

function selectAuditEvent(path) {
  state.selectedAuditEvent = state.auditEvents.find((item) => item.path === path) || null;
  byId("auditPath").textContent = state.selectedAuditEvent ? state.selectedAuditEvent.path : "No activity selected";
  byId("auditReport").innerHTML = renderActivityReport(state.selectedAuditEvent);
  byId("auditOutput").textContent = pretty(state.selectedAuditEvent || {});
  renderAuditEvents();
}

function renderUsers() {
  const list = byId("usersList");
  if (!list) {
    return;
  }
  byId("adminPersona").innerHTML = adminPersonaOptions();
  byId("usersCount").textContent = `${state.users.length} users`;
  byId("userAdminSummary").textContent = currentPersona().views.includes("users")
    ? `${currentPersona().label} can manage users`
    : "Admin access required";
  list.innerHTML = state.users.map((user) => {
    const persona = PERSONAS[user.persona] || {};
    return `
      <button class="list-row" type="button">
        <span>
          <strong>${escapeHtml(user.display_name || user.uid)}</strong>
          <small>${escapeHtml(user.uid)} / ${escapeHtml(user.email || "no email")}</small>
        </span>
        <em>${escapeHtml(persona.label || label(user.persona))} / ${escapeHtml((user.modules || []).map(moduleName).join(", "))}</em>
      </button>
    `;
  }).join("") || `<p class="empty">No users</p>`;
}

function adminPersonaOptions() {
  return Object.entries(PERSONAS).map(([value, persona]) => `
    <option value="${escapeHtml(value)}">${escapeHtml(persona.label)}</option>
  `).join("");
}

function moduleName(moduleId) {
  return moduleMeta(moduleId).name;
}

async function createUser() {
  const payload = await fetchJson("/users", {
    method: "POST",
    body: {
      uid: byId("adminUid").value.trim(),
      passcode: byId("adminPasscode").value,
      display_name: byId("adminDisplayName").value.trim(),
      email: byId("adminEmail").value.trim(),
      persona: byId("adminPersona").value,
    },
  });
  byId("userAdminSummary").textContent = `${payload.user.uid} added`;
  byId("adminUid").value = "";
  byId("adminPasscode").value = "";
  byId("adminDisplayName").value = "";
  byId("adminEmail").value = "";
  await loadUsers();
  setStatus("User added");
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
  renderRecordForm(null);
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
  byId("proposalReport").innerHTML = renderRecordResultReport("Publication draft written", result);
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
  byId("proposalReport").innerHTML = renderDraftCheckReport(result);
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
  if (!personaAllowsTemplate(templateId)) {
    throw new Error(`${currentPersona().label} cannot start that work item`);
  }
  const object = withUniqueId(template.build());
  state.activeModule = template.module;
  state.recordModuleFilter = template.module;
  state.selectedObject = null;
  byId("objectTypeFilter").value = "";
  byId("selectedObjectTitle").textContent = recordName(object);
  byId("selectedObjectPath").textContent = "New work item";
  byId("objectEditor").value = pretty(object);
  renderRecordForm(object);
  setRecordAction("create");
  byId("recordFields").value = "";
  byId("requestId").value = requestId("ui");
  byId("recordResultSummary").textContent = `${template.label} template loaded`;
  byId("recordResultReport").innerHTML = renderRecordResultReport(`${template.label} template loaded`, {
    object_type: template.object_type,
    object_id: object.id,
    decision: "ready",
  });
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
  if (!personaAllowsModule(moduleId)) {
    setStatus(`${currentPersona().label} cannot open that module`);
    return;
  }
  state.activeModule = moduleId;
  state.recordModuleFilter = moduleId;
  state.selectedObject = null;
  byId("objectTypeFilter").value = "";
  activateView("records");
  loadObjects().catch((error) => setStatus(error.message));
  renderModules();
}

function openModule(moduleId) {
  if (!personaAllowsModule(moduleId)) {
    setStatus(`${currentPersona().label} cannot open that module`);
    return;
  }
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
  byId("recordResultReport").innerHTML = renderRecordResultReport(summary, payload);
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
  return moduleById(state.activeModule) || visibleModules()[0] || state.modules[0] || null;
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
  return visibleTemplateIds(moduleId).map((templateId) => {
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
  const actor = currentIdentity().username || "anonymous";
  return {
    id,
    object_type: objectType,
    owner: actor,
    created_by: actor,
    updated_by: actor,
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

function roleLabel(value) {
  return ROLE_LABELS[value] || label(value);
}

function displayApprovers(values) {
  const approvers = values || [];
  return approvers.length ? approvers.map(roleLabel).join(", ") : "none";
}

function displayValue(value) {
  if (value === undefined || value === null || value === "") {
    return "none";
  }
  if (typeof value === "boolean") {
    return value ? "yes" : "no";
  }
  if (Array.isArray(value)) {
    return value.length ? value.map(displayValue).join(", ") : "none";
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
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

byId("recordForm").addEventListener("input", (event) => {
  updateObjectFromField(event.target);
});

byId("recordForm").addEventListener("change", (event) => {
  updateObjectFromField(event.target);
});

byId("objectEditor").addEventListener("input", () => {
  try {
    const object = JSON.parse(byId("objectEditor").value);
    renderRecordForm(object);
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

byId("objectTypeFilter").addEventListener("change", () => {
  state.recordModuleFilter = "";
  state.selectedObject = null;
  loadObjects().catch((error) => setStatus(error.message));
});

bindAsync("loginButton", loginUser);
bindAsync("registerButton", registerUser);
bindAsync("logoutButton", logoutUser);
bindAsync("refreshButton", loadWorkspace);
bindAsync("createUserButton", createUser);
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

restoreSession().catch((error) => {
  setStatus(error.message);
});
