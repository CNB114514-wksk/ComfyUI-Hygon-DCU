import logging
import os
import threading
import warnings
import weakref

import comfy_kitchen as ck
import torch

import comfy_aimdo.malloc_graph
import comfy_aimdo.model_vbar
from comfy.cli_args import args
import comfy.memory_management
import comfy.model_management
import comfy.ops

PREFETCH_QUEUES = []
GRAPH_WARMED_MODULES = weakref.WeakSet()
GRAPH_CAPTURE_STREAMS = {}
MALLOC_GRAPHS = {}
MALLOC_GRAPH_BREAKS = 0
MALLOC_GRAPH_ROGUES = 0
MALLOC_GRAPH_USED = False

def _malloc_graph_break():
    global MALLOC_GRAPH_BREAKS
    MALLOC_GRAPH_BREAKS += 1
    logging.debug("Comfy model compiler graph break")

def malloc_graph_enabled(device):
    return not args.disable_comfy_compiler and comfy.memory_management.aimdo_enabled and comfy.model_management.is_device_cuda(device)

def cuda_graphs_usable(device):
    """Whether CUDA graphs can be captured without the comfy-aimdo allocator.

    The Comfy model compiler normally rides on aimdo: its malloc graph brackets
    the capture and each per-layer graph is keyed by a VBAR fault signature so it
    is only replayed while the same weights are resident. On a device aimdo cannot
    drive (its VBAR path needs a working virtual-address reservation) there is no
    VBAR and nothing to bracket -- but then the weights are also pinned in place
    for good, so a captured graph stays valid and the allocator hooks are simply
    skipped. ``COMFY_DCU_CUDA_GRAPHS=0`` opts back out.
    """
    if os.environ.get("COMFY_DCU_CUDA_GRAPHS", "1") == "0":
        return False
    return (not args.disable_comfy_compiler and not args.disable_cuda_graphs
            and comfy.model_management.is_device_cuda(device))


class _PauseMallocGraph:
    def __init__(self, sync=False):
        self.sync = sync

    def __enter__(self):
        graph = MALLOC_GRAPHS.get(threading.get_ident())
        if graph is not None and graph._comfy_active:
            graph.pause(sync=self.sync)

    def __exit__(self, *args):
        graph = MALLOC_GRAPHS.get(threading.get_ident())
        if graph is not None and graph._comfy_active:
            graph.resume(sync=self.sync)

def pause_malloc_graph(sync=False):
    return _PauseMallocGraph(sync)

class _MallocGraphScope:
    def __init__(self, device):
        self.device = device

    def __enter__(self):
        malloc_graph_begin(self.device)

    def __exit__(self, exc_type, *args):
        if exc_type is None:
            malloc_graph_end()
        else:
            cleanup_malloc_graph()

def malloc_graph_scope(device):
    return _MallocGraphScope(device)

def malloc_graph_begin(device):
    global MALLOC_GRAPH_USED
    if not malloc_graph_enabled(device):
        return
    thread_id = threading.get_ident()
    graph = MALLOC_GRAPHS.get(thread_id)
    if graph is None:
        graph = comfy_aimdo.malloc_graph.record(
            comfy.model_management.current_stream(device), args.assert_graph_breaks
        )
        graph._comfy_cuda_graph_modules = weakref.WeakSet()
        MALLOC_GRAPHS[thread_id] = graph
    else:
        graph.push()
    if hasattr(ck, "set_allocation_context"):
        ck.set_allocation_context(pause_malloc_graph())
    graph._comfy_active = True
    MALLOC_GRAPH_USED = True

def malloc_graph_end():
    thread_id = threading.get_ident()
    graph = MALLOC_GRAPHS.get(thread_id)
    if graph is not None and graph._comfy_active:
        if graph.pop():
            _malloc_graph_break()
        graph._comfy_active = False

def cleanup_malloc_graph():
    global MALLOC_GRAPH_ROGUES

    graph = MALLOC_GRAPHS.pop(threading.get_ident(), None)
    if graph is not None:
        if graph._comfy_active:
            graph.abort()
            graph._comfy_active = False
        for module in graph._comfy_cuda_graph_modules:
            _drop_graph(module)
        MALLOC_GRAPH_ROGUES += graph.rogue_count
        del graph

def pin_modules(comfy_modules, device, dtype=None):
    registerable_size = 0
    for s in comfy_modules:
        registerable_size += comfy.memory_management.vram_aligned_size([s.weight, s.bias])
        for param_key in ("weight", "bias"):
            lowvram_fn = getattr(s, param_key + "_lowvram_function", None)
            if lowvram_fn is not None:
                registerable_size += lowvram_fn.memory_required()

    offload_stream, fully_faulted = comfy.ops.cast_modules_with_vbar(comfy_modules, None, device, None, True, return_faulted=True)
    if not (comfy_modules and comfy_modules[0]._pin_state["fast_disk"]):
        comfy.model_management.ensure_pin_registerable(registerable_size)
    comfy.model_management.sync_stream(device, offload_stream)
    if fully_faulted and dtype is not None:
        for comfy_module in comfy_modules:
            comfy.ops.resolve_cast_module_with_vbar(comfy_module, dtype, device, dtype, None, False, return_weights=False)
    return offload_stream, fully_faulted

def cleanup_prefetched_modules(module, comfy_modules):
    for s in comfy_modules:
        prefetch = getattr(s, "_prefetch", None)
        if prefetch is None:
            continue
        for param_key in ("weight", "bias"):
            lowvram_fn = getattr(s, param_key + "_lowvram_function", None)
            if lowvram_fn is not None:
                lowvram_fn.clear_prepared()
        if prefetch["signature"] is not None:
            comfy_aimdo.model_vbar.vbar_unpin(s._v)
        delattr(s, "_prefetch")
    if getattr(module, "_v_block_faulted", False):
        comfy_aimdo.model_vbar.vbar_unpin(module._v_block)
        del module._v_block_faulted

def _drop_graph(module):
    graph = getattr(module, "_comfy_graph", None)
    if graph is None:
        return
    # reset() through the bound method surfaces the allocator's benign
    # "uncaptured free of a captured allocation" as catchable Python warnings;
    # a plain del frees from the C++ dealloc path and spams stderr instead
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        graph["graph"].reset()
    del module._comfy_graph

def reset_graphs(modules):
    """Drop graphs cached on modules whose static inputs are rebuilt per call.

    With aimdo the cached per-layer graphs are torn down with the malloc graph at
    the end of a run, and a VBAR signature check guards the ones that survive. The
    bare (no-aimdo) graphs instead point straight at the KV cache and decode
    buffers, which every generate() call allocates afresh -- replaying a graph from
    a previous call would read freed memory. So they are dropped here, and the
    modules are unwarmed so the next run re-warms and re-captures.
    """
    for module in modules:
        _drop_graph(module)
    GRAPH_WARMED_MODULES.clear()

def cleanup_prefetch_queues():
    global PREFETCH_QUEUES
    global MALLOC_GRAPH_BREAKS
    global MALLOC_GRAPH_ROGUES
    global MALLOC_GRAPH_USED

    cleanup_malloc_graph()
    for queue in PREFETCH_QUEUES:
        for entry in queue:
            if entry is None or not isinstance(entry, tuple):
                continue
            _, prefetch_state = entry
            prefetched_module, comfy_modules = prefetch_state
            if comfy_modules is not None:
                cleanup_prefetched_modules(prefetched_module, comfy_modules)
    PREFETCH_QUEUES = []
    GRAPH_WARMED_MODULES.clear()
    if MALLOC_GRAPH_USED:
        logging.info("Comfy model compiler graph breaks: %d, rogues: %d", MALLOC_GRAPH_BREAKS, MALLOC_GRAPH_ROGUES)
    MALLOC_GRAPH_BREAKS = 0
    MALLOC_GRAPH_ROGUES = 0
    MALLOC_GRAPH_USED = False

def prefetch_queue_pop(queue, device, module, dtype=None, core=None, enable_graph=False, generator=None, malloc_scope=None, allow_bare_graph=False):
    malloc_graph = MALLOC_GRAPHS.get(threading.get_ident())
    if malloc_graph is not None and not malloc_graph._comfy_active:
        malloc_graph = None
    vbar = getattr(module, "_v_block", None)
    # Two ways to have a valid per-layer graph. With aimdo the malloc graph brackets
    # the capture and the VBAR fault signature decides whether a cached graph still
    # matches the resident weights. Without aimdo (bare_graphs) there is no VBAR, so
    # the weights never move and a captured graph is valid for the life of the model.
    # bare_graphs is opt-in per call site: it is only correct where the caller keeps
    # the layer input in a static buffer (see the decode_buffers path in llama.py).
    aimdo_graphs = malloc_graph is not None and vbar is not None
    bare_graphs = allow_bare_graph and malloc_graph is None and vbar is None and cuda_graphs_usable(device)
    enable_graph = enable_graph and (aimdo_graphs or bare_graphs)
    if queue is None:
        if malloc_graph is not None and malloc_scope is not None:
            if malloc_graph.iterate(malloc_scope if module is not None else None):
                _malloc_graph_break()
        if core is not None:
            core()
        return

    capture_stream = None
    if enable_graph:
        capture_stream = GRAPH_CAPTURE_STREAMS.get(device)
        if capture_stream is None:
            capture_stream = torch.cuda.Stream(device=device)
            # Keep PyTorch's persistent BLAS workspaces outside the allocation graph.
            if malloc_graph is not None:
                malloc_graph.pause()
            with torch.cuda.stream(capture_stream):
                torch.cuda.current_blas_handle()
                one = torch.empty((2, 2), device=device)
                torch.addmm(one[0], one, one)
            if malloc_graph is not None:
                malloc_graph.resume()
            GRAPH_CAPTURE_STREAMS[device] = capture_stream

    signature = None
    graph_hit = False
    graph = getattr(module, "_comfy_graph", None) if enable_graph else None
    if graph is not None:
        if vbar is not None:
            signature = comfy_aimdo.model_vbar.vbar_fault(vbar)
            if signature is not None:
                module._v_block_faulted = True
                graph_hit = comfy_aimdo.model_vbar.vbar_signature_compare(signature, graph["signature"])
        else:
            # no VBAR to fault: the weights are resident, so the graph always applies
            graph_hit = True

    if malloc_graph is not None and malloc_scope is not None:
        if malloc_graph.iterate(malloc_scope if module is not None and not graph_hit else None):
            _malloc_graph_break()

    consumed = queue.pop(0)
    if consumed is not None:
        offload_stream, prefetch_state = consumed
        if offload_stream is not None:
            offload_stream.wait_stream(comfy.model_management.current_stream(device))
        prefetched_module, comfy_modules = prefetch_state
        if comfy_modules is not None:
            cleanup_prefetched_modules(prefetched_module, comfy_modules)

    if graph_hit:
        queue[0] = (None, (module, []))
        if os.environ.get("COMFY_DCU_CUDA_GRAPHS_DEBUG"):
            print("GRAPH replay", type(module).__name__, flush=True)
        graph["graph"].replay()
        return

    fully_faulted = False
    prefetch = queue[0]
    if prefetch is not None:
        comfy_modules = []
        prefetch_modules = prefetch if isinstance(prefetch, (list, tuple)) else (prefetch,)
        for root in prefetch_modules:
            for s in root.modules():
                if hasattr(s, "_v"):
                    comfy_modules.append(s)

        offload_stream, fully_faulted = pin_modules(comfy_modules, device, dtype)
        queue[0] = (offload_stream, (module, comfy_modules))

    if core is not None:
        capture_ready = (enable_graph and module in GRAPH_WARMED_MODULES
                         and not getattr(module, "_comfy_graph_disabled", False)
                         and (fully_faulted or bare_graphs))
        if capture_ready:
            if signature is None and vbar is not None:
                signature = comfy_aimdo.model_vbar.vbar_fault(module._v_block)
                if signature is not None:
                    module._v_block_faulted = True
            if signature is not None or bare_graphs:
                try:
                    _drop_graph(module)
                    if malloc_graph is not None:
                        malloc_graph.pause()
                    graph = torch.cuda.CUDAGraph()
                    if generator is not None:
                        graph.register_generator_state(generator)
                    if malloc_graph is not None:
                        malloc_graph.resume()
                    # Capture-time VBAR eviction is safe after prior work completes.
                    comfy.model_management.synchronize()
                    capture_stream.wait_stream(comfy.model_management.current_stream(device))
                    if malloc_graph is not None:
                        malloc_graph.pause(sync=True)
                        stream_ctx = malloc_graph.use_stream(capture_stream)
                    else:
                        stream_ctx = torch.cuda.stream(capture_stream)
                    with stream_ctx:
                        with torch.cuda.graph(graph, stream=capture_stream, capture_error_mode="thread_local"):
                            if malloc_graph is not None:
                                malloc_graph.resume()
                            core()
                            if malloc_graph is not None:
                                malloc_graph.pause()
                    if malloc_graph is not None:
                        malloc_graph.resume(sync=True)
                    comfy.model_management.current_stream(device).wait_stream(capture_stream)
                    graph.replay()
                    module._comfy_graph = {"graph": graph, "signature": signature}
                    if malloc_graph is not None:
                        malloc_graph._comfy_cuda_graph_modules.add(module)
                    if os.environ.get("COMFY_DCU_CUDA_GRAPHS_DEBUG"):
                        print("GRAPH capture", type(module).__name__, flush=True)
                    return
                except Exception as e:
                    # A device or op that cannot be captured must not take the whole
                    # run down: drop the half-built graph and fall through to eager.
                    logging.warning("CUDA graph capture failed, falling back to eager: %s", e)
                    if malloc_graph is not None:
                        malloc_graph.resume(sync=True)
                    _drop_graph(module)
                    module._comfy_graph_disabled = True
                    comfy.model_management.current_stream(device).wait_stream(capture_stream)
        if capture_stream is None:
            core()
        else:
            capture_stream.wait_stream(comfy.model_management.current_stream(device))
            if malloc_graph is not None:
                stream_ctx = malloc_graph.use_stream(capture_stream)
            else:
                stream_ctx = torch.cuda.stream(capture_stream)
            with stream_ctx:
                core()
            comfy.model_management.current_stream(device).wait_stream(capture_stream)
            GRAPH_WARMED_MODULES.add(module)


def make_prefetch_queue(queue, device, transformer_options):
    if (not transformer_options.get("prefetch_dynamic_vbars", False)
        or comfy.model_management.NUM_STREAMS == 0
        or comfy.model_management.is_device_cpu(device)
        or not comfy.model_management.device_supports_non_blocking(device)):
        return None

    queue = [None] + queue + [None]
    PREFETCH_QUEUES.append(queue)
    return queue
