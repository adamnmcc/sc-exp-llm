import argparse
import json

MODEL = "unsloth/Qwen2.5-Coder-3B-Instruct-bnb-4bit"
DATA = "train.jsonl"
OUT = "adapters_cuda"

RANK = 8
# ponytail: MLX `scale=20` == PEFT lora_alpha/rank. rank 8 -> alpha 160 to match.
LORA_ALPHA = 160
MAX_SEQ = 4096
ITERS = 800
LR = 1e-5

# Qwen2.5-Coder-3B = 36 layers. MLX `num_layers: 12` trains only the last 12.
QWEN_3B_LAYERS = 36
LAST_N = 12
LAYERS = list(range(QWEN_3B_LAYERS - LAST_N, QWEN_3B_LAYERS))


def check_dataset():
    with open(DATA) as f:
        rows = [json.loads(line) for line in f if line.strip()]
    assert rows, f"{DATA} is empty"
    assert all("text" in r for r in rows), "every record must have a 'text' field"
    assert all("<|im_start|>" in r["text"] for r in rows), "chat template missing from text"
    print(f"OK: {len(rows)} records, all have templated 'text'")


def train():
    from unsloth import FastLanguageModel
    from datasets import load_dataset
    from trl import SFTConfig, SFTTrainer

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=MODEL,
        max_seq_length=MAX_SEQ,
        load_in_4bit=True,
    )

    model = FastLanguageModel.get_peft_model(
        model,
        r=RANK,
        lora_alpha=LORA_ALPHA,
        lora_dropout=0.0,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
        layers_to_transform=LAYERS,
        use_gradient_checkpointing="unsloth",
        random_state=0,
    )

    dataset = load_dataset("json", data_files=DATA, split="train")

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        args=SFTConfig(
            dataset_text_field="text",
            max_seq_length=MAX_SEQ,
            per_device_train_batch_size=1,
            gradient_accumulation_steps=1,
            max_steps=ITERS,
            learning_rate=LR,
            optim="adamw_8bit",
            logging_steps=10,
            save_steps=100,
            seed=0,
            output_dir=OUT,
            report_to="none",
        ),
    )

    trainer.train()
    model.save_pretrained(OUT)
    tokenizer.save_pretrained(OUT)
    print(f"Saved LoRA adapters to {OUT}/")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="validate dataset only, no GPU")
    args = ap.parse_args()
    if args.check:
        check_dataset()
    else:
        check_dataset()
        train()
