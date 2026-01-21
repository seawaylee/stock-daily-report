#!/usr/bin/env python3
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
from datetime import datetime

# Enable Simple Network Logging (No Proxies/Retries)
try:
    from common import network
    network.apply_patch()
except ImportError:
    pass

# Convert string "YYYYMMDD" to path "results/YYYYMMDD" 
def get_date_dir(date_str=None):
    if not date_str:
        date_str = datetime.now().strftime('%Y%m%d')
    return os.path.join("results", date_str), date_str

def run_fish_basin(args):
    print("\n=== [Module 1] Fish Basin Trend Analysis ===")
    from modules.fish_basin import fish_basin, fish_basin_sectors
    
    # 1. Indices
    print("--- Part A: Indices ---")
    fish_basin.run(args.date_dir)
    
    # 2. Sectors
    print("\n--- Part B: Sectors ---")
    fish_basin_sectors.run(args.date_dir)
    
    # 3. Generate Prompts
    print("\n--- Part C: Generate Prompts ---")
    from modules.fish_basin import generate_trend_prompts
    generate_trend_prompts.generate_all_prompts(args.date_str)
    
    return True


def run_b1_selection(args):
    print("\n=== [Module 2] B1 Stock Selection & AI Analysis ===")
    from modules.stock_selection import b1_selection
    return b1_selection.run(args.date_dir)

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

def run_all(args):
    print("🌟 Starting Full Daily Workflow (Parallel Execution) 🌟")
    print(f"Target Directory: {args.date_dir}")
    
    # We can run these in parallel:
    # 1. Fish Basin (Indices & Sectors)
    # 2. B1 Selection (might be slow)
    # 3. Sector Flow
    # 4. Market Ladder
    
    from concurrent.futures import ProcessPoolExecutor, wait
    
    # Note: ProcessPoolExecutor requires functions to be picklable. 
    # Wrapper partials might be needed if we pass complex args, but here we just pass 'args' namespace?
    # Actually, args (Namespace) is picklable. But we need to import modules inside the worker functions 
    # if we use ProcessPoolExecutor to avoid global state issues, OR just rely on standard multiprocessing.
    # The existing run_* functions import modules inside them, which is good.
    
    tasks = [
        (run_fish_basin, args),
        (run_b1_selection, args),
        (run_sector_flow, args),
        (run_market_ladder, args)
    ]
    
    with ProcessPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(task, arg) for task, arg in tasks]
        
        # Wait for all to complete
        wait(futures)
        
        for future in futures:
            try:
                future.result()
            except Exception as e:
                print(f"⚠️ Task failed with error: {e}")

    print("\n✅ All parallel tasks completed.")

def main():
    parser = argparse.ArgumentParser(description="Stock Daily Report System")
    subparsers = parser.add_subparsers(dest='command', help='Module to run')
    
    # Shared args
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument('--date', type=str, help='Date YYYYMMDD (default: today)')
    
    # Subcommands
    subparsers.add_parser('all', parents=[parent_parser], help='Run all modules in parallel')
    subparsers.add_parser('fish_basin', parents=[parent_parser], help='Run Fish Basin Analysis')
    subparsers.add_parser('b1', parents=[parent_parser], help='Run B1 Stock Selection')
    subparsers.add_parser('sector_flow', parents=[parent_parser], help='Run Sector Flow')
    subparsers.add_parser('ladder', parents=[parent_parser], help='Run Market Ladder')

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
    elif args.command == 'all':
        run_all(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
