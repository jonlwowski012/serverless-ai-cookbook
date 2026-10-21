---
title: RFD4-Proteina NVIDIA NIM
category: life-sciences
type: endpoint
runtime: gpu-h100-sxm
frameworks: [nvidia-nim]
keywords: [protein-design, rfd4]
difficulty: intermediate
---

# RFD4-Proteina NVIDIA NIM

<!-- factory:deploy -->

<a href="https://console.nebius.com/serverless/endpoint/create?image=nvcr.io%2Fnim%2Fipd%2Frfd4-proteina%40sha256%3Af4106e6b659aa53979d37c450c0c0cef620dcfce63934ef7e8e1268c5439b49a&amp;platform=gpu-h100-sxm&amp;preset=1gpu-16vcpu-200gb&amp;preemptible=false&amp;diskSize=200GiB&amp;targetPort=8000&amp;auth=true"><img src="../assets/create-endpoint.svg" alt="Create Endpoint" width="138" height="20"></a>

<!-- /factory:deploy -->

Follow the [recipe](../../life-science/rfd4-proteina/nim/README.md) for
secrets, bucket setup, commands and expected outputs. The image is pulled directly
from NVIDIA.

[Validation status](../../life-science/rfd4-proteina/validation.md).
