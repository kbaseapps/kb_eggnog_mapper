# -*- coding: utf-8 -*-
#BEGIN_HEADER
import logging
import os
import re
import subprocess
import sys
import traceback
import uuid
from datetime import datetime
from pprint import pformat

# SDK Utils
from installed_clients.KBaseDataObjectToFileUtilsClient import KBaseDataObjectToFileUtils
from installed_clients.DataFileUtilClient import DataFileUtil as DFUClient
from installed_clients.KBaseReportClient import KBaseReport
from installed_clients.WorkspaceClient import Workspace as workspaceService

# EggnogMapperUtil
from kb_eggnog_mapper.Utils.EggnogMapperUtil import EggnogMapperUtil

#END_HEADER


class kb_eggnog_mapper:
    '''
    Module Name:
    kb_eggnog_mapper

    Module Description:
    A KBase module: kb_eggnog_mapper
    '''

    ######## WARNING FOR GEVENT USERS ####### noqa
    # Since asynchronous IO can lead to methods - even the same method -
    # interrupting each other, you must be *very* careful when using global
    # state. A method could easily clobber the state set by another while
    # the latter method is running.
    ######################################### noqa
    VERSION = "0.0.1"
    GIT_URL = "https://github.com/kbaseapps/kb_eggnog_mapper"
    GIT_COMMIT_HASH = "e80aadc84a9663e2421ce90545bc7e0939b4252f"

    #BEGIN_CLASS_HEADER
    #END_CLASS_HEADER

    # config contains contents of config file in a hash or None if it couldn't
    # be found
    def __init__(self, config):
        #BEGIN_CONSTRUCTOR
        self.config = config
        self.workspaceURL = config['workspace-url']
        self.shockURL = config['shock-url']
        self.handleURL = config['handle-service-url']
        self.serviceWizardURL = config['srv-wiz-url']
        self.callbackURL = os.environ.get('SDK_CALLBACK_URL')
        if self.callbackURL == None:
            raise ValueError ("SDK_CALLBACK_URL not set in environment")

        self.EMAPPER_VER = config['emapper_ver']
        
        self.scratch = os.path.abspath(config['scratch'])
        if self.scratch == None:
            self.scratch = os.path.join('/kb','module','local_scratch')
        if not os.path.exists(self.scratch):
            os.makedirs(self.scratch)

        logging.basicConfig(format='%(created)s %(levelname)s: %(message)s',
                            level=logging.INFO)
        #END_CONSTRUCTOR
        pass


    def run_eggnog_mapper(self, ctx, params):
        """
        :param params: instance of type "EggnogMapper_Input"
           (run_eggnog_mapper() ** ** run eggnog-mapper on a collection of
           genomes and/or AMAs) -> structure: parameter "workspace_name" of
           type "workspace_name" (** Common types), parameter "workspace_id"
           of type "workspace_id", parameter "target_refs" of type
           "data_obj_ref", parameter "novel_fams" of type "bool", parameter
           "genome_disp_name_config" of String
        :returns: instance of type "ReportResults" (** Report Results) ->
           structure: parameter "report_name" of String, parameter
           "report_ref" of String
        """
        # ctx is the context object
        # return variables are: output
        #BEGIN run_eggnog_mapper
        search_tool_name = 'eggnog_mapper_v'+self.EMAPPER_VER
        emu = EggnogMapperUtil(self.config, ctx)
        output = emu.run_EMAPPER_App (search_tool_name, params)
        #END run_eggnog_mapper

        # At some point might do deeper type checking...
        if not isinstance(output, dict):
            raise ValueError('Method run_eggnog_mapper return value ' +
                             'output is not type dict as required.')
        # return the results
        return [output]
    def status(self, ctx):
        #BEGIN_STATUS
        returnVal = {'state': "OK",
                     'message': "",
                     'version': self.VERSION,
                     'git_url': self.GIT_URL,
                     'git_commit_hash': self.GIT_COMMIT_HASH}
        #END_STATUS
        return [returnVal]
