from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
import os
from pyomo.environ import *
from . import utilities


dependencies = 'switch_model.busSchedule'


def define_components(mod):
    mod.partial1 = [ 'T' + str(i) for i in range(10*4, 4*13) ]  
    mod.peak = [ 'T' + str(i) for i in range(13*4, 4*17)]  
    mod.partial2  = [ 'T' + str(i) for i in range(17*4, 4*20) ]  

    mod.kWh = {t:     0.03798 - 0.02500           + 0.05690 + 0.00258 + 0.00018 + 0.00535 + 0.01813 for t in times if int(t[1:]) < 4*10 }                          # base
    mod.kWh.update({t:0.03798 - 0.02500 + 0.05464 + 0.05690 + 0.00258 + 0.00018 + 0.00535 + 0.01813 for t in times if int(t[1:]) >= 4*10 and  int(t[1:]) < 4*13} ) # partial peak
    mod.kWh.update({t:0.03798 - 0.02500 + 0.05464 + 0.05690 + 0.00258 + 0.00018 + 0.00535 + 0.01813 for t in times if int(t[1:]) >= 4*13 and  int(t[1:]) < 4*17} ) # high peak 
    mod.kWh.update({t:0.03798 - 0.02500 + 0.05464 + 0.05690 + 0.00258 + 0.00018 + 0.00535 + 0.01813 for t in times if int(t[1:]) >= 4*17 and  int(t[1:]) < 4*20} ) # partial peak
    mod.kWh.update({t:0.03798 - 0.02500           + 0.05690 + 0.00258 + 0.00018 + 0.00535 + 0.01813 for t in times if int(t[1:]) >= 4*20 and  int(t[1:]) < 4*24} ) # base


    mod.kW = {'peak': 4.75, 'partial_peak': 0, 'all': 5.36 + 0.46 + 0.96 + 1.56 }



    # mod.peakSet = Set()
    # mod.partPeakSet = Set()
    # mod.kWh = Param(mod.timePoint)
    # mod.peakSetkW = 
    # mod.partPeakSetkW = 


# def define_dynamic_components(mod):    

# def load_inputs(mod, switch_data, inputs_dir):
#     switch_data.load_aug(
#         filename=os.path.join(inputs_dir, 'financialParams.csv'),
#         auto_select=True,
#         param=(mod.installationFactor, mod.k))

def post_solve(m, outdir):
    import switch_model.reporting as reporting
    print(mod.kW)
    print(mod.kWh)