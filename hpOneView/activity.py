# -*- coding: utf-8 -*-

"""
activity.py
~~~~~~~~~~~~

This module implements the Activity HP OneView REST API
"""

__title__ = 'activity'
__version__ = '0.0.1'
__copyright__ = '(C) Copyright 2012-2014 Hewlett-Packard Development ' \
                ' Company, L.P.'
__license__ = 'MIT'
__status__ = 'Development'

###
# (C) Copyright 2014 Hewlett-Packard Development Company, L.P.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
###


from hpOneView.common import *
from hpOneView.connection import *
from hpOneView.exceptions import *
import time  # For sleep
import sys  # For verbose


TaskErrorStates = ['Error', 'Warning', 'Terminated', 'Killed']
TaskCompletedStates = ['Error', 'Warning', 'Completed', 'Terminated', 'Killed']
TaskPendingStates = ['New', 'Starting', 'Running', 'Suspended', 'Stopping']


class activity(object):

    def __init__(self, con):
        self._con = con

    ###########################################################################
    # Tasks
    ###########################################################################
    #
    def get_task_associated_resource(self, task):
        if not task:
            return {}
        if task['type'] == 'TaskResource':
            obj = self._con.get(task['associatedResourceUri'])
            tmp = {
                'resourceName': obj['name'],
                'associationType': None,
                'resourceCategory': None,
                'resourceUri': obj['uri']}
        elif task['type'] == 'TaskResourceV2':
            tmp = task['associatedResource']
        else:
            raise HPOneViewInvalidResource('Task resource is not a recognized'
                                           ' version')
        return tmp

    def make_task_entity_tuple(self, obj):
        task = {}
        entity = {}
        if obj:
            if obj['category'] == 'tasks' or obj['category'] == 'backups':
                # it is an error if type is not in obj, so let the except flow
                uri = ''
                if obj['type'] == 'TaskResource':
                    task = obj
                    uri = obj['associatedResourceUri']
                elif obj['type'] == 'TaskResourceV2':
                    task = obj
                    uri = obj['associatedResource']['resourceUri']
                elif obj['type'] == 'BACKUP':
                    task = self._con.get(obj['taskUri'])
                    uri = obj['uri']
                else:
                    raise HPOneViewInvalidResource('Task resource is not a'
                                                   ' recognized version')
                if uri:
                    try:
                        entity = self._con.get(uri)
                    except HPOneViewException:
                        raise
                else:
                    entity = obj
            else:
                raise HPOneViewUnknownType('Unknown object type')

        return task, entity

    def is_task_running(self, task):
        global TaskPendingStates
        if 'uri' in task:
            task = self._con.get(task['uri'])
            if 'taskState' in task and task['taskState'] in TaskPendingStates:
                return True
        return False

    def wait4task(self, task, tout=60, verbose=False):
        count = 0
        if task is None:
            return None
        while self.is_task_running(task):
            if verbose:
                    sys.stdout.write('Task still running after %d seconds   \r'
                                     % count)
                    sys.stdout.flush()
            time.sleep(1)
            count += 1
            if count > tout:
                raise HPOneViewTimeout('Waited ' + str(tout) +
                                       ' seconds for task to complete, aborting')
        task = self._con.get(task['uri'])
        if task['taskState'] in TaskErrorStates and task['taskState'] != 'Warning':
                err = task['taskErrors'][0]
                msg = err['message']
                if msg is not None:
                    raise HPOneViewTaskError(msg)
                elif task['taskStatus'] is not None:
                    raise HPOneViewTaskError(task['taskStatus'])
                else:
                    raise HPOneViewTaskError('Unknown Exception')
        return task

    def wait4tasks(self, tasks, tout=60, verbose=False):
        running = list(filter(self.is_task_running, tasks[:]))
        count = 0
        while running:
            if verbose:
                    print(('Tasks still running after %s seconds', count))
                    print(running)
            time.sleep(1)
            count += 1
            running = list(filter(self.is_task_running, running))
            if count > tout:
                raise HPOneViewTimeout('Waited 60 seconds for task to complete'
                                       ', aborting')

    def get_tasks(self):
        global uri
        return get_members(self._con.get(uri['task']))

    ###########################################################################
    # Alerts
    ###########################################################################
    def get_alerts(self, AlertState='All'):
        global uri
        if AlertState == 'All':
            return get_members(self._con.get(uri['alerts']))
        else:
            return(self._con.get_entities_byfield(uri['alerts'],
                                                  'alertState',
                                                  AlertState))

    def delete_alert(self, alert):
        self._con.delete(alert['uri'])

    def delete_alerts(self):
        self._con.delete(uri['alerts'])

    def update_alert(self, alert, alertMap):
        task, moddedAlert = self._con.put(alert['uri'], alertMap)
        return moddedAlert

    ###########################################################################
    # Audit Logs
    ###########################################################################
    def get_audit_logs(self, query=''):
        global uri
        body = self._con.get(uri['audit-logs'] + '?' + query)
        return get_members(body)

    def create_audit_log(self, auditLogRecord):
        global uri
        self._con.post(uri['audit-logs'], auditLogRecord)
        return

    def download_audit_logs(self, filename):
        body = self._con.get(uri['audit-logs-download'])
        f = open(filename, 'wb')
        f.write(body)
        f.close()
        return

    ###########################################################################
    # Events
    ###########################################################################
    def get_events(self, query=''):
        global uri
        body = self._con.get(uri['events'] + '?' + query)
        return get_members(body)

    def create_event(self, eventRecord):
        global uri
        self._con.post(uri['events'], eventRecord)
        return
