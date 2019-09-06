from httpimport import github_repo, bitbucket_repo, gitlab_repo

# import logging
# logging.getLogger('httpimport').setLevel(logging.DEBUG)




print ("[+] Importing from GitLab")
# Needs 'requests' and 'six' to work
with gitlab_repo('harinathreddyk', 'python-gitlab', module='gitlab'):
	from gitlab import const as gitlab
	# import gitlab 

print (gitlab)

print ("[+] Importing from GitHub")
with github_repo('operatorequals','covertutils'):
    import covertutils

print (covertutils)


print ("[+] Importing from BitBucket")
with bitbucket_repo('atlassian', 'python-bitbucket', module = 'pybitbucket'):
    import pybitbucket

print (pybitbucket)

