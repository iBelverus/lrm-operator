# CRD Specification

## API Group & Version

- **Group:** `lrm.openlab.io`
- **Version:** `v1alpha1`

---

## 1. LockableResourceTemplate CRD

**Purpose:** Template that generates `LockableResource` children.

### Spec

| Field | Type | Required | Notes |
|---|---|---|---|
| `type` | `string` | Yes | Enum: `generated`, `static` |
| `number` | `int32` | `type=generated` only | Min 1 |
| `resourceList` | `[]ResourceItem{name, labels}` | `type=static` only | Min 1 entry |
| `mainLabel` | `string` | No | Applied to all children |
| `extraLabels` | `map[string]string` | No | Merged onto children |
| `nodeSelector` | `map[string]string` | No | Copied to child Pod contexts |
| `resources` | `corev1.ResourceRequirements` | No | Copied to child Pod contexts |
| `tolerations` | `[]corev1.Toleration` | No | |
| `affinity` | `*corev1.Affinity` | No | |
| `topologySpreadConstraints` | `[]corev1.TopologySpreadConstraint` | No | |
| `serviceAccountName` | `string` | No | |
| `priorityClassName` | `string` | No | |
| `schedulerName` | `string` | No | |
| `runtimeClassName` | `*string` | No | |

### Status

| Field | Type | Description |
|---|---|---|
| `ready` | `bool` | Template processed |
| `generatedCount` | `int32` | Number of children created |
| `conditions` | `[]metav1.Condition` | Ready, GenerationSucceeded |

### Controller Behavior

- `type=generated` → creates `number` children named `<template-name>-<index>`
- `type=static` → creates one child per `resourceList` entry
- Children have owner references → auto garbage collected when template is deleted
- Pod-spec fields copied into each child's spec at creation time

### Kopf Handler (template.py)

```python
import kopf

@kopf.on.create("lrm.openlab.io", "v1alpha1", "lockableresourcetemplates")
async def on_template_create(body, spec, logger, **kwargs):
    ...

@kopf.on.update("lrm.openlab.io", "v1alpha1", "lockableresourcetemplates")
async def on_template_update(body, spec, old, new, logger, **kwargs):
    ...
```

---

## 2. LockableResource CRD

**Purpose:** Single lockable unit. Bound to Pod lifecycle with manual reservation support.

### Spec

| Field | Type | Description |
|---|---|---|
| `templateRef` | `corev1.LocalObjectReference` | Parent template |
| `nodeSelector` | `map[string]string` | Inherited from template |
| `resources` | `corev1.ResourceRequirements` | Inherited from template |
| `tolerations` | `[]corev1.Toleration` | Inherited |
| `affinity` | `*corev1.Affinity` | Inherited |
| `topologySpreadConstraints` | `[]corev1.TopologySpreadConstraint` | Inherited |
| `serviceAccountName` | `string` | Inherited |
| `priorityClassName` | `string` | Inherited |
| `schedulerName` | `string` | Inherited |
| `runtimeClassName` | `*string` | Inherited |

### Status

| Field | Type | Description |
|---|---|---|
| `phase` | `string` | Enum: `free`, `reserved`, `locked` |
| `podRef` | `*corev1.ObjectReference` | Set when `phase=locked` |
| `lockedAt` | `*metav1.Time` | When Pod acquired the lock |
| `reservedBy` | `*string` | Personnel identifier; settable even while `locked` |
| `reservedAt` | `*metav1.Time` | When reservation was placed |
| `conditions` | `[]metav1.Condition` | Standard conditions |

### State Machine

```
free ──(Pod starts)─────────────────→ locked
free ──(personnel)──────────────────→ reserved
locked ──(Pod done, reservedBy set)─→ reserved
locked ──(Pod done, reservedBy nil)─→ free
reserved ──(personnel)──────────────→ free
```

### State Machine Implementation (state_machine.py)

```python
TRANSITIONS: dict[tuple[str, str], str] = {
    ("free",     "pod_start"):      "locked",
    ("free",     "personnel_req"):  "reserved",
    ("locked",   "pod_done_nil"):   "free",
    ("locked",   "pod_done_set"):   "reserved",
    ("reserved", "personnel_clr"):  "free",
}

def transition(current_phase: str, event: str) -> str | None:
    return TRANSITIONS.get((current_phase, event))
```

### Reservation-While-Locked

Personnel can set `reservedBy` on a `locked` resource. On Pod completion:

- `reservedBy` is set → phase becomes `reserved`
- `reservedBy` is nil → phase becomes `free`

Personnel may clear `reservedBy` while locked to re-enable auto-release. Only one locking Pod at a time.

### Invalid Transitions (rejected by controller)

- `reserved` → `locked`
- `locked` → `locked` (already taken)
- `reserved` → `reserved` (already held)
- `free` → `free` (no-op)

### Pod Binding

1. **Annotation:** `lrm.openlab.io/lockable-resource: <name>` on the Pod
2. **Resource claim:** Custom field in Pod spec, validated via mutating webhook or scheduling gate

### Kopf Handler (resource.py)

```python
import kopf

@kopf.on.create("lrm.openlab.io", "v1alpha1", "lockableresources")
async def on_resource_create(body, spec, status, logger, **kwargs):
    ...

@kopf.on.update("lrm.openlab.io", "v1alpha1", "lockableresources")
async def on_resource_update(body, spec, status, old, new, logger, **kwargs):
    ...

@kopf.on.event("", "v1", "pods")
async def on_pod_event(event, body, logger, **kwargs):
    ...
```

### Pydantic Models (models.py)

```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class LockableResourceSpec(BaseModel):
    template_ref: dict

class LockableResourceStatus(BaseModel):
    phase: str  # free, reserved, locked
    pod_ref: Optional[dict] = None
    locked_at: Optional[datetime] = None
    reserved_by: Optional[str] = None
    reserved_at: Optional[datetime] = None
```

---

## 3. RBAC Manifests

Scope: ClusterRole (single operator watches all namespaces).

### LockableResourceTemplate Controller

```yaml
rules:
  - apiGroups: [lrm.openlab.io]
    resources: [lockableresourcetemplates]
    verbs: [get, list, watch]
  - apiGroups: [lrm.openlab.io]
    resources: [lockableresourcetemplates/status]
    verbs: [get, patch, update]
  - apiGroups: [lrm.openlab.io]
    resources: [lockableresources]
    verbs: [get, list, watch, create, update, patch, delete]
```

### LockableResource Controller

```yaml
rules:
  - apiGroups: [lrm.openlab.io]
    resources: [lockableresources]
    verbs: [get, list, watch]
  - apiGroups: [lrm.openlab.io]
    resources: [lockableresources/status]
    verbs: [get, patch, update]
  - apiGroups: [""]
    resources: [pods]
    verbs: [get, list, watch]
  - apiGroups: [""]
    resources: [events]
    verbs: [create, patch]
```

### Leader Election

```yaml
rules:
  - apiGroups: [coordination.k8s.io]
    resources: [leases]
    verbs: [get, list, watch, create, update, patch, delete]
```

---

## 4. Project Structure

```
lrm-operator/
├── pyproject.toml
├── src/
│   └── lrm_operator/
│       ├── __init__.py
│       ├── main.py
│       ├── models.py
│       ├── state_machine.py
│       └── handlers/
│           ├── __init__.py
│           ├── template.py
│           └── resource.py
├── deploy/
│   ├── crds/
│   │   ├── lockableresourcetemplates.yaml
│   │   └── lockableresources.yaml
│   ├── rbac.yaml
│   └── deployment.yaml
├── tests/
│   ├── test_state_machine.py
│   ├── test_template_handler.py
│   └── test_resource_handler.py
├── Dockerfile
├── .gitignore
├── LICENSE
└── README.md
```

## 5. Implementation Steps

1. Create venv + install uv
2. Install deps: kopf, kubernetes, pydantic, pyyaml, pytest, pytest-asyncio, ruff
3. Create `pyproject.toml` with all dependencies and ruff config
4. Define CRD YAMLs in `deploy/crds/` with OpenAPI validation schemas
5. Implement `models.py` — Pydantic `BaseModel` for both CRDs
6. Implement `state_machine.py` — transition table + validation
7. Implement `handlers/template.py` — `@kopf.on.create` / `@kopf.on.update` for template → child resources
8. Implement `handlers/resource.py` — `@kopf.on.update` for phase enforcement, Pod annotation watch
9. Create `main.py` entry point for `kopf run --module lrm_operator`
10. Create `deploy/rbac.yaml` (ClusterRole + ClusterRoleBinding + ServiceAccount)
11. Create `deploy/deployment.yaml` (in-cluster operator Deployment)
12. Tests (unit for state machine + handler tests with KopfRunner / mocked API)
13. Dockerfile (python:3-slim, copy src/, kopf run)
14. Setup kind cluster + README with quick start

See also: [GitHub issue #1](https://github.com/iBelverus/lrm-operator/issues/1)
