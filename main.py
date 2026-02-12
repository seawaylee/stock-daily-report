#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified Entry Point for Stock Daily Report System.
Supports 4 independent modules:
1. Fish Basin (Trend Analysis)
2. Stock Selection (AI Analysis)
3. Sector Flow (Funds Flow)
4. Market Ladder (Sentiment/Limit-up)
"""
import sys
import os
import argparse
from datetime import datetime, timedelta

# Enable Simple Network Logging (No Proxies/Retries)
try:
    from common import network
    network.apply_patch()
except ImportError:
    pass

# Convert string "YYYYMMDD" to path "results/YYYYMMDD"
def get_date_dir(date_str=None):
    if not date_str:
        now = datetime.now()
        # If before 09:00 AM, assume we are reviewing the Previous Trading Day (late night session)
        if now.hour < 9:
            date_str = (now - timedelta(days=1)).strftime('%Y%m%d')
            print("Current time {} before 09:00. Auto-selecting Yesterday: {}".format(now.strftime('%H:%M'), date_str))
        else:
            date_str = now.strftime('%Y%m%d')
    return os.path.join("results", date_str), date_str

def run_fish_basin(args):
    print("\n=== [Module 1] Fish Basin Trend Analysis ===")
    from modules.fish_basin import fish_basin, fish_basin_sectors
    from modules.fish_basin import generate_combined_prompt
    import pandas as pd
    
    # 1. Indices (In-Memory)
    print("--- Part A: Indices ---")
    df_index = fish_basin.run(args.date_dir, save_excel=True)

    # 2. Sectors (In-Memory)
    print("\n--- Part B: Sectors ---")
    df_sector = fish_basin_sectors.run(args.date_dir, save_excel=True)
    
    # 3. Save Merged Excel (Index and Sector together in ONE sheet)
    if not df_index.empty or not df_sector.empty:
        merged_path = os.path.join(args.date_dir, "趋势模型_合并.xlsx")
        print(f"\nSaving Merged Excel: {merged_path}")
        try:
            from modules.fish_basin.fish_basin_helper import save_merged_excel
            save_merged_excel(df_index, df_sector, merged_path)
        except Exception as e:
            print(f"Failed to save Merged Excel: {e}")

        # 4. Generate Combined Prompt
        print("\n--- Part C: Generate Combined Prompt ---")
        generate_combined_prompt.generate_combined_prompt(args.date_str, df_index, df_sector)
    
    return True


def run_b1_selection(args):
    print("\n=== [Module 2] B1 Stock Selection & AI Analysis ===")
    from modules.stock_selection import b1_selection
    force = getattr(args, 'force', False)
    return b1_selection.run(args.date_dir, force=force)

def run_sector_flow(args):
    print("\n=== [Module 3] Sector Funds Flow ===")
    from modules.sector_flow import sector_flow
    return sector_flow.run(args.date_dir)

def run_market_ladder(args):
    print("\n=== [Module 4] Market Limit-up Ladder ===")
    from modules.market_ladder import generate_ladder_prompt

    # Needs date_str and output_dir
    # args.date_dir is full path "results/20260122"
    # generate_ladder_prompt expects (date_str, output_dir)
    return generate_ladder_prompt.run(args.date_str, args.date_dir)

def run_core_news (args):
    print("\n=== [Module 7] Core News Monitor ===")
    from modules.core_news import core_news_monitor
    
    # Check if Fri/Sat/Sun
    dt = datetime.strptime(args.date_str, '%Y%m%d')
    is_weekend = dt.weekday() >= 4
    
    return core_news_monitor.run(args.date_str, args.date_dir, run_weekly=is_weekend)

def run_weekly_preview(args):
    print("\n=== [Module 8] Weekly Events Preview ===")
    from modules.weekly_preview import generate_weekly_preview
    
    # Check if Fri/Sat/Sun
    dt = datetime.strptime(args.date_str, '%Y%m%d')
    is_weekend = dt.weekday() >= 4
    
    return generate_weekly_preview.run(args.date_str, args.date_dir, run_weekly=is_weekend)

def run_earnings_analysis(args):
    print("\n=== [Module 9] Earnings Analysis ===")
    from modules.earnings import run as run_earnings
    return run_earnings(args.date_str, args.date_dir)

def run_earnings_prompt(args):
    print("\n=== [Module 10] Earnings Performance Prompt ===")
    from modules.earnings import run_prompt_gen
    return run_prompt_gen(args.date_str, args.date_dir)

def run_market_sentiment(args):
    print("\n=== [Module 11] Market Sentiment Index ===")
    from modules.market_sentiment import market_sentiment

    # Run analysis (Now generates final 市场情绪_Prompt.txt with hexagonal radar chart)
    analyzer = market_sentiment.run_analysis(args.date_str)

    # DISABLED: No longer generate intermediate files
    # The final 市场情绪_Prompt.txt now contains complete Midjourney/SD prompt
    return True

def run_close_report(args):
    print("\n=== [Module 13] Close Report Prompt ===")
    from modules.close_report import run as run_close_report_module
    return run_close_report_module(args.date_str, args.date_dir)

def run_dragon_tiger(args):
    print("\n=== [Module 12] Dragon Tiger List ===")
    from modules.dragon_tiger import dragon_tiger
    return dragon_tiger.run(args.date_dir)

def run_all(args):
    print("🌟 Starting Full Daily Workflow (Parallel Execution) 🌟")
    print(f"Target Directory: {args.date_dir}")
    
    # Determine Weekend Status
    dt = datetime.strptime(args.date_str, '%Y%m%d')
    is_weekend = dt.weekday() >= 4
    if is_weekend:
        print("📅 Weekend Mode Detected (Fri/Sat/Sun) -> Enabling Weekly Summaries")
    else:
        print("📅 Weekday Mode -> Daily Summaries Only")
    
    # We can run these in parallel:
    # 1. Fish Basin (Indices & Sectors)
    # 2. B1 Selection (with data masking)
    # 3. Sector Flow
    # 4. Market Ladder
    # 5. Weekly Preview (if weekend)
    # 6. Earnings Analysis
    # 7. Market Sentiment
    # 8. Dragon Tiger

    # DISABLED by default: Core News
    # - Core News module is available for manual execution but excluded from daily workflow
    # - Other modules can still import its data functions (e.g., fetch_eastmoney_data)

    tasks = [
        (run_fish_basin, args),
        (run_b1_selection, args),  # ENABLED: B1 Selection with data masking (code: 5133**, name: 平安YH)
        (run_sector_flow, args),
        (run_market_ladder, args),
        # (run_core_news, args),  # DISABLED: Core News - Manual execution only (data functions still available)
        (run_weekly_preview, args),
        (run_earnings_analysis, args),
        (run_earnings_prompt, args),
        (run_market_sentiment, args),
        (run_close_report, args),
        (run_dragon_tiger, args)
    ]

    # Switch to sequential execution to avoid akshare/mini_racer multiprocessing crashes
    print("⚠️ Running tasks sequentially to ensure stability...")

    for task_func, task_args in tasks:
        try:
            task_func(task_args)
        except Exception as e:
            print(f"⚠️ Task {task_func.__name__} failed with error: {e}")

    # from concurrent.futures import ProcessPoolExecutor, wait
    #
    # # Note: ProcessPoolExecutor requires functions to be picklable.
    # # Wrapper partials might be needed if we pass complex args, but here we just pass 'args' namespace?
    # # Actually, args (Namespace) is picklable. But we need to import modules inside the worker functions
    # # if we use ProcessPoolExecutor to avoid global state issues, OR just rely on standard multiprocessing.
    # # The existing run_* functions import modules inside them, which is good.
    #
    # tasks = [
    #     (run_fish_basin, args),
    #     (run_b1_selection, args),
    #     (run_sector_flow, args),
    #     (run_market_ladder, args),
    #     (run_core_news, args),
    #     (run_weekly_preview, args),
    #     (run_earnings_analysis, args),
    #     (run_earnings_prompt, args),
    #     (run_market_sentiment, args)
    # ]
    #
    # with ProcessPoolExecutor(max_workers=4) as executor:
    #     futures = [executor.submit(task, arg) for task, arg in tasks]
    #
    #     # Wait for all to complete
    #     wait(futures)
    #
    #     for future in futures:
    #         try:
    #             future.result()
    #         except Exception as e:
    #             print(f"⚠️ Task failed with error: {e}")

    print("\n✅ All parallel tasks completed.")
    
    # Auto-cleanup old results (Keep last 7 days)
    cleanup_old_results()

def cleanup_old_results(keep_days=7):
    """
    Remove results directories older than keep_days.
    Always excludes 'cache' or other non-date directories.
    """
    import shutil
    results_base = "results"
    if not os.path.exists(results_base):
        return

    # Find date directories
    date_dirs = []
    try:
        for d in os.listdir(results_base):
            path = os.path.join(results_base, d)
            # Strict date format check: YYYYMMDD
            if os.path.isdir(path) and d.isdigit() and len(d) == 8:
                date_dirs.append(d)
    except Exception:
        return
    
    # Sort: Newest first
    date_dirs.sort(reverse=True)
    
    if len(date_dirs) > keep_days:
        to_remove = date_dirs[keep_days:]
        print(f"\n🧹 Cleaning up old results (Keeping last {keep_days} days)...")
        for d in to_remove:
            path = os.path.join(results_base, d)
            print(f"   Deleting: {path}")
            try:
                shutil.rmtree(path)
            except Exception as e:
                print(f"   Failed to delete {path}: {e}")


def main():
    parser = argparse.ArgumentParser(description="Stock Daily Report System")
    subparsers = parser.add_subparsers(dest='command', help='Module to run')
    
    # Shared args
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument('--date', type=str, help='Date YYYYMMDD (default: today)')
    parent_parser.add_argument('--force', action='store_true', help='Force regeneration, bypass cache')
    
    # Subcommands
    subparsers.add_parser('all', parents=[parent_parser], help='Run all modules in parallel')
    subparsers.add_parser('fish_basin', parents=[parent_parser], help='Run Fish Basin Analysis')
    subparsers.add_parser('b1', parents=[parent_parser], help='Run B1 Stock Selection')
    subparsers.add_parser('sector_flow', parents=[parent_parser], help='Run Sector Flow')
    subparsers.add_parser('ladder', parents=[parent_parser], help='Run Market Ladder')
    subparsers.add_parser('core_news', parents=[parent_parser], help='Run Core News Monitor')
    subparsers.add_parser('weekly_preview', parents=[parent_parser], help='Run Weekly Events Preview')
    subparsers.add_parser('earnings', parents=[parent_parser], help='Run Earnings Analysis')
    subparsers.add_parser('earnings_prompt', parents=[parent_parser], help='Generate Earnings Performance Prompt')
    subparsers.add_parser('sentiment', parents=[parent_parser], help='Run Market Sentiment Analysis')
    subparsers.add_parser('close_report', parents=[parent_parser], help='Generate Close Report Prompt')
    subparsers.add_parser('dragon', parents=[parent_parser], help='Run Dragon Tiger Analysis')

    args = parser.parse_args()
    
    # Prepare common environment
    sys.path.append(os.getcwd())
    
    # Calculate paths
    output_dir, date_str = get_date_dir(args.date if hasattr(args, 'date') else None)
    os.makedirs(output_dir, exist_ok=True)
    
    # Attach to args for easy access
    args.date_dir = output_dir
    args.date_str = date_str

    # Dispatch
    if args.command == 'fish_basin':
        run_fish_basin(args)
    elif args.command == 'b1':
        run_b1_selection(args)
    elif args.command == 'sector_flow':
        run_sector_flow(args)
    elif args.command == 'ladder':
        run_market_ladder(args)
    elif args.command == 'core_news':
        run_core_news(args)
    elif args.command == 'weekly_preview':
        run_weekly_preview(args)
    elif args.command == 'all':
        run_all(args)
    elif args.command == 'earnings':
        run_earnings_analysis(args)
    elif args.command == 'earnings_prompt':
        run_earnings_prompt(args)
    elif args.command == 'sentiment':
        run_market_sentiment(args)
    elif args.command == 'close_report':
        run_close_report(args)
    elif args.command == 'dragon':
        run_dragon_tiger(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
