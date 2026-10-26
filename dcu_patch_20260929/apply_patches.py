#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DCU (gfx928) ComfyUI 调优补丁 —— 幂等重打脚本（2026-09-29）。

合并新版 torch 镜像后 site-packages 与 comfy/ 会被覆盖，用本脚本重打：
    /root/private_data/venv/bin/python \
        /root/private_data/ComfyUI/dcu_patch_20260929/apply_patches.py [--check]

补丁：
  1. attention.py  查询分块（核心，采样 1.42x，精确等价）   [默认开]
  2. rope.py       rms_norm 用 matmul 归约（op 1.87x，端到端 0%）[默认开]
  3. samplers.py   CK_PROFILE 剖析钩子（env 关闭，无性能影响）    [默认开]
  4. model.py      H3_DEBUG 形状打印（env 关闭）                 [默认开]

详见 /root/private_data/ComfyUI/DCU调优结论_20260929.md
"""
import argparse
import os
import shutil
import sys
import time

SP = "/usr/local/lib/python3.12/site-packages/comfy_kitchen/backends/eager/rope.py"
ATTN = "/root/private_data/ComfyUI/comfy/ldm/modules/attention.py"
SAMP = "/root/private_data/ComfyUI/comfy/samplers.py"
MODEL = "/root/private_data/ComfyUI/comfy/ldm/minimax/model.py"

# ---------------------------------------------------------------- attention.py
ATTN_OLD = '''    try:
        if mask is not None:
            raise RuntimeError("Mask must not be set for Flash attention")
        out = flash_attn_wrapper(
            q.transpose(1, 2),
            k.transpose(1, 2),
            v.transpose(1, 2),
            dropout_p=0.0,
            causal=False,
            softmax_scale=kwargs.get("scale", -1.0),
        ).transpose(1, 2)
'''
ATTN_NEW = '''    try:
        if mask is not None:
            raise RuntimeError("Mask must not be set for Flash attention")
        _qf = q.transpose(1, 2)
        _kf = k.transpose(1, 2)
        _vf = v.transpose(1, 2)
        _scale = kwargs.get("scale", -1.0)
        # DCU (gfx928) perf patch: the flash kernel's cost grows super-linearly in the
        # query length (S=16278 -> 38 TFLOPS, but four S=4069 chunks -> 101 TFLOPS).
        # Attention is independent per query, so splitting q and letting every chunk
        # attend the full k/v is mathematically exact (bit-identical per row) and
        # ~2.2x faster at H3's sequence length.  Set CK_ATTN_CHUNK=0 to disable.
        _chunk = int(os.environ.get("CK_ATTN_CHUNK", "4096"))
        if _chunk > 0 and _qf.shape[1] > _chunk and _qf.shape[0] == 1:
            out = torch.cat(
                [flash_attn_wrapper(_qf[:, i:i + _chunk].contiguous(), _kf, _vf,
                                    dropout_p=0.0, causal=False, softmax_scale=_scale)
                 for i in range(0, _qf.shape[1], _chunk)],
                dim=1,
            ).transpose(1, 2)
        else:
            out = flash_attn_wrapper(
                _qf, _kf, _vf,
                dropout_p=0.0,
                causal=False,
                softmax_scale=_scale,
            ).transpose(1, 2)
'''
ATTN_IMPORT_OLD = "import json\n"
ATTN_IMPORT_NEW = "import json\nimport os\n"
ATTN_MARK = "DCU (gfx928) perf patch: the flash kernel's cost grows super-linearly"

# ---------------------------------------------------------------------- rope.py
ROPE_OLD = '''    x_norm = torch.nn.functional.rms_norm(
        x,
        (x.shape[-1],),
        weight=scale,
        eps=epsilon,
    )
'''
ROPE_NEW = '''    _d = x.shape[-1]
    # DCU (gfx928) perf patch: ATen's last-dim reduction runs at ~50 GB/s for
    # widths <= 128 (vs ~800 GB/s for >= 160), making F.rms_norm the hottest op
    # in H3 (head_dim == 128).  Computing the mean square as (x*x) @ ones routes
    # the reduction through the matmul kernel instead; ~4.2x faster, <1 bf16 ulp.
    if _d <= 128 and x.dtype in (torch.bfloat16, torch.float16) and x.is_cuda:
        _x2 = x.reshape(-1, _d)
        _ones = torch.ones(_d, 1, dtype=x.dtype, device=x.device)
        _ms = torch.matmul(_x2 * _x2, _ones).reshape(x.shape[:-1] + (1,)) / _d
        x_norm = x * (torch.rsqrt(_ms + epsilon) * scale).to(x.dtype)
    else:
        x_norm = torch.nn.functional.rms_norm(
            x,
            (x.shape[-1],),
            weight=scale,
            eps=epsilon,
        )
'''
ROPE_MARK = "DCU (gfx928) perf patch: ATen's last-dim reduction"

# ------------------------------------------------------------------ samplers.py
SAMP_OLD = '''def sample(model, noise, positive, negative, cfg, device, sampler, sigmas, model_options={}, latent_image=None, denoise_mask=None, callback=None, disable_pbar=False, seed=None):
    cfg_guider = CFGGuider(model)
    cfg_guider.set_conds(positive, negative)
    cfg_guider.set_cfg(cfg)
    return cfg_guider.sample(noise, latent_image, sampler, sigmas, denoise_mask, callback, disable_pbar, seed)
'''
SAMP_NEW = SAMP_OLD + '''

# DCU debug hook: CK_PROFILE=1 dumps a CUDA-time kernel breakdown for the sampling
# loop to /tmp/ck_profile.txt.  Off by default; no effect on normal runs.
_orig_cfgguider_sample = CFGGuider.sample

def _profiled_cfgguider_sample(self, *args, **kwargs):
    import os
    if not os.environ.get("CK_PROFILE"):
        return _orig_cfgguider_sample(self, *args, **kwargs)
    import torch
    with torch.profiler.profile(activities=[torch.profiler.ProfilerActivity.CUDA]) as prof:
        out = _orig_cfgguider_sample(self, *args, **kwargs)
    txt = prof.key_averages().table(sort_by="cuda_time_total", row_limit=45)
    with open("/tmp/ck_profile.txt", "w") as f:
        f.write(txt + "\\n")
    if os.environ.get("CK_PROFILE_TRACE"):
        prof.export_chrome_trace("/tmp/ck_trace.json")
    logging.info("CK_PROFILE written to /tmp/ck_profile.txt")
    return out

CFGGuider.sample = _profiled_cfgguider_sample
'''
SAMP_MARK = "_profiled_cfgguider_sample"

# --------------------------------------------------------------------- model.py
MODEL_OLD = '''            else:
                mod_segments.append((a, b, row_base + seg_tag[kind]))
'''
MODEL_NEW = MODEL_OLD + '''
        if os.environ.get("H3_DEBUG"):
            import logging as _lg
            _lg.info("[H3_DEBUG] seq_len=%d segments=%s mod_segments=%d text_tags=%s",
                     layout.seq_len, [(k, b - a) for a, b, k in layout.segments],
                     len(mod_segments),
                     None if text_tags is None else len(text_tags.view(-1)))
'''
MODEL_IMPORT_OLD = "import math\n\nimport torch\n"
MODEL_IMPORT_NEW = "import math\nimport os\n\nimport torch\n"
MODEL_MARK = "[H3_DEBUG] seq_len="

PATCHES = [
    ("attention.py", ATTN, ATTN_OLD, ATTN_NEW, ATTN_MARK),
    ("attention.py:import os", ATTN, ATTN_IMPORT_OLD, ATTN_IMPORT_NEW, "import json\nimport os\n"),
    ("rope.py", SP, ROPE_OLD, ROPE_NEW, ROPE_MARK),
    ("samplers.py", SAMP, SAMP_OLD, SAMP_NEW, SAMP_MARK),
    ("model.py", MODEL, MODEL_OLD, MODEL_NEW, MODEL_MARK),
    ("model.py:import os", MODEL, MODEL_IMPORT_OLD, MODEL_IMPORT_NEW, "import math\nimport os\n"),
]


def apply_one(name, path, old, new, mark, check):
    if not os.path.exists(path):
        print(f"  [MISS ] {name}: {path} 不存在")
        return "missing"
    src = open(path, encoding="utf-8").read()
    if mark in src:
        print(f"  [SKIP ] {name}: 已打过")
        return "already"
    if old not in src:
        print(f"  [FAIL ] {name}: 找不到原文（镜像版本可能不同），需手工打")
        return "fail"
    if check:
        print(f"  [WOULD] {name}: 可打")
        return "would"
    if not os.path.exists(path + ".dcupatch.bak"):
        shutil.copy2(path, path + ".dcupatch.bak")
    open(path, "w", encoding="utf-8").write(src.replace(old, new, 1))
    print(f"  [OK   ] {name}: 已打（备份 {path}.dcupatch.bak）")
    return "ok"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只检查，不写文件")
    a = ap.parse_args()
    print(f"DCU 调优补丁 {'(dry-run)' if a.check else ''}  {time.strftime('%F %T')}")
    res = {}
    for name, path, old, new, mark in PATCHES:
        res[name] = apply_one(name, path, old, new, mark, a.check)
    ok = sum(1 for v in res.values() if v in ("ok", "already", "would"))
    print(f"\n合计 {ok}/{len(PATCHES)} 可/已应用。"
          f"{'（dry-run，未写盘）' if a.check else ''}")
    if any(v in ("fail", "missing") for v in res.values()):
        print("有补丁失败，请按 DCU调优结论_20260929.md §7 手工处理。")
        sys.exit(1)


if __name__ == "__main__":
    main()
