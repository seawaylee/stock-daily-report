# -*- coding: utf-8 -*-
import os
import json
import asyncio
import uuid
import base64
import httpx
from openai import OpenAI
from pydub import AudioSegment

# ================= 配置区域 =================
# LLM 配置 (用于生成剧本)
API_KEY = "sk-f750eba34c6145fc857feaf7f3851f5b"
BASE_URL = "http://127.0.0.1:8045/v1"
MODEL_NAME = "gpt-3.5-turbo"

# 豆包 TTS 配置
DOUBAO_API_URL = "https://openspeech.bytedance.com/api/v1/tts"
DOUBAO_API_KEY = "99407c21-4a41-4050-8557-78160150380c"
CLUSTER = "volcano_tts"
SPEED_RATIO = 1.5  # 语速: 1.0正常, 1.5为提速50%

INPUT_FILE = "input.txt"
OUTPUT_FILE = "podcast_doubao.mp3"
TEMP_DIR = "temp_audio_doubao"
SCRIPT_FILE = "script.json" # 优先读取此文件，如果不存在则生成

# 角色声音配置 (豆包 Voice Type)
# BV001: 通用女声
# BV002: 通用男声 (如果不发音，可能需要换其他 ID)
VOICE_MAPPING = {
    "Host": "zh_male_jingqiangkanye_moon_bigtts",  # 尝试这个新 ID
    "Guest": "zh_female_zhixingnvsheng_mars_bigtts"  # 知性女声
}
# ===========================================

async def generate_script(text):
    """使用 LLM 将文本转换为双人对话脚本"""
    # 优先检查本地是否存在 script.json
    if os.path.exists(SCRIPT_FILE):
        print(f"发现本地脚本 {SCRIPT_FILE}，直接使用...")
        try:
            with open(SCRIPT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"读取本地脚本失败: {e}，将重新生成...")

    print("正在生成对话脚本...")
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

    prompt = f"""
    请将以下文本改编成一段大约 3-5 分钟的双人播客对话脚本。
    角色：
    - Host (主持人): 负责引导话题，提问，总结。
    - Guest (嘉宾): 负责深入解释，举例。

    风格：轻松、口语化、像真实的访谈。

    输出格式必须是纯 JSON 数组，不要包含 markdown 格式标记。
    数组中每个元素是一个对象，包含 "role" 和 "text" 两个字段。
    "role" 只能是 "Host" 或 "Guest"。

    文本内容：
    {text}
    """

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "你是一个专业的播客脚本编剧。"},
                {"role": "user", "content": prompt}
            ]
        )
        content = response.choices[0].message.content
        content = content.replace("```json", "").replace("```", "").strip()
        script = json.loads(content)

        # 保存生成的脚本
        with open(SCRIPT_FILE, "w", encoding="utf-8") as f:
            json.dump(script, f, ensure_ascii=False, indent=2)

        return script
    except Exception as e:
        print(f"脚本生成失败: {e}")
        return None

async def generate_audio_segment_doubao(text, role, index):
    """使用豆包 API 生成单个音频片段"""
    voice_type = VOICE_MAPPING.get(role, "BV001")
    output_path = os.path.join(TEMP_DIR, f"{index:03d}_{role}.mp3")
    req_id = str(uuid.uuid4())

    payload = {
        "app": {
            "cluster": CLUSTER
        },
        "user": {
            "uid": "user_1"
        },
        "audio": {
            "voice_type": voice_type,
            "encoding": "mp3",
            "speed_ratio": SPEED_RATIO,
            "volume_ratio": 1.0,
            "pitch_ratio": 1.0
        },
        "request": {
            "reqid": req_id,
            "text": text,
            "operation": "query"
        }
    }

    headers = {
        "x-api-key": DOUBAO_API_KEY,
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(DOUBAO_API_URL, json=payload, headers=headers, timeout=30.0)
            response_json = response.json()

            if response.status_code == 200 and "data" in response_json:
                # 豆包返回的是 base64 编码的音频数据
                audio_base64 = response_json["data"]
                if audio_base64:
                    with open(output_path, "wb") as f:
                        f.write(base64.b64decode(audio_base64))
                    return output_path
                else:
                    print(f"片段 {index} 生成失败: 返回数据为空")
                    return None
            else:
                print(f"片段 {index} API 错误: {response_json}")
                return None

        except Exception as e:
            print(f"片段 {index} 请求异常: {e}")
            return None

async def main():
    if not os.path.exists(INPUT_FILE):
        print(f"错误: 找不到输入文件 {INPUT_FILE}")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        text = f.read()

    # 1. 获取脚本 (优先读本地 script.json)
    script = await generate_script(text)
    if not script:
        return

    # 2. 准备临时目录
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)

    # 3. 生成语音 (改为限制并发，防止触发 QPS 限制)
    print("正在调用豆包 API 合成语音(顺序执行以避免限流)...")

    # 使用 Semaphore 限制并发数为 1 (变成顺序执行)
    sem = asyncio.Semaphore(1)

    async def generate_with_limit(text, role, i):
        async with sem:
            return await generate_audio_segment_doubao(text, role, i)

    tasks = []
    for i, line in enumerate(script):
        role = line.get("role")
        text = line.get("text")
        if role and text:
            tasks.append(generate_with_limit(text, role, i))

    results = await asyncio.gather(*tasks)
    # 过滤掉生成失败的 None
    generated_files = [path for path in results if path]

    if not generated_files:
        print("错误: 没有生成任何音频片段")
        return

    # 4. 合并音频
    print(f"正在合并 {len(generated_files)} 个音频片段...")
    combined = AudioSegment.empty()
    silence = AudioSegment.silent(duration=500) # 500ms 间隔

    # 确保按文件名顺序合并 (000, 001, 002...)
    generated_files.sort()

    for file_path in generated_files:
        try:
            segment = AudioSegment.from_mp3(file_path)
            combined += segment + silence
        except Exception as e:
            print(f"合并出错 {file_path}: {e}")

    # 5. 导出
    combined.export(OUTPUT_FILE, format="mp3")
    print(f"完成！豆包版播客已保存为: {OUTPUT_FILE}")

    # 清理
    for f in generated_files:
        try: os.remove(f)
        except: pass
    try: os.rmdir(TEMP_DIR)
    except: pass

if __name__ == "__main__":
    asyncio.run(main())
