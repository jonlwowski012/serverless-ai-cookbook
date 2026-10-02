# Nebius cloud validation, October 2, 2026

The one-H200 smoke Job `aijob-u00zq9r3tdnya9wj6z` reached provider state
`COMPLETED`. Its durable run prefix is
`s3://flux-action-droid-cookbook-us-20260930-1800/runs/flux-aloha-h200-onegpu-smoke-20261002T1620Z/`
in us-central1. The Job used the pinned ALOHA dataset revision
`d793c969cf716001dcca18a0842c3d7e9de9e41b` and base revision
`62878e2925e59b7a89ec14463ce89932624c490d`.

`PREPARED.json` records 50 eligible episodes, 45 train and five reserved
validation episodes, 18,350 valid window starts, and zero rejected rows. The
published `train.json` records one GPU, BF16 parameters, global batch two, and
four optimizer updates. All four losses were finite (2.0514, 1.9367, 2.0054,
1.5764); peak reported GPU memory was 68.6 GB.

Object Storage contains `checkpoints/step-4/COMPLETE`, its model and optimizer
shards, `metrics.jsonl`, a 13,894,319,672-byte `export/model.safetensors`, and
`TRAIN_COMPLETE.json`. The export manifest and training receipt agree on model
SHA-256 `ffa05a2137b696746f16526704dfd55a224b46aee0aca4f4a3085904012b0a2f`.
The exported policy config has a 14-value ALOHA action head, three ordered
cameras, 50 Hz timing, and absolute actions.

The separate CPU Job `aijob-u00vfd9eq2fvgj2jf8` reached `COMPLETED`. It copied
and re-hashed the published export, rebuilt the pinned dataset index, reloaded
the policy, and inferred one reserved validation window. Its
[completion receipt](check-complete.json) has the same model SHA-256, normalized
action MSE `0.7700108289718628`, and raw action MSE
`0.17172571922752208`. The [full one-window report](offline-val-one-window.json)
is retained. This closes the technical smoke path from preparation through
full-weight training, publication, and reloaded inference in Nebius Cloud.
The live CPU Job injected a one-window variant of `check_export.py`; the
equivalent `cpu-d3` option is now in `job.sh` and `check_export.py`.

One CPU window is a functional check. It is not a policy quality benchmark;
the 20-window GPU score, 3,000-update schedule, and robot task success remain
unverified.

## Long-run checkpoint progress

The one-H200 3,000-update Job `aijob-u00kkydywtsxkrmxsy` uses run prefix
`s3://flux-action-droid-cookbook-us-20260930-1800/runs/flux-aloha-h200-onegpu-full-20261002T1715Z/`.
It prepared the same pinned 50-episode dataset, trained through trunk unfreeze
at step 200, and wrote its first scheduled checkpoint at step 500. Object
Storage contains `checkpoints/step-500/COMPLETE`, the 13,894,976,571-byte model
shard, and the 27,638,354,199-byte optimizer shard. The Job subsequently
published steps 1,000, 1,500, 2,000, and 2,500, with finite losses and
68.6 GB reported peak GPU memory. The step-2,500 completion marker was
verified in Object Storage. This is a
progress record, not a terminal result; require Job `COMPLETED`, a step-3000
checkpoint, final export, and an independent check before calling the long
schedule complete.

## Standalone image build

The cookbook Dockerfile built locally as
`flux-action-aloha-cookbook:selfcontained-20261002` (linux/amd64). A container
check confirmed BFL source commit
`e2dd1d8dbc5977b54315d61f7548c63c043d6d4f`, PyTorch `2.10.0+cu128`,
`natten` `0.21.6`, and matching SHA-256 hashes for the five copied cookbook
files. Python compilation inside the image passed. This local build check is
separate from the Nebius Jobs above, which used a thin overlay on the same
pinned source and dependency environment.
