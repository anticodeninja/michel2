Description
===========

Michel-orgmode is a fork of [michel](https://github.com/chmduquesne/michel)
which serves as a bridge between an [org-mode](http://orgmode.org/) textfile
and a google-tasks task list.  It can push/pull org-mode text files to/from
google tasks, and perform bidirectional synchronization/merging between an
org-mode text file and a google tasks list.

Usage
=====

Examples
--------

- Pull your default task-list to an org-mode file:

            michel --pull --orgfile myfile.org

- Pull the default task-list from a different google account to an org-mode file:

            michel --pull --orgfile myfile_other.org --profile other_acct

- Push an org-mode file to your default task-list:

            michel --push --orgfile myfile.org

- Synchronize an org-mode file with your default task-list:

            michel --sync --orgfile myfile.org

- Synchronize an org-mode file with your task-list named "Shopping":

            michel --sync --orgfile shopping.org --listname Shopping

Configuration
-------------

The first time michel is run under a particular profile, you will be shown a
URL.  Click it, and authorize michel to access google-tasks data for whichever
google-account you want to associate with the profile.  You're done!  If no
profile is specified when running michel, a default profile will be used.

The authorization token is stored in
`$XDG_DATA_HOME/michel/<profile-name>_oauth.dat`. No other information is
stored, since the authorization token is the only information needed for michel
to authenticate with google and access your tasks data.


Command line options
--------------------

    usage: michel [-h] (--push | --pull | --sync) [--orgfile FILE]
                  [--profile PROFILE] [--listname LISTNAME]

    optional arguments:
      -h, --help           show this help message and exit
      --push               replace LISTNAME with the contents of FILE.
      --pull               replace FILE with the contents of LISTNAME.
      --sync               synchronize changes between FILE and LISTNAME.
      --orgfile FILE       An org-mode file to push from / pull to
      --profile PROFILE    A user-defined profile name to distinguish between
                           different google accounts
      --listname LISTNAME  A GTasks list to pull from / push to (default list if
                           empty)

Org-mode Syntax
---------------

This script currently only supports a subset of the org-mode format.  The
following elements are mapped mapped between a google-tasks list and an
org-mode file:

* Task Indentation <--> Number of asterisks preceding a headline
* Task Notes <--> Headline's body text
* Checked-off / crossed-out <--> Headline is marked as DONE


Installation Dependencies
=========================

The `michel.py` script runs under Linux (not tested on other platforms yet).
To run the script, you need to install the following dependencies:

* [google-api-python-client](http://code.google.com/p/google-api-python-client/)
* [python-gflags](http://code.google.com/p/python-gflags/) (usually available in
  package repositories of major linux distributions)


About
=====

Author/License
--------------

- License: Public Domain
- Original author: Christophe-Marie Duquesne ([blog post](http://blog.chmd.fr/releasing-michel-a-flat-text-file-to-google-tasks-uploader.html))
- Author of org-mode version: Mark Edgington ([bitbucket site](https://bitbucket.org/edgimar/michel-orgmode))

Contributing
------------

Patches are welcome, as long as they keep the source simple and short.
