"""Local read API tests."""

from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from company_os_core import (
    APIResponse,
    AccountStage,
    ApprovalStatus,
    CRMAccount,
    CRMOpportunity,
    CustomerHealth,
    LocalReadAPI,
    OpportunityStage,
    Permission,
    PermissionAction,
    PolicyEngine,
    RBACEngine,
    Role,
    User,
    approval_required,
)
from company_os_core.serialization import read_yaml, write_yaml


TIMESTAMP = datetime(2026, 6, 6, 10, 0, 0, tzinfo=timezone.utc)


class LocalReadAPITests(unittest.TestCase):
    def test_root_returns_api_index(self) -> None:
        api = LocalReadAPI(repo_root=Path("."), policy_engine=self._policy_engine())

        response = api.handle_get(
            path="/",
            query={},
            user=User(id="anonymous", username="anonymous"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.body["name"], "opra.ai API")
        self.assertIn("/crm/summary", response.body["endpoints"])
        self.assertIn("/proposals", response.body["endpoints"])
        self.assertIn("/objects/delete", response.body["endpoints"])
        self.assertIn("/github/messages", response.body["endpoints"])

    def test_skills_endpoint_returns_workspace_crud_descriptors(self) -> None:
        api = LocalReadAPI(repo_root=Path("."), policy_engine=self._policy_engine())

        response = api.handle_get(
            path="/skills",
            query={},
            user=User(id="ssabbani", username="ssabbani", roles=("founder",)),
        )

        self.assertEqual(response.status_code, 200)
        skill_names = {skill["name"] for skill in response.body["skills"]}
        self.assertIn("record-create", skill_names)
        self.assertIn("record-read", skill_names)
        self.assertIn("record-update", skill_names)
        self.assertIn("record-delete", skill_names)

    def test_health_returns_ok_without_crm_data(self) -> None:
        api = LocalReadAPI(repo_root=Path("."), policy_engine=self._policy_engine())

        response = api.handle_get(
            path="/health",
            query={},
            user=User(id="anonymous", username="anonymous"),
        )

        self.assertEqual(response, APIResponse(status_code=200, body={"status": "ok"}))

    def test_crm_summary_returns_authorized_summary(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_seed(root)
            api = LocalReadAPI(repo_root=root, policy_engine=self._policy_engine())

            response = api.handle_get(
                path="/crm/summary",
                query={},
                user=User(id="ssabbani", username="ssabbani", roles=("sales_rep",)),
            )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.body["summary"]["account_count"], 1)
            self.assertEqual(response.body["summary"]["weighted_pipeline_amount"], 325000)

    def test_crm_accounts_denies_user_without_read_permission(self) -> None:
        with TemporaryDirectory() as temp_dir:
            api = LocalReadAPI(repo_root=Path(temp_dir), policy_engine=self._policy_engine())

            response = api.handle_get(
                path="/crm/accounts",
                query={},
                user=User(id="viewer", username="viewer", roles=()),
            )

            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.body["object_type"], "account")

    def test_crm_opportunities_filters_by_account_and_limit(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_seed(root)
            self._write_account(root, self._account(account_id="acct_other", name="Other Corp"))
            self._write_opportunity(
                root,
                self._opportunity(
                    opportunity_id="opp_other",
                    account_id="acct_other",
                    amount=900000,
                    probability=0.2,
                ),
            )
            api = LocalReadAPI(repo_root=root, policy_engine=self._policy_engine())

            response = api.handle_get(
                path="/crm/opportunities",
                query={"account_id": "acct_other", "limit": "1"},
                user=User(id="ssabbani", username="ssabbani", roles=("sales_rep",)),
            )

            self.assertEqual(response.status_code, 200)
            opportunities = response.body["opportunities"]
            self.assertEqual(len(opportunities), 1)
            self.assertEqual(opportunities[0]["id"], "opp_other")

    def test_crm_skill_endpoint_returns_skill_result(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_seed(root)
            api = LocalReadAPI(repo_root=root, policy_engine=self._policy_engine())

            response = api.handle_get(
                path="/crm/skills/pipeline-summary",
                query={"limit": "1"},
                user=User(id="ssabbani", username="ssabbani", roles=("sales_rep",)),
            )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.body["decision"], "allow")
            self.assertIn("500000 open pipeline", response.body["summary"])

    def test_unknown_crm_skill_returns_not_found(self) -> None:
        api = LocalReadAPI(repo_root=Path("."), policy_engine=self._policy_engine())

        response = api.handle_get(
            path="/crm/skills/missing",
            query={},
            user=User(id="ssabbani", username="ssabbani", roles=("sales_rep",)),
        )

        self.assertEqual(response.status_code, 404)

    def test_objects_endpoint_lists_and_validates_source_records(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_seed(root)
            api = LocalReadAPI(repo_root=root, policy_engine=self._policy_engine())

            list_response = api.handle_get(
                path="/objects",
                query={},
                user=User(id="ssabbani", username="ssabbani", roles=("sales_rep",)),
            )

            self.assertEqual(list_response.status_code, 200)
            self.assertEqual(len(list_response.body["objects"]), 2)

            validate_response = api.handle_post(
                path="/objects/validate",
                body={"path": "modules/crm/objects/accounts/acct_acme.yaml"},
                user=User(id="ssabbani", username="ssabbani", roles=("sales_rep",)),
            )

            self.assertEqual(validate_response.status_code, 200)
            self.assertTrue(validate_response.body["valid"])
            self.assertEqual(validate_response.body["object_type"], "account")

    def test_modules_endpoint_groups_records_by_module(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_seed(root)
            write_yaml(
                root / "modules/issues/objects/defects/defect_demo.yaml",
                self._base_record("defect_demo", "defect"),
            )
            write_yaml(
                root / "modules/hr/objects/employees/emp_demo.yaml",
                self._base_record("emp_demo", "employee", visibility="hr_private"),
            )
            api = LocalReadAPI(repo_root=root, policy_engine=self._policy_engine())

            response = api.handle_get(
                path="/modules",
                query={},
                user=User(id="ssabbani", username="ssabbani", roles=("founder",)),
            )

            self.assertEqual(response.status_code, 200)
            modules = {module["id"]: module for module in response.body["modules"]}
            self.assertEqual(modules["crm"]["record_count"], 2)
            self.assertEqual(modules["issues"]["type_counts"]["defect"], 1)
            self.assertEqual(modules["hr"]["type_counts"]["employee"], 1)

    def test_generic_reads_are_filtered_by_policy(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_seed(root)
            write_yaml(
                root / "modules/issues/objects/defects/defect_demo.yaml",
                self._base_record("defect_demo", "defect"),
            )
            write_yaml(
                root / "modules/hr/objects/employees/emp_demo.yaml",
                self._base_record("emp_demo", "employee", visibility="hr_private"),
            )
            api = LocalReadAPI(repo_root=root, policy_engine=self._policy_engine())
            user = User(id="ssabbani", username="ssabbani", roles=("sales_rep",))

            modules = api.handle_get(path="/modules", query={}, user=user)
            self.assertEqual(modules.status_code, 200)
            self.assertEqual([module["id"] for module in modules.body["modules"]], ["crm"])

            denied_module = api.handle_get(path="/objects", query={"module": "hr"}, user=user)
            self.assertEqual(denied_module.status_code, 403)

            denied_object = api.handle_get(
                path="/object",
                query={"path": "modules/hr/objects/employees/emp_demo.yaml"},
                user=user,
            )
            self.assertEqual(denied_object.status_code, 403)

            denied_preview = api.handle_get(path="/github/previews/prs", query={}, user=user)
            self.assertEqual(denied_preview.status_code, 403)

            denied_messages = api.handle_get(path="/github/messages", query={}, user=user)
            self.assertEqual(denied_messages.status_code, 403)

    def test_proposal_lifecycle_can_be_driven_through_api(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_seed(root)
            api = LocalReadAPI(repo_root=root, policy_engine=self._policy_engine())
            account_path = root / "modules/crm/objects/accounts/acct_acme.yaml"
            account = dict(read_yaml(account_path))
            account["metadata"] = {"source": "workspace"}
            account["updated_at"] = "2026-06-06T10:05:00Z"
            account["version"] = 2

            created = api.handle_post(
                path="/proposals",
                body={
                    "object": account,
                    "action": "update",
                    "request_id": "req_workspace_metadata",
                    "fields": ["metadata"],
                },
                user=User(id="ssabbani", username="ssabbani", roles=("sales_rep",)),
            )

            self.assertEqual(created.status_code, 201)
            proposal = created.body["proposal"]
            proposal_id = proposal["id"]
            self.assertEqual(proposal["status"], "proposed")
            self.assertEqual(proposal["required_approvers"], ["sales_manager"])

            approved = api.handle_post(
                path=f"/proposals/{proposal_id}/approve",
                body={"reason": "metadata approved"},
                user=User(id="ssabbani", username="ssabbani", roles=("sales_manager",)),
            )

            self.assertEqual(approved.status_code, 200)
            self.assertEqual(approved.body["proposal"]["status"], "approved")

            applied = api.handle_post(
                path=f"/proposals/{proposal_id}/apply",
                body={},
                user=User(id="ssabbani", username="ssabbani", roles=("founder",)),
            )

            self.assertEqual(applied.status_code, 200)
            self.assertEqual(applied.body["proposal"]["status"], "applied")
            self.assertEqual(read_yaml(account_path)["metadata"], {"source": "workspace"})

            audit = api.handle_get(
                path="/audit/events",
                query={},
                user=User(id="ssabbani", username="ssabbani", roles=("founder",)),
            )

            self.assertEqual(audit.status_code, 200)
            self.assertEqual(len(audit.body["events"]), 1)
            self.assertEqual(audit.body["events"][0]["event"]["source"]["interface"], "web")

    def test_github_issue_preview_create_and_update(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            api = LocalReadAPI(repo_root=root, policy_engine=self._policy_engine())
            user = User(id="ssabbani", username="ssabbani", roles=("founder",))

            created = api.handle_post(
                path="/github/issues",
                body={
                    "title": "Workspace smoke issue",
                    "body": "Created from the local UI.",
                    "labels": ["crm"],
                },
                user=user,
            )

            self.assertEqual(created.status_code, 201)
            self.assertEqual(created.body["issue"]["number"], 1)

            updated = api.handle_post(
                path="/github/issues/1",
                body={"state": "closed", "labels": ["validated"]},
                user=user,
            )

            self.assertEqual(updated.status_code, 200)
            self.assertEqual(updated.body["issue"]["state"], "closed")
            self.assertEqual(updated.body["issue"]["labels"], ["crm", "validated"])

            previews = api.handle_get(
                path="/github/previews/issues",
                query={},
                user=user,
            )

            self.assertEqual(previews.status_code, 200)
            self.assertEqual(len(previews.body["issues"]), 1)

    def test_github_message_thread_create_and_reply(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            api = LocalReadAPI(repo_root=root, policy_engine=self._policy_engine())
            user = User(id="ssabbani", username="ssabbani", roles=("founder",))

            created = api.handle_post(
                path="/github/messages",
                body={
                    "title": "Launch room",
                    "body": "Coordinate the launch checklist.",
                    "participants": ["@sabbanis", "octocat"],
                    "repo_url": "https://github.com/acme/opra.ai",
                },
                user=user,
            )

            self.assertEqual(created.status_code, 201)
            thread = created.body["thread"]
            self.assertEqual(thread["pull_request"]["number"], 1)
            self.assertEqual(thread["participants"], ["@sabbanis", "octocat"])
            self.assertEqual(thread["messages"][0]["author"], "ssabbani")

            replied = api.handle_post(
                path=f"/github/messages/{thread['id']}/comments",
                body={
                    "body": "I added the release owner.",
                    "repo_url": "https://github.com/acme/opra.ai",
                },
                user=user,
            )

            self.assertEqual(replied.status_code, 200)
            self.assertEqual(len(replied.body["thread"]["messages"]), 2)
            self.assertEqual(replied.body["thread"]["messages"][1]["body"], "I added the release owner.")
            self.assertEqual(replied.body["thread"]["messages"][1]["id"], "1")

            second = api.handle_post(
                path="/github/messages",
                body={
                    "title": "Second room",
                    "body": "Another top-level message.",
                    "repo_url": "https://github.com/acme/opra.ai",
                },
                user=user,
            )

            self.assertEqual(second.status_code, 201)
            self.assertEqual(second.body["thread"]["pull_request"]["number"], 2)

            listed = api.handle_get(path="/github/messages", query={}, user=user)
            self.assertEqual(listed.status_code, 200)
            self.assertEqual(len(listed.body["threads"]), 2)

    def test_delete_object_removes_file_and_records_audit_event(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_seed(root)
            account_path = root / "modules/crm/objects/accounts/acct_acme.yaml"
            api = LocalReadAPI(repo_root=root, policy_engine=self._policy_engine())

            response = api.handle_post(
                path="/objects/delete",
                body={
                    "path": "modules/crm/objects/accounts/acct_acme.yaml",
                    "request_id": "req_delete_account",
                },
                user=User(id="ssabbani", username="ssabbani", roles=("founder",)),
            )

            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.body["deleted"])
            self.assertFalse(account_path.exists())

            audit = api.handle_get(
                path="/audit/events",
                query={},
                user=User(id="ssabbani", username="ssabbani", roles=("founder",)),
            )
            self.assertEqual(audit.status_code, 200)
            self.assertEqual(audit.body["events"][0]["event"]["action"], "delete")
            self.assertEqual(audit.body["events"][0]["event"]["result"], "completed")

    def test_delete_object_denies_user_without_permission(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_seed(root)
            account_path = root / "modules/crm/objects/accounts/acct_acme.yaml"
            api = LocalReadAPI(repo_root=root, policy_engine=self._policy_engine())

            response = api.handle_post(
                path="/objects/delete",
                body={
                    "path": "modules/crm/objects/accounts/acct_acme.yaml",
                    "request_id": "req_denied_delete",
                },
                user=User(id="ssabbani", username="ssabbani", roles=("sales_rep",)),
            )

            self.assertEqual(response.status_code, 403)
            self.assertFalse(response.body["deleted"])
            self.assertTrue(account_path.exists())

    def test_unknown_route_returns_not_found(self) -> None:
        api = LocalReadAPI(repo_root=Path("."), policy_engine=self._policy_engine())

        response = api.handle_get(
            path="/missing",
            query={},
            user=User(id="ssabbani", username="ssabbani", roles=("sales_rep",)),
        )

        self.assertEqual(response.status_code, 404)

    def _policy_engine(self) -> PolicyEngine:
        founder = Role(
            id="founder",
            name="Founder",
            permissions=(
                Permission(
                    subject="founder",
                    action=PermissionAction.ALL,
                    object_type="*",
                    scope="company",
                ),
            ),
        )
        sales_rep = Role(
            id="sales_rep",
            name="Sales Rep",
            permissions=(
                Permission(
                    subject="sales_rep",
                    action=PermissionAction.READ,
                    object_type="account",
                    scope="company",
                ),
                Permission(
                    subject="sales_rep",
                    action=PermissionAction.READ,
                    object_type="opportunity",
                    scope="company",
                ),
                Permission(
                    subject="sales_rep",
                    action=PermissionAction.UPDATE,
                    object_type="account",
                    scope="owned_by_me",
                    fields=("status", "tags", "metadata"),
                ),
            ),
        )
        sales_manager = Role(
            id="sales_manager",
            name="Sales Manager",
            permissions=(
                Permission(
                    subject="sales_manager",
                    action=PermissionAction.READ,
                    object_type="account",
                    scope="company",
                ),
                Permission(
                    subject="sales_manager",
                    action=PermissionAction.APPROVE,
                    object_type="account",
                    scope="company",
                ),
            ),
        )
        return PolicyEngine(
            rbac=RBACEngine(roles=(founder, sales_rep, sales_manager)),
            approval_rules=(
                approval_required(
                    object_type="account",
                    action=PermissionAction.UPDATE,
                    fields=("metadata",),
                    required_approvers=("sales_manager",),
                    reason="Account metadata changes require sales manager approval in demo policy.",
                    rule_id="account_metadata_approval",
                ),
            ),
        )

    def _write_seed(self, root: Path) -> None:
        self._write_account(root, self._account())
        self._write_opportunity(root, self._opportunity())

    def _write_account(self, root: Path, account: CRMAccount) -> None:
        write_yaml(root / f"modules/crm/objects/accounts/{account.id}.yaml", account)

    def _write_opportunity(self, root: Path, opportunity: CRMOpportunity) -> None:
        write_yaml(
            root / f"modules/crm/objects/opportunities/{opportunity.id}.yaml",
            opportunity,
        )

    def _account(
        self,
        account_id: str = "acct_acme",
        name: str = "Acme Corp",
    ) -> CRMAccount:
        return CRMAccount(
            id=account_id,
            owner="ssabbani",
            created_by="ssabbani",
            updated_by="ssabbani",
            created_at=TIMESTAMP,
            updated_at=TIMESTAMP,
            name=name,
            stage=AccountStage.ACTIVE_CUSTOMER,
            industry="manufacturing",
            arr=250000,
            health=CustomerHealth.YELLOW,
            renewal_date="2026-09-30",
        )

    def _opportunity(
        self,
        opportunity_id: str = "opp_acme_renewal_2026",
        account_id: str = "acct_acme",
        amount: int = 500000,
        probability: float = 0.65,
    ) -> CRMOpportunity:
        return CRMOpportunity(
            id=opportunity_id,
            owner="ssabbani",
            created_by="ssabbani",
            updated_by="ssabbani",
            created_at=TIMESTAMP,
            updated_at=TIMESTAMP,
            account_id=account_id,
            stage=OpportunityStage.PROPOSAL,
            amount=amount,
            probability=probability,
            close_date="2026-09-30",
            discount_requested=12,
            next_step="Send renewal proposal and technical validation plan",
            approval_status=ApprovalStatus.PENDING_FINANCE,
        )

    def _base_record(
        self,
        object_id: str,
        object_type: str,
        visibility: str = "company",
    ):
        return {
            "id": object_id,
            "object_type": object_type,
            "owner": "ssabbani",
            "created_by": "ssabbani",
            "updated_by": "ssabbani",
            "created_at": "2026-06-06T10:00:00Z",
            "updated_at": "2026-06-06T10:00:00Z",
            "version": 1,
            "status": "active",
            "visibility": visibility,
            "links": [],
            "tags": [],
            "metadata": {},
        }


if __name__ == "__main__":
    unittest.main()
