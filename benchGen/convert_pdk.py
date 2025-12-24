'''
Author: JeanneWillis hi@jeannewillis.cn
Date: 2025-12-23 02:51:20
LastEditors: JeanneWillis hi@jeannewillis.cn
LastEditTime: 2025-12-23 18:11:53
FilePath: /ORFS-Research/tools/RosettaStone2.0/benchGen/convert_pdk.py
Description: convert the benchmark to PDK format according to the configuration file
'''
from BookshelfToOdb import BookshelfToOdb
from openroad import Design, Tech
import odb
import os
import json
import argparse
import sys


def PreProcessPDK(db, ffClkPinList):
    """preprocess the database, set the masters with the specified clock pins as sequential"""
    for lib in db.getLibs():
        for master in lib.getMasters():
            for mTerm in master.getMTerms():
                if mTerm.getName() in ffClkPinList:
                    master.setSequential(True)
                    print("[INFO] Set %s as sequential masters" %
                          (master.getName()))
                    break


def load_config(config_file):
    """load the PDK configuration file"""
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


def read_lef_files(db, lef_dir, lef_files):
    """read the LEF file list"""
    for lef_file in lef_files:
        lef_path = os.path.join(lef_dir, lef_file)
        if not os.path.exists(lef_path):
            print(f"[WARNING] LEF file not found: {lef_path}")
            continue
        odb.read_lef(db, lef_path)
        print(f"[INFO] Read LEF file: {lef_path}")


def convert_bench_to_pdk(config_file,
                         design=None,
                         benchmarks=None,
                         platform=None,
                         orfs_dir=None):
    """
    convert the benchmark to PDK format according to the configuration file
    
    Args:
        config_file: configuration file path
        design: design name (if provided, will override the value in the configuration file)
        benchmarks: benchmark collection name (if provided, will override the value in the configuration file)
        platform: platform name (if provided, will override the value in the configuration file)
    """
    # load the configuration
    config = load_config(config_file)

    # get the configuration parameters, allow command line parameters to override the value in the configuration file
    pdk_config = config.get('pdk', {})
    design = design or config.get('design', 'adaptec1')
    benchmarks = benchmarks or config.get('benchmarks', 'ispd2005')
    platform = platform or config.get('platform',
                                      pdk_config.get('name', 'unknown'))
    orfs_dir = orfs_dir or config.get('orfs_dir', '../../flow/')

    # get the PDK specific configuration
    lef_dir = pdk_config.get('lef_dir', '')
    lef_files = pdk_config.get('lef_files', [])
    site_name = pdk_config.get('site_name', '')
    macro_inst_obs_layer = pdk_config.get('macro_inst_obs_layer', [])
    macro_inst_pin_layer = pdk_config.get('macro_inst_pin_layer', [])
    primary_layer = pdk_config.get('primary_layer', '')
    masters_file_name = pdk_config.get('masters_file_name', '')
    ff_clk_pin_list = pdk_config.get('ff_clk_pin_list', [])
    custom_fp_ratio = pdk_config.get('custom_fp_ratio', 1.0)

    # validate the required parameters
    required_params = {
        'lef_dir': lef_dir,
        'lef_files': lef_files,
        'site_name': site_name,
        'macro_inst_obs_layer': macro_inst_obs_layer,
        'macro_inst_pin_layer': macro_inst_pin_layer,
        'primary_layer': primary_layer,
        'masters_file_name': masters_file_name,
        'ff_clk_pin_list': ff_clk_pin_list
    }

    missing_params = [k for k, v in required_params.items() if not v]
    if missing_params:
        print(
            f"[ERROR] Missing required configuration parameters: {', '.join(missing_params)}"
        )
        sys.exit(1)

    # create the database
    db = Design.createDetachedDb()

    # read the LEF files
    lef_path = os.path.join(orfs_dir, 'platforms', lef_dir)
    read_lef_files(db, lef_path, lef_files)

    # preprocess the database
    PreProcessPDK(db, ff_clk_pin_list)

    # create the BookshelfToOdb converter
    aux_name = f"{design}.aux"
    bs = BookshelfToOdb(opendbpy=odb,
                        opendb=db,
                        auxName=aux_name,
                        siteName=site_name,
                        macroInstObsLayer=macro_inst_obs_layer,
                        macroInstPinLayer=macro_inst_pin_layer,
                        primaryLayer=primary_layer,
                        mastersFileName=masters_file_name,
                        ffClkPinList=ff_clk_pin_list,
                        customFPRatio=custom_fp_ratio,
                        benchmarks=benchmarks)

    # write the output files
    macro_lef = f'{design}_macro.lef'
    def_file = f'{design}.def'
    db_file = f'{design}.db'

    bs.WriteMacroLef(macro_lef)
    odb.write_def(db.getChip().getBlock(), def_file)
    odb.write_db(db, db_file)

    # create the output directory and move the files
    output_dir = f'bench/{platform}/{benchmarks}_{design}'
    os.system(f"mkdir -p {output_dir}")
    os.system(f"mv {macro_lef} {output_dir}/")
    os.system(f"mv {def_file} {output_dir}/")
    os.system(f"mv {db_file} {output_dir}/")

    print(f"[INFO] Conversion completed! Output directory: {output_dir}")


def main():
    parser = argparse.ArgumentParser(
        description='convert the benchmark to PDK format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example configuration file format (config.json):
{
  "design": "adaptec1",
  "benchmarks": "ispd2005",
  "platform": "ng45",
  "pdk": {
    "name": "ng45",
    "lef_dir": "nangate45/lef",
    "lef_files": [
      "NangateOpenCellLibrary.tech.lef",
      "NangateOpenCellLibrary.macro.rect.lef"
    ],
    "site_name": "FreePDK45_38x28_10R_NP_162NW_34O",
    "macro_inst_obs_layer": ["metal1", "via1", "metal2", "via2"],
    "macro_inst_pin_layer": ["metal3", "metal4"],
    "primary_layer": "metal3",
    "masters_file_name": "cellList_ng45.txt",
    "ff_clk_pin_list": ["CK"],
    "custom_fp_ratio": 2
  }
}
        """)
    parser.add_argument('config',
                        help='PDK configuration file path (JSON format)')
    parser.add_argument(
        '--design',
        help='design name (override the value in the configuration file)')
    parser.add_argument(
        '--benchmarks',
        help=
        'benchmark collection name (override the value in the configuration file)'
    )
    parser.add_argument(
        '--platform',
        help='platform name (override the value in the configuration file)')
    parser.add_argument(
        '--orfs_dir',
        help='ORFS directory (override the value in the configuration file)')

    args = parser.parse_args()

    convert_bench_to_pdk(args.config,
                         design=args.design,
                         benchmarks=args.benchmarks,
                         platform=args.platform,
                         orfs_dir=args.orfs_dir)


if __name__ == '__main__':
    main()
