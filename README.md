![image](https://img.shields.io/badge/Python-FFD43B?style=for-the-badge&logo=python&logoColor=blue)
[![image](https://img.shields.io/badge/Gmail-D14836?style=for-the-badge&logo=gmail&logoColor=white)](mailto:thomas.dambrin@gmail.com?subject=[GitHub]%20Snowflake%20Git%20Versioning)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

# Snowflake Git

# Worksheet Versioning

Inspired by a snowflake developers maintained [repository](https://github.com/Snowflake-Labs/sfsnowsightextensions).

### Git integration 

The extension is designed to **apply git versioning on worksheets while developing on Snowsight, fully taking advantage of its functionalities**.\
The following workflow is advised :
1. [Start session] Upload worksheet from local branch to a user Snowsight workspace
2. Test, update and validate on Snowsight 
3. [End session] Update local branch with modified Snowsight worksheets

## Installation

Entry points are accessible through a CLI once the package is installed. 
To install it, please follow the following steps :

```bash
# [Optional: Python virtual environement]
$ pyenv virtualenv 3.10.4 sf
$ pyenv activate sf

# [Mandatory: Pip install]
$ pip install -U pip
$ pip install sf_git@git+https://github.com/tdambrin/sf_git@v1.0

# [Check your installation]
$ sfgit --help
```

Commands have been created to **import/export (respectively fetch/push) snowsight worksheets to/from local**.

## Git configuration

> **Warning**
> A git repository is necessary to manage worksheets. You can either use an existing one
> or create a new one.

To apply versioning to your worksheets, you need to **configure Git information**
through the config command. 

First, set git repository to be used:

```bash
# if you want to use an existing git repository
$ sfgit config --git-repo <path_to_git_repo>

# if you want to create a new one 
$ sfgit init <path_to_git_repo>
```

Then, set a location to save your worksheets within this git repository:
```bash
$ sfgit config --save-directory <path_to_worksheets_persistency_directory>
```

## Authentication
Currently, two authentication modes are supported i.e. credentials (PWD) and single sign-on (SSO).

Commands requiring Snowsight authentication all have options to provide at command time. 
If you don't want to manually input them everytime, you can set them at Python/Virtual environement level with :


```bash
$ sfgit config --account <your_snowsight_account_id>
$ sfgit config --username <your_snowsight_login_name>
$ sfgit config --password <your_snowsight_password>  # unnecessary for SSO authentication mode
```

## Usage

**Import user worksheet locally** :
```bash
$ sfgit fetch -username tdambrin -account-id my_account.west-europe.azure --auth-mode SSO
```

**Commit you worksheets** (or through git commands for more flexibility) :
```bash
$ sfgit commit --branch master -m "Initial worksheet commit" -username tdambrin
```

**Export user worksheets to Snowsight** :
```bash
$ sfgit push --auth-mode SSO --branch master
```

## Policies
Feedbacks and contributions are greatly appreciated. This package was made to ease every day life for Snowflake 
developers and promote version control as much as possible.

For questions, please feel free to reach out [by email](mailto:thomas.dambrin@gmail.com?subject=[GitHub]%20Snowflake%20Git%20Versioning).
