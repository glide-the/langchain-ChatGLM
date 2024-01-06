"""
Apply the LoRA weights on top of a base model.

Usage:
python3 -m fastchat.model.apply_lora --base ~/model_weights/llama-7b --target ~/model_weights/baize-7b --lora project-baize/baize-lora-7B

Dependency:
pip3 install git+https://github.com/huggingface/peft.git@2822398fbe896f25d4dac5e468624dc5fd65a51b
"""
import argparse

import torch
from peft import PeftModel
from transformers import AutoTokenizer, AutoModelForCausalLM

from transformers import (
    AutoConfig,
    AutoModel,
    AutoModelForCausalLM,
    AutoModelForSeq2SeqLM,
    AutoTokenizer,
    LlamaTokenizer,
    LlamaForCausalLM,
    T5Tokenizer,
)
def apply_lora(base_model_path, target_model_path, lora_path):
    print(f"Loading the base model from {base_model_path}")
    # base = AutoModelForCausalLM.from_pretrained(
    #     base_model_path, torch_dtype=torch.float16, low_cpu_mem_usage=True
    # )
    # base_tokenizer = AutoTokenizer.from_pretrained(base_model_path, use_fast=False)

    from transformers.generation import GenerationConfig

    revision = 'main'
    config = AutoConfig.from_pretrained(
        base_model_path,
        trust_remote_code=True,
    )
    # NOTE: if you use the old version of model file, please remove the comments below
    # config.use_flash_attn = False
    # self.float_set(config, "fp16")
    generation_config = GenerationConfig.from_pretrained(
        base_model_path, trust_remote_code=True
    )
    base = AutoModelForCausalLM.from_pretrained(
        base_model_path,
        config=config,
        low_cpu_mem_usage=True,
        trust_remote_code=True, revision=revision
    ).eval()
    if hasattr(base.config, "use_dynamic_ntk") and base.config.use_dynamic_ntk:
        base.config.max_sequence_length = 16384
    base_tokenizer = AutoTokenizer.from_pretrained(
        base_model_path, trust_remote_code=True, revision=revision
    )
    base_tokenizer.eos_token_id = config.eos_token_id
    base_tokenizer.bos_token_id = config.bos_token_id
    base_tokenizer.pad_token_id = generation_config.pad_token_id
    base.config.eos_token_id = base_tokenizer.eos_token_id
    base.config.bos_token_id = base_tokenizer.bos_token_id
    base.config.pad_token_id = base_tokenizer.pad_token_id
    print(f"Loading the LoRA adapter from {lora_path}")

    lora_model = PeftModel.from_pretrained(
        base,
        lora_path,
        # torch_dtype=torch.float16
    )

    print("Applying the LoRA")
    model = lora_model.merge_and_unload()

    print(f"Saving the target model to {target_model_path}")
    model.save_pretrained(target_model_path)
    base_tokenizer.save_pretrained(target_model_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-model-path", type=str, required=True)
    parser.add_argument("--target-model-path", type=str, required=True)
    parser.add_argument("--lora-path", type=str, required=True)

    args = parser.parse_args()

    apply_lora(args.base_model_path, args.target_model_path, args.lora_path)
