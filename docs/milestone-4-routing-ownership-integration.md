# Milestone 4 — Routing Ownership Context Integration

## Objective

Integrate the already accepted Kubernetes EndpointSlice/Pod/controller ownership artifact into workload inventory and incident impact context without adding infrastructure reads, RBAC, telemetry, or remediation.

## Inputs

Local same-cycle artifacts only:

```text
/var/lib/infra-assurance/evidence/inventory.json
/var/lib/infra-assurance/evidence/kubernetes-routing-ownership.json
/var/lib/infra-assurance/evidence/incident-candidates.json
```

The routing artifact remains authoritative for the routing observation performed by this platform slice. The base topology selector relation remains separate and weaker.

## Output semantics

### Workload inventory

Final inventory version becomes `0.4`.

Every workload gains a `relationships.routing_services` array. It is populated only when:

```text
routing source overall = COMPLETE
route state = RESOLVED_WORKLOAD_ROUTING
route scope completeness = COMPLETE
exact workload subject joins current inventory
```

Existing `relationships.services` selector inference remains unchanged.

Inventory also carries a compact sanitized Service-route state projection so `NON_POD_ROUTING`, missing endpoints, partial routing, and unknown routing remain first-class context.

### Incident candidates

Final incident-candidate version becomes `0.2` and records routing source status.

Only exact `SERVICE` candidate subjects are eligible for routing-based impact-context enrichment.

When complete routing is available, routing-owned workloads replace selector-inferred related workloads for that Service candidate. Multi-controller routing is preserved.

When exact observed routing says `NON_POD_ROUTING`, `NO_ENDPOINTS_OBSERVED`, `PARTIAL_ROUTING`, `SERVICE_NOT_OBSERVED`, or `UNKNOWN`, no workload impact relation is asserted from the selector fallback.

When there is no exact routing record at all, the previous selector inference may remain visible as a weaker fallback.

Namespace and Platform candidates are not promoted through Service routing. This protects the scope correction accepted in PR #20.

## Runtime placement

```text
kubernetes_runtime
routing_ownership
alert_scope_runtime
incident_runtime
routing_context_integration
```

The last step atomically rewrites the local inventory and incident artifacts and their summaries. It contains no query-capable client.

## Extension schemas

The base schemas continue to describe artifacts before this final post-step. Integration-specific final fields are validated by:

```text
schemas/workload-routing-integration.schema.json
schemas/incident-routing-integration.schema.json
```

## Trust boundary

- routing evidence is ownership/routing context, not application health;
- a related routed workload is not automatically an impacted workload;
- selector inference remains distinguishable from observed routing;
- multiple real backend controllers remain multiple;
- non-Pod routing does not become workload ownership;
- partial/failed routing does not become absence;
- no raw routing path, address, Pod spec, Secret-related data, logs, or credentials are copied downstream;
- `mutation_allowed=false` remains unchanged.

## Acceptance focus

The management-host gate must validate:

1. full pytest suite passes;
2. no RBAC diff from main;
3. no query-capable client in `routing_context_integration.py`;
4. systemd final post-step succeeds;
5. routing source remains `COMPLETE` on the current cluster;
6. inventory version is `0.4` and incident version `0.2`;
7. selector and routing relations remain separately labeled;
8. `loki-headless` retains both real backend controllers in routing inventory context;
9. kubelet Service remains `NON_POD_ROUTING` and gains no workload routing relation;
10. current Namespace/Platform incident candidates from PR #20 are not promoted into Service/workload scope;
11. sensitive/full-object guard remains clean;
12. no root-cause or business-impact language is introduced.
