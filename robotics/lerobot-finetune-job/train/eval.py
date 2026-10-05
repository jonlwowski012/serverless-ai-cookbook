"""Load a saved ACT policy to check that the checkpoint is usable."""

import argparse
from pathlib import Path

from lerobot.policies.act.modeling_act import ACTPolicy


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path, help="The checkpoint's pretrained_model directory")
    args = parser.parse_args()
    for name in ("config.json", "model.safetensors"):
        if not (args.checkpoint / name).is_file():
            raise FileNotFoundError(f"missing checkpoint file: {args.checkpoint / name}")
    print(f"Loading ACT policy from {args.checkpoint}")
    policy = ACTPolicy.from_pretrained(args.checkpoint)
    policy.eval()
    print("Policy loaded. This checks the export, not task performance.")


if __name__ == "__main__":
    main()
