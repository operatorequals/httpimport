import httpimport
from tests import HttpImportTest, PROFILE_PATH


class TestPypi(HttpImportTest):

    def test_pypi(self):
        with httpimport.pypi_repo():
            import distlib
        self.assertTrue(distlib)

    def test_pypi_project_names(self):
        httpimport.set_profile('''[project_names_profile]
project-names:
    sample: sampleproject''')
        with httpimport.pypi_repo(profile='project_names_profile'):
            import sample
        self.assertTrue('sampleproject' in sample.__url__)

    def test_pypi_version(self, version='0.3.5'):
        httpimport.set_profile('''[reqs_profile]
requirements:
    distlib=={version}'''.format(version=version))
        with httpimport.pypi_repo(profile='reqs_profile'):
            import distlib
        self.assertTrue(distlib.__version__ == version)

    def test_pypi_requirements_file(self):
        profile_path = PROFILE_PATH + 'profile_requirements.txt'
        httpimport.set_profile('''[reqs_path_profile]
requirements-file: {profiles_path}

            '''.format(profiles_path=profile_path))

        with httpimport.pypi_repo(profile='reqs_path_profile'):
            import distlib

        # Parse version from file
        with open(profile_path) as f:
            version = f.read().split('==')[1].strip()

        self.assertTrue(distlib.__version__ == version)
