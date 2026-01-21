
import akshare as ak
import pandas as pd
import random

from datetime import datetime
import os
import platform


def get_sector_flow(sector_type='行业资金流'):
    """获取板块资金流排名 (返回 Top 10 流入和 Top 10 流出)"""
    try:
        print(f"正在获取 {sector_type} 数据...")
        import time
        df = None
        
        # Plan A: THS (Tonghuashun) - prioritized
        # Plan B: EastMoney (Fallback)
        
        data_source = "THS" 
        
        # --- THS Implementation ---
        try:
            print("尝试数据源: 同花顺 (THS)...")
            df_ths = ak.stock_board_industry_summary_ths()
            if df_ths is not None and not df_ths.empty:
                # Columns: ['序号', '板块', '涨跌幅', '总成交量', '总成交额', '净流入', ...]
                # Renaming for compatibility
                df_ths = df_ths.rename(columns={'板块': '名称', '净流入': 'net_flow'})
                
                # Assume 'net_flow' from THS is already in '亿' (Billions) based on debug.
                df_ths['net_flow_billion'] = pd.to_numeric(df_ths['net_flow'], errors='coerce')
                
                # Ensure we have both Inflow and Outflow
                top_inflow = df_ths.sort_values(by='net_flow_billion', ascending=False).head(10)
                top_outflow = df_ths.sort_values(by='net_flow_billion', ascending=True).head(10)
                
                # Rename columns to match expected output for prompt generator
                return top_inflow, top_outflow, '名称', 'net_flow_billion'

        except Exception as e:
            print(f"THS source failed: {e}")
            df_ths = None # Ensure df_ths is cleared if it failed
            
        # --- Fallback to EastMoney if THS fails ---
        print("尝试数据源: 东方财富 (EastMoney)...")
        df_em = None
        for i in range(2): # Reduced retries for EM
            try:
                df_em = ak.stock_sector_fund_flow_rank(indicator='今日', sector_type=sector_type)
                if df_em is not None and not df_em.empty:
                     data_source = "EM"
                     break
            except Exception as e:
                print(f"尝试 {i+1}/2 失败: {e}")
                time.sleep(1)
        
        if df_em is None or df_em.empty:
            print(f"❌ 最终获取 {sector_type} 失败 (THS和EM均失败)")
            return None
             
        # Process EastMoney data if it was successfully retrieved
        target_col = None
        name_col = None
        
        # 优先寻找 "主力净流入"
        for col in df_em.columns:
            if "主力" in col and "净流入" in col and "净额" in col:
                target_col = col
                break
        
        # Fallback
        if not target_col:
             for col in df_em.columns:
                if "净流入" in col and "净额" in col and "今日" in col:
                    target_col = col
                    break

        for col in df_em.columns:
             if "名称" in col:
                name_col = col
                break
                
        if not target_col or not name_col:
            print(f"❌ 东方财富数据列识别失败: target_col={target_col}, name_col={name_col}")
            return None
            
        # 确保数值类型
        df_em['net_flow_billion'] = pd.to_numeric(df_em[target_col], errors='coerce') / 100000000
        
        # 排序
        top_inflow = df_em.sort_values(by='net_flow_billion', ascending=False).head(10)
        top_outflow = df_em.sort_values(by='net_flow_billion', ascending=True).head(10)
        
        return top_inflow, top_outflow, name_col, 'net_flow_billion'
        
    except Exception as e:
        print(f"获取 {sector_type} 失败: {e}")
        return None


def get_creative_title(top_names):
    """根据Top板块生成生动标题"""
    if not top_names:
        return "资金涌入"
        
    # 1. 组合判断 (Combos)
    # 金融
    finance_kw = ['证券', '银行', '保险', '多元金融']
    fin_count = sum(1 for n in top_names if any(k in n for k in finance_kw))
    if fin_count >= 2:
        return random.choice(["大金融爆发", "金三胖发力", "权重搭台", "金融狂欢"])
        
    # 科技
    tech_kw = ['半导体', '软件', '计算机', '通信', '电子', '芯片', '光刻机', '消费电子']
    tech_count = sum(1 for n in top_names if any(k in n for k in tech_kw))
    if tech_count >= 2:
        return random.choice(["科技狂欢", "硬科技突围", "科创大涨", "算力崛起", "芯火燎原"])
        
    # 新能源
    new_energy_kw = ['光伏', '电池', '风电', '能源金属', '电网', '储能']
    ne_count = sum(1 for n in top_names if any(k in n for k in new_energy_kw))
    if ne_count >= 2:
        return random.choice(["新能车飙车", "绿电狂飙", "光储盛宴", "赛道股回归", "电光火石"])

    # 医药医疗
    med_kw = ['医药', '医疗', '中药', '生物制品', '化学制药']
    med_count = sum(1 for n in top_names if any(k in n for k in med_kw))
    if med_count >= 2:
        return random.choice(["医药反攻", "吃药行情", "杏林春暖", "大健康起舞"])

    # 消费
    con_kw = ['酿酒', '食品', '旅游', '家电', '零售', '商业百货']
    con_count = sum(1 for n in top_names if any(k in n for k in con_kw))
    if con_count >= 2:
        return random.choice(["大消费复苏", "喝酒吃肉", "消费回暖", "醉美A股"])

    # 2. Top 1 单一判断 (Top 1 Specific)
    first = top_names[0]
    
    mapping = {
        # 大金融
        "证券": ["牛市旗手", "券商暴动", "旗手扛鼎"],
        "银行": ["大象起舞", "定海神针", "银行护盘"],
        "保险": ["险资进场", "蓝筹核心"],
        "多元金融": ["金融活跃", "金控发力"],

        # 核心科技
        "半导体": ["芯火燎原", "国产之光", "缺芯涨价"],
        "芯片": ["芯火燎原", "国产之光"],
        "软件": ["软件定义", "信创崛起", "数字底座"],
        "计算机": ["算力为王", "AI风口", "数字经济"],
        "通信": ["5G先锋", "信息高速", "云网融合"],
        "电子": ["电子狂潮", "硬件复苏"],
        "消费电子": ["果链反弹", "消费复苏"],
        "光刻机": ["突破封锁", "光刻机魂"],
        "PCB": ["电子之母", "硬板崛起"],
        
        # 新能源/赛道
        "光伏": ["光芒万丈", "追光逐日", "光伏反转"],
        "电池": ["能动未来", "锂想主义", "电池革命"],
        "能源金属": ["锂钴齐飞", "资源为王"],
        "风电": ["御风而行", "风电抢装"],
        "电网": ["特高压起", "电网升级"],
        
        # 大消费
        "酿酒": ["把酒言欢", "醉美A股", "喝酒吃药"],
        "食品": ["舌尖美味", "吃喝行情"],
        "家电": ["智能家居", "家电下乡"],
        "旅游": ["诗与远方", "报复消费"],
        "航空": ["起飞时刻", "云端漫步"],
        "酒店": ["复苏先锋", "出行回暖"],
        "影视": ["票房大卖", "娱乐至上"],
        "游戏": ["玩赚世界", "元宇宙风口"],
        "汽车": ["极速狂飙", "弯道超车"],
        
        # 医药医疗
        "医药": ["药神归来", "健康中国"],
        "医疗": ["器械突围", "医疗新基建"],
        "中药": ["国粹传承", "中药瑰宝"],
        "生物": ["创新药魂", "生物科技"],

        # 周期/资源
        "石油": ["两桶油", "黑金狂舞"],
        "煤炭": ["煤飞色舞", "黑金时代"],
        "有色": ["有色王者", "顺周期"],
        "钢铁": ["钢铁洪流", "基建脊梁"],
        "化工": ["化工茅起", "涨价题材"],
        "黄金": ["金光闪闪", "避险之王"],
        "稀土": ["稀土永磁", "工业维生素"],

        # 地产基建
        "房地产": ["金辉重现", "地产反弹", "保交楼"],
        "工程建设": ["基建狂魔", "稳增长"],
        "水泥": ["建材龙头", "涨价预期"],
        "建材": ["地产链动", "装修旺季"],

        # 题材概念
        "低空经济": ["飞行汽车", "低空腾飞"],
        "人工智能": ["AI觉醒", "智领未来"],
        "机器人": ["人机共舞", "智能制造"],
        "卫星导航": ["星链计划", "天地互联"],
        "量子科技": ["量子纠缠", "未来科技"],
        "华为": ["遥遥领先", "鸿蒙生态"],
        "数字货币": ["数字人民币", "金融科技"],
    }
    
    # 模糊匹配
    for key, opts in mapping.items():
        if key in first:
            return random.choice(opts)
            
    # 3. 通用兜底 (Fallback)
    suffixes = ["领涨", "爆发", "抢筹", "崛起", "突围", "吸金", "霸榜", "大涨"]
    # 取板块名简写 (e.g. remove '行业')
    short_name = first.replace('行业', '').replace('概念', '').replace('板块', '')
    return f"{short_name}{random.choice(suffixes)}"


def generate_prompt(industry_inflow, industry_outflow, output_path="results/sector_flow_image_prompt.txt"):
    """
    生成 Nano Banana Pro 优化的 AI 绘画提示词 (手绘风格)
    """
    
    # 获取数据 Top 3 Inflow (Name, Flow)
    top_in_data = []
    for i, (_, row) in enumerate(industry_inflow.head(3).iterrows()):
         val = float(row['net_flow_billion'])
         top_in_data.append({'name': row['名称'], 'flow': f"+{val:.1f}亿"})
    
    # 获取 Top 10 Outflow (Name, Flow)
    top_out_list = []
    for i, (_, row) in enumerate(industry_outflow.head(10).iterrows()):
         val = float(row['net_flow_billion'])
         top_out_list.append(f"{row['名称']} ({val:.1f}亿)")
         
    outflow_text = ", ".join(top_out_list)

    # 动态构建物体描述
    # e.g. "Center object representing [Sector]"
    
    def get_obj_desc(idx):
        if idx < len(top_in_data):
            item = top_in_data[idx]
            return item['name'], item['flow']
        return "Unknown", ""

    name_c, flow_c = get_obj_desc(0)
    name_l, flow_l = get_obj_desc(1)
    name_r, flow_r = get_obj_desc(2)

    # 智能生成标题
    top_names = [d['name'] for d in top_in_data]
    selected_title = get_creative_title(top_names)

    prompt_content = f"""
(masterpiece, best quality), (vertical:1.2), (aspect ratio: 10:16), (hand drawn), (illustration), (vintage style), (surrealism)

**SUBJECT**: A surreal conceptual illustration.

**HEADER TEXT**:
- At the top of the image, elegantly integrate the text "**{selected_title}**" using **Artistic Chinese Calligraphy**.
- **BACKGROUND for Text**: Place the text on a **Red Ink Grunge / Paint Brush Stroke** background to make it pop.
- **Text Color**: Use **Gold or White** text to contrast strongly against the red background.
- The text should be **clearly visible** and distinct from the rest of the illustration.

1. **THE GIANTS (Top Inflow Sectors)**:
   Three COLOSSAL, SYMBOLIC MONUMENTS towering in the center, representing the top winning industries. (NON-HUMANOID OBJECTS)
   - **CENTER (Largest)**: A giant symbolic object representing **"{name_c}"**. It should be a physical object or structure, NOT A PERSON. 
     **Text label on it**: "{name_c}" (Black Bold) and "{flow_c}" (Small RED text next to it).
   - **LEFT**: A massive symbolic object representing **"{name_l}"**. (Physical object, non-human).
     **Text label on it**: "{name_l}" (Black Bold) and "{flow_l}" (Small RED text).
   - **RIGHT**: A massive symbolic object representing **"{name_r}"**. (Physical object, non-human).
     **Text label on it**: "{name_r}" (Black Bold) and "{flow_r}" (Small RED text).

2. **THE WORSHIPPERS (Top Outflow Sectors)**:
   In the **FOREGROUND**, a group of **LARGE**, kneeling figures (pilgrims) with their backs facing the viewer. 
   - They should be **CLOSE TO THE CAMERA** so their backs take up significant space.
   - **CRITICAL**: The text labels on their backs must be **LARGE and CLEARLY LEGIBLE**.
   - **Labels on backs**: {outflow_text}
   - **TEXT STYLING (Split Style)**:
     - **Sector Name**: Use **White or Light Grey** text. Uniform font.
     - **Money Number**: Use **Bright Neon Green** text (e.g., -157.4亿) to represent outflow. 
     - **NO BACKGROUND PATCH**. Just the text floating on the dark clothing.
     - Ensure the text has a slight **Glow** for high visibility.
   - **COLOR**: These figures must be **DARK GREEN, GREY, or COLD COLORS** to represent outflow/loss. **ABSOLUTELY NO RED CLOTHING** for these figures. They should look gloomy.


**ART STYLE**: 
- **Vintage Hand-drawn Illustration**: Warm paper texture background, ink lines, watercolor washes.
- **Atmosphere**: Epic, religious scale, slightly dystopian but artistic.
- **Colors**: Sepia, warm brown, faded red (giants), dull green/grey (worshippers).

**TEXT RENDERING**:
- Please ensure the Chinese text labels for sectors are visible.
- Font style: Hand-written Chinese calligraphy or block print.

(Optimized for Nano Banana Pro: Focus on the contrast between the giant objects and the tiny kneeling crowd.)
"""
    
    with open(output_path, "w", encoding='utf-8') as f:
        f.write(prompt_content.strip())
    
    print(f"Image Prompt saved to {output_path} (Title: {selected_title})")



def run(date_dir=None):
    """每日定期运行的入口函数"""
    print(f"\n=== A股板块资金流向统计 ({datetime.now().strftime('%Y-%m-%d')}) ===")
    
    # 1. 获取数据
    res_industry = get_sector_flow('行业资金流')
    res_concept = get_sector_flow('概念资金流')
    
    if res_industry and res_concept:
        # 2. 打印文本表格
        inflow, outflow, name_col, flow_col = res_industry
        
        print("\\n🏆 行业板块 - 主力净流入 Top 10")
        for i, (_, row) in enumerate(inflow.iterrows()):
            print(f"{i+1}. {row[name_col]:<10} {row[flow_col]:.2f}亿")

        print("\\n😭 行业板块 - 主力净流出 Top 10")
        for i, (_, row) in enumerate(outflow.iterrows()):
            print(f"{i+1}. {row[name_col]:<10} {row[flow_col]:.2f}亿")
            
        # 3. 确定输出路径
        if date_dir:
            prompt_dir = os.path.join(date_dir, "AI提示词")
            if not os.path.exists(prompt_dir):
                os.makedirs(prompt_dir, exist_ok=True)
            prompt_path = os.path.join(prompt_dir, "资金流向_Prompt.txt")
        else:
            # 默认路径: 自动获取今日日期
            today_dir = datetime.now().strftime('%Y%m%d')
            prompt_dir = os.path.join("results", today_dir, "AI提示词")
            if not os.path.exists(prompt_dir):
                os.makedirs(prompt_dir, exist_ok=True)
            prompt_path = os.path.join(prompt_dir, "资金流向_Prompt.txt")

        # 4. 生成提示词
        generate_prompt(inflow, outflow, output_path=prompt_path)
        
        print("✅ 板块资金流分析已完成")
        return True
    else:
        print("⚠️ 数据获取不完整，跳过板块分析")
        return False


if __name__ == "__main__":
    run()
