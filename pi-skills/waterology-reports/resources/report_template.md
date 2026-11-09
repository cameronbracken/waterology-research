# <Report Title> (`<report-id-YYYY-MM-DD>`)

**Date:** <Month Day, Year>  
**Report ID:** `<report-id-YYYY-MM-DD>`  
**Primary Engine / Simulator:** `<Primary Engine>`  
**Core Deliverables:** `<Deliverable 1>` + `<Deliverable 2>`  
**Companion Reference Document:** `COMPARISON_MODELS.md` *(Complete Mathematical and Architectural Reference for Baselines and Methods)*

---

## 1. Executive Summary

1. **`[<TAG-1>]` - <First Major Contribution Title>:**
   - Concise summary of implementation changes with relative source links (`../../src/package/module.py#L1-L50`) and headline metrics (**`KGE(Q) = 0.8825`**, **`1.42e-14 m3/s`** parity).
2. **`[<TAG-2>]` - <Second Major Contribution Title>:**
   - Summary of diagnostic methodology, verification gates, and scientific findings.

---

## 2. Verification Gates and Sanity Checks

`![Figure 1: Mandatory Verification Gates and Precision Audit]({{figures_dir}}/fig1_verification_gates.png)`
**Figure 1:** *(a) Mandatory verification gate scorecard across all structural, parity, and anti-leakage checks; (b) $-\log_{10}(\text{Error})$ precision audit confirming machine-precision agreement and zero test-window leakage.*

<details>
<summary><strong>Table 1: Mandatory Verification Gate Requirements and Measured Results (Click to expand)</strong></summary>

**Table 1:** *Summary of mandatory verification gates enforced in `../../tests/test_suite.py`.*

| Gate | Verification Test | Requirement | Measured Result | Status |
| :--- | :--- | :--- | :--- | :---: |
| **Gate 1** | `test_gate1_...` | `< 1e-9` max difference | **`1.42e-14`** | **PASS** |
| **Gate 2** | `test_gate2_...` | Zero test-canary sensitivity (`max |delta_theta| == 0.0`) | **`0.0`** | **PASS** |

</details>

---

## 3. Primary Benchmark and Experimental Results

`![Figure 2: Cross-Family Comparison (Ordered Asc Left / Desc Right of Red Line) and Horizon Crossover]({{figures_dir}}/fig2_cross_family_comparison.png)`
**Figure 2:** *(a) Cross-family comparison of held-out performance, ordered **lowest-to-highest left of the vertical red line** (Proposed Family) and **highest-to-lowest right of the red line** (Statistical/ML and Literature Baselines); (b) Performance across state re-initialization windows (`1-Day`, `7-Day`, `30-Day`, `Annual WY-Reset`, `Open-Loop`).*

<details>
<summary><strong>Table 2: Cross-Family Performance Summary Across All Evaluation Horizons (Click to expand)</strong></summary>

**Table 2:** *Held-out performance across all evaluation cadences (ordered matching Figure 2a: Proposed Family ascending, then Baselines descending by Primary Sort Key).*

| Side of Red Line / Family | Model | Info Class | `1-Day` Reset | `30-Day` Reset | **Annual Reset (Sort Key)** | **Open-Loop** |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Left (Proposed, Asc $\uparrow$)** | `Model A (Variant 1)` | `Class 2` | 0.6680 | 0.5890 | **0.5855** | 0.5852 |
| **Left (Proposed, Peak $\uparrow$)** | **`Model A (Best)`** | `Class 3` | 0.7854 | 0.6789 | **0.6860** | **0.6761** |
| **Right (Baselines, Peak $\downarrow$)** | `Baseline 1` | `Class 1` | 0.6812 | 0.6485 | **0.6419** | 0.6034 |
| **Right (Baselines, Desc $\downarrow$)** | `Baseline 2` | `Class 3-Exh` | **0.9569** | **0.7289** | **0.5802** | 0.5435 |

</details>

> [!IMPORTANT]
> **Physical and Mathematical Explanation of Key Mechanism:**
> Explain *why* the observed ranking, regime crossover, or parameter sensitivity occurs so any reader or peer reviewer has complete clarity without needing to inspect the source code.
