from pyomo.environ import *
import switch_mod.utilities as utilities
from util import get
import os, itertools
from pyomo.environ import *
from switch_mod.financials import capital_recovery_factor as crf
from switch_mod.reporting import write_table

dependencies = (
    'switch_mod.timescales', 'switch_mod.balancing.load_zones',
    'switch_mod.financials', 'switch_mod.energy_sources.properties.properties',
    'switch_mod.generators.core.build', 'switch_mod.generators.core.dispatch'
)

def define_components(m):
    """Make various changes to the model to facilitate reporting and avoid unwanted behavior"""
    
    # define an indexed set of all periods before or including the current one.
    # this is useful for calculations that must index over previous and current periods
    # e.g., amount of capacity of some resource that has been built
    m.CURRENT_AND_PRIOR_PERIODS = Set(m.PERIODS, ordered=True, initialize=lambda m, p:
        # note: this is a fast way to refer to all previous periods, which also respects 
        # the built-in ordering of the set, but you have to be careful because 
        # (a) pyomo sets are indexed from 1, not 0, and
        # (b) python's range() function is not inclusive on the top end.
        [m.PERIODS[i] for i in range(1, m.PERIODS.ord(p)+1)]
    )
    
    # create lists of projects by energy source
    # we sort these to help with display, but that may not actually have any effect
    m.GENERATION_PROJECTS_BY_FUEL = Set(m.FUELS, initialize=lambda m, f:
        sorted([p for p in m.FUEL_BASED_GENS if f in m.FUELS_FOR_GEN[p]])
    )
    m.GENERATION_PROJECTS_BY_NON_FUEL_ENERGY_SOURCE = Set(m.NON_FUEL_ENERGY_SOURCES, initialize=lambda m, s:
        sorted([p for p in m.NON_FUEL_BASED_GENS if m.gen_energy_source[p] == s])
    )


    ##########################
    m.extraction_binary = Param(m.GENERATION_PROJECTS,within=Binary)
    m.transportation1_binary = Param(m.GENERATION_PROJECTS,within=Binary)
    m.transportation2_binary = Param(m.GENERATION_PROJECTS,within=Binary)
    m.extraction_binary_offshore = Param(m.GENERATION_PROJECTS,within=Binary)
    m.transportation1_binary_offshore = Param(m.GENERATION_PROJECTS,within=Binary)
    m.transportation2_binary_offshore = Param(m.GENERATION_PROJECTS,within=Binary)
    m.extraction_binary_shale= Param(m.GENERATION_PROJECTS,within=Binary)
    m.extraction_binary_surface= Param(m.GENERATION_PROJECTS,within=Binary)
    m.OG_share_lb= Param(m.PERIODS, within=NonNegativeReals)
    m.OG_share_ub= Param(m.PERIODS, within=NonNegativeReals)
    m.extraction_offshore_share_ub = Param(m.FUELS_PERIOD,within=NonNegativeReals)
    m.extraction_shale_share_ub = Param(m.FUELS_PERIOD,within=NonNegativeReals)
    m.extraction_surface_ub = Param(m.FUELS_PERIOD,within=NonNegativeReals)
    m.extraction_offshore_share_lb = Param(m.FUELS_PERIOD,within=NonNegativeReals)
    m.extraction_shale_share_lb = Param(m.FUELS_PERIOD,within=NonNegativeReals)
    m.extraction_surface_lb = Param(m.FUELS_PERIOD,within=NonNegativeReals)
    m.extraction_share_lb = Param(m.GENERATION_PROJECTS_EXTRACTION_PERIOD,within=NonNegativeReals)
    m.extraction_share_ub = Param(m.GENERATION_PROJECTS_EXTRACTION_PERIOD,within=NonNegativeReals)

    m.Limited_Fuels_coal_LNG = Set(dimen=1, initialize=["Coal", "LNG"],filter=lambda m, r: r in m.FUELS)
    m.Limited_Fuels_coal = Set(dimen=1, initialize=["Coal"],filter=lambda m, r: r in m.FUELS)
    m.Limited_Fuels_oil = Set(dimen=1, initialize=["Oil"],filter=lambda m, r: r in m.FUELS)
    m.Limited_Fuels_gas =Set(dimen=1, initialize=["LNG"],filter=lambda m, r: r in m.FUELS)
    m.Limited_Fuels_oil_gas = Set(dimen=1, initialize=["Oil", "LNG"],filter=lambda m, r: r in m.FUELS)

    '''

    #################
    # Mines_Coal_Underground + Mines_Coal_Surface >= Total coal consumption 
    # Wells_Conventional_Oil + Wells_Shale_Oil + Wells_Offshore_Oil >= Total Oil consumption
    # Wells_Conventional_Gas + Wells_Shale_Gas + Wells_Offshore_Gas  >= Total Gas consumption 
    # MMBTU on the left side, and MWh on the right side 
    #################
    # f: coal, and LNG 


    def supply_rule_downstream(m,f,p):
        return(sum(m.GenFuelUseRate[g, t, f] * m.tp_weight[t] 
            for g in m.GENERATION_PROJECTS_BY_FUEL[f]  
            for t in m.TPS_FOR_GEN_IN_PERIOD[g,p])/3.412 <= sum(m.GenCapacity[g,p] * m.extraction_binary[g] * m.tp_weight[t] 
            for g in m.GENERATION_PROJECTS_BY_FUEL[f]  
            for t in m.TPS_IN_PERIOD[p])
            )
    m.Build_FuelCapacity_downstream = Constraint(m.Limited_Fuels_coal_LNG, m.PERIODS, rule = supply_rule_downstream)

    # f: oil, since oil maps to LSFO and Diesel, f = Oil as fuel source, x = LSFO, Diesel as a fuel source 
    m.Oil_Fuels_Diesel = Set(dimen=1, initialize=["LSFO", "Diesel"], filter=lambda m, r: r in m.FUELS)
    m.Oil_Fuels_LSFO = Set(dimen=1, initialize=["LSFO", "Diesel"], filter=lambda m, r: r in m.FUELS)
    def supply_rule_downstream_oil(m,f, f1, f2, p):
        return(
            sum(m.GenFuelUseRate[g, t, f1] * m.tp_weight[t]  
                for g in m.GENERATION_PROJECTS_BY_FUEL[f1] 
                for t in m.TPS_FOR_GEN_IN_PERIOD[g,p]
                )/3.412 +
            sum(m.GenFuelUseRate[g, t, f2] * m.tp_weight[t]  
                for g in m.GENERATION_PROJECTS_BY_FUEL[f2] 
                for t in m.TPS_FOR_GEN_IN_PERIOD[g,p]
                )/3.412              
            <= sum(m.GenCapacity[g,p] * m.extraction_binary[g] * m.tp_weight[t] 
                for g in m.GENERATION_PROJECTS_BY_FUEL[f] 
                for t in m.TPS_IN_PERIOD[p]
                )
            )
    m.Build_FuelCapacity_downstream_oil = Constraint(m.Limited_Fuels_oil, m.Oil_Fuels_LSFO, m.Oil_Fuels_Diesel, m.PERIODS, rule = supply_rule_downstream_oil)
    ################### 


    #######################################################################################################################
    # NonHawaii_CoalRail >= Mines_Coal_Underground + Mines_Coal_Surface  
    # NonHawaii_OilPipeline_Onshore >= Wells_Conventional_Oil + Wells_Shale_Oil  
    # NonHawaii_OilPipeline_Offshore >= Wells_Offshore_Oil 
    # NonHawaii_GasService >= Wells_Conventional_Gas +Wells_Shale_Gas  
    #######################################################################################################################


    # f= OIL, GAS, COAL   Transmission Gas pipelines /Oil Onshore/Coal Rail >= Extraction ###########################################################
    def supply_rule_upstream(m, f,p):
        return(
         sum(m.GenCapacity[g,p] * m.transportation2_binary[g] for g in m.GENERATION_PROJECTS_BY_FUEL[f] )>= sum(
            m.GenCapacity[g,p] * m.extraction_binary[g] for g in m.GENERATION_PROJECTS_BY_FUEL[f] ))
    m.Build_FuelCapacity_upstream = Constraint(m.Limited_Fuels, m.PERIODS, rule = supply_rule_upstream) 


    # f= GAS ##############################################################################################################

    # # service and distribution are all dependent upon consumption  
    # def supply_rule_midstream_gas_distribution(f,p): 
    #      sum(m.GenCapacity[g,p] * m.transportation3_binary[g] for g in m.GENERATION_PROJECTS_BY_FUEL[f] >= sum(
    #         m.GenCapacity[g,p] * m.transportation4_binary[g] for g in m.GENERATION_PROJECTS_BY_FUEL[f] )
    # m.Build_FuelCapacity_midstream_gas_distribution = Constraint(m.Limited_Fuels_gas, m.PERIODS, rule = supply_rule_midstream_gas_distribution)

    # # transmission (onshore and offshore) is also dependent upon consumption CRUDE_APPROXIMATION 
    # def supply_rule_midstream_transmission(f,p):
    #      sum(m.GenCapacity[g,p] * m.transportation2_binary[g] for g in m.GENERATION_PROJECTS_BY_FUEL[f] >= sum(
    #         m.GenCapacity[g,p] * m.extraction_binary[g] for g in m.GENERATION_PROJECTS_BY_FUEL[f] )
    # m.Build_FuelCapacitymidstream_transmission = Constraint(m.Limited_Fuels_gas, m.PERIODS, rule = supply_rule_midstream_transmission)
    
    # gathering is dependent upon extraction 
    def supply_rule_midstream_gathering(m, f,p):
        return(
            sum(m.GenCapacity[g,p] * m.transportation1_binary[g] for g in m.GENERATION_PROJECTS_BY_FUEL[f] )>= sum(
            m.GenCapacity[g,p] * m.extraction_binary[g] for g in m.GENERATION_PROJECTS_BY_FUEL[f] ))
    m.Build_FuelCapacity_midstream_gathering = Constraint(m.Limited_Fuels_gas, m.PERIODS, rule = supply_rule_midstream_gathering)


    #######################################################################################################################
    # Offshore vs onshore products has to have different values // The usage of distribution and service pipeline is not 
    # part of the discussion here, unless there is domestic household usage of natural gas 
    # f: GAS, and OIL 
    def supply_rule_offshore_extraction_gathering(m,f,p):
        return(sum(m.GenCapacity[g,p] * m.transportation1_binary_offshore[g] for g in m.GENERATION_PROJECTS_BY_FUEL[f] )>= sum(
            m.GenCapacity[g,p] * m.extraction_binary_offshore[g] for g in m.GENERATION_PROJECTS_BY_FUEL[f] ))
    m.Build_FuelCapacity_offshore_extraction_gathering = Constraint(
        m.Limited_Fuels_oil_gas, m.PERIODS, rule = supply_rule_offshore_extraction_gathering)
    # f: GAS 
    def supply_rule_offshore_extraction_transmission(m,f,p):
        return(sum(m.GenCapacity[g,p] * m.transportation2_binary_offshore[g] for g in m.GENERATION_PROJECTS_BY_FUEL[f] )>= sum(
            m.GenCapacity[g,p] * m.extraction_binary_offshore[g] for g in m.GENERATION_PROJECTS_BY_FUEL[f] ))
    m.Build_FuelCapacity_offshore_extraction_transmission = Constraint(
        m.Limited_Fuels_gas, m.PERIODS, rule = supply_rule_offshore_extraction_transmission)
    

    #######################################################################################################################
    # m.GENERATION_PROJECTS_EXTRACTION = Set(dimen=1, initialize=["Wells_Shale_Oil",
    #     "Wells_Offshore_Oil","Wells_Shale_Gas","Wells_Offshore_Gas",
    #     "Mines_Coal_Surface"],filter=lambda m, r: r in m.GENERATION_PROJECTS)
    # m.GENERATION_PROJECTS_EXTRACTION_PERIOD = Set(dimen=2,initialize=m.GENERATION_PROJECTS_EXTRACTION * m.PERIODS) 
    def offshore_ratio_rule(m, f, p):
        return(m.extraction_offshore_share_ub[f, p]*sum(m.GenCapacity[g,p] * m.extraction_binary[g] 
            for g in m.GENERATION_PROJECTS_BY_FUEL[f])>=sum(m.GenCapacity[g,p] * m.extraction_binary_offshore[g] 
            for g in m.GENERATION_PROJECTS_BY_FUEL[f]))
    def shale_ratio_rule(m, f, p):
        return(m.extraction_shale_share_ub[f, p]*sum(m.GenCapacity[g,p] * m.extraction_binary[g] 
            for g in m.GENERATION_PROJECTS_BY_FUEL[f])>=sum(m.GenCapacity[g,p] * m.extraction_binary_shale[g] 
            for g in m.GENERATION_PROJECTS_BY_FUEL[f]))
    m.offshore_ratio = Constraint(m.Limited_Fuels_oil_gas, m.PERIODS, rule = offshore_ratio_rule)
    m.shale_ratio = Constraint(m.Limited_Fuels_oil_gas, m.PERIODS, rule = shale_ratio_rule)

    def offshore_ratio_lb_rule(m, f, p):
        return(m.extraction_offshore_share_lb[f, p]*sum(m.GenCapacity[g,p] * m.extraction_binary[g] 
            for g in m.GENERATION_PROJECTS_BY_FUEL[f])<=sum(m.GenCapacity[g,p] * m.extraction_binary_offshore[g] 
            for g in m.GENERATION_PROJECTS_BY_FUEL[f]))
    def shale_ratio_lb_rule(m, f, p):
        return(m.extraction_shale_share_lb[f, p]*sum(m.GenCapacity[g,p] * m.extraction_binary[g] 
            for g in m.GENERATION_PROJECTS_BY_FUEL[f])<=sum(m.GenCapacity[g,p] * m.extraction_binary_shale[g] 
            for g in m.GENERATION_PROJECTS_BY_FUEL[f]))
    m.offshore_lb_ratio = Constraint(m.Limited_Fuels_oil_gas, m.PERIODS, rule = offshore_ratio_lb_rule)
    m.shale_lb_ratio = Constraint(m.Limited_Fuels_oil_gas, m.PERIODS, rule = shale_ratio_lb_rule)

    def coal_ratio_ub_rule(m, f, p):
        return(m.extraction_surface_ub[f, p]*sum(m.GenCapacity[g,p] * m.extraction_binary[g] 
            for g in m.GENERATION_PROJECTS_BY_FUEL[f])>=sum(m.GenCapacity[g,p] * m.extraction_binary_surface[g] 
            for g in m.GENERATION_PROJECTS_BY_FUEL[f]))
    m.coal_surface_ub_ratio = Constraint(m.Limited_Fuels_coal, m.PERIODS, rule = coal_ratio_ub_rule)

    # def coal_ratio_lb_rule(m, f, p):
    #     return(m.extraction_surface_lb[f, p]*sum(m.GenCapacity[g,p] * m.extraction_binary[g] 
    #         for g in m.GENERATION_PROJECTS_BY_FUEL[f])<=sum(m.GenCapacity[g,p] * m.extraction_binary_surface[g] 
    #         for g in m.GENERATION_PROJECTS_BY_FUEL[f]))
    # m.coal_surface_lb_ratio = Constraint(m.Limited_Fuels_coal, m.PERIODS, rule = coal_ratio_lb_rule)

    # # # Oil vs Gas
    # def OG_ratio_rule(m, f1, f2, p):
    #     return(m.OG_share_lb[p]*sum(
    #         m.GenCapacity[g,p] * m.extraction_binary[g] for g in m.GENERATION_PROJECTS_BY_FUEL[f2])<= sum(
    #         m.GenCapacity[g,p] * m.extraction_binary[g] for g in m.GENERATION_PROJECTS_BY_FUEL[f1]))
    # m.OG_ratio = Constraint(m.Limited_Fuels_oil, m.Limited_Fuels_gas, m.PERIODS, rule = OG_ratio_rule)

    #######################################################################################################################
    m.GENERATION_PROJECTS_HAWAII_GAS = Set(dimen=1, initialize=["Hawaii_GasTransmission_Onshore","Hawaii_GasDistribution","Hawaii_GasService",
        ],filter=lambda m, r: r in m.GENERATION_PROJECTS)
    m.GENERATION_PROJECTS_LNG = Set(dimen=1, initialize=[
        "Hawaii_LNG"],filter=lambda m, r: r in m.GENERATION_PROJECTS)
    m.GENERATION_PROJECTS_HAWAII_OIL = Set(dimen=1, initialize=["Hawaii_OilPipeline_Onshore"],filter=lambda m, r: r in m.GENERATION_PROJECTS)

    # 97 MW from TrillionBTU per year for RCI Gas usage. Assume flat demand -- same as flat load demand 
    def supply_rule_hawaii_gas(m,f,p, r):
        return(m.GenCapacity[r,p] >= sum( m.GenCapacity[g,p] * m.extraction_binary[g] for g in m.GENERATION_PROJECTS_BY_FUEL[f] )
        + 97 )
    m.Build_FuelCapacity_hawaii_gas = Constraint(
    m.Limited_Fuels_gas, m.PERIODS, m.GENERATION_PROJECTS_HAWAII_GAS, rule = supply_rule_hawaii_gas)

    def supply_rule_hawaii_lng(m,f,p, r):
        return(m.GenCapacity[r,p] + 1163 >= sum( m.GenCapacity[g,p] * m.extraction_binary[g] for g in m.GENERATION_PROJECTS_BY_FUEL[f] )
         )
    m.Build_FuelCapacity_hawaii_lng = Constraint(
    m.Limited_Fuels_gas, m.PERIODS, m.GENERATION_PROJECTS_LNG, rule = supply_rule_hawaii_lng)

    # 980 MW from TrillionBTU per year for RCI Oil usage. 4858 from Gasoline. Assume flat demand -- same as flat load demand 
    def supply_rule_hawaii_oil(m,f,p, r):
        return(m.GenCapacity[r,p] >= sum(m.GenCapacity[g,p] * m.extraction_binary[g] for g in m.GENERATION_PROJECTS_BY_FUEL[f]) + 979
            + 980 + 4858)
    m.Build_FuelCapacity_hawaii_oil = Constraint(
    m.Limited_Fuels_oil, m.PERIODS, m.GENERATION_PROJECTS_HAWAII_OIL, rule = supply_rule_hawaii_oil)
    '''
    #######################################################################################################################
def load_inputs(mod, switch_data, inputs_dir):
    switch_data.load_aug(
        filename=os.path.join(inputs_dir, 'extraction_share_v2.tab'),
        auto_select=True,
        index=mod.FUELS_PERIOD,
        param=(mod.extraction_offshore_share_lb, mod.extraction_shale_share_lb, mod.extraction_surface_lb))
    
