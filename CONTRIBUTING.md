# Contributing to Serverless Cookbook

This repository helps Serverless customers complete common tasks with small,
easy-to-follow examples. Each example should teach one runnable path from inputs
to a checked result. Production features belong here when they are the task the
example teaches.

## Keep the code simple

- Use one pinned runtime and its supported API; avoid runtime version detection.
- Expose the few inputs a customer needs to change. Define defaults once.
- Show clear stages: load inputs, run the workload, save or serve the result.
- Prefer standard library CLI parsing and plain progress messages to extra wrappers.
- Use a workload's Python API or supported CLI directly. Keep necessary launchers.
- Choose one output route for the first run: a mounted bucket or an explicit upload.
- Let unexpected failures raise. A required upload failure must fail the Job.
- Preserve useful input checks, authentication, TLS, and complete-checkpoint checks.
- Keep optional plots, benchmarks, tracking, and tuning below the first run or in
  a linked guide. Do not bundle run-result directories just to show validation.
- Keep each example self-contained; avoid a shared orchestration framework.

## What to contribute

- Runnable, workload-first examples with clear input/output behavior.
- Open contribution scope for categories:
  `quickstarts/`, `training/`, `inference/`, `agents/`, `robotics/`, `life-science/`, `mlops/`.

### `quickstarts/`

Use for first-run examples with the lowest setup cost.

Expected scope:

- first job and first endpoint flows
- small, fast validation workloads
- minimal setup with explicit success criteria

### `training/`

Use when the main value is model training or fine-tuning.

Expected scope:

- framework-specific training runs
- fine-tuning workflows (for example LoRA/QLoRA)
- distributed or multi-GPU training patterns

### `inference/`

Use for serving and batch inference workloads.

Expected scope:

- endpoint-based model serving
- batch inference over prompts or datasets
- OpenAI-compatible API serving patterns

### `agents/`

Use for workloads where agent behavior is the core workload.

Expected scope:

- concrete tasks with clear outcomes
- explicit runtime model and tool usage
- clear deployment pattern

### `robotics/`

Use for simulation, dataset generation, and robotics-adjacent compute workflows.

Expected scope:

- simulation jobs
- synthetic dataset generation
- robotics-oriented GPU/CPU pipelines

### `life-science/`

Use for health, biology, and life-science workloads that are recognizable and runnable.

Expected scope:

- drug discovery workflows
- protein folding workloads
- genomics pipelines
- molecular simulations
- batch processing pipelines for scientific data
- reproducible domain-specific examples

Contributor expectation for all sections:

- prefer updating an existing example over creating a near-duplicate
- keep examples concise, runnable, and easy to adapt
- include practical commands and expected output

## What not to contribute

- Planning-only docs
- Marketing copy
- Placeholder examples without a runnable path


## Required example layout

Each example directory should be self-contained and easy to scan.

```text
example-name/
├─ README.md
├─ scripts/               # optional
├─ src/                   # optional
└─ assets/                # optional
```

Minimum required files:

- `README.md`
- runnable config/command files needed for first execution

## README front matter

Store lightweight metadata in YAML front matter at the top of each example `README.md`.

Console templates under `templates/` may use their existing `config.json` and
Deploy URL as metadata instead. Catalog READMEs do not need example front matter.

Recommended fields:

- `title`
- `category`
- `type`
- `runtime`
- `frameworks`
- `keywords`
- `difficulty`

`category` must be one of:
`quickstarts`, `training`, `inference`, `agents`, `robotics`, `life-sciences`.

## README checklist

Keep README files concise and practical. Include:

1. Goal and expected result; explain why a Job or Endpoint fits.
2. Before you start: required tools, access, compute, and inputs.
3. Run: one copyable sequence with a short explanation of Serverless arguments.
4. Verify: resource status plus a concrete log, response, or durable artifact.
5. Adapt and finish: useful inputs to change, cleanup, and short troubleshooting.

State how the current version was checked. Local syntax checks, image builds,
CLI dry runs, and live workload checks are different evidence. For an Endpoint,
show deletion to stop billing. For a Job that produces files, show where the files
survive completion. Never commit tenant IDs or secrets; public image references
may include their registry namespace.

Run `python3 scripts/check_examples.py` for lightweight file/link/syntax checks.
Then use the example's smallest meaningful workload to verify changed behavior.

## Naming rules

- Use kebab-case directory names
- Prefer workload-first names (for example: `vllm-endpoint`, `first-job`)
- Avoid generic names like `demo1`, `sample-project`

## Submission checklist

- [ ] Example is runnable end-to-end
- [ ] Workload and outcome are obvious within 5 minutes
- [ ] Compute assumptions are explicit
- [ ] `README.md` includes expected output
- [ ] `README.md` includes accurate YAML front matter
- [ ] No secrets or tenant-specific values are committed
