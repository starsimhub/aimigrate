import starsim as ss
import numpy as np

class Zombie(ss.SIR):
    """ Extent the base SIR class to represent Zombies! """
    def __init__(self, pars=None, **kwargs):
        super().__init__()

        self.default_pars(
            inherit = True, # Inherit from SIR defaults
            dur_inf = ss.constant(v=1000), # Once a zombie, always a zombie! Units are years.

            p_fast = ss.bernoulli(p=0.10), # Probability of being fast
            dur_fast = ss.constant(v=1000), # Duration of fast before becoming slow
            p_symptomatic = ss.bernoulli(p=1.0), # Probability of symptoms
            p_death_on_zombie_infection = ss.bernoulli(p=0.25), # Probability of death at time of infection

            p_death = ss.bernoulli(p=1), # All zombies die instead of recovering
        )
        self.update_pars(pars, **kwargs)

        self.add_states(
            ss.BoolArr('fast', default=self.pars.p_fast), # True if fast
            ss.BoolArr('symptomatic', default=False), # True if symptomatic
            ss.FloatArr('ti_slow'), # Time index of changing from fast to slow
        )

        # Counters for reporting
        self.cum_congenital = 0 # Count cumulative congenital cases
        self.cum_deaths = 0 # Count cumulative deaths

        return

    def update_pre(self):
        """ Updates states before transmission on this timestep """
        self.cum_deaths += np.count_nonzero(self.ti_dead <= self.sim.ti)

        super().update_pre()

        # Transition from fast to slow
        fast_to_slow_uids = (self.infected & self.fast & (self.ti_slow <= self.sim.ti)).uids
        self.fast[fast_to_slow_uids] = False

        return

    def set_prognoses(self, uids, source_uids=None):
        """ Set prognoses of new zombies """
        super().set_prognoses(uids, source_uids)

        # Choose which new zombies will be symptomatic
        self.symptomatic[uids] = self.pars.p_symptomatic.rvs(uids)

        # Set timer for fast to slow transition
        fast_uids = uids[self.fast[uids]]
        dur_fast = self.pars.dur_fast.rvs(fast_uids)
        self.ti_slow[fast_uids] = np.round(self.sim.ti + dur_fast / self.sim.dt)

        # Handle possible immediate death on zombie infection
        dead_uids = self.pars.p_death_on_zombie_infection.filter(uids)
        self.cum_deaths += len(dead_uids)
        self.sim.people.request_death(dead_uids)
        return

    def set_congenital(self, target_uids, source_uids=None):
        """ Congenital zombies """
        self.cum_congenital += len(target_uids)
        self.set_prognoses(target_uids, source_uids)
        return