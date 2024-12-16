""" run_results.py
Try utilizing the code snippets here to run the code
"""
import os
import re
import sys
import importlib.util
import numpy as np
from pathlib import Path
import matplotlib.pyplot as pyplot

import starsim_ai as sa
import starsim as ss

os.chdir(os.path.dirname(__file__))

def load_module(module_name, module_path):
    # Create a module spec from the file location
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None:
        raise ImportError(f"Cannot create a module spec for {module_name} at {module_path}")
    # Create a new module based on the spec
    module = importlib.util.module_from_spec(spec)
    # Execute the module in its own namespace
    spec.loader.exec_module(module)
    # Optionally add the module to sys.modules
    sys.modules[module_name] = module
    return module

def test_basic_zombie(module):
    people = ss.People(n_agents=5_000) # People, as before

    # Configure and create an instance of the Zombie class
    zombie_pars = dict(
        init_prev = 0.03,
        beta = {'random': ss.beta(0.05), 'maternal': ss.beta(0.5)},
        p_fast = ss.bernoulli(p=0.1),
        p_death_on_zombie_infection = ss.bernoulli(p=0.25),
        p_symptomatic = ss.bernoulli(p=1.0),
    )
    zombie = module.Zombie(zombie_pars)

    # This function allows the lambda parameter of the poisson distribution used to determine
    # n_contacts to vary based on agent characteristics, a key feature of Starsim.
    def choose_degree(self, sim, uids):
        mean_degree = np.full(fill_value=4, shape=len(uids)) # Default value is 4
        zombie = sim.diseases['zombie'] 
        is_fast = zombie.infected[uids] & zombie.fast[uids]
        mean_degree[is_fast] = 50 # Fast zombies get 50
        return mean_degree

    # We create two network layers, random and maternal
    networks = [
        ss.RandomNet(n_contacts=ss.poisson(lam=choose_degree)),
        ss.MaternalNet()
    ]

    # Configure and create demographic modules
    death_pars = dict(
        death_rate = 15, # per 1,000
        p_zombie_on_natural_death = ss.bernoulli(p=0.2),
    )
    deaths = module.DeathZombies(**death_pars)
    births = ss.Pregnancy(fertility_rate=175) # per 1,000 women 15-49 annually
    demog = [births, deaths]

    # Create an intervention that kills symptomatic zombies
    interventions = module.KillZombies(year=2024, rate=0.1)

    # And finally bring everything together in a sim
    sim_pars = dict(start=2024, stop=2040, dt=0.5, verbose=0)
    sim = ss.Sim(sim_pars, people=people, diseases=zombie, networks=networks, demographics=demog, interventions=interventions)

    # Run the sim and plot results
    sim.run()
    sim.plot('zombie')
    pyplot.savefig('zombie.png')


# directory with results
result_dir = Path(__file__).parent / 'results'

# file with the code
code_file = sa.paths.data / 'zombiesim' / 'zombie.py' # v0.5.2

# trial id
trial_id = 'B' # or trial_id = 'A'
# script name that was migrated/refactored
stem = code_file.stem

# find the files with the results
result_pattern = f'{stem}_*_{trial_id}.py'
results = list(result_dir.glob(result_pattern))
print(f"Found {len(results)} results for {stem} and trial {trial_id}")

# Extract the models from the filenames
model_pattern = re.compile(rf'{stem}_(.*?)_{trial_id}\.py')
models = [model_pattern.search(result.name).group(1) for result in results if model_pattern.search(result.name)]

print(f"Extracted models: {models}")
for model in models:
    module_name = f"{stem}_{model}_{trial_id}"
    print(f"Processing {module_name}")

    try:
        load_module(module_name, result_dir / f"{stem}_{model}_{trial_id}.py")
    except Exception as e:
        print(f"Error loading {module_name}: {e}")

    try:
        test_basic_zombie(sys.modules[module_name])
    except Exception as e:
        print(f"Error running {module_name}: {e}")

    print("continuing...")