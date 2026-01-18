#!/usr/bin/env python3
"""
Agent工作流执行器
自动处理agent_tasks目录中的所有任务并生成结果
"""
import os
import sys
import glob
from datetime import datetime

def find_latest_date_dir():
    """查找最新的日期目录"""
    results_dir = "results"
    if not os.path.exists(results_dir):
        print("❌ results目录不存在")
        return None
    
    # 查找所有日期目录
    date_dirs = [d for d in os.listdir(results_dir) 
                 if os.path.isdir(os.path.join(results_dir, d)) and d.isdigit()]
    
    if not date_dirs:
        print("❌ 未找到日期目录")
        return None
    
    # 返回最新的目录
    latest_dir = max(date_dirs)
    return os.path.join(results_dir, latest_dir)

def process_task_file(task_file, output_file):
    """
    处理单个任务文件
    读取任务提示词，然后提示用户使用Agent处理
    """
    print(f"\n{'='*70}")
    print(f"📋 任务文件: {task_file}")
    print(f"📝 输出文件: {output_file}")
    print(f"{'='*70}\n")
    
    # 读取任务内容
    with open(task_file, 'r', encoding='utf-8') as f:
        task_content = f.read()
    
    print("📖 任务内容预览 (前500字符):")
    print("-" * 70)
    print(task_content[:500])
    if len(task_content) > 500:
        print("...\n(内容已截断)")
    print("-" * 70)
    
    # 检查输出文件是否已存在
    if os.path.exists(output_file):
        print(f"✅ 输出文件已存在，跳过处理")
        return True
    
    print("\n⚠️  此任务需要Agent处理")
    print("请将以上任务内容提供给Agent，或使用 /daily_stock_analysis 工作流")
    print("\n等待处理中...")
    
    return False

def main():
    print("🤖 Agent工作流执行器")
    print("="*70)
    
    # 查找最新的日期目录
    date_dir = find_latest_date_dir()
    if not date_dir:
        return
    
    print(f"📂 工作目录: {date_dir}")
    
    # 检查agent_tasks目录
    agent_task_dir = os.path.join(date_dir, "agent_tasks")
    if not os.path.exists(agent_task_dir):
        print(f"❌ 未找到任务目录: {agent_task_dir}")
        print("请先运行 python run_ai_analysis.py 生成任务")
        return
    
    # 创建agent_outputs目录
    agent_output_dir = os.path.join(date_dir, "agent_outputs")
    os.makedirs(agent_output_dir, exist_ok=True)
    
    # 定义任务映射
    task_mapping = {
        "task_analysis.txt": "result_analysis.txt",
        "task_xiaohongshu.txt": "result_xiaohongshu.txt",
        "task_image_prompt.txt": "result_image_prompt.txt"
    }
    
    # 处理所有任务
    all_completed = True
    for task_file, output_file in task_mapping.items():
        task_path = os.path.join(agent_task_dir, task_file)
        output_path = os.path.join(agent_output_dir, output_file)
        
        if os.path.exists(task_path):
            completed = process_task_file(task_path, output_path)
            if not completed:
                all_completed = False
        else:
            print(f"\n⚠️  任务文件不存在: {task_file}")
    
    print("\n" + "="*70)
    if all_completed:
        print("✅ 所有任务已完成！")
        print("请重新运行 python run_ai_analysis.py 生成最终报告")
    else:
        print("⏸️  部分任务等待处理")
        print("\n📝 下一步操作:")
        print("1. 阅读上面显示的任务内容")
        print("2. 使用Agent处理这些任务（遵循任务中的所有要求）")
        print("3. 将Agent的回复保存到对应的输出文件")
        print("4. 或者运行 /daily_stock_analysis 工作流自动处理")
    print("="*70)

if __name__ == "__main__":
    main()
