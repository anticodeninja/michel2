Description
===========

**Michel2** is fork
of [michel-orgmode](https://bitbucket.org/edgimar/michel-orgmode) which serves
as a bridge between an [org-mode](http://orgmode.org/) textfile and cloud based
task trackers such as Google Task. It can push/pull/bidirectionally sync and
merge org-mode text files to/from/with a cloud based task tracker.

p.s. Really, only Google Tasks are supported now.


Usage
=====

Supported Integrations
----------------------

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


Installation
------------

The `michel` script runs under Linux, Windows and should work under MacOS,
although it hasn't been tested yet. To install script, you need to clone
repository and install via `pip`:

    git clone git@github.com:anticodeninja/michel2.git
    cd michel2
    pip install -e .


Configuration
-------------

The first time **Michel2** is run under a particular profile, you will be shown a
URL.  Click it, and authorize **Michel2** to access google-tasks data for whichever
google-account you want to associate with the profile.  You're done!  If no
profile is specified when running michel, a default profile will be used.

The authorization token is stored in
`$XDG_DATA_HOME/.michel/<profile-name>_oauth.dat`. No other information is
stored, since the authorization token is the only information needed for michel
to authenticate with google and access your tasks data.


Command Line Options
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


Script File Syntax
------------------

If you often work with the same files you can prefer using a script file like
this (really it is JSON):

    [
        { "action": "repair", "org_file": "~/Dropbox/org/work.org" },
        { "action": "repair", "org_file": "~/Dropbox/org/personal.org" },
        { "action": "sync", "org_file": "~/Dropbox/org/work.org", "url": "gtask://__default/work", "only_todo": true },
        { "action": "sync", "org_file": "~/Dropbox/org/personal.org", "url": "gtask://__default/personal", "only_todo": true }
    ]

And run it with `michel run script.json`.  If you constantly use the same files
you can save this file as `$XDG_DATA_HOME/.michel/profile` and run it very
quickly with the shortest variant `michel`.


Emacs Integrations
------------------

As a continuation of a previous step, you can integrate **Michel2** in Emacs by the
following elisp snippet (do not forget to correct the encoding if you try to use it
under Windows):

    (defun michel()
        (interactive)
        (let ((michel-buf (generate-new-buffer "Emacs Michel")))
            (switch-to-buffer michel-buf)
            (insert "=== Emacs Michel ===\n")
            (let* ((michel-proc (start-process "michel" michel-buf "michel")))
                (if (string-equal system-type "windows-nt") ;; HACK, use latin-1 or your
                    (set-buffer-process-coding-system 'cp1251 'cp1251)) ;; encoding here
                (comint-mode)
                (set-process-sentinel michel-proc
                    `(lambda (p e) (if (eq (current-buffer) ,michel-buf)
                        (progn
                        (insert "====================\n")
                        (sit-for 3)
                        (kill-buffer))))))))

It is not the best way to integrate **Michel2** to Emacs, but it works the same
way under Linux and Windows.


Org-mode Syntax
---------------

Currently, this script supports only a subset of the org-mode format. The
following elements are mapped between a google-tasks list and an org-mode file:

* Task Indentation <--> Number of asterisks preceding a headline
* Task Notes <--> Headline's body text
* Checked-off / crossed-out <--> Headline is marked as DONE


About
=====


Author/License
--------------

- License: MPL2
- Original author: Christophe-Marie Duquesne ([blog post](http://blog.chmd.fr/releasing-michel-a-flat-text-file-to-google-tasks-uploader.html))
- Author of org-mode version: Mark Edgington ([bitbucket site](https://bitbucket.org/edgimar/michel-orgmode))
- Author of Michel2 version: @anticodeninja ([github site](https://github.com/anticodeninja/michel2))


Contributing
------------

Patches/issues/other feedback are welcome.
