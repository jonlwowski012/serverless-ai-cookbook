# Validation of the cookbook simplification

Checked October 5, 2026. This records the evidence for this change; it does not claim that every workload in the catalog was rerun.

| Example | Check and result |
| --- | --- |
| First Job | Live L40S Job completed and returned the NVIDIA GPU table. |
| First Endpoint | Commands checked against the installed CLI and official documentation; nginx was not deployed in this change. |
| vLLM Qwen Endpoint | Live L40S Endpoint listed the model and returned a chat response over managed HTTPS. A request without the token returned HTTP 401. Test Endpoint deleted. |
| Train and Serve | Live training exposed a direct-to-bucket serialization failure. Fixed by saving locally, copying the finished adapter, and writing `COMPLETE` last. The corrected 32-example L40S training run completed and published its adapter. A vLLM Endpoint listed `tinyllama_adapter` and returned a completion using it over HTTPS; an unauthenticated request returned HTTP 401. A separate Job read back the adapter weights and completion marker. Test Endpoint deleted. |
| Image classifier | Live one-epoch L40S Job completed, saved model weights and test metrics, and copied them to the bucket. A separate Job verified the saved weights and completion marker and read back test accuracy `0.71875`. This demonstrates execution, not a benchmark claim. |
| LeRobot | CLI and upload wrapper simplified. Upload success/failure checks and Dockerfile checks passed. The new image built, both CLI entry points loaded, and one actual ACT/PushT CPU training update produced a checkpoint that the simplified evaluation command loaded successfully. GPU training and a real S3 transfer were not rerun. |
| OpenMM | Real OpenMM 8.4 CPU run completed 20 steps using bundled `1UBQ`, producing a nonempty trajectory and metadata. Upload failure checks and Dockerfile checks passed. CUDA and real S3 upload were not rerun. |
| FLUX Action cookbooks | Checkpoint scheduling made explicit; publication behavior retained. SO-101 unit suite: eight passed, one skipped because optional parquet/safetensors readers were absent. No new GPU training or policy evaluation run. |
| NIM, Axolotl, OpenClaw, BioNeMo, Parabricks, SmolVLA, FLUX.2 and Console templates | Source/link/syntax checks only in this change. Existing workload-specific validation notes still apply; these workloads were not launched. |

Run the lightweight checks with Python 3.11 or newer:

```bash
python3 scripts/check_examples.py
python3 -m unittest discover -s tests -v  # needs boto3
```

The checker validates local Markdown/HTML file links, required example front matter, Python/shell syntax, and JSON/TOML syntax. It does not check external URLs, Markdown anchors, model quality, or cloud availability. Tests verify that required upload failures propagate and incomplete copies do not receive completion markers.

The installed CLI advertises a one-hour minimum timeout; its dry run also accepted `15m`. The first-Job examples use `1h` to match current documentation. A Job releases compute when its command finishes rather than waiting for its timeout.

Cloud staging for the training checks used a small bootstrap to copy the same example files into the temporary bucket; this validation shell did not have Object Storage access keys. It therefore does not validate the README's host-side `aws s3 cp/sync` steps.

All temporary Endpoints, Job records, and the validation bucket were deleted after these checks. Endpoint and bucket lookups confirmed they no longer existed. No test images were pushed to a registry.
