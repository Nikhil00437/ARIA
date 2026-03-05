import os, re, torch
from diffusers import StableDiffusionPipeline

class ImageGenerator:
    def __init__(self):
        self.pipe = None
        self.device = "cuda" if self._cuda_available() else "cpu"

    def _cuda_available(self):
        try:
            return torch.cuda.is_available()
        except Exception:
            return False

    def load_model(self):
        if self.pipe is not None: return
        model_id = "Manojb/stable-diffusion-2-1-base"
        print(f"[ImageGenerator] Loading model on {self.device}...")
        if self.device == "cuda":
            self.pipe = StableDiffusionPipeline.from_pretrained(
                model_id,
                torch_dtype=torch.float16
            ).to("cuda")
        else:
            self.pipe = StableDiffusionPipeline.from_pretrained(
                model_id
            ).to("cpu")
        self.pipe.safety_checker = None
        print("[ImageGenerator] Model loaded.")

    def generate(self, prompt: str, output_path: str = "generated.png") -> str:
        self.load_model()
        print(f"[ImageGenerator] Generating: '{prompt}'")
        result = self.pipe(prompt, num_inference_steps=20, guidance_scale=7.5)
        image = result.images[0]
        # Ensure output directory exists
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        image.save(output_path)
        print(f"[ImageGenerator] Saved to: {output_path}")
        return output_path

    @staticmethod
    def safe_filename(prompt: str, max_length: int = 50) -> str:
        safe = re.sub(r'[^\w\s-]', '', prompt).strip().replace(' ', '_')
        return safe[:max_length] or "generated"

#if __name__ == "__main__":
 #   gen = ImageGenerator()
  #  gen.generate("a black cat sleeping on a soft blanket", "cat1.png")
   # print("Done.")
