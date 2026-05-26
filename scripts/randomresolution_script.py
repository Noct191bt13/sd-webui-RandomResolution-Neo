import gradio as gr
import json
import math
import modules.scripts as scripts
import os
import random
from modules import rng

class AspectRatioPreset:
    def __init__(self, name, ratio):
        self.name = name
        self.ratio = ratio

    def get_dimensions(self, target_pixels):
        width = math.sqrt(target_pixels * self.ratio)
        height = width / self.ratio
        return (round(width / 8) * 8, round(height / 8) * 8)

class Script(scripts.Script):
    def __init__(self):
        super().__init__()
        self.extension_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.presets_dir = os.path.join(self.extension_dir, "presets")

        self.defaults = {
            "SD1.5": [(768,768),(768,512),(512,768),(768,576),(576,768),(912,512),(512,912)],
            "SDXL": [(1024,1024),(1152,896),(896,1152),(1216,832),(832,1216),(1344,768),(768,1344)],
            "Anima": [(1024,1024),(1152,896),(896,1152),(1216,832),(832,1216),(1536,1536)],
        }

        self.aspect_ratios = [
            AspectRatioPreset("Square (1:1)", 1.0),
            AspectRatioPreset("Portrait (2:3)", 2/3),
            AspectRatioPreset("Landscape (3:2)", 1.5),
            AspectRatioPreset("Wide (16:9)", 16/9),
            AspectRatioPreset("Ultrawide (21:9)", 21/9),
            AspectRatioPreset("Phone (9:19)", 9/19),
        ]

        os.makedirs(self.presets_dir, exist_ok=True)
        self._ensure_default_presets()
        self.preset_cache = {}
        self._load_all_presets()

    def _ensure_default_presets(self):
        for name, resolutions in self.defaults.items():
            path = os.path.join(self.presets_dir, f"{name}.json")
            if not os.path.exists(path):
                with open(path, 'w') as f:
                    json.dump(resolutions, f)

    def _load_all_presets(self):
        self.preset_cache = {}
        for fname in os.listdir(self.presets_dir):
            if fname.endswith(".json"):
                name = fname[:-5]
                path = os.path.join(self.presets_dir, fname)
                try:
                    with open(path, 'r') as f:
                        self.preset_cache[name] = json.load(f)
                except:
                    self.preset_cache[name] = self.defaults.get(name, [])

    def _list_presets(self):
        names = []
        for fname in sorted(os.listdir(self.presets_dir)):
            if fname.endswith(".json"):
                names.append(fname[:-5])
        return names

    def _save_preset(self, name, resolutions):
        path = os.path.join(self.presets_dir, f"{name}.json")
        with open(path, 'w') as f:
            json.dump(resolutions, f)
        self.preset_cache[name] = resolutions

    def _delete_preset(self, name):
        if name in self.defaults:
            return
        path = os.path.join(self.presets_dir, f"{name}.json")
        if os.path.exists(path):
            os.remove(path)
        self.preset_cache.pop(name, None)

    def _load_preset(self, name):
        return list(self.preset_cache.get(name, []))

    def _validate_anima_resolution(self, width, height):
        width = (width // 64) * 64
        height = (height // 64) * 64
        width = max(width, 512)
        height = max(height, 512)
        width = min(width, 2048)
        height = min(height, 2048)
        return width, height

    sorting_priority = 15.1

    def title(self):
        return "Random Resolution"

    def ui(self, is_img2img):
        preset_names = self._list_presets()

        with gr.Accordion("Random Resolution", open=False):
            with gr.Column():
                is_enabled = gr.Checkbox(False, label="Enable random resolution")

                with gr.Accordion("Presets", open=True):
                    with gr.Row():
                        preset_dropdown = gr.Dropdown(
                            choices=preset_names, value=preset_names[0] if preset_names else None,
                            label="Preset", allow_custom_value=True
                        )
                        save_preset_btn = gr.Button("Save", scale=0)
                        delete_preset_btn = gr.Button("Delete", scale=0)
                    with gr.Row():
                        new_preset_name = gr.Textbox(label="New Preset Name", placeholder="Enter name...", scale=1)
                        new_preset_btn = gr.Button("New", scale=0)

                with gr.Row():
                    weight_mode = gr.Radio(
                        choices=["Equal Weights", "Favor Smaller", "Favor Larger"],
                        value="Equal Weights", label="Weight Mode"
                    )
                with gr.Row():
                    orientation = gr.Radio(
                        choices=["Both", "Vertical", "Horizontal"],
                        value="Both", label="Orientation"
                    )
                with gr.Row():
                    min_dim = gr.Slider(minimum=256, maximum=3072, step=64, value=512,
                                      label="Min Dimension")
                    max_dim = gr.Slider(minimum=256, maximum=3072, step=64, value=2048,
                                      label="Max Dimension")

                initial_preset = preset_names[0] if preset_names else None
                initial_res = self._load_preset(initial_preset) if initial_preset else []
                initial_text = ';'.join(f"{w},{h}" for w, h in initial_res)

                with gr.Row():
                    current_resolutions = gr.Textbox(
                        label="Current Resolutions (width,height)", value=initial_text,
                        lines=2, placeholder="1024,1024;1152,896;1216,832"
                    )

                with gr.Row():
                    new_width = gr.Number(label="Width", precision=0, value=1024, step=64)
                    new_height = gr.Number(label="Height", precision=0, value=1024, step=64)
                    add_btn = gr.Button("Add", scale=0)

                with gr.Row():
                    reset_btn = gr.Button("Reset", scale=0)
                    clear_btn = gr.Button("Clear", scale=0)
                    sort_btn = gr.Button("Sort", scale=0)

                with gr.Row():
                    remove_large = gr.Button("Remove > 1MP", scale=0)
                    remove_small = gr.Button("Remove < 0.3MP", scale=0)

                with gr.Accordion("Add from AR", open=False):
                    with gr.Row():
                        aspect_ratio = gr.Dropdown(
                            choices=[p.name for p in self.aspect_ratios],
                            label="Aspect Ratio"
                        )
                        target_mpix = gr.Dropdown(
                            choices=["0.5", "0.75", "1.0", "1.5", "2.0"],
                            value="1.0", label="Target MP"
                        )
                        add_ar_btn = gr.Button("Add", scale=0)

        # ---- wire up ----
        def fmt(seq):
            return ';'.join(f"{w},{h}" for w, h in seq)

        def load_preset_ui(name):
            res = self._load_preset(name)
            return fmt(res)

        def save_preset_ui(name, current_text):
            res = _parse_text(current_text)
            self._save_preset(name, res)
            return fmt(res)

        def new_preset_ui(name, current_text):
            if not name or name in self.defaults:
                return gr.Dropdown.update(), current_text
            res = _parse_text(current_text)
            self._save_preset(name, res)
            new_names = self._list_presets()
            return gr.Dropdown.update(choices=new_names, value=name), fmt(res)

        def delete_preset_ui(name):
            if name in self.defaults:
                return gr.Dropdown.update(), ""
            self._delete_preset(name)
            new_names = self._list_presets()
            fallback = new_names[0] if new_names else None
            res = self._load_preset(fallback) if fallback else []
            return gr.Dropdown.update(choices=new_names, value=fallback), fmt(res)

        def on_enable_change(enable, preset_name):
            if enable:
                return load_preset_ui(preset_name)
            return gr.update()

        def _parse_text(text):
            result = []
            if text and text.strip():
                for pair in text.strip().split(';'):
                    w, h = map(int, pair.split(','))
                    result.append((w, h))
            return result

        def _text_to_model(model_name, text):
            return _parse_text(text)

        def _resave(model_name, res_list):
            self._save_preset(model_name, res_list)
            return fmt(res_list)

        def add_resolution(name, current, width, height):
            if not width or not height:
                return current
            new_res = (int(width), int(height))
            if name in self.defaults and name == "Anima":
                new_res = self._validate_anima_resolution(*new_res)
            res = _parse_text(current)
            if new_res not in res:
                res.append(new_res)
            return _resave(name, res)

        def add_ar(name, current, preset_name, mpix):
            preset = next((p for p in self.aspect_ratios if p.name == preset_name), None)
            if not preset:
                return current
            target_px = float(mpix) * 1024 * 1024
            w, h = preset.get_dimensions(target_px)
            if name == "Anima":
                w, h = self._validate_anima_resolution(w, h)
            res = _parse_text(current)
            new_res = (w, h)
            if new_res not in res:
                res.append(new_res)
            return _resave(name, res)

        def reset_to_defaults(name):
            default = list(self.defaults.get(name, []))
            self._save_preset(name, default)
            return fmt(default)

        def clear_resolutions(name):
            self._save_preset(name, [])
            return ""

        def sort_resolutions(name, current):
            res = _parse_text(current)
            res.sort(key=lambda x: x[0] * x[1])
            return _resave(name, res)

        def remove_by_size(name, current, min_mp, max_mp):
            res = _parse_text(current)
            res = [(w, h) for w, h in res if min_mp <= (w * h) / (1024 * 1024) <= max_mp]
            return _resave(name, res)

        preset_dropdown.change(fn=load_preset_ui, inputs=[preset_dropdown], outputs=[current_resolutions])

        is_enabled.change(fn=on_enable_change, inputs=[is_enabled, preset_dropdown], outputs=[current_resolutions])

        add_btn.click(fn=add_resolution, inputs=[preset_dropdown, current_resolutions, new_width, new_height], outputs=[current_resolutions])

        add_ar_btn.click(fn=add_ar, inputs=[preset_dropdown, current_resolutions, aspect_ratio, target_mpix], outputs=[current_resolutions])

        save_preset_btn.click(fn=save_preset_ui, inputs=[preset_dropdown, current_resolutions], outputs=[current_resolutions])

        new_preset_btn.click(fn=new_preset_ui, inputs=[new_preset_name, current_resolutions], outputs=[preset_dropdown, current_resolutions])

        delete_preset_btn.click(fn=delete_preset_ui, inputs=[preset_dropdown], outputs=[preset_dropdown, current_resolutions])

        reset_btn.click(fn=reset_to_defaults, inputs=[preset_dropdown], outputs=[current_resolutions])

        clear_btn.click(fn=clear_resolutions, inputs=[preset_dropdown], outputs=[current_resolutions])

        sort_btn.click(fn=sort_resolutions, inputs=[preset_dropdown, current_resolutions], outputs=[current_resolutions])

        remove_large.click(fn=lambda n, c: remove_by_size(n, c, 0, 1.0), inputs=[preset_dropdown, current_resolutions], outputs=[current_resolutions])

        remove_small.click(fn=lambda n, c: remove_by_size(n, c, 0.3, float('inf')), inputs=[preset_dropdown, current_resolutions], outputs=[current_resolutions])

        return [is_enabled, preset_dropdown, current_resolutions, weight_mode, orientation, min_dim, max_dim]

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def before_process_batch(self, p, is_enabled, preset_name, current_resolutions, weight_mode, orientation, min_dim, max_dim, *args, **kwargs):
        if not is_enabled:
            return

        if getattr(p, 'enable_hr', False):
            return

        if hasattr(p, 'sd_model') and hasattr(p.sd_model, 'is_wan') and p.sd_model.is_wan:
            detected = "Anima"
        elif hasattr(p, 'sd_model') and hasattr(p.sd_model, 'is_sdxl') and p.sd_model.is_sdxl:
            detected = "SDXL"
        else:
            detected = "SD 1.5"

        res_list = []
        try:
            if current_resolutions and current_resolutions.strip():
                for pair in current_resolutions.strip().split(';'):
                    w, h = map(int, pair.split(','))
                    if detected == "Anima":
                        w, h = self._validate_anima_resolution(w, h)
                    if min(w, h) >= min_dim and max(w, h) <= max_dim:
                        res_list.append((w, h))
        except:
            pass

        if not res_list:
            res_list = self._load_preset(preset_name)
        if not res_list:
            res_list = list(self.defaults.get(detected, self.defaults["SDXL"]))

        filtered = [(w, h) for w, h in res_list if min(w, h) >= min_dim and max(w, h) <= max_dim]
        if filtered:
            res_list = filtered

        if detected == "Anima":
            res_list = [self._validate_anima_resolution(w, h) for w, h in res_list]

        if orientation == "Vertical":
            res_list = [(w, h) for w, h in res_list if h > w]
        elif orientation == "Horizontal":
            res_list = [(w, h) for w, h in res_list if w > h]

        if not res_list:
            res_list = [(512, 768)] if orientation == "Vertical" else [(768, 512)]

        weights = None
        if weight_mode == "Favor Smaller":
            weights = [1.0 / (w * h) for w, h in res_list]
        elif weight_mode == "Favor Larger":
            weights = [float(w * h) for w, h in res_list]
        if weights:
            total = sum(weights)
            if total > 0:
                weights = [w / total for w in weights]
            else:
                weights = None

        opt_f = 8
        batch_number = kwargs.get('batch_number', 0)
        seed = p.seed + batch_number if p.seed != -1 else random.randint(0, 2**32 - 1)
        random.seed(seed)

        res_tuple = random.choices(res_list, weights=weights, k=1)[0]
        if detected == "Anima":
            res_tuple = self._validate_anima_resolution(res_tuple[0], res_tuple[1])

        p.width = res_tuple[0]
        p.height = res_tuple[1]

        if getattr(p, 'enable_hr', False):
            p.hr_upscale_to_x = int(p.width * p.hr_scale)
            p.hr_upscale_to_y = int(p.height * p.hr_scale)

            if hasattr(p, 'hr_resize_x') and hasattr(p, 'hr_resize_y'):
                if p.hr_resize_x != 0 or p.hr_resize_y != 0:
                    if p.hr_resize_y == 0:
                        p.hr_resize_y = p.hr_resize_x * p.height // p.width
                    elif p.hr_resize_x == 0:
                        p.hr_resize_x = p.hr_resize_y * p.width // p.height
                    target_w = p.hr_resize_x
                    target_h = p.hr_resize_y
                    src_ratio = p.width / p.height
                    dst_ratio = p.hr_resize_x / p.hr_resize_y
                    if src_ratio < dst_ratio:
                        p.hr_upscale_to_x = p.hr_resize_x
                        p.hr_upscale_to_y = p.hr_resize_x * p.height // p.width
                    else:
                        p.hr_upscale_to_x = p.hr_resize_y * p.width // p.height
                        p.hr_upscale_to_y = p.hr_resize_y
                    p.truncate_x = (p.hr_upscale_to_x - target_w) // opt_f
                    p.truncate_y = (p.hr_upscale_to_y - target_h) // opt_f

        if hasattr(p, 'rng'):
            old_shape = p.rng.shape
            new_shape = tuple(list(old_shape[:-2]) + [p.height // opt_f, p.width // opt_f])
            p.rng = rng.ImageRNG(
                new_shape, p.seeds, subseeds=p.subseeds,
                subseed_strength=p.subseed_strength,
                seed_resize_from_h=getattr(p, 'seed_resize_from_h', 0),
                seed_resize_from_w=getattr(p, 'seed_resize_from_w', 0),
            )

        print(f"Random resolution: {p.width}x{p.height} (preset: {preset_name}, detected: {detected})")
