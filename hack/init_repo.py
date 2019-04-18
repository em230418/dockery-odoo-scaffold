#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import re
from distutils.spawn import find_executable

import click
from _helpers import (
    basename,
    call_cmd,
    dirname,
    get_hack_dir,
    green,
    mkdir_p,
    red,
    replace_in_file,
    yellow,
)

ODOO_VERSIONS = ("10.0", "11.0", "12.0", "master")
IS_GIT_URL_REGEXP = (
    r"(?:git|ssh|https?|git@[-\w.]+):(\/\/)?(.*?)(\.git)(\/?|\#[-\d\w._]+?)$"
)
REPO_REGEXP = "(?P<host>(git@|https://)([\\w\\.@]{1,})(/|:))(?P<owner>[\\w,\\-,_]{1,})/(?P<repo>[\\w,\\-,_]{1,})(.git){0,1}((/){0,1})"  # noqa


class OdooVersionChoice(click.types.Choice):
    name = "odoo-version"

    def __init__(self, choices, case_sensitive=True):
        super(OdooVersionChoice, self).__init__(choices, case_sensitive)
        self.versions = choices
        self.choices = [str(x + 1) for x in range(len(choices))]
        click.echo("\nAvailable Odoo Versions:")
        click.echo(
            "\n".join(
                [
                    "{}) {}".format(i + 1, choice)
                    for i, choice in enumerate(self.versions)
                ]
            )
        )
        click.echo("\n")

    def convert(self, value, param, ctx):
        value = super(OdooVersionChoice, self).convert(value, param, ctx)
        normed_value = ODOO_VERSIONS[int(value) - 1]
        if normed_value in self.versions:
            click.echo(green("Odoo version: {}".format(normed_value)))
            return normed_value
        else:
            self.fail(red(value) + " can't be converted to Odoo Version", param, ctx)

        return value


class GitRepo(click.types.StringParamType):
    name = "git-repo"

    def convert(self, value, param, ctx):
        value = super(GitRepo, self).convert(value, param, ctx)
        found = re.match(IS_GIT_URL_REGEXP, value)

        if not found:
            self.fail(red(value) + " is not a git url", param, ctx)

        return value


def print_edition(ctx, param, value):
    def get_edition(odoo_version, value):
        ee = "EE(Enterprise Edition)"
        ce = "CE(Community Edition)"
        return green("Odoo " + odoo_version + " " + (ee if value else ce))

    click.echo("You selected " + get_edition(ctx.params["odoo_version"], value))


@click.command()
@click.option(
    "--odoo-version",
    type=OdooVersionChoice(ODOO_VERSIONS),
    prompt="Please select Odoo version",
)
@click.option(
    "--is-enterprise",
    is_flag=True,
    default=False,
    prompt="Use Odoo Enterprise (access required)",
    callback=print_edition,
)
def main(odoo_version, is_enterprise):
    project = basename(dirname(os.path.join(get_hack_dir())))

    additional_repos = []
    fist_repo = True
    while True:
        msg = "Add additional repo" if fist_repo else "Add another repo"
        add_new = click.confirm(msg, default=True)
        if not add_new:
            break
        repo = click.prompt("Enter Repo", type=GitRepo())
        fist_repo = False
        additional_repos += [repo]

    for repo_url in additional_repos:
        org = basename(dirname(repo_url))
        matches = re.search(REPO_REGEXP, repo_url)
        try:
            repo_name = matches.group("repo")
        except (AttributeError, IndexError):
            repo_name = basename(repo_url).split(".")[0]

        mkdir_p(os.path.join("vendor", org))

        call_cmd(
            "git submodule add -b {odoo_version} {repo_url} "
            "vendor/{org}/{repo_name}".format(
                odoo_version=odoo_version,
                repo_url=repo_url,
                org=org,
                repo_name=repo_name,
            ),
            echo_cmd=True,
            exit_on_error=False,
        )

    call_cmd(
        "git submodule add -b {odoo_version} "
        "https://github.com/odoo/odoo.git vendor/odoo/cc".format(
            odoo_version=odoo_version
        ),
        echo_cmd=True,
        exit_on_error=False,
    )

    if is_enterprise:
        call_cmd(
            "git submodule add -b {odoo_version} "
            "https://github.com/odoo/enterprise.git vendor/odoo/ee".format(
                odoo_version=odoo_version
            ),
            echo_cmd=True,
            exit_on_error=False,
        )

    # Seed Placeholders
    replacements = {
        ("Dockerfile", ".env"): [
            {"from": "{{ PROJECT }}", "to": project},
            {"from": "{{ DEFAULT_BRANCH }}", "to": odoo_version},
        ]
    }
    for files, rules in replacements.items():
        for rule in rules:
            replace_in_file(files, rule["from"], rule["to"])

    # Git commit
    call_cmd("git add .")
    call_cmd('git commit -m "Customize Project"')

    compose_impersonation = os.getenv("COMPOSE_IMPERSONATION")
    if not compose_impersonation:
        compose_impersonation = "{}:{}".format(os.getuid(), os.getgid())
        os.putenv("COMPOSE_IMPERSONATION", compose_impersonation)
        os.environ["COMPOSE_IMPERSONATION"] = compose_impersonation
        try:
            with open(os.path.realpath(os.path.expanduser("~/.bashrc")), "a") as file:
                file.write(
                    "\nexport COMPOSE_IMPERSONATION='{COMPOSE_IMPERSONATION}'\n".format(
                        COMPOSE_IMPERSONATION=compose_impersonation
                    )
                )
        except IOError:
            click.echo(
                red(
                    "Failed adding following line to {}:\n\t "
                    "export COMPOSE_IMPERSONATION='{}'\n "
                    "Please add it manually for full feature support.".format(
                        os.path.realpath(os.path.expanduser("~/.bashrc")),
                        compose_impersonation,
                    )
                )
            )

    if not find_executable("pre-commit"):  # Python 2.4+
        click.echo(
            red(
                "We install a bunch of pre-commit.com hooks"
                "to help you produce better code ...\n"
            )
        )
        call_cmd("sudo -k -H pip install pre-commit")
    call_cmd("pre-commit install")

    click.echo("Next, run: " + yellow("`make info`"))


if __name__ == "__main__":
    main()
