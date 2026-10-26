import os, sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))
os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"
sys.path.insert(0, "/root/O.o-AI/gradio-libs")

import json, math, os, psutil, signal, subprocess, time, urllib, uuid
import gradio as gr

def release_port(port):
    connections = psutil.net_connections(kind='inet')
    for conn in connections:
        if conn.laddr.port == port and conn.pid:
            os.kill(conn.pid, signal.SIGTERM)
            return

release_port(7860)

class Func:
    hidden_file_list = [os.path.basename(__file__)]
    module_args_dict = {}
    module_id_block_list = []
    running_module_list = []
    max_connection = 4
    speed_threshold = 1024
    time_threshold = 10
    url_filename_prefix_list = ["attname=", "filename%3D", "name="]
    url_header_dict = {"liblibai-online.liblib.cloud": "--header='Referer: https://www.liblib.art'"}
    if os.environ.get("HF_ENDPOINT", ""):
        url_mirror_dict = {"https://huggingface.co": os.environ.get("HF_ENDPOINT", "")}
    else:
        url_mirror_dict = {}

    def load_json(path):
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as file:
                return json.load(file)
        return {}

    def format_size(size):
        if size >= 1073741824:
            return f"{round(size / 1073741824, 1)}GB"
        elif size >= 1048576:
            return f"{round(size / 1048576)}MB"
        elif size >= 1024:
            return f"{round(size / 1024)}KB"
        else:
            return f"{round(size)}B"

    def format_speed(speed):
        return f"{Func.format_size(speed)}/s"

    def format_time(sec):
        sec = round(sec)
        day = sec // 86400
        sec = sec % 86400
        hour = sec // 3600
        sec = sec % 3600
        minute = sec // 60
        sec = sec % 60
        time = ""
        time += f"{day}d" if day else ""
        time += f"{hour}h" if hour else ""
        time += f"{minute}m" if minute else ""
        time += f"{sec}s"
        return time

    def kill(process):
        if process.poll() is None:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)

    def try_remove(path):
        count = 1
        while count < 5:
            try:
                os.remove(path)
                return
            except:
                count += 1

    def aria2c(path, url, gen_code=False, module_id="", prefix="", max_connection="", progress=gr.Progress()):
        aria2c_path = "aria2c"
        for i in Func.url_mirror_dict:
            if i in url:
                url = url.replace(i, Func.url_mirror_dict[i])
        header = ""
        for i in Func.url_header_dict:
            if i in url:
                header = Func.url_header_dict[i].replace('"', "")
        folder = os.path.dirname(path)
        file_name = os.path.basename(path)
        if gen_code:
            code = ""
            if folder and not os.path.exists(folder):
                code = f'mkdir -p "{folder}"\n'
            code += f"{aria2c_path} "
            if max_connection:
                code += f"-x {max_connection} -s {max_connection} "
            code += "-c "
            if folder:
                code += f'-d "{folder}" '
            code += f'-o "{file_name}" '
            if header:
                code += f"{header} "
            code += f'"{url}"\n'
            return code
        if folder:
            os.makedirs(folder, exist_ok=True)
        cmd = [aria2c_path]
        if max_connection:
            cmd += ["-x", str(max_connection), "-s", str(max_connection)]
        cmd.append("-c")
        if folder:
            cmd += ["-d", folder]
        cmd += ["-o", file_name]
        if header:
            cmd.append(header)
        cmd += ["--summary-interval=1", url]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, preexec_fn=os.setsid)
        while True:
            if module_id and module_id not in Func.running_module_list:
                Func.kill(process)
                return "下载中断"
            output = process.stdout.readline().strip()
            if output == "(OK):download completed.":
                return "下载完成"
            if process.poll() is not None:
                return "下载中断"
            if output.startswith("[") and output.endswith("]") and "ETA:" in output:
                output, remaining_time = output[1:-1].split("ETA:")
                output, speed = output.split("DL:")
                speed = speed.strip().replace("i", "") + "/s"
                size_info, percent = output.split(" ")[1].split("(")
                size_info = size_info.replace("i", "")
                percent = int(percent[:-2]) / 100
                progress(percent, desc=f"{prefix}{file_name} {size_info} {speed} {remaining_time}")

    def wget(path, url, gen_code=False, module_id="", prefix="", progress=gr.Progress()):
        for i in Func.url_mirror_dict:
            if i in url:
                url = url.replace(i, Func.url_mirror_dict[i])
        header = ""
        for i in Func.url_header_dict:
            if i in url:
                header = Func.url_header_dict[i].replace('"', "")
        folder = os.path.dirname(path)
        if gen_code:
            code = ""
            if folder and not os.path.exists(folder):
                code = f'mkdir -p "{folder}"\n'
            code += f"wget {header} " if header else "wget "
            code += f'-c -O "{path}" "{url}"\n'
            return code
        if folder:
            os.makedirs(folder, exist_ok=True)
        log_folder = os.environ.get("TEMP", "/tmp")
        log_path = os.path.join(log_folder, f"wget-{time.time()}.log")
        cmd = ["wget", "-o", log_path, "-c", "-O", path, url]
        if header:
            cmd.insert(3, header)
        process = subprocess.Popen(cmd, preexec_fn=os.setsid)
        content_length = 0
        content_length2 = ""
        start_time = time.time()
        while not os.path.exists(path) or content_length == 0:
            time.sleep(0.1)
            if os.path.exists(log_path):
                with open(log_path, "r") as file:
                    for line in file.readlines():
                        if "The file is already fully retrieved" in line:
                            Func.try_remove(log_path)
                            return "下载完成"
                        if "Length: " in line:
                            content_length = int(line.split(" ")[1])
                            if "(" in line and ")" in line:
                                content_length2 = line.split(" ")[2]
            if process.poll() is not None:
                if content_length == 0:
                    if os.path.exists(path):
                        os.remove(path)
                    Func.try_remove(log_path)
                    return "未下载，链接有误"
            if time.time() - start_time > 10:
                Func.kill(process)
                if os.path.exists(path):
                    if os.path.getsize(path) == 0:
                        os.remove(path)
                Func.try_remove(log_path)
                return "未下载，网络连接超时"
        time_interval = 0.5
        file_name = f"{os.path.basename(path)}{content_length2}"
        file_size = os.path.getsize(path)
        remaining_time = ""
        start_time = time.time()
        while True:
            if module_id and module_id not in Func.running_module_list:
                Func.kill(process)
                Func.try_remove(log_path)
                return "下载中断"
            initial_file_size = os.path.getsize(path)
            time.sleep(time_interval)
            file_size = os.path.getsize(path)
            speed = (file_size - initial_file_size) / time_interval
            if speed:
                remaining_sec = (content_length - file_size) / speed
                remaining_time = f" {Func.format_time(remaining_sec)}"
            desc = f"{prefix}{file_name} 下载中 {Func.format_speed(speed)}{remaining_time}"
            progress(file_size / content_length, desc=desc)
            if module_id and module_id in Func.module_args_dict:
                speed_threshold, time_threshold = Func.module_args_dict[module_id]
                if speed > 1024 * speed_threshold:
                    start_time = time.time()
                if time.time() - start_time > time_threshold:
                    progress(file_size / content_length, desc=f"{prefix}重启下载子进程")
                    Func.kill(process)
                    process = subprocess.Popen(cmd, preexec_fn=os.setsid)
                    start_time = time.time()
                    time.sleep(3)
            if file_size > content_length:
                progress(file_size / content_length, desc=f"{prefix}{file_name} 下载错误")
                Func.kill(process)
                os.remove(path)
                Func.try_remove(log_path)
                return "下载错误，请重试"
            if process.poll() is not None:
                if file_size == content_length:
                    output = "下载完成"
                if file_size < content_length:
                    output = "下载中断"
                progress(file_size / content_length, desc=f"{prefix}{file_name} {output}")
                Func.try_remove(log_path)
                return output

    def interrupt(module_id):
        if module_id in Func.running_module_list:
            Func.running_module_list.remove(module_id)

    def refresh_restart_threshold(module_id, enable, speed_threshold, time_threshold):
        if enable and module_id:
            Func.module_args_dict[module_id] = [speed_threshold, time_threshold]
        if not enable and module_id in Func.module_args_dict:
            del Func.module_args_dict[module_id]

    def restart_block():
        module_id = gr.State()
        Func.module_id_block_list.append(module_id)
        restart = gr.Checkbox(label="自动重启下载", value=True)
        speed_threshold = gr.Slider(minimum=128, maximum=10240, step=128, label="速度阈值（KB/s）", value=Func.speed_threshold)
        time_threshold = gr.Slider(minimum=1, maximum=60, step=1, label="时间阈值（s）", value=Func.time_threshold)
        notes = gr.Markdown("说明：**持续低于**速度阈值并**超出**时间阈值时自动重启下载")
        restart.change(fn=lambda visible: [gr.update(visible=visible), gr.update(visible=visible), gr.update(visible=visible)], inputs=restart, outputs=[speed_threshold, time_threshold, notes], show_progress=False)
        for block in [restart, speed_threshold, time_threshold]:
            if type(block) is gr.components.slider.Slider:
                block.release(fn=Func.refresh_restart_threshold, inputs=[module_id, restart, speed_threshold, time_threshold], show_progress=False)
            else:
                block.change(fn=Func.refresh_restart_threshold, inputs=[module_id, restart, speed_threshold, time_threshold], show_progress=False)
        return module_id

    def refresh_module_id_block(*block_list):
        output = []
        for i in block_list:
            module_id = str(uuid.uuid4())
            output.append(module_id)
            Func.refresh_restart_threshold(module_id, True, Func.speed_threshold, Func.time_threshold)
        if len(block_list) == 1:
            return output[0]
        return output

    def get_file_name_from_url(url):
        if not url:
            return
        for i in url.split("&"):
            for prefix in Func.url_filename_prefix_list:
                if prefix in i:
                    return urllib.parse.unquote(i.split(prefix)[-1].replace("%22", ""))
        if "?" in url:
            if "cnb.cool" in url:
                return url.split("?", 1)[-1].split("name=")[-1]
            if "hf-mirror.com" in url or "huggingface.co" in url:
                return url.split("?", 1)[0].split("/")[-1]

    def download_aria2c(url, file_name, folder, module_id=str(uuid.uuid4()), max_connection=max_connection, gen_code=False, progress=gr.Progress()):
        if not url:
            return "请输入下载链接"
        if not file_name:
            return "请输入文件保存名称"
        path = os.path.join(os.path.abspath(folder), file_name)
        if gen_code:
            return Func.aria2c(path, url, max_connection=max_connection, gen_code=True)
        Func.running_module_list.append(module_id)
        output = Func.aria2c(path, url, module_id=module_id, max_connection=max_connection, progress=progress)
        Func.interrupt(module_id)
        return output

    def download_aria2c_block(demo=None, value=""):
        url = gr.Textbox(label="下载链接", lines=2)
        file_name = gr.Textbox(label="文件保存名称")
        folder = Func.path_block("保存文件夹", only_folder=True, demo=demo, value=value)
        with gr.Row():
            btn = gr.Button("开始下载", elem_id="button")
            btn2 = gr.Button("中断下载", visible=False)
            btn3 = gr.Button("生成终端下载代码")
        output = gr.Textbox(label="提示/终端下载代码", show_copy_button=True)
        max_connection = gr.Slider(minimum=0, maximum=16, step=1, label="线程数", value=Func.max_connection)
        module_id = gr.State()
        Func.module_id_block_list.append(module_id)
        gen_code = gr.State(True)
        btn.click(fn=lambda: [gr.update(interactive=False), gr.update(visible=True), gr.update(visible=False), "", gr.update(interactive=False)], outputs=[btn, btn2, btn3, output, max_connection]).then(fn=Func.download_aria2c, inputs=[url, file_name, folder, module_id, max_connection], outputs=output).then(fn=lambda: [gr.update(interactive=True), gr.update(visible=False), gr.update(visible=True), gr.update(interactive=True)], outputs=[btn, btn2, btn3, max_connection])
        btn2.click(fn=Func.interrupt, inputs=module_id)
        btn3.click(fn=Func.download_aria2c, inputs=[url, file_name, folder, module_id, max_connection, gen_code], outputs=output)
        url.change(fn=Func.get_file_name_from_url, inputs=url, outputs=file_name)
        return url, file_name, folder, output

    def download_wget(url, file_name, folder, module_id=str(uuid.uuid4()), gen_code=False, progress=gr.Progress()):
        if not url:
            return "请输入下载链接"
        if not file_name:
            return "请输入文件保存名称"
        path = os.path.join(os.path.abspath(folder), file_name)
        if gen_code:
            return Func.wget(path, url, gen_code=True)
        Func.running_module_list.append(module_id)
        output = Func.wget(path, url, module_id=module_id, progress=progress)
        Func.interrupt(module_id)
        return output

    def download_wget_block(demo=None, value=""):
        url = gr.Textbox(label="下载链接", lines=2)
        file_name = gr.Textbox(label="文件保存名称")
        folder = Func.path_block("保存文件夹", only_folder=True, demo=demo, value=value)
        with gr.Row():
            btn = gr.Button("开始下载", elem_id="button")
            btn2 = gr.Button("中断下载", visible=False)
            btn3 = gr.Button("生成终端下载代码")
        output = gr.Textbox(label="提示/终端下载代码", show_copy_button=True)
        module_id = Func.restart_block()
        gen_code = gr.State(True)
        btn.click(fn=lambda: [gr.update(interactive=False), gr.update(visible=True), gr.update(visible=False), ""], outputs=[btn, btn2, btn3, output]).then(fn=Func.download_wget, inputs=[url, file_name, folder, module_id], outputs=output).then(fn=lambda: [gr.update(interactive=True), gr.update(visible=False), gr.update(visible=True)], outputs=[btn, btn2, btn3])
        btn2.click(fn=Func.interrupt, inputs=module_id)
        btn3.click(fn=Func.download_wget, inputs=[url, file_name, folder, module_id, gen_code], outputs=output)
        url.change(fn=Func.get_file_name_from_url, inputs=url, outputs=file_name)
        return url, file_name, folder, output

    def list_dir(path="", folder_prefix=""):
        if not path or not os.path.exists(path):
            path = None
        file_list = []
        folder_list = []
        for i in os.listdir(path):
            if not path and i.startswith(".") or i in Func.hidden_file_list:
                continue
            if path:
                temp_path = os.path.join(path, i)
            else:
                temp_path = i
            if os.path.isfile(temp_path):
                file_list.append(temp_path)
            if os.path.isdir(temp_path):
                folder_list.append(f"{folder_prefix}{temp_path}")
        file_list = sorted(file_list)
        folder_list = sorted(folder_list)
        return folder_list + file_list, folder_list, file_list

    def refresh_path_list(path, folder_prefix="", only_folder=False, value=""):
        home_path = f"{folder_prefix}主目录"
        if path == home_path:
            if only_folder:
                return gr.update(choices=Func.list_dir()[1], value=""), path
            return gr.update(choices=Func.list_dir(folder_prefix=folder_prefix)[0], value=""), path
        choices = [home_path]
        path = path.replace(folder_prefix, "")
        if os.path.isdir(path):
            if os.path.dirname(path):
                choices.append(folder_prefix + os.path.dirname(path))
            choices.append(folder_prefix + path)
            if only_folder:
                choices += Func.list_dir(path)[1]
            else:
                choices += Func.list_dir(path, folder_prefix=folder_prefix)[0]
            if value:
                return gr.update(choices=choices, value=value), path
            else:
                return gr.update(choices=choices), path
        return gr.update(), gr.update()

    def path_block(label, only_folder=False, demo=None, value=""):
        with gr.Row():
            if only_folder:
                folder_prefix = ""
                path = gr.Dropdown([], label=label, value="", allow_custom_value=True, scale=99)
            else:
                folder_prefix = "📂 "
                path = gr.Dropdown([], label=label, value="", allow_custom_value=True, scale=99)
            path_dir = gr.State(f"{folder_prefix}{value}")
            refresh = gr.Button("🔄", elem_id="refresh", scale=1, min_width=1)
        path.select(fn=lambda path: Func.refresh_path_list(path, folder_prefix=folder_prefix, only_folder=only_folder), inputs=path, outputs=[path, path_dir], show_progress=False)
        refresh.click(fn=lambda path: Func.refresh_path_list(path, folder_prefix=folder_prefix, only_folder=only_folder), inputs=path_dir, outputs=[path, path_dir], show_progress=False)
        if demo:
            demo.load(fn=lambda path: Func.refresh_path_list(path, folder_prefix=folder_prefix, only_folder=only_folder, value=value), inputs=path_dir, outputs=[path, path_dir], show_progress=False)
        return path

    def multi_block(block, num="5", demo=None, value=""):
        for i in range(num):
            if num == 1:
                if demo:
                    if value:
                        block(demo=demo, value=value)
                    else:
                        block(demo=demo)
                else:
                    if value:
                        block(value=value)
                    else:
                        block()
            else:
                with gr.Tab(f"任务 {i + 1}"):
                    if demo:
                        if value:
                            block(demo=demo, value=value)
                        else:
                            block(demo=demo)
                    else:
                        if value:
                            block(value=value)
                        else:
                            block()

    def refresh_blocks():
        demo.load(fn=Func.refresh_module_id_block, inputs=Func.module_id_block_list, outputs=Func.module_id_block_list)

class Preset:
    def load_source():
        from hook_by_xu import all_file_dict, all_source_dict
        source = all_source_dict
        all_file_dict_for_search = {}
        all_file_path_dict = {}
        for file_type in all_file_dict:
            all_file_path_dict[file_type] = os.path.join("models", file_type)
            source[file_type] = all_file_dict[file_type]
            for file in all_file_dict[file_type]:
                file_name = os.path.join(file_type, file)
                all_file_dict_for_search[file_name] = all_file_dict[file_type][file]
        source["全部模型"] = all_file_dict_for_search
        source["path_dict"]["全部模型"] = {}
        source["path_dict"]["全部模型"]["全部模型"] = "models"
        for key in sorted(all_file_path_dict):
            source["path_dict"]["全部模型"][key] = all_file_path_dict[key]
        Preset.source = source
        class_1st_list = list(source["path_dict"].keys())
        class_1st = class_1st_list[0]
        class_2nd_list = list(Preset.source["path_dict"][class_1st].keys())
        class_2nd = class_2nd_list[0]
        return gr.update(choices=class_1st_list, value=class_1st), gr.update(choices=class_2nd_list, value=class_2nd)

    def refresh_preset_file_choices(class_1st, class_2nd):
        if not class_2nd:
            return "", gr.update(choices=[], value=[]), gr.update(choices=[], value=[]), ""
        file_choices = []
        folder = Preset.source["path_dict"][class_1st][class_2nd]
        if isinstance(folder, list):
            folder = folder[0]
        for file in Preset.source[class_2nd]:
            path = os.path.join(folder, file)
            if not os.path.exists(path):
                file_choices.append(file)
            elif os.path.islink(path):
                file_choices.append(f"{file}（已缓存至云节点）")
            else:
                file_choices.append(f"{file}（已下载）")
        subfolder_choices = ["该分类下所有文件"]
        for path in Preset.source[class_2nd]:
            choice = ""
            subfolder = ""
            while "/" in path:
                subfolder, path = path.split("/", 1)
                choice = os.path.join(choice, subfolder)
                if choice not in subfolder_choices:
                    subfolder_choices.append(choice)
        return folder, gr.update(choices=file_choices, value=[]), gr.update(choices=subfolder_choices, value=[]), ""

    def download_aria2c(class_2nd, file_list, subfolder_list, folder, module_id=str(uuid.uuid4()), max_connection="", gen_code=False, progress=gr.Progress()):
        if not file_list and not subfolder_list:
            return "请选择预设文件/文件夹"
        if not gen_code:
            Func.running_module_list.append(module_id)
        output = ""
        for file_name in file_list:
            file_name = file_name.replace("（已下载）", "").replace("（已缓存至云节点）", "")
            url = Preset.source[class_2nd][file_name]
            path = os.path.join(os.path.abspath(folder), file_name)
            if gen_code:
                output += Func.aria2c(path, url, max_connection=max_connection, gen_code=True)
            else:
                output += f"{file_name} {Func.aria2c(path, url, module_id=module_id, max_connection=max_connection, progress=progress)}\n"
                if module_id not in Func.running_module_list:
                    break
        if "该分类下所有文件" in subfolder_list:
            subfolder_list = ["该分类下所有文件"]
        for subfolder in subfolder_list:
            running = True
            for file_name in Preset.source[class_2nd]:
                if file_name.startswith(subfolder) or subfolder == "该分类下所有文件":
                    url = Preset.source[class_2nd][file_name]
                    path = os.path.join(os.path.abspath(folder), file_name)
                    if gen_code:
                        output += Func.aria2c(path, url, max_connection=max_connection, gen_code=True)
                    else:
                        output += f"{file_name} {Func.aria2c(path, url, module_id=module_id, max_connection=max_connection, progress=progress)}\n"
                        if module_id not in Func.running_module_list:
                            running = False
                            break
            if not running:
                break
        Func.interrupt(module_id)
        return output

    def download_aria2c_block():
        with gr.Row():
            class_2nd = gr.Dropdown([], label="二级分类")
            class_1st = gr.Dropdown([], label="一级分类")
        folder = gr.Textbox(label="预设保存文件夹")
        file_list = gr.Dropdown([], label="预设文件列表（按文件下载，可多选）", multiselect=True, interactive=True)
        subfolder_list = gr.Dropdown([], label="预设文件夹列表（按文件夹下载，可多选）", multiselect=True, interactive=True)
        with gr.Row():
            btn = gr.Button("开始下载", elem_id="button")
            btn2 = gr.Button("中断下载", visible=False)
            btn3 = gr.Button("生成终端下载代码")
        output = gr.Textbox(label="提示/终端下载代码", show_copy_button=True, lines=2)
        max_connection = gr.Slider(minimum=0, maximum=16, step=1, label="线程数", value=Func.max_connection)
        module_id = gr.State()
        Func.module_id_block_list.append(module_id)
        gen_code = gr.State(True)
        btn.click(fn=lambda: [gr.update(interactive=False), gr.update(visible=True), gr.update(visible=False), "", gr.update(interactive=False)], outputs=[btn, btn2, btn3, output, max_connection]).then(fn=Preset.download_aria2c, inputs=[class_2nd, file_list, subfolder_list, folder, module_id, max_connection], outputs=output).then(fn=lambda: [gr.update(interactive=True), gr.update(visible=False), gr.update(visible=True), gr.update(interactive=True)], outputs=[btn, btn2, btn3, max_connection])
        btn2.click(fn=Func.interrupt, inputs=module_id)
        btn3.click(fn=Preset.download_aria2c, inputs=[class_2nd, file_list, subfolder_list, folder, module_id, max_connection, gen_code], outputs=output)
        class_1st.select(fn=lambda: None, outputs=class_2nd, show_progress=False)
        class_1st.select(fn=lambda class_1st: [gr.update(choices=list(Preset.source["path_dict"][class_1st].keys())), "", gr.update(choices=[], value=[]), ""], inputs=class_1st, outputs=[class_2nd, folder, file_list, output], show_progress=False)
        class_2nd.change(fn=Preset.refresh_preset_file_choices, inputs=[class_1st, class_2nd], outputs=[folder, file_list, subfolder_list, output], show_progress=False)
        file_list.select(fn=lambda: gr.update(value=[]), outputs=subfolder_list, show_progress=False)
        subfolder_list.select(fn=lambda: gr.update(value=[]), outputs=file_list, show_progress=False)
        demo.load(fn=Preset.load_source, outputs=[class_1st, class_2nd], show_progress=False)

css = """
#button {background: #FFE1C0; color: #FF453A; align-self: flex-end;}
#refresh {background: transparent; align-self: flex-end;}
.block.padded:not(.gradio-accordion) {padding: 0 !important;}
.gradio-container {max-width: 600px !important;}
div.form {border-width: 0; box-shadow: none; background: transparent; gap: 0.5em;}
footer {display: none !important;}
#footer {text-align: center; font-size: 16px; font-weight: bold;}
"""

with gr.Blocks(css=css) as demo:
    with gr.Tab("Aria2c"): Func.multi_block(Func.download_aria2c_block, 5, demo=demo, value="models")
    with gr.Tab("Wget"): Func.multi_block(Func.download_wget_block, 5, demo=demo, value="models")
    with gr.Tab("预设下载"): Preset.download_aria2c_block()
    Func.refresh_blocks()
    gr.Markdown('Based on [**Gradio**](https://www.gradio.app) • Powered by [**旭**](https://cnb.cool/u/cnb-xu)', elem_id="footer")

inbrowser = os.environ.get("inbrower", "")
if inbrowser:
    demo.queue(concurrency_count=100).launch(inbrowser=True, server_name="0.0.0.0")
else:
    demo.queue(concurrency_count=100).launch(server_name="0.0.0.0")