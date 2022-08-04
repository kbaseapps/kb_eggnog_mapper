#!/bin/bash

. /kb/deployment/user-env.sh

python ./scripts/prepare_deploy_cfg.py ./deploy.cfg ./work/config.properties

if [ -f ./work/token ] ; then
  export KB_AUTH_TOKEN=$(<./work/token)
fi

if [ $# -eq 0 ] ; then
  sh ./scripts/start_server.sh
elif [ "${1}" = "test" ] ; then
  echo "Run Tests"
  make test
elif [ "${1}" = "async" ] ; then
  sh ./scripts/run_async.sh
elif [ "${1}" = "init" ] ; then
  echo "Initialize module"


  # Don't use their script.  colors in output cause KBase registration to fail
  #EGGNOG_DB_DOWNLOAD=/kb/module/eggnog-mapper/download_eggnog_data.py
  
  EGGNOG_DB_VER=5.0.2
  EGGNOG_DB_DIR=/data/eggnogdb/$EGGNOG_DB_VER
  mkdir -p $EGGNOG_DB_DIR
  cd $EGGNOG_DB_DIR

  EGGNOG_DB_BASE_URL="http://eggnog5.embl.de/download/emapperdb-$EGGNOG_DB_VER/"

  # regular gzips
  for DB in eggnog.db eggnog_proteins.dmnd ; do
    cmd="curl -o $DB.gz $EGGNOG_DB_BASE_URL/$DB.gz"
    echo $cmd
    $cmd
    cmd="gunzip $DB.gz"
    echo $cmd
    $cmd
  done

  # tarballs
  for DB in eggnog.taxa mmseqs pfam ; do
    cmd="curl -o $DB.tar.gz $EGGNOG_DB_BASE_URL/$DB.tar.gz"
    echo $cmd
    $cmd
    cmd="tar xfz $DB.tar.gz"
    echo $cmd
    $cmd
    cmd="rm $DB.tar.gz"
    echo $cmd
    $cmd
  done
  
  if [ -s "$EGGNOG_DB_DIR/eggnog.db" -a -s "$EGGNOG_DB_DIR/eggnog.taxa.db" -a -s "$EGGNOG_DB_DIR/eggnog.taxa.db.traverse.pkl" -a -s "$EGGNOG_DB_DIR/eggnog_proteins.dmnd" -a -s "$EGGNOG_DB_DIR/novel_fams.dmnd" -a -s "$EGGNOG_DB_DIR/mmseqs/mmseqs.db" -a -s "$EGGNOG_DB_DIR/Pfam-A.hmm" ] ; then
    echo "DATA DOWNLOADED SUCCESSFULLY"
    touch /data/__READY__
  else
    echo "Init failed"
  fi  
elif [ "${1}" = "bash" ] ; then
  bash
elif [ "${1}" = "report" ] ; then
  export KB_SDK_COMPILE_REPORT_FILE=./work/compile_report.json
  make compile
else
  echo Unknown
fi
