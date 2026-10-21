---
title: RFD4-Proteina on Nebius Serverless AI
category: life-sciences
type: endpoint
runtime: gpu-h100-sxm
frameworks: [nvidia-nim, pytorch, huggingface]
keywords: [protein-design, bionemo, object-storage]
difficulty: intermediate
---

# RFD4-Proteina on Nebius Serverless AI

Choose one of two ways to run RFD4. Both use NVIDIA images directly from
`nvcr.io`. The recipes do not build or mirror images.

| Recipe | How it runs | Model release |
|---|---|---|
| [NVIDIA NIM](nim/README.md) | A GPU endpoint; a small CPU job sends bucket requests and saves responses | NVIDIA NIM's checkpoint pair |
| [Hugging Face](hugging-face/README.md) | A finite GPU job installs the public package and reads/writes your bucket | Retrained public model and matching autoencoder |

These releases use different checkpoints. Keep their results separate. The
[image and model pins](images.json) identify each one. Both recipes include
ready-made monomer, PD-L1 binder and heme inputs. The
[PD-L1 workflow](pdl1/README.md) also covers an optional OpenFold3 structure check.

Read the [validation status](validation.md) before deployment and
[scientific notes](science.md) before interpreting the results. The recipes have
not had live acceptance on these exact vendor-image configurations.

The examples follow the cookbook's Apache-2.0 license. Input structures derive
from the public BSD-3-Clause RFD4 repository; its [notice](licenses/RFD4-BSD-3-Clause.txt)
and [input provenance](inputs/provenance.json) are retained. NVIDIA containers
have their own terms: [NIM](https://catalog.ngc.nvidia.com/orgs/nim/ipd/containers/rfd4-proteina/-/governing-terms)
and [PyTorch](https://catalog.ngc.nvidia.com/orgs/nvidia/containers/pytorch).
