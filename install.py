#
#    Copyright (c) 2020 Tom Keffer <tkeffer@gmail.com>
#
#    See the file LICENSE.txt for your full rights.
#
"""Installer for XAggs"""

from distutils.version import StrictVersion

from weecfg.extension import ExtensionInstaller
import weewx

REQUIRED_WEEWX = "4.2.0"
if StrictVersion(weewx.__version__) < StrictVersion(REQUIRED_WEEWX):
    raise weewx.UnsupportedFeature("weewx %s or greater is required, found %s"
                                   % (REQUIRED_WEEWX, weewx.__version__))


def loader():
    return XAggsInstaller()


class XAggsInstaller(ExtensionInstaller):
    def __init__(self):
        super(XAggsInstaller, self).__init__(
            version="0.8",
            name='xaggs',
            description='XTypes extension that calculates historical highs and lows for a date, '
                        'or days above or below a mean value',
            author="Thomas Keffer",
            author_email="tkeffer@gmail.com",
            xtype_services='user.xaggs.XAggsService',
            files=[('bin/user', ['bin/user/xaggs.py'])]
        )
