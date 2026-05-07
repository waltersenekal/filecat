"""
Patch RAM model's bert.py for compatibility with transformers >= 5.0
(apply_chunking_to_forward, find_pruneable_heads_and_indices, prune_linear_layer were removed)
"""
import os
import sys
import site

# Find RAM's bert.py
site_packages = site.getsitepackages()[0] if hasattr(site, 'getsitepackages') else os.path.join(sys.prefix, 'lib', 'site-packages')
# On Windows it might be Lib/site-packages
for candidate in [site_packages, os.path.join(sys.prefix, 'Lib', 'site-packages'), os.path.join(sys.prefix, 'lib', f'python{sys.version_info.major}.{sys.version_info.minor}', 'site-packages')]:
    bert_path = os.path.join(candidate, 'ram', 'models', 'bert.py')
    if os.path.exists(bert_path):
        break
else:
    print("RAM bert.py not found - skipping patch (AI tagger may not work)")
    sys.exit(0)

with open(bert_path, 'r') as f:
    content = f.read()

OLD_IMPORT = """from transformers.modeling_utils import (
    PreTrainedModel,
    apply_chunking_to_forward,
    find_pruneable_heads_and_indices,
    prune_linear_layer,
)"""

NEW_IMPORT = """from transformers.modeling_utils import PreTrainedModel
import torch

def apply_chunking_to_forward(forward_fn, chunk_size, chunk_dim, *input_tensors):
    if chunk_size > 0:
        tensor_shape = input_tensors[0].shape[chunk_dim]
        if tensor_shape % chunk_size != 0:
            raise ValueError(f"dimension {chunk_dim} must be divisible by chunk_size {chunk_size}")
        num_chunks = tensor_shape // chunk_size
        input_tensors_chunks = tuple(t.chunk(num_chunks, dim=chunk_dim) for t in input_tensors)
        output_chunks = tuple(forward_fn(*chunks) for chunks in zip(*input_tensors_chunks))
        return torch.cat(output_chunks, dim=chunk_dim)
    return forward_fn(*input_tensors)

def find_pruneable_heads_and_indices(heads, n_heads, head_size, already_pruned_heads):
    mask = torch.ones(n_heads, head_size)
    heads = set(heads) - already_pruned_heads
    for head in heads:
        head = head - sum(1 if h < head else 0 for h in already_pruned_heads)
        mask[head] = 0
    mask = mask.view(-1).contiguous().eq(1)
    index = torch.arange(len(mask))[mask].long()
    return heads, index

def prune_linear_layer(layer, index, dim=0):
    index = index.to(layer.weight.device)
    W = layer.weight.index_select(dim, index).clone().detach()
    if layer.bias is not None:
        if dim == 1:
            b = layer.bias.clone().detach()
        else:
            b = layer.bias[index].clone().detach()
    else:
        b = None
    new_size = list(layer.weight.size())
    new_size[dim] = len(index)
    new_layer = torch.nn.Linear(new_size[1], new_size[0], bias=layer.bias is not None).to(layer.weight.device)
    new_layer.weight.requires_grad = False
    new_layer.weight.copy_(W.contiguous())
    new_layer.weight.requires_grad = True
    if b is not None:
        new_layer.bias.requires_grad = False
        new_layer.bias.copy_(b.contiguous())
        new_layer.bias.requires_grad = True
    return new_layer"""

if OLD_IMPORT in content:
    content = content.replace(OLD_IMPORT, NEW_IMPORT)
    with open(bert_path, 'w') as f:
        f.write(content)
    print(f"Patched: {bert_path}")
else:
    print("bert.py: Already patched or import format differs - skipping")

# Patch utils.py - fix additional_special_tokens_ids removed in transformers 5.x
utils_path = os.path.join(os.path.dirname(bert_path), 'utils.py')
if os.path.exists(utils_path):
    with open(utils_path, 'r') as f:
        utils_content = f.read()

    OLD_TOKENIZER = "    tokenizer.enc_token_id = tokenizer.additional_special_tokens_ids[0]"
    NEW_TOKENIZER = "    # Patched for transformers>=5.0 (additional_special_tokens_ids removed)\n    tokenizer.enc_token_id = tokenizer.convert_tokens_to_ids('[ENC]')"

    if OLD_TOKENIZER in utils_content:
        utils_content = utils_content.replace(OLD_TOKENIZER, NEW_TOKENIZER)
        with open(utils_path, 'w') as f:
            f.write(utils_content)
        print(f"Patched: {utils_path}")
    else:
        print("utils.py: Already patched or format differs - skipping")

