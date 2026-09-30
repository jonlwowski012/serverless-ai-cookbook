"""Stage the pinned full DROID split, or a small end-to-end test sample."""

import json
import os
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory

from huggingface_hub import HfApi, hf_hub_download

from flux_action.data.droid.index import build_manifest, build_rows, write_manifest


REVISION = "5c11a20accb11497270a5247a7f1e66ad04c956c"
FILTER_REVISION = "bcb840c3b496533e0adf548a54b51f2f00057837"
WORK = Path("/workspace/run")
SOURCE = Path("/workspace/data/full/source")
INDEX = Path("/workspace/data/full/index")
SAMPLE_FILES = {
    "success/meta/info.json",
    "success/meta/tasks.parquet",
    "success/meta/episodes/chunk-000/file-000.parquet",
    "success/data/chunk-000/file-000.parquet",
    "success/videos/observation.image.wrist_image_left/chunk-000/file-000.mp4",
    "success/videos/observation.image.exterior_image_1_left/chunk-000/file-000.mp4",
    "success/videos/observation.image.exterior_image_2_left/chunk-000/file-000.mp4",
}


def stage_file(file):
    target = SOURCE / file.rfilename
    if target.is_file() and target.stat().st_size == file.size:
        return
    with TemporaryDirectory(dir=WORK) as temporary:
        downloaded = hf_hub_download(
            "nvidia/Cosmos3-DROID",
            file.rfilename,
            repo_type="dataset",
            revision=REVISION,
            local_dir=temporary,
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(downloaded, target)
    if target.stat().st_size != file.size:
        raise ValueError(f"incomplete upload: {file.rfilename}")


def main():
    mode = os.environ.get("STAGE_MODE", "full")
    if mode not in {"full", "sample"}:
        raise ValueError("STAGE_MODE must be full or sample")
    WORK.mkdir(parents=True, exist_ok=True)
    files = [
        file
        for file in HfApi().dataset_info(
            "nvidia/Cosmos3-DROID", revision=REVISION, files_metadata=True
        ).siblings
        if (file.rfilename.startswith("success/") if mode == "full" else file.rfilename in SAMPLE_FILES)
    ]
    if mode == "sample" and {file.rfilename for file in files} != SAMPLE_FILES:
        raise ValueError("pinned DROID sample is missing files")
    print(f"Staging {len(files)} files ({sum(file.size for file in files):,} bytes)", flush=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        for count, _ in enumerate(pool.map(stage_file, files), 1):
            if count % 100 == 0 or count == len(files):
                print(f"Staged {count}/{len(files)} files", flush=True)

    filter_file = hf_hub_download(
        "KarlP/droid",
        "keep_ranges_1_0_1.json",
        revision=FILTER_REVISION,
        local_dir=WORK / "filter",
    )
    shutil.copyfile(filter_file, SOURCE / "keep_ranges_1_0_1.json")
    manifest = build_manifest(
        SOURCE, SOURCE / "keep_ranges_1_0_1.json", revision=REVISION,
        only_available=mode == "sample",
    )
    local_index = WORK / "index"
    local_index.mkdir()
    build_rows(SOURCE, manifest, local_index / "rows.f32.npy")
    write_manifest(manifest, local_index / "manifest.json")
    INDEX.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(local_index / "rows.f32.npy", INDEX / "rows.f32.npy")
    shutil.copyfile(local_index / "manifest.json", INDEX / "manifest.json")
    print(json.dumps(manifest["counts"]), flush=True)


if __name__ == "__main__":
    main()
