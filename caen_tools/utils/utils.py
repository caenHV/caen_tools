import configparser
import pathlib


def config_processor(configfile):
    """Opens custom config file
    (if configfile is None this uses default config)
    """

    default_config = pathlib.Path(__file__).parent.parent.parent / "config.ini"
    configs = [default_config]

    settings = configparser.ConfigParser(
        interpolation=configparser.ExtendedInterpolation()
    )
    if configfile is not None:
        configs.append(configfile.name)

    settings.read(configs)
    return settings
