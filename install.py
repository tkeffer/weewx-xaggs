#
#    Copyright (c) 2020 Tom Keffer <tkeffer@gmail.com>
#
#    See the file LICENSE.txt for your full rights.
#
"""Installer for XStats"""

from distutils.version import StrictVersion

from weecfg.extension import ExtensionInstaller
import weewx

# REQUIRED_WEEWX = "4.1.0"
# if StrictVersion(weewx.__version__) < StrictVersion(REQUIRED_WEEWX):
#     raise weewx.UnsupportedFeature("weewx %s or greater is required, found %s"
#                                    % (REQUIRED_WEEWX, weewx.__version__))


def loader():
    return XStatsInstaller()


class XStatsInstaller(ExtensionInstaller):
    def __init__(self):
        super(XStatsInstaller, self).__init__(
            version="0.4",
            name='xstats',
            description='XTypes extension that calculates historical highs and lows for a date, '
                        'or days above or below a mean value',
            author="Thomas Keffer",
            author_email="tkeffer@gmail.com",
            report_services='user.xstats.XStatsService',
            files=[('bin/user', ['bin/user/xstats.py'])]
        )
