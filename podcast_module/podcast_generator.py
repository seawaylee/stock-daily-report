import os
import json
import asyncio
import uuid
import base64
import httpx
import argparse
import shutil
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

# 角色声音配置 (豆包 Voice Type)
VOICE_MAPPING = {
    "Host": "zh_male_jingqiangkanye_moon_bigtts",
    "Guest": "zh_female_zhixingnvsheng_mars_bigtts"
}
# ===========================================

async def generate_script(text, script_file):
    """使用 LLM 将文本转换为双人对话脚本"""
    if os.path.exists(script_file):
        print(f"发现本地脚本 {script_file}，直接使用...")
        try:
            with open(script_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"读取本地脚本失败: {e}，将重新生成...")

    print("正在生成对话脚本...")
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

    prompt = f"""
    请将以下文本改编成一段大约 2分钟以内 的双人播客对话脚本。
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

        os.makedirs(os.path.dirname(script_file), exist_ok=True)
        with open(script_file, "w", encoding="utf-8") as f:
            json.dump(script, f, ensure_ascii=False, indent=2)

        return script
    except Exception as e:
        print(f"脚本生成失败: {e}")
        return None

async def generate_audio_segment_doubao(text, role, index, temp_dir):
    """使用豆包 API 生成单个音频片段"""
    voice_type = VOICE_MAPPING.get(role, "BV001")
    output_path = os.path.join(temp_dir, f"{index:03d}_{role}.mp3")
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
    parser = argparse.ArgumentParser(description="Generate Podcast Audio")
    parser.add_argument("--input", required=True, help="Input text file path")
    parser.add_argument("--output", required=True, help="Output mp3 file path")
    args = parser.parse_args()

    input_file = args.input
    output_file = args.output

    base_name = os.path.splitext(os.path.basename(input_file))[0]
    output_dir = os.path.dirname(output_file)
    script_file = os.path.join(output_dir, f"../scripts/{base_name}_script.json") # Save scripts in a separate folder
    temp_dir = os.path.join(output_dir, f"temp_{base_name}")

    if not os.path.exists(input_file):
        print(f"错误: 找不到输入文件 {input_file}")
        return

    print(f"输入文件: {input_file}")
    print(f"输出文件: {output_file}")

    with open(input_file, "r", encoding="utf-8") as f:
        text = f.read()

    script = await generate_script(text, script_file)
    if not script:
        return

    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    print("正在调用豆包 API 合成语音(顺序执行以避免限流)...")
    sem = asyncio.Semaphore(1)

    async def generate_with_limit(text, role, i):
        async with sem:
            return await generate_audio_segment_doubao(text, role, i, temp_dir)

    tasks = []
    for i, line in enumerate(script):
        role = line.get("role")
        text = line.get("text")
        if role and text:
            tasks.append(generate_with_limit(text, role, i))

    results = await asyncio.gather(*tasks)
    generated_files = [path for path in results if path]

    if not generated_files:
        print("错误: 没有生成任何音频片段")
        return

    print(f"正在合并 {len(generated_files)} 个音频片段...")
    combined = AudioSegment.empty()
    silence = AudioSegment.silent(duration=500)

    generated_files.sort()

    for file_path in generated_files:
        try:
            segment = AudioSegment.from_mp3(file_path)
            combined += segment + silence
        except Exception as e:
            print(f"合并出错 {file_path}: {e}")

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    combined.export(output_file, format="mp3")
    print(f"完成！豆包版播客已保存为: {output_file}")

    try:
        shutil.rmtree(temp_dir)
    except Exception as e:
        print(f"清理临时目录失败: {e}")

if __name__ == "__main__":
    asyncio.run(main())