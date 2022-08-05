# -*- coding: utf-8 -*-
import os
import re
import subprocess
import sys
import gzip
import traceback
import uuid
from datetime import datetime
from pprint import pformat

# SDK Utils
from installed_clients.KBaseDataObjectToFileUtilsClient import KBaseDataObjectToFileUtils
from installed_clients.DataFileUtilClient import DataFileUtil as DFUClient
from installed_clients.KBaseReportClient import KBaseReport
from installed_clients.WorkspaceClient import Workspace as workspaceService


###############################################################################
# EggnogMapperUtil: methods to support Apps in kb_eggnog_mapper KBase module
###############################################################################

class EggnogMapperUtil:

    ######## WARNING FOR GEVENT USERS ####### noqa
    # Since asynchronous IO can lead to methods - even the same method -
    # interrupting each other, you must be *very* careful when using global
    # state. A method could easily clobber the state set by another while
    # the latter method is running.
    ######################################### noqa
    VERSION = "0.0.1"
    GIT_URL = "https://github.com/kbaseapps/kb_eggnog_mapper.git"
    GIT_COMMIT_HASH = "0722ff0b7d723e654ef9ebe470e2b515d13671bc"

    #BEGIN_CLASS_HEADER

    # paths

    # timestamp
    def now_ISO(self):
        now_timestamp = datetime.now()
        now_secs_from_epoch = (now_timestamp - datetime(1970,1,1)).total_seconds()
        now_timestamp_in_iso = datetime.fromtimestamp(int(now_secs_from_epoch)).strftime('%Y-%m-%d_%T')
        return now_timestamp_in_iso

    # message logging
    def log(self, target, message):
        message = '['+self.now_ISO()+'] '+message
        if target is not None:
            target.append(message)
        print(message)
        sys.stdout.flush()


    # config contains contents of config file in a hash or None if it couldn't
    # be found
    def __init__(self, config, ctx):
        #BEGIN_CONSTRUCTOR
        self.config = config
        self.ctx = ctx

        self.workspaceURL = config['workspace-url']
        self.shockURL = config['shock-url']
        self.handleURL = config['handle-service-url']
        self.serviceWizardURL = config['srv-wiz-url']
        self.callbackURL = os.environ.get('SDK_CALLBACK_URL')
        if self.callbackURL is None:
            raise ValueError ("SDK_CALLBACK_URL not set in environment")

        self.REFDATA_VER = config['eggnogdb_ver']
        self.REFDATA_DIR = "/data/eggnogdb/"+self.REFDATA_VER
        self.EMAPPER_BIN = "/kb/module/eggnog-mapper/emapper.py"
        self.cpus = config['cpus']

        self.scratch = os.path.abspath(config['scratch'])
        if self.scratch is None:
            self.scratch = os.path.join('/kb','module','local_scratch')
        if not os.path.exists(self.scratch):
            os.makedirs(self.scratch)

        try:
            self.wsClient = workspaceService(self.workspaceURL, token=self.ctx['token'])
        except:
            raise ValueError ("Failed to connect to workspace service")
        try:
            REPORT_SERVICE_VER = 'release'
            self.reportClient = KBaseReport(self.callbackURL, token=self.ctx['token'], service_ver=REPORT_SERVICE_VER)
        except:
            raise ValueError ("Failed to instantiate KBaseReport client")
        try:
            #DOTFU_SERVICE_VER = 'release'
            DOTFU_SERVICE_VER = 'beta'  # DEBUG
            self.DOTFU = KBaseDataObjectToFileUtils (url=self.callbackURL, token=self.ctx['token'], service_ver=DOTFU_SERVICE_VER)
        except:
            raise ValueError ("Failed to instantiate DataObjectToFileUtils client")

        self.genome_id_feature_id_delim = '.f:'


        #END_CONSTRUCTOR
        pass


    # _instantiate_provenance()
    #
    def _instantiate_provenance(self, 
                                method_name=None,
                                input_obj_refs=None):
        service = 'kb_eggnog_mapper'

        provenance = [{}]
        if 'provenance' in self.ctx:
            provenance = self.ctx['provenance']
        # add additional info to provenance here, in this case the input data object reference
        provenance[0]['input_ws_objects'] = []
        if input_obj_refs:
            for input_ref in input_obj_refs:
                if '/' in input_ref:
                    provenance[0]['input_ws_objects'].append(input_ref)
        provenance[0]['service'] = service
        provenance[0]['method'] = method_name

        return provenance


    #### Sequence Validation
    ##
    def validateSeq (self, seq_type, sequence_str, header_id):
        console = []
        PROT_pattern = re.compile("^[acdefghiklmnpqrstvwyACDEFGHIKLMNPQRSTVWYxX ]+$")
        NUC_pattern  = re.compile("^[acgtuACGTUnryNRY ]+$")   

        if header_id is None:  header_id = 'N/A'

        if seq_type.startswith('NUC'):
            if not NUC_pattern.match(sequence_str):
                self.log(console,"Not finding NUCLEOTIDE sequence for ID "+str(header_id)+" sequence: "+str(sequence_str))
                return False
        elif seq_type.startswith('PROT'): 
            if NUC_pattern.match(sequence_str):
                self.log(console,"Finding NUCLEOTIDE instead of PROTEIN sequence for ID "+str(header_id)+" sequence: "+str(sequence_str))
                return False
            elif not PROT_pattern.match(sequence_str):
                self.log(console,"Not finding PROTEIN sequence for ID "+str(header_id)+" sequence: "+str(sequence_str))
                return False

        return True


    #### Validate App input params
    ##
    def validate_EMAPPER_app_params (self, params):

        # do some basic checks
        if not params.get('workspace_name'):
            raise ValueError('workspace_name parameter is required')
        if not params.get('target_refs'):
            raise ValueError('targets_refs is required')
        if int(params.get('novel_fams',"-1")) == -1:
            raise ValueError('novel_fams is required')
        #if 'genome_disp_name_config' not in params:
        #    raise ValueError('genome_disp_name_config parameter is required')

        return True


    #### Get the input target object
    ##
    def write_target_obj_to_file (self, params, target_ref):
        console = []
        invalid_msgs = []
        seq_type = 'PRO'
        appropriate_sequence_found_in_target_input = False
        target_feature_info = { 'feature_ids': None,
                                'feature_ids_by_genome_ref': None,
                                'feature_ids_by_genome_id': None,
                                'feature_id_to_function': None,
                                'genome_ref_to_sci_name': None,
                                'genome_ref_to_obj_name': None,
                                'genome_id_to_genome_ref': None
        }

        # defaults
        if not params.get('write_off_code_prot_seq'):
            params['write_off_code_prot_seq'] = 1
        params['write_off_code_prot_seq'] = int(params['write_off_code_prot_seq'])
        
        try:
            #objects = ws.get_objects([{'ref': input_target_ref}])
            objects = self.wsClient.get_objects2({'objects':[{'ref': target_ref}]})['data']
            target_data = objects[0]['data']
            info = objects[0]['info']
            target_name = str(info[1])
            target_type_name = info[2].split('.')[1].split('-')[0]
        except Exception as e:
            raise ValueError('Unable to fetch target object '+target_ref+' from workspace: ' + str(e))
            #to get the full stack trace: traceback.format_exc()
            
        # Genome
        #
        if target_type_name == 'Genome':
            target_fasta_file_dir = self.scratch
            target_fasta_file = target_name+".fasta"

            # DEBUG
            #beg_time = (datetime.utcnow() - datetime.utcfromtimestamp(0)).total_seconds()
            GenomeToFASTA_params = {
                'genome_ref':          target_ref,
                'file':                target_fasta_file,
                'dir':                 target_fasta_file_dir,
                'console':             console,
                'invalid_msgs':        invalid_msgs,
                'residue_type':        seq_type,
                'feature_type':        'ALL',
                'record_id_pattern':   '%%genome_ref%%'+self.genome_id_feature_id_delim+'%%feature_id%%',
                'record_desc_pattern': '[%%genome_id%%]',
                'case':                'upper',
                'linewrap':            50,
                'id_len_limit':        49,
                'write_off_code_prot_seq': params['write_off_code_prot_seq']
                }

            GenomeToFASTA_retVal = self.DOTFU.GenomeToFASTA (GenomeToFASTA_params)
            target_fasta_file_path = GenomeToFASTA_retVal['fasta_file_path']
            target_feature_info['short_id_to_rec_id'] = GenomeToFASTA_retVal['short_id_to_rec_id']
            target_feature_info['feature_ids'] = GenomeToFASTA_retVal['feature_ids']
            if len(target_feature_info['feature_ids']) > 0:
                appropriate_sequence_found_in_target_input = True
            target_feature_info['feature_id_to_function'] = GenomeToFASTA_retVal['feature_id_to_function']
            target_feature_info['genome_ref_to_sci_name'] = GenomeToFASTA_retVal['genome_ref_to_sci_name']
            target_feature_info['genome_ref_to_obj_name'] = GenomeToFASTA_retVal['genome_ref_to_obj_name']
            

            # DEBUG
            #end_time = (datetime.utcnow() - datetime.utcfromtimestamp(0)).total_seconds()
            #self.log(console, "Genome2Fasta() took "+str(end_time-beg_time)+" secs")


        # GenomeSet
        #
        elif target_type_name == 'GenomeSet':
            target_genomeSet = target_data
            target_fasta_file_dir = self.scratch
            target_fasta_file = target_name+".fasta"

            # DEBUG
            #beg_time = (datetime.utcnow() - datetime.utcfromtimestamp(0)).total_seconds()
            GenomeSetToFASTA_params = {
                'genomeSet_ref':       target_ref,
                'file':                target_fasta_file,
                'dir':                 target_fasta_file_dir,
                'console':             console,
                'invalid_msgs':        invalid_msgs,
                'residue_type':        seq_type,
                'feature_type':        'ALL',
                'record_id_pattern':   '%%genome_ref%%'+self.genome_id_feature_id_delim+'%%feature_id%%',
                'record_desc_pattern': '[%%genome_ref%%]',
                'case':                'upper',
                'linewrap':            50,
                'id_len_limit':        49,
                'write_off_code_prot_seq': params['write_off_code_prot_seq'],
                'merge_fasta_files':   'TRUE'
                }

            GenomeSetToFASTA_retVal = self.DOTFU.GenomeSetToFASTA (GenomeSetToFASTA_params)
            target_fasta_file_path = GenomeSetToFASTA_retVal['fasta_file_path_list'][0]
            target_feature_info['short_id_to_rec_id'] = GenomeSetToFASTA_retVal['short_id_to_rec_id']
            target_feature_info['feature_ids_by_genome_id'] = GenomeSetToFASTA_retVal['feature_ids_by_genome_id']
            if len(list(target_feature_info['feature_ids_by_genome_id'].keys())) > 0:
                appropriate_sequence_found_in_target_input = True
            target_feature_info['feature_id_to_function'] = GenomeSetToFASTA_retVal['feature_id_to_function']
            target_feature_info['genome_ref_to_sci_name'] = GenomeSetToFASTA_retVal['genome_ref_to_sci_name']
            target_feature_info['genome_ref_to_obj_name'] = GenomeSetToFASTA_retVal['genome_ref_to_obj_name']

            target_feature_info['genome_id_to_genome_ref'] = dict()
            for genome_id in target_genomeSet['elements'].keys():
                genome_ref = target_genomeSet['elements'][genome_id]['ref']
                target_feature_info['genome_id_to_genome_ref'][genome_id] = genome_ref

            # DEBUG
            #end_time = (datetime.utcnow() - datetime.utcfromtimestamp(0)).total_seconds()
            #self.log(console, "GenomeSetToFasta() took "+str(end_time-beg_time)+" secs")


        # SpeciesTree
        #
        elif target_type_name == 'Tree':
            target_speciesTree = target_data
            target_fasta_file_dir = self.scratch
            target_fasta_file = target_name+".fasta"

            # DEBUG
            #beg_time = (datetime.utcnow() - datetime.utcfromtimestamp(0)).total_seconds()
            SpeciesTreeToFASTA_params = {
                'tree_ref':            target_ref,
                'file':                target_fasta_file,
                'dir':                 target_fasta_file_dir,
                'console':             console,
                'invalid_msgs':        invalid_msgs,
                'residue_type':        seq_type,
                'feature_type':        'ALL',
                'record_id_pattern':   '%%genome_ref%%'+self.genome_id_feature_id_delim+'%%feature_id%%',
                'record_desc_pattern': '[%%genome_ref%%]',
                'case':                'upper',
                'linewrap':            50,
                'id_len_limit':        49,
                'write_off_code_prot_seq': params['write_off_code_prot_seq'],
                'merge_fasta_files':   'TRUE'
                }

            SpeciesTreeToFASTA_retVal = self.DOTFU.SpeciesTreeToFASTA (SpeciesTreeToFASTA_params)
            target_fasta_file_path = SpeciesTreeToFASTA_retVal['fasta_file_path_list'][0]
            target_feature_info['short_id_to_rec_id'] = SpeciesTreeToFASTA_retVal['short_id_to_rec_id']
            target_feature_info['feature_ids_by_genome_id'] = SpeciesTreeToFASTA_retVal['feature_ids_by_genome_id']
            if len(list(target_feature_info['feature_ids_by_genome_id'].keys())) > 0:
                appropriate_sequence_found_in_target_input = True
            target_feature_info['feature_id_to_function'] = SpeciesTreeToFASTA_retVal['feature_id_to_function']
            target_feature_info['genome_ref_to_sci_name'] = SpeciesTreeToFASTA_retVal['genome_ref_to_sci_name']
            target_feature_info['genome_ref_to_obj_name'] = SpeciesTreeToFASTA_retVal['genome_ref_to_obj_name']

            target_feature_info['genome_id_to_genome_ref'] = dict()
            for genome_id in target_speciesTree['ws_refs'].keys():
                genome_ref = target_speciesTree['ws_refs'][genome_id]['g'][0]
                target_feature_info['genome_id_to_genome_ref'][genome_id] = genome_ref

            # DEBUG
            #end_time = (datetime.utcnow() - datetime.utcfromtimestamp(0)).total_seconds()
            #self.log(console, "SpeciesTreeToFasta() took "+str(end_time-beg_time)+" secs")


        # AnnotatedMetagenomeAssembly
        #
        elif target_type_name == 'AnnotatedMetagenomeAssembly':
            target_fasta_file_dir = self.scratch
            target_fasta_file = target_name+".fasta"

            # DEBUG
            #beg_time = (datetime.utcnow() - datetime.utcfromtimestamp(0)).total_seconds()
            AnnotatedMetagenomeAssemblyToFASTA_params = {
                'ama_ref':             target_ref,
                'file':                target_fasta_file,
                'dir':                 target_fasta_file_dir,
                'console':             console,
                'invalid_msgs':        invalid_msgs,
                'residue_type':        seq_type,
                'feature_type':        'ALL',
                'record_id_pattern':   '%%ama_ref%%'+self.genome_id_feature_id_delim+'%%feature_id%%',
                'record_desc_pattern': '[%%genome_id%%]',
                'case':                'upper',
                'linewrap':            50,
                'id_len_limit':        49,
                'write_off_code_prot_seq': params['write_off_code_prot_seq']
                }

            AnnotatedMetagenomeAssemblyToFASTA_retVal = self.DOTFU.AnnotatedMetagenomeAssemblyToFASTA (AnnotatedMetagenomeAssemblyToFASTA_params)
            target_fasta_file_path = AnnotatedMetagenomeAssemblyToFASTA_retVal['fasta_file_path']
            target_feature_info['short_id_to_rec_id'] = AnnotatedMetagenomeAssemblyToFASTA_retVal['short_id_to_rec_id']
            target_feature_info['feature_ids'] = AnnotatedMetagenomeAssemblyToFASTA_retVal['feature_ids']
            if len(target_feature_info['feature_ids']) > 0:
                appropriate_sequence_found_in_target_input = True
            target_feature_info['feature_id_to_function'] = AnnotatedMetagenomeAssemblyToFASTA_retVal['feature_id_to_function']
            target_feature_info['ama_ref_to_obj_name'] = AnnotatedMetagenomeAssemblyToFASTA_retVal['ama_ref_to_obj_name']

            # DEBUG
            #with open (target_fasta_file_path, 'r') as fasta_handle:
            #    for fasta_line in fasta_handle.readlines():
            #        print ("FASTA_LINE: '"+fasta_line)
            

            # DEBUG
            #end_time = (datetime.utcnow() - datetime.utcfromtimestamp(0)).total_seconds()
            #self.log(console, "Genome2Fasta() took "+str(end_time-beg_time)+" secs")


        # Missing proper input_target_type
        #
        else:
            raise ValueError('Cannot yet handle target type of: '+target_type_name)


        return ({ 'target_name': target_name,
                  'target_type_name': target_type_name,
                  'target_fasta_file_path': target_fasta_file_path,
                  'appropriate_sequence_found_in_target_input': appropriate_sequence_found_in_target_input,
                  'invalid_msgs': invalid_msgs,
                  'target_feature_info': target_feature_info
              })


    # input data failed validation.  Need to return
    #
    def save_error_report_with_invalid_msgs (self, invalid_msgs, target_refs, method_name):
        console = []

        # build output report object
        #
        self.log(console,"BUILDING REPORT")  # DEBUG
        report += "FAILURE:\n\n"+"\n".join(invalid_msgs)+"\n"
        reportObj = {
            'objects_created':[],
            'text_message':report
        }

        reportName = 'eggnog_mapper_report_'+str(uuid.uuid4())
        report_obj_info = self.wsClient.save_objects({
            #'id':info[6],
            'workspace':params['workspace_name'],
            'objects':[
                {
                    'type':'KBaseReport.Report',
                    'data':reportObj,
                    'name':reportName,
                    'meta':{},
                    'hidden':1,
                    'provenance': self._instantiate_provenance(method_name = method_name,
                                                               input_obj_refs = target_refs)
                }
            ]
        })[0]

        error_report_info = { 'name': reportName,
                              'ref': str(report_obj_info[6]) + '/' + str(report_obj_info[0]) + '/' + str(report_obj_info[4])
                          }
        return error_report_info

    
    #### merge_and_format_protein_fastas()
    ##
    def merge_and_format_protein_fastas (self, ref_list, target_fasta_file_paths):
        console = []
        merged_target_fasta_file_paths = []

        # TODO: MERGE HERE, check header format too

        
        return merged_target_fasta_file_paths


    # _check_EMAPPER_input_ready()
    #
    def _check_EMAPPER_input_ready (self, EMAPPER_bin, target_fasta_file_path):
        console = []
        ENM_ready = True

        # check for necessary files
        if not os.path.isfile(EMAPPER_bin):
            self.log(console, "no such file '"+EMAPPER_bin+"'")
            ENM_ready = False

        if not os.path.isfile(target_fasta_file_path):
            self.log(console, "no such file '"+target_fasta_file_path+"'")
            ENM_ready = False
        if not os.path.getsize(target_fasta_file_path) > 0:
            self.log(console, "empty file '"+target_fasta_file_path+"'")
            ENM_ready = False

        for db in ['eggnog.db', 'eggnog_proteins.dmnd', 'novel_fams.dmnd', 'eggnog.taxa.db', 'eggnog.taxa.db.traverse.pkl']:
            db_path = os.path.join(self.REFDATA_DIR, db)
            if not os.path.isfile(db_path) or not os.path.getsize(db_path) > 0:
                self.log(console, "no such file '"+db_path+"'")
                ENM_ready = False

        return ENM_ready


    # _set_output_path()
    #
    #def _set_output_path (self, chunk, mode):
    def _set_output_path (self, target_fasta_file_path, mode):
        timestamp = int((datetime.utcnow() - datetime.utcfromtimestamp(0)).total_seconds()*1000)
        output_dir = os.path.join(self.scratch,'output.'+str(timestamp))
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        base_filename = re.sub(r'^.*\/', '', target_fasta_file_path)
        base_filename = re.sub(r'\.fasta$', '', base_filename)
        base_filename = re.sub(r'\.faa$', '', base_filename)
            
        #return os.path.join(output_dir, 'chunk_'+str(chunk)+'-'+mode)
        db = 'eggnog5'
        if mode == 'novel_fams':
            db = 'novel_fams'
        return os.path.join(output_dir, base_filename+'-'+db)


    # _build_EMAPPER_cmd()
    #
    def _build_EMAPPER_cmd (self, 
                            target_fasta_file_path=None,
                            output_annot_base_path=None,
                            search_novel_fams=None,
                            cpus=None):

        # set EMAPPER bin
        EMAPPER_bin = self.EMAPPER_BIN

        # check if ready
        if not self._check_EMAPPER_input_ready (EMAPPER_bin, target_fasta_file_path):
            raise ValueError ("Not ready to run EMAPPER")

        # NEW SYNTAX: emapper.py --cpu <cpus> --data_dir <data_dir> -i <targets_file> --output <output_path> -m <mode(diamond/novel_fams)>
        emapper_cmd = [EMAPPER_bin]
        emapper_cmd.append('--cpu')
        emapper_cmd.append(str(cpus))
        emapper_cmd.append('--data_dir')
        emapper_cmd.append(self.REFDATA_DIR)
        emapper_cmd.append('-i')
        emapper_cmd.append(target_fasta_file_path)
        emapper_cmd.append('--output')
        emapper_cmd.append(output_annot_base_path)
        emapper_cmd.append('-m')
        if search_novel_fams:
            emapper_cmd.append('novel_fams')
        else:
            emapper_cmd.append('diamond')

        return emapper_cmd


    # _exec_EMAPPER()
    #
    def _exec_EMAPPER (self, emapper_cmd):
        console = []

        # Run EMAPPER, capture output as it happens
        self.log(console, 'RUNNING EMAPPER:')
        self.log(console, ' '.join(emapper_cmd))
        self.log(console, '--------------------------------------')

        p = subprocess.Popen(emapper_cmd, \
                             cwd = self.scratch, \
                             stdout = subprocess.PIPE, \
                             stderr = subprocess.STDOUT, \
                             shell = False)

        while True:
            line = p.stdout.readline().decode()
            if not line: break
            self.log(console, line.replace('\n', ''))

        p.stdout.close()
        p.wait()
        self.log(console, 'return code: ' + str(p.returncode))
        if p.returncode != 0:
            return 'Error running EMAPPER, return code: '+str(p.returncode) + '\n\n'+ '\n'.join(console)

        return 'Success'


    # _unshorten_feature_IDs()
    #
    def _unshorten_feature_IDs (self, annot_path, short_ID_mapping):
        buf = []
        with open(annot_path, 'r') as annot_h:
            for annot_line in annot_h:
                if not annot_line.startswith('#'):
                    fid = annot_line.split()[0]
                    if fid in short_ID_mapping:
                        new_fid = short_ID_mapping[fid]
                        annot_line = re.sub(fid, new_fid, annot_line)
                buf.append(annot_line)
        with open(annot_path, 'w') as annot_h:
            annot_h.writelines(buf)
        buf = []

        return annot_path
    

    #### run_EMAPPER(): actual invocation
    ##
    def run_EMAPPER (self, 
                     target_fasta_file_path = None,
                     target_feature_info = None,
                     #chunk = None,
                     novel_fams = None, 
                     cpus = None):
        console = []
        annot_paths = []
        bulk_save_info = []
        
        run_modes = ['diamond']
        #run_modes = []  # DEBUG
        if novel_fams and int(novel_fams) == 1:
            run_modes.append('novel_fams')

        for mode in run_modes:
                    
            # set the output path
            #output_annot_base_path = self._set_output_path (chunk, mode)
            output_annot_base_path = self._set_output_path (target_fasta_file_path, mode)

            # construct the EMAPPER command
            search_novel_fams = False
            if mode == 'novel_fams':
                search_novel_fams = True
            emapper_cmd = self._build_EMAPPER_cmd (
                target_fasta_file_path = target_fasta_file_path,
                output_annot_base_path = output_annot_base_path,
                search_novel_fams = search_novel_fams,
                cpus = cpus)

            # execute EMAPPER
            EMAPPER_exec_return_msg = self._exec_EMAPPER (emapper_cmd)
            if EMAPPER_exec_return_msg != 'Success':
                self.log(console, EMAPPER_exec_return_msg)
                raise ValueError ("FAILURE executing EMAPPER with command: \n\n"+"\n".join(emapper_cmd))

            # TODO:
            # modify genome and AMA objects with func annot
            #
            
            # upload EMAPPER output
            dfu = DFUClient(self.callbackURL)
            for annot_type in ['annotations', 'hits', 'seed_orthologs']:
                annot_path = output_annot_base_path+'.emapper.'+annot_type
                if os.path.exists(annot_path) and os.path.getsize(annot_path) > 0:

                    # fix short IDs
                    annot_path = self._unshorten_feature_IDs (annot_path, target_feature_info['short_id_to_rec_id'])
                    
                    # compress
                    with open(annot_path, 'rb') as f_in, \
                         gzip.open(annot_path+'.gz', 'wb') as f_out:
                        f_out.writelines(f_in)

                    # capture filename and upload to shock
                    annot_paths.append(annot_path)
                    try:
                        bulk_save_info.append(dfu.file_to_shock({'file_path': annot_path+'.gz',
                                                                 # DEBUG
                                                                 # 'make_handle': 0,
                                                                 # 'pack': 'zip'})
                                                                 'make_handle': 0}))
                    except:
                        raise ValueError ('error uploading '+annot_path+'.gz'+' file')

        # return output
        return {
            'annot_paths': annot_paths,
            'bulk_save_info': bulk_save_info
        }


    #### build output report
    ##
    def build_EMAPPER_report (self, 
                              search_tool_name = None,
                              params = None,
                              targets_name = None,
                              targets_type_name = None,
                              annot_paths = None,
                              bulk_save_infos = None,
                              objects_created = None):

        # init
        method_name = search_tool_name
        console = []
        invalid_msgs = []
        report = ''
        self.log(console,"BUILDING REPORT")  # DEBUG

        target_refs = params['target_refs']

        # create report object
        reportName = 'blast_report_'+str(uuid.uuid4())
        reportObj = {'objects_created': [],
                     'message': '',
                     'direct_html_link_index': None,
                     'file_links': [],
                     'html_links': [],
                     'workspace_name': params['workspace_name'],
                     'report_object_name': reportName
        }
        reportObj['direct_html_link_index'] = 0
        reportObj['file_links'] = []
        for target_ref in target_refs:
            target_name = targets_name[target_ref]
            annot_path_list = annot_paths[target_ref]
            bulk_save_info_list = bulk_save_infos[target_ref]

            for file_i,bulk_save_info in enumerate(bulk_save_info_list):
                annot_path = annot_path_list[file_i]
                annot_path = re.sub (r'.*\/', '', annot_path)
                reportObj['file_links'].append({'shock_id': bulk_save_info['shock_id'],
                                                'name': annot_path+'.gz',
                                                'label': annot_path+'.gz'})

        # complete report
        reportObj['objects_created'] = objects_created
        
        ##reportObj['message'] = report

        # save report object
        report_info = self.reportClient.create_extended_report(reportObj)

        return report_info


    #### run_EMAPPER_App(): top-level method
    ##
    def run_EMAPPER_App (self, search_tool_name, params):
        console = []
        invalid_msgs = []
        method_name = search_tool_name
        self.log(console,'Running '+search_tool_name+' with params=')
        self.log(console, "\n"+pformat(params))
        report = ''
        
        #### Validate App input params
        #
        if not self.validate_EMAPPER_app_params (params):
            raise ValueError('App input validation failed in validate_EMAPPER_app_params() for App ' + method_name)

        # Get input obj refs
        #
        target_refs = params.get('target_refs',[])

        # Write target objs to fasta file
        #
        targets_name = dict()
        targets_type_name = dict()
        targets_fasta_file_path = dict()
        appropriate_sequence_found_in_target_inputs = dict()
        targets_feature_info = dict()
        for target_ref in target_refs:
            write_target_obj_to_file_result = self.write_target_obj_to_file (params, target_ref)
            targets_name[target_ref] = write_target_obj_to_file_result['target_name']
            targets_type_name[target_ref] = write_target_obj_to_file_result['target_type_name']
            targets_fasta_file_path[target_ref] = write_target_obj_to_file_result['target_fasta_file_path']
            appropriate_sequence_found_in_target_inputs[target_ref] = write_target_obj_to_file_result['appropriate_sequence_found_in_target_input']
            invalid_msgs.extend(write_target_obj_to_file_result['invalid_msgs'])

            targets_feature_info[target_ref] = write_target_obj_to_file_result['target_feature_info']


        # check for failed input file creation
        #
        for target_ref in target_refs:
            if not appropriate_sequence_found_in_target_inputs[target_ref]:
                self.log(invalid_msgs,"no "+t_seq_type+" sequences found in '"+target_name+"'")

        if len(invalid_msgs) > 0:
            error_report_info = self.save_error_report_with_invalid_msgs (invalid_msgs, target_refs, method_name)
            returnVal = { 'report_name': report_info['name'],
                          'report_ref': report_info['ref']
                      }        
            return [returnVal]


        # TODO:
        # MERGE FASTAS
        # HERE


        #### Run EMAPPER
        ##
        annot_paths = dict()
        bulk_save_infos = dict()
        for target_ref in target_refs:

            EMAPPER_output_results = self.run_EMAPPER (
                target_fasta_file_path = targets_fasta_file_path[target_ref],
                target_feature_info = targets_feature_info[target_ref],
                #chunk = '0000-9999',
                novel_fams = params['novel_fams'],
                cpus = self.cpus
            )
            annot_paths[target_ref] = EMAPPER_output_results['annot_paths']
            bulk_save_infos[target_ref] = EMAPPER_output_results['bulk_save_info']


        # TODO:
        # MODIFY GENOME AND AMA OBJECTS WITH UPDATED ANNOTATIONS
        # HERE
        objects_created = []
        
            
        # build output report object
        #
        report_info = self.build_EMAPPER_report (search_tool_name = search_tool_name,
                                                 params = params,
                                                 targets_name = targets_name,
                                                 targets_type_name = targets_type_name,
                                                 annot_paths = annot_paths,
                                                 bulk_save_infos = bulk_save_infos,
                                                 objects_created = objects_created)

        #report_info = dict()
        #report_info['name'] = 'FOO'
        #report_info['ref'] = '3/2/1'

        # return
        #
        self.log(console,search_tool_name+" DONE")
        returnVal = { 'report_name': report_info['name'],
                      'report_ref': report_info['ref']
                      }
        return returnVal
