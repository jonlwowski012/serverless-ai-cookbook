"""Train a ViT image classifier and save its model and test metrics."""

import argparse
import shutil
import tempfile
from pathlib import Path

import numpy as np
import yaml
from datasets import load_dataset
from torchvision.transforms import (
    Compose,
    Normalize,
    RandomHorizontalFlip,
    Resize,
    ToTensor,
)
from transformers import (
    AutoImageProcessor,
    AutoModelForImageClassification,
    DefaultDataCollator,
    Trainer,
    TrainingArguments,
)


def compute_metrics(prediction):
    predicted_labels = np.argmax(prediction.predictions, axis=-1)
    return {"accuracy": float(np.mean(predicted_labels == prediction.label_ids))}


def publish_output(source: Path, destination: Path):
    # Save model weights locally before copying them to the mounted bucket.
    for path in source.rglob("*"):
        if path.is_file():
            target = destination / path.relative_to(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
    (destination / "COMPLETE").write_text("Model and metrics copied successfully.\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("/mnt/data/config.yaml"))
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    config = yaml.safe_load(args.config.read_text())
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise FileExistsError(f"use a fresh output directory: {args.output_dir}")
    local_output = Path(tempfile.mkdtemp(prefix="classifier-"))

    print("Loading the image dataset", flush=True)
    dataset = load_dataset(config["dataset_name"], revision=config["dataset_revision"])
    labels = dataset["train"].features["label"].names
    processor = AutoImageProcessor.from_pretrained(config["model_name"])
    image_size = processor.size["height"]
    normalize = Normalize(processor.image_mean, processor.image_std)
    train_transforms = Compose(
        [
            Resize((image_size, image_size)),
            RandomHorizontalFlip(),
            ToTensor(),
            normalize,
        ]
    )
    test_transforms = Compose([Resize((image_size, image_size)), ToTensor(), normalize])

    def transform_batch(batch, transforms):
        images = []
        for image in batch["image"]:
            images.append(transforms(image.convert("RGB")))
        return {"pixel_values": images, "labels": batch["label"]}

    training_data = dataset["train"].with_transform(
        lambda batch: transform_batch(batch, train_transforms)
    )
    validation_data = dataset["validation"].with_transform(
        lambda batch: transform_batch(batch, test_transforms)
    )
    test_data = dataset["test"].with_transform(
        lambda batch: transform_batch(batch, test_transforms)
    )
    model = AutoModelForImageClassification.from_pretrained(
        config["model_name"],
        num_labels=len(labels),
        id2label=dict(enumerate(labels)),
        label2id={label: index for index, label in enumerate(labels)},
        ignore_mismatched_sizes=True,  # Replace the pretrained classification head.
    )
    trainer = Trainer(
        model=model,
        args=TrainingArguments(
            output_dir=str(local_output),
            num_train_epochs=config["epochs"],
            per_device_train_batch_size=config["batch_size"],
            per_device_eval_batch_size=config["batch_size"],
            learning_rate=2e-5,
            eval_strategy="epoch",
            save_strategy="epoch",
            load_best_model_at_end=True,
            metric_for_best_model="accuracy",
            save_total_limit=1,
            save_only_model=True,
            fp16=True,
            remove_unused_columns=False,  # Keep images for the dataset transforms.
            report_to="none",
            seed=42,
        ),
        train_dataset=training_data,
        eval_dataset=validation_data,
        data_collator=DefaultDataCollator(),
        compute_metrics=compute_metrics,
    )
    print("Training the classifier", flush=True)
    trainer.train()
    metrics = trainer.evaluate(test_data, metric_key_prefix="test")
    trainer.save_metrics("test", metrics)
    trainer.save_model(str(local_output / "model"))
    processor.save_pretrained(local_output / "model")
    publish_output(local_output, args.output_dir)
    print(f"Test accuracy: {metrics['test_accuracy']:.3f}")
    print(f"Model and metrics saved to {args.output_dir}", flush=True)


if __name__ == "__main__":
    main()
