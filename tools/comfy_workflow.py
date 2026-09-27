"""ComfyUI の API 形式ワークフローを生成する。
  t2i : Krea-2 Turbo でテキストから生成
  edit: Qwen Image Edit 2511 (Lightning 4step) で参照画像から派生
usage: python comfy_workflow.py t2i  <name> <seed> <w> <h> <prompt_file> [rmbg]
       python comfy_workflow.py edit <name> <seed> <w> <h> <prompt_file> <ref1[,ref2]> [rmbg]
"""
import json, sys

mode, name, seed, w, h, pfile = sys.argv[1:7]
rest = sys.argv[7:]
prompt = open(pfile, encoding='utf-8').read().strip()
rmbg = 'rmbg' in rest

if mode == 't2i':
    wf = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "krea2_turbo_fp8_scaled.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen3vl_4b_fp8_scaled.safetensors", "type": "krea2", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "qwen_image_vae.safetensors"}},
        "20": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": prompt}},
        "21": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["20", 0]}},
        "30": {"class_type": "EmptyLatentImage", "inputs": {"width": int(w), "height": int(h), "batch_size": 1}},
        "31": {"class_type": "KSampler", "inputs": {"model": ["1", 0], "positive": ["20", 0], "negative": ["21", 0], "latent_image": ["30", 0],
                                                    "seed": int(seed), "steps": 8, "cfg": 1, "sampler_name": "euler", "scheduler": "simple", "denoise": 1}},
    }
else:
    refs = rest[0].split(',')
    wf = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "qwen_image_edit_2511_int8_convrot.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen_2.5_vl_7b_fp8_scaled.safetensors", "type": "qwen_image", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "qwen_image_vae.safetensors"}},
        "4": {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["1", 0], "shift": 3.1}},
        "5": {"class_type": "CFGNorm", "inputs": {"model": ["4", 0], "strength": 1, "pre_cfg": False}},
        "6": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["5", 0], "lora_name": "Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors", "strength_model": 1}},
        "20": {"class_type": "TextEncodeQwenImageEditPlus", "inputs": {"clip": ["2", 0], "vae": ["3", 0], "prompt": prompt}},
        "21": {"class_type": "TextEncodeQwenImageEditPlus", "inputs": {"clip": ["2", 0], "vae": ["3", 0], "prompt": ""}},
        "22": {"class_type": "FluxKontextMultiReferenceLatentMethod", "inputs": {"conditioning": ["20", 0], "reference_latents_method": "index_timestep_zero"}},
        "23": {"class_type": "FluxKontextMultiReferenceLatentMethod", "inputs": {"conditioning": ["21", 0], "reference_latents_method": "index_timestep_zero"}},
        "30": {"class_type": "EmptySD3LatentImage", "inputs": {"width": int(w), "height": int(h), "batch_size": 1}},
        "31": {"class_type": "KSampler", "inputs": {"model": ["6", 0], "positive": ["22", 0], "negative": ["23", 0], "latent_image": ["30", 0],
                                                    "seed": int(seed), "steps": 4, "cfg": 1, "sampler_name": "euler", "scheduler": "simple", "denoise": 1}},
    }
    for i, r in enumerate(refs):
        nid = str(10 + i)
        wf[nid] = {"class_type": "LoadImage", "inputs": {"image": r}}
        wf["20"]["inputs"][f"image{i+1}"] = [nid, 0]
        wf["21"]["inputs"][f"image{i+1}"] = [nid, 0]

wf["32"] = {"class_type": "VAEDecode", "inputs": {"samples": ["31", 0], "vae": ["3", 0]}}
wf["33"] = {"class_type": "SaveImage", "inputs": {"images": ["32", 0], "filename_prefix": f"tyajin/{name}_raw"}}
if rmbg:
    wf["40"] = {"class_type": "LoadBackgroundRemovalModel", "inputs": {"bg_removal_name": "birefnet.safetensors"}}
    wf["41"] = {"class_type": "RemoveBackground", "inputs": {"bg_removal_model": ["40", 0], "image": ["32", 0]}}
    wf["42"] = {"class_type": "InvertMask", "inputs": {"mask": ["41", 0]}}
    wf["43"] = {"class_type": "JoinImageWithAlpha", "inputs": {"image": ["32", 0], "alpha": ["42", 0]}}
    wf["44"] = {"class_type": "SaveImage", "inputs": {"images": ["43", 0], "filename_prefix": f"tyajin/{name}"}}

json.dump(wf, open(f"wf_{name}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"wf_{name}.json")
