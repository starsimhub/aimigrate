import starsim as ss
import sciris as sc
import numpy as np

class Zombie(ss.SIR):
    """ Extent the base SIR class to represent Zombies! """
    def __init__(self, pars=None, **kwargs):
        super().__init__()

        self.define_pars(
            dur_inf = ss.constant(v=1000), # Once a zombie, always a zombie! Units are years.

            p_fast = ss.bernoulli(p=0.10), # Probability of being fast
            dur_fast = ss.constant(v=1000), # Duration of fast before becoming slow
            p_symptomatic = ss.bernoulli(p=1.0), # Probability of symptoms
            p_death_on_zombie_infection = ss.bernoulli(p=0.25), # Probability of death at time of infection

            p_death = ss.bernoulli(p=1), # All zombies die instead of recovering
        )
        self.update_pars(pars, **kwargs)

        self.define_states(
            ss.BoolArr('fast', default=self.pars.p_fast), # True if fast
            ss.BoolArr('symptomatic', default=False), # True if symptomatic
            ss.FloatArr('ti_slow'), # Time index of changing from fast to slow
        )

        # Counters for reporting
        self.cum_congenital = 0 # Count cumulative congenital cases
        self.cum_deaths = 0 # Count cumulative deaths

        return

    def step_state(self):
        """ Updates states before transmission on this timestep """
        self.cum_deaths += np.count_nonzero(self.ti_dead <= self.ti)

        super().step_state()

        # Transition from fast to slow
        fast_to_slow_uids = (self.infected & self.fast & (self.ti_slow <= self.ti)).uids
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
        self.ti_slow[fast_uids] = np.round(self.ti + dur_fast / self.t.dt)

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

    def init_results(self):
        """ Initialize results """
        super().init_results()
        self.define_results(
            ss.Result('cum_congenital', dtype=int, scale=True),
            ss.Result('cum_deaths', dtype=int, scale=True),
        )
        return

    def update_results(self):
        """ Update results on each time step """
        super().update_results()
        res = self.results
        ti = self.ti
        res.cum_congenital[ti] = self.cum_congenital
        res.cum_deaths[ti] = self.cum_deaths
        return


class DeathZombies(ss.Deaths):
    """ Extension of Deaths to make some agents who die turn into zombies """
    def __init__(self, pars=None, metadata=None, **kwargs):
        super().__init__(death_rate=kwargs.pop('death_rate', None))
        self.define_pars(
            p_zombie_on_natural_death = ss.bernoulli(p=0.75), # Probability of becoming a zombie on death
        )
        kwargs.pop('death_rate', None)
        self.update_pars(pars, **kwargs)

        return

    def step(self):
        """ Select people to die """

        # Ensure that zombies do not die of natural causes
        not_zombie = self.sim.people.alive.asnew() # Zombies do not die of natural (demographic) causes
        for name, disease in self.sim.diseases.items():
            if 'zombie' in name:
                not_zombie = not_zombie & (~disease.infected)

        death_uids = self.pars.death_rate.filter(not_zombie.uids)
        zombie_uids, death_uids = self.pars.p_zombie_on_natural_death.filter(death_uids, both=True)

        # These uids will die
        if len(death_uids):
            self.sim.people.request_death(death_uids)

        # And these uids will become zombies
        if len(zombie_uids):
            # If we have fast_zombie and slow_zombie types, choose slow_zombie
            zombie = 'zombie' if 'zombie' in self.sim.diseases else 'slow_zombie'
            self.sim.diseases[zombie].set_prognoses(zombie_uids)

        return len(death_uids)


class KillZombies(ss.Intervention):
    """ Intervention that kills symptomatic zombies at a user-specified rate """
    def __init__(self, year, rate, **kwargs):
        self.requires = Zombie
        self.year = sc.promotetoarray(year)
        self.rate = sc.promotetoarray(rate)
        super().__init__(**kwargs)

        # The killing rate is an interpolation of year-rate values
        self.p = ss.bernoulli(p= lambda self, sim, uids: np.interp(self.t.now('year'), self.year, self.rate*self.t.dt))
        return

    def step(self):
        if self.t.now('year') < self.year[0]:
            return

        sim = self.sim
        eligible = ~sim.people.alive.asnew()
        for name, disease in sim.diseases.items():
            if 'zombie' in name:
                eligible = eligible | (disease.infected & disease.symptomatic)
        death_uids = self.p.filter(eligible.uids)

        sim.people.request_death(death_uids)

        return len(death_uids)

class zombie_vaccine(ss.sir_vaccine):
    """
    Create a vaccine product that affects the probability of infection.
    
    The vaccine can be either "leaky", in which everyone who receives the vaccine 
    receives the same amount of protection (specified by the efficacy parameter) 
    each time they are exposed to an infection. The alternative (leaky=False) is
    that the efficacy is the probability that the vaccine "takes", in which case
    that person is 100% protected (and the remaining people are 0% protected).
    
    Args:
        efficacy (float): efficacy of the vaccine (0<=efficacy<=1)
        leaky (bool): see above
    """
    def administer(self, people, uids):        
        if self.pars.leaky:
            people.zombie.rel_sus[uids] *= 1-self.pars.efficacy
        else:
            people.zombie.rel_sus[uids] *= np.random.binomial(1, 1-self.pars.efficacy, len(uids))
        return

    
class ZombieConnector(ss.Connector):
    """ Connect fast and slow zombies so agents don't become double-zombies """

    def __init__(self, pars=None, **kwargs):
        self.requires = Zombie
        super().__init__(label='Zombie Connector')

        self.define_pars(
            rel_sus = 0
        )
        self.update_pars(pars, **kwargs)
        return

    def step(self):
        """ Specify cross protection between fast and slow zombies """

        ppl = self.sim.people
        fast = self.sim.diseases['fast_zombie']
        slow = self.sim.diseases['slow_zombie']

        fast.rel_sus[ppl.alive] = 1
        fast.rel_sus[slow.infected] = self.pars.rel_sus

        slow.rel_sus[ppl.alive] = 1
        slow.rel_sus[fast.infected] = self.pars.rel_sus

        return
