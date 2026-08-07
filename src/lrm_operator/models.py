from __future__ import annotations

from pydantic import BaseModel, Field


class ResourceItem(BaseModel):
    name: str = Field(..., description="Resource name")
    labels: dict[str, str] = Field(default_factory=dict, description="Resource labels")


class LockableResourceTemplateSpec(BaseModel):
    model_config = {"populate_by_name": True}

    type: str = Field(..., description="Template type: 'generated' or 'static'")
    number: int | None = Field(
        default=None, description="Number of children to generate (type=generated only)", ge=1
    )
    resource_list: list[ResourceItem] | None = Field(
        default=None,
        alias="resourceList",
        description="Static resource list (type=static only)",
    )
    main_label: str | None = Field(
        default=None, alias="mainLabel", description="Label applied to all children"
    )
    extra_labels: dict[str, str] | None = Field(
        default=None, alias="extraLabels", description="Labels merged onto children"
    )
    node_selector: dict[str, str] | None = Field(
        default=None, alias="nodeSelector", description="Node selector for child Pods"
    )
    resources: dict | None = Field(default=None, description="Resource requirements for child Pods")
    tolerations: list[dict] | None = Field(default=None, description="Tolerations for child Pods")
    affinity: dict | None = Field(default=None, description="Affinity for child Pods")
    topology_spread_constraints: list[dict] | None = Field(
        default=None,
        alias="topologySpreadConstraints",
        description="Topology spread constraints for child Pods",
    )
    service_account_name: str | None = Field(
        default=None, alias="serviceAccountName", description="Service account for child Pods"
    )
    priority_class_name: str | None = Field(
        default=None, alias="priorityClassName", description="Priority class for child Pods"
    )
    scheduler_name: str | None = Field(
        default=None, alias="schedulerName", description="Scheduler name for child Pods"
    )
    runtime_class_name: str | None = Field(
        default=None, alias="runtimeClassName", description="Runtime class for child Pods"
    )


class LockableResourceTemplateStatus(BaseModel):
    model_config = {"populate_by_name": True}

    ready: bool = Field(default=False, description="Whether the template has been processed")
    generated_count: int = Field(
        default=0, alias="generatedCount", description="Number of children created"
    )
    conditions: list[dict] = Field(default_factory=list, description="Standard conditions")


class LockableResourceSpec(BaseModel):
    model_config = {"populate_by_name": True}

    template_ref: dict = Field(
        ..., alias="templateRef", description="Reference to parent LockableResourceTemplate"
    )
    node_selector: dict[str, str] | None = Field(
        default=None, alias="nodeSelector", description="Inherited node selector"
    )
    resources: dict | None = Field(default=None, description="Inherited resource requirements")
    tolerations: list[dict] | None = Field(default=None, description="Inherited tolerations")
    affinity: dict | None = Field(default=None, description="Inherited affinity")
    topology_spread_constraints: list[dict] | None = Field(
        default=None,
        alias="topologySpreadConstraints",
        description="Inherited topology spread constraints",
    )
    service_account_name: str | None = Field(
        default=None, alias="serviceAccountName", description="Inherited service account"
    )
    priority_class_name: str | None = Field(
        default=None, alias="priorityClassName", description="Inherited priority class"
    )
    scheduler_name: str | None = Field(
        default=None, alias="schedulerName", description="Inherited scheduler name"
    )
    runtime_class_name: str | None = Field(
        default=None, alias="runtimeClassName", description="Inherited runtime class"
    )


class LockableResourceStatus(BaseModel):
    model_config = {"populate_by_name": True}

    phase: str = Field(default="free", description="Current phase: free, reserved, locked")
    pod_ref: dict | None = Field(
        default=None, alias="podRef", description="Pod reference when phase=locked"
    )
    locked_at: str | None = Field(
        default=None, alias="lockedAt", description="Timestamp when Pod acquired lock"
    )
    reserved_by: str | None = Field(
        default=None, alias="reservedBy", description="Personnel identifier for reservation"
    )
    reserved_at: str | None = Field(
        default=None, alias="reservedAt", description="Timestamp when reservation was placed"
    )
    conditions: list[dict] = Field(default_factory=list, description="Standard conditions")
