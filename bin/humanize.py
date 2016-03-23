#!/usr/bin/env python

import sys
from splunklib.searchcommands import \
    dispatch, StreamingCommand, Configuration, Option, validators, Set
import humanize
import datetime


@Configuration()
class HumanizeCommand(StreamingCommand):
    """ %(synopsis)

    ##Syntax

    %(syntax)

    ##Description

    %(description)

    """

    humanize_commands = Set("intcomma",
        "intword",
        "apnumber",
        "naturalday",
        "naturaldate",
        "naturaldelta",
        "naturaltime",
        "naturalsize",
        "fractional",
        )

    command = Option(
        doc='''
        **Syntax:** **command=***<command>*
        **Description:** Name of the Humanize command that will run''',
        require=True, validate=humanize_commands)

    out = Option(
        doc='''
        **Syntax:** **command=***<command>*
        **Description:** Name of the output field''',
        require=False, validate=validators.Fieldname())

    def processDate(self, event, field):
        try:
            timestamp = float(event[field])
            value = repr(datetime.date.fromtimestamp(timestamp))
            return eval("humanize." + self.command + "(" + value + ")")
        except ValueError:
            pass

    def processTime(self, event, field):
        try:
            timestamp = float(event[field])
            value = repr(datetime.datetime.fromtimestamp(timestamp))
            return eval("humanize." + self.command + "(" + value + ")")
        except ValueError:
            pass

    def stream(self, events):
        self.logger.debug('HumanizeCommand: {}\n {}'.format(self, self.command))  # logs command line
        for event in events:
            for field in self.fieldnames:
                if self.command in ['naturalday', 'naturaldate'] and field in event and len(event[field]) > 0:
                    event[field] = self.processDate(event, field)
                elif self.command == 'naturaltime' and field in event and len(event[field]) > 0:
                    event[field] = self.processTime(event, field)
                elif field in event and len(event[field]) > 0:
                    event[field] = eval("humanize." + self.command + "(" + event[field] + ")")
            yield event


dispatch(HumanizeCommand, sys.argv, sys.stdin, sys.stdout, __name__)
