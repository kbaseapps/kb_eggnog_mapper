# -*- coding: utf-8 -*-
#BEGIN_HEADER
import logging
import os

from installed_clients.KBaseReportClient import KBaseReport
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
    GIT_COMMIT_HASH = "c481b89ce18aa70825f6b7b558ec6c24ff3bf603"

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
