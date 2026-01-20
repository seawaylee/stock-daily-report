"""
Generate AI Image Prompt for Fish Basin Trend Model Results
Style: Vintage hand-drawn illustration (matching sector_flow)
"""
import pandas as pd
from datetime import datetime
import os

def generate_fish_basin_prompt(date_str=None):
    if date_str is None:
        date_str = datetime.now().strftime('%Y%m%d')
    
    date_dir = f"results/{date_str}"
    
    # Load data
    df_indices = pd.read_excel(f"{date_dir}/fish_basin_report.xlsx")
    df_sectors = pd.read_excel(f"{date_dir}/fish_basin_sectors.xlsx")
    
    # Split by status
    bullish_indices = df_indices[df_indices['状态'] == 'YES'].head(5)
    bearish_indices = df_indices[df_indices['状态'] == 'NO'].head(3)
    
    bullish_sectors = df_sectors[df_sectors['状态'] == 'YES'].head(5)
    bearish_sectors = df_sectors[df_sectors['状态'] == 'NO'].head(5)
    
    # Format data for prompt
    def format_item(row):
        name = row['名称']
        dev = row['偏离率']
        return f"{name} ({dev})"
    
    bulls_idx = [format_item(r) for _, r in bullish_indices.iterrows()]
    bears_idx = [format_item(r) for _, r in bearish_indices.iterrows()]
    bulls_sec = [format_item(r) for _, r in bullish_sectors.iterrows()]
    bears_sec = [format_item(r) for _, r in bearish_sectors.iterrows()]
    
    prompt = f"""(masterpiece, best quality), (vertical:1.2), (aspect ratio: 10:16), (hand drawn), (illustration), (vintage style), (surrealism)

**SUBJECT**: A surreal conceptual illustration titled \"**鱼盆趋势模型**\" (Fish Basin Trend Model).

**HEADER**:
- Title at top: \"**鱼盆趋势模型**\" in **Bold Red-Gold Chinese Calligraphy**.
- Subtitle: \"SMA20 Status | {datetime.now().strftime('%Y.%m.%d')}\"

---

**SECTION 1: THE RISING TIDE (Bullish - Above SMA20)**

**Visual**: A magnificent golden koi fish pond with several fish **LEAPING UPWARD** out of the water, catching sunlight. The fish are stylized, elegant, and glowing.

**Labels on the Rising Fish (Indices)**:
{chr(10).join([f"- {item}" for item in bulls_idx])}

**Labels on Golden Lotus Flowers (Sectors)**:
{chr(10).join([f"- {item}" for item in bulls_sec])}

The water should have a warm golden-red glow. Ripples emanating outward.

---

**SECTION 2: THE DEPTHS (Bearish - Below SMA20)**

**Visual**: At the bottom of the pond, in darker, cooler blue-green water, some fish are **SINKING** or **RESTING** on the bottom. They appear tired or dormant.

**Labels on Sinking Fish (Indices)**:
{chr(10).join([f"- {item}" for item in bears_idx]) if bears_idx else "- (None today)"}

**Labels on Wilting Lotus (Sectors)**:
{chr(10).join([f"- {item}" for item in bears_sec]) if bears_sec else "- (None today)"}

The bottom should have a cooler, darker tone with subtle shadows.

---

**ART STYLE**:
- **Vintage Hand-drawn Illustration**: Warm paper texture, ink lines, watercolor washes.
- **Color Palette**: 
  - Upper half: Warm gold, crimson, orange (prosperity, rising)
  - Lower half: Cool blue-grey, teal (dormant, waiting)
- **Atmosphere**: Serene yet dynamic, like a traditional Chinese ink painting meets modern infographic.

**TEXT RENDERING**:
- Chinese labels should be clear and legible.
- Deviation percentages in **RED** for positive, **GREEN** for negative.
- Font: Hand-written Chinese calligraphy or elegant brush script.

**LAYOUT**:
- Vertical 10:16 ratio (phone wallpaper style)
- Clear visual separation between rising (top 60%) and depths (bottom 40%)

(Optimized for Nano Banana Pro3: Focus on the contrast between the leaping golden koi and the resting fish in the depths.)
"""
    
    # Save prompt
    output_file = f"{date_dir}/fish_basin_image_prompt.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(prompt)
    
    print(f"✅ Saved: {output_file}")
    return prompt

if __name__ == "__main__":
    prompt = generate_fish_basin_prompt()
    print(prompt)
