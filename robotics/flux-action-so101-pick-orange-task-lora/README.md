---
title: Train a FLUX 3 Action SO-101 Pick Orange task LoRA
category: robotics
type: batch-job
runtime: nebius-ai-jobs
frameworks: [pytorch, lerobot, isaac-sim]
keywords: [robotics, flux-action, so101, lora, benchmark]
difficulty: advanced
---

# Train a FLUX 3 Action SO-101 Pick Orange task LoRA

This **task LoRA** adapts [BFL's prepared SO-101 policy](https://docs.bfl.ai/flux_3/flux3_action_so101) to Pick Orange on the same SO-101 embodiment. It is not the standalone full fine-tuning path for a new robot's controls. A **one-GPU Nebius Job** trains on [LeIsaac Pick Orange](https://huggingface.co/datasets/LightwheelAI/leisaac-pick-orange): 60 demonstrations, 36,293 frames, two cameras, 30 Hz, and a 698 MB source download. The dataset is Apache 2.0; the model uses the [FLUX Kommunity License](https://huggingface.co/black-forest-labs/flux-3-action-so101). For the full-weight path, see the [new-embodiment cookbook](../flux-action-new-embodiment-full-finetune/README.md).

The separate closed-loop evaluation runs the base and adapted policy on the same 25 Isaac Sim seeds. [A published ACT policy on this dataset placed 33/75 oranges](https://huggingface.co/wsagi/ACT-PickOrange). That result is context for task difficulty, **not a published FLUX score or an identical-seed comparison**. The recipe reports actual FLUX placements, full task completions, paired improvement, and rollout videos.

## Calibration used by this revision

LeIsaac stores five arm channels in its motor range, while the released FLUX
SO-101 checkpoint uses a different joint frame. The recipe now composes
[LeIsaac's pinned motor-to-USD conversion](https://github.com/LightwheelAI/leisaac/blob/24d3bcd/source/leisaac/leisaac/utils/robot_utils.py)
and [the FLUX SO-101 simulation's physical-angle-to-model mapping](https://huggingface.co/spaces/multimodalart/flux-3-action-so101-sim/blob/73899a12fafef320c10345602be5ebc794dcf382/sim.py).
It applies the resulting transform to both demonstration states and absolute
actions before v3 conversion, and reverses it between LeIsaac and the policy
service during evaluation. The gripper remains in percentage points. The
checkpoint's saved processors and normalization statistics stay fixed. Each
published checkpoint records the calibration ID; the service rejects an
adapter made before this change.

Before training, `calibration-report.json` records the fraction of source
frames outside each checkpoint state q01–q99 range. The job stops if a joint
has no overlap. Passing that check does not establish model quality; inspect
the per-joint fractions and run the paired benchmark.

This geometric mapping comes from a separate Hugging Face SO-101 simulation.
It is a source-backed candidate for LeIsaac, **not yet a validated Pick Orange
calibration or a quality result**. The demonstrations still cover poses outside
the checkpoint's usual state range, and the simulator reset pose differs from
recorded starts. Verify the mapped arm pose and closed-loop behavior before
interpreting a new fine-tune as successful.

A [calibrated step-100 cloud smoke](e2e-results/README.md) completed on Nebius
RTX with one paired Pick Orange seed. Base and adapter each placed 0/3 oranges
in a full 7,200-step episode. This validates the inference path and leaves
calibration quality and the 25-seed gate unresolved.

## Previous uncalibrated end-to-end run (October 1, 2026)

The prior Nebius H100 job completed 10,000 microsteps and 2,500 optimizer updates in 8,715.5 training seconds. It used LeIsaac motor values directly, without the calibration above, and covered about 0.67 training epoch. Its [completion marker](e2e-results/TRAIN_COMPLETE.json) records the dataset revision, checkpoint paths, and adapter hashes. The closed-loop evaluation used seeds 42000–42024, 120 simulator seconds per seed, one 60 Hz physics step per action, and a 30 Hz paced policy loop.

| Policy | Oranges placed | Full task successes | Paired improvement over base, 95% bootstrap interval |
| --- | ---: | ---: | ---: |
| Released SO-101 base | 0/75 | 0/25 | — |
| Step 10,000 raw LoRA | 2/75 | 0/25 | +2 [0, 5] |
| Step 10,000 EMA LoRA | 9/75 | 0/25 | +9 [3, 17] |

The complete [base](e2e-results/base.json), [raw adapter](e2e-results/adapter-raw.json), and [EMA adapter](e2e-results/adapter-ema.json) reports and their [raw](e2e-results/quality-raw.json) and [EMA](e2e-results/quality-ema.json) paired summaries are included. EMA placed more oranges, but **neither adapter passed the recipe's 25/75 quality gate**. These artifacts are historical and must not be mixed with results from the calibrated recipe. Orange counts record whether each orange reached the plate at any point in an episode; full task success requires the simulator's terminal success condition. The ACT 33/75 figure comes from a different policy and evaluation runs.

## What runs where

| Stage | Machine | Output |
| --- | --- | --- |
| Dataset download, v2.1→v3 conversion, SO-101 checks, LoRA | One Nebius H100 Job | Dataset report, logs, raw/EMA checkpoints in Object Storage; optional W&B training charts |
| Base and adapter rollouts | Isaac Sim 5.1 machine with an RTX GPU; FLUX service in the same Docker image | 25 episodes per policy, videos, JSON reports |
| Comparison | Any Python 3 machine | Paired quality report |

The dataset is small, but the 7B policy and shared encoders add many GB of model downloads. Run the 100-microstep smoke first and use its **measured** duration to estimate the full job. The full job uses BFL's one-GPU preset: batch 2, accumulation 4, rank/alpha 32 LoRA, BF16, and EMA. Its default 10,000 microsteps give 2,500 optimizer updates; set `FULL_STEPS` to a multiple of 5,000 for a longer run. The preset holds out the last 20% of episodes for one final offline validation pass; the smoke skips that expensive pass. All code and revision pins needed for the job are in this directory.

## 1. Configure and build

You need Nebius CLI, Docker, AWS CLI credentials for Nebius Object Storage, a project/subnet/bucket/registry in one region, and access to the [SO-101 weights](https://huggingface.co/black-forest-labs/flux-3-action-so101). Work from this directory:

If your Hugging Face account requires a token for the model, put it in a Nebius MysteryBox secret and set `NEBIUS_HF_TOKEN_SECRET` to that secret's selector before running `job.sh`. The job passes it as `HF_TOKEN` through `--env-secret`. For local evaluation, export `HF_TOKEN` on the RTX host; Docker passes it into the policy container without baking it into the image.

To track training in Weights & Biases, create a Nebius MysteryBox secret for
your W&B API key and set `WANDB_API_KEY` to that secret's **selector** before
submitting either job (do not put the raw key in this shell variable):

```bash
export WANDB_API_KEY=YOUR_SECRET_SELECTOR
export WANDB_PROJECT=flux-so101-orange
```

Set `WANDB_ENTITY` as well if the project belongs to a team. The job passes
the key through `--env-secret`, names the W&B run after `RUN_NAME`, and enables
LeRobot's built-in training metrics every 20 microsteps. The full job also
logs its held-out evaluation loss at the final evaluation step. Look for
`Track this run -->` in the Nebius job logs to open the live W&B run. Model
checkpoints remain in Object Storage; duplicate W&B artifact uploads are
disabled. Without the secret selector, training runs with local logs only.

```bash
export NEBIUS_PROFILE=YOUR_PROFILE
export NEBIUS_PROJECT_ID=YOUR_PROJECT_ID
export NEBIUS_SUBNET_ID=YOUR_SUBNET_ID
export NEBIUS_BUCKET=YOUR_BUCKET_NAME
export NEBIUS_BUCKET_ID=YOUR_STORAGEBUCKET_ID
export NEBIUS_REGISTRY_ID=YOUR_REGISTRY_ID
export NEBIUS_REGION=YOUR_REGION
export NEBIUS_GPU_PLATFORM=gpu-h200-sxm
export NEBIUS_S3_ENDPOINT="https://storage.$NEBIUS_REGION.nebius.cloud"
export AWS_PROFILE=YOUR_OBJECT_STORAGE_PROFILE
export NEBIUS_IMAGE="cr.$NEBIUS_REGION.nebius.cloud/${NEBIUS_REGISTRY_ID#registry-}/flux-so101-orange:$(date -u +%Y%m%dT%H%M%SZ)"
docker build --platform linux/amd64 -t "$NEBIUS_IMAGE" .
docker push "$NEBIUS_IMAGE"
```

Use the same image for training and evaluation. The image pins LeRobot and its dependency lockfile. The job downloads pinned BFL model revisions at runtime; it does not upload datasets or weights to Hugging Face.

## 2. Measure a smoke job

```bash
export RUN_NAME="flux-orange-smoke-$(date -u +%Y%m%dT%H%M%SZ)"
bash job.sh smoke show
bash job.sh smoke dry-run
bash job.sh smoke submit
```

Record the returned job ID. Wait for Nebius state `COMPLETED`, inspect its logs, and check the durable marker:

```bash
nebius ai job get SMOKE_JOB_ID --profile "$NEBIUS_PROFILE"
nebius ai job logs SMOKE_JOB_ID --profile "$NEBIUS_PROFILE" --tail 50
aws s3 cp "s3://$NEBIUS_BUCKET/runs/$RUN_NAME/TRAIN_COMPLETE.json" - \
  --endpoint-url "$NEBIUS_S3_ENDPOINT"
```

The marker must say `status: trained`, `microsteps: 100`, and contain a verified step-100 adapter SHA-256 and the calibration ID. LeRobot zero-pads checkpoint directories, so step 100 is `checkpoints/000100/`. `train_seconds` measures trainer time after downloads and conversion; include those earlier log timestamps when estimating total job time. Inspect `dataset.json`, `calibration-report.json`, and `camera-preview.jpg` in the same run prefix before the full job.

## 3. Train the full adapter

```bash
export FULL_STEPS=60000  # about four dataset passes; 15,000 optimizer updates
export NEBIUS_PREEMPTIBLE=1  # optional; the GPU can be interrupted
export RUN_NAME="flux-orange-full-$(date -u +%Y%m%dT%H%M%SZ)"
bash job.sh full dry-run
bash job.sh full submit
nebius ai job get FULL_JOB_ID --profile "$NEBIUS_PROFILE"
nebius ai job logs FULL_JOB_ID --profile "$NEBIUS_PROFILE" --tail 50
aws s3 cp "s3://$NEBIUS_BUCKET/runs/$RUN_NAME/TRAIN_COMPLETE.json" - \
  --endpoint-url "$NEBIUS_S3_ENDPOINT"
```

Require both terminal `COMPLETED` and `TRAIN_COMPLETE.json` with the requested `microsteps`. The job checks source metadata, transforms demonstration states, actions, and episode statistics into the model frame, converts locally with LeRobot's converter, verifies 30 Hz/six-joint/two-camera input, and refuses a reused run name. It trains on local disk, publishes complete checkpoints to Object Storage, and writes each `COMPLETE.json` **after** copying and hashing its adapter and recording the calibration ID. The `pretrained_model` and `pretrained_model_ema` directories are retained. Runs longer than 10,000 steps save every 5,000 steps to limit disk use; use the marker's `selected_checkpoint` field as the authoritative final path. `TRAIN_COMPLETE.json` proves training and publication; policy quality remains pending until evaluation.

With `NEBIUS_PREEMPTIBLE=1`, Nebius may interrupt the job at any time. Complete 5,000-step checkpoints remain in Object Storage, but this recipe does not automatically resume training after preemption. The job uses `restart-policy=never` so a restart cannot collide with its existing run prefix.

## 4. Set up closed-loop evaluation

Use a Linux host with an RTX GPU and Docker GPU access. Isaac Sim requires RT cores; H100 is unsuitable for this stage. The RTX GPU must have room for both Isaac Sim and the FLUX service. If they do not fit together, run the service on another NVIDIA GPU host, use an authenticated HTTPS endpoint that the simulator host can reach, and pass its URL with `evaluate.py --endpoint`. Set `SERVICE_TOKEN_FILE` to its bearer token file and, for a private certificate, `SERVICE_TLS_CERT_FILE` to the trusted certificate path. Follow [LeIsaac's Isaac Sim 5.1 installation and kitchen-asset instructions](https://lightwheelai.github.io/leisaac/docs/getting_started/installation/). Keep its PyTorch 2.7 environment separate from the training image's PyTorch 2.11 environment. Pin the LeIsaac checkout:

If Isaac Sim runs in a CUDA Ubuntu container, expose NVIDIA graphics libraries (`NVIDIA_DRIVER_CAPABILITIES=all`) and install `libegl1 libglx0 libopengl0 libglu1-mesa libxt6 libvulkan1`. Check that `vulkaninfo --summary` lists the RTX GPU before launching Isaac Sim.

```bash
git clone --recursive https://github.com/LightwheelAI/leisaac.git
cd leisaac
git checkout --detach 24d3bcd
git submodule update --init --recursive
# Follow the linked installation guide for Isaac Sim 5.1, IsaacLab, LeIsaac,
# and the Kitchen with Orange assets before running the evaluator.
```

Copy this cookbook directory to the evaluation host and set absolute paths to it and to a working directory. Download the published checkpoint, including `COMPLETE.json`:

```bash
export RECIPE_DIR=/ABSOLUTE/PATH/TO/flux-action-so101-pick-orange-task-lora
export EVAL_DIR="$RECIPE_DIR/eval"
mkdir -p "$EVAL_DIR/checkpoint" "$EVAL_DIR/model-cache" "$EVAL_DIR/hf-cache"
export CHECKPOINT_STEP=$(printf '%06d' "${FULL_STEPS:-10000}")
aws s3 cp "s3://$NEBIUS_BUCKET/runs/$RUN_NAME/checkpoints/$CHECKPOINT_STEP/" \
  "$EVAL_DIR/checkpoint/" --recursive --endpoint-url "$NEBIUS_S3_ENDPOINT"
```

Run the synchronous policy service in one terminal. For the **base** run:

```bash
docker run --rm --gpus all --ipc host -p 127.0.0.1:8765:8765 \
  -e HF_TOKEN \
  -e MODEL_VARIANT=base \
  -v "$EVAL_DIR/model-cache:/workspace/work/models" \
  -v "$EVAL_DIR/hf-cache:/workspace/cache" \
  "$NEBIUS_IMAGE" python3 /app/recipe/policy_service.py
```

In another terminal, activate the LeIsaac/Isaac Sim environment, work from the pinned LeIsaac checkout, and run:

```bash
python "$RECIPE_DIR/evaluate.py" --model base \
  --output "$EVAL_DIR/base.json" --episodes 25 --seed 42000 \
  --episode_length_s 120 --device cuda --enable_cameras --headless
```

Stop the base service. Start the **adapter** service with the same image, GPU, and cached base weights:

```bash
docker run --rm --gpus all --ipc host -p 127.0.0.1:8765:8765 \
  -e HF_TOKEN \
  -e MODEL_VARIANT=adapter \
  -e CHECKPOINT_DIR=/workspace/checkpoint/pretrained_model \
  -v "$EVAL_DIR/checkpoint:/workspace/checkpoint:ro" \
  -v "$EVAL_DIR/model-cache:/workspace/work/models" \
  -v "$EVAL_DIR/hf-cache:/workspace/cache" \
  "$NEBIUS_IMAGE" python3 /app/recipe/policy_service.py
```

Then run the same evaluation with `--model adapter --output "$EVAL_DIR/adapter.json"`. The service verifies the adapter against its published SHA-256, uses the checkpoint's saved pre/postprocessors every control tick, and resets history between episodes. The evaluator uses LeIsaac's SO-101 unit conversion and per-orange placement predicate. It writes progress after every episode and saves front-camera videos for the first three episodes of each policy. To compare EMA, run the adapter service again with `CHECKPOINT_DIR=/workspace/checkpoint/pretrained_model_ema` and use a separate evaluation output. The training marker's `selected_checkpoint` points to the raw checkpoint; it does not claim that raw is the better policy. In the measured run above, EMA scored higher.

Each episode seeds LeIsaac before constructing the environment, warms the scene for 30 control steps while holding the reset pose, then runs up to 120 simulator seconds (7,200 policy actions). It keeps LeIsaac's default one 60 Hz physics step per action and paces policy actions at 30 Hz, matching [LeIsaac's evaluation loop](https://github.com/LightwheelAI/leisaac/blob/24d3bcd/scripts/evaluation/policy_inference.py). It checks placement before each step because LeIsaac resets the scene immediately after a terminal step.

The evaluator starts a fresh Isaac Sim process for each seed and merges the completed episode reports into `base.json` or `adapter.json`. This also makes a simulator exit during reset visible as an incomplete report. Allow for simulator startup time on every episode.

## 5. Compare results

```bash
python3 "$RECIPE_DIR/summarize.py" "$EVAL_DIR/base.json" "$EVAL_DIR/adapter.json" \
  "$EVAL_DIR/quality.json"
```

`quality.json` requires 25 matching seeds per policy. It reports oranges placed out of 75, full task successes, and a paired episode bootstrap interval. The recipe's quality gate is **at least 25/75 placements**, **at least 10 more placements than the released SO-101 checkpoint**, and a paired interval above zero. The published ACT 33/75 result is included as context; its policy and seeds differ. If the gate fails, the cookbook still has a trained adapter, but it has **not** shown the intended model quality. No FLUX quality result is claimed until these rollouts run.
