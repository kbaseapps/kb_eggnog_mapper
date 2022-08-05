# -*- coding: utf-8 -*-
import os
import time
import json
import shutil
from pprint import pprint
import unittest
from configparser import ConfigParser
from os import environ


from kb_eggnog_mapper.kb_eggnog_mapperImpl import kb_eggnog_mapper
from kb_eggnog_mapper.kb_eggnog_mapperServer import MethodContext
from kb_eggnog_mapper.authclient import KBaseAuth as _KBaseAuth

from installed_clients.WorkspaceClient import Workspace
from installed_clients.GenomeFileUtilClient import GenomeFileUtil
from installed_clients.DataFileUtilClient import DataFileUtil


class kb_eggnog_mapperTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        token = os.environ.get('KB_AUTH_TOKEN', None)
        config_file = os.environ.get('KB_DEPLOYMENT_CONFIG', None)
        cls.cfg = {}
        config = ConfigParser()
        config.read(config_file)
        for nameval in config.items('kb_eggnog_mapper'):
            cls.cfg[nameval[0]] = nameval[1]
        # Getting username from Auth profile for token
        authServiceUrl = cls.cfg['auth-service-url']
        auth_client = _KBaseAuth(authServiceUrl)
        user_id = auth_client.get_user(token)
        # WARNING: don't call any logging methods on the context object,
        # it'll result in a NoneType error
        cls.ctx = MethodContext(None)
        cls.ctx.update({'token': token,
                        'user_id': user_id,
                        'provenance': [
                            {'service': 'kb_eggnog_mapper',
                             'method': 'please_never_use_it_in_production',
                             'method_params': []
                             }],
                        'authenticated': 1})
        cls.wsURL = cls.cfg['workspace-url']
        cls.callback_url = os.environ['SDK_CALLBACK_URL']
        cls.wsClient = Workspace(cls.wsURL)
        cls.dfuClient = DataFileUtil(cls.callback_url)
        cls.serviceImpl = kb_eggnog_mapper(cls.cfg)
        cls.scratch = cls.cfg['scratch']
        suffix = int(time.time() * 1000)
        cls.wsName = "test_eggnog_mapper_" + str(suffix)
        ret = cls.wsClient.create_workspace({'workspace': cls.wsName})  # noqa

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'wsName'):
            cls.wsClient.delete_workspace({'workspace': cls.wsName})
            print('Test workspace was deleted')

    def getWsClient(self):
        return self.__class__.wsClient

    def getWsName(self):
        if hasattr(self.__class__, 'wsName'):
            return self.__class__.wsName
        suffix = int(time.time() * 1000)
        wsName = "test_kb_blast_" + str(suffix)
        ret = self.getWsClient().create_workspace({'workspace': wsName})  # noqa
        self.__class__.wsName = wsName
        return wsName

    def getImpl(self):
        return self.__class__.serviceImpl

    def getContext(self):
        return self.__class__.ctx

    def _print_test_name (self, test_name):
        print ("\n"+('='*(10+len(test_name))))
        print ("RUNNING "+test_name+"()")
        print (('='*(10+len(test_name)))+"\n")
        return
    
    # get obj_ref in form D/D/D
    def get_obj_ref_from_obj_info (self, obj_info):
        [OBJID_I, NAME_I, TYPE_I, SAVE_DATE_I, VERSION_I, SAVED_BY_I, WSID_I, WORKSPACE_I, CHSUM_I, SIZE_I, META_I] = list(range(11))  # object_info tuple
        return '/'.join([str(obj_info[WSID_I]), str(obj_info[OBJID_I]), str(obj_info[VERSION_I])])

    # get obj_name
    def get_obj_name_from_obj_info (self, obj_info):
        [OBJID_I, NAME_I, TYPE_I, SAVE_DATE_I, VERSION_I, SAVED_BY_I, WSID_I, WORKSPACE_I, CHSUM_I, SIZE_I, META_I] = list(range(11))  # object_info tuple
        return obj_info[NAME_I]

    # retrieve stored obj info
    def _get_stored_obj_info (self, obj_type, obj_name, item_i=0):
        infoAttr = obj_type + 'Info_list' # e.g. 'ama' or 'genome'
        nameAttr = obj_type + 'Name_list'
        if hasattr(self.__class__, infoAttr):
            try:
                info_list = getattr(self.__class__, infoAttr)
                name_list = getattr(self.__class__, nameAttr)
                info      = info_list[item_i]
                name      = name_list[item_i]
                if info != None:
                    if name != obj_name:
                        info_list[item_i] = None
                        name_list[item_i] = None
                        setattr (self.__class__, infoAttr, info_list)
                        setattr (self.__class__, nameAttr, name_list)
                    else:
                        return info
            except:
                pass
        return None

    # save stored obj info
    def _save_stored_obj_info (self, obj_type, obj_info, obj_name, item_i=0):
        infoAttr = obj_type + 'Info_list' # e.g. 'ama' or 'genome'
        nameAttr = obj_type + 'Name_list'
        if not hasattr(self.__class__, infoAttr):
            setattr (self.__class__, infoAttr, [])
            setattr (self.__class__, nameAttr, [])

        info_list = getattr(self.__class__, infoAttr)
        name_list = getattr(self.__class__, nameAttr)
        for i in range(item_i+1):
            try:
                assigned = info_list[i]
            except:
                info_list.append(None)
                name_list.append(None)
        info_list[item_i] = obj_info
        name_list[item_i] = obj_name
        setattr (self.__class__, infoAttr, info_list)
        setattr (self.__class__, nameAttr, name_list)
        return
        
        
    # call this method to get the WS object info of a Genome
    #   (will upload the example data if this is the first time the method is called during tests)
    def getGenomeInfo(self, genome_basename, item_i=0):
        info = self._get_stored_obj_info ('genome', genome_basename, item_i)
        if info != None:
            return info

        # 1) transform genbank to kbase genome object and upload to ws
        shared_dir = "/kb/module/work/tmp"
        genome_data_file = 'data/genomes/'+genome_basename+'.gbff.gz'
        genome_file = os.path.join(shared_dir, os.path.basename(genome_data_file))
        shutil.copy(genome_data_file, genome_file)

        SERVICE_VER = 'release'
        GFU = GenomeFileUtil(os.environ['SDK_CALLBACK_URL'],
                             token=self.getContext()['token'],
                             service_ver=SERVICE_VER
                         )
        print ("UPLOADING genome: "+genome_basename+" to WORKSPACE "+self.getWsName()+" ...")
        genome_upload_result = GFU.genbank_to_genome({'file': {'path': genome_file },
                                                      'workspace_name': self.getWsName(),
                                                      'genome_name': genome_basename
                                                  })
        pprint(genome_upload_result)
        genome_ref = genome_upload_result['genome_ref']
        new_obj_info = self.getWsClient().get_object_info_new({'objects': [{'ref': genome_ref}]})[0]

        # 2) store it
        self._save_stored_obj_info ('genome', new_obj_info, genome_basename, item_i)
        return new_obj_info

    
    # call this method to get the WS object info of an AnnotatedMetagenomeAssembly
    #   (will upload the example data if this is the first time the method is called during tests)
    def getAMAInfo(self, ama_basename, item_i=0):
        info = self._get_stored_obj_info ('ama', ama_basename, item_i)
        if info != None:
            return info

        # 1) transform GFF+FNA to kbase AMA object and upload to ws
        shared_dir = "/kb/module/work/tmp"
        ama_gff_srcfile = 'data/amas/'+ama_basename+'.gff'
        ama_fna_srcfile = 'data/amas/'+ama_basename+'.fa'
        ama_gff_dstfile = os.path.join(shared_dir, os.path.basename(ama_gff_srcfile))
        ama_fna_dstfile = os.path.join(shared_dir, os.path.basename(ama_fna_srcfile))
        shutil.copy(ama_gff_srcfile, ama_gff_dstfile)
        shutil.copy(ama_fna_srcfile, ama_fna_dstfile)

        try:
            SERVICE_VER = 'release'
            GFU = GenomeFileUtil(os.environ['SDK_CALLBACK_URL'],
                                 token=self.getContext()['token'],
                                 service_ver=SERVICE_VER
            )
        except:
            raise ValueError ("unable to obtain GenomeFileUtil client")
        print ("UPLOADING AMA: "+ama_basename+" to WORKSPACE "+self.getWsName()+" ...")
        ama_upload_params = {
            "workspace_name": self.getWsName(),
            "genome_name": ama_basename,
            "fasta_file": {"path": ama_fna_dstfile},
            "gff_file": {"path": ama_gff_dstfile},
            "source": "GFF",
            "scientific_name": "TEST AMA",
            "generate_missing_genes": "True"
        }        
        try:
            ama_upload_result = GFU.fasta_gff_to_metagenome(ama_upload_params)
        except:
            raise ValueError("unable to upload test AMA data object")
        print ("AMA UPLOADED")
        pprint(ama_upload_result)

        ama_ref = ama_upload_result['metagenome_ref']
        new_obj_info = self.getWsClient().get_object_info_new({'objects': [{'ref': ama_ref}]})[0]

        # 2) store it
        self._save_stored_obj_info ('ama', new_obj_info, ama_basename, item_i)
        return new_obj_info


    # call this method to get the WS object info of a Tree
    #   (will upload the example data if this is the first time the method is called during tests)
    def getTreeInfo(self, tree_basename, lib_i=0, genome_ref_map=None):
        if hasattr(self.__class__, 'treeInfo_list'):
            try:
                info = self.__class__.treeInfo_list[lib_i]
                name = self.__class__.treeName_list[lib_i]
                if info != None:
                    if name != tree_basename:
                        self.__class__.treeInfo_list[lib_i] = None
                        self.__class__.treeName_list[lib_i] = None
                    else:
                        return info
            except:
                pass

        # 1) transform json to kbase Tree object and upload to ws
        shared_dir = "/kb/module/work/tmp"
        tree_data_file = 'data/trees/'+tree_basename+'.json'
        tree_file = os.path.join(shared_dir, os.path.basename(tree_data_file))
        shutil.copy(tree_data_file, tree_file)

        # create object
        with open (tree_file, 'r') as tree_fh:
            tree_obj = json.load(tree_fh)

        # update genome_refs
        if genome_ref_map != None:
            for label_id in tree_obj['default_node_labels']:
                for old_genome_ref in genome_ref_map.keys():
                    tree_obj['default_node_labels'][label_id] = tree_obj['default_node_labels'][label_id].replace(old_genome_ref, genome_ref_map[old_genome_ref])
            for label_id in tree_obj['ws_refs'].keys():
                new_genome_refs = []
                for old_genome_ref in tree_obj['ws_refs'][label_id]['g']:
                    new_genome_refs.append(genome_ref_map[old_genome_ref])
                tree_obj['ws_refs'][label_id]['g'] = new_genome_refs

        provenance = [{}]
        new_obj_info = self.getWsClient().save_objects({
            'workspace': self.getWsName(), 
            'objects': [
                {
                    'type': 'KBaseTrees.Tree',
                    'data': tree_obj,
                    'name': tree_basename+'.test_TREE',
                    'meta': {},
                    'provenance': provenance
                }
            ]})[0]

        # 2) store it
        if not hasattr(self.__class__, 'treeInfo_list'):
            self.__class__.treeInfo_list = []
            self.__class__.treeName_list = []
        for i in range(lib_i+1):
            try:
                assigned = self.__class__.treeInfo_list[i]
            except:
                self.__class__.treeInfo_list.append(None)
                self.__class__.treeName_list.append(None)

        self.__class__.treeInfo_list[lib_i] = new_obj_info
        self.__class__.treeName_list[lib_i] = tree_basename
        return new_obj_info


    # Test eggnog-mapper (ENM): Single Genome target
    #
    # Uncomment to skip this test
    # HIDE @unittest.skip("skipped test_01_Genome_ENM")
    def test_01_Genome_ENM(self):
        [OBJID_I, NAME_I, TYPE_I, SAVE_DATE_I, VERSION_I, SAVED_BY_I, WSID_I, WORKSPACE_I, CHSUM_I, SIZE_I, META_I] = list(range(11
))  # object_info tuple
        test_name = 'test_01_Genome_ENM'
        self._print_test_name(test_name)

        load_genomes = [
            { 'file': 'GCF_000287295.1_ASM28729v1_genomic',
              'sciname': 'Candidatus Carsonella ruddii HT isolate Thao2000'
            },
#            { 'file': 'GCF_000306885.1_ASM30688v1_genomic',
#              'sciname': 'Wolbachia endosymbiont of Onchocerca ochengi'
#            },
#            { 'file': 'GCF_001439985.1_wTPRE_1.0_genomic',
#              'sciname': 'Wolbachia endosymbiont of Trichogramma pretiosum'
#            },
#            { 'file': 'GCF_000022285.1_ASM2228v1_genomic',
#              'sciname': 'Wolbachia sp. wRi'
#            }
        ]
        for genome_i,genome in enumerate(load_genomes):
            obj_info = self.getGenomeInfo(genome['file'], genome_i)            
            load_genomes[genome_i]['ref'] = self.get_obj_ref_from_obj_info(obj_info)
            load_genomes[genome_i]['name'] = self.get_obj_name_from_obj_info(obj_info)

        # run
        parameters = { 'workspace_name': self.getWsName(),
                       'target_refs': [load_genomes[0]['ref']],
                       'novel_fams': '1'
                     }
        ret = self.getImpl().run_eggnog_mapper(self.getContext(), parameters)[0]
        self.assertIsNotNone(ret['report_ref'])

        # check created obj
        """
        report_obj = self.dfuClient.get_objects([{'ref':ret['report_ref']}])[0]['data']
        self.assertIsNotNone(report_obj['objects_created'][0]['ref'])

        created_obj_0_info = self.getWsClient().get_object_info_new({'objects':[{'ref':report_obj['objects_created'][0]['ref']}]})[0]
        self.assertEqual(created_obj_0_info[NAME_I], genome_name_0)
        self.assertEqual(created_obj_0_info[TYPE_I].split('-')[0], obj_out_type)
        """


    # Test eggnog-mapper (ENM): GenomeSet target
    #
    # Uncomment to skip this test
    # HIDE @unittest.skip("skipped test_02_GenomeSet_ENM")
    def test_02_GenomeSet_ENM(self):
        [OBJID_I, NAME_I, TYPE_I, SAVE_DATE_I, VERSION_I, SAVED_BY_I, WSID_I, WORKSPACE_I, CHSUM_I, SIZE_I, META_I] = list(range(11
))  # object_info tuple
        test_name = 'test_02_GenomeSet_ENM'
        self._print_test_name(test_name)

        load_genomes = [
            { 'file': 'GCF_000287295.1_ASM28729v1_genomic',
              'sciname': 'Candidatus Carsonella ruddii HT isolate Thao2000'
            },
            { 'file': 'GCF_000306885.1_ASM30688v1_genomic',
              'sciname': 'Wolbachia endosymbiont of Onchocerca ochengi'
            },
            { 'file': 'GCF_001439985.1_wTPRE_1.0_genomic',
              'sciname': 'Wolbachia endosymbiont of Trichogramma pretiosum'
            },
            { 'file': 'GCF_000022285.1_ASM2228v1_genomic',
              'sciname': 'Wolbachia sp. wRi'
            }
        ]
        for genome_i,genome in enumerate(load_genomes):
            obj_info = self.getGenomeInfo(genome['file'], genome_i)            
            load_genomes[genome_i]['ref'] = self.get_obj_ref_from_obj_info(obj_info)
            load_genomes[genome_i]['name'] = self.get_obj_name_from_obj_info(obj_info)

        # create GenomeSet
        genomeSet_name = test_name+'.GenomeSet'
        testGS = {
            'description': 'four genomes',
            'elements': dict()
        }
        for genome_i,genome in enumerate(load_genomes): 
            testGS['elements'][genome['sciname']] = { 'ref': genome['ref'] }

        obj_info = self.getWsClient().save_objects({'workspace': self.getWsName(),       
                                                    'objects': [
                                                        {
                                                            'type':'KBaseSearch.GenomeSet',
                                                            'data':testGS,
                                                            'name':genomeSet_name,
                                                            'meta':{},
                                                            'provenance':[
                                                                {
                                                                    'service':'kb_eggnog_mapper',
                                                                    'method':'eggnog-mapper'
                                                                }
                                                            ]
                                                        }]
                                                })[0]

        #pprint(obj_info)
        target_genomeSet_ref = self.get_obj_ref_from_obj_info(obj_info)            
            
        # run
        parameters = { 'workspace_name': self.getWsName(),
                       'target_refs': [target_genomeSet_ref],
                       'novel_fams': '1'
                     }
        ret = self.getImpl().run_eggnog_mapper(self.getContext(), parameters)[0]
        self.assertIsNotNone(ret['report_ref'])

        # check created obj
        """
        report_obj = self.dfuClient.get_objects([{'ref':ret['report_ref']}])[0]['data']
        self.assertIsNotNone(report_obj['objects_created'][0]['ref'])

        created_obj_0_info = self.getWsClient().get_object_info_new({'objects':[{'ref':report_obj['objects_created'][0]['ref']}]})[0]
        self.assertEqual(created_obj_0_info[NAME_I], genome_name_0)
        self.assertEqual(created_obj_0_info[TYPE_I].split('-')[0], obj_out_type)
        """


    # Test eggnog-mapper (ENM): SpeciesTree target
    #
    # Uncomment to skip this test
    # HIDE @unittest.skip("skipped test_03_SpeciesTree_ENM")
    def test_03_SpeciesTree_ENM(self):
        [OBJID_I, NAME_I, TYPE_I, SAVE_DATE_I, VERSION_I, SAVED_BY_I, WSID_I, WORKSPACE_I, CHSUM_I, SIZE_I, META_I] = list(range(11
))  # object_info tuple
        test_name = 'test_03_SpeciesTree_ENM'
        self._print_test_name(test_name)

        load_genomes = [
            { 'file': 'GCF_000287295.1_ASM28729v1_genomic',
              'sciname': 'Candidatus Carsonella ruddii HT isolate Thao2000'
            },
            { 'file': 'GCF_000306885.1_ASM30688v1_genomic',
              'sciname': 'Wolbachia endosymbiont of Onchocerca ochengi'
            },
            { 'file': 'GCF_001439985.1_wTPRE_1.0_genomic',
              'sciname': 'Wolbachia endosymbiont of Trichogramma pretiosum'
            },
            { 'file': 'GCF_000022285.1_ASM2228v1_genomic',
              'sciname': 'Wolbachia sp. wRi'
            }
        ]
        for genome_i,genome in enumerate(load_genomes):
            obj_info = self.getGenomeInfo(genome['file'], genome_i)            
            load_genomes[genome_i]['ref'] = self.get_obj_ref_from_obj_info(obj_info)
            load_genomes[genome_i]['name'] = self.get_obj_name_from_obj_info(obj_info)

        # create Tree
        genome_refs_map = { '23880/3/1': load_genomes[0]['ref'],
                            '23880/4/1': load_genomes[1]['ref'],
                            '23880/5/1': load_genomes[2]['ref'],
                            '23880/6/1': load_genomes[3]['ref']
                          }        
        speciesTree_name = test_name+'.SpeciesTree'
        tree_obj_info = self.getTreeInfo('Tiny_things.SpeciesTree', 0, genome_refs_map)
        target_tree_ref = self.get_obj_ref_from_obj_info(tree_obj_info)
            
        # run
        parameters = { 'workspace_name': self.getWsName(),
                       'target_refs': [target_tree_ref],
                       'novel_fams': '1'
                     }
        ret = self.getImpl().run_eggnog_mapper(self.getContext(), parameters)[0]
        self.assertIsNotNone(ret['report_ref'])

        # check created obj
        """
        report_obj = self.dfuClient.get_objects([{'ref':ret['report_ref']}])[0]['data']
        self.assertIsNotNone(report_obj['objects_created'][0]['ref'])

        created_obj_0_info = self.getWsClient().get_object_info_new({'objects':[{'ref':report_obj['objects_created'][0]['ref']}]})[0]
        self.assertEqual(created_obj_0_info[NAME_I], genome_name_0)
        self.assertEqual(created_obj_0_info[TYPE_I].split('-')[0], obj_out_type)
        """


    # Test eggnog-mapper (ENM): AMA target
    #
    # Uncomment to skip this test
    # HIDE @unittest.skip("skipped test_04_AMA_ENM")
    def test_04_AMA_ENM(self):
        [OBJID_I, NAME_I, TYPE_I, SAVE_DATE_I, VERSION_I, SAVED_BY_I, WSID_I, WORKSPACE_I, CHSUM_I, SIZE_I, META_I] = list(range(11
))  # object_info tuple
        test_name = 'test_04_AMA_ENM'
        self._print_test_name(test_name)

        load_amas = [
            { 'file': 'test_ama',
            }
        ]
        for ama_i,ama in enumerate(load_amas):
            obj_info = self.getAMAInfo(load_amas[ama_i]['file'], ama_i)            
            load_amas[ama_i]['ref'] = self.get_obj_ref_from_obj_info(obj_info)
            load_amas[ama_i]['name'] = self.get_obj_name_from_obj_info(obj_info)

        # run
        parameters = { 'workspace_name': self.getWsName(),
                       'target_refs': [load_amas[0]['ref']],
                       'novel_fams': '1'
                     }
        ret = self.getImpl().run_eggnog_mapper(self.getContext(), parameters)[0]
        self.assertIsNotNone(ret['report_ref'])

        # check created obj
        """
        report_obj = self.dfuClient.get_objects([{'ref':ret['report_ref']}])[0]['data']
        self.assertIsNotNone(report_obj['objects_created'][0]['ref'])

        created_obj_0_info = self.getWsClient().get_object_info_new({'objects':[{'ref':report_obj['objects_created'][0]['ref']}]})[0]
        self.assertEqual(created_obj_0_info[NAME_I], genome_name_0)
        self.assertEqual(created_obj_0_info[TYPE_I].split('-')[0], obj_out_type)
        """


    # Test eggnog-mapper (ENM): AMA target + species tree
    #
    # Uncomment to skip this test
    # HIDE @unittest.skip("skipped test_05_multitarget_AMA_SpeciesTree_ENM")
    def test_05_multitarget_AMA_SpeciesTree_ENM(self):
        [OBJID_I, NAME_I, TYPE_I, SAVE_DATE_I, VERSION_I, SAVED_BY_I, WSID_I, WORKSPACE_I, CHSUM_I, SIZE_I, META_I] = list(range(11
))  # object_info tuple
        test_name = 'test_05_multitarget_AMA_SpeciesTree_ENM'
        self._print_test_name(test_name)

        # AMA
        load_amas = [
            { 'file': 'test_ama',
            }
        ]
        for ama_i,ama in enumerate(load_amas):
            obj_info = self.getAMAInfo(load_amas[ama_i]['file'], ama_i)            
            load_amas[ama_i]['ref'] = self.get_obj_ref_from_obj_info(obj_info)
            load_amas[ama_i]['name'] = self.get_obj_name_from_obj_info(obj_info)

        # Species Tree
        load_genomes = [
            { 'file': 'GCF_000287295.1_ASM28729v1_genomic',
              'sciname': 'Candidatus Carsonella ruddii HT isolate Thao2000'
            },
            { 'file': 'GCF_000306885.1_ASM30688v1_genomic',
              'sciname': 'Wolbachia endosymbiont of Onchocerca ochengi'
            },
            { 'file': 'GCF_001439985.1_wTPRE_1.0_genomic',
              'sciname': 'Wolbachia endosymbiont of Trichogramma pretiosum'
            },
            { 'file': 'GCF_000022285.1_ASM2228v1_genomic',
              'sciname': 'Wolbachia sp. wRi'
            }
        ]
        for genome_i,genome in enumerate(load_genomes):
            obj_info = self.getGenomeInfo(genome['file'], genome_i)            
            load_genomes[genome_i]['ref'] = self.get_obj_ref_from_obj_info(obj_info)
            load_genomes[genome_i]['name'] = self.get_obj_name_from_obj_info(obj_info)

        # create Tree
        genome_refs_map = { '23880/3/1': load_genomes[0]['ref'],
                            '23880/4/1': load_genomes[1]['ref'],
                            '23880/5/1': load_genomes[2]['ref'],
                            '23880/6/1': load_genomes[3]['ref']
                          }        
        speciesTree_name = test_name+'.SpeciesTree'
        tree_obj_info = self.getTreeInfo('Tiny_things.SpeciesTree', 0, genome_refs_map)
        target_tree_ref = self.get_obj_ref_from_obj_info(tree_obj_info)

        # run
        parameters = { 'workspace_name': self.getWsName(),
                       'target_refs': [load_amas[0]['ref'], target_tree_ref],
                       'novel_fams': '1'
                     }
        ret = self.getImpl().run_eggnog_mapper(self.getContext(), parameters)[0]
        self.assertIsNotNone(ret['report_ref'])

        # check created obj
        """
        report_obj = self.dfuClient.get_objects([{'ref':ret['report_ref']}])[0]['data']
        self.assertIsNotNone(report_obj['objects_created'][0]['ref'])

        created_obj_0_info = self.getWsClient().get_object_info_new({'objects':[{'ref':report_obj['objects_created'][0]['ref']}]})[0]
        self.assertEqual(created_obj_0_info[NAME_I], genome_name_0)
        self.assertEqual(created_obj_0_info[TYPE_I].split('-')[0], obj_out_type)
        """
