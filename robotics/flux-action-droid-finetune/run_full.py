"""Run full DROID training, publishing complete checkpoints from rank zero."""

import os
import re
import shutil
from pathlib import Path

import torch
import torch.distributed as dist

from flux_action.training.checkpoint import export_policy, latest_checkpoint
from flux_action.training.distributed import barrier, init_distributed
from flux_action.training.trainer import TrainConfig, Trainer


def copy_files(source, destination):
    for path in source.rglob("*"):
        if path.is_file() and path.name != "COMPLETE":
            target = destination / path.relative_to(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
            if target.stat().st_size != path.stat().st_size:
                raise ValueError(f"incomplete copy: {target}")


class PublishingTrainer(Trainer):
    def __init__(self, config, output):
        super().__init__(config)
        self.publish_dir = output

    def _checkpoint(self):
        super()._checkpoint()
        if self.rank == 0:
            checkpoint = latest_checkpoint(self.output_dir)
            destination = self.publish_dir / checkpoint.name
            copy_files(checkpoint, destination)
            shutil.copyfile(checkpoint / "COMPLETE", destination / "COMPLETE")
            shutil.copyfile(self.output_dir / "metrics.jsonl", self.publish_dir / "metrics.jsonl")
            print(f"Published {checkpoint.name}", flush=True)
        barrier()


def main():
    bucket = Path(os.environ.get("FLUX_ACTION_BUCKET", "/workspace/data/full"))
    work = Path(os.environ.get("FLUX_ACTION_WORK", "/workspace/run"))
    config_path = Path(os.environ.get("FLUX_ACTION_CONFIG", bucket / "train.json"))
    run_name = os.environ["RUN_NAME"]
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", run_name):
        raise ValueError("RUN_NAME must be a simple name")
    rank = int(os.environ.get("RANK", "0"))
    local_rank = int(os.environ.get("LOCAL_RANK", "0"))
    world_size = int(os.environ.get("WORLD_SIZE", "1"))
    expected_world_size = int(os.environ.get("EXPECTED_WORLD_SIZE", "1"))
    if world_size != expected_world_size:
        raise ValueError(f"expected {expected_world_size} training ranks, got {world_size}")
    expected_gpu = os.environ.get("EXPECTED_GPU_NAME")
    if expected_gpu:
        if torch.cuda.device_count() != world_size:
            raise RuntimeError(f"expected {world_size} GPUs, got {torch.cuda.device_count()}")
        name = torch.cuda.get_device_name(local_rank)
        if expected_gpu.lower() not in name.lower():
            raise RuntimeError(f"rank {rank}: expected {expected_gpu}, got {name}")
        print(f"rank {rank}/{world_size}: {name}", flush=True)
    init_distributed()

    try:
        config = TrainConfig.from_file(config_path)
        if world_size > 1 and config.shard_size != world_size:
            raise ValueError(f"config shard_size {config.shard_size} does not match {world_size} ranks")
        output = bucket / "output" / run_name
        if rank == 0:
            output.mkdir(parents=True, exist_ok=True)
            if (output / "COMPLETE").exists():
                raise FileExistsError(f"run already completed: {run_name}")
            shutil.copytree(bucket / "index", work / "index", copy_function=shutil.copyfile)
            previous = latest_checkpoint(output)
            if previous is not None:
                restored = work / "checkpoints" / previous.name
                copy_files(previous, restored)
                shutil.copyfile(previous / "COMPLETE", restored / "COMPLETE")
        barrier()

        PublishingTrainer(config, output).run()
        barrier()
        if rank == 0:
            checkpoint = latest_checkpoint(config.output_dir)
            export_policy(checkpoint, work / "export", profile="model", dtype="bfloat16")
            shutil.copyfile(config_path, output / "train.json")
            shutil.copyfile(Path(config.output_dir) / "metrics.jsonl", output / "metrics.jsonl")
            copy_files(work / "export", output / "export")
            (output / "COMPLETE").write_text(f"{config.steps}\n")
        barrier()
    finally:
        if dist.is_initialized():
            dist.destroy_process_group()


if __name__ == "__main__":
    main()
