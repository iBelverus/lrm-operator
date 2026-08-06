# LRM Operator

Kubernetes operator for managing **Lockable Resources** — resources that can be locked by Pods or manually reserved by personnel.

Built with [Kopf](https://kopf.readthedocs.io/) (Python) and [Pydantic](https://docs.pydantic.dev/).

## CRDs

| CRD | Purpose |
|---|---|
| `LockableResourceTemplate` | Generates child `LockableResource` objects (generated or static) |
| `LockableResource` | Single lockable unit (`free` → `locked` → `reserved` state machine) |

API group: `lrm.openlab.io/v1alpha1`

## Examples

Example LockableResourceTemplates are in the [`examples/`](examples/) directory:

| File | Type | Description |
|---|---|---|
| [`generated-template.yaml`](examples/generated-template.yaml) | `generated` | Creates 5 numbered CI runner slots |
| [`static-template.yaml`](examples/static-template.yaml) | `static` | Creates 3 named lab device resources |

### Testing with Examples

```bash
# Apply example templates
kubectl apply -f examples/generated-template.yaml
kubectl apply -f examples/static-template.yaml

# Verify templates are ready
kubectl get lockableresourcetemplates
# NAME          TYPE        READY   COUNT
# ci-runners    generated   true    5
# lab-devices   static      true    3

# Check generated lockable resources
kubectl get lockableresources
# NAME              PHASE   POD   RESERVED BY
# ci-runners-0      free
# ci-runners-1      free
# ci-runners-2      free
# ci-runners-3      free
# ci-runners-4      free
# thermal-camera    free
# oscilloscope      free
# fpga-devkit       free

# Test manual reservation
kubectl patch lockableresource thermal-camera --type=merge \
  -p '{"status":{"phase":"reserved","reservedBy":"ops-team"}}'

# Test Pod lock (annotate a Pod with the resource name)
kubectl run test-pod --image=nginx --restart=Never \
  --overrides='{"metadata":{"annotations":{"lrm.openlab.io/lockable-resource":"ci-runners-0"}}}'
```

## Quick Start

### Prerequisites

- Python 3.12+
- Kubernetes cluster (e.g. [kind](https://kind.sigs.k8s.io/))

### Local Development

```bash
# Create venv and install uv
python3 -m venv .venv
source .venv/bin/activate
pip install uv

# Install dependencies
uv pip install kopf kubernetes pydantic pyyaml
uv pip install pytest pytest-asyncio ruff

# Deploy CRDs
kubectl apply -f deploy/crds/

# Run operator locally
kopf run --module lrm_operator --verbose
```

### Lint

```bash
ruff check src/ tests/
ruff format --check src/ tests/
```

### Tests

```bash
pytest tests/ -v
```

### Docker

```bash
docker build -t lrm-operator .
```

### In-Cluster Deployment

```bash
kubectl create namespace lrm-system
kubectl apply -f deploy/crds/
kubectl apply -f deploy/rbac.yaml
kubectl apply -f deploy/deployment.yaml
```

## State Machine

```
free ──(Pod starts)─────────────────→ locked
free ──(personnel)──────────────────→ reserved
locked ──(Pod done, reservedBy set)─→ reserved
locked ──(Pod done, reservedBy nil)─→ free
reserved ──(personnel)──────────────→ free
```

## Pod Binding

Annotate a Pod with `lrm.openlab.io/lockable-resource: <name>` to acquire a lock on a `LockableResource`.

## License

Apache License 2.0
