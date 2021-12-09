#
#    Copyright (c) 2020 Tom Keffer <tkeffer@gmail.com>
#
#    See the file LICENSE.txt for your full rights.
#
"""WeeWX XTypes extensions that add new types of aggregations. It can calculate:

  - historical highs, lows for a date, and the times they occurred;
  - the number of days in a time span with the average greater than, greater than or equal to,
    less than, or less than or equal, to a value.

    WeeWX Version 4.2 or later REQUIRED.

    """

import datetime

import weedb
import weewx.tags
import weewx.units
import weewx.xtypes
from weeutil.weeutil import isStartOfDay
from weewx.engine import StdService

VERSION = "0.8"

# We have to add this to the collection of special aggregation types that change the unit. For example, asking for the
# time of a minimum temperature returns something in group_time, not group_temperature.
weewx.units.agg_group['historical_mintime'] = 'group_time'
weewx.units.agg_group['historical_maxtime'] = 'group_time'


class XAggsHistorical(weewx.xtypes.XType):
    """XTypes extension to calculate historical statistics for days-of-the-year"""

    sql_stmts = {
        'sqlite': {
            'historical_min': "SELECT MIN(`min`) FROM {table}_day_{obs_type} "
                              "WHERE STRFTIME('%m-%d', dateTime,'unixepoch','localtime') = '{month:02d}-{day:02d}';",
            'historical_mintime': "SELECT `mintime` FROM {table}_day_{obs_type} "
                                  "WHERE STRFTIME('%m-%d', dateTime,'unixepoch','localtime') = '{month:02d}-{day:02d}' "
                                  "ORDER BY `min` ASC LIMIT 1;",
            'historical_min_avg': "SELECT AVG(`min`) FROM {table}_day_{obs_type} "
                                  "WHERE STRFTIME('%m-%d', dateTime,'unixepoch','localtime') = '{month:02d}-{day:02d}';",
            'historical_max': "SELECT MAX(`max`) FROM {table}_day_{obs_type} "
                              "WHERE STRFTIME('%m-%d', dateTime,'unixepoch','localtime') = '{month:02d}-{day:02d}';",
            'historical_maxtime': "SELECT `maxtime` FROM {table}_day_{obs_type} "
                                  "WHERE STRFTIME('%m-%d', dateTime,'unixepoch','localtime') = '{month:02d}-{day:02d}' "
                                  "ORDER BY `max` DESC LIMIT 1;",
            'historical_max_avg': "SELECT AVG(`max`) FROM {table}_day_{obs_type} "
                                  "WHERE STRFTIME('%m-%d', dateTime,'unixepoch','localtime') = '{month:02d}-{day:02d}';",
            'historical_avg': "SELECT SUM(`wsum`), SUM(`sumtime`) FROM {table}_day_{obs_type} "
                              "WHERE STRFTIME('%m-%d', dateTime,'unixepoch','localtime') = '{month:02d}-{day:02d}';",
        },
        'mysql': {
            'historical_min': "SELECT MIN(`min`) FROM {table}_day_{obs_type} "
                              "WHERE FROM_UNIXTIME(dateTime, '%%m-%%d') = '{month:02d}-{day:02d}';",
            'historical_mintime': "SELECT `mintime` FROM {table}_day_{obs_type} "
                                  "WHERE FROM_UNIXTIME(dateTime, '%%m-%%d') = '{month:02d}-{day:02d}' "
                                  "ORDER BY `min` ASC, dateTime ASC LIMIT 1;",
            'historical_min_avg': "SELECT AVG(`min`) FROM {table}_day_{obs_type} "
                                  "WHERE FROM_UNIXTIME(dateTime, '%%m-%%d') = '{month:02d}-{day:02d}';",
            'historical_max': "SELECT MAX(`max`) FROM {table}_day_{obs_type} "
                              "WHERE FROM_UNIXTIME(dateTime, '%%m-%%d') = '{month:02d}-{day:02d}';",
            'historical_maxtime': "SELECT `maxtime` FROM {table}_day_{obs_type} "
                                  "WHERE FROM_UNIXTIME(dateTime, '%%m-%%d') = '{month:02d}-{day:02d}' "
                                  "ORDER BY `max` DESC, dateTime ASC LIMIT 1;",
            'historical_max_avg': "SELECT AVG(`max`) FROM {table}_day_{obs_type} "
                                  "WHERE FROM_UNIXTIME(dateTime, '%%m-%%d') = '{month:02d}-{day:02d}';",
            'historical_avg': "SELECT SUM(`wsum`), SUM(`sumtime`) FROM {table}_day_{obs_type} "
                              "WHERE FROM_UNIXTIME(dateTime, '%%m-%%d') = '{month:02d}-{day:02d}';",
        },
    }

    def get_aggregate(self, obs_type, timespan, aggregate_type, db_manager, **option_dict):
        """Calculate historical statistical aggregation for a date in the year"""

        dbtype = db_manager.connection.dbtype

        # Do we know how to calculate this kind of aggregation?
        if aggregate_type not in XAggsHistorical.sql_stmts[dbtype]:
            raise weewx.UnknownAggregation(aggregate_type)

        # The time span must lie on midnight-to-midnight boundaries
        if db_manager.first_timestamp is None or db_manager.last_timestamp is None:
            raise weewx.UnknownAggregation(aggregate_type)
        if not (isStartOfDay(timespan.start) or timespan.start == db_manager.first_timestamp) \
                or not (isStartOfDay(timespan.stop) or timespan.stop == db_manager.last_timestamp):
            raise weewx.UnknownAggregation("%s of %s" % (aggregate_type, timespan))

        start_day = datetime.date.fromtimestamp(timespan.start)
        stop_day = datetime.date.fromtimestamp(timespan.stop)

        # The timespan must cover just one day
        delta = stop_day - start_day
        if delta.days != 1:
            raise weewx.UnknownAggregation("%s of %s" % (aggregate_type, timespan))

        interp_dict = {
            'table': db_manager.table_name,
            'obs_type': obs_type,
            'month': start_day.month,
            'day': start_day.day
        }

        # Get the correct sql statement, and format it with the interpolation dictionary.
        sql_stmt = XAggsHistorical.sql_stmts[dbtype][aggregate_type].format(**interp_dict)

        try:
            row = db_manager.getSql(sql_stmt)
        except weedb.NoColumnError:
            raise weewx.UnknownType(aggregate_type)

        # Given the result set, calculate the desired value
        if not row or None in row:
            value = None
        elif aggregate_type == 'historical_avg':
            value = row[0] / row[1] if row[1] else None
        else:
            value = row[0]

        # Look up the unit type and group of this combination of observation type and aggregation:
        u, g = weewx.units.getStandardUnitType(db_manager.std_unit_system, obs_type,
                                               aggregate_type)

        # Form the ValueTuple and return it:
        return weewx.units.ValueTuple(value, u, g)


class XAggsAvg(weewx.xtypes.XType):
    """XTypes extension to calculate days with an average above or below a certain value"""

    sql_stmts = {
        'avg_ge': "SELECT SUM(wsum/sumtime >= {val}) FROM {table}_day_{obs_type} "
                  "WHERE dateTime >= {start} AND dateTime < {stop};",
        'avg_gt': "SELECT SUM(wsum/sumtime > {val}) FROM {table}_day_{obs_type} "
                  "WHERE dateTime >= {start} AND dateTime < {stop};",
        'avg_le': "SELECT SUM(wsum/sumtime <= {val}) FROM {table}_day_{obs_type} "
                  "WHERE dateTime >= {start} AND dateTime < {stop};",
        'avg_lt': "SELECT SUM(wsum/sumtime < {val}) FROM {table}_day_{obs_type} "
                  "WHERE dateTime >= {start} AND dateTime < {stop};",
    }

    def get_aggregate(self, obs_type, timespan, aggregate_type, db_manager, **option_dict):
        """Calculate days with an average value above or below something"""

        if aggregate_type not in XAggsAvg.sql_stmts:
            raise weewx.UnknownAggregation(aggregate_type)

        if db_manager.std_unit_system is None:
            raise weewx.CannotCalculate("No unit system in database")

        val = option_dict.get('val')

        # Convert val to the same unit system used in the database
        val_std = weewx.units.convertStd(val, db_manager.std_unit_system)

        # Form the interpolation dictionary:
        interp_dict = {
            'table': db_manager.table_name,
            'obs_type': obs_type,
            'val': val_std[0],
            'start': timespan.start,
            'stop': timespan.stop,
        }

        # Get the correct sql statement, then format it with the interpolation dictionary.
        sql_stmt = XAggsAvg.sql_stmts[aggregate_type].format(**interp_dict)

        # Hit the database:
        try:
            row = db_manager.getSql(sql_stmt)
        except weedb.NoColumnError:
            raise weewx.UnknownType(obs_type)

        # Get the value out of the result set
        days = row[0] if row else None

        # Form a ValueTuple and return it
        vt = weewx.units.ValueTuple(days, 'count', 'group_count')
        return vt


class XAggsService(StdService):
    """WeeWX dummy service for initializing the XStats extensions.

    This service should be included in the `xtypes_services` section of weewx.conf.
    """

    def __init__(self, engine, config_dict):
        super(XAggsService, self).__init__(engine, config_dict)

        # Create instances of XStatsHistorical and XStatsAvg:
        self.xstats_historical = XAggsHistorical()
        self.xstats_avg = XAggsAvg()
        # Register them with the XTypes system:
        weewx.xtypes.xtypes.append(self.xstats_historical)
        weewx.xtypes.xtypes.append(self.xstats_avg)

    def shutDown(self):
        # The engine is shutting down. Remove the XType extensions:
        weewx.xtypes.xtypes.remove(self.xstats_historical)
        weewx.xtypes.xtypes.remove(self.xstats_avg)


if __name__ == '__main__':
    import time
    import weewx.manager
    from weeutil.weeutil import archiveDaySpan, archiveMonthSpan

    db_manager = weewx.manager.DaySummaryManager.open({'SQLITE_ROOT': '/home/weewx/archive',
                                                       'database_name': 'weewx.sdb',
                                                       'driver': 'weedb.sqlite'})

    # 2-jan-2020, 0400:
    ts = time.mktime((2020, 1, 1, 4, 0, 0, 0, 0, -1))
    dayspan = archiveDaySpan(ts)
    print(dayspan)
    monthspan = archiveMonthSpan(ts)
    print(monthspan)

    dh = XAggsHistorical()
    r = dh.get_aggregate('outTemp', dayspan, 'historical_min', db_manager)
    print(r)

    r = dh.get_aggregate('outTemp', dayspan, 'historical_mintime', db_manager)
    print(r)

    r = dh.get_aggregate('outTemp', dayspan, 'historical_min_avg', db_manager)
    print(r)

    r = dh.get_aggregate('outTemp', dayspan, 'historical_max', db_manager)
    print(r)

    r = dh.get_aggregate('outTemp', dayspan, 'historical_maxtime', db_manager)
    print(r)

    r = dh.get_aggregate('outTemp', dayspan, 'historical_max_avg', db_manager)
    print(r)

    r = dh.get_aggregate('outTemp', dayspan, 'historical_avg', db_manager)
    print(r)

    # da = XStatsAvg()
    # r = da.get_aggregate('outTemp', monthspan, 'avg_ge', db_manager)((5.0, 'degree_C', 'group_temperature'))
    # print(r)
