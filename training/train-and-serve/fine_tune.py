"""Fine-tune TinyLlama on one GPU and save a LoRA adapter to the mounted bucket."""

import argparse
import shutil
import tempfile
from pathlib import Path

import torch
from datasets import load_dataset
from peft import LoraConfig, prepare_model_for_kbit_training
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from trl import SFTConfig, SFTTrainer


def publish_output(source: Path, destination: Path):
    # safetensors needs a local filesystem; the bucket receives finished files.
    for path in source.rglob("*"):
        if path.is_file():
            target = destination / path.relative_to(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
    (destination / "COMPLETE").write_text("Adapter saved and copied successfully.\n")


def format_instruction(example):
    return {
        "text": f"### Instruction:\n{example['instruction']}\n\n"
        f"### Response:\n{example['output']}"
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="TinyLlama/TinyLlama-1.1B-Chat-v1.0")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-samples", type=int, default=32)
    parser.add_argument("--num-epochs", type=int, default=1)
    args = parser.parse_args()
    if args.max_samples < 10 or args.num_epochs < 1:
        parser.error("use at least 10 samples and one epoch")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise FileExistsError(f"use a fresh output directory: {args.output_dir}")
    local_output = Path(tempfile.mkdtemp(prefix="tinyllama-"))

    print("Loading instruction data", flush=True)
    dataset = load_dataset(
        "WizardLMTeam/WizardLM_evol_instruct_70k",
        revision="16b48bd8eecad79d4f42e1ab641db317e1b27443",
        split="train",
    )
    dataset = dataset.select(range(min(args.max_samples, len(dataset))))
    dataset = dataset.map(format_instruction, remove_columns=dataset.column_names)
    dataset = dataset.train_test_split(test_size=0.1, seed=42)

    print(f"Loading {args.model} in 4-bit precision", flush=True)
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        device_map={"": 0},
        quantization_config=BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
        ),
    )
    model.config.use_cache = False
    model = prepare_model_for_kbit_training(model)

    # These calls target the Transformers/TRL versions installed in start.sh.
    trainer = SFTTrainer(
        model=model,
        processing_class=tokenizer,
        train_dataset=dataset["train"],
        eval_dataset=dataset["test"],
        peft_config=LoraConfig(
            r=16,
            lora_alpha=32,
            lora_dropout=0.05,
            bias="none",
            task_type="CAUSAL_LM",
            target_modules="all-linear",
        ),
        args=SFTConfig(
            output_dir=str(local_output),
            num_train_epochs=args.num_epochs,
            per_device_train_batch_size=1,
            per_device_eval_batch_size=1,
            gradient_accumulation_steps=4,
            learning_rate=2e-4,
            max_seq_length=256,
            dataset_text_field="text",
            gradient_checkpointing=True,
            bf16=True,
            optim="paged_adamw_32bit",
            logging_steps=1,
            eval_strategy="epoch",
            save_strategy="no",
            report_to="none",
            seed=42,
        ),
    )
    print("Training", flush=True)
    trainer.train()
    trainer.save_metrics("eval", trainer.evaluate())
    trainer.save_model(str(local_output))
    tokenizer.save_pretrained(local_output)
    print("Copying the completed adapter to Object Storage", flush=True)
    publish_output(local_output, args.output_dir)
    print(f"TRAINING COMPLETE: adapter saved to {args.output_dir}", flush=True)


if __name__ == "__main__":
    main()
