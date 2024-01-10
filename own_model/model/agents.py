# Importing necessary libraries
import random
from mesa import Agent
from shapely.geometry import Point
from shapely import contains_xy

# Import functions from functions.py
from functions import generate_random_location_within_map_domain, get_flood_depth, calculate_basic_flood_damage, floodplain_multipolygon


# Define the Households agent class
class Households(Agent):
    """
    An agent representing a household in the model.
    Each household has a flood depth attribute which is randomly assigned for demonstration purposes.
    In a real scenario, this would be based on actual geographical data or more complex logic.
    """

    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        self.is_adapted = False  # Initial adaptation status set to False

        # New attributes here:
        self.risk_appraisal = 0  # Assumption that households start with 0 appraisal
        self.coping_appraisal = 0
        self.total_individual_appraisal = 0 

        # getting flood map values
        # Get a random location on the map
        loc_x, loc_y = generate_random_location_within_map_domain()
        self.location = Point(loc_x, loc_y)

        # Check whether the location is within floodplain
        self.in_floodplain = False
        if contains_xy(geom=floodplain_multipolygon, x=self.location.x, y=self.location.y):
            self.in_floodplain = True

        # Get the estimated flood depth at those coordinates. 
        # the estimated flood depth is calculated based on the flood map (i.e., past data) so this is not the actual flood depth
        # Flood depth can be negative if the location is at a high elevation
        self.flood_depth_estimated = get_flood_depth(corresponding_map=model.flood_map, location=self.location, band=model.band_flood_img)
        # handle negative values of flood depth
        if self.flood_depth_estimated < 0:
            self.flood_depth_estimated = 0
        
        # calculate the estimated flood damage given the estimated flood depth. Flood damage is a factor between 0 and 1
        self.flood_damage_estimated = calculate_basic_flood_damage(flood_depth=self.flood_depth_estimated)

        # Add an attribute for the actual flood depth. This is set to zero at the beginning of the simulation since there is not flood yet
        # and will update its value when there is a shock (i.e., actual flood). Shock happens at some point during the simulation
        self.flood_depth_actual = 0
        
        #calculate the actual flood damage given the actual flood depth. Flood damage is a factor between 0 and 1
        self.flood_damage_actual = calculate_basic_flood_damage(flood_depth=self.flood_depth_actual) 


    # Function to count friends who can be influencial.
 #   def count_friends(self, radius):
  #      """Count the number of neighbors within a given radius (number of edges away). This is social relation and not spatial"""
   #     friends = self.model.grid.get_neighborhood(self.pos, include_center=False, radius=radius)
    #    return len(friends)

    def step(self):
        # Protection Motivation Theory: we assume once a threshold of awareness/appraisal is surpassed the households adapt
        # Update total_appraisal
        self.total_individual_appraisal = self.risk_appraisal + self.coping_appraisal

        if self.risk_appraisal >= 0.3 and self.coping_appraisal >= 0.3 and random.random()<(0.2+(self.total_individual_appraisal/2)):
            self.is_adapted = True  # Agent adapts to flooding

    
        
# Define the Government agent class
class Government(Agent):
    """
    A government performs according to average appraisal of Households:
    """
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        self.average_appraisal = 0

    
    def step(self):
        # Governments assess the average appraisal of the population by the following:
        total_collective_appraisal = 0
        household_count = 0
        total_flood_damage_estiamted = 0
        average_appraisal = total_collective_appraisal / household_count*2 if household_count else 0
        mean_flood_damage_estimated = total_flood_damage_estiamted / household_count if household_count else 0
        #print(self.average_appraisal, household_count)
        appraisal_multiplier = 0.5

        for agent in self.model.schedule.agents:
            if isinstance(agent, Households):
                total_collective_appraisal += agent.total_individual_appraisal
                household_count += 1
                total_flood_damage_estiamted += agent.flood_damage_estimated



            
            if self.average_appraisal < 0.2:  # TP_RC (top-down: flyers with risk & coping information)
                print("Average appraisal is less than 0.2")
                for agent in self.model.schedule.agents:
                    if isinstance(agent, Households) and agent.total_individual_appraisal <= 0.3: #we assume that flyers only increase appraisal for households with very low awareness
                        print(f"Agent {agent.unique_id} total individual appsraisal: {agent.total_individual_appraisal}")
                        agent.risk_appraisal += appraisal_multiplier * agent.flood_damage_estimated #/ mean_flood_damage_estimated #we assume that risk awareness is dependent on actual threat for each household relative to the average threat
                        agent.coping_appraisal += appraisal_multiplier * agent.flood_damage_estimated #/ mean_flood_damage_estimated
            elif self.average_appraisal < 0.5:  # PC (People centered strategy: social media)
                print("Average appraisal is greater than or equal to 0.2")
                for agent in self.model.schedule.agents:
                    if isinstance(agent, Households) and (agent.risk_appraisal <= 0.5 or agent.coping_appraisal <= 0.5):
                        print(f"Agent {agent.unique_id} risk appraisal: {agent.risk_appraisal}, coping appraisal: {agent.coping_appraisal}")
                        # if agent.risk_appraisal > 0.5: # PC_C (people centered: individual information on coping), since that household is already risk aware
                        #     agent.coping_appraisal += 0.1 * agent.flood_damage_estimated / mean_flood_damage_estimated
                        # elif agent.coping_appraisal > 0.5: # PC_R (people centered: individual information on risk), since that household is already coping aware
                        #     agent.risk_appraisal += 0.1 * agent.flood_damage_estimated / mean_flood_damage_estimated
                        # elif agent.total_individual_appraisal <= 0.1: #PC_RC
                        #     agent.risk_appraisal += 0.05 * agent.flood_damage_estimated / mean_flood_damage_estimated
                        #     agent.coping_appraisal += 0.05 * agent.flood_damage_estimated / mean_flood_damage_estimated
                        if agent.risk_appraisal > agent.coping_appraisal: # PC_C (people centered: individual information on coping), since that household is already risk aware
                            agent.coping_appraisal += appraisal_multiplier * agent.flood_damage_estimated #/ mean_flood_damage_estimated
                        elif agent.coping_appraisal > agent.risk_appraisal: # PC_R
                            agent.risk_appraisal += appraisal_multiplier * agent.flood_damage_estimated #/ mean_flood_damage_estimated
            else:
                print('Campainging has stopped.')