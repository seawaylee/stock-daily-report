import os
import subprocess
import sys

# Add project root to sys.path to ensure imports work
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from common.video_generator import generate_video_from_image_and_audio

def run_podcast_generation(input_text_path, output_audio_path):
    """
    Calls the podcast_generator.py script via subprocess.
    """
    script_path = os.path.join(project_root, "podcast_module", "podcast_generator.py")

    if not os.path.exists(script_path):
        print(f"❌ Error: Podcast generator script not found at {script_path}")
        return False

    cmd = [
        sys.executable,
        script_path,
        "--input", input_text_path,
        "--output", output_audio_path
    ]

    print(f"🎙️ Generating Audio from {os.path.basename(input_text_path)}...")
    try:
        # Run and wait
        subprocess.run(cmd, check=True)
        if os.path.exists(output_audio_path):
            return True
        else:
            print("❌ Audio file was not created.")
            return False
    except subprocess.CalledProcessError as e:
        print(f"❌ Podcast Generation Failed: {e}")
        return False

def run_full_media_pipeline(text_path, image_path, base_output_dir, basename):
    """
    Runs the full media pipeline: Text -> Audio -> Video.

    Args:
        text_path: Path to the input text file (podcast script).
        image_path: Path to the cover image.
        base_output_dir: Base directory for the date (e.g., results/20260207).
        basename: Basename for output files (e.g., market_sentiment).
    """
    # Define paths
    audio_dir = os.path.join(base_output_dir, "mp3")
    video_dir = os.path.join(base_output_dir, "video")

    os.makedirs(audio_dir, exist_ok=True)
    os.makedirs(video_dir, exist_ok=True)

    audio_path = os.path.join(audio_dir, f"{basename}.mp3")
    video_path = os.path.join(video_dir, f"{basename}.mp4")

    print(f"\n🎬 Starting Media Pipeline for {basename}...")

    # 1. Generate Audio
    if run_podcast_generation(text_path, audio_path):
        # 2. Generate Video
        generate_video_from_image_and_audio(image_path, audio_path, video_path)
    else:
        print("⏭️ Skipping video generation due to audio failure.")
