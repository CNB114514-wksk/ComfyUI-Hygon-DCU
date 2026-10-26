# ComfyUI — Hygon DCU (gfx928) fork

> **Fork notice.** This branch is upstream ComfyUI **v0.38.2** (`daeb5e53`) with the
> Hygon DCU port committed on top — the full source tree, not just diffs.
> Target: **Hygon K100_AI** (`gfx928`, wave64), DTK 26.04, torch 2.7.1+rocm6.3.
> Kernel-level work lives in
> [`comfy-kitchen-Hygon-DCU`](https://github.com/CNB114514-wksk/comfy-kitchen-Hygon-DCU).

## Repo layout

```
ComfyUI/                  upstream tree at daeb5e53 + DCU changes
├── dcu-port/
│   ├── patches/          9 core patches (same changes, replayable on clean upstream)
│   ├── patches-autodownload/  3 patches that need the private hook_by_xu
│   └── scripts/apply.sh  idempotent replay onto a clean checkout
├── *.md                  tuning notes, MMAC port notes, audits (repo root)
├── gfx9_port_0.2.35/     comfy-kitchen gfx9 sources + prebuilt kernels
└── dcu_patch_20260929/   idempotent patch re-application helper
```

Run it the same way as upstream:

```sh
python main.py --listen --enable-cors-header --use-flash-attention \
  --disable-dynamic-vram --enable-triton-backend
```

## Baseline

- **Upstream:** ComfyUI **v0.38.2**, commit `daeb5e53`
- **GPU:** Hygon K100_AI, `gfx928:sramecc+:xnack-`, warpSize 64
- **Toolchain:** DTK **26.04**, torch **2.7.1+rocm6.3**
- **Kernels:** comfy-kitchen **0.2.35** + gfx9 MMAC port

The patches are generated from a working tree at that commit; they apply with
`patch -p1` in numeric order.

## What changed

12 files, **+513 / −116**.

### Core patches — `patches/`

Applied by default. These are self-contained and apply to a clean upstream checkout.

| Patch | File | What it does |
|---|---|---|
| `0001-attention-query-chunking` | `comfy/ldm/modules/attention.py` | Splits the query dimension in `attention_flash`. The flash kernel's cost grows super-linearly with query length (S=16278 → 38 TFLOPS, 4×S=4069 → 101 TFLOPS). Attention is independent per query, so splitting q and attending the full k/v is **mathematically exact** (bit-identical per row). ~**1.42× sampling** on Qwen-Image-2.1 int8. |
| `0002-samplers-ck-profile` | `comfy/samplers.py` | `CK_PROFILE=1` dumps a CUDA-time kernel breakdown of the sampling loop to `/tmp/ck_profile.txt`. Off by default, no effect on normal runs. |
| `0003-model-prefetch` | `comfy/model_prefetch.py` | Per-layer graph-capture validity: with aimdo the malloc graph brackets capture and the VBAR fault signature decides whether a cached graph still matches resident weights; without aimdo (bare graphs) weights never move, so a captured graph stays valid for the life of the model. Also hardens prefetch queue cleanup. |
| `0006-execution` | `execution.py` | When a combo value is not in the options list, retry by basename (case-insensitive) before failing. Lets workflows that reference `model.safetensors` resolve to a catalog entry stored as `org/model.safetensors`. |
| `0007-text-encoder-llama` | `comfy/text_encoders/llama.py` | Capture a graphed layer only when the static decode buffers exist; without aimdo the cached graphs point at this call's KV cache and must not survive into the next `generate()`. |
| `0008-minimax-model` | `comfy/ldm/minimax/model.py` | `H3_DEBUG=1` logs sequence layout, segment lengths and modality segment count for MiniMax H3. Debug only. |
| `0009-lightricks-model` | `comfy/ldm/lightricks/model.py` | Restores the legacy rope helpers (`generate_freq_grid_np` / `generate_freq_grid_pytorch`) removed by the 0.30 rope refactor. `ComfyUI-LTXVideo`'s `embeddings_connector` still calls the old API. Pure functions, independent of the new `freqs_cis_matrix` / `apply_rotary_emb` path. |
| `0011-app-user-manager` | `app/user_manager.py` | Adds the `POST /userdata/{file}/move/{dest}` endpoint (move/rename with overwrite and full-info options) and aligns the surrounding userdata handlers. |
| `0012-websocket-image-save` | `custom_nodes/websocket_image_save.py` | Moves the node to `api/image` and drops the display-name mapping. |

### Auto-download patches — `patches-autodownload/`

**Not applied by default.** They depend on a private `hook_by_xu` module that is
not part of this repo (it resolves a model name against a catalog and downloads
it on first use). Kept separate so the core patch set stays portable.

| Patch | File | What it does |
|---|---|---|
| `0004-folder-paths` | `folder_paths.py` | Imports `hook_by_xu`; adapts aria2c download concurrency (32 threads by default, auto-degrades to 16 when the 5-minute average drops below 30 MiB/s, state in `/tmp/aria2c_speed_state.json`). |
| `0005-server-auto-download` | `server.py` | Admission guard for batch auto-download: only fill "missing models" while a valid workflow is attached, so dirty/API requests cannot trigger a full-catalog pull. |
| `0010-app-model-manager` | `app/model_manager.py` | Surfaces downloaded models in the model-manager listing via `hook_by_xu.import_models2`. |

## Apply

```sh
git clone https://github.com/Comfy-Org/ComfyUI.git
cd ComfyUI && git checkout daeb5e53

# core patches only
../ComfyUI-Hygon-DCU/scripts/apply.sh .

# core + auto-download patches (needs hook_by_xu on PYTHONPATH)
../ComfyUI-Hygon-DCU/scripts/apply.sh --with-autodownload .
```

`apply.sh` refuses to run if the checkout is not at `daeb5e53`.

## Verification

- **Attention chunking** — Qwen-Image-2.1 int8, sampling **1.42×**, per-row output
  bit-identical to the unchunked path.
- **MiniMax H3** — official image-to-video workflow runs end to end; shape and
  segment layout verified with `H3_DEBUG=1`.
- Kernel-level numbers (int8 MMAC GEMM, flash decode, quantized ops) are in the
  companion repo.

Details, measurements and dead ends: see `docs/`.

## Known limitations

- The auto-download patches require `hook_by_xu`; without it `folder_paths` will
  fail to import. Keep them out unless you have that module.
- int4 MMAC (`mmop3`) compiles but **traps on the silicon**; int4 ops fall back to
  int8. See the kitchen repo.
- `CK_PROFILE` and `H3_DEBUG` are environment-gated debug hooks and are not part of
  the normal execution path.

## Docs

| File | Content |
|---|---|
| `docs/DCU调优结论_20260929.md` | Tuning results: attention chunking, rope, sampling profile, benchmark tables |
| `docs/gfx928_mmac_移植笔记.md` | Matrix-core port notes (mmop2/mmop3, wave size, LDS) |
| `docs/DCU卡级问题_静态审计_20260926.md` | Static audit of card-level issues |
| `docs/llamacpp对齐报告_给ComfyUI_20260926.md` | Alignment notes vs. the llama.cpp DCU port |

## License

GPL-3.0, same as upstream. See [LICENSE](LICENSE). The patches are derivative
work of ComfyUI; the upstream copyright notice applies.
