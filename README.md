Description
===========

Michel-orgmode is a fork of [michel](https://github.com/chmduquesne/michel)
which serves as a bridge between an [org-mode](http://orgmode.org/) textfile
and a google-tasks task list.  It can push/pull org-mode text files to/from
google tasks, and perform bidirectional synchronization/merging between an
org-mode text file and a google tasks list.

Usage
=====

Your Google task list will be represented as a particular URL that follows
the format:

    gtask://<profile>/<list name>

If you have lists that contain spaces or special characters, just add single
quotes around  the URL to avoid having the command line interpret any of these.

Examples
--------

- Pull your default task-list to an org-mode file:

            michel pull myfile.org gtask://profile/default

- Push an org-mode file to your default task-list:

            michel push myfile.org gtask://profile/default

- Synchronize an org-mode file with your default task-list:

            michel sync myfile.org gtask://profile/default

- Synchronize an org-mode file with your task-list named "Shopping":

            michel sync shopping.org gtask://profile/Shopping

Configuration
-------------

The first time =michel2= is run under a particular profile, you will be shown a
URL.  Click it, and authorize =michel2= to access google-tasks data for whichever
google-account you want to associate with the profile.  You're done!  If no
profile is specified when running michel, a default profile will be used.

The authorization token is stored in
`$XDG_DATA_HOME/michel/<profile-name>_oauth.dat`. No other information is
stored, since the authorization token is the only information needed for michel
to authenticate with google and access your tasks data.


Command line options
--------------------

    usage: michel [-h] (push|pull|sync|print|repair|run) ...

    optional arguments:
      -h, --help           show this help message and exit

    Commands:
      push FILE URL   replace task list in URL with the contents of FILE.
      pull FILE URL   replace FILE with the contents of tasks at URL.
      sync FILE URL   synchronize changes between FILE and tasks at URL.
      print URL       displays the tasks in URL as org format to the console.
      repair FILE     combines the FILE with conficted copies.
      run SCRIPTFILE  runs the commands stored in FILE as JSON.

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

- License: MPL2
- Original author: Christophe-Marie Duquesne ([blog post](http://blog.chmd.fr/releasing-michel-a-flat-text-file-to-google-tasks-uploader.html))
- Author of org-mode version: Mark Edgington ([bitbucket site](https://bitbucket.org/edgimar/michel-orgmode))

Contributing
------------

Patches are welcome, as long as they keep the source simple and short.
