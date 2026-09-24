# Waterology documentation

Start with [How to use the research workflow](workflow-guide.md). It maps the
pieces, explains when to use them, and follows a project from a question to
recorded evidence and a reproducible deliverable.

| Guide | Use it to |
| --- | --- |
| [Engineering](engineering.md) | Build or repair to a specification, or optimize under fixed constraints |
| [Workflow guide](workflow-guide.md) | Choose skills, experiments, workflows, studies, and deliverables |
| [Getting started](getting-started.md) | Install Waterology, initialize a project, and run an experiment |
| [Workflow execution](workflow-execution.md) | Register project tasks, execute them, and reproduce a selected result |
| [Managed studies](managed-studies.md) | Authorize bounded iteration, compare evidence, and record conclusions |
| [Configuration](configuration.md) | Declare commands, outputs, metrics, archives, and compute profiles |
| [Personal configuration](local-configuration.md) | Keep private preferences and machine settings outside the package |
| [TORC execution](torc.md) | Prepare workers and diagnose local, remote, or Slurm execution |
| [RO-Crate integration](ro-crate.md) | Inspect automatic crates, export run provenance, and interpret validation |
| [Workflow Run RO-Crate evaluation](workflow-run-ro-crate.md) | Read the profile design and interoperability evaluation |

The files under `superpowers/specs/` and `superpowers/plans/` are design and
implementation records. They explain why behavior exists, but are not setup
guides. The `validation/` directory records checks performed at specific
revisions; those records do not establish readiness in a new environment.
