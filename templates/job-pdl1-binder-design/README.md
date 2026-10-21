---
title: PD-L1 binder design with RFD4-Proteina
category: life-sciences
type: job
runtime: gpu-h100-sxm
frameworks: [pytorch, huggingface, nvidia-nim]
keywords: [protein-design, pdl1, openfold3]
difficulty: intermediate
---

# PD-L1 binder design with RFD4-Proteina

<!-- factory:deploy -->

<a href="https://console.nebius.com/serverless/job/create?image=nvcr.io%2Fnvidia%2Fpytorch%40sha256%3Af71fd67f6d71f685e0bd08ce6c8df48807624cc5d48886370d3471bc4f89d81d&amp;platform=gpu-h100-sxm&amp;preset=1gpu-16vcpu-200gb&amp;preemptible=false&amp;command=%2Fbin%2Fbash+-lc+%27set+-e%0Aapt-get+update+%26%26+apt-get+install+-y+--no-install-recommends+libxrender1+libx11-6+libxext6%0Aunset+PYTHONPATH%0Aexport+LD_LIBRARY_PATH%3D%2Fusr%2Flocal%2Fnvidia%2Flib%3A%2Fusr%2Flocal%2Fnvidia%2Flib64%0Atest+%21+-e+%2Fdata%2Frfd4%2Fruns%2Fpdl1-001%0Apython+-m+pip+install+--no-cache-dir+uv%3D%3D0.13.4%0Auv+venv+--python+3.12+%2Ftmp%2Frfd4%0Auv+pip+install+--python+%2Ftmp%2Frfd4%2Fbin%2Fpython+--torch-backend+cu130+torch%3D%3D2.14.1+%27%22%27%22%27atomworks%5Bml%2Copenbabel%5D%3D%3D3.0.4%27%22%27%22%27+cuequivariance%3D%3D0.13.0+cuequivariance-torch%3D%3D0.13.0+cuequivariance-ops-torch-cu13%3D%3D0.13.0+cuequivariance-ops-cu13%3D%3D0.13.0+%27%22%27%22%27rfd4-proteina%5Ball-cuda13%5D%3D%3D0.0.2%27%22%27%22%27%0A%2Ftmp%2Frfd4%2Fbin%2Frfd4-generate+inputs%3D%2Fdata%2Frfd4%2Finputs%2Fpdl1.cif+out_dir%3D%2Fdata%2Frfd4%2Fruns%2Fpdl1-001+hf_ckpt_path%3Dnvidia%2FRFD4-Proteina+hf_ckpt_revision%3Da06e2509c7033b010fc43614e9fd840303588502+num_replicates%3D2+batch_size%3D1+seed%3D42+recycle_strategy%3Dmedium%2Ffront_loaded+inference_backend%3Dnative+compile_lengths%3Dnull+prevalidate_inputs%3Dtrue+~metrics%27&amp;diskSize=200GiB&amp;volume=%2Fdata"><img src="../assets/create-job.svg" alt="Create Job" width="138" height="20"></a>

<!-- /factory:deploy -->

Generate two 80-residue binder proposals against PD-L1 using the public model
in NVIDIA's PyTorch image. Follow the [workflow](../../life-science/rfd4-proteina/pdl1/README.md)
for bucket setup, the alternative RFD4 NIM path and an optional OpenFold3 NIM
check. Adapted from Arseniy Sokolov's PD-L1 contribution.

[Validation status](../../life-science/rfd4-proteina/validation.md).
