.. _sec_develop:

===========
Development
===========

This section gives on overview about everything you need to know if you
wish to contribute to BMicro.


Development workflow
====================
The main branch for developing BMicro is ``main``.
If you want to make small changes like one-liners,
documentation, or default values in the configuration,
you may work on the ``main`` branch. If you want to change
more, please (fork BMicro and) create a separate branch,
e.g. ``my_new_feature_dev``, and create a pull-request
once you are done making your changes.
Please make sure to edit the
`Changelog <https://github.com/BrillouinMicroscopy/BMicro/blob/main/CHANGELOG>`__.

**Very important:** Please try to always pull with rebase

::

    git pull --rebase

instead of

::

    git pull

to prevent confusions in the commit history.


Documentation
=============
It is always helpful to have code examples and thorough descriptions
in a documentation. We use sphinx-autodoc for the
:ref:`code reference <sec_coderef>`, which means that the docstrings
of your functions and classes are automatically rendered. Please
make sure that this is working properly - go to the ``docs`` directory
and execute:

::

    pip install -r requirements.txt
    sphinx-build . _build

This will create a a file ``_build/index.html`` which you can open in
your favorite browser.



Tests
=====
We try to adhere to test-driven development. Please always write test
functions for your code. You can run all tests via

::

    python setup.py test


Making a new release
====================
The release process of BMicro is completely automated. All you need to know
is that you have to create an incremental tag:

::

    git tag -a "0.1.3"
    # or (if you have set up PGP)
    git tag -s "0.1.3"
    # and finally
    git push --tags

For more information on how automatic deployment to PyPI works, please
read on.


Continuous integration
======================
The following things are automated:

- pytest and flake8 on Linux, macOS, and Windows via GitHub Actions:
  https://github.com/BrillouinMicroscopy/BMicro/actions?query=workflow%3AChecks

  You should always check that all checks pass before you merge a pull request
  (A green state on your local machine does not mean a global green state).
- automatic deployment to PyPI on tag creation via GitHub Actions:
  https://github.com/BrillouinMicroscopy/BMicro/actions?query=workflow%3A%22Release+to+PyPI%22

  Paul Müller created the `BMicro <https://pypi.org/project/bmicro/>`_ package on
  PyPI and gave the user ``ci_bm`` permission to upload new releases. The
  password for this user is an
  `organization secret <https://github.com/organizations/BrillouinMicroscopy/settings/secrets/actions>`_.
- documentation is built automatically (for all tags and for the latest commit
  to the main branch) on readthedocs: https://readthedocs.org/projects/BMicro/builds/
- coverage statistics are done with codecov: https://codecov.io/gh/BrillouinMicroscopy/BMicro

  Please try stay above 90% coverage.

Badges for all of these CI tasks are in the main ``README.rst`` file.
