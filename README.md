# 国家超算互联网平台白嫖 GPU 运行 ComfyUI+Openclaw 指南
# Scnet ComfyUI baipiao Guide

[图文版教学](https://cnb.cool/comfyui114514/Scnet_Comfyui_Guide) [github guide(eng)](https://github.com/cnb114514/Scnet_Comfyui_Guide) 

## 📑 目录

- [准备](#准备)
- [1. 注册账号](#1-注册账号)
- [2. 白嫖资源](#2-白嫖资源)
- [3. 用社区镜像创建 Notebook容器](#3-用社区镜像创建-notebook容器)
- [4. 文件扩容](#4-文件扩容)
- [5. 访问 Linux 系统](#5-访问-linux-系统)
- [6. 启动 ComfyUI 后端程序](#6-启动-comfyui-后端程序)
- [7. 启动 ComfyUI 前端网页](#7-启动-comfyui-前端网页)
- [8. 关于模型下载](#8-关于模型下载)
- [9. ComfyUI 的正常操作](#9-comfyui-的正常操作)
- [10. 白嫖的 token 使用](#10-白嫖的-token-使用)
- [11. 问题反馈](#11-问题反馈)
- [12. 容器版本教学](#12-容器版本教学)
- [12.1 高级-创建镜像（保存自定义镜像））](#121-高级-创建镜像保存自定义镜像)
- [13. 命令合集（一键快捷指令）](#13-命令合集一键快捷指令)

> 感谢 CNB 平台大佬 **cnb-xu**（又名 O.o）的开发，方便各位在国家投资的平台（十万张国产 GPU）上运行 ComfyUI。实测 海光bw 64gb显卡在没有任何加速的情况下，fp8效率为h20的1/4

> **提示**：部分 N 卡专用功能以及 LLM 暂不支持。

> **提示**：笔者并未测试过ssh方案，以下内容仅供参考。

## 准备

- **方案 A（推荐）**：一台能访问浏览器的电脑
  - 无需任何其他准备
- **方案 B**：如果通过通用云端 SSH 部署，请先安装以下两个文件到 Windows（适用于各种云平台的通用方案，例如仙宫云版本 O.o ComfyUI 镜像）：
  - 两个文件安装一下，安装向导里能勾选的功能都勾上即可
  - [Icon.installericon.exe（PuTTY 安装包）](应用/Icon.installericon.exe)
  - [WinSCP-6.5.6-Setup.exe](应用/WinSCP-6.5.6-Setup%20(1).exe)

。
## 镜像
- 镜像分为  # 纯净版：o.o-comfyui #  ||  # 预装版：o.o-comfyui-withopenclaw #
- 目前纯净版截止0.30版本不支持容器实例，预装版截止3.2dev版本，预装了插件和工作流，兼容notebook和容器，但是可能存在不稳定性
- [原版链接](https://www.scnet.cn/ui/aihub/image/scnet_xu/2077623634511740929) [预装版链接](https://www.scnet.cn/ui/aihub/image/comfyui114514/2078319083724169218/versions1)

——————————————————————————————————————————————

## 步骤

### 1. 注册账号

如果后续需要实名，就实名一下。

👉 [注册账号链接](https://www.scnet.cn/sso/register?service=https%3A%2F%2Fwww.scnet.cn%2Fac%2Fapi%2Fauth%2FloginSsoRedirect.action%3ForiginalUrl%3Dhttps%253A%252F%252Fwww.scnet.cn%252Fhome%252Fsubject%252Fhxjd%252Findex.html%253Fshow%253Dtrue%2526marketActivityId%253DgpQZWR9H%2526inviterId%253D11263962531)

——————————————————————————————————————————————

### 2. 白嫖资源

- 领取百万 token（7.17 当前为一个月的 kimi-2.6）：👉 [领取千万 token](https://www.scnet.cn/home/subject/hxjd/index.html)
- 领取国产 GPU（三个月）：👉 [领取国产 GPU](https://www.scnet.cn/ui/mall/search/resource?region=20091)

> **注意**：看到试用都能领，不过本教学用到的是 **BW1 64GB**。notebook有100小时bw，容器实例有3种dcu各100小时。

<img src="https://cnb.cool/comfyui114514/Scnet_Comfyui_Guide/-/git/raw/main/图片/img2.png" alt="img2" width="700">

<sub>（步骤2图片）</sub>

——————————————————————————————————————————————

### 3. 用社区镜像创建 Notebook容器

管理界面（即人工智能）：👉 [notebook网页](https://www.scnet.cn/ui/console/index.html#/notebook?notebookStatus=Running)

操作流程：

***创建 Notebook → 选择64gb显存的bw主机 → 社区镜像 → 搜索 o.o-comfyui  → 选择最新的版本 → 部署***

> <sub>作者通道 [O.o-comfyui原版镜像库链接](https://www.scnet.cn/ui/aihub/image/scnet_xu/2077623634511740929) [O.o-comfyui-withopenclaw社区版镜像库链接](https://www.scnet.cn/ui/aihub/image/accma5g3vg/2078319083724169218)</sub>



> **提示**：每次启动可以运行 **72h**，操作完下一步 4文件扩容 可以保存关机！




<img src="https://cnb.cool/comfyui114514/Scnet_Comfyui_Guide/-/git/raw/main/图片/img3.png" alt="img3" width="700">

<sub>（步骤3图片）<sub>

> 等待启动完成……

——————————————————————————————————————————————

### 4. 文件扩容

平台**默认只给一台机器分配 500GB 空间**，但需要手动设置一下文件夹配额。

👉 [存储管理链接](https://www.scnet.cn/ui/console/index.html#/my-product/basic-resources/storage_resource)

操作步骤：

- 进入存储管理页面，点击 **扩容**；
- **用户主目录**：默认只有 50GB，改成 **450GB**；
- **共享目录**：设置为 **50GB**。

> <sub>共享目录暂时不清楚是干什么用的，先按 50GB 设置即可。</sub>

——————————————————————————————————————————————

### 5. 访问 Linux 系统

访问方式有两种：

- **方案 A（推荐）**：人工智能 Notebook 网页 JupyterLab 直接登录 👉 [JupyterLab 登录入口](https://www.scnet.cn/ui/console/index.html#/notebook)
- **方案 B（SSH）**：在人工智能页面，WinSCP 输入登录指令、密码、端口，直接连接机器。

> SSH 方法通用性强，可适用于各种云平台都玩的老资历。记得在「选项设置 → 应用设置」里保存密码，WinSCP 传输密码给 PuTTY，启动 ComfyUI 时就不用重复输入密码。

<img src="https://cnb.cool/comfyui114514/Scnet_Comfyui_Guide/-/git/raw/main/图片/img5a.png" alt="img5a" width="700">

<sub>（步骤5-A 步骤7-AB 图片）</sub>

<img src="https://cnb.cool/comfyui114514/Scnet_Comfyui_Guide/-/git/raw/main/图片/img1.png" alt="img1" width="700">

<sub>（步骤5-B图片）</sub>

——————————————————————————————————————————————

### 6. 启动 ComfyUI 后端程序

访问 Linux 后，进入终端，输入 `qd` 回车（即 `/root/O.o-ai/qd` 的快捷方式）。

> **注意**：2.4以下的镜像版本ComfyUI 本体的文件主目录并不在 `root` 的 `comfyui`，而是在 `private_data`，其下方才是 `comfyui`。2.4以上privatedata作为模型持久化目录

等待启动完成……可看到 **8188** 本地端口已创建。

——————————————————————————————————————————————

### 7. 启动 ComfyUI 前端网页

访问方案有三种：

- **方案 A（推荐）**：执行完 5 和 6 后，在人工智能 Notebook 网页，容器右侧「访问自定义服务：8188」弹出隧道网页。
- **方案 B**：未执行 5 和 6，直接访问 自定义服务🔧（端口：8188，启动命令：`/root/O.o-ai/qd`）弹出隧道网页。
- **方案 C（SSH）**：执行完 5 和 6 后，通过 PuTTY 会把云端的本地端口映射为自己的本地端口，直接访问固定地址 👉 http://0.0.0.0:8188

<img src="https://cnb.cool/comfyui114514/Scnet_Comfyui_Guide/-/git/raw/main/图片/img7.png" alt="img7" width="700">

<sub>（步骤7图片）</sub>

——————————————————————————————————————————————

### 8. 关于模型下载

此镜像基于 cnb-xu 开发的自动下载方案：如果模型 Loader 节点下拉存在模型名字，运行工作流时会自动下载，速度 30–100 MB/s 不等。

- **方案 A（推荐!自定义下载）**：使用o.o-comfyui-withopenclaw社区镜像后，打开 `private_data/comfyui/自定义下载.yaml`，根据示例自己添加下载链接
- **方案 B（传统下载）**：选择 `private_data/comfyui/models`，进入对应模型类型的目录打开终端，用 `curl -L -OJ` 下载自己想跑的 CNB 模型。
- **方案 C（自动下载）**：直接打开工作流看看下拉菜单有没有模型，运行工作流即可。
- **方案 D（搬运自动下载）**：编辑 `private_data/comfyui/source.json`，把下载链接添加进去，或者添加本仓库里的两个文件，即可把 CNB 的社区收录搬运过去。👉 [aimodels包](https://cnb.cool/comfyui114514/Scnet_Comfyui_Guide/-/blob/main/cnb%E6%A8%A1%E5%9E%8B%E4%B8%8B%E8%BD%BD%E6%96%87%E4%BB%B6%EF%BC%88%E6%8B%96%E5%85%A5comfyui%E7%9B%AE%E5%BD%95%EF%BC%89/source.json)
👉 [社区包](https://cnb.cool/comfyui114514/Scnet_Comfyui_Guide/-/blob/main/cnb%E6%A8%A1%E5%9E%8B%E4%B8%8B%E8%BD%BD%E6%96%87%E4%BB%B6%EF%BC%88%E6%8B%96%E5%85%A5comfyui%E7%9B%AE%E5%BD%95%EF%BC%89/source-community.json)
- **方案 E（添加下载链接）**：终端输入 `ui`，再去人工智能 Notebook 网页，自定义端口改成 `7860`，就能在网页交互式下载模型。
- **方案 F（本地上传）**：直接拖拽上传到 JupyterLab 或 WinSCP，后者支持断点续传。

> 模型下载链接的获取支持 HuggingFace、CNB、ModelScope。

——————————————————————————————————————————————

### 9. ComfyUI 的正常操作

ComfyUI 的正常操作这里不再赘述，如果遇到问题可以问 AI，也可用白嫖的 token 新建 API 导入到 OpenClaw，让 AI 帮你解决问题。

——————————————————————————————————————————————

### 10. 白嫖的 token 使用

- **方案 A**：直接下载 scnet 的 Windows app，可免费调用 `scnet-max` / `kimi-2.6` 两种模型。
- **方案 B**：使用预装 openclaw 环境版本镜像 `O.o-comfyui-withopenclaw`，然后按下面操作：

  - 获取 API（需要先领取 kimi-2.6 token）：👉 [创建 apikey](https://www.scnet.cn/ui/console/index.html#/llm/apikeys)
  - 终端执行 `bash /root/setup_openclaw.sh` → 输入 api → 选择模型 → 回车。

——————————————————————————————————————————————

### 11. 问题反馈

- **渠道 1**：装完 openclaw 自己问。
- **渠道 2**：来 cnb 文档仓库的 issue 反馈 👉 [Scnet_Comfyui_Guide 仓库](https://cnb.cool/comfyui114514/Scnet_Comfyui_Guide) | [Issues 列表](https://cnb.cool/comfyui114514/Scnet_Comfyui_Guide/-/issues)
- **渠道 3**：加镜像作者 cnb-xu 的微信群 👉 [**群二维码**](https://cnb.cool/cnb-xu/docs/-/git/raw/main/comfyui/image/qrcode.png)

###### *cnb白嫖人，跑路！*

——————————————————————————————————————————————

### 12. 容器版本教学


**入口**：控制台 → 容器服务 → 容器实例 👉 [容器实例页面](https://www.scnet.cn/ui/console/index.html#/container)

操作流程概览：

1. 进入 **容器服务 → 容器实例**，点击「新建容器实例」；
2. 选择 **资源/队列**（如 `hx1hdnormal` 异构加速卡 BW/64GB）；
3. 选择 **开发镜像**：`O.o-comfyui-xu` → 版本 `v1.0.0`（或 `0.0-comfyui-xu-rongqi`）；
4. 配置 **实例数量 / 每实例加速卡数量**；
5. 高级配置里设置 **服务端口**：`8188`（HTTP）、`7860`（HTTP）；
6. 确认资源配置（如 16 核 / 59GB 内存 / 1 加速卡），运行时限 72 小时，提交创建。

> **注意**：容器版本存储和镜像是分离开的，public用户目录下才会持久化，但是不会保存到镜像，private路径要保存请在关机前保存为镜像

下面以截图形式完整演示**创建容器实例**的每一步操作（截图来自「SCNet创建容器实例」文档）：

<img src="https://cnb.cool/comfyui114514/Scnet_Comfyui_Guide/-/git/raw/main/图片/img20.png" alt="创建容器实例-1" width="700">

<sub>（步骤12-1 控制台入口：人工智能 / 容器服务 / 网络服务等导航）</sub>

<img src="https://cnb.cool/comfyui114514/Scnet_Comfyui_Guide/-/git/raw/main/图片/img21.png" alt="创建容器实例-2" width="700">

<sub>（步骤12-2 Notebook 列表，可切换至容器实例入口）</sub>

<img src="https://cnb.cool/comfyui114514/Scnet_Comfyui_Guide/-/git/raw/main/图片/img22.png" alt="创建容器实例-3" width="700">

<sub>（步骤12-3 容器实例页面，暂无数据，点击新建）</sub>

<img src="https://cnb.cool/comfyui114514/Scnet_Comfyui_Guide/-/git/raw/main/图片/img23.png" alt="创建容器实例-4" width="700">

<sub>（步骤12-4 资源选择：队列与加速卡型号/显存）</sub>

<img src="https://cnb.cool/comfyui114514/Scnet_Comfyui_Guide/-/git/raw/main/图片/img24.png" alt="创建容器实例-5" width="700">

<sub>（步骤12-5 选择镜像 O.o-comfyui-xu 及版本）</sub>

<img src="https://cnb.cool/comfyui114514/Scnet_Comfyui_Guide/-/git/raw/main/图片/img25.png" alt="创建容器实例-6" width="700">

<sub>（步骤12-6 高级配置：服务端口 8188 / 7860 与资源配置）</sub>

<img src="https://cnb.cool/comfyui114514/Scnet_Comfyui_Guide/-/git/raw/main/图片/img14.png" alt="img14" width="700">

<sub>（步骤12-7 提交创建后实例启动 / 运行详情）</sub>

——————————————————————————————————————————————

> **注意**：容器实例关机后privatedata的数据会转移到public/（用户名）下，暂时还没有更方便的持久化方案

> ===================================================


### 12.1 高级-创建镜像（保存自定义镜像）

> **注意**：插件改动跨容器保存必须保存镜像！镜像保存只保存系统盘的数据！不保存用户数据！

> **注意**：保存路径 root/

> **注意**：notebook用户路径 root/privatedata 或 public/home/用户名 (二者相同)

> **注意**：容器实例16gb的显卡用户路径不同 work/home/用户名

 本步骤讲解如何在国家超算互联网平台（SCNet）上**拉取社区镜像**与**保存为自定义镜像**，方便后续快速复用环境、上传镜像到社区

* 拉取镜像操作流程概览（附图）：

1. 进入容器管理界面，找到正在运行的实例；
2. 点击「创建镜像 / 保存镜像」，填写镜像名称与版本；
3. 等待镜像构建完成；
4. 在「我的镜像」中确认镜像已生成；
5. 后续新建容器时可直接选用该自定义镜像。

* 保存镜像操作流程（无图）
1. 在文件管理器或终端 把 root/ 下的原镜像内容删掉
2. 在终端或者文件管理器把 public/home/用户名 或 root/privatedata  或 work/home/用户名 的数据复制到root/ 
3. 在  [容器实例页面](https://www.scnet.cn/ui/console/index.html#/container)  或 [notebook网页](https://www.scnet.cn/ui/console/index.html#/notebook?notebookStatus=Running) 选择你当前运行的容器，更多-保存镜像-填写镜像名称与版本；


<img src="https://cnb.cool/comfyui114514/Scnet_Comfyui_Guide/-/git/raw/main/图片/img15.png" alt="创建镜像-步骤1" width="700">

<sub>（步骤 12.1-1 容器列表，进入实例详情）</sub>

<img src="https://cnb.cool/comfyui114514/Scnet_Comfyui_Guide/-/git/raw/main/图片/img16.png" alt="创建镜像-步骤2" width="700">

<sub>（步骤 12.1-2 点击创建镜像，填写名称与版本）</sub>

<img src="https://cnb.cool/comfyui114514/Scnet_Comfyui_Guide/-/git/raw/main/图片/img17.png" alt="创建镜像-步骤3" width="700">

<sub>（步骤 12.1-3 提交后镜像构建中）</sub>

<img src="https://cnb.cool/comfyui114514/Scnet_Comfyui_Guide/-/git/raw/main/图片/img18.png" alt="创建镜像-步骤4" width="700">

<sub>（步骤 12.1-4 镜像构建完成提示）</sub>

<img src="https://cnb.cool/comfyui114514/Scnet_Comfyui_Guide/-/git/raw/main/图片/img19.png" alt="创建镜像-步骤5" width="700">

<sub>（步骤 12.1-5 在「我的镜像」中查看已保存的镜像）</sub>


——————————————————————————————————————————————

### 13. 命令合集（一键快捷指令）

预装版 `O.o-comfyui-withopenclaw` 镜像后，终端里直接敲下面这些指令即可, 纯净版会缺少前两个命令

| 指令 | 作用说明 |
| :--- | :--- |
| `bash /root/setup_hermes.sh` |  预装版命令⬆️ 首次使用请先执行 `bash /root/setup_hermes.sh`，按提示填入 scnet API 与模型，即可完成 OpenClaw 的环境配置。
| `bash /root/setup_openclaw.sh` | 预装版命令⬆️ 首次使用请先执行 `bash /root/setup_openclaw.sh`，按提示填入 scnet API 与模型，即可完成 OpenClaw 的环境配置。
| `hermes` | 🚀启动hermes (需o.o-comfyui 0.30以上)
| `openclaw` | 🚀启动openclaw (同上)
| `qd` | 🚀 启动comfyui（端口8188）
| `qdcpu` | 🚀 无卡模式下备用的cpu启动comfyui（端口8188）
| `ui` | 🖥️ 启动交互模型下载器（端口7860） |
| `update` | ⬆️ 升级comfyui，推荐询问openclaw操作以保留魔改代码 |
| chown -R acw8nw1afo /public/home/acw8nw1afo/ComfyUI/models | （自己改用户路径）修复部分文件读写bug |


> 💡 提示：以上指令均为镜像内置的快捷方式，建议在已完成 [步骤 5 访问 Linux 系统](#5-访问-linux-系统) 的终端中使用。

——————————————————————————————————————————————
###### *cnb白嫖人，跑路！*

# 更新日志
    **2026.08-26** 新增minimax h3生态插件与加速；新增no cache启动命令防止RAM爆；cnb已移除32线程下载支持（改16线程）
    **2026.08-06**  o.o-comfyui-withopenclaw-3.2 解决notebook，容器实例两种环境的自动兼容问题，现在可以无感重启系统持久化目录
    **2026.08-03** （已删除）o.o-comfyui-withopenclaw-3.0 修复2.4因驱动丢失开始无法启动comfy，更新comfy到0.30，新增minimax h3工作流 ，已知问题：1. ltxv插件未适配0.30，等待插件官方更新 2. 容器实例持久化需要手动备份数据到public再重启 3. 软链接models文件夹丢失
    **2026.07-27** （已删除）o.o-comfyui-withopenclaw-2.5 预装工作流，自动同步功能恢复
    **2026.07-26** （已删除）o.o-comfyui-withopenclaw-2.4 重大更新，comfyui主目录挪到root下，支持qdcpu启动comfyui，预装100个左右的插件，自动同步模型暂时取消
    **2026.07-18** （稳定版）o.o-comfyui-withopenclaw-2.1 更新comfyui114514自动同步模型，aimodels模型，自定义下载模型脚本，cnb工作流示例（未安装插件）
    **2026.07-17** o.o-comfyui-withopenclaw-1.0 新增openclaw预装和api导入交互脚本