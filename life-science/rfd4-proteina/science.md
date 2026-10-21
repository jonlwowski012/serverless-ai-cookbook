# Scientific notes

The two recipes run different checkpoint pairs. NVIDIA's NIM release includes
its own pre-release pair; the Hugging Face recipe pins the retrained public
flow model and autoencoder together. Results from one release do not establish
quality or performance for the other.

The supplied problems are:

- A blank 150-residue protein, with no supplied sequence or fold.
- An 80-residue binder candidate around a fixed 115-residue PD-L1 target and
  contact annotations. The target sequence was checked against human PD-L1,
  [UniProt Q9NZQ7](https://www.uniprot.org/uniprotkb/Q9NZQ7/entry).
- A 150-residue protein conditioned on the identity and coordinates of heme B.

Keep the request or annotated CIF, its hash, the image digest, model revision,
seed, software versions and every proposed structure. For NIM, also retain the
response's `model`, `runtime`, `schedule` and `warnings` fields. A seed does not
make different models or execution backends equivalent.

NIM's built-in design metrics do not constitute independent refolding or binding
validation. The Hugging Face example disables optional metrics and returns raw
proposals. Neither recipe bundles a structure-prediction oracle. NVIDIA documents
an [external-oracle interface](https://docs.nvidia.com/nim/bionemo/rfd4-proteina/latest/oracle.html)
for separate evaluation workflows.

A proposed structure does not establish solubility, specificity, binding, metal
coordination or enzyme activity. These recipes carry no comparative success-rate
or cross-GPU benchmark claim. Earlier experiments with other images/checkpoints
are kept separate from this publication.
