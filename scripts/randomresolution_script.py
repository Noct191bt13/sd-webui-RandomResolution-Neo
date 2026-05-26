import modules.scripts as scripts
import gradio as gr
import random
import json
import os
from modules import rng
from modules.shared import opts
import math

class AspectRatioPreset:
    def __init__(self, name, ratio):
        self.name = name
        self.ratio = ratio  # width/height

    def get_dimensions(self, target_pixels):
        # Calculate dimensions maintaining aspect ratio and target pixel count
        width = math.sqrt(target_pixels * self.ratio)
        height = width / self.ratio
        return (round(width / 8) * 8, round(height / 8) * 8)  # Round to nearest multiple of 8

class Script(scripts.Script):
    def __init__(self):
        super().__init__()
        self.config_dir = os.path.join(scripts.basedir(), "random_res_config")
        self.sd15_config = os.path.join(self.config_dir, "sd15_resolutions.json")
        self.sdxl_config = os.path.join(self.config_dir, "sdxl_resolutions.json")
        self.anima_config = os.path.join(self.config_dir, "anima_resolutions.json")

        # Default resolution lists
        self.default_sd15_res = [(768,768),(768,512),(512,768),(768,576),(576,768),(912,512),(512,912)]
        self.default_sdxl_res = [(1024,1024),(1152,896),(896,1152),(1216,832),(832,1216),(1344,768),(768,1344)]

        # Anima-specific resolutions - MUST be divisible by 64 for Anima compatibility
        self.default_anima_res = [
            (1024, 1024),  # 1:1
            (1152, 896),   # ~5:4
            (896, 1152),   # ~4:5
            (1216, 832),   # ~3:2
            (832, 1216),   # ~2:3
            (1088, 1088),  # 1:1 alternative
            (960, 960),    # 1:1 smaller
        ]

        # Aspect ratio presets
        self.aspect_ratios = [
            AspectRatioPreset("Square (1:1)", 1.0),
            AspectRatioPreset("Portrait (2:3)", 2/3),
            AspectRatioPreset("Landscape (3:2)", 1.5),
            AspectRatioPreset("Wide (16:9)", 16/9),
            AspectRatioPreset("Ultrawide (21:9)", 21/9),
            AspectRatioPreset("Phone (9:19)", 9/19),
        ]

        # Create config directory if it doesn't exist
        os.makedirs(self.config_dir, exist_ok=True)

        # Load or create configuration files
        self.sd15_resolutions = self.load_resolutions(self.sd15_config, self.default_sd15_res)
        self.sdxl_resolutions = self.load_resolutions(self.sdxl_config, self.default_sdxl_res)
        self.anima_resolutions = self.load_resolutions(self.anima_config, self.default_anima_res)

    def load_resolutions(self, config_file, default_list):
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    return json.load(f)
            except:
                return default_list
        else:
            with open(config_file, 'w') as f:
                json.dump(default_list, f)
            return default_list

    def save_resolutions(self, model_type, resolutions):
        """Save resolutions for the given model type"""
        if model_type == "SDXL":
            config_file = self.sdxl_config
        elif model_type == "Anima":
            config_file = self.anima_config
        else:  # "SD 1.5"
            config_file = self.sd15_config
        with open(config_file, 'w') as f:
            json.dump(resolutions, f)

    def _get_res_list_for_model(self, model_type):
        if model_type == "SDXL":
            return self.sdxl_resolutions
        elif model_type == "Anima":
            return self.anima_resolutions
        else:  # SD 1.5
            return self.sd15_resolutions

    def _get_default_list(self, model_type):
        if model_type == "SDXL":
            return self.default_sdxl_res
        elif model_type == "Anima":
            return self.default_anima_res
        else:
            return self.default_sd15_res

    def _validate_anima_resolution(self, width, height):
        """Ensure resolution is compatible with Anima model requirements"""
        # Anima requires dimensions divisible by 64
        width = (width // 64) * 64
        height = (height // 64) * 64

        # Ensure minimum dimensions
        width = max(width, 512)
        height = max(height, 512)

        # Ensure maximum dimensions (to prevent memory issues)
        width = min(width, 2048)
        height = min(height, 2048)

        return width, height

    sorting_priority = 15.1

    def title(self):
        return "Random Resolution"

    def ui(self, is_img2img):
        with gr.Accordion("Random Resolution", open=False):
            with gr.Column():
                is_enabled = gr.Checkbox(False, label="Enable random resolution")

                with gr.Row():
                    model_type = gr.Radio(
                        choices=["SD 1.5", "SDXL", "Anima"],
                        value="SDXL",
                        label="Model Type"
                    )
                    weight_mode = gr.Radio(
                        choices=["Equal Weights", "Favor Smaller", "Favor Larger"],
                        value="Equal Weights",
                        label="Resolution Weight Mode"
                    )

                with gr.Row():
                    min_dim = gr.Slider(minimum=256, maximum=3072, step=64, value=512,  # Changed step to 64
                                      label="Minimum Dimension")
                    max_dim = gr.Slider(minimum=256, maximum=3072, step=64, value=2048,  # Changed step to 64
                                      label="Maximum Dimension")

                with gr.Row():
                    current_resolutions = gr.Textbox(
                        label="Current Resolutions (width,height format)",
                        lines=2,
                        placeholder="Example: 1024,1024;1152,896;1216,832"
                    )

                with gr.Row():
                    with gr.Column(scale=1):
                        new_width = gr.Number(label="New Width", precision=0, value=1024)
                        new_height = gr.Number(label="New Height", precision=0, value=1024)
                        add_btn = gr.Button("Add Resolution")

                    with gr.Column(scale=1):
                        aspect_ratio = gr.Dropdown(
                            choices=[preset.name for preset in self.aspect_ratios],
                            label="Add from Aspect Ratio Preset"
                        )
                        target_mpix = gr.Slider(0.1, 2.0, value=1.0, step=0.1,  # Changed default to 1.0 for Anima
                                              label="Target Megapixels")
                        add_preset_btn = gr.Button("Add Preset Resolution")

                with gr.Row():
                    reset_btn = gr.Button("Reset to Defaults")
                    clear_btn = gr.Button("Clear All")
                    sort_btn = gr.Button("Sort by Size")

                with gr.Row():
                    remove_large = gr.Button("Remove Resolutions > 1MP")
                    remove_small = gr.Button("Remove Resolutions < 0.3MP")
                    validate_btn = gr.Button("Validate for Anima")

        # ---------- UI callbacks ----------
        def update_resolutions(model_choice):
            res_list = self._get_res_list_for_model(model_choice)
            return ';'.join([f"{w},{h}" for w, h in res_list])

        def on_enable_change(enable_value, current_model_type):
            if enable_value:
                return update_resolutions(current_model_type)
            return gr.update()

        def add_resolution(model_choice, current, width, height):
            if not width or not height:
                return current
            new_res = (int(width), int(height))

            # Validate for Anima
            if model_choice == "Anima":
                new_res = self._validate_anima_resolution(new_res[0], new_res[1])

            res_list = self._get_res_list_for_model(model_choice)
            if new_res not in res_list:
                res_list.append(new_res)
                self.save_resolutions(model_choice, res_list)
            return ';'.join([f"{w},{h}" for w, h in res_list])

        def add_preset_resolution(model_choice, current, preset_name, target_mpix):
            preset = next((p for p in self.aspect_ratios if p.name == preset_name), None)
            if not preset:
                return current
            target_pixels = target_mpix * 1024 * 1024
            width, height = preset.get_dimensions(target_pixels)

            # Validate for Anima
            if model_choice == "Anima":
                width, height = self._validate_anima_resolution(width, height)

            res_list = self._get_res_list_for_model(model_choice)
            new_res = (width, height)
            if new_res not in res_list:
                res_list.append(new_res)
                self.save_resolutions(model_choice, res_list)
            return ';'.join([f"{w},{h}" for w, h in res_list])

        def validate_resolutions(model_choice, current):
            """Validate all resolutions for Anima compatibility"""
            if model_choice != "Anima" or not current.strip():
                return current

            validated = []
            for res_pair in current.strip().split(';'):
                try:
                    w, h = map(int, res_pair.split(','))
                    w, h = self._validate_anima_resolution(w, h)
                    validated.append((w, h))
                except:
                    continue

            # Update stored list
            self.anima_resolutions = validated
            self.save_resolutions("Anima", validated)

            # Show message about validated resolutions
            if validated:
                print(f"Validated {len(validated)} resolutions for Anima compatibility")
            return ';'.join([f"{w},{h}" for w, h in validated])

        def reset_to_defaults(model_choice):
            default = self._get_default_list(model_choice).copy()
            if model_choice == "SDXL":
                self.sdxl_resolutions = default
            elif model_choice == "Anima":
                self.anima_resolutions = default
            else:
                self.sd15_resolutions = default
            self.save_resolutions(model_choice, default)
            return update_resolutions(model_choice)

        def clear_resolutions(model_choice):
            empty = []
            if model_choice == "SDXL":
                self.sdxl_resolutions = empty
            elif model_choice == "Anima":
                self.anima_resolutions = empty
            else:
                self.sd15_resolutions = empty
            self.save_resolutions(model_choice, empty)
            return ""

        def sort_resolutions(model_choice, current):
            if not current.strip():
                return current
            res_list = []
            for res_pair in current.strip().split(';'):
                w, h = map(int, res_pair.split(','))
                res_list.append((w, h))
            res_list.sort(key=lambda x: x[0] * x[1])

            if model_choice == "SDXL":
                self.sdxl_resolutions = res_list
            elif model_choice == "Anima":
                self.anima_resolutions = res_list
            else:
                self.sd15_resolutions = res_list
            self.save_resolutions(model_choice, res_list)
            return ';'.join([f"{w},{h}" for w, h in res_list])

        def remove_by_size(model_choice, current, min_mp, max_mp):
            if not current.strip():
                return current
            res_list = []
            for res_pair in current.strip().split(';'):
                w, h = map(int, res_pair.split(','))
                mp = (w * h) / (1024 * 1024)
                if min_mp <= mp <= max_mp:
                    res_list.append((w, h))
            if model_choice == "SDXL":
                self.sdxl_resolutions = res_list
            elif model_choice == "Anima":
                self.anima_resolutions = res_list
            else:
                self.sd15_resolutions = res_list
            self.save_resolutions(model_choice, res_list)
            return ';'.join([f"{w},{h}" for w, h in res_list])

        # Wire up UI events
        model_type.change(fn=update_resolutions,
                         inputs=[model_type],
                         outputs=[current_resolutions])

        is_enabled.change(fn=on_enable_change,
                         inputs=[is_enabled, model_type],
                         outputs=[current_resolutions])

        add_btn.click(fn=add_resolution,
                     inputs=[model_type, current_resolutions, new_width, new_height],
                     outputs=[current_resolutions])

        add_preset_btn.click(fn=add_preset_resolution,
                           inputs=[model_type, current_resolutions, aspect_ratio, target_mpix],
                           outputs=[current_resolutions])

        reset_btn.click(fn=reset_to_defaults,
                       inputs=[model_type],
                       outputs=[current_resolutions])

        clear_btn.click(fn=clear_resolutions,
                       inputs=[model_type],
                       outputs=[current_resolutions])

        sort_btn.click(fn=sort_resolutions,
                     inputs=[model_type, current_resolutions],
                     outputs=[current_resolutions])

        remove_large.click(
            fn=lambda m, c: remove_by_size(m, c, 0, 1.0),
            inputs=[model_type, current_resolutions],
            outputs=[current_resolutions]
        )

        remove_small.click(
            fn=lambda m, c: remove_by_size(m, c, 0.3, float('inf')),
            inputs=[model_type, current_resolutions],
            outputs=[current_resolutions]
        )

        validate_btn.click(
            fn=validate_resolutions,
            inputs=[model_type, current_resolutions],
            outputs=[current_resolutions]
        )

        return [is_enabled, model_type, current_resolutions, weight_mode, min_dim, max_dim]

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def before_process_batch(self, p, is_enabled, model_type, current_resolutions, weight_mode, min_dim, max_dim, *args, **kwargs):
        if not is_enabled:
            return

        # Automatic model detection
        if hasattr(p, 'sd_model') and hasattr(p.sd_model, 'is_wan') and p.sd_model.is_wan:
            detected_model = "Anima"
        elif hasattr(p, 'sd_model') and hasattr(p.sd_model, 'is_sdxl') and p.sd_model.is_sdxl:
            detected_model = "SDXL"
        else:
            detected_model = "SD 1.5"

        # Build resolution list
        res_list = []
        try:
            if current_resolutions and current_resolutions.strip():
                for res_pair in current_resolutions.strip().split(';'):
                    try:
                        w, h = map(int, res_pair.split(','))
                        # Apply Anima validation if needed
                        if detected_model == "Anima":
                            w, h = self._validate_anima_resolution(w, h)
                        if min(w, h) >= min_dim and max(w, h) <= max_dim:
                            res_list.append((w, h))
                    except:
                        continue
        except:
            pass

        if not res_list:
            res_list = self._get_res_list_for_model(detected_model)

        # Apply min/max dimension filters
        filtered = [(w, h) for w, h in res_list if min(w, h) >= min_dim and max(w, h) <= max_dim]
        if filtered:
            res_list = filtered
        elif not res_list:
            res_list = self._get_default_list(detected_model)
            # Validate defaults for Anima if needed
            if detected_model == "Anima":
                res_list = [self._validate_anima_resolution(w, h) for w, h in res_list]

        # Apply weighting
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

        # Choose resolution
        opt_C = 4
        opt_f = 8

        # Handle seed for reproducibility
        batch_number = kwargs.get('batch_number', 0)
        seed = p.seed + batch_number if p.seed != -1 else random.randint(0, 2**32 - 1)
        random.seed(seed)

        res_tuple = random.choices(res_list, weights=weights, k=1)[0]

        # Final validation for Anima
        if detected_model == "Anima":
            res_tuple = self._validate_anima_resolution(res_tuple[0], res_tuple[1])

        # Apply chosen resolution
        p.width = res_tuple[0]
        p.height = res_tuple[1]

        # Hi-res fix adjustments
        if hasattr(p, 'enable_hr') and p.enable_hr:
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

        # Update RNG — preserve leading dims from original shape (e.g. [C] or [C,T])
        if hasattr(p, 'rng'):
            old_shape = p.rng.shape
            new_shape = tuple(list(old_shape[:-2]) + [p.height // opt_f, p.width // opt_f])
            p.rng = rng.ImageRNG(
                new_shape,
                p.seeds,
                subseeds=p.subseeds,
                subseed_strength=p.subseed_strength,
                seed_resize_from_h=p.seed_resize_from_h if hasattr(p, 'seed_resize_from_h') else 0,
                seed_resize_from_w=p.seed_resize_from_w if hasattr(p, 'seed_resize_from_w') else 0
            )

        print(f"Selected resolution: {p.width}x{p.height} (model: {detected_model})")
        if hasattr(p, 'enable_hr') and p.enable_hr:
            print(f"Target hi-res resolution: {p.hr_upscale_to_x}x{p.hr_upscale_to_y}")
