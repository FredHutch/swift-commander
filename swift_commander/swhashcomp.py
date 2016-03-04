#! /usr/bin/env python3

# Script for comparing the md5sum of a posix file with the md5sums of a multi chunk swift object
#
# swhashcomp dirkpetersen / Feb 2015 
#

import swiftclient, sys, os, argparse, functools, hashlib, json

class KeyboardInterruptError(Exception): pass

def main():

    c=create_sw_conn()
    md5all = hashlib.md5()

    print ("    comparing swift object %s/%s with %s..." % (args.container, args.obj, args.locfile))

    #headers, objects = c.get_container(args.container,prefix=args.prefix,full_listing=True)
    headers = c.head_object(args.container, args.obj)

    if 'x-static-large-object' in headers:
        #print(headers['x-static-large-object'])
        headers, body = c.get_object(args.container, args.obj, query_string='multipart-manifest=get')
        if not os.path.isfile(args.locfile):
            if 'md5sum' in headers:
                if args.locfile.strip() == headers['md5sum']:
                    print('    md5sum:%s' % headers['md5sum'])
                    is_valid = True
                else:
                    is_valid = False
            else:
                is_valid = check_segments(body,args.locfile.strip(),c)
        else:
            if os.path.splitext(args.locfile)[1].lower() == '.md5':
                with open(args.locfile, 'r') as f:
                    myhash = f.read().split(None,1)[0]
                    print('md5sum from md5 file: %s' % myhash)
                    is_valid = check_segments(body,myhash,c)
            else:
                with open(args.locfile, 'rb') as f:
                    is_valid = check_manifest(body, f, md5all)
    else:
        is_valid=False
        if os.path.isfile(args.locfile):
            if os.path.splitext(args.locfile)[1].lower() == '.md5':
                with open(args.locfile, 'r') as f:
                    myhash = f.read().split(None,1)[0]	
                print('md5sum from md5 file: %s' % myhash)
            else:
                with open(args.locfile, 'rb') as f:
                    hasher = hashlib.md5(f.read()) # needed for compatiblity between python3 and python2
                    myhash = hasher.hexdigest()
                print('md5sum of local file: %s' % myhash)
            if myhash == headers['etag']:
                print('    md5sum:%s' % headers['etag'])
                is_valid = True
        else:
            if args.locfile.strip() == headers['etag']:
                print('    md5sum:%s' % headers['etag'])
                is_valid = True

    if is_valid:
        print ("object %s/%s and '%s' are identical!" % (args.container, args.obj, args.locfile))
        return 0
    else:
        print ("*** WARNING ***: object %s/%s and '%s' are different!" % (args.container, args.obj, args.locfile))
        return 1

def check_manifest(manifest, body, md5all):
    """
    check if a body is the same object described by the manifest

    :param manifest: the raw body of the manifest from swift
    :param body: a file like object to check against the manfiest
    """
    manifest = json.loads(manifest.decode())
    for segment in manifest:
        print ("    testing chunk %s" % segment['name'])
        chunk = body.read(segment['bytes'])
        hasher = hashlib.md5(chunk)
        md5all.update(chunk)
        if hasher.hexdigest() != segment['hash']:
            print ('    %s != %s' % (hasher.hexdigest(), segment['hash']))            
            return False
    print("    md5sum:%s" % md5all.hexdigest())
    return True

def check_segments(manifest,md5sum,c):
    manifest = json.loads(manifest.decode())
    digest = hashlib.md5()
    for segment in manifest:
        print ("    please wait ... testing chunk %s" % segment['name'])
        segment_container, segment_obj = parseSwiftUrl(segment['name'])
        attributes, content = c.get_object(segment_container, segment_obj)
        digest.update(content)
    if digest.hexdigest() != md5sum:
        print ('    %s != %s' % (digest.hexdigest(), md5sum))
        return False
    return True

def create_sw_conn():
    if args.authtoken and args.storageurl:
        return swiftclient.Connection(preauthtoken=args.authtoken, preauthurl=args.storageurl)
    else:
        authtoken=os.environ.get("OS_AUTH_TOKEN")
        storageurl=os.environ.get("OS_STORAGE_URL")
        if authtoken and storageurl:
            return swiftclient.Connection(preauthtoken=authtoken, preauthurl=storageurl)
        else:
            swift_auth=os.environ.get("ST_AUTH")
            swift_user=os.environ.get("ST_USER")
            swift_key=os.environ.get("ST_KEY")
            if swift_auth and swift_user and swift_key:
                return swiftclient.Connection(authurl=swift_auth,user=swift_user,key=swift_key)
                
def parseSwiftUrl(path):
    path = path.lstrip('/')
    components = path.split('/');
    container = components[0];
    obj = '/'.join(components[1:])
    return container, obj

def parse_arguments():
    """
    Gather command-line arguments.
    """

    parser = argparse.ArgumentParser(prog='swhashcomp',
        description='compare the md5sum of a local file or hash with the hash ' + \
        'of a swift object folder after a data migration ' + \
        '')
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
    parser.add_argument( '--authtoken', '-a', dest='authtoken',
        action='store',
        help='a swift authentication token (required when storage-url is used)',
        default=None)
    parser.add_argument( '--storage-url', '-s', dest='storageurl',
        action='store',
        help='a swift storage url (required when authtoken is used)',
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

