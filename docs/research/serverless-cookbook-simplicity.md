# Research: small, useful Serverless AI examples

Checked 2026-10-05 against Nebius documentation and first party documentation guides. This is source material for a repo simplification plan, not a new example.

The repo observations below describe the source before the simplification change.

## Customer path to teach

1. **Choose the resource by task.** Nebius describes Jobs as finite training, preprocessing, batch inference, evaluation, or simulation workloads, and Endpoints as request-serving workloads. Each example should choose one as its main path and explain that choice in one sentence. [Nebius overview](https://docs.nebius.com/serverless/overview)
2. **Show one copyable first run.** The official Job quickstart creates an image-backed `nvidia-smi` Job with a platform, matching preset, and timeout, then gets the Job ID, checks status, and reads logs. The official Endpoint quickstart creates an `nginx` Endpoint, gets its managed HTTPS URL, and verifies an HTTP response. These are better models for a demo than an orchestration framework. [Job quickstart](https://docs.nebius.com/serverless/quickstart/jobs) · [Endpoint quickstart](https://docs.nebius.com/serverless/quickstart/endpoints)
3. **Name the output and its location.** A Job's container disk disappears when the Job finishes. For durable outputs such as model adapters and checkpoints, Nebius mounts Object Storage; the official Axolotl tutorial demonstrates the input config and output weights in one bucket. A README should say exactly which log line, response, or bucket object proves completion. [Nebius overview](https://docs.nebius.com/serverless/overview) · [Axolotl tutorial](https://docs.nebius.com/serverless/tutorials/fine-tuning) · [Managing Jobs](https://docs.nebius.com/serverless/jobs/manage)
4. **Keep the security and cost boundary visible without building a framework.** Nebius supports `--env-secret` for stored secrets and `--volume` for a durable bucket. Endpoint auth defaults to none for prototypes; `--auth token` enables bearer auth. A public IP (`--public`) is not required to call the managed HTTPS URL. Running Jobs and Endpoints bill for compute and storage, and mounted storage is billed separately; stop or delete an Endpoint after the demo. [Managing Jobs](https://docs.nebius.com/serverless/jobs/manage) · [Managing Endpoints](https://docs.nebius.com/serverless/endpoints/manage) · [Nebius overview](https://docs.nebius.com/serverless/overview)

## Documentation pattern

Google's [developer procedure guide](https://developers.google.com/style/procedures) advises one main procedure, the shortest accessible route, few interruptions, and action → command → placeholders → output. Its [sample guide](https://googlecloudplatform.github.io/samples-style-guide/) values copyable, runnable code that teaches why the service feature is used. Diátaxis distinguishes a guided learning tutorial from a goal-oriented how-to and advises against creating empty documentation structures. Applied here: make each README a task-first, numbered run with prerequisites, expected result, one adaptation point, and a short troubleshooting note; link deeper reference material instead of duplicating it. [Diátaxis](https://diataxis.fr/) · [Applying Diátaxis](https://www.diataxis.fr/how-to-use-diataxis/)

## Repo-specific observations to verify in the plan

- [CONTRIBUTING.md](../../CONTRIBUTING.md) already asks for self-contained, concise, runnable examples with clear input/output, compute, expected output, adaptation, and troubleshooting. Improve examples against that rule rather than introducing a heavy new template.
- [First Job](../../quickstarts/first-job.md) links to `README.md#prerequisites`, but the root README's heading is `Prerequisites`. It also uses `nebius ai logs`; the current official Job quickstart prints `nebius ai job logs`. Both forms work in the installed CLI (`--help` succeeded for each), so this is a consistency issue, not a broken command. [Job quickstart](https://docs.nebius.com/serverless/quickstart/jobs)
- [Train and Serve](../../training/train-and-serve/README.md) hardcodes a project ID. Replace it with a required user-supplied value or configured profile. Its unauthenticated endpoint is documented as acceptable for a prototype, but the README should say that plainly and give the token-auth command if users will expose real data. Its `--public` flag is unnecessary for the managed HTTPS route. [Managing Endpoints](https://docs.nebius.com/serverless/endpoints/manage)
- The root [README](../../README.md) advertises a 30-second quickstart, while Nebius says a Job can take several minutes to complete. Distinguish copy/paste setup time from time to observe the result. [Job quickstart](https://docs.nebius.com/serverless/quickstart/jobs)
- Nebius's current [Managing Jobs](https://docs.nebius.com/serverless/jobs/manage) page states a minimum Job timeout of `1h`; the root README and First Job example show `15m`. Verify against the installed CLI and a dry run before changing the examples.

Research only: no cloud execution or cookbook changes were performed.
