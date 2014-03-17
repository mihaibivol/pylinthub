PyLintHub
=========

Automatic code review tool that integrates pylint with a github pull
request.

How to run it
=============

* Manually get the code from the pull request you want to lint
* Add your credentials into $PATH_TO_PYLINTHUB/credentials.py
  * Credentials is a dictionary with the arguments that [PyGitHub](https://github.com/jacquev6/PyGithub/blob/master/github/MainClass.py#L57) receives. The user should have acces to the repo.
  * example:
  ```python
  credentials={'login_or_token': 'mihaibivol', 'password': 'mypassword'}
  ```
  
  * ```python main.py -r 'mihaibivol/pylinthub' -n 1```

Usage
-----
```
usage: main.py [-h] -r REPO -n PULL_NUMBER [-rc RCFILE]
               [-a ASSIGNEES [ASSIGNEES ...]]

optional arguments:
  -h, --help            show this help message and exit
  -r REPO, --repo REPO  Repository of the Pull Request (default: None)
  -n PULL_NUMBER, --pull_number PULL_NUMBER
                        Pull Request number (default: None)
  -rc RCFILE, --rcfile RCFILE
                        Pylint rc file (default: None)
  -a ASSIGNEES [ASSIGNEES ...], --assignees ASSIGNEES [ASSIGNEES ...]
                        Pull Request assignees for which the script is ran. If
                        not set the script will run for any assignee (default:
                        None)
```

Jenkins example
===============

* Create build project using the Pull Request Builder configuration that suits your needs. Help on that [here](https://wiki.jenkins-ci.org/display/JENKINS/GitHub+pull+request+builder+plugin)
* Add this shell script in a build step
```
#!/bin/bash

if [ ! -d venv ] ; then
   virtualenv --python=python2.7 venv
fi
source venv/bin/activate
export PYTHONPATH="$PWD:$PYTHONPATH"

# Get pylinthub sources
git clone https://github.com/mihaibivol/pylinthub.git __pylinthub
pip install -r __pylinthub/requirements.txt

# This can be any valid credential login
echo "credentials = {'login_or_token': 'username', 'password': 'password'}" > __pylinthub/credentials.py

python __pylinthub/main.py -r mihaibivol/pylinthub -n $ghprbPullId

# In order for git pull to work if credentials is modified
rm __pylinthub.credentials.py
```

* For manually running a build you must
  * Mark ```This build is parameterized```
  * Add a String Parameter called ```sha1```
  * Add a String Parameter called ```ghprbPullId```
  * Click on ```Build with Parameters```. And add to ```sha1``` ```origin/pr/$PR_TO_LINT/merge``` and to ```ghprbPullId``` ```$PR_TO_LINT```
  
  
  
