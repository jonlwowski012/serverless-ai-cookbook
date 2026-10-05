# Plan: make the Serverless AI cookbook easy to run and learn from

**Status:** implementation applied, October 5, 2026. The runnable paths and concrete code candidates below have been simplified. See [validation notes](validation.md) for completed checks and remaining workload validation.

## Purpose

This repository should help a customer complete a common task with Nebius Serverless and understand the few platform choices that matter. A reader should be able to answer: Why a Job or Endpoint? What do I need? What do I run? How do I know it worked? Where is the result? What should I change for my workload?

Nebius describes Jobs as run-to-completion tasks and Endpoints as request-serving resources. Job container disks disappear after completion, so examples that produce durable files need an explicit storage handoff. [Nebius overview](https://docs.nebius.com/serverless/overview). The [official Job](https://docs.nebius.com/serverless/quickstart/jobs) and [Endpoint](https://docs.nebius.com/serverless/quickstart/endpoints) quickstarts model the short create → check → use path. [Google's procedure guide](https://developers.google.com/style/procedures) recommends one short route with commands, placeholders, and expected results. See the [research notes](research/serverless-cookbook-simplicity.md) for sources and findings.

## The shape of an example

Use the existing [contribution rules](../CONTRIBUTING.md) as the base. Make the README show one tested path in this order:

1. **Goal and outcome:** one sentence naming the workload, the Serverless resource, and the expected result.
2. **Before you start:** only the required account access, tools, model or dataset access, region, and GPU/preset. Define each value once; never commit tenant IDs or secrets.
3. **Run:** a short, copyable sequence from the example directory. Use the CLI or a small `job.sh` only when it removes repeated, confusing arguments. Show the image, command, platform/preset, timeout, and storage mount where they teach the Serverless pattern.
4. **Verify:** capture the resource ID; check terminal Job state and logs or Endpoint readiness and an authenticated request. Give one concrete expected log line, response, or durable object path.
5. **Adapt and finish:** name the two or three inputs a customer should change, link to deeper reference material, and show Endpoint stop/delete or persistent-artifact cleanup when relevant.

Keep model internals, alternate hardware, long evaluations, and production tuning below the first run or in a linked page. Do not introduce a shared orchestration framework or a rigid line limit. Keep validation that protects inputs, secrets, and published outputs. Templates can use a one-click Console path, but should still show the request, result, authentication, and cleanup.

## Simplify the actual code

The code should teach the workload and the Serverless handoff. A reader should be able to follow the main path without first learning a configuration framework, several compatibility branches, or a custom runner. Start by deleting unused behavior, then rewrite what remains in plain steps. Fewer lines are useful only when the result is easier to understand.

### Rules for the implementation

- **Support one documented runtime.** Pin dependencies in the image and call that version's API directly. Remove signature inspection, alternate import paths, executable discovery, and legacy argument names after verifying the pinned runtime. Add a compatibility branch only when the example explicitly teaches multiple runtimes.
- **Expose only useful inputs.** Keep model/dataset, run length, and output location configurable when customers need to change them. Put fixed demonstration settings in one visible block. Avoid repeating the same default across environment variables, CLI arguments, configuration classes, and JSON/YAML. Keep distributed training or experiment tracking in examples that teach those features.
- **Use a short sequence of named stages.** For a longer script, make `main()` read as load inputs → run workload → save result. Extract functions for meaningful stages or repeated operations; keep small scripts inline. Prefer descriptive variables and ordinary loops over nested expressions, generic dispatch, or one-line forwarding helpers.
- **Use the workload library directly when practical.** Call an installed Python API for Python work. Use a short shell command for a command-line tool. Keep subprocesses when an upstream CLI is the supported interface, a launcher initializes distributed state, or process isolation is required; do not replace those with an improvised API.
- **Choose one storage route per first run.** If a mounted bucket meets the example's requirements, write the output there directly. If the lesson is an S3 upload, use one client and a short upload loop. Avoid configuring the AWS CLI from Python while also using boto3. Keep the required local scratch space and publication order for workloads that cannot safely write directly to a mount.
- **Let unexpected errors fail clearly.** Use required environment lookups, normal exceptions, and `subprocess.run(..., check=True)`. Remove broad catch-and-continue blocks, optional dependency imports for packages installed by the image, and fallback chains that obscure the documented path. Keep a short explanation for a common user mistake when it helps them act. A failed required upload must fail the Job.
- **Keep only the output that teaches success.** Print stage progress, the resource/artifact location, and a useful result. Use the library's saved metrics instead of custom report conversion when sufficient. Move extra plots, duplicate CSV/JSON reports, and optional dashboards out of the first run.
- **Keep checks with a concrete purpose.** Preserve authentication, TLS, input limits on HTTP requests, dataset/model compatibility, and protection against overwriting or publishing incomplete checkpoints. Simplify how these checks are written; do not remove them to reach a line count. Use framework validation where it already supplies the needed check.

### Concrete candidates in this repo

These candidates guided the implementation. The links point to the simplified scripts; the descriptions record the rationale for the changes.

| Starting point | Suggested code change | What the customer still learns |
| --- | --- | --- |
| [Train and Serve trainer](../training/train-and-serve/fine_tune.py) and [launcher](../training/train-and-serve/start.sh) | Replace `inspect.signature` branches with direct calls for the pinned Transformers/TRL versions. Make the first run one GPU and one fixed QLoRA recipe with a few inputs; move distributed setup and the optional MLflow callback to examples that teach them. Replace the long configuration banner with short stage messages. | Load data, fine-tune, save an adapter to the mounted output path, and serve it. |
| [LeRobot runner](../robotics/lerobot-finetune-job/train/run.py) | Use one verified LeRobot entry point. Replace Typer/Pydantic configuration wrappers and Rich summary panels with `argparse`, a few explicit checks, and plain progress messages where those dependencies only support this runner. Retain the training library's own configuration and validation. | Change the dataset and training steps, run the upstream trainer, and locate a complete checkpoint. |
| [OpenMM storage](../life-science/openmm-simulation/sim/storage.py) | Remove Python calls to `aws configure` from the boto3 path. Choose mounted output or a direct boto3 upload for the documented run. Remove optional-import flags and nested catches when the image and recipe require upload; report the output location after successful publication. | Understand how simulation results survive the Job's ephemeral disk. |
| [Image classifier](../training/image-classifier-finetuning/src/train.py) | Keep data → processor/model → trainer → evaluation → save as the main path. Use `trainer.save_metrics` for core results; move custom learning-curve joins and per-class CSV/JSON reports into an optional evaluation script. Replace dense transform expressions with readable steps where needed. | Train a classifier, read one evaluation metric, and find the saved model. |
| [SO-101 runner](../robotics/flux-action-so101-pick-orange-task-lora/train_job.py) and [new-embodiment runner](../robotics/flux-action-new-embodiment-full-finetune/train_job.py) | Name intermediate decisions such as checkpoint frequency instead of nesting conditional expressions. Keep upstream training launches and checkpoint publication in explicit stages. Document the purpose of the watcher and checkpoint hook; simplify them only if the upstream trainer can provide the same publication behavior. | Prepare compatible data, train, and publish complete checkpoints/export without losing results on interruption. |

For example, a trainer with pinned dependencies should show one explicit `TrainingArguments(...)` and `SFTTrainer(...)` construction instead of inspecting which keyword names exist at runtime. A required upload should call the upload operation and print its destination after it succeeds, rather than catch any exception and continue as if the task completed.

### How to carry out each refactor

1. Write down the example's required inputs and promised outputs. Trace the README command through the script and identify branches it actually uses.
2. Delete unsupported options, unused helpers, duplicate configuration, and redundant dependencies. Adjust callers and documentation in the same change.
3. Rewrite the remaining main path into clear stages. Keep comments that explain a library requirement or a Serverless behavior; remove comments that merely repeat the code.
4. Run the smallest workload that checks the changed behavior and promised output. For compatibility removal, use the exact pinned image. For storage changes, verify durable output and failure on an unsuccessful required write. State separately whether the edited version was run on Nebius.

## Work in order

### 1. Fix first-run blockers and misleading claims

- In [README.md](../README.md) and [first-job.md](../quickstarts/first-job.md), replace the “30 seconds” result claim with a truthful startup expectation, repair the nonexistent `#setup` link, and use one CLI spelling for Job logs. Both `nebius ai logs` and `nebius ai job logs` work in the installed CLI; the [official quickstart](https://docs.nebius.com/serverless/quickstart/jobs) uses the latter.
- Check the documented `15m` first-Job timeout against the installed CLI and a dry run. The current [Managing Jobs guide](https://docs.nebius.com/serverless/jobs/manage) states a `1h` minimum. Change the example only after that check.
- Make [image-classifier-finetuning](../training/image-classifier-finetuning/README.md) runnable or remove it from the catalog until it is: its README names `.env.template` and `requirements.txt`, and its Makefile installs `requirements.txt`, but neither file is present.
- Replace the project ID embedded in [train-and-serve](../training/train-and-serve/README.md) with a customer-supplied value. Make the public endpoint's authentication choice explicit; prefer the managed HTTPS URL unless a public IP is needed. [Managing Endpoints](https://docs.nebius.com/serverless/endpoints/manage).

### 2. Rewrite three pilot paths

- **First Job:** a one-GPU visibility task: create, capture ID, get state, read `nvidia-smi` output. This becomes the reference for Job examples.
- **vLLM Endpoint:** create with one pinned small model and token authentication, get its URL, make one request, then stop/delete it. This becomes the reference for Endpoint examples.
- **Train and Serve:** show the Job → Object Storage → Endpoint handoff with one artifact path and one inference request. Keep application code limited to the training and serving steps.

For each pilot, remove unused branches and duplicate setup, retain a short explanation of each Nebius-specific argument, and verify the commands against current documentation and a small live run. Record what was actually tested in the README without bundling large run-result directories.

Use Train and Serve as the first code simplification pilot: remove its runtime API detection, reduce its demonstration options, and make the saved adapter path explicit. Review the resulting script alongside its README so both describe the same short path.

### 3. Apply the pattern to the rest of the catalog

Review Jobs, Endpoints, templates, robotics, and life-science examples by customer task, starting with the most visited or easiest to run. Preserve the self-contained files each example needs. For advanced workloads such as FLUX Action or simulation, keep a smoke path first and link the longer evaluation separately. Update [CONTRIBUTING.md](../CONTRIBUTING.md) with the repo purpose and the short example checklist; state any template-specific exception to front matter explicitly.

Apply the code rules above to each example as it is revised. Start with LeRobot's runner and OpenMM's storage wrapper after the pilot, then simplify reporting in the image classifier. Review advanced checkpoint and service code against its actual requirements before changing it.

### 4. Keep examples honest with small checks

- Static: local Markdown links, declared files, front matter where required, shell/Python syntax, and no tenant IDs or raw secrets.
- Local: build or dry-run the changed image/command, then run the smallest meaningful workload check.
- Nebius: require the actual terminal state plus the promised output: a log or HTTP response for simple examples, a durable artifact for Jobs that produce files. Do not call a dry run, build, or finite loss a completed customer task.
- Recheck links and CLI syntax when product docs or images change. Avoid a large test harness; a small checker plus per-example smoke instructions is enough.

## Done when

A new customer can start from the catalog, choose a Job or Endpoint example, fill in only documented values, run the shown commands, recognize success, find the output, and stop any resource that continues billing. Every listed example either meets that bar or is clearly marked as needing repair. Cloud validation status is stated precisely for the version of the example that was run.

The application code follows that same path: required inputs are easy to find, each stage has a clear purpose, dependencies match the pinned image, and errors cannot silently discard a promised result. Compare a refactor by removed branches, options, dependencies, and duplicated steps as well as readability; do not set a target line count.
