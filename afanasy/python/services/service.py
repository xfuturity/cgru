# -*- coding: utf-8 -*-

import os
import sys

import traceback

import afcommon

import cgruconfig
import cgrupathmap
import cgruutils

str_capacity = '@AF_CAPACITY@'
str_hosts = '@AF_HOSTS@'
str_hostsprefix = '-H '
str_hostseparator = ','


class service(object):  # TODO: Class names should follow CamelCase naming convention
    """This is base service class.

    :param taskInfo:
    """

    def __init__(self, taskInfo, i_verbose):
        self.taskInfo = taskInfo
        self.verbose = i_verbose
        self.log = None

        self.numeric = afcommon.checkBlockFlag(
            taskInfo['block_flags'], 'numeric'
        )
        if self.verbose: print(taskInfo)

        self.pm = cgrupathmap.PathMap()

        self.str_capacity = str_capacity
        self.str_hosts = str_hosts
        self.str_hostsprefix = str_hostsprefix
        self.str_hostseparator = str_hostseparator

        # Transfer working folder:
        taskInfo['wdir'] = self.pm.toClient(taskInfo['wdir'])

        # Process command:
        command = self.processCommandPattern()

        # Transfer command:
        command = self.pm.toClient(command)

        # Apply capacity:
        if self.taskInfo['capacity'] > 0:
            command = self.applyCmdCapacity(command)

        # Apply hosts (multihosts tasks):
        if len(self.taskInfo['hosts']):
            command = self.applyCmdHosts(command)

        taskInfo['command'] = command
        if self.verbose:
            print('Processed task command:\n' + command)

        # Process files:
        taskInfo['files'] = self.processFilesPattern()
        if self.verbose:
            print('Processed task files:')
            for afile in taskInfo['files']:
                print(afile)

        # Transfer paths in files:
        for i in range(0, len(self.taskInfo['files'])):
            self.taskInfo['files'][i] = \
                self.pm.toClient(self.taskInfo['files'][i])

        # Check files:
        if self.isSkippingExistingFiles() and len(self.taskInfo['files']):
            self.checkExistingFiles()

        # Transfer paths in environment:
        for name in self.taskInfo['environment']:
            self.taskInfo['environment'][name] = self.pm.toClient(self.taskInfo['environment'][name])

        # When GUI receives task exec to show files,
        # server sends exec with parsed files.
        for i in range(0, len(self.taskInfo['parsed_files'])):
            self.taskInfo['parsed_files'][i] = \
                self.pm.toClient(self.taskInfo['parsed_files'][i])

        # Initialize parser:
        self.parser = None
        parser = cgruutils.toStr(taskInfo['parser'])
        if len(taskInfo['parser']):
            try:
                mod = __import__('parsers', globals(), locals(), [parser])
                cmd = 'mod.%s.%s()' % (parser, parser)
                self.parser = eval(cmd)
                self.parser.setTaskInfo(taskInfo)
            except:  # TODO: too broad exception clause
                self.parser = None
                print('ERROR: Failed to import parser "%s"' % parser)
                traceback.print_exc(file=sys.stdout)

        if self.verbose and self.log and len(self.log):
            print(self.log)

    def processCommandPattern(self):
        return self.processPattern(
                self.taskInfo['command_block'],
                [self.taskInfo['command_task']],
                self.taskInfo['frame_start'],
                self.taskInfo['frame_finish'])[0]

    def processPattern(self, i_block, i_tasks, i_start, i_finish):
        """ Fill numbers for numeric blocks or combine block and tasks patterns for blocks with tasks
        :param i_block: a string with a block part
        :param i_tasks: an array of strings with a tasks parts for a not numeric blocks
        :retutn: as array combined of stings (1 element in array for a numeric)
        """
        block = cgruutils.toStr(i_block)

        if self.numeric:
            return [afcommon.fillNumbers(block, i_start, i_finish)]

        array = []
        for task in i_tasks:
            if len(task) == 0:
                continue
            task = cgruutils.toStr(task)
            result = block
            if len(result):
                if result.find('@#@') != -1:
                    result = result.replace('@#@', task)
                else:
                    result += task
            else:
                result = task
            array.append(result)

        if len(array) == 0:
             array.append(block)

        return array

    def processFilesPattern(self):
        files = []
        for block_file in self.taskInfo['files_block']:
            frame = self.taskInfo['frame_start']
            while frame <= self.taskInfo['frame_finish']:
                files.extend(self.processPattern(block_file, self.taskInfo['files_task'], frame, frame))
                frame += self.taskInfo['frame_inc']
        return files

    def isSkippingExistingFiles(self):
        return afcommon.checkBlockFlag(self.taskInfo['block_flags'], 'skipexistingfiles')

    def checkExistingFiles(self):
        allFilesExist = True
        log = ''
        for i in range(0, len(self.taskInfo['files'])):
            afile = self.taskInfo['files'][i]
            if len(afile) == 0: continue
            afile = os.path.join(self.taskInfo['wdir'], afile)
            if not os.path.isfile(afile):
                allFilesExist = False
                continue

            # Check files size:
            file_size_min = self.taskInfo['file_size_min']
            file_size_max = self.taskInfo['file_size_max']
            if file_size_min > 0 or file_size_max > 0:
                size = os.path.getsize(afile)
                if file_size_min > 0 and size < file_size_min:
                    allFilesExist = False
                    log += 'File size less than minimum(%d): "%s"\n' % (file_size_min, afile)
                    continue
                if file_size_max > 0 and size > file_size_max:
                    log += 'File size greater than maximum(%d): "%s"\n' % (file_size_max, afile)
                    allFilesExist = False
                    continue

            log += 'File exists: "%s"\n' % afile

        if allFilesExist:
            log += 'Task file(s) exists. Skipping command execution.\n'
            self.taskInfo['command'] = ''

        if len(log):
            if self.log is not None and len(self.log):
                self.log += log
            else:
                self.log = log

    def getWDir(self):
        """Missing DocString

        :return:
        """
        return self.taskInfo['wdir']

    def getCommand(self):
        """Missing DocString

        :return:
        """
        return self.taskInfo['command']

    def getFiles(self):
        """Missing DocString

        :return:
        """
        return self.taskInfo['files']

    def getParsedFiles(self):
        """Missing DocString

        :return:
        """
        # taskInfo does not have parsed files on render,
        # afserver set parsed files parameter on TaskExec for GUIs only,
        # it needed for GUIs only to transfer files paths to view
        if len(self.taskInfo['parsed_files']):
            return self.taskInfo['parsed_files']
        elif self.parser is not None:
            files = self.parser.getFiles()
            for i in range(0, len(files)):
                files[i] = self.pm.toServer(files[i])
            return files
        else:
            return []

    def getEnvironment(self):
        """Missing DocString

        :return:
        """
        return self.taskInfo['environment']

    def getLog(self):
        """
            This string will appear in server task log
        """
        log = ''

        if self.parser is not None:
            parser_log = self.parser.getLog()
            if parser_log is not None and len(parser_log):
                log = 'Parser: ' + parser_log

        if self.log is not None and len(self.log):
            if len(log):
                log += '\n'
            log += 'Service: ' + self.log

        return log

    def applyCmdCapacity(self, command):
        """Missing DocString

        :return:
        """
        command = command.replace(
            self.str_capacity,
            str(self.taskInfo['capacity'])
        )
        print('Capacity coefficient %s applied:' % self.taskInfo['capacity'])
        print(command)
        return command

    def applyCmdHosts(self, command):
        """Missing DocString

        :param command:
        :return:
        """
        hosts = str_hostsprefix
        firsthost = True
        for host in self.taskInfo['hosts']:
            if firsthost:
                firsthost = False
            else:
                hosts += self.str_hostseparator
            hosts += str(host)
        command = command.replace(self.str_hosts, hosts)
        print('Hosts list "%s" applied:' % str(hosts))
        print(command)
        return command

    def hasParser(self):
        return self.parser is not None

    def parse(self, i_args):
        """Missing DocString
        :return:
        """
        if self.parser is None:
            return None

        self.parser.parse(i_args)

        thumb_cmds = self.generateThumbnail(True)
        for cmd in thumb_cmds:
            print('Generating thumbnail "on-the-fly":')
            print(cmd)
            os.system(cmd)

        return self.parser

    def toHTML(self, i_data):
        """ Convert data to HTML.
            Designed for GUIs for escape sequences, errors highlighting.
        :param i_data: input data
        :return: converted data
        """
        if self.parser is None:
            print('Servie.toHTML(): parser is None.')
            return i_data

        return self.parser.toHTML(i_data)

    def checkExitStatus(self, i_status):
        """ This function needed to check task process exit status.
            By default zero is success, any other means some error.
            But some services can have some other good exit status value(s).
        """
        status = False
        if i_status == 0:
            status = True

        if self.verbose:
            msg = 'ERROR'
            if status:
                msg = 'SUCCESS'
            print('service::checkExitStatus: %d %s' % (i_status, msg))

        return status

    def doPost(self):
        """Missing DocString

        :return:
        """
        post_cmds = []

        if not afcommon.checkBlockFlag(self.taskInfo['block_flags'], 'skipthumbnails'):
            post_cmds.extend(self.generateThumbnail(False))

        # post_cmds.extend(['ls -la > ' + self.taskInfo['store_dir'] + '/afile'])

        return post_cmds

    def doPostLimitSec(self):
        return cgruconfig.VARS['af_task_post_limit_sec']

    def generateThumbnail(self, i_onthefly):
        """Missing DocString

        :return:
        """
        cmds = []

        if not os.path.isdir(self.taskInfo['store_dir']):
            return cmds

        files_list = []
        if self.parser is not None:
            if i_onthefly:
                files_list = self.parser.getFilesOnTheFly()
            else:
                files_list = self.parser.getFiles()

        if len(files_list):
            if len(files_list) > 3:
                files_list = [
                    files_list[0],
                    files_list[int(len(files_list) / 2)],
                    files_list[-1]
                ]
        elif len(self.taskInfo['files']) and not i_onthefly:
            for afile in self.taskInfo['files']:
                files_list.append(afile)
            # files_list.append(afile.decode('utf-8'))
        else:
            return cmds

        for image in files_list:
            image = cgruutils.toStr(image)
            if len(image) < 1:
                continue
            image = os.path.join(self.taskInfo['wdir'], image)
            if not os.path.isfile(image):
                continue

            basename, ext = os.path.splitext(os.path.basename(image))
            if len(ext) < 2:
                continue
            ext = ext.lower()[1:]
            if ext not in cgruconfig.VARS['af_thumbnail_extensions']:
                continue

            store_dir = cgruutils.toStr(self.taskInfo['store_dir'])
            thumbnail = os.path.basename(image) + '.jpg'
            thumbnail = store_dir + '/' + thumbnail

            self.taskInfo['image'] = os.path.normpath(image)
            self.taskInfo['thumbnail'] = os.path.normpath(thumbnail)
            self.taskInfo['pre_args'] = ''
            if ext == 'dpx' or ext == 'cin':
                self.taskInfo['pre_args'] = '-set colorspace Log'
            if ext == 'exr':
                self.taskInfo['pre_args'] = '-set colorspace RGB'

            cmd = str(cgruconfig.VARS['af_thumbnail_cmd']) % self.taskInfo
            # print( cmd)
            # cmds.append('echo ' + cmd)
            cmds.append(cmd)

        return cmds

    def checkRenderedFiles(self):
        """Missing DocString
        :return:
        """

        file_size_min = self.taskInfo['file_size_min']
        file_size_max = self.taskInfo['file_size_max']

        for i in range(0, len(self.taskInfo['files'])):
            afile = self.taskInfo['files'][i]
            afile = os.path.join(self.taskInfo['wdir'], afile)
            # print('Checking for "%s" %d-%d' %( afile, file_size_min, file_size_max ))

            if not os.path.isfile(afile):
                self.log = 'File does not exist:\n' + afile
                return False

            if file_size_min > 0 or file_size_max > 0:
                size = os.path.getsize(afile)

                if file_size_min > 0 and size < file_size_min:
                    self.log = 'File size less than minimum (%d < %d):\n%s' % (size, file_size_min, afile)
                    return False

                if file_size_max > 0 and size > file_size_max:
                    self.log = 'File size greater than maximum (%d < %d):\n%s' % (size, file_size_max, afile)
                    return False

        return True
