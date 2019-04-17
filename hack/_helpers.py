# -*- coding: utf-8 -*-
import errno
import os
import subprocess

import click


def green(msg):
    return click.style(msg, fg="green")


def red(msg):
    return click.style(msg, fg="red")


def yellow(msg):
    return click.style(msg, fg="yellow")


def cyan(msg):
    return click.style(msg, fg="cyan")


def call_cmd(cmd, echo_cmd=True, exit_on_error=True):
    if echo_cmd:
        click.echo(green(cmd))
    try:
        result = subprocess.check_output(
            cmd, stderr=subprocess.STDOUT, shell=True, universal_newlines=True
        )
    except subprocess.CalledProcessError as exc:
        click.echo(red(str(exc.output).strip()))
        if exit_on_error:
            exit(exc.returncode)
        result = "ERROR"
    return result


def call_cmd_realtime(cmd, echo_cmd=True):
    if echo_cmd:
        click.echo(green(cmd))
    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True
    )
    while True:
        line = process.stdout.readline().rstrip()
        if not line and process.poll() is not None:
            break
        yield line


def get_hack_dir():
    return os.path.dirname(os.path.abspath(__file__))


def get_from_image(image_type):
    values = {key: os.getenv(key) for key in ["FROM", "ODOO_VERSION"]}
    values.update({"IMAGE_TYPE": image_type})
    return "{FROM}:{ODOO_VERSION}-{IMAGE_TYPE}".format(**values)


def get_image_tag(image_type):
    values = {key: os.getenv(key) for key in ["IMAGE", "ODOO_VERSION"]}
    values.update({"IMAGE_TYPE": image_type})
    return "{IMAGE}:{IMAGE_TYPE}-{ODOO_VERSION}".format(**values)


def replace_in_file(files, from_str, to_str):
    if not isinstance(files, (list, tuple)):
        files = [files]
    for file_path in files:
        data = open(file_path).read()
        new_data = data.replace(from_str, to_str)
        if data != new_data:
            with open(file_path, "w") as file:
                file.write(new_data)


def basename(path):
    return os.path.basename(path)


def dirname(path):
    return os.path.abspath(os.path.join(path, ".."))


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if not (exc.errno == errno.EEXIST and os.path.isdir(path)):
            raise
