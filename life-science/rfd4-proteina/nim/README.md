---
title: RFD4-Proteina with NVIDIA NIM
category: life-sciences
type: endpoint
runtime: gpu-h100-sxm
frameworks: [nvidia-nim]
keywords: [protein-design, object-storage, rfd4]
difficulty: intermediate
---

# RFD4-Proteina with NVIDIA NIM

Run NVIDIA's official image, upload a request to your private bucket, and use a
CPU job to send it to the model. The response returns to the same bucket.
No Docker build or image copy is needed.

This NIM uses the checkpoint pair listed in NVIDIA's [release notes](https://docs.nvidia.com/nim/bionemo/rfd4-proteina/latest/release-notes.html#model-checkpoints),
which differs from the [public Hugging Face model](../hugging-face/README.md).

## Create the model endpoint

You need a Nebius project with H100 quota, an NGC API key with access to this
NIM, and a private Object Storage bucket.

1. In MysteryBox, save your NGC key in a secret with payload keys
   `NGC_API_KEY` and `REGISTRY_PASSWORD`. Add `REGISTRY_USERNAME` with the literal
   value `$oauthtoken` to that same secret.
2. Create a second secret with an `AUTH_TOKEN` payload containing your chosen
   endpoint access token. Keep both tokens out of URLs and input files.
3. Open **Create Endpoint**:

<!-- factory:deploy -->

<a href="https://console.nebius.com/serverless/endpoint/create?image=nvcr.io%2Fnim%2Fipd%2Frfd4-proteina%40sha256%3Af4106e6b659aa53979d37c450c0c0cef620dcfce63934ef7e8e1268c5439b49a&amp;platform=gpu-h100-sxm&amp;preset=1gpu-16vcpu-200gb&amp;preemptible=false&amp;diskSize=200GiB&amp;targetPort=8000&amp;auth=true"><img src="../../../templates/assets/create-endpoint.svg" alt="Create Endpoint" width="138" height="20"></a>

<!-- /factory:deploy -->

4. Select your project, one regular H100 (`gpu-h100-sxm`,
   `1gpu-16vcpu-200gb`), a **200 GiB disk**, and container port **8000**.
   Keep the image's default startup command.
5. Select your NGC secret under private-registry credentials. Add `NGC_API_KEY`
   as an environment variable from that secret. Enable **Token authentication**
   using the `AUTH_TOKEN` secret. Start with at most one replica.
6. Add these ordinary environment variables to bound the NIM's request queue:

```text
NIM_ENABLE_QUEUE_METRICS=true
NIM_MAX_CONCURRENT_REQUESTS=1
NIM_MAX_QUEUE_DEPTH=8
NIM_QUEUE_TIMEOUT_SECONDS=60
```

These are admission settings, not a measured customer capacity. Wait for the
endpoint to be ready and copy its HTTPS URL. NIM downloads its checkpoints on
first startup. Check readiness from a terminal with your own URL and token:

```bash
curl --fail -H "Authorization: Bearer $AUTH_TOKEN" "$RFD4_URL/v1/health/ready"
```

## Send a request from your bucket

1. Upload [monomer.json](../inputs/nim/monomer.json) to
   `rfd4/inputs/monomer.json` in your bucket.
2. Open **Create Job**:

<a href="https://console.nebius.com/serverless/job/create?image=alpine%2Fcurl%40sha256%3Ac103daf2dbf75dbaee86c278f45be6c82acd86eef27e17521d0992bf90031d81&amp;platform=cpu-d3&amp;preset=2vcpu-8gb&amp;preemptible=false&amp;command=%2Fbin%2Fsh+-c+%27test+%21+-e+%2Fdata%2Frfd4%2Fruns%2Fmonomer-001%2Fresponse.json+%26%26+curl+--fail-with-body+--show-error+--silent+--max-time+1800+--create-dirs+-H+%22Authorization%3A+Bearer+%24AUTH_TOKEN%22+-H+%22Content-Type%3A+application%2Fjson%22+--data-binary+%40%2Fdata%2Frfd4%2Finputs%2Fmonomer.json+--output+%2Fdata%2Frfd4%2Fruns%2Fmonomer-001%2Fresponse.json+%22%24RFD4_URL%2Fbiology%2Fipd%2Frfd4-proteina%2Fgenerative%22%27&amp;diskSize=20GiB&amp;volume=%2Fdata"><img src="../../../templates/assets/create-job.svg" alt="Create Job" width="138" height="20"></a>

3. Use regular CPU compute (`cpu-d3`, `2vcpu-8gb`), a **20 GiB disk** and a
   **one-hour timeout**. Attach your bucket **read-write at `/data`**.
4. Set `RFD4_URL` to the endpoint's HTTPS URL, without a trailing slash.
   Set `AUTH_TOKEN` from the same MysteryBox token secret. Check the prefilled
   command and create the job.
5. Collect `rfd4/runs/monomer-001/response.json` from the bucket. It contains
   proposed sequences, CIF structure text, metrics, seeds and model metadata.

The job refuses to replace an existing `response.json`; choose a new run folder
for each attempt. An HTTP error fails the job and leaves the response body for
diagnosis. It does not retry a design request automatically.

## Other examples

Use the same endpoint and bucket. Upload the selected JSON to
`rfd4/inputs/`, then use its job button.

| Request | What it asks for | Run |
|---|---|---|
| [pdl1.json](../inputs/nim/pdl1.json) | Two 80-residue binder candidates against the supplied PD-L1 target | <a href="https://console.nebius.com/serverless/job/create?image=alpine%2Fcurl%40sha256%3Ac103daf2dbf75dbaee86c278f45be6c82acd86eef27e17521d0992bf90031d81&amp;platform=cpu-d3&amp;preset=2vcpu-8gb&amp;preemptible=false&amp;command=%2Fbin%2Fsh+-c+%27test+%21+-e+%2Fdata%2Frfd4%2Fruns%2Fpdl1-001%2Fresponse.json+%26%26+curl+--fail-with-body+--show-error+--silent+--max-time+1800+--create-dirs+-H+%22Authorization%3A+Bearer+%24AUTH_TOKEN%22+-H+%22Content-Type%3A+application%2Fjson%22+--data-binary+%40%2Fdata%2Frfd4%2Finputs%2Fpdl1.json+--output+%2Fdata%2Frfd4%2Fruns%2Fpdl1-001%2Fresponse.json+%22%24RFD4_URL%2Fbiology%2Fipd%2Frfd4-proteina%2Fgenerative%22%27&amp;diskSize=20GiB&amp;volume=%2Fdata"><img src="../../../templates/assets/create-job.svg" alt="Create Job" width="138" height="20"></a> |
| [heme.json](../inputs/nim/heme.json) | Two 150-residue proteins conditioned on heme B | <a href="https://console.nebius.com/serverless/job/create?image=alpine%2Fcurl%40sha256%3Ac103daf2dbf75dbaee86c278f45be6c82acd86eef27e17521d0992bf90031d81&amp;platform=cpu-d3&amp;preset=2vcpu-8gb&amp;preemptible=false&amp;command=%2Fbin%2Fsh+-c+%27test+%21+-e+%2Fdata%2Frfd4%2Fruns%2Fheme-001%2Fresponse.json+%26%26+curl+--fail-with-body+--show-error+--silent+--max-time+1800+--create-dirs+-H+%22Authorization%3A+Bearer+%24AUTH_TOKEN%22+-H+%22Content-Type%3A+application%2Fjson%22+--data-binary+%40%2Fdata%2Frfd4%2Finputs%2Fheme.json+--output+%2Fdata%2Frfd4%2Fruns%2Fheme-001%2Fresponse.json+%22%24RFD4_URL%2Fbiology%2Fipd%2Frfd4-proteina%2Fgenerative%22%27&amp;diskSize=20GiB&amp;volume=%2Fdata"><img src="../../../templates/assets/create-job.svg" alt="Create Job" width="138" height="20"></a> |

Change `sampling.num_replicates` or `sampling.seed` in the JSON for another run.
For your own structures and tasks, follow NVIDIA's
[request examples](https://docs.nvidia.com/nim/bionemo/rfd4-proteina/latest/example-requests.html).
The supplied request embeds its input structure; no extra file upload is needed.

To save the first returned structure locally:

```bash
jq -r '.designs[0].structure.content' response.json > design.cif
```

Delete completed CPU jobs after collecting results. Stop or delete the GPU
endpoint when finished, or configure scale-to-zero for your project.
[Validation limits](../validation.md) include direct NVCR pull and cold-start acceptance.

## Troubleshooting

If the endpoint fails before any container logs appear, check the
[direct NVCR pull limitation](../validation.md). If checkpoint download fails,
check NGC access and the `NGC_API_KEY` secret. For request errors, retain
`response.json` and check readiness and the endpoint token before a new attempt.
