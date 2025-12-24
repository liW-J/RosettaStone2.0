'''
Author: JeanneWillis hi@jeannewillis.cn
Date: 2025-12-23 03:10:00
LastEditors: JeanneWillis hi@jeannewillis.cn
LastEditTime: 2025-12-23 18:21:49
FilePath: /ORFS-Research/tools/RosettaStone2.0/odbComm/convert_lefdef2odb.py
Description: convert LEF/DEF to OpenDB (.odb) according to configuration file
'''

from openroad import Design, Tech
import odb
import os
import json
import argparse
import sys
from typing import List, Dict, Any


def load_config(config_file: str) -> Dict[str, Any]:
    """load the configuration file"""
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        print(f"[ERROR] Configuration file not found: {config_file}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"[ERROR] Configuration file format error: {e}")
        sys.exit(1)


def ensure_dir(path: str) -> None:
    """create directory if not exists"""
    if not os.path.exists(path):
        os.makedirs(path)


def read_lefs(db: odb.dbDatabase, lef_files: List[str]) -> None:
    """read LEF files into db"""
    for lef in lef_files:
        if not os.path.exists(lef):
            print(f"[WARNING] LEF file not found: {lef}")
            continue
        print(f"[INFO] Read LEF file: {lef}")
        odb.read_lef(db, lef)


def format_paths(patterns: List[str], context: Dict[str, Any]) -> List[str]:
    """format a list of path patterns with context variables"""
    result = []
    for p in patterns:
        try:
            result.append(p.format(**context))
        except KeyError as e:
            print(f"[ERROR] Missing key {e} in pattern: {p}")
            sys.exit(1)
    return result


def format_path(pattern: str, context: Dict[str, Any]) -> str:
    """format a single path pattern with context variables"""
    try:
        return pattern.format(**context)
    except KeyError as e:
        print(f"[ERROR] Missing key {e} in pattern: {pattern}")
        sys.exit(1)


def convert_lefdef2odb(config_file: str,
                       designs: str = None,
                       platform: str = None,
                       contest: str = None,
                       orfs_dir: str = None,
                       bench_dir: str = None,
                       output_dir: str = None) -> None:
    """
    convert LEF/DEF to OpenDB (.odb) according to the configuration file

    Args:
        config_file: configuration file path
        designs: comma separated design names (override the list in config)
        platform: platform name (override the value in the configuration file)
        contest: contest name (override the value in the configuration file)
        orfs_dir: ORFS directory (override the value in the configuration file)
        bench_dir: benchmark directory (override the value in the configuration file)
        output_dir: output directory for .odb files (override the value in the configuration file)
    """
    config = load_config(config_file)

    # global settings
    platform = platform or config.get('platform', 'ng45')
    contest = contest or config.get('contest', 'ispd2005')
    orfs_dir = orfs_dir or config.get('orfs_dir', '../../../../ORFS-Research')
    bench_dir = bench_dir or config.get('bench_dir', 'bench')
    output_dir = output_dir or config.get('output_dir', 'odbFiles')

    # design list
    if designs is not None:
        design_list = [d.strip() for d in designs.split(',') if d.strip()]
    else:
        design_list = config.get('designs', [])

    if not design_list:
        print(
            "[ERROR] No designs specified. Please set 'designs' in config or use --designs."
        )
        sys.exit(1)

    # path patterns
    lef_patterns = config.get('lef_files', [])
    def_pattern = config.get('def_file', '')
    odb_pattern = config.get(
        'odb_file',
        os.path.join(output_dir, '{platform}_{contest}_{design}.odb'))

    if not lef_patterns or not def_pattern:
        print(
            "[ERROR] 'lef_files' and 'def_file' must be specified in config.")
        sys.exit(1)

    ensure_dir(output_dir)

    for design in design_list:
        context = {
            'platform': platform,
            'contest': contest,
            'design': design,
            'orfs_dir': orfs_dir,
            'bench_dir': bench_dir,
            # for backward compatibility with older variable names
            'bench_path': bench_dir,
            'output_dir': output_dir,
        }

        lef_list = format_paths(lef_patterns, context)
        def_file = format_path(def_pattern, context)
        odb_file = format_path(odb_pattern, context)

        print(f"[INFO] Processing design: {design}")
        print(f"[INFO] Platform: {platform}, Contest: {contest}")
        print(f"[INFO] DEF file: {def_file}")
        print(f"[INFO] ODB output: {odb_file}")

        if not os.path.exists(def_file):
            print(f"[ERROR] DEF file not found: {def_file}")
            sys.exit(1)

        # create db and read LEF/DEF
        db = Design.createDetachedDb()
        read_lefs(db, lef_list)
        odb.read_def(db.getTech(), def_file)

        chip = db.getChip()
        if chip is None:
            sys.exit("ERROR: READ DEF Failed")

        # export odb
        export_result = odb.write_db(db, odb_file)
        if export_result != 1:
            sys.exit("ERROR: Export DB Failed")

        # simple check: re-open and print nets
        new_db = odb.dbDatabase.create()
        new_db = odb.read_db(new_db, odb_file)
        if new_db is None:
            sys.exit("ERROR: Import DB Failed")

        print("[INFO] Nets in imported DB:")
        for net in new_db.getChip().getBlock().getNets():
            print(f"  {net.getName()}")

        print(f"[INFO] Finished design {design}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=
        'convert LEF/DEF to OpenDB (.odb) according to configuration file',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example configuration file (config_ng45.json):
{
  "platform": "ng45",
  "contest": "ispd2005",
  "orfs_dir": "../../../../ORFS-Research",
  "bench_dir": "../bench",
  "output_dir": "odbFiles",
  "designs": ["adaptec1"],
  "lef_files": [
    "{orfs_dir}/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef",
    "{orfs_dir}/flow/platforms/nangate45/lef/NangateOpenCellLibrary.macro.rect.lef",
    "{orfs_dir}/flow/platforms/nangate45/lef/NangateOpenCellLibrary.macro.mod.lef",
    "{bench_dir}/{platform}/{contest}_{design}/{design}_macro.lef"
  ],
  "def_file": "{bench_dir}/{platform}/{contest}_{design}/{design}.def"
}

Example configuration file (config_iccad2015.json):
{
  "platform": "fake",
  "contest": "iccad2015",
  "orfs_dir": "/home/openroad/ORFS-Research",
  "bench_dir": "/home/openroad/ORFS-Research/tools/RosettaStone2.0/bench/fake",
  "output_dir": "odbFiles",
  "designs": ["superblue1"],
  "lef_files": [
    "{bench_dir}/{platform}_{contest}_{design}/{design}.lef"
  ],
  "def_file": "{bench_dir}/{platform}_{contest}_{design}/{design}.def"
}
        """)

    parser.add_argument('config', help='configuration file path (JSON format)')
    parser.add_argument(
        '--designs',
        help=
        'comma separated design names (override the list in the configuration file)'
    )
    parser.add_argument(
        '--platform',
        help='platform name (override the value in the configuration file)')
    parser.add_argument(
        '--contest',
        help='contest name (override the value in the configuration file)')
    parser.add_argument(
        '--orfs_dir',
        help='ORFS directory (override the value in the configuration file)')
    parser.add_argument(
        '--bench_dir',
        help=
        'benchmark directory (override the value in the configuration file)')
    parser.add_argument(
        '--output_dir',
        help=
        'output directory for .odb files (override the value in the configuration file)'
    )

    args = parser.parse_args()

    convert_lefdef2odb(config_file=args.config,
                       designs=args.designs,
                       platform=args.platform,
                       contest=args.contest,
                       orfs_dir=args.orfs_dir,
                       bench_dir=args.bench_dir,
                       output_dir=args.output_dir)


if __name__ == '__main__':
    main()
