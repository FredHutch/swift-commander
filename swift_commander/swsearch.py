#!/usr/bin/env python3

# get multisegment swift files in parallel

import re
import argparse
import fnmatch
import psutil

import sys,os,getopt,json
import time

import multiprocessing

import swiftclient

def create_sw_conn(swift_auth_token,storage_url):
    if swift_auth_token and storage_url:
        return swiftclient.Connection(preauthtoken=swift_auth_token,
            preauthurl=storage_url)

    swift_auth=os.environ.get("ST_AUTH")
    swift_user=os.environ.get("ST_USER")
    swift_key=os.environ.get("ST_KEY")

    if swift_auth and swift_user and swift_key:
        return swiftclient.Connection(authurl=swift_auth,user=swift_user,
            key=swift_key)

    print("Error: Swift environment not configured!")
    sys.exit()

textchars=bytearray({7,8,9,10,12,13,27}|set(range(0x20, 0x100))-{0x7f})
is_binary_string=lambda bytes:bool(bytes.translate(None,textchars))

def print_match(object,body,pattern):
    offset=body.find(pattern)
    if offset!=-1:
        print("%s: matched at offset %d" % (object,offset),flush=True)
        range=25
        excerpt=body[max(0,offset-range):offset+len(pattern)+range]
        print('\t'+repr(excerpt.decode()))

def search_object(parse_arg,object):
    sc=create_sw_conn(parse_arg.authtoken,parse_arg.storage_url)

    match=object.find(parse_arg.pattern)
    if match!=-1:
       print("%s: matched object name" % object,flush=True)

    headers,body=sc.get_object(parse_arg.container,object)
    if not parse_arg.binary or not is_binary_string(body):
        #print("scanning object",object,flush=True)
        if not parse_arg.insensitive:
            print_match(object,body,bytes(parse_arg.pattern,"utf-8"))
        else:
            m_o=re.search(bytes(parse_arg.pattern,"utf-8"),body,re.IGNORECASE)
            if m_o:
                print_match(object,body,m_o.group(0))

    sc.close()

# order is type,sc,container,object,pattern
def search_worker(item):
    search_object(*item)

skip_suffices=tuple(['.bam','.gz','.tif','.nc','.fcs','.dv','.MOV','.bin',\
    '.jpg','.zip','.nd2','.lsm','.bz2','.avi','.pdf','.tgz','.xls','.png',\
    '.gif','.pyc'])

def search_container(parse_arg):
    global skip_suffices

    # changed from obsolete psutil.phymem_usage().available
    memavail=psutil.virtual_memory().available

    sc=create_sw_conn(parse_arg.authtoken,parse_arg.storage_url)

    try:
        if parse_arg.prefix:
            headers,objs=sc.get_container(parse_arg.container,
                prefix=parse_arg.prefix,full_listing=True)
        else:
            headers,objs=sc.get_container(parse_arg.container,full_listing=True)

        search_pool=multiprocessing.Pool(parse_arg.maxproc)

        for obj in objs:
            if obj['name'].endswith(skip_suffices) or\
                (parse_arg.filename and not \
                    fnmatch.fnmatch(obj['name'],parse_arg.filename)):
                    continue

            if obj['bytes']>memavail:
                print("Object",obj['name'],"too large for memory!",
                    file=sys.stderr)
                continue

            #search_pool.apply_async(search_worker,[[parse_arg,obj['name']]])
            search_object(parse_arg,obj['name'])

        search_pool.close()
        search_pool.join()

    except swiftclient.ClientException:
        print("Error: cannot access Swift container '%s'!" % 
            parse_arg.container)

    sc.close()

def parse_arguments():
    parser=argparse.ArgumentParser(
        description="Search text objects for pattern")
    parser.add_argument('-c','--container',required=True)
    parser.add_argument('pattern',type=str)
    parser.add_argument('-m','--maxproc',type=int,
        help="maximum number of processes to run",default=5)
    parser.add_argument('-a','--authtoken',
        default=os.environ.get("OS_AUTH_TOKEN"),
        help='swift authentication token (required when storage-url is used)')
    parser.add_argument('-s','--storage-url',
        default=os.environ.get("OS_STORAGE_URL"),
        help='swift storage url (required when authtoken is used)')
    parser.add_argument('-f','--filename',
        help='limit search to objects matching this pattern')
    parser.add_argument('-p','--prefix',
        help='limit search to objects matching this prefix')
    parser.add_argument('-b','--binary',action='store_true',
        help='try to exclude files identified as binary')
    parser.add_argument('-i','--insensitive',action='store_true',
        help='case insensitive search')

    return parser.parse_args()

def main():
    search_container(parse_arguments())

if __name__ == '__main__':
    main()
