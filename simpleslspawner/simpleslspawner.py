import os
import os.path
import sys
from traitlets import Unicode

from jupyterhub.spawner import LocalProcessSpawner


class SimpleLocalProcessSymlinkSpawner(LocalProcessSpawner):
    """
    A version of LocalProcessSpawner that doesn't require users to exist on
    the system beforehand.

    Note: DO NOT USE THIS FOR PRODUCTION USE CASES! It is very insecure, and
    provides absolutely no isolation between different users!
    """

    home_path_template = Unicode(
        '/tmp/{userid}',
        config=True,
        help='Template to expand to set the user home. {userid} and {username} are expanded'
    )

    symlink_dir = Unicode(
        '',
        config=True,
        help='String with a path to a folder, that will be symlinked in each home_path_template; if it is an empty or invalid string, no symlinking is performed'
    )

    @property
    def home_path(self):
        return self.home_path_template.format(
            userid=self.user.id,
            username=self.user.name
        )

    def make_preexec_fn(self, name):
        home = self.home_path
        def preexec():
            try:
                os.makedirs(home, 0o755, exist_ok=True)
                os.chdir(home)
                symlink_dir_bn = os.path.basename(self.symlink_dir)
                if os.path.exists(self.symlink_dir):
                  # check that we haven't added symlink previously - via basename, now that we're chdir'd here:
                  if not(os.path.exists(symlink_dir_bn)):
                    os.symlink(self.symlink_dir, "./{}".format(symlink_dir_bn))
                  else:
                    print("{} found, not creating symlink".format(symlink_dir_bn))
                # repeat install of nbextensions - should end up in this folder/.local ?
                # it sort of doesn't? But still can see the configurator - just with limited installs?
                # actually, JupyterHub may dump output from these commands to /var/log/syslog
                #os.system("jupyter contrib nbextension install --user") # seems OK, but unneeded?
                os.system("jupyter nbextensions_configurator enable --user")
                # it turns out, we need to use absolute path to install these extensions in /tmp/dir/local;
                # then we can enable them as usual
                # so, first get the full path of the interpreter; then derive site packages path
                NBPATH = os.path.abspath(os.path.join(sys.executable, os.pardir, os.pardir))
                #CONBE_PATH = os.path.abspath(os.path.join(NBPATH, "lib/python3.8/site-packages/jupyter_contrib_nbextensions/nbextensions"))
                CONBE_PATH = None
                for root, subdirs, files in os.walk(NBPATH):
                  for d in subdirs:
                    if d == "jupyter_contrib_nbextensions":
                      CONBE_PATH = os.path.join(root, d, "nbextensions")
                #os.system("jupyter nbextension enable hide_input/main --user")
                #os.system("jupyter nbextension enable codefolding/main --user")
                #os.system("jupyter nbextension enable init_cell/main --user")
                #os.system("jupyter nbextension enable keyboard_shortcut_editor/main --user")
                # NOTE: at this point, HOME seems to be still "/home/jupyter" (so we install in its .local)
                # BUT, after the JupyterHub user is inited, we have `home` as HOME (e.g. /tmp/1 - and we want to save in its .local)
                for NBEXT in ["hide_input", "codefolding", "init_cell", "keyboard_shortcut_editor"]:
                  os.system( "HOME={} jupyter nbextension install {} --user".format(home, os.path.join(CONBE_PATH, NBEXT)) )
                  os.system( "HOME={} jupyter nbextension enable {}/main --user".format(home, NBEXT) )
            except e:
                print(e)
        return preexec

    def user_env(self, env):
        env['USER'] = self.user.name
        env['HOME'] = self.home_path
        env['SHELL'] = '/bin/bash'
        return env
