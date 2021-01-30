'''
Define an interface called Constraints. 
All constraint objects are going to extend that interace 

- Your model class is going to take a property that has a type of Constraint 
- Your model class has a method called "Add Constraints 

model.winterConstraints
model.summerConstraints 

'''

# class Model extends abstract model 

class Model: 
    def __init__(self, inputParam1, inputParam2):
        self.variables = variableList
        # every variable you create can extend the list of variables 
        # variable list can be a singleton 


        self.constraints = ConstraintList() # map of names and constraints. Implement the hashmap. 
        '''
        switch_mod
        switch_mod.timescales
        switch_mod.financials
        switch_mod.balancing.load_zones
        switch_mod.energy_sources.properties
        switch_mod.generators.core.build
        #switch_mod.generators.core.build_original
        switch_mod.generators.core.dispatch
        switch_mod.reporting
        ### end core modules ###
        #### necessary but not core modules #### 
        switch_mod.energy_sources.fuel_costs.markets
        switch_mod.generators.core.proj_discrete_build
        switch_mod.generators.core.commit.operate
        switch_mod.generators.core.commit.fuel_use
        ####### Suggested Modules to Run ######
        #switch_mod.hawaii.switch_patch  
        #switch_mod.hawaii.switch_patch_original  
        switch_mod.hawaii.kalaeloa 
        switch_mod.hawaii.demand_response_simple
        switch_mod.hawaii.smooth_dispatch
        ####### Add Carbon Cap ######
        #switch_mod.policies.carbon_policies
        switch_mod.hawaii.save_results
        '''
    
    def addConstraints(self, sthConstraint):
        self.constraints.add(
            a x  >= c 
        )
    
    # singleton. 
    # getter and setters 
    
    # create indexed constraints, exist on the constraint class 



instance = Something(electricityPricingOver10years, inflationRate)
