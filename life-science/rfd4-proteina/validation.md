# Validation status — 21 October 2026

This contribution is a review draft. It uses vendor images directly and contains
no mirrored images, model weights, custom Dockerfiles or model-serving wrappers.

Checked without starting new GPU work:

- NVIDIA NIM, NVIDIA PyTorch and Alpine curl image manifests and pinned digests.
- All three NIM requests against NVIDIA's published OpenAPI schema.
- Public-package availability and resolution of the pinned Hugging Face
  dependency set with CUDA 13 wheels in an isolated Python 3.12 environment.
- Input provenance, hashes, launch-link parameters and shell syntax.

The exact NIM endpoint, CPU bucket client and Hugging Face startup-installation
job have **not** had live end-to-end acceptance. Results from earlier custom
images are not presented as validation or benchmarks for these configurations.
Signed-in console acceptance is also pending; automated console access received
Cloudflare 403.

The cookbook's existing [NIM guide](https://github.com/nebius/serverless-ai-cookbook/blob/main/inference/nim-endpoint/README.md)
records direct NVCR image pulls exceeding the Serverless cold-start window.
This contribution keeps direct NVIDIA references; it does not use that guide's
registry-mirror workaround. Direct-pull acceptance is a merge prerequisite.

Before merging, confirm readiness and authenticated requests, then check bucket
input/output and requested proposal counts for each example. Check the HF
runtime versions and model revision against images.json. Keep completed jobs'
outputs and remove their compute resources after acceptance.
