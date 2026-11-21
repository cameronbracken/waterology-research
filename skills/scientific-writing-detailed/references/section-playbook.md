# Manuscript Section Playbook

Apply these section architectures, rhetorical moves, and prose patterns when drafting or restructuring scientific papers. Adapt headings to the target journal's house format.

## 1. Choosing the macro-structure

Select the section layout that matches the contribution:

- **Empirical, physical, or scenario analysis paper:** `Abstract` -> `1. Introduction` -> `2. Data and Methods` (opening with a model-chain overview and schematic `Figure 1`, followed by data, definitions, and experimental setup subsections) -> `3. Results` (organized by property, scale, season, and spatial co-occurrence) -> `4. Discussion` -> `5. Limitations` (dedicated section or `Limitations and Discussion`) -> `6. Conclusions` -> `Data and Code Availability`.
- **Methodological or statistical modeling paper:** Separate the general formulation from the specific case study so readers see that the method transfers to other domains: `Abstract` -> `1. Introduction` -> `2. Proposed Framework` (general model structure, joint/marginal likelihood, priors or estimation, and step-by-step simulation or inference algorithm) -> `3. Application` (study area, data filtering, covariates, distributional/copula adequacy tests, implementation details, and baseline comparison models) -> `4. Results` -> `5. Discussion and Conclusions` -> `Data and Code Availability`.
- **Data descriptor paper:** `Abstract` -> `Background & Summary` (system role, dataset gap, spatial/temporal coverage, scenarios, and end-to-end modeling chain `Figure 1`) -> `Methods` (forcing, process models, calibration objective and budget justification, operational constraint approximations) -> `Data Records` (archive link, file-naming convention, and column-by-column schema with units and join keys) -> `Technical Validation` (split-sample calibration/validation, out-of-sample cross-validation, station/facility verification, and multi-model benchmark comparison) -> `Usage Notes` -> `Code Availability`.

## 2. Move-by-move section blueprints

### Title, Highlights, Abstract, and Plain Language Summary

- **Title:** Use a specific, descriptive noun phrase naming the method or phenomenon, spatial/temporal scale, and domain (for example, _Spatial Bayesian Hierarchical Modeling of Seasonal Runoff Extremes Over a Large Domain_). Avoid puns, colon-heavy marketing slogans, and vague claims.
- **Key Points / Highlights (when required):** Write 3 concise, parallel single-sentence claims (~12 to 20 words each): (1) methodological or dataset contribution, (2) primary quantitative or directional finding, and (3) spatial, seasonal, or operational takeaway.
- **Abstract (single paragraph, ~150 to 250 words, no subheadings unless required):**
  1. _Context and stakes (1-2 sentences):_ Name the physical or engineering phenomenon and why it matters for planning, reliability, or design.
  2. _Gap (1-2 sentences):_ Pinpoint what existing datasets, definitions, or models omit (such as intersite dependence, seasonal timescales, multivariate coupling, or evolving infrastructure).
  3. _Approach (1-2 sentences):_ State the contribution with an active verb (`In this study, we present ...`, `We propose ...`, `We examine ...`), naming the model or dataset, spatial unit, and historical/future period.
  4. _Quantitative findings (2-4 sentences):_ Report concrete results (`Results indicate that ...`, `We find that ...`) with specific magnitudes, durations, seasons, regions, or uncertainty reductions relative to a baseline.
  5. _Operational consequence (1 sentence):_ Close with how the findings or dataset inform design, forecasting, or planning models.
- **Plain Language Summary:** Translate jargon into concrete terms (`rare hydrologic events (e.g., floods)`, `prolonged periods of low wind and solar generation`) while keeping the same 5-move sequence and measured tone without oversimplifying uncertainty.

### Introduction (4 to 7 paragraphs)

1. **System and operational motivation (Paragraph 1):** Open with the physical phenomenon or engineering problem and connect it immediately to concrete system vulnerability or management decisions. An intuitive contrast or well-known historical episode can anchor the stakes.
2. **Thematic literature synthesis and structural critiques (Paragraphs 2 to 5):** Organize prior work by **mechanism, spatial/temporal scale, or modeling class**, never as a chronological author-by-author list. Credit key studies concisely (`Author et al. (Year) analyze ... finding that ...`), then pivot with `However,`, `While attractive,`, or `Despite this growing body of literature,` to expose the structural trade-off:
   - Single-site or independent marginals vs. network/multisite spatial dependence;
   - Purely atmospheric metrics vs. translation into system-scale operational impacts;
   - Computational bottlenecks (such as $O(n^3)$ covariance inversions or low-rank knot artifacts) over large domains;
   - Short-term stationarity vs. multidecadal climate regimes or evolving infrastructure.
3. **Contribution, scale justification, and roadmap (Final paragraph):**
   - Pivot cleanly (`To address these limitations,`, `To this end, in this study we develop ...`, `Given the lack of ..., we propose ...`).
   - Explicitly justify **why the chosen spatial unit and temporal aggregation** match the decision process.
   - Include a numbered list of 2 to 3 research questions or required model properties only when the study has distinct coupled objectives.
   - Close with a compact 2 to 4 sentence organization roadmap (`This paper is organized as follows: Section 2 describes ...`).

### Data and Methods (or Proposed Framework + Application)

- **Pipeline overview first:** When a study couples multiple datasets or models, begin the section with a high-level narrative paragraph paired with a schematic flowchart (`Figure 1`) explaining what each stage takes as input and passes downstream before detailing individual components.
- **Data provenance and filtering:** State the data source, spatial resolution, period of record, spin-up/calibration/validation windows, and exact station/facility inclusion rules (for example, `Of the 1,492 facilities in the source database, 1,452 are retained, with 40 excluded due to records shorter than 2 years or zero generation throughout the period`). Call out known observational or reanalysis biases and explain how bias correction or per-period normalization addresses them.
- **Model formulation and assumptions:**
  - Introduce model layers in operational or hierarchical order (data layer -> process/parameter layer -> priors/constraints).
  - Justify distributional and functional choices explicitly (support bounds, tail behavior, parameter interpretability, parsimony).
  - Test key structural assumptions rather than taking them on faith (such as testing multivariate normality or asymptotic tail independence when applying a Gaussian copula, or running sensitivity checks on block/group sizes and percentile thresholds).
- **Estimation, computation, and validation:** Specify optimization or MCMC algorithms, chain counts, iteration and warmup budgets, convergence thresholds ($\hat{R} < 1.1$), approximate runtime/hardware when computationally nontrivial, named baseline models, and out-of-sample validation designs (split-sample, leave-one-out, drop-$k$% holdout, or retroactive operational hindcast).

### Results

- **Organize by analytical question or dimension:** Group subsections around distinct properties (severity, duration, seasonality, spatial co-occurrence, experimental isolation of drivers, or baseline skill comparison) rather than walking mechanically through model outputs.
- **Isolate drivers cleanly:** When multiple drivers act together (such as climate change and infrastructure buildout, or marginal distributions and copula dependence), structure paired comparisons or differences that isolate one factor while holding the other fixed, and explain that experimental logic at the top of the subsection.
- **Orient, observe, contrast, explain:**
  1. Orient the reader to the figure/table layout and visual encoding (`Figure 4 shows ... Solid lines denote the median and shaded ribbons span the 5th to 95th percentiles.`).
  2. State the primary quantitative or spatial pattern.
  3. Contrast regions, seasons, timescales, or competing models with concrete numbers.
  4. Offer the concise physical or statistical reason (`This pattern reflects ...`, `This reduction in uncertainty stems from borrowing strength across correlated variables.`) and flag any artifacts or null results honestly.

### Discussion, Limitations, and Conclusions

- **Discussion:** Synthesize overarching mechanisms (such as seasonal resource complementarity, tail-heaviness vs. regression shrinkage, or spatial plant density effects) rather than repeating the Results table. Connect findings to downstream modeling practice and concrete recommendations (`We therefore recommend that capacity expansion and adequacy studies represent ...`).
- **Limitations (dedicated section or explicit paragraphs):** Put methodological and data limits in plain view:
  - What process, variable, or feedback was omitted (such as transmission congestion, human reservoir management at multi-year scales, tail dependence, or dynamic event frequency under thermodynamic replay forcing);
  - How that omission bounds interpretation of the current results; and
  - What specific data or model extension would address it in future work.
- **Conclusions (2 to 4 compact paragraphs):** Summarize the framework/dataset and domain scope in 2 to 3 sentences, distill the 3 to 4 durable empirical or methodological takeaways and their planning implications, and end with concrete, bounded next extensions.
- **Data and Code Availability:** Provide direct archive citations and persistent repository links for input datasets, derived outputs, and analysis scripts.

## 3. Target prose patterns (synthetic domain-neutral examples)

### Pattern A: Thematic literature critique and gap pivot

- _Avoid (chronological list + hype):_
  > Smith (2019) studied river floods. Jones (2021) used copulas for two gauges. Lee (2023) used nonstationary GEV models. However, nobody has ever built a truly revolutionary framework that combines all of these vital pieces together!
- _Prefer (thematic grouping + structural trade-off + grounded contribution):_
  > Regional frequency analysis reduces parameter uncertainty by pooling observations across sites, while copula-based models explicitly represent pairwise dependence among hydrologic variables. Nonstationary extensions further allow distribution parameters to vary with large-scale climate indices. Despite this body of work, existing formulations typically treat spatial pooling, multivariate dependence, and temporal nonstationarity in isolation or rely on maximum likelihood fits that struggle to converge on short gauge records. Here we combine Generalized Extreme Value marginals, time-varying climate covariates, and a Gaussian elliptical copula within a unified Bayesian hierarchical framework that propagates parameter uncertainty directly into return level estimates.

### Pattern B: Equation integration with statistical and operational intuition

- _Avoid (dropped symbol soup):_
  > Equation 1 is the formula:
  > $$R(i, j) = \exp(-\|s_i - s_j\| / \alpha_0)$$
  > $\alpha_0$ is range. $s$ is site.
- _Prefer (grammatical lead-in + complete `where` clause + limiting intuition):_
  > Pairwise spatial dependence between sites is modeled as a function of separation distance using an exponential correlation structure
  > $$R(i, j) = \exp\left(-\frac{\|s_i - s_j\|}{\alpha_0}\right),$$
  > where $s_i$ and $s_j$ denote the coordinates of sites $i$ and $j$, and $\alpha_0 > 0$ is the range parameter controlling the distance over which stations remain correlated. Large values of $\alpha_0$ indicate strong coherence across distant gauges, whereas values approaching zero recover site-by-site independence.

### Pattern C: Self-orienting figure narration and regional contrast

- _Avoid (unoriented pointer + vague adjective):_
  > Results are shown in Figure 2. Winter is very big in the west and summer is much smaller, which proves strong seasonality.
- _Prefer (visual orientation -> primary pattern -> regional contrast -> mechanism):_
  > Figure 2 shows the seasonal distribution of compound deficit months from 1982 to 2019 across all 18 control regions, ordered from west (bottom) to east (top), where each unit bar height represents one deficit month. Deficit events concentrate primarily in fall and winter across western regions, whereas eastern regions experience markedly fewer events overall. This west-to-east gradient reflects stronger seasonal hydropower variability in snowmelt-dominated western basins alongside weaker winter complementarity between wind and solar generation.

### Pattern D: Candid null result and limitation diagnosis

- _Avoid (evasive burial):_
  > Duration changes were mostly flat across runs (Figure 5), which may be explored more in future research.
- _Prefer (direct null statement + experimental diagnosis + interpretive boundary):_
  > No statistically significant trend in event duration was detected across either the infrastructure or climate scenarios (Figure 5), with median durations remaining near 1 day due to the strongly right-skewed duration distribution. This null result likely stems from the thermodynamic replay design of the meteorological forcing, which applies warming perturbations to historical boundary conditions while preserving the historical sequencing and persistence of synoptic weather systems. For this reason, projected changes in multi-day event duration derived from this forcing dataset should be interpreted with caution.
