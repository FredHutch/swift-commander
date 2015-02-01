#! /usr/bin/env python3

# Script for comparing the size of a posix folder with the size of a swift pseudo folder
#
# swcompare dirkpetersen / Jan 2015 
#

import swiftclient, sys, os, argparse

class KeyboardInterruptError(Exception): pass

def main():

    c=create_sw_conn()
    headers, objects = c.get_container(args.container,prefix=args.prefix,full_listing=True)
    #print(headers)
    #print(objects)
    sbytes=0
    for object in objects:
        sbytes+=object['bytes']
    #print(sbytes)
    pbytes = getFolderSize(args.posixfolder)
    print ("bytes posix folder : %i" % pbytes)
    print ("bytes swift folder : %i" % sbytes)

def getFolderSize(p):
    if "/.snapshot/" in p or os.path.islink(p):
        return 0
    from functools import partial
    prepend = partial(os.path.join, p)
    try:
        return sum([(os.path.getsize(f) if os.path.isfile(f) else getFolderSize(f)) for f in map(prepend, os.listdir(p))])
    except:
        print("    ...Error getting size of folder %s" % p)
        return 0

def create_sw_conn():
    swift_auth=os.environ.get("ST_AUTH")
    swift_user=os.environ.get("ST_USER")
    swift_key=os.environ.get("ST_KEY")
    if swift_auth and swift_user and swift_key:
        return swiftclient.Connection(authurl=swift_auth,user=swift_user,key=swift_key)

def parse_arguments():
    """
    Gather command-line arguments.
    """

    parser = argparse.ArgumentParser(prog='swcompare',
        description='compare the size of a posix folder with the size ' + \
        'of a swift (pseudo) folder after a data migration ' + \
        '()')
    parser.add_argument( '--posixfolder', '-p', dest='posixfolder',
        action='store',
        help='a folder on a posix file system ',
        default='' )        
    parser.add_argument( '--container', '-c', dest='container',
        action='store',
        help='a container in the swift object store',
        default='' )
    parser.add_argument( '--prefix', '-x', dest='prefix',
        action='store',
        help='a swift object prefix',
        default=None)
    parser.add_argument( '--proc', '-m', dest='maxproc',
        action='store',
        type=int,
        help='maximum number of processes to run ',
        default=0 )
    args = parser.parse_args()
    if not args.posixfolder:
        parser.error('required option --posixfolder not given !')
    if not args.container:
        parser.error('required option --container not given !')
    return args

if __name__ == '__main__':
    # Parse command-line arguments
    args = parse_arguments()
    sys.exit(main())
