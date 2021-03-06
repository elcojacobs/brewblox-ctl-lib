
import click
from brewblox_ctl import click_helpers, sh

from brewblox_ctl_lib import utils


@click.group(cls=click_helpers.OrderedGroup)
def cli():
    """Command collector"""


def discover_device(discovery, release):
    sudo = utils.optsudo()
    mdns = 'brewblox/brewblox-mdns:{}'.format(utils.docker_tag(release))

    utils.info('Pulling image...')
    sh('{}docker pull {}'.format(sudo, mdns), silent=True)

    utils.info('Discovering devices...')
    raw_devs = sh('{}docker run '.format(sudo) +
                  '--rm -it ' +
                  '--net=host ' +
                  '-v /dev/serial:/dev/serial ' +
                  '{} --cli --discovery {}'.format(mdns, discovery),
                  capture=True)

    return [dev for dev in raw_devs.split('\n') if dev.rstrip()]


def find_device(discovery, release, device_host):
    devs = discover_device(discovery, release)

    if not devs:
        click.echo('No devices discovered')
        return None

    if device_host:
        for dev in devs:  # pragma: no cover
            if device_host in dev:
                click.echo('Discovered device "{}" matching device host {}'.format(dev, device_host))
                return dev

    for i, dev in enumerate(devs):
        click.echo('device {} :: {}'.format(i+1, dev))

    idx = click.prompt('Which device do you want to use?',
                       type=click.IntRange(1, len(devs)),
                       default=1)

    return devs[idx-1]


@cli.command()
@click.option('--discovery',
              type=click.Choice(['all', 'usb', 'wifi']),
              default='all',
              help='Discovery setting. Use "all" to check both Wifi and USB')
@click.option('--release',
              default=None,
              help='Brewblox release track')
def discover_spark(discovery, release):
    """
    Discover available Spark controllers.

    This prints device ID for all devices, and IP address for Wifi devices.
    If a device is connected over USB, and has Wifi active, it may show up twice.

    Multicast DNS (mDNS) is used for Wifi discovery. Whether this works is dependent on your router's configuration.
    """
    utils.confirm_mode()
    for dev in discover_device(discovery, release):
        click.echo(dev)
    utils.info('Done!')


@cli.command()
@click.option('-n', '--name',
              prompt='How do you want to call this service? The name must be unique',
              callback=utils.check_service_name,
              help='Service name')
@click.option('--discover-now/--no-discover-now',
              default=True,
              help='Select from discovered devices if --device-id is not set')
@click.option('--device-id',
              help='Checked device ID')
@click.option('--discovery',
              type=click.Choice(['all', 'usb', 'wifi']),
              default='all',
              help='Discovery setting. Use "all" to check both Wifi and USB')
@click.option('--device-host',
              help='Static controller URL')
@click.option('-c', '--command',
              help='Additional arguments to pass to the service command')
@click.option('-f', '--force',
              is_flag=True,
              help='Allow overwriting an existing service')
@click.option('--release',
              help='Brewblox release track used by the discovery container.')
def add_spark(name, discover_now, device_id, discovery, device_host, command, force, release):
    """
    Create or update a Spark service.

    If you run brewblox-ctl add-spark without any arguments,
    it will prompt you for required info, and then create a sensibly configured service.

    If you want to fine-tune your service configuration, multiple arguments are available.

    For a detailed explanation: https://brewblox.netlify.com/user/connect_settings.html
    """
    utils.check_config()
    utils.confirm_mode()

    sudo = utils.optsudo()
    config = utils.read_compose()

    if name in config['services'] and not force:
        click.echo('Service "{}" already exists. Use the --force flag if you want to overwrite it'.format(name))
        raise SystemExit(1)

    if device_id is None and discover_now:
        dev = find_device(discovery, release, device_host)

        if dev:
            device_id = dev.split(' ')[1]
        elif device_host is None:
            # We have no device ID, and no device host. Avoid a wildcard service
            click.echo('No valid combination of device ID and device host.')
            raise SystemExit(1)

    commands = [
        '--name=' + name,
        '--mdns-port=${BREWBLOX_PORT_MDNS}',
        '--discovery=' + discovery,
    ]

    if device_id:
        commands += ['--device-id=' + device_id]

    if device_host:
        commands += ['--device-host=' + device_host]

    if command:
        commands += [command]

    config['services'][name] = {
        'image': 'brewblox/brewblox-devcon-spark:{}'.format(utils.docker_tag('${BREWBLOX_RELEASE}')),
        'privileged': True,
        'restart': 'unless-stopped',
        'labels': [
            'traefik.port=5000',
            'traefik.frontend.rule=PathPrefix: /{}'.format(name),
        ],
        'command': ' '.join(commands)
    }

    utils.write_compose(config)
    click.echo("Added Spark service '{}'.".format(name))
    click.echo('It will automatically show up in the UI.\n')
    if utils.confirm("Do you want to run 'brewblox-ctl up' now?"):
        sh('{}docker-compose up -d --remove-orphans'.format(sudo))
