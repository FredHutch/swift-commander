#! /usr/bin/env python2

# Script for comparing the md5sum of a posix file with the md5sums of a multi chunk swift object
#
# swcompare dirkpetersen / Jan 2015 
#

import swiftclient, sys, os, argparse, functools, hashlib, json

class KeyboardInterruptError(Exception): pass

def main():

    c=create_sw_conn()
    md5all = hashlib.md5()

    print ("comparing swift object %s/%s with file %s..." % (args.container, args.obj, args.locfile))

    #headers, objects = c.get_container(args.container,prefix=args.prefix,full_listing=True)
    headers, body = c.get_object(args.container, args.obj, query_string='multipart-manifest=get')

    with open(args.locfile) as f:
        is_valid = check_manifest(body, f, md5all)

    if is_valid:
        print ("object %s/%s and file %s are identical!" % (args.container, args.obj, args.locfile))
        return 0
    else:
        print ("Error: object %s/%s and file %s are different!" % (args.container, args.obj, args.locfile))
        return 1

def check_manifest(manifest, body, md5all):
    """
    check if a body is the same object described by the manifest

    :param manifest: the raw body of the manifest from swift
    :param body: a file like object to check against the manfiest
    """
    manifest = json.loads(manifest)
    for segment in manifest:
        print ("testing chunk %s" % segment['name'])
        chunk = body.read(segment['bytes'])
        hasher = hashlib.md5(chunk)
        md5all.update(chunk)
        if hasher.hexdigest() != segment['hash']:
            print ('%s != %s' % (hasher.hexdigest(), segment['hash']))            
            return False
    print("md5sum:%s" % md5all.hexdigest())
    return True

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

    parser = argparse.ArgumentParser(prog='swhashcomp',
        description='compare the md5sum of a local file with the hash ' + \
        'of a swift object folder after a data migration ' + \
        '()')
    parser.add_argument( '--locfile', '-f', dest='locfile',
        action='store',
        help='a local or networked file to compare',
        default='' )        
    parser.add_argument( '--container', '-c', dest='container',
        action='store',
        help='a container in the swift object store',
        default='' )
    parser.add_argument( '--obj', '-o', dest='obj',
        action='store',
        help='an object in a swift container',
        default=None)
    args = parser.parse_args()
    if not args.locfile:
        parser.error('required option --locfile not given !')
    if not args.container:
        parser.error('required option --container not given !')
    if not args.obj:
        parser.error('required option --obj not given !')
    return args

if __name__ == '__main__':
    # Parse command-line arguments
    args = parse_arguments()
    sys.exit(main())

