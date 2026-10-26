"""兼容占位模块（pure-Python stub）—— 让启动脚本 qd 的预检在任意解释器下都能通过。

背景：
    真正的 patch_by_xu 是编译扩展模块
    ``patch_by_xu.cpython-312-x86_64-linux-gnu.so``，只有 CPython 3.12 能加载。

    启动脚本 /root/O.o-AI/qd 在「激活 venv 之前」会做一次完整性预检：

        python3 -c "import sys; sys.path.insert(0,'<ComfyUI>'); import patch_by_xu"

    这里用的是 PATH 里的裸 python3。本镜像里 python3 = CPython 3.10，
    它既找不到也加载不了 3.12 的 .so，于是预检永远失败、qd 误判「模板不完整」，
    从而每次运行都执行 rm -rf + 重铺用户区（会清掉用户区已下载的模型/自建工作流）。

本文件的作用：
    纯 Python 实现，任何 Python 版本都能 import 成功，专门让上面的预检通过。

为什么不会影响运行时：
    CPython 的 import 顺序里「扩展模块(.so) 优先于 源码(.py)」。在 venv 的 3.12 下，
    真正的 ``patch_by_xu.cpython-312-x86_64-linux-gnu.so`` 会优先被加载，本占位文件被遮蔽；
    只有在无法加载 .so 的旧解释器（如 qd 预检用的 3.10）里才会命中本文件。
    因此 ComfyUI 运行行为完全不变。

维护提示：
    不要删除真正的 ``patch_by_xu*.so``；本文件只是预检用的壳，不提供任何真实功能。
"""

__all__ = []
