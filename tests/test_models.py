from __future__ import annotations

from lrm_operator.models import (
    LockableResourceSpec,
    LockableResourceStatus,
    LockableResourceTemplateSpec,
    LockableResourceTemplateStatus,
    ResourceItem,
)


class TestLockableResourceTemplateSpec:
    def test_generated_template(self):
        spec = LockableResourceTemplateSpec(type="generated", number=5)
        assert spec.type == "generated"
        assert spec.number == 5
        assert spec.resource_list is None

    def test_static_template(self):
        items = [ResourceItem(name="res-1", labels={"env": "prod"})]
        spec = LockableResourceTemplateSpec(type="static", resource_list=items)
        assert spec.type == "static"
        assert len(spec.resource_list) == 1
        assert spec.resource_list[0].name == "res-1"

    def test_template_with_labels(self):
        spec = LockableResourceTemplateSpec(
            type="generated",
            number=3,
            main_label="my-resource",
            extra_labels={"team": "backend"},
        )
        assert spec.main_label == "my-resource"
        assert spec.extra_labels == {"team": "backend"}

    def test_template_with_pod_fields(self):
        spec = LockableResourceTemplateSpec(
            type="generated",
            number=1,
            node_selector={"disk": "ssd"},
            service_account_name="my-sa",
        )
        assert spec.node_selector == {"disk": "ssd"}
        assert spec.service_account_name == "my-sa"

    def test_template_alias_mapping(self):
        spec = LockableResourceTemplateSpec.model_validate(
            {
                "type": "generated",
                "number": 2,
                "resourceList": [{"name": "r1"}, {"name": "r2"}],
            }
        )
        assert len(spec.resource_list) == 2


class TestLockableResourceTemplateStatus:
    def test_default_status(self):
        status = LockableResourceTemplateStatus()
        assert status.ready is False
        assert status.generated_count == 0

    def test_ready_status(self):
        status = LockableResourceTemplateStatus(ready=True, generated_count=5)
        assert status.ready is True
        assert status.generated_count == 5


class TestLockableResourceSpec:
    def test_minimal_spec(self):
        spec = LockableResourceSpec(template_ref={"name": "my-template"})
        assert spec.template_ref["name"] == "my-template"

    def test_spec_with_pod_fields(self):
        spec = LockableResourceSpec(
            template_ref={"name": "tpl"},
            node_selector={"gpu": "true"},
            tolerations=[{"key": "dedicated", "operator": "Exists"}],
        )
        assert spec.node_selector == {"gpu": "true"}


class TestLockableResourceStatus:
    def test_default_phase(self):
        status = LockableResourceStatus()
        assert status.phase == "free"

    def test_locked_status(self):
        status = LockableResourceStatus(
            phase="locked",
            pod_ref={"name": "my-pod", "namespace": "default"},
            locked_at="2024-01-01T00:00:00Z",
        )
        assert status.phase == "locked"
        assert status.pod_ref["name"] == "my-pod"

    def test_reserved_status(self):
        status = LockableResourceStatus(
            phase="reserved",
            reserved_by="ops-team",
            reserved_at="2024-01-01T00:00:00Z",
        )
        assert status.phase == "reserved"
        assert status.reserved_by == "ops-team"
