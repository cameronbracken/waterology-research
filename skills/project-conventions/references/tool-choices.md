# Tool choices

Use these defaults when the task and existing project leave the choice open:

- Prefer local development, command line tools, and readable text output.
  Use a richer interface when it helps explain or inspect a complex relationship.
- Prefer open source, cross-platform, actively maintained software with clear
  documentation. Look for established packages from CRAN, PyPI, or conda-forge
  before writing a custom implementation.
- Prefer Python for general software, larger projects, collaboration, and
  interoperability; R for specialized statistics and ggplot2 graphics; Julia
  for heavy computation; and Fortran 90 or newer when compiled code is required.
  Preserve the project's established language rather than rewriting it.
- Prefer Pixi for system tools, compiled dependencies, and mixed-language work;
  uv for pure Python; rv for new R environments; and direnv for project variables.
  Use [setup-environment](../../setup-environment/SKILL.md) only when creating,
  changing, repairing, or moving an environment.
- Use TORC for managed local and HPC jobs. Obtain the target's allocation and
  job size or count before an HPC submission; follow existing compute authority
  and report costs when the target provides them. Machine names, allocation
  identifiers, and pricing details come from project or private configuration.
- Give long-running work visible progress through a progress bar or concise
  status output. Prefer portable commands and paths over private shell aliases.
- Cite sources and credit human authors, including ORCID when available.
  Record actual AI model use in the project's README statement when appropriate;
  do not invent identities or add unsolicited coauthor or generated-by trailers.
