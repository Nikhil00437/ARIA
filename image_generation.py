import os, threading, datetime

def generate_image_async(prompt: str, signals, output_dir: str = None):
    def _run():
        try:
            signals.status_update.emit("🎨 Loading Stable Diffusion model...")
            signals.timeline_event.emit("image_gen", f"Generating: {prompt[:60]}")

            import torch
            from diffusers import StableDiffusionPipeline

            device = "cuda" if torch.cuda.is_available() else "cpu"
            dtype  = torch.float16 if device == "cuda" else torch.float32

            pipe = StableDiffusionPipeline.from_pretrained(
                "Manojb/stable-diffusion-2-1-base",
                torch_dtype=dtype,
            )
            pipe = pipe.to(device)

            signals.status_update.emit("🎨 Generating image...")
            image = pipe(
                prompt,
                num_inference_steps=30,
                guidance_scale=7.5,
            ).images[0]

            # Save
            if not output_dir:
                output_dir = os.path.join(os.path.expanduser("~"), "Desktop")
            os.makedirs(output_dir, exist_ok=True)
            ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(output_dir, f"aria_gen_{ts}.png")
            image.save(path)
            signals.chat_response.emit("assistant", f"✅ Image saved to `{path}`")
            signals.timeline_event.emit("image_gen", f"Saved: {path}")
            signals.status_update.emit("Ready")
        except ImportError:
            signals.chat_response.emit("assistant", "❌ `diffusers` or `torch` not installed. Run: `pip install diffusers transformers torch`")
            signals.status_update.emit("Ready")
        except Exception as e:
            signals.chat_response.emit("assistant", f"❌ Image generation failed: {e}")
            signals.status_update.emit("Ready")
    t = threading.Thread(target=_run, daemon=True)
    t.start()