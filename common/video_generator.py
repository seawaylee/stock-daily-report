import os
import subprocess

def generate_video_from_image_and_audio(image_path, audio_path, output_path):
    """
    Combines an image and an audio file into an MP4 video.
    Video duration will match audio duration.

    Args:
        image_path (str): Path to the static image.
        audio_path (str): Path to the audio file (mp3/wav).
        output_path (str): Path for the output video (mp4).

    Returns:
        bool: True if successful, False otherwise.
    """
    if not os.path.exists(image_path):
        print(f"❌ Video Gen Error: Image not found at {image_path}")
        return False
    if not os.path.exists(audio_path):
        print(f"❌ Video Gen Error: Audio not found at {audio_path}")
        return False

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # FFmpeg command
    # -loop 1: Loop image
    # -i image: Input image
    # -i audio: Input audio
    # -c:v libx264: Video codec
    # -tune stillimage: Optimize for static image
    # -c:a aac: Audio codec
    # -b:a 192k: Audio bitrate
    # -pix_fmt yuv420p: Compatibility
    # -shortest: Finish when the shortest input (audio) ends
    # -y: Overwrite output

    cmd = [
        "ffmpeg",
        "-y",
        "-loop", "1",
        "-i", image_path,
        "-i", audio_path,
        "-c:v", "libx264",
        "-tune", "stillimage",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        output_path
    ]

    print(f"🎬 synthesizing video: {output_path}...")
    try:
        # Run ffmpeg with captured output to avoid cluttering console unless error
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if result.returncode == 0:
            print(f"✅ Video created successfully: {output_path}")
            return True
        else:
            print(f"❌ Video creation failed. FFmpeg stderr:\n{result.stderr}")
            return False

    except Exception as e:
        print(f"❌ Exception during video generation: {e}")
        return False
