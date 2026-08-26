from unsloth import FastLanguageModel

ADAPTERS = "adapters_cuda"
OUT = "model-gguf"
QUANT = "q5_k_m"  # q4_k_m smaller, q6_k higher quality; all fit a 6GB 1660 for a 3B

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=ADAPTERS,          # unsloth reads the base model from adapter_config
    max_seq_length=32768,
    load_in_4bit=True,
)
model.save_pretrained_gguf(OUT, tokenizer, quantization_method=QUANT)
print(f"Saved GGUF ({QUANT}) to {OUT}/  -- scp this home, run with Ollama/llama.cpp")
