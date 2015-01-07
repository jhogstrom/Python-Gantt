#!/usr/bin/env python3
# -*- coding: utf-8-unix -*-
"""
org2gantt.py - version and date, see below

Author : Alexandre Norman - norman at xael.org
Licence : GPL v3 or any later version


This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""


__author__ = 'Alexandre Norman (norman at xael.org)'
__version__ = '0.2.1'
__last_modification__ = '2015.01.05'


import datetime
import logging
import os
import sys
import re

############################################################################

try:
    import clize
except ImportError:
    print("This program uses clize. See : https://github.com/epsy/clize")
    sys.exit(1)

############################################################################

try:
    import Orgnode
except ImportError:
    print("This program uses Orgnode. See : http://members.optusnet.com.au/~charles57/GTD/orgnode.html")
    sys.exit(1)

############################################################################

def __show_version__(name, **kwargs):
    """
    Show version
    """
    import os
    print("{0} version {1}".format(os.path.basename(name), __version__))
    return True


############################################################################

def _iso_date_to_datetime(isodate):
    """
    """
    __LOG__.debug("_iso_date_to_datetime ({0})".format({'isodate':isodate}))
    y, m, d = isodate.split('-')
    if m[0] == '0':
        m = m[1]
    if d[0] == '0':
        d = d[1]
    return "datetime.date({0}, {1}, {2})".format(y, m, d)

############################################################################

__LOG__ = None

############################################################################

def _init_log_to_sysout(level=logging.INFO):
    """
    """
    global __LOG__
    logger = logging.getLogger("org2gantt")
    logger.setLevel(level)
    fh = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    __LOG__ = logging.getLogger("org2gantt")
    return

############################################################################

@clize.clize(
    alias = {
        'org': ('o',),
        'debug': ('d',),
        'gantt': ('g',),
        },
    extra = (
        clize.make_flag(
            source=__show_version__,
            names=('version', 'v'),
            help="Show the version",
            ),
        )
    )
def __main__(org, gantt='', debug=False):
    """
    org2gantt.py
    
    org: org-mode filename

    gantt: output python-gantt filename (default sysout)
    
    debug: debug

    Example :
    python org2gantt.py TEST.org

    Written by : Alexandre Norman <norman at xael.org>
    """
    global __LOG__
    if debug:
        _init_log_to_sysout(logging.DEBUG)
    else:
        _init_log_to_sysout()

    if not os.path.isfile(org):
        __LOG__.error('** File do not exist : {0}'.format(org))
        sys.exit(1)
    
    # load orgfile
    nodes = Orgnode.makelist(org)

    __LOG__.debug('_analyse_nodes ({0})'.format({'nodes':nodes}))

    gantt_code = """#!/usr/bin/env python3
# -*- coding: utf-8-unix -*-

import datetime
import gantt
"""


    # Find CONFIGURATION in heading
    n_configuration = None
    for n in nodes:
        if n.headline == "CONFIGURATION":
            n_configuration = n

    planning_start_date = None
    planning_end_date = None
    planning_today_date = _iso_date_to_datetime(str(datetime.date.today()))

    # Generate code for configuration
    if n_configuration is not None:
        if 'start_date' in n_configuration.properties:
            dates = re.findall('[1-9][0-9]{3}-[0-9]{2}-[0-9]{2}', n_configuration.properties['start_date'])
            if len(dates) == 1:
                planning_start_date = _iso_date_to_datetime(dates[0])

        if 'end_date' in n_configuration.properties:
            dates = re.findall('[1-9][0-9]{3}-[0-9]{2}-[0-9]{2}', n_configuration.properties['end_date'])
            if len(dates) == 1:
                planning_end_date = _iso_date_to_datetime(dates[0])

        if 'today' in n_configuration.properties:
            dates = re.findall('[1-9][0-9]{3}-[0-9]{2}-[0-9]{2}', n_configuration.properties['today'])
            if len(dates) == 1:
                planning_today_date = _iso_date_to_datetime(dates[0])



    # Find RESSOURCES in heading
    n_ressources = []
    ressources_id = []
    found = False
    plevel = 0
    for n in nodes:
        if found == True and n.level > plevel:
            n_ressources.append(n)
        elif found == True and n.level <= plevel:
            break
        if found == False and n.headline == "RESSOURCES":
            found = True
            plevel = n.level

    # Generate code for ressources
    gantt_code += "\n#### Ressources \n"
    next_level = 0
    current_level = 0
    current_group = None

    for nr in range(len(n_ressources)):
        r = n_ressources[nr]

        rname = r.headline
        rid = r.properties['ressource_id'].strip()
        
        if rid in ressources_id:
            __LOG__.critical('** Duplicate ressource_id: [{0}]'.format(rid))
            sys.exit(1)

        ressources_id.append(rid)

        if ' ' in rid:
            __LOG__.critical('** Space in ressource_id: [{0}]'.format(rid))
            sys.exit(1)

        new_group_this_turn = False

        current_level = r.level
        if nr < len(n_ressources) - 2:
            next_level = n_ressources[nr+1].level

        # Group mode
        if current_level < next_level:
            gantt_code += "{0} = gantt.GroupOfRessources('{1}')\n".format(rid, rname)
            current_group = rid
            new_group_this_turn = True
        # Ressource
        else:
            gantt_code += "{0} = gantt.Ressource('{1}')\n".format(rid, rname)
            
        # Vacations in body of node
        for line in r.body.split('\n'):
            if line.startswith('-'):
                dates = re.findall('[1-9][0-9]{3}-[0-9]{2}-[0-9]{2}', line)
                if len(dates) == 2:
                    start, end = dates
                    gantt_code += "{0}.add_vacations(dfrom={1}, dto={2})\n".format(rid, _iso_date_to_datetime(start), _iso_date_to_datetime(end))
                elif len(dates) == 1:
                    start = dates[0]
                    gantt_code += "{0}.add_vacations(dfrom={1})\n".format(rid, _iso_date_to_datetime(start))
                
            else:
                if line != '' and not line.startswith(':'):
                    __LOG__.warning("Unknown ressource line : {0}".format(line))


        if new_group_this_turn == False and current_group is not None:
            gantt_code += "{0}.add_ressource(ressource={1})\n".format(current_group, rid)

            # end of group
            if current_level > next_level:
                current_group = None


    # Find VACATIONS in heading
    n_vacations = None
    for n in nodes:
        if n.headline == "VACATIONS":
            n_vacations = n

    # Generate code for vacations
    gantt_code += "\n#### Vacations \n"
    if n_vacations is not None:
        for line in n_vacations.body.split('\n'):
            if line.startswith('-'):
                dates = re.findall('[1-9][0-9]{3}-[0-9]{2}-[0-9]{2}', line)
                if len(dates) == 2:
                    start, end = dates
                    gantt_code += "gantt.add_vacations({0}, {1})\n".format(_iso_date_to_datetime(start), _iso_date_to_datetime(end))
                elif len(dates) == 1:
                    start = dates[0]
                    gantt_code += "gantt.add_vacations({0})\n".format(_iso_date_to_datetime(start))

            else:
                if line != '':
                    __LOG__.warning("Unknown vacation line : {0}".format(line))


    # Generate code for Projects
    gantt_code += "\n#### Projects \n"
    cproject = 0
    ctask = 0
    prj_found = False
    tasks_name = {}
    for n in nodes:
        # new project heading
        if n.level == 1 and  not n.headline in ('RESSOURCES', 'VACATIONS', 'CONFIGURATION') and 'no_gantt' not in n.tags:
            cproject += 1
            gantt_code += "###### Project {0} \n".format(n.headline)
            gantt_code += "project_{0} = gantt.Project(name='{1}')\n".format(cproject, n.headline)
            prj_found = True
        elif n.level == 1:
            prj_found = False
        elif n.level > 1 and prj_found == True and n.todo in ('TODO', 'STARTED', 'HOLD', 'DONE', 'WAITING'):
            ctask += 1
            name = n.properties['task_id'].strip()

            if ' ' in name:
                __LOG__.critical('** Space in task_id: [{0}]'.format(name))
                sys.exit(1)


            fullname = n.headline
            start = end = duration = None
            if n.scheduled != '':
                start = "{0}".format(_iso_date_to_datetime(str(n.scheduled)))
            if n.deadline != '':
                end = "{0}".format(_iso_date_to_datetime(str(n.deadline)))
            if 'Effort' in n.properties:
                duration = n.properties['Effort'].replace('d', '')

            try:
                depends = n.properties['BLOCKER'].split()
            except KeyError:
                depends_of = None
            else: # no exception raised
                depends_of = []
                for d in depends:
                    depends_of.append(tasks_name[d])

            try:
                percentdone = n.properties['PercentDone']
            except KeyError:
                percentdone = None

            if n.todo == 'DONE':
                if percentdone is not None:
                    __LOG__.warning('** Task [{0}] marked as done but PercentDone is set to {1}'.format(name, percentdone))
                percentdone = 100

            if len(n.tags) > 0:
                ress = "{0}".format(["{0}".format(x) for x in n.tags.keys()]).replace("'", "")
            else:
                ress = None
            gantt_code += "task_{0} = gantt.Task(name='{1}', start={2}, stop={6}, duration={3}, ressources={4}, depends_of={5}, percent_done={7}, fullname='{8}')\n".format(ctask, name, start, duration, ress, str(depends_of).replace("'", ""), end, percentdone, fullname)
            if name in tasks_name:
                __LOG__.critical("Duplicate task id: {0}".format(name))
                sys.exit(1)

            tasks_name["{0}".format(name)] = "task_{0}".format(ctask)
            gantt_code += "project_{0}.add_task(task_{1})\n".format(cproject, ctask)


    gantt_code += "\n#### Outputs \n"
    gantt_code += "project_0 = gantt.Project()\n"
    for i in range(1, cproject + 1):
        gantt_code += "project_{0}.make_svg_for_tasks(filename='project_{0}.svg', today={1}, start={2}, end={3})\n".format(i, planning_today_date, planning_start_date, planning_end_date)
        gantt_code += "project_{0}.make_svg_for_ressources(filename='project_{0}_ressources.svg', today={1}, start={2}, end={3})\n".format(i, planning_today_date, planning_start_date, planning_end_date)
        gantt_code += "project_0.add_task(project_{0})\n".format(i)

    gantt_code += "project_0.make_svg_for_tasks(filename='project.svg', today={0}, start={1}, end={2})\n".format(planning_today_date, planning_start_date, planning_end_date)
    gantt_code += "project_0.make_svg_for_ressources(filename='project_ressources.svg', today={0}, start={1}, end={2})\n".format(planning_today_date, planning_start_date, planning_end_date)



    # write Gantt code
    if gantt == '':
        print(gantt_code)
    else:
        open(gantt, 'w').write(gantt_code)




    __LOG__.debug("All done. Exiting.")
    
    return

############################################################################




__all__ = ['org2gantt']


# MAIN -------------------
if __name__ == '__main__':

    clize.run(__main__)
    sys.exit(0)

    
#<EOF>######################################################################

