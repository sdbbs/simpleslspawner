import os
import os.path
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
                os.system("jupyter contrib nbextension install --user")
                os.system("jupyter nbextensions_configurator enable --user")
                os.system("jupyter hide_input enable --user")
                os.system("jupyter codefolding enable --user")
                os.system("jupyter init_cell enable --user")
                os.system("jupyter keyboard_shortcut_editor enable --user")
            except e:
                print(e)
        return preexec

    def user_env(self, env):
        env['USER'] = self.user.name
        env['HOME'] = self.home_path
        env['SHELL'] = '/bin/bash'
        return env
