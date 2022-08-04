# -*- coding: utf-8 -*-
#BEGIN_HEADER
import logging
import os

from installed_clients.KBaseReportClient import KBaseReport
#END_HEADER


class kb_genetree:
    '''
    Module Name:
    kb_genetree

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
    GIT_COMMIT_HASH = "02195ab7da98168eb60695eeaf0d2021e5b3bffa"

    #BEGIN_CLASS_HEADER
    #END_CLASS_HEADER

    # config contains contents of config file in a hash or None if it couldn't
    # be found
    def __init__(self, config):
        #BEGIN_CONSTRUCTOR
        self.callback_url = os.environ['SDK_CALLBACK_URL']
        self.shared_folder = config['scratch']
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
           of type "workspace_id", parameter "input_targets_ref" of type
           "data_obj_ref", parameter "novel_fams" of type "bool", parameter
           "genome_disp_name_config" of String
        :returns: instance of type "ReportResults" (** Report Results) ->
           structure: parameter "report_name" of String, parameter
           "report_ref" of String
        """
        # ctx is the context object
        # return variables are: output
        #BEGIN run_eggnog_mapper
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
