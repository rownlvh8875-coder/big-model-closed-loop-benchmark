# Namespace diagnostic design

The user authorized proceeding autonomously with the first remaining step: identify why the consumed builder request failed at isolated loopback RTM_NEWADDR. This is a new model-free diagnostic, not a retry of builder-20261113-01. Main, Cloud publication, all 45 existing workflows, old artifacts and scientific budgets stay unchanged.

Use installed Ubuntu 24.04 host Python and Linux syscalls, with no package installation or downloaded code. Three fresh bounded workers test USER_NET, USER_NET_DROP_BOUNDING and USER_NET_DROP_ALL_CAPS. Each must prove both user and network namespaces changed, map the calling UID/GID, and only then attempt loopback address/link changes. Bounding and effective capability changes are separate interventions. The all-capabilities-cleared case is a negative control. No changes to host network, sysctls, AppArmor or seccomp policy are authorized by this protocol.

Record only whitelisted namespace IDs, capabilities, numeric errno, known AppArmor labels (unknown text is hashed), kernel/image identifiers and relevant sanitized kernel capability denials. A missing kernel log is UNKNOWN. Capability observations alone do not prove an LSM cause. Successful diagnosis does not prove the complete builder sandbox or scientific benchmark ready.

Alternatives considered: rerunning the consumed builder cannot isolate the cause and violates its budget; globally disabling AppArmor would obscure the cause and broaden host policy. A new narrowly scoped syscall diagnostic gives causal evidence with fewer side effects. This choice is the implementer's under the user's explicit instruction to proceed without further questions.

New exact branch diagnose/engine-clock-namespace-20261113-01, request namespace-diagnostic-20261113-01, one run/attempt, three workers. Reviewed source closure and GitHub API bind checkout, workflow, request, run/head, branch and attempt. The activation commit changes only the new request. Outputs are bounded artifacts, preserved as original bytes. Any targeted repair/build is a separately registered action after diagnosis.
