import httpimport
from tests import HttpImportTest, PROFILE_PATH


class TestLoadPypi(HttpImportTest):

    def test_load_pypi(self):
        mod = httpimport.load(
            'distlib', importer_class=httpimport.PyPIImporter)
        self.assertTrue(mod)

    def test_pypi_project_names(self):
        httpimport.set_profile('''[project_names_profile]
project-names:
    sample: sampleproject''')
        mod = httpimport.load(
            'sample',
            importer_class=httpimport.PyPIImporter,
            profile='project_names_profile')
        self.assertTrue('sampleproject' in mod.__url__)

    def test_pypi_version(self, version='0.3.5'):
        httpimport.set_profile('''[reqs_profile]
requirements:
    distlib=={version}'''.format(version=version))

        mod = httpimport.load(
            'distlib',
            importer_class=httpimport.PyPIImporter,
            profile='reqs_profile')
        self.assertTrue(mod.__version__ == version)

    def test_pypi_requirements_file(self):
        profile_path = PROFILE_PATH + 'profile_requirements.txt'
        httpimport.set_profile('''[reqs_path_profile]
requirements-file: {profiles_path}

            '''.format(profiles_path=profile_path))

        mod = httpimport.load(
            'distlib',
            importer_class=httpimport.PyPIImporter,
            profile='reqs_path_profile')

        # Parse version from file
        with open(profile_path) as f:
            version = f.read().split('==')[1].strip()

        self.assertTrue(mod.__version__ == version)
