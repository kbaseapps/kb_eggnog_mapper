FROM kbase/sdkpython:3.8.10
MAINTAINER KBase Developer [Dylan Chivian (DCChivian@lbl.gov)]
# -----------------------------------------
# In this section, you can install any system dependencies required
# to run your App.  For instance, you could place an apt-get update or
# install line here, a git checkout to download code, or run any other
# installation scripts.


# Update
RUN apt-get update

# udpate certs
RUN apt-get upgrade -y
RUN sed -i 's/\(.*DST_Root_CA_X3.crt\)/!\1/' /etc/ca-certificates.conf
RUN update-ca-certificates

# -----------------------------------------

COPY ./ /kb/module
RUN mkdir -p /kb/module/work
RUN chmod -R a+rw /kb/module

WORKDIR /kb/module

# install eggnog-mapper
ENV VER=2.1.9
RUN git clone --depth 1 --single-branch --branch ${VER} https://github.com/eggnogdb/eggnog-mapper

RUN make all

ENTRYPOINT [ "./scripts/entrypoint.sh" ]

CMD [ ]
