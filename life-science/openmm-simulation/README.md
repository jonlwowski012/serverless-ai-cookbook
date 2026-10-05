---
title: OpenMM Serverless Molecular Dynamics with Nebius AI Jobs
category: life-sciences
type: batch-job
runtime: nebius-ai-jobs
frameworks: [openmm, python]
keywords: [molecular-simulation, serverless-jobs, s3, cuda]
difficulty: intermediate
---

# Run an OpenMM simulation in a GPU Job

Run a short molecular dynamics simulation of ubiquitin (`1UBQ`) on a GPU, then upload its trajectory and metadata to Object Storage. A bundled PDB file makes the initial input reproducible. This example teaches Serverless execution and persistence; scientific use needs an appropriate simulation protocol.

## Before you start

Complete the [CLI prerequisites](../../README.md#prerequisites). You need Docker, the AWS CLI with [Object Storage credentials](https://docs.nebius.com/object-storage/interfaces/aws-cli), an existing bucket, a container registry you can push to, and quota for one L40S GPU VM. Run commands from `life-science/openmm-simulation`.

## Run

### 1. Build the example image

Use a fresh tag so the image contains your current code:

```bash
export IMAGE="your-registry/openmm-demo:your-new-tag"
docker build --platform linux/amd64 -t "$IMAGE" .
docker push "$IMAGE"
```

The Dockerfile installs OpenMM 8.4 with CUDA 12 support and the example's locked Python dependencies. `sim/run.py` prepares the structure, runs OpenMM, saves metadata, and calls the short boto3 uploader.

### 2. Configure storage and submit

Choose your subnet with `nebius vpc subnet list`. Set the region to match your bucket. AWS credentials come from your configured shell; do not commit keys.

```bash
export SUBNET_ID="your-subnet-id"
export AWS_ACCESS_KEY_ID="your-object-storage-access-key"
export AWS_SECRET_ACCESS_KEY="your-object-storage-secret-key"
export AWS_DEFAULT_REGION="eu-north1"
export S3_ENDPOINT_URL="https://storage.$AWS_DEFAULT_REGION.nebius.cloud"
export S3_BUCKET="your-existing-bucket"
export S3_PREFIX="openmm-demo"

aws --endpoint-url "$S3_ENDPOINT_URL" s3 ls "s3://$S3_BUCKET/"
bash scripts/run_serverless.sh 1UBQ 200
```

The helper selects one L40S GPU and `OPENMM_PLATFORM=CUDA`, so a failed CUDA initialization cannot silently fall back to CPU. The one-hour timeout caps runtime. For shared environments, use [secret references](https://docs.nebius.com/serverless/jobs/manage) in place of passing credentials through `--env`.

## Verify

Follow the log and status commands printed by the helper. Wait for `COMPLETED`. Logs must show `Using OpenMM platform: CUDA`, `Results uploaded to s3://...`, and `Simulation complete!`. A failed required upload fails the Job.

Copy the output URI from the logs and download it:

```bash
export OUTPUT_URI="s3://your-bucket/openmm-demo/your-run-directory/"
aws --endpoint-url "$S3_ENDPOINT_URL" s3 sync "$OUTPUT_URI" ./results/downloaded/
```

The result contains the input/processed PDB files, the simulation topology, a `.dcd` trajectory, simulation log, and metadata file. These confirm execution and persistence; they are not a biological validation result.

## Adapt and finish

Change the protein ID and step count passed to the helper. Other PDB IDs are downloaded from RCSB; for custom cached structures use the trainer's `--pdb-cache-dir` argument. Add `--plots` to the container arguments to generate optional trajectory plots.

A local CPU check keeps output on the host and does not upload it:

```bash
bash scripts/run_docker.sh 1UBQ 200
```

The direct Python equivalent is `OPENMM_PLATFORM=CPU python -m sim.run --protein-id 1UBQ --steps 200`. With `S3_BUCKET` unset it writes local results only; with a bucket set, upload is required.

Delete the completed Job record. Remove only this run's artifacts when you no longer need them:

```bash
nebius ai job delete <job-id>
aws --endpoint-url "$S3_ENDPOINT_URL" s3 rm "$OUTPUT_URI" --recursive
```

For input or simulation errors, start with the bundled `1UBQ` and inspect logs. For upload failures, check bucket permissions and endpoint URL. The demo uses hydrogen-bond constraints, a Langevin integrator, and energy minimization; it fails if this protocol cannot initialize.

## Validation

Checked locally: OpenMM 8.4 completed 20 CPU steps with bundled `1UBQ`, saving a trajectory and metadata. CUDA and real S3 upload were not rerun. See [validation notes](../../docs/validation.md).
