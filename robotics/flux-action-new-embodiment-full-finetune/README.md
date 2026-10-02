---
title: Full fine-tune FLUX 3 Action for a new robot embodiment
category: robotics
type: batch-job
runtime: nebius-ai-jobs
frameworks: [pytorch, lerobot]
keywords: [robotics, flux-action, full-finetune, new-embodiment, aloha]
difficulty: advanced
---

# Full fine-tune FLUX 3 Action for a new robot embodiment

This recipe starts from BFL's **action-pretrained FLUX 3 Action base** and trains the model weights and a new 14-channel ALOHA action head with the [standalone full fine-tuning trainer](https://docs.bfl.ai/flux_3/flux3_action_finetuning). It defaults to eight GPUs in one Nebius Job and also supports a one GPU memory saving configuration. It does **not** load the prepared SO-101 policy or train a LoRA. For a task adapter on an existing SO-101 policy, use the [SO-101 Pick Orange task LoRA](../flux-action-so101-pick-orange-task-lora/README.md).

The concrete example is [LeRobot's MIT-licensed ALOHA Static Cups Open dataset](https://huggingface.co/datasets/lerobot/aloha_static_cups_open) at the commit in [`recipe.json`](recipe.json): 50 episodes, 20,000 frames, 50 Hz, 14 measured-state values, 14 commanded-action values, and three selected cameras. Its size makes it useful for exercising a new embodiment's data and training path. It does not establish a good ALOHA policy. The recipe's output is a full checkpoint and BF16 inference export; robot task success requires a separate closed-loop evaluation.

## Embodiment contract

The indexer reads a pinned LeRobot v2 or v3 dataset. [`recipe.json`](recipe.json) fixes the dataset revision, robot type, ordered state and action channels, camera features, FPS, and held-out episodes. [`train.json`](train.json) fixes the new policy's action modality and dimension, grid camera layout, 32-action horizon, 50 Hz timing, and training schedule. The example treats recorded actions as **absolute** commands and keeps both grippers in their recorded convention. Confirm those semantics before robot rollout.

For a different robot, update **both files** before building the image. Confirm state and action channel order and units, what the action column commands, gripper sign/range, camera identity and order, frame/action timing, and episode alignment from real recordings. Choose `absolute` or `joint_delta` deliberately. If using deltas, list channels that must remain absolute in `absolute_action_dims`. Set an explicit evaluation split and define how exported actions are converted back into your robot's commands. Matching the vector width alone is insufficient. The preparation stage rejects metadata or policy settings that disagree with the contract.

The [BFL full fine-tuning guide](https://docs.bfl.ai/flux_3/flux3_action_finetuning) explains the difference from the [SO-101 LeRobot task LoRA](https://docs.bfl.ai/flux_3/flux3_action_so101). The image pins the standalone `black-forest-labs/flux-action` source and lockfile; the base model and encoder references use BFL's pinned model revision. The dataset and base weights are downloaded at job runtime; checkpoints are published to Object Storage. Access to the [base model](https://huggingface.co/black-forest-labs/flux-3-action-base) is required. The model is subject to its own license.

## 1. Configure and build

Work from this directory. Set your Nebius project, bucket, and registry in the **same region**. `NEBIUS_BUCKET_ID` is the full `storagebucket-...` ID; the registry path uses the registry ID without `registry-`.

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
export NEBIUS_IMAGE="cr.$NEBIUS_REGION.nebius.cloud/${NEBIUS_REGISTRY_ID#registry-}/flux-action-full:$(date -u +%Y%m%dT%H%M%SZ)"
docker build --platform linux/amd64 -t "$NEBIUS_IMAGE" .
docker push "$NEBIUS_IMAGE"
```

The example defaults to eight H200 GPUs. The helper also maps H100, B200, or RTX 6000 GPUs if available; measure memory on the intended hardware with the smoke job. RTX 6000 has less GPU memory than H200 or B200, so a successful dry run alone does not establish that full training fits. Full-weight training stores model weights, gradients, optimizer state, and checkpoints, so inference memory is not a training estimate. The default uses one window per GPU and two accumulation rounds: **global batch 16**, BF16 compute with FP32 parameters, and no EMA. This deliberately differs from BFL's larger reference batches. If eight GPU capacity is unavailable, set `NEBIUS_GPU_COUNT=1` before submitting. This uses BF16 parameters and global batch 2; train a fresh run because its optimization and memory behavior differ from the eight GPU run. Confirm memory with a smoke before the full schedule. Set `NEBIUS_HF_TOKEN_SECRET` to a Nebius MysteryBox selector if the dataset or model needs Hugging Face authentication; the helper passes it as `HF_TOKEN` without putting the value in the image.

## 2. Run a four-update smoke

```bash
export RUN_NAME="flux-aloha-smoke-$(date -u +%Y%m%dT%H%M%SZ)"
bash job.sh smoke show
bash job.sh smoke dry-run
bash job.sh smoke submit
```

Record the returned job ID. The job downloads the pinned dataset, verifies the ALOHA contract, indexes its windows and normalization statistics, starts the selected number of `torchrun` ranks, trains four optimizer updates with a short warmup, then exports the raw model. Check the terminal job state and durable objects:

```bash
nebius ai job get SMOKE_JOB_ID --profile "$NEBIUS_PROFILE"
nebius ai job logs SMOKE_JOB_ID --profile "$NEBIUS_PROFILE" --tail 80
aws s3 cp "s3://$NEBIUS_BUCKET/runs/$RUN_NAME/PREPARED.json" - \
  --endpoint-url "$NEBIUS_S3_ENDPOINT"
aws s3 cp "s3://$NEBIUS_BUCKET/runs/$RUN_NAME/TRAIN_COMPLETE.json" - \
  --endpoint-url "$NEBIUS_S3_ENDPOINT"
```

Require terminal `COMPLETED`, `checkpoints/step-4/COMPLETE`, `export/model.safetensors`, and `TRAIN_COMPLETE.json` with `optimizer_updates: 4`. Download `metrics.jsonl` from the same run prefix and check finite losses, nonzero trunk/head learning rates, and measured peak GPU memory. The preparation record and index describe the actual selected episodes, channels, and normalization. Inspect representative camera frames, states, and actions before a long job. A successful smoke proves the pipeline ran; it does not prove policy quality. The [October 2 Nebius smoke evidence](e2e-results/README.md) records a completed one-H200 four-update run and its published export.

Reload that export in a separate one-GPU Job. This checks the published weight hash, rebuilds the pinned dataset index, and scores 20 windows from the five reserved episodes:

```bash
export CHECK_NAME="smoke-check-$(date -u +%Y%m%dT%H%M%SZ)"
bash job.sh check dry-run
bash job.sh check submit
nebius ai job get CHECK_JOB_ID --profile "$NEBIUS_PROFILE"
nebius ai job logs CHECK_JOB_ID --profile "$NEBIUS_PROFILE" --tail 80
aws s3 cp "s3://$NEBIUS_BUCKET/runs/$RUN_NAME/checks/$CHECK_NAME/COMPLETE.json" - \
  --endpoint-url "$NEBIUS_S3_ENDPOINT"
```

Require terminal `COMPLETED`, `offline-val.json`, and `COMPLETE.json` with finite action errors and the same export hash. Use a fresh `CHECK_NAME` for each check.

If no GPU is available, set `NEBIUS_GPU_PLATFORM=cpu-d3` and a fresh
`CHECK_NAME`, then run `bash job.sh check dry-run` and `bash job.sh check submit`.
This uses 32 vCPUs and scores one reserved window. It checks export integrity,
reload, and inference; use the GPU job above for the 20-window score. The
[October 2 evidence](e2e-results/README.md) includes a completed one-window CPU
check after a one-H200 training smoke.

## 3. Run full training

The included schedule is 3,000 **optimizer updates**. The trunk is frozen for the first 200 updates, then warms for 600; this differs from the SO-101 LoRA microstep count. Checkpoint publication follows every 500 updates. Each published step has a `COMPLETE` marker written after its files; a failed job may retain earlier complete steps, but this recipe starts a fresh run name and does not automatically resume them.

```bash
export RUN_NAME="flux-aloha-full-$(date -u +%Y%m%dT%H%M%SZ)"
bash job.sh full show
bash job.sh full dry-run
bash job.sh full submit
nebius ai job get FULL_JOB_ID --profile "$NEBIUS_PROFILE"
nebius ai job logs FULL_JOB_ID --profile "$NEBIUS_PROFILE" --tail 80
aws s3 cp "s3://$NEBIUS_BUCKET/runs/$RUN_NAME/TRAIN_COMPLETE.json" - \
  --endpoint-url "$NEBIUS_S3_ENDPOINT"
```

The final receipt records the selected checkpoint and the SHA-256 of the BF16 export. Download it with the export and verify the hash:

```bash
mkdir -p "$RUN_NAME/export"
aws s3 cp "s3://$NEBIUS_BUCKET/runs/$RUN_NAME/export/" "$RUN_NAME/export/" \
  --recursive --endpoint-url "$NEBIUS_S3_ENDPOINT"
aws s3 cp "s3://$NEBIUS_BUCKET/runs/$RUN_NAME/TRAIN_COMPLETE.json" \
  "$RUN_NAME/TRAIN_COMPLETE.json" --endpoint-url "$NEBIUS_S3_ENDPOINT"
sha256sum "$RUN_NAME/export/model.safetensors"
```

Compare that checksum with `export_model_sha256`. Keep the base model's VAE and text encoder available at inference: the export records their pinned references, but does not duplicate those weights. `TRAIN_COMPLETE.json` proves training and publication, not successful manipulation.

Run `bash job.sh check dry-run` and `bash job.sh check submit` again with a fresh `CHECK_NAME` while `RUN_NAME` points to the full run. Check its terminal state and `checks/$CHECK_NAME/COMPLETE.json` as above.

## 4. Evaluate the policy

The index reserves five episodes for offline comparison. The indexer's normalization statistics include all indexed episodes, so this split is useful for diagnostics but is **not a strict unseen-data benchmark**. For policy selection, use an external held-out dataset and run BFL's `flux-action evaluate` on the same windows for candidate checkpoints. For robot quality, compare against an appropriate baseline on the same ALOHA tasks, initial states, control settings, and success criteria. ALOHA deployment also needs verified action units, calibration, both arm mappings, and camera placement. No ALOHA success rate is claimed here.
