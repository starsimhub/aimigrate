"""
Default migrator
"""

import aimigrate as aim

__all__ = ['Migrate', 'migrate']

class Migrate(aim.MigrateDiff):
    __doc__ = aim.MigrateDiff.__doc__
    ...

def migrate(*args, **kwargs):
    """ Helper function for the Migrate class """
    mig = Migrate(*args, **kwargs)
    mig.run()
    return mig