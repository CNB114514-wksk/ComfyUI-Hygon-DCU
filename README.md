# ComfyUI · Hygon DCU (base on o.o-comfyui)

base version： https://www.scnet.cn/ui/aihub/image/scnet_xu/2077623634511740929

A working fork of [ComfyUI](https://github.com/Comfy-Org/ComfyUI) for **Hygon K100_AI**
(`gfx928`). The complete tree is committed, so `git clone` gives you a runnable
install — not a patch stack you have to assemble first.

| | |
|---|---|
| Upstream | ComfyUI **v0.38.2** (`daeb5e53`) |
| GPU | Hygon K100_AI, `gfx928:sramecc+:xnack-`, warpSize 64 |
| Toolchain | DTK **26.04**, torch **2.7.1+rocm6.3** |
| Kernels | [comfy-kitchen-Hygon-DCU](https://github.com/CNB114514-wksk/comfy-kitchen-Hygon-DCU) (gfx9 MMAC port) |

Kernel work lives in that companion repo. This one is the application layer: the
changes needed to make ComfyUI's sampling, graph capture and node runtime behave
on a wave64 DCU.

## Layout

```
.
├── dcu-port/
│   ├── patches/                changes that replay onto a clean upstream checkout
│   ├── patches-autodownload/   model-provisioning patches, need hook_by_xu
│   └── scripts/apply.sh        replay helper, pins daeb5e53
├── gfx9_port_0.2.35/           kitchen gfx9 sources + two prebuilt kernels
├── dcu_patch_20260929/         re-applies the tuning set after an image merge
├── docs / *.md                 tuning notes, MMAC port notes, audits
└── (upstream tree)             unmodified except the files listed below
```

## What was changed

Grouped by what they fix, not by file.

**Sampling throughput.** `attention_flash` splits the query dimension and lets each
chunk attend the full key/value. The flash kernel's cost grows faster than linear
in query length (S=16278 → 38 TFLOPS; four chunks of S=4069 → 101 TFLOPS), and
attention is independent per query, so the split is exact — rows are bit-identical
to the unchunked path. Measured **1.42×** on Qwen-Image-2.1 int8.

**Graph capture correctness.** Prefetch and the Llama text encoder only keep a
captured graph while its buffers are still the ones that were captured. With aimdo
the malloc graph brackets capture and the VBAR fault signature decides reuse;
without it, graphs are dropped between `generate()` calls. Stale graphs were the
source of silent wrong-output runs after a shape change.

**Compatibility.** The legacy rope helpers removed in the 0.30 refactor are back as
pure functions, because `ComfyUI-LTXVideo`'s `embeddings_connector` still calls them.
A missing combo value now retries by basename, so a workflow that says
`model.safetensors` resolves to a catalog entry stored as `org/model.safetensors`.
The websocket save node moved under `api/image`.

**Diagnostics.** `CK_PROFILE=1` writes a kernel-time breakdown of the sampling loop;
`H3_DEBUG=1` logs the MiniMax H3 sequence layout. Both are off by default and sit
outside the normal execution path.

**Model provisioning (optional).** A private `hook_by_xu` module resolves a model
name against a catalog and downloads it on first use, with adaptive aria2c
concurrency and a guard that stops dirty requests from pulling the whole catalog.
Those patches are kept separate because the module is not in this repo.

## Run

```sh
git clone https://github.com/CNB114514-wksk/ComfyUI-Hygon-DCU.git
cd ComfyUI-Hygon-DCU
pip install -r requirements.txt

python main.py --listen --enable-cors-header --use-flash-attention \
  --disable-dynamic-vram --enable-triton-backend
```

Weights go under `models/` as usual. If `hook_by_xu` is present, the catalog in
`source.json` / `source-community.json` fills them on first use instead.

To move these changes onto a clean upstream checkout instead of using this tree:

```sh
git clone https://github.com/Comfy-Org/ComfyUI.git
git -C ComfyUI checkout daeb5e53
dcu-port/scripts/apply.sh ComfyUI
```

## Verified

- **Qwen-Image-2.1 int8** — sampling 1.42× faster, per-row output identical to the
  unchunked path.
- **MiniMax H3** — official image-to-video workflow runs end to end; layout checked
  with `H3_DEBUG=1`.
- **int8 MMAC kernels** — numbers and caveats in the kitchen repo.

Measurements, failed attempts and the reasoning behind each change are in the
root-level notes.

## Limits

- gfx9 only. The AMD WMMA paths for gfx11/gfx12 are untouched and untested here.
- int4 MMAC (`mmop3`) compiles but traps on the silicon; int4 ops fall back to int8.
- The provisioning patches need `hook_by_xu`; without it `folder_paths` will not
  import, so use the core set only.
- Third-party `custom_nodes` are not vendored — install them yourself.
- `models/`, `user/`, `input/`, `output/` are gitignored; this repo carries code, not
  data.

## Related

- [comfy-kitchen-Hygon-DCU](https://github.com/CNB114514-wksk/comfy-kitchen-Hygon-DCU) — gfx9 kernel backend
- [DeepInfer-hygon-DCU](https://github.com/CNB114514-wksk/DeepInfer-hygon-DCU) — inference engine port
- [llama.cpp-Hygon-DCU](https://github.com/CNB114514-wksk/llama.cpp-Hygon-DCU) — llama.cpp port

## License

GPL-3.0, inherited from upstream. See [LICENSE](LICENSE).
