/*
A KBase module: kb_eggnog_mapper
*/

module kb_genetree {

        
    /*
    ** Common types
    */
    typedef string workspace_name;
    typedef int    workspace_id;
    typedef string data_obj_ref;
    typedef string data_obj_name;
    typedef int    bool;


    /*
    ** Report Results
    */
    typedef structure {
        string report_name;
        string report_ref;
    } ReportResults;


    /* run_eggnog_mapper()
    **
    ** run eggnog-mapper on a collection of genomes and/or AMAs
    */
    typedef structure {
        workspace_name  workspace_name;
        workspace_id    workspace_id;
        data_obj_ref    input_targets_ref;  /* Genome, AMA, GenomeSet, SpeciesTree */
        bool            novel_fams;
        string          genome_disp_name_config;
    } EggnogMapper_Input;

    funcdef run_eggnog_mapper(EggnogMapper_Input params)
        returns (ReportResults output)
        authentication required;
};
