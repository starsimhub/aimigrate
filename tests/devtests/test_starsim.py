import os
import git
import pytest
import sciris as sc
import shutil
import aimigrate as aim
from pathlib import Path
os.chdir(Path(__file__).parent)

@pytest.fixture(scope="module")
def starsim_directory():
    this_dir = Path(__file__).parent
    return this_dir / 'starsim'

@pytest.fixture(scope="module")
def setup(starsim_directory):
    print("Setting up test environment...")
    if starsim_directory.exists():
        shutil.rmtree(starsim_directory)
    # https://gist.github.com/plembo/a786ce2851cec61ac3a051fcaf3ccdab
    repo = git.Repo.clone_from('https://github.com/starsimhub/starsim.git',
                            starsim_directory,
                            branch='main')
    yield
    shutil.rmtree(starsim_directory)

def test_MigrateOOB(setup, starsim_directory):
    M = aim.MigrateOOB(
        source_dir='source',
        dest_dir='migrated',
        v_from='v0.5.3',
        v_to='v2.0',
        library='starsim',
        library_alias='ss',
        model='openai:gpt-4o-mini'
    )
    M.run()


def test_MigrateDiff(setup, starsim_directory):
    M = aim.MigrateDiff(
        source_dir='source',
        dest_dir='migrated',
        v_from='9dc28ffa7ad41f4cea8969673c43654eefd0d473',
        v_to='v2.0.0',
        library=starsim_directory,
        library_alias='ss',
        include=['starsim/diseases/sir.py'],
        exclude=[],
        # diff_speed=True,
        diff_speed=False,
        model='openai:gpt-4o-mini'
    )
    M.run()

def test_MigrateRepo(setup, starsim_directory):
    M = aim.MigrateRepo(
        source_dir='source',
        dest_dir='migrated',
        v_from='v0.5.3',
        v_to='v2.0.0',
        # library = project_dir / 'submodules' / 'starsim',
        library=starsim_directory,
        library_alias=starsim_directory,
        include=['starsim/diseases/sir.py'],
        exclude=[],
        model='openai:gpt-4o-mini'
    )
    M.run()

@pytest.mark.parametrize("diff_speed", [True, False])
def test_Migrate(diff_speed, setup, starsim_directory):
    M = aim.Migrate(
        source_dir='source',
        dest_dir='migrated',
        v_from='9dc28ffa7ad41f4cea8969673c43654eefd0d473',
        v_to='v2.0.0',
        library=starsim_directory,
        library_alias='ss',
        include=['starsim/diseases/sir.py'],
        exclude=[],
        diff_speed=diff_speed,
        model='openai:gpt-4o-mini'
    )
    M.run()