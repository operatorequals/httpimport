from httpimport import github_repo, bitbucket_repo

with github_repo('operatorequals','covertutils'):
    import covertutils

print covertutils


with bitbucket_repo('atlassian', 'python-bitbucket', module = 'pybitbucket'):
    import pybitbucket

print pybitbucket
