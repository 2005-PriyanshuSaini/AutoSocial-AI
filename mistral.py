from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

_mistral_tokenizer = None
_mistral_model = None

def load_mistral():
    global _mistral_tokenizer, _mistral_model
    if _mistral_tokenizer is None or _mistral_model is None:
        _mistral_tokenizer = AutoTokenizer.from_pretrained("mistralai/Mistral-7B-Instruct-v0.2")
        _mistral_model = AutoModelForCausalLM.from_pretrained("mistralai/Mistral-7B-Instruct-v0.2")
    return _mistral_tokenizer, _mistral_model

def generate_mistral_content(prompt: str, max_new_tokens: int = 128) -> str:
    tokenizer, model = load_mistral()
    inputs = tokenizer(prompt, return_tensors="pt")
    with torch.no_grad():
        outputs = model.generate(**inputs, max_new_tokens=max_new_tokens)
    return tokenizer.decode(outputs[0], skip_special_tokens=True)