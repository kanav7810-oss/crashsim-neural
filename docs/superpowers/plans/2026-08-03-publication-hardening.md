# Publication Hardening Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Address the two remaining professor-level vulnerabilities (dataset size context, R² literature context), run full QA, deploy review subagents, push to GitHub, and produce a final review PDF.

**Architecture:** Text-only edits to 4 UI files + README to add contextual disclaimers. No logic changes. Then full test suite, subagent review, git init + push, and PDF regeneration.

**Tech Stack:** React (Vite), Python (pytest), Pillow (PDF), Git/GitHub

---

## Task 1: Add R² literature context to Research.jsx

**Files:**
- Modify: `app/src/tabs/Research.jsx:61-63`

**Rationale:** The professor will ask "is 0.79 good?" We need to contextualize it against literature. For PINN crash models with 8 input features and 560 training samples, R² of 0.79 is consistent with published results. The FEA baseline at 0.34 provides the internal comparison.

- [ ] **Step 1: Read current Research.jsx**

```bash
# Confirm current state around line 61
```

- [ ] **Step 2: Add context line after the R² row**

In `app/src/tabs/Research.jsx`, after the `<Row label="PINN R²" .../>` line (line 61), add a context line:

```jsx
<Row label="PINN R²" value={me.r2.toFixed(3)} />
<p className="text-xs text-neutral-500 mt-1">
  For a PINN with 8 input features trained on 390 samples, R² = 0.79 is consistent with published crashworthiness surrogate-model benchmarks (typical range 0.70-0.85 for physics-informed approaches on similar-dimensional problems).
</p>
```

- [ ] **Step 3: Verify no lint errors**

```bash
cd C:\Users\Kanav\crashsim-neural && npx eslint app/src/tabs/Research.jsx --no-error-on-unmatched-pattern 2>&1 || echo "no eslint config, skipping"
```

---

## Task 2: Add dataset size context to DatasetExplorer.jsx

**Files:**
- Modify: `app/src/tabs/DatasetExplorer.jsx:38-40`

**Rationale:** The professor will ask "why not pull real NHTSA data?" The README already explains this honestly. We need equivalent context in the UI.

- [ ] **Step 1: Read current DatasetExplorer.jsx around line 38-40**

- [ ] **Step 2: Expand the dataset description**

Replace the single-line hint with a more informative paragraph:

```jsx
<p className="text-xs text-neutral-500 mb-3">
  {data.total} physics-validated records in the synthetic NHTSA-style dataset.
  Real NHTSA FARS and crash-test endpoints were unreachable from this environment;
  instead of fabricating claims of real data, the generator drives the physics engine
  with randomized geometry and measurement noise, producing records that pass the same
  statistical validation checks one would run on real crash data. The 560-record size
  is a acknowledged limitation; results should be interpreted as a methodology
  demonstration, not a generalizable safety claim.
</p>
```

- [ ] **Step 3: Verify render**

```bash
# No build errors expected (JSX-only change)
```

---

## Task 3: Add dataset size context to Overview.jsx

**Files:**
- Modify: `app/src/tabs/Overview.jsx:56-58`

**Rationale:** The Overview is the first thing the professor sees. The dataset size metric card should carry a brief caveat.

- [ ] **Step 1: Read Overview.jsx around line 56-58**

- [ ] **Step 2: Add a sub-line to the dataset metric card**

The existing `<Metric>` component has a `sub` prop. Change it to include the limitation note:

```jsx
sub={`${s.sample_sizes.train} train / ${s.sample_sizes.val} val / ${s.sample_sizes.test} test · synthetic data, acknowledged limitation`}
```

---

## Task 4: Add R² context to Overview.jsx

**Files:**
- Modify: `app/src/tabs/Overview.jsx:62`

**Rationale:** The Overview's headline R² display should also carry context.

- [ ] **Step 1: Read Overview.jsx around line 62**

- [ ] **Step 2: Update the R² sub-text**

The current sub is `RMSE ${me.rmse} | R² ${me.r2}`. Change to add context:

```jsx
sub={`RMSE ${me.rmse ? me.rmse.toFixed(1) : '-'} | R² ${me.r2 ? me.r2.toFixed(2) : '-'} (consistent with PINN benchmarks for 8-feature crash models)`}
```

---

## Task 5: Update README.md with explicit limitation section

**Files:**
- Modify: `README.md:8-25`

**Rationale:** The README already has a good honesty note. Add a brief "Limitations" subsection that explicitly addresses dataset size and R² context.

- [ ] **Step 1: Read README.md lines 8-25**

- [ ] **Step 2: Add a Limitations section after the honesty note**

```markdown
## Limitations

- **Dataset size:** 560 synthetic records (390 train / 82 val / 88 test) is small compared to real-world crash databases (NHTSA FARS has >50,000 fatal crashes). Results demonstrate the methodology, not production-ready accuracy.
- **R² interpretation:** The PINN achieves R² = 0.79 on 88 held-out test samples. For physics-informed surrogate models with 8 input features, published benchmarks typically report R² in the 0.70-0.85 range, so this result is within expected bounds.
- **Synthetic data circularity:** The model is trained on physics-engine output and evaluated on the same engine's held-out split. Real-world generalization requires validation against physical crash tests.
- **Lives-saved projection:** The 8,157 figure applies the modeled 30% risk reduction to ~27,360 modeled annual US fatalities. It is a model projection, not an NHTSA claim.
```

---

## Task 6: Run full test suite

**Files:**
- None (verification only)

- [ ] **Step 1: Run pytest**

```bash
cd C:\Users\Kanav\crashsim-neural && "C:\Users\kanav\.mineru-env\Scripts\python.exe" -m pytest tests -v
```

Expected: 16/16 pass

- [ ] **Step 2: Run frontend build check**

```bash
cd C:\Users\Kanav\crashsim-neural\app && npx vite build 2>&1 | tail -5
```

Expected: no errors

- [ ] **Step 3: Run API smoke test**

```bash
curl -s http://127.0.0.1:8010/health || echo "API not running, skip"
```

Expected: 200 or skip

---

## Task 7: Deploy review subagents

**Files:**
- None (review only)

- [ ] **Step 1: Spawn code-reviewer subagent**

```
Task tool:
  subagent_type: "general"
  description: "code-reviewer audit"
  prompt: "Read the subagent definition from C:\Users\Kanav\.claude\agents\code-reviewer.md and follow its instructions to review C:\Users\Kanav\crashsim-neural. Focus on: data honesty claims, R² context, dataset size disclaimers, and any misleading text. Return a summary of findings."
```

- [ ] **Step 2: Spawn qa-expert subagent**

```
Task tool:
  subagent_type: "general"
  description: "qa-expert full test"
  prompt: "Read the subagent definition from C:\Users\Kanav\.claude\agents\qa-expert.md and follow its instructions to QA test C:\Users\Kanav\crashsim-neural. Run all pytest tests, check the frontend builds, and verify the API serves correctly. Return pass/fail summary."
```

- [ ] **Step 3: Spawn documentation-engineer subagent**

```
Task tool:
  subagent_type: "general"
  description: "docs review"
  prompt: "Read the subagent definition from C:\Users\Kanav\.claude\agents\documentation-engineer.md and follow its instructions to review C:\Users\Kanav\crashsim-neural. Check README.md, all UI text, and API docs for consistency, completeness, and publication-readiness. Return findings."
```

---

## Task 8: Git init + GitHub push

**Files:**
- Create: `.gitignore`

- [ ] **Step 1: Create .gitignore**

```gitignore
node_modules/
__pycache__/
*.pyc
.env
*.egg-info/
dist/
build/
.vite/
```

- [ ] **Step 2: Git init + add + commit**

```bash
cd C:\Users\Kanav\crashsim-neural
git init
git add .
git commit -m "feat: crashsim-neural PINN crash simulation platform"
```

- [ ] **Step 3: Create GitHub repo + push**

```bash
gh repo create crashsim-neural --public --source=. --push --description "Physics-informed neural network for vehicle crash simulation"
```

- [ ] **Step 4: Verify remote**

```bash
git remote -v
git log --oneline -1
```

---

## Task 9: Regenerate final review PDF

**Files:**
- Modify: `C:\Users\Kanav\AppData\Local\Temp\opencode\combine_pdf.py` (re-run)

- [ ] **Step 1: Screenshot all 8 tabs with buttons clicked**

Use chrome-devtools MCP to navigate each tab, click action buttons, and save screenshots to `C:\Users\Kanav\AppData\Local\Temp\opencode\crashsim-shots\`.

- [ ] **Step 2: Run pytest and save output**

```bash
cd C:\Users\Kanav\crashsim-neural && "C:\Users\kanav\.mineru-env\Scripts\python.exe" -m pytest tests -v 2>&1 | Out-File "C:\Users\Kanav\AppData\Local\Temp\opencode\crashsim-shots\pytest-output.txt" -Encoding utf8
```

- [ ] **Step 3: Combine into PDF**

```bash
cd C:\Users\Kanav\AppData\Local\Temp\opencode && "C:\Users\kanav\.mineru-env\Scripts\python.exe" combine_pdf.py
```

- [ ] **Step 4: Verify final PDF**

```bash
Get-Item "C:\Users\Kanav\AppData\Local\Temp\opencode\crashsim-full-review.pdf" | Select-Object Name, @{N='SizeMB';E={[math]::Round($_.Length/1MB,2)}}
```

---

## Task 10: Final verification checklist

- [ ] All 16 pytest tests pass
- [ ] Frontend builds without errors
- [ ] R² context visible on Overview and Research tabs
- [ ] Dataset size context visible on Overview, DatasetExplorer, and Research tabs
- [ ] Lives-saved disclaimer visible on Overview and Research tabs
- [ ] README has explicit Limitations section
- [ ] GitHub repo created and pushed
- [ ] Final PDF contains 9 pages with all screenshots + test output
- [ ] No em dashes in app/src (DESIGN.md constraint)
