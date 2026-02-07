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
DOUBAO_API_URL = "https://openspeech.bytedance.com/api/v3/tts/unidirectional"
DOUBAO_ACCESS_TOKEN = "uwHZD-4b-MVOCJYL6kS4iq-hxk2cVG9Q"
DOUBAO_APP_ID = "1946894207"
DOUBAO_RESOURCE_ID = "seed-tts-2.0"
CLUSTER = "volcano_tts"
SPEED_RATIO = 1.1  # 语速调整：1.1 (适中偏快)

# 角色声音配置 (豆包 Voice Type)
# M191 男声电台 (Upgrade from Horoscope project)
VOICE_MAPPING = {
    "Host": "zh_male_m191_uranus_bigtts",
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
    请将以下文本改编成一段大约 45秒 (约160字) 的单人播客脚本。

    角色设置：
    - 名字: 量化小万
    - 身份: 专业的AI量化交易员，说话干练、客观，喜欢用数据说话。

    要求：
    1. 必须是单人播报模式 (Monologue)。
    2. 语气要像真人在复盘，口语化，不要有朗诵腔。
    3. 开场白固定为："大家好，我是量化小万。"
    4. 严格控制篇幅，语速适中（1.5倍速下）时长控制在45秒左右。

    输出格式必须是纯 JSON 数组，不要包含 markdown 格式标记。
    数组中每个元素是一个对象，包含 "role" 和 "text" 两个字段。
    "role" 固定为 "Host"。

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
    # 按照用户要求，强制使用指定的音色ID，或者根据角色映射
    voice_type = VOICE_MAPPING.get(role, "zh_male_m191_uranus_bigtts")

    output_path = os.path.join(temp_dir, f"{index:03d}_{role}.mp3")
    req_id = str(uuid.uuid4())

    # 构建基于 req_params 的 payload (升级为 seed-tts-2.0 格式)
    payload = {
        "req_params": {
            "text": text,
            "speaker": voice_type,
            "additions": json.dumps({
                "disable_markdown_filter": False,
                "enable_language_detector": True,
                "enable_latex_tn": True,
                "disable_default_bit_rate": True,
                "max_length_to_filter_parenthesis": 0,
                "cache_config": {"text_type": 1, "use_cache": True}
            }),
            "audio_params": {
                "format": "mp3",
                "sample_rate": 24000,
                "speed_ratio": SPEED_RATIO,
                "volume_ratio": 1.0,
                "pitch_ratio": 1.0,
                # "emotion": "story"  # 股票财经类不使用story情感，使用默认以保持专业感
            }
        }
    }

    headers = {
        "X-Api-Access-Key": DOUBAO_ACCESS_TOKEN,
        "X-Api-Resource-Id": DOUBAO_RESOURCE_ID,
        "X-Api-App-Key": DOUBAO_APP_ID,
        "Content-Type": "application/json",
        "Connection": "keep-alive"
    }

    async with httpx.AsyncClient() as client:
        try:
            # 改为流式请求 (stream) 以处理分块返回的 JSON
            async with client.stream("POST", DOUBAO_API_URL, json=payload, headers=headers, timeout=60.0) as response:
                if response.status_code == 200:
                    with open(output_path, "wb") as f:
                        # 逐行读取响应
                        async for line in response.aiter_lines():
                            if not line:
                                continue
                            try:
                                # 尝试解析每一行为 JSON
                                response_json = json.loads(line)

                                # 提取音频数据
                                # 情况1: data 是直接的 base64 字符串 (常见于 simple 模式)
                                if "data" in response_json and isinstance(response_json["data"], str):
                                    audio_base64 = response_json["data"]
                                    if audio_base64:
                                        f.write(base64.b64decode(audio_base64))

                                # 情况2: data 是对象且包含 audio (常见于 verbose 模式)
                                elif "data" in response_json and isinstance(response_json["data"], dict) and "audio" in response_json["data"]:
                                    audio_base64 = response_json["data"]["audio"]
                                    if audio_base64:
                                        f.write(base64.b64decode(audio_base64))

                                # 检查是否有错误信息
                                if "message" in response_json and response_json["message"] and response_json["code"] != 0:
                                    print(f"片段 {index} API 收到错误消息: {response_json['message']}")

                            except json.JSONDecodeError:
                                # 如果解析失败，可能是非 JSON 数据?
                                # 但在流式接口中，通常都是 JSON 行。
                                # 也有可能是二进制数据混入（虽然不太可能，如果是 json 行模式）
                                pass
                            except Exception as e:
                                print(f"片段 {index} 处理行数据时出错: {e}")

                    # 检查生成的文件大小，确保不是空的
                    if os.path.exists(output_path) and os.path.getsize(output_path) > 100:
                        return output_path
                    else:
                        print(f"片段 {index} 生成的文件过小或为空")
                        return None
                else:
                    # 获取错误响应内容（如果不是流式200）
                    error_content = await response.aread()
                    print(f"片段 {index} API 错误: {response.status_code} - {error_content.decode('utf-8', errors='ignore')}")
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