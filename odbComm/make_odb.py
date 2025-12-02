# This script generate OpenDB database (.odb) from LEF/DEF format for
# academic contest benchmarks.
from openroad import Design, Tech
import odb
import os

################ Settings #################
# Platform for ODB generation
platform = 'ng45'
# Contest name
contest = 'ISPD2005'
# OpenROAD-flow-scripts path
orfs_path = '../../../../ORFS-Research'
## Benchmark path (for DEF)
bench_path = '../bench'

design_list = ['adaptec1', \
               ]

###########################################

for design in design_list:

    lef_list = [
        '%s/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef' % orfs_path,
        '%s/flow/platforms/nangate45/lef/NangateOpenCellLibrary.macro.rect.lef' %
        orfs_path,
        '%s/flow/platforms/nangate45/lef/NangateOpenCellLibrary.macro.mod.lef' % orfs_path,
        '%s/%s/%s_%s/%s_macro.lef' %
        (bench_path, platform, contest, design, design),
    ]

    def_file = "%s/%s/%s_%s/%s.def" % (bench_path, platform, contest, design,
                                       design)
    # db = odb.dbDatabase.create()
    db = Design.createDetachedDb()

    for lef_file in lef_list:
        odb.read_lef(db, "%s" % lef_file)
    odb.read_def(db.getTech(), "%s" % (def_file))
    chip = db.getChip()
    tech = db.getTech()
    libs = db.getLibs()

    if chip is None:
        exit("ERROR: READ DEF Failed")

    if not os.path.exists('odbFiles'):
        os.makedirs('odbFiles')
    export_result = odb.write_db(
        db, "odbFiles/%s_%s_%s.odb" % (platform, contest, design))
    if export_result != 1:
        exit("Export DB Failed")

    new_db = odb.dbDatabase.create()
    new_db = odb.read_db(new_db,
                         "odbFiles/%s_%s_%s.odb" % (platform, contest, design))

    for net in new_db.getChip().getBlock().getNets():
        print(net.getName())

    if new_db is None:
        exit("Import DB Failed")
    # if odb.db_diff(db, new_db):
    #     exit("Error: Difference found between exported and imported DB")
