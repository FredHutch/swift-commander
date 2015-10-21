#!/usr/bin/env python3

# get multisegment swift files in parallel

import argparse
import fnmatch

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

def search_single_object(sc,container,object,pattern,multi=""):
    headers,body=sc.get_object(container,object)

    if not is_binary_string(body):
        s=body.decode("utf-8")
        match=s.find(pattern)
        if match!=-1:
            if multi:
                print(multi+':'+object+": matched at offset",match)
            else:
                print(object+": matched at offset",match)

def search_multi_object(sc,container,object,pattern):
    headers,body=sc.get_object(container,object,
        query_string='multipart-manifest=get')
    manifest=json.loads(body.decode())
    for segment in manifest:
        segment_container,segment_obj=parseSwiftUrl(segment['name'])
        search_single_object(sc,segment_container,segment_object,pattern,
            object)

def search_objects(type,parse_arg,object):
    sc=create_sw_conn(parse_arg.authtoken,parse_arg.storage_url)

    if type=='m':
        search_multi_object(sc,parse_arg.container,object,parse_arg.pattern)
    else:
        search_single_object(sc,parse_arg.container,object,parse_arg.pattern)

    sc.close()

# order is type,sc,container,object,pattern
def search_worker(item):
    search_objects(*item)

skip_suffices=tuple(['.gz'])

def search_container(parse_arg):
    global skip_suffices

    obj_list=[]

    sc=create_sw_conn(parse_arg.authtoken,parse_arg.storage_url)

    try:
        headers,objs=sc.get_container(parse_arg.container,full_listing=True)
        for obj in objs:
            if obj['name'].endswith(skip_suffices) or\
                (parse_arg.filename and not \
                    fnmatch.fnmatch(obj['name'],parse_arg.filename)):
                    continue

            try:
                headers=sc.head_object(parse_arg.container, obj['name'])
            except:
                headers=[]
           
            if 'x-static-large-object' in headers:
                obj_list.append(['m',parse_arg,obj['name']])
            else:
                obj_list.append(['s',parse_arg,obj['name']])

        search_pool=multiprocessing.Pool(parse_arg.maxproc)
        search_pool.map(search_worker,obj_list)

    except swiftclient.ClientException:
        print("Error: cannot access Swift container '%s'!" % 
            parse_arg.container)

    sc.close()

def parse_arguments():
    parser=argparse.ArgumentParser(
        description="Search text objects for pattern")
    parser.add_argument('-c','--container',required=True)
    #parser.add_argument('pattern',nargs=1,type=str)
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
        help='search objects with name matching this pattern')

    return parser.parse_args()

def main(args):
    search_container(parse_arguments())

if __name__ == '__main__':
    main(sys.argv[1:])
